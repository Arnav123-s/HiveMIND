# Muse's work — Muse's side

# Wave 4 · Lens 3 — LONG-HORIZON mechanisms (Idea Engine, rotation 4, miner 3)

<!-- Muse's work — Muse's side of the BitNet lab. Nothing here is in the pool until
the pool's owner merges it. IDEA-POOL.md was NOT edited. -->

## Premise

The lab's trials are 8 min / ~160 steps. Almost every filed entry is horizon-blind:
it assumes the trainer state distribution at step 160 is the distribution the
mechanism will live in. It is not. At 1,600–16,000 steps (10–100×) new populations
exist that a 160-step run cannot contain: counters thousands of steps old, a
saturated-counter majority, a zero fraction that has had time to drift, early-flip
cohorts that have shaped thousands of later gradients, Adam moments for rows not
seen in thousands of steps, scales that have random-walked far from their anchor.

Every entry below therefore carries two extra fields no earlier wave required:
**horizon of onset** (where the effect switches on — all ≥ ~800 steps, i.e. ≥5×
the trial) and a **short-horizon proxy** — a cheap measurement inside a normal
160-step budget whose reading predicts the long-horizon effect, because the mill
cannot spend 100× trials on spec. The proxy is the entry's probe; the full-form
prediction is what the proxy is a proxy *for*.

**Dedupe (mandatory pass, done in full):** read IDEA-POOL.md, CANDIDATES-A/B/C/D/
E/F/G/H, FABLE-CANDIDATES.md. Explicitly NOT re-proposed: the whole D-wave dreaming
family (D-001..D-007 — LH-004 uses fresh windows only, no replay buffer, no dream
content), anything F-031-adjacent (JEPA in any role), always-on leak (MILL-209..213
— LH-009 is leak with a delayed *onset*, a different claim), single counter reset
(A-110), cyclic V (A-033), tail freeze (A-022), per-step scale trust region (G-003),
frustration census (WH-051 — LH-002 counts *all* clamped counters, not only
boundary-blocked ones, and acts on width, not readout), counter-validity AUC
(WH-052), F-025's stalled-threshold erosion (LH-006 is its opposite sign, on a
different variable: survival time, not stall time), F-023 importance consolidation
(gradient-energy, not survival), F-043 (V vs model size N — LH-012 is V vs
*training progress* at fixed N), E-013/E-014 (level population at 40 min — LH-003
is the zero level specifically, over 10–100× horizons, with a servo, not a census).
Nothing closed is re-opened: overshoot carry, AdamW cooldown, anneal 8→64,
magnitude votes as specified, JEPA objective.

**Chassis / bars** as in waves F–H: layered_half + rotary, V=32, champion held
2.8580 ± 0.0161. "Full form" below means 3 seeds × 1,600 steps minimum, judged at
equal steps; 16,000-step claims are stated as extrapolations of the 1,600-step form.

---

### LH-001 ★ · Stale-bank purge: counters outlive the model that earned them
- **source:** long-horizon lens — a counter is evidence integrated under past installed states. A weight that last flipped at step 100 and sits at c=+28 at step 5,000 holds a bank earned against a network that has since flipped thousands of other weights. At 160 steps the oldest possible bank is 160 steps old and the landscape has barely moved, so staleness is structurally invisible to every trial the lab has run.
- **mechanism:** Near-threshold counters (|c| ≥ 16) whose sign no longer matches the current gradient consensus are *stale-signed*: when they finally cross, they flip the weight the way the old model wanted, not the way the current one does. Their share of the near-threshold population grows with run length because banks accumulate faster than they resolve. A periodic purge — revalidate the near-threshold bank against fresh batches and zero the counters that fail — spends a few passes to delete evidence that has become actively wrong.
- **exact change:** new flag `--bank-purge 1000` on Layered: every 1,000 steps, for each weight with |c| ≥ 16 in either component, accumulate 8 fresh training batches' gated votes read-only; if the fresh net vote's sign opposes sign(c) by ≥ 4, set that counter to 0 (state untouched). Log purged share per purge. Control: same run, purge counterfactual logged but not applied.
- **horizon of onset:** ~1,000–2,000 steps — the first point where a bank can be ~10× older than the 160-step horizon over which the lab validated counter behaviour (WH-052's predicted counter half-life is ~60–90 steps; a bank surviving >10 half-lives is archaeology by that entry's own estimate).
- **short-horizon proxy + predicted reading:** two-phase switch run inside one 160-step budget: train 80 steps on source-partition A of the corpus, then 80 on partition B; at the switch and at step 160, measure the stale-sign fraction among |c| ≥ 16 counters (fresh-batch vote sign vs bank sign, as above). **Predicted reading: 30–45% stale-signed at step 160 after a single hard switch** — if a mere 80-step regime change already invalidates a third of the bank, a 10,000-step run's bank (thousands of soft regime changes) is majority-suspect. Proxy < 15% kills the entry cheap.
- **full-form prediction:** at 1,600 steps, purge beats no-purge by −0.02..−0.05 held, with purged share rising purge-over-purge (5% → 15%+ of near-threshold counters). At 16,000 steps the gap widens; the no-purge arm's late flips are increasingly old-model flips.
- **status:** queued

### LH-002 ★ · Saturation creep: the clamped-counter majority (int8 is a short-horizon answer)
- **source:** long-horizon lens + train.py audit — counters are int8 clamped at ±V=±32. Every step a counter sits at the clamp, agreeing evidence is silently discarded (the clamp, not the boundary no-op of WH-051 — this counts *all* pinned counters, boundary or not). MILL-631..633 probed clamp width at 160 steps, where few counters have had time to pin; their verdict, whatever it is, is a verdict about a regime where saturation barely exists.
- **mechanism:** The pinned fraction grows roughly monotonically: each weight that reaches ±32 and stays in a stable gradient regime parks there, insensitive — further evidence cannot strengthen it, and reversal must first unwind a full 32 of banked votes regardless of how long ago they were earned. As the pinned share rises, the trainer's *effective* sensitivity falls: a growing fraction of the network is running on a saturated integrator. Widening the counters (int16, clamp ±256, V unchanged at 32) does nothing at step 160 and everything once pinning is the norm — the extra headroom is precisely a record of *how much* evidence beyond threshold a weight has, which is also what a reversal should have to overcome.
- **exact change:** new flag `--counter-width 16` on Layered/Direct: int16 counters, clamp ±256, flip threshold still |c| ≥ 32, reset on flip unchanged. State cost +1 B/weight/component, charged. No other change — this is deliberately the MILL-631 idea re-asked at the horizon where its mechanism exists.
- **horizon of onset:** ~800–1,600 steps — when the pinned fraction crosses ~25% of all counters (below that, width is inert by construction).
- **short-horizon proxy + predicted reading:** census only, no new arm: in a standard 160-step champion run, log the pinned fraction (|c| = 32) at steps 40/80/120/160. **Predicted reading: pinned share reaches 8–15% by step 160 and is still rising near-linearly (~+2–4 pts per 40 steps)** — linear extrapolation crosses 25% before step ~600 and 40%+ by 1,600. A plateau ≤ 10% by step 160 kills the entry.
- **full-form prediction:** at 1,600 steps int16 beats int8 by −0.02..−0.06 held, driven by mid-run reversals resolving faster on genuinely-contested weights; at 160 steps the two arms tie within noise (the expected null that explains why the short-horizon clamp grid could never see this).
- **status:** queued

### LH-003 ★ · Zero-fraction creep: slow sparsity drift with no restoring force
- **source:** long-horizon lens — the ~42% zero fraction is load-bearing (built-in feature selection, per the lab's standing reading of BitNet), yet nothing in the trainer regulates it: it is wherever the vote dynamics happen to have wandered. A-009's static zero-bias prices a *level* shift at 160 steps; no entry treats the zero share as a slowly drifting state variable, because at 160 steps drift is smaller than seed noise.
- **mechanism:** Flips into 0 and out of 0 are not symmetric over long horizons: a weight at 0 whose row is quiet receives weak, mixed evidence and tends to stay, while non-zero weights keep accumulating directional pressure — the zero population behaves like a slow sink (or, in layers with strong gate statistics, a slow source). Either direction, an unregulated drift of even ~1 pt per 160 steps compounds to 6–10 pts by 1,600–16,000 steps: the long-run model is a materially sparser (or denser) model than any trial ever measured, and per-byte verdicts from short trials are denominated in the wrong sparsity.
- **exact change:** new flag `--zero-band 0.40,0.46` on Layered: every 100 steps, measure the global installed zero share; if outside the band, nudge the gate quantile for zero-ward vs zero-leaving votes by ∓0.02 (restoring force toward the band, capped ±0.06 total) — a slow homeostat on the *population*, distinct from F-024 (per-row activity servo on scales) and A-009 (fixed 1.5× zero-ward vote weight). Log zero share every 100 steps in all arms, including controls.
- **horizon of onset:** ~800 steps — drift must first exceed the ±1–2 pt seed-to-seed band visible at 160 steps; predicted crossing at 5–8× the trial horizon.
- **short-horizon proxy + predicted reading:** measure the zero share at steps 80 and 160 in 3 champion seeds and take the signed slope of the second half. **Predicted reading: a consistent-sign slope of +0.8..+1.5 pts per 160 steps in ≥ 2 of 3 seeds** (direction predicted upward — zero as sink — but the entry lives on |slope| with consistent sign, not on the direction). Inconsistent signs or |slope| < 0.3 pts kills it.
- **full-form prediction:** unservoed zero share exits the 40–46% band by ~1,600 steps and reaches ~50%+ (or < 36%) by 16,000; the servoed arm holds the band and beats the drifted arm by −0.02..−0.05 held at 1,600 steps, growing with horizon. Side deliverable either way: the first measurement of the drift rate itself.
- **status:** queued

### LH-004 · Multi-cycle consolidation: bank resolution only pays when it repeats
- **source:** long-horizon lens — D-003 established the bank-resolution idea (drop V late, let banked evidence in [8, 32) fire) as a *single* end-of-run event inside 160 steps, where the bank is thinnest. A bank is not a one-time object: it refills continuously. Only a long run can afford the phase structure the mechanism actually implies — resolve, reopen, refill, resolve again — and a single cycle at step 160 tests the weakest possible version of it.
- **mechanism:** Every 400 steps, a 40-step consolidation window at V=8 on **fresh windows only** (no replay, no buffer, no hard-window targeting — this is not a D-wave entry; the content is deliberately neutral so the *cycle* is the only variable), then V returns to 32. Each window fires the resolution wave from the bank accumulated since the last one. The claim is specifically about repetition: cycle 1 spends a young bank, cycles 3+ spend banks earned by a mature model, and the marginal value per cycle should *rise* before it falls — a shape no single-cycle design can exhibit.
- **exact change:** new flag `--consol-cycle 400,40,8` on Layered (period, window, low-V) in a companion runner; factorial controls at full form: single end-cycle only, and V=8 windows on the same schedule with counters pre-zeroed (windows without a bank — separates "low V" from "bank resolution", extending D-003's 2×2 logic across cycles).
- **horizon of onset:** ~1,200 steps — the third cycle is the first that can differ from a single consolidation; below that this collapses into D-003's territory and should not be run.
- **short-horizon proxy + predicted reading:** compress two cycles into 160 steps (V=8 for steps 76–84 and 152–160, fresh windows) vs one end cycle (steps 152–160 only) vs none, step-matched. **Predicted reading: two-cycle beats one-cycle by −0.01..−0.02 even compressed**, and the second cycle's resolution-wave flip share is ≥ 60% of the first's (bank visibly refilled in 68 steps). If the second wave is < 30% of the first, banks refill too slowly for cycles to matter and the entry dies at probe.
- **full-form prediction:** at 1,600 steps (4 cycles) multi-cycle beats single-end-consolidation by −0.02..−0.04 and beats no-consolidation by −0.03..−0.06; per-cycle wave size decays slowly (≥ 50% retained at cycle 4), which is itself the bank-refill rate the lab has never measured.
- **status:** queued

### LH-005 · Early-flip cohort scar: the first flips govern the next ten thousand steps
- **source:** long-horizon lens — a weight flipped at step 20 of a 160-step run influences 140 later steps; the same flip at step 20 of a 16,000-step run influences 15,980. Early flips are made on the weakest evidence of the run (near-init gradients, unformed scales) yet acquire the longest leverage — path dependence that scales with horizon and is therefore largest exactly where the lab never looks. At 160 steps the scar and the run are the same size, so no short trial can separate "early flips were right" from "early flips were merely first."
- **mechanism:** Give the earliest cohort a second chance at mid-horizon: snapshot the identities of the first 5% of weights ever to flip; at 50% of the run, re-randomize *those weights'* ternary states (fresh draw from the init distribution), zero their counters, and let them re-earn their states against the mature network. If early flips were good, re-earning converges back to similar states at small cost; if they were scars, the cohort lands somewhere better and the gain persists for the whole second half.
- **exact change:** new flag `--cohort-retry 0.05,0.5` on Layered (cohort share, retry point) in a companion runner; control arm retries a *random* 5% cohort of the same size at the same step (prices re-randomization itself vs earliness specifically). Log cohort state-agreement between pre-retry states and end-of-run states.
- **horizon of onset:** ~1,600 steps — the retry needs a long second half (≥ 800 steps) for re-earned states to repay the disruption; at 160 steps the second half is 80 steps and the entry is expected to read as pure cost.
- **short-horizon proxy + predicted reading:** measurement only, inside one 160-step run: split flipped weights by flip-time quartile and compute each quartile's *final-state stability* (share whose installed value at step 160 equals their value right after their first flip, minus the same share for a matched never-early control) plus flip-back rate. **Predicted reading: the earliest quartile shows the highest flip-back / instability rate (≥ 1.5× the latest quartile)** — early flips are disproportionately wrong-but-sticky. Earliest quartile most stable instead kills the scar story and the entry with it.
- **full-form prediction:** at 1,600 steps early-cohort retry beats random-cohort retry by −0.02..−0.04 and beats no-retry by −0.01..−0.03; cohort agreement (retried weights returning to their pre-retry value) lands at 40–60% — the first direct price of early-evidence quality in this trainer.
- **status:** queued

### LH-006 · Survival consolidation: a weight that survives an epoch unflipped has earned its threshold
- **source:** long-horizon lens — at 160 steps almost no weight has a meaningful "age": the run is shorter than one pass over the legal stream. At 1,600+ steps a new observable exists — time-since-last-flip spanning orders of magnitude — and the population splits into a churning minority and a settled majority that has survived hundreds of batches of counter-evidence without flipping. Survival under fire is evidence *about* a weight that neither its gradient energy (F-023) nor its flip count (A-008) records. F-025 erodes a *stalled counter's* threshold (a counter property, opposite sign); this hardens a *surviving state's* threshold (a state property).
- **mechanism:** Each weight tracks steps-since-last-flip. Once a weight has survived S = 500 consecutive steps unflipped, its personal threshold doubles (32 → 64, int16 counters) and stays doubled while it survives; a flip resets both the counter and the survival clock. Settled structure stops paying churn tax to late noise; plastic weights keep the champion's threshold exactly. The asymmetry only exists when S is a small fraction of the run — at 160 steps S = 500 never fires, which is the point: short trials cannot have tested it.
- **exact change:** new flag `--survive-v 500,2` on Layered (survival steps, threshold multiplier; per-weight age counter + int16 counters, state charged).
- **horizon of onset:** ~1,000–1,500 steps — the first cohort completes its 500-step survival and the doubled-threshold population becomes a material share (~30%+) of weights.
- **short-horizon proxy + predicted reading:** in a 160-step champion run, compute the survival curve: share of weights whose *current* state has already survived ≥ 80 steps by run end, and their forward flip hazard in steps 120–160 vs younger weights. **Predicted reading: ≥ 35% of weights are ≥ 80-step survivors by step 160, and their flip hazard is ≤ half the young weights' hazard** — survival is already informative at half-horizon, so a 500-step version at 10× horizon is a real population, not a tail. Hazard ratio ≥ 0.9 kills it (survival predicts nothing).
- **full-form prediction:** at 1,600 steps survival consolidation beats champion by −0.01..−0.04, concentrated in reduced late-run flip-back rate (≥ 25% fewer reversals among survivors); at 16,000 steps it is the difference between a settled core and perpetual slow churn.
- **status:** queued

### LH-007 · Rare-row Adam decay: the FP optimizer forgets rows the corpus rarely visits
- **source:** long-horizon lens — the shared FP parts use AdamW with β2 = 0.95 (second-moment horizon ~20 steps). A frequent embedding row is updated every step and its moments stay fresh; a tail row (the audit: 1,984 ids occur < 100 times in the whole corpus) may go hundreds or thousands of steps between updates at long horizons, and standard Adam implementations either decay its moments toward the intervening gradients of *other* rows' steps (dense update path) or leave bias correction stale — either way the row's first update after a long absence is taken with moments that describe a model thousands of steps younger. At 160 steps absences are ≤ ~160 steps and the distortion is bounded and small; it grows with the absence distribution's tail, i.e. with horizon and epochs.
- **mechanism:** Track per-row last-update step for the tied embedding; on a row's first update after a gap > 100 steps, refresh its Adam state before stepping: re-estimate exp_avg_sq from the current batch's gradient for that row (or equivalently reset the row's moments and let bias correction treat it as young), leaving frequent rows bit-identical to champion. The fix is scoped to exactly the rows the pathology can touch.
- **exact change:** new flag `--adam-refresh-gap 100` on Layered/Direct: per-row gap counter on `model.tok.weight`; moment refresh inside `step()` for rows crossing the gap threshold. Log gap distribution and refreshed-row count per 100 steps.
- **horizon of onset:** ~1,600 steps / second epoch — gaps > 500 steps for tail rows only become common once the run is long enough for the sampler to have cycled the stream; multi-epoch long runs are where the tail of the gap distribution lives.
- **short-horizon proxy + predicted reading:** instrument one 160-step champion run: histogram per-row update gaps and, for rows returning after a gap ≥ 40 steps, the ratio of their realised first-update magnitude to their median update magnitude. **Predicted reading: ≥ 20% of active rows experience a gap ≥ 40 steps even in 160 steps, and their return updates are ≥ 1.5× oversized** (stale-moment signature). Oversize ratio ≈ 1.0 kills the entry — the moments are not, in fact, going stale in this implementation, and that negative is worth owning before anyone builds the fix.
- **full-form prediction:** at 1,600 steps moment refresh improves held by −0.01..−0.03, concentrated in held windows containing tail pieces (report the rare-window split, cf. WH-019's diagnostic discipline); the gain grows with epoch count, not with steps per se.
- **status:** queued

### LH-008 · Scale random-walk anchoring: per-step innocence, cumulative drift
- **source:** long-horizon lens — G-003 bounds each log_scale step (±2%) and G-004 gates scale updates by flips; neither bounds the *cumulative* path. Over 160 steps a bounded random walk stays near its start; over 16,000 steps the same walk's displacement grows ~√T and the hand-set gradient's persistent component grows ~T — the install scales at long horizon end wherever the walk took them, potentially far from the measured absmean the init chose and that `install()`'s own formula implies. The trained endpoint scale has never been compared to the data's scale at any horizon.
- **mechanism:** Periodically re-anchor: every 1,000 steps, compute each layer's installed absmean directly and blend log_scale 25% toward log(absmean) (soft anchor, not a reset — the learned deviation is mostly kept, the walk's tail is trimmed). If cumulative drift is signal, a 25% blend costs little; if it is walk noise, anchoring removes a distortion that grows √T forever.
- **exact change:** new flag `--scale-anchor 1000,0.25` on Layered: anchor pass inside the training loop at the stated period; log per-layer |log_scale − log(absmean)| at every anchor point in all arms (the control's un-anchored distance trace is itself a deliverable).
- **horizon of onset:** ~2,000 steps — cumulative displacement must first exceed the per-layer scale differences that G-025's post-hoc calibration found worth fitting at 160 steps (~5–15%); √T scaling from a 160-step base puts that crossing in the low thousands.
- **short-horizon proxy + predicted reading:** in a 160-step champion run, log per-layer log_scale at every step; compute path length (Σ|Δ|) vs net displacement (|final − init|) per layer. **Predicted reading: path/displacement ratio ≥ 5 (a walk, not a march) with net displacement already 2–6% of scale by step 160** — a walk-dominated trace at short horizon guarantees a drift-dominated trace at 100×. Ratio ≤ 2 (scales march purposefully) kills the entry.
- **full-form prediction:** at 1,600 steps anchoring beats champion by −0.01..−0.03 with visibly smaller seed variance in final scales; at 16,000 the un-anchored arm's scales are predicted ≥ 20% from absmean in at least one layer, with held cost growing accordingly.
- **status:** queued

### LH-009 · Delayed leak: forgetting is poison early and medicine late
- **source:** long-horizon lens — the pooled leak family (MILL-209..213, λ = 0.95–0.99 always-on from step 0) will be verdicted at 160 steps, where leak's cost (discarding scarce early evidence before any flip has banked) is at its maximum and its benefit (forgetting dead regimes) cannot exist yet — there has been no time for a regime to die. The verdict will generalize wrongly in one direction or the other, because the leak question is intrinsically a horizon question: the optimal memory length is a property of how long the run is, not of the trainer alone.
- **mechanism:** Leak with a delayed onset: λ = 1.0 (no leak, champion-identical) until step 1,000, then λ = 0.999 (effective memory ~1,000 steps) for the remainder. Early evidence is kept whole while the model is young and every vote is precious; forgetting switches on only once the run is long enough to contain genuinely stale evidence (the LH-001 bank, attacked by decay instead of purge — the pair prices the two stale-evidence policies against each other at full form).
- **exact change:** new flag `--leak-delay 1000,0.999` on Layered (fractional fixed-point counters as in MILL-209's plumbing; onset step and λ are the only new parameters). Full-form factorial: {no leak, always-on 0.999, delayed} × equal steps — always-on at long horizon is *not* the pooled short-horizon arm and must be re-run at length.
- **horizon of onset:** 1,000 steps by construction — and that is the claim: below onset the arm is *identical* to champion, so any short-horizon probe is a plumbing check only and a flat probe reading is predicted, not excused.
- **short-horizon proxy + predicted reading:** regime-switch probe (shares LH-001's apparatus): train 80 steps on partition A, 80 on B, with λ ∈ {1.0, 0.99} from the switch onward; measure steps-to-recover (B-partition loss returning to its pre-switch trend) and A-bank stale-sign fraction at step 160. **Predicted reading: post-switch leak recovers ≥ 15% faster than no-leak while pre-switch (always-on) leak in a control probe costs ≥ 0.02 on the A phase** — the asymmetry (leak hurts before a regime exists, helps after one dies) is the whole entry, readable in 160 steps. Symmetric readings kill it.
- **full-form prediction:** at 1,600 steps delayed leak beats both no-leak (−0.01..−0.03) and always-on leak (−0.01..−0.02); at 16,000 the ordering is the same with larger gaps, and λ = 0.999's ~1,000-step memory tracks the bank-purge period of LH-001 — if both win, the mill has measured the trainer's true evidence half-life twice, independently.
- **status:** queued

### LH-010 · Era-stratified readout: the modal window must grow with the run
- **source:** long-horizon lens — the pooled modal readout (MILL-218/219) takes the per-weight majority over the last 5–9 checkpoints of a 160-step run: a window spanning a large fraction of the run's settled life. Copied naively to a 16,000-step run, "last 9 checkpoints" spans a negligible era and averages only the final noise; copied proportionally, it spans eras between which the model genuinely moved, and majority-voting across a real trajectory change blurs structure instead of denoising it. Readout window is a horizon-relative quantity that no entry has treated as one.
- **mechanism:** Save checkpoints at log-spaced eras (50%, 70%, 85%, 100% of the run, plus the final state) and read out the per-weight modal state across eras *weighted toward the recent* (weights 1, 2, 3, 4): the readout keeps modal denoising but its window is defined in run-fractions, so it scales with horizon by construction. Distinct from G-029 (era-matched SWA of FP parts within a short run) and G-026 (counter-resolved readout of a single final state): this is the discrete readout's window-scaling law.
- **exact change:** eval-side only, new flag `--era-modal 0.5,0.7,0.85,1.0` on the readout runner: checkpoint saves at those run fractions during any long run (storage charged), modal-with-weights at eval; report last-9 modal and final-state held on the same weights as built-in controls.
- **horizon of onset:** ~1,600 steps — eras must be separated by enough steps (≥ 250) for inter-era model movement to be real; at 160 steps the eras are 25 steps apart and all readout variants collapse into each other (predicted, and itself a checkable null).
- **short-horizon proxy + predicted reading:** on a 160-step champion run with saves at 50/70/85/100%, compute per-weight inter-era disagreement (share of weights whose era states are not unanimous) and era-modal vs last-5-modal held delta. **Predicted reading: inter-era disagreement is already 15–25% at 160 steps while the two readouts tie within ±0.005** — disagreement (the raw material era weighting acts on) is plentiful and growing with era separation, but at short horizon there is no settled era to weight toward. Disagreement < 8% kills it (the trajectory barely moves; readout window is moot at any horizon).
- **full-form prediction:** at 1,600 steps era-modal beats final-state by −0.01..−0.03 and beats last-9 modal by −0.005..−0.02; at 16,000 the last-9 baseline degrades toward final-state (window too small to denoise) while era-modal retains most of its gain — the readout's value becomes *more* horizon-dependent, not less.
- **status:** queued

### LH-011 · Block-age divergence: the two blocks stop training at the same speed
- **source:** long-horizon lens — F-010 discounts block-2 counters when block 1 flips hard (an event-level interaction). The long-horizon version is a *trend*, not an event: over thousands of steps the blocks' flip shares diverge — one block's structure settles (flip share → ~0) while the other keeps churning — so for most of a long run the network is effectively training one block against a frozen other, then vice versa, never both at matched plasticity. At 160 steps both blocks are young and their flip shares are still comparable; divergence is a slow variable.
- **mechanism:** Measure per-block flip share on a slow EMA; when the ratio between blocks exceeds 3× for 200 consecutive steps, run a 50-step *solo phase* for the settled block only (its counters live at V=16, the churning block's counters and state frozen, FP parts live) to let it re-fit against the partner's current state, then resume joint training. Solo phases are the long-run form of block coordinate descent — affordable only when the run has thousands of steps to spend them in, pointless at 160 where freezing half the model for 50 steps is a third of the run.
- **exact change:** new flag `--block-solo 3,200,50` on Layered (divergence ratio, patience, solo length) in a companion runner; log per-block flip-share EMAs for all arms — the divergence trace is a deliverable even if the entry dies.
- **horizon of onset:** ~1,200–2,000 steps — divergence must first persist for the 200-step patience window; predicted first solo phase fires in that band.
- **short-horizon proxy + predicted reading:** in a 160-step champion run, log per-block flip share in steps 0–80 vs 80–160 and compute the block ratio's drift. **Predicted reading: the block flip-share ratio moves ≥ 1.8× between halves (one block visibly settling faster) in ≥ 2 of 3 seeds** — divergence is already underway at trial horizon, just not yet actionable. Ratio stable within ±20% kills the entry.
- **full-form prediction:** at 1,600 steps, 1–3 solo phases fire and the arm beats champion by −0.01..−0.03; the settled block's post-solo flip share recovers to ≥ 50% of its early value for ≥ 200 steps (the solo phase genuinely re-opened it, rather than merely perturbing it).
- **status:** queued

### LH-012 · Evidence devaluation: a strong vote at step 10,000 is not a strong vote at step 10
- **source:** long-horizon lens — the gate is *relative* (median of the current layer, every step) and the increment is *absolute* (±1, every era). Jointly they assert that the stronger half of today's gradients is worth exactly one count, forever. But as loss falls over a long run, gradient magnitudes fall with it: the median |g| at step 10,000 is a fraction of its step-100 value, so a late "strong" vote certifies far less absolute evidence than an early one — yet it moves the same counter by the same 1 toward the same 32. At 160 steps loss moves ~2.9 → 2.86 territory on the vote path's scale and median |g| barely changes; over 16,000 steps the devaluation is first-order and the counter's evidence standard silently inflates away. (F-043 scales V with model size at fixed horizon; this scales the *count* with training progress at fixed size — orthogonal axes.)
- **mechanism:** Restore cross-time comparability: each gated vote's increment is scaled by the ratio (current layer median |g|) / (median |g| averaged over the first 100 steps), accumulated in fixed point — early votes count ~1.0, late votes count proportionally less as gradients shrink, so 32 counts always means ~32 counts *of step-100-grade evidence*. If gradients instead grow, increments grow symmetrically (cap ratio at [0.25, 2]). This is not calibrated magnitude votes (MILL-201..203 scale increments by *within-step* relative magnitude); the normalizer here is *across time*, against the run's own youth.
- **exact change:** new flag `--vote-deflate` on Layered: per-layer baseline median stored at step 100; fixed-point counter accumulation with the per-step ratio applied to increments (int16 counters; clamp/threshold logic unchanged in count units).
- **horizon of onset:** ~1,600 steps — median |g| must first fall by ≥ ~30% from its early baseline; at 160 steps the fall is within noise and the arm is champion-equivalent by construction (stated plainly: a flat probe is the predicted reading, not a disappointment).
- **short-horizon proxy + predicted reading:** measurement only: log per-layer median |g| at steps 20/80/160 in champion runs and fit its decay rate. **Predicted reading: median |g| falls 8–15% from step 20 to step 160 with a consistent sign across layers and seeds** — extrapolating that decay puts the 30% crossing inside the low thousands of steps, i.e. inside every serious long run and outside every trial. A flat or rising median-|g| trace kills the entry and, usefully, certifies the counter's evidence standard as time-invariant in this regime.
- **full-form prediction:** at 1,600 steps deflated counting beats champion by −0.01..−0.03, with the gain concentrated in late-run flip quality (flip-back rate in the final quarter down ≥ 20%); at 16,000 steps, where the undevalued counter's standard has inflated several-fold, the gap is predicted at −0.03..−0.07 — the largest full-form number in this file, and the one most tightly chained to its proxy's measured decay rate.
- **status:** queued

---

## Miner's note — the distortion already inside the 8-minute verdicts

The effect most likely to be *silently distorting current verdicts today* is the
**counter-bank complex of LH-001 + LH-002: staleness plus saturation.** Every
160-step verdict is issued by a trainer whose counters are young, mostly
unsaturated, and earned against a near-init network — the one counter regime in
which the mechanism behaves like the clean integrator the pool's mental model
assumes. Arms are therefore being ranked partly by how they interact with a
*transient* bank: leak looks worse than it is (its benefit needs a dead regime to
exist), layered levels look worse than they are (their second bank has barely
begun resolving), and any arm that front-loads flips looks better than it is
(its early flips face no stale opposition yet). None of this requires any single
verdict to be wrong at 160 steps — they are all correct measurements of a regime
that production-horizon runs will not be in. The cheapest insurance in this file
is LH-002's proxy: it is a *census on runs the mill already executes*, costing
logging only, and its slope tells the lab whether every verdict it owns is
denominated in a counter regime with a shelf life.

*End of wave-4 lens-3. 12 entries, LH-001..LH-012, ranked as listed; ★ = LH-001,
LH-002, LH-003. All status queued; merge is the pool owner's call.*
