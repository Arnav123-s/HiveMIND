# Muse's work — built by Muse on Muse's side of the bitnet-lab. Fable's side was read read-only; nothing on Fable's side was touched.

"""Consolidation-dream prototype on the champion chassis (layered_half + rotary): phase 1 is ordinary Layered vote training that also remembers the hardest training windows it saw (per-window loss, top-K offsets, deduped), and phase 2 — the dream — replays only those hard windows with the vote threshold lowered (trainer.votes 32 -> 8), so weights that were a few votes short of flipping get a second, cheaper chance to consolidate; the --control modes split that idea into its two levers (hard-window targeting vs lowered threshold) plus a step-matched ordinary-training baseline, so a later run can say which lever, if either, actually moved held loss."""

import argparse, json, random, sys, time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

HERE = Path(__file__).resolve().parent
LAB = HERE.parent
sys.path.insert(0, str(LAB))

from train import CTX, EASE, VOCAB, Layered, Tiny, held_loss, held_windows, offsets

BATCH = 32


def build_batch(data, at):
    return torch.stack([torch.from_numpy(data[i:i + CTX + 1].astype("int64")) for i in at])


def freeze_adamw(trainer):
    """--freeze votes helper: make trainer.opt.step a no-op and return a
    restore callable. In train.py's Layered, the AdamW update (embeddings,
    norms, log_scales) happens only via self.opt.step() inside step(); the
    vote-counter flips live outside it, so they keep working while AdamW
    is frozen."""
    orig_step = trainer.opt.step

    def restore():
        trainer.opt.step = orig_step

    trainer.opt.step = lambda *args, **kwargs: None
    return restore


def snapshot_ternary(trainer):
    """--freeze ternary helper: deep-copy the vote-trainer state."""
    return ([t.clone() for t in trainer.t1], [t.clone() for t in trainer.t2],
            [c.clone() for c in trainer.c1], [c.clone() for c in trainer.c2])


def restore_ternary(trainer, snap):
    """Put the snapshotted t1/t2/c1/c2 back and reinstall, so the model's
    weights again match the restored ternary states (the AdamW parts —
    embeddings, norms, log_scales — keep whatever phase 2 did to them)."""
    trainer.t1, trainer.t2, trainer.c1, trainer.c2 = snap
    trainer.install()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--steps1", type=int, default=120)
    ap.add_argument("--steps2", type=int, default=30)
    ap.add_argument("--dream-votes", type=int, default=8)
    ap.add_argument("--buffer-k", type=int, default=512)
    ap.add_argument("--control", default="full", choices=["none", "target", "threshold", "full"],
                    help="full = hard windows + dream votes; target = hard windows at V=32; "
                         "threshold = random windows + dream votes; none = random windows at V=32 "
                         "(step-matched ordinary training)")
    ap.add_argument("--freeze", default="none", choices=["none", "votes", "ternary"],
                    help="phase-2 attribution control: votes = AdamW parts frozen during "
                         "phase 2 (only t1/t2 vote flips move); ternary = t1/t2/c1/c2 "
                         "snapshotted before phase 2 and restored after (only AdamW "
                         "trains); none = both move, as usual")
    ap.add_argument("--minutes", type=float, default=20.0,
                    help="safety cap only; the run normally ends on the step budgets")
    a = ap.parse_args()

    # 2x2 attribution: (source of phase-2 windows, phase-2 vote threshold).
    use_buffer = a.control in ("full", "target")
    phase2_votes = a.dream_votes if a.control in ("full", "threshold") else 32

    data = np.memmap(LAB / "corpus.u16", dtype=np.uint16, mode="r")
    held = held_windows(data)
    torch.manual_seed(a.seed)
    EASE[0] = 1.0  # non-STE arms, exactly as train.py's main loop
    model = Tiny(layers=2, rotary=True)  # layered_half chassis: 2 blocks instead of 4
    trainer = Layered(model, votes=32)

    total_target = a.steps1 + a.steps2
    rnd = random.Random(a.seed)
    t0 = time.time()
    budget = a.minutes * 60
    truncated = False

    def over_budget():
        return time.time() - t0 >= budget

    h_init = held_loss(model, held)
    print(f"[dream-proto {a.control} s{a.seed}] held_init {h_init:.4f}", flush=True)

    # ---- Phase 1 (wake): ordinary training + hardest-window buffer ----
    # Buffer: {offset: best (highest) per-window loss seen for that offset}.
    # Per-window losses come from the SAME forward used for training (no
    # second forward): cross_entropy with reduction='none', reshaped per
    # window and averaged over each window's tokens; the training loss is
    # that vector's mean, which is exactly train.py's batch loss.
    buffer = {}
    phase1_losses = []
    steps1_done = 0
    for _ in range(a.steps1):
        if over_budget():
            truncated = True
            break
        EASE[0] = 1.0
        at = offsets(rnd, len(data), BATCH)
        x = build_batch(data, at)
        logits = model.next_piece(x[:, :-1])
        loss_tok = F.cross_entropy(logits.reshape(-1, VOCAB), x[:, 1:].reshape(-1),
                                   reduction="none").reshape(BATCH, -1).mean(1)
        loss = loss_tok.mean()
        phase1_losses.append(loss.item())
        for off, win_loss in zip(at, loss_tok.detach().tolist()):
            if off not in buffer or win_loss > buffer[off]:
                buffer[off] = win_loss
        if len(buffer) > a.buffer_k:
            keep = sorted(buffer.items(), key=lambda kv: kv[1], reverse=True)[:a.buffer_k]
            buffer = dict(keep)
        done = (steps1_done + 1) / total_target if total_target else 0.0
        trainer.step(loss, done)
        steps1_done += 1

    buffer_offsets = list(buffer.keys())
    buffer_mean = (sum(buffer.values()) / len(buffer)) if buffer else 0.0
    phase1_mean = (sum(phase1_losses) / len(phase1_losses)) if phase1_losses else 0.0
    h_phase1 = held_loss(model, held)
    print(f"[dream-proto {a.control} s{a.seed}] phase 1 done: steps {steps1_done}, "
          f"held {h_phase1:.4f}, buffer {len(buffer)} offsets, "
          f"buffer mean loss {buffer_mean:.4f} vs phase-1 mean loss {phase1_mean:.4f}",
          flush=True)

    # ---- Phase 2 (dream, or its control): same step count in every mode ----
    # Freeze axis (attribution): 'votes' freezes the AdamW parts so only vote
    # flips can move the model; 'ternary' restores the vote state afterwards
    # so only AdamW could have moved it. Both are undone before held_phase2
    # is measured, whatever happens in the loop.
    steps2_done = 0
    trainer.votes = phase2_votes  # Layered.step reads self.votes on every step
    restore_adamw = freeze_adamw(trainer) if a.freeze == "votes" else None
    ternary_snap = snapshot_ternary(trainer) if a.freeze == "ternary" else None
    try:
        for _ in range(a.steps2):
            if over_budget():
                truncated = True
                break
            EASE[0] = 1.0
            if use_buffer and buffer_offsets:
                at = [rnd.choice(buffer_offsets) for _ in range(BATCH)]  # with replacement
            else:
                # 'threshold' / 'none' — and the degenerate empty-buffer case —
                # draw exactly as train.py does.
                at = offsets(rnd, len(data), BATCH)
            x = build_batch(data, at)
            loss = F.cross_entropy(model.next_piece(x[:, :-1]).reshape(-1, VOCAB),
                                   x[:, 1:].reshape(-1))
            done = (steps1_done + steps2_done + 1) / total_target if total_target else 0.0
            trainer.step(loss, done)
            steps2_done += 1
    finally:
        trainer.votes = 32
        if restore_adamw is not None:
            restore_adamw()
        if ternary_snap is not None:
            restore_ternary(trainer, ternary_snap)

    h_phase2 = held_loss(model, held)
    wall = time.time() - t0
    print(f"[dream-proto {a.control} s{a.seed}] phase 2 done: steps {steps2_done} "
          f"(control={a.control}, source={'buffer' if use_buffer else 'random'}, "
          f"votes={phase2_votes}, freeze={a.freeze}), held {h_phase2:.4f}", flush=True)
    print(f"HELD init {h_init:.4f} -> after_phase1 {h_phase1:.4f} -> after_phase2 {h_phase2:.4f} "
          f"| steps {steps1_done}+{steps2_done} | buffer {len(buffer)} offsets, "
          f"mean buffered loss {buffer_mean:.4f} vs phase-1 mean loss {phase1_mean:.4f}",
          flush=True)

    rec = {"proto": "dream_consolidation", "chassis": "layered_half+rotary",
           "control": a.control, "seed": a.seed,
           "steps1_target": a.steps1, "steps2_target": a.steps2,
           "steps1": steps1_done, "steps2": steps2_done,
           "dream_votes": a.dream_votes, "phase2_votes": phase2_votes,
           "freeze": a.freeze,
           "phase2_source": "buffer" if use_buffer else "random",
           "buffer_k": a.buffer_k, "buffer_size": len(buffer),
           "buffer_mean_loss": round(buffer_mean, 4),
           "phase1_mean_loss": round(phase1_mean, 4),
           "held_init": round(h_init, 4), "held_phase1": round(h_phase1, 4),
           "held_phase2": round(h_phase2, 4),
           "batch": BATCH, "ctx": CTX, "layers": 2, "rotary": True,
           "minutes": a.minutes, "wall_s": round(wall, 1), "truncated": truncated}
    with open(HERE / "proto-runs.jsonl", "a") as f:
        f.write(json.dumps(rec) + "\n")
    print("RESULT " + json.dumps(rec), flush=True)


if __name__ == "__main__":
    main()
