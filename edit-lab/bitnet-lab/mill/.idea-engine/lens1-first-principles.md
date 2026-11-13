# Muse's work — Muse's side

# LENS 1 — FIRST-PRINCIPLES candidates for the Idea Engine (BitNet lab, Muse's side)

<!-- Miner 1, first-principles lens. Every entry is derived from the mathematics of the
vote mechanism itself — what a counter IS — not from papers and not from past failures.
Deduped against mill/IDEA-POOL.md (all sections incl. merged stream A), CANDIDATES-A/B/C/D
and FABLE-CANDIDATES.md. Nothing here restates a pooled family (counter clamps, leak
variants, hysteresis, thrash tax/freeze, two-counter race, EMA evidence, soft gate,
per-row gate, flip arbitration, readouts, V/gate grids) and nothing re-opens the closed
list (overshoot carry, AdamW cooldown, threshold anneal 8→64, magnitude votes as
specified, JEPA objective). -->

**Chassis for every entry:** the champion — layered_half + rotary, held 2.8580 ± 0.0161,
884,736 ternary weights, V=32, batch 32, ctx 256, vocab 4096, dim 192 × 2 blocks.
All entries are `mode: process` (each needs one new flag; screen.py defers until it lands).
Probe = standard 75 s; trial = 3 seeds × 8 min. Several mechanisms are provably near-inert
at probe horizon (~25 steps < V=32 net votes to a first flip from 0) — those entries say so
and stake their prediction at trial scale, with the probe as a plumbing/direction check.

**Top 3:**
- ★ **FP-001 · Boundary-pressure rerouting** — saturated weights' outward votes currently vanish into a no-op; conservation of gradient pressure says that signal must go somewhere, and the per-layer scale is the only channel that can hold it.
- ★ **FP-002 · Weak-half slow counter** — the median gate discards half of all samples; by the law of large numbers that half's aggregate sign is real signal, and no pooled entry ever recovers it.
- ★ **FP-003 · Orthogonal second channel for t2** — two counters fed the *identical* vote stream carry 1 bit/step total, not 2; the layered structure's second information channel is currently transmitting a copy.

---

### FP-001 · Boundary-pressure rerouting: saturated votes feed the scale ★
- **source:** first-principles derivation — ternary state space is bounded ({-1,0,+1} per component, installed {-2..+2}), so a strong vote pushing a saturated weight further outward triggers the boundary no-op rule and its information is *destroyed*. Gradient pressure is a conserved signal in the backward pass: whatever the discrete state cannot express must exit through a continuous channel or be lost. The only continuous channel attached to the same layer is its install scale (log_scale).
- **mechanism:** when a component sits at its boundary (+1 with a + vote, -1 with a - vote) and the vote is strong (passes the median gate), the vote does not increment the counter; instead it adds a small fixed quantum (1/V of a step) to a per-layer boundary-pressure accumulator. At each step the layer's log_scale is nudged by lr_scale × (net boundary pressure that step), then the accumulator resets. Inward and ordinary votes behave exactly as champion.
- **train.py:** new flag `--boundary-scale` on Layered (boundary votes diverted from `c1/c2` into a per-layer scalar; applied to `log_scale` inside `step()`, alongside the existing AdamW update of the same parameter — the two contributions sum).
- **mode:** process
- **prediction:** -0.02..-0.05 at trial scale. Reasoning: the zero-heavy trained histogram means a large share of weights sit at ±1/±2 late in training, so the discarded outward stream is a substantial fraction of all strong votes — recovering it as scale motion is recovering magnitude information the ternary code structurally cannot hold (the same information STE carries in its latent weights). At probe scale expect ~0 to -0.01 (few weights are saturated in the first ~25 steps); a probe win is not required, a probe *loss* >0.02 kills it.
- **status:** queued
```mill
id: FP-001
mode: process
run: --arm layered_half --rope --boundary-scale
```

### FP-002 · Weak-half slow counter: the gated-out 50% votes on a long clock ★
- **source:** first-principles derivation — the median gate keeps the stronger half of gradients and discards the weaker half entirely (0 bits retained). But a weak vote is a Bernoulli sample with the same sign bias p as a strong one, only noisier per sample; by the law of large numbers, the *sum* of N weak votes has SNR growing as √N·(2p-1), so over a long enough horizon the discarded half carries flip-grade evidence. Discarding it is optimal only if the horizon is infinite for the strong stream and zero for the weak — the current design.
- **mechanism:** each weight gains a second, slow counter fed ONLY by gated-out (weak-half) votes, with its own threshold V_slow = 128 (4× V). A flip fires when *either* counter crosses its threshold (fast counter at ±32 from strong votes, slow counter at ±128 from weak votes); on any flip both counters reset. Distinct from the pooled two-counter race (A-006: up/down split, BOTH conditions required, same stream), from A-109 dual streams (alternating batches, consensus required), and from the soft gate (A-001: reweights strong-side increments, weak side still contributes exactly 0).
- **train.py:** new flag `--weak-slow 128` on Layered (int16 slow counters; gate already computes the weak/strong partition, so the weak votes exist in `step()` today and are thrown away there).
- **mode:** process
- **prediction:** -0.01..-0.04 at trial scale, ~0 at probe scale by construction (128 net weak votes cannot accumulate in ~25 steps — the probe is a plumbing check only; judge at trial). Reasoning: weak-stream flips will be rare and late, but they are flips the champion *never* makes, on evidence that is unbiased; the risk is that weak votes are weak because their weights are genuinely contested (p≈0.5), in which case slow counters random-walk and almost never cross ±128 — the mechanism is self-limiting, which caps the downside near 0.
- **status:** queued
```mill
id: FP-002
mode: process
run: --arm layered_half --rope --weak-slow 128
```

### FP-003 · Orthogonal second channel: t2 votes on the gradient innovation ★
- **source:** first-principles derivation — information theory of the layered code: both component counters integrate the *same* vote stream sign(g) (gated). Two integrators fed identical inputs carry exactly 1 bit/step of new information in total, however many counters there are; the second component's counter adds state but no bandwidth. The gradient stream contains a second, nearly independent bit per step — the sign of the innovation, sign(g_t − EMA(g)) — which is (to first order) uncorrelated with sign(g) itself and is currently computed by no one.
- **mechanism:** c1 integrates the champion vote stream unchanged. c2 integrates sign of the per-weight gradient innovation: vote2 = sign(g − ḡ) when |g − ḡ| clears its own layer median, where ḡ is a per-weight EMA of g (β=0.9, fp state charged honestly at 4 B/weight). t2 therefore flips on *changes* in the gradient's direction/magnitude regime — it becomes a genuine correction channel tracking what the backbone's evidence is drifting toward, instead of a delayed copy of the backbone's own stream. Flip thresholds stay V=32 for both; arbitration unchanged.
- **train.py:** new flag `--t2-innov` on Layered (EMA buffer + second gate inside `step()`; c2's increment source is the only change).
- **mode:** process
- **prediction:** -0.02..-0.06 at trial scale; -0.00..-0.02 at probe scale. Reasoning: the half-control showed two components fed one stream earn nothing at equal size/steps (gap 0.0020) — this entry is the direct test of *why*: if the null was an information-bandwidth null (identical inputs), an independent second channel is the fix the null itself points to; if FP-003 also ties plain, the levels question is closed for a deeper reason and that is a finding worth its probe.
- **status:** queued
```mill
id: FP-003
mode: process
run: --arm layered_half --rope --t2-innov
```

### FP-004 · SPRT thresholds: per-weight V from the vote stream's own consistency
- **source:** first-principles derivation — sequential analysis (Wald's SPRT): a counter accumulating ±1 votes is a random walk whose log-likelihood ratio after net count c and total votes n is c · log(p/(1−p)), where p is the weight's probability of a + vote. A *constant evidence standard* therefore means a constant threshold in LLR units, which means the vote-count threshold must scale as V_i ∝ 1 / log(p_i/(1−p_i)) — a single global V=32 holds consistent weights (p near 0 or 1) and coin-flip weights (p≈0.5) to wildly different evidence standards, over-waiting on the former and under-waiting on the latter.
- **mechanism:** each weight tracks its own vote consistency online (counts of + and − strong votes since last flip, two int16s or one fp ratio). Its personal threshold is V_i = clip(round(A / |log(p̂/(1−p̂))|), 8, 96), with A set so a p̂=0.75 weight gets V_i=32 (champion-equivalent at that consistency). p̂ is Laplace-smoothed and frozen for the first 16 votes after a flip (insufficient data → V_i=32). Distinct from per-layer flip-rate V (MILL-207/208: feedback on a *rate*, per layer), thrash tax (A-008: threshold from *flip count*), and depth/role V priors (A-025/026/029: fixed by position, not measured per weight).
- **train.py:** new flag `--sprt-v` on Layered (per-weight threshold array replacing the scalar `self.votes` in the flip test; clamp stays at the personal threshold).
- **mode:** process
- **prediction:** -0.02..-0.05 at trial scale; ~0 at probe (p̂ estimates are meaningless for the first flips; expect champion-identical behaviour until mid-run). Reasoning: the weights with p̂ far from 0.5 are the majority of eventual flips, and they currently wait for 32 net votes when SPRT says ~10–16 carry the same evidence — they flip late or, within a ~160-step run, never. Faster correct flips early compound through every later gradient.
- **status:** queued
```mill
id: FP-004
mode: process
run: --arm layered_half --rope --sprt-v
```

### FP-005 · State-stratified gate: the median is computed within each ternary state
- **source:** first-principles derivation — the gradient distribution is *conditioned on the weight's current state*: a weight at 0 and a weight at +1 have systematically different |g| distributions (their loss derivatives differ by construction of the forward pass). A single layer-wide median therefore does not select "the stronger half of evidence" — it selects a state-biased subset, silently giving whichever state group has larger typical |g| a majority of all votes, every step, in every layer.
- **mechanism:** the strong/weak partition is computed separately within each installed-state group of the layer (for layered: within each installed level −2..+2; groups with <64 members fall back to the layer median). Every state group contributes its own stronger half, so each state's weights receive votes at the same *rate* and are selected by within-group strength. Gate quantile stays q=0.5 inside each group. Distinct from per-row gate (A-002: stratifies by output neuron) and per-layer V (stratifies the threshold, not the gate).
- **train.py:** new flag `--gate-scope state` on Layered (alongside `--gate-q`; grouped quantile inside `step()`).
- **mode:** process
- **prediction:** -0.01..-0.04 at both probe and trial scale (the bias, if real, acts from step 0 — this is one of the few entries whose probe reading is meaningful). Reasoning: if the state groups' |g| medians differ by even 20%, the pooled gate misallocates roughly a tenth of all votes toward the already-dominant state; the probe also returns the diagnostic itself (per-state median ratios), which prices the bias even if the loss is flat.
- **status:** queued
```mill
id: FP-005
mode: process
run: --arm layered_half --rope --gate-q 0.5 --gate-scope state
```

### FP-006 · Canonicalization of the layered code (degeneracy removal)
- **source:** first-principles derivation — the layered encoding is many-to-one: installed value v = t1 + t2 with t1,t2 ∈ {−1,0,+1} has redundant representations (e.g. +1 = (1,0) = (0,1); 0 = (0,0) = (1,−1) = (−1,1)). The counter dynamics wander this degenerate fibre freely: components can swap or cancel (t1 up while t2 down) while the installed value — the only thing the loss sees — does not move. Those are wasted flips and wasted counter motion in a representation space larger than the function space.
- **mechanism:** every 32 steps, each weight's component pair is rewritten to the canonical representative of its installed value — t1 = sign(v)·min(|v|,1), t2 = v − t1 — *without changing any installed value* (forward output is bit-identical across the rewrite). Counters are remapped with it: the canonical backbone component keeps the sum c1+c2 clipped to ±V, the correction component's counter restarts at 0. Distinct from comp-reset (A-020: resets a sibling counter *on a flip*; this is a scheduled, value-preserving reparameterization) and from all flip-arbitration rules (which govern crossings, not representations).
- **train.py:** new flag `--canon 32` on Layered (periodic reparameterization pass in the training loop / `step()`).
- **mode:** process
- **prediction:** -0.01..-0.03 at trial scale; ~0 at probe (one or two canonicalizations only). Reasoning: cancellation pairs (1,−1) sitting at installed 0 are pure churn capacity — they hold two live counters that can burn flips returning to the same function; canonical form concentrates all evidence for a value into one counter, so subsequent flips express real function changes. Downside is bounded: the rewrite provably cannot change the function, only the dynamics.
- **status:** queued
```mill
id: FP-006
mode: process
run: --arm layered_half --rope --canon 32
```

### FP-007 · Counter-confidence install: the counter modulates the forward magnitude
- **source:** first-principles derivation — the counter is a sufficient statistic for the weight's recent gradient history (it is literally the integrated evidence), yet the forward pass reads only the ternary state and discards the counter entirely. Two weights both at +1, one at c=+31 (about to flip up) and one at c=−31 (about to flip down), present *identical* values to the network despite opposite, near-certain futures. That is information the model computed and then refused to use.
- **mechanism:** the installed value becomes t · γ_layer · (1 + κ · c/(V · γ̂)) applied per component — concretely, effective weight = γ · (t + κ·c/V) with κ=0.25: the counter contributes a bounded continuous correction of at most ±25% of one level, so a weight leans toward its impending flip before it commits. At a flip the counter resets, so the correction is continuous through the flip boundary (the pre-flip lean and the post-flip state agree to within the κ band). Serving strips the correction (export = plain ternary at the final states); it is a training-time representation only, charged as such. Distinct from all scale-granularity entries (MILL-107/108/701–703: scales from weight *magnitudes*) and learn-scale (MILL-1013): here the modulation source is the *counter*, a quantity no pooled entry reads in the forward pass.
- **train.py:** new flag `--conf-install 0.25` on Layered (install() adds the counter term; eval/export path unchanged).
- **mode:** process
- **prediction:** -0.02..-0.05 at probe and trial scale (acts from the first counter movement, unlike most entries here). Reasoning: this softens the mechanism's core discontinuity — the installed function currently jumps by a full level on flip day and is frozen between flips; a κ-lean makes the effective function move quasi-continuously with evidence, recovering part of what STE's latent weights provide, at zero extra state (the counter already exists). Risk: forward now depends on a noisy statistic; κ=0.25 bounds the noise injection to a quarter-level.
- **status:** queued
```mill
id: FP-007
mode: process
run: --arm layered_half --rope --conf-install 0.25
```

### FP-008 · Row-coincidence flip cap: at most one flip per output row per step
- **source:** first-principles derivation — perturbation bound for one neuron: a flip in row j changes that neuron's output by γ·|x_i| for the flipped input i. If k weights in the same row flip on the same step, the neuron's output jumps by up to k·γ·max|x| in one step — an unbounded, uncontrolled perturbation whose size is set by coincidence, not by evidence. The counter system prices each flip independently; the *function* prices their sum per row.
- **mechanism:** per step, within each output row of each matrix, at most 1 pending flip is applied — the one with the largest |counter overshoot|; other crossing counters in that row keep their (clamped) counts and remain eligible next step. Distinct from the global flip budget (A-017: caps the *total* count, indifferent to where flips land) and block staggering (A-018: rotates by block): this caps *spatial coincidence at the unit whose output actually sums the flips*.
- **train.py:** new flag `--row-flip-cap 1` on Layered (row-wise top-1 selection in the flip application inside `step()`).
- **mode:** process
- **prediction:** -0.01..-0.03 at trial scale; ~0 at probe (coincidences are rare in ~25 steps). Reasoning: simultaneous same-row crossings are most likely exactly when a batch is atypical (correlated gradients push a whole row), i.e. precisely the flips most likely to be noise acting in concert; deferring them by one step costs the true flips almost nothing (their counters persist) and converts a k-fold output jump into k single steps the rest of the network can track.
- **status:** queued
```mill
id: FP-008
mode: process
run: --arm layered_half --rope --row-flip-cap 1
```

### FP-009 · Common-mode rejection: subtract the layer's mean vote before counting
- **source:** first-principles derivation — each step's gradient is computed on ONE batch, so it decomposes as g = ḡ_signal + b_batch + noise, where b_batch is a component shared across many weights of a layer (the batch's idiosyncratic pull: an unusual window moves whole layers coherently). Independent counters integrate b_batch as if it were per-weight signal; over a run, batch common-mode is a random walk added to every counter in the layer simultaneously — correlated counter motion with no per-weight information in it.
- **mechanism:** before counting, the vote stream is centred per layer: instead of counting sign(g_i) for gated weights, count sign(g_i − median_layer(g)) — i.e. a weight votes up only if its gradient pulls up *relative to its layer's typical pull this step*. The gate (on |g|) is unchanged; only the sign reference moves from 0 to the layer median. Distinct from gradient whitening (MILL-232: second-moment normalization in a rotated basis) — this removes the first moment only, in the original basis, at zero extra state.
- **train.py:** new flag `--vote-center` on Layered (median subtraction in `step()` before the sign is taken).
- **mode:** process
- **prediction:** -0.01..-0.04 at probe and trial scale. Reasoning: at batch 32 the batch term is large (it is the dominant correlated noise source in SGD), and the counter — an integrator with a ~32-step memory — is exactly the device most vulnerable to integrating a correlated component: uncorrelated noise averages out over the climb to V, common-mode noise does not, because it pushes the same direction for many consecutive steps whenever similar windows recur.
- **status:** queued
```mill
id: FP-009
mode: process
run: --arm layered_half --rope --vote-center
```

### FP-010 · Cross-layer staleness discount: downstream counters pay for upstream flips
- **source:** first-principles derivation — counters assume a stationary target: counter c in block 2 integrates gradients that were computed *through* block 1's weights. Every block-1 flip changes the function block 2's gradients describe, so a fraction of block 2's banked evidence refers to a network that no longer exists. The staleness of a downstream counter is, to first order, proportional to the upstream flip volume since its evidence was gathered — a quantity the trainer already measures (flip share) and currently ignores across layers.
- **mechanism:** after each step, if block 1's flip share that step exceeds 0.2% of its weights, block 2's counters are discounted once: c ← round(0.75 · c) for both components (a 25% evidence write-down, event-driven, not periodic). Block 1's own counters are never discounted by its own flips (its evidence is about its own inputs, which did not change). At the champion's 2-block depth this is the complete rule; it generalizes to "each block discounts by the product of upstream flip events." Distinct from leak (MILL-209–213: time-driven decay regardless of cause) and comp-reset (A-020: same-weight sibling): this is *cause*-driven decay, priced by measured upstream change.
- **train.py:** new flag `--xstale 0.75` on Layered (cross-block hook after the flip application in `step()`).
- **mode:** process
- **prediction:** -0.01..-0.03 at trial scale; ~0 at probe (flip share rarely crosses the trigger in the first steps). Reasoning: the champion's mean flip share is ~0.11%/step, so the trigger fires on the high-flip tail — exactly the steps after which downstream evidence is stalest. If it never fires at trial either, the entry retires itself with a measurement (cross-layer staleness is negligible at this depth), which is also worth owning.
- **status:** queued
```mill
id: FP-010
mode: process
run: --arm layered_half --rope --xstale 0.75
```

### FP-011 · Dithered gate: randomized median threshold (stochastic inclusion)
- **source:** first-principles derivation — a deterministic threshold applied to a continuous statistic creates a systematic exclusion set: a weight whose |g| sits permanently just below the layer median casts *zero* votes for the entire run, while a weight ε above it votes every step — an infinite evidence ratio for an ε difference in information. Quantization theory's standard fix is dithering: adding noise before a threshold converts a hard exclusion into an inclusion *probability* that is continuous (in fact linear) in the underlying statistic, making the expected vote an unbiased, graded function of |g|.
- **mechanism:** each step, each weight's gate test uses a jittered threshold: it votes iff |g_i| > median_layer · u_i, with u_i ~ Uniform(0.7, 1.3) drawn fresh per weight per step. Weights at the median vote ~50% of steps; at 1.3× median, always; at 0.7×, never. Increments stay exactly ±1 (this is not magnitude weighting) and the strong-side cliff is untouched in form — what changes is that the cliff's *position* is randomized. Distinct from the soft gate (A-001: deterministic continuous increment *above* the median; below-median weights still contribute exactly 0 forever) and from FP-002 (which gives the weak half its own slow counter rather than probabilistic admission to the fast one).
- **train.py:** new flag `--gate-dither 0.3` on Layered (per-step uniform draw in the gate test inside `step()`; own RNG stream per seed-discipline).
- **mode:** process
- **prediction:** -0.01..-0.03 at probe and trial scale. Reasoning: the excluded-just-below-median population is by construction the largest group of near-miss weights in every layer; even a fractional admission rate gives their counters a real (if slower) climb, and stochastic rounding is *unbiased* — unlike the hard gate, it introduces no systematic preference beyond |g| itself. Expected effect is smaller than FP-002's if the weak half's signal is mostly long-horizon; the pair brackets the two ways to recover the same discarded information.
- **status:** queued
```mill
id: FP-011
mode: process
run: --arm layered_half --rope --gate-dither 0.3
```

### FP-012 · Predictive threshold crossing: flip on the counter's extrapolated value
- **source:** first-principles derivation — the counter is an integrator; its recent slope (mean vote over the last k steps) is an independent statistic from its level, and first-passage theory says the optimal decision uses both: a counter at +24 rising at +0.8/step will cross +32 in ~10 steps with high probability, while a counter at +24 falling will not. The champion's rule reads the level only, so it treats these identically — it waits for certainty in cases where the trajectory already carries it, and the wait costs the remaining run length (at ~160 steps, a 10-step delay is 6% of the run, per flip).
- **mechanism:** maintain a per-weight short-window vote mean m (EMA of the vote stream, β=0.8, fp state charged). The flip test becomes: flip when c + τ·m ≥ V (for the + direction; mirrored for −), with τ=8 steps of lookahead. The counter itself, the clamp, and the reset are unchanged — only the crossing test is trend-adjusted (a proportional-derivative rule on top of the integral state). Distinct from EMA evidence (A-011: replaces the vote *direction* with sign(EMA of g)) and from leak (decays the level): here the level is untouched and the EMA is used only to *extrapolate* it.
- **train.py:** new flag `--pred-flip 8` on Layered (EMA buffer + modified flip test in `step()`).
- **mode:** process
- **prediction:** -0.01..-0.03 at trial scale; ~0..-0.01 at probe. Reasoning: the gain is bounded by (flips whose crossing is predictable) × (steps saved) — both modest — but the failure mode is also bounded: a mispredicted flip is one whose counter was within τ·m of threshold on a genuine trend, i.e. a flip that was likely within ~8 steps anyway. The asymmetry (bounded downside, compounding upside from earlier correct structure) is the argument.
- **status:** queued
```mill
id: FP-012
mode: process
run: --arm layered_half --rope --pred-flip 8
```

### FP-013 · Position-information-weighted votes: early positions know less, so they vote less
- **source:** first-principles derivation — causal information content: the gradient contribution of position t is computed from a context of t tokens, so per-position gradient noise scales roughly as 1/√t while the vote path sums all 256 positions' contributions into one gradient and takes one sign — treating position 2 (context: 2 tokens) as an equal witness to position 250. The vote is the trainer component most sensitive to witness quality, because it keeps only the sign of the sum.
- **mechanism:** in the vote path only, the loss is reweighted per position by w_t = log2(t+2)/log2(258) (position 0 ≈ 0.125, position 255 = 1.0) before the backward that feeds the counters; the AdamW parts (embeddings, norms, scales) continue to train on the plain, unweighted loss in a second backward (cost: one extra backward per step, charged honestly — or equivalently a gradient-hook split). Distinct from loss-weighted token votes (A-013 in stream A: weights by the token's *loss value*, a difficulty signal) — this weights by *context size*, a pure information quantity that is independent of the model's current errors and cannot chase its biases.
- **train.py:** new flag `--posw-vote` on Layered (per-position loss weights applied to the vote-path gradient only, in the training loop).
- **mode:** process
- **prediction:** -0.01..-0.03 at probe and trial scale, with the extra-backward cost charged: at equal *minutes* the probe may read flat while winning at equal *steps* — the trial must report both, and adoption requires the per-minute reading to win too. Reasoning: the first ~32 positions are ~12% of every window's vote evidence at the lowest witness quality; down-weighting them raises the SNR of every counter in the network by a few percent, which compounds over the ~32-vote climb to every flip.
- **status:** queued
```mill
id: FP-013
mode: process
run: --arm layered_half --rope --posw-vote
```

### FP-014 · Dithered per-weight thresholds: fixed random V_i ∈ [24, 40]
- **source:** first-principles derivation — first-passage synchronization: with a single global V, weights whose evidence streams are similar cross threshold in *correlated bursts* (the same good/bad batch moves thousands of counters in lockstep), so flip volume per step is far more variable than independent counters would produce — the flip-rate time series inherits the batch stream's variance. Drawing each weight's threshold once, uniformly from [24, 40] (mean 32 = champion), decorrelates crossing times without changing the mean evidence standard: a quantizer-dithering argument applied to the threshold instead of the signal.
- **mechanism:** at init, each weight draws V_i ~ Uniform{24..40} (seeded, fixed for the run); its clamp and flip test use V_i. Nothing else changes. Distinct from per-head temperature spread (A-029: four structured values assigned by head) and per-layer adaptive V (feedback-driven): this is unstructured, per-weight, open-loop heterogeneity whose only job is desynchronization — the control that tells the lab whether *any* V diversity helps, before it invests in principled diversity (cf. FP-004).
- **train.py:** new flag `--v-dither 24,40` on Layered (per-weight threshold array replacing the scalar in `step()`; shares plumbing with FP-004 but no online estimation).
- **mode:** process
- **prediction:** -0.005..-0.02 at probe and trial scale — the smallest expected effect in this file, included because it is the cheapest possible test of threshold diversity and its result disciplines FP-004's interpretation (if random diversity ≈ SPRT diversity, the SPRT estimation machinery earns nothing; if SPRT >> dither, per-weight *information* is the active ingredient). Reasoning: burst decorrelation smooths the structure's effective learning rate across steps, which should help most in the high-flip early phase.
- **status:** queued
```mill
id: FP-014
mode: process
run: --arm layered_half --rope --v-dither 24,40
```

### FP-015 · Warm-started counters: pre-roll evidence at init
- **source:** first-principles derivation — hitting time from a cold start: a counter starting at 0 under drift μ needs an expected V/μ steps to its first flip; at V=32 and the modest drifts typical of real weights, that is a large fraction of a ~160-step run spent with *no structure learning at all* from that weight — yet the information that determines the drift's sign is available at initialization, in the gradient statistics at init, before any flip is allowed to fire. Starting counters at 0 discards a measurable head start that costs only forward/backward passes, not training steps.
- **mechanism:** before step 0, run 32 no-update passes over training windows (offsets() draws, held-safe) at the init model, accumulating each weight's gated votes exactly as `step()` would, then set c_i = clip(accumulated, −16, +16) — at most half of V, so no weight can flip on pre-roll evidence alone; it can only start halfway up the climb it was already going to make. The ternary state is untouched (this is not a state init). Distinct from vote warmup (A-023: delays flips while counters accumulate *live* from 0 — the run still pays the climb in training steps) and from the init entries (A-113/A-114: change the ternary *state*, counters still 0).
- **train.py:** new flag `--counter-warm 32` on Layered/Direct (pre-roll loop in the runner before training; 32 passes charged to wall-clock, ~32 step-equivalents, stated in the record).
- **mode:** process
- **prediction:** -0.01..-0.03 at probe scale, -0.00..-0.02 at trial scale (the head start is a fixed step saving, worth relatively more in a 25-step probe than a 160-step trial — the honest shape of this effect). Reasoning: weights whose init-gradient consensus is strong are disproportionately the weights whose first flip is correct; advancing them ~16 votes converts dead early steps into structure formation, and the ±16 cap guarantees at least 16 live votes still gate every first flip. If init gradients are uninformative about later drift, the pre-roll is pure noise bounded by the same cap, and the probe will show it.
- **status:** queued
```mill
id: FP-015
mode: process
run: --arm layered_half --rope --counter-warm 32
```

---

*End of lens 1. 15 entries (FP-001…FP-015), all first-principles derivations from the vote
mechanism's mathematics: bounded state space (FP-001), discarded-sample information
(FP-002, FP-011), channel bandwidth of identical streams (FP-003), sequential-evidence
units (FP-004, FP-014), state-conditioned gradient distributions (FP-005), encoding
degeneracy (FP-006), the counter as a discarded sufficient statistic (FP-007),
per-neuron perturbation bounds (FP-008), correlated batch noise in an integrator
(FP-009), non-stationarity across layers (FP-010), first-passage prediction (FP-012),
causal witness quality (FP-013), and cold-start hitting time (FP-015).*
