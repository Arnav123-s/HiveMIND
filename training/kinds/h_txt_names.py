"""The kind h_txt_names: names written "Last, First" turned into "First Last" by rules, sorted, saved (hard: text).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import re

from training import hive_bench as B
from training.kinds._common import _file, _fill, _says, HARD_NAMES as FIRSTS

KIND = "h_txt_names"
FAMILY = "hard: text"
HARD = True
ORDER = 410

LASTS = ["Hartmann", "Van Dijk", "Okafor", "De Luca", "Berg", "Nakamura", "Silva", "Novak", "Ahmed", "Lindqvist", "Da Costa", "Moreau"]


def _messy(r, word):
    return r.choice([word, word, word.upper(), word.lower()])


def _first(first, mid):
    return first + (f" {mid}." if mid else "")


def h_txt_names(r):
    n, people = r.randrange(6, 10), []
    while len(people) < n:
        first, last = r.choice(FIRSTS), r.choice(LASTS)
        mid = r.choice(["", "", r.choice("ABDEJKMRS")])
        if (first, last) not in [(f, la) for f, la, _ in people]:
            people.append((first, last, mid))
    lines = []
    for first, last, mid in people:
        f = _messy(r, first) + ((" " + _messy(r, mid) + r.choice(["", "."])) if mid else "")
        lines.append(_messy(r, last) + r.choice([",", ", ", " ,  ", ",  "]) + f + r.choice(["", " "]))
    want = [f"{_first(f, m)} {la}" for f, la, m in sorted(people, key=lambda p: (p[1], _first(p[0], p[2])))]

    def check(run, report):
        f = _file(run, "names.txt")
        if not f:
            return False, "no names.txt saved"
        got = [ln.strip() for ln in f.read_text().splitlines() if ln.strip()]
        ok = got == want and _says(B._body(report), len(want), 0.1)
        return ok, f"names.txt {got[:10]} against {want}; the count {len(want)} in the answer"
    return ("hard: text", "names turned and sorted", "Here are names, one per line, each written 'Last, First':\n" + "\n".join(lines)
            + "\nWrite each name as 'First Last'. Rules: every word has its first letter capital and the rest small; extra spaces "
            "go; a middle initial stays after the first name with a dot ('Berg, Mira k' becomes 'Mira K. Berg'); a last name of two "
            "words keeps both. Sort them by last name, then by first name (with its initial), save them one per line in names.txt, "
            "and tell me how many names there are.", check)


def names(task):
    m = re.search(r"each written 'Last, First':\n(.*?)\nWrite each name as", task, re.S)
    if not m:
        return None
    return _fill('''out = []
for line in __NAMES__.splitlines():
    last, first = [" ".join(w.capitalize() for w in part.split()) for part in line.split(",")]
    words = first.split()
    if len(words) > 1 and len(words[-1].rstrip(".")) == 1:
        words[-1] = words[-1].rstrip(".") + "."
    out.append((last, " ".join(words)))
out.sort()
with open("names.txt", "w") as f:
    f.write("\\n".join(first + " " + last for last, first in out) + "\\n")
print("names.txt saved")
print("names:", len(out))
''', names=m.group(1))


make = h_txt_names
lesson = names
