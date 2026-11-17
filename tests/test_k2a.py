"""K2a: the kinds of the family "tables and data files" (training/kinds/h_tab_*.py).

Every taught kind's lesson is right by its own check on 40 seeds of 40, every kind makes its task without the network,
the same every time, and an answer with one value changed is refused by the check. The two held-out kinds have no
lesson; their checks are tried here on programs written in this test, which nothing teaches.
"""
import re
import tempfile
from pathlib import Path

import pytest

from training import exam, kinds, lessons
from team.tools.sandbox import give, run_python

TAB = [k.KIND for k in kinds.ALL if k.KIND.startswith("h_tab_")]
TAUGHT = [k for k in TAB if not kinds.get(k).HELD_OUT]
HELD = [k for k in TAB if kinds.get(k).HELD_OUT]
SEEDS = [f"k2a:{i}" for i in range(40)]


def _no_network(*a, **k):
    raise AssertionError("a kind's sample asked the network")


@pytest.fixture
def offline(monkeypatch):
    import requests
    monkeypatch.setattr(requests, "get", _no_network)
    monkeypatch.setattr(requests, "post", _no_network)


# the held-out kinds' right programs: here only, never in training/kinds/, so they are never taught
HELD_PROGRAMS = {
    "h_tab_topn": lambda task: '''import csv, re
task = %r
name = re.search(r"Here is the file (\\S+):", task).group(1)
out, group, who, col = re.search(r"Save a file (\\S+) with the columns (\\w+),rank,(\\w+),(\\w+):", task).groups()
n = int(re.search(r"its (\\d+) rows with the", task).group(1))
rows = list(csv.DictReader(open(name)))
with open(out, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow([group, "rank", who, col])
    for g in sorted({r[group] for r in rows}):
        mine = sorted((r for r in rows if r[group] == g), key=lambda r: (-int(r[col]), r[who]))[:n]
        for i, r in enumerate(mine):
            w.writerow([g, i + 1, r[who], r[col]])
print("highest:", max(rows, key=lambda r: int(r[col]))[who])
''' % task,
    "h_tab_dates": lambda task: '''import csv, re, datetime
task = %r
name = re.search(r"Here is the file (\\S+):", task).group(1)
out, key, col = re.search(r"Save a file (\\S+) with the columns (\\w+),date,(\\w+),", task).groups()
lo, hi = re.search(r"dated from (\\S+) to (\\S+),", task).groups()
def day(s):
    for form in ("%%Y-%%m-%%d", "%%d/%%m/%%Y", "%%d %%b %%Y"):
        try:
            return datetime.datetime.strptime(s, form).date().isoformat()
        except ValueError:
            pass
kept = [r for r in csv.DictReader(open(name)) if lo <= day(r["date"]) <= hi]
with open(out, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow([key, "date", col])
    w.writerows([r[key], day(r["date"]), r[col]] for r in kept)
print("total:", sum(int(r[col]) for r in kept))
''' % task,
}


def _program(name, task):
    return HELD_PROGRAMS[name](task) if name in HELD_PROGRAMS else kinds.get(name).lesson(task)


def _sit(name, seed, spoil=False):
    """The kind's task of this seed, its right program run where the runtime would run it, and the check's verdict;
    spoil: one digit of the file the program saved moved by 5 (past any rounding the check forgives) before the check reads it."""
    field, kind, task, check = exam._made(kinds.get(name).make, seed, 0)
    program = _program(name, task)
    assert program, f"{name}: no program for {task[:200]}"
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "work"
        give(task, work, skip=lessons._wanted(task))
        res = run_python(program, work, name="lesson.py", timeout=60)
        assert res["returncode"] == 0, res["stderr"][-400:]
        (work / "lesson.py").unlink()
        if spoil:
            (saved,) = [work / f for f in lessons._wanted(task)]
            text = saved.read_text()
            i = max(m.start() for m in re.finditer(r"\d", text))
            saved.write_text(text[:i] + str((int(text[i]) + 5) % 10) + text[i + 1:])
        return check(Path(tmp), res["stdout"].strip())


def test_the_family_has_eight_kinds_two_held_out_in_their_own_orders():
    assert len(TAB) == 8 and len(HELD) == 2 and set(HELD) == {"h_tab_topn", "h_tab_dates"}
    assert all(300 <= kinds.get(k).ORDER < 400 and kinds.get(k).HARD and kinds.get(k).FAMILY == "hard: tables" for k in TAB)
    assert set(TAUGHT) <= set(lessons.SOLVERS) and not set(HELD) & set(lessons.SOLVERS)
    assert all(kinds.get(k).lesson is None for k in HELD)


@pytest.mark.parametrize("name", TAB)
def test_a_tables_kind_makes_its_task_without_the_network_the_same_every_time(name, offline):
    field, kind, task, check = kinds.sample(name)
    assert field == "hard: tables" and kind and callable(check) and "Here is the file " in task
    assert kinds.sample(name)[2] == task
    assert exam._made(kinds.get(name).make, "k2a:same", 0)[2] == exam._made(kinds.get(name).make, "k2a:same", 0)[2]
    assert lessons._wanted(task), f"{name}: the task asks for no file the runtime knows"


@pytest.mark.parametrize("name", TAUGHT)
def test_a_taught_kind_is_right_by_its_own_check_40_of_40(name, offline):
    wrong = [(s, why) for s in SEEDS for ok, why in [_sit(name, s)] if not ok]
    assert not wrong, f"{name}: {len(SEEDS) - len(wrong)} of {len(SEEDS)} right; {wrong[:2]}"


@pytest.mark.parametrize("name", HELD)
def test_a_held_out_kind_s_check_passes_a_right_program_40_of_40(name, offline):
    wrong = [(s, why) for s in SEEDS for ok, why in [_sit(name, s)] if not ok]
    assert not wrong, f"{name}: {len(SEEDS) - len(wrong)} of {len(SEEDS)} right; {wrong[:2]}"


@pytest.mark.parametrize("name", TAB)
def test_an_answer_with_one_value_changed_is_refused(name, offline):
    for s in SEEDS[:5]:
        ok, why = _sit(name, s, spoil=True)
        assert not ok, f"{name} {s}: a spoiled file passed: {why}"
        field, kind, task, check = exam._made(kinds.get(name).make, s, 0)
        with tempfile.TemporaryDirectory() as tmp:
            assert not check(Path(tmp), "done")[0]  # nothing saved
