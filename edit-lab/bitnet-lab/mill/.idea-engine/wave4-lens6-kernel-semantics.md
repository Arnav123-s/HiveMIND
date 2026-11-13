# Muse's work — Muse's side

# Wave 4 · Lens 6 — KERNEL-SEMANTICS (rotation-4 miner 6)

Trainer ideas whose mechanism is a **computation structure**: ways of computing the
vote / install / forward that change *what the trainer effectively does*, not just
how fast. Every entry states its gradient/vote path explicitly, because the mill's
kernel benches are forward-only and no kernel is trainer-ready until that path exists.

Chassis for all entries unless stated: `layered_half + rope`, V=32, batch 32 × CTX 256
= 8,192 token positions/step, 884,736 ternary weights (t1 count; ×2 components),
champion held 2.8580 ± 0.0161 at full format, mean flip share ≈ 0.11%/step
≈ 970 flips/step. All entries `mode: process` (code-path changes, isolated probes).

## What the kernel streams already produced — and what it changed here

- `kernels/` (bench_matmul / bench_vote / bench_attention): **no RESULTS file exists**
  (`kernels/RESULTS-KERNELS.md` was never landed). Its variants — direct int32, lut_g4,
  on-the-fly int, fused vote update, complex rotary, manual attention — are already
  pooled as **C-C01..C-C06, all `pending-kernel-results`**, and every one of them is an
  *exact* swap (fused vote update is bit-identical by construction). **None is
  re-proposed here.** Consequence: the fused-update and exact-LUT spaces are closed to
  this lens — a kernel-semantics entry has to change the *rule*, not the implementation.
- `kernels-lut/RESULTS-LUT.md`: correctness **PASS, bit-exact (max abs err 0.0, 50
  checks)**; **timing NOT measured** (deferred under ladder contention, still open).
  Forward-only; its own note states an STE wrapper is required before any trainer use.
  Consequence: an *approximate* LUT can be priced against a proven bit-exact oracle —
  that is what promotes KT-003 into the top 3. No entry in this file borrows a LUT
  speed claim, because none exists.
- `kernels-attn/` (bench_attn / bench_head / bench_quant): scripts only, **no results
  file, no verdicts**. Consequence: KT-008 (attention) is ranked on semantics alone.
- Net ranking effect: with zero timing verdicts anywhere, entries are ranked by
  semantic leverage and decisiveness, not throughput; KT-007 (int8 backward) sits
  below KT-002 because its forward analogue C-C01's speed is still unpriced.

## Dedupe statement

Read in full before writing: `mill/IDEA-POOL.md`, `CANDIDATES-A/B/C/D/E/F/G/H`,
`FABLE-CANDIDATES.md`. Deliberately avoided: C-C01..C-C06 (exact kernel swaps),
B-025..B-030 (T-MAC / TEAL / PowerInfer / Ladder / FLUTE / N:M — inference-kernel
entries), MILL-107/108 (scale granularity), MILL-129/130 (Hadamard, activation
sparsify), MILL-201..203 + MILL-226/227 (magnitude votes, residual accumulators —
different dials from KT-004, see its note), F-007 / G-030 (counter-in-forward
installs), F-017 (TPDF dither at the gate), F-018 (sub-electorate quorum),
F-044 (rotating eligibility), F-045 (sparse counter *storage*), A-002 (per-row
gate), A-016/A-018 (batched / staggered flip application), A-013 (loss-weighted
token votes). Where an entry is a near neighbour, the difference is stated in it.

---

### KT-001 ★ · Vote-then-sum: per-token majority voting (integer vote matmul)
- **source:** kernel-semantics lens — the vote rule re-derived from the shape of the
  backward GEMM itself (`grad_w = upstreamᵀ @ x` is a reduction; the order of
  `sign` and `sum` in that reduction is a free choice the current code makes silently).
- **mechanism:** Cast the vote **per token position first, then sum**: for each weight,
  `v = Σ_t sign(upstream_t · x_t)` over the step's 8,192 positions, computed as one
  int8-sign × int8-sign → int32 GEMM per BitLinear (exact integer arithmetic,
  |v| ≤ 8,192). The counter increments by `sign(v)` only if `|v| ≥ 410`
  (net token majority ≥ 5% of positions); otherwise the weight abstains that step.
  No median gate. t1/t2 arbitration, clamp ±32, reset-on-flip unchanged.
- **exact change:** new flag `--vote-mode tokensum --token-tau 0.05` on `Layered`
  (and `Direct`); the vote path no longer reads `m.weight.grad` for BitLinear weights.
- **semantic difference, plainly:** today a weight's vote is decided by the *summed*
  gradient — one token position with a huge gradient outweighs hundreds of small
  ones (magnitude rules). Here every position gets exactly one vote of equal weight
  and only the majority direction counts (democracy rules). On this corpus that is a
  real change, not a nuance: the ~23% numeric-dump share (E-020) produces outsized
  gradients and currently steers counters out of proportion to its token share;
  under vote-then-sum its influence is capped at its token share, by construction.
- **gradient/vote path:** the FP32 backward still runs for the AdamW parts and for
  `log_scale` (whose grad `(g·t).sum()` is kept from the FP pass, charged honestly —
  so this entry pays one FP backward **plus** one sign-GEMM per layer per step,
  ≈ +1 GEMM against the step's ~3 GEMM-equivalents of BitLinear matmul, i.e.
  roughly +15–20% step time in GEMM terms, likely less end-to-end in torch).
  Counters consume only the integer vote matmul's output.
- **prediction:** quality −0.02..+0.06 at equal steps (the wide band is honest: if
  magnitude information is doing real work, this loses; if outlier positions are
  doing damage, it wins). Detectability arithmetic: per-token sign agreement p
  gives E[net] = 8192·(2p−1), σ ≈ √8192 ≈ 91; τ=410 admits only weights with
  p ≳ 0.55 sustained — a *stronger* evidence bar than one median-gated sign, so
  expect flip share to fall ~30–50%; if it falls >70%, τ is the binding constraint
  and the dose variant τ=0.02 is the follow-up. Throughput −10..−20% (extra GEMM).
  Distinct from A-004 (sign of the batch-mean = today's rule), A-013 (loss-weighted
  FP sum — magnitudes kept), F-018 (4 sub-batch FP signs + per-step quorum; here
  8,192 persistent per-position votes summed into the counter stream).
- **status:** queued

### KT-002 ★ · Lane-local gate: the median is computed per 32-weight SIMD lane
- **source:** kernel-semantics lens — the median gate is the one operation in
  `Layered.step` that is a *global, layer-wide reduction*; it is what stops the vote
  update from being a pure elementwise/SIMD kernel. This entry chooses the vote
  rule that vectorizes, and says what that costs semantically.
- **mechanism:** Weights are viewed in row-major lanes of 32 consecutive fan-in
  elements (one wide vector). The gate threshold is the median |g| **within the
  lane** instead of within the layer: `strong = |g| ≥ median_lane(|g|)`, computed
  on the reshaped `[..., 32]` tensor with no cross-lane communication. Vote,
  clamp, flip, reset otherwise unchanged.
- **exact change:** new flag `--gate lane32` on `Layered`/`Direct`.
- **semantic difference, plainly:** today ~50% of a *layer* votes, but they are
  whichever weights happen to sit in the layer's hot regions — a quiet output row
  may contribute almost no voters for long stretches. Lane-local gating forces
  **every 32-weight segment to contribute exactly ~16 voters every step**: flip
  pressure is equalized across the whole matrix by construction, and a weight now
  competes with its 31 fan-in neighbours instead of with the layer. Evidence
  becomes a local contest, not a global one.
- **gradient/vote path:** unchanged FP32 backward; only the gate statistic's
  reduction scope changes, inside the existing vote update (composes with the
  C-C04 fused kernel rather than competing with it — the fused kernel gets
  *simpler*, since its one global reduction disappears).
- **prediction:** throughput +0..+2% end-to-end (the vote update is a few percent
  of step time per C-C04's own accounting; the win is kernel simplicity, not
  seconds). Quality −0.03..+0.03. The decisive value is diagnostic: if lane32 ≈
  champion, gate *scope* is free and every future fused kernel can drop the global
  median permanently; if it wins outright, local competition was the active
  ingredient. Sibling control: A-002 (per-row gate, 192–768 wide) — lane32 is the
  sub-row point on the same scope dial, and the pair brackets where scope stops
  mattering.
- **status:** queued

### KT-003 ★ · Clipped-partial LUT forward: the error budget is a trainer variable
- **source:** kernel-semantics lens, built directly on `kernels-lut/RESULTS-LUT.md`:
  the exact LUT is proven bit-identical (err 0.0), so an *approximate* LUT's error
  can be priced exactly, against an oracle, per step.
- **mechanism:** LUT g=4 forward as in the bench (81-entry tables per activation
  group of 4), except table entries are stored **clipped**: a group partial sum
  (exact range ±508 in activation-code units) is saturated at ±L, with L annealed
  508 → 160 over the run. The trainer logs the measured forward error vs the exact
  LUT each 100 steps (max and RMS per output), so the error budget ε(L) is a
  measured quantity, not an assumption. Saturated groups contribute exactly ±L
  regardless of how large their true partial was.
- **exact change:** new flag `--fwd lutclip --clip-anneal 508:160` in
  `BitLinear.forward` for the vote arms, behind the STE wrapper the LUT stream's
  own note requires (below).
- **semantic difference, plainly:** the forward is no longer the ternary matmul
  the weights describe — activation groups with very large partial sums are
  *softly clipped inside the sum itself*. A weight fed by outlier-heavy inputs
  has its forward contribution capped per group, so the network the loss is
  computed on is a mildly outlier-suppressed version of the installed network,
  with the suppression strength (L) as an annealed trainer hyperparameter —
  an approximation treated as a mechanism, in the family of activation clipping
  (cf. MILL-129's Hadamard motivation) but arising from table storage, at the
  group level, and priced exactly.
- **gradient/vote path:** as RESULTS-LUT.md requires, the LUT forward carries no
  autograd path to the weights, so a straight-through wrapper is added: backward
  passes the upstream gradient to the counters (vote arms) as if the clipped LUT
  forward were the identity-quantized forward — the same detach trick
  `BitLinear` already uses. Honest consequence: vote evidence is computed *at
  the clipped forward*, so weights feeding saturated groups receive attenuated,
  biased evidence — that bias is the mechanism under test, and WH-043's
  gradient-noise tolerance curve is the prior for how much bias is free.
- **prediction:** error arithmetic: real activations are absmax-scaled, so most
  |x| are far below 127; a 4-group partial is a sum of 4 products of a ternary
  sign with such codes, typical |partial| ≈ 30–80, so L=160 saturates only the
  outlier tail (est. <2% of groups late, more early before the anneal bites).
  Worst-case per-output error at K=192 (48 groups) is bounded by
  Σ_sat (|partial| − L) and is *measured*, with kill line: mean RMS error
  >5% of mean |Y| (≈ 886 code units at champion shapes → RMS budget ≈ 44)
  retires the anneal point. Quality −0.01..+0.04; throughput **unclaimed** —
  LUT timing was never measured (deferred in RESULTS-LUT.md) and the torch
  gather path is expected to lose to BLAS; this entry is bought for its
  semantics and its exact error ledger, and any future native kernel inherits
  both.
- **status:** queued

### KT-004 · Int8 backward for the vote path: evidence on an integer lattice
- **source:** kernel-semantics lens — C-C01 proved the *forward* integer path is
  exact; this entry asks what happens when the *backward* weight-gradient GEMM
  is integer too, which is not exact, and says so.
- **mechanism:** For each BitLinear, the weight gradient is computed as
  `grad_w = upstream_qᵀ @ x_q` in int32, where `upstream_q` is the upstream
  gradient quantized per token-row to int8 by absmax (the same quantization the
  forward already applies to activations) and `x_q` is the forward's saved int8
  activation codes. The activation-gradient path to earlier layers stays FP32,
  so the distortion is applied per layer independently and does not compound
  through depth. The vote (sign + median gate) reads this integer gradient.
- **exact change:** new flag `--bwd int8` on `Layered`/`Direct` (custom autograd
  function for BitLinear weight-grad only; STE arms excluded — their latent
  weights need the FP gradient this entry deliberately destroys).
- **semantic difference, plainly:** vote evidence gains an **absolute floor**:
  an upstream contribution below 1/127 of its row's max contributes exactly
  zero, where today it contributes its true small FP value. And all magnitudes
  land on an integer lattice — ties at the median become common, so the gate's
  `≥` admits a tie-block whose size varies step to step. The gate stops being
  purely relative-to-the-layer and becomes partly absolute (row-max-relative).
- **gradient/vote path:** this entry *is* the gradient path: exact integer
  accumulation (max |sum| = 8192·127·127 ≈ 1.3×10⁸ < 2³¹ ✓), quantized inputs.
  `log_scale` grad keeps the FP `(g·t)` value from a shadow FP grad_w computed
  only as a scalar reduction — no: charged honestly, log_scale grad is computed
  from the integer grad_w as well (`(g_int·t).sum()`), a second, smaller bias
  that the entry accepts and the probe's log_scale trajectory will show.
- **prediction:** quality −0.01..+0.03 (WH-043's premise — sign votes tolerate
  large gradient perturbations — predicts near-flat; the lattice/tie effect is
  the risk). Throughput unpriced: the int32 GEMM's speed vs FP32 on this
  2-thread box
...[truncated 12507 chars]  is exactly what C-C01's still-missing timing would have told us; this entry
  must not be probed until that bench lands or it runs its own paired timing.
  Ranked below KT-002 for precisely that reason.
- **status:** queued

### KT-005 · Counter-proximate sparse backward: the grad_w GEMM only computes near-flip weights
- **source:** kernel-semantics lens — the backward's grad_w GEMM computes a
  gradient for every weight every step, but the vote trainer can only *use*
  evidence at weights whose counters are within reach of a flip.
- **mechanism:** grad_w is computed only for output columns whose weight has
  |c1| ≥ 16 or |c2| ≥ 16 (either component within half of V=32), plus a rotating
  5% audit slice of all remaining weights (hash-rotated per step). All other
  weights get grad exactly 0 that step: no vote, counter unchanged. The mask is
  recomputed from the counters each step (one comparison pass, no GEMM).
- **exact change:** new flag `--bwd-sparse prox --audit 0.05` on
  `Layered` (column-masked grad_w; grad_x path untouched and full — earlier
  layers still receive complete signal).
- **semantic difference, plainly:** evidence allocation becomes
  *state-dependent and positively reinforcing*: weights near a flip get full
  evidence every step; weights at c ≈ 0 are blind except when the audit slice
  visits them (expected revisit every ~20 steps), so a weight whose true
  gradient reverses while it sits at zero waits, on average, 20 steps to even
  start its 32-vote climb. The trainer develops a rich-get-richer evidence
  economy that today's uniform backward does not have.
- **gradient/vote path:** vote rule, gate, clamp, flip all unchanged — what
  changes is *which weights receive a gradient at all*. AdamW parts and
  log_scale (a scalar reduction over the computed columns only — noted as a
  small bias: log_scale grad misses the masked columns' `(g·t)` mass) as
  described.
- **prediction:** arithmetic depends on the counter distribution, which the
  probe must report: if ~25% of weights qualify + 5% audit, the grad_w GEMM
  (⅓ of BitLinear matmul FLOPs: fwd 1, grad_x 1, grad_w 1) drops to ×0.30,
  i.e. ~23% off backward matmul, ~15% off step matmul — in torch, with mask
  overhead, honestly 0–10% end-to-end. Quality +0.00..+0.04 at equal steps
  (the cold-population cost), possibly net-negative at equal minutes if the
  step saving doesn't materialize. Distinct from F-044 (eligibility rotates
  uniformly by hash, state-blind, and *pauses counters*; here eligibility is
  counter-driven and grad_x is never masked) and F-045 (counter *storage*
  eviction; nothing here is evicted).
- **status:** queued

### KT-006 · Block-sparse flip application: a block installs when 2 of its weights are pending
- **source:** kernel-semantics lens — `install()` currently rewrites all
  884,736 FP weights every step to apply ~970 flips (0.11%); the computation
  structure (dense install) forces flips to be temporally uniform, which is a
  semantic choice nobody made deliberately.
- **mechanism:** Counters update every step exactly as now, but a threshold
  crossing only marks the flip *pending* (direction recorded, counter reset as
  usual). Installed weights live in 128-weight blocks (6,912 blocks at
  champion); when a block accumulates ≥2 pending flips, all its pending flips
  install in one scatter pass and only that block's slice of the installed
  buffer is recomputed. Blocks below the trigger keep serving their old values.
- **exact change:** new flag `--install block-sparse --block 128 --block-k 2`
  on `Layered` (pending bitmask + direction arrays: +2 bits/weight state,
  charged).
- **semantic difference, plainly:** the installed network lags its own counters
  by a block-dependent delay, and flips land in **spatially correlated bursts**
  instead of a uniform drizzle. A block with diffuse, slow evidence waits
  longer (its flips integrate more counter cycles before acting); a hot block
  installs almost immediately. That is a per-block adaptive effective
  threshold implemented purely as an install-scheduling rule.
- **gradient/vote path:** backward and votes run against the *installed*
  (lagged) weights — gradients are honest gradients of the network actually
  being served, which is one step more principled than it sounds: today the
  same is true with a lag of exactly one step for every weight; here the lag
  varies 1..~15 steps by block. Counters keep counting against the lagged
  forward throughout.
- **prediction:** delay arithmetic: ~970 flips/step over 6,912 blocks ≈ 0.14
  pending/block/step → mean wait to k=2 ≈ 14 steps (Poisson; hot blocks much
  less, cold blocks much more — the spread is the mechanism). Install write
  traffic: install events/step ≈ 970/2 ≈ 485 blocks × 128 = ~62k weights
  ≈ 7% of the current full install — a ~14× cut in install writes, worth
  maybe +1–3% end-to-end. Quality −0.01..+0.05; the burst/delay interaction
  with F-010's staleness concern is the named risk. Distinct from A-016
  (global 8-step batching — a *time* trigger hitting all blocks at once),
  A-018 (rotating block schedule), F-008 (per-row cap of 1 flip/step — a
  *limit*, not a trigger; unchosen flips there stay counted, here they are
  recorded and certain to land).
- **status:** queued

### KT-007 · Stochastic-rounding int8 gradient accumulation across micro-batches
- **source:** kernel-semantics lens — gradient accumulation is normally a
  pure batching trick; at int8 accumulator precision it stops being one.
- **mechanism:** The batch of 32 is run as 8 micro-batches of 4. Weight
  gradients accumulate in an **int8 fixed-point accumulator** (1 byte/weight)
  with stochastic rounding: per layer, quantum q = mean|g|/16 measured on
  micro-batch 1; each micro-gradient is added as round_sr(g_micro / q),
  saturating at ±127q. After 8 micro-batches, one vote is cast from the
  accumulator (sign + median gate on accumulator magnitudes, as today) and
  the accumulator zeroes.
- **exact change:** new flag `--accum sr8 --micro 8` on `Layered`/`Direct`
  (accumulator replaces the FP32 grad buffer for BitLinear weights only;
  AdamW parts keep normal FP accumulation).
- **semantic difference, plainly:** the vote sees a *temporally quantized*
  gradient. A weight with a persistent micro-gradient of 0.4q accumulates
  ≈ 3.2 quanta over the step in expectation — stochastic rounding is
  unbiased, so weak-but-steady evidence survives; under deterministic
  rounding (or under today's median gate applied per micro-batch) it would
  vanish. Conversely a single bursty micro-gradient saturates at 127q and
  cannot dominate the sum the way an FP outlier can. Precision becomes a
  vote-shaping choice: the accumulator is a low-pass, outlier-clipping
  evidence filter that happens to be 1 byte wide.
- **gradient/vote path:** votes consume only the int8 accumulator; this is a
  within-step structure (the accumulator never carries across steps).
  Distinct from MILL-226 resid8 (a *cross-step* residual in a different
  trainer arm whose crossings flip weights directly — no vote, no gate) and
  F-017 (TPDF noise added once to the full-batch gradient before the gate —
  no accumulation, no saturation, no micro structure) and A-100 (FP
  accumulation ×2 — exact batching, no precision change).
- **prediction:** memory: grad buffer for ternary weights drops 4 B → 1 B
  (884,736 × 3 B ≈ 2.7 MB — small, stated honestly). Throughput ~neutral in
  torch (8 smaller backwards may even lose); the claim is semantic.
  Quality −0.02..+0.02. Its real product is a measurement: if int8-SR
  accumulation is flat vs FP, the vote path provably needs almost no
  gradient precision, which licenses KT-004's integer backward and any
  future low-precision kernel; if it loses, the loss localizes *where*
  precision matters (temporal integration, not the sign).
- **status:** queued

### KT-008 · Quantized-probability attention: softmax output snapped to a 1/256 grid
- **source:** kernel-semantics lens — a fixed-point attention pipeline
  (uint8 probabilities feeding an int8 PV product) is the computation
  structure a CPU kernel wants; this entry prices what it does to the model.
- **mechanism:** Attention runs in the explicit form (the C-C06 structure,
  which exists as a bench) with one change: after softmax, probabilities are
  rounded to multiples of 1/256 and **not** renormalized (row sums land in
  [1−δ, 1], δ measured and logged). P is stored uint8; the PV product reads
  the quantized P. Everything else — RoPE, ternary projections — unchanged.
- **exact change:** new flag `--attn qsoftmax` in `Block.forward` (vote and
  STE arms both; it is a forward-structure change, trainer-agnostic).
- **semantic difference, plainly:** attention becomes **exactly sparse at
  the tail and coarse at the head**: any probability < 1/512 rounds to
  exactly 0, so barely-attended tokens contribute *nothing*, not a little;
  a probability of 1/256 carries up to 50% relative error, while p > 1/8 is
  accurate to <2%. The head's output is a quantized mixture — the attention
  distribution the rest of the network sees is a different, peakier
  distribution than the logits describe.
- **gradient/vote path:** straight-through on the rounding (gradients flow
  as if P were unquantized), Q/K gradients computed from the quantized P —
  so vote evidence for the qkv/out projections is evidence about the
  quantized-attention network, consistently with KT-003's principle that
  the gradient belongs to the forward actually run. AdamW parts unaffected
  structurally.
- **prediction:** arithmetic: at CTX 256, uniform attention is p = 1/256 —
  exactly one quantum — so early-training, near-uniform heads are maximally
  distorted (entries snap to {0, 1/256, 2/256}); peaked heads barely notice.
  Expect quality +0.00..+0.05 early, shrinking as head entropy falls; the
  probe must log per-head entropy beside held loss or the number is
  uninterpretable. Throughput ~0 claimed at CTX 256 (attention is a small
  share; C-C06's manual form is expected *slower* than SDPA) — this is a
  semantics probe whose value grows with context length, bought cheap now.
  Not covered by B-023 (sigmoid attention — different function, not a
  quantized softmax) or any pooled entry.
- **status:** queued

### KT-009 · Stale-forward pipelining: votes are cast on last step's weights
- **source:** kernel-semantics lens — every pipelined kernel design (install
  overlapping the next forward) secretly assumes one-step-stale gradients
  are free; nobody in the pool has priced that assumption.
- **mechanism:** Two installed buffers ping-pong. Step k's forward and
  backward run against the weights installed at the end of step k−2's vote
  update — i.e. `t_fwd` lags the voting state `t_cur` by exactly one step.
  Votes from g(t_fwd) update t_cur's counters under the unchanged rule.
- **exact change:** new flag `--fwd-lag 1` on `Layered` (+1 installed-buffer
  copy: 884,736 × 4 B ≈ 3.5 MB, charged).
- **semantic difference, plainly:** every vote is evidence about the
  *previous* network. Today a weight's counter integrates gradients of a
  network that contained its own current value; here it integrates gradients
  of a network one flip-generation older. At 0.11% flip share, t_fwd and
  t_cur differ in ~970 weights — the bias is small, but it is *systematic*
  exactly at the weights that just flipped (their freshest evidence describes
  the value they just left).
- **gradient/vote path:** gradients are exact gradients of t_fwd (no STE
  fiction); the staleness is in *which* network they describe, and the
  counters absorb it untreated — that untreated absorption is the thing
  being priced.
- **prediction:** quality −0.005..+0.01 (expected near-flat; staleness-1 is
  the gentlest point on the curve). Throughput on this serial VM ≈ the
  install share only (+1–2% at best, stated honestly) — the entry's product
  is the price tag: if lag-1 is free, KT-006's variable block lags and any
  future async kernel are licensed; if it is *not* free at this tiny
  staleness, F-010's staleness-discount family gains a measured foundation
  (F-010 *responds* to staleness by discounting counters; this entry
  *creates* a controlled dose of it — opposite sides of the same variable).
- **status:** queued

### KT-010 · Shard counters with agreement merge: two half-batch evidence streams
- **source:** kernel-semantics lens — the data-parallel kernel form (two
  independent counter streams, one merge) applied to the trainer's state.
- **mechanism:** The batch splits into two halves of 16 windows. Each half
  keeps its **own counter pair** (cA, cB per component), updated by its own
  half's gated votes each step. A flip fires only when sign(cA) == sign(cB)
  for that component **and** |cA + cB| ≥ 32; on a flip both shard counters
  reset. State cost: counters double (2 B → 4 B per component-pair per
  weight, charged).
- **exact change:** new flag `--shards 2` on `Layered`.
- **semantic difference, plainly:** a flip needs *sustained agreement between
  two independent data halves*, not just a large total. Under today's single
  counter, one atypical half-batch (say, all numeric-dump windows) can push
  a counter most of the way to a flip in a few steps; here the other shard's
  counter refuses to corroborate and the flip cannot fire, however large
  the sum grows. Evidence becomes a two-witness rule.
- **gradient/vote path:** two half-batch backwards (or one backward with
  per-half gradient hooks — implementation choice, cost charged either way:
  gradient materialization ×2 for BitLinear weights). Votes, gate, and
  arbitration within each shard are the champion rule verbatim.
- **prediction:** flip rate falls (agreement is a stricter bar than the
  sum): expect flip share −30..−60% and quality −0.01..+0.04 at equal steps
  — the bet is that the flips removed are the batch-composition artefacts.
  Throughput −5..−15% (extra gradient handling). Distinct from F-018
  (3-of-4 *per-step sign* quorum over 4 sub-electorates, no persistent
  per-shard state — a weight can flip there on one step's majority; here
  each shard must independently accumulate ≥ ~16 net votes, a *temporal*
  two-witness rule).
- **status:** queued

### KT-011 · Int8 body→head path: the head reads a quantized residual stream
- **source:** kernel-semantics lens — the head matmul (`body @ tok.weight.T`,
  FP, over a 192–512-dim body) is the one large matmul in the model whose
  *input* is never quantized; the kernels-attn stream's head bench exists
  because this path is a major cost share at ladder shapes.
- **mechanism:** The body output is quantized per token to int8 by absmax
  (the BitLinear activation quantizer, reused verbatim) before the head
  matmul; logits = int32(body_q @ W_tokᵀ) × (body_scale × 1) with W_tok the
  FP tied table cast to int8 codes per row with per-row scales — no: kept
  honest and simpler: body_q int8 × FP table via the C-C01-style integer
  path is impossible against an FP table, so the head runs
  `F.linear(body_q · body_scale, W_tok)` — the *input-side* quantization is
  the whole change; the table stays FP and AdamW-trained.
- **exact change:** new flag `--head int8body` in `Tiny.next_piece`
  (training and held eval both — it is the served function too, and is
  charged as such).
- **semantic difference, plainly:** the head stops distinguishing body
  vectors that differ by less than one activation quantum (top/254 per
  element): logit resolution is capped, and embedding rows receive gradients
  that are piecewise-constant in the body — two nearby hidden states that
  quantize identically produce *identical* embedding gradients. The output
  layer's effective input alphabet becomes finite (256 levels × dim), where
  today it is continuous.
- **gradient/vote path:** STE through the body quantization (identity
  backward), exactly as BitLinear treats its activations; the vote arms'
  counters are untouched structurally, but their final-layer evidence now
  arrives through the quantized head's backward — the entry is judged on
  the full model, not the head alone. Distinct from MILL-118 (quantizes the
  *table's storage* to INT8, body stays FP — the complementary operand) and
  WH-014 (table itself vote-trained ternary).
- **prediction:** logit error arithmetic: per-element body error ≤ top/254,
  RMS ≈ top/(254·√3); over dim 192 with table rows of norm ~√192·σ_w, logit
  RMS error ≈ 1–3% of typical logit spread — expect quality +0.00..+0.03.
  Throughput: the FP GEMM remains (only its input is pre-quantized), so
  ~0 claimed; the entry prices the *input* side so a future integer head
  kernel knows which operand's precision is free to cut.
- **status:** queued

### KT-012 · Nibble-packed counters: c1 and c2 share one byte, V forced to 7
- **source:** kernel-semantics lens — the bit-packed counter update the
  territory names, with its semantic price stated instead of hidden: packing
  two int4 counters into one byte with saturating nibble arithmetic is the
  update a SIMD kernel can do in a single op, and it *cannot* represent
  V=32.
- **mechanism:** c1 and c2 are stored as the two nibbles of one uint8 per
  weight (offset-binary, range −7..+7 each). One packed add + nibble-mask
  saturation updates both counters per step; the flip test reads nibbles
  at |c| ≥ 7. Everything else (gate, vote, t1-priority, reset) unchanged.
- **exact change:** new flag `--pack nibble` on `Layered` (implies V=7;
  counter state 2 B → 1 B per weight).
- **semantic difference, plainly:** versus the champion this is **not** an
  implementation of the same trainer: the evidence horizon collapses from
  32 net votes to 7, so at equal drift a weight flips ~4.6× sooner, and the
  two components' counters now saturate independently at ±7 — long,
  slow-building evidence for a flip is *unrepresentable*, not just slower.
  Versus simply running int8 counters at V=8 (MILL-502's grid point), the
  difference is only the packing and V=7 vs 8 — stated plainly so the entry
  is judged as what it is: the V≈7 point *plus* a halved counter footprint,
  inseparable in this form.
- **gradient/vote path:** unchanged FP backward and vote computation; only
  the counter storage/arithmetic changes — this is the one entry whose vote
  path needs no wrapper, and the one whose adoption case rests entirely on
  the packed kernel existing (a torch probe measures the *semantics* of
  V=7-with-nibble-saturation; the speed belongs to a future native kernel
  and is claimed here only as state traffic: counter reads/writes halve,
  ≈ 1.8 MB/step saved at champion — under 1% of step traffic, honestly
  negligible at this scale, material at 50M where counters dominate).
- **prediction:** quality: read against MILL-502 (V=8) — expected within
  ±0.01 of it, i.e. likely worse than V=32 champion by whatever the V-grid
  says 8 costs; the probe is worth running only paired with MILL-502 so the
  packing itself is isolated. Ranked last: smallest semantic delta in the
  file, included because the territory names the mechanism and its honest
  price (V is not a free parameter once counters are packed) belongs on
  record before any kernel work assumes otherwise.
- **status:** queued

---

*Closing note on scope:* every entry above changes what the trainer computes —
a vote statistic, a gate scope, a forward function, an evidence stream, an install
schedule, a state representation. The exact kernel swaps (C-C01..C-C06) and the
literature kernel entries (B-025..B-030) remain the pool's speed lane and are
untouched by this file; several KT entries (KT-002, KT-004, KT-007) are designed
to become *more* attractive, not less, if those benches ever land their missing
timing verdicts.
