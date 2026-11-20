"""Run the shipped schedule command on only project inputs and validate each result independently."""
import argparse
import gzip
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here))
from checker import check

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--checkout", type=Path, required=True)
parser.add_argument("--out", type=Path, help="write the full CLI transcript and independent scores")
args = parser.parse_args()
cli = args.checkout.resolve() / "hive"
evidence = json.loads(gzip.decompress((here / "evidence.json.gz").read_bytes()))
cases = [(row["name"], row["input"]) for row in evidence["projects"]]
cases.append(("community_kitchen", json.loads((here/"example.json").read_text())))
rows = []
env = {**os.environ, "HIVE_BANK": "off", "HIVE_PYTHON": sys.executable, "HIVE_TERNARY_BIN": "/unavailable"}
with tempfile.TemporaryDirectory() as directory:
    # The CLI receives the numerical inputs and optional user labels only. The same
    # anonymous path is used for every project. Reference scores never enter its process.
    path = Path(directory) / "project.json"
    for name, project in cases:
        path.write_text(json.dumps(project))
        start = time.monotonic()
        call = subprocess.run([str(cli), "schedule", str(path)], env=env, cwd=directory,
                              capture_output=True, text=True, timeout=120, check=False)
        row = {"name": name, "exit": call.returncode, "stdout": call.stdout, "stderr": call.stderr,
               "seconds": round(time.monotonic() - start, 5)}
        if call.returncode:
            raise RuntimeError(f"{name} returned {call.returncode}: {call.stderr}")
        starts = json.loads(call.stdout)
        grade = check(project, {"value": starts})
        header = call.stderr.splitlines()[0] if call.stderr else ""
        receipt = re.fullmatch(r"Makespan (\d+)\. Winner (classical/[^\s.]+)\.", header)
        if not grade.get("feasible") or receipt is None or int(receipt[1]) != grade["makespan"]:
            raise ValueError(f"{name}: {grade}, {header}")
        row.update(grade=grade, winner=receipt[2], starts=starts)
        rows.append(row)
        print(name, grade["makespan"], receipt[2])
if args.out:
    args.out.write_text(json.dumps(rows, indent=2) + "\n")
