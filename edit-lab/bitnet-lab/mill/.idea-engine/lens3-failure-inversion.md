# Muse's work — Muse's side

# Lens 3 — FAILURE INVERSION: every documented failure read as a signpost (Muse's work, Muse's side)

> Coordination note: `mill/CANDIDATES-E.md` **existed when I read it** (31,839 bytes,
> mined by the parallel E stream) and was re-checked before this file was finished
> (see the closing note). All 24 E entries were read in full and are NOT duplicated
> below: E catalogues the failure and proposes its *repair or diagnosis*; each entry
> here asks the inverted question — **what would have to be true for this failure to
> be a feature?** — and designs the test that exploits the failure in its failed
> form. Also deduped against `mill/IDEA-POOL.md` (368 entries), CANDIDATES-A/B/C/D
> and FABLE-CANDIDATES.md. Nothing closed is re-proposed in its failed form:
> overshoot carry, cooldown, anneal 8→64, magnitude votes as specified, and the JEPA
> objective all stay closed — where one of them appears below, the mechanism is
> changed (different job, reversed schedule, or different consumer), never re-run.

Champion reference: layered_half + rotary + plain votes, held **2.8580 ± 0.0161**,
adoption bar held < 2.8258. Factory serving: battery 0.941, sealed bug-pattern 0.8611.

---

### FI-001 ★ · JEPA as initializer, not objective — a trunk "equal to random init" on the probe may still be a better-than-random place to *start*
- **source:** `RESULTS-JEPA-2026-11-12.md` — JEPA probe CE 3.2428 vs untrained floor 3.2445 (paired mean −0.0017, a coin flip), yet JEPA's own prediction loss fell ~4–5× (0.086–0.092 → 0.019–0.023) and target-representation diversity *rose* (per-dim std 0.29–0.32 → 0.36–0.48) with no collapse. E-010/011/012 probe the frozen trunk, mature the target, and densify the mask — all still judge JEPA as a finished representation.
- **mechanism:** Inversion: the probe verdict says JEPA's trunk carries no *linearly readable token information* — it does not say the trunk is in the same *place* as random init. A trunk whose representations are diverse, non-collapsed, and predictive of masked spans may be a superior initialization for ordinary token training even though it is a worthless finished product. Use the six saved trunks in `jepa-states/` as the init for the champion token trainer, instead of random init. JEPA's job changes from "be the model" to "warm the basin."
- **train.py:** `run_jepa.py` already saves the trunks; add `--init-from <state_dict>` to `train.py` (load trunk weights into the layered_half + rotary chassis, fresh counters, fresh AdamW parts) — arms: (a) init from `jepa_half_rope` trunk, (b) init from the paired control trunk (positive control: a token-trained init must help), (c) random init (= champion record). 3 seeds × 8 min, judged at equal steps.
- **mode:** process
- **prediction:** If the diversity/no-collapse traces mean anything, (a) beats random init by ≥0.03 at equal steps and reaches 2.8580's neighbourhood in visibly fewer steps, while landing well behind (b). Any (a) > (c) gap is information the linear probe structurally cannot see — which would reframe the JEPA verdict from "learned nothing" to "learned something the token probe doesn't read, but token training can spend."
- **kill test:** Paired (a)−(c) mean ≥ −0.01 (no better than noise) across 3 seeds — then JEPA init is exactly as empty as the probe said, the inversion dies, and Family 4 of E closes with it.
- **status:** queued
- ★ reason: cheapest strong test in this file — the trunks already exist on disk, and it is the only entry that can overturn a headline verdict (JEPA = nothing) rather than merely price it.

### FI-002 ★ · Junk-first curriculum — if ~79% junk produced every number the lab trusts, maybe the junk is load-bearing, and *order* is how it helps
- **source:** `DATA-AUDIT.md` §2–§5 — corpus v1 is 30.8% exact-duplicate pieces, ~23% numeric test-matrix dumps (nine lines of 120k–154k pieces), merge-table gibberish as the two largest sources, 73.9% of source bytes from venv/HF-cache junk — yet this stream produced the champion 2.8580 and every arm verdict. E-018/019/020/021 all *remove* parts of the junk to price the damage; A-041 orders windows by init loss. Nobody has treated junk as an ingredient.
- **mechanism:** Inversion: numeric dumps and boilerplate are low-entropy, highly predictable text — exactly the stream on which a vote counter can bank its first reliable flips (consistent, agreeing gradient evidence) and on which embeddings/scales can calibrate before real prose arrives. Test junk as a *curriculum phase*, not a contaminant: first 25% of steps sample only junk-type windows (numeric dumps + boilerplate + duplicates, tagged at corpus build), remaining 75% sample clean v2 windows only. Mandatory control in the same entry: the identical two-source mixture, shuffled (same junk share, no order) — the pair isolates ORDER from MIXTURE, which no existing entry does.
- **train.py:** new sampler flag `--junk-first 0.25` in `train.py` (window stream tagged by source type from a `make_corpus.py` variant emitting per-line type tags; junk = numeric-dump / separator-boilerplate / exact-duplicate lines per DATA-AUDIT §5 definitions); control arm `--junk-mix 0.25` (same tags, shuffled). Champion chassis, 3 seeds × 8 min, held on v2-native windows so junk familiarity cannot flatter the judge.
- **mode:** process
- **prediction:** Junk-first beats its shuffled-mixture control by ≥0.03 and beats a clean-v2-only run at equal tokens by ≥0.02 — the signature of junk doing early-evidence work rather than merely diluting. Corollary trace: flip share in the first 25% of steps is higher and less thrashy (fewer flip reversals) under junk-first than under either control.
- **kill test:** Junk-first ≥ shuffled control (order earns nothing) **or** junk-first ≥ v2-only (the junk phase is pure cost) — either retires the idea and strengthens E-020's reading that the dumps are inert filler.
- **status:** queued
- ★ reason: it inverts the lab's most embarrassing fact instead of cleaning it up, and its shuffled control makes the result decisive either way — a win rewrites corpus policy, a loss finally clears the junk question.

### FI-003 ★ · Split the layered stack into an ensemble — levels that earn nothing *summed* may earn something *voting*
- **source:** `RESULTS-HALF-CONTROL-2026-11-12.md` — plain_half 2.9010 vs layered_half 2.8990 at equal size/steps (Δ 0.0020, clears neither bar): the five levels earn nothing. And `RESULTS-2026-11-11.md` — at equal weights layered was already no better than plain (3.098 vs 3.074). A-036 collapses the components into one plain model late; nobody has separated them.
- **mechanism:** Inversion: a sum forces the two ternary components to agree on one weight value; their failure to beat plain may mean they learned *redundantly*, or it may mean they learned *different* things that the sum averages away. Split a trained layered_half checkpoint into its two component models (t1-only and t2-only, each a complete plain ternary model at half the mechanism state), and serve the pair as a two-model ensemble (mean of logits). If the components' errors are decorrelated, the ensemble beats both the summed model and either component — the layered idea pays, but as an ensemble factory, not as a weight format.
- **train.py:** no training change; new evaluation path `--split-ensemble` in `train.py`'s eval (load a layered checkpoint, build the two component models, report held for t1-only, t2-only, summed, and logit-mean ensemble, per seed, on the standard 128 held windows).
- **mode:** process
- **prediction:** Ensemble held ≤ summed − 0.02 (i.e. ≤ ~2.88 against layered_half's 2.8990 record, re-measured in the same run), with t1-only and t2-only each in the 2.95–3.10 band and per-window error overlap < 80% — decorrelation is the mechanism, so the overlap number is reported either way.
- **kill test:** Ensemble ≥ summed model, or component error overlap ≥ 90% (the components really are redundant copies) — then the levels earn nothing in any arrangement and the layered line is closed at serving as well as in training.
- **status:** queued
- ★ reason: zero training cost (checkpoints + one eval path), and it tests the one arrangement of Arnav's layered idea that has never been tried — separation instead of summation.

### FI-004 · The learned say as a verification-budget allocator — a bias that ruins a verdict may be ideal for triage
- **source:** `factory/reports/learned-say-2026-11-12.md` via CANDIDATES-E Family 1 — learned say: dev 0.6528 vs uniform 0.5972, sealed 0.8056 vs incumbent 0.8611, the entire gap clean recall 0.8182 → 0.6364: the say pushes clean code *defect-ward*. E-001/002/003 all try to fix the say's verdict (refit in-loop, constrain the fit, renormalize margins).
- **mechanism:** Inversion: keep the say exactly as fitted and change its job. A defect-ward bias is a failed *judge* but a natural *screener*: high sensitivity, poor precision is precisely the profile wanted for deciding which items deserve the expensive execution-verification pass first. Deploy the say as the verification scheduler: items ranked by say defect-margin descending get waking/execution verification until the budget runs out; the verdict itself always comes from the incumbent composer + verifier path, never from the say.
- **train.py:** factory-side — `factory/learned_say.py` (export the fitted say's per-item defect-margin as a ranking score) + the serving path's verification loop (verify in say-rank order under a call budget). No refitting, no model change.
- **mode:** factory
- **prediction:** At 50% of the full verification budget, say-first allocation holds sealed accuracy ≥ 0.8472 (within 1 item of the 0.8611 full-budget incumbent), and beats random-order and incumbent-margin-order allocation at the same budget by ≥ 1 item — the say's "false alarms" are concentrated exactly where verification pays.
- **kill test:** Say-first allocation ≤ random allocation at equal budget on the sealed battery — the defect-ward lean carries no triage information and the say is retired entirely, not just as a judge.
- **status:** queued

### FI-005 · Partial births — adopt the slices a child actually won, keep the parent everywhere else
- **source:** `growth/growth-cycle-006.md` — both children passed the dual pristine gate (expression 0.8500→0.9500 phase-3, 0.6326→0.7392 intent; index 0.9500→1.0000, 0.9566→1.0000), then serving fell 0.8611 → 0.8056 and both births were rolled back wholesale; cycle 7 repeated the shape (serving 0.8611 → 0.8333, clean recall 0.8182 → 0.7273). E-007 adds a gate that blocks bad births; E-008 floors the remainder. Both still treat a birth as all-or-nothing.
- **mechanism:** Inversion: a child that regresses *in composition* but wins *on slices* is not a failed birth — it is a partial one being judged in the wrong unit. Replace whole-model adoption in `factory/growth_cycle.py` with per-intent adoption: on the composed dev path, compute the child's gain intent-by-intent; adopt the child only for intents where composed-dev improves, keep the parent for every other intent (routing already serves slices independently, so the machinery exists). Retro-apply first to the recorded cycle-6/7 children, whose models and slices are on record.
- **train.py:** factory-side — `factory/growth_cycle.py` adoption sequence (per-intent composed-dev diff → adoption mask → routed serving config). No BitNet `train.py` change.
- **mode:** factory
- **prediction:** Retro-check: at least one of the four rolled-back children has ≥1 intent with a real composed-dev gain, and partial adoption of it holds sealed ≥ 0.8611 while capturing part of that gain — converting two total losses (plus two repair operations) into small wins. Prospectively, rollback count drops because fewer births need one.
- **kill test:** For both cycles, *no* intent slice shows a composed-dev gain > 0 for any child — the regressions are uniform, not compositional, partial adoption has nothing to adopt, and E-007's whole-birth gate is the right unit after all.
- **status:** queued

### FI-006 · Swapped-operands blindness as a commutativity guarantee — route *to* the blind spot, not away from it
- **source:** `factory/reports/spawn-mining-2026-11-13.md` via CANDIDATES-E Family 2 — raw composed recall on the sealed swapped-operands/plain slice is 0.0 in all 11 measurements, while the seats score 0.88–0.96 alone and serving shows 1.0 only because execution verification carries the class. E-004/005 try to cure the blindness (forced routing, margin normalization); E-006 prices it.
- **mechanism:** Inversion: total, stable operand-order blindness is what an *order-invariant* detector looks like. For genuinely commutative operations (sum, product, max, min) invariance is not a bug — it is the correct inductive bias, and a composer that provably cannot see operand order cannot be fooled by operand order. Split the class by commutativity: route commutative-operator items to the raw composer *because* it is blind (cheap, no verification needed), and reserve the execution-verified path for the non-commutative operators (difference, quotient, remainder, element_at) where order is the whole meaning.
- **train.py:** factory-side — serving routing table (strengths/router config in the swarm composer path): key the swapped/plain slice by operator commutativity instead of routing it wholesale to "whole". Evaluation on dev + sealed, per operator class.
- **mode:** factory
- **prediction:** On the commutative slice, the blind raw composer's accuracy is within 0.05 of the verified path's, while verification calls on the whole swapped slice drop ≥ 30% at unchanged sealed total (≥ 0.8611). If blindness is really invariance, the lab has been paying full verification price to protect a slice that never needed it.
- **kill test:** Commutative-slice raw accuracy < 0.8× the verified path's — the blindness is not clean invariance but general order-confusion that also corrupts commutative items, and the routing inversion dies (E-004/005 remain the only live attacks).
- **status:** queued

### FI-007 · Reverse cooldown — if decaying the AdamW parts starved them, feed them *more* late
- **source:** `RESULTS-ROUND2-2026-11-12.md` — two-stage cooldown 2.9707 ± 0.0108 vs baseline 2.8580 (+0.1127, every seed worse than every baseline seed); the record's own diagnosis: "halving the AdamW parts' effective learning in the second half starves the embeddings, norms and scales that the vote-trained weights depend on." E-015 adds the missing weight decay; E-016 exempts the embeddings. Both still decay *something*.
- **mechanism:** Inversion: take the starvation diagnosis literally and run its opposite — a two-stage *warm-up ending hot*: AdamW lr constant 1e-3 for the first half, then linearly **rising** to 2e-3 over the second half, vote rule untouched (V=32, median gate fixed — this is not the closed vote-threshold anneal). Rationale the failure suggests: vote flips keep landing all run, so the continuous parts face a *moving* target late; they may need more fitting capacity at the end, not less. Constant-lr 2e-3 exists in the pool (C-B04) — a late-only ramp is a different claim: early stability, late appetite.
- **train.py:** new flag `--cooldown-inv` on the `Layered` trainer in `train.py` (mirror the existing `cooldown` multiplier code with stage-2 multiplier 1.0 → 2.0 on the AdamW param groups only); sweep config `--arm layered_half --rope --cooldown-inv`, 3 seeds × 8 min.
- **mode:** sweep
- **prediction:** Held recovers the starvation gap and then some: 2.83–2.87, i.e. at or near the 2.8580 champion, with the gain concentrated in the second half's held-loss slope (logged per 20 steps). Even a tie at 2.8580 with a rising schedule falsifies "decay is the right direction for the continuous parts" on this chassis.
- **kill test:** Mean held ≥ 2.8765 (the champion's worst seed) — rising lr hurts or does nothing, the starvation story is wrong in both directions, and the AdamW schedule is confirmed a dead dial at constant 1e-3.
- **status:** queued

### FI-008 · The ladder measured tokens; the champion spends steps — re-run one rung at champion steps and count flips
- **source:** `run_scale_ladder.py` — every ladder rung is fixed at 56 steps × 32 batch × 256 ctx = 458,752 pieces; the champion's 2.8580 (`RESULTS-HALF-CONTROL-2026-11-12.md`) came from 154–170 steps ≈ 1.26–1.39M pieces, ~3× the ladder budget. With V=32, a counter needs 32 net agreeing votes to flip once — at 56 steps most weights can flip at most once or twice, so the ladder's big rungs were judged in a regime where the vote mechanism is barely allowed to move. C-A fills the trainer×size×rotary grid *at ladder steps*; E-014 lengthens layered-vs-plain at full width. Neither re-prices a ladder rung at champion steps.
- **mechanism:** Inversion: for a vote trainer, **steps are the currency, tokens are the denomination** — equalizing tokens across rungs systematically handicaps the mechanism the ladder claims to measure. Re-run the 2M rung (dim 288, 2 blocks) at 160 steps, layered+rope and plain+rope, and log the per-weight flip-count distribution at 56 vs 160 steps. The claim under test is vote-specific: the layered-vs-plain gap and the absolute loss at 160 steps should move *more* than a generic "more training helps" effect predicts from the plain arm.
- **train.py:** sweep configs `--arm layered --rope --dim 288 --layers-n 2 --steps 160 --tag scale2m-steps160` and `--arm plain --rope --dim 288 --layers-n 2 --steps 160 --tag scale2m-steps160`, 2 seeds, plus flip-count histogram logging in the `Layered`/`Direct` trainers (count flips per weight, dump at end of run).
- **mode:** sweep
- **prediction:** At 56 steps ≥ 85% of ternary weights flip ≤ 1 time (the ceiling made visible); at 160 steps the layered arm improves over its 56-step record by ≥ 0.10 while plain improves by less, reopening a layered gap that the 56-step ladder reported as flat. Either way, the flip histogram becomes the lab's standard caveat on every fixed-token comparison.
- **kill test:** Both arms improve by the same amount (± 0.02) from 56 → 160 steps, or the 56-step flip histogram already shows a broad multi-flip distribution — then steps are just generic budget, the ladder's token equalization stands, and this entry retires.
- **status:** queued

### FI-009 · Carry as a measuring instrument — the arm that lost on mean won on variance by 5×
- **source:** `RESULTS-ROUND2-2026-11-12.md` — overshoot carry: mean 2.8761, **sd 0.0030**, vs the baseline's sd 0.0161; "the three seeds cluster very tightly." Carry is closed as a *trainer* (worse mean, +80% state). Nothing in the pool uses a trainer as an instrument. (E-017 tests carry as a trainer again at V=8 — a different claim, untouched by this entry.)
- **mechanism:** Inversion: a trainer that trades 0.018 of mean for a ~5× tighter seed spread is a worse product and a better *ruler*. The mill's probe screen lives and dies on single-seed (seed-0) verdicts (`RIGOR-AUDIT.md` §3a, priced by E-022); a low-variance probe chassis would make those verdicts cheaper to trust. Re-probe job zero plus four already-ledgered entries with the carry trainer at probe budget and compare cross-seed spread and verdict agreement (promote/flat/below) against the standard plain-vote probes.
- **train.py:** mill-side — `mill/sweep_probe.py` probe config variant `--carry` (the flag already exists in `train.py` for layered arms); no new trainer code.
- **mode:** process
- **prediction:** Carry probes show cross-seed sd ≤ 0.5× the standard probes' sd on the same entries, and the seed-0 verdict agrees with the 3-seed verdict on ≥ 4 of 5 entries (vs the standard chassis' agreement measured in the same pass). If both hold, carry becomes the screening chassis while the champion stays the adoption chassis.
- **kill test:** Carry probe sd ≥ standard probe sd at probe budget (the tight clustering was an 8-minute artefact), or verdict agreement is no better — carry is then closed as an instrument too, completely.
- **status:** queued

### FI-010 · Descending vote threshold 64 → 8 — the anneal failed hot-first; run it cold-first
- **source:** `RESULTS-2026-11-11.md` — annealed threshold 8→64 lost decisively: 3.850 ± 0.029 vs plain 3.074; diagnosis: "starting at 8 votes fires flips on weak early evidence… raising the threshold later cannot undo the early disorganization." The pool's schedules (MILL-204/205/206) all *rise* from 24–32; A-033 cycles; D-003 drops V late only inside a replay phase on hard windows. A plain descending schedule over the whole run has never run.
- **mechanism:** Inversion: the failure localizes the damage to the *early hot* phase, so reverse the direction — start strict (V=64: only overwhelming evidence flips while embeddings and scales are still forming) and end hot (V=8: late in the run, gradients are informative and the structure is stable enough to spend flips on fine corrections). Same start/end values as the closed arm, opposite order, different mechanism: the closed arm's sin was early disorganization, which this schedule is built to prevent.
- **train.py:** new flag `--votes-schedule 64-8` on the `Layered` trainer in `train.py` (linear V(step) from 64 to 8 over the run, counter clamp follows current V); sweep config `--arm layered_half --rope --votes-schedule 64-8`, 3 seeds × 8 min.
- **mode:** sweep
- **prediction:** Held lands ≤ 2.90 — far clear of the closed anneal's 3.850 and within reach of the 2.8580 champion — with early flip share (first 25% of steps) at most half the closed arm's ~2×-plain rate. Adoption is not predicted; the claim is directional: order, not endpoints, was the failure.
- **kill test:** Mean held ≥ 2.8990 (layered_half without rotary's record — i.e. no better than doing nothing) or early flip share is not visibly suppressed — descending V is just the anneal wearing its coat backwards, and V-schedules close in both directions.
- **status:** queued

### FI-011 · The duplicate-gap as a capacity gauge — leakage flattered every number; turn it into the ladder's memorization instrument
- **source:** `DATA-AUDIT.md` §4 — 30.8% of v1 pieces are exact-duplicate copies and held windows come from the same stream, so "all v1 held losses are flattered by an unknown amount." E-019 removes the leakage to price it; this entry *keeps* the leakage and reads it.
- **mechanism:** Inversion: the flattery is not uniform — it is a measurement of memorization, and memorization capacity is exactly what the scale ladder's 10M/50M rungs claim to add. Partition the 128 held windows into duplicate-tainted (content also present in the training stream) and clean windows, and report the per-rung **duplicate-gap** (clean held − tainted held) for the champion chassis and one 10M rung. If bigger ternary models memorize more, the gap widens with size — a capacity signal that costs no new training data and is invisible in the single pooled held number everyone currently quotes.
- **train.py:** evaluation-only — new `--dup-split-held` reporting in `train.py`'s eval (tag each held window by exact-line overlap with the training stream per DATA-AUDIT §4's method; report both slice losses alongside the pooled number) on one fresh champion run and one `--dim 512 --layers-n 3` layered+rope run at ladder steps.
- **mode:** process
- **prediction:** Champion duplicate-gap is 0.05–0.20, and the 10M rung's gap is visibly larger (≥ 1.5×) despite its worse pooled loss — i.e. the big rungs are spending their capacity on memorization the pooled number hides. Future ladder verdicts should quote both slices.
- **kill test:** Gap < 0.05 at both sizes, or non-monotone in size — leakage flatters everyone equally, carries no capacity information, and E-019's excision is the only duplicate experiment worth its cost.
- **status:** queued

### FI-012 · ±2 levels as a free abstention signal — the population that earned nothing as capacity may earn something as confidence
- **source:** `RESULTS-2026-11-11.md` — after 8 minutes only 1.7% of layered weights sat at each of −2/+2, and `RESULTS-HALF-CONTROL-2026-11-12.md` showed those levels earn nothing for loss at equal size/steps. FI-003 splits the components; this entry reads the *level distribution itself*, a signal no pool entry uses.
- **mechanism:** Inversion: a weight that fought its way to ±2 holds stronger accumulated evidence than one at ±1 or 0. Even if that extra evidence doesn't lower loss when summed into the weight, it may *mark* the windows the model understands: per-window, the share of active ±2 weights is a zero-cost confidence score computed from state the trainer already maintains. Test it as an abstention signal: rank held windows by ±2-share and check whether loss is monotone in the ranking (selective prediction — answer confidently on high-±2 windows, flag the rest).
- **train.py:** evaluation-only instrumentation in `train.py` — during the standard held evaluation of a layered_half + rotary run, log per-window loss and per-window ±2-active share (weights with |level| = 2 participating in that window's forward); report Spearman correlation and the loss of the top-half vs bottom-half windows by ±2-share.
- **mode:** process
- **prediction:** Spearman ρ ≤ −0.3 between ±2-share and per-window loss, and the top-half-by-±2 windows beat the pooled 2.8580-equivalent per-window loss by ≥ 0.15 — a usable confidence readout from a population currently treated as waste. A flat readout at probe scale but a strengthening one in FI-008's 160-step run would tie the signal to level population, as the 1.7% figure suggests.
- **kill test:** |ρ| < 0.2 on the champion run — the levels carry no confidence information either, and ±2 joins the closed list in every role: capacity, ensemble member (pending FI-003), and signal.
- **status:** queued

---

## Lens coordinator's note

The pattern across all twelve: this lab's failures are rarely *noise* — they are
consistent, directional, and therefore informative in reverse. Carry is consistent
(sd 0.0030). The say's bias is consistent (exactly one thing traded, every time).
The swapped blindness is *perfectly* consistent (0.0 in 11 of 11). Cooldown's
starvation is consistent (every seed worse than every baseline seed). Systems that
fail this cleanly are usually succeeding at a different job than the one they were
assigned — each entry above simply reassigns the job and charges the failure's own
consistency as the evidence.

**The inversion I believe in most: FI-001 (JEPA as initializer).** The JEPA record
contains its own contradiction — prediction loss down 4–5×, representation diversity
*up*, no collapse, yet probe CE identical to random init (−0.0017). Probes read what
is linearly available at the end; initialization spends what is geometrically
available at the start. Those are different currencies, the saved trunks make the
test nearly free, and it is the only entry here that can convert a closed headline
loss into a win without re-running the closed experiment.

*Closing coordination check: `mill/CANDIDATES-E.md` was re-checked immediately
before this file was written — present, unchanged (31,839 bytes). No FI entry
duplicates an E entry; where both touch the same failure (JEPA, the say,
swapped-operands, growth, cooldown, carry, corpus), the E entry repairs or diagnoses
and the FI entry reassigns the failing mechanism to a new job.*
