"""Replay primary programs, self-retry, and supplementary large-integer checks in WASI."""
import argparse
import gzip
import json
from pathlib import Path
import sys

here = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--checkout", required=True, type=Path)
parser.add_argument("--sdk", required=True, type=Path)
args = parser.parse_args()
sys.path.insert(0, str(args.checkout))
from training.experiments.fieldwork.guest import Guest

evidence = json.loads(gzip.decompress((here / "evidence.json.gz").read_bytes()))
guest = Guest(args.sdk)

def verify(source, checks):
    rows, _, _ = guest.run(source, [r["input"] for r in checks], fuel=30_000_000_000)
    if len(rows) != len(checks):
        raise RuntimeError("Guest returned the wrong result count")
    for row, check in zip(rows, checks):
        right = type(row.get("value")) is int and row["value"] == check["expected"]
        if row != check["actual"] or right != check["correct"]:
            raise RuntimeError(f"Replay mismatch on input {check['input']}")
    return len(checks)

counts = {"primary": 0, "self_retry": 0, "large_integer": 0}
for records in evidence["attempts"].values():
    for record in records:
        for split in ("public", "validation", "fresh"):
            counts["primary"] += verify(record["source"], record[split])
for checks in evidence["self_retry"]["scores"].values():
    counts["self_retry"] += verify(evidence["self_retry"]["source"], checks)
for task, cases in evidence["large_integer"].items():
    for record, case in zip(evidence["attempts"][task], cases):
        counts["large_integer"] += verify(record["source"], case["cases"])
print(json.dumps(counts))
