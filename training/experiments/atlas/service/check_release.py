"""Run both frozen panels through the shipped CLI in separate, single-CPU processes."""
import argparse
from collections import Counter
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

from training.experiments.atlas.service.judge.run import invoke, match


HERE = Path(__file__).resolve().parent
MODULE = "training.experiments.atlas.service.ask"


def check(sdk):
    env = os.environ | {"HF_HUB_OFFLINE": "1", "OPENBLAS_NUM_THREADS": "1", "RAYON_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"}
    cpu = {min(os.sched_getaffinity(0))}
    bank = HERE.parents[2] / "reports/retained-skills/shipping/bank"
    command = [sys.executable, "-m", MODULE, "--sdk", str(sdk.resolve()), "--bank", str(bank), "--json"]
    result = {"service_sha256": sha256((HERE / "ask.py").read_bytes()).hexdigest(), "panels": {}}
    for panel_name in ("judge", "wording_eval"):
        directory = HERE / panel_name
        cases = json.loads((directory / "panel.json").read_bytes())
        keys = json.loads((directory / "keys.json").read_bytes())
        records = []
        for case in cases:
            key = keys[case["id"]]
            trial = invoke(command + [case["question"]], env, cpu)
            if trial["exit"] not in (0, 1):
                raise ValueError(f"CLI failed on {case['id']}: {trial}")
            response = json.loads(trial["stdout"])
            if key["value"] is None:
                verdict = "withheld" if trial["exit"] == 1 and response["value"] is None else "wrong"
            elif trial["exit"] == 1:
                verdict = "missed"
            else:
                expected = dict(key)
                expected.setdefault("unit", "weekday" if isinstance(key["value"], str) else "days")
                okay = match(response["value"], response["unit"], expected)
                verdict = "correct" if okay and response["status"] == "answered" else "wrong"
            records.append({"id": case["id"], "response": response, "verdict": verdict, "exit": trial["exit"],
                            "seconds": trial["seconds"]})
        result["panels"][panel_name] = {
            "panel_sha256": sha256((directory / "panel.json").read_bytes()).hexdigest(),
            "keys_sha256": sha256((directory / "keys.json").read_bytes()).hexdigest(),
            "counts": dict(Counter(r["verdict"] for r in records)), "rows": records,
        }
        print(panel_name, result["panels"][panel_name]["counts"], flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.write_text(json.dumps(check(args.sdk), indent=2, ensure_ascii=False) + "\n")
