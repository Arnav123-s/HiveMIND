# Muse's work — written by Muse, on Muse's side. train.py / train_next.py were read
# read-only and NOT modified; Fable's side was not touched.
# Provenance: this staging trainer imports the lab's own train.py as a module and reuses
# its classes/functions verbatim (Tiny, Block, BitLinear, Direct, Layered, STE,
# held_windows, held_loss, offsets, EASE, constants). Only the run loop, CLI extras and
# the checkpoint save/restore below are new (Compute Department, checkpoint-resume work).

"""Resumable-checkpoint staging copy of the BitNet trainer (Muse's side).

Why: train.py's --ckpt flag is GRADIENT checkpointing (memory-only math trade) — it has
nothing to do with resumable training state. Two lab runs were lost to runtime restarts
on 2026-11-12, and the scale confirmation runs need 7-11h. This file adds true
save/kill/resume on top of the unmodified lab trainer.

Checkpoint contents (one .pt file, written atomically via tmp + os.replace):
  config            arm/seed/shape/flags/batch/steps-target — resume refuses a mismatch
  step              steps completed so far (schedule position: done = step/steps_target)
  elapsed_s         accumulated wall seconds (so a --minutes safety cap / time-based
                    `done` continues approximately across a restart)
  model             model.state_dict(): FP parts (tok/pos embeddings, norms) AND the
                    BitLinear weights (for vote arms these are derived from the ternary
                    states + log_scales and re-derived by install() on restore anyway)
  trainer_kind      "layered" | "direct" | "ste"
  trainer_state     vote arms: ternary states (t, or t1+t2), vote counters (c, or
                    c1+c2, dtype preserved — int8, or int16 with --carry), log_scale
                    parameter VALUES (they live in the optimizer, not the model),
                    votes/mode/carry/cooldown/base_lr/base_wd, trainer.steps
                    ste: lr, warm, steps
  opt               AdamW state_dict (exp_avg / exp_avg_sq / step counts / param-group
                    hyper-params) for the FP + log_scale parameters
  torch_rng         torch.get_rng_state()
  rnd_state         the batch-stream random.Random state (see below)
  ease              train.EASE[0] at save time (STE rounding ease-in position)
  losses, jumps     per-step series so far, so a resumed run reports the FULL series

Batch order: train.py samples batches with offsets(rnd, ...) where rnd is a dedicated
random.Random(seed) advanced once per step. Batch order is therefore deterministic
from (seed, step) ONLY through that Random's internal state — saving rnd.getstate()
in the checkpoint (and restoring it) reproduces the exact post-resume batch stream.
Torch RNG is saved too (init is pre-checkpoint, but SDPA/other torch draws stay covered).

Founding-pattern parity: like Grok's 'founding' checkpoints on Fable's side (weights +
optimiser + elapsed + schedule position), and the checkpoint file is DELETED on
successful completion of the run — a leftover .pt means an unfinished run.

New CLI flags (everything else matches train.py):
  --ckpt-every K    save a checkpoint every K steps (0 = off; default 0)
  --ckpt-path P     checkpoint file (default compute/ckpt-<label>-s<seed>.pt)
  --resume-from P   restore checkpoint P and continue to --steps (config must match)
  --series P        on completion, write {"losses": [...], "jumps": [...]} JSON here
  --record          also append the RESULT record to LAB/runs.jsonl (train.py behaviour;
                    default OFF here so proof/smoke runs do not pollute the lab record)
"""
import argparse, json, os, random, sys, time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB))
import train as T  # the lab trainer, read-only source, reused as a module


# ---------------------------------------------------------------- checkpoint IO

def trainer_state(trainer):
    if isinstance(trainer, T.Layered):
        return {"kind": "layered",
                "t1": [t.clone() for t in trainer.t1], "t2": [t.clone() for t in trainer.t2],
                "c1": [c.clone() for c in trainer.c1], "c2": [c.clone() for c in trainer.c2],
                "log_scale": [p.detach().clone() for p in trainer.log_scale],
                "votes": trainer.votes, "steps": trainer.steps,
                "carry": trainer.carry, "cooldown": trainer.cooldown,
                "base_lr": trainer.base_lr, "base_wd": trainer.base_wd}
    if isinstance(trainer, T.Direct):
        return {"kind": "direct",
                "t": [t.clone() for t in trainer.t],
                "count": [c.clone() for c in trainer.count],
                "log_scale": [p.detach().clone() for p in trainer.log_scale],
                "mode": trainer.mode, "votes": trainer.votes, "steps": trainer.steps}
    if isinstance(trainer, T.STE):
        return {"kind": "ste", "lr": trainer.lr, "warm": trainer.warm, "steps": trainer.steps}
    raise TypeError(f"unknown trainer {type(trainer)}")


def restore_trainer_state(trainer, st):
    kind = trainer_state(trainer)["kind"]
    if kind != st["kind"]:
        raise ValueError(f"trainer kind mismatch: checkpoint {st['kind']} vs run {kind}")
    if kind in ("layered", "direct"):
        for name in (["t1", "t2", "c1", "c2"] if kind == "layered" else ["t", "count"]):
            dst, src = getattr(trainer, name), st[name]
            if len(dst) != len(src):
                raise ValueError(f"{name}: checkpoint has {len(src)} layers, run has {len(dst)}")
            for d, s in zip(dst, src):
                if d.shape != s.shape or d.dtype != s.dtype:
                    raise ValueError(f"{name}: shape/dtype mismatch {tuple(s.shape)}/{s.dtype} "
                                     f"vs {tuple(d.shape)}/{d.dtype}")
                d.copy_(s)
        for p, v in zip(trainer.log_scale, st["log_scale"]):
            p.data.copy_(v)
        trainer.steps = st["steps"]
        if kind == "layered":
            trainer.carry, trainer.cooldown = st["carry"], st["cooldown"]
            trainer.base_lr, trainer.base_wd = st["base_lr"], st["base_wd"]
        trainer.install()  # re-derive BitLinear weights from ternary states + scales
    else:  # ste: latent FP weights live in the model state_dict, already restored
        trainer.lr, trainer.warm, trainer.steps = st["lr"], st["warm"], st["steps"]


def save_checkpoint(path, *, config, model, trainer, opt, rnd, step, elapsed_s, losses, jumps):
    ck = {"config": config,
          "step": step,
          "elapsed_s": elapsed_s,
          "model": model.state_dict(),
          "trainer_kind": trainer_state(trainer)["kind"],
          "trainer_state": trainer_state(trainer),
          "opt": opt.state_dict(),
          "torch_rng": torch.get_rng_state(),
          "rnd_state": rnd.getstate(),
          "ease": T.EASE[0],
          "losses": list(losses), "jumps": list(jumps)}
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    t0 = time.time()
    torch.save(ck, tmp)
    os.replace(tmp, path)  # atomic: a kill mid-save never leaves a torn checkpoint
    return path.stat().st_size, time.time() - t0


def config_of(a, layers):
    return {"arm": a.arm, "seed": a.seed, "dim": a.dim, "layers_n": layers,
            "batch": a.batch, "rope": bool(a.rope), "carry": bool(a.carry),
            "cooldown": bool(a.cooldown), "grad_ckpt": bool(a.ckpt)}


# ---------------------------------------------------------------- run loop

def main():
    ap = argparse.ArgumentParser(description="train.py staging copy with resumable checkpoints (Muse's side)")
    ap.add_argument("--arm", required=True, choices=["plain", "ste", "mag", "layered", "layered_half", "anneal",
                                                     "plain_half", "ste_half"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--minutes", type=float, default=8.0)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--rope", action="store_true")
    ap.add_argument("--carry", action="store_true")
    ap.add_argument("--cooldown", action="store_true")
    ap.add_argument("--dim", type=int, default=T.DIM)
    ap.add_argument("--layers-n", type=int, default=None)
    ap.add_argument("--steps", type=int, default=0)
    ap.add_argument("--tag", default="")
    ap.add_argument("--ckpt", action="store_true",
                    help="gradient checkpointing, exactly as train.py (NOT resumable checkpoints)")
    ap.add_argument("--ckpt-every", type=int, default=0, help="save a resumable checkpoint every K steps")
    ap.add_argument("--ckpt-path", default="", help="resumable checkpoint file path")
    ap.add_argument("--resume-from", default="", help="checkpoint file to restore and continue from")
    ap.add_argument("--held-n", type=int, default=128,
                    help="held windows to score on (subset of the lab's standard 128; proof runs may use fewer under contention)")
    ap.add_argument("--log-every", type=int, default=10, help="print a progress line every K steps")
    ap.add_argument("--series", default="", help="write full per-step loss/jump series JSON here on completion")
    ap.add_argument("--record", action="store_true", help="append RESULT record to LAB/runs.jsonl")
    a = ap.parse_args()
    if (a.carry or a.cooldown) and a.arm not in ("layered", "layered_half"):
        ap.error("--carry/--cooldown are levers on the layered vote trainer only")
    label = a.arm + ("_rope" if a.rope else "") + ("_carry" if a.carry else "") + \
        ("_cooldown" if a.cooldown else "") + (("_" + a.tag) if a.tag else "")
    ckpt_path = Path(a.ckpt_path) if a.ckpt_path else Path(__file__).resolve().parent / f"ckpt-{label}-s{a.seed}.pt"

    data = np.memmap(LAB / "corpus.u16", dtype=np.uint16, mode="r")
    held = T.held_windows(data)[:a.held_n]
    torch.manual_seed(a.seed)
    layers = a.layers_n if a.layers_n else (2 if a.arm in ("layered_half", "plain_half", "ste_half") else 4)
    model = T.Tiny(layers=layers, dim=a.dim, rotary=a.rope)
    model.ckpt = a.ckpt
    if a.arm in ("ste", "ste_half"):
        trainer = T.STE(model)
    elif a.arm in ("layered", "layered_half"):
        trainer = T.Layered(model, carry=a.carry, cooldown=a.cooldown)
    else:
        trainer = T.Direct(model, mode="plain" if a.arm == "plain_half" else a.arm)
    opt = trainer.opt
    cfg = config_of(a, layers)

    rnd, steps, losses, jumps = random.Random(a.seed), 0, [], []
    elapsed_before, resumed_from = 0.0, None
    if a.resume_from:
        ck = torch.load(a.resume_from, map_location="cpu", weights_only=False)
        bad = {k: (ck["config"].get(k), v) for k, v in cfg.items() if ck["config"].get(k) != v}
        if bad:
            ap.error(f"checkpoint config mismatch (ckpt vs run): {bad}")
        model.load_state_dict(ck["model"])
        restore_trainer_state(trainer, ck["trainer_state"])
        opt.load_state_dict(ck["opt"])
        torch.set_rng_state(ck["torch_rng"])
        rnd.setstate(ck["rnd_state"])
        T.EASE[0] = ck["ease"]
        steps, losses, jumps = ck["step"], list(ck["losses"]), list(ck["jumps"])
        if trainer.steps != steps or len(losses) != steps:
            ap.error(f"checkpoint inconsistent: step={steps} trainer.steps={trainer.steps} len(losses)={len(losses)}")
        elapsed_before, resumed_from = ck["elapsed_s"], str(a.resume_from)
        print(f"RESUMED from {a.resume_from} at step {steps} (elapsed {elapsed_before:.1f}s restored)", flush=True)

    n_tern = sum(t.numel() for t in (trainer.t if hasattr(trainer, "t") else trainer.t1)) if a.arm not in ("ste", "ste_half") else \
        sum(p.numel() for m in model.modules() if isinstance(m, T.BitLinear) for p in [m.weight])
    h0 = T.held_loss(model, held) if steps == 0 else None
    t0, budget = time.time(), a.minutes * 60
    save_times = []
    while (time.time() - t0) + elapsed_before < budget:
        if a.steps and steps >= a.steps:
            break
        done = (steps / a.steps) if a.steps else ((time.time() - t0) + elapsed_before) / budget
        T.EASE[0] = min(1.0, done / 0.5) if a.arm in ("ste", "ste_half") else 1.0
        at = T.offsets(rnd, len(data), a.batch)
        x = torch.stack([torch.from_numpy(data[i:i + T.CTX + 1].astype("int64")) for i in at])
        loss = F.cross_entropy(model.next_piece(x[:, :-1]).reshape(-1, T.VOCAB), x[:, 1:].reshape(-1))
        losses.append(loss.item())
        jumps.append(trainer.step(loss, done))
        steps += 1
        if a.ckpt_every and steps % a.ckpt_every == 0 and not (a.steps and steps >= a.steps):
            size, dt = save_checkpoint(ckpt_path, config=cfg, model=model, trainer=trainer, opt=opt,
                                       rnd=rnd, step=steps, elapsed_s=elapsed_before + (time.time() - t0),
                                       losses=losses, jumps=jumps)
            save_times.append(round(dt, 3))
            print(f"CKPT step {steps} path {ckpt_path} bytes {size} save_s {dt:.3f}", flush=True)
        if a.log_every and steps % a.log_every == 0:
            w = losses[-a.log_every:]
            print(f"[{label} s{a.seed}] step {steps}: train {sum(w)/len(w):.3f}, "
                  f"flips {sum(jumps[-a.log_every:])/a.log_every:.3%}", flush=True)
    wall = (time.time() - t0) + elapsed_before
    h1 = T.held_loss(model, held)
    if a.arm in ("layered", "layered_half"):
        states = torch.cat([(t1 + t2).flatten() for t1, t2 in zip(trainer.t1, trainer.t2)])
        hist = {int(v): round(float((states == v).float().mean()), 4) for v in (-2, -1, 0, 1, 2)}
        state_bytes = (4 if a.carry else 2) * n_tern + n_tern // 2
    elif a.arm in ("ste", "ste_half"):
        hist, state_bytes = {}, 12 * n_tern
    else:
        states = torch.cat([t.flatten() for t in trainer.t])
        hist = {int(v): round(float((states == v).float().mean()), 4) for v in (-1, 0, 1)}
        state_bytes = (2 if a.arm == "mag" else 1) * n_tern + n_tern // 4
    rec = {"arm": label, "seed": a.seed, "steps": steps, "wall_s": round(wall, 1),
           "held_init": round(h0, 4) if h0 is not None else None, "held_final": round(h1, 4),
           "train_last100": round(sum(losses[-100:]) / max(1, len(losses[-100:])), 4),
           "ternary_weights": n_tern, "mech_state_bytes": state_bytes,
           "mean_flip_share": round(sum(jumps) / max(1, len(jumps)), 5), "state_hist": hist,
           "corpus_pieces": int(len(data)), "minutes": a.minutes,
           "rope": bool(a.rope), "carry": bool(a.carry), "cooldown": bool(a.cooldown),
           "dim": a.dim, "layers_n": layers, "ckpt": bool(a.ckpt),
           "steps_target": a.steps if a.steps else None,
           "total_params": sum(p.numel() for p in model.parameters()),
           "resumed_from": resumed_from, "ckpt_save_s": save_times, "held_n": a.held_n}
    if a.series:
        Path(a.series).write_text(json.dumps({"label": label, "seed": a.seed, "losses": losses, "jumps": jumps}))
    completed = bool(a.steps) and steps >= a.steps
    if a.record:
        with open(LAB / "runs.jsonl", "a") as f:
            f.write(json.dumps(rec) + "\n")
    print("RESULT " + json.dumps(rec), flush=True)
    if completed and ckpt_path.exists():
        ckpt_path.unlink()  # founding pattern: a finished run retires its checkpoint
        print(f"CKPT retired (deleted) on completion: {ckpt_path}", flush=True)


if __name__ == "__main__":
    main()
