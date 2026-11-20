"""A task of several parts is worked part by part (team/by_part.py): g53's practice lost most of its compound tasks
(1 of 28 right at the first try, 15 of 17 cap timeouts) because members spent the time on part A."""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts import selfreliance  # noqa: E402
from team import by_part, parts, solo  # noqa: E402

A, B = "Add 2 and 3 and tell me the sum.", "Multiply 4 by 5 and tell me the product."
TASK = parts.join([A, B])


def _hive(monkeypatch, replies):
    left = list(replies)

    def chat(*a, **k):
        r = left.pop(0)
        if r == "SLOW":
            time.sleep(30)
        return r if r == "DONE" else f"```python\n{r}\n```"
    monkeypatch.setattr(solo.llm, "chat", chat)
    return left


def test_plain_and_single_part_tasks_are_not_split(monkeypatch):
    assert by_part.split(A) == {}
    assert set(by_part.split(TASK)) == {"A", "B"}
    monkeypatch.setenv("HIVE_BY_PART", "0")
    assert by_part.split(TASK) == {}


def test_the_time_share_is_what_is_left_over_the_parts_left():
    assert by_part.shares(None, 2) is None
    assert by_part.shares(540, 2) == 270 and by_part.shares(300, 1) == 300 and by_part.shares(1, 2) == 5


def test_each_part_agrees_on_its_own_and_the_answers_are_joined(tmp_path, monkeypatch):
    _hive(monkeypatch, ["print('sum: 5')", "DONE", "print('The sum is 5')", "DONE",
                        "print('product: 20')", "DONE", "print('product 20')", "DONE"])
    out = solo.run(TASK, tmp_path / "a", "never", members=2)
    assert out["agreed"] and out["tries"] == 2
    assert out["answer"].startswith("PART A\n") and "\n\nPART B\n" in out["answer"] and "20" in out["answer"]
    assert parts.of_answer(out["report"]).keys() >= {"A", "B"}
    assert (tmp_path / "a" / "part_A" / "REPORT.md").exists() and (tmp_path / "a" / "part_B" / "REPORT.md").exists()
    d = json.loads((tmp_path / "a" / "members.json").read_text())
    assert d["agreed"] and d["agreeing"] == [1, 2]
    m1 = json.loads((tmp_path / "a" / "member1.json").read_text())
    assert "PART A" in m1["answer"] and "PART B" in m1["answer"] and m1["who"]


def test_a_part_nobody_agrees_on_is_not_delivered(tmp_path, monkeypatch):
    _hive(monkeypatch, ["print('sum: 5')", "DONE", "print('sum: 5')", "DONE",
                        "print('product: 20')", "DONE", "print('product: 21')", "DONE", "print('product: 22')", "DONE"])
    out = solo.run(TASK, tmp_path / "b", "never", members=2)
    assert not out["agreed"] and out["answer"] == "" and out["report"].startswith("Not confirmed")
    assert "PART B" in out["report"]


def test_a_part_that_uses_up_its_share_leaves_the_time_to_the_next(tmp_path, monkeypatch):
    monkeypatch.setenv("HIVE_CAP_SECONDS", "40")  # 10 s of work: a 5 s share for part A
    _hive(monkeypatch, ["SLOW", "print('product: 20')", "DONE", "print('product 20')", "DONE"])
    t = time.time()
    out = solo.run(TASK, tmp_path / "c", "never", members=2)
    assert time.time() - t < 20
    assert not out["agreed"] and "PART A" in out["report"]
    assert json.loads((tmp_path / "c" / "members.json").read_text())["by_part"]["B"]["agreed"]
    assert not solo._CAP["hit"] or solo._CAP["term"] is False


def test_a_member_with_one_program_per_part_is_right_first_try(tmp_path, monkeypatch):
    _hive(monkeypatch, ["print('sum: 5')", "DONE", "print('sum: 5')", "DONE",
                        "print('product: 20')", "DONE", "print('product: 20')", "DONE"])
    run = tmp_path / "t"
    run.mkdir()
    solo.run(TASK, run / "members", "never", members=2)
    (run / "exam.json").write_text(json.dumps({"ok": True}))
    assert selfreliance.one(run) == (True, True, [])
