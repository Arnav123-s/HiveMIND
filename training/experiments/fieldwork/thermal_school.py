"""Transfer candidate equation structures between independently calibrated instruments."""

import argparse
from collections import Counter
from pathlib import Path

import numpy as np

from .campaign import save
from .cases import make_thermal, response
from .discovery import columns, dictionary, drive, forecast, identify, raw_lags


def observe(world, u):
    return np.array(response(world, u, noisy=True))


def error(p, y):
    return float(np.sqrt(np.mean((np.array(p) - y) ** 2)) / max(0.15, np.std(y)))


def grow_school(u):
    terms = dictionary()
    index = {t[3]: i for i, t in enumerate(terms)}
    votes = Counter()
    for w in make_thermal(481993, 24):
        prediction, record = identify(u, observe(w, u), w[2])
        if error(prediction, response(w, w[2])) <= 0.10:
            votes[tuple(sorted(index[k] for k in record))] += 1
    return votes


def score_past(ids, u, y, X, terms):
    chosen = [terms[i] for i in ids]
    loss = []
    for stop in (len(u) * 2 // 3, len(u) * 4 // 5):
        weights = np.linalg.lstsq(X[:stop, ids], y[:stop], rcond=1e-8)[0]
        pred = forecast(chosen, weights, u, y[:stop])
        loss.append(np.mean((pred - y[stop:]) ** 2))
    return float(np.mean(loss)) + 0.00006 * len(ids)


def evaluate(u, school, worlds):
    terms = dictionary()
    index = {t[3]: i for i, t in enumerate(terms)}
    rng = np.random.default_rng(331921)
    random_bank = [
        tuple(sorted([0, *rng.choice(np.arange(1, len(terms)), len(s) - 1, replace=False).tolist()]))
        for s in school
    ]
    results = []
    for w in worlds:
        y = observe(w, u)
        truth = response(w, w[2])
        X = columns([raw_lags(y, u, t) for t in range(len(y))], terms)
        pred, record = identify(u, y, w[2])
        original = tuple(sorted(index[k] for k in record))
        outcomes = {"alone": error(pred, truth)}
        choices = {}
        for mode, bank in (
            ("memory", list(school)),
            ("memory_and_growth", [original, *school]),
            ("random_and_growth", [original, *random_bank]),
        ):
            best = min(bank, key=lambda ids: score_past(ids, u, y, X, terms))
            weights = np.linalg.lstsq(X[:, best], y, rcond=1e-8)[0]
            chosen = [terms[i] for i in best]
            outcomes[mode] = error(forecast(chosen, weights, w[2]), truth)
            choices[mode] = [s[3] for s in chosen]
        results.append(dict(family=w[0], errors=outcomes, chosen=choices))
    return results


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    u = drive(48)
    school = grow_school(u)
    if not school:
        raise ValueError("no verified structures")
    # New populations, distinct from the development class and both original field exams.
    scores = evaluate(u, school, [w for seed in (643973, 798593, 916613) for w in make_thermal(seed, 24)])
    archive = [
        dict(terms=[dictionary()[i][3] for i in ids], verified_instances=n) for ids, n in school.items()
    ]
    save(
        args.out,
        dict(teacher_seed=481993, exam_seeds=[643973, 798593, 916613], school=archive, rows=scores),
    )
    print({m: sum(r["errors"][m] <= 0.10 for r in scores) for m in scores[0]["errors"]})


if __name__ == "__main__":
    main()
