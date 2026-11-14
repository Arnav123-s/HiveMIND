import json

from team import ternary
from training import exam, grow_record


def test_a_weakness_goes_to_the_cell_strongest_nearest_to_it(monkeypatch, tmp_path):
    monkeypatch.setenv("HIVE_MEMBERS", "t17+g1code,t17+g1data,t17+g1words")
    monkeypatch.setenv("HIVE_SEATING", "strength")
    table = {"code": {"kind": {"a simulation": [0, 4]}, "organ": {"code": [3, 10]}},
             "data": {"kind": {"a simulation": [3, 4]}, "organ": {"code": [5, 10]}},
             "words": {"kind": {}, "organ": {"code": [1, 10]}}}
    f = tmp_path / "strengths.json"
    f.write_text(json.dumps({"by_lean": table}))
    monkeypatch.setattr(ternary, "STRENGTHS", f)
    task = "Calculate how many steps the robot program takes"
    assert ternary.organ(task) == "code"
    # on a kind it has met, the data cell was right 3 of 4 times: it sits first, though the task is code's organ
    assert ternary.seating(task, "a simulation")[0] == "t17+g1data"
    # a kind nobody has met: the cell best on the task's organ (the nearer degree) goes first
    assert ternary.seating(task, "something never seen")[:2] == ["t17+g1data", "t17+g1code"]
    # not asked for, or no records: the cells that lean to the organ first, as before
    monkeypatch.delenv("HIVE_SEATING")
    assert ternary.seating(task, "a simulation")[0] == "t17+g1code"
    monkeypatch.setenv("HIVE_SEATING", "strength")
    f.write_text("{}")
    assert ternary.seating(task, "a simulation")[0] == "t17+g1code"


def test_each_members_own_answer_is_checked(tmp_path):
    home = tmp_path / "members"
    (home / "work").mkdir(parents=True)
    (home / "work" / "out.txt").write_text("42")
    (home / "member1.json").write_text(json.dumps({"who": "t17+g1code", "answer": "42", "work": str(home / "work")}))
    (home / "member2.json").write_text(json.dumps({"who": "t17+g1data", "answer": "41", "work": str(home / "nowhere")}))
    check = lambda run, report: ((run / "work" / "out.txt").exists() and "42" in report, "")  # noqa: E731
    assert exam.each_member(tmp_path, check) == [{"who": "t17+g1code", "ok": True}, {"who": "t17+g1data", "ok": False}]


def test_the_gate_records_strengths_for_the_nightly_line_only(tmp_path, monkeypatch):
    folder, got = tmp_path / "gate", tmp_path / "got"
    got.mkdir()
    for arm, p in (("dna", 2), ("before", 3), ("after", 5)):
        d = folder / f"gate-{arm}-1"
        d.mkdir(parents=True)
        tasks = [{"kind": "units", "ok": True, "task": "Calculate 3 + 4",
                  "members": [{"who": "t17+g7code", "ok": True}, {"who": "t17+g7words", "ok": False}]}]
        (d / "x.json").write_text(json.dumps({"summary": {"passed": p, "tasks": 8, "minutes": 5}, "tasks": tasks}))
    (got / "t17.g8code.gguf").write_text("x")
    (got / "t17.g8code.json").write_text(json.dumps({"rows": 3, "seconds": 60}))
    body, strengths, record = tmp_path / "body.json", tmp_path / "strengths.json", tmp_path / "g.jsonl"
    body.write_text(json.dumps({"dna": "t17", "generation": 7, "cells": ["g7code", "g7words"]}))
    monkeypatch.setattr(grow_record, "BODY", body)
    monkeypatch.setattr(grow_record, "STRENGTHS", strengths)
    monkeypatch.setattr(grow_record, "RECORD", record)
    grow_record.gate([str(folder), str(got), "g8", "--trial"])
    assert not strengths.exists()
    grow_record.gate([str(folder), str(got), "g8"])
    s = json.loads(strengths.read_text())["by_lean"]
    assert s["code"]["kind"]["units"] == [1, 1] and s["words"]["organ"]["code"] == [0, 1]
