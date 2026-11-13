#!/usr/bin/env python3
"""run_overlap.py — driver skeleton for the overlap program (Muse's work, Muse's side).

Implements OVERLAP-DESIGN.md at SMOKE scale (2M-rung shape, v1 corpus, german/prose
tilts — the only real-text contrast v1 supports; see BUCKETS.md). The full program
swaps in corpus-v2 buckets behind the same bucket_of() interface and the ladder-
confirmed member shape; neither is wired here yet.

Discipline (same as the rest of the lab):
  - fixed held windows: every-40th rule via train.held_windows; training sampler
    mirrors train.offsets()' exclusion (a window is trainable only if neither it
    nor the following block is a held block);
  - seeds recorded on every record; results appended to scale-next/overlap-runs.jsonl
    (NEVER the ladder's runs.jsonl);
  - byte budgets by serialized artifact size with a manifest written before training.

SAFETY: without --launch this script only prints its plan and exits. It was
delivered unlaunched on purpose.

Core loops are real (sampler, training, probing, exchange-set construction,
ensemble/router reads, Gate 0 divergence). Stubbed with TODO: dreaming round,
chunked/resumable generalist for the full shape, corpus-v2 bucket swap.
"""
import argparse
import io
import json
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent          # scale-next/
LAB = HERE.parent                                # bitnet-lab/
sys.path.insert(0, str(LAB))
sys.path.insert(0, str(HERE))

import numpy as np
import torch
import torch.nn.functional as F

from train import (CTX, EASE, HELD_EVERY, VOCAB, Layered, Tiny,  # noqa: E402
                   held_loss, held_windows)
from bucket_probe import bucket_of  # noqa: E402  (module loads tokenizer + memmap)

RESULTS = HERE / "overlap-runs.jsonl"
INDEX_CACHE = HERE / "window-index.json"
MANIFEST = HERE / "byte-manifest.json"

# --- frozen design constants (OVERLAP-DESIGN.md; change only via a design revision) ---
TILTS = ("german", "prose")          # skeleton: 2 tilts on v1; full program: v2 buckets
UNIFORM_SHARE = 0.55                 # tilt mix: 55% uniform + 45% own bucket
WEAK_MARGIN = 0.5                    # relative-weakness margin (best-other beats member by >=)
PROBE_CAP_PER_BUCKET = 2048          # probe-pool subsample cap
SHINGLE = 64                         # near-duplicate guard vs held windows
MIN_BUCKET_HELD = 40                 # per-bucket claims need >= this many held candidates
SMOKE_SHAPE = dict(dim=288, layers=2)              # 2M rung
SMOKE_GENERALIST = dict(dim=688, layers=7)         # ~equal served bytes to 4 smoke members (NUMBERS.md)
BATCH = 32


# ----------------------------------------------------------------------------- data
class WindowIndex:
    """Aligned 256-token windows, bucketed once, split by the lab's held rule."""

    def __init__(self, data):
        self.data = data
        if INDEX_CACHE.exists():
            raw = json.loads(INDEX_CACHE.read_text())
            self.by_bucket = {k: list(map(int, v)) for k, v in raw["by_bucket"].items()}
            self.held_candidates = list(map(int, raw["held_candidates"]))
            return
        n_win = (len(data) - CTX) // CTX
        self.by_bucket, self.held_candidates = {}, []
        for w in range(n_win):
            s = w * CTX
            if w % HELD_EVERY == 0:
                self.held_candidates.append(s)
                continue
            if (w + 1) % HELD_EVERY == 0:
                continue  # offsets() exclusion: window feeding into a held block
            name, _, _ = bucket_of(np.asarray(data[s:s + CTX]))
            self.by_bucket.setdefault(name, []).append(s)
        INDEX_CACHE.write_text(json.dumps(
            {"by_bucket": self.by_bucket, "held_candidates": self.held_candidates}))

    def all_train_starts(self):
        out = []
        for v in self.by_bucket.values():
            out.extend(v)
        return out

    def held_shingles(self):
        sh = set()
        for s in self.held_candidates:
            toks = tuple(int(x) for x in self.data[s:s + CTX])
            for i in range(0, CTX - SHINGLE + 1):
                sh.add(toks[i:i + SHINGLE])
        return sh

    def touches_held(self, start, shingles):
        toks = tuple(int(x) for x in self.data[start:start + CTX])
        return any(toks[i:i + SHINGLE] in shingles for i in range(0, CTX - SHINGLE + 1))


class MixtureSampler:
    """Weighted draw over named start pools: [(pool_starts, weight), ...]."""

    def __init__(self, pools, rnd):
        self.pools = [(list(p), w) for p, w in pools if p and w > 0]
        self.rnd = rnd
        self.weights = [w for _, w in self.pools]

    def batch(self):
        out = []
        for pool, _ in self.rnd.choices(self.pools, weights=self.weights, k=BATCH):
            out.append(self.rnd.choice(pool))
        return out


# ----------------------------------------------------------------------------- training
def batch_tensor(data, starts):
    return torch.stack([torch.from_numpy(data[s:s + CTX + 1].astype("int64")) for s in starts])


def train_steps(model, trainer, data, sampler, steps, seed, flip_target=None):
    """Mirror of train.py's loop with a custom sampler. Returns flip stats.
    If flip_target is set, stop early once cumulative flip-events/weight >= target
    (round budgets are denominated in flips, per OVERLAP-DESIGN.md §3)."""
    rnd = random.Random(seed)
    losses, jumps = [], []
    n_pos = sum(t.numel() for t in trainer.t1)
    for step in range(steps):
        x = batch_tensor(data, sampler.batch())
        loss = F.cross_entropy(model.next_piece(x[:, :-1]).reshape(-1, VOCAB),
                               x[:, 1:].reshape(-1))
        losses.append(loss.item())
        jumps.append(trainer.step(loss, step / max(1, steps)))
        if flip_target and sum(jumps) * n_pos >= flip_target * n_pos:
            break
    return {"steps_done": len(jumps),
            "flip_share_total": round(sum(jumps), 5),
            "train_last100": round(sum(losses[-100:]) / max(1, len(losses[-100:])), 4)}


def fresh_member(shape, seed, ckpt=False):
    torch.manual_seed(seed)
    model = Tiny(layers=shape["layers"], dim=shape["dim"], rotary=True)
    model.ckpt = ckpt
    return model, Layered(model)


def served_states(trainer):
    return torch.cat([(t1 + t2).flatten() for t1, t2 in zip(trainer.t1, trainer.t2)])


def hamming(a, b):
    return round(float((a != b).float().mean()), 5)


def artifact_bytes(model):
    """Planning proxy for served-artifact size: serialized state_dict bytes.
    The frozen rule (design §6) is measured artifact size; the launch path must
    replace this with the real serializer once one exists, and the manifest
    records whichever was used."""
    buf = io.BytesIO()
    torch.save(model.state_dict(), buf)
    return buf.tell()


# ----------------------------------------------------------------------------- probing / exchange
@torch.no_grad()
def per_window_losses(model, data, starts):
    old = EASE[0]
    EASE[0] = 1.0
    model.eval()
    out = []
    for i in range(0, len(starts), BATCH):
        x = batch_tensor(data, starts[i:i + BATCH])
        logits = model.next_piece(x[:, :-1])
        ce = F.cross_entropy(logits.reshape(-1, VOCAB), x[:, 1:].reshape(-1),
                             reduction="none").reshape(x.shape[0], -1)
        out.extend(ce.mean(dim=1).tolist())
    model.train()
    EASE[0] = old
    return out


def build_exchange_sets(members, index, seed):
    """members: {name: model}. Returns {name: [starts]} of RELATIVE weaknesses:
    windows where the best other member beats this member by >= WEAK_MARGIN,
    near-duplicate-guarded against held windows. All-bad windows are excluded
    by construction (someone must be good at the window for it to qualify)."""
    rnd = random.Random(seed)
    shingles = index.held_shingles()
    pools = {}
    for bucket, starts in index.by_bucket.items():
        pools[bucket] = rnd.sample(starts, min(PROBE_CAP_PER_BUCKET, len(starts)))
    losses = {}
    for bucket, starts in pools.items():
        for name, model in members.items():
            losses.setdefault(name, {})[bucket] = per_window_losses(model, index.data, starts)
    exchange = {name: [] for name in members}
    for bucket, starts in pools.items():
        for j, s in enumerate(starts):
            per = {name: losses[name][bucket][j] for name in members}
            best_name = min(per, key=per.get)
            for name in members:
                if name != best_name and per[name] - per[best_name] >= WEAK_MARGIN:
                    if not index.touches_held(s, shingles):
                        exchange[name].append(s)
    return exchange


# ----------------------------------------------------------------------------- system reads
@torch.no_grad()
def ensemble_held(models, held):
    """Averaged-distribution read (label: len(models)x inference compute)."""
    old = EASE[0]
    EASE[0] = 1.0
    tot, n = 0.0, 0
    for m in models:
        m.eval()
    for i in range(0, len(held), BATCH):
        x = held[i:i + BATCH]
        probs = None
        for m in models:
            p = torch.softmax(m.next_piece(x[:, :-1]).float(), dim=-1)
            probs = p if probs is None else probs + p
        probs = probs / len(models)
        tot += F.nll_loss(torch.log(probs.reshape(-1, VOCAB)), x[:, 1:].reshape(-1),
                          reduction="sum").item()
        n += x[:, 1:].numel()
    for m in models:
        m.train()
    EASE[0] = old
    return round(tot / n, 4)


@torch.no_grad()
def router_held(models, data, held_starts_list, peek=32):
    """Router read: pick the member by loss on the first `peek` tokens; score is
    computed ONLY on positions after the peek (prefix-excluded, design §6)."""
    old = EASE[0]
    EASE[0] = 1.0
    for m in models:
        m.eval()
    tot, n = 0.0, 0
    for s in held_starts_list:
        x = batch_tensor(data, [s])
        losses = []
        for m in models:
            logits = m.next_piece(x[:, :-1])
            ce = F.cross_entropy(logits.reshape(-1, VOCAB), x[:, 1:].reshape(-1),
                                 reduction="none").reshape(-1)
            losses.append(ce)
        pick = int(torch.argmin(torch.stack([c[:peek].mean() for c in losses])))
        rest = losses[pick][peek:]
        tot += rest.sum().item()
        n += rest.numel()
    for m in models:
        m.train()
    EASE[0] = old
    return round(tot / n, 4)


# ----------------------------------------------------------------------------- records
def record(obj):
    obj = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), **obj}
    with RESULTS.open("a") as f:
        f.write(json.dumps(obj) + "\n")
    print(json.dumps(obj), flush=True)


def write_manifest(entries):
    MANIFEST.write_text(json.dumps({"entries": entries}, indent=1))
    tot = [e["bytes"] for e in entries]
    assert max(tot) / min(tot) <= 1.01 or len(set(tot)) == 1, "arm budgets differ by >1%"


# ----------------------------------------------------------------------------- phases
def tilt_sampler(index, tilt, rnd):
    return MixtureSampler([(index.all_train_starts(), UNIFORM_SHARE),
                           (index.by_bucket[tilt], 1.0 - UNIFORM_SHARE)], rnd)


def uniform_sampler(index, rnd):
    return MixtureSampler([(index.all_train_starts(), 1.0)], rnd)


def german_held_tensor(data, index):
    """Criterion 2's held slice: the tilt bucket's held candidates (aligned
    starts w*CTX, w % HELD_EVERY == 0) bucketed 'german' by bucket_of —
    40 windows on v1. Tensor built exactly as train.held_windows builds its 128."""
    starts = [s for s in index.held_candidates
              if bucket_of(np.asarray(data[s:s + CTX]))[0] == TILTS[0]]
    tensor = torch.stack([torch.from_numpy(data[s:s + CTX + 1].astype("int64"))
                          for s in starts])
    return tensor, len(starts)


def gate0(data, index, held, seeds=(0,), doses=(56, 168)):
    """OVERLAP-DESIGN.md §3: does tilt register in served states beyond seed noise?
    Criterion 2: the tilted arm must also beat uniform on its own bucket's held
    windows — measured live at each dose below, while the models are in scope.
    Corpus is v1 (decision 2026-11-12); every record carries "corpus": "v1"."""
    ger_held, n_ger = german_held_tensor(data, index)
    for seed in seeds:
        base = {}
        own = {}
        for tag, sampler_fn, sd in (("uniform", uniform_sampler, seed),
                                    ("tilted", None, seed),
                                    ("uniform_s2", uniform_sampler, seed + 1000)):
            model, trainer = fresh_member(SMOKE_SHAPE, sd)
            samp = sampler_fn(index, random.Random(sd)) if sampler_fn else \
                tilt_sampler(index, TILTS[0], random.Random(sd))
            prev = 0
            for dose in doses:
                st = train_steps(model, trainer, data, samp, dose - prev, sd)
                prev = dose
                base[(tag, dose)] = served_states(trainer)
                if tag in ("uniform", "tilted"):
                    own[(tag, dose)] = round(held_loss(model, ger_held), 4)
                record({"phase": "gate0", "corpus": "v1", "arm": tag, "seed": sd, "dose": dose, **st})
        for dose in doses:
            record({"phase": "gate0_pairs", "corpus": "v1", "seed": seed, "dose": dose,
                    "hamming_tilt_vs_uniform": hamming(base[("tilted", dose)], base[("uniform", dose)]),
                    "hamming_seed_noise": hamming(base[("uniform_s2", dose)], base[("uniform", dose)])})
            record({"phase": "gate0_held", "corpus": "v1", "seed": seed, "dose": dose,
                    "bucket": TILTS[0], "n_windows": n_ger,
                    "held_german_U": own[("uniform", dose)],
                    "held_german_T": own[("tilted", dose)]})
    # NOTE: doses are cumulative targets on one trajectory per arm
    # (train to 56, measure, continue to 168, measure) — a dose-response curve,
    # not independent runs. Hamming pairs are read off the same trajectory.


def smoke(data, index, held, seeds=(0,), steps1=56, steps2=14):
    """All arms at smoke scale. steps2 is a placeholder until Gate 0 sets the
    flip-denominated exchange dose (pass flip_target through train_steps)."""
    raise NotImplementedError(
        "smoke wiring is the launch task: build members per arm from the helpers "
        "above (tilt_sampler / uniform_sampler / build_exchange_sets), read with "
        "held_loss / ensemble_held / router_held, record per design §7. "
        "Do not improvise the win-condition bookkeeping — transcribe it from "
        "OVERLAP-DESIGN.md §6-§7.")


def dreaming_round(*_a, **_k):
    # TODO (design §5): only after exchange beats placebo. Failure windows seed
    # member-generated continuations; dream data tagged in records; never held.
    raise NotImplementedError("gated option — see OVERLAP-DESIGN.md §5")


# ----------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--launch", action="store_true",
                    help="actually run (default: print the plan and exit)")
    ap.add_argument("--phase", choices=["gate0", "smoke"], default="gate0")
    ap.add_argument("--seeds", type=int, nargs="+", default=[0])
    ap.add_argument("--steps1", type=int, default=56)
    ap.add_argument("--steps2", type=int, default=14)
    a = ap.parse_args()

    plan = {"phase": a.phase, "seeds": a.seeds, "shape": SMOKE_SHAPE,
            "tilts": TILTS, "results": str(RESULTS),
            "design": "scale-next/OVERLAP-DESIGN.md"}
    if not a.launch:
        print("NOT LAUNCHED (no --launch). Plan:")
        print(json.dumps(plan, indent=1))
        return

    data = np.memmap(LAB / "corpus.u16", dtype=np.uint16, mode="r")
    held = held_windows(data)
    index = WindowIndex(data)
    if a.phase == "gate0":
        gate0(data, index, held, seeds=tuple(a.seeds))
    else:
        smoke(data, index, held, seeds=tuple(a.seeds), steps1=a.steps1, steps2=a.steps2)


if __name__ == "__main__":
    main()
