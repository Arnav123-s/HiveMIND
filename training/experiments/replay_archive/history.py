"""Matched retrospective of archived paired sittings. All results stay outside the live archive."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZipFile

from team.ternary import organ
from training import body_archive, self_replay


def test_generation(folder):
    seen = set()
    useful = set()
    counts = Counter()
    hashes = {}
    pair = None
    for seat in range(1, 9):
        sides = {}
        for arm in ("before", "after"):
            path = folder / f"gate-{arm}-{seat}.zip"
            if not path.is_file():
                return None
            hashes[path.name] = sha256(path.read_bytes()).hexdigest()
            with ZipFile(path) as z:
                name, = z.namelist()
                sides[arm] = {r["id"]: r for r in json.loads(z.read(name))["tasks"]}
        for key in sorted(sides["after"].keys() & sides["before"].keys()):
            before, after = sides["before"][key], sides["after"][key]
            q = self_replay.question(after["task"])
            if q != self_replay.question(before["task"]) or q in seen:
                continue
            def checked(row, num):
                entries = [x for x in row.get("members", []) if x.get("member") == num and type(x.get("ok")) is bool]
                return entries[0] if len(entries) == 1 else {}
            prior, primary, secondary = checked(before, 1), checked(after, 1), checked(after, 2)
            if not all(body_archive.TRUNK.fullmatch(x.get("who", "")) for x in (prior, primary)) or not secondary:
                continue
            actors = (primary["who"], prior["who"])
            if pair and pair != actors:
                raise ValueError("trunk or primary changed within a matched pair")
            pair = actors
            if actors[0] == actors[1]:
                continue
            o = organ(after["task"])
            seen.add(q)
            if seat <= 4:
                counts["development"] += 1
                if prior["ok"] and not primary["ok"]:
                    useful.add(o)
                continue
            routed = o in useful
            second = prior["ok"] if routed else secondary["ok"]
            counts["reserved"] += 1
            counts["routed"] += routed
            counts["primary_correct"] += primary["ok"]
            counts["default_pair_any"] += primary["ok"] or secondary["ok"]
            counts["routed_pair_any"] += primary["ok"] or second
            counts["gained_union"] += second and not primary["ok"] and not secondary["ok"]
            counts["lost_union"] += secondary["ok"] and not second and not primary["ok"]
            counts["actual_delivery"] += after["ok"]
    return dict(pair=pair, useful_organs=sorted(useful), counts=dict(counts), sha256=hashes)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    a = p.parse_args()
    kept = {r["generation"] for r in map(json.loads, (body_archive.ROOT / "training/reports/generations.jsonl").read_text().splitlines()) if r["kept"]}
    records = {f.name: r for f in sorted(a.root.iterdir()) if f.name in kept and (r := test_generation(f))}
    print(json.dumps(dict(generations=records, totals=dict(sum((Counter(r["counts"]) for r in records.values()), Counter()))), indent=2))
