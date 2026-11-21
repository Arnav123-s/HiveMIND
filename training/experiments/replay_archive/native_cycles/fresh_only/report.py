"""Collect the three fresh-only controls and validate them against the pinned mixed arms."""
import argparse
import gzip
import json
from pathlib import Path

from training.experiments.replay_archive.native_cycles import pilot
from training.experiments.replay_archive.native_cycles.fresh_only.freeze import HERE
from training.experiments.replay_archive.native_cycles.report import tensor_change


def read(path):
    return json.loads(path.read_text())


def runtime_flags(calls):
    flags = list(calls["flags"])
    flags[flags.index("--port") + 1] = "<ephemeral>"
    return flags


def collect(scratch, original, initial):
    assert pilot.native.digest(initial) == pilot.START_SHA
    manifest = pilot.load(HERE / "manifest.json", pilot.CONTROL_SHA)
    mixed = read(pilot.HERE / "results.json")
    mixed_calls = json.loads(gzip.decompress((pilot.HERE / "native-calls.json.gz").read_bytes()))
    assert read(scratch / "release-grades.json") == mixed["arms"]["release"]
    assert read(scratch / "release-calls.json") == mixed_calls["release"]
    assert mixed["panel_sha256"] == manifest["panel_sha256"] == pilot.PANEL_SHA
    report = dict(panel_sha256=pilot.PANEL_SHA, manifest_sha256=pilot.CONTROL_SHA,
                  retained_parent_sha256=pilot.START_SHA, comparisons=[])
    captures = {}
    for i, (stage, old) in enumerate(zip(manifest["stages"], mixed["transitions"], strict=True), 1):
        name = f"cycle-{i}"
        grades = read(scratch / (name+"-grades.json"))
        fit = read(scratch / (name+"-fit.json"))
        decision = read(scratch / (name+"-decision.json"))
        raw = read(scratch / (name+"-calls.json"))
        captures[name] = raw
        baseline = mixed_calls[name]
        assert all(raw[k] == baseline[k] for k in ("panel_sha256", "model_sha256", "runtime_sha256", "sampling", "complete"))
        assert runtime_flags(raw) == runtime_flags(baseline) and raw["affinity"] == baseline["affinity"]
        assert raw["complete"] and len(raw["calls"]) == 5
        assert [c["name"] for c in raw["calls"]] == [c["name"] for c in baseline["calls"]]
        assert raw["lora_sha256"] == fit["gguf_sha256"] == grades["lora_sha256"]
        assert decision["parent"] == old["decision"]["parent"] == "release"
        assert fit["parent_trainable_sha256"] == old["fit"]["parent_trainable_sha256"] == pilot.START_SHA
        assert fit["optimizer_order"] == stage["optimizer_order"] and len(set(fit["optimizer_order"])) == 3
        assert fit["meta"]["steps"] == old["fit"]["meta"]["steps"] == 3
        assert fit["meta"]["new_rows"] == fit["meta"]["passes"] == fit["meta"]["used"] == 3
        assert "self_replay" not in fit["meta"] and fit["meta"]["memory"]["rows_skipped"] == 0
        assert fit["meta"]["rows_by_kind"] and sum(r["trained"] for r in fit["meta"]["rows_by_kind"].values()) == 3
        rel = Path(name) / "grow" / ("t80+retention"+str(i)) / "adapter_model.safetensors"
        fresh_weights, mixed_weights = scratch / rel, original / rel
        assert pilot.native.digest(fresh_weights) == fit["trainable_sha256"]
        assert pilot.native.digest(mixed_weights) == old["fit"]["trainable_sha256"]
        shared = stage["shared_answer_total"]
        fresh_cost = [sum(r[k] for r in shared) + stage["fresh_answer_total"][k] for k in (0, 1)]
        mixed_cost = [sum(r[k] for r in shared) + stage["old_answer_total"][k] for k in (0, 1)]
        assert mixed_cost[0] == sum(old["fit"]["meta"]["self_replay"]["answer_tokens"].values())
        siblings = mixed["arms"][name]["results"]
        changed = [k for k, r in grades["results"].items() if r["program_sha256"] != siblings[k]["program_sha256"]]
        flips = [k for k, r in grades["results"].items() if r["passed"] != siblings[k]["passed"]]
        report["comparisons"].append(dict(family=stage["family"], fresh_only_fit=fit, fresh_only_decision=decision,
                fresh_only_grades=grades, mixed_decision=old["decision"], changed_first_programs=changed,
                changed_whole_task_grades=flips, same_two_anchors=all(grades["results"][k]["passed"] == siblings[k]["passed"]
                    for k in ("m_percent","m_weekday")), mixed_answer_total_tokens=mixed_cost,
                fresh_answer_total_tokens=fresh_cost, fresh_inference_seconds=sum(c["wall_seconds"] for c in raw["calls"]),
                mixed_inference_seconds=sum(c["wall_seconds"] for c in baseline["calls"]),
                parent_to_fresh=tensor_change(initial, fresh_weights), mixed_to_fresh=tensor_change(mixed_weights,fresh_weights)))
    (HERE / "results.json").write_text(json.dumps(report,indent=2) + "\n")
    (HERE / "native-calls.json.gz").write_bytes(gzip.compress((json.dumps(captures,indent=2)+"\n").encode(),mtime=0))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for k in ("scratch", "original", "initial"):
        p.add_argument("--"+k, type=Path, required=True)
    a=p.parse_args()
    collect(a.scratch, a.original, a.initial)
