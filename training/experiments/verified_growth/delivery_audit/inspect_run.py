"""Read original archived worker scripts/logs and replay the normal post-worker handoff, without model calls."""
import argparse
from contextlib import ExitStack, redirect_stdout
from hashlib import sha256
import io
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
from zipfile import ZipFile

from team import deliverables, domain_route, engram, solo

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SOURCE = ROOT / "training/experiments/atlas/module_recovery"
ARTIFACTS = ROOT / "training/experiments/atlas/pulse/artifacts.json"
CASES = (("h20000523_03", 14587903855), ("h20000527_03", 14587642648))


def digest(data):
    return sha256(data).hexdigest()


def run_handoff(task, workers):
    """Replay after generation, retaining actual publication, inspection, quorum and copy behavior."""
    names = list(deliverables.wanted(task))
    def recorded(task, n, board, guard, work, temperature, who, also):
        out, program = workers[n - 1]
        work.mkdir(parents=True, exist_ok=True)
        if program:
            solo.module(task, program, work, board, n)
        return {"answer": out, "program": program or "", "turns": [], "who": who, "also": []}
    with tempfile.TemporaryDirectory() as tmp, ExitStack() as cm:
        home = Path(tmp)
        # Freeze at the historical three-seat budget and replay the recorded responses.
        # The later reserve-seat system would generate unseen outputs without this cap.
        cm.enter_context(patch.object(solo, "member", side_effect=recorded))
        cm.enter_context(patch.object(solo.ternary, "seating", return_value=["replay-1","replay-2","replay-3"]))
        cm.enter_context(patch.object(solo, "extra_seat", return_value=False))
        cm.enter_context(patch.object(solo, "keep"))
        cm.enter_context(patch.object(engram, "for_request", return_value=[]))
        cm.enter_context(patch.object(domain_route, "prepare_advice"))
        cm.enter_context(redirect_stdout(io.StringIO()))
        out = solo.first(task, home, members=2)
        data = json.loads((home/"members/members.json").read_bytes())
        held = []
        for idx in range(1, out["tries"] + 1):
            obj = json.loads((home/f"members/member{idx}.json").read_bytes())
            base = Path(obj["work"])
            held.append(dict(seat=idx, answer=obj["answer"], issues=obj["delivery"]["issues"],
                             byte_hashes=obj["delivery"]["byte_hashes"],
                             files=[name for name in names if (base/name).is_file()]))
        published = {name:digest((home/"work"/name).read_bytes()) for name in names if (home/"work"/name).is_file()}
        return dict(members=held, selected=data["selected_member"], agreed=out["agreed"],
                    returned_files=out["files"], published=published,
                    evidence_in_public_report=out["report"].strip(), report_points_to_third="member 3" in out["report"].casefold())


def original(archives, task_id, artifact):
    filename = archives / f"{artifact}.zip"
    manifest = next(r for r in json.loads(ARTIFACTS.read_text()) if r["id"] == artifact)
    actual_hash = digest(filename.read_bytes())
    if actual_hash != manifest["sha256"]:
        raise ValueError("archive hash mismatch")
    with ZipFile(filename) as z:
        prefix = next(n[:-len("TASK.md")] for n in z.namelist() if n.endswith(f"/{task_id}/members/TASK.md"))
        entries = [s[len(prefix):] for s in z.namelist() if s.startswith(prefix)]
        task = z.read(prefix+"TASK.md").decode().strip()
        candidates = []
        raw_out = z.read(prefix+"member3/.member3_2.py.out").decode().strip()
        successful_program = z.read(prefix+"member3/member3_2.py").decode()
        for row in z.read(prefix+"events.jsonl").decode().splitlines():
            event = json.loads(row)
            if event["kind"] in ("module","answer","same-error"):
                candidates.append([event["agent"],event["kind"],event["msg"]])
        # No hidden verdict, answer key, or manually authored duration test is supplied to solo.
        result = run_handoff(task, [("",None), ("",None), (raw_out,successful_program)])
        grade = json.loads(z.read(prefix.removesuffix("members/")+"exam.json"))
        observed_report = z.read(prefix+"REPORT.md").decode().strip()
    expected = digest((SOURCE/"g52"/task_id/"durations.py").read_bytes())
    assert result["members"][2]["byte_hashes"] == {"durations.py":expected}
    assert result["evidence_in_public_report"] == observed_report
    return dict(id=task_id, artifact=artifact, archive_sha256=actual_hash, original_events=candidates,
                archive_contains_named_file=any(n.endswith("/durations.py") for n in entries),
                archive_contains_member_manifests=any(n=="member3.json" for n in entries),
                archived_successful_script_sha256=digest(successful_program.encode()),
                reproduction=result, existing_writer_matches_atlas_bytes=expected,
                later_exam_evidence=dict(release=grade["ok"],why=grade["why"],members=grade["members"]))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archives", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    original_cases = [original(args.archives, task, artifact) for task,artifact in CASES]
    task = "Write a Python module and save it as scale.py. Define scale(x) to return twice x. Print scale(0)."
    correct = "def scale(x):\n    return 2 * x\n"
    wrong = "def scale(x):\n    return 0\n"
    controls = {
        "wrong_lone_program": run_handoff(task,[("",None),("",None),("0",wrong)]),
        "same_stdout_distinct_modules": run_handoff(task,[("0",wrong),("0",correct)]),
        "same_correct_program": run_handoff(task,[("0",correct),("0",correct)])
    }
    wrong_hash = digest(wrong.encode())
    assert not controls["wrong_lone_program"]["agreed"]
    assert controls["same_stdout_distinct_modules"]["published"] == {"scale.py":wrong_hash}
    assert controls["same_correct_program"]["published"] == {"scale.py":digest(correct.encode())}
    doc = dict(original_code="136e8880243a533299448fe8505ef08194d5bd18", jobs=original_cases,
               controls=controls, wrong_program=wrong, correct_program=correct)
    args.out.write_text(json.dumps(doc,indent=2)+"\n")


if __name__ == "__main__":
    main()
