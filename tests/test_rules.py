"""Fast tests (no models): Arnav's rules, JSON parsing, quote checking, plan repair."""
import json

import pytest

from team import llm, memory
from team.guard import Blocked, Guard, check_task
from team.specialists import coordinator
from team.specialists.verifier import quote_in


class FakeBoard:
    def __init__(self):
        self.approvals = []

    def record_approval(self, *a):
        self.approvals.append(a)

    def log(self, *a):
        pass


@pytest.fixture(autouse=True)
def clean_policy(tmp_path, monkeypatch):
    monkeypatch.setattr(memory, "POLICY", tmp_path / "policy.json")


def test_family_only_when_ordered():
    assert check_task("Text my mom that I'm late", goal="Find the cheapest flight to Pune")
    assert check_task("Text my mom that I'm late", goal="Text my mom that I'm late") is None
    assert check_task("Benchmark list.sort on 1M ints", goal="Benchmark list.sort") is None


def test_orders_are_parsed_and_negations_are_not_orders():
    from team.guard import parse_orders
    assert parse_orders("Run a model locally: no paying and no accounts. Don't delete anything.") == {}
    o = parse_orders("Buy 'Soumission' on books.toscrape.com and email me the receipt.")
    assert "spend" in o and "send" in o and "delete" not in o


def test_unordered_risky_actions_wait_for_arnav():
    b = FakeBoard()
    g = Guard(b, "never", goal="Find the price of a book on books.toscrape.com")
    assert not g.check_browser("browser", {"action": "click", "id": 1}, {"text": "Add to basket", "tag": "button"})
    assert not g.check_browser("browser", {"action": "click", "id": 1}, {"text": "Delete repository", "tag": "button"})
    assert not g.check_browser("browser", {"action": "click", "id": 1}, {"text": "Send", "tag": "button"})
    assert len(g.pending) == 3
    with pytest.raises(Blocked):
        g.check_browser("browser", {"action": "click", "id": 1}, {"text": "Login", "href": "/login", "tag": "a"},
                        page_url="https://books.toscrape.com/")
    with pytest.raises(Blocked):
        g.check_browser("browser", {"action": "goto", "url": "https://huggingface.co/join"})
    # searching is not sending
    assert g.check_browser("browser", {"action": "press", "key": "Enter"}, {"text": "q", "tag": "input"},
                           typed_fields=[{"search": True}])


def test_ordered_actions_go_ahead_exactly_where_ordered():
    g = Guard(FakeBoard(), "never", goal="Buy 'Soumission' on books.toscrape.com. Log in to quotes.toscrape.com and list my quotes.")
    assert g.check_browser("browser", {"action": "click", "id": 1}, {"text": "Add to basket", "tag": "button"})
    assert g.check_browser("browser", {"action": "click", "id": 1}, {"text": "Login", "href": "/login", "tag": "a"},
                           page_url="https://quotes.toscrape.com/")
    with pytest.raises(Blocked):  # login was ordered for quotes.toscrape.com only
        g.check_browser("browser", {"action": "click", "id": 1}, {"text": "Login", "href": "/login", "tag": "a"},
                        page_url="https://huggingface.co/")
    with pytest.raises(Blocked):  # a sign-up was not ordered
        g.check_browser("browser", {"action": "click", "id": 1}, {"text": "Sign up", "href": "/signup", "tag": "a"},
                        page_url="https://quotes.toscrape.com/")
    with pytest.raises(Blocked):  # models never type passwords, even when login is ordered
        g.check_browser("browser", {"action": "type", "id": 2}, {"type": "password", "text": ""},
                        page_url="https://quotes.toscrape.com/login")
    assert not g.check_code("coder", "import os\nos.remove('x')")  # deleting was not ordered


def test_code_rules():
    g = Guard(FakeBoard(), "never", goal="Count primes below 10000")
    assert not g.check_code("coder", "import os\nos.remove('x')")
    assert not g.check_code("coder", "import smtplib")
    assert not g.check_code("coder", "requests.post('https://example.com/x', json={})")
    assert g.check_code("coder", "requests.post('https://api.osv.dev/v1/query', json={})")
    assert g.check_code("coder", "print(sum(range(10)))")


def test_standing_policy(tmp_path):
    memory.POLICY.write_text(json.dumps({"delete": "allow"}))
    g = Guard(FakeBoard(), "never", goal="Clean up old logs")
    assert g.check_code("coder", "import os\nos.remove('x')")
    assert not g.check_code("coder", "import smtplib")


def test_parse_json_forgiving():
    assert llm.parse_json('```json\n{"a": [1, 2,],}\n```') == {"a": [1, 2]}
    assert llm.parse_json('Sure! {"action": "click", "id": 3} done') == {"action": "click", "id": 3}
    assert llm.parse_json("no json here") is None


def test_quote_in():
    page = "A Light in the Attic\n£51.77\n In stock (22 available)"
    assert quote_in("£51.77 In stock (22 available)", page)
    assert not quote_in("£15.77", page)


def test_plan_normalize_repairs():
    plan = {"steps": [{"id": "s1", "agent": "researcher", "task": "find models", "needs": []},
                      {"id": "s2", "agent": "verifier", "task": "check"},
                      {"id": "s3", "agent": "browser", "task": "open page", "for_each": "s1"}]}
    steps, problems = coordinator.normalize(plan, "goal")
    assert [s["agent"] for s in steps] == ["researcher", "browser", "writer"]
    assert "{item}" in steps[1]["task"] and steps[1]["needs"] == ["s1"]
    assert any("verifier" in p for p in problems)


def test_json_stop_waits_for_outer_object():
    assert not llm._closes_from_start('{"steps": [{"id": "s1"}')
    assert llm._closes_from_start('{"steps": [{"id": "s1"}]}')
    assert not llm._closes_from_start('{"a": "}"')


def test_hard_item_checks():
    from team.specialists.verifier import hard_item_check
    task = "Find text-generation models under 2B parameters with permissive licenses that are not gated"
    assert hard_item_check(task, "mistralai/Mistral-7B | params 7.242B | license apache-2.0 | gated False")
    assert hard_item_check(task, "meta-llama/Llama-3.2-1B | params 1.236B | license llama3.2 | gated manual") == "gated"
    assert hard_item_check(task, "Qwen/Qwen2.5-1.5B-Instruct | params 1.544B | license apache-2.0 | gated False") is None


def test_kill_switch_kills_running_code_and_its_children(tmp_path, monkeypatch):
    import threading
    import time

    from team import stop
    from team.tools.sandbox import run_python
    monkeypatch.setattr(stop, "FLAG", tmp_path / "STOP")
    monkeypatch.setattr(stop, "INBOX_FLAG", tmp_path / "inbox_STOP")
    code = ("import subprocess, time\n"
            "subprocess.Popen(['sleep', '60'])\n"   # a child process must die too
            "time.sleep(60)\n")
    threading.Timer(1.0, lambda: stop.request("test")).start()
    t0 = time.time()
    with pytest.raises(stop.Stopped):
        run_python(code, tmp_path / "work", timeout=120)
    assert time.time() - t0 < 5


def test_kill_switch_stops_model_calls(tmp_path, monkeypatch):
    from team import llm, stop
    monkeypatch.setattr(stop, "FLAG", tmp_path / "STOP")
    stop.request("test")
    with pytest.raises(stop.Stopped):
        llm.chat("verifier", [{"role": "user", "content": "hi"}], max_new_tokens=5)


def test_quote_credited_to_the_source_that_contains_it(tmp_path):
    from team.board import Board
    from team.specialists import verifier
    b = Board(tmp_path, echo=False)
    step = {"id": "s1", "agent": "researcher", "task": "license of X", "done_when": "license quoted"}
    corpus = {"https://huggingface.co/X": "Model card text", "https://huggingface.co/api/models/X": "X | license apache-2.0"}
    verifier.check_fact = lambda c, q: (True, "ok")
    verifier.judge = lambda *a: ("PASS", "ok")
    res = {"summary": "apache-2.0", "items": [], "corpus": corpus,
           "facts": [{"claim": "X is apache-2.0", "quote": "license apache-2.0", "url": "https://huggingface.co/X"}]}
    assert verifier.verify(step, res, b, tmp_path)[0] == "PASS"
    f = b.facts("s1")[0]
    assert f["status"] == "supported" and f["url"].endswith("/api/models/X")


def test_writer_strikes_unverified_numbers():
    from team.specialists.writer import ground_numbers
    text = "- License: apache-2.0 [1]\n- Load time: 0.00 seconds\n- Correct: 10/10\n- Size: 988.10 MB [2]"
    out, struck = ground_numbers(text, "weights total 988.10 MB, license apache-2.0")
    assert "988.10 MB" in out and "apache-2.0" in out
    assert len(struck) == 2 and "0.00" not in out and "10/10" not in out


def _writer_with_fakes(tmp_path, monkeypatch, replies, checklist=("Find the licence", "say who made it")):
    """A writer run with stand-in models. The writer gives `replies` in turn; the critic ticks "say who made it" only
    if the report says "made by", and "two-line" only if the report has two lines."""
    from team.board import Board
    from team.specialists import writer
    b = Board(tmp_path, echo=False)
    b.checklist = list(checklist)
    writes, critiques = [], []

    def chat(role, msgs, **kw):
        writes.append(msgs[-1]["content"])
        return replies[min(len(writes), len(replies)) - 1]

    def chat_json(role, msgs, **kw):
        report = msgs[-1]["content"].split("REPORT:\n", 1)[1]
        critiques.append(report)
        made = "made by" in report
        two = len([ln for ln in report.split("\n") if ln.strip()]) == 2
        ticks = {"Find the licence": (True, "quoted"), "say who made it": (made, "made by" if made else "no maker"),
                 "give me a two-line summary": (two, "two lines" if two else "not two lines")}
        return {"unsupported": [], "unordered": [], "checklist": [
            {"instruction": i, "done": ticks[i][0], "why": ticks[i][1]} for i in checklist]}, ""

    monkeypatch.setattr(writer.llm, "chat", chat)
    monkeypatch.setattr(writer.llm, "chat_json", chat_json)
    monkeypatch.setattr(writer.memory, "profile", lambda: "")
    return writer.run("goal", "write it", b, [])["summary"], writes, critiques


def test_writer_fixes_an_instruction_the_critic_finds_missing(tmp_path, monkeypatch):
    out, writes, critiques = _writer_with_fakes(tmp_path, monkeypatch, ["License: apache-2.0.",
                                                                        "License: apache-2.0. It is made by HF."])
    assert len(writes) == 2 and "- say who made it\n" in writes[1] and "no maker" not in writes[1]
    assert len(critiques) == 2  # the ticks are about the fixed report
    assert "✅ say who made it" in out and "❌" not in out


def test_writer_reports_a_miss_it_could_not_fix(tmp_path, monkeypatch):
    out, writes, critiques = _writer_with_fakes(tmp_path, monkeypatch, ["License: apache-2.0."])
    assert len(writes) == 3 and len(critiques) == 3  # writer, its fix, then the bigger editor once
    assert "❌ say who made it - no maker" in out


def test_writer_is_told_the_layout_arnav_ordered_and_it_is_checked(tmp_path, monkeypatch):
    table = "License: apache-2.0.\n\n| License |\n|---|\n| apache-2.0 |\n\nNot confirmed."
    out, writes, critiques = _writer_with_fakes(
        tmp_path, monkeypatch, [table, "License: apache-2.0.\nParameters: 0.135B."],
        checklist=("Find the licence", "give me a two-line summary"))
    assert "FORMAT Arnav ordered: exactly 2 lines of plain text" in writes[0]
    assert len(writes) == 2 and "exactly 2 lines" in writes[1]  # 7 lines came back: asked once more, in code
    assert len(critiques) == 1 and "✅ give me a two-line summary" in out


def test_ordered_layout_is_read_only_from_the_deliverable():
    from team.specialists.writer import ordered_format
    assert ordered_format(["give me a two-line summary"]) == (
        "exactly 2 lines of plain text, no table, no headings, no other sections", 2)
    assert ordered_format(["Summarise it in 3 sentences"])[0].startswith("exactly 3 sentences")
    assert ordered_format(["no table, in under 50 words"])[0] == "at most 50 words; no table"
    for not_a_layout in (["fix the two lines of code in main.py"], ["print the first 3 lines of the file"],
                         ["Find the licence", "Do not log in or pay"]):
        assert ordered_format(not_a_layout) == ("", None)


def test_an_empty_not_confirmed_heading_is_dropped():
    from team.specialists.writer import drop_empty_sections
    assert drop_empty_sections("Answer.\n\nNot confirmed.") == "Answer."
    assert drop_empty_sections("A.\n**Not confirmed:**\n## Sources\n[1] x") == "A.\n## Sources\n[1] x"
    kept = "A.\n\n## Not confirmed\n- the size"
    assert drop_empty_sections(kept) == kept


def test_a_bare_label_claim_takes_its_quote():
    from team.specialists.researcher import with_value
    assert with_value({"claim": "parameter count", "quote": "params 0.135B"})["claim"] == "parameter count: params 0.135B"
    full = {"claim": "SmolLM2-135M has 0.135B parameters", "quote": "params 0.135B"}
    assert with_value(dict(full)) == full


def test_a_failed_steps_evidence_is_nobodys_source(tmp_path):
    from team.board import Board
    from team.hive import retract_failed
    b = Board(tmp_path, echo=False)
    b.add_fact("s2", "Hugging Face", "https://huggingface.co/models/x/y", "Hugging Face", "supported", "evidence seen on page")
    b.add_fact("s1", "license apache-2.0", "https://huggingface.co/api/models/x/y", "license apache-2.0", "supported")
    retract_failed(b, {"id": "s2", "agent": "browser"}, "The page is not accessible.")
    retract_failed(b, {"id": "s1", "agent": "researcher"}, "jury 1/3")
    assert [f["step"] for f in b.facts(status="supported")] == ["s1"]


def test_the_browser_is_told_about_an_error_page():
    from types import SimpleNamespace
    from team.specialists.browser_agent import bad_page
    assert "HTTP 404" in bad_page(SimpleNamespace(http_status=404))
    assert bad_page(SimpleNamespace(http_status=200)) == "" and bad_page(SimpleNamespace(http_status=None)) == ""


def test_missing_cells_are_built_on_first_use(monkeypatch):
    from team.cells import runtime
    runs, left = [], [["route_step"]]
    monkeypatch.setattr(runtime, "missing", lambda: left[0])
    monkeypatch.setattr(runtime.subprocess, "run", lambda *a, **k: (runs.append(a), left.__setitem__(0, [])))
    monkeypatch.setenv("AGENT_TEAM_CELLS", "0")
    assert runtime.ensure_built(log=lambda m: None) == ["route_step"] and runs == []  # cells off: nothing built
    monkeypatch.setenv("AGENT_TEAM_CELLS", "1")
    assert runtime.ensure_built(log=lambda m: None) == [] and len(runs) == 1
    assert runtime.ensure_built(log=lambda m: None) == [] and len(runs) == 1  # built once


def test_saying_what_was_not_reached_is_never_flagged():
    from team.specialists.writer import HONEST
    assert HONEST.search("The model page is not accessible or the information is not available.")
    assert not HONEST.search("The license is MIT.")


def test_quantized_size_read_from_name():
    from team.specialists.verifier import hard_item_check
    task = "models under 2B parameters"
    assert hard_item_check(task, "line-corporation/japanese-large-lm-3.6b-instruction-sft-4bit | params 0.861B | gated False")
    assert hard_item_check(task, "Qwen/Qwen2.5-1.5B-Instruct | params 1.544B | gated False") is None


def test_an_ordered_file_always_gets_a_coder_step():
    from team.specialists.coordinator import ensure_file_step
    plan = [{"id": "s1", "agent": "researcher", "task": "find the books", "needs": [], "for_each": None, "done_when": ""},
            {"id": "s2", "agent": "writer", "task": "write", "needs": ["s1"], "for_each": None, "done_when": ""}]
    steps, added = ensure_file_step("Find the three cheapest books and save them to a CSV", plan)
    assert [s["agent"] for s in steps] == ["researcher", "coder", "writer"] and added
    assert steps[1]["needs"] == ["s1"] and steps[2]["needs"] == ["s1", steps[1]["id"]]
    assert ensure_file_step("Find the licence of X", plan) == (plan, [])


def test_a_question_is_not_an_order_unless_it_asks_the_team():
    from team.guard import parse_orders
    for q in ("Is it safe to buy from this shop?", "How much does it cost to book a room?",
              "Who can remove posts on that forum?", "Can I pay with PayPal on that site?", "What does the delete key do?"):
        assert not parse_orders(q), q
    assert set(parse_orders("Can you delete the old logs?")) == {"delete"}
    assert set(parse_orders("Could you pay the invoice for me?")) == {"spend"}
    assert set(parse_orders("Buy the book. Is it safe?")) == {"spend"}


def test_calculator_runs_only_arithmetic(tmp_path, monkeypatch):
    from team.board import Board
    from team.specialists import calculator, verifier
    b = Board(tmp_path, echo=False)
    monkeypatch.setattr(calculator.llm, "chat", lambda *a, **k: '```python\nprint("17.5% of 2340 =", f"{0.175 * 2340:.2f}")\n```')
    r = calculator.run("What is 17.5% of 2,340?", "", b, "s1", tmp_path)
    assert r["returncode"] == 0 and r["summary"] == "17.5% of 2340 = 409.50"
    monkeypatch.setattr(verifier, "_judge_one", lambda *a: ("PASS", "computes it"))
    assert verifier.verify({"id": "s1", "agent": "calculator", "task": "t", "done_when": "d"}, r, b, tmp_path)[0] == "PASS"
    monkeypatch.setattr(calculator.llm, "chat", lambda *a, **k: "import shutil\nshutil.rmtree('/tmp/x')")
    r = calculator.run("t", "", b, "s2", tmp_path)
    assert "failed" in r and not (tmp_path / "calc" / "s2.py").exists()


def test_a_short_report_is_not_a_failure_but_an_empty_one_is(tmp_path):
    from team.board import Board
    from team.specialists import verifier
    b = Board(tmp_path, echo=False)
    w = {"id": "s1", "agent": "writer", "task": "t", "done_when": "d"}
    assert verifier.verify(w, {"summary": "La réunion est déplacée à vendredi.\n\n## Sources"}, b, tmp_path)[0] == "PASS"
    assert verifier.verify(w, {"summary": "\n## Your instructions\n- ❌ x"}, b, tmp_path)[0] == "FAIL"


def test_a_writer_only_task_uses_arnavs_words_as_the_source(tmp_path, monkeypatch):
    from team.board import Board
    from team.specialists import writer
    b = Board(tmp_path, echo=False)
    seen = []
    monkeypatch.setattr(writer.llm, "chat", lambda role, msgs, **k: seen.append(msgs[-1]["content"]) or "La réunion est déplacée.")
    monkeypatch.setattr(writer.llm, "chat_json", lambda *a, **k: ({"unsupported": [], "unordered": [], "checklist": []}, ""))
    monkeypatch.setattr(writer.memory, "profile", lambda: "")
    writer.run("Translate into French: 'The meeting has been moved.'", "Translate it", b, [])
    assert "Arnav's own words are the source" in seen[0] and "The meeting has been moved." in seen[0]


def test_triage_takes_a_shortcut_only_when_the_cell_is_sure(tmp_path, monkeypatch):
    from team.board import Board
    from team.cells import runtime, use
    from team.specialists import coordinator
    b = Board(tmp_path, echo=False)
    monkeypatch.setattr(use, "on", lambda s: s == "task_kind")
    monkeypatch.setattr(runtime, "label_probs", lambda s, t: {"calc": 0.97, "plan": 0.03})
    steps = coordinator.triage("What is 17.5% of 2,340?", b)
    assert [s["agent"] for s in steps] == ["calculator", "writer"] and steps[1]["needs"] == ["s1"]
    monkeypatch.setattr(runtime, "label_probs", lambda s, t: {"write": 0.99})
    assert [s["agent"] for s in coordinator.triage("Translate: 'hi'", b)] == ["writer"]
    monkeypatch.setattr(runtime, "label_probs", lambda s, t: {"calc": 0.6, "plan": 0.4})
    assert coordinator.triage("Compare two models and chart them", b) is None  # unsure: the coordinator plans
    monkeypatch.setattr(runtime, "label_probs", lambda s, t: {"plan": 0.95})
    assert coordinator.triage("Compare two models and chart them", b) is None
    # a kind with its own threshold (chosen on dev): a 'write' shortcut skips research, so it must be surer
    monkeypatch.setattr(use, "wins", lambda: {"task_kind": {"use": True, "thresholds": {"write": 0.995}}})
    monkeypatch.setattr(runtime, "label_probs", lambda s, t: {"write": 0.99})
    assert coordinator.triage("If I pay 64.20 a month, how much is that in a year?", b) is None
    monkeypatch.setattr(runtime, "label_probs", lambda s, t: {"calc": 0.97, "plan": 0.03})
    assert [s["agent"] for s in coordinator.triage("What is 17.5% of 2,340?", b)] == ["calculator", "writer"]


def test_a_failed_steps_result_is_never_passed_on_as_verified(tmp_path):
    from team.board import Board
    b = Board(tmp_path, echo=False)
    for sid, verdict, summ in (("s1", "PASS", "Einstein: two ways to live"), ("s2", "FAIL", "made-up quotes")):
        b.add_step({"id": sid, "agent": "browser", "task": f"task {sid}", "needs": []})
        b.update_step(sid, verdict=verdict, feedback="evidence not on the page", result={"summary": summ, "url": "https://q/",
                                                                                         "page": "line A\nline B"})
    ctx = b.context_for(["s1", "s2"])
    assert "Einstein" in ctx and "line A" in ctx
    assert "made-up quotes" not in ctx and "Not confirmed: evidence not on the page" in ctx


def test_a_browser_step_starts_where_the_last_one_ended(tmp_path, monkeypatch):
    from team import hive
    from team.board import Board
    h = hive.Hive.__new__(hive.Hive)
    h.board = Board(tmp_path, echo=False)
    h.board.add_step({"id": "s1", "agent": "browser", "task": "open the tag page", "needs": []})
    h.board.update_step("s1", verdict="PASS", result={"summary": "ok", "url": "https://quotes.toscrape.com/tag/x/"})
    assert h._last_page({"id": "s2", "needs": ["s1"]}) == "https://quotes.toscrape.com/tag/x/"
    assert h._last_page({"id": "s2", "needs": []}) is None


def test_a_reroute_with_no_other_specialist_retries_the_step(tmp_path, monkeypatch):
    """A search returned the wrong papers; next_move said reroute, no other specialist fits: retry, never drop."""
    from team import hive, memory, smiths
    from team.board import Board
    from team.cells import use
    h = hive.Hive.__new__(hive.Hive)
    h.board, h.dir, h.work, h.goal = Board(tmp_path, echo=False), tmp_path, tmp_path, "List the newest papers"
    s = {"id": "s1", "agent": "researcher", "task": "find the newest papers", "needs": []}
    h.board.add_step(s)
    tasks = []
    monkeypatch.setattr(h, "_dispatch", lambda st, task, ctx: tasks.append(task) or {"summary": f"try {len(tasks)}"},
                        raising=False)
    monkeypatch.setattr(hive.verifier, "verify",
                        lambda st, r, b, w: ("PASS", "ok") if r["summary"] == "try 2" else ("FAIL", "not about the topic"))
    monkeypatch.setattr(use, "on", lambda k: k == "next_move")
    monkeypatch.setattr(use, "ask", lambda k, text, board=None: "reroute")
    monkeypatch.setattr(hive.coordinator, "reroute", lambda goal, st, fb: None)
    monkeypatch.setattr(memory, "lessons_for", lambda *a: [])
    monkeypatch.setattr(smiths, "route", lambda agent, task: agent)
    h._run_step(s)
    assert len(tasks) == 2 and "not about the topic" in tasks[1] and h.board.step("s1")["verdict"] == "PASS"


def test_when_nothing_was_verified_no_answer_is_made_up(tmp_path, monkeypatch):
    """Every look-up failed: no model writes (it listed the rejected papers with today's date); his instructions are
    marked not done, so an until-done round plans again."""
    from team import sdk
    from team.board import Board
    from team.specialists import writer
    b = Board(tmp_path, echo=False)
    b.checklist = ["List the three newest arXiv papers about mixture of experts", "with their titles and dates"]
    b.add_step({"id": "s1", "agent": "researcher", "task": "find the newest papers", "needs": []})
    b.update_step("s1", verdict="FAIL", feedback="no listed item meets the task", status="failed")
    monkeypatch.setattr(writer.llm, "chat", lambda *a, **k: pytest.fail("no model may write an unverified answer"))
    out = writer.run("List the three newest arXiv papers about mixture of experts, with their titles and dates.",
                     "Write the answer", b, ["s1"])["summary"]
    assert out.startswith(writer.NOTHING_VERIFIED) and "no listed item meets the task" in out
    assert len(sdk.unmet(out)) == 3  # two instructions and the failed step
    # text he handed over is still worked on: a failed look-up next to it does not stop the writer
    assert not writer.nothing_verified("Summarise this: The bridge opened in 1932. It took eight months to build.", b, [])


def test_a_bigger_editor_rewrites_only_when_the_writer_cannot_fix_it(tmp_path, monkeypatch):
    from team.board import Board
    from team.specialists import writer
    b = Board(tmp_path, echo=False)
    b.checklist = ["Translate into French: 'Friday'"]
    roles = []

    def chat(role, msgs, **kw):
        roles.append(role)
        return "vendredi" if role == "editor" else "mercredi"

    def chat_json(role, msgs, **kw):
        ok = "vendredi" in msgs[-1]["content"].split("REPORT:\n", 1)[1]
        return {"unsupported": [] if ok else ["mercredi"], "unordered": [],
                "checklist": [{"instruction": "Translate into French: 'Friday'", "done": ok, "why": "" if ok else "wrong day"}]}, ""
    monkeypatch.setattr(writer.llm, "chat", chat)
    monkeypatch.setattr(writer.llm, "chat_json", chat_json)
    monkeypatch.setattr(writer.memory, "profile", lambda: "")
    out = writer.run("Translate into French: 'Friday'", "Translate it", b, [])["summary"]
    assert roles == ["writer", "writer", "editor"] and out.startswith("vendredi") and "✅" in out
    roles.clear()
    monkeypatch.setattr(writer.llm, "chat", lambda role, msgs, **kw: roles.append(role) or "vendredi")
    writer.run("Translate into French: 'Friday'", "Translate it", b, [])
    assert roles == ["writer"]  # right first time: no fix round, no editor


def test_text_he_hands_over_is_material_not_orders(monkeypatch):
    from team.cells import use
    from team.guard import parse_orders, split_material
    from team.specialists import coordinator
    assert split_material("Translate into French: 'Send the report to Sam.'") == ("Translate into French",
                                                                                  "'Send the report to Sam.'")
    assert not parse_orders(split_material("Translate into French: 'Send the report to Sam.'")[0])
    assert split_material("Buy two tickets: one for me and one for Sam.")[1] == ""  # a colon alone is not material
    para = "Summarise this in one sentence: The bridge was built in 1932. It closed in March. Buses detour."
    monkeypatch.setattr(use, "on", lambda s: s == "split_orders")
    monkeypatch.setattr(use, "ask", lambda skill, text, board=None: text)  # the cell returns the order as one line
    assert coordinator.instructions(para) == [para]  # one instruction with its material, not one per sentence


def test_the_writer_step_is_checked_by_the_family_rule_only(monkeypatch):
    from team import guard
    monkeypatch.setattr(guard, "_family_cell", lambda text: "explanation" in (text or ""))  # a false "yes"
    step = "Write a three-sentence explanation of what a mixture-of-experts model is"
    assert guard.check_task(step, "Explain mixture-of-experts models")  # an acting step: the cell still blocks
    assert guard.check_task(step, "Explain mixture-of-experts models", cell=False) is None
    assert guard.check_task("Write a note to my wife", "Explain models", cell=False)  # the rule still blocks


def test_a_saved_chart_is_shown_to_the_jury_and_linked_in_the_report(tmp_path):
    """The jury rejected a saved chart ("the evidence shows the downloads, not the file"); the writer linked the
    chart to a Hugging Face API page; 3,905,849 was struck although the source said 3905849."""
    from PIL import Image, ImageDraw
    from team.specialists.verifier import describe_file
    from team.specialists.writer import fix_images, ground_numbers
    im = Image.new("RGB", (200, 100), "white")
    ImageDraw.Draw(im).rectangle([20, 20, 60, 90], fill="blue")
    im.save(tmp_path / "chart.png")
    Image.new("RGB", (200, 100), "white").save(tmp_path / "blank.png")
    assert "valid PNG image, 200x100" in describe_file(tmp_path / "chart.png")
    assert describe_file(tmp_path / "blank.png").startswith("BROKEN")
    (tmp_path / "empty.csv").write_text("")
    assert describe_file(tmp_path / "empty.csv").startswith("EMPTY")
    assert fix_images("![Bar](https://huggingface.co/api/models/x)", [tmp_path / "chart.png"]) == "![Bar](work/chart.png)"
    assert fix_images("![Bar](https://example.com/c.png)", []) == ""
    kept, struck = ground_numbers("It has 3,905,849 downloads.\nIt has 1,999 stars.", "downloads 3905849")
    assert kept == "It has 3,905,849 downloads." and struck == ["It has 1,999 stars."]


def test_a_reply_cut_off_at_the_token_limit_is_asked_again_with_room(monkeypatch):
    """The browser's answer with three quotes passed its token limit; asked again with the same limit, it was cut off
    every time until it ran out of actions."""
    from team import llm
    full = '{"action": "done", "answer": "“A.”\\n“B.”\\n“C.”", "evidence": "“A.”\\n“B.”\\n“C.”"}'
    seen = []

    def chat(specialist, messages, max_new_tokens=512, adapter=True, prefix="", stop=None, **kw):
        seen.append(max_new_tokens)
        return full if max_new_tokens >= 300 else full[:40].replace("“A.”", "“A")
    monkeypatch.setattr(llm, "chat", chat)
    monkeypatch.setattr(llm, "parse_json", lambda t: __import__("json").loads(t) if t.endswith("}") else None)
    data, _ = llm.chat_json("browser", [{"role": "user", "content": "x"}], max_new_tokens=160)
    assert data["action"] == "done" and seen == [160, 320]


def test_code_the_team_writes_never_sees_tokens_or_keys(tmp_path, monkeypatch):
    """Model-written code ran with the whole environment: GitHub tokens and cloud keys included."""
    from team.tools.sandbox import run_python
    monkeypatch.setenv("GH_TOKEN", "ghp_secret")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "aws-secret")
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.local:3128")
    r = run_python("import os\nprint(sorted(os.environ))", tmp_path)
    assert "GH_TOKEN" not in r["stdout"] and "OPENAI_API_KEY" not in r["stdout"] and "AWS_SECRET" not in r["stdout"]
    assert "HTTPS_PROXY" in r["stdout"] and "PATH" in r["stdout"]  # it can still reach the web and run


def test_the_coder_sees_a_site_named_without_a_scheme_and_the_links_its_task_names():
    """'on books.toscrape.com' gave no preview: the coder wrote http:// URLs and guessed where the Mystery books are."""
    from bs4 import BeautifulSoup
    from team.tools.preview import task_links
    from team.tools.web import urls_in
    assert urls_in("Find the cheapest Mystery books on books.toscrape.com and save them to a CSV.") == \
        ["https://books.toscrape.com/"]
    assert urls_in("Mail it to arnav@example.com") == []
    soup = BeautifulSoup('<a href="catalogue/category/books/mystery_3/index.html">Mystery</a>'
                         '<a href="catalogue/category/books/poetry_23/index.html">Poetry</a>', "html.parser")
    assert task_links(soup, "the three cheapest Mystery books", "https://books.toscrape.com/") == \
        ["Mystery -> https://books.toscrape.com/catalogue/category/books/mystery_3/index.html"]
