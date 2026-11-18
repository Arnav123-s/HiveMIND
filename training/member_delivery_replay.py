"""Verify a member-versus-delivery report against hash-pinned GitHub Actions grade archives.

    python -m training.member_delivery_replay
    python -m training.member_delivery_replay --archives /path/to/grade-zips

With no archive directory, use the GitHub CLI to download the listed ZIP files into a temporary directory.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from zipfile import ZipFile

from training import grow_record

DEFAULT = Path(__file__).resolve().parent / "reports" / "checked-delivery" / "g47-headroom.json"


def recount(manifest, archives, extracted):
    details = {"before": [], "after": []}
    for spec in manifest["grade_archives"]:
        name = spec["name"]
        path = archives / (name + ".zip")
        contents = path.read_bytes()
        if hashlib.sha256(contents).hexdigest() != spec["sha256"]:
            raise ValueError(f"{name}: SHA-256 mismatch")
        with ZipFile(path) as archive:
            files = [f for f in archive.infolist() if f.filename.endswith("_mixed.json")]
            if len(files) != 1 or files[0].file_size > 2_000_000:
                raise ValueError(f"{name}: expected one small mixed-exam grade JSON")
            raw = archive.read(files[0])
        group = name.split("-")[1]
        folder = extracted / name
        folder.mkdir()
        (folder / Path(files[0].filename).name).write_bytes(raw)
        for task in json.loads(raw)["tasks"]:
            if task.get("ok") is not False or not task["id"].startswith("h"):
                continue
            outcome = grow_record.member_delivery_outcome(task)
            details[group].append({"id": task["id"], "kind": task["kind"], "outcome": outcome,
                                   "passing_members": [m["who"] for m in task["members"] if m["ok"] is True],
                                   "failing_members": [m["who"] for m in task["members"] if m["ok"] is False],
                                   "delivery_finding": task["why"][:200],
                                   "final_answer": task["answer"][:180] if outcome == "member_only" else None})
    arms, seeds = grow_record.paired(extracted)
    if len(seeds) != 8 or len(manifest["grade_archives"]) != 2 * len(seeds):
        raise ValueError("Expected all eight paired seeds")
    results = {}
    for name in ("before", "after"):
        arm = arms[name]
        missing = sorted(details[name], key=lambda d: d["id"])
        results[name] = {"tasks": arm["tasks"], "passed": arm["passed"], "hard": arm["hard"],
                         "member_delivery": arm["member_delivery"], "hard_delivery_failures": missing,
                         "hard_failed_without_a_passing_member_by_kind":
                             dict(sorted(Counter(d["kind"] for d in missing if d["outcome"] == "neither").items()))}
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT)
    parser.add_argument("--archives", type=Path)
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        archives = args.archives or folder
        if args.archives is None:
            for a in report["grade_archives"]:
                with (folder / (a["name"] + ".zip")).open("wb") as f:
                    subprocess.run(["gh", "api", f"repos/{report['repo']}/actions/artifacts/{a['id']}/zip"],
                                   stdout=f, check=True)
        results = recount(report, archives, folder)
    if results != report["results"]:
        raise ValueError("The recorded report disagrees with the grade archives")
    for arm, data in results.items():
        print(arm, json.dumps(data["member_delivery"]))
    print(f"Verified {len(report['grade_archives'])} archive hashes and both recorded outcomes.")


if __name__ == "__main__":
    main()
