"""His ideas of 2026-11-12, each against the recipe new bodies are founded with, at equal wall time.

    python training/experiments/ideas.py OUT.json [--minutes 20] [--budget BLOCK_STEPS] [--seed 0] [--only WORD ...]

The recipe as built in (body.NEW_BODY): the hive's own BitNet (scratch.Tiny, 192 wide, 4 blocks, rotary positions),
rate 3e-3 reached over 200 steps and falling over the second half, the rounding eased in over the first half.
Every arm changes one thing, starts from the same seed, runs the same minutes on 4 threads with nothing else
running, and is read on the 352 gate passages recipe7 and votes5 read (never trained on).

- "a scale for every row": BitNets differ from ordinary nets in what a layer can say: three values times ONE number
  for the whole layer. Here every output row of a layer has its own number (a few hundred ordinary numbers a layer).
- "predicting what it will think (same net)": the JEPA idea on a BitNet, cheapest form. Besides the next piece, the
  net predicts its own inner state four places ahead (a small ordinary predictor; the target is its own state with
  no gradient). Prediction in the space of meanings, not of pieces.
- "predicting what it will think (running-mean teacher)": the same, with the target read by a running mean of the
  net's weights, as JEPA has it. It costs a second reading of every batch; equal minutes charge it for that.
- "six blocks": bigger, from the start.
- "two blocks", "three blocks": smaller. At 8 minutes a net of half the blocks read better here (votes5) and on
  the other agent's rig (its half-size control, 2026-11-12: 2.8205 against 2.9952), because it takes more steps.
  Does that still hold at the length a new body is founded with, on an equal work budget?
- "grown from four blocks to six at half time": bigger by growing. Two blocks whose output layers are all zeros
  are added (the net reads exactly as before at that moment) and training goes on. If this holds, a body can
  start small and fast and get bigger turn by turn, without starting again.

Equal minutes turned out not to be equal work on this machine: the grown net got 1607 steps in its 20 minutes where
four blocks alone got 1605, though half its steps were through six blocks. So the arms that change the net's size
are also run with --budget: the same number of block-steps for every arm (a step of a net of n blocks costs n).
"""
import copy
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

CTX, VOCAB, AHEAD = T.CTX, T.VOCAB, 4


class RowBit(T.BitLinear):
    """A three-valued layer with a number for every output row instead of one for the layer."""

    def forward(self, x):
        w, ease = self.weight, T.EASE[0]
        scale = w.abs().mean(1, keepdim=True).clamp(min=1e-5)
        w = w + ease * ((w / scale).round().clamp(-1, 1) * scale - w).detach()
        top = x.abs().amax(-1, keepdim=True).clamp(min=1e-5)
        x = x + ease * ((x * 127 / top).round().clamp(-128, 127) * top / 127 - x).detach()
        return F.linear(x, w, self.bias)


ARMS = {
    "as built in": {},
    "a scale for every row": {"rows": True},
    "predicting what it will think (same net)": {"jepa": "self"},
    "predicting what it will think (running-mean teacher)": {"jepa": "teacher"},
    "six blocks": {"layers": 6},
    "two blocks": {"layers": 2},
    "three blocks": {"layers": 3},
    "grown from four blocks to six at half time": {"grow": 2},
}


def new_block(model):
    b = T.Block(True, model.dim, model.blocks[0].heads, model.blocks[0].subln, model.rotary)
    for m in b.modules():
        if isinstance(m, torch.nn.Linear):
            torch.nn.init.normal_(m.weight, std=0.02)
    torch.nn.init.zeros_(b.out.weight)   # what it writes into the stream starts as nothing:
    torch.nn.init.zeros_(b.down.weight)  # the net reads exactly as it did before the block was added
    return b


def run(name, how, seed, minutes, data, gate, budget=0):
    shape = {"bit": True, "dim": T.DIM, "layers": how.get("layers", T.LAYERS), "heads": T.HEADS, "subln": False, "rotary": True}
    torch.manual_seed(seed)
    model = T.Tiny(shape=shape)
    if how.get("rows"):
        for m in model.modules():
            if isinstance(m, T.BitLinear):
                m.__class__ = RowBit
    extra = []
    if how.get("jepa"):
        guess = torch.nn.Sequential(torch.nn.Linear(model.dim, 2 * model.dim), torch.nn.GELU(), torch.nn.Linear(2 * model.dim, model.dim))
        extra = list(guess.parameters())
        teacher = copy.deepcopy(model) if how["jepa"] == "teacher" else None
    make = lambda: torch.optim.AdamW(list(model.parameters()) + extra, lr=3e-3, weight_decay=0.01, betas=(0.9, 0.95))  # noqa: E731
    opt, rnd, t0, steps, losses, grown = make(), random.Random(seed), time.time(), 0, [], False
    spent = 0  # block-steps: one step of a net of n blocks costs n (the teacher's extra reading is not counted)
    while True:
        done = spent / budget if budget else (time.time() - t0) / (minutes * 60)
        if done >= 1:
            break
        if how.get("grow") and not grown and done >= 0.5:
            for _ in range(how["grow"]):
                model.blocks.append(new_block(model))
            opt, grown = make(), True
        x = torch.stack([torch.from_numpy(data[i:i + CTX + 1].astype("int64")) for i in T.offsets(rnd, len(data), 32)])
        T.EASE[0] = min(1.0, done / 0.5)
        h = model.body(x[:, :-1])
        loss = F.cross_entropy((h @ model.tok.weight.T).reshape(-1, VOCAB), x[:, 1:].reshape(-1))
        losses.append(loss.item())
        if how.get("jepa"):
            if teacher is not None:
                with torch.no_grad():
                    target = teacher.body(x[:, :-1])[:, AHEAD:]
            else:
                target = h[:, AHEAD:].detach()
            loss = loss + 0.3 * (1 - F.cosine_similarity(guess(h[:, :-AHEAD]), target, dim=-1)).mean()
        for g in opt.param_groups:
            g["lr"] = 3e-3 * min(1.0, (steps + 1) / 200) * T.falling(done, 0.5, 0.1)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(list(model.parameters()) + extra, 1.0)
        opt.step()
        if how.get("jepa") == "teacher":
            with torch.no_grad():
                for a, b in zip(teacher.parameters(), model.parameters()):
                    a.mul_(0.99).add_(b, alpha=0.01)
        steps += 1
        spent += len(model.blocks)
    T.EASE[0] = 1.0
    model.eval()
    with torch.no_grad():
        tot = sum(F.cross_entropy(model.next_piece(gate[j:j + 32, :-1]).reshape(-1, VOCAB), gate[j:j + 32, 1:].reshape(-1)).item()
                  * len(gate[j:j + 32]) for j in range(0, len(gate), 32))
    return {"gate": round(tot / len(gate), 4), "steps": steps, "minutes": round((time.time() - t0) / 60, 1) if budget else minutes, "train_last": round(sum(losses[-100:]) / max(1, len(losses[-100:])), 4),
            "weights": sum(p.numel() for p in model.parameters())}


def main(argv):
    out = Path(argv[0])
    opt = lambda k, d: argv[argv.index(k) + 1] if k in argv else d  # noqa: E731
    minutes, seed, budget = float(opt("--minutes", 20)), int(opt("--seed", 0)), int(opt("--budget", 0))
    only = argv[argv.index("--only") + 1:] if "--only" in argv else []
    torch.set_num_threads(4)
    data = T.corpus(T.tokenizer())
    held = [i * CTX for i in range(56541) if i % 40 == 0]
    gate = torch.stack([torch.from_numpy(data[i:i + CTX + 1].astype("int64")) for i in held[0::2][::2][:352]])
    for name, how in ARMS.items():
        got = json.loads(out.read_text()) if out.exists() else {}
        key = f"{name}, {budget} block-steps, start {seed}" if budget else f"{name}, {minutes:g} minutes, start {seed}"
        if key in got or (only and not any(o in name for o in only)):
            continue
        got[key] = run(name, how, seed, minutes, data, gate, budget)
        out.write_text(json.dumps(got, indent=1))
        print(key, got[key], flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
