# Cycle 3 — registered surfaces and targets (prep, 2026-11-11)

Prepared, not run. Cycle 3 (`growth-cycle-003`) has not been
attempted; this file registers its judge surfaces and its targets
so the cycle itself starts from a written record. Machine-readable
form: `growth/cycle3_surfaces.json`.

## Why these surfaces

Both cycle-2 births were decided on the phase-3 held slice —
n=20 per target slice, now spent as a decision surface twice. The
cycle-2 report's instruction was explicit: a LARGER pristine
phase-3-style held slice (new template families, disjoint
names/idioms), and a second name-intent partition so the intent
judge is not one fixed surface. The spent slice also explains the
remaining targets by itself: subset sizes on phase-3 held are
accumulator n=9 (3 pos), comparison **n=0** (no judge ever
existed), range n=9 (3 pos).

## Surface 1 — phase3x held (sealed)

- Builder: `factory/held_slice_v2.py`; data:
  `growth/data/phase3x_held.json`; manifest:
  `growth/data/phase3x_manifest.json`.
- 25 new template families written; 23 survived contamination
  filtering (the two zip-comprehension families were dropped as
  too close to phase-3's zip families — the filter working, not a
  defect). **n = 69** items: clean 23, wrong-operator 19,
  missing-return 12, off-by-one 10, swapped-operands 3,
  mutable-default 2.
- Labels execution-verified: all 25 raw families and all 69
  written items re-checked by execution (clean runs clean on its
  probes; every defect differs behaviourally from its family's
  correct body on ≥1 probe; mutable-default via sequential-call
  probes). 0 failures.
- Target-slice subsets (n / positives): wrong-operator/expression
  45, wrong-operator/comparison 12/4, wrong-operator/accumulator
  12/4, off-by-one/index 57, off-by-one/range 12/4.
- **Sealed**: never trained on, never used for candidate
  selection; no model was measured on it in this prep. Wiring it
  in as a gate is cycle 3's own step.

## Surface 2 — name-intent partition 2 (comparison/accumulator)

- Builder: `factory/name_intent2.py`; data:
  `growth/data/name_intent2_train.json` (n=128) +
  `growth/data/name_intent2_held.json` (n=128, the held split);
  manifest: `growth/data/name_intent2_manifest.json`.
- Ten new intents, disjoint from partition 1 in ids, names,
  identifier vocabulary and neutral names — comparison:
  count_above, count_between, first_index_above, any_below,
  all_above; accumulator: running_total, running_product,
  weighted_total, sum_squares, sum_upto_n.
- Same construction discipline as partition 1 (construction-known
  labels, execution sanity + independent re-verification: 50
  clean + 78 defect items checked per partition, 0 failures;
  contamination-filtered against all corpora AND partition 1,
  text mode + name/shape guard). Two generator defects were
  caught by the verification passes during the build and fixed
  (a sum_upto_n idiom that collided with phase-3's total_upto;
  orphan handling when filtering removes a group's clean item).
- Slice routing is exact under `swarm.decomposers.slice_of`:
  all 24 comparison-intent wrong-operator held items slice as
  "comparison"; all 18 accumulator-intent ones as "accumulator".
- Held subsets for the targets (n / pos): accumulator 64/18,
  comparison 64/24, off-by-one/range 28/12.

## Registered targets for growth-cycle-003

All three are the slices still routed "whole" after cycle 2
(the cycle-2 addendum's list). Parents identified; no training
was done in this prep.

| target | parent | prospective child | state |
|---|---|---|---|
| wrong-operator/accumulator | bug-wrong-operator-model | bug-wrong-operator-accumulator-model | child file exists (Phase-era birth, heldout 0.7778 on its era slice) but composer routes the slice to "whole" — the parent serves it |
| wrong-operator/comparison | bug-wrong-operator-model | bug-wrong-operator-comparison-model | no child file exists; the spent phase-3 slice had NO comparison subset (n=0) — this target never had a judge until now |
| off-by-one/range | bug-off-by-one-model | bug-off-by-one-range-model | child file exists (Phase-era birth, heldout 0.7778 on its era slice) but composer routes the slice to "whole" — the parent serves it |

Judges for each target: phase3x held subset + name-intent-2 held
subset (table above / `cycle3_surfaces.json`). Parent baselines
on the new judges are cycle 3's first measurement, under its own
protocol.

Learned-say is **not** a cycle-3 target: cycle 2's v2 fit closed
the question (0.7931 vs routed 0.8276).

## Cron readiness (the four blockers from the cycle-2 report)

All four are implemented in `factory/growth_cycle.py` and
verified 2026-11-11:

1. **Cycle-id auto-increment** — no `--cycle-id` → derived from
   the ledger (next: `growth-cycle-003`). Explicit ids reproduce
   cycle-1/2 invocations exactly.
2. **Single-instance lock + lab-busy skip** — `growth/.growth.lock`
   (pid + timestamp, stale after 2h or on dead pid) plus a /proc
   scan for other heavy lab jobs. A skip writes one ledger line
   and exits 0, training nothing. Verified live: with the
   weights-reader v2 worker running, preflight reports
   would-skip ("lab busy: pid 7490 (python3 v2gen.py bases)"); a
   planted live lock produced a real skip (ledger line written,
   exit 0, no run dir). The synthetic test skip line
   (growth-cycle-900) was removed from the ledger afterwards to
   keep the auto-numbering clean; the test is recorded here.
3. **Per-cycle novelty** — keyed by cycle number: intent-cap
   sampling seed (99 + 7919·N), dream-pool band counts, and
   seeded transforms of the candidate grid (epoch ladder steps,
   mixture leans, curriculum-lean swaps, occasional hidden-size
   changes; every change logged into the cycle report's "Novelty
   rotation" section). Deterministic per cycle number — cycle N
   is reproducible, cycle N+1 is a different grid. Legacy
   invocations skip rotation entirely.
4. **Alert path** — rollback, audit failure, or a runner error
   writes `growth/ALERT-<cycle-id>.md` (what failed, what was
   rolled back, battery before/after). Absence = quiet cycle.
   Verified with a synthetic rolled-back cycle (file written,
   contents correct, test file removed).

`--preflight` prints the whole cron decision (derived id,
rotation spec, would-skip + why) without writing anything.

**Ready to schedule on a ~6h cron: yes** — with the standing
caveat that a cycle skips (by design) whenever the weights-reader
or another heavy job holds the VM, so the effective cadence is
"every ~6h when the lab is free."
