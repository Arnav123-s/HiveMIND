"""Measure a second growth step with checked regional discovery and fallbacks to the whole population."""
import argparse
import gzip
import json
import os
import resource
import time
from collections import Counter
from pathlib import Path

import numpy as np

from training.experiments.hive_scale import Readings, apply_maps, teach
from training.experiments.hive_scale_archive import Archive, Workers
from training.experiments.hive_scale_cells import BYTES
from training.experiments.hive_scale_router import Directory, verified


SHARD = 64


def select_pair(directory, inputs, outputs, checks, expected):
    candidates = directory.candidates(inputs, outputs, 2, "linear")
    plan, _ = verified(directory, candidates, checks, expected)
    if plan is None:
        return None
    return tuple(directory.groups[i][0] for i in plan)


def route(root, regions, hints, readings, mode):
    """Return physical member IDs. Hints name eligible regions; observations verify every chosen pair."""
    anchors, checks = root.anchors, readings.checks
    mid, end = readings.observe(anchors, True)
    check_mid, check_end = readings.observe(checks, True)
    plan, escalations = (), 0
    for region, evidence in zip(hints, ((anchors, mid, checks, check_mid), (mid, end, check_mid, check_end))):
        first = root if mode == "global" else regions[region]
        pair = select_pair(first, *evidence)
        if pair is None and mode == "fallback":
            escalations += 1
            pair = select_pair(root, *evidence)
        if pair is None:
            return None, escalations
        plan += pair
    return plan, escalations


def cases(rng, n, maps, anchors, public, exam, count):
    jobs = []
    for i in range(count):
        regions = rng.integers(n // SHARD, size=2)
        ids = np.repeat(regions, 2) * SHARD + rng.integers(SHARD, size=4)
        hints = regions.copy()
        kind = ("local", "local", "local", "stale_hint", "cross_region")[i % 5]
        slot = int(rng.integers(2))
        adjacent = (regions[slot] + 1) % (n // SHARD)
        if kind == "stale_hint":
            hints[slot] = adjacent
        if kind == "cross_region":
            ids[2 * slot + 1] = adjacent * SHARD + rng.integers(SHARD)
        mid = apply_maps(maps, ids[:2], BYTES)
        end = apply_maps(maps, ids[2:], mid)
        checks = rng.choice(public[3:], 3, replace=False)
        jobs.append((kind, hints, Readings(4, anchors, checks, mid, end), end[exam]))
    rng.shuffle(jobs)
    return jobs


def evaluate(root, regions, jobs, archive, exam, seconds):
    result = {}
    for mode in ("global", "region_only", "fallback"):
        # Workers address physical IDs here. The specialist population has no functional duplicates.
        worker = Workers(archive, root.groups)
        def attempt(job):
            _, hints, reads, expected = job
            plan, broad = route(root, regions, hints, reads, mode)
            if plan is None:
                return "defer", broad
            prediction = worker.execute(plan, exam)
            return ("correct" if np.array_equal(prediction, expected) else "wrong"), broad
        strata = {}
        for job in jobs:
            outcome, escalations = attempt(job)
            s = strata.setdefault(job[0], Counter())
            s[outcome] += 1
            s["global_retries"] += escalations
        worker = Workers(archive, root.groups)
        counts = Counter()
        start = time.process_time_ns()
        i = 0
        while True:
            outcome, retries = attempt(jobs[i % len(jobs)])
            if time.process_time_ns() - start > seconds * 1e9:
                break
            counts[outcome] += 1
            counts["global_retries"] += retries
            i += 1
        result[mode] = dict(by_stratum=strata, fixed_cpu=counts, paid_seconds=seconds,
                            completed=i, peak_workers=worker.peak)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seeds", nargs="+", type=int, default=[929, 947, 971])
    parser.add_argument("--sizes", nargs="+", type=int, default=[128, 1024, 4096])
    parser.add_argument("--jobs", type=int, default=120)
    parser.add_argument("--cpu-seconds", type=float, default=0.4)
    args = parser.parse_args()
    if any(n < 2 * SHARD or n % SHARD for n in args.sizes) or args.jobs <= 0 or args.cpu_seconds <= 0:
        parser.error("use at least two complete regions and positive job and time budgets")
    args.out.mkdir(parents=True, exist_ok=False)
    core = None
    if hasattr(os, "sched_getaffinity"):
        core = min(os.sched_getaffinity(0))
        os.sched_setaffinity(0, {core})
    records = dict(seeds={}, jobs=args.jobs, shard=SHARD, pinned_core=core)
    for seed in args.seeds:
        rng = np.random.default_rng(seed)
        members, maps, learning = teach(rng, count=max(args.sizes), foreign=0)
        archive = Archive.create(args.out / str(seed), members, region_size=SHARD)
        inputs = rng.permutation(BYTES)
        public, exam = inputs[:128], inputs[128:]
        banks = {}
        for n in args.sizes:
            root = Directory(archive, public[:3], range(n))
            if root.size != n:
                raise AssertionError("a learned member duplicates another at this scale")
            regional = [Directory(archive, public[:3], range(i, i + SHARD)) for i in range(0, n, SHARD)]
            jobs = cases(rng, n, maps, public[:3], public, exam, args.jobs)
            banks[n] = dict(learned_exact=sum(x["active_errors"] == 0 for x in learning[:n]),
                            passive_exact=sum(x["passive_errors"] == 0 for x in learning[:n]),
                            training_probes=sum(x["probes"] for x in learning[:n]),
                            training_cpu_ns=sum(x["train_ns"] for x in learning[:n]),
                            global_build_ns=root.base_build_ns,
                            region_build_ns=sum(r.base_build_ns for r in regional),
                            global_array_bytes=root.tables.nbytes + root.single.nbytes,
                            regional_array_bytes=sum(r.tables.nbytes + r.single.nbytes for r in regional),
                            results=evaluate(root, regional, jobs, archive, exam, args.cpu_seconds))
        records["seeds"][seed] = banks
        print(f"regional seed {seed} complete", flush=True)
    records["process_max_rss_kib_linux"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    with gzip.open(args.out / "region-measurements.json.gz", "wt") as f:
        json.dump(records, f, separators=(",", ":"))


if __name__ == "__main__":
    main()
