"""Build a short feasible project schedule and independently verify its start times."""

import argparse
import heapq
import json
from pathlib import Path
import random
import sys

from . import saved

# The exact public scheduling contract on which compatible writers must have qualified.
CONTRACT = (
    'Write a general Python function solve(x) for nonpreemptive project scheduling. x is a decoded '
    "dict. x['capacity'] is a list of positive integer capacities for renewable resources. x['jobs'] is "
    'a list of jobs, each [duration, demand, predecessors]. duration is a nonnegative integer, '
    'demand[r] is the simultaneous integer demand on resource r, and predecessors is a list of '
    'zero-based job indices. The precedence graph is acyclic. Each job fits individually. Start every '
    'job once at a nonnegative integer time. Every predecessor must finish before its successor starts '
    '(finishing and starting at the same time is allowed). Active jobs occupy [start,start+duration); '
    'their summed demand must stay within every capacity. Return a list of integer start times in '
    'original job-index order. Find a feasible schedule with a short makespan (latest finish); it need '
    'not be optimal. The same program will process multiple independent projects.'
)
TASK = "project_schedule"
MAX_JOBS, MAX_RESOURCES, MAX_HORIZON = 64, 8, 2048
MAX_BANK, FUEL = 4, 2_000_000_000


def _order(jobs, successors, priority):
    remaining = [len(job[2]) for job in jobs]
    ready = [(priority[j], j) for j, count in enumerate(remaining) if not count]
    heapq.heapify(ready)
    order = []
    while ready:
        _, job = heapq.heappop(ready)
        order.append(job)
        for child in successors[job]:
            remaining[child] -= 1
            if remaining[child] == 0:
                heapq.heappush(ready, (priority[child], child))
    if len(order) != len(jobs):
        raise ValueError("job predecessors contain a cycle")
    return order


def _project(raw):
    if not isinstance(raw, dict) or set(raw) - {"capacity", "jobs", "job_names"}:
        raise ValueError("expected a project object with capacity, jobs and optional job_names")
    capacity, jobs = raw.get("capacity"), raw.get("jobs")
    if (not isinstance(capacity, list) or len(capacity) > MAX_RESOURCES
            or any(type(v) is not int or v <= 0 for v in capacity)):
        raise ValueError(f"capacity must list up to {MAX_RESOURCES} positive whole resource capacities")
    if not isinstance(jobs, list) or len(jobs) > MAX_JOBS:
        raise ValueError(f"jobs must list up to {MAX_JOBS} activities")
    names = raw.get("job_names", [])
    if "job_names" in raw and (not isinstance(names, list) or len(names) != len(jobs)
            or any(not isinstance(s, str) or not 1 <= len(s) <= 120 or not s.isprintable() for s in names)):
        raise ValueError("provide one short printable name per job")
    successors = [[] for _ in jobs]
    normalized = []
    for j, job in enumerate(jobs):
        if not isinstance(job, list) or len(job) != 3:
            raise ValueError(f"job {j} must be [duration, resource demand, predecessor indices]")
        duration, demand, parents = job
        if type(duration) is not int or duration < 0:
            raise ValueError(f"job {j} needs a nonnegative whole duration")
        if (not isinstance(demand, list) or len(demand) != len(capacity)
                or any(type(v) is not int or v < 0 for v in demand)):
            raise ValueError(f"job {j} needs one nonnegative whole demand per resource")
        if any(v > cap for v, cap in zip(demand, capacity)):
            raise ValueError(f"job {j} exceeds the available resource capacity")
        if (not isinstance(parents, list) or any(type(p) is not int or not 0 <= p < len(jobs) for p in parents)):
            raise ValueError(f"job {j} has an invalid predecessor index")
        unique = sorted(set(parents))
        for parent in unique:
            successors[parent].append(j)
        normalized.append([duration, demand, unique])
    if sum(row[0] for row in normalized) > MAX_HORIZON:
        raise ValueError(f"total duration exceeds {MAX_HORIZON} time units")
    return {"capacity": capacity, "jobs": normalized}, successors, names


def checked_makespan(project, starts):
    """Validate a submission using interval events, independently of the scheduler's time-slot table."""
    jobs, capacity = project["jobs"], project["capacity"]
    if not isinstance(starts, list) or len(starts) != len(jobs) or any(type(t) is not int or t < 0 for t in starts):
        raise ValueError("expected one nonnegative integer start time per job")
    ends = [t + job[0] for t, job in zip(starts, jobs)]
    changes = {}
    for j, (duration, demand, parents) in enumerate(jobs):
        if any(ends[p] > starts[j] for p in parents):
            raise ValueError(f"job {j} starts before a predecessor finishes")
        if duration:
            for t, sign in ((starts[j], 1), (ends[j], -1)):
                delta = changes.setdefault(t, [0] * len(capacity))
                for r, amount in enumerate(demand):
                    delta[r] += sign * amount
    used = [0] * len(capacity)
    for t in sorted(changes):
        used = [v + delta for v, delta in zip(used, changes[t])]
        if any(v > limit for v, limit in zip(used, capacity)):
            raise ValueError(f"resource capacity exceeded at time {t}")
    return max(ends, default=0)


def _serial(project, order):
    jobs, capacity = project["jobs"], project["capacity"]
    horizon = sum(job[0] for job in jobs)
    loads = [[0] * len(capacity) for _ in range(horizon)]
    starts = [0] * len(jobs)
    for j in order:
        duration, demand, parents = jobs[j]
        start = max((starts[p] + jobs[p][0] for p in parents), default=0)
        limits = [(r, capacity[r] - d) for r, d in enumerate(demand) if d]
        if duration and limits:
            free = 0
            for t in range(start, horizon):
                free = free + 1 if all(loads[t][r] <= limit for r, limit in limits) else 0
                if free == duration:
                    start = t + 1 - duration
                    break
            else:
                raise RuntimeError("serial scheduler exceeded the sum of the job durations")
            for t in range(start, start + duration):
                for r, _ in limits:
                    loads[t][r] += demand[r]
        starts[j] = start
    return starts


def _classical(project, successors):
    jobs = project["jobs"]
    durations = [j[0] for j in jobs]
    topo = _order(jobs, successors, durations)
    yield "classical/shortest-duration", _serial(project, topo)
    tails = durations.copy()
    for j in reversed(topo):
        tails[j] += max((tails[k] for k in successors[j]), default=0)
    yield "classical/longest-tail", _serial(project, _order(jobs, successors, [-t for t in tails]))
    # Fixed CPU envelope for the pilot's seeded priority search on larger projects.
    work = max(1, len(jobs)) * max(1, sum(durations)) * max(1, len(project["capacity"]))
    rng = random.Random(2808)
    for i in range(min(64, max(0, 2_000_000 // work - 2)) if jobs else 0):
        priority = [rng.random() for _ in jobs]
        yield f"classical/seed-2808-draw-{i + 1}", _serial(project, _order(jobs, successors, priority))


def schedule(raw, bank=None):
    from training.experiments.fieldwork.work import load_bank

    project, successors, names = _project(raw)
    # The first equally short plan wins, so an equal checked method cannot displace the baseline.
    best = min(((checked_makespan(project, starts), label, starts) for label, starts in _classical(project, successors)),
               key=lambda candidate: candidate[0])
    rows = [row for row in load_bank(bank) if row["task"] == TASK and row["description"] == CONTRACT]
    notes = []
    if len(rows) > MAX_BANK:
        notes.append(f"Checking the first {MAX_BANK} of {len(rows)} compatible methods in source digest order.")
    runner = saved.guest() if rows else None
    if rows and runner is None:
        notes.append("Saved methods require the optional WebAssembly runtime.")
    if runner is not None:
        for row in sorted(rows, key=lambda r: r["digest"])[:MAX_BANK]:
            label = "bank/" + row["digest"]
            try:
                results, _, _ = runner.run(row["source"], [{"capacity": raw["capacity"], "jobs": raw["jobs"]}], fuel=FUEL)
                if len(results) != 1 or not isinstance(results[0], dict) or "value" not in results[0]:
                    raise ValueError("guest did not return start times")
                starts = results[0]["value"]
                span = checked_makespan(project, starts)
            except Exception as exc:  # A failed optional guest must leave the independently checked baseline available.
                notes.append(f"Skipped {label}: {type(exc).__name__}: {str(exc)[:160]}")
                continue
            if span < best[0]:
                best = span, label, starts
    return best, names, notes


def main(argv=None):
    parser = argparse.ArgumentParser(prog="hive schedule", description=__doc__,
        epilog="Up to 64 jobs, 8 renewable resources and 2,048 total duration units. "
               "At most 66 classical priorities and 4 checked bank programs (2 billion WASI fuel each).")
    parser.add_argument("project", type=Path, help="JSON with capacity and jobs; optional job_names annotate the schedule")
    parser.add_argument("--bank", type=Path, default=saved.bank_path(), help="checked fieldwork bank (default: HIVE_BANK)")
    args = parser.parse_args(argv)
    try:
        with args.project.open("rb") as file:
            data = file.read(131_073)
        if len(data) > 131_072:
            raise ValueError("project exceeds 128 KiB")
        raw = json.loads(data, object_pairs_hook=saved._object)
        (span, label, starts), names, notes = schedule(raw, args.bank)
    except (OSError, ValueError, RecursionError) as exc:
        print(f"Cannot schedule project: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(starts))
    print(f"Makespan {span}. Winner {label}.", file=sys.stderr)
    for i, name in enumerate(names):
        print(f"{i}. {name}: start {starts[i]}, finish {starts[i] + raw['jobs'][i][0]}", file=sys.stderr)
    for note in notes:
        print(note, file=sys.stderr)
    return 0
