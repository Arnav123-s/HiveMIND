# CANDIDATES-A — idea-mining stream A for the mill pool (Muse's work, Muse's side)

<!-- Muse's work — Muse's side of the BitNet lab. Generated 2026-11-12 by research
department stream A under Arnav's mass-testing directive. This is a CANDIDATE file:
nothing here is in the pool until the pool's owner merges it. IDEA-POOL.md was read
in full and NOT edited. -->

## Method and de-duplication

Read before generating: the lab's RESULTS files (2026-11-11 sweep, ROPE, HALF-CONTROL,
ROUND2, JEPA), `BITNET-DIRECT-TRAINER-STUDY-2026-11-11.md`, the 2026-11-12 architecture
research report, `FABLE-STUDY-2026-11-11.md`, and the whole existing pool
(`mill/IDEA-POOL.md`, MILL-000 + 175 entries).

**Zero-duplicate rule applied.** Nothing below restates a pooled MILL entry or a closed
arm. Closed and never re-proposed: overshoot carry, AdamW two-stage cooldown on the
layered chassis, threshold annealing 8→64, magnitude votes as specified (±96), the JEPA
objective, magnitude votes at full size as specified. Pooled families deliberately NOT
re-generated: V grids, gate-q grids, flip arbitration (counter/t1-first/sign-agree/
alternate), counter clamps, fractional/integer leak, thrash freezing, modal readout,
calibrated magnitude votes (half size), vote-threshold schedules 32→64/96 and 24→48,
per-layer flip-rate V, hybrids by phase, annealflip, DisARM, resid8/16, fisherflip,
verify-flips, whitening, low-rank side terms, ease-in, opt-lr points, polish, component
counts 1/3/4/5 and per-component V pairs, failweight sampling, QK-Norm (pre-RoPE),
gated attention, sink logit, scale granularities, two-stage STE, FP-first splits, KD,
DeltaNet/RWKV hybrids, embedding int8/untie, MoE forms, MTP extra heads, Muon, SubLN,
norm removal, Hadamard, act-sparsify, QK-Clip, partial RoPE, NoPE, SwiGLU control, SWA,
norm families, GQA/MQA/head counts, RoPE bases 500/50000, FFN widths/activations, quant
functions, init stds, shape grid, batch grid, STE recipe grid. Also excluded per the
research report's do-not-test list (MLA/NSA/DSA/CSA, MoD, mHC, A4 activations, FP4/FP8,
quantized recurrent state, ultra-sparse MoE, packing/kernel-only ideas, ladder rungs).

**Chassis** unless an entry says otherwise: layered_half + rotary, V=32, gate q=0.5,
the lab's standard probe format. **Cost key:** *cheap probe* = fits the standard
~75-second probe unchanged in shape; *full trial only* = machinery or budget makes a
probe reading uninformative, send straight to 3 seeds × 8 min if merged.

---

## S1 — Vote accounting and evidence shaping

### A-001 · Soft gate (continuous evidence weighting)
- **mechanism:** a vote's increment scales continuously with how far |g| exceeds the layer median (0 at the median, 1 at 2× median) instead of the hard pass/fail cliff.
- **flag-level change:** new flag `--soft-gate` on Layered/Direct (replaces `--gate-q` step function).
- **why it might win:** the study names the hard median cliff as a core defect of the shipped mechanism; calibrated magnitude votes (pooled) change increment SIZE by gradient size in fixed steps — this removes the cliff itself while keeping increments ±1-shaped.
- **cost:** cheap probe.

### A-002 · Per-row gate (gate scope = output neuron)
- **mechanism:** the gate quantile is computed per output row of each matrix instead of per layer, so rows with small gradient scales still get their stronger half counted.
- **flag-level change:** new flag `--gate-scope row` alongside `--gate-q`.
- **why it might win:** per-layer gating silently disenfranchises low-scale rows; their weights then flip on stale evidence. Row scope is the granularity fix one level down from the pooled per-layer threshold idea.
- **cost:** cheap probe.

### A-003 · Batch-aggregated votes (one vote per 4 micro-batches)
- **mechanism:** gradient signs accumulate over 4 micro-batches and each weight casts a single vote from the accumulated sign, so votes reflect batch-level consensus instead of single-batch noise.
- **flag-level change:** new flag `--vote-every 4` on Layered/Direct.
- **why it might win:** at batch 32 the per-step sign is a noisy witness; the counter's whole job is evidence integration, and pre-aggregating raises the evidence quality per count rather than the count rate.
- **cost:** cheap probe.

### A-004 · Vote statistic: sign of batch-mean gradient
- **mechanism:** the vote direction is sign(mean gradient over the batch) rather than the summed per-sample signs (mean-of-signs) the counter effectively integrates.
- **flag-level change:** new flag `--vote-stat batchmean`.
- **why it might win:** mean-of-signs lets a majority of tiny gradients outvote a few large correct ones; the two statistics disagree exactly on the contested weights, and only one has ever been run.
- **cost:** cheap probe.

### A-005 · Deadband with active forgetting
- **mechanism:** gradients below 0.25× the layer median cast no vote AND pull the counter one step toward zero — non-evidence actively erases stale conviction instead of merely pausing it.
- **flag-level change:** new flag `--deadband 0.25` on Layered.
- **why it might win:** counters currently hold early convictions indefinitely through quiet periods; a deadband is the standard control-theory fix and is distinct from leak (which decays regardless of evidence).
- **cost:** cheap probe.

### A-006 · Two-counter race (sustained-evidence flips)
- **mechanism:** separate up and down counters per weight; a flip needs net ≥ V AND total votes ≥ 2V, so a weight cannot flip on a short one-sided burst.
- **flag-level change:** new flag `--race` on Layered (int16 counters ×2).
- **why it might win:** net-only accounting can't distinguish 32-for/0-against from 500-for/468-against; the second is a contested weight whose flip is a coin toss. The race prices contestedness.
- **cost:** cheap probe.

### A-007 · Hysteresis band on levels (sticky ±1)
- **mechanism:** leaving 0 for ±1 costs the full V, but returning from ±1 to 0 costs only V/2 of contrary evidence — earned levels are sticky, unearned ones are cheap to try.
- **flag-level change:** new flag `--hyst 0.5` on Layered/Direct.
- **why it might win:** study candidate C4 pairs hysteresis with thrash freezing, but only freezing was pooled; hysteresis is the half that acts BEFORE oscillation starts, by making the 0↔±1 boundary asymmetric.
- **cost:** cheap probe.

### A-008 · Thrash tax (per-weight adaptive threshold from own flip count)
- **mechanism:** after each flip, a weight's personal V multiplies by 1.5, decaying back toward the global V over ~200 steps; chronic flippers need progressively stronger evidence but are never frozen outright.
- **flag-level change:** new flag `--thrash-tax 1.5` on Layered.
- **why it might win:** freezing (pooled) is a hard stop after k flips; a tax is the soft version — it preserves the option value of a genuinely contested weight while damping the documented oscillation pathology.
- **cost:** cheap probe.

### A-009 · Zero-state bias (sparsity pressure through the counter)
- **mechanism:** votes that move a weight TOWARD 0 count 1.5×; votes away from 0 count 1× — a sparsity prior expressed inside the vote accounting.
- **flag-level change:** new flag `--zero-bias 1.5` on Layered/Direct.
- **why it might win:** the ~42% zero fraction is load-bearing for BitNet quality (built-in feature selection) and the current mechanism reaches it only as a by-product; pricing zero-ward evidence higher tests whether more deliberate sparsity helps at fixed size.
- **cost:** cheap probe.

### A-010 · Layer-normalized vote increments (fixed V, equal flip pressure)
- **mechanism:** each layer's increments are rescaled so every layer expects the same flip share per step, while V itself stays the global 32 — normalization on the evidence, not the threshold.
- **flag-level change:** new flag `--vote-norm` on Layered.
- **why it might win:** the pooled per-layer-V entries adapt the threshold to hit a flip-rate target; this reaches a similar equalization by the dual route and the two need not agree — the comparison itself is informative about which quantity should be equalized.
- **cost:** cheap probe.

### A-011 · Momentum-filtered evidence (EMA-signed votes)
- **mechanism:** the vote direction is the sign of a per-weight EMA of gradients (β=0.9); the counter, gate, and threshold are untouched — momentum filters the EVIDENCE instead of decaying the counter.
- **flag-level change:** new flag `--vote-ema 0.9` on Layered/Direct.
- **why it might win:** the pooled leak family decays accumulated counts; nothing has smoothed the incoming stream. Sign-of-EMA is the direct transplant of why momentum helps signSGD-style updates, at 4 B/weight of fp state (charged honestly).
- **cost:** cheap probe.

### A-012 · Agreement-weighted votes (fast/slow EMA)
- **mechanism:** two gradient EMAs (β=0.5 and β=0.99) per weight; when they agree the vote counts 2, when they disagree it counts 1 — agreement amplifies, never vetoes.
- **flag-level change:** new flag `--vote-ema2` on Layered.
- **why it might win:** the pooled `--agree` retest gates votes OFF on disagreement (Fable's form); weighting instead of gating keeps weak evidence flowing while still pricing multi-timescale consensus — a genuinely different rule.
- **cost:** cheap probe.

### A-013 · Loss-weighted token votes
- **mechanism:** each token position's contribution to a weight's vote is weighted by that token's current loss, so the positions the model gets wrong drive the discrete structure.
- **flag-level change:** new flag `--tokw-loss` in the training loop (per-position loss weights into the vote path only; the AdamW parts keep the plain loss).
- **why it might win:** failweight (pooled) reweights whole WINDOWS in the sampler; this is the finer, per-position form inside the vote mechanism itself, and it leaves the shared parts' training distribution untouched.
- **cost:** cheap probe.

### A-014 · Shared counter across layered components
- **mechanism:** one counter per weight serves both ternary components; when it crosses V the flip is spent on the cheaper component first (t2 until it saturates, then t1).
- **flag-level change:** new flag `--shared-counter` on Layered.
- **why it might win:** separate counters can push t1 and t2 in cancelling directions (the arbitration entries only govern simultaneous crossings); a shared evidence stream makes cancellation impossible by construction and halves counter state.
- **cost:** cheap probe.

## S2 — Flip rules and state dynamics

### A-015 · Probabilistic flip on threshold crossing
- **mechanism:** when |count| crosses V the weight flips with probability |count|/(2V) (counter resets either way) — deep conviction flips surely, marginal conviction flips sometimes.
- **flag-level change:** new flag `--flip-prob` on Layered (needs the int16 counter path, no overshoot retention).
- **why it might win:** overshoot carry (deterministic retention of leftover evidence) is closed, but stochastic throttling of marginal flips is a different use of the overshoot signal: it rations exactly the flips the evidence is least sure about.
- **cost:** cheap probe.

### A-016 · Batched flips (structure updates every 8 steps)
- **mechanism:** counters accumulate continuously but flips are APPLIED only every 8 steps, so the network the gradients describe is stable between structure rounds.
- **flag-level change:** new flag `--flip-batch 8` on Layered/Direct.
- **why it might win:** per-step flipping means every gradient is computed against a network that just changed in ~0.1% of its weights; block-updating the discrete side is the discrete analogue of target networks / block coordinate descent and has never been tried here.
- **cost:** cheap probe.

### A-017 · Global flip budget (rationed flips per step)
- **mechanism:** at most 0.05% of weights may flip per step; if more cross V, the largest-overshoot counters win and the rest keep accumulating.
- **flag-level change:** new flag `--flip-cap 0.0005` on Layered.
- **why it might win:** flip RATE is currently an emergent by-product nobody controls; the ladder records show flip share varying 2× between arms with no design intent. A budget makes the structure's learning rate an explicit dial, orthogonal to V.
- **cost:** cheap probe.

### A-018 · Block-staggered flips (one block flips per step, rotating)
- **mechanism:** flip eligibility rotates across blocks — on any step only one block's threshold crossings are applied; other blocks' counters keep accumulating.
- **flag-level change:** new flag `--flip-stagger` on Layered.
- **why it might win:** simultaneous flips in adjacent blocks interact (a flip in block 1 changes what block 2's gradients meant); staggering serializes the interaction, the same reason coordinate descent can beat joint updates on coupled problems.
- **cost:** cheap probe.

### A-019 · Flip-flop quarantine
- **mechanism:** a weight that flips and flips back within 20 steps has its counter zeroed and its personal V doubled for the next 100 steps, then released.
- **flag-level change:** new flag `--quarantine` on Layered.
- **why it might win:** freezing (pooled) punishes flip COUNT over a window and is permanent; quarantine punishes the specific flip-FLOP signature (immediate reversal = the flip was noise) and is temporary and targeted.
- **cost:** cheap probe.

### A-020 · Component coupling on flip (sibling counter reset)
- **mechanism:** when one layered component flips, the OTHER component's counter resets to 0 — a flip restarts the sibling's evidence from scratch.
- **flag-level change:** new flag `--comp-reset` on Layered.
- **why it might win:** after t1 flips, t2's accumulated evidence was gathered against the old installed value and is partly stale; the pooled arbitration rules govern simultaneous flips only, never this cross-time staleness.
- **cost:** cheap probe.

### A-021 · Post-flip rebound damping
- **mechanism:** for 10 steps after a weight flips, its incoming votes count half — the new state gets a settling period before contrary evidence can accumulate at full strength.
- **flag-level change:** new flag `--rebound 10` on Layered/Direct.
- **why it might win:** the cheapest possible anti-oscillation device: no thresholds, no freezing, just a refractory period — the neural-dynamics answer to the same pathology freezing attacks statistically.
- **cost:** cheap probe.

### A-022 · Tail freeze (V×3 for the last 10% of steps)
- **mechanism:** V triples for the final 10% of the run while everything else (including AdamW parts) continues unchanged — the discrete structure sets like cooling metal at the end.
- **flag-level change:** new flag `--vtail 3` on Layered.
- **why it might win:** the pooled schedules move V linearly across the whole run; this is a step change confined to the tail, and the closed anneal arm's lesson (hot starts poison) says nothing about cold ENDINGS. It is the vote-side form of Fable's cool-down finding, in its most conservative shape.
- **cost:** cheap probe.

### A-023 · Vote warmup (no flips for the first 5% of steps)
- **mechanism:** counters accumulate from step 0 but NO flip may fire during the first 5% of steps; structure commits only on banked evidence.
- **flag-level change:** new flag `--vwarm 0.05` on Layered/Direct.
- **why it might win:** the anneal disaster (3.850) proved early flips on weak evidence are the mechanism's worst failure; every pooled schedule still flips from step 0. A pure delay is the most direct repair and has literally never been run in this lab.
- **cost:** cheap probe.

### A-024 · ε-greedy random flips (lattice exploration)
- **mechanism:** each step, a random 0.1% of weights flip to a random other level regardless of counters.
- **flag-level change:** new flag `--flip-eps 0.001` on Layered.
- **why it might win:** vote dynamics are purely exploitative — a weight whose early evidence was unlucky may never revisit a better level; a small exploration rate is the standard bandit fix and its cost at 0.1% is measurable, not assumed.
- **cost:** cheap probe.

## S3 — Per-layer, per-role, per-head treatment

### A-025 · Depth-scaled V (fixed depth prior: 16 → 48)
- **mechanism:** block 1 runs V=16, block 2 runs V=48 — deeper blocks flip colder because their errors compound through everything downstream.
- **flag-level change:** new flag `--vdepth 16,48` on Layered.
- **why it might win:** pooled per-layer entries ADAPT V to a flip-rate target (feedback); this is the open-loop prior from error-compounding theory. If the prior alone captures the gain, the adaptive machinery is unnecessary.
- **cost:** cheap probe.

### A-026 · Role-scaled V (attention cold, FFN hot)
- **mechanism:** attention projections run V=48, FFN projections V=24.
- **flag-level change:** new flag `--vrole 48,24` on Layered.
- **why it might win:** every record agrees attention logits are the fragile side of a ternary net (coarse QK products get exponentiated); the FFN is a sum where flip noise averages out. One global V prices both the same today.
- **cost:** cheap probe.

### A-027 · Mixed structure by depth (block 1 plain, block 2 layered)
- **mechanism:** the first block uses single-component ternary weights, the second uses two-component layered weights (same total ternary count rebalanced).
- **flag-level change:** new flag `--mixed-depth` in the model builder.
- **why it might win:** the half-control settled that levels earn nothing UNIFORMLY at equal size/steps; it never tested levels concentrated where representation is richest (the last block). Placement is a different question from count.
- **cost:** cheap probe.

### A-028 · Hybrid by depth (block 1 STE, block 2 votes)
- **mechanism:** the first block's ternary weights train by STE, the second block's by votes, simultaneously — trainer assignment by depth instead of by phase.
- **flag-level change:** new flag `--hybrid-depth ste,votes` (both trainers active in one run).
- **why it might win:** pooled hybrids switch trainers over TIME; the phase switch forces one mechanism to inherit the other's half-trained state. Depth-splitting lets each mechanism own the territory it suits (early feature extraction vs late refinement) with no hand-off.
- **cost:** full trial only (two trainer paths interact; a 75-second probe under-measures the STE block).

### A-029 · Per-head temperature spread (V = 16/24/32/48 across heads)
- **mechanism:** the four attention heads' QKVO weights run four different fixed thresholds, giving the model a built-in diversity of flip temperatures.
- **flag-level change:** new flag `--vhead` on Layered.
- **why it might win:** heads specialize; a single V forces identical evidence standards on heads doing different jobs. A spread is also a cheap ensemble-inside-one-layer: at least one head sits near the (unknown) optimal temperature.
- **cost:** cheap probe.

### A-030 · Scale-coupled V (V proportional to layer γ)
- **mechanism:** each layer's V is set proportional to its absmean scale γ (recomputed as γ drifts), so layers whose installed steps are physically larger demand proportionally more evidence.
- **flag-level change:** new flag `--vscale` on Layered.
- **why it might win:** a flip changes the output by ~γ; equal V across layers means unequal physical step sizes per unit evidence. Coupling V to γ equalizes the evidence-per-physical-change ratio — a units argument, not a tuning guess.
- **cost:** cheap probe.

### A-031 · Counter width by depth (int8 early, int16 late)
- **mechanism:** block 1 keeps int8 counters, block 2 gets int16 counters (with V=64 there) — state bytes allocated where the network is deepest.
- **flag-level change:** new flags `--width-depth` + per-block `--votes`.
- **why it might win:** the accumulator-precision dial (study A3) has only been turned uniformly; if precision matters, it should matter most where errors compound. This prices the dial's placement at ~half the cost of widening everywhere.
- **cost:** cheap probe.

### A-032 · Role-split trainers (votes on QK, STE on V/O/FFN)
- **mechanism:** votes train the Q and K projections only; STE trains V, O, and FFN projections.
- **flag-level change:** new flag `--role-split qk`.
- **why it might win:** QK products are where ternary coarseness is exponentiated — arguably where the vote counter's patience helps most — while the value/FFN path is a plain sum where STE's fine convergence is strongest. Nobody has split the mechanisms by projection role.
- **cost:** full trial only.

## S4 — Schedules and phases specific to votes

### A-033 · Cyclic V (16 → 48 → 16, twice per run)
- **mechanism:** V follows a triangular cycle over the run instead of a monotone schedule — periodic reheating lets settled structure re-open, cooling re-sets it.
- **flag-level change:** new flag `--vcycle` on Layered.
- **why it might win:** pooled schedules are monotone (cool only); cyclical schedules (SGDR) exist in FP training precisely because monotone cooling strands models in early basins. The vote lattice is at least as basin-prone.
- **cost:** cheap probe.

### A-034 · Gate ease-in (quantile ramps 0 → 0.5 over the first 25%)
- **mechanism:** the gate starts OPEN (every gradient votes) and tightens to the standard stronger-half rule over the first quarter of the run.
- **flag-level change:** new flag `--gate-ease 0.25` on Layered.
- **why it might win:** pooled ease-in entries ease the ROUNDING (STE-side concept ported to votes); easing the GATE is the vote-native version — early training gets maximum evidence flow while gradients are large and informative, selectivity arrives as they shrink.
- **cost:** cheap probe.

### A-035 · Grow components mid-run (plain → layered at 25%)
- **mechanism:** train plain votes for the first 25%, then split each weight: t1 keeps the trained state, t2 enters at 0 with fresh counters — the layered structure is GROWN from a trained plain net.
- **flag-level change:** new flag `--grow-comps 0.25` on Layered.
- **why it might win:** layered-from-scratch wastes early steps populating levels (the sweep record: ±2 barely populated at 8 min); growing gives the second component a meaningful backbone to correct from step one of its life. It is the layered idea's best-case entry point, never tested.
- **cost:** cheap probe.

### A-036 · Collapse components late (layered → plain at 75%)
- **mechanism:** at 75% of the run, t2 folds into t1 by rounding the installed sum back to {-1,0,1} and training finishes as plain votes.
- **flag-level change:** new flag `--collapse 0.75` on Layered.
- **why it might win:** tests whether the levels' value is as early-training scaffolding (extra expressiveness while structure forms) rather than as a serving format — if collapse matches layered, the serving model can ship at half the mechanism state.
- **cost:** cheap probe.

### A-037 · Frozen-structure polish (votes off at 60%, AdamW parts finish)
- **mechanism:** after 60% of steps the ternary state freezes completely and only embeddings, norms, and scales train for the remaining 40%.
- **flag-level change:** new flag `--freeze-tern 0.6` on Layered/Direct.
- **why it might win:** prices the structure-vs-calibration split directly: how much of the remaining loss is the discrete structure vs the FP parts' fit to it? Fable's polish (pooled) runs the whole STE net at low lr; freezing ONLY the discrete side is the vote-native form.
- **cost:** cheap probe.

### A-038 · Alternating update phases (200-step blocks)
- **mechanism:** alternate 200 steps of votes-only updates (AdamW parts frozen) with 200 steps of AdamW-only updates (counters frozen).
- **flag-level change:** new flag `--alt-phase 200` in the training loop.
- **why it might win:** simultaneous updating means each side perpetually chases the other's motion; alternation is block coordinate descent across the discrete/continuous split — the same argument as A-018, applied across trainer types instead of blocks.
- **cost:** cheap probe.

### A-039 · AdamW warmup for the shared parts (vote arms)
- **mechanism:** the shared parts' lr warms 0 → 1e-3 over the first 100 steps while votes run at full rate from step 0.
- **flag-level change:** new flag `--opt-warmup 100` on Direct/Layered.
- **why it might win:** STE arms have always had warmup (200 steps, in the built-in recipe); vote arms never have — an unexamined recipe asymmetry between the two families whose comparison is the lab's central question. Nearly free to test.
- **cost:** cheap probe.

### A-040 · Gradient-norm clipping before signing
- **mechanism:** each layer's gradient is norm-clipped (to 1.0) before its sign/magnitude feeds the vote path; the AdamW parts see the unclipped gradient.
- **flag-level change:** new flag `--gclip 1.0` on Layered/Direct.
- **why it might win:** a single outlier batch currently casts a full-strength vote storm; clipping bounds any one batch's say over the discrete structure without touching the continuous parts' training.
- **cost:** cheap probe.

## S5 — Training-data side: curricula, ordering, mixture

### A-041 · Easy-to-hard curriculum (windows ordered by init loss)
- **mechanism:** training windows are scored once by the init model and presented in ascending-loss order across the run (uniform sampling within decile bands to avoid pure sorting).
- **flag-level change:** new flag `--curr asc` (sampler change; one init pass over the corpus, charged).
- **why it might win:** the lab has only ever sampled uniformly; a vote counter forming structure early benefits from clean signal first — the curriculum hypothesis applied to exactly the phase where the anneal arm showed early evidence quality is decisive.
- **cost:** cheap probe.

### A-042 · Hard-to-easy anti-curriculum (control)
- **mechanism:** the reverse ordering of A-041 (descending init loss).
- **flag-level change:** new flag `--curr desc`.
- **why it might win:** curriculum claims are unfalsifiable without the reverse control; if desc ≥ asc, ordering effects here are about recency, not difficulty — either answer disciplines A-041's interpretation.
- **cost:** cheap probe.

### A-043 · Middle-out curriculum
- **mechanism:** start from median-difficulty windows and expand the band symmetrically toward easy and hard extremes.
- **flag-level change:** new flag `--curr mid`.
- **why it might win:** median windows are where the model's errors are most informative (not yet mastered, not hopeless); both pure orderings spend early steps on one uninformative extreme.
- **cost:** cheap probe.

### A-044 · Paired repetition (each window twice in a row)
- **mechanism:** every sampled window is trained on twice consecutively before the stream moves on.
- **flag-level change:** new flag `--repeat 2` (sampler).
- **why it might win:** the second pass's gradients are computed against a network that just absorbed the first pass — for a counter integrating signs, paired passes turn single noisy votes into before/after comparisons. Ordering has never been varied at all in this lab.
- **cost:** cheap probe.

### A-045 · Context-length curriculum (64 → 128 → 256 by thirds)
- **mechanism:** the run trains at ctx 64 for the first third, 128 for the second, 256 for the last (RoPE positions span each range as it arrives).
- **flag-level change:** new flag `--ctx-curr` (window slicing in the sampler).
- **why it might win:** short contexts are cheaper per step and teach local structure first; the final third still trains at full length. Even at equal minutes the step count rises — charged honestly, judged per minute like every arm.
- **cost:** cheap probe.

### A-046 · Reverse context curriculum (256 → 128 → 64, control)
- **mechanism:** the reverse schedule of A-045.
- **flag-level change:** new flag `--ctx-curr rev`.
- **why it might win:** control for A-045 — separates "ends at the tested length" (both end differently, deliberately) from "short first helps"; read together, the pair isolates the ordering effect from the endpoint effect.
- **cost:** cheap probe.

### A-047 · Near-duplicate window removal
- **mechanism:** windows whose token stream is a near-duplicate of an earlier window (hash of sorted 8-gram shingles) are dropped from the stream.
- **flag-level change:** new flag `--dedup` (sampler preprocessing, charged).
- **why it might win:** the corpus is harvested prose — boilerplate and repeated passages are plausible; duplicated windows are invisible oversampling of whatever they contain, and uniform sampling has never been audited for it.
- **cost:** cheap probe.

### A-048 · Source-balanced mixture (equal weight per source file)
- **mechanism:** sampling weights are set so each of the ~393 source files contributes equally, instead of in proportion to its length.
- **flag-level change:** new flag `--src-balance` (sampler weights).
- **why it might win:** length-proportional sampling lets the longest files dominate the structure the votes build; the 2B4T recipe literature treats mixture as a first-class lever, and this lab has never moved it. Failweight (pooled) reweights by LOSS; this reweights by PROVENANCE — different axis.
- **cost:** cheap probe.

### A-049 · Frequent-token downweighting
- **mechanism:** windows where the 100 most frequent tokens make up >60% of positions are sampled at half rate.
- **flag-level change:** new flag `--freq-balance` (sampler weights).
- **why it might win:** stopword-dominated windows carry little structural signal per step but consume the same vote budget; this is a content-based mixture correction that needs no loss measurements and cannot chase the model's own biases (unlike failweight).
- **cost:** cheap probe.

### A-050 · Held-adjacency buffer (leak-tightening control)
- **mechanism:** training windows within ±2 window positions of any held window are excluded from the stream.
- **flag-level change:** new flag `--buffer 2` (sampler exclusion).
- **why it might win:** held windows were chosen by an every-40th rule, so their immediate neighbours ARE trained on — near-duplicate context could inflate every held number the lab owns. This is a methods audit priced as one probe: if the loss moves, all prior margins get re-read.
- **cost:** cheap probe.

### A-051 · Cyclic-shift augmentation
- **mechanism:** each window is cyclically shifted by a random offset when sampled (the token ring rotates; RoPE sees the same content at different absolute phases).
- **flag-level change:** new flag `--shift-aug` (sampler transform).
- **why it might win:** with only ~8 minutes of unique stream, augmentation multiplies the effective data; rotation specifically attacks position overfitting, which a carried position table + rotary hybrid could plausibly suffer.
- **cost:** cheap probe.

### A-052 · Span-noise input masking (objective unchanged)
- **mechanism:** one random 8-token span per window is replaced by a mask embedding in the INPUT; targets remain the true next tokens everywhere — pure input-noise regularization under the standard token loss.
- **flag-level change:** new flag `--span-noise 8` in the model input path.
- **why it might win:** the JEPA objective is closed, and this is NOT it — the loss, targets, and yardstick are unchanged. It tests only whether input corruption regularizes a vote-trained trunk (whose discrete weights may overfit surface patterns faster than FP weights).
- **cost:** cheap probe.

### A-053 · Source-diverse batches (≥8 files per batch)
- **mechanism:** batch construction deliberately mixes windows from at least 8 different source files, instead of whatever consecutive sampling produces.
- **flag-level change:** new flag `--batch-mix` (batch builder).
- **why it might win:** for a sign-integrating trainer, batch composition IS the evidence distribution; homogeneous batches cast correlated votes. Diversity per batch is the mixture lever at the finest grain, distinct from global sampling weights.
- **cost:** cheap probe.

### A-054 · Regression-weighted sampling (Δloss, not loss level)
- **mechanism:** windows are re-scored periodically; those whose loss INCREASED since their last scoring are oversampled 2× — targeting forgetting, not difficulty.
- **flag-level change:** new flag `--regress-weight 2` (sampler).
- **why it might win:** failweight (pooled) oversamples the statically worst decile; regression weighting targets what training is actively LOSING — catastrophic-forgetting repair aimed at the discrete structure's known weakness (flips erase as well as write).
- **cost:** cheap probe.

### A-055 · Coverage-first sampling (unseen windows preferred)
- **mechanism:** sampling weight is highest for windows never yet sampled and drops after each visit, maximizing unique-window coverage within the budget.
- **flag-level change:** new flag `--coverage` (sampler).
- **why it might win:** at 8 minutes the run sees a fraction of the corpus; uniform sampling revisits some windows while never touching others. For a token-hungry model family, breadth of unique tokens is the scarcest resource — this spends the budget on it directly.
- **cost:** cheap probe.

### A-056 · Corrupt-window filtering (drop worst 2% by init loss)
- **mechanism:** the 2% of windows with the highest init-model loss are removed from the stream entirely (likely boilerplate, markup wreckage, or foreign text).
- **flag-level change:** new flag `--drop-worst 0.02` (sampler preprocessing, shares A-041's scoring pass).
- **why it might win:** the mirror image of failweight: instead of training MORE on the hardest windows, test whether the hardest sliver is noise rather than signal. The pair (406/A-056) brackets the hardest-window question from both directions.
- **cost:** cheap probe.

## S6 — Combinations of known-good or neutral elements, never tried together

### A-057 · STE-half + rotary + EMA (running-mean) readout
- **mechanism:** ste_half with rotary, evaluated at an exponential moving average of the latent weights (decay 0.999) as well as at the final weights.
- **flag-level change:** new flag `--ema-readout 0.999` on the STE trainer (eval-side, like the pooled modal readout but for the FP trainer).
- **why it might win:** Fable's recipe line reads EVERY run at running-mean weights and the modal readout (pooled) imports the idea for votes; the STE side of THIS lab has never had its readout measured, yet ste_half currently leads the whole table (2.8205) — its readout delta is unpriced.
- **cost:** cheap probe.

### A-058 · Fractional leak 0.99 + thrash freeze 5
- **mechanism:** the study's C3 and C4 add-ons stacked on the layered chassis.
- **flag-level change:** `--leak 0.99 --freeze 5` (both flags pooled separately; the combination is new).
- **why it might win:** leak smooths evidence over time; freezing removes proven oscillators. They attack the same pathology at different points (input vs state) and the study's own ordering presents them as a pair — the pair has never run.
- **cost:** cheap probe.

### A-059 · Calibrated magnitude votes at FULL width + rotary
- **mechanism:** `--mag-cal 1.0` on the full-width plain trainer with rotary.
- **flag-level change:** `--arm plain --rope --mag-cal 1.0`.
- **why it might win:** calibrated magnitude votes are pooled only at half width; the as-specified full-width arm is closed but the pool's own precedent says a calibrated re-set is a different arm. Width interacts with the accumulator dial (more weights = different gradient statistics), so the half result cannot simply be assumed to transfer.
- **cost:** cheap probe.

### A-060 · Rounding ease-in 0.5 + vote schedule 32→64
- **mechanism:** the two Fable-trace transfers for votes stacked: `--ease 0.5 --vsched 32:64`.
- **flag-level change:** both flags pooled separately; combination new.
- **why it might win:** ease-in protects early structure formation; the schedule cools late flips. They act on disjoint phases of the run, so additivity is plausible — and if they interfere, that interaction is itself a finding about phase overlap.
- **cost:** cheap probe.

### A-061 · Failweight 2 + modal readout 5
- **mechanism:** weakness-targeted sampling with the discrete-EMA readout: `--failweight 2 --modal 5`.
- **flag-level change:** both pooled separately; combination new.
- **why it might win:** failweight changes what the structure learns; modal readout reduces the variance of what gets shipped. Training-side and readout-side gains are the most likely pair in the pool to be purely additive.
- **cost:** cheap probe.

### A-062 · QK-Norm + gated attention
- **mechanism:** the research report's rank-1 and rank-2 items stacked: `--qk-norm --gated-attn`.
- **flag-level change:** both pooled separately; combination new.
- **why it might win:** QK-Norm bounds logits before the softmax; the gate suppresses sink-dumping after it. They guard the same pathway at two different stations — the report ranks both top-2 but the lab tests singles first; this is the designated first stack once both singles read.
- **cost:** cheap probe.

### A-063 · Per-channel scales + Hadamard rotation
- **mechanism:** `--scale-gran channel --hadamard` — finer weight scales plus activation-outlier spreading.
- **flag-level change:** both pooled separately; combination new.
- **why it might win:** both are magnitude-management moves but on opposite sides of the matmul (weights vs activations); ternary error lives in their interaction, so the stack could compound — or reveal that one makes the other redundant.
- **cost:** cheap probe.

### A-064 · SubLN + logits KD (BitDistill's actual pairing)
- **mechanism:** `--subln --kd 1.0` — SubLN inserted exactly as BitDistill's stage-1 precondition for its stage-3 distillation.
- **flag-level change:** both pooled separately; combination new (and it is the published recipe's real form).
- **why it might win:** BitDistill's evidence is for the SEQUENCE, not for either piece alone; testing KD without its designed preconditioner (the pooled singles) may underprice both. This entry is the faithful transplant.
- **cost:** full trial only (requires the teacher run; a probe's short horizon distorts KD most).

### A-065 · FP-first 0.9 + two-stage weight decay (STE)
- **mechanism:** ParetoQ's split with the official recipe's WD shape: WD cosines to 0.1 during the FP phase and switches off for the ternary phase.
- **flag-level change:** `--fp-first 0.9 --two-stage-wd` on the STE trainer.
- **why it might win:** the pooled entries test the split and the two-stage recipe separately; the published recipes were designed together (the stage boundary in 2B4T IS a data/recipe switch), so the combination is the honest form of both.
- **cost:** full trial only.

### A-066 · Three components + descending per-component V (32, 16, 8)
- **mechanism:** `--comps 3 --comp-v 32,16,8` — each successive component flips hotter than the last.
- **flag-level change:** pooled pieces (comps 3; comp-v pairs) extended to a 3-term descending ladder; combination new.
- **why it might win:** the pooled pair (32,16) tests backbone+correction; a descending ladder is the multigrid version — coarse stable structure, then progressively finer/faster corrections — which is how residual quantizers are actually built.
- **cost:** cheap probe.

### A-067 · Ungated calibrated magnitude votes (plain, q removed entirely)
- **mechanism:** `--arm plain_half --rope --mag-cal 1.0 --gate-q 0.0` — calibrated increments with NO median gate anywhere in the path.
- **flag-level change:** combination new (gate-off exists pooled only on layered with plain increments).
- **why it might win:** completes the 2×2 of {gate, increment type} for the calibrated family: if ungated-calibrated wins, the gate was the problem all along and several pooled gate entries get re-read.
- **cost:** cheap probe.

### A-068 · Gradient whitening + Muon (hybrid arm)
- **mechanism:** on the votes→STE hybrid, the vote phase uses whitened gradients and the STE phase uses Muon: `--hybrid 0.7:ste --whiten --muon`.
- **flag-level change:** all three pooled separately; combination new.
- **why it might win:** whitening and Muon are the same idea (orthogonalize the update geometry) expressed for the two trainer families; running them in their respective phases tests whether update-geometry is the hybrid's binding constraint.
- **cost:** full trial only.

### A-069 · Verify-flips with Fisher-ranked queue
- **mechanism:** `--verify-flips 200 --share 0.001` semantics merged: the periodic verification budget is spent on the Fisher-ranked candidate queue instead of merely the nearest-to-threshold weights.
- **flag-level change:** combination of pooled MILL-231 and MILL-229 mechanics; new joint flag `--verify-fisher`.
- **why it might win:** verify-flips picks candidates by counter proximity (cheap, myopic); Fisher ranking picks by estimated loss effect (the cell-scale winner's criterion). Verification is the scarce resource — aiming it better is the obvious joint upgrade.
- **cost:** cheap probe.

### A-070 · Modal readout during a vote polish phase
- **mechanism:** after the standard layered run, a 25% polish phase at V=64 with modal readout taken over the polish checkpoints: `--vtail`-style cold polish + `--modal 5` restricted to the polish window.
- **flag-level change:** new flag `--polish-votes 0.25` combining pooled pieces (polish exists for STE; modal for votes; the vote-polish is new).
- **why it might win:** Fable's sleep experiment says plain continued training at low rate beat fancier options; the vote analogue — colder votes, modal-read — has never been assembled, and readout-over-polish averages exactly the most-settled states.
- **cost:** cheap probe.

### A-071 · RoPE base 1000 + partial RoPE 0.5
- **mechanism:** `--rope-base 1000 --rope-frac 0.5` — a mid-range base (the pooled grid has 500 and 50000) with half the head dims rotated.
- **flag-level change:** combination new; base 1000 itself is also unpooled.
- **why it might win:** base and fraction both reshape the rotation spectrum; at ctx 256 the standard base 10000 leaves the fastest pairs nearly unrotated — a smaller base makes rotation actually engage at lab context lengths, and the fraction hedges the scramble risk.
- **cost:** cheap probe.

### A-072 · Thrash freeze 5 + zero-bias 1.5
- **mechanism:** `--freeze 5 --zero-bias 1.5` — stability machinery plus the sparsity prior.
- **flag-level change:** freeze pooled; zero-bias is A-009; combination new.
- **why it might win:** freezing stabilizes the weights that oscillate; zero-bias decides WHERE stabilized weights prefer to sit. If sparsity is good, frozen-at-nonzero oscillators are the ones wasting it.
- **cost:** cheap probe.

## S7 — Architecture micro-variants (ternary-compatible)

### A-073 · Zero-init output projections
- **mechanism:** the attention-output and FFN-down ternary states initialize to all zeros, so each block starts as a near-identity residual and votes grow its output structure from nothing.
- **flag-level change:** new flag `--zero-init-out` in the model builder.
- **why it might win:** random-init ternary outputs inject full-strength noise into the residual stream from step 0; zero-init (the ReZero/Fixup insight) lets early training organize around a clean signal — and vote counters, which need consistent evidence, should benefit most.
- **cost:** cheap probe.

### A-074 · Depth-scaled residual gains (1/√(2L))
- **mechanism:** each block's output is scaled by 1/√(2·blocks) before joining the residual stream (DeepNet-style).
- **flag-level change:** new flag `--deepnet-scale` in Block.
- **why it might win:** ternary block outputs have quantized, scale-quantized magnitudes; residual variance growth across blocks is currently unmanaged. This is the norm family's missing member (the pooled norm entries move norms around; none scale the residual contribution).
- **cost:** cheap probe.

### A-075 · Attention logit softcap (tanh, cap 30)
- **mechanism:** attention logits pass through 30·tanh(logits/30) before the softmax — smooth bounding instead of norming or clipping.
- **flag-level change:** new flag `--softcap 30` in attention.
- **why it might win:** QK-Norm (pooled) renormalizes Q/K; QK-Clip (pooled) rescales after the fact; softcap bounds the logit itself differentiably (Gemma-2's choice) and interacts with gradients during training, not just the forward range. Three different governors — the lab should own all three numbers.
- **cost:** cheap probe.

### A-076 · Ternary value activations (V path only)
- **mechanism:** the V projection's OUTPUT activations are quantized to {-1,0,1}×per-head scale before the attention weighted sum (weights and all other activations unchanged, still INT8 elsewhere).
- **flag-level change:** new flag `--act-ternary-v` in attention.
- **why it might win:** attention outputs are convex combinations of value vectors; ternarizing values tests how much of attention's work is routing (which survives) vs content (which degrades). A scoping probe for how far activation ternarization can go on the safest path first.
- **cost:** cheap probe.

### A-077 · Per-head QK scales
- **mechanism:** Q and K projections get per-HEAD absmean scales instead of per-layer scales.
- **flag-level change:** new flag `--qk-scale head` in BitLinear usage for qkv.
- **why it might win:** heads with different roles develop different magnitude profiles; a single per-layer γ forces one compromise. This is scale granularity (pooled for whole layers) applied at the granularity attention actually varies at.
- **cost:** cheap probe.

### A-078 · Learned per-head attention temperature
- **mechanism:** each head's logits are divided by a learned FP temperature (init 1.0, AdamW-trained).
- **flag-level change:** new flag `--attn-temp` in attention.
- **why it might win:** ternary QK dot products have a coarse, layer-dependent natural scale; a per-head temperature is the cheapest possible calibration (4 scalars) and the pooled QK entries all constrain the DISTRIBUTION, never the softmax's sharpness directly.
- **cost:** cheap probe.

### A-079 · Half-gated FFN (ternary gate, FP value path)
- **mechanism:** FFN becomes gate(x) ⊙ value(x) where the gate branch is ternary but the value branch stays FP until the down projection.
- **flag-level change:** new flag `--ffn halfglu` in Block.
- **why it might win:** SwiGLU (pooled as negative control) multiplies TWO coarse branches — the stated objection; half-gating keeps the selection mechanism (which is where GLU gains live) while letting one branch carry full precision, at partial byte cost charged honestly.
- **cost:** cheap probe.

### A-080 · RoPE with the position table REMOVED
- **mechanism:** rotary on, and the carried `pos` table is deleted from the model entirely (49,152 fewer parameters) instead of carried unused Fable-style.
- **flag-level change:** new flag `--rope-nopos` in the model builder.
- **why it might win:** the ROPE results note explicitly chose to carry the table for compatibility and flagged removal as the untested variant; at lab scale 49K FP parameters is ~3% of the model, and per-byte judging needs this number.
- **cost:** cheap probe.

### A-081 · Ternary LM head (embeddings stay FP)
- **mechanism:** the output head becomes a BitLinear (ternary weights, per-row scales) while the input embedding stays FP and untied-for-this-purpose.
- **flag-level change:** new flag `--head-ternary` in the model builder.
- **why it might win:** the pooled embedding entries price the TIED table; the head and the embedding have opposite jobs (classification geometry vs input representation) and the head is the larger consumer at vocab 4096. Pricing the head alone completes the map.
- **cost:** cheap probe.

### A-082 · Fixed local pre-mix before block 1
- **mechanism:** token embeddings pass through a fixed (non-learned) average over positions ±1 before the first block — a zero-parameter local smoothing.
- **flag-level change:** new flag `--premix` in the model builder.
- **why it might win:** the first ternary block sees raw embeddings; a fixed local average gives it bigram-ish context for free, testing whether the first block's ternary capacity is being spent re-deriving local context that a fixed filter supplies.
- **cost:** cheap probe.

### A-083 · Bigram hash embedding (small FP side table)
- **mechanism:** an FP embedding of the hashed previous-token pair (512 buckets × dim/4, projected and added) supplements the token embedding.
- **flag-level change:** new flag `--bigram-emb 512` in the model builder.
- **why it might win:** embeddings are the FP part of this model and local word-pair statistics are the cheapest predictive signal in prose; if a tiny side table buys loss, it prices where FP bytes earn most — the complement question to A-081.
- **cost:** full trial only (new parameter plumbing; probe horizons underprice embeddings).

### A-084 · FFN activation clipping at 6
- **mechanism:** FFN intermediate activations are clipped to [-6, 6] before the down projection's INT8 quantization.
- **flag-level change:** new flag `--act-clip 6` in Block.
- **why it might win:** INT8 absmax quantization is destroyed by rare huge activations (the same outlier story as Hadamard, attacked by truncation instead of rotation); clipping is one line and its loss cost at 6 is measurable, making it the cheapest member of the outlier family to price.
- **cost:** cheap probe.

### A-085 · LayerScale on blocks (learnable residual gains, init 0.1)
- **mechanism:** each sublayer output is multiplied by a learned per-channel FP gain initialized at 0.1.
- **flag-level change:** new flag `--layerscale` in Block.
- **why it might win:** A-074 fixes the gain by formula; LayerScale learns it — together they test whether residual-stream budgeting matters for ternary blocks and whether the right budget is learnable at this scale.
- **cost:** cheap probe.

### A-086 · QK-Norm AFTER RoPE (placement variant)
- **mechanism:** RMSNorm applied to q,k after the rotary rotation instead of before it.
- **flag-level change:** new flag `--qk-norm-post`.
- **why it might win:** the pooled QK-Norm specifies pre-RoPE placement; rotation preserves norms per pair but redistributes them across dims, so post-RoPE norming constrains the quantities the softmax actually sees. Placement was decisive for RoPE itself in this lab — it is a real variable, not a detail.
- **cost:** cheap probe.

### A-087 · Rotary on V (values rotated too)
- **mechanism:** the rotary rotation is applied to v as well as q,k.
- **flag-level change:** new flag `--rope-v`.
- **why it might win:** almost certainly a falsification probe: rotating values should scramble content — but "should" is doing the work in that sentence, the cost is one probe, and a surprise here would rewrite the lab's understanding of what rotary contributes (position signal vs regularization noise).
- **cost:** cheap probe.

### A-088 · Head dim 32 × 6 heads
- **mechanism:** attention restructured to 6 heads of dim 32 (from 4 of 48), same total width.
- **flag-level change:** new flag `--head-dim 32` in the model builder.
- **why it might win:** pooled head-count entries (2/8) keep the model dim and change head dim implicitly the other way; this point fills the geometry grid between them and tests whether per-head dim (rotation pairs: 16 vs 24) matters to ternary QK quality.
- **cost:** cheap probe.

### A-089 · Context 512 at the chassis shape
- **mechanism:** the chassis trained and evaluated at ctx 512 instead of 256 (nothing else changes).
- **flag-level change:** `--ctx 512` run configuration (steps will fall at equal minutes; charged).
- **why it might win:** the scale ladder varies WEIGHT count; context length is a different axis and the lab's rope/SWA entries all carry "expected flat at ctx 256" caveats. This prices the length axis once, honestly, on the champion.
- **cost:** cheap probe (slower steps accepted; judged per minute).

### A-090 · Learned scalar gates on sublayer outputs (init 1)
- **mechanism:** one FP scalar per sublayer multiplies its output before the residual add, learned by AdamW.
- **flag-level change:** new flag `--gate-resid` in Block.
- **why it might win:** the scalar version of A-085 — 4 scalars per block total. If even scalars move the loss, residual budgeting is a real ternary lever; if not, A-074/A-085's chances fall together. Cheap joint information.
- **cost:** cheap probe.

### A-091 · Embedding-output norm
- **mechanism:** an RMSNorm on the token+position embedding sum before block 1.
- **flag-level change:** new flag `--emb-norm` in the model builder.
- **why it might win:** every norm entry in the pool lives inside blocks; the embedding output is the one unnormalized input to the first ternary matmul, and its scale sets the first block's activation-quantization range.
- **cost:** cheap probe.

### A-092 · No final norm (head reads the raw residual)
- **mechanism:** the final RMSNorm before the LM head is removed and replaced by a single learned scalar.
- **flag-level change:** new flag `--no-final-norm` in the model builder.
- **why it might win:** a falsification/pricing probe in the Falcon-E spirit (norm removal direction): the final norm is where residual scale meets the FP head; if a scalar suffices, the norm's per-channel freedom was costing or earning something measurable either way.
- **cost:** cheap probe.

## S8 — Readout, evaluation-side, and state economy

### A-093 · Median readout (last 5 checkpoints)
- **mechanism:** the shipped state is the per-weight MEDIAN of the last 5 checkpoint states instead of the mode.
- **flag-level change:** new flag `--median-readout 5` (eval-side).
- **why it might win:** for two-component layered weights the median and mode differ exactly on the contested weights; the pooled modal readout assumes majority is right, the median is the robust-statistics alternative — one extra eval on the same run prices both.
- **cost:** cheap probe (rides any layered run's checkpoints).

### A-094 · Average-then-round readout (last 5 checkpoints)
- **mechanism:** average the last 5 ternary states per weight in FP, then round to the nearest installed level — the closest possible analogue of Fable's running-mean readout for a discrete model.
- **flag-level change:** new flag `--avg-readout 5` (eval-side).
- **why it might win:** modal readout (pooled) takes a majority vote of states; averaging preserves HOW contested each weight was (a 3-2 split rounds differently from 5-0). Fable's proven readout is an average, not a vote — this is its faithful discrete translation, and it has not been run.
- **cost:** cheap probe (rides any layered run's checkpoints).

### A-095 · Best-checkpoint readout (selection upper bound)
- **mechanism:** evaluate held loss at each of the last 5 checkpoints and report the best, as a diagnostic only.
- **flag-level change:** new flag `--best-ckpt` (eval-side).
- **why it might win:** prices the ceiling of ALL readout games (modal/median/average) before the mill invests in them: if best-ckpt ≈ final state, readout variance is small and the whole family drops in priority; if the gap is large, readout is a real lever. Methodological, one eval pass.
- **cost:** cheap probe.

### A-096 · int8 counters at V=16 (state-halved hot point)
- **mechanism:** the V=16 point of the pooled threshold grid, but with counter width explicitly cut to int8 (the grid runs the standard width) — mechanism state per weight halves vs the int16 path.
- **flag-level change:** `--votes 16 --counter-w 8` on Plain.
- **why it might win:** judged per byte of mechanism state, a slightly-worse-but-half-state arm can win the lab's actual objective (the vote counter's whole claim is state economy). The grid measures loss; this measures the loss/state trade at the hot end.
- **cost:** cheap probe.

### A-097 · SGD-momentum for the shared parts (no AdamW)
- **mechanism:** embeddings, norms, and scales train with plain momentum SGD (lr tuned to 3e-2, momentum 0.9) instead of AdamW in the vote arms.
- **flag-level change:** new flag `--opt sgd` on Direct/Layered.
- **why it might win:** AdamW's per-parameter adaptivity is 8 B/param of state the vote story never accounts for; if momentum-SGD matches it, the direct trainer's true state advantage over STE grows — a verdict about the mechanism's honesty, priced in one probe.
- **cost:** cheap probe.

### A-098 · Weight decay 0.01 on the shared parts (vote arms)
- **mechanism:** AdamW weight decay set to 0.01 for the non-ternary parts of the vote trainers (they have always run wd=0).
- **flag-level change:** new flag `--opt-wd 0.01` on Direct/Layered.
- **why it might win:** the STE recipe grid (pooled) varies wd on the STE chassis; the winning family's own recipe cell is empty. In a model whose ternary weights can't decay, the FP parts' decay shapes everything the ternary side must fit — an untested, one-number change on the champion.
- **cost:** cheap probe.

### A-099 · AdamW betas (0.9, 0.99) for the shared parts
- **mechanism:** the second beta rises from the lab-standard 0.95 to 0.99 in the vote arms' AdamW.
- **flag-level change:** new flag `--betas 0.9,0.99`.
- **why it might win:** β2=0.95 was inherited from Fable's Direct defaults and never varied on ANY arm in the lab; with ~160-step runs, β2 sets the effective averaging window of the second moment (≈20 steps at 0.95 vs ≈100 at 0.99) — at this horizon that is a materially different optimizer, hiding inside a "default".
- **cost:** cheap probe.

### A-100 · Gradient accumulation ×2 for votes (effective batch 64)
- **mechanism:** two micro-batches accumulate before each optimizer/vote step — effective batch 64 reached by accumulation rather than by batch size.
- **flag-level change:** new flag `--accum 2` in the training loop.
- **why it might win:** the pooled batch grid (1201-1203) changes batch size directly, which changes per-step gradient noise AND step count together; accumulation changes the vote evidence per count while holding micro-batch statistics fixed — for a counter, evidence-per-count is the operative variable, so these are not the same experiment.
- **cost:** cheap probe.

## S9 — Objective-adjacent (token loss stays the objective)

### A-101 · Label smoothing 0.05
- **mechanism:** the token loss uses 0.05 label smoothing.
- **flag-level change:** new flag `--ls 0.05` in the loss.
- **why it might win:** ternary heads produce coarse logits; smoothing caps the gradient any single confident-wrong token can inject into the vote stream. Never tried on any arm here, one line, and the vote path is exactly where outlier gradients do structural damage.
- **cost:** cheap probe.

### A-102 · Z-loss on the head logits (1e-4)
- **mechanism:** a penalty of 1e-4 · logsumexp²(logits) added to the loss, keeping logit norms bounded.
- **flag-level change:** new flag `--zloss 1e-4` in the loss.
- **why it might win:** logit growth is the failure mode QK-Clip/MuonClip exist to fight on the attention side; the HEAD side has no governor at all in this lab, and z-loss is the standard one (PaLM lineage). It also stabilizes the loss scale the vote gate's quantiles are computed from.
- **cost:** cheap probe.

### A-103 · Same-head auxiliary next-next-token loss (weight 0.05)
- **mechanism:** the existing head also predicts token t+2 from position t, with loss weight 0.05 — no extra head, no extra parameters.
- **flag-level change:** new flag `--aux-nn 0.05` in the loss.
- **why it might win:** pooled MTP entries add a separate head (parameters + plumbing); the same-head version isolates the pure SUPERVISION-density effect (more signal per window for a token-hungry trainer) from the capacity effect, at zero serving cost.
- **cost:** cheap probe.

### A-104 · EMA self-teacher on the token loss (mean teacher)
- **mechanism:** an EMA copy of the model (decay 0.99) produces soft targets on the same windows; loss = CE + 0.5·KL(EMA || student), all in token space.
- **flag-level change:** new flag `--ema-teach 0.99` in the training loop (EMA state charged, ~7 MB training-only).
- **why it might win:** JEPA is closed — it failed in REPRESENTATION space against a token yardstick. This keeps the teacher idea but stays in token space with the standard loss: the teacher is the model's own smoothed self, the targets are distributions over tokens, and the yardstick is the lab's own. It tests whether ANY teacher signal helps votes, without re-opening the JEPA question.
- **cost:** cheap probe.

### A-105 · Consistency regularization (two-pass KL, dropout 0.05)
- **mechanism:** dropout 0.05 is enabled; each batch is forwarded twice with different dropout masks and a KL penalty between the two predictive distributions is added (weight 0.5).
- **flag-level change:** new flags `--dropout 0.05 --rdrop 0.5` in the model/loss.
- **why it might win:** the lab runs dropout nowhere; discrete weights + no dropout is an unusual regularization vacuum. Consistency loss specifically penalizes predictions that hinge on individual activations — the ones INT8 quantization perturbs.
- **cost:** cheap probe.

### A-106 · Per-token loss clipping (cap 8 nats)
- **mechanism:** each token's loss contribution is clipped at 8 nats before averaging (gradients flow through the clipped value as a constant beyond the cap).
- **flag-level change:** new flag `--loss-clip 8` in the loss.
- **why it might win:** a handful of catastrophic tokens (rare words, markup) can dominate a batch's gradient and therefore its votes; clipping bounds any token's structural say. Distinct from A-040 (norm clipping per layer) — this acts per token, before aggregation.
- **cost:** cheap probe.

### A-107 · Focal-style token weighting (γ=0.5, loss-side)
- **mechanism:** each token's loss is weighted by (1 − p_token)^0.5, down-weighting tokens the model already predicts well — inside the loss, with sampling untouched.
- **flag-level change:** new flag `--focal 0.5` in the loss.
- **why it might win:** failweight (pooled) moves the SAMPLER toward hard windows, changing what the AdamW parts see too; focal weighting moves only the loss geometry, continuously, per token. The pair separates "see hard examples more" from "weight hard examples more" — currently conflated.
- **cost:** cheap probe.

### A-108 · Attention entropy bonus (1e-3)
- **mechanism:** a small bonus (+1e-3 × mean attention entropy) added to the loss, discouraging attention collapse onto single positions.
- **flag-level change:** new flag `--attn-ent 1e-3` in the loss.
- **why it might win:** ternary QK logits are coarse, so attention distributions can collapse early and freeze (the votes then train around a dead routing pattern); a tiny entropy pressure keeps routing plastic. The sink/gate entries treat the symptom architecturally; this treats it in the objective.
- **cost:** cheap probe.

## S10 — Trainer-level structure: populations, resets, inits

### A-109 · Dual evidence streams (two counters, alternating batches)
- **mechanism:** two independent counters per weight; even batches vote into counter A, odd into counter B; a flip requires BOTH counters past V/2 in the same direction (consensus of two evidence streams over one shared lattice).
- **flag-level change:** new flag `--dual-vote` on Layered.
- **why it might win:** a single counter can be stampeded by a correlated run of batches; two streams fed disjoint data that must agree is bagging inside the trainer — variance reduction at the evidence level rather than the readout level.
- **cost:** full trial only (consensus dynamics need the full horizon to separate from plain V effects).

### A-110 · Counter reset at halfway (weights kept)
- **mechanism:** at 50% of the run all counters zero out while the ternary state is untouched — the second half's structure is decided by fresh evidence only.
- **flag-level change:** new flag `--counter-reset 0.5` on Layered/Direct.
- **why it might win:** counters integrate from step 0, so early (near-random-network) evidence still sits in them at the end; a mid-run reset asks whether the first half's evidence is an asset or a contaminant. One flag, and the answer reinterprets every long-run dynamic the lab has recorded.
- **cost:** cheap probe.

### A-111 · Dead-weight revival at halfway
- **mechanism:** at 50%, weights sitting at 0 whose |count| < 4 are randomly re-seeded to ±1 (counters zeroed).
- **flag-level change:** new flag `--revive 0.5` on Layered.
- **why it might win:** a weight at 0 with no accumulated evidence is a dead slot — the counter never found a reason to move it, which at init-noise levels means it never got a fair trial. Revival is the population-genetics fix (mutation of the unfit) inside one network.
- **cost:** cheap probe.

### A-112 · Scale-only polish for STE (freeze ternary, retrain scales/norms)
- **mechanism:** after a standard ste_half run, the ternary weights freeze and only scales + norms train for 10% extra steps.
- **flag-level change:** new flag `--scale-polish` on the STE trainer.
- **why it might win:** A-037 prices this split for votes; the STE version prices how much of ste_half's table-leading 2.8205 is its scale freedom rather than its weight path — a number that bounds what ANY vote variant can hope to win back.
- **cost:** cheap probe.

### A-113 · Majority-of-3 inits
- **mechanism:** three random ternary inits are drawn per run and the starting state is their per-weight majority; counters start at 0.
- **flag-level change:** new flag `--init-majority` in the model builder.
- **why it might win:** init variance is a known share of seed variance in this lab's tables; a majority init is the cheapest variance cut available and, if seed spread shrinks, every subsequent comparison in the mill gets sharper for free.
- **cost:** cheap probe.

### A-114 · Histogram-matched init
- **mechanism:** the init ternary state is drawn to match the final state histogram of a trained plain model (~30% zeros / 35% / 35%) instead of the symmetric random split.
- **flag-level change:** new flag `--init-hist` in the model builder.
- **why it might win:** trained nets converge to a characteristic level histogram; starting there skips the phase where votes merely redistribute mass among levels. Tests whether the histogram itself is part of what training "learns" early.
- **cost:** cheap probe.

---

## Stream A's top 15 (ranked, with reasons)

1. **A-023 · Vote warmup (no flips, first 5%).** The single most direct repair of the mechanism's one PROVEN catastrophe: the anneal arm's 3.850 showed early flips on weak evidence are poison. Every pooled schedule still flips from step 0. One flag, huge prior, tiny cost.
2. **A-022 · Tail freeze (V×3, last 10%).** The conservative half of the cool-down finding — Fable's trace says cooling is the largest cheap effect on their side, and the vote-side forms pooled so far move V across the whole run. A tail-only step change is the form most likely to keep the gain without the schedule's side effects.
3. **A-001 · Soft gate.** Removes the hard median cliff — a defect named in Fable's own records and the direct-trainer study — by a continuous route the calibrated-magnitude entries do not cover. Attacks a known flaw, not a speculation.
4. **A-094 · Average-then-round readout.** Fable's proven readout is an average; the pooled modal readout is a vote. This is the faithful translation, it rides existing checkpoints at ~zero marginal cost, and readout gains (if real) apply to every arm ever run.
5. **A-011 · Momentum-filtered evidence.** Sign-of-EMA is the one momentum placement never tried (the pool decays counters; nothing smooths evidence). Strong signSGD-momentum theory, small state cost, immediate readability.
6. **A-007 · Hysteresis band.** Study candidate C4's missing half. Freezing reacts to oscillation after it happens; hysteresis prevents the cheapest oscillations from starting. If it works, it also stacks with everything.
7. **A-098 · Weight decay 0.01 on vote arms' shared parts.** The champion family's own recipe cell is empty while the STE family's is gridded. One number, on the winning trainer, with a real chance the FP parts are under-regularized.
8. **A-037 · Frozen-structure polish.** Prices the structure-vs-calibration split — a number the whole program needs (it bounds what better vote rules can still win) — and doubles as a candidate improvement.
9. **A-099 · AdamW β2 0.99.** A "default" that is actually an unexamined experimental variable, at a run length where its effect is largest. Nearly free, and the answer propagates to every future arm's recipe.
10. **A-017 · Global flip budget.** Flip rate is the structure's true learning rate and today it is an uncontrolled emergent quantity that varied 2× between recorded arms. Making it a dial is the kind of move that reorganizes a whole results table.
11. **A-041 · Easy-to-hard curriculum.** The entire data-ordering axis is untouched in this lab (uniform sampling everywhere), and the curriculum hypothesis interacts with the vote mechanism's known early-evidence sensitivity in a specific, testable way. A-042 rides as its control.
12. **A-086 · QK-Norm after RoPE.** The pool's rank-1 research item has an untested placement half, and this lab's own history (RoPE adoption) shows placement decisions here are worth real loss. Cheap, and it completes the QK-Norm question whatever it finds.
13. **A-104 · EMA self-teacher (token space).** The disciplined successor to the JEPA loss: same teacher intuition, but the loss and targets stay in token space where this lab's yardstick lives. It converts a closed failure into a sharper question.
14. **A-035 · Grow components mid-run.** The layered idea's best-case entry point. The half-control killed levels-at-equal-size/steps from scratch; growing them from a trained plain net is the one form that was never given its chance, and Arnav's component line deserves its strongest test, not its weakest.
15. **A-059 · Calibrated magnitude votes, full width + rotary.** Completes the calibrated story at the width where the mechanism's state-economy claim actually matters, under the pool's own "calibrated = different arm" precedent. If C1 is real, it should show here too — and if it doesn't, the width interaction is the finding.

## Notes for the pool owner

- Entries A-050 (held-adjacency buffer) is a methods audit, not a performance candidate: if merged, run it once early — its result re-prices confidence in every existing margin.
- Readout entries A-093/A-094/A-095 and A-057 can ride checkpoints from runs already queued; they should not each consume a full probe slot if the screening harness supports eval-only attachments.
- Several S6 combinations are explicitly sequenced (A-062/A-063 after their singles read; A-064/A-065 are full-trial forms of pooled singles) — they are listed now so the combination layer exists in one place, not because they should jump the queue.
- Count: **114 candidates (A-001…A-114)**, all disjoint from the 175 pooled entries, the closed arms, and the research report's do-not-test list, by construction against the files listed in the method section.
