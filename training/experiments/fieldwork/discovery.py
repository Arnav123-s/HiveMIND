"""Small numerical specialists. Fit and select models on each instrument's own observations."""

import argparse
from pathlib import Path

import numpy as np


def drive(budget):
    rng = np.random.default_rng(1941)
    winner, best = None, -1
    for _ in range(80):
        u = rng.integers(-2, 3, budget).astype(float)
        raw = np.stack([u, np.roll(u, 1), np.roll(u, 2)], axis=1)[2:]
        cross = np.column_stack(
            (raw, abs(raw), raw**2, raw[:, 0] * raw[:, 1], raw[:, 0] * raw[:, 2], raw[:, 1] * raw[:, 2])
        )
        centered = cross - cross.mean(0)
        norm = np.linalg.norm(centered, axis=0)
        if norm.min() == 0:
            continue
        value = np.linalg.svd(centered / norm, compute_uv=False)[-1]
        if value > best:
            winner, best = u, value
    return winner.astype(int).tolist()


def raw_lags(y, u, t):
    return [y[t - i] if t >= i else 0 for i in (1, 2, 3)] + [
        u[t - i] if t >= i else 0 for i in (0, 1, 2, 3)
    ]


def dictionary():
    variables = ["y1", "y2", "y3", "u0", "u1", "u2", "u3"]
    terms = [("constant", 0, 0, "1")]
    for i, name in enumerate(variables):
        terms.extend(
            [("linear", i, i, name), ("absolute", i, i, "abs(" + name + ")"), ("square", i, i, name + "^2")]
        )
    for i in range(len(variables)):
        for j in range(i):
            terms.append(("product", i, j, variables[j] + "*" + variables[i]))
    return terms


def columns(raw, terms):
    x = np.asarray(raw)
    out = []
    for op, i, j, _ in terms:
        v = x[..., i]
        if op == "constant":
            v = np.ones_like(v)
        elif op == "absolute":
            v = np.abs(v)
        elif op == "square" or op == "product":
            v = v * x[..., j]
        out.append(v)
    return np.stack(out, axis=-1)


def forecast(terms, weights, u, observed=()):
    out = list(observed)
    for t in range(len(out), len(u)):
        with np.errstate(over="ignore", invalid="ignore"):
            value = float(columns(raw_lags(out, u, t), terms) @ weights)
        if not np.isfinite(value) or abs(value) > 1e5:
            return np.full(len(u) - len(observed), 1e5)
        out.append(value)
    return np.array(out[len(observed) :])


def paths(X, y, limit=12):
    ids = [0]
    for _ in range(limit):
        active = X[:, ids]
        coef = np.linalg.lstsq(active, y, rcond=1e-8)[0]
        yield ids.copy(), coef
        other = [j for j in range(X.shape[1]) if j not in ids]
        # Compare additional predictors after removing directions the selected terms already explain.
        residuals = X[:, other] - active @ np.linalg.lstsq(active, X[:, other], rcond=1e-8)[0]
        norm = np.linalg.norm(residuals, axis=0)
        gain = np.abs(residuals.T @ (y - active @ coef)) / np.maximum(norm, 1e-8)
        if gain.max() < 1e-8:
            return
        ids.append(other[int(np.argmax(gain))])


def identify(u, y, future, grow=True):
    y = np.asarray(y)
    terms = dictionary()
    X = columns([raw_lags(y, u, t) for t in range(len(y))], terms)
    if grow:
        # Estimate the useful number of terms on two earlier chronological splits. Each validation
        # trajectory rolls forward from its last observed state without reading later measurements.
        scores = []
        for end in (len(y) * 2 // 3, len(y) * 4 // 5):
            fold = []
            for ids, weights in paths(X[:end], y[:end]):
                predicted = forecast([terms[i] for i in ids], weights, u, y[:end])
                error = np.mean((predicted - y[end:]) ** 2)
                fold.append(float(error) + 0.00006 * len(ids))
            scores.append(fold)
        size = int(np.argmin(np.mean([s[: min(map(len, scores))] for s in scores], axis=0))) + 1
        candidates = list(paths(X, y))
        ids, weights = candidates[min(size, len(candidates)) - 1]
    else:
        ids = [0, 1, 10]  # constant, previous temperature, current drive
        weights = np.linalg.lstsq(X[:, ids], y, rcond=1e-8)[0]
    chosen = [terms[i] for i in ids]
    return forecast(chosen, weights, future).tolist(), {r[3]: float(w) for r, w in zip(chosen, weights)}


def seasonal(past, future, window, degree):
    past = np.asarray(past[-12 * window :], float)
    center = past[-1, 0] + (past[-1, 1] - 1) / 12

    def design(rows):
        rows = np.asarray(rows, float)
        t = rows[:, 0] + (rows[:, 1] - 1) / 12 - center
        cols = [np.ones_like(t), t] + ([t * t] if degree == 2 else [])
        return np.column_stack(cols + [rows[:, 1] == m for m in range(2, 13)])

    coef = np.linalg.lstsq(design(past), past[:, 2], rcond=None)[0]
    pred = design(future) @ coef
    offsets = [0] + list(coef[degree + 1 :])
    return pred, float(coef[1]), int(np.argmax(offsets)) + 1


def atmosphere(x, choose=True):
    history, future = x["history"], x["future"]
    scored = []
    for window in (5, 10, 15):
        for degree in (1, 2):
            errors = []
            for hold in (24, 36, 48, 60):
                cutoff = len(history) - hold
                test = history[cutoff : cutoff + 24]
                pred, _, _ = seasonal(history[:cutoff], test, window, degree)
                errors.extend(np.array([r[2] for r in test]) - pred)
            scored.append((float(np.sqrt(np.mean(np.square(errors)))), window, degree))
    rank, window, degree = min(scored) if choose else next(k for k in scored if k[1:] == (10, 1))
    predicted, _, _ = seasonal(history, future, window, degree)
    _, slope, peak = seasonal(history, future, 10, 1)
    return dict(
        forecast=predicted.tolist(),
        trend=slope,
        peak_month=peak,
        validation_rmse=rank,
        method=f"Calendar-month offsets and polynomial degree {degree}, {window}-year window; ten-year linear slope and seasonal peak.",
    )


class Scientist:
    def __init__(self, grow=True, excite=True):
        self.grow, self.excite = grow, excite
        self.models = []

    def run(self, name, inputs, fuel=None):
        rows = []
        for x in inputs:
            if name == "climate":
                val = atmosphere(x, self.grow)
                self.models.append({k: v for k, v in val.items() if k != "forecast"})
            elif x["phase"] == "design":
                val = drive(x["budget"]) if self.excite else [i % 5 - 2 for i in range(x["budget"])]
            else:
                val, model = identify(x["u"], x["y"], x["future"], self.grow)
                self.models.append(model)
            rows.append({"value": val})
        return rows, 0, 0


def main():
    from .campaign import save
    from .grade import grade

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--split", choices=("public", "exam", "confirmation"), required=True)
    args = p.parse_args()
    for name in ("thermal", "climate"):
        for label, grow, excite in (
            ("fixed", False, True),
            ("growth", True, True),
            ("periodic", True, False),
        ):
            if name == "climate" and label == "periodic":
                continue
            s = Scientist(grow, excite)
            res = grade(s, name, name, args.split)
            save(args.out / args.split / (name + "-" + label + ".json"), dict(models=s.models, **res))
            print(name, label, res["correct"], res["total"], flush=True)


if __name__ == "__main__":
    main()
