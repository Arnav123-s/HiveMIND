"""Reconstruct the training barrier and its contribution to recorded generation time."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
from statistics import median
import subprocess


HERE = Path(__file__).resolve().parent
REPO = "Arnav123-s/HiveMIND"
RUNS = {"g51": 44525337919, "g52": 44594712108, "g53": 44649281647}


def capture(local=None):
    runs = {}
    for generation, run in RUNS.items():
        if local:
            lines = (local / f"jobs-{run}.jsonl").read_text().splitlines()
        else:
            result = subprocess.check_output(
                ["gh", "api", f"repos/{REPO}/actions/runs/{run}/jobs?per_page=100",
                 "--paginate", "--jq", ".jobs[]"], text=True)
            lines = result.splitlines()
        jobs = []
        for line in lines:
            source = json.loads(line)
            # A workflow can synthesize a skipped bench without timestamps or a hosted runner.
            if source["conclusion"] == "skipped":
                continue
            row = {k: source[k] for k in ("id", "name", "status", "conclusion", "started_at", "completed_at")}
            row["grow"] = next(({k: s[k] for k in ("started_at", "completed_at", "conclusion")}
                                for s in source["steps"] if s["name"] == "Grow the cell"), None)
            jobs.append(row)
        runs[generation] = {"id": run, "jobs": jobs}
    finished = max((local / f"jobs-{run}.jsonl").stat().st_mtime for run in RUNS.values()) if local else datetime.now(timezone.utc).timestamp()
    return {"retrieved_utc": datetime.fromtimestamp(finished, timezone.utc).isoformat(timespec="seconds"), "runs": runs}


def timestamp(value):
    return datetime.fromisoformat(value).timestamp()


def minutes(seconds):
    return round(seconds / 60, 3)


def details(run):
    jobs = run["jobs"]
    phases = {}
    for item in jobs:
        phases.setdefault(item["name"].partition(" (")[0], []).append(item)
    result = {"job_counts": {k: dict(Counter(j["status"] for j in group)) for k, group in phases.items()}}
    training = phases["train"]
    result["train_outcomes"] = dict(Counter(j["conclusion"] or j["status"] for j in training))
    spans = {}
    for k, group in phases.items():
        if all(j["completed_at"] and j["started_at"] for j in group):
            spans[k] = minutes(max(timestamp(j["completed_at"]) for j in group) -
                               min(timestamp(j["started_at"]) for j in group))
    result["completed_stage_minutes"] = spans
    if "record" not in spans:
        return result
    end = max(timestamp(j["completed_at"]) for j in jobs)
    start = min(timestamp(j["started_at"]) for j in jobs)
    begin_train = min(timestamp(j["started_at"]) for j in training)
    end_train = max(timestamp(j["completed_at"]) for j in training)
    span = end_train - begin_train
    outside = end - start - span
    gate_start = min(timestamp(j["started_at"]) for j in phases["gate"])
    gate_end = max(timestamp(j["completed_at"]) for j in phases["gate"])
    result["nonoverlapping_wall_minutes"] = {
        "preparation": minutes(begin_train - start),
        "training": minutes(span),
        "join_merge_wait": minutes(gate_start - end_train),
        "complete_gate": minutes(gate_end - gate_start),
        "finish": minutes(end - gate_end),
    }
    events = []
    for j in training:
        grow = j["grow"]
        duration = None
        if grow and grow["completed_at"] and grow["started_at"]:
            duration = timestamp(grow["completed_at"]) - timestamp(grow["started_at"])
        events.append((timestamp(j["completed_at"]), j["conclusion"] == "success", duration))
    successful = [e for e in events if e[1]]
    # In the second scenario only the successfully timed Grow segment shrinks, leaving measured
    # starts, job overhead, failures, and subsequent barrier-to-record elapsed time intact.
    projected_end = max(t - (d / 2 if ok and d is not None else 0) for t, ok, d in events)
    last_good = max(t for t, _, _ in successful)
    critical = max(training, key=lambda j: j["completed_at"])
    result.update({
        "actual_minutes": minutes(end - start), "outside_train_minutes": minutes(outside),
        "train_span_minutes": minutes(span), "allowed_train_minutes_for_three_hours": minutes(10800 - outside),
        "if_whole_train_span_halved_minutes": minutes(outside + span / 2),
        "if_successful_grow_steps_halved_minutes": minutes(outside + projected_end - begin_train),
        "if_failures_report_by_last_success_minutes": minutes(outside + last_good - begin_train),
        "if_successful_grow_steps_halved_and_failures_report_by_last_success_minutes":
            minutes(outside + max(t - d / 2 for t, ok, d in successful if d is not None) - begin_train),
        "last_to_finish": {"name": critical["name"], "id": critical["id"], "conclusion": critical["conclusion"]},
        "last_success_to_last_job_minutes": minutes(end_train - last_good),
        "successful_grow_duration_minutes": {
            "median": minutes(median(d for _, _, d in successful if d is not None)),
            "minimum": minutes(min(d for _, _, d in successful if d is not None)),
            "maximum": minutes(max(d for _, _, d in successful if d is not None)),
        }
    })
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, help="write a current public GitHub snapshot")
    parser.add_argument("--from-local", type=Path, help="capture saved gh --jq '.jobs[]' files")
    parser.add_argument("--input", type=Path, default=HERE / "jobs.json")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.capture:
        snapshot = capture(args.from_local)
        args.capture.write_text(json.dumps(snapshot, indent=2) + "\n")
    else:
        snapshot = json.loads(args.input.read_text())
    summary = {k: details(r) for k, r in snapshot["runs"].items()}
    args.out.write_text(json.dumps(summary, indent=2) + "\n")
    for generation, row in summary.items():
        print(generation, {k: v for k, v in row.items() if "minutes" in k and not isinstance(v, dict)})
