# CANDIDATES-E — failure-driven candidates for the mill pool (Muse's work, Muse's side)

<!-- Muse's work — Muse's side of the BitNet lab. Mined 2026-11-12 by idea-mining
wave E under Arnav's mass-testing directive. This is a CANDIDATE file: nothing here is
in the pool until the pool's owner merges it. IDEA-POOL.md was read for dedupe and NOT
edited. Every entry below starts from a documented failure, regression, retraction, or
unexplained gap in the lab's own records — the follow-up test that failure implies. -->

## Method and de-duplication

Sources mined, in full: `bitnet-lab/RESULTS-2026-11-11.md`, `RESULTS-ROPE-2026-11-11.md`,
`RESULTS-HALF-CONTROL-2026-11-12.md`, `RESULTS-ROUND2-2026-11-12.md`,
`RESULTS-JEPA-2026-11-12.md`, `bitnet-lab/DATA-AUDIT.md`, `mill/RIGOR-AUDIT.md`,
`factory/reports/learned-say-2026-11-12.md`, `factory/reports/spawn-mining-2026-11-13.md`,
`factory/reports/factory-report.md`, and `growth/growth-cycle-001..006.md` plus
`REPAIR-cycle-006/007-2026-11-12.md` and both ALERT files.

Deduped against CANDIDATES-A (114), B (31), C (27), D (7) and the pool. Deliberately NOT
re-proposed: vote warmup (A-023 covers the anneal repair), tail freeze (A-022), calibrated
magnitude votes (MILL-201..203 / A-059 / A-067 — the RESULTS-2026-11-11 "fair retest" is
already owned), near-dup removal (A-047 / B-007), dream family (D-001..007), the trainer×
size×rotary grid (C-A), champion one-gene mutations (C-B), the mill confirmation set and
per-seed adoption guard (RIGOR-AUDIT fixes already implemented by the fixes stream),
probe-noise preflight (already scripted in PREFLIGHT.md). JEPA entries below are
*diagnostics of a closed result*, not re-proposals of the objective.

**Champion (gen 0):** layered_half + rotary + plain votes — held 2.8580 ± 0.0161,
adoption bar held < 2.8258. Factory serving: battery 0.941, sealed bug-pattern 0.8611.

---

## Family 1 — The learned say's clean-recall collapse (factory)

Failure: the learned say gained on dev (0.6528 vs uniform 0.5972) and lost on the sealed
set (0.8056 vs incumbent 0.8611), with **every defect class identical** — the entire gap
is clean recall 0.8182 → 0.6364 (−2 items). The report's own reading: the re-weighted
margins push clean code defect-ward into the waking layer, whose gates key off margin
*scale*, and the say was fitted on raw verdicts, not on serving-path outcomes.

### E-001 · Waking-in-the-loop say fit
- **source:** `learned-say-2026-11-12.md` — "A future attempt should fit with the waking layer in the loop on dev (fit on dev-path outcomes, not raw verdicts) — recorded as the next attack, not attempted here."
- **mechanism:** Refit the say's seat standings + thresholds by coordinate ascent where the objective is the accuracy of the **full dev serving path** (composer → waking layer → verdict) instead of raw composed verdicts. Same dev pool (216 items), same ascent discipline (strict improvements only).
- **mode:** process — factory (`factory/learned_say.py` fit objective change; judged by the existing battery `a1s` path, sealed set untouched during fitting).
- **prediction:** If the collapse was a fit-objective mismatch, dev-path fitting recovers most of the clean loss: sealed ≥ 0.8472 (within 1 item of incumbent) while keeping some dev gain. If sealed still drops ≥ 2 clean items, the problem is margin *scale* itself → E-003 decides.
- **status:** queued

### E-002 · Clean-floor constrained say fit
- **source:** same report — the say traded exactly one thing (clean recall) for its dev gain; nothing in the fit priced that trade.
- **mechanism:** Coordinate ascent as in the original build, but any step that drops **dev clean recall below the incumbent rule's dev clean recall** is rejected, however much it raises total dev accuracy. The say may only win on defect classes.
- **mode:** process — factory (`factory/learned_say.py`, one constraint in the ascent acceptance rule).
- **prediction:** Dev gain shrinks (expect 0.62–0.64 vs 0.6528 unconstrained) but sealed clean recall holds at ≥ 0.7727 and sealed total lands 0.8472–0.8750 — i.e. this is the version that could actually adopt. A sealed win here + a loss in E-001 would say the constraint, not the loop, was the missing piece.
- **status:** queued

### E-003 · Margin-scale decoupling diagnostic (is it direction or scale?)
- **source:** same report — "here the say feeds a verify-by-execution layer whose gates key off margin scale, so combination changes move the verification behaviour, not just the verdict."
- **mechanism:** Two-arm diagnostic on the existing fitted say, no refitting: (a) say directions with margins **renormalized to the incumbent's per-class margin-scale distribution** on dev; (b) the say as fitted. Compare sealed clean recall across arms. This separates "the say points the wrong way on clean code" from "the say points the right way at a scale the waking gates misread."
- **mode:** process — factory (serving-path evaluation only; a measurement, not a new model).
- **prediction:** Arm (a) recovers ≥ 1 of the 2 lost clean items if scale is the culprit. If arm (a) changes nothing, the say's directions on clean code are genuinely defect-leaning and Family 1 should stop at E-001/E-002 rather than grow more variants.
- **status:** queued

---

## Family 2 — Swapped-operands: total raw blindness, perfectly masked (factory)

Failure: raw composed recall on the sealed swapped-operands/plain slice is **0.0 in all
11 recorded measurements**, while every swapped seat is individually strong (binary dev
0.88–0.96) and the strengths table routes the plain slice to "whole", never to the plain
seat. Serving shows 1.0 only because execution verification carries the class entirely.
The spawn candidate also failed Gate 1 twice — data scale was blamed, but the routing/
margin evidence was never isolated first.

### E-004 · Forced-route diagnostic (route plain slice to the plain seat)
- **source:** `spawn-mining-2026-11-13.md` failure shape #1.
- **mechanism:** Override the strengths table for one evaluation: route the swapped/plain slice to the plain seat instead of "whole", on dev + the sealed-proxy surfaces, everything else unchanged. Measures whether the seat's binary strength (0.88–0.96) survives routing, i.e. whether the 0.0 is a routing artefact.
- **mode:** process — factory (evaluation-only routing override; no training).
- **prediction:** If routing is the failure, forced-route raw recall on the plain slice jumps from ~0.0 to ≥ 0.5. If it stays near 0.0, the seat's binary accuracy does not transfer to the composed setting and E-005's margin story is next.
- **status:** queued

### E-005 · Margin-competition autopsy + per-seat margin normalization
- **source:** same — seats strong alone, class invisible in composition: the signature of a margin-scale competition loss, the same mechanism suspected in Family 1.
- **mechanism:** Step 1 (measurement): log every seat's margin on dev plain-slice swapped items; check whether the correct seat's margin is right-signed but systematically smaller in scale than the winning seats'. Step 2 (the test): z-normalize each seat's margins by its own dev margin distribution before composition and re-measure raw recall on dev, then sealed.
- **mode:** process — factory (composer-level change in `swarm/composers.class_margins`; dev-fitted normalization constants only).
- **prediction:** Step 1 shows the plain seat right-signed on ≥ 60% of items it "misses". Step 2 lifts dev routed plain recall from 0.0667 toward ≥ 0.4. If step 1 shows the seat is simply wrong-signed in composition, both Family 2 composition entries die and the class goes back to corpus-scale growth, as the mining report concluded.
- **status:** queued

### E-006 · Verification-ablation audit (price the single point of failure)
- **source:** same — sealed recall 1.0 is *entirely* execution verification; the raw composer's 0.0 means any input the execution layer cannot decide is silently unprotected.
- **mechanism:** Run the sealed battery with the waking/execution layer disabled, per class, and record the true raw-only serving profile. No model change — this prices how much of the headline 0.8611 is the composer and how much is the verifier, class by class.
- **mode:** process — factory (battery configuration ablation).
- **prediction:** Bug-pattern sealed falls from 0.8611 to the raw composed band (~0.50–0.56), with swapped at 0.0 and clean inflated (everything leans defect-ward without verification). The number this produces is the one future composition work should be judged against — not the verification-masked headline.
- **status:** queued

---

## Family 3 — Growth gates pass, serving regresses (factory growth)

Failure, twice: cycle 6 births passed the dual pristine gate, then serving fell
0.8611 → 0.8056 and the rollback deleted the incumbents; cycle 7 births passed the gate
(expression 0.9500, index 1.0000/1.0000) and serving *still* regressed
(0.8611 → 0.8333, clean recall 0.8182 → 0.7273) before its rollback crashed. The gate
measures two held slices; the regression lives in the composed serving path the gate
never looks at. A second silent pattern: children are born with their **remainder-slice
accuracy collapsed** (expression 1.0000 → 0.4444 in cycle 6; index 0.8889 → 0.3333 in
cycle 4) — recorded as "informational" because routing serves the remainder by the
parent, so the gate never prices the debt.

### E-007 · Composed-dev third gate for births
- **source:** `growth-cycle-006.md` / `REPAIR-cycle-007-2026-11-12.md` — dual-gate births regressed serving in 2 of 2 rollback cycles.
- **mechanism:** Before a birth is adopted, run the candidate configuration through the **raw composed path on the existing dev pool** (the say_dev 216-item surface, not the sealed set): the composed raw score with the child installed must not fall below the composed raw score with the parent installed. Only then does serving verification run.
- **mode:** process — factory (`factory/growth_cycle.py` adoption sequence; dev pool already exists and is contamination-filtered).
- **prediction:** Retro-check first: both cycle-6 and cycle-7 children would have failed this gate (their serving regressions were clean-recall/composition effects visible in the raw path). Prospectively, expect it to block roughly the cycles that would have rolled back, at the cost of occasionally blocking a birth serving would have accepted.
- **status:** queued

### E-008 · Remainder-floor gate (stop birthing hollow specialists)
- **source:** `growth-cycle-002/004/006.md` — child remainder acc 0.7778 / 0.3333 / 0.4444 vs parent 0.8889–1.0000, waved through as "informational — routing serves the remainder by the parent."
- **mechanism:** A birth must also clear a remainder floor: child remainder-slice accuracy ≥ parent − 0.15 on the intent surface. Children that specialize by abandoning the rest of their slice are rejected even if both pristine slices pass.
- **mode:** process — factory (`factory/growth_cycle.py` gate; remainder slices already measured every cycle).
- **prediction:** Under this floor, cycle 4's index child (0.3333) and cycle 6's expression child (0.4444) would not have been born. The open question it answers: do floored children exist in the same grids (the per-config tables say the grids are wide), or is remainder collapse the *only* way these grids win — in which case the routing-serves-remainder arrangement is load-bearing and should be made explicit, not accidental.
- **status:** queued

### E-009 · Gate-slice enlargement retro-judgement (n=20 decides births)
- **source:** `growth-cycle-001/003.md` — births repeatedly decided by a single item on the n=20 phase-3 slice (0.9500 vs 0.9500 ties = no birth); cycle 2's own note flags it: "the honest fix is a LARGER pristine phase-3-style held slice… not more candidates against the same 20 items."
- **mechanism:** Build a new pristine phase-3-style held slice, n ≥ 100, from fresh template families (disjoint names/idioms, contamination-filtered), then **retro-judge the recorded winning children of cycles 2–6** against their parents on it. No new training — the children are on disk.
- **mode:** process — factory (new held surface + evaluation of recorded models).
- **prediction:** At least one historical birth verdict flips or ties at n ≥ 100 (the n=20 wins at exactly 1.0000 have nowhere to go but down). Whatever the outcome, every future cycle's gate inherits a slice where one item is worth 0.01, not 0.05.
- **status:** queued

---

## Family 4 — JEPA: representations equal to random init (BitNet, diagnostic)

Failure: JEPA probe CE 3.2428 vs untrained floor 3.2445 (paired mean −0.0017, a coin
flip) while its prediction loss fell ~4–5× with no collapse. The record's own hypothesis:
the signal reaches the trunk only through 64 masked positions per window, and the EMA
target (momentum 0.99 over ~170–210 steps) is still partly the random init early on.
Neither clause has been tested. These entries exist to *explain* the result — the
objective itself stays closed.

### E-010 · Non-token yardsticks on the saved JEPA trunks
- **source:** `RESULTS-JEPA-2026-11-12.md` — "It does not test JEPA's home metric… this lab has no such yardstick built."
- **mechanism:** The six saved trunks (`jepa-states/`) already exist. Probe them with (a) a 2-layer MLP readout instead of the linear probe, and (b) a span-retrieval/alignment probe (representations of two halves of one window vs mismatched windows). No training of trunks; probes only.
- **mode:** process — BitNet lab (probe scripts against saved state dicts; cheap).
- **prediction:** If JEPA learned *something* the linear token probe can't read, the MLP probe separates JEPA from the init floor by ≥ 0.05. If JEPA ≈ floor on every yardstick, the no-information verdict is total at this scale and Family 4 closes permanently.
- **status:** queued

### E-011 · Mature-target ablation (was the EMA target the poison?)
- **source:** same — "the trunk spends much of its budget learning to match a moving, partly-random target's geometry."
- **mechanism:** One JEPA arm, one change: the target encoder is **frozen at the control arm's trained trunk** (same seed) instead of an EMA of the student from init. Everything else identical to `jepa_half_rope`. This is a mechanism test, not a proposed trainer — the target now has information by construction.
- **mode:** process — BitNet lab (`run_jepa.py` variant; full trial only, 3 seeds × 8 min).
- **prediction:** If the partly-random target was the failure, probe CE improves from 3.2428 toward ≤ 3.05 (still likely behind the 2.8935 control — the claim is about the mechanism, not adoption). If it stays ≈ 3.24, target maturity is exonerated and the sparse-signal clause (E-012) is the whole story.
- **status:** queued

### E-012 · Mask-density sweep (was the signal too sparse?)
- **source:** same — signal reaches the trunk "only through 64 masked positions per window" of 256.
- **mechanism:** JEPA arms at 128 and 192 masked positions (contiguous blocks, same recipe otherwise), judged by the same linear probe against the existing 64-position records and the init floor.
- **mode:** process — BitNet lab (`run_jepa.py --mask-len 128|192`; full trial only).
- **prediction:** Monotone improvement with density (192-mask probe ≤ 3.10) would confirm sparsity as a first-order cause. Flat ≈ 3.24 at all densities kills the sparsity clause and, with E-011, closes the JEPA explanation: at 0.885M weights / 8 min the objective itself carries nothing.
- **status:** queued

---

## Family 5 — The layered retraction's open edge (BitNet)

Failure/bound: the half-control retracted the layered win **at 8 minutes** — and the
original sweep recorded why that bound matters: at equal weights, the ±2 levels were
barely populated (1.7% of weights at each of −2/+2 after 8 min). The sweep's own
"what I would run next" listed a founding-length run; it has never been run, and no
candidate file owns it.

### E-013 · Level-population dynamics (does the second layer ever wake up?)
- **source:** `RESULTS-2026-11-11.md` — "the second ternary layer had only begun to be used, so this is a verdict about 8 minutes, not about the idea's ceiling."
- **mechanism:** Instrument one layered full-width run at 8 / 20 / 40 minutes: log the ±2 population share and per-level flip rates at each checkpoint. Pure measurement; decides whether E-014 is worth its cost.
- **mode:** process — BitNet lab (`train.py` layered arm with histogram logging; one seed suffices for the dynamics question).
- **prediction:** ±2 share grows from 1.7% toward ≥ 6% by 40 min if time is the missing ingredient. If it plateaus ≤ 2.5% by 20 min, the levels are structurally starved (the vote rule rarely pushes a second component across), E-014 is cancelled, and the retraction stands at all budgets.
- **status:** queued

### E-014 · Founding-length layered vs plain (40 min, equal steps)
- **source:** `RESULTS-2026-11-11.md` "What I would run next" #2; bounded explicitly in `RESULTS-HALF-CONTROL-2026-11-12.md` ("that would be a new test, not a rescue of this one").
- **mechanism:** Layered (full width) vs plain votes (full width) at 40 minutes, judged at **equal steps** (cap both at the plain arm's step count) so the half-control's step confound cannot re-enter. 3 seeds.
- **mode:** process — BitNet lab (full trial only, long format; schedule in a free lab window).
- **prediction:** Contingent on E-013 showing population growth: layered closes at most half the 8-minute gap (3.098 → ~3.06 vs plain ~3.05) — a tie at the bar, not a win. A genuine win (layered < plain by > 2 sd and > 0.01) would be the first evidence the levels earn anything anywhere, and would reopen the layered line at long budgets only.
- **status:** queued

---

## Family 6 — Round-2 rejects with a confound still inside them (BitNet)

### E-015 · Cooldown as actually published (weight decay was a no-op)
- **source:** `RESULTS-ROUND2-2026-11-12.md` — "this trainer is built with weight decay 0, so the schedule's weight-decay component scaled a zero — weight decay was a no-op in this arm."
- **mechanism:** The cooldown arm re-run with the one change that makes it the published recipe: `--wd 0.1` on the AdamW parts (C-B07 tests wd 0.1 *without* the schedule; the combination has never run). Same two-stage lr decay, same chassis.
- **flag-level change:** existing flags combined — `--arm layered_half --rope --cooldown --wd 0.1`; mode: sweep.
- **prediction:** Still a loss, but a smaller one (2.90–2.94 vs cooldown's 2.9707): wd gives the decay phase something real to anneal. If it instead beats 2.8580, the round-2 verdict was an artefact of a half-implemented recipe and the record needs correcting.
- **status:** queued
```mill
id: E-015
mode: sweep
run: --arm layered_half --rope --cooldown --wd 0.1
```

### E-016 · Embedding-exempt cooldown (which part starved?)
- **source:** same — the record's diagnosis: decay "starves the embeddings, norms and scales that the vote-trained weights depend on," untested as separate parts.
- **mechanism:** Two-stage cooldown applied to norms + `log_scale`s only; **embeddings keep the constant lr 1e-3** for the whole run. One change from the rejected arm, aimed at its named mechanism.
- **flag-level change:** new flag `--cooldown-noemb` on the Layered trainer's AdamW groups; mode: process until the flag lands.
- **prediction:** Recovers at least half the cooldown gap (≤ 2.9143) if embedding starvation was the main clause. Recovery to ≤ 2.8580 is not predicted — the scales/norms clause may share the blame — but the split of the 0.1127 gap between parts is the deliverable either way.
- **status:** queued

### E-017 · Overshoot carry at V=8 (carry where overshoot is large)
- **source:** `RESULTS-ROUND2-2026-11-12.md` — carry rejected at V=32 with flip share and histograms "nearly identical to baseline… discarded overshoot was apparently never the bottleneck" *at V=32*.
- **mechanism:** Carry's discarded evidence scales with overshoot/V; at V=8 the same gradient stream produces proportionally ~4× the relative overshoot. Arm: layered_half + rope at V=8 with `--carry`, judged against a V=8 no-carry control run in the same window (the control is part of the entry — V=8 alone is pooled, the interaction is not).
- **flag-level change:** existing flags combined — `--arm layered_half --rope --votes 8 --carry` vs `--votes 8`; mode: sweep (pair).
- **prediction:** Carry's delta vs its control is ≥ 0.01 in *some* direction at V=8 (vs +0.0181 worse at V=32) — the entry tests whether carry has a regime at all. A flat result at V=8 too closes carry at every threshold, finally.
- **status:** queued
```mill
id: E-017
mode: sweep
run: --arm layered_half --rope --votes 8 --carry
```

---

## Family 7 — The corpus itself (BitNet, from DATA-AUDIT)

Failure: corpus v1's 5.92M pieces are ~0.91M unique real text; 30.8% of pieces are exact
duplicate copies, ~23% are numeric test-matrix dumps, the largest sources are BPE
merge-table gibberish, and the German *test* split sits inside the training data. Because
held windows come from the same duplicated stream, **all v1 held losses are flattered by
an unknown amount** — the champion's 2.8580 included. Corpus v2 (0.907M clean pieces)
exists; no arm has ever been re-baselined on it.

### E-018 · Corpus-v2 re-baseline (the honest champion number)
- **source:** `DATA-AUDIT.md` §4/§7 — v2 "fixes honesty, not volume"; recommendation was to adopt v2 for new series, but the champion has never been measured on it.
- **mechanism:** Champion config (layered_half + rope, plain votes) trained on corpus-v2 with v2-native held windows (same every-40th rule on the v2 stream), 3 seeds × 8 min. Produces the leakage-free reference every future v2 series will be judged against, and — against 2.8580 — the first estimate of the v1 flattery.
- **mode:** process — BitNet lab (new corpus path in the runner; full trial only).
- **prediction:** v2 held reads **worse** than 2.8580 by 0.15–0.45 (no duplicate leakage, no number-stream easy wins, but also far fewer unique pieces per run — the two effects oppose; the range is honest). The deliverable is the number itself: until it exists, every mill verdict is denominated in a currency known to be inflated.
- **status:** queued

### E-019 · Leakage excision on v1 (price the flattery exactly)
- **source:** `DATA-AUDIT.md` §4 — "held-out content routinely also appears in training windows, so all v1 held losses are flattered by an unknown amount."
- **mechanism:** Minimal-change control: rebuild the v1 stream with **only** the lines that duplicate held-window content removed from the training side (held windows untouched, all other junk left in). Champion re-run, 3 seeds. Δ vs 2.8580 isolates leakage from every other v1 defect — which E-018 deliberately bundles together.
- **mode:** process — BitNet lab (corpus variant + champion re-run; full trial only).
- **prediction:** Held worsens by 0.03–0.12. A Δ at the low end says arm-vs-arm v1 verdicts were barely distorted; at the high end, close verdicts in the record (RoPE's +0.0411 margin) fall inside the leakage band and must be re-read.
- **status:** queued

### E-020 · Numeric-dump ablation (23% of the corpus is float streams)
- **source:** `DATA-AUDIT.md` §5.1 — nine "lines" of 120k–154k pieces of scipy test matrices "teach number-stream statistics, not language, and… fill entire training windows by themselves."
- **mechanism:** v1 minus the mega-lines (> 1,000-piece lines: 23.0% of pieces), champion re-run at equal tokens, 3 seeds. A-047 removes near-duplicate *windows* and B-007 dedups documents; neither touches the mega-line dumps specifically.
- **mode:** process — BitNet lab (corpus variant + champion re-run; full trial only).
- **prediction:** Held improves slightly (≤ 0.05) or stays flat — the dumps are easy loss (predictable floats) but consume a quarter of all windows. If held *worsens* materially, the float streams were secretly load-bearing as a low-entropy training stabilizer, which would be a finding about the vote trainer, not the corpus.
- **status:** queued

### E-021 · German-test excision (a test split inside training data)
- **source:** `DATA-AUDIT.md` §5.5 — `de_sentences_test.txt` was included as training text in v1 and kept in v2 "for parity — flagged, not silently fixed."
- **mechanism:** Remove the German test file's lines from the training stream (v1 variant), champion re-run, and report held on German-source windows separately from the global held number — the contamination only matters if German windows are in or near the held set.
- **mode:** process — BitNet lab (corpus variant + champion re-run; cheap at probe scale first).
- **prediction:** Global held moves < 0.01 (the file is a small share), but the German-window slice moves measurably. The entry's real product is procedural: a corpus build rule (no *_test source ever enters a training stream) with one measured instance behind it.
- **status:** queued

---

## Family 8 — Mill methodology failures (from RIGOR-AUDIT)

### E-022 · Seed-0 false-negative audit (what did the screen silently kill?)
- **source:** `RIGOR-AUDIT.md` §3a(i) — "seed 0 is never rotated, so an idea that is genuinely good but unlucky on seed 0 is ledgered and dead for the generation."
- **mechanism:** After the mill's first generation completes, take every probe ledgered `flat` or `below` within Δ 0.10 of job zero and re-probe it on seeds 1 and 2 (same budget, same pass conditions). Count how many would have promoted under a 2-of-3-seeds probe rule.
- **mode:** process — mill (post-generation audit pass over `ledger.jsonl`; no pool change).
- **prediction:** 5–15% of near-miss entries flip to promote on another seed. If the rate is ≥ 20%, single-seed screening is the mill's biggest throughput leak and probe format should change to 2 seeds at half budget; if ≤ 2%, seed-0 screening is vindicated with a number instead of an assumption.
- **status:** queued

### E-023 · Fixed-step probes (remove the machine-speed confound)
- **source:** `RIGOR-AUDIT.md` §2c + `RESULTS-JEPA-2026-11-12.md` — identical configs took 129–139 vs 154–170 steps in different windows; every wall-clock probe verdict inherits that variance, and one 2026-11-11 run was discarded outright for contention (52 steps vs 121–124 clean).
- **mechanism:** A probe-format variant judged at **equal steps** (e.g. 40 steps, however long they take) instead of equal wall time, run head-to-head against the standard 75 s probe on job zero + the first five queued entries: compare verdict agreement and verdict spread across repeated passes at different machine loads.
- **mode:** process — mill (screening-format experiment in `sweep_probe.py`; verdicts recorded as method data, not pool verdicts).
- **prediction:** Fixed-step verdicts show ≥ 30% lower pass-to-pass spread under load, at the cost of unbounded probe wall time when the machine is busy. If spread does not improve, wall-clock probing stands and the step-count variance is smaller in practice than the JEPA window suggested.
- **status:** queued

---

## Family 9 — Ternary substrate collapse, one niche only (factory)

Failure: in the factory's substrate line, four niches transfer fp → ternary nearly free
(agreement 0.93–0.99), but **commit-type collapses: fp 0.9625 → ternary 0.7625,
cross-substrate agreement 0.7375**. Nothing in the record explains why this niche alone
breaks, and it stays fp by default as a result.

### E-024 · Commit-type ternary autopsy + disagreement-harvest QAT
- **source:** `factory/reports/factory-report.md` substrate line — commit-type-model is the lone substrate failure.
- **mechanism:** Step 1 (measurement): per-class fp-vs-ternary confusion on the commit-type dev surface — is the 0.20 gap one class or uniform? Step 2 (the test): QAT for the ternary commit-type model with its training mix **harvested from fp/ternary disagreement items** (the factory's own dream/harvest machinery aimed at exactly the inputs the substrate change breaks), same candidate budget as the original ternary attempt.
- **mode:** process — factory (substrate/QAT path; dev surfaces only, sealed untouched).
- **prediction:** Step 1 shows the gap concentrated in ≤ 2 commit classes (the substrate pattern elsewhere is class-specific, cf. contract's ok→no-empty-guard cluster). Step 2 recovers ternary accuracy to ≥ 0.90 if disagreement harvesting works; if it stalls ≤ 0.82, commit-type has a genuine substrate capacity wall and the fp default is a finding, not a placeholder.
- **status:** queued

---

## Coordinator's top 5

1. **E-018 — Corpus-v2 re-baseline.** Every number the mill will ever produce is
   denominated in v1 held loss, which the data audit proved is flattered by duplicate
   leakage of unknown size. One 3-seed run converts "unknown" into a number and gives
   all future series an honest reference. Highest leverage per minute in this file.
2. **E-007 — Composed-dev third gate.** The costliest repeated failure in the record:
   two consecutive cycles passed both gates, regressed serving, and triggered two
   repair operations (one after the rollback *deleted the serving models*). The gate
   measures slices; the failures live in composition. Cheap, uses surfaces that
   already exist, and retro-checkable against cycles 6/7 before it ever runs live.
3. **E-001 — Waking-in-the-loop say fit.** The factory report names this exact attack
   and nobody has run it. The learned say is the composition layer's best dev result
   ever recorded (0.6528) and it is sitting in shadow over a 2-item clean-recall gap
   with a named, testable cause.
4. **E-005 — Margin-competition autopsy (swapped-operands).** A class at exactly 0.0
   across 11 measurements while its seats score 0.88–0.96 alone is the strangest
   signal in the whole record. Step 1 is nearly free and its outcome routes three
   different follow-ups (routing fix, margin normalization, or back to corpus-scale
   growth) — maximum information per cost.
5. **E-014 — Founding-length layered vs plain** (gated by E-013's dynamics check).
   The only entry that can still move a *headline* claim: the layered retraction is
   explicitly bounded to 8 minutes, the ±2 levels were 1.7% populated, and the
   original sweep promised this test in writing. Either it retires the idea at all
   budgets or it reopens a line everyone currently treats as closed.

## The single most surprising failure pattern

**Swapped-operands blindness is total, stable, and invisible.** Raw recall of exactly
0.0 in **all 11 measurements ever taken** — never 0.1, never noise-level partial credit —
produced by seats that individually score 0.88–0.96, on a slice the router sends to the
wrong seat ("whole") every time, inside a serving stack whose headline number (1.0
sealed recall for the class) looks perfect because execution verification silently
carries the entire class. Every layer of the system had a reason to look healthy, and
the failure only exists in the one measurement (raw composed recall) that nothing in
the serving path depends on. It is the cleanest example in the record of the lab's
recurring pattern — also seen in the growth gates passing children that regress
serving, and in JEPA's training loss falling 4–5× on representations worth nothing —
**each layer's local metric can be green while the composed system is blind, and only
the composed measurement ever tells.**
