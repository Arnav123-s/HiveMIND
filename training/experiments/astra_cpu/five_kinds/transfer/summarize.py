"""Pair first attempts by their frozen question, with strict and diagnostic outcomes."""
import argparse
import hashlib
import json
from pathlib import Path


def summarize(native, assessments):
    arms = ("parent", "five")
    names = [r["name"] for r in native["parent"]["calls"]]
    by_name = {}
    totals = {}
    for arm in arms:
        n, a = native[arm], assessments[arm]
        if not n["complete"] or n["arm"] != a["arm"] or n["arm"] != arm:
            raise ValueError("wrong or incomplete arm")
        assert n["panel_sha256"] == a["panel_sha256"]
        assert [r["name"] for r in n["calls"]] == [r["name"] for r in a["graded"]] == names
        totals[arm] = {"full_pass": sum(x["full_pass"] for x in a["graded"]),
                       "emitted_module": sum(bool(x["file_sha256"]) for x in a["graded"]),
                       "program_exit_ok": sum(x["program_exit_ok"] for x in a["graded"]),
                       "public_values_ok": sum(x["public_values_ok"] for x in a["graded"]),
                       "hidden_passed": sum(x["hidden_passed"] for x in a["graded"]),
                       "hidden_total": sum(x["hidden_total"] for x in a["graded"]),
                       "truncations": sum(x["finish_reason"] == "length" for x in n["calls"]),
                       "generated_tokens": sum(x["usage"]["completion_tokens"] for x in n["calls"]),
                       "inference_seconds": round(sum(x["wall_seconds"] for x in n["calls"]), 3)}
        for attempt, grade in zip(n["calls"], a["graded"]):
            by_name.setdefault(grade["name"], {})[arm] = {
                "full_pass": grade["full_pass"], "public_values_ok": grade["public_values_ok"],
                "hidden": [grade["hidden_passed"], grade["hidden_total"]],
                "module_source": grade["module_source"], "reason": grade.get("reason"),
                "generated_tokens": attempt["usage"]["completion_tokens"],
                "finish_reason": attempt["finish_reason"], "raw_sha256": hashlib.sha256(attempt["text"].encode()).hexdigest(),
            }
    assert native["parent"]["panel_sha256"] == native["five"]["panel_sha256"]
    assert native["parent"]["sampling"] == native["five"]["sampling"]
    assert native["parent"]["model_sha256"] == native["five"]["model_sha256"]
    assert native["parent"]["runtime_sha256"] == native["five"]["runtime_sha256"]
    assert native["parent"]["lora_sha256"] != native["five"]["lora_sha256"]
    return {
        "panel_sha256": native["parent"]["panel_sha256"], "totals": totals, "pairs": by_name,
        "gains": [name for name, p in by_name.items() if p["five"]["full_pass"] and not p["parent"]["full_pass"]],
        "losses": [name for name, p in by_name.items() if p["parent"]["full_pass"] and not p["five"]["full_pass"]],
        "identical_responses": [name for name,p in by_name.items() if p["parent"]["raw_sha256"] == p["five"]["raw_sha256"]],
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--directory", type=Path, required=True)
    a = p.parse_args()
    def load(pattern):
        return {arm: json.loads((a.directory / pattern.format(arm=arm)).read_bytes()) for arm in ("parent","five")}
    print(json.dumps(summarize(load("native-{arm}.json"), load("grades-{arm}.json")), indent=2))
