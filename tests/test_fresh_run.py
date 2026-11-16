"""The first job of a run, run as GitHub runs it: a run whose body is no longer the branch's ends at once, and the
nightly schedule starts nothing while a run of the line is under way. Seen 2026-11-16: generation 35 was started by
the schedule while 34 ran, queued behind it, grew from 28's body (siblings of 34's cells) and its record could not be
joined to 34's. These run the real text of the step against a made-up repository."""
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


def _run(tmp_path, moved=False, event="workflow_dispatch", busy=0):
    work, sha = _repo(tmp_path, moved)
    shim = tmp_path / "bin"
    shim.mkdir()
    # `gh api .../runs ... --jq '... | length'`: how many other runs of the line are under way
    (shim / "gh").write_text(f"#!/bin/bash\necho {busy}\n")
    (shim / "gh").chmod(0o755)
    out = tmp_path / "output"
    env = dict(os.environ, PATH=f"{shim}:{os.environ['PATH']}", GITHUB_SHA=sha, GITHUB_REF_NAME="main", GITHUB_RUN_ID="7",
               GITHUB_REPOSITORY="o/r", GITHUB_OUTPUT=str(out), EVENT=event, GH_TOKEN="x")
    p = subprocess.run(["bash", "-e", "-c", _step()], cwd=work, env=env, capture_output=True, text=True)
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
    p, out = _run(tmp_path, event="schedule", busy=1)
    assert p.returncode == 0 and "go=0" in out and "only starts a line that has stopped" in p.stdout


def test_the_schedule_restarts_a_line_that_stopped(tmp_path):
    p, out = _run(tmp_path, event="schedule", busy=0)
    assert p.returncode == 0 and "go=1" in out


def test_every_later_job_waits_for_the_answer():
    jobs = yaml.safe_load((ROOT / ".github" / "workflows" / "grow.yml").read_text())["jobs"]
    for j in ("practice", "gather", "plan"):
        assert "fresh" in str(jobs[j]["needs"]) and "needs.fresh.outputs.go == '1'" in jobs[j]["if"], j
    for j in ("join", "gate", "record"):  # a re-sit (cells_from_run) trains nothing, so it is held by plan
        assert "needs.plan.result == 'success'" in jobs[j]["if"], j
