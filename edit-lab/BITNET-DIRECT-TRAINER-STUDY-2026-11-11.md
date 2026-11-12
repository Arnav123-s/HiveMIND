> **Muse's work** — written by Muse, on Muse's side. Fable's HiveMIND was read read-only; nothing on Fable's side was touched.

# Fable's Direct BitNet Trainer — Study and Improvement Assessment

**Date:** 2026-11-11 · **Scope:** Muse's side only. The audit copy (`~/workspace/fable-audit-copy`,
make-it-work @ c254975) was read, never written. Nothing here touches Fable's side.
**Question (Arnav):** Fable built a way to train BitNets *directly* — not by converting ordinary
weights. How does it work, can Muse improve it, and is there possibly a better mechanism entirely?

---

## 1. The mechanism, exactly

There are **three** direct mechanisms in the repo, not one. Two live in `training/scratch.py`
(stem-cell scale), one in `training/body.py` (cell scale).

### 1.0 The shared setting

- The model is `scratch.Tiny`: a 4-layer transformer, dim 192, vocab 4096, context 256 —
  **2.6M weights total**, of which the three-valued (BitLinear) layers hold ~1.8M. The rest —
  word-piece table, position table, norms, biases — is ordinary and shared by all cells.
- A `BitLinear` layer (`scratch.py:67`) at work is: every weight ∈ {−1, 0, +1} × **one learned
  number per layer** (the scale); activations are rounded to 8 bits per token. Forward uses a
  straight-through trick: the rounding is applied with the correction detached, so autograd
  produces a gradient *as if* no rounding had happened, evaluated **at the current
  three-valued point**.
- Loss is ordinary next-piece cross-entropy on the hive's harvested text (48 MB; 14.5M pieces),
  batch 32 windows. (`pretrain_direct` can optionally mix in a teacher's KL term; no recorded
  vote run used it.)

### 1.1 Direct v1 — stochastic jumps (dead end, kept in code)

`scratch.Direct` with `votes=0` (`scratch.py:155`, step at `:226`). The weight tensor itself is
only ever a carrier: after `install()` it always holds exactly `t · scale`, where `t` is the
stored three-valued state. Each step:

1. Backprop the loss through the STE forward; read each layer's gradient `g`.
2. For each weight, the candidate is `want = t − sign(g)` (one step toward lower loss), and it
   jumps with probability `rate · |g| / mean|g|` over the layer.
3. `rate` anneals linearly to 1/20 of its start over the run (`pretrain_direct`, `scratch.py:285`).

Measured (commit `add5984`, README): three rates gave **4.237–4.293** against **4.241** with no
jumps at all — *the jumps taught nothing on real text*. Per-step coin flips have no memory: a
weak-but-steady pull is indistinguishable from noise, because nothing adds the evidence up.

### 1.2 Direct v2 — the vote counter (the real invention)

`scratch.Direct` with `votes=V` (`scratch.py:167–224`; commits `6249578`, `9711292`). Per
three-valued weight, the entire training state is:

- `t` ∈ {−1, 0, +1} — the weight itself;
- `count` — an **int8 counter**, clamped to ±V (at V=32 it needs ~6 bits);
- `last` — one int8 sign (only used by the `agree` variant);
- plus, per *layer* (not per weight), one fp number: `log_scale`, trained by AdamW through the
  hand-set gradient `(g·t).sum() · scale`.

Each step (`scratch.py:205–224`):

1. Backprop as above → gradient `g` per layer.
2. **Strong gate:** a weight may vote only if its |g| is in the layer's stronger half —
   `|g| ≥ median(|g|)` (the `strong` parameter moves the quantile; 0.5 is the median).
3. **Vote:** `vote = −sign(g)` for strong weights, else 0. (With `agree=True`, the vote counts
   only if it matches last step's pull for that weight.)
4. **Accumulate:** `count ← clamp(count + vote, −V, +V)`. (With `leak=k`, every k steps every
   counter first moves one step toward 0.)
5. **Flip:** when `|count| ≥ V`, the weight jumps one value in the counter's direction —
   `want = t + sign(count)` — and its counter **resets to 0**. Weights at ±1 whose counter
   points outward don't move (`want ≠ t` check).
6. Everything not three-valued (embeddings, norms, biases, the per-layer scales) is trained by
   ordinary AdamW (lr 1e-3, betas 0.9/0.95) in the same step; then `install()` rewrites each
   layer's tensor as exactly `t · scale`.

So: **the gradient's role is reduced to a signed ballot; the counter is an integer evidence
integrator; V is the learning rate** (flips per unit of accumulated evidence); there is no
momentum term as such — accumulation *is* the momentum, in integer form. The flip pace is set
entirely by V and the evidence rate; the `rate` argument of v1 is ignored in vote mode.

**Measured** (README "Training a BitNet directly", HANDOFF.md:332–334; 8-minute runs, one random
start, same text; the figure is the harness's recorded loss — mean training loss over the last
100 steps, `pretrain_direct`'s `_record`):

| way | loss |
|---|---|
| no three-valued weight ever moves | 4.241 |
| v1 stochastic jumps, 3 rates | 4.237 – 4.293 |
| **votes: 4 / 8 / 16 / 32 / 64 to jump** | **4.667 / 4.450 / 4.181 / 4.141 / 4.174** |
| published way (STE, ordinary weights underneath) | 4.031 |

At the best setting (32 votes) the counter captures **about half the published way's gain**
(4.241→4.141 = 0.100 of 4.241→4.031 = 0.210). Their own summary: *"votes work … and
nothing-at-all-underneath does not."*

**State cost, the actual point of the design:** STE training keeps, per ternary weight, an fp32
latent weight + two AdamW moments ≈ **12 bytes**. The vote way keeps **1 byte** of counter (2
with `agree`) — for 1.8M ternary weights ≈ 3.6 MB vs ≈ 21.6 MB of optimizer state, and the
stored model is the training state (2 bits/weight packed, 0.61 MB/cell vs 10.5 MB).

### 1.3 The cell-scale sibling — `_flip_read` (measured greedy flips)

`training/body.py:414` (commit `b67aad4`), registered as body trainers t5/t6. No counters, no
per-step updates — **batched coordinate descent with a holdout referee**:

1. Accumulate gradients over 4 batches.
2. Rank every weight by |g| among those whose one-step flip `t − sign(g)` changes them; flip
   the top `share` (default 0.2% of all weights) **at once**.
3. Measure loss on check windows the cell never trains on (every 10th of its territory, ≤96).
   Better by >1e-4 → keep; not better → **undo all of it and halve the share**.
4. Stop when time is up or `share · total < 20`. A round costs ~6 passes; ordinary reading
   costs ~1000 steps.

Record so far: *"has only run in a toy test"* (HANDOFF) plus one real birth — the first
flip-grown cell was **removed at birth** by the body's gate (commit `cb4862e`; `body.json`:
t6 births 1, kept 0).

### 1.4 How it differs from the two things it is not

**(i) Conversion** (`scratch.to_bitnet`, `scratch.py:364`): take the *already-trained fp stem
cell* (loss 2.70), keep its fp weights as latent state, switch the forward to three values, and
read on for 30 minutes so it adapts. Result **2.70 → 3.02** — the conversion tax. Nothing is
trained from scratch; the ternary net is a compressed fp net, and the fp original is kept
(`base_full.pt`). The direct way never has an fp net to convert: it starts from random
three-valued weights.

**(ii) The published BitNet way (STE + latent weights)** (`scratch.BitLinear` + AdamW): the
weight that is *stored* is fp32; each step it is rounded for the forward pass and the gradient
updates the fp original, so a weight can sit at 0.49 for a thousand steps accumulating tiny
updates before its rounded value changes. The latent copy is exactly "what the stored copy was
for" (Direct's docstring). The vote way replaces that fp accumulator with a 6-bit integer one
and throws away gradient *magnitude* per weight (only the sign votes, and only from the
stronger half). Everything the hive actually serves is still trained the published way — the
vote way is in the code (`scratch.py direct --votes 32`) but is **not** the production trainer.

---

## 2. Its limits — from their own records

1. **Half the gain, at one scale, in short runs.** All vote numbers are 8-minute runs, one seed,
   one start, at the 2.6M stem-cell shape. Their own caveat: *"Short runs: they rank the ways,
   they do not say where each ends."* The vote way has **never** been run at founding length
   (40 min), never at any other size, never with a second seed.
2. **The comparison's settings are not fully recorded.** The runs' record files are not in the
   repo, and `pretrain_direct` does not pass its `lr` argument to `Direct` — so in vote mode the
   shared (non-ternary) parts always trained at lr 1e-3, while the recipe sweep
   (`bitnet_recipe.json`) later showed lr 3e-3 + warmup + easing is worth ~0.2 for the STE way
   (4.2315 → 4.0220 at 600 steps, held loss). How much of the 4.141-vs-4.031 gap is mechanism
   and how much is recipe is **not separable from the record**. Any re-run must be
   recipe-matched before it says anything about the mechanism.
3. **The three variants were judged on confounded runs.** `agree` (votes must repeat), `leak`
   (counters forget), and a stricter voting threshold scored **4.28–4.38, none better than plain
   32 votes (4.141)** — but README itself notes *"those runs shared the CPU and took fewer
   steps, so they are not a clean comparison."* At the noise level of a last-100-step training
   loss, differences of ±0.03–0.1 in that table are not decisions; they are suggestions.
   (Today's `gate_noise` measurement on their side prices this: a 60-passage gate difference
   carries a standard error of ~0.0035, and their own recipe7 sets the bar at >2 sd **and**
   >0.01 — the variant table meets neither standard.)
4. **Non-monotone in V, with no adaptation.** 64 votes (4.174) is worse than 32 (4.141): too
   little evidence and noise flips weights; too much and learning crawls within the budget. V
   is one global constant for all layers and all phases of training — no schedule (contrast:
   v1's rate annealed; the STE recipe's lr warms up and, per today's trace, badly wants a
   cool-down), and no per-layer setting, although layers differ widely in gradient distribution.
5. **Magnitude blindness, by construction.** A vote is ±1 whether the gradient is barely past
   the median or a hundred times it. The median gate is a hard cliff: a weight just under the
   median contributes nothing that step, however consistent its pull. And when a flip fires, the
   counter resets to 0 — overshoot evidence (a pull strong enough to have earned two flips) is
   discarded.
6. **No check that a flip helped.** Votes trust accumulated gradient signs; nothing ever
   measures the result of flipping (contrast `_flip_read`, which measures everything and
   learns nothing between rounds). The two mechanisms are complementary and have never been
   combined.
7. **Never used where it would compound.** Direct-by-votes exists only for stem pretraining.
   Cells are grown by STE or by flips. Distillation into a vote-trained net (the harness
   supports a teacher term) was never run. Neither was votes on the third body's clean data
   regime (the vote runs predate the held-window fix in `scratch.offsets` — same-start/same-text
   comparisons still rank fairly, but the absolute numbers are of the old regime).

---

## 3. Improvement candidates for the vote counter (Muse's side)

Common experiment discipline for all of them (this is what Fable's runs lacked, and what
recipe7 on their side now does right): same random start, same batch order, **3 seeds**,
**recipe-matched** (non-ternary parts at the winning recipe settings), judged on **held loss**
(the 96 held passages + the 352-passage gate split), at **equal steps and equal wall time**,
win bar = better than the plain-32-votes mean by >2 sd and >0.01. Reference points: plain
32 votes = 4.141 (their measure), published way = 4.031, no-jumps = 4.241. Each arm is an
8-minute run ≈ 10 min of solo VM time; a 6-arm × 3-seed sweep ≈ 3 h; founding-length
confirmation (40 min × 2 arms × 2 seeds) ≈ 3 h. Implementation is a variant of
`scratch.Direct.step` in Muse's own copy — under a day each.

### C1 — Magnitude-weighted votes (confidence-weighted evidence integrator) ★ top candidate
- **Changes:** the counter accumulates a *clipped magnitude*, not a bare sign:
  `count += clip(round(−g / mean|g|), −3, +3)` for every weight (no median gate), counter in
  int16 or fixed-point, threshold scaled to match (e.g. ±96 ≙ 32 unit votes).
- **Why it should help:** it removes two of the mechanism's three known information losses at
  once — equal-evidence (a pull 10× the layer mean counts ~3×, not 1×) and the median cliff
  (weak pulls still count, proportionally). What the latent fp weight does in STE is precisely
  "accumulate signed magnitudes"; this keeps that signal but quantizes the *accumulator* to
  ~8–11 bits instead of keeping a 32-bit weight + 64 bits of Adam state. The vote counter is
  the 1-bit-evidence point on a dial; this tests the 2-bit-evidence point on the same dial.
- **Proving experiment:** arms = plain-32 vs C1, recipe-matched, 3 seeds × 8 min. **Kill** if
  C1's held loss is not ≤ plain-32's by the win bar; **proven** if it closes ≥half the
  remaining distance to the STE arm run in the same sweep.

### C2 — A schedule on the threshold (votes cool-down)
- **Changes:** V anneals over the run (e.g. 8 → 64, flips get rarer and more certain late),
  mirroring v1's rate anneal and the STE lr schedule. Optionally per-layer: V scaled so each
  layer's flip rate tracks a common target (~0.1–0.3% of weights/step).
- **Why:** today's one-model trace (§5) shows a stem founded hot and never cooled leaves ~0.24
  of loss on the table that six low-rate minutes recover — the single largest cheap effect in
  the whole repo this week. The vote runs' fixed V spends the whole run at one temperature;
  64-votes-being-worse is exactly what a too-cold *start* predicts, and 4-votes-being-worse a
  too-hot one. A schedule gets both ends.
- **Experiment:** plain-32 fixed vs V: 8→64 linear vs V: 16→48; same sweep as C1. Kill if
  neither schedule beats fixed-32 by the bar.

### C3 — Fractional leak (true momentum on the vote stream)
- **Changes:** replace the integer lockstep leak (every k steps, all counters −1 toward 0 —
  the variant that "failed") with a per-step fractional decay `count ← 0.98·count + vote`
  in fixed point. That is a leaky integrator = exponential momentum over sign evidence.
- **Why:** the published theory of sign methods says accumulation order matters — signSGD
  fails to converge in cases where **sign descent with momentum** provably converges
  (Safaryan & Richtárik, ICML 2021), and error-feedback is the known repair for sign
  compression's bias (Karimireddy et al. 2019; 1-bit Adam, Tang et al. 2020). Fable's leak
  test was the crudest possible decay (integer, synchronized, and run under CPU contention —
  limit #3), so the idea is *not* refuted by their record; it was never cleanly tried.
- **Experiment:** leak ∈ {none, 0.99, 0.98, 0.95} at V=32-equivalent, equal steps (not just
  equal minutes — the fix for their confound). Kill if the best leak ≤ plain by the bar.

### C4 — Flip bookkeeping: hysteresis + thrash freezing
- **Changes:** keep one extra int8 per weight: a flip-history counter. A weight that flips
  ≥k times within a window is **frozen at its modal value** for the rest of the run (or its
  personal threshold doubles). Overshoot is no longer discarded either: on flip, keep
  `count − sign·V` instead of resetting to 0 (one-line change, test separately).
- **Why:** oscillation around a threshold is *the* documented pathology of low-bit training
  (Nagel et al., ICML 2022: latent weights oscillating between grid points measurably degrade
  accuracy; their fixes — dampening and **iterative freezing of frequent oscillators at their
  most frequent state** — were state of the art at 3–4 bits). A vote-trained net has the same
  disease in discrete form: weights near a decision boundary flip back and forth, spending the
  flip budget on noise. Freezing converts their wasted flips into stability.
- **Experiment:** plain-32 vs plain-32+residual-keep vs plain-32+freeze; log flip counts per
  weight (the diagnostic is nearly free and itself tests the pathology's size at this scale).

### C5 — Hybrid phases (votes where they're strong, STE where they're strong)
- **Changes:** two-phase run: votes from random init for the first ~70% (cheap state, big
  structural moves), then *materialize* latent weights at `t·scale` and finish with STE at a
  low rate (the cool-down phase). Or the reverse order as a control.
- **Why:** votes' weakness is fine convergence (unit steps, sign-only evidence); STE's weakness
  is cost and early oscillation. The phases attack different regimes. This also concedes the
  honest point (§6): if the last stretch needs the latent copy anyway, the claim shrinks to
  "votes are the better *early* trainer" — worth knowing exactly, either way.
- **Experiment:** votes-8min vs STE-8min vs votes-5.6min+STE-2.4min, all recipe-matched,
  3 seeds. The hybrid wins only if it beats *both* pure arms by the bar.

### C6 — Votes + measurement (marry the counter to `_flip_read`)
- **Changes:** run votes as the engine, but periodically (every N steps) spend one round of
  `_flip_read`-style verification on the *pending* flips: weights whose counters are near
  threshold get their candidate flips ranked by measured Δloss on a check batch, and only
  verified ones fire early.
- **Why:** votes never check a flip helped (limit #6); flips never accumulate evidence
  (rounds are memoryless). Each covers the other's hole. Cost: a few extra passes per round.
- **Experiment:** later — only if C1/C2 show the counter itself is worth keeping. (Sequencing
  matters: don't engineer the hybrid before the base mechanism is de-confounded.)

---

## 4. Alternatives — could something else beat both STE and votes?

Arnav's addition: *"There might be a better way to it — the idea is good, something that might
work better."* Surveyed against the vote counter's three structural weaknesses: **(W1)** all
evidence counts equally (sign only), **(W2)** flips are all-or-nothing unit steps with no
knowledge of how much the other state would help, **(W3)** nothing measures whether a flip
actually helped. (STE's weaknesses, for symmetry: 12 bytes/weight of state, biased gradient,
threshold oscillation.)

### A1 — Annealed stochastic flips (Metropolis on the ternary lattice) ★ most principled repair
- **Mechanism:** keep the ternary state and the same backward pass. For each weight compute the
  first-order estimate of the loss change from flipping, `ΔL̂ ≈ g·(w_new − w)·scale` — free,
  from the gradient already computed. Flip with probability `min(1, exp(−ΔL̂/T))`, temperature
  T annealed over the run. Improving flips are near-certain, worsening flips happen early
  (exploration) and vanish late.
- **Fixes:** W1 (evidence is a *magnitude* — the estimated loss change itself), W2 (a flip's
  probability is proportional to how much it should help), and the temperature replaces both
  the rate schedule (v1) and the threshold V (votes) with one principled knob. It is what v1
  was reaching for: v1 flipped with probability ∝ |g| but with **no acceptance test and no
  temperature**, i.e. it accepted worsening flips at a constant rate forever — and measured
  exactly nothing learned. The acceptance test is the difference between noise and annealing.
- **Evidence:** stochastic ternarization has precedent (Ternary Connect, Lin et al. 2015,
  sampled weights from per-weight probabilities during training); simulated-annealing training
  of binary nets is repeatedly reported competitive at small scale but slow. No published
  result at LM scale. Repo evidence is v1's failure — which this mechanism specifically
  explains and repairs.
- **Head-to-head:** A1 vs plain-32 vs C1, same sweep as §3 (equal steps, 3 seeds, held loss).
  Kill if A1 ≤ plain-32 by the bar — its extra machinery must pay rent immediately.

### A2 — Per-weight probability state with an unbiased estimator (ARM / DisARM family)
- **Mechanism:** each weight carries a small fp state — two logits giving a probability over
  {−1, 0, +1}. Each step, sample the ternary weights, and update the logits with the
  **DisARM** estimator (Dong et al. 2020; Yin & Zhou's ARM/U2G): an *unbiased*, low-variance
  gradient for discrete variables built from antithetically coupled samples (two forward
  passes with mirrored randomness). Anneal the probabilities toward determinism; the final
  net is the per-weight argmax.
- **Fixes:** STE's bias (the estimator is unbiased for the *expected* loss under the sampling
  distribution, not a pretend-gradient) and W1/W2 (the state is a real confidence: a weight
  at 51/49 explores, at 99/1 is settled — exactly the "votes for direction + separate
  confidence state" hybrid, except the confidence is trained, not counted).
- **Costs/evidence:** ~2 forward passes per estimate (~2× step cost — at CPU prices this is
  the whole ballgame), and 8 bytes/weight of state: more than votes (1), less than STE (12).
  ARM/DisARM beat REINFORCE and relaxation baselines on discrete latent-variable benchmarks;
  never tried for ternary LM pretraining at any scale. This is the strongest *published*
  alternative estimator family, and the least tried in this setting.
- **Head-to-head:** A2 vs STE at **equal wall time** (not equal steps — its 2× pass cost must
  be charged), 8 min, 3 seeds. It wins only if it beats STE's held loss outright; a tie loses,
  because STE is simpler and already in production.

### A3 — The dial itself: quantized residual (error feedback in higher precision)
- **Mechanism:** per weight, keep an int8/fp16 *residual* `r`: each step `r += −lr·g`;
  whenever `r` crosses ±scale, flip the weight one step and subtract the quantum from `r`.
  This is error-feedback (the repair the sign-compression literature converged on: EF-signSGD,
  Karimireddy et al. 2019; 1-bit Adam keeps error feedback + moments and matches Adam) applied
  to the *state* instead of the gradient.
- **Fixes:** W1 entirely (full magnitude evidence, integrated exactly), and the counter-reset
  evidence loss (the residual *is* the overshoot). Honest framing: **votes and STE are two
  points on one dial — the precision of the per-weight accumulator** (votes = 1-bit evidence,
  int8 counter; A3 = 8–16-bit residual; STE = 32-bit latent + moments). C1 (§3) is the 2-bit
  point on the same dial. The research question is not "votes or STE" but "where on the dial
  does the loss stop improving" — and nobody, in the repo or the literature, has mapped that
  curve for ternary training.
- **Head-to-head:** the dial sweep itself: evidence ∈ {sign (votes), 2-bit (C1), int8
  residual (A3), fp32 (STE)} at matched everything. Whichever point first reaches within
  noise of the fp32 point *is* the best known direct trainer, by construction.

### A4 — Zeroth-order / evolution in discrete space (TerMeZO, QES, ES) — right tool, wrong job
- **Mechanism:** no backprop at all. Perturb weights (TerMeZO: sparse perturbations of the
  latent weights nearest their ternary thresholds; QES: evolution strategies directly on
  quantized weights, with — notably — *accumulated error feedback*; classic ES: population of
  perturbed models, fitness-weighted update), estimate direction from forward passes only.
- **Fixes:** the entire gradient apparatus (no STE bias, no backward memory) and works
  natively in discrete space. But per-weight signal per FLOP is far worse than one backward
  pass — at 2.6M weights from scratch this is not competitive for *pretraining*, and the
  evidence agrees: TerMeZO (Sifaou et al.) fine-tunes 1–3B BitNets, QES fine-tunes quantized
  LLMs, ES-at-scale (Qiu et al., ICML 2026) fine-tunes with populations of 30 — **all
  fine-tuning, none from-scratch**. Where it fits is exactly where `_flip_read` already lives:
  growing/adjusting an existing cell, where the search is local and a holdout can referee.
- **Head-to-head:** for cell growth only: flip-rounds (A5) vs sparse-ZO rounds at equal wall
  time on one territory, judged by the body's own local gate. Not a stem-pretraining arm.

### A5 — Measured greedy flips, grown up (Fisher-ranked `_flip_read`) ★ best cell-scale bet
- **Mechanism:** `_flip_read` with two upgrades: rank candidate flips not by |g| alone but by
  estimated loss change with a curvature penalty — `ΔL̂ ≈ −g·Δw − ½·F̂·(Δw)²`, where `F̂` is a
  diagonal Fisher estimate accumulated from squared gradients (nearly free: one more
  accumulator, the same trick as Adam's second moment) — and spend the round's budget in
  *verified batches with restarts*, keeping the holdout referee and share-halving.
- **Fixes:** W2 and W3 directly: flips are chosen by how much they should help *and* kept only
  if they measurably did. This is the OBS/GPTQ lineage (second-order, one-shot) made iterative
  and honest. Repo evidence: `_flip_read` exists and is mechanically sound, but has had
  exactly **one** real trial (removed at birth — which is the gate working, on a sample of
  one, for a trainer whose share schedule starts at 0.2% with no ranking beyond |g|).
- **Head-to-head:** A5 vs t1 (ordinary STE cell growth) on the same territory at equal minutes,
  judged by `judge_local`. Also A5 vs votes is *not* the comparison — they operate at
  different scales (growth vs pretraining); forcing one would repeat Fable's confound error.

### A6 — Local learning rules (Forward-Forward, feedback alignment) — surveyed, ranked last
- **Mechanism:** replace global backprop with per-layer local objectives (Hinton's
  Forward-Forward: two forward passes, layer-local "goodness" losses) or fixed random
  feedback paths (DFA).
- **Honest assessment:** these change *where the signal comes from*, not *how discrete weights
  absorb it* — a local gradient still needs an accumulator (votes or latent) underneath, so
  they compose with the counter rather than replacing it. Published evidence at LM scale is
  absent, DFA is known to lag backprop as scale grows, and next-token prediction decomposes
  awkwardly into layer-local goodness. Included for completeness; **not** a recommended arm.
  If ever tried, the cheap version is DFA-into-the-vote-counter on one layer group, as a
  diagnostic, not a contender.

### A7 — Oscillation freezing as an add-on (not a standalone trainer)
Nagel et al.'s iterative freezing (track per-weight flip frequency; freeze frequent
oscillators at their modal state) is mechanism-agnostic: it layers onto votes (C4), STE, or
A1 at the cost of one int8 per weight. Given the published size of the oscillation effect at
low bit-widths, any winner from §3/§4 should be re-run +frozen before being declared final.

---

## 5. From Fable's latest trace — better ideas

The four commits after d31fd51 (`88deeee`, `af45ccb`, `292a48f`, `c254975`, all 2026-11-11
evening / 11-12), read in full. None of them touches the vote counter — but the trace points
at it, and past it, in several places.

### What Fable tried, and what it measured

1. **One model vs a body, at equal minutes** (`one_model.py`, `one_model_b3.json`). B3's stem
   cell, reading on alone at the low rate for the 60 minutes its six cells had together:
   yardstick 3.1146 → **2.7827**; the body with its six cells: **2.7806**. All-text: 2.9954 vs
   2.9863. **A tie** — with a fifth of the weights and one model awake instead of five. Two
   confessed causes: (a) the stem was founded hot (lr 3e-3) and never cooled — it gained 0.08
   in the first 6 low-rate minutes, and ~0.24 is available from cool-down alone; *"most of
   what b3's cells add to their stem cell is that and not their territories"*; (b) for the
   first body, whose stem *had* slowed, ten cells genuinely add 0.16 — composition pays only
   after the base is finished improving cheaply.
2. **recipe7** (`training/experiments/recipe7.py`, written, **results still running** — no
   result file in the repo yet): the built-in recipe from **three starts** (to price chance;
   a change must beat the base mean by >2 sd **and** >0.01), then one change at a time:
   lr **cool-down** in the second half (to 1/10, to 1/100 — motivated by finding 1a), **Muon**
   (Newton–Schulz-orthogonalized momentum) for the three-valued layers, a **low-rank fp side
   term** beside every ternary layer (rank 4/8, +~20% disk at rank 4), plus recipe6's arms
   (batch 16/8, RoPE, ReLU², RMSNorm, small-init output layers, QK-norm). Winners are then run
   together and, if they hold at founding length (40 min), built into `scratch.py`/`NEW_BODY`.
   Every run is also read at its **running-mean weights** (EMA readout).
3. **The birth gate's noise, priced** (`gate_noise.py`, in `88deeee`): a newborn must gain
   0.004 on 60 passages; the standard error of such a gain is **0.0035** — the bar is ~1 SE,
   so *"a newborn that adds nothing passes now and then by luck."* Of 6 gated living cells, 3
   add nothing distinguishable from zero on report passages. Also found: the yardstick's
   passages stop at window 47,880 of 56,542 — the last seventh of the text (all Wikipedia) was
   invisible to it; body 1 reads 2.4856 on the yardstick vs 2.7062 on all-text passages.
4. **The speed table** (`cpu_speed_result.json`): a from-nothing BitNet trains at 11,221
   pieces/s at 2.6M weights on 4 cores; 3,576 at 12M; 1,675 at 27M; 591 at 88M. (At the
   runner ration below, the 88M would need ~150,000 days to read what the one strong published
   BitNet read — the honest scale wall for from-nothing training.)
5. **His answer, and the ration** (`292a48f` HANDOFF; `c254975`): Arnav approved the proposed
   direction *"only if it improves"*, with the explicit rider that **BitNets themselves — how
   they are made and trained — are to be improved, not merely used as-is** — which is precisely
   this study's mandate. Separately, GitHub Actions' proportionality terms cut the hive's
   runner turns to **one growth turn + one exam a day**: compute is now rationed on their
   side, which raises the value of training-state economy (the vote counter's whole pitch).

### Better ideas the trace suggests for Muse's side

- **B1 — Cool-down is a first-class schedule, including for votes.** Fable found the effect on
  the STE side (hot founding, no cooling, 0.24 recoverable) and is now testing lr cool-down in
  recipe7. The vote counter has the exact analogue untested: **anneal V upward late** (C2).
  Muse's side can run this before Fable's recipe7 even reports — and, more generally, adopt
  the rule the trace teaches: *never credit a composite/birth/trainer gain until the base has
  had its cool-down* — add an equal-compute, cooled-incumbent control to the growth gate's
  audit, so Muse's births are not credited with the parent's unfinished cooling (the b3
  confound, imported as a gate repair).
- **B2 — Price your gates before you trust your tables.** The gate-noise measurement (bar ≈
  1 SE) retroactively underpowers several of Fable's own verdicts — including "no vote variant
  beats plain 32" (§2, limit 3). Muse-side rule, adopted in §3's discipline: every comparison
  ships with its standard error and a >2 sd + >0.01 bar (recipe7's standard), and every gate
  states its SE. Cheap, immediate, and it changes which results are believed.
- **B3 — Muon for the ternary layers, and its vote-side analogue.** recipe7 tries
  orthogonalized momentum on the *latent* weights. The vote-side translation: the gradient
  field that feeds the counter could be **whitened per layer** before signing (the counter
  then integrates evidence in a rotated basis where directions are balanced) — speculative,
  one arm. The plain version is directly usable: Muse's factory STE arms can test Muon as an
  optimizer swap under the existing gate, at near-zero implementation cost.
- **B4 — The low-rank side term is a serving-format idea, not just a training one.** A ternary
  layer + rank-4 fp patch costs ~20% more disk and (if recipe7 confirms the gain) buys back
  part of the ternary accuracy tax. For Muse's ternary specialists, "ternary + low-rank
  patch" is a candidate *serving* format to be judged by the battery gate exactly like the
  existing ternary singles — the trace suggests the format; Fable is only testing it as a
  training recipe.
- **B5 — Modal-state readout (the discrete EMA).** recipe7 reads every run at its running-mean
  weights — an average the vote-trained net cannot take, since its states are discrete. The
  discrete analogue exists and is untried anywhere in the repo: keep the last k checkpoints'
  ternary states and read out the **per-weight modal (majority) state** — a variance cut that
  pairs naturally with C4's freezing (Nagel's freezing is the same idea, applied during
  training). Nearly free to test on any vote run: save t every 50 steps, evaluate the modal
  readout alongside the final state.
- **B6 — Report cost in two currencies.** With turns rationed (their side) and one heavy job
  at a time (Muse's side), "loss at equal minutes" is only half the ledger. The vote
  counter's real claim is loss **per byte of training state** and per watt-hour on a small
  machine. Muse-side experiments should publish both — at 88M weights the state difference
  (12 B/w vs 1 B/w) is the difference between fitting and not fitting, and the cpu_speed table
  is the reminder that scale is where the direct trainer's argument actually lives. A single
  12M-weight arm in the §3 sweep tests whether votes' relative gain holds or grows with size;
  at 2.6M, where everything fits, STE's advantage is free and the comparison is at its most
  unfair to votes.

---

## 6. Verdict

**Is Fable's the best known way to train BitNets directly? Split the question:**

- **Best way to train a BitNet, full stop:** still the **published STE way** — Fable's own
  hive trains everything that serves by it, it won the only head-to-head on record
  (4.031 vs 4.141), and at full length its recipe line reaches 2.9288 (40 min, held) with **no
  direct-training number anywhere near that regime to compare against**. Anyone claiming a
  direct trainer "beats STE" today is claiming past the evidence.
- **Best way with nothing underneath (the actual invention):** the **vote counter**, and it is
  not close — it is the only mechanism in the repo or the surveyed literature that learns
  *at all* with ~1 byte of per-weight state (v1's memoryless jumps measured exactly nothing).
  QES/TerMeZO keep latent weights or fp residuals; ARM/DisARM keep fp logits; STE keeps the
  fp weight itself. The counter is the extreme point of the accumulator-precision dial (A3),
  and it demonstrably works.

**Is it improvable? Yes — plainly, and the improvements are specific, not hopeful.** The
mechanism as shipped discards gradient magnitude (W1), gates evidence with a hard median
cliff, saturates and resets its counters, runs one global threshold with no schedule, and was
never (a) recipe-matched, (b) run past 8 minutes, (c) run with a second seed, or (d) cleanly
compared against its own variants. Its three "failed" variants were judged on confounded runs
by a standard its own side has since shown to be ~1 standard error. A mechanism cannot be
called tight when its ablations were never cleanly run. The ordered path:

1. **De-confound first** (recipe-matched, 3 seeds, held metric, equal steps): re-measure plain
   32 votes. The 4.141 reference itself may move.
2. **C1 magnitude-weighted votes** — the top improvement candidate; it tests the 2-bit point
   on the accumulator dial, where the STE gap should shrink most per added bit.
3. **C2 threshold schedule (cool-down)** — backed by the largest cheap effect in Fable's
   latest trace.
4. **A1 annealed flips** as the genuinely different mechanism in the same sweep — it is the
   principled repair of v1's measured failure.
5. **B5 modal readout + C4 freezing** as nearly-free add-ons to whichever arm wins.

**Where the honest doubt sits:** STE's latent weight is *strictly more informative* than any
small counter — it integrates exact magnitudes with per-weight adaptive scaling (Adam). At
2.6M weights on a machine where that state costs 22 MB, votes are solving a problem that does
not bind, and may never beat STE on loss at this scale no matter how well they are tuned. The
vote counter's winning conditions are the ones Fable built it for and the trace keeps
reinforcing: **state economy at scale** (1 B/w vs 12 B/w), a training state that *is* the
shipped model, and rationed compute on small machines. So the final verdict:

> **Improvable — yes. Already beaten by something else — no. Proven better than the published
> way — no, and not yet fairly tried.** The best known direct trainer is Fable's vote counter,
> improved along C1/C2 and re-measured under recipe7-grade discipline; the best known BitNet
> trainer overall remains STE, and the two meet on the accumulator-precision dial (A3), whose
> curve nobody has mapped. Mapping it — at 2.6M and at 12M — is the experiment that settles
> Arnav's question for real.

---

### Sources
Repo (`~/workspace/fable-audit-copy` @ c254975): `training/scratch.py` (BitLinear :67, Direct
:154–232, pretrain_direct :235, to_bitnet :364), `training/body.py` (_flip_read :414, TRAINERS
:536), `training/reports/bitnet_recipe.json`, `training/experiments/{recipe7.py,
one_model_b3.json, cpu_speed_result.json, gate_noise.py}`, README "Training a BitNet directly"
+ "Measured: the hive's own BitNets", HANDOFF.md:330–345 and the 2026-11-11/12 sections;
commits `add5984`, `6249578`, `9711292`, `b63c9f6`, `b67aad4`, `cb4862e`, `88deeee`, `af45ccb`,
`292a48f`, `c254975`.
Literature: Wang et al. 2023 / Ma et al. 2024 (BitNet b1.58); Lin et al. 2015 (Ternary
Connect); Bernstein et al. 2018 (signSGD); Karimireddy et al. 2019 (error feedback);
Tang et al. 2020 (1-bit Adam); Safaryan & Richtárik 2021 (stochastic sign descent with
momentum); Nagel et al. 2022 (oscillations in QAT, dampening & freezing); Yin & Zhou 2019
(ARM); Dong et al. 2020 (DisARM); Sifaou et al. (TerMeZO); Cognizant AI Labs (QES);
Qiu et al. 2026 (ES at scale); Hinton 2022 (Forward-Forward).
