# Muse's work — Muse's side

# Wave 7 · Lens 3 — Measurement Backlog (rotation-7 miner 3)

<!-- Muse's work — Muse's side of the BitNet lab. Every number the program
REFERENCES but has never MEASURED. Sources swept: mill/RIGOR-AUDIT.md (§5a
preflights), mill/PROMOTE.md, mill/CONCURRENCY.md, mill/PRIORITIES.md,
mill/CANDIDATES-A..K headers and bodies, RESULTS-*.md, kernels/RESULTS-KERNELS.md,
kernels-lut/RESULTS-LUT.md, scale-next/NUMBERS.md + REDTEAM-MEASUREMENT.md,
compute/probe_startup.py + probe_phases.py, runs.jsonl.
Rank = (decision weight) / (measurement cost). Cost class per entry:
0-train = no training run at all; piggyback = rides a run already scheduled;
micro-train = ≤ ~5 min of training. Execution order: run every 0-train entry
first in wall-clock order, whatever its rank; rank below is the ratio order. -->

---

## ★ OB-001 · Probe-noise sd at probe budget

- **Quantity:** Sample sd of job zero's held loss at probe budget (75 s /
  1.25 min), across seeds — the noise floor the promotion bar is priced against.
  Today the only number on record is the *full-format* seed sd, 0.0161
  (3 seeds × 8 min), which is a different quantity at a different budget.
- **Cited from:** `mill/RIGOR-AUDIT.md` §5a — "the noise figure it rests on
  **has never been measured**: job zero has never been run at probe budget, on
  any seed"; `mill/PROMOTE.md` probe-bar section — Δ ≥ 0.05 promotes because
  "probe noise at 75 seconds is much larger than the full-format seed sd
  (0.0161)", asserted, not measured; `mill/PREFLIGHT.md` — the check is
  scripted (`mill/preflight.py`, ~5 min) and, as of the 2026-11-12 rigor-fix
  pass, **has not yet run**. Decision depending on it: `PROMOTE_DELTA = 0.05`
  in `mill/screen.py` + PROMOTE.md screens the entire ~638-entry pool; every
  probe verdict, near-miss, and wasted 24-min trial inherits it.
- **Cheapest measurement:** micro-train. Run the already-written preflight:
  job zero at 1.25 min on seeds 0, 1, 2, solo — 3 × 75 s ≈ 4 min total.
  Write the sd to `mill/PROBE-NOISE.md`. No new code.
- **Decision fork:** sd ≤ 0.025 → 0.05 ≥ 2 sd holds, PROMOTE.md's rationale
  becomes a measurement, funnel stands as-is. sd ≈ 0.04–0.06 → 0.05 is ~1 sd:
  roughly a third of flat ideas promote on noise, the trial queue drowns —
  raise `PROMOTE_DELTA` to ceil(2 × sd) in both `screen.py` and PROMOTE.md
  (the preflight script already prints the replacement value). sd ≥ 0.10 →
  the probe is a coin flip at any plausible bar: the funnel itself is wrong
  at 75 s — lengthen the probe or go step-boxed before another pass is trusted.

## ★ OB-002 · Sweep-vs-subprocess parity: `held_init` = 8.3138, and the `held_final` gap

- **Quantity:** (a) Seed-0 `held_init` from the sweep path, claimed to be
  exactly **8.3138**; (b) the sweep-vs-process difference in `held_final` for
  the identical champion config at probe budget. Neither has ever been
  recorded — no `mill/ledger.jsonl` exists yet.
- **Cited from:** `mill/RIGOR-AUDIT.md` §2b (NOT-YET-CHECKABLE) and its
  first-pass checklist items 1–2; `mill/PREFLIGHT.md` check (b). The value
  8.3138 itself is real in exactly one place: `runs.jsonl`,
  `layered_half_rope` seed 0 (`held_init: 8.3138`, seeds 1/2 are
  8.2652 / 8.2892). Decision depending on it: every sweep-mode verdict is
  compared against a sweep-measured job zero while process-mode verdicts are
  compared against the same baseline — if the sweep's init/stream replication
  is broken, **no sweep verdict stands**, and sweep is the default path for
  all config variants (`mill/IDEA-POOL.md` header).
- **Cheapest measurement:** 0-train for (a): one seed-0 sweep construction +
  init eval only — seconds of compute, no training steps; compare to 8.3138
  character-for-character. (b) is micro-train: one process-mode champion
  probe (75 s) against the sweep job zero from the same pass.
- **Decision fork:** (a) exact match and (b) gap inside the OB-001 noise →
  cross-mode verdicts become real; preflight closes. (a) any mismatch →
  halt all sweep screening, fix `sweep_probe.py`'s replication of
  `train.py:main()` first — cheaper now than after a generation of verdicts
  is on the ledger. (b) gap larger than probe noise with (a) clean → the
  two paths train differently (reseeding / sampler order); verdicts must be
  mode-segregated until the divergence is found.

## ★ OB-003 · Process startup cost as a share of a 75 s probe

- **Quantity:** Seconds (and % of the 75 s probe budget) spent before the
  first training step in process mode: bare python, `import torch`,
  `import train`, corpus memmap + `held_windows()` construction, model +
  trainer construction, and the initial `held_loss()` eval — itemised, solo
  and under typical lab load.
- **Cited from:** `mill/IDEA-POOL.md` header — "On this VM, process startup
  (torch import) plus data setup is **a large share of a 75-second probe's
  cost** — the sweep removes it per-probe." No number is given anywhere.
  Decision depending on it: sweep is the DEFAULT execution path and process
  mode is reserved for code-path changes, i.e. the mill's whole two-mode
  architecture — and its complexity, parity risk (OB-002) and frozen-parser
  hazard (RIGOR-AUDIT §4.4) — is bought with this unmeasured saving. The
  measuring instruments already exist and have no recorded output:
  `compute/probe_startup.py` (5 snippets × 2 reps, self-reporting wall/CPU/RSS)
  and `compute/probe_phases.py` (imports / setup / per-phase timing); there
  is no results file for either in `compute/`.
- **Cheapest measurement:** 0-train. Run `compute/probe_startup.py` once on
  a free lab (~1 min), append one `held_loss()` timing (128 windows) from
  `probe_phases.py`'s setup phase. Record per-phase seconds in the file that
  should exist: `compute/STARTUP.md`.
- **Decision fork:** Startup ≥ ~20 s (≥ 25% of probe) → sweep's premise is
  proven; keep both modes and the parity burden. Startup ≈ 8–15 s → sweep
  still wins per batch, but a *longer* process-mode probe recovers most of
  it — re-price process entries before deferring flags for sweep's sake.
  Startup ≤ ~5 s → the two-mode split is complexity bought for nothing:
  collapse to process mode, delete the parity problem (OB-002b) and the
  frozen sweep parser with it.

## OB-004 · LUT / int8 matmul timing in the dedicated LUT bench

- **Quantity:** Median ms/call at N = 8192 (one trainer step's rows) for
  `lut2`, `lut4`, and `int8mm` vs the fp32 `ref`, per lab shape, plus the
  per-rung block/full-model totals — in `kernels-lut/bench_lut.py`'s own
  variants and accounting (table construction inside the timed region,
  weight codes excluded).
- **Cited from:** `kernels-lut/RESULTS-LUT.md` — "Speed: **NOT MEASURED —
  no verdict**"; correctness is proven bit-exact (50 checks, max abs error
  0.0) and the timing table is "Deferred — lab contention", gated on one
  named command. Decision depending on it: whether the LUT family lives at
  all on Muse's side, and what bar a future C kernel must beat. Note the
  trap this entry closes: `kernels/RESULTS-KERNELS.md` §1 *did* time a
  different torch-emulated LUT g=4 (8–49 s/call, "a dead end on this
  stack") — the record currently holds both "LUT is timed and dead" and
  "LUT speed is not measured", for two different implementations, and
  either sentence can be quoted against the other.
- **Cheapest measurement:** 0-train. One command on a free lab, already
  written in RESULTS-LUT.md: `bench_lut.py timing --wait-s 600`; it appends
  to the existing `kernels-lut/results.jsonl` (which today contains only
  `phase: correctness` lines).
- **Decision fork:** lut2/lut4 lose to `ref` by ≥ 5× (the file's own
  design-level expectation) → close the torch-LUT line permanently, keep
  `int8mm`'s number as the integer-GEMM bar for any off-torch serving work.
  Any variant within ~1.5× of `ref` → the kernels-bench verdict was an
  artefact of its implementation; the LUT entry re-opens, with the
  STE-wrapper caveat from RESULTS-LUT.md still gating trainer use.
  `int8mm` beats `ref` anywhere → first real integer-GEMM signal on this
  CPU build; contradicts kernels §1 and demands a re-check there before
  either number is quoted again.

## OB-005 · Counter saturation in real champion runs

- **Quantity:** End-of-run distribution of the vote counters themselves:
  fraction of `c1`/`c2` sitting exactly at the ±V = ±32 clamp, the full
  |counter| histogram, per layer — for the champion recipe at full format.
- **Cited from:** Referenced everywhere, logged nowhere. `runs.jsonl`
  records `state_hist` and `mean_flip_share` but **no counter field at
  all** (key list verified: arm, steps, held, state_hist, flip share, … —
  no counters). Yet: `mill/CANDIDATES-G.md` G-026 is built on "the final
  counters are clamped ±32 and are discarded unread" and predicts
  −0.01..−0.04 from resolving pending flips; the frustration census
  (PRIORITIES.md rank 4, WH-051) predicts 4–8% frustrated in champion-family
  runs vs > 15% catastrophe-class; `RESULTS-ROUND2-2026-11-12.md` rejected
  the carry arm (int16, no clamp) against a baseline whose clamp occupancy
  was never measured — if almost no counter ever reaches ±32, carry was
  rejected for a mechanism that barely engages. Decisions depending on it:
  G-026/G-030 readout priority, the carry verdict's interpretation, and
  every V-scaling entry's premise.
- **Cheapest measurement:** Piggyback, 0 extra training. Counters are not
  saved by any current run, so: add a one-line histogram dump
  (`|c| ∈ {0, 1–7, 8–15, 16–31, 32}` × layer) to the *next already-scheduled*
  champion-format run's record — or, standalone, read them off one 8-min
  seed-0 run. No eval passes, no new arm.
- **Decision fork:** Clamp occupancy < 1% → saturation is a non-event:
  G-026's pending-flip pool is tiny (demote it), carry's rejection stands
  clean, V entries argue from flip share instead. Occupancy 4–8% → the
  census prediction lands; G-026/G-030 keep their top readout slots and
  the histogram becomes a standing per-run record. Occupancy > 15% → a
  sixth of the model's evidence is being silently truncated every run:
  the clamp, not the vote, is a first-order mechanism — V / counter-width
  entries jump the queue and round 2's carry result must be re-read as
  "the right idea at the wrong setting", not a closure.

## OB-006 · The champion reference itself: 2.8580 ± 0.0161 as a mill constant

- **Quantity:** The gen-0 champion reference as the *mill* holds it — a
  fresh, fingerprinted measurement of `layered_half + rope` at full format
  under current `train.py` and current `corpus.u16`. What exists instead is
  a prose transcription: `mill/screen.py:64-65` hardcodes
  `DEFAULT_CHAMPION = {ref_mean: 2.8580, ref_sd: 0.0161, from RESULTS-ROPE}`;
  `mill/champion.json`, `mill/ledger.jsonl` and `mill/trials.jsonl` do not
  exist; `mill/PROMOTE.md` concedes gen 0's reference "carries no
  fingerprint" (fingerprints begin with the first mill-installed champion).
- **Cited from:** `mill/PROMOTE.md` (adoption bar 2.8258 = 2.8580 −
  max(2 × 0.0161, 0.01); stale-reference guard), `mill/RIGOR-AUDIT.md`
  §§2c/5b. The underlying per-seed values *are* in `runs.jsonl`
  (2.8765 / 2.8477 / 2.8497 — transcription verified, mean/sd recomputed by
  the audit), so this is not a wrong number; it is an *unanchored* one:
  measured once, in a different code/corpus moment, never re-measured by
  the system that judges everything against it. Decision depending on it:
  literally every adoption the mill will ever make.
- **Cheapest measurement:** 0-train half: confirm no drift inputs — hash
  `train.py` + `corpus.u16` now and record them as gen 0's retroactive
  fingerprint. Micro/medium half: one fresh seed-0 full-format run
  (8 min, solo) under current code; compare its held to 2.8765.
- **Decision fork:** Fresh seed 0 within ±0.016 of 2.8765 → reference
  anchored; the 2.8258 bar stands with a fingerprint. Deviation
  0.02–0.06 → JEPA-window drift is live in the reference itself: trigger
  PROMOTE.md's own fourth-job control early — re-run all 3 seeds and
  re-issue the bar before the first trial is judged. Deviation > 0.06 →
  the champion the mill defends is not the champion the current code
  trains; every queued verdict pauses until the reference is re-measured
  in full.

## OB-007 · The champion's actual zero fraction (the "~42%" figure)

- **Quantity:** The zero share of the trained champion's effective weights
  (t1 + t2 ∈ {−2..+2}), overall and per layer/role — and, separately, the
  plain (single-component) arm's zero share that the ~42% figure may
  actually describe.
- **Cited from:** `mill/CANDIDATES-A.md` and `mill/CANDIDATES-B.md` both
  reason from "~42% of ternary weights are already zero" / "the ~42% zero
  fraction is load-bearing for BitNet quality (built-in feature
  selection)" — the premise for the zero-ward vote pricing (A-009) and
  the zero-cull wild card (70% cull priced against a 42% baseline). But
  the lab's own record disagrees with itself: `runs.jsonl`'s recorded
  `state_hist` for the champion reads **0: 0.275–0.280** across seeds,
  while `kernels-lut/RESULTS-LUT.md` drew its test weights from "the
  ladder's recorded state distribution (−1: 0.344, 0: 0.308, +1: 0.344)".
  Three numbers — 42%, 30.8%, 27.5–28.0% — circulate for overlapping
  quantities, and no file says which object each belongs to.
- **Cheapest measurement:** 0-train. The effective-weight figure is
  already recorded — recompute it from `runs.jsonl` (one grep + mean over
  the three champion seeds) and write the per-object definitions down.
  The per-layer split needs one state dump (rides OB-005's run, free).
- **Decision fork:** Champion effective zeros confirmed ≈ 28% → the 42%
  premise is retired wherever it prices an entry: A-009's and the
  zero-cull's effect sizes are re-based (a cull to 70% is a +42-point
  intervention, not +28), and RESULTS-LUT's test distribution is
  corrected to the real one before OB-004's timings are interpreted.
  42% turns out to be the *plain* arm's number → both figures survive but
  get labelled per-arm, and "load-bearing feature selection" claims must
  say which trainer's sparsity they mean. Either way the fork is the
  same work: one canonical, per-arm, per-layer table replaces a slogan.

## OB-008 · Steps actually bought under contention, at probe AND trial format

- **Quantity:** Completed steps (and resulting held) for the champion
  config at workers = 1, 2, 3, measured at *both* budgets that verdicts
  use: 75 s probes and 8-min trial seeds — not only at the study's
  0.75-min probe size.
- **Cited from:** `mill/CONCURRENCY.md` — "Status: PENDING — machinery
  built, study not yet run… **Any concurrency figure quoted before this
  file records a completed study is invented**"; interim `CONCURRENCY=1`.
  `mill/RIGOR-AUDIT.md` §6b: the study as designed licenses **0.75-min
  sweep probes only**, while the setting would govern 1.25-min probes and
  the 8-min trial seeds that decide adoptions; its 0.02 honesty tolerance
  is "an asserted constant, not derived from measured probe seed noise"
  (depends on OB-001). The only contention data in the whole record is an
  anecdote: `RESULTS-JEPA-2026-11-12.md` — identical configs took
  129–139 steps in one window vs 154–170 in another (≈ +0.06 held riding
  on step count). Decision depending on it: whether workers > 1 may run
  verdict-bearing work at all, and whether PROMOTE.md's "trial seeds
  always run solo" is a necessity or a superstition costing ~3× throughput.
- **Cheapest measurement:** Piggyback on the designed study: run
  `mill/bench_concurrency.py` as written (6 × 0.75 min × 3 worker counts),
  plus **one** added leg — one contended 8-min trial-format seed vs its
  solo replicate (~16 min total). That single leg is the difference
  between a screening licence and an adoption licence.
- **Decision fork:** Contended held within max(2 × replicate spread,
  derived tolerance) at both formats → workers > 1 licensed for trials
  too; mill throughput roughly triples per added honest worker. Honest at
  0.75 min, shifted at 8 min → concurrency stays probes-only (PROMOTE.md's
  current rule becomes measured law, not caution). Shifted even at probe
  format → `CONCURRENCY=1` is permanent on this VM, the throughput roadmap
  moves to ashp offload (already measured ~3× per step,
  `compute/COMPUTE-ASHP.md`), and every step-count-sensitive verdict gains
  a `contended` re-queue rule.

## OB-009 · Fused vote-update speedup inside the real trainer

- **Quantity:** Per-step wall/CPU time of `Layered.step`'s vote-update
  block, current vs fused variant, **in situ** in `train.py` — where
  counters are updated in place and no state clone exists.
- **Cited from:** `kernels/RESULTS-KERNELS.md` §2 — bitwise-identical
  fused variant, champion 1.7–1.8×, but the harness clones state for both
  arms ("in the real trainer there is no clone — so gross-vs-net brackets
  the true gain"), and the 2M arm "caught a contention spike" (4.6×
  gross, explicitly untrusted). Decision depending on it: whether to edit
  the trainer's mechanism loop — the runner-up kernel recommendation,
  queued behind the RoPE trial — and how CANDIDATES-C's kernel family
  prices every vote-update entry.
- **Cheapest measurement:** 0-train as a bench, minutes as a probe:
  re-run `kernels/bench_vote.py` with the clone removed from both arms
  (the in-situ condition) on a free lab, champion shape, ≥ 20 reps,
  median. If it survives, one paired 75 s A/B probe confirms steps-gained
  end-to-end.
- **Decision fork:** In-situ gain ≥ 1.5× → adopt into `train.py` behind
  its bitwise-identity proof (state err 0.0 already shown); every vote
  arm's probe buys ~half again as many steps. Gain 1.1–1.5× → worth it
  only bundled with the RoPE kernel trial, not as its own trainer edit.
  Gain ≈ 1.0× → the 1.7× was clone-accounting; the kernel family's
  vote-update entries are re-priced to zero and the bench harness's
  method (clone both arms) is flagged wherever else it was used.

## OB-010 · Complex-RoPE gain in training: the backward pass and the full step

- **Quantity:** End-to-end training-step time (forward + backward +
  vote update) with `train.py`'s slice/stack `rotated()` vs the complex-
  multiply rotor — the number a mill trial would actually harvest.
- **Cited from:** `kernels/RESULTS-KERNELS.md` §3 + Recommendation — the
  complex rotor is the mill's #1 kernel pick on a forward-only bench:
  combined rope+attention path 1.4–2.9× across two contended runs, with
  the claim "training also pays `rotated()`'s slice/stack cost again in
  the backward pass, so the training gain **should be at least** what is
  measured here" — the backward half is asserted, and single-op rope
  timings in the same table swing 0.078–0.27 s (reference) under
  contention. Decision depending on it: this variant gets the first full
  mill trial slot (24 min) ahead of every other kernel entry.
- **Cheapest measurement:** 0-train beyond a profiling run: use the
  existing instrumented copy `compute/probe_phases.py` pattern — 12 timed
  steps per variant, champion shape, solo, reporting fwd / bwd / vote
  phases separately (~2 × 40 s). No `train.py` edit.
- **Decision fork:** Full-step gain ≥ 1.3× → trial slot justified as
  first priority; expected steps-per-probe gain is written into the
  trial's pre-registration. Gain concentrated in forward only, full-step
  ≈ 1.1× → still adoptable (bitwise identical, err 0.0) but demoted
  behind OB-009 if that lands ≥ 1.5×. Full-step ≈ 1.0× → attention is
  not the step's bottleneck at lab scale (vote update / matmul is); the
  kernel recommendation is withdrawn and CANDIDATES-C family C re-ranks
  around the measured phase shares.

## OB-011 · The 50M rung's true seconds-per-step (with checkpointing)

- **Quantity:** Measured s/step for the 768 × 7 rung with `--ckpt` on
  this VM, including checkpoint save cost — replacing an extrapolation
  and a driver estimate that currently disagree by construction.
- **Cited from:** `scale-next/NUMBERS.md` — the rung has "**no completed
  56-step run yet**"; its ~91 s/step is a *driver estimate* (5,100 s),
  a two-point fit (`s/step ≈ 2.08 + 9.39e-7 · MACs/token`, cross-checked
  at ±30%) predicts ~52 s/step before checkpointing, and the file quotes
  budgets as fit → fit × 1.3 → driver-anchored ranges. Decisions
  depending on it: the entire overlap program's costing — smoke (a)
  ≈ 2.0–2.6 h and full (b) ≈ 9.04 h of member runs plus generalist runs
  at 42–74 s/step (`scale-next/NUMBERS.md` §§a–b) — and every
  loss-per-byte statement that needs the 50M point
  (only a 2-step smoke, held 6.5932, exists, explicitly "not comparable").
- **Cheapest measurement:** Micro-train: launch the ckpt rung, time
  steps 2–6 individually plus one checkpoint save, kill it — ~8 min
  buys s/step to a few percent instead of ±30–75%. (The first 56-step
  completion, whenever the ladder runs it, supersedes this for free.)
- **Decision fork:** True value near 52–65 s/step → overlap (b) shrinks
  by ~30%; the generalist long pole (0.82–1.43 h) re-plans and the 50M
  rung joins loss-per-byte honestly. Near 91 s/step → driver estimate
  vindicated, fit discarded for ckpt shapes; (b)'s budget stands and
  any 50M-inclusive design pays it knowingly. Above ~110 s/step → the
  rung is not a rung on this VM at all: scale claims cap at 10M until
  ashp/GPU execution is measured, and ladder reporting says so.

## OB-012 · Real packed serving bytes: 0.25 vs 0.375 vs 0.5 B per weight

- **Quantity:** The actual bytes of a lossless packed artifact for the
  layered champion — t1 + t2 is a **5-level** value (−2..+2) — produced
  by working pack/unpack code with a round-trip test, not by a stated
  convention.
- **Cited from:** `scale-next/NUMBERS.md` §1 prices every rung at
  **0.25 B/weight** (2 bits) while conceding in its own caveat that
  5 levels "strictly needs 3 bits packed (0.375 B/w), or 0.5 B/w if the
  two components are packed separately" — totals swing 26.0 MB →
  32.2 MB → 38.4 MB at the 50M rung depending on the choice;
  `scale-next/REDTEAM-MEASUREMENT.md` §1 makes the same point as an
  attack: a 3-bit code "is legitimate — but only with working
  pack/unpack code and a lossless round-trip test in the repo, not as
  an assumption in a spreadsheet", and shows the ensemble-vs-baseline
  headline can hide a 1.95–2.91× budget error. Decision depending on
  it: every loss-per-byte claim in the program and the overlap
  program's "equal total serving bytes" headline equality.
- **Cheapest measurement:** 0-train. Write the packer (base-5 / 3-bit
  and separate 2-bit × 2), pack the champion's recorded state
  distribution (or one state dump from OB-005's run), unpack, assert
  identity, report real bytes for champion / 2M / 10M shapes. An
  afternoon-scale script, zero training, zero eval.
- **Decision fork:** 3-bit packing round-trips losslessly → adopt
  0.375 B/w as *the* convention with code behind it; NUMBERS.md's
  tables are re-issued once, rankings unchanged per its own sensitivity
  note. Only separate-component packing works cleanly → 0.5 B/w is the
  honest number; all per-byte claims shrink by the stated factor and
  the overlap budgets are re-cut before any build. Packing overhead
  (indices/alignment) pushes real bytes above both → the per-byte
  metric itself gets a measured fudge factor, published with the
  artifact, instead of a convention chosen per spreadsheet.

---

*Count: 12 entries (OB-001–OB-012). ★ Top 3: OB-001 probe-noise sd,
OB-002 held_init parity, OB-003 startup-cost share. Zero-training entries
(OB-002a, OB-003, OB-004, OB-007, OB-012, and the bench halves of OB-009 /
OB-010) can all land in a single free-lab hour, before any of the
micro-train entries are scheduled.*
