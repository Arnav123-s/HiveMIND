"""Measured T80 fits and five-question first-program panels for the frozen local line."""
import argparse
import json
import os
from pathlib import Path
import time
import tempfile

from team import solo
from team.specialists.coder import extract_code
from team.tools.sandbox import GIVEN, give
from training import exam
from training.experiments.astra_cpu.five_kinds.transfer import native
from training.experiments.astra_cpu.five_kinds.transfer.grade import RUN, run_guest
from training.experiments.fieldwork.guest import Guest
from training.experiments.replay_archive.native_cycles.freeze import HERE, FAMILIES, digest, row_id

PANEL_SHA = "b47c3198485544e736774fac16b7536ff62fef55e26b656d3dba0e453e58d099"
MANIFEST_SHA = "4e267e24dd57b85a4280a80283fb6178aaa6e14f91c1ec19734a3a5edde553b6"
CONTROL_SHA = "96926f0e537c9aaabc64daffd19b8a4ba05cb86c36ba1f8bf6aeee2448231f18"
START_SHA = "6d2b50f593941b73e564286a3889768948bf539fec5517c6b884cd2c390d0ab0"
START_GGUF = "72913f1c566638f2177574178f1d6925cde956a92b35af06795e7598c5729036"


def load(path, expect):
    assert native.digest(path) == expect
    return json.loads(path.read_text())


def evaluate(a):
    a.arm = "release" if a.cycle == 0 else f"cycle-{a.cycle}"
    a.out = a.scratch / f"{a.arm}-calls.json"
    a.log = a.scratch / f"{a.arm}-server.log"
    a.lora_sha = START_GGUF if a.cycle == 0 else json.loads((a.scratch / f"cycle-{a.cycle}-fit.json").read_text())["gguf_sha256"]
    native.run(a, panel=HERE / "panel.json", panel_sha=PANEL_SHA)


def score(a):
    cases = load(HERE / "panel.json", PANEL_SHA)["rows"]
    raw = json.loads((a.scratch / f"{a.arm}-calls.json").read_text())
    assert raw["complete"] and raw["panel_sha256"] == PANEL_SHA
    assert [x["name"] for x in raw["calls"]] == [r["name"] for r in cases]
    guest, scores = Guest(a.sdk), {}
    for row, call in zip(cases, raw["calls"]):
        task, check = exam.remake(row["name"], row["seed"], 0)[2:]
        assert task == row["task"]
        code = extract_code(call["text"])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            work = root / "work"
            work.mkdir()
            give(task, work, skip=solo.wanted(task))
            (work / "member1_1.py").write_text(code)
            # The regular local sandbox exposes its prompt-provided file map to the open hook.
            # The guest sees the same map, inside its own preopened working directory.
            boot = f"import os\nos.environ['HIVE_GIVEN'] = {GIVEN!r}\n" + RUN
            out = run_guest(guest, work, root / "io", boot, [], True)
            paths = list(work.rglob("*"))
            regular = len(paths) <= 128 and all(not p.is_symlink() and (p.is_dir() or p.is_file() and p.stat().st_size <= 1_000_000) for p in paths)
            error = out["error"] or ("unexpected output tree" if not regular else None)
            ok, detail = check(root, out["stdout"].strip()) if code and not error else (False, error or "no program")
            scores[row["name"]] = {"passed": bool(ok), "grader": detail, "exit_error": error,
                                   "stdout": out["stdout"][:1200], "stderr": out["stderr"], "program_sha256": digest(code.encode()),
                                   "files": {str(p.relative_to(work)): native.digest(p) for p in sorted(paths)
                                             if regular and p.is_file() and p.name != "member1_1.py"}}
    native.save(a.scratch / f"{a.arm}-grades.json", {"lora_sha256": raw["lora_sha256"], "results": scores})


def decide(a):
    parent = json.loads((a.scratch / f"{a.parent}-grades.json").read_text())
    child = json.loads((a.scratch / f"cycle-{a.cycle}-grades.json").read_text())
    fit = json.loads((a.scratch / f"cycle-{a.cycle}-fit.json").read_text())
    assert fit["parent_gguf_sha256"] == parent["lora_sha256"] and fit["gguf_sha256"] == child["lora_sha256"]
    old, new = ({k for k, result in arm["results"].items() if result["passed"]} for arm in (parent, child))
    gained, lost = new - old, old - new
    keep = not lost and bool(gained.intersection(FAMILIES))
    native.save(a.scratch / f"cycle-{a.cycle}-decision.json", dict(parent=a.parent, child=f"cycle-{a.cycle}", parent_passed=sorted(old),
                child_passed=sorted(new), gained=sorted(gained), lost=sorted(lost), keep=keep, next=f"cycle-{a.cycle}" if keep else a.parent))


def train(a):
    row_path = a.scratch / f"rows-{a.cycle}.jsonl"
    ids = [row_id(json.loads(l)) for l in row_path.read_text().splitlines()]
    if a.fresh_only:
        stage = load(HERE / "fresh_only/manifest.json", CONTROL_SHA)["stages"][a.cycle - 1]
        assert a.parent == "release" and native.digest(row_path) == stage["input_sha256"]
        assert ids == stage["layout"]
    else:
        stage = load(HERE / "manifest.json", MANIFEST_SHA)["stages"][a.cycle - 1]
        assert ids == stage["fresh"] + [stage["replay"]]
    parent_sha = START_SHA if a.parent == "release" else json.loads((a.scratch / f"{a.parent}-fit.json").read_text())["trainable_sha256"]
    assert native.digest(a.weights) == parent_sha
    parent_gguf = START_GGUF if a.parent == "release" else json.loads((a.scratch / f"{a.parent}-fit.json").read_text())["gguf_sha256"]
    if a.cycle > 1 and not a.fresh_only:
        assert json.loads((a.scratch / f"cycle-{a.cycle-1}-decision.json").read_text())["next"] == a.parent
    run = a.scratch / f"cycle-{a.cycle}"
    run.mkdir()
    name = "retention" + str(a.cycle)
    os.environ.update(HF_HUB_OFFLINE="1", HIVE_GPU="0", HIVE_ROW_CHECKPOINT="1", HIVE_CHUNK_CE="128", HIVE_SELF_REPLAY="0" if a.fresh_only else "1",
                      HIVE_SELF_REPLAY_RATIO="2", HIVE_KEEP_BACK="0", HIVE_PREFIX_CACHE="0", AGENT_TEAM_THREADS="2")
    from training import grow
    assert grow.KEEP_BACK == 0
    grow.GROW = run / "grow"
    # Check that no inherited tensor can silently be omitted by the normal parent loader.
    from safetensors import safe_open
    from training import ternary_base
    original_load = ternary_base.load
    original_begin = grow.MemoryGuard.begin
    inherited = {}
    original_pick = grow.Study.pick
    picked = []

    def track_pick(study, *args, **kwargs):
        value = original_pick(study, *args, **kwargs)
        if value is not None:
            picked.append(ids[value[1]])
        return value

    def verify_start(guard):
        if inherited:
            import torch
            with safe_open(a.weights, framework="pt") as sd:
                for key, param in inherited.items():
                    assert torch.equal(param.detach().cpu(), sd.get_tensor(key)), key
            inherited.clear()
        return original_begin(guard)

    def validate(*args, **kwargs):
        model, cell = original_load(*args, **kwargs)
        inherited.update({f"base_model.model.{n}.lora_{side}.weight": getattr(layer, f"lora_{side}")
                    for n, layer in cell.layers.items() for side in ("A", "B")})
        expected = {k: list(param.shape) for k, param in inherited.items()}
        with safe_open(a.weights, framework="np") as sd:
            assert set(sd.keys()) == set(expected) and len(expected) == 196
            assert all(sd.get_slice(k).get_shape() == shape for k, shape in expected.items())
        return model, cell

    ternary_base.load = validate
    grow.MemoryGuard.begin = verify_start
    if a.fresh_only:
        grow.Study.pick = track_pick
    begin = time.monotonic()
    try:
        result = grow.train(row_path, name=name, base="t80", epochs=1, rank=32, lr=.0002, max_len=1152, layers="last14",
                            accum=1, seed=56, lean="sources", checkpoint=False, int8_base=True, gen="g56",
                            parent=str(a.weights), out_dir=run / "exports")
    finally:
        grow.Study.pick = original_pick
        ternary_base.load = original_load
        grow.MemoryGuard.begin = original_begin
    assert not inherited, "no measured optimizer input"
    gguf = Path(result.pop("file"))
    tensor = grow.GROW / ("t80+" + name) / "adapter_model.safetensors"
    out = {"parent": a.parent, "parent_trainable_sha256": parent_sha, "parent_gguf_sha256": parent_gguf, "inherited_tensors": 196,
           "trainable_sha256": native.digest(tensor), "gguf_sha256": native.digest(gguf), "elapsed_seconds": round(time.monotonic()-begin, 2),
           "meta": result}
    if a.fresh_only:
        assert picked == stage["optimizer_order"]
        assert result["new_rows"] == result["used"] == result["steps"] == 3
        assert result["memory"]["rows_skipped"] == 0 and "self_replay" not in result
        out["optimizer_order"] = picked
    native.save(a.scratch / f"cycle-{a.cycle}-fit.json", out)
    if a.fresh_only:
        return
    expected = {"fresh": 2, "replay": 1, "other": 0}
    assert all(result["self_replay"][k] == expected for k in ("passes", "unique_rows")), result["self_replay"]


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("train", "evaluate", "score", "decide"))
    p.add_argument("--cycle", type=int, choices=range(4), default=0)
    for k in ("scratch", "weights", "lora", "sdk", "model", "runtime"):
        p.add_argument("--" + k, type=Path, required=k == "scratch")
    p.add_argument("--parent", default="release")
    p.add_argument("--fresh-only", action="store_true", help="use the frozen follow-up control for this proposal")
    p.add_argument("--arm", default="release")
    args = p.parse_args()
    {"evaluate": evaluate, "train": train, "score": score, "decide": decide}[args.mode](args)
