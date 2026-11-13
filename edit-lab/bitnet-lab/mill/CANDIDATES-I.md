# CANDIDATES-I — Idea Engine wave I (Muse's work, Muse's side)

<!-- Muse's work — Muse's side of the BitNet lab. Produced 2026-11-12 by the Idea Engine
(rotation 4: negative space, second-order combinations, long horizon, discrete search,
hive-side wave 2, kernel semantics) under Arnav's no-limit ideation order. CANDIDATE
file: nothing here is in the pool until the pool's owner merges it. IDEA-POOL.md was
read by every miner and NOT edited. The hive-side lens of this rotation (HV-001..HV-012)
is merged into factory/CANDIDATES-IDEAS.md instead of this file. Waves F/G/H are
CANDIDATES-F.md / CANDIDATES-G.md / CANDIDATES-H.md. -->

## Method and de-duplication

Every miner deduped against IDEA-POOL.md (368 entries), CANDIDATES-A/B/C/D/E/F/G/H and
FABLE-CANDIDATES.md. The negative-space lens read the whole union (~11,470 lines) and
REJECTED several presumed gaps with citations before filing only the sub-dimensions
that survived (its verified gap list opens Lens 1 below). Nothing closed re-proposed.
Chassis/bars as in waves F–H: champion held 2.8580 ± 0.0161; adoption >2sd AND >0.01.

## Coordinator's top 3 for this wave ★

1. **I-001 · Init-seed × stream-seed factorial** — one `--seed` in train.py drives BOTH
   `torch.manual_seed` (init) and `random.Random` (batch stream); the champion's
   ±0.0161 sd has never been decomposed into its two halves. Every verdict the lab has
   issued inherits that ambiguity; unwelding the seed re-prices all of them, cheaply.
2. **I-025 · Stale-bank purge** (with I-026, saturation creep) — counters outlive the
   model that earned them; the long-horizon lens's warning is that ALL current verdicts
   are issued in the one regime where counters are young and unsaturated, which
   systematically underprices leak/layered arms and overprices front-loading arms.
   I-026's proxy is a logging-only census on runs the mill already executes.
3. **I-015 · Stream-walk × Benna–Fusi cascade (G-014 × F-022)** — the combination the
   combinations miner would bet on: each member's own filed prediction names the
   other's absence as its limiting factor. Predicted both −0.04..−0.08 against
   two-sided singles. (I-016 is the wave's cheapest certain information: a predicted-
   interference pair where one of two filed premises must lose.)

**Boldest entry: I-049 · Vote-then-sum** — per-token majority voting via an integer
sign-GEMM replaces magnitude-summed evidence entirely, capping the numeric-dump corpus
share's influence at its token share; it changes the evidence statistic itself, with
its detectability limit priced in-entry (τ = 5% net majority ⇒ only p ≳ 0.55 per-token
agreement votes at all).

---

## Lens 1 — Negative space (was NG-###)

### Verified gaps (each entry below lives in exactly one)

- **GAP-1 · The seed is two variables welded together.** In train.py's
  `main()`, one `--seed` sets `torch.manual_seed(a.seed)` (the init) AND
  `random.Random(a.seed)` (the batch stream). The union spends seeds
  (economy: G-037/G-039/G-062/G-063, E-022), ensembles them (G-036/G-052),
  and — in G-049/G-050 — deliberately holds the init seed *fixed* while
  varying the data seed, for merge commensurability. No entry crosses
  init-seed × stream-seed factorially, and no entry decomposes the
  champion's ±0.0161 seed SD into init share vs stream share. Verified by
  grep: every "data seed / init seed" hit in the union is a G-049/G-050
  merge context. → I-001.
- **GAP-2 · Language share has never been a dose.** On v2, the union varies
  German's *placement* at fixed 45.7% share (G-019), the *period* at which
  sources alternate at fixed ratios (G-016), ratios *staged over time*
  (B-001), per-*file* balance (A-048 — changes language share only as an
  unmeasured side effect), a per-batch diversity floor (A-053), and one
  contaminated file's excision (E-021). No entry sweeps the static German
  share {0%, ~23%, 45.7%} at fixed total tokens with per-language held
  slices. The dose–response curve of the majority language does not exist.
  → I-002.
- **GAP-3 · The gate has never been scoped or set by projection role.**
  Two narrow survivals here, checked separately: (a) **scope** — the gate
  median is computed over a whole BitLinear matrix; pooled scopes are
  per-layer (default), per-row (A-002), per-state (F-005). But train.py's
  attention projection is one *fused* `qkv` matrix (dim→3·dim): Q rows,
  K rows and V rows, three roles with different gradient distributions,
  share a single median. No entry scopes the gate per projection slice
  inside `qkv`. (b) **level** — V is role-split (A-026: attention 48 /
  FFN 24) and the trainer is role-split (A-032), but gate-q is only ever
  set uniformly per layer (MILL-601..606 + interactions MILL-651..654).
  No entry sets gate-q by role. → I-003 (scope), I-004 (level).
- **GAP-4 · Quantiles are only ever a single threshold.** MILL-601..606
  move the one cut; F-028 servos that cut to hold admitted *mass*;
  A-005's deadband is a single multiple of the median (0.25×) with erosion
  below it. No entry uses *two* order statistics of the same |g|
  distribution as a band — counted above an upper quantile, eroded below
  a lower quantile, silent between. The interquartile band as the gate's
  shape is untested. → I-005.
- **GAP-5 · Phase is varied lever-by-lever, never attributed.** The union
  has first-only levers (A-023 warmup, A-034 gate ease-in), last-only
  levers (A-022 tail freeze, A-036 collapse at 75%), halves (MILL-220..222
  hybrid phases, A-110 reset at 50%), thirds (A-045 ctx curriculum) and a
  cycle (A-033 cyclic V). No entry takes *one* lever and applies it in
  exactly one run-third per arm — first vs middle vs last — so no lever's
  effect has ever been located in time. The middle third in particular
  hosts no isolated intervention anywhere in the union. → I-006.
- **GAP-6 · Position inside the window is weighted, never partitioned —
  and the FP loss is never touched.** F-013 reweights the *vote-path*
  gradient by log position (AdamW parts explicitly untouched); G-022
  shortens whole windows (late positions then appear only in long
  batches); G-017/G-018/G-023 change which positions text lands at.
  No entry (a) restricts a step's loss to one position *band* of a
  full-length window, or (b) removes any position band from the *shared*
  loss that trains the FP parts as well as the votes. → I-007, I-008.
- **GAP-7 · Time-between-flips enters only as age or count, never as
  trend.** F-025 uses a counter's stall *age* (time since sign change);
  A-008 uses flip *count* in a window (a rate); F-004 uses vote
  consistency since the last flip. No entry uses the *change* in a
  weight's inter-flip interval — acceleration — as a signal or a control
  input. A weight flipping every 40 steps and a weight whose intervals
  run 80 → 40 → 20 are indistinguishable to every pooled rule. → I-009.
- **GAP-8 · Context length is monotone, random, or fixed — never cyclic.**
  A-045/046: monotone thirds (length confounded with phase, as G-022
  itself notes). G-022: stationary random mix (no order at all). A-089:
  fixed 512. No entry cycles ctx deterministically (64→128→256→128→…),
  the one design that is ordered like a curriculum but phase-balanced
  like a mixture. → I-010.
- **GAP-9 · Held is sliced by source, never by target-token frequency.**
  Per-source slices exist (G-019, E-021). Token frequency appears only on
  the *training* side (tail-row V, TK-family embedding entries). No entry
  reports held binned by the target token's corpus frequency, so the lab
  does not know which frequency band its 2.8580 is made of — or which
  band any arm's Δ lives in. → I-011.
- **GAP-10 · Held is sliced by position only inside one entry's arms.**
  G-018 logs per-position held loss as a diagnostic *for its own BOS
  comparison*. No standalone entry bins the standard held eval by
  position bucket for the champion family, so rotary's one confirmed win
  (−0.0411) has never been located inside the window it supposedly
  improves. → I-012.

### Rejected gaps (suggested, checked, already covered — do NOT file)

- "Language as a variable" in general — covered: G-019, G-016, B-001,
  A-048, A-053, E-021. Only the static dose (GAP-2) survives.
- "Position as a variable" in general — covered: F-013 (vote weighting),
  G-017 (stride lattice), G-018 (BOS anchoring), G-023 (phase dither),
  MILL-133..135 (partial/no RoPE). Only loss partitioning (GAP-6) and the
  standalone eval slice (GAP-10) survive.
- "Phase beyond first/last" in general — covered: A-033 (cyclic V),
  A-035/A-036 (grow/collapse), A-110 (midpoint reset), MILL-220..222.
  Only same-lever phase *attribution* (GAP-5) survives.
- "Seed as a variable" in general — covered as economy/ensemble/init
  (above). Only the init×stream weld (GAP-1) survives.
- "Ctx as curriculum" — covered: A-045/A-046, G-022, A-089, G-069. Only
  the cyclic form (GAP-8) survives.
- "Attention vs FFN treated identically by every vote rule" — **false as
  stated**: A-026 splits V by role, A-032 splits the trainer by role,
  A-029 splits V by head, A-025/MILL-207/208 split V by depth/layer.
  Only the *gate* (scope and level, GAP-3) is genuinely role-blind.
- "Other quantiles as the gate threshold" — covered: MILL-601..606
  (q = 0.0..0.9, layered and plain) and MILL-651..654 (q×V interactions).
  Only the two-quantile *band* (GAP-4) survives.
- "Time since a flip as a signal" — covered in first order: F-025
  (stall age), A-008 (flip count), F-004 (consistency since flip).
  Only the interval *trend* (GAP-7) survives.
- Counter clamp ≠ threshold, counter reset variants, without-replacement
  sampling, per-part lr, log_scale optimizer/trust region — all covered
  (MILL-64x clamp grid, A-020, G-021, G-001, G-003/G-006). Not filed.

---

## Entries (ranked)

### I-001 ★ · Init-seed × stream-seed factorial: unweld the seed and price its two halves
- **source:** verified GAP-1 — train.py `main()` drives both
  `torch.manual_seed(a.seed)` and `random.Random(a.seed)` from one flag;
  the union's only init/data seed separation (G-049/G-050) holds init
  fixed for merging and never crosses the factors.
- **mechanism:** Four probe arms at champion config: (init, stream) ∈
  {(0,0) = champion, (1,0), (0,1), (1,1)}. (0,0) is job zero, already
  paid. The three new runs decompose the seed SD: if (1,0) ≈ (1,1) ≉
  (0,0) ≈ (0,1), variance is init-driven; if the pairing flips, it is
  stream-driven. Every mill verdict since the pool opened has spent
  "seed" as one currency; this prices which half of it the ±0.0161
  champion SD actually is — and whether future paired comparisons should
  pair on init, on stream, or (as now, accidentally) on both.
- **train.py:** split the flag — `--init-seed` (default = `--seed`) fed
  to `torch.manual_seed`, `--stream-seed` (default = `--seed`) fed to
  `random.Random`; record both in runs.jsonl. Defaults reproduce every
  existing arm bit-for-bit.
- **mode:** process
- **prediction:** stream share ≥ 60% of seed variance at probe scale
  (a ~40-step probe sees ~1,280 windows; which windows is the larger
  dice roll), init share rising at trial scale as early flips compound.
  The crossed arm (1,0) lands within ±0.02 of (0,0)'s family mean — the
  weld itself is predicted to be worth nothing, which is exactly why
  breaking it is free information. If instead (0,0)/(1,1) cluster apart
  from the crossed pairs, the coupling is load-bearing and every
  cross-seed comparison in the ledger inherits a confound nobody priced.
- **status:** queued
```mill
id: I-001
mode: process
run: --arm layered_half --rope --init-seed 1 --stream-seed 0
```

### I-002 ★ · German dose–response on v2: 0% / 23% / 45.7% at fixed tokens, per-language held
- **source:** verified GAP-2 — v2's actual mix (45.7% German / 41.9%
  HiveMIND docs / 12.4% lab notes, DATA-AUDIT §7) has been placed
  (G-019), period-swept (G-016) and staged (B-001), never dosed.
- **mechanism:** Three v2 arms, identical total tokens, identical
  HiveMIND:lab ratio within the non-German remainder, fully shuffled:
  German share 0%, 22.9% (half-dose), 45.7% (the built mix = E-018's
  re-baseline arm, reused, not re-run). Judged on pooled v2 held AND on
  German-majority vs English-majority held slices (G-019's slicing,
  reused). For a vote counter the dose question is sharper than for STE:
  German Tatoeba lines are short and formulaic, so their votes are
  unusually *consistent* — a 45.7% share may be supplying cheap,
  agreeing evidence that props up the pooled number while taxing the
  English structure the lab actually cares about, or the reverse.
- **train.py:** sampler weights by source class on the v2 stream —
  `--de-share 0.0|0.229` (depends on the same `--corpus v2` path as
  E-018/G-016; per-source held slicing is eval-side tagging, no new
  held data, held predicate applied per source before weighting).
- **mode:** process
- **prediction:** the German slice improves monotonically with dose
  (≥0.10 from 0% to 45.7%); the English slice is *best at 22.9%* and
  worse by +0.02..+0.05 at 45.7%; pooled held is flat within ±0.02
  across doses — i.e. the built mix sits past the pooled optimum and
  the pooled number cannot see it. Any of the three patterns (monotone
  pooled win for 45.7%, monotone loss, or the predicted slice split)
  sets the mixture policy for v3; a flat-everywhere result retires
  language share as an axis at this scale, which is also a deliverable.
- **status:** queued
```mill
id: I-002
mode: process
run: --arm layered_half --rope --corpus v2 --de-share 0.229
```

### I-003 ★ · Per-projection gate: Q, K and V stop sharing one median inside the fused qkv
- **source:** verified GAP-3a — `Block.qkv` is a single BitLinear
  (192→576); `Layered.step` computes one `g.abs().median()` over all
  110,592 gradients, so the stronger-half rule is enforced on a mixture
  of three distributions. Gate scopes pooled: layer (default), row
  (A-002), state (F-005). Projection slice: none.
- **mechanism:** The gate quantile (q=0.5, unchanged) is computed
  separately within the Q row-block (rows 0–191), K row-block
  (192–383) and V row-block (384–575) of each `qkv` matrix; `out`,
  `up`, `down` keep their layer median. Each projection then admits
  its own stronger half: if K gradients run systematically smaller
  than Q's, the fused median currently lets Q's evidence outvote K's
  on K's own weights, every step. Mandatory diagnostic printed with
  the probe: the three per-projection medians and their ratios — if
  they sit within 10% of each other, the mechanism has no population
  and the entry voids itself on its own diagnostic.
- **train.py:** new flag `--gate-scope proj` on Layered/Direct
  (grouped quantile inside `step()`, alongside the `--gate-q` /
  `--gate-scope` plumbing A-002/F-005 already specify).
- **mode:** process
- **prediction:** −0.01..−0.03 at probe and trial. Prior from the
  record: every attention-side fragility note in the union (A-026's
  premise, A-032's premise) says QK gradients behave unlike the rest;
  the fused gate is the one place that difference is still averaged
  away before a single vote is cast. Expected median spread: K's
  median |g| 20–40% below Q's at mid-run.
- **status:** queued
```mill
id: I-003
mode: process
run: --arm layered_half --rope --gate-scope proj
```

### I-004 · Role-split gate quantile: attention admits less, FFN admits more (with its reverse as control)
- **source:** verified GAP-3b — A-026 splits the flip *threshold* V by
  role (attention 48 / FFN 24); nobody splits the *admission* quantile.
  V and q are different dials: V is how much evidence a flip costs, q
  is whose evidence counts at all.
- **mechanism:** Two arms, run as one entry: (a) attention matrices
  (`qkv`, `out`) at q=0.75, FFN matrices (`up`, `down`) at q=0.5;
  (b) the reverse (attention 0.5 / FFN 0.75) as the direction control.
  Global V=32 unchanged in both. If (a) beats (b), admission strictness
  belongs on the fragile side — the same prior as A-026, tested on the
  dial A-026 does not touch; the pair also cross-reads A-026 itself
  (if both role splits win in the same direction, role asymmetry is
  real and compounding; if they win in opposite directions, the two
  dials trade off and neither should be adopted alone).
- **train.py:** new flag `--gate-q-role 0.75,0.5` on Layered (per-matrix
  quantile in `step()`, role determined by module name — the trainer
  already enumerates BitLinears in model order).
- **mode:** process
- **prediction:** (a) −0.01..−0.02 vs champion; (b) +0.01..+0.03.
  The (a)−(b) gap (0.02–0.05) is the entry's real product: the first
  measurement of whether gate admission, like flip cost, is
  role-asymmetric — at two probes' price.
- **status:** queued
```mill
id: I-004
mode: process
run: --arm layered_half --rope --gate-q-role 0.75,0.5
```

### I-005 · IQR band gate: counted above Q3, eroded below Q1, silent between
- **source:** verified GAP-4 — every pooled gate is one cut
  (MILL-601..606), one servoed cut (F-028), or one cut plus blanket
  erosion below a median multiple (A-005: below 0.25×median). Two
  quantiles of the same distribution, used as a band, appear nowhere.
- **mechanism:** Per layer per step, from the |g| distribution:
  weights above Q3 vote normally (−sign(g) into the counter); weights
  below Q1 move their counter one step *toward zero* (erosion, as in
  A-005 but restricted to the genuinely weakest quartile); weights
  between Q1 and Q3 do nothing. Three evidence classes instead of two:
  the middle half of every layer — currently forced to be either
  voters (q<0.5 settings) or silent equals of the weakest (champion)
  — is declared *uninformative* rather than *weak*, and only true
  weakness erases. Distinct from A-005 in both cuts (quantiles, not a
  median multiple) and in scope (erosion touches ≤25%, not ~all
  sub-0.25×median weights; the voting class shrinks from 50% to 25%,
  which no A-005 setting produces).
- **train.py:** new flag `--gate-band 0.25,0.75` on Layered/Direct
  (two `quantile()` calls replacing the `median()` line in `step()`;
  erosion applied to the counter before the flip test, clamped as now).
- **mode:** process
- **prediction:** −0.005..−0.02 at trial, ~0 at probe (erosion needs
  time to clear stale counters). Risk stated plainly: halving the
  voter class halves vote throughput, so flips arrive later — if the
  probe's flip share falls below ~60% of job zero's, the trial read
  must be at equal steps, not equal minutes, before any verdict.
- **status:** queued
```mill
id: I-005
mode: process
run: --arm layered_half --rope --gate-band 0.25,0.75
```

### I-006 · Phase attribution: one lever (V=16), three windows — first, middle, last
- **source:** verified GAP-5 — pooled schedules each move a lever
  across the whole run or park it at one end (A-022 last 10%, A-023
  first 5%, A-033 cycles, MILL-204..206 monotone ramps). No same-lever,
  same-dose, different-third comparison exists, so the lab cannot say
  *when* any schedule lever earns.
- **mechanism:** Three arms, one entry: V=16 (the pooled MILL-504
  dose) applied **only** during steps [0, 33%), only during [33%,
  66%), or only during [66%, 100%); V=32 (champion) at all other
  steps. Counters clamp at the *current* V (a counter at ±32 entering
  a hot window truncates to ±16 — logged, it is part of the treatment,
  exactly as in the pooled consolidation entries). The middle arm is
  the novel cell: the first arm re-prices the anneal catastrophe's
  timing claim (hot-early poisoned the 8→64 arm — was it the heat or
  the earliness?), the last arm re-prices tail-freeze logic on the V
  dial instead of the freeze dial.
- **train.py:** new flag `--v-window 0.33,0.66 --votes 16` on Layered
  (window bounds as run fractions of `done`, which train.py already
  computes; three runs differ only in the bounds argument).
- **mode:** process
- **prediction:** middle-only captures ≥70% of whatever full-run V=16
  shows in the pooled grid; first-only is the worst arm (+0.02..+0.05
  vs champion — early evidence is the noisiest and hot flips bank it);
  last-only ≈ champion ±0.01 (late hot flips mostly re-litigate settled
  weights). If instead first-only ≈ middle-only, timing is a dead axis
  for V and every schedule entry in the pool should be read as a dose
  entry — a pool-wide reinterpretation for three probes.
- **status:** queued
```mill
id: I-006
mode: process
run: --arm layered_half --rope --v-window 0.33,0.66 --votes 16
```

### I-007 · Rotating position-band loss: each step, one quarter of the window casts all the votes
- **source:** verified GAP-6a — F-013 *weights* positions inside one
  shared gradient; G-022 *shortens* windows. No entry partitions a
  full-length window's loss by position band while keeping the full
  context in the forward pass.
- **mechanism:** Forward is the standard ctx-256 window. The loss —
  for both the vote path and the AdamW parts — is computed only on
  target positions in one 64-position band, rotating by step
  (step mod 4 → band 0–63, 64–127, 128–191, 192–255). Over any 4
  steps every position is a target exactly once (stationary, unlike
  a curriculum), but each individual step's counters integrate
  evidence from a single context-depth regime: band-0 votes are cast
  by a model guessing from ≤64 tokens of context, band-3 votes by one
  guessing from ≥192. The champion's single gradient mixes all four
  regimes into one sign per weight per step.
- **train.py:** new flag `--pos-band 64` in the training loop (loss
  masked to the step's band before `cross_entropy` reduction; held
  eval untouched, always full-window).
- **mode:** process
- **prediction:** −0.00..−0.02 at equal steps; per-minute roughly
  neutral (backward through the head shrinks, attention backward does
  not). The diagnostic that decides whether the mechanism is real:
  flip share by band-step — if band-0 steps flip at ≥1.5× the rate of
  band-3 steps under the champion's mixed loss (measurable only
  here), early-position evidence has been stampeding the counters
  and banding is the fix; uniform flip rates retire the premise.
- **status:** queued
```mill
id: I-007
mode: process
run: --arm layered_half --rope --pos-band 64
```

### I-008 · Drop the first 16 targets from the shared loss (both paths, hard cut)
- **source:** verified GAP-6b — F-013 down-weights early positions in
  the vote path only, softly (log weights, position 0 still counts
  0.125) and explicitly leaves the FP parts' loss plain. The shared
  loss itself has never lost a position.
- **mechanism:** Targets at positions 0–15 (context of 0–15 tokens —
  the nearest thing to irreducible noise in the window: the model is
  predicting running text from almost nothing) are excluded from the
  cross-entropy for *both* the vote counters and the AdamW parts.
  6.25% of every batch's gradient is removed, not reweighted; the
  remaining 240 positions renormalise. Held eval is unchanged (all
  256 positions), so any win is a training-evidence win, not a
  judging artefact. Read against F-013 as a pair: F-013 says early
  positions are weak *witnesses for votes*; this says they are noise
  *for everyone, embeddings included* — if I-008 wins and F-013
  doesn't (or vice versa), the lab learns which path the noise was
  hurting.
- **train.py:** new flag `--drop-early 16` in the training loop
  (slice targets/positions before the loss; no model change).
- **mode:** process
- **prediction:** −0.005..−0.015 pooled held, with the per-position
  held buckets (I-012's instrument) showing positions 0–15 *worse*
  by +0.03..+0.08 (never trained) and positions 64+ better by
  −0.01..−0.02 (cleaner structure) — the pooled sign is the bet that
  the second effect outweighs the first at 16/256 of the window.
  At 32 dropped positions the bet is predicted to flip; 16 is the
  dose where the entry expects to win.
- **status:** queued
```mill
id: I-008
mode: process
run: --arm layered_half --rope --drop-early 16
```

### I-009 · Flip-acceleration tax: a weight whose flips are speeding up pays more for the next one
- **source:** verified GAP-7 — A-008 taxes flip *count*; F-025 erodes
  on stall *age*; F-004 prices vote *consistency*. The interval
  *trend* — is this weight settling or destabilising? — is read by no
  pooled rule.
- **mechanism:** Each weight records the step of its last two flips
  (two int16 stamps per component, +4 B/weight charged — this entry
  is not state-free and says so). After a flip, if the just-ended
  interval is < ½ the previous interval (flips accelerating), the
  weight's personal V ×1.5 for its next cycle; if the interval more
  than doubled (settling), V ×0.75, floored at 16, capped at 64;
  personal V resets to 32 after any cycle with no flip for 200 steps.
  A chronic oscillator (A-008's target) and an accelerating
  destabiliser overlap but are not the same population: a weight can
  flip rarely in total yet be accelerating *now*, and that is the
  population this entry claims is about to thrash.
- **train.py:** new flag `--flip-accel 1.5` on Layered (per-weight
  V array as in F-004's `--sprt-v` plumbing, plus flip-step stamps
  updated in the flip branch of `step()`).
- **mode:** process
- **prediction:** ~0 at probe (few weights complete two intervals in
  ~40 steps — this is a trial-format entry and is not probe-honest);
  −0.01..−0.02 at trial, concentrated in the second half, with the
  count of weights flipping ≥4 times falling ≥25% vs champion. If
  the accelerating population measures <1% of weights at trial, the
  entry retires on its own census, like F-025's void condition.
- **status:** queued
```mill
id: I-009
mode: process
run: --arm layered_half --rope --flip-accel 1.5
```

### I-010 · Cyclic context length: 64→128→256→128→64, one full cycle per run
- **source:** verified GAP-8 — A-045's monotone curriculum confounds
  length with phase (G-022's own criticism); G-022's stationary mix
  removes order entirely. A deterministic cycle is the untested
  middle: ordered within each cycle, balanced across the run.
- **mechanism:** ctx follows a triangular cycle over steps —
  64, 128, 192, 256, 192, 128, then repeats — completing ~4 cycles
  per trial. Every length is visited at every run phase, so a win
  cannot be a phase effect and a loss cannot be blamed on one; early
  flips see short *and* long contexts, unlike A-045 where the entire
  first third's structure is built at ctx 64. Judged at ctx 256 on
  the standard held, at equal steps (mean ctx ≈ 160, so equal-steps
  is the honest currency; equal-minutes reported alongside).
- **train.py:** new flag `--ctx-cycle` in the sampler (window length
  by step index, reusing A-045's `--ctx-curr` slicing plumbing with a
  cyclic schedule in place of thirds).
- **mode:** process
- **prediction:** beats A-045's curriculum arm by −0.01..−0.02 and
  ties G-022's mix within ±0.01 at equal steps. If the cycle beats
  *both*, order-within-length is a real term neither design isolated;
  if it ties both, ctx scheduling closes as an axis and A-045/G-022
  stand as its complete exploration.
- **status:** queued
```mill
id: I-010
mode: process
run: --arm layered_half --rope --ctx-cycle
```

### I-011 · Frequency-binned held: report what the 2.8580 is made of
- **source:** verified GAP-9 — held has been sliced by source
  (G-019/E-021) but never by the target token's corpus frequency,
  while a whole vocab family (TK-entries, tail-row V) bets on the
  tail mattering.
- **mechanism:** Eval-only instrumentation, no training change: for
  the champion and for plain_half (the standing control), report
  held loss split by target-token frequency quartile (counts from
  the training corpus itself), as (a) mean loss per quartile and
  (b) each quartile's share of total held loss mass. Also report the
  champion−control Δ per quartile. One eval pass per model on the
  standard 128 windows; the binning is a tag on tokens already scored.
- **train.py:** eval-side only — `held_loss` gains a `--held-bins
  freq` reporting mode (per-token losses bucketed before averaging);
  no trainer, sampler or model change.
- **mode:** process
- **prediction:** the rarest quartile carries ≥40% of total loss
  mass at a mean ≥2× the commonest quartile's — but the
  champion-vs-plain Δ concentrates in the *second* quartile
  (mid-frequency tokens: common enough to earn flips, rare enough to
  still be contested), with the tail quartile's Δ within ±0.01.
  If that holds, tail-targeted entries (tail-row V and kin) are
  capped at near-zero pooled value and should be re-ranked before
  the mill spends probes on them; if the tail Δ is instead the
  largest, those entries gain their first direct evidence.
- **status:** queued
```mill
id: I-011
mode: process
run: --arm layered_half --rope --held-bins freq
```

### I-012 · Position-binned held: locate rotary's win inside the window
- **source:** verified GAP-10 — G-018 logs per-position held only as
  an internal diagnostic of its BOS arms. The champion family's
  standard eval has never been reported by position bucket, although
  rotary — the lab's one confirmed win, −0.0411 (RESULTS-ROPE) — is
  a claim *about* position.
- **mechanism:** Eval-only: report held for the champion
  (layered_half+rope) and its no-rope control (layered_half, the
  2.8990 arm) in four position buckets (targets 0–63, 64–127,
  128–191, 192–255), same 128 held windows, per-token means per
  bucket plus each bucket's share of the pooled Δ. No training, no
  new data; the two models' existing eval path, bucketed.
- **train.py:** eval-side only — the same `--held-bins pos`
  reporting mode as I-011 (the two entries share one instrument
  and should be merged at implementation, kept separate here
  because they answer to different families: vocab vs RoPE).
- **mode:** process
- **prediction:** bucket means fall monotonically, roughly
  3.4 / 3.0 / 2.7 / 2.5 from first to last bucket, and ≥60% of
  rotary's pooled −0.0411 sits in buckets 128–255 (long-range
  positions are where a position *scheme*, vs a position *table*,
  should earn). If the win instead concentrates in buckets 0–63,
  rotary's mechanism story in the lab's record is wrong — it would
  be winning as a local-smoothing change, not a long-context one —
  and the partial-RoPE / NoPE entries (MILL-133..135) should be
  re-read under that story before further probes.
- **status:** queued
```mill
id: I-012
mode: process
run: --arm layered_half --rope --held-bins pos
```

---

## Miner's ranking note

★★★ are I-001/002/003. I-001 is first because it is the only entry
whose result re-prices *every other verdict in the ledger*: until the
seed's two halves are priced separately, "seed variance" is an
unanalysed lump inside every ± in the lab. I-002 is second because
45.7% of the clean corpus is one language and the lab has measured
everything about that fact except its amount. I-003 is third because
it needs no new corpus, no new flag family — one grouped median where
the code currently takes one median over three jobs at once — and its
own diagnostic can void it for free. I-011/I-012 are ranked last as
entries but cost almost nothing (one shared eval instrument, zero
training) and should in practice be *run* first: they are the map
this lens would want before spending probes anywhere else.

## Lens 2 — Second-order combinations (was CB-###)

### I-013 ★ · F-001 × F-024 — the rerouting's exit channel is deleted and rebuilt per-row
- **source:** F-001 · Boundary-pressure rerouting — outward votes on saturated weights are destroyed by the boundary no-op; reroute them into the layer's `log_scale`. / F-024 · Homeostatic scaling — per-output-row scales servoed to an activity set-point, *replacing* the gradient-trained per-layer `log_scale` entirely.
- **interaction hypothesis:** F-024 abolishes the exact parameter F-001 reroutes into. That is not additive, it is structural: under F-024 there is no per-layer scalar to receive boundary pressure, so the pressure must land on the saturated weight's *own row scale* — a finer, local channel F-001 alone does not have. The servo also fights back: it pulls every row toward the median RMS, so rerouted pressure that inflates one row is partly taxed away every 10 steps. The pair therefore tests a new mechanism (local magnitude escape under a conserving servo), not two stacked ones.
- **exact combined change:** `--boundary-scale --homeo 0.05` on Layered: boundary-strong votes add their 1/V quantum to the accumulator of the weight's output row; the servo update every 10 steps applies (servo delta + accumulated boundary delta) to that row's scale, accumulator then resets. No per-layer `log_scale` exists in this arm.
- **mode:** process
- **2×2 prediction:** champion 2.8580 · F-001 alone −0.02..−0.05 · F-024 alone −0.01..−0.05 · **both −0.05..−0.09** if per-row escape beats per-layer escape (saturated weights cluster in high-activity rows, whose scales are exactly the ones that should move); both ≈ −0.01..−0.03 if the servo tax eats the rerouted signal.
- **kill criterion:** pair claim dies if both lands within 0.01 of the better single, OR if the logged boundary-pressure reaching row scales is <20% of what F-001 alone delivers to `log_scale` (the servo tax, not locality, was the whole story).
- **status:** queued
```mill
id: I-013
mode: process
run: --arm layered_half --rope --boundary-scale --homeo 0.05
```

### I-014 ★ · F-007 × G-030 — train with the lean, serve with the lean: the counter equilibrium moves
- **source:** F-007 · Counter-confidence install — during training the forward weight leans by its counter, effective = γ·(t + 0.25·c/V). / G-030 · Counter-soft install — eval-only readout installing t + α·(c/V), α fitted on calibration windows, on champion-trained weights.
- **interaction hypothesis:** one-entry-fixes-the-other's-weakness, with a twist. G-030 alone suffers a train/serve mismatch: the network never trained with leaned weights. F-007 removes that mismatch — but it also changes the *equilibrium* the counters reach: if the forward already expresses a fraction of the pending evidence, gradient pressure to complete the flip falls, so final counters should sit systematically closer to threshold than champion counters do. G-030's α, fitted on champion dumps, therefore mis-transfers to F-007 dumps in a predictable direction (the pair needs a *smaller* α for the same served offset). Neither single can see this; only the pair measures it.
- **exact combined change:** train `--conf-install 0.25` (F-007 as filed), dump final state, then readout `--counter-soft` with α refit on calibration windows *from the F-007 run* (α ∈ {0.15, 0.3, 0.5}); the 2×2's other cells are F-007 + plain readout and champion training + G-030 at its filed α grid.
- **mode:** process
- **2×2 prediction:** champion 2.8580 · F-007 alone −0.02..−0.05 · G-030 alone −0.005..−0.03 · **both −0.04..−0.08**, with the fitted α_pair measurably below α_champion-fit and the final |c| distribution shifted toward threshold vs the F-007-alone dump.
- **kill criterion:** pair claim dies if both is within 0.01 of F-007 alone with plain readout (the soft serve added nothing once training matched it), OR if α_pair ≈ α_champion-fit and the counter distributions are indistinguishable (no equilibrium shift — the mismatch story was wrong).
- **status:** queued
```mill
id: I-014
mode: process
run: --arm layered_half --rope --conf-install 0.25 --readout counter-soft
```

### I-015 ★ · G-014 × F-022 — coherent evidence is the fuel the cascade is starved of
- **source:** G-014 · Sequential stream walk — replace i.i.d. offsets with a contiguous tile walk (stream-shuffled arm), giving counters long temporally-coherent evidence runs. / F-022 · Benna–Fusi cascade — a fast counter (clamp ±8) must saturate repeatedly to feed a slow counter; the weight flips only at |cs| ≥ 4, so one-off bursts die and only persistent evidence becomes durable.
- **interaction hypothesis:** pure synergy with a stated mechanism. The cascade's transfer rule rewards *persistence across time*; i.i.d. sampling is the zero-coherence stream, the worst possible input for it — F-022's own filed prediction is two-sided (−0.02..+0.02) precisely because the chassis starves it. The stream walk manufactures exactly the long agreeing runs that push cf to saturation again and again. Conversely the walk's known risk (a locally one-topic stretch stampedes counters) is what the cascade's fast stage absorbs. Each entry covers the other's filed weakness.
- **exact combined change:** `--sampler stream-shuffled --cascade 8:4` on the plain_half chassis (F-022's chassis, as filed): contiguous shuffled-tile batches feeding the two-stage cascade trainer; all other settings champion.
- **mode:** process
- **2×2 prediction:** champion (i.i.d., plain counters) = rung control · G-014 alone −0.01..−0.05 · F-022 alone −0.02..+0.02 · **both −0.04..−0.08**, i.e. strictly better than either single by ≥0.02, with cs-transfer counts per step at least 2× the F-022-alone rate.
- **kill criterion:** pair claim dies if both is within 0.01 of G-014 alone (coherence helped, the cascade was inert decoration), OR if the cs-transfer rate under the walk is not measurably higher than under i.i.d. (the fuel story never happened, whatever the loss says).
- **status:** queued
```mill
id: I-015
mode: process
run: --arm plain_half --rope --sampler stream-shuffled --cascade 8:4
```

### I-016 · F-003 × F-006 — canonicalization assumes the components are interchangeable; the innovation channel says they are not
- **source:** F-003 · Orthogonal second channel — c1 integrates sign(g); c2 integrates sign of the gradient *innovation* sign(g − EMA(g)), a different bit of information. / F-006 · Canonicalization — every 32 steps each (t1, t2) pair is rewritten to its canonical representative, counters remapped as c_backbone = clip(c1 + c2), c_corr = 0, installed value unchanged.
- **interaction hypothesis:** predicted *interference*, and the most falsifying pair in this file. F-006's remap is only harmless if c1 and c2 are two piles of the same evidence — true on the champion, false by construction under F-003, where summing the counters mixes a level signal with a change signal and zeroing c2 erases the innovation integrator every 32 steps. If the pair collapses to F-006-alone or worse, F-003's bandwidth claim survives a hard test; if the pair wins anyway, the innovation channel was never carrying distinct information and F-003's premise dies instead. One of the two premises must lose.
- **exact combined change:** `--t2-innov --canon 32` on Layered, both exactly as filed; log the post-canon c2 regrowth curve as the mechanism diagnostic.
- **mode:** process
- **2×2 prediction:** champion 2.8580 · F-003 alone −0.02..−0.06 · F-006 alone −0.01..−0.03 · **both −0.00..−0.02** (canon strips most of F-003's gain; the residual is F-006's own churn reduction) — a negative interaction of 0.02–0.04 against the better single.
- **kill criterion:** pair claim (interference) dies if both ≥ F-003 alone − 0.01, i.e. canonicalization costs the innovation channel nothing; in that case F-003's "independent second bit" claim is what dies, and that verdict must be written onto F-003's record.
- **status:** queued
```mill
id: I-016
mode: process
run: --arm layered_half --rope --t2-innov --canon 32
```

### I-017 · F-013 × G-022 — two entries with opposite premises about early positions, forced to share a run
- **source:** F-013 · Position-information-weighted votes — early positions have tiny context, so their vote-path loss is down-weighted by w_t = log2(t+2)/log2(258). / G-022 · Stationary mixed context lengths — each batch draws ctx ∈ {64, 128, 256}, so positions 0–63 receive ~3× the gradient exposure of positions 192–255.
- **interaction hypothesis:** the premises collide on the same quantity. G-022's stated bet is that early positions are *undertrained* and deserve more exposure; F-013's stated bet is that early-position evidence is *low-quality* and deserves less vote weight. Run together, G-022 triples the supply of exactly the evidence F-013 discounts. If F-013 is right, it should rescue G-022 from its own side effect (exposure without quality) and the pair beats both; if G-022 is right, F-013's discount throws away the extra exposure and the pair falls back to F-013 alone. The pair adjudicates a premise, not just a loss.
- **exact combined change:** `--ctx-mix 64,128,256 --posw-vote` on Layered, both as filed; verdict at equal steps (G-022's primary currency), per-position held loss logged for positions 0–63 vs 192–255.
- **mode:** process
- **2×2 prediction:** champion 2.8580 · F-013 alone −0.01..−0.03 · G-022 alone −0.01..−0.03 · **both −0.03..−0.06** under the F-013-premise (discounted-but-frequent early evidence is the best of both), with the early-position held slice improving more than the global mean; under the G-022-premise both ≈ −0.01..−0.02.
- **kill criterion:** pair claim dies if both is within 0.01 of the better single AND the early-position slice moves with the global mean (no position-specific mechanism fired — the two dials were simply independent).
- **status:** queued
```mill
id: I-017
mode: process
run: --arm layered_half --rope --ctx-mix 64,128,256 --posw-vote
```

### I-018 · F-002 × F-043 — at the V the scaling law demands, the slow counter is reset to death
- **source:** F-002 · Weak-half slow counter — gated-out weak votes feed a second counter at V_slow = 128; *any* flip (fast or slow) resets both counters. / F-043 · Vote-threshold scaling law — V must fall as N rises: V ≈ 8 at the 10M rung to hold flip share ≈ 0.001/step.
- **interaction hypothesis:** interference through the shared reset, invisible at champion scale. F-002's slow counter needs 128 net weak votes *uninterrupted*; every fast flip wipes it. At V = 32 fast flips are rare enough that some slow climbs survive. At F-043's 10M setting (V = 8) fast flips fire ~4× as often per weight, so the slow counter's expected uninterrupted run collapses and its contribution should vanish — F-002's benefit is a *function of V*, and the pair maps that function at the one rung where both entries are detectable. The combined arm also forces a design question neither file asks: should V_slow scale with V (128 → 32) or stay absolute?
- **exact combined change:** 10M rung, ladder/long format as in F-043: `--votes 8 --weak-slow 128` (absolute arm) and `--votes 8 --weak-slow 32` (proportional arm) against `--votes 8` alone and the champion-scale F-002 record; slow-flip count logged separately from fast flips.
- **mode:** process
- **2×2 prediction:** rung control (10M, V=32) 2.9472 · F-002 alone (champion scale) −0.01..−0.04 · F-043 alone (10M, V=8) −0.04..−0.10 vs rung control · **both (absolute 128) ≈ F-043 alone ± 0.01 with slow flips ≈ 0**; both (proportional 32) recovers −0.01..−0.03 beyond F-043 alone if the reset-starvation account is right.
- **kill criterion:** pair claim dies if the absolute arm's slow-flip count is comparable (within 25%) to its champion-scale rate — then fast flips do not starve the slow counter and there is no interaction to price — or if the proportional arm also adds nothing, in which case F-002's evidence simply does not exist at 10M regardless of resets.
- **status:** queued
```mill
id: I-018
mode: process
run: --arm layered --rope --dim 512 --layers-n 3 --votes 8 --weak-slow 128
```

### I-019 · WH-025 × F-010 — deep supervision manufactures the upstream flip volume that triggers the discount
- **source:** WH-025 · Deep supervision — block 1 gets a direct same-token CE (weight 0.1, every 4th position), shortening its gradient path. / F-010 · Cross-layer staleness discount — whenever block 1's per-step flip share exceeds 0.2%, block 2's counters are written down ×0.75, because upstream flips stale downstream evidence.
- **interaction hypothesis:** a causal chain through a measured trigger. WH-025's own filed diagnostic predicts block-1 flip share *rises* under deep supervision. F-010's discount fires only on steps above the 0.2% trigger — a rate set from champion flip share (~0.11% mean), which WH-025 deliberately inflates. So the pair should discount block 2 far more often than F-010 alone ever does: either that is exactly right (block 2's evidence really is staler when block 1 is learning faster — synergy), or the discount becomes a near-constant leak that taxes block 2 for block 1's improvement (interference). F-010 alone cannot distinguish "fires rarely because staleness is rare" from "fires rarely because the trigger was calibrated to a slow block 1."
- **exact combined change:** `--deep-sup 0.1 --xstale 0.75` on Layered, both as filed; trigger-fire rate and block-2 counter mass logged per phase.
- **mode:** process
- **2×2 prediction:** champion 2.8580 · WH-025 alone −0.02..−0.05 · F-010 alone −0.01..−0.03 · **both −0.04..−0.07** if the discount rate rises to match real staleness (fire rate 2–4× F-010-alone); both ≈ −0.00..−0.02 if the write-downs become a constant tax (fire rate >8× with block-2 flip share collapsing).
- **kill criterion:** pair claim dies if the trigger-fire rate under the pair is within 25% of F-010 alone (deep supervision did not move the quantity the discount prices — the chain never closed), whatever the held loss does.
- **status:** queued
```mill
id: I-019
mode: process
run: --arm layered_half --rope --deep-sup 0.1 --xstale 0.75
```

### I-020 · WH-014 × G-001 — the per-part ratio loses its biggest member and gains 4,096 new ones
- **source:** WH-014 · Embedding rows join the vote trainer — the tied table leaves AdamW, becomes ternary with per-row scales; served bytes 3.81 MB → ~0.86 MB at a predicted +0.04..+0.12 nats/token cost (per-byte win if ≤ +0.05). / G-001 · Per-part lr ratio — log_scale hot at 3e-3, embedding cold at 3e-4, norms at 1e-3, instead of one pooled lr.
- **interaction hypothesis:** G-001's ratio was designed for 8 log_scale scalars and one FP embedding table. Under WH-014 the embedding group *ceases to exist* in AdamW, and the "scale" group grows from 8 scalars to 4,096 per-row scales — the only continuous degrees of freedom the ternary table has. Running those at G-001's hot 3e-3 could either compensate the ternary table's coarseness (the scales do all the fine fitting, faster — shrinking WH-014's filed cost below its per-byte bar) or destabilise it (4,096 hot scalars chasing a still-flipping code). G-001 alone says nothing about this: its hot group was 8 parameters, not 4,096.
- **exact combined change:** `--emb-vote --part-lr scale:3e-3,emb:3e-4,norm:1e-3` on Layered, where the part-lr "scale" group is defined to include the per-row embedding scales alongside the 8 layer log_scales; norms at champion; judged on WH-014's pre-stated per-byte bar, not raw loss.
- **mode:** process
- **2×2 prediction:** champion 2.8580 at 3,806,208 B · WH-014 alone +0.04..+0.12 at ~860,000 B · G-001 alone −0.02..−0.05 at full bytes · **both +0.00..+0.06 at ~860,000 B** — i.e. the hot-scale ratio claws back roughly half of WH-014's cost, landing the pair at or inside the ≤ +0.05 per-byte adoption bar that WH-014 alone is predicted to straddle.
- **kill criterion:** pair claim dies if both's cost vs champion is within 0.01 of WH-014 alone's cost (the ratio did nothing for the row scales — G-001's effect lives only in its original 8 scalars), or if both is *worse* than WH-014 alone by >0.02 with row-scale path length exploding (hot scales are a liability at 4,096-wide, closing the transfer).
- **status:** queued
```mill
id: I-020
mode: process
run: --arm layered_half --rope --emb-vote --part-lr scale:3e-3,emb:3e-4,norm:1e-3
```

### I-021 · G-013 × F-018 — does the quorum already eat the seams, or only their votes?
- **source:** G-013 · Boundary-masked line packing — pack whole lines, mask the ~7 seam targets per window out of the CE entirely (no loss, no gradient, no vote). / F-018 · Byzantine quorum — split each batch into 4 sub-electorates; a counter moves only when ≥3 of 4 sub-batches agree on the sign.
- **interaction hypothesis:** redundancy-vs-complementarity on the same noise source. Seam positions are the highest-loss, most contradictory gradients in every window — exactly the evidence most likely to split sub-electorates 2–2 and force abstentions. If the quorum is already neutralising seams *in the vote path*, G-013 adds nothing under F-018 (pair ≈ F-018 alone). But F-018 leaves the AdamW path untouched — the FP parts still step on the summed gradient including seams — while G-013 removes seams from both paths. The pair's margin over F-018 alone therefore prices the seam damage done through AdamW specifically, a quantity no single entry isolates.
- **exact combined change:** `--pack-mask --byz 4:3` on Layered (v2 corpus, as G-013 specifies), both as filed; quorum agreement rate and abstention rate logged per phase.
- **mode:** process
- **2×2 prediction:** champion 2.8580 · G-013 alone −0.02..−0.06 · F-018 alone −0.01..−0.05 per step · **both −0.04..−0.08** if the AdamW-path seam damage is real (sub-additive vs the naive sum, super-additive vs either single), with the quorum abstention rate falling measurably vs F-018 alone because the surviving evidence agrees more.
- **kill criterion:** pair claim dies if both is within 0.01 of the better single AND the abstention rate is unchanged from F-018 alone (the two mechanisms were eating the same noise through the same path — full redundancy, and one of the two entries should be retired in the other's favour).
- **status:** queued
```mill
id: I-021
mode: process
run: --arm layered_half --rope --corpus v2 --pack-mask --byz 4:3
```

### I-022 · G-017 × F-048 — the discount deletes the repetition, leaving only the phase: a decomposition pair
- **source:** G-017 · Stride-64 overlap lattice — every token appears in exactly 4 windows at 4 different window positions; predicted −0.01..−0.04 if phase diversity is the active ingredient, +0.02..+0.05 if unique coverage dominates. / F-048 · Repetition-discounted votes — a vote from a window on its n-th visit counts with probability 1/n, so repeated evidence cannot masquerade as independent evidence (10M multi-epoch format).
- **interaction hypothesis:** the pair is a scalpel for G-017's own ambiguity. G-017 bundles two effects — 4× repetition of each token and 4-phase diversity — and its filed prediction cannot separate them. F-048 prices repetition at its actuarial value (the 4 testimonies of one token count as ~1 + 1/2 + 1/3 + 1/4 ≈ 2.08, not 4). Under the pair, whatever gain survives *is* the phase-diversity effect, and whatever vanishes was repetition inflation. That attribution is the deliverable; it exists in neither single.
- **exact combined change:** F-048's multi-epoch format (10M shape, fixed corpus slice) with the sampler restricted to the stride-64 lattice and per-window visit counts fed to `--rep-discount`, both mechanisms exactly as filed; judged at equal steps against the format's undiscounted, non-lattice control.
- **mode:** process
- **2×2 prediction:** format control = baseline · G-017 alone (in-format) −0.01..−0.04 · F-048 alone −0.03..−0.08 in epochs 3–4 · **both −0.03..−0.06**, sitting strictly between the singles if phase diversity is worth about half of G-017's effect; both ≈ F-048 alone if G-017 was pure repetition.
- **kill criterion:** pair claim (that the pair decomposes G-017) dies only if the lattice's visit structure cannot be logged cleanly in the multi-epoch format — on the numbers, every outcome is a verdict: both ≈ G-017-alone-plus-F-048's epoch gain means phase and repetition were independent after all, and *that* equality, if it lands within 0.01 of the additive prediction, is the result that kills the interaction claim.
- **status:** queued
```mill
id: I-022
mode: process
run: --arm layered --rope --dim 512 --layers-n 3 --stride 64 --rep-discount
```

### I-023 · WH-027 × F-002 — which "weak" deserves a slow counter: weak-for-the-layer or weak-for-itself?
- **source:** WH-027 · Self-normalised surprise gate — the gate is taken on g / (per-weight EMA of |g|): a weight votes when its gradient is large *for it*, not for its layer. / F-002 · Weak-half slow counter — the gate's rejected half feeds a slow counter at V_slow = 128 instead of being discarded.
- **interaction hypothesis:** both entries act on the same object — the gate partition — but they define its halves differently, and F-002's premise is partition-specific. F-002 argues the rejected half carries the same sign bias as the accepted half, only noisier. That was derived for *layer-relative* weakness. Under WH-027 the rejected population is a different set: weights having a typical-for-them step, including chronically-large weights on quiet steps — a population whose sign bias has never been argued for by anyone. The pair tests whether "the discarded half is evidence" is a property of discarding, or of *this particular* discard rule; the slow flips under the pair should come from a measurably different weight population than under F-002 alone.
- **exact combined change:** `--surprise-gate --weak-slow 128` on Layered: the slow counter is fed by WH-027's shaped-gate rejects (the gate already computes the partition inside `step()`); slow-flip population logged by layer-relative |g| rank so the two arms' flip populations can be compared directly.
- **mode:** process
- **2×2 prediction:** champion 2.8580 · WH-027 alone a modest gate-partition gain (its file's class: −0.01..−0.03) · F-002 alone −0.01..−0.04 · **both −0.03..−0.06** if self-relative rejects carry at least as much slow evidence as layer-relative ones (the union of two differently-defined weak sets is larger than either); both ≈ WH-027 alone if the surprise-gate's rejects are genuinely empty of signal.
- **kill criterion:** pair claim dies if both is within 0.01 of the better single AND the slow-flip population under the pair is the same population (same weights, same layers, within sampling noise) as under F-002 alone — then the partition definition never mattered and the interaction was illusory.
- **status:** queued
```mill
id: I-023
mode: process
run: --arm layered_half --rope --surprise-gate --weak-slow 128
```

### I-024 · F-064 × WH-033 — a cull that imposes 70% zeros meets a controller that defends 42%
- **source:** F-064 · The 70% zero cull — every 10 steps, randomly zero currently-nonzero weights (counters zeroed) until the installed zero fraction is exactly 70%. / WH-033 · Homeostatic histogram regularizer — every 20 steps, if the zero fraction leaves the band [0.38, 0.46], votes in the restoring direction count double until it re-enters.
- **interaction hypothesis:** two opposed forces create a selection process neither has alone. The cull is deliberately skill-free (uniform random), and the homeostat is deliberately blind (it defends a fraction, not particular weights). Together they form a ratchet: the cull knocks weights to zero at random; between culls the homeostat, seeing z = 0.70 ≫ 0.46, doubles every away-from-zero vote, so the weights that regrow first are the ones with the strongest live evidence, while unevidenced culled weights stay zero. Random destruction + evidence-priced regrowth = a sparsity *selection* mechanism assembled from two entries that each claim to have no selection in them. The steady state should sit between 46% and 70% zeros, occupied by a better-chosen population than either endpoint's.
- **exact combined change:** `--zero-cull 0.7 --cull-every 10 --hist-homeo 0.38,0.46` on Layered, both exactly as filed; zero fraction and the identity overlap between successive post-cull regrowth sets logged per cull cycle.
- **mode:** process
- **2×2 prediction:** champion 2.8580 · F-064 alone within +0.02 of champion counts as its filed "interesting" outcome · WH-033 alone ~0..−0.02 (the band rarely binds on champion runs) · **both −0.01..−0.04 at a served zero fraction of ~50–60%** — a loss win F-064 alone does not predict and a sparsity level WH-033 alone never reaches; the pessimistic branch is an oscillator (z sawtooths 0.46↔0.70, held +0.02..+0.05) if the doubled votes regrow everything indiscriminately.
- **kill criterion:** pair claim dies if both is within 0.01 of F-064 alone at the same final zero fraction (the homeostat contributed nothing but arithmetic), OR if the regrowth sets show no evidence concentration — post-cull regrown weights' mean |counter| no higher than a random nonzero set's — in which case the ratchet never existed.
- **status:** queued
```mill
id: I-024
mode: process
run: --arm layered_half --rope --zero-cull 0.7 --cull-every 10 --hist-homeo 0.38,0.46
```

---

## Miner's note

The pair I would bet on most is **I-015 (G-014 × F-022)**: it is the only pair here
where each member's filed prediction already names the other's absence as its limiting
factor — the cascade is two-sided *because* i.i.d. evidence cannot persist, and the
stream walk's stampede risk is exactly what a fast-saturating first stage absorbs.
I-013 is the largest predicted swing but carries redesign risk (the rerouted channel
has to be rebuilt per-row before it can be tested); I-016 is the cheapest certain
information — one of two filed premises must lose, and the mill learns which for the
price of one trial.

## Lens 3 — Long horizon (was LH-###)

### I-025 ★ · Stale-bank purge: counters outlive the model that earned them
- **source:** long-horizon lens — a counter is evidence integrated under past installed states. A weight that last flipped at step 100 and sits at c=+28 at step 5,000 holds a bank earned against a network that has since flipped thousands of other weights. At 160 steps the oldest possible bank is 160 steps old and the landscape has barely moved, so staleness is structurally invisible to every trial the lab has run.
- **mechanism:** Near-threshold counters (|c| ≥ 16) whose sign no longer matches the current gradient consensus are *stale-signed*: when they finally cross, they flip the weight the way the old model wanted, not the way the current one does. Their share of the near-threshold population grows with run length because banks accumulate faster than they resolve. A periodic purge — revalidate the near-threshold bank against fresh batches and zero the counters that fail — spends a few passes to delete evidence that has become actively wrong.
- **exact change:** new flag `--bank-purge 1000` on Layered: every 1,000 steps, for each weight with |c| ≥ 16 in either component, accumulate 8 fresh training batches' gated votes read-only; if the fresh net vote's sign opposes sign(c) by ≥ 4, set that counter to 0 (state untouched). Log purged share per purge. Control: same run, purge counterfactual logged but not applied.
- **horizon of onset:** ~1,000–2,000 steps — the first point where a bank can be ~10× older than the 160-step horizon over which the lab validated counter behaviour (WH-052's predicted counter half-life is ~60–90 steps; a bank surviving >10 half-lives is archaeology by that entry's own estimate).
- **short-horizon proxy + predicted reading:** two-phase switch run inside one 160-step budget: train 80 steps on source-partition A of the corpus, then 80 on partition B; at the switch and at step 160, measure the stale-sign fraction among |c| ≥ 16 counters (fresh-batch vote sign vs bank sign, as above). **Predicted reading: 30–45% stale-signed at step 160 after a single hard switch** — if a mere 80-step regime change already invalidates a third of the bank, a 10,000-step run's bank (thousands of soft regime changes) is majority-suspect. Proxy < 15% kills the entry cheap.
- **full-form prediction:** at 1,600 steps, purge beats no-purge by −0.02..−0.05 held, with purged share rising purge-over-purge (5% → 15%+ of near-threshold counters). At 16,000 steps the gap widens; the no-purge arm's late flips are increasingly old-model flips.
- **status:** queued

### I-026 ★ · Saturation creep: the clamped-counter majority (int8 is a short-horizon answer)
- **source:** long-horizon lens + train.py audit — counters are int8 clamped at ±V=±32. Every step a counter sits at the clamp, agreeing evidence is silently discarded (the clamp, not the boundary no-op of WH-051 — this counts *all* pinned counters, boundary or not). MILL-631..633 probed clamp width at 160 steps, where few counters have had time to pin; their verdict, whatever it is, is a verdict about a regime where saturation barely exists.
- **mechanism:** The pinned fraction grows roughly monotonically: each weight that reaches ±32 and stays in a stable gradient regime parks there, insensitive — further evidence cannot strengthen it, and reversal must first unwind a full 32 of banked votes regardless of how long ago they were earned. As the pinned share rises, the trainer's *effective* sensitivity falls: a growing fraction of the network is running on a saturated integrator. Widening the counters (int16, clamp ±256, V unchanged at 32) does nothing at step 160 and everything once pinning is the norm — the extra headroom is precisely a record of *how much* evidence beyond threshold a weight has, which is also what a reversal should have to overcome.
- **exact change:** new flag `--counter-width 16` on Layered/Direct: int16 counters, clamp ±256, flip threshold still |c| ≥ 32, reset on flip unchanged. State cost +1 B/weight/component, charged. No other change — this is deliberately the MILL-631 idea re-asked at the horizon where its mechanism exists.
- **horizon of onset:** ~800–1,600 steps — when the pinned fraction crosses ~25% of all counters (below that, width is inert by construction).
- **short-horizon proxy + predicted reading:** census only, no new arm: in a standard 160-step champion run, log the pinned fraction (|c| = 32) at steps 40/80/120/160. **Predicted reading: pinned share reaches 8–15% by step 160 and is still rising near-linearly (~+2–4 pts per 40 steps)** — linear extrapolation crosses 25% before step ~600 and 40%+ by 1,600. A plateau ≤ 10% by step 160 kills the entry.
- **full-form prediction:** at 1,600 steps int16 beats int8 by −0.02..−0.06 held, driven by mid-run reversals resolving faster on genuinely-contested weights; at 160 steps the two arms tie within noise (the expected null that explains why the short-horizon clamp grid could never see this).
- **status:** queued

### I-027 ★ · Zero-fraction creep: slow sparsity drift with no restoring force
- **source:** long-horizon lens — the ~42% zero fraction is load-bearing (built-in feature selection, per the lab's standing reading of BitNet), yet nothing in the trainer regulates it: it is wherever the vote dynamics happen to have wandered. A-009's static zero-bias prices a *level* shift at 160 steps; no entry treats the zero share as a slowly drifting state variable, because at 160 steps drift is smaller than seed noise.
- **mechanism:** Flips into 0 and out of 0 are not symmetric over long horizons: a weight at 0 whose row is quiet receives weak, mixed evidence and tends to stay, while non-zero weights keep accumulating directional pressure — the zero population behaves like a slow sink (or, in layers with strong gate statistics, a slow source). Either direction, an unregulated drift of even ~1 pt per 160 steps compounds to 6–10 pts by 1,600–16,000 steps: the long-run model is a materially sparser (or denser) model than any trial ever measured, and per-byte verdicts from short trials are denominated in the wrong sparsity.
- **exact change:** new flag `--zero-band 0.40,0.46` on Layered: every 100 steps, measure the global installed zero share; if outside the band, nudge the gate quantile for zero-ward vs zero-leaving votes by ∓0.02 (restoring force toward the band, capped ±0.06 total) — a slow homeostat on the *population*, distinct from F-024 (per-row activity servo on scales) and A-009 (fixed 1.5× zero-ward vote weight). Log zero share every 100 steps in all arms, including controls.
- **horizon of onset:** ~800 steps — drift must first exceed the ±1–2 pt seed-to-seed band visible at 160 steps; predicted crossing at 5–8× the trial horizon.
- **short-horizon proxy + predicted reading:** measure the zero share at steps 80 and 160 in 3 champion seeds and take the signed slope of the second half. **Predicted reading: a consistent-sign slope of +0.8..+1.5 pts per 160 steps in ≥ 2 of 3 seeds** (direction predicted upward — zero as sink — but the entry lives on |slope| with consistent sign, not on the direction). Inconsistent signs or |slope| < 0.3 pts kills it.
- **full-form prediction:** unservoed zero share exits the 40–46% band by ~1,600 steps and reaches ~50%+ (or < 36%) by 16,000; the servoed arm holds the band and beats the drifted arm by −0.02..−0.05 held at 1,600 steps, growing with horizon. Side deliverable either way: the first measurement of the drift rate itself.
- **status:** queued

### I-028 · Multi-cycle consolidation: bank resolution only pays when it repeats
- **source:** long-horizon lens — D-003 established the bank-resolution idea (drop V late, let banked evidence in [8, 32) fire) as a *single* end-of-run event inside 160 steps, where the bank is thinnest. A bank is not a one-time object: it refills continuously. Only a long run can afford the phase structure the mechanism actually implies — resolve, reopen, refill, resolve again — and a single cycle at step 160 tests the weakest possible version of it.
- **mechanism:** Every 400 steps, a 40-step consolidation window at V=8 on **fresh windows only** (no replay, no buffer, no hard-window targeting — this is not a D-wave entry; the content is deliberately neutral so the *cycle* is the only variable), then V returns to 32. Each window fires the resolution wave from the bank accumulated since the last one. The claim is specifically about repetition: cycle 1 spends a young bank, cycles 3+ spend banks earned by a mature model, and the marginal value per cycle should *rise* before it falls — a shape no single-cycle design can exhibit.
- **exact change:** new flag `--consol-cycle 400,40,8` on Layered (period, window, low-V) in a companion runner; factorial controls at full form: single end-cycle only, and V=8 windows on the same schedule with counters pre-zeroed (windows without a bank — separates "low V" from "bank resolution", extending D-003's 2×2 logic across cycles).
- **horizon of onset:** ~1,200 steps — the third cycle is the first that can differ from a single consolidation; below that this collapses into D-003's territory and should not be run.
- **short-horizon proxy + predicted reading:** compress two cycles into 160 steps (V=8 for steps 76–84 and 152–160, fresh windows) vs one end cycle (steps 152–160 only) vs none, step-matched. **Predicted reading: two-cycle beats one-cycle by −0.01..−0.02 even compressed**, and the second cycle's resolution-wave flip share is ≥ 60% of the first's (bank visibly refilled in 68 steps). If the second wave is < 30% of the first, banks refill too slowly for cycles to matter and the entry dies at probe.
- **full-form prediction:** at 1,600 steps (4 cycles) multi-cycle beats single-end-consolidation by −0.02..−0.04 and beats no-consolidation by −0.03..−0.06; per-cycle wave size decays slowly (≥ 50% retained at cycle 4), which is itself the bank-refill rate the lab has never measured.
- **status:** queued

### I-029 · Early-flip cohort scar: the first flips govern the next ten thousand steps
- **source:** long-horizon lens — a weight flipped at step 20 of a 160-step run influences 140 later steps; the same flip at step 20 of a 16,000-step run influences 15,980. Early flips are made on the weakest evidence of the run (near-init gradients, unformed scales) yet acquire the longest leverage — path dependence that scales with horizon and is therefore largest exactly where the lab never looks. At 160 steps the scar and the run are the same size, so no short trial can separate "early flips were right" from "early flips were merely first."
- **mechanism:** Give the earliest cohort a second chance at mid-horizon: snapshot the identities of the first 5% of weights ever to flip; at 50% of the run, re-randomize *those weights'* ternary states (fresh draw from the init distribution), zero their counters, and let them re-earn their states against the mature network. If early flips were good, re-earning converges back to similar states at small cost; if they were scars, the cohort lands somewhere better and the gain persists for the whole second half.
- **exact change:** new flag `--cohort-retry 0.05,0.5` on Layered (cohort share, retry point) in a companion runner; control arm retries a *random* 5% cohort of the same size at the same step (prices re-randomization itself vs earliness specifically). Log cohort state-agreement between pre-retry states and end-of-run states.
- **horizon of onset:** ~1,600 steps — the retry needs a long second half (≥ 800 steps) for re-earned states to repay the disruption; at 160 steps the second half is 80 steps and the entry is expected to read as pure cost.
- **short-horizon proxy + predicted reading:** measurement only, inside one 160-step run: split flipped weights by flip-time quartile and compute each quartile's *final-state stability* (share whose installed value at step 160 equals their value right after their first flip, minus the same share for a matched never-early control) plus flip-back rate. **Predicted reading: the earliest quartile shows the highest flip-back / instability rate (≥ 1.5× the latest quartile)** — early flips are disproportionately wrong-but-sticky. Earliest quartile most stable instead kills the scar story and the entry with it.
- **full-form prediction:** at 1,600 steps early-cohort retry beats random-cohort retry by −0.02..−0.04 and beats no-retry by −0.01..−0.03; cohort agreement (retried weights returning to their pre-retry value) lands at 40–60% — the first direct price of early-evidence quality in this trainer.
- **status:** queued

### I-030 · Survival consolidation: a weight that survives an epoch unflipped has earned its threshold
- **source:** long-horizon lens — at 160 steps almost no weight has a meaningful "age": the run is shorter than one pass over the legal stream. At 1,600+ steps a new observable exists — time-since-last-flip spanning orders of magnitude — and the population splits into a churning minority and a settled majority that has survived hundreds of batches of counter-evidence without flipping. Survival under fire is evidence *about* a weight that neither its gradient energy (F-023) nor its flip count (A-008) records. F-025 erodes a *stalled counter's* threshold (a counter property, opposite sign); this hardens a *surviving state's* threshold (a state property).
- **mechanism:** Each weight tracks steps-since-last-flip. Once a weight has survived S = 500 consecutive steps unflipped, its personal threshold doubles (32 → 64, int16 counters) and stays doubled while it survives; a flip resets both the counter and the survival clock. Settled structure stops paying churn tax to late noise; plastic weights keep the champion's threshold exactly. The asymmetry only exists when S is a small fraction of the run — at 160 steps S = 500 never fires, which is the point: short trials cannot have tested it.
- **exact change:** new flag `--survive-v 500,2` on Layered (survival steps, threshold multiplier; per-weight age counter + int16 counters, state charged).
- **horizon of onset:** ~1,000–1,500 steps — the first cohort completes its 500-step survival and the doubled-threshold population becomes a material share (~30%+) of weights.
- **short-horizon proxy + predicted reading:** in a 160-step champion run, compute the survival curve: share of weights whose *current* state has already survived ≥ 80 steps by run end, and their forward flip hazard in steps 120–160 vs younger weights. **Predicted reading: ≥ 35% of weights are ≥ 80-step survivors by step 160, and their flip hazard is ≤ half the young weights' hazard** — survival is already informative at half-horizon, so a 500-step version at 10× horizon is a real population, not a tail. Hazard ratio ≥ 0.9 kills it (survival predicts nothing).
- **full-form prediction:** at 1,600 steps survival consolidation beats champion by −0.01..−0.04, concentrated in reduced late-run flip-back rate (≥ 25% fewer reversals among survivors); at 16,000 steps it is the difference between a settled core and perpetual slow churn.
- **status:** queued

### I-031 · Rare-row Adam decay: the FP optimizer forgets rows the corpus rarely visits
- **source:** long-horizon lens — the shared FP parts use AdamW with β2 = 0.95 (second-moment horizon ~20 steps). A frequent embedding row is updated every step and its moments stay fresh; a tail row (the audit: 1,984 ids occur < 100 times in the whole corpus) may go hundreds or thousands of steps between updates at long horizons, and standard Adam implementations either decay its moments toward the intervening gradients of *other* rows' steps (dense update path) or leave bias correction stale — either way the row's first update after a long absence is taken with moments that describe a model thousands of steps younger. At 160 steps absences are ≤ ~160 steps and the distortion is bounded and small; it grows with the absence distribution's tail, i.e. with horizon and epochs.
- **mechanism:** Track per-row last-update step for the tied embedding; on a row's first update after a gap > 100 steps, refresh its Adam state before stepping: re-estimate exp_avg_sq from the current batch's gradient for that row (or equivalently reset the row's moments and let bias correction treat it as young), leaving frequent rows bit-identical to champion. The fix is scoped to exactly the rows the pathology can touch.
- **exact change:** new flag `--adam-refresh-gap 100` on Layered/Direct: per-row gap counter on `model.tok.weight`; moment refresh inside `step()` for rows crossing the gap threshold. Log gap distribution and refreshed-row count per 100 steps.
- **horizon of onset:** ~1,600 steps / second epoch — gaps > 500 steps for tail rows only become common once the run is long enough for the sampler to have cycled the stream; multi-epoch long runs are where the tail of the gap distribution lives.
- **short-horizon proxy + predicted reading:** instrument one 160-step champion run: histogram per-row update gaps and, for rows returning after a gap ≥ 40 steps, the ratio of their realised first-update magnitude to their median update magnitude. **Predicted reading: ≥ 20% of active rows experience a gap ≥ 40 steps even in 160 steps, and their return updates are ≥ 1.5× oversized** (stale-moment signature). Oversize ratio ≈ 1.0 kills the entry — the moments are not, in fact, going stale in this implementation, and that negative is worth owning before anyone builds the fix.
- **full-form prediction:** at 1,600 steps moment refresh improves held by −0.01..−0.03, concentrated in held windows containing tail pieces (report the rare-window split, cf. WH-019's diagnostic discipline); the gain grows with epoch count, not with steps per se.
- **status:** queued

### I-032 · Scale random-walk anchoring: per-step innocence, cumulative drift
- **source:** long-horizon lens — G-003 bounds each log_scale step (±2%) and G-004 gates scale updates by flips; neither bounds the *cumulative* path. Over 160 steps a bounded random walk stays near its start; over 16,000 steps the same walk's displacement grows ~√T and the hand-set gradient's persistent component grows ~T — the install scales at long horizon end wherever the walk took them, potentially far from the measured absmean the init chose and that `install()`'s own formula implies. The trained endpoint scale has never been compared to the data's scale at any horizon.
- **mechanism:** Periodically re-anchor: every 1,000 steps, compute each layer's installed absmean directly and blend log_scale 25% toward log(absmean) (soft anchor, not a reset — the learned deviation is mostly kept, the walk's tail is trimmed). If cumulative drift is signal, a 25% blend costs little; if it is walk noise, anchoring removes a distortion that grows √T forever.
- **exact change:** new flag `--scale-anchor 1000,0.25` on Layered: anchor pass inside the training loop at the stated period; log per-layer |log_scale − log(absmean)| at every anchor point in all arms (the control's un-anchored distance trace is itself a deliverable).
- **horizon of onset:** ~2,000 steps — cumulative displacement must first exceed the per-layer scale differences that G-025's post-hoc calibration found worth fitting at 160 steps (~5–15%); √T scaling from a 160-step base puts that crossing in the low thousands.
- **short-horizon proxy + predicted reading:** in a 160-step champion run, log per-layer log_scale at every step; compute path length (Σ|Δ|) vs net displacement (|final − init|) per layer. **Predicted reading: path/displacement ratio ≥ 5 (a walk, not a march) with net displacement already 2–6% of scale by step 160** — a walk-dominated trace at short horizon guarantees a drift-dominated trace at 100×. Ratio ≤ 2 (scales march purposefully) kills the entry.
- **full-form prediction:** at 1,600 steps anchoring beats champion by −0.01..−0.03 with visibly smaller seed variance in final scales; at 16,000 the un-anchored arm's scales are predicted ≥ 20% from absmean in at least one layer, with held cost growing accordingly.
- **status:** queued

### I-033 · Delayed leak: forgetting is poison early and medicine late
- **source:** long-horizon lens — the pooled leak family (MILL-209..213, λ = 0.95–0.99 always-on from step 0) will be verdicted at 160 steps, where leak's cost (discarding scarce early evidence before any flip has banked) is at its maximum and its benefit (forgetting dead regimes) cannot exist yet — there has been no time for a regime to die. The verdict will generalize wrongly in one direction or the other, because the leak question is intrinsically a horizon question: the optimal memory length is a property of how long the run is, not of the trainer alone.
- **mechanism:** Leak with a delayed onset: λ = 1.0 (no leak, champion-identical) until step 1,000, then λ = 0.999 (effective memory ~1,000 steps) for the remainder. Early evidence is kept whole while the model is young and every vote is precious; forgetting switches on only once the run is long enough to contain genuinely stale evidence (the I-025 bank, attacked by decay instead of purge — the pair prices the two stale-evidence policies against each other at full form).
- **exact change:** new flag `--leak-delay 1000,0.999` on Layered (fractional fixed-point counters as in MILL-209's plumbing; onset step and λ are the only new parameters). Full-form factorial: {no leak, always-on 0.999, delayed} × equal steps — always-on at long horizon is *not* the pooled short-horizon arm and must be re-run at length.
- **horizon of onset:** 1,000 steps by construction — and that is the claim: below onset the arm is *identical* to champion, so any short-horizon probe is a plumbing check only and a flat probe reading is predicted, not excused.
- **short-horizon proxy + predicted reading:** regime-switch probe (shares I-025's apparatus): train 80 steps on partition A, 80 on B, with λ ∈ {1.0, 0.99} from the switch onward; measure steps-to-recover (B-partition loss returning to its pre-switch trend) and A-bank stale-sign fraction at step 160. **Predicted reading: post-switch leak recovers ≥ 15% faster than no-leak while pre-switch (always-on) leak in a control probe costs ≥ 0.02 on the A phase** — the asymmetry (leak hurts before a regime exists, helps after one dies) is the whole entry, readable in 160 steps. Symmetric readings kill it.
- **full-form prediction:** at 1,600 steps delayed leak beats both no-leak (−0.01..−0.03) and always-on leak (−0.01..−0.02); at 16,000 the ordering is the same with larger gaps, and λ = 0.999's ~1,000-step memory tracks the bank-purge period of I-025 — if both win, the mill has measured the trainer's true evidence half-life twice, independently.
- **status:** queued

### I-034 · Era-stratified readout: the modal window must grow with the run
- **source:** long-horizon lens — the pooled modal readout (MILL-218/219) takes the per-weight majority over the last 5–9 checkpoints of a 160-step run: a window spanning a large fraction of the run's settled life. Copied naively to a 16,000-step run, "last 9 checkpoints" spans a negligible era and averages only the final noise; copied proportionally, it spans eras between which the model genuinely moved, and majority-voting across a real trajectory change blurs structure instead of denoising it. Readout window is a horizon-relative quantity that no entry has treated as one.
- **mechanism:** Save checkpoints at log-spaced eras (50%, 70%, 85%, 100% of the run, plus the final state) and read out the per-weight modal state across eras *weighted toward the recent* (weights 1, 2, 3, 4): the readout keeps modal denoising but its window is defined in run-fractions, so it scales with horizon by construction. Distinct from G-029 (era-matched SWA of FP parts within a short run) and G-026 (counter-resolved readout of a single final state): this is the discrete readout's window-scaling law.
- **exact change:** eval-side only, new flag `--era-modal 0.5,0.7,0.85,1.0` on the readout runner: checkpoint saves at those run fractions during any long run (storage charged), modal-with-weights at eval; report last-9 modal and final-state held on the same weights as built-in controls.
- **horizon of onset:** ~1,600 steps — eras must be separated by enough steps (≥ 250) for inter-era model movement to be real; at 160 steps the eras are 25 steps apart and all readout variants collapse into each other (predicted, and itself a checkable null).
- **short-horizon proxy + predicted reading:** on a 160-step champion run with saves at 50/70/85/100%, compute per-weight inter-era disagreement (share of weights whose era states are not unanimous) and era-modal vs last-5-modal held delta. **Predicted reading: inter-era disagreement is already 15–25% at 160 steps while the two readouts tie within ±0.005** — disagreement (the raw material era weighting acts on) is plentiful and growing with era separation, but at short horizon there is no settled era to weight toward. Disagreement < 8% kills it (the trajectory barely moves; readout window is moot at any horizon).
- **full-form prediction:** at 1,600 steps era-modal beats final-state by −0.01..−0.03 and beats last-9 modal by −0.005..−0.02; at 16,000 the last-9 baseline degrades toward final-state (window too small to denoise) while era-modal retains most of its gain — the readout's value becomes *more* horizon-dependent, not less.
- **status:** queued

### I-035 · Block-age divergence: the two blocks stop training at the same speed
- **source:** long-horizon lens — F-010 discounts block-2 counters when block 1 flips hard (an event-level interaction). The long-horizon version is a *trend*, not an event: over thousands of steps the blocks' flip shares diverge — one block's structure settles (flip share → ~0) while the other keeps churning — so for most of a long run the network is effectively training one block against a frozen other, then vice versa, never both at matched plasticity. At 160 steps both blocks are young and their flip shares are still comparable; divergence is a slow variable.
- **mechanism:** Measure per-block flip share on a slow EMA; when the ratio between blocks exceeds 3× for 200 consecutive steps, run a 50-step *solo phase* for the settled block only (its counters live at V=16, the churning block's counters and state frozen, FP parts live) to let it re-fit against the partner's current state, then resume joint training. Solo phases are the long-run form of block coordinate descent — affordable only when the run has thousands of steps to spend them in, pointless at 160 where freezing half the model for 50 steps is a third of the run.
- **exact change:** new flag `--block-solo 3,200,50` on Layered (divergence ratio, patience, solo length) in a companion runner; log per-block flip-share EMAs for all arms — the divergence trace is a deliverable even if the entry dies.
- **horizon of onset:** ~1,200–2,000 steps — divergence must first persist for the 200-step patience window; predicted first solo phase fires in that band.
- **short-horizon proxy + predicted reading:** in a 160-step champion run, log per-block flip share in steps 0–80 vs 80–160 and compute the block ratio's drift. **Predicted reading: the block flip-share ratio moves ≥ 1.8× between halves (one block visibly settling faster) in ≥ 2 of 3 seeds** — divergence is already underway at trial horizon, just not yet actionable. Ratio stable within ±20% kills the entry.
- **full-form prediction:** at 1,600 steps, 1–3 solo phases fire and the arm beats champion by −0.01..−0.03; the settled block's post-solo flip share recovers to ≥ 50% of its early value for ≥ 200 steps (the solo phase genuinely re-opened it, rather than merely perturbing it).
- **status:** queued

### I-036 · Evidence devaluation: a strong vote at step 10,000 is not a strong vote at step 10
- **source:** long-horizon lens — the gate is *relative* (median of the current layer, every step) and the increment is *absolute* (±1, every era). Jointly they assert that the stronger half of today's gradients is worth exactly one count, forever. But as loss falls over a long run, gradient magnitudes fall with it: the median |g| at step 10,000 is a fraction of its step-100 value, so a late "strong" vote certifies far less absolute evidence than an early one — yet it moves the same counter by the same 1 toward the same 32. At 160 steps loss moves ~2.9 → 2.86 territory on the vote path's scale and median |g| barely changes; over 16,000 steps the devaluation is first-order and the counter's evidence standard silently inflates away. (F-043 scales V with model size at fixed horizon; this scales the *count* with training progress at fixed size — orthogonal axes.)
- **mechanism:** Restore cross-time comparability: each gated vote's increment is scaled by the ratio (current layer median |g|) / (median |g| averaged over the first 100 steps), accumulated in fixed point — early votes count ~1.0, late votes count proportionally less as gradients shrink, so 32 counts always means ~32 counts *of step-100-grade evidence*. If gradients instead grow, increments grow symmetrically (cap ratio at [0.25, 2]). This is not calibrated magnitude votes (MILL-201..203 scale increments by *within-step* relative magnitude); the normalizer here is *across time*, against the run's own youth.
- **exact change:** new flag `--vote-deflate` on Layered: per-layer baseline median stored at step 100; fixed-point counter accumulation with the per-step ratio applied to increments (int16 counters; clamp/threshold logic unchanged in count units).
- **horizon of onset:** ~1,600 steps — median |g| must first fall by ≥ ~30% from its early baseline; at 160 steps the fall is within noise and the arm is champion-equivalent by construction (stated plainly: a flat probe is the predicted reading, not a disappointment).
- **short-horizon proxy + predicted reading:** measurement only: log per-layer median |g| at steps 20/80/160 in champion runs and fit its decay rate. **Predicted reading: median |g| falls 8–15% from step 20 to step 160 with a consistent sign across layers and seeds** — extrapolating that decay puts the 30% crossing inside the low thousands of steps, i.e. inside every serious long run and outside every trial. A flat or rising median-|g| trace kills the entry and, usefully, certifies the counter's evidence standard as time-invariant in this regime.
- **full-form prediction:** at 1,600 steps deflated counting beats champion by −0.01..−0.03, with the gain concentrated in late-run flip quality (flip-back rate in the final quarter down ≥ 20%); at 16,000 steps, where the undevalued counter's standard has inflated several-fold, the gap is predicted at −0.03..−0.07 — the largest full-form number in this file, and the one most tightly chained to its proxy's measured decay rate.
- **status:** queued

---

## Miner's note — the distortion already inside the 8-minute verdicts

The effect most likely to be *silently distorting current verdicts today* is the
**counter-bank complex of I-025 + I-026: staleness plus saturation.** Every
160-step verdict is issued by a trainer whose counters are young, mostly
unsaturated, and earned against a near-init network — the one counter regime in
which the mechanism behaves like the clean integrator the pool's mental model
assumes. Arms are therefore being ranked partly by how they interact with a
*transient* bank: leak looks worse than it is (its benefit needs a dead regime to
exist), layered levels look worse than they are (their second bank has barely
begun resolving), and any arm that front-loads flips looks better than it is
(its early flips face no stale opposition yet). None of this requires any single
verdict to be wrong at 160 steps — they are all correct measurements of a regime
that production-horizon runs will not be in. The cheapest insurance in this file
is I-026's proxy: it is a *census on runs the mill already executes*, costing
logging only, and its slope tells the lab whether every verdict it owns is
denominated in a counter regime with a shelf life.

*End of wave-4 lens-3. 12 entries, I-025..I-036, ranked as listed; ★ = I-025,
I-026, I-027. All status queued; merge is the pool owner's call.*

## Lens 4 — Discrete search (was DS-###)

### I-037 ★ · Tabu batch local search, counter-proposed
- **source:** discrete-search lens; proposal prior from WH-052 (counters predict future flips, FFN AUC 0.72–0.82) and WH-051 (frustrated/boundary population must be excluded from proposals); acceptance machinery from tabu search (Glover) — no pooled entry has memory of where it has already searched.
- **mechanism:** 40 rounds. Each round: build the proposal pool = top 512 unflipped-this-search component slots ranked by proposal score `|c| · (1 + 0.5·[layer is up/down])` (WH-052's FFN weighting), boundary no-ops and tabu slots excluded. Partition the pool's top 192 into 8 disjoint batches of 24 flips (each flip in the counter's sign direction). Score each batch by applying it, `install()`, and micro-evaluating on a rotating 32-window CAL-A slice (slices cycle, so no slice is optimised twice in a row). Accept the best batch **if its micro-Δ < +0.005** (near-neutral batches are accepted — that is the tabu point: walk through flat ground instead of stopping); all 24 flipped slots enter the tabu list for 5 rounds. **Aspiration:** a tabu batch is allowed if its micro-Δ beats the best full-CAL-A score seen so far. Every 5 rounds, score the incumbent on full CAL-A (2 EP) and snapshot it if it is the best full-CAL-A state yet; the search's output is the best snapshot, never the last state.
- **exact change:** new eval-side runner `mill/search.py --search tabu` (loads `--dump-state`, freezes FP/`log_scale`, owns the tabu list + snapshot ring; scoring is the `held_loss()` body pointed at CAL windows). No train.py change.
- **budget:** 40 rounds × 8 batches × 0.25 EP = 80 EP micro + 8 full-CAL-A snapshots × 2 EP = 16 EP + CAL-B 1 EP = **97 EP**.
- **prediction:** −0.03..−0.07 vs 2.8580. Batch evaluation prices flip *interactions* (including the per-layer `mean|s|` renormalisation) that single-flip verification cannot see, tabu memory stops the search re-litigating the same contested weights, and the counter prior concentrates proposals where post-training evidence already points. The champion was trained ~160 steps; its state is a vote equilibrium, not a loss optimum — a measured local search is the first procedure that optimises the actual objective over the actual discrete space.
- **overfitting guard:** CAL-A 256 windows; rotating micro-slices (a batch is never accepted on the same slice twice); hard cap **2,000 accepted component flips** (0.23% of positions); ship rule as protocol (CAL-B ≥ 0.01 and ≥ 50% transfer) — a CAL-A-memorising search fails CAL-B and ships the champion.
- **status:** queued
```mill
id: I-037
mode: process
run: --arm layered_half --rope --dump-state --search tabu
```

### I-038 ★ · Layer-sweep greedy coordinate descent (one BitLinear layer at a time)
- **source:** discrete-search lens; block-coordinate descent applied at the granularity `install()` itself defines — the per-layer `mean|s|` renormalisation means a flip's side effects are contained in exactly one layer's scale, so layer-isolated moves have the cleanest measurable deltas in the whole search space. Layer order follows WH-052's validity gradient (FFN layers' counters are the strongest witnesses, attention's the weakest).
- **mechanism:** One sweep = the 8 layers in fixed order: block2-down, block2-up, block2-out, block2-qkv, block1-down, block1-up, block1-out, block1-qkv. Per layer: proposals = that layer's top 256 slots by |counter| (counter direction only, no-ops excluded); form 6 sequential batches of 16 flips; for each batch, apply → `install()` → micro-eval on a fixed 32-window CAL-A slice reserved for this layer; keep the batch iff micro-Δ < 0, else revert it exactly. After each layer, one 128-window CAL-A read (1 EP); if it is worse than the sweep's entry read by > 0.01, restore the layer-entry snapshot (a layer can veto itself). A second sweep runs **only if** the first gained ≥ 0.02 on full CAL-A.
- **exact change:** new runner mode `mill/search.py --search layersweep` (per-layer snapshot/restore over `t1/t2` slices; everything else as I-037's runner).
- **budget:** per layer 6 × 0.25 EP micro + 1 EP confirm = 2.5 EP → 20 EP per sweep + CAL-B 1 EP = **21 EP** (≤ 41 EP if the second sweep triggers).
- **prediction:** −0.02..−0.05 vs 2.8580. The cheapest procedure here whose every accepted move was jointly measured in the only subspace where its renormalisation side effect lives. Expected to capture most of I-037's single-basin gain; what it cannot do is cross-layer coordinated moves — that gap is exactly what I-037/I-039 are priced against.
- **overfitting guard:** CAL-A 256 windows with a per-layer reserved slice (no layer is judged on another's slice); per-layer self-veto restore; hard cap **1,200 accepted flips**; CAL-B ship rule as protocol.
- **status:** queued
```mill
id: I-038
mode: process
run: --arm layered_half --rope --dump-state --search layersweep
```

### I-039 ★ · Checkpoint-population recombination (discrete crossover, one shipped state)
- **source:** discrete-search lens; population methods over the run's own trajectory diversity — the last-5 checkpoint saves that MILL-218/G-027/G-029 already assume exist, used here as *genotypes* instead of things to average or ensemble. WH-060 prices the contested population (10–16% of weights, ≥ 35% of late flips) — crossover is a search move aimed exactly at weights the trajectory itself never settled.
- **mechanism:** Population 12, all derived from the **same run**: the final state, the modal-5 state (MILL-218's readout, as a genotype), the counter-resolved τ=24 state (G-026's readout, as a genotype), the other 4 checkpoint states, and 5 children built by **uniform crossover** — for each installed position, copy the `(t1, t2)` pair *jointly* from one parent chosen per position (pair-joint, so a component combination a checkpoint actually held is never split) — parents drawn from the checkpoint set, plus counter-biased mutation (each position flips one component with probability `0.002 · |c|/32`). Score all 12 on full CAL-A (2 EP each). Then 6 generations: tournament-select 2 parents (best of 3 random members), produce 8 offspring by the same crossover + mutation, score each on full CAL-A, keep the best 12 of (parents + offspring), with the original final state as a permanent elite (the population can never lose the champion). Ship the best final member.
- **exact change:** new runner mode `mill/search.py --search population` (needs the last-5 `--dump-state` saves; crossover/mutation over dumped `t1/t2`, FP frame from the final save only, stated plainly — members are *states*, read through the final FP frame, the same era choice G-027 makes implicitly).
- **budget:** 12 × 2 EP initial + 6 generations × 8 offspring × 2 EP = 24 + 96 = 120 EP + CAL-B 1 EP = **121 EP**.
- **prediction:** −0.03..−0.08 vs 2.8580 — the largest ceiling in this file. Recombination reaches states no local path from the final state reaches cheaply: a weight that was right at checkpoint 3 and flipped away by checkpoint 5 can be restored *in combination with* the rest of the final state, per position, at population scale. If per-position checkpoint disagreement is mostly noise, CAL-B vetoes it and the entry retires the trajectory-diversity hypothesis with a number.
- **overfitting guard:** CAL-A 256 windows, full-set scoring of every member (no micro-slices — population selection on slices is how populations memorise); offspring must differ from the champion state in **≤ 8,000 positions (0.9%)** or they are discarded unscored; elite preservation; CAL-B ship rule as protocol, applied to the single best member only (no CAL-B shopping across the population).
- **status:** queued
```mill
id: I-039
mode: process
run: --arm layered_half --rope --dump-state --search population
```

### I-040 · Measured simulated annealing (post-training, CE-accepted)
- **source:** discrete-search lens; the honest post-training form of the idea MILL-223 reached for during training — with the one ingredient MILL-223 lacked: acceptance by **measured** calibration CE, not by a gradient-estimated ΔL.
- **mechanism:** 60 rounds. Each round proposes one batch of 16 flips drawn from the counter proposal distribution (probability ∝ |c|, direction = counter sign, no-ops excluded), applies it, `install()`s, and micro-evaluates on a rotating 64-window CAL-A slice. Δ = micro-CE change vs the incumbent's score **on the same slice** (paired, so slice difficulty cancels). Accept if Δ < 0, or with probability `exp(−Δ/T)` if Δ > 0, with T annealed geometrically 0.020 → 0.002 nats over the 60 rounds (T is in *measured nats*, not gradient units — the calibration MILL-223 could not make). Every 10 rounds, full-CAL-A read (2 EP) and snapshot-if-best; output is the best snapshot, so late hot wandering cannot damage the result.
- **exact change:** new runner mode `mill/search.py --search anneal` (own RNG stream; paired-slice scoring cache so each round costs one new micro-eval, the incumbent's slice score is already known).
- **budget:** 60 × 0.5 EP micro + 6 × 2 EP snapshots = 30 + 12 = 42 EP + final snapshot confirm 2 EP + CAL-B 1 EP = **45 EP**.
- **prediction:** −0.02..−0.06 vs 2.8580, high variance across seeds by design. Annealing's claim over I-037/I-038 is escaping the first basin: vote training ends in a state where every *counter-aligned* single move looks flat, and only accepted-worse batches cross to a neighbouring basin. If the 3-seed spread is wide with a good mean, the mill learns the landscape is multi-basin; if it ties I-038, the landscape is single-basin at this scale and the greedy entries own the territory.
- **overfitting guard:** CAL-A 256 windows; paired rotating slices; hard cap **960 accepted flips** (60 × 16, and rejected batches revert); best-snapshot (never last-state) output; CAL-B ship rule as protocol.
- **status:** queued
```mill
id: I-040
mode: process
run: --arm layered_half --rope --dump-state --search anneal
```

### I-041 · Focused search (WalkSAT-style: work only on the worst windows' disagreements)
- **source:** discrete-search lens; WalkSAT / focused local search for SAT — global greedy stalls because most constraints are already satisfied; progress comes from picking an *unsatisfied* constraint and fixing what it complains about. Transplant: an unsatisfied constraint is a high-loss calibration window; its complaint is its gradient.
- **mechanism:** 400 iterations. Maintain a rotating panel of 32 CAL-A windows with individually cached losses (panel re-scored every 20 iterations, 0.25 EP). Each iteration: take the panel's worst window, run **one backward** on it alone (cost counted below), and among that window's gradient's top-50 counter-aligned candidate slots (gradient sign agrees with a flip direction *and* the slot's counter does not oppose it), flip the single slot with the largest |gradient| — with probability 0.15 flip a random one of the 50 instead (the WalkSAT noise move, the escape hatch against cycling). No per-flip eval: the discipline is focus + the periodic full read. Every 50 iterations, full-CAL-A read (2 EP), snapshot-if-best, and any slot flipped 3 times is frozen for the rest of the search (anti-thrash, WH-058's hidden-thrash population is this entry's named enemy).
- **exact change:** new runner mode `mill/search.py --search focused` (per-window loss cache + single-window backward path reusing `Tiny.next_piece`; the only entry that computes gradients, and it never updates anything with them except the flip choice).
- **budget:** gradient cost 400 × (1 window fwd+bwd ≈ 0.016 EP) ≈ 7 EP + panel re-scores 20 × 0.25 EP = 5 EP + 8 × 2 EP full reads = 16 EP + CAL-B 1 EP = **29 EP** (stated as ≈ 29 EP; the gradient term is a compute-equivalent estimate, charged, not hidden).
- **prediction:** −0.01..−0.04 vs 2.8580. Per-flip cost is ~50× cheaper than any verified entry, so it makes 400 *targeted* moves inside a small budget; the risk is the mirror image — unverified flips chase the worst windows' idiosyncrasies. The snapshot discipline bounds the downside to the CAL-B veto.
- **overfitting guard:** CAL-A 256 windows but the panel rotates through all of them (no window is focused twice until all have been panel members); per-slot 3-flip freeze; hard cap **400 flips** (one per iteration); snapshot-if-best every 50 iterations; CAL-B ship rule as protocol — this entry is the one most likely to *need* the veto, and it is priced accordingly.
- **status:** queued
```mill
id: I-041
mode: process
run: --arm layered_half --rope --dump-state --search focused
```

### I-042 · Compensating-pair search (2-flip moves that preserve each row)
- **source:** discrete-search lens; 2-opt reasoning — a single-flip local optimum can hide improving *pairs*: one flip that hurts alone (+δ) and one that helps alone (−ε) with ε < δ, whose joint move improves because the pair preserves the row's total drive while rearranging it. G-035's single-flip walk is blind to this entire neighbourhood by construction.
- **mechanism:** Candidate pairs live inside one output row of one BitLinear: slot *i* flips in its counter's direction, slot *j* (same row) flips *against* the installed-sum direction so the row's sum of `s` is unchanged by the pair. Rank all such pairs by `|c_i| + |c_j|`, take the top 200. Evaluate in groups: apply 10 pairs (20 flips), `install()`, micro-eval on a 64-window CAL-A slice (0.5 EP); if the group improves, bisect it (≤ 4 further micro-evals) to isolate the contributing pairs and keep only those; if not, revert the group whole. 20 groups maximum. Output = incumbent after all kept pairs, confirmed on full CAL-A.
- **exact change:** new runner mode `mill/search.py --search pairs` (row index built from the dumped layer shapes; pair generator + group-bisect driver).
- **budget:** 20 × 0.5 EP groups = 10 EP + bisection ≤ 20 × 0.5 EP = 10 EP (capped) + 4 full-CAL-A confirms × 2 EP = 8 EP + CAL-B 1 EP = **29 EP**.
- **prediction:** −0.01..−0.03 vs 2.8580 standalone; its larger value is sequential — run *after* I-038 on I-038's output, it is the priced test of whether the greedy optimum was a real optimum or a single-flip artefact. Standalone-first is deliberate: if pairs win from the champion directly, pair structure exists in the vote equilibrium itself.
- **overfitting guard:** CAL-A 256 windows; pair cap 200 proposed / **≤ 80 kept pairs (160 flips)**; row-sum preservation means the level histogram and `mean|s|` denominators move only through the kept pairs' arrangement, not their totals; CAL-B ship rule as protocol.
- **status:** queued
```mill
id: I-042
mode: process
run: --arm layered_half --rope --dump-state --search pairs
```

### I-043 · Row best-response search (the output row as the coordinate)
- **source:** discrete-search lens; F-008's per-neuron perturbation bound read backwards — if a row's output is what the function prices, the row (not the weight, not the layer) is the natural coordinate: a row move rearranges all of one neuron's incoming ternary weights at once, in the direction that neuron's own evidence points.
- **mechanism:** Rank all 3,456 output rows (per block: qkv 576, out 192, up 768, down 192) by their total counter mass `Σ|c|` over both components; take the top 512 rows. For each row in rank order: the row move = flip every slot in the row with |c| ≥ 16 in its counter direction (typically 2–8 flips; rows with zero qualifying slots are skipped). Moves are evaluated in blocks of 8 rows: apply 8 row moves, `install()`, micro-eval on a 32-window CAL-A slice (0.25 EP); if the block improves, keep all 8 and then test dropping each row move in turn only if the block gain was < 0.002 (marginal blocks pay for attribution); if the block does not improve, revert all 8. Three passes over the 512 rows, re-ranked between passes by fresh counter mass (counters do not change during search — re-ranking is by *kept-move* history: rows whose moves were kept drop out, reverted rows return at half priority).
- **exact change:** new runner mode `mill/search.py --search rows` (row-mass ranking + block-of-8 evaluation driver in the I-037 runner).
- **budget:** per pass 512/8 × 0.25 EP = 16 EP → 3 passes = 48 EP + marginal-block attribution ≤ 4 EP + full-CAL-A confirms 2 × 2 EP = 4 EP + CAL-B 1 EP = **57 EP** (attribution capped; overflow blocks skip attribution, stated in the log).
- **prediction:** −0.015..−0.045 vs 2.8580. Row moves are the smallest moves that can express a *feature* change (one neuron re-deciding what it detects); weight moves mostly express noise around a feature. If row search beats I-038 per EP, the coordinate granularity lesson generalises to every future search entry.
- **overfitting guard:** CAL-A 256 windows; hard cap **2,500 accepted flips** across all passes; a row may be kept-moved at most once per pass; CAL-B ship rule as protocol.
- **status:** queued
```mill
id: I-043
mode: process
run: --arm layered_half --rope --dump-state --search rows
```

### I-044 · Iterated local search (greedy descent + counter-weighted kicks)
- **source:** discrete-search lens; iterated local search (Lourenço et al.) — the standard answer when greedy descent works but its basin is not trusted: descend, perturb the *result* (not the start), descend again, keep the best. Distinct from I-040: ILS's acceptance is elitist (only near-best restarts survive) where annealing's is thermal (worse states are *lived in*, not just visited).
- **mechanism:** Descent operator = a fixed cheap greedy: I-038's batch rule restricted to the top 2 layers by counter mass, micro-evaluated, ≈ 6 EP per descent (budgeted, not re-derived). Iteration: from the best state so far, apply a **kick** of 100 flips drawn ∝ |c| (counter-weighted, so kicks explore plausible territory, not uniform noise), run one descent, read full CAL-A (2 EP); accept the result as the new restart point iff its CAL-A ≤ best + 0.005, else restart from the best snapshot. 6 iterations. Output = best snapshot ever read on full CAL-A.
- **exact change:** new runner mode `mill/search.py --search ils` (composes I-038's descent as a subroutine — the one entry that depends on another's code landing first; flagged as such).
- **budget:** 6 × (6 EP descent + 2 EP read) = 48 EP + CAL-B 1 EP = **49 EP**.
- **prediction:** −0.02..−0.05 vs 2.8580. Kicks of 100 counter-weighted flips are large enough to leave the greedy basin (≈ 0.01% of positions, ~10× a training step's flip volume) and small enough that one descent re-settles them; the +0.005 acceptance band is what lets it drift along a ridge instead of re-descending into the same basin six times — the failure mode the iteration count is there to reveal if it happens (log restart-point Hamming distances; six identical restarts = single-basin evidence, reported as such).
- **overfitting guard:** CAL-A 256 windows; cumulative distinct flipped positions **≤ 3,000**; best-snapshot elitism (the shipped state is always a full-CAL-A-read state, never a post-kick state); CAL-B ship rule as protocol.
- **status:** queued
```mill
id: I-044
mode: process
run: --arm layered_half --rope --dump-state --search ils
```

### I-045 · Large-neighbourhood search: destroy-and-repair the two most contested layers
- **source:** discrete-search lens; LNS (Shaw) aimed by WH-051 + WH-060's anatomy — frustration (boundary-pinned counters) and c1/c2 disagreement (both |c| ≥ 8, opposite signs) jointly name the layers where the installed state and its own evidence disagree most. Those layers are where a *large* move has its best prior; everywhere else the state is left exactly alone.
- **mechanism:** From the dump, compute per layer: frustrated fraction (WH-051) + contested fraction (WH-060). Take the top 2 layers. **Destroy:** in those layers only, revert every contested slot (sign(c1) ≠ sign(c2), both |c| ≥ 8) to its modal-5 checkpoint value (MILL-218's saves) — an evidence-chosen alternative state, not a random reset. **Repair:** run I-037's batch rule (counter-proposed batches of 24, micro-evaluated, best-batch acceptance) restricted to the 2 destroyed layers, 20 rounds. **Restore guarantee:** if the repaired state's full-CAL-A is worse than the champion's, ship the champion — the destroy step is fully reversible from the dump, by construction.
- **exact change:** new runner mode `mill/search.py --search lns` (anatomy computation over the dump + I-037's batch driver with a layer mask; needs modal-5 saves).
- **budget:** repair 20 rounds × 8 batches × 0.25 EP = 40 EP + 2 full-CAL-A reads × 2 EP = 4 EP + CAL-B 1 EP = **45 EP**.
- **prediction:** −0.01..−0.05 vs 2.8580, the highest variance in the file after I-040. Concentrating the entire move budget on the two layers with a measured state/evidence conflict is either exactly right (the conflict was the loss) or exactly wrong (the conflict was load-bearing tension the loss needs) — the restore guarantee caps the cost of being wrong at the budget, and the anatomy-vs-outcome pair is a deliverable either way: it is the first test of whether WH-051/060's statistics *cause* anything.
- **overfitting guard:** CAL-A 256 windows; only 2 of 8 layers may move at all (a structural cap no scalar budget can imitate); accepted flips **≤ 5,000** including the destroy step's reverts, all inside the 2 layers; CAL-B ship rule as protocol.
- **status:** queued
```mill
id: I-045
mode: process
run: --arm layered_half --rope --dump-state --search lns
```

### I-046 · Beam search over flip batches (width-4, depth-10)
- **source:** discrete-search lens; beam search — the middle point between I-037's single path and I-039's population: several partial solutions are carried in parallel and pruned by measured score, so an early batch that looks neutral is not discarded if its *children* score well (the failure mode of pure greedy batch acceptance).
- **mechanism:** Beam = 4 states, all starting at the champion. Depth 10. Each state expands 3 children, each child = one 20-flip batch from a **different proposal family** (this is the beam's diversity mechanism, stated explicitly): (a) counter-top batch, (b) checkpoint-difference batch (positions where the modal-5 state differs from this state, flipped toward modal), (c) counter-weighted random batch. Score every child on a 64-window CAL-A slice fixed per depth (0.5 EP each; all children at a depth share the slice, so pruning compares like with like). Keep the best 4 of 12 as the next beam. Every 3 depths, re-score the whole beam on full CAL-A (2 EP each) and re-rank by that, not by slice scores. Ship the best final beam member by full CAL-A.
- **exact change:** new runner mode `mill/search.py --search beam` (multi-state driver — the runner holds 4 `t1/t2` state copies, 4 × ~0.9 MB of ternary state, negligible; FP frame shared).
- **budget:** per depth 12 × 0.5 EP = 6 EP → 10 depths = 60 EP + re-scores 3 × 4 × 2 EP = 24 EP + CAL-B 1 EP = **85 EP**.
- **prediction:** −0.02..−0.05 vs 2.8580. Beam's edge over I-037 is keeping the modal-difference and random lineages alive alongside the counter lineage for 10 depths; its cost is the widest per-depth evaluation in the file. If the winning lineage is (a) in ≥ 8 of 10 depths, the counter prior was sufficient and I-046 retires itself in favour of I-037 — lineage tracking is logged for exactly that verdict.
- **overfitting guard:** CAL-A 256 windows; per-depth shared slices (no child is scored on a private slice); path cap **≤ 200 flips per member** (10 × 20) and final shipped member must differ from champion in **≤ 600 positions**; CAL-B ship rule as protocol, applied to the shipped member only.
- **status:** queued
```mill
id: I-046
mode: process
run: --arm layered_half --rope --dump-state --search beam
```

### I-047 · Histogram-preserving swap search (arrangement only, totals frozen)
- **source:** discrete-search lens; a controlled experiment disguised as a search — every other entry can win by *changing* the level histogram (more/fewer zeros, different ±2 mass). A swap move (one slot +1 step, another slot −1 step, same layer) preserves the layer's installed-sum histogram and its `mean|s|` denominator **exactly**, so any win is pure *arrangement*: the right weights at the levels, not more of a level. No pooled or candidate entry has ever separated those two claims.
- **mechanism:** Donors = slots whose counter argues down (c ≤ −8) at a level above the layer minimum; receivers = slots whose counter argues up (c ≥ +8) below the layer maximum; a swap pairs one donor flip with one receiver flip in the same layer. Evaluate batches of 8 swaps (16 flips) on rotating 32-window CAL-A micro-slices (0.25 EP): accept the best of 4 candidate batches per round iff its micro-Δ < 0, with a swap-tabu (a swapped pair may not be re-swapped, in either direction, for the rest of the search — swaps can otherwise undo themselves invisibly). 40 rounds. Confirm on full CAL-A every 10 rounds, snapshot-if-best.
- **exact change:** new runner mode `mill/search.py --search swaps` (donor/receiver pairing from the counter field; histogram assertion after every accepted batch — `mean|s|` per layer bit-compared before/after, a free correctness check no other entry gets).
- **budget:** 40 × 4 × 0.25 EP = 40 EP + 4 × 2 EP confirms = 8 EP + CAL-B 1 EP = **49 EP**.
- **prediction:** −0.01..−0.035 vs 2.8580 — deliberately the most conservative win prediction among the batch entries, because the histogram channel (plausibly part of any search gain) is closed to it by construction. Its verdict disciplines the whole lens: I-037's gain minus I-047's gain at matched flips *is* the histogram's share of post-training search value, a number the lab will otherwise never know.
- **overfitting guard:** CAL-A 256 windows; swap cap **320 swaps (640 flips)**; exact histogram preservation asserted per batch (a violated assertion voids the run, not just the batch); CAL-B ship rule as protocol.
- **status:** queued
```mill
id: I-047
mode: process
run: --arm layered_half --rope --dump-state --search swaps
```

### I-048 · (1+λ) black-box evolution, unguided — the guidance control
- **source:** discrete-search lens; filed as a **control**, not a hope — every other entry spends the counter field, gradients, or checkpoint structure as guidance, and none of that guidance has ever been priced against no guidance at matched eval budget. This entry is the price tag.
- **mechanism:** (1+8) evolution, 8 generations. Parent = best state so far by CAL-A (128-window subset, 1 EP per evaluation — the subset is fixed for the whole entry). Each generation: 8 offspring, each = parent + exactly 60 **uniformly random** component flips (uniform over slots, uniform direction among legal moves; no counter, no gradient, no checkpoint information anywhere in the loop). Offspring scoring on the same 128-window subset; the best offspring replaces the parent iff it scores better, else the parent survives unchanged. Ship the final parent.
- **exact change:** new runner mode `mill/search.py --search evolve-control` (the I-039 population driver with its proposal machinery removed — sharing the driver is what makes the comparison honest).
- **budget:** 8 generations × 8 offspring × 1 EP = 64 EP + CAL-B 1 EP = **65 EP**.
- **prediction:** −0.00..−0.02 vs 2.8580, and most of that is expected to be CAL-A selection noise that the CAL-B ship rule vetoes — i.e. the honest prediction is that this entry usually ships the champion. That is its function: if I-048 instead matches I-037/I-039 on held, the counter/checkpoint guidance in this whole lens earns nothing and the file should be re-read as one expensive null; if it ships the champion while they win, guidance is priced at the difference.
- **overfitting guard:** CAL-A **128 windows only** (deliberately the weakest set in the file — the control should face the *hardest* time transferring, so a transfer here cannot be attributed to a bigger calibration set); mutation distance fixed at 60 flips/offspring (no distance tuning); CAL-B ship rule as protocol, expected to fire often.
- **status:** queued
```mill
id: I-048
mode: process
run: --arm layered_half --rope --dump-state --search evolve-control
```

---

## Lens ranking note

Ranked by expected held gain × probability of real transfer ÷ eval budget, with the
overfitting guard's strength counted in the probability term:

1. **I-037 ★ (tabu batch, 97 EP)** — the complete procedure: interaction-aware batch
   acceptance, tabu memory, aspiration, best-snapshot output. The entry the lens
   would run first at full size.
2. **I-039 ★ (checkpoint population, 121 EP)** — the highest ceiling and the only
   non-local move set; recombination over the run's own states is information no
   local search can synthesise.
3. **I-038 ★ (layer sweep, 21 EP)** — the best value in the file: clean per-layer
   attribution, a self-veto per layer, and the smallest budget of any entry with a
   joint-measurement acceptance rule.
4. I-040 (annealing, 45 EP) · 5. I-046 (beam, 85 EP) · 6. I-044 (ILS, 49 EP) ·
7. I-043 (rows, 57 EP) · 8. I-045 (LNS, 45 EP) · 9. I-041 (focused, ≈29 EP) ·
10. I-042 (pairs, 29 EP) · 11. I-047 (swaps, 49 EP) · 12. I-048 (control, 65 EP).

**Cheapest search with a real chance: I-038 at 21 EP** (≈ 21 held-eval equivalents,
no retraining) — one layer sweep, every accepted batch jointly measured, per-layer
restore if a layer hurts. I-041/I-042 match its price (~29 EP) but buy unverified
or second-order moves; I-038 is the cheapest entry whose acceptance rule is the
same kind (measured, joint, reversible) as the top-ranked entry's.

**The lens's shared bet, stated once:** the champion's 2.8580 is a *vote equilibrium* —
a state where 32-vote evidence stopped moving weights — and no procedure in the lab
has ever optimised measured loss over the discrete state directly, at any budget.
If all twelve entries ship the champion under their CAL-B rules, that is a strong,
priced result: the vote equilibrium is a loss optimum at calibration resolution,
and post-training search joins the readout lens as a closed direction — with the
budgets above as the cost of knowing.

## Lens 6 — Kernel semantics (was KT-###)

### I-049 ★ · Vote-then-sum: per-token majority voting (integer vote matmul)
- **source:** kernel-semantics lens — the vote rule re-derived from the shape of the
  backward GEMM itself (`grad_w = upstreamᵀ @ x` is a reduction; the order of
  `sign` and `sum` in that reduction is a free choice the current code makes silently).
- **mechanism:** Cast the vote **per token position first, then sum**: for each weight,
  `v = Σ_t sign(upstream_t · x_t)` over the step's 8,192 positions, computed as one
  int8-sign × int8-sign → int32 GEMM per BitLinear (exact integer arithmetic,
  |v| ≤ 8,192). The counter increments by `sign(v)` only if `|v| ≥ 410`
  (net token majority ≥ 5% of positions); otherwise the weight abstains that step.
  No median gate. t1/t2 arbitration, clamp ±32, reset-on-flip unchanged.
- **exact change:** new flag `--vote-mode tokensum --token-tau 0.05` on `Layered`
  (and `Direct`); the vote path no longer reads `m.weight.grad` for BitLinear weights.
- **semantic difference, plainly:** today a weight's vote is decided by the *summed*
  gradient — one token position with a huge gradient outweighs hundreds of small
  ones (magnitude rules). Here every position gets exactly one vote of equal weight
  and only the majority direction counts (democracy rules). On this corpus that is a
  real change, not a nuance: the ~23% numeric-dump share (E-020) produces outsized
  gradients and currently steers counters out of proportion to its token share;
  under vote-then-sum its influence is capped at its token share, by construction.
- **gradient/vote path:** the FP32 backward still runs for the AdamW parts and for
  `log_scale` (whose grad `(g·t).sum()` is kept from the FP pass, charged honestly —
  so this entry pays one FP backward **plus** one sign-GEMM per layer per step,
  ≈ +1 GEMM against the step's ~3 GEMM-equivalents of BitLinear matmul, i.e.
  roughly +15–20% step time in GEMM terms, likely less end-to-end in torch).
  Counters consume only the integer vote matmul's output.
- **prediction:** quality −0.02..+0.06 at equal steps (the wide band is honest: if
  magnitude information is doing real work, this loses; if outlier positions are
  doing damage, it wins). Detectability arithmetic: per-token sign agreement p
  gives E[net] = 8192·(2p−1), σ ≈ √8192 ≈ 91; τ=410 admits only weights with
  p ≳ 0.55 sustained — a *stronger* evidence bar than one median-gated sign, so
  expect flip share to fall ~30–50%; if it falls >70%, τ is the binding constraint
  and the dose variant τ=0.02 is the follow-up. Throughput −10..−20% (extra GEMM).
  Distinct from A-004 (sign of the batch-mean = today's rule), A-013 (loss-weighted
  FP sum — magnitudes kept), F-018 (4 sub-batch FP signs + per-step quorum; here
  8,192 persistent per-position votes summed into the counter stream).
- **status:** queued

### I-050 ★ · Lane-local gate: the median is computed per 32-weight SIMD lane
- **source:** kernel-semantics lens — the median gate is the one operation in
  `Layered.step` that is a *global, layer-wide reduction*; it is what stops the vote
  update from being a pure elementwise/SIMD kernel. This entry chooses the vote
  rule that vectorizes, and says what that costs semantically.
- **mechanism:** Weights are viewed in row-major lanes of 32 consecutive fan-in
  elements (one wide vector). The gate threshold is the median |g| **within the
  lane** instead of within the layer: `strong = |g| ≥ median_lane(|g|)`, computed
  on the reshaped `[..., 32]` tensor with no cross-lane communication. Vote,
  clamp, flip, reset otherwise unchanged.
- **exact change:** new flag `--gate lane32` on `Layered`/`Direct`.
- **semantic difference, plainly:** today ~50% of a *layer* votes, but they are
  whichever weights happen to sit in the layer's hot regions — a quiet output row
  may contribute almost no voters for long stretches. Lane-local gating forces
  **every 32-weight segment to contribute exactly ~16 voters every step**: flip
  pressure is equalized across the whole matrix by construction, and a weight now
  competes with its 31 fan-in neighbours instead of with the layer. Evidence
  becomes a local contest, not a global one.
- **gradient/vote path:** unchanged FP32 backward; only the gate statistic's
  reduction scope changes, inside the existing vote update (composes with the
  C-C04 fused kernel rather than competing with it — the fused kernel gets
  *simpler*, since its one global reduction disappears).
- **prediction:** throughput +0..+2% end-to-end (the vote update is a few percent
  of step time per C-C04's own accounting; the win is kernel simplicity, not
  seconds). Quality −0.03..+0.03. The decisive value is diagnostic: if lane32 ≈
  champion, gate *scope* is free and every future fused kernel can drop the global
  median permanently; if it wins outright, local competition was the active
  ingredient. Sibling control: A-002 (per-row gate, 192–768 wide) — lane32 is the
  sub-row point on the same scope dial, and the pair brackets where scope stops
  mattering.
- **status:** queued

### I-051 ★ · Clipped-partial LUT forward: the error budget is a trainer variable
- **source:** kernel-semantics lens, built directly on `kernels-lut/RESULTS-LUT.md`:
  the exact LUT is proven bit-identical (err 0.0), so an *approximate* LUT's error
  can be priced exactly, against an oracle, per step.
- **mechanism:** LUT g=4 forward as in the bench (81-entry tables per activation
  group of 4), except table entries are stored **clipped**: a group partial sum
  (exact range ±508 in activation-code units) is saturated at ±L, with L annealed
  508 → 160 over the run. The trainer logs the measured forward error vs the exact
  LUT each 100 steps (max and RMS per output), so the error budget ε(L) is a
  measured quantity, not an assumption. Saturated groups contribute exactly ±L
  regardless of how large their true partial was.
- **exact change:** new flag `--fwd lutclip --clip-anneal 508:160` in
  `BitLinear.forward` for the vote arms, behind the STE wrapper the LUT stream's
  own note requires (below).
- **semantic difference, plainly:** the forward is no longer the ternary matmul
  the weights describe — activation groups with very large partial sums are
  *softly clipped inside the sum itself*. A weight fed by outlier-heavy inputs
  has its forward contribution capped per group, so the network the loss is
  computed on is a mildly outlier-suppressed version of the installed network,
  with the suppression strength (L) as an annealed trainer hyperparameter —
  an approximation treated as a mechanism, in the family of activation clipping
  (cf. MILL-129's Hadamard motivation) but arising from table storage, at the
  group level, and priced exactly.
- **gradient/vote path:** as RESULTS-LUT.md requires, the LUT forward carries no
  autograd path to the weights, so a straight-through wrapper is added: backward
  passes the upstream gradient to the counters (vote arms) as if the clipped LUT
  forward were the identity-quantized forward — the same detach trick
  `BitLinear` already uses. Honest consequence: vote evidence is computed *at
  the clipped forward*, so weights feeding saturated groups receive attenuated,
  biased evidence — that bias is the mechanism under test, and WH-043's
  gradient-noise tolerance curve is the prior for how much bias is free.
- **prediction:** error arithmetic: real activations are absmax-scaled, so most
  |x| are far below 127; a 4-group partial is a sum of 4 products of a ternary
  sign with such codes, typical |partial| ≈ 30–80, so L=160 saturates only the
  outlier tail (est. <2% of groups late, more early before the anneal bites).
  Worst-case per-output error at K=192 (48 groups) is bounded by
  Σ_sat (|partial| − L) and is *measured*, with kill line: mean RMS error
  >5% of mean |Y| (≈ 886 code units at champion shapes → RMS budget ≈ 44)
  retires the anneal point. Quality −0.01..+0.04; throughput **unclaimed** —
  LUT timing was never measured (deferred in RESULTS-LUT.md) and the torch
  gather path is expected to lose to BLAS; this entry is bought for its
  semantics and its exact error ledger, and any future native kernel inherits
  both.
- **status:** queued

### I-052 · Int8 backward for the vote path: evidence on an integer lattice
- **source:** kernel-semantics lens — C-C01 proved the *forward* integer path is
  exact; this entry asks what happens when the *backward* weight-gradient GEMM
  is integer too, which is not exact, and says so.
- **mechanism:** For each BitLinear, the weight gradient is computed as
  `grad_w = upstream_qᵀ @ x_q` in int32, where `upstream_q` is the upstream
  gradient quantized per token-row to int8 by absmax (the same quantization the
  forward already applies to activations) and `x_q` is the forward's saved int8
  activation codes. The activation-gradient path to earlier layers stays FP32,
  so the distortion is applied per layer independently and does not compound
  through depth. The vote (sign + median gate) reads this integer gradient.
- **exact change:** new flag `--bwd int8` on `Layered`/`Direct` (custom autograd
  function for BitLinear weight-grad only; STE arms excluded — their latent
  weights need the FP gradient this entry deliberately destroys).
- **semantic difference, plainly:** vote evidence gains an **absolute floor**:
  an upstream contribution below 1/127 of its row's max contributes exactly
  zero, where today it contributes its true small FP value. And all magnitudes
  land on an integer lattice — ties at the median become common, so the gate's
  `≥` admits a tie-block whose size varies step to step. The gate stops being
  purely relative-to-the-layer and becomes partly absolute (row-max-relative).
- **gradient/vote path:** this entry *is* the gradient path: exact integer
  accumulation (max |sum| = 8192·127·127 ≈ 1.3×10⁸ < 2³¹ ✓), quantized inputs.
  `log_scale` grad keeps the FP `(g·t)` value from a shadow FP grad_w computed
  only as a scalar reduction — no: charged honestly, log_scale grad is computed
  from the integer grad_w as well (`(g_int·t).sum()`), a second, smaller bias
  that the entry accepts and the probe's log_scale trajectory will show.
- **prediction:** quality −0.01..+0.03 (WH-043's premise — sign votes tolerate
  large gradient perturbations — predicts near-flat; the lattice/tie effect is
  the risk). Throughput unpriced: the int32 GEMM's speed vs FP32 on this
  2-thread box
...[truncated 12507 chars]  is exactly what C-C01's still-missing timing would have told us; this entry
  must not be probed until that bench lands or it runs its own paired timing.
  Ranked below I-050 for precisely that reason.
- **status:** queued

### I-053 · Counter-proximate sparse backward: the grad_w GEMM only computes near-flip weights
- **source:** kernel-semantics lens — the backward's grad_w GEMM computes a
  gradient for every weight every step, but the vote trainer can only *use*
  evidence at weights whose counters are within reach of a flip.
- **mechanism:** grad_w is computed only for output columns whose weight has
  |c1| ≥ 16 or |c2| ≥ 16 (either component within half of V=32), plus a rotating
  5% audit slice of all remaining weights (hash-rotated per step). All other
  weights get grad exactly 0 that step: no vote, counter unchanged. The mask is
  recomputed from the counters each step (one comparison pass, no GEMM).
- **exact change:** new flag `--bwd-sparse prox --audit 0.05` on
  `Layered` (column-masked grad_w; grad_x path untouched and full — earlier
  layers still receive complete signal).
- **semantic difference, plainly:** evidence allocation becomes
  *state-dependent and positively reinforcing*: weights near a flip get full
  evidence every step; weights at c ≈ 0 are blind except when the audit slice
  visits them (expected revisit every ~20 steps), so a weight whose true
  gradient reverses while it sits at zero waits, on average, 20 steps to even
  start its 32-vote climb. The trainer develops a rich-get-richer evidence
  economy that today's uniform backward does not have.
- **gradient/vote path:** vote rule, gate, clamp, flip all unchanged — what
  changes is *which weights receive a gradient at all*. AdamW parts and
  log_scale (a scalar reduction over the computed columns only — noted as a
  small bias: log_scale grad misses the masked columns' `(g·t)` mass) as
  described.
- **prediction:** arithmetic depends on the counter distribution, which the
  probe must report: if ~25% of weights qualify + 5% audit, the grad_w GEMM
  (⅓ of BitLinear matmul FLOPs: fwd 1, grad_x 1, grad_w 1) drops to ×0.30,
  i.e. ~23% off backward matmul, ~15% off step matmul — in torch, with mask
  overhead, honestly 0–10% end-to-end. Quality +0.00..+0.04 at equal steps
  (the cold-population cost), possibly net-negative at equal minutes if the
  step saving doesn't materialize. Distinct from F-044 (eligibility rotates
  uniformly by hash, state-blind, and *pauses counters*; here eligibility is
  counter-driven and grad_x is never masked) and F-045 (counter *storage*
  eviction; nothing here is evicted).
- **status:** queued

### I-054 · Block-sparse flip application: a block installs when 2 of its weights are pending
- **source:** kernel-semantics lens — `install()` currently rewrites all
  884,736 FP weights every step to apply ~970 flips (0.11%); the computation
  structure (dense install) forces flips to be temporally uniform, which is a
  semantic choice nobody made deliberately.
- **mechanism:** Counters update every step exactly as now, but a threshold
  crossing only marks the flip *pending* (direction recorded, counter reset as
  usual). Installed weights live in 128-weight blocks (6,912 blocks at
  champion); when a block accumulates ≥2 pending flips, all its pending flips
  install in one scatter pass and only that block's slice of the installed
  buffer is recomputed. Blocks below the trigger keep serving their old values.
- **exact change:** new flag `--install block-sparse --block 128 --block-k 2`
  on `Layered` (pending bitmask + direction arrays: +2 bits/weight state,
  charged).
- **semantic difference, plainly:** the installed network lags its own counters
  by a block-dependent delay, and flips land in **spatially correlated bursts**
  instead of a uniform drizzle. A block with diffuse, slow evidence waits
  longer (its flips integrate more counter cycles before acting); a hot block
  installs almost immediately. That is a per-block adaptive effective
  threshold implemented purely as an install-scheduling rule.
- **gradient/vote path:** backward and votes run against the *installed*
  (lagged) weights — gradients are honest gradients of the network actually
  being served, which is one step more principled than it sounds: today the
  same is true with a lag of exactly one step for every weight; here the lag
  varies 1..~15 steps by block. Counters keep counting against the lagged
  forward throughout.
- **prediction:** delay arithmetic: ~970 flips/step over 6,912 blocks ≈ 0.14
  pending/block/step → mean wait to k=2 ≈ 14 steps (Poisson; hot blocks much
  less, cold blocks much more — the spread is the mechanism). Install write
  traffic: install events/step ≈ 970/2 ≈ 485 blocks × 128 = ~62k weights
  ≈ 7% of the current full install — a ~14× cut in install writes, worth
  maybe +1–3% end-to-end. Quality −0.01..+0.05; the burst/delay interaction
  with F-010's staleness concern is the named risk. Distinct from A-016
  (global 8-step batching — a *time* trigger hitting all blocks at once),
  A-018 (rotating block schedule), F-008 (per-row cap of 1 flip/step — a
  *limit*, not a trigger; unchosen flips there stay counted, here they are
  recorded and certain to land).
- **status:** queued

### I-055 · Stochastic-rounding int8 gradient accumulation across micro-batches
- **source:** kernel-semantics lens — gradient accumulation is normally a
  pure batching trick; at int8 accumulator precision it stops being one.
- **mechanism:** The batch of 32 is run as 8 micro-batches of 4. Weight
  gradients accumulate in an **int8 fixed-point accumulator** (1 byte/weight)
  with stochastic rounding: per layer, quantum q = mean|g|/16 measured on
  micro-batch 1; each micro-gradient is added as round_sr(g_micro / q),
  saturating at ±127q. After 8 micro-batches, one vote is cast from the
  accumulator (sign + median gate on accumulator magnitudes, as today) and
  the accumulator zeroes.
- **exact change:** new flag `--accum sr8 --micro 8` on `Layered`/`Direct`
  (accumulator replaces the FP32 grad buffer for BitLinear weights only;
  AdamW parts keep normal FP accumulation).
- **semantic difference, plainly:** the vote sees a *temporally quantized*
  gradient. A weight with a persistent micro-gradient of 0.4q accumulates
  ≈ 3.2 quanta over the step in expectation — stochastic rounding is
  unbiased, so weak-but-steady evidence survives; under deterministic
  rounding (or under today's median gate applied per micro-batch) it would
  vanish. Conversely a single bursty micro-gradient saturates at 127q and
  cannot dominate the sum the way an FP outlier can. Precision becomes a
  vote-shaping choice: the accumulator is a low-pass, outlier-clipping
  evidence filter that happens to be 1 byte wide.
- **gradient/vote path:** votes consume only the int8 accumulator; this is a
  within-step structure (the accumulator never carries across steps).
  Distinct from MILL-226 resid8 (a *cross-step* residual in a different
  trainer arm whose crossings flip weights directly — no vote, no gate) and
  F-017 (TPDF noise added once to the full-batch gradient before the gate —
  no accumulation, no saturation, no micro structure) and A-100 (FP
  accumulation ×2 — exact batching, no precision change).
- **prediction:** memory: grad buffer for ternary weights drops 4 B → 1 B
  (884,736 × 3 B ≈ 2.7 MB — small, stated honestly). Throughput ~neutral in
  torch (8 smaller backwards may even lose); the claim is semantic.
  Quality −0.02..+0.02. Its real product is a measurement: if int8-SR
  accumulation is flat vs FP, the vote path provably needs almost no
  gradient precision, which licenses I-052's integer backward and any
  future low-precision kernel; if it loses, the loss localizes *where*
  precision matters (temporal integration, not the sign).
- **status:** queued

### I-056 · Quantized-probability attention: softmax output snapped to a 1/256 grid
- **source:** kernel-semantics lens — a fixed-point attention pipeline
  (uint8 probabilities feeding an int8 PV product) is the computation
  structure a CPU kernel wants; this entry prices what it does to the model.
- **mechanism:** Attention runs in the explicit form (the C-C06 structure,
  which exists as a bench) with one change: after softmax, probabilities are
  rounded to multiples of 1/256 and **not** renormalized (row sums land in
  [1−δ, 1], δ measured and logged). P is stored uint8; the PV product reads
  the quantized P. Everything else — RoPE, ternary projections — unchanged.
- **exact change:** new flag `--attn qsoftmax` in `Block.forward` (vote and
  STE arms both; it is a forward-structure change, trainer-agnostic).
- **semantic difference, plainly:** attention becomes **exactly sparse at
  the tail and coarse at the head**: any probability < 1/512 rounds to
  exactly 0, so barely-attended tokens contribute *nothing*, not a little;
  a probability of 1/256 carries up to 50% relative error, while p > 1/8 is
  accurate to <2%. The head's output is a quantized mixture — the attention
  distribution the rest of the network sees is a different, peakier
  distribution than the logits describe.
- **gradient/vote path:** straight-through on the rounding (gradients flow
  as if P were unquantized), Q/K gradients computed from the quantized P —
  so vote evidence for the qkv/out projections is evidence about the
  quantized-attention network, consistently with I-051's principle that
  the gradient belongs to the forward actually run. AdamW parts unaffected
  structurally.
- **prediction:** arithmetic: at CTX 256, uniform attention is p = 1/256 —
  exactly one quantum — so early-training, near-uniform heads are maximally
  distorted (entries snap to {0, 1/256, 2/256}); peaked heads barely notice.
  Expect quality +0.00..+0.05 early, shrinking as head entropy falls; the
  probe must log per-head entropy beside held loss or the number is
  uninterpretable. Throughput ~0 claimed at CTX 256 (attention is a small
  share; C-C06's manual form is expected *slower* than SDPA) — this is a
  semantics probe whose value grows with context length, bought cheap now.
  Not covered by B-023 (sigmoid attention — different function, not a
  quantized softmax) or any pooled entry.
- **status:** queued

### I-057 · Stale-forward pipelining: votes are cast on last step's weights
- **source:** kernel-semantics lens — every pipelined kernel design (install
  overlapping the next forward) secretly assumes one-step-stale gradients
  are free; nobody in the pool has priced that assumption.
- **mechanism:** Two installed buffers ping-pong. Step k's forward and
  backward run against the weights installed at the end of step k−2's vote
  update — i.e. `t_fwd` lags the voting state `t_cur` by exactly one step.
  Votes from g(t_fwd) update t_cur's counters under the unchanged rule.
- **exact change:** new flag `--fwd-lag 1` on `Layered` (+1 installed-buffer
  copy: 884,736 × 4 B ≈ 3.5 MB, charged).
- **semantic difference, plainly:** every vote is evidence about the
  *previous* network. Today a weight's counter integrates gradients of a
  network that contained its own current value; here it integrates gradients
  of a network one flip-generation older. At 0.11% flip share, t_fwd and
  t_cur differ in ~970 weights — the bias is small, but it is *systematic*
  exactly at the weights that just flipped (their freshest evidence describes
  the value they just left).
- **gradient/vote path:** gradients are exact gradients of t_fwd (no STE
  fiction); the staleness is in *which* network they describe, and the
  counters absorb it untreated — that untreated absorption is the thing
  being priced.
- **prediction:** quality −0.005..+0.01 (expected near-flat; staleness-1 is
  the gentlest point on the curve). Throughput on this serial VM ≈ the
  install share only (+1–2% at best, stated honestly) — the entry's product
  is the price tag: if lag-1 is free, I-054's variable block lags and any
  future async kernel are licensed; if it is *not* free at this tiny
  staleness, F-010's staleness-discount family gains a measured foundation
  (F-010 *responds* to staleness by discounting counters; this entry
  *creates* a controlled dose of it — opposite sides of the same variable).
- **status:** queued

### I-058 · Shard counters with agreement merge: two half-batch evidence streams
- **source:** kernel-semantics lens — the data-parallel kernel form (two
  independent counter streams, one merge) applied to the trainer's state.
- **mechanism:** The batch splits into two halves of 16 windows. Each half
  keeps its **own counter pair** (cA, cB per component), updated by its own
  half's gated votes each step. A flip fires only when sign(cA) == sign(cB)
  for that component **and** |cA + cB| ≥ 32; on a flip both shard counters
  reset. State cost: counters double (2 B → 4 B per component-pair per
  weight, charged).
- **exact change:** new flag `--shards 2` on `Layered`.
- **semantic difference, plainly:** a flip needs *sustained agreement between
  two independent data halves*, not just a large total. Under today's single
  counter, one atypical half-batch (say, all numeric-dump windows) can push
  a counter most of the way to a flip in a few steps; here the other shard's
  counter refuses to corroborate and the flip cannot fire, however large
  the sum grows. Evidence becomes a two-witness rule.
- **gradient/vote path:** two half-batch backwards (or one backward with
  per-half gradient hooks — implementation choice, cost charged either way:
  gradient materialization ×2 for BitLinear weights). Votes, gate, and
  arbitration within each shard are the champion rule verbatim.
- **prediction:** flip rate falls (agreement is a stricter bar than the
  sum): expect flip share −30..−60% and quality −0.01..+0.04 at equal steps
  — the bet is that the flips removed are the batch-composition artefacts.
  Throughput −5..−15% (extra gradient handling). Distinct from F-018
  (3-of-4 *per-step sign* quorum over 4 sub-electorates, no persistent
  per-shard state — a weight can flip there on one step's majority; here
  each shard must independently accumulate ≥ ~16 net votes, a *temporal*
  two-witness rule).
- **status:** queued

### I-059 · Int8 body→head path: the head reads a quantized residual stream
- **source:** kernel-semantics lens — the head matmul (`body @ tok.weight.T`,
  FP, over a 192–512-dim body) is the one large matmul in the model whose
  *input* is never quantized; the kernels-attn stream's head bench exists
  because this path is a major cost share at ladder shapes.
- **mechanism:** The body output is quantized per token to int8 by absmax
  (the BitLinear activation quantizer, reused verbatim) before the head
  matmul; logits = int32(body_q @ W_tokᵀ) × (body_scale × 1) with W_tok the
  FP tied table cast to int8 codes per row with per-row scales — no: kept
  honest and simpler: body_q int8 × FP table via the C-C01-style integer
  path is impossible against an FP table, so the head runs
  `F.linear(body_q · body_scale, W_tok)` — the *input-side* quantization is
  the whole change; the table stays FP and AdamW-trained.
- **exact change:** new flag `--head int8body` in `Tiny.next_piece`
  (training and held eval both — it is the served function too, and is
  charged as such).
- **semantic difference, plainly:** the head stops distinguishing body
  vectors that differ by less than one activation quantum (top/254 per
  element): logit resolution is capped, and embedding rows receive gradients
  that are piecewise-constant in the body — two nearby hidden states that
  quantize identically produce *identical* embedding gradients. The output
  layer's effective input alphabet becomes finite (256 levels × dim), where
  today it is continuous.
- **gradient/vote path:** STE through the body quantization (identity
  backward), exactly as BitLinear treats its activations; the vote arms'
  counters are untouched structurally, but their final-layer evidence now
  arrives through the quantized head's backward — the entry is judged on
  the full model, not the head alone. Distinct from MILL-118 (quantizes the
  *table's storage* to INT8, body stays FP — the complementary operand) and
  WH-014 (table itself vote-trained ternary).
- **prediction:** logit error arithmetic: per-element body error ≤ top/254,
  RMS ≈ top/(254·√3); over dim 192 with table rows of norm ~√192·σ_w, logit
  RMS error ≈ 1–3% of typical logit spread — expect quality +0.00..+0.03.
  Throughput: the FP GEMM remains (only its input is pre-quantized), so
  ~0 claimed; the entry prices the *input* side so a future integer head
  kernel knows which operand's precision is free to cut.
- **status:** queued

### I-060 · Nibble-packed counters: c1 and c2 share one byte, V forced to 7
- **source:** kernel-semantics lens — the bit-packed counter update the
  territory names, with its semantic price stated instead of hidden: packing
  two int4 counters into one byte with saturating nibble arithmetic is the
  update a SIMD kernel can do in a single op, and it *cannot* represent
  V=32.
- **mechanism:** c1 and c2 are stored as the two nibbles of one uint8 per
  weight (offset-binary, range −7..+7 each). One packed add + nibble-mask
  saturation updates both counters per step; the flip test reads nibbles
  at |c| ≥ 7. Everything else (gate, vote, t1-priority, reset) unchanged.
- **exact change:** new flag `--pack nibble` on `Layered` (implies V=7;
  counter state 2 B → 1 B per weight).
- **semantic difference, plainly:** versus the champion this is **not** an
  implementation of the same trainer: the evidence horizon collapses from
  32 net votes to 7, so at equal drift a weight flips ~4.6× sooner, and the
  two components' counters now saturate independently at ±7 — long,
  slow-building evidence for a flip is *unrepresentable*, not just slower.
  Versus simply running int8 counters at V=8 (MILL-502's grid point), the
  difference is only the packing and V=7 vs 8 — stated plainly so the entry
  is judged as what it is: the V≈7 point *plus* a halved counter footprint,
  inseparable in this form.
- **gradient/vote path:** unchanged FP backward and vote computation; only
  the counter storage/arithmetic changes — this is the one entry whose vote
  path needs no wrapper, and the one whose adoption case rests entirely on
  the packed kernel existing (a torch probe measures the *semantics* of
  V=7-with-nibble-saturation; the speed belongs to a future native kernel
  and is claimed here only as state traffic: counter reads/writes halve,
  ≈ 1.8 MB/step saved at champion — under 1% of step traffic, honestly
  negligible at this scale, material at 50M where counters dominate).
- **prediction:** quality: read against MILL-502 (V=8) — expected within
  ±0.01 of it, i.e. likely worse than V=32 champion by whatever the V-grid
  says 8 costs; the probe is worth running only paired with MILL-502 so the
  packing itself is isolated. Ranked last: smallest semantic delta in the
  file, included because the territory names the mechanism and its honest
  price (V is not a free parameter once counters are packed) belongs on
  record before any kernel work assumes otherwise.
- **status:** queued

---

*Closing note on scope:* every entry above changes what the trainer computes —
a vote statistic, a gate scope, a forward function, an evidence stream, an install
schedule, a state representation. The exact kernel swaps (C-C01..C-C06) and the
literature kernel entries (B-025..B-030) remain the pool's speed lane and are
untouched by this file; several KT entries (I-050, I-052, I-055) are designed
to become *more* attractive, not less, if those benches ever land their missing
timing verdicts.

---

## Appendix — working-id mapping (miners -> wave I)

- NG-001 -> I-001
- NG-002 -> I-002
- NG-003 -> I-003
- NG-004 -> I-004
- NG-005 -> I-005
- NG-006 -> I-006
- NG-007 -> I-007
- NG-008 -> I-008
- NG-009 -> I-009
- NG-010 -> I-010
- NG-011 -> I-011
- NG-012 -> I-012
- CB-001 -> I-013
- CB-002 -> I-014
- CB-003 -> I-015
- CB-004 -> I-016
- CB-005 -> I-017
- CB-006 -> I-018
- CB-007 -> I-019
- CB-008 -> I-020
- CB-009 -> I-021
- CB-010 -> I-022
- CB-011 -> I-023
- CB-012 -> I-024
- LH-001 -> I-025
- LH-002 -> I-026
- LH-003 -> I-027
- LH-004 -> I-028
- LH-005 -> I-029
- LH-006 -> I-030
- LH-007 -> I-031
- LH-008 -> I-032
- LH-009 -> I-033
- LH-010 -> I-034
- LH-011 -> I-035
- LH-012 -> I-036
- DS-001 -> I-037
- DS-002 -> I-038
- DS-003 -> I-039
- DS-004 -> I-040
- DS-005 -> I-041
- DS-006 -> I-042
- DS-007 -> I-043
- DS-008 -> I-044
- DS-009 -> I-045
- DS-010 -> I-046
- DS-011 -> I-047
- DS-012 -> I-048
- KT-001 -> I-049
- KT-002 -> I-050
- KT-003 -> I-051
- KT-004 -> I-052
- KT-005 -> I-053
- KT-006 -> I-054
- KT-007 -> I-055
- KT-008 -> I-056
- KT-009 -> I-057
- KT-010 -> I-058
- KT-011 -> I-059
- KT-012 -> I-060
