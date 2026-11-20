"""Reproduce the registered 2 x 2 experiment on frozen native endpoint states, using one CPU thread."""
import os
for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[variable] = "1"

import argparse
from hashlib import sha256
import json
import platform
from statistics import median
import sys
from time import process_time

import numpy as np

from data import HERE, ROOT, REPORT, load
sys.path.insert(0, str(ROOT))
from training import merge

RANK = 4
HEAD = "output"
ARMS = [(keep, pull) for keep in (1.0, 0.5) for pull in (0.5, 0.1)]


def matrix(edit):
    a, b = edit[HEAD]
    return b.astype(np.float64) @ a.astype(np.float64)


class Study:
    def __init__(self):
        self.rows, self.x, self.tokens, self.base, self.other, self.outside_id, self.outside_word = load()
        self.domains = sorted({r.domain for r in self.rows})
        self.cols = {d: sorted({int(np.searchsorted(self.tokens, r.token)) for r in self.rows if r.domain == d and r.split == "train"})
                     for d in self.domains}
        self.gold = np.searchsorted(self.tokens, [r.token for r in self.rows])
        self.words = {r.token: r.label.casefold() for r in self.rows if r.split == "train"}
        self.train = [i for i, r in enumerate(self.rows) if r.split == "train"]
        self.test = [i for i, r in enumerate(self.rows) if r.split != "train"]
        self.empty = {HEAD: (np.zeros((RANK, 4096), np.float32), np.zeros((len(self.tokens), RANK), np.float32))}

    def margins(self, ix):
        scores = self.base[ix].copy()
        gold = self.gold[ix]
        scores[np.arange(len(ix)), gold] = -np.inf
        return np.maximum(self.other[ix], scores.max(axis=1)) - self.base[ix, gold]

    def schedule(self, keep):
        jobs = [{d: [] for d in self.domains} for _ in range(3)]
        for j, domain in enumerate(self.domains):
            for k, col in enumerate(self.cols[domain]):
                ix = [i for i in self.train if self.rows[i].domain == domain and self.gold[i] == col]
                if keep < 1:
                    ix = [i for _, i in sorted(zip(-self.margins(ix), ix),
                                                key=lambda entry: (entry[0], self.rows[entry[1]].key))[:len(ix) // 2]]
                jobs[(j + k) % 3][domain] = ix
        return jobs

    def fit(self, initial, ix, cols):
        x = self.x[ix]
        norms = np.linalg.norm(x, axis=1)
        unit = x / norms[:, None]
        target = np.zeros((len(ix), len(cols)))
        target[np.arange(len(ix)), np.searchsorted(cols, self.gold[ix])] = np.maximum(0, self.margins(ix) + 6)
        a, b = initial[HEAD]
        residual = target - (x @ a.T) @ b[cols].T
        dual = np.linalg.solve(unit @ unit.T + 0.1 * np.eye(len(ix)), residual)
        new_b = np.zeros((len(self.tokens), len(ix)))
        new_b[cols] = dual.T
        update = {HEAD: (unit / np.median(norms), new_b)}
        return merge.merge([initial, update], [1, 1], rank=RANK, normalize=False)[0]

    def train_arm(self, keep, pull):
        start = process_time()
        jobs = self.schedule(keep)
        scheduling = process_time() - start
        fitting = 0.0
        locals_ = {d: self.empty for d in self.domains}
        trunk = self.empty
        history = []
        for round_jobs in jobs:
            children = {}
            for d in self.domains:
                initial, _ = merge.merge([locals_[d], trunk], [1 - pull, pull], rank=RANK)
                t = process_time()
                children[d] = self.fit(initial, round_jobs[d], self.cols[d])
                fitting += process_time() - t
            locals_ = children
            trunk, _ = merge.merge(list(locals_.values()), rank=RANK)
            history.append((locals_, trunk))
        migrants = {d: merge.merge([local, trunk], [0.5, 0.5], rank=RANK)[0] for d, local in locals_.items()}
        history.append((migrants, trunk))
        return history, {"total": process_time() - start, "fit": fitting, "schedule": scheduling}

    def score(self, head, *, by_domain=False, detail=False):
        predictions = []
        for i in self.test:
            r = self.rows[i]
            a, b = (head[r.domain] if by_domain else head)[HEAD]
            new = self.base[i] + (self.x[i] @ a.T) @ b.T
            j = int(new.argmax())
            token = int(self.tokens[j])
            if self.other[i] > new[j] or (self.other[i] == new[j] and self.outside_id[i] < token):
                token, word = int(self.outside_id[i]), str(self.outside_word[i])
            else:
                word = self.words[token]
            predictions.append({"key": r.key, "token": token, "word": word, "ok": word == r.label.casefold(),
                                "exact": token == r.token, "split": r.split, "domain": r.domain})
        def count(group):
            return sum(p["ok"] for p in group)
        result = {s: count([p for p in predictions if p["split"] == s]) for s in ("anchor", "held")}
        result.update(total=count(predictions), canonical=sum(p["exact"] for p in predictions),
                      by_domain={d: count([p for p in predictions if p["domain"] == d]) for d in self.domains})
        if detail:
            result["cases"] = predictions
        return result

    def merge_controls(self, locals_):
        heads = list(locals_.values())
        mats = np.array([matrix(h) for h in heads])
        flat = mats.reshape(len(mats), -1)
        magnitudes = np.linalg.norm(flat, axis=1)
        dots = (flat @ flat.T) / np.outer(magnitudes, magnitudes)
        cosines = dots[np.triu_indices(len(mats), 1)]
        result = {"pairwise_cosines": cosines.tolist(), "negative_pairs": int(sum(cosines < -1e-8))}
        for label, signs in (("mean", [1] * len(heads)), ("signed", [1, -1] * (len(heads) // 2))):
            exact = np.average(mats * np.array(signs)[:, None, None], axis=0)
            energy = np.linalg.svd(exact, compute_uv=False) ** 2
            tests = {}
            for rank in (1, 4, 8, 16, 32):
                signed = [{HEAD: (h[HEAD][0], s * h[HEAD][1])} for h, s in zip(heads, signs)]
                merged, share = merge.merge(signed, rank=rank)
                expected = energy[:rank].sum() / energy.sum()
                assert abs(share - expected) < 1e-6
                error = np.linalg.norm(exact - matrix(merged)) / np.linalg.norm(exact)
                if rank == 32:
                    assert error < 1e-5
                tests[str(rank)] = dict(energy=round(share, 8), relative_error=float(error),
                                        **self.score(merged, detail=rank == 4))
            result[label] = dict(singular_energy=energy.tolist(), cuts=tests,
                                 squared_norm_fraction=float((np.linalg.norm(exact) / magnitudes.mean()) ** 2))
        return result

    def diagnostics(self, keep, pull, times):
        history, _ = self.train_arm(keep, pull)
        jobs = self.schedule(keep)
        rounds = []
        for i, (locals_, trunk) in enumerate(history):
            rounds.append(dict(stage=f"generation-{i + 1}" if i < 3 else "migration",
                               local=self.score(locals_, by_domain=True, detail=i >= 2),
                               trunk=self.score(trunk, detail=i == 2)))
        return dict(keep=keep, pull=pull, rows=sum(len(ix) for rnd in jobs for ix in rnd.values()),
                    training_ids=[{d: [self.rows[i].key for i in rnd[d]] for d in self.domains} for rnd in jobs],
                    cpu_median_s={k: median(t[k] for t in times) for k in times[0]}, cpu_runs_s=times,
                    rounds=rounds, merge=self.merge_controls(history[2][0]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=HERE / "results.json")
    args = parser.parse_args()
    study = Study()
    clocks = {arm: [] for arm in ARMS}
    for arm in ARMS:
        study.train_arm(*arm)
    for rep in range(9):
        offset = rep % len(ARMS)
        for arm in ARMS[offset:] + ARMS[:offset]:
            _, costs = study.train_arm(*arm)
            clocks[arm].append(costs)
    pooled = study.fit(study.empty, study.train, list(range(len(study.tokens))))
    files = [HERE / name for name in ("run.py", "protocol.md", "data.py", "cached-endpoints.npz")]
    files += [ROOT / "training/merge.py", REPORT / "exercises.json", REPORT / "training-states.npz"]
    for d in ("water-v2", "timing-v2"):
        files.extend([REPORT / d / "training-states.npz", REPORT / d / "exercises.json"])
    result = dict(trainer="frozen raw model endpoint, sparse output head", numpy=np.__version__, python=sys.version,
                  platform=platform.platform(), cpu_model=next((line.split(":", 1)[1].strip() for line in
                  open("/proc/cpuinfo") if line.startswith("model name")), None),
                  inputs={str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest() for p in files},
                  rows={r.key: {"domain": r.domain, "split": r.split, "gold": r.label} for r in study.rows},
                  bare=study.score(study.empty, detail=True), pooled=study.score(pooled, detail=True),
                  arms=[study.diagnostics(*arm, clocks[arm]) for arm in ARMS])
    with open(args.out, "w") as f:
        json.dump(result, f, separators=(",", ":"), allow_nan=False)
        f.write("\n")


if __name__ == "__main__":
    main()
