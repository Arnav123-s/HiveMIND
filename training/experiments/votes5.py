"""Votes and five-level weights against gradient training, with the runs the first comparison left out.

    python training/experiments/votes5.py OUT.json [--minutes 8] [--seeds 0,1] [--only WORD ...]

What was reported to him on 2026-11-11 by another agent (the layered rule here is its own, line for line): BitNets trained directly by votes (scratch.Direct), and "layered" weights, two
three-valued layers stacked so that a weight has five levels (-2..+2). At 8 minutes of wall time a layered net of
half the weights read 2.90, gradient training 3.00, plain votes 3.09, and the layered net at full size 3.10.

What that comparison cannot tell apart: a net of half the weights takes about twice the steps in the same minutes.
So the half-size layered net may have won by its steps and not by its five levels. The runs that tell: plain votes
at half size and gradient training at half size, for the same minutes. And since the shape of the net is a separate
matter from how it is trained, each way is also run with rotary positions (recipe7: 3.6940 against 3.9636).

Every run: the same start for a given seed and shape, `minutes` of wall time on 4 threads, nothing else running,
then read on the 352 gate passages recipe7 reads (held from all training). Half size is 2 blocks of 192 instead of
4 (884,736 three-valued weights, the number reported). Its own record (hivemind_muse: edit-lab/bitnet-lab/
RESULTS-2026-11-11.md) names the same doubt and says no control was run; its runs were 115 to 163 steps long.
One arm is new here: votes whose bar rises over the second half of the run (32 to 96), as the rate of gradient
training falls there (its bar that started low and rose, 8 to 64, lost). Results are kept as each run ends.
"""
import json
import random
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from training import scratch as T  # noqa: E402

CTX, VOCAB = T.CTX, T.VOCAB


class Five(T.BitLinear):
    """A layer whose weights are already what they are (five levels times the layer's number): only what comes in
    is rounded to 8 bits."""

    def forward(self, x):
        top = x.abs().amax(-1, keepdim=True).clamp(min=1e-5)
        return F.linear(x + ((x * 127 / top).round().clamp(-128, 127) * top / 127 - x).detach(), self.weight, self.bias)


class Direct5(T.Direct):
    """Layered weights as the other agent built them (hivemind_muse: edit-lab/bitnet-lab/train.py, class Layered):
    a weight is the sum of two three-valued parts, each with its own counter of votes; both counters get every
    vote; at most one part moves in a step (the first, unless it is already at its end, then the second), and only
    the part that moved starts its counter again. The second part starts at zero."""

    def __init__(self, model, **kw):
        super().__init__(model, **kw)
        self.t2 = [torch.zeros_like(t) for t in self.t]
        self.count2 = [torch.zeros_like(c) for c in self.count]
        for m in self.layers:
            m.__class__ = Five

    def install(self):
        with torch.no_grad():
            for i, (m, ls) in enumerate(zip(self.layers, self.log_scale)):
                s = self.t[i] + self.t2[i] if hasattr(self, "t2") else self.t[i]
                m.weight.copy_(s * (ls.exp() / s.abs().mean().clamp(min=1e-5)))

    def step(self, loss, rate):
        self.opt.zero_grad(set_to_none=True)
        for m in self.layers:
            m.weight.grad = None
        loss.backward()
        torch.nn.utils.clip_grad_norm_([p for g in self.opt.param_groups for p in g["params"] if p.grad is not None], 1.0)
        jumped = total = 0
        v = self.votes
        with torch.no_grad():
            for i, m in enumerate(self.layers):
                g, t1, t2 = m.weight.grad, self.t[i], self.t2[i]
                self.log_scale[i].grad = (g * (t1 + t2)).sum() * self.log_scale[i].exp()
                vote = (-g.sign() * (g.abs() >= g.abs().median())).to(torch.int8)
                c1, c2 = (self.count[i] + vote).clamp(-v, v), (self.count2[i] + vote).clamp(-v, v)
                go1 = (c1.abs() >= v) & ((t1 + c1.sign()).clamp(-1, 1) != t1)
                go2 = (~go1) & (c2.abs() >= v) & ((t2 + c2.sign()).clamp(-1, 1) != t2)
                self.t[i] = torch.where(go1, (t1 + c1.sign()).clamp(-1, 1), t1)
                self.t2[i] = torch.where(go2, (t2 + c2.sign()).clamp(-1, 1), t2)
                self.count[i] = torch.where(go1, torch.zeros_like(c1), c1)
                self.count2[i] = torch.where(go2, torch.zeros_like(c2), c2)
                jumped, total = jumped + int(go1.sum()) + int(go2.sum()), total + t1.numel()
        self.opt.step()
        self.install()
        self.steps += 1
        return jumped / total


ARMS = {  # name: (how it is trained, shape)
    "gradient training, as built in": ("gradient", {}),
    "gradient training, half size": ("gradient", {"layers": 2}),
    "votes": ("votes", {}),
    "votes, half size": ("votes", {"layers": 2}),
    "votes, five levels, half size": ("five", {"layers": 2}),
    "votes, five levels": ("five", {}),
    "gradient training, rotary positions, the rate falls in the second half": ("gradient+", {"rotary": True}),
    "votes, the bar rises in the second half": ("votes^", {}),
    "votes, rotary positions": ("votes", {"rotary": True}),
    "votes, five levels, half size, rotary positions": ("five", {"layers": 2, "rotary": True}),
}


def run(way, shape, seed, minutes, data, gate):
    shape = {"bit": True, "dim": T.DIM, "layers": T.LAYERS, "heads": T.HEADS, "subln": False, "rotary": False, **shape}
    torch.manual_seed(seed)
    model = T.Tiny(shape=shape)
    if way.startswith("gradient"):  # body.NEW_BODY: rate 3e-3 reached over 200 steps, the rounding eased in over half the run
        opt = torch.optim.AdamW(model.parameters(), lr=3e-3, weight_decay=0.01, betas=(0.9, 0.95))
    else:
        trainer = (Direct5 if way == "five" else T.Direct)(model, seed=seed, votes=32)  # scratch.Direct clamps a counter at the bar
    rnd, t0, steps, losses, at_five = random.Random(seed), time.time(), 0, [], None
    while True:
        done = (time.time() - t0) / (minutes * 60)
        if done >= 1:
            break
        x = torch.stack([torch.from_numpy(data[i:i + CTX + 1].astype("int64")) for i in T.offsets(rnd, len(data), 32)])
        T.EASE[0] = min(1.0, done / 0.5) if way.startswith("gradient") else 1.0
        loss = F.cross_entropy(model.next_piece(x[:, :-1]).reshape(-1, VOCAB), x[:, 1:].reshape(-1))
        if way.startswith("gradient"):
            for g in opt.param_groups:
                g["lr"] = 3e-3 * min(1.0, (steps + 1) / 200) * (T.falling(done, 0.5, 0.1) if way == "gradient+" else 1.0)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
        else:
            if way == "votes^":
                trainer.votes = int(round(32 * (1 + 2 * max(0.0, done - 0.5) / 0.5)))
            trainer.step(loss, 0.0)
        losses.append(loss.item())
        steps += 1
    T.EASE[0] = 1.0
    model.eval()
    with torch.no_grad():
        tot = sum(F.cross_entropy(model.next_piece(gate[j:j + 32, :-1]).reshape(-1, VOCAB), gate[j:j + 32, 1:].reshape(-1)).item()
                  * len(gate[j:j + 32]) for j in range(0, len(gate), 32))
    res = {"gate": round(tot / len(gate), 4), "steps": steps, "minutes": minutes, "train_last": round(sum(losses[-100:]) / max(1, len(losses[-100:])), 4),
           "three_valued_weights": sum(m.weight.numel() for m in model.modules() if isinstance(m, T.BitLinear))}
    if way == "five":
        t = torch.cat([(x + y).flatten() for x, y in zip(trainer.t, trainer.t2)])
        res["share_at_the_outer_levels"] = round((t.abs() == 2).float().mean().item(), 4)
    return res


def main(argv):
    out = Path(argv[0])
    opt = lambda k, d: argv[argv.index(k) + 1] if k in argv else d  # noqa: E731
    minutes, seeds = float(opt("--minutes", 8)), [int(s) for s in str(opt("--seeds", "0,1")).split(",")]
    only = argv[argv.index("--only") + 1:] if "--only" in argv else []
    torch.set_num_threads(4)
    data = T.corpus(T.tokenizer())
    held = [i * CTX for i in range(56541) if i % 40 == 0]
    gate = torch.stack([torch.from_numpy(data[i:i + CTX + 1].astype("int64")) for i in held[0::2][::2][:352]])
    for seed in seeds:
        for name, (way, shape) in ARMS.items():
            got = json.loads(out.read_text()) if out.exists() else {}
            key = f"{name}, start {seed}"
            if key in got or (only and not any(o in name for o in only)):
                continue
            got[key] = run(way, shape, seed, minutes, data, gate)
            out.write_text(json.dumps(got, indent=1))
            print(key, got[key], flush=True)
    got = json.loads(out.read_text()) if out.exists() else {}
    table = {}
    for name in ARMS:
        rows = [v for k, v in got.items() if k.rsplit(", start ", 1)[0] == name]
        if rows:
            table[name] = {"gate": round(sum(r["gate"] for r in rows) / len(rows), 4), "each": [r["gate"] for r in rows],
                           "steps": round(sum(r["steps"] for r in rows) / len(rows))}
    print(json.dumps(table, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
