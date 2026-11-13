# CANDIDATES-C — second-order candidates for the mill pool (Muse's work, Muse's side)

<!-- Muse's work — Muse's side of the BitNet lab. Assembled 2026-11-12 by the
mill-expansion department (coordinator + four specialists: combinations, champion
mutations, kernel variants, promotion planning). This is a CANDIDATE file: nothing
here is in the pool until the pool's owner merges it — screen.py reads only
mill/IDEA-POOL.md. IDEA-POOL.md and CANDIDATES-A.md were read in full and NOT edited. -->

## Method and ground rules

Built only from the lab's own records (RESULTS-2026-11-11, RESULTS-ROPE-2026-11-11,
RESULTS-HALF-CONTROL-2026-11-12, RESULTS-ROUND2-2026-11-12, RESULTS-JEPA-2026-11-12,
runs.jsonl — every mean/SD below was recomputed from runs.jsonl during assembly).

**Champion (gen 0):** layered_half + rotary + plain votes — held **2.8580 ± 0.0161**,
state 2,211,840 B; dim 192, 4 heads (head_dim 48), 2 blocks, ctx 256, vocab 4096,
884,736 ternary weights, vote threshold V=32, AdamW parts lr 1e-3, betas (0.9, 0.95),
wd 0.0, batch 32.

**Premise correction, stated plainly:** QK-Norm, per-channel scales, gated attention
and friends are NOT confirmed winners — they are untested research-ranked items
already pooled as MILL-101+. Family A therefore uses only MEASURED elements
(trainers × sizes × rotary). Nothing closed is re-proposed anywhere in this file:
overshoot carry (2.8761, rejected), AdamW cooldown (2.9707, rejected), threshold
annealing 8→64 (3.8503), magnitude votes as specified (3.1352; calibrated retest is
pooled as MILL-201..203), the JEPA objective (lost to its own control).

**Costs.** Every entry probes at the standard 75 s / seed 0 (PROMOTE.md) unless its
own text says otherwise. Family A scale entries' FULL form is ladder format
(56 steps; ~12 min/run at 2M, ~25 min/run at 10M), not the 3×8 min trial — read
their predictions at ladder format. Family B process entries are DEFERRED by
screen.py until their flag lands in train.py (pool law). Family C entries cost
nothing until the pending protocol at the end of this file flips them.

---

## Family A — combinations of measured elements (the complete remainder of the grid)

Eligible grid: trainers {plain votes, layered votes, STE} × sizes {half (dim 192×2,
884,736), full (dim 192×4, 1,769,472), scale2m (dim 288×2, 1,990,656, 56 steps),
scale10m (dim 512×3, 9,437,184, 56 steps)} × rotary {off, on} = 24 cells. Already
run: 9. Already pooled as bare combos: 3 (plain×half+rotary = MILL-1901,
layered×full+rotary = MILL-1902, STE×half+rotary = MILL-1903). The 12 entries below
are exactly the remaining cells, in ranked order. All are config-only with existing
flags → all sweep. Note: the 10M comparator (`layered_rope_scale10m`, 2.9472) is
n=1 (seed 0 only; seed 1 never landed) — every 10M prediction carries that bound.

### C-A01 · STE at the 2M ladder rung, with rotary
- **source:** combination of measured elements (STE: `ste_half` 2.8205 ± 0.0069, best quality in RESULTS-HALF-CONTROL-2026-11-12, and `ste` 2.9952 in RESULTS-2026-11-11; scale2m rung + rotary: `layered_rope_scale2m` 3.2745 ± 0.0119, 3 seeds × 56 steps, runs.jsonl)
- **mechanism:** The gradient trainer rides the one fully-measured ladder rung with rotary. At 56 fixed steps there is no steps-per-minute confound — this is the cleanest per-step trainer comparison the lab has never had above half size.
- **train.py:** no change; existing flags only — `--arm ste --rope --dim 288 --layers-n 2`. Full-trial form is ladder format: add `--steps 56 --minutes 12 --tag scale2m` (recorded as `ste_rope_scale2m`, mirroring run_scale_ladder.py). STE state at this rung: 23,887,872 B.
- **mode:** sweep — config-only via existing flags; runs in mill/sweep_probe.py
- **prediction:** At probe scale (75 s, time-boxed) expect it to beat the layered-rung direction but read noisy; at ladder format expect held ~3.15–3.22, i.e. −0.05..−0.12 vs the rung's 3.2745 — the STE-vs-layered gap at equal steps was 0.0785 at half size (2.8205 vs 2.8990, step counts overlapping), and rotary is already in both sides of this comparison.
- **status:** queued
```mill
id: C-A01
mode: sweep
run: --arm ste --rope --dim 288 --layers-n 2
```

### C-A02 · STE at full size, with rotary
- **source:** combination of measured elements (STE full: 2.9952 ± 0.0245, RESULTS-2026-11-11 / RESULTS-HALF-CONTROL-2026-11-12; rotary: −0.0411 on the layered_half chassis, 2.8990 → 2.8580, RESULTS-ROPE-2026-11-11)
- **mechanism:** Rotary has only ever ridden a vote trainer. This tests whether the lab's one confirmed win transfers to the gradient trainer at the size where STE's recipe was actually tuned (lr 3e-3, warmup 200, wd 0.01).
- **train.py:** no change; existing flags only — `--arm ste --rope` (dim 192, 4 blocks defaults reproduce the measured `ste` arm exactly). STE state 21,233,664 B.
- **mode:** sweep — config-only via existing flags; runs in mill/sweep_probe.py
- **prediction:** −0.02..−0.05 vs the `ste` arm's 2.9952 at full format (rotary's vote-side gain was 0.0411 with no step confound); at probe scale the same direction, smaller and noisier because the 4-block arm takes few steps in 75 s. A flat result is also valuable: it would make rotary a vote-trainer-specific win.
- **status:** queued
```mill
id: C-A02
mode: sweep
run: --arm ste --rope
```

### C-A03 · Plain votes at the 2M ladder rung, with rotary
- **source:** combination of measured elements (plain votes: `plain_half` 2.9010 vs `layered_half` 2.8990 — equal within 0.0020, RESULTS-HALF-CONTROL-2026-11-12; scale2m rung + rotary: `layered_rope_scale2m` 3.2745 ± 0.0119, runs.jsonl)
- **mechanism:** The single-component trainer on the measured rung. If plain ties layered at scale as it did at half size, the rung's result is available at half the mechanism state (2,488,320 B vs 4,976,640 B). NOTE: already queued as the ride-along in run_scale_ladder.py — merge, don't duplicate the run.
- **train.py:** no change; existing flags only — `--arm plain --rope --dim 288 --layers-n 2`. Full-trial form is ladder format: add `--steps 56 --minutes 12 --tag scale2m` (recorded as `plain_rope_scale2m`).
- **mode:** sweep — config-only via existing flags; runs in mill/sweep_probe.py
- **prediction:** Held within ±0.03 of the rung's 3.2745 at ladder format — the half-control showed levels earn nothing at equal size/steps (gap 0.0020, sign flips per seed), and nothing about dim 288×2 should change that. The win condition is a tie at half the state, judged per byte.
- **status:** queued
```mill
id: C-A03
mode: sweep
run: --arm plain --rope --dim 288 --layers-n 2
```

### C-A04 · Plain votes at full size, with rotary
- **source:** combination of measured elements (plain full: 3.0743 ± 0.0316, RESULTS-2026-11-11; rotary: −0.0411 on layered_half, RESULTS-ROPE-2026-11-11)
- **mechanism:** Completes rotary × plain votes (the half-size cross is already pooled as MILL-1901). Tests whether rotary's gain survives at the size where plain votes take only ~115–124 steps in 8 minutes.
- **train.py:** no change; existing flags only — `--arm plain --rope` (defaults reproduce the measured `plain` arm). State 2,211,840 B.
- **mode:** sweep — config-only via existing flags; runs in mill/sweep_probe.py
- **prediction:** −0.02..−0.05 vs 3.0743 at full format; at probe scale expect a smaller, noisier gain in the same direction (fewer steps per probe at full size). If the gain vanishes here but holds at half, rotary's value is step-count-dependent — a real finding either way.
- **status:** queued
```mill
id: C-A04
mode: sweep
run: --arm plain --rope
```

### C-A05 · Layered votes at the 2M ladder rung, NO rotary (rung ablation)
- **source:** combination of measured elements (the rung itself: `layered_rope_scale2m` 3.2745 ± 0.0119 at 56 steps, runs.jsonl; rotary's only measurement is at half size: −0.0411, RESULTS-ROPE-2026-11-11)
- **mechanism:** The exact rung configuration minus `--rope` — the built-in position table returns. This is the control that prices rotary at scale; every other scale entry in this family is read against a rung whose rotary contribution is currently assumed, not measured.
- **train.py:** no change; existing flags only — `--arm layered --dim 288 --layers-n 2` (no `--rope`). Full-trial form: add `--steps 56 --minutes 12 --tag scale2m`.
- **mode:** sweep — config-only via existing flags; runs in mill/sweep_probe.py
- **prediction:** +0.03..+0.06 vs 3.2745 at ladder format (worse without rotary, by roughly the half-size gain); if the gap is ~0, rotary's win does not scale and the ladder's per-byte story needs re-reading.
- **status:** queued
```mill
id: C-A05
mode: sweep
run: --arm layered --dim 288 --layers-n 2
```

### C-A06 · Plain votes at the 2M ladder rung, NO rotary
- **source:** combination of measured elements (plain votes at half/full without rotary: 2.9010 / 3.0743, RESULTS-HALF-CONTROL-2026-11-12 and RESULTS-2026-11-11; scale2m shape: dim 288×2, 1,990,656 ternary weights, runs.jsonl scale records)
- **mechanism:** Plain trainer × ladder size with the position table. Paired with C-A03 it isolates rotary for the plain trainer at scale; paired with C-A05 it isolates trainer (plain vs layered) at scale without rotary.
- **train.py:** no change; existing flags only — `--arm plain --dim 288 --layers-n 2`. Full-trial form: add `--steps 56 --minutes 12 --tag scale2m`. State 2,488,320 B.
- **mode:** sweep — config-only via existing flags; runs in mill/sweep_probe.py
- **prediction:** ~3.30–3.36 at ladder format: the rung's 3.2745 plus rotary's ~0.04, with plain≈layered (0.0020 at half) contributing ~0. Primarily a cell-completing control — its value is making C-A03/C-A05 interpretable.
- **status:** queued
```mill
id: C-A06
mode: sweep
run: --arm plain --dim 288 --layers-n 2
```

### C-A07 · STE at the 2M ladder rung, NO rotary
- **source:** combination of measured elements (STE without rotary at half/full: 2.8205 / 2.9952, RESULTS-HALF-CONTROL-2026-11-12; scale2m shape from runs.jsonl scale records)
- **mechanism:** Completes the 2×2 {STE, layered} × {rotary, table} at the 2M rung with C-A01 and C-A05. Without it, a C-A01 win cannot be split into "STE is better per step" vs "STE uses rotary better."
- **train.py:** no change; existing flags only — `--arm ste --dim 288 --layers-n 2`. Full-trial form: add `--steps 56 --minutes 12 --tag scale2m`. STE state 23,887,872 B.
- **mode:** sweep — config-only via existing flags; runs in mill/sweep_probe.py
- **prediction:** ~3.19–3.27 at ladder format (C-A01's expectation plus rotary's ~0.04). Expected to still beat the layered rung's 3.2745 if the STE per-step advantage is real.
- **status:** queued
```mill
id: C-A07
mode: sweep
run: --arm ste --dim 288 --layers-n 2
```

### C-A08 · STE at the 10M ladder rung, with rotary
- **source:** combination of measured elements (STE: 2.8205 half / 2.9952 full, RESULTS-HALF-CONTROL-2026-11-12; 10M rung + rotary: `layered_rope_scale10m` seed 0 only, 2.9472 at 56 steps, 9,437,184 ternary weights, runs.jsonl)
- **mechanism:** The best-quality trainer at the largest measured size. The 10M rung already showed scale helps at equal tokens (2.9472 vs the 2M rung's 3.2745, albeit n=1); this asks whether STE's per-step advantage survives — or grows — at 9.44M weights.
- **train.py:** no change; existing flags only — `--arm ste --rope --dim 512 --layers-n 3`. Full-trial form is ladder format ONLY: add `--steps 56 --minutes 25 --tag scale10m` (~12 min/seed for the layered rung; STE state 113,246,208 B). A 75 s probe is a smoke/direction read only — it cannot reach 56 steps and must not be verdicted as a rung result.
- **mode:** sweep — config-only via existing flags; runs in mill/sweep_probe.py
- **prediction:** ~2.85–2.92 at ladder format, −0.03..−0.10 vs the rung's single-seed 2.9472 (STE's equal-step advantage was 0.0785 at half size; wider models give STE's latent weights more room, but n=1 comparator means wide error bars).
- **status:** queued
```mill
id: C-A08
mode: sweep
run: --arm ste --rope --dim 512 --layers-n 3
```

### C-A09 · Plain votes at the 10M ladder rung, with rotary
- **source:** combination of measured elements (plain votes: `plain_half` 2.9010 ≈ `layered_half` 2.8990, RESULTS-HALF-CONTROL-2026-11-12; 10M rung: `layered_rope_scale10m` seed 0, 2.9472, runs.jsonl)
- **mechanism:** The state-economy test at the largest measured size: plain at this rung costs 11,796,480 B of mechanism state vs layered's 23,592,960 B. If the half-control's tie repeats at 10M, the levels earn nothing at any measured size.
- **train.py:** no change; existing flags only — `--arm plain --rope --dim 512 --layers-n 3`. Full-trial form is ladder format ONLY: add `--steps 56 --minutes 25 --tag scale10m`. Probe is a smoke read only (see C-A08).
- **mode:** sweep — config-only via existing flags; runs in mill/sweep_probe.py
- **prediction:** Within ±0.04 of 2.9472 at ladder format (tie expected, per the 0.0020 half-size precedent), at half the mechanism state — a per-byte win if it ties, a genuine levels-at-scale finding if it doesn't.
- **status:** queued
```mill
id: C-A09
mode: sweep
run: --arm plain --rope --dim 512 --layers-n 3
```

### C-A10 · Layered votes at the 10M ladder rung, NO rotary (rung ablation)
- **source:** combination of measured elements (the rung: `layered_rope_scale10m` seed 0, 2.9472 at 56 steps, runs.jsonl; rotary gain at half size −0.0411, RESULTS-ROPE-2026-11-11)
- **mechanism:** The 10M analogue of C-A05: prices rotary at the largest measured size, where longer effective capacity might make position handling worth more — or less — than at 0.88M.
- **train.py:** no change; existing flags only — `--arm layered --dim 512 --layers-n 3` (no `--rope`). Full-trial form: add `--steps 56 --minutes 25 --tag scale10m`. Probe is a smoke read only.
- **mode:** sweep — config-only via existing flags; runs in mill/sweep_probe.py
- **prediction:** +0.03..+0.07 vs 2.9472 at ladder format — but the comparator is n=1, so this entry's real deliverable is a paired seed-0 reading, not a mean difference.
- **status:** queued
```mill
id: C-A10
mode: sweep
run: --arm layered --dim 512 --layers-n 3
```

### C-A11 · Plain votes at the 10M ladder rung, NO rotary
- **source:** combination of measured elements (plain votes without rotary: 2.9010 half / 3.0743 full; 10M shape: dim 512×3, 9,437,184 ternary weights, runs.jsonl)
- **mechanism:** Completes plain × 10M: with C-A09 it isolates rotary for plain at 10M; with C-A10 it isolates trainer at 10M without rotary. State 11,796,480 B.
- **train.py:** no change; existing flags only — `--arm plain --dim 512 --layers-n 3`. Full-trial form: add `--steps 56 --minutes 25 --tag scale10m`. Probe is a smoke read only.
- **mode:** sweep — config-only via existing flags; runs in mill/sweep_probe.py
- **prediction:** ~2.98–3.03 at ladder format (rung 2.9472 + rotary's ~0.04 + plain≈layered ~0). Lowest information per minute in the 10M block; included for grid completeness.
- **status:** queued
```mill
id: C-A11
mode: sweep
run: --arm plain --dim 512 --layers-n 3
```

### C-A12 · STE at the 10M ladder rung, NO rotary
- **source:** combination of measured elements (STE without rotary: 2.8205 half / 2.9952 full, RESULTS-HALF-CONTROL-2026-11-12; 10M shape from runs.jsonl)
- **mechanism:** Completes the grid's last cell: with C-A08/C-A10 it finishes the {STE, layered} × {rotary, table} 2×2 at 10M. STE state 113,246,208 B.
- **train.py:** no change; existing flags only — `--arm ste --dim 512 --layers-n 3`. Full-trial form: add `--steps 56 --minutes 25 --tag scale10m`. Probe is a smoke read only.
- **mode:** sweep — config-only via existing flags; runs in mill/sweep_probe.py
- **prediction:** ~2.89–2.96 at ladder format (C-A08's expectation plus rotary's ~0.04). Ranked last: most expensive cell, read against an n=1 comparator, and its information is largely implied once C-A08 and C-A10 land.
- **status:** queued
```mill
id: C-A12
mode: sweep
run: --arm ste --dim 512 --layers-n 3
```

**Family A — rejected as ineligible or duplicate (for the merge record):**
plain_half+rotary (pooled, MILL-1901); layered full+rotary (pooled, MILL-1902);
ste_half+rotary (pooled, MILL-1903 — plausibly the highest-value rotary cross in
absolute terms, but it is the pool's, not this family's); layered_half+rotary
(already run — the champion); any cross with mag (closed as specified; calibrated
retest pooled as MILL-201..203), anneal (closed), `--carry`/`--cooldown` (closed
elements, rejected on the champion chassis), or the JEPA objective (closed); any
cross at scale50m (size element unmeasured — only a 2-step smoke exists in
runs.jsonl — and ~85 min/run); trainer×trainer simultaneities (hybrids already
pooled: MILL-220..222, MILL-401..405/1401/1402, A-028/A-032/A-035/A-036);
rotary/size crosses with untested research items (MILL-101+ own those crosses once
measured); batch crosses (batch was never varied in any measured arm — not a
measured element; champion batch grid is pooled as MILL-1201..1203 plus C-B05/06).

---

## Family B — champion mutations (one gene at a time; the completion set)

**Audit first:** most of the naïve grid around the champion is ALREADY pooled.
Dropped as duplicates (do not re-merge): V → 8/16/24/48/64/96 (MILL-502/504/505/
506/507/508; the grid also holds 4, 12, 128 and plain-side 511–515); AdamW lr 3e-3
(MILL-304; 3e-4 is MILL-305); batch 16/64 (MILL-1201/1202; 128 is MILL-1203);
dim 160/176/208/224 at 2 blocks (MILL-1113/1111/1112/1108); layers-n 1/3 at dim 192
(MILL-1109/1107); layers-n 4 (MILL-1902 — `--arm layered --rope` is bit-identical
to `layered_half --rope --layers-n 4`); heads 2/8 (MILL-903/904); wd 0.01
(CANDIDATES-A A-098). Nothing in runs.jsonl measures any Family B point (every
recorded arm is a default-recipe arm or a ladder rung).

**Mill mechanics (verified in train.py + mill/sweep_probe.py):** both parsers carry
only `--arm/--seed/--minutes/--batch/--rope/--carry/--cooldown/--dim/--layers-n/
--steps/--tag/--ckpt`. Sweep mode can set batch, dim, layers-n TODAY; every other
gene needs its flag added to BOTH parsers plus the constructor pass-through, and is
therefore `mode: process` (DEFERRED by screen.py until the flag lands). Flag names
reuse the pool's own (`--opt-lr`, `--opt-wd`, `--betas`) so Family B shares one flag
implementation with MILL-304/305 and A-098/A-099.

The 9 entries below are the one-gene points the existing grids skipped.

### C-B01 · AdamW lr -> 5e-4
- **source:** champion mutation grid (gene: opt-lr, champion value: 1e-3)
- **mechanism:** Cold-side interior point of the shared-parts lr curve (pooled: 3e-4, 3e-3; champion: 1e-3). Tests whether 1e-3 is even a local optimum for the FP parts, or whether the curve is flat/monotone through it.
- **train.py:** `--arm layered_half --rope --opt-lr 5e-4` — `--opt-lr` is NOT a CLI flag. One-line pass-through needed in both runners: `Layered(model, lr=a.opt_lr, carry=…, cooldown=…)` (constructor already accepts `lr=`; main() and sweep `run_one()` currently never pass it) + the argparse line in both parsers. Mark mode process.
- **mode:** process
- **prediction:** +0.00..+0.03 at probe scale (FP parts undertrained at short horizon; may invert at full trial). Risk: lr touches only embeddings/norms/scales — the vote path never sees it — so a flat reading bounds the FP parts' share, it does not indict votes.
- **status:** queued
```mill
id: C-B01
mode: process
run: --arm layered_half --rope --opt-lr 5e-4
```

### C-B02 · AdamW lr -> 7e-4
- **source:** champion mutation grid (gene: opt-lr, champion value: 1e-3)
- **mechanism:** Near-champion cold point: with C-B01 this resolves the curve's shape between pooled 3e-4 and the champion — a smooth slope vs a cliff just below 1e-3 read differently (cliff = champion sits on an edge).
- **train.py:** `--arm layered_half --rope --opt-lr 7e-4` — same `--opt-lr` pass-through as C-B01 (constructor arg exists, no CLI flag in either parser). Mark mode process.
- **mode:** process
- **prediction:** ~0 ± 0.02 expected; its value is curve shape, not a win. Same FP-parts-only risk as C-B01.
- **status:** queued
```mill
id: C-B02
mode: process
run: --arm layered_half --rope --opt-lr 7e-4
```

### C-B03 · AdamW lr -> 1.5e-3
- **source:** champion mutation grid (gene: opt-lr, champion value: 1e-3)
- **mechanism:** First hot-side step above the champion: tests whether the shared parts are lr-starved at 1e-3 before jumping to the pooled 3e-3 recipe-matching point (MILL-304).
- **train.py:** `--arm layered_half --rope --opt-lr 1.5e-3` — same `--opt-lr` pass-through as C-B01. Mark mode process.
- **mode:** process
- **prediction:** -0.01..+0.02. Risk: at probe horizon a hotter lr mostly buys faster early fitting of embeddings/scales; a probe win here must be re-read at full trial before it means the recipe was wrong.
- **status:** queued
```mill
id: C-B03
mode: process
run: --arm layered_half --rope --opt-lr 1.5e-3
```

### C-B04 · AdamW lr -> 2e-3
- **source:** champion mutation grid (gene: opt-lr, champion value: 1e-3)
- **mechanism:** Hot-side interior point between champion 1e-3 and pooled 3e-3 (MILL-304): together they trace whether the STE side's 3e-3 advantage (~0.2 there) transfers to the vote arms' shared parts gradually or not at all — the de-confounding question behind every votes-vs-STE comparison in the record.
- **train.py:** `--arm layered_half --rope --opt-lr 2e-3` — same `--opt-lr` pass-through as C-B01. Mark mode process.
- **mode:** process
- **prediction:** -0.02..+0.02; highest-variance lr point (AdamW instability on the log_scale params shows up here first if it exists). Same FP-parts-only risk as C-B01.
- **status:** queued
```mill
id: C-B04
mode: process
run: --arm layered_half --rope --opt-lr 2e-3
```

### C-B05 · batch -> 24
- **source:** champion mutation grid (gene: batch, champion value: 32)
- **mechanism:** Interior cold point of the batch curve (pooled: 16, 64, 128). For a vote trainer batch is a vote-statistics dial: 24 = more steps, noisier per-step gradients, more votes cast per minute. Tests whether the 32→16 direction is monotone or already turning.
- **train.py:** `--arm layered_half --rope --batch 24` — `--batch` is a real CLI flag in train.py AND in sweep_probe.py's parser; runnable in sweep mode today, no code change.
- **mode:** sweep
- **prediction:** ±0.03, direction genuinely uncertain. CONFOUND (not a pure gene effect): at fixed minutes, steps/minute rises and tokens/step falls, so this reads batch+steps+vote-noise together; a --steps-matched companion is required before any promotion.
- **status:** queued
```mill
id: C-B05
mode: sweep
run: --arm layered_half --rope --batch 24
```

### C-B06 · batch -> 48
- **source:** champion mutation grid (gene: batch, champion value: 32)
- **mechanism:** Interior hot point between champion 32 and pooled 64: fewer, cleaner votes per minute. With C-B05 it brackets the champion on the only trainer gene the sweep can move today; if both interiors are flat, the batch curve is a plateau and MILL-1201–1203's extremes are edge effects.
- **train.py:** `--arm layered_half --rope --batch 48` — `--batch` exists in both parsers; sweep-runnable today, no code change.
- **mode:** sweep
- **prediction:** ±0.03. Same confound as C-B05, mirrored: fewer steps/minute at fixed minutes; median-gate statistics also shift with batch size, so the vote stream itself changes, not just its rate.
- **status:** queued
```mill
id: C-B06
mode: sweep
run: --arm layered_half --rope --batch 48
```

### C-B07 · weight_decay -> 0.1
- **source:** champion mutation grid (gene: opt-wd, champion value: 0.0)
- **mechanism:** The strong-dose point for a dial never tried alone on this chassis (A-098 proposes only 0.01; the round-2 cooldown's wd component multiplied base_wd = 0.0 and was a no-op). At 0.1 the question becomes binary: if even this is flat, wd is a dead dial on the vote chassis; if it moves, dose matters and 0.01 is worth its probe.
- **train.py:** `--arm layered_half --rope --opt-wd 0.1` — NOT reachable today: Layered has NO wd constructor arg (AdamW `weight_decay=0.0` and `self.base_wd = 0.0` are hardcoded). Needs: constructor param `wd=0.0` wired to both `weight_decay=wd` and `self.base_wd = wd` (else a future cooldown rescales from 0), `--opt-wd` argparse line + pass-through in both runners. Mark mode process.
- **mode:** process
- **prediction:** +0.00..+0.04 (slightly worse is the prior — strong decay on embeddings at this scale). Mechanism caveat: decoupled decay also shrinks the `log_scale` params, i.e. the installed ternary step sizes — a move here is partly a scale-shrink effect, not pure regularization.
- **status:** queued
```mill
id: C-B07
mode: process
run: --arm layered_half --rope --opt-wd 0.1
```

### C-B08 · betas -> (0.9, 0.999)
- **source:** champion mutation grid (gene: betas, champion value: (0.9, 0.95))
- **mechanism:** β2 0.95 → 0.999 pushes the second-moment horizon from ~20 steps to ~1000 — longer than any run this lab makes (~160 steps full format, far fewer at probe). A-099 proposes 0.99 (~100 steps); 0.999 is the distinct regime where v̂ never equilibrates, which is the actual methodological question.
- **train.py:** `--arm layered_half --rope --betas 0.9,0.999` — NOT reachable today: betas are hardcoded `(0.9, 0.95)` in the Layered/Direct/STE AdamW calls, no constructor arg. Needs: `betas=` param on Layered, `--betas` argparse line + pass-through in both runners (flag form follows A-099). Mark mode process.
- **mode:** process
- **prediction:** ±0.04 with high seed variance expected (bias-corrected v̂ is dominated by early gradients for the whole run). Risk: a noisy probe here is uninformative in both directions — this entry earns its keep at full trial, not probe.
- **status:** queued
```mill
id: C-B08
mode: process
run: --arm layered_half --rope --betas 0.9,0.999
```

### C-B09 · betas -> (0.85, 0.95)
- **source:** champion mutation grid (gene: betas, champion value: (0.9, 0.95))
- **mechanism:** The β1 move nobody has proposed anywhere (A-099 moves only β2): momentum horizon 10 → ~6.7 steps on the shared parts. Tests whether the FP parts want fresher gradient averages when the ternary side they serve is itself re-deciding structure every step.
- **train.py:** `--arm layered_half --rope --betas 0.85,0.95` — same `--betas` plumbing as C-B08. Mark mode process.
- **mode:** process
- **prediction:** ~0 ± 0.02; the cleanest optimizer-geometry read in the family (size-, state-, and step-neutral, horizon well inside the run length, unlike C-B08).
- **status:** queued
```mill
id: C-B09
mode: process
run: --arm layered_half --rope --betas 0.85,0.95
```

**Family B — unreachable genes (what each needs; no entries, already specified elsewhere):**
votes V (constructor accepts `votes=`, neither runner passes it; needs `--votes` in
both parsers — fully specified by pooled MILL-501..509; note V ≤ 96 is sound on int8
counters, V=128 saturates at 127, hence MILL-641's int16 re-list); heads (model-level:
`Tiny` takes no `heads` arg; needs `Tiny(heads=)` threaded into `Block` + `--heads` in
both parsers — specified by MILL-903/904; head_dim 48 → 96 or 24, RoPE pairs 24 → 48
or 12, ternary count unchanged). Reachable today (sweep): batch, dim, layers-n only.

**Family B — confound summary:** batch (C-B05/06) is NOT a pure gene effect (steps/min,
tokens/step, vote noise, and median-gate statistics all move together; a
`--steps`-matched companion is required before promotion). opt-lr / opt-wd / betas
(C-B01–04, 07–09) are size-, state-, and step-neutral — the cleanest reads in the
family — but act ONLY on the shared FP parts (embeddings, norms, log_scales; under
`--rope` the carried pos table gets grad=None and is skipped), so effects are bounded
by the FP parts' share of the loss, and recipe genes read noisier at probe horizon
than at trial. C-B07 additionally entangles wd with installed step size via log_scale
decay; C-B08's β2 horizon (~1000 steps) exceeds the run itself.

---

## Family C — kernel-informed variants (ALL pending: no kernels/RESULTS-KERNELS.md yet)

The kernel stream's benches exist (`kernels/bench_matmul.py`, `bench_vote.py`,
`bench_attention.py`, ~03:50 UTC) but, re-checked at assembly time, **there is
still no `kernels/RESULTS-KERNELS.md`** — so every entry in this family is
`pending-kernel-results` and flips only via the protocol at the end of this family.

**Bench-vs-train.py discrepancies the wiring must respect (kernel specialist's audit):**
1. All three benches are forward/update-only — none tests a backward pass. train.py's
   BitLinear is an STE construction (detach-splice); the integer paths have no gradient
   at all. Wiring any matmul variant needs a custom autograd wrapper reproducing the
   STE gradients, or the vote trainers silently get no votes and the STE arm breaks.
2. The matmul bench assumes hard-quantized operands — true for the vote arms and for
   held evaluation, FALSE for STE arms during ease-in. Family C matmul entries are
   scoped to the vote chassis (the mill default) only. The bench also omits
   BitLinear's bias; wiring adds it back after the kernel.
3. The bench's two LM-head cases time a TERNARY head; train.py's head is the FP tied
   embedding. Head-case timings are excluded from every adoption decision.
4. The vote bench validates the non-carry `Layered` update only — nothing about
   `Direct` or `--carry`. Its timing subtracts medians (approximate): fused gains
   under ~10% at kernel level should be treated as noise.
5. The attention bench uses synthetic q/k/v (projections excluded — end-to-end gains
   will be smaller), rebuilds the manual variant's mask inside the timed call
   (overstates manual's cost), and never times `sdpa_math` (see "no entry" below).
   The LUT bench runs reps=3/warm=1 (vs 9/3 elsewhere) over prototype code
   (per-call [rows, groups, 81] tables, Python group loop) — a prototype's numbers,
   not a production kernel's.
6. No bench sets a pass threshold in code; the gates in the pending protocol are the
   kernel specialist's proposed adoption gates, set to Arnav's criterion (best
   balance / most precision, not raw speed).

### C-C01 · Integer matmul, direct int32 (codes @ ternary, rescale once)
- **source:** kernel stream (kernels/bench_matmul.py) — STATUS: PENDING results
- **mechanism:** Each BitLinear forward stops materialising dequantized fp32 operands. Activation int8 codes `xi` and ternary weights as int8 `wi` are multiplied as an exact int32 matmul `xi.int32 @ wi.T.int32`, then rescaled once by `(xscale * s)` — one rescale instead of an fp32 GEMM over already-quantized values. Bit-exact integer accumulation; the only error vs the bench ref is fp32 rounding in the reference itself.
- **train.py:** new flag `--matmul int32` in `BitLinear.forward`, vote arms only (see discrepancy 2), plus a custom autograd/STE wrapper reproducing the current detach-trick gradients (discrepancy 1) and the bias add-back. Must NOT be wired until `kernels/RESULTS-KERNELS.md` lands and this variant passes the protocol below.
- **mode:** process
- **prediction:** Pure kernel swap — at equal steps the held loss must be identical within rounding (trajectory-preserving). Mill probe (1.25 min, seed 0, vs job-zero baseline at the same generation) is a correctness/speed gate, not a loss hunt: **PASS if held_final ≤ baseline + 0.02 (the mill's "flat" band) AND steps ≥ 1.10× baseline steps** in the same wall time. A loss *improvement* beyond flat would come only from the extra steps, never from the math.
- **status:** pending-kernel-results
```mill
id: C-C01
mode: process
run: --arm layered_half --rope --matmul int32
```

### C-C02 · LUT matmul, TL2-like groups of 4 (lut_g4)
- **source:** kernel stream (kernels/bench_matmul.py) — STATUS: PENDING results
- **mechanism:** K is grouped in 4s; for each (row, group) a table of all 3⁴=81 ternary combinations of the 4 int8 codes is built by DP (`einsum` with the combo matrix), weights are pre-encoded as base-3 indices `widx ∈ 0..80`, and the output is a sum of `gather`s from the tables, rescaled once. Trades the multiply-accumulate for table-build + gather; also exact integer arithmetic.
- **train.py:** new flag `--matmul lut4` in `BitLinear.forward`, vote arms only, same STE-wrapper and bias requirements as C-C01, plus pre-encoding each layer's `widx` once per `install()` (weights only change on flips) rather than per forward. Must NOT be wired until the kernel results land and pass correctness — and note the bench implementation (per-call `[rows, groups, 81]` tables, Python group loop, `reps=3`) is a prototype; wiring the bench code as-is is not the proposal, a production version must at least pre-build weight indices.
- **mode:** process
- **prediction:** Same correctness gate as C-C01 (held loss unchanged at equal steps — exact integer math), but a **higher speed bar because of table memory and build cost: PASS if probe held_final ≤ baseline + 0.02 AND steps ≥ 1.20× baseline steps.** Anything less does not pay for the table footprint at 8192 training rows.
- **status:** pending-kernel-results
```mill
id: C-C02
mode: process
run: --arm layered_half --rope --matmul lut4
```

### C-C03 · On-the-fly integer matmul (quantize inside the kernel)
- **source:** kernel stream (kernels/bench_matmul.py) — STATUS: PENDING results
- **mechanism:** Starts from raw fp32 `x` each call: per-row absmax quantize to int8 codes happens *inside* the path, followed by the same exact int32 matmul and single rescale as C-C01. This is the closest drop-in for `train.py`, whose `BitLinear.forward` already re-quantizes activations on every forward — C-C01 assumes codes already exist, C-C03 pays the quantization itself, and the bench's `quantize_only` timing exists precisely to price that difference.
- **train.py:** new flag `--matmul otf` in `BitLinear.forward`, vote arms only, same STE-wrapper and bias requirements as C-C01. Must NOT be wired until the kernel results land and pass correctness.
- **mode:** process
- **prediction:** Held loss unchanged at equal steps (it performs the identical quantization `train.py` already performs, then exact integer math). **PASS if probe held_final ≤ baseline + 0.02 AND steps ≥ 1.10× baseline steps.** The honest kernel-level comparison for this variant is `onthefly_int` vs `direct_fp32 + quantize_only`, not vs `direct_fp32` alone.
- **status:** pending-kernel-results
```mill
id: C-C03
mode: process
run: --arm layered_half --rope --matmul otf
```

### C-C04 · Fused vote-counter update (step_fused)
- **source:** kernel stream (kernels/bench_vote.py) — STATUS: PENDING results
- **mechanism:** Only the elementwise vote update inside `Layered.step` changes (AdamW and backward untouched — the bench does not time them and neither does this entry). Sign computed once; counters updated in place (`add_` / `clamp_`); the flip test `(t + c.sign()).clamp(-1,1) != t` is replaced by the exactly-equivalent `(s != 0) & (t != s)`; on a flip the new value is `t + s` directly; `where` writes reuse preallocated state where the current code allocates. Same median gate, same vote, same clamp/reset, V=32, same t1-before-t2 one-flip rule.
- **train.py:** new flag `--vote-kernel fused` on `Layered` (and `Direct` only after its own equivalence check — the bench validates `Layered` semantics only; explicitly NOT `--carry`, see discrepancy 4). Must NOT be wired until the kernel results land and show exact state equivalence.
- **mode:** process
- **prediction:** This variant claims *exact* equivalence, so the probe gate is the tightest in Family C: at equal steps the training trajectory should be bit-identical. **PASS if probe held_final ≤ baseline + 0.01 AND steps ≥ 1.03× baseline steps** (the vote update is a small share of step time next to backward, so even a large kernel-level win dilutes to a few percent end-to-end — 3% is the honest adoption floor).
- **status:** pending-kernel-results
```mill
id: C-C04
mode: process
run: --arm layered_half --rope --vote-kernel fused
```

### C-C05 · Complex-multiplication rotary (rotated_cplx)
- **source:** kernel stream (kernels/bench_attention.py) — STATUS: PENDING results
- **mechanism:** `train.py`'s `rotated()` (slice pairs → `stack([a·cos − b·sin, a·sin + b·cos])` → `flatten`) is replaced by the identical interleaved-pair rotation done as one complex multiply: pairs viewed as `a+bi`, times a precomputed unit rotor `cos + i·sin`, `view_as_real` back to interleaved layout. Same rotation, same angles, applied to q and k only; SDPA itself unchanged. The bench's `rope+sdpa_cplx_s` composite is this entry's end-to-end timing.
- **train.py:** new flag `--rope-impl cplx` selecting the `rotated()` implementation inside `Block` (rotor registered as a complex buffer alongside the existing `cos`/`sin` buffers; only meaningful with `--rope`). Autograd flows through `view_as_complex`/`view_as_real`, but gradient equivalence vs the reference rotation must be sanity-checked at wiring time — the bench is forward-only. Must NOT be wired until the kernel results land and pass correctness.
- **mode:** process
- **prediction:** Held loss unchanged within fp rounding at equal steps (complex vs real arithmetic reorder rounding only; small trajectory drift over a probe is expected and acceptable inside the flat band). **PASS if probe held_final ≤ baseline + 0.02 AND steps ≥ 1.05× baseline steps** (rotary is applied twice per block per forward, but attention+MLP dominate step time).
- **status:** pending-kernel-results
```mill
id: C-C05
mode: process
run: --arm layered_half --rope --rope-impl cplx
```

### C-C06 · Manual attention (explicit QKᵀ, mask, softmax, @V)
- **source:** kernel stream (kernels/bench_attention.py) — STATUS: PENDING results
- **mechanism:** `F.scaled_dot_product_attention(is_causal=True)` in `Block.forward` is replaced by the explicit form: `att = (q @ kᵀ)·hd^-0.5`, causal mask via `triu(1)` bool `masked_fill(-inf)`, `softmax @ v`. Identical math; materialises the `[b, h, 256, 256]` logits that SDPA's backends avoid. Included for completeness as a falsification/speed gate — the prior is that it is **slower**, and the bench even overstates its cost by rebuilding the mask per timed call (a wiring would cache the mask).
- **train.py:** new flag `--attn manual` in `Block.forward`, mask cached as a buffer. Must NOT be wired until the kernel results land and pass correctness.
- **mode:** process
- **prediction:** Held loss unchanged within fp rounding at equal steps. **PASS if probe held_final ≤ baseline + 0.02 AND steps ≥ 1.05× baseline steps.** Expected outcome is FAIL on speed; if the kernel results confirm `manual_s > sdpa_s`, this entry should never flip (see protocol) and the probe should not be spent on it.
- **status:** pending-kernel-results
```mill
id: C-C06
mode: process
run: --arm layered_half --rope --attn manual
```

**No entry — stated plainly:** `sdpa_math` (SDPA MATH backend) gets NO entry — the
bench computes its error but never times it, so there is no speed number to draft
honestly on; if the kernel stream amends bench_attention.py to time it and it beats
the default backend, an entry (`--attn sdpa-math`) can be drafted then.
`direct_fp32`, `step_current`, `rotated_ref`, SDPA default are baselines, not
variants. `quantize_only` is a diagnostic timing, used in C-C03's fair comparison.
`rope+sdpa_*` timings are composites — evidence for C-C05, not separate variants.

### Pending protocol — mechanical flip conditions (pending → queued)

An entry's status may be flipped to `queued` **only when ALL of the following
hold**. Any failure, missing field, or missing case = stays
`pending-kernel-results`. Flipping authorises *wiring + probing only* — adoption
still goes through the normal mill probe/trial bars in `PROMOTE.md`.

**Gate 0 (existence & completeness).** `kernels/RESULTS-KERNELS.md` exists and
contains one result line per bench case: matmul — all 8 cases (`champ_qkv`,
`champ_up`, `champ_down`, `lad2m_qkv`, `lad2m_up`, `lad2m_down`, `champ_head_r2048`,
`lad2m_head_r2048`); vote — both cases (`champion_884736`, `ladder2m_1990656`);
attention — both cases (`champion_dim192`, `ladder2m_dim288`). Head cases must be
*present* but are **excluded from all decisions** (discrepancy 3).

**Gate 1 (correctness, hard, per variant — every non-head case must pass):**
- C-C01: `direct_int32_err ≤ 1e-3` absolute.
- C-C02: `lut_g4_err ≤ 1e-3` absolute.
- C-C03: `onthefly_int_err ≤ 1e-3` absolute.
- C-C04: `fused_max_state_err == 0.0` exactly, both cases. Any nonzero value fails — the variant's entire claim is exact equivalence.
- C-C05: `rope_cplx_err ≤ 1e-4` absolute, both cases.
- C-C06: `manual_err ≤ 1e-4` absolute, both cases. (`sdpa_math_err ≤ 1e-4` is recorded for information only; it flips nothing.)

**Gate 2 (speed, per variant — median seconds as printed by the benches):**
- C-C01: `direct_int32 ≤ 0.90 × direct_fp32` on each of `champ_qkv`, `champ_up`, `champ_down`, and `≤ 1.00 × direct_fp32` on each ladder block case.
- C-C02: `lut_g4 ≤ 0.80 × direct_fp32` on each champion block case (higher margin: table memory/build cost, and its bench timing is `reps=3` — if the margin is between 0.80× and 1.00×, it stays pending pending a re-bench at `reps=9`, it does not flip).
- C-C03: `onthefly_int ≤ 0.90 × (direct_fp32 + quantize_only)` on each champion block case.
- C-C04: `fused_net_s ≤ 0.80 × current_net_s` on **both** vote cases (net fields, clone cost already subtracted; a win on only one case does not flip — see discrepancy 4 on median-subtraction noise).
- C-C05: `rope_cplx_s ≤ 0.90 × rope_ref_s` **and** `rope+sdpa_cplx_s ≤ 0.95 × rope+sdpa_ref_s`, both attention cases.
- C-C06: `manual_s ≤ 0.90 × sdpa_s`, both attention cases. (Expected to fail; that is the designed outcome.)

**Gate 3 (scope reminder, not a bench number).** Even after flipping to `queued`,
C-C01/C-C02/C-C03 may only be wired for the vote arms with the STE-gradient wrapper
(discrepancies 1–2), and C-C04 only for non-carry `Layered`. If wiring reveals the
gradient wrapper cannot reproduce the current detach-trick gradients exactly, the
entry returns to pending regardless of kernel results.

---

## Coordinator's top 10 across families

1. **C-A01 · STE × 2M rung + rotary** — stacks the best-quality measured trainer onto
   the only fully-measured rung in the one format with no step confound; answers the
   lab's central open question (does the vote-vs-gradient gap survive scale?).
2. **C-B04 · lr 2e-3** — with pooled MILL-304 (3e-3), settles whether STE's lr
   advantage transfers to the champion's shared parts; de-confounds every
   votes-vs-STE comparison in the record.
3. **C-A02 · STE full + rotary** — transfer test for the lab's only confirmed win, at
   STE's tuned size; a flat result is as informative as a win. Cheap.
4. **C-B07 · wd 0.1** — one probe renders a verdict on an entire never-tried dial:
   flat at 0.1 kills the wd family on this chassis; movement justifies the dose curve.
5. **C-A03 · plain × 2M rung + rotary** — the per-byte tie test at scale (half the
   state); already queued in the ladder driver, so it costs the mill nothing to track.
6. **C-B06 · batch 48** — sweep-runnable today at zero code cost; with C-B05 brackets
   the champion's batch curve (plateau vs slope) and calibrates MILL-1201..1203.
7. **C-C04 · fused vote update** *(pending)* — the only kernel entry claiming exact
   equivalence; if the kernel results land clean, it speeds every vote run forever
   at zero quality risk.
8. **C-B08 · betas (0.9, 0.999)** — the only point anywhere (pool + candidates) where
   the optimizer's memory horizon exceeds the training run itself.
9. **C-A08 · STE × 10M rung + rotary** — highest ceiling in the file; capped by the
   n=1 comparator (2.9472) and ~25 min/run ladder format.
10. **C-C01 · int32 matmul** *(pending)* — the foundational kernel swap for the vote
    chassis: exact integer math, one rescale; every other matmul entry is read
    against it.

## Merge notes for the pool owner

- screen.py reads only IDEA-POOL.md — this file queues nothing until merged, by design.
- C-A03 is already queued in run_scale_ladder.py as a ride-along: merge the record,
  don't double-run it.
- Family B's flags (`--opt-lr`, `--opt-wd`, `--betas`) are the pool's own flag names —
  one implementation serves MILL-304/305, A-098/A-099, and C-B01..04/07..09.
- Family C flips mechanically via its pending protocol when
  kernels/RESULTS-KERNELS.md lands; no judgement call is needed or permitted.
- Small record notes: the scale2m mean recomputes to 3.2745 (not 3.2746 — rounding);
  pool entry MILL-904's mechanism line has an arithmetic typo (head_dim 48 → 24 at
  8 heads; it is the RoPE pair count that goes 24 → 12) — its run line is unaffected.
