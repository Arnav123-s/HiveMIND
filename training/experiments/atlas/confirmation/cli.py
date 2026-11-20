"""Run one fixed confirmation job at each shipping terminal entry point."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def run(sdk):
    panel = {c["id"]: c for c in json.loads((HERE / "shipping.json").read_text())}
    bank = ROOT / "training/reports/retained-skills/shipping/bank"
    results = []
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        env = os.environ | {"HIVE_PYTHON": sys.executable, "HIVE_BANK": str(bank),
                            "HIVE_FIELDWORK_SDK": str(sdk.resolve()), "HIVE_ROLES": "0",
                            "HIVE_TERNARY_BIN": str(tmp / "no-model"), "AGENT_TEAM_HOME": str(tmp / "state")}
        for surface, ident in (("opt-in", "light-pair"), ("default", "plain-control")):
            case = panel[ident]
            if surface == "opt-in":
                command = [sys.executable, "-m", "training.experiments.atlas.traces.demo", "--sdk", str(sdk),
                           "--bank", str(bank), "--sibling-bank", str(tmp / "branches"), "answer", case["message"]]
            else:
                command = ["./hive", "--local", "--once", case["message"]]
            proc = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=90, check=True)
            if surface == "opt-in":
                answer = json.loads(proc.stdout)["answer"]["value"]
            else:
                answer = int(proc.stdout.splitlines()[0].strip())
            assert case["per_bank"] == answer, (surface, proc.stdout)
            results.append(dict(surface=surface, id=ident, prompt=case["message"], expected=case["per_bank"],
                                answer=answer, exit=proc.returncode, stdout=proc.stdout, stderr=proc.stderr))
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.write_text(json.dumps(run(args.sdk), indent=2) + "\n")
