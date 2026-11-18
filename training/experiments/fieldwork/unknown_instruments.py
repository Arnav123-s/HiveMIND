"""Test an experimenter that may add a state variable, validate a new mechanism, or withhold a forecast."""

import argparse
from pathlib import Path

import numpy as np

from .campaign import save
from .discovery import drive
from .thermal_school import error


def state_path(u, low, high):
    state = 0
    states = []
    for v in u:
        if v >= high:
            state = 1
        elif v <= low:
            state = 0
        states.append(state)
    return np.array(states)


def measure(device, u, rng, noise):
    a, b, gain, low, high, kind = device
    reg = state_path(u, low, high) if kind == "latch" else np.zeros(len(u))
    if kind == "external":
        # An independent, unmeasured offset is redrawn after each reset.
        reg = rng.choice([-1, 1], len(u))
    val = 0.0
    y = []
    for v, s in zip(u, reg):
        val = a * val + b * v + gain * s
        y.append(val + (rng.normal(0, 0.012) if noise else 0))
    return np.array(y)


def fit(u, y, gate):
    cols = [np.ones(len(u)), np.r_[0.0, y[:-1]], u]
    if gate is not None:
        cols.append(state_path(u, *gate))
    return np.linalg.lstsq(np.column_stack(cols), y, rcond=None)[0]


def project(u, weights, gate):
    modes = state_path(u, *gate) if gate is not None else np.zeros(len(u))
    val = 0.0
    out = []
    for v, s in zip(u, modes):
        val = weights[0] + weights[1] * val + weights[2] * v + (weights[3] * s if gate is not None else 0)
        out.append(val)
    return np.array(out)


def run(seed=447711):
    rng = np.random.default_rng(seed)
    initial = drive(48)
    # Long zero-input runs inspect whether a past excitation persists after its direct thermal effect decays.
    audit = [-2, 0, 0, 0, 0, 1, 0, 0, 2, 0, 0, 0, 0, -1, 0, 0, 1, -2, 1, 0, 2, 0, -1, 0]
    gates = [(a, b) for a in (-2, -1, 0) for b in (0, 1, 2) if a < b]
    rows = []
    for i in range(90):
        kind = ("linear", "latch", "external")[i % 3]
        low, high = gates[int(rng.integers(len(gates)))]
        dev = (rng.uniform(0.3, 0.75), rng.uniform(0.38, 0.8), rng.uniform(1.3, 2.4), low, high, kind)
        future = rng.integers(-2, 3, 60).tolist()
        train = measure(dev, initial, rng, True)
        second = measure(dev, audit, rng, True)
        truth = measure(dev, future, rng, False)
        candidates = []
        for gate in [None, *gates]:
            weights = fit(initial, train, gate)
            validation = error(project(audit, weights, gate), second)
            candidates.append((validation + (0.003 if gate is not None else 0), validation, gate, weights))
        methods = {}
        for method, row in (("fixed", candidates[0]), ("expanded", min(candidates, key=lambda c: c[0]))):
            _, valid, gate, weights = row
            private = error(project(future, weights, gate), truth)
            methods[method] = dict(
                gate=gate,
                validation=valid,
                nrmse=private,
                issued=bool(valid <= 0.10),
                correct_if_issued=bool(valid <= 0.10 and private <= 0.10),
            )
        rows.append(dict(kind=kind, true_gate=[low, high] if kind == "latch" else None, methods=methods))
    return dict(seed=seed, initial_drive=initial, independent_audit=audit, threshold=0.10, rows=rows)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    result = run()
    save(args.out, result)
    for method in ("fixed", "expanded"):
        print(
            method,
            [
                (
                    kind,
                    sum(r["methods"][method]["issued"] for r in result["rows"] if r["kind"] == kind),
                    sum(
                        r["methods"][method]["correct_if_issued"]
                        for r in result["rows"]
                        if r["kind"] == kind
                    ),
                )
                for kind in ("linear", "latch", "external")
            ],
        )


if __name__ == "__main__":
    main()
