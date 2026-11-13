# CONCURRENCY — the mill's measured-concurrency study (Muse's work, Muse's side)

<!-- Muse's work — Muse's side of the BitNet lab. -->

## Status: PENDING — machinery built, study not yet run

Built 2026-11-12 under Arnav's directive that the one-heavy-job-at-a-time
limit is a research problem, not a law. The study script,
`mill/bench_concurrency.py`, is complete and self-guarding: it refuses to
start while the ladder, a growth cycle, or any other mill process owns the
machine, and it writes NOTHING unless the whole study completes. At build
time the scale ladder owns the lab (priorities stand: ladder and growth
cycles preempt the mill), so no numbers exist yet. **Any concurrency figure
quoted before this file records a completed study is invented.**

Interim setting — the only one with honesty evidence, because it IS the solo
condition every lab number so far was measured under:

CONCURRENCY=1

## The study (what bench_concurrency.py measures when the lab frees up)

- **Throughput:** a fixed queue of 6 sweep-mode probes (chassis, two shape
  points, a batch variant, the plain-vote control, a deep-narrow shape) at
  0.75 min each, run at 1, 2, and 3 concurrent sweep workers. Solo worker:
  OMP/MKL = 2. Multi-worker: OMP/MKL = 1 each, per the directive. Metric:
  finished probes per hour.
- **Honesty:** 3 of the queue's configs (chassis, dim-256×1, plain+rope) are
  run solo TWICE — the replicate spread is the noise floor — and once inside
  each multi-worker batch. A worker count is honest only if every config's
  concurrent held loss is within max(2 × replicate spread, 0.02) of its solo
  mean. Concurrency must move the clock, not the numbers.
- **Verdict rule:** the winner is the largest worker count with ≥ 10%
  throughput gain over the count below it AND a clean honesty check. The
  bench writes the result here (replacing this page's pending record, with
  all raw numbers) and into `mill/concurrency.json`; screen.py reads that
  file on every pass, and run-forever.sh is adjusted by the main agent to
  match.
- **Scope:** concurrency applies among mill workers only. The ladder and
  the growth cycles still preempt the mill entirely, at any worker count.

## Why this needs measuring at all

The VM has 1.5 shared vCPUs and a 6 GB cap. Two workers at OMP=1 might beat
one worker at OMP=2 (less synchronisation waste, better cache behaviour on
tiny models) — or might halve each other's cache and lose. Torch thread
count can also change reduction order, which is why the honesty check
exists: a throughput win bought by silently shifting held losses would
poison every verdict in the ledger.
