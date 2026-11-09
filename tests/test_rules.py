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
    monkeypatch.setattr(writer.llm, "chat", lambda role, msgs, **k: seen.append(msgs) or "La réunion est déplacée.")
    monkeypatch.setattr(writer.llm, "chat_json", lambda *a, **k: ({"unsupported": [], "unordered": [], "checklist": []}, ""))
    monkeypatch.setattr(writer.memory, "profile", lambda: "")
    writer.run("Translate into French: 'The meeting has been moved.'", "Translate it", b, [])
    # his text is the material, and the writer is told to change it (not to report it "from the verified results")
    assert seen[0][0]["content"] == writer.prompts.WRITER_TEXT and "The meeting has been moved." in seen[0][-1]["content"]


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
    from team import config
    monkeypatch.setattr(config, "TRANSLATE_ROLE", "writer")  # the escalation path itself (translations now go to the 4B)

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


def test_the_coder_stops_when_its_fix_changes_nothing(tmp_path, monkeypatch):
    """The same unreachable-host error 12 times cost 28 minutes of the 7B coder."""
    from team.board import Board
    from team.specialists import coder
    calls = []
    monkeypatch.setattr(coder, "preview", lambda task, wd: "")
    monkeypatch.setattr(coder.llm, "chat", lambda *a, **k: calls.append(1) or "```python\nimport requests\n```")
    monkeypatch.setattr(coder, "run_python", lambda code, wd, name: {
        "returncode": 1, "stdout": "", "stderr": "Traceback ...\nConnectionError: Max retries exceeded (host unreachable)",
        "seconds": 0.2, "path": str(wd / name)})

    class G:
        def check_code(self, who, code):
            return True
    out = coder.run("Scrape the site", "", Board(tmp_path, echo=False), "s1", G(), tmp_path / "work")
    assert len(calls) == 2 and out["returncode"] == 1 and "ConnectionError" in out["stderr"]


def test_the_report_keeps_his_instructions_and_the_calendar_s_weekdays():
    """The critic added an instruction he never gave and ticked it; the report called 15 January 2026 a Monday."""
    from team.specialists.writer import align_checklist, check_weekdays
    mine = ["How many days are there from 15 January 2026 to 1 March 2026?", "Give the answer in one sentence"]
    critic = [{"instruction": "How many days are there from 15 January 2026 to 1 March 2026", "done": True},
              {"instruction": "Provide a table with dates, days of the week, and notes", "done": True}]
    out, extra = align_checklist(critic, mine)
    assert [c["instruction"] for c in out] == mine and out[0]["done"] and out[1]["done"] is False
    assert extra == ["Provide a table with dates, days of the week, and notes"]
    text, wrong = check_weekdays("45 days.\n| Date | Day |\n|---|---|\n| 15 January 2026 | Monday |\n"
                                 "4 July 1976 was a Sunday. 2026-03-01 is a Sunday.")
    # the calendar is exact: the wrong day is corrected, not struck (striking left a held-out answer as the bare "6")
    assert wrong == ["| 15 January 2026 | Monday |"] and "| 15 January 2026 | Thursday |" in text
    assert "4 July 1976 was a Sunday" in text and "| Date | Day |" in text


def test_the_layout_comes_from_his_order_not_from_the_text_he_hands_over():
    """'the apples that was on the table' made the writer add a table; 'give me only the corrected sentence' was not
    read as a layout at all."""
    from team.specialists.writer import ordered_format
    fmt, lines = ordered_format(["Correct the grammar of this sentence: 'She don't like the apples that was on the table.'",
                                 "give me only the corrected sentence"])
    assert "table" not in fmt.replace("no table", "") and fmt.startswith("only the corrected sentence") and lines == 1
    assert ordered_format(["Compare the two models in a table"]) == ("include a table", None)
    assert ordered_format(["Summarise this: 'The table was moved. The chairs stayed.'"]) == ("", None)


def test_a_draft_is_only_the_draft_in_the_ordered_length():
    """'a two-sentence email' was not read as a layout; the writer added a Details list and a table repeating it."""
    from team.specialists.writer import ordered_format
    fmt, _ = ordered_format(["Write a two-sentence email to Priya declining Friday's 3pm meeting"])
    assert "exactly 2 sentences" in fmt and "only the email itself" in fmt
    assert ordered_format(["Fix the two lines of code"]) == ("", None)


def test_code_that_prints_nothing_is_sent_back_and_his_task_travels_with_the_step(tmp_path, monkeypatch):
    """The coder defined fib() and never called it; the calculator's step had lost 'fib(1) = 1' and counted from 0."""
    from team import hive
    from team.board import Board
    from team.specialists import coder
    outs = iter(["", "832040\n"])
    asked = []
    monkeypatch.setattr(coder, "preview", lambda task, wd: "")
    monkeypatch.setattr(coder, "review", lambda *a: [])
    monkeypatch.setattr(coder.llm, "chat", lambda role, msgs, **k: asked.append(msgs[-1]["content"]) or "```python\npass\n```")
    monkeypatch.setattr(coder, "run_python", lambda code, wd, name: {"returncode": 0, "stdout": next(outs), "stderr": "",
                                                                     "seconds": 0.1, "path": str(wd / name)})

    class G:
        def check_code(self, who, code):
            return True
    out = coder.run("Write fib and tell me fib(30)", "", Board(tmp_path, echo=False), "s1", G(), tmp_path / "w")
    assert out["summary"] == "832040" and "printed nothing" in asked[1]
    seen = {}
    h = hive.Hive.__new__(hive.Hive)
    h.board, h.work, h.goal = Board(tmp_path / "b", echo=False), tmp_path, "Write fib (fib(1) = 1, fib(2) = 1) and tell me fib(30)."
    monkeypatch.setattr(hive.calculator, "run", lambda task, ctx, *a: seen.update(ctx=ctx) or {"summary": "832040"})
    h._dispatch({"id": "s2", "agent": "calculator", "needs": []}, "Calculate the 30th Fibonacci number", "")
    assert "fib(1) = 1, fib(2) = 1" in seen["ctx"]


def test_the_jury_sees_the_program_beside_its_output(tmp_path, monkeypatch):
    """Shown only '30', the jury rejected a right fix of the loop as 'insufficient evidence'."""
    from team.board import Board
    from team.specialists import verifier
    (tmp_path / "s1.py").write_text("total = 0\nfor i in range(1, 11):\n    if i % 2 == 0:\n        total += i\nprint(total)\n")
    seen = {}
    monkeypatch.setattr(verifier, "judge", lambda check, work, ev: seen.update(work=work, ev=ev) or ("PASS", "ok"))
    step = {"id": "s1", "agent": "coder", "task": "Fix it and tell me the right answer", "done_when": "prints the right sum"}
    res = {"summary": "30", "returncode": 0, "stderr": "", "files": [], "code_path": str(tmp_path / "s1.py")}
    assert verifier.verify(step, res, Board(tmp_path, echo=False), tmp_path)[0] == "PASS"
    assert "range(1, 11)" in seen["ev"] and "OUTPUT:\n30" in seen["ev"] and "Files" not in seen["work"]


def test_data_he_hands_over_is_material_and_orders_after_it_still_count():
    """'Monthly sales: Jan 120, Feb 95, ...' became four 'instructions'; a risky order next to data is still read."""
    from team.guard import parse_orders, split_material
    order, data = split_material("Monthly sales: Jan 120, Feb 95, Mar 143, Apr 110. Which month had the highest sales?")
    assert order == "Which month had the highest sales?" and data.startswith("Jan 120")
    order, data = split_material("Bills: rent 500, gym 30 and phone 20. Pay the rent.")
    assert "spend" in parse_orders(order) and data == "rent 500, gym 30 and phone 20."
    assert "spend" in parse_orders(split_material("Pay: rent 500, gym 30, phone 20")[0])


def test_a_trailing_clause_of_his_order_stays_on_the_checklist(monkeypatch):
    """'..., with their titles and dates' was lost (the sentence was half covered); a cut-short line was listed twice."""
    from team.cells import use
    from team.specialists import coordinator
    monkeypatch.setattr(use, "ask", lambda s, t, b=None: "List the three newest arXiv papers about mixture of experts\n"
                                                         "List the three newes")
    assert coordinator._split("List the three newest arXiv papers about mixture of experts, with their titles and "
                              "dates.") == ["List the three newest arXiv papers about mixture of experts",
                                            "with their titles and dates"]


def test_the_research_hive_splits_filters_fills_gaps_and_cross_checks(tmp_path, monkeypatch):
    """A research question: sub-questions, a relevance cell per search result, a gap gets one more search, sources
    that disagree are listed. Members and the web are stand-ins."""
    from team.board import Board
    from team.cells import use
    from team.specialists import research_hive as R
    from team.tools import web
    b = Board(tmp_path, echo=False)
    plans, asked = [], []

    def chat_json(role, msgs, **kw):
        sys_, user = msgs[0]["content"], msgs[-1]["content"]
        if sys_ == R.DECOMPOSE:
            return {"questions": ["How do tidal turbines work?", "How much power does the Kalo array make?"]}, ""
        if sys_ == R.ANSWERS:  # the researcher's yes/no per fact (a fact about popularity answers nothing here)
            pairs = __import__("re").findall(r"QUESTION: (.*)\n\s+FACT: (.*)", user)
            return {"answers": ["no" if "popular" in f or ("power" in q and "MW" not in f) else "yes"
                                for q, f in pairs]}, ""
        if "Choose where to look" in sys_:
            plans.append(user)
            return {"searches": [{"source": "wikipedia", "q": user.split("Task: ")[1].split("\n")[0][:40]}]}, ""
        q = user.split("Task: ")[1].split("\n")[0] if "Task: " in user else ""
        if "power" in q and sum("power" in p for p in plans) < 2:
            return {"summary": "", "facts": [{"claim": "Tidal turbines are popular.", "quote": "popular", "url": "https://a"}]}, ""
        claim = "The Kalo array makes 320 MW." if "power" in q else "Tidal turbines turn with the tide."
        url = "https://b" if "power" in q else "https://a"
        facts = [{"claim": claim, "quote": "x", "url": url}]
        if "power" in q:
            facts.append({"claim": "The Kalo array makes 302 MW.", "quote": "y", "url": "https://c"})
        return {"summary": "", "facts": facts}, ""
    monkeypatch.setattr(R.llm, "chat_json", chat_json)
    monkeypatch.setattr(web, "search", lambda src, q, **kw: [{"title": "Tidal power", "url": "https://w/1", "snippet": "tides"},
                                                             {"title": "Tidal waves", "url": "https://w/2", "snippet": "waves"}])
    monkeypatch.setattr(web, "read_url", lambda u, max_chars=0: {"title": "t", "text": "short page"})
    on = {"result_relevant", "answers_q", "claims_agree"}
    monkeypatch.setattr(use, "on", lambda k: k in on)

    def ask(skill, text, board=None):
        asked.append(skill)
        if skill == "result_relevant":
            return "no" if "Tidal waves" in text else "yes"
        if skill == "answers_q":
            return "no" if "popular" in text or ("power" in text and "MW" not in text) else "yes"
        return "conflict" if "320" in text and "302" in text else "agree"
    monkeypatch.setattr(use, "ask", ask)
    monkeypatch.setattr(use, "ask_all", lambda skill, texts, board=None: [ask(skill, t) for t in texts])
    assert R.broad("Research how tidal turbines work and how much power the Kalo array makes")
    out = R.run("Research how tidal turbines work and how much power the Kalo array makes", "", b, "s1")
    assert out["sub_questions"] == ["How do tidal turbines work?", "How much power does the Kalo array make?"]
    assert sum("power" in p for p in plans) == 2 and "other sources or other words" in plans[-1]  # the gap's second search
    assert "Sources disagree" in out["summary"] and out["open_questions"] == []
    assert asked.count("result_relevant") >= 6 and "claims_agree" in asked
    ev = [__import__("json").loads(ln) for ln in (tmp_path / "events.jsonl").read_text().splitlines()]
    assert any("kept 1 of 2" in e["msg"] for e in ev if e["kind"] == "filter")


def test_the_coder_is_held_to_his_own_examples_and_told_the_kind_of_error(tmp_path, monkeypatch):
    """fib(30) came out as fib(29): his 'fib(1) = 1, fib(2) = 1' now runs against the program's fib()."""
    from team.board import Board
    from team.specialists import coder
    wrong = "def fib(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return b\nprint(fib(30))\n"
    right = "def fib(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\nprint(fib(30))\n"
    progs, asked = iter([wrong, right]), []
    monkeypatch.setattr(coder, "preview", lambda task, wd: "")
    monkeypatch.setattr(coder, "review", lambda *a: [])
    monkeypatch.setattr(coder.llm, "chat", lambda role, msgs, **k: asked.append(msgs[-1]["content"])
                        or f"```python\n{next(progs)}```")

    class G:
        def check_code(self, who, code):
            return True
    out = coder.run("Write fib (fib(1) = 1, fib(2) = 1) and tell me fib(30).", "", Board(tmp_path, echo=False), "s1", G(),
                    tmp_path / "w")
    assert out["summary"] == "832040" and "fib(1) returned 1" not in asked[1] and "but the task says fib(" in asked[1]
    assert coder.error_kind("requests.exceptions.ConnectionError: Max retries exceeded") == "network"
    assert coder.error_kind("NameError: name 'x' is not defined") is None


def test_a_listing_s_next_page_is_pointed_out_and_the_site_name_is_not_a_task_word():
    """Only page 1 of the Mystery listing was read (2 of the 3 cheapest); 'books' in books.toscrape.com picked the
    all-books link."""
    from bs4 import BeautifulSoup
    from team.tools.preview import next_page, task_links
    soup = BeautifulSoup('<a href="catalogue/category/books_1/index.html">Books</a>'
                         '<a href="catalogue/category/books/mystery_3/index.html">Mystery</a>'
                         '<li class="next"><a href="page-2.html">next</a></li>', "html.parser")
    assert task_links(soup, "the cheapest Mystery books", "https://books.toscrape.com/") == \
        ["Mystery -> https://books.toscrape.com/catalogue/category/books/mystery_3/index.html"]
    assert next_page(soup, "https://books.toscrape.com/catalogue/category/books/mystery_3/index.html") == \
        "https://books.toscrape.com/catalogue/category/books/mystery_3/page-2.html"


def test_research_can_run_experiments_and_do_math_not_only_read(tmp_path, monkeypatch):
    """A sub-question answered by an experiment: the coder's program runs it; each RESULT line is a claim whose
    evidence is the program's own output, which the verifier checks like a quote."""
    from team.board import Board
    from team.specialists import coder, research_hive as R, verifier
    b = Board(tmp_path, echo=False)
    monkeypatch.setattr(R.llm, "chat_json", lambda role, msgs, **k: ({"questions": [
        {"q": "Is insertion sort faster than merge sort on lists of 20 numbers?", "how": "experiment"}]}, ""))
    (tmp_path / "exp.py").write_text("import random\nrandom.seed(0)\n# times both sorts\n")

    def fake_coder(task, ctx, board, sid, guard, work):
        assert "RESULT: " in task and "fixed random seed" in task
        return {"summary": "METHOD: timed both sorts 1000 times on random lists of 20\n"
                           "RESULT: insertion sort mean time = 3.1 us\nRESULT: merge sort mean time = 7.9 us",
                "returncode": 0, "code_path": str(tmp_path / "exp.py"), "stderr": "", "files": []}
    monkeypatch.setattr(coder, "run", fake_coder)
    assert R.broad("Run an experiment: is insertion sort faster than merge sort on small lists?")
    out = R.run("Run an experiment: is insertion sort faster than merge sort on small lists?", "", b, "s1",
                guard=object(), work=tmp_path)
    assert [f["claim"] for f in out["facts"]] == ["insertion sort mean time = 3.1 us", "merge sort mean time = 7.9 us"]
    assert out["items"] == [] or "Method" in out["items"][0]
    src = out["facts"][0]["url"]
    assert src.startswith("experiment:") and "RESULT: insertion sort mean time = 3.1 us" in out["corpus"][src]
    assert verifier.quote_in(out["facts"][0]["quote"], out["corpus"][src])


def test_several_quoted_items_are_each_checked_on_the_page_and_a_failed_step_s_facts_verify_nothing(tmp_path):
    """The browser copied the right three quotes one per line; on the page their authors and tags sit between them,
    so the evidence was 'not on the page'. And a failed researcher step's checked facts had kept the writer writing
    a report of empty step headings."""
    from team.board import Board
    from team.specialists.verifier import quote_in
    from team.specialists import writer
    page = "“Quote one.” by A (about)\nTags: x y\n“Quote two.” by B (about)\nTags: z\n“Quote three.” by C"
    assert quote_in("“Quote one.”\n“Quote two.”\n“Quote three.”", page)
    assert not quote_in("“Quote one.”\n“Quote four.”", page)
    b = Board(tmp_path, echo=False)
    b.add_step({"id": "s1r", "agent": "researcher", "task": "find quotes", "needs": []})
    b.update_step("s1r", verdict="FAIL", status="failed", feedback="no listed item meets the task")
    b.add_fact("s1r", "Albert Einstein is quoted", "https://q", "Albert Einstein", "supported", "ok")
    assert writer.nothing_verified("List the first three quotes on the site.", b, b.facts(status="supported"))


def test_a_quote_is_credited_to_the_page_read_in_full_not_a_search_snippet(tmp_path, monkeypatch):
    from team.board import Board
    from team.specialists import verifier
    monkeypatch.setattr(verifier, "check_fact", lambda c, q: (True, "ok"))
    monkeypatch.setattr(verifier, "judge", lambda *a: ("PASS", "ok"))
    article = "Mixture of experts (MoE) is a machine learning technique where multiple expert networks divide a problem space. " * 20
    corpus = {"https://en.wikipedia.org/wiki/Mistral_AI": "Mistral AI | its models use a mixture of experts (MoE) is a machine "
                                                          "learning technique where multiple expert networks divide",
              "https://en.wikipedia.org/wiki/Mixture_of_experts": article, "search:wikipedia:moe": "listing"}
    b = Board(tmp_path, echo=False)
    b.add_step({"id": "s1", "agent": "researcher", "task": "explain MoE", "needs": []})
    res = {"summary": "MoE", "items": [], "corpus": corpus, "facts": [
        {"claim": "MoE uses multiple expert networks", "url": "search:wikipedia:moe",
         "quote": "a machine learning technique where multiple expert networks divide"}]}
    verifier.verify({"id": "s1", "agent": "researcher", "task": "explain MoE"}, res, b, tmp_path)
    assert b.facts("s1", "supported")[0]["url"] == "https://en.wikipedia.org/wiki/Mixture_of_experts"


def test_data_he_hands_over_is_computed_on_not_researched():
    from team.specialists.coordinator import ensure_data_steps
    goal = "Monthly sales: Jan 120, Feb 95, Mar 143, Apr 110. Which month had the highest sales, and what was the average?"
    plan = [{"id": "s1", "agent": "researcher", "task": "Find the month with the highest sales from the given data.",
             "needs": []},
            {"id": "s2", "agent": "writer", "task": "Write the answer", "needs": ["s1"]}]
    fixed, notes = ensure_data_steps(goal, plan)
    assert fixed[0]["agent"] == "calculator" and "Jan 120" in fixed[0]["task"] and notes
    assert ensure_data_steps("Find the licence of Qwen/Qwen3-1.7B.", plan)[0][0]["agent"] == "researcher"


def test_a_chart_drawn_with_show_is_sent_back_and_never_passes_unsaved(tmp_path, monkeypatch):
    """Held-out run: the coder drew the bar chart with plt.show(), which shows nothing here; no file was saved and the
    jury passed it because the program printed which model was higher."""
    from team.board import Board
    from team.specialists import coder, verifier
    from team.tools.sandbox import program_env
    assert program_env()["MPLBACKEND"] == "Agg"  # on his desktop, plt.show() would open a window and wait
    shown = ("import matplotlib.pyplot as plt\nplt.bar(['a', 'b'], [1, 2])\nplt.show()\nprint('b is higher')\n")
    saved = ("import matplotlib.pyplot as plt\nplt.bar(['a', 'b'], [1, 2])\nplt.savefig('chart.png')\n"
             "print('saved chart.png; b is higher')\n")
    progs, asked = iter([shown, saved]), []
    monkeypatch.setattr(coder, "preview", lambda task, wd: "")
    monkeypatch.setattr(coder, "review", lambda *a: [])
    monkeypatch.setattr(coder.llm, "chat", lambda role, msgs, **k: asked.append(msgs[-1]["content"])
                        or f"```python\n{next(progs)}```")

    class G:
        def check_code(self, who, code):
            return True
    task = "Plot the download counts of a and b as a bar chart"
    out = coder.run(task, "", Board(tmp_path, echo=False), "s1", G(), tmp_path / "w")
    assert out["files"] == ["chart.png"] and "plt.savefig" in asked[1] and "saved no image" in asked[1]
    # and the verifier fails a drawn chart that was never saved, before any juror is asked
    (tmp_path / "w" / "s1.py").write_text(shown)
    v, why = verifier.verify({"agent": "coder", "id": "s1", "task": task},
                             {"returncode": 0, "summary": "b is higher", "files": [],
                              "code_path": str(tmp_path / "w" / "s1.py")}, Board(tmp_path, echo=False), tmp_path / "w")
    assert v == "FAIL" and "saved no image" in why
    assert coder.unsaved_output("Save the three cheapest books to a CSV", "print(1)", []) is not None
    assert coder.unsaved_output("Compute the mean of data.csv", "print(1)", []) is None
    assert coder.unsaved_output("Find the shortest path in this graph", "import networkx as nx\nprint(3)", []) is None


def test_a_name_alone_is_not_an_instruction_of_its_own(monkeypatch):
    """'Plot the counts of A and B as a bar chart' was cut into 'Plot the counts of A' and 'B'; the critic then had
    nothing to check 'B' against."""
    from team.cells import use
    from team.specialists import coordinator
    goal = ("Plot the Hugging Face download counts of org/model-a and other/model-b as a bar chart and tell me which "
            "is higher.")
    monkeypatch.setattr(use, "ask", lambda s, t, b=None: "Plot the Hugging Face download counts of org/model-a\n"
                                                         "other/model-b\ntell me which is higher")
    assert coordinator._split(goal) == ["Plot the Hugging Face download counts of org/model-a and other/model-b",
                                        "tell me which is higher"]


def test_the_browser_sees_the_rare_goal_word_before_the_menu():
    """On the right book page the UPC line was cut: 'Books' and 'Philosophy' in the menu and the long description used
    up the budget first, and the browser gave up on the page that held the answer."""
    from team.tools.browser import focus_text
    menu = "\n".join(["Books to Scrape We love being scraped!", "Home  Books  Philosophy Sophie's World"]
                     + [f"Books category {i}" for i in range(40)] + ["Philosophy"] * 3)
    desc = "Product Description\n" + "\n".join(["A book of philosophy for every reader, " * 6] * 4)
    table = ("Product Information\nUPC\n6be3beb0793a53e7\nProduct Type\nBooks\nPrice (excl. tax)\n£15.94\n"
             "Availability\nIn stock (18 available)\nNumber of reviews\n0")  # one cell per line, as read
    page = menu + "\n" + desc + "\n" + table
    seen = focus_text(page, "On books.toscrape.com, go to the Philosophy category, open the first book there and "
                            "tell me its UPC.")
    assert "6be3beb0793a53e7" in seen and len(seen) < 1800
    from team.tools.browser import goal_words
    assert "upc" in goal_words("tell me its UPC.") and "books.toscrape.com" in goal_words("on books.toscrape.com")


def test_a_value_never_found_is_not_covered_with_a_placeholder(tmp_path, monkeypatch):
    """Held-out run: the author was in <small class="author">, the program looked for a span, and its fix wrote
    'Unknown' in all 10 rows; three jurors passed the CSV."""
    from team.board import Board
    from team.specialists import coder, verifier
    from team import prompts
    assert "placeholder" in prompts.FIX_HINTS["data"] and "check for missing values" not in prompts.FIX_HINTS["data"]
    covered = ("import csv\nrows = [('a quote', None), ('another', None)]\nwith open('quotes.csv', 'w', newline='') as f:\n"
               "    w = csv.writer(f)\n    w.writerow(['Text', 'Author'])\n"
               "    for t, a in rows:\n        w.writerow([t, a or 'Unknown'])\nprint('saved 2 quotes')\n")
    found = covered.replace("None), ('another', None)", "'Ann'), ('another', 'Bo')")
    progs, asked = iter([covered, found]), []
    monkeypatch.setattr(coder, "preview", lambda task, wd: "")
    monkeypatch.setattr(coder, "review", lambda *a: [])
    monkeypatch.setattr(coder.llm, "chat", lambda role, msgs, **k: asked.append(msgs[-1]["content"])
                        or f"```python\n{next(progs)}```")

    class G:
        def check_code(self, who, code):
            return True
    out = coder.run("Save the text and author of every quote to a CSV file.", "", Board(tmp_path, echo=False), "s1", G(),
                    tmp_path / "w")
    assert out["files"] == ["quotes.csv"] and "'Unknown' in all 2 rows" in asked[1]
    p = tmp_path / "bad.csv"
    p.write_text("Text,Author,Notes\nx,N/A,\ny,N/A,\n")
    assert verifier.describe_file(p).startswith("BROKEN") and "'Author'" in verifier.describe_file(p)
    p.write_text("Text,Author\nx,Ann\ny,Unknown\n")  # one author not known is data, not a cover-up
    assert not verifier.describe_file(p).startswith("BROKEN")


def test_the_answer_comes_in_the_form_he_asked_for(tmp_path, monkeypatch):
    """Held-out runs: 'One decimal place' printed 42.16 (the prompt's example said round(answer, 2)); 'what day of the
    week' printed weekday() = 6 and the writer turned it into 'Saturday'."""
    from team.board import Board
    from team.specialists import calculator
    from team import prompts
    assert "round(answer, 2)" not in prompts.CALCULATOR and "strftime" in prompts.CALCULATOR
    progs, asked = iter(["from datetime import date\nprint('Answer:', date(1976, 7, 4).weekday())",
                         "from datetime import date\nprint('Answer:', date(1976, 7, 4).strftime('%A'))"]), []
    monkeypatch.setattr(calculator.llm, "chat", lambda role, msgs, **k: asked.append(msgs[-1]["content"])
                        or f"```python\n{next(progs)}\n```")
    out = calculator.run("What day of the week was 4 July 1976?", "", Board(tmp_path, echo=False), "s1", tmp_path)
    assert out["summary"] == "Answer: Sunday" and "strftime" in asked[1] and "Output was: Answer: 6" in asked[1]
    assert calculator.form_problems("How many km is 26.2 miles? One decimal place.", "26.2 miles = 42.16 km")
    assert not calculator.form_problems("How many km is 26.2 miles? One decimal place.", "Answer: 42.2")
    assert not calculator.form_problems("What is 17% of 300?", "Answer: 51.0")


def test_a_report_that_repeats_his_text_has_not_done_what_he_ordered_to_it():
    """Held-out run: 'Translate into Spanish: ...' came back as the English sentence; the critic ticked it done."""
    from team.specialists.writer import echoed, mark_echo
    from team.board import Board
    goal = "Translate into Spanish: 'The library closes at eight tonight.'"
    assert echoed(goal, "The library closes at eight tonight.")
    assert not echoed(goal, "La biblioteca cierra a las ocho esta noche.")
    fix = "Correct the grammar of this sentence: 'She don't like the apples that was on the table.'"
    assert echoed(fix, "She don't like the apples that was on the table.")
    assert not echoed(fix, "She doesn't like the apples that were on the table.")
    assert not echoed("What is a hash table?", "A hash table maps keys to values.")
    # held-out after the fixes: the writer's fix gave the sentence three times, and it passed as a rewrite
    polite = "Rewrite this to sound polite and give me only the new sentence: 'Send me the file now.'"
    assert echoed(polite, "Send me the file now.  \nSend me the file now.  \nSend me the file now.")
    assert echoed(polite, "Send me the file now, now.")
    assert not echoed(polite, "Could you please send me the file?")
    assert not echoed("Fix the bug in this code: def f(x): return x - 1  # should add one", "def f(x): return x + 1")
    import tempfile
    from pathlib import Path
    b = Board(Path(tempfile.mkdtemp()), echo=False)
    ticks = mark_echo(goal, "The library closes at eight tonight.", [{"instruction": goal, "done": True}], b)
    assert ticks[0]["done"] is False
    # and the writer working on his own text is told to change it, not to report it "from the verified results"
    from team.specialists.writer import OWN_TEXT, messages
    from team import prompts
    m = messages(goal, "Write the finished answer", f"{OWN_TEXT}\n{goal}", [])
    assert m[0]["content"] == prompts.WRITER_TEXT and "VERIFIED RESULTS" not in m[1]["content"]
    assert messages("What is X?", "s", "## s1 ...", [])[0]["content"] == prompts.WRITER


def test_a_page_reads_as_sentences_and_a_quote_is_found_across_its_links():
    """Every text node on its own line made Wikipedia read 'In\\ncomputer science\\n, a\\nhash table ...'; a quote
    written as the page shows it was never found, and every fact of a held-out explanation was rejected."""
    from team.tools.web import readable
    from team.specialists.verifier import quote_in
    html = ('<html><body><main><p>In <a href="/cs">computer science</a>, a <b>hash table</b> is a '
            '<a href="/ds">data structure</a> that maps <a href="/k">keys</a> to values.<sup>[3]</sup> A hash table uses '
            'a <a href="/hf">hash function</a>.</p><ul><li>one</li><li>two</li></ul>'
            '<table><tr><th>UPC</th><td>6be3beb0793a53e7</td></tr></table></main></body></html>')
    page = readable(html, "https://en.wikipedia.org/wiki/Hash_table")
    assert ("In computer science, a hash table is a data structure that maps keys to values.[3] A hash table uses a "
            "hash function.") in page["text"]
    assert "one\ntwo" in page["text"] and "UPC | 6be3beb0793a53e7" in page["text"]
    assert ("computer science", "https://en.wikipedia.org/cs") in page["links"]
    assert quote_in("a hash table is a data structure that maps keys to values. A hash table uses a hash function",
                    "In\ncomputer science\n, a\nhash table\nis a\ndata structure\nthat maps keys to values.\n[\n3\n]\n"
                    "A hash table uses a\nhash function\n.")
    assert not quote_in("a hash table maps names to addresses", page["text"])  # its words, in order, or nothing


def test_a_prompt_too_long_for_the_window_is_cut_in_the_middle_not_crashed():
    """A researcher read a long article and crashed: 'Requested tokens (4119) exceed context window of 4096'."""
    from team.llm import CUT, fit
    count = lambda ms: sum(len(m["content"]) // 4 + 4 for m in ms)  # noqa: E731
    ms = [{"role": "system", "content": "Extract facts."},
          {"role": "user", "content": "TASK: what slows it?\n" + "page text " * 3000 + "\nReply with JSON."}]
    out, budget = fit(ms, count, 4096, 900)
    assert count(out) + budget <= 4096 and CUT.strip() in out[1]["content"]
    assert out[1]["content"].startswith("TASK: what slows it?") and out[1]["content"].endswith("Reply with JSON.")
    assert fit(ms[:1], count, 4096, 900) == (ms[:1], 900)


def test_a_research_question_never_takes_a_shortcut_to_another_specialist(tmp_path, monkeypatch):
    """The triage cell said 'code' (0.92) for 'Research how lithium-ion batteries degrade ...': the research hive
    never ran and the coder fetched a blocked site."""
    from team.board import Board
    from team.cells import runtime, use
    from team.specialists import coordinator
    b = Board(tmp_path, echo=False)
    monkeypatch.setattr(use, "on", lambda s: s == "task_kind")
    monkeypatch.setattr(use, "wins", lambda: {})
    monkeypatch.setattr(runtime, "label_probs", lambda s, t: {"code": 0.95, "plan": 0.05})
    steps = coordinator.triage("Research how lithium-ion batteries degrade over time and what slows it.", b)
    assert [s["agent"] for s in steps] == ["researcher", "writer"] and "batteries" in steps[0]["task"]
    assert coordinator.triage("Research battery degradation and save the findings to a CSV file.", b) is None
    assert [s["agent"] for s in coordinator.triage("Write a Python function that reverses a string.", b)] == \
        ["coder", "writer"]
    # the coordinator's padding: steps added "if needed" are not his orders
    plan = [{"id": "s1", "agent": "researcher", "task": "Find facts about X", "needs": []},
            {"id": "s2", "agent": "browser", "task": "Search the web for X, if needed", "needs": []},
            {"id": "s3", "agent": "coder", "task": "Process data about X if necessary", "needs": ["s1"]},
            {"id": "s4", "agent": "writer", "task": "Write it", "needs": ["s1", "s2", "s3"]}]
    kept, note = coordinator.drop_padding(plan)
    assert [s["id"] for s in kept] == ["s1", "s4"] and kept[1]["needs"] == ["s1"] and note
    only = [{"id": "s1", "agent": "coder", "task": "Fix it if needed", "needs": []}, plan[3]]
    assert coordinator.drop_padding(only) == (only, [])  # never the only step doing the work


def test_layout_orders_are_the_report_s_and_verified_facts_carry_a_step(tmp_path, monkeypatch):
    """A held-out explanation: every search title was dropped for 'not giving the two-sentence explanation', and the
    step failed although its facts were checked against Wikipedia."""
    from team.board import Board
    from team.specialists import verifier
    assert verifier.without_layout("Find what Arnav asked: In two sentences, explain what a hash table is.") == \
        "Find what Arnav asked: explain what a hash table is."
    assert verifier.without_layout("Summarise this in one sentence: the bridge") == "Summarise this: the bridge"
    page = "In computer science, a hash table is a data structure that maps keys to values."
    monkeypatch.setattr(verifier, "check_fact", lambda c, q: (True, "stub"))
    monkeypatch.setattr(verifier.llm, "chat_json", lambda *a, **k: ({"meets": False, "why": "not two sentences"}, ""))
    monkeypatch.setattr(verifier, "judge", lambda check, work, ev: ("PASS", "stub jury"))
    from team.cells import learn
    monkeypatch.setattr(learn, "decide", lambda *a, **k: None)
    monkeypatch.setattr(learn, "record", lambda *a, **k: None)
    url = "https://en.wikipedia.org/wiki/Hash_table"
    v, why = verifier.verify(
        {"agent": "researcher", "id": "s1", "task": "In two sentences, explain what a hash table is."},
        {"corpus": {url: page}, "items": ["hash table"], "summary": "A hash table maps keys to values.",
         "facts": [{"claim": "A hash table maps keys to values", "quote": "a hash table is a data structure that maps keys "
                    "to values", "url": url}]}, Board(tmp_path, echo=False), tmp_path)
    assert v == "PASS"


def test_scholarly_papers_are_a_source_with_their_abstracts(monkeypatch):
    """Research needs what studies found: OpenAlex (free, every field) gives each paper's abstract, quotable and
    credited to its DOI; a key, if he sets one, never reaches an error message."""
    from team.tools import web
    seen = {}

    def fake_get(url, params=None, as_json=False):
        seen.update(params or {})
        return {"results": [
            {"doi": "https://doi.org/10.1/none", "display_name": "No abstract", "publication_date": "2020-01-01",
             "cited_by_count": 3, "abstract_inverted_index": None, "primary_location": {}},
            {"doi": "https://doi.org/10.1/aging", "display_name": "Calendar  aging of cells", "publication_date": "2021-05-02",
             "cited_by_count": 40, "abstract_inverted_index": {"Heat": [0], "speeds": [1], "aging.": [2]},
             "primary_location": {"source": {"display_name": "J. Power Sources"}}}]}
    monkeypatch.setattr(web, "get", fake_get)
    monkeypatch.setenv("OPENALEX_API_KEY", "k-123")
    res = web.search("openalex", "battery aging", newest=True)
    assert res[0]["url"] == "https://doi.org/10.1/aging" and res[0]["title"] == "Calendar aging of cells"
    assert res[0]["snippet"].endswith("| J. Power Sources | Heat speeds aging.") and res[1]["title"] == "No abstract"
    assert seen["sort"] == "publication_date:desc" and seen["api_key"] == "k-123"
    assert "k-123" not in web.redact("https://api.openalex.org/works?search=x&api_key=k-123&per-page=6")

    class R:
        headers, text = {}, '{"message": "Please retry in 31s"}'
    assert web.retry_wait(R(), 0) == 31


def test_an_explanation_is_never_rerouted_to_a_program(monkeypatch):
    """Held-out: the researcher's explanation failed and was rerouted to 'Write a Python program that explains what a
    hash table is in two sentences', which made invalid Python."""
    from team.specialists import coordinator
    step = {"id": "s1", "agent": "researcher", "task": "Explain what a hash table is.", "needs": [], "done_when": ""}
    monkeypatch.setattr(coordinator.llm, "chat_json", lambda *a, **k: (
        {"agent": "coder", "task": "Write a Python program that explains what a hash table is in two sentences."}, ""))
    assert coordinator.reroute("In two sentences, explain what a hash table is.", step, "no fact") is None
    monkeypatch.setattr(coordinator.llm, "chat_json", lambda *a, **k: (
        {"agent": "coder", "task": "Fetch the downloads from the Hugging Face API and print them."}, ""))
    assert coordinator.reroute("Plot the download counts of a and b", step, "x")["agent"] == "coder"


def test_a_retry_previews_his_pages_not_the_missing_page_in_its_error(tmp_path, monkeypatch):
    """Dev re-run: a retry carrying '404 ... for url: https://books.toscrape.com/page-2.html' previewed only that
    missing page, losing the Mystery listing; the 404 got the generic network hint."""
    from team.board import Board
    from team.specialists import coder
    previewed = []
    monkeypatch.setattr(coder, "preview", lambda task, wd: previewed.append(task) or "")
    monkeypatch.setattr(coder.llm, "chat", lambda *a, **k: "```python\nprint('saved 3 books to books.csv')\n```")
    monkeypatch.setattr(coder, "review", lambda *a: [])

    class G:
        def check_code(self, who, code):
            return True
    task = ("Find the three cheapest Mystery books on books.toscrape.com and save them to a CSV.\n(Previous attempt was "
            "rejected: program exited 1: 404 Client Error: Not Found for url: https://books.toscrape.com/page-2.html)")
    coder.run(task, "", Board(tmp_path, echo=False), "s1", G(), tmp_path / "w")
    assert previewed == ["Find the three cheapest Mystery books on books.toscrape.com and save them to a CSV."]
    assert coder.error_kind("requests.exceptions.HTTPError: 404 Client Error: Not Found for url: https://x/p.html") \
        == "not_found"
    assert coder.error_kind("requests.exceptions.HTTPError: 503 Server Error") == "network"
    assert "urljoin(the URL of the page the link was found on" in coder.prompts.FIX_HINTS["not_found"]


def test_a_missing_element_is_looked_up_on_the_page_itself(tmp_path, monkeypatch):
    """Held-out, twice: the preview showed <small class="author">; the coder looked for a span both times, and the
    same-error check compared the hint (the same every time), not the error."""
    from team.board import Board
    from team.specialists import coder
    from team.tools import web
    html = ('<div class="quote"><span class="text">"Be."</span><span>by <small class="author">Ann</small></span></div>'
            '<div class="quote"><span class="text">"Go."</span><span>by <small class="author">Bo</small></span></div>')
    monkeypatch.setattr(web, "get", lambda url, *a, **k: html)
    err = ('Traceback (most recent call last):\n  File "s1.py", line 9, in <module>\n'
           "    author = quote.find('span', class_='author').get_text(strip=True)\n"
           "AttributeError: 'NoneType' object has no attribute 'get_text'")
    fact = coder.page_fact(err, ["https://quotes.toscrape.com/"])
    assert "no <span class=\"author\">" in fact and "is on <small>" in fact and "find('small', class_='author')" in fact
    assert coder.page_fact(err.replace("'span'", "'small'"), ["https://quotes.toscrape.com/"]) is None
    assert "is on <small>" in coder.page_fact("x = soup.select_one('span.author').text", ["https://q/"])
    # in the loop: the coder is told, and a different error after it is not taken for 'the same error'
    progs = iter(["import sys\nprint(None.get_text())  # quote.find('span', class_='author').get_text()\n",
                  "print({}['a'])\n", "print('saved 2 quotes')\n"])
    asked = []
    monkeypatch.setattr(coder, "preview", lambda task, wd: "")
    monkeypatch.setattr(coder, "review", lambda *a: [])
    monkeypatch.setattr(coder.llm, "chat", lambda role, msgs, **k: asked.append(msgs[-1]["content"])
                        or f"```python\n{next(progs)}```")

    class G:
        def check_code(self, who, code):
            return True
    out = coder.run("Save every quote on quotes.toscrape.com", "", Board(tmp_path, echo=False), "s1", G(), tmp_path / "w")
    assert "Page check:" in asked[1] and "is on <small>" in asked[1] and out["summary"] == "saved 2 quotes"


def test_a_named_answer_passes_the_calculator_s_check(tmp_path, monkeypatch):
    """Held-out after the fixes: the calculator printed 'Answer: Sunday' (right), and the verifier failed it three
    times for printing no number."""
    from team.board import Board
    from team.specialists import verifier
    monkeypatch.setattr(verifier, "_judge_one", lambda *a, **k: ("PASS", "stub"))
    step = {"agent": "calculator", "id": "s1", "task": "What day of the week was 4 July 1976?"}
    ok = verifier.verify(step, {"summary": "Answer: Sunday", "returncode": 0, "code": "print('Answer: Sunday')"},
                         Board(tmp_path, echo=False), tmp_path)
    assert ok[0] == "PASS"
    bad = verifier.verify(step, {"summary": "Answer: done", "returncode": 0, "code": "print('Answer: done')"},
                          Board(tmp_path, echo=False), tmp_path)
    assert bad == ("FAIL", "the program printed no number")


def test_a_browser_answer_s_values_must_be_in_its_evidence(tmp_path, monkeypatch):
    """Held-out set 2: 'Thomas A. Edison was born on 1847-02-04' with the evidence 'by Thomas A. Edison (about)' (no
    date at all) passed the jury 3/3; he was born on 11 February 1847."""
    from team.board import Board
    from team.specialists import verifier
    monkeypatch.setattr(verifier, "judge", lambda *a: ("PASS", "stub jury"))
    page = "“Genius is one percent inspiration...” by Thomas A. Edison (about) Born: February 11, 1847"
    step = {"agent": "browser", "id": "s1", "task": "tell me his date of birth"}
    v, why = verifier.verify(step, {"summary": "Thomas A. Edison was born on 1847-02-04", "page_text": page,
                                    "evidence": "by Thomas A. Edison (about)", "url": "https://q/"},
                             Board(tmp_path, echo=False), tmp_path)
    assert v == "FAIL" and "1847-02-04" in why
    v, _ = verifier.verify(step, {"summary": "He was born on February 11, 1847.", "page_text": page,
                                  "evidence": "Born: February 11, 1847", "url": "https://q/"},
                           Board(tmp_path, echo=False), tmp_path)
    assert v == "PASS"
    assert verifier.values_not_in("Here are the 3 quotes", "“A” “B” “C”") == []  # a small count is not a value to copy
    assert verifier.values_not_in("It costs £51.77", "Price £51.77 In stock") == []


def test_a_missing_page_is_found_where_it_really_is_and_page_one_means_page_one(monkeypatch):
    """Held-out set 2 and a dev run: 'page-2.html' was joined to the site's home page (404) and the hint, given
    twice, did not change the program; the task had asked for the first page only."""
    from team.specialists import coder
    from team.tools import web
    from team.tools.preview import FIRST_PAGE
    real = {"https://books.toscrape.com/catalogue/category/books/food-and-drink_33/page-2.html"}

    def fake_get(url, *a, **k):
        if url in real or url.endswith("index.html") or url == "https://books.toscrape.com/":
            return "<html></html>"
        raise web.FetchError(f"HTTP 404 from {url}")
    monkeypatch.setattr(web, "get", fake_get)
    err = ("requests.exceptions.HTTPError: 404 Client Error: Not Found for url: https://books.toscrape.com/page-2.html")
    code = 'url = urljoin(base_url, "catalogue/category/books/food-and-drink_33/index.html")'
    fact = coder.missing_page_fact(err, ["https://books.toscrape.com/"], code)
    assert "food-and-drink_33/page-2.html, which exists" in fact
    assert FIRST_PAGE.search("every book's name and price from the first page of the Food and Drink category")
    assert not FIRST_PAGE.search("the three cheapest Mystery books")


def test_a_number_counts_by_its_value_not_its_spelling():
    """Held-out set 2: the calculator printed 161.0, the writer wrote $161.00, and the report's grounding struck the
    right answer because the strings differed."""
    from team.specialists.writer import ground_numbers
    text, struck = ground_numbers("The discount is **$161.00**.\n| 35% of 460 | 161.00 |", "Result: Answer: 161.0\n460 35%")
    assert struck == [] and "161.00" in text
    text, struck = ground_numbers("The discount is 162.", "Answer: 161.0")
    assert struck == ["The discount is 162."]


def test_data_he_hands_over_goes_to_the_calculator_whatever_the_cell_says(tmp_path, monkeypatch):
    """Held-out set 2: the cell was unsure ('plan' 0.62) for 'Monthly rainfall in mm: Jan 80, ...'; the coordinator sent
    researchers to search the web for it and a coder to an invented URL, and the data check skipped a plan with a
    coder in it."""
    from team.board import Board
    from team.cells import runtime, use
    from team.specialists import coordinator
    b = Board(tmp_path, echo=False)
    monkeypatch.setattr(use, "on", lambda s: s == "task_kind")
    monkeypatch.setattr(runtime, "label_probs", lambda s, t: {"plan": 0.62, "calc": 0.38})
    rain = "Monthly rainfall in mm: Jan 80, Feb 65, Mar 72, Apr 40. Which month was the driest, and what was the average?"
    assert [s["agent"] for s in coordinator.triage(rain, b)] == ["calculator", "writer"]
    assert coordinator.triage("Monthly sales: Jan 120, Feb 95, Mar 143. Plot them as a bar chart.", b) is None
    plan = [{"id": "s1", "agent": "researcher", "task": "Find the rainfall data", "needs": []},
            {"id": "s2", "agent": "coder", "task": "Calculate the average", "needs": ["s1"]},
            {"id": "s3", "agent": "writer", "task": "Write it", "needs": ["s2"]}]
    fixed, notes = coordinator.ensure_data_steps(rain, plan)
    assert [s["agent"] for s in fixed] == ["calculator", "calculator", "writer"]
    assert notes[1].startswith("s2: coder -> calculator")


def test_the_research_hive_splits_the_question_not_the_step_s_wrapper(tmp_path, monkeypatch):
    """Research eval: handed 'Find, with quotes from sources, what Arnav asked: Research how ...', the decomposer made
    'What did Arnav ask about lithium-ion battery degradation?' a sub-question, and called a literature question about
    batteries an experiment."""
    from team.board import Board
    from team.specialists import research_hive as R
    seen = []
    monkeypatch.setattr(R, "decompose", lambda task, board: seen.append(task) or [])
    monkeypatch.setattr(R, "answered", lambda facts, board: [])
    monkeypatch.setattr(R, "conflicts", lambda facts, board, limit=24: [])
    R.run("Find, with quotes from sources, what Arnav asked: Research how lithium-ion batteries degrade over time.", "",
          Board(tmp_path, echo=False), "s1")
    assert seen == ["Research how lithium-ion batteries degrade over time."]
    assert "Never for the physical world" in R.DECOMPOSE and "never about what Arnav asked" in R.DECOMPOSE


def test_only_what_this_computer_can_test_is_an_experiment(tmp_path, monkeypatch):
    """Research eval: the 4B called 'What factors slow the degradation of lithium-ion batteries?' an experiment; a
    program would have invented a battery model and its numbers would have counted as verified."""
    from team.board import Board
    from team.specialists import research_hive as R
    monkeypatch.setattr(R.llm, "chat_json", lambda *a, **k: ({"questions": [
        {"q": "How do lithium-ion batteries degrade?", "how": "read"},
        {"q": "What factors slow the degradation?", "how": "experiment"}]}, ""))
    b = Board(tmp_path, echo=False)
    assert [h for _, h in R.decompose("Research how lithium-ion batteries degrade over time.", b)] == ["read", "read"]
    got = R.decompose("Run an experiment to test whether Python's sort is faster than a merge sort.", b)
    assert [h for _, h in got] == ["read", "experiment"]


def test_a_budget_spent_for_the_day_is_not_waited_for(monkeypatch):
    """OpenAlex's anonymous budget ran out; every search then waited twice (about 90 s) for a 429 that could not
    clear."""
    from team.tools import web
    calls = []

    class R:
        status_code, headers, url = 429, {}, "https://api.openalex.org/works?search=x"
        apparent_encoding = encoding = "utf-8"
        text = '{"error":"Rate limit exceeded","message":"Insufficient budget. This request has no API key, so ..."}'
    monkeypatch.setattr(web._S, "get", lambda url, params=None, timeout=None: calls.append(url) or R())
    monkeypatch.setattr(web, "_wait", lambda s: (_ for _ in ()).throw(AssertionError("waited")))
    monkeypatch.setattr(web, "SPENT", {})
    monkeypatch.setattr(web, "_cache", {})
    import pytest
    with pytest.raises(web.FetchError):
        web.get("https://api.openalex.org/works", {"search": "x"})
    with pytest.raises(web.FetchError, match="skipped for the rest of this run"):
        web.get("https://api.openalex.org/works", {"search": "y"})
    assert len(calls) == 1


def test_the_researcher_judges_which_facts_answer_a_sub_question(tmp_path, monkeypatch):
    """Research eval: the answers_q cell said 'no' to all 15 real facts (3/15 right), 'SEI growth is a degradation
    mechanism' against 'How do lithium-ion batteries degrade?' among them; it scored 0.933 on synthetic data."""
    import json
    from team.board import Board
    from team.cells import use
    from team.specialists import research_hive as R
    b = Board(tmp_path, echo=False)
    facts = [{"question": "How do lithium-ion batteries degrade?", "claim": c} for c in
             ("SEI growth is a degradation mechanism", "Paris is the capital of France")]
    monkeypatch.setattr(use, "on", lambda s: s == "answers_q")
    monkeypatch.setattr(use, "ask_all", lambda skill, texts, board=None: ["no"] * len(texts))
    monkeypatch.setattr(R.llm, "chat_json", lambda *a, **k: ({"answers": ["yes", "no"]}, ""))
    assert R.answered(facts, b) == [True, False]
    monkeypatch.setattr(R.llm, "chat_json", lambda *a, **k: (None, "garbled"))
    assert R.answered(facts, b) == [True, True]  # unreadable reply, cell not checked on real pairs: every fact counts
    real = [json.loads(x) for x in open("training/evals/answers_q_real.jsonl")]
    assert len(real) == 15 and sum(r["label"] == "yes" for r in real) == 12


def test_an_instruction_no_source_answered_is_not_ticked_done(tmp_path):
    """The battery report answered 'what slows the degradation' with factors that drive it, after the research hive
    found nothing that answers it; the critic ticked it."""
    from team.board import Board
    from team.specialists.writer import mark_open, open_questions
    b = Board(tmp_path, echo=False)
    b.add_step({"id": "s1", "agent": "researcher", "task": "research", "needs": [], "for_each": None, "done_when": ""})
    b.update_step("s1", verdict="PASS", status="done",
                  result={"sub_questions": [["How do lithium-ion batteries degrade over time?", "read"],
                                            ["What factors slow the degradation of lithium-ion batteries?", "read"]],
                          "open_questions": ["What factors slow the degradation of lithium-ion batteries?"]})
    open_qs = open_questions(b)
    ticks = [{"instruction": "Research how lithium-ion batteries degrade over time", "done": True},
             {"instruction": "what slows the degradation", "done": True}]
    out = mark_open(ticks, open_qs)
    assert out[0]["done"] is True and out[1]["done"] is False and "no source" in out[1]["why"]


def test_a_sentence_from_memory_in_a_sourced_report_is_flagged():
    """The single researcher's battery report: four paragraphs on battery management systems from one verified claim
    about modelling, 'based on the verified results', and nothing flagged."""
    from team.specialists.writer import ungrounded
    verified = ("- Lithium-ion battery degradation is caused by SEI growth, lithium plating and electrolyte "
                "decomposition (quote: ...)\n- Degradation depends on design factors and operating conditions")
    report = ("SEI growth, lithium plating and electrolyte decomposition cause lithium-ion battery degradation.\n"
              "Effective battery management systems monitor and control charge cycles, keeping optimal operating "
              "temperatures and humidity to extend service life considerably.\n## Sources\n[1] x")
    flagged = ungrounded(report, verified)
    assert len(flagged) == 1 and flagged[0].startswith("Effective battery management")


def test_a_search_result_naming_the_question_s_subject_is_relevant():
    """Research eval: 'Compare the speed of SQLite and DuckDB for analytics on a laptop' has six content words, so
    Wikipedia's SQLite article (one of them) was dropped with every other result."""
    from team.specialists import research_hive as R
    q = "Compare the speed of SQLite and DuckDB for analytics on a laptop"
    assert R.subjects(q) == {"sqlite", "duckdb"}
    res = [{"title": "SQLite", "snippet": "SQLite is a database engine written in C"},
           {"title": "Laptop", "snippet": "A laptop is a small portable computer"}]
    assert R.relevant(q, res) == [True, False]


def test_an_experiment_result_names_its_method_and_rewordings_are_not_conflicts(tmp_path, monkeypatch):
    """Research eval (sorting experiment): 'RESULT: Time taken: 0.001302 seconds' after 'METHOD: Python's built-in
    sort' said nothing of which sort, and the critic flagged the right measurements; the claims_agree cell called
    four rewordings of 'Python uses timsort' conflicts."""
    from team.board import Board
    from team.cells import use
    from team.specialists import coder, research_hive as R
    work = tmp_path / "w"
    work.mkdir()
    (work / "s1_exp1.py").write_text("print('x')")
    out = ("METHOD: Python's built-in sort\nRESULT: Time taken: 0.001302 seconds\n"
           "METHOD: Hand-written merge sort\nRESULT: Time taken: 0.014714 seconds\n")
    monkeypatch.setattr(coder, "run", lambda *a, **k: {"summary": out, "returncode": 0,
                                                       "code_path": str(work / "s1_exp1.py")})
    facts, _, _, _ = R.experiment("Is the built-in sort faster?", Board(tmp_path, echo=False), "s1", None, work)
    assert [f["claim"] for f in facts] == ["Python's built-in sort: Time taken: 0.001302 seconds",
                                           "Hand-written merge sort: Time taken: 0.014714 seconds"]
    monkeypatch.setattr(use, "on", lambda s: s == "claims_agree")
    monkeypatch.setattr(use, "ask_all", lambda skill, texts, board=None: ["conflict"] * len(texts))
    same = [{"claim": "Timsort is used in Python's standard library", "url": "https://a"},
            {"claim": "Python's built-in sort is called timsort", "url": "https://b"}]
    assert R.conflicts(same) == []
    two = [{"claim": "The array makes 320 MW", "url": "https://a"}, {"claim": "The array makes 302 MW", "url": "https://b"}]
    assert len(R.conflicts(two)) == 1


def test_a_translation_is_written_by_the_member_that_translates_best(tmp_path, monkeypatch):
    """training/translator.py on 120 held-out professional translations: the 4B 51.6 chrF, a translation edit of the
    1.7B 48.4, the writer 46.7 (held-out set 2: 'Der Zug fährt um 9 Uhr in der Morgens')."""
    from team.board import Board
    from team.specialists import writer
    roles = []
    monkeypatch.setattr(writer.llm, "chat", lambda role, msgs, **k: roles.append(role) or "Der Zug fährt um neun Uhr morgens ab.")
    monkeypatch.setattr(writer.llm, "chat_json", lambda *a, **k: ({"unsupported": [], "unordered": [], "checklist": []}, ""))
    monkeypatch.setattr(writer.memory, "profile", lambda: "")
    writer.run("Translate into German: 'The train leaves at nine in the morning.'", "Translate it",
               Board(tmp_path, echo=False), [])
    assert roles[0] == "editor"
    assert writer.translator_role("Summarise this: ...", f"{writer.OWN_TEXT}\n...") == "writer"


def test_the_browser_does_not_give_up_while_a_next_page_is_unread(tmp_path, monkeypatch):
    """Held-out set 3: Khaled Hosseini is not on the first page of quotes.toscrape.com; the browser gave up there
    without following a link, and the page's lines failed on '10,000' (a check meant for answers)."""
    from team.board import Board
    from team.specialists import browser_agent, verifier

    class B:
        elements = {1: {"id": 1, "tag": "a", "text": "Next →", "href": "/page/2/"},
                    2: {"id": 2, "tag": "a", "text": "Login", "href": "/login"}}
    assert browser_agent.next_link(B())["id"] == 1
    B.elements = {2: {"id": 2, "tag": "a", "text": "Login", "href": "/login"}}
    assert browser_agent.next_link(B()) is None
    monkeypatch.setattr(verifier, "judge", lambda *a: ("FAIL", "stub jury"))
    v, why = verifier.verify({"agent": "browser", "id": "s1", "task": "his date of birth"},
                             {"summary": "From https://quotes.toscrape.com/:\nTop Ten tags\n10,000 quotes",
                              "evidence": "Top Ten tags", "page_text": "Top Ten tags 10,000 quotes",
                              "url": "https://quotes.toscrape.com/"}, Board(tmp_path, echo=False), tmp_path)
    assert "which the evidence copied from the page does not contain" not in why
