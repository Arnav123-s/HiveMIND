"""An optional sequential look at complete fresh before/after grade artifacts.

After four and six seeds, compare P(child wins | discordant)=.6 against .4.
The paired Wald threshold assumes independent discordant outcomes. Shared exam kinds
can violate that assumption; the ordinary full parallel gate remains available.
"""
import argparse
import json
import math
import os
from pathlib import Path

from training import grow_record


def decisive(gained, lost):
    return abs(gained - lost) * math.log(1.5) >= math.log(19)


def look(folder, run_number, seats):
    if seats not in (4, 6):
        raise ValueError("look requires four or six seeds")
    expected = {f"gate-{arm}-{i}" for i in range(1, seats + 1) for arm in ("before", "after")}
    if {p.name for p in folder.glob("gate-*")} != expected:
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
    return {"stop": decisive(gained, lost), "seats": seats, "gained": gained, "lost": lost}


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
