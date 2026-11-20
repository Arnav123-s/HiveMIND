"""Guided selection and checked input collection through the local hive entrypoint."""

import io
import os
from pathlib import Path
import subprocess
import sys

import pytest

from team import cli, saved, skill_inputs
from training.experiments.fieldwork import work as fw

ROOT = Path(__file__).resolve().parent.parent
BANK = ROOT / "training/reports/verified-learning/live/example-bank"


class Terminal(io.StringIO):
    def isatty(self):
        return True


class Echo:
    def run(self, source, values, fuel):
        return [{"value": value if source == "first" else "different"} for value in values], 0, 0


def record(bank, description="Keep the measured input", source="first", sample=None):
    row = dict(task="measure", description=description, source=source, digest=fw.fingerprint(source),
               public=2, validation=3, parents=[])
    if sample is not None:
        row["input_contract"] = skill_inputs.infer_contract(sample)
    fw.admit(bank, row)
    return row


def test_piped_listing_neither_prompts_nor_runs_a_method(monkeypatch, capsys):
    monkeypatch.setenv("HIVE_BANK", str(BANK))
    stdin = Terminal("1\n")
    monkeypatch.setattr(sys, "stdin", stdin)
    monkeypatch.setattr(saved, "guest", lambda: pytest.fail("listing must not run a guest"))
    assert cli.main(["skills"]) == 0
    output = capsys.readouterr()
    lines = output.out.splitlines()
    assert len(lines) == 2 and "quote_spread@" in lines[0] and "transit_tickets@" in lines[1]
    assert "cents" in lines[0] and stdin.tell() == 0 and not output.err


def test_interactive_number_and_typed_fields_reuse_saved_answer(tmp_path, monkeypatch):
    bank = tmp_path / "bank"
    record(bank, sample=[{"run_times": [3], "label": "trial", "count": 4}, {"run_times": [5], "count": 2}])
    monkeypatch.setenv("HIVE_BANK", str(bank))
    monkeypatch.setattr(saved, "guest", lambda: Echo())
    monkeypatch.setattr(sys, "stdin", Terminal("1\n9\n\n4, 7, -3\n"))
    stdout, stderr = Terminal(), Terminal()
    monkeypatch.setattr(sys, "stdout", stdout)
    monkeypatch.setattr(sys, "stderr", stderr)
    assert cli.main(["skills"]) == 0
    assert "1. measure@" in stdout.getvalue() and '"run_times": [4, 7, -3]' in stdout.getvalue()
    assert '"count": 9' in stdout.getvalue() and "with no model call" in stdout.getvalue()
    assert "Choose a method by number" in stderr.getvalue() and "Run times" in stderr.getvalue()


def test_legacy_shape_preserves_strict_json_and_contract_selection(tmp_path, monkeypatch, capsys):
    bank = tmp_path / "bank"
    first = record(bank)
    record(bank, description="A different meaning", source="second")
    monkeypatch.setenv("HIVE_BANK", str(bank))
    monkeypatch.setattr(saved, "guest", lambda: Echo())
    assert cli.main(["skills", "measure"]) == 1
    assert "measure@" in capsys.readouterr().err
    name = "measure@" + fw.contract_id(first)[:12]
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"q":1,"q":2}\n'))
    assert cli.main(["skills", name]) == 1
    assert "please give me" in capsys.readouterr().out
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"q":2}\n'))
    assert cli.main(["skills", name]) == 0
    assert '"q": 2' in capsys.readouterr().out


def test_disagreement_off_and_unknown_never_invoke_the_model(tmp_path, monkeypatch, capsys):
    bank = tmp_path / "bank"
    for source in ("first", "second"):
        record(bank, source=source, sample=[[3, 6]])
    monkeypatch.setenv("HIVE_BANK", str(bank))
    monkeypatch.setattr(saved, "guest", lambda: Echo())
    monkeypatch.setattr(sys, "stdin", io.StringIO("3,6\n"))
    assert cli.main(["skills", "measure"]) == 1 and "disagree" in capsys.readouterr().out
    assert cli.main(["skills", "unknown"]) == 1 and "No saved method" in capsys.readouterr().err
    monkeypatch.setenv("HIVE_BANK", "off")
    assert cli.main(["skills", "measure"]) == 1 and "disabled" in capsys.readouterr().err


def test_real_cli_turns_an_ordinary_price_list_into_a_checked_quote(tmp_path):
    sdk = os.environ.get("HIVE_FIELDWORK_WASI")
    if not sdk:
        pytest.skip("set HIVE_FIELDWORK_WASI to use the real checked method")
    pytest.importorskip("wasmtime")
    env = {**os.environ, "HIVE_BANK": str(BANK), "HIVE_PYTHON": sys.executable, "HIVE_FIELDWORK_SDK": sdk}
    proc = subprocess.run([str(ROOT / "hive"), "skills", "quote_spread"], input="250, 180, 220\n",
                          cwd=tmp_path, env=env, capture_output=True, text=True, check=True)
    assert proc.stdout.splitlines()[0] == "70" and "with no model call" in proc.stdout
    assert "Quotes" in proc.stderr and not list(tmp_path.iterdir())
