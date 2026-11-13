# CANDIDATES-G — Idea Engine wave G (Muse's work, Muse's side)

<!-- Muse's work — Muse's side of the BitNet lab. Produced 2026-11-12 by the Idea Engine
(rotation 2: continuous parts, data construction, readout, mill methodology, model
composition, throughput) under Arnav's no-limit ideation order. This is a CANDIDATE file:
nothing here is in the pool until the pool's owner merges it. IDEA-POOL.md was read by
every miner and NOT edited. Wave F is CANDIDATES-F.md; hive-side output lives in
factory/CANDIDATES-IDEAS.md. -->

## Method and de-duplication

Every miner deduped against IDEA-POOL.md (368 entries), CANDIDATES-A/B/C/D/E/F and
FABLE-CANDIDATES.md. Nothing closed re-proposed (overshoot carry, AdamW cooldown,
threshold anneal 8→64, magnitude votes as specified, JEPA objective). **Convergence
flag:** G-037 and G-063 were derived independently by two miners (methodology and
throughput) — both found that a trial whose first 2 seeds both miss the reference mean
can never pass the ≥2-of-3 per-seed adoption guard, so seed 3 is provably wasted.
Independent re-derivation is evidence; at pool-merge time they should land as ONE entry
(G-037's simple form plus G-063's shared stale-guard control).

**Chassis / bars** as in wave F: champion held 2.8580 ± 0.0161; adoption >2sd AND >0.01;
probe 75s vs job zero; trial 3 seeds × 8 min. Readout entries (G-025..G-036) are mostly
eval-only against the SAME trained weights — the cheapest entries in either wave.
Methodology/throughput entries (G-037..G-048, G-061..G-072) change the mill, not the
trainer; their payoffs are stated in probes/hour and trial-hours.

## Coordinator's top 3 for this wave ★

1. **G-037 · Trial futility stop** — pure arithmetic on the existing adoption guard:
   when the first 2 trial seeds both fail the reference mean, skip seed 3 and save
   8 minutes per doomed trial at zero false-rejection risk. No statistics, no
   calibration; starts paying from the mill's first trial. (Twin: G-063.)
2. **G-026 · Counter-resolved readout** — the final counters are clamped ±32 and
   discarded unread; applying the pending flips where |counter| ≥ τ before install
   costs ≤3 eval passes, no retraining, and tests information that provably exists.
   Predicted −0.01..−0.04.
3. **G-001 · Per-part lr ratio** — five prior entries traced one global lr for a group
   whose members differ by ~5 orders of magnitude in parameter count; the RATIO
   (log_scale 3e-3 / embedding 3e-4 / norms 1e-3) was never tested, and the plumbing
   unlocks G-005 and G-007 in the same pass.

**Boldest entry in the wave: G-050 · Counter-sum merge** — merge independently trained
runs in latent counter space (L = 32·t + c) instead of weight space, shipping one model
under champion bytes; paired with G-053 so "do counters merge better than weights?" gets
one clean answer.

---

## Lens 1 — Continuous parts (was CP-###)

### G-001 · Per-part lr ratio: scales hot, embeddings cold, norms at champion ★
- **source:** continuous-parts lens — the AdamW group lumps a 786k tied embedding table, ~2.3k norm/bias params, and 8 scalar log_scales under one lr. The pooled lr family (MILL-304/305 at 3e-3/3e-4, C-B01..04 interior points) only ever moved them together, so the record cannot distinguish "1e-3 is right" from "1e-3 is the average of a too-hot scale and a too-cold embedding."
- **mechanism:** three param groups with fixed lr ratios: log_scale at 3e-3 (3×), token embedding at 3e-4 (0.3×), norms + BitLinear biases at the champion 1e-3. Rationale per part: a log_scale is one scalar per layer whose hand-set gradient already aggregates the whole layer — it is the slowest-moving quantity per unit of function change and can afford heat; the tied embedding is also the head, its rows receive gradient from every position of every window, and at 1e-3 it is the part most likely to chase the still-moving ternary structure; norms/biases stay at the proven point as the control inside the arm.
- **train.py:** new flag `--part-lr scale:3e-3,emb:3e-4,norm:1e-3` on Layered — split the single AdamW group in `Layered.__init__` into three groups (log_scale params / `model.tok.weight` / everything else) with those lrs; betas (0.9, 0.95) and wd 0.0 unchanged in all groups.
- **mode:** process
- **prediction:** −0.02..−0.05 vs champion 2.8580 at trial scale; ~−0.01 at probe. If it lands flat while MILL-304 (global 3e-3) also reads flat, the parts' lr sensitivities cancel — itself a load-bearing fact that retires the whole lr family with a reason.
- **status:** queued
```mill
id: G-001
mode: process
run: --arm layered_half --rope --part-lr scale:3e-3,emb:3e-4,norm:1e-3
```

### G-002 · Flip-servoed continuous lr: AdamW speed follows flip share ★
- **source:** continuous-parts lens + RESULTS-ROUND2-2026-11-12 — the cooldown record's own diagnosis is that the FP parts were *starved* while the ternary side kept moving; F-037 answers with a clock-based rise. Neither couples the continuous speed to the discrete side's actual activity, which the trainer already measures every step (`step()` returns flip share, champion mean ≈ 0.0011).
- **mechanism:** the embedding + norm/bias groups' lr is servoed to the trailing 20-step mean flip share φ: multiplier = clip(0.0011/φ, 0.5, 2.0) applied to base lr 1e-3 each step. When structure churns (φ high), the continuous parts slow down instead of fitting a network that is about to change; when flips settle (φ low), they speed up to fit the structure that actually exists. log_scale is exempt (it is part of the install geometry, priced separately in G-003/004). The vote rule never sees this — flips are neither halted (F-027) nor rationed; only the FP parts' step size breathes. Not a schedule: at constant flip share the lr is constant forever, at any run length.
- **train.py:** new flag `--flip-servo` on Layered — per-step lr multiplier on the emb/norm param groups from the EMA of returned flip shares; log_scale group untouched.
- **mode:** process
- **prediction:** −0.01..−0.04 at trial scale. Diagnostic logged either way: correlation between φ and held-loss slope per 20-step window — if high-churn windows are not where continuous fitting is wasted, the servo has no signal to ride and the probe shows it.
- **status:** queued
```mill
id: G-002
mode: process
run: --arm layered_half --rope --flip-servo
```

### G-003 · log_scale trust region: per-step move clamped to ±2% ★
- **source:** continuous-parts lens — `install()` rescales an entire layer by exp(log_scale); the hand-set gradient `(g·s).sum()·scale` sums over up to ~590k weights, so a single AdamW step on log_scale after an atypical batch can shift every installed magnitude in the layer at once — and because the assignment happens after clipping, no bound of any kind applies to it today.
- **mechanism:** after each `opt.step()`, clamp each layer's log_scale change for that step to ±0.02 in log space (≤ ~2% multiplicative rescale per step, either direction). The gradient, lr, and Adam state are untouched — only the realised per-step displacement is bounded, a trust region on the one parameter whose step is layer-wide. Distinct from F-024 (servo *replaces* the gradient path with an activity rule) and F-001 (adds a second, vote-derived contribution to log_scale): this keeps the champion's exact update and bounds its step.
- **train.py:** new flag `--scale-trust 0.02` on Layered/Direct — snapshot log_scale before `opt.step()`, clamp the delta after, inside `step()`.
- **mode:** process
- **prediction:** −0.01..−0.03, concentrated in variance: seed sd should shrink vs the champion's 0.0161 even if the mean gain is small, because the clamped events are the rare large-rescale steps that plausibly drive seed divergence. A flat mean with halved sd still promotes — it makes every other probe in the mill sharper.
- **status:** queued
```mill
id: G-003
mode: process
run: --arm layered_half --rope --scale-trust 0.02
```

### G-004 · Flip-gated log_scale: scales move only on steps their layer flipped
- **source:** continuous-parts lens — today log_scale updates on *every* step, including the ~99.9% of weights' worth of steps where its layer's installed structure did not change at all; on those steps the scale is fitting gradient noise against a fixed code. The scale's real job is re-fitting magnitude *after* the code moves.
- **mechanism:** per layer, the log_scale AdamW update is applied only on steps where that layer recorded ≥1 flip; on no-flip steps its gradient is zeroed for that step (Adam moments still age — stated plainly, that decay of stale moments is part of the design). Embeddings, norms, biases train every step as champion. This is event-gating of an existing update, the mirror image of F-001: F-001 *adds* boundary-vote pressure into log_scale; G-004 *withholds* the ordinary gradient update until a flip gives it something to calibrate. A-037/D-006 freeze whole sides on a clock or in dream phases; this freeze is per-layer and fired by the layer's own flips.
- **train.py:** new flag `--scale-flipgate` on Layered — zero `log_scale[i].grad` on steps where layer i's flip count (already computed as `go1/go2` sums) is 0.
- **mode:** process
- **prediction:** −0.01..−0.03 at trial scale, ~0 at probe (early flips are frequent, so the gate is mostly open at probe horizon — judge at trial). Side measurement: log_scale total path length should fall sharply; if loss is unchanged at a fraction of the path, most scale motion was noise-chasing.
- **status:** queued
```mill
id: G-004
mode: process
run: --arm layered_half --rope --scale-flipgate
```

### G-005 · Weight-decay scope: decay the embedding only, scales and norms exempt
- **source:** continuous-parts lens + C-B07's own caveat — the pooled wd points (A-098 at 0.01, C-B07 at 0.1) apply decay to the whole AdamW group, and C-B07's entry already flags the entanglement: decoupled decay on log_scale shrinks the installed step size toward scale 1.0, an arbitrary target for a log-parameter whose init is the layer's measured absmean. A global wd reading therefore mixes a plausible embedding regulariser with a scale-shrink artefact.
- **mechanism:** wd 0.01 applied to the token-embedding group only; log_scale, norms, and biases run wd exactly 0.0. One variable against the champion (wd 0 everywhere) and one against A-098 (wd 0.01 everywhere): the pair of readings splits A-098's verdict into its parts.
- **train.py:** new flag `--wd-scope emb --opt-wd 0.01` on Layered — per-group `weight_decay` in the AdamW construction (needs the group split of G-001, shares its plumbing).
- **mode:** process
- **prediction:** −0.01..−0.03 if the embedding is the under-regularised part (it is the largest FP block and the head); if A-098 reads positive and this reads flat, A-098's gain was the scale-shrink artefact and the wd family re-reads accordingly.
- **status:** queued
```mill
id: G-005
mode: process
run: --arm layered_half --rope --opt-wd 0.01 --wd-scope emb
```

### G-006 · Optimizer split: plain SGD for log_scale, AdamW for everything else
- **source:** continuous-parts lens — log_scale's gradient is already a hand-normalised layer aggregate (`(g·s).sum()·exp(log_scale)`); running it through AdamW divides it by a running root-mean-square of *itself*, which for a single scalar per layer mostly erases the magnitude information the hand-set gradient deliberately carries (a layer whose gradients double gets the same Adam step as one whose halve). A-097 tests SGD for the *whole* shared group; the split by part has never run.
- **mechanism:** log_scale params leave AdamW and train by plain SGD, lr 1e-4, no momentum (the update is then proportional to the hand-set gradient, as the install formula's design implies); embeddings, norms, biases keep champion AdamW (1e-3, betas (0.9, 0.95)) untouched.
- **train.py:** new flag `--scale-opt sgd:1e-4` on Layered — second optimizer instance stepped alongside `self.opt` in `step()`; log_scale removed from the AdamW group.
- **mode:** process
- **prediction:** −0.01..−0.04. Diagnostic: per-layer log_scale trajectories — under AdamW they should look near-constant-velocity (sign-like); under SGD they should track gradient magnitude. If the loss is flat under both, the scale's *dynamics* don't matter, only its endpoint, which re-prices G-003/004 downward honestly.
- **status:** queued
```mill
id: G-006
mode: process
run: --arm layered_half --rope --scale-opt sgd:1e-4
```

### G-007 · Per-part betas: fast moments for log_scale, champion moments elsewhere
- **source:** continuous-parts lens — the pooled betas entries (A-099 (0.9, 0.99), C-B08 (0.9, 0.999), C-B09 (0.85, 0.95)) move betas globally, but the parts' gradient streams have opposite stationarity: embedding/norm gradients are comparatively steady, while log_scale's hand-set gradient is a *function of the current ternary state* — every flip in its layer changes what its next gradient means, so a β2 horizon of ~20 steps (0.95) averages moments across different installed networks.
- **mechanism:** log_scale group runs betas (0.5, 0.90) — first-moment horizon ~2 steps, second-moment ~10 — so its adaptive rate tracks the current structure; embedding and norm/bias groups keep (0.9, 0.95) exactly. β1/β2 move together for the scale only, the combination no global entry tests.
- **train.py:** new flag `--part-betas scale:0.5,0.90` on Layered — per-group betas in the AdamW construction (shares G-001's group split).
- **mode:** process
- **prediction:** −0.01..−0.03 at trial scale; expected ~0 at probe (few flips have landed, so staleness has barely accumulated — a probe flat does not kill). If it wins, the reading generalises: any parameter whose gradient is state-dependent wants short moments in a vote-trained net.
- **status:** queued
```mill
id: G-007
mode: process
run: --arm layered_half --rope --part-betas scale:0.5,0.90
```

### G-008 · Early log_scale hold: scales frozen for the first 20%, then released
- **source:** continuous-parts lens — at init the ternary state is a rounding of random FP weights, and the first flips are the run's noisiest (the anneal record's lesson about early evidence). Through that phase log_scale trains freely, so the install geometry the early votes vote *against* is itself drifting; the early structure forms inside a moving frame. No pooled entry freezes the scales early: A-037 freezes the *ternary* side late, D-006 freezes AdamW inside dream phases, A-039 *ramps* all FP lr from step 0 (the scales still move, just slowly at first).
- **mechanism:** log_scale params are held at their init values (the per-layer absmean at install) for the first 20% of steps — grads zeroed, no Adam state accumulated — then released at full champion AdamW settings for the remaining 80%. Embeddings and norms train from step 0 unchanged, so this is not a warmup: exactly one part is held, and it is held at a *meaningful* value (the measured init scale), not at a ramp.
- **train.py:** new flag `--scale-hold 0.2` on Layered — zero log_scale grads and skip its Adam moments while `done < 0.2`.
- **mode:** process
- **prediction:** −0.01..−0.03. Falsifier built in: log held at the 20% boundary vs champion's same-step held — if the held scales cost nothing even *during* the hold, scale motion in the first fifth was never earning anything and the entry's premise (not just its fix) is measured.
- **status:** queued
```mill
id: G-008
mode: process
run: --arm layered_half --rope --scale-hold 0.2
```

### G-009 · Per-group gradient clipping: the clip stops being one joint budget
- **source:** continuous-parts lens — in `Layered.step`, `clip_grad_norm_(…, 1.0)` rescales the *joint* norm of embeddings + norms + biases. The embedding table's gradient norm dwarfs the norms'/biases' by orders of magnitude, so on clipped steps the small parts' updates are shrunk by a factor set almost entirely by the embedding's behaviour that step — the parts share a clip budget none of them chose. (log_scale is not in the clip at all — see G-003.)
- **mechanism:** clip each param group separately at 1.0: embedding group, norm+bias group — each group's realised step is governed by its own gradient scale. Vote path untouched (A-040 clips layer gradients *before signing*, a different site and purpose).
- **train.py:** new flag `--clip-scope group` on Layered/Direct — replace the single `clip_grad_norm_` call with one call per AdamW param group in `step()`.
- **mode:** process
- **prediction:** −0.01..−0.03, with the mechanism checkable in logs: fraction of steps where the joint clip actually binds, and the norm/bias groups' realised update norms before vs after. If the joint clip binds on <5% of steps, the entry retires itself as a non-effect, cheaply.
- **status:** queued
```mill
id: G-009
mode: process
run: --arm layered_half --rope --clip-scope group
```

### G-010 · Adam-state reset for log_scale at the midpoint (stale-moment purge)
- **source:** continuous-parts lens — by mid-run a layer's ternary state has flipped hundreds of times since init; its log_scale's Adam second moment is an average over gradient regimes belonging to installed networks that no longer exist. A-110 resets the *vote counters* at halfway (weights kept); nothing has ever reset an *optimizer's* state mid-run on any part.
- **mechanism:** at 50% of steps, the AdamW exp_avg / exp_avg_sq for the log_scale params only are zeroed (parameters themselves untouched — the next steps re-estimate moments against the current structure, with bias correction doing its usual early-run work). Embedding/norm moments are *not* reset: they are the within-entry control, since their gradients are far less state-dependent (G-007's premise, tested from the other side).
- **train.py:** new flag `--adam-reset scale@0.5` on Layered — zero the optimizer state tensors of the log_scale group once, at the step where `done` crosses 0.5.
- **mode:** process
- **prediction:** −0.005..−0.02 — the smallest expected effect in this file, included because it is a one-line, zero-risk probe of a question (does optimizer state go stale across flip regimes?) that G-007 also touches; the pair read together separates "shorter moments help" from "old moments hurt."
- **status:** queued
```mill
id: G-010
mode: process
run: --arm layered_half --rope --adam-reset scale@0.5
```

### G-011 · Shared second moment: log_scale and its layer's norm gains pool one v̂
- **source:** continuous-parts lens — the task's optimizer-state-sharing axis, made concrete: a BitLinear layer's log_scale and the *preceding* LayerNorm's gain act on the same activation stream (norm sets its distribution, scale sets the installed step that quantises it), yet AdamW keeps fully independent second moments for them, each estimated from few effective samples (one scalar; one vector). Pooling the v̂ estimate across the pair gives both a stabler adaptive rate for the quantity they jointly control — the layer's dynamic range.
- **mechanism:** for each block, the log_scale params of its BitLinears and that block's n1/n2 gain vectors share one pooled second-moment estimate (v̂_pooled = mean of the members' v̂, applied to all members); first moments and parameters stay separate, betas/lr unchanged. This is state *sharing between parts*, distinct from B-016/B-019 (state *compression* within one optimizer) and A-014 (a shared *vote counter*, ternary side).
- **train.py:** new flag `--adam-share-v scale-norm` on Layered — custom step wrapper that overwrites the log_scale and norm-gain exp_avg_sq entries with their per-block pooled mean before the AdamW update.
- **mode:** process
- **prediction:** −0.005..−0.02, honestly speculative — the prior is variance reduction on the noisiest adaptive rates in the group, and the downside is bounded by the same argument (pooling can only pull each rate toward the pair's mean). A flat result closes the state-sharing axis with a number instead of an assumption.
- **status:** queued
```mill
id: G-011
mode: process
run: --arm layered_half --rope --adam-share-v scale-norm
```

### G-012 · Tied-embedding row max-norm: cap the rows that are also the head
- **source:** continuous-parts lens — the embedding is tied, so each row is simultaneously an input vector and an output classifier direction: a frequent token's row receives gradient from both roles every step and can grow until its logit dominates by norm rather than by fit, injecting outsized, frequency-driven gradients into every vote its windows touch. No pooled entry constrains embedding geometry at all (MILL-118/119 price its precision and tying, A-091 norms its output, none bound the rows).
- **mechanism:** after each AdamW step, any embedding row with L2 norm > 1.0 is rescaled to exactly 1.0 (projected update, word2vec-style max-norm). Init row norms sit near 0.02·√192 ≈ 0.28, so the cap binds only on rows that grew ~3.5× — a constraint on runaway rows, not a shrinkage of the table. Votes, scales, norms untouched.
- **train.py:** new flag `--emb-maxnorm 1.0` on Layered/Direct — row-wise norm clamp on `model.tok.weight` after `opt.step()` in the training loop.
- **mode:** process
- **prediction:** −0.01..−0.03 if head-norm domination is real at this scale; the run logs the binding fraction (rows at cap) per phase — if it stays at 0% throughout, the constraint never existed and the entry is void, not wrong. Per-byte neutral: no parameters added.
- **status:** queued
```mill
id: G-012
mode: process
run: --arm layered_half --rope --emb-maxnorm 1.0
```

---

## Lens notes for the pool owner

- All 12 are `mode: process` honestly — every one needs param-group plumbing or a
  step-hook train.py does not have; screen.py should DEFER them until their flags
  land. G-001's three-group split is shared plumbing for G-005 and G-007: wire
  it once, three entries become runnable.
- Closed-form guard, stated once for the whole file: nothing here decays any FP
  lr in a second stage. G-002's servo is symmetric (it rises as readily as it
  falls) and driven by flip share, not by `done`; G-008 holds one part at its
  init value and releases it *up* to full lr. Neither is the closed cooldown in
  new clothes.
- Cheapest first contact: G-003 and G-010 are each a few lines and act on the
  parameter class with the least existing instrumentation; their logs (scale path
  length, per-step delta distribution) are worth having before G-001's wider
  plumbing lands.
- The idea I believe in most is **G-001**: the lab has spent five entries
  (MILL-304/305, C-B01..04) tracing one global lr curve for a group whose members
  differ by five orders of magnitude in count and by construction in gradient
  character. The ratio was always the variable; the level was the average hiding it.

*End of wave-2 lens 1. 12 entries (G-001..G-012), all on the champion chassis,
all continuous-parts, none duplicating IDEA-POOL.md, CANDIDATES-A/B/C/D/E/F, or
FABLE-CANDIDATES.md.*

## Lens 2 — Data construction (was DC-###)

### G-013 · Boundary-masked line packing ★
- **source:** data-construction derivation from DATA-AUDIT §7 + train.py's slicing — v2's median
  line is 36 pieces, so the champion's windows each splice ~7 unrelated line/document fragments
  and train full CE on the seams: the model is paid to predict the first tokens of a lab note
  from the tail of a German sentence. No pooled entry touches packing at all (the architecture
  report's do-not-test list even set packing aside as "kernel-only" — for the vote trainer it is
  an evidence-quality question, not a kernel question).
- **mechanism:** Build windows by **packing whole lines** in stream order until 256 pieces are
  filled (last line truncated only if it alone exceeds 256), and **mask out of the CE sum** every
  target position whose prediction crosses a line start — i.e. the first target after each BOS
  inside the window contributes no loss and no gradient. All other positions train exactly as
  champion. The vote stream then integrates only within-document evidence; seam positions stop
  casting systematically misleading votes ~7 times per window.
- **exact change:** corpus-builder + runner change — `make_corpus_v2.py` variant emits a
  line-boundary sidecar for the stream; train.py gains `--pack-mask` (batch builder packs from
  the sidecar instead of slicing offsets; CE computed with a per-position mask). Applies to v2
  first; v3 form is G-024's territory.
- **mode:** process
- **prediction:** −0.02..−0.06 at trial scale on v2-native held. Reasoning: ~7/256 ≈ 3% of
  positions are seam targets, but they are the *highest-loss, most contradictory* positions in
  every window — exactly the gradients whose signs disagree batch-to-batch and cancel inside
  the counters. Removing them should raise flip efficiency (fewer wasted votes) measurably:
  log flip share and counter-reversal rate alongside held.
- **contamination control:** packing draws lines only from the non-held side — any line that
  appears inside a held block (exact-line match, the v3 builder's test) is excluded from the
  pack stream, and held windows are constructed exactly as today (every-40th block, unpacked)
  and never packed, masked, or trained on. Runner asserts `packed_held_overlap = 0` per run.
- **status:** queued
```mill
id: G-013
mode: process
run: --arm layered_half --rope --corpus v2 --pack-mask
```

### G-014 · Sequential stream walk (read the corpus, don't sample it) ★
- **source:** data-construction derivation — `offsets()` is i.i.d. sampling and has never been
  varied in any record the lab owns; every curriculum entry (A-041ff) reorders *scored windows*
  but keeps i.i.d. draws underneath. A vote counter is an integrator with a ~32-vote memory:
  the *temporal coherence* of its evidence stream is a property of the sampler, and i.i.d.
  sampling is the zero-coherence extreme.
- **mechanism:** Replace i.i.d. offsets with a **contiguous walk**: the run reads the legal
  (non-held) stream in order, one non-overlapping 256-piece tile after another, batch = 32
  consecutive tiles, reshuffling tile order only at pass boundaries (two arms in one entry:
  strict stream order, and per-pass shuffled tiles — the pair separates "contiguity within the
  batch" from "global order"). Each legal piece is seen exactly once per pass.
- **exact change:** train.py flag `--sampler stream|stream-shuffled` replacing the `offsets()`
  call in the training loop; tiles are the stream cut at fixed 256 boundaries, held tiles
  skipped by the same predicate `offsets()` uses today.
- **mode:** process
- **prediction:** −0.01..−0.05 for stream-shuffled; strict stream order is the high-variance
  arm (local topics give counters long agreeing runs — fast early flips, but German-only
  stretches are a forgetting risk, read against G-019). Diagnostic either way: flip share in
  the first 25% of steps vs the i.i.d. champion — coherence should show there first.
- **contamination control:** the walk enumerates only tiles that pass the existing held
  predicate (a tile is legal iff neither its first nor last block index is ≡ 0 mod 40, the
  `offsets()` test applied to tile boundaries); held tiles are skipped, never split, and the
  runner logs `tiles_total / tiles_held_skipped` and asserts no trained tile overlaps a held
  block.
- **status:** queued
```mill
id: G-014
mode: process
run: --arm layered_half --rope --sampler stream-shuffled
```

### G-015 · Content-based held moat: 8-gram exclusion + ±16-block positional moat ★
- **source:** DATA-AUDIT §4 (held content routinely recurs in training windows on v1) +
  A-050's known limit — A-050 excludes only windows within ±2 *positions* of a held window,
  but duplication in this corpus is **content-scattered, not position-local**: a held window's
  lines recur hundreds of blocks away (license text, repeated report scaffolding), where a
  positional buffer never looks. E-019 prices this by rebuilding v1; this entry enforces it in
  the sampler, on any corpus, with no rebuild.
- **mechanism:** A training offset is legal only if (a) its window shares **no 8-token shingle**
  with any held window (shingle sets precomputed once per corpus, charged to wall-clock), and
  (b) it sits at least **16 blocks** from the nearest held block. Everything else is champion.
  On v2 (all lines unique) the shingle test should exclude almost nothing beyond the positional
  moat — that near-zero count is itself the verification that v2 held numbers are clean; on v1
  the excluded fraction prices the leak in sampler units.
- **exact change:** train.py flag `--held-moat 16,8` in `offsets()` (shingle index built at
  runner start from the held windows only; legality test replaces the current two-endpoint
  predicate). No corpus file is modified.
- **mode:** process
- **prediction:** On v1: held worsens by +0.02..+0.10 vs 2.8580 — a *worse* number that is the
  deliverable (the honest v1 reference, complementing E-018's v2 number). On v2: held within
  ±0.01 of the v2 re-baseline (E-018) if v2 is as clean as its build log claims. Any v1 arm
  whose margin over champion is smaller than this entry's Δ must be re-read.
- **contamination control:** this entry *is* the contamination control. The shingle test runs
  against the exact 128 held windows used for judging (not a proxy set), the exclusion is
  applied before any training draw, and the runner logs `offsets_rejected_shingle`,
  `offsets_rejected_moat`, and asserts a post-hoc audit pass over every offset actually
  trained on returns zero held-shingle collisions.
- **status:** queued
```mill
id: G-015
mode: process
run: --arm layered_half --rope --held-moat 16,8
```

### G-016 · Mixture-order period sweep on v2 (fixed ratios, three alternation periods)
- **source:** data-construction lens on v2's actual mix (German 45.7% / HiveMIND docs 41.9% /
  lab notes 12.4%, DATA-AUDIT §7). B-001 changes mixture *ratios* across coarse stages;
  A-053 imposes a per-batch file-diversity floor. Neither varies the **period** at which
  sources alternate inside a run at fixed global ratios — and period is the variable a vote
  counter is most sensitive to, because a 16-step single-source block lets one source's
  evidence climb counters uninterrupted, then the next source's block votes against it.
- **mechanism:** Three arms, identical v2 mixture ratios, identical total tokens: (a) fully
  shuffled offsets (champion-equivalent control), (b) **batch-grain round-robin** — each batch
  of 32 is composed ~15 German / ~13 HiveMIND / ~4 lab-note windows, every batch, (c)
  **block-grain rotation** — 16 consecutive steps draw from one source only, rotating
  German → HiveMIND → lab. The (b)-vs-(c) gap at fixed ratios is the pure order effect.
- **exact change:** train.py flag `--mix-order shuffle|batch|block16` (sampler partitions
  legal offsets by source class using the v2 build's per-file provenance; batch builder
  composes per arm). Source tags come from `corpus-v2.json`, no corpus rebuild.
- **mode:** process
- **prediction:** batch-grain beats shuffled by −0.01..−0.04 and beats block16 by −0.02..−0.05:
  per-batch source balance makes every vote a vote on the full mixture, while block16 spends
  its middle steps un-flipping the previous block's structure (watch cross-block flip-reversal
  rate — predicted highest in (c)). If all three tie, within-run order is a dead axis at this
  scale and B-001's stage question is the only mixture question left.
- **contamination control:** source partitioning is applied to legal offsets only — the held
  predicate runs first, per source, and each source's sampler asserts zero held-block overlap
  independently, so no source arm can re-admit a held window the unified sampler would reject.
- **status:** queued
```mill
id: G-016
mode: process
run: --arm layered_half --rope --corpus v2 --mix-order batch
```

### G-017 · Stride-64 overlap lattice (each token testifies at four positions)
- **source:** data-construction derivation — with random offsets, a token's *position inside
  its window* is whatever chance assigns, and most corpus positions are never sampled at all
  in a ~160-step run (5,120 windows over 907k v2 pieces ≈ 1.4 passes, unevenly). Overlap and
  stride have never been set deliberately; the architecture report excluded packing/kernel
  ideas but never priced designed overlap for a vote trainer.
- **mechanism:** Tile the legal stream at **stride 64** (256-piece windows overlapping by
  75%): every token appears in exactly 4 windows, at 4 different window positions (p, p+64,
  p+128, p+192 phase classes). Windows are dealt in shuffled lattice order at equal *steps*
  to champion (so tokens-seen is matched; unique-token coverage per run falls 4× — that trade
  is the measurement, stated plainly, against A-055/G-021's coverage pole).
- **exact change:** train.py flag `--stride 64` (offsets restricted to the stride-64 lattice
  over legal starts; legality = the window passes the held predicate at both ends, as today).
- **mode:** process
- **prediction:** −0.01..−0.04 at equal steps if position-phase diversity is the active
  ingredient (the same text voting from four RoPE phases is four partially independent
  witnesses — the counter integrates them like extra data); +0.02..+0.05 if unique coverage
  dominates, which would jointly confirm G-021's premise from the opposite side. The pair
  G-017/G-021 brackets the overlap dial with the champion in the middle.
- **contamination control:** lattice starts are filtered by the unchanged held predicate
  *before* dealing — any lattice window whose span touches a held block is removed from the
  lattice entirely (not shifted to a legal neighbour, which would silently change the stride),
  and the removed count is logged.
- **status:** queued
```mill
id: G-017
mode: process
run: --arm layered_half --rope --corpus v2 --stride 64
```

### G-018 · BOS-anchored window starts (position 0 is always a real beginning)
- **source:** data-construction derivation from v2's line structure — random offsets start
  ~255/256 of windows mid-line, so position 0's statistics are "arbitrary mid-document
  token," and the carried position table + RoPE spend their early positions on fragments.
  No entry constrains *where in a line* a window may start.
- **mechanism:** Window starts are restricted to **BOS positions** (line starts) in the legal
  stream: every window opens with a genuine document/line onset and its first line is whole.
  Control arm in the same entry: anti-anchored starts (starts at line-midpoint ±0 only) —
  the pair prices anchoring itself rather than any particular text. Token budget, ratios,
  and all else champion.
- **exact change:** train.py flag `--anchor bos|mid` in `offsets()` (legal-start set
  precomputed from the stream's BOS positions; the held predicate applied to the anchored
  start exactly as to a random one).
- **mode:** process
- **prediction:** −0.01..−0.03 for BOS-anchored. The effect should concentrate in early-position
  loss (log per-position held loss: positions 0–31 improve most). If the anti-anchored control
  matches it, start-phase is irrelevant and G-023's dither premise dies with it — the entry
  is designed to be decisive for both.
- **contamination control:** anchoring never relaxes exclusion — an anchored start is legal
  only if its full window passes the existing held predicate, and BOS positions *inside* held
  blocks are excluded from the start set at construction (asserted count logged).
- **status:** queued
```mill
id: G-018
mode: process
run: --arm layered_half --rope --corpus v2 --anchor bos
```

### G-019 · German placement on v2: first, last, or interleaved (the majority-source order test)
- **source:** v2-specific construction (DATA-AUDIT §7): 45.7% of the clean corpus is one
  language (German Tatoeba sentences) and 54.3% is English project prose. F-032 orders *junk
  vs clean*; B-001 stages *ratios*. Nobody has placed a single dominant source at different
  run positions at fixed ratio — and for a vote counter the placement question is a forgetting
  question: does the last-seen source's structure overwrite the first's, since late flips face
  no further counter-evidence?
- **mechanism:** Three arms at the identical 45.7% German share: (a) German block first
  (steps 0–46% German-only, then English-only), (b) German block last, (c) shuffled control.
  Judged on the pooled v2 held **and** on per-source held slices (German-majority held windows
  vs English-majority held windows reported separately) — the slice gap is the mechanism's
  signature, the pooled number alone cannot see it.
- **exact change:** train.py flag `--src-place de-first|de-last|shuffle` (sampler-level, v2
  provenance tags as in G-016; per-source held slicing is an eval-side tag on the standard
  held windows, no new held data).
- **mode:** process
- **prediction:** de-last wins the German slice by ≥0.08 over de-first and loses the English
  slice by a smaller margin; pooled, de-last −0.01..−0.03 vs shuffled if recency dominates,
  or shuffled wins pooled if interference is symmetric. Any of the three outcomes sets the
  default ordering policy for every future multi-source corpus (v3 included).
- **contamination control:** both blocks draw only from offsets passing the held predicate
  within their own source partition; the per-source held slices are a *tagging* of the same
  untouched 128 held windows, so no held window is ever trained on in any arm and slice
  membership cannot leak into sampling.
- **status:** queued
```mill
id: G-019
mode: process
run: --arm layered_half --rope --corpus v2 --src-place de-last
```

### G-020 · Duplicate-adjacency spacing: near-dupes must wait 32 steps (kept, not removed)
- **source:** data-construction derivation from DATA-AUDIT §4 — on v1, 30.8% of pieces are
  exact-duplicate copies and i.i.d. sampling deals near-identical windows back-to-back by
  chance; for a counter, two identical windows 3 steps apart are not two witnesses, they are
  one witness counted twice at full strength, and they can push a weight across V=32 on what
  is effectively a single observation repeated. A-047 *removes* near-dupes, F-048 *discounts
  their votes* inside the trainer — neither keeps the data and fixes only its **spacing**.
- **mechanism:** The sampler keeps a last-dealt step per 8-gram shingle signature; a candidate
  window sharing any signature with a window dealt in the previous **32 steps** is deferred
  to a holding queue and dealt only after the gap clears (never dropped; total tokens and
  window multiset identical to control by construction — only the order changes).
- **exact change:** train.py flag `--dup-gap 32` (sampler wrapper around `offsets()` with a
  signature ring buffer; deferral queue drained in FIFO order whenever the gap allows).
- **mode:** process
- **prediction:** On v1: −0.01..−0.04 vs champion (spacing breaks up duplicate vote-storms;
  watch the flip-reversal rate fall). On v2: ~0 expected — v2 has no duplicate lines, so a
  v2 win would falsify the mechanism and indict shingle collisions instead; run v1 first,
  v2 as the built-in negative control.
- **contamination control:** spacing operates only on the legal-offset stream (held predicate
  applied upstream, unchanged); deferral never substitutes a replacement window from outside
  the legal set, and the queue is flushed by re-dealing deferred legal windows, so no held
  window can enter through the spacing machinery.
- **status:** queued
```mill
id: G-020
mode: process
run: --arm layered_half --rope --dup-gap 32
```

### G-021 · Without-replacement epoch deck (every legal window exactly once per pass)
- **source:** data-construction derivation — `offsets()` samples **with replacement**: at
  trial scale (160 steps × 32 = 5,120 draws) some windows are drawn 3+ times while a large
  share of the legal stream is never drawn, purely by birthday-paradox arithmetic. A-055
  *weights* unseen windows higher but still samples with replacement, so collisions persist;
  B-009 counts epochs but keeps the same sampler. The strict deck has never been run.
- **mechanism:** Enumerate all legal block-aligned starts once, shuffle them into a deck,
  deal without replacement; reshuffle a fresh deck only when the first is exhausted. At
  probe/trial scale on v2 this guarantees maximum unique coverage per step — the exact
  opposite pole from G-017's designed overlap, with the champion's i.i.d. sampler between
  them.
- **exact change:** train.py flag `--sampler deck` (deck built at runner start from legal
  starts; seed-disciplined shuffle via the run's own RNG stream, per the dream protocol's
  seed rules).
- **mode:** process
- **prediction:** −0.01..−0.03 at trial scale, growing with run length (the with-replacement
  waste compounds: by 5,120 draws ~35–40% of v2's legal windows are expected undrawn under
  i.i.d.). At probe scale (~800 draws) the gap should be small — a probe win is not required,
  a probe *loss* >0.02 kills it.
- **contamination control:** the deck is enumerated from legal starts only (held predicate
  applied at enumeration, before shuffling); reshuffles re-enumerate from the same legal set,
  and the runner asserts deck ∩ held = ∅ by construction check on the start list.
- **status:** queued
```mill
id: G-021
mode: process
run: --arm layered_half --rope --corpus v2 --sampler deck
```

### G-022 · Stationary mixed context lengths (ctx drawn per batch: 64 / 128 / 256)
- **source:** data-construction derivation — A-045/46 test a monotone ctx *curriculum*
  (thirds of the run at one length each). The untested alternative is a **stationary mixture**:
  every batch independently draws its ctx from {64, 128, 256} uniformly, for the whole run.
  The two designs differ exactly where it matters for votes: the curriculum confounds length
  with run phase (early flips only ever see short contexts), the mixture does not.
- **mechanism:** Per-batch ctx ∈ {64, 128, 256} (mean 149 pieces/window — step-matched *and*
  token-matched controls are both reported; primary verdict at equal steps, per the lab's
  step-currency lesson from F-038). Position distribution shifts by design: positions 0–63
  receive 3× the gradient exposure of positions 192–255. Final judging is always at ctx 256
  on the standard held windows.
- **exact change:** train.py flag `--ctx-mix 64,128,256` (batch builder slices each drawn
  window to the batch's drawn length; RoPE buffers already span 256; no model change).
- **mode:** process
- **prediction:** −0.01..−0.03 at equal steps if early-position undertraining is real (at fixed
  ctx 256 every position trains equally per window, but short-window structure — the local
  syntax the first blocks must learn — is diluted across 256 positions of loss). If it ties
  A-045's curriculum arm, phase-confounding was harmless; if it beats it, the curriculum
  family's readings need the stationary control before any adoption.
- **contamination control:** slicing never extends a window — a mixed-ctx window is a prefix
  of a legal full-length draw, so its legality is inherited from the parent draw's held
  predicate; truncated windows are never re-padded from neighbouring (possibly held) text.
- **status:** queued
```mill
id: G-022
mode: process
run: --arm layered_half --rope --ctx-mix 64,128,256
```

### G-023 · Position-phase dither by masked left-pad (same text, new RoPE phase, no wrap)
- **source:** data-construction derivation — A-051 cyclically *rotates* a window's tokens
  (tail wraps to head: token adjacency is destroyed at the seam and every token keeps a
  neighbour it never had). The gentler transform nobody has tried: shift the window's content
  right by k ∈ {0..31} **masked pad positions** — adjacency fully preserved, nothing wraps,
  the content simply sits at a different absolute phase for RoPE and the carried position
  table. Pad positions carry no loss and no targets.
- **mechanism:** Each drawn window is left-padded by a fresh uniform k per window per visit,
  so across a run the same passage votes from up to 32 different absolute phases. This directly
  attacks absolute-phase overfitting in a chassis that carries *both* rotary and a (dormant
  under `--rope`) position table — phase-locked memorisation is a plausible hidden tax on a
  0.91M-piece corpus seen repeatedly.
- **exact change:** train.py flag `--pad-dither 31` (sampler transform in the batch builder;
  pad token = BOS id with its target positions masked out of the CE sum — construction-side
  masking as in G-013, objective unchanged).
- **mode:** process
- **prediction:** −0.01..−0.03, largest on v2/v1 where repetition makes phase-locking
  learnable; ~0 on v3's 21M pieces (too little repetition to phase-lock — v3 is the negative
  control). Read against A-051: if pad-dither ≥ cyclic-shift, adjacency preservation was the
  active ingredient; if cyclic wins, the wrap seam was harmless and phase diversity alone
  explains both.
- **contamination control:** the transform is applied *after* the held predicate, to the
  drawn window only — padding adds no corpus tokens, shifts no offsets, and cannot pull held
  text into a training window; the underlying draw's legality is asserted before padding.
- **status:** queued
```mill
id: G-023
mode: process
run: --arm layered_half --rope --pad-dither 31
```

### G-024 · Corpus-v3 book-block order (whole books as the unit of order)
- **source:** corpus-v3 construction (make_corpus_v3.py; ~21.4M pieces, Gutenberg books +
  WikiText-103) — v3's documents are *books*: single sources run to hundreds of thousands of
  pieces, so "order" on v3 has a grain v2 never had. The first v3 series will pick an ordering
  by default (whatever the sampler happens to do); this entry makes that choice a measured
  one before it hardens into the v3 baseline every later arm is judged against.
- **mechanism:** Three orderings at fixed v3 mixture: (a) i.i.d. offsets (default control),
  (b) **book-block walk** — books taken one at a time in ascending length order (short books
  first: the only curriculum here is document length, not loss or difficulty), read
  contiguously within each book (G-014's walk at book grain), WikiText interleaved at its
  natural share between books, (c) book-block walk in *descending* length order (control for
  (b)'s direction). Long coherent documents give counters multi-thousand-step agreeing
  evidence runs that v2's 36-piece lines never could.
- **exact change:** runner change — new companion runner flag `--v3-order iid|book-asc|book-desc`
  (book boundaries from the v3 build's per-category source table; v3-native held windows per
  the E-018 pattern on the v3 stream). Requires the `--corpus v3` path (same dependency as
  E-018's v2 path).
- **mode:** process
- **prediction:** book-asc beats i.i.d. by −0.02..−0.05 at ladder format on v3 (coherence is
  worth more, not less, as documents lengthen — the G-014 mechanism at its natural scale);
  book-desc within ±0.02 of book-asc if only contiguity matters, worse by ≥0.03 if the
  short-first direction itself earns. Full-trial/ladder format only — a 75 s probe sees a
  fraction of one book and cannot read this.
- **contamination control:** v3 was built with a held-line leak guard (every line appearing
  inside a v1/v2 held window was dropped at build time, and global line dedup prevents any
  line repeating); on top of that, the v3 series' own held windows are excluded by the
  standard predicate in all three arms, book walks skip held blocks inside a book rather
  than splitting the book around them, and the runner asserts zero overlap between dealt
  windows and v3 held windows per arm.
- **status:** queued
```mill
id: G-024
mode: process
run: --arm layered_half --rope --corpus v3 --v3-order book-asc
```

---

## Miner's ranking note

The construction layer is the least-owned territory in the lab: the sampler has exactly one
form in every record (`offsets()`, i.i.d., blind slices), while the trainer above it has
hundreds of pooled variants. My top 3 are the three that change what a *vote is evidence of*:
**G-013** stops ~7 seam positions per window from casting contradictory votes at all;
**G-014** tests whether evidence *coherence in time* — the property an integrator is built
to exploit — has been sitting at zero by accident; **G-015** is the integrity entry, the one
whose (possibly worse) number every other v1 verdict silently depends on. G-016/G-019 are
the cheapest decisive pair in the file (same flags, two questions about v2's real mixture),
and G-017/G-021 are a designed bracket: designed overlap vs guaranteed coverage, champion
in the middle — whichever way they land, the overlap dial gets its first two measurements.

*End of wave-G lens-2 (data construction). 12 entries, G-013..G-024, all queued, all
process mode, none duplicating IDEA-POOL.md or CANDIDATES-A/B/C/D/E/F.*

## Lens 3 — Readout (was RO-###)

### G-025 ★ · Per-layer install-scale calibration (post-hoc `log_scale` line search)
- **source:** train.py code audit — `Layered.install()` + `Layered.step`'s hand-set `log_scale` gradient (`(g·s).sum()·exp(log_scale)`, AdamW lr 1e-3 shared with embeddings/norms)
- **mechanism:** The only magnitude information a vote-trained model carries lives in 8 scalars, and they were fitted by a one-term proxy gradient, never by the loss itself. After training, freeze `t1/t2` and every FP part; for each BitLinear layer in turn, try multipliers {0.85, 0.925, 1.0, 1.08, 1.18} on `exp(log_scale)`, keep the value minimising CE on calibration windows, two coordinate rounds. Because `BitLinear.forward` renormalises by the installed abs-mean, each multiplier is exactly a per-layer output gain — this searches the true objective over the model's entire continuous readout space, which training never did.
- **train.py:** no training change; new eval runner `mill/readout.py --calibrate-scales` (loads a `--dump-state` final state, or attaches at end of a champion run): perturbs `trainer.log_scale[i]`, calls `trainer.install()`, scores with the `held_loss()` body on calibration windows, writes the fitted multipliers, then one final `held_loss()` read.
- **mode:** process — eval-side runner; stays isolated until it has a full-trial record
- **prediction:** −0.015..−0.05 vs 2.8580 on the same weights. The proxy gradient for `log_scale` ignores every downstream layer's response to a scale change; a direct line search cannot do worse than the trained point on the calibration objective (1.0 is in every grid), so the only question is transfer to held — 8 scalars cannot overfit 128 windows.
- **cost:** eval-only — ~64 calibration forward passes (8 layers × 5 values × ~1.6 rounds) + 1 held pass; no retraining, no new training state.
- **status:** queued
```mill
id: G-025
mode: process
run: --arm layered_half --rope --dump-state --readout calibrate-scales
```

### G-026 ★ · Counter-resolved readout (express the pending flips the final state is sitting on)
- **source:** train.py code audit — `Layered.step`: a component flips only when its counter reaches |c| = V = 32 and then resets to 0; at end of run every counter holds 0–31 votes of unexpressed, post-last-flip evidence
- **mechanism:** The shipped state systematically lags its own evidence: a weight at counter +31 has effectively been voted up 31 times since its last flip and the readout throws that away. At readout, apply each component's pending flip once where |c| ≥ τ (τ ∈ {16, 24} — two reads), respecting the install-time rules training used: boundary no-ops skipped (clamp would not move the component), t1 priority where both components qualify. Then `install()` and read held once per τ. This is the only readout that uses information the weights provably do not contain.
- **train.py:** no training change; eval-side flag `--counter-resolve 24` in the readout runner (needs the `--dump-state` counters; on an in-process end-of-run attach it reads `trainer.c1/c2` directly).
- **mode:** process — eval-side flag; stays isolated until it has a full-trial record
- **prediction:** −0.01..−0.04. The last fraction of any run is the least converged (freshest flips, counters mid-climb); resolving the near-threshold band expresses roughly the next flip-wave early. If the delta is ~0 at both τ, that is itself a finding: the final state is evidence-complete and the counter stream carries nothing the weights don't.
- **cost:** eval-only — one install + one held pass per τ tried (≤3 passes total); the cheapest entry in this file per unit of new information.
- **status:** queued
```mill
id: G-026
mode: process
run: --arm layered_half --rope --dump-state --readout counter-resolve 24
```

### G-027 ★ · Checkpoint logit-ensemble (average predictions, not weights)
- **source:** ensemble theory + the pool's own gap — MILL-218/A-093/A-094 all combine checkpoints in WEIGHT space; F-033 ensembles the two COMPONENTS of one state; no entry averages the PREDICTIONS of one run's successive checkpoints
- **mechanism:** Save the last 5 checkpoints (same saves the modal entries already assume); at readout, run all 5 installed states, average their softmax probabilities token-by-token, and score CE of the averaged distribution. Vote training makes successive states differ by a sparse set of flips — near-independent errors on exactly the contested weights — so prediction averaging cancels flip noise that no single-state readout (final, modal, or rounded-average) can: weight-space averaging must commit each weight to one level, probability averaging lets the ensemble stay uncertain where the run itself was uncertain.
- **train.py:** no training change; new eval path `--ckpt-ensemble 5` in the readout runner (loads 5 dumped states, loops `held_loss()`'s body collecting log-probs, averages in prob space, one CE).
- **mode:** process — eval-side runner; stays isolated until it has a full-trial record
- **prediction:** −0.02..−0.06 — the largest single expected delta in this file; checkpoint ensembles at correlated-but-not-identical states reliably buy a few hundredths of CE, and this run's checkpoints differ by discrete flips (high diversity per unit of quality loss). Serving cost is 5× forward, reported honestly alongside.
- **cost:** eval-only — 5 forward passes over the held set; no retraining (rides the same `--dump-state` saves as MILL-218).
- **status:** queued
```mill
id: G-027
mode: process
run: --arm layered_half --rope --dump-state --readout ckpt-ensemble 5
```

### G-028 · Logit temperature on the readout (one scalar, cached logits)
- **source:** calibration literature (temperature scaling) applied to `held_loss()`'s exact form — CE over `next_piece` logits, a metric that is NOT argmax-invariant
- **mechanism:** The champion trains ~155–170 steps: a heavily undertrained model whose logit scale was set by whatever the tied FP head and final norm happened to reach, not by calibration. Readout divides logits by T, T fitted on calibration windows over a log grid 0.70–1.45. Underconfidence (T < 1) is the expected direction at this step count; either way CE — the lab's judge — prices calibration error directly, so a real miscalibration is a real held gain, not a metric trick.
- **train.py:** no training change; eval-side flag `--temp T` in the readout runner, implemented by computing held logits ONCE, caching them, and sweeping T on the cached tensor (the sweep itself costs zero extra forward passes).
- **mode:** process — eval-side flag; stays isolated until it has a full-trial record
- **prediction:** −0.005..−0.02. Small, but the prior is directional (undertrained ⇒ underconfident) and the parameter count is one — it either transfers or it is flat, it cannot overfit.
- **cost:** eval-only — exactly 1 forward pass + an arithmetic sweep on cached logits; the cheapest entry in the file outright.
- **status:** queued
```mill
id: G-028
mode: process
run: --arm layered_half --rope --readout temp
```

### G-029 · Full-state checkpoint averaging (era-matched SWA: FP parts averaged too)
- **source:** gap inside A-094 — it averages only the ternary states and pairs them with the FINAL step's embeddings, norms and `log_scale`s, i.e. weights from one era read through continuous parts from another
- **mechanism:** Average EVERYTHING across the last 5 checkpoints: FP parts (tok/pos embeddings, norms, `log_scale`s) in FP, ternary components average-then-round as in A-094, then `install()` once. The vote trainers move their FP parts every step via AdamW, so the final FP frame is fitted to the final ternary state specifically; a ternary average read through it is a mismatched pairing. Era-matching is the faithful translation of Fable's running-mean readout, which averages the whole model, not one parameter class.
- **train.py:** no training change; eval-side flag `--swa-full 5` in the readout runner (needs full FP params in `--dump-state`, not just ternary states — the one dump-format extension in this file).
- **mode:** process — eval-side flag; stays isolated until it has a full-trial record
- **prediction:** −0.01..−0.03 vs final state, and the A-094 comparison is built in: if G-029 ≈ A-094's number on the same run, era mismatch costs nothing and A-094 stands as the cheaper readout; if G-029 < A-094, every ternary-only readout in the pool has been under-read.
- **cost:** eval-only — 1 held pass after averaging; rides the same 5 saves as MILL-218/A-094.
- **status:** queued
```mill
id: G-029
mode: process
run: --arm layered_half --rope --dump-state --readout swa-full 5
```

### G-030 · Counter-soft install (fractional pending evidence, through the forward rounding boundary)
- **source:** continuous relaxation of G-026 — where G-026 hard-flips the near-threshold band, this entry asks what the FULL counter field is worth as a graded readout signal
- **mechanism:** Install soft states instead of the raw integers: per component, `t_soft = t + α·(c/V)`, α ∈ {0.3, 0.5, 0.8} fitted on calibration windows (one scalar), sum the components, `install()`. This is not cosmetic: `BitLinear.forward` serves `round(w / mean|w|)·mean|w|`, so a fractional offset changes the SERVED ternary value exactly for borderline weights — a 0-state with a strong counter (α·c/V pushing it past 0.5·mean|s| ≈ 0.39 at the champion's level histogram) serves as ±1, and a ±1 whose counter strongly opposes it drops to 0. The counters thereby act as a per-weight tie-breaker/evidence dial across the whole population, not just the |c| ≥ τ band.
- **train.py:** no training change; eval-side flag `--counter-soft 0.5` in the readout runner (installs from dumped `t1/t2/c1/c2` with the offset, bypassing `trainer.install()`'s integer assumption via a readout-local install that reproduces its normalisation exactly).
- **mode:** process — eval-side flag; stays isolated until it has a full-trial record
- **prediction:** −0.005..−0.03, expected ≥ G-026's delta if graded evidence beats a hard threshold, ≤ it if only the near-threshold band carries signal — the pair prices the counter field's shape, not just its existence.
- **cost:** eval-only — 1 held pass per α (3 passes) after calibration fitting; no retraining.
- **status:** queued
```mill
id: G-030
mode: process
run: --arm layered_half --rope --dump-state --readout counter-soft 0.5
```

### G-031 · Validation-selected checkpoint (the deployable form of best-checkpoint)
- **source:** A-095's own framing — it prices the selection ceiling by selecting ON held, which no shippable readout may do; the deployable question (does selection on legal data capture any of that ceiling?) is unasked
- **mechanism:** Score each of the last 9 checkpoints on calibration windows (non-held), ship the argmin, read held once. Checkpoint-to-checkpoint spread within a run has never been measured in this lab (only seed-to-seed, ±0.0161); if within-run spread is comparable, honest selection captures a real share of it, and the gap G-031 vs A-095's number prices exactly how much of the ceiling was judge-leakage.
- **train.py:** no training change; eval-side flag `--select-ckpt 9` in the readout runner (9 calibration passes + 1 held pass).
- **mode:** process — eval-side flag; stays isolated until it has a full-trial record
- **prediction:** −0.01..−0.03 vs the final state, contingent on within-run checkpoint spread ≥ ~0.02 — which this entry measures either way (report all 9 calibration scores). A flat result retires the whole selection family cheaply, including future variants.
- **cost:** eval-only — 10 forward passes; no retraining.
- **status:** queued
```mill
id: G-031
mode: process
run: --arm layered_half --rope --dump-state --readout select-ckpt 9
```

### G-032 · Disagreement-gated zeroing (contested weights ship as 0, not as a coin-flip sign)
- **source:** robust-readout reasoning against A-094's weak point — average-then-round resolves a 3–2 checkpoint split by majority, i.e. it ships a ± level on evidence barely better than chance
- **mechanism:** From the last 5 checkpoints compute each weight's state mean; weights with |mean| below a gate (splits 3–2 or worse, gate fitted in {0.2, 0.6} on calibration windows) install as 0 regardless of final state; stable weights keep their final state. Zero is the minimax level for a weight the run itself could not decide: a wrong ±1 contributes a full-magnitude wrong product to every downstream sum, a 0 contributes nothing and biases nothing. Distinct from modal/average readouts, which use checkpoint history to PICK A SIGN; this uses it to decide which weights have earned a sign at all.
- **train.py:** no training change; eval-side flag `--gate-zero 0.6` in the readout runner (installs the gated state via the readout-local install, then one `held_loss()` read).
- **mode:** process — eval-side flag; stays isolated until it has a full-trial record
- **prediction:** −0.005..−0.025. At the champion's histogram ~28% of weights already sit at 0 and the ±2 population is only ~7% — the contested band is where the remaining readout error concentrates. Report the gated share; if >25% of weights gate to 0, the run was less converged than its flip rate suggested.
- **cost:** eval-only — 1–2 held passes; rides the same 5 saves as MILL-218.
- **status:** queued
```mill
id: G-032
mode: process
run: --arm layered_half --rope --dump-state --readout gate-zero 0.6
```

### G-033 · Per-head attention temperature, fitted post-hoc
- **source:** A-078's mechanism moved to the readout — A-078 LEARNS per-head temperatures during training (a trainer change, pooled); nobody has fitted them after training on a finished model, where the fit is 8 scalars against the true loss
- **mechanism:** In the eval runner only, scale each head's q by √λ_h (equivalently divide its attention logits by a per-head temperature) before SDPA, λ_h fitted per head per block (4 heads × 2 blocks = 8 scalars) by coordinate grid {0.8, 0.9, 1.0, 1.1, 1.25} on calibration windows. Ternary QK products are coarse and each head's natural logit scale differs; training had no dial for this at all on the vote chassis (SDPA's hd^-0.5 is fixed in `Block.forward`), so any systematic per-head sharpness error is still sitting in the champion untouched.
- **train.py:** no training change; eval-side flag `--head-temp` in the readout runner (monkeypatches `Block.forward`'s SDPA call in eval only — training code untouched, and the fitted λ ship as part of the readout spec).
- **mode:** process — eval-side flag; stays isolated until it has a full-trial record
- **prediction:** −0.005..−0.02. Bounded by how much of the loss is attention-sharpness error at ctx 256; the coordinate fit is 8 scalars on 128 windows, so a win transfers or it is honestly flat.
- **cost:** eval-only — ~40 calibration passes + 1 held pass; no retraining.
- **status:** queued
```mill
id: G-033
mode: process
run: --arm layered_half --rope --readout head-temp
```

### G-034 · Unigram prior-correction bias on the head (closed-form, no fitting loop)
- **source:** prior-correction / marginal-calibration practice, applied to `Tiny.next_piece` — the head is the tied FP embedding, trained jointly for ~160 steps, so the model's implied token marginal has had little time to match the corpus marginal
- **mechanism:** Compute the model's average predicted distribution over calibration windows and the windows' empirical token distribution; add a per-vocab logit bias `b_v = log(p_emp(v) / p_model(v))` (smoothed, clipped to ±0.5) at readout. 4,096 numbers but ZERO fitted parameters in the optimisation sense — the bias is a closed-form statistic of the calibration set, the same form as the corpus's own unigram table. It corrects exactly one failure mode: systematic over/under-prediction of frequent tokens, which CE punishes on every single position.
- **train.py:** no training change; eval-side flag `--prior-bias` in the readout runner (one calibration pass to accumulate the marginal, bias added to `next_piece` logits in eval only).
- **mode:** process — eval-side flag; stays isolated until it has a full-trial record
- **prediction:** −0.005..−0.02, with a hard honesty check built in: report the KL between model and empirical marginals first — if it is already < 0.01 nats, the predicted gain is ~0 and the entry should be read as a measurement, not a candidate.
- **cost:** eval-only — 1 calibration pass + 1 held pass; no retraining.
- **status:** queued
```mill
id: G-034
mode: process
run: --arm layered_half --rope --readout prior-bias
```

### G-035 · Measured greedy flip polish, counter-ranked (readout-time, verified per flip)
- **source:** the lab's own measured-flip precedent (`_flip_read` / MILL-228's Fisher-ranked flips) relocated to where it is cheapest — MILL-228 does measured flips DURING training at ~6 passes per round; the same verification logic applied once, post-hoc, to a finished model is a readout
- **mechanism:** Rank candidate single-component flips by |counter| descending (the counter field is the candidate generator — no gradient pass needed). Walk the top 200 candidates: tentatively apply the flip, `install()`, score on a fixed calibration batch; keep the flip only if calibration CE improves, else revert. Sequential, greedy, every kept flip verified on legal data. This is G-026 with a measurement replacing its threshold rule: it spends ~200 small eval passes to buy certainty per flip instead of trusting the counter's say-so in bulk.
- **train.py:** no training change; eval-side runner mode `--greedy-polish 200` (operates on the dumped final state; the polished state is a readout artifact, never written back to any training state).
- **mode:** process — eval-side runner; stays isolated until it has a full-trial record
- **prediction:** −0.01..−0.04 on held if counter rank correlates with true flip value (G-026/G-030 read first — this entry is ranked below them deliberately, and is only worth its passes if at least one of them shows the counter field carries signal). Overfit guard: candidates capped at 200, calibration batch disjoint from the held judge, held read once at the end.
- **cost:** eval-only but the most expensive eval-only entry here — ~200–400 small-batch forward passes (still minutes, vs 8 min for one training run); no retraining.
- **status:** queued
```mill
id: G-035
mode: process
run: --arm layered_half --rope --dump-state --readout greedy-polish 200
```

### G-036 · Cross-seed logit ensemble (the champion's own three seeds as the ensemble)
- **source:** runs.jsonl — the champion exists as three completed independent runs (seeds 0/1/2: held 2.8765 / 2.8477 / 2.8497, mean 2.8580); ensembling a run's own checkpoints is G-027, ensembling across runs is the same readout principle at maximum state diversity, and no pool entry proposes it
- **mechanism:** Probability-mean ensemble (as G-027) over the three seeds' final installed states. Independent inits + independent batch streams decorrelate errors far more than checkpoints of one trajectory do; the ensemble's held is compared against the MEAN member (2.8580) and the BEST member (2.8477) — beating the best member is the bar that makes it a readout rather than a selection.
- **train.py:** no training change; eval-side runner mode `--seed-ensemble` over three `--dump-state` finals. NOTE the honest cost below: today's runs saved no state, so the three finals must be re-produced once (same seeds/config — the runs are deterministic given seed, so the re-produced states ARE the champion's states, at re-run cost).
- **mode:** process — eval-side runner; stays isolated until it has a full-trial record
- **prediction:** −0.03..−0.08 vs the 2.8580 mean — the largest ceiling in this file, priced accordingly: serving cost is 3 full models (3× bytes, 3× forward), so even a win is a per-byte trade the trial must state, not a free champion replacement.
- **cost:** retrain (state recovery) — 3 × 8 min to re-produce the unsaved finals, then eval-only forever after; the ONLY entry in this file whose cost is not purely eval-side, ranked last for exactly that reason.
- **status:** queued
```mill
id: G-036
mode: process
run: --arm layered_half --rope --dump-state --readout seed-ensemble
```

---

## Ranking rationale (one line each)

1. **G-025** — direct line search over the model's only continuous readout degrees of freedom; cannot lose on its own fit objective, 8 scalars.
2. **G-026** — uses information (final counters) that provably exists and is provably discarded; ≤3 eval passes.
3. **G-027** — biggest expected single delta among same-run readouts; prediction-space averaging is untested in this lab in any form.
4. **G-028** — one scalar, one forward pass; directional prior from the run's short length.
5. **G-029** — fixes a real era-mismatch inside the pooled A-094 rather than duplicating it.
6. **G-030** — G-026's graded sibling; the pair together price the counter field's shape.
7. **G-031** — converts A-095's leaked diagnostic into a deployable readout and measures within-run spread for the first time.
8. **G-032** — minimax readout for contested weights; orthogonal to every sign-picking readout in the pool.
9. **G-033** — A-078's dial fitted post-hoc against the true loss instead of learned through STE-era gradients.
10. **G-034** — closed-form marginal correction; includes its own pre-measurement (KL) that can honestly zero it.
11. **G-035** — strongest verification per flip, but deliberately gated on G-026/G-030 showing counter signal first.
12. **G-036** — highest ceiling, only non-eval-only cost, 3× serving bytes; a trade, not a free win.

## Lens 4 — Mill methodology (was MM-###)

### G-037 ★ · Futility stop for trial seeds — never run a seed that cannot change the verdict
- **source:** `screen.py: run_trial_seeds()` unconditionally runs the fixed seed trio (0, 1, 2) for every queued trial, and `judge_trials()` only evaluates adoption afterwards. The adoption rule itself (PROMOTE.md: mean beats ref by >2sd AND >0.01, **and ≥2 of 3 seeds individually beat `ref_mean`**) makes many third seeds mathematically dead before they run.
- **mechanism:** After seed 1 (the second seed), if both seeds are ≥ `ref_mean`, the per-seed guard is already unpassable — the third seed can produce at most 1 win, and adoption requires 2. That trial is decided; running seed 2 spends 8 solo minutes proving nothing. A second, softer futility bound: if even a third seed equal to the best held value ever ledgered at trial format could not pull the mean under `ref_mean − max(2·ref_sd, 0.01)`, the trial is also decided. This is sequential testing applied where the outcome space is already closed — distinct from any probe-format change.
- **change:** `screen.py` — in `run_trial_seeds()`, after each seed event is appended to `trials.jsonl`, evaluate the two futility conditions against the current champion reference; on a hard (per-seed-guard) stop, write a terminal seed event `{"event": "futility_stop", "after_seed": 1, "reason": "per-seed guard unpassable"}` and let `judge_trials()` ledger it as `reject` with `verdict_reason: "futility"`. The soft (mean-bound) stop is ledgered separately as `futility_soft` so the two are never conflated in later audits.
- **payoff:** 8 min saved per futility-stopped trial = 33% of that trial's 24 min. Break-even is trivially met: the hard stop has a 0% false-rejection rate by construction (it fires only when adoption is arithmetically impossible). If half of a generation's trials are rejects and half of those show 0 wins after 2 seeds, that is ~2 min saved per trial run, every generation, forever — and the freed solo time goes straight back to probes (~6 extra probes per saved trial).
- **risk:** a bug in the futility test silently kills a real adoption. Guard: the hard stop uses only the per-seed guard (integer win counting, no statistics); the soft stop is opt-in per generation and its bound uses a ledger-observed floor, never an assumed one. Both stops are ledgered with their inputs so any stop can be re-checked by hand from `trials.jsonl` alone.

### G-038 ★ · Multi-fidelity probe ladder — stop spending 75 s uniformly on ideas that die in 30 s
- **source:** `screen.py: lane_work()` gives every runnable entry the identical budget (`probe_minutes = 1.25` for all, sweep and process alike), in pool order, regardless of the idea's family, prior-generation delta, or how fast its loss curve separates from job zero. PROMOTE.md justifies the loose 0.05 bar by probe noise, but nothing in the funnel uses a cheaper first look.
- **mechanism:** Successive halving over fidelity, not over ideas: Stage A probes everything at 30 s; Stage B tops survivors (top ~40% by Δ, plus every `near`-or-better idea) up to the standard 75 s total; only Stage B verdicts are ledgered as probe verdicts, Stage A is ledgered as a cheaper `kind: "prescreen"` line. The standard verdict machinery is untouched — what changes is that the bottom of the pool, which the 0.05 bar exists to kill cheaply, is killed at 30 s instead of 75 s.
- **change:** `sweep_probe.py` — allow a job line to carry `"minutes": 0.5` and a `"stage": "A"` marker (the runner already accepts per-job minutes; no loop change). `screen.py` — add the two-stage scheduling in `lane_work()`: Stage A batch sweep first, rank by Δ vs that pass's job zero (also run at 30 s for the Stage A comparison, 75 s for Stage B), then Stage B for survivors. PROMOTE.md gains one paragraph defining `prescreen` as a non-verdict.
- **payoff:** Per full sweep: Stage A 380 × 30 s = 190 min + Stage B 152 × 45 s (top-up only) = 114 min → ~304 min vs ~475 min uniform, a **~36% saving, ≈ 2.9 extra solo-hours per generation sweep**, or equivalently ~1.55× the ideas screened per wall hour at the same final fidelity. Gate the saving on calibration (below) — if the 30 s ranking does not hold up, the ladder collapses back to uniform 75 s at no loss.
- **risk:** 30 s rankings may not predict 75 s rankings (horizon-dependent schedules are exactly the B-017 confound — but B-017 proposes changing the *trainer*; this entry only changes *budget allocation* and must prove itself empirically). Guard: before enabling, run one calibration pass — the first 40 pool entries at both 30 s and 75 s — and enable the ladder only if the rank correlation of Δ is ≥ 0.8 and no 75 s `promote` was ranked in the Stage A bottom half; re-run the calibration whenever the champion generation changes. Calibration result is written to `mill/PROBE-NOISE.md` next to the §5a noise number.

### G-039 ★ · Two-stage promotion gate — a 75 s repeat on a second seed before any 24 min trial
- **source:** `screen.py: verdict_for()` promotes on a single seed-0 probe at Δ ≥ `PROMOTE_DELTA` (0.05), and `queue_trial()` immediately commits 24 solo minutes. PROMOTE.md accepts wasted trials as the cost of a loose screen, but with ~380 probes per generation the *count* of noise promotions is a queue-size effect nobody prices: even at a well-set 2σ bar, a few percent of 380 null ideas is 8–15 false trials ≈ 3–6 solo hours per generation.
- **mechanism:** Split the promote band. Δ ≥ 0.10 promotes directly, as today. 0.05 ≤ Δ < 0.10 is `promote_pending`: before queueing the trial, the idea gets one repeat 75 s probe on **seed 1** against a seed-1 job zero (paired, same construction as the existing seed discipline). The trial queues only if the seed-1 Δ is also > 0. This is a live pre-trial gate, not E-022's post-generation audit of the dead — E-022 counts the killed; this stops the mill paying 24 min for the lucky.
- **change:** `screen.py` — add `PROMOTE_DIRECT = 0.10` beside `PROMOTE_DELTA`; `verdict_for()` returns `promote_pending` in the band; a small coordinator step (before lanes, alongside trial work) runs pending repeats via the sweep path and calls `queue_trial()` only on a pass. Ledger lines carry `verdict: "promote_pending"` then the repeat's own probe line with `"seed": 1`, so the gate is fully reconstructible. PROMOTE.md's probe-bar section documents the band.
- **payoff:** Each blocked false trial saves 24 min at a cost of 2.5 min (repeat probe + seed-1 job zero, amortised across the band). Break-even: the gate pays if ≥ ~10% of band promotions are noise — near-certain if the bar is ~2σ, where the one-sided false rate in the band is far higher. At 10 band promotions per generation with half failing the repeat: **~1.8 solo hours saved per generation**.
- **risk:** a real small effect that is seed-sensitive gets gated out and ledgered dead for the generation. Guard: a failed repeat does not ledger `flat`/`below` — it ledgers `promote_unconfirmed`, a distinct verdict that (a) keeps the idea eligible for the near-band extension in G-044 and (b) is exactly the population E-022-style audits sample from, so the gate's own false-negative rate becomes measurable instead of assumed.

### G-040 · Drift sentinels — job-zero replicates interleaved through the pass, verdicts judged locally in time
- **source:** FABLE-CAND-01 (`mill/FABLE-CANDIDATES.md`): on Fable's side, identical code took 22 s in one sitting and 594 s in another — a **27× load swing** — and its conclusion is that wall-clock comparisons are only valid between concurrent runs. The mill's implemented fix is weaker than that lesson: `measure_baseline()` runs job zero **once, solo, at pass start**, and `lane_work()` then judges probes against it for up to 45 min, through whatever load drift the pass encounters. Fresh-per-pass fixed staleness across days; nothing tracks drift *within* the pass.
- **mechanism:** Every sweep batch (`SWEEP_BATCH = 8`) carries one extra job: a job-zero replicate (seed 0, 75 s). The batch's deltas are computed against the *interpolated* sentinel series (pass-start baseline + in-pass replicates), and a batch whose sentinel held or step count has moved beyond the PREFLIGHT probe-noise band is ledgered `contended` and re-queued rather than verdicted. Probes and their reference now share the pass's load history — the paired-comparison principle FABLE-CAND-01 states, applied inside the pass instead of only across experiments.
- **change:** `screen.py` — `run_sweep_batch()` job lists built in `lane_work()` gain a sentinel job with id `MILL-000S<batch>`; `ledger_probe()` takes the local baseline value and stamps `baseline_kind: "pass_start" | "sentinel_interp"` plus the sentinel's `steps` on each line. PROMOTE.md's probe section notes that deltas are local-in-time from this change on.
- **payoff:** Cost is 75 s per 8 probes ≈ **12.5% probe overhead**. Return: one drift-faked promotion costs a 24 min trial — the sentinels pay for a whole 45 min pass (~4 sentinels, 5 min) if they prevent **one false trial per ~5 passes**, and they additionally rescue true ideas from being ledgered `below` in a slow window (the corrosive direction RIGOR-AUDIT §2c named). Every `contended` batch is also the first direct measurement of within-pass drift on this VM.
- **risk:** sentinel interpolation could mask a real, sustained machine slowdown by normalising it away. Guard: the pass-start solo baseline remains the ledgered `baseline` of record; sentinels only *flag and defer* batches outside the noise band and adjust nothing silently — a batch is either verdicted against the pass baseline (in-band) or re-queued (out-of-band), never verdicted against a quietly shifted reference.

### G-041 · Generation re-screen triage — don't re-buy the whole pool at full price every generation
- **source:** PROMOTE.md's funnel: on adoption "the whole pool re-opens under the new generation (ledger keys are (idea, generation))", and `ledger_state(gen)` accordingly treats every idea as undone in the new generation. A champion that improved by, say, 0.03 therefore triggers ~7.9 h of re-probing, most of it re-measuring ideas that lost to the *weaker* champion by 0.15 or more.
- **mechanism:** Carry prior-generation deltas forward as a triage prior (not a verdict). In generation g+1: ideas whose generation-g Δ was below `−(champion_gain + 0.10)` are `deferred_by_triage` — not probed this generation — unless drawn in a 10% random audit sample of the deferred set, which *is* probed at full fidelity. Ideas within the margin get full probes as today. The audit sample is what makes the skip honest: if audited ideas start promoting, the margin is wrong and the data says so within one generation.
- **change:** `screen.py` — `ledger_state()` also folds the previous generation's probe deltas; `lane_work()` partitions the runnable queue into full-probe and triage-deferred, ledgering one `kind: "triage"` line (ids + margin + champion gain) per pass, in the same spirit as the existing `deferrals` line. PROMOTE.md's adoption section states the triage rule and the audit rate.
- **payoff:** If ~50% of the pool lost by more than the margin (plausible — most screens are mostly dead ideas), saving ≈ 190 × 75 s ≈ **4.0 h per generation**, minus ~24 min for the 10% audit sample: net **~3.6 h per generation** returned to new ideas and trials.
- **risk:** non-additivity — an idea that lost to champion g can genuinely beat champion g+1 through an interaction with the new champion's mechanism, and triage would skip it. Guard: the margin is deliberately wide (champion gain + 0.10, i.e. an idea must have lost by more than the entire improvement plus a noise band), the 10% audit sample probes skipped ideas anyway, and any idea a human names is always full-probed. The audit sample's promote rate is the standing check on the rule.

### G-042 · Surrogate-ranked queue — expected value first, pool order last
- **source:** `screen.py: lane_work()` works the queue strictly in `parse_pool()` order (sweep entries first, then process entries), and a pass is only 45 min — roughly 30–35 probes — against a ~380-entry pool that preempts whenever the lab gets busy. Under truncation, pool order *is* the allocation policy, and it allocates by where an idea happened to be pasted into IDEA-POOL.md.
- **mechanism:** A cheap surrogate, refit after every pass from the ledger itself: features from the run string (arm, flags, dim, layers, batch) plus family history (mean Δ of ledgered probes sharing the arm/flag prefix) predict Δ for unprobed entries. The queue is sorted by predicted P(Δ ≥ 0.05) × predicted Δ, with a fixed **20% exploration slice** interleaved in pool order so the surrogate can never starve a family it is wrong about. Cold start is family priors from the lab's RESULTS records; the model is a regularised linear model or shallow gradient boosting — at ledger scale (hundreds of rows) anything larger is theatre. Distinct from B-031: that fits a *physics* scaling law to price arms; this fits the *mill's own outcomes* to order its queue.
- **change:** new script `mill/rank_queue.py` — reads `ledger.jsonl` + IDEA-POOL.md, writes `mill/queue-order.json` (ranked ids + predicted values + model card: fit date, n rows, backtest rank correlation on a held-out slice of the ledger). `screen.py` — `lane_work()` consumes `queue-order.json` when present and fresh for the current generation, else falls back to pool order exactly as today.
- **payoff:** No saving if every pass drained the pool — passes don't. If promoters are ~5% of the pool, pool order expects the first promoter at ~probe 20; a surrogate with even modest 3× enrichment in its top decile expects it at ~probe 7, i.e. **the first trial of a generation starts ~16 probes (~20 min) earlier**, and every preempted pass spends its truncated budget on the highest-expected-value ideas instead of the alphabetically lucky. Backtest gate (below) decides whether the enrichment is real before a single probe is reordered.
- **risk:** feedback loop — the surrogate orders the queue, the queue generates the ledger, the ledger refits the surrogate; a wrong early belief becomes self-confirming. Guard: the 20% exploration slice is non-negotiable and ledgered as such; `rank_queue.py` refuses to emit an order unless its backtest (train on earlier generations/passes, test on later ones) beats pool-order enrichment on the same data; champion-generation changes reset family priors to weak strength.

### G-043 · Step-count validity gate — a verdict whose probe bought a different number of steps is not a verdict
- **source:** `screen.py: verdict_for(held, baseline_held)` looks at held loss only. Both the probe line and the baseline line already record `steps`, and the lab's own record (RIGOR-AUDIT §2c, the JEPA window: identical configs at 129–139 vs 154–170 steps) shows wall-clock budgets buying materially different step counts under load. A probe that ran 20% fewer steps than its baseline and ledgered `below` may have measured the machine, not the idea. This is **not** E-023 (which changes the probe format to fixed steps); this entry changes nothing about how probes run — it refuses to verdict the runs whose own recorded step counts say they weren't comparable.
- **mechanism:** At ledger time, compare probe `steps` to the pass baseline's `steps`. Divergence beyond a band set from the PREFLIGHT noise data (starting suggestion: ±15%) marks the line `verdict: "contended"` instead of flat/below/near/promote, and `contended` is treated like `error` in `ledger_state()` — not done, re-queues next pass, and does **not** count toward the 3-strike bench (contention is not the idea's fault).
- **change:** `screen.py` — the comparison inside `ledger_probe()` (both `steps` values are already in scope there); one new verdict string; `ledger_state()` folds `contended` with the error/re-queue path but a separate counter. PROMOTE.md's probe-bar section gains the validity band.
- **payoff:** Costs a re-probe (75 s) for the contended fraction — if 10% of probes are contended, ~48 min per full sweep. Saves the invisible loss: every false `below` is an idea dead for the generation for machine reasons, and every false `promote` costs 24 min. Break-even against false promotions alone: preventing **2 per sweep** pays for the re-probes.
- **risk:** on a persistently loaded VM the band could re-queue the same ideas repeatedly and stall the sweep. Guard: an idea contended 3 times in a generation is probed once more and verdicted on that run whatever its steps, with `steps_flag: true` on the line — the mill degrades to today's behaviour per-idea rather than stalling globally.

### G-044 · Near-band auto-extension — resolve 0.02–0.05 at 3 min instead of parking it for a human
- **source:** PROMOTE.md, verbatim behaviour: a `near` verdict (0.02 ≤ Δ < 0.05) is "recorded, no trial. A human may re-probe a `near` entry at a longer probe budget; **the mill does not on its own**." In an unattended mill running to 2026-11-15, "a human may" means "nobody does" — the band where real small effects and probe noise are indistinguishable is exactly where the mill currently stops thinking.
- **mechanism:** Upper-near ideas (Δ in [0.035, 0.05)) automatically get one extended probe at 3 min (4× budget; step count ~4×, so noise on the delta shrinks roughly 2× if noise is step-dominated). Extended Δ ≥ 0.035 queues the trial; below that, the idea is parked as `near_resolved` — a stronger death than `near`, earned at 4× the evidence. Lower-near ideas (0.02–0.035) stay parked as today; the extension budget is spent only where the prior is highest.
- **change:** `screen.py` — a coordinator step after lanes (or first step of the next pass) collects the pass's upper-near lines and runs their extensions through `run_sweep_batch()` at `"minutes": 3.0`, ledgering `kind: "probe_extended"` lines that `queue_trial()` reads. A per-pass cap (suggestion: 4 extensions = 12 min) bounds the cost; overflow carries to the next pass in Δ order.
- **payoff:** Each resolved near costs 3 min instead of either 24 min (a speculative trial) or ∞ (a real effect never tested). If a generation produces ~20 upper-near ideas and the extension promotes a quarter of them, that is **5 trials found that the current mill never runs**, bought for ~60 min — versus 120 min to trial all 20 blind, most of them noise.
- **risk:** extended probes at 3 min still aren't the 8 min trial format; horizon effects could make the extension systematically optimistic or pessimistic. Guard: the extension can only *queue* a trial, never adopt — the full 3 × 8 min trial remains the sole judge, so a biased extension costs at most a trial, and its promote rate is ledgered separately so the bias itself becomes a measured number after one generation.

### G-045 · Pass-budget partitioning — verdict work may not eat the whole pass, every pass
- **source:** `screen.py: main()` runs, in order: confirmation (2 × 8 min), fresh job zero, `run_trial_seeds()`, `judge_trials()` (which can itself trigger a 3 × 8 min stale-reference control re-run) — **all before the first probe** — inside a 45 min wall cap. One pending trial plus a stale control is 48 min of verdict work: the pass probes nothing, and because trial state is resumable but probe time is not reserved, a trial-heavy stretch can starve screening for consecutive passes.
- **mechanism:** Make the pass an explicit budget allocation instead of a fixed sequence: verdict-bearing work (confirmation, trial seeds, controls) is capped at ~55% of the pass wall; probe lanes are guaranteed the remaining ~45% (≈ 20 min ≈ 16 probes minimum per pass) unless there is no queued verdict work, in which case probes take the whole pass as today. Trial seeds already persist per-seed in `trials.jsonl`, so splitting a trial across passes costs nothing in correctness — the machinery supports the partition; only the scheduling decision is missing.
- **change:** `screen.py` — `main()` computes a `verdict_deadline = start + 0.55 × max_wall` and passes it to `run_confirmation()` / `run_trial_seeds()` / `judge_trials()` in place of the single shared deadline (all three already accept a deadline and already stop cleanly at it); lanes then run to the full deadline. PROMOTE.md's execution section states the split.
- **payoff:** Guarantees **≥ ~16 probes per pass even in the worst verdict-heavy pass**, versus 0 today — over a preempted, interrupted sprint, that floor is the difference between the pool draining in ~12 passes and stalling behind its own trial queue. No total-time saving is claimed; this buys *progress guarantees*, priced honestly as such.
- **risk:** a trial split across passes is judged against a champion reference measured earlier — but that is already true today (seeds persist across passes), and the stale-reference guard in `judge_trials()` already handles fingerprint drift. Guard: the partition never splits a trial *mid-judging* — `judge_trials()` for a completed trial always runs to completion once started; only seed execution is partitioned.

### G-046 · Interaction mining — let the ledger propose the two-flag combinations no human queued
- **source:** The pool is human-authored single-mechanism entries, and `screen.py` only ever runs the run strings it is given. Yet the standing champion is itself an interaction (`--arm layered_half --rope` — neither the lab's story nor its numbers are the sum of the parts), and the ledger accumulates exactly the per-flag delta data needed to spot the next such pair. Nothing in the mill reads its own ledger for structure.
- **mechanism:** An offline miner over `ledger.jsonl` + the lab's `runs.jsonl`: (a) group probe deltas by individual flag/arm component; (b) flag pairs whose components are individually `near`/`flat` (not `below` — dead components stay dead) but mechanistically orthogonal (different subsystems per the pool entry text: trainer vs sampler vs architecture vs readout); (c) emit the top pairs as *proposed* pool entries into a review file. A reserved slice of probe capacity — 1 slot per sweep batch of 8 — runs approved combos, so interaction exploration is a budgeted line item (~12% of probes), not a raid on the main queue.
- **change:** new script `mill/mine_interactions.py` — pure ledger analysis, writes `mill/INTERACTION-PROPOSALS.md` (pair, component deltas with generation + code_sha, orthogonality rationale, predicted additive Δ vs the interaction hypothesis). Combos enter IDEA-POOL.md only as normal `mill` blocks (human or a later automation step adds them); `screen.py` needs no change beyond the batch-slice convention documented in PROMOTE.md.
- **payoff:** Priced as exploration, not throughput: at 12% of a 7.9 h sweep, ~57 min per generation buys ~45 combo probes. One adopted interaction per generation pays for the slice outright — the champion's own history (rope's gain appearing on the layered chassis) is the existence proof that this lab's wins can be combinatorial. The miner also returns a ranked component-effect table, which feeds G-042's surrogate features for free.
- **risk:** data dredging — with hundreds of pairs, some combo will look good by chance, and additive-Δ predictions from single-seed probes are weak evidence. Guard: proposals are probes, never trials — a combo still needs Δ ≥ 0.05 at probe and the full trial bar to adopt, so dredging costs 75 s per false lead, capped by the batch slice; the proposals file must print each component's n and spread next to its delta, and pairs whose components were measured under different `code_sha` fingerprints are marked non-comparable and excluded.

### G-047 · Champion-defence scheduling + rotating confirmation subsets — the gate should not be one seed, one set, once
- **source:** PROMOTE.md's confirmation gate runs **once per champion, seed 0 only, 2 × 8 min**, on the single fixed confirmation set (residue 20), after which that champion's reference judges an entire generation of probes and trials — potentially weeks and hundreds of selection events. Two exposures compound: a seed-0 confirmation is a single draw (a champion can pass it by luck), and the confirmation set itself becomes a selection target across generations — every champion that survives was chosen partly for not losing *there*, which is generation-overfitting one level up, beyond the confirmation set's current design.
- **mechanism:** (a) *Defence cadence:* after every 100 ledgered probes under a champion, or before its third trial judging, whichever comes first, the champion re-defends: one 8 min run on the confirmation windows with the *next unused seed* (1, then 2…), against the predecessor's stored confirmation value for that seed if present, else a fresh predecessor run. A failed defence freezes the reference exactly as a failed initial confirmation does. (b) *Rotating subsets:* `sweep_probe.py`'s `CONFIRM_OFFSET = 20` becomes a small rotation of disjoint offsets (e.g. residues 20, 10, 30 — all disjoint from held residue 0 and from each other at block granularity), one per defence event, so no single neighbour set accumulates all the selection pressure.
- **change:** `sweep_probe.py` — parameterise `confirm_windows()` / `offsets_x()` by offset (the residue arithmetic already isolates the logic). `screen.py` — a defence counter in `champion.json` (`probes_since_defence`, `defences_run`), checked in `main()` beside the existing confirmation gate; defence runs ledger as `kind: "confirmation"` with `"phase": "defence"`, `"seed": n`, `"offset": r`. PROMOTE.md's confirmation section is extended, not replaced.
- **payoff:** Cost per defence: 8 min (champion only, when the predecessor's same-seed value is stored) to 16 min, per 100 probes (~125 min of probing) — **~6–13% overhead on verdict infrastructure that currently costs 16 min per generation and then is trusted indefinitely**. The return is risk removal, stated plainly: it converts "the champion passed once, on one seed, on one set" into a standing, multi-seed, multi-set record, and it is the only entry here that watches the judge while the judge watches everything else.
- **risk:** more gates mean more chances to freeze a good champion on a noisy defence draw. Guard: a defence failure triggers one immediate re-run on a second seed before freezing (2-of-3 logic, mirroring the trial per-seed guard); freezing remains a ledgered, reported event, never a silent stop — exactly the existing confirmation-failure semantics.

### G-048 · Deferral ROI ledger — rank the missing flags by the ideas they are holding hostage
- **source:** `screen.py: ledger_deferrals()` faithfully records *which* entries cannot run and why (flag/arm not in `train.py`), once per pass per generation — and nothing ever aggregates it. The pool's deferred population is invisible as a decision: nobody can see that one unimplemented flag might be blocking 30 probes while another blocks 2, so trainer-implementation time (the scarcest resource in the lab) is allocated without the mill's own data.
- **mechanism:** Aggregate the deferral lines by missing flag/arm: entries blocked, their families, and (via G-042's surrogate features, when available) their predicted value. Output a ranked implementation queue: flag, blocked count, blocked families. This is ledger mining aimed at the *supply* side — the mill telling the lab which single code change buys the most new screening capacity.
- **change:** new script `mill/flag_roi.py` — reads the latest `deferrals` line per generation from `ledger.jsonl` plus IDEA-POOL.md, writes `mill/FLAG-ROI.md` (ranked table, regenerated per run, with the generation and code_sha it was computed from). No change to `screen.py` — the data is already ledgered; this entry exists because recording a thing and reading it are different acts.
- **payoff:** If the top missing flag blocks even 20 entries, implementing it unlocks 20 probes (~25 min of screening) that currently return a deferral line every pass forever; ranked against a flag blocking 2, the same implementation hour buys **10× the queue**. The table also exposes dead weight: flags blocking entries whose families have uniformly failed can be struck from the pool instead of deferred eternally, shrinking every future pass's validation overhead.
- **risk:** blocked-count is a crude value proxy — a flag can block many low-value entries. Guard: FLAG-ROI.md prints count and family spread side by side and labels the ranking "count-first, judgement required"; it recommends an order for human implementation time and changes no code, queue, or verdict by itself.

---

## Landing order, if only three land

1. **G-037** — pure arithmetic, zero statistical risk, saves 8 min per doomed trial from the first trial onward.
2. **G-039** — one band, one repeat probe; converts the loosest step in the funnel into a gated one and makes its own error rate measurable.
3. **G-038** — the largest single throughput win (~36% of sweep time), but deliberately third: it should only land after its 30 s ↔ 75 s calibration pass has been run and recorded.

## Lens 5 — Model composition (was MC-###)

### G-049 ★ · Two plain bodies, one shared embedding — an ensemble at exactly the champion's bytes
- **source:** byte arithmetic above + RESULTS-HALF-CONTROL-2026-11-12 (plain_half 2.9010 ≈ layered_half 2.8990: at equal size/steps the second *component* earns nothing summed into the same weight)
- **mechanism:** Train two plain_half+rope bodies (data seeds 0 and 1, same init seed) that share ONE token+position embedding and tied head — the artifact is a single model file: shared FP embedding stack (3,343,872 B incl. final norm) + 2 bodies (each 221,184 B ternary + 19,968 B block-local FP) = **3,826,176 B served, +0.52% vs the champion's 3,806,208** and byte-identical to a plain_full solo. Serve by mean of the two bodies' logits. The bet: the layered idea's missing 0.04 was never about levels — two *decorrelated wholes* at the same bytes vote better than two *summed components*. Sharing the embedding is not an accounting trick: the bodies' only difference is their blocks, and the shared head forces both to speak the same output geometry, which is what makes their logits commensurable.
- **train.py:** new runner `mill/run_compose.py --shared-ens 2` (trains two `plain_half --rope` bodies against one shared `tok`/`pos` embedding module — embedding grads from both bodies summed, one AdamW step per body step, alternating windows) + eval path `--ens-eval` reporting each body solo and the logit-mean on the 128 held windows. Also report the duplicated-embedding control (two fully independent plain_half, 7,170,048 B) once, so the sharing cost is priced, not assumed.
- **mode:** process
- **prediction:** Ensemble held **2.82–2.86 at trial format, beating the byte-matched champion baseline 2.8580 (3,806,208 B)** and each body solo (~2.88–2.92) by ≥0.03; the duplicated-embedding control is predicted within 0.01 of the shared version — i.e. the second embedding's 3.34 MB buys nothing. Kill: ensemble ≥ best body solo − 0.01 (no decorrelation even across data seeds) or shared-vs-duplicated gap > 0.03 (the sharing is doing hidden damage and the honest artifact is the 7.17 MB one).
- **status:** queued
```mill
id: G-049
mode: process
run: --arm plain_half --rope --shared-ens 2
```

### G-050 ★ · Counter-sum merge — average the counters, not the weights: do counters merge better than weights?
- **source:** the vote trainer's own structure — a run's knowledge lives in (ternary state t, int8 counter c) pairs, and c is *integrated gradient evidence* that every weight-space merge in the literature throws away; the lab itself discards counters at serving (overlap Fact 1)
- **mechanism:** Train two plain_half+rope runs with the SAME init seed and different data streams (states start identical, diverge only by votes, so counters are commensurable). Each weight's implied latent position is L = 32·t + c ∈ [−64, +64]. Merge: L̄ = (L_A + L_B)/2, then t_m = clamp(round(L̄/32), −1, 1), c_m = round(L̄ − 32·t_m). Per-layer scales and all FP parts are averaged (standard soup on the FP side, same-init so averaging is sound). The merged artifact is ONE plain model: **3,585,024 B served — 221,184 B under the champion**. Companion readout in the same entry: state-only merge (G-053's rule) on the same two runs, so "counters vs states" is one paired comparison, not two anecdotes.
- **train.py:** new eval/merge path `--counter-merge A.pt B.pt` in train.py (loads two saved trainer states — requires `--save-state` on the donor runs: t, c, log_scales, FP state_dict), writes the merged model and reports held for donor A, donor B, state-only merge, counter merge, on the 128 held windows.
- **mode:** process
- **prediction:** Counter merge held **≤ 2.88 at trial format — beating both donors (~2.90, the plain_half baseline family) and beating the state-only merge by ≥0.015, at 3,585,024 B vs the champion's 3,806,208 (2.8580)**. Reasoning: where donors disagree on a weight, the one whose counter has climbed further toward its next flip holds the fresher evidence; the latent-average rule prices exactly that, while a state majority vote treats a just-flipped weight and a long-settled one as equals. Kill: counter merge ≤ state merge (counters carry no mergeable information beyond states — a clean, quotable negative that also caps F-033-style hopes) or merged ≥ worse donor.
- **status:** queued
```mill
id: G-050
mode: process
run: --arm plain_half --rope --counter-merge 2
```

### G-051 ★ · Sequential boosting — model 2 trains only on model 1's residual windows, served as a logit sum
- **source:** task territory (boosting) + the lab's own failweight line (MILL-406: ONE model oversamples its own failures *during* its own training — no second model, no additive serving, exists in the pool)
- **mechanism:** Model 1 = plain_half+rope, champion recipe, full format. Freeze it. Score every training-pool window by model 1's per-window loss; model 2 (same shape, fresh init) trains with window sampling probability ∝ clip(loss₁, 1.0, 6.0) — it spends its whole vote budget where model 1 is provably wrong-but-learnable (windows where loss₁ > 6 are near-irreducible on this corpus and are capped, the known boosting-on-noise guard). Serve shared-embedding (G-049 accounting): logit = logit₁ + α·logit₂, α ∈ {0.5, 1.0} chosen on 32 validation windows drawn from the training pool, never the 128 judge windows. **Served 3,826,176 B (+0.52% vs champion).** Distinct from the overlap exchange round: that patches *relative* weakness between *tilted generalists* on corpus-v2 at rung shapes; this is a strict sequence — model 2 has no generalist duty at all, only residuals.
- **train.py:** new sampler flag `--boost-from <m1-ckpt>` in train.py (precomputes per-window loss₁ once, ~1 extra pass over the pool, charged) + `--ens-alpha` in the eval path of `mill/run_compose.py`.
- **mode:** process
- **prediction:** Boosted pair held **2.83–2.87 at trial format vs the byte-matched champion 2.8580**, and — the discriminating claim — ≥0.015 better than G-049's *parallel* pair at identical served bytes: sequential residual training should buy more than a second independent opinion at this scale, because model 2's flips are spent entirely on windows the pair currently loses. Diagnostic reported either way: pair's loss on model-1's worst training decile vs G-049's pair on the same decile. Kill: boosted ≤ parallel pair (residual targeting earns nothing over independence — boosting joins failweight as a within-noise idea) or model 2 solo < 3.30 (it never became a language model at all, only a patch — then the α-fit is hiding a broken member).
- **status:** queued
```mill
id: G-051
mode: process
run: --arm plain_half --rope --boost-from m1 --ens-alpha fit
```

### G-052 · Three fully independent seeds at full price vs one bigger single model at the same bytes
- **source:** task territory (independently-seeded ensembles at equal total bytes vs one bigger model) — the honest-price version of G-049: NO sharing anywhere
- **mechanism:** Three independent plain_half+rope runs (seeds 0/1/2, own embeddings), served by logit-mean: **3 × 3,585,024 = 10,755,072 B**. Byte-matched single comparator: one plain+rope run at dim 464 × 4 layers = **10,761,088 B (+0.06%)**, same trial format, same tokens. Context baseline: the 10M plain rung serves 11,356,160 B (5.6% MORE than the ensemble) and the 10M layered rung recorded 2.9472 at 56 steps — different format, quoted only to show the ensemble is not sneaking a size advantage.
- **train.py:** no training change (existing flags: members `--arm plain_half --rope`; comparator `--arm plain --rope --dim 464 --layers-n 4`); ensemble read via `--ens-eval` from G-049's runner.
- **mode:** process
- **prediction:** Ensemble held **2.80–2.85 at trial format, beating the byte-matched 464×4 single by 0.02–0.06** — three decorrelated 0.88M-weight opinions over one 10.6M-weight opinion, because at fixed bytes the single model's extra weights are mostly *more embedding* (its FP stack is ~7.4 MB of its 10.76 MB), not more diverse computation. Kill: single ≤ ensemble (bytes really are fungible into width/depth at this scale, and every shared-embedding entry above inherits a problem: their wins were budget, not composition).
- **status:** queued
```mill
id: G-052
mode: process
run: --arm plain_half --rope --ens-eval 3 --vs-single 464x4
```

### G-053 · Ternary majority soup — merge the final states only, counters discarded
- **source:** model-soup literature transplanted to ternary states; the deliberate control twin of G-050 (same donors, dumber merge) — the pair is the experiment
- **mechanism:** From G-050's same two donors (plus a third seed for a true majority): per weight, merged state = majority of {t_A, t_B, t_C} (3-way splits and A≠B in the 2-donor read resolve to the better-solo donor's state); per-layer scales averaged; FP parts averaged. Counters are *not read*. Served as ONE plain model: **3,585,024 B, 221,184 B under the champion (2.8580)**; solo baseline plain_half 2.9010 family.
- **train.py:** `--state-merge A.pt B.pt C.pt` in train.py's merge path (sibling of `--counter-merge`; shares the `--save-state` donor plumbing).
- **mode:** process
- **prediction:** Majority soup held **2.88–2.91 at trial format: better than the mean donor, worse than G-050's counter merge by ≥0.015** — the gap between G-053 and G-050 *is* the measured value of the counter as a mergeable object, the lab's first price on its own training state. Kill: soup ≥ mean donor (independent-seed ternary states are not even majority-compatible — same-init divergence is chaos, not diversity; that result would also kill G-050's premise and must be reported with it).
- **status:** queued
```mill
id: G-053
mode: process
run: --arm plain_half --rope --state-merge 3
```

### G-054 · Flip-pattern diversity as a member-selection metric
- **source:** task territory — ensemble folklore says "diversity helps" but the lab has never *measured* diversity in its native unit: the flip pattern (which weights sit where, and which windows members disagree on)
- **mechanism:** Train 6 plain_half+rope members (seeds 0–5, trial format). For every pair compute (a) served-state Hamming distance (fraction of weights with different t) and (b) per-window loss disagreement on 256 training-pool validation windows. Select the 3-member subset by greedy max-min Hamming distance; serve shared-embedding (**4,067,328 B**: shared FP 3,403,776 incl. block-local FP for 3 bodies + 3 × 221,184 ternary). Comparators at identical bytes and identical member pool: best-3-by-solo-loss subset, and the mean of 5 random 3-subsets. The selection metric costs zero training — it spends information the runs already produced.
- **train.py:** `--diversity-select 3` in `mill/run_compose.py` (pairwise Hamming + disagreement tables printed to the record; subset chosen before any held evaluation — selection never sees the 128 judge windows).
- **mode:** process
- **prediction:** Diversity-selected trio held **0.01–0.03 better than the best-by-loss trio at trial format, both read against the champion-bytes neighbourhood (champion 2.8580 at 3,806,208 B; this trio serves +6.9% more bytes and must beat 2.8580 outright to justify itself)**. Predicted side-finding: Hamming distance and window disagreement correlate only weakly (ρ < 0.5) — weight-space diversity and function-space diversity are different goods, and only the functional one should predict ensemble gain. Kill: diversity trio ≤ random-trio mean (the metric selects nothing real) or Hamming predicts gain *better* than disagreement (then selection is trivial and the functional machinery is waste).
- **status:** queued
```mill
id: G-054
mode: process
run: --arm plain_half --rope --diversity-select 3
```

### G-055 · Counter transplant — swap two runs' counters at mid-training, keep their states
- **source:** member exchange, trainer-side — the causal test underneath G-050: if counters from another run can be *dropped into* a live run without damage, counters are fungible evidence and merging them is principled; if the transplant wrecks the run, each counter is married to its own state's history
- **mechanism:** Two plain_half+rope runs, same init seed, different data streams (G-050's donor configuration, so donors are shared across entries). At 50% of steps, swap the full counter arrays c_A ↔ c_B; states, scales, FP parts stay with their original run. Continue to full format. Controls: the unswapped donor pair (already run for G-050/005 — zero extra cost). Served: each transplanted model solo at **3,585,024 B**; secondary read: their shared-embedding logit pair at 3,826,176 B vs the control pair from G-049.
- **train.py:** new flag `--swap-counters <peer-state-file> --swap-at 0.5` on the Direct trainer (state file written at the swap step by a paired-runner mode in `mill/run_compose.py --paired-swap`).
- **mode:** process
- **prediction:** Transplant costs **+0.02..+0.06 vs the unswapped controls (~2.90 solo baseline family)** — counters encode *which evidence this state has already acted on*, so a foreign counter double-counts some flips and orphans others. The size of the cost is the deliverable: cost ≈ 0 would be the more explosive result (counters are pure evidence integrals, fully portable — G-050's merge becomes the conservative option and mid-run counter *pooling* becomes the obvious next entry). Kill (of the portability claim): cost > +0.10 — counters are state-history, full stop.
- **status:** queued
```mill
id: G-055
mode: process
run: --arm plain_half --rope --swap-counters peer --swap-at 0.5
```

### G-056 · Block grafting — serve block 1 from member A and block 2 from member B
- **source:** member exchange at the block level (model surgery between whole vote models; the factory's surgery line works on hive specialists, never on trainer checkpoints)
- **mechanism:** From trained plain_half+rope members, assemble grafts: (block1_A, block2_B) and (block1_B, block2_A), FP parts averaged, no retraining. Two arms: donors share the init seed (states start aligned) vs donors fully independent (different init — permutation misalignment should bite). Then a repair arm: each graft gets 14 steps (25% of a ladder run) of continued vote training at V=32. Served solo: **3,585,024 B** per graft. Baselines: donor solos (~2.90 family) at identical bytes; champion 2.8580 at 3,806,208 B.
- **train.py:** `--graft A.pt B.pt --take-blocks 1,2` in train.py's merge path + standard continued-training invocation for the repair arm (`--init-from graft.pt --steps 14`).
- **mode:** process
- **prediction:** Same-init grafts lose **+0.05..+0.15** vs donors (block 2 was vote-trained on block 1's *evolved* outputs, not its final ones — a real but bounded mismatch); different-init grafts lose **≥ +0.50** (near-collapse: the misalignment price, measured for the first time on vote models); 14 repair steps recover ≥ 70% of the same-init graft's deficit. Kill: same-init grafts ≥ +0.30 (blocks are not modules even under shared init — composition below the whole-model level is dead in this lab, which fences G-060 too) or different-init grafts lose < +0.10 (alignment doesn't matter, which would contradict everything known about permutation symmetry and demand its own investigation).
- **status:** queued
```mill
id: G-056
mode: process
run: --arm plain_half --rope --graft A B
```

### G-057 · Ensemble-into-one distillation — a vote-trained student drinks the ensemble
- **source:** task territory (distillation *between vote models*) — distinct from MILL-113/115/A-064 on both ends: the teacher is a *vote ensemble*, not an FP twin, and the student is *vote-trained*, not STE/layered
- **mechanism:** Teacher = G-049's shared two-body ensemble (3,826,176 B, teaching-time only). Student = one plain_half body, vote-trained from scratch on the same windows with loss = CE + 1.0 · KL(teacher‖student) at temperature 2 (MILL-113's dose, kept deliberately so the teacher swap is the only change). The vote counters integrate the KD gradient's sign exactly as they integrate CE's — the question is whether a *ternary teacher's* dark knowledge (its per-token uncertainty, produced by two disagreeing ternary bodies) survives the 1-bit vote channel. **Student served solo: 3,585,024 B — 221,184 B under the champion.**
- **train.py:** new flag `--kd-ens <ens-ckpt> --kd 1.0` on the Direct trainer in train.py (teacher forward per step, frozen, charged: expect ~0.7× steps/minute, reported).
- **mode:** process
- **prediction:** Student held **2.86–2.89 at trial format — recovering ≥ 50% of G-049's ensemble gain over a solo plain body while serving under the champion's 3,806,208 B (champion baseline 2.8580)**; and ≥ 0.01 better than a CE-only student trained identically (the in-entry control). Kill: student ≈ CE-only control (the vote channel cannot carry teacher distributions — KD on this trainer needs the FP teacher's smoother signal, MILL-113's design was right by necessity) or student ≥ 2.92 (distillation actively hurts votes).
- **status:** queued
```mill
id: G-057
mode: process
run: --arm plain_half --rope --kd-ens shared2 --kd 1.0
```

### G-058 · Distill the ensemble at the counter level — initialize the student's counters from the teachers' disagreement
- **source:** composition of G-050 and G-057 — if counters are evidence (G-050's claim), a student should be able to *inherit* evidence, not just imitate outputs
- **mechanism:** Student starts from the G-053 majority-soup states. Its counters initialize NOT at 0 but at c₀ = (c_A + c_B)/2 from G-050's donors, clipped to ±16 (half of V, so no inherited flip can fire without ≥ 16 fresh agreeing votes — the F-015 warm-start cap logic applied across models). Student then vote-trains on CE only, full format. Control: identical soup init with counters at 0. **Served 3,585,024 B.**
- **train.py:** `--init-counters avg --init-from soup.pt` on the Direct trainer (donor plumbing from `--save-state`).
- **mode:** process
- **prediction:** Counter-inherited student beats the zero-counter control by **0.01–0.03 at trial format** (both vs the plain_half 2.9010 solo family; champion 2.8580 at +221,184 B remains the adoption bar) — inherited counters aim the student's first flips at the weights both teachers were *about* to move, the exact population a cold start wastes its first ~32 steps re-deriving. Kill: inherited ≤ control (teacher counters point at teacher-specific futures; cross-model evidence inheritance is dead even when output distillation in G-057 works — a clean split between the two distillation channels).
- **status:** queued
```mill
id: G-058
mode: process
run: --arm plain_half --rope --init-from soup --init-counters avg
```

### G-059 · Agreement-gated partial merge — merge the blocks where members agree, ensemble only where they don't
- **source:** G-054's diversity tables + G-056's grafting question, composed: full ensembles pay a second body for *every* block; if disagreement is concentrated in one block, the agreeing block can be merged for free
- **mechanism:** From G-049's two bodies: per block, compute served-state agreement (fraction of equal t). Blocks with agreement ≥ τ (τ ∈ {0.85, 0.90, 0.95}, chosen on validation windows) are merged by G-050's latent-average rule into ONE block; blocks below τ stay as two parallel bodies under the shared embedding. Predicted artifact (block 1 merges, block 2 doesn't): shared FP 3,343,872 + merged block (110,592 ternary + 9,984 FP) + 2 unmerged blocks (2 × 120,576) = **3,705,600 B — 100,608 B under the champion**, with the logit read taken after the unmerged block(s) (both copies forwarded, logits averaged at the head).
- **train.py:** `--gated-merge A.pt B.pt --agree-tau {0.85,0.90,0.95}` in the merge path of train.py / `mill/run_compose.py` (block-wise agreement report is a required output, not a by-product).
- **mode:** process
- **prediction:** The gated artifact lands **within 0.01 of G-049's full ensemble at trial format while serving fewer bytes than the champion (2.8580 at 3,806,208 B)** — *if* agreement is block-concentrated (predicted: block 1 agreement ≥ 0.90, block 2 ≤ 0.85, because late blocks absorb the data-seed divergence). Kill: agreement is uniform across blocks (within 0.02) — partial merging has no structure to exploit at 2 blocks, and the entry retires until a ≥4-block chassis gives it room; or the gated artifact loses > 0.02 vs the full ensemble at any τ (the merged block was carrying diversity the agreement metric can't see).
- **status:** queued
```mill
id: G-059
mode: process
run: --arm plain_half --rope --gated-merge --agree-tau 0.90
```

### G-060 · How the vote is taken — weighted, geometric, and median logit composition of the same members
- **source:** the composition rule itself, never varied in this lab: every ensemble read above assumes uniform arithmetic logit-mean (inherited from F-033's spec and the overlap program's primary read)
- **mechanism:** Eval-only, on G-052's three independent members (no new training): compare (a) uniform logit-mean [the standing rule], (b) weighted logit-mean — per-member scalar weights + one temperature fitted by minimizing loss on 256 training-pool validation windows (4 scalars total, +16 B served, counted), (c) probability-mean (average softmax, then log), (d) median-of-logits per token (robust rule: one bad member cannot drag a token). Plus a stress read: corrupt one member (shuffle its block-2 rows) and re-read all four rules — the robust rule should degrade least, pricing robustness as a property, not a hope. **Served 10,755,072 B (+16 B for rule (b)) in all arms** — the members are identical; only the read differs. Baselines: members solo (~2.90 family); rule (a) is the number G-052 stands on.
- **train.py:** `--ens-rule {logit,weighted,prob,median}` in the `--ens-eval` path (weight fit on validation windows only; judge windows untouched by fitting).
- **mode:** process
- **prediction:** On clean members the four rules land **within 0.01 of each other** (members this similar leave the rule nothing to decide — itself the finding that retires rule-shopping at this scale); weighted beats uniform by ≤ 0.01 and its fitted weights stay within [0.7, 1.4] (no member is secretly carrying the trio). Under corruption: median loses ≤ half what logit-mean loses. Kill: any clean-rule gap > 0.02 (the standing uniform read has been leaving real loss on the table in every ensemble number the lab will ever quote — then the winning rule must be retro-applied to G-049/003/004's reads before their verdicts stand).
- **status:** queued
```mill
id: G-060
mode: process
run: --arm plain_half --rope --ens-eval 3 --ens-rule all
```

---

## Rank order and the ★ three

1. **G-049 ★** — the exact-bytes ensemble: two plain bodies on one shared
   embedding serve at 3,826,176 B vs the champion's 3,806,208 B. If
   decorrelated wholes beat summed components at the *same* bytes, the
   layered result gets its explanation and the lab gets a new champion form
   for free. Cheapest decisive composition test available.
2. **G-050 ★** — counter-sum merge: the only entry that treats the vote
   counter as what it is — integrated evidence — and asks whether it merges
   better than the weights it produced. A win ships a *single* model under
   champion bytes; a loss cleanly closes cross-run merging. Either way the
   lab learns what its training state is worth.
3. **G-051 ★** — sequential boosting at G-049's exact bytes: the
   head-to-head (sequential-residual vs parallel-independent) is the
   composition question with the most riding on it, because the overlap
   program's exchange loop is a parallel-patching bet — this prices the
   sequential alternative at 1/12th of its byte budget before it scales.

Then G-052 (the fungibility control every other entry leans on), G-057,
G-054, G-053, G-055, G-059, G-058, G-056, G-060 (eval-only; run it
the moment G-052's members exist, whatever its rank).

**Best single idea: G-049.** It needs no new mechanism — two bodies, one
embedding, a logit mean — and its byte match to the champion is exact to
0.52%, so its verdict cannot be argued with on budget grounds. It also
manufactures the donors, checkpoints, and shared-embedding serving path
that G-051, G-054, G-057, and G-059 all reuse.

## Lens 6 — Throughput (was TH-###)

### G-061 · Three-stage funnel with a known-answer calibration set ★
- **source:** the full-pool cost itself: 368 × 75 s ≈ 7.7 h per probe pass, and 24 min per
  trial behind it. Of the 13 completed non-champion arms in runs.jsonl, 6 lost to the champion
  by ≥ +0.10 at 8 min (anneal +0.99, mag +0.28, layered +0.24, plain +0.22, ste +0.14,
  cooldown +0.11) — 46% of everything the lab has ever run was a catastrophe-class loser that
  a screen never needed 75 s, let alone 24 min, to bury.
- **mechanism:** Stage 0 (15 s, ≈5 steps, no held eval): kill only on catastrophe signals —
  flip share ≥3× or ≤⅕ of job zero's paired value (mag sits at 0.09×, the D §4 FLIP-STORM
  flag already uses 3×), train-loss slope worse than job zero's paired slope by a calibrated
  margin, or a crash/divergence. Stage 0 cannot promote and cannot kill anything in the
  ambiguous band. Stage 1 = today's 75 s probe, unchanged. Stage 2 = trial, unchanged.
  Before stage 0 judges anything live, calibrate it on a **known-answer set**: six arms whose
  8-min verdicts runs.jsonl already owns (champion = tie, carry +0.018 = near, plain_half
  +0.043 = near, cooldown +0.113 = loser, anneal +0.992 = catastrophe, ste_half −0.038 =
  winner) run once at 15 s; stage-0 thresholds are set from those six readings and the
  measured information loss (which losers stage 0 misses, which nears it would have killed)
  is written into PROMOTE.md next to the bar it modifies.
- **change:** `mill/screen.py`: add a stage-0 pass (probe_minutes 0.25, verdicts `kill0` /
  `pass0` ledgered distinctly; `kill0` is generation-scoped like any verdict) gated on a
  one-time calibration block in `mill/PROBE-NOISE.md` recording the six known-answer
  readings; PROMOTE.md gains the stage-0 paragraph with its measured loss table.
- **payoff:** at the measured 46% catastrophe share, expected cost per screened idea =
  15 s + 0.54 × 75 s = 55.5 s vs 75 s → **≈65 vs 48 ideas/h solo (+35%)**, ≈2.0 h saved per
  full pool pass, plus every stage-0 kill is a trial that can never be wasted (24 min each).
  If the true catastrophe share is only 25%, the saving is still ≈1.0 h/pass. Arithmetic
  uses the 13-arm history; the calibration set replaces the assumption with a measurement
  before the stage is trusted.
- **validity risk:** a slow-starting winner (FP-first MILL-111/112, cascade-style entries
  whose own pool text says the probe under-measures them) could look catastrophic at 5 steps.
  Guard: stage 0 kills on mechanism signals (flip share, divergence), never on held/train
  level alone; every PROMOTE.md exception-listed id bypasses stage 0 entirely; and the
  calibration set must show zero false kills on its near/winner members before stage 0
  goes live — one false kill in calibration keeps the stage advisory-only.

### G-062 · Banded second seed: seed economy where the decision actually lives ★
- **source:** seed 0 alone misleads at a measured rate: 2/13 sign flips vs the 3-seed mean
  (carry, JEPA control) and 1/13 false promotes (ste_half: seed-0 Δ +0.0615 ≥ 0.05 bar,
  mean Δ +0.0375) in runs.jsonl. A false promote costs a 24-min trial; a false kill costs
  the idea for the generation (RIGOR-AUDIT §3a(i)). E-022 audits the losers *after* the
  generation; nothing audits a lucky winner before it spends 24 min.
- **mechanism:** probes stay seed-0/75 s outside the decision band. Any probe landing in
  |Δ| < 0.10 (the band containing every measured sign flip: carry 0.001–0.018, JEPA control
  0.013–0.059, ste_half 0.038–0.062, plain_half 0.042–0.043, layered_half 0.017–0.041)
  automatically gets a seed-1 probe at the same budget, judged against a seed-1 job zero
  measured in the same pass; the verdict uses the 2-seed mean Δ. Outside the band, one seed
  has never flipped in the lab's record, so one seed is what it gets.
- **change:** `mill/screen.py`: after ledgering a probe, if |Δ| < 0.10, queue the same id
  with seed 1 plus a seed-1 MILL-000 for that pass; ledger lines gain the second seed and
  the verdict rule (2-seed mean vs the same 0.05/0.02 bars) is written into PROMOTE.md.
  Distinct from E-022: this changes live verdicts in both directions, E-022 only counts
  the damage afterwards.
- **payoff:** band share in the 13-arm history = 5/13 ≈ 38% → added cost 0.38 × 75 s ≈
  29 s per idea. False-promote rate 1/13 ≈ 8% → expected trial waste avoided
  0.08 × 24 min ≈ 1.9 min per idea. Net ≈ **+1.4 min saved per idea screened, ≈8–9
  trial-hours per full pool pass**, before counting rescued false kills (unpriced upside).
  Small-sample basis (n=13 arms) — the band and rates are re-estimated from the mill ledger
  after generation 0 and the entry says so in PROMOTE.md.
- **validity risk:** the 2-seed mean is a different estimator than the pool's other
  verdicts, so band verdicts and non-band verdicts are not strictly commensurable, and a
  seed-1 job zero doubles that pass's baseline cost when the band is busy. Guard: both
  seeds' raw Δs are ledgered individually (the mean is derived, never the only record);
  the trial stage is untouched, so a band verdict can only spend or save a trial, never
  adopt; re-check the flip rate on ledger data after gen 0 and narrow the band if the
  measured flip rate outside it is truly zero.

### G-063 · Sequential trials: spend the third seed only when it can still change the verdict ★
- **source:** a trial is 3 × 8 min = 24 min, the most expensive unit in the funnel
  (CAPACITY: 7.5 trial-units/h theoretical, 0 delivered). PROMOTE.md's adoption rule has
  two parts — mean beats ref by >2 sd AND >0.01, **and ≥2 of 3 seeds individually beat the
  reference mean** — and the second part can become mathematically undecidable-or-decided
  before the third seed runs.
- **mechanism:** run trial seeds in fixed order 0, 1, 2 with two pre-registered stops.
  (a) *Guard-dead stop:* if seeds 0 and 1 both fail to beat the reference mean, the
  per-seed guard can never pass (at best 1 of 3) — stop; verdict `below`, zero information
  loss, it is arithmetic, not inference. (b) *Mean-dead stop:* if after 2 seeds even a
  third seed at the best value ever recorded for this chassis family (a bound set in
  PROMOTE.md from runs.jsonl, e.g. 2.815, ste_half seed 0) could not pull the mean under
  the adoption threshold, stop; verdict `below`. Additionally, the stale-reference control
  (3 × 8 min champion re-run, PROMOTE.md) is run **once per fingerprint epoch** and shared
  by every trial judged while code_sha + corpus_sha are unchanged, instead of once per trial.
- **change:** `mill/screen.py` trial runner: judge after each seed against the two stop
  rules; `mill/trials.jsonl` gains `stopped_after` on the verdict event; the shared control
  is ledgered once with kind `control` and referenced by trial id. PROMOTE.md records both
  stop rules and the optimistic-bound constant.
- **payoff:** each guard-dead or mean-dead trial saves the full third seed = **8 min**.
  At an illustrative 20% promotion rate the pool yields ≈74 trials; if even ⅓ die on the
  first two seeds (the historical arms suggest most trials will fail — only 1 of 13
  completed arms beat the champion at all), that is ≈74 × ⅓ × 8 min ≈ **3.3 trial-hours
  per generation**, plus 24 min × (trials per epoch − 1) from control sharing. Promotion
  rate and dead-share are unmeasured until the mill runs — marked as such; the per-trial
  saving itself (8 min, zero-loss for stop (a)) is exact.
- **validity risk:** stop (b) smuggles in an assumption (the optimistic bound) — a freak
  third seed better than anything in runs.jsonl would be censored. Guard: the bound is set
  generously (best-ever seed minus a further 0.02), stop (b) verdicts are ledgered as
  `below (bounded)` so they are distinguishable and re-runnable on a human's word, and
  stop (a) — the zero-assumption half — is expected to do most of the saving anyway.

### G-064 · Held-eval economy: cache held_init exactly, subsample held_final sequentially
- **source:** every run pays held_loss twice (init + final; train.py main and
  sweep_probe.run_one both do). Each call is 128 windows in 4 batches of 32 — derived
  ≈128 forward-equivalents ≈ 1.3 training steps ≈ **~4 s per call, ~8 s of a 75 s probe
  (~11%)**, and ~53% of a 15 s stage-0 budget, which is what makes cheap stages impossible
  while eval stays full-size. (Derived from step timing, not yet profiled — compute's
  probe_phases.py is the instrument that replaces this estimate; marked accordingly.)
  Meanwhile held_init is *deterministic*: seed-0 champion construction records exactly
  **8.3138** in runs.jsonl and the JEPA smoke test reproduced it exactly (RIGOR-AUDIT §2b).
- **mechanism:** (1) Cache held_init keyed by (seed, construction-affecting flags: arm
  family shape, --dim, --layers-n, rope, init-affecting flags); trainer-only flags share
  the cached value because construction — and therefore init held — is identical. The
  first run under any new key still measures it, and the sweep's 8.3138 invariant check
  runs against the cache. (2) held_final becomes sequential: evaluate a pre-registered
  nested 32-window subset first (held_windows' pick is evenly strided, so the first 32
  picks are themselves an even cover), compute the per-window SE of Δ vs job zero's
  same-subset Δ, and extend to 64, then 128, only while the verdict is inside the
  confidence margin of a bar (0.05/0.02). Clear verdicts stop at 32.
- **change:** `train.py`/`sweep_probe.py`: held_loss returns per-window losses (the
  reduction='sum' loop already visits batches; split to per-window accumulation);
  `mill/screen.py` holds the init cache in the ledger (kind `held_init`, keyed as above)
  and applies the sequential-extension rule; every ledger line records `held_n` actually used.
- **payoff:** init cache saves ~4 s on every trainer-flag probe (≈5% of probe cost;
  process-mode probes included). Sequential final eval saves ~3 s on the ~70% of probes
  whose 32-window Δ is clear of the bars (estimate from the historical Δ spread — most
  arms sat ≥0.10 from the champion) → combined ≈ **48 → ~52–53 probes/h solo**, and it is
  the enabler that keeps G-061's 15 s stage from spending half its budget on evaluation.
- **validity risk:** per-window losses are heavy-tailed, so a 32-window SE can understate
  the true spread and stop early on a flattering subset. Guard: subsets are nested and
  fixed in advance (no adaptive window choice), extension is mandatory whenever the CI
  touches *either* bar, `held_n` is on every ledger line so any verdict can be re-checked
  at full 128, and G-061's calibration set is also run at held_n ∈ {32, 64, 128} to
  measure the stopping rule's actual error before it judges live probes.

### G-065 · Step-10 early kill from flip share + paired loss slope (kill-only predictor)
- **source:** at ≈3.0 s/step, steps 11–25 of a probe are 45 s — 60% of its cost — spent
  after the mechanism's vital signs are already readable. Flip share separates the
  recorded failures by an order of magnitude (mag 0.00010 vs champion 0.0011) and is
  seed-stable to ±3% for the champion; the anneal disaster (held 3.85, +0.99) is the class
  of run the mill should never pay full price for again. No probe has ever logged a
  mid-run reading, so the predictor's accuracy at step 10 is **unmeasured** — this entry
  is a measurement protocol first, a kill rule second.
- **mechanism:** sweep and process probes log, at step 10, flip share so far and the
  train-loss slope over steps 5–10, *paired* against job zero's same-step readings on the
  identical batch stream (same seed → same stream, the pairing the lab already relies on).
  A probe is killed at step 10 only if BOTH signals agree it is off-mechanism: flip share
  outside [0.2×, 3×] of job zero's AND paired slope worse by more than a calibrated margin.
  Train loss alone never kills (train_last100 is documented to misrank held). The rule
  activates only after its precision is measured on G-061's calibration set plus the
  first 30 live probes' step-10 logs vs their completed verdicts (target: zero false
  kills on eventual `near`/`promote` probes; anything less keeps it advisory).
- **change:** `sweep_probe.run_one` + train.py probe path: emit a `MID` record at step 10
  (flip share, slope, steps) into runs.jsonl; `mill/screen.py` applies the kill only when
  `mill/PROBE-NOISE.md` carries an activated threshold pair with its measured precision.
- **payoff:** if the activated rule kills 25% of probes at step 10 (plausible against the
  46% catastrophe share, discounted for the both-signals-agree requirement), saving =
  368 × 0.25 × 45 s ≈ **69 min per pool pass**, i.e. ~15% on top of G-061 (the two
  compose: stage 0 catches the diverged, step-10 catches the slow failures). Marked
  estimate — the kill rate is the calibration's output, not an input.
- **validity risk:** some mechanisms are late by design (leak/freeze/schedules act over
  the full run; F-002/F-022's pool text says a flat probe must not kill them). Guard:
  kill-only, never promote; exception-listed ids and any entry whose pool text declares
  a long-horizon mechanism are exempt by id list in screen.py; a killed probe is ledgered
  `kill10` with its mid readings, re-runnable on a human's word, and the activation gate
  (zero measured false kills) is the entry's own kill test.

### G-066 · Dose-family sequential testing: middle dose first, extremes on evidence
- **source:** the pool is full of 3-point dose brackets that are currently paid in full
  regardless of outcome: mag-cal MILL-201/202/203, vsched 204/205/206, leak 209/210/211
  (+212/213), freeze 215/216/217, modal 218/219, plus the V grid (501–509, nine points),
  gate-q grid (601–606), scale-granularity, rope-frac, SWA and MoE brackets — conservatively
  ~45 sibling probes in ≥15 families. A dead family currently costs 3 × 75 s to learn one fact.
- **mechanism:** within a dose family, probe the middle (champion-nearest) dose first.
  Extremes run only if the middle lands `promote` or `near` (|Δ| < 0.05), or — the
  non-monotonicity hedge — if the middle is `flat` but the family's mechanism predicts a
  threshold effect, in which case exactly one extreme (the predicted-active side) runs.
  A `below` middle with no threshold prediction closes the family for the generation;
  the closure is ledgered per skipped sibling so the saving is auditable, not silent.
- **change:** pool-order/protocol change only: `mill/screen.py` gains a family map
  (family id per bracket, derivable from the pool's own "dose variant" source lines) and
  defers siblings until the middle's verdict exists; PROMOTE.md documents the rule and
  the threshold-effect hedge. No train.py change.
- **payoff:** a dead family costs 75 s instead of 225 s (saves 150 s); a live family costs
  the same as today. At ~15 families and the historical ~50% dead-family rate: ≈7.5 ×
  150 s ≈ **19 min saved per generation pass**, growing linearly if later waves add
  brackets the same way A–F did. Zero cost to winners by construction.
- **validity risk:** a genuinely non-monotone dose response (middle flat, extreme wins —
  e.g. a threshold that only bites at V=96) would be closed wrongly. Guard: the
  threshold-hedge run above; family closures are per-generation (a new champion re-opens
  them, as all verdicts do); and any family whose three pool predictions are non-monotone
  on their face is exempted in the family map at merge time.

### G-067 · Fork screening for late-acting families: one trunk, several endings
- **source:** several pooled families differ *only* in what happens late in the run —
  vsched 204/205/206 (threshold path), freeze 215/216/217 (freezing bites after flips
  accumulate), polish MILL-306, tail-freeze-style entries — yet each pays a full
  independent 25-step probe whose first ~15 steps are bit-identical work: same seed →
  same init, same batch stream, and the flags do not act until late. Modal readout
  MILL-218/219 already exploits the readout version of this (one run, two verdicts,
  noted in RIGOR-AUDIT §1a); the fork generalises it to training endings.
- **mechanism:** for a certified late-acting family, run one shared trunk to the fork
  step (step 15 of 25 at probe scale), snapshot trainer state in-process, then branch
  each dose for the remaining 10 steps and score each branch against a job zero forked
  the same way (its own trunk, its own unchanged branch). Certification = the flag's
  code path provably cannot alter any update before the fork step (checked by reading
  the flag's implementation, recorded per family in PROBE-NOISE.md).
- **change:** `mill/sweep_probe.py`: an in-process fork mode for certified families
  (state snapshot/restore around branches; each branch still appends its own runs.jsonl
  record, tagged `fork:<family>`). Probe-only — trials are never forked.
- **payoff:** a 3-dose family costs 15 + 3 × 10 = 45 step-equivalents instead of 75 —
  **40% off forkable families** (225 s → ~135 s + snapshot overhead per family at probe
  scale). Applied to the ~4 clearly late-acting brackets above: ~6 min/pass today; the
  real value is that it scales with every future schedule/tail/readout family, which
  waves A–F kept producing. Estimate — snapshot overhead at this model size is small
  (2.2 MB mechanism state) but unmeasured.
- **validity risk:** a flag certified late-acting that actually leaks early influence
  (e.g. a schedule that pre-computes from total steps and changes step 1 behaviour)
  would make branches measure a trunk that never existed standalone. Guard: certification
  requires a step-10 log match — each branch's trunk-phase flip share and loss must equal
  the standalone probe's step-10 log (G-065's MID record) the first time the family runs;
  any mismatch decertifies the family permanently and its fork verdicts are voided in the
  ledger, not silently kept.

### G-068 · Steps as a ledgered covariate: adjust Δ for the machine, keep the wall clock
- **source:** probe verdicts are wall-clock verdicts, and the machine's speed is a
  measured confound: JEPA-control runs at 129–139 steps scored mean held 2.9173 vs the
  same config's 2.8580 at 154–170 steps — ≈+0.06 of held elevation riding on step count
  alone, larger than the 0.05 promotion bar. plain_half's seeds show the same coupling
  in miniature (176 steps → 2.8692 vs 150 steps → 2.9179). E-023 would fix this by
  changing the budget to fixed steps; this entry deliberately does not — it keeps the
  funnel's wall-clock semantics and removes the bias arithmetically.
- **mechanism:** every probe already ledgers `steps`. Per generation, fit the local
  steps→held slope from data the mill already owns: job-zero replicates across passes
  (same config, varying steps — a pure machine-speed instrument) plus the calibration
  arms. Report Δ_adj = Δ_raw + slope × (steps_probe − steps_jobzero) alongside Δ_raw.
  Promotion uses Δ_raw until the calibration shows Δ_adj has lower pass-to-pass replicate
  spread than Δ_raw on job zero itself; from then on Δ_adj is primary and Δ_raw is the
  reported cross-check. A crude first slope from plain_half's seeds is ≈ −0.0019/step,
  implying a ±5-step machine wobble at probe scale biases Δ by ≈ ±0.01 — 20% of the bar.
- **change:** `mill/screen.py`: compute and ledger both Δs (one extra field); the slope
  fit + the spread comparison live in `mill/PROBE-NOISE.md`, refreshed per generation.
  No change to budgets, budgets' meaning, or train.py.
- **payoff:** no probes/h gain on paper — the payoff is trial-hours: verdicts stop
  promoting step-lucky probes and killing step-starved ones. If step noise contributes
  even 0.01 of spurious Δ spread against a 0.05 bar, roughly 1 in 5 borderline verdicts
  is machine weather; at ~74 trials per generation that is on the order of **2–4 wasted
  or missed trials (48–96 min) per generation** reclaimed. Marked estimate — the slope
  and the spread reduction are measured by the entry's own first-generation fit.
- **validity risk:** the steps→held slope is itself estimated from confounded data
  (different seeds differ in more than steps), and over-adjusting could manufacture
  verdicts. Guard: the slope is fit on job-zero replicates first (steps vary there only
  via machine speed), the switch to Δ_adj-primary requires a *measured* replicate-spread
  reduction, and both numbers stay on every ledger line forever — any verdict can be
  re-read under the other convention.

### G-069 · Proxy-context pre-screen: paired Δ at ctx 128 for context-free mechanisms
- **source:** per-step cost is dominated by tokens processed: batch 32 × ctx 256. The
  pool's own context entries (A-045/A-046 curricula, MILL-137/138 SWA) treat ctx as a
  variable, but the *screening format* has never used it: most pooled mechanisms — vote
  accounting, gates, counters, leaks, freezes (sections A/B of the pool) — make no
  reference to context length at all, yet every one of their probes pays full ctx-256 price.
- **mechanism:** a kill-only pre-screen at ctx 128 (batch 32): tokens/step halve, so the
  same 75 s buys roughly twice the steps (derived ≈1.7–2×, attention's quadratic term is
  small at dim 192/ctx 256 — marked estimate). The verdict is a *paired* Δ against job
  zero also run at ctx 128 in the same pass; absolute held values are never compared
  across contexts. A ctx-128 `below` (Δ ≤ −0.02, the flat/below boundary) closes the idea
  for the generation; anything else proceeds to the standard ctx-256 probe, which remains
  the only verdict that can promote. Excluded by construction: anything whose mechanism
  names position, context, RoPE, SWA, or attention span (MILL-133–138, 905/906, A-045/046,
  A-071, A-086/087 and kin) — for them ctx is the treatment, not the format.
- **change:** `mill/sweep_probe.py` + screen.py: a `--ctx` job field honoured by the
  pre-screen pass only (window slicing already exists in train.py's sampler shape);
  ledger lines record `ctx: 128` so a proxy verdict is never mistaken for a real one.
  Rank preservation (does ctx-128 Δ order ideas the way ctx-256 Δ does?) is measured on
  G-061's calibration set at both contexts before the screen may kill anything.
- **payoff:** if ~60% of the pool is context-free mechanism (sections A/B dominate waves
  A–F) and the screen kills the historical ~45% loser share among them at ~40 s average
  cost instead of 75 s: saving ≈ 368 × 0.6 × 0.45 × 35 s ≈ **58 min per pass**, and the
  survivors arrive at the real probe with a second, independent-context reading attached.
  Estimates throughout — the calibration's rank-correlation number decides whether this
  entry lives.
- **validity risk:** vote dynamics are step-count-sensitive (more steps at ctx 128 =
  more flips banked), so a mechanism could genuinely behave differently, not just noisily,
  at the proxy context — the half-control's lesson (layered's win was its step count) is
  exactly this trap. Guard: kill-only asymmetry (a proxy pass never promotes, a proxy
  kill requires Δ ≤ −0.02 *and* flip share inside the champion's band, so step-regime
  artefacts that move flips disqualify the kill), plus the calibration gate: if the six
  known-answer arms do not preserve their ordering at ctx 128, the screen is retired
  before it judges a single live idea.

### G-070 · Dual-read probes: every 75 s probe also yields its 15 s reading, for free
- **source:** G-061 and G-065 both need paired (short, full) readings to price their
  information loss, and a dedicated calibration campaign to get them costs ~30 extra
  probes (~37 min) per generation — and goes stale the moment the champion changes.
  Meanwhile every probe already *passes through* its own step-5/step-10 states and
  throws them away; job zero is re-measured fresh every pass and its early segment is
  likewise discarded.
- **mechanism:** probes and job zero log two extra readings in-flight: a 32-window
  subsampled held eval (G-064's machinery, ~1 s) at the 15 s mark, and the G-065 MID
  record at step 10. These readings are **log-only** — under the CANDIDATES-D §4 rule, a
  mid-run held value never feeds back into its own run; they exist so that, after each
  pass, the mill can compute the *realised* information loss of the 15 s stage and the
  step-10 predictor on live data (what would stage 0 have killed? what did it cost?)
  and recalibrate thresholds for the *next* pass. Job zero's 15 s reading doubles as the
  stage-0 baseline for that same pass — no separate stage-0 job zero is ever run.
- **change:** `sweep_probe.run_one` / train.py probe path: timed checkpoint eval at
  15 s (subsampled, log-only, stamped `dual_read` in runs.jsonl); `mill/screen.py`
  appends a per-pass stage-loss summary line to the ledger. Cost ≈1–2 s per probe.
- **payoff:** replaces a recurring ~37 min/generation calibration campaign with ~1–2 s
  per probe (~10 min spread across a full pass, most of it inside time already budgeted),
  and — the larger prize — it converts G-061/G-065 from one-off calibrations into
  continuously re-measured instruments, so their thresholds track champion changes
  instead of silently rotting. Net ≈ **25+ min saved per generation, every generation**,
  plus the audit trail that keeps the cheap stages honest.
- **validity risk:** the checkpoint eval perturbs the run it rides on (eval switches
  EASE to full rounding and back, costs ~1 s of the 75 s budget — a ~1–2% step tax on
  every probe, applied to job zero too, so the pairing absorbs most of it). Guard: the
  tax is identical for probe and baseline in the same pass; the first pass runs a
  parity check (dual-read job zero vs a clean job zero in the same pass must agree
  within the replicate spread, the CONCURRENCY.md honesty pattern) before dual-read
  verdicts are trusted for calibration.

### G-071 · Fixed train-window proxy judge for the cheapest stage (spend held windows last)
- **source:** RIGOR-AUDIT §1b: every verdict is a selection event on the same 128 held
  windows, and the mill will issue thousands. The cheapest stages are where verdict
  volume is highest and individual verdicts matter least — exactly where the held set
  should not be spent. runs.jsonl already hints a proxy can rank: at 8 min, train_last100
  separates the catastrophe class cleanly (anneal 4.31–4.37 vs champion 3.03–3.15) even
  though it misranks the close arms — a proxy only needs to work where the cheap stage works.
- **mechanism:** fix a set of 128 *training* windows once (drawn via offsets(), held-safe
  by construction, frozen in a small file in mill/). Stage-0/stage-1 pre-screens judge
  paired Δ on this proxy set instead of held; held is touched only by the standard 75 s
  probe and above. Proxy Δ ships with its per-window SE (G-064's per-window plumbing),
  so every proxy verdict carries a confidence, and the proxy↔held Δ correlation is
  tracked per pass from the probes that run both (G-070's dual reads make this free).
- **change:** `mill/proxy_windows.json` (generated once by a offsets()-driven script,
  offsets ledgered); sweep_probe gains an eval-set switch used only by pre-screen jobs;
  PROMOTE.md states that no promotion, adoption, or champion reference ever reads the
  proxy set.
- **payoff:** throughput of *trustworthy* verdicts rather than raw probes/h: the two
  cheapest stages stop consuming held-set selection budget, which defers the
  confirmation-set pressure that otherwise grows with every generation — priced
  conservatively as avoiding one extra confirmation/control cycle (24–48 min) per
  generation, plus it makes G-061's stage 0 judgeable at 15 s without the held-eval
  cost G-064 prices at ~53% of that budget. Proxy↔held correlation at the catastrophe
  band is **unmeasured** — marked as such; the calibration set measures it first.
- **validity risk:** a proxy drawn from training windows can be memorised into
  uselessness as runs lengthen, and any idea whose mechanism interacts with the
  train/held distinction (failweight MILL-406/407, curriculum entries) would be judged
  on the wrong axis. Guard: proxy verdicts are kill-only and catastrophe-band-only;
  sampling-interacting families are exempt by id; the tracked proxy↔held correlation is
  printed per pass and the proxy judge auto-suspends if the correlation in the kill
  band drops below its calibrated floor.

### G-072 · Process-mode caravan: amortise startup for code-path probes, prove isolation per job
- **source:** process-mode probes (every code-path change — the majority of waves A–F)
  each pay full interpreter + torch import + corpus memmap + held-window construction,
  which IDEA-POOL's execution-modes note calls "a large share of a 75-second probe's
  cost"; sweep mode already amortises it across batches of 8, process mode amortises
  nothing. The exact startup figure is **unmeasured** (compute/probe_startup.py exists
  to measure it; no results recorded yet) — this entry is conditional on that number.
- **mechanism:** run process-mode probes as a caravan: one parent process loads corpus
  and held windows once, then spawns each probe as a *fresh interpreter child* that
  inherits the read-only memmap via fork (copy-on-write; the child builds its own model,
  trainer, and RNG streams exactly as a standalone run). Isolation is not asserted, it
  is *checked per job*: each child must reproduce the seed-0 held_init invariant for its
  construction key (8.3138 for the champion shape, G-064's cache) before training, and
  one job per caravan is randomly designated a parity job whose config is *also* run
  standalone in the same pass — the pair must agree within the solo replicate spread
  (the RIGOR-AUDIT §2b check, run continuously instead of once).
- **change:** `mill/screen.py`: caravan launcher for process-mode batches (children are
  ordinary train.py invocations with an inherited-memmap flag added to train.py);
  ledger lines record `caravan: <id>` and the parity pair's two readings. This is a
  measurement protocol around unchanged train.py runs — not the compute department's
  queue (no priorities, no leasing; screen.py's existing order is untouched).
- **payoff:** if startup+setup measures at ~10 s (estimate, to be replaced by
  probe_startup.py's medians), a caravan of 8 saves 7 × 10 s = 70 s per 8 process
  probes ≈ **12% on the process-mode share** — worth ≈25–30 min per full pass if
  process mode is ~half the pool. If the measured startup is <3 s, the entry retires
  itself: the payoff formula is printed with the entry so the decision is arithmetic.
- **validity risk:** a fork-inherited memmap is shared state a standalone run never
  has; a child that accidentally wrote through it would contaminate its siblings.
  Guard: the memmap is opened read-only (`mode="r"`, as train.py already does), the
  per-job held_init invariant catches construction drift before it can become a
  verdict, and the continuous parity job means any systematic caravan effect shows up
  as a parity failure within one pass — at which point caravan verdicts from that pass
  are voided and re-run standalone, ledgered as such.

---

## Ranking note

G-061–G-063 attack the funnel's shape (stage cost, seed spend, trial spend) and carry
the largest measured savings; G-064–G-065 make the cheap stages physically possible
and safe; G-066–G-067 stop paying full price for families whose members share most of
their information; G-068–G-072 each remove one named, measured tax (machine weather,
context price, calibration rot, held-set spend, startup) with a guard that can retire
the entry on its own numbers. Biggest single measured saving: **G-063's guard-dead
stop — 8 min per affected trial at zero information loss**, with G-062's ≈8–9
trial-hours per generation the largest expected aggregate.

---

## Appendix — working-id mapping (miners -> wave G)

- CP-001 -> G-001
- CP-002 -> G-002
- CP-003 -> G-003
- CP-004 -> G-004
- CP-005 -> G-005
- CP-006 -> G-006
- CP-007 -> G-007
- CP-008 -> G-008
- CP-009 -> G-009
- CP-010 -> G-010
- CP-011 -> G-011
- CP-012 -> G-012
- DC-001 -> G-013
- DC-002 -> G-014
- DC-003 -> G-015
- DC-004 -> G-016
- DC-005 -> G-017
- DC-006 -> G-018
- DC-007 -> G-019
- DC-008 -> G-020
- DC-009 -> G-021
- DC-010 -> G-022
- DC-011 -> G-023
- DC-012 -> G-024
- RO-001 -> G-025
- RO-002 -> G-026
- RO-003 -> G-027
- RO-004 -> G-028
- RO-005 -> G-029
- RO-006 -> G-030
- RO-007 -> G-031
- RO-008 -> G-032
- RO-009 -> G-033
- RO-010 -> G-034
- RO-011 -> G-035
- RO-012 -> G-036
- MM-001 -> G-037
- MM-002 -> G-038
- MM-003 -> G-039
- MM-004 -> G-040
- MM-005 -> G-041
- MM-006 -> G-042
- MM-007 -> G-043
- MM-008 -> G-044
- MM-009 -> G-045
- MM-010 -> G-046
- MM-011 -> G-047
- MM-012 -> G-048
- MC-001 -> G-049
- MC-002 -> G-050
- MC-003 -> G-051
- MC-004 -> G-052
- MC-005 -> G-053
- MC-006 -> G-054
- MC-007 -> G-055
- MC-008 -> G-056
- MC-009 -> G-057
- MC-010 -> G-058
- MC-011 -> G-059
- MC-012 -> G-060
- TH-001 -> G-061
- TH-002 -> G-062
- TH-003 -> G-063
- TH-004 -> G-064
- TH-005 -> G-065
- TH-006 -> G-066
- TH-007 -> G-067
- TH-008 -> G-068
- TH-009 -> G-069
- TH-010 -> G-070
- TH-011 -> G-071
- TH-012 -> G-072
