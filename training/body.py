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
- Growth where the body fails. A cell divides: the territory the body reads worst is split in two and a daughter
  cell grows on the worse half (also: on text far from every territory, and on the windows read worst of all).

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
REPORT = ROOT / "training" / "reports" / (f"body_{T.BODY}.json" if T.BODY else "body.json")  # each body keeps its own record
HIVE = ROOT / "training" / "reports" / "hive_of_bodies.json"
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
    return {f.stem: T.load_cell(f).eval() for f in sorted(HOME.glob("cell_*.pt"))}


def _placer():
    """The stem cell as it was when the territories were drawn. Where a passage lies is always asked of this one, so
    the map of territories stays true while the living stem cell goes on learning (placer.pt; a body made before
    this existed is placed by the stem cell itself)."""
    f = HOME / "placer.pt"
    m = T.Tiny()
    m.load_state_dict(torch.load(f if f.exists() else T.HOME / "base.pt"))
    return m.eval()


def _body():
    """Everyone who reads for the body: the stem cell, always, and every cell alive. The stem cell knows a little of
    everything; with it in the body, a passage no cell fits is still read by someone who can."""
    return {"stem": _stem().eval(), **_cells()}


NEAR_M, LOCAL = 2, 0.004  # cells awake beside the stem cell; what a newborn must gain where it lives


class Body:
    """The body as it runs when it is big. Only the stem cell and the map of territories are in memory. A passage is
    read by the stem cell and by the few cells whose territories lie nearest to it; those are taken from disk when
    they wake (the last 32 woken stay in memory) and everyone else sleeps. So reading, judging a newborn and the
    immune check cost the same whether the body has ten cells or ten thousand; only the disk grows."""

    def __init__(self):
        self.stem, self.placer = _stem().eval(), _placer()
        self.terr = torch.load(HOME / "territories.pt")
        self.alive = sorted(int(f.stem.split("_")[1]) for f in HOME.glob("cell_*.pt"))
        self._awake = {}

    def cell(self, k):
        if k not in self._awake:
            if len(self._awake) >= 32:
                self._awake.pop(next(iter(self._awake)))
            self._awake[k] = T.load_cell(HOME / f"cell_{k:02d}.pt").eval()
        return self._awake[k]

    def near(self, data, windows):
        """How near each passage lies to each territory, by its first half (the second half is what is predicted)."""
        return torch.cat([place(self.placer, torch.stack([_window(data, i)[:W // 2] for i in windows[j:j + 64]]))
                          @ self.terr["centre"].T for j in range(0, len(windows), 64)])

    def read(self, data, windows, m=NEAR_M, without=()):
        """(first-half loss [passages, 1 + m], second-half log-probabilities [passages, 1 + m, pieces], who [passages,
        m]): column 0 is the stem cell, the others the m nearest living cells of each passage (without: as if those
        cells were not there). A column nobody fills is asleep: it has no say."""
        alive = [k for k in self.alive if k not in without and k < self.terr["centre"].shape[0]]
        m = min(m, len(alive))
        f0, s0 = _read_all({"stem": self.stem}, data, windows)
        first = torch.full((len(windows), 1 + m), 50.0)
        second = s0.repeat(1, 1 + m, 1).clone()
        first[:, 0] = f0[:, 0]
        if not m:
            return first, second, torch.zeros((len(windows), 0), dtype=torch.long)
        open_ = torch.full((self.terr["centre"].shape[0],), float("-inf"))
        open_[alive] = 0.0
        who = (self.near(data, windows) + open_).topk(m, dim=1).indices
        for k in sorted(set(who.flatten().tolist())):
            rows, slots = (who == k).nonzero(as_tuple=True)
            f, s2 = _read_all({"c": self.cell(k)}, data, [windows[i] for i in rows.tolist()])
            first[rows, 1 + slots], second[rows, 1 + slots] = f[:, 0], s2[:, 0]
        return first, second, who

    def losses(self, data, windows, **kw):
        first, second, _ = self.read(data, windows, **kw)
        return fit_loss(first, second)


def place_new(b, data, log=print):
    """Text harvested since the last turn is given its place: each new window joins its two nearest territories, so
    there is always new ground for cells to divide on."""
    n, done = _windows(data), b.terr.get("placed")
    if done is None:  # a map drawn before this was kept: everything there then was placed
        b.terr["placed"] = n
        _save_map(b.terr)
        return 0
    new = [i for i in range(done, n) if i % HELD]
    if new and b.alive:
        open_ = torch.full((b.terr["centre"].shape[0],), float("-inf"))
        open_[[k for k in b.alive if k < len(open_)]] = 0.0
        for j in range(0, len(new), 2048):
            part = new[j:j + 2048]
            for i, pair in zip(part, (b.near(data, part) + open_).topk(min(2, len(b.alive)), dim=1).indices.tolist()):
                for k in pair:
                    b.terr["owns"].setdefault(k, []).append(i)
        log(f"[body] {len(new)} new windows of harvested text were given their place on the map", flush=True)
    b.terr["placed"] = n
    _save_map(b.terr)
    return len(new)


def _save_map(terr):
    """The map of territories, written whole, with a second copy beside it (what regeneration restores it from)."""
    HOME.mkdir(parents=True, exist_ok=True)
    T.whole(terr, HOME / "territories.pt")
    T.whole(terr, HOME / "territories.bak")


def _loads(path):
    try:
        return torch.load(path, weights_only=False)
    except Exception:  # noqa: BLE001 - a file that cannot be read is a lost file
        return None


def heal(log=print):
    """Regeneration: what this body has lost or had cut off is made again, before anything else in its turn.
    - the stem cell gone or unreadable: it comes back from the copy that drew the map (placer.pt); that copy gone: it
      is taken from the stem cell;
    - the map gone or unreadable: it comes back from its second copy; both gone: the body draws a new map on its next
      step and every cell regrows on it (the old cells belonged to the old map and are put away);
    - a cell unreadable: it is removed, and since the map still knows its territory it is grown again from the stem
      cell on that territory, like a cell that was never born; a cell file simply missing is regrown the same way;
    - a territory pointing at text that is no longer there: those windows are dropped from it.
    Returns what was done, in words; nothing lost, nothing said."""
    import shutil
    did = []
    HOME.mkdir(parents=True, exist_ok=True)
    base, placer = T.HOME / "base.pt", HOME / "placer.pt"
    if _loads(base) is None and _loads(placer) is not None:
        shutil.copyfile(placer, base)
        did.append("the stem cell was lost and came back from the copy that drew the map")
    if _loads(placer) is None and _loads(base) is not None and (HOME / "territories.pt").exists():
        shutil.copyfile(base, placer)
        did.append("the copy of the stem cell that places text was lost and was taken again from the stem cell")
    terr = _loads(HOME / "territories.pt")
    if terr is None and _loads(HOME / "territories.bak") is not None:
        shutil.copyfile(HOME / "territories.bak", HOME / "territories.pt")
        terr = _loads(HOME / "territories.pt")
        did.append("the map of territories was lost and came back from its second copy")
    if terr is None and list(HOME.glob("cell_*.pt")):
        away = HOME.parent / f"body_lost_{time.strftime('%Y%m%d_%H%M')}"
        away.mkdir(parents=True, exist_ok=True)
        for f in HOME.glob("cell_*.pt"):
            f.rename(away / f.name)
        (HOME / "territories.pt").unlink(missing_ok=True)
        did.append("the map and its second copy were lost: a new map is drawn and every cell regrows on it")
    if terr is not None and _loads(base) is not None:
        for f in sorted(HOME.glob("cell_*.pt")):
            try:
                T.load_cell(f)
            except Exception:  # noqa: BLE001
                f.unlink()
                did.append(f"{f.stem} could not be read and is grown again on its territory")
        gone = [int(k) for k in terr["owns"] if not (HOME / f"cell_{int(k):02d}.pt").exists()]
        if gone and not any("grown again" in d for d in did) and _report().get("measured"):
            did.append(f"cells {gone} were missing and are grown again on their territories")
        n = _windows(_data())
        cut = {k: [i for i in v if i < n] for k, v in terr["owns"].items()}
        if any(len(cut[k]) != len(terr["owns"][k]) for k in cut):
            terr["owns"], terr["placed"] = cut, min(terr.get("placed", n), n)
            _save_map(terr)
            did.append("territories pointed at text that is no longer there; those windows were dropped")
    for d in did:
        log(f"[body] regeneration: {d}", flush=True)
    if did:
        _report(regenerated=_report().get("regenerated", []) + [{"when": time.strftime("%Y-%m-%d %H:%M"), "what": did}])
    return did


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
    """Territories are found on a sample of windows; then every training window is given its place (its two nearest
    territories). The first body placed only the sample: its cells had a few thousand windows each and knew them by
    heart."""
    data, stem = _data(), _stem().eval()
    n = _windows(data)
    rnd = random.Random(seed)
    train = [i for i in range(n) if i % HELD]
    pick = rnd.sample(train, min(sample, len(train)))
    t0 = time.time()

    def places(ws):
        return torch.cat([place(stem, torch.stack([_window(data, i)[:-1] for i in ws[j:j + 64]])) for j in range(0, len(ws), 64)])
    z = places(pick)
    g = torch.Generator().manual_seed(seed)
    centre = z[torch.randperm(len(z), generator=g)[:cells]].clone()
    for _ in range(25):  # k-means on directions
        near = (z @ centre.T).argmax(1)
        for k in range(cells):
            if (near == k).any():
                centre[k] = F.normalize(z[near == k].mean(0), dim=0)
    owns, nearest = {k: [] for k in range(cells)}, {}
    for j in range(0, len(train), 2048):
        part = train[j:j + 2048]
        sim = places(part) @ centre.T
        for i, pair in zip(part, sim.topk(min(2, cells), dim=1).indices.tolist()):
            for k in pair:
                owns[k].append(i)
        for k in range(cells):
            b = sim[:, k].argmax().item()
            if k not in nearest or sim[b, k].item() > nearest[k][0]:
                nearest[k] = (sim[b, k].item(), part[b])
    HOME.mkdir(parents=True, exist_ok=True)
    _save_map({"centre": centre, "owns": owns})
    torch.save(stem.state_dict(), HOME / "placer.pt")  # the stem cell that drew this map keeps placing passages on it
    tk = T.tokenizer()
    shown = {k: tk.decode(_window(data, nearest[k][1])[:40].tolist())[:110] for k in owns if k in nearest}
    for k, sh in shown.items():
        log(f"[body] territory {k}: {len(owns[k])} windows, at its centre: {sh!r}", flush=True)
    _report(territories={"cells": cells, "windows_placed": len(train), "sizes": {str(k): len(v) for k, v in owns.items()},
                         "examples": {str(k): sh for k, sh in shown.items()}, "seconds": round(time.time() - t0)})
    return owns


def _read(model, data, windows, minutes, seed, lr=5e-4, batch=32, share_table=True):
    """The model goes on reading these windows (next-piece prediction), for at most so many minutes. A tenth of the
    windows is its own check: it never trains on them. Every 100 steps it is measured on them; the best state is
    kept, and the reading stops when three checks in a row brought nothing. (Without the check a cell read its
    territory until it knew it by heart: loss 0.29 there, 5.3 on text it had not seen.)
    Returns (steps taken, its loss on the check windows at its best, the same before it read anything)."""
    if getattr(model, "bit", False) and share_table:
        for p in (model.tok.weight, model.pos.weight):  # a BitNet cell keeps the stem cell's table of word pieces
            p.requires_grad_(False)
    check = windows[::10][:96] or windows[:8]
    seen = [w for i, w in enumerate(windows) if i % 10] or windows
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=lr, weight_decay=0.01, betas=(0.9, 0.95))
    rnd, t0, steps = random.Random(seed), time.time(), 0

    def checked():
        v = _check_loss(model, data, check)
        model.train()
        return v
    start = checked()
    best, stale = (start, {k: v.clone() for k, v in model.state_dict().items()}), 0
    while time.time() - t0 < minutes * 60 and stale < 3:
        x = torch.stack([_window(data, rnd.choice(seen)) for _ in range(batch)])
        loss = F.cross_entropy(model.next_piece(x[:, :-1]).reshape(-1, T.VOCAB), x[:, 1:].reshape(-1))
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        steps += 1
        if steps % 100 == 0:
            v = checked()
            if v < best[0] - 0.002:
                best, stale = (v, {k: t.clone() for k, t in model.state_dict().items()}), 0
            else:
                stale += 1
    model.load_state_dict(best[1])
    return steps, round(best[0], 3), round(start, 3)


def _check_loss(model, data, check):
    model.eval()
    tot = 0.0
    with torch.no_grad():
        for j in range(0, len(check), 32):
            x = torch.stack([_window(data, i) for i in check[j:j + 32]])
            tot += F.cross_entropy(model.next_piece(x[:, :-1]).reshape(-1, T.VOCAB), x[:, 1:].reshape(-1)).item() * x.shape[0]
    return tot / len(check)


def _flip_read(model, data, windows, minutes, seed, batch=32, share=0.002):
    """A BitNet cell grown the direct way: no ordinary weights underneath. Each round the cell reads four batches and
    asks, for every three-valued weight, which way the loss would fall if it moved one value; the weights that
    would help most (a small share of all) are moved at once. The cell is then measured on windows of its territory
    it never trains on: better, the moves stay; not better, they are undone and the next round moves half as many.
    It ends when the time is up or the moves have become too few to matter. A round costs about six passes; reading
    the ordinary way costs a pass a step and takes a thousand steps.
    Returns (rounds, its loss on the check windows at its best, the same before it changed anything)."""
    layers = [m for m in model.modules() if isinstance(m, T.BitLinear)]
    for p in model.parameters():
        p.requires_grad_(False)
    state = []
    for m in layers:  # each layer as its one number and its three values
        scale = m.weight.abs().mean().clamp(min=1e-5)
        state.append([float(scale), (m.weight / scale).round().clamp(-1, 1)])
        m.weight.requires_grad_(True)

    def install():
        for m, (scale, t) in zip(layers, state):
            m.weight.data = t * (scale / t.abs().mean().clamp(min=1e-5))  # rounding this again gives exactly t times scale
    install()
    check = windows[::10][:96] or windows[:8]
    seen = [w for i, w in enumerate(windows) if i % 10] or windows
    total = sum(t.numel() for _, t in state)
    rnd, t0, rounds = random.Random(seed), time.time(), 0
    start = best = _check_loss(model, data, check)
    while time.time() - t0 < minutes * 60 and share * total >= 20:
        model.train()
        for m in layers:
            m.weight.grad = None
        for _ in range(4):
            x = torch.stack([_window(data, rnd.choice(seen)) for _ in range(batch)])
            F.cross_entropy(model.next_piece(x[:, :-1]).reshape(-1, T.VOCAB), x[:, 1:].reshape(-1)).backward()
        moves, gains = [], []
        for m, (_, t) in zip(layers, state):
            new = (t - m.weight.grad.sign()).clamp(-1, 1)
            moves.append(new)
            gains.append((m.weight.grad.abs() * (new != t)).flatten())
        cut = torch.cat(gains).topk(int(share * total)).values[-1]
        before = [t.clone() for _, t in state]
        for i, (m, new) in enumerate(zip(layers, moves)):
            pick = (m.weight.grad.abs() >= cut) & (new != state[i][1]) & (cut > 0)
            state[i][1] = torch.where(pick, new, state[i][1])
        install()
        v = _check_loss(model, data, check)
        rounds += 1
        if v < best - 1e-4:
            best = v
        else:
            for i, t in enumerate(before):
                state[i][1] = t
            install()
            share /= 2
    return rounds, round(best, 3), round(start, 3)


def differentiate(minutes=10.0, log=print):
    data = _data()
    owns = torch.load(HOME / "territories.pt")["owns"]
    for k, windows in owns.items():
        f = HOME / f"cell_{int(k):02d}.pt"
        if f.exists() or not windows:
            continue
        cell = _stem()
        steps, loss, was = _read(cell, data, windows, minutes, seed=int(k))
        T.save_cell(cell, f)
        log(f"[body] cell {k}: {steps} steps on its {len(windows)} windows; on windows of its territory it never "
            f"trained on, loss {was} -> {loss}", flush=True)
    return len(owns)


def control(log=print):
    """One model with the same total training: the stem cell reads everything for as long as all cells read."""
    data = _data()
    rep = _report()
    minutes = rep.get("minutes_per_cell", 10.0) * len(list(HOME.glob("cell_*.pt")))
    train = [i for i in range(_windows(data)) if i % HELD]
    m = _stem()
    steps, loss, _ = _read(m, data, train, minutes, seed=99)
    torch.save(m.state_dict(), HOME / "control.pt")
    log(f"[body] control: one model, {steps} steps on everything ({minutes:.0f} minutes), loss {loss}", flush=True)


def _half_losses(model, x):
    """Per window: the loss on its first half and on its second half."""
    with torch.no_grad():
        lp = F.log_softmax(model.next_piece(x[:, :-1]), -1).gather(-1, x[:, 1:, None])[..., 0]
    h = lp.shape[1] // 2
    return -lp[:, :h].mean(1), lp[:, h:]  # first-half loss, second-half log-probabilities per piece


FIT = "body, by fit: the stem cell and every cell read, weighed by how each predicted the first half"
NEAR = "body: the stem cell and the 2 nearest cells read, the rest sleep"


def measure(n=300, log=print, part="report"):
    """part: the held-out passages are two sets that never mix. "gate" is where newborns are judged; "report" is only
    ever reported, so the number shown is not one the body was selected on."""
    data, b = _data(), Body()
    held = _held(data, part, n)
    first, second, _ = b.read(data, held)
    res = {"stem cell alone": -second[:, 0].mean().item(), NEAR: fit_loss(first, second).mean().item()}
    if len(b.alive) > NEAR_M:
        res["body: the stem cell and the 4 nearest cells read"] = b.losses(data, held, m=4).mean().item()
    if len(b.alive) <= 12:  # every cell reading: only while the body is small enough for that to be worth the time
        f, s2 = _read_all(_body(), data, held)
        res[FIT] = fit_loss(f, s2).mean().item()
    res = {k: round(v, 4) for k, v in res.items()}
    log(f"[body] {len(b.alive)} cells; {len(held)} passages nobody trained on, loss in predicting the second half (lower is better):", flush=True)
    for k, v in res.items():
        log(f"[body]   {v:.4f}  {k}", flush=True)
    if part == "report":
        hist = _report().get("measured", [])
        hist.append({"when": time.strftime("%Y-%m-%d %H:%M"), "cells": len(b.alive), "passages": len(held), "loss": res})
        _report(measured=hist)
    return res


# ---- the organs: trainers, immunity, memory, scouts --------------------------------------------------------------
TRAINERS = [  # the first ways of growing a cell; more are bred from the ones whose cells are kept (breed)
    {"id": "t1", "start": "nearest", "lr": 5e-4, "span": 1.0, "on": "division"},
    {"id": "t2", "start": "stem", "lr": 5e-4, "span": 1.0, "on": "division"},
    {"id": "t3", "start": "stem", "lr": 5e-4, "span": 1.0, "on": "uncharted"},
    {"id": "t4", "start": "nearest", "lr": 3e-4, "span": 0.5, "on": "division"},
    # for BitNet cells only: no ordinary weights underneath, the three values are moved directly (_flip_read)
    {"id": "t5", "start": "nearest", "lr": 0, "span": 0.5, "on": "division", "how": "flips"},
    {"id": "t6", "start": "nearest", "lr": 0, "span": 0.5, "on": "uncharted", "how": "flips"},
]
KEEP, HARM, IDLE = 0.001, 0.01, 0.0005  # a birth must gain this much; no territory may lose this much; a cell must be worth this


def trainers():
    """The trainers at work. The ones that move three-valued weights directly join once the cells are BitNets."""
    ts = _report().get("trainers") or [dict(t, births=0, kept=0) for t in TRAINERS if "how" not in t]
    if T.is_bit() and not any(t.get("how") == "flips" for t in ts):
        ts += [dict(t, births=0, kept=0) for t in TRAINERS if t.get("how") == "flips"]
    return ts


def pick_trainer(ts, rnd):
    """Which trainer grows the next cell: each is drawn in proportion to how often its cells were kept (a trainer
    with no births yet gets its chance; Thompson sampling)."""
    return max(ts, key=lambda t: rnd.betavariate(t["kept"] + 1, t["births"] - t["kept"] + 1))


def breed(ts, rnd):
    """After every fourth birth: a variant of the trainer with the best record joins, with one thing changed; a
    trainer with three births and no kept cell leaves. At most eight trainers."""
    if sum(t["births"] for t in ts) % 4 or not ts:
        return ts
    new_id = f"t{max(int(t['id'][1:]) for t in ts) + 1}"  # never the number of a trainer that left
    ts = [t for t in ts if not (t["births"] >= 3 and t["kept"] == 0)] or ts[:1]
    best = max(ts, key=lambda t: (t["kept"] + 1) / (t["births"] + 2))
    child = dict(best, births=0, kept=0, id=new_id, parent=best["id"])
    what = rnd.choice(["start", "span", "on"] + ([] if best.get("how") == "flips" else ["lr"]))
    child[what] = {"start": "nearest" if best["start"] == "stem" else "stem", "lr": best["lr"] * rnd.choice([0.5, 2.0]),
                   "span": best["span"] * rnd.choice([0.5, 2.0]), "on": rnd.choice([o for o in ("division", "uncharted", "worst") if o != best["on"]])}[what]
    return (ts + [child])[-8:]


def _held(data, part, n=240):
    held = [i for i in range(_windows(data)) if i % HELD == 0][(0 if part == "gate" else 1)::2]
    return held[::max(1, len(held) // n)][:n]


def _read_all(cells, data, windows):
    """Every cell reads every passage: (first-half loss [passages, cells], second-half log-probabilities [passages,
    cells, pieces])."""
    names, first, second = list(cells), [], []
    for j in range(0, len(windows), 32):
        x = torch.stack([_window(data, i) for i in windows[j:j + 32]])
        f, s2 = zip(*[_half_losses(cells[k], x) for k in names])
        first.append(torch.stack(f, 1))
        second.append(torch.stack(s2, 1))
    return torch.cat(first), torch.cat(second)


def fit_loss(first, second, cols=None):
    """The body's loss on each passage, cells weighed by fit; cols: only these cells (the body without the others)."""
    if cols is not None:
        first, second = first[:, cols], second[:, cols]
    w = torch.softmax(-first * (W // 2), 1)
    return -torch.logsumexp(second + w.log()[:, :, None], 1).mean(1)


def _targets(on, data, cells, stem, terr, sample, rnd):
    """Where the new cell grows. "worst": the fifth of a sample of training windows the body predicts worst.
    "uncharted": the fifth that lies farthest from every territory the body has (the scouts)."""
    if on == "division":
        return _division(data, cells, stem, terr, rnd)
    pick = rnd.sample([i for i in range(_windows(data)) if i % HELD], sample)
    if on == "uncharted":
        far = []
        for j in range(0, len(pick), 64):
            z = place(stem, torch.stack([_window(data, i)[:-1] for i in pick[j:j + 64]]))
            far += (z @ terr["centre"].T).max(1).values.tolist()
        scored = sorted(zip(far, pick))  # least like any territory first
    else:
        scored = sorted(zip(cells.losses(data, pick).tolist(), pick), reverse=True)
    return [i for _, i in scored[:len(scored) // 5]]


def _division(data, cells, stem, terr, rnd, probe=160, most=8000):
    """Where a cell divides. The territory the body reads worst is found (on a sample of its own windows), its
    windows are split in two by where the stem cell places them, and the half the body reads worse is where the
    daughter cell grows. A territory is thousands of windows of real text, so there is something to learn; the
    windows the body reads worst of all are mostly lists and noise, and two cells grown on those learned nothing."""
    alive = set(cells.alive)

    def loss_on(ws):
        return cells.losses(data, ws).mean().item()

    def places(ws):
        return torch.cat([place(stem, torch.stack([_window(data, i)[:-1] for i in ws[j:j + 64]])) for j in range(0, len(ws), 64)])
    owned = {k: v for k, v in terr["owns"].items() if k in alive and len(v) >= 2000}
    if not owned:
        return []
    worst = max(owned, key=lambda k: loss_on(rnd.sample(owned[k], min(probe, len(owned[k])))))
    ws = rnd.sample(owned[worst], min(most, len(owned[worst])))
    z = places(ws)
    centre = F.normalize(torch.stack([z[0], z[(z @ z[0]).argmin()]]), dim=-1)  # two windows far apart to start from
    for _ in range(15):
        side = (z @ centre.T).argmax(1)
        for c in (0, 1):
            if (side == c).any():
                centre[c] = F.normalize(z[side == c].mean(0), dim=0)
    halves = [[w for w, sd in zip(ws, side.tolist()) if sd == c] for c in (0, 1)]
    halves = [h for h in halves if len(h) >= 300]
    if len(halves) < 2:
        return halves[0] if halves else []
    return max(halves, key=lambda h: loss_on(rnd.sample(h, min(probe, len(h)))))


def grow(minutes=10.0, sample=3000, log=print, trainer=None, body=None):
    """A new cell, grown by one trainer's way of doing it. Returns its number."""
    data, cells, stem = _data(), body or Body(), _placer()
    terr = torch.load(HOME / "territories.pt")
    t = trainer or dict(TRAINERS[0])
    k = terr["centre"].shape[0]  # a new number, never one a retired cell had: its row in the map of territories
    rnd = random.Random(k)
    windows = _targets(t["on"], data, cells, stem, terr, sample, rnd)
    if len(windows) < 50:  # nowhere to grow this way just now: the trainer's other way
        windows = _targets("uncharted", data, cells, stem, terr, sample, rnd)
    z = torch.cat([place(stem, torch.stack([_window(data, i)[:-1] for i in windows[j:j + 64]])) for j in range(0, len(windows), 64)])
    centre = F.normalize(z.mean(0), dim=0)
    cell = _stem()
    if t["start"] == "nearest":  # a daughter of the cell whose territory lies nearest
        near = int((terr["centre"] @ centre).argmax())
        f = HOME / f"cell_{near:02d}.pt"
        if f.exists():
            cell = T.load_cell(f)
    if t.get("how") == "flips" and getattr(cell, "bit", False):
        steps, loss, was = _flip_read(cell, data, windows, minutes * t["span"], seed=k)
    else:
        steps, loss, was = _read(cell, data, windows, minutes * t["span"], seed=k, lr=t["lr"] or 5e-4)
    T.save_cell(cell, HOME / f"cell_{k:02d}.pt")
    terr["centre"] = torch.cat([terr["centre"], centre[None]])
    terr["owns"][k] = windows
    _save_map(terr)
    log(f"[body] trainer {t['id']} ({t['start']}, {t['on']}, {t.get('how', 'reading')}, span {t['span']:g}) grew cell {k} on "
        f"{len(windows)} windows: {steps} {'rounds of moves' if t.get('how') == 'flips' else 'steps'}, loss on unseen "
        f"windows there {was} -> {loss}", flush=True)
    return k


def _remove(k):
    (HOME / f"cell_{k:02d}.pt").unlink(missing_ok=True)
    terr = torch.load(HOME / "territories.pt")
    terr["owns"].pop(k, None)
    terr["retired"] = sorted(set(terr.get("retired", [])) | {k})  # its place in the map stays; nobody is there
    _save_map(terr)


def judge(before, after, where, places):
    """Is a new cell kept? (yes/no, why). before/after: the body's loss on each gate passage; where: the territory
    each passage lies in. It must make the body better on the whole (KEEP), and it must not make any territory the
    body already knew worse by more than HARM: the body stays good at what it was."""
    gain = (before.mean() - after.mean()).item()
    if gain <= KEEP:
        return False, f"the body gained {gain:+.4f} (it needs more than {KEEP})"
    for t in places:
        m = where == t
        if m.sum() >= 5 and (after[m].mean() - before[m].mean()).item() > HARM:
            return False, f"territory {t} got worse by {(after[m].mean() - before[m].mean()).item():.4f}"
    return True, f"the body gained {gain:+.4f} and no territory lost more than {HARM}"


def immune(first, second, names, log=print):
    """The body checks its own cells: for each, the gate loss of the body without it. The cell whose absence costs
    least is retired if the body is not worse by IDLE without it (at most one a turn, never the last two, never the
    stem cell)."""
    if sum(n != "stem" for n in names) <= 2:
        return None
    whole = fit_loss(first, second).mean().item()
    worth = {n: fit_loss(first, second, [c for c in range(len(names)) if c != i]).mean().item() - whole
             for i, n in enumerate(names) if n != "stem"}
    idle = min(worth, key=worth.get)
    if worth[idle] < IDLE:
        k = int(idle.split("_")[1])
        _remove(k)
        log(f"[body] immune: cell {k} retired; without it the body's loss changes by {worth[idle]:+.4f}", flush=True)
        return {"cell": k, "worth": round(worth[idle], 5)}
    return None


def stem_reads(data, gate, first, second, minutes=3.0, log=print):
    """The stem cell never stops learning. Each turn it reads everything a little longer, with its table of word
    pieces held still: that table is the one thing every cell leans on, so the cells stay whole while the rest of the
    stem cell changes. Its new self is kept only if the body, with it in the stem cell's place, predicts the gate
    passages better; otherwise the stem cell stays as it was. (New cells start as copies of the stem cell as it is
    then, so what it learns is inherited.)"""
    stem = _stem()
    for p in (stem.tok.weight, stem.pos.weight):
        p.requires_grad_(False)
    train = [i for i in range(_windows(data)) if i % HELD]
    steps, loss, was = _read(stem, data, train, minutes, seed=len(_report().get("stem_reads", [])), lr=3e-4, share_table=False)
    f2, s2 = _read_all({"stem": stem.eval()}, data, gate)
    before = fit_loss(first, second).mean().item()
    first, second = first.clone(), second.clone()
    first[:, 0], second[:, 0] = f2[:, 0], s2[:, 0]  # the stem cell is the body's first member
    after = fit_loss(first, second).mean().item()
    kept = after < before - IDLE
    if kept:
        T.whole(stem.state_dict(), T.HOME / "base.pt")
    out = {"when": time.strftime("%Y-%m-%d %H:%M"), "steps": steps, "gate_before": round(before, 4), "gate_after": round(after, 4), "kept": kept}
    _report(stem_reads=_report().get("stem_reads", []) + [out])
    log(f"[body] the stem cell read {steps} more steps; the body on the gate passages {before:.4f} -> {after:.4f}: "
        f"{'kept' if kept else 'not kept, it stays as it was'}", flush=True)
    return out


def immune_near(b, first, second, who, log=print):
    """The immune check of a big body. Each cell is judged where it was awake: the body's loss on those passages with
    it and as if it slept. The cell that helps least is retired if it does not help by IDLE (at most one a turn;
    never the last two; a cell awake on fewer than five of the passages is not judged this time)."""
    if len(b.alive) <= 2 or not who.numel():
        return None
    worth = {}
    for k in set(who.flatten().tolist()):
        rows, slots = (who == k).nonzero(as_tuple=True)
        if len(rows) < 5:
            continue
        asleep = first[rows].clone()
        asleep[torch.arange(len(rows)), 1 + slots] = 50.0
        worth[k] = (fit_loss(asleep, second[rows]) - fit_loss(first[rows], second[rows])).mean().item()
    if not worth:
        return None
    idle = min(worth, key=worth.get)
    if worth[idle] < IDLE:
        _remove(idle)
        log(f"[body] immune: cell {idle} retired; where it was awake the body's loss changes by {worth[idle]:+.4f} without it", flush=True)
        return {"cell": idle, "worth": round(worth[idle], 5)}
    return None


def judge_local(before, after, woke):
    """Is a newborn kept? It is judged where it lives: on unseen passages nearest to its territory, the body with it
    against the body as if it were not there (it takes another cell's place among those awake, so what it costs is in
    the same number). It must wake on some of them and gain LOCAL there. Elsewhere it sleeps and changes nothing,
    which is how the body stays good at what it was."""
    gain = (before.mean() - after.mean()).item()
    if woke <= 0:
        return False, "it would never be among the cells awake on unseen passages near it"
    if gain <= LOCAL:
        return False, f"where it lives the body gained {gain:+.4f} (it needs more than {LOCAL})"
    return True, f"where it lives the body gained {gain:+.4f}; it wakes on {woke:.0%} of the passages near it"


def turn(minutes=10.0, cells=6, stem_minutes=90.0, log=print, births=3):
    """One turn of the body's life with nobody watching (`python -m team body`; the always-on agent runs it whenever
    the device is idle). Whatever is missing is made first: the harvest, the vocabulary, the stem cell, the first
    cells. After that, every turn:
    - text harvested since the last turn is given its place on the map (place_new);
    - the stem cell reads a little more, and its new self is kept only if the body is better for it (stem_reads);
    - immunity: a cell that does not help where it is awake is retired (immune_near);
    - the body multiplies: `births` times, a trainer chosen by its record grows a cell (a cell divides, or the scouts
      settle text far from every territory), and the newborn is kept only if the body is better for it on unseen
      passages near its territory (judge_local); otherwise it is removed at birth. Older cells are never retrained.
    - the trainers' records are updated, and now and then a variant of the best trainer is bred.
    Everything is read the way a big body reads: the stem cell and the few nearest cells, the rest asleep on disk, so
    a turn costs the same at ten cells and at ten thousand. Returns one line on what the turn did."""
    from team import harvest
    if not harvest.files():
        harvest.main(["--no-trickle"])
    if not (T.HOME / "tokenizer.json").exists():
        T.tokenizer(train=True)
    if not (T.HOME / "base.pt").exists():
        T.pretrain(stem_minutes)
        return "the stem cell read the harvest"
    heal(log)
    if not (HOME / "territories.pt").exists():
        territories(cells, log=log)
    unborn = [k for k in torch.load(HOME / "territories.pt")["owns"] if not (HOME / f"cell_{int(k):02d}.pt").exists()]
    if unborn:  # the first cells, or the ones a cut-off turn left ungrown (a restart once left two territories empty)
        _report(minutes_per_cell=minutes)
        differentiate(minutes, log=log)
        measure(log=log)
        return f"{len(unborn)} cells grew from the stem cell on territories that had none"
    data, b = _data(), Body()
    place_new(b, data, log)
    pool = _held(data, "gate", 10 ** 9)
    spread = pool[::max(1, len(pool) // 200)][:200]
    first, second, who = b.read(data, spread)
    learned = stem_reads(data, spread, first, second, minutes=minutes * 0.3, log=log)
    if learned and learned["kept"]:
        b = Body()
        first, second, who = b.read(data, spread)
    try:  # the kind of text the body reads worst, for the hive's dreams (team/harvest.py, dream)
        loss, home = fit_loss(first, second), who[:, 0]
        by = {t: loss[home == t].mean().item() for t in set(home.tolist()) if (home == t).sum() >= 5}
        worst = max(by, key=by.get)
        hardest = max((i for i in range(len(spread)) if home[i] == worst), key=lambda i: loss[i].item())
        _report(weakest={"territory": worst, "loss": round(by[worst], 4),
                         "text": T.tokenizer().decode(_window(data, spread[hardest])[:W].tolist())})
    except (ValueError, RuntimeError, IndexError):
        pass
    retired = immune_near(b, first, second, who, log)
    if retired:
        _report(retired=_report().get("retired", []) + [dict(retired, when=time.strftime("%Y-%m-%d %H:%M"))])
        b = Body()
    kept_n = 0
    for _ in range(births):
        ts = trainers()
        rnd = random.Random(sum(t["births"] for t in ts))
        t = next(x for x in ts if x["id"] == pick_trainer(ts, rnd)["id"])
        k = grow(minutes, log=log, trainer=t, body=b)
        b = Body()
        near = b.near(data, pool)[:, k]
        local = [pool[i] for i in near.topk(min(60, len(pool))).indices.tolist()]  # the unseen passages nearest to it
        f1, s1, _ = b.read(data, local, without=(k,))
        f2, s2, w2 = b.read(data, local)
        before, after = fit_loss(f1, s1), fit_loss(f2, s2)
        kept, why = judge_local(before, after, (w2 == k).any(1).float().mean().item())
        if not kept:
            _remove(k)
            b = Body()
        kept_n += int(kept)
        t["births"] += 1
        t["kept"] += int(kept)
        born = _report().get("births", [])
        born.append({"cell": k, "when": time.strftime("%Y-%m-%d %H:%M"), "trainer": t["id"], "on": t["on"], "kept": kept, "why": why,
                     "near_before": round(before.mean().item(), 4), "near_after": round(after.mean().item(), 4)})
        _report(births=born, trainers=breed(ts, rnd))
        log(f"[body] trainer {t['id']} grew cell {k} ({t['on']}); {'kept' if kept else 'removed at birth'}: {why}", flush=True)
    measure(log=log)
    line = (f"{births} cells were grown, {kept_n} kept; the body has {len(Body().alive)} cells"
            + (f"; cell {retired['cell']} was retired by the immune check" if retired else ""))
    log("[body] " + line, flush=True)
    return line


# ---- a hive of bodies ------------------------------------------------------------------------------------------------
# His picture (2026-11-11): the whole is not one body. It is made of bodies that never stop growing, many alike or
# overlapping, each with weaknesses the others do not have, each covering what another misses. So the same rule that
# holds between cells holds between bodies: each body has its own stem cell and its own cells and grows on its own
# turns; a passage is read by every body, and a body that fits it gets more say; and a new body is founded on what
# the bodies there are read worst. All bodies share one vocabulary and one harvest, so their readings can be put
# together. A body lives in cells/scratch/bodies/<name>/ (the first one in cells/scratch/), and a process works on
# the body named in HIVE_BODY.
def bodies():
    """The names of the bodies there are, the first one ("") first."""
    try:
        return json.loads((T.SHARED / "bodies.json").read_text())
    except (OSError, ValueError):
        return [""]


def readings(windows):
    """This body reading these passages as one: (how it fitted the first half [n], its log-probability of every piece
    of the second half [n, pieces]). Its members are weighed by fit among themselves; the body's own fit is its best
    member's."""
    first, second, _ = Body().read(_data(), windows)
    w = torch.softmax(-first * (W // 2), 1)
    return first.min(1).values, torch.logsumexp(second + w.log()[:, :, None], 1)


def _ask(name, windows, tag):
    """Another body's readings, from a process of its own (a body's folder is chosen when its process starts)."""
    import os
    import subprocess
    tmp = T.SHARED / "bodies"
    tmp.mkdir(parents=True, exist_ok=True)
    wf, of = tmp / f".{tag}_windows.json", tmp / f".{tag}_{name or 'first'}.pt"
    wf.write_text(json.dumps(windows))
    subprocess.run([sys.executable, str(Path(__file__)), "readings", str(wf), str(of)], cwd=ROOT, check=True,
                   env={**os.environ, "HIVE_BODY": name}, capture_output=True)
    out = torch.load(of)
    of.unlink()
    return out["first"], out["second"]


def together(reads):
    """The bodies reading as one: each body's reading of the second half, weighed by how it fitted the first half.
    reads: [(first [n], second [n, pieces])]. Returns the loss on each passage."""
    first = torch.stack([f for f, _ in reads], 1)
    second = torch.stack([s2 for _, s2 in reads], 1)
    return fit_loss(first, second)


def hive_measure(n=300, log=print):
    """Each body alone and all of them as one, on report passages nobody trained on."""
    data = _data()
    held = _held(data, "report", n)
    names = [b for b in bodies() if (T.SHARED / ("bodies/" + b if b else "") / "body" / "territories.pt").exists()]
    reads = [_ask(b, held, "measure") for b in names]
    res = {"bodies": {b or "first": round(-s2.mean().item(), 4) for b, (_, s2) in zip(names, reads)},
           "as_one": round(together(reads).mean().item(), 4), "passages": len(held), "when": time.strftime("%Y-%m-%d %H:%M")}
    hist = json.loads(HIVE.read_text()) if HIVE.exists() else []
    HIVE.write_text(json.dumps(hist + [res], indent=1))
    log(f"[hive] {len(names)} bodies on {len(held)} passages nobody trained on: each alone {res['bodies']}, as one {res['as_one']}", flush=True)
    return res


def found(name, minutes=40.0, sample=8000, log=print):
    """A new body is founded on what the bodies there are read worst. Its stem cell starts from random three-valued
    weights of its own and reads the harvest with half of every batch taken from the worse-read half of a sample of
    windows; so it is a generalist that leans toward the others' weaknesses. Its cells then grow on its own turns."""
    import os
    import subprocess
    data = _data()
    rnd = random.Random(name)
    pick = rnd.sample([i for i in range(_windows(data)) if i % HELD], sample)
    loss = together([_ask(b, pick, "found") for b in bodies()])
    hard = [i for _, i in sorted(zip(loss.tolist(), pick), reverse=True)[:sample // 2]]
    home = T.SHARED / "bodies" / name
    home.mkdir(parents=True, exist_ok=True)
    (home / ".hard.json").write_text(json.dumps(hard))
    subprocess.run([sys.executable, str(Path(__file__)), "stem", str(home / ".hard.json"), str(minutes)], cwd=ROOT, check=True,
                   env={**os.environ, "HIVE_BODY": name})
    (T.SHARED / "bodies.json").write_text(json.dumps(bodies() + [name]))
    log(f"[hive] body {name!r} founded: its stem cell read for {minutes:.0f} minutes, half of it the {len(hard)} windows "
        f"the other bodies read worst (their loss there {sum(sorted(loss.tolist())[-len(hard):]) / len(hard):.3f}, "
        f"on all {loss.mean().item():.3f})", flush=True)
    return name


def hive_turn(minutes=10.0, births=3, log=print):
    """One turn of the whole hive with nobody watching: every body takes its own turn (it multiplies); a new body is
    founded when the bodies there are have grown enough (one more body for every eight living cells); and the hive
    is measured, each body alone and all as one."""
    import os
    import subprocess
    names = bodies()
    for b in names[1:]:  # regeneration of a whole body: one whose stem cell and its copy are both gone is founded again
        home = T.SHARED / "bodies" / b
        if _loads(home / "base.pt") is None and _loads(home / "body" / "placer.pt") is None:
            log(f"[hive] regeneration: body {b!r} was lost and is founded again", flush=True)
            (T.SHARED / "bodies.json").write_text(json.dumps([x for x in names if x != b]))
            found(b, log=log)
    for b in names:
        subprocess.run([sys.executable, str(Path(__file__)), "turn", "--minutes", str(minutes), "--births", str(births)],
                       cwd=ROOT, env={**os.environ, "HIVE_BODY": b})
    alive = sum(len(list((T.SHARED / ("bodies/" + b if b else "") / "body").glob("cell_*.pt"))) for b in names)
    if len(names) < 1 + alive // 8:
        found(f"b{len(names) + 1}", log=log)
    return hive_measure(log=log)


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
    elif cmd == "readings":  # for another process: this body's readings of the windows in a file
        first, second = readings(json.loads(Path(argv[1]).read_text()))
        torch.save({"first": first, "second": second}, argv[2])
    elif cmd == "stem":  # for found: this body's stem cell, from random three-valued weights
        T.pretrain_direct(float(argv[2]), usual=True, name="base", hard=json.loads(Path(argv[1]).read_text()),
                          seed=sum(map(ord, T.BODY)))
        (T.HOME / "stem.json").write_text(json.dumps({"bit": True, "since": time.strftime("%Y-%m-%d %H:%M"), "founded_on": "the other bodies' worst-read windows"}))
    elif cmd == "found":
        found(argv[1], opt("--minutes", 40.0))
    elif cmd == "hive":
        print(json.dumps(hive_turn(opt("--minutes", 10.0), opt("--births", 3))))
    elif cmd == "hive-measure":
        print(json.dumps(hive_measure()))
    elif cmd == "turn":
        print(turn(opt("--minutes", 10.0), opt("--cells", 6), births=opt("--births", 3)))
    else:
        print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
