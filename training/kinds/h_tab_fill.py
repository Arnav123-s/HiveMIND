"""The kind h_tab_fill: the blank values of a CSV given in the task filled by a rule (hard: tables).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import datetime
import re

from training import hive_bench as B
from training.kinds._common import _fill, _says
from training.kinds import _tab

KIND = "h_tab_fill"
FAMILY = "hard: tables"
HARD = True
ORDER = 330

# (file, the column of who measures, its values, the column measured, its range)
THEMES = [("readings.csv", "sensor", ["s1", "s2", "s3", "s4"], "temp", (-50, 300)),
          ("levels.csv", "tank", ["A", "B", "C", "D"], "litres", (100, 900)),
          ("weights.csv", "pen", ["north", "south", "east"], "kg", (200, 600))]


def h_tab_fill(r):
    name, who, values, col, (lo, hi) = r.choice(THEMES)
    out = r.choice(["filled.csv", "complete.csv", "clean.csv"])
    keys = r.sample(values, r.randrange(2, len(values) + 1))
    start = datetime.date(2026, r.randrange(1, 13), r.randrange(1, 20))
    days = r.randrange(4, 7)
    rows = []
    for d in range(days):
        for k in keys:
            rows.append([k, (start + datetime.timedelta(days=d)).isoformat(), f"{r.randrange(lo, hi) / 10:.1f}"])
    blanks = r.sample(range(len(rows)), max(2, len(rows) // 4))
    for i in blanks:
        rows[i][2] = ""
    for k in keys:  # a key with no value at all has nothing to fill from: its last day is given
        if not any(x[2] for x in rows if x[0] == k):
            last = max(i for i, x in enumerate(rows) if x[0] == k)
            rows[last][2] = f"{r.randrange(lo, hi) / 10:.1f}"
    filled = [list(x) for x in rows]
    for k in keys:
        mine = [x for x in filled if x[0] == k]
        known = None
        for x in mine:  # the last value before it
            known = x[2] = x[2] or known
        later = None
        for x in reversed(mine):  # none before: the first one after it
            later = x[2] = x[2] or later
    n = sum(1 for x in rows if not x[2])
    text = f"{who},day,{col}\n" + "\n".join(",".join(x) for x in rows)

    def check(run, report):
        got = _tab.rows(run, out)
        if got is None:
            return False, f"no {out} saved"
        ok = (_tab.head(got, [who, "day", col]) and len(got) == len(filled) + 1
              and all(g[:2] == w[:2] and len(g) == 3 and _tab.near(g[2], float(w[2]), 0.001) for g, w in zip(got[1:], filled))
              and _says(B._body(report), n, 0.1))
        return ok, f"{out}: {len(got) - 1} rows against {len(filled)}, {n} filled in the answer: {ok}"
    return ("hard: tables", "the blanks of a table filled by a rule", _tab.given(name, text,
            f"Some {col} values are blank. Save a file {out} with the same rows in the same order, each blank {col} filled with the last "
            f"{col} of the same {who} on an earlier day, or, where that {who} has none earlier, with its first {col} on a later day. "
            "Then tell me how many values you filled."), check)


def fill(task):
    m = re.search(r"Here is the file (\S+):\n(\w+),day,(\w+)\n.+Save a file (\S+) with the same rows", task, re.S)
    if not m:
        return None
    return _fill('''import csv

rows = list(csv.DictReader(open(__NAME__)))
key, col = __KEY__, __COLUMN__
blank = sum(1 for row in rows if not row[col])
for late_first in (False, True):  # the last value before; then, for what is still blank, the first after
    known = {}
    for row in sorted(rows, key=lambda x: x["day"], reverse=late_first):
        row[col] = row[col] or known.get(row[key], "")
        known[row[key]] = row[col]
with open(__OUT__, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=[key, "day", col])
    w.writeheader()
    w.writerows(rows)
print(__OUT__, "saved")
print("filled:", blank)
''', name=m.group(1), key=m.group(2), column=m.group(3), out=m.group(4))


make = h_tab_fill
lesson = fill
