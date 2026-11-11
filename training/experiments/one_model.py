"""Many cells against one model given the same total training (the comparison the README says was dropped).

    HIVE_BODY=<name> python training/experiments/one_model.py [out.json] [minutes] [rate]

A body is a stem cell and cells that each read their territory for some minutes. Here a copy of the body's stem
cell reads on alone, everything but the held windows, for as long as all the body's cells may have read together
(minutes for a cell times living cells, unless minutes is given), at the rate a stem cell reads on at
(body.STEM_RATE) unless a rate is given. Every tenth of that time it is read on the same report passages the body is
measured on, so the result is a curve: after how many minutes, if ever, one model of a cell's size reads as well as
the whole body. Two sets of report passages, 300 each: the yardstick (body.YARD: the passages every recorded number
of 2026-11-11 was taken on; they leave out the last seventh of the text) and passages spread over all the text.

What this does and does not say. The one model gets the most training the cells can have had (a cell stops early
when it stops getting better, and how early is not on record), so it is not favoured against. The body has several
times the weights and wakes five models to read a passage where this wakes one. So "the body reads better" means
the cells are a good use of training minutes, and "the one model reads better" means that reading on would have
been the better use of them.
Nothing of the hive is changed: the copy lives in this process only. The result is written after every measurement,
so a run that is cut off leaves what it had. Run it alone on the machine.
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
from training import body as B  # noqa: E402
from training import scratch as T  # noqa: E402


def reads(model, data, sets):
    """The loss in predicting the second half of each passage, as body.measure reports "stem cell alone"."""
    model.eval()
    out = {name: round(-B._read_all({"m": model}, data, held)[1][:, 0].mean().item(), 4) for name, held in sets.items()}
    model.train()
    return out


def main(argv):
    out = Path(argv[0]) if argv else None
    data, b = B._data(), B.Body()
    sets = {"yardstick": B._held(data, "report", 300, upto=B.YARD), "all_text": B._held(data, "report", 300)}
    body = {name: b.read(data, held)[:2] for name, held in sets.items()}
    minutes = float(argv[1]) if len(argv) > 1 else B._report().get("minutes_per_cell", 10.0) * len(b.alive)
    rate = float(argv[2]) if len(argv) > 2 else B.STEM_RATE
    model = B._stem()
    res = {"body": T.BODY or "first", "cells": len(b.alive), "passages": 300, "minutes": minutes, "rate": rate,
           "the_body": {name: round(B.fit_loss(f, s2).mean().item(), 4) for name, (f, s2) in body.items()},
           "its_stem_cell_alone": {name: round(-s2[:, 0].mean().item(), 4) for name, (f, s2) in body.items()},
           "one_model": [{"minutes": 0.0, "steps": 0, "loss": reads(model, data, sets)}], "when": time.strftime("%Y-%m-%d %H:%M")}
    print(json.dumps({k: v for k, v in res.items() if k != "one_model"}), flush=True)
    train = [i for i in range(B._windows(data)) if i % B.HELD]  # never a held window, as a stem cell reads
    opt = torch.optim.AdamW(model.parameters(), lr=rate, weight_decay=0.01, betas=(0.9, 0.95))
    rnd, steps, spent, t0 = random.Random(99), 0, 0.0, time.time()
    marks = [minutes * 60 * (i + 1) / 10 for i in range(10)]
    model.train()
    while marks:
        x = torch.stack([B._window(data, rnd.choice(train)) for _ in range(32)])
        loss = F.cross_entropy(model.next_piece(x[:, :-1]).reshape(-1, T.VOCAB), x[:, 1:].reshape(-1))
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        steps += 1
        if spent + time.time() - t0 >= marks[0]:  # the time spent measuring is not counted as training
            spent += time.time() - t0
            res["one_model"].append({"minutes": round(marks.pop(0) / 60, 1), "steps": steps, "loss": reads(model, data, sets)})
            print(res["one_model"][-1], flush=True)
            if out:
                out.write_text(json.dumps(res, indent=1))
            t0 = time.time()
    return res


if __name__ == "__main__":
    main(sys.argv[1:])
