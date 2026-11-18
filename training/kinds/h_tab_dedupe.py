"""The kind h_tab_dedupe: a CSV given in the task cut to one row a key, the row of the latest date kept (hard: tables).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import datetime
import re

from training import hive_bench as B
from training.kinds._common import _fill, _says, HARD_NAMES as NAMES
from training.kinds import _tab

KIND = "h_tab_dedupe"
FAMILY = "hard: tables"
HARD = True
ORDER = 320

# (file, the key column, its prefix, the column that changes, its values)
THEMES = [("customers.csv", "id", "C", "plan", ["free", "basic", "pro", "team"]),
          ("devices.csv", "serial", "D", "status", ["active", "repair", "spare", "retired"]),
          ("members.csv", "member", "M", "level", ["bronze", "silver", "gold"])]


def h_tab_dedupe(r):
    name, key, prefix, col, values = r.choice(THEMES)
    date_col = r.choice(["updated", "changed", "date"])
    out = r.choice(["latest.csv", "current.csv", "deduped.csv"])
    ids = sorted(r.sample(range(100, 1000), r.randrange(5, 9)))
    start = datetime.date(2025, r.randrange(1, 13), r.randrange(1, 29))
    data = []
    for i in ids:
        who = r.choice(NAMES)
        for d in r.sample(range(0, 400), r.choice([1, 1, 2, 2, 3])):  # dates of one key never the same
            data.append((f"{prefix}{i}", who, r.choice(values), (start + datetime.timedelta(days=d)).isoformat()))
    while len(data) == len(ids):  # nothing to remove: one key written twice
        data.append((f"{prefix}{ids[0]}", NAMES[0], values[0], (start + datetime.timedelta(days=401)).isoformat()))
    r.shuffle(data)
    latest = {}
    for row in data:
        if row[0] not in latest or row[3] > latest[row[0]][3]:
            latest[row[0]] = row
    want = [list(latest[k]) for k in sorted(latest)]
    removed = len(data) - len(want)
    text = f"{key},name,{col},{date_col}\n" + "\n".join(",".join(x) for x in data)

    def check(run, report):
        got = _tab.rows(run, out)
        if got is None:
            return False, f"no {out} saved"
        ok = _tab.head(got, [key, "name", col, date_col]) and got[1:] == want and _says(B._body(report), removed, 0.1)
        return ok, f"{out}: {len(got) - 1} rows against {len(want)} wanted, the same: {got[1:] == want}; {removed} removed in the answer: {ok}"
    return ("hard: tables", "a table cut to one row a key, the latest kept", _tab.given(name, text,
            f"Some {key}s appear more than once. Save a file {out} with the same columns that keeps one row for each {key}: the row with "
            f"the latest {date_col}. Sort the rows by {key}. Then tell me how many rows were removed."), check)


def dedupe(task):
    m = re.search(r"Here is the file (\S+):\n(\w+),.+?,(\w+)\n.+Save a file (\S+) with the same columns", task, re.S)
    if not m:
        return None
    return _fill('''import csv

rows = list(csv.DictReader(open(__NAME__)))
latest = {}
for row in rows:
    k = row[__KEY__]
    if k not in latest or row[__DATE__] > latest[k][__DATE__]:  # dates as YYYY-MM-DD: compared as text
        latest[k] = row
with open(__OUT__, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(latest[k] for k in sorted(latest))
print(__OUT__, "saved:", len(latest), "rows")
print("removed:", len(rows) - len(latest))
''', name=m.group(1), key=m.group(2), date=m.group(3), out=m.group(4))


make = h_tab_dedupe
lesson = dedupe
