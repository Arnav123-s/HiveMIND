"""The kind m_days: the days between two dates (dates).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import datetime
import re

from training.kinds._common import DATE, MONTHS, _fill, says

KIND = "m_days"
FAMILY = "dates"
HARD = False
ORDER = 20
LESSON_ORDER = 20


def m_days(r):
    a = datetime.date(r.choice([2026, 2027, 2028]), r.randrange(1, 13), r.randrange(1, 28))
    b = a + datetime.timedelta(days=r.randrange(20, 200))
    f = lambda d: f"{d.day} {MONTHS[d.month - 1]} {d.year}"  # noqa: E731
    return "dates", "days between two dates", f"How many days are there from {f(a)} to {f(b)}?", says((b - a).days, 0.1)


def days(task):
    m = re.search(rf"from {DATE} to {DATE}", task)
    return m and _fill('''from datetime import datetime

start = datetime.strptime(__A__, "%d %B %Y").date()
end = datetime.strptime(__B__, "%d %B %Y").date()
print("days:", (end - start).days)
''', a=" ".join(m.group(1, 2, 3)), b=" ".join(m.group(4, 5, 6)))


make = m_days
lesson = days
