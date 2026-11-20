"""Run the paired budget study through the ordinary grow.train entry point."""
from hashlib import sha256
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SOURCE = ROOT / "training/data/rows_g11_recovered.jsonl"
KINDS = ("days between two dates", "follow a form to the letter")


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def inputs(arm):
    groups = {kind: {} for kind in KINDS}
    for line in SOURCE.read_text().splitlines():
        row = json.loads(line)
        if row["kind"] in groups and row["type"] == "first" and len(row["output"]) < 300:
            groups[row["kind"]].setdefault(row["task"], row)
    rows = []
    for kind, count in zip(KINDS, (3, 5), strict=True):
        ordered = sorted(groups[kind].items(), key=lambda p: sha256(p[0].encode()).digest())
        assert len(ordered) > count
        rows.extend(r for _, r in ordered[:2 if arm == "half" else count])
        rows.append(dict(ordered[-1][1], who="lesson"))
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("arm", choices=("half", "full"))
    p.add_argument("--scratch", required=True, type=Path)
    p.add_argument("--result", required=True, type=Path)
    args = p.parse_args()
    args.scratch.mkdir(parents=True, exist_ok=False)
    rows = inputs(args.arm)
    rowfile = args.scratch / "rows.jsonl"
    rowfile.write_text("".join(json.dumps(r) + "\n" for r in rows))
    sys.path.insert(0, str(ROOT))
    os.environ["AGENT_TEAM_THREADS"] = "2"
    os.environ["HIVE_GPU"] = "0"
    os.environ["HIVE_KEEP_BACK"] = "1"
    from training import grow
    grow.GROW = args.scratch / "grow"
    start = time.monotonic()
    meta = grow.train(rowfile, name="budgetstudy", base="t80", epochs=1, rank=16,
                      max_len=512, layers="last14", accum=4, seed=53, lean="words", checkpoint=False,
                      int8_base=True, read=0, judged=0, out_dir=args.scratch / "exports")
    elapsed = time.monotonic() - start
    if meta["passes"] != len(rows) - 2 or meta["used"] != len(rows) - 2:
        raise ValueError(f"unexpected trained size: {meta['used']}, {meta['passes']}, {len(rows)-2}")
    adapter = Path(meta.pop("file"))
    result = dict(arm=args.arm, source_sha256=digest(SOURCE), script_sha256=digest(HERE / "slice_bench.py"),
                  corpus_sha256=digest(rowfile), task_hashes=[sha256(r["task"].encode()).hexdigest() for r in rows],
                  measured="grow.train through GGUF export, imports of its training dependencies included",
                  elapsed_seconds=round(elapsed, 3), adapter_sha256=digest(adapter), meta=meta)
    args.result.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
