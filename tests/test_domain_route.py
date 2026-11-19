"""The learned signal and checked neural edit on the ordinary user path."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from team import domain_advice, domain_route, engram, signals, talk, ternary


@pytest.fixture
def routed(monkeypatch):
    from team import domain_consensus
    monkeypatch.delenv("HIVE_SIGNALS", raising=False)
    monkeypatch.setattr(domain_consensus, "read_consensus", lambda message, history, decision: decision)
    monkeypatch.setattr(signals, "read_request", lambda message, history: {"domain": message})


def test_specialist_only_supplies_missing_seat_and_is_request_local(routed):
    sync = Barrier(2)
    def choose(domain):
        with domain_route.for_request(domain):
            sync.wait(timeout=3)
            with domain_route.for_request("conversation", inherit=True):
                assert domain_route.current_domain() == domain
                assert domain_route.specialist("sources") == "sources"
                assert domain_route.specialist("code") == "code"
                return domain_route.specialist(ternary.organ("unrecognized", fallback=None))
    with ThreadPoolExecutor(2) as pool:
        assert list(pool.map(choose, ["machine_learning", "conversation"])) == ["data", "words"]
    with pytest.raises(ValueError), domain_route.for_request("coding"):
        raise ValueError
    assert domain_route.current_domain() is None
    assert domain_route.specialist(None) == "code"


def test_chat_consults_edit_once_and_continues_when_lookup_fails(monkeypatch, tmp_path):
    from team import domain_consensus
    monkeypatch.setattr(domain_consensus, "read_consensus", lambda *args: {"domain": "machine_learning"})
    monkeypatch.delenv("HIVE_SIGNALS", raising=False)
    monkeypatch.delenv("HIVE_ENGRAMS", raising=False)
    monkeypatch.setenv("HIVE_BANK", "off")
    monkeypatch.setattr(ternary, "ENGRAMS", tmp_path)
    row = {"dna": "t80", "name": "e_split", "skill_id": "dataset_split", "domain": "machine_learning",
           "verified": True, "task": "Choose the dataset split", "form": "label", "labels": ["train", "validation", "test"],
           "instruction": "Choose the dataset split.", "cues": ["dataset"]}
    engram.update_index(lambda rows: [row], home=tmp_path)
    (tmp_path / "t80+e_split.gguf").write_bytes(b"fixture")
    monkeypatch.setattr(talk, "route", lambda base, message, history: ("talk", [{"role": "user", "content": message}]))
    responses = iter(["validation", "unrecognized", RuntimeError("model busy")])
    received = []
    def respond(member, messages, **options):
        if options.get("also"):
            assert options["also"] == ("e_split",)
            assert options["max_new_tokens"] == 1
            word = next(responses)
            if isinstance(word, BaseException):
                raise word
            return word
        received.append(messages)
        return "A normal answer."
    monkeypatch.setattr(ternary, "chat", respond)
    for accepted in (True, False, False):
        out = talk.reply("Which dataset should I use for early stopping?", base="t80")
        assert out["domain_signal"]["domain"] == "machine_learning"
        assert out["engram_advice"]["accepted"] is accepted
        assert ("specialist suggests validation" in received[-1][0]["content"]) is accepted
        assert out["text"] == "A normal answer."
    assert out["engram_advice"]["reason"] == "inference_unavailable"
    assert domain_route.advice() is None


def test_phase_edit_respects_units_pressure_and_scope(monkeypatch):
    row = {"name": "phase", "skill_id": "water_phase", "domain": "physical_science", "labels": ["solid", "liquid", "gas"],
           "instruction": "Which phase?"}
    monkeypatch.setattr(engram, "label_for", lambda *args: row)
    monkeypatch.delenv("HIVE_ENGRAMS", raising=False)
    monkeypatch.setattr(ternary, "chat", lambda *args, **kwargs: "gas")
    def consult(msg):
        return domain_advice.consult("Which phase applies? " + msg, "t80", "physical_science", "")
    assert consult("Pure water at 125 °C and 1 atm")["accepted"]
    decision = consult("Pure water at 25 °C and 1 atm")
    assert decision["label"] == "gas" and decision["model_reply"] == "gas" and not decision["accepted"]
    assert decision["check"] == "pure_water_equilibrium_1atm" and decision["checked_phase"] == "liquid"
    assert "gives liquid" in domain_advice.hint(decision)
    assert consult("Water at −20 °C and 1 atm")["checked_phase"] == "solid"
    for message in ("Water at 100 °C and 1 atm", "Water at -20 °C and 10 atm", "Water from 20 to 110 °C at 1 atm",
                    "Water at 120 °F and 1 atm", "Water at ±20 °C and 1 atm", "Salt water at -1 °C and 1 atm"):
        assert consult(message) is None


def test_named_learned_convention_works_without_a_domain_suggestion(tmp_path, monkeypatch):
    monkeypatch.setattr(ternary, "ENGRAMS", tmp_path)
    monkeypatch.setenv("HIVE_BANK", "off")
    monkeypatch.setenv("HIVE_SIGNALS", "0")
    monkeypatch.delenv("HIVE_ENGRAMS", raising=False)
    for year, label in [(2025, "Blue"), (2026, "Amber")]:
        row = {"name": f"eg{year}", "task": f"review policy {year}", "form": "label",
               "dna": "t80", "growth_group": str(year), "verified": True, "domain": "machine_learning",
               "labels": ["Blue", "Amber"], "cues": ["review", "policy"]}
        (tmp_path / f"t80+eg{year}.gguf").write_bytes(b"fixture")
        engram.update_index(lambda rows: rows + [row], home=tmp_path)
    monkeypatch.setattr(talk, "route", lambda base, message, history: ("talk", [{"role": "user", "content": message}]))
    def infer(member, messages, **options):
        if options.get("also"):
            return {"eg2025": "Blue", "eg2026": "Amber"}[options["also"][0]]
        return "Reviewed."
    monkeypatch.setattr(ternary, "chat", infer)
    for year, label in [(2025, "Blue"), (2026, "Amber")]:
        result = talk.reply(f"Under review policy {year}, which label applies to the holdout?", base="t80")
        assert "domain_signal" not in result
        assert result["engram_advice"] == {"engram": f"eg{year}", "skill": f"review policy {year}",
                                          "accepted": True, "label": label}
    ambiguous = talk.reply("Which label applies under review policy 2025 and review policy 2026?", base="t80")
    assert "engram_advice" not in ambiguous


def test_explicit_narrow_task_can_consult_when_topic_is_unknown(monkeypatch):
    row = {"name": "e_clock", "skill_id": "timing_unit", "labels": ["ns", "us", "ms"],
           "instruction": "Choose the timing unit."}
    monkeypatch.delenv("HIVE_ENGRAMS", raising=False)
    monkeypatch.setattr(engram, "named_label_for", lambda *args: None)
    looked_up = []
    def lookup(task, base, domain):
        looked_up.append(domain)
        return row
    monkeypatch.setattr(engram, "label_for", lookup)
    monkeypatch.setattr(ternary, "chat", lambda *args, **kwargs: "us")
    result = domain_advice.consult("Which time unit means a millionth of a second on a timer?", "t80", None, "")
    assert result["accepted"] and result["label"] == "us"
    assert domain_advice.consult("Walk me through this timer design.", "t80", None, "") is None
    assert looked_up == ["computer_engineering"]


@pytest.mark.parametrize(("question", "expected"), [
    ("What geometric quantity describes the inside of a storage bin?", True),
    ("Identify the appropriate measurement for covering a tabletop.", True),
    ("Design a storage bin with enough volume for all my spare parts.", False),
    ("Explain how different dimensions affect the material cost of a box.", False),
])
def test_label_head_requires_a_request_for_its_decision(question, expected):
    from team.domain_intent import requests_choice
    assert requests_choice(question, "geometry_measure", ["length", "area", "volume"]) == expected
