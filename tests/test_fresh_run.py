"""The first job of a run, run as GitHub runs it: a run whose body is no longer the branch's ends at once, and the
nightly schedule starts nothing when the line ran within 8 hours (it restarts itself after each record), and a run
ends when a newer run of the line is already under way. Seen 2026-11-16: generation 35 was started by the schedule
while 34 ran, queued behind it, grew from 28's body (siblings of 34's cells) and its record could not be joined to
34's. Seen 2026-11-17: g40, scheduled while g39 ran, passed the body check (g39's record had failed) and grew from the
old body beside the self-restarting line. These run the real text of the step against a made-up repository and a
fake `gh` that lists made-up runs."""
import datetime as dt
import json
import os
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _step():
    flow = yaml.safe_load((ROOT / ".github" / "workflows" / "grow.yml").read_text())
    return next(s for s in flow["jobs"]["fresh"]["steps"] if s.get("id") == "fresh")["run"]


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def _repo(tmp_path, moved):
    """A branch 'main' on an origin; this run checked out its first commit. moved: the branch's body changed since."""
    origin, work = tmp_path / "origin.git", tmp_path / "work"
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    _git(tmp_path, "clone", "-q", str(origin), str(work))
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        _git(work, "config", k, v)
    (work / "cells").mkdir()
    (work / "cells" / "body.json").write_text('{"generation": 28}')
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "g28")
    sha = _git(work, "rev-parse", "HEAD")
    if moved:
        (work / "cells" / "body.json").write_text('{"generation": 34}')
    else:
        (work / "README").write_text("a change that is not the body")
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", "later")
    _git(work, "push", "-q", "origin", "HEAD:main")
    _git(work, "checkout", "-q", sha)  # the commit this run checked out
    return work, sha


def _ago(hours):
    return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _line(number, status="completed", hours=1.0, title="Generation"):
    """A run of grow.yml as `gh run list --json` gives it, started `hours` ago (ended an hour later when completed)."""
    return {"databaseId": 1000 + number, "number": number, "displayTitle": f"{title} g{number} · t80 · main",
            "status": status, "createdAt": _ago(hours + 0.5), "startedAt": _ago(hours),
            "updatedAt": _ago(max(hours - 1, 0)) if status == "completed" else _ago(0)}


def _run(tmp_path, moved=False, event="workflow_dispatch", runs=(), number=40, not_line=""):
    work, sha = _repo(tmp_path, moved)
    shim = tmp_path / "bin"
    shim.mkdir()
    # `gh run list --workflow grow.yml --branch main --json ...`: the made-up runs of the workflow, this one among them
    listed = [*runs, {"databaseId": 7, "number": number, "displayTitle": f"Generation g{number} · t80 · main",
                      "status": "in_progress", "createdAt": _ago(0.1), "startedAt": _ago(0), "updatedAt": _ago(0)}]
    (tmp_path / "runs.json").write_text(json.dumps(listed))
    (shim / "gh").write_text(f"#!/bin/bash\n[ \"$1 $2\" = 'run list' ] || exit 1\ncat '{tmp_path / 'runs.json'}'\n")
    (shim / "gh").chmod(0o755)
    out, summary = tmp_path / "output", tmp_path / "summary"
    env = dict(os.environ, PATH=f"{shim}:{os.environ['PATH']}", GITHUB_SHA=sha, GITHUB_REF_NAME="main", GITHUB_RUN_ID="7",
               GITHUB_RUN_NUMBER=str(number), GITHUB_REPOSITORY="o/r", GITHUB_OUTPUT=str(out),
               GITHUB_STEP_SUMMARY=str(summary), EVENT=event, GH_TOKEN="x", NOT_LINE=not_line)
    p = subprocess.run(["bash", "-e", "-c", _step()], cwd=work, env=env, capture_output=True, text=True)
    p.summary = summary.read_text() if summary.exists() else ""
    return p, out.read_text() if out.exists() else ""


def test_a_run_whose_body_is_still_the_branchs_goes_on(tmp_path):
    p, out = _run(tmp_path, moved=False)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "go=1" in out


def test_a_run_queued_behind_a_generation_that_recorded_ends(tmp_path):
    p, out = _run(tmp_path, moved=True)
    assert p.returncode == 0, p.stdout + p.stderr  # it ends without failing: the later jobs are skipped
    assert "go=0" in out and "siblings, not children" in p.stdout


def test_the_schedule_starts_nothing_while_the_line_runs(tmp_path):
    p, out = _run(tmp_path, event="schedule", runs=[_line(39, "in_progress", hours=3)])
    assert p.returncode == 0 and "go=0" in out and "only starts a line that has stopped" in p.stdout


def test_a_scheduled_run_ends_when_the_line_ran_2_hours_ago(tmp_path):
    p, out = _run(tmp_path, event="schedule", runs=[_line(39, "completed", hours=3)])  # ended 2 h ago
    assert p.returncode == 0, p.stdout + p.stderr
    assert "go=0" in out and "within 8 hours" in p.summary


def test_the_schedule_restarts_a_line_that_stopped(tmp_path):
    # the line's last run ended 10 h ago; a trial 1 h ago is not the line
    p, out = _run(tmp_path, event="schedule", runs=[_line(38, hours=11), _line(39, hours=1, title="Trial generation")])
    assert p.returncode == 0, p.stdout + p.stderr
    assert "go=1" in out and p.summary == ""


def test_a_dispatched_run_ends_when_a_newer_line_run_is_queued(tmp_path):
    p, out = _run(tmp_path, runs=[_line(39, hours=3), _line(41, "queued", hours=0)])
    assert p.returncode == 0, p.stdout + p.stderr
    assert "go=0" in out and "the newer one wins" in p.summary and "g41" in p.summary


def test_a_dispatched_run_alone_goes_on(tmp_path):
    # an older line run ended an hour ago and this run is the restart it made: it goes on
    p, out = _run(tmp_path, runs=[_line(39, hours=2)])
    assert p.returncode == 0, p.stdout + p.stderr
    assert "go=1" in out and p.summary == ""


def test_a_trial_is_not_ended_by_a_newer_line_run(tmp_path):
    p, out = _run(tmp_path, runs=[_line(41, "in_progress", hours=0)], not_line="1")
    assert p.returncode == 0 and "go=1" in out


def test_every_later_job_waits_for_the_answer():
    jobs = yaml.safe_load((ROOT / ".github" / "workflows" / "grow.yml").read_text())["jobs"]
    for j in ("practice", "gather", "plan"):
        assert "fresh" in str(jobs[j]["needs"]) and "needs.fresh.outputs.go == '1'" in jobs[j]["if"], j
    for j in ("join", "gate", "record"):  # a re-sit (cells_from_run) trains nothing, so it is held by plan
        assert "needs.plan.result == 'success'" in jobs[j]["if"], j
