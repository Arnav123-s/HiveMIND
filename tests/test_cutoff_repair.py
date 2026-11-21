import pytest
from team import solo, ternary


class Log:
    def log(self, *args):
        pass


def run(monkeypatch, tmp_path, turns, enabled=True):
    requests = []
    example = iter(turns)
    def ask(member, endpoint, cell, path, body, cap):
        assert path == "/v1/chat/completions"
        assert body["max_tokens"] == cap
        requests.append(cap)
        content, reason, used = next(example)
        return {"choices": [{"message": {"content": content}, "finish_reason": reason}],
                "usage": {"completion_tokens": used}}
    monkeypatch.setattr(ternary, "up", lambda member: "fixture")
    monkeypatch.setattr(ternary, "_ask", ask)
    monkeypatch.setattr(solo, "TURNS", 3)
    monkeypatch.setattr(solo, "LONG", 8)
    monkeypatch.setenv("HIVE_CUTOFF_REPAIR", str(int(enabled)))
    task = "Print the number 7."
    board = Log()
    result = solo.member(task, 1, board, solo.Guard(board, approve="never", goal=task),
                         tmp_path, 0., who="t80+fixture")
    return result, requests


BROKEN = "```python\nprint("
GOOD = "```python\nprint(7)\n```"


def test_real_length_metadata_repairs_incomplete_python_within_same_total(monkeypatch, tmp_path):
    result, caps = run(monkeypatch, tmp_path, [(BROKEN, "length", 8), (GOOD, "stop", 13), ("DONE", "stop", 2)])
    assert caps == [8, 16, 3]
    assert result["answer"] == "7"
    assert result["hints"] == ["reply_cutoff"]
    assert result["turns"] == 3
    assert any("output limit" in m["content"] for m in result["messages"] if m["role"] == "user")


@pytest.mark.parametrize("enabled,reason,count", [(False, "length", 8), (True, "stop", 8),
                                                  (True, "length", 4), (True, "length", None)])
def test_default_and_unconfirmed_cutoffs_keep_normal_budget(monkeypatch, tmp_path, enabled, reason, count):
    result, caps = run(monkeypatch, tmp_path, [(BROKEN, reason, count), (GOOD, "stop", 5), ("DONE", "stop", 2)], enabled)
    assert caps == [8, 8, 8]
    assert result["answer"] == "7" and "reply_cutoff" not in result["hints"]


def test_complete_program_at_cap_keeps_its_result(monkeypatch, tmp_path):
    result, caps = run(monkeypatch, tmp_path, [(GOOD, "length", 8), ("DONE", "stop", 2)])
    assert caps == [8, 8] and result["answer"] == "7" and "reply_cutoff" not in result["hints"]


def test_fully_spent_tokens_end_the_member_without_an_extra_call(monkeypatch, tmp_path):
    result, caps = run(monkeypatch, tmp_path, [(BROKEN, "length", 8), (BROKEN, "length", 16)])
    assert caps == [8, 16] and result["turns"] == 2 and result["answer"] == ""
