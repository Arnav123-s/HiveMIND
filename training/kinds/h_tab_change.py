"""The kind h_tab_change: the percent change between two columns of a CSV given in the task, rounded by a stated rule
(hard: tables).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import re
from fractions import Fraction

from training import hive_bench as B
from training.kinds._common import _fill
from training.kinds import _tab

KIND = "h_tab_change"
FAMILY = "hard: tables"
HARD = True
ORDER = 340

# (file, the column of what, its values, the two columns compared)
THEMES = [("prices.csv", "item", ["apples", "bread", "butter", "cheese", "coffee", "eggs", "flour", "milk", "rice", "tea"], "old", "new"),
          ("staff.csv", "team", ["design", "finance", "legal", "ops", "research", "sales", "support", "web"], "last_year", "this_year"),
          ("traffic.csv", "page", ["about", "blog", "contact", "docs", "home", "jobs", "news", "shop"], "before", "after")]
BASES = [0, 4, 8, 16, 20, 25, 40, 50, 64, 80, 125, 160, 200, 250, 320, 400, 3, 6, 7, 12, 30, 45, 120]  # many make halves to round


def _round(x):
    """x rounded to 1 decimal, halves away from zero, written with its one decimal."""
    tenths = int(abs(x) * 10 + Fraction(1, 2))
    return ("-" if x < 0 and tenths else "") + f"{tenths // 10}.{tenths % 10}"


def h_tab_change(r):
    name, what, values, a, b = r.choice(THEMES)
    out = r.choice(["change.csv", "growth.csv", "percent.csv"])
    data = []
    for w in r.sample(values, r.randrange(5, 9)):
        old = r.choice(BASES)
        data.append((w, old, max(0, old + r.randrange(-old, old + 30) // r.choice([1, 2, 4]))))
    if all(o == 0 for _, o, _ in data):
        data[0] = (data[0][0], 8, 9)
    change = {w: "n/a" if o == 0 else _round(Fraction(n - o, o) * 100) for w, o, n in data}
    rise = {w: Fraction(n - o, o) for w, o, n in data if o}
    while sorted(rise.values())[-1:] == sorted(rise.values())[-2:-1]:  # a tie has no single answer: the first one rises more
        w, o, n = next(x for x in data if x[1] and Fraction(x[2] - x[1], x[1]) == max(rise.values()))
        data[data.index((w, o, n))] = (w, o, n + 1)
        change[w], rise[w] = _round(Fraction(n + 1 - o, o) * 100), Fraction(n + 1 - o, o)
    best = max(rise, key=rise.get)
    want = [[w, str(o), str(n), change[w]] for w, o, n in data]
    text = f"{what},{a},{b}\n" + "\n".join(f"{w},{o},{n}" for w, o, n in data)

    def check(run, report):
        got = _tab.rows(run, out)
        if got is None:
            return False, f"no {out} saved"
        ok = (_tab.head(got, [what, a, b, "change"]) and got[1:] == want
              and re.search(rf"\b{best}\b", B._body(report), re.I) is not None)
        bad = [(g, w) for g, w in zip(got[1:], want) if g != w][:3]
        return ok, f"{out}: {len(got) - 1} rows against {len(want)}, the rows that differ (got, wanted) {bad}; {best} named: {ok}"
    return ("hard: tables", "the percent change between two columns, rounded by a rule", _tab.given(name, text,
            f"Save a file {out} with the columns {what},{a},{b},change: the rows in the same order, and change the percent change from "
            f"{a} to {b}, rounded to 1 decimal with halves rounded away from zero (12.25 is 12.3, -12.25 is -12.3) and always written "
            f"with its one decimal (5.0); where {a} is 0, write n/a. Then tell me which {what} rose the most in percent."), check)


def change(task):
    m = re.search(r"Here is the file (\S+):\n(\w+),(\w+),(\w+)\n.+Save a file (\S+) with the columns", task, re.S)
    if not m:
        return None
    return _fill('''import csv
from decimal import Decimal as D, ROUND_HALF_UP as H
w, a, b, up = __WHAT__, __A__, __B__, {}
R = list(csv.DictReader(open(__NAME__)))
for r in R:
    o = D(r[a])
    if o:
        up[r[w]] = p = (D(r[b]) - o) * 100 / o
    r["change"] = p.quantize(D("0.1"), H) if o else "n/a"
with open(__OUT__, "w", newline="") as f:
    c = csv.DictWriter(f, [w, a, b, "change"])
    c.writeheader()
    c.writerows(R)
print("rose the most:", max(up, key=up.get))
''', name=m.group(1), what=m.group(2), a=m.group(3), b=m.group(4), out=m.group(5))


make = h_tab_change
lesson = change
