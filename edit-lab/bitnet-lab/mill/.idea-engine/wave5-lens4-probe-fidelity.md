# Wave 5 · Lens 4 — PROBE FIDELITY (Idea Engine, rotation 5, miner 4)

Muse's work — Muse's side

<!-- Muse's work — Muse's side of the BitNet lab. Not Fable's side; nothing here touches it. -->

**Territory.** The mill's economy is a chain of proxies: a 75 s probe (~25 steps,
seed 0) predicts an 8-min trial (3 seeds), and the trial predicts a real win.
CANDIDATES-G (G-061..G-072) optimised that chain's **cost**; CANDIDATES-D fixed
the dream family's evaluation protocol. Nobody has measured the chain's
**fidelity** as its own object: what rank correlation does a probe actually
carry, where does it systematically lie, and what should the mill demand
before trusting a stage? Every entry below states the recorded arms it can be
checked against **today, at zero training cost**, where one exists.

**Ground truth available today** (`runs.jsonl`, 45 runs): 15 arms × 3 seeds at
8 min — plain 3.0743, ste 2.9952, mag 3.1352, layered 3.0977, layered_half
2.8990, anneal 3.8503, layered_half_rope (champion) 2.8580, plain_half 2.9010,
ste_half 2.8205, carry 2.8761, cooldown 2.9707, jepa_ctrl 2.9173, jepa 3.24x,
plus scale arms (2M / 10M). Each run already carries candidate probe features:
`held_final`, `steps`, `train_last100`, `mean_flip_share`, `state_hist`.
**No probe-budget run exists yet** — that absence is itself TR-001's finding.
Deduped against G-061 (stage-0 cost), G-062 (banded seed), G-064 (eval
economy), G-065 (step-10 kill), G-068 (steps covariate), G-070 (dual reads),
G-071 (proxy windows), E-022/E-023, and D's probe table: entries here reuse
their machinery only as instruments, never re-propose their savings.

---

### TR-001 ★ · The fidelity ledger: score every cheap observable already in runs.jsonl against the 8-min ranking
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

### TR-002 ★ · Counter-state ensemble probe: Δheld + flip-share + saturation, one combined score
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
  weights + fit live in FIDELITY.md (TR-001's output).
- **validation set today:** the 15 arms — fit on 10, check sign agreement on
  the held-out 5 (must include mag, anneal, ste_half); zero training.
- **predicted fidelity gain, quantified:** false-promote rate at the bar from
  the measured 1/13 (≈8%, ste_half seed-0) to ≤1/26 equivalent; target
  ensemble ρ ≥ 0.95 vs seed-0-held-alone ρ ≈ 0.9 on the validation split.
- **status:** queued

### TR-003 ★ · The lie registry: per-family onset horizon, and `INCONCLUSIVE` as a first-class probe verdict
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

### TR-004 · Rank-correlation admission targets: a stage earns trust, it is not granted it
- **source:** PROMOTE.md sets Δ bars (0.05 / 0.02) with no fidelity floor
  underneath them; RIGOR-AUDIT §5a showed the noise basis was asserted, never
  measured. A bar without a measured ρ is a ritual.
- **mechanism:** pre-registered admission targets per stage, checked on
  TR-001's ledger and re-checked each generation: probe stage admitted only
  if Spearman ρ(probe, trial-mean) ≥ 0.80 **and** false-promote ≤ 10% **and**
  false-kill (of eventual trial winners) = 0 on the calibration arms; a stage
  failing any target is demoted to advisory (verdicts ledgered, no trials
  queued from it) until re-calibrated.
- **exact change:** PROMOTE.md gains the admission table; `screen.py` reads
  the stage's admitted/advisory state from FIDELITY.md, never hard-codes it.
- **validation set today:** the 15 arms give the gen-0 admission test for the
  seed-0-held proxy immediately; full probe-stage admission waits on the
  first pass's real probe↔trial pairs (TR-009 supplies them continuously).
- **predicted fidelity gain, quantified:** converts silent fidelity rot
  (champion change, machine drift) into a ledgered demotion within one
  generation instead of an unbounded number of mis-judged passes.
- **status:** queued

### TR-005 · Probe shape: fewer steps at batch 64 vs more steps at batch 32 — variance against horizon
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

### TR-006 · Truncated-held bias curve: what a 32/64-window probe verdict systematically over- and under-states
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

### TR-007 · Pairing dividend, measured: how much of probe fidelity is the shared seed/stream?
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
  already and need the TR-002 ensemble most.
- **status:** queued

### TR-008 · Noise decomposition probe: seed vs machine vs init, factorially separated
- **source:** PREFLIGHT measures job zero on seeds 0/1/2 — one number that
  conflates seed noise, init noise, and machine-speed noise (steps ranged
  129–176 for identical configs in the record). The right remedy differs per
  component (more seeds / step-boxing / nothing), so the conflation blocks
  every fidelity decision downstream, including TR-004's targets.
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

### TR-009 · Trajectory fidelity: rank the probe by its learning-curve slope, not its endpoint
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

### TR-010 · Fidelity decay under champion change: a calibration has a half-life
- **source:** every fidelity number in this file is measured against the
  gen-0 champion (layered_half + rope, 2.8580). When a trial adopts a new
  champion, probe geometry changes with it — step rate, flip regime, Δ
  spread — and yesterday's ρ silently stops describing today's screen.
  Nothing in the mill notices.
- **mechanism:** per generation, FIDELITY.md is re-issued: TR-001's analysis
  re-run on that generation's ledger pairs, and each stage's TR-004
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

### TR-011 · Winner's-curse shrinkage: a promoted Δ is a biased estimate of the trial Δ
- **source:** selection guarantees it — probes promote *because* their Δ
  cleared 0.05, so promoted Δs overstate true effects on average. The
  record shows the shrinkage directly: ste_half seed-0 Δ +0.0615 vs its
  3-seed mean Δ +0.0375 (a 39% shrink); carry's per-seed Δs straddle zero.
  Trial expectations, queue priority, and any "expected gain" reporting
  that use raw promoted Δ are systematically optimistic.
- **mechanism:** empirical-Bayes shrink: expected trial Δ = promoted Δ ×
  (signal variance / (signal + noise variance)), with both variances from
  TR-008's decomposition and the calibration arms; the shrunk value is
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

### TR-012 · Cross-scale fidelity: does the half-width probe predict the full-width verdict?
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

TR-001 is the root: until the fidelity ledger exists, every other number in
the mill is an assertion. TR-002 is the cheapest live improvement (features
already recorded, ensemble fitted offline). TR-003 names and fences the
lie that has already cost the lab one wave (D) and is latent in a quarter
of the pool. TR-004/TR-010 make fidelity a maintained property rather than
a founding hope; TR-005..TR-009 and TR-011/TR-012 each convert one named,
recorded anomaly (JEPA step drift, ste_half's shrink, the half-control
reversal, mag's silent counters) into a measured component of the screen's
error budget.
