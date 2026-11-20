"""Summarize the first-call generation and independent two-arm grading receipts."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path


def summarize(raw_file, grade_file):
    native = json.loads(raw_file.read_bytes())
    grade = json.loads(grade_file.read_bytes())
    assert native.get("end_utc") and len({r["id"] for r in grade["rows"]}) == len(grade["rows"]) == 10
    calls = {r["id"]: r for r in native["calls"]}
    rates, cases = {}, []
    for arm in ("plain", "delivered"):
        counts = Counter()
        for record in grade["rows"]:
            passed = record[arm]["passed"]
            counts["unavailable" if passed is None else "correct" if passed else "incorrect"] += 1
        rates[arm] = dict(counts)
    returned = [row for row in calls.values() if row["state"] == "returned"]
    for g in grade["rows"]:
        row = calls.get(g["id"], {})
        cases.append({"id": g["id"], "maker": g["maker"], "state": row.get("state", "no_call"),
                      "finish": row.get("finish_reason"), "tokens": row.get("usage", {}).get("completion_tokens", 0),
                      "files": sorted(g["products"]), "plain_ok": g["plain"]["passed"],
                      "delivered_ok": g["delivered"]["passed"], "wall_s": row.get("wall_s")})
    return {"native_sha256": sha256(raw_file.read_bytes()).hexdigest(), "grades_sha256": sha256(grade_file.read_bytes()).hexdigest(),
            "represented_families": len({r["maker"] for r in grade["rows"]}), "score_counts": rates,
            "returned": len(returned), "stops": dict(Counter(row["finish_reason"] for row in returned)),
            "jobs_with_requested_files": sum(bool(r["requested"]) for r in grade["rows"]),
            "jobs_materialized": sum(bool(g["products"]) for g in grade["rows"]),
            "paired_gains": sum(r["plain"]["passed"] is False and r["delivered"]["passed"] is True for r in grade["rows"]),
            "paired_losses": sum(r["plain"]["passed"] is True and r["delivered"]["passed"] is False for r in grade["rows"]),
            "prompt_tokens": sum(row["usage"]["prompt_tokens"] for row in returned),
            "output_tokens": sum(row["usage"]["completion_tokens"] for row in returned),
            "server_cpu_s": round(sum(row["server_cpu_s"] or 0 for row in calls.values()), 3),
            "calls_wall_s": round(sum(row["wall_s"] for row in calls.values()), 3), "cases": cases}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--receipts", required=True, type=Path)
    p.add_argument("--grades", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    obj = summarize(args.receipts, args.grades)
    args.out.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")
    print({k: v for k, v in obj.items() if k != "cases"})
