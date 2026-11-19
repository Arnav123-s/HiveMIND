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


@pytest.mark.parametrize(("message", "expected"), [
    ("Order #817: calculate the depot shipping fee for two parcels weighing 199 and 501 grams.", [199, 501]),
    ("Calculate the shipping fee for order 817: parcel weights are 199 g and 501 g.", [199, 501]),
    ("Quote the depot fee for three parcels, 190 g each.", [190, 190, 190]),
    ("Please use our usual depot tariff. I have a 1,250 g box. What's the shipping fee?", [1250]),
    ("Calculate the shipping fee for an empty shipment.", []),
])
def test_shipping_binds_only_the_parcels(message, expected):
    guest = Guest()
    out = saved.answer(message, SHIPPING, guest)
    assert out["input"] == {"grams": expected} and out["status"] == "answered"
    assert guest.calls == 1


@pytest.mark.parametrize("message", [
    "Write a message asking 'What's the depot shipping fee for a 200 g parcel?'",
    "Calculate the shipping fee for order 581.",
    "Calculate the depot shipping fee for 4 parcels of 520 grams.",
    "Calculate the depot shipping fee for two parcels weighing 170 g and one not yet weighed.",
    "Do not calculate the shipping fee for 200 g.",
    "What is the shipping fee for 280 g with a half-price discount?",
    "Calculate the invoice subtotal for invoice 381, lines of 40 and 50 cents.",
    "Calculate the shipping fee for 0 g.",
    "Calculate the shipping fee for 12.5 g.",
    "Calculate the shipping fee for a 3 kg bag.",
])
def test_other_intent_ambiguous_or_invalid_amount_never_calls(message):
    guest = Guest()
    out = saved.answer(message, SHIPPING, guest)
    assert out is None or out["status"] == "missing"
    assert guest.calls == 0


def retain(bank, name, description, source, inputs=None):
    from team.skill_inputs import infer_contract
    row = dict(task=name, description=description, source=source, digest=fw.fingerprint(source),
               public=2, validation=2, parents=[])
    if inputs is not None:
        row["input_contract"] = infer_contract(inputs)
    fw.admit(bank, row)
    return row


def test_any_saved_task_can_take_exact_json_including_root_values(tmp_path):
    source = "def solve(x):\n    return x"
    runner = Guest()
    retain(tmp_path, "label", "Return the supplied label.", source, ["blue"])
    retain(tmp_path, "mirror", "Return the sequence.", source, [[1, 2]])
    retain(tmp_path, "counter", "Return the supplied count.", source, [7])
    for name, arg in [("label", '"CL-019"'), ("mirror", "[3, 3, 4]"), ("counter", "-3")]:
        message = f"Run {name} with {arg}"
        assert saved.explicit_request(message)
        out = saved.answer(message, tmp_path, runner)
        assert out["input"] == out["value"] == json.loads(arg)
    assert saved.answer("Run counter with true", tmp_path, runner)["status"] == "missing"
    assert saved.answer('Run label with 17', tmp_path, runner)["status"] == "missing"
    assert saved.answer("Write instructions showing how to run counter with 2", tmp_path, runner) is None
    assert runner.calls == 3


def test_generic_object_fields_and_json_types_are_exact(tmp_path):
    runner = Guest()
    retain(tmp_path, "ladder", "Calculate the ladder bill.", "def solve(x):\n    return x['rungs']",
           [{"rungs": 3, "paint": False}, {"rungs": 9}])
    assert saved.answer("Calculate the ladder bill for order 52.", tmp_path, runner) is None
    assert saved.answer('Run ladder with {"rungs": 5}', tmp_path, runner)["value"] == 5
    for bad in ('{"rungs": true}', '{"rungs": "5"}', '{"rungs": 5.0}', '{"rungs": 5, "paint": 0}',
                '{"rungs": 5, "grams": 5}', '{"rungs": 3, "rungs": 5}', '{"rungs": Infinity}',
                '{"rungs": 1e999}', '{"paint": true}', '{"rungs": 5} and write a receipt', '[]', ''):
        assert saved.answer("Run ladder with " + bad, tmp_path, runner)["status"] == "missing"
    assert runner.calls == 1


def test_exact_name_requires_contract_choice_and_keeps_all_versions(tmp_path):
    runner = Guest()
    source = "def solve(x):\n    return x['amount'] + 1"
    a = retain(tmp_path, "due", "Weekday fare.", source)
    retain(tmp_path, "due", "Weekend fare.", source.replace("+ 1", "+ 3"))
    retain(tmp_path, "due", "Weekday fare.", source.replace("+ 1", "+ 2"))
    ambiguous = saved.answer('Run due with {"amount": 8}', tmp_path, runner)
    cid = fw.contract_id(a)[:12]
    assert ambiguous["status"] == "missing" and cid in ambiguous["text"] and runner.calls == 0
    scoped = saved.answer(f'Run due@{cid} with {{"amount": 8}}', tmp_path, runner)
    assert scoped["status"] == "ambiguous" and len(scoped["methods"]) == 2 and runner.calls == 2


@pytest.mark.parametrize("data", ['{"grams": [true]}', '{"grams": [0]}', '{"grams": [1.0]}',
                                   '{"grams": [5], "order": 7}', '{"GRAMS": [4]}', '{"grams": "400"}'])
def test_legacy_shipping_json_requires_positive_whole_weights(data):
    runner = Guest()
    assert saved.answer("Run depot_shipping_fee with " + data, SHIPPING, runner)["status"] == "missing"
    assert runner.calls == 0


def test_natural_json_is_the_whole_input_and_preserves_keys():
    runner = Guest()
    out = saved.answer('Compute the depot shipping fee from this exact input: {"grams": [3, 501]}.', SHIPPING, runner)
    assert out["value"] == 520 and out["input"] == {"grams": [3, 501]}
    for message in ('Compute the depot shipping fee from this exact input: {"GRAMS":[25]}.',
                    'Compute the depot shipping fee from this exact input: {"grams":[3]} plus another parcel.',
                    'Compute the shipping fee on this empty shipment: {"grams": [4]}.'):
        out = saved.answer(message, SHIPPING, runner)
        assert out is None or out["status"] == "missing"
    assert runner.calls == 1


def test_explicit_named_method_reports_absent_runtime_without_model(monkeypatch):
    monkeypatch.setattr(saved, "guest", lambda: None)
    result = saved.answer('Run depot_shipping_fee with {"grams": [2]}', SHIPPING)
    assert result["status"] == "missing" and "runtime" in result["text"]


@pytest.mark.parametrize("text, arguments", [
    ("How much to ship two parcels at the depot? The first weighs 202 grams; the other is 301 grams.", [202, 301]),
    ("Parcel weights (grams): 50,500,500. What will the depot bill me for sending them together?", [50, 500, 500]),
    ("Quote the shipping fee for a pair of 400 g packets and a 50 g box.", [400, 400, 50]),
    ("Quote the shipping fee for 3 x 500 grams plus 18 g.", [500, 500, 500, 18]),
    ("Quote the shipping fee for a parcel weighing 12 and 30 grams.", None),
    ("Quote the shipping fee for a parcel weighing 12- g.", None),
    ("Quote the shipping fee for three parcels. The first is 190 g; the second is 27 g.", None),
])
def test_weight_lists_and_multiplicity(text, arguments):
    guest = Guest()
    out = saved.answer(text, SHIPPING, guest)
    if arguments is None:
        assert out is None or out["status"] == "missing"
        assert guest.calls == 0
    else:
        assert out["input"] == {"grams": arguments} and guest.calls == 1


def test_finite_and_typed_array_inputs_from_new_work_orders(tmp_path):
    runner = Guest()
    retain(tmp_path, "balance", "Return the integer balance.", "def solve(x):\n    return sum(x)", [[1, 4]])
    retain(tmp_path, "package", "Return values.", "def solve(x):\n    return x",
           [{"labels": ["a", "b"], "discount": 0.75}])
    assert saved.answer("Run balance with [false, 3]", tmp_path, runner)["status"] == "missing"
    assert saved.answer('Run package with {"labels":[3],"discount":1}', tmp_path, runner)["status"] == "missing"
    assert saved.answer('Run package with {"labels":[],"discount":1}', tmp_path, runner)["status"] == "answered"
    assert runner.calls == 1


def test_bad_saved_input_metadata_withholds_execution(tmp_path):
    runner = Guest()
    row = retain(tmp_path, "charge", "Return the supplied value.", "def solve(x):\n    return x", [2])
    path = tmp_path / (row["digest"] + ".json")
    row["input_contract"] = {"properties": {"num": "integer"}, "kinds": ["object"]}
    path.write_text(json.dumps(row))
    result = saved.answer('Run charge with {"num": 5}', tmp_path, runner)
    assert result["status"] == "missing" and runner.calls == 0
