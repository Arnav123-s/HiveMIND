"""Footprint / concurrency test. Run from the coding/ directory:

    python3 -m swarm.footprint_test

Builds the niche tree, then spawns constructed specialists in batches and
measures resident memory. Constructed specialists are the swarm's mass
unit: shared code, a few hundred bytes of state each. Model-bound
specialists are NOT counted per-head — they time-share one resident base
model through the interface layer (PLAN.md, footprint budget).
"""
import resource
import time
from pathlib import Path

from .board import Board
from .niches import NICHES, build_swarm


def rss_kb():
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith("VmRSS"):
            return int(line.split()[1])
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss


def main():
    board = Board()
    reg = build_swarm(board)
    coords = sum(1 for s in reg.all() if s.kind == "coordinator")
    print(f"niche tree: {reg.count()} specialists across {len(NICHES)} niches "
          f"({coords} niche coordinators included)")
    base = reg.get("output-differ")
    marks = [(0, rss_kb())]
    t0 = time.time()
    total = 0
    for batch in (1000, 4000, 15000, 30000):
        for i in range(batch):
            reg.add(base.clone(f"f{total + i}"))
        total += batch
        marks.append((total, rss_kb()))
        print(f"  +{total:>6} constructed specialists resident: RSS {marks[-1][1] / 1024:.1f} MiB")
    dt = time.time() - t0
    (n1, r1), (n2, r2) = marks[-2], marks[-1]
    per = (r2 - r1) * 1024 / (n2 - n1)
    print(f"spawn rate: {total / dt:.0f} specialists/s; marginal footprint: {per:.0f} bytes/specialist")
    for envelope_gib in (1, 5):
        cap = int(envelope_gib * 2**30 / per)
        print(f"capacity at {per:.0f} B/head: ~{cap:,} constructed specialists in a {envelope_gib} GiB envelope")
    print(f"peak RSS of this process: {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024:.1f} MiB "
          f"with {reg.count()} specialists registered")


if __name__ == "__main__":
    main()
