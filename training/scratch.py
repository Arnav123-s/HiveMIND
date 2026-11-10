"""Cells trained from nothing, on the CPU: no outside weights at all.

    python training/scratch.py tokenizer                 a vocabulary of 4096 word pieces, learned from the harvest
    python training/scratch.py pretrain [--minutes 60]   a tiny language model reads the harvest (it learns to predict
                                                         the next piece); a later run goes on from where it stopped
    python training/scratch.py fit <skill> [--plain]     every weight is trained on one cell job (--plain: without the
                                                         reading first: random weights straight to the job)
    python training/scratch.py all [--plain] [--rows N]  every cell job that is a choice between labels; a table
                                                         against the cells the hive has today (--rows: train on N
                                                         rows from the job's own generator, not a few hundred)

    python training/scratch.py together [--consult]      ONE model for every cell job: a shared trunk and a small
                                                         head per job, trained on all jobs at once (--consult: each
                                                         head also sees what the other heads say about the input)

Today's cells are SmolLM2-135M (someone else's pretrained weights) with a small edit. This is the other way to make
one: a model of about 2.6 million weights that starts from random numbers. What it knows about words it gets from the
text the hive harvested itself (team/harvest.py); what it knows about its job it gets from the same training rows as
today's cell (training/cells.py, data). It is scored on the same test split: other words, frames and sites than it
was trained on. Chosen on the dev split; the test split is only reported.

Files: cells/scratch/tokenizer.json, cells/scratch/base.pt (the reader), cells/scratch/<skill>.pt,
cells/scratch/record.json; training/reports/scratch_cells.json.
"""
import json
import math
import random
import sys
import time
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
HOME = ROOT / "cells" / "scratch"
VOCAB, DIM, LAYERS, HEADS, CTX = 4096, 192, 4, 4, 256
PAD, BOS = 0, 1


class Block(nn.Module):
    def __init__(self):
        super().__init__()
        self.n1, self.n2 = nn.LayerNorm(DIM), nn.LayerNorm(DIM)
        self.qkv, self.out = nn.Linear(DIM, 3 * DIM), nn.Linear(DIM, DIM)
        self.up, self.down = nn.Linear(DIM, 4 * DIM), nn.Linear(4 * DIM, DIM)

    def forward(self, x, causal):
        b, t, d = x.shape
        q, k, v = self.qkv(self.n1(x)).view(b, t, 3, HEADS, d // HEADS).permute(2, 0, 3, 1, 4)
        a = F.scaled_dot_product_attention(q, k, v, is_causal=causal)
        x = x + self.out(a.transpose(1, 2).reshape(b, t, d))
        return x + self.down(F.gelu(self.up(self.n2(x))))


class Tiny(nn.Module):
    """A small transformer. As a reader it predicts the next piece; as a cell it reads the whole input and its last
    position chooses a label."""

    def __init__(self, labels=0):
        super().__init__()
        self.tok, self.pos = nn.Embedding(VOCAB, DIM), nn.Embedding(CTX, DIM)
        self.blocks = nn.ModuleList(Block() for _ in range(LAYERS))
        self.norm = nn.LayerNorm(DIM)
        self.head = nn.Linear(DIM, labels) if labels else None
        self.apply(lambda m: nn.init.normal_(m.weight, std=0.02) if isinstance(m, (nn.Linear, nn.Embedding)) else None)

    def body(self, ids, causal=True):
        x = self.tok(ids) + self.pos(torch.arange(ids.shape[1]))
        for blk in self.blocks:
            x = blk(x, causal)
        return self.norm(x)

    def next_piece(self, ids):
        return self.body(ids) @ self.tok.weight.T  # the output layer is the input table: fewer weights

    def label(self, ids, last):
        h = self.body(ids)
        return self.head(h[torch.arange(ids.shape[0]), last])


def tokenizer(train=False):
    from tokenizers import Tokenizer, decoders, models, pre_tokenizers, trainers
    f = HOME / "tokenizer.json"
    if f.exists() and not train:
        return Tokenizer.from_file(str(f))
    from team import harvest
    files = [str(p) for p in harvest.files()]
    if not files:
        raise SystemExit("nothing harvested yet: python -m team harvest")
    tk = Tokenizer(models.BPE(unk_token=None))
    tk.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=True)
    tk.decoder = decoders.ByteLevel()
    tk.train(files, trainers.BpeTrainer(vocab_size=VOCAB, special_tokens=["<pad>", "<bos>"],
                                        initial_alphabet=pre_tokenizers.ByteLevel.alphabet(), show_progress=False))
    HOME.mkdir(parents=True, exist_ok=True)
    tk.save(str(f))
    print(f"[scratch] vocabulary of {tk.get_vocab_size()} pieces learned from {len(files)} harvested files", flush=True)
    return tk


def _record(**new):
    f = HOME / "record.json"
    rec = json.loads(f.read_text()) if f.exists() else {}
    rec.update(new)
    HOME.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(rec, indent=1))
    return rec


def corpus(tk):
    """The harvest as one long row of pieces (kept on disk; made again when the harvest has grown)."""
    import numpy as np
    from team import harvest
    files = harvest.files()
    size = sum(p.stat().st_size for p in files)
    f = HOME / "corpus.u16"
    if not f.exists() or _record().get("corpus_bytes") != size:
        with open(f, "wb") as out:
            for p in files:
                with open(p, encoding="utf-8", errors="replace") as fh:
                    while True:
                        lines = fh.readlines(4_000_000)
                        if not lines:
                            break
                        for e in tk.encode_batch(lines):
                            np.asarray([BOS] + e.ids, dtype=np.uint16).tofile(out)
        _record(corpus_bytes=size, corpus_pieces=f.stat().st_size // 2)
    return np.memmap(f, dtype=np.uint16, mode="r")


def pretrain(minutes=60, batch=32, lr=1e-3, seed=0):
    tk = tokenizer()
    data = corpus(tk)
    torch.manual_seed(seed)
    model, f = Tiny(), HOME / "base.pt"
    rec = _record()
    steps = rec.get("pretrain_steps", 0)
    if f.exists():
        model.load_state_dict(torch.load(f))
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01, betas=(0.9, 0.95))
    n = sum(p.numel() for p in model.parameters())
    print(f"[scratch] reader: {n / 1e6:.2f}M weights, {len(data) / 1e6:.1f}M pieces of harvested text, "
          f"{steps} steps so far", flush=True)
    rnd, t0, seen, losses = random.Random(seed + steps), time.time(), 0, []
    while time.time() - t0 < minutes * 60:
        for g in opt.param_groups:  # a short warm-up, then steady: the run is cut by the clock, not by a schedule
            g["lr"] = lr * min(1.0, (steps + 1) / 200)
        at = [rnd.randrange(0, len(data) - CTX - 1) for _ in range(batch)]
        x = torch.stack([torch.from_numpy(data[i:i + CTX + 1].astype("int64")) for i in at])
        loss = F.cross_entropy(model.next_piece(x[:, :-1]).reshape(-1, VOCAB), x[:, 1:].reshape(-1))
        opt.zero_grad(set_to_none=True)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        steps, seen = steps + 1, seen + batch * CTX
        losses.append(loss.item())
        if steps % 100 == 0:
            print(f"[scratch] step {steps}: loss {sum(losses[-100:]) / len(losses[-100:]):.3f}, "
                  f"{seen / (time.time() - t0):.0f} pieces a second", flush=True)
            torch.save(model.state_dict(), f)
            _record(pretrain_steps=steps, pretrain_loss=round(sum(losses[-100:]) / len(losses[-100:]), 3),
                    pretrain_pieces_read=rec.get("pretrain_pieces_read", 0) + seen, weights=n)
    torch.save(model.state_dict(), f)
    return _record(pretrain_steps=steps, pretrain_loss=round(sum(losses[-100:]) / max(1, len(losses[-100:])), 3),
                   pretrain_pieces_read=rec.get("pretrain_pieces_read", 0) + seen, weights=n)


def _batch(tk, xs):
    ids = [([BOS] + e.ids)[-CTX:] for e in tk.encode_batch(list(xs))]  # too long: the end of the input is kept
    width = max(len(i) for i in ids)
    return (torch.tensor([i + [PAD] * (width - len(i)) for i in ids]), torch.tensor([len(i) - 1 for i in ids]))


def accuracy(model, tk, rows, labels):
    model.eval()
    ok = 0
    with torch.no_grad():
        for i in range(0, len(rows), 64):
            part = rows[i:i + 64]
            ids, last = _batch(tk, [x for x, _ in part])
            # the input is padded on the right and read left to right: a position never sees the padding after it
            ok += (model.label(ids, last).argmax(-1) == torch.tensor([labels.index(y) for _, y in part])).sum().item()
    return ok / max(1, len(rows))


def fit(skill, plain=False, epochs=12, batch=32, seed=0, log=print, rows=0):
    """Train every weight on one cell job. Returns the scores; the weights go to cells/scratch/<skill>.pt.
    rows: train on that many rows from the job's own generator instead of the few hundred today's cells get. A model
    that starts from nothing needs far more examples (the Tiny Recursive Model, 7M weights, was trained on about a
    thousand variations of each example). The extra rows come from the training pool of words only; none is a dev or
    test input. With them the dev split no longer holds back words, so it picks the epoch and says little else; the
    test split (the other pool of words) is unchanged."""
    from team.cells import skills as S
    from training import cells as C
    labels = S.SKILLS[skill]["labels"]
    tr, dv, te = C.data(skill)
    if rows and not S.SKILLS[skill].get("learned"):
        held = {x for x, _ in dv} | {x for x, _ in te}
        more = [r for sd in range(1, 4) for r in S.examples(skill, "train", rows, seed=sd)]
        tr = list({x: (x, y) for x, y in tr + more if x not in held}.values())[:rows]
        epochs = max(3, min(epochs, 60000 // max(1, len(tr))))  # about the same number of steps as a long small run
    tk = tokenizer()
    torch.manual_seed(seed)
    model = Tiny(len(labels))
    if not plain:
        model.load_state_dict(torch.load(HOME / "base.pt"), strict=False)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3 if plain else 5e-4, weight_decay=0.05)
    rnd, best, t0 = random.Random(seed), (-1.0, None), time.time()
    for ep in range(epochs):
        model.train()
        order = list(tr)
        rnd.shuffle(order)
        for i in range(0, len(order), batch):
            part = order[i:i + batch]
            ids, last = _batch(tk, [x for x, _ in part])
            loss = F.cross_entropy(model.label(ids, last), torch.tensor([labels.index(y) for _, y in part]))
            opt.zero_grad(set_to_none=True)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
        d = accuracy(model, tk, dv, labels)
        if d > best[0]:
            best = (d, {k: v.clone() for k, v in model.state_dict().items()})
    model.load_state_dict(best[1])
    out = {"skill": skill, "labels": len(labels), "train_rows": len(tr), "epochs": epochs, "dev": round(best[0], 4),
           "test": round(accuracy(model, tk, te, labels), 4), "test_rows": len(te), "read_first": not plain,
           "seconds": round(time.time() - t0)}
    if not plain:
        torch.save(model.state_dict(), HOME / f"{skill}.pt")
    log(f"[scratch] {skill}{' (plain)' if plain else ''}: dev {out['dev']:.3f}, test {out['test']:.3f} on "
        f"{len(te)} rows of unseen words, {out['seconds']} s", flush=True)
    return out


class Brain(nn.Module):
    """Every cell job in one model: one trunk that reads the input, and a small head per job. With talk, a job's
    head also sees what every other head says about the same input before it decides: the cells consult each other."""

    def __init__(self, jobs, talk=False):
        super().__init__()
        self.trunk, self.jobs, self.talk = Tiny(), dict(jobs), talk
        self.first = nn.ModuleDict({k: nn.Linear(DIM, n) for k, n in jobs.items()})
        said = sum(jobs.values())
        self.second = nn.ModuleDict({k: nn.Linear(DIM + said, n) for k, n in jobs.items()}) if talk else None

    def forward(self, job, ids, last):
        h = self.trunk.body(ids)[torch.arange(ids.shape[0]), last]
        own = self.first[job](h)
        if not self.talk:
            return own, own
        said = torch.cat([F.softmax(self.first[k](h), -1) for k in self.jobs], -1).detach()
        return self.second[job](torch.cat([h, said], -1)), own


def together(talk=False, plain=False, epochs=12, batch=32, seed=0, log=print):
    """One brain for all the cell jobs, trained on all of them at once (his direction: cells trained together, each
    depending on the others, acting as one). Each step takes one job at random and a batch of its rows, so a job
    with few rows counts as much as one with many. The same rows, dev and test as the cells trained alone."""
    from team.cells import learn
    from team.cells import skills as S
    from training import cells as C
    learn.register()
    data = {}
    for skill, sk in S.SKILLS.items():
        if "labels" in sk and skill != "gate":
            try:
                tr, dv, te = C.data(skill)
                if tr and dv and te:
                    data[skill] = (tr, dv, te, sk["labels"])
            except Exception as e:  # noqa: BLE001
                log(f"[scratch] {skill}: left out ({type(e).__name__})", flush=True)
    tk = tokenizer()
    torch.manual_seed(seed)
    model = Brain({k: len(v[3]) for k, v in data.items()}, talk)
    if not plain:
        model.trunk.load_state_dict(torch.load(HOME / "base.pt"), strict=False)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3 if plain else 5e-4, weight_decay=0.05)
    rnd, t0, names = random.Random(seed), time.time(), list(data)
    steps = sum(len(v[0]) for v in data.values()) * epochs // batch

    def acc(split):
        model.eval()
        out = {}
        with torch.no_grad():
            for k, v in data.items():
                rows, labels, ok = v[split], v[3], 0
                for i in range(0, len(rows), 64):
                    part = rows[i:i + 64]
                    ids, last = _batch(tk, [x for x, _ in part])
                    ok += (model(k, ids, last)[0].argmax(-1) == torch.tensor([labels.index(y) for _, y in part])).sum().item()
                out[k] = ok / len(rows)
        return out
    best = (-1.0, None)
    for step in range(1, steps + 1):
        model.train()
        k = rnd.choice(names)
        tr, labels = data[k][0], data[k][3]
        part = [tr[rnd.randrange(len(tr))] for _ in range(batch)]
        ids, last = _batch(tk, [x for x, _ in part])
        y = torch.tensor([labels.index(t) for _, t in part])
        final, own = model(k, ids, last)
        loss = F.cross_entropy(final, y) + (F.cross_entropy(own, y) if talk else 0)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        if step % max(1, steps // 12) == 0 or step == steps:
            d = acc(1)
            mean = sum(d.values()) / len(d)
            if mean > best[0]:
                best = (mean, {n: v.clone() for n, v in model.state_dict().items()})
            log(f"[scratch] together{' (consulting)' if talk else ''}: step {step} of {steps}, mean dev {mean:.3f}", flush=True)
    model.load_state_dict(best[1])
    te = acc(2)
    key = ("together_consulting" if talk else "together") + ("_plain" if plain else "")
    torch.save(model.state_dict(), HOME / f"brain_{key}.pt")
    f = ROOT / "training" / "reports" / "scratch_cells.json"
    res = json.loads(f.read_text()) if f.exists() else {}
    for k, v in te.items():
        res.setdefault(k, {})[key] = {"test": round(v, 4), "test_rows": len(data[k][2])}
    res["_" + key] = {"jobs": len(data), "weights": sum(p.numel() for p in model.parameters()), "mean_dev": round(best[0], 4),
                      "mean_test": round(sum(te.values()) / len(te), 4), "seconds": round(time.time() - t0)}
    f.write_text(json.dumps(res, indent=1))
    log(f"[scratch] {key}: {len(data)} jobs in one model of {res['_' + key]['weights'] / 1e6:.2f}M weights, mean test "
        f"{res['_' + key]['mean_test']:.3f} (mean dev {best[0]:.3f}), {res['_' + key]['seconds']} s", flush=True)
    return res["_" + key]


def everything(plain=False, rows=0):
    from team.cells import skills as S
    from team.cells import learn, use
    learn.register()
    wins, f = use.wins(), ROOT / "training" / "reports" / "scratch_cells.json"
    res = json.loads(f.read_text()) if f.exists() else {}
    key = ("plain" if plain else "read_first") + (f"_{rows}_rows" if rows else "")
    for skill, s in S.SKILLS.items():
        if "labels" not in s or skill == "gate" or key in res.get(skill, {}):
            continue
        try:
            r = fit(skill, plain, rows=rows)
        except Exception as e:  # noqa: BLE001 - a job with no rows yet is skipped and named
            print(f"[scratch] {skill}: skipped ({type(e).__name__}: {str(e)[:100]})", flush=True)
            continue
        w = wins.get(skill, {})
        res.setdefault(skill, {}).update({key: r, "todays_cell": w.get("cell"), "member": w.get("incumbent"),
                                          "member_name": w.get("incumbent_name")})
        f.write_text(json.dumps(res, indent=1))
    return res


def main(argv):
    opt = lambda k, d: type(d)(argv[argv.index(k) + 1]) if k in argv else d  # noqa: E731
    cmd = argv[0] if argv else ""
    if cmd == "tokenizer":
        tokenizer(train=True)
    elif cmd == "pretrain":
        print(json.dumps(pretrain(opt("--minutes", 60.0))))
    elif cmd == "fit":
        print(json.dumps(fit(argv[1], "--plain" in argv, rows=opt("--rows", 0))))
    elif cmd == "together":
        print(json.dumps(together("--consult" in argv, "--plain" in argv)))
    elif cmd == "all":
        everything("--plain" in argv, rows=opt("--rows", 0))
    else:
        print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
