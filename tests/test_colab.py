"""The owner's Colab GPU, reached through the release: a child is ordered only when the notebook said it is there, its
cell comes back as the train job would have made it, and with no notebook (or a failure) the runner trains as always."""
import io
import json
import tarfile
import time
from pathlib import Path

import pytest

from training import colab


class Release:
    """The release, in memory: put, get, drop and list, as training/colab.py uses them."""
    def __init__(self):
        self.files = {}

    def install(self, mp):
        mp.setattr(colab, "release", lambda s=None: (1, "up", {n: {"id": n, "url": n} for n in self.files}))
        mp.setattr(colab, "put", lambda name, data, s=None, kind="": self.files.__setitem__(name, bytes(data)))
        mp.setattr(colab, "drop", lambda names, s=None: [self.files.pop(n, None) for n in names])

        def get(name, to, s=None):
            if name not in self.files:
                return False
            open(to, "wb").write(self.files[name])
            return True
        mp.setattr(colab, "get", get)
        mp.setattr(colab, "_session", lambda: None)
        mp.setattr(colab.time, "sleep", lambda s: None)


def test_with_no_notebook_nothing_is_ordered_and_the_runner_trains(tmp_path, monkeypatch):
    rel = Release()
    rel.install(monkeypatch)
    rows = tmp_path / "rows.jsonl"
    rows.write_text("{}\n")
    o = {"gen": "g29", "name": "g29code", "dna": "t80"}
    assert colab.order(o, rows) is False and rel.files == {}  # never seen
    rel.files["colab-alive.json"] = json.dumps({"when": time.time() - 2 * colab.ALIVE, "gpu": "L4"}).encode()
    assert colab.order(o, rows) is False and "colab-order-g29-g29code.json" not in rel.files  # gone too long


def test_an_ordered_child_comes_back_as_the_train_job_would_have_made_it(tmp_path, monkeypatch):
    rel = Release()
    rel.install(monkeypatch)
    rel.files["colab-alive.json"] = json.dumps({"when": time.time(), "gpu": "NVIDIA L4"}).encode()
    rows = tmp_path / "rows.jsonl"
    rows.write_text('{"task": "x"}\n')
    o = {"gen": "g29", "name": "g29code", "organ": "code", "dna": "t80", "parent": "t80.g28code.safetensors", "parent_cell": "g28code", "trunk": ""}
    assert colab.order(o, rows) is True
    assert json.loads(rel.files["colab-order-g29-g29code.json"])["parent_cell"] == "g28code" and rel.files["colab-rows-g29-g29code.jsonl"] == rows.read_bytes()
    # the notebook's answer: the three files the train job uploads as its cell
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        for name in ("t80.g29code.gguf", "t80.g29code.json", "t80.g29code.safetensors"):
            data = b"cell"
            info = tarfile.TarInfo(name)
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))
    rel.files["colab-done-g29-g29code.tar.gz"] = buf.getvalue()
    out = tmp_path / "out"
    assert colab.wait("g29", "g29code", 5, out) is True
    assert sorted(p.name for p in out.iterdir()) == ["t80.g29code.gguf", "t80.g29code.json", "t80.g29code.safetensors"]
    assert not [n for n in rel.files if n.endswith("g29-g29code.json") or "g29-g29code" in n]  # the order's files are cleaned away


def test_a_failure_or_no_answer_lets_the_runner_train_and_cleans_up(tmp_path, monkeypatch):
    rel = Release()
    rel.install(monkeypatch)
    rel.files["colab-order-g29-g29data.json"] = b"{}"
    rel.files["colab-failed-g29-g29data.txt"] = b"RuntimeError: out of memory"
    assert colab.wait("g29", "g29data", 5, tmp_path / "o") is False and not rel.files
    clock = iter(range(0, 10**6, 400))
    monkeypatch.setattr(colab.time, "time", lambda: next(clock))
    assert colab.wait("g29", "g29words", 1, tmp_path / "o") is False  # nothing came: the runner trains it


def test_the_notebook_grows_an_order_with_the_same_training_and_sends_back_what_it_made(tmp_path, monkeypatch):
    rel = Release()
    rel.install(monkeypatch)
    rel.files["colab-rows-g29-g29code.jsonl"] = b'{"task": "x"}\n'
    rel.files["t80.g28code.safetensors"] = b"parent"
    ran = {}

    def run(args, cwd=None, capture_output=True, text=True):
        ran["args"] = args
        (tmp_path / "cells" / "members").mkdir(parents=True)
        (tmp_path / "runs" / "grow" / "t80+g29code").mkdir(parents=True)
        (tmp_path / "cells" / "members" / "t80+g29code.gguf").write_bytes(b"g")
        (tmp_path / "cells" / "members" / "t80+g29code.json").write_text(json.dumps({"seconds": 300}))
        (tmp_path / "runs" / "grow" / "t80+g29code" / "adapter_model.safetensors").write_bytes(b"s")
        return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
    monkeypatch.setattr(colab, "ROOT", tmp_path)
    monkeypatch.setattr(colab.subprocess, "run", run)
    colab.grow({"gen": "g29", "name": "g29code", "organ": "code", "dna": "t80", "parent": "t80.g28code.safetensors", "parent_cell": "g28code",
                "trunk": "t80.missing.safetensors", "read": 40, "judged": 10, "epochs": 2}, log=lambda *a, **k: None)
    a = ran["args"]
    assert "--int8-base" not in a and a[a.index("--read") + 1] == "40" and "--parent" in a and "--trunk" not in a  # a trunk not there is left out
    with tarfile.open(fileobj=io.BytesIO(rel.files["colab-done-g29-g29code.tar.gz"])) as t:
        assert sorted(t.getnames()) == ["t80.g29code.gguf", "t80.g29code.json", "t80.g29code.safetensors"]


def test_the_notebook_refuses_a_gpu_too_small_for_the_8b_and_says_what_to_choose(monkeypatch):
    import torch
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    with pytest.raises(SystemExit, match="L4 or A100"):
        colab.serve(0.01)


def test_the_notebook_is_offered_only_the_children_it_can_finish_a_different_one_each_generation():
    """g38: every child was offered to the notebook at once, and it grows one at a time in up to an hour while a child
    waits for it 90 minutes. Now K children (HIVE_COLAB_CHILDREN, 1 unless set) are offered, turn by turn."""
    import subprocess
    from pathlib import Path
    flow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "grow.yml").read_text()
    lines = flow.splitlines()
    i = next(n for n, x in enumerate(lines) if x.strip().startswith('K="${{ vars.HIVE_COLAB_CHILDREN'))
    step = "\n".join(x.strip() for x in lines[i:i + 3])
    assert "PICK=$(" in step and "CM=$((" in step and '--minutes "$CM"' in flow
    children = json.dumps([{"name": f"g40{o}", "organ": o} for o in ("sources", "code", "code2", "data", "words", "words2")])

    def picked(k, run):
        out = []
        for c in json.loads(children):
            text = (step.replace("${{ vars.HIVE_COLAB_CHILDREN || '1' }}", k).replace("${{ needs.plan.outputs.children }}", children)
                    .replace("${{ github.run_number }}", str(run)))
            r = subprocess.run(["bash", "-ec", f'NAME={c["name"]}\n{text}\necho "$PICK $CM"'], capture_output=True, text=True)
            assert r.returncode == 0, r.stderr
            pick, cm = (r.stdout.split() + [""])[:2] if r.stdout.split()[0] == "1" else ("", r.stdout.split()[0])
            out += [c["name"]] * (pick == "1")
            minutes = int(cm)
        return out, minutes
    one, minutes = picked("1", 40)
    assert len(one) == 1 and minutes == 60
    assert picked("1", 41)[0] != one  # another organ the next generation
    two, minutes = picked("2", 40)
    assert len(two) == 2 and minutes == 35
    assert picked("0", 40)[0] == [] and picked("x", 40)[0] and len(picked("x", 40)[0]) == 1  # 0: none; nonsense: 1


# ---- the notebook may come up any time during practice (g42's came up 13 minutes after its training began, and each
# train job had looked for it once, at its start): the child offered waits for it, and one decision is made a child ----
def test_slice_0_waits_and_orders_when_the_notebook_comes_up_after_3_looks(tmp_path, monkeypatch):
    rel = Release()
    rel.install(monkeypatch)
    rel.files["colab-alive.json"] = json.dumps({"when": time.time() - 3 * 3600, "gpu": "NVIDIA L4"}).encode()  # seen 3 h ago
    looks, said = [], []
    rows = tmp_path / "rows.jsonl"

    def sleep(s):
        looks.append(s)
        if len(looks) == 3 and not rows.exists():  # the owner opens the notebook (once)
            rel.files["colab-alive.json"] = json.dumps({"when": time.time(), "gpu": "NVIDIA L4"}).encode()
    monkeypatch.setattr(colab.time, "sleep", sleep)
    assert colab.seen(12) and colab.await_alive(15, log=lambda m, **k: said.append(m)) is True
    assert len(looks) == 3 and len([m for m in said if m.startswith("colab: waiting for the notebook, minute")]) == 3
    rows = tmp_path / "rows.jsonl"
    rows.write_text("{}\n")
    assert colab.order({"gen": "g43", "name": "g43code", "dna": "t80"}, rows) and "colab-order-g43-g43code.json" in rel.files
    # the child's other slices learn it from the order, though the notebook has since gone quiet
    rel.files["colab-alive.json"] = json.dumps({"when": time.time() - 3600, "gpu": "NVIDIA L4"}).encode()
    looks.clear()
    assert colab.aside("g43", "g43code", 15, log=lambda *a, **k: None) is True and not looks
    # no order, no notebook: the whole window, then train as always
    assert colab.aside("g43", "g43data", 15, log=lambda *a, **k: None) is False and len(looks) == 15
    looks.clear()
    assert colab.await_alive(15, log=lambda *a, **k: None) is False and len(looks) == 15


def test_a_notebook_not_seen_for_12_hours_is_not_waited_for(monkeypatch):
    rel = Release()
    rel.install(monkeypatch)
    assert colab.seen(12) is False  # never
    rel.files["colab-alive.json"] = json.dumps({"when": time.time() - 13 * 3600, "gpu": "NVIDIA L4"}).encode()
    assert colab.seen(12) is False
    looks = []
    monkeypatch.setattr(colab.time, "sleep", looks.append)
    assert colab.await_alive(0, log=lambda *a, **k: None) is False and colab.aside("g43", "g43code", 0, log=lambda *a, **k: None) is False and not looks


# the train step's real text, with the release a folder (HIVE_COLAB_LOCAL) and the real training/colab.py; only
# training/grow.py is a stand-in
FLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "grow.yml"


def _step_text(wait="3"):
    import re
    import yaml
    step = next(s for s in yaml.safe_load(FLOW.read_text())["jobs"]["train"]["steps"] if s.get("name") == "Grow the cell")
    children = json.dumps([{"name": f"g40{o}", "organ": o} for o in ("sources", "code", "data", "words")])
    values = {"needs.plan.outputs.children": children, "github.run_number": "40", "vars.HIVE_COLAB_CHILDREN || '1'": "1",
              "vars.HIVE_COLAB_WAIT || '15'": wait, "vars.HIVE_READ || '40'": "40", "vars.HIVE_JUDGED || '10'": "10", "inputs.epochs || '2'": "2"}
    return re.sub(r"\$\{\{(.*?)\}\}", lambda m: values.get(m.group(1).strip(), ""), step["run"])


def _cell_tar(name):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        for arc, data in ((f"t80.{name}.gguf", b"g"), (f"t80.{name}.safetensors", b"s"),
                          (f"t80.{name}.json", json.dumps({"member": f"t80+{name}", "steps": 900, "seconds": 840, "gpu": "NVIDIA L4"}).encode())):
            info = tarfile.TarInfo(arc)
            info.size = len(data)
            t.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _run(tmp_path, name, shard, n, release, wait="3", clock="auto", policy="hash", plateau="off"):
    import os
    import subprocess
    import sys
    import tempfile
    root = Path(__file__).resolve().parents[1]
    work = Path(tempfile.mkdtemp(dir=tmp_path))
    (work / "scripts").symlink_to(root / "scripts")  # the step runs scripts/capped_run.sh
    (work / "cells").mkdir()
    (work / "cells" / "body.json").write_text(json.dumps({"dna": "t80", "trunk": ""}))
    (work / "got").mkdir()
    (work / "got" / "rows.jsonl").write_text('{"task": "x"}\n')
    shim = work / "bin"
    shim.mkdir()
    stand_in = ('#!/bin/bash\ncase "$1" in\n'
                f'  training/colab.py) shift; exec {sys.executable} {root}/training/colab.py "$@" ;;\n'
                '  training/grow.py) echo "train $*" >> calls; mkdir -p cells/members "runs/grow/$DNA+$NAME"\n'
                '    echo g > "cells/members/$DNA+$NAME.gguf"; echo "{}" > "cells/members/$DNA+$NAME.json"\n'
                '    echo w > "runs/grow/$DNA+$NAME/adapter_model.safetensors"; exit 0 ;;\n'
                f'  *) exec {sys.executable} "$@" ;;\nesac\n')
    for exe in ("python", "python3"):
        (shim / exe).write_text(stand_in)
        (shim / exe).chmod(0o755)
    env = dict(os.environ, PATH=f"{shim}:{os.environ['PATH']}", DNA="t80", GEN="g40", NAME=name, ORGAN="code", P="", VERSUS="",
               HIVE_TRAIN_MIN="170" if clock == "auto" else clock, TRAIN_PROFILE=clock, HIVE_SHARD_POLICY=policy, HIVE_TRAIN_PLATEAU=plateau,
               SHARD=str(shard), N=str(n), GITHUB_REPOSITORY="x/y", GITHUB_STEP_SUMMARY=str(work / "summary"),
               HIVE_COLAB_LOCAL=str(release), HIVE_COLAB_POLL="0")
    p = subprocess.run(["bash", "-e", "-c", _step_text(wait)], cwd=work, env=env, capture_output=True, text=True)
    calls = (work / "calls").read_text() if (work / "calls").exists() else ""
    return p, calls, work


def _alive(release, hours_ago, gpu="NVIDIA L4"):
    release.mkdir(exist_ok=True)
    (release / "colab-alive.json").write_text(json.dumps({"when": time.time() - hours_ago * 3600, "gpu": gpu}))


def test_the_step_slice_0_orders_from_a_notebook_that_is_there_and_marks_the_cell(tmp_path):
    from training import reads
    release = tmp_path / "release"
    _alive(release, 0)
    (release / "colab-done-g40-g40sources.tar.gz").write_bytes(_cell_tar("g40sources"))  # the notebook's answer
    p, calls, work = _run(tmp_path, "g40sources", 0, 2, release)  # run 40: g40sources is the child offered
    assert p.returncode == 0, p.stdout + p.stderr
    assert "is growing g40sources" in p.stdout and not calls and (work / "out" / "whole").exists()
    rec = json.loads((work / "out" / "t80.g40sources.json").read_text())
    assert rec["grown_on"] == "colab" and rec["gpu"] == "NVIDIA L4" and rec["minutes"] == 0
    # printed in the log as a slice's record is, so the run's facts find it, and the read measures it
    found = reads.record_in_log(p.stdout)
    assert found["grown_on"] == "colab" and reads._slim(found)["minutes"] == 0
    assert not [f for f in release.iterdir() if "g40-g40sources" in f.name]  # the order's files cleaned away


def test_the_step_other_slices_stand_aside_once_the_order_exists(tmp_path):
    release = tmp_path / "release"
    _alive(release, 1)  # gone quiet an hour ago, but slice 0 ordered while it was there
    (release / "colab-order-g40-g40sources.json").write_text("{}")
    p, calls, _ = _run(tmp_path, "g40sources", 1, 2, release)
    assert p.returncode == 0 and "stands aside" in p.stdout and "is ordered from the notebook" in p.stdout and not calls


@pytest.mark.parametrize("clock,policy,plateau", [
    ("85", "hash", "off"), ("110", "hash", "off"), ("170", "hash", "off"),
    ("auto", "cost", "off"), ("auto", "hash", "observe"), ("auto", "hash", "stop"),
])
def test_explicit_cpu_trials_use_the_requested_clock_even_with_a_live_notebook(tmp_path, clock, policy, plateau):
    release = tmp_path / "release"
    _alive(release, 0)
    p, calls, work = _run(tmp_path, "g40sources", 0, 2, release, clock=clock, policy=policy, plateau=plateau)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "--shard 0/2 " in calls and calls.split()[calls.split().index("--minutes") + 1] == ("170" if clock == "auto" else clock)
    assert not (work / "out" / "whole").exists() and not (release / "colab-order-g40-g40sources.json").exists()


def test_the_step_waits_the_window_then_trains_as_always_with_no_order_and_no_notebook(tmp_path):
    release = tmp_path / "release"
    _alive(release, 2)  # seen 2 h ago: worth the wait
    for shard in (0, 1):
        p, calls, _ = _run(tmp_path, "g40sources", shard, 2, release)
        assert p.returncode == 0, p.stdout + p.stderr
        assert p.stdout.count("colab: waiting for") == 3 and f"--shard {shard}/2 " in calls  # one line a minute, 3 minutes
        assert "colab-order-g40-g40sources.json" not in {f.name for f in release.iterdir()}


def test_the_step_no_one_waits_for_a_notebook_not_seen_for_12_hours_nor_for_a_child_not_offered(tmp_path):
    release = tmp_path / "release"
    _alive(release, 13)
    for shard in (0, 1):
        p, calls, _ = _run(tmp_path, "g40sources", shard, 2, release, wait="15")
        assert p.returncode == 0 and "no notebook seen in the last 12 hours" in p.stdout and "waiting for" not in p.stdout
        assert f"--shard {shard}/2 " in calls
    _alive(release, 0)  # the notebook is there, but g40code is not the child offered this run
    p, calls, _ = _run(tmp_path, "g40code", 1, 2, release)
    assert p.returncode == 0 and "colab:" not in p.stdout and "--shard 1/2 " in calls
    assert "colab-order-g40-g40code.json" not in {f.name for f in release.iterdir()}
