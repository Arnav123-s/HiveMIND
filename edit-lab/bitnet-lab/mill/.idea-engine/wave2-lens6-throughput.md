# Wave G · Lens 6 — THROUGHPUT: experiment-design for probes/hour (Muse's work — Muse's side)

<!-- Muse's work — Muse's side of the BitNet lab. Idea Engine wave G, miner 6.
Territory: EXPERIMENT-DESIGN only — learning the same thing cheaper. NOT infrastructure:
checkpoint-resume and the job queue belong to the compute department (compute/CAPACITY.md
levers 2–3) and are not proposed here. Nothing here is in the pool until the pool's owner
merges it. -->

## Measured baseline (every number below traces to a lab record)

- Funnel today (PROMOTE.md): probe = 75 s, seed 0 only, 128 held windows → trial =
  3 seeds × 8 min = **24 min per promoted idea**. Pool ≈ 368 entries (CANDIDATES-F method
  count) → one full probe pass ≈ 368 × 75 s ≈ **7.7 h solo**, before any trial.
- Delivered throughput is currently **0 probes/h** (compute/CAPACITY.md, 2026-11-12):
  the mill has yielded on every pass; `mill/ledger.jsonl` does not exist yet and no probe
  has ever run (RIGOR-AUDIT). All seed/step statistics below are therefore measured from
  the lab's only completed record, `runs.jsonl` (45 lines, 13 three-seed arms at 8-min
  format + ladder/JEPA runs) — the mill ledger will extend, not replace, these numbers.
- Champion rate: layered_half+rope took 154–170 steps in 480 s (≈3.0 s/step), so a 75 s
  probe is **≈25 steps** (CANDIDATES-D §3 independently puts S0 ≈ 25).
- Machine-speed variance is measured, not hypothetical: identical JEPA-control configs
  took 129–139 steps in one window vs 154–170 in another (−18% steps), and one 2026-11-11
  run was discarded at 52 steps vs 121–124 clean (runs-discarded.jsonl).
- Seed-0 reliability, measured on runs.jsonl: comparing each arm's seed-0 Δ vs champion
  seed 0 against its 3-seed mean Δ vs champion mean (2.8580), **2 of 13 arms flip sign**:
  carry (seed-0 Δ −0.0014, mean Δ +0.0181) and the JEPA control (seed-0 Δ −0.0134, mean
  Δ +0.0593). ste_half is a false promote at probe logic: seed-0 Δ +0.0615 clears the
  0.05 bar, its 3-seed mean Δ is only +0.0375. Within-arm 8-min ranges run 0.006–0.098
  (champion range 0.0288, sd 0.0161) — and RIGOR-AUDIT §5a notes probe-scale (75 s) seed
  noise has **never been measured**; several entries below exist to measure it cheaply.
- Flip share is the lab's most stable per-step statistic: champion 0.00110/0.00116/0.00113
  across seeds (±3%), while failed mechanisms sit far away — mag 0.00010–0.00011 (10× low),
  anneal 0.00063–0.00068, plain 0.00036–0.00038. `train_last100` is documented to rank
  differently from held loss (RESULTS-2026-11-11), so no entry below trusts train loss alone.

## Dedupe statement

Read and NOT re-proposed: the sweep's shared-data load (IDEA-POOL execution modes,
SWEEP_BATCH=8), fresh job zero per pass (PROMOTE.md, post-audit), the concurrency study's
worker-count question (CONCURRENCY.md — entries below extend its *logic*: verdict-bearing
runs stay solo, screening absorbs all risk), E-022 (post-generation seed-0 audit of losers —
TH-002 is its prospective, live-funnel counterpart and also audits *winners*, which E-022
never checks), E-023 / CANDIDATES-D §3 (fixed-step / step-boxed budgets — TH-008 keeps the
wall-clock budget and adjusts for steps instead of changing the budget), B-017 (schedule-free
training), the batch/shape grids as *treatments* (MILL-1201–1203, MILL-1101–1114 — TH-009
uses shape as a *screening format*, judged only by paired Δ, never as a treatment claim).

---

### TH-001 · Three-stage funnel with a known-answer calibration set ★
- **source:** the full-pool cost itself: 368 × 75 s ≈ 7.7 h per probe pass, and 24 min per
  trial behind it. Of the 13 completed non-champion arms in runs.jsonl, 6 lost to the champion
  by ≥ +0.10 at 8 min (anneal +0.99, mag +0.28, layered +0.24, plain +0.22, ste +0.14,
  cooldown +0.11) — 46% of everything the lab has ever run was a catastrophe-class loser that
  a screen never needed 75 s, let alone 24 min, to bury.
- **mechanism:** Stage 0 (15 s, ≈5 steps, no held eval): kill only on catastrophe signals —
  flip share ≥3× or ≤⅕ of job zero's paired value (mag sits at 0.09×, the D §4 FLIP-STORM
  flag already uses 3×), train-loss slope worse than job zero's paired slope by a calibrated
  margin, or a crash/divergence. Stage 0 cannot promote and cannot kill anything in the
  ambiguous band. Stage 1 = today's 75 s probe, unchanged. Stage 2 = trial, unchanged.
  Before stage 0 judges anything live, calibrate it on a **known-answer set**: six arms whose
  8-min verdicts runs.jsonl already owns (champion = tie, carry +0.018 = near, plain_half
  +0.043 = near, cooldown +0.113 = loser, anneal +0.992 = catastrophe, ste_half −0.038 =
  winner) run once at 15 s; stage-0 thresholds are set from those six readings and the
  measured information loss (which losers stage 0 misses, which nears it would have killed)
  is written into PROMOTE.md next to the bar it modifies.
- **change:** `mill/screen.py`: add a stage-0 pass (probe_minutes 0.25, verdicts `kill0` /
  `pass0` ledgered distinctly; `kill0` is generation-scoped like any verdict) gated on a
  one-time calibration block in `mill/PROBE-NOISE.md` recording the six known-answer
  readings; PROMOTE.md gains the stage-0 paragraph with its measured loss table.
- **payoff:** at the measured 46% catastrophe share, expected cost per screened idea =
  15 s + 0.54 × 75 s = 55.5 s vs 75 s → **≈65 vs 48 ideas/h solo (+35%)**, ≈2.0 h saved per
  full pool pass, plus every stage-0 kill is a trial that can never be wasted (24 min each).
  If the true catastrophe share is only 25%, the saving is still ≈1.0 h/pass. Arithmetic
  uses the 13-arm history; the calibration set replaces the assumption with a measurement
  before the stage is trusted.
- **validity risk:** a slow-starting winner (FP-first MILL-111/112, cascade-style entries
  whose own pool text says the probe under-measures them) could look catastrophic at 5 steps.
  Guard: stage 0 kills on mechanism signals (flip share, divergence), never on held/train
  level alone; every PROMOTE.md exception-listed id bypasses stage 0 entirely; and the
  calibration set must show zero false kills on its near/winner members before stage 0
  goes live — one false kill in calibration keeps the stage advisory-only.

### TH-002 · Banded second seed: seed economy where the decision actually lives ★
- **source:** seed 0 alone misleads at a measured rate: 2/13 sign flips vs the 3-seed mean
  (carry, JEPA control) and 1/13 false promotes (ste_half: seed-0 Δ +0.0615 ≥ 0.05 bar,
  mean Δ +0.0375) in runs.jsonl. A false promote costs a 24-min trial; a false kill costs
  the idea for the generation (RIGOR-AUDIT §3a(i)). E-022 audits the losers *after* the
  generation; nothing audits a lucky winner before it spends 24 min.
- **mechanism:** probes stay seed-0/75 s outside the decision band. Any probe landing in
  |Δ| < 0.10 (the band containing every measured sign flip: carry 0.001–0.018, JEPA control
  0.013–0.059, ste_half 0.038–0.062, plain_half 0.042–0.043, layered_half 0.017–0.041)
  automatically gets a seed-1 probe at the same budget, judged against a seed-1 job zero
  measured in the same pass; the verdict uses the 2-seed mean Δ. Outside the band, one seed
  has never flipped in the lab's record, so one seed is what it gets.
- **change:** `mill/screen.py`: after ledgering a probe, if |Δ| < 0.10, queue the same id
  with seed 1 plus a seed-1 MILL-000 for that pass; ledger lines gain the second seed and
  the verdict rule (2-seed mean vs the same 0.05/0.02 bars) is written into PROMOTE.md.
  Distinct from E-022: this changes live verdicts in both directions, E-022 only counts
  the damage afterwards.
- **payoff:** band share in the 13-arm history = 5/13 ≈ 38% → added cost 0.38 × 75 s ≈
  29 s per idea. False-promote rate 1/13 ≈ 8% → expected trial waste avoided
  0.08 × 24 min ≈ 1.9 min per idea. Net ≈ **+1.4 min saved per idea screened, ≈8–9
  trial-hours per full pool pass**, before counting rescued false kills (unpriced upside).
  Small-sample basis (n=13 arms) — the band and rates are re-estimated from the mill ledger
  after generation 0 and the entry says so in PROMOTE.md.
- **validity risk:** the 2-seed mean is a different estimator than the pool's other
  verdicts, so band verdicts and non-band verdicts are not strictly commensurable, and a
  seed-1 job zero doubles that pass's baseline cost when the band is busy. Guard: both
  seeds' raw Δs are ledgered individually (the mean is derived, never the only record);
  the trial stage is untouched, so a band verdict can only spend or save a trial, never
  adopt; re-check the flip rate on ledger data after gen 0 and narrow the band if the
  measured flip rate outside it is truly zero.

### TH-003 · Sequential trials: spend the third seed only when it can still change the verdict ★
- **source:** a trial is 3 × 8 min = 24 min, the most expensive unit in the funnel
  (CAPACITY: 7.5 trial-units/h theoretical, 0 delivered). PROMOTE.md's adoption rule has
  two parts — mean beats ref by >2 sd AND >0.01, **and ≥2 of 3 seeds individually beat the
  reference mean** — and the second part can become mathematically undecidable-or-decided
  before the third seed runs.
- **mechanism:** run trial seeds in fixed order 0, 1, 2 with two pre-registered stops.
  (a) *Guard-dead stop:* if seeds 0 and 1 both fail to beat the reference mean, the
  per-seed guard can never pass (at best 1 of 3) — stop; verdict `below`, zero information
  loss, it is arithmetic, not inference. (b) *Mean-dead stop:* if after 2 seeds even a
  third seed at the best value ever recorded for this chassis family (a bound set in
  PROMOTE.md from runs.jsonl, e.g. 2.815, ste_half seed 0) could not pull the mean under
  the adoption threshold, stop; verdict `below`. Additionally, the stale-reference control
  (3 × 8 min champion re-run, PROMOTE.md) is run **once per fingerprint epoch** and shared
  by every trial judged while code_sha + corpus_sha are unchanged, instead of once per trial.
- **change:** `mill/screen.py` trial runner: judge after each seed against the two stop
  rules; `mill/trials.jsonl` gains `stopped_after` on the verdict event; the shared control
  is ledgered once with kind `control` and referenced by trial id. PROMOTE.md records both
  stop rules and the optimistic-bound constant.
- **payoff:** each guard-dead or mean-dead trial saves the full third seed = **8 min**.
  At an illustrative 20% promotion rate the pool yields ≈74 trials; if even ⅓ die on the
  first two seeds (the historical arms suggest most trials will fail — only 1 of 13
  completed arms beat the champion at all), that is ≈74 × ⅓ × 8 min ≈ **3.3 trial-hours
  per generation**, plus 24 min × (trials per epoch − 1) from control sharing. Promotion
  rate and dead-share are unmeasured until the mill runs — marked as such; the per-trial
  saving itself (8 min, zero-loss for stop (a)) is exact.
- **validity risk:** stop (b) smuggles in an assumption (the optimistic bound) — a freak
  third seed better than anything in runs.jsonl would be censored. Guard: the bound is set
  generously (best-ever seed minus a further 0.02), stop (b) verdicts are ledgered as
  `below (bounded)` so they are distinguishable and re-runnable on a human's word, and
  stop (a) — the zero-assumption half — is expected to do most of the saving anyway.

### TH-004 · Held-eval economy: cache held_init exactly, subsample held_final sequentially
- **source:** every run pays held_loss twice (init + final; train.py main and
  sweep_probe.run_one both do). Each call is 128 windows in 4 batches of 32 — derived
  ≈128 forward-equivalents ≈ 1.3 training steps ≈ **~4 s per call, ~8 s of a 75 s probe
  (~11%)**, and ~53% of a 15 s stage-0 budget, which is what makes cheap stages impossible
  while eval stays full-size. (Derived from step timing, not yet profiled — compute's
  probe_phases.py is the instrument that replaces this estimate; marked accordingly.)
  Meanwhile held_init is *deterministic*: seed-0 champion construction records exactly
  **8.3138** in runs.jsonl and the JEPA smoke test reproduced it exactly (RIGOR-AUDIT §2b).
- **mechanism:** (1) Cache held_init keyed by (seed, construction-affecting flags: arm
  family shape, --dim, --layers-n, rope, init-affecting flags); trainer-only flags share
  the cached value because construction — and therefore init held — is identical. The
  first run under any new key still measures it, and the sweep's 8.3138 invariant check
  runs against the cache. (2) held_final becomes sequential: evaluate a pre-registered
  nested 32-window subset first (held_windows' pick is evenly strided, so the first 32
  picks are themselves an even cover), compute the per-window SE of Δ vs job zero's
  same-subset Δ, and extend to 64, then 128, only while the verdict is inside the
  confidence margin of a bar (0.05/0.02). Clear verdicts stop at 32.
- **change:** `train.py`/`sweep_probe.py`: held_loss returns per-window losses (the
  reduction='sum' loop already visits batches; split to per-window accumulation);
  `mill/screen.py` holds the init cache in the ledger (kind `held_init`, keyed as above)
  and applies the sequential-extension rule; every ledger line records `held_n` actually used.
- **payoff:** init cache saves ~4 s on every trainer-flag probe (≈5% of probe cost;
  process-mode probes included). Sequential final eval saves ~3 s on the ~70% of probes
  whose 32-window Δ is clear of the bars (estimate from the historical Δ spread — most
  arms sat ≥0.10 from the champion) → combined ≈ **48 → ~52–53 probes/h solo**, and it is
  the enabler that keeps TH-001's 15 s stage from spending half its budget on evaluation.
- **validity risk:** per-window losses are heavy-tailed, so a 32-window SE can understate
  the true spread and stop early on a flattering subset. Guard: subsets are nested and
  fixed in advance (no adaptive window choice), extension is mandatory whenever the CI
  touches *either* bar, `held_n` is on every ledger line so any verdict can be re-checked
  at full 128, and TH-001's calibration set is also run at held_n ∈ {32, 64, 128} to
  measure the stopping rule's actual error before it judges live probes.

### TH-005 · Step-10 early kill from flip share + paired loss slope (kill-only predictor)
- **source:** at ≈3.0 s/step, steps 11–25 of a probe are 45 s — 60% of its cost — spent
  after the mechanism's vital signs are already readable. Flip share separates the
  recorded failures by an order of magnitude (mag 0.00010 vs champion 0.0011) and is
  seed-stable to ±3% for the champion; the anneal disaster (held 3.85, +0.99) is the class
  of run the mill should never pay full price for again. No probe has ever logged a
  mid-run reading, so the predictor's accuracy at step 10 is **unmeasured** — this entry
  is a measurement protocol first, a kill rule second.
- **mechanism:** sweep and process probes log, at step 10, flip share so far and the
  train-loss slope over steps 5–10, *paired* against job zero's same-step readings on the
  identical batch stream (same seed → same stream, the pairing the lab already relies on).
  A probe is killed at step 10 only if BOTH signals agree it is off-mechanism: flip share
  outside [0.2×, 3×] of job zero's AND paired slope worse by more than a calibrated margin.
  Train loss alone never kills (train_last100 is documented to misrank held). The rule
  activates only after its precision is measured on TH-001's calibration set plus the
  first 30 live probes' step-10 logs vs their completed verdicts (target: zero false
  kills on eventual `near`/`promote` probes; anything less keeps it advisory).
- **change:** `sweep_probe.run_one` + train.py probe path: emit a `MID` record at step 10
  (flip share, slope, steps) into runs.jsonl; `mill/screen.py` applies the kill only when
  `mill/PROBE-NOISE.md` carries an activated threshold pair with its measured precision.
- **payoff:** if the activated rule kills 25% of probes at step 10 (plausible against the
  46% catastrophe share, discounted for the both-signals-agree requirement), saving =
  368 × 0.25 × 45 s ≈ **69 min per pool pass**, i.e. ~15% on top of TH-001 (the two
  compose: stage 0 catches the diverged, step-10 catches the slow failures). Marked
  estimate — the kill rate is the calibration's output, not an input.
- **validity risk:** some mechanisms are late by design (leak/freeze/schedules act over
  the full run; F-002/F-022's pool text says a flat probe must not kill them). Guard:
  kill-only, never promote; exception-listed ids and any entry whose pool text declares
  a long-horizon mechanism are exempt by id list in screen.py; a killed probe is ledgered
  `kill10` with its mid readings, re-runnable on a human's word, and the activation gate
  (zero measured false kills) is the entry's own kill test.

### TH-006 · Dose-family sequential testing: middle dose first, extremes on evidence
- **source:** the pool is full of 3-point dose brackets that are currently paid in full
  regardless of outcome: mag-cal MILL-201/202/203, vsched 204/205/206, leak 209/210/211
  (+212/213), freeze 215/216/217, modal 218/219, plus the V grid (501–509, nine points),
  gate-q grid (601–606), scale-granularity, rope-frac, SWA and MoE brackets — conservatively
  ~45 sibling probes in ≥15 families. A dead family currently costs 3 × 75 s to learn one fact.
- **mechanism:** within a dose family, probe the middle (champion-nearest) dose first.
  Extremes run only if the middle lands `promote` or `near` (|Δ| < 0.05), or — the
  non-monotonicity hedge — if the middle is `flat` but the family's mechanism predicts a
  threshold effect, in which case exactly one extreme (the predicted-active side) runs.
  A `below` middle with no threshold prediction closes the family for the generation;
  the closure is ledgered per skipped sibling so the saving is auditable, not silent.
- **change:** pool-order/protocol change only: `mill/screen.py` gains a family map
  (family id per bracket, derivable from the pool's own "dose variant" source lines) and
  defers siblings until the middle's verdict exists; PROMOTE.md documents the rule and
  the threshold-effect hedge. No train.py change.
- **payoff:** a dead family costs 75 s instead of 225 s (saves 150 s); a live family costs
  the same as today. At ~15 families and the historical ~50% dead-family rate: ≈7.5 ×
  150 s ≈ **19 min saved per generation pass**, growing linearly if later waves add
  brackets the same way A–F did. Zero cost to winners by construction.
- **validity risk:** a genuinely non-monotone dose response (middle flat, extreme wins —
  e.g. a threshold that only bites at V=96) would be closed wrongly. Guard: the
  threshold-hedge run above; family closures are per-generation (a new champion re-opens
  them, as all verdicts do); and any family whose three pool predictions are non-monotone
  on their face is exempted in the family map at merge time.

### TH-007 · Fork screening for late-acting families: one trunk, several endings
- **source:** several pooled families differ *only* in what happens late in the run —
  vsched 204/205/206 (threshold path), freeze 215/216/217 (freezing bites after flips
  accumulate), polish MILL-306, tail-freeze-style entries — yet each pays a full
  independent 25-step probe whose first ~15 steps are bit-identical work: same seed →
  same init, same batch stream, and the flags do not act until late. Modal readout
  MILL-218/219 already exploits the readout version of this (one run, two verdicts,
  noted in RIGOR-AUDIT §1a); the fork generalises it to training endings.
- **mechanism:** for a certified late-acting family, run one shared trunk to the fork
  step (step 15 of 25 at probe scale), snapshot trainer state in-process, then branch
  each dose for the remaining 10 steps and score each branch against a job zero forked
  the same way (its own trunk, its own unchanged branch). Certification = the flag's
  code path provably cannot alter any update before the fork step (checked by reading
  the flag's implementation, recorded per family in PROBE-NOISE.md).
- **change:** `mill/sweep_probe.py`: an in-process fork mode for certified families
  (state snapshot/restore around branches; each branch still appends its own runs.jsonl
  record, tagged `fork:<family>`). Probe-only — trials are never forked.
- **payoff:** a 3-dose family costs 15 + 3 × 10 = 45 step-equivalents instead of 75 —
  **40% off forkable families** (225 s → ~135 s + snapshot overhead per family at probe
  scale). Applied to the ~4 clearly late-acting brackets above: ~6 min/pass today; the
  real value is that it scales with every future schedule/tail/readout family, which
  waves A–F kept producing. Estimate — snapshot overhead at this model size is small
  (2.2 MB mechanism state) but unmeasured.
- **validity risk:** a flag certified late-acting that actually leaks early influence
  (e.g. a schedule that pre-computes from total steps and changes step 1 behaviour)
  would make branches measure a trunk that never existed standalone. Guard: certification
  requires a step-10 log match — each branch's trunk-phase flip share and loss must equal
  the standalone probe's step-10 log (TH-005's MID record) the first time the family runs;
  any mismatch decertifies the family permanently and its fork verdicts are voided in the
  ledger, not silently kept.

### TH-008 · Steps as a ledgered covariate: adjust Δ for the machine, keep the wall clock
- **source:** probe verdicts are wall-clock verdicts, and the machine's speed is a
  measured confound: JEPA-control runs at 129–139 steps scored mean held 2.9173 vs the
  same config's 2.8580 at 154–170 steps — ≈+0.06 of held elevation riding on step count
  alone, larger than the 0.05 promotion bar. plain_half's seeds show the same coupling
  in miniature (176 steps → 2.8692 vs 150 steps → 2.9179). E-023 would fix this by
  changing the budget to fixed steps; this entry deliberately does not — it keeps the
  funnel's wall-clock semantics and removes the bias arithmetically.
- **mechanism:** every probe already ledgers `steps`. Per generation, fit the local
  steps→held slope from data the mill already owns: job-zero replicates across passes
  (same config, varying steps — a pure machine-speed instrument) plus the calibration
  arms. Report Δ_adj = Δ_raw + slope × (steps_probe − steps_jobzero) alongside Δ_raw.
  Promotion uses Δ_raw until the calibration shows Δ_adj has lower pass-to-pass replicate
  spread than Δ_raw on job zero itself; from then on Δ_adj is primary and Δ_raw is the
  reported cross-check. A crude first slope from plain_half's seeds is ≈ −0.0019/step,
  implying a ±5-step machine wobble at probe scale biases Δ by ≈ ±0.01 — 20% of the bar.
- **change:** `mill/screen.py`: compute and ledger both Δs (one extra field); the slope
  fit + the spread comparison live in `mill/PROBE-NOISE.md`, refreshed per generation.
  No change to budgets, budgets' meaning, or train.py.
- **payoff:** no probes/h gain on paper — the payoff is trial-hours: verdicts stop
  promoting step-lucky probes and killing step-starved ones. If step noise contributes
  even 0.01 of spurious Δ spread against a 0.05 bar, roughly 1 in 5 borderline verdicts
  is machine weather; at ~74 trials per generation that is on the order of **2–4 wasted
  or missed trials (48–96 min) per generation** reclaimed. Marked estimate — the slope
  and the spread reduction are measured by the entry's own first-generation fit.
- **validity risk:** the steps→held slope is itself estimated from confounded data
  (different seeds differ in more than steps), and over-adjusting could manufacture
  verdicts. Guard: the slope is fit on job-zero replicates first (steps vary there only
  via machine speed), the switch to Δ_adj-primary requires a *measured* replicate-spread
  reduction, and both numbers stay on every ledger line forever — any verdict can be
  re-read under the other convention.

### TH-009 · Proxy-context pre-screen: paired Δ at ctx 128 for context-free mechanisms
- **source:** per-step cost is dominated by tokens processed: batch 32 × ctx 256. The
  pool's own context entries (A-045/A-046 curricula, MILL-137/138 SWA) treat ctx as a
  variable, but the *screening format* has never used it: most pooled mechanisms — vote
  accounting, gates, counters, leaks, freezes (sections A/B of the pool) — make no
  reference to context length at all, yet every one of their probes pays full ctx-256 price.
- **mechanism:** a kill-only pre-screen at ctx 128 (batch 32): tokens/step halve, so the
  same 75 s buys roughly twice the steps (derived ≈1.7–2×, attention's quadratic term is
  small at dim 192/ctx 256 — marked estimate). The verdict is a *paired* Δ against job
  zero also run at ctx 128 in the same pass; absolute held values are never compared
  across contexts. A ctx-128 `below` (Δ ≤ −0.02, the flat/below boundary) closes the idea
  for the generation; anything else proceeds to the standard ctx-256 probe, which remains
  the only verdict that can promote. Excluded by construction: anything whose mechanism
  names position, context, RoPE, SWA, or attention span (MILL-133–138, 905/906, A-045/046,
  A-071, A-086/087 and kin) — for them ctx is the treatment, not the format.
- **change:** `mill/sweep_probe.py` + screen.py: a `--ctx` job field honoured by the
  pre-screen pass only (window slicing already exists in train.py's sampler shape);
  ledger lines record `ctx: 128` so a proxy verdict is never mistaken for a real one.
  Rank preservation (does ctx-128 Δ order ideas the way ctx-256 Δ does?) is measured on
  TH-001's calibration set at both contexts before the screen may kill anything.
- **payoff:** if ~60% of the pool is context-free mechanism (sections A/B dominate waves
  A–F) and the screen kills the historical ~45% loser share among them at ~40 s average
  cost instead of 75 s: saving ≈ 368 × 0.6 × 0.45 × 35 s ≈ **58 min per pass**, and the
  survivors arrive at the real probe with a second, independent-context reading attached.
  Estimates throughout — the calibration's rank-correlation number decides whether this
  entry lives.
- **validity risk:** vote dynamics are step-count-sensitive (more steps at ctx 128 =
  more flips banked), so a mechanism could genuinely behave differently, not just noisily,
  at the proxy context — the half-control's lesson (layered's win was its step count) is
  exactly this trap. Guard: kill-only asymmetry (a proxy pass never promotes, a proxy
  kill requires Δ ≤ −0.02 *and* flip share inside the champion's band, so step-regime
  artefacts that move flips disqualify the kill), plus the calibration gate: if the six
  known-answer arms do not preserve their ordering at ctx 128, the screen is retired
  before it judges a single live idea.

### TH-010 · Dual-read probes: every 75 s probe also yields its 15 s reading, for free
- **source:** TH-001 and TH-005 both need paired (short, full) readings to price their
  information loss, and a dedicated calibration campaign to get them costs ~30 extra
  probes (~37 min) per generation — and goes stale the moment the champion changes.
  Meanwhile every probe already *passes through* its own step-5/step-10 states and
  throws them away; job zero is re-measured fresh every pass and its early segment is
  likewise discarded.
- **mechanism:** probes and job zero log two extra readings in-flight: a 32-window
  subsampled held eval (TH-004's machinery, ~1 s) at the 15 s mark, and the TH-005 MID
  record at step 10. These readings are **log-only** — under the CANDIDATES-D §4 rule, a
  mid-run held value never feeds back into its own run; they exist so that, after each
  pass, the mill can compute the *realised* information loss of the 15 s stage and the
  step-10 predictor on live data (what would stage 0 have killed? what did it cost?)
  and recalibrate thresholds for the *next* pass. Job zero's 15 s reading doubles as the
  stage-0 baseline for that same pass — no separate stage-0 job zero is ever run.
- **change:** `sweep_probe.run_one` / train.py probe path: timed checkpoint eval at
  15 s (subsampled, log-only, stamped `dual_read` in runs.jsonl); `mill/screen.py`
  appends a per-pass stage-loss summary line to the ledger. Cost ≈1–2 s per probe.
- **payoff:** replaces a recurring ~37 min/generation calibration campaign with ~1–2 s
  per probe (~10 min spread across a full pass, most of it inside time already budgeted),
  and — the larger prize — it converts TH-001/TH-005 from one-off calibrations into
  continuously re-measured instruments, so their thresholds track champion changes
  instead of silently rotting. Net ≈ **25+ min saved per generation, every generation**,
  plus the audit trail that keeps the cheap stages honest.
- **validity risk:** the checkpoint eval perturbs the run it rides on (eval switches
  EASE to full rounding and back, costs ~1 s of the 75 s budget — a ~1–2% step tax on
  every probe, applied to job zero too, so the pairing absorbs most of it). Guard: the
  tax is identical for probe and baseline in the same pass; the first pass runs a
  parity check (dual-read job zero vs a clean job zero in the same pass must agree
  within the replicate spread, the CONCURRENCY.md honesty pattern) before dual-read
  verdicts are trusted for calibration.

### TH-011 · Fixed train-window proxy judge for the cheapest stage (spend held windows last)
- **source:** RIGOR-AUDIT §1b: every verdict is a selection event on the same 128 held
  windows, and the mill will issue thousands. The cheapest stages are where verdict
  volume is highest and individual verdicts matter least — exactly where the held set
  should not be spent. runs.jsonl already hints a proxy can rank: at 8 min, train_last100
  separates the catastrophe class cleanly (anneal 4.31–4.37 vs champion 3.03–3.15) even
  though it misranks the close arms — a proxy only needs to work where the cheap stage works.
- **mechanism:** fix a set of 128 *training* windows once (drawn via offsets(), held-safe
  by construction, frozen in a small file in mill/). Stage-0/stage-1 pre-screens judge
  paired Δ on this proxy set instead of held; held is touched only by the standard 75 s
  probe and above. Proxy Δ ships with its per-window SE (TH-004's per-window plumbing),
  so every proxy verdict carries a confidence, and the proxy↔held Δ correlation is
  tracked per pass from the probes that run both (TH-010's dual reads make this free).
- **change:** `mill/proxy_windows.json` (generated once by a offsets()-driven script,
  offsets ledgered); sweep_probe gains an eval-set switch used only by pre-screen jobs;
  PROMOTE.md states that no promotion, adoption, or champion reference ever reads the
  proxy set.
- **payoff:** throughput of *trustworthy* verdicts rather than raw probes/h: the two
  cheapest stages stop consuming held-set selection budget, which defers the
  confirmation-set pressure that otherwise grows with every generation — priced
  conservatively as avoiding one extra confirmation/control cycle (24–48 min) per
  generation, plus it makes TH-001's stage 0 judgeable at 15 s without the held-eval
  cost TH-004 prices at ~53% of that budget. Proxy↔held correlation at the catastrophe
  band is **unmeasured** — marked as such; the calibration set measures it first.
- **validity risk:** a proxy drawn from training windows can be memorised into
  uselessness as runs lengthen, and any idea whose mechanism interacts with the
  train/held distinction (failweight MILL-406/407, curriculum entries) would be judged
  on the wrong axis. Guard: proxy verdicts are kill-only and catastrophe-band-only;
  sampling-interacting families are exempt by id; the tracked proxy↔held correlation is
  printed per pass and the proxy judge auto-suspends if the correlation in the kill
  band drops below its calibrated floor.

### TH-012 · Process-mode caravan: amortise startup for code-path probes, prove isolation per job
- **source:** process-mode probes (every code-path change — the majority of waves A–F)
  each pay full interpreter + torch import + corpus memmap + held-window construction,
  which IDEA-POOL's execution-modes note calls "a large share of a 75-second probe's
  cost"; sweep mode already amortises it across batches of 8, process mode amortises
  nothing. The exact startup figure is **unmeasured** (compute/probe_startup.py exists
  to measure it; no results recorded yet) — this entry is conditional on that number.
- **mechanism:** run process-mode probes as a caravan: one parent process loads corpus
  and held windows once, then spawns each probe as a *fresh interpreter child* that
  inherits the read-only memmap via fork (copy-on-write; the child builds its own model,
  trainer, and RNG streams exactly as a standalone run). Isolation is not asserted, it
  is *checked per job*: each child must reproduce the seed-0 held_init invariant for its
  construction key (8.3138 for the champion shape, TH-004's cache) before training, and
  one job per caravan is randomly designated a parity job whose config is *also* run
  standalone in the same pass — the pair must agree within the solo replicate spread
  (the RIGOR-AUDIT §2b check, run continuously instead of once).
- **change:** `mill/screen.py`: caravan launcher for process-mode batches (children are
  ordinary train.py invocations with an inherited-memmap flag added to train.py);
  ledger lines record `caravan: <id>` and the parity pair's two readings. This is a
  measurement protocol around unchanged train.py runs — not the compute department's
  queue (no priorities, no leasing; screen.py's existing order is untouched).
- **payoff:** if startup+setup measures at ~10 s (estimate, to be replaced by
  probe_startup.py's medians), a caravan of 8 saves 7 × 10 s = 70 s per 8 process
  probes ≈ **12% on the process-mode share** — worth ≈25–30 min per full pass if
  process mode is ~half the pool. If the measured startup is <3 s, the entry retires
  itself: the payoff formula is printed with the entry so the decision is arithmetic.
- **validity risk:** a fork-inherited memmap is shared state a standalone run never
  has; a child that accidentally wrote through it would contaminate its siblings.
  Guard: the memmap is opened read-only (`mode="r"`, as train.py already does), the
  per-job held_init invariant catches construction drift before it can become a
  verdict, and the continuous parity job means any systematic caravan effect shows up
  as a parity failure within one pass — at which point caravan verdicts from that pass
  are voided and re-run standalone, ledgered as such.

---

## Ranking note

TH-001–TH-003 attack the funnel's shape (stage cost, seed spend, trial spend) and carry
the largest measured savings; TH-004–TH-005 make the cheap stages physically possible
and safe; TH-006–TH-007 stop paying full price for families whose members share most of
their information; TH-008–TH-012 each remove one named, measured tax (machine weather,
context price, calibration rot, held-set spend, startup) with a guard that can retire
the entry on its own numbers. Biggest single measured saving: **TH-003's guard-dead
stop — 8 min per affected trial at zero information loss**, with TH-002's ≈8–9
trial-hours per generation the largest expected aggregate.
