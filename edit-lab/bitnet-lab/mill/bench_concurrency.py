#!/usr/bin/env python3
"""bench_concurrency.py — the mill's measured-concurrency study (Muse's work, Muse's side).

Arnav's directive (2026-11-12): the one-heavy-job-at-a-time limit is a research
problem, not a law. This script MEASURES the mill's own concurrency — it never
competes with the ladder or the growth cycles:

  * It refuses to start (exit 3, nothing written) while any heavier lab process
    or another mill process owns the machine, and it drops a .bench-running
    marker so screen.py yields to it in turn.
  * Throughput: a fixed 6-probe queue runs at 1, 2, then 3 concurrent sweep
    workers (OMP/MKL = 2 for the single worker, 1 each for multi-worker runs,
    per the directive). Metric: finished probes per hour.
  * Honesty: 3 of the queue's configs double as honesty configs. Each is run
    solo twice (the replicate spread = the noise floor) and once inside each
    multi-worker batch. A worker count is honest only if every config's
    concurrent held loss sits within max(2 x replicate spread, 0.02) of its
    solo mean — concurrency must not move the numbers, only the clock.
  * Verdict: the largest worker count that (a) improves throughput by >= 10%
    over the count below it and (b) passes honesty. Written to
    mill/CONCURRENCY.md (with the marked CONCURRENCY=<n> line) and
    mill/concurrency.json, which screen.py reads on every pass.

If the study is preempted mid-run it aborts cleanly, removes its marker, and
writes NOTHING — the standing setting (1 worker) stays in force until a
complete study says otherwise.

Usage: bench_concurrency.py [--minutes 0.75]   (lab venv python; run only when
the lab is free — it will tell you if it isn't)
"""
import json, subprocess, sys, time
from pathlib import Path

MILL = Path(__file__).resolve().parent
LAB = MILL.parent
sys.path.insert(0, str(MILL))
import screen as S  # reuse the mill's own busy check, env, and sweep runner

QUEUE = [  # the throughput queue; the first three double as honesty configs
    ("MILL-000", "--arm layered_half --rope"),
    ("MILL-1101", "--arm layered_half --rope --dim 256 --layers-n 1"),
    ("MILL-1901", "--arm plain_half --rope"),
    ("MILL-1103", "--arm layered_half --rope --dim 160 --layers-n 3"),
    ("MILL-1202", "--arm layered_half --rope --batch 64"),
    ("MILL-1105", "--arm layered_half --rope --dim 128 --layers-n 4"),
]
HONESTY = ["MILL-000", "MILL-1101", "MILL-1901"]
MARKER = MILL / ".bench-running"


def run_batch(jobs, workers, omp, minutes):
    """Split jobs across `workers` sweep processes run concurrently; return
    ({id: held}, wall_seconds). Uses screen.run_sweep_batch per worker via
    threads so the batches truly overlap."""
    import threading
    chunks = [[] for _ in range(workers)]
    for i, j in enumerate(jobs):
        chunks[i % workers].append(j)
    out = {}

    def work(chunk):
        if chunk:
            out.update(S.run_sweep_batch(chunk, omp, time.time() + 3600))
    threads = [threading.Thread(target=work, args=(c,)) for c in chunks]
    t0 = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    wall = time.time() - t0
    return {i: r["held_final"] for i, r in out.items() if "held_final" in r}, wall


def main():
    minutes = float(sys.argv[sys.argv.index("--minutes") + 1]) if "--minutes" in sys.argv else 0.75
    busy = S.lab_busy()
    if busy:
        print(f"[bench] lab busy ({busy}) — study deferred, nothing written")
        return 3
    others = subprocess.run(["pgrep", "-f", "screen.py|sweep_probe.py"],
                            capture_output=True, text=True).stdout.split()
    others = [p for p in others if int(p) != S.os.getpid()]
    if others:
        print(f"[bench] another mill process is active {others} — study deferred")
        return 3
    MARKER.write_text(str(time.time()))
    try:
        jobs = [{"id": i, "run": r, "minutes": minutes, "seed": 0,
                 "tag": "bench" + i.replace("MILL-", "")} for i, r in QUEUE]
        print(f"[bench] solo pass (workers=1, timed) + replicate pass (noise floor), "
              f"{minutes} min/probe")
        helds, walls = {}, {}
        helds[1], walls[1] = run_batch(jobs, 1, 2, minutes)
        solo_a = helds[1]
        solo_b, _ = run_batch([j for j in jobs if j["id"] in HONESTY], 1, 2, minutes)
        if len(solo_a) < len(QUEUE) or len(solo_b) < len(HONESTY):
            print("[bench] solo pass incomplete (preempted?) — aborting, nothing written")
            return 3
        print(f"[bench] workers=1: {len(QUEUE)} probes in {walls[1]:.0f}s")
        for w in (2, 3):
            if S.lab_busy():
                print(f"[bench] lab became busy before workers={w} — aborting, nothing written")
                return 3
            helds[w], walls[w] = run_batch(jobs, w, 1, minutes)
            if len(helds[w]) < len(QUEUE):
                print(f"[bench] workers={w} batch incomplete — aborting, nothing written")
                return 3
            print(f"[bench] workers={w}: {len(QUEUE)} probes in {walls[w]:.0f}s")
        tput = {w: len(QUEUE) / walls[w] * 3600 for w in (1, 2, 3)}
        print(f"[bench] throughput probes/hour: " +
              ", ".join(f"W{w}={tput[w]:.1f}" for w in (1, 2, 3)))
        honesty = {}
        for w in (2, 3):
            rows, ok = [], True
            for cfg in HONESTY:
                a, b, c = solo_a[cfg], solo_b[cfg], helds[w][cfg]
                spread = abs(a - b)
                tol = max(2 * spread, 0.02)
                dev = abs(c - (a + b) / 2)
                good = dev <= tol
                ok = ok and good
                rows.append((cfg, a, b, c, spread, tol, dev, good))
            honesty[w] = (ok, rows)
            print(f"[bench] honesty at W={w}: {'PASS' if ok else 'FAIL'}")
        win = 1
        for w in (2, 3):
            if tput[w] >= tput[w - 1] * 1.10 and honesty[w][0]:
                win = w
            else:
                break
        omp = 2 if win == 1 else 1
        (MILL / "concurrency.json").write_text(json.dumps(
            {"workers": win, "omp_threads": omp, "ts": time.time(),
             "study": "CONCURRENCY.md"}, indent=2))
        lines = ["# CONCURRENCY — the mill's measured-concurrency study (Muse's work, Muse's side)",
                 "",
                 f"Study completed by mill/bench_concurrency.py. Probe budget {minutes} min, "
                 f"queue of {len(QUEUE)} sweep-mode probes, solo OMP/MKL=2, multi-worker OMP/MKL=1.",
                 "",
                 "## Throughput (finished probes per hour)",
                 ""]
        for w in (1, 2, 3):
            lines.append(f"- workers={w}: {tput[w]:.1f} probes/hour ({len(QUEUE)} probes in {walls[w]:.0f}s)")
        lines += ["", "## Honesty (held loss: solo A / solo B / concurrent; must agree within noise)", ""]
        for w in (2, 3):
            ok, rows = honesty[w]
            lines.append(f"### workers={w}: {'PASS' if ok else 'FAIL'}")
            for cfg, a, b, c, spread, tol, dev, good in rows:
                lines.append(f"- {cfg}: solo {a:.4f} / {b:.4f} (spread {spread:.4f}), "
                             f"concurrent {c:.4f}, deviation {dev:.4f} vs tolerance {tol:.4f} "
                             f"-> {'ok' if good else 'OUT OF NOISE'}")
        lines += ["", "## Verdict", "",
                  f"Winning worker count: **{win}** (largest count with >=10% throughput gain "
                  f"over the count below it AND a clean honesty check). screen.py reads "
                  f"mill/concurrency.json on every pass; OMP/MKL per worker = {omp}.",
                  "The ladder and the growth cycles still preempt the mill entirely — "
                  "this concurrency applies among mill workers only.",
                  "",
                  f"CONCURRENCY={win}", ""]
        (MILL / "CONCURRENCY.md").write_text("\n".join(lines))
        print(f"[bench] verdict: CONCURRENCY={win} — recorded in mill/CONCURRENCY.md + concurrency.json")
        return 0
    finally:
        MARKER.unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
