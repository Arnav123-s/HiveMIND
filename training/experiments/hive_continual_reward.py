"""Delayed-reward continual routing among two learned sensory skills, with an optional probe."""
import argparse
import json
from collections import deque
from pathlib import Path

import numpy as np
import torch

from training.experiments.engram_distill import replay
from training.experiments.engram_halves import measurements


WINDOW = 256
DELAY = 8
PROBE_COST = 0.12
EXPLORE = 0.12
LEGACY = np.array([0, 1, 0, 1])
POLICIES = ("frozen", "always_probe", "lifetime_mean", "recent", "recent_wrong_receipt", "policy_gradient",
            "drift_switch", "oracle")


@torch.no_grad()
def world(model, seed):
    rng = np.random.default_rng(seed)
    n = WINDOW * 4
    stations = rng.integers(0, 4, n)
    role = LEGACY[stations].copy()
    phase = np.arange(n) // WINDOW
    changed = (phase == 1) & (stations < 2)
    role[changed] = 1 - role[changed]
    volatile = (phase == 3) & (stations < 2)
    role[volatile] = rng.integers(0, 2, sum(volatile))
    x, labels = measurements(n * 2, seed + 80000)
    pred = (model(x) > 0).numpy()
    y = labels.numpy()[np.arange(n * 2), np.tile(role, 2)]
    return stations, role, pred[:n], y[:n], pred[n:], y[n:], rng.random((n, 2))


def choose(method, station, values, logits, rnd):
    default = int(LEGACY[station])
    if method == "frozen":
        return default, default, None
    if method == "always_probe":
        return 2, default, None
    if method == "policy_gradient":
        raw = np.exp(logits[station] - logits[station].max())
        pi = raw / raw.sum()
        behavior = (1 - EXPLORE) * pi + EXPLORE / 3
        action = min(2, int(np.searchsorted(behavior.cumsum(), rnd[0])))
        # Gradient of the probability actually used, including uniform exploration.
        grad = -pi.copy()
        grad[action] += 1
        grad *= (1 - EXPLORE) * pi[action] / behavior[action]
        return action, int(np.argmax(logits[station, :2])), grad
    action = int(rnd[1] * 3) if rnd[0] < EXPLORE else int(np.argmax(values[station]))
    return action, int(np.argmax(values[station, :2])), None


def play(data, method, faulty):
    stations, roles, pred, truth, witness_pred, witness_truth, dice = data
    values = np.full((4, 3), 0.55)
    values[:, 2] = 0.68
    values[np.arange(4), LEGACY] = 0.8
    counts = np.full((4, 3), 2)
    logits = (values - 0.65) * 6
    baseline = np.full(4, 0.75)
    pending = deque()
    owner = LEGACY.copy()
    epoch = np.zeros(4, dtype=int)
    evidence = np.zeros(4)
    record = []
    for t, station in enumerate(stations):
        if method == "oracle":
            action, fallback, grad = int(roles[t]), 0, None
        elif method == "drift_switch":
            action, fallback, grad = int(owner[station]), 0, None
        else:
            action, fallback, grad = choose(method, station, values, logits, dice[t])
        probe = action == 2
        selected = action
        if probe:
            matches = np.flatnonzero(witness_pred[t] == witness_truth[t])
            selected = int(matches[0]) if len(matches) == 1 else fallback
        correct = float(pred[t, selected] == truth[t])
        observed = 1. if faulty and t >= WINDOW and station == 0 and selected == 1 else correct
        cost = PROBE_COST * probe
        record.append((correct, observed, float(probe), correct - cost, observed - cost))
        pending.append((station, action, observed - cost, grad, baseline[station], epoch[station]))
        if len(pending) > DELAY:
            s, a, r, g, old_baseline, assigned_epoch = pending.popleft()
            if method == "recent_wrong_receipt":
                s, a = station, action
            if method in ("lifetime_mean", "recent", "recent_wrong_receipt"):
                counts[s, a] += 1
                rate = 1. / counts[s, a] if method == "lifetime_mean" else 0.16
                values[s, a] += rate * (r - values[s, a])
            elif method == "policy_gradient":
                logits[s] += 0.22 * (r - old_baseline) * g
                baseline[s] += 0.08 * (r - baseline[s])
            elif method == "drift_switch" and epoch[s] == assigned_epoch:
                # Sequential evidence for a pass rate declining from 0.90 to 0.55.
                # Old-owner rewards are still in the history but cannot flip a newer assignment.
                increment = np.log(0.55 / 0.9) if r else np.log(0.45 / 0.1)
                evidence[s] = max(0., evidence[s] + increment)
                if evidence[s] > 4.:
                    owner[s] = 1 - owner[s]
                    epoch[s] += 1
                    evidence[s] = 0.
    array = np.asarray(record)
    def average(part):
        return dict(zip(("pass", "reported_pass", "probe_rate", "net", "reported_net"), array[part].mean(0).tolist()))
    return {"all": average(slice(None)), "phases": [average(slice(i * WINDOW, (i + 1) * WINDOW)) for i in range(4)],
            "first_32_after_change": average(slice(WINDOW, WINDOW + 32)),
            "last_32_before_return": average(slice(2 * WINDOW - 32, 2 * WINDOW)),
            "fault_site_after_return": average((np.arange(len(stations)) // WINDOW == 2) & (stations == 0))}


def summarize(streams, case):
    rng = np.random.default_rng(729)
    draws = rng.integers(0, len(streams), (2000, len(streams)))
    out = {}
    for method in POLICIES:
        trials = [stream[case][method] for stream in streams]
        def means(rows):
            return {k: float(np.mean([r[k] for r in rows])) for k in rows[0]}
        row = {k: means([r[k] for r in trials]) for k in ("all", "first_32_after_change", "last_32_before_return",
                                                            "fault_site_after_return")}
        row["phases"] = [means([r["phases"][i] for r in trials]) for i in range(4)]
        diffs = np.array([s[case][method]["all"]["net"] - s[case]["frozen"]["all"]["net"] for s in streams])
        row["net_minus_frozen"] = float(diffs.mean())
        row["paired_stream_bootstrap_95"] = np.quantile(diffs[draws].mean(1), [0.025, 0.975]).tolist()
        out[method] = row
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--memory", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--first-seed", type=int, default=811)
    args = p.parse_args()
    torch.set_num_threads(1)
    model = replay(args.memory.read_bytes())
    seeds = list(range(args.first_seed, args.first_seed + 24))
    out = {"seeds": seeds, "tasks_per_stream": 4 * WINDOW, "phase_length": WINDOW,
           "reward_delay": DELAY, "extra_probe_cost": PROBE_COST, "exploration": EXPLORE, "per_seed": {}}
    for seed in seeds:
        data = world(model, seed)
        out["per_seed"][seed] = {case: {k: play(data, k, faulty) for k in POLICIES}
                                 for case, faulty in (("clean", False), ("faulty_verifier", True))}
    out["summary"] = {case: summarize(list(out["per_seed"].values()), case) for case in ("clean", "faulty_verifier")}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2) + "\n")
    for k in POLICIES:
        print(k, round(np.mean([s["clean"][k]["all"]["net"] for s in out["per_seed"].values()]), 4))


if __name__ == "__main__":
    main()
