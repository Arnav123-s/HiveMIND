"""Compare the frozen F3 stock arm with the separately dispatched F4 child exam."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

import yaml

from training import exam
from training.grow_record import kind_passed
from .paired import paired_scores, read_arm, read_artifact

STOCK_SHA = "ac77ff328406b4404de205c4ce62266ac0b181b8"
PARENT = "72913f1c566638f2177574178f1d6925cde956a92b35af06795e7598c5729036"
STUDY = "training/experiments/astra_orders/worker_contracts"
TRUNK = "cells/members/t80+g55trunk.gguf"
ROSTER_HASHES = (
    b"754046ea66667e06ef6aae21e03799a5a708ebc88af78edf5ef14c49e06bcb88  cells/body.json\n"
    b"bf3d8e5660e66c6600628b755f1166d27c18ff5456013aabda570fd537a673d4  cells/studied.json\n"
)


def check_workflows(stock, child):
    """Bind settings omitted by the receipts, including the command and time limits."""
    a, b = (workflow["jobs"]["exam"] for workflow in (stock, child))
    flags = {key: "0" for key in ("HIVE_ASSERT_FIRST", "HIVE_PAGE_CHECKS", "HIVE_HTTP_CACHE")}
    expected_env = a["env"] | flags | {"ARM": "child"}
    expected_matrix = {key: value for key, value in a["strategy"]["matrix"].items() if key != "mode"}
    expected_strategy = a["strategy"] | {"matrix": expected_matrix}
    step_name = "Run this shard of the normal fixed held-out exam"
    exams = [[s for s in job["steps"] if s.get("name") == step_name] for job in (a, b)]
    actions = [[s.get("uses") for s in job["steps"] if "uses" in s] for job in (a, b)]
    if (b["env"] != expected_env or b["strategy"] != expected_strategy
            or len(exams[0]) != 1 or exams[1] != exams[0] or actions[1] != actions[0]
            or len(b["steps"]) != len(a["steps"]) or b["steps"][:3] != a["steps"][:3]
            or b.get("runs-on") != a.get("runs-on") or b.get("timeout-minutes") != a.get("timeout-minutes")
            or stock.get("env") != child.get("env") or a.get("defaults") != b.get("defaults")
            or stock.get("defaults") != child.get("defaults")):
        raise ValueError("F4 worker settings, setup or official exam command differ from the frozen control")


def load_registration(child_sha):
    """Read trusted config from the dispatched Git object, independent of the receipts."""
    if not re.fullmatch("[0-9a-f]{40}", child_sha) or child_sha == STOCK_SHA:
        raise ValueError("expected the separately dispatched F4 workflow commit")
    repo = Path(__file__).resolve().parents[4]
    git = ["git", "-C", str(repo)]
    identity = subprocess.check_output([*git, "rev-parse", "--verify", f"{child_sha}^{{commit}}"], text=True).strip()
    if identity != child_sha:
        raise ValueError("F4 workflow SHA must be a commit")
    unchanged = ["team", "training/exam.py", "training/hive_bench.py", "training/kinds",
                 "training/lineage.py", "training/grow_record.py", ".github/actions/hive", "cells",
                 f"{STUDY}/g55-contemporaneous.sha256", f"{STUDY}/g55-checked-task-texts.json.gz"]
    subprocess.run([*git, "diff", "--exit-code", "--quiet", STOCK_SHA, child_sha, "--", *unchanged], check=True)
    workflows = [yaml.safe_load(subprocess.check_output([*git, "show", f"{sha}:.github/workflows/exam.yml"]))
                 for sha in (STOCK_SHA, child_sha)]
    check_workflows(*workflows)
    blob = subprocess.check_output([*git, "show", f"{child_sha}:{STUDY}/f4-adapter.json"])
    return json.loads(blob)


def child_manifest(stock, registration):
    expected = {"parent_sha256": PARENT, "stock_workflow_sha": STOCK_SHA, "file": "t80-hint-dream.gguf"}
    if not isinstance(registration, dict) or any(registration.get(k) != v for k, v in expected.items()):
        raise ValueError("registration differs from the frozen G55 parent")
    child = registration.get("sha256")
    ref = registration.get("source_ref")
    if not isinstance(child, str) or not re.fullmatch("[0-9a-f]{64}", child) or child == PARENT:
        raise ValueError("registration must name the fitted child adapter digest")
    if not isinstance(ref, str) or not re.fullmatch("[0-9a-f]{40}", ref):
        raise ValueError("registration must pin the immutable adapter source commit")
    original = f"{PARENT}  {TRUNK}\n".encode()
    if stock.splitlines(keepends=True).count(original) != 1:
        raise ValueError("registered parent missing from the frozen G55 manifest")
    return stock.replace(original, f"{child}  {TRUNK}\n".encode(), 1)


def collect(folder, allow_through, stock_run, child_run, child_sha):
    if not (1 <= allow_through <= 100):
        raise ValueError("through-attempt must be between 1 and 100")
    if stock_run == child_run or any(not re.fullmatch("[1-9][0-9]*", r) for r in (stock_run, child_run)):
        raise ValueError("provide the distinct stock and child run IDs from the dispatch records")
    registration = load_registration(child_sha)
    stock = Path(__file__).with_name("g55-contemporaneous.sha256").read_bytes()
    child = child_manifest(stock, registration)
    roster = ",".join(Path(line.split()[1]).stem for line in stock.decode().splitlines())
    runs = {"stock": {"id": stock_run, "sha": STOCK_SHA, "members": roster},
            "child": {"id": child_run, "sha": child_sha, "members": roster}}

    def validate(artifact, assignment):
        arm = assignment["ARM"]
        if (assignment.get("GITHUB_RUN_ID") != runs[arm]["id"]
                or assignment.get("GITHUB_SHA") != runs[arm]["sha"]
                or assignment.get("machine") != "x86_64"):
            raise ValueError(f"wrong hosted run, code or machine in {artifact.name}")
        if read_artifact(artifact, "roster.sha256") != ROSTER_HASHES:
            raise ValueError(f"wrong frozen G55 roster bytes in {artifact.name}")
        expected = stock if arm == "stock" else child
        if read_artifact(artifact, "adapters.sha256") != expected:
            raise ValueError(f"wrong {arm} adapter manifest in {artifact.name}")
        if arm == "child":
            if json.loads(read_artifact(artifact, "f4-adapter.json")) != registration:
                raise ValueError(f"wrong registered F4 adapter in {artifact.name}")
            name = f"held_{assignment['SHARD']}.json"
            digest = hashlib.sha256(read_artifact(artifact, name)).hexdigest()
            if read_artifact(artifact, "held.sha256") != f"{digest}  {name}\n".encode():
                raise ValueError(f"wrong official grade checksum in {artifact.name}")

    fixed = exam.held_exam()
    raw, notes = {}, []
    for arm, prefix in (("stock", "f3"), ("child", "f4")):
        raw[arm], shards = read_arm(folder, allow_through, arm, prefix, "0", fixed, roster, validate)
        notes.extend(shards)
    result = paired_scores(fixed, raw)
    gained_kinds = lost_kinds = None
    if result["complete"]:
        passing = {arm: {k for k, counts in kinds.items() if kind_passed(*counts)}
                   for arm, kinds in result["right_and_total_by_kind"].items()}
        gained_kinds = sorted(passing["child"] - passing["stock"])
        lost_kinds = sorted(passing["stock"] - passing["child"])
    kind_counts = result["kinds_passing_of_ten"]
    return {"runs": runs, "registration": registration, **result, "gained_kinds": gained_kinds,
            "lost_kinds": lost_kinds, "net_kinds": kind_counts["child"] - kind_counts["stock"] if result["complete"] else None,
            "child_at_least_two_kinds": kind_counts["child"] >= 2 if result["complete"] else None, "shards": notes}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("folder", type=Path)
    p.add_argument("--stock-run", required=True)
    p.add_argument("--child-run", required=True)
    p.add_argument("--child-sha", required=True, help="full F4 workflow commit present in the local Git repository")
    p.add_argument("--through-attempt", type=int, default=1)
    args = p.parse_args()
    print(json.dumps(collect(args.folder, args.through_attempt, args.stock_run, args.child_run, args.child_sha), indent=2))
