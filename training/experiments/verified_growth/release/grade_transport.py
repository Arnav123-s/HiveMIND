"""Grade the immutable post-audit inline transport receipts using the official 30 cases."""
import argparse
from collections import Counter
import json
from pathlib import Path

from score import HERE, digest, exam, grade, score


def compare(path):
    ledger = json.loads((HERE / "ledger.json").read_bytes())
    receipts = json.loads(path.read_bytes())
    questions = {q[0]: q for q in exam.held_exam()}
    prompts = {tid: digest(q[3].strip().encode()) for tid, q in questions.items()}
    assert prompts == ledger["prompt_sha256"]
    assert set(prompts.values()) == set(receipts["records"])
    outcomes = {}
    evaluated = {}
    for tid, key in sorted(prompts.items()):
        row = receipts["records"][key]
        evaluated[tid] = {method: grade(questions[tid], row[method], None) for method in ("rules", "bridged_rules")}
    for gen in ("g51", "g52"):
        old = ledger["snapshots"][gen + "-after"]
        original = {tid: "correct" if rec["delivered"] else "wrong" if rec["status"] == "delivered" else "withheld"
                    for tid, rec in old.items()}
        for method in ("rules", "bridged_rules"):
            combined = dict(original)
            solo = {}
            for tid, grades in evaluated.items():
                grading = grades[method]
                if grading["submitted"]:
                    combined[tid] = "correct" if grading["passed"] else "wrong"
                    solo[tid] = combined[tid]
                else:
                    solo[tid] = "withheld"
            outcomes[f"{gen}_{method}"] = {
                "solo": dict(Counter(solo.values())), "with_fallback": dict(Counter(combined.values())),
                "solo_scores": score({k: v == "correct" for k, v in solo.items()}),
                "paired_scores": score({k: v == "correct" for k, v in combined.items()}),
                "lost": [k for k in original if original[k] == "correct" and combined[k] != "correct"],
                "gained": [k for k in original if original[k] != "correct" and combined[k] == "correct"],
            }
    return {"sealed_receipts_sha256": digest(path.read_bytes()), "official_prompt_hashes_matched": len(prompts),
            "bound_inline_table": sum(row["bound"] for row in receipts["records"].values()),
            "outcomes": outcomes, "cases": evaluated}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = compare(args.decisions)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("Transport bound", result["bound_inline_table"], "of", result["official_prompt_hashes_matched"])
    for arm, value in result["outcomes"].items():
        print(arm, value["solo"], value["with_fallback"])
