"""Collect immutable fits, model completions, grader decisions and realized exposures."""
import argparse
import gzip
import json
from pathlib import Path

from training.experiments.replay_archive.native_cycles import pilot


def collect(scratch):
    cases = pilot.load(pilot.HERE / "panel.json", pilot.PANEL_SHA)["rows"]
    parent = "release"
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
            report["transitions"].append({"fit": fit, "decision": decision})
            parent = decision["next"]
        report["arms"][name] = graded
    report["retained"] = parent
    return report, captures


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch", type=Path, required=True)
    p = parser.parse_args()
    report, calls = collect(p.scratch)
    (pilot.HERE / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    (pilot.HERE / "native-calls.json.gz").write_bytes(gzip.compress((json.dumps(calls, indent=2) + "\n").encode(), mtime=0))
