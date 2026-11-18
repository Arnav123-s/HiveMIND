import json
import subprocess
import sys

import pytest

from training.experiments.hive_commitment_bench import parse, recover, run_case
from training.experiments.hive_commitment_cases import cases
from training.experiments.hive_commitments import Conflict, Journal, literal, proposals
from training.experiments.hive_work_order_replay import teach_and_transfer
from training.experiments.hive_work_order_rules import interpret, learn_exchange


def test_late_and_duplicate_writes_after_real_worker_loss(tmp_path):
    db = tmp_path / "work.sqlite"
    public = next(cases())["public"].copy()
    latest = public.pop("last")
    tasks = ["calendar", "pickup"]
    proc = subprocess.run([sys.executable, "-m", "training.experiments.hive_commitment_bench", "stage", str(db)],
                          input=json.dumps({"tasks": tasks, "opening_context": public}), text=True)
    assert proc.returncode == 37
    book, rival = Journal(db), Journal(db)
    saved, draft = recover(book, tasks[0])
    assert saved == public and "last" not in saved
    update = literal(latest, public, draft)
    assert rival.apply(tasks[0], "new", 1, update) == 2
    assert book.apply(tasks[0], "first", 0, draft) == 1
    assert book.apply(tasks[0], "new", 1, update) == 2
    with pytest.raises(Conflict):
        book.apply(tasks[0], "first", 0, update)
    with pytest.raises(Conflict):
        book.apply(tasks[0], "different", 1, public["opening"])
    with pytest.raises(ValueError):
        book.apply(tasks[0], "illegal", 2, {})
    assert book.read(tasks[0])[1:] == (2, update)
    assert rival.read(tasks[1])[1:] == (1, draft)


def test_same_transcript_requires_an_answer_before_commitment():
    left, right = list(cases())[12:14]
    public = left["public"]
    draft = literal(public["first"], public, public["opening"])
    assert right["public"] == public and left["expected"] != right["expected"]
    menu = proposals(public, draft)
    assert parse('{"pick":true}', public, menu) == ("invalid", None)
    assert parse('{"rows":[["day","site"],["day","site"]]}', public, None) == ("invalid", None)
    def answer(case):
        return {"text": json.dumps({"rows": [case["expected"][n] for n in public["names"]]})}
    guessed = run_case(left, public, draft, "full", lambda *args: answer(left))
    assert guessed["state_correct"] and not guessed["completed"]
    for case in (left, right):
        replies = iter([{"text": '{"ask":"Which item should change?"}'}, answer(case)])
        assert run_case(case, public, draft, "full", lambda *args: next(replies))["completed"]
        assert interpret(public, draft)[0] == "ask"
        assert interpret(public, draft, case["clarification"]) == ("apply", case["expected"])


def test_alias_requires_a_demonstrated_change_and_preserves_scope():
    unchanged = {"X": ["Friday", "East"], "Y": ["Monday", "West"]}
    with pytest.raises(ValueError):
        learn_exchange("Trade the dates.", unchanged, unchanged)
    study = teach_and_transfer()
    assert study["record"]["observed_field"] == 1
    assert all(x["correct_after"] for x in study["transfer"])
    assert any(x["field"] == 0 and not x["correct_before"] for x in study["transfer"])


def test_partial_understanding_cannot_authorize_an_extra_condition_or_unknown_site():
    public = next(cases())["public"]
    draft = literal(public["first"], public, public["opening"])
    name = public["names"][0]
    learned = {"verb": "trade", "operation": "exchange", "observed_field": 1}
    for text in (f"Move {name} to Tuesday at Ghosttown.", f"Move {name} to Tuesday after approval.",
                 "Trade both dates. Keep the dates.", "Trade the two sites with a third group."):
        assert interpret(dict(public, last=text), draft, learned=learned) == ("defer", None)
