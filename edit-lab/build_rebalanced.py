#!/usr/bin/env python3
"""Build a rebalanced coordinator training file from the original data.

Original: 38 examples; 19 are 2-step plans, but the coordinator eval's
size check requires 3-7 steps, so the original edit overfit to short
plans. Rebalance: keep every >=3-step example twice (oversampled), keep
only 4 of the 2-step examples once. No text is edited; examples are
verbatim copies of the originals.

Output: edit-lab/data/coordinator_rebalanced.jsonl (42 rows)
"""
import json
import re
from pathlib import Path

src = Path("~/workspace/edit-lab/tree/training/data/coordinator.jsonl").expanduser()
rows = [json.loads(l) for l in open(src) if l.strip()]


def n_steps(row):
    try:
        return len(json.loads(row["output"])["steps"])
    except Exception:
        return len(re.findall(r'"agent"\s*:', row.get("output", "")))


long_rows = [r for r in rows if n_steps(r) >= 3]
short_rows = [r for r in rows if n_steps(r) < 3]
out = long_rows * 2 + short_rows[:4]
out_path = Path("~/workspace/edit-lab/data/coordinator_rebalanced.jsonl").expanduser()
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w") as f:
    for r in out:
        f.write(json.dumps(r) + "\n")
from collections import Counter

print("original:", len(rows), Counter(n_steps(r) for r in rows))
print("rebalanced:", len(out), Counter(n_steps(r) for r in out))
print("wrote", out_path)
