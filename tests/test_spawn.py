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


def test_the_hive_picks_the_specialist_that_failed_most_to_work_on_next(tmp_path, monkeypatch):
    import sqlite3
    from team import config, dream
    from team.board import Board
    monkeypatch.setattr(config, "RUNS", tmp_path)
    for n, (agent, verdict) in enumerate([("coder", "FAIL")] * 4 + [("researcher", "FAIL")] * 2 + [("coder", "PASS")] * 5):
        b = Board(tmp_path / f"r{n:02d}", echo=False)
        b.add_step({"id": "s1", "agent": agent, "task": "t"})
        b.update_step("s1", verdict=verdict)
    assert dream.worst_role() == "coder"
    assert dream.worst_role(least=5) is None  # too few failures to act on


def test_school_specialists_answer_together():
    from team import school
    # what most decide; on a tie the one that did best in its exam (first in the order)
    assert school.majority({"a": ["coder"], "b": ["writer"], "c": ["writer"]}, ["a", "b", "c"]) == ["writer"]
    assert school.majority({"a": ["coder"], "b": ["writer"]}, ["a", "b"]) == ["coder"]
    assert school.majority({"a": None, "b": ["writer"]}, ["a", "b"]) == ["writer"]
    assert school.majority({"a": None}, ["a"]) is None
    rows = [{"exam": False}, {"exam": True}, {"exam": False}]
    assert [len(p) for p in school.split(rows)] == [2, 1]


def test_a_task_goes_to_the_specialist_whose_lesson_it_is_most_like():
    from team import school
    terr = {"right": ["What is 17% of 250?", "Translate into French: good morning"],
            "planner2": ["Scrape the ten newest posts on news.example.com and save them to posts.csv"]}
    assert school.route("coordinator", "Scrape the five newest posts on blog.example.org and save them to blog.csv", terr) == "planner2"
    assert school.route("coordinator", "What is 12% of 990?", terr) is None
    assert school.route("coordinator", "anything", {}) is None


def test_a_taught_specialist_ahead_of_the_untouched_student_holds_the_job_only_in_the_small_hive(monkeypatch):
    from team import config, school
    ahead = {"graduated": False, "ahead": True}
    monkeypatch.setattr(config, "SMALL", False)
    assert not school.holds(ahead) and school.holds({"graduated": True})
    monkeypatch.setattr(config, "SMALL", True)
    assert school.holds(ahead) and not school.holds({"graduated": False})
    monkeypatch.setenv("AGENT_TEAM_SCHOOL", "0")
    assert not school.holds(ahead)


def test_a_school_program_is_judged_by_what_it_prints_when_run():
    from team import school
    assert school._program_key("```python\nprint(2 + 3)\nprint('Done')\n```", "t") == "5 done"
    assert school._program_key("```python\nprint(1/0)\n```", "t") is None            # it does not run
    assert school._program_key("```python\nx = 1\n```", "t") is None                   # it prints nothing
    assert school._program_key("```python\nimport os\nprint(os.getcwd())\n```", "t") is None  # not a school program


def test_every_school_role_says_how_it_is_taught_and_the_next_one_is_the_one_longest_away(monkeypatch):
    from team import school
    for r in school.ROLES.values():
        assert {"teacher", "student", "messages", "key", "tokens", "chat", "what"} <= set(r)
        assert r.get("of") in school.ROLES or {"known", "write", "topics", "example"} <= set(r)
    monkeypatch.setattr(school, "_has_work", lambda r: not school.ROLES[r].get("of"))
    monkeypatch.setattr(school, "record", lambda: {"coordinator": {"taught_agrees": 0.5, "when": "2026-11-10 09:27"}})
    assert school.next_role() == "coder"                                               # never taught goes first
    monkeypatch.setattr(school, "record", lambda: {"coordinator": {"taught_agrees": 0.5, "when": "2026-11-10 09:27"},
                                                   "coder": {"taught_agrees": 0.2, "when": "2026-11-10 12:00"}})
    assert school.next_role() == "coordinator"


def test_program_key_floats_that_differ_in_the_last_digit_are_the_same():
    from team import school
    assert school._same_floats("166.3256237947956") == school._same_floats("166.32562379479558")
    assert school._same_floats("7.701635339554948") != school._same_floats("8.043231726932046")
    assert school._same_floats("version 3.14 of [2, 4, 6] 0.5") == "version 3.14 of [2, 4, 6] 0.5"


def test_a_second_job_goes_to_school_only_while_its_first_job_has_unused_lessons(monkeypatch, tmp_path):
    from team import school
    monkeypatch.setattr(school, "DATA", tmp_path)
    monkeypatch.setattr(school, "lessons", lambda role: [{"task": "a"}, {"task": "b"}] if role == "coder" else [])
    assert school._has_work("coder") and school._has_work("coder_fix")
    (tmp_path / "coder_fix_seen.json").write_text('["a", "b"]')
    assert not school._has_work("coder_fix")


def test_plain_feedback_is_what_the_run_loop_says(monkeypatch):
    from team.specialists import coder
    assert coder.plain_feedback("t", "x", {"returncode": 0, "stdout": "", "stderr": ""}) == coder.SILENT
    died = coder.plain_feedback("t", "x", {"returncode": 1, "stdout": "", "stderr": "KeyError: 'a'"})
    assert died.startswith("KeyError: 'a'") and "Hint (data)" in died
    monkeypatch.setattr(coder, "review", lambda task, code, out: ["It counts y as a vowel."])
    monkeypatch.setattr(coder, "order_problem", lambda task, code: None)
    said = coder.plain_feedback("Count the vowels", "print(5)", {"returncode": 0, "stdout": "5\n", "stderr": ""})
    assert said.startswith(coder.WRONG + "It counts y as a vowel.") and said.endswith("Output was:\n5\n")
    monkeypatch.setattr(coder, "review", lambda task, code, out: [])
    assert coder.plain_feedback("Count the vowels", "print(3)", {"returncode": 0, "stdout": "3\n", "stderr": ""}) is None


def _candidate(**over):
    c = {"id": "bartowski/Yi-Coder-1.5B-Chat-GGUF", "author": "bartowski", "gated": False, "license": "apache-2.0",
         "params": 1.5e9, "template": True, "base": "01-ai/Yi-Coder-1.5B-Chat", "base_gated": False,
         "base_license": "apache-2.0", "file": "x-Q8_0.gguf", "size": 1.6e9}
    return {**c, **over}


def test_the_hive_recruits_only_small_open_ungated_chat_models_from_known_hands():
    from team import recruit
    assert recruit.suitable(_candidate()) == (True, "")
    for over, word in [({"gated": True}, "login"), ({"base_gated": True}, "login"), ({"license": "other"}, "licence"),
                       ({"base_license": None}, "licence"), ({"params": 2.5e9}, "parameters"), ({"params": None}, "parameters"),
                       ({"author": "someone"}, "neither its maker"), ({"file": None}, "no model file"),
                       ({"template": False}, "not a chat model"), ({"id": "x/Qwen3-VL-2B-GGUF"}, "not a chat model"),
                       ({"id": "x/Yi-Coder-abliterated-GGUF"}, "safety"), ({"base": None}, "no base model")]:
        ok, why = recruit.suitable(_candidate(**over))
        assert not ok and word in why, (over, why)
    assert recruit.suitable(_candidate(author="01-ai")) == (True, "")                  # converted by its own makers


def test_the_recruit_file_is_the_most_exact_one_that_fits():
    from team import recruit
    files = [("m-Q4_K_M.gguf", 1.0e9), ("m-Q6_K.gguf", 2.0e9), ("m-Q8_0.gguf", 3.0e9), ("m-f16.gguf", 5e9)]
    assert recruit.pick_file(files) == ("m-Q6_K.gguf", 2.0e9)
    assert recruit.pick_file([("m-f16.gguf", 5e9)]) is None


def test_a_voice_of_a_role_can_be_another_model_or_an_edit_of_one(monkeypatch):
    from team import config, school
    monkeypatch.setitem(config.GGUF_MODELS, "yicoder15bchat", ("r", "f", "t"))
    assert school._spec("coder", "untouched") == ("coder15", False)
    assert school._spec("coder", "coder_school") == ("coder15+coder_school", True)
    assert school._spec("coder", "yicoder15bchat") == ("yicoder15bchat", False)
    assert school._spec("coder", "yicoder15bchat+coder_school_yicoder15bchat") == ("yicoder15bchat+coder_school_yicoder15bchat", True)


def test_an_import_a_program_never_uses_does_not_keep_it_out_of_school():
    from team import school
    code = "import requests\nfrom bs4 import BeautifulSoup\nimport pandas as pd\nimport math\n\nprint(math.sqrt(16))\n"
    out = school._without_idle_imports(code)
    assert "requests" not in out and "bs4" not in out and "pandas" not in out and "import math" in out
    assert school._program_key(f"```python\n{code}```", "t") == "4.0"
    used = "import requests\nprint(requests.get('https://example.com').status_code)\n"
    assert school._without_idle_imports(used) == used and school._program_key(f"```python\n{used}```", "t") is None
    assert school._program_key("```python\nimport os\nprint(os.getcwd())\n```", "t") is None


def test_harvest_keeps_a_line_once_and_only_lines_that_are_text(tmp_path, monkeypatch):
    from team import harvest
    monkeypatch.setattr(harvest, "HOME", tmp_path)
    shelf = harvest._Shelf("t")
    shelf.add("A real sentence about the price of books in a shop.\n{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}\nshort\n"
              "A real sentence about the price of books in a shop.")
    shelf.f.flush()
    assert shelf.path.read_text().splitlines() == ["A real sentence about the price of books in a shop."]
    again = harvest._Shelf("t")
    again.add("A real sentence about the price of books in a shop.")
    assert again.added == 0


def test_a_cell_from_scratch_reads_left_to_right_so_padding_changes_nothing():
    import torch
    from training import scratch
    torch.manual_seed(0)
    m = scratch.Tiny(labels=3).eval()
    ids = torch.tensor([[1, 5, 9, 7]])
    padded = torch.tensor([[1, 5, 9, 7, 0, 0, 0]])
    with torch.no_grad():
        assert torch.allclose(m.label(ids, torch.tensor([3])), m.label(padded, torch.tensor([3])), atol=1e-5)
    assert sum(p.numel() for p in scratch.Tiny().parameters()) < 3_000_000


def test_one_brain_holds_every_job_and_a_consulting_head_sees_the_others():
    import torch
    from training import scratch
    torch.manual_seed(0)
    jobs = {"a": 2, "b": 3}
    ids, last = torch.tensor([[1, 5, 9, 7]]), torch.tensor([3])
    plain = scratch.Brain(jobs).eval()
    final, own = plain("a", ids, last)
    assert final.shape == (1, 2) and torch.equal(final, own)
    talk = scratch.Brain(jobs, talk=True).eval()
    final, own = talk("b", ids, last)
    assert final.shape == (1, 3) and talk.second["b"].in_features == scratch.DIM + 5


def test_the_from_scratch_trainer_knows_its_commands():
    from training import scratch
    for word in ("tokenizer", "pretrain", "pairs", "fit", "together", "all"):
        assert f"scratch.py {word}" in scratch.__doc__
    assert callable(scratch.pairs) and callable(scratch.together)


def test_the_body_keeps_a_new_cell_only_if_it_gains_and_no_territory_it_knew_gets_worse():
    import torch
    from training import body as B
    where = torch.tensor([0] * 6 + [1] * 6)
    before = torch.full((12,), 2.50)
    better = before - 0.05
    assert B.judge(before, better, where, [0, 1])[0]
    assert not B.judge(before, before - 0.0005, where, [0, 1])[0]                       # too small a gain
    lopsided = before.clone()
    lopsided[:6] -= 0.20                                                                # territory 0 gains a lot
    lopsided[6:] += 0.05                                                                # territory 1 forgets
    kept, why = B.judge(before, lopsided, where, [0, 1])
    assert not kept and "territory 1 got worse" in why


def test_the_immune_check_retires_the_cell_the_body_does_not_need(tmp_path, monkeypatch):
    import torch
    from training import body as B
    monkeypatch.setattr(B, "HOME", tmp_path)
    torch.save({"centre": torch.zeros(3, 4), "owns": {0: [1], 1: [2], 2: [3]}}, tmp_path / "territories.pt")
    for k in range(3):
        (tmp_path / f"cell_{k:02d}.pt").write_bytes(b"x")
    pieces = B.W // 2
    # cell 0 fits and predicts the first four passages, cell 1 the other four; cell 2 never fits what it reads
    first = torch.tensor([[1.0, 9.0, 9.0]] * 4 + [[9.0, 1.0, 9.0]] * 4)
    good, bad = torch.full((4, pieces), -1.0), torch.full((4, pieces), -6.0)
    second = torch.stack([torch.cat([good, bad]), torch.cat([bad, good]), torch.full((8, pieces), -6.0)], 1)
    out = B.immune(first, second, ["cell_00", "cell_01", "cell_02"], log=lambda *a, **k: None)
    assert out["cell"] == 2 and not (tmp_path / "cell_02.pt").exists() and (tmp_path / "cell_00.pt").exists()
    t = torch.load(tmp_path / "territories.pt")
    assert t["centre"].shape[0] == 3 and t["retired"] == [2] and 2 not in t["owns"]     # its place in the map stays
    assert B.immune(first[:, :2], second[:, :2], ["cell_00", "cell_01"], log=lambda *a, **k: None) is None  # never the last two


def test_trainers_with_kept_cells_are_chosen_more_and_bred():
    import random
    from training import body as B
    ts = [dict(t, births=0, kept=0) for t in B.TRAINERS[:4]]
    ts[0].update(births=12, kept=0)
    ts[1].update(births=12, kept=12)
    picks = [B.pick_trainer(ts[:2], random.Random(i))["id"] for i in range(200)]
    assert picks.count("t2") > 190
    ts = [dict(t, births=1, kept=1) for t in B.TRAINERS[:4]]                                # four births in all: time to breed
    ts[3].update(births=3, kept=0)
    ts[0].update(births=0, kept=0)
    ts[1].update(births=1, kept=1)
    ts[2].update(births=0, kept=0)
    grown = B.breed(ts, random.Random(0))
    assert "t4" not in [t["id"] for t in grown] and grown[-1]["id"] == "t5" and grown[-1]["births"] == 0
    assert sum(grown[-1][k] != next(t for t in grown if t["id"] == grown[-1]["parent"])[k] for k in ("start", "lr", "span", "on")) == 1


def test_the_org_chart_shows_the_body_from_its_own_record(tmp_path, monkeypatch):
    import json
    from team import config, org
    monkeypatch.setattr(config, "ROOT", tmp_path)
    assert org.body_lines() == []
    (tmp_path / "training" / "reports").mkdir(parents=True)
    (tmp_path / "cells" / "scratch" / "body").mkdir(parents=True)
    (tmp_path / "cells" / "scratch" / "body" / "cell_00.pt").write_bytes(b"x")
    (tmp_path / "training" / "reports" / "body.json").write_text(json.dumps({
        "births": [{"cell": 6, "when": "2026-11-10 20:00", "trainer": "t1", "on": "worst", "kept": True, "why": "the body gained +0.0100"}],
        "retired": [], "trainers": [{"id": "t1", "start": "stem", "on": "worst", "lr": 5e-4, "span": 1.0, "births": 1, "kept": 1}],
        "measured": [{"when": "2026-11-10 20:01", "passages": 300, "loss": {"stem cell alone": 2.7, "body, by fit: x": 2.6}}]}))
    text = "\n".join(org.body_lines())
    assert "1 cells alive" in text and "1 kept" in text and "the body at its best 2.6" in text and "trainer t1" in text


def test_the_brain_from_nothing_takes_a_job_only_where_it_measured_at_least_as_well():
    from team.cells import tiny
    wins = {"a": {"use": True, "cell": 0.90, "incumbent": 0.80}, "b": {"use": True, "cell": 0.95, "incumbent": 0.5},
            "c": {"use": False, "cell": 0.40, "incumbent": 0.70}, "d": {}}
    held = tiny.decide_holds({"a": 0.92, "b": 0.90, "c": 0.75, "d": 0.99}, wins)
    assert set(held) == {"a", "c"} and held["a"]["from"] == "today's cell" and held["c"]["from"] == "the member or rule"


def test_the_brain_answers_a_job_it_holds_and_can_be_switched_off(tmp_path, monkeypatch):
    import json
    import torch
    from team.cells import tiny, use
    from training import scratch as T
    if not (T.HOME / "tokenizer.json").exists():
        return  # no vocabulary on this checkout yet: the hive makes it on its first turns
    monkeypatch.setattr(tiny, "HOME", tmp_path)
    monkeypatch.setattr(tiny, "_state", {})
    torch.manual_seed(0)
    torch.save(T.Brain({"licence_open": 2}).state_dict(), tmp_path / "brain.pt")
    (tmp_path / "brain.json").write_text(json.dumps({"jobs": {"licence_open": ["yes", "no"]}, "talk": False}))
    (tmp_path / "holds.json").write_text(json.dumps({"licence_open": {"test": 0.99, "was": 0.9}}))
    assert use.on("licence_open") and use.ask("licence_open", "org/model | apache-2.0") in ("yes", "no")
    assert use.ask_all("licence_open", ["a | mit", "b | cc-by-nc-4.0"])[0] in ("yes", "no")
    monkeypatch.setenv("AGENT_TEAM_TINY", "0")
    assert tiny.holds() == {}


def test_a_scout_lets_in_only_text_that_reads_like_text():
    from team import harvest
    from team import config
    good = (config.ROOT / "README.md").read_text().splitlines()                          # real, varied prose
    assert harvest.readable(good) == (True, "")
    assert not harvest.readable(["x"] * 300)[0]                                          # not running text
    assert "alphabet" in harvest.readable([f"Река возле города {i} длинная, и весной она заливает все поля вокруг." for i in range(120)])[1]
    assert "repeats" in harvest.readable(["The same sentence is written here again and again, every time."] * 200)[1]
    assert harvest.pick_file([("a.parquet", 5e6), ("data/train-0.parquet", 9e6), ("big.txt", 9e9), ("small.txt", 10)]) == "data/train-0.parquet"
    assert harvest.pick_file([("default/part-0.parquet", 5e6)]) == "default/part-0.parquet"
    assert harvest.pick_file([("corpus.txt", 4e6), ("data/train-0.parquet", 2e6)]) == "corpus.txt"
    assert harvest.pick_file([("model.bin", 5e6)]) is None


def test_the_corpus_only_grows_at_its_end_so_no_window_moves(tmp_path, monkeypatch):
    import numpy as np
    from team import harvest
    from training import scratch as T
    if not (T.HOME / "tokenizer.json").exists():
        return
    tk = T.tokenizer()
    shelf = tmp_path / "harvest"
    shelf.mkdir()
    monkeypatch.setattr(harvest, "HOME", shelf)
    monkeypatch.setattr(T, "HOME", tmp_path)
    monkeypatch.setattr(T, "SHARED", tmp_path)                                          # never the hive's real text
    (shelf / "b.txt").write_text("The first shelf has one line about a river.\n")
    first = np.array(T.corpus(tk)).copy()
    (shelf / "b.txt").write_text("The first shelf has one line about a river.\nAnd now a second line about a bridge.\n")
    (shelf / "a.txt").write_text("A new shelf whose name sorts first.\n")
    grown = np.array(T.corpus(tk))
    assert len(grown) > len(first) and (grown[:len(first)] == first).all()
    assert len(np.array(T.corpus(tk))) == len(grown)                                     # nothing new: nothing added


def test_a_bitnet_layer_works_in_three_values_and_learns_on_ordinary_weights():
    import torch
    from training import scratch as T
    torch.manual_seed(0)
    layer = T.BitLinear(8, 4)
    x = torch.randn(3, 8)
    scale = layer.weight.abs().mean()
    three = (layer.weight / scale).round().clamp(-1, 1) * scale
    top = x.abs().amax(-1, keepdim=True)
    x8 = (x * 127 / top).round().clamp(-128, 127) * top / 127
    assert torch.allclose(layer(x), torch.nn.functional.linear(x8, three, layer.bias), atol=1e-6)
    layer(x).sum().backward()
    assert layer.weight.grad is not None and layer.weight.grad.abs().sum() > 0          # the ordinary weights learn


def test_a_packed_bitnet_cell_answers_exactly_as_before_and_is_small(tmp_path, monkeypatch):
    import torch
    from training import scratch as T
    monkeypatch.setattr(T, "HOME", tmp_path)
    torch.manual_seed(0)
    stem = T.Tiny(bit=True)
    torch.save(stem.state_dict(), tmp_path / "base.pt")
    cell = T.Tiny(bit=True)
    cell.load_state_dict(stem.state_dict())
    with torch.no_grad():
        for p in cell.blocks.parameters():
            p.add_(torch.randn_like(p) * 0.01)                                          # it has grown away from the stem cell
    T.save_cell(cell, tmp_path / "cell_00.pt")
    back = T.load_cell(tmp_path / "cell_00.pt")
    ids = torch.randint(2, T.VOCAB, (2, 40))
    with torch.no_grad():
        assert torch.allclose(cell.eval().next_piece(ids), back.eval().next_piece(ids), atol=2e-2)
    assert (tmp_path / "cell_00.pt").stat().st_size < 700_000 and back.bit
    full = T.Tiny(bit=False)
    T.save_cell(full, tmp_path / "cell_01.pt")
    assert not T.load_cell(tmp_path / "cell_01.pt").bit and (tmp_path / "cell_01.pt").stat().st_size > 5_000_000


def test_a_bitnet_cell_can_be_grown_by_moving_its_three_values_directly(tmp_path, monkeypatch):
    import numpy as np
    import torch
    from training import body as B
    from training import scratch as T
    torch.manual_seed(0)
    torch.set_num_threads(2)
    monkeypatch.setattr(T, "CTX", 32)
    monkeypatch.setattr(B, "W", 32)
    rng = np.random.default_rng(0)
    data = np.tile(rng.integers(2, 60, size=33 * 8), 40).astype(np.uint16)              # text with a pattern to learn
    cell = T.Tiny(bit=True)
    before = {n: p.clone() for n, p in cell.state_dict().items()}
    rounds, best, start = B._flip_read(cell, data, list(range(200)), minutes=0.25, seed=0, batch=8, share=0.01)
    assert rounds >= 1 and best <= start
    for m in cell.modules():
        if isinstance(m, T.BitLinear):                                                  # every layer is still three values times a number
            scale = m.weight.abs().mean()
            assert set((m.weight / scale).round().clamp(-1, 1).unique().tolist()) <= {-1.0, 0.0, 1.0}
    assert all(torch.equal(before[n], p) for n, p in cell.state_dict().items() if n.startswith(("tok.", "pos.", "norm.")))


def test_the_direct_way_trains_a_bitnet_without_ordinary_weights_underneath(monkeypatch):
    import numpy as np
    import torch
    import torch.nn.functional as F
    from training import scratch as T
    torch.manual_seed(0)
    torch.set_num_threads(2)
    monkeypatch.setattr(T, "CTX", 32)
    rng = np.random.default_rng(0)
    data = torch.from_numpy(np.tile(rng.integers(2, 60, size=33 * 4), 30).astype("int64"))   # text with a pattern to learn
    model = T.Tiny(bit=True)
    trainer = T.Direct(model, seed=0)
    losses = []
    for step in range(120):
        at = torch.randint(0, len(data) - 33, (16,))
        x = torch.stack([data[i:i + 33] for i in at.tolist()])
        loss = F.cross_entropy(model.next_piece(x[:, :-1]).reshape(-1, T.VOCAB), x[:, 1:].reshape(-1))
        losses.append(loss.item())
        trainer.step(loss, 0.01)
    assert sum(losses[-10:]) / 10 < sum(losses[:10]) / 10 - 1.0                          # it learns
    for m, t in zip(trainer.layers, trainer.t):                                         # and every weight is one of three values
        assert set(t.unique().tolist()) <= {-1.0, 0.0, 1.0}
        scale = m.weight.abs().mean()
        assert torch.equal((m.weight / scale).round().clamp(-1, 1), t)


def test_a_stem_cell_never_trains_on_the_held_windows():
    import random
    from training import scratch as T
    rnd = random.Random(0)
    at = T.offsets(rnd, T.CTX * 400, 2000)
    assert len(at) == 2000
    assert all((i // T.CTX) % T.HELD and ((i + T.CTX) // T.CTX) % T.HELD for i in at)     # no window it reads touches a held one


def test_a_new_stem_cell_eases_into_three_values_and_learns_from_a_teacher(tmp_path, monkeypatch):
    import json
    import numpy as np
    import torch
    from training import scratch as T
    torch.manual_seed(0)
    torch.set_num_threads(2)
    layer, x = T.BitLinear(8, 8), torch.randn(4, 8)
    try:
        T.EASE[0] = 0.0
        assert torch.allclose(layer(x), torch.nn.functional.linear(x, layer.weight, layer.bias))   # not eased in yet: an ordinary layer
    finally:
        T.EASE[0] = 1.0
    assert not torch.allclose(layer(x), torch.nn.functional.linear(x, layer.weight, layer.bias))   # as it works: three values

    monkeypatch.setattr(T, "CTX", 32)
    monkeypatch.setattr(T, "HOME", tmp_path / "new")
    rng = np.random.default_rng(0)
    text = np.tile(rng.integers(2, 60, size=33 * 4), 60).astype("uint16")
    monkeypatch.setattr(T, "tokenizer", lambda *a, **k: None)
    monkeypatch.setattr(T, "corpus", lambda tk: text)
    old = tmp_path / "old"                                                               # a teacher of another shape than the new body
    old.mkdir()
    (old / "stem.json").write_text(json.dumps({"bit": False, "dim": 64, "layers": 1, "heads": 2}))
    torch.save(T.Tiny(shape=T.kind(old)).state_dict(), old / "base.pt")
    (tmp_path / "new").mkdir()
    (tmp_path / "new" / "stem.json").write_text(json.dumps({"bit": True, "dim": 64, "layers": 2, "heads": 2}))
    seen = []
    step = T.BitLinear.forward
    monkeypatch.setattr(T.BitLinear, "forward", lambda self, x: (seen.append(T.EASE[0]), step(self, x))[1])
    out = T.pretrain_direct(0.03, usual=True, name="base", lr=3e-3, warm=5, ease=0.5, teacher=old, log=lambda *a, **k: None)
    assert out["steps"] > 3 and (tmp_path / "new" / "base.pt").exists()
    assert min(seen) < 0.2 and max(seen) == 1.0 and T.EASE[0] == 1.0                    # it began nearly ordinary and ended a BitNet
    assert T.Tiny().blocks[0].qkv.weight.shape == (3 * 64, 64)                          # and has its own body's shape


def test_dreams_are_written_on_what_the_body_reads_worst_and_get_harder(tmp_path, monkeypatch):
    import json
    from team import config, harvest, llm
    monkeypatch.setattr(harvest, "HOME", tmp_path / "harvest")
    monkeypatch.setattr(config, "ROOT", tmp_path)
    assert harvest.dream(log=lambda *a, **k: None) == 0                                  # no body yet: nothing to dream about
    (tmp_path / "training" / "reports").mkdir(parents=True)
    (tmp_path / "training" / "reports" / "body.json").write_text(json.dumps({"weakest": {"text": "The mill by the river grinds corn."}}))
    asked = []

    def chat(role, messages, **kw):
        asked.append(messages[1]["content"])
        return f"Dream number {len(asked)} tells how a mill turns grain into flour by the weight of falling water."
    monkeypatch.setattr(llm, "chat", chat)
    kept = harvest.dream(n=3, log=lambda *a, **k: None)
    assert kept > 0 and all("The mill by the river" in a and harvest.LEVELS[0] in a for a in asked)
    assert len((tmp_path / "harvest" / "dreams.txt").read_text().splitlines()) == 3
    harvest._record(dreams=harvest.PER_LEVEL)
    harvest.dream(n=1, log=lambda *a, **k: None)
    assert harvest.LEVELS[1] in asked[-1]                                                # the next forty are harder


def test_the_stem_cell_keeps_what_it_learned_only_if_the_body_is_better_for_it(tmp_path, monkeypatch):
    import torch
    from training import body as B
    from training import scratch as T
    monkeypatch.setattr(B, "HOME", tmp_path)
    monkeypatch.setattr(B, "REPORT", tmp_path / "body.json")
    monkeypatch.setattr(T, "HOME", tmp_path)
    torch.manual_seed(0)
    stem = T.Tiny(bit=True)
    torch.save(stem.state_dict(), tmp_path / "base.pt")
    monkeypatch.setattr(B, "_stem", lambda: T.Tiny(bit=True))
    monkeypatch.setattr(B, "_windows", lambda data: 400)
    froze = {}

    def read(model, data, windows, minutes, seed, lr=5e-4, share_table=True):
        froze["table"] = not model.tok.weight.requires_grad and not model.pos.weight.requires_grad
        return 10, 2.0, 2.1
    monkeypatch.setattr(B, "_read", read)
    pieces = B.W // 2
    first = torch.tensor([[1.0, 1.0]] * 6)
    second = torch.full((6, 2, pieces), -2.0)
    better = (torch.tensor([[1.0]] * 6), torch.full((6, 1, pieces), -1.0))
    monkeypatch.setattr(B, "_read_all", lambda cells, data, windows: better)
    out = B.stem_reads(None, list(range(6)), first, second, log=lambda *a, **k: None)
    assert out["kept"] and froze["table"] and out["gate_after"] < out["gate_before"]
    saved = (tmp_path / "base.pt").stat().st_mtime_ns
    worse = (torch.tensor([[1.0]] * 6), torch.full((6, 1, pieces), -3.0))
    monkeypatch.setattr(B, "_read_all", lambda cells, data, windows: worse)
    out = B.stem_reads(None, list(range(6)), first, second, log=lambda *a, **k: None)
    assert not out["kept"] and (tmp_path / "base.pt").stat().st_mtime_ns == saved      # it stays as it was


def test_a_newborn_is_judged_where_it_lives():
    import torch
    from training import body as B
    before, after = torch.full((60,), 2.50), torch.full((60,), 2.48)
    assert B.judge_local(before, after, 0.4)[0]
    assert not B.judge_local(before, before - 0.001, 0.4)[0]                             # too small a gain where it lives
    kept, why = B.judge_local(before, after, 0.0)
    assert not kept and "never be among the cells awake" in why


def test_the_immune_check_of_a_big_body_judges_a_cell_where_it_was_awake(tmp_path, monkeypatch):
    import torch
    from training import body as B
    monkeypatch.setattr(B, "HOME", tmp_path)
    torch.save({"centre": torch.zeros(4, 4), "owns": {1: [1], 2: [2], 3: [3]}}, tmp_path / "territories.pt")
    for k in (1, 2, 3):
        (tmp_path / f"cell_{k:02d}.pt").write_bytes(b"x")

    class Fake:
        alive = [1, 2, 3]
    pieces = B.W // 2
    who = torch.tensor([[1, 2]] * 6 + [[3, 2]] * 6)                                      # cells 1 and 3 each wake on six passages, 2 on all
    first = torch.full((12, 3), 1.0)
    second = torch.full((12, 3, pieces), -2.0)
    second[:6, 1] = -1.0                                                                 # cell 1 reads its passages well
    second[6:, 1] = -4.0                                                                 # cell 3 reads its passages badly: the body is better without it
    out = B.immune_near(Fake(), first, second, who, log=lambda *a, **k: None)
    assert out["cell"] == 3 and not (tmp_path / "cell_03.pt").exists() and (tmp_path / "cell_01.pt").exists()


def test_bodies_read_as_one_and_the_one_that_fits_has_the_say(tmp_path, monkeypatch):
    import torch
    from training import body as B
    monkeypatch.setattr(B.T, "SHARED", tmp_path)                                         # no rule learned yet, one body
    pieces = B.W // 2
    fits = (torch.tensor([1.0, 1.0]), torch.full((2, pieces), -1.0))                     # this body knows these passages
    lost = (torch.tensor([9.0, 9.0]), torch.full((2, pieces), -6.0))                     # this one does not
    assert torch.allclose(B.together([fits, lost]), torch.tensor([1.0, 1.0]), atol=1e-3)
    half = (torch.tensor([1.0, 9.0]), torch.stack([torch.full((pieces,), -1.0), torch.full((pieces,), -6.0)]))
    other = (torch.tensor([9.0, 1.0]), torch.stack([torch.full((pieces,), -6.0), torch.full((pieces,), -1.0)]))
    one = B.together([half, other])                                                     # each covers what the other misses
    assert torch.allclose(one, torch.tensor([1.0, 1.0]), atol=1e-3)
    assert -half[1].mean().item() > 3 and -other[1].mean().item() > 3 and one.mean().item() < 1.1
    assert B.bodies()[0] == ""


def test_the_body_regenerates_what_it_lost(tmp_path, monkeypatch):
    import torch
    from training import body as B
    from training import scratch as T
    home = tmp_path / "body"
    home.mkdir()
    monkeypatch.setattr(B, "HOME", home)
    monkeypatch.setattr(B, "REPORT", tmp_path / "body.json")
    monkeypatch.setattr(T, "HOME", tmp_path)
    monkeypatch.setattr(B, "_data", lambda: list(range(B.W * 50 + 1)))
    torch.manual_seed(0)
    stem = T.Tiny(bit=True)
    torch.save(stem.state_dict(), tmp_path / "base.pt")
    torch.save(stem.state_dict(), home / "placer.pt")
    B._save_map({"centre": torch.zeros(2, 4), "owns": {0: [1, 2, 3], 1: [4, 5, 999]}})
    T.save_cell(stem, home / "cell_00.pt")
    (home / "cell_01.pt").write_bytes(b"cut off in the middle")                          # a cell that was cut off
    (tmp_path / "base.pt").unlink()                                                      # the stem cell is lost
    (home / "territories.pt").write_bytes(b"torn")                                       # the map is torn
    did = " | ".join(B.heal(log=lambda *a, **k: None))
    assert "stem cell was lost and came back" in did and "map of territories was lost and came back" in did
    assert "cell_01 could not be read" in did and not (home / "cell_01.pt").exists() and (home / "cell_00.pt").exists()
    assert "no longer there" in did and torch.load(home / "territories.pt")["owns"][1] == [4, 5]
    assert torch.load(tmp_path / "base.pt").keys() == stem.state_dict().keys()
    assert B.heal(log=lambda *a, **k: None) == [] or "missing" in " ".join(B.heal(log=lambda *a, **k: None))


def test_a_lost_text_stream_is_made_again_with_every_window_where_it_was(tmp_path, monkeypatch):
    import numpy as np
    from team import harvest
    from training import scratch as T
    if not (T.SHARED / "tokenizer.json").exists():
        return
    tk = T.tokenizer()
    shelf = tmp_path / "harvest"
    shelf.mkdir()
    monkeypatch.setattr(harvest, "HOME", shelf)
    monkeypatch.setattr(T, "HOME", tmp_path)
    monkeypatch.setattr(T, "SHARED", tmp_path)
    (shelf / "b.txt").write_text("The first shelf has one line about a river.\n")
    T.corpus(tk)
    (shelf / "a.txt").write_text("A new shelf whose name sorts first.\n")
    with open(shelf / "b.txt", "a") as f:
        f.write("And now a second line about a bridge.\n")
    grown = np.array(T.corpus(tk)).copy()
    (tmp_path / "corpus.u16").unlink()                                                   # the stream is lost
    again = np.array(T.corpus(tk))
    assert len(again) == len(grown) and (again == grown).all()


def test_the_say_of_each_member_is_learned_and_beats_winner_takes_all(tmp_path, monkeypatch):
    import torch
    from training import body as B
    monkeypatch.setattr(B, "HOME", tmp_path)
    torch.manual_seed(0)
    pieces, n = B.W // 2, 80
    # two members that fit the first half about alike; each knows the pieces the other does not (which ones differs
    # by passage); a third member that predicts nothing well
    first = torch.cat([2.0 + 0.1 * torch.randn(n, 2), torch.full((n, 1), 2.2)], 1)
    knows = torch.rand(n, pieces) < 0.5
    second = torch.stack([torch.where(knows, -0.5, -5.0), torch.where(knows, -5.0, -0.5), torch.full((n, pieces), -6.0)], 1)
    old = B.fit_loss(first, second, rule={"h": float(pieces), "bias": []}).mean().item()
    msgs = []
    rule = B.learn_say(first[::2], second[::2], log=lambda *a, **k: msgs.append(a[0]))
    new = B.fit_loss(first[1::2], second[1::2]).mean().item()                            # passages the rule was not learned on
    assert new < old - 0.3 and rule["h"] < pieces / 4
    assert rule["bias"][2] < min(rule["bias"][:2]) - 1                                   # the member that knows nothing lost its standing
    assert B._rule() == rule and "learned again" in msgs[0]
    # a seat asleep (nobody fills it) still has no say under a soft rule
    asleep = first.clone()
    asleep[:, 2] = 50.0
    assert B._say(asleep, rule)[:, 2].exp().max().item() < 1e-6
    # every cell reading at once has more seats than the rule knows: its sharpness only
    wide = torch.cat([first, first], 1)
    assert torch.allclose(B._say(wide, rule), torch.log_softmax(-rule["h"] * wide, 1))


def test_the_say_of_each_body_is_learned_too(tmp_path, monkeypatch):
    import json
    import torch
    from training import body as B
    monkeypatch.setattr(B.T, "SHARED", tmp_path)
    torch.manual_seed(1)
    pieces, n = B.W // 2, 60
    knows = torch.rand(n, pieces) < 0.7                                                  # the big body knows most pieces, the small one the rest
    big = (torch.full((n,), 2.0), torch.where(knows, -0.5, -5.0))
    small = (torch.full((n,), 2.4), torch.where(knows, -5.0, -0.5))
    alone = -big[1].mean().item()
    sharp = B.together([big, small], rule={"h": float(pieces), "bias": []}).mean().item()
    assert abs(sharp - alone) < 0.01                                                     # the old rule: the weaker body is never heard
    rule = B.learn_rule(torch.stack([big[0], small[0]], 1), torch.stack([big[1], small[1]], 1))
    (tmp_path / B.HIVE_RULE).write_text(json.dumps(rule))
    assert B.together([big, small]).mean().item() < alone - 0.5                          # as one they are better than the best alone
    assert B.together([big, small, small]).shape == (n,)                                 # a body founded since: the rule's sharpness only


def test_a_cell_of_the_team_learns_what_the_body_misses(tmp_path, monkeypatch):
    import math
    import torch
    from training import body as B
    from training import scratch as T
    monkeypatch.setattr(T, "HOME", tmp_path)
    monkeypatch.setattr(T, "CTX", 16)
    torch.manual_seed(0)
    cell = T.Tiny(bit=True)
    x = torch.randint(2, T.VOCAB, (4, 17))
    own = -B._piece_lp(cell, x).mean().item()                                            # the cell alone: it knows nothing yet
    knows = torch.full((4, 16), -0.01)                                                   # the body knows every piece already
    lost = torch.full((4, 16), -20.0)                                                    # the body knows none
    assert B._team_loss(cell, x, knows, 0.25).item() < -math.log(0.75) + 0.02            # little is asked of the cell there
    assert abs(B._team_loss(cell, x, lost, 0.25).item() - (own - math.log(0.25))) < 0.05  # here everything hangs on it
    # the push on the cell comes from the pieces the body misses
    half = knows.clone()
    half[:, 8:] = -20.0
    cell.zero_grad()
    logits = cell.next_piece(x[:, :-1])
    logits.retain_grad()
    lp = torch.log_softmax(logits, -1).gather(-1, x[:, 1:, None])[..., 0]
    (-torch.logaddexp(lp + math.log(0.25), half + math.log(0.75)).mean()).backward()
    push = logits.grad.abs().sum(-1)
    assert push[:, 8:].mean().item() > 50 * push[:, :8].mean().item()


def test_a_new_kind_of_trainer_joins_once_and_the_worst_record_makes_room(tmp_path, monkeypatch):
    import json
    import random
    from training import body as B
    monkeypatch.setattr(B, "REPORT", tmp_path / "body.json")
    monkeypatch.setattr(B.T, "is_bit", lambda: False)
    ts = B.trainers()
    team = [t for t in ts if t.get("how") == "team"]
    assert len(team) == 2 and len({t["id"] for t in ts}) == len(ts) and not any(t.get("how") == "flips" for t in ts)
    (tmp_path / "body.json").write_text(json.dumps({"trainers": [t for t in ts if "how" not in t], "kinds_tried": ["team"]}))
    assert not any(t.get("how") == "team" for t in B.trainers())                        # it had its chance and left: it does not come back
    eight = [{"id": f"t{i}", "start": "stem", "lr": 5e-4, "span": 1.0, "on": "division", "births": 2, "kept": 2} for i in range(1, 9)]
    eight[0].update(births=2, kept=0)                                                    # the oldest, and the worst record
    eight[5].update(births=0, kept=0)                                                    # one that has not had its chance
    eight[7].update(births=4, kept=4)                                                    # sixteen births in all: time to breed
    out = B.breed(eight, random.Random(0))
    assert len(out) == 8 and "t1" not in {t["id"] for t in out} and {"t6", "t9"} <= {t["id"] for t in out}


def test_the_hive_moves_as_one_file_and_a_bigger_hive_is_not_overwritten(tmp_path, monkeypatch):
    import io
    import json
    import tarfile
    import pytest
    from training import hive_state as H

    def hive(root, cells):
        homes = {"scratch": root / "scratch", "harvest": root / "harvest", "reports": root / "reports"}
        for h in homes.values():
            h.mkdir(parents=True)
        (homes["scratch"] / "base.pt").write_bytes(b"stem")
        (homes["scratch"] / "corpus.u16").write_bytes(b"made again from the harvest")           # left out
        (homes["scratch"] / "body").mkdir()
        (homes["scratch"] / "bodies" / "b2" / "body").mkdir(parents=True)
        for k in range(cells):
            (homes["scratch"] / "body" / f"cell_{k:02d}.pt").write_bytes(b"cell %d" % k)
        (homes["scratch"] / "bodies" / "b2" / "body" / "cell_00.pt").write_bytes(b"another body's cell")
        (homes["scratch"] / "bodies" / "b2" / "base.pt.part").write_bytes(b"half written")       # left out
        (homes["harvest"] / "wikipedia.txt").write_text("text " * 100)
        (homes["reports"] / "hive_of_bodies.json").write_text(json.dumps([{"bodies": {"first": 2.5}, "as_one": 2.4, "when": "then"}]))
        (homes["reports"] / "bench.json").write_text("{}")                                       # not the hive's
        return homes

    there, here = hive(tmp_path / "there", 3), hive(tmp_path / "here", 1)
    monkeypatch.setattr(H, "_homes", lambda: there)
    m = H.pack(tmp_path / "state.tar.gz")
    assert (m["bodies"], m["cells"], m["as_one"]) == (2, 4, 2.4)
    names = tarfile.open(tmp_path / "state.tar.gz").getnames()
    assert "scratch/body/cell_02.pt" in names and "scratch/bodies/b2/body/cell_00.pt" in names
    assert not [n for n in names if n.endswith((".part", "corpus.u16", "bench.json"))]

    monkeypatch.setattr(H, "_homes", lambda: here)
    assert "is here: 2 bodies, 4 living cells" in H.pull(tmp_path / "state.tar.gz")             # the smaller hive takes the bigger one
    assert (here["scratch"] / "body" / "cell_02.pt").read_bytes() == b"cell 2"
    assert (here["scratch"] / "bodies" / "b2" / "body" / "cell_00.pt").exists()
    (here["scratch"] / "body" / "cell_09.pt").write_bytes(b"born here since")
    assert H.pull(tmp_path / "state.tar.gz").startswith("left as it is")                        # a hive that grew past it is not overwritten
    assert (here["scratch"] / "body" / "cell_09.pt").exists()

    bad = tmp_path / "bad.tar"                                                                  # a file that reaches outside the hive is refused
    with tarfile.open(bad, "w") as tar:
        for name, blob in (("manifest.json", json.dumps({"bodies": 9, "cells": 99, "harvest_mb": 0, "as_one": 1}).encode()), ("scratch/../../evil.py", b"x")):
            info = tarfile.TarInfo(name)
            info.size = len(blob)
            tar.addfile(info, io.BytesIO(blob))
    with pytest.raises(ValueError):
        H.pull(bad)
    assert not (tmp_path / "evil.py").exists() and not (tmp_path / "here" / "evil.py").exists()


def test_a_hive_turn_keeps_to_its_time_and_the_body_that_waited_longest_goes_first(tmp_path, monkeypatch):
    import json
    import subprocess
    from training import body as B
    monkeypatch.setattr(B.T, "SHARED", tmp_path)
    (tmp_path / "bodies.json").write_text(json.dumps(["", "b2", "b3"]))
    (tmp_path / B.TURNS).write_text(json.dumps({"": 300.0, "b2": 100.0}))                       # b3 never had a turn, b2 waited longer than the first
    went, clock = [], [1000.0]
    monkeypatch.setattr(B.time, "time", lambda: clock[0])

    sick = set()

    def run(cmd, cwd=None, env=None, **kw):
        went.append(env["HIVE_BODY"])
        clock[0] += 50 * 60                                                                     # a body's turn takes fifty minutes
        return subprocess.CompletedProcess(cmd, int(env["HIVE_BODY"] in sick))
    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(B, "_loads", lambda p: object())                                        # no body is lost
    monkeypatch.setattr(B, "hive_measure", lambda log=print: {"as_one": 2.4})
    monkeypatch.setattr(B, "found", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no body is due")))
    assert B.hive_turn(budget=90, log=lambda *a, **k: None) == {"as_one": 2.4}                  # the measurement is always made
    assert went == ["b3", "b2"]                                                                 # the first body waits for the next turn
    went.clear()
    B.hive_turn(budget=40, log=lambda *a, **k: None)
    assert went == [""]                                                                         # and then it is the one that waited longest
    went.clear()
    sick.add("b3")                                                                              # a body whose turn fails
    saved = []
    res = B.hive_turn(budget=0, log=lambda *a, **k: None, after=lambda: saved.append(went[-1]))
    assert res["failed_turns"] == ["b3"] and went == ["b3", "b2", ""]                           # it is said, and the others still take their turns
    assert saved == ["b2", ""]                                                                  # the hive is saved after the turns that worked


def test_the_yardstick_is_the_same_passages_however_much_the_text_grows():
    import numpy as np
    from training import body as B
    small, big = np.zeros(B.W * 4000 + 1, "uint16"), np.zeros(B.W * 9000 + 1, "uint16")
    assert B._held(small, "report", 20, upto=4000) == B._held(big, "report", 20, upto=4000)
    held = [i for i in range(4000) if i % B.HELD == 0][1::2]
    assert B._held(big, "report", 20, upto=4000) == held[::len(held) // 20][:20]         # chosen as they were on 2026-11-11
    assert B._held(big, "report", 20) != B._held(small, "report", 20)                    # spread over all the text, they move
    assert all(i % B.HELD == 0 for i in B._held(big, "report", 20))
    wide = B._held(big, "report", 20)
    assert wide[-1] >= 9000 - 2 * B.HELD and len(set(wide)) == 20                         # and they reach the end of the text


def test_the_hive_is_saved_under_a_new_name_and_never_smaller_than_it_came(tmp_path, monkeypatch):
    import io
    import json
    import subprocess
    import tarfile
    import urllib.error
    from training import hive_state as H
    homes = {"scratch": tmp_path / "scratch", "harvest": tmp_path / "harvest", "reports": tmp_path / "reports"}
    for h in homes.values():
        h.mkdir()
    (homes["scratch"] / "body").mkdir()
    for k in range(4):
        (homes["scratch"] / "body" / f"cell_{k:02d}.pt").write_bytes(b"cell")
    (homes["scratch"] / "base.pt").write_bytes(b"stem")
    monkeypatch.setattr(H, "_homes", lambda: homes)
    monkeypatch.setattr(H.shutil, "which", lambda name: "/usr/bin/gh")
    monkeypatch.setenv("GH_TOKEN", "t")
    calls, there = [], [("hive-state-300.tar.gz", "u3"), ("hive-state-200.tar.gz", "u2"), ("hive-state-100.tar.gz", "u1")]

    def run(cmd, **kw):
        calls.append(cmd[1:4] + [a for a in cmd[4:] if a.startswith("hive-state-")])
        return subprocess.CompletedProcess(cmd, 0, "", "")
    monkeypatch.setattr(H.subprocess, "run", run)
    monkeypatch.setattr(H, "_states", lambda: there)
    said = []
    H.save(log=lambda *a, **k: said.append(a[0]))                                        # it did not come from the release, and a hive is there
    assert not calls and "NOT saved" in said[-1]

    (homes["scratch"] / H.CAME).write_text(json.dumps({"bodies": 1, "cells": 4}))
    H.save(log=lambda *a, **k: said.append(a[0]))
    assert [c[:2] for c in calls] == [["release", "view"], ["release", "upload"], ["release", "edit"], ["release", "delete-asset"]]
    assert calls[-1][-1] == "hive-state-100.tar.gz"                                      # the two newest stay, the oldest goes
    assert "saved as hive-state-" in said[-1]

    calls.clear()
    (homes["scratch"] / H.CAME).write_text(json.dumps({"bodies": 3, "cells": 22}))       # a run whose fetch went wrong has less than it came from
    H.save(log=lambda *a, **k: said.append(a[0]))
    assert not calls and "NOT saved" in said[-1]

    (homes["scratch"] / H.CAME).unlink()                                                 # the very first hive: no release yet
    monkeypatch.setattr(H, "_states", lambda: (_ for _ in ()).throw(urllib.error.HTTPError("u", 404, "no release", None, None)))
    assert H._shrunk({"bodies": 1, "cells": 4}) is None
    monkeypatch.setattr(H, "_states", lambda: (_ for _ in ()).throw(OSError("the network is down")))
    assert H._shrunk({"bodies": 1, "cells": 4})                                          # it cannot be seen: not saved over it

    # fetching: the newest state that can be read; a broken newest falls back to the one before
    good = io.BytesIO()
    with tarfile.open(fileobj=good, mode="w:gz") as tar:
        blob = json.dumps({"bodies": 1, "cells": 4}).encode()
        info = tarfile.TarInfo("manifest.json")
        info.size = len(blob)
        tar.addfile(info, io.BytesIO(blob))
    monkeypatch.setattr(H, "_states", lambda: [("hive-state-300.tar.gz", "u3"), ("hive-state-200.tar.gz", "u2")])
    monkeypatch.setattr(H.urllib.request, "urlopen", lambda url, timeout=0: io.BytesIO(b"cut off" if url == "u3" else good.getvalue()))
    assert H.fetch(tmp_path / "got.tar.gz", log=lambda *a, **k: None) == "hive-state/hive-state-200.tar.gz"
    monkeypatch.setattr(H, "fetch", lambda to, log=print: None)                           # nothing can be fetched
    assert H.main(["pull", "--force"]) == 0 and H.main(["pull", "--force", "--must"]) == 1   # the run on GitHub stops there


def test_the_vocabulary_is_learned_once_and_a_wrong_text_stream_is_made_again(tmp_path, monkeypatch):
    import json
    import numpy as np
    from team import harvest
    from training import body as B
    from training import scratch as T
    if not (T.SHARED / "tokenizer.json").exists():
        return
    real = (T.SHARED / "tokenizer.json").read_text()
    tk = T.tokenizer()
    shelf = tmp_path / "harvest"
    shelf.mkdir()
    monkeypatch.setattr(harvest, "HOME", shelf)
    monkeypatch.setattr(T, "SHARED", tmp_path)
    monkeypatch.setattr(T, "HOME", tmp_path / "bodies" / "b2")                            # a body that is not the first
    (tmp_path / "bodies" / "b2").mkdir(parents=True)
    (tmp_path / "tokenizer.json").write_text(real)
    (tmp_path / "bodies" / "b2" / "base.pt").write_bytes(b"a stem cell made with this vocabulary")
    (shelf / "new.txt").write_text("Text harvested since, full of zebras and quartz.\n" * 50)
    T.tokenizer(train=True)                                                              # asked to learn it again: it is kept
    assert (tmp_path / "tokenizer.json").read_text() == real
    src = open(B.__file__).read()
    assert 'T.HOME / "tokenizer.json"' not in src                                        # a body looks for the vocabulary where it is: shared

    (shelf / "new.txt").write_text("One line about a harbour.\nAnother about a lighthouse.\n")
    right = np.array(T.corpus(tk)).copy()
    assert json.loads((tmp_path / "corpus.json").read_text())["pieces"] == len(right)
    with open(tmp_path / "corpus.u16", "ab") as f:                                       # an addition that was cut off, or a row from another hive
        np.asarray([7, 7, 7], dtype=np.uint16).tofile(f)
    again = np.array(T.corpus(tk))
    assert len(again) == len(right) and (again == right).all()


def test_bodies_are_founded_for_ever_and_each_a_little_later():
    from training import body as B
    assert not B.body_is_due(1, 7) and B.body_is_due(1, 8)                                 # the second body at eight cells
    assert not B.body_is_due(3, 35) and B.body_is_due(3, 36)                               # the fourth when three bodies average twelve
    due = [next(a for a in range(10 ** 6) if B.body_is_due(n, a)) for n in range(1, 30)]
    assert all(b > a for a, b in zip(due, due[1:]))                                        # there is always a next body
    assert due[9] / 10 > due[1] / 2                                                        # and bodies are deeper by then


def test_every_founding_is_an_experiment_on_the_recipe(tmp_path, monkeypatch):
    import json
    import random
    from training import body as B
    monkeypatch.setattr(B.T, "SHARED", tmp_path)
    full = lambda r: {**B.NEW_BODY, **r, "shape": {"dim": B.T.DIM, "layers": B.T.LAYERS, **(r.get("shape") or {})}}  # noqa: E731
    recipe, changed = B.next_recipe(random.Random(0))
    assert changed is None and recipe == full(B.NEW_BODY)                                   # nothing measured yet: the recipe as it stands
    (tmp_path / B.RECIPES).write_text(json.dumps([{"body": "b3", "recipe": recipe, "minutes": 40.0, "score": 3.10}]))
    seen = set()
    for seed in range(40):
        child, what = B.next_recipe(random.Random(seed))
        seen.add(what)
        differs = [k for k in ("lr", "ease", "warm", "batch") if child[k] != recipe[k]] + [k for k in ("dim", "layers") if child["shape"][k] != recipe["shape"][k]]
        assert differs == [what]                                                             # one thing changed, and only one
        assert child["shape"]["dim"] % 32 == 0 and 3 <= child["shape"]["layers"] <= 8
    assert seen == {"lr", "ease", "warm", "batch", "dim", "layers"}
    better = dict(recipe, lr=0.0048)
    (tmp_path / B.RECIPES).write_text(json.dumps([{"body": "b3", "recipe": recipe, "minutes": 40.0, "score": 3.10},
                                                   {"body": "b4", "recipe": better, "minutes": 40.0, "score": 3.02},
                                                   {"body": "b5", "recipe": dict(recipe, ease=0.0), "minutes": 40.0, "score": 3.20}]))
    kids = [B.next_recipe(random.Random(seed))[0] for seed in range(40)]
    assert all(k["lr"] in (0.0048, round(0.0048 * 0.6, 5), round(0.0048 * 1.6, 5)) for k in kids)   # the children are the best one's
    monkeypatch.setitem(B.NEW_BODY, "warm", 100)                                            # the recipe changed by hand is tried once as it stands
    assert B.next_recipe(random.Random(0)) == (full(B.NEW_BODY), None)


def test_the_workflow_that_grows_the_hive_is_a_valid_file():
    from pathlib import Path
    try:
        import yaml
    except ImportError:
        return
    flow = yaml.safe_load((Path(__file__).resolve().parent.parent / ".github" / "workflows" / "hive.yml").read_text())
    steps = flow["jobs"]["turn"]["steps"]
    runs = " ".join(s.get("run", "") for s in steps)
    assert "pull --force --must" in runs and "--save" in runs and "hive_state.py log" in runs
    fetched = next(i for i, s in enumerate(steps) if s.get("id") == "fetched")
    assert all("steps.fetched.outcome == 'success'" in s["if"] for s in steps[fetched + 1:] if "if" in s)   # nothing is saved over a hive that was not fetched
    assert flow["permissions"] == {"contents": "write"} and flow["concurrency"]["group"] == "hive"


def test_a_founding_asks_the_bodies_that_read_best(tmp_path, monkeypatch):
    import json
    from training import body as B
    monkeypatch.setattr(B.T, "SHARED", tmp_path)
    monkeypatch.setattr(B, "HIVE", tmp_path / "hive.json")
    names = ["", "b2", "b3", "b4", "b5", "b6"]
    (tmp_path / "bodies.json").write_text(json.dumps(names))
    for b in names[:-1]:                                                                 # b6 was founded and has no cells yet
        home = tmp_path / ("bodies/" + b if b else "") / "body"
        home.mkdir(parents=True)
        (home / "territories.pt").write_bytes(b"map")
    assert B._readers() == ["", "b2", "b3", "b4"]                                         # nothing measured yet: the first four with a map
    (tmp_path / "hive.json").write_text(json.dumps([{"bodies": {}, "yardstick": {"bodies": {"first": 2.4, "b2": 2.9, "b3": 2.7, "b4": 2.5, "b5": 2.6}}}]))
    assert B._readers() == ["", "b4", "b5", "b3"]                                         # the four that read the yardstick best


def test_the_exam_is_fresh_every_sitting_and_checked_in_code():
    from training import exam as E
    a, b = E.exam(400), E.exam(401)
    assert [t[3] for t in a] == [t[3] for t in E.exam(400)] and [t[3] for t in a] != [t[3] for t in b]   # the seed is the sitting
    assert all(len({t[3] for t in E.exam(s)}) == 16 for s in range(400, 430))               # no task twice in a sitting
    fields = {t[1] for s in range(400, 430) for t in E.exam(s)}
    assert {"maths", "dates", "code", "live facts", "websites", "instructions", "knowledge", "languages", "understanding"} <= fields
    ok = lambda check, body: check(None, body)[0]                                             # noqa: E731
    assert ok(E.says(851), "The new price is $851.00.") and ok(E.says(1150), "It costs 1,150 dollars.") and not ok(E.says(851), "About 850.")
    import random
    for seed in range(30):                                                                   # every maker: a right answer passes, a wrong one fails
        r = random.Random(seed)
        _, _, task, check = E.m_steps(r)
        nums = [int(x) for x in __import__("re").findall(r"multiply (\d+) by (\d+)", task)[0]]
        word = __import__("re").search(r"word '(\w+)'", task).group(1)
        country = task.rsplit("capital of ", 1)[1].rstrip(".")
        right = f"A: {nums[0] * nums[1]}\nB: {word[::-1]}\nC: {E.CAPITALS[country]}"
        assert ok(check, right) and not ok(check, right.replace(f"A: {nums[0] * nums[1]}", "A: 1")) and not ok(check, right.replace("C:", "D:"))
    _, _, task, check = E.m_follow(random.Random(3))
    assert not ok(check, "")                                                                 # an empty answer never passes
    _, _, task, check = E.m_percent(random.Random(5))
    assert not ok(check, "I could not work it out.")


def test_the_record_of_exams_takes_only_numbers_and_known_names(tmp_path, monkeypatch):
    import json
    from training import exam_record as R
    good = {"seed": 315, "when": "2026-11-12 09:43", "passed": 11, "tasks": 16, "by_field": {"maths": [1, 1], "code": [1, 2], "made up": [5, 5]},
            "minutes": 71, "code": "8be45ff", "memory": "none"}
    line = R.line(good)
    assert line["passed"] == 11 and line["by_field"] == {"maths": [1, 1], "code": [1, 2]}       # a field the exam does not have is dropped
    assert R.line(dict(good, passed=99)) is None and R.line(dict(good, seed="315; rm -rf")) is None and R.line("text") is None
    assert R.line(dict(good, code="$(curl evil)", when="<script>"))["code"] == "" and R.line(dict(good, when="<script>"))["when"] == ""
    monkeypatch.setattr(R, "RECORD", tmp_path / "exams.jsonl")
    (tmp_path / "sitting").mkdir()
    (tmp_path / "sitting" / "315.json").write_text(json.dumps({"summary": good, "tasks": [{"answer": "anything the hive wrote"}]}))
    (tmp_path / "sitting" / "bad.json").write_text("not json")
    assert R.main([str(tmp_path / "sitting")]) == 0 and R.main([str(tmp_path / "sitting")]) == 0   # a sitting is recorded once
    lines = [json.loads(ln) for ln in (tmp_path / "exams.jsonl").read_text().splitlines()]
    assert len(lines) == 1 and set(lines[0]) == {"seed", "when", "passed", "tasks", "by_field", "minutes", "code", "memory"}
