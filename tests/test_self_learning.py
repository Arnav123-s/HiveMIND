"""The hive learning by itself: dreams that try a failed task again with another cell, lessons that stop once the hive
has right programs of its own, and raw data read in every child's training."""
import json
from pathlib import Path

from training import exam, grow, lessons

ROOT = Path(__file__).resolve().parents[1]


def test_a_dream_tries_again_with_another_cell_beside_the_trunk_and_keeps_only_what_the_check_confirms(tmp_path, monkeypatch):
    failures = tmp_path / "failures.jsonl"
    failures.write_text(json.dumps({"maker": "m_units", "rseed": "u1", "level": 0, "program": "print(1)", "printed": "1", "said": "wants #"}) + "\n")
    seats, sat = [], []

    def sit_one(tag, tid, task, check, home, timeout=None, kind=""):
        import os
        seats.append(os.environ.get("HIVE_ROTATE"))
        sat.append(tid)
        return {"ok": len(sat) == 2, "seconds": 1}  # the first try fails, the second (another cell) is right
    monkeypatch.setattr(exam, "sit_one", sit_one)
    # rows_of gives rows from every try; here no member of the first try was right by the check, so it gives none
    monkeypatch.setattr(grow, "rows_of", lambda run, task, kind="", seed=None: [{"type": "first", "task": task, "run": str(run)}] if str(run).endswith("_1") else [])
    monkeypatch.setattr(grow, "pair_rows", lambda *a, **k: [])
    monkeypatch.setenv("HIVE_ROTATE", "3")
    out = tmp_path / "rows.jsonl"
    res = grow.dream(7, 1, failures, out, log=lambda *a, **k: None, tries=2)
    assert res == {"dream": 7, "tasks": 1, "right": 1, "rows": 1}
    assert seats == ["3", "4"] and sat == ["d7_00", "d7_00_1"]  # another cell the second time
    monkeypatch.delenv("HIVE_ROTATE")
    seats.clear(), sat.clear()
    grow.dream(9, 1, failures, tmp_path / "r2.jsonl", log=lambda *a, **k: None, tries=2)
    assert seats == [None, "1"] and "HIVE_ROTATE" not in __import__("os").environ  # unset stays unset
    monkeypatch.setenv("HIVE_ROTATE", "3")
    row = json.loads(out.read_text())
    assert row["dream"] and row["run"].endswith("d7_00_1")  # the rows are the try that the check confirmed
    import os
    assert os.environ["HIVE_ROTATE"] == "3"  # the runner's own turn is given back
    seats.clear(), sat.clear()
    monkeypatch.setattr(exam, "sit_one", lambda *a, **k: sat.append(1) or {"ok": False, "seconds": 1})
    assert grow.dream(8, 1, failures, out, log=lambda *a, **k: None, tries=1)["right"] == 0 and len(sat) == 1


def test_lessons_start_a_kind_and_stop_once_the_hive_has_right_programs_of_its_own(tmp_path):
    rows = tmp_path / "rows.jsonl"
    own = [{"type": "first", "kind": "a unit conversion", "who": "t80+g27code"}] * 3 + [
        {"type": "first", "kind": "the weekday of a date", "who": "lesson"}] * 5 + [  # a lesson's rows are not the hive's own
        {"type": "done", "kind": "the weekday of a date", "who": "t80+g27code"}]
    rows.write_text("\n".join(json.dumps(r) for r in own) + "\n")
    count = lessons.own_counts(rows, tmp_path / "missing.jsonl")
    assert count == {"a unit conversion": 3}
    said = []
    import pytest
    monkey = pytest.MonkeyPatch()
    monkey.setattr(lessons, "SOLVERS", {"m_units": lessons.units, "m_weekday": lessons.weekday})
    try:
        out = tmp_path / "lessons.jsonl"
        res = lessons.teach("t", 1, None, out=out, levels={}, log=lambda *a, **k: said.append(a[0]), several=0, own=count)
    finally:
        monkey.undo()
    taught = {json.loads(x)["lesson"] for x in out.read_text().splitlines()}
    assert taught == {"m_weekday"} and res["left_to_the_hive"] == ["a unit conversion"]
    assert any("left to the hive" in s for s in said)


def test_every_child_reads_raw_data_and_answers_people_judged_and_dreams_try_twice():
    flow = (ROOT / ".github" / "workflows" / "grow.yml").read_text()
    train = next(ln for ln in flow.splitlines() if "python training/grow.py train" in ln)
    assert "READ=\"${{ vars.HIVE_READ || '40' }}\"; JUDGED=\"${{ vars.HIVE_JUDGED || '10' }}\"" in flow
    assert '--read "$READ" --judged "$JUDGED"' in train
    assert train.index("$VERSUS") < train.index("--read")  # a versus trial's own --read comes first and wins
    order = next(ln for ln in flow.splitlines() if "training/colab.py order" in ln)
    assert '--read "$READ" --judged "$JUDGED"' in order  # a child grown on the Colab GPU reads as much as one grown here
    assert "grow.py dream" in flow and "--tries 2" in flow
    assert "--own-rows old.jsonl" in flow  # lessons count what the hive found itself
