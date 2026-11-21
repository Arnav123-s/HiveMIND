"""The paired gate (docs/DECISIONS.md, order 1 to B, part b): a body that grows sits before and after its children
on the same 8 seeds, and the record keeps or drops the children by itself."""
import json
import re
from pathlib import Path

import yaml

from training import grow_record

ROOT = Path(__file__).resolve().parent.parent


def _arm(passed, tasks=64, easy=(28, 32), hard=(4, 24), seeds=8):
    return {"passed": passed, "tasks": tasks, "minutes": 100, "unpractised": [0, 0], "seeds": seeds, "kinds": {}, "by_lean": {},
            "hard": list(hard), "easy": list(easy), "several": [0, 8]}


def _pair(before, after):
    return {"dna": _arm(0, 0, (0, 0), (0, 0), 0), "before": before, "after": after, "versus": _arm(0, 0, (0, 0), (0, 0), 0)}


def test_decide_keeps_and_drops_rightly():
    same = _arm(35, easy=(25, 32), hard=(4, 24))
    keep, why = grow_record.decide(_pair(same, dict(same)), grow=True)  # after = before: a tie keeps
    assert keep and why.startswith("kept: 35 against 35")
    keep, why = grow_record.decide(_pair(_arm(35), _arm(34, easy=(28, 32))), grow=True)  # 1 under in all
    assert not keep and why.startswith("dropped: 34 against 35")
    keep, why = grow_record.decide(_pair(_arm(35, easy=(28, 32), hard=(4, 24)), _arm(35, easy=(25, 32), hard=(7, 24))), grow=True)
    assert keep  # equal in all: easy lost 3, hard gained 3
    assert grow_record.decide(_pair(_arm(35), _arm(40, easy=(30, 32))), grow=True)[0]  # after better
    assert not grow_record.decide(_pair(_arm(35, easy=(28, 32)), _arm(33, easy=(26, 32))), grow=True)[0]  # 2 under: dropped now
    assert not grow_record.decide(_pair(_arm(35), _arm(35, seeds=7)), grow=True)[0]  # not the same seeds


def test_the_real_g43_and_g45_are_dropped_and_g42_kept():
    # the arms as training/reports/generations.jsonl holds them
    g43 = _pair(_arm(54, easy=(32, 32), hard=(22, 32)), _arm(52, easy=(32, 32), hard=(20, 32)))
    g45 = _pair(_arm(47, easy=(32, 32), hard=(15, 32)), _arm(45, easy=(32, 32), hard=(13, 32)))
    g42 = _pair(_arm(54, easy=(31, 32), hard=(23, 32)), _arm(54, easy=(31, 32), hard=(23, 32)))
    assert grow_record.decide(g43, grow=True)[1].startswith("dropped: 52 against 54")
    assert grow_record.decide(g45, grow=True)[1].startswith("dropped: 45 against 47")
    assert grow_record.decide(g42, grow=True)[1].startswith("kept: 54 against 54")


def test_a_held_out_loss_with_no_gain_elsewhere_drops():
    before, after = _arm(35), _arm(35)
    before["unpractised"], after["unpractised"] = [2, 6], [0, 6]
    keep, why = grow_record.decide(_pair(before, after), grow=True)  # held out 0 against 2, the rest +2: a gain
    assert keep
    before["unpractised"], after["unpractised"] = [2, 6], [1, 6]
    after["passed"] = 36  # held out lost 1, the rest gained 2: kept
    assert grow_record.decide(_pair(before, after), grow=True)[0]
    # held out 0 against 2 and the rest the same (33 and 33): a drop
    after["unpractised"], after["passed"] = [0, 6], 33
    keep, why = grow_record.decide(_pair(before, after), grow=True)
    assert not keep and why.startswith("dropped: 33 against 35")


def _sitting(folder, arm, seed, passed_easy, passed_hard, easy=4, hard=4):
    d = folder / f"gate-{arm}-{seed}"
    d.mkdir(parents=True)
    tasks = ([{"id": f"e{i}", "kind": "units", "ok": i < passed_easy} for i in range(easy)]
             + [{"id": f"h{i}", "kind": "a log", "ok": i < passed_hard} for i in range(hard)])
    (d / "x_mixed.json").write_text(json.dumps({"summary": {"passed": passed_easy + passed_hard, "tasks": easy + hard, "minutes": 9}, "tasks": tasks}))


def _gen(tmp_path, monkeypatch, gen, after_easy, seeds=8):
    folder, got = tmp_path / gen / "gate", tmp_path / gen / "got"
    got.mkdir(parents=True)
    for s in range(1, seeds + 1):
        _sitting(folder, "before", s, 3, 1)
        _sitting(folder, "after", s, after_easy if s == 1 else 3, 1)
    for c in (f"{gen}code", f"{gen}words"):
        (got / f"t80.{c}.gguf").write_text("x")
        (got / f"t80.{c}.json").write_text(json.dumps({"rows": 3, "seconds": 60}))
    return grow_record.gate([str(folder), str(got), gen, "--dna", "t80", "--grow"])


def _files(tmp_path, monkeypatch):
    body, record = tmp_path / "body.json", tmp_path / "g.jsonl"
    body.write_text(json.dumps({"dna": "t80", "generation": 7, "cells": ["g7code", "g7words"], "trunk": "g7trunk", "levels": {"units": 2}}))
    monkeypatch.setattr(grow_record, "BODY", body)
    monkeypatch.setattr(grow_record, "STRENGTHS", tmp_path / "strengths.json")
    monkeypatch.setattr(grow_record, "RECORD", record)
    return body, record


def test_a_dropped_generation_leaves_the_body_and_says_so_with_both_arms(tmp_path, monkeypatch):
    body, record = _files(tmp_path, monkeypatch)
    was = body.read_text()
    _gen(tmp_path, monkeypatch, "g8", after_easy=0)  # after: 3 under before on easy (and in all)
    line = json.loads(record.read_text().splitlines()[-1])
    assert line["verdict"] == "dropped" and not line["kept"] and body.read_text() == was
    assert line["paired"]["before"]["passed"] == 32 and line["paired"]["after"]["passed"] == 29 and line["paired"]["after"]["tasks"] == 64
    assert line["paired"]["before"]["easy"] == [24, 32] and line["paired"]["after"]["easy"] == [21, 32] and line["paired"]["after"]["hard"] == [8, 32]
    assert line["body_after"] == ["g7code", "g7words"] and line["paired"]["seeds"] == [str(s) for s in range(1, 9)]
    _gen(tmp_path, monkeypatch, "g9", after_easy=3)  # after = before: kept, the children join
    line = json.loads(record.read_text().splitlines()[-1])
    assert line["verdict"] == "kept" and json.loads(body.read_text())["cells"] == ["g7code", "g7words", "g9code", "g9words"]


def test_a_seat_that_died_on_one_side_is_left_out_of_both(tmp_path, monkeypatch):
    body, record = _files(tmp_path, monkeypatch)
    _gen(tmp_path, monkeypatch, "g8", after_easy=3)
    import shutil
    shutil.rmtree(tmp_path / "g8" / "gate" / "gate-after-5")
    record.write_text("")
    folder = tmp_path / "g8" / "gate"
    arms, seeds = grow_record.paired(folder)
    assert seeds == ["1", "2", "3", "4", "6", "7", "8"] and arms["before"]["seeds"] == arms["after"]["seeds"] == 7


def test_three_drops_running_stop_the_restart(tmp_path, monkeypatch, capsys):
    record = tmp_path / "g.jsonl"
    rows = [{"generation": "g30", "verdict": "kept"}, {"generation": "g31", "verdict": "dropped"},
            {"generation": "g32", "verdict": "dropped"}, {"generation": "g33", "trial": True, "verdict": "dropped"}]
    record.write_text("".join(json.dumps(r) + "\n" for r in rows))
    assert grow_record.restart([str(record)]) == 0  # two drops of the line (a trial is not of the line)
    with open(record, "a") as f:
        f.write(json.dumps({"generation": "g34", "verdict": "dropped", "why": "after is 4 under"}) + "\n")
    assert grow_record.restart([str(record)]) == 1
    out = capsys.readouterr().out
    assert "the line stops" in out and "g34: after is 4 under" in out
    with open(record, "a") as f:
        f.write(json.dumps({"generation": "g35", "verdict": "kept"}) + "\n")
    assert grow_record.restart([str(record)]) == 0
    # the old records, before the paired gate, have no verdict: they never stop the line
    record.write_text("".join(json.dumps({"generation": f"g{g}", "kept": False}) + "\n" for g in range(3)))
    assert grow_record.restart([str(record)]) == 0


def _workflow():
    return yaml.safe_load((ROOT / ".github" / "workflows" / "grow.yml").read_text())


def test_the_gate_sits_before_and_after_on_the_same_eight_seeds_for_a_growing_body():
    gate = _workflow()["jobs"]["gate"]
    matrix = gate["strategy"]["matrix"]
    grow_arms = re.search(r"needs\.plan\.outputs\.grow && '(\[[^']*\])'", matrix["arm"]).group(1)
    assert json.loads(grow_arms) == ["before", "after"]
    seeds = json.loads(re.search(r"\|\| '(\[[^']*\])'\)", matrix["seed"]).group(1))
    assert seeds == list(range(1, 9)) and len(json.loads(grow_arms)) * len(seeds) == 16 <= 20
    # every arm sits the same seed for the same matrix.seed: the arm is not in the exam's seed
    sit = next(s["run"] for s in gate["steps"] if "exam.py sit" in s.get("run", ""))
    seed_expr = re.search(r"--seed (\$\(\(.*?\)\))", sit).group(1)
    assert "matrix.seed" in seed_expr and "matrix.arm" not in seed_expr and "--tasks 8" in sit
    # before is the body as it answers, fetched from the release; trials keep their own arms
    who = next(s["run"] for s in gate["steps"] if s.get("name") == "Who sits (the arm)")
    assert 'lineage.py members "$DNA"' in who.split("before)")[1].split(";;")[0]
    assert '["dna","before","after"]' in matrix["arm"]


def test_the_record_does_not_restart_after_three_drops():
    steps = _workflow()["jobs"]["record"]["steps"]
    again = next(s for s in steps if s.get("name", "").startswith("Grow again"))
    run = again["run"]
    assert "grow_record.py restart" in run and run.index("grow_record.py restart") < run.index("gh workflow run")
