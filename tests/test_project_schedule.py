"""Feasibility, resource limits and provenance of the public scheduling command."""

import json
import os

import pytest

from team import cli, schedule
from training.experiments.fieldwork import work as fw


PROJECT = {"capacity": [2], "jobs": [[1, [1], [2]], [1, [1], [2]], [2, [2], []]]}


def test_cli_returns_the_frozen_start_vector_and_named_job_times(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HIVE_BANK", "off")
    p = tmp_path / "project.json"
    p.write_text(json.dumps(dict(PROJECT, job_names=["Serve", "Pack", "Prepare"])))
    assert cli.main(["schedule", str(p)]) == 0
    out = capsys.readouterr()
    assert json.loads(out.out) == [2, 2, 0]
    assert out.err.splitlines()[0] == "Makespan 3. Winner classical/shortest-duration."
    assert "Prepare: start 0, finish 2" in out.err and "Serve: start 2, finish 3" in out.err


@pytest.mark.parametrize("project", [
    {"capacity": [1], "jobs": [[0, [2], []]]},
    {"capacity": [1], "jobs": [[1, [1], [1]], [2, [1], [0]]]},
    {"capacity": [2], "jobs": [[1, [1], [-1]]]},
    {"capacity": [True], "jobs": []},
    {"capacity": [1], "jobs": [[True, [1], []]]},
    {"capacity": [2], "jobs": [[3, [], []]]},
    {"capacity": [3], "jobs": [[2049, [1], []]]},
    {"capacity": [1], "jobs": [[1, [1], []]] * 65},
    {"capacity": [1] * 9, "jobs": []},
    dict(PROJECT, job_names=["one"]),
    dict(PROJECT, price_per_hour=7),
])
def test_invalid_projects_have_no_result(tmp_path, project, capsys):
    p = tmp_path / "project.json"
    p.write_text(json.dumps(project))
    assert schedule.main([str(p)]) == 2
    out = capsys.readouterr()
    assert not out.out and "Cannot schedule project" in out.err


def test_duplicate_json_keys_and_oversized_files_are_refused(tmp_path, capsys):
    p = tmp_path / "project.json"
    for body in ['{"capacity":[1],"jobs":[],"jobs":[]}', " " * 131_073]:
        p.write_text(body)
        assert schedule.main([str(p)]) == 2
        assert not capsys.readouterr().out


def test_event_check_handles_boundary_reuse_empty_jobs_and_arbitrary_valid_waits():
    project = {"capacity": [1], "jobs": [[3, [1], []], [5, [1], [0]], [0, [1], []]]}
    assert schedule.checked_makespan(project, [0, 3, 2]) == 8
    assert schedule.checked_makespan(project, [0, 10**10, 1]) == 10**10 + 5
    with pytest.raises(ValueError, match="predecessor"):
        schedule.checked_makespan(project, [0, 2, 1])
    with pytest.raises(ValueError, match="capacity"):
        schedule.checked_makespan({"capacity": [1], "jobs": [[3, [1], []], [3, [1], []]]}, [0, 1])
    for starts in ([False, 3, 1], [0, 3], [-2, 3, 0]):
        with pytest.raises(ValueError):
            schedule.checked_makespan(project, starts)
    assert schedule.schedule({"capacity": [], "jobs": []})[0] == (0, "classical/shortest-duration", [])


def add_method(bank, source, description=schedule.CONTRACT):
    row = dict(task=schedule.TASK, source=source, digest=fw.fingerprint(source), description=description,
               public=2, validation=3, parents=[])
    fw.admit(bank, row)
    return row["digest"]


def test_only_a_strictly_shorter_checked_bank_result_wins(tmp_path, monkeypatch):
    # A slow but feasible baseline makes a real improvement observable in this arbitration fixture.
    monkeypatch.setattr(schedule, "_classical", lambda project, edges: iter([("classical/test", [3, 4, 0])]))
    candidates = {"tie": [3, 4, 0], "shorter": [2, 2, 0], "broken": [0, 0, 0]}
    calls = []
    class Runner:
        def run(self, source, inputs, fuel):
            assert inputs == [PROJECT] and fuel == schedule.FUEL
            calls.append(source)
            return [{"value": candidates[source]}], 0, 0

    monkeypatch.setattr(schedule.saved, "guest", lambda: Runner())
    add_method(tmp_path, "broken")
    add_method(tmp_path, "tie")
    add_method(tmp_path, "other", "Different rule with the same task name")
    raw = dict(PROJECT, job_names=["One", "Two", "Three"])
    (span, winner, starts), _, notes = schedule.schedule(raw, tmp_path)
    assert (span, winner, starts) == (5, "classical/test", [3, 4, 0]) and len(notes) == 1
    key = add_method(tmp_path, "shorter")
    (span, winner, starts), _, notes = schedule.schedule(raw, tmp_path)
    assert (span, winner, starts) == (3, "bank/" + key, [2, 2, 0])
    assert set(calls) == set(candidates) and len(notes) == 1


def test_invalid_real_wasi_method_cannot_displace_verified_baseline(tmp_path, monkeypatch):
    sdk = os.environ.get("HIVE_FIELDWORK_WASI")
    if not sdk:
        pytest.skip("set HIVE_FIELDWORK_WASI to run the real WebAssembly guest")
    pytest.importorskip("wasmtime")
    monkeypatch.setenv("HIVE_FIELDWORK_SDK", sdk)
    digest = add_method(tmp_path, "def solve(x): return [0] * len(x['jobs'])")
    (span, winner, starts), _, notes = schedule.schedule(PROJECT, tmp_path)
    assert (span, winner, starts) == (3, "classical/shortest-duration", [2, 2, 0])
    assert len(notes) == 1 and digest in notes[0] and "predecessor" in notes[0]
