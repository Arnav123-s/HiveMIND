# Weights-Reader V2 — PRE-REGISTRATION

Written 2026-11-11, before any v2 data was generated or any v2 model
trained. Arnav's directive: "make more training data, make it dream with
the harder things, make it better." Bars below are fixed; results are
reported against them as-is, losses included. Nothing here moves v1's
bars retroactively — v2 is scored against v1's *measured numbers*.

## What v1 established (the numbers v2 must beat)

- Edit verdict, internals-constructed exam (train 490 / test 175): **0.726**
- Consequence transfer, maps→coordinator adapters (n=11): **0.273** (chance ≈ 0.33)
- Absolute score, train swarm+internals-models → test coordinator: **R² −1.22**
- Dominant layer from pooled map features (train 451 / test 152): **0.204**
  (internals hand instrument reference: 0.736)
- Public LOFO regressions (item-weighted R²): layers **−0.170**,
  hidden **−1.005**, log-params **−2.115**; bvi 0.500, quant 0.931
- Controls gate: **FAILED** — family argmax unchanged on shuffled /
  random / permuted copies of one source family (SmolLM2-360M);
  pooled features are shuffle-invariant value statistics by construction.

## V2 design commitments

1. **Zoo corpus (self-generated, verified).** Small MLPs trained in numpy
   across 6 generator lineages ("families") × 4 synthetic tasks × seeds.
   Variations are construction-known (planted defect layer, edit kind,
   config); consequences are **measured** (exam accuracy before/after on
   a fixed per-task exam set). No guessed labels anywhere.
2. **Per-layer sequence representation.** Readers consume the featurizer's
   per-layer token sequence via a positional readout (resample to 16
   normalized positions per channel + per-channel argmax positions +
   sequence length), replacing v1's position-destroying pooling.
   Feature blocks: DIST = v1 pooled features (control arm);
   STRUCT = spectral/positional channels only (log-σ1, stable-rank
   channels at all positions + argmax positions + length);
   FULL = DIST + STRUCT. Paired-delta features (edited − base tokens,
   position-aligned) are first-class inputs for edit items.
3. **Dream loop (≥2 rounds).** Evaluate → harvest worst slices →
   generate concentrated harder data (subtler defects, nonlocal-effect
   defects, function-preserving permutation traps, same-statistics
   twins) → retrain → re-measure on FROZEN exams. Item types the reader
   already solves (≥0.95 held-out) are deleted from the next round's
   generation mix (s1 rule).
4. **Controls v2.** ≥3 source families (public SmolLM2-360M + ≥2 zoo
   lineages); control types: per-matrix element shuffle,
   spectrum-transplant (random orthogonal factors, original singular
   values), moment-matched Gaussian. Probability-based metric, not
   argmax.

## Pre-registered bars

- **B1 edit verdict:** on v1's exact HV1 exam (same 490/175 split),
  a v2 arm trained without the test items scores **> 0.726**.
  Arms reported individually: (a) v1 train only, v2 case-features;
  (b) v1 train + zoo case-feature data; (c) zoo only.
- **B2 consequence:** (a) zoo-trained consequence reader → coordinator
  adapter verdicts (n=11, v1 protocol): **acc > 0.27**;
  (b) score regression trained on zoo+swarm+internals-models → coordinator
  scores: **R² > −1.22**; (c) within-zoo held-out score R² reported,
  aim **> 0**.
- **B3 dominant layer:** HMAP exam (v1 split) with per-layer map
  sequences: **acc > 0.20** (reference: instrument 0.736). Zoo
  planted-layer localization reported alongside.
- **B4 cross-family regression:** public LOFO (v1 protocol, DeepSeek
  never trained on) item-weighted R² for layers / hidden / log-params
  each **less negative than v1** (−0.170 / −1.005 / −2.115). Zoo LOFO
  config regression reported alongside. Disclosure: a sequence reader
  can count its tokens; sequence length is a structural property of
  the weights and is a legitimate input — stated, not hidden.
- **B5 controls v2:** PASS iff for the STRUCT block, averaged over
  control sources, mean P(true family) on controls ≤ 0.5 × mean
  P(true family) on the originals, AND a real-vs-twin authenticity
  head trained on other sources scores ≥ 0.80 on held-out sources'
  twins. DIST and FULL blocks reported with the same metric;
  the headline verdict is the STRUCT block's, per the v2 requirement
  ("structural features must degrade").
- **B6 (secondary, no bar):** public LOFO bvi / quant with FULL
  features vs v1's 0.500 / 0.931.

## Amendments (logged before zoo data generation, 2026-11-11)

- The first task set included a parity task; a smoke test showed it is
  unlearnable by gradient descent at zoo scale (exam acc = chance for
  every family), which would have made every consequence label noise.
  Replaced with a bucketed-count task before any corpus data was kept.
- A task-generation bug (per-split redraw of the labeling function)
  was caught by the same smoke test (exam acc ≈ chance on a linearly
  separable task) and fixed: task parameters are drawn once per task.
  No v1 exam, split, or bar was touched by either fix.

## Frozen exams

HV1 split, HMAP split, coordinator items, and public LOFO folds are
v1's, untouched. Zoo exams: base-model seeds 1000–1023 (24 bases per
family-task cell are NOT used — see generator config; exam bases are a
disjoint seed range) — concretely, zoo bases with seed % 5 == 4 form
the frozen zoo exam pool and never enter reader training in any round.
Dream rounds may only generate from training-pool bases/configs.

## Ship rule

An arm ships (is recorded as the v2 reader) only if it beats its bar.
Losing arms are reported as losses with their numbers. The public
201 GB corpus on ashp is unreachable and is NOT used; public-track
numbers come from v1's already-featurized local feature files.

## Amendments (logged when made, before affected data is used)
- A1 (smoke pass, before corpus generation): the parity task was
  replaced by bucketed-count — gradient descent does not learn parity
  at zoo scale (chance accuracy in every family), so all its
  consequence labels would have been noise.
- A2 (smoke pass): the task generator initially redrew the labeling
  function per split, so exam labels disagreed with train labels. Task
  parameters are now drawn ONCE per task.
- A3 (round-0 generation, ~2 min in, before any reader was trained):
  the permute-trap is NOT function-preserving in residual models —
  branch output is added to the unpermuted skip stream, so the "trap"
  measured Δ=−0.348 on a res-relu base. Fixed: permute-trap invalid
  for residual models; generator hard-fails if any trap measures
  |Δ| > 0.01. The contaminated ~2 min of round-0 items were deleted
  and round 0 regenerated.
