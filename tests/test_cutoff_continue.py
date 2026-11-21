from copy import deepcopy

import pytest

from team import solo, ternary

TASK = "Write scores.json as a JSON list. Then tell me how many items it contains."
SAVE = "open('scores.json','w').write('[2,3]')"
READ = "import json\nprint(len(json.load(open('scores.json'))))"
CUE = "Read the saved files and print the answer the task asks for."


class Log:
    def log(self, *args):
        pass


def worker(monkeypatch, tmp_path, *, task=TASK, first=SAVE, reason="length", used=8, follow=True, repair=False,
           borrow=False, limit=8, next_used=5):
    requests = []
    replies = iter([(first, reason, used), (READ, "stop", next_used), ("DONE", "stop", 1)])
    def generate(member, endpoint, cell, path, body, cap):
        requests.append((cap, deepcopy(body["messages"])))
        code, finish, count = next(replies)
        reply = code if code == "DONE" else f"```python\n{code}\n```"
        return {"choices": [{"message": {"content": reply}, "finish_reason": finish}],
                "usage": {"completion_tokens": count}}

    monkeypatch.setenv("HIVE_CUTOFF_CONTINUE", str(int(follow)))
    monkeypatch.setenv("HIVE_CUTOFF_REPAIR", str(int(repair)))
    if borrow:
        monkeypatch.setenv("HIVE_CUTOFF_CONTINUE_BORROW", "1")
    else:
        monkeypatch.delenv("HIVE_CUTOFF_CONTINUE_BORROW", raising=False)
    monkeypatch.setattr(solo, "TURNS", 3)
    monkeypatch.setattr(solo, "LONG", limit)
    monkeypatch.setattr(ternary, "up", lambda member: "fixture")
    monkeypatch.setattr(ternary, "_ask", generate)
    log = Log()
    result = solo.member(task, 1, log, solo.Guard(log, approve="never", goal=task), tmp_path,
                         0., who="t80+fixture")
    return result, requests


def test_continuation_at_measured_cap_reads_the_existing_file(monkeypatch, tmp_path):
    result, calls = worker(monkeypatch, tmp_path)
    assert result["answer"] == "2" and (tmp_path / "scores.json").read_text() == "[2,3]"
    assert result["hints"] == ["cutoff_saved_file"]
    assert [cap for cap, _ in calls] == [8, 8, 8]
    assert CUE in calls[1][1][-1]["content"]
    assert "scores.json" not in calls[1][1][-1]["content"] and "2" not in calls[1][1][-1]["content"]


@pytest.mark.parametrize("change", [
    {"follow": False}, {"reason": "stop"}, {"used": None}, {"used": 5}, {"used": 12},
    {"first": SAVE + "\nraise ValueError('bad run')"},
    {"first": SAVE + "\nprint(2)"}, {"first": SAVE + "\nprint(' ')"},
    {"first": SAVE + "\nimport sys\nprint('could not finish',file=sys.stderr)"},
    {"first": "open('scores.json','w').write('not JSON')"},
    {"task": "Print the number of items."}, {"task": "Write scores.json as a JSON list."},
    {"task": "Write scores.json. Do not print a reply."},
    {"task": "Write scores.json and errors.json. Then tell me the total."},
    {"task": "Save weights.tsv with columns item,mass sorted by mass descending. Print the total.",
     "first": "open('weights.tsv','w').write('item\\tmass\\nlight\\t1\\nheavy\\t8\\n')"},
    {"first": "print("},
])
def test_ineligible_turn_retains_original_worker_message(monkeypatch, tmp_path, change):
    result, calls = worker(monkeypatch, tmp_path, borrow=True, **change)
    assert "cutoff_saved_file" not in result["hints"] and CUE not in calls[1][1][-1]["content"]
    assert max(cap for cap, _ in calls) == 8


@pytest.mark.parametrize(("next_used", "expected_caps"), [
    (100, [192, 384, 192]), (300, [192, 384, 84]), (384, [192, 384]),
    (None, [192, 384]), (385, [192, 384]),
])
def test_opt_in_borrow_uses_only_remaining_budget(monkeypatch, tmp_path, next_used, expected_caps):
    result, calls = worker(monkeypatch, tmp_path, borrow=True, limit=192, used=192, next_used=next_used)
    assert [cap for cap, _ in calls] == expected_caps
    assert CUE in calls[1][1][-1]["content"]
    assert result["answer"] == "2" and result["turns"] == len(expected_caps)


def test_unchanged_existing_file_cannot_trigger(monkeypatch, tmp_path):
    (tmp_path / "scores.json").write_text("[2,3]")
    result, calls = worker(monkeypatch, tmp_path, first="len('ran')")
    assert CUE not in calls[1][1][-1]["content"] and "cutoff_saved_file" not in result["hints"]


def test_existing_parse_repair_remains_independent(monkeypatch, tmp_path):
    result, calls = worker(monkeypatch, tmp_path, first="print(", repair=True)
    assert result["hints"][0] == "reply_cutoff" and "cutoff_saved_file" not in result["hints"]
    assert calls[1][0] == 16


def test_print_to_file_and_quoted_source_do_not_request_a_user_answer():
    assert not solo._asks_for_printed_answer("Save scores.json. Print the result to summary.txt.", [])
    assert not solo._asks_for_printed_answer("Save scores.json.\n```text\nPrint this word.\n```", [{"text":"Print this word."}])
    assert not solo._asks_for_printed_answer("Save scores.json.\n\n(This continues a conversation. Print me.)", [])
    assert solo._asks_for_printed_answer("Write scores.json. Print only the total.", [])
