"""A body of cells grown from one stem cell, from nothing, on the CPU.

    python training/body.py territories [--cells 6]      split the harvested text into overlapping territories
    python training/body.py differentiate [--minutes 10] one cell per territory: a copy of the stem cell that goes on
                                                         reading only its own territory
    python training/body.py control                      one model, the stem cell reading everything for as long as
                                                         all the cells together read (the same total training)
    python training/body.py measure                      text none of them trained on in this stage: who predicts it
    python training/body.py grow [--minutes 10]          a new cell on the text the whole body predicts worst
    python -m team body                                  one turn with nobody watching: make what is missing, else
                                                         grow one cell and keep it only if the body measures better

His idea (2026-11-10): thousands of cells, each the smallest model that can be made, none doing the same thing, their
specialities overlapping, no cell important alone, the body important together; and more cells grown with more data.
What is built here, each part after how a body does it:
- One origin. The stem cell is the reader trained from random numbers on the harvest (training/scratch.py,
  cells/scratch/base.pt). Every cell starts as a copy of it, so all cells keep the same vocabulary and start from the
  same inner language.
- Territories that overlap. Every window of text is given a place by what the stem cell makes of it (the mean of its
  inner states); nearby windows form a territory; each window belongs to its two nearest territories.
- Each cell knows when it applies. Two ways are measured: "by territory" (the stem cell reads the passage, the cells
  of the nearest territories wake, the rest sleep) and "by fit" (every cell reads the first half of a passage; a cell
  that predicted it well gets more say on the second half).
- Growth where the body fails. grow finds the windows the whole body predicts worst, and a new cell is grown on them.

Measured on windows kept out of every cell's and the control's training in this stage (every 40th window; the stem
cell itself read all of the harvest before, the same for everyone who starts from it): the loss in predicting the
second half of each window, for the stem cell, the control, one cell alone, and the body.
Files: cells/scratch/body/ (territories, cells), training/reports/body.json.
"""
import json
import random
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from training import scratch as T  # noqa: E402

HOME = T.HOME / "body"
REPORT = ROOT / "training" / "reports" / "body.json"
W = T.CTX  # one window of text
HELD = 40  # every 40th window is never trained on here


def _data():
    return T.corpus(T.tokenizer())


def _window(data, i):
    return torch.from_numpy(data[i * W:i * W + W + 1].astype("int64"))


def _windows(data):
    return (len(data) - 1) // W


def _stem():
    m = T.Tiny()
    m.load_state_dict(torch.load(T.HOME / "base.pt"))
    return m


def _cells():
    out = {}
    for f in sorted(HOME.glob("cell_*.pt")):
        m = T.Tiny()
        m.load_state_dict(torch.load(f))
        out[f.stem] = m.eval()
    return out


def _report(**new):
    rec = json.loads(REPORT.read_text()) if REPORT.exists() else {}
    rec.update(new)
    REPORT.write_text(json.dumps(rec, indent=1))
    return rec


def place(model, x):
    """Where a passage lies: the mean of the stem cell's inner states over it."""
    with torch.no_grad():
        return F.normalize(model.body(x).mean(1), dim=-1)


def territories(cells=6, sample=12000, seed=0, log=print):
    data, stem = _data(), _stem().eval()
    n = _windows(data)
    rnd = random.Random(seed)
    train = [i for i in range(n) if i % HELD]
    pick = rnd.sample(train, min(sample, len(train)))
    t0 = time.time()
    z = torch.cat([place(stem, torch.stack([_window(data, i)[:-1] for i in pick[j:j + 64]])) for j in range(0, len(pick), 64)])
    g = torch.Generator().manual_seed(seed)
    centre = z[torch.randperm(len(z), generator=g)[:cells]].clone()
    for _ in range(25):  # k-means on directions
        near = (z @ centre.T).argmax(1)
        for k in range(cells):
            if (near == k).any():
                centre[k] = F.normalize(z[near == k].mean(0), dim=0)
    top2 = (z @ centre.T).topk(2, dim=1).indices
    owns = {k: [pick[i] for i in range(len(pick)) if k in top2[i].tolist()] for k in range(cells)}
    HOME.mkdir(parents=True, exist_ok=True)
    torch.save({"centre": centre, "owns": owns}, HOME / "territories.pt")
    tk = T.tokenizer()
    shown = {k: tk.decode(_window(data, v[0])[:40].tolist())[:110] for k, v in owns.items() if v}
    for k, s in shown.items():
        log(f"[body] territory {k}: {len(owns[k])} windows, e.g. {s!r}", flush=True)
    _report(territories={"cells": cells, "windows_placed": len(pick), "sizes": {str(k): len(v) for k, v in owns.items()},
                         "examples": {str(k): s for k, s in shown.items()}, "seconds": round(time.time() - t0)})
    return owns


def _read(model, data, windows, minutes, seed, lr=5e-4, batch=32):
    """The model goes on reading these windows (next-piece prediction) for so many minutes."""
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01, betas=(0.9, 0.95))
    rnd, t0, steps, losses = random.Random(seed), time.time(), 0, []
    model.train()
    while time.time() - t0 < minutes * 60:
        x = torch.stack([_window(data, rnd.choice(windows)) for _ in range(batch)])
        loss = F.cross_entropy(model.next_piece(x[:, :-1]).reshape(-1, T.VOCAB), x[:, 1:].reshape(-1))
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        steps += 1
        losses.append(loss.item())
    return steps, round(sum(losses[-50:]) / max(1, len(losses[-50:])), 3)


def differentiate(minutes=10.0, log=print):
    data = _data()
    owns = torch.load(HOME / "territories.pt")["owns"]
    for k, windows in owns.items():
        f = HOME / f"cell_{int(k):02d}.pt"
        if f.exists() or not windows:
            continue
        cell = _stem()
        steps, loss = _read(cell, data, windows, minutes, seed=int(k))
        torch.save(cell.state_dict(), f)
        log(f"[body] cell {k}: {steps} steps on its {len(windows)} windows, loss there {loss}", flush=True)
    return len(owns)


def control(log=print):
    """One model with the same total training: the stem cell reads everything for as long as all cells read."""
    data = _data()
    rep = _report()
    minutes = rep.get("minutes_per_cell", 10.0) * len(list(HOME.glob("cell_*.pt")))
    train = [i for i in range(_windows(data)) if i % HELD]
    m = _stem()
    steps, loss = _read(m, data, train, minutes, seed=99)
    torch.save(m.state_dict(), HOME / "control.pt")
    log(f"[body] control: one model, {steps} steps on everything ({minutes:.0f} minutes), loss {loss}", flush=True)


def _half_losses(model, x):
    """Per window: the loss on its first half and on its second half."""
    with torch.no_grad():
        lp = F.log_softmax(model.next_piece(x[:, :-1]), -1).gather(-1, x[:, 1:, None])[..., 0]
    h = lp.shape[1] // 2
    return -lp[:, :h].mean(1), lp[:, h:]  # first-half loss, second-half log-probabilities per piece


FIT = "body, by fit: every cell reads, weighed by how it predicted the first half"


def measure(n=300, log=print, part="report"):
    """part: the held-out passages are two sets that never mix. "gate" decides whether a new cell is kept; "report"
    is only ever reported, so the number shown is not one the body was selected on."""
    data, stem, cells = _data(), _stem().eval(), _cells()
    terr = torch.load(HOME / "territories.pt")
    held = [i for i in range(_windows(data)) if i % HELD == 0][(0 if part == "gate" else 1)::2]
    held = held[::max(1, len(held) // n)][:n]
    names = list(cells)
    ctrl = None
    if (HOME / "control.pt").exists():
        ctrl = T.Tiny()
        ctrl.load_state_dict(torch.load(HOME / "control.pt"))
        ctrl.eval()
    tot = {"stem cell alone": 0.0, "one model, same total training": 0.0, "the best single cell for each passage (hindsight)": 0.0,
           "body, by territory: 1 cell awake": 0.0, "body, by territory: 2 cells awake": 0.0,
           "body, by fit: every cell reads, weighed by how it predicted the first half": 0.0,
           "body, every cell with the same say": 0.0}
    per_cell, count, h = {k: 0.0 for k in names}, 0, W // 2
    for j in range(0, len(held), 32):
        x = torch.stack([_window(data, i) for i in held[j:j + 32]])
        b = x.shape[0]
        _, s = _half_losses(stem, x)
        tot["stem cell alone"] += -s.mean(1).sum().item()
        if ctrl is not None:
            tot["one model, same total training"] += -_half_losses(ctrl, x)[1].mean(1).sum().item()
        first, second = zip(*[_half_losses(cells[k], x) for k in names])
        first, second = torch.stack(first, 1), torch.stack(second, 1)  # [b, cells], [b, cells, pieces]
        for c, k in enumerate(names):
            per_cell[k] += -second[:, c].mean(1).sum().item()
        tot["the best single cell for each passage (hindsight)"] += (-second.mean(2)).min(1).values.sum().item()
        # by territory: where the stem cell places the first half decides who wakes
        with torch.no_grad():
            near = (place(stem, x[:, :h]) @ terr["centre"].T)
        order = near.argsort(1, descending=True)
        idx = {int(k.split("_")[1]): c for c, k in enumerate(names)}
        for awake, key in ((1, "body, by territory: 1 cell awake"), (2, "body, by territory: 2 cells awake")):
            for r in range(b):
                who = [idx[t] for t in order[r].tolist() if t in idx][:awake]
                w = torch.softmax(near[r, [t for t in order[r].tolist() if t in idx][:awake]] * 20, 0)
                mix = torch.logsumexp(second[r, who] + w.log()[:, None], 0)
                tot[key] += -mix.mean().item()
        w = torch.softmax(-first * h, 1)  # a cell's say: how likely it found the first half (as a whole)
        tot["body, by fit: every cell reads, weighed by how it predicted the first half"] += \
            (-torch.logsumexp(second + w.log()[:, :, None], 1).mean(1)).sum().item()
        tot["body, every cell with the same say"] += (-(torch.logsumexp(second, 1) - torch.log(torch.tensor(float(len(names))))).mean(1)).sum().item()
        count += b
    res = {k: round(v / count, 4) for k, v in tot.items() if v}
    res_cells = {k: round(v / count, 4) for k, v in per_cell.items()}
    log(f"[body] {count} passages no cell trained on, loss in predicting the second half (lower is better):", flush=True)
    for k, v in res.items():
        log(f"[body]   {v:.4f}  {k}", flush=True)
    log(f"[body]   each cell alone: {res_cells}", flush=True)
    if part == "report":
        hist = _report().get("measured", [])
        hist.append({"when": time.strftime("%Y-%m-%d %H:%M"), "cells": len(names), "passages": count, "loss": res, "cell_alone": res_cells})
        _report(measured=hist)
    return res


def grow(minutes=10.0, sample=4000, log=print):
    """A new cell on what the whole body predicts worst (by fit): the worst fifth of a sample of training windows."""
    data, cells = _data(), _cells()
    names = list(cells)
    rnd = random.Random(len(names))
    pick = rnd.sample([i for i in range(_windows(data)) if i % HELD], sample)
    h, scored = W // 2, []
    for j in range(0, len(pick), 32):
        x = torch.stack([_window(data, i) for i in pick[j:j + 32]])
        first, second = zip(*[_half_losses(cells[k], x) for k in names])
        first, second = torch.stack(first, 1), torch.stack(second, 1)
        w = torch.softmax(-first * h, 1)
        loss = -torch.logsumexp(second + w.log()[:, :, None], 1).mean(1)
        scored += list(zip(loss.tolist(), pick[j:j + 32]))
    scored.sort(reverse=True)
    worst = [i for _, i in scored[:len(scored) // 5]]
    k = max(int(n.split("_")[1]) for n in names) + 1
    cell = _stem()
    steps, loss = _read(cell, data, worst, minutes, seed=k)
    torch.save(cell.state_dict(), HOME / f"cell_{k:02d}.pt")
    terr = torch.load(HOME / "territories.pt")
    stem = _stem().eval()
    z = torch.cat([place(stem, torch.stack([_window(data, i)[:-1] for i in worst[j:j + 64]])) for j in range(0, len(worst), 64)])
    terr["centre"] = torch.cat([terr["centre"], F.normalize(z.mean(0), dim=0)[None]])
    terr["owns"][k] = worst
    torch.save(terr, HOME / "territories.pt")
    log(f"[body] grown: cell {k} on the {len(worst)} windows the body predicted worst (their loss {scored[0][0]:.2f} to "
        f"{scored[len(worst) - 1][0]:.2f}, the body's mean {sum(s for s, _ in scored) / len(scored):.2f}); {steps} steps, loss there {loss}",
        flush=True)
    return k


def turn(minutes=10.0, cells=6, stem_minutes=90.0, log=print):
    """One turn of the body's life with nobody watching (`python -m team body`; the always-on agent runs it when
    the device is idle). Whatever is missing is made first: the harvest, the vocabulary, the stem cell, the first
    cells. After that every turn grows one cell on what the body predicts worst, and the cell is kept only if the
    body then predicts the gate passages better than before; otherwise it is removed at birth. Nothing is kept that
    did not measure better on text it never trained on. Returns one line saying what the turn did."""
    from team import harvest
    if not harvest.files():
        harvest.main(["--no-trickle"])
    if not (T.HOME / "tokenizer.json").exists():
        T.tokenizer(train=True)
    if not (T.HOME / "base.pt").exists():
        T.pretrain(stem_minutes)
        return "the stem cell read the harvest"
    if not (HOME / "territories.pt").exists():
        territories(cells, log=log)
    if len(list(HOME.glob("cell_*.pt"))) < cells:
        _report(minutes_per_cell=minutes)
        differentiate(minutes, log=log)
        measure(log=log)
        return f"the first {cells} cells grew from the stem cell"
    before = measure(log=lambda *a, **k: None, part="gate")[FIT]
    k = grow(minutes, log=log)
    after = measure(log=lambda *a, **k: None, part="gate")[FIT]
    born = _report().get("births", [])
    kept = after < before - 0.001
    if not kept:  # removed at birth: the body is as it was
        (HOME / f"cell_{k:02d}.pt").unlink()
        terr = torch.load(HOME / "territories.pt")
        terr["centre"], _ = terr["centre"][:-1], terr["owns"].pop(k, None)
        torch.save(terr, HOME / "territories.pt")
    born.append({"cell": k, "when": time.strftime("%Y-%m-%d %H:%M"), "gate_before": before, "gate_after": after, "kept": kept})
    _report(births=born)
    measure(log=log)
    line = (f"cell {k} was grown on what the body predicted worst and {'kept' if kept else 'removed at birth'}: "
            f"the body's loss on the gate passages went from {before:.4f} to {after:.4f}")
    log("[body] " + line, flush=True)
    return line


def main(argv):
    opt = lambda k, d: type(d)(argv[argv.index(k) + 1]) if k in argv else d  # noqa: E731
    cmd = argv[0] if argv else ""
    if cmd == "territories":
        territories(opt("--cells", 6))
    elif cmd == "differentiate":
        _report(minutes_per_cell=opt("--minutes", 10.0))
        differentiate(opt("--minutes", 10.0))
    elif cmd == "control":
        control()
    elif cmd == "measure":
        measure()
    elif cmd == "grow":
        grow(opt("--minutes", 10.0))
    elif cmd == "turn":
        print(turn(opt("--minutes", 10.0), opt("--cells", 6)))
    else:
        print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
