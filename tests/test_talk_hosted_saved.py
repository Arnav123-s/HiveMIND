"""The hosted thread can run a registered method before fetching any model."""

import json
import os
from pathlib import Path
import subprocess

import pytest
import yaml

from team import saved, talk


ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / "training/reports/verified-learning/live/example-bank"
FLOW = yaml.safe_load((ROOT / ".github/workflows/talk.yml").read_text())["jobs"]["answer"]["steps"]
STEP = next(step for step in FLOW if step.get("id") == "saved")


def thread(folder, message):
    path = folder / "thread.json"
    path.write_text(json.dumps({"name": "owner", "messages": [{"role": "user", "content": message}]}))
    return path


def test_workflow_gates_each_model_download_and_reply_step_after_saved_attempt():
    saved_index = FLOW.index(STEP)
    body, setup, model = FLOW[saved_index + 1:saved_index + 4]
    assert "grow_record.py fetch" in body["run"] and setup["uses"] == "./.github/actions/hive"
    assert "python -m team.talk --thread" in model["run"] and model["env"]["HIVE_BANK"] == "off"
    assert all(step["if"] == "steps.saved.outputs.answered != 'true'" for step in (body, setup, model))
    assert STEP["continue-on-error"] and "vars.HIVE_BANK" in STEP["env"]["HIVE_BANK"]
    assert BANK.relative_to(ROOT).as_posix() in STEP["env"]["HIVE_BANK"]
    assert 'python="$RUNNER_TEMP/hive-fieldwork/bin/python"' in STEP["run"]
    assert '"$python" scripts/setup_fieldwork.py' in STEP["run"] and '"$python" -m team.talk' in STEP["run"]


@pytest.mark.parametrize(("bank", "message"), [
    (str(BANK), "Hello, please tell me a story."),
    ("off", 'Run the saved method quote_spread with {"quotes":[80,65]}'),
])
def test_workflow_shell_falls_through_without_setting_up_wasi(tmp_path, bank, message):
    thread(tmp_path, message)
    output = tmp_path / "outputs"
    output.touch()
    env = {**os.environ, "HIVE_BANK": bank, "HIVE_FIELDWORK_SDK": str(tmp_path / "not-installed"),
           "PYTHONPATH": str(ROOT), "RUNNER_TEMP": str(tmp_path), "GITHUB_OUTPUT": str(output),
           "GITHUB_STEP_SUMMARY": str(tmp_path / "summary")}
    subprocess.run(["bash", "-eo", "pipefail", "-c", STEP["run"]], cwd=tmp_path, env=env, check=True)
    assert output.read_text() == "" and not (tmp_path / "reply.md").exists()
    assert not (tmp_path / "hive-fieldwork").exists()


def test_unavailable_sdk_is_requested_only_after_the_input_is_accepted(tmp_path, monkeypatch):
    monkeypatch.setenv("HIVE_BANK", str(BANK))
    monkeypatch.setattr(saved, "guest", lambda: None)
    output = tmp_path / "reply.md"
    for message, expected in [('Run quote_spread with {"quotes":[80,65]}', 4),
                              ('Run marathon with 1', 3),
                              ('Run quote_spread with {}', 0)]:
        argv = ["--thread", str(thread(tmp_path, message)), "--saved-only", "--out", str(output)]
        assert talk.main(argv) == expected
        assert output.exists() == (expected == 0)
    assert "quotes" in output.read_text() and "Saved method · missing" in output.read_text()


def test_normal_thread_still_sends_an_unmatched_request_to_the_model(tmp_path, monkeypatch):
    message = "Tell me a short story"
    argv = ["--thread", str(thread(tmp_path, message)), "--out", str(tmp_path / "reply.md")]
    monkeypatch.setenv("HIVE_BANK", str(BANK))
    calls = []
    def ordinary(latest, history, name, *args, **kwargs):
        calls.append((latest, history, name))
        return dict(worked=False, agreed=False, seconds=1, text="The story begins.")
    monkeypatch.setattr(talk, "reply", ordinary)
    assert talk.main(argv + ["--saved-only"]) == 3
    assert not calls and not (tmp_path / "reply.md").exists()
    assert talk.main(argv) == 0 and calls == [(message, [], "owner")]
    assert "Answered directly" in (tmp_path / "reply.md").read_text()


@pytest.mark.parametrize(("message", "answer"), [
    ('Run quote_spread with {"quotes":[250,180,220]}', 70),
    ('Run transit_tickets with {"minutes":[51,0,49,50]}', 2),
])
def test_real_guest_answers_registered_hosted_methods(tmp_path, monkeypatch, message, answer):
    sdk = os.environ.get("HIVE_FIELDWORK_WASI")
    if not sdk:
        pytest.skip("set HIVE_FIELDWORK_WASI to use the real guest")
    pytest.importorskip("wasmtime")
    monkeypatch.setenv("HIVE_FIELDWORK_SDK", sdk)
    monkeypatch.setenv("HIVE_BANK", str(BANK))
    output = tmp_path / "reply.md"
    assert talk.main(["--thread", str(thread(tmp_path, message)), "--saved-only", "--out", str(output)]) == 0
    text = output.read_text()
    assert text.splitlines()[0] == str(answer) and "Saved method · answered" in text


def test_ordinary_cli_reports_an_unloadable_wasi_guest(tmp_path, monkeypatch, capsys):
    pytest.importorskip("wasmtime")
    (tmp_path / "python.wasm").touch()
    monkeypatch.setenv("HIVE_FIELDWORK_SDK", str(tmp_path))
    monkeypatch.setenv("HIVE_BANK", str(BANK))
    assert talk.main(['Run quote_spread with {"quotes":[80,65]}']) == 1
    output = capsys.readouterr().out
    assert "unavailable" in output and "python.wasm" in output and "HIVE_FIELDWORK_SDK" in output
