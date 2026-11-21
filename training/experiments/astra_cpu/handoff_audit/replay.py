"""Replay frozen policies on eight same-seed pairs. Sealed exam material is never read."""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
ARMS = ("before", "after")


def outcomes(path, seed, work):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    result = {}
    with ZipFile(path) as z:
        if work:
            pattern = rf"exam_{seed}_mixed/([ehc]{seed}_\d\d)/exam.json"
            for name in z.namelist():
                match = re.fullmatch(pattern, name)
                if match:
                    task_id = match[1]
                    row = json.loads(z.read(name))
                    assert row["id"] == task_id and type(row["ok"]) is bool and task_id not in result
                    # Compare prompt bytes for pair identity; no prompts, answers or outputs are exported.
                    task = z.read(name.removesuffix("exam.json") + "members/TASK.md")
                    result[task_id] = (hashlib.sha256(task).hexdigest(), row["ok"])
        else:
            doc = json.loads(z.read(f"{seed}_mixed.json"))
            assert doc["summary"]["seed"] == seed and doc["summary"]["tasks"] == 8
            for row in doc["tasks"]:
                task_id = row["id"]
                assert re.fullmatch(rf"[ehc]{seed}_\d\d", task_id)
                assert type(row["ok"]) is bool and task_id not in result
                result[task_id] = ((doc["summary"]["code"], row["task"], row["kind"]), row["ok"])
            assert doc["summary"]["passed"] == sum(grade for _, grade in result.values())
    assert len(result) == 8
    return result, digest


def collect(work, index, grades):
    runs = {}
    if index:
        for entry in json.loads(index.read_text()):
            arm, shard = entry["name"].split("-")[-2:]
            runs.setdefault(entry["generation"], {})[int(shard), arm] = (
                work / f"{entry['id']}.zip", True, entry["sha256"], entry["id"])
    for group in grades:
        generation, folder = group.split("=", 1)
        assert generation not in runs
        entries = json.loads((Path(folder) / "index.json").read_text())["archives"]
        runs[generation] = {}
        for source in entries:
            name = source["name"]
            _, arm, shard = name.split("-")
            runs[generation][int(shard), arm] = (
                Path(folder) / f"{name}.zip", False, source["digest"].removeprefix("sha256:"), source["id"])
    rows = {}
    for gen, files in sorted(runs.items()):
        rows[gen] = []
        for shard in range(1, 9):
            seed = 20_000_000 + int(gen.removeprefix("g")) * 10 + shard
            arms, sources = {}, {}
            for arm in ARMS:
                path, is_work, expected_hash, artifact_id = files[shard, arm]
                arms[arm], digest = outcomes(path, seed, is_work)
                assert expected_hash is None or expected_hash == digest
                sources[arm] = dict(sha256=digest, artifact=artifact_id or path.name)
            before, after = arms["before"], arms["after"]
            assert before.keys() == after.keys()
            matching = [k for k in before if before[k][0] == after[k][0]]
            wins = sum(after[k][1] and not before[k][1] for k in matching)
            losses = sum(before[k][1] and not after[k][1] for k in matching)
            rows[gen].append(dict(seed=seed, after=sum(x[1] for x in after.values()),
                                  before=sum(x[1] for x in before.values()), wins=wins, losses=losses,
                                  matched=len(matching), unmatched_ids=sorted(set(before) - set(matching)),
                                  sources=sources))
    return rows


def evaluate(rows):
    ret = {}
    for gen, seeds in rows.items():
        assert len(seeds) == 8
        if any(s["matched"] != 8 for s in seeds):
            ret[gen] = dict(excluded="arm task identities differ", matched=sum(s["matched"] for s in seeds))
            continue
        assert all(s["after"] - s["before"] == s["wins"] - s["losses"] for s in seeds)
        full_net = sum(s["wins"] - s["losses"] for s in seeds)
        full = full_net >= 0
        results = {}
        for rule in ("lr", "certain"):
            history = []
            for n in (4, 6, 8):
                prefix = seeds[:n]
                wins = sum(s["wins"] for s in prefix)
                losses = sum(s["losses"] for s in prefix)
                net = wins - losses
                left = (8 - n) * 8
                stop = (abs(net) * math.log(1.5) >= math.log(19) if rule == "lr"
                        else net >= left or net < -left)
                history.append(dict(seeds=n, wins=wins, losses=losses, net=net))
                if stop or n == 8:
                    break
            results[rule] = dict(seeds=n, keep=net >= 0, agrees=(net >= 0) == full,
                                 paired_tasks_saved=left, path=history)
        ret[gen] = dict(before=sum(s["before"] for s in seeds), after=sum(s["after"] for s in seeds),
                        full_fresh_keep=full, **results)
    return ret


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path)
    parser.add_argument("--index", type=Path)
    parser.add_argument("--grades", action="append", default=[], metavar="gNN=DIRECTORY")
    parser.add_argument("--ledger", type=Path, default=HERE / "paired.json")
    parser.add_argument("--out", type=Path, default=HERE / "results.json")
    args = parser.parse_args()
    if args.index or args.grades:
        ledger = collect(args.work, args.index, args.grades)
        args.ledger.write_text(json.dumps(ledger, indent=2) + "\n")
    args.out.write_text(json.dumps(evaluate(json.loads(args.ledger.read_text())), indent=2) + "\n")
