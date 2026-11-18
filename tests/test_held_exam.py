"""X1: a fixed held-out exam each generation. The pulse drew only 3 to 9 held-out tasks a generation (g43 0 of 6,
g44 0 of 3, g45 0 of 9), which is noise; the fixed exam is the same 30 tasks every generation, 3 of each held-out
kind, sat by before and after in the gate, recorded by kind, shown in the read and counted by the keep-or-drop rule."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

import yaml

from training import exam, grow_record, kinds, progress, reads

ROOT = Path(__file__).resolve().parent.parent
# the exam's ids, fields, kinds and task texts as they are made today: a change here changes the exam every
# generation is compared on, so it is meant only when a held-out kind itself is changed (then write the new hash)
FIXED = "a0a9b93fab7244deb57e5e8cb1a1099f5812194d"


def _hash(tasks):
    return hashlib.sha1(json.dumps([[a, b, c, d] for a, b, c, d, _ in tasks]).encode()).hexdigest()


# ---- the fixed seeds ---------------------------------------------------------------------------------------------------
def test_the_same_thirty_tasks_every_time_three_of_each_held_out_kind():
    t = exam.held_exam()
    assert len(t) == 30 == 3 * len(kinds.HELD_OUT)
    assert _hash(t) == _hash(exam.held_exam()) == FIXED
    assert {c.maker for *_, c in t} == kinds.HELD_OUT
    assert all(tid == f"x_{c.maker}_{tid[-1]}" for tid, *_, c in t)
    assert len({task for _, _, _, task, _ in t}) == 30  # no task twice
    # nothing of the day, the run or the pulse's seed is in it: the pulse's own exams draw other tasks
    pulse = exam.exam(20000000 + 46 * 10 + 1, 8, (), "mixed")
    assert not {x[3] for x in t} & {x[3] for x in pulse}


def test_two_a_kind_is_the_first_two_of_three_and_the_eight_seats_share_it_whole():
    two = exam.held_exam(2)
    assert len(two) == 20 and [x[0] for x in two] == [x[0] for x in exam.held_exam() if not x[0].endswith("_2")]
    t = exam.held_exam()
    shares = [exam.held_share(t, s, 8) for s in range(1, 9)]
    assert sorted(x[0] for sh in shares for x in sh) == sorted(x[0] for x in t)
    assert [len(sh) for sh in shares] == [4, 4, 4, 4, 4, 4, 3, 3]  # 3 or 4 tasks a seat


def test_a_seat_writes_its_share_after_every_task(tmp_path, monkeypatch):
    seen = []

    def fake(tag, tid, task, check, home, timeout=None, kind=""):
        assert timeout == 900
        seen.append(json.loads((tmp_path / "held_3.json").read_text())["summary"]["tasks"])
        return {"id": tid, "ok": tid.endswith("_0"), "why": "", "seconds": 1, "note": "", "answer": "", "members": []}
    monkeypatch.setattr(exam, "sit_one", fake)
    line = exam.sit_held(3, 8, out=tmp_path, log=lambda *a, **k: None, seconds=900)
    d = json.loads((tmp_path / "held_3.json").read_text())
    assert seen == [0, 1, 2, 3] and line["tasks"] == 4 and d["summary"]["exam"] == "held"
    assert [t["id"] for t in d["tasks"]] == [x[0] for x in exam.held_share(exam.held_exam(), 3, 8)]
    assert all(t["maker"] in kinds.HELD_OUT for t in d["tasks"])


# ---- the record --------------------------------------------------------------------------------------------------------
def _seat(folder, arm, seat, right):
    """One seat's sitting of the fixed exam: its share, right where right(task id) says."""
    d = folder / f"held-{arm}-{seat}"
    d.mkdir(parents=True)
    tasks = [{"id": tid, "kind": k, "maker": c.maker, "ok": right(tid)} for tid, _, k, _, c in exam.held_share(exam.held_exam(), seat, 8)]
    (d / f"held_{seat}.json").write_text(json.dumps({"summary": {"exam": "held", "passed": sum(t["ok"] for t in tasks), "tasks": len(tasks)}, "tasks": tasks}))


def test_the_record_counts_by_kind_on_the_tasks_both_arms_sat(tmp_path):
    for s in range(1, 9):
        _seat(tmp_path, "before", s, lambda tid: tid.startswith(("x_h_sim", "x_h_edit")) and not tid.endswith("_2"))
        if s != 8:  # after lost its last seat: its three tasks are compared on neither side
            _seat(tmp_path, "after", s, lambda tid: tid.startswith(("x_h_sim", "x_h_edit", "x_h_two")))
    # what is not the exam's is not taken: a made-up id, and a kind that is not held out
    bad = tmp_path / "held-after-9"
    bad.mkdir()
    (bad / "held_9.json").write_text(json.dumps({"summary": {"exam": "held"}, "tasks": [{"id": "x_h_sim_7", "maker": "h_join", "ok": True}]}))
    h = grow_record.held_exam(tmp_path)
    lost = {x[0] for x in exam.held_share(exam.held_exam(), 8, 8)}
    assert h["tasks"] == 30 - len(lost) == 27
    b, a = h["before"], h["after"]
    assert b["by_kind"]["h_sim"] == [2, 3] and b["by_kind"]["h_edit"] == [2, 3] and b["kinds"] == [2, 10]
    assert a["by_kind"]["h_two"][0] == a["by_kind"]["h_two"][1] and a["kinds"] == [3, 10]
    assert (b["right"], b["of"], a["of"]) == (4, 27, 27)
    assert grow_record.held_exam(tmp_path / "none") == {}


def test_a_kind_is_passed_at_two_of_three():
    assert [grow_record.kind_passed(r, 3) for r in range(4)] == [False, False, True, True]
    assert grow_record.kind_passed(2, 2) and not grow_record.kind_passed(1, 2) and grow_record.kind_passed(1, 1)
    assert not grow_record.kind_passed(0, 0)


# ---- the keep-or-drop rule ---------------------------------------------------------------------------------------------
def _arm(passed, unpractised=(0, 0)):
    return {"passed": passed, "tasks": 64, "minutes": 100, "unpractised": list(unpractised), "seeds": 8, "kinds": {}, "by_lean": {},
            "hard": [4, 24], "easy": [28, 32], "several": [0, 8]}


def _held(before, after, of=30):
    return {"tasks": of, "before": {"right": before, "of": of, "by_kind": {}, "kinds": [0, 10]},
            "after": {"right": after, "of": of, "by_kind": {}, "kinds": [0, 10]}}


def _pair(before, after):
    return {"before": before, "after": after}


def test_a_loss_on_the_fixed_exam_with_no_gain_on_the_pulse_drops():
    keep, why = grow_record.decide(_pair(_arm(40), _arm(40)), grow=True, held=_held(9, 7))
    assert not keep and why.startswith("dropped: 40 against 40, the fixed held-out exam 7 against 9 with no gain on the pulse")
    # a gain on the pulse keeps it, the loss on the fixed exam said
    keep, why = grow_record.decide(_pair(_arm(40), _arm(41)), grow=True, held=_held(9, 7))
    assert keep and "the fixed held-out exam: after 7 of 30, before 9 of 30" in why
    # equal or better on the fixed exam keeps a tie on the pulse
    assert grow_record.decide(_pair(_arm(40), _arm(40)), grow=True, held=_held(9, 9))[0]
    assert grow_record.decide(_pair(_arm(40), _arm(40)), grow=True, held=_held(9, 12))[0]
    # the pulse still comes first: fewer passed there drops whatever the fixed exam says
    assert grow_record.decide(_pair(_arm(40), _arm(39)), grow=True, held=_held(5, 12))[1].startswith("dropped: 39 against 40")


def test_the_fixed_exam_stands_in_for_the_pulse_s_few_held_out_tasks():
    # a tie on the pulse with its few held-out tasks lost (0 against 2) is a gain on its other tasks, so the pulse's rule
    # keeps it; the fixed exam, sat by both, decides: lost there, it is dropped; held, it is kept
    before, after = _arm(35, (2, 6)), _arm(35, (0, 6))
    assert grow_record.decide(_pair(before, after), grow=True)[0]
    assert not grow_record.decide(_pair(before, after), grow=True, held=_held(8, 6))[0]
    assert grow_record.decide(_pair(before, after), grow=True, held=_held(8, 8))[0]
    # sat by one arm only, or not on the same tasks: the pulse's rule stands
    one = {"tasks": 30, "after": {"right": 6, "of": 30, "by_kind": {}, "kinds": [0, 10]}}
    assert grow_record.decide(_pair(before, after), grow=True, held=one)[0]
    assert grow_record.decide(_pair(before, after), grow=True, held=dict(_held(8, 6), after={"right": 6, "of": 29, "by_kind": {}, "kinds": [0, 10]}))[0]


def test_the_gate_records_the_fixed_exam(tmp_path, monkeypatch):
    gate, got, held = tmp_path / "gate", tmp_path / "got", tmp_path / "held"
    got.mkdir()
    for arm in ("before", "after"):
        for s in range(1, 9):
            d = gate / f"gate-{arm}-{s}"
            d.mkdir(parents=True)
            tasks = [{"id": f"e{i}", "kind": "units", "ok": True} for i in range(4)] + [{"id": f"h{i}", "kind": "a log", "ok": i < 2} for i in range(4)]
            (d / "x_mixed.json").write_text(json.dumps({"summary": {"passed": 6, "tasks": 8, "minutes": 9}, "tasks": tasks}))
            _seat(held, arm, s, (lambda tid: tid.startswith("x_h_sim")) if arm == "after" else (lambda tid: tid.startswith(("x_h_sim", "x_h_two"))))
    for c in ("g46code",):
        (got / f"t80.{c}.gguf").write_text("g")
        (got / f"t80.{c}.json").write_text(json.dumps({"rows": 10, "seconds": 600}))
    body, record = tmp_path / "body.json", tmp_path / "generations.jsonl"
    body.write_text(json.dumps({"dna": "t80", "cells": ["g45code"]}))
    monkeypatch.setattr(grow_record, "BODY", body)
    monkeypatch.setattr(grow_record, "RECORD", record)
    monkeypatch.setattr(grow_record, "STRENGTHS", tmp_path / "strengths.json")
    assert grow_record.gate([str(gate), str(got), "g46", "--dna", "t80", "--grow", "--held", str(held)]) == 0
    line = json.loads(record.read_text().splitlines()[-1])
    hx = line["held_exam"]
    assert hx["tasks"] == 30 and hx["after"]["right"] == 3 and hx["before"]["right"] == 6
    assert hx["after"]["kinds"] == [1, 10] and hx["before"]["kinds"] == [2, 10] and hx["after"]["by_kind"]["h_sim"] == [3, 3]
    assert line["verdict"] == "dropped" and "the fixed held-out exam 3 against 6 with no gain on the pulse" in line["why"]


# ---- the read and the graph --------------------------------------------------------------------------------------------
def test_the_read_shows_the_fixed_exam_with_the_pulse_beside_it():
    hx = {"tasks": 30, "after": {"right": 13, "of": 30, "by_kind": {}, "kinds": [4, 10]}, "before": {"right": 9, "of": 30, "by_kind": {}, "kinds": [3, 10]}}
    arm = {"passed": 40, "tasks": 64, "seeds": 8, "easy": [30, 32], "hard": [10, 32], "unpractised": [0, 9], "kinds": {}}
    line = {"generation": "g46", "arms": {"after": arm, "before": dict(arm)}, "held_exam": hx}
    prev = {"generation": "g45", "arms": {"after": dict(arm, unpractised=[0, 3])}}
    rows = dict((r[0], r[1:]) for r in reads.top_table(line, prev, {}, [prev, line], 1))
    now, last, before = rows["Hard kinds never practised (held out)"]
    assert now == "4 of 10 kinds (13 of 30 tasks of the fixed exam; pulse 0 of 9)"
    assert last == "0 of 3" and before == "3 of 10 kinds (9 of 30 tasks of the fixed exam; pulse 0 of 9)"
    # scripts/cycle.py reads the bar from the row: the share of held-out kinds passed
    import re
    m = re.search(r"never practised \(held out\) \| (\d+) of (\d+)", f"| Hard kinds never practised (held out) | {now} |")
    assert m.groups() == ("4", "10")


def test_carry_svg_draws_the_fixed_exam_beside_the_pulse():
    a = {"passed": 40, "tasks": 64, "unpractised": [0, 6]}
    gens = [{"generation": "g45", "dna": "t80", "arms": {"after": a}},
            {"generation": "g46", "dna": "t80", "arms": {"after": a}, "held_exam": {"after": {"right": 13, "of": 30, "kinds": [4, 10]}}},
            {"generation": "g47", "dna": "t80", "arms": {"after": a}, "held_exam": {"after": {"right": 16, "of": 30, "kinds": [5, 10]}}}]
    svg = progress.share_chart(gens, progress._carried, "t", "n", also=(progress._fixed, "fixed exam", "kinds"))
    assert svg.count('class="sfixed"') == 3 and 'class="lfixed"' in svg and "5 of 10 kinds" in svg and "fixed exam" in svg
    assert progress._fixed(gens[0]) is None and progress._fixed(gens[1]) == (4, 10)


# ---- the workflow ------------------------------------------------------------------------------------------------------
def _flow():
    return yaml.safe_load((ROOT / ".github" / "workflows" / "grow.yml").read_text())


def test_before_and_after_sit_it_in_the_gate_and_it_never_fails_a_seat():
    steps = _flow()["jobs"]["gate"]["steps"]
    i = next(k for k, s in enumerate(steps) if s.get("name", "").startswith("The fixed held-out exam"))
    sit, up = steps[i], steps[i + 1]
    pulse_up = next(k for k, s in enumerate(steps) if (s.get("with") or {}).get("name") == "gate-${{ matrix.arm }}-${{ matrix.seed }}")
    assert pulse_up < i  # after the pulse is uploaded: it cannot change the pulse's numbers
    assert sit["continue-on-error"] is True and sit["timeout-minutes"] <= 40 and "--seconds 900" in sit["run"]
    assert "matrix.arm == 'before'" in sit["if"] and "matrix.arm == 'after'" in sit["if"]
    assert up["with"]["name"] == "held-${{ matrix.arm }}-${{ matrix.seed }}" and up["continue-on-error"] is True
    rec = _flow()["jobs"]["record"]["steps"]
    dl = next(s for s in rec if (s.get("with") or {}).get("pattern") == "held-*-[0-9]")
    assert dl["continue-on-error"] is True and dl["with"]["path"] == "held"
    assert "--held held" in next(s for s in rec if s.get("name", "").startswith("The record (")).get("run")


def test_the_seat_step_runs_as_github_runs_it(tmp_path):
    step = next(s for s in _flow()["jobs"]["gate"]["steps"] if s.get("name", "").startswith("The fixed held-out exam"))
    shim = tmp_path / "bin"
    shim.mkdir()
    (shim / "python").write_text('#!/bin/bash\necho "$@" > args.txt\n')
    (shim / "python").chmod(0o755)
    run = step["run"].replace("${{ matrix.seed }}", "3")
    p = subprocess.run(["bash", "-e", "-c", run], cwd=tmp_path, env=dict(os.environ, PATH=f"{shim}:{os.environ['PATH']}"), capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert (tmp_path / "args.txt").read_text().split() == ["training/exam.py", "held", "--seat", "3", "--seats", "8", "--per", "3", "--seconds", "900"]
    assert exam.main(["show", "--level", "held"]) == 0
