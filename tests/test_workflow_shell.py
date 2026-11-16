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
