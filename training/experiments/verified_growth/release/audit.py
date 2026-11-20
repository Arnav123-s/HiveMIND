"""Rebuild the fixed-exam receipts from the archived after/before worker folders."""
import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
PULSE = HERE.parent.parent / "atlas/pulse"
ARMS = tuple(f"g{n}-{arm}" for n in (50, 51, 52) for arm in ("before", "after"))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def collect(folder):
    manifest = json.loads((PULSE / "artifacts.json").read_text())
    snapshots = {arm: {} for arm in ARMS}
    prompts = {}
    g52_wrong = []
    for source in manifest:
        _, _, which, _ = source["name"].split("-")
        arm = source["generation"] + "-" + which
        archive = folder / f"{source['id']}.zip"
        assert digest(archive.read_bytes()) == source["sha256"]
        with ZipFile(archive) as z:
            for item in sorted(z.namelist()):
                if not item.endswith("/exam.json"):
                    continue
                raw = z.read(item)
                data = json.loads(raw)
                job = data["id"]
                prefix = item.removesuffix("exam.json")
                members = data["members"]
                if job.startswith("x_"):
                    task_hash = digest(z.read(prefix + "members/TASK.md").strip())
                    assert prompts.setdefault(job, task_hash) == task_hash
                    assert job not in snapshots[arm]
                    prefix_answer = data["answer"].strip().casefold()
                    withheld = not prefix_answer or prefix_answer.startswith(("not confirmed", "no member"))
                    snapshots[arm][job] = {
                        "delivered": data["ok"], "status": "withheld" if withheld else "delivered",
                        "members": members, "artifact": source["id"],
                        "exam_sha256": digest(raw),
                    }
                elif arm == "g52-after" and not data["ok"]:
                    report_path = prefix + "REPORT.md"
                    report = z.read(report_path).decode() if report_path in z.namelist() else ""
                    # The actual published report contains declared agreement. Exclude withheld jobs.
                    if "## How it was checked" in report and (
                        "two of them agreed" in report or "two gave the same values" in report
                    ):
                        g52_wrong.append({
                            "id": job, "artifact": source["id"], "exam_sha256": digest(raw),
                            "report_sha256": digest(report.encode()), "report": report,
                            "original_prompt": z.read(prefix + "members/TASK.md").decode().strip(),
                            "official_reason": data["why"], "members": members,
                        })
    assert len(prompts) == 30 and all(set(s) == set(prompts) for s in snapshots.values())
    assert len(g52_wrong) == 2
    return {"manifest_sha256": digest((PULSE / "artifacts.json").read_bytes()), "prompt_sha256": prompts,
            "snapshots": snapshots, "g52_wrong_pulse": g52_wrong}


def score(flags):
    grouped = defaultdict(list)
    for ident, success in flags.items():
        grouped[ident.rsplit("_", 1)[0].removeprefix("x_")].append(success)
    assert len(grouped) == 10 and all(len(rows) == 3 for rows in grouped.values())
    counts = {kind: sum(values) for kind, values in sorted(grouped.items())}
    return {"tasks": sum(counts.values()), "kinds": sum(n >= 2 for n in counts.values()), "by_kind": counts}


def minimum_new(ceiling):
    """Optimistically assign new successes to the five closest families."""
    return sum(sorted(max(0, 2 - n) for n in ceiling["by_kind"].values())[:5])


def summarize(ledger):
    ever = defaultdict(bool)
    summaries = {}
    for arm in ARMS:
        snap = ledger["snapshots"][arm]
        delivered = {job: row["delivered"] for job, row in snap.items()}
        candidates = {job: any(m["ok"] for m in row["members"]) for job, row in snap.items()}
        union = {job: delivered[job] or candidates[job] for job in snap}
        for job, value in union.items():
            ever[job] |= value
        summaries[arm] = {
            "original_counts": dict(Counter("correct" if row["delivered"] else
                                             "wrong" if row["status"] == "delivered" else "withheld"
                                             for row in snap.values())),
            "delivery": score(delivered), "recorded_worker": score(candidates), "either": score(union),
            "minimum_extra_task_successes_for_five_kinds": minimum_new(score(union)),
            "no_member_verdict": [k for k, v in snap.items() if not v["members"]],
            "unselected_correct": sorted(k for k, v in candidates.items() if v and not delivered[k]),
            "verdict_count": sum(len(v["members"]) for v in snap.values()),
        }
    availability = score(ever)
    # Minimum number of extra task successes, assuming every existing success is selected perfectly.
    return {"arms": summaries, "history_oracle": availability, "minimum_additional_successes_for_target":
            minimum_new(availability), "g52_wrong_pulse": [r["id"] for r in ledger["g52_wrong_pulse"]]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archives", type=Path, help="verify and rebuild from ZIPs named by artifact ID")
    parser.add_argument("--write-ledger", type=Path, help="optional destination for the reconstructed ledger")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    ledger = collect(args.archives) if args.archives else json.loads((HERE / "ledger.json").read_text())
    if args.write_ledger:
        args.write_ledger.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n")
    result = summarize(ledger)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    for arm, r in result["arms"].items():
        print(arm, {k: (r[k]["tasks"], r[k]["kinds"]) for k in ("delivery", "recorded_worker", "either")})
    print("All available answers", result["history_oracle"])


if __name__ == "__main__":
    main()
