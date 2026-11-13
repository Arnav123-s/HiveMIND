# CANDIDATES-F — Idea Engine wave F (Muse's work, Muse's side)

<!-- Muse's work — Muse's side of the BitNet lab. Produced 2026-11-12 by the Idea Engine
(coordinator + 6 lens miners) under Arnav's no-limit ideation order. This is a CANDIDATE
file: nothing here is in the pool until the pool's owner merges it. IDEA-POOL.md was read
by every miner and NOT edited. Hive-side output of this wave lives separately in
factory/CANDIDATES-IDEAS.md (15 entries, H-001..H-015). -->

## Method and de-duplication

Six lenses ran in parallel: first-principles, cross-domain transfer, failure inversion,
scale extrapolation, hive-side (factory file), wild cards. Every miner deduped against
IDEA-POOL.md (368 entries incl. merged A–D), CANDIDATES-A/B/C/D, CANDIDATES-E (24 entries,
read in full by the failure-inversion and cross-domain miners), and FABLE-CANDIDATES.md.
Nothing closed is re-proposed in its failed form: overshoot carry, AdamW cooldown,
threshold anneal 8→64, magnitude votes as specified, the JEPA objective.

**Chassis** unless an entry says otherwise: layered_half + rotary, V=32, champion held
**2.8580 ± 0.0161**; adoption bar >2sd AND >0.01; probe = 75s/1 seed vs job zero; trial =
3 seeds × 8 min. Entries are grouped by lens below, each lens internally ranked; ids were
renumbered F-001..F-066 at merge (appendix maps the miners' working ids).

**Deliberate near-neighbour pair, kept as a bracket:** F-001 and F-016 attack the SAME
defect — strong votes destroyed by the boundary no-op on saturated weights — from opposite
sides: F-001 reroutes the destroyed pressure into the layer's log_scale; F-016 stops
integrating it (anti-windup). Running both prices the defect and the two candidate fixes
against each other; neither duplicates the other.

## Coordinator's top 3 for this wave ★

1. **F-001 · Boundary-pressure rerouting** — the ternary state space is bounded, so every
   outward vote on a saturated weight is provably destroyed signal; the layer's log_scale
   is the one continuous channel it could exit through. The current trainer loses it on
   what is plausibly a large share of all strong votes late in training. Predicted
   −0.02..−0.05 at trial scale.
2. **F-043 · Vote-threshold scaling law (V must fall as N rises)** — flip share fell ~5×
   from 0.885M to 10M at fixed V=32; at 50M most weights would never flip in any feasible
   run, silently freezing every other scale measurement against a near-init baseline.
   Cheap sweep at 10M (V ∈ {32,16,8,4}) with 2M as the flat negative control.
3. **F-055 · The reservoir control** — freeze all ternary weights at random init, train
   only the FP parts. One probe prices what vote training itself earns over no training;
   the whole program's effect size is currently unmeasured. Killed if ≥ job-zero + 0.30.

**Wildest entry that still has a real kill test: F-061 · Scalar-feedback votes** — the
vote path never sees a per-weight gradient; one global bit per step (batch loss fell/rose)
reinforces or punishes every counter in its current direction. Retires if its probe lands
within 0.02 of F-055's frozen-reservoir probe, or ≥ job-zero + 0.20 standalone.

---

## Lens 1 — First-principles (was FP-###)

### F-001 · Boundary-pressure rerouting: saturated votes feed the scale ★
- **source:** first-principles derivation — ternary state space is bounded ({-1,0,+1} per component, installed {-2..+2}), so a strong vote pushing a saturated weight further outward triggers the boundary no-op rule and its information is *destroyed*. Gradient pressure is a conserved signal in the backward pass: whatever the discrete state cannot express must exit through a continuous channel or be lost. The only continuous channel attached to the same layer is its install scale (log_scale).
- **mechanism:** when a component sits at its boundary (+1 with a + vote, -1 with a - vote) and the vote is strong (passes the median gate), the vote does not increment the counter; instead it adds a small fixed quantum (1/V of a step) to a per-layer boundary-pressure accumulator. At each step the layer's log_scale is nudged by lr_scale × (net boundary pressure that step), then the accumulator resets. Inward and ordinary votes behave exactly as champion.
- **train.py:** new flag `--boundary-scale` on Layered (boundary votes diverted from `c1/c2` into a per-layer scalar; applied to `log_scale` inside `step()`, alongside the existing AdamW update of the same parameter — the two contributions sum).
- **mode:** process
- **prediction:** -0.02..-0.05 at trial scale. Reasoning: the zero-heavy trained histogram means a large share of weights sit at ±1/±2 late in training, so the discarded outward stream is a substantial fraction of all strong votes — recovering it as scale motion is recovering magnitude information the ternary code structurally cannot hold (the same information STE carries in its latent weights). At probe scale expect ~0 to -0.01 (few weights are saturated in the first ~25 steps); a probe win is not required, a probe *loss* >0.02 kills it.
- **status:** queued
```mill
id: F-001
mode: process
run: --arm layered_half --rope --boundary-scale
```

### F-002 · Weak-half slow counter: the gated-out 50% votes on a long clock ★
- **source:** first-principles derivation — the median gate keeps the stronger half of gradients and discards the weaker half entirely (0 bits retained). But a weak vote is a Bernoulli sample with the same sign bias p as a strong one, only noisier per sample; by the law of large numbers, the *sum* of N weak votes has SNR growing as √N·(2p-1), so over a long enough horizon the discarded half carries flip-grade evidence. Discarding it is optimal only if the horizon is infinite for the strong stream and zero for the weak — the current design.
- **mechanism:** each weight gains a second, slow counter fed ONLY by gated-out (weak-half) votes, with its own threshold V_slow = 128 (4× V). A flip fires when *either* counter crosses its threshold (fast counter at ±32 from strong votes, slow counter at ±128 from weak votes); on any flip both counters reset. Distinct from the pooled two-counter race (A-006: up/down split, BOTH conditions required, same stream), from A-109 dual streams (alternating batches, consensus required), and from the soft gate (A-001: reweights strong-side increments, weak side still contributes exactly 0).
- **train.py:** new flag `--weak-slow 128` on Layered (int16 slow counters; gate already computes the weak/strong partition, so the weak votes exist in `step()` today and are thrown away there).
- **mode:** process
- **prediction:** -0.01..-0.04 at trial scale, ~0 at probe scale by construction (128 net weak votes cannot accumulate in ~25 steps — the probe is a plumbing check only; judge at trial). Reasoning: weak-stream flips will be rare and late, but they are flips the champion *never* makes, on evidence that is unbiased; the risk is that weak votes are weak because their weights are genuinely contested (p≈0.5), in which case slow counters random-walk and almost never cross ±128 — the mechanism is self-limiting, which caps the downside near 0.
- **status:** queued
```mill
id: F-002
mode: process
run: --arm layered_half --rope --weak-slow 128
```

### F-003 · Orthogonal second channel: t2 votes on the gradient innovation ★
- **source:** first-principles derivation — information theory of the layered code: both component counters integrate the *same* vote stream sign(g) (gated). Two integrators fed identical inputs carry exactly 1 bit/step of new information in total, however many counters there are; the second component's counter adds state but no bandwidth. The gradient stream contains a second, nearly independent bit per step — the sign of the innovation, sign(g_t − EMA(g)) — which is (to first order) uncorrelated with sign(g) itself and is currently computed by no one.
- **mechanism:** c1 integrates the champion vote stream unchanged. c2 integrates sign of the per-weight gradient innovation: vote2 = sign(g − ḡ) when |g − ḡ| clears its own layer median, where ḡ is a per-weight EMA of g (β=0.9, fp state charged honestly at 4 B/weight). t2 therefore flips on *changes* in the gradient's direction/magnitude regime — it becomes a genuine correction channel tracking what the backbone's evidence is drifting toward, instead of a delayed copy of the backbone's own stream. Flip thresholds stay V=32 for both; arbitration unchanged.
- **train.py:** new flag `--t2-innov` on Layered (EMA buffer + second gate inside `step()`; c2's increment source is the only change).
- **mode:** process
- **prediction:** -0.02..-0.06 at trial scale; -0.00..-0.02 at probe scale. Reasoning: the half-control showed two components fed one stream earn nothing at equal size/steps (gap 0.0020) — this entry is the direct test of *why*: if the null was an information-bandwidth null (identical inputs), an independent second channel is the fix the null itself points to; if F-003 also ties plain, the levels question is closed for a deeper reason and that is a finding worth its probe.
- **status:** queued
```mill
id: F-003
mode: process
run: --arm layered_half --rope --t2-innov
```

### F-004 · SPRT thresholds: per-weight V from the vote stream's own consistency
- **source:** first-principles derivation — sequential analysis (Wald's SPRT): a counter accumulating ±1 votes is a random walk whose log-likelihood ratio after net count c and total votes n is c · log(p/(1−p)), where p is the weight's probability of a + vote. A *constant evidence standard* therefore means a constant threshold in LLR units, which means the vote-count threshold must scale as V_i ∝ 1 / log(p_i/(1−p_i)) — a single global V=32 holds consistent weights (p near 0 or 1) and coin-flip weights (p≈0.5) to wildly different evidence standards, over-waiting on the former and under-waiting on the latter.
- **mechanism:** each weight tracks its own vote consistency online (counts of + and − strong votes since last flip, two int16s or one fp ratio). Its personal threshold is V_i = clip(round(A / |log(p̂/(1−p̂))|), 8, 96), with A set so a p̂=0.75 weight gets V_i=32 (champion-equivalent at that consistency). p̂ is Laplace-smoothed and frozen for the first 16 votes after a flip (insufficient data → V_i=32). Distinct from per-layer flip-rate V (MILL-207/208: feedback on a *rate*, per layer), thrash tax (A-008: threshold from *flip count*), and depth/role V priors (A-025/026/029: fixed by position, not measured per weight).
- **train.py:** new flag `--sprt-v` on Layered (per-weight threshold array replacing the scalar `self.votes` in the flip test; clamp stays at the personal threshold).
- **mode:** process
- **prediction:** -0.02..-0.05 at trial scale; ~0 at probe (p̂ estimates are meaningless for the first flips; expect champion-identical behaviour until mid-run). Reasoning: the weights with p̂ far from 0.5 are the majority of eventual flips, and they currently wait for 32 net votes when SPRT says ~10–16 carry the same evidence — they flip late or, within a ~160-step run, never. Faster correct flips early compound through every later gradient.
- **status:** queued
```mill
id: F-004
mode: process
run: --arm layered_half --rope --sprt-v
```

### F-005 · State-stratified gate: the median is computed within each ternary state
- **source:** first-principles derivation — the gradient distribution is *conditioned on the weight's current state*: a weight at 0 and a weight at +1 have systematically different |g| distributions (their loss derivatives differ by construction of the forward pass). A single layer-wide median therefore does not select "the stronger half of evidence" — it selects a state-biased subset, silently giving whichever state group has larger typical |g| a majority of all votes, every step, in every layer.
- **mechanism:** the strong/weak partition is computed separately within each installed-state group of the layer (for layered: within each installed level −2..+2; groups with <64 members fall back to the layer median). Every state group contributes its own stronger half, so each state's weights receive votes at the same *rate* and are selected by within-group strength. Gate quantile stays q=0.5 inside each group. Distinct from per-row gate (A-002: stratifies by output neuron) and per-layer V (stratifies the threshold, not the gate).
- **train.py:** new flag `--gate-scope state` on Layered (alongside `--gate-q`; grouped quantile inside `step()`).
- **mode:** process
- **prediction:** -0.01..-0.04 at both probe and trial scale (the bias, if real, acts from step 0 — this is one of the few entries whose probe reading is meaningful). Reasoning: if the state groups' |g| medians differ by even 20%, the pooled gate misallocates roughly a tenth of all votes toward the already-dominant state; the probe also returns the diagnostic itself (per-state median ratios), which prices the bias even if the loss is flat.
- **status:** queued
```mill
id: F-005
mode: process
run: --arm layered_half --rope --gate-q 0.5 --gate-scope state
```

### F-006 · Canonicalization of the layered code (degeneracy removal)
- **source:** first-principles derivation — the layered encoding is many-to-one: installed value v = t1 + t2 with t1,t2 ∈ {−1,0,+1} has redundant representations (e.g. +1 = (1,0) = (0,1); 0 = (0,0) = (1,−1) = (−1,1)). The counter dynamics wander this degenerate fibre freely: components can swap or cancel (t1 up while t2 down) while the installed value — the only thing the loss sees — does not move. Those are wasted flips and wasted counter motion in a representation space larger than the function space.
- **mechanism:** every 32 steps, each weight's component pair is rewritten to the canonical representative of its installed value — t1 = sign(v)·min(|v|,1), t2 = v − t1 — *without changing any installed value* (forward output is bit-identical across the rewrite). Counters are remapped with it: the canonical backbone component keeps the sum c1+c2 clipped to ±V, the correction component's counter restarts at 0. Distinct from comp-reset (A-020: resets a sibling counter *on a flip*; this is a scheduled, value-preserving reparameterization) and from all flip-arbitration rules (which govern crossings, not representations).
- **train.py:** new flag `--canon 32` on Layered (periodic reparameterization pass in the training loop / `step()`).
- **mode:** process
- **prediction:** -0.01..-0.03 at trial scale; ~0 at probe (one or two canonicalizations only). Reasoning: cancellation pairs (1,−1) sitting at installed 0 are pure churn capacity — they hold two live counters that can burn flips returning to the same function; canonical form concentrates all evidence for a value into one counter, so subsequent flips express real function changes. Downside is bounded: the rewrite provably cannot change the function, only the dynamics.
- **status:** queued
```mill
id: F-006
mode: process
run: --arm layered_half --rope --canon 32
```

### F-007 · Counter-confidence install: the counter modulates the forward magnitude
- **source:** first-principles derivation — the counter is a sufficient statistic for the weight's recent gradient history (it is literally the integrated evidence), yet the forward pass reads only the ternary state and discards the counter entirely. Two weights both at +1, one at c=+31 (about to flip up) and one at c=−31 (about to flip down), present *identical* values to the network despite opposite, near-certain futures. That is information the model computed and then refused to use.
- **mechanism:** the installed value becomes t · γ_layer · (1 + κ · c/(V · γ̂)) applied per component — concretely, effective weight = γ · (t + κ·c/V) with κ=0.25: the counter contributes a bounded continuous correction of at most ±25% of one level, so a weight leans toward its impending flip before it commits. At a flip the counter resets, so the correction is continuous through the flip boundary (the pre-flip lean and the post-flip state agree to within the κ band). Serving strips the correction (export = plain ternary at the final states); it is a training-time representation only, charged as such. Distinct from all scale-granularity entries (MILL-107/108/701–703: scales from weight *magnitudes*) and learn-scale (MILL-1013): here the modulation source is the *counter*, a quantity no pooled entry reads in the forward pass.
- **train.py:** new flag `--conf-install 0.25` on Layered (install() adds the counter term; eval/export path unchanged).
- **mode:** process
- **prediction:** -0.02..-0.05 at probe and trial scale (acts from the first counter movement, unlike most entries here). Reasoning: this softens the mechanism's core discontinuity — the installed function currently jumps by a full level on flip day and is frozen between flips; a κ-lean makes the effective function move quasi-continuously with evidence, recovering part of what STE's latent weights provide, at zero extra state (the counter already exists). Risk: forward now depends on a noisy statistic; κ=0.25 bounds the noise injection to a quarter-level.
- **status:** queued
```mill
id: F-007
mode: process
run: --arm layered_half --rope --conf-install 0.25
```

### F-008 · Row-coincidence flip cap: at most one flip per output row per step
- **source:** first-principles derivation — perturbation bound for one neuron: a flip in row j changes that neuron's output by γ·|x_i| for the flipped input i. If k weights in the same row flip on the same step, the neuron's output jumps by up to k·γ·max|x| in one step — an unbounded, uncontrolled perturbation whose size is set by coincidence, not by evidence. The counter system prices each flip independently; the *function* prices their sum per row.
- **mechanism:** per step, within each output row of each matrix, at most 1 pending flip is applied — the one with the largest |counter overshoot|; other crossing counters in that row keep their (clamped) counts and remain eligible next step. Distinct from the global flip budget (A-017: caps the *total* count, indifferent to where flips land) and block staggering (A-018: rotates by block): this caps *spatial coincidence at the unit whose output actually sums the flips*.
- **train.py:** new flag `--row-flip-cap 1` on Layered (row-wise top-1 selection in the flip application inside `step()`).
- **mode:** process
- **prediction:** -0.01..-0.03 at trial scale; ~0 at probe (coincidences are rare in ~25 steps). Reasoning: simultaneous same-row crossings are most likely exactly when a batch is atypical (correlated gradients push a whole row), i.e. precisely the flips most likely to be noise acting in concert; deferring them by one step costs the true flips almost nothing (their counters persist) and converts a k-fold output jump into k single steps the rest of the network can track.
- **status:** queued
```mill
id: F-008
mode: process
run: --arm layered_half --rope --row-flip-cap 1
```

### F-009 · Common-mode rejection: subtract the layer's mean vote before counting
- **source:** first-principles derivation — each step's gradient is computed on ONE batch, so it decomposes as g = ḡ_signal + b_batch + noise, where b_batch is a component shared across many weights of a layer (the batch's idiosyncratic pull: an unusual window moves whole layers coherently). Independent counters integrate b_batch as if it were per-weight signal; over a run, batch common-mode is a random walk added to every counter in the layer simultaneously — correlated counter motion with no per-weight information in it.
- **mechanism:** before counting, the vote stream is centred per layer: instead of counting sign(g_i) for gated weights, count sign(g_i − median_layer(g)) — i.e. a weight votes up only if its gradient pulls up *relative to its layer's typical pull this step*. The gate (on |g|) is unchanged; only the sign reference moves from 0 to the layer median. Distinct from gradient whitening (MILL-232: second-moment normalization in a rotated basis) — this removes the first moment only, in the original basis, at zero extra state.
- **train.py:** new flag `--vote-center` on Layered (median subtraction in `step()` before the sign is taken).
- **mode:** process
- **prediction:** -0.01..-0.04 at probe and trial scale. Reasoning: at batch 32 the batch term is large (it is the dominant correlated noise source in SGD), and the counter — an integrator with a ~32-step memory — is exactly the device most vulnerable to integrating a correlated component: uncorrelated noise averages out over the climb to V, common-mode noise does not, because it pushes the same direction for many consecutive steps whenever similar windows recur.
- **status:** queued
```mill
id: F-009
mode: process
run: --arm layered_half --rope --vote-center
```

### F-010 · Cross-layer staleness discount: downstream counters pay for upstream flips
- **source:** first-principles derivation — counters assume a stationary target: counter c in block 2 integrates gradients that were computed *through* block 1's weights. Every block-1 flip changes the function block 2's gradients describe, so a fraction of block 2's banked evidence refers to a network that no longer exists. The staleness of a downstream counter is, to first order, proportional to the upstream flip volume since its evidence was gathered — a quantity the trainer already measures (flip share) and currently ignores across layers.
- **mechanism:** after each step, if block 1's flip share that step exceeds 0.2% of its weights, block 2's counters are discounted once: c ← round(0.75 · c) for both components (a 25% evidence write-down, event-driven, not periodic). Block 1's own counters are never discounted by its own flips (its evidence is about its own inputs, which did not change). At the champion's 2-block depth this is the complete rule; it generalizes to "each block discounts by the product of upstream flip events." Distinct from leak (MILL-209–213: time-driven decay regardless of cause) and comp-reset (A-020: same-weight sibling): this is *cause*-driven decay, priced by measured upstream change.
- **train.py:** new flag `--xstale 0.75` on Layered (cross-block hook after the flip application in `step()`).
- **mode:** process
- **prediction:** -0.01..-0.03 at trial scale; ~0 at probe (flip share rarely crosses the trigger in the first steps). Reasoning: the champion's mean flip share is ~0.11%/step, so the trigger fires on the high-flip tail — exactly the steps after which downstream evidence is stalest. If it never fires at trial either, the entry retires itself with a measurement (cross-layer staleness is negligible at this depth), which is also worth owning.
- **status:** queued
```mill
id: F-010
mode: process
run: --arm layered_half --rope --xstale 0.75
```

### F-011 · Dithered gate: randomized median threshold (stochastic inclusion)
- **source:** first-principles derivation — a deterministic threshold applied to a continuous statistic creates a systematic exclusion set: a weight whose |g| sits permanently just below the layer median casts *zero* votes for the entire run, while a weight ε above it votes every step — an infinite evidence ratio for an ε difference in information. Quantization theory's standard fix is dithering: adding noise before a threshold converts a hard exclusion into an inclusion *probability* that is continuous (in fact linear) in the underlying statistic, making the expected vote an unbiased, graded function of |g|.
- **mechanism:** each step, each weight's gate test uses a jittered threshold: it votes iff |g_i| > median_layer · u_i, with u_i ~ Uniform(0.7, 1.3) drawn fresh per weight per step. Weights at the median vote ~50% of steps; at 1.3× median, always; at 0.7×, never. Increments stay exactly ±1 (this is not magnitude weighting) and the strong-side cliff is untouched in form — what changes is that the cliff's *position* is randomized. Distinct from the soft gate (A-001: deterministic continuous increment *above* the median; below-median weights still contribute exactly 0 forever) and from F-002 (which gives the weak half its own slow counter rather than probabilistic admission to the fast one).
- **train.py:** new flag `--gate-dither 0.3` on Layered (per-step uniform draw in the gate test inside `step()`; own RNG stream per seed-discipline).
- **mode:** process
- **prediction:** -0.01..-0.03 at probe and trial scale. Reasoning: the excluded-just-below-median population is by construction the largest group of near-miss weights in every layer; even a fractional admission rate gives their counters a real (if slower) climb, and stochastic rounding is *unbiased* — unlike the hard gate, it introduces no systematic preference beyond |g| itself. Expected effect is smaller than F-002's if the weak half's signal is mostly long-horizon; the pair brackets the two ways to recover the same discarded information.
- **status:** queued
```mill
id: F-011
mode: process
run: --arm layered_half --rope --gate-dither 0.3
```

### F-012 · Predictive threshold crossing: flip on the counter's extrapolated value
- **source:** first-principles derivation — the counter is an integrator; its recent slope (mean vote over the last k steps) is an independent statistic from its level, and first-passage theory says the optimal decision uses both: a counter at +24 rising at +0.8/step will cross +32 in ~10 steps with high probability, while a counter at +24 falling will not. The champion's rule reads the level only, so it treats these identically — it waits for certainty in cases where the trajectory already carries it, and the wait costs the remaining run length (at ~160 steps, a 10-step delay is 6% of the run, per flip).
- **mechanism:** maintain a per-weight short-window vote mean m (EMA of the vote stream, β=0.8, fp state charged). The flip test becomes: flip when c + τ·m ≥ V (for the + direction; mirrored for −), with τ=8 steps of lookahead. The counter itself, the clamp, and the reset are unchanged — only the crossing test is trend-adjusted (a proportional-derivative rule on top of the integral state). Distinct from EMA evidence (A-011: replaces the vote *direction* with sign(EMA of g)) and from leak (decays the level): here the level is untouched and the EMA is used only to *extrapolate* it.
- **train.py:** new flag `--pred-flip 8` on Layered (EMA buffer + modified flip test in `step()`).
- **mode:** process
- **prediction:** -0.01..-0.03 at trial scale; ~0..-0.01 at probe. Reasoning: the gain is bounded by (flips whose crossing is predictable) × (steps saved) — both modest — but the failure mode is also bounded: a mispredicted flip is one whose counter was within τ·m of threshold on a genuine trend, i.e. a flip that was likely within ~8 steps anyway. The asymmetry (bounded downside, compounding upside from earlier correct structure) is the argument.
- **status:** queued
```mill
id: F-012
mode: process
run: --arm layered_half --rope --pred-flip 8
```

### F-013 · Position-information-weighted votes: early positions know less, so they vote less
- **source:** first-principles derivation — causal information content: the gradient contribution of position t is computed from a context of t tokens, so per-position gradient noise scales roughly as 1/√t while the vote path sums all 256 positions' contributions into one gradient and takes one sign — treating position 2 (context: 2 tokens) as an equal witness to position 250. The vote is the trainer component most sensitive to witness quality, because it keeps only the sign of the sum.
- **mechanism:** in the vote path only, the loss is reweighted per position by w_t = log2(t+2)/log2(258) (position 0 ≈ 0.125, position 255 = 1.0) before the backward that feeds the counters; the AdamW parts (embeddings, norms, scales) continue to train on the plain, unweighted loss in a second backward (cost: one extra backward per step, charged honestly — or equivalently a gradient-hook split). Distinct from loss-weighted token votes (A-013 in stream A: weights by the token's *loss value*, a difficulty signal) — this weights by *context size*, a pure information quantity that is independent of the model's current errors and cannot chase its biases.
- **train.py:** new flag `--posw-vote` on Layered (per-position loss weights applied to the vote-path gradient only, in the training loop).
- **mode:** process
- **prediction:** -0.01..-0.03 at probe and trial scale, with the extra-backward cost charged: at equal *minutes* the probe may read flat while winning at equal *steps* — the trial must report both, and adoption requires the per-minute reading to win too. Reasoning: the first ~32 positions are ~12% of every window's vote evidence at the lowest witness quality; down-weighting them raises the SNR of every counter in the network by a few percent, which compounds over the ~32-vote climb to every flip.
- **status:** queued
```mill
id: F-013
mode: process
run: --arm layered_half --rope --posw-vote
```

### F-014 · Dithered per-weight thresholds: fixed random V_i ∈ [24, 40]
- **source:** first-principles derivation — first-passage synchronization: with a single global V, weights whose evidence streams are similar cross threshold in *correlated bursts* (the same good/bad batch moves thousands of counters in lockstep), so flip volume per step is far more variable than independent counters would produce — the flip-rate time series inherits the batch stream's variance. Drawing each weight's threshold once, uniformly from [24, 40] (mean 32 = champion), decorrelates crossing times without changing the mean evidence standard: a quantizer-dithering argument applied to the threshold instead of the signal.
- **mechanism:** at init, each weight draws V_i ~ Uniform{24..40} (seeded, fixed for the run); its clamp and flip test use V_i. Nothing else changes. Distinct from per-head temperature spread (A-029: four structured values assigned by head) and per-layer adaptive V (feedback-driven): this is unstructured, per-weight, open-loop heterogeneity whose only job is desynchronization — the control that tells the lab whether *any* V diversity helps, before it invests in principled diversity (cf. F-004).
- **train.py:** new flag `--v-dither 24,40` on Layered (per-weight threshold array replacing the scalar in `step()`; shares plumbing with F-004 but no online estimation).
- **mode:** process
- **prediction:** -0.005..-0.02 at probe and trial scale — the smallest expected effect in this file, included because it is the cheapest possible test of threshold diversity and its result disciplines F-004's interpretation (if random diversity ≈ SPRT diversity, the SPRT estimation machinery earns nothing; if SPRT >> dither, per-weight *information* is the active ingredient). Reasoning: burst decorrelation smooths the structure's effective learning rate across steps, which should help most in the high-flip early phase.
- **status:** queued
```mill
id: F-014
mode: process
run: --arm layered_half --rope --v-dither 24,40
```

### F-015 · Warm-started counters: pre-roll evidence at init
- **source:** first-principles derivation — hitting time from a cold start: a counter starting at 0 under drift μ needs an expected V/μ steps to its first flip; at V=32 and the modest drifts typical of real weights, that is a large fraction of a ~160-step run spent with *no structure learning at all* from that weight — yet the information that determines the drift's sign is available at initialization, in the gradient statistics at init, before any flip is allowed to fire. Starting counters at 0 discards a measurable head start that costs only forward/backward passes, not training steps.
- **mechanism:** before step 0, run 32 no-update passes over training windows (offsets() draws, held-safe) at the init model, accumulating each weight's gated votes exactly as `step()` would, then set c_i = clip(accumulated, −16, +16) — at most half of V, so no weight can flip on pre-roll evidence alone; it can only start halfway up the climb it was already going to make. The ternary state is untouched (this is not a state init). Distinct from vote warmup (A-023: delays flips while counters accumulate *live* from 0 — the run still pays the climb in training steps) and from the init entries (A-113/A-114: change the ternary *state*, counters still 0).
- **train.py:** new flag `--counter-warm 32` on Layered/Direct (pre-roll loop in the runner before training; 32 passes charged to wall-clock, ~32 step-equivalents, stated in the record).
- **mode:** process
- **prediction:** -0.01..-0.03 at probe scale, -0.00..-0.02 at trial scale (the head start is a fixed step saving, worth relatively more in a 25-step probe than a 160-step trial — the honest shape of this effect). Reasoning: weights whose init-gradient consensus is strong are disproportionately the weights whose first flip is correct; advancing them ~16 votes converts dead early steps into structure formation, and the ±16 cap guarantees at least 16 live votes still gate every first flip. If init gradients are uninformative about later drift, the pre-roll is pure noise bounded by the same cap, and the probe will show it.
- **status:** queued
```mill
id: F-015
mode: process
run: --arm layered_half --rope --counter-warm 32
```

---

*End of lens 1. 15 entries (F-001…F-015), all first-principles derivations from the vote
mechanism's mathematics: bounded state space (F-001), discarded-sample information
(F-002, F-011), channel bandwidth of identical streams (F-003), sequential-evidence
units (F-004, F-014), state-conditioned gradient distributions (F-005), encoding
degeneracy (F-006), the counter as a discarded sufficient statistic (F-007),
per-neuron perturbation bounds (F-008), correlated batch noise in an integrator
(F-009), non-stationarity across layers (F-010), first-passage prediction (F-012),
causal witness quality (F-013), and cold-start hitting time (F-015).*

## Lens 2 — Cross-domain transfer (was XD-###)

### F-016 · Anti-windup: conditional integration at the saturated boundary ★
- **source:** control theory — anti-windup by conditional integration (Åström & Wittenmark): when the actuator is saturated, the integrator stops accumulating in the saturating direction.
- **mechanism:** In `Layered.step` today a component at its boundary (t=+1, vote pushing +1-ward, or t=−1 pushing −1-ward) cannot flip — `want != t` fails — yet its counter keeps integrating and sits clamped at ±V. That is integral windup: when the gradient later reverses, the weight must first unwind up to 32 banked votes before any reverse progress registers, so saturated weights are systematically the last to correct. Anti-windup rule: if the flip a vote argues for is a boundary no-op for that component, the vote is NOT integrated into that component's counter this step (the other component integrates normally). Counters therefore never hold evidence for a move that is physically impossible; reversal latency at saturated weights drops from ~V steps to ~0.
- **train.py:** new flag `--anti-windup` on `Layered` (and `Direct`): in the vote loop, mask the increment per component — `inc = vote * ((t + vote.clamp(-1,1)).clamp(-1,1) != t or sign(c) != sign(vote))` in effect: integrate freely when the vote reduces |c| or argues a legal move; skip only same-direction votes while at the boundary. No new state, no new hyperparameter.
- **mode:** process
- **prediction:** −0.01..−0.04. The gain concentrates in weights that reach ±1 early and later need to come back — exactly the population the anneal disaster showed is mishandled. Diagnostic logged at trial: mean counter value among boundary-blocked weights (should sit near 0 under this arm vs pinned at ±32 on the chassis).
- **status:** queued
```mill
id: F-016
mode: process
run: --arm layered_half --rope --anti-windup
```

### F-017 · TPDF dither before the median gate ★
- **source:** signal processing — dither (Lipshitz & Vanderkooy): triangular-probability-density noise added before a coarse quantizer to decorrelate quantization error from the signal and destroy limit cycles.
- **mechanism:** The vote path is two cascaded 1-bit quantizers — the median gate (pass/fail) and `sign(g)` — fed by a deterministic gradient stream. Undithered, weights whose |g| sits just under the layer median are starved deterministically and gradient patterns near the threshold lock into limit cycles (the same weights vote / don't vote in a fixed pattern). Add TPDF noise `d = (u1 − u2) · 0.5 · median|g|` (u1,u2 ~ U(0,1), per weight, per step) to g before BOTH the gate comparison and the sign: `vote = −sign(g + d) · 𝟙[|g + d| ≥ median|g|]`. Sub-threshold weights now vote with probability proportional to their distance below the median; supra-threshold weights occasionally abstain. Counters, V, clamp unchanged; zero extra state (noise is ephemeral).
- **train.py:** new flag `--dither 0.5` on `Layered`/`Direct` (argument = dither amplitude in units of the layer median |g|; TPDF from two uniform draws inside `step`).
- **mode:** process
- **prediction:** −0.01..−0.03, plus a measurable side effect: the flip-count distribution across weights should flatten (fewer never-vote weights). Distinct from A-024 (ε-greedy flips act AFTER the counter, at random, ignoring evidence) and A-015 (stochastic flip at crossing): dither acts BEFORE quantization, is evidence-shaped, and never flips anything by itself.
- **status:** queued
```mill
id: F-017
mode: process
run: --arm layered_half --rope --dither 0.5
```

### F-018 · Byzantine quorum: 3-of-4 sub-electorates must agree ★
- **source:** distributed consensus — Byzantine fault tolerance (PBFT, Castro & Liskov): with f faulty voters, a decision needs 2f+1 of 3f+1 independent votes; here f=1, so 3 of 4.
- **mechanism:** Today one batch of 32 casts one vote per weight: a single atypical batch is a Byzantine voter with full voting power. Split the batch into 4 sub-electorates of 8 windows; run the backward per sub-batch and take each sub-batch's gated sign vote independently. The counter increments by the MAJORITY sub-vote only when at least 3 of 4 sub-electorates agree on its sign; on a 2–2 split or 2–1 plurality the weight abstains (counter unchanged). Correlated noise inside one sub-batch can no longer move any counter, and the vote that does land carries a quorum certificate: it was the majority view of independent samples, not one draw.
- **train.py:** new flag `--byz 4:3` on `Layered`: main loop splits each batch into 4×8, calls a sub-step backward per slice accumulating per-slice votes, applies the 3-of-4 rule, then one AdamW step on the summed gradient. Cost charged honestly: 4 backward passes per step on ¼-batches (≈ same FLOPs, worse efficiency — expect ~0.8× steps/minute; judged per step AND per minute at trial).
- **mode:** process
- **prediction:** −0.01..−0.05 per step; per minute it must overcome its own overhead. Distinct from A-003 (accumulates 4 micro-batches into ONE summed vote — a single bad micro-batch still contributes its sign mass; no agreement test exists) and A-109 (two counters over alternating batches, both must fill — a time split, not a simultaneous quorum).
- **status:** queued
```mill
id: F-018
mode: process
run: --arm layered_half --rope --byz 4:3
```

### F-019 · Sortition: a randomly drawn jury votes each step
- **source:** voting theory / Athenian democracy — sortition: office-holders and juries chosen by lot each term, so no fixed faction can capture the process and every citizen serves in expectation equally.
- **mechanism:** Each step, for each layer, draw a fresh random 25% subset of weights (without replacement, RNG independent of the batch stream). Only jury members integrate this step's vote and only jury members may flip; non-members' counters and states are frozen for that step. Over 4 steps every weight serves once in expectation, but no weight can be stampeded by a short correlated run of batches — between its jury terms, contrary fashions pass it by — and simultaneous-flip interference is cut 4× because at most 25% of weights are ever eligible on the same step. Unlike a rotation, the lot is redrawn independently each step: eligibility is unpredictable, so no periodic data pattern can synchronise with a weight's voting days.
- **train.py:** new flag `--sortition 0.25` on `Layered`/`Direct`: per-step Bernoulli/fixed-size mask in `step`, applied to the increment and to `go1/go2`. No extra persistent state (mask is per-step).
- **mode:** process
- **prediction:** −0.01..+0.02 — genuinely two-sided: it is a variance/capture trade, slowing each weight's evidence rate 4× while cleaning it. The probe's job is pricing that trade. Distinct from A-018 (block-staggered flips: deterministic rotation at BLOCK level, flips only — votes still accumulate everywhere every step) and A-016 (batched flips: everyone votes, flips deferred).
- **status:** queued
```mill
id: F-019
mode: process
run: --arm layered_half --rope --sortition 0.25
```

### F-020 · Quadratic voting: votes are bought from a per-step credit budget
- **source:** economics / social choice — quadratic voting (Lalley & Weyl): casting intensity x of influence costs x² credits from a fixed budget, so broad weak preferences are priced out and concentrated conviction is what gets expressed.
- **mechanism:** Per layer per step, define intensity r = |g| / median|g| for each strong-half weight. Admitting a weight's vote costs r² credits. Votes are admitted in descending r order until the step's credit budget B is spent, where B = 0.25 × Σ r² over the strong half (so the budget is a fixed share of the step's total would-be cost, self-calibrating across layers and training phases). Admitted weights cast the usual ±1 vote; the rest abstain. Effect: on steps where gradient mass is concentrated (a few weights really matter), almost all strong weights still vote — their rivals are cheap. On diffuse steps (mass spread thin, r ≈ 1 everywhere), only ~25% vote: the mechanism refuses to spend the network's flip budget on steps where no weight stands out. The median gate today treats both regimes identically (top half always votes at flat cost).
- **train.py:** new flag `--quad 0.25` on `Layered`/`Direct`: inside `step`, per layer compute r, sort descending (one sort per layer per step, charged), admit by cumulative r² ≤ 0.25·Σr², zero the non-admitted votes before the counter update.
- **mode:** process
- **prediction:** −0.01..−0.04. Distinct from MILL-601..606 gate-q (admits a fixed FRACTION at flat cost), A-001 soft gate (scales increments continuously, no budget, everyone above median still counts), and MILL-201..203 calibrated magnitude votes (increment SIZE carries intensity; here increments stay ±1 and intensity buys ADMISSION under a hard budget).
- **status:** queued
```mill
id: F-020
mode: process
run: --arm layered_half --rope --quad 0.25
```

### F-021 · Veto player: the output row can veto a flip
- **source:** political science — veto-player theory (Tsebelis): a change from the status quo requires the assent of every veto player; any one of them can block, and blocking preserves the status quo without erasing the proposal.
- **mechanism:** A weight at threshold flips only if its output ROW (its veto player) does not dissent: compute the row's mean vote this step over all weights in that row of the matrix; if sign(row-mean vote) is non-zero and opposite to the flipping weight's counter sign, the flip is vetoed for this step. The counter is NOT reset — the proposal stays on the table and can pass on a later step when the row no longer dissents (veto ≠ the sign-agree flip rule, which arbitrates between two components at one weight; the row is a different constituency with its own aggregate interest: a lone weight flipping against the direction its whole neuron is moving usually means its evidence is idiosyncratic noise, while a weight flipping WITH its row rides a coherent feature change).
- **train.py:** new flag `--row-veto` on `Layered`: in `step`, after computing `vote`, reduce it per output row (mean over dim −1); `go1/go2` additionally require `row_sign == 0 or row_sign == c.sign()`. No new state.
- **mode:** process
- **prediction:** −0.01..−0.03, with flip share down ~10–30% (vetoed flips are logged). If flip share collapses instead, the row signal is too coarse at width 192 and the entry dies on its own log.
- **status:** queued
```mill
id: F-021
mode: process
run: --arm layered_half --rope --row-veto
```

### F-022 · Benna–Fusi cascade: a fast counter drives a slow counter
- **source:** neuroscience — the Benna–Fusi cascade model of synaptic memory (Benna & Fusi, 2016): a chain of coupled variables with progressively slower timescales gives power-law memory lifetimes — fast variables absorb new evidence, only evidence that persists propagates down the chain and becomes durable.
- **mechanism:** Replace the plain chassis's single counter per weight with a serial cascade of two counters that are NOT both installed (this is not layered t1+t2, whose components sum into the weight). Fast counter cf (clamp ±8) receives every vote. Whenever cf saturates at ±8, it transfers one unit into the slow counter cs (cs += sign(cf), cf -= sign(cf)·8 — a carry INSIDE the cascade, between timescales, not the closed overshoot carry on a flip). The ternary weight flips only when |cs| ≥ 4, i.e. after ~32 net votes have each survived the fast stage's saturation test repeatedly; cs then resets. One-off bursts die in cf; only evidence that keeps arriving across many steps ever reaches cs. Effective memory lifetime scales ~quadratically in the stage thresholds instead of linearly in V.
- **train.py:** new trainer path `--cascade 8:4` on the `Direct` chassis (chassis-changing entry: `--arm plain_half --rope --cascade 8:4`): two int8 counters per weight (2 B/weight vs plain's 1 B — charged), transfer rule in `step`, flip test on cs only.
- **mode:** process
- **prediction:** −0.02..+0.02 at probe horizon (the cascade's advantage is a long-horizon property — a flat probe does NOT kill it; verdict at full trial). Distinct from fractional leak MILL-209..211 (a single counter forgetting exponentially — the cascade forgets as a power law and never decays cs at all) and from A-006's race (parallel up/down counters with a total-count condition; no timescale coupling).
- **status:** queued
```mill
id: F-022
mode: process
run: --arm plain_half --rope --cascade 8:4
```

### F-023 · Synaptic consolidation: importance raises a weight's personal V
- **source:** neuroscience / continual learning — synaptic intelligence & EWC (Zenke et al. 2017; Kirkpatrick et al. 2017): synapses that were important for past performance are consolidated — made harder to change — in proportion to an online importance integral.
- **mechanism:** Each weight accumulates an importance ω = EMA(β=0.99) of g² (the online Fisher proxy). Its personal flip threshold is V_i = V · (1 + ω_i / median(ω)) clipped to [32, 96]: the median weight keeps the champion's threshold, a weight carrying 2× median gradient energy needs up to 3× the evidence to flip. Important synapses consolidate; unimportant ones stay plastic at the proven setting. The asymmetry is the point no existing entry has: thrash tax raises V from a weight's own FLIP history (behaviour), consolidation raises it from its gradient-energy history (function) — a weight can be heavily consolidated without ever having flipped, and a chronic flipper with tiny gradients stays cheap to flip.
- **train.py:** new flag `--consol-v` on `Layered`: per-weight fp32 ω (4 B/weight, charged) + int16 counters (clamp per-weight at ±V_i, max 96); flip test `|c| ≥ V_i` per weight in `step`.
- **mode:** process
- **prediction:** −0.01..−0.04. Watch the zero-fraction: consolidation should preferentially protect the ±1 population that carries the features, letting the zero population keep reorganising.
- **status:** queued
```mill
id: F-023
mode: process
run: --arm layered_half --rope --consol-v
```

### F-024 · Homeostatic scaling: per-row scales servoed to an activity set-point
- **source:** neuroscience — homeostatic synaptic scaling (Turrigiano): each neuron multiplicatively rescales all its synapses up or down to hold its firing rate at a set-point, on a slow timescale, independent of the Hebbian signal.
- **mechanism:** Today each BitLinear layer has ONE learned `log_scale`, trained by the hand-set gradient (g·t)·scale. Replace it with per-OUTPUT-ROW scales that are not gradient-trained at all: a forward hook keeps an EMA of each row's output RMS; every 10 steps each row's install scale is multiplied by exp(η·(log RMS_target − log RMS_row)), with RMS_target = the layer's median row RMS and η=0.05. Rows that shout get turned down, rows that whisper get turned up, and the layer's total scale budget is conserved (median-anchored). The vote counters then compete inside a layer whose rows are activity-equalised, instead of inside one where a few high-scale rows dominate every downstream gate statistic.
- **train.py:** new flag `--homeo 0.05` on `Layered`: per-row scale buffer in `install()` (fp32, dim floats per layer — negligible bytes), RMS EMA hook on each BitLinear forward, servo update every 10 steps replacing the `log_scale` gradient path for vote arms.
- **mode:** process
- **prediction:** −0.01..−0.05; the most architectural entry in this file. Distinct from MILL-107 per-channel scales (a static absmean STATISTIC at finer granularity — no feedback, no set-point, no time dynamics) and MILL-1013 learn-scale (gradient-learned): homeostatic scales are servoed to measured activity by a rule that never sees the loss.
- **status:** queued
```mill
id: F-024
mode: process
run: --arm layered_half --rope --homeo 0.05
```

### F-025 · Supermajority decay: a stalled counter's threshold erodes
- **source:** voting theory / DAO governance — decaying supermajority (quorum decay): a proposal that cannot reach its supermajority sees the required threshold decay over time, so persistent minorities cannot filibuster a persistent majority forever.
- **mechanism:** Each counter carries an age: steps since it last changed sign or flipped. A counter that has held the same sign for 50 steps without reaching V is stalled evidence — a durable majority that the fixed supermajority keeps disenfranchising. Its personal threshold erodes by 1 per further 50 stalled steps, floored at V/2 = 16: V_eff = max(16, 32 − floor((age − 50)/50)). Age resets on flip or sign change. The floor and the age condition are what separate this from the closed 8→64 anneal: nothing here is ever hot for YOUNG evidence (the poison that killed the anneal arm) — erosion is earned only by evidence that has already survived 50+ steps pointing one way, and 16 is far above the poisoned 8.
- **train.py:** new flag `--stall-decay 50:16` on `Layered`: per-component int16 age tensor (2 B/weight, charged), per-weight V_eff in the flip test; counters clamp at ±32 as now (clamp is not the threshold).
- **mode:** process
- **prediction:** −0.01..−0.03. Diagnostic: the counter-age histogram at end of run — if almost no counters ever stall past 50 steps, the mechanism has no population to act on and the entry is void, not wrong. Distinct from MILL-204..206 global V schedules (time-based, identical for all weights regardless of their evidence history) and A-008 thrash tax (raises V after flips; this lowers it after stalls — opposite sign, opposite trigger).
- **status:** queued
```mill
id: F-025
mode: process
run: --arm layered_half --rope --stall-decay 50:16
```

### F-026 · Bid–ask spread: the flip threshold widens with vote-stream volatility
- **source:** economics — market microstructure (Glosten–Milgrom): a market maker quotes a bid–ask spread that widens with adverse-selection risk / volatility; you may trade, but crossing a wide spread costs more conviction.
- **mechanism:** Treat a flip as a trade: the counter must cross not V but V + spread/2 on either side, where the per-layer spread is quoted from the vote stream's own volatility: churn_t = fraction of strong votes whose sign disagrees with that weight's previous-step vote (the stream's realised volatility). spread = round(16 · EMA₀.₉₅(churn)), so V_eff ∈ [32, 48], recomputed per layer per step, and V_eff can only widen from the champion's 32, never narrow below it. In calm regimes (gradients pointing consistently) the spread collapses and trading is at champion cost; in churn regimes — where flips are most likely to be noise — the market charges more evidence. This is a volatility quote, not a rate controller: it does not target any flip rate, it prices the current disagreement.
- **train.py:** new flag `--spread 16` on `Layered`: per-layer churn EMA (one float per layer), per-layer integer V_eff used in both the clamp and the flip test each step. No per-weight state.
- **mode:** process
- **prediction:** −0.01..−0.03. Distinct from A-007 hysteresis (a STATIC asymmetry between the 0↔±1 boundaries, fixed at build time) and MILL-207/208 per-layer V (adapts V to hit a target flip RATE by feedback; the spread adapts to vote-stream VOLATILITY and has no target rate).
- **status:** queued
```mill
id: F-026
mode: process
run: --arm layered_half --rope --spread 16
```

### F-027 · Circuit breaker: a flip storm halts trading, not rationing
- **source:** economics — exchange circuit breakers (NYSE Rule 80B lineage): when movement in a session exceeds a threshold, trading HALTS for a cooling period; orders are not rationed, the market closes and reopens.
- **mechanism:** The runner tracks the trailing 100-step mean flip share (≈0.11% on this chassis). If a single step's flip share exceeds 3× that mean AND 0.5% absolute, a breaker trips: for the next 10 steps NO flips are applied anywhere (counters keep integrating and clamping normally, AdamW parts keep training), then trading reopens automatically. Rationale: a flip storm means the network just moved under its own gradient stream — the next several batches' gradients describe a network that no longer exists, and their flips compound the shock. A halt lets the continuous parts re-fit the new structure before more structure moves. Every trip is logged (step, share, trailing mean).
- **train.py:** new flag `--breaker 3:10` on `Layered`: breaker state (halt counter + trailing flip-share ring) in the trainer; `go1/go2` masked to false while halted. No per-weight state.
- **mode:** process
- **prediction:** −0.01..+0.02 — the honest prior is that storms are rare at 0.11% mean share, so the entry may simply never trip, which is itself the measurement (log `trips=0` retires it). Distinct from A-017 flip cap (rations flips WITHIN every step by overshoot ranking — the market never closes) and A-019 quarantine (per-weight, triggered by its own flip-flop, not by a market-wide event).
- **status:** queued
```mill
id: F-027
mode: process
run: --arm layered_half --rope --breaker 3:10
```

### F-028 · AGC gate: automatic gain control on admitted gradient mass
- **source:** signal processing — automatic gain control (receiver design): a feedback loop with fast attack and slow release holds the admitted signal LEVEL at a set-point by continuously adjusting gain, whatever the input level does.
- **mechanism:** The median gate fixes the admitted FRACTION at 50% of weights, but the admitted gradient MASS (Σ|g| over strong weights ÷ Σ|g| overall) swings freely as the gradient distribution changes shape over training. AGC instead holds admitted mass at a 0.60 set-point: each layer keeps a live gate quantile q_t (init 0.5); per step, measure admitted mass m_t; if m_t > 0.60, q_t rises with fast attack (+0.05/step, gain down — fewer, stronger voters); if m_t < 0.60, q_t falls with slow release (−0.005/step, gain up), q_t ∈ [0.2, 0.9]. The gate then uses q_t in place of the fixed 0.5 quantile. As gradients concentrate late in training (a few large, many small), the fixed gate admits ever more of the total mass through ever more marginal weights; AGC tightens admittance to keep the counter's diet constant in the units that matter — energy, not headcount.
- **train.py:** new flag `--agc 0.60` on `Layered`/`Direct`: per-layer q_t float + attack/release update inside `step`, replacing the hard-coded `median()` gate with a `quantile(q_t)` gate.
- **mode:** process
- **prediction:** −0.01..−0.03. Distinct from the MILL-601..606 gate-q grid (STATIC quantiles — each is one frozen gain setting; AGC is the loop that moves between them) and A-001 soft gate (continuous weighting at a fixed median; no feedback, no set-point).
- **status:** queued
```mill
id: F-028
mode: process
run: --arm layered_half --rope --agc 0.60
```

### F-029 · Gossip diffusion: counters average with their neighbours
- **source:** distributed consensus — gossip / epidemic averaging (Demers et al.; Kempe et al.): nodes repeatedly average their state with random neighbours and the whole system converges to the global mean without any coordinator, robust to node failure.
- **mechanism:** Every 10 steps, each counter diffuses toward its spatial neighbours in the weight matrix: c ← clamp(c + 0.25 · (mean of the 4-neighbour counters − c)), neighbours taken along both matrix axes with circular wrap, applied to c1 and c2 independently, with no flip test on diffused values (flips are still only ever caused by voted crossings on normal steps). Weight matrices are not spatially random — adjacent columns share input features, adjacent rows share output units, and the QKV projection packs q|k|v in row bands — so a weight whose evidence is strong but whose neighbours all lean the other way is probably reading a local artefact; diffusion lets coherent regional evidence reinforce and isolated counter spikes dissipate before they can spend a flip. It is the only entry that couples DIFFERENT weights' evidence.
- **train.py:** new flag `--gossip 0.25:10` on `Layered`: every 10 steps in `step`, a shift-and-average pass over each counter tensor (4 `roll` ops), then clamp to ±V. No persistent state.
- **mode:** process
- **prediction:** −0.02..+0.03 — the widest honest range in this file: the spatial-coherence prior is real for embeddings/QKV bands and weak for FFN matrices, and the per-layer read at trial will show which. Distinct from MILL-232 whitening (rotates the GRADIENT basis per layer; counters stay independent) — nothing pooled couples counters across weights at all.
- **status:** queued
```mill
id: F-029
mode: process
run: --arm layered_half --rope --gossip 0.25:10
```

### F-030 · PID flip test: proportional and derivative terms join the integral
- **source:** control theory — PID control: the counter is only the Integral term; a full controller also acts on the Proportional (current error rate) and Derivative (its rate of change) terms.
- **mechanism:** The chassis flips on the integral alone: |c| ≥ 32, blind to whether the evidence is accelerating or dying. Add the missing two terms per weight, in fixed point: a fast evidence tracker r (int16, ×16 scale) updated r += vote·16 − r/4 each step (EMA horizon ≈ 4 steps — the Proportional term, P = r/16 ∈ [−1, 1] in vote units, scaled ×4); the Derivative term D = (r − r_prev)/16, the change in evidence rate. Flip test becomes |c + 4·P + 4·D| ≥ V with sign taken from the combined signal, counter reset as usual on a flip. Accelerating evidence (P and D aligned with c) crosses early — the controller anticipates instead of waiting for the integral to fill; evidence that is decelerating or reversing (D against c) must fill the integral honestly. This is anticipation/braking on the flip DECISION, not on the evidence stream.
- **train.py:** new flag `--pid 4:4` on `Layered`: per-component r and r_prev int16 tensors (4 B/weight total, charged), combined-signal flip test in `step`; counters and gate unchanged.
- **mode:** process
- **prediction:** −0.01..+0.02, ranked last on complexity-per-prior: it spends the most state in this file for the least certain return, but it is the only entry that makes the flip rule a function of evidence DYNAMICS rather than evidence totals. Distinct from A-011 vote-EMA (smooths the incoming VOTE and still flips on the plain integral of it) and A-012 (weights votes by EMA agreement; no derivative term, no anticipation).
- **status:** queued
```mill
id: F-030
mode: process
run: --arm layered_half --rope --pid 4:4
```

---

## Miner 2 notes for the pool owner

- All 15 are `process` mode honestly: every one needs a flag `train.py` does not
  have yet, so `screen.py` should DEFER them until their flag lands (pool law).
  None was dressed up as a sweep entry.
- Cheapest first contact: F-016, F-017, F-027, F-021 add no persistent state
  and are each a few lines inside `Layered.step` — they can share one wiring pass.
- The transfer I trust most is **F-016 (anti-windup)**: it is the only entry whose
  target defect can be pointed at in the current code — counters clamped at ±V
  while `want != t` blocks their flip — and its fix is a rule, not a tuned knob,
  so a win cannot be a hyperparameter accident.
- Two entries carry explicit self-voiding diagnostics (F-025's stall histogram,
  F-027's trip count): if the population/event they act on does not exist at this
  scale, their logs say so and they retire without a verdict fight.

## Lens 3 — Failure inversion (was FI-###)

### F-031 ★ · JEPA as initializer, not objective — a trunk "equal to random init" on the probe may still be a better-than-random place to *start*
- **source:** `RESULTS-JEPA-2026-11-12.md` — JEPA probe CE 3.2428 vs untrained floor 3.2445 (paired mean −0.0017, a coin flip), yet JEPA's own prediction loss fell ~4–5× (0.086–0.092 → 0.019–0.023) and target-representation diversity *rose* (per-dim std 0.29–0.32 → 0.36–0.48) with no collapse. E-010/011/012 probe the frozen trunk, mature the target, and densify the mask — all still judge JEPA as a finished representation.
- **mechanism:** Inversion: the probe verdict says JEPA's trunk carries no *linearly readable token information* — it does not say the trunk is in the same *place* as random init. A trunk whose representations are diverse, non-collapsed, and predictive of masked spans may be a superior initialization for ordinary token training even though it is a worthless finished product. Use the six saved trunks in `jepa-states/` as the init for the champion token trainer, instead of random init. JEPA's job changes from "be the model" to "warm the basin."
- **train.py:** `run_jepa.py` already saves the trunks; add `--init-from <state_dict>` to `train.py` (load trunk weights into the layered_half + rotary chassis, fresh counters, fresh AdamW parts) — arms: (a) init from `jepa_half_rope` trunk, (b) init from the paired control trunk (positive control: a token-trained init must help), (c) random init (= champion record). 3 seeds × 8 min, judged at equal steps.
- **mode:** process
- **prediction:** If the diversity/no-collapse traces mean anything, (a) beats random init by ≥0.03 at equal steps and reaches 2.8580's neighbourhood in visibly fewer steps, while landing well behind (b). Any (a) > (c) gap is information the linear probe structurally cannot see — which would reframe the JEPA verdict from "learned nothing" to "learned something the token probe doesn't read, but token training can spend."
- **kill test:** Paired (a)−(c) mean ≥ −0.01 (no better than noise) across 3 seeds — then JEPA init is exactly as empty as the probe said, the inversion dies, and Family 4 of E closes with it.
- **status:** queued
- ★ reason: cheapest strong test in this file — the trunks already exist on disk, and it is the only entry that can overturn a headline verdict (JEPA = nothing) rather than merely price it.

### F-032 ★ · Junk-first curriculum — if ~79% junk produced every number the lab trusts, maybe the junk is load-bearing, and *order* is how it helps
- **source:** `DATA-AUDIT.md` §2–§5 — corpus v1 is 30.8% exact-duplicate pieces, ~23% numeric test-matrix dumps (nine lines of 120k–154k pieces), merge-table gibberish as the two largest sources, 73.9% of source bytes from venv/HF-cache junk — yet this stream produced the champion 2.8580 and every arm verdict. E-018/019/020/021 all *remove* parts of the junk to price the damage; A-041 orders windows by init loss. Nobody has treated junk as an ingredient.
- **mechanism:** Inversion: numeric dumps and boilerplate are low-entropy, highly predictable text — exactly the stream on which a vote counter can bank its first reliable flips (consistent, agreeing gradient evidence) and on which embeddings/scales can calibrate before real prose arrives. Test junk as a *curriculum phase*, not a contaminant: first 25% of steps sample only junk-type windows (numeric dumps + boilerplate + duplicates, tagged at corpus build), remaining 75% sample clean v2 windows only. Mandatory control in the same entry: the identical two-source mixture, shuffled (same junk share, no order) — the pair isolates ORDER from MIXTURE, which no existing entry does.
- **train.py:** new sampler flag `--junk-first 0.25` in `train.py` (window stream tagged by source type from a `make_corpus.py` variant emitting per-line type tags; junk = numeric-dump / separator-boilerplate / exact-duplicate lines per DATA-AUDIT §5 definitions); control arm `--junk-mix 0.25` (same tags, shuffled). Champion chassis, 3 seeds × 8 min, held on v2-native windows so junk familiarity cannot flatter the judge.
- **mode:** process
- **prediction:** Junk-first beats its shuffled-mixture control by ≥0.03 and beats a clean-v2-only run at equal tokens by ≥0.02 — the signature of junk doing early-evidence work rather than merely diluting. Corollary trace: flip share in the first 25% of steps is higher and less thrashy (fewer flip reversals) under junk-first than under either control.
- **kill test:** Junk-first ≥ shuffled control (order earns nothing) **or** junk-first ≥ v2-only (the junk phase is pure cost) — either retires the idea and strengthens E-020's reading that the dumps are inert filler.
- **status:** queued
- ★ reason: it inverts the lab's most embarrassing fact instead of cleaning it up, and its shuffled control makes the result decisive either way — a win rewrites corpus policy, a loss finally clears the junk question.

### F-033 ★ · Split the layered stack into an ensemble — levels that earn nothing *summed* may earn something *voting*
- **source:** `RESULTS-HALF-CONTROL-2026-11-12.md` — plain_half 2.9010 vs layered_half 2.8990 at equal size/steps (Δ 0.0020, clears neither bar): the five levels earn nothing. And `RESULTS-2026-11-11.md` — at equal weights layered was already no better than plain (3.098 vs 3.074). A-036 collapses the components into one plain model late; nobody has separated them.
- **mechanism:** Inversion: a sum forces the two ternary components to agree on one weight value; their failure to beat plain may mean they learned *redundantly*, or it may mean they learned *different* things that the sum averages away. Split a trained layered_half checkpoint into its two component models (t1-only and t2-only, each a complete plain ternary model at half the mechanism state), and serve the pair as a two-model ensemble (mean of logits). If the components' errors are decorrelated, the ensemble beats both the summed model and either component — the layered idea pays, but as an ensemble factory, not as a weight format.
- **train.py:** no training change; new evaluation path `--split-ensemble` in `train.py`'s eval (load a layered checkpoint, build the two component models, report held for t1-only, t2-only, summed, and logit-mean ensemble, per seed, on the standard 128 held windows).
- **mode:** process
- **prediction:** Ensemble held ≤ summed − 0.02 (i.e. ≤ ~2.88 against layered_half's 2.8990 record, re-measured in the same run), with t1-only and t2-only each in the 2.95–3.10 band and per-window error overlap < 80% — decorrelation is the mechanism, so the overlap number is reported either way.
- **kill test:** Ensemble ≥ summed model, or component error overlap ≥ 90% (the components really are redundant copies) — then the levels earn nothing in any arrangement and the layered line is closed at serving as well as in training.
- **status:** queued
- ★ reason: zero training cost (checkpoints + one eval path), and it tests the one arrangement of Arnav's layered idea that has never been tried — separation instead of summation.

### F-034 · The learned say as a verification-budget allocator — a bias that ruins a verdict may be ideal for triage
- **source:** `factory/reports/learned-say-2026-11-12.md` via CANDIDATES-E Family 1 — learned say: dev 0.6528 vs uniform 0.5972, sealed 0.8056 vs incumbent 0.8611, the entire gap clean recall 0.8182 → 0.6364: the say pushes clean code *defect-ward*. E-001/002/003 all try to fix the say's verdict (refit in-loop, constrain the fit, renormalize margins).
- **mechanism:** Inversion: keep the say exactly as fitted and change its job. A defect-ward bias is a failed *judge* but a natural *screener*: high sensitivity, poor precision is precisely the profile wanted for deciding which items deserve the expensive execution-verification pass first. Deploy the say as the verification scheduler: items ranked by say defect-margin descending get waking/execution verification until the budget runs out; the verdict itself always comes from the incumbent composer + verifier path, never from the say.
- **train.py:** factory-side — `factory/learned_say.py` (export the fitted say's per-item defect-margin as a ranking score) + the serving path's verification loop (verify in say-rank order under a call budget). No refitting, no model change.
- **mode:** factory
- **prediction:** At 50% of the full verification budget, say-first allocation holds sealed accuracy ≥ 0.8472 (within 1 item of the 0.8611 full-budget incumbent), and beats random-order and incumbent-margin-order allocation at the same budget by ≥ 1 item — the say's "false alarms" are concentrated exactly where verification pays.
- **kill test:** Say-first allocation ≤ random allocation at equal budget on the sealed battery — the defect-ward lean carries no triage information and the say is retired entirely, not just as a judge.
- **status:** queued

### F-035 · Partial births — adopt the slices a child actually won, keep the parent everywhere else
- **source:** `growth/growth-cycle-006.md` — both children passed the dual pristine gate (expression 0.8500→0.9500 phase-3, 0.6326→0.7392 intent; index 0.9500→1.0000, 0.9566→1.0000), then serving fell 0.8611 → 0.8056 and both births were rolled back wholesale; cycle 7 repeated the shape (serving 0.8611 → 0.8333, clean recall 0.8182 → 0.7273). E-007 adds a gate that blocks bad births; E-008 floors the remainder. Both still treat a birth as all-or-nothing.
- **mechanism:** Inversion: a child that regresses *in composition* but wins *on slices* is not a failed birth — it is a partial one being judged in the wrong unit. Replace whole-model adoption in `factory/growth_cycle.py` with per-intent adoption: on the composed dev path, compute the child's gain intent-by-intent; adopt the child only for intents where composed-dev improves, keep the parent for every other intent (routing already serves slices independently, so the machinery exists). Retro-apply first to the recorded cycle-6/7 children, whose models and slices are on record.
- **train.py:** factory-side — `factory/growth_cycle.py` adoption sequence (per-intent composed-dev diff → adoption mask → routed serving config). No BitNet `train.py` change.
- **mode:** factory
- **prediction:** Retro-check: at least one of the four rolled-back children has ≥1 intent with a real composed-dev gain, and partial adoption of it holds sealed ≥ 0.8611 while capturing part of that gain — converting two total losses (plus two repair operations) into small wins. Prospectively, rollback count drops because fewer births need one.
- **kill test:** For both cycles, *no* intent slice shows a composed-dev gain > 0 for any child — the regressions are uniform, not compositional, partial adoption has nothing to adopt, and E-007's whole-birth gate is the right unit after all.
- **status:** queued

### F-036 · Swapped-operands blindness as a commutativity guarantee — route *to* the blind spot, not away from it
- **source:** `factory/reports/spawn-mining-2026-11-13.md` via CANDIDATES-E Family 2 — raw composed recall on the sealed swapped-operands/plain slice is 0.0 in all 11 measurements, while the seats score 0.88–0.96 alone and serving shows 1.0 only because execution verification carries the class. E-004/005 try to cure the blindness (forced routing, margin normalization); E-006 prices it.
- **mechanism:** Inversion: total, stable operand-order blindness is what an *order-invariant* detector looks like. For genuinely commutative operations (sum, product, max, min) invariance is not a bug — it is the correct inductive bias, and a composer that provably cannot see operand order cannot be fooled by operand order. Split the class by commutativity: route commutative-operator items to the raw composer *because* it is blind (cheap, no verification needed), and reserve the execution-verified path for the non-commutative operators (difference, quotient, remainder, element_at) where order is the whole meaning.
- **train.py:** factory-side — serving routing table (strengths/router config in the swarm composer path): key the swapped/plain slice by operator commutativity instead of routing it wholesale to "whole". Evaluation on dev + sealed, per operator class.
- **mode:** factory
- **prediction:** On the commutative slice, the blind raw composer's accuracy is within 0.05 of the verified path's, while verification calls on the whole swapped slice drop ≥ 30% at unchanged sealed total (≥ 0.8611). If blindness is really invariance, the lab has been paying full verification price to protect a slice that never needed it.
- **kill test:** Commutative-slice raw accuracy < 0.8× the verified path's — the blindness is not clean invariance but general order-confusion that also corrupts commutative items, and the routing inversion dies (E-004/005 remain the only live attacks).
- **status:** queued

### F-037 · Reverse cooldown — if decaying the AdamW parts starved them, feed them *more* late
- **source:** `RESULTS-ROUND2-2026-11-12.md` — two-stage cooldown 2.9707 ± 0.0108 vs baseline 2.8580 (+0.1127, every seed worse than every baseline seed); the record's own diagnosis: "halving the AdamW parts' effective learning in the second half starves the embeddings, norms and scales that the vote-trained weights depend on." E-015 adds the missing weight decay; E-016 exempts the embeddings. Both still decay *something*.
- **mechanism:** Inversion: take the starvation diagnosis literally and run its opposite — a two-stage *warm-up ending hot*: AdamW lr constant 1e-3 for the first half, then linearly **rising** to 2e-3 over the second half, vote rule untouched (V=32, median gate fixed — this is not the closed vote-threshold anneal). Rationale the failure suggests: vote flips keep landing all run, so the continuous parts face a *moving* target late; they may need more fitting capacity at the end, not less. Constant-lr 2e-3 exists in the pool (C-B04) — a late-only ramp is a different claim: early stability, late appetite.
- **train.py:** new flag `--cooldown-inv` on the `Layered` trainer in `train.py` (mirror the existing `cooldown` multiplier code with stage-2 multiplier 1.0 → 2.0 on the AdamW param groups only); sweep config `--arm layered_half --rope --cooldown-inv`, 3 seeds × 8 min.
- **mode:** sweep
- **prediction:** Held recovers the starvation gap and then some: 2.83–2.87, i.e. at or near the 2.8580 champion, with the gain concentrated in the second half's held-loss slope (logged per 20 steps). Even a tie at 2.8580 with a rising schedule falsifies "decay is the right direction for the continuous parts" on this chassis.
- **kill test:** Mean held ≥ 2.8765 (the champion's worst seed) — rising lr hurts or does nothing, the starvation story is wrong in both directions, and the AdamW schedule is confirmed a dead dial at constant 1e-3.
- **status:** queued

### F-038 · The ladder measured tokens; the champion spends steps — re-run one rung at champion steps and count flips
- **source:** `run_scale_ladder.py` — every ladder rung is fixed at 56 steps × 32 batch × 256 ctx = 458,752 pieces; the champion's 2.8580 (`RESULTS-HALF-CONTROL-2026-11-12.md`) came from 154–170 steps ≈ 1.26–1.39M pieces, ~3× the ladder budget. With V=32, a counter needs 32 net agreeing votes to flip once — at 56 steps most weights can flip at most once or twice, so the ladder's big rungs were judged in a regime where the vote mechanism is barely allowed to move. C-A fills the trainer×size×rotary grid *at ladder steps*; E-014 lengthens layered-vs-plain at full width. Neither re-prices a ladder rung at champion steps.
- **mechanism:** Inversion: for a vote trainer, **steps are the currency, tokens are the denomination** — equalizing tokens across rungs systematically handicaps the mechanism the ladder claims to measure. Re-run the 2M rung (dim 288, 2 blocks) at 160 steps, layered+rope and plain+rope, and log the per-weight flip-count distribution at 56 vs 160 steps. The claim under test is vote-specific: the layered-vs-plain gap and the absolute loss at 160 steps should move *more* than a generic "more training helps" effect predicts from the plain arm.
- **train.py:** sweep configs `--arm layered --rope --dim 288 --layers-n 2 --steps 160 --tag scale2m-steps160` and `--arm plain --rope --dim 288 --layers-n 2 --steps 160 --tag scale2m-steps160`, 2 seeds, plus flip-count histogram logging in the `Layered`/`Direct` trainers (count flips per weight, dump at end of run).
- **mode:** sweep
- **prediction:** At 56 steps ≥ 85% of ternary weights flip ≤ 1 time (the ceiling made visible); at 160 steps the layered arm improves over its 56-step record by ≥ 0.10 while plain improves by less, reopening a layered gap that the 56-step ladder reported as flat. Either way, the flip histogram becomes the lab's standard caveat on every fixed-token comparison.
- **kill test:** Both arms improve by the same amount (± 0.02) from 56 → 160 steps, or the 56-step flip histogram already shows a broad multi-flip distribution — then steps are just generic budget, the ladder's token equalization stands, and this entry retires.
- **status:** queued

### F-039 · Carry as a measuring instrument — the arm that lost on mean won on variance by 5×
- **source:** `RESULTS-ROUND2-2026-11-12.md` — overshoot carry: mean 2.8761, **sd 0.0030**, vs the baseline's sd 0.0161; "the three seeds cluster very tightly." Carry is closed as a *trainer* (worse mean, +80% state). Nothing in the pool uses a trainer as an instrument. (E-017 tests carry as a trainer again at V=8 — a different claim, untouched by this entry.)
- **mechanism:** Inversion: a trainer that trades 0.018 of mean for a ~5× tighter seed spread is a worse product and a better *ruler*. The mill's probe screen lives and dies on single-seed (seed-0) verdicts (`RIGOR-AUDIT.md` §3a, priced by E-022); a low-variance probe chassis would make those verdicts cheaper to trust. Re-probe job zero plus four already-ledgered entries with the carry trainer at probe budget and compare cross-seed spread and verdict agreement (promote/flat/below) against the standard plain-vote probes.
- **train.py:** mill-side — `mill/sweep_probe.py` probe config variant `--carry` (the flag already exists in `train.py` for layered arms); no new trainer code.
- **mode:** process
- **prediction:** Carry probes show cross-seed sd ≤ 0.5× the standard probes' sd on the same entries, and the seed-0 verdict agrees with the 3-seed verdict on ≥ 4 of 5 entries (vs the standard chassis' agreement measured in the same pass). If both hold, carry becomes the screening chassis while the champion stays the adoption chassis.
- **kill test:** Carry probe sd ≥ standard probe sd at probe budget (the tight clustering was an 8-minute artefact), or verdict agreement is no better — carry is then closed as an instrument too, completely.
- **status:** queued

### F-040 · Descending vote threshold 64 → 8 — the anneal failed hot-first; run it cold-first
- **source:** `RESULTS-2026-11-11.md` — annealed threshold 8→64 lost decisively: 3.850 ± 0.029 vs plain 3.074; diagnosis: "starting at 8 votes fires flips on weak early evidence… raising the threshold later cannot undo the early disorganization." The pool's schedules (MILL-204/205/206) all *rise* from 24–32; A-033 cycles; D-003 drops V late only inside a replay phase on hard windows. A plain descending schedule over the whole run has never run.
- **mechanism:** Inversion: the failure localizes the damage to the *early hot* phase, so reverse the direction — start strict (V=64: only overwhelming evidence flips while embeddings and scales are still forming) and end hot (V=8: late in the run, gradients are informative and the structure is stable enough to spend flips on fine corrections). Same start/end values as the closed arm, opposite order, different mechanism: the closed arm's sin was early disorganization, which this schedule is built to prevent.
- **train.py:** new flag `--votes-schedule 64-8` on the `Layered` trainer in `train.py` (linear V(step) from 64 to 8 over the run, counter clamp follows current V); sweep config `--arm layered_half --rope --votes-schedule 64-8`, 3 seeds × 8 min.
- **mode:** sweep
- **prediction:** Held lands ≤ 2.90 — far clear of the closed anneal's 3.850 and within reach of the 2.8580 champion — with early flip share (first 25% of steps) at most half the closed arm's ~2×-plain rate. Adoption is not predicted; the claim is directional: order, not endpoints, was the failure.
- **kill test:** Mean held ≥ 2.8990 (layered_half without rotary's record — i.e. no better than doing nothing) or early flip share is not visibly suppressed — descending V is just the anneal wearing its coat backwards, and V-schedules close in both directions.
- **status:** queued

### F-041 · The duplicate-gap as a capacity gauge — leakage flattered every number; turn it into the ladder's memorization instrument
- **source:** `DATA-AUDIT.md` §4 — 30.8% of v1 pieces are exact-duplicate copies and held windows come from the same stream, so "all v1 held losses are flattered by an unknown amount." E-019 removes the leakage to price it; this entry *keeps* the leakage and reads it.
- **mechanism:** Inversion: the flattery is not uniform — it is a measurement of memorization, and memorization capacity is exactly what the scale ladder's 10M/50M rungs claim to add. Partition the 128 held windows into duplicate-tainted (content also present in the training stream) and clean windows, and report the per-rung **duplicate-gap** (clean held − tainted held) for the champion chassis and one 10M rung. If bigger ternary models memorize more, the gap widens with size — a capacity signal that costs no new training data and is invisible in the single pooled held number everyone currently quotes.
- **train.py:** evaluation-only — new `--dup-split-held` reporting in `train.py`'s eval (tag each held window by exact-line overlap with the training stream per DATA-AUDIT §4's method; report both slice losses alongside the pooled number) on one fresh champion run and one `--dim 512 --layers-n 3` layered+rope run at ladder steps.
- **mode:** process
- **prediction:** Champion duplicate-gap is 0.05–0.20, and the 10M rung's gap is visibly larger (≥ 1.5×) despite its worse pooled loss — i.e. the big rungs are spending their capacity on memorization the pooled number hides. Future ladder verdicts should quote both slices.
- **kill test:** Gap < 0.05 at both sizes, or non-monotone in size — leakage flatters everyone equally, carries no capacity information, and E-019's excision is the only duplicate experiment worth its cost.
- **status:** queued

### F-042 · ±2 levels as a free abstention signal — the population that earned nothing as capacity may earn something as confidence
- **source:** `RESULTS-2026-11-11.md` — after 8 minutes only 1.7% of layered weights sat at each of −2/+2, and `RESULTS-HALF-CONTROL-2026-11-12.md` showed those levels earn nothing for loss at equal size/steps. F-033 splits the components; this entry reads the *level distribution itself*, a signal no pool entry uses.
- **mechanism:** Inversion: a weight that fought its way to ±2 holds stronger accumulated evidence than one at ±1 or 0. Even if that extra evidence doesn't lower loss when summed into the weight, it may *mark* the windows the model understands: per-window, the share of active ±2 weights is a zero-cost confidence score computed from state the trainer already maintains. Test it as an abstention signal: rank held windows by ±2-share and check whether loss is monotone in the ranking (selective prediction — answer confidently on high-±2 windows, flag the rest).
- **train.py:** evaluation-only instrumentation in `train.py` — during the standard held evaluation of a layered_half + rotary run, log per-window loss and per-window ±2-active share (weights with |level| = 2 participating in that window's forward); report Spearman correlation and the loss of the top-half vs bottom-half windows by ±2-share.
- **mode:** process
- **prediction:** Spearman ρ ≤ −0.3 between ±2-share and per-window loss, and the top-half-by-±2 windows beat the pooled 2.8580-equivalent per-window loss by ≥ 0.15 — a usable confidence readout from a population currently treated as waste. A flat readout at probe scale but a strengthening one in F-038's 160-step run would tie the signal to level population, as the 1.7% figure suggests.
- **kill test:** |ρ| < 0.2 on the champion run — the levels carry no confidence information either, and ±2 joins the closed list in every role: capacity, ensemble member (pending F-033), and signal.
- **status:** queued

---

## Lens coordinator's note

The pattern across all twelve: this lab's failures are rarely *noise* — they are
consistent, directional, and therefore informative in reverse. Carry is consistent
(sd 0.0030). The say's bias is consistent (exactly one thing traded, every time).
The swapped blindness is *perfectly* consistent (0.0 in 11 of 11). Cooldown's
starvation is consistent (every seed worse than every baseline seed). Systems that
fail this cleanly are usually succeeding at a different job than the one they were
assigned — each entry above simply reassigns the job and charges the failure's own
consistency as the evidence.

**The inversion I believe in most: F-031 (JEPA as initializer).** The JEPA record
contains its own contradiction — prediction loss down 4–5×, representation diversity
*up*, no collapse, yet probe CE identical to random init (−0.0017). Probes read what
is linearly available at the end; initialization spends what is geometrically
available at the start. Those are different currencies, the saved trunks make the
test nearly free, and it is the only entry here that can convert a closed headline
loss into a win without re-running the closed experiment.

*Closing coordination check: `mill/CANDIDATES-E.md` was re-checked immediately
before this file was written — present, unchanged (31,839 bytes). No FI entry
duplicates an E entry; where both touch the same failure (JEPA, the say,
swapped-operands, growth, cooldown, carry, corpus), the E entry repairs or diagnoses
and the FI entry reassigns the failing mechanism to a new job.*

## Lens 4 — Scale extrapolation (was SX-###)

### F-043 · Vote-threshold scaling law: V must FALL as N rises ★
- **source:** scale reasoning — per-weight vote evidence dilutes as weights multiply at fixed tokens: flip share fell from ~0.0011/step (0.885M champion) to ≈0.00021/step at 10M, i.e. at fixed V=32 the trainer gets ~5× colder per 10× of weights. Extrapolated to 50M/500M, V=32 leaves most weights unflipped for the entire run — the model ships near its init.
- **mechanism:** Open-loop threshold law V(N) set to hold flip share ≈0.001/step: V ≈ 32 at 0.885M, ≈16 at 2M, ≈8 at 10M, ≈4 at 50M (int16 counters not needed; hotter, not colder). Distinct from MILL-501..509 (V grid at ONE size), MILL-207/208 (per-layer feedback to a flip-rate target within a run), and A-025 (depth prior): this is a single global V chosen from N before the run, and its claim is that the V-curve's minimum MOVES with N.
- **train.py:** sweep config, no new mechanism — `--arm layered --rope --votes {32,16,8,4}` crossed with rung shapes `--dim 288 --layers-n 2` / `--dim 512 --layers-n 3` / `--dim 1024 --layers-n 4`, ladder format `--steps 56`. Smallest rung where detectable: **10M** (at 2M the dilution is only ~2× and V=16 vs 32 is expected within noise; include 2M as the negative control).
- **mode:** sweep
- **prediction:** At 10M, V=8 beats the rung champion 2.9472 by −0.04..−0.10 and V=16 by −0.02..−0.05, reversing the 0.885M expectation that colder is safer; at 2M all three sit within ±0.02 of 3.2746. At 50M the V=32 champion-config is predicted ≥0.15 worse than V=4.
- **status:** queued
- ★ Top-3 reason: if this law is real and untested, every rung above 2M is being trained with a systematically frozen trainer — the single most expensive silent error available at scale.

### F-044 · Rotating eligibility phases: concentrate evidence on a subset ★
- **source:** scale reasoning — total gradient mass per step is fixed by tokens, not by N, so mean evidence per weight falls as 1/N; at 10M a weight already needs ~190 tilted steps per flip, and at 50M/500M uniform eligibility means almost no weight ever accumulates 32 net votes inside a feasible run.
- **mechanism:** Only 1/k of weights are vote-eligible in each phase (k=5 at 10M, k=10 at 50M); eligibility rotates by weight-index hash every 20 steps so every weight gets focused windows, and ineligible weights' counters are paused (not decayed). Eligible weights receive the full batch's evidence with no dilution across the frozen majority's noise votes. Distinct from A-018 (per-step block rotation of flip *application*; counters still accumulate everywhere) and A-017 (a cap on flips, evidence still uniform): here the *evidence stream itself* is concentrated.
- **train.py:** new flag `--eligible-k 5 --eligible-phase 20` on Layered (hash-partitioned mask over flattened weight index, rotated per phase). Smallest rung where detectable: **10M** (at 0.885M/2M uniform evidence is already sufficient — the mask only throws away signal there).
- **mode:** process
- **prediction:** At 10M ladder format, −0.03..−0.08 vs 2.9472, with eligible-phase flip share ≥4× the champion's 0.00021/step; at 2M, +0.00..+0.04 (expected slightly worse — the control that proves it is a scale effect, not a free win).
- **status:** queued
- ★ Top-3 reason: it is the only entry that attacks evidence dilution structurally instead of retuning around it, and it gets *more* necessary, not less, at 500M.

### F-045 · Sparse counter store: evict near-zero counters ★
- **source:** scale reasoning — counter state (~1 B/weight per component, ~2 B layered) scales linearly with N while the shared parts' AdamW state does not grow with ternary count; at 500M the counters alone are ~1 GB, exceeding the served ternary bytes (~100 MB packed) by ~10×. Simultaneously, evidence sparsity means the large majority of counters sit at |c| < 4 at any moment at scale.
- **mechanism:** Counters live in a sparse store: a weight's counter is materialised only once |c| would reach 4, and evicted back to 0 if it decays below 2 (hysteresis band prevents thrash). Evicted evidence is genuinely discarded — the claim is that at scale, sub-4 evidence is noise-dominated and its loss costs less than the state it occupies. At 0.885M the dense store is trivially cheap, so this is pointless there by construction.
- **train.py:** new flag `--counter-sparse 4,2` on Layered (sparse dict/hash storage for c1/c2, dense fallback below 2M weights). Report state bytes alongside held loss; judged per byte. Smallest rung where detectable: **10M** (state saving ≈5–8× there; loss cost is the measurement).
- **mode:** process
- **prediction:** At 10M, held within +0.00..+0.02 of 2.9472 at ≤25% of the champion's counter bytes — a per-byte win. Falsifier: if the loss cost exceeds +0.03, weak evidence was load-bearing and the dilution picture in F-043/F-044 needs revising.
- **status:** queued
- ★ Top-3 reason: at 500M the vote trainer's state economy — its founding claim vs STE's ~12 B/weight — quietly inverts unless the counter store stops being dense; nobody else in the pool prices counter bytes at scale.

### F-046 · Function-preserving width growth: 2M → 10M with inherited counters
- **source:** scale reasoning — training cost per step grows with N, but a 10M model trained from scratch spends its scarce 56 ladder steps re-learning what a 2M model already knows; at fixed total tokens, growing a trained small net should beat a fresh big one, and the gap widens with the size ratio (invisible at 0.885M, where from-scratch is cheap).
- **mechanism:** Train the 2M rung to its 56 steps, then widen dim 288 → 512 by duplicating each ternary weight's row/column with ±1-level perturbations (installed values preserved in expectation), inheriting counters scaled ×0.5, and train the remaining token budget at 10M shape. Control: 10M from scratch at equal TOTAL tokens (2M phase tokens charged to the growth arm).
- **train.py:** new runner path `--grow-from <2m-ckpt> --grow-width 512` (weight duplication + counter inheritance in the Layered trainer). Smallest rung where detectable: **10M** (growth target; the 2M source is the measured rung).
- **mode:** process
- **prediction:** −0.05..−0.12 vs 2.9472 at equal total tokens. If growth merely ties, from-scratch scaling is healthier than the step-scarcity argument assumes — also a load-bearing answer for the 50M/500M rungs, where from-scratch may be unaffordable outright.

### F-047 · Depth growth by block duplication: 3 blocks → 6, counters halved
- **source:** scale reasoning — depth is the axis where a vote-trained net can add capacity without diluting per-weight evidence as fast as width does (new blocks get fresh weights; existing blocks keep their evidence), but from-scratch depth at 50M pays full price for early blocks that a shallower trained net already solved.
- **mechanism:** Train the 10M shape (dim 512 × 3), then duplicate each block once (6 blocks, ~18.9M weights) with the copy's counters set to half the source's and its ternary states perturbed on 5% of weights; finish at equal total tokens vs an 18.9M from-scratch control. Distinct from A-035 (growing *components* within a weight) and from Fable-side block growth (FP/STE chassis, no counter inheritance — the vote-specific question is whether banked evidence survives duplication).
- **train.py:** new runner path `--grow-depth 2` on Layered. Smallest rung where detectable: **10M** (as the source; effect read at the ~19M target).
- **mode:** process
- **prediction:** −0.03..−0.09 vs the from-scratch ~19M control at equal tokens; the diagnostic that matters is post-growth flip share in duplicated blocks — if it collapses to the 50M-style starved regime, depth growth inherits F-043's problem instead of dodging it.

### F-048 · Repetition-discounted votes: evidence decays with window visits
- **source:** scale reasoning — the corpus holds only ~0.91M unique real pieces (corpus-v2: 907,409 unique); at 0.885M a run barely repeats data, but any serious 50M/500M training is necessarily multi-epoch, and a vote counter cannot distinguish "32 independent windows agree" from "the same window seen 32 times" — repeated windows can single-handedly flip weights, manufacturing structure that is memorisation, not evidence.
- **mechanism:** Each training window carries a visit count; a vote cast from a window on its n-th visit is counted with probability 1/n (stochastic discount, expectation-exact). Fresh windows vote at full strength forever. Distinct from B-009 (measures epoch scaling, changes no rule), B-007/B-008 (corpus-side dedup/filtering), and MILL-406 failweight (oversamples by loss): this discounts by *repetition*, inside the vote accounting.
- **train.py:** new flag `--rep-discount` on Layered/Direct (sampler exposes per-window visit counts to the vote path). Requires a multi-epoch format: 10M shape, 4 epochs over a fixed 25% corpus slice, steps-matched control. Smallest rung where detectable: **10M**, long format only — undetectable in 56-step ladder format at any rung, stated plainly.
- **mode:** process
- **prediction:** In epochs 3–4, held −0.03..−0.08 vs the undiscounted control (which is predicted to *gain* train loss while losing held — the memorisation signature); epochs 1–2 within noise of control.

### F-049 · Gate quantile × width crossover: q must RISE with fan-in
- **source:** scale reasoning — batch-level gradient statistics change character with width: as fan-in grows, per-weight gradient magnitudes concentrate (relative spread shrinks ~1/√fan-in), so the median gate at q=0.5 increasingly admits weights whose |g| is barely above a tightening median — the "stronger half" becomes a weaker filter exactly as the weight count explodes.
- **mechanism:** The gate quantile becomes a width-dependent setting: q=0.5 at dim 192, q=0.75 at dim 512, q=0.9 at dim 1024. Distinct from MILL-601..606 (q grid at the champion shape only): the claim is an interaction — q=0.9 is expected to *lose* at 0.885M (too little evidence survives) and *win* at 10M+.
- **train.py:** sweep of existing-style flags at rung shapes: `--arm layered --rope --gate-q {0.5,0.75,0.9} --dim 512 --layers-n 3 --steps 56` (gate-q flag per MILL-601 family). Smallest rung where detectable: **10M**.
- **mode:** process
- **prediction:** At 10M, q=0.75 beats 2.9472 by −0.02..−0.06 and q=0.9 by −0.01..−0.05; at 0.885M the pooled q grid is expected to show the reverse ordering. A flat q-response at 10M falsifies the gradient-concentration story.

### F-050 · Large-batch vote regime: batch 256–512 with step-matched judging
- **source:** scale reasoning — at 50M+ a step is expensive and tokens are the budget; large batches are the only way to spend tokens, but one vote per weight per step throws away the extra evidence a 512-batch carries (per-step gradient SNR rises ~√batch while the counter still increments by ±1). The batch grid pooled at champion shape (16/64/128, judged per-minute) cannot see this regime.
- **mechanism:** At the 10M rung, run batch {32, 128, 512} judged at EQUAL STEPS (56) and equal tokens separately — two verdicts, not one. The scale claim: batch 128–512, which loses per-minute at 0.885M, wins per-step at 10M because each vote is cast on far cleaner evidence, partially compensating the dilution in F-043.
- **train.py:** sweep config only — `--arm layered --rope --dim 512 --layers-n 3 --steps 56 --batch {32,128,512}`. Smallest rung where detectable: **10M**.
- **mode:** sweep
- **prediction:** Per-step at 10M: batch 128 held −0.03..−0.07 vs the batch-32 champion's 2.9472; batch 512 a further −0.00..−0.03 per-step but clearly worse per-token. If per-step ordering at 10M matches the 0.885M per-minute ordering, batch is not a scale lever and F-043's law must carry the dilution alone.

### F-051 · Vocabulary scaling at fixed ternary budget: 4096 → 16384 at 50M
- **source:** scale reasoning — served bytes flip composition with scale: at 0.885M the FP tied embedding (4096 × 192) rivals the ternary body, but at 50M the ternary share dominates, so vocabulary — unaffordable at lab size — becomes cheap per byte exactly when a bigger vocab's shorter sequences (fewer pieces per byte of text) start paying. Nobody has varied vocab size at any size (B-002 refits the tokenizer at the SAME size; MILL-118/119 price embedding precision/tying at 4096).
- **mechanism:** At the 50M shape, vocab 16384 with a tokenizer refit at that size on corpus-v2, ternary count held at ~50M (dim trimmed 1024 → 960 to pay the embedding). Judged in nats/byte, not nats/token.
- **train.py:** config + corpus rebuild — `--vocab 16384 --dim 960 --layers-n 4 --steps 56` on the 50M shape, corpus-v2 rebuilt at the new vocab. Smallest rung where detectable: **50M** (at 10M the embedding still eats the win — run 10M as the predicted-negative control).
- **mode:** process
- **prediction:** At 50M, nats/byte −0.02..−0.05 vs the 4096-vocab champion-config despite flat-to-worse nats/token; at 10M, nats/byte +0.01..+0.04 (worse). The crossover itself is the deliverable — it sets the vocab for every rung above 50M.

### F-052 · Iso-weight shape reversal at 50M: deep-narrow beats wide-shallow
- **source:** scale reasoning — the shape grid (MILL-1101..1113) and its stated prior ("wider-shallower has the better prior at fixed weights") were established at ≤1.33M weights, where a block is cheap and depth's compounding of ternary error is short. At 50M the terms trade places: wide layers dilute per-weight evidence (F-043) across more weights per block, while depth reuses each block's evidence through more composition.
- **mechanism:** One iso-weight pair at ~50.3M ternary weights, same recipe, ladder format: wide = dim 1024 × 4 blocks; deep = dim 512 × 16 blocks. Nothing else varies.
- **train.py:** sweep config only — `--arm layered --rope --dim {1024,512} --layers-n {4,16} --steps 56`. Smallest rung where detectable: **50M** (a 10M version — 512×3 vs 362×6 — is a legitimate cheap pre-read but the claimed reversal is a 50M claim).
- **mode:** sweep
- **prediction:** Deep beats wide by −0.04..−0.10 at 50M, reversing the small-shape prior; if wide still wins at 50M, the prior is scale-free and the 500M shape is settled cheaply — either outcome retires a whole axis of guessing.

### F-053 · Recurrent depth: block sharing ×2 at 10M, judged per byte
- **source:** scale reasoning — redundancy grows with size: at 0.885M every block is load-bearing, but at 10M+ adjacent blocks in trained transformers are measurably similar, so applying one 10M block-stack twice (effective depth 6, stored depth 3) should cost little loss while halving stored ternary bytes — a trade that only exists once the model is big enough to have slack.
- **mechanism:** The 10M shape (dim 512 × 3 stored blocks) with each block applied twice in sequence; votes accumulate from both applications into the shared block's counters (evidence per stored weight doubles — a side benefit under dilution). Judged per served byte against the unshared 10M champion and against a stored-3/applied-3 control at equal steps.
- **train.py:** new flag `--share-blocks 2` in the model builder. Smallest rung where detectable: **10M**.
- **mode:** process
- **prediction:** Held +0.01..+0.04 vs 2.9472 (a small cost) at 50% of the ternary bytes — a per-byte win; at 0.885M the same trick is predicted to cost +0.08 or more, which is why it was never worth pooling there.

### F-054 · Depth-graded freezing at depth ≥6: bottom half sets early
- **source:** scale reasoning — with depth, early blocks' flips perturb every downstream block's evidence stream; at 2 blocks freezing half the net is absurd, but at 6–16 blocks the bottom half converges first (its gradients are the least diluted — shortest path from the loss through shared structure) and its late flip noise is pure cost imposed on all blocks above it.
- **mechanism:** On a depth-6+ shape, the bottom half of blocks stop flipping after 50% of steps (counters keep recording, flips are suppressed — so the freeze is reversible and auditable), while the top half trains to the end. Distinct from A-037/D-006 (whole-structure or AdamW freezes at 2 blocks) — the claim is specifically that the freeze boundary should sit mid-depth and only exists at depth.
- **train.py:** new flag `--freeze-bottom 0.5,0.5` (fraction of blocks, fraction of run) on Layered, run at dim 768 × 6 (~42M) or the F-052 deep shape. Smallest rung where detectable: **50M** (depth 6 at ~42–50M; at the 10M rung's depth 3 the "bottom half" is 1–2 blocks and the effect is not separable from noise).
- **mode:** process
- **prediction:** −0.02..−0.06 vs the 50M champion-config at equal steps, with top-half flip share rising after the freeze (evidence stops being scrambled from below). A loss would mean early-block plasticity is still earning at depth — which would re-rank F-047's depth-growth assumptions.

---

*End of lens 4. 12 entries (F-043..F-054), ranked; ★ = F-043, F-044, F-045.*

## Lens 6 — Wild cards (was WC-###)

### F-055 · ★ The reservoir control: never train the ternary weights at all
- **source:** wild-card reasoning — a careful person filters this because it "isn't training the model": freeze every ternary state at its random init for the whole run and let only the FP parts (embeddings, norms, per-layer scales) learn. They might be wrong to skip it: the lab has never priced what vote training itself earns against a random ternary reservoir with trained scales, and every votes-vs-STE comparison silently assumes the answer is "a lot."
- **mechanism:** random frozen ternary matrices are a fixed random-feature reservoir; the FP parts fit readouts/scales to it. The probe measures the exact size of the hole the vote mechanism fills — the denominator every other entry in the pool is implicitly divided by.
- **train.py:** new flag `--freeze-tern 0.0` on Layered (ternary states and counters frozen from step 0; AdamW group trains normally) — `--arm layered_half --rope --freeze-tern 0.0`
- **mode:** process
- **prediction:** interesting if probe held lands within 0.10 of job-zero — that would mean most of the champion's quality is reservoir + FP fitting, and the entire vote program is fighting over a sliver.
- **kill test:** retire if the one probe lands ≥ job-zero + 0.30 (frozen reservoir catastrophically worse): votes plainly earn their keep, the suspicion dies in 75 seconds, and the number still enters the record as the mechanism's priced floor.
- **status:** queued

### F-056 · ★ Knowledge lives in the counters: wipe the last block's weights, keep its counters
- **source:** wild-card reasoning — a careful person filters this because deliberately destroying trained weights mid-run looks like sabotage. They might be wrong: the trainer's design says the counters ARE the accumulated evidence and the ternary state is just their readout; if so, a wiped block should be rebuilt by its own banked counters within a few dozen steps, and "training" was never in the weights at all.
- **mechanism:** every 20 steps, re-randomise block 2's ternary states (t1/t2) while leaving c1/c2 untouched. Counters keep voting from their banked positions, so flips re-install approximately the pre-wipe state — unless the knowledge was in the states, in which case each wipe is a real amputation.
- **train.py:** new flag `--wipe-block 2 --wipe-every 20` on Layered (state re-init only; counters, scales, AdamW untouched) — `--arm layered_half --rope --wipe-block 2 --wipe-every 20`
- **mode:** process
- **prediction:** interesting if probe held is within +0.03 of job-zero despite ~5–8 full wipes in a probe run — recovery that fast proves counters carry reconstructable knowledge, a claim no entry in the pool makes.
- **kill test:** retire if probe held ≥ job-zero + 0.10, OR if the logged post-wipe flip share does not spike to ≥3× the run's mean flip share in the 5 steps after a wipe (no spike = the counters are not even trying to rebuild; the mechanism story is dead on its own terms).
- **status:** queued

### F-057 · ★ Easy-only diet: throw away every hard window, train on what the model already gets right
- **source:** wild-card reasoning — a careful person filters this because training only on mastered material "teaches nothing," and the pool's whole data side pushes the other way (failweight, mistake replay, hard curricula). They might be wrong: a vote counter needs CONSISTENT evidence to reach 32 net votes; hard windows are exactly where per-batch gradient signs contradict each other and cancel in the counter. A coherent, easy gradient field may build clean structure that generalises to hard windows it never saw.
- **mechanism:** score windows once with the init model (the curriculum family's existing scoring pass); exclude every window above the median loss from the stream entirely — not downweighted, not ordered: gone. The run trains on the easy half only, at matched step count.
- **train.py:** new flag `--easy-only 0.5` (sampler exclusion by init-loss percentile; distinct from A-041's ordering, which keeps all data, and A-056's 2% trim) — `--arm layered_half --rope --easy-only 0.5`
- **mode:** process
- **prediction:** interesting if probe held beats job-zero by ≥0.02 — half the corpus, the "useless" half by doctrine, winning would invert the lab's data doctrine and re-read failweight and the dream family.
- **kill test:** retire if probe held ≥ job-zero + 0.02 (outside the flat band on the wrong side): easy evidence is as empty as doctrine says, one probe, done.
- **status:** queued

### F-058 · Minority readout: ship the LEAST common state of the last 5 checkpoints
- **source:** wild-card reasoning — a careful person filters this because majority/mode readout is "obviously" the right summary and the minority is by definition the states training rejected. They might be wrong: on contested weights the modal state is the one the lattice kept leaving; the minority state is disproportionately the most recent direction of travel. If the checkpoint sequence has momentum, the tail state — not the consensus — is the prediction.
- **mechanism:** save ternary states every N steps as the modal-readout entries already do; at readout, per weight ship the least frequent of the last 5 checkpoint states (ties → the most recent). Eval-side only; the same run also reports its modal readout, so the probe measures the readout delta directly.
- **train.py:** new eval-side flag `--minority-readout 5` on Layered — `--arm layered_half --rope --minority-readout 5`
- **mode:** process
- **prediction:** interesting if minority readout is within 0.01 of modal readout on the same run (consensus was never the active ingredient), and a sensation if it beats modal by >0.01.
- **kill test:** retire if minority readout is ≥0.05 worse than the modal readout measured on the identical run — one eval pass on checkpoints that already exist; the cheapest kill in this file.
- **status:** queued

### F-059 · Cross-layer vote transplant: each layer votes on its neighbour's gradients
- **source:** wild-card reasoning — a careful person filters this because a weight voting on another layer's gradient signs is a category error. They might be wrong: gradient sign fields across adjacent blocks of the same width are correlated through the residual stream; if transplanted votes train nearly as well, the vote mechanism's value is mostly "any consistent sign pressure," not per-weight evidence — which would demote a shelf of per-weight machinery in the pool.
- **mechanism:** in `Layered.step`, cyclically permute the per-layer gradient tensors before the gate/vote computation: block 1's weights accumulate votes from block 2's gradient signs and vice versa (shapes match at half chassis: both blocks dim 192). Counters, gate, V, and flip rules unchanged; AdamW parts get their true gradients.
- **train.py:** new flag `--vote-xplant` on Layered — `--arm layered_half --rope --vote-xplant`
- **mode:** process
- **prediction:** interesting if probe held is within +0.05 of job-zero — locality of evidence, assumed by every vote entry ever filed, would be falsified at probe cost.
- **kill test:** retire if probe held ≥ job-zero + 0.15: per-weight evidence is as load-bearing as assumed, and the transplant number becomes the locality bound in the record.
- **status:** queued

### F-060 · Counter diffusion: evidence leaks sideways into neighbouring weights
- **source:** wild-card reasoning — a careful person filters this because counters are per-weight by definition and blurring them "destroys the accounting." They might be wrong: weights in the same row share an input and their true gradient signs are spatially correlated; the pool's leak family only ever decays counters in TIME. A small spatial diffusion is a denoiser matched to the noise structure — each counter borrows its neighbours' evidence the way an image filter borrows pixels.
- **mechanism:** after each step, each counter moves 10% toward the mean of its four nearest neighbours' counters within the same matrix row/column grid (fixed-point, clamp ±V preserved). No change to votes, gate, or flip rule.
- **train.py:** new flag `--counter-diffuse 0.1` on Layered — `--arm layered_half --rope --counter-diffuse 0.1`
- **mode:** process
- **prediction:** interesting if probe held beats job-zero by ≥0.02, especially with a lower flip count (same loss on fewer, surer flips = the denoising story confirmed in the run's own logs).
- **kill test:** retire if probe held ≥ job-zero + 0.02, OR if total flips fall by >50% vs job-zero at flat-or-worse loss (diffusion only smeared the evidence into inaction).
- **status:** queued

### F-061 · Scalar-feedback votes: no per-weight gradients in the vote path at all
- **source:** wild-card reasoning — a careful person filters this because replacing per-weight gradients with one global bit of feedback ("loss went down / up") throws away nearly all the information in training. They might be wrong: the counter is an integrator, and integrators exist to extract signal from exactly this kind of impoverished stream; 884k weights × thousands of steps is a lot of coin flips for a bandit to learn from.
- **mechanism:** each step, compute the batch loss delta vs the previous batch. Every weight whose counter is non-zero receives a vote in its counter's current direction if loss fell, against it if loss rose (rich-get-richer bandit reinforcement); zero counters receive a random ±1 vote. Gate and magnitudes are not used — the vote path never sees a gradient. AdamW parts train normally on true gradients.
- **train.py:** new flag `--bandit-votes` on Layered — `--arm layered_half --rope --bandit-votes`
- **mode:** process
- **prediction:** interesting if probe held beats the F-055 reservoir control by ≥0.05 — structure learning from a single bit per step would be a genuinely new fact about this trainer family.
- **kill test:** retire if probe held is within 0.02 of F-055's frozen-reservoir probe (bandit votes indistinguishable from not training the weights), or ≥ job-zero + 0.20 outright if F-055 has not run yet.
- **status:** queued

### F-062 · Reversed-text first half: learn language backwards, then turn around
- **source:** wild-card reasoning — a careful person filters this because language modelling is causal and reversed windows are "garbage data." They might be wrong: the ternary lattice's early phase — the phase the closed anneal arm proved is decisive — may mostly be learning local token statistics, which are nearly direction-symmetric at short range; a reversed first half could pre-build that structure without burning forward-pass evidence on init noise, and rotary's geometry does not care which way the text runs.
- **mechanism:** for the first 50% of steps, every training window is reversed (token order flipped; the model predicts the previous token). At 50% the stream flips to normal forward windows for the remainder. Objective, chassis, and budget unchanged; total steps matched to control.
- **train.py:** new flag `--reverse-first 0.5` (sampler transform) — `--arm layered_half --rope --reverse-first 0.5`
- **mode:** process
- **prediction:** interesting if probe held beats job-zero by ≥0.02 — the reversed phase acted as free pre-structure rather than poison — or if the loss at the 50% flip point recovers to the control's same-step loss within 10 steps (no lasting damage from half a run of "garbage").
- **kill test:** retire if probe held ≥ job-zero + 0.05: backwards pre-training is a real cost the second half cannot repay at any horizon this lab can afford.
- **status:** queued

### F-063 · Batch 1: one window, one testimony, no averaging anywhere
- **source:** wild-card reasoning — a careful person filters this because batch 1 is "obviously" too noisy and the pooled batch grid stops at 16. They might be wrong: batch-32 pre-averaging destroys exactly the per-example sign disagreement that a counter exists to integrate over time. Averaging first and integrating second is doing the counter's job badly, upstream, with the wrong statistic (mean instead of accumulated sign evidence).
- **mechanism:** batch size 1 for the whole run; every step is one window's unmediated vote. Steps per probe rise sharply (charged honestly: judged per minute like every arm, and the step count is logged).
- **train.py:** no new flag — `--arm layered_half --rope --batch 1` (existing `--batch` in both parsers)
- **mode:** sweep
- **prediction:** interesting if probe held beats job-zero by ≥0.02 at equal minutes — the counter was the right integrator all along and batching was the noise source, not the cure.
- **kill test:** retire if probe held ≥ job-zero + 0.05, OR if flip share exceeds 5× job-zero's (the lattice is thrashing, not integrating — the noise story wins).
- **status:** queued

### F-064 · The 70% zero cull: impose the sparsity, don't persuade it
- **source:** wild-card reasoning — a careful person filters this because randomly zeroing trained weights every 10 steps is vandalism, and the pool's only sparsity lever is a gentle 1.5× vote nudge toward zero (A-009). They might be wrong: the lab's own record says the ~42% zero fraction is load-bearing feature selection — but that fraction is an emergent accident. If zero-ness is doing real work, forcing it to 70% should either win outright or show exactly where the accident was already optimal.
- **mechanism:** every 10 steps, randomly select currently-nonzero weights and set them to 0 (counters zeroed) until the installed zero fraction is exactly 70%. Between culls, training is untouched champion. The cull is uniform-random — no magnitude ranking — so any win is attributable to the fraction itself, not to pruning skill.
- **train.py:** new flag `--zero-cull 0.7 --cull-every 10` on Layered — `--arm layered_half --rope --zero-cull 0.7 --cull-every 10`
- **mode:** process
- **prediction:** interesting if probe held is within +0.02 of job-zero at 70% zeros — the serving model could then ship far sparser at no cost — and a win (>0.02 better) would indict the natural 42% as under-sparse.
- **kill test:** retire if probe held ≥ job-zero + 0.08: the emergent fraction was near its optimum and imposed sparsity is just damage, priced in one probe.
- **status:** queued

### F-065 · Backwards rotary: positions run in reverse while the text runs forward
- **source:** wild-card reasoning — a careful person filters this because RoPE's angles encode true position order and negating them "breaks the position signal." They might be wrong: rotary's measured win (−0.0411) was never split into "a consistent relative-position code" vs "the CORRECT code." A sign-flipped rotation is an equally consistent code with reversed geometry — if it also wins, the lab has been crediting position understanding for what is really a conditioning/regularisation effect.
- **mechanism:** negate all RoPE rotation angles (equivalently, rotate by position −t instead of t) for both Q and K; data order, chassis, and everything else unchanged.
- **train.py:** new flag `--rope-neg` in Block (angle sign flip; requires `--rope`) — `--arm layered_half --rope --rope-neg`
- **mode:** process
- **prediction:** interesting if probe held is within +0.02 of job-zero (backwards positions ≈ forwards positions: the win is code-consistency, not order) — a result that re-reads the ROPE results file and the whole partial/NoPE family.
- **kill test:** retire if probe held ≥ the no-rope control (MILL-1114) probe + 0.02: reversed geometry is worse than no geometry, order really is the content, question closed in one probe.
- **status:** queued

### F-066 · All-+1 init: start from the worst possible histogram
- **source:** wild-card reasoning — a careful person filters this because initialising every ternary weight to +1 (no zeros, no −1s) is a sabotaged start no sane run would use, and the pool's init entries go the other way (match the trained histogram, A-114). They might be wrong: if the vote mechanism is a real attractor, the init histogram should be nearly irrelevant by mid-run, and proving that on the most hostile init available is the strongest robustness evidence the mechanism could own — plus any init-dependence found here bounds every seed-variance argument in the record.
- **mechanism:** all t1 states init to +1, all t2 states to 0 (installed value uniformly +1×scale per weight); counters at 0; everything else champion. The counters must carve the entire {-1,0,+1} structure out of a constant field.
- **train.py:** new flag `--init allpos` in the model builder — `--arm layered_half --rope --init allpos`
- **mode:** process
- **prediction:** interesting if probe held is within +0.05 of job-zero — the mechanism recovers from a maximally wrong start inside 75 seconds, and init engineering (two pooled entries) drops in value accordingly.
- **kill test:** retire if probe held ≥ job-zero + 0.15: init is a first-order variable even for votes, the hostile-init number stands as its priced bound, and A-113/A-114 gain priority instead.
- **status:** queued

---

## Appendix — working-id mapping (miners -> wave F)

- FP-001 -> F-001
- FP-002 -> F-002
- FP-003 -> F-003
- FP-004 -> F-004
- FP-005 -> F-005
- FP-006 -> F-006
- FP-007 -> F-007
- FP-008 -> F-008
- FP-009 -> F-009
- FP-010 -> F-010
- FP-011 -> F-011
- FP-012 -> F-012
- FP-013 -> F-013
- FP-014 -> F-014
- FP-015 -> F-015
- XD-001 -> F-016
- XD-002 -> F-017
- XD-003 -> F-018
- XD-004 -> F-019
- XD-005 -> F-020
- XD-006 -> F-021
- XD-007 -> F-022
- XD-008 -> F-023
- XD-009 -> F-024
- XD-010 -> F-025
- XD-011 -> F-026
- XD-012 -> F-027
- XD-013 -> F-028
- XD-014 -> F-029
- XD-015 -> F-030
- FI-001 -> F-031
- FI-002 -> F-032
- FI-003 -> F-033
- FI-004 -> F-034
- FI-005 -> F-035
- FI-006 -> F-036
- FI-007 -> F-037
- FI-008 -> F-038
- FI-009 -> F-039
- FI-010 -> F-040
- FI-011 -> F-041
- FI-012 -> F-042
- SX-001 -> F-043
- SX-002 -> F-044
- SX-003 -> F-045
- SX-004 -> F-046
- SX-005 -> F-047
- SX-006 -> F-048
- SX-007 -> F-049
- SX-008 -> F-050
- SX-009 -> F-051
- SX-010 -> F-052
- SX-011 -> F-053
- SX-012 -> F-054
- WC-001 -> F-055
- WC-002 -> F-056
- WC-003 -> F-057
- WC-004 -> F-058
- WC-005 -> F-059
- WC-006 -> F-060
- WC-007 -> F-061
- WC-008 -> F-062
- WC-009 -> F-063
- WC-010 -> F-064
- WC-011 -> F-065
- WC-012 -> F-066
