# Wave 3 · Lens 6 — CROSS-POLLINATION (Muse's work — Muse's side)

<!-- Muse's work — Muse's side of the BitNet lab. Rotation-3 miner 6, 2026-11-12.
Territory: lessons from the OTHER two programs — Fable's side (read read-only) and
Muse's side's factory — transplanted INTO the vote trainer. Nothing here edits
Fable's side, the factory, IDEA-POOL.md, or train.py. Candidate file only: nothing
is in the pool until the pool's owner merges it.

Deduped against: mill/IDEA-POOL.md, CANDIDATES-A/B/C/D/E/F/G, mill/FABLE-CANDIDATES.md,
~/workspace/edit-lab/FABLE-STUDY-2026-11-11.md, factory/CANDIDATES-IDEAS.md.
NOT re-filed (already taken): rotary + EMA readout + falling rate (adopted);
members-first routing as a FACTORY entry (FABLE-CAND-03 / factory file — XP-004 is
the trainer-side analogue, a different mechanism in a different program);
waking-dream for the factory (the D-wave is the trainer-side dreaming family —
XP-009 is a filter variant inside D-002's machinery, not a new dream entry);
paired-timing methodology (FABLE-CAND-01 — adopted as method; several entries
below inherit its paired-control discipline instead of re-proposing it).
Nothing closed is re-proposed: overshoot carry, AdamW cooldown, threshold anneal
8→64, magnitude votes as specified, the JEPA objective.

Chassis unless an entry says otherwise: layered_half + rotary, V=32, champion held
2.8580 ± 0.0161; adoption bar >2sd AND >0.01; probe 75 s / seed 0 vs job zero;
trial 3 seeds × 8 min. -->

## Coordinator's top 3 ★

1. **XP-001 · Learned say for the layered components** — Fable's say is the strongest
   measured composition result in either program (ensemble 2.4807 under the learned
   say vs 2.5754 under winner-take-all, where combining previously *hurt*), and the
   layered trainer's two components are two seats being combined by a fixed rule
   (plain sum) that has never been fitted.
2. **XP-002 · Cross-family agreement flips** — the only perfect record in Fable's
   trace (58/58: whenever two different families agreed, the answer was right),
   transplanted to the one place the vote trainer has two families available: the
   vote counter and an STE shadow of itself.
3. **XP-003 · Growth shape schedule, judged in both currencies** — the only source
   lesson measured on BitNet bodies themselves, with the verdict *flipping* between
   equal-work (growing loses: 3.1704 vs 3.1017) and equal-minutes (growing wins:
   3.085). No trainer-side shape schedule has ever been judged in both currencies.

**Strongest source evidence overall: XP-003** — a controlled three-arm comparison
(plain 4 blocks / grown 4→6 / fixed 6 blocks at 6,420 block-steps, plus the
equal-clock re-read) run on the same substrate family as the target (from-nothing
BitNet bodies), not an analogy imported from another domain.

---

### XP-001 ★ · Learned say for the layered components (per-layer t1/t2 standings, re-fit on fresh windows)
- **source:** Fable's side (growing hive) — the learned say, `body.learn_say` /
  `body._say`, commits `bea40f6` / `06b536a` / `7a11fcc`, FABLE-STUDY §2.5: first
  full unattended turn, bodies as one scored **2.4807** under the learned say —
  the first time the ensemble beat its best member (2.5715) — while the same
  population under the old winner-take-all rule scored **2.5754** as one, i.e.
  combining hurt. The say is re-made at every measurement and deliberately never
  kept in git. Muse's side's factory has the same idea only as a *serving*
  composition fit (learned say, currently SHADOW after its sealed regression,
  factory H-001/E-001); it has never been applied inside a trainer.
- **mechanism:** `Layered.install()` currently sums the two components at fixed
  standing (1, 1): installed `s = t1 + t2`. Replace the fixed sum with a learned
  per-layer say: installed `s = α_l · t1 + β_l · t2`, where (α_l, β_l) are
  re-fit every 50 steps by coordinate ascent on *fresh training windows only*
  (drawn via `offsets()`, never held windows), minimising next-token CE of the
  installed model; the fit starts from (1, 1) each time, moves only on strict
  improvement, and the standings are a function of the current state — logged
  per fit, never carried as a tuned artifact across runs. Export/serving strips
  the say exactly as Fable's does: the shipped weights are the plain ternary
  states at the final standings folded into `log_scale`.
- **train.py:** new flag `--say-fit 50` on Layered — `install()` gains per-layer
  `self.say` pairs (init (1.0, 1.0)); a `_refit_say()` helper called from `step()`
  every 50 steps scores candidate standings on 4 fresh `offsets()` batches
  (scoring passes charged to wall-clock and logged as overhead, per the D-wave
  protocol's honesty rule).
- **mode:** process
- **prediction:** −0.02..−0.05 at trial scale. The half-control proved the two
  components fed one stream earn nothing *summed equally* (gap 0.0020); Fable's
  record says the combination rule itself was the missing variable there —
  winner-take-all also earned nothing (worse than nothing) until the say was
  learned. If XP-001 also ties plain, the levels question closes for a deeper
  reason than F-003's bandwidth argument, and that is worth one trial.
- **status:** queued
```mill
id: XP-001
mode: process
run: --arm layered_half --rope --say-fit 50
```

### XP-002 ★ · Cross-family agreement flips (vote counter × STE shadow: agree = fast track, disagree = verify)
- **source:** Fable's side (working hive) — cross-family agreement as a free
  verifier, `training/diverse.py`, FABLE-STUDY §2.11: recruits from other families
  share fewer mistakes (joint-error overlap near chance vs ~2× chance for
  same-model pairs); voting gained nothing overall (27/32 = best alone), **but
  whenever two different families printed the same program output it was right —
  58/58 across five pairs**. Agreement = trust without a jury; disagreement =
  where to spend effort. Explicitly "not built into the run loop yet" on Fable's
  side. Muse's side's factory translation table (#19) has the same idea only as
  a measurement log between Tier-1 and Tier-0 — never inside a trainer.
- **mechanism:** The trainer runs a cheap second family alongside the votes: an
  STE shadow latent for each ternary weight, updated *only* as a direction
  witness (one fp32 EMA of the latent's implied pull, `sign(latent − installed)`,
  β=0.9 — no STE training of the model itself). Per step, per weight: where the
  shadow's pull agrees with the gated vote's sign, the vote counts **2** (the two
  families concur — the 58/58 population); where they disagree, the vote counts
  **1** as champion and the weight is added to a disagreement list. Every 100
  steps, the disagreement list's pending flips (largest |counter| first, cap
  0.1% of weights) are verified by measured delta-loss on a fresh batch before
  firing — verification effort is spent exactly where the families split, which
  is the source lesson's allocation rule. Distinct from A-012 (agreement between
  two EMAs of the *same* gradient stream — one family, two timescales), F-018
  (quorum among sub-batches of the *same* batch — one family), and MILL-231
  (verify-flips spends its budget by counter proximity, with no agreement
  signal deciding where to look).
- **train.py:** new flag `--xfamily` on Layered — shadow pull EMA buffer in
  `__init__` (4 B/weight, charged in the record's state bytes), agreement-weighted
  increment in `step()`, disagreement verification pass every 100 steps reusing
  the fresh-batch delta-loss pattern of the fisherflip entries.
- **mode:** process
- **prediction:** −0.02..−0.05 at trial scale. Mechanism check logged either way:
  audited flip accuracy split by agreement class — the source predicts agreed
  flips are near-error-free and the entire error mass sits in the disagreed
  class; if the lab's split does not show that shape, the transplant's premise
  is false here and the entry retires on its own log.
- **status:** queued
```mill
id: XP-002
mode: process
run: --arm layered_half --rope --xfamily
```

### XP-003 ★ · Growth shape schedule on the champion chassis, judged at equal steps AND equal minutes (2 blocks → 4 blocks at 50%)
- **source:** Fable's side (growing hive) — the growth-at-equal-work verdict,
  restated in the 2026-11-13 HANDOFF (FABLE-CANDIDATES, "checked — not new"
  section) and FABLE-STUDY §2.8/§3.3's equal-budget discipline: at **equal work**
  (6,420 block-steps) plain 4 blocks **3.1017**, grown 4→6 **3.1704**, fixed 6
  blocks **3.2837** — growing *loses*; at **equal clock time** the grown body
  wins (**3.085**) because the small body is cheaper per step. The verdict is a
  function of the currency, and Fable's side reports both. Muse's side's
  trainer record has never judged any shape change in both currencies: the
  scale ladder is step-boxed only, the mill probes are minute-boxed only.
- **mechanism:** Champion chassis grows mid-run: steps 0–50% run layered_half
  (2 blocks); at 50% two fresh blocks are appended (ternary states rounded from
  the current init distribution, counters at 0) and the run finishes as full
  layered (4 blocks) — total ternary weights 884,736 → 1,769,472. Following
  Fable's age-dependent recipe (newborn cells keep the *old* rate: 5e-4 beat
  3e-3 locally, FABLE-STUDY §3.3), the newborn blocks' counters run **V=48**
  for their first 25% of life while inherited blocks stay at V=32. The entry
  is judged **twice, as two separate verdicts**: (a) step-matched vs the
  layered full arm capped at the same total steps; (b) minute-matched vs both
  layered_half and layered at 8 min. The Fable prediction is imported as the
  hypothesis, not assumed: (a) loses, (b) wins — any other pattern is the
  finding. Distinct from F-047 (depth growth 3→6 by block *duplication* with
  counters *halved*, at 10M scale, single-currency) and A-035 (grows the
  second *component* of existing weights, not the model's depth).
- **train.py:** new flag `--grow-at 0.5` on Layered — model builder appends two
  `Block`s at the phase boundary; trainer extends `t1/t2/c1/c2/log_scale` lists
  for the new blocks (fresh counters, V=48 probation via a per-block votes
  array), existing blocks' state untouched byte-for-byte.
- **mode:** process — full trial only in both currencies (a 75 s probe cannot
  hold a 50% growth point and two judgements); paired side-by-side re-runs per
  FABLE-CAND-01 wherever a minutes verdict is claimed.
- **prediction:** Step-matched: **+0.02..+0.05** vs full layered (growing loses
  at equal work, per source). Minute-matched: **−0.01..−0.03** vs layered_half's
  2.8580 (the cheap early half buys steps the fixed shapes cannot). Adoption
  requires the minute-matched win AND a step-matched loss no worse than the
  source's own growth penalty (+0.069 at their scale) — the entry's product is
  the dual-currency number itself, which every future shape entry inherits.
- **status:** queued
```mill
id: XP-003
mode: process
run: --arm layered_half --rope --grow-at 0.5
```

### XP-004 · Members-first correction: the second component exists only where plain votes cannot confirm
- **source:** Fable's side — members-first routing, commit `61fb325`, seed 9007
  clean sitting (FABLE-CAND-03): **members first 10/16 in 179 min; roles alone
  9/16 in 178 min; members alone 9/16 in 69 min** — the generalist attempting
  the whole task first, with the specialist pipeline taking only what it cannot
  confirm, matched the full pipeline at ~40% of the wall time and beat it when
  combined. Filed for Muse's side's *factory* serving (factory/CANDIDATES-IDEAS,
  FABLE-CAND-03 entry); never transplanted into the trainer. Fable's caveat is
  carried with it: two members agreeing *by the same method* is not independent
  verification — so "cannot confirm" below is judged on fresh windows, not on
  the windows that produced the indecision.
- **mechanism:** Plain votes are the member; the layered correction (t2) is the
  specialist pipeline, engaged per weight only where the member cannot confirm:
  a weight's t2 counter activates when, by 60% of the run, its plain counter
  has either (a) never fired a flip, or (b) fired and reversed ≥2 times
  (oscillation = unconfirmed). All other weights keep t2 ≡ 0 for the whole run
  — the model serves as plain + a sparse correction population. Activation is
  judged at the 60% boundary on the counter record; whether an activated t2
  *earns* its place is judged at trial on fresh held windows (different method,
  per the caveat). Distinct from A-035 (t2 grown for *every* weight at 25%)
  and F-003 (t2 fed a different stream for every weight): here the specialist's
  *existence*, not its diet, is what is routed.
- **train.py:** new flag `--members-first 0.6` on Layered — t2 counters masked
  to zero until activation; activation pass at the phase boundary reads the
  plain counter's flip history (a per-weight flip/reversal log, new int8
  buffer); state bytes reported as plain + activated-fraction × t2 cost.
- **mode:** process
- **prediction:** Within ±0.015 of the full layered champion at trial scale at
  a predicted 30–55% of the t2 state — the win condition is the members-alone
  shape (same score, fraction of the cost), judged per byte. If the activated
  fraction exceeds ~70%, plain confirms almost nothing at this scale and the
  routing premise is false here — that number is reported either way.
- **status:** queued
```mill
id: XP-004
mode: process
run: --arm layered_half --rope --members-first 0.6
```

### XP-005 · Snapshot-and-immune rollback for flip cohorts (the cycle-6/7 repair, inside the trainer)
- **source:** Muse's side's factory — growth cycles 6 and 7 (2026-11-12): births
  passed both pristine gates, serving regressed (battery 0.941 → 0.934, then
  0.941 → 0.9375), and cycle 6's rollback *deleted the two serving model files
  instead of restoring them*. The repair (`growth/REPAIR-cycle-006-2026-11-12.md`)
  fixed `growth_cycle.py` to **snapshot target files before any birth and
  restore byte-for-byte on rollback**, with a regression test (suite 78/78);
  cycle 7's repair found the fix had covered only one of three cycle paths.
  Paired source: Fable's side §2.4 immune check — a newborn is refused if *any*
  known territory gets worse (`judge_local`, `e5ff3eb`). The vote trainer has
  no snapshot, no local judgement, and no rollback anywhere: a bad flip cohort
  is permanent the moment it lands.
- **mechanism:** Every 200 steps the runner snapshots the full trainer state
  (t1/t2/c1/c2 + AdamW moments + log_scale) to a ring of 2 snapshots. At each
  snapshot point, the *outgoing* 200-step cohort is judged locally: fresh-window
  training loss (never held) is split by block — cohort kept only if the pooled
  fresh loss did not regress >0.02 vs the previous snapshot point AND no single
  block's territory windows (fresh windows routed by lowest per-block loss
  contribution, the judge_local analogue) regressed >0.05. On failure: restore
  the snapshot byte-for-byte and halve the next cohort's flip budget (the
  A-017 dial, used as the immune response). All three judgement paths (pooled,
  per-block, restore) are covered by the snapshot — the cycle-7 lesson (a fix
  on one path is not a fix) is written into the entry as a completeness
  requirement, not left as commentary.
- **train.py:** new flag `--immune 200` on Layered — snapshot/restore helpers on
  the trainer (state_dict over its own tensors, not the model's), cohort
  judgement in the training loop on `offsets()` draws, restore path exercised
  by a forced-failure smoke test before any trial counts.
- **mode:** process — full trial only (cohorts of 200 steps do not exist at
  probe horizon).
- **prediction:** −0.01..−0.03 at trial scale, concentrated in seed variance:
  the champion's sd (0.0161) should shrink because the catastrophic-cohort tail
  is exactly what rollback removes. If restores fire on >1 cohort per run on
  average, the cohort is too large or the thresholds too tight — reported, not
  tuned mid-trial.
- **status:** queued
```mill
id: XP-005
mode: process
run: --arm layered_half --rope --immune 200
```

### XP-006 · Breadth flips: the per-step flip budget is spread thin across every layer before it concentrates anywhere
- **source:** The Opus method, studied on Arnav's order and adopted into Muse's
  side's repair work 2026-11-09 (`~/workspace/edit-lab/METHODS-FROM-MAKE-IT-WORK.md`):
  **breadth beats concentration — thin rank-2 edits across every module beat
  concentrated rank-8 edits**, winners chosen on a dev split. It was adopted for
  weight *editing* on Muse's side and for the factory's repair job; it has
  never been applied to the vote trainer's flips, which currently concentrate
  freely: whichever layer's counters cross in a step takes the whole step's
  flip volume.
- **mechanism:** A per-step flip budget of 0.1% of weights (the chassis's own
  measured mean flip share, ≈0.11%) is allocated **breadth-first**: each
  BitLinear layer first receives an equal share (budget / n_layers) spent on
  its largest-overshoot pending flips; only unspent share (a layer with fewer
  pending flips than its share) pools upward for a second pass. No layer may
  flip more than 2× its equal share in one step. Distinct from A-017 (a single
  global cap — concentration *within* the cap is unrestricted, which is
  precisely what the source lesson says loses) and A-018 (staggering
  *concentrates* flips into one block per step — the opposite allocation,
  already filed; XP-006 vs A-018 is a clean breadth-vs-concentration head-to-head
  the pool currently cannot run because only one side exists).
- **train.py:** new flag `--breadth-flips` on Layered — two-pass allocation in
  the flip application inside `step()` (pending sets are already computed as
  `go1/go2`; the change is the selection among them when they exceed budget).
- **mode:** process
- **prediction:** −0.01..−0.03 at trial scale; ~0 at probe (pending sets rarely
  exceed budget in the first steps). Side measurement that decides the
  mechanism even on a flat loss: per-layer flip-share variance across the run
  should fall sharply vs champion; if it does not, the budget never bound and
  the entry is void, not wrong.
- **status:** queued
```mill
id: XP-006
mode: process
run: --arm layered_half --rope --breadth-flips
```

### XP-007 · Per-direction flip switch-on with live audit and automatic retirement (the spawn trainer, per flip direction)
- **source:** Fable's side (working hive) — the spawn trainer, `team/cells/spawn.py`,
  FABLE-STUDY §2.6: a noticed job is staffed **per label** — a label switches on
  only if the newest decisions contain ≥3 cases where the member chose a
  different label, the cell is wrong at most half as often as blind answering,
  then ≥95% agreement on what it answers; at work, **1 sure call in 10 is also
  sent to the member, and live agreement under 93% (RETIRE = 0.93) retires the
  cell automatically**. The first round stayed off for lack of evidence — the
  gate refusing to fire was itself reported as a result. Muse's side's factory
  lacks per-label adoption entirely (translation table #9); the trainer has
  never gated anything per direction.
- **mechanism:** The trainer's "labels" are its four flip directions per
  component (0→+1, 0→−1, +1→0, −1→0). All directions start ON (champion
  behaviour) but are audited: 1 in 10 flips of each direction is shadow-checked
  — the flip is applied to a scratch copy of that one weight, and the fresh
  batch's loss is measured with and without it (two extra forward passes on a
  32-window batch, charged). A direction whose audited flips *hurt* the batch
  loss in >7% of audits over a trailing 50-audit window (the RETIRE=0.93
  transplant) is switched OFF for the next 200 steps: its counters keep
  accumulating (evidence is not destroyed) but its flips cannot fire. A
  direction may also be switched off *from the start* per layer if a 20-flip
  pre-audit at step 100 shows the hurt rate already >7% — the per-label
  evidence gate, with "too little evidence" (fewer than 20 audits) reported
  as exactly that, never as failure.
- **train.py:** new flag `--dir-audit` on Layered — per-direction audit
  counters and enable masks in `step()`; shadow check reuses a single-weight
  install perturbation (no full reinstall: the weight's contribution is
  recomputed for the audit batch only).
- **mode:** process — full trial only (audit statistics need hundreds of flips).
- **prediction:** −0.01..−0.04 at trial scale, with the diagnostic as the real
  product: the per-direction hurt-rate table. Prior from the state histograms:
  flips *into* 0 (feature deletion) are the likeliest chronic losers; if all
  four directions audit clean, the trainer's flip quality is uniform and that
  is a finding the lab has never had.
- **status:** queued
```mill
id: XP-007
mode: process
run: --arm layered_half --rope --dir-audit
```

### XP-008 · Gate/report split of the held set, plus a frozen yardstick that never gates (trainer-side)
- **source:** Fable's side — two linked disciplines: (i) the **gate/report
  split** (§2.4): a newborn is judged on a gate set of never-trained passages,
  while a separate report set "is only ever reported, never gated on — the
  split keeps the judging set from becoming a training target"; (ii) the
  **fixed yardstick** (§2.7, `body.YARD`): the same 300 held passages every
  time, because the all-its-text number moves whenever the harvest grows — "only
  the yardstick says whether the hive got better." Muse's side's factory
  translation table (#2/#3) records Muse's side as *weaker* on both (its held
  slices both act as gates; nothing is report-only). The BitNet mill is weaker
  still: its single 128-window held set is simultaneously the probe gate, the
  trial gate, and the reported number for every entry in the pool.
- **mechanism:** Split the judging surface three ways, permanently:
  **GATE-64** (the first 64 of the current 128 held windows) — the only surface
  probes and trials may gate/promote/adopt on. **REPORT-64** (the remaining 64)
  — computed and recorded on every verdict-bearing run, *never* read by any
  gate, promotion rule, or kill criterion. **YARD** — 128 windows drawn once
  from the corpus-v3 stream's tail (never trained on by any v1/v2 series),
  frozen in a sealed file, reported once per champion generation and never
  gated on. A GATE win that REPORT contradicts by >0.03 is stamped
  `GATE-OVERFIT SUSPECT` in the ledger — the split's whole purpose is making
  that stamp possible. Distinct from G-047 (rotating confirmation subsets —
  rotation eventually gates on everything, which is the opposite discipline)
  and E-018 (a one-off honest re-baseline on v2; XP-008 is the standing split
  every future run inherits).
- **train.py:** no trainer change; runner change in `held_windows()` usage —
  new flags `--held-split gate|report|yard` selecting which surface a run
  *reports*, with screen.py's promotion path hard-wired to `gate` (the wiring,
  not a convention, is the entry: a run that gates on report/yard is invalid
  by construction).
- **mode:** process — methodology arm; judged on the first champion generation
  run under it (GATE/REPORT divergence on the existing champion is the first
  measurement).
- **prediction:** No held-loss gain is claimed — the prediction is about the
  numbers' honesty: GATE−REPORT divergence on already-promoted arms will read
  0.01–0.03 (the selection pressure the single-set mill has silently absorbed),
  and at least one historical close verdict (margin <0.03) will fall inside
  that band. If divergence reads <0.005 across a full generation, the single
  set was honest and the split retires to a cheap permanent safeguard.
- **status:** queued
```mill
id: XP-008
mode: process
run: --arm layered_half --rope --held-split gate
```

### XP-009 · Checker-verified synthetic spans (D-002 gains a different-family filter — the coordinator-repair lesson)
- **source:** Two records, one lesson — verification must come from a *different
  method* than the thing being verified: (i) Muse's side's HiveMIND coordinator
  repair, WON and closed 2026-11-10 — the r4 finalist scored **0.954 on the
  pristine test vs the 0.930 gate/base**, and "the winning path was
  **checker-verified self-generated data, not surgery**"; (ii) Fable's side's
  members-first caveat (FABLE-CAND-03): members who ran the same broken program
  *agreed on its wrong output* — same-method agreement is not verification.
  The trainer's only self-generated-data entry, D-002, filters its spans by
  the *generating model's own* vote dynamics and its *own* CE guard band
  [1.8, 4.5] — self-verification by construction, exactly the shape both
  records warn against.
- **mechanism:** A fourth filter variant inside D-002's existing machinery
  (same generation, same 50%→85% mixing, same guard band, same pre-trial
  gates): a candidate span is kept only if a **checker from a different
  family** — the FP/STE twin of the chassis, trained once on the same corpus
  and frozen — also places the span in a usable band: checker CE ∈ [1.8, 4.5]
  AND |checker CE − generator CE| ≤ 0.75. Spans the generator loves but the
  checker finds alien (the echo-chamber signature D-002's own kill criteria
  watch for) are rejected *before* the vote-dynamic filter runs. The checker
  is never trained on synthetic data and never gates on held windows.
- **train.py:** no change; companion-runner variant of D-002 — new flag
  `--synth-filter checker` on `run_dream.py` alongside `flipband|agree|strongmass`,
  plus the one-time FP-twin checkpoint (its training cost charged to the entry,
  as MILL-113 charges its teacher).
- **mode:** process — full trial only, inheriting D-002's protocol wholesale
  (step-boxed, CONTROL-D paired, 2×2 source × filter factorial with this as
  the filtered cell).
- **prediction:** −0.01..−0.03 vs D-002a (the strongest self-filter) at trial
  scale, *if* D-002 survives its own pre-trial gates at all. If the checker's
  acceptance rate diverges wildly from the self-filters' (<5% or >80% overlap
  disagreement), that divergence is itself the measurement: it prices how much
  of D-002's "frontier band" is the generator grading its own homework.
- **status:** queued
```mill
id: XP-009
mode: process
run: --arm layered_half --rope --dream synth --synth-filter checker
```

### XP-010 · Surgery-mapped repair window (ablation map indicts one block; only its counters train)
- **source:** Arnav's surgery doctrine for Muse's side (2026-11-08): "if
  training is performing bad then surgery after mapping is necessary — map
  first (per-unit ablation), then surgery on only what the map indicts;
  training is demoted to repairing indicted units, never the blind default."
  Fable's side ran the mapping half literally (`training/cells_cut.py`,
  FABLE-STUDY §3.3): a knockout map indicted 8 near-dead layers — and its
  *removal* edit was then **rejected** on measurement (retrained cells dropped
  0.936 → 0.789), which is why this entry's surgery is repair-training of the
  indicted unit, never removal. The vote trainer has never frozen a healthy
  part to concentrate repair on an indicted one; its phases (A-038) alternate
  by clock, not by indictment.
- **mechanism:** At 50% of steps, build the map: for each block, measure the
  fresh-window loss increase when that block's ternary states are temporarily
  zeroed (ablation pass over 8 `offsets()` batches, charged as overhead). The
  block whose ablation costs the *least* loss is the indicted (near-dead /
  under-contributing) block — Fable's knockout criterion. For the next 20% of
  steps, only the indicted block's counters integrate and flip; every other
  block's counters and states freeze (AdamW parts keep training throughout —
  the frame stays live, as in D-006's lesson that the parts must be separable).
  Final 30%: normal champion training. One indictment, one repair window, no
  re-mapping — the doctrine's discipline is that the map is taken once and
  the repair is judged as a whole.
- **train.py:** new flag `--surgery 0.5,0.2` on Layered — ablation hook in the
  training loop at the phase boundary; per-block counter freeze masks in
  `step()` during the repair window.
- **mode:** process — full trial only (the map needs a trained-enough model to
  indict anything real).
- **prediction:** −0.01..−0.03 at trial scale if a near-dead block exists at
  champion scale (2 blocks: the map has only two suspects, so the prior is
  honestly weaker than at Fable's depth — a flat result plus a map showing
  both blocks load-bearing is a clean negative that retires the surgery line
  for this chassis size, which is also a deliverable).
- **status:** queued
```mill
id: XP-010
mode: process
run: --arm layered_half --rope --surgery 0.5,0.2
```

### XP-011 · Precision ladder by saturation indictment (no wider counters when the evidence, not the counter, is what is missing)
- **source:** Fable's side — the spawn trainer's size ladder (FABLE-STUDY §2.6,
  commit `47960f0`): a bigger base is tried **only if the smaller one cannot
  hold the job**, and "*no bigger base when the evidence, not the cell, is
  what is missing*." The trainer's accumulator-precision family violates this
  in both directions today: MILL-201..203 widen the increment globally by
  prescription, MILL-226/227 change the accumulator globally by prescription,
  and A-031 allocates int16 by a fixed depth prior — none of them first
  measures whether int8 evidence is actually being *clipped* anywhere.
- **mechanism:** Measure first, widen only where indicted. During the first
  25% of steps, log per layer the **saturation rate**: the share of steps on
  which a layer's counters sit at the ±V clamp while same-sign votes keep
  arriving (evidence that exists but cannot be stored — the counter, not the
  evidence, is the binding constraint, in the source's terms). At 25%, layers
  whose saturation rate exceeds 2% are widened for the rest of the run
  (counters re-cast to int16, clamp raised to ±64, flip threshold unchanged
  at 32 net votes — only the *storage* grows); all other layers stay int8 at
  champion cost. If no layer is indicted, the run is byte-identical to the
  champion and the entry reports exactly that.
- **train.py:** new flag `--ladder-precision 0.02` on Layered — saturation
  counters in `step()` (one int per layer), one-time counter re-cast at the
  phase boundary; state bytes reported as champion + widened layers only.
- **mode:** process
- **prediction:** −0.01..−0.03 at trial scale *conditional on an indictment
  existing*; the unconditional prediction is that ≤ half the layers indict
  (early blocks saturate on large early gradients; late blocks rarely do), so
  most of any global-widening gain should be buyable at a fraction of the
  global state cost. If saturation reads <0.5% everywhere, the whole
  precision-dial family (MILL-201/226/227 included) is re-priced downward
  with a measurement instead of an assumption.
- **status:** queued
```mill
id: XP-011
mode: process
run: --arm layered_half --rope --ladder-precision 0.02
```

### XP-012 · The library analogue, priced as a negative control: counter-archive restore on flip-back
- **source:** Fable's side — the library turned **off by default**: members
  *with* the library (stored material consulted instead of learned) did
  **worse than members who learned nothing, on two seeds** (Fable trace /
  HANDOFF record as carried in Muse's side's records, 2026-11-12). The
  trainer-side analogue of "data the model consults that hurts": the vote
  trainer's only consultable store is its own archived evidence. Today a flip
  *resets* the flipped component's counter to 0 — the trainer consults
  nothing. The library form would archive each counter's pre-flip value and,
  if the weight later flips *back* to the state it left, restore the archived
  counter instead of starting from 0 — the weight "consults its file" on the
  state instead of re-learning it.
- **mechanism:** One extra int8 archive per component (the counter's value at
  its last departure from the state it is now re-entering; overwritten on each
  departure). On a flip into a previously occupied state with an archive
  entry, the counter initialises to the archived value (clamped to ±(V−8) so
  restored evidence alone can never immediately re-flip) instead of 0. Every
  other rule is champion. This is not the closed overshoot carry: carry keeps
  *leftover* evidence from the *same* crossing in the *same* direction of
  travel; the archive restores evidence from a *previous visit* to a state,
  across an intervening occupation of a different state — the consultation
  event is the return, which carry never models.
- **train.py:** new flag `--counter-library` on Layered — archive buffers
  alongside `c1/c2`, restore branch in the flip application inside `step()`;
  +2 B/weight state, charged.
- **mode:** process
- **prediction:** **+0.00..+0.04 (expected flat-to-worse)** — a priced negative
  control, filed because the source result is a measured negative and the
  transplant exists to test whether it generalises: Fable's lesson predicts
  consulted stale evidence hurts *because the world (here: the rest of the
  network) changed while the file sat still*. A win here would be the more
  interesting result — it would bound the library lesson to retrieval-style
  consultation and clear counter memory as safe — and the entry is cheap
  enough that either verdict earns its probe.
- **status:** queued
```mill
id: XP-012
mode: process
run: --arm layered_half --rope --counter-library
```

---

*End of wave-3 lens 6 (cross-pollination). 12 entries, XP-001..XP-012, ranked;
★ = XP-001, XP-002, XP-003. Every entry names its source lesson with the
originating program and record, the exact transplant mechanism, and the nearest
already-filed neighbour it must not be confused with. Strongest source evidence:
XP-003 (growth at equal work vs equal minutes — a controlled three-arm verdict
measured on BitNet bodies, reported in both currencies by Fable's side itself).*
