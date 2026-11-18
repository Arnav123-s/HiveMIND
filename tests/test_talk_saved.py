"""Chat answers from a saved, checked fieldwork method (HIVE_BANK), with no model call."""
import json
from pathlib import Path

import pytest

from team import saved, solo, talk, ternary
from training.experiments.fieldwork import work as fw

ROOT = Path(__file__).resolve().parent.parent
SHIPPING = ROOT / "training/reports/retained-skills/shipping/bank"
CASES = json.loads((ROOT / "training/reports/retained-skills/work-order-cases.json").read_text())


class Guest:
    """Runs the saved sources in-process, the way the WebAssembly guest runs them."""

    def __init__(self):
        self.calls = 0

    def run(self, program, inputs, fuel=None):
        self.calls += 1
        scope = {}
        exec(program, scope)
        return [{"value": scope["solve"](x)} for x in inputs], 0, 0


@pytest.fixture
def hive(monkeypatch):
    calls = {"model": 0, "solo": 0}
    runner = Guest()

    def chat(*a, **k):
        calls["model"] += 1
        return "It is 409.5."

    def first(task, home, *a, **k):
        calls["solo"] += 1
        return {"report": "409.5", "agreed": True, "files": []}

    monkeypatch.setattr(ternary, "chat", chat)
    monkeypatch.setattr(solo, "first", first)
    monkeypatch.setattr(saved, "guest", lambda: runner)
    return calls, runner


def ask(message, tmp_path):
    return talk.reply(message, base="dna", run_dir=str(tmp_path / "run"))


def test_shipping_fee_answered_from_saved_method(hive, monkeypatch, tmp_path):
    calls, runner = hive
    monkeypatch.setenv("HIVE_BANK", str(SHIPPING))
    out = ask("Calculate the shipping fee for parcels of 25 g and 999 g.", tmp_path)
    (row,) = fw.load_bank(SHIPPING)
    scope = {}
    exec(row["source"], scope)
    expected = scope["solve"]({"grams": [25, 999]})
    assert expected == 250 + 90 + 2 * 90
    assert out["saved"]["status"] == "answered" and out["saved"]["value"] == expected
    assert out["text"].startswith(str(expected)) and row["digest"][:12] in out["text"] and "depot_shipping_fee" in out["text"]
    assert calls == {"model": 0, "solo": 0} and runner.calls == 1
    assert out["agreed"] and out["worked"]


def invoice_bank(tmp_path):
    bank = tmp_path / "invoice-bank"
    for source in (CASES["programs"]["per_line"], CASES["programs"]["per_invoice"]):
        fw.admit(bank, dict(task=CASES["name"], description=CASES["description"], source=source,
                            digest=fw.fingerprint(source), public=2, validation=2, parents=[]))
    return bank


def test_disagreeing_invoice_methods_name_the_bill(hive, monkeypatch, tmp_path):
    calls, _ = hive
    monkeypatch.setenv("HIVE_BANK", str(invoice_bank(tmp_path)))
    out = ask("Calculate the invoice tax for lines of 10, 10 and 10 cents.", tmp_path)
    assert out["saved"]["status"] == "ambiguous" and not out["agreed"]
    assert '{"lines": [10, 10, 10]}' in out["text"] and ("2 or 3" in out["text"] or "3 or 2" in out["text"]) and "disagree" in out["text"]
    assert calls == {"model": 0, "solo": 0}
    # on a bill where both conventions agree the amount is released
    out = ask("Calculate the invoice tax for lines of 20 and 40 cents.", tmp_path / "b")
    assert out["saved"]["status"] == "answered" and out["saved"]["value"] == 3 and "2 saved methods" in out["text"]


def test_missing_inputs_named(hive, monkeypatch, tmp_path):
    calls, runner = hive
    monkeypatch.setenv("HIVE_BANK", str(SHIPPING))
    out = ask("Calculate the shipping fee for my parcels.", tmp_path)
    assert out["saved"]["status"] == "missing" and "grams" in out["text"] and runner.calls == 0
    assert calls == {"model": 0, "solo": 0}


def test_unrelated_message_falls_through_unchanged(hive, monkeypatch, tmp_path):
    calls, runner = hive
    monkeypatch.delenv("HIVE_BANK", raising=False)
    before = ask("Calculate 17.5% of 2340.", tmp_path / "off")
    monkeypatch.setenv("HIVE_BANK", str(SHIPPING))
    after = ask("Calculate 17.5% of 2340.", tmp_path / "on")
    for out in (before, after):
        out.pop("seconds"), out.pop("dir"), out.pop("task")
    assert before == after and "saved" not in after and after["text"] == "It is 409.5."
    assert calls == {"model": 2, "solo": 2} and runner.calls == 0


def test_off_without_bank_or_runtime(hive, monkeypatch, tmp_path):
    calls, _ = hive
    monkeypatch.delenv("HIVE_BANK", raising=False)
    out = ask("Calculate the shipping fee for parcels of 25 g and 999 g.", tmp_path / "a")
    assert "saved" not in out and calls["solo"] == 1
    monkeypatch.setenv("HIVE_BANK", str(SHIPPING))
    monkeypatch.setattr(saved, "guest", lambda: None)
    out = ask("Calculate the shipping fee for parcels of 25 g and 999 g.", tmp_path / "b")
    assert "saved" not in out and calls["solo"] == 2
