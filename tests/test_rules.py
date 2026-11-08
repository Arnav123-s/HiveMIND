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
    assert len(writes) == 2 and len(critiques) == 2
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
