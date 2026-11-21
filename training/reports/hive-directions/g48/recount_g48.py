"""Recompute G48 member/delivery and paired-job counts from source archives. Python standard library only.

python recount_g48.py
python recount_g48.py --download  # GitHub CLI required; download and hash-check the original ZIPs
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import subprocess
from zipfile import ZipFile

HOME_DIR = Path(__file__).resolve().parent
REPORT = HOME_DIR / "g48-audit.json"
MANIFEST = HOME_DIR / "g48-manifest.json"


def read_arms(manifest, archive_dir, download):
    grade = defaultdict(dict)
    rosters = {}
    for a in manifest["archives"]:
        name = a["name"]
        path = archive_dir / (name + ".zip")
        if download:
            path.parent.mkdir(exist_ok=True, parents=True)
            with path.open("wb") as f:
                subprocess.run(["gh", "api", f"repos/{manifest['repo']}/actions/artifacts/{a['id']}/zip"], stdout=f, check=True)
        data = path.read_bytes()
        if len(data) != a["bytes"] or hashlib.sha256(data).hexdigest() != a["sha256"]:
            raise ValueError(f"Bad source digest: {name}")
        with ZipFile(path) as z:
            entries = [f for f in z.infolist() if f.filename.endswith("_mixed.json")]
            if len(entries) != 1 or entries[0].file_size > 2_000_000:
                raise ValueError(f"Expected one mixed-exam grade file in {name}")
            sitting = json.loads(z.read(entries[0]))
        arm = name.split("-")[1]
        info = sitting["summary"]
        if not manifest["exam_commit"].startswith(info["code"]):
            raise ValueError(f"Unexpected exam revision in {name}")
        roster = info["members"].split(",")
        if rosters.setdefault(arm, roster) != roster:
            raise ValueError(f"Roster changed across seeds in {arm}")
        for t in sitting["tasks"]:
            tid = t["id"]
            if tid in grade[arm] or type(t["ok"]) is not bool:
                raise ValueError(f"Bad grade in {name}: {tid}")
            members = t["members"]
            if not members or any(type(m["ok"]) is not bool for m in members):
                raise ValueError(f"Incomplete member grades for {tid}")
            grade[arm][tid] = {"seed": info["seed"], "kind": t["kind"], "field": t["field"],
                              "prompt_sha256": hashlib.sha256(t["task"].encode()).hexdigest(),
                              "final": t["ok"], "finding": t["why"][:220],
                              "graded_members": [{"who": m["who"], "passed": m["ok"], "seat": m["member"]} for m in members],
                              "final_excerpt": t["answer"][:130] if not t["ok"] and any(m["ok"] for m in members) else None}
    return grade, rosters


def summarize(grade):
    joint = {s: dict.fromkeys(["both", "member_only", "delivery_only", "neither"], 0) for s in ("all", "hard", "easy")}
    workers = defaultdict(Counter)
    missed = []
    for tid, row in sorted(grade.items()):
        passing = [m["who"] for m in row["graded_members"] if m["passed"]]
        fin = row["final"]
        category = (("neither", "delivery_only"), ("member_only", "both"))[bool(passing)][fin]
        for s in ("all", "hard" if tid.startswith("h") else "easy"):
            joint[s][category] += 1
        if category == "member_only":
            missed.append({"id": tid, "kind": row["kind"], "passing": passing,
                           "finding": row["finding"], "final_excerpt": row["final_excerpt"]})
        for m in row["graded_members"]:
            c = workers[m["who"]]
            c["graded_seats"] += 1
            c["passed"] += int(m["passed"])
            c["passed_where_final_failed"] += int(m["passed"] and not fin)
            c["failed_where_final_passed"] += int(not m["passed"] and fin)
    return {"joint": joint, "workers": workers, "missed_correct_member": missed}


def compare(by_arm):
    old, new = by_arm["before"], by_arm["after"]
    if old.keys() != new.keys() or len(old) != 64:
        raise ValueError("Did not find the same 64 job IDs")
    paired = {s: dict.fromkeys(["both", "after_only", "before_only", "neither"], 0) for s in ("all", "hard", "easy")}
    trades = []
    for tid, b in sorted(old.items()):
        a = new[tid]
        if any(a[k] != b[k] for k in ("seed", "kind", "field", "prompt_sha256")):
            raise ValueError(f"Job identity changed for {tid}")
        state = (("neither", "after_only"), ("before_only", "both"))[b["final"]][a["final"]]
        for s in ("all", "hard" if tid.startswith("h") else "easy"):
            paired[s][state] += 1
        if b["final"] != a["final"]:
            trades.append({"id": tid, "kind": a["kind"], "passed": "after" if a["final"] else "before"})
    return {"outcomes": paired, "discordant_jobs": trades}


def run(directory, download=False):
    manifest = json.loads(MANIFEST.read_text())
    arms, rosters = read_arms(manifest, directory, download)
    return {"source_manifest": MANIFEST.name, "run": manifest["workflow_run"],
            "exam_commit": manifest["exam_commit"], "record_commit": manifest["record_commit"],
            "paired_deliveries": compare(arms), "by_arm": {k: summarize(v) for k, v in arms.items()},
            "listed_rosters": rosters, "job_grades": arms}


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--archives", type=Path, default=HOME_DIR / "g48-grade-zips")
    cli.add_argument("--download", action="store_true")
    cli.add_argument("--write", action="store_true")
    args = cli.parse_args()
    results = run(args.archives, args.download)
    text = json.dumps(results, sort_keys=True, indent=1) + "\n"
    if args.write:
        REPORT.write_text(text)
    elif text != REPORT.read_text():
        raise ValueError("Stored audit differs from source grade ZIPs")
    for arm, data in results["by_arm"].items():
        print(arm, data["joint"])
    print("paired", results["paired_deliveries"]["outcomes"])
