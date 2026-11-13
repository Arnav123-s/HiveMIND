# Muse's work — Muse's side

# Wave 6, Lens 2 — META-CONTROL: closed-loop control of the trainer's own dials

<!-- Muse's work — Muse's side of the BitNet lab. Not Fable's side; nothing here touches it. -->

Rotation-6 miner 2. Territory: **closed-loop** control, during a run, of the dials
`train.py` currently holds fixed — the vote threshold `V` (`Layered.votes = 32`),
the gate quantile `q` (hard-coded at the median in
`strong = g.abs() >= g.abs().median()`), the counter leak `λ` (no leak exists in
`train.py` today; MILL-209..213 pool *fixed* values of it), and the AdamW `lr`
(1e-3, constant in `Layered` except under the closed `--cooldown` schedule) —
driven by measured run state, with every control law stated exactly: signal,
update rule, bounds, stability guard, and the controller's own named failure mode.

**Boundary discipline (dedupe, read in full before filing).** The following are
taken and are NOT re-filed here, in any dose:

- Fixed, time-driven schedules: MILL-204/205/206 (V 32→64, 32→96, 24→48),
  MILL-109/110 two-stage lr, the closed 8→64 anneal and `--cooldown`. Every law
  below is a function of a measured signal; at constant signal it holds its dial
  constant forever, at any run length — that is the test each entry passes.
- MILL-207/208: **per-layer V servoed to a flip-rate target** (0.1% / 0.3%).
  Flip rate as the controlled variable for V is theirs. No entry below servos V
  to flip rate; MT-003 instead sits *above* MILL-207 and moves its setpoint.
- F-024: per-row scales servoed to an activity-RMS set-point. F-028: gate
  quantile `q` servoed to admitted gradient **mass** (set-point 0.60, fast
  attack / slow release). G-002: AdamW lr servoed to **flip share** φ.
  F-026: flip threshold widened by vote-stream **volatility** (bid–ask spread).
  F-027: flip-share-spike circuit breaker (a halt, not a servo). F-025: per-weight
  V erosion from counter stall age. A-008: per-weight V from own flip count.
  The I-wave zero-share homeostat: gate quantile nudged to hold installed zero
  share in a 40–46% band. G-065: flip share + loss slope used to *kill* probes
  (a verdict, not a control action).
- Every entry below therefore either (a) closes its loop on a signal none of the
  above use — executable-saturation share, WH-051 frustration, WH-060 c1/c2
  contest, WH-055 counter entropy, WH-059 counter kurtosis, WH-058 sub-flip
  oscillation, vote-stream sign coherence, flip productivity — or (b) is a
  meta-loop **above** a taken servo, setting that servo's setpoint or gain
  (MT-003, MT-007, MT-011), which the lens brief explicitly reserves.

**Signals borrowed from counter forensics (CANDIDATES-H), cited where used.**
WH-051 defines the *frustrated* population exactly: a component at a boundary
state whose counter is saturated with outward sign — its flip is a no-op and the
clamp silently absorbs further agreeing votes. WH-049..WH-060 supply the rest of
the counter-field vocabulary: WH-055 histogram entropy, WH-057 dead counters,
WH-058 sub-flip path/oscillation, WH-059 kurtosis, WH-060 the contested
population (sign(c1) ≠ sign(c2), both |c| ≥ 8). All of those entries are
*measurement only* — none of them actuates anything. This file is where those
signals get hands.

**Chassis and judging.** All entries run on the champion chassis,
`--arm layered_half --rope`, held **2.8580 ± 0.0161** at full format, judged
against MILL-000 job zero at probe budget first. All are `mode: process`
(isolated `train.py` subprocesses; every one changes a code path). Controller
state is a handful of floats per layer unless an entry says otherwise; any entry
that needs wider counters says so and charges the bytes. Universal guard,
inherited by every entry and not repeated in full: dials update at most once
per control interval (never per step, unless the entry says per step and why),
every dial is hard-clamped to the bounds stated, and every controller **fails
safe to the champion's fixed value** (V=32, q=0.5, λ=1.0 i.e. no leak beyond the
clamp, lr=1e-3) if its signal is undefined, NaN, or computed over fewer than
one interval of data.

---

### MT-001 ★ · Saturation-servoed V: the threshold follows the executable backlog
- **source:** control theory (PI control of a queue) + WH-051's code audit, split
  in two. WH-051 counts counters pinned at the clamp; this entry splits that
  population by the one property WH-051's census does not separate out: whether
  the pinned counter's flip is *executable* (the component is not at the boundary
  its sign pushes against, so reaching V would actually flip it) or *frustrated*
  (boundary-blocked; MT-002's signal). An executable backlog means evidence is
  queuing behind a threshold that is too high for the current gradient regime;
  a fixed V=32 cannot know that.
- **control law (signal → rule → bounds):** signal `s_t` = global share of
  counters (c1 and c2 pooled) with |c| = V whose pending flip is executable,
  EMA-smoothed over 20 steps (α=0.1), sampled every 20 steps. Target band
  s* ∈ [0.5%, 2%]. Integral-only update, once per interval:
  `V ← V − 1 if s̄ > 2%`, `V ← V + 1 if s̄ < 0.5%`, else hold (deadband).
  Bounds V ∈ [20, 48]. One step of V per interval, never more.
- **exact train.py change:** new flag `--sat-servo` on `Layered`. In `step()`,
  after the existing clamp, compute executability from tensors already present:
  `exec1 = (c1.abs() >= V) & ((t1 + c1.sign()).clamp(-1,1) != t1)` (and likewise
  c2/t2) — the same predicate already inside `go1/go2`, reused before the flip
  test; accumulate the pooled share into `self.sat_ema`; every 20 steps apply
  the rule to `self.votes` (today the local `V = self.votes` read at the top of
  `step()` makes this a one-line actuation). Log `V` and `s̄` in the step-100
  print line. No new per-weight state.
- **stability guard / own failure mode:** the failure mode is a **limit cycle**:
  lowering V drains the backlog in a flip burst, saturation collapses, the
  controller raises V, the backlog rebuilds — V hunting ±1 forever and the run
  effectively training at a dithered threshold. Guards: the deadband (a 4× wide
  target band, not a point), the 20-step interval (≥ the EMA's own horizon, so
  the controller never reacts to its own last action before that action's effect
  is measured), and the ±1 rate limit. Second failure mode: saturation is partly
  *caused* by the clamp itself — gaming by construction — which is exactly why
  the frustrated share is excluded from this signal and given its own dial
  (MT-002); if s̄ and frustration rise together, this controller is reading
  alphabet failure as backlog, and the logged pair (s̄, frustration) makes that
  confound visible in one probe.
- **prediction:** −0.01..−0.04 vs champion at full format. The mechanism claim is
  narrow and falsifiable from the log alone: in champion runs s̄ is predicted to
  sit outside the band for most of the run (early: above 2%, evidence-rich;
  late: below 0.5%, evidence-starved), i.e. fixed V=32 is wrong at both ends in
  opposite directions — no fixed schedule can express that, because the crossing
  times are state-driven, not clock-driven.
- **status:** queued
```mill
id: MT-001
mode: process
run: --arm layered_half --rope --sat-servo
```

### MT-002 · Frustration-servoed leak: pinned evidence is forgotten, live evidence is not
- **source:** WH-051 (frustration census) used as an actuator input for the first
  time + MILL-209..211's fractional leak, which pools λ as three *fixed*
  constants (0.99 / 0.98 / 0.95). Nobody has let the measured frustrated
  population choose λ. A frustrated counter is absorbing agreeing votes into a
  clamp and returning nothing; the longer it pins, the more of the run's evidence
  budget is spent on a state the ternary alphabet cannot express. Leak is the
  dial that retires pinned evidence: with λ < 1 a pinned counter decays off the
  clamp and its weight re-enters play.
- **control law (signal → rule → bounds):** signal `f_t` = WH-051 frustrated
  fraction, global, computed exactly as WH-051 defines it (component at boundary,
  counter saturated, outward sign), EMA over 20 steps, sampled every 20 steps.
  WH-051 predicts champion-family runs at 4–8% end-of-run. Rule (proportional,
  anchored at that band): `λ = clip(1.0 − 0.6·max(0, f̄ − 0.04), 0.96, 1.0)` —
  at or below 4% frustration there is no leak at all (champion behaviour); at
  8% frustration λ = 0.976; the floor 0.96 is reached only above ~10.7%.
  Applied per step as `c ← round(λ·c) + vote` in fixed point (see change).
- **exact train.py change:** new flag `--frust-leak` on `Layered`; requires the
  fractional-leak plumbing of MILL-209 (counters promoted to int16 fixed point,
  ×256 — charged: 4 B/weight of counter state vs the champion's 2 B, stated in
  the run record). In `step()`: compute the frustrated mask from (t1, c1) and
  (t2, c2) before the vote add (four comparisons on tensors already live), update
  `self.f_ema`, set `self.lam` by the rule, then apply leak inside the existing
  counter update in place of the bare `(self.c1[i] + vote).clamp(-V, V)`.
  Frustration fraction logged every 100 steps alongside flip share.
- **stability guard / own failure mode:** the failure mode is **self-exciting
  forgetting**: leak unpins counters → frustration falls → λ returns to 1.0 →
  counters re-pin → leak returns — a relaxation oscillation that periodically
  wipes the evidence of exactly the most-contested weights. Guards: the EMA +
  20-step sampling make λ move slowly against a 25–100-step pinning timescale;
  the 4% deadband means the loop is *open* (λ ≡ 1.0, bit-identical to champion)
  in the regime WH-051 calls healthy; and λ's floor (0.96, horizon 25 steps) is
  set no stronger than MILL-211's weakest pooled dose, so the controller can
  never reach a forgetting rate the pool hasn't already priced as a constant.
  Second failure mode — gaming: leak also decays *non*-frustrated counters,
  so the controller pays for unpinning with global memory loss; the per-layer
  frustration log is the audit (if frustration is concentrated in `down`, as
  WH-051 predicts, a global λ is the wrong scope and MT-008 is the repair).
- **prediction:** −0.01..−0.03, concentrated in the second half (frustration is a
  late-run population). Flat-or-better is also a verdict: if f̄ never leaves the
  deadband, the arm is bit-identical to the champion and WH-051's separator claim
  weakens — the probe reports f̄'s trajectory either way.
- **status:** queued
```mill
id: MT-002
mode: process
run: --arm layered_half --rope --frust-leak
```

### MT-003 ★ · Meta-loop: loss slope sets MILL-207's flip-rate setpoint
- **source:** cascade control (an outer loop trims an inner loop's setpoint —
  the standard industrial answer when the inner setpoint's right value drifts)
  applied to MILL-207, whose per-layer V servo holds flip rate at a *fixed*
  target (0.1% or 0.3%) chosen before the run. That target is a guess about how
  much structural churn the run can profitably absorb, and the profitable amount
  plainly changes as the loss curve bends. This entry files no new inner loop:
  it owns only the setpoint, which is the meta-level the brief reserves.
- **control law (signal → rule → bounds):** inner loop = MILL-207 unchanged
  (per-layer V, flip-rate target φ*). Outer signal: train-loss slope over the
  trailing 100 steps, `m_t` = (EMA₁₀₀ loss now − EMA₁₀₀ loss 100 steps ago)/100,
  normalised by the run's own first-100-step slope m₀, ρ = m_t/m₀. Outer rule,
  every 100 steps: `φ* ← φ* · 1.25 if ρ > 0.7` (loss still falling at ≥70% of
  its early rate — structure churn is still paying, allow more), `φ* ← φ* · 0.8
  if ρ < 0.3` (loss has flattened — churn is now mostly noise, ration it), else
  hold. Bounds φ* ∈ [0.03%, 0.4%], initialised at MILL-207's 0.1%.
- **exact train.py change:** new flag `--meta-flip-target` on `Layered`,
  requires `--vlayer` (MILL-207) to be active; `Layered` gains `self.phi_star`
  (one float) read by the vlayer update in place of its constant, plus a
  100-step loss ring buffer fed from `main()`'s existing `losses` list via the
  `step(loss, done)` argument the trainer already receives. Outer update inside
  `step()` gated on `self.steps % 100 == 0`. Both φ* and ρ logged every 100 steps.
- **stability guard / own failure mode:** the failure mode is **two loops
  fighting**: the inner loop moves V to chase φ*, the outer loop moves φ*
  because loss slope moved — but loss slope also moves *because* V moved, so the
  outer loop can chase its own tail (raise φ* → more flips → transient loss rise
  → ρ collapses → cut φ* → …). Guards: strict timescale separation — the outer
  loop's interval (100 steps) is ≥5× the inner servo's settling time, the
  classical cascade condition; multiplicative steps are small (±20–25%) and
  asymmetric in the safe direction (cuts are faster than raises, 0.8 vs 1.25);
  and ρ is computed on train loss *excluding* the 10 steps immediately after
  each outer update, so the transient the update itself causes is never read as
  evidence. Named residual risk: ρ conflates "churn stopped paying" with "the
  AdamW parts saturated" — the log separates them only if read next to G-002's
  φ-vs-slope correlation diagnostic; the entry accepts that ambiguity openly.
- **prediction:** −0.01..−0.04 over MILL-207 alone at full format (and therefore
  the comparison that matters is MT-003 vs MILL-207, not vs champion — the probe
  must run both). Predicted φ* trajectory: rises early (ρ ≈ 1), peaks mid-run,
  ends at or below its 0.03% floor — a *shape* no fixed target and no fixed V
  schedule contains.
- **status:** queued
```mill
id: MT-003
mode: process
run: --arm layered_half --rope --vlayer 0.001 --meta-flip-target
```

### MT-004 · Contest-servoed gate: c1/c2 disagreement tightens who may vote
- **source:** WH-060 (c1/c2 disagreement anatomy: the contested population —
  sign(c1) ≠ sign(c2), both |c| ≥ 8 — is predicted at 10–16% of weights and
  ≥35% of late flips) as a control input. F-028 servos the same dial (gate
  quantile q) on a different signal (admitted gradient *mass*); the gate's other
  failure is not mass drift but *evidence quality*: when the two components of
  the same weight persistently argue, the layer's gradient stream is internally
  inconsistent, and admitting the median-strength half of it (q = 0.5, the
  hard-coded `median()` gate) feeds that argument at full rate.
- **control law (signal → rule → bounds):** signal `κ_t` = global contested
  fraction per WH-060's exact definition, EMA over 20 steps, sampled every
  20 steps. Rule (proportional on q): `q = clip(0.5 + 1.5·(κ̄ − 0.10), 0.5, 0.8)`
  — at WH-060's predicted healthy κ ≈ 10% the gate is the champion's median
  gate; at κ = 20% only the top 30% by |g| vote; q never goes *below* 0.5
  (this controller may only ever tighten, never loosen past champion).
- **exact train.py change:** new flag `--contest-gate` on `Layered`. In `step()`,
  replace `strong = g.abs() >= g.abs().median()` with
  `strong = g.abs() >= g.abs().quantile(self.q)` when the flag is on; κ computed
  per layer from (c1, c2) already in scope (`(c1.sign() != c2.sign()) &
  (c1.abs() >= 8) & (c2.abs() >= 8)`), pooled globally into `self.k_ema`, q
  updated every 20 steps. Cost: one `quantile` per layer per step replaces one
  `median` — same complexity class, charged honestly at equal minutes.
- **stability guard / own failure mode:** the failure mode is **starving the
  argument instead of settling it**: tightening the gate excludes exactly the
  mid-strength votes that would eventually resolve contested weights, so κ stays
  high *because* q is high — the controller reads its own shadow as a permanent
  condition and the gate ratchets to 0.8 and stays (a windup analogue: not an
  integrator, but a one-way causal loop). Guards: q is a pure proportional
  function of the current κ̄ (no memory, no ratchet — if κ falls, q falls the
  same interval); the 20-step EMA prevents step-to-step gate flicker from
  decorrelating consecutive vote streams; and the tighten-only asymmetry is
  capped at 0.8 so at least the strongest 20% always vote — the contested
  population can never be fully disenfranchised, only slowed. Diagnostic that
  convicts the failure mode if it occurs: κ̄ and q logged together; q pinned at
  0.8 with κ̄ *rising* for >200 steps is the signature, and it is printable from
  one probe.
- **prediction:** −0.01..−0.03. Side value either way: the first causal test of
  WH-060 — if throttling votes *into* contested layers-by-proxy (globally, here)
  helps, contest is noise; if it hurts, contest was load-bearing exploration,
  and WH-060's anatomy flips sign as evidence.
- **status:** queued
```mill
id: MT-004
mode: process
run: --arm layered_half --rope --contest-gate
```

### MT-005 · Productivity-servoed lr: the FP parts speed up only while flips pay
- **source:** flip *productivity* — held-proxy loss improvement per flip — a
  signal no filed entry controls on. G-002 servos this same dial (AdamW lr) on
  flip *share* (how much structure moved); share says nothing about whether the
  movement helped. G-065 uses loss slope + flip share to kill probes early.
  Here the ratio of the two becomes the controlled quantity for the continuous
  parts: the embedding/norm/scale groups should train fastest exactly when the
  structure they must fit is both moving *and* improving, and should quiet down
  when flips have stopped buying loss (late-run churn), instead of fitting noise
  at full speed.
- **control law (signal → rule → bounds):** every 50 steps, productivity
  `p = −ΔL₁₀₀ / max(F₅₀, 1)` where ΔL₁₀₀ is the change in 100-step EMA train
  loss across the window and F₅₀ is the flip count in the last 50 steps
  (`step()` already returns flip share; the trainer accumulates it). Normalise
  by the run's own first-window productivity p₀. Rule:
  `lr_mult = clip(p/p₀, 0.4, 1.5)`, applied to all AdamW param groups in
  `Layered.opt`, smoothed: `lr_mult ← 0.7·lr_mult_prev + 0.3·clip(p/p₀, …)` so
  no single window moves lr by more than ~±20%. Base lr stays 1e-3; bounds are
  the multiplier's.
- **exact train.py change:** new flag `--prod-lr` on `Layered`: trainer keeps
  `self.flip_hist` (from its own `jumped/total` accounting, already computed),
  a loss EMA fed by the `loss` argument, and every 50 steps rewrites
  `g["lr"] = self.base_lr * self.lr_mult` for each param group — the same
  param-group write `--cooldown` already performs in this class, but driven by
  p/p₀ instead of `done`. lr_mult, p/p₀ logged every 100 steps.
- **stability guard / own failure mode:** the failure mode is **Goodharting the
  ratio**: lr itself affects ΔL, so the controller can discover that *cutting*
  lr makes short-window ΔL smoother and drive itself to the 0.4 floor and call
  it productivity — a controller gaming its own signal by changing the
  measurement conditions. Guards: p₀ is frozen from the first window (the
  yardstick cannot drift with the controller's own actions); the denominator
  floor `max(F₅₀, 1)` plus a rule that windows with F₅₀ < 0.02% of weights
  *hold* lr_mult rather than update it (near-zero flips make the ratio
  meaningless, not infinite); and the 0.4 floor guarantees the FP parts never
  train slower than the closed `--cooldown` arm's mid-run rate, so the worst
  case degrades toward a known arm, not an unknown one.
- **prediction:** −0.01..−0.03. Predicted trajectory: lr_mult ≈ 1.3–1.5 early
  (flips buying loss at the highest rate of the run), decaying through 1.0 to
  the 0.4–0.6 range late — i.e. the controller is expected to *invent* something
  shaped like a cooldown, but timed by measured payoff rather than by the clock
  that defined the closed arm; if it instead holds ≈1.0 throughout, productivity
  is scale-free in this trainer and G-002's share signal was sufficient.
- **status:** queued
```mill
id: MT-005
mode: process
run: --arm layered_half --rope --prod-lr
```

### MT-006 · Coherence-servoed V: the threshold prices how much the vote stream agrees with itself
- **source:** WH-058's premise (the informative action is *under* the flips, in
  the counters' path) reduced to its cheapest statistic. Define per-step vote
  coherence `a_t` = fraction of gated weights whose vote sign equals the sign of
  their own counter's accumulated direction (c1 and c2 pooled; counters at 0
  excluded). Coherence is the vote stream's self-consistency: high a means
  successive batches keep pushing the same way (evidence is a signal, a low V
  suffices); low a means the stream is arguing with its own recent past
  (evidence is mostly noise, and V — the number of net votes demanded — is
  exactly the dial that prices noise). F-026 prices *magnitude* volatility into
  a spread; A-011/A-012 filter the evidence per weight. Neither moves the global
  threshold on the stream's sign-consistency.
- **control law (signal → rule → bounds):** ā = EMA₂₀ of a_t, sampled every
  20 steps. Rule (stepwise proportional, deadbanded): `V ← V − 2 if ā > 0.75`,
  `V ← V + 2 if ā < 0.55`, else hold. Bounds V ∈ [16, 56] — the floor 16 is
  held at twice the poisoned anneal arm's hot start (8) deliberately, and the
  entry states why: coherence is *lowest* early, when gradients are least
  settled, so this controller's natural early move is to raise V, away from the
  known poison, not toward it.
- **exact train.py change:** new flag `--cohere-v` on `Layered`. In `step()`,
  after `vote` is formed (it already exists as a tensor), per layer compute
  agreement against the pre-update counters:
  `agree = (vote.sign() == c1.sign()) & (c1 != 0)` pooled with the c2 analogue
  over gated (strong) weights only; accumulate into `self.a_ema`; every 20 steps
  apply the rule to `self.votes`. No new per-weight state; ā and V logged
  every 100 steps.
- **stability guard / own failure mode:** the failure mode is a **coherence
  trap**: raising V means fewer flips, counters live longer and accumulate more
  one-directional history, so measured coherence *rises mechanically* — the
  controller then lowers V, flips resume, coherence falls, and the pair
  oscillates with the period of the counter lifetime (~V steps), not of any real
  signal. Guards: coherence is measured only on gated weights with |c| < V/2
  (young counters, whose sign is recent evidence, not the controller's own
  residue — this restriction is the guard, stated as part of the law); the
  ±2 step is small against the [16, 56] range; and the deadband [0.55, 0.75]
  is wide because ā's null level under random signs is 0.5 — the controller
  must see agreement clearly above chance before it spends threshold on it.
- **prediction:** −0.01..−0.03, with the highest diagnostic value in this file
  after MT-001: ā's trajectory is the first published trace of vote-stream
  self-consistency for this trainer, and if ā sits inside the deadband for the
  whole run the entry retires itself with that number attached.
- **status:** queued
```mill
id: MT-006
mode: process
run: --arm layered_half --rope --cohere-v
```

### MT-007 · Meta-loop: loss slope sets F-028's admitted-mass setpoint
- **source:** the second reserved meta-level: F-028's AGC holds admitted
  gradient mass at a set-point of 0.60 chosen by hand, forever. Whether 0.60 is
  right plausibly depends on training phase: early, gradients are diffuse and a
  0.60 mass target forces the gate wide (many marginal voters); late, gradients
  concentrate and 0.60 forces it narrow. This entry owns only the setpoint
  m*; F-028's fast-attack/slow-release inner loop is untouched.
- **control law (signal → rule → bounds):** outer signal ρ = normalised
  train-loss slope, computed exactly as in MT-003 (trailing-100-step slope ÷
  first-100-step slope), sampled every 100 steps. Rule:
  `m* ← m* + 0.03 if ρ > 0.7` (loss still falling fast — evidence is plentiful,
  admit more of its mass), `m* ← m* − 0.03 if ρ < 0.3` (flattening — restrict
  the vote to the strongest mass), else hold. Bounds m* ∈ [0.45, 0.75],
  initialised at F-028's 0.60. Inner loop reads m* in place of its constant.
- **exact train.py change:** new flag `--meta-agc` on `Layered`, requires
  `--agc` (F-028) active: the AGC's per-layer `q_t` update reads
  `self.m_star` instead of the literal 0.60; `self.m_star` updated in `step()`
  on `self.steps % 100 == 0` from the loss ring buffer shared with MT-003's
  plumbing (if both meta flags are ever combined, they share the buffer and
  update on the same tick — noted, not pooled as a combination here).
  m* and ρ logged every 100 steps.
- **stability guard / own failure mode:** the failure mode is **setpoint
  chasing a moving inner loop**: AGC's q_t needs ~20–50 steps to re-settle after
  m* moves (slow release is 0.005/step by F-028's own law), so an outer tick
  every 100 steps is only ~2–5 inner time-constants — marginal separation, and
  this entry says so rather than claiming cascade textbook conditions. Guards:
  the ±0.03 step is small against the [0.45, 0.75] range (a full traverse takes
  ≥1,000 steps); the deadband on ρ ([0.3, 0.7] = hold) means m* moves only on
  a clear phase change; and the post-update 10-step slope exclusion from MT-003
  applies here too. Second failure mode: ρ falls late in *every* run, so m*
  will predictably end low — if the end state is all the entry produces, it has
  reinvented a schedule with extra steps; the probe's defence is that the *time*
  of the descent is slope-triggered, and a paired fixed-m* F-028 probe at the
  same budget is the required control.
- **prediction:** −0.005..−0.02 over F-028 alone — the smallest expected effect
  in this file, filed because the setpoint question is currently answered by a
  constant nobody chose on evidence, and the meta-level is where the brief
  points. Kill criterion stated in advance: if m* never leaves [0.57, 0.63],
  the hand-set 0.60 was right and the entry retires at probe.
- **status:** queued
```mill
id: MT-007
mode: process
run: --arm layered_half --rope --agc 0.60 --meta-agc
```

### MT-008 · Per-layer frustration leak: MT-002's dial, at the scope WH-051 predicts
- **source:** WH-051's per-layer prediction — frustration concentrates in `down`
  projections by ≥2× over `qkv` — taken as a scoping instruction. MT-002 applies
  one global λ bought with global memory loss; if the frustrated population
  really lives in two of the eight BitLinear layers of `layered_half`, a global
  leak pays eight layers' worth of forgetting for two layers' worth of problem.
  This is a distinct entry from MT-002, not a dose of it: the controlled
  variable is a per-layer vector λᵢ, and the falsifiable claim is about scope.
- **control law (signal → rule → bounds):** per-layer frustrated fraction
  fᵢ (WH-051's definition, per layer), EMA₂₀, sampled every 20 steps.
  Per-layer rule, same anchor as MT-002 applied independently:
  `λᵢ = clip(1.0 − 0.6·max(0, f̄ᵢ − 0.04), 0.96, 1.0)`. Layers at or below 4%
  frustration run the champion's exact update; only frustrated layers leak.
- **exact train.py change:** new flag `--frust-leak-layer` on `Layered`; same
  int16 fixed-point counter promotion as MT-002 (charged identically). The
  frustrated-mask computation in `step()` is already per layer (the loop is
  `for i, m in enumerate(self.layers)`); this entry keeps `self.f_ema` and
  `self.lam` as per-layer lists and applies `self.lam[i]` inside layer i's
  counter update. Per-layer f̄ᵢ logged every 100 steps (8 numbers).
- **stability guard / own failure mode:** the failure mode is **inter-layer
  desynchronisation**: layers leaking at different rates hold evidence of
  different ages, so a downstream layer's counters describe a network whose
  upstream layers have since forgotten why they flipped — cross-layer staleness
  (F-010's named pathology) manufactured by the controller itself. Guards: all
  λᵢ share MT-002's floor (0.96) and anchor, so the maximum evidence-age ratio
  between any two layers is bounded at ~25 steps of horizon difference; the
  shared 4% deadband keeps the vector at all-1.0 (champion) whenever frustration
  is diffuse rather than concentrated — i.e. this controller activates *only*
  in the regime WH-051 predicts, and is inert in the regime that would convict
  its premise. Oscillation guard inherited from MT-002 (EMA + 20-step sampling
  per layer).
- **prediction:** −0.01..−0.03 vs champion, and ≥ MT-002's effect if WH-051's
  concentration prediction holds; if frustration turns out diffuse, MT-008 ≈
  MT-002 by construction and the pair together measure the concentration —
  run MT-002 first; MT-008's probe is only interpretable second.
- **status:** queued
```mill
id: MT-008
mode: process
run: --arm layered_half --rope --frust-leak-layer
```

### MT-009 · Kurtosis-pre-empted gate: tighten before the loss spike, not after
- **source:** WH-059 (counter-kurtosis early warning: field-shape spikes precede
  loss spikes) — the only *predictive* signal in WH-049..060, and the only one
  whose value exists solely if it is acted on *before* the event it predicts.
  Every other entry in this file is feedback (react to a measured state); this
  one is feedforward: kurtosis of the counter distribution is the leading
  indicator, the gate is the actuator, and the loss spike is the event being
  pre-empted. Distinct from F-028 (reacts to admitted mass, a coincident
  signal) and MT-004 (reacts to contest, a coincident signal).
- **control law (signal → rule → bounds):** signal: excess kurtosis K_t of the
  pooled counter distribution (c1, c2), computed every 10 steps from the
  counters' moments (no dump needed — four reductions). Baseline K₀ = median of
  K over the run's first 100 steps, frozen. Rule (event-driven, not
  proportional): if K_t > K₀ + 2.0, tighten the gate for the next 30 steps:
  `q = 0.7`; if K_t > K₀ + 4.0, `q = 0.85`. When neither condition has fired for
  30 consecutive steps, q returns to 0.5. The gate never loosens below the
  champion's 0.5. Each firing logged with step and K_t.
- **exact train.py change:** new flag `--kurt-gate` on `Layered`: moments
  accumulated inside the existing per-layer counter loop into four global sums,
  K assembled every 10 steps in `step()`; q applied exactly as in MT-004
  (`quantile(self.q)` in place of `median()`), with `self.q` driven by this
  entry's event rule instead of MT-004's proportional rule. The two gate
  entries share one plumbing change and must not be combined in one arm.
- **stability guard / own failure mode:** the failure mode is **crying wolf
  into a self-fulfilling calm**: if kurtosis spikes are actually *caused* by
  healthy large-scale reorganisation, tightening the gate suppresses the
  reorganisation, no loss spike follows, and the controller logs a perfect
  prediction record for events it prevented from being testable — unfalsifiable
  success, the worst outcome in this lab's terms. Guard, stated as part of the
  entry: the probe must report firing count and the counterfactual cannot be
  recovered from the same run, so the entry is judged **only** on held loss vs
  champion, never on "spikes avoided"; a flat held result with many firings
  retires it (it paid gate-tightening costs to prevent nothing measurable).
  Second guard: the 30-step tightening window is fixed and non-retriggerable
  while active, so a sustained high-K regime tightens in discrete 30-step
  blocks with 0.5-gated gaps between them — the run can never be locked into a
  permanently tightened gate by one long event.
- **prediction:** −0.005..−0.02 on average, but the distribution is the claim:
  most seeds ≈ champion (no spikes to pre-empt), the gain concentrated in the
  worst seed — this is a variance-reduction entry, judged on worst-seed held
  across the probe's seeds, and it should be promoted or killed on that
  statistic, not the mean.
- **status:** queued
```mill
id: MT-009
mode: process
run: --arm layered_half --rope --kurt-gate
```

### MT-010 · Oscillation-taxed leak: sub-flip thrash shortens evidence memory
- **source:** WH-058 (sub-flip oscillation anatomy: the argument underneath the
  flips — counters that travel far and net little) as a control input. Define
  the oscillation index per layer from quantities the trainer can maintain
  exactly: over a trailing 50-step window, `o = Σ|Δc| / max(|ΣΔc|, 1)` pooled
  over weights — a random-walk counter has o ≫ 1, a steadily-pushed counter has
  o ≈ 1. A-005's deadband forgets counters inside a band (a fixed rule);
  MILL-209..213 fix λ globally. Neither prices *measured* thrash into the
  forgetting rate. High o means the gradient stream is spending votes reversing
  itself inside the counters; a shorter evidence horizon (stronger leak) makes
  those reversals cancel sooner and stops stale opposition from delaying flips
  that current evidence supports.
- **control law (signal → rule → bounds):** ō = global oscillation index,
  EMA over the 50-step window itself, sampled every 25 steps. Rule:
  `λ = clip(1.0 − 0.02·max(0, ō − 3), 0.97, 1.0)` — at ō ≤ 3 (already a
  reversal-heavy stream by the definition) no leak; each further unit of ō
  costs 0.02 of λ; floor 0.97 (horizon ~33 steps) is weaker than every pooled
  fixed dose except MILL-209's 0.99, deliberately: this controller's signal is
  noisier than MT-002's census, so its authority is smaller.
- **exact train.py change:** new flag `--osc-leak` on `Layered`; same int16
  fixed-point counter promotion as MT-002 (charged identically). Path sums
  require one extra int16 accumulator per counter (`self.path1/path2`,
  +4 B/weight — charged, and the reason this entry is not cheap): each step adds
  |vote| contributions into the path accumulator and net Δc into a second;
  every 25 steps ō is computed, the accumulators reset, λ updated and applied
  inside the counter update as in MT-002. ō and λ logged every 100 steps.
- **stability guard / own failure mode:** the failure mode is **leak amplifying
  the thrash it measures**: shorter memory → counters reach V on shorter,
  noisier evidence → more flips → flips perturb gradients → more reversal → ō
  rises → more leak. A positive feedback loop with gain through the network
  itself, not just the arithmetic. Guards: λ's floor (0.97) caps the loop's
  authority below the weakest fixed dose the pool already tolerates as an
  *open-loop* constant — if the loop runs away it lands on a constant the lab
  has priced, not in uncharted territory; ō is computed over 50 steps and λ
  updates every 25, so the controller integrates over ≥2 flip-generation cycles
  before acting twice; and ō explicitly excludes weights that flipped inside the
  window (their path is post-reset and would read as pure oscillation — a
  measurement artefact, excluded by construction).
- **prediction:** −0.005..−0.025. Honest prior: this is the entry most likely to
  return a clean zero — ō may sit ≤ 3 for the whole champion run, in which case
  the arm is the champion plus logging, and WH-058 learns that sub-flip thrash
  at this scale is modest. Filed because a priced zero on the lab's most-cited
  unmeasured pathology is worth one probe.
- **status:** queued
```mill
id: MT-010
mode: process
run: --arm layered_half --rope --osc-leak
```

### MT-011 ★ · The watchdog: a meta-controller that detects a servo oscillating and takes its authority away
- **source:** supervisory control / gain-scheduling practice — every inner loop
  filed in this wave (and MILL-207, F-028 before it) carries an oscillation
  failure mode that its own guards *reduce* but cannot *detect*. Detection
  requires standing outside the loop and watching the dial itself, which no
  filed entry does. This entry controls no dial directly: it watches one inner
  controller (specified per arm; the pooled form watches MT-001's V), measures
  the dial's own dynamics, and degrades the inner loop's authority in graded
  steps when the dial — not the loss, not the signal — shows a limit cycle.
  It is the meta-level in its purest form in this file.
- **control law (signal → rule → bounds):** signal: the inner dial's trajectory
  (e.g. V_t sampled at its own update ticks). Oscillation statistic: sign-change
  count of Δdial over the trailing 12 ticks, `z`, plus dial range over the same
  window, `r`. Rule (graded, evaluated every 12 inner ticks): if `z ≥ 8` and
  `r ≥ 4` (V units; rescaled per dial), halve the inner loop's step size
  (MT-001: ±1 → ±1 every *other* interval; generic form: step × 0.5, floored at
  0.25× nominal) — authority level 1. If oscillation persists for the next 12
  ticks at level 1, **freeze** the dial at its trailing-12-tick median for the
  rest of the run (authority level 2 — the arm degrades to a fixed-dial run at
  a measured, not guessed, value). If z ≤ 3 for 24 consecutive ticks at level 1,
  restore full authority (the watchdog can forgive). Bounds: the watchdog may
  never move a dial itself, never widen an inner loop's bounds, and never act
  before 24 inner ticks of history exist.
- **exact train.py change:** new flag `--watchdog` on `Layered`, composable with
  exactly one inner control flag (pooled form: `--sat-servo`); implementation is
  a small `Watchdog` class in `train.py` holding the dial's tick history, called
  from the inner controller's update site with (dial value, nominal step),
  returning the permitted step multiplier and a possible freeze value the inner
  update must honour. Watchdog level and every transition logged; the run record
  gains `watchdog_level_final`. Overhead: floats, no per-weight state.
- **stability guard / own failure mode:** the failure mode is **the watchdog
  mistaking adaptation for oscillation**: a healthy controller tracking a
  genuinely moving regime (early-run V *should* walk in one direction, then
  reverse once as the regime changes) can trip z ≥ 8 if the regime itself
  oscillates — e.g. batch-stream periodicity — and the watchdog then freezes a
  dial that was doing its job, converting a controlled run into a fixed-dial run
  at a mediocre value. Guards: the range condition `r ≥ 4` alongside z (a dial
  twitching ±1 around a point has z high but r small — that is deadband
  behaviour, explicitly *not* punished; only full-range hunting counts); the
  freeze value is the window *median*, not the current value, so a freeze lands
  mid-range rather than at an extreme; and level-1 halving precedes any freeze,
  giving a merely-noisy loop a chance to settle at reduced gain — the classical
  answer, since most limit cycles are gain problems before they are concept
  problems. The watchdog's own stability is trivially guaranteed: its actions
  are monotone in authority (full → half → frozen, with one forgiving edge),
  so it cannot itself oscillate a dial.
- **prediction:** ≈ 0.000 on arms whose inner loop is stable (the watchdog is
  inert — by design, and the probe must confirm inertness, not assume it) and
  −0.01..−0.03 of *insurance value* on arms where the inner loop hunts: the
  honest framing is that MT-011 is not a gain entry, it is what makes the other
  eleven entries safe to promote past probe scale, where longer runs give limit
  cycles time to develop that a 75-second probe cannot exhibit. Judged on:
  (a) zero held Δ vs MT-001 alone when inert, (b) in a deliberately
  destabilised control arm (MT-001 with its deadband removed — a *test fixture*,
  not a pooled candidate), the watchdog restores held to within 0.01 of the
  guarded MT-001.
- **status:** queued
```mill
id: MT-011
mode: process
run: --arm layered_half --rope --sat-servo --watchdog
```

### MT-012 · Dead-counter-servoed lr on log_scale only: when structure stops testifying, scales take the gradient alone
- **source:** WH-057 (dead-counter census: counters that never move — the
  silent-weight population as wasted capacity) crossed with F-001's insight
  that pressure which cannot move structure can still move scale. Scope is the
  narrowest in this file: of the AdamW groups, only `log_scale` (the per-layer
  install scales, whose gradient is the hand-set `(g·s)·scale`) is actuated.
  G-002 servos lr on flip share across emb/norm groups and *exempts* log_scale;
  this entry actuates exactly the group G-002 exempts, on a signal G-002 does
  not use.
- **control law (signal → rule → bounds):** signal `d_t` = dead fraction:
  share of counters (c1, c2 pooled) whose value has not changed in the trailing
  50 steps and which sit at |c| ≤ 2 (never engaged — distinct from WH-051's
  frustrated, who are maximally engaged and blocked). Tracked with a per-counter
  last-change step stamp (one int16 per counter, +4 B/weight — charged; see
  change). Sampled every 50 steps, EMA-smoothed (α=0.3 at that cadence). Rule:
  `scale_lr_mult = clip(1.0 + 4·max(0, d̄ − 0.15), 1.0, 2.0)` — below 15% dead,
  scales train at the champion's lr; at 35% dead, they train at 2× — the layer's
  magnitude channel works harder exactly when its structural channel has gone
  quiet. All other param groups: champion lr, untouched, forever.
- **exact train.py change:** new flag `--dead-scale-lr` on `Layered`: the
  `log_scale` parameters are split into their own param group at `self.opt`
  construction (today they are appended to the single AdamW call in
  `Layered.__init__` — the split is mechanical and changes nothing at mult 1.0);
  `self.last_change` int16 tensors updated in `step()` wherever counters are
  written (`torch.where(c_new != c_old, step, last_change)`); every 50 steps
  d̄ is computed, and the scale group's `lr` rewritten as in MT-005's plumbing.
  d̄ and scale_lr_mult logged every 100 steps.
- **stability guard / own failure mode:** the failure mode is **scales absorbing
  the loss that structure should have taken**: raising scale lr lets the model
  buy loss reductions by rescaling layers instead of flipping weights, counters
  go *deader* as gradients shrink through rescaled layers, d̄ rises, scale lr
  rises again — a quiet runaway that ends with a well-scaled random-ish
  structure, F-055's reservoir wearing a fitted suit. Guards: the 2.0 cap (the
  runaway, if it starts, saturates at a bounded, known rate); the deadband at
  15% (WH-057 has never published the champion's dead fraction — if it is
  naturally ~30%, the anchor is wrong and the probe's first log line says so,
  which is why the anchor is stated as a number and not hidden); and the
  decisive audit is built into the prediction — dead fraction and flip share are
  both already logged quantities, so the runaway's signature (d̄ ↑, flips ↓,
  held flat) is distinguishable from the intended signature (d̄ ↓ as scales
  re-shape gradients, held ↓) in a single probe record.
- **prediction:** −0.005..−0.02, the weakest prior in this file, filed last
  deliberately: it is the only entry whose actuated parameter can *substitute*
  for the mechanism under study rather than assist it, and the lab should learn
  that price from its cheapest possible experiment. Kill criterion: if d̄ at
  probe end exceeds its value at the first sample while held is not better than
  champion, retire without a trial.
- **status:** queued
```mill
id: MT-012
mode: process
run: --arm layered_half --rope --dead-scale-lr
```

---

## Coordinator's ranking and the one to trust first

**★ Top 3: MT-001, MT-003, MT-011.**

1. **MT-001 — trust this one first.** Its signal is the only one in the file
   that is (a) exactly computable from tensors already live inside
   `Layered.step` (zero new state, zero estimation), (b) mechanically coupled
   to its dial — a backlog of executable flips behind the threshold *is* a
   statement about the threshold, with no interpretive step in between — and
   (c) bounded into harmlessness: ±1 per 20 steps inside [20, 48] with a wide
   deadband means the worst case is a run that wanders gently around V=32,
   i.e. around the champion. Every other entry inserts at least one inference
   (that contest means noise, that kurtosis means danger, that slope means
   churn stopped paying); MT-001's inference is one step long. It also produces,
   as a by-product, the executable/frustrated split of WH-051's census that the
   forensics wave never separated.
2. **MT-003** — the cleanest meta-level entry: it files no new inner loop, it
   repairs the one arbitrary constant inside an already-pooled servo
   (MILL-207's fixed flip-rate target), and its guard (≥5× timescale
   separation) is the textbook condition, checkable from the design rather than
   hoped for.
3. **MT-011** — expected value ≈ 0 as a gain and highest as infrastructure:
   it is the only entry that makes the *rest* of the closed-loop programme
   promotable to long horizons, where the limit cycles it exists to catch have
   time to appear. Its destabilised-fixture test is the most falsifiable
   protocol in the file.

**Run order note:** MT-002 before MT-008 (scope question is only interpretable
in that order); MT-004 and MT-009 share gate plumbing and must never be combined
in one arm; MT-007's probe is uninterpretable without a paired fixed-setpoint
F-028 control at the same budget.

*End of wave-6 lens 2 (meta-control). 12 entries, MT-001..MT-012, all queued,
all `mode: process` on `--arm layered_half --rope`. Champion held 2.8580 ±
0.0161 is the bar throughout.*
