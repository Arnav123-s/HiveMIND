"""The kind m_steps: three orders in one message, answered A, B and C (understanding).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import re

from training import hive_bench as B
from training.kinds._common import CAPITALS, _fill, _nums

KIND = "m_steps"
FAMILY = "understanding"
HARD = False
ORDER = 160
LESSON_ORDER = 80


def m_steps(r):
    a, b = r.randrange(12, 60), r.randrange(3, 12)
    word = r.choice(["lantern", "harvest", "pocket", "window", "garden"])
    c = CAPITALS[(country := r.choice(sorted(CAPITALS)))]

    def check(run, report):
        body = B._body(report)
        parts = re.split(r"(?m)^\s*\**([ABC])[).:\*]", body)
        got = {parts[i]: parts[i + 1] for i in range(1, len(parts) - 1, 2)}
        ok = (set(got) == {"A", "B", "C"} and any(abs(x - a * b) < 0.1 for x in _nums(got["A"])) and word[::-1] in got["B"].lower()
              and (c.lower() in got["C"].lower() or c.replace("í", "i").lower() in got["C"].lower()))
        return ok, f"three labelled answers {sorted(got)}; each right: {ok}"
    return ("understanding", "several orders in one message", f"Do these three things and label the answers A, B and C, each on its own line: "
            f"first multiply {a} by {b}; then write the word '{word}' backwards; then name the capital of {country}.", check)


def orders(task):
    m = re.search(r"first multiply (\d+) by (\d+); then write the word '(\w+)' backwards; then name the capital of (.+?)\.$", task.strip())
    if not (m and m.group(4) in CAPITALS):
        return None
    return _fill('''print("A:", __A__ * __B__)
print("B:", __W__[::-1])
print("C:", __C__)  # a capital city is known: no source
''', a=int(m.group(1)), b=int(m.group(2)), w=m.group(3), c=CAPITALS[m.group(4)])


make = m_steps
lesson = orders
