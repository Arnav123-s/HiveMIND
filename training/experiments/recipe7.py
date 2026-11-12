"""What gets a BitNet stem cell further in the same time: recipe6_speed.py taken in whole, and more.

    python training/experiments/recipe7.py OUT.json [--minutes M] [--seeds 0,1,2] [only ...]
    python training/experiments/recipe7.py LONG.json --minutes 40 --seeds 0 --confirm OUT.json
                        only the recipe as built in and everything that helped in OUT.json together, at the length
                        of a founding: does what won in 600 steps still win in 40 minutes?

Every run starts from the same random numbers and reads the same passages in the same order: 600 steps of 32
passages, or, with --minutes, as many steps as fit (then the runs are equal in time, not in steps, and must run
alone on the machine). A run is read afterwards with its weights as they are and with their running mean.

What is tried, one change at a time against the recipe as built in (body.NEW_BODY: rate 3e-3 reached over 200 steps,
the rounding to three values eased in over the first half):
- from recipe6: 16 or 8 passages at a time, rotary positions, relu squared, a plainer norm, output layers that start
  small, normed queries and keys;
- the rate falls in the second half (to a tenth, to a hundredth). Found on 2026-11-11: the third body's stem cell,
  founded at the high rate and never cooled, gained 0.24 from six minutes at a low rate;
- Muon for the three-valued layers: each update is turned into one that moves every direction of the layer equally
  (the momentum of the gradient made orthogonal by five Newton-Schulz steps); the other weights keep AdamW;
- a small term of ordinary weights and low rank beside every three-valued layer (rank 4 or 8): the layer is its
  three values times a number, plus B.A. It costs a fifth more disk for a cell at rank 4.

Chance. The recipe as built in is run from three starts; the spread between them is what a difference must beat.
A change counts as helping when it is better than the mean of the three by more than twice their standard deviation
and by more than 0.01. Everything that helped is then run together, from the same three starts.

Which passages decide. "gate" below: 352 held passages on the gate side (never trained on by anything; they decide
things in the hive already). "the 96": the held passages of the runs of 2026-11-11, for comparison with those
numbers; they are reported, they decide nothing. Report-side passages (the yardstick) are not read here at all.

Results are kept as each run ends; a run already in the file is not made again.
"""
import json
import math
import os
import random
import sys
import time

import torch
import torch.nn as nn
import torch.nn.functional as F

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from training import scratch as T  # noqa: E402

CTX, VOCAB = T.CTX, T.VOCAB
LAM = [1.0]  # how much of the rounding is on


class BL(nn.Linear):
    """A three-valued layer (as scratch.BitLinear). rank > 0: plus a term of ordinary weights of that rank, B.A,
    reading the same 8-bit input."""

    def __init__(s, i, o, rank=0):
        super().__init__(i, o)
        s.rank = rank
        if rank:  # drawn from numbers of its own, so that every other weight starts as in a run without the term
            s.A = nn.Parameter(torch.randn(rank, i, generator=torch.Generator().manual_seed(1000 * i + o)) / math.sqrt(i))
            s.B = nn.Parameter(torch.zeros(o, rank))

    def forward(s, x):
        w = s.weight
        m = w.abs().mean().clamp(min=1e-5)
        w = w + LAM[0] * ((w / m).round().clamp(-1, 1) * m - w).detach()
        top = x.abs().amax(-1, keepdim=True).clamp(min=1e-5)
        x = x + LAM[0] * ((x * 127 / top).round().clamp(-128, 127) * top / 127 - x).detach()
        y = F.linear(x, w, s.bias)
        return y + F.linear(F.linear(x, s.A), s.B) if s.rank else y


class RMS(nn.Module):
    def __init__(s, d):
        super().__init__()
        s.weight = nn.Parameter(torch.ones(d))

    def forward(s, x):
        return x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + 1e-6) * s.weight


def turn(x, cos, sin):  # rotary positions: [b, h, t, d]
    a, b = x[..., ::2], x[..., 1::2]
    return torch.stack([a * cos - b * sin, a * sin + b * cos], -1).flatten(-2)


class Block(nn.Module):
    def __init__(s, dim, heads, rope=False, act="gelu", rms=False, qknorm=False, rank=0):
        super().__init__()
        s.heads, s.rope, s.act, s.qknorm = heads, rope, act, qknorm
        N = RMS if rms else nn.LayerNorm
        s.n1, s.n2 = N(dim), N(dim)
        s.qkv, s.out, s.up, s.down = BL(dim, 3 * dim, rank), BL(dim, dim, rank), BL(dim, 4 * dim, rank), BL(4 * dim, dim, rank)
        if rope:
            f = 1.0 / (10000 ** (torch.arange(0, dim // heads, 2).float() / (dim // heads)))
            ang = torch.arange(CTX).float()[:, None] * f[None]
            s.register_buffer("cos", ang.cos(), persistent=False)
            s.register_buffer("sin", ang.sin(), persistent=False)

    def forward(s, x):
        b, t, d = x.shape
        q, k, v = s.qkv(s.n1(x)).view(b, t, 3, s.heads, d // s.heads).permute(2, 0, 3, 1, 4)
        if s.qknorm:
            q, k = F.normalize(q, dim=-1) * 4.0, F.normalize(k, dim=-1) * 4.0
        if s.rope:
            q, k = turn(q, s.cos[:t], s.sin[:t]), turn(k, s.cos[:t], s.sin[:t])
        a = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        x = x + s.out(a.transpose(1, 2).reshape(b, t, d))
        h = s.up(s.n2(x))
        return x + s.down(F.relu(h).square() if s.act == "relu2" else F.gelu(h))


class Net(nn.Module):
    def __init__(s, dim=192, layers=4, heads=4, small=False, **blk):
        super().__init__()
        s.rope = blk.get("rope", False)
        s.tok, s.pos = nn.Embedding(VOCAB, dim), nn.Embedding(CTX, dim)
        s.blocks = nn.ModuleList(Block(dim, heads, **blk) for _ in range(layers))
        s.norm = (RMS if blk.get("rms") else nn.LayerNorm)(dim)
        s.apply(lambda m: nn.init.normal_(m.weight, std=0.02) if isinstance(m, (nn.Linear, nn.Embedding)) else None)
        if small:  # the layers that write into the stream start small
            for b in s.blocks:
                for m in (b.out, b.down):
                    nn.init.normal_(m.weight, std=0.02 / math.sqrt(2 * layers))

    def next_piece(s, ids):
        x = s.tok(ids) if s.rope else s.tok(ids) + s.pos(torch.arange(ids.shape[1]))
        for b in s.blocks:
            x = b(x)
        return s.norm(x) @ s.tok.weight.T


def orthogonal(g, steps=5):
    """The nearest thing to g that moves every direction equally (Newton-Schulz, the quintic of Muon)."""
    a, b, c = 3.4445, -4.7750, 2.0315
    x = g / (g.norm() + 1e-7)
    tall = g.shape[0] > g.shape[1]
    if tall:
        x = x.T
    for _ in range(steps):
        A = x @ x.T
        x = a * x + (b * A + c * A @ A) @ x
    return x.T if tall else x


class Muon:
    """Momentum of the gradient, made orthogonal, for the weights of the three-valued layers."""

    def __init__(s, params, lr, momentum=0.95):
        s.params, s.lr, s.momentum = list(params), lr, momentum
        s.buf = [torch.zeros_like(p) for p in s.params]

    def step(s, scale=1.0):
        with torch.no_grad():
            for p, buf in zip(s.params, s.buf):
                if p.grad is None:
                    continue
                buf.mul_(s.momentum).add_(p.grad)
                g = orthogonal(p.grad.add(buf, alpha=s.momentum))
                p.add_(g, alpha=-s.lr * scale * max(1.0, p.shape[0] / p.shape[1]) ** 0.5)


class Bench:
    """The text, the held passages and the file of results."""

    def __init__(s, out, minutes=0.0, only=()):
        s.out, s.minutes, s.only = out, minutes, list(only)
        torch.set_num_threads(4)
        s.data = T.corpus(T.tokenizer())
        held = [i * CTX for i in range(56541) if i % 40 == 0]
        s.sets = {"gate": s._stack(held[0::2][::2][:352]), "the 96": s._stack(held[::29][:96])}

    def _stack(s, at):
        return torch.stack([torch.from_numpy(s.data[i:i + CTX + 1].astype("int64")) for i in at])

    def held(s, m):
        m.eval()
        lam, LAM[0] = LAM[0], 1.0
        out = {}
        with torch.no_grad():
            for name, hx in s.sets.items():
                tot = sum(F.cross_entropy(m.next_piece(hx[j:j + 32, :-1]).reshape(-1, VOCAB), hx[j:j + 32, 1:].reshape(-1)).item()
                          * len(hx[j:j + 32]) for j in range(0, len(hx), 32))
                out[name] = round(tot / len(hx), 4)
        m.train()
        LAM[0] = lam
        return out

    def done(s):
        try:
            return json.load(open(s.out))
        except (OSError, ValueError):
            return {}

    def run(s, name, seed=0, lr=3e-3, batch=32, anneal=0.5, wd=0.01, ema=0.99, fall=0.0, floor=0.1, muon=0.0, steps=600, **shape):
        """One run; returns its record. fall: the share of the run, from its end, over which the rate falls (a half
        cosine) to floor times itself. muon: its rate for the three-valued layers (0: AdamW for everything)."""
        if name in s.done():
            return s.done()[name]
        if s.only and not any(o in name for o in s.only):
            return None
        n = steps * 32 // batch
        torch.manual_seed(seed)
        rnd = random.Random(seed)
        m = Net(**shape)
        bit = [b_.weight for blk in m.blocks for b_ in (blk.qkv, blk.out, blk.up, blk.down)] if muon else []
        ids = {id(p) for p in bit}
        opt = torch.optim.AdamW([p for p in m.parameters() if id(p) not in ids], lr=lr, weight_decay=wd, betas=(0.9, 0.95))
        mu = Muon(bit, muon) if muon else None
        mean = {k: v.clone() for k, v in m.state_dict().items()}
        keep = ema ** (batch / 32)
        warm = max(1, 200 * 32 // batch)
        t0, losses, step = time.time(), [], 0
        while True:
            part = (time.time() - t0) / (s.minutes * 60) if s.minutes else step / n  # how far the run is
            if part >= 1.0:
                break
            LAM[0] = min(1.0, part / anneal) if anneal else 1.0
            scale = min(1.0, (step + 1) / warm)
            if fall and part > 1 - fall:
                scale *= floor + (1 - floor) * 0.5 * (1 + math.cos(math.pi * (part - (1 - fall)) / fall))
            for g in opt.param_groups:
                g["lr"] = lr * scale
            at = [rnd.randrange(0, len(s.data) - CTX - 1) for _ in range(batch)]
            x = torch.stack([torch.from_numpy(s.data[i:i + CTX + 1].astype("int64")) for i in at])
            loss = F.cross_entropy(m.next_piece(x[:, :-1]).reshape(-1, VOCAB), x[:, 1:].reshape(-1))
            opt.zero_grad(set_to_none=True)
            for p in bit:
                p.grad = None
            loss.backward()
            nn.utils.clip_grad_norm_(m.parameters(), 1.0)
            opt.step()
            if mu:
                mu.step(scale)
            losses.append(loss.item())
            step += 1
            with torch.no_grad():
                for k, v in m.state_dict().items():
                    mean[k].mul_(keep).add_(v, alpha=1 - keep)
        last = max(1, 100 * 32 // batch)
        res = {"held": s.held(m), "minutes": round((time.time() - t0) / 60, 1), "steps": step, "seed": seed, "batch": batch, "lr": lr,
               "anneal": anneal, "fall": fall, "floor": floor, "muon": muon, **shape,
               "weights": sum(p.numel() for p in m.parameters()), "train_last": round(sum(losses[-last:]) / len(losses[-last:]), 4)}
        m.load_state_dict(mean)
        res["held, running mean of the weights"] = s.held(m)
        allr = s.done()
        allr[name] = res
        json.dump(allr, open(s.out, "w"), indent=1)
        print(name, res, flush=True)
        return res


CHANGES = {  # one change each against the recipe as built in
    "the rate falls in the second half, to a tenth": dict(fall=0.5),
    "the rate falls in the second half, to a hundredth": dict(fall=0.5, floor=0.01),
    "Muon at 0.05 for the three-valued layers": dict(muon=0.05),
    "Muon at 0.1 for the three-valued layers": dict(muon=0.1),
    "a term of rank 4 beside every three-valued layer": dict(rank=4),
    "a term of rank 8 beside every three-valued layer": dict(rank=8),
    "rotary positions": dict(rope=True),
    "relu squared instead of gelu": dict(act="relu2"),
    "a plainer norm (no mean, no shift)": dict(rms=True),
    "the layers that write into the stream start small": dict(small=True),
    "normed queries and keys": dict(qknorm=True),
    "16 at a time, twice the steps": dict(batch=16),
    "16 at a time, rate 2e-3": dict(batch=16, lr=2e-3),
    "8 at a time, four times the steps, rate 2e-3": dict(batch=8, lr=2e-3),
}
BASE = "as built in"


def spread(xs):
    mean = sum(xs) / len(xs)
    return mean, (sum((x - mean) ** 2 for x in xs) / max(1, len(xs) - 1)) ** 0.5


def main(argv):
    minutes, seeds, rest, confirm = 0.0, [0, 1, 2], [], None
    it = iter(argv[1:])
    for a in it:
        if a == "--minutes":
            minutes = float(next(it))
        elif a == "--seeds":
            seeds = [int(x) for x in next(it).split(",")]
        elif a == "--confirm":
            confirm = json.load(open(next(it)))["_verdict"]["helped"]
        else:
            rest.append(a)
    b = Bench(argv[0], minutes, rest)
    base = [b.run(f"{BASE}, start {sd}", seed=sd) for sd in seeds]
    if confirm is not None:
        both = [b.run(f"everything that helped, together, start {sd}: " + json.dumps(confirm, sort_keys=True), seed=sd, **confirm) for sd in seeds]
        allr = b.done()
        allr["_verdict"] = {"minutes": minutes, "helped": confirm, "base": [r["held"]["gate"] for r in base],
                            "together": [r["held"]["gate"] for r in both],
                            "base, running mean": [r["held, running mean of the weights"]["gate"] for r in base],
                            "together, running mean": [r["held, running mean of the weights"]["gate"] for r in both]}
        json.dump(allr, open(b.out, "w"), indent=1)
        print("verdict", allr["_verdict"], flush=True)
        return
    got = {name: (b.run(name, **kw), kw) for name, kw in CHANGES.items()}
    if any(r is None for r in base) or any(r is None for r, _ in got.values()):
        return  # only some runs were asked for
    mean, sd = spread([r["held"]["gate"] for r in base])
    bar = mean - max(0.01, 2 * sd)
    won = {}
    for name, (r, kw) in sorted(got.items(), key=lambda kv: kv[1][0]["held"]["gate"]):
        if r["held"]["gate"] < bar and not any(k in won for k in kw):  # of two settings of one thing, the better one
            won.update(kw)
    verdict = {"base_mean": round(mean, 4), "base_sd": round(sd, 4), "bar": round(bar, 4), "helped": won,
               "each": {name: r["held"]["gate"] for name, (r, _) in got.items()}}
    if won:
        both = [b.run(f"everything that helped, together, start {sd}: " + json.dumps(won, sort_keys=True), seed=sd, **won) for sd in seeds]
        verdict["together_mean"], verdict["together_sd"] = [round(x, 4) for x in spread([r["held"]["gate"] for r in both])]
    allr = b.done()
    allr["_verdict"] = verdict
    json.dump(allr, open(b.out, "w"), indent=1)
    print("verdict", verdict, flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
