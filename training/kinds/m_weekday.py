"""The kind m_weekday: the weekday of a date (dates).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import datetime
import re

from training import hive_bench as B
from training.kinds._common import DATE, MONTHS, _fill

KIND = "m_weekday"
FAMILY = "dates"
HARD = False
ORDER = 30
LESSON_ORDER = 30


def m_weekday(r):
    d = datetime.date(r.choice([2026, 2027, 2028]), r.randrange(1, 13), r.randrange(1, 28))
    return ("dates", "the weekday of a date", f"What day of the week is {d.day} {MONTHS[d.month - 1]} {d.year}?",
            B.has(d.strftime("%A")))


def weekday(task):
    m = re.search(rf"What day of the week is {DATE}", task)
    return m and _fill('''from datetime import datetime

print(datetime.strptime(__D__, "%d %B %Y").strftime("%A"))
''', d=" ".join(m.groups()))


make = m_weekday
lesson = weekday
