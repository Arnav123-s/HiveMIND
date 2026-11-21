"""Score official F3 paired artifacts after downloading them by their original names."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

from training import exam
from training.grow_record import kind_passed

ARMS = ("stock", "f3")
INDEX = "6379846f333435ea1818a5821822b208f26d28da13a4f3ff4fb69983647418e6"


def read_artifact(path, name, limit=1_000_000):
    """Read a known short receipt from an unpacked artifact or from its zip."""
    if path.is_dir():
        with (path / name).open("rb") as f:
            data = f.read(limit + 1)
    else:
        with ZipFile(path) as archive, archive.open(name) as f:
            data = f.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"oversized {path.name}/{name}")
    return data


def collect(folder, allow_through):
    fixed = exam.held_exam()
    requests = {tid: task for tid, _, _, task, _ in fixed}
    manifest = Path(__file__).with_name("g55-contemporaneous.sha256").read_bytes()
    raw = {arm: {} for arm in ARMS}
    runs, digests, notes = set(), set(), []
    for arm in ARMS:
        flag = "1" if arm == "f3" else "0"
        for seat in range(1, 9):
            # A rerun can cover only failed shards. Use the latest supplied attempt of each, up to the requested cap.
            artifact = None
            for attempt in range(allow_through, 0, -1):
                stem = f"f3-{arm}-{seat}-attempt-{attempt}"
                paths = [p for p in [folder / stem, folder / (stem + ".zip")] if p.exists()]
                if len(paths) > 1:
                    raise ValueError(f"both zip and folder provided for {stem}")
                if paths:
                    artifact = paths[0]
                    break
            if artifact is None:
                notes.append({"arm": arm, "shard": seat, "status": "artifact missing"})
                continue
            try:
                assignment = json.loads(read_artifact(artifact, "assignment.json"))
                required = {"ARM": arm, "SHARD": str(seat), "AGENT_TEAM_SOLO": "2", "HIVE_ASSERT_FIRST": flag,
                            "HIVE_PAGE_CHECKS": flag, "HIVE_HTTP_CACHE": flag}
                if any(assignment.get(k) != v for k, v in required.items()):
                    raise ValueError(f"wrong arm, shard or settings in {artifact.name}")
                if read_artifact(artifact, "familiar-index.sha256").decode().split()[0] != INDEX:
                    raise ValueError(f"wrong G55 history in {artifact.name}")
                if not assignment.get("GITHUB_RUN_ID") or not assignment.get("GITHUB_SHA") or not assignment.get("HIVE_MEMBERS"):
                    raise ValueError(f"missing run identity in {artifact.name}")
                runs.add((assignment["GITHUB_RUN_ID"], assignment["GITHUB_SHA"], assignment["HIVE_MEMBERS"]))
                if read_artifact(artifact, "adapters.sha256") != manifest:
                    raise ValueError(f"wrong G55 adapter manifest in {artifact.name}")
                digests.add(hashlib.sha256(read_artifact(artifact, "roster.sha256")).hexdigest())
                receipt = json.loads(read_artifact(artifact, f"held_{seat}.json"))
            except (FileNotFoundError, KeyError):
                notes.append({"arm": arm, "shard": seat, "attempt": attempt, "status": "incomplete artifact"})
                continue
            if receipt.get("summary", {}).get("exam") != "held" or receipt["summary"].get("seat") != seat:
                raise ValueError(f"wrong official exam in {artifact.name}")
            expected = {row[0] for row in exam.held_share(fixed, seat, 8)}
            received = set()
            for row in receipt["tasks"]:
                tid = row["id"]
                if (tid not in expected or tid in received or row["task"] != requests[tid] or type(row["ok"]) is not bool
                        or tid.rsplit("_", 1)[0] != "x_" + row["maker"]):
                    raise ValueError(f"unexpected, malformed or duplicate task in {artifact.name}")
                received.add(tid)
                raw[arm][tid] = row
            notes.append({"arm": arm, "shard": seat, "attempt": attempt,
                          "reported": len(received), "missing": sorted(expected - received)})
    if len(runs) > 1 or len(digests) > 1:
        raise ValueError("shards differ in workflow run, code, body or member order")
    common = sorted(set(raw["stock"]) & set(raw["f3"]))
    correct = {arm: {tid for tid in common if raw[arm][tid]["ok"]} for arm in ARMS}
    by_kind = {}
    for arm in ARMS:
        grouped = Counter(raw[arm][tid]["maker"] for tid in common)
        right = Counter(raw[arm][tid]["maker"] for tid in correct[arm])
        by_kind[arm] = {k: [right[k], grouped[k]] for k in sorted(grouped)}
    gained, lost = (sorted(correct[a] - correct[b]) for a, b in (("f3", "stock"), ("stock", "f3")))
    complete = set(common) == set(requests)
    run = dict(zip(("id", "sha", "members"), next(iter(runs)))) if runs else None
    return {"run": run, "complete": complete, "expected": len(fixed), "paired": len(common),
            "observed_by_arm": {arm: len(rows) for arm, rows in raw.items()},
            "right_on_paired": {arm: len(correct[arm]) for arm in ARMS},
            "missing": {arm: sorted(set(requests) - set(rows)) for arm, rows in raw.items()},
            "gained": gained, "lost": lost, "net": len(gained) - len(lost),
            "at_least_four_more": len(gained) - len(lost) >= 4 if complete else None,
            "right_and_total_by_kind": by_kind,
            "kinds_passing_of_ten": {arm: sum(kind_passed(*r) for r in by_kind[arm].values())
                                    if complete else None for arm in ARMS},
            "live_failures": {arm: {tid: {"note": raw[arm][tid].get("note"), "reason": raw[arm][tid].get("why")}
                                   for tid in common if raw[arm][tid]["maker"] in {"h_quotes", "h_two"}
                                   and tid not in correct[arm]} for arm in ARMS},
            "shards": notes}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("folder", type=Path)
    p.add_argument("--through-attempt", type=int, default=1)
    args = p.parse_args()
    if not 1 <= args.through_attempt <= 100:
        p.error("--through-attempt must be between 1 and 100")
    print(json.dumps(collect(args.folder, args.through_attempt), indent=2))
