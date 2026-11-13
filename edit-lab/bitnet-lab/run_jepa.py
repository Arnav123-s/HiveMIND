# Muse's work — written by Muse, on Muse's side. Fable's HiveMIND was read read-only; nothing on Fable's side was touched.
# Muse's work — built and run by Muse on Muse's side of the lab.

"""JEPA-in-BitNet experiment (2026-11-12, Arnav's idea, IDEA-LOG 13:01 PT): take LeCun's JEPA
method — the one behind the 109M model beating 70B models on representation alignment via
'good views' (arXiv:2610.39302; research note lecun-feifei-small-specialists-2026-11-10.md) —
and apply it to BitNet training on Muse's side.

QUESTION: at the same chassis, size, corpus and wall-clock budget, does training the ternary
trunk with an embedding-prediction (JEPA) objective produce better representations than
training it with the next-token objective?

CHASSIS: the lab's current best stack — layered vote trainer (Arnav's two-component layered
weights), half size (2 blocks, 884,736 ternary weights), rotary positions. Round 2 (carry /
cooldown) produced no winner, so the chassis is unchanged: layered_half + rope, held token
loss 2.8580 +- 0.0161. Ternary/vote mechanics are IDENTICAL in both arms — only the training
OBJECTIVE differs. This tests the objective, not a new optimizer.

ARMS (3 seeds x 8 min each, same init, same window stream):
  jepa_ctrl_half_rope - control: next-token loss, exactly the lab's layered_half_rope arm,
                        re-run here so the trained trunk can be saved and probed.
  jepa_half_rope      - JEPA: context encoder (the student trunk) sees the window with one
                        contiguous block of 64/256 positions masked out (mask embedding);
                        a small fp predictor (2-layer MLP, AdamW-trained, discarded after
                        training) predicts, from the context representations at the masked
                        positions, the representations of the SAME positions produced by a
                        target encoder on the clean window. Target encoder = EMA (0.99) of
                        the student, stop-gradient — the standard I-JEPA recipe.
                        'Good views' for text, concretely: view 1 = the span with a hole
                        (partial observation), view 2 = the complete span (full observation)
                        — two observations of the same underlying text. Caveat, stated
                        plainly: the two views share tokens, so they are not as independent
                        as the Platonic paper's cross-modal pairs; masked-span prediction is
                        the canonical JEPA adaptation to a single token stream (I-JEPA), and
                        it is what this corpus (one flat stream, no paired renderings) can
                        honestly supply.

YARDSTICK (token loss cannot judge a JEPA model — it was never trained to emit tokens):
  Linear probe, identical protocol for every trunk: freeze the trunk, fit ONE fresh linear
  readout (192 -> 4096, Adam lr 1e-2, 150 steps, batch 32, positions strided by 2, probe
  seed fixed) on non-held windows, then measure next-token cross-entropy of the probe on
  the lab's standard 128 held windows. Also probe the untrained init trunk per seed (floor).
  The probe measures how much next-token information is linearly readable from the frozen
  representations. It does NOT measure generation quality, and it is structurally generous
  to the control (whose training signal is exactly next-token prediction) — a JEPA win
  under this yardstick is therefore a conservative claim; a JEPA loss is a real loss.
  Per-byte: both arms serve identical bytes (same chassis); JEPA's extra TRAINING state
  (EMA copy + predictor) is disclosed in the records, not hidden.

PRE-REGISTERED VERDICT RULE (fixed before any probe number exists):
  JEPA WIN  - JEPA probe CE < control probe CE on >= 2 of 3 seeds AND mean margin > 0.02.
  JEPA LOSS - mirror image. Anything else: TIE / INCONCLUSIVE, with reasons.
  Sanity gates: control held token loss within ~0.10 of the recorded 2.8580 mean (else the
  control mirror is broken and the comparison is void); both trained arms probe clearly
  below the init floor (else training did not happen).

Records: appended to runs.jsonl (arm records carry probe fields); trunk states saved under
jepa-states/; per-seed checkpoints under jepa-runs/ so a crash loses nothing completed.
"""
import argparse, json, math, random, time
from pathlib import Path
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

torch.set_num_threads(2)

from train import LAB, VOCAB, DIM, CTX, Tiny, Layered, offsets, held_windows, held_loss, EASE

MASK_LEN = 64            # one contiguous masked block, 64 of 256 positions (I-JEPA style)
EMA_MOM = 0.99           # short runs (~100-160 steps): EMA must move on training's timescale
PROBE_STEPS, PROBE_SEED, PROBE_LR = 150, 777, 1e-2
STATES = LAB / "jepa-states"
CKPT = LAB / "jepa-runs"
STATES.mkdir(exist_ok=True)
CKPT.mkdir(exist_ok=True)


class JepaModel(nn.Module):
    """Student trunk (Tiny, vote-trained BitLinears) + fp predictor + mask embedding.
    The predictor and mask embedding are training scaffolding: the Layered trainer's AdamW
    group trains them (they are not BitLinear weights); they are discarded at probe time."""
    def __init__(self):
        super().__init__()
        self.trunk = Tiny(layers=2, rotary=True)          # built FIRST: same init stream as control
        self.predictor = nn.Sequential(nn.Linear(DIM, DIM), nn.GELU(), nn.Linear(DIM, DIM))
        self.mask_vec = nn.Parameter(torch.zeros(DIM))
        nn.init.normal_(self.mask_vec, std=0.02)

    def context_body(self, ids, starts):
        """Trunk representations of the masked view: token embeddings at masked positions
        replaced by the learned mask vector, then the trunk's blocks + final norm."""
        t = self.trunk
        x = t.tok(ids)
        pos = torch.arange(ids.shape[1])
        m = (pos[None, :] >= starts[:, None]) & (pos[None, :] < starts[:, None] + MASK_LEN)
        x = torch.where(m.unsqueeze(-1), self.mask_vec, x)
        for blk in t.blocks:
            x = blk(x)
        return t.norm(x), m


def ema_update(target, student, mom=EMA_MOM):
    with torch.no_grad():
        for pt, ps in zip(target.parameters(), student.parameters()):
            pt.mul_(mom).add_(ps.detach(), alpha=1.0 - mom)


def train_control(seed, minutes, data, held):
    torch.manual_seed(seed)
    model = Tiny(layers=2, rotary=True)
    trainer = Layered(model)
    h0 = held_loss(model, held)
    rnd, t0, steps, losses, jumps = random.Random(seed), time.time(), 0, [], []
    budget = minutes * 60
    while time.time() - t0 < budget:
        done = (time.time() - t0) / budget
        EASE[0] = 1.0
        at = offsets(rnd, len(data), 32)
        x = torch.stack([torch.from_numpy(data[i:i + CTX + 1].astype("int64")) for i in at])
        loss = F.cross_entropy(model.next_piece(x[:, :-1]).reshape(-1, VOCAB), x[:, 1:].reshape(-1))
        losses.append(loss.item())
        jumps.append(trainer.step(loss, done))
        steps += 1
        if steps % 50 == 0:
            print(f"[ctrl s{seed}] step {steps}: train {sum(losses[-50:])/50:.3f}", flush=True)
    wall = time.time() - t0
    h1 = held_loss(model, held)
    return model, dict(steps=steps, wall_s=round(wall, 1), held_init=round(h0, 4), held_final=round(h1, 4),
                       train_last100=round(sum(losses[-100:]) / max(1, len(losses[-100:])), 4),
                       mean_flip_share=round(sum(jumps) / max(1, len(jumps)), 5))


def train_jepa(seed, minutes, data, held):
    torch.manual_seed(seed)
    model = JepaModel()
    target = Tiny(layers=2, rotary=True)
    target.load_state_dict(model.trunk.state_dict())
    target.eval()
    for p in target.parameters():
        p.requires_grad_(False)
    trainer = Layered(model)
    rnd, mrnd = random.Random(seed), random.Random(seed * 7 + 13)
    t0, steps, losses, stds = time.time(), 0, [], []
    budget = minutes * 60
    while time.time() - t0 < budget:
        done = (time.time() - t0) / budget
        EASE[0] = 1.0
        at = offsets(rnd, len(data), 32)
        x = torch.stack([torch.from_numpy(data[i:i + CTX + 1].astype("int64")) for i in at])
        ids = x[:, :-1]
        starts = torch.tensor([mrnd.randrange(0, CTX - MASK_LEN) for _ in range(len(ids))])
        h_ctx, m = model.context_body(ids, starts)
        with torch.no_grad():
            h_tgt = target.body(ids)
        pred = model.predictor(h_ctx[m])
        loss = F.smooth_l1_loss(pred, h_tgt[m].detach())
        losses.append(loss.item())
        trainer.step(loss, done)
        ema_update(target, model.trunk)
        steps += 1
        if steps % 20 == 0:
            with torch.no_grad():
                stds.append(round(float(h_tgt.std(dim=0).mean()), 4))
        if steps % 50 == 0:
            print(f"[jepa s{seed}] step {steps}: jepa loss {sum(losses[-50:])/50:.4f}, "
                  f"target rep std {stds[-1] if stds else -1}", flush=True)
    wall = time.time() - t0
    h_tok = held_loss(model.trunk, held)  # curiosity only: NOT the yardstick (see docstring)
    return model.trunk, dict(steps=steps, wall_s=round(wall, 1), jepa_loss_first50=round(sum(losses[:50]) / max(1, len(losses[:50])), 4),
                             jepa_loss_last50=round(sum(losses[-50:]) / max(1, len(losses[-50:])), 4),
                             target_std_last=stds[-1] if stds else None, target_std_first=stds[0] if stds else None,
                             held_token_loss_info_only=round(h_tok, 4))


@torch.no_grad()
def _probe_eval(W, trunk, held):
    trunk.eval()
    tot, n = 0.0, 0
    for i in range(0, len(held), 32):
        x = held[i:i + 32]
        h = trunk.body(x[:, :-1])
        tot += F.cross_entropy((h @ W.weight.T + W.bias).reshape(-1, VOCAB), x[:, 1:].reshape(-1),
                               reduction="sum").item()
        n += x[:, 1:].numel()
    return tot / n


def probe_ce(trunk, data, held):
    """Identical linear-probe protocol for every trunk. Returns held probe CE."""
    for p in trunk.parameters():
        p.requires_grad_(False)
    trunk.eval()
    torch.manual_seed(PROBE_SEED)
    W = nn.Linear(DIM, VOCAB)
    opt = torch.optim.Adam(W.parameters(), lr=PROBE_LR)
    rnd = random.Random(PROBE_SEED)
    for _ in range(PROBE_STEPS):
        at = offsets(rnd, len(data), 32)
        x = torch.stack([torch.from_numpy(data[i:i + CTX + 1].astype("int64")) for i in at])
        with torch.no_grad():
            h = trunk.body(x[:, :-1])[:, ::2]
        loss = F.cross_entropy((h @ W.weight.T + W.bias).reshape(-1, VOCAB), x[:, 1::2].reshape(-1))
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
    return _probe_eval(W, trunk, held)


def state_hist(trunk_trainer_states):
    return None  # state histograms recorded by train.py arms; JEPA records carry flip/loss traces instead


def run_seed(seed, minutes, data, held, record=True):
    ck = CKPT / f"seed{seed}.json"
    if ck.exists():
        print(f"[jepa] seed {seed}: checkpoint exists, skipping", flush=True)
        return json.loads(ck.read_text())
    out = {"seed": seed}
    # control
    ctrl_model, ctrl_stats = train_control(seed, minutes, data, held)
    torch.save(ctrl_model.state_dict(), STATES / f"ctrl-s{seed}.pt")
    # jepa
    jepa_trunk, jepa_stats = train_jepa(seed, minutes, data, held)
    torch.save(jepa_trunk.state_dict(), STATES / f"jepa-s{seed}.pt")
    # init floor
    torch.manual_seed(seed)
    init_trunk = Tiny(layers=2, rotary=True)
    # probes (identical protocol)
    t = time.time(); out["probe_ctrl"] = round(probe_ce(ctrl_model, data, held), 4); out["probe_ctrl_s"] = round(time.time() - t, 1)
    t = time.time(); out["probe_jepa"] = round(probe_ce(jepa_trunk, data, held), 4); out["probe_jepa_s"] = round(time.time() - t, 1)
    t = time.time(); out["probe_init"] = round(probe_ce(init_trunk, data, held), 4); out["probe_init_s"] = round(time.time() - t, 1)
    out["ctrl"] = ctrl_stats
    out["jepa"] = jepa_stats
    ck.write_text(json.dumps(out, indent=1))
    if record:
        n_tern = 884736
        base = {"seed": seed, "steps": None, "corpus_pieces": int(len(data)), "minutes": minutes,
                "ternary_weights": n_tern, "total_params": 1725696, "rope": True}
        rec_c = dict(base, arm="jepa_ctrl_half_rope", steps=ctrl_stats["steps"], wall_s=ctrl_stats["wall_s"],
                     held_init=ctrl_stats["held_init"], held_final=ctrl_stats["held_final"],
                     train_last100=ctrl_stats["train_last100"], mech_state_bytes=2 * n_tern + n_tern // 2,
                     mean_flip_share=ctrl_stats["mean_flip_share"], probe_held_ce=out["probe_ctrl"],
                     probe_init_floor_ce=out["probe_init"])
        ema_bytes = 1725696 * 4
        pred_params = sum(p.numel() for p in JepaModel().predictor.parameters()) + DIM
        rec_j = dict(base, arm="jepa_half_rope", steps=jepa_stats["steps"], wall_s=jepa_stats["wall_s"],
                     held_init=None, held_final=jepa_stats["held_token_loss_info_only"],
                     jepa_loss_first50=jepa_stats["jepa_loss_first50"], jepa_loss_last50=jepa_stats["jepa_loss_last50"],
                     target_std_first=jepa_stats["target_std_first"], target_std_last=jepa_stats["target_std_last"],
                     mech_state_bytes=2 * n_tern + n_tern // 2,
                     extra_training_state_bytes=ema_bytes + pred_params * 12,
                     probe_held_ce=out["probe_jepa"], probe_init_floor_ce=out["probe_init"])
        with open(LAB / "runs.jsonl", "a") as f:
            f.write(json.dumps(rec_c) + "\n")
            f.write(json.dumps(rec_j) + "\n")
    print(f"[jepa] seed {seed} DONE: probe ctrl {out['probe_ctrl']}, jepa {out['probe_jepa']}, "
          f"init floor {out['probe_init']}", flush=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--minutes", type=float, default=8.0)
    ap.add_argument("--smoke", action="store_true", help="1-minute seed-0 run, no records, no checkpoints")
    a = ap.parse_args()
    data = np.memmap(LAB / "corpus.u16", dtype=np.uint16, mode="r")
    held = held_windows(data)
    if a.smoke:
        out = run_seed(0, 1.0, data, held, record=False)
        (CKPT / "seed0.json").unlink(missing_ok=True)
        print("SMOKE " + json.dumps(out), flush=True)
        return
    results = [run_seed(s, a.minutes, data, held) for s in a.seeds]
    print("ALL " + json.dumps(results), flush=True)


if __name__ == "__main__":
    main()
