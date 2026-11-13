# Muse's work — Muse's side

# Wave 5 · Lens 1 (Prioritization) — The Attack Order

<!-- Muse's work — Muse's side of the BitNet lab. Rotation-5 miner 1, prioritization lens.
Input: CANDIDATES-F (66) + G (72) + H/WH (72) + I (60) = 270 unmerged candidates, on top of the
368-entry IDEA-POOL and CANDIDATES-A..E. Law: mill/PROMOTE.md. Nothing here merges anything;
this is the order the pool owner should merge/test in. -->

## The budget arithmetic that decides everything

- Probe = 75 s, trial = 24 min (3 seeds × 8 min), one full pool pass ≈ **7.7 h at the current
  368 entries**. Probing all 270 newcomers costs **270 × 75 s ≈ 5.6 h of probes per pass, per
  generation** — before a single trial — and roughly doubles every future pass and every
  generation re-screen. Merging everything is not a plan; it is a doubling of the mill's rent.
- Therefore the order below is bought with three rules, applied without exceptions:
  1. **Mill-changes that cut the price of every later verdict go first.** A futility stop and a
     probe ladder pay on all ~638 entries, forever; no single arm does.
  2. **Eval-only before training.** Readouts, censuses and diagnostics on weights/checkpoints
     that already exist cost minutes and several carry the largest predicted deltas in the
     waves (G-027: −0.02..−0.06; G-036: −0.03..−0.08). No 24-min trial should be bought while
     a ≤3-eval-pass readout on the same weights is still unrun.
  3. **A probe must be able to kill its entry.** Entries whose own file says "~0 at probe by
     construction" (F-002, F-004, F-006, WH-002-class late actors) do not get funnel slots;
     they wait for a named human to send them straight to trial under PROMOTE.md's exception
     logic, or they wait forever. The probe bar (Δ ≥ 0.05 promote / 0.02 near) is a screen,
     and an entry the screen cannot see is not "promising", it is unscreened spending.
- Dose families: **one dose first** (the family's central point), siblings only on a signal.
  Running three doses of a dead family is the pool's most common way to burn 3 probes learning
  one fact. This is also why G-066-style sequential dosing, where adopted, outranks doses.

Cost classes: **sweep** = runs in the shared-data sweep, cheapest probe · **process-flag** =
one new flag/arm + isolated 75 s probe · **eval-only** = no training run (readout / census /
analysis on existing state) · **full-trial-only** = no honest probe exists, the first real
reading costs 24 min · **mill-change** = changes screen.py/PROMOTE machinery, judged in
probes/hour or trial-hours saved, not held loss.

---

## The top 40 — merge/test in this order

| # | id | cost | Why this slot |
|---|----|------|---------------|
| 1 | G-037 | mill-change | Futility stop: if trial seeds 1–2 both miss the reference mean, the ≥2-of-3 per-seed guard makes seed 3 mathematically unable to adopt — skipping it saves 8 min per doomed trial at zero false-rejection risk. Pure arithmetic, pays from the mill's first trial. **Absorbs G-063** (same derivation, twice-found); G-063's stale-guard control folds into this entry, it does not get its own slot. |
| 2 | G-038 | mill-change | Multi-fidelity probe ladder: stop spending a uniform 75 s on ideas that die in 30 s. At 638 entries/pass this is the single largest probe-budget lever available; every rank below this one gets cheaper the day it lands. |
| 3 | G-026 | eval-only | Counter-resolved readout: final counters sit clamped at ±32 and are discarded unread; resolving pending flips (|counter| ≥ τ) before install costs ≤3 eval passes on existing weights, predicted −0.01..−0.04. Free information that provably exists. |
| 4 | WH-051 | eval-only | Frustration census: exactly computable from one state dump, no eval pass, no fitted model — and it *measures the population F-001 wants to reroute* (predicted 4–8% in champion-family runs vs >15% catastrophe-class). F-001's effect size is a guess until this lands; it also doubles as a halfway kill signal for doomed trials. |
| 5 | F-043 | sweep | Vote-threshold scaling law (V must fall as N rises): flip share already fell ~5× from 0.885M→10M at fixed V=32; if real, every ladder rung above 2M is being measured against a near-frozen trainer — the most expensive silent error in the lab. Cheap sweep at 10M (V ∈ {32,16,8,4}) with 2M as flat negative control. Gates F-051/052/053 and all scale claims. |
| 6 | G-039 | mill-change | Two-stage promotion gate: a 75 s second-seed repeat before any 24-min trial. Probe noise at 75 s is ≫ the 0.0161 full-format sd; this is the cheapest insurance against spending trials on seed-0 luck. **Picked over G-062** (banded second seed — same purchase, narrower); see deferrals. |
| 7 | G-044 | mill-change | Near-band auto-extension: PROMOTE.md parks every 0.02 ≤ Δ < 0.05 entry for a human who may never come. Resolving the near band at 3 min converts a growing graveyard of maybes into verdicts at 1/8 of a trial's price. |
| 8 | G-025 | eval-only | Per-layer install-scale calibration: post-hoc log_scale line search on trained weights, predicted −0.015..−0.05 vs 2.8580 on the *same* weights. The proxy gradient ignores downstream response; a direct search is the honest price, and it is eval-only. Runs after G-026 so the two readouts don't confound each other's baseline. |
| 9 | E-018 | full-trial-only | **The one A–E straggler promoted into the top 10.** Corpus-v2 re-baseline: every mill verdict is denominated in v1 held loss, which the data audit proved is flattered by duplicate leakage of unknown size. One 3-seed run (24 min) converts "unknown" into the honest champion number every future series is judged against. Expensive, indivisible, and worth more than any ten arms measured in a rigged currency. |
| 10 | F-055 | process-flag | The reservoir control: freeze all ternary weights at random init, train only the FP parts. One probe prices what vote training itself earns — the whole program's effect size, currently unmeasured. Also the kill-test anchor for F-061 and every "is it just the FP parts?" doubt. Killed if ≥ job-zero + 0.30. |
| 11 | G-027 | eval-only | Checkpoint logit-ensemble: average predictions, not weights — predicted −0.02..−0.06, the largest single expected delta in wave G, at eval-only cost on checkpoints that already exist. If it wins, it also reprices what a "champion" should ship. |
| 12 | WH-015 | eval-only | Post-training vocab excision + tail merge: step (a) returns 420,864 served bytes (−11.1%) at *exactly* 0.000 nats by construction, on already-trained champions, today. The only guaranteed-positive entry in all four waves. Zero-risk component first, priced merge second. |
| 13 | I-001 | process-flag | Init-seed × stream-seed factorial: one `--seed` currently welds init and batch stream together, so the champion's ±0.0161 sd has never been decomposed. Every verdict the lab has issued inherits that ambiguity; a handful of probes unwelds it (needs the seed-split flag). Stream share predicted ≥60% at probe scale. |
| 14 | F-001 | process-flag | Boundary-pressure rerouting — wave F's coordinator #1, on merit: outward votes on saturated weights are provably destroyed signal, and log_scale is the one continuous channel it can exit through; predicted −0.02..−0.05 at trial scale. Sequenced *after* WH-051 (#4), which prices its target population, and *before* its bracket sibling F-016 (#31). |
| 15 | WH-037 | eval-only | Serving fault injection — wave H coordinator #1: ternary flips predicted graceful (1% → +0.03..+0.10) but one exponent-bit flip in a single FP log_scale predicted at Δ ≥ +0.5. If true, hardening priority inverts for everything the lab ships: protect a few hundred FP scalars first, at ~zero cost. Eval-side, on copies of trained state. |
| 16 | G-001 | process-flag | Per-part lr ratio (scales 3e-3 / embedding 3e-4 / norms 1e-3) — wave G coordinator #3: five prior entries only ever moved one global lr for parts differing by ~5 orders of magnitude in count; the ratio was never tested, predicted −0.02..−0.05, and the plumbing unlocks G-005/G-007 in the same pass. A flat result here *plus* flat MILL-304 retires the whole lr family with a reason. |
| 17 | F-007 | process-flag | Counter-confidence install: the counter modulates forward magnitude. Rare and valuable property — it acts from the first counter movement, so unlike most of wave F it is **probe-honest** (−0.02..−0.05 predicted at probe *and* trial scale). Probe-honest entries with top-quartile predictions jump the queue; that is the funnel working as designed. |
| 18 | I-011 | eval-only | Frequency-binned held: report what the 2.8580 is *made of*. No entry in the union slices held by target-token frequency; the lab does not know which frequency band any arm's Δ lives in. Eval-only re-slicing of existing evals — after this, a dozen pooled arms become interpretable retroactively. |
| 19 | WH-049 | eval-only | Counter-histogram forecast: predict final held from the counter field at 25%/50% (target: leave-one-arm-out R² ≥ 0.7, MAE ≤ 0.03). If it works, the worst third of trials die at half price forever — a mill-change in effect, bought at analysis-script cost. Ranked below WH-051 because it must be *fitted and validated*, where the census is exact. |
| 20 | F-031 | process-flag | JEPA-as-initializer ★: the JEPA trunks already exist on disk; starting vote training from one is the only entry in any wave that can *overturn a headline verdict* (JEPA = nothing) rather than merely price it, and the test is cheap because the expensive half was paid in 2026-11-12's JEPA runs. Win condition pre-stated (≥0.03 over random init at equal steps). |
| 21 | F-033 | eval-only | Split the layered stack into an ensemble: the half-control proved the five levels earn nothing *summed* (2.8990 vs plain 2.9010); separation instead of summation has never been tried. Zero training cost — checkpoints + one eval path. Directly follows from the lab's own retraction, which is exactly where untested arrangements hide. |
| 22 | WH-014 | process-flag | Embedding rows join the vote trainer — wave H coordinator #2: the tied table is ≈83% of served bytes (3.81 MB → ~0.86 MB if it works) and no embedding row has ever voted. Largest byte prize in the waves, with a pre-stated per-byte bar (≤ +0.05 nats wins, ≥ +0.12 kills the family). Its verdict gates WH-016/006/007-class follow-ups. |
| 23 | G-036 | eval-only | Cross-seed logit ensemble: the champion's own three trial seeds as the ensemble, predicted −0.03..−0.08 — the largest ceiling in wave G. Ranked below G-027 deliberately: serving cost is 3× bytes / 3× forward, so even a win is a *pricing* result, not a shipping candidate. Buy it eval-only, know the number, don't pretend it's free at serve time. |
| 24 | WH-013 | sweep | Vocab 2048 at the champion — the down-dial nobody has run, at the scale where the table is 83% of served bytes. One refit + one run sets the dial's direction for the whole vocab family. **Picked over its dose siblings** WH-020 (8192) and WH-022 (1024): direction first, dose curve only if the direction pays. |
| 25 | F-005 | process-flag | State-stratified gate: the median computed within each ternary state. Probe-honest (−0.01..−0.04 at probe and trial, bias acts from step 0) and mechanistically orthogonal to F-001/F-007 — it questions the gate's *population*, not the counter or the install. |
| 26 | G-014 | process-flag | Sequential stream walk (read the corpus, don't sample it) ★: the data-order entry with a real mechanism — coherent evidence instead of resampled fragments. Also a parent of I-015 (#39); it must have its own probe record before any combination containing it is interpretable. |
| 27 | WH-001 | process-flag | FFN width skew, late-wide (512→1024) at *exactly* 884,736 ternary / identical served bytes: width sits where flip share is highest instead of being split by symmetry; predicted −0.02..−0.06 vs the equal-budget champion. **Picked over WH-008** (the reverse skew): WH-008 runs only as WH-001's kill condition (if reverse beats it, the flip-share story is backwards) — one slot, both answers. |
| 28 | WH-025 | process-flag | Deep supervision: block-1 same-token auxiliary head (t+1, not the pooled t+2 MTP) — the densest new CE signal per unit compute in wave H, predicted −0.02..−0.05 at trial, −0.01..−0.03 at probe, acts from step 0 with no horizon needed. Probe-honest aux signal; the pooled MTP entries (MILL-123/124) never tested this form. |
| 29 | I-003 | process-flag | Per-projection gate: Q, K, V stop sharing one median inside the fused qkv. A verified negative-space gap — three roles with different gradient distributions have shared a single gate statistic for the lab's entire history; predicted −0.01..−0.03 at probe and trial. Small flag, structural blind spot. |
| 30 | G-002 | process-flag | Flip-servoed continuous lr: AdamW speed follows measured flip share (clip 0.5–2.0×) instead of a clock. The cooldown record's own diagnosis was FP parts starved while the ternary side kept moving; F-037 answers with a clock, this answers with the signal itself. Predicted −0.01..−0.04, and its φ-vs-loss-slope diagnostic is logged either way. |
| 31 | F-016 | process-flag | Anti-windup: conditional integration at the saturated boundary — F-001's deliberate bracket sibling (stop integrating destroyed pressure vs reroute it), predicted −0.01..−0.04. Runs second in the pair: together they price the defect *and* the two fixes; alone, F-001 is the better bet because it recovers signal instead of discarding it more carefully. |
| 32 | I-038 | eval-only | Layer-sweep greedy coordinate descent (one BitLinear layer at a time, post-training): wave I's own "best value in the file" (21 EP), predicted −0.02..−0.05, every accepted move jointly measured in the only subspace where its renormalisation side-effect lives. **Picked over I-037** (tabu batch, 97 EP) and I-039 (recombination, 121 EP) — same discrete-search family, a fifth of the price; see deferrals for what would reverse this. |
| 33 | G-049 | full-trial-only | Two plain bodies, one shared embedding — an ensemble at *exactly* the champion's bytes, predicted 2.82–2.86 at trial format, beating each body solo by ≥0.03. No honest probe exists (two trainings + ensemble eval), so it pays full price — but it is the only exact-bytes composition test, and G-036 (#23) will already have priced the ensemble ceiling at 3× bytes. |
| 34 | G-050 | full-trial-only | Counter-sum merge (merge in latent counter space L = 32·t + c, ship one model at champion bytes) — wave G's boldest entry, paired verdict with G-053 as its built-in control. "Do counters merge better than weights?" is a founding-mechanism question with one clean experimental answer; it needs donor runs, hence full-trial-only. |
| 35 | I-012 | eval-only | Position-binned held: locate rotary's win inside the window (predicted ≥60% of the pooled −0.0411 sits in buckets 128–255). Eval-only, and it retroactively explains the lab's one confirmed win — knowledge that shapes every future position/curriculum entry (F-013, I-007/008, G-017/018/023). Ranked below I-011 only because frequency ignorance currently costs more than position ignorance. |
| 36 | I-026 | eval-only | Saturation creep census: counters outlive the model that earned them, and *all* current verdicts are issued in the one regime where counters are young — systematically underpricing leak/layered arms and overpricing front-loaders. Logging-only census on runs the mill already executes (with I-025 as its action arm if the census bites). Near-zero marginal cost for a bias warning on the whole ledger. |
| 37 | F-003 | process-flag | Orthogonal second channel: t2 votes on the gradient *innovation*. The half-control showed two summed components feeding on near-identical evidence earn nothing; this is the one wave-F entry that makes the second component's evidence actually different. Predicted −0.02..−0.06 at trial, −0.00..−0.02 at probe — trial-leaning, but the mechanism directly addresses a *measured* null, which earns it the slot over fresher speculations. |
| 38 | WH-002 | process-flag | Decoupled sublayers (A–F–A–F) at exactly 884,736 ternary / identical served bytes, predicted −0.01..−0.05: four norm/residual boundaries instead of 2×2 fused, second attention reads FFN-processed features. Its own file warns a flat probe does not kill it — accepted here because the budget is *exact* and the shape question (fused vs decoupled) is otherwise completely unowned in the union. |
| 39 | I-015 | process-flag | G-014 × F-022 (stream walk × Benna–Fusi cascade) — the **only** second-order combination admitted to the top 40: each member's filed prediction names the other's absence as its limiting factor, predicted −0.04..−0.08 against two-sided singles. Sequenced after G-014 (#26) has a solo record; F-022 must also be probed solo in the same pass or this entry's result is unattributable and should be voided. |
| 40 | G-030 | eval-only | Counter-soft install: fractional pending evidence through the forward rounding boundary, predicted −0.005..−0.03, expected ≥ G-026 if graded evidence beats a hard threshold. The natural closing entry: it is G-026's dose/shape successor, eval-only, and the pair together prices the readout band completely. (G-035, measured flip polish, is next in this family — it does not get a slot until G-026/G-030 read.) |

**First reserve (41st): E-013 · Level-population dynamics** (eval/logging-only) — does the
±2 population ever wake up (1.7% → ≥6% by 40 min, or plateau ≤2.5% by 20 min)? It gates E-014
and the entire layered-at-longer-budgets question. It misses the 40 only because I-026 (#36)
covers the adjacent long-horizon ignorance at even lower cost. If any top-40 entry dies in
preflight, E-013 takes its slot — no re-ranking debate needed.

**What the top 40 costs:** 5 mill-changes (one-time), ~14 eval-only (minutes each), 2 sweeps,
16 process-flag probes (16 × 75 s ≈ 20 min of probing), 3 full-trial-only entries (3 × 24 min).
Total first-pass exposure ≈ **under 3 hours** to first verdicts on all 40 — versus ≈ 5.6 h of
probes alone for the unranked 270, with nothing learned about the mill itself.

---

## Defer / retire on sight

### Retire as duplicates or superseded (do not merge as separate entries)

| id | verdict | Reason |
|----|---------|--------|
| G-063 | **RETIRE — duplicate** | Sequential trials / spend seed 3 only when it can change the verdict: independently derived twin of G-037 (wave G's own method note says so). Merge as G-037 plus G-063's stale-guard control detail. Two entries, one theorem. |
| G-062 | **RETIRE — superseded by G-039** | Banded second seed is the same purchase as the two-stage promotion gate, restricted to a band. G-039 (#6) covers the decision point where the money is spent. *What would change my mind:* evidence that false promotions concentrate specifically in the 0.02–0.05 band and nowhere else — then the banded form is the cheaper sufficient tool. |
| G-053 | **RETIRE as standalone — demote to control arm** | Ternary majority soup (merge final states, counters discarded) is strictly dominated by G-050 (#34), which was filed *paired with it* as its control. Run it inside G-050's experiment where it earns its keep as the comparison; as an independent pool entry it buys the same donor runs to answer a worse question. |
| G-028 | **RETIRE as standalone — fold into G-027's eval batch** | Logit temperature on the readout: one scalar fitted on cached logits. It can ride along inside the G-027/G-036 readout sessions for seconds; as its own entry it would consume a queue slot, a ledger line and a report sentence out of all proportion to one scalar. |
| I-060 | **RETIRE** | Nibble-packed counters forcing V=7: its own prediction is "within ±0.01 of MILL-502 (V=8), i.e. likely worse than the V=32 champion by whatever V=8 costs". It prices a packing nobody will ship at a threshold the grid already condemns. Cost ≫ information, by its own arithmetic. |
| I-050 | **RETIRE** | Lane-local gate: predicted throughput +0..+2% end-to-end, by its own entry because the vote update is a few percent of step time. A kernel-semantics flag, a probe, and a trial-risk surface in exchange for a rounding error. |
| WH-072 | **RETIRE** | The library analogue, filed by its own lens *priced as a negative control* (counter-archive restore on flip-back). The lab already owns this lesson from the growth-cycle rollbacks; a negative control for a settled question is not an experiment. |
| F-065 | **RETIRE** | Backwards rotary (positions reversed, text forward): a wild card whose mechanism fights the one confirmed win in the record (rotary, −0.0411) with no compensating hypothesis at ctx 256. Wild cards earn slots by having a kill test that teaches something (F-061 has one; this one's "win" would be uninterpretable noise-chasing). |

### Defer — real ideas, wrong time (named trigger for each)

| id | Trigger to un-defer |
|----|---------------------|
| **F-002** · Weak-half slow counter ★ | **The deferral I would defend hardest — see below.** Un-defer only on a named human sending it straight to trial as a PROMOTE.md exception, with F-043's scaled-V interaction (I-018) answered first. |
| F-040 · Descending V 64→8 | Cold-first anneal is still the anneal family: the 8→64 form is *closed*, and reversing a closed schedule's direction is a retest of a closed question wearing a new sign. Un-defer only if F-043's scaling law shows V's *level* matters far less than its *trajectory* — currently no evidence says that. |
| F-061 · Scalar-feedback votes | Its own kill test is defined relative to F-055's reservoir probe ("retires if within 0.02 of F-055"). Until F-055 (#10) lands, F-061 is literally uninterpretable. Un-defer the pass after F-055 reads. |
| I-013..I-024 (all combinations except I-015) | Combining two unmeasured parents produces an unattributable number whatever it shows. Each un-defers individually once *both* parents hold probe records. I-013 (F-001 × F-024) is the worst offender: it deletes and rebuilds per-row the very exit channel F-001 creates — a combination that can destroy its parent's mechanism before the parent is measured. |
| I-037 · Tabu batch search | Deferred behind I-038 (#32), same family, ~5× the evaluation points (97 EP vs 21 EP). *What would change my mind:* I-038 stalling at a plateau its own trace attributes to flip *interactions* within a layer — that is precisely the failure tabu batch prices and layer-sweep cannot see. |
| I-039 · Checkpoint-population recombination | Highest ceiling in wave I (−0.03..−0.08) and highest price (121 EP). Deferred behind I-038 for the same reason; un-defers if I-038's accepted-move rate is still healthy at exhaustion (evidence the discrete surface is rich, not picked clean). |
| I-048 · (1+λ) unguided evolution | Its own honest prediction is that most of its apparent gain is selection noise its ship rule vetoes. A control that predicts its own null does not get a standalone slot; it runs, if at all, inside I-037/I-039's budget as *their* control. |
| G-052 · Three independent seeds vs one bigger model | Pays 3× full price to answer an ensemble question G-049 (#33) answers at exactly the champion's bytes. Un-defer only if G-049 wins *and* the follow-up "was it the ensembling or the sharing?" is the lab's actual next question. |
| G-035 · Measured greedy flip polish | Correctly self-ranked below G-026/G-030 by its own lens. Un-defers the moment both readouts land; running it before them spends verified-flip budget without knowing whether counter rank even correlates with flip value. |
| WH-006 · FP block placed FIRST | Placement is a two-point question and only one point needs buying first: WH-003 (FP last) has the prior (last block writes into final norm/head geometry where coarseness can't be corrected downstream). WH-006 un-defers only as WH-003's kill/control arm if WH-003 shows *any* signal. Neither makes the 40 because WH-014 (#22) is the better mixed-precision bet at this scale — it attacks 83% of bytes, not one block's placement. |
| WH-020 / WH-022 · Vocab 8192 / 1024 | Dose siblings of WH-013 (#24). Direction first; a three-point dose curve for a dial whose direction is unknown is two wasted runs in two of three worlds. |
| F-051 / F-052 / F-053 / F-054 · 50M-scale entries (vocab 16384, iso-weight shape reversal, recurrent depth, depth-graded freezing) | All four presuppose a 50M rung that does not exist and a V-scaling answer F-043 (#5) hasn't delivered yet. At fixed V=32 most 50M weights would never flip — these would measure a frozen trainer and call it architecture. Un-defer in order after F-043 lands and a ≥10M rung is real. |
| F-064 · The 70% zero cull | Imposing a histogram the training dynamics never chose, against WH-033's homeostatic family which defends ~42% — I-024 already files their collision. Un-defer as that collision experiment (I-024), not as a standalone cull, and only after WH-051's census says what the natural zero fraction actually is. |
| I-055 / I-057 / I-059 · Throughput micro-entries (stochastic-rounding accumulation, stale-forward pipelining, int8 body→head) | Honest small beer, by their own entries: 2.7 MB saved, throughput ≈ "the install share only" on a serial VM, logit-error arithmetic with no quality claim. On a 1.5-CPU VM where the mill is *preempted* by the ladder and growth cycles, throughput micro-opts solve a bottleneck the lab does not currently have. Revisit if the pool ever becomes throughput-bound rather than idea-bound. |
| A-004 / A-008-class A-wave vote-statistic variants (as a family) | Not undervalued — *over*-represented. The pool already carries the vote-statistic dial (gate scope/quantile/threshold families, MILL-601..654) at far finer grain than CANDIDATES-A's early entries; F-005/F-017/I-003/I-005 attack the same statistic with sharper mechanisms. The A stragglers worth money were the ones FLAGS-BUILT already made runnable; the rest wait for the F/I gate results to show which sub-dimension is still open. |

### The deferral I would defend hardest: F-002

F-002 (weak-half slow counter, V_slow = 128) is a lens-★ entry with a respectable
predicted −0.01..−0.04 — and it should not be merged now, for one structural reason:
**its own entry states it is ~0 at probe scale by construction** (128 net weak votes
cannot accumulate in ~25 probe steps). Under PROMOTE.md the probe is the only screen
the mill has; an entry the screen cannot see can only enter by consuming a full
24-min trial unscreened, on a human's say-so. That is sometimes right (the exception
list exists for it) — but F-002 hasn't earned the exception, because wave I filed its
executioner: **I-018 shows that at the lowered V which F-043's scaling law demands,
the slow counter is reset to death** — the two wave-F darlings are mutually hostile,
and until F-043 (#5) reads, nobody knows at which V F-002 would even be trialled.
Spending the trial first and the 75-second scaling sweep second is exactly backwards.
What would change my mind: F-043 landing flat at 10M (V's level doesn't bind, so the
I-018 interaction evaporates) *and* a probe-format variant of F-002 with V_slow
lowered enough to flip within a probe — i.e., evidence the mechanism can be *seen*
cheaply at some setting. Absent both, F-002 stays deferred no matter how good its
story is; the funnel exists precisely for stories this good.

---

*End of wave-5 lens-1 priorities. Ranked: 40. Deferred/retired: 8 retired outright,
2 retired-as-standalone/demoted to controls, 15+ deferred with named triggers,
1 A-wave family held. First reserve: E-013.*
