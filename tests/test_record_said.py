"""What the record job says by itself: a failed read is written on the page (training/grow_record.failed_page), one
entry a generation goes into docs/knowledge.json (training/reads.add_generation) in the shape scripts/knowledge.py
checks, and the nightly backstop (.github/workflows/nightly.yml) starts nothing, and takes no generation number,
while a run of grow.yml is in progress or queued."""
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from training import grow_record, reads  # noqa: E402
import knowledge  # noqa: E402

G45 = {"generation": "g45", "when": "2026-11-18 09:00", "verdict": "kept", "kept": True, "why": "kept: 45 against 47",
       "arms": {"before": {"passed": 47, "tasks": 64, "seeds": 8, "easy": [32, 32], "hard": [15, 32], "unpractised": [0, 3], "kinds": {}},
                "after": {"passed": 45, "tasks": 64, "seeds": 8, "easy": [32, 32], "hard": [13, 32], "unpractised": [0, 3], "kinds": {}}},
       "first_try": [53, 100], "hours": 4.4}


def test_a_failed_read_writes_a_short_page_with_the_records_numbers(tmp_path):
    record = tmp_path / "g.jsonl"
    record.write_text(json.dumps(G45) + "\n")
    grow_record.failed_page("g45", "777", ["read"], record, tmp_path / "reads")
    text = (tmp_path / "reads" / "latest.md").read_text()
    assert "The read failed in run [777](" in text and "see the record job's log" in text
    assert "after 45 of 64, before 47 of 64" in text and "easy 32 of 32, hard 13 of 32, held out 0 of 3" in text
    assert "first try 0.53" in text and "hours 4.4" in text and (tmp_path / "reads" / "g45.md").read_text() == text
    # the graphs alone failed: the read stays, the failure is put at its top
    (tmp_path / "reads" / "latest.md").write_text("# The read of g45\n\nall of it\n")
    grow_record.failed_page("g45", "777", ["progress"], record, tmp_path / "reads")
    text = (tmp_path / "reads" / "latest.md").read_text()
    assert text.index("The progress graphs failed in run [777]") < text.index("all of it")


def test_the_cli_says_the_read_failed(tmp_path):
    record = tmp_path / "g.jsonl"
    record.write_text(json.dumps(G45) + "\n")
    assert grow_record.failed_page("g45", "1", [], record, tmp_path / "r") == 0  # nothing named: the numbers only


def test_one_entry_a_generation_in_the_shape_knowledge_checks(tmp_path):
    record, k = tmp_path / "g.jsonl", tmp_path / "knowledge.json"
    record.write_text(json.dumps(G45) + "\n")
    shutil.copy(ROOT / "docs" / "knowledge.json", k)
    talk = tmp_path / "talk"
    talk.mkdir()
    (talk / "g45.json").write_text(json.dumps({"of": 10, "out_of_10": 6}))
    assert reads.add_generation("g45", record, k, talk) == 0
    assert reads.add_generation("g45", record, k, talk) == 0  # once only
    gens = json.loads(k.read_text())["generations"]
    assert len(gens) == 1
    e = gens[0]
    assert tuple(e) == reads.ENTRY == knowledge.GENERATION_FIELDS
    assert e["id"] == "gen-g45" and e["verdict"] == "kept" and e["after"] == [45, 64] and e["before"] == [47, 64]
    assert e["easy"] == [32, 32] and e["held_out"] == [0, 3] and e["first_try"] == 0.53 and e["talk"] == 6 and e["hours"] == 4.4
    assert e["hard"] is None or len(e["hard"]) == 2  # the hard kinds that have lessons, from the after arm's kinds
    assert knowledge.problems(json.loads(k.read_text())) == []
    bad = json.loads(k.read_text())
    bad["generations"].append({"id": "gen-g45", "verdict": "maybe"})
    said = " | ".join(knowledge.problems(bad))
    assert "used twice" in said and "not kept or dropped" in said and "no generation" in said
    assert reads.add_generation("g99", record, k) == 1  # no record line, no entry


def test_the_record_job_adds_the_entry_and_draws_the_page():
    steps = yaml.safe_load((ROOT / ".github" / "workflows" / "grow.yml").read_text())["jobs"]["record"]["steps"]
    run = next(s for s in steps if s.get("name", "").startswith("Keep the cells"))["run"]
    assert run.index('reads.py knowledge "$GEN"') < run.index("scripts/knowledge.py") < run.index("git add docs/PROGRESS.md")
    assert "docs/knowledge.json" in run.split("git add docs/PROGRESS.md")[1].split("\n")[0]


# ---- the nightly backstop --------------------------------------------------------------------------------------------
def _ago(hours):
    return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _r(number, status="completed", hours=1.0, title="Generation"):
    return {"databaseId": 1000 + number, "number": number, "displayTitle": f"{title} g{number} · t80 · main", "status": status,
            "createdAt": _ago(hours + 0.5), "startedAt": _ago(hours), "updatedAt": _ago(max(hours - 1, 0)) if status == "completed" else _ago(0)}


def _nightly(tmp_path, runs, loop=""):
    flow = yaml.safe_load((ROOT / ".github" / "workflows" / "nightly.yml").read_text())
    step = flow["jobs"]["start"]["steps"][0]["run"]
    shim = tmp_path / "bin"
    shim.mkdir(parents=True)
    (tmp_path / "runs.json").write_text(json.dumps(runs))
    (shim / "gh").write_text(f"#!/bin/bash\ncase \"$1 $2\" in\n 'run list') cat '{tmp_path / 'runs.json'}';;\n"
                             f" 'workflow run') echo \"$@\" > '{tmp_path / 'started'}';;\n *) exit 1;;\nesac\n")
    (shim / "gh").chmod(0o755)
    env = dict(os.environ, PATH=f"{shim}:{os.environ['PATH']}", GH_TOKEN="x", LOOP=loop, GITHUB_STEP_SUMMARY=str(tmp_path / "summary"))
    p = subprocess.run(["bash", "-e", "-c", step], cwd=tmp_path, env=env, capture_output=True, text=True)
    return p, (tmp_path / "started").read_text() if (tmp_path / "started").exists() else ""


def test_the_schedule_is_not_on_grow_yml_where_it_takes_a_generation_number():
    grow = yaml.safe_load((ROOT / ".github" / "workflows" / "grow.yml").read_text())
    on = grow.get("on", grow.get(True))
    assert "schedule" not in on and "workflow_dispatch" in on
    nightly = yaml.safe_load((ROOT / ".github" / "workflows" / "nightly.yml").read_text())
    assert "schedule" in nightly.get("on", nightly.get(True)) and nightly["permissions"]["actions"] == "write"


def test_the_nightly_starts_nothing_while_a_run_is_in_progress_or_queued(tmp_path):
    for i, runs in enumerate(([_r(45, "in_progress", hours=3)], [_r(44, hours=20), _r(46, "queued", hours=0)],
                              [_r(44, hours=20), _r(47, "in_progress", hours=0, title="Trial generation")])):
        p, started = _nightly(tmp_path / str(i), runs)
        assert p.returncode == 0, p.stdout + p.stderr
        assert started == "" and "in progress or queued" in p.stdout and "no generation number is taken" in p.stdout


def test_the_nightly_starts_nothing_when_the_line_ran_within_8_hours(tmp_path):
    p, started = _nightly(tmp_path, [_r(45, hours=3)])
    assert p.returncode == 0 and started == "" and "within 8 hours" in p.stdout


def test_the_nightly_restarts_a_line_that_stopped(tmp_path):
    p, started = _nightly(tmp_path, [_r(44, hours=11), _r(45, hours=1, title="Trial generation")])
    assert p.returncode == 0, p.stdout + p.stderr
    assert started.startswith("workflow run grow.yml --ref main")


def test_the_nightly_stops_with_the_line(tmp_path):
    p, started = _nightly(tmp_path, [], loop="stop")
    assert p.returncode == 0 and started == "" and "HIVE_LOOP" in p.stdout
