"""The kind h_table: several facts fetched from PyPI and laid out as a Markdown file (hard: plans).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import re

from training.kinds._common import PYPI, _file, _fill, _pypi, HARD_PACKAGES as PACKAGES

KIND = "h_table"
FAMILY = "hard: plans"
HARD = True
ORDER = 60
LESSON_ORDER = 190
NETWORK = True


def h_table(r):
    pk = sorted(r.sample(PACKAGES, r.choice([3, 4])))

    def check(run, report):
        f = _file(run, "versions.md")
        if not f:
            return False, "no versions.md saved"
        rows = [x for x in f.read_text().splitlines() if x.strip().startswith("|") and not re.fullmatch(r"[|\s:-]+", x.strip())]
        cells = [[c.strip() for c in x.strip().strip("|").split("|")] for x in rows][1:]
        want = [[p, *_pypi(p)] for p in pk]
        ok = len(cells) == len(want) and all(len(c) >= 3 and c[0].lower() == w[0] and c[1] == w[1] and w[2] in c[2] for c, w in zip(cells, want))
        return ok, f"versions.md has {len(cells)} rows; the {len(want)} packages in order with version and date: {ok}"
    return ("hard: plans", "several facts fetched and laid out as a file", f"Save a file versions.md holding a Markdown table with the columns "
            f"package, version, released: one row for each of the PyPI packages {', '.join(pk)}, sorted by package name, with its latest "
            "version and that version's release date as YYYY-MM-DD. Then tell me which of them was released most recently.", check)


def table(task):
    m = re.search(r"PyPI packages (.+?), sorted by package name", task)
    if not m:
        return None
    return _fill(PYPI + '''
rows = sorted((p, *latest(p)) for p in __PACKAGES__)
with open("versions.md", "w") as f:
    f.write("| package | version | released |\\n|---|---|---|\\n")
    for p, v, d in rows:
        f.write(f"| {p} | {v} | {d} |\\n")
newest = max(rows, key=lambda r: r[2])
print("versions.md saved")
print("released most recently:", newest[0], newest[2])
''', packages=[p.strip() for p in m.group(1).split(",")])


make = h_table
lesson = table
