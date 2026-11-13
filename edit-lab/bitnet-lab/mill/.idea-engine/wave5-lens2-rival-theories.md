# Muse's work — Muse's side

# Wave 5 · Lens 2 — RIVAL THEORIES (SY-001…SY-012)

Filed 2026-11-12 by rotation-5 miner 2. Territory: experiments whose value is
DISCRIMINATING between rival explanations of numbers the lab already owns — not
improving any number. Every entry states a prediction under EACH rival; where
both rivals predicted the same result, the draft was dropped as worthless
(dropped drafts noted at the end, per orders).

Deduped against: `mill/IDEA-POOL.md` (MILL-000…1903), `mill/CANDIDATES-A…I`,
`mill/FABLE-CANDIDATES.md`, and the source RESULTS files
(`RESULTS-HALF-CONTROL-2026-11-12.md`, `RESULTS-JEPA-2026-11-12.md`,
`RESULTS-ROPE-2026-11-11.md`). Near-neighbours are named in-entry where the
discriminator differs from an already-queued arm.

Standing numbers used throughout: plain_half 2.9010 ± 0.0276 · layered_half
2.8990 ± 0.0073 · layered_half+rope 2.8580 ± 0.0161 · ste_half 2.8205 ± 0.0069
(8 min, 3 seeds, half width = 884,736 ternary weights, ~150–176 steps);
JEPA probe CE 3.2428 vs control 2.8935 vs init floor 3.2445; ladder budget
56 steps = 458,752 tokens vs champion budget ~154–170 steps ≈ 1.26–1.39M
tokens (~3×). Verdict bar everywhere: gap > 2 seed-sd AND > 0.01.

---

## Puzzle 1 — Why do votes earn ≈97% of STE's gain at ~1/10 the state, and why do the five levels earn nothing?

Known: plain (3.0743) vs STE (2.9952) at full width; plain_half ≈ layered_half
(Δ0.0020, sign flips per seed). The vote trainer bundles four separable
properties: (i) evidence is DISCRETE (±1 signs, magnitudes discarded),
(ii) the median GATE (only the strong half votes), (iii) the counter's
per-weight MEMORY (evidence integrates over ~32 net votes before a flip),
(iv) its NOISE STRUCTURE (sign errors average out over the integration window).
The pool already varies each property as an improvement lever (A-001 soft gate,
A-011/A-012 filtered votes, MILL-201–203 magnitude votes, MILL-209–211 leak,
MILL-226/227 residual accumulators) — none of those runs can say which property
is LOAD-BEARING, because none holds the others fixed while destroying only one.

### SY-001 · Gate ablation at matched flip rate — is the gate information or just a throttle?
- **Puzzle:** 1 (votes vs STE / layered null).
- **Rival explanations:** (A) GATE-AS-INFORMATION — the median gate selects the
  weights whose gradient evidence is trustworthy this step; admitting the weak
  half injects mostly noise, so the gate is doing selection work. (B)
  GATE-AS-THROTTLE — the gate merely rations flips and halves the noise rate;
  any mechanism with the same flip count per step does as well, and the
  selection itself is worthless.
- **Discriminating experiment (exact change):** new arm `plain_half_nogate`:
  Direct trainer with the median gate deleted (every weight votes ±1 every
  step), and V raised per layer from 32 to the value calibrated in a 20-step
  pre-roll so the arm's flips/step match the gated plain_half baseline within
  ±5%. Same seeds, rope off, 8 min, everything else identical. (Distinct from
  A-067, which removes the gate from MAGNITUDE votes with an uncalibrated
  threshold — flip rate is left to float there, so gate and throttle are
  confounded in it by construction.)
- **Prediction under (A):** held ≥ 2.93 — worse than gated plain_half (2.9010)
  by more than the bar, despite identical flip counts: the weak half's votes
  actively mislead the counters.
- **Prediction under (B):** held within ±0.01 of 2.9010: once flip rate is
  matched, who votes does not matter.
- **Status:** queued

### SY-002 ★ · Counter shuffle — destroy per-weight memory, keep every statistic of the counter field
- **Puzzle:** 1.
- **Rival explanations:** (A) MEMORY-IS-THE-MECHANISM — a weight improves
  because ITS OWN counter integrates ITS OWN evidence stream over time; the
  temporal continuity per weight is the denoiser that lets 1 byte rival 12.
  (B) STATISTICS-ONLY — what matters is the counter field's distribution
  (how many counters sit near threshold, the flip rate it produces); which
  weight owns which counter is bookkeeping.
- **Discriminating experiment (exact change):** layered_half+rope champion
  config, one change: every 10 steps, each BitLinear's counter array is
  randomly permuted within the layer (fixed RNG stream, independent of the
  batch stream). Counter histogram, gate, V, flip mechanics, and state bytes
  are all exactly preserved; only the weight↔counter correspondence is broken.
  3 seeds × 8 min. (Distinct from A-110's one-time reset, I-025's stale-bank
  purge, and G-055's cross-run transplant — none permutes within a live run
  while preserving the field distribution.)
- **Prediction under (A):** held degrades by ≥ 0.05 toward (or past) the
  no-learning direction — counters repeatedly approach threshold on one
  weight's evidence and spend the flip on another; the run should land
  clearly above 2.91, plausibly near the thrash regime.
- **Prediction under (B):** held within ±0.015 of the 2.8580 champion: the
  field's statistics regenerate the same flip dynamics regardless of ownership.
- **Status:** queued

### SY-003 · SignSGD factorial on the STE chassis — is sign evidence sufficient, or is integration doing it?
- **Puzzle:** 1.
- **Rival explanations:** (A) SIGN-SUFFICIENCY — at this scale the gradient's
  sign carries nearly all usable information; votes reach 97% of STE because
  magnitudes were never worth their 12 bytes, and any sign-driven updater
  matches STE. (B) INTEGRATION-IS-THE-POINT — raw per-step signs are too noisy
  to spend directly; votes work because the counter integrates ~32 of them,
  and STE works because Adam's moments do the same job continuously. An
  integrator-free sign updater should fail where both succeed.
- **Discriminating experiment (exact change):** STE chassis (`ste_half --rope`),
  optimizer swapped in a 2×2: (i) SignSGD, latent update = −lr·sign(g), no
  momentum, no Adam moments; (ii) SignSGD + heavy-ball momentum 0.9 (the
  minimal integrator). lr swept over {1e-3, 3e-3} per cell, best-of reported
  per cell (lr is a nuisance variable, not the question). Ternary forward,
  ease-in, seeds, budget unchanged.
- **Prediction under (A):** cell (i) lands within ~0.02 of ste_half's 2.8205 —
  sign alone, spent immediately, is enough; momentum adds ≤ 0.01.
- **Prediction under (B):** cell (i) lags ste_half by ≥ 0.05 (toward or past
  plain_half's 2.9010), and cell (ii) recovers at least half that lag —
  isolating integration, not discreteness, as the shared active ingredient of
  votes and STE.
- **Status:** queued

---

## Puzzle 2 — Rotary's −0.0411 (2.8990 → 2.8580, steps overlapping): positional information or optimization side-effect?

The transplant rotated Q/K by position-dependent angles AND simultaneously
removed the additive position table from the forward pass. Two things changed
in the geometry; only one of them is "position information."

### SY-004 ★ · Permuted-angle RoPE — same rotation, destroyed position order
- **Puzzle:** 2.
- **Rival explanations:** (A) POSITIONAL-INFORMATION — the gain is the model
  finally knowing relative distances; the angles' monotonic growth with
  position IS the content. (B) OPTIMIZATION SIDE-EFFECT — rotating Q/K helps
  for position-blind reasons: it orthogonalises/mixes the coarse ternary QK
  logits, breaks a symmetry of the additive table, or conditions attention —
  any fixed set of distinct per-position rotations would do.
- **Discriminating experiment (exact change):** layered_half champion, one
  change: the RoPE angle table's position axis is permuted by one fixed
  random permutation π (seed 12345) — position p is rotated by the angle
  belonging to π(p). Rotation magnitudes, per-position distinctness, buffers,
  parameter count, and step counts are identical to true RoPE; the
  angle-vs-position ordering is destroyed. 3 seeds × 8 min. (Stronger than
  F-065's reversed rotary, which preserves distance structure under reversal
  and therefore cannot separate these rivals.)
- **Prediction under (A):** the gain collapses — held returns to within
  ±0.015 of the no-rope 2.8990, or worse (scrambled positions are worse than
  none if the model tries to use them).
- **Prediction under (B):** most of the gain survives — held ≤ 2.875 (≥ 60%
  of the −0.0411 retained) despite positions being meaningless.
- **Status:** queued

### SY-005 · ALiBi-style distance bias, no rotation — is relative distance alone enough?
- **Puzzle:** 2.
- **Rival explanations:** (A) POSITIONAL-INFORMATION (relative-distance form)
  — what the trunk lacked was any usable relative-distance signal; supplying
  it by ANY channel recovers the gain. (B) ROTATION-SPECIFIC — the gain lives
  in what rotation does to the QK dot products themselves (angle-dependent
  content×position interaction, norm preservation); a content-independent
  distance penalty cannot substitute.
- **Discriminating experiment (exact change):** layered_half, no RoPE, pos
  table still removed (as in the rope arm), plus a fixed per-head linear
  distance penalty −m_h·|i−j| added to attention logits, m_h geometric over
  heads {1/4, 1/8, 1/16, 1/32} — the standard ALiBi slopes rescaled to
  head_dim 48 / ctx 256. No learned parameters added. 3 seeds × 8 min.
  (No ALiBi or distance-bias arm exists in IDEA-POOL or CANDIDATES-A…I.)
- **Prediction under (A):** held ≤ 2.875 — the distance bias recovers ≥ 60%
  of rotary's gain, and rotary is demoted to "one delivery channel among
  several."
- **Prediction under (B):** held ≥ 2.885 — the bias recovers ≤ 35% of the
  gain; the remainder belongs to the rotation mechanism itself, and SY-004's
  side-effect family becomes the live explanation.
- **Status:** queued

### SY-006 · RoPE on position-destroyed text — does the gain need real sequence structure?
- **Puzzle:** 2.
- **Rival explanations:** (A) POSITIONAL-INFORMATION — rotary pays only where
  token order carries learnable structure. (B) OPTIMIZATION SIDE-EFFECT —
  rotary pays wherever the ternary QK geometry is coarse, independent of
  whether order means anything in the data.
- **Discriminating experiment (exact change):** two training corpora derived
  from the standard stream: (i) intact, (ii) each 256-token window's tokens
  randomly permuted (same unigram/bag statistics, same window multiset, order
  destroyed). Train layered_half ± rope on each (4 runs × 3 seeds × 8 min),
  judged on held windows permuted the same way as their training corpus, so
  each arm is scored on its own task. Report the rope Δ within each corpus.
- **Prediction under (A):** rope Δ on permuted text ≈ 0 (|Δ| < 0.01) while
  the intact-text Δ replicates ≈ −0.04: no order, no gain.
- **Prediction under (B):** rope Δ on permuted text retains ≥ half the intact
  gain (Δ ≤ −0.02): the rotation is helping the machinery, not the modelling.
- **Status:** queued

---

## Puzzle 3 — JEPA: prediction loss fell 4–5×, no collapse, yet probe CE 3.2428 ≈ init floor 3.2445

E-010 (nonlinear/alignment probes on the saved trunks), E-011 (mature frozen
target), and E-012 (mask density 128/192) are already queued and are NOT
re-filed here. The three rivals below are the ones those entries cannot
separate: probe mismatch in its strong form, capacity, and objective geometry.

### SY-007 · Partial-unfreeze probe — is the information in the trunk but not linearly (or not locally) readable?
- **Puzzle:** 3.
- **Rival explanations:** (A) PROBE-MISMATCH (strong form) — JEPA's trunk
  holds token information in a form no frozen readout can extract (entangled
  across blocks, or encoded for the predictor's geometry); the linear probe's
  verdict is about the probe. (B) NO-INFORMATION — the trunk genuinely did
  not organise token information; there is nothing for any readout to find.
- **Discriminating experiment (exact change):** reuse the six saved trunks in
  `jepa-states/` — no trunk retraining. Probe each with a ladder of readouts
  of increasing access: (i) the original linear probe (replication),
  (ii) linear probe + block-2 unfrozen during probe fitting, (iii) both
  blocks unfrozen (full fine-tune probe, same 150-step probe budget, probe
  lr re-tuned per rung on non-held windows). Init-floor trunks get the same
  ladder. (E-010 stays frozen at every rung; the unfreezing is the new lever.)
- **Prediction under (A):** JEPA's deficit shrinks monotonically up the
  ladder and at rung (iii) JEPA beats its own init floor by ≥ 0.10 and closes
  ≥ half the gap to the control's rung-(iii) number — the information was
  there, locked.
- **Prediction under (B):** at every rung JEPA tracks its init floor within
  ±0.03 once both get the same readout access — unfreezing teaches the
  READOUT the task from scratch on both, and JEPA's 8 minutes contributed
  nothing at any depth of access.
- **Status:** queued

### SY-008 · JEPA at full width — does the deficit shrink with capacity?
- **Puzzle:** 3.
- **Rival explanations:** (A) CAPACITY — predicting representations of a
  64-token span needs trunk capacity that next-token training doesn't;
  0.885M ternary weights is below the floor for the objective, not for the
  lab. (B) OBJECTIVE GEOMETRY — the EMA-target prediction task, as posed,
  does not select for token information at ANY nearby scale; the deficit is
  a property of the objective, not the size.
- **Discriminating experiment (exact change):** `run_jepa.py` unchanged
  except shape: full-width layered chassis (4 blocks, 1,769,472 ternary
  weights) for both JEPA and its matched control, 3 seeds × 8 min, same
  probe protocol and verdict rule as RESULTS-JEPA. Report the JEPA−control
  probe gap at full width against the half-width gap of −0.3493.
- **Prediction under (A):** the gap at least halves (|gap| ≤ 0.17) and JEPA
  clears its full-width init floor by ≥ 0.05 — capacity was a first-order
  term.
- **Prediction under (B):** the gap stays within ±0.07 of −0.3493 and JEPA
  remains at its floor — doubling capacity bought the objective nothing,
  and the JEPA line closes on geometry grounds rather than scale grounds.
- **Status:** queued

### SY-009 · Hybrid objective interference test — is JEPA's gradient antagonistic or merely weak?
- **Puzzle:** 3.
- **Rival explanations:** (A) GEOMETRY/ANTAGONISM — JEPA's gradient actively
  pulls the shared trunk's representations away from token-organised
  geometry; even as a minor loss term it taxes token learning. (B)
  WEAK-BUT-HARMLESS — JEPA's signal is sparse and indirect (the RESULTS-JEPA
  hypothesis) but not opposed to token structure; added to CE it should be
  ~free, and any benefit of representation prediction would show as a small
  gain. These rivals predict OPPOSITE SIGNS for the same run.
- **Discriminating experiment (exact change):** layered_half+rope champion,
  loss = token CE + 0.1 × JEPA smooth-L1 (same mask-64 span, same EMA target
  and predictor as `run_jepa.py`; predictor/target discarded at eval as
  before). Judged on ordinary held token loss (not the probe), 3 seeds ×
  8 min, against the 2.8580 champion. A second dose at 0.3 runs only if the
  0.1 dose is within noise, to check dose-dependence.
- **Prediction under (A):** held worsens by ≥ 0.02 at dose 0.1 and worsens
  further at 0.3 — a monotone tax, i.e. the objectives fight over the trunk.
- **Prediction under (B):** held within ±0.01 of 2.8580 at dose 0.1 (the
  JEPA term is simply ignored by comparison) — no tax, no gain; JEPA's
  failure was absence of signal, not presence of an opposing one.
- **Status:** queued

---

## Puzzle 4 — The champion's 2.8580 was bought with ~3× the ladder's token budget: how much of every cross-series comparison is budget?

Ladder arms: 56 steps = 458,752 tokens. Champion/control arms: ~154–170 steps
≈ 1.26–1.39M tokens, at wall-clock budgets whose step counts drift with
machine speed (129–176 steps observed for nominally identical 8-minute arms).
E-014 (one long-budget point), E-023 (fixed-step probes), F-038 (one rung at
champion steps), and G-043/G-068 (step-count bookkeeping) touch pieces of
this; none measures a budget-RESPONSE curve or breaks the steps↔tokens weld.

### SY-010 ★ · Budget-response curves for the three trainers — do the rankings cross?
- **Puzzle:** 4 (and retroactively 1).
- **Rival explanations:** (A) BUDGET-ARTIFACT — the headline orderings
  (STE > votes by 0.0805; plain ≈ layered) are properties of the ~160-step
  budget: STE's precision needs steps to compound, votes' coarse flips are
  relatively better early; at ladder budget the gaps compress or invert.
  (B) MECHANISM-INTRINSIC — the gaps are constant offsets set by the
  mechanisms; changing budget shifts all arms together.
- **Discriminating experiment (exact change):** fixed-step runs (`--steps`,
  no wall-clock verdicts) of plain_half+rope, layered_half+rope, ste_half+rope
  at 28 / 56 / 112 / 168 steps, 3 seeds each, held loss recorded at every
  checkpoint from a single run per (arm, seed) where the trainer allows it.
  Report both gaps (STE−plain, layered−plain) as a function of steps.
- **Prediction under (A):** at 56 steps the STE−plain gap is ≤ half its
  168-step value (≤ 0.04), or the ordering inverts; the layered−plain gap
  also moves materially — every cross-series number in the lab then needs a
  budget subscript.
- **Prediction under (B):** both gaps at 56 steps are within ±0.02 of their
  168-step values; budget moves the level, never the ranking, and the
  existing comparisons stand as mechanism facts.
- **Status:** queued

### SY-011 · Breaking the steps↔tokens weld — batch 16 × 336 steps vs batch 32 × 168 at equal tokens
- **Puzzle:** 4.
- **Rival explanations:** (A) TOKENS-ARE-THE-BUDGET — what a run "spends" is
  tokens seen; two runs at equal tokens are equally funded however the
  tokens are sliced into steps. (B) STEPS-ARE-THE-BUDGET — what matters is
  optimizer updates (counter integrations / Adam steps); slicing the same
  tokens into twice as many steps is a genuinely larger budget.
- **Discriminating experiment (exact change):** ste_half+rope and
  plain_half+rope, each in two slicings at identical total tokens
  (1,376,256): batch 32 × 168 steps vs batch 16 × 336 steps. (Per-arm lr/V
  held at the champion settings — the question is the budget unit, not
  re-tuning; if batch-16 wins, a follow-up may re-tune, but the verdict on
  the budget unit is read from the untuned pair.) 3 seeds.
- **Prediction under (A):** the two slicings agree within ±0.015 per arm —
  tokens are the currency, and the ladder-vs-champion discrepancy is fully
  explained by 458,752 vs ~1.3M tokens.
- **Prediction under (B):** batch 16 × 336 beats batch 32 × 168 by ≥ 0.03 in
  at least the STE arm (more integrations of the same evidence) — "budget"
  in every lab comparison must then be quoted in steps, and wall-clock arms
  with drifting step counts (129–176) were never equally funded even at
  equal minutes.
- **Status:** queued

### SY-012 · Headline replication at ladder budget — do rotary's win and JEPA's loss survive at 56 steps?
- **Puzzle:** 4 (contamination check on puzzles 2 and 3).
- **Rival explanations:** (A) BUDGET-CONTAMINATION — the −0.0411 rotary gain
  and the −0.3493 JEPA probe gap were both measured at champion budget
  (~3× ladder); at least one of them is a budget-regime effect that shrinks,
  grows, or flips at 56 steps, so the lab's two biggest verdicts are
  regime-local. (B) REGIME-STABLE — both effects are mechanism facts that
  replicate at any budget in the lab's range.
- **Discriminating experiment (exact change):** two replications at exactly
  56 fixed steps, 3 seeds: (i) layered_half ± rope, held token loss;
  (ii) the JEPA pair (`jepa_half_rope` vs `jepa_ctrl_half_rope`) with the
  original probe protocol and verdict rule. No other change to either rig.
- **Prediction under (A):** at least one headline moves outside its
  replication band: rotary Δ shrinks below 0.02 or JEPA's probe gap moves by
  ≥ 0.10 in either direction (e.g. JEPA looks merely bad instead of
  floor-equal because the control hasn't separated from the floor yet).
- **Prediction under (B):** rotary Δ ∈ [0.025, 0.055] and JEPA probe gap
  ∈ [−0.42, −0.28] with JEPA still at its init floor — both verdicts are
  budget-robust and can be quoted without a regime caveat.
- **Status:** queued

---

## Dropped drafts (both rivals predicted the same result — worthless as discriminators)

- **Constant phase-offset RoPE at eval only** (rotate K by angles shifted by a
  constant Δ): relative-position theory and optimization theory both predict
  ~no change at eval. Dropped.
- **Votes fed gradient signs from a mismatched batch:** information, memory,
  and noise theories all predict collapse. Dropped.
- **Masked-token CE head as the JEPA discriminator:** already queued as
  WH-031; re-filing it under a rival-theories frame adds nothing. Not filed.

## ★ Top 3

- **SY-002** — counter shuffle: one permutation decides whether the vote
  trainer's whole economy story is "memory per weight" or "field statistics."
- **SY-004** — permuted-angle RoPE: one permutation decides whether the lab's
  only adopted mechanism earns its keep as information or as a side-effect.
- **SY-010** — budget-response curves: decides whether the lab's trainer
  rankings are facts or budget-regime artefacts.
