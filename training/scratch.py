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

    python training/scratch.py pairs [--minutes 30]      a second way of reading: from one passage, predict what the
                                                         passage next to it means (writes base_pairs.pt);
                                                         `together --trunk base_pairs` then builds the brain on it

    python training/scratch.py bitnet [--minutes 30]     the stem cell becomes a BitNet (weights of -1, 0, +1), trained
                                                         here; every cell grown from it afterwards is a BitNet cell

    python training/scratch.py direct [--minutes 20] [--rate 0.003]   a BitNet stem cell trained the direct way, from
                                                         random three-valued weights, with no ordinary weights underneath

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
SHARED = ROOT / "cells" / "scratch"  # what every body of the hive shares: the vocabulary and the harvested text as pieces
BODY = __import__("os").environ.get("HIVE_BODY", "")  # which body this process works on ("": the first one)
HOME = SHARED / "bodies" / BODY if BODY else SHARED  # that body's own stem cell, cells and records
VOCAB, DIM, LAYERS, HEADS, CTX = 4096, 192, 4, 4, 256
PAD, BOS = 0, 1
HELD = 40  # every 40th window of the text is never trained on, by a stem cell or by a cell: the hive is measured there
EASE = [1.0]  # how much of the rounding is on (1: a BitNet as it works; less only while a new stem cell eases into it)


def offsets(rnd, n, batch):
    """Where a batch of training windows starts in a text of n pieces: anywhere that does not touch a held window."""
    out = []
    while len(out) < batch:
        i = rnd.randrange(0, n - CTX - 1)
        if (i // CTX) % HELD and ((i + CTX) // CTX) % HELD:
            out.append(i)
    return out


class BitLinear(nn.Linear):
    """A layer of a BitNet (b1.58): when it works, every weight is -1, 0 or +1, times one number for the whole layer,
    and what comes in is rounded to 8 bits. It is trained on ordinary weights underneath: at each step they are
    rounded to the three values for the forward pass, and the correction flows back to the ordinary weights as if
    no rounding had happened (the straight-through way). So training costs what it always costs; the cell that
    comes out is stored in about two bits a weight (pack)."""

    def forward(self, x):
        w, ease = self.weight, EASE[0]
        scale = w.abs().mean().clamp(min=1e-5)
        w = w + ease * ((w / scale).round().clamp(-1, 1) * scale - w).detach()
        top = x.abs().amax(-1, keepdim=True).clamp(min=1e-5)
        x = x + ease * ((x * 127 / top).round().clamp(-128, 127) * top / 127 - x).detach()
        return F.linear(x, w, self.bias)


def kind(home=None):
    """What this body's cells are: {"bit", "dim", "layers", "heads", "subln"}. It is written once, when the body's
    stem cell is made (stem.json beside the stem cell; the first body's travels with it in git), and every cell of
    the body has it. Bodies may differ: what they share is the vocabulary and the harvest, not their shape."""
    try:
        k = json.loads(((home or HOME) / "stem.json").read_text())
    except (OSError, ValueError):
        k = {}
    return {"bit": bool(k.get("bit")), "dim": int(k.get("dim", DIM)), "layers": int(k.get("layers", LAYERS)),
            "heads": int(k.get("heads", HEADS)), "subln": bool(k.get("subln"))}


def is_bit():
    """Are this body's own cells BitNets?"""
    return kind()["bit"]


class Block(nn.Module):
    """subln: one more norm right before each of the block's two output layers (the published BitNet recipe: what
    goes into a three-valued layer is normed before it is rounded to 8 bits; without it the stem cell's first
    BitNets rounded un-normed numbers at those two layers)."""

    def __init__(self, bit=False, dim=DIM, heads=HEADS, subln=False):
        super().__init__()
        lin = BitLinear if bit else nn.Linear
        self.heads = heads
        self.n1, self.n2 = nn.LayerNorm(dim), nn.LayerNorm(dim)
        self.qkv, self.out = lin(dim, 3 * dim), lin(dim, dim)
        self.up, self.down = lin(dim, 4 * dim), lin(4 * dim, dim)
        if subln:
            self.s1, self.s2 = nn.LayerNorm(dim), nn.LayerNorm(4 * dim)
        self.subln = subln

    def forward(self, x, causal):
        b, t, d = x.shape
        q, k, v = self.qkv(self.n1(x)).view(b, t, 3, self.heads, d // self.heads).permute(2, 0, 3, 1, 4)
        a = F.scaled_dot_product_attention(q, k, v, is_causal=causal).transpose(1, 2).reshape(b, t, d)
        x = x + self.out(self.s1(a) if self.subln else a)
        h = F.gelu(self.up(self.n2(x)))
        return x + self.down(self.s2(h) if self.subln else h)


class Tiny(nn.Module):
    """A small transformer. As a reader it predicts the next piece; as a cell it reads the whole input and its last
    position chooses a label."""

    def __init__(self, labels=0, bit=None, shape=None):
        super().__init__()
        k = shape or kind()
        self.bit = k["bit"] if bit is None else bit
        self.dim = dim = k["dim"]
        self.tok, self.pos = nn.Embedding(VOCAB, dim), nn.Embedding(CTX, dim)
        self.blocks = nn.ModuleList(Block(self.bit, dim, k["heads"], k["subln"]) for _ in range(k["layers"]))
        self.norm = nn.LayerNorm(dim)
        self.head = nn.Linear(dim, labels) if labels else None
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


class Direct:
    """Training a BitNet the direct way: there are no ordinary weights underneath.

    The usual way keeps a full-precision copy of every weight and rounds it at each step. Here a weight of a
    three-valued layer is never anything but -1, 0 or +1. At each step every such weight may jump one value in the
    direction that lowers the loss, with a probability in proportion to how strongly its own gradient asks for it
    (its gradient against the layer's average). A weight that is pulled weakly but always the same way still gets
    there, by chance adding up over steps, which is what the stored copy was for. `rate` is the share of a layer's
    weights expected to jump in one step; it is lowered as training goes on, and the jumping dies down.
    What is not three-valued (the table of word pieces, the norms, the biases, and one number per layer that scales
    its three values) is trained the ordinary way; that is under a third of the stem cell and is shared by all cells.
    (His order, 2026-11-10: if no direct route exists, make one.)"""

    def __init__(self, model, lr=1e-3, seed=0, votes=0, strong=0.5, leak=0, agree=False):
        # by votes, three things can be set: which share of a layer's weights is too weakly pulled to vote (strong),
        # after how many steps every counter forgets one vote (leak; 0: never), and whether a vote only counts when
        # the weight was pulled the same way at the step before (agree: one more bit per weight)
        self.votes, self.strong, self.leak, self.agree, self.steps = votes, strong, leak, agree, 0
        self.layers = [m for m in model.modules() if isinstance(m, BitLinear)]
        own = {id(m.weight) for m in self.layers}
        self.t, self.log_scale = [], []
        for m in self.layers:
            scale = m.weight.detach().abs().mean().clamp(min=1e-5)
            self.t.append((m.weight.detach() / scale).round().clamp(-1, 1))
            self.log_scale.append(torch.nn.Parameter(scale.log()))
        self.opt = torch.optim.AdamW([p for p in model.parameters() if id(p) not in own] + self.log_scale, lr=lr,
                                     weight_decay=0.0, betas=(0.9, 0.95))
        self.gen = torch.Generator().manual_seed(seed)
        self.model = model
        self.count = [torch.zeros_like(t, dtype=torch.int8) for t in self.t]  # the votes, when it trains by votes
        self.last = [torch.zeros_like(t, dtype=torch.int8) for t in self.t]   # which way each weight was pulled last
        self.install()

    def install(self):
        """Each layer's weights as its three values times a number such that rounding gives them back exactly."""
        with torch.no_grad():
            for m, t, ls in zip(self.layers, self.t, self.log_scale):
                m.weight.copy_(t * (ls.exp() / t.abs().mean().clamp(min=1e-5)))

    def step(self, loss, rate):
        """One step. Returns the share of three-valued weights that jumped."""
        self.opt.zero_grad(set_to_none=True)
        for m in self.layers:
            m.weight.grad = None
        loss.backward()
        nn.utils.clip_grad_norm_([p for g in self.opt.param_groups for p in g["params"] if p.grad is not None], 1.0)
        jumped, total = 0, 0
        with torch.no_grad():
            for i, m in enumerate(self.layers):
                g, t = m.weight.grad, self.t[i]
                self.log_scale[i].grad = (g * t).sum() * self.log_scale[i].exp()  # the layer's number learns the ordinary way
                if self.votes:
                    # by votes: a small counter per weight (a few bits) instead of a full-precision copy. Each step a
                    # weight whose gradient is not among the layer's weak half gets one vote for the direction that
                    # lowers the loss; at `votes` more votes one way than the other it jumps one value and its
                    # counter starts again. (The first direct way had nothing that added the evidence up, and on
                    # real text its jumps taught nothing: 4.25 with them, 4.24 without, 4.03 the published way.)
                    strong = g.abs() >= (g.abs().median() if self.strong == 0.5 else g.abs().flatten().kthvalue(
                        max(1, int(self.strong * g.numel()))).values)
                    vote = (-g.sign() * strong).to(torch.int8)
                    if self.agree:
                        vote, self.last[i] = torch.where(vote == self.last[i], vote, torch.zeros_like(vote)), vote
                    c = self.count[i]
                    if self.leak and self.steps % self.leak == 0:
                        c = c - c.sign()
                    c = (c + vote).clamp(-self.votes, self.votes)
                    go = c.abs() >= self.votes
                    want = (t + c.sign()).clamp(-1, 1)
                    self.count[i] = torch.where(go, torch.zeros_like(c), c)
                    go = go & (want != t)
                else:
                    want = (t - g.sign()).clamp(-1, 1)
                    go = (torch.rand(g.shape, generator=self.gen) < rate * g.abs() / g.abs().mean().clamp(min=1e-12)) & (want != t)
                self.t[i] = torch.where(go, want, t)
                jumped, total = jumped + int(go.sum()), total + t.numel()
        self.opt.step()
        self.install()
        self.steps += 1
        return jumped / total


def pretrain_direct(minutes=20.0, rate=0.003, batch=32, seed=0, name="base_direct", log=print, usual=False, votes=0,
                    strong=0.5, leak=0, agree=False, hard=None, lr=1e-3, warm=0, ease=0.0, teacher=None, taught=0.5):
    """A BitNet stem cell from random three-valued weights, trained the direct way on the harvest (cells/scratch/
    <name>.pt). The rate of jumping falls in a straight line to a twentieth of its start over the run.
    Two things to hold it against, from the same start, for the same time: rate 0 (no weight ever jumps: what the
    parts that are not three-valued learn by themselves) and usual=True (the published way: ordinary weights
    underneath, rounded at every step; `lr` is its rate, reached over the first `warm` steps).
    ease: the share of the run over which the rounding is eased in (it starts as an ordinary net and is a BitNet
    from there on). teacher: the home of a body whose stem cell reads every batch too; the new one learns the text
    and, for `taught` of its loss, what the teacher expects next. Both measured: training/reports/bitnet_recipe.json."""
    tk = tokenizer()
    data = corpus(tk)
    torch.manual_seed(seed)
    model = Tiny(bit=True)
    if teacher is not None:
        old = Tiny(shape=kind(Path(teacher)))
        old.load_state_dict(torch.load(Path(teacher) / "base.pt"))
        old.eval()
    if usual:
        opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01, betas=(0.9, 0.95))

        class trainer:  # noqa: N801 - the same two lines as pretrain, in the shape of Direct
            @staticmethod
            def step(loss, rate):
                for g in opt.param_groups:
                    g["lr"] = lr * min(1.0, (steps + 1) / max(1, warm))
                opt.zero_grad(set_to_none=True)
                loss.backward()
                nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                opt.step()
                return 0.0
    else:
        trainer = Direct(model, seed=seed, votes=votes, strong=strong, leak=leak, agree=agree)
    rnd, t0, steps, losses, jumps = random.Random(seed), time.time(), 0, [], []
    while time.time() - t0 < minutes * 60:
        done = (time.time() - t0) / (minutes * 60)
        at = offsets(rnd, len(data), batch)
        if hard:  # half of what it reads is the text the bodies before it read worst
            at[:batch // 2] = [rnd.choice(hard) * CTX for _ in range(batch // 2)]
        x = torch.stack([torch.from_numpy(data[i:i + CTX + 1].astype("int64")) for i in at])
        EASE[0] = min(1.0, done / ease) if ease else 1.0
        logits = model.next_piece(x[:, :-1])
        loss = F.cross_entropy(logits.reshape(-1, VOCAB), x[:, 1:].reshape(-1))
        if teacher is not None:
            EASE[0] = 1.0  # the teacher reads as it works
            with torch.no_grad():
                expects = F.log_softmax(old.next_piece(x[:, :-1]), -1)
            EASE[0] = min(1.0, done / ease) if ease else 1.0
            away = F.kl_div(F.log_softmax(logits, -1), expects, log_target=True, reduction="batchmean") / CTX
            losses.append(loss.item())
            loss = (1 - taught) * loss + taught * away
        else:
            losses.append(loss.item())
        jumps.append(trainer.step(loss, rate * (1 - 0.95 * done)))
        steps += 1
        if steps % 100 == 0:
            log(f"[scratch] direct, step {steps}: loss {sum(losses[-100:]) / 100:.3f}, {sum(jumps[-100:]) / 100:.2%} of the "
                f"three-valued weights jump a step", flush=True)
    EASE[0] = 1.0
    HOME.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), HOME / f"{name}.pt")
    out = {"steps": steps, "loss": round(sum(losses[-100:]) / max(1, len(losses[-100:])), 3), "rate": rate, "minutes": minutes,
           "way": "usual (ordinary weights underneath)" if usual else f"direct by votes ({votes}; strong {strong}, leak {leak}, agree {agree})" if votes else "direct" if rate else "direct with no jumps"}
    _record(**{name: out})
    return out


TABLE = ("tok.", "pos.")  # what every cell has from the stem cell and does not carry itself


def pack(model):
    """A BitNet cell as it is stored: for each of its three-valued layers the one number and two bit-planes (where
    the weight is +1, where it is -1); the few other numbers (norms, biases) in 16 bits. The table of word pieces is
    not stored: every cell has the stem cell's. About half a megabyte for 1.8 million weights."""
    import numpy as np
    out = {}
    for name, p in model.state_dict().items():
        if name.startswith(TABLE):
            continue
        if name.startswith("blocks.") and name.endswith(".weight") and p.dim() == 2:
            scale = p.abs().mean().clamp(min=1e-5)
            t = (p / scale).round().clamp(-1, 1)
            out[name] = {"scale": float(scale), "shape": list(p.shape), "plus": np.packbits((t == 1).numpy()),
                         "minus": np.packbits((t == -1).numpy())}
        else:
            out[name] = p.to(torch.float16)
    return out


def unpack(packed, stem_state):
    """The weights of a stored BitNet cell. A three-valued layer comes back as its values times a number chosen so
    that rounding it again gives exactly the same layer (the layer's one number divided by the share of weights
    that are not zero)."""
    import numpy as np
    state = {k: v for k, v in stem_state.items() if k.startswith(TABLE)}
    for name, v in packed.items():
        if isinstance(v, dict):
            n = v["shape"][0] * v["shape"][1]
            t = (np.unpackbits(v["plus"])[:n].astype("float32") - np.unpackbits(v["minus"])[:n].astype("float32")).reshape(v["shape"])
            share = max(float(np.abs(t).mean()), 1e-5)
            state[name] = torch.from_numpy(t) * (v["scale"] / share)
        else:
            state[name] = v.to(torch.float32)
    return state


def whole(obj, path):
    """Write a file whole or not at all: to a side file first, then in its place in one move. A run that is cut off
    while it writes leaves the old file, never half of a new one."""
    import os
    path = Path(path)
    tmp = path.with_name(path.name + ".part")
    torch.save(obj, tmp)
    os.replace(tmp, path)


def save_cell(model, path):
    whole(pack(model) if model.bit else model.state_dict(), path)


def load_cell(path, labels=0):
    """A cell from its file: a BitNet cell is unpacked onto the stem cell's table of word pieces."""
    got = torch.load(path, weights_only=False)
    packed = any(isinstance(v, dict) for v in got.values())
    m = Tiny(labels, bit=packed)
    m.load_state_dict(unpack(got, torch.load(HOME / "base.pt")) if packed else got)
    return m


def to_bitnet(minutes=30.0):
    """The stem cell becomes a BitNet. Its ordinary weights are kept as what it is trained on underneath; from now on
    it works in three values, and it goes on reading the harvest that way for so many minutes, so that it learns to
    do with three values what it did with many. The stem cell as it was stays in base_full.pt. Every cell grown
    after this is a BitNet cell; cells grown before are of the other kind and are put away."""
    import shutil
    if not is_bit():
        shutil.copyfile(HOME / "base.pt", HOME / "base_full.pt")
        old = HOME / "body"
        if old.exists():
            shutil.rmtree(HOME / "body_full", ignore_errors=True)
            old.rename(HOME / "body_full")
        (HOME / "stem.json").write_text(json.dumps({"bit": True, "since": time.strftime("%Y-%m-%d %H:%M"),
                                                    "loss_before": _record().get("pretrain_loss")}, indent=1))
    out = pretrain(minutes)
    kind = json.loads((HOME / "stem.json").read_text())
    kind.update(loss_now=out.get("pretrain_loss"), steps=out.get("pretrain_steps"))
    (HOME / "stem.json").write_text(json.dumps(kind, indent=1))
    return out


def tokenizer(train=False):
    from tokenizers import Tokenizer, decoders, models, pre_tokenizers, trainers
    f = SHARED / "tokenizer.json"
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
    SHARED.mkdir(parents=True, exist_ok=True)
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
    """The harvest as one long row of pieces, kept on disk and shared by every body. It only ever grows at its end:
    when the harvest has new text (a longer file, a new source), only the new part is turned into pieces and added.
    What was at a place stays at that place, so the windows the cells' territories and the held-out passages are
    made of never move. cells/scratch/corpus.json keeps the order in which every stretch of text was added; if the
    row of pieces is lost it is made again in exactly that order (regeneration), and every window is where it was."""
    import numpy as np
    from team import harvest
    f, book = SHARED / "corpus.u16", SHARED / "corpus.json"
    try:
        log = json.loads(book.read_text())
    except (OSError, ValueError):
        log = None
    moved = False
    if isinstance(log, dict) and "log" not in log:  # kept as name -> bytes before the order was kept: that order was by name
        log, moved = {"log": [[n, 0, b] for n, b in sorted(log.items())]}, True
    files = {p.name: p for p in harvest.files()}
    if log is None:
        old = json.loads((SHARED / "record.json").read_text()).get("corpus_files") if (SHARED / "record.json").exists() else None
        if old is None and f.exists():
            old = {n: p.stat().st_size for n, p in files.items()}
        log = {"log": [[n, 0, b] for n, b in sorted((old or {}).items())]}
    SHARED.mkdir(parents=True, exist_ok=True)

    def add(out, path, start, end):
        """Exactly the bytes from start to end, line by line (a read "of about so many bytes" takes whole lines past
        the end, and a stretch read twice would move every window after it)."""
        with open(path, "rb") as fh:
            fh.seek(start)
            left, carry = end - start, b""
            while left > 0:
                chunk = fh.read(min(4_000_000, left))
                if not chunk:
                    break
                left -= len(chunk)
                parts = (carry + chunk).split(b"\n")
                carry = parts.pop()
                lines = [p + b"\n" for p in parts] + ([carry] if left <= 0 and carry else [])
                for e in tk.encode_batch([ln.decode("utf-8", errors="replace") for ln in lines]):
                    np.asarray([BOS] + e.ids, dtype=np.uint16).tofile(out)
    if not f.exists() and log["log"]:  # the row of pieces is gone: made again, every stretch in the order it was added
        with open(f, "wb") as out:
            for name, start, end in log["log"]:
                if name in files:
                    add(out, files[name], start, end)
    done = {}
    for name, _, end in log["log"]:
        done[name] = max(done.get(name, 0), end)
    grew = not book.exists()
    with open(f, "ab") as out:
        for name in sorted(files, key=lambda n: (n not in done, n)):
            at, size = done.get(name, 0), files[name].stat().st_size
            if size > at:
                add(out, files[name], at, size)
                log["log"].append([name, at, size])
                grew = True
    if grew or moved or not book.exists():
        book.write_text(json.dumps(log))
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
        at = offsets(rnd, len(data), batch)
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


def pairs(minutes=30, batch=48, lr=3e-4, seed=0, width=64):
    """A second way of reading, after LeCun's joint-embedding work (JEPA; a 109M model trained on paired views lined
    up with image models better than a 72B language model): two passages that stand next to each other in the
    harvest are two views of one thing. The trunk reads each; from what the first means it must predict what the
    second means. Two terms keep it from the easy way out of saying the same for everything: every direction of the
    meaning must keep its spread across a batch, and the directions must not copy each other (VICReg, from the same
    lab). Next-piece prediction goes on beside it, so the trunk does not forget how to read.
    It goes on from cells/scratch/base.pt and writes cells/scratch/base_pairs.pt; base.pt stays as it is."""
    tk = tokenizer()
    data = corpus(tk)
    torch.manual_seed(seed)
    model = Tiny()
    src = HOME / "base_pairs.pt" if (HOME / "base_pairs.pt").exists() else HOME / "base.pt"
    model.load_state_dict(torch.load(src))
    predict = nn.Sequential(nn.Linear(model.dim, 2 * model.dim), nn.GELU(), nn.Linear(2 * model.dim, model.dim))
    opt = torch.optim.AdamW(list(model.parameters()) + list(predict.parameters()), lr=lr, weight_decay=0.01)
    rnd, t0, steps, log = random.Random(seed + _record().get("pairs_steps", 0)), time.time(), 0, []

    def spread(z):
        z = z - z.mean(0)
        std = torch.sqrt(z.var(0) + 1e-4)
        cov = (z.T @ z) / (z.shape[0] - 1)
        off = cov - torch.diag(torch.diag(cov))
        return F.relu(1 - std).mean(), (off ** 2).sum() / z.shape[1]
    while time.time() - t0 < minutes * 60:
        at = [rnd.randrange(0, len(data) - 2 * width - 1) for _ in range(batch)]
        a = torch.stack([torch.from_numpy(data[i:i + width].astype("int64")) for i in at])
        b = torch.stack([torch.from_numpy(data[i + width:i + 2 * width + 1].astype("int64")) for i in at])
        ha, hb = model.body(a), model.body(b[:, :-1])
        za, zb = ha.mean(1), hb.mean(1)
        va, ca = spread(za)
        vb, cb = spread(zb)
        same = F.mse_loss(predict(za), zb)
        read = F.cross_entropy((hb @ model.tok.weight.T).reshape(-1, VOCAB), b[:, 1:].reshape(-1))
        loss = 25 * same + 25 * (va + vb) + (ca + cb) + read
        opt.zero_grad(set_to_none=True)
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        steps += 1
        log.append((same.item(), (va + vb).item(), read.item()))
        if steps % 100 == 0:
            m = [sum(x[i] for x in log[-100:]) / 100 for i in range(3)]
            print(f"[scratch] pairs step {steps}: second view predicted to {m[0]:.4f}, spread lost {m[1]:.3f}, "
                  f"next piece {m[2]:.3f}", flush=True)
            torch.save(model.state_dict(), HOME / "base_pairs.pt")
    torch.save(model.state_dict(), HOME / "base_pairs.pt")
    m = [sum(x[i] for x in log[-100:]) / max(1, len(log[-100:])) for i in range(3)]
    return _record(pairs_steps=_record().get("pairs_steps", 0) + steps, pairs_second_view=round(m[0], 4),
                   pairs_next_piece=round(m[2], 3))


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
        dim = self.trunk.dim
        self.first = nn.ModuleDict({k: nn.Linear(dim, n) for k, n in jobs.items()})
        said = sum(jobs.values())
        self.second = nn.ModuleDict({k: nn.Linear(dim + said, n) for k, n in jobs.items()}) if talk else None

    def forward(self, job, ids, last):
        h = self.trunk.body(ids)[torch.arange(ids.shape[0]), last]
        own = self.first[job](h)
        if not self.talk:
            return own, own
        said = torch.cat([F.softmax(self.first[k](h), -1) for k in self.jobs], -1).detach()
        return self.second[job](torch.cat([h, said], -1)), own


def together(talk=False, plain=False, epochs=12, batch=32, seed=0, log=print, trunk="base"):
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
        model.trunk.load_state_dict(torch.load(HOME / f"{trunk}.pt"), strict=False)
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
    key = ("together_consulting" if talk else "together") + ("_plain" if plain else "") + ("" if trunk == "base" else "_" + trunk[5:])
    torch.save(model.state_dict(), HOME / f"brain_{key}.pt")
    f = ROOT / "training" / "reports" / "scratch_cells.json"
    res = json.loads(f.read_text()) if f.exists() else {}
    for k, v in te.items():
        res.setdefault(k, {})[key] = {"test": round(v, 4), "test_rows": len(data[k][2])}
    res["_" + key] = {"jobs": len(data), "weights": sum(p.numel() for p in model.parameters()), "mean_dev": round(best[0], 4),
                      "mean_test": round(sum(te.values()) / len(te), 4), "seconds": round(time.time() - t0)}
    f.write_text(json.dumps(res, indent=1))
    if not plain:  # this brain goes to work: it holds each job where it scored at least as well as the present holder
        from team.cells import tiny, use
        torch.save(model.state_dict(), HOME / "brain.pt")
        (HOME / "brain.json").write_text(json.dumps({"jobs": {k: v[3] for k, v in data.items()}, "talk": talk,
                                                     "trunk": trunk, "test": {k: round(v, 4) for k, v in te.items()}}, indent=1))
        held = tiny.decide_holds(te, use.wins())
        (HOME / "holds.json").write_text(json.dumps(held, indent=1))
        log(f"[scratch] the brain holds {len(held)} of {len(data)} jobs: {', '.join(held) or 'none'}", flush=True)
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
    elif cmd == "direct":
        print(json.dumps(pretrain_direct(opt("--minutes", 20.0), opt("--rate", 0.003), name=opt("--name", "base_direct"),
                                         usual="--usual" in argv, votes=opt("--votes", 0), strong=opt("--strong", 0.5),
                                         leak=opt("--leak", 0), agree="--agree" in argv)))
    elif cmd == "bitnet":
        print(json.dumps(to_bitnet(opt("--minutes", 30.0))))
    elif cmd == "pretrain":
        print(json.dumps(pretrain(opt("--minutes", 60.0))))
    elif cmd == "fit":
        print(json.dumps(fit(argv[1], "--plain" in argv, rows=opt("--rows", 0))))
    elif cmd == "together":
        print(json.dumps(together("--consult" in argv, "--plain" in argv, trunk=opt("--trunk", "base"))))
    elif cmd == "pairs":
        print(json.dumps(pairs(opt("--minutes", 30.0))))
    elif cmd == "all":
        everything("--plain" in argv, rows=opt("--rows", 0))
    else:
        print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
