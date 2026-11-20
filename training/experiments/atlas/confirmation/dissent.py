"""Score a frozen, controlled set of proposed answers through the actual Atlas decision entry point."""
import argparse
from collections import Counter, defaultdict
from pathlib import Path
import hashlib
import json
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from training.experiments.atlas.dissent import study
from training.experiments.fieldwork.guest import Guest

EXPECTED = {"study.py": "33a473755962b4f6f30e0206cd4f7b94c6e289f6c55607d54888dfabc02ea7f0",
            "verifier.py": "574e834ecc8abd74cb1030a2184f345a716ceb72439c9b7a47e13223eeb75b30",
            "PROTOCOL.md": "7cc501ade0b6253cb7bf166fbe3303c1320dd29bfec060a3e7e4ac856920d7d7"}


def same(answer, key):
    if answer is None or key is None:
        return False
    value = str(answer).strip()
    return value.lower() == key if key in ("yes", "no") else value == key


def score(sdk):
    panel = json.loads((HERE / "dissent.json").read_text())
    guest = Guest(sdk)
    for name, expected in EXPECTED.items():
        assert hashlib.sha256((HERE.parent / "dissent" / name).read_bytes()).hexdigest() == expected
    policies = {}
    for policy in ("current", "diverse", "verified", "reordered"):
        rows = []
        groups = defaultdict(Counter)
        for case in panel:
            began = time.monotonic()
            result = study.decide(case["task"], case["replies"], policy, guest)
            seconds = round(time.monotonic() - began, 5)
            output = result.get("answer")
            if case["gold"] is None:
                verdict = "justified_abstention" if output is None else "unjustified"
            elif output is None:
                verdict = "missed"
            else:
                verdict = "correct" if same(output, case["gold"]) else "wrong"
            check = result.get("check") or {}
            for key in ("all", case["group"]):
                c = groups[key]
                c[verdict] += 1
                c["seats"] += len(result["seats"])
                c["questions_with_check"] += bool(check)
                c["guest_calls"] += check.get("calls", 0)
                c["wrong_checked_releases"] += bool(check and output is not None and verdict != "correct")
            rows.append(dict(id=case["id"], gold=case["gold"], group=case["group"], verdict=verdict,
                             seconds=seconds, **result))
        policies[policy] = {"counts": dict(groups), "rows": rows}
    return {"implementation_sha256": EXPECTED, "model_generations": 0, "results": policies}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.write_text(json.dumps(score(args.sdk), indent=2) + "\n")
