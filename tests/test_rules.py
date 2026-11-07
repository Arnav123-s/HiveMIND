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


@pytest.mark.parametrize("text", ["Plan a dinner for my wife's birthday", "Text my mom that I'm late",
                                  "Help me with my relationship problems", "Find a gift for my girlfriend",
                                  "Organize the family trip itinerary"])
def test_family_is_never_task_material(text):
    assert check_task(text)


@pytest.mark.parametrize("text", ["Find the price of a book on books.toscrape.com",
                                  "Explain the relationship between two variables in this CSV? no wait, plot it",
                                  "Benchmark list.sort on 1M ints"])
def test_normal_tasks_pass(text):
    assert check_task(text) is None


def test_login_and_signup_blocked():
    g = Guard(FakeBoard(), "never")
    with pytest.raises(Blocked):
        g.check_browser("browser", {"action": "click", "id": 1}, {"text": "Login", "href": "/login", "tag": "a"})
    with pytest.raises(Blocked):
        g.check_browser("browser", {"action": "goto", "url": "https://huggingface.co/join"})
    with pytest.raises(Blocked):
        g.check_browser("browser", {"action": "type", "id": 2}, {"type": "password", "text": ""})


def test_login_allowed_only_on_named_site_and_never_signup():
    g = Guard(FakeBoard(), "never", allow_login=["quotes.toscrape.com"])
    assert g.check_browser("browser", {"action": "click", "id": 1}, {"text": "Login", "href": "/login", "tag": "a"},
                           page_url="https://quotes.toscrape.com/")
    with pytest.raises(Blocked):
        g.check_browser("browser", {"action": "click", "id": 1}, {"text": "Login", "href": "/login", "tag": "a"},
                        page_url="https://books.toscrape.com/")
    with pytest.raises(Blocked):
        g.check_browser("browser", {"action": "click", "id": 1}, {"text": "Sign up", "href": "/signup", "tag": "a"},
                        page_url="https://quotes.toscrape.com/")


def test_spend_delete_send_need_approval():
    b = FakeBoard()
    g = Guard(b, "never")
    assert not g.check_browser("browser", {"action": "click", "id": 1}, {"text": "Add to basket", "tag": "button"})
    assert not g.check_browser("browser", {"action": "click", "id": 1}, {"text": "Delete repository", "tag": "button"})
    assert not g.check_browser("browser", {"action": "click", "id": 1}, {"text": "Send", "tag": "button"})
    assert len(g.pending) == 3
    # searching is not sending
    assert g.check_browser("browser", {"action": "press", "key": "Enter"}, {"text": "q", "tag": "input"},
                           typed_fields=[{"search": True}])


def test_code_rules():
    g = Guard(FakeBoard(), "never")
    assert not g.check_code("coder", "import os\nos.remove('x')")
    assert not g.check_code("coder", "import smtplib")
    assert not g.check_code("coder", "requests.post('https://example.com/x', json={})")
    assert g.check_code("coder", "requests.post('https://api.osv.dev/v1/query', json={})")
    assert g.check_code("coder", "print(sum(range(10)))")


def test_standing_policy(tmp_path):
    memory.POLICY.write_text(json.dumps({"delete": "allow"}))
    g = Guard(FakeBoard(), "never")
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
