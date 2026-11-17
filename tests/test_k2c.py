"""K2c: the family "programs" (training/kinds/h_prog_*.py): a module the hive writes and saves, put to hidden tests.

For every taught kind, 40 of 40 lessons are right by the kind's own check over 40 seeds; every kind makes its sample
without the network; a wrong program (one rule of the task broken) fails the check. The two held-out kinds are never
taught: a right program for them (their `solution`, kept for this test only) passes their check and a wrong one fails.
"""
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from training import exam, kinds, lessons

PROGS = [k.KIND for k in kinds.ALL if k.KIND.startswith("h_prog_")]
TAUGHT = [n for n in PROGS if not kinds.get(n).HELD_OUT]
HELD = [n for n in PROGS if kinds.get(n).HELD_OUT]

# one rule of the task broken in the right program: the hidden tests must see it
WRONG = {"h_prog_bank": ("self.withdrawals += 1", "pass"),
         "h_prog_machine": ("states.append(step(states[-1], event))", "states.append(step(states[0], event))"),
         "h_prog_lru": ("del self.kept[next(iter(self.kept))]", "self.kept.popitem()"),
         "h_prog_calc": ("BINDS[op] + (0 if op == SYMBOL and RIGHT else 1)", "BINDS[op]"),
         "h_prog_schedule": ('raise ValueError("the dependencies go round in a circle")', "break"),
         "h_prog_grid": ("if cell != LAND or (y, x) in seen:", "if cell != LAND:"),
         "h_prog_queue": ("(FIRST * priority, arrival, name, duration)", "(arrival, FIRST * priority, name, duration)"),
         "h_prog_wrap": ("len(lines[-1]) + 1 + len(w) <= width", "len(lines[-1]) + 1 + len(w) < width")}


def _no_network(*a, **k):
    raise AssertionError("a kind's sample asked the network")


def _program(name, task):
    k = kinds.get(name)
    return (k.lesson or k.solution)(task)


def _sit(name, rseed, program=None):
    """(ok, why) of a program for the task this kind draws with the seed, run as a lesson's is."""
    from team.tools.sandbox import give, run_python
    field, kind, task, check = exam._made(kinds.get(name).make, rseed)
    program = program(task) if program else _program(name, task)
    assert program, f"{name}: no program for {task}"
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "work"
        give(task, work)
        res = run_python(program, work, name="lesson.py", timeout=60)
        (work / "lesson.py").unlink(missing_ok=True)
        if res["returncode"]:
            return False, res["stderr"][-300:]
        return check(Path(tmp), res["stdout"].strip())


def test_the_family_has_eight_kinds_two_held_out_in_its_orders():
    assert len(PROGS) == 8 and len(HELD) == 2 and len(TAUGHT) == 6
    for n in PROGS:
        k = kinds.get(n)
        assert k.HARD and k.FAMILY == "programs" and 500 <= k.ORDER <= 599 and not k.NETWORK
    assert set(HELD) <= kinds.HELD_OUT and not set(HELD) & set(lessons.SOLVERS)
    assert all(kinds.get(n).lesson is None and callable(kinds.get(n).solution) for n in HELD)
    assert set(TAUGHT) <= set(lessons.SOLVERS)


@pytest.mark.parametrize("name", PROGS)
def test_a_sample_is_made_offline_and_the_same_every_time(name, monkeypatch):
    import requests
    monkeypatch.setattr(requests, "get", _no_network)
    monkeypatch.setattr(requests, "post", _no_network)
    field, kind, task, check = kinds.sample(name)
    assert field == "programs" and callable(check) and kinds.sample(name)[2] == task
    assert _program(name, task)


@pytest.mark.parametrize("name", TAUGHT)
def test_forty_of_forty_lessons_are_right_by_their_own_check(name):
    with ThreadPoolExecutor(8) as pool:
        got = list(pool.map(lambda i: lessons.lesson(name, f"k2c:{i}", timeout=60), range(40)))
    bad = [(g["rseed"], g["why"]) for g in got if not g["ok"]]
    assert not bad, f"{name}: {len(bad)} of 40 wrong, first {bad[0]}"
    assert len({g["task"] for g in got}) == 40  # every seed its own task


@pytest.mark.parametrize("name", HELD)
def test_a_held_out_kind_s_right_program_passes_its_check(name):
    for i in range(10):
        ok, why = _sit(name, f"k2c:{i}")
        assert ok, f"{name} k2c:{i}: {why}"


@pytest.mark.parametrize("name", PROGS)
def test_a_wrong_program_fails(name):
    old, new = WRONG[name]

    def wrong(task):
        right = _program(name, task)
        assert old in right
        return right.replace(old, new)
    for i in range(5):
        ok, why = _sit(name, f"k2c-wrong:{i}", wrong)
        assert not ok, f"{name} k2c-wrong:{i}: a wrong program passed: {why}"
    # and a right module whose answer leaves out the value asked fails too
    field, kind, task, check = exam._made(kinds.get(name).make, "k2c-quiet")
    with tempfile.TemporaryDirectory() as tmp:
        from team.tools.sandbox import run_python
        work = Path(tmp) / "work"
        prog = _program(name, task).split("    print(")[0]
        assert run_python(prog, work, name="lesson.py", timeout=60)["returncode"] == 0
        (work / "lesson.py").unlink()
        assert not check(Path(tmp), "saved and tested")[0]
