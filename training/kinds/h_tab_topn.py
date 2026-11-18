"""The kind h_tab_topn: the top N rows of each group of a CSV given in the task, ranked and saved (hard: tables).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
it has no lesson: it is held out, never practised or taught, so what the hive scores on it is what carries over.
"""
import re

from training import hive_bench as B
from training.kinds._common import HARD_NAMES as NAMES
from training.kinds import _tab

KIND = "h_tab_topn"
FAMILY = "hard: tables"
HARD = True
ORDER = 360
HELD_OUT = True

# (file, the group column, its values, the column of who, the column ranked)
THEMES = [("scores.csv", "team", ["red", "blue", "green", "gold"], "player", "score"),
          ("results.csv", "class", ["A1", "A2", "B1", "B2"], "student", "marks"),
          ("shops.csv", "shop", ["Avon", "Clyde", "Severn", "Tees"], "seller", "sold")]


def h_tab_topn(r):
    name, group, values, who, col = r.choice(THEMES)
    out = r.choice(["top.csv", "best.csv", "leaders.csv"])
    n = r.randrange(2, 4)
    groups = r.sample(values, r.randrange(2, 5))
    data = []
    for g in groups:
        for p in r.sample(NAMES, r.randrange(n - 1, n + 4)):  # a group may have fewer than n rows
            data.append((g, p, r.randrange(40, 100)))
    top = max(x[2] for x in data)
    while sum(1 for x in data if x[2] == top) > 1:  # the best of all is one row
        i = next(i for i, x in enumerate(data) if x[2] == top)
        data[i] = (data[i][0], data[i][1], top + 1)
        top += 1
    r.shuffle(data)
    best = next(x[1] for x in data if x[2] == top)
    want = []
    for g in sorted(groups):
        mine = sorted((x for x in data if x[0] == g), key=lambda x: (-x[2], x[1]))[:n]
        want += [[g, str(i + 1), p, str(s)] for i, (_, p, s) in enumerate(mine)]
    text = f"{group},{who},{col}\n" + "\n".join(f"{g},{p},{s}" for g, p, s in data)

    def check(run, report):
        got = _tab.rows(run, out)
        if got is None:
            return False, f"no {out} saved"
        ok = (_tab.head(got, [group, "rank", who, col]) and len(got) == len(want) + 1
              and all(len(g) == 4 and g[0] == w[0] and _tab.near(g[1], int(w[1]), 0.01) and g[2] == w[2] and _tab.near(g[3], int(w[3]), 0.01)
                      for g, w in zip(got[1:], want))
              and re.search(rf"\b{best}\b", B._body(report)) is not None)
        return ok, f"{out}: {len(got) - 1} rows against {len(want)}, wants {want[:3]}...; {best} named: {ok}"
    return ("hard: tables", "the top rows of each group ranked", _tab.given(name, text,
            f"Save a file {out} with the columns {group},rank,{who},{col}: for each {group}, sorted by {group}, its {n} rows with the "
            f"highest {col} (a {group} with fewer rows lists all it has), ranked 1 to {n} from the highest; equal {col} values are "
            f"ranked by {who} name. Then tell me which {who} has the highest {col} of all."), check)


make = h_tab_topn
lesson = None
