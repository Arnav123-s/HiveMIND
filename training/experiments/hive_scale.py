"""One-CPU scale experiment. Run with python -m training.experiments.hive_scale --out NEW_DIR."""
import argparse
import gzip
import json
import os
import platform
import resource
import shutil
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from training.experiments.hive_scale_archive import Archive, Workers
from training.experiments.hive_scale_cells import BYTES, draw_cell, fit, forward, learn
from training.experiments.hive_scale_certify import certify, replay
from training.experiments.hive_scale_router import Directory, discover, fixed_scans


SEEDS = (611, 673, 701, 743, 809)
METHODS = {2: ("scan", "linear", "pairs"), 4: ("scan", "linear", "checkpoint")}


def apply_maps(maps, members, values):
    for member in members:
        values = maps[member][values]
    return values


def teach(rng, count=128, foreign=8):
    members, maps, seen, rows = [], [], set(), []
    while len(maps) < count + foreign:
        source = draw_cell(rng)
        reference = forward(source.tables(), BYTES)
        if reference.tobytes() in seen:
            continue
        seen.add(reference.tobytes())
        maps.append(reference)
        if len(maps) > count:  # Foreign cells appear only in the out-of-library evaluation.
            continue
        order = rng.permutation(BYTES)
        start = time.process_time_ns()
        child, log = learn(source, order)
        train_ns = time.process_time_ns() - start
        used = len(log) // 2
        passive, _ = fit(order[:used], reference[order[:used]])
        active_prediction = forward(child.tables(), BYTES)
        unused = np.ones(256, bool)
        unused[np.frombuffer(log, np.uint8)[::2]] = False
        rows.append(dict(probes=used, train_ns=train_ns,
                         active_errors=int(np.count_nonzero(active_prediction != reference)),
                         active_unseen_errors=int(np.count_nonzero(active_prediction[unused] != reference[unused])),
                         passive_errors=int(np.count_nonzero(forward(passive.tables(), BYTES) != reference))))
        members.append((child.archive(), log))
    return members, np.stack(maps), rows


class Readings:
    """The discovery API exposes only readings at the six public inputs and the announced depth."""
    def __init__(self, depth, anchors, checks, mid, end):
        self.depth, self.checks = depth, checks
        self.allowed = frozenset(anchors.tolist() + checks.tolist())
        self._mid, self._end = mid, end
        self.end_bytes = self.mid_bytes = 0

    def observe(self, x, midpoint):
        if not all(int(v) in self.allowed for v in x):
            raise ValueError("reading outside public probes")
        self.end_bytes += len(x)
        if midpoint:
            self.mid_bytes += len(x)
        return (self._mid[x] if midpoint else None), self._end[x]


@dataclass
class Trial:
    stratum: str
    stages: tuple
    public: Readings
    midpoint: np.ndarray
    truth: np.ndarray


def tasks(rng, maps, anchors, public, exam, per_stratum):
    trials = {2: [], 4: []}
    for depth in trials:
        for name, start, stop in (("core", 0, 8), ("middle", 8, 32), ("wide", 32, 128),
                                  ("foreign", 128, 136), ("exception", 0, 8)):
            for _ in range(per_stratum):
                pool = min(stop, 128)
                ids = rng.integers(0, pool, depth)
                ids[rng.integers(depth)] = rng.integers(start, stop)
                stages = tuple(map(int, ids))
                mid = apply_maps(maps, stages[:depth // 2], BYTES)
                end = apply_maps(maps, stages[depth // 2:], mid)
                if name == "exception":
                    # One exceptional code in each partition. The public one may or may not be queried.
                    a, b = rng.choice(public), rng.choice(exam)
                    end[[a, b]] = end[[b, a]]
                checks = rng.choice(public[3:], 3, replace=False)
                trials[depth].append(Trial(name, stages, Readings(depth, anchors, checks, mid, end), mid, end))
        rng.shuffle(trials[depth])
    return trials


def run_one(directory, workers, trial, exam, method, scans):
    task = trial.public
    task.end_bytes = task.mid_bytes = 0
    plan, why, width = discover(directory, task, method, scans)
    if plan is None:
        return "defer", why, width, None
    values = workers.execute(plan, exam)
    if values is None:
        return "defer", "unavailable", width, plan
    return ("correct" if np.array_equal(values, trial.truth[exam]) else "wrong"), why, width, plan


def evaluate(directory, archive, trials, exam, scans):
    groups, evidence = {}, []
    for depth, bank in trials.items():
        for method in METHODS[depth]:
            workers = Workers(archive, directory.groups)
            for trial in bank:
                start = time.process_time_ns()
                outcome, reason, width, plan = run_one(directory, workers, trial, exam, method, scans)
                elapsed = time.process_time_ns() - start
                key = f"{depth}-{method}-{trial.stratum}"
                row = groups.setdefault(key, Counter())
                row.update([outcome])
                row["cpu_ns"] += elapsed
                row["candidates"] += width
                row["end_bytes"] += trial.public.end_bytes
                row["mid_bytes"] += trial.public.mid_bytes
                if outcome == "defer":
                    row[reason] += 1
                if method == "checkpoint" and not any(x["stratum"] == trial.stratum for x in evidence):
                    evidence.append(dict(stratum=trial.stratum, source=trial.stages, selected=plan, result=outcome,
                                         inputs=directory.anchors.tolist() + trial.public.checks.tolist(),
                                         end_bytes=trial.public.end_bytes, mid_bytes=trial.public.mid_bytes))
    return groups, evidence


def timed(directory, archive, stream, exam, method, scans, seconds, offset):
    workers = Workers(archive, directory.groups)
    counts = Counter()
    attempts = 0
    started = time.process_time_ns()
    deadline = started + round(seconds * 1e9)
    while True:
        trial = stream[(offset + attempts) % len(stream)]
        outcome, _, _, _ = run_one(directory, workers, trial, exam, method, scans)
        now = time.process_time_ns()
        if now > deadline:
            break  # A job whose answer crosses the deadline earns no credit.
        counts[outcome] += 1
        attempts += 1
    return dict(counts, completed=attempts, elapsed_ns=now-started, loads_including_last=workers.loads,
                max_worker_slots=workers.peak)


def commission(directory, bank, exam, scans):
    """Commission clean, near-match and foreign devices in a separate, fully observed phase."""
    groups, example = {}, None
    for i, trial in enumerate(bank):
        if trial.stratum not in ("core", "exception", "foreign"):
            continue
        stats = groups.setdefault(trial.stratum, Counter())
        method = "checkpoint" if trial.public.depth == 4 else "linear"
        plan, _, _ = discover(directory, trial.public, method, scans)
        if plan is None:
            stats["quick_deferred"] += 1
        else:
            stats["quick_answered"] += 1
            stats["quick_wrong"] += int(not np.array_equal(directory.predict(plan, exam), trial.truth[exam]))
        def measured(values, inputs, counter):
            stats[counter] += len(inputs)
            return values[inputs]

        version = f"sensor-{trial.public.depth}-{i}/v1"
        record = certify(directory, trial.public.depth, plan, version,
                         lambda x: measured(trial.truth, x, "full_readings"),
                         lambda x: measured(trial.midpoint, x, "extra_midpoint_readings"))
        if record is None:
            stats["rejected"] += 1
            continue
        stats["correct_all_256"] += int(np.array_equal(replay(record, directory, version, BYTES), trial.truth))
        stats["previously_deferred_recovered"] += int(plan is None)
        stats["correction_bytes"] += len(bytes.fromhex(record["edits"]))
        stats["serialized_bytes"] += len(json.dumps(record, separators=(",", ":")).encode())
        if trial.stratum == "exception" and example is None:
            example = record
    return dict(by_stratum=groups, example=example)


def execution_control(directory, archive, rng):
    programs = rng.integers(directory.size, size=(128, 4))
    lut = np.stack([directory.predict((i,), BYTES) for i in range(directory.size)])
    controls = {}
    expected = [apply_maps(lut, p, BYTES[:128]) for p in programs]
    for mode in ("neural_worker", "table_worker", "resident_masks", "resident_lut"):
        w = Workers(archive, directory.groups, neural=mode == "neural_worker")
        start = time.process_time_ns()
        for p, y in zip(programs, expected):
            if mode.endswith("worker"):
                prediction = w.execute(p, BYTES[:128])
            elif mode == "resident_masks":
                prediction = directory.predict(p, BYTES[:128])
            else:
                prediction = apply_maps(lut, p, BYTES[:128])
            if not np.array_equal(prediction, y):
                raise AssertionError("execution paths disagree")
        controls[mode] = dict(cpu_ns=time.process_time_ns()-start, jobs=len(programs), loads=w.loads)
    return controls


def outage(root, archive, directory, rng):
    scratch = root / "outage"
    shutil.copytree(archive.root, scratch)
    victim = Archive(scratch)
    # Services retain the pre-outage directory. Each phase starts with cold workers.
    (scratch / "region-0.bin").unlink()
    n = directory.size
    plans = [(i, int(rng.integers(n))) for i in range(8)]
    if n > 8:
        plans += [tuple(map(int, rng.integers(8, n, 2))) for _ in range(8)]
    def phase(heal, selected=plans):
        worker = Workers(victim, directory.groups, heal=heal)
        results = []
        for p in selected:
            got = worker.execute(p, BYTES)
            results.append(got is not None and np.array_equal(got, directory.predict(p, BYTES)))
        return dict(correct=sum(results), jobs=len(results), lost_region_jobs=sum(results[:8]),
                    repairs=worker.repairs, failed_reads=worker.unavailable, slots=worker.peak)
    phases = {"unassisted": phase(False), "regrowth": phase(True), "cold_restart": phase(False)}
    # Leave one cell unreadable both locally and in its teaching record.
    # The manifest checksum remains available, sufficient to reject an incorrect reconstruction.
    if n == len(archive.records):
        (scratch / "restored" / "0").unlink(missing_ok=True)
        (scratch / "teaching.bin").write_bytes(b"")
        phases["lost_weights_and_teaching"] = phase(True, [(0, 0)])
        phases["rejected_overlay_absent"] = not (scratch / "restored" / "0").exists()
    shutil.rmtree(scratch)
    return phases


def measure_seed(root, seed, count, seconds):
    rng = np.random.default_rng(seed)
    members, maps, learning = teach(rng)
    inputs = rng.permutation(BYTES)
    public, exam = inputs[:128], inputs[128:]
    anchors = public[:3]
    trials = tasks(rng, maps, anchors, public, exam, count)
    results = {}
    for label, size, repeats in (("8", 8, 1), ("32", 32, 1), ("128", 128, 1), ("copies", 8, 16)):
        archive = Archive.create(root / label, members[:size] * repeats)
        directory = Directory(archive, anchors)
        scans = fixed_scans(directory.size)
        pair_bytes = directory.pair_index().nbytes
        quality, trace = evaluate(directory, archive, trials, exam, scans)
        costs = {}
        for depth, methods in METHODS.items():
            # The same offered ordering for every archive/method at each seed and depth.
            offered = [t for t in trials[depth] if t.stratum in ("core", "middle", "wide")]
            rotation = seed % len(methods)
            for method in methods[rotation:] + methods[:rotation]:
                costs[f"{depth}-{method}"] = timed(directory, archive, offered, exam, method, scans,
                                                    seconds, seed % len(offered))
        # Same procedures and failure selection across implementation alternatives.
        test_rng = np.random.default_rng(seed + 319)
        outcome = dict(physical=len(archive.records), unique=directory.size,
                       base_build_ns=directory.base_build_ns, pair_build_ns=directory.pair_build_ns,
                       mask_bytes=directory.tables.nbytes, single_index_bytes=directory.single.nbytes,
                       pair_index_bytes=pair_bytes, manifest_bytes=(archive.root / "manifest.json").stat().st_size,
                       teaching_bytes=(archive.root / "teaching.bin").stat().st_size,
                       packed_weights_bytes=16*len(archive.records), quality=quality, examples=trace,
                       fixed_cpu=costs, execution=execution_control(directory, archive, test_rng))
        # Place the throwaway outage copy beside the archive, never inside its source.
        drill = root / (label + "-drill")
        drill.mkdir()
        outcome["outage"] = outage(drill, archive, directory, test_rng)
        if label == "128":
            outcome["commission"] = {depth: commission(directory, bank, exam, scans)
                                     for depth, bank in trials.items()}
        results[label] = outcome
    return dict(seed=seed, anchors=anchors.tolist(), exam=exam.tolist(), learning=learning, banks=results)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seeds", type=int, nargs="+", default=SEEDS)
    parser.add_argument("--per-stratum", type=int, default=24)
    parser.add_argument("--cpu-seconds", type=float, default=0.25)
    args = parser.parse_args()
    if args.per_stratum <= 0 or args.cpu_seconds <= 0:
        parser.error("trial count and CPU time must be positive")
    args.out.mkdir(parents=True, exist_ok=False)
    core = None
    if hasattr(os, "sched_getaffinity"):
        core = min(os.sched_getaffinity(0))
        os.sched_setaffinity(0, {core})
    result = dict(format=1, per_stratum=args.per_stratum, cpu_seconds=args.cpu_seconds,
                  platform=platform.platform(), python=platform.python_version(), numpy=np.__version__,
                  pinned_core=core, seeds=[])
    for seed in args.seeds:
        root = args.out / str(seed)
        root.mkdir()
        result["seeds"].append(measure_seed(root, seed, args.per_stratum, args.cpu_seconds))
        print(f"seed {seed} complete", flush=True)
    result["process_max_rss_kib_linux"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    with gzip.open(args.out / "scale-measurements.json.gz", "wt") as stream:
        json.dump(result, stream, separators=(",", ":"))


if __name__ == "__main__":
    main()
