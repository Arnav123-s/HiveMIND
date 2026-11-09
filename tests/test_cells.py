"""Cells: data splits never overlap, scoring is exact, and the hive falls back cleanly when a cell is off."""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from team.cells import skills as S, use  # noqa: E402
from training.cells import data  # noqa: E402


def test_splits_disjoint_and_labelled():
    for skill in S.SKILLS:
        tr, dv, te = data(skill)
        xs = [{x for x, _ in part} for part in (tr, dv, te)]
        assert not (xs[0] & xs[1]) and not (xs[0] & xs[2]), skill
        if "labels" in S.SKILLS[skill]:
            assert all(y in S.SKILLS[skill]["labels"] for _, y in tr + dv + te), skill


def test_scoring():
    assert S.score("json_repair", '{"a": 1}', '{"a":1}') == 1.0
    assert S.score("json_repair", '{"a": 2}', '{"a":1}') == 0.0
    assert S.score("split_orders", "Find x\nEmail me", "Find x\nEmail me") == 1.0
    assert S.score("split_orders", "Find x", "Find x\nEmail me") == 0.0
    assert S.score("route_step", "coder", "coder") == 1.0


def test_orders_cells_use_the_order_reader_labels():
    from training import build_orders as bo
    rows = bo.build(bo.FRAMES_TEST, bo.OBJ_TEST, bo.DISTRACT_TEST, bo.NEG_TEST, 40, 2)
    gold = {t: k for t, k in rows}
    for x, y in S.examples("orders_send", "test", 60):
        assert (y == "yes") == ("send" in gold[x])


def test_cells_switch_off(monkeypatch):
    monkeypatch.setenv("AGENT_TEAM_CELLS", "0")
    assert not use.on("json_repair") and not use.orders_on()
    from team import guard, llm
    assert llm.parse_json("not json at all") is None
    assert guard.check_task("Plan a dinner for my wife", "Find restaurants") is not None
    assert guard.check_task("Kill the child process", "Fix the server") is None


def test_gate_groups_cover_every_skill():
    for skill in S.SKILLS:
        if skill != "gate":
            assert any(skill in m for m in S.GROUPS.values()), skill


def test_registry_updates_merge(tmp_path, monkeypatch):
    from team.cells import runtime
    monkeypatch.setattr(runtime, "CELLS", tmp_path)
    runtime.update_registry("a", {"x": 1})
    runtime.update_registry("b", {"y": 2})
    runtime.update_registry("a", {"z": 3})
    assert runtime.registry() == {"a": {"x": 1, "z": 3}, "b": {"y": 2}}
    runtime.update_registry("a", {"w": 4}, replace=True)
    assert runtime.registry()["a"] == {"w": 4}


def test_page_organizer_asks_each_element_and_acts_on_most_likely_yes(monkeypatch):
    from team.cells import runtime
    seen = []

    def fake(skill, text, edit=True):
        seen.append((skill, text))
        return {"yes": 0.9 if '"Buy now"' in text else 0.1, "no": 0.1}

    monkeypatch.setattr(runtime, "label_probs", fake)
    x = 'GOAL: purchase it\nELEMENTS:\n[19] button "Romance"\n[27] span "Buy now"\n[87] input[text] ""'
    assert runtime.pick_element(x) == "27"
    assert seen[0] == ("element_match", 'GOAL: purchase it\nELEMENT: button "Romance"') and len(seen) == 3


def test_quote_rescue_returns_an_exact_source_sentence(monkeypatch):
    from team.specialists import verifier
    asked = []
    monkeypatch.setattr(use, "on", lambda skill: skill == "quote_pick")
    monkeypatch.setattr(use, "ask", lambda skill, x, board=None: asked.append(x) or "1")
    corpus = {"https://a": "Intro line here.\nThe model Foo-1B is released under the Apache 2.0 licence. Other text.",
              "https://b": "Nothing about it."}
    quote, url = verifier._rescue_quote("Foo-1B is released under Apache 2.0", corpus, None)
    assert url == "https://a" and quote in corpus[url] and "Apache 2.0" in quote
    assert asked and asked[0].startswith("CLAIM: Foo-1B")
    monkeypatch.setattr(use, "on", lambda skill: False)
    assert verifier._rescue_quote("Foo-1B is released under Apache 2.0", corpus, None) is None


def test_family_cell_only_adds_blocks(monkeypatch):
    from team import guard
    monkeypatch.setattr(guard, "_family_cell", lambda text: "Mom" in (text or "") or "offsite" in (text or ""))
    assert guard.check_task("Book a table for Mom", "Find restaurants") is not None   # the cell catches what the rule misses
    assert guard.check_task("Book a table for Mom", "Plan a dinner with Mom") is None  # ordered: allowed
    assert guard.check_task("Text my wife the plan", "Plan the team offsite") is not None  # the cell cannot unlock the rule


def test_checklist_keeps_arnavs_words_and_skips_nothing(monkeypatch):
    from team.specialists import coordinator
    goal = ("Find the licence and the parameter count of HuggingFaceTB/SmolLM2-135M-Instruct on Hugging Face and give me "
            "a two-line summary. Do not log in or pay.")
    monkeypatch.setattr(use, "on", lambda skill: skill == "split_orders")
    monkeypatch.setattr(use, "ask", lambda skill, x, board=None: "Find the licence\nThe parameter count of Hugging Face "
                        "TB/Smol LM2-135M-Instruct on Hugging Face\nGive me a two-line summary")
    items = coordinator.instructions(goal)
    assert "the parameter count of HuggingFaceTB/SmolLM2-135M-Instruct on Hugging Face" in items
    assert items[-1] == "Do not log in or pay"


def test_the_hive_logs_its_members_decisions_and_a_learned_cell_answers_only_when_sure(tmp_path, monkeypatch):
    """Decisions a member makes are logged for growing a cell; a grown cell answers when it is as sure as dev said."""
    from team.cells import learn, runtime
    from team.specialists import verifier
    monkeypatch.setattr(learn, "DIR", tmp_path / "decisions")
    monkeypatch.setattr(verifier.llm, "chat_json", lambda *a, **k: ({"verdict": "SUPPORTED", "reason": "ok"}, ""))
    monkeypatch.setattr(use, "on", lambda k: False)
    for i in range(3):
        assert verifier.check_fact(f"Kalo has {i} pools.", f"Kalo: {i} pools")[0]
    rows = learn.rows("learned_claim")
    assert len(rows) == 3 and rows[0][1] == "SUPPORTED" and "CLAIM: Kalo has 0 pools." in rows[0][0]
    tr, dv, te = learn.split("learned_claim")
    assert len(tr) + len(dv) + len(te) == 3 and data("learned_claim") is not None
    monkeypatch.setattr(use, "wins", lambda: {"learned_claim": {"use": True, "threshold": 0.9}})
    monkeypatch.setattr(runtime, "available", lambda s: True)
    monkeypatch.setattr(runtime, "label_probs", lambda s, t: {"SUPPORTED": 0.95, "UNSUPPORTED": 0.05})
    assert learn.decide("learned_claim", "CLAIM: x\nQUOTE: x") == "SUPPORTED"
    monkeypatch.setattr(runtime, "label_probs", lambda s, t: {"SUPPORTED": 0.6, "UNSUPPORTED": 0.4})
    assert learn.decide("learned_claim", "CLAIM: x\nQUOTE: y") is None  # unsure: the member decides
