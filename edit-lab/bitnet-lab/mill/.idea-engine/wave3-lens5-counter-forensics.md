# Muse's work — Muse's side

# Wave 3, Lens 5 — COUNTER FORENSICS: the counter field as data (Muse's work, Muse's side)

> **Territory.** A finished layered_half run leaves 884,736 vote counters behind —
> `c1`/`c2`, int8, clamped ±32, reset to 0 only on a flip (`Layered.step` in train.py) —
> and every run in the lab's history has discarded them unread. Wave G's G-026 reads
> them **once, at readout**, to express pending flips. This lens never touches the
> readout and never changes a vote: it treats the counter **field** — the full
> 65-bin distribution over 884,736 counters, per layer, per component, over time —
> as a dataset in its own right, and asks what it can *predict, certify, and detect*
> that held loss currently pays full price to learn.
>
> **Code grounding (train.py, read before drafting).** In `Layered` (non-carry),
> each step adds one gated sign vote (`-sign(g)` where `|g| ≥ median|g|`, else 0) to
> both `c1` and `c2`, clamps to ±32, flips a component when `|c| ≥ 32` *and* the flip
> is not a boundary no-op, and resets **only the flipped component's** counter.
> Three forensic consequences: (1) a counter is a *censored integral* — it records
> net evidence since the weight's last flip, so its distribution is a running
> histogram of unresolved disagreement; (2) a counter pinned at ±32 whose flip is a
> boundary no-op (t already at ±1, vote pushing outward) is **frustrated evidence** —
> it can sit saturated indefinitely and is the only population that can saturate at
> all in steady state; (3) `c1` and `c2` receive the *identical* vote stream and
> differ only in reset history, so their disagreement is a pure record of flip-path
> divergence. Champion reference: held 2.8580 ± 0.0161, ~155–170 steps at 8 min,
> mean flip share ≈ 0.0011.
>
> **Shared plumbing (stated once, assumed by every entry below).** train.py persists
> no state today. All entries assume the one shared addition several waves already
> assume: `--dump-state` extended to also dump at fractional points
> (`--dump-at 0.25,0.5,0.75,1.0`), each dump saving `t1/t2/c1/c2/log_scale` per layer.
> One dump ≈ 884,736 int8 counters + 442,368×2 ternary states ≈ 1.3 MB — negligible.
> Every entry below is an **analysis script, runner hook, or eval-side read** on
> those dumps; none changes a training update, so none can contaminate a run it
> measures. Where an entry fits anything, it fits on dumps + `runs.jsonl` records
> only, never on held windows.
>
> **Coordination, stated plainly.** The throughput lens owns *flip share* as a
> predictor (G-061 stage-0 catastrophe kill, G-065 step-10 flip-share + loss-slope
> kill, G-070 dual reads). Flip share is one scalar derived from the weights'
> *motion*. This lens uses the counters' *state* — distribution shape, saturation,
> cross-component and cross-run structure — which flip share cannot see (a run can
> have champion flip share with a pathological counter field, and vice versa).
> Where an entry here could be confused with a throughput entry, the distinction
> is named in the entry itself.
>
> **Deduped against** IDEA-POOL.md, CANDIDATES-A/B/C/D/E/F/G, FABLE-CANDIDATES.md.
> NOT re-proposed: counter-resolved readout (G-026), counter-soft install (G-030),
> counter-ranked greedy polish (G-035), counter-sum merge (G-050), counter transplant
> (G-055), counter-inherited init (G-058), boundary-pressure rerouting of saturated
> votes into the scale (F-001 — a *mechanism*; IC-003 below is a *measurement* of
> the same population, no rerouting), sparse counter storage (F-045), counter reset
> at halfway (A-110), thrash freezing and its flip-count log (MILL-215/216/217 —
> flip counts count *completed* flips; IC-010 measures sub-flip oscillation no flip
> count can see), calibration-loss checkpoint selection (G-031 — IC-006 selects on
> counters alone, zero eval passes), counter-pressure dream mining (D-004 — dreams
> *windows*; nothing here generates data).

---

### IC-001 ★ · Counter-histogram forecast: predict final held loss from the field at 25% and 50%
- **source:** counter-forensics derivation — the mill currently learns a probe's fate only by finishing it (75 s) and a trial's only by running all 3 seeds (24 min). The counter field at mid-run is an integral of every gradient sign the run has seen; if its *shape* encodes how much unresolved disagreement remains, it encodes how much loss is left to win.
- **mechanism:** Offline first, kill rule second. From `--dump-at` dumps of ≥20 completed runs (champion re-runs + ledgered arms, all with known final held), extract per-dump features: histogram entropy, mean |c|, kurtosis, mass in |c| ∈ [24, 32] (near-flip band), mass at exactly 0, per-layer mean |c| spread (max/min across the 8 BitLinear layers). Fit a ridge regression from the 25% and 50% feature vectors to final held. Only if out-of-sample (leave-one-arm-out) R² clears the bar does it become a runner hook: a probe/trial whose 50% forecast CI lies entirely above the adoption threshold is stopped and ledgered `forecast_dead` with its forecast attached.
- **exact change:** new analysis script `mill/counter_forecast.py` (reads dumps + runs.jsonl, writes the fit + per-run forecast table to `mill/COUNTER-FORECAST.md`); runner hook in `mill/screen.py` gated on the script's reported R², exactly as G-065's kill is gated on its measured precision.
- **mode:** process — analysis script + gated runner hook; no train.py change beyond the shared `--dump-state` plumbing.
- **prediction:** the 50% feature vector forecasts final held with leave-one-arm-out R² ≥ 0.7 and mean absolute error ≤ 0.03 — tight enough to kill the worst third of trials at half price (≈4 min saved per killed trial seed, ≈12 min per killed trial). The single strongest feature will be near-flip-band mass at 50%: a run still carrying >12% of counters in [24, 32] at halfway is a run whose structure is still churning, and churn at halfway has never ended well in this lab. At 25% the forecast will be weaker (R² ≈ 0.4–0.55) — reported honestly, used only for queue ordering, never for killing. **Distinction from G-065:** that kills at step 10 on flip share + train slope (motion signals, catastrophe band only); this forecasts a *continuous* final-loss value at 25–50% from distribution shape and is aimed at the near/promote band G-065 explicitly does not touch.
- **cost:** zero training cost — dumps ride on runs the mill already pays for; the fit is seconds of CPU. The hook, once active, only saves time.
- **status:** queued

### IC-002 ★ · Counter-field divergence as a verdict signal: rank arms by their distance from the champion's field, before any held eval
- **source:** counter-forensics derivation — every probe verdict today costs a held eval, and held is the lab's scarcest epistemic resource (the same 128 windows judge everything; RIGOR-AUDIT §1b counts each verdict as a selection event on them). Two runs on the same seed see the *identical* batch stream, so their counter fields are paired observations: an arm that changes nothing real should produce a near-champion field, and an arm that helps should move the field in the direction the champion's own later field moves.
- **mechanism:** For a probe arm and its paired job-zero run (same seed, same stream), compute at matched steps: (a) per-layer Jensen–Shannon divergence between the arm's and champion's counter histograms, and (b) **field velocity alignment** — cosine similarity between the arm's counter displacement (dump at 50% → dump at 100%) and the champion's displacement over the same interval, per weight, aggregated. Test, across ≥20 ledgered arms with known held Δ, whether (a)+(b) rank arms the way held Δ does. If they do, the mill gains a held-free pre-verdict: arms whose field is both far from champion *and* misaligned with champion velocity are demoted in the queue without spending a held read; held still renders every actual verdict.
- **exact change:** new analysis script `mill/counter_divergence.py` (paired-dump comparison, Spearman ρ of the divergence ranking vs held-Δ ranking printed per generation into `mill/COUNTER-FORECAST.md` alongside IC-001's table — the two share one report because they share one question: does the field know the verdict early?).
- **mode:** process — analysis script only; a queue-ordering hook in screen.py is proposed *inside* the entry but activates only on the measured ρ, as in G-042's backtest gate.
- **prediction:** Spearman ρ ≥ 0.75 between the combined divergence/alignment score and held Δ across arms — the counter field is downstream of every gradient the arm produced, so a mechanism that truly changes learning must move it, and one that moves it *against* the champion's own trajectory is spending votes unlearning. The falsifiable edge: readout-only and continuous-parts arms (G-001 family) move the field least per unit of held gain, so the score will *underrate* them — the report must print the ranking split by family, and the hook, if any, applies only within trainer/sampler families. A ρ < 0.4 result is equally valuable: it proves the field is mechanism-noise, not verdict signal, and retires IC-001's premise with it.
- **cost:** zero training cost; pairwise dump comparison is ~1 s per arm pair.
- **status:** queued

### IC-003 ★ · Frustration census: the saturated, boundary-blocked counter population as the good/bad run separator
- **source:** train.py code audit — in `Layered.step`, a counter at ±32 flips its component only if the flip moves the state; when t is already at the boundary the vote pushes against, the flip is a no-op and the counter **stays pinned at ±32**, absorbing further agreeing votes invisibly (clamp). This population — call it *frustrated* — is the only counter subpopulation whose size is exactly computable from a dump (sign(c) pointing outward from a boundary state) and it has never been counted. F-001 *reroutes* this pressure into log_scale; nobody has first *measured* whether the pressure distinguishes good runs from bad ones.
- **mechanism:** From end-of-run dumps (and 50% dumps where available), compute per layer and globally: frustrated fraction = #{weights with a component at boundary, its counter saturated with outward sign} / 442,368. Correlate with final held across all dumped runs, and track its trajectory shape (rising / flat / falling over the run's second half) as a run-quality signature.
- **exact change:** new analysis script `mill/counter_anatomy.py` (shared by IC-003/004/009/010/012 — one pass over a dump emits the full anatomy table); frustration census is its first report section.
- **mode:** process — analysis script only; no trainer, readout, or runner change.
- **prediction:** frustrated fraction at end of run separates the lab's known arms cleanly: champion-family runs land at 4–8%, catastrophe-class runs (anneal-class dynamics, if re-dumped) above 15%, and across ordinary arms frustrated fraction correlates with held at ρ ≥ 0.6 — a weight begging to leave the ternary alphabet is a weight the alphabet is failing, and a run full of them is a run whose capacity is mis-shaped, not undertrained. The sharper, decision-changing version: frustrated fraction at **50%** predicts the *sign* of the second half's held improvement (runs whose frustration is still rising at halfway gain < 0.01 in their second half in ≥80% of cases) — if true, the mill can stop paying second halves for first halves that have already announced themselves. Per-layer readout included: frustration is predicted to concentrate in `down` projections (fan-in 768, the coarsest sums) by ≥2× over `qkv`.
- **cost:** zero training cost; one dump pass per run.
- **status:** queued

### IC-004 · Per-weight counter validity: does a counter at step k actually predict its weight's final state?
- **source:** counter-forensics derivation — every counter-based idea in every wave (readout, merge, inherit, forecast) rests on one unmeasured assumption: that a counter's value carries information about where its weight *should* end up, rather than being a random walk with resets. That assumption is directly testable per weight, per layer, from dumps alone.
- **mechanism:** Across ≥10 runs with 25/50/75/100% dumps: for each weight, score how well sign(c) and |c| at step k predict (a) whether the weight flips again before end of run, and (b) its final state relative to its state at k. Report AUC per layer, per component, per k. Also report the **counter half-life**: the lag at which a counter's sign stops predicting the next flip's direction better than chance.
- **exact change:** analysis only, in `mill/counter_anatomy.py` (validity section); output is a layer × horizon AUC table.
- **mode:** process — analysis script only.
- **prediction:** AUC at 50% for "flips again before end" lands at 0.72–0.82 for `down`/`up` layers but only 0.55–0.65 for `qkv` (attention weights receive the noisiest, most context-dependent gradients) — i.e. the counter is a strong witness in the FFN and a weak one in attention, a fact that would re-price every counter entry in the pool per layer: G-026-style resolution restricted to high-AUC layers should beat its whole-field form, and IC-001's features should be FFN-weighted. Counter half-life is predicted at ~60–90 steps (roughly half a trial run) — evidence older than that is archaeology. If AUC ≈ 0.5 everywhere, the honest headline is that counters are near-memoryless at flip horizons and the entire counter research line should be re-based on short horizons only.
- **cost:** zero training cost.
- **status:** queued

### IC-005 · Counter fingerprint I — duplicate/contaminated run detection from field correlation
- **source:** mill-integrity derivation — the mill's ledger trusts that each ledgered run is the run its line claims: distinct seed, clean data, no accidental re-run of an earlier config under a new id, no held windows in the training stream. Today nothing could detect a violation after the fact. Two runs sharing an init seed start from identical states; their per-weight counters then integrate their respective batch streams — so the **per-weight counter correlation between two same-init runs is a direct meter of how much training stream they shared**, computable from two dumps and nothing else.
- **mechanism:** Calibration first: run same-init pairs at known stream overlaps (0%, 25%, 50%, 100% shared windows, constructed by the runner from legal offsets) and measure per-weight counter Pearson ρ per overlap. Then the forensic use: any two ledgered runs claiming different data/seeds whose dump-pair ρ sits in the calibrated "shared stream" band are flagged in a `mill/COUNTER-AUDIT.md` report — this catches duplicated runs, seed-reuse accidents, and, pointed at a deliberately contaminated calibration arm (5% held windows mixed into training), tests whether training-on-held leaves a counter signature distinguishable from clean training at the same init.
- **exact change:** new script `mill/counter_fingerprint.py` + four short calibration runs (probe budget, same init, runner flag `--stream-overlap F` in the *runner's* sampler, not train.py's trainer); audit mode runs over existing dumps pairwise.
- **mode:** process — analysis script + 4 probe-budget calibration runs.
- **prediction:** per-weight counter ρ tracks stream overlap near-linearly: ≈0.05 at 0% overlap (shared init only), ≈0.45–0.55 at 50%, ≥0.9 at 100% (identical runs are bit-identical, ρ = 1 by construction — the calibration's real content is the middle). The contamination arm is the gamble: a 5% held admixture is predicted to be detectable not by field ρ (too diffuse) but by a **held-window counter shadow** — weights whose counters move anomalously on held-content gradients — honestly predicted weak (AUC 0.6–0.7); even a null there is a quotable bound on what post-hoc forensics can certify. The duplicate-detection half needs no luck: it is arithmetic.
- **cost:** 4 × 75 s calibration probes; audit passes over dumps are seconds.
- **status:** queued

### IC-006 · Counter-settled checkpoint selection: pick the checkpoint whose field has stopped arguing, with zero eval passes
- **source:** gap inside G-031 — it selects among the last 9 checkpoints by calibration-window loss (10 eval passes, and one more selection pressure on legal-but-finite calibration data). A checkpoint's *own* counters offer a selection signal that costs no forward passes at all: total pending evidence P = Σ|c| over the field is the run's own measure of how much of its current state its evidence still disputes.
- **mechanism:** From the last-9 `--dump-state` saves of completed runs, compute P (and its near-flip component, mass in |c| ≥ 24) per checkpoint. Offline: compare the checkpoint each statistic selects against (a) the final checkpoint and (b) G-031's calibration-selected checkpoint, on held, across ≥8 runs. If settledness selection captures most of loss selection's gain, it becomes the default first pass — loss selection runs only when settledness is ambiguous (two checkpoints within 2% P).
- **exact change:** analysis in `mill/counter_anatomy.py` (settledness section, reads the same multi-save dumps G-031 already requires); no new dumps, no new eval passes in the analysis phase.
- **mode:** process — analysis script only in this entry; adoption as a readout is a follow-up the numbers would justify, not this entry.
- **prediction:** P falls monotonically over the last 9 checkpoints in <60% of runs — vote training keeps arguing late — and the P-minimum checkpoint beats the final checkpoint by −0.005..−0.02 on held while landing within 0.01 of the calibration-selected checkpoint in ≥6 of 8 runs. The decision-changing case is the disagreement runs: where P-minimum and loss-minimum pick *different* checkpoints, the P pick is predicted to generalise at least as well, because it never touched any eval windows to make its choice. If P is monotone in ≥90% of runs, settledness selection is vacuous (it always picks the last save) and the entry retires itself in one table.
- **cost:** zero — rides G-031's dumps; pure arithmetic per checkpoint.
- **status:** queued

### IC-007 · Counter entropy clock: histogram entropy as a convergence measure that prices run length
- **source:** counter-forensics derivation — the lab sets run length by wall clock and steps, two currencies the half-control proved treacherous (layered's "win" was its step count). The counter field offers a mechanism-native clock: at init all counters are 0 (entropy 0); evidence polarises the field (entropy rises as mass spreads over 65 bins, then falls as flips reset counters and surviving evidence concentrates). Where a run sits on that curve is a statement about its training, not about the machine it ran on.
- **mechanism:** From fractional dumps across arms and rungs (including scale-ladder dumps), plot field entropy and mean |c| against *held improvement remaining* (final held minus held-at-dump, from paired eval reads on the same dumps). Test whether "entropy within 5% of its run-final value" is a transferable stopping state across arms and sizes — a state-based budget rule ("train until the field settles to X") instead of a time-based one.
- **exact change:** analysis in `mill/counter_anatomy.py` (entropy section); requires held reads at dump points, which the readout runner already performs for G-031's saves — shared, not new, eval cost.
- **mode:** process — analysis script only.
- **prediction:** entropy at 50% of a run already sits within 8% of its final value for champion-family runs, while held still improves by 0.03–0.06 in the second half — i.e. **the field settles before the loss does**, because the AdamW parts keep fitting a structure the counters have stopped disputing. If that ordering holds across arms, entropy is a *leading* indicator and the ladder can price rungs by "steps to field-settling" (predicted: settling steps grow sublinearly with size, ~N^0.5, so larger rungs are relatively *less* undertrained at equal steps than the lab assumes). The negative result is also priced: if entropy and held plateau together within noise, the field carries no timing information beyond the loss curve and IC-001 loses its cheapest feature family.
- **cost:** zero training cost; dump-point held reads shared with G-031.
- **status:** queued

### IC-008 · Cross-arm field taxonomy: which layers' counter fields are data-driven and which are mechanism-driven
- **source:** counter-forensics derivation — when an arm wins or loses, the lab learns *that*, never *where in the network the mechanism acted*. Counter dumps give a per-layer witness: compare each arm's end-of-run field against the champion's per layer (same seed/stream pairing as IC-002) and cluster the 8 layers by how much each arm family moves them.
- **mechanism:** Build the arm × layer divergence matrix (Jensen–Shannon per layer, from IC-002's machinery) over ≥15 ledgered arms spanning families (vote-rule, sampler, architecture, continuous-parts). Read the matrix two ways: layers whose fields barely move under *any* arm are data-determined (their evidence is overwhelming and mechanism-proof); layers whose fields move under one family only localise that family's action.
- **exact change:** analysis output of `mill/counter_divergence.py` (taxonomy section — same computation as IC-002, aggregated across arms instead of ranked per arm).
- **mode:** process — analysis script only.
- **prediction:** block-1 `qkv`/`out` fields will prove the most data-determined (JS < 0.05 under every family — early attention evidence is dominated by local syntax every mechanism agrees on), while block-2 `down` is the most mechanism-sensitive layer in the model (JS > 0.25 under vote-rule arms) — meaning vote-rule innovation is effectively acting on one layer and the other seven are passengers. The actionable consequence, stated as the prediction's second half: at least two pooled vote-rule variants whose *global* held Δ was flat will show a clean block-2-`down`-only field signature — localised action with no global payoff — marking them as layer-targeted-retest candidates rather than dead ideas. If instead divergence is uniform across layers for all families, mechanisms act globally and per-layer targeting is a dead axis — also worth one table to know.
- **cost:** zero training cost; reuses IC-002's pairwise computations.
- **status:** queued

### IC-009 · Dead-counter census: the silent-weight population and what it says about wasted capacity
- **source:** train.py code audit — a counter only moves when its weight's gradient passes the median gate with a consistent sign; nothing in any record counts how many of the 884,736 counters end a run having barely moved (|c_final| ≤ 4 *and* never flipped — the second clause needs the flip history, available from multi-point dumps as state-change counting). MILL-215 logs flip counts *during* training as a freezing diagnostic; the end-state census of never-engaged weights, per layer, has never been taken. F-045 proposes *evicting* near-zero counters for storage; this entry measures whether the silent population is large and structured enough for that question — or a pruning question — to be worth asking at all.
- **mechanism:** From dumps + state-change reconstruction: per layer, dead fraction (never flipped, |c| never ≥ 8 at any dump), dormant fraction (flipped exactly once, early, then silent), and their overlap with the final zero-state population. Cross-arm comparison: does dead fraction predict held (capacity wasted) or anti-predict it (sparsity earned)?
- **exact change:** analysis in `mill/counter_anatomy.py` (census section).
- **mode:** process — analysis script only.
- **prediction:** dead fraction is large and layer-structured: 25–40% of block-1 counters never engage, vs 8–15% in block 2 — early layers converge to their (mostly local-syntax) structure fast and then sit out the run. Across arms, dead fraction will *anti*-correlate with held at ρ ≈ −0.4..−0.6 within the champion family (a run that engages more of its field uses more of its capacity) but the relation inverts for catastrophe arms (frantic engagement = thrash) — the census's real deliverable is that two-regime picture, which no single correlation states. Either way the number disciplines F-045: eviction is worth building only if the truly-dead share (not merely near-zero at one instant) exceeds ~20%.
- **cost:** zero training cost.
- **status:** queued

### IC-010 · Sub-flip oscillation anatomy: the argument underneath the flips
- **source:** counter-forensics derivation — flip counts (MILL-215's diagnostic, A-008's thrash tax) see only arguments that *ended*: a weight whose counter swings +28 → −28 → +28 without ever reaching 32 is in violent disagreement with itself and is invisible to every flip-based statistic the lab owns. Only multi-point counter dumps can see it.
- **mechanism:** From dumps at 25/50/75/100%: per weight, count counter sign changes and total counter path length Σ|Δc| between dumps; define the **hidden-thrash population** as weights with ≥2 sign changes and path length ≥ 64 but zero flips. Report its size per layer, and test whether hidden-thrash share at 50% predicts a run's second-half held gain better than its flip share does (the head-to-head against the throughput lens's scalar, run on forensics turf: same runs, same outcome, two predictors).
- **exact change:** analysis in `mill/counter_anatomy.py` (oscillation section).
- **mode:** process — analysis script only.
- **prediction:** the hidden-thrash population is 3–6% of weights, concentrated in block-2 `qkv`, and its 50% share predicts second-half gain with ρ ≈ −0.6, beating flip share's ρ on the same runs by ≥0.2 — because flip share measures *resolved* churn (often healthy late training) while hidden thrash measures *unresolvable* churn (two data regimes voting one weight in opposite directions, the signature G-016's mixture-order entry predicts block-grain rotation would create — this census is that entry's cheapest possible pilot: if hidden thrash does not spike under conflicting evidence, mixture order has no counter-level mechanism to act through). A hidden-thrash share under 1% everywhere retires the concept and strengthens flip share's claim to be the whole motion story.
- **cost:** zero training cost; needs the 4-point dumps of the shared plumbing.
- **status:** queued

### IC-011 · Counter-kurtosis early warning: field shape spikes before loss spikes
- **source:** failure-forensics derivation — the lab discovers a diverging or destabilised run at its end (held read) or not at all. A destabilising run should deform its counter field *before* the deformation reaches held loss: a few weights receiving extreme one-sided evidence (kurtosis spike in the |c| distribution, mass suddenly piling into the near-flip band in one layer) is the field-level shape of a gradient pathology, and counters integrate it within a few steps.
- **mechanism:** Retrospective study on dumps from the lab's known bad runs (anneal-class and any ledgered divergence, re-dumped at 10% intervals for this entry — the one place this file asks for short re-runs) plus champion controls: compute per-dump excess kurtosis of |c| and single-layer near-flip-band mass; measure lead time between the first dump where either statistic exits the champion family's band and the first dump where paired held-at-dump exits its band.
- **exact change:** 3–4 probe-budget re-runs of known-bad configs with `--dump-at 0.1,0.2,…,1.0` + analysis section in `mill/counter_anatomy.py`; if lead time is real, a runner hook (warn-only, never kill — killing stays IC-001/G-065's gated business) is the stated follow-up, not part of this entry.
- **mode:** process — analysis script + ≤4 short re-runs.
- **prediction:** kurtosis exits the champion band 15–25% of a run *before* held does in the anneal-class failure (its hot start fires flips on weak evidence, which must show as a field-wide |c| pile-up within the first fifth), giving a genuine early-warning window; for slow failures (cooldown-class starvation, a continuous-parts pathology) the counter field is predicted to show **nothing** — the counters are healthy while the FP parts starve — and that blind spot, measured rather than assumed, is half the deliverable: it fences exactly which failure classes counter forensics can ever police.
- **cost:** ≤4 × 75 s re-runs; rest is dump arithmetic.
- **status:** queued

### IC-012 · c1/c2 disagreement anatomy: the layered chassis's internal contested population
- **source:** train.py code audit — `Layered` feeds both components the *same* vote; `c1` and `c2` diverge only because flips reset them at different times and t1 has flip priority. Their per-weight sign disagreement is therefore a quantity no other chassis produces: a direct census of weights where the two components' recent evidence points in opposite directions — weights the summed code (levels −2..+2) is internally undecided about. The half-control proved the second component earns nothing *on average*; this anatomy asks whether it earns something on an identifiable subpopulation and is pure noise elsewhere.
- **mechanism:** From champion dumps: per layer, contested fraction = #{sign(c1) ≠ sign(c2), both |c| ≥ 8} / 442,368, tracked over the run; and the retrospective test — do contested weights at 75% account for a disproportionate share of the flips and held-relevant state changes in the final quarter (measurable from the 100% dump's state diff)? Compare against plain_half dumps, where the analogous quantity (single counter near zero with high path length, from IC-010) defines its contested set, so the two chassis' indecision can be priced in the same units.
- **exact change:** analysis in `mill/counter_anatomy.py` (disagreement section; the plain-chassis comparison reuses IC-010's outputs).
- **mode:** process — analysis script only.
- **prediction:** contested fraction settles at 10–16% of weights and is *not* uniform: it concentrates where |t1 + t2| ∈ {0, 2} (the levels the forward rounding treats most coarsely) and in block 2. Contested weights at 75% will account for ≥35% of final-quarter flips from ~13% of the population — the second component's real job, if it has one, is arbitrating exactly this set. The decision this prices: a future layered variant that spends its second component *only* on the contested population (and runs plain elsewhere, at plain's state bytes) is worth pooling iff the contested set carries ≥2× its share of late flips; below that, the layered idea has no anatomical refuge left and the half-control's verdict stands unqualified.
- **cost:** zero training cost.
- **status:** queued

---

## Miner's ranking note

Ranked by (decision changed) × (probability the signal is real) ÷ (cost — which is
near zero throughout, so ranking is almost purely about consequence):

1. **IC-001 ★** — a working 50% forecast converts every trial from a fixed 24 min
   purchase into a sequential decision; it is the only entry here that pays for
   itself in the mill's own currency from its first generation.
2. **IC-002 ★** — if field divergence ranks arms, held stops being spent on
   pre-verdicts and survives longer as a judge; if it doesn't, IC-001's premise
   dies cheaply alongside it. The pair stand or fall together, by design.
3. **IC-003 ★** — the frustration census is the cheapest statistic in the file
   (one dump, one pass, exact definition) with the sharpest predicted separation,
   and its 50% form doubles as a second-half kill signal independent of IC-001's
   regression.
4. IC-004 — the validity bedrock: every counter idea in every wave silently
   assumes what this measures.
5. IC-005 — the integrity instrument; duplicate detection is arithmetic, the
   contamination bound is a bonus.
6. IC-006 through IC-012 — anatomy that re-prices existing pool entries
   (G-031, F-045, MILL-215, G-016, the layered chassis itself) rather than
   proposing new mechanisms; each is one section of two shared scripts, so the
   marginal cost of the whole tail is a few hours of analysis over dumps the
   shared plumbing produces anyway.

**The most decision-changing counter signal, if I must name one:** the
**frustrated fraction at 50%** (IC-003) — the share of weights whose counters are
pinned at ±32 begging for a flip the ternary alphabet forbids. It is exactly
computable, needs no fitted model and no eval pass, and if its predicted
signature holds (rising frustration at halfway ⇒ a second half that gains
< 0.01), it simultaneously (a) kills doomed second halves across the whole mill,
(b) turns "is the ternary alphabet the binding constraint?" from a philosophy
question into a per-layer number, and (c) gives the scale ladder its first
mechanism-native capacity gauge — larger rungs should show *falling* frustration
if width is what the frustrated weights were asking for.

*End of wave-3 lens 5 (counter forensics). 12 entries, IC-001..IC-012, all queued,
none duplicating IDEA-POOL.md or CANDIDATES-A/B/C/D/E/F/G or FABLE-CANDIDATES.md.
Shared assumption, stated once in the header: `--dump-state` with fractional
`--dump-at` points persisting `c1/c2` alongside `t1/t2`.*
