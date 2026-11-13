# Wave 3 · Lens 4 — Robustness: what breaks the vote trainer, tested deliberately

Muse's work — Muse's side

**Champion of record:** layered_half + rotary + plain votes, held **2.8580 ± 0.0161**,
counters int8 clamped **±32**, flip at 32 net votes, counter resets on flip, median
strong-half gate, flip share at champion ≈ **0.0011/step** (~973 of 884,736 ternary
weights/step). Adoption bar in this lab: >2 sd and >0.01, i.e. held < 2.8258 to adopt,
and by symmetry a degradation **> +0.032** is a measured break, not noise.

**The accidental datum this lens exploits:** corpus v1 is ~79% junk by content
(DATA-AUDIT.md: only ~0.91M of 5.92M pieces unique real text; 30.8% of pieces are
exact-duplicate copies, ~23% numeric dumps, merge-table gibberish, license
boilerplate) — and it produced *every* number the lab trusts, including the champion.
So the trainer is already proven robust to *unstructured, stationary* junk at a 4:1
junk:signal ratio. What is NOT known is its tolerance to *structured, targeted, or
non-stationary* corruption. Every entry below injects a named corruption at a
measured rate and returns either a breaking point (a number the lab should know
before scaling) or a hardened variant that beats the champion under that corruption.

**Held-set hygiene, stated once and binding on all 12 entries:** corruption is
**training-side only** (or, for serving-fault entries RB-001/RB-009, applied to a
*copy* of the trained state at eval time). The 128 held windows are never corrupted,
never injected, never duplicated into training, and are evaluated clean in every
arm. A run that touches the held set is discarded, not ledgered.

**Dedupe, stated once:** not re-proposed — A-052 (one contiguous 8-token span masked
in the input; single fixed dose, no curve), A-056 (drop worst-2% windows — removal,
not injection), A-047 / G-020 / B-007 (duplicate *removal/spacing* — this lens does
the opposite operation, deliberate duplication, to price it), A-040 (gradient-norm
clipping — a bound, not injected noise), F-018 (Byzantine quorum as a *mechanism*;
RB-005 is the stress test that prices whether any such mechanism is needed, and at
what fraction), F-032 (junk-*first* ordering on v1), E-020 (numeric-dump *ablation*
from v1; RB-008 injects measured junk into clean v2), B-009 (whole-corpus epoch
repetition; RB-006/RB-012 duplicate a *target* / a *measured fraction*, not epochs),
A-101 (label smoothing — a softening of correct labels, not replacement by wrong
ones). Where an entry is adjacent to one of these, the distinction is in its mechanism.

**Mode note:** all entries are `process` — each changes a code path (sampler,
trainer, or eval) and runs as an isolated train.py subprocess, per pool discipline.
Dose families run as separate probes per dose; the *curve*, not any single dose,
is the deliverable.

---

### RB-001 ★ · Serving fault injection: ternary flips are cheap, one FP-scale flip may not be
- **source:** territory brief (bit-flips in counters at serving) + train.py structure: the served model is 884,736 ternary weights *plus* a small set of FP parts — per-layer `log_scale`, norms, and the tied FP embedding/head — trained by AdamW. Every robustness intuition in the lab is about the ternary majority; nobody has priced the FP minority, which has no majority to hide in.
- **mechanism:** Take the trained champion state (3 seeds), copy it, and inject faults into the copy at eval only, in four separate families: (a) random ternary level flips at f = 0.01%, 0.1%, 1%, 5% of weights; (b) random int8 counter bit-flips applied to the counters *before* a final readout/install (simulating a corrupted resume-from-checkpoint); (c) single bit-flips in FP parts — one exponent-bit flip in one layer's `log_scale`, one in the embedding, one in a norm gain (n=1 per family, swept over layers); (d) whole-`log_scale` sign flip per layer. Held loss measured clean after each injection.
- **exact change:** new eval-side script flag `--fault-inject {ternary|counter|scale|embed} --rate f --seed s` operating on a checkpoint copy; no training code touched. Hardening variant, run only if (c)/(d) breaks: per-layer scale stored redundantly (median of 3 copies) + scale clamped to the training-observed range at load — one extra flag `--scale-guard`.
- **mode:** process — eval-side code path, isolated.
- **prediction (quantified):** ternary flips degrade gracefully — f=0.1% (~885 weights) Δheld < +0.01, f=1% Δ +0.03..+0.10, f=5% Δ > +0.30. Counter bit-flips are worse per event than ternary flips (an MSB flip in an int8 counter moves it by 64–128, i.e. ≥2 thresholds of phantom evidence) but still bounded: 0.1% of counters Δ < +0.05. **The FP families are the cliff: a single exponent-bit flip in one `log_scale` is predicted to cost Δ ≥ +0.5, plausibly total loss of that layer's contribution (held > 3.5); a `log_scale` sign flip makes the layer's install scale negative — predicted held > 4.0 from ONE flipped bit.**
- **what the number teaches either way:** if the ternary curve is as flat as predicted, the 1.58-bit serving story is genuinely fault-tolerant and that becomes a citable property at 50M. If the FP cliff is real, the lab's hardening priority is inverted: protect ~a few hundred FP scalars (redundancy + clamp, ~zero cost) before spending anything on ternary redundancy. If even the FP flips are absorbed (norms rescaling downstream), the whole stack is more redundant than its structure suggests and serving on unreliable hardware is de-risked in one experiment.
- **status:** queued

### RB-002 ★ · Label (target-token) noise dose–response: find p where votes stop learning
- **source:** territory brief (label noise) + the vote mechanism itself: a vote is the *sign* of a gated gradient, accumulated to ±32 before anything moves. Sign-aggregation is a majority filter — random wrong targets should cast near-random votes that cancel, while true targets vote coherently. STE has no such filter: every wrong label moves its latents at full lr.
- **mechanism:** With probability p per position, replace the training target token with a uniform-random vocab token (input untouched). Doses p = 0.01, 0.05, 0.10, 0.20, 0.30, 0.40 on the champion chassis; one matched ste_half arm at p = 0.10, 0.20 as the cross-trainer control. Theory: coherent signal scales as (1−2p), so evidence-per-flip inflates by 1/(1−2p) — at p=0.20 flips need ~1.67× the steps; at p=0.50 signal is exactly zero.
- **exact change:** new flag `--label-noise p` in the loss path (target replacement after window sampling, seeded separately so batch streams stay paired across doses). Hardening variant at the breaking dose: `--label-noise p --vlayer`-style flip-rate servo is NOT used; the hardening tested is simply raising V 32→48 at that dose (more votes = stronger majority filter) — flag `--votes 48`.
- **mode:** process — isolated subprocess per dose.
- **prediction (quantified):** champion holds Δ < +0.032 (inside the break bar) through p=0.10; Δ +0.05..+0.12 at p=0.20; **breaking point p* ≈ 0.30 ± 0.05**, where Δ crosses +0.20 and flip share collapses below ~0.0004/step (votes drowning, not votes erring). ste_half at p=0.20 is predicted to degrade ≥2× the vote arm's Δ at the same dose. The V=48 hardening at p* is predicted to recover roughly half the Δ at ~⅔ the flip share.
- **what the number teaches either way:** p* is the single most portable robustness number the lab can own — it converts directly into a data-cleaning budget (below p*, cleaning buys nothing; above it, nothing else matters). If votes break *earlier* than STE, the majority-filter story is wrong at this scale — the median gate, not the counter, was doing the work — and every downstream vote-trainer claim gets re-read. If V=48 rescues p*, threshold becomes a *noise-adaptive* knob, set from a measured corpus-noise estimate rather than by habit.
- **status:** queued

### RB-003 ★ · Mid-run distribution shift: how many steps does a 32-vote memory take to turn around?
- **source:** territory brief (distribution shift mid-run) + DATA-AUDIT.md §7: v1 and v2 are two real, already-built distributions differing maximally (v1: 79% junk, median line 9 pieces; v2: clean, median 36) — a ready-made shift pair no synthetic construction has to invent. A counter at ±32 is up to 32 steps of committed evidence *against* the new distribution; the trainer's inertia is exactly measurable.
- **mechanism:** Train on v1 for the first 50% of steps, then switch the sampler to v2 (clean) for the second 50% — and the reverse direction (v2→v1) as the second arm. Log held loss (clean held set, fixed throughout) every 10 steps post-shift to trace the recovery curve: steps-to-return-to-pre-shift-slope, and final held vs both no-shift controls. Hardening variants at the shift point: (a) counters zeroed (weights kept), (b) counters halved, (c) counters kept (control = the base arm).
- **exact change:** new flags `--shift-at 0.5 --shift-corpus corpus-v2/corpus-v2.u16` in the sampler; `--shift-counters {keep|zero|half}` in Layered at the shift step.
- **mode:** process — isolated; shift is a code-path change.
- **prediction (quantified):** v1→v2: a post-shift held *worsening* of +0.05..+0.15 lasting ~30–60 steps (the counter-turnaround window: at flip share 0.0011/step, re-flipping even 5% of weights takes ~45 steps), then recovery to beat the pure-v1 control by ≥0.05 by run end — but NOT catch the pure-v2 control (E-018's re-baseline, when run) within one budget. Counter-zeroing is predicted to shorten the worsening window by ~40% at a cost of +0.02 final held (forgotten still-valid evidence); halving dominates: ~25% shorter window, no final cost. v2→v1 degrades monotonically post-shift with no recovery — direction asymmetry is part of the prediction.
- **what the number teaches either way:** the recovery-step count *is* the trainer's effective memory horizon, measured instead of inferred from V — the number that decides whether curriculum changes, corpus upgrades (the v2 adoption question), or mixture re-weighting mid-run are cheap or ruinous at 50M, where a run is too long to restart on a data fix. If zeroing counters wins outright, "counters are a liability at a regime change" becomes a standing rule for every future corpus swap; if keeping them wins, the inertia is a feature (shift-robustness for free) and v2 adoption mid-series stops being feared.
- **status:** queued

### RB-004 · Input-token corruption dose–response (uniform random replacement, inputs only)
- **source:** territory brief (corrupted data injection). Distinct from A-052: that masks ONE contiguous 8-token span with a mask embedding at one fixed dose; this corrupts a *measured fraction of all positions* with *real random tokens* — the model sees plausible-but-wrong context everywhere, not an obvious hole somewhere.
- **mechanism:** With probability q per input position, replace the input token with a uniform-random token; targets stay true (the model must predict the real continuation from damaged context). Doses q = 0.01, 0.05, 0.10, 0.25. This is the deployment-realistic corruption: tokeniser damage, transmission errors, upstream pipeline bugs corrupt inputs, not labels.
- **exact change:** new flag `--input-noise q` in the sampler's window transform (seeded, paired across doses).
- **mode:** process — isolated per dose.
- **prediction (quantified):** flatter curve than RB-002 at equal rate — attention can route around scattered wrong tokens, and no wrong evidence is written into counters as *targets*: Δ < +0.032 through q=0.10, Δ +0.04..+0.09 at q=0.25, no sharp breaking point below q=0.40. Secondary prediction: input noise at q=0.05 *helps* clean held by −0.01..−0.03 (regularisation — the corrupted-context model cannot lean on surface collocations, which on a boilerplate-heavy corpus are exactly the overfittable part).
- **what the number teaches either way:** the RB-002/RB-004 asymmetry (labels break it, inputs don't — or the reverse) locates the trainer's fragility in the *evidence path* vs the *representation path*, which dictates where hardening money goes: label filtering vs input denoising. If q=0.05 genuinely improves clean held, the lab gains a free regulariser discovered by trying to break the model — and a suspicion that part of v1's junk was acting as exactly this all along.
- **status:** queued

### RB-005 · Byzantine batches: what fraction of sign-reversed batches can votes absorb?
- **source:** territory brief (adversarial / gradient noise) + F-018 (Byzantine quorum, a mechanism looking for its justification). Before building quorum machinery, price the threat: a bad data shard, a corrupted worker, or a poisoned slice of corpus does not add random noise — it votes *coherently backwards*.
- **mechanism:** A fraction b of batches have their gradients sign-reversed before voting (worst-case coherent adversary, strictly stronger than random corruption at the same rate). Doses b = 0.05, 0.10, 0.20, 0.30, both scattered (random batches) and concentrated (one contiguous block, same total). Median-gate note: reversed batches still pass the gate — their |g| is unchanged — so the gate offers no protection here by construction.
- **exact change:** new flag `--byzantine b --byzantine-mode {scatter|block}` in the trainer step (sign flip applied to g before the vote increment, on the affected batches only).
- **mode:** process — isolated per dose/mode.
- **prediction (quantified):** scattered: signal scales as (1−2b) as in RB-002 but with full-magnitude coherent votes, so the curve is steeper — Δ < +0.032 through b=0.10, **breaking point b* ≈ 0.20 ± 0.05** (Δ > +0.20, flip share toward the *wrong* states measurable in the state histogram). Block mode at b=0.20 is predicted *less* damaging than scatter (the block's damage is partially un-done by the clean 80% re-voting afterwards; net Δ roughly half of scatter's). 
- **what the number teaches either way:** b* is the lab's data-provenance requirement, stated as a number: if b* ≈ 0.20, a corpus that is <20% coherently hostile is safe and F-018's quorum is insurance against a threat already priced as remote; if b* ≤ 0.05, quorum/trimmed-vote hardening jumps the queue ahead of every quality lever, because one bad source file in a v3 build could exceed it. Block-vs-scatter tells whether *auditing for contiguous bad regions* (cheap, file-level) is sufficient, or per-batch defence (expensive) is required.
- **status:** queued

### RB-006 · Single-window duplication poison: how many repeats hijack a weight population?
- **source:** territory brief (duplicated data injection) + DATA-AUDIT.md §4: v1 already spends 30.8% of pieces on duplicates — but spread over ~165k duplicated lines. The untested case is *concentration*: one window, repeated deliberately, the classic memorisation/poison probe.
- **mechanism:** Pick one fixed 256-piece training window (mid-loss, ordinary prose). Inject extra copies so it occupies r = 0.1%, 1%, 5% of all training steps (on top of its natural occurrence). Measure (a) clean held loss, (b) the model's loss on the poison window itself (memorisation depth), (c) flip share attributable during poison steps. Distinct from B-009 (uniform epoch repetition of everything) and RB-012 (bulk fraction of *random* windows).
- **exact change:** new flag `--poison-window <offset> --poison-rate r` in the sampler (deterministic interleave, e.g. every ⌈1/r⌉-th batch has one slot replaced).
- **mode:** process — isolated per dose.
- **prediction (quantified):** at r=0.1% (~5 extra presentations at probe scale, ~160 at full format) poison-window loss falls ≥1.0 nat while clean held moves < +0.01 — memorisation is *local*, the trainer absorbs it. At r=1%: poison loss < 0.5, clean held Δ +0.01..+0.04. **At r=5%: clean held Δ > +0.10** — the repeated window's votes start flipping weights the general distribution needs, i.e. the breaking point for a single source is between 1% and 5% of steps.
- **what the number teaches either way:** this prices the worst case hiding inside v1's duplication statistic: no single v1 source plausibly exceeds ~1–2% of steps except the numeric dumps and merge tables (~23% and ~10%+ of pieces respectively — *above* the predicted breaking band, which would mean the champion was trained *past* a poison threshold by two sources and still won; that reframes the audit's "junk" as active opposition the trainer overcame). Either way the v3 corpus builder gets a hard per-source cap derived from measurement, not taste.
- **status:** queued

### RB-007 · Gradient-noise tolerance: how much noise can a sign vote survive that STE cannot?
- **source:** territory brief (gradient noise) + the core claim of the vote design: votes keep only sign + a median gate, discarding magnitude — so additive gradient noise should be nearly free until it flips signs, whereas STE integrates the noisy magnitude directly into latents.
- **mechanism:** Two noise forms, doses each: (a) Gaussian noise added to g before signing, σ = 0.25×, 0.5×, 1.0×, 2.0× the per-layer mean|g|; (b) per-weight sign-flip probability s = 0.05, 0.10, 0.20, 0.30 applied to the vote increment only. Matched ste_half arm under form (a) at σ = 0.5×, 1.0×. Note form (b) at s is *equivalent* to label noise only in expectation — it bypasses the gate and the loss, isolating the counter's own noise floor.
- **exact change:** new flags `--grad-noise sigma_mult` and `--vote-signflip s` in Layered.step (noise applied after backward, before the gate for (a); after the gate for (b)).
- **mode:** process — isolated per dose/form.
- **prediction (quantified):** form (a): Δ < +0.032 through σ=0.5× (the median gate discards the noisy weak half by construction), Δ +0.05..+0.10 at σ=1.0×, break (Δ>+0.20) near σ≈1.5–2.0×. ste_half at σ=1.0× predicted Δ ≥ +0.15 — votes win the comparison at high noise, lose nothing at low. Form (b): near-linear degradation, Δ ≈ +0.3·s, breaking at s≈0.30 consistent with RB-002's p* (a cross-check: two independent injections should agree on the counter's effective noise ceiling ≈30%).
- **what the number teaches either way:** if the σ-curve is flat to 1.0×, the vote trainer is *the* trainer for noisy-gradient regimes — cheap hardware, aggressive kernel approximations, low-precision backward passes all become permissible, which feeds directly back into the kernels work (an approximate matmul that perturbs g by <0.5× mean|g| is *free*). If form (b) breaks far below s=0.30 while RB-002 doesn't, the gate — not the counter — is the noise defence, and kernel noise that enters *after* the gate (i.e. in the counter update itself) is the dangerous kind. Either result draws the exact line an approximate kernel must stay under.
- **status:** queued

### RB-008 · Junk-burst timing on clean v2: does WHEN the junk lands matter?
- **source:** territory brief (corrupted data injection, distribution shift) + F-032 (junk-first curriculum — order claimed to matter, on v1) + E-020 (numeric ablation). This entry inverts both: start from *clean* v2, inject v1-style junk (numeric-dump + merge-table windows) as one contiguous burst occupying 20% of the run, placed early (steps 0–20%), mid (40–60%), or late (80–100%), plus a scattered-20% control at the same total dose.
- **mechanism:** Same corruption, same dose, four placements. The vote counter's memory (≤32 net votes, reset on flip) predicts placement matters asymmetrically: early junk is voted *away* by the clean 80% that follows; late junk lands on a converged counter population with the fewest remaining steps to repair it; mid junk is partially repaired.
- **exact change:** new flags `--junk-burst 0.20 --junk-at {0.0|0.4|0.8|scatter} --junk-corpus corpus.u16` in the sampler (burst steps draw from v1's numeric/merge regions only, identified by the audit's line offsets).
- **mode:** process — isolated per placement.
- **prediction (quantified):** early burst: final Δ vs pure-v2 control < +0.02 (fully repaired — and possibly −0.01, if F-032's junk-as-regulariser suspicion is real). Mid: Δ +0.02..+0.05. **Late: Δ +0.08..+0.15 — the worst placement, 4–7× the early cost at identical dose.** Scatter sits between mid and late. 
- **what the number teaches either way:** a placement curve converts "data quality" from a static property into a *schedule* property: it tells the v3 builder whether junk must be excluded (if even early bursts cost) or merely *front-loaded and diluted* (if early is free) — the difference between a filtering project and an ordering flag. It also directly tests F-032's premise from the clean side: if late junk costs 5× early junk on v2, then v1's champion number was earned *despite* its junk being uniformly scattered — the worst-but-one arrangement — and a junk-first v1 re-run should beat 2.8580, a falsifiable follow-on.
- **status:** queued

### RB-009 · Stuck-at counters during training: frozen evidence, live weights
- **source:** territory brief (bit-flips/faults in counters) + a fault class RB-001 does not cover: not flipped bits at serving, but counters that *stop updating* during training — the realistic failure of a corrupted checkpoint resume, a buggy fused kernel (cf. C-C04), or a partially-written state file at 50M where state is ~125 MB and a torn write is plausible.
- **mechanism:** At step 25%, freeze a fraction f of counters (both components, chosen at random) at their current values — they never vote again; their weights can therefore never flip again. f = 1%, 5%, 10%, 25%. Second form at f=10%: counters frozen *at ±32 specifically* (stuck at threshold — these weights flip once immediately, then freeze), the nastier stuck-at value.
- **exact change:** new flag `--counter-freeze f --freeze-at 0.25 --freeze-value {current|sat}` in Layered (a boolean mask applied in step; mask excluded from state-bytes accounting, noted in the run line).
- **mode:** process — isolated per dose/form.
- **prediction (quantified):** graceful to f=10%: Δ +0.01..+0.03 (at 25% of the run, most weights that will flip have begun to; freezing 10% of counters strands ≈10% of the *remaining* flip capacity, and flip share is already only 0.0011/step). f=25%: Δ +0.05..+0.10. Stuck-at-±32 at f=10% is the exception: predicted Δ +0.08..+0.15, worse than f=25% frozen-at-current — one forced wrong flip per stuck weight, applied instantly.
- **what the number teaches either way:** the f-curve is the checkpoint-integrity requirement for long runs: if f=10% is nearly free, torn writes and silent counter corruption at 50M are a nuisance, not a catastrophe, and checksumming state is optional; if stuck-at-sat is as bad as predicted, the *value* counters are stuck at matters more than the count — and a cheap load-time guard (reject/resample counters at exactly ±32 beyond the expected saturated fraction) becomes a standing rule. It also measures, as a by-product, how much of the run's remaining gain after 25% is carried by how small a minority of weights — a plasticity census the lab has never taken.
- **status:** queued

### RB-010 · Adversarial windows: max-loss replay as an attack, not a curriculum
- **source:** territory brief (adversarial windows) + A-056 / F-family failweight entries, which train *more* on hard windows as a *remedy* at mild doses. This entry pushes the same lever to attack doses and adversarial *selection*: windows chosen to maximise damage, not representativeness.
- **mechanism:** Mine the 32 training windows with highest loss under the *initial* model (fixed adversary — chosen before training, no adaptation). Replay them at rate a = 1%, 5%, 10% of steps replacing ordinary batches. A second, adaptive form re-mines every 25% of the run against the *current* model (the adversary tracks the defence). Ordinary hard-window replay at these rates is the point where "hard example mining" and "poisoning" become the same operation viewed from different intentions — the curve locates the boundary.
- **exact change:** new flag `--adv-replay a --adv-mode {fixed|adaptive}` in the sampler (mining pass at init / at quarter points, cost charged to the run's wall time and ledgered).
- **mode:** process — isolated per dose/mode.
- **prediction (quantified):** fixed adversary: a=1% Δ −0.01..+0.02 (indistinguishable from failweight's mild benefit); a=5% Δ +0.03..+0.07; **a=10% Δ > +0.12 — replay of 32 fixed windows at 10% is a poison, not a curriculum.** Adaptive adversary is worse at every dose by ~1.5× (it keeps finding the current model's wounds): break (Δ>+0.20) predicted at a≈10%.
- **what the number teaches either way:** the crossover dose where hard-window emphasis flips from remedy to attack is a safety bound on *every* hard-example idea already in the pool (failweight, D-family dream replay, A-054 regression-weighted sampling all inherit it — none of them states a ceiling). If no crossover appears even at 10% adaptive, the vote trainer is unusually replay-proof (plausible: a replayed window's votes saturate its counters, then the flip resets them — the mechanism has a built-in per-window rate limit), and that becomes a named structural property worth testing at 50M before any dream/replay system is trusted there.
- **status:** queued

### RB-011 · Counter bit-flips during training: single-event upsets in the evidence itself
- **source:** territory brief (bit-flips in counters) — the training-time twin of RB-001(b). At 50M weights the counter store is the largest single state object; on commodity hardware, silent bit errors are a rate, not a hypothetical. Nobody knows the rate the trainer tolerates because nobody has injected one.
- **mechanism:** Each step, each counter independently suffers a random single-bit flip with probability u per counter-step, u = 1e-6, 1e-5, 1e-4, 1e-3. Effect size is position-dependent by construction: a bit-0 flip moves a counter by 1 (one vote — nothing); a bit-6/7 flip moves it by 64/128 — across the ±32 threshold instantly, forcing a flip next step and a reset. So the *effective* spurious-flip rate is ≈ u × P(high bit) × N, directly computable and directly observable in flip-share telemetry.
- **exact change:** new flag `--counter-seu u` in Layered.step (XOR with a sparse random bit mask after the clamp; mask generation seeded and vectorised — cost noted, this flag is a probe tool, not a serving feature).
- **mode:** process — isolated per dose.
- **prediction (quantified):** u=1e-6 and 1e-5: Δ < +0.01 (at half width, 1e-5 × 1.77M counter-steps ≈ 18 upsets/step, of which ~¼ are high-bit — a handful of spurious flips/step against a natural ~973 — absorbed). u=1e-4: flip share measurably inflated (+10–25%) but Δ still < +0.032 — the clean majority out-votes the damage. **u=1e-3: break — spurious flips rival natural flips (~50%+ inflation), Δ > +0.10, state histogram visibly smeared toward uniform.** Breaking point u* ≈ 3e-4 ± half a decade.
- **what the number teaches either way:** u* converts into a hardware requirement in one line: at 50M counters × ~10⁴ steps, u* ≈ 3e-4/step tolerates ~10⁸ total upsets per run — orders of magnitude above any realistic silent-error rate, which would *close* the ECC question for the counter store permanently. If instead u* lands at 1e-5, the opposite follows: counters need protection (parity per row is 1 bit per 8 — cheap, but only worth building on this evidence), and the high-bit asymmetry argues for a specific redesign — sign-magnitude or Gray-coded counters, where no single bit is worth 64 votes. Either way a design decision currently made by default gets made by measurement.
- **status:** queued

### RB-012 · Bulk duplication dose on clean v2: price the accident that built v1
- **source:** territory brief (duplicated data injection at measured rates) + DATA-AUDIT.md §4/§5: v1's 30.8% duplicate-piece share was an *accident* whose cost has never been isolated — E-019 prices the held-set *leakage* flattery, but the training-side cost of duplication itself (effective epochs on the duplicated fraction, wasted steps on zero-new-evidence windows) is unmeasured. RB-006 covers one targeted window; this covers the global dose.
- **mechanism:** On clean v2 (zero duplicates by construction), duplicate a random fraction d of windows exactly once each (each chosen window appears twice per epoch-equivalent), d = 10%, 30%, 50% — d=30% deliberately reproduces v1's measured duplicate share, on clean text, with the held set untouched and unleaked. Sampler otherwise unchanged.
- **exact change:** new flag `--dup-dose d` in the v2 sampler (duplicated set chosen once, seeded, ledgered as a window-id list hash).
- **mode:** process — isolated per dose, v2 chassis (champion configuration, v2 corpus).
- **prediction (quantified):** mild and monotone: d=10% Δ +0.00..+0.02, d=30% Δ +0.02..+0.05, d=50% Δ +0.04..+0.08 — duplication wastes steps rather than poisoning them (a duplicate's second presentation votes with evidence the counters already spent; after the flip-and-reset, the same window re-earns its flips slowly). No sharp break predicted below d=50%.
- **what the number teaches either way:** at d=30% this isolates the exact price of v1's best-documented flaw: combined with E-018 (v2 re-baseline) and E-019 (leakage price), it completes the decomposition of "how much of the v1↔v2 gap is leakage, how much is duplication, how much is junk content" — three numbers the lab currently lumps into one shrug. If the dose curve is instead *negative* (duplication helps — mild repetition as implicit curriculum on a 0.91M-piece corpus that is starved, not saturated), then v2's aggressive dedup threw away the one free lunch a tiny corpus had, and the v3 builder should duplicate *deliberately* at the measured optimum rather than dedup by reflex.
- **status:** queued

---

## Ranking rationale (one line each)

RB-001 first because its predicted failure is *catastrophic and singular* (one bit,
one layer) while everything else degrades in doses. RB-002 second because p* is the
most portable number here — it sets the data-cleaning budget for every future corpus.
RB-003 third because the shift-recovery horizon decides the v2-adoption and
corpus-swap questions the lab already owes answers to. RB-004–RB-012 follow by
(blindness of the lab today) × (cost if the bad case is true at 50M): coherent
attack (RB-005) before random noise (RB-007), targeted poison (RB-006) before bulk
dose (RB-012), timing (RB-008) and replay (RB-010) as the two order-effects, and the
two counter-fault entries (RB-009, RB-011) last only because their predicted
tolerances are the widest — if either prediction is wrong, it promotes itself.
