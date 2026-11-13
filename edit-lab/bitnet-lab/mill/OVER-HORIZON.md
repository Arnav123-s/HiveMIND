# OVER-HORIZON — pool entries whose flat probe must read INCONCLUSIVE — horizon (minimal J-027)

<!-- Muse's work — Muse's side of the BitNet lab. Flag list only, 2026-11-12: produced
for ENDGAME.md §E-11 / CANDIDATES-J.md J-027 (minimal form). IDEA-POOL.md, screen.py,
and PROMOTE.md were NOT edited. Companion: mill/FIDELITY.md. -->

## The rule

The probe is 75 s ≈ **~25 steps**; a full trial is ~155–170 steps. An entry is flagged
here when its mechanism — *as specified in its own pool entry* — first acts, completes,
or reaches its trial-scale form **beyond ~25 steps**. A flagged entry's flat or below
probe is **not a kill**: it ledgers as `INCONCLUSIVE — horizon` and routes to
trial-or-drop by a human's word, exactly as J-027 specifies. Unflagged entries are
not certified probe-safe; they are entries whose own text gives no late-onset evidence.

## Count

- **Flagged: 95 of 380 pool entries = 25.0%** (of the 378 judgeable
  trainer entries — excluding MILL-000 job zero and FABLE-CAND-01, a methods rule —
  25.1%.)
- **HARD: 44 (11.6% of judgeable)** — the mechanism *cannot* act within 25 steps
  (a switch/phase that has not fired, a cadence longer than the probe, a trigger that is
  arithmetically unreachable: a vote counter gains at most 1 per step, so any flip
  threshold V > 25 flips zero weights in a probe, and any clamp ≥ 32 can never bind).
- **SOFT: 51 (13.5% of judgeable)** — the mechanism acts inside the probe but
  its trial-scale form (phase length, counter-bank maturity, EMA time constant, readout
  tail, scoring maturity) lies mostly beyond 25 steps, so the probe measures a
  fraction of the claim.
- The filed J-027 estimate was **15–25%** of entries. The strict (HARD-only) reading
  lands at 11.6%, the inclusive reading at 25.1% — the filed band sits between the two
  tiers, and the tier split is the honest form of the estimate.

## HARD — cannot act within ~25 steps (44)

- **A-003** — one vote per 4 micro-batches: evidence cadence /4, first flip needs ~4x the steps
- **A-006** — two-counter race: a flip needs total votes >= 2V = 64 — impossible before step 64
- **A-022** — tail freeze: V x3 only for the last 10% of steps — the mechanism is the tail
- **A-036** — collapse layered -> plain at 75%: the collapsed phase is ~6 probe steps on an immature bank
- **A-038** — alternating phases in 200-step blocks: a probe sees only the first (votes-only) block
- **A-045** — context curriculum by thirds (64->128->256): a probe never leaves the ctx-64 third; the full-length phase never occurs
- **A-057** — EMA readout decay 0.999 (time constant ~1000 steps): at 25 steps the running mean is still init-dominated
- **A-065** — FP-first 0.9 + two-stage WD: inherits MILL-111's 90/10 split
- **A-069** — verify-flips with Fisher queue: inherits the 200-step verification cadence of MILL-231
- **A-070** — modal readout over a final 25% polish phase: both the phase and the readout are post-run
- **A-109** — dual evidence streams: entry itself is filed FULL TRIAL ONLY, never probe-eligible (flip needs both counters past V/2, each fed every other batch)
- **A-112** — scale-only polish: trains only in the +10% of steps after a standard run ends
- **B-001** — staged data mixture: stage 1 is the uniform control; the staged contrast (HQ-heavy final third) never appears in a probe
- **B-009** — epoch/repetition scaling: the phenomenon (repeated data) begins only after the first epoch completes — past the probe on any epoch grid
- **D-001** — mistake replay: phase 2 (replay) starts at 70% of steps; phase 1 is the unchanged champion
- **D-002** — self-generated practice: generation begins at 50% of steps, practice phase after — nothing dream-like exists in a probe
- **D-003** — consolidation pass: low-V finish on hard windows — a final-phase mechanism (filed full-trial-only in J-027)
- **D-004** — counter-pressure mining: spends the counter bank, thinnest exactly at probe horizon (filed full-trial-only in J-027)
- **D-005** — flip-share-triggered dream: the trigger reads flip-share dynamics that are startup transient at probe horizon (filed full-trial-only in J-027)
- **D-006** — frozen-AdamW dream phases sit at 50% and 80% of steps — a probe contains no dream phase
- **D-007** — interleaved micro-dreams: placement claim needs dream cycles interleaved across a full run (filed full-trial-only in J-027)
- **E-014** — founding-length (40 min, equal steps) comparison: filed FULL TRIAL ONLY, long format — a 75 s probe of it is a category error
- **MILL-111** — FP-first 90/10: ternary phase is the last 10% (~2-3 probe steps); PROMOTE exception already
- **MILL-112** — FP-first 75/25: ternary phase is the last 25% (~6 probe steps); PROMOTE exception already
- **MILL-130** — activation sparsification switches on only after 75% of steps
- **MILL-212** — integer leak acts every 50 steps — first leak event is past the probe
- **MILL-217** — freeze after 8 flips: at recorded flip shares ~0 flips/weight occur in 25 steps; the freeze population does not exist yet
- **MILL-220** — hybrid votes 70% -> STE 30%: the STE phase gets ~7 probe steps
- **MILL-222** — hybrid STE 70% -> votes 30% (reverse): the vote phase gets ~7 probe steps
- **MILL-231** — verify-flips cadence is 200 steps (flag --verify-flips 200) — no verification can occur in a probe
- **MILL-306** — polish phase is +25% steps AFTER the standard run — outside any probe budget
- **MILL-506** — V=48: a counter gains at most 1/step, so no weight can flip before step 48 — zero flips in a probe
- **MILL-507** — V=64: no flip possible before step 64 — zero flips in a probe
- **MILL-508** — V=96: no flip possible before step 96 — zero flips in a probe
- **MILL-509** — V=128: no flip possible before step 128 — zero flips in a probe
- **MILL-514** — V=48 (plain): no flip possible before step 48 — zero flips in a probe
- **MILL-515** — V=64 (plain): no flip possible before step 64 — zero flips in a probe
- **MILL-631** — clamp 2V=64: counters reach at most 25 in a probe, so the clamp can never bind — identical machine to any looser clamp at probe scale
- **MILL-632** — clamp none: diverges from a clamped run only after counters would have saturated (>=32-64 steps) — indistinguishable at probe scale
- **MILL-641** — V=128 with int16 counters: no flip possible before step 128
- **MILL-642** — V=256 with int16 counters: no flip possible before step 256 — past even the trial
- **MILL-652** — interaction point V=64: no flip possible before step 64
- **MILL-654** — interaction point V=64: no flip possible before step 64
- **MILL-1602** — interaction point batch 64, V=64: no flip possible before step 64

## SOFT — acts early, matures late (51)

- **A-007** — hysteresis band on levels: it only acts on flip-backs; flip-backs need a flip history that a probe has not built
- **A-008** — thrash tax: personal V decays back over ~200 steps; the tax dynamics span far past the probe
- **A-012** — fast/slow EMA agreement: the slow EMA (beta 0.99, ~100-step constant) is unformed at step 25
- **A-019** — flip-flop quarantine: trigger needs a flip and a flip-back within 20 steps, then runs 100 steps — the signature is rare and the sentence long at probe scale
- **A-033** — cyclic V, twice per run: a probe samples a fraction of one cycle phase against an immature bank
- **A-034** — gate ease-in: quantile ramps over the first 25% (~40 trial steps); a probe ends mid-ramp
- **A-035** — grow plain -> layered at 25%: the switch fires on a ~6-step-old plain bank at probe scale vs ~40 steps at trial
- **A-037** — frozen-structure polish: votes off at 60%; the polish finishes a structure that at probe scale is ~15 steps old
- **A-041** — easy-to-hard curriculum: windows are ordered across the whole run; a probe sees only the easiest slice
- **A-042** — hard-to-easy anti-curriculum (control for A-041): a probe sees only the hardest slice
- **A-043** — middle-out curriculum: a probe sees only the middle band of the ordering
- **A-054** — regression-weighted sampling: a window's delta-loss needs two scorings with training between; at probe scale almost no window has been revisited
- **A-058** — leak 0.99 + thrash freeze 5: both components are slow (100-step integrator; 5-flip trigger)
- **A-060** — ease-in 0.5 + vsched 32->64: both components complete/mature past the probe
- **A-061** — failweight 2 + modal readout 5: both components are horizon-bound (scoring maturity; tail readout)
- **A-066** — three components, descending V (32,16,8): outer-level population matures late (cf. MILL-401)
- **A-072** — thrash freeze 5 + zero-bias: the freeze trigger needs a flip history a probe has not built
- **A-093** — median readout, last 5 checkpoints: readout spans a few early checkpoints at probe scale, not a run tail
- **A-094** — average-then-round readout, last 5 checkpoints: same tail problem as A-093
- **A-095** — best-checkpoint readout: checkpoint selection over a probe's handful of early checkpoints is not the trial's selection
- **A-104** — EMA self-teacher decay 0.99 (~100-step constant): the teacher at step 25 is an average of a barely-trained model (JEPA teacher-maturity class)
- **A-110** — counter reset at halfway: the reset's cost/benefit is the second half's rebuild, ~12 steps at probe scale vs ~80 at trial
- **A-111** — dead-weight revival at halfway: the dead population is defined by half a run of evidence; a probe's half is ~12 steps
- **B-015** — AdEMAMix: slow EMA beta up to 0.9999; entry itself files it for the longest runs, where the long memory pays
- **E-011** — mature-target ablation (JEPA): target maturity IS the variable; a probe-scale EMA target is immature by construction
- **E-015** — cooldown as published: the two-stage decay's effect lives in the decay stage; the filed arm already lost +0.113 at full trial on schedule grounds
- **E-016** — embedding-exempt cooldown: same decay-stage horizon as E-015
- **MILL-109** — two-stage LR: the mid-run drop's payoff needs a stage-2 of ~80 steps; a probe's stage 2 is ~12
- **MILL-110** — two-stage LR + WD-off in stage 2: same stage-length problem as MILL-109
- **MILL-204** — vsched 32->64: the cooled regime acts on a counter bank only ~25 steps old (filer-named lie family in J-027)
- **MILL-205** — vsched 32->96: deeper cooling, same bank-maturity problem as MILL-204
- **MILL-206** — vsched 24->48: same bank-maturity problem as MILL-204
- **MILL-209** — fractional leak 0.99: integrator time constant ~100 steps; at step 25 it holds a fraction of its steady-state memory
- **MILL-210** — fractional leak 0.98: time constant ~50 steps — half the memory is still missing at probe end
- **MILL-215** — freeze after 3 flips: the thrashing population it exists to freeze has barely flipped once by step 25
- **MILL-216** — freeze after 5 flips: same population problem as MILL-215, deeper
- **MILL-218** — modal readout over the last 5 checkpoints: at probe scale the checkpoints span a few early steps, not a mature run's tail
- **MILL-219** — modal readout over the last 9 checkpoints: same horizon problem as MILL-218
- **MILL-221** — hybrid votes 50% -> STE 50%: each phase gets ~12 probe steps; the hand-off claim needs both phases at length
- **MILL-223** — annealed stochastic flips T 1.0->0.05: the cold, selective regime is the end of the anneal; a probe lives in the hot regime
- **MILL-224** — annealed stochastic flips T 0.3->0.02: same late-cold-regime problem as MILL-223
- **MILL-301** — rounding ease-in over the first 25% (~40 trial steps): a probe ends before the ease completes
- **MILL-302** — rounding ease-in over the first 50% (~80 trial steps): a probe sees only the early ramp
- **MILL-303** — rounding ease-in 50% on plain votes: same ramp problem as MILL-302
- **MILL-401** — three components (7 levels): the +-3 levels need three sequential flips per weight; level population is the D-wave bank problem
- **MILL-402** — three components at V=16 (7 levels): outer levels still need sequential flips; population matures late
- **MILL-406** — failweight 2x: worst-decile is scored periodically from a training model; at probe scale the decile is init-noise, not measured failure
- **MILL-407** — failweight 4x: dose sibling of MILL-406, same scoring-maturity problem
- **MILL-1309** — STE ease-in 25%: a probe ends before the ease completes (cf. MILL-301)
- **MILL-1401** — four components (9 levels): outer levels populate only after repeated sequential flips
- **MILL-1402** — five components at V=16 (11 levels): outer levels populate only after repeated sequential flips

## Considered and NOT flagged (the boundary, so it can be audited)

- **Warmups** (MILL-1304 warmup 50, MILL-1305 warmup 400, A-039 opt-warmup 100,
  A-023 vote warmup first 5%): early-phase mechanisms that act from step 1 by
  definition; their probe distortion is real but it is not late onset.
- **Chassis-normal thresholds** (every entry inheriting V=32, MILL-403/404 per-component
  V, MILL-211 leak 0.95 with a ~20-step constant, MILL-213 ileak 10, A-011 EMA β=0.9):
  these mature at or inside the chassis's own horizon, which job zero shares — the
  comparison stays paired. Only thresholds *raised above* the chassis (V ≥ 48,
  total-vote gates, clamps ≥ 2V) are flagged.
- **Per-step mechanisms with no accumulation in their spec**: QK-Norm/gating/scales
  (MILL-101..108), Muon (MILL-125/126), KD (MILL-113..115 — the teacher is a fixed
  pre-trained checkpoint, so the student signal acts from step 1), Fisher flips
  (MILL-228..230 — first round after 4 batches), per-layer V controllers
  (MILL-207/208), residual accumulators (MILL-226/227), DisARM (MILL-225),
  corpus-construction entries (B-005, B-007, B-010, E-018..E-021 — the data acts
  from step 1), and per-event flip rules keyed to ordinary flips (MILL-621..624,
  A-016..A-021).
- **Already exception-listed in PROMOTE.md on other axes** (not counted above):
  MILL-111/112 *are* counted (they are horizon cases first). MILL-118 (byte-pricing),
  MILL-120/121/122 (MoE — loss *and* speed axis), MILL-129 (Hadamard — speed axis),
  MILL-137/138 (SWA hybrid — *context* horizon: meaningless at ctx 256 without a
  long-context check) are exceptions the funnel already keeps by hand; their axis is
  not the ~25-step one, so they are not in this count — but a flat probe must not
  kill them either, for their own filed reasons.
- **Not trainer probes** (horizon question does not apply): E-001..E-010, E-013,
  E-022, E-023, E-024, B-017 (its filed claim is precisely that probe readings
  transfer across budgets), B-026/B-027 (decode-bench), B-031 (analysis),
  FABLE-CAND-01 (methods rule), MILL-000 (job zero). E-013/E-014's *subject* is the
  horizon itself; E-014 is counted HARD above because it is filed as an arm.

## Method

All 380 entries in IDEA-POOL.md were read; a keyword screen (fractions of the run,
stage/phase/switch, schedules/ramps/anneals, EMA/checkpoint/readout, freeze/quarantine/
thrash, every-N-steps, curriculum, dream/replay) produced 134 candidates, each then
adjudicated against its own mechanism text; arithmetic triggers (vote cadence, counter
thresholds vs the 25-step cap, EMA time constants 1/(1−β)) were computed from the
entry's own numbers and the recorded flip shares in runs.jsonl. Dose siblings inherit
their family's verdict unless their own dose crosses the horizon (e.g. MILL-211 and
MILL-213 stay unflagged inside flagged families).

