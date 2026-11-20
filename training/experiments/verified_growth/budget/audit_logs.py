"""Audit what ended every successful G51/G52 training slice."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import re
from statistics import median
import subprocess


HERE = Path(__file__).resolve().parent
KEEP = re.compile(r"^\S+ (?:\d+ rows, \d+ within|time is up after |every row has been |no row left fits|slice \d+ of \d+: |lessons kept back: )")
STEP = re.compile(r"^\S+ step \d+ \(\d+% done")


def fetch(snapshot):
    result = {}
    for generation in ("g51", "g52"):
        rows = []
        for job in snapshot["runs"][generation]["jobs"]:
            if job["name"].split(" (")[0] != "train" or job["conclusion"] != "success":
                continue
            text = subprocess.check_output(["gh", "api",
                f"repos/Arnav123-s/HiveMIND/actions/jobs/{job['id']}/logs"], text=True,
                encoding="utf-8-sig")
            steps = [line for line in text.splitlines() if STEP.search(line)]
            rows.append({"id": job["id"], "name": job["name"],
                         "lines": [line for line in text.splitlines() if KEEP.search(line)],
                         "last_five_step_log": steps[-1] if steps else None})
        result[generation] = rows
    return result


def summarize(snapshot, records, timeline):
    all_results = {}
    for generation, records_g in records.items():
        workers = {j["id"]: j for j in snapshot["runs"][generation]["jobs"] if
                   j["name"].split(" (")[0] == "train" and j["conclusion"] == "success"}
        if set(workers) != {r["id"] for r in records_g}:
            raise ValueError("logs must cover every successful training slice")
        gives = []
        for worker in records_g:
            raw = "\n".join(worker["lines"])
            n = int(re.search(r"time is up after (\d+) passes", raw)[1])
            used = int(re.search(r"\d+ rows, (\d+) within", raw)[1])
            check_s = int(re.search(r"rows measured in (\d+) s", raw)[1])
            # The end measure gets the first measure's duration as reserve in grow.train.
            finished_first_check = next(s for s in worker["lines"] if " lessons kept back: " in s).split(" ")[0]
            first = datetime.fromisoformat(finished_first_check).timestamp()
            job_start = datetime.fromisoformat(workers[worker["id"]]["started_at"]).timestamp()
            gives.append({"passes": n, "eligible": used, "passes_per_eligible": n/used, "check_s": check_s,
                          "reserve_and_start": first - job_start + check_s})
        possible = timeline[generation]["allowed_train_minutes_for_three_hours"]
        all_results[generation] = {
            "successful_log_count": len(gives), "ended_at_time_limit": len(gives),
            "passes_range": [min(r["passes"] for r in gives), max(r["passes"] for r in gives)],
            "eligible_range": [min(r["eligible"] for r in gives), max(r["eligible"] for r in gives)],
            "median_passes_per_eligible": round(median(r["passes_per_eligible"] for r in gives), 5),
            "fewer_passes_than_half_the_available_rows": sum(2*r["passes"] < r["eligible"] for r in gives),
            "median_initial_reference_check_min": round(median(r["check_s"] for r in gives)/60, 3),
            "median_setup_initial_check_and_equal_reserve_min": round(median(r["reserve_and_start"] for r in gives)/60, 3),
            "would_have_no_update_window_with_unchanged_setup_and_equal_reserve":
                sum(r["reserve_and_start"] > 60*possible for r in gives)}
    return all_results


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fetch", type=Path, help="save a fresh projection of GitHub job logs")
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    snap = json.loads((HERE/"jobs.json").read_text())
    logs = fetch(snap) if args.fetch else json.loads((HERE/"training-logs.json").read_text())
    if args.fetch:
        args.fetch.write_text(json.dumps(logs, indent=2) + "\n")
    report = summarize(snap, logs, json.loads((HERE/"timeline.json").read_text()))
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
