"""The kind h_since: a release read from PyPI and a date sum on it (hard: live facts).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import datetime
import re

from training import hive_bench as B
from training.kinds._common import PYPI, _fill, _nums, _pypi, HARD_PACKAGES as PACKAGES

KIND = "h_since"
FAMILY = "hard: live facts"
HARD = True
ORDER = 40
LESSON_ORDER = 170
NETWORK = True


def h_since(r):
    pkg = r.choice(PACKAGES)

    def check(run, report):
        v, d = _pypi(pkg)
        days = (datetime.date.today() - datetime.date.fromisoformat(d)).days
        body = B._body(report)
        ok = v in body and any(abs(g - days) <= 1 for g in _nums(body))
        return ok, f"{pkg} {v} of {d}, {days} days ago; version and days in the answer: {ok}"
    return ("hard: live facts", "a fact read and a date sum on it", f"What is the latest version of {pkg} on PyPI, on which date was it released, "
            "and how many days ago was that?", check)


def since(task):
    m = re.search(r"latest version of (\S+) on PyPI", task)
    return m and _fill(PYPI + '''
version, released = latest(__PACKAGE__)
print("version:", version)
print("released:", released)
print("days ago:", (date.today() - date.fromisoformat(released)).days)
''', package=m.group(1))


make = h_since
lesson = since
