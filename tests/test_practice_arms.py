"""Practice split by orders (training/practice_arms.py, piece O1) and its first try by the kinds' age (piece F2): the arm
of each runner, what practice.json and the record say of each arm, the read's rows and the shell of the practice job.
No model: tasks are made up."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from training import exam, grow, grow_record, practice_arms, reads  # noqa: E402


def test_the_arm_is_set_by_the_runner_and_the_split_can_be_turned_off():
    got = [practice_arms.arm(s) for s in range(1, 13)]
    assert got == ["full", "short"] * 6 and got == [practice_arms.arm(str(s), "1") for s in range(1, 13)]
    assert got.count("short") == got.count("full") == 6
    assert all(practice_arms.arm(s, off) == "" for s in range(1, 13) for off in ("0", "off", ""))
    assert practice_arms.arm("x") == ""
    assert practice_arms.env_for("short") == {"HIVE_SHORT_ORDERS": "1"} and practice_arms.env_for("full") == {"HIVE_FULL_ORDERS": "1"}
    assert practice_arms.env_for("") == {}


def test_the_shell_of_the_practice_job_gives_each_runner_its_arm():
    import yaml
    wf = yaml.safe_load((ROOT / ".github" / "workflows" / "grow.yml").read_text())
    step = next(s for s in wf["jobs"]["practice"]["steps"] if s.get("name") == "Practice")
    assert step["env"]["ORDERS_AB"] == "${{ vars.HIVE_SHORT_ORDERS_AB || '1' }}"
    line = next(x for x in step["run"].splitlines() if "HIVE_ORDERS_ARM=" in x)
    for shard, ab, want in ((4, "1", "short"), (7, "1", "full"), (4, "0", "")):
        sh = line.replace("${{ matrix.shard }}", str(shard)) + '; printf %s "$HIVE_ORDERS_ARM"'
        out = subprocess.run(["bash", "-c", sh], cwd=ROOT, env=dict(os.environ, ORDERS_AB=ab), capture_output=True, text=True)
        assert out.returncode == 0 and out.stdout == want, (shard, ab, out.stderr)
    # the gate and the dreams are not split: no arm anywhere but practice
    for job in ("gate", "dream"):
        assert "HIVE_ORDERS_ARM" not in json.dumps(wf["jobs"][job]) and "HIVE_FULL_ORDERS" not in json.dumps(wf["jobs"][job])


def test_the_full_arm_gives_a_taught_member_the_full_orders_and_the_short_arm_the_short(monkeypatch):
    from team import solo
    seen = []

    class Stop(Exception):
        pass

    def chat(who, messages, **k):
        seen.append(messages[0]["content"])
        raise Stop
    monkeypatch.setattr(solo.ternary, "chat", chat)
    monkeypatch.setattr(solo, "give", lambda *a, **k: None)

    class Board:
        def log(self, *a):
            pass
    for env, want in (({}, solo.orders("t+")), ({"HIVE_SHORT_ORDERS": "1"}, solo.orders("t+")), ({"HIVE_FULL_ORDERS": "1"}, solo.orders("t"))):
        for k in ("HIVE_SHORT_ORDERS", "HIVE_FULL_ORDERS"):
            monkeypatch.delenv(k, raising=False)
        for k, v in env.items():
            monkeypatch.setenv(k, v)
        with pytest.raises(Stop):
            solo.member("add 2 and 3", 1, Board(), None, Path("/nonexistent"), 0.0, who="t80+g45trunk")
        assert seen[-1].split("Today is")[0] == want.split("Today is")[0], env


def test_the_kinds_age_is_read_from_the_registry():
    assert practice_arms.age("h_tab_group") == practice_arms.age("h_txt_ini") == practice_arms.age("h_prog_wrap") == "new"
    assert practice_arms.age("h_web") == practice_arms.age("m_percent") == practice_arms.age("h_walk") == "old"
    assert practice_arms.age("compound", [["m_days", "s", 0], ["h_tab_pivot", "s", 1]]) == "new"
    assert practice_arms.age("compound", [["m_days", "s", 0], ["m_units", "s", 1]]) == "old"
    assert practice_arms.age("nothing") == "" and practice_arms.age("compound", []) == ""
    from training import kinds
    assert sum(practice_arms.age(m.KIND) == "new" for m in kinds.ALL) == 24


def _practice_json(folder, arm, tasks):
    folder.mkdir(parents=True)
    (folder / "practice.json").write_text(json.dumps({"seed": 1, "arm": arm, "tasks": tasks}))


def _t(ok, first, seconds, age="old", timeout=False):
    return {"maker": "m_days", "level": 0, "ok": ok, "kind": "k", "some": ok, "first": first, "seconds": seconds, "timeout": timeout, "age": age}


def test_the_record_counts_each_arm_and_each_age(tmp_path):
    _practice_json(tmp_path / "rows-2", "short", [_t(True, True, 100), _t(True, False, 300, "new"), _t(False, False, 600, "new", True)])
    _practice_json(tmp_path / "rows-4", "short", [_t(True, True, 200)])
    _practice_json(tmp_path / "rows-1", "full", [_t(False, False, 400), _t(True, True, 200, "new")])
    # practice from before the split: no arm, no first try; it counts in neither
    _practice_json(tmp_path / "rows-9", "", [{"maker": "m_days", "level": 0, "ok": True, "kind": "k"}])
    got = practice_arms.summary([tmp_path])
    assert got["orders_ab"] == {"short": {"runners": 2, "first_try": [2, 4], "right": [3, 4], "seconds": 300, "timeouts": 1},
                                "full": {"runners": 1, "first_try": [1, 2], "right": [1, 2], "seconds": 300, "timeouts": 0}}
    assert got["first_try_by_age"] == {"old": [2, 3], "new": [1, 3]}
    assert practice_arms.summary([tmp_path / "rows-9"]) == {}
    assert practice_arms.ab_text(got["orders_ab"]) == ("short: first try 0.50 (2 of 4), right 0.75 (3 of 4), 300 s a task, 1 timed out, 2 runners; "
                                                       "full: first try 0.50 (1 of 2), right 0.50 (1 of 2), 300 s a task, 0 timed out, 1 runners")
    assert practice_arms.age_text(got["first_try_by_age"]) == "old kinds 0.67 (2 of 3); new kinds (K2) 0.33 (1 of 3)"


def test_the_gate_writes_both_into_the_record_line(tmp_path, monkeypatch):
    rec, body = tmp_path / "generations.jsonl", tmp_path / "body.json"
    body.write_text(json.dumps({"dna": "t80", "cells": [], "parents": {}}))
    monkeypatch.setattr(grow_record, "RECORD", rec)
    monkeypatch.setattr(grow_record, "BODY", body)
    (tmp_path / "got").mkdir()
    _practice_json(tmp_path / "prac" / "rows-2", "short", [_t(True, True, 100, "new")])
    _practice_json(tmp_path / "prac" / "rows-1", "full", [_t(False, False, 500)])
    assert grow_record.gate([str(tmp_path / "gate"), str(tmp_path / "got"), "g46", "--dna", "t80", "--practice", str(tmp_path / "prac")]) == 0
    line = json.loads(rec.read_text().splitlines()[-1])
    assert line["orders_ab"]["short"]["first_try"] == [1, 1] and line["orders_ab"]["full"]["first_try"] == [0, 1]
    assert line["first_try_by_age"] == {"old": [0, 1], "new": [1, 1]}


def test_the_read_has_one_row_for_the_orders_and_one_for_the_ages():
    ab = {"short": {"runners": 6, "first_try": [30, 48], "right": [35, 48], "seconds": 200, "timeouts": 1},
          "full": {"runners": 6, "first_try": [12, 48], "right": [20, 48], "seconds": 400, "timeouts": 5}}
    line = {"generation": "g46", "arms": {}, "orders_ab": ab, "first_try_by_age": {"old": [20, 40], "new": [5, 30]}}
    prev = {"generation": "g45", "arms": {}}
    rows = {r[0]: r for r in reads.top_table(line, prev, {}, [prev, line], 1)}
    assert rows["Right at the first try by orders (practice split by runner)"][1].startswith("short: first try 0.62 (30 of 48), right 0.73 (35 of 48), 200 s")
    assert "full: first try 0.25 (12 of 48)" in rows["Right at the first try by orders (practice split by runner)"][1]
    assert rows["Right at the first try, old kinds and K2's new kinds (practice)"][1:] == ("old kinds 0.50 (20 of 40); new kinds (K2) 0.17 (5 of 30)", "-", "-")
    # a generation that did not split: no orders row; the ages row says not measured
    rows = {r[0]: r for r in reads.top_table(prev, None, {}, [prev], 0)}
    assert "Right at the first try by orders (practice split by runner)" not in rows
    assert rows["Right at the first try, old kinds and K2's new kinds (practice)"][1] == "not measured"


def test_the_cycle_screen_shows_the_split_beside_the_first_try():
    import cycle
    rec = {"orders_ab": {"short": {"first_try": [3, 4]}, "full": {"first_try": [1, 4]}}, "first_try_by_age": {"old": [1, 2], "new": [0, 2]}}
    assert cycle.first_note(rec) == "practice; orders short 0.75, full 0.25; old kinds 0.50, new kinds 0.00"
    assert cycle.first_note({}) == "practice"


def test_practice_writes_the_arm_and_each_tasks_first_try_age_seconds_and_timeout(tmp_path, monkeypatch):
    def check(run, report):
        return False, "no"
    check.maker, check.level = "h_tab_group", 0
    monkeypatch.setattr(exam, "RUNS", tmp_path / "runs")
    monkeypatch.setattr(exam, "_memory", lambda empty: tmp_path)
    monkeypatch.setattr(exam, "exam", lambda *a, **k: iter([("h1_00", "hard", "a table", "group it", check)]))

    def sit_one(tag, tid, task, chk, home, kind=""):
        run = exam.RUNS / tag / tid
        (run / "members").mkdir(parents=True)
        events = [{"agent": "member1", "kind": "run"}, {"agent": "member1", "kind": "answer", "msg": "5"}]
        (run / "members" / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
        res = {"id": tid, "ok": True, "why": "", "seconds": 42, "note": "", "members": []}
        (run / "exam.json").write_text(json.dumps(res))
        return res
    monkeypatch.setattr(exam, "sit_one", sit_one)
    for k in ("HIVE_SHORT_ORDERS", "HIVE_FULL_ORDERS"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("HIVE_ORDERS_ARM", "full")
    out = tmp_path / "grow" / "rows.jsonl"
    got = grow.practice(5, 1, "mixed", out, log=lambda *a, **k: None)
    assert got["arm"] == "full" and os.environ.get("HIVE_FULL_ORDERS") == "1" and os.environ.get("HIVE_SHORT_ORDERS") is None
    d = json.loads(out.with_name("practice.json").read_text())
    assert d["arm"] == "full"
    t = d["tasks"][0]
    assert (t["first"], t["seconds"], t["timeout"], t["age"]) == (True, 42, False, "new")
    os.environ.pop("HIVE_FULL_ORDERS", None)
