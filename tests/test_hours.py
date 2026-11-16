"""A generation in about 5 hours with no less work (docs/PLAN.md, L2). g38's hours: practice 134 minutes (each runner
dreamed before its tasks, and a task could take 1500 s), then 8 children of 3 slices made 24 training jobs where 20 run
at once, so 4 slices waited 175 minutes. These run the real text of grow.yml's steps."""
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
FLOW = yaml.safe_load((ROOT / ".github" / "workflows" / "grow.yml").read_text())
JOBS = FLOW["jobs"]


def _step(job, name):
    return next(s for s in JOBS[job]["steps"] if s.get("name", "").startswith(name))


def _fill(text, values):
    """The step's ${{ }} expressions as GitHub would fill them: the ones given, the rest empty."""
    return re.sub(r"\$\{\{(.*?)\}\}", lambda m: values.get(m.group(1).strip(), ""), text)


def _children(m):
    organs = ["sources", "code", "data", "words"]
    return [{"name": f"g40{organs[i % 4]}{i // 4 + 1 if i >= 4 else ''}", "suffix": f"{organs[i % 4]}{i // 4 + 1 if i >= 4 else ''}",
             "organ": organs[i % 4], "parent": ""} for i in range(m)]


def _plan(tmp_path, m, run=40, shards="", versus=""):
    """The plan step run as GitHub runs it, with lineage.py giving m children."""
    work = Path(tempfile.mkdtemp(dir=tmp_path))
    (work / "training").mkdir(parents=True)
    (work / "training" / "lineage.py").write_text(f"print({json.dumps(json.dumps(_children(m)))})\n")
    step = _step("plan", "Which cells have children")
    text = _fill(step["run"], {"vars.HIVE_SHARDS || '3'": shards or "3", "github.run_number": str(run)})
    out = work / "out"
    env = dict(os.environ, GEN="g40", DNA="t80", ORGANS="", VERSUS=versus, GITHUB_OUTPUT=str(out), GITHUB_STEP_SUMMARY=str(work / "summary"))
    p = subprocess.run(["bash", "-e", "-c", text], cwd=work, env=env, capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
    said = dict(ln.split("=", 1) for ln in out.read_text().splitlines())
    assert "shards" not in said  # the old one list for every child is gone
    return json.loads(said["slices"]), p.stdout


def _per_child(slices):
    by = {}
    for e in slices:
        by.setdefault(e["child"]["name"], []).append(e)
    return by


def test_never_more_than_20_training_jobs_and_every_child_on_its_own_slices(tmp_path):
    for m, jobs, most in ((6, 18, 3), (8, 20, 3), (10, 20, 2)):
        slices, said = _plan(tmp_path, m)
        by = _per_child(slices)
        assert len(slices) == jobs and len(by) == m, m
        assert f"{jobs} training jobs" in said
        for name, es in by.items():
            n = es[0]["n"]
            assert 2 <= n <= most and all(e["n"] == n for e in es)
            assert sorted(e["shard"] for e in es) == list(range(n))  # shard k of n, each once
            assert es[0]["child"]["name"] == name and set(es[0]["child"]) == {"name", "suffix", "organ", "parent"}
    by = _per_child(_plan(tmp_path, 8)[0])
    assert Counter(es[0]["n"] for es in by.values()) == {3: 4, 2: 4}  # g38's 8 children: 20 jobs, not 24
    # today's shape where it fits: 4 children of 3; HIVE_SHARDS still sets it (2: 2 each, 1: one runner each)
    assert Counter(e["n"] for e in _plan(tmp_path, 4)[0]) == {3: 12}
    assert Counter(e["n"] for e in _plan(tmp_path, 8, shards="2")[0]) == {2: 16}
    assert Counter(e["n"] for e in _plan(tmp_path, 8, shards="1")[0]) == {1: 8}


def test_from_11_children_some_grow_whole_on_one_runner_and_the_jobs_stay_at_20(tmp_path):
    slices, _ = _plan(tmp_path, 11)
    assert len(slices) == 20 and Counter(es[0]["n"] for es in _per_child(slices).values()) == {2: 9, 1: 2}
    slices, _ = _plan(tmp_path, 21)  # more children than runners: one each (lineage.py grows at most 8)
    assert len(slices) == 21 and {e["n"] for e in slices} == {1}


def test_the_extra_slice_turns_with_the_run_number_and_not_to_the_colab_child(tmp_path):
    longer = {}
    for run in range(40, 48):
        by = _per_child(_plan(tmp_path, 8, run=run)[0])
        longer[run] = {name for name, es in by.items() if es[0]["n"] == 3}
        names = list(by)
        # the child the train step offers the Colab notebook (PICK with K=1: (index - run) % children == 0)
        colab = next(n for i, n in enumerate(names) if (i - run) % len(names) == 0)
        assert colab not in longer[run]
    assert longer[40] != longer[41]
    # over 8 runs every child has the extra slice as often as any other
    assert set(Counter(n for s in longer.values() for n in s).values()) == {4}


def test_a_versus_trial_keeps_both_kinds_within_20_and_sliced_alike(tmp_path):
    slices, said = _plan(tmp_path, 4, versus="--pairs")
    assert len(slices) == 10 and "20 training jobs" in said  # each entry runs twice, once a kind
    assert Counter(e["n"] for e in slices if e["shard"] == 0) == {3: 2, 2: 2}
    assert '["cell","versus"]' in JOBS["train"]["strategy"]["matrix"]["variant"]


def test_the_train_matrix_is_the_plans_slices():
    m = JOBS["train"]["strategy"]["matrix"]
    assert m["slice"] == "${{ fromJSON(needs.plan.outputs.slices) }}" and "shard" not in m and "child" not in m
    assert JOBS["plan"]["outputs"]["slices"] == "${{ steps.plan.outputs.slices }}"
    env = _step("train", "Grow the cell")["env"]
    assert env["SHARD"] == "${{ matrix.slice.shard }}" and env["N"] == "${{ matrix.slice.n }}" and env["NAME"] == "${{ matrix.slice.child.name }}"
    up = next(s for s in JOBS["train"]["steps"] if s.get("uses", "").startswith("actions/upload-artifact"))
    # the name join downloads: part-<variant>-<suffix>-s*, whatever number of slices the child had
    assert up["with"]["name"] == "part-${{ matrix.variant }}-${{ matrix.slice.child.suffix }}-s${{ matrix.slice.shard }}"
    down = next(s for s in JOBS["join"]["steps"] if s.get("uses", "").startswith("actions/download-artifact"))
    assert down["with"]["pattern"] == "part-${{ matrix.variant }}-${{ matrix.child.suffix }}-s*"


def _train(tmp_path, name, shard, n, alive=False):
    """The train step's shell, with stand-ins for the notebook and for training: what grow.py train was asked."""
    work = Path(tempfile.mkdtemp(dir=tmp_path))
    (work / "cells").mkdir(parents=True)
    (work / "cells" / "body.json").write_text(json.dumps({"dna": "t80", "trunk": ""}))
    shim = work / "bin"
    shim.mkdir()
    stand_in = (f'#!/bin/bash\ncase "$1" in\n  training/colab.py) [ "$2" = alive ] && exit {0 if alive else 1}; exit 1 ;;\n'
                '  training/grow.py) echo "train $*" >> calls; mkdir -p cells/members "runs/grow/$DNA+$NAME"\n'
                '    echo g > "cells/members/$DNA+$NAME.gguf"; echo "{}" > "cells/members/$DNA+$NAME.json"\n'
                '    echo w > "runs/grow/$DNA+$NAME/adapter_model.safetensors"; exit 0 ;;\n'
                f'  *) exec {sys.executable} "$@" ;;\nesac\n')
    for exe in ("python", "python3"):
        (shim / exe).write_text(stand_in)
        (shim / exe).chmod(0o755)
    children = json.dumps(_children(8))
    text = _fill(_step("train", "Grow the cell")["run"], {"needs.plan.outputs.children": children, "github.run_number": "40",
                                                        "vars.HIVE_COLAB_CHILDREN || '1'": "1"})
    env = dict(os.environ, PATH=f"{shim}:{os.environ['PATH']}", DNA="t80", GEN="g40", NAME=name, ORGAN="code", P="", VERSUS="",
               SHARD=str(shard), N=str(n), GITHUB_REPOSITORY="x/y", GITHUB_STEP_SUMMARY=str(work / "summary"))
    p = subprocess.run(["bash", "-e", "-c", text], cwd=work, env=env, capture_output=True, text=True)
    calls = (work / "calls").read_text() if (work / "calls").exists() else ""
    return p, calls, work


def test_the_train_step_slices_by_the_entrys_own_n(tmp_path):
    # g40code is not the notebook's this run (run 40: g40sources is, index 0)
    p, calls, _ = _train(tmp_path, "g40code", 1, 2)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "--shard 1/2 " in calls
    p, calls, _ = _train(tmp_path, "g40code", 2, 3)
    assert p.returncode == 0 and "--shard 2/3 " in calls
    p, calls, work = _train(tmp_path, "g40code", 0, 1)  # one slice: the child grown whole on one runner
    assert p.returncode == 0 and "--shard" not in calls and (work / "out" / "whole").exists()
    p, calls, _ = _train(tmp_path, "g40code", 2, 2)  # no such slice
    assert p.returncode == 1 and "not a slice" in p.stdout and not calls
    step = _step("train", "Grow the cell")["run"]
    assert "outputs.shards" not in step and 'SLICE="--shard $SHARD/$N"' in step


def test_the_colab_childs_other_slices_still_stand_aside_while_the_notebook_is_there(tmp_path):
    p, calls, _ = _train(tmp_path, "g40sources", 1, 2, alive=True)
    assert p.returncode == 0 and "stands aside" in p.stdout and not calls
    p, calls, _ = _train(tmp_path, "g40sources", 1, 2, alive=False)
    assert p.returncode == 0 and "--shard 1/2 " in calls


def test_practice_and_dreams_take_at_most_600_s_a_task_and_the_gate_keeps_its_own():
    """The slowest right practice task took 518 s (g38), the slowest corrected dream 242 s: 600 loses no right row."""
    assert _step("practice", "Practice")["env"]["HIVE_TASK_SECONDS"] == "600"
    assert _step("dream", "Dream")["env"]["HIVE_TASK_SECONDS"] == "600"
    assert "HIVE_TASK_SECONDS" not in str(JOBS["gate"]) and "HIVE_TASK_SECONDS" not in str(FLOW.get("env"))


def test_dreams_have_runners_of_their_own_beside_practice():
    practice, dream = JOBS["practice"], JOBS["dream"]
    assert "grow.py dream" not in str(practice) and "grow.py practice" in _step("practice", "Practice")["run"]
    assert dream["strategy"]["matrix"]["dream"] == list(range(1, 9))
    assert len(json.loads(practice["strategy"]["matrix"]["shard"].split("'")[1])) + 8 == 20  # 20 jobs at once
    # the same setup as practice: who sits, the cells, the hive, another cell beside the trunk on each runner
    steps = dream["steps"]
    assert "training/lineage.py members" in steps[1]["run"] and "grow_record.py fetch" in steps[2]["run"]
    assert steps[3]["uses"] == "./.github/actions/hive"
    run = _step("dream", "Dream")["run"]
    assert _step("dream", "Dream")["env"]["HIVE_ROTATE"] == "${{ matrix.dream }}"
    assert "hive-grown/failures.jsonl" in run and "--failures old_failures.jsonl --out rows.jsonl" in run and "--tries 2" in run
    assert 'DREAMS="${{ inputs.dreams || \'3\' }}"' in run and 8 * 3 >= 12 * 2  # as many dreams as before, or more
    assert dream["if"] == practice["if"].replace(" }}", " && inputs.dreams != '0' }}") and dream["needs"] == "fresh"
    # its rows go where gather looks for practice's
    up = next(s for s in steps if s.get("uses", "").startswith("actions/upload-artifact"))
    assert up["with"]["name"] == "rows-dream-${{ matrix.dream }}" and up["with"]["path"] == "rows.jsonl"
    down = next(s for s in JOBS["gather"]["steps"] if s.get("uses", "").startswith("actions/download-artifact"))
    assert down["with"]["pattern"] == "rows-*" and "find new seed -name rows.jsonl" in _step("gather", "Every row")["run"]
    names = {s["with"]["name"] for j in JOBS.values() for s in j.get("steps", []) if s.get("uses", "").startswith("actions/upload-artifact")}
    assert "rows-${{ matrix.shard }}" in names and "dream-work-${{ matrix.dream }}" in names and "practice-work-${{ matrix.shard }}" in names
    # what waited on practice waits on the dreams too, and goes on when they are skipped (dreams 0, a re-sit)
    for j in ("gather", "plan"):
        assert {"practice", "dream"} <= set(JOBS[j]["needs"]) and JOBS[j]["if"].startswith("${{ !cancelled()"), j


def test_dream_seeds_meet_no_practice_seed_and_no_earlier_runs_dream():
    run = _step("dream", "Dream")["run"]
    seed = re.search(r"--seed \$\(\((.*?)\)\)", run).group(1)
    assert seed == "30000000 + ${{ github.run_number }} * 100 + 50 + ${{ matrix.dream }}"
    new = {30000000 + r * 100 + 50 + d for r in range(1, 200) for d in range(1, 9)}
    old_dreams = {30000000 + r * 100 + s for r in range(1, 200) for s in range(1, 13)}  # on the practice runners, until g38
    practice = {10000000 + r * 100 + s for r in range(1, 200) for s in range(1, 13)}
    assert len(new) == 199 * 8 and not new & old_dreams and not new & practice
