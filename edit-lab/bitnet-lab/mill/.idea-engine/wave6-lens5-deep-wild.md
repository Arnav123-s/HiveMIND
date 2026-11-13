# WAVE 6 — LENS 5: DEEP WILD (Muse's work — Muse's side)

<!-- Muse's work — Muse's side of the BitNet lab. Idea Engine rotation 6, miner 5.
Targets are the field's NEW assumptions — premises waves F–J created, not the ones they
attacked. Deduped against mill/IDEA-POOL.md and CANDIDATES-A/B/C/D/E/F/G/H/I/J +
FABLE-CANDIDATES.md. Nothing closed is re-proposed in its original form: no overshoot
carry, no AdamW cooldown, no threshold anneal 8→64, no magnitude votes as specified,
no JEPA objective. Chassis/bars as in waves F–J unless an entry changes the chassis or
the corpus: champion layered_half + rotary, held 2.8580 ± 0.0161 (v1); probe = 75 s /
seed 0 vs that pass's job zero, verdicts in Δ vs job zero, exactly as wave F's wild
cards (F-055..F-066) were judged. Every entry states its premise bet: which F–J premise
must be FALSE for it to pay, and what it is worth in that world. -->

## Coordinator's top 3 ★

1. **DW-003 · Lottery flips (counters deleted)** — the design for the world where
   J-002's statistics-only rival wins: if per-weight counter ownership is bookkeeping,
   the honest trainer keeps no counters at all and spends the field's flip rate by
   lottery among gated weights. Zero counter bytes; ties-or-dies in one probe.
2. **DW-009 · Tiny-loop scarcity diet** — v3 landed (~21.4M pieces) on the assumption
   that more unique data is the fix; a vote counter that needs ~32 net agreeing votes
   per flip may instead be *starved* by uniqueness. A 512-window loop, repeated, is the
   opposite pole from every coverage/deck entry in the pool — and the cheapest v3 test
   in this file.
3. **DW-011 · Vote-trained ternary RNN (no attention, no RoPE)** — every entry in six
   waves searches inside one architecture family. This exits it: the vote mechanism
   transplanted onto a recurrent chassis at the exact ternary budget, so a loss is a
   priced fact about the family, not an assumption.

**Wildest entry with a real kill test: DW-003** — it deletes the mechanism's founding
object (the per-weight counter, ~2.2 MB of state on the champion) and predicts the
deletion is free if J-002's rival theory is true. Kill is one probe: ≥ job-zero + 0.15
and the design dies *and* J-002's memory theory gains its strongest corroboration.

---

### DW-001 · Boundary-pressure damping: saturated votes shrink the step, they don't feed it
- **premise inverted (cited):** F-001 — "gradient pressure is a conserved signal…
  whatever the discrete state cannot express must exit through a continuous channel
  or be lost," so outward votes on saturated weights are rerouted INTO `log_scale`
  as signal. **Premise bet: F-001's conservation premise is FALSE.** Outward pressure
  at a boundary is not conserved information; it is the signature of a weight whose
  evidence stream has gone one-sided — runaway, not riches. In that world F-001's
  rerouting amplifies exactly the layers that are already over-committed, and the
  correct exit for boundary pressure is *damping*: this entry is worth −0.02..−0.04
  there, and is predicted to lose by roughly F-001's gain in the world where F-001
  is right — the pair is a signed discriminator, run both.
- **mechanism:** when a strong vote argues for a boundary no-op (component at +1
  pushed +, or −1 pushed −), it does not increment any counter and does not feed
  `log_scale` positively; instead it adds to a per-layer pressure accumulator, and
  at step end that layer's `log_scale` is nudged DOWN by `0.02 × (net outward
  pressure / strong votes that step)` in log space — saturation literally shrinks
  the physical step the saturated weights take, until inward evidence re-earns it.
  Distinct from F-016 (anti-windup: outward votes are *ignored* — no signal used in
  either direction) and from F-001 (same votes, opposite sign of use).
- **exact change:** new flag `--boundary-damp 0.02` on Layered; accumulator is one
  float per BitLinear, no per-weight state; the AdamW update of `log_scale` is
  untouched, the two contributions sum (same wiring point as F-001, opposite sign).
- **mode:** process
- **prediction:** −0.01..−0.04 at probe scale if the damping world is real (boundary
  saturation exists from early steps per WH-051's census prediction of 4–8% frustrated
  weights); ≈ +0.02..+0.05 (a loss mirroring F-001's predicted gain) if it is not.
- **one-probe kill test:** retire if probe held ≥ job-zero + 0.02 — damping is then
  strictly worse than doing nothing with the pressure, F-001's direction stands
  unopposed, and this entry closes as its negative control.
- **status:** queued

### DW-002 · Boundary eviction: a saturated weight that keeps pushing outward is reset to 0
- **premise inverted (cited):** F-001 again, at the state level rather than the scale
  level — F-001 and F-016 both assume a saturated weight should KEEP its state and
  have its excess pressure rerouted (F-001) or ignored (F-016). **Premise bet: both
  are wrong about what saturation means.** A component pinned at its boundary while
  outward votes keep arriving is a feature claiming more magnitude than the code
  can express — the ternary answer to an over-claimed feature is not a bigger scale,
  it is eviction: free the slot to 0 and let the evidence re-earn a level honestly.
  Worth −0.01..−0.03 in that world; worthless (pure churn) if saturation is stable
  success, which the kill test prices.
- **mechanism:** each component carries a small outward-pressure count (int8): a
  strong outward vote at the boundary increments it, any inward or ordinary vote
  resets it to 0. At 16 consecutive outward votes the component's state is forced
  to 0, both its counters zero, pressure count zero. The weight must then climb
  from 0 on fresh evidence like any zero weight. Distinct from F-064's zero cull
  (uniform-random, population-fraction target, no evidence condition) and from
  thrash freezing (punishes *flipping*; this punishes *refusing to stop pushing*).
- **exact change:** new flag `--boundary-evict 16` on Layered (one int8 per
  component, +2 B/weight charged; eviction applied inside `step()` after the
  normal flip pass, logged as `evictions/step`).
- **mode:** process
- **prediction:** −0.01..−0.03 at trial scale, ~0 at probe (16 *consecutive* outward
  votes need a saturated population to exist). Side signature if real: evictions
  concentrate in ≤ 5% of weights, and evicted weights re-flip to a *different* level
  than they held in ≥ 40% of cases — they were mis-seated, not merely loud.
- **one-probe kill test:** retire if probe held ≥ job-zero + 0.03, OR if the logged
  eviction count over the probe is 0 (no population — the premise has no object at
  this scale and the entry is void, not wrong).
- **status:** queued

### DW-003 ★ · Lottery flips: delete the counters, spend the flip rate by lot
- **premise inverted (cited):** J-002's rival (A) — MEMORY-IS-THE-MECHANISM: "a weight
  improves because ITS OWN counter integrates ITS OWN evidence stream over time."
  **Premise bet: J-002 comes out for rival (B), STATISTICS-ONLY** — its filed
  prediction under (B) is held within ±0.015 of 2.8580 under a full counter shuffle
  every 10 steps. *Assume it failed for (A); this entry is the design that world
  asks for.* If ownership is bookkeeping, keeping 884,736 individual counters is
  ceremony: all the trainer needs is the counter *field's* one honest output — how
  many flips this step should spend — plus the gate's answer to *which weights are
  eligible*. In that world this entry is worth the champion's loss at **0 counter
  bytes** (vs 2,211,840 B of mechanism state), i.e. the vote trainer's state claim
  improves from "~1/10 of STE" to "~0", and every per-weight counter entry in the
  pool (leak, freeze, SPRT, cascade…) is re-read as field-statistics machinery.
- **mechanism:** no per-weight counters exist. Each step: compute the gated strong
  half as champion; the flip budget is `k = round(0.0011 × N)` flips (the champion's
  measured mean flip share, a field statistic); choose k eligible weights uniformly
  at random from the strong half (own RNG stream) and flip each one step in its
  current vote's direction (boundary no-ops skipped, budget not re-spent). V, clamp,
  and reset have no referent and are gone; AdamW parts unchanged. Distinct from
  J-002 (a *diagnostic* that permutes live counters — the counters still exist and
  still integrate between shuffles), from F-019 sortition (eligibility lottery, but
  counters integrate and decide), and from F-061 bandit votes (counters exist and
  are reinforced by a global bit; here there is nothing to reinforce).
- **exact change:** new trainer mode `--arm lottery --flip-share 0.0011` (Direct
  chassis, plain_half shape + `--rope`); trainer state for the ternary side is
  exactly the ternary states themselves.
- **mode:** process
- **prediction:** under premise (B): probe held within +0.05 of job zero — the field
  statistic plus the gate carries the result, ownership contributed nothing. Under
  premise (A): a collapse of +0.15 or worse, toward the F-055 reservoir direction.
  The band between (+0.05..+0.15) is the interesting residue: partial memory value,
  priced for the first time.
- **one-probe kill test:** retire if probe held ≥ job-zero + 0.15 — memory was the
  mechanism after all, the no-counter design is dead in one probe, and J-002's (A)
  gains a corroboration stronger than the shuffle itself (deletion ≫ permutation).
  A landing ≤ job-zero + 0.05 does NOT adopt it — it promotes it to a 3-seed trial
  against J-002's own ±0.015 band.
- **status:** queued

### DW-004 · Two-step memory: the counter is a 2-vote window, nothing older exists
- **premise inverted (cited):** the same J-002 premise as DW-003, attacked at the
  opposite design point. DW-003 bets memory is worth *zero*; the pool's whole
  long-horizon lens (I-025/I-026/I-033) bets the opposite failure — that banks go
  *stale*, i.e. old evidence is worse than no evidence. **Premise bet: the truth is
  between J-002's rivals — integration helps, but only over ~2 steps; everything
  older is staleness wearing memory's clothes.** In that world a V=32 bank is mostly
  a liability the lab has been pricing as an asset, and this entry (worth −0.01..−0.03
  there) beats both the champion and DW-003's amnesia.
- **mechanism:** each weight keeps only its last two gated votes (2 bits of history,
  packed). It flips one step when both votes agree in a direction that changes its
  state; any disagreement or abstention clears the window. No counter, no clamp, no
  threshold — the flip rule is "two consecutive agreeing strong votes." Effective
  evidence standard is ~2 net votes instead of 32, so flip share will run far hotter
  than the champion's 0.0011 — that heat is the treatment, logged, not tuned away.
  Distinct from the closed anneal family (a *threshold schedule* on a real counter;
  there is no counter here) and from F-022's cascade (two counters in series whose
  whole point is *longer* effective memory — this is its directional opposite).
- **exact change:** new trainer mode `--arm twostep` on the plain_half + rope shape
  (2-bit history per weight ≈ 0.25 B/weight, charged; gate q=0.5 unchanged).
- **mode:** process
- **prediction:** −0.01..−0.03 if short memory is the truth (fresh evidence, no stale
  bank, flips track the current model); +0.05..+0.15 if the 32-vote climb was doing
  real denoising — in which case flip share ≥ 5× job zero's is the expected
  signature and the entry dies by its own log as much as by its loss.
- **one-probe kill test:** retire if probe held ≥ job-zero + 0.05, OR if probe flip
  share ≥ 5× job zero's at flat-or-worse loss (thrash, not freshness — the 2-vote
  window was just a hot threshold, and V-schedule entries already own that axis).
- **status:** queued

### DW-005 · Max-witness votes: one token position decides, the other 8,191 are ignored
- **premise inverted (cited):** the evidence-aggregation premise shared by BOTH the
  champion (a weight's vote is the sign of the *summed* gradient over 8,192 token
  positions) and its filed inversion I-049 (vote-then-sum: per-token signs summed
  into a majority, τ = 5% net). Champion says magnitude-summed evidence; I-049 says
  democratic evidence. **Premise bet: both aggregation stories are wrong — evidence
  is *extremal*.** The positions that should move a weight are the rare ones where
  the model is decisively wrong about that weight's input; summing (either way)
  lets thousands of near-zero, near-random positions outvote the one witness that
  knows. In that world this entry is worth −0.02..−0.05, and I-049's detectability
  arithmetic (only p ≳ 0.55 majorities vote at all) is re-read as a *defect*: it
  silences exactly the minority-witness weights.
- **mechanism:** per weight per step, find the single token position maximising
  |upstream_t · x_t| (the largest-magnitude per-token gradient contribution);
  the weight's vote is that position's sign alone, admitted only if that maximum
  exceeds the layer's median of maxima (a gate on witnesses, not on sums). Counter,
  V=32, clamp, arbitration unchanged — only the evidence statistic changes, from
  a sum over positions to an argmax over positions. Distinct from A-013 (loss-
  *weighting* a still-summed gradient) and F-020 quadratic voting (a budget over
  weights within a step; positions are still summed inside each weight).
- **exact change:** new flag `--vote-mode maxwitness` on Layered (per-token
  products computed in the vote path as in I-049's sign-GEMM plumbing, reduced by
  argmax instead of sum; FP backward still runs for the AdamW parts, charged as
  in I-049, ≈ +15–20% step time).
- **mode:** process
- **prediction:** −0.02..−0.05 at equal steps if extremal evidence is real, with
  flip share *rising* vs champion (witnesses are less likely to cancel than sums);
  +0.03..+0.08 if aggregation was the denoiser — a single witness per step is the
  noisiest possible statistic and the loss will say so plainly.
- **one-probe kill test:** retire if probe held ≥ job-zero + 0.03 at equal steps
  (per-minute reporting alongside, per I-049's honesty rule — a per-minute-only
  loss with an equal-steps win does not kill it, it queues the step-matched read).
- **status:** queued

### DW-006 · Error-only counting: agreeing votes are discarded, only dissent integrates
- **premise inverted (cited):** the counting premise underneath the champion and
  I-049 alike — *every* gated vote increments the counter, so most of what a counter
  integrates over a run is confirmation: votes agreeing with the weight's current
  state, pushing it toward a boundary it may already sit at. **Premise bet:
  confirmation is not evidence.** A vote that says "stay" carries no information
  about where the weight should *go*; the counter's climb should be built only from
  votes that argue for change, and the current design dilutes them ~2:1 with
  applause. Worth −0.01..−0.04 in that world, concentrated late in the run (early,
  most weights are wrong, so dissent dominates anyway — the entry's own onset
  prediction). If confirmation turns out to be load-bearing (it is what holds
  correct weights at their levels against noise), the kill test shows it fast.
- **mechanism:** a gated vote increments the counter ONLY if its direction differs
  from the weight's current installed direction for that component (vote pushes
  toward a different level than the one installed); agreeing votes are dropped
  entirely — not rerouted (F-001), not damped (DW-001), simply not counted.
  Counters therefore measure *net pressure to change*, and a flip fires at V=32
  of pure dissent. Boundary no-op votes are a special case of agreement and drop
  with the rest. Nothing else changes.
- **exact change:** new flag `--dissent-only` on Layered (one comparison in
  `step()`'s vote loop: `inc *= (vote_dir != installed_dir)` per component).
- **mode:** process
- **prediction:** −0.01..−0.04 at trial scale; probe ~0 to −0.01 (onset is late by
  the premise itself — a flat probe does not kill, a *bad* probe does). Flip share
  falls 30–50% vs champion (half the stream is discarded); the claim is that the
  surviving flips are the informative ones, so loss per flip rises.
- **one-probe kill test:** retire if probe held ≥ job-zero + 0.03, OR if end-of-probe
  state histogram shows the zero-fraction moved > 5 points vs job zero (dissent-only
  counting collapsed the histogram toward 0 — confirmation was the scaffolding,
  premise dead on its own diagnostic).
- **status:** queued

### DW-007 · Eat the held set: at v3 scale the 128 windows are data, not a shrine
- **premise inverted (cited):** the founding discipline J-042/J-037 defend and price —
  held windows are never trained on, and 2.8580's authority rests on that purity.
  **Premise bet: the purity is a v1 ritual that v3's arrival made free to break.**
  On a ~21.4M-piece corpus, 128 windows are 0.15% of the stream; a *fresh*
  confirmation set (the PROMOTE offset-by-20 windows, never selected on) can take
  over judging duty at zero cost. If the held windows are ordinary data, eating
  them gains ≈ 0 and the lab learns its judge was replaceable all along; if they
  gain measurably on the *confirmation* set, the held windows were never ordinary —
  they were the most central slice of the corpus, and every "held measures language"
  claim (J-013's anatomy included) inherits that specialness. Either reading is
  worth one run; the entry is the only one in six waves that spends the held set
  itself instead of defending it.
- **mechanism:** on the v3 chassis (champion config, `--corpus v3`): the 128 v1-style
  held windows are added to the *training* stream at their natural rate; judging
  moves entirely to the confirmation windows (every-40th offset by 20 on the v3
  stream, excluded from training by the standard predicate). Control in the same
  pass: identical v3 run with held windows excluded as usual, judged on the same
  confirmation windows. The pair isolates "held windows as food" from "new judge."
- **exact change:** runner-level — `--corpus v3 --eat-held --judge confirm` vs
  `--corpus v3 --judge confirm`; no trainer change. Confirmation-set overlap with
  both training streams asserted 0, per the dream protocol's contamination rules.
- **mode:** process
- **prediction:** Δ(confirmation) between the arms within ±0.01 — held windows are
  ordinary, the shrine was empty, and future series may fold any spent judge into
  training once its replacement is seated. A Δ ≤ −0.02 (eating helps on an
  untouched judge) is the sensation outcome and re-opens J-042's leak pricing from
  the other side.
- **one-probe kill test:** retire if the eat-held arm's confirmation loss is ≥
  control + 0.02 (the held windows were actively *bad* food — e.g. the most
  duplicated, most memorised slice — and purity was protecting the trainer, not
  just the judge), or if either arm's confirmation-vs-standard held gap exceeds
  0.10 (the two judges disagree so much that no verdict transfers and the entry
  is void until J-030's bias curve explains it).
- **status:** queued

### DW-008 · Junk-only diet: train on nothing the lab calls language
- **premise inverted (cited):** J-013/J-047's shared assumption in mirror image —
  both anatomise held to ask how much of 2.8580 is junk, assuming junk is the
  *dilutant* and prose the substance. F-032 tests junk as a 25% *appetiser* before
  clean data. **Premise bet: nobody has tested junk as the whole meal, and the
  pooled judge may not be able to tell the difference.** If ≥ 35–45% of held
  targets sit in junk-class windows at mean ≤ 1.5 (J-013's own prediction), a model
  trained ONLY on dump/merges/boilerplate windows should score *respectably on the
  pooled judge* while collapsing on the prose slice — and the size of that gap is
  the most direct price ever put on "the held set measures language": it is worth
  exactly the junk-only model's pooled score. In the world where J-013's anatomy
  comes out flat (classes within 0.15), this entry is worth ≈ 0 and dies by its
  own kill test — stated in advance.
- **mechanism:** sampler restricted to windows whose dominant source class (J-013's
  offsets-sidecar classification) is numeric dump, `merges.txt` gibberish, or
  license/package boilerplate — 100% junk, whole run, champion chassis otherwise.
  Judged twice from the same run: pooled v1 held, and J-013's prose+lab+German
  slice (`prose_held`). No mixed phase, no clean steps — that is what separates it
  from F-032 (junk-*first*, then 75% clean, judged on v2 held).
- **exact change:** new sampler flag `--train-class junk-only` on Layered (class
  tags from the J-013 sidecar; step count matched to job zero, tokens-seen logged
  — the junk stream is smaller, repetition is part of the treatment and is counted,
  per the dream protocol's token rules).
- **mode:** process
- **prediction:** pooled held lands 3.05–3.35 (only +0.20..+0.50 worse than the
  champion despite seeing no prose at all) while `prose_held` lands ≥ 4.2 — the
  split, not either number, is the deliverable. If pooled lands ≥ 3.60 instead,
  junk carried less of the judge than J-013 predicts and the anatomy file needs
  re-reading before its licensed interventions are spent.
- **one-probe kill test:** retire if probe pooled held ≥ job-zero + 0.60 (junk-only
  is catastrophically bad even on its home judge — the pooled number was honest
  language measurement after all), OR if `prose_held` − pooled < 0.30 in the same
  probe (no split exists to price; J-013's premise and this entry die together).
- **status:** queued

### DW-009 ★ · Tiny-loop scarcity diet: 512 windows, repeated, beat 21M pieces seen once
- **premise inverted (cited):** the v3 premise — corpus-v3 (~21.4M pieces, G-024's
  construction) was built on "more unique data is the fix," the same assumption
  behind A-055 coverage-first sampling, G-021's without-replacement deck, and
  B-009's fresh-data scaling. **Premise bet: for a VOTE trainer the assumption is
  backwards.** A counter needs ~32 *net agreeing* votes to move a weight once; a
  stream of never-repeated windows gives each pattern one testimony, and
  testimonies from unrelated windows cancel inside the counter. Repetition is not
  memorisation risk for this mechanism — it is the only way evidence ever
  *accumulates*. F-048 discounts repetition (1/n per visit) on exactly the
  opposite theory; the pair cannot both be right, and v3 is the first corpus big
  enough to run the scarcity arm without the loop being the whole corpus. Worth
  −0.02..−0.05 at equal steps in the scarcity world.
- **mechanism:** on v3: before step 0, draw 512 legal windows once (seed-disciplined,
  held predicate applied) and train on that fixed loop, cycling in fixed order for
  the whole run — every window is seen ~10× in a 160-step trial. Control in the
  same pass: the standard broad v3 stream at equal steps. Everything else is the
  champion config. Distinct from D-001 mistake replay (a *phase* replaying
  *hard* windows inside a mostly-fresh run — content selected by loss, majority
  fresh) and from A-044 paired repetition (each window twice *in a row*, stream
  still broad): here the diet is total, loss-blind, and looped.
- **exact change:** new sampler flag `--stream-loop 512` (v3 path; loop drawn from
  legal offsets only, `held_overlap = 0` asserted; unique tokens U = 512 × 256
  logged beside tokens-seen T, per the dream protocol's counting rules).
- **mode:** process
- **prediction:** loop beats broad stream by −0.02..−0.05 on v3-native held at
  equal steps, with flip share ≥ 2× the broad arm's (evidence finally repeats
  enough to resolve counters) and train loss on *fresh* (never-looped) windows —
  logged separately, per the noise-chasing rule — falling with held, not against
  it. If fresh-window train loss falls while held rises, that is memorisation,
  the entry's own suspicion rule fires, and the scarcity story is dead even if
  the pooled number looks kind.
- **one-probe kill test:** retire if probe held ≥ broad-stream job-zero + 0.03 at
  equal steps, OR if the probe's flip share is NOT ≥ 1.5× the broad arm's (the
  accumulation mechanism never fired — repetition did not resolve counters, so
  any loss reading is uninterpretable and the premise has no object).
- **status:** queued

### DW-010 · Data annealing: the corpus SHRINKS on a schedule (100% → 50% → 25% → 12.5%)
- **premise inverted (cited):** the same v3 premise as DW-009, attacked in time
  rather than in diet. Every schedule in the pool anneals a *trainer* quantity
  (V, lr, temperature); the data pool itself only ever grows or stays fixed, and
  the one data schedule family (A-041..A-046 curricula) reorders a fixed pool.
  **Premise bet: DW-009's scarcity effect, if real, is a *late-run* effect** —
  early training wants breadth (find the structure), late training wants
  repetition (resolve the counters against a settled model). In that world a
  shrinking pool beats both the broad stream and DW-009's all-loop diet, worth
  −0.02..−0.04; if DW-009 wins outright instead, scarcity was a whole-run
  property and this entry's phase story dies — the pair is designed to split
  that difference. (This is a *data* schedule; it is not the closed vote-threshold
  anneal 8→64 — V never moves.)
- **mechanism:** v3 stream in four equal step-quarters with nested legal pools:
  quarter 1 draws from all legal windows; quarter 2 from a fixed random 50%
  subset; quarter 3 from a nested 25%; quarter 4 from a nested 12.5% (each pool
  a subset of the previous, drawn once at run start, seed-disciplined). By the
  final quarter each surviving window has been drawable for the entire run and
  is being re-seen at 8× its quarter-1 rate. Sampler-only; trainer untouched.
- **exact change:** new sampler flag `--data-anneal 1,0.5,0.25,0.125` on the v3
  path (nested pool construction at runner start; held predicate applied before
  nesting; per-quarter unique-token counts logged).
- **mode:** process
- **prediction:** −0.02..−0.04 vs the broad-stream v3 control at equal steps, with
  the gain concentrated in the final quarter's held slope (logged per 20 steps)
  and flip share rising quarter-over-quarter as pools shrink. A gain spread
  evenly across quarters would mean nesting did nothing a smaller fixed pool
  wouldn't — re-read as a DW-009 result, not this entry's.
- **one-probe kill test:** retire if probe held ≥ broad-stream job-zero + 0.02
  (at probe scale only the first shrink, to 50%, has room to act — if even that
  costs more than the flat band, the late-scarcity story starts from a deficit
  it is unlikely to repay), OR if quarter-2 flip share in the probe window does
  not rise ≥ 1.25× vs the control's same steps.
- **status:** queued

### DW-011 ★ · Exit the family: a vote-trained ternary RNN at the exact champion budget
- **premise inverted (cited):** the pool's founding scope choice, stated in
  IDEA-POOL.md's chassis paragraph and inherited by all six waves — the search
  space IS the Tiny transformer family (blocks, heads, RoPE, FFN), and waves F–I's
  architecture lenses (WH-001..WH-012 shapes, MILL-116/117 DeltaNet/RWKV hybrids)
  vary it from inside: even the "recurrent" entries keep attention blocks in a
  3:1 hybrid and keep the transformer as the host. **Premise bet: the vote
  mechanism has never been separated from its host.** If counters earn their keep
  by integrating sign evidence — a claim about *evidence*, not about attention —
  they should work on any ternary substrate; if they only work inside attention's
  gradient geometry, six waves of vote entries are priced facts about one family,
  not about a trainer. Worth, in the transfer world: a within-0.05 landing re-opens
  the entire architecture axis the pool closed by assumption, at every scale rung.
- **mechanism:** a plain Elman RNN: token embedding (tied, FP, as champion) →
  2 recurrent layers whose input and recurrent matrices are BitLinears trained by
  the *unchanged* Layered vote rule (same gate, V=32, counters, arbitration) →
  final norm → tied head. Hidden width set so total ternary = 884,736 exactly
  (width ≈ 300: per layer input 300×300 + recurrent 300×300, ×2 layers, solved at
  wiring and logged). No attention, no RoPE, no position table — position exists
  only as recurrence. BPTT through 256 steps at batch 32 is the honest cost,
  charged per-minute AND per-step; judged primarily per-step.
- **exact change:** new model class + arm `--arm rnn_vote --rope-off` in a companion
  runner importing the Layered trainer unchanged (the trainer already collects
  BitLinears wherever they live — that reusability is part of the test).
- **mode:** process
- **prediction:** per-step held 2.95–3.10 at trial format — worse than the
  champion's 2.8580 (attention is worth something; the entry does not pretend
  otherwise) but far clear of the F-055 reservoir floor direction, with flip share
  in the champion's band (0.0005–0.002). The deliverable is the *gap*: it is the
  first price ever put on the host family itself, and every shape entry in WH's
  lens is a claim that the answer is "small differences inside the family."
- **one-probe kill test:** retire if probe held ≥ job-zero + 0.25 at equal steps
  (the mechanism does not transfer at all — votes were attention's accessory, and
  the architecture axis closes with a number instead of an assumption), OR if
  probe flip share < 0.2× job zero's (the recurrent gradient stream starves the
  counters — vanishing evidence, a mechanism failure, not a family verdict; the
  distinction is logged either way).
- **status:** queued

### DW-012 · No attention at all: fixed-shift token mixing + vote FFNs (a mixer, not a transformer)
- **premise inverted (cited):** the milder half of DW-011's premise, kept separate
  because the two exits fail differently: WH-012 tapers attention *windows* per
  block and MILL-137/138 ration global blocks 3:1 / 5:1 — every filed entry keeps
  *learned* attention somewhere. **Premise bet: at ctx 256 and 0.885M weights,
  learned content-based routing may be the part attention is worst at** (coarse
  ternary QK logits, exponentiated — the fragility every QK entry in the pool
  works around), while its *mixing* job can be done by a fixed, parameter-free
  shift pattern that no gradient can corrupt. In that world removing attention
  removes the fragile part and keeps the useful part, worth −0.01..−0.04; in
  DW-011's world (recurrence is the right mixing) this entry should land between
  the champion and the RNN, and the DW-011/DW-012/champion triangle prices
  mixing-by-recurrence vs mixing-by-shift vs mixing-by-attention in one pass.
- **mechanism:** each block = pre-norm → fixed mixing: each position's vector is
  replaced by the mean of itself and the vectors at offsets −1, −4, −16, −64
  (causal, zero-padded; no parameters, no logits, nothing to quantize) → residual
  → pre-norm → vote-trained ternary FFN (width solved so total ternary = 884,736
  exactly) → residual. 4 blocks of FFN-only mixing replace the champion's 2 full
  blocks. No Q, no K, no V, no RoPE, no position table. The FFNs and embeddings
  train exactly as the champion's (votes + AdamW parts respectively).
- **exact change:** new block type `--mixer shift` in the model builder (mixing is
  an indexing/gather op in `forward`; BitLinear collection and the Layered trainer
  are untouched).
- **mode:** process
- **prediction:** −0.01..−0.04 vs champion if routing was the tax (side signature:
  the FFNs' flip share rises vs the champion's FFN layers — freed from compensating
  for attention noise, their evidence cleans up); +0.04..+0.10 if content-based
  routing was carrying the model, in which case attention's value is priced
  against its cheapest possible substitute for the first time.
- **one-probe kill test:** retire if probe held ≥ job-zero + 0.08 — a fixed shift
  pattern losing by more than twice rotary's entire filed margin (0.0411) means
  learned routing earns far more than its fragility costs, the no-attention exit
  closes, and DW-011's recurrent arm becomes the family's only live challenger.
- **status:** queued

---

*End of wave-6 lens 5 (deep wild). 12 entries, DW-001..DW-012, all status queued.
Premise map: F-001 boundary pressure → DW-001 (damp it), DW-002 (evict on it);
J-002 counters-as-memory, assumed failed for rival (A) → DW-003 (delete them),
DW-004 (keep 2 steps of them); summed evidence (champion) and its inversion I-049
→ DW-005 (argmax witness), DW-006 (dissent only); held-as-language (J-013/J-037/
J-042) → DW-007 (eat the judge), DW-008 (junk-only diet); more-data (v3) →
DW-009 (512-window loop), DW-010 (shrinking pool); the transformer family itself
→ DW-011 (recurrent exit), DW-012 (attention-free mixer). Nothing here edits
IDEA-POOL.md or any CANDIDATES file; merge is the pool owner's call.*
