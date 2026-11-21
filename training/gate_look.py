"""An optional sequential look at complete fresh before/after grade artifacts.

Of paired tasks, let q be the discordance probability and p the child's conditional
win probability. Win/loss/tie probabilities are (q*p, q*(1-p), 1-q). Profiling q
under both p=.6 and p=.4 gives the same estimate, discordances / total pairs.
The resulting generalized log-likelihood ratio equals the conditional binomial one.
The two interim Wald boundaries have nominal alpha=beta=.05 under the working
independence model. Shared tasks and lineages can correlate outcomes.
"""
import argparse
import json
import math
import os
from pathlib import Path

from training import grow_record


def paired_log_lr(gained, lost):
    return (gained - lost) * math.log(0.6 / 0.4)


def decisive(gained, lost):
    return abs(paired_log_lr(gained, lost)) >= math.log(19)


def look(folder, run_number, seats):
    if seats not in (4, 6, 8):
        raise ValueError("paired gate requires four, six or eight seeds")
    expected = {f"gate-{arm}-{i}" for i in range(1, seats + 1) for arm in ("before", "after")}
    observed = {p.name for arm in ("before", "after") for p in folder.glob(f"gate-{arm}-*")}
    if observed != expected:
        return {"stop": False, "reason": "incomplete or unexpected grade shards"}
    for i in range(1, seats + 1):
        seed = 20_000_000 + run_number * 10 + i
        for arm in ("before", "after"):
            shard = folder / f"gate-{arm}-{i}"
            if list(shard.rglob("*.json")) != [shard / f"{seed}_mixed.json"]:
                return {"stop": False, "reason": "expected one fresh exam per shard"}
            sitting = next(grow_record._sittings(shard), None)
            if sitting is None:
                return {"stop": False, "reason": "invalid grade summary"}
            summary, tasks = sitting
            if summary.get("seed") != seed or summary.get("level") != "mixed" or summary["tasks"] != 8 or len(tasks) != 8:
                return {"stop": False, "reason": "incomplete or unexpected exam"}
    changes = grow_record.delivery_changes(folder)
    if changes["comparable"] != 8 * seats:
        return {"stop": False, "reason": "missing, duplicate or mismatched task identities"}
    counts = changes["counts"]
    gained, lost = counts["gained"], counts["lost"]
    return {"stop": seats < 8 and decisive(gained, lost), "seats": seats, "gained": gained, "lost": lost,
            "log_lr": round(paired_log_lr(gained, lost), 6)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grades", type=Path, required=True)
    parser.add_argument("--run-number", type=int, required=True)
    parser.add_argument("--seats", type=int, choices=[4, 6], required=True)
    args = parser.parse_args()
    result = look(args.grades, args.run_number, args.seats)
    message = json.dumps(result, sort_keys=True)
    print(message)
    if path := os.getenv("GITHUB_STEP_SUMMARY"):
        with open(path, "a") as f:
            print(message, file=f)
    if path := os.getenv("GITHUB_OUTPUT"):
        with open(path, "a") as f:
            print(f"stop={int(result['stop'])}", file=f)
