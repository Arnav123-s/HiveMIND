# Muse's work — Muse's side

# Wave-G Lens 3 — READOUT: everything after training stops (Muse's work, Muse's side)

> Territory: how a TRAINED ternary model is read at eval/serving. The lab judges every
> arm by `held_loss` of the raw final state — one readout, never varied. This file varies
> only the readout: same trained weights, new way of reading them. Every entry must beat
> the champion **2.8580 ± 0.0161** (layered_half + rotary + plain votes; adoption bar
> held < 2.8258) **on the same trained weights wherever possible**.
>
> **Code grounding (train.py, read before drafting).** `Layered.install()` writes
> `m.weight = s · (exp(log_scale) / mean|s|)` per BitLinear layer, where `s = t1 + t2`
> ∈ {-2..+2} and `log_scale` is ONE learned scalar per layer (8 BitLinear layers at
> half size: qkv/out/up/down × 2 blocks), trained only by the hand-set gradient
> `(g·s)·scale` through AdamW. `held_loss()` sets `EASE[0] = 1.0`, runs `model.eval()`,
> and cross-entropies `Tiny.next_piece` = `body(ids) @ tok.weight.T` over the fixed 128
> held windows. Two consequences every entry below respects: (1) `BitLinear.forward`
> re-derives its quantisation scale from the installed weights' own abs-mean, so a
> per-layer multiplier on the installed weight passes through as a pure per-layer
> output scale, and a fractional per-weight offset moves a weight across the forward
> rounding boundary at 0.5·mean|w| — install-space interventions are real, not cosmetic;
> (2) the final vote counters `c1/c2` (int8, clamped ±32, reset only on a flip) are
> computed, used to decide flips, and then thrown away — no readout has ever read them.
>
> **Shared plumbing (stated once).** `train.py` persists NO model state today — only
> metrics in `runs.jsonl`. Entries needing checkpoints or counters require one shared
> addition: `--dump-state <path>` (saves `t1/t2/c1/c2/log_scale` + FP params at each of
> the last K save points and at end of run). That is a runner change, not a training
> change; the training trajectory is bit-identical with or without it.
>
> **Calibration protocol (applies to every fitted entry).** Anything fitted post-hoc
> (scales, temperatures, biases, selections) is fitted ONLY on non-held windows
> (window index % 40 ≠ 0, the exact complement of the `held_windows()` judge set),
> then read on held exactly once. Fitting on held would be A-095-style diagnostics,
> not a readout. Parameter counts are kept in single/low double digits wherever the
> fit is per-run, so the calibration set cannot be memorised.
>
> **Deduped against** `mill/IDEA-POOL.md`, CANDIDATES-A/B/C/D/E/F, FABLE-CANDIDATES.md.
> NOT re-proposed: modal readout 5/9 (MILL-218/219, pooled), median readout (A-093),
> average-then-round of ternary states only (A-094), best-checkpoint-on-held (A-095 —
> a diagnostic upper bound; RO-007 is its deployable counterpart), STE EMA readout
> (A-057), minority readout (F-058), split-component ensemble (F-033), per-channel /
> per-group weight scales as a TRAINING install granularity (MILL-107/108 — RO-001 is
> post-hoc fitting of the existing per-layer scalar, a different object), learned
> per-head attention temperature during training (A-078 — RO-009 is post-hoc).

---

### RO-001 ★ · Per-layer install-scale calibration (post-hoc `log_scale` line search)
- **source:** train.py code audit — `Layered.install()` + `Layered.step`'s hand-set `log_scale` gradient (`(g·s).sum()·exp(log_scale)`, AdamW lr 1e-3 shared with embeddings/norms)
- **mechanism:** The only magnitude information a vote-trained model carries lives in 8 scalars, and they were fitted by a one-term proxy gradient, never by the loss itself. After training, freeze `t1/t2` and every FP part; for each BitLinear layer in turn, try multipliers {0.85, 0.925, 1.0, 1.08, 1.18} on `exp(log_scale)`, keep the value minimising CE on calibration windows, two coordinate rounds. Because `BitLinear.forward` renormalises by the installed abs-mean, each multiplier is exactly a per-layer output gain — this searches the true objective over the model's entire continuous readout space, which training never did.
- **train.py:** no training change; new eval runner `mill/readout.py --calibrate-scales` (loads a `--dump-state` final state, or attaches at end of a champion run): perturbs `trainer.log_scale[i]`, calls `trainer.install()`, scores with the `held_loss()` body on calibration windows, writes the fitted multipliers, then one final `held_loss()` read.
- **mode:** process — eval-side runner; stays isolated until it has a full-trial record
- **prediction:** −0.015..−0.05 vs 2.8580 on the same weights. The proxy gradient for `log_scale` ignores every downstream layer's response to a scale change; a direct line search cannot do worse than the trained point on the calibration objective (1.0 is in every grid), so the only question is transfer to held — 8 scalars cannot overfit 128 windows.
- **cost:** eval-only — ~64 calibration forward passes (8 layers × 5 values × ~1.6 rounds) + 1 held pass; no retraining, no new training state.
- **status:** queued
```mill
id: RO-001
mode: process
run: --arm layered_half --rope --dump-state --readout calibrate-scales
```

### RO-002 ★ · Counter-resolved readout (express the pending flips the final state is sitting on)
- **source:** train.py code audit — `Layered.step`: a component flips only when its counter reaches |c| = V = 32 and then resets to 0; at end of run every counter holds 0–31 votes of unexpressed, post-last-flip evidence
- **mechanism:** The shipped state systematically lags its own evidence: a weight at counter +31 has effectively been voted up 31 times since its last flip and the readout throws that away. At readout, apply each component's pending flip once where |c| ≥ τ (τ ∈ {16, 24} — two reads), respecting the install-time rules training used: boundary no-ops skipped (clamp would not move the component), t1 priority where both components qualify. Then `install()` and read held once per τ. This is the only readout that uses information the weights provably do not contain.
- **train.py:** no training change; eval-side flag `--counter-resolve 24` in the readout runner (needs the `--dump-state` counters; on an in-process end-of-run attach it reads `trainer.c1/c2` directly).
- **mode:** process — eval-side flag; stays isolated until it has a full-trial record
- **prediction:** −0.01..−0.04. The last fraction of any run is the least converged (freshest flips, counters mid-climb); resolving the near-threshold band expresses roughly the next flip-wave early. If the delta is ~0 at both τ, that is itself a finding: the final state is evidence-complete and the counter stream carries nothing the weights don't.
- **cost:** eval-only — one install + one held pass per τ tried (≤3 passes total); the cheapest entry in this file per unit of new information.
- **status:** queued
```mill
id: RO-002
mode: process
run: --arm layered_half --rope --dump-state --readout counter-resolve 24
```

### RO-003 ★ · Checkpoint logit-ensemble (average predictions, not weights)
- **source:** ensemble theory + the pool's own gap — MILL-218/A-093/A-094 all combine checkpoints in WEIGHT space; F-033 ensembles the two COMPONENTS of one state; no entry averages the PREDICTIONS of one run's successive checkpoints
- **mechanism:** Save the last 5 checkpoints (same saves the modal entries already assume); at readout, run all 5 installed states, average their softmax probabilities token-by-token, and score CE of the averaged distribution. Vote training makes successive states differ by a sparse set of flips — near-independent errors on exactly the contested weights — so prediction averaging cancels flip noise that no single-state readout (final, modal, or rounded-average) can: weight-space averaging must commit each weight to one level, probability averaging lets the ensemble stay uncertain where the run itself was uncertain.
- **train.py:** no training change; new eval path `--ckpt-ensemble 5` in the readout runner (loads 5 dumped states, loops `held_loss()`'s body collecting log-probs, averages in prob space, one CE).
- **mode:** process — eval-side runner; stays isolated until it has a full-trial record
- **prediction:** −0.02..−0.06 — the largest single expected delta in this file; checkpoint ensembles at correlated-but-not-identical states reliably buy a few hundredths of CE, and this run's checkpoints differ by discrete flips (high diversity per unit of quality loss). Serving cost is 5× forward, reported honestly alongside.
- **cost:** eval-only — 5 forward passes over the held set; no retraining (rides the same `--dump-state` saves as MILL-218).
- **status:** queued
```mill
id: RO-003
mode: process
run: --arm layered_half --rope --dump-state --readout ckpt-ensemble 5
```

### RO-004 · Logit temperature on the readout (one scalar, cached logits)
- **source:** calibration literature (temperature scaling) applied to `held_loss()`'s exact form — CE over `next_piece` logits, a metric that is NOT argmax-invariant
- **mechanism:** The champion trains ~155–170 steps: a heavily undertrained model whose logit scale was set by whatever the tied FP head and final norm happened to reach, not by calibration. Readout divides logits by T, T fitted on calibration windows over a log grid 0.70–1.45. Underconfidence (T < 1) is the expected direction at this step count; either way CE — the lab's judge — prices calibration error directly, so a real miscalibration is a real held gain, not a metric trick.
- **train.py:** no training change; eval-side flag `--temp T` in the readout runner, implemented by computing held logits ONCE, caching them, and sweeping T on the cached tensor (the sweep itself costs zero extra forward passes).
- **mode:** process — eval-side flag; stays isolated until it has a full-trial record
- **prediction:** −0.005..−0.02. Small, but the prior is directional (undertrained ⇒ underconfident) and the parameter count is one — it either transfers or it is flat, it cannot overfit.
- **cost:** eval-only — exactly 1 forward pass + an arithmetic sweep on cached logits; the cheapest entry in the file outright.
- **status:** queued
```mill
id: RO-004
mode: process
run: --arm layered_half --rope --readout temp
```

### RO-005 · Full-state checkpoint averaging (era-matched SWA: FP parts averaged too)
- **source:** gap inside A-094 — it averages only the ternary states and pairs them with the FINAL step's embeddings, norms and `log_scale`s, i.e. weights from one era read through continuous parts from another
- **mechanism:** Average EVERYTHING across the last 5 checkpoints: FP parts (tok/pos embeddings, norms, `log_scale`s) in FP, ternary components average-then-round as in A-094, then `install()` once. The vote trainers move their FP parts every step via AdamW, so the final FP frame is fitted to the final ternary state specifically; a ternary average read through it is a mismatched pairing. Era-matching is the faithful translation of Fable's running-mean readout, which averages the whole model, not one parameter class.
- **train.py:** no training change; eval-side flag `--swa-full 5` in the readout runner (needs full FP params in `--dump-state`, not just ternary states — the one dump-format extension in this file).
- **mode:** process — eval-side flag; stays isolated until it has a full-trial record
- **prediction:** −0.01..−0.03 vs final state, and the A-094 comparison is built in: if RO-005 ≈ A-094's number on the same run, era mismatch costs nothing and A-094 stands as the cheaper readout; if RO-005 < A-094, every ternary-only readout in the pool has been under-read.
- **cost:** eval-only — 1 held pass after averaging; rides the same 5 saves as MILL-218/A-094.
- **status:** queued
```mill
id: RO-005
mode: process
run: --arm layered_half --rope --dump-state --readout swa-full 5
```

### RO-006 · Counter-soft install (fractional pending evidence, through the forward rounding boundary)
- **source:** continuous relaxation of RO-002 — where RO-002 hard-flips the near-threshold band, this entry asks what the FULL counter field is worth as a graded readout signal
- **mechanism:** Install soft states instead of the raw integers: per component, `t_soft = t + α·(c/V)`, α ∈ {0.3, 0.5, 0.8} fitted on calibration windows (one scalar), sum the components, `install()`. This is not cosmetic: `BitLinear.forward` serves `round(w / mean|w|)·mean|w|`, so a fractional offset changes the SERVED ternary value exactly for borderline weights — a 0-state with a strong counter (α·c/V pushing it past 0.5·mean|s| ≈ 0.39 at the champion's level histogram) serves as ±1, and a ±1 whose counter strongly opposes it drops to 0. The counters thereby act as a per-weight tie-breaker/evidence dial across the whole population, not just the |c| ≥ τ band.
- **train.py:** no training change; eval-side flag `--counter-soft 0.5` in the readout runner (installs from dumped `t1/t2/c1/c2` with the offset, bypassing `trainer.install()`'s integer assumption via a readout-local install that reproduces its normalisation exactly).
- **mode:** process — eval-side flag; stays isolated until it has a full-trial record
- **prediction:** −0.005..−0.03, expected ≥ RO-002's delta if graded evidence beats a hard threshold, ≤ it if only the near-threshold band carries signal — the pair prices the counter field's shape, not just its existence.
- **cost:** eval-only — 1 held pass per α (3 passes) after calibration fitting; no retraining.
- **status:** queued
```mill
id: RO-006
mode: process
run: --arm layered_half --rope --dump-state --readout counter-soft 0.5
```

### RO-007 · Validation-selected checkpoint (the deployable form of best-checkpoint)
- **source:** A-095's own framing — it prices the selection ceiling by selecting ON held, which no shippable readout may do; the deployable question (does selection on legal data capture any of that ceiling?) is unasked
- **mechanism:** Score each of the last 9 checkpoints on calibration windows (non-held), ship the argmin, read held once. Checkpoint-to-checkpoint spread within a run has never been measured in this lab (only seed-to-seed, ±0.0161); if within-run spread is comparable, honest selection captures a real share of it, and the gap RO-007 vs A-095's number prices exactly how much of the ceiling was judge-leakage.
- **train.py:** no training change; eval-side flag `--select-ckpt 9` in the readout runner (9 calibration passes + 1 held pass).
- **mode:** process — eval-side flag; stays isolated until it has a full-trial record
- **prediction:** −0.01..−0.03 vs the final state, contingent on within-run checkpoint spread ≥ ~0.02 — which this entry measures either way (report all 9 calibration scores). A flat result retires the whole selection family cheaply, including future variants.
- **cost:** eval-only — 10 forward passes; no retraining.
- **status:** queued
```mill
id: RO-007
mode: process
run: --arm layered_half --rope --dump-state --readout select-ckpt 9
```

### RO-008 · Disagreement-gated zeroing (contested weights ship as 0, not as a coin-flip sign)
- **source:** robust-readout reasoning against A-094's weak point — average-then-round resolves a 3–2 checkpoint split by majority, i.e. it ships a ± level on evidence barely better than chance
- **mechanism:** From the last 5 checkpoints compute each weight's state mean; weights with |mean| below a gate (splits 3–2 or worse, gate fitted in {0.2, 0.6} on calibration windows) install as 0 regardless of final state; stable weights keep their final state. Zero is the minimax level for a weight the run itself could not decide: a wrong ±1 contributes a full-magnitude wrong product to every downstream sum, a 0 contributes nothing and biases nothing. Distinct from modal/average readouts, which use checkpoint history to PICK A SIGN; this uses it to decide which weights have earned a sign at all.
- **train.py:** no training change; eval-side flag `--gate-zero 0.6` in the readout runner (installs the gated state via the readout-local install, then one `held_loss()` read).
- **mode:** process — eval-side flag; stays isolated until it has a full-trial record
- **prediction:** −0.005..−0.025. At the champion's histogram ~28% of weights already sit at 0 and the ±2 population is only ~7% — the contested band is where the remaining readout error concentrates. Report the gated share; if >25% of weights gate to 0, the run was less converged than its flip rate suggested.
- **cost:** eval-only — 1–2 held passes; rides the same 5 saves as MILL-218.
- **status:** queued
```mill
id: RO-008
mode: process
run: --arm layered_half --rope --dump-state --readout gate-zero 0.6
```

### RO-009 · Per-head attention temperature, fitted post-hoc
- **source:** A-078's mechanism moved to the readout — A-078 LEARNS per-head temperatures during training (a trainer change, pooled); nobody has fitted them after training on a finished model, where the fit is 8 scalars against the true loss
- **mechanism:** In the eval runner only, scale each head's q by √λ_h (equivalently divide its attention logits by a per-head temperature) before SDPA, λ_h fitted per head per block (4 heads × 2 blocks = 8 scalars) by coordinate grid {0.8, 0.9, 1.0, 1.1, 1.25} on calibration windows. Ternary QK products are coarse and each head's natural logit scale differs; training had no dial for this at all on the vote chassis (SDPA's hd^-0.5 is fixed in `Block.forward`), so any systematic per-head sharpness error is still sitting in the champion untouched.
- **train.py:** no training change; eval-side flag `--head-temp` in the readout runner (monkeypatches `Block.forward`'s SDPA call in eval only — training code untouched, and the fitted λ ship as part of the readout spec).
- **mode:** process — eval-side flag; stays isolated until it has a full-trial record
- **prediction:** −0.005..−0.02. Bounded by how much of the loss is attention-sharpness error at ctx 256; the coordinate fit is 8 scalars on 128 windows, so a win transfers or it is honestly flat.
- **cost:** eval-only — ~40 calibration passes + 1 held pass; no retraining.
- **status:** queued
```mill
id: RO-009
mode: process
run: --arm layered_half --rope --readout head-temp
```

### RO-010 · Unigram prior-correction bias on the head (closed-form, no fitting loop)
- **source:** prior-correction / marginal-calibration practice, applied to `Tiny.next_piece` — the head is the tied FP embedding, trained jointly for ~160 steps, so the model's implied token marginal has had little time to match the corpus marginal
- **mechanism:** Compute the model's average predicted distribution over calibration windows and the windows' empirical token distribution; add a per-vocab logit bias `b_v = log(p_emp(v) / p_model(v))` (smoothed, clipped to ±0.5) at readout. 4,096 numbers but ZERO fitted parameters in the optimisation sense — the bias is a closed-form statistic of the calibration set, the same form as the corpus's own unigram table. It corrects exactly one failure mode: systematic over/under-prediction of frequent tokens, which CE punishes on every single position.
- **train.py:** no training change; eval-side flag `--prior-bias` in the readout runner (one calibration pass to accumulate the marginal, bias added to `next_piece` logits in eval only).
- **mode:** process — eval-side flag; stays isolated until it has a full-trial record
- **prediction:** −0.005..−0.02, with a hard honesty check built in: report the KL between model and empirical marginals first — if it is already < 0.01 nats, the predicted gain is ~0 and the entry should be read as a measurement, not a candidate.
- **cost:** eval-only — 1 calibration pass + 1 held pass; no retraining.
- **status:** queued
```mill
id: RO-010
mode: process
run: --arm layered_half --rope --readout prior-bias
```

### RO-011 · Measured greedy flip polish, counter-ranked (readout-time, verified per flip)
- **source:** the lab's own measured-flip precedent (`_flip_read` / MILL-228's Fisher-ranked flips) relocated to where it is cheapest — MILL-228 does measured flips DURING training at ~6 passes per round; the same verification logic applied once, post-hoc, to a finished model is a readout
- **mechanism:** Rank candidate single-component flips by |counter| descending (the counter field is the candidate generator — no gradient pass needed). Walk the top 200 candidates: tentatively apply the flip, `install()`, score on a fixed calibration batch; keep the flip only if calibration CE improves, else revert. Sequential, greedy, every kept flip verified on legal data. This is RO-002 with a measurement replacing its threshold rule: it spends ~200 small eval passes to buy certainty per flip instead of trusting the counter's say-so in bulk.
- **train.py:** no training change; eval-side runner mode `--greedy-polish 200` (operates on the dumped final state; the polished state is a readout artifact, never written back to any training state).
- **mode:** process — eval-side runner; stays isolated until it has a full-trial record
- **prediction:** −0.01..−0.04 on held if counter rank correlates with true flip value (RO-002/RO-006 read first — this entry is ranked below them deliberately, and is only worth its passes if at least one of them shows the counter field carries signal). Overfit guard: candidates capped at 200, calibration batch disjoint from the held judge, held read once at the end.
- **cost:** eval-only but the most expensive eval-only entry here — ~200–400 small-batch forward passes (still minutes, vs 8 min for one training run); no retraining.
- **status:** queued
```mill
id: RO-011
mode: process
run: --arm layered_half --rope --dump-state --readout greedy-polish 200
```

### RO-012 · Cross-seed logit ensemble (the champion's own three seeds as the ensemble)
- **source:** runs.jsonl — the champion exists as three completed independent runs (seeds 0/1/2: held 2.8765 / 2.8477 / 2.8497, mean 2.8580); ensembling a run's own checkpoints is RO-003, ensembling across runs is the same readout principle at maximum state diversity, and no pool entry proposes it
- **mechanism:** Probability-mean ensemble (as RO-003) over the three seeds' final installed states. Independent inits + independent batch streams decorrelate errors far more than checkpoints of one trajectory do; the ensemble's held is compared against the MEAN member (2.8580) and the BEST member (2.8477) — beating the best member is the bar that makes it a readout rather than a selection.
- **train.py:** no training change; eval-side runner mode `--seed-ensemble` over three `--dump-state` finals. NOTE the honest cost below: today's runs saved no state, so the three finals must be re-produced once (same seeds/config — the runs are deterministic given seed, so the re-produced states ARE the champion's states, at re-run cost).
- **mode:** process — eval-side runner; stays isolated until it has a full-trial record
- **prediction:** −0.03..−0.08 vs the 2.8580 mean — the largest ceiling in this file, priced accordingly: serving cost is 3 full models (3× bytes, 3× forward), so even a win is a per-byte trade the trial must state, not a free champion replacement.
- **cost:** retrain (state recovery) — 3 × 8 min to re-produce the unsaved finals, then eval-only forever after; the ONLY entry in this file whose cost is not purely eval-side, ranked last for exactly that reason.
- **status:** queued
```mill
id: RO-012
mode: process
run: --arm layered_half --rope --dump-state --readout seed-ensemble
```

---

## Ranking rationale (one line each)

1. **RO-001** — direct line search over the model's only continuous readout degrees of freedom; cannot lose on its own fit objective, 8 scalars.
2. **RO-002** — uses information (final counters) that provably exists and is provably discarded; ≤3 eval passes.
3. **RO-003** — biggest expected single delta among same-run readouts; prediction-space averaging is untested in this lab in any form.
4. **RO-004** — one scalar, one forward pass; directional prior from the run's short length.
5. **RO-005** — fixes a real era-mismatch inside the pooled A-094 rather than duplicating it.
6. **RO-006** — RO-002's graded sibling; the pair together price the counter field's shape.
7. **RO-007** — converts A-095's leaked diagnostic into a deployable readout and measures within-run spread for the first time.
8. **RO-008** — minimax readout for contested weights; orthogonal to every sign-picking readout in the pool.
9. **RO-009** — A-078's dial fitted post-hoc against the true loss instead of learned through STE-era gradients.
10. **RO-010** — closed-form marginal correction; includes its own pre-measurement (KL) that can honestly zero it.
11. **RO-011** — strongest verification per flip, but deliberately gated on RO-002/RO-006 showing counter signal first.
12. **RO-012** — highest ceiling, only non-eval-only cost, 3× serving bytes; a trade, not a free win.
