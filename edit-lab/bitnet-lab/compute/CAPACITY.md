# CAPACITY — the Compute Department's scoreboard (Muse's work, Muse's side)

Mission (Arnav's order, 2026-11-12): compute is the bottleneck strangling the sprint.
This ledger tracks the lab's real throughput — finished, trustworthy training runs
per hour — before the department's levers and after each one lands, measured the
same way every time.

## How the numbers are taken

- **Standard units.** Probe unit = mill probe (champion shape `layered_half --rope`,
  75 s budget). Trial unit = mill full trial seed (champion shape, 8 min budget).
  Ladder units = 56-step runs at the 2M shape (dim 288 × 2 layers) and the 10M
  shape (dim 512 × 3 layers).
- **Two columns, always.** *Solo reference* = the unit's wall time with the machine
  effectively to itself (from the lab's recorded runs). *Delivered* = what the
  sprint actually got per hour under real contention (all streams sharing
  1.5 vCPU quota). The gap between the columns is the contention tax — the thing
  this department exists to shrink.
- Every entry names its source (log/record/measurement) and date. No estimates
  dressed as measurements: derived rates say "derived".

## Baseline — before the department (Thu 2026-11-12, ~20:07 PT)

Machine state at founding: 4+ heavy training processes sharing the VM
(ladder driver on the 10M rung, weights-reader v3, flag-factory baselines),
RAM ~0.9 GB free of 7.9 GB, CPU quota 1.5 vCPU on an EPYC 9D25 host.

| Unit | Solo reference | Derived solo rate | Delivered under sprint contention |
|---|---|---|---|
| Ladder 2M unit (56 steps) | 287.7 s (ladder-driver.log, 02:07Z) | ~12.5 runs/h | not measured as a rate; the ladder took ~1 h 47 min wall for the 10M seed-0 unit slot incl. queueing behind other work |
| Ladder 10M unit (56 steps) | 722.9 s (ladder-driver.log, 03:48Z) | ~5.0 runs/h | seed 1 still in flight at founding, hours after seed 0 |
| Mill probe unit (75 s) | 75 s budget by design | 48 probes/h theoretical | **0 probes delivered** — the mill loop has yielded to heavier work on every pass so far (etiquette contention) |
| Mill trial unit (8 min) | 480 s budget by design | 7.5 runs/h theoretical | 0 delivered (no promotions yet; trials have not run) |
| Restart recovery | — | — | **0 of 2** interrupted runs recoverable today (JEPA run 1, scale ladder run 1 — both restarted from scratch; train.py has no resume) |

## Levers in flight (each gets a row here when it lands, with its measured delta)

1. **Profile first** → `COMPUTE-AUDIT.md` (where the time goes; picks the targets).
2. **Checkpoint-resume** → `train_ckpt.py` + `RESUME-PROOF.md` (an interrupted run
   stops costing its full length; unlocks the 7–11 h confirmation runs).
3. **Job queue** → `queue/` (priorities replace pgrep-and-yield; probes stop
   starving behind whatever started first).
4. **Concurrency study** (mill's own `bench_concurrency.py`, already built by the
   mill stream) — verdict lands in `mill/CONCURRENCY.md`; this ledger records the
   delivered probes/h before vs after it is adopted.
5. **ashp offload** → `COMPUTE-ASHP.md` (a second machine for probes, if the
   measured numbers and the thermal law allow it).

## After-action entries

_(appended as levers land — date, lever, unit, before → after, source)_

- **2026-11-12 ~20:11 PT — Job queue BUILT, not yet adopted.** `queue/labqueue.py`
  (stdlib-only, directory-per-state + atomic rename + flock'd claims; priorities
  ladder/growth > trial > probe > benchmark; lease/heartbeat claims, stale-claim
  reaping, release without consuming an attempt). 21/21 tests pass under both
  system python3 and the lab venv python, including 20 parallel claimers with
  zero double-claims. Delivered-throughput delta: none yet — adoption by the
  mill/ladder/growth streams is a separate, later step (plan in `queue/QUEUE.md`).
  What it retires when adopted: pgrep-and-yield etiquette and the mill's
  claims.jsonl/mill.lock bookkeeping.
- **2026-11-12 ~20:31 PT — ashp offload MEASURED: GO for mill probes**
  (`COMPUTE-ASHP.md`). The laptop's CPU runs the lab's own train.py ~3× faster
  than the VM per step: champion shape 1.06 s/step (8 threads) vs the VM's
  ~2.84–3.13 s/step; 2M ladder shape 1.63 s/step vs VM 5.14 s/step solo. A real
  75 s-budget probe on ashp completed 75 steps (86.6 s end-to-end) vs ~24–26
  steps in a VM probe — one ashp worker ≈ 41 finished probes/hour, untaxed by
  VM contention (VM delivered so far: 0). Thermals a non-issue at probe scale
  (peak 51 °C CPU burst / 57 °C GPU burst vs the ~88–90 °C abort line; the
  1650 Ti is hardware-capped at 50 W, so the house power-limit intent is
  already satisfied). GPU is faster still (8.3 steps/s) but stock train.py has
  no device handling — it needs a `--device` change before use. Ladder-class
  long runs on ashp: NO-GO until a monitored sustained trial (no true CPU-temp
  sensor on the box; SSH drops at ~23 s, so a runner must be fire-and-forget
  with file-based completion polling — both noted in the report). Status:
  measured and recommended; the probe runner itself is a later build.
