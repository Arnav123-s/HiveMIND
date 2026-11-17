"""The kind h_txt_mdcsv: a markdown table turned into a CSV file (hard: text).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import csv
import re

from training import hive_bench as B
from training.kinds._common import _file, _fill, _says, HARD_NAMES as NAMES

KIND = "h_txt_mdcsv"
FAMILY = "hard: text"
HARD = True
ORDER = 440
GIVEN_FILE = True

CITIES = ["Portland, OR", "Lyon", "Kyoto", "Austin, TX", "Porto", "Graz", "Salem, MA", "Accra"]
TEAMS = ["blue", "red", "green", ""]


def h_txt_mdcsv(r):
    head = ["Name", "City", "Team", "Score"]
    rows = [[n, r.choice(CITIES), r.choice(TEAMS), f"{r.randrange(10, 100)}.{r.randrange(0, 10)}"] for n in r.sample(NAMES, r.randrange(5, 10))]

    def md(cells):
        inner = " | ".join(c + " " * r.randrange(0, 3) for c in cells)
        return r.choice(["| ", "|", "|  "]) + inner + r.choice([" |", "|", " |  "])
    align = "|" + "|".join(r.choice([":---", "---:", ":--:", "------"]) for _ in head) + "|"
    text = "\n".join([md(head), align] + [md(row) for row in rows])
    want = [head] + rows

    def check(run, report):
        f = _file(run, "table.csv")
        if not f:
            return False, "no table.csv saved"
        with open(f, newline="") as fh:
            got = [row for row in csv.reader(fh) if row]
        ok = got == want and _says(B._body(report), len(rows), 0.1)
        return ok, f"table.csv {got[:3]}... ({len(got)} rows) against {want[:3]}... ({len(want)} rows); {len(rows)} data rows said"
    return ("hard: text", "a markdown table turned into CSV", "Here is a markdown table:\n" + text + "\nSave it as table.csv: the header "
            "row first, then the data rows in the same order; no line for the row of dashes; every cell without the spaces around it "
            "(an empty cell stays an empty field); a cell that holds a comma is quoted, as Python's csv module writes it. Then tell "
            "me how many data rows the table has.", check)


def mdcsv(task, copy=False):
    """The table is data the task gives: the runtime saves it as a file, so the program reads table.md; copy: the table
    copied into the program instead (a task of several parts whose first block of data is another part's)."""
    m = re.search(r"Here is a markdown table:\n(.*?)\nSave it as table\.csv", task, re.S)
    if not m:
        return None
    lines = repr(m.group(1)) + ".splitlines()" if copy else 'open("table.md")'
    return _fill('''import csv
rows = []
for line in __LINES__:
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if all(set(c) <= set(":-") for c in cells):
        continue
    rows.append(cells)
with open("table.csv", "w", newline="") as f:
    csv.writer(f).writerows(rows)
print("table.csv saved")
print("data rows:", len(rows) - 1)
''').replace("__LINES__", lines)


make = h_txt_mdcsv
lesson = mdcsv
