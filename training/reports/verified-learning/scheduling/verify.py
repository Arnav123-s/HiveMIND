"""Re-run archived model programs on every public and benchmark case, and recheck the baselines."""
import argparse
import gzip
import json
from pathlib import Path
import sys

from checker import check

here = Path(__file__).resolve().parent
p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--checkout", type=Path, required=True)
p.add_argument("--sdk", type=Path, required=True)
args = p.parse_args()
sys.path.insert(0, str(args.checkout))
from training.experiments.fieldwork.guest import Guest

evidence = json.loads(gzip.decompress((here / "evidence.json.gz").read_bytes()))
guest = Guest(args.sdk)
counts = {"public": 0, "benchmark": 0, "classical": 0}

def replay(source, project, recorded):
    rows, _, _ = guest.run(source, [project], fuel=30_000_000_000)
    if rows[0] != recorded["guest"] or check(project, rows[0]) != recorded["checked"]:
        raise ValueError("Different guest output or schedule validity from release")

for t in evidence["generations"]:
    for example, observed in zip(evidence["public"]["examples"], t["public"], strict=True):
        replay(t["source"], example["input"], observed)
        counts["public"] += 1
for project, sample in zip(evidence["projects"], evidence["scores"], strict=True):
    assert project["name"] == sample["name"]
    for policy, target in project["policies"].items():
        result = check(project["input"], {"value": target["starts"]})
        assert result == {"feasible": True, "makespan": sample["baselines"][policy]}
        counts["classical"] += 1
    for t, recorded in zip(evidence["generations"], sample["attempts"], strict=True):
        replay(t["source"], project["input"], recorded)
        counts["benchmark"] += 1
    selection = evidence["public_selection"]["selected_attempt"]
    if selection is not None:
        assert sample["delivery"] == sample["attempts"][selection - 1]["checked"]
    else:
        assert sample["delivery"] == {"feasible": False, "reason": "no qualified public solver"}
rescue = evidence["rescue"]
counts["rescue_public"] = 0
counts["rescue_benchmark"] = 0
for candidate in rescue["checked_candidates"]:
    for ex, check_row in zip(evidence["public"]["examples"], candidate["public"], strict=True):
        replay(candidate["source"], ex["input"], check_row)
        counts["rescue_public"] += 1
for project, outcome in zip(evidence["projects"], evidence["rescue_scores"], strict=True):
    if rescue["selected"]:
        replay(rescue["selected"]["program"], project["input"], outcome["result"])
        counts["rescue_benchmark"] += 1
    else:
        assert outcome["result"] is None
print(json.dumps(counts))
