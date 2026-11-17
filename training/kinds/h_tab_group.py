"""The kind h_tab_group: a CSV given in the task grouped by a column, each group's total and mean written as a CSV
(hard: tables).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import re

from training import hive_bench as B
from training.kinds._common import _fill, HARD_NAMES as NAMES
from training.kinds import _tab

KIND = "h_tab_group"
FAMILY = "hard: tables"
HARD = True
ORDER = 300

# (file, the column grouped by, its values, the column of who, the column summed)
THEMES = [("sales.csv", "region", ["north", "south", "east", "west", "central"], "rep", "amount"),
          ("expenses.csv", "department", ["sales", "support", "research", "legal", "finance"], "employee", "cost"),
          ("orders.csv", "category", ["books", "games", "garden", "kitchen", "toys"], "customer", "price")]


def h_tab_group(r):
    name, group, values, who, col = r.choice(THEMES)
    groups = r.sample(values, r.randrange(3, 5))
    out = r.choice(["totals.csv", "summary.csv", "by_group.csv"])
    data = [(g, r.choice(NAMES), r.randrange(5, 400) + r.choice([0, 0, 0.5, 0.25])) for g in groups]  # every group has a row
    data += [(r.choice(groups), r.choice(NAMES), r.randrange(5, 400) + r.choice([0, 0, 0.5, 0.25])) for _ in range(r.randrange(8, 15))]
    r.shuffle(data)

    def sums():
        return {g: sum(v for x, _, v in data if x == g) for g in groups}
    while len(set(sums().values())) < len(groups):  # equal totals have no single order: one more row breaks it
        data.append((groups[0], NAMES[0], 1))
    total = sums()
    count = {g: sum(1 for x, _, _ in data if x == g) for g in groups}
    want = sorted(groups, key=lambda g: -total[g])
    text = f"{group},{who},{col}\n" + "\n".join(f"{g},{w},{v:g}" for g, w, v in data)

    def check(run, report):
        got = _tab.rows(run, out)
        if got is None:
            return False, f"no {out} saved"
        ok = (_tab.head(got, [group, "total", "mean"]) and len(got) == len(want) + 1
              and all(len(row) >= 3 and row[0].lower() == g and _tab.near(row[1], total[g]) and _tab.near(row[2], total[g] / count[g], 0.0051)
                      for row, g in zip(got[1:], want))
              and re.search(rf"\b{want[0]}\b", B._body(report), re.I) is not None)
        return ok, f"{out}: wants {[(g, round(total[g], 2)) for g in want]}, largest {want[0]} named; got {got[1:][:5]}: {ok}"
    return ("hard: tables", "a table grouped, each group's total and mean saved", _tab.given(name, text,
            f"Save a file {out} with the columns {group},total,mean: one row for each {group}, sorted by total from the largest to the "
            f"smallest, holding the total of its {col} values and their mean rounded to 2 decimals. Then tell me which {group} has the "
            "largest total."), check)


def group(task):
    m = re.search(r"Here is the file (\S+):\n.+Save a file (\S+) with the columns (\w+),total,mean: .+? the total of its (\w+) values", task, re.S)
    if not m:
        return None
    return _fill('''import csv

values = {}
for row in csv.DictReader(open(__NAME__)):
    values.setdefault(row[__GROUP__], []).append(float(row[__COLUMN__]))
rows = sorted(((g, round(sum(v), 2), round(sum(v) / len(v), 2)) for g, v in values.items()), key=lambda x: -x[1])
with open(__OUT__, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow([__GROUP__, "total", "mean"])
    w.writerows(rows)
print(__OUT__, "saved:", rows)
print("largest total:", rows[0][0])
''', name=m.group(1), out=m.group(2), group=m.group(3), column=m.group(4))


make = h_tab_group
lesson = group
