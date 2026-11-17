# A kind of task in one file

Every kind of task the hive is examined on, practises on and is taught lives in one file of its own in
`training/kinds/`. The exam (`training/exam.py`, `training/exam_hard.py`) and the lessons (`training/lessons.py`)
find the files by themselves (`training/kinds/__init__.py`, the registry). So an agent adds a kind by adding one
file: nobody else's file is touched, and many agents can add kinds at once (PLAN pieces K1, K2).

## What the file holds

Look at `training/kinds/m_days.py` (small, easy) or `training/kinds/h_join.py` (hard, with a level) first.

```python
"""The kind h_rota: ... (one line: what the task asks)."""
from training.kinds._common import _fill, says   # shared checks and lesson pieces, if you need them

KIND = "h_rota"           # its name: the same as the maker's name (the exam seeds each task with it)
FAMILY = "hard: plans"    # the field its tasks are counted under (the first thing make returns)
HARD = True               # True: the hard exam; False: the first exam
ORDER = 200               # its place in its exam: a number after every kind already there (see below)


def h_rota(r):
    """r is a random.Random: draw every value from it, never from anything else."""
    people = r.sample(["Mira", "Tomas", "Aiko"], 2)
    ...
    want = ...                                   # the right answer, worked out here

    def check(run, report):                      # run: the task's run folder (files are under run / "work")
        ok = ...                                 # report: the hive's answer as text
        return ok, f"wants {want}; ..."          # (right or not, and why in a few words)
    return FAMILY, "a rota for a week", "the task as the hive reads it ...", check


def rota(task):
    """The lesson: the right program for a task of this kind, read back from the task's own text; None if it
    cannot. Every value the program prints is computed by it, never typed."""
    ...
    return _fill("""...program...""", people=...)


make = h_rota
lesson = rota             # or None: then the hive is never shown this kind done
```

## The rules

- **The maker draws from `r` only.** The same seed must give the same task, every time and on every runner.
  No clock, no `random.random()`, no network while making the task (the network may be used inside the check,
  as the live-fact kinds do).
- **The check is made together with the task** and holds the right values; it is the same check the exam,
  practice and the lessons use. A lesson whose program the check does not pass is never taught.
- **`ORDER` takes a number after the last one of its exam** (the easy kinds are at 10 to 160 now, the hard ones at
  10 to 130; take 200, 210 ... and check no one else holds yours). The exam shuffles its kinds with the seed, in
  this order, so the order is part of what a seed draws and must not hang on file names. Two kinds with the same
  `ORDER` refuse to load.
- **A sample without network.** The registry makes one task of every kind offline (`kinds.sample(name)`) and
  `tests/test_kinds.py` checks it, and that the lesson writes a program for it. If your maker would reach the
  network while making a task, give the file a `sample()` that makes one without it (see `h_web.py`).
- **Say what it needs.** `NETWORK = True` if the check or the lesson reads a site (its lesson is then not run by
  the offline test). A kind without `NETWORK` and with a lesson has its lesson run and checked by
  `tests/test_kinds.py`: it must be right.
- **Never write a model's name** in a task, a check or a lesson.

## What else a kind may say

| Name | Meaning |
|---|---|
| `COPIES = 2` | drawn twice as often in its exam (two places in the list) |
| `LEVELED = True` | the maker reads `getattr(r, "level", 0)` and makes a harder task at a higher level |
| `HELD_OUT = True` | never practised or taught: measures what carries over. The commander says which new kinds are held out (one in four) |
| `GIVEN_FILE = True` | the lesson reads the task's data from the file the runtime saves (`log.txt`); it is called as `lesson(task, copy=True)` when it must copy the data into its program instead |
| `LESSON_ORDER` | where its lesson stands among the lessons; by default after all the old ones |

Constants and helpers only your kind uses stay in your file. `training/kinds/_common.py` holds what two kinds or
more share (the number checks `says`, `every`, `_nums`, `_says`, `_file`, lists like `MONTHS` and `CAPITALS`, the
beginnings of lesson programs `HEAD`, `PYPI`, `CATEGORY`). Add to it only what a second kind needs, and never change
what is there: other kinds' exams depend on it.

## To see and test a kind

    python training/exam.py show --level hard --seed 9001     a sitting, with your kind in it
    python training/lessons.py --show h_rota --seed 1          your lesson: task, program, what it printed, right or not
    python -m pytest -q tests/test_kinds.py tests/test_kinds_same_exams.py

Adding a kind changes the exams of every seed: there is one more kind to shuffle, and each task's seed holds its
place in the shuffle. That is meant. What must not change is how the old kinds make their tasks:
`tests/test_kinds_same_exams.py` sits the old kinds alone, on the seeds in `tests/data/exams_golden.json`, and
compares every task and every value its check holds with what the code made before the kinds were moved.
