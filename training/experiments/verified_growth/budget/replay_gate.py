"""Simulate separating preserved exam work on 20 runners using actual step durations."""
import argparse
from datetime import datetime
import heapq
import json
import re
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
RUNS = {"g51": 44525337919, "g52": 44594712108}


def secs(x):
    return datetime.fromisoformat(x).timestamp()


def collect(local=None):
    records = {}
    for g, run in RUNS.items():
        if local:
            jsonl = (local / f"jobs-{run}.jsonl").read_text()
        else:
            jsonl = subprocess.check_output(["gh","api",f"repos/Arnav123-s/HiveMIND/actions/runs/{run}/jobs?per_page=100",
                                             "--paginate","--jq",".jobs[]"], text=True)
        group = []
        for line in jsonl.splitlines():
            j = json.loads(line)
            if not j["name"].startswith("gate ("):
                continue
            tasks = {}
            for kind, text in (("fresh", "A fresh exam,"), ("held", "The fixed held-out exam,"),
                               ("talk", "The talk exam ("), ("smoke", "Three plain messages,")):
                step = next(s for s in j["steps"] if s["name"].startswith(text))
                if step["conclusion"] == "success":
                    tasks[kind] = {"start":step["started_at"],"end":step["completed_at"]}
            group.append({"job":j["name"], "id":j["id"], "start":j["started_at"],"end":j["completed_at"],
                          "steps":tasks})
        assert len(group) == 16
        records[g] = group
    return records


def pieces(jobs):
    work = {}
    for row in jobs:
        name = row["job"]
        span = secs(row["end"]) - secs(row["start"])
        measured = {k: secs(s["end"])-secs(s["start"]) for k,s in row["steps"].items()}
        overhead = span - sum(measured.values())
        assert overhead >= 0
        work[name + "/fresh"] = overhead + measured["fresh"] + measured.get("smoke", 0)
        work[name + "/held"] = overhead + measured["held"]
        if "talk" in measured:
            work[name + "/talk"] = overhead + measured["talk"]
    return work


def simulate(work, order, count=20):
    ends = [(0, i) for i in range(count)]
    finish = 0
    for name in order:
        t, runner = heapq.heappop(ends)
        finish = max(finish, t+work[name])
        heapq.heappush(ends, (t+work[name], runner))
    return round(finish/60, 3)


def compare(records):
    previous = None
    result = {}
    for g, raw in records.items():
        work = pieces(raw)
        baseline = max(secs(j["end"]) for j in raw) - min(secs(j["start"]) for j in raw)
        split_order = sorted(work, key=lambda k: (k.split("/")[-1] != "fresh", k))
        bound = max(max(work.values()), sum(work.values())/20)
        row = {
            "original_gate_min": round(baseline/60, 3), "retained_job_parts": len(work),
            "duplicated_fixed_costs_included": True, "runner_capacity": 20,
            "lower_bound_scheduling_only_min": round(bound/60, 3),
            "fixed_order_min": simulate(work, split_order),
            "current_length_oracle_order_min": simulate(work, sorted(work,key=lambda k:(-work[k],k))),
            "longest_part": max(work,key=work.get),
        }
        if previous is not None:
            assert set(previous) == set(work)
            row["previous_generation_order_min"] = simulate(work, sorted(work,key=lambda k:(-previous[k],k)))
        result[g] = row
        previous = work
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--capture", type=Path)
    p.add_argument("--from-local", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--next-order", type=Path,
                   help="export the complete matrix.include entries ordered by the last observed costs")
    args = p.parse_args()
    records = collect(args.from_local) if args.capture else json.loads((HERE/"gate-steps.json").read_text())
    if args.capture:
        args.capture.write_text(json.dumps(records, indent=2)+"\n")
    if args.next_order:
        latest = pieces(records[max(records, key=lambda name: int(name[1:]))])
        matrix = []
        for key in sorted(latest, key=lambda name: (-latest[name], name)):
            match = re.fullmatch(r"gate \((before|after), (\d+)\)/(fresh|held|talk)", key)
            if not match:
                raise ValueError(f"unrecognized gate part: {key}")
            matrix.append({"arm": match[1], "seed": int(match[2]), "part": match[3]})
        args.next_order.write_text(json.dumps(matrix, indent=2)+"\n")
    result = compare(records)
    args.out.write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result, indent=2))
