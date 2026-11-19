"""A local fieldwork bank can serve people without a model and switch between checked conventions."""

import json
import os
import subprocess
import sys
from types import SimpleNamespace

import pytest

from team import cli, config, saved, talk
from training.experiments.fieldwork import work as fw
from test_talk_saved import CASES, SHIPPING, Guest, invoice_bank, retain


@pytest.mark.parametrize("request_text", [
    'Run depot_shipping_fee@deadbeefdead with {"grams":[999]}',
    'Run depot_shipping_fee@old with {"grams":[999]}',
    'Run depot_shipping_fee@ with {"grams":[999]}',
    'Run the saved method no_worker with 7',
    'Run missing_worker with {"count":7}',
    'Run ticker with {"count":7}',
])
def test_absolute_method_requests_report_a_miss_without_a_model(request_text, monkeypatch, capsys):
    monkeypatch.setenv("HIVE_BANK", str(SHIPPING))
    monkeypatch.setattr(talk, "speaker", lambda: pytest.fail("looked for a model"))
    assert cli.main(["--once", request_text]) == 1
    reply = capsys.readouterr().out
    assert "unavailable" in reply or "no saved method" in reply
    if "depot_shipping_fee@" in request_text:
        assert "Available contracts" in reply


def test_known_natural_request_precedes_model_but_unrelated_commands_still_go_to_service(monkeypatch, capsys):
    monkeypatch.setenv("HIVE_BANK", str(SHIPPING))
    monkeypatch.delenv("HIVE_ROLES", raising=False)
    monkeypatch.setattr(saved, "guest", Guest)
    monkeypatch.setattr(talk, "speaker", lambda: pytest.fail("looked for a model"))
    assert cli.main(["--once", "Calculate the shipping fee for parcels of 25 g and 999 g."]) == 0
    assert capsys.readouterr().out.startswith("520\n")
    monkeypatch.setattr(talk, "speaker", lambda: None)
    monkeypatch.setattr(cli, "service_up", lambda: True)
    received = []
    monkeypatch.setattr(cli, "say_remote", lambda msg, history, rounds: received.append(msg) or "done")
    assert cli.main(["--once", "Use caution with wet equipment"]) == 0
    assert received == ["Use caution with wet equipment"]


def test_interactive_without_a_body_serves_each_turn_and_keeps_remote_history(monkeypatch, capsys):
    monkeypatch.setenv("HIVE_BANK", str(SHIPPING))
    monkeypatch.delenv("HIVE_ROLES", raising=False)
    monkeypatch.setattr(talk, "speaker", lambda: None)
    monkeypatch.setattr(saved, "guest", Guest)
    monkeypatch.setattr(cli.sys, "stdin", SimpleNamespace(isatty=lambda: True))
    remote = []
    monkeypatch.setattr(cli, "service_up", lambda: True)
    monkeypatch.setattr(cli, "say_remote", lambda msg, history, rounds: remote.append((msg, history)) or "done")
    named = 'Run depot_shipping_fee with {"grams":[700]}'
    turns = iter([named, "What time is it?", "quit"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(turns))
    assert cli.main([]) == 0
    out = capsys.readouterr().out
    assert "Saved methods: depot_shipping_fee" in out and "hive> 430" in out
    assert remote[0][0] == "What time is it?" and remote[0][1][0] == ("user", named)
    assert remote[0][1][1][1].startswith("430\n")
    turns = iter([named, "Which week is it?", "exit"])
    assert talk.main([]) == 0
    out = capsys.readouterr().out
    assert "hive> 430" in out and "No saved method fits" in out


def test_no_runtime_or_body_gets_setup_directions(monkeypatch, capsys):
    monkeypatch.setenv("HIVE_BANK", str(SHIPPING))
    monkeypatch.setattr(talk, "speaker", lambda: None)
    monkeypatch.setattr(saved, "guest", lambda: None)
    assert cli.main(["--once", "Calculate the shipping fee for parcels of 25 g."]) == 1
    assert "python scripts/setup_fieldwork.py" in capsys.readouterr().out


def test_user_can_choose_invoice_rounding_in_both_directions(tmp_path):
    bank, runner = invoice_bank(tmp_path), Guest()
    for amounts, convention, due, version in [
        ("13, 13 and 13", "per-line", 3, "per_line"),
        ("12 and 12", "invoice-total", 1, "per_invoice"),
        ("9 and 9", "per-line", 0, "per_line"),
    ]:
        out = saved.answer(f"Calculate the invoice tax for lines of {amounts} cents using {convention} rounding.", bank, runner)
        assert out["value"] == due and out["methods"] == [fw.fingerprint(CASES["programs"][version])]
        assert out["convention_check"]["convention"] == convention
        assert "11, 11" in out["text"]
    assert saved.answer("Calculate the invoice tax for lines of 12 and 12 cents.", bank, runner)["status"] == "ambiguous"
    assert saved.answer("Calculate the invoice tax for lines of 12 and 12 cents without per-line rounding.", bank, runner) is None


def test_wrong_lone_shipping_version_is_withheld_and_both_work_on_fresh_inputs(tmp_path):
    pooled = "def solve(x):\n    return 250 + 90 * ((sum(x['grams']) + 499) // 500) if x['grams'] else 0"
    bank = tmp_path / "bank"
    retain(bank, *saved.SHIPPING, pooled)
    runner = Guest()
    per_parcel = "Calculate the shipping fee for parcels of 250 g and 250 g with our usual per-parcel pricing."
    assert saved.answer(per_parcel, bank, runner)["status"] == "missing"
    row, = fw.load_bank(SHIPPING)
    fw.admit(bank, row)
    assert saved.answer(per_parcel, bank, runner)["value"] == 430
    pooled_request = "Calculate the shipping fee for parcels of 502 g and 506 g using pooled rounding."
    out = saved.answer(pooled_request, bank, runner)
    assert out["value"] == 520 and out["methods"] == [fw.fingerprint(pooled)]
    assert saved.answer(per_parcel.replace("250 g and 250 g", "140 g and 194 g"), bank, runner)["value"] == 430
    untyped = "Calculate the shipping fee for parcels of 140 g and 194 g."
    assert saved.answer(untyped, bank, runner)["status"] == "ambiguous"


def test_legacy_two_phase_work_order_only_accepts_the_public_shape_for_its_phase():
    folder = config.ROOT / "training/reports/rule_lab/fieldwork"
    spec = json.loads((folder / "geology-order.json").read_text())
    rows = fw.load_bank(folder / "bank")
    member, = [row for row in rows if row["task"] == spec["name"]]
    versions, contract = [member], (member["task"], member["description"])
    for example in spec["examples"]:
        value = example["input"]
        assert saved._json_input(json.dumps(value), versions, contract) == (value, None)
    bad = [
        {"phase": "intake"},
        {"phase": "intake", "events": [["ticket", 1]]},
        {"phase": "revise", "snapshot": {}, "exclude": "Cove", "minimum": 1},
        {"phase": "revise", "events": []},
        {"phase": ["intake"], "events": []},
        {"phase": "unrecognized", "events": []},
    ]
    runner = Guest()
    for value in bad:
        response = saved.answer("Run geology_order with " + json.dumps(value), folder / "bank", runner)
        assert response["status"] == "missing"
    assert runner.calls == 0
    assert not saved._archived_geology_phases((member["task"], member["description"] + " New version."))



def test_legacy_geology_worker_serves_a_new_snapshot_across_cli_processes(tmp_path):
    sdk = os.environ.get("HIVE_FIELDWORK_WASI")
    if not sdk:
        pytest.skip("set HIVE_FIELDWORK_WASI to exercise the two-phase worker")
    env = os.environ | {
        "HIVE_PYTHON": sys.executable, "HIVE_FIELDWORK_SDK": sdk,
        "HIVE_BANK": str(config.ROOT / "training/reports/rule_lab/fieldwork/bank"),
        "HIVE_TERNARY_HOME": str(tmp_path / "no-model"), "HIVE_ADAPTERS_HOME": str(tmp_path / "no-adapters"),
    }
    def invoke(value):
        message = "Run geology_order with " + json.dumps(value)
        result = subprocess.run([str(config.ROOT / "hive"), "--once", message], check=True,
                                capture_output=True, text=True, timeout=90, env=env)
        return json.loads(result.stdout.splitlines()[0])

    events = [["a", 1, "Bay", 5, "ok"], ["b", 0, "Sky", 8, "ok"], ["c", 2, "Bay", 9, "ok"],
              ["b", 0, "Hill", 3, "ok"], ["a", 0, "Sky", 20, "ok"]]
    snapshot = invoke({"phase": "intake", "events": events})
    assert snapshot == {"kept": [["a", 1, "Bay", 5], ["c", 2, "Bay", 9]], "conflicts": ["b"]}
    files = invoke({"phase": "revise", "snapshot": snapshot, "exclude": "Hill", "minimum": 1})
    assert files["summary.csv"] == "zone,count,grams\nBay,2,14\n"
    assert json.loads(files["audit.json"]) == {"kept_count": 2, "conflicts": ["b"]}
