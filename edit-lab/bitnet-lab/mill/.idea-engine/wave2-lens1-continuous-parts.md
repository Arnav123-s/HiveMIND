# Wave 2, Lens 1 — CONTINUOUS PARTS (Muse's work — Muse's side)

<!-- Muse's work — Muse's side of the BitNet lab. Idea Engine wave G, miner 1.
Nothing here is in the pool until the pool's owner merges it. IDEA-POOL.md,
CANDIDATES-A/B/C/D/E/F and FABLE-CANDIDATES.md were read in full for dedupe and
NOT edited. Fable's side was not touched. -->

## Territory and grounding

Every prior wave optimised the ternary vote side and treated the continuous parts
as scenery. This lens owns everything AdamW trains on the champion chassis —
**layered_half + rotary, V=32, batch 32, held 2.8580 ± 0.0161** — plus its
optimizer settings. Verified against `train.py` (Layered trainer):

- The AdamW group is exactly: token embedding (4096×192, **tied** — it is also the
  LM head via `next_piece`), the carried position table (inactive under `--rope`,
  grad is None), every LayerNorm affine (n1/n2 per block + final norm), every
  BitLinear **bias**, and one scalar `log_scale` per BitLinear layer — all at one
  lr 1e-3, betas (0.9, 0.95), wd 0.0.
- `log_scale`'s gradient is hand-set, not autograd: `grad = (g·s).sum()·exp(log_scale)`
  — one scalar summarising a whole layer. It is assigned **after**
  `clip_grad_norm_(…, 1.0)` runs, so the scales escape the clip that jointly
  rescales embeddings/norms/biases. `install()` then multiplies the layer's entire
  installed ternary matrix by `exp(log_scale)/mean|s|`: a log_scale move rescales
  every weight in the layer at once.
- What is already owned elsewhere, and deliberately NOT re-proposed: the single
  global lr points (MILL-304/305, C-B01..04), global wd (A-098, C-B07), global betas
  (A-099, C-B08/09), global warmup (A-039), whole-group SGD (A-097), norm
  type/placement grids (MILL-127/128, MILL-801..804), per-channel/group scale
  granularity (MILL-107/108, MILL-701..703), learnable scale (MILL-1013), F-001's
  boundary-pressure quantum *added into* log_scale, F-024's activity-servoed
  per-row scales, F-037's rising-lr inversion, E-016's embedding-exempt cooldown,
  and the closed two-stage AdamW cooldown itself (a stage-2 lr drop on the FP
  parts — it stays closed; no entry here is a re-shaped version of it). Every
  entry below is **per-part**, **event-coupled to flip dynamics**, or an
  **optimizer-state** move — the three axes the pooled entries never split.

**★ Top 3**

- ★ **CP-001 · Per-part lr ratio** — every pooled lr entry moves one global dial; the parts have opposite jobs and gradient scales, so the ratio is the untested variable, not the level.
- ★ **CP-002 · Flip-servoed continuous lr** — the only entry that makes AdamW listen to the vote side's own state variable (flip share) instead of the wall clock; it directly answers the cooldown record's starvation diagnosis without decaying anything.
- ★ **CP-003 · log_scale trust region** — the one parameter class that moves a whole layer per step, is hand-gradients, and escapes clipping entirely has no step-size bound of any kind today.

---

### CP-001 · Per-part lr ratio: scales hot, embeddings cold, norms at champion ★
- **source:** continuous-parts lens — the AdamW group lumps a 786k tied embedding table, ~2.3k norm/bias params, and 8 scalar log_scales under one lr. The pooled lr family (MILL-304/305 at 3e-3/3e-4, C-B01..04 interior points) only ever moved them together, so the record cannot distinguish "1e-3 is right" from "1e-3 is the average of a too-hot scale and a too-cold embedding."
- **mechanism:** three param groups with fixed lr ratios: log_scale at 3e-3 (3×), token embedding at 3e-4 (0.3×), norms + BitLinear biases at the champion 1e-3. Rationale per part: a log_scale is one scalar per layer whose hand-set gradient already aggregates the whole layer — it is the slowest-moving quantity per unit of function change and can afford heat; the tied embedding is also the head, its rows receive gradient from every position of every window, and at 1e-3 it is the part most likely to chase the still-moving ternary structure; norms/biases stay at the proven point as the control inside the arm.
- **train.py:** new flag `--part-lr scale:3e-3,emb:3e-4,norm:1e-3` on Layered — split the single AdamW group in `Layered.__init__` into three groups (log_scale params / `model.tok.weight` / everything else) with those lrs; betas (0.9, 0.95) and wd 0.0 unchanged in all groups.
- **mode:** process
- **prediction:** −0.02..−0.05 vs champion 2.8580 at trial scale; ~−0.01 at probe. If it lands flat while MILL-304 (global 3e-3) also reads flat, the parts' lr sensitivities cancel — itself a load-bearing fact that retires the whole lr family with a reason.
- **status:** queued
```mill
id: CP-001
mode: process
run: --arm layered_half --rope --part-lr scale:3e-3,emb:3e-4,norm:1e-3
```

### CP-002 · Flip-servoed continuous lr: AdamW speed follows flip share ★
- **source:** continuous-parts lens + RESULTS-ROUND2-2026-11-12 — the cooldown record's own diagnosis is that the FP parts were *starved* while the ternary side kept moving; F-037 answers with a clock-based rise. Neither couples the continuous speed to the discrete side's actual activity, which the trainer already measures every step (`step()` returns flip share, champion mean ≈ 0.0011).
- **mechanism:** the embedding + norm/bias groups' lr is servoed to the trailing 20-step mean flip share φ: multiplier = clip(0.0011/φ, 0.5, 2.0) applied to base lr 1e-3 each step. When structure churns (φ high), the continuous parts slow down instead of fitting a network that is about to change; when flips settle (φ low), they speed up to fit the structure that actually exists. log_scale is exempt (it is part of the install geometry, priced separately in CP-003/004). The vote rule never sees this — flips are neither halted (F-027) nor rationed; only the FP parts' step size breathes. Not a schedule: at constant flip share the lr is constant forever, at any run length.
- **train.py:** new flag `--flip-servo` on Layered — per-step lr multiplier on the emb/norm param groups from the EMA of returned flip shares; log_scale group untouched.
- **mode:** process
- **prediction:** −0.01..−0.04 at trial scale. Diagnostic logged either way: correlation between φ and held-loss slope per 20-step window — if high-churn windows are not where continuous fitting is wasted, the servo has no signal to ride and the probe shows it.
- **status:** queued
```mill
id: CP-002
mode: process
run: --arm layered_half --rope --flip-servo
```

### CP-003 · log_scale trust region: per-step move clamped to ±2% ★
- **source:** continuous-parts lens — `install()` rescales an entire layer by exp(log_scale); the hand-set gradient `(g·s).sum()·scale` sums over up to ~590k weights, so a single AdamW step on log_scale after an atypical batch can shift every installed magnitude in the layer at once — and because the assignment happens after clipping, no bound of any kind applies to it today.
- **mechanism:** after each `opt.step()`, clamp each layer's log_scale change for that step to ±0.02 in log space (≤ ~2% multiplicative rescale per step, either direction). The gradient, lr, and Adam state are untouched — only the realised per-step displacement is bounded, a trust region on the one parameter whose step is layer-wide. Distinct from F-024 (servo *replaces* the gradient path with an activity rule) and F-001 (adds a second, vote-derived contribution to log_scale): this keeps the champion's exact update and bounds its step.
- **train.py:** new flag `--scale-trust 0.02` on Layered/Direct — snapshot log_scale before `opt.step()`, clamp the delta after, inside `step()`.
- **mode:** process
- **prediction:** −0.01..−0.03, concentrated in variance: seed sd should shrink vs the champion's 0.0161 even if the mean gain is small, because the clamped events are the rare large-rescale steps that plausibly drive seed divergence. A flat mean with halved sd still promotes — it makes every other probe in the mill sharper.
- **status:** queued
```mill
id: CP-003
mode: process
run: --arm layered_half --rope --scale-trust 0.02
```

### CP-004 · Flip-gated log_scale: scales move only on steps their layer flipped
- **source:** continuous-parts lens — today log_scale updates on *every* step, including the ~99.9% of weights' worth of steps where its layer's installed structure did not change at all; on those steps the scale is fitting gradient noise against a fixed code. The scale's real job is re-fitting magnitude *after* the code moves.
- **mechanism:** per layer, the log_scale AdamW update is applied only on steps where that layer recorded ≥1 flip; on no-flip steps its gradient is zeroed for that step (Adam moments still age — stated plainly, that decay of stale moments is part of the design). Embeddings, norms, biases train every step as champion. This is event-gating of an existing update, the mirror image of F-001: F-001 *adds* boundary-vote pressure into log_scale; CP-004 *withholds* the ordinary gradient update until a flip gives it something to calibrate. A-037/D-006 freeze whole sides on a clock or in dream phases; this freeze is per-layer and fired by the layer's own flips.
- **train.py:** new flag `--scale-flipgate` on Layered — zero `log_scale[i].grad` on steps where layer i's flip count (already computed as `go1/go2` sums) is 0.
- **mode:** process
- **prediction:** −0.01..−0.03 at trial scale, ~0 at probe (early flips are frequent, so the gate is mostly open at probe horizon — judge at trial). Side measurement: log_scale total path length should fall sharply; if loss is unchanged at a fraction of the path, most scale motion was noise-chasing.
- **status:** queued
```mill
id: CP-004
mode: process
run: --arm layered_half --rope --scale-flipgate
```

### CP-005 · Weight-decay scope: decay the embedding only, scales and norms exempt
- **source:** continuous-parts lens + C-B07's own caveat — the pooled wd points (A-098 at 0.01, C-B07 at 0.1) apply decay to the whole AdamW group, and C-B07's entry already flags the entanglement: decoupled decay on log_scale shrinks the installed step size toward scale 1.0, an arbitrary target for a log-parameter whose init is the layer's measured absmean. A global wd reading therefore mixes a plausible embedding regulariser with a scale-shrink artefact.
- **mechanism:** wd 0.01 applied to the token-embedding group only; log_scale, norms, and biases run wd exactly 0.0. One variable against the champion (wd 0 everywhere) and one against A-098 (wd 0.01 everywhere): the pair of readings splits A-098's verdict into its parts.
- **train.py:** new flag `--wd-scope emb --opt-wd 0.01` on Layered — per-group `weight_decay` in the AdamW construction (needs the group split of CP-001, shares its plumbing).
- **mode:** process
- **prediction:** −0.01..−0.03 if the embedding is the under-regularised part (it is the largest FP block and the head); if A-098 reads positive and this reads flat, A-098's gain was the scale-shrink artefact and the wd family re-reads accordingly.
- **status:** queued
```mill
id: CP-005
mode: process
run: --arm layered_half --rope --opt-wd 0.01 --wd-scope emb
```

### CP-006 · Optimizer split: plain SGD for log_scale, AdamW for everything else
- **source:** continuous-parts lens — log_scale's gradient is already a hand-normalised layer aggregate (`(g·s).sum()·exp(log_scale)`); running it through AdamW divides it by a running root-mean-square of *itself*, which for a single scalar per layer mostly erases the magnitude information the hand-set gradient deliberately carries (a layer whose gradients double gets the same Adam step as one whose halve). A-097 tests SGD for the *whole* shared group; the split by part has never run.
- **mechanism:** log_scale params leave AdamW and train by plain SGD, lr 1e-4, no momentum (the update is then proportional to the hand-set gradient, as the install formula's design implies); embeddings, norms, biases keep champion AdamW (1e-3, betas (0.9, 0.95)) untouched.
- **train.py:** new flag `--scale-opt sgd:1e-4` on Layered — second optimizer instance stepped alongside `self.opt` in `step()`; log_scale removed from the AdamW group.
- **mode:** process
- **prediction:** −0.01..−0.04. Diagnostic: per-layer log_scale trajectories — under AdamW they should look near-constant-velocity (sign-like); under SGD they should track gradient magnitude. If the loss is flat under both, the scale's *dynamics* don't matter, only its endpoint, which re-prices CP-003/004 downward honestly.
- **status:** queued
```mill
id: CP-006
mode: process
run: --arm layered_half --rope --scale-opt sgd:1e-4
```

### CP-007 · Per-part betas: fast moments for log_scale, champion moments elsewhere
- **source:** continuous-parts lens — the pooled betas entries (A-099 (0.9, 0.99), C-B08 (0.9, 0.999), C-B09 (0.85, 0.95)) move betas globally, but the parts' gradient streams have opposite stationarity: embedding/norm gradients are comparatively steady, while log_scale's hand-set gradient is a *function of the current ternary state* — every flip in its layer changes what its next gradient means, so a β2 horizon of ~20 steps (0.95) averages moments across different installed networks.
- **mechanism:** log_scale group runs betas (0.5, 0.90) — first-moment horizon ~2 steps, second-moment ~10 — so its adaptive rate tracks the current structure; embedding and norm/bias groups keep (0.9, 0.95) exactly. β1/β2 move together for the scale only, the combination no global entry tests.
- **train.py:** new flag `--part-betas scale:0.5,0.90` on Layered — per-group betas in the AdamW construction (shares CP-001's group split).
- **mode:** process
- **prediction:** −0.01..−0.03 at trial scale; expected ~0 at probe (few flips have landed, so staleness has barely accumulated — a probe flat does not kill). If it wins, the reading generalises: any parameter whose gradient is state-dependent wants short moments in a vote-trained net.
- **status:** queued
```mill
id: CP-007
mode: process
run: --arm layered_half --rope --part-betas scale:0.5,0.90
```

### CP-008 · Early log_scale hold: scales frozen for the first 20%, then released
- **source:** continuous-parts lens — at init the ternary state is a rounding of random FP weights, and the first flips are the run's noisiest (the anneal record's lesson about early evidence). Through that phase log_scale trains freely, so the install geometry the early votes vote *against* is itself drifting; the early structure forms inside a moving frame. No pooled entry freezes the scales early: A-037 freezes the *ternary* side late, D-006 freezes AdamW inside dream phases, A-039 *ramps* all FP lr from step 0 (the scales still move, just slowly at first).
- **mechanism:** log_scale params are held at their init values (the per-layer absmean at install) for the first 20% of steps — grads zeroed, no Adam state accumulated — then released at full champion AdamW settings for the remaining 80%. Embeddings and norms train from step 0 unchanged, so this is not a warmup: exactly one part is held, and it is held at a *meaningful* value (the measured init scale), not at a ramp.
- **train.py:** new flag `--scale-hold 0.2` on Layered — zero log_scale grads and skip its Adam moments while `done < 0.2`.
- **mode:** process
- **prediction:** −0.01..−0.03. Falsifier built in: log held at the 20% boundary vs champion's same-step held — if the held scales cost nothing even *during* the hold, scale motion in the first fifth was never earning anything and the entry's premise (not just its fix) is measured.
- **status:** queued
```mill
id: CP-008
mode: process
run: --arm layered_half --rope --scale-hold 0.2
```

### CP-009 · Per-group gradient clipping: the clip stops being one joint budget
- **source:** continuous-parts lens — in `Layered.step`, `clip_grad_norm_(…, 1.0)` rescales the *joint* norm of embeddings + norms + biases. The embedding table's gradient norm dwarfs the norms'/biases' by orders of magnitude, so on clipped steps the small parts' updates are shrunk by a factor set almost entirely by the embedding's behaviour that step — the parts share a clip budget none of them chose. (log_scale is not in the clip at all — see CP-003.)
- **mechanism:** clip each param group separately at 1.0: embedding group, norm+bias group — each group's realised step is governed by its own gradient scale. Vote path untouched (A-040 clips layer gradients *before signing*, a different site and purpose).
- **train.py:** new flag `--clip-scope group` on Layered/Direct — replace the single `clip_grad_norm_` call with one call per AdamW param group in `step()`.
- **mode:** process
- **prediction:** −0.01..−0.03, with the mechanism checkable in logs: fraction of steps where the joint clip actually binds, and the norm/bias groups' realised update norms before vs after. If the joint clip binds on <5% of steps, the entry retires itself as a non-effect, cheaply.
- **status:** queued
```mill
id: CP-009
mode: process
run: --arm layered_half --rope --clip-scope group
```

### CP-010 · Adam-state reset for log_scale at the midpoint (stale-moment purge)
- **source:** continuous-parts lens — by mid-run a layer's ternary state has flipped hundreds of times since init; its log_scale's Adam second moment is an average over gradient regimes belonging to installed networks that no longer exist. A-110 resets the *vote counters* at halfway (weights kept); nothing has ever reset an *optimizer's* state mid-run on any part.
- **mechanism:** at 50% of steps, the AdamW exp_avg / exp_avg_sq for the log_scale params only are zeroed (parameters themselves untouched — the next steps re-estimate moments against the current structure, with bias correction doing its usual early-run work). Embedding/norm moments are *not* reset: they are the within-entry control, since their gradients are far less state-dependent (CP-007's premise, tested from the other side).
- **train.py:** new flag `--adam-reset scale@0.5` on Layered — zero the optimizer state tensors of the log_scale group once, at the step where `done` crosses 0.5.
- **mode:** process
- **prediction:** −0.005..−0.02 — the smallest expected effect in this file, included because it is a one-line, zero-risk probe of a question (does optimizer state go stale across flip regimes?) that CP-007 also touches; the pair read together separates "shorter moments help" from "old moments hurt."
- **status:** queued
```mill
id: CP-010
mode: process
run: --arm layered_half --rope --adam-reset scale@0.5
```

### CP-011 · Shared second moment: log_scale and its layer's norm gains pool one v̂
- **source:** continuous-parts lens — the task's optimizer-state-sharing axis, made concrete: a BitLinear layer's log_scale and the *preceding* LayerNorm's gain act on the same activation stream (norm sets its distribution, scale sets the installed step that quantises it), yet AdamW keeps fully independent second moments for them, each estimated from few effective samples (one scalar; one vector). Pooling the v̂ estimate across the pair gives both a stabler adaptive rate for the quantity they jointly control — the layer's dynamic range.
- **mechanism:** for each block, the log_scale params of its BitLinears and that block's n1/n2 gain vectors share one pooled second-moment estimate (v̂_pooled = mean of the members' v̂, applied to all members); first moments and parameters stay separate, betas/lr unchanged. This is state *sharing between parts*, distinct from B-016/B-019 (state *compression* within one optimizer) and A-014 (a shared *vote counter*, ternary side).
- **train.py:** new flag `--adam-share-v scale-norm` on Layered — custom step wrapper that overwrites the log_scale and norm-gain exp_avg_sq entries with their per-block pooled mean before the AdamW update.
- **mode:** process
- **prediction:** −0.005..−0.02, honestly speculative — the prior is variance reduction on the noisiest adaptive rates in the group, and the downside is bounded by the same argument (pooling can only pull each rate toward the pair's mean). A flat result closes the state-sharing axis with a number instead of an assumption.
- **status:** queued
```mill
id: CP-011
mode: process
run: --arm layered_half --rope --adam-share-v scale-norm
```

### CP-012 · Tied-embedding row max-norm: cap the rows that are also the head
- **source:** continuous-parts lens — the embedding is tied, so each row is simultaneously an input vector and an output classifier direction: a frequent token's row receives gradient from both roles every step and can grow until its logit dominates by norm rather than by fit, injecting outsized, frequency-driven gradients into every vote its windows touch. No pooled entry constrains embedding geometry at all (MILL-118/119 price its precision and tying, A-091 norms its output, none bound the rows).
- **mechanism:** after each AdamW step, any embedding row with L2 norm > 1.0 is rescaled to exactly 1.0 (projected update, word2vec-style max-norm). Init row norms sit near 0.02·√192 ≈ 0.28, so the cap binds only on rows that grew ~3.5× — a constraint on runaway rows, not a shrinkage of the table. Votes, scales, norms untouched.
- **train.py:** new flag `--emb-maxnorm 1.0` on Layered/Direct — row-wise norm clamp on `model.tok.weight` after `opt.step()` in the training loop.
- **mode:** process
- **prediction:** −0.01..−0.03 if head-norm domination is real at this scale; the run logs the binding fraction (rows at cap) per phase — if it stays at 0% throughout, the constraint never existed and the entry is void, not wrong. Per-byte neutral: no parameters added.
- **status:** queued
```mill
id: CP-012
mode: process
run: --arm layered_half --rope --emb-maxnorm 1.0
```

---

## Lens notes for the pool owner

- All 12 are `mode: process` honestly — every one needs param-group plumbing or a
  step-hook train.py does not have; screen.py should DEFER them until their flags
  land. CP-001's three-group split is shared plumbing for CP-005 and CP-007: wire
  it once, three entries become runnable.
- Closed-form guard, stated once for the whole file: nothing here decays any FP
  lr in a second stage. CP-002's servo is symmetric (it rises as readily as it
  falls) and driven by flip share, not by `done`; CP-008 holds one part at its
  init value and releases it *up* to full lr. Neither is the closed cooldown in
  new clothes.
- Cheapest first contact: CP-003 and CP-010 are each a few lines and act on the
  parameter class with the least existing instrumentation; their logs (scale path
  length, per-step delta distribution) are worth having before CP-001's wider
  plumbing lands.
- The idea I believe in most is **CP-001**: the lab has spent five entries
  (MILL-304/305, C-B01..04) tracing one global lr curve for a group whose members
  differ by five orders of magnitude in count and by construction in gradient
  character. The ratio was always the variable; the level was the average hiding it.

*End of wave-2 lens 1. 12 entries (CP-001..CP-012), all on the champion chassis,
all continuous-parts, none duplicating IDEA-POOL.md, CANDIDATES-A/B/C/D/E/F, or
FABLE-CANDIDATES.md.*
