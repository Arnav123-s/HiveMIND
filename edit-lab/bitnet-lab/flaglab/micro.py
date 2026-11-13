#!/usr/bin/env python3
"""Muse's work, Muse's side — per-step divergence localiser.
Steps live vs staging trainers on identical batches and reports the FIRST
step/tensor where they differ. Cases: direct plain, ste, layered leak fused."""
import importlib.util
import random
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


live = load("train_live", "train.py")
nxt = load("train_next_mod", "train_next.py")


def batches(mod, n=12):
    rnd = random.Random(0)
    out = []
    for _ in range(n):
        at = mod.offsets(rnd, len(DATA), 8)
        out.append(torch.stack([torch.from_numpy(DATA[i:i + mod.CTX + 1].astype("int64")) for i in at]))
    return out


def cmp_tensors(label, xs, ys):
    for j, (x, y) in enumerate(zip(xs, ys)):
        if not torch.equal(x, y):
            d = (x.float() - y.float()).abs()
            print(f"  FIRST DIFF {label}[{j}] shape={tuple(x.shape)} dtype={x.dtype}/{y.dtype} "
                  f"n_diff={int((x != y).sum())} max={float(d.max()):.6g}")
            idx = (x != y).nonzero()
            if len(idx):
                k = tuple(idx[0].tolist())
                print(f"    e.g. at {k}: live={x[k].item()!r} next={y[k].item()!r}")
            return False
    return True


def case_direct():
    print("CASE direct plain (live vs staging)")
    torch.manual_seed(0); m1 = live.Tiny(2, 64, rotary=True); t1 = live.Direct(m1, mode="plain")
    torch.manual_seed(0); m2 = nxt.Tiny(2, 64, rotary=True); t2 = nxt.Direct(m2, mode="plain")
    bs = batches(live)
    for s in range(12):
        x = bs[s]
        for mod, m, t in ((live, m1, t1), (nxt, m2, t2)):
            mod.EASE[0] = 1.0
            loss = F.cross_entropy(m.next_piece(x[:, :-1]).reshape(-1, mod.VOCAB), x[:, 1:].reshape(-1))
            t.step(loss, s / 12)
        ok = cmp_tensors("t", t1.t, t2.t) and cmp_tensors("count", t1.count, t2.count) \
            and cmp_tensors("log_scale", [p.data for p in t1.log_scale], [p.data for p in t2.log_scale]) \
            and cmp_tensors("weight", [mm.weight.data for mm in t1.layers], [mm.weight.data for mm in t2.layers])
        print(f"  step {s}: {'same' if ok else 'DIVERGED'}")
        if not ok:
            return


def case_ste():
    print("CASE ste (live vs staging)")
    torch.manual_seed(0); m1 = live.Tiny(2, 64, rotary=True); t1 = live.STE(m1)
    torch.manual_seed(0); m2 = nxt.Tiny(2, 64, rotary=True); t2 = nxt.STE(m2)
    bs = batches(live)
    names = [n for n, _ in m1.named_parameters()]
    for s in range(12):
        x = bs[s]
        for mod, m, t in ((live, m1, t1), (nxt, m2, t2)):
            mod.EASE[0] = min(1.0, (s / 12) / 0.5)
            loss = F.cross_entropy(m.next_piece(x[:, :-1]).reshape(-1, mod.VOCAB), x[:, 1:].reshape(-1))
            t.step(loss, s / 12)
        ps1 = [p.data for p in m1.parameters()]
        ps2 = [p.data for p in m2.parameters()]
        ok = True
        for nm, x1, x2 in zip(names, ps1, ps2):
            if not torch.equal(x1, x2):
                d = (x1 - x2).abs()
                print(f"  FIRST DIFF param {nm} n_diff={int((x1 != x2).sum())} max={float(d.max()):.6g}")
                ok = False
                break
        print(f"  step {s}: {'same' if ok else 'DIVERGED'}")
        if not ok:
            return


def case_leak_fused():
    print("CASE layered leak (staging current vs fused)")
    torch.manual_seed(0); m1 = nxt.Tiny(2, 64, rotary=True); t1 = nxt.Layered(m1, leak=0.99)
    torch.manual_seed(0); m2 = nxt.Tiny(2, 64, rotary=True); t2 = nxt.Layered(m2, leak=0.99, vote_kernel="fused")
    bs = batches(nxt)
    for s in range(12):
        x = bs[s]
        for m, t in ((m1, t1), (m2, t2)):
            nxt.EASE[0] = 1.0
            loss = F.cross_entropy(m.next_piece(x[:, :-1]).reshape(-1, nxt.VOCAB), x[:, 1:].reshape(-1))
            t.step(loss, s / 12)
        flat1 = [u for layer in t1.cs for u in layer]
        flat2 = [u for layer in t2.cs for u in layer]
        ok = cmp_tensors("cs", flat1, flat2)
        ts1 = [u for layer in t1.ts for u in layer]
        ts2 = [u for layer in t2.ts for u in layer]
        ok = cmp_tensors("ts", ts1, ts2) and ok
        print(f"  step {s}: {'same' if ok else 'DIVERGED'}")
        if not ok:
            return


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("direct", "all"):
        case_direct()
    if which in ("ste", "all"):
        case_ste()
    if which in ("leak", "all"):
        case_leak_fused()
