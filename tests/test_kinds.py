"""Every kind in training/kinds/ keeps the form docs/KINDS.md gives it, makes a task without the network, and where
it has a lesson and needs no site, its lesson's program is right by the task's own check."""
from pathlib import Path

import pytest

from training import exam, exam_hard, kinds, lessons


def _no_network(*a, **k):
    raise AssertionError("a kind's sample asked the network")


@pytest.fixture
def offline(monkeypatch):
    import requests
    monkeypatch.setattr(requests, "get", _no_network)
    monkeypatch.setattr(requests, "post", _no_network)


def test_every_kind_has_its_form_and_the_exams_read_them_from_the_registry():
    assert len(kinds.ALL) >= 29
    for k in kinds.ALL:
        assert k.KIND == k.make.__name__ and isinstance(k.FAMILY, str) and isinstance(k.HARD, bool) and isinstance(k.ORDER, int)
        assert k.lesson is None or callable(k.lesson)
    assert [m.__name__ for m in exam.MAKERS] == [m.__name__ for m in kinds.makers(hard=False)]
    assert [m.__name__ for m in exam_hard.MAKERS] == [m.__name__ for m in kinds.makers(hard=True)]
    assert exam_hard.HELD_OUT == kinds.HELD_OUT and exam.LEVELED == kinds.LEVELED
    assert lessons.SOLVERS == kinds.SOLVERS and not set(lessons.SOLVERS) & kinds.HELD_OUT
    assert all(kinds.get(n).lesson for n in lessons.SOLVERS)


@pytest.mark.parametrize("name", [k.KIND for k in kinds.ALL])
def test_a_kind_makes_a_task_without_the_network(name, offline):
    field, kind, task, check = kinds.sample(name)
    assert field == kinds.get(name).FAMILY and kind and task and callable(check)
    assert kind in kinds.written(name), f"{name}: the recorded kind must be visible to the generation reports"
    assert kinds.sample(name)[2] == task  # the same sample every time
    les = kinds.get(name).lesson
    if les and not kinds.get(name).HELD_OUT:
        assert les(task), f"{name}: its lesson has no program for its own sample"


@pytest.mark.parametrize("name", [k.KIND for k in kinds.ALL if k.lesson and not k.NETWORK and not k.HELD_OUT])
def test_a_lesson_that_needs_no_site_is_right_by_its_own_check(name, offline):
    les = lessons.lesson(name, "kinds-test", 0, timeout=60)
    assert les["ok"], f"{name}: {les['why']}\n{les['task']}\n{les['program']}\n{les['answer']}"


def test_a_kind_that_breaks_the_form_is_not_loaded(tmp_path, monkeypatch):
    bad = tmp_path / "bad_kind.py"
    bad.write_text("KIND = 'bad_kind'\nFAMILY = 'x'\nHARD = False\nORDER = 10\n\ndef other(r):\n    pass\n\nmake = other\n")
    monkeypatch.setattr(kinds, "__path__", [str(tmp_path)])
    monkeypatch.setattr(kinds, "__name__", "kinds_under_test")
    import sys
    import types
    pkg = types.ModuleType("kinds_under_test")
    pkg.__path__ = [str(tmp_path)]
    monkeypatch.setitem(sys.modules, "kinds_under_test", pkg)
    with pytest.raises(ImportError, match="must be the same"):
        kinds._load()
    assert Path(bad).exists()
