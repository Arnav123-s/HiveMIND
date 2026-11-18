"""Give every colony the same births, deaths and teaching budget. Score the work its living members finish."""
import argparse
import json
from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

import numpy as np

from training.experiments.hive_scale_cells import BYTES, draw_cell, fit, forward, learn


@dataclass
class Member:
    duty: int
    table: np.ndarray
    settled: bool
    until: int
    parent: int | None


def fixture(seed):
    rng = np.random.default_rng(seed)
    schools, reference = [], []
    for _ in range(56):
        source = draw_cell(rng)
        order = rng.permutation(BYTES)
        _, lesson = learn(source, order)
        active = np.frombuffer(lesson, np.uint8)[::2]
        course = np.concatenate((active, order[~np.isin(order, active)]))
        schools.append(course)
        reference.append(forward(source.tables(), BYTES))
    # The first eight services are shared. Three sets of paired services come into demand, then the first returns.
    jobs = []
    for season in (0, 1, 2, 0):
        start = 8 + 16 * season
        for _ in range(6):
            batch = []
            for _ in range(64):
                group = min(int(rng.geometric(0.23)) - 1, 7)
                a = start + 2 * group
                draw = rng.random()
                if draw < 0.55:
                    pair = (a, a + 1)
                elif draw < 0.80:
                    pair = (int(rng.integers(8)), a + int(rng.integers(2)))
                elif draw < 0.90:
                    pair = tuple(map(int, rng.integers(8, size=2)))
                else:
                    pair = tuple(map(int, rng.integers(start, start + 16, size=2)))
                batch.append(pair)
            jobs.append(batch)
    lifetimes = rng.geometric(0.008, size=8 + 2 * len(jobs))
    return schools, np.stack(reference), jobs, lifetimes


def choose(policy, served, recent, living, rng):
    if policy == "inherit":
        parents = rng.choice(list(living), size=2)
        return [living[i].duty for i in parents]
    waiting = sorted(set(range(56)) - set(served))
    if len(waiting) < 2:
        return (waiting + sorted(served))[:2]
    if policy == "random":
        return rng.choice(waiting, 2, replace=False).tolist()
    demand = Counter()
    for pair, jobs in recent.items():
        for need in set(pair) - set(served):
            demand[need] += jobs
    if policy == "frequency":
        return sorted(waiting, key=lambda k: (-demand[k], k))[:2]
    one, both = Counter(), Counter()
    for pair, jobs in recent.items():
        missing = tuple(sorted(set(pair) - set(served)))
        if len(missing) == 1:
            one[missing[0]] += jobs
        elif len(missing) == 2:
            both[missing] += jobs
    return max(combinations(waiting, 2),
               key=lambda p: (one[p[0]] + one[p[1]] + both[p], demand[p[0]] + demand[p[1]]))


def colony(seed, world, policy):
    schools, truth, jobs, lifetimes = world
    rng = np.random.default_rng(seed + 17)
    # All colonies begin with the same eight previously commissioned elders.
    living, seen, notebooks = {}, Counter(), {}
    for i in range(8):
        cell, gaps = fit(BYTES, truth[i])
        living[i] = Member(i, cell.tables(), not gaps.any(), int(lifetimes[i]), None)
        notebooks[i] = dict(zip(BYTES.tolist(), truth[i].tolist()))
    epochs, retired = [], 0
    for epoch, batch in enumerate(jobs):
        expired = [i for i, child in living.items() if child.until <= epoch]
        for i in expired:
            del living[i]
        retired += len(expired)
        served = {child.duty: child.table for child in living.values() if child.settled}
        completed = 0
        for a, b in batch:
            if a in served and b in served:
                y = forward(served[b], forward(served[a], BYTES))
                completed += int(np.array_equal(y, truth[b, truth[a]]))
        # Birth decisions see only actual recent requests and which duties have a current qualified worker.
        recent = Counter(pair for block in jobs[max(0, epoch - 1):epoch + 1] for pair in block)
        candidates = choose(policy, served, recent, living, rng)
        for offset, duty in enumerate(candidates):
            duty = int(duty)
            # A parent of the same duty can teach. A different parent can adopt a new duty for its child.
            relatives = [i for i, m in living.items() if m.duty == duty]
            parent = int(rng.choice(relatives or list(living)))
            previous = seen[duty] + (256 if duty < 8 else 0)
            # A regional log survives the death of individuals. Further readings after the course repeats are audits.
            paid = schools[duty][np.arange(previous, previous + 14) % 256]
            seen[duty] += len(paid)
            book = notebooks.setdefault(duty, {})
            book.update(zip(paid.tolist(), truth[duty, paid].tolist()))
            cell, gaps = fit(list(book), list(book.values()))
            ident = 8 + 2 * epoch + offset
            living[ident] = Member(duty, cell.tables(), not gaps.any(), epoch + int(lifetimes[ident]), parent)
        epochs.append(dict(finished=completed, offered=len(batch), duties_before=len(served), births=list(map(int, candidates)),
                           living=len(living), unqualified_living=sum(not m.settled for m in living.values()),
                           deaths=len(expired)))
    return dict(completed=sum(e["finished"] for e in epochs), teaching_readings=sum(seen.values()),
                deaths=retired, epochs=epochs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    results = {}
    for seed in (1511, 1523, 1543, 1553, 1567, 1571, 1579, 1583):
        world = fixture(seed)
        results[seed] = {p: colony(seed, world, p) for p in ("inherit", "random", "frequency", "pairs")}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
