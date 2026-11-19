import json

import pytest

from team import domain_advice, engram, solo, talk, ternary, water_phase


OBSERVE = "Which phase of pure water would I observe at 24 C and one atmosphere?"


@pytest.mark.parametrize("question,expected", [
    (OBSERVE, "liquid"),
    ("Pure water is at -15 C and 1 atm. Identify its state of matter.", "solid"),
    ("Is a sample of pure water at 150 C and 1 atm solid, liquid or gas?", "gas"),
    ("What phase would you expect for a sample of pure water at 22 C and one atmosphere?", "liquid"),
    (OBSERVE.replace("24 C", "100 C"), None),
    (OBSERVE.replace("pure water", "salt water"), None),
    ("Which phase is copper in? Pure water at 24 C and one atmosphere is nearby.", None),
    ("Which phase is it? Pure water at 24 C and one atmosphere is nearby.", None),
    ("Which phase of copper is near pure water at 24 C and one atmosphere?", None),
    ("Write a program to illustrate the state of pure water at 24 C and one atmosphere.", None),
])
def test_check_is_bound_to_the_subject_and_known_measurement(question, expected):
    assert water_phase.standalone_phase(question) is None
    assert water_phase.output_check_phase(question) == expected
    assert water_phase.output_check_phase(question, ["Earlier discussion"]) is None


def ordinary(monkeypatch, way):
    monkeypatch.setenv("HIVE_SIGNALS", "0")
    monkeypatch.setenv("HIVE_BANK", "off")
    monkeypatch.setenv("HIVE_ENGRAMS", "0")
    monkeypatch.setattr(domain_advice, "consult", lambda *args, **kw: None)
    monkeypatch.setattr(talk, "route", lambda base, msg, history: (way, [*history, {"role": "user", "content": msg}]))


def test_direct_chat_withholds_only_a_complete_contradictory_output(monkeypatch):
    ordinary(monkeypatch, "talk")
    monkeypatch.setattr(engram, "for_request", lambda *args, **kw: ("edit",))
    for proposed, request, history, reject in (
        ("The sample would be a gas.", OBSERVE, [], True),
        ("It is solid.", OBSERVE + " Include a source for your answer.", [], True),
        ("The water is liquid.", OBSERVE, [], False),
        ("Liquid. My source is NIST.", OBSERVE + " Include a source for your answer.", [], False),
        ("def phase(): return 'gas'", OBSERVE + " Also include Python code.", [], False),
        ("It is solid.", OBSERVE, [{"role": "user", "content": "Use our lab's custom terminology."}], False),
    ):
        monkeypatch.setattr(ternary, "chat", lambda *args, **kw: proposed)
        out = talk.reply(request, history, base="t80")
        if reject:
            assert out["text"] == water_phase.WITHHELD and out["agreed"] is False
            assert out["water_phase_check"]["model_answer"] == proposed
            assert out["engrams"][0]["stage"] == "answer_attempt"
        else:
            assert out["text"] == proposed and "water_phase_check" not in out


@pytest.mark.parametrize("answers,accepted,rejected", [
    (["gas", "gas", "The sample is ice."], [], [1, 2, 3]),
    (["gas", "liquid", "liquid"], [2, 3], [1]),
])
def test_workers_and_training_log_agree_on_which_claims_were_rejected(tmp_path, monkeypatch, answers, accepted, rejected):
    ordinary(monkeypatch, "work")
    def member(task, n, board, guard, work, temp, who, also):
        work.mkdir(parents=True, exist_ok=True)
        return dict(answer=answers[n - 1], program="pass", who=who)
    monkeypatch.setattr(solo, "member", member)
    monkeypatch.setattr(solo, "keep", lambda *args: None)
    out = solo.first(OBSERVE, tmp_path, members=2)
    record = json.loads((tmp_path / "members/members.json").read_text())
    assert record["water_phase_check"]["rejected_members"] == rejected
    assert out["agreed"] is bool(accepted) and record["agreeing"] == accepted
    if not accepted:
        assert out["report"].strip() == water_phase.WITHHELD
        # The normal user interface must carry that decision without sending it back for a rewrite.
        monkeypatch.setattr(solo, "first", lambda *args, **kw: out)
        monkeypatch.setattr(ternary, "chat", lambda *args, **kw: pytest.fail("rewrote a withheld worker report"))
        delivered = talk.reply(OBSERVE, base="t80", run_dir=tmp_path)
        assert not delivered["agreed"] and delivered["text"] == water_phase.WITHHELD
        assert delivered["water_phase_check"]["rejected_members"] == rejected
