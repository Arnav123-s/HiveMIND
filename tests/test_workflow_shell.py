"""The join step's shell, run as GitHub runs it (bash -e): generation 33's joins all failed on a search that ended on a
false test inside $( ), which bash -e takes as the step's end, with no word said. These run the real text of the step."""
import os
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _step():
    flow = yaml.safe_load((ROOT / ".github" / "workflows" / "grow.yml").read_text())
    return next(s for s in flow["jobs"]["join"]["steps"] if s.get("name", "").startswith("The child"))["run"]


def _run(tmp_path, folders):
    for name, files in folders.items():
        d = tmp_path / "parts" / name
        d.mkdir(parents=True)
        for f in files:
            (d / f).write_text("x")
    shim = tmp_path / "bin"
    shim.mkdir()
    # `python training/merge.py join work FILES --base D --name N --out-dir made`: makes what the real one makes
    (shim / "python").write_text('#!/bin/bash\nmkdir -p work made\necho w > work/adapter_model.safetensors\n'
                                 'echo g > "made/$DNA+$NAME.gguf"\necho "{\\"slices\\": $(($# - 9))}" > "made/$DNA+$NAME.json"\necho joined "$@"\n')
    (shim / "python").chmod(0o755)
    env = dict(os.environ, PATH=f"{shim}:{os.environ['PATH']}", DNA="t80", NAME="g35code", GITHUB_STEP_SUMMARY=str(tmp_path / "summary"))
    return subprocess.run(["bash", "-e", "-c", _step()], cwd=tmp_path, env=env, capture_output=True, text=True)


def test_slices_are_joined_under_bash_e(tmp_path):
    p = _run(tmp_path, {f"part-cell-code-s{k}": [f"t80.g33code.{e}" for e in ("gguf", "json", "safetensors")] for k in range(3)})
    assert p.returncode == 0, p.stdout + p.stderr
    assert "joined" in p.stdout and sorted(x.name for x in (tmp_path / "out").iterdir()) == ["t80.g35code.gguf", "t80.g35code.json", "t80.g35code.safetensors"]


def test_a_whole_cell_is_taken_as_it_is(tmp_path):
    p = _run(tmp_path, {"part-cell-code-s0": ["whole", "t80.g33code.gguf", "t80.g33code.json", "t80.g33code.safetensors"]})
    assert p.returncode == 0, p.stdout + p.stderr
    assert "joined" not in p.stdout and (tmp_path / "out" / "t80.g35code.safetensors").exists()


def test_an_earlier_runs_cell_from_before_slices_is_taken_whole(tmp_path):
    p = _run(tmp_path, {"cell-code": ["t80.g27code.gguf", "t80.g27code.json", "t80.g27code.safetensors"]})
    assert p.returncode == 0, p.stdout + p.stderr
    assert (tmp_path / "out" / "t80.g35code.gguf").exists()


def test_nothing_grown_says_so_and_fails(tmp_path):
    p = _run(tmp_path, {"part-cell-code-s0": []})
    assert p.returncode == 1 and "no slice of g35code grew" in p.stdout


# The record job's last step, run as GitHub runs it against a scratch branch: generation 39's record failed its rebase
# on docs/PROGRESS.md, which main had redrawn after the job's checkout. A drawn file must never block a record.
def _record_step():
    flow = yaml.safe_load((ROOT / ".github" / "workflows" / "grow.yml").read_text())
    return next(s for s in flow["jobs"]["record"]["steps"] if s.get("name", "").startswith("Keep the cells"))["run"]


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def test_a_record_lands_when_main_redrew_progress_after_checkout(tmp_path, monkeypatch):
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    origin, job, other = tmp_path / "origin.git", tmp_path / "job", tmp_path / "other"
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    _git(tmp_path, "clone", "-q", str(origin), str(other))
    for k, v in {"user.name": "t", "user.email": "t@t"}.items():
        _git(other, "config", k, v)
    (other / "cells").mkdir()
    (other / "training" / "reports").mkdir(parents=True)
    (other / "docs" / "progress").mkdir(parents=True)
    (other / "training" / "reports" / "generations.jsonl").write_text('{"generation": "g38"}\n')
    (other / "cells" / "body.json").write_text('{"generation": 34}\n')
    (other / "docs" / "PROGRESS.md").write_text("drawn from 1 lines\n")
    (other / "docs" / "KNOWLEDGE.md").write_text("known\n")
    (other / "docs" / "progress" / "score.svg").write_text("<svg/>\n")
    _git(other, "add", "-A")
    _git(other, "commit", "-q", "-m", "start")
    _git(other, "push", "-q", "origin", "main")
    _git(tmp_path, "clone", "-q", str(origin), str(job))  # the record job's checkout
    # main moves on after the checkout: the progress page is drawn again there
    (other / "docs" / "PROGRESS.md").write_text("drawn again on main\n")
    (other / "notes.md").write_text("main's own work\n")
    _git(other, "add", "-A")
    _git(other, "commit", "-q", "-m", "main moves")
    _git(other, "push", "-q", "origin", "main")
    # what the record step before this one wrote: the generation's line and the new body
    with open(job / "training" / "reports" / "generations.jsonl", "a") as f:
        f.write('{"generation": "g39", "kept": true}\n')
    (job / "cells" / "body.json").write_text('{"generation": 39}\n')
    (job / "got").mkdir()  # the cells and rows the job downloaded (not in the repository)
    shim = tmp_path / "bin"
    shim.mkdir()
    # python3: the drawing scripts draw from the record as it stands in the checkout; the rest do nothing
    (shim / "python3").write_text(
        '#!/bin/bash\ncase "$1" in\n'
        ' training/progress.py) echo "drawn from $(wc -l < training/reports/generations.jsonl) lines" > docs/PROGRESS.md;;\n'
        ' training/reads.py) mkdir -p docs/reads; echo "read of $3" > "docs/reads/$3.md"; cp "docs/reads/$3.md" docs/reads/latest.md;;\n'
        ' scripts/knowledge.py) echo "known, drawn" > docs/KNOWLEDGE.md;;\nesac\n')
    (shim / "gh").write_text("#!/bin/bash\nexit 0\n")
    (shim / "curl").write_text("#!/bin/bash\nexit 22\n")
    for f in shim.iterdir():
        f.chmod(0o755)
    env = dict(os.environ, PATH=f"{shim}:{os.environ['PATH']}", DNA="t80", GEN="g39", GITHUB_REF_NAME="main",
               GITHUB_REPOSITORY="o/r", GITHUB_STEP_SUMMARY=str(tmp_path / "summary"))
    p = subprocess.run(["bash", "-e", "-c", _record_step()], cwd=job, env=env, capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
    _git(other, "pull", "-q", "--rebase", "origin", "main")
    assert _git(other, "log", "-1", "--format=%s") == "The hive's body: generation g39"
    assert (other / "training" / "reports" / "generations.jsonl").read_text().splitlines() == ['{"generation": "g38"}', '{"generation": "g39", "kept": true}']
    assert (other / "cells" / "body.json").read_text() == '{"generation": 39}\n'
    assert (other / "docs" / "PROGRESS.md").read_text() == "drawn from 2 lines\n"  # drawn again, from the new record
    assert (other / "docs" / "reads" / "g39.md").exists() and (other / "notes.md").exists()  # main's own work is kept
