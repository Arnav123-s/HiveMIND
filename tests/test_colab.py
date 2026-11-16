"""The owner's Colab GPU, reached through the release: a child is ordered only when the notebook said it is there, its
cell comes back as the train job would have made it, and with no notebook (or a failure) the runner trains as always."""
import io
import json
import tarfile
import time

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
