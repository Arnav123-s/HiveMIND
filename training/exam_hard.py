"""The harder kinds of the hive's exam: work of several steps, still made by code and checked by code.

The first exam (training/exam.py) asks for one sum, one date, one fact. By 2026-11-13 the hive passed 14 to 16 of
its 16 tasks, so it could no longer show whether a change made the hive better. These kinds take several steps
each and their space of tasks is large (the numbers, tables, sites and specifications are drawn afresh):

    walk a site over several pages and count        two facts from two sources, combined
    a module of two functions, with hidden tests    a file given in the task, edited to a specification
    a join over two small tables                    a log read and counted into a file
    a search for a number with given properties     a simulation followed step by step
    several facts fetched and laid out as a file    a fact from a site and a date sum on it

Every check is computed in the kind's file or read live from the source at the moment of checking. `python
training/exam.py show --level hard --seed N` prints a sitting; `sit --level hard` sits it.

Each kind lives in a file of its own, training/kinds/h_*.py (docs/KINDS.md); this module keeps the old names.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from training import kinds  # noqa: E402
from training.kinds._common import HARD_NAMES as NAMES  # noqa: E402,F401
from training.kinds._common import HARD_PACKAGES as PACKAGES  # noqa: E402,F401
from training.kinds._common import MONTHS, _file, _nums, _pypi, _says  # noqa: E402,F401
from training.kinds.h_age import AUTHORS, h_age  # noqa: E402,F401
from training.kinds.h_edit import CITIES, h_edit  # noqa: E402,F401
from training.kinds.h_join import ITEMS, h_join  # noqa: E402,F401
from training.kinds.h_log import SERVICES, h_log  # noqa: E402,F401
from training.kinds.h_module import (SPECS, _balanced, _base, _caesar, _dur, _factors, _fmt, _hidden, _letters,  # noqa: E402,F401
                                     _load, _merge, _rle, _roman, _spiral, _words, h_module)
from training.kinds.h_quotes import h_quotes  # noqa: E402,F401
from training.kinds.h_search import h_search  # noqa: E402,F401
from training.kinds.h_sim import h_sim  # noqa: E402,F401
from training.kinds.h_since import h_since  # noqa: E402,F401
from training.kinds.h_table import h_table  # noqa: E402,F401
from training.kinds.h_two import h_two  # noqa: E402,F401
from training.kinds.h_walk import BIG, _all_books, h_walk  # noqa: E402,F401
from training.kinds.h_web import (_UA, WEB, WEB_FALLBACK, _web_claims, _web_label, _web_pick, _web_values,  # noqa: E402,F401
                                  h_web)

# the hard exam's makers, in the order its seed shuffles them (a kind with COPIES = 2 twice)
MAKERS = kinds.makers(hard=True)
# Kinds the hive never practises on (training/practice draws from the others): what it scores on these is what it
# learned that carries over to work it has not seen, not what it learned by heart. A kind says so itself (HELD_OUT).
HELD_OUT = set(kinds.HELD_OUT)
