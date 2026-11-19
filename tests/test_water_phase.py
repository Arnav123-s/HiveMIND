import pytest

from team import engram, talk, ternary
from team.water_phase import equilibrium_phase


@pytest.mark.parametrize(("message", "expected"), [
    ("Pure water at 1 atm and −23 °C", "solid"),
    ("At one atmosphere the pure water is at minus 8 degrees Celsius.", "solid"),
    ("Pure water at negative twenty-three degrees Celsius and standard atmospheric pressure", "solid"),
    ("Water at 72 C and 1 atm", "liquid"),
    ("Pure water at +123°C and 1.0 atmosphere", "gas"),
])
def test_unambiguous_equilibrium_states(message, expected):
    assert equilibrium_phase(message) == expected


@pytest.mark.parametrize("conditions", [
    "pure water at -0.1°C and 1 atm", "water at 100.09 C and 1 atm", "water at 99.9 C and 1 atm",
    "water at 27 C and 0.1 atm", "water at 45 C near sea level", "water at 27 C at 1 atm or under vacuum",
    "water at 108 C and a gauge pressure of 1 atm", "water at 108 C and twice standard atmospheric pressure",
    "salt water at -7 C and 1 atm", "water with glycerol at 27 C and 1 atm", "supercooled water at -4 C and 1 atm",
    "water at thirty or forty degrees Celsius and one atmosphere", "water at one hundred ten Celsius and one atmosphere",
    "water at 30–40 C and 1 atm", "water between 20 and 30 C at 1 atm", "water above 20 C at 1 atm",
    "water at 21 C and 1 atm but not at equilibrium", "water at 27°F and 1 atm", "water at 3000 C and 1 atm",
])
def test_scoped_exercise_declines_other_conditions(conditions):
    assert equilibrium_phase(conditions) is None


def test_registered_label_head_checks_same_scope_before_applying_weights(tmp_path, monkeypatch):
    monkeypatch.setattr(ternary, "ENGRAMS", tmp_path)
    monkeypatch.delenv("HIVE_ENGRAMS", raising=False)
    row = dict(name="phase_v2", dna="t80", domain="physical_science", task="Water phase", form="label",
               skill_id="water_phase", verified=True, instruction="Choose the phase.",
               labels=["solid", "liquid", "gas"], cues=["water"])
    engram.update_index(lambda records: [row], home=tmp_path)
    (tmp_path / "t80+phase_v2.gguf").touch()
    def selected(conditions):
        return engram.for_request("Choose solid, liquid, or gas for " + conditions, "t80", domain="physical_science")
    assert selected("pure water at 72 °C and 1 atm") == ("phase_v2",)
    assert selected("pure water at minus twenty °C and one atmosphere") == ("phase_v2",)
    assert selected("pure water at 100 °C and 1 atm") == ()
    assert selected("pure water at 72 °C and either 1 atm or 3 atm") == ()
    assert selected("salt water at 72 °C and 1 atm") == ()

    monkeypatch.setenv("HIVE_SIGNALS", "0")
    monkeypatch.setenv("HIVE_BANK", "off")
    monkeypatch.setattr(talk, "route", lambda base, msg, history: ("talk", [{"role":"user", "content": msg}]))
    def fake_native(base, messages, **options):
        if options.get("also"):
            return "Gas."
        assert "equilibrium check" in messages[0]["content"] and "gives liquid" in messages[0]["content"]
        return "The water is liquid."
    monkeypatch.setattr(ternary, "chat", fake_native)
    out = talk.reply("At one atmosphere, what phase is pure water at 72 C?", base="t80")
    receipt = out["engram_advice"]
    assert out["text"] == "The water is liquid." and receipt["model_reply"] == "Gas."
    assert receipt["checked_phase"] == "liquid" and not receipt["accepted"]
