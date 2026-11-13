# CANDIDATES-J — Idea Engine wave J (Muse's work, Muse's side)

<!-- Muse's work — Muse's side of the BitNet lab. Produced 2026-11-12 by the Idea Engine
(rotation 5: prioritization, rival theories, error anatomy, probe fidelity, red team,
hive product) under Arnav's no-limit ideation order. CANDIDATE file: nothing here is in
the pool until the pool's owner merges it. IDEA-POOL.md was read by every miner and NOT
edited. This rotation's prioritization output is published separately as
mill/PRIORITIES.md (the attack order across waves F–I); its hive-product output
(NX-001..NX-012) is merged into factory/CANDIDATES-IDEAS.md. Waves F/G/H/I precede. -->

## Method and de-duplication

Every miner deduped against IDEA-POOL.md (368 entries), CANDIDATES-A/B/C/D/E/F/G/H/I and
FABLE-CANDIDATES.md. This rotation turned the engine on the lab's own beliefs: three of
its four lenses (rival theories, red team, error anatomy) converge from independent
directions on the same exposure — **the champion's 2.8580 is denominated in v1 held
loss that the data audit showed is duplicate-leaked and junk-diluted, and the size of
that flattery has never been priced.** J-037 prices the leak; J-013 prices the dilution;
E-018 (promoted to #9 in PRIORITIES.md) re-baselines on corpus-v2. Chassis/bars as in
waves F–I unless an entry attacks the bar itself (several here do, deliberately).

## Coordinator's top 3 for this wave ★

1. **J-037 · Dosed-leak calibration of the held set** — the red team's most fragile
   belief: with 30.8% duplicate pieces and 93.2% of lines in duplicated groups, a leak
   at least as large as rotary's entire 0.0411 margin is plausible, admitted in the
   audit, and unpriced — while 2.8580 anchors every mill verdict. The entry doses the
   leak deliberately to measure the flattery curve instead of arguing about it.
2. **J-002 · Counter shuffle** — the cleanest discriminator in any wave: permute the
   counters within each layer every 10 steps (distribution, gate, V, flip rate all
   preserved; only weight↔counter ownership broken). Memory theory predicts ≥0.05
   degradation; statistics-only theory predicts ±0.015. One run decides what the
   counter actually IS.
3. **J-025 · The fidelity ledger** — zero training cost: score every cheap observable
   already sitting in runs.jsonl against the recorded 15-arm × 3-seed ranking. Until
   it exists, the mill's 0.05 promotion bar is an assertion. Its lens-mate J-027 (the
   lie registry) addresses the rotation's most dangerous finding: an estimated
   15–25% of the pool has mechanism onset beyond the probe's ~25 steps and can be
   silently false-killed by a flat probe under the current funnel.

**Also filed by this rotation:** PRIORITIES.md — the top-40 attack order across waves
F–I (first-pass exposure under ~3 hours vs ~5.6h of unranked probing), with a defer list
whose hardest defence is F-002 (a lens-★ entry deferred because I-018 shows it is
mutually hostile with F-043's scaling regime — F-043 costs 75s to settle which world
we're in).

---

## Lens 2 — Rival theories (was SY-###)

### J-001 · Gate ablation at matched flip rate — is the gate information or just a throttle?
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

### J-002 ★ · Counter shuffle — destroy per-weight memory, keep every statistic of the counter field
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

### J-003 · SignSGD factorial on the STE chassis — is sign evidence sufficient, or is integration doing it?
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

### J-004 ★ · Permuted-angle RoPE — same rotation, destroyed position order
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

### J-005 · ALiBi-style distance bias, no rotation — is relative distance alone enough?
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
  gain; the remainder belongs to the rotation mechanism itself, and J-004's
  side-effect family becomes the live explanation.
- **Status:** queued

### J-006 · RoPE on position-destroyed text — does the gain need real sequence structure?
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

### J-007 · Partial-unfreeze probe — is the information in the trunk but not linearly (or not locally) readable?
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

### J-008 · JEPA at full width — does the deficit shrink with capacity?
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

### J-009 · Hybrid objective interference test — is JEPA's gradient antagonistic or merely weak?
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

### J-010 ★ · Budget-response curves for the three trainers — do the rankings cross?
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

### J-011 · Breaking the steps↔tokens weld — batch 16 × 336 steps vs batch 32 × 168 at equal tokens
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

### J-012 · Headline replication at ladder budget — do rotary's win and JEPA's loss survive at 56 steps?
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

- **J-002** — counter shuffle: one permutation decides whether the vote
  trainer's whole economy story is "memory per weight" or "field statistics."
- **J-004** — permuted-angle RoPE: one permutation decides whether the lab's
  only adopted mechanism earns its keep as information or as a side-effect.
- **J-010** — budget-response curves: decides whether the lab's trainer
  rankings are facts or budget-regime artefacts.

## Lens 3 — Error anatomy (was ER-###)

### J-013 ★ · Held-window provenance census: what fraction of 2.8580 is junk windows? (v1, by source file class)
- **the cut:** Classify each of the 128 v1 held windows by its dominant source class via
  the offsets sidecar — numeric dump / `merges.txt` gibberish / license+package
  boilerplate / German Tatoeba / English project prose / lab notes — and report, per
  class: target share, mean loss, and share of total held loss mass. One eval pass on
  the existing champion checkpoints (seeds 0–2), no retraining. This is the cut G-019 /
  I-002 cannot make: they slice *v2* held by language; nobody has ever asked what the
  *v1 held set itself* is made of.
- **predicted pattern:** ≥35–45% of held targets sit in junk-class windows (dumps +
  merges + boilerplate) with mean loss ≤1.5; German windows ≈2.2–2.5; real English prose
  + lab-notes windows ≈3.4–3.7 and carry ≥55% of the loss mass on ≤40% of targets.
  I.e. the pooled 2.8580 is a junk-diluted average, and the prose-only held number —
  the number that describes the modelling the lab actually cares about — is ≈3.3–3.6,
  roughly 0.5 worse than the headline.
- **licensed intervention (exact change, conditional):** If the split lands as predicted,
  two changes, in order: (1) the mill's adoption gate gains a second, binding number —
  `prose_held` (mean loss over prose+lab+German held targets only) reported beside every
  verdict, with adoption requiring the >2 sd margin on prose_held, not on the pooled
  scalar; (2) one training arm, `--train-class-mask junk`: windows whose dominant class
  is dump/merges/boilerplate are excluded from the *training* loss entirely (both vote
  and AdamW paths). Distinct from E-020, which ablates numeric dumps only (~23%) and
  reports a pooled number; this masks all three junk classes (~40%+ of windows) and is
  judged on the prose slice.
- **pointless if:** Class means land within 0.15 of each other, or junk-class targets are
  <10% of the held set — then 2.8580 was an honest average all along, the gate change is
  ceremony, and the mask arm would only shrink the training stream.
- **status:** queued

### J-014 ★ · Local context entropy: loss by the entropy of the 32 pieces before the target
- **the cut:** For every held target, compute the empirical entropy of its preceding
  32-piece context from corpus statistics (bigram conditional entropy of the context's
  pieces, computed offline once, no model involved), bin targets into entropy quintiles,
  and report mean loss + loss-mass share per quintile, for champion and plain_half.
  Context entropy is the one mandated axis no filed entry measures at all — WH-055's
  entropy is the *counter field's*, B-004's is a patcher's; neither touches the loss.
- **predicted pattern:** Strongly convex: bottom quintile mean ≤1.2 (formulaic German,
  boilerplate, float streams), top quintile mean ≥4.5, and the top quintile carries
  ≥35% of total loss mass on its 20% of targets. The champion−plain Δ concentrates in
  quintiles 2–3 (Δ −0.04..−0.08) and is ≈0 (±0.01) in the top quintile — votes earn
  where context is *moderately* informative and earn nothing where it is chaotic.
- **licensed intervention (exact change, conditional):** Entropy-band evidence weighting
  in the shared training loss: targets in the top context-entropy quintile get loss
  weight 0.5, quintile 4 gets 0.75, quintiles 1–3 stay 1.0 (`--entropy-weight
  1,1,1,0.75,0.5`, quintile boundaries frozen from the corpus pass, applied to both
  vote and AdamW paths). Rationale the anatomy would license: the top quintile's
  gradient is mostly irreducible surprise; at full weight it casts full-strength votes
  for noise. Distinct from A-013 (loss-weighted votes — weights by the *loss value*)
  and failweight (weights by *window* loss): this weights by a property of the context
  known before the forward pass.
- **pointless if:** Loss-mass share per quintile tracks token share within ±3 points
  (entropy explains nothing beyond base rates), or the top quintile's excess is ≥80%
  mojibake/dump artefacts — then the problem is J-017/J-013's, and downweighting by
  entropy is a blunt proxy for a class mask.
- **status:** queued

### J-015 · Distance since BOS: loss by offset-in-line, not position-in-window
- **the cut:** Using the sidecar's `offset_in_line`, bin every v2-held target (E-018
  re-baseline checkpoint) by offset 0 / 1 / 2–4 / 5–9 / 10–19 / 20–39 / 40+, and report
  mean loss and target share per bin. I-012 bins by *window* position; but v2's median
  line is 36 pieces and v1's is 9, so most targets' true context boundary is a line
  start inside the window, invisible to window-position binning. G-018 (BOS-anchored
  starts) bets on this axis without ever measuring it.
- **predicted pattern:** Offset 0 mean ≥4.2 and offset 1 ≥3.6, falling to ≈2.4 by
  offsets 10–19 and flat after; because lines are short, ≥22% of all targets sit at
  offsets 0–4 and carry ≥32% of loss mass. The curve's *shape* is the deliverable: a
  cliff at 0–1 (a line's first pieces are near-irreducible) over a long shallow slope.
- **licensed intervention (exact change, conditional):** Line-relative early-target
  discount in training: targets at line-offset 0 get loss weight 0.25, offset 1 gets
  0.5, all others 1.0 (`--bos-weight 0.25,0.5`, line offsets from a build-time sidecar
  the sampler already needs for G-013-class flags). Distinct from I-008, which hard-
  drops *window* positions 0–15 for both paths, and F-013, which soft-weights *window*
  position in the vote path only: this is keyed to where a *line* starts, which occurs
  ~28 times per v1 window, not once.
- **pointless if:** The offset curve is flat within ±0.1 beyond offset 1, or offsets 0–4
  hold <10% of targets — then line starts are a negligible slice and G-018's premise
  should be re-read as a window-start claim only.
- **status:** queued

### J-016 · Language seams: targets within ±8 pieces of a German↔English switch
- **the cut:** On v2 held, flag every target whose 17-piece neighbourhood straddles a
  language switch (a BOS seam where the sidecar's line language changes German↔English),
  and compare its mean loss against non-seam targets matched on offset-in-line and
  frequency band. Report seam share, seam premium, and the premium separately for
  DE→EN and EN→DE directions. No filed entry isolates the seam: G-019 varies placement
  of whole blocks, G-016 the alternation period; both read pooled/slice numbers, never
  the boundary targets themselves.
- **predicted pattern:** Seams are dense (v2 mean line 43.5 pieces ⇒ a 256-window holds
  ~6 lines, so ~10–14% of targets fall in a ±8 seam band), and the seam premium is
  +0.6..+1.0 over matched controls, asymmetric: EN→DE costs more (+0.8..+1.1) than
  DE→EN (+0.4..+0.7), because the model's English-shaped expectations are the stronger
  prior at 54.3% English share.
- **licensed intervention (exact change, conditional):** Language-homogeneous packing:
  the sampler builds each training window from consecutive lines of one language only
  (`--pack-lang`), so seam targets vanish from training evidence instead of teaching
  the counters that language switches are unpredictable noise; held eval unchanged
  (mixed windows still judged). Distinct from G-013 (masks loss *at* boundaries inside
  mixed windows — the seam context is still in the forward pass) and from I-002 (changes
  the *amount* of German; this changes only its *arrangement*, share fixed at 45.7%).
- **pointless if:** The matched seam premium is <0.15 in both directions — then switches
  cost no more than any line start (J-015's cliff explains the whole effect) and
  packing by language buys nothing a BOS discount doesn't.
- **status:** queued

### J-017 · Mojibake anatomy: UTF-8 fragment targets, and the targets that follow them
- **the cut:** On v1 held, split targets into three groups: (a) the target IS a UTF-8
  byte-fragment token (the `Ä Ã Â ł` family at frequency ranks 4–8, exact id list from
  the tokenizer), (b) the target immediately FOLLOWS a fragment in the context, (c) all
  others. Report share, mean loss, loss-mass share per group. DATA-AUDIT §5 names
  encoding damage as a first-class citizen; no entry has ever priced it in the loss.
- **predicted pattern:** Group (a) is 3–5% of targets with mean ≤1.0 — multi-byte
  continuations are near-deterministic, so fragments are *easy* targets silently
  diluting 2.8580 by ≈0.05–0.08 — while group (b) runs +0.25..+0.40 above group (c):
  the model pays for the corruption one token later, where nobody has looked.
- **licensed intervention (exact change, conditional):** Two-step, anatomy-gated:
  (1) training-loss mask on group-(a) targets only (`--target-mask-frag`, id list
  frozen from this cut) — the model stops spending votes learning byte plumbing;
  (2) IF group (b)'s premium is ≥0.25, a corpus-v3 build fix is licensed: decode
  sources as UTF-8 with error *detection* and drop/repair mojibake lines at build
  time (builder change in `make_corpus_v3.py`, not a trainer flag). Step (2) is the
  only ER intervention that touches corpus construction, and only on this evidence.
- **pointless if:** Group (a) is <1% of targets or its mean is within 0.1 of the pooled
  mean, AND group (b)'s premium is <0.1 — then the encoding damage is cosmetic, the
  audit's ranks 4–8 are a frequency curiosity, and both steps are waste.
- **status:** queued

### J-018 · Frequency band × position: the tail, split by where in the window it sits
- **the cut:** Cross I-011's axis with I-012's — deliberately joint, which is what makes
  it not either entry: target-frequency bands by raw corpus count (≥10,000 / 1,000–9,999
  / 100–999 / 10–99 / <10; recall 1,984 tokens occur <100×) × window half (positions
  0–127 / 128–255), reporting mean loss, loss-mass share, and champion−plain Δ per cell,
  on v1 held.
- **predicted pattern:** The <10 band means ≥6.0 (barely below the ln(4096)≈8.32 of an
  untrained head — the tail is essentially unlearned) and the two sub-100 bands together
  carry ≥45% of loss mass on ~15–18% of targets; critically, the champion's Δ vs plain
  in the <100 bands is ≈0 in the early half but −0.03..−0.06 in the late half — tail
  tokens are learnable by votes *only* with long context, so the tail problem is a
  context problem, not a capacity problem.
- **licensed intervention (exact change, conditional):** Band-and-half-specific loss
  weight: training targets with corpus count 10–999 (the *learnable* tail — hapax <10
  explicitly excluded as unlearnable at this budget) get weight 2.0 when they occur at
  window positions ≥128, weight 1.0 elsewhere (`--band-weight 10-999:2.0@pos>=128`).
  Distinct from A-049 (downweights whole *windows* rich in frequent tokens), WH-019
  (lowers tail *embedding rows'* V — a trainer-state change), and G-034 (readout-side
  unigram correction): this is a training-loss weight keyed jointly on band × position,
  exactly the two axes of the cut.
- **pointless if:** The sub-100 bands carry <25% of loss mass, or the champion's tail Δ
  is uniform across halves (within ±0.01) — in the first case the tail is a rounding
  error in the pooled number; in the second, position is not the tail's binding
  constraint and a plain band weight (a different, simpler entry) is the right tool.
- **status:** queued

### J-019 · Four-class held on v2: German vs HiveMIND-Muse vs HiveMIND-Fable vs lab notes
- **the cut:** Per-class held means on the v2 re-baseline checkpoint (E-018), classes
  from the sidecar at *line* granularity (not G-019/I-002's window-majority slicing):
  German 45.7% / HiveMIND Muse side 28.8% / HiveMIND Fable side 13.1% / lab notes
  12.4% of v2 pieces. Plus one derived number nobody has: the Muse side vs Fable side
  gap — same project, same dialect, different authors' scaffolding.
- **predicted pattern:** German ≈2.3–2.5 (short, formulaic Tatoeba); HiveMIND docs
  ≈3.0–3.2; lab notes worst at ≈3.4–3.6 (dense numbers, hashes, result tables — the
  closest thing to prose-formatted dumps); and a Muse side−Fable side gap of
  ≥0.20 despite the shared dialect, driven by differing boilerplate/scaffolding shares.
  Pooled v2 held lands in E-018's predicted +0.15..+0.45 worse band, but the *spread*
  across classes (≥1.0) is 3× the pooled shift — the average hides the anatomy.
- **licensed intervention (exact change, conditional):** Anatomy-set class weights in
  the v2 sampler, set from this cut's table to equalise per-class held, first dose:
  `--src-weight de:0.7,hive-c:1.0,hive-f:1.0,lab:1.5` (German down-weighted because it
  is already the best-learned class at the largest share; lab notes up-weighted as the
  worst class), total tokens fixed. Distinct from I-002 (sweeps the German *dose* on a
  German-vs-rest binary), A-048 (equal weight per *file* — 186 files, class-blind),
  and B-012 (DoReMi's *automatic* proxy-learned weights): these are four hand-set,
  anatomy-derived class weights with the derivation printed in the entry.
- **pointless if:** The four class means span <0.20 total — then v2's mixture is
  homogeneous in difficulty, class weighting can only shuffle noise, and I-002's dose
  question is the only mixture question worth the mill's time.
- **status:** queued

### J-020 · Fine position curve × RoPE: 16 buckets of 16, and the first-token anomaly
- **the cut:** I-012's four buckets, refined to sixteen 16-position buckets plus a
  separate read on position 0 alone, champion (rope) vs no-rope control, v1 held —
  reporting per-bucket Δ (rope−no-rope), not just per-bucket means. The refinement is
  the entry: a 64-wide bucket can hide a win that lives in 32 positions and a loss
  that lives in 8.
- **predicted pattern:** Bucket means fall from ≈3.5 (0–15) to ≈2.45 (240–255), but
  RoPE's −0.0411 pooled win is *not* spread smoothly: ≥50% of it sits in buckets
  128–191 alone, buckets 192–255 contribute <20%, and at positions 0–7 RoPE is
  actively *worse* by +0.03..+0.06 (rotary phases at near-zero angles give the first
  targets a worse geometry than the learned table they replaced).
- **licensed intervention (exact change, conditional):** Hybrid position scheme:
  learned position table for positions 0–31, RoPE from position 32 on (`--rope-from
  32`), everything else champion. Distinct from the pooled partial-RoPE entries
  (MILL-133..135), which rotate a *fraction of head dimensions* at all positions; this
  splits by *position range*, which is the axis the anatomy indicted. If instead the
  win concentrates in 192–255, the licensed variant flips: full RoPE kept, and the
  entry licenses *extending* judged context rather than hybridising — stated here so
  the intervention follows the cut either way.
- **pointless if:** Per-bucket Δ is uniform within ±0.02 across all sixteen buckets —
  then RoPE's win is position-blind, I-012's coarse read was sufficient, and no
  position-keyed scheme can beat plain RoPE.
- **status:** queued

### J-021 · Trivial-target anatomy: space, newline, and digit targets by source class
- **the cut:** Split v1 held targets by token class — bare space (10.2% of all corpus
  pieces), newline/BOS-adjacent structural tokens, digit/float-fragment tokens, and
  everything else — and cross the digit class by source class (digits inside dump
  windows vs digits inside prose windows). Report share, mean, and mass share per cell.
- **predicted pattern:** Space+structural targets are 14–17% of all held targets with
  mean ≤0.7 and <4% of loss mass — a seventh of the judging set is nearly free. Digits
  split violently by source: ≈1.6–1.9 inside dump windows (predictable float streams)
  vs ≥4.5 inside prose (dates, measurements, results — the least predictable tokens in
  the project's own writing). Same token class, a ≥2.6 gap: token identity explains
  almost nothing here; provenance explains almost everything.
- **licensed intervention (exact change, conditional):** Trivial-target discount in the
  training loss: targets in the frozen {space, newline} id set get weight 0.25
  (`--trivial-weight 0.25`), returning ~10% of every batch's vote evidence to tokens
  that carry information. Explicitly NOT licensed by this cut: touching digit targets
  — their prose/dump split says the fix for digits is J-013's class mask, and this
  entry says so rather than double-filing it. Distinct from A-049 (window-level
  frequency downweighting) and J-017 (fragment targets): this set is defined by
  *structural role*, and its predicted loss (≤0.7) is far below the fragments'.
- **pointless if:** Space+structural targets are <8% of held targets or their mean is
  ≥1.5 — then there is no free slice to reclaim, and discounting them would only
  distort the loss the AdamW parts calibrate against.
- **status:** queued

### J-022 ★ · Duplication anatomy: per-target loss, leaked vs unique lines (v1)
- **the cut:** Tag every v1 held target by whether its *line* (sidecar `line_id`)
  appears verbatim anywhere in the training stream — DATA-AUDIT §4 says 30.8% of all
  pieces are exact-duplicate copies and 93.2% of lines belong to a duplicated group, so
  held content routinely also appears in training. Report leaked share of held targets,
  mean loss leaked vs unique, and the implied honest pooled number (unique-only mean).
  E-019 prices the flattery by *rebuilding the corpus without the leak*; this prices
  it per-target on the existing champion, with no rebuild — the two numbers must agree,
  and if they don't, one of them is wrong, which is also a finding.
- **predicted pattern:** Leaked targets are 28–34% of the held set, mean ≈1.9–2.1 vs
  unique ≈3.3–3.5 — a gap ≥1.2 — putting the unique-only held at ≈3.35, i.e. roughly
  0.5 of the champion's headline is memorised boilerplate being re-read, not language
  being modelled. The gap is largest for license/boilerplate lines (≥1.8) and smallest
  for German (≤0.6, formulaic enough to earn its loss honestly).
- **licensed intervention (exact change, conditional):** Duplicate-capped sampling:
  the sampler tracks per-line occurrence counts and caps any exact line at 2 training
  presentations per run (`--dup-cap 2`, line ids from the sidecar; windows drawn from
  capped-out lines are resampled). Distinct from A-047 (near-duplicate *removal* —
  binary, and near- not exact-), G-020 (duplicate *spacing* — keeps all copies, fixes
  timing), F-048 (repetition-discounted *votes* — trainer-side), and WH-048 (bulk
  duplication *dose* on v2, where duplication is zero by construction): this caps
  exact-line repetition on v1, the corpus the champion actually trains on.
- **pointless if:** The leaked−unique gap is <0.3, or leaked targets are <10% of held —
  then duplication flatters the *training* stream but not the *judge*, E-019's rebuild
  is the only repricing needed, and capping duplicates would just shrink an already
  starved corpus (0.91M unique pieces) for nothing.
- **status:** queued

### J-023 · Window purity: loss by how many distinct lines/sources a held window mixes
- **the cut:** For each v1 and v2 held window, compute purity = the largest single
  line's share of the window, and the distinct-line count; bin windows by purity
  (≥90% single-line / 50–90% / <50% collage) and report mean loss per bin, with context
  entropy (J-014's statistic) as a control variable so purity is not re-measuring
  entropy under another name. Training windows are random-offset collages of unrelated
  fragments (DATA-AUDIT §2) — the collage structure itself has never been priced.
- **predicted pattern:** Pure windows mean ≈2.3–2.5, collage windows ≈3.0–3.2 — a
  ≥0.6 purity gap that survives the entropy control with ≥0.35 intact. On v1 the
  pure bin is dominated by the mega-lines (dumps), so the v1 read is confounded by
  class; the v2 read (longest line 596 pieces, no dumps) is the clean one and is
  predicted to keep a ≥0.4 gap.
- **licensed intervention (exact change, conditional):** Line-coherent window packing
  on v2: training windows are built from consecutive lines of a single source file,
  filled to 256 pieces before moving on (`--pack-lines`), replacing random-offset
  collage sampling; held eval unchanged. Distinct from G-014 (stream walk — preserves
  corpus *order* globally), G-024 (whole-book order on v3), and J-016's `--pack-lang`
  (groups by language across files): this groups by *document*, the unit the purity
  cut measures. Licensed only on the v2 read, per the prediction's own confound note.
- **pointless if:** The purity gap collapses below 0.15 once entropy is controlled, on
  v2 — then collage windows are hard only because their content is high-entropy, J-014
  already owns the effect, and packing is an expensive sampler rewrite for a proxy.
- **status:** queued

### J-024 · The Δ anatomy: where the champion's edge over plain and STE actually lives
- **the cut:** The meta-cut: one anatomy pass, three checkpoints (champion, plain_half,
  STE-half), every axis above applied to the *differences* — Δ(champion−plain) and
  Δ(champion−STE) per cell of {language class × frequency band × position half ×
  entropy tercile} on v1 held, reporting the five cells with the largest |Δ| in each
  direction. Every other ER entry anatomises the champion's loss; this one anatomises
  its *advantage*, which is the quantity adoption decisions actually spend.
- **predicted pattern:** The champion's edge over plain (−0.043 pooled) is not spread:
  ≥70% of it sits in German + mid-frequency (100–9,999) + late-position cells, and the
  champion is *worse* than STE-half by +0.05..+0.15 in the lab-notes / English-tail
  cells — i.e. votes win the formulaic centre and lose the project's own hard tail to
  gradients, and the pooled 2.8580 vs 2.8205 ordering reverses inside identifiable
  cells. (STE-half's pooled win is already known; *where* it wins is not.)
- **licensed intervention (exact change, conditional):** Anatomy-guided continuation:
  take the champion checkpoint and run a final 25%-of-budget continuation phase on
  English lab-notes + HiveMIND windows only, with the trainer swapped to STE for that
  phase (`--continue-class lab,hive-en --continue-trainer ste --continue-frac 0.25`) —
  spend gradient training exactly on the cells where the Δ anatomy says votes lose,
  and nowhere else. Distinct from every hybrid-by-*layer* entry (A-028/A-032 split
  trainers by module): this splits by *data cell and phase*, a partition only an
  error anatomy can draw. If the losing cells are instead German, the class argument
  flips to `de` — the flag is the intervention, the anatomy chooses its value.
- **pointless if:** Both Δ tables are uniform within ±0.02 across cells — then the
  champion is uniformly a bit better than plain and uniformly a bit worse than STE,
  no cell-targeted phase can beat simply scaling the better trainer, and this lens's
  whole premise (that pooled numbers hide exploitable structure) takes its hardest
  available hit.
- **status:** queued

---

## Miner's ranking note

★★★ are J-013, J-014, J-022. J-013 first: it is the cheapest cut in the file (one
eval pass, no retraining) and the one most likely to embarrass the champion — if a
third or more of the judging set is dump/merges/boilerplate windows scoring ≤1.5, then
"2.8580" has never been a language-modelling number, it is a weighted average of
language modelling and float-stream re-reading, and every verdict the mill has issued
in that currency inherits the dilution. J-022 is its twin from the training side
(leaked lines re-read at ≈2.0 vs unique text at ≈3.4), and the pair put a hard number
— predicted ≈0.5 — on how much of the headline is real. J-014 second because context
entropy is the only mandated axis with *no* filed measurement of any kind, and its
predicted shape (top quintile: ≥35% of the loss, ≈0 of the champion's edge) is the
single most actionable pattern in the file if it lands.

## Lens 4 — Probe fidelity (was TR-###)

### J-025 ★ · The fidelity ledger: score every cheap observable already in runs.jsonl against the 8-min ranking
- **source (fidelity gap):** the mill will trust Δ ≥ 0.05 at 75 s, yet no
  observable's probe→trial fidelity has ever been computed — not even the ones
  already recorded. `train_last100` is *documented* to misrank close arms and
  separate catastrophes; whether flip share, state_hist entropy, or steps rank
  better is unknown.
- **mechanism:** offline analysis only: for the 15 recorded arms, compute
  Spearman ρ and Kendall τ of each candidate feature (and of seed-0 held alone
  as the probe's stand-in) against the 3-seed mean held ranking; report
  sign-flip rate and false-promote rate at the 0.05 bar per feature.
- **exact change:** new `mill/fidelity.py` (read-only over runs.jsonl +
  ledger.jsonl) writing `mill/FIDELITY.md`; PROMOTE.md gains one line: no
  stage's bar is operative until its ρ appears in FIDELITY.md.
- **validation set today:** all 15 arms × 3 seeds in runs.jsonl — zero training.
- **predicted fidelity gain, quantified:** replaces an asserted bar with a
  measured one; expected headline numbers from the recorded spread: seed-0
  held ρ ≈ 0.85–0.92 with 2/13 sign flips (G-062's count), train_last100
  ρ ≈ 0.6–0.75. Whichever feature wins becomes the probe's reported companion.
- **status:** queued

### J-026 ★ · Counter-state ensemble probe: Δheld + flip-share + saturation, one combined score
- **source:** a probe reads only held loss, but the vote mechanism leaves a
  second, independent witness in the counters — and it already separates
  recorded arms by an order of magnitude (mag flip share 0.00011 vs champion
  0.0011; anneal's held catastrophe pairs with an unremarkable 0.00067, i.e.
  loss and counters disagree informatively).
- **mechanism:** probe score = Δheld z-scored within the pass, plus flip-share
  z and counter-saturation fraction (|counter| at clamp share from state_hist)
  z, weights fitted on the calibration arms and frozen; a probe promotes only
  if the ensemble and Δheld do not *disagree in sign* (disagreement →
  `contested`, human's word, like PROMOTE exceptions).
- **exact change:** `sweep_probe.py` logs the three features per probe (two
  already exist in runs.jsonl); `screen.py` computes the ensemble verdict;
  weights + fit live in FIDELITY.md (J-025's output).
- **validation set today:** the 15 arms — fit on 10, check sign agreement on
  the held-out 5 (must include mag, anneal, ste_half); zero training.
- **predicted fidelity gain, quantified:** false-promote rate at the bar from
  the measured 1/13 (≈8%, ste_half seed-0) to ≤1/26 equivalent; target
  ensemble ρ ≥ 0.95 vs seed-0-held-alone ρ ≈ 0.9 on the validation split.
- **status:** queued

### J-027 ★ · The lie registry: per-family onset horizon, and `INCONCLUSIVE` as a first-class probe verdict
- **source — the most dangerous known probe lie:** **a mechanism whose onset
  horizon exceeds the probe's ~25 steps reads flat at probe scale while being
  real (or really harmful) at trial scale.** The D-wave proved it once:
  D-003/D-004/D-005/D-007 are full-trial-only because the counter bank they
  spend is thinnest exactly at probe horizon and flip share there is the
  startup transient. The same lie is already latent outside dreams —
  MILL-111/112 (FP-first pays late), leak/freeze/vsched families, JEPA
  (probe-scale JEPA loss fell 4–5× while held carried no information).
  PROMOTE.md handles this as a hand-kept exception list; nothing generalises it.
- **mechanism:** every pool entry declares `onset_steps` (the step by which
  its mechanism first acts, from its own spec); if onset > probe steps, the
  probe verdict is `INCONCLUSIVE — horizon`, never `flat`/`below`, and the
  entry routes to trial-or-drop by a human's word. The registry in
  FIDELITY.md lists each known lie class with its recorded exemplar.
- **exact change:** pool schema gains `onset_steps:`; `screen.py` maps
  flat/below → inconclusive for over-horizon entries; PROMOTE.md's exception
  list is generated from the registry instead of hand-maintained.
- **validation set today:** D-003/D-004/D-005 protocol rows; carry
  (+0.018, late-acting, near) and cooldown (+0.113) arms; JEPA vs jepa_ctrl
  pair — check the registry retro-classifies all of them correctly.
- **predicted fidelity gain, quantified:** eliminates the false-kill class
  entirely for declared families — on the D-wave's own count, 4 of 7 dream
  entries (57%) were probe-unjudgeable; pool-wide an estimated 15–25% of
  entries (schedules, phases, readouts) carry onset > 25 steps.
- **status:** queued

### J-028 · Rank-correlation admission targets: a stage earns trust, it is not granted it
- **source:** PROMOTE.md sets Δ bars (0.05 / 0.02) with no fidelity floor
  underneath them; RIGOR-AUDIT §5a showed the noise basis was asserted, never
  measured. A bar without a measured ρ is a ritual.
- **mechanism:** pre-registered admission targets per stage, checked on
  J-025's ledger and re-checked each generation: probe stage admitted only
  if Spearman ρ(probe, trial-mean) ≥ 0.80 **and** false-promote ≤ 10% **and**
  false-kill (of eventual trial winners) = 0 on the calibration arms; a stage
  failing any target is demoted to advisory (verdicts ledgered, no trials
  queued from it) until re-calibrated.
- **exact change:** PROMOTE.md gains the admission table; `screen.py` reads
  the stage's admitted/advisory state from FIDELITY.md, never hard-codes it.
- **validation set today:** the 15 arms give the gen-0 admission test for the
  seed-0-held proxy immediately; full probe-stage admission waits on the
  first pass's real probe↔trial pairs (J-033 supplies them continuously).
- **predicted fidelity gain, quantified:** converts silent fidelity rot
  (champion change, machine drift) into a ledgered demotion within one
  generation instead of an unbounded number of mis-judged passes.
- **status:** queued

### J-029 · Probe shape: fewer steps at batch 64 vs more steps at batch 32 — variance against horizon
- **source:** the 75 s probe's shape (batch 32, ~25 steps) was inherited,
  never chosen. Batch 64 halves the steps but cuts per-step gradient noise;
  for sign-vote trainers the evidence per step also changes (one vote per
  batch either way). Which shape's Δ ranks trial outcomes better is a pure
  fidelity question G never asked (it priced shapes, not their truth).
- **mechanism:** on the calibration arms only, run both shapes at 75 s and
  compare each shape's Δ ranking against the recorded 8-min ranking; adopt
  the higher-ρ shape as the probe format, keep the loser as a reported
  cross-check for one generation.
- **exact change:** `sweep_probe.py` gains a `--probe-batch` job field used
  by calibration jobs only until the shape is decided in FIDELITY.md.
- **validation set today:** partial — plain_half's recorded seeds are a
  natural step-count experiment (150 steps → 2.9179 vs 176 → 2.8692) bounding
  the horizon side of the trade; the batch side needs the calibration runs
  (6 arms × 2 shapes × 75 s ≈ 15 min, the only non-zero cost in this wave).
- **predicted fidelity gain, quantified:** expected ρ difference 0.03–0.08
  between shapes; if batch-64 wins, per-Δ standard error falls ~√2 on the
  gradient-noise component at equal seconds.
- **status:** queued

### J-030 · Truncated-held bias curve: what a 32/64-window probe verdict systematically over- and under-states
- **source:** G-064 spends truncated held evals to save seconds and guards
  them with a per-window SE — but SE measures spread, not *bias*: if the
  first-32 strided windows systematically flatter (say) rope arms or punish
  high-flip arms, sequential extension inherits a signed error no CI catches.
- **mechanism:** eval-only re-scoring: take the recorded arms' final
  checkpoints where they exist, or one fresh 8-min champion run, and score
  held at n ∈ {16, 32, 64, 128} per window; publish the signed bias per n
  (subset mean − full mean) and whether bias correlates with arm family.
  No training is involved — held_loss is eval-only by construction.
- **exact change:** `mill/fidelity.py` gains the bias-curve mode; any
  truncated verdict in the ledger must cite the curve's bias at its n.
- **validation set today:** champion + ste_half + mag (three families with
  opposed mechanisms) — eval passes only, minutes not hours.
- **predicted fidelity gain, quantified:** if |bias₃₂| ≥ 0.01 (20% of the
  promotion bar), correcting it removes a systematic misranking of every
  truncated verdict; if |bias₃₂| < 0.003, G-064's economy is certified
  unbiased and this entry closes itself with that number.
- **status:** queued

### J-031 · Pairing dividend, measured: how much of probe fidelity is the shared seed/stream?
- **source:** the probe's one real fidelity asset is pairing — same seed →
  same init and batch stream as job zero (RIGOR-AUDIT §3a). Its size has
  never been priced: nobody knows whether pairing buys ρ 0.02 or 0.20, so
  nobody knows what is lost when a comparison is accidentally unpaired
  (new champion, re-measured baseline, different pass).
- **mechanism:** pure reanalysis: from the 45 recorded runs, compute Δ
  variance two ways — seed-matched pairs (arm seed k vs champion seed k)
  vs all unmatched pairings — per arm family; the ratio is the pairing
  dividend, published per family in FIDELITY.md.
- **exact change:** analysis in `mill/fidelity.py`; PROMOTE.md cites the
  dividend next to the rule that baselines are re-measured per pass (the
  rule's justification becomes a number).
- **validation set today:** all 45 runs; zero training, zero eval.
- **predicted fidelity gain, quantified:** expected dividend 30–60% Δ-variance
  reduction for vote arms (shared stream cancels corpus noise); any family
  where the dividend is ≈0 is flagged — its probes are effectively unpaired
  already and need the J-026 ensemble most.
- **status:** queued

### J-032 · Noise decomposition probe: seed vs machine vs init, factorially separated
- **source:** PREFLIGHT measures job zero on seeds 0/1/2 — one number that
  conflates seed noise, init noise, and machine-speed noise (steps ranged
  129–176 for identical configs in the record). The right remedy differs per
  component (more seeds / step-boxing / nothing), so the conflation blocks
  every fidelity decision downstream, including J-028's targets.
- **mechanism:** factorial design on job zero at probe budget: {seed 0 fixed,
  re-run ×5} isolates machine+stream-replay noise; {seeds 0–4, one run each}
  adds seed/init; the difference of variances is the decomposition. Step-box
  half the fixed-seed replicates (D's step-boxing apparatus) to split
  machine noise into step-count vs pure-timing parts.
- **exact change:** `mill/preflight.py` gains the factorial mode; results
  land in PROBE-NOISE.md as three numbers, not one.
- **validation set today:** the JEPA-control anomaly is the existing
  existence proof (129–139 steps → 2.9173 vs 154–170 → 2.8580, ≈ +0.06 of
  pure machine/step effect — larger than the promotion bar); the factorial
  turns that anecdote into components.
- **predicted fidelity gain, quantified:** if machine/step noise is ≥50% of
  probe variance (the JEPA numbers suggest it can be), step-boxed probes
  alone cut probe σ by ~30% — equivalent to raising the bar's real
  stringency from ~2σ toward ~3σ at zero cost per probe.
- **status:** queued

### J-033 · Trajectory fidelity: rank the probe by its learning-curve slope, not its endpoint
- **source:** a probe's endpoint at step ~25 is one noisy sample of a curve
  still falling steeply; two arms can cross after the probe ends (cooldown's
  effect is by construction late; carry's is cumulative). Endpoint Δ throws
  away the curve's shape, which is the part most likely to extrapolate.
- **mechanism:** calibration-only instrumentation: on the six G-061
  known-answer arms, log held (32-window, log-only, G-070's dual-read
  machinery) at steps 5/10/15/20/25; fit each arm's local power-law slope;
  test whether slope-rank or endpoint-rank better matches the recorded
  8-min ranking, and whether slope+endpoint beats either alone.
- **exact change:** dual-read checkpoints extended to five marks for
  calibration jobs only (production probes keep G-070's two); the winning
  statistic is named in FIDELITY.md before any production use.
- **validation set today:** the six known-answer arms' 8-min endpoints are
  already recorded (champion tie, carry near, plain_half near, cooldown
  loser, anneal catastrophe, ste_half winner); only the 75 s trajectories
  are new (~8 min total).
- **predicted fidelity gain, quantified:** target +0.05–0.10 ρ over endpoint
  alone, concentrated in the near band (|Δ| < 0.10) where G-062 showed every
  recorded sign flip lives.
- **status:** queued

### J-034 · Fidelity decay under champion change: a calibration has a half-life
- **source:** every fidelity number in this file is measured against the
  gen-0 champion (layered_half + rope, 2.8580). When a trial adopts a new
  champion, probe geometry changes with it — step rate, flip regime, Δ
  spread — and yesterday's ρ silently stops describing today's screen.
  Nothing in the mill notices.
- **mechanism:** per generation, FIDELITY.md is re-issued: J-025's analysis
  re-run on that generation's ledger pairs, and each stage's J-028
  admission re-tested. A generation whose probe ρ drops > 0.10 from the
  previous one triggers a printed warning in the bundled report (the one
  early-surface case PROMOTE.md allows besides an adoption).
- **exact change:** `screen.py` pass-end hook runs the fidelity re-issue;
  champion-install (the locked section) invalidates FIDELITY.md's
  admission states until re-issued.
- **validation set today:** gen-0 only — the champion-vs-field spread in
  runs.jsonl (Δ range +0.018..+0.99 across families) is the baseline
  geometry whose drift later generations are compared against.
- **predicted fidelity gain, quantified:** bounds the mill's exposure to a
  stale screen at one generation of verdicts instead of the unbounded
  run the current design permits.
- **status:** queued

### J-035 · Winner's-curse shrinkage: a promoted Δ is a biased estimate of the trial Δ
- **source:** selection guarantees it — probes promote *because* their Δ
  cleared 0.05, so promoted Δs overstate true effects on average. The
  record shows the shrinkage directly: ste_half seed-0 Δ +0.0615 vs its
  3-seed mean Δ +0.0375 (a 39% shrink); carry's per-seed Δs straddle zero.
  Trial expectations, queue priority, and any "expected gain" reporting
  that use raw promoted Δ are systematically optimistic.
- **mechanism:** empirical-Bayes shrink: expected trial Δ = promoted Δ ×
  (signal variance / (signal + noise variance)), with both variances from
  J-032's decomposition and the calibration arms; the shrunk value is
  ledgered beside the raw Δ and used for trial queue ordering (largest
  expected gain first) — verdicts and bars stay on raw Δ.
- **exact change:** `screen.py` ledger gains `delta_shrunk`; PROMOTE.md
  states queue order is by shrunk Δ.
- **validation set today:** the 13 completed non-champion arms — compute
  each arm's seed-0 Δ vs its mean Δ and check the shrink factor recovers
  the mean within ±0.01 on ≥10/13; zero training.
- **predicted fidelity gain, quantified:** removes an expected ~25–40%
  overstatement on promoted arms (ste_half's measured 39% is the anchor),
  reordering the trial queue toward arms whose gains survive averaging.
- **status:** queued

### J-036 · Cross-scale fidelity: does the half-width probe predict the full-width verdict?
- **source:** the chassis is `layered_half` — the probe *and* trial both run
  at half width, but the lab's founding question is about the full model,
  and the HALF-CONTROL already proved one transfer failure: layered's
  apparent win at half size was its step count, not its levels (plain_half
  2.9010 vs layered_half 2.8990). A screen tuned entirely at half width may
  be optimising a geometry the real model does not share.
- **mechanism:** transfer check on recorded pairs: for the families measured
  at both widths (plain, ste, mag, layered — full 3.07/3.00/3.14/3.10 vs
  half 2.901/2.821/—/2.899), compute the half→full rank correlation and the
  sign agreement of each family's half-Δ vs full-Δ against its own width's
  champion; publish as the lab's only measured cross-scale fidelity number,
  extended by the scale arms (2M / 10M) as they complete.
- **exact change:** analysis section in FIDELITY.md; any future claim of
  the form "wins at probe scale" must cite this number when it is read as
  evidence about full width.
- **validation set today:** the four dual-width families in runs.jsonl —
  zero training; the mag-at-full-width calibrated retest (MILL-201..203's
  parent question) is the known open cell, named as such.
- **predicted fidelity gain, quantified:** expected half→full ρ ≈ 0.8 on
  n=4 families with 1 known mechanism-level reversal (the layered
  step-confound) — the deliverable is the honest n and the named reversal,
  replacing an implicit assumption of ρ = 1.
- **status:** queued

---

## Ranking note

J-025 is the root: until the fidelity ledger exists, every other number in
the mill is an assertion. J-026 is the cheapest live improvement (features
already recorded, ensemble fitted offline). J-027 names and fences the
lie that has already cost the lab one wave (D) and is latent in a quarter
of the pool. J-028/J-034 make fidelity a maintained property rather than
a founding hope; J-029..J-033 and J-035/J-036 each convert one named,
recorded anomaly (JEPA step drift, ste_half's shrink, the half-control
reversal, mag's silent counters) into a measured component of the screen's
error budget.

## Lens 5 — Red team (was AG-###)

### J-037 ★ · "Votes reach ≈97% of STE's gain at ~1/10 the state"
- **belief (cited):** RESULTS-HALF-CONTROL-2026-11-12.md: "votes at full width reached ~97% of STE's improvement at ~1/10 the state (3.0743 vs 2.9952)"; founded in RESULTS-2026-11-11.md ("The vote counter at 1.25 B/w of state reaches within 0.08 of a trainer using 12 B/w"). Two load-bearing choices hide inside the sentence: (a) "improvement" is measured from the init loss (~8.3), so a 0.079 absolute gap becomes "97%" only because the denominator is the ~5.3-nat fall from random init — a denominator neither trainer chose; (b) "state" is `mech_state_bytes` only — the ternary mechanism's counters/latents — and excludes the AdamW state both arms carry identically for the FP parts (tied embedding 786,432 params + norms + scales: parameters + two moments ≈ 12 bytes/param ≈ 9.9 MB, present in BOTH arms). Counted as total training state, the ratio is not ~1/10; it is roughly (2.21 + 9.9) / (21.23 + 9.9) ≈ 0.39.
- **strongest fair refutation (exact change):** One pre-registered 2×2 on the filed arms, nothing else changed: {plain (full), ste (full)} × {equal-minutes (the filed 8 min), equal-steps (both arms stopped at exactly 115 steps, the slower arm's filed count)}. Recipes exactly as filed (STE's built-in recipe untouched — recipe parity is J-046's separate question, not smuggled in here). Every record reports BOTH state accountings side by side: `mech_state_bytes` as today, and total training state = mechanism state + all FP parameters + all AdamW moments actually allocated, measured from the process, not estimated. The headline ratio is then recomputed under each cell and each accounting, with the init-denominator stated next to it and the raw held gap (the denominator-free number) given first.
- **outcome that kills the belief:** Either (i) under total-state accounting the vote arm's state is >25% of STE's in any cell — the "~1/10" half of the claim dies as an accounting artefact even if the loss numbers stand; or (ii) at equal steps the held gap widens beyond 0.12 (from the filed 0.079) — the "≈97%" half was partly a step-count artefact (filed steps already differ: plain 115–124, STE 115–119, and at half size the confound the lab itself proved was worth 0.17). Either kill stands alone.
- **outcome that strengthens it:** At equal steps the gap stays ≤0.085 AND the total-state ratio still computes ≤0.15 — then the claim survives the two hardest accountings its defender can be offered, and it should be re-filed in the stronger form ("≈97% at ~1/7 total state, equal steps") with both denominators printed.
- **status:** queued

### J-038 ★ · "The rotary win is real" (2.8580 vs 2.8990)
- **belief (cited):** RESULTS-ROPE-2026-11-11.md verdict: gain 0.0411 "clears 2× the baseline sd (0.0145), 2× the rotary arm's own sd (0.0322), and the 0.01 floor… Rotary positions, done Fable's way, improve our best trainer." The evidence is n=3 seeds per arm; the baseline arm was measured in an earlier window (the sweep), not interleaved with the rotary runs; and RESULTS-JEPA-2026-11-12.md documents that identical configs on this VM took 129–139 steps in one window vs 154–170 in another — a machine-speed drift large enough that a 0.041 gap measured across windows is not yet safe. The rotary arm's own sd (0.0161) is 2.2× the baseline's (0.0073), so the win also rests on the noisier arm's mean.
- **strongest fair refutation (exact change):** A fresh, single-window, interleaved replication: seeds 3, 4, 5 (never used for this claim), arms alternated ABABAB solo in one sitting, each run stopped at a FIXED 160 steps instead of 8 minutes (removing the documented speed drift entirely; wall time recorded but not budgeted). Two scorings of the same six finished models: the standard 128 held windows, and the PROMOTE confirmation windows (every-40th offset by 20) which no verdict has ever selected on. The mechanism is byte-identical to the filed `--rope` implementation; the baseline is the filed layered_half, re-run in-window, never the stored 2.8990.
- **outcome that kills the belief:** Mean paired gain on the fresh seeds < 0.01, OR gain ≥0.01 on the standard held set but ≤0 on the confirmation windows (the signature of selection/window luck, per RIGOR-AUDIT §1b), OR ≥3 of 6 fresh paired comparisons flip sign. Any one kills "the win is real" as filed; what survives is at most "rotary helped on seeds 0–2 in November's window."
- **outcome that strengthens it:** Fresh-seed mean gain ≥0.0322 (2× the rotary arm's filed sd) at fixed steps AND a positive gain on the confirmation windows — the win then holds across new seeds, a fixed-step currency, and an unselected window set, which is strictly stronger evidence than the original filing had.
- **status:** queued

### J-039 · "The gate's strong half is the right half"
- **belief (cited):** train.py (Layered.step / Direct.step): `strong = g.abs() >= g.abs().median(); vote = (-g.sign() * strong)` — only the stronger-|g| half of each layer may vote, inherited from Fable's Direct and present in every vote-arm number the lab has filed. IDEA-POOL MILL-601..606 sweep the quantile q ∈ {0.0…0.9}, but every point on that sweep still selects BY |g| RANK: the pool can discover the best fraction, never whether |g|-rank is the right selector at all. A selector claim is only refuted by a different selector at the same throughput.
- **strongest fair refutation (exact change):** Three arms on layered_half + rope, V=32, identical in every other respect, differing ONLY in which 50% of each layer's weights vote each step: (a) champion — top half by |g| (the filed rule); (b) ANTI-GATE — bottom half by |g| (the weak half votes, the strong half is silenced); (c) RANDOM-HALF — a fresh uniform 50% subset per layer per step (own RNG stream, seed-disciplined), |g| never consulted. Vote throughput, counter mechanics, flip rule, and AdamW parts are identical across arms, so any held difference is attributable to the selection criterion alone. Standard 3 seeds × 8 min.
- **outcome that kills the belief:** Anti-gate OR random-half finishes within 0.01 of the champion (or beats it) — then "strong" selection earns nothing over its exact opposite or over chance at equal throughput, and every design downstream of the gate (soft gate A-001, gate scopes F-005/I-003, band gate I-005) is refining a selector that was never load-bearing. A random-half win is the harder kill: it cannot be explained by weak votes carrying different-but-real signal.
- **outcome that strengthens it:** Champion beats BOTH controls by >2 sd AND >0.01, with anti-gate worst — a clean dose ordering (strong > random > weak) is the exact signature of |g|-rank carrying real evidence, and it converts the gate from an inherited default into a measured result.
- **status:** queued

### J-040 · "Corpus v1's junk didn't matter for the verdicts / v2 will read worse and mean more"
- **belief (cited):** DATA-AUDIT.md §8: v1 stays "the canonical corpus for the current experiment series" because "Arm-vs-arm comparisons (same corpus, same split) remain valid," and v2 held loss is expected to read higher "partly because the duplicate leakage in §4 is gone" — i.e. the filed position is that v1's 73.9% junk bytes, 23% numeric dumps and merge-table gibberish inflate the LEVEL but preserve the RANKING and the MARGINS. E-018 (v2 re-baseline of the champion alone) tests the level on one arm; it cannot test the ranking, because a ranking needs at least two arms on both corpora.
- **strongest fair refutation (exact change):** A 2-corpus × 3-arm transfer matrix, full trial format on both sides: arms = champion (layered_half+rope), plain_half+rope (the half-control's tied rival — deliberately the closest filed margin, 0.0020 at half size without rope), ste_half (the filed leader at half size, 2.8205). On v1: the filed numbers stand as the v1 column (no re-run). On v2: all three arms trained on corpus-v2 with v2-native held windows (every-40th rule on the v2 stream, the E-018 construction), 3 seeds × 8 min, PLUS each v2-trained model cross-scored on the v1 held windows and vice versa, so a corpus-difficulty shift is separable from a ranking change. Distinct from E-018 (one arm, level only) and from J-042 (leak share of one number on v1 itself).
- **outcome that kills the belief:** Any pairwise ordering inverts on v2 (e.g. ste_half's filed 0.0375 lead over the champion reverses, or plain_half+rope separates from the champion by >0.01 in either direction), OR the champion-vs-plain margin on v2 exceeds 5× its v1 value — then v1's junk was not a neutral level shift: it was compressing or manufacturing margins, and "arm-vs-arm on v1 remains valid" dies for exactly the close verdicts the lab trades in.
- **outcome that strengthens it:** All three pairwise orderings preserved on v2 and every margin within ±0.02 of its v1 value, while all v2 levels read worse — the audit's §8 position then has a measured ranking-preservation result behind it instead of an argument, and v1 verdicts can be quoted with that transfer bound attached.
- **status:** queued

### J-041 · "The champion is the right chassis for the mill's gen 0"
- **belief (cited):** IDEA-POOL.md: "probes run on the lab's best stack: layered_half + rotary… every verdict is relative to it," and PROMOTE.md's funnel judges all ~368 pooled entries against job zero on that chassis. But the chassis was never the best measured stack: RESULTS-HALF-CONTROL-2026-11-12.md records ste_half at 2.8205, beating the champion's 2.8580 by 0.0375 (clearing the bar), and plain_half tying layered_half (gap 0.0020) at half the mechanism state. Gen 0's chassis is therefore a choice (vote-economy over held loss), and every gen-0 verdict silently assumes treatment effects measured on it transfer — that an idea's sign on layered votes predicts its sign on the arms the lab might actually adopt.
- **strongest fair refutation (exact change):** A chassis-transfer audit, probe format, no new ideas: take 12 already-pooled entries stratified across families (3 vote-mechanics, 3 continuous-parts, 3 architecture, 3 data/sampler — the pool owner picks by a pre-stated rule: the first queued entry of each family in IDEA-POOL order, no cherry-picking after seeing results). Run each entry AND its job-zero control on THREE chassis: (a) champion layered_half+rope, (b) plain_half+rope, (c) ste_half+rope — same seed 0, same 75 s budget, fresh job zero per chassis per pass (PROMOTE's own freshness rule). The product is the 12×3 sign table of Δ vs own-chassis job zero, not 36 new verdicts.
- **outcome that kills the belief:** ≥3 of 12 entries flip Δ sign between chassis (a), and either (b) or (c) — then gen-0 verdicts are chassis-local facts, "the right chassis" is false in the only sense the mill uses it, and any adoption decision needs a second-chassis confirmation before it can be stated generally. A flip concentrated in one family kills the belief for that family and is reported as such, not averaged away.
- **outcome that strengthens it:** ≤1 sign flip across the 36 cells and a rank correlation of Δ ≥0.8 between chassis — the champion then earns its gen-0 role empirically: not the best stack, but a demonstrated neutral yardstick, which is the property the funnel actually needs.
- **status:** queued

### J-042 ★ · "Held windows are clean" — how much of 2.8580 is the leak?
- **belief (cited):** The lab's founding measurement discipline (RESULTS-2026-11-11.md): the judge is "held loss on a fixed set of 128 held windows (every-40th-window rule; no arm ever trained on them)." DATA-AUDIT.md §4 refutes the strong reading in the lab's own words — 30.8% of all pieces are exact-duplicate copies, 93.2% of lines belong to some duplicated group, so "held-out content routinely also appears in training windows, so all v1 held losses are flattered by an unknown amount" — yet 2.8580 continues to function as the mill's gen-0 reference (PROMOTE.md) with the flattery unpriced. E-019 (excise held-duplicating lines, re-run) prices it one way, but a single excision number cannot distinguish "the leak is small" from "excision also removed legitimate near-held training signal." This entry adds the calibration E-019 lacks.
- **strongest fair refutation (exact change):** Three champion runs, 3 seeds × 8 min each, held windows byte-identical in all three: (a) FILED — v1 as-is (control; expected to reproduce 2.8580 in-window); (b) EXCISED — E-019's construction (every training-side line whose exact text appears inside any held window is removed; all other junk left in); (c) DOSED — v1 as-is PLUS a synthetic leak of known size: the held windows' lines are injected into the training side at exactly 5% of training pieces, evenly spread. Run (c) is the calibration: it measures how much held loss a KNOWN 5-point leak buys on this rig, converting run (b)'s Δ from an uninterpretable difference into a leak-share estimate (Δ_b ÷ Δ_c × 5%). Additionally, every held window is scored individually in (a) and split post-hoc into "leaked" (≥1 of its lines found verbatim in the training stream) vs "clean" windows, and both slice means are reported — the slice gap is a second, independent leak estimate from the same runs.
- **outcome that kills the belief:** Calibrated leak share ≥2% of pieces-equivalent, OR excision worsens held by ≥0.0411 (rotary's entire filed margin — at that point the lab's one confirmed win fits inside its leak band), OR the leaked-vs-clean held slice gap in run (a) exceeds 0.10. Any one means "held windows are clean" is false at a magnitude that reaches filed verdicts, and 2.8580 must be re-filed as a range, not a point.
- **outcome that strengthens it:** Excision Δ < 0.01, calibrated share <0.5%, and slice gap <0.03 — then the audit's "unknown amount" becomes a measured small amount, the founding discipline is vindicated with a number, and E-019/G-015 can be retired as priced-and-closed instead of standing worries.
- **status:** queued

### J-043 · "Equal minutes is the lab's fair currency"
- **belief (cited):** Every RESULTS file budgets arms at 8 minutes ("3 seeds × 8 minutes, same wall-clock discipline as every prior arm," RESULTS-JEPA-2026-11-12.md), and PROMOTE.md trials inherit the format. The half-control proved the currency can manufacture a winner: layered_half's celebrated win was ~161 steps vs ~115–121 at equal minutes and vanished at equal size/steps (gap 0.0020). Yet two REJECTIONS were filed in the same currency and never re-checked in the other: overshoot carry (+0.0181, steps 154–158 vs baseline 154–170) and AdamW cooldown (+0.1127, steps 148–155), RESULTS-ROUND2-2026-11-12.md — the cooldown note itself concedes "step differences elsewhere in this lab move held loss by ~0.05 at most," an estimate, not a measurement, doing load-bearing work in a rejection.
- **strongest fair refutation (exact change):** Re-run exactly the round-2 pair at FIXED STEPS: carry and cooldown, 3 seeds each, every run (including a fresh in-window champion control) stopped at exactly 155 steps — the midpoint of the filed step ranges — with all other settings byte-identical to run_round2.py. No new arms, no tuning: this is the filed experiment with one variable (the currency) changed, which is what makes it fair to the original authors.
- **outcome that kills the belief:** Either rejected arm's fixed-step mean comes within 0.01 of the fresh champion control (or beats it) — then at least one standing rejection is a currency artefact, "equal minutes is fair" dies as a general rule, and every close verdict in the record (any |Δ| < 0.06, the measured step-effect band) needs a stated currency before it can be quoted.
- **outcome that strengthens it:** Both rejections reproduce at fixed steps within ±0.015 of their filed gaps — the currency question is then settled for the only two rejections it could plausibly have manufactured, and the 8-minute format gains a measured robustness result instead of a precedent from one direction (the half-control) only.
- **status:** queued

### J-044 · "The mill's probe funnel can tell signal from noise"
- **belief (cited):** PROMOTE.md: probe Δ ≥ 0.05 promotes to trial, justified because "probe noise at 75 seconds is much larger than the full-format seed sd (0.0161), so the bar is set loose on purpose." RIGOR-AUDIT.md §5a flags the hole: that probe noise "has never been measured: job zero has never been run at probe budget, on any seed" — so nobody knows whether 0.05 is 3σ (a screen) or 0.5σ (a coin flip promoting ~a third of the pool). The funnel is the mill's front door; every gen-0 "flat/below" ledger line is a belief that the door works.
- **strongest fair refutation (exact change):** A null-probe census, the cheapest entry in this file: run JOB ZERO against itself at probe format — champion config, seed 0, 75 s, 20 replicates, interleaved across one full mill pass so machine drift is inside the sample, each replicate scored against that pass's fresh job-zero baseline exactly as screen.py scores a real probe. No code change beyond replicate count: the replicates differ only by the nondeterminism and load variation the mill already lives with. The deliverable is the empirical null distribution of Δ for an idea that is BY CONSTRUCTION identical to the baseline.
- **outcome that kills the belief:** ≥2 of 20 null replicates reach Δ ≥ 0.05 (the promote line), or the null Δ sd exceeds 0.025 (making 0.05 a <2σ bar) — then the funnel promotes noise at a measured rate, every "promote" in the ledger is suspect until re-screened, and PROMOTE_DELTA must be re-set from the measured null, not from the full-format sd.
- **outcome that strengthens it:** 0 of 20 nulls promote and null sd ≤0.017 — the 0.05 bar is then a measured ≥3σ screen, the audit's §5a gap closes with the number it asked for, and "flat" verdicts at probe scale gain the standing they currently borrow.
- **status:** queued

### J-045 · "Eight-minute verdicts extrapolate to longer budgets"
- **belief (cited):** The lab closes arms at 8 minutes (carry and cooldown "tested and closed," RESULTS-ROUND2-2026-11-12.md; anneal 8→64 closed, magnitude votes as-specified closed) — while simultaneously excusing one arm in the opposite direction: RESULTS-2026-11-11.md on layered at equal weights: "in 8 minutes the ±2 levels were barely populated (1.7% of weights at each of −2/+2)… this is a verdict about 8 minutes, not about the idea's ceiling. A founding-length (40 min) run is the honest next test." That test was never run. The standing practice therefore believes both "8 minutes is enough to close an arm" and "8 minutes is not enough to judge an arm," choosing per arm.
- **strongest fair refutation (exact change):** One founding-length matrix, 40 min × 3 seeds, solo, fixed settings from the filed drivers: champion (layered_half+rope), layered FULL width + rope (the excused arm — its ±2 population at 40 min is itself a logged endpoint), and carry (a closed arm, re-run at the length its mechanism — leftover evidence compounding across flips — most plausibly needs). Held, state histograms, and flip share logged at 8-minute checkpoints inside each run, so the 8-minute ranking and the 40-minute ranking come from the SAME trajectories with no window confound.
- **outcome that kills the belief:** Any ranking inversion between the 8-minute checkpoint and the 40-minute endpoint among the three arms, OR layered-full's ±2 population rises above 10% while its held loss crosses below plain's filed standing — then closure-at-8-minutes is a horizon artefact, every "closed" entry in the pool appendix re-opens in principle, and the mill's trial format (not just its probe format) needs a horizon guard.
- **outcome that strengthens it:** Identical ordering at 8 and 40 minutes with margins growing or holding, and layered-full's levels still unpopulated (<4%) at 40 min — then the 8-minute closures were horizon-safe, the one excuse in the record is retired by measurement, and short-format verdicts can be quoted without the caveat.
- **status:** queued

### J-046 · "The champion's gain is vote training's gain"
- **belief (cited):** The lab's framing throughout: the vote trainer is the mechanism under study and 2.8580 is its result. But in every vote arm the FP parts — tied embedding (786,432 params, ~83% of served bytes per CANDIDATES-H WH-014's audit), norms, and per-layer scales — train by ordinary AdamW, and RESULTS-2026-11-11.md itself names the confound for layered_half: "its ordinary-trained share… is proportionally twice as large — so more of its learning rode on ordinary gradients, not on votes." F-055 (frozen-ternary reservoir) prices votes-vs-nothing from a random start; it cannot attribute the FINISHED champion's loss between its two trained halves. Nobody has.
- **strongest fair refutation (exact change):** A parts-transplant on finished models, eval-only, no retraining: take the 3 filed champion runs' final states and the 3 plain_half runs' final states (same seeds). Construct the two hybrids per seed: (a) champion FP parts (embedding, norms, scales) + plain_half ternary body; (b) plain_half FP parts + champion ternary body. Score all four combinations (2 originals + 2 hybrids) on the standard held set with the shared `held_loss()`. Because both parents share shape (884,736 ternary, dim 192 × 2 blocks) and seed-matched init, the transplants are well-defined; any hybrid collapse from part incompatibility is itself reported per seed, not hidden.
- **outcome that kills the belief:** Hybrid (a) — champion FP parts carrying an ordinary plain body — recovers ≥70% of the champion's held advantage over plain_half, while hybrid (b) recovers ≤30% — then the champion's edge lives in its AdamW-trained parts, the vote-side story (layered structure, rotary-on-votes) is demoted to a minor contributor, and the mill is optimising the smaller half of its own model. (If both hybrids collapse >0.15 below both parents, the parts are co-adapted and attribution by transplant is void — reported as void, not spun either way.)
- **outcome that strengthens it:** Hybrid (b) recovers ≥70% and hybrid (a) ≤30% — the gain follows the ternary body, the lab's central attribution is confirmed by the strongest instrument available (stronger than F-055's freeze, which conflates "votes earn" with "a random body can be compensated"), and the FP-share caveat in the 2026-11-11 record can be closed.
- **status:** queued

### J-047 · "The pooled held number represents prose quality"
- **belief (cited):** Every verdict quotes one pooled mean over the 128 held windows as "held loss," implicitly the model's language-modelling quality. But the held windows are drawn from v1's stream, whose composition the audit measured (DATA-AUDIT.md §3/§5): merge-table gibberish, numeric dumps and boilerplate dominate the source mix, and scale-next/GATE0-READY.md's bucket census of v1's held candidates reads: gibberish 313, numeric 144, prose 78, german 40, lists 3 of 578. A pooled mean over such a set can crown an arm that wins on gibberish and loses on prose. I-011/I-012 bin held by token frequency and by position; nobody has binned the standard verdict by source bucket. G-019/E-021 slice held per source only inside their own arms.
- **strongest fair refutation (exact change):** Eval-only re-scoring of three already-trained arm families (champion, plain_half, ste_half — final states / fresh seed-matched re-runs if states were not kept, stated either way): the standard 128 held windows are tagged by the GATE0 bucket_probe classification (gibberish / numeric / prose / german), and held loss is reported per bucket alongside the pooled mean, per seed. No training change, no new held data, no arm gets a bucket it was not already judged on in aggregate.
- **outcome that kills the belief:** The pooled ranking (ste_half < champion < plain-family) inverts on the prose bucket, or the champion's pooled advantage over plain_half is entirely (≥90%) carried by the gibberish+numeric buckets with the prose bucket tied or reversed — then the lab's headline numbers measure junk-stream fit, every "held loss" claim must be re-filed bucket-first, and v2's "read worse and mean more" (J-040) stops being a prediction and becomes the only honest reporting format.
- **outcome that strengthens it:** The pooled ranking holds in EVERY bucket with ≥40 windows, and bucket margins are within 2× of the pooled margin — the pooled number is then a demonstrated fair summary of a skewed set, and single-number reporting is vindicated rather than merely habitual.
- **status:** queued

### J-048 · "Rotary's gain is a property of rotary, not of the layered chassis it was measured on"
- **belief (cited):** RESULTS-ROPE-2026-11-11.md tested rotary on exactly one arm — "the question was whether it improves our best trainer" (layered_half) — and the champion stack, the mill chassis (IDEA-POOL.md), and the scale ladder ("Best recipe throughout: layered + rotary + plain votes," scale-next/NUMBERS.md) all inherit rotary as a general ingredient. Yet runs.jsonl contains no plain_half+rope and no ste_half+rope arm at any budget: rotary has never been measured on the plain vote trainer it supposedly also improves, nor on the STE trainer that actually leads at half size (2.8205). An interaction — rotary helping only where layered counters are the bottleneck — is fully consistent with everything filed.
- **strongest fair refutation (exact change):** Complete the 2×2 the record skipped, at half size, fixed 160 steps (J-038's currency, so the two entries share controls where they overlap): {plain_half, layered_half} × {rope, no-rope}, seeds 0–2, plus the single decisive fifth arm ste_half+rope at 8 min × 3 seeds (its no-rope control, 2.8205, is already filed). plain_half+rope is a config run of the existing `--rope` flag on the Direct trainer — no new mechanism code. Report the interaction term directly: (layered rope gain) − (plain rope gain).
- **outcome that kills the belief:** Plain's rope gain ≤0.01 while layered's replicates at ≥0.03 (interaction ≥0.02), OR ste_half+rope fails to beat ste_half's filed 2.8205 by the standing bar — then "rotary improves our trainers" is false as a general claim; what is true is "rotary repairs something specific to the layered vote chassis," the ladder's recipe justification must be rewritten in those terms, and rotary should not be assumed into any future chassis (including the mill's gen-1) without a per-chassis test.
- **outcome that strengthens it:** Rope gains on plain and layered agree within ±0.015 and ste_half+rope clears its bar — rotary is then a measured main effect across two trainer families and both vote structures, the strongest generality evidence any ingredient in this lab would hold, and its place in the ladder recipe is earned rather than inherited.
- **status:** queued

---

## Closing note — what I could not kill on paper

**The JEPA loss stands.** RESULTS-JEPA-2026-11-12.md's claim is explicitly bounded
("at lab scale and budget, for the token work this lab's models actually do"), was
judged by a pre-registered rule, and won by 17× its own bar: control beats JEPA on
3 of 3 seeds (mean margin 0.3493 against a 0.02 threshold), JEPA's probe CE
(3.2428) is indistinguishable from the untrained init floor (3.2445), and the JEPA
machinery demonstrably worked (loss fell 4–5×, no representation collapse) — so
there is no malfunction to appeal to. Every refutation I could design either
changes the yardstick (an alignment probe the lab does not have — moving the posts
the filing itself warns against), changes the budget/scale (which tests a different,
unfiled claim), or re-runs the same test hoping for noise (a 0.35 gap at sd ~0.05
does not fall to re-rolling). A fair kill for the filed claim does not exist; the
honest red-team verdict is that this belief is load-bearing AND sound, and the
pool's "JEPA objective: closed" entry should stay closed at this scale. The same
holds, by a wider margin, for the anneal 8→64 rejection (filed gap 0.78, ~27× its
sd) — I did not spend an AG entry on either.

*12 entries, J-037..J-048, all queued. ★ = J-042, J-038, J-037 (see the
report's fragility ranking). Nothing here edits IDEA-POOL.md or any CANDIDATES
file; merging is the pool owner's call.*

---

## Appendix — working-id mapping (miners -> wave J)

- SY-001 -> J-001
- SY-002 -> J-002
- SY-003 -> J-003
- SY-004 -> J-004
- SY-005 -> J-005
- SY-006 -> J-006
- SY-007 -> J-007
- SY-008 -> J-008
- SY-009 -> J-009
- SY-010 -> J-010
- SY-011 -> J-011
- SY-012 -> J-012
- ER-001 -> J-013
- ER-002 -> J-014
- ER-003 -> J-015
- ER-004 -> J-016
- ER-005 -> J-017
- ER-006 -> J-018
- ER-007 -> J-019
- ER-008 -> J-020
- ER-009 -> J-021
- ER-010 -> J-022
- ER-011 -> J-023
- ER-012 -> J-024
- TR-001 -> J-025
- TR-002 -> J-026
- TR-003 -> J-027
- TR-004 -> J-028
- TR-005 -> J-029
- TR-006 -> J-030
- TR-007 -> J-031
- TR-008 -> J-032
- TR-009 -> J-033
- TR-010 -> J-034
- TR-011 -> J-035
- TR-012 -> J-036
- AG-001 -> J-037
- AG-002 -> J-038
- AG-003 -> J-039
- AG-004 -> J-040
- AG-005 -> J-041
- AG-006 -> J-042
- AG-007 -> J-043
- AG-008 -> J-044
- AG-009 -> J-045
- AG-010 -> J-046
- AG-011 -> J-047
- AG-012 -> J-048

---

**Errata (filed 2026-11-12 by the endgame miner, verified against the entry bodies):** the coordinator note above mislabels the dosed-leak calibration as J-037. The filed body under J-037 is the votes-vs-STE accounting audit; the dosed-leak calibration is **J-042** (with J-022 anatomy and E-019 excision). Cite J-042 for the leak in all downstream documents, including the Sunday bundle.
