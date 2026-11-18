"""The kind m_pypi: the current version of a package on PyPI (live facts).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
its lesson writes the right program for a task of it (training/lessons.py teaches it).
"""
import re

from training import hive_bench as B
from training.kinds._common import PYPI, _fill

KIND = "m_pypi"
FAMILY = "live facts"
HARD = False
ORDER = 80
LESSON_ORDER = 100
NETWORK = True


PACKAGES = ["requests", "numpy", "pandas", "flask", "django", "pytest", "rich", "httpx", "pydantic", "click", "tqdm", "scipy", "pillow", "jinja2"]


def m_pypi(r):
    pkg = r.choice(PACKAGES)

    def check(run, report):
        import requests
        v = requests.get(f"https://pypi.org/pypi/{pkg}/json", timeout=30).json()["info"]["version"]
        return v in B._body(report), f"latest {pkg} {v} in the answer"
    return "live facts", "a fact read from a source", f"Tell me the current version of {pkg} on PyPI.", check


def pypi_version(task):
    m = re.search(r"current version of (\S+) on PyPI", task)
    return m and _fill(PYPI + '''
print("version:", latest(__P__)[0])
''', p=m.group(1))


make = m_pypi
lesson = pypi_version
