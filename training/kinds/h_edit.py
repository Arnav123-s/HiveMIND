"""The kind h_edit: a CSV given in the task, edited to a specification (hard: files).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
it has no lesson: the hive is never shown it done.
"""
import csv
import io

from training import hive_bench as B
from training.kinds._common import _file, _says, HARD_NAMES as NAMES

KIND = "h_edit"
FAMILY = "hard: files"
HARD = True
ORDER = 90
HELD_OUT = True


CITIES = ["Lisbon", "Oslo", "Kyoto", "Lima", "Cairo", "Perth", "Quito", "Riga"]


def h_edit(r):
    rows = [(n, r.randrange(17, 70), r.choice(CITIES[:4])) for n in r.sample(NAMES, r.randrange(8, 12))]
    least = r.randrange(25, 45)
    text = "name,age,city\n" + "\n".join(f"{n},{a},{c}" for n, a, c in rows)
    want = [[n, str(a), c, n[0] + c[0]] for n, a, c in sorted((x for x in rows if x[1] >= least), key=lambda x: (x[2], x[0]))]

    def check(run, report):
        f = _file(run, "people.csv")
        if not f:
            return False, "no people.csv saved"
        got = [[c.strip() for c in row] for row in csv.reader(io.StringIO(f.read_text())) if any(c.strip() for c in row)]
        head = bool(got) and [c.lower() for c in got[0]] == ["name", "age", "city", "code"]
        ok = head and got[1:] == want and _says(B._body(report), len(want), 0.1)
        return ok, f"people.csv: heading right {head}, {len(got) - 1 if got else 0} rows against {len(want)} wanted, the same and counted in the answer: {ok}"
    return ("hard: files", "a file given in the task, edited to a specification", "Here is a CSV file:\n" + text + f"\nMake a new file people.csv from "
            f"it: keep only the people aged {least} or more, sort them by city and then by name, and add a fourth column 'code' holding the "
            "first letter of the name followed by the first letter of the city. Keep the heading line. Then tell me how many people are in "
            "the new file.", check)


make = h_edit
lesson = None
