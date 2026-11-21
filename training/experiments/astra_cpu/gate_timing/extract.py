"""Extract durations from unmodified Actions jobs JSON and grade ZIPs. Omit prompts and answers."""
import argparse
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import re
from zipfile import ZipFile


def utc(value):
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())


def stamp(rows):
    return sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def extract(folder):
    index = json.loads((folder / "index.json").read_text())
    artifacts = {r["name"]: r for r in index["archives"]}
    jobs_doc = json.loads((folder / "jobs.json").read_text())
    jobs = jobs_doc["jobs"]
    assert len(jobs) == jobs_doc["total_count"]
    gates = [j for j in jobs if j["name"].startswith("gate (")]
    assert len(gates) == 33
    zero = min(utc(j["started_at"]) for j in gates)
    # The replay may use original occupancy; policy can observe past job starts and releases only.
    upstream = [[j["name"].split(" ")[0], utc(j["started_at"]) - zero, utc(j["completed_at"]) - zero]
                for j in jobs if j["name"].split(" ")[0] in {"train", "join", "merge", "bench"}
                and j["conclusion"] != "skipped"]
    seats, grades, seen = {}, {}, set()
    for j in gates:
        arm, digit, part = re.fullmatch(r"gate \((before|after), ([1-8]), (fresh|held|talk)\)", j["name"]).groups()
        key = f"{part}-{arm}-{digit}"
        start, finish = utc(j["started_at"]) - zero, utc(j["completed_at"]) - zero
        d = seats[key] = dict(start=start, elapsed=finish-start)
        if part == "talk":
            continue
        name = ("gate" if part == "fresh" else "held") + f"-{arm}-{digit}"
        archive = folder / (name + ".zip")
        a = artifacts[name]
        assert len(archive.read_bytes()) == a["size_in_bytes"]
        assert sha256(archive.read_bytes()).hexdigest() == a["digest"].removeprefix("sha256:")
        with ZipFile(archive) as z:
            fn, = z.namelist()
            doc = json.loads(z.read(fn))
        tasks = doc["tasks"]
        assert doc["summary"]["tasks"] == len(tasks) and doc["summary"]["passed"] == sum(r["ok"] for r in tasks)
        assert all(type(r["seconds"]) is int and r["seconds"] > 0 and type(r["ok"]) is bool for r in tasks)
        for i, row in enumerate(tasks):
            identity = (arm, part, row["id"])
            assert identity not in seen
            seen.add(identity)
            grades[(part, digit, i, arm)] = (row["id"], row["ok"])
        step, = [s for s in j["steps"] if s["conclusion"] != "skipped" and s["name"].startswith(
            "A fresh exam" if part == "fresh" else "The fixed held-out exam")]
        s0, s1 = utc(step["started_at"]) - zero, utc(step["completed_at"]) - zero
        d.update(pre=s0-start, post=finish-s1, seconds=[r["seconds"] for r in tasks],
                 residual=s1-s0-sum(r["seconds"] for r in tasks))
    # Membership comparison consumes grades only for the historical early-stop baseline.
    looks = []
    for seats_done in (4, 6):
        delta = 0
        for seat in range(1, seats_done+1):
            for i in range(8):
                b, a = [grades[("fresh", str(seat), i, arm)] for arm in ("before", "after")]
                assert b[0] == a[0]
                delta += int(a[1]) - int(b[1])
        looks.append(delta)
    train = [j for j in jobs if j["name"].startswith("train (")]
    straggler = max(utc(j["completed_at"]) for j in train) - max(
        utc(j["completed_at"]) for j in train if j["conclusion"] == "success")
    return dict(run=index["run"], upstream=sorted(upstream), seats=seats, paired_net_gains=looks,
                cancelled_slice_tail=straggler,
                grade_set_sha256=stamp(sorted((list(k),v) for k,v in grades.items())),
                jobs_sha256=sha256((folder / "jobs.json").read_bytes()).hexdigest(),
                archives_sha256=stamp(sorted((a["id"],a["digest"]) for a in artifacts.values())))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    p.add_argument("out", type=Path)
    args = p.parse_args()
    rows = {gen:extract(args.root / gen) for gen in ("g53", "g54", "g55", "g56")}
    args.out.write_text(json.dumps(rows, sort_keys=True, separators=(",", ":")) + "\n")
