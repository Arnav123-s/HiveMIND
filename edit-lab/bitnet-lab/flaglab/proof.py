#!/usr/bin/env python3
"""Muse's work, Muse's side — per-step BITWISE identity proofs for the kernel landings.

Part 1: complex-multiplication RoPE (staging default) vs live train.py —
  (a) rotated() on random tensors must be torch.equal;
  (b) full 12-step training runs (layered_half / plain_half / ste_half, rope on)
      must give identical per-step losses and identical held_init/held_final.
Part 2: --vote-kernel fused vs current (staging only) — per-step losses identical
  AND final trainer state tensors torch.equal, across Layered (default, carry,
  comps/counter, leak) and Direct (plain, mag).
Run inside flaglab/ (copies of train.py + train_next.py, corpus symlinked).
"""
import importlib.util
import random
import struct
import sys

import torch
import torch.nn.functional as F

torch.set_num_threads(2)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


live = load("train_live", "train.py")
nxt = load("train_next_mod", "train_next.py")

fails = []


def check(label, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + label + ((" :: " + detail) if detail and not ok else ""))
    if not ok:
        fails.append(label)


def bits(f):
    return struct.pack("<f", float(f)).hex()


# ---- Part 1a: rotated() function-level bitwise identity
g = torch.Generator().manual_seed(7)
for shape in [(2, 4, 37, 48), (3, 2, 256, 72), (2, 4, 16, 16)]:
    x = torch.randn(*shape, generator=g)
    t, pairs = shape[2], shape[3] // 2
    cos = torch.randn(t, pairs, generator=g)
    sin = torch.randn(t, pairs, generator=g)
    r_live = live.rotated(x, cos, sin)
    r_next = nxt.rotated(x, cos, sin)
    check(f"rotated bitwise {shape}", torch.equal(r_live, r_next))


import numpy as np

DATA = np.memmap("corpus.u16", dtype=np.uint16, mode="r")


def run12(mod, arm):
    """Replicates main()'s loop for 12 steps at the tiny config; returns
    (held_init, [per-step losses], held_final)."""
    torch.manual_seed(0)
    data = DATA
    held = mod.held_windows(data)
    model = mod.Tiny(2, 64, rotary=True)
    if arm == "layered_half":
        tr = mod.Layered(model)
    elif arm == "plain_half":
        tr = mod.Direct(model, mode="plain")
    elif arm == "ste_half":
        tr = mod.STE(model, lr=3e-3)
    else:
        raise ValueError(arm)
    rnd = random.Random(0)
    hi = mod.held_loss(model, held)
    losses = []
    for step in range(12):
        done = step / 12
        mod.EASE[0] = min(1.0, done / 0.5) if arm == "ste_half" else 1.0
        x = torch.stack([torch.from_numpy(data[o:o + mod.CTX + 1].astype("int64"))
                         for o in mod.offsets(rnd, len(data), 8)])
        loss = F.cross_entropy(model.next_piece(x[:, :-1]).reshape(-1, mod.VOCAB), x[:, 1:].reshape(-1))
        losses.append(float(loss))
        tr.step(loss, done)
    hf = mod.held_loss(model, held)
    return hi, losses, hf


for arm in ["layered_half", "plain_half", "ste_half"]:
    a = run12(live, arm)
    b = run12(nxt, arm)
    same_steps = all(bits(x) == bits(y) for x, y in zip(a[1], b[1]))
    check(f"rope per-step identity {arm}", same_steps and bits(a[0]) == bits(b[0]) and bits(a[2]) == bits(b[2]),
          f"live hi={a[0]:.6f} hf={a[2]:.6f} vs next hi={b[0]:.6f} hf={b[2]:.6f}; steps equal: {same_steps}")


# ---- Part 2: fused vs current
def run_fused(make_tr):
    torch.manual_seed(0)
    data = DATA
    held = nxt.held_windows(data)
    model = nxt.Tiny(2, 64, rotary=True)
    tr = make_tr(model)
    rnd = random.Random(0)
    losses = []
    for step in range(12):
        done = step / 12
        nxt.EASE[0] = 1.0
        x = torch.stack([torch.from_numpy(data[o:o + nxt.CTX + 1].astype("int64"))
                         for o in nxt.offsets(rnd, len(data), 8)])
        loss = F.cross_entropy(model.next_piece(x[:, :-1]).reshape(-1, nxt.VOCAB), x[:, 1:].reshape(-1))
        losses.append(float(loss))
        tr.step(loss, done)
    state = []
    if hasattr(tr, "ts"):
        for i in range(len(tr.ts)):
            state.extend(tr.ts[i])
            state.extend(tr.cs[i])
            state.append(tr.ls[i])
    else:
        state.extend(tr.t)
        state.extend(tr.count)
    return losses, state, model


CASES = [
    ("layered default", lambda m, fk: nxt.Layered(m, vote_kernel=fk)),
    ("layered carry", lambda m, fk: nxt.Layered(m, carry=True, vote_kernel=fk)),
    ("layered comps3 counter", lambda m, fk: nxt.Layered(m, comps=3, comp_v=[32, 48, 64],
                                                         flip_rule="counter", vote_kernel=fk)),
    ("layered leak", lambda m, fk: nxt.Layered(m, leak=0.99, vote_kernel=fk)),
    ("direct plain", lambda m, fk: nxt.Direct(m, mode="plain", vote_kernel=fk)),
    ("direct mag", lambda m, fk: nxt.Direct(m, mode="mag", vote_kernel=fk)),
]
for label, mk in CASES:
    la, sa, ma = run_fused(lambda m: mk(m, "current"))
    lb, sb, mb = run_fused(lambda m: mk(m, "fused"))
    steps_ok = all(bits(x) == bits(y) for x, y in zip(la, lb))
    state_ok = len(sa) == len(sb) and all(torch.equal(x, y) for x, y in zip(sa, sb))
    params_ok = all(torch.equal(x, y) for x, y in zip(ma.state_dict().values(), mb.state_dict().values()))
    check(f"fused identity {label}", steps_ok and state_ok and params_ok,
          f"steps={steps_ok} state={state_ok} params={params_ok}")

print("RESULT:", "ALL PASS" if not fails else f"{len(fails)} FAILURES: {fails}")
sys.exit(1 if fails else 0)
