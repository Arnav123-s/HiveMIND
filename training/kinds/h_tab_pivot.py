"""The kind h_tab_pivot: a long table given in the task turned wide, one column a month (hard: tables).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import re

from training import hive_bench as B
from training.kinds._common import _fill
from training.kinds import _tab

KIND = "h_tab_pivot"
FAMILY = "hard: tables"
HARD = True
ORDER = 310

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
# (file, the column of the rows, its values, the column summed)
THEMES = [("units.csv", "store", ["Alder", "Birch", "Cedar", "Maple", "Rowan", "Willow"], "units"),
          ("visits.csv", "clinic", ["Harbor", "Hill", "Lake", "Market", "Park", "River"], "visits"),
          ("tickets.csv", "desk", ["alpha", "bravo", "delta", "echo", "kilo", "sierra"], "tickets")]


def h_tab_pivot(r):
    name, key, values, col = r.choice(THEMES)
    first = r.randrange(0, 9)
    months = MONTHS[first:first + r.randrange(3, 5)]
    keys = sorted(r.sample(values, r.randrange(3, 6)))
    out = r.choice(["wide.csv", "by_month.csv", "pivot.csv"])
    cell = {(k, m): r.randrange(1, 90) for k in keys for m in months if r.random() < 0.75}
    for k in keys:  # every row of the wide table has a value somewhere in the long one
        if not any((k, m) in cell for m in months):
            cell[(k, months[0])] = r.randrange(1, 90)

    def month_sums():
        return {m: sum(v for (_, x), v in cell.items() if x == m) for m in months}
    while sorted(month_sums().values())[-1] == sorted(month_sums().values())[-2]:  # a tie has no single answer
        s = month_sums()
        top = max(months, key=s.get)
        cell[(keys[0], top)] = cell.get((keys[0], top), 0) + 1
    s = month_sums()
    best = max(months, key=s.get)
    data = list(cell.items())
    r.shuffle(data)
    text = f"{key},month,{col}\n" + "\n".join(f"{k},{m},{v}" for (k, m), v in data)
    want = [[k] + [cell.get((k, m), 0) for m in months] for k in keys]

    def check(run, report):
        got = _tab.rows(run, out)
        if got is None:
            return False, f"no {out} saved"
        body = B._body(report)
        ok = (_tab.head(got, [key] + months) and len(got) == len(want) + 1
              and all(len(g) == len(w) and g[0] == w[0] and all(_tab.near(a, b, 0.01) for a, b in zip(g[1:], w[1:])) for g, w in zip(got[1:], want))
              and re.search(rf"\b{best}", body, re.I) is not None)
        return ok, f"{out}: wants {want[:3]}..., the month {best} named; got {got[1:][:3]}: {ok}"
    return ("hard: tables", "a long table turned wide", _tab.given(name, text,
            f"Save a file {out} with one row for each {key}, sorted by {key} name, and one column for each month in the order "
            f"{', '.join(months)} (the heading: {key},{','.join(months)}), holding that {key}'s {col} in that month, or 0 where the file has "
            f"no row for it. Then tell me which month had the most {col} over all of them."), check)


def pivot(task):
    m = re.search(r"Here is the file (\S+):\n.+Save a file (\S+) with one row for each (\w+), .+? in the order (.+?) \(the heading.+?"
                  r"holding that \w+'s (\w+) in", task, re.S)
    if not m:
        return None
    return _fill('''import csv

key, months, cell = __KEY__, __MONTHS__, {}
for row in csv.DictReader(open(__NAME__)):
    cell[row[key], row["month"]] = cell.get((row[key], row["month"]), 0) + int(row[__COLUMN__])
keys = sorted({k for k, _ in cell})
with open(__OUT__, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow([key] + months)
    for k in keys:
        w.writerow([k] + [cell.get((k, m), 0) for m in months])
total = {m: sum(cell.get((k, m), 0) for k in keys) for m in months}
print(__OUT__, "saved:", len(keys), "rows")
print("most:", max(months, key=total.get))
''', name=m.group(1), out=m.group(2), key=m.group(3), months=m.group(4).split(", "), column=m.group(5))


make = h_tab_pivot
lesson = pivot
