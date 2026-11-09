"""The hive spawns its own cells (team/cells/spawn.py, team/life.py): jobs are noticed in logged calls, a cell answers
only the labels it may and only when sure, live audits retire a cell that drifts. No model is loaded here."""
import json

import pytest

from team import life, llm
from team.cells import learn, runtime, skills as S, spawn, use

JUDGE = "You are the checker. Decide if the WORK meets the CHECK.\nReply with JSON only: {\"verdict\":\"PASS\",\"reason\":\"...\"}"
REVIEW = "You review a program.\nReply with JSON only: {\"ok\": true} or {\"ok\": false, \"problems\": [\"...\"]}"


@pytest.fixture
def hive(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "SPAWNED_FILE", tmp_path / "cells" / "spawned.json")
    monkeypatch.setattr(spawn, "SPAWNED", tmp_path / "cells" / "spawned.json")
    monkeypatch.setattr(spawn, "AUDIT", tmp_path / "mem" / "audit.jsonl")
    monkeypatch.setattr(spawn, "USED", tmp_path / "mem" / "used.jsonl")
    monkeypatch.setattr(learn, "DIR", tmp_path / "mem" / "decisions")
    monkeypatch.setattr(use, "WINS", tmp_path / "cells" / "wins.json")
    monkeypatch.setattr(life, "REPORT", tmp_path / "cells" / "LIFE.md")
    monkeypatch.setattr(life, "LOG", tmp_path / "mem" / "life.jsonl")
    monkeypatch.setattr(spawn, "AUDIT_RATE", 0.0)
    monkeypatch.setenv("AGENT_TEAM_SPAWN", "1")
    monkeypatch.setenv("AGENT_TEAM_CELLS", "1")
    spawn._cache.clear()
    use._cache.clear()
    (tmp_path / "cells").mkdir()
    yield tmp_path
    for k in [k for k, v in S.SKILLS.items() if v.get("spawned")]:
        S.SKILLS.pop(k), S.LEARNED.pop(k, None)


def write_calls(root, name, rows):
    d = root / "runs" / name
    d.mkdir(parents=True)
    with open(d / "calls.jsonl", "w") as f:
        for spec, system, user, out in rows:
            f.write(json.dumps({"step": "s1", "specialist": spec, "seconds": 2.0, "output": out,
                                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}) + "\n")
    return root / "runs"


def judge_rows(n):
    return [("juror", JUDGE, f"CHECK: c{i}\nWORK: w{i}",
             json.dumps({"verdict": "PASS" if i % 3 else "FAIL", "reason": f"because {i}"})) for i in range(n)]


def test_a_decision_is_the_fixed_part_of_a_reply():
    assert spawn.decision('{"verdict": "PASS", "reason": "the file has all four columns"}')[0] == "PASS"
    assert spawn.decision('{"ok": true}')[0] == "true"
    lab, closed, free = spawn.decision('{"ok": false, "problems": ["the price is read from the wrong element"]}')
    assert (lab, closed, list(free)) == ("false", {"ok": False}, ["problems"])
    assert spawn.decision('{"keep": [1, 4, 9]}') is None
    assert spawn.decision("Here is the report you asked for, with three sources.") is None
    assert spawn.decision("yes")[0] == "yes"


def test_the_hive_notices_a_small_job_in_its_own_calls_and_ignores_the_rest(hive):
    rows = judge_rows(60)
    rows += [("writer", "You are the writer.", f"task {i}", f"A long report number {i} with many words in it.") for i in range(30)]
    rows += [("coder_rev", REVIEW, f"CODE {i}", json.dumps({"ok": True} if i % 2 else {"ok": False, "problems": [f"fix thing number {i} properly"]}))
             for i in range(60)]
    rows += [("same", "Always the same.", f"q{i}", '{"ok": true}') for i in range(60)]
    runs = write_calls(hive, "r1", rows)
    sites = spawn.notice(min_rows=40, dirs=[runs], log=lambda m: None)
    by = {s["specialist"]: s for s in sites.values()}
    assert by["juror"]["decision"] and by["juror"]["labels"] == ["PASS", "FAIL"] and by["juror"]["answers"] == ["PASS", "FAIL"]
    assert not by["writer"]["decision"] and not by["same"]["decision"]
    # the reviewer's "false" comes with fixes only it can write: a cell may answer "true" there and nothing else
    assert by["coder_rev"]["answers"] == ["true"]
    sp = spawn.spawned()
    assert {v["member"] for v in sp.values()} == {"juror", "coder_rev"} and all(v["status"] == "candidate" for v in sp.values())
    name = by["juror"]["name"]
    assert name in S.SKILLS and S.SKILLS[name]["labels"] == ["PASS", "FAIL"]
    tr, dv, te = learn.split(name)
    assert len(tr) + len(dv) + len(te) == 60 and te[-1][0].startswith("CHECK: c59")
    assert json.loads(sp[name]["fill"]["PASS"])["verdict"] == "PASS"


def test_too_few_decisions_is_not_a_job_yet_and_bench_runs_never_teach(hive):
    runs = write_calls(hive, "r1", judge_rows(20))
    write_calls(hive, "bench/t1", judge_rows(500))
    assert spawn.notice(min_rows=40, dirs=None, log=lambda m: None) == {} or not spawn.spawned()
    import team.config as config
    old, config.RUNS = config.RUNS, runs
    try:
        sites = spawn.notice(min_rows=40, log=lambda m: None)
    finally:
        config.RUNS = old
    assert [s["calls"] for s in sites.values()] == [20] and not spawn.spawned()


def switch_on(hive, monkeypatch, probs):
    runs = write_calls(hive, "r1", judge_rows(60))
    sites = spawn.notice(min_rows=40, dirs=[runs], log=lambda m: None)
    name = next(iter(sites.values()))["name"]
    spawn.set_status(name, "on", on_since=0)
    use.WINS.write_text(json.dumps({name: {"use": True, "thresholds": {"PASS": 0.9, "FAIL": 0.95}}}))
    monkeypatch.setattr(runtime, "available", lambda s: True)
    monkeypatch.setattr(runtime, "label_probs", lambda s, x: probs(x))
    asked = []
    monkeypatch.setattr(llm, "_chat_member", lambda spec, msgs, *a: asked.append(msgs[1]["content"]) or '{"verdict":"FAIL","reason":"member"}')
    return name, asked


def msgs(user, system=JUDGE):
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def test_a_working_cell_answers_only_when_sure_and_the_member_answers_the_rest(hive, monkeypatch):
    name, asked = switch_on(hive, monkeypatch, lambda x: {"PASS": 0.97, "FAIL": 0.03} if "easy" in x else {"PASS": 0.6, "FAIL": 0.4})
    seen = []
    llm.set_recorder(lambda spec, m, out, **info: seen.append((spec, info.get("by_cell"))))
    try:
        data, _ = llm.chat_json("juror", msgs("CHECK: easy one"))
        assert data["verdict"] == "PASS" and asked == [] and seen == [(f"cell:{name}", True)]
        data, _ = llm.chat_json("juror", msgs("CHECK: hard one"))
        assert data["reason"] == "member" and asked == ["CHECK: hard one"]
        llm.chat_json("writer", msgs("CHECK: easy one", system="another instruction"))  # another site: not its job
        assert len(asked) == 2
        monkeypatch.setenv("AGENT_TEAM_SPAWN", "0")
        llm.chat_json("juror", msgs("CHECK: easy one"))
        assert len(asked) == 3
    finally:
        llm.set_recorder(None)


def test_a_cell_s_own_answers_are_never_training_rows(hive):
    d = hive / "runs" / "r9"
    d.mkdir(parents=True)
    line = {"specialist": "cell:x", "by_cell": True, "output": '{"verdict":"PASS"}',
            "messages": msgs("CHECK: z")}
    (d / "calls.jsonl").write_text(json.dumps(line) + "\n")
    assert spawn.sites(dirs=[hive / "runs"]) == {}


def test_live_audits_retire_a_cell_that_stops_agreeing(hive, monkeypatch):
    name, asked = switch_on(hive, monkeypatch, lambda x: {"PASS": 0.99, "FAIL": 0.01})
    monkeypatch.setattr(spawn, "AUDIT_RATE", 1.0)  # every sure call also goes to the member, who says FAIL
    for i in range(spawn.AUDIT_MIN):
        data, _ = llm.chat_json("juror", msgs(f"CHECK: {i}"))
        assert data["reason"] == "member"  # an audited call is answered by the member
    assert spawn.live(name) == {"answered": 0, "audits": spawn.AUDIT_MIN, "agreement": 0.0}
    out = spawn.review(log=lambda m: None)
    assert out[name]["retired"] and spawn.spawned()[name]["status"] == "retired"
    assert not use.wins()[name]["use"]
    asked.clear()
    monkeypatch.setattr(spawn, "AUDIT_RATE", 0.0)
    llm.chat_json("juror", msgs("CHECK: after"))
    assert asked == ["CHECK: after"]  # the job is back with the member


def test_the_gate_needs_agreement_coverage_and_enough_calls():
    from training import cells_spawn as cs
    dev = [("PASS", 0.99, "PASS")] * 8 + [("PASS", 0.7, "FAIL")] * 4 + [("FAIL", 0.99, "PASS")] * 6
    thr = cs.thresholds(dev, ["PASS", "FAIL"])
    assert thr == {"PASS": 0.8, "FAIL": 1.01}  # FAIL is never right on dev: the cell may never answer it
    test = [("PASS", 0.99, "PASS")] * 12 + [("PASS", 0.6, "PASS")] * 10 + [("FAIL", 0.99, "FAIL")] * 8
    assert cs.verified(test, thr) == thr
    j = cs.judged(test, thr)
    assert j["answered"] == 12 and j["covers"] == 0.4 and cs.passes(j)
    assert not cs.passes(cs.judged([("PASS", 0.99, "FAIL")] * 2 + test, thr))  # 12 of 14 agree: under the bar
    assert not cs.passes(cs.judged(test[:5], thr))  # too few answered calls to trust


def test_a_cell_that_learned_nothing_cannot_pass_on_a_site_that_mostly_says_yes():
    from training import cells_spawn as cs
    thr = {"PASS": 0.5}
    # the member said PASS 38 times in 40 and the cell says PASS every time: 95% agreement, nothing learned
    blind = [("PASS", 0.99, "PASS")] * 38 + [("PASS", 0.99, "FAIL")] * 2
    assert cs.verified(blind, thr) == {"PASS": 1.01}  # only 2 decisions could have shown a mistake
    blind = [("PASS", 0.99, "PASS")] * 36 + [("PASS", 0.99, "FAIL")] * 4
    assert cs.verified(blind, thr) == {"PASS": 1.01}  # as many mistakes as answering blindly
    learned = [("PASS", 0.99, "PASS")] * 36 + [("FAIL", 0.9, "FAIL")] * 4
    assert cs.verified(learned, thr) == thr and cs.passes(cs.judged(learned, cs.verified(learned, thr)))


def test_practice_recombines_only_the_older_real_inputs_and_the_member_decides(hive):
    import random
    a, b = "CLAIM: Kalo has 12 pools.\nQUOTE: Kalo: 12 pools", "CLAIM: Miro opened in 1999.\nQUOTE: Miro, opened 1999"
    made = {spawn.recombine(a, b, random.Random(i)) for i in range(40)}
    assert None not in made and a not in made
    assert any("Miro" in m and "Kalo" in m for m in made)        # a mismatch: one part from the other input
    assert any("Miro" not in m and "12 pools.\n" not in m for m in made)  # a near miss: one number changed
    assert spawn.recombine("no labelled parts here", b, random.Random(0)) is None
    rows = [("verifier", JUDGE, f"CLAIM: Town {i} has {i} pools.\nQUOTE: Town {i}: {i} pools",
             json.dumps({"verdict": "PASS" if i % 4 else "FAIL", "reason": "r"})) for i in range(40)]
    runs = write_calls(hive, "r1", rows)
    import team.config as config
    old, config.RUNS = config.RUNS, runs
    try:
        sites = spawn.notice(min_rows=30, log=lambda m: None)
        name = next(iter(sites.values()))["name"]
        asked = []
        n = spawn.rehearse(name, 20, log=lambda m: None,
                           ask=lambda x: asked.append(x) or '{"verdict": "FAIL", "reason": "does not match"}')
    finally:
        config.RUNS = old
    assert n == 20 and len(asked) == 20
    newest = [f"Town {i} " for i in range(28, 40)]  # the newest 30% are what the cell is judged on
    assert not any(t in x for x in asked for t in newest)
    tr, dv, te = learn.split(name)
    assert len(tr) == 28 + 20 and len(dv) + len(te) == 12 and all("Town" in x for x, _ in dv + te)
    assert all(y == "FAIL" for x, y in tr[28:])


def test_a_turn_of_life_trains_what_is_due_and_writes_the_report(hive, monkeypatch):
    runs = write_calls(hive, "r1", judge_rows(60))
    out = life.turn(min_rows=40, dirs=[runs], train=False, log=lambda m: None)
    assert out["sites"] == 1 and out["decision_sites"] == 1 and out["trained"] == {}
    name = next(iter(spawn.spawned()))
    assert life.due(name, spawn.spawned()[name]) == "new job"
    spawn.set_status(name, "failed", rows_at_fail=60)
    assert life.due(name, spawn.spawned()[name]) is None  # nothing new to learn from
    sp = spawn.spawned()[name]
    assert "grew" in life.due(name, {**sp, "rows": 90})
    text = life.REPORT.read_text()
    assert name in text and "| juror | 60 |" in text


def test_the_org_chart_lists_every_cell_once():
    from team import org
    text = org.chart()
    assert "UNPLACED" not in text
    for k in runtime.registry():
        assert text.count(f"cell  {k} ") + text.count(f"cell  {k:<22} ") >= 1
