"""Repair misleading continual rewards with a fixed budget of delayed independent outcome checks."""
import argparse
import json
from collections import deque
from pathlib import Path

import numpy as np
import torch

from training.experiments.engram_distill import replay
from training.experiments.hive_continual_reward import DELAY, LEGACY, PROBE_COST, WINDOW, world


BLOCK = 8
METHODS = ("trust_primary", "replace_on_audit", "quarantine_uniform", "quarantine_targeted", "two_rate_targeted")


def play(data, seed, method, faulty, noisy):
    stations, _, predictions, truth, *_ = data
    n = len(stations)
    rng = np.random.default_rng(seed + 90000)
    corrupt_site = int(rng.integers(2))
    favored = 1 - LEGACY[corrupt_site]
    # One audit per block in every arm. All policies share the noise and initial sampling schedule.
    offsets = rng.integers(BLOCK, size=n // BLOCK)
    flips = rng.random(n) < (0.03 if noisy else 0.)
    owners, epochs = LEGACY.copy(), np.zeros(4, dtype=int)
    drift, distrust = np.zeros(4), np.zeros(4)
    flagged = np.zeros(4, dtype=bool)
    pending = deque()
    correct, reported, audits = [], [], []
    detected_at = None
    for t, site in enumerate(stations):
        if t % BLOCK == 0:
            used = False
        if method in ("quarantine_targeted", "two_rate_targeted") and flagged.any():
            audit = not used and (flagged[site] or t % BLOCK == BLOCK - 1)
        else:
            audit = not used and (t % BLOCK == offsets[t // BLOCK] or t % BLOCK == BLOCK - 1)
        used |= audit
        chosen = owners[site]
        passed = bool(predictions[t, chosen] == truth[t])
        primary = True if faulty and site == corrupt_site and t >= WINDOW and chosen == favored else passed
        witness = bool(passed ^ flips[t]) if audit else None
        correct.append(passed)
        reported.append(primary)
        audits.append(audit)
        pending.append((site, epochs[site], primary, witness))
        if len(pending) <= DELAY:
            continue
        s, epoch, observed, checked = pending.popleft()
        if checked is not None and method in METHODS[2:]:
            if method == "two_rate_targeted":
                # Compare 3% normal disagreement with 30% for a failing verifier.
                delta = np.log(0.30 / 0.03) if observed != checked else np.log(0.70 / 0.97)
                distrust[s] = max(0., distrust[s] + delta)
                flagged[s] |= distrust[s] > 4
            else:
                flagged[s] |= observed != checked
            if flagged[corrupt_site] and detected_at is None:
                detected_at = t
        if epochs[s] != epoch or (flagged[s] and checked is None):
            continue
        reward = observed if checked is None or method == "trust_primary" else checked
        delta = np.log(0.55 / 0.90) if reward else np.log(0.45 / 0.10)
        drift[s] = max(0., drift[s] + delta)
        if drift[s] > 4:
            owners[s] = 1 - owners[s]
            epochs[s] += 1
            drift[s] = 0
    if sum(audits) != n // BLOCK:
        raise RuntimeError("audit budget changed")
    returned = (np.arange(n) // WINDOW == 2) & (stations == corrupt_site)
    return {"true_pass": float(np.mean(correct)), "reported_pass": float(np.mean(reported)),
            "net": float(np.mean(correct) - PROBE_COST * np.mean(audits)), "audits": int(sum(audits)),
            "fault_site_after_return": float(np.array(correct)[returned].mean()),
            "fault_site_reported_after_return": float(np.array(reported)[returned].mean()),
            "flagged_healthy_stations": int(flagged.sum() - (int(flagged[corrupt_site]) if faulty else 0)),
            "flag_time_in_stream": detected_at, "fault_site": corrupt_site}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--memory", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    torch.set_num_threads(1)
    model = replay(args.memory.read_bytes())
    result = {}
    for seed in range(1721, 1745):
        data = world(model, seed)
        result[seed] = {k: {m: play(data, seed, m, f, noise) for m in METHODS}
                        for k, f, noise in (("clean", False, False), ("biased", True, False),
                                            ("noisy_audit", False, True), ("both_faults", True, True))}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
