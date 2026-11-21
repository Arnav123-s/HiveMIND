"""Collect immutable fits, model completions, grader decisions and realized exposures."""
import argparse
import gzip
import json
from pathlib import Path

from training.experiments.replay_archive.native_cycles import pilot


def tensor_change(before, after):
    import numpy as np
    from safetensors import safe_open
    count = changed = 0
    squared_update = 0.0
    with safe_open(before, framework="np") as start, safe_open(after, framework="np") as end:
        assert len(start.keys()) == 196 and set(start.keys()) == set(end.keys())
        for name in start.keys():
            a, b = start.get_tensor(name), end.get_tensor(name)
            assert a.shape == b.shape and np.isfinite(b).all()
            delta = b.astype(np.float64) - a
            count += delta.size
            changed += int(np.count_nonzero(delta))
            squared_update += float(np.sum(delta * delta))
    assert changed > 0
    return {"values": count, "changed": changed, "squared_update": squared_update}


def collect(scratch, initial):
    cases = pilot.load(pilot.HERE / "panel.json", pilot.PANEL_SHA)["rows"]
    parent = "release"
    weights = {"release": initial}
    assert pilot.native.digest(initial) == pilot.START_SHA
    report = {"panel_sha256": pilot.PANEL_SHA, "manifest_sha256": pilot.MANIFEST_SHA, "arms": {}, "transitions": []}
    captures = {}
    for i in range(4):
        name = "release" if i == 0 else f"cycle-{i}"
        raw = json.loads((scratch / f"{name}-calls.json").read_text())
        graded = json.loads((scratch / f"{name}-grades.json").read_text())
        assert graded["lora_sha256"] == raw["lora_sha256"]
        assert raw["complete"] and raw["panel_sha256"] == pilot.PANEL_SHA
        assert [c["name"] for c in raw["calls"]] == [c["name"] for c in cases]
        captures[name] = raw
        if i:
            fit = json.loads((scratch / f"{name}-fit.json").read_text())
            decision = json.loads((scratch / f"{name}-decision.json").read_text())
            assert decision["parent"] == parent and decision["child"] == name and fit["parent"] == parent
            assert fit["gguf_sha256"] == raw["lora_sha256"] and fit["parent_gguf_sha256"] == report["arms"][parent]["lora_sha256"]
            assert fit["gguf_sha256"] != fit["parent_gguf_sha256"]
            expected = {"fresh": 2, "replay": 1, "other": 0}
            assert fit["meta"]["steps"] == 3 and fit["meta"]["memory"]["rows_skipped"] == 0
            assert all(fit["meta"]["self_replay"][k] == expected for k in ("passes", "unique_rows"))
            candidate = scratch / name / "grow" / f"t80+retention{i}" / "adapter_model.safetensors"
            assert pilot.native.digest(candidate) == fit["trainable_sha256"]
            weights[name] = candidate
            report["transitions"].append({"fit": fit, "decision": decision, "inherited_to_final": tensor_change(weights[parent], candidate)})
            parent = decision["next"]
        report["arms"][name] = graded
    report["retained"] = parent
    return report, captures


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--initial", type=Path, required=True)
    p = parser.parse_args()
    report, calls = collect(p.scratch, p.initial)
    (pilot.HERE / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    (pilot.HERE / "native-calls.json.gz").write_bytes(gzip.compress((json.dumps(calls, indent=2) + "\n").encode(), mtime=0))
