#!/usr/bin/env python3
"""Muse's work, Muse's side — re-run proof.py's run12 for ONE arm in a fresh
process, printing every per-step loss for live and staging side by side."""
import importlib.util
import random
import struct
import sys

import numpy as np
import torch
import torch.nn.functional as F

torch.set_num_threads(2)
DATA = np.memmap("corpus.u16", dtype=np.uint16, mode="r")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run12(mod, arm):
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


arm = sys.argv[1]
live = load("train_live", "train.py")
nxt = load("train_next_mod", "train_next.py")
a = run12(live, arm)
b = run12(nxt, arm)
print(f"{arm}: hi live={a[0]!r} next={b[0]!r} equal={struct.pack('<f', a[0]) == struct.pack('<f', b[0])}")
for i, (x, y) in enumerate(zip(a[1], b[1])):
    eq = struct.pack("<f", x) == struct.pack("<f", y)
    if not eq or i < 3:
        print(f"  step {i}: live={x!r} next={y!r} {'==' if eq else 'DIFF'}")
print(f"hf live={a[2]!r} next={b[2]!r} equal={struct.pack('<f', a[2]) == struct.pack('<f', b[2])}")
