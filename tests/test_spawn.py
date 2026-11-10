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
    ts = [dict(t, births=0, kept=0) for t in B.TRAINERS]
    ts[0].update(births=12, kept=0)
    ts[1].update(births=12, kept=12)
    picks = [B.pick_trainer(ts[:2], random.Random(i))["id"] for i in range(200)]
    assert picks.count("t2") > 190
    ts = [dict(t, births=1, kept=1) for t in B.TRAINERS]                                # four births in all: time to breed
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
