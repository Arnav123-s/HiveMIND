# Muse's work — Muse's side

# LENS 2 — CROSS-DOMAIN TRANSFER candidates for the vote trainer (Idea Engine, miner 2)

<!-- Muse's work — Muse's side of the BitNet lab. Nothing here touches Fable's side.
Candidate file only: nothing is in the pool until the pool's owner merges it. -->

**Lens:** import mechanisms from OTHER fields and map each one concretely onto the
vote trainer in `train.py`. Every entry names its source-field mechanism precisely
and states the exact `train.py` change — no analogies without a flag.

**Chassis (all entries unless stated):** champion `layered_half` + rotary, held
**2.8580 ± 0.0161**, V=32 net strong votes to flip a ternary weight, counters clamp
±V (int8), median strong gate (q=0.5), batch 32, one component flip per weight per
step (t1 first, t2 only if t1's flip is a boundary no-op), flipped counter resets
to 0. Extra state bytes are charged in each entry that spends them.

**Dedupe (mandatory pass, done before generating):** read in full —
`mill/IDEA-POOL.md` (MILL-000…, incl. merged stream A as §F), `mill/CANDIDATES-A.md`,
`B`, `C`, `D`, `FABLE-CANDIDATES.md` (and `CANDIDATES-E.md` for safety), plus
`train.py`. Nothing below restates a pooled/candidate mechanism or a closed arm.
Closed and NOT re-proposed: overshoot carry, AdamW cooldown, threshold anneal
8→64, magnitude votes as specified, JEPA. Deliberately avoided as already owned:
deadband / hysteresis / leak / thrash tax & freeze (A + pool — the control-theory
standards), calibrated magnitude votes (MILL-201..203), vote schedules & per-layer
flip-rate V (MILL-204..208), modal readout, hybrids, annealflip, DisARM, resid8/16,
verify-flips, whitening, Cautious-vote masking (B-014), SpinQuant/Schedule-Free
(B — literature transplants), dream/replay in all forms (CANDIDATES-D — sleep
replay is TAKEN, per orders). Where an entry sits near an owned mechanism, the
entry itself names the neighbour and the exact difference.

**Top 3 (★):**
- ★ **XD-001 Anti-windup** — the defect is visible in `train.py` itself: counters
  sit clamped at ±V while their flip is blocked; that banked saturation is pure
  integral windup and conditional integration is its textbook, parameter-free cure.
- ★ **XD-002 TPDF dither** — one line before the median gate; breaks the limit
  cycles a hard 1-bit gate + sign quantizer is guaranteed to produce, at zero state.
- ★ **XD-003 Byzantine sub-electorates** — the only entry that changes *who votes*:
  3-of-4 independent sub-batch electorates must agree, so no single noisy batch
  (the Byzantine voter) can ever move a counter.

---

### XD-001 · Anti-windup: conditional integration at the saturated boundary ★
- **source:** control theory — anti-windup by conditional integration (Åström & Wittenmark): when the actuator is saturated, the integrator stops accumulating in the saturating direction.
- **mechanism:** In `Layered.step` today a component at its boundary (t=+1, vote pushing +1-ward, or t=−1 pushing −1-ward) cannot flip — `want != t` fails — yet its counter keeps integrating and sits clamped at ±V. That is integral windup: when the gradient later reverses, the weight must first unwind up to 32 banked votes before any reverse progress registers, so saturated weights are systematically the last to correct. Anti-windup rule: if the flip a vote argues for is a boundary no-op for that component, the vote is NOT integrated into that component's counter this step (the other component integrates normally). Counters therefore never hold evidence for a move that is physically impossible; reversal latency at saturated weights drops from ~V steps to ~0.
- **train.py:** new flag `--anti-windup` on `Layered` (and `Direct`): in the vote loop, mask the increment per component — `inc = vote * ((t + vote.clamp(-1,1)).clamp(-1,1) != t or sign(c) != sign(vote))` in effect: integrate freely when the vote reduces |c| or argues a legal move; skip only same-direction votes while at the boundary. No new state, no new hyperparameter.
- **mode:** process
- **prediction:** −0.01..−0.04. The gain concentrates in weights that reach ±1 early and later need to come back — exactly the population the anneal disaster showed is mishandled. Diagnostic logged at trial: mean counter value among boundary-blocked weights (should sit near 0 under this arm vs pinned at ±32 on the chassis).
- **status:** queued
```mill
id: XD-001
mode: process
run: --arm layered_half --rope --anti-windup
```

### XD-002 · TPDF dither before the median gate ★
- **source:** signal processing — dither (Lipshitz & Vanderkooy): triangular-probability-density noise added before a coarse quantizer to decorrelate quantization error from the signal and destroy limit cycles.
- **mechanism:** The vote path is two cascaded 1-bit quantizers — the median gate (pass/fail) and `sign(g)` — fed by a deterministic gradient stream. Undithered, weights whose |g| sits just under the layer median are starved deterministically and gradient patterns near the threshold lock into limit cycles (the same weights vote / don't vote in a fixed pattern). Add TPDF noise `d = (u1 − u2) · 0.5 · median|g|` (u1,u2 ~ U(0,1), per weight, per step) to g before BOTH the gate comparison and the sign: `vote = −sign(g + d) · 𝟙[|g + d| ≥ median|g|]`. Sub-threshold weights now vote with probability proportional to their distance below the median; supra-threshold weights occasionally abstain. Counters, V, clamp unchanged; zero extra state (noise is ephemeral).
- **train.py:** new flag `--dither 0.5` on `Layered`/`Direct` (argument = dither amplitude in units of the layer median |g|; TPDF from two uniform draws inside `step`).
- **mode:** process
- **prediction:** −0.01..−0.03, plus a measurable side effect: the flip-count distribution across weights should flatten (fewer never-vote weights). Distinct from A-024 (ε-greedy flips act AFTER the counter, at random, ignoring evidence) and A-015 (stochastic flip at crossing): dither acts BEFORE quantization, is evidence-shaped, and never flips anything by itself.
- **status:** queued
```mill
id: XD-002
mode: process
run: --arm layered_half --rope --dither 0.5
```

### XD-003 · Byzantine quorum: 3-of-4 sub-electorates must agree ★
- **source:** distributed consensus — Byzantine fault tolerance (PBFT, Castro & Liskov): with f faulty voters, a decision needs 2f+1 of 3f+1 independent votes; here f=1, so 3 of 4.
- **mechanism:** Today one batch of 32 casts one vote per weight: a single atypical batch is a Byzantine voter with full voting power. Split the batch into 4 sub-electorates of 8 windows; run the backward per sub-batch and take each sub-batch's gated sign vote independently. The counter increments by the MAJORITY sub-vote only when at least 3 of 4 sub-electorates agree on its sign; on a 2–2 split or 2–1 plurality the weight abstains (counter unchanged). Correlated noise inside one sub-batch can no longer move any counter, and the vote that does land carries a quorum certificate: it was the majority view of independent samples, not one draw.
- **train.py:** new flag `--byz 4:3` on `Layered`: main loop splits each batch into 4×8, calls a sub-step backward per slice accumulating per-slice votes, applies the 3-of-4 rule, then one AdamW step on the summed gradient. Cost charged honestly: 4 backward passes per step on ¼-batches (≈ same FLOPs, worse efficiency — expect ~0.8× steps/minute; judged per step AND per minute at trial).
- **mode:** process
- **prediction:** −0.01..−0.05 per step; per minute it must overcome its own overhead. Distinct from A-003 (accumulates 4 micro-batches into ONE summed vote — a single bad micro-batch still contributes its sign mass; no agreement test exists) and A-109 (two counters over alternating batches, both must fill — a time split, not a simultaneous quorum).
- **status:** queued
```mill
id: XD-003
mode: process
run: --arm layered_half --rope --byz 4:3
```

### XD-004 · Sortition: a randomly drawn jury votes each step
- **source:** voting theory / Athenian democracy — sortition: office-holders and juries chosen by lot each term, so no fixed faction can capture the process and every citizen serves in expectation equally.
- **mechanism:** Each step, for each layer, draw a fresh random 25% subset of weights (without replacement, RNG independent of the batch stream). Only jury members integrate this step's vote and only jury members may flip; non-members' counters and states are frozen for that step. Over 4 steps every weight serves once in expectation, but no weight can be stampeded by a short correlated run of batches — between its jury terms, contrary fashions pass it by — and simultaneous-flip interference is cut 4× because at most 25% of weights are ever eligible on the same step. Unlike a rotation, the lot is redrawn independently each step: eligibility is unpredictable, so no periodic data pattern can synchronise with a weight's voting days.
- **train.py:** new flag `--sortition 0.25` on `Layered`/`Direct`: per-step Bernoulli/fixed-size mask in `step`, applied to the increment and to `go1/go2`. No extra persistent state (mask is per-step).
- **mode:** process
- **prediction:** −0.01..+0.02 — genuinely two-sided: it is a variance/capture trade, slowing each weight's evidence rate 4× while cleaning it. The probe's job is pricing that trade. Distinct from A-018 (block-staggered flips: deterministic rotation at BLOCK level, flips only — votes still accumulate everywhere every step) and A-016 (batched flips: everyone votes, flips deferred).
- **status:** queued
```mill
id: XD-004
mode: process
run: --arm layered_half --rope --sortition 0.25
```

### XD-005 · Quadratic voting: votes are bought from a per-step credit budget
- **source:** economics / social choice — quadratic voting (Lalley & Weyl): casting intensity x of influence costs x² credits from a fixed budget, so broad weak preferences are priced out and concentrated conviction is what gets expressed.
- **mechanism:** Per layer per step, define intensity r = |g| / median|g| for each strong-half weight. Admitting a weight's vote costs r² credits. Votes are admitted in descending r order until the step's credit budget B is spent, where B = 0.25 × Σ r² over the strong half (so the budget is a fixed share of the step's total would-be cost, self-calibrating across layers and training phases). Admitted weights cast the usual ±1 vote; the rest abstain. Effect: on steps where gradient mass is concentrated (a few weights really matter), almost all strong weights still vote — their rivals are cheap. On diffuse steps (mass spread thin, r ≈ 1 everywhere), only ~25% vote: the mechanism refuses to spend the network's flip budget on steps where no weight stands out. The median gate today treats both regimes identically (top half always votes at flat cost).
- **train.py:** new flag `--quad 0.25` on `Layered`/`Direct`: inside `step`, per layer compute r, sort descending (one sort per layer per step, charged), admit by cumulative r² ≤ 0.25·Σr², zero the non-admitted votes before the counter update.
- **mode:** process
- **prediction:** −0.01..−0.04. Distinct from MILL-601..606 gate-q (admits a fixed FRACTION at flat cost), A-001 soft gate (scales increments continuously, no budget, everyone above median still counts), and MILL-201..203 calibrated magnitude votes (increment SIZE carries intensity; here increments stay ±1 and intensity buys ADMISSION under a hard budget).
- **status:** queued
```mill
id: XD-005
mode: process
run: --arm layered_half --rope --quad 0.25
```

### XD-006 · Veto player: the output row can veto a flip
- **source:** political science — veto-player theory (Tsebelis): a change from the status quo requires the assent of every veto player; any one of them can block, and blocking preserves the status quo without erasing the proposal.
- **mechanism:** A weight at threshold flips only if its output ROW (its veto player) does not dissent: compute the row's mean vote this step over all weights in that row of the matrix; if sign(row-mean vote) is non-zero and opposite to the flipping weight's counter sign, the flip is vetoed for this step. The counter is NOT reset — the proposal stays on the table and can pass on a later step when the row no longer dissents (veto ≠ the sign-agree flip rule, which arbitrates between two components at one weight; the row is a different constituency with its own aggregate interest: a lone weight flipping against the direction its whole neuron is moving usually means its evidence is idiosyncratic noise, while a weight flipping WITH its row rides a coherent feature change).
- **train.py:** new flag `--row-veto` on `Layered`: in `step`, after computing `vote`, reduce it per output row (mean over dim −1); `go1/go2` additionally require `row_sign == 0 or row_sign == c.sign()`. No new state.
- **mode:** process
- **prediction:** −0.01..−0.03, with flip share down ~10–30% (vetoed flips are logged). If flip share collapses instead, the row signal is too coarse at width 192 and the entry dies on its own log.
- **status:** queued
```mill
id: XD-006
mode: process
run: --arm layered_half --rope --row-veto
```

### XD-007 · Benna–Fusi cascade: a fast counter drives a slow counter
- **source:** neuroscience — the Benna–Fusi cascade model of synaptic memory (Benna & Fusi, 2016): a chain of coupled variables with progressively slower timescales gives power-law memory lifetimes — fast variables absorb new evidence, only evidence that persists propagates down the chain and becomes durable.
- **mechanism:** Replace the plain chassis's single counter per weight with a serial cascade of two counters that are NOT both installed (this is not layered t1+t2, whose components sum into the weight). Fast counter cf (clamp ±8) receives every vote. Whenever cf saturates at ±8, it transfers one unit into the slow counter cs (cs += sign(cf), cf -= sign(cf)·8 — a carry INSIDE the cascade, between timescales, not the closed overshoot carry on a flip). The ternary weight flips only when |cs| ≥ 4, i.e. after ~32 net votes have each survived the fast stage's saturation test repeatedly; cs then resets. One-off bursts die in cf; only evidence that keeps arriving across many steps ever reaches cs. Effective memory lifetime scales ~quadratically in the stage thresholds instead of linearly in V.
- **train.py:** new trainer path `--cascade 8:4` on the `Direct` chassis (chassis-changing entry: `--arm plain_half --rope --cascade 8:4`): two int8 counters per weight (2 B/weight vs plain's 1 B — charged), transfer rule in `step`, flip test on cs only.
- **mode:** process
- **prediction:** −0.02..+0.02 at probe horizon (the cascade's advantage is a long-horizon property — a flat probe does NOT kill it; verdict at full trial). Distinct from fractional leak MILL-209..211 (a single counter forgetting exponentially — the cascade forgets as a power law and never decays cs at all) and from A-006's race (parallel up/down counters with a total-count condition; no timescale coupling).
- **status:** queued
```mill
id: XD-007
mode: process
run: --arm plain_half --rope --cascade 8:4
```

### XD-008 · Synaptic consolidation: importance raises a weight's personal V
- **source:** neuroscience / continual learning — synaptic intelligence & EWC (Zenke et al. 2017; Kirkpatrick et al. 2017): synapses that were important for past performance are consolidated — made harder to change — in proportion to an online importance integral.
- **mechanism:** Each weight accumulates an importance ω = EMA(β=0.99) of g² (the online Fisher proxy). Its personal flip threshold is V_i = V · (1 + ω_i / median(ω)) clipped to [32, 96]: the median weight keeps the champion's threshold, a weight carrying 2× median gradient energy needs up to 3× the evidence to flip. Important synapses consolidate; unimportant ones stay plastic at the proven setting. The asymmetry is the point no existing entry has: thrash tax raises V from a weight's own FLIP history (behaviour), consolidation raises it from its gradient-energy history (function) — a weight can be heavily consolidated without ever having flipped, and a chronic flipper with tiny gradients stays cheap to flip.
- **train.py:** new flag `--consol-v` on `Layered`: per-weight fp32 ω (4 B/weight, charged) + int16 counters (clamp per-weight at ±V_i, max 96); flip test `|c| ≥ V_i` per weight in `step`.
- **mode:** process
- **prediction:** −0.01..−0.04. Watch the zero-fraction: consolidation should preferentially protect the ±1 population that carries the features, letting the zero population keep reorganising.
- **status:** queued
```mill
id: XD-008
mode: process
run: --arm layered_half --rope --consol-v
```

### XD-009 · Homeostatic scaling: per-row scales servoed to an activity set-point
- **source:** neuroscience — homeostatic synaptic scaling (Turrigiano): each neuron multiplicatively rescales all its synapses up or down to hold its firing rate at a set-point, on a slow timescale, independent of the Hebbian signal.
- **mechanism:** Today each BitLinear layer has ONE learned `log_scale`, trained by the hand-set gradient (g·t)·scale. Replace it with per-OUTPUT-ROW scales that are not gradient-trained at all: a forward hook keeps an EMA of each row's output RMS; every 10 steps each row's install scale is multiplied by exp(η·(log RMS_target − log RMS_row)), with RMS_target = the layer's median row RMS and η=0.05. Rows that shout get turned down, rows that whisper get turned up, and the layer's total scale budget is conserved (median-anchored). The vote counters then compete inside a layer whose rows are activity-equalised, instead of inside one where a few high-scale rows dominate every downstream gate statistic.
- **train.py:** new flag `--homeo 0.05` on `Layered`: per-row scale buffer in `install()` (fp32, dim floats per layer — negligible bytes), RMS EMA hook on each BitLinear forward, servo update every 10 steps replacing the `log_scale` gradient path for vote arms.
- **mode:** process
- **prediction:** −0.01..−0.05; the most architectural entry in this file. Distinct from MILL-107 per-channel scales (a static absmean STATISTIC at finer granularity — no feedback, no set-point, no time dynamics) and MILL-1013 learn-scale (gradient-learned): homeostatic scales are servoed to measured activity by a rule that never sees the loss.
- **status:** queued
```mill
id: XD-009
mode: process
run: --arm layered_half --rope --homeo 0.05
```

### XD-010 · Supermajority decay: a stalled counter's threshold erodes
- **source:** voting theory / DAO governance — decaying supermajority (quorum decay): a proposal that cannot reach its supermajority sees the required threshold decay over time, so persistent minorities cannot filibuster a persistent majority forever.
- **mechanism:** Each counter carries an age: steps since it last changed sign or flipped. A counter that has held the same sign for 50 steps without reaching V is stalled evidence — a durable majority that the fixed supermajority keeps disenfranchising. Its personal threshold erodes by 1 per further 50 stalled steps, floored at V/2 = 16: V_eff = max(16, 32 − floor((age − 50)/50)). Age resets on flip or sign change. The floor and the age condition are what separate this from the closed 8→64 anneal: nothing here is ever hot for YOUNG evidence (the poison that killed the anneal arm) — erosion is earned only by evidence that has already survived 50+ steps pointing one way, and 16 is far above the poisoned 8.
- **train.py:** new flag `--stall-decay 50:16` on `Layered`: per-component int16 age tensor (2 B/weight, charged), per-weight V_eff in the flip test; counters clamp at ±32 as now (clamp is not the threshold).
- **mode:** process
- **prediction:** −0.01..−0.03. Diagnostic: the counter-age histogram at end of run — if almost no counters ever stall past 50 steps, the mechanism has no population to act on and the entry is void, not wrong. Distinct from MILL-204..206 global V schedules (time-based, identical for all weights regardless of their evidence history) and A-008 thrash tax (raises V after flips; this lowers it after stalls — opposite sign, opposite trigger).
- **status:** queued
```mill
id: XD-010
mode: process
run: --arm layered_half --rope --stall-decay 50:16
```

### XD-011 · Bid–ask spread: the flip threshold widens with vote-stream volatility
- **source:** economics — market microstructure (Glosten–Milgrom): a market maker quotes a bid–ask spread that widens with adverse-selection risk / volatility; you may trade, but crossing a wide spread costs more conviction.
- **mechanism:** Treat a flip as a trade: the counter must cross not V but V + spread/2 on either side, where the per-layer spread is quoted from the vote stream's own volatility: churn_t = fraction of strong votes whose sign disagrees with that weight's previous-step vote (the stream's realised volatility). spread = round(16 · EMA₀.₉₅(churn)), so V_eff ∈ [32, 48], recomputed per layer per step, and V_eff can only widen from the champion's 32, never narrow below it. In calm regimes (gradients pointing consistently) the spread collapses and trading is at champion cost; in churn regimes — where flips are most likely to be noise — the market charges more evidence. This is a volatility quote, not a rate controller: it does not target any flip rate, it prices the current disagreement.
- **train.py:** new flag `--spread 16` on `Layered`: per-layer churn EMA (one float per layer), per-layer integer V_eff used in both the clamp and the flip test each step. No per-weight state.
- **mode:** process
- **prediction:** −0.01..−0.03. Distinct from A-007 hysteresis (a STATIC asymmetry between the 0↔±1 boundaries, fixed at build time) and MILL-207/208 per-layer V (adapts V to hit a target flip RATE by feedback; the spread adapts to vote-stream VOLATILITY and has no target rate).
- **status:** queued
```mill
id: XD-011
mode: process
run: --arm layered_half --rope --spread 16
```

### XD-012 · Circuit breaker: a flip storm halts trading, not rationing
- **source:** economics — exchange circuit breakers (NYSE Rule 80B lineage): when movement in a session exceeds a threshold, trading HALTS for a cooling period; orders are not rationed, the market closes and reopens.
- **mechanism:** The runner tracks the trailing 100-step mean flip share (≈0.11% on this chassis). If a single step's flip share exceeds 3× that mean AND 0.5% absolute, a breaker trips: for the next 10 steps NO flips are applied anywhere (counters keep integrating and clamping normally, AdamW parts keep training), then trading reopens automatically. Rationale: a flip storm means the network just moved under its own gradient stream — the next several batches' gradients describe a network that no longer exists, and their flips compound the shock. A halt lets the continuous parts re-fit the new structure before more structure moves. Every trip is logged (step, share, trailing mean).
- **train.py:** new flag `--breaker 3:10` on `Layered`: breaker state (halt counter + trailing flip-share ring) in the trainer; `go1/go2` masked to false while halted. No per-weight state.
- **mode:** process
- **prediction:** −0.01..+0.02 — the honest prior is that storms are rare at 0.11% mean share, so the entry may simply never trip, which is itself the measurement (log `trips=0` retires it). Distinct from A-017 flip cap (rations flips WITHIN every step by overshoot ranking — the market never closes) and A-019 quarantine (per-weight, triggered by its own flip-flop, not by a market-wide event).
- **status:** queued
```mill
id: XD-012
mode: process
run: --arm layered_half --rope --breaker 3:10
```

### XD-013 · AGC gate: automatic gain control on admitted gradient mass
- **source:** signal processing — automatic gain control (receiver design): a feedback loop with fast attack and slow release holds the admitted signal LEVEL at a set-point by continuously adjusting gain, whatever the input level does.
- **mechanism:** The median gate fixes the admitted FRACTION at 50% of weights, but the admitted gradient MASS (Σ|g| over strong weights ÷ Σ|g| overall) swings freely as the gradient distribution changes shape over training. AGC instead holds admitted mass at a 0.60 set-point: each layer keeps a live gate quantile q_t (init 0.5); per step, measure admitted mass m_t; if m_t > 0.60, q_t rises with fast attack (+0.05/step, gain down — fewer, stronger voters); if m_t < 0.60, q_t falls with slow release (−0.005/step, gain up), q_t ∈ [0.2, 0.9]. The gate then uses q_t in place of the fixed 0.5 quantile. As gradients concentrate late in training (a few large, many small), the fixed gate admits ever more of the total mass through ever more marginal weights; AGC tightens admittance to keep the counter's diet constant in the units that matter — energy, not headcount.
- **train.py:** new flag `--agc 0.60` on `Layered`/`Direct`: per-layer q_t float + attack/release update inside `step`, replacing the hard-coded `median()` gate with a `quantile(q_t)` gate.
- **mode:** process
- **prediction:** −0.01..−0.03. Distinct from the MILL-601..606 gate-q grid (STATIC quantiles — each is one frozen gain setting; AGC is the loop that moves between them) and A-001 soft gate (continuous weighting at a fixed median; no feedback, no set-point).
- **status:** queued
```mill
id: XD-013
mode: process
run: --arm layered_half --rope --agc 0.60
```

### XD-014 · Gossip diffusion: counters average with their neighbours
- **source:** distributed consensus — gossip / epidemic averaging (Demers et al.; Kempe et al.): nodes repeatedly average their state with random neighbours and the whole system converges to the global mean without any coordinator, robust to node failure.
- **mechanism:** Every 10 steps, each counter diffuses toward its spatial neighbours in the weight matrix: c ← clamp(c + 0.25 · (mean of the 4-neighbour counters − c)), neighbours taken along both matrix axes with circular wrap, applied to c1 and c2 independently, with no flip test on diffused values (flips are still only ever caused by voted crossings on normal steps). Weight matrices are not spatially random — adjacent columns share input features, adjacent rows share output units, and the QKV projection packs q|k|v in row bands — so a weight whose evidence is strong but whose neighbours all lean the other way is probably reading a local artefact; diffusion lets coherent regional evidence reinforce and isolated counter spikes dissipate before they can spend a flip. It is the only entry that couples DIFFERENT weights' evidence.
- **train.py:** new flag `--gossip 0.25:10` on `Layered`: every 10 steps in `step`, a shift-and-average pass over each counter tensor (4 `roll` ops), then clamp to ±V. No persistent state.
- **mode:** process
- **prediction:** −0.02..+0.03 — the widest honest range in this file: the spatial-coherence prior is real for embeddings/QKV bands and weak for FFN matrices, and the per-layer read at trial will show which. Distinct from MILL-232 whitening (rotates the GRADIENT basis per layer; counters stay independent) — nothing pooled couples counters across weights at all.
- **status:** queued
```mill
id: XD-014
mode: process
run: --arm layered_half --rope --gossip 0.25:10
```

### XD-015 · PID flip test: proportional and derivative terms join the integral
- **source:** control theory — PID control: the counter is only the Integral term; a full controller also acts on the Proportional (current error rate) and Derivative (its rate of change) terms.
- **mechanism:** The chassis flips on the integral alone: |c| ≥ 32, blind to whether the evidence is accelerating or dying. Add the missing two terms per weight, in fixed point: a fast evidence tracker r (int16, ×16 scale) updated r += vote·16 − r/4 each step (EMA horizon ≈ 4 steps — the Proportional term, P = r/16 ∈ [−1, 1] in vote units, scaled ×4); the Derivative term D = (r − r_prev)/16, the change in evidence rate. Flip test becomes |c + 4·P + 4·D| ≥ V with sign taken from the combined signal, counter reset as usual on a flip. Accelerating evidence (P and D aligned with c) crosses early — the controller anticipates instead of waiting for the integral to fill; evidence that is decelerating or reversing (D against c) must fill the integral honestly. This is anticipation/braking on the flip DECISION, not on the evidence stream.
- **train.py:** new flag `--pid 4:4` on `Layered`: per-component r and r_prev int16 tensors (4 B/weight total, charged), combined-signal flip test in `step`; counters and gate unchanged.
- **mode:** process
- **prediction:** −0.01..+0.02, ranked last on complexity-per-prior: it spends the most state in this file for the least certain return, but it is the only entry that makes the flip rule a function of evidence DYNAMICS rather than evidence totals. Distinct from A-011 vote-EMA (smooths the incoming VOTE and still flips on the plain integral of it) and A-012 (weights votes by EMA agreement; no derivative term, no anticipation).
- **status:** queued
```mill
id: XD-015
mode: process
run: --arm layered_half --rope --pid 4:4
```

---

## Miner 2 notes for the pool owner

- All 15 are `process` mode honestly: every one needs a flag `train.py` does not
  have yet, so `screen.py` should DEFER them until their flag lands (pool law).
  None was dressed up as a sweep entry.
- Cheapest first contact: XD-001, XD-002, XD-012, XD-006 add no persistent state
  and are each a few lines inside `Layered.step` — they can share one wiring pass.
- The transfer I trust most is **XD-001 (anti-windup)**: it is the only entry whose
  target defect can be pointed at in the current code — counters clamped at ±V
  while `want != t` blocks their flip — and its fix is a rule, not a tuned knob,
  so a win cannot be a hyperparameter accident.
- Two entries carry explicit self-voiding diagnostics (XD-010's stall histogram,
  XD-012's trip count): if the population/event they act on does not exist at this
  scale, their logs say so and they retire without a verdict fight.
