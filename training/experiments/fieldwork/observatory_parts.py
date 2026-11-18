"""Test two model-written members with a supplied intermediate type on a fresh observatory work order."""

import argparse
import csv
import io
import random
from contextlib import nullcontext
from pathlib import Path

from .campaign import save, tool_source
from .guest import Guest
from .native import generate, server
from .observatory import files, inspect_delivery, specs
from .work import load_bank, work


COVERAGE = """Write solve(x) for an observatory. Input has window [lo,hi], positive quorum and records [instrument,start,end]. Return sorted maximal half-open [start,end] intervals inside the window where at least quorum DISTINCT instruments observe simultaneously. A single instrument may have overlapping, touching, or duplicate records. Join adjacent qualifying intervals even if instruments change. Ignore empty intervals. Up to 60,000 records and trillion-sized time coordinates. Use an efficient algorithm independent of the time range. Return only the interval list."""
RENDER = """Read a list of sorted disjoint [start,end] integer coverage intervals. Return two file texts in a dict. 'coverage.csv' has a start,end header, intervals in order, and a final newline. 'audit.json' has covered (sum of lengths) and longest ([start,end] of the longest interval, earliest on ties, or null if empty)."""


def intervals(example):
    rows = csv.reader(io.StringIO(example["output"]["coverage.csv"]))
    next(rows)
    return dict(input=example["input"], output=[[int(a), int(b)] for a, b in rows])


def experiment(guest, ask, out, previous):
    seed = 512331
    _, training = specs(774129)
    _, audit = specs(seed)
    rng = random.Random(278601)
    rows = [[], [[1, 4], [8, 11]], [[-7, -6], [10, 14]]]
    for _ in range(32):
        batch = []
        t = rng.randrange(-16, 15)
        for _ in range(rng.randrange(8)):
            t += rng.randrange(1, 6)
            stop = t + rng.randrange(1, 15)
            batch.append([t, stop])
            t = stop
        rows.append(batch)
    render = [dict(input=s, output=files(s)) for s in rows]
    parts = [
        dict(
            name="coverage_spans",
            task=COVERAGE,
            examples=list(map(intervals, training["examples"])),
            validation=list(map(intervals, training["validation"])),
            jobs=[],
        ),
        dict(
            name="coverage_files",
            task=RENDER,
            examples=render[:3],
            validation=render[3:],
            compare=audit["compare"],
            jobs=[],
        ),
    ]
    banks = {part["name"]: out / (part["name"] + "-bank") for part in parts}
    helpers = [s for s in load_bank(previous) if s["task"] == "merge_runs"]
    for member in helpers:
        save(banks["coverage_spans"] / (member["digest"] + ".json"), member)
    for spec in parts:
        receipt = work(spec, guest, ask, out / spec["name"], banks[spec["name"]], 2)
        print(spec["name"], receipt["public"], receipt["validated"], flush=True)
    members = {s["task"]: s for bank in banks.values() for s in load_bank(bank)}
    if any(p["name"] not in members for p in parts):
        save(
            out / "outcome.json",
            dict(released=False, reason="one or more phase workers failed independent qualification"),
        )
        return
    ordered = [members[p["name"]] for p in parts]
    source = tool_source("def solve(x):\n    return skill_coverage_files(skill_coverage_spans(x))", ordered)

    def link(task, prefix, prior):
        return {"source": source, "usage": {"completion_tokens": 0}, "stop": "linked_verified_members"}

    final = out / "joint"
    receipt = work(audit, guest, link, final, None, 1)
    inspect_delivery(guest, final, receipt, audit, 7733, seed)
    save(
        out / "outcome.json",
        dict(
            released=receipt["validated"] == len(audit["validation"]),
            digest=receipt["digest"],
            parents=[p["digest"] for p in ordered],
        ),
    )
    print("joint", receipt["validated"], len(receipt["jobs"]), flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for k in ("out", "sdk", "prior-school"):
        p.add_argument("--" + k, type=Path, required=True)
    p.add_argument("--url")
    p.add_argument("--binary", type=Path)
    p.add_argument("--weights", type=Path)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    if not args.url and not (args.binary and args.weights):
        p.error("provide a local endpoint or binary and weights")
    endpoint = (
        nullcontext(args.url)
        if args.url
        else server(args.binary, args.weights, args.out / "server.log", threads=2)
    )
    with endpoint as url:

        def ask(task, prefix, prior):
            return generate(url, task, prefix, prior, budget=1100, focused=True, concise=True)

        experiment(Guest(args.sdk), ask, args.out, args.prior_school)


if __name__ == "__main__":
    main()
