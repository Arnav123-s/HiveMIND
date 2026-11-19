"""A new repair instruction can rescue an older failure without another model call."""
import json
import os

import pytest

from training.experiments.fieldwork import work as fw
from training.experiments.fieldwork.guest import Guest


def test_batch_revisits_older_public_failure_then_serves_old_and_new_methods(tmp_path, monkeypatch):
    sdk = os.getenv("HIVE_FIELDWORK_WASI")
    if not sdk:
        pytest.skip("set HIVE_FIELDWORK_WASI to exercise the WebAssembly work-order sequence")
    guest = Guest(sdk)
    bank, out = tmp_path / "learned", tmp_path / "course"
    names = ["parcel_adjustment", "score_tick", "meter_step"]
    descriptions = ["Increment the parcel reading by one.", "Advance the contest score by one.",
                    "Return one above the meter reading."]
    specs = []
    for i, (name, text) in enumerate(zip(names, descriptions)):
        specs.append(dict(name=name, task=text, examples=[dict(input=i, output=i + 1)],
                          validation=[dict(input=40 + i, output=41 + i)],
                          jobs=[dict(id="new", input=70 + i)]))
    calls = []

    def propose(task, prefix, prior):
        i = descriptions.index(task.text.split("Current assignment:\n")[-1])
        calls.append((i, prior is not None))
        # These are controlled proposals. Even the second writer fails the first order.
        arg = ["parcels", "points", "meter"][i]
        op = "+" if i and prior else "-"
        return dict(source=f"def solve({arg}):\n    return {arg} {op} 1", usage={})

    results = fw.run_orders(specs, guest, propose, out, bank, rounds=2, repair_budget=1)
    assert calls == [(0, False), (0, True), (1, False), (1, True), (2, False), (2, True)]
    rescued = results[0]
    assert rescued["prior_searches"][0]["candidates_checked"] == 0
    assert rescued["learned_repair"]["support"] == 2
    assert "repair_experience" not in rescued
    assert [row["jobs"][0]["value"] for row in results] == [71, 72, 73]
    assert len(fw.load_bank(bank)) == 3
    # Completed orders resume identically, while the public-only replay was allowed once.
    assert fw.run_orders(specs, guest, None, out, bank, rounds=2, repair_budget=1) == results

    from team import cli, talk
    monkeypatch.setenv("HIVE_BANK", str(bank))
    monkeypatch.setenv("HIVE_FIELDWORK_SDK", sdk)
    monkeypatch.setattr(talk, "speaker", lambda: pytest.fail("a saved invocation contacted a model"))
    for name in names:
        assert cli.main(["--once", f"Run {name} with 102"]) == 0
        reply = talk.reply(f"Run {name} with 103")
        assert reply["saved"]["value"] == 104


def test_resume_uses_original_writer_position_and_feedback(tmp_path):
    from tests.test_fieldwork_versions import Guest, order
    spec = order("Transform a sensor value", [(2, 4)], [(3, 6)], [5])
    recorded = []
    def first(*args):
        recorded.append("first")
        return {"source": "identity", "usage": {}}
    def interrupted(*args):
        raise RuntimeError("interrupted")
    def second(task, prefix, prior):
        assert prior[0] == "identity"
        recorded.append("second")
        return {"source": "double", "usage": {}}

    g = Guest({"identity": lambda x: x, "double": lambda x: x * 2})
    out = tmp_path / "run"
    with pytest.raises(RuntimeError, match="interrupted"):
        fw.work(spec, g, (first, interrupted), out, rounds=2)
    result = fw.work(spec, g, (first, second), out, rounds=2)
    assert recorded == ["first", "second"]
    assert result["jobs"][0]["value"] == 10
    assert json.loads((out / "attempt-2.json").read_text())["writer_parent"] == fw.fingerprint("identity")


def test_waiting_request_can_use_newly_acquired_exact_contract(tmp_path):
    from tests.test_fieldwork_versions import Guest, order, version
    g = Guest({"double": lambda x: x * 2, "wrong": lambda x: 0})
    spec = order("Double the amount", [(2, 4)], [(3, 6)], [5])
    bank, out = tmp_path / "bank", tmp_path / "out"
    assert fw.work(spec, g, None, out, bank)["status"] == "needs_generation"
    version(bank, spec["name"], "Unrelated policy", "wrong", 2)
    assert fw.work(spec, g, None, out, bank)["status"] == "needs_generation"
    assert not g.calls
    version(bank, spec["name"], spec["task"], "double", 2)
    receipt = fw.work(spec, g, None, out, bank)
    assert receipt["jobs"] == [dict(id="job0", value=10)]
    calls = len(g.calls)
    assert fw.work(spec, g, None, out, bank) == receipt and len(g.calls) == calls
