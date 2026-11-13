# Muse's work — Muse's side

# Wave 4 · Lens 1 — NEGATIVE SPACE: the coverage map first, then what it leaves (Idea Engine, rotation 4, miner 1)

<!-- Muse's work — Muse's side of the BitNet lab. Nothing here is in the pool until
the pool's owner merges it — screen.py reads only mill/IDEA-POOL.md. IDEA-POOL.md
and CANDIDATES-A..H were read as one union (~11,470 lines) and NOT edited. -->

**Method.** This lens does not brainstorm. It first maps what the union
(IDEA-POOL.md + CANDIDATES-A/B/C/D/E/F/G/H) already varies, dimension by
dimension, and files entries only in the cells that survive verification.
Every gap below names the nearest pooled neighbours and the exact
sub-dimension they leave untouched. Where a suggested axis turned out to be
covered, it is listed as a **rejected gap** — filing it would have been a
duplicate dressed as a discovery.

**Champion reference (all predictions read against it):** layered_half +
rotary + plain votes, held **2.8580 ± 0.0161**, dim 192, 2 blocks, 4 heads,
ctx 256, vocab 4096, 884,736 ternary weights, V=32, median strong gate
(`|g| ≥ median|g|` per BitLinear layer, in `Layered.step`/`Direct.step`),
AdamW parts lr 1e-3, batch 32, ~160 steps at 8 min trial, 75 s probe.
Default corpus in train.py is v1 (`corpus.u16`); corpus-v2 exists on disk
(45.7% German / 41.9% HiveMIND docs / 12.4% lab notes, DATA-AUDIT §7) but
train.py has no `--corpus` flag yet — every v2 entry in the union is
process-mode for exactly that reason, and NG-002 inherits the dependency.

---

## The coverage map — verified gaps and rejected gaps

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
  merge context. → NG-001.
- **GAP-2 · Language share has never been a dose.** On v2, the union varies
  German's *placement* at fixed 45.7% share (G-019), the *period* at which
  sources alternate at fixed ratios (G-016), ratios *staged over time*
  (B-001), per-*file* balance (A-048 — changes language share only as an
  unmeasured side effect), a per-batch diversity floor (A-053), and one
  contaminated file's excision (E-021). No entry sweeps the static German
  share {0%, ~23%, 45.7%} at fixed total tokens with per-language held
  slices. The dose–response curve of the majority language does not exist.
  → NG-002.
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
  No entry sets gate-q by role. → NG-003 (scope), NG-004 (level).
- **GAP-4 · Quantiles are only ever a single threshold.** MILL-601..606
  move the one cut; F-028 servos that cut to hold admitted *mass*;
  A-005's deadband is a single multiple of the median (0.25×) with erosion
  below it. No entry uses *two* order statistics of the same |g|
  distribution as a band — counted above an upper quantile, eroded below
  a lower quantile, silent between. The interquartile band as the gate's
  shape is untested. → NG-005.
- **GAP-5 · Phase is varied lever-by-lever, never attributed.** The union
  has first-only levers (A-023 warmup, A-034 gate ease-in), last-only
  levers (A-022 tail freeze, A-036 collapse at 75%), halves (MILL-220..222
  hybrid phases, A-110 reset at 50%), thirds (A-045 ctx curriculum) and a
  cycle (A-033 cyclic V). No entry takes *one* lever and applies it in
  exactly one run-third per arm — first vs middle vs last — so no lever's
  effect has ever been located in time. The middle third in particular
  hosts no isolated intervention anywhere in the union. → NG-006.
- **GAP-6 · Position inside the window is weighted, never partitioned —
  and the FP loss is never touched.** F-013 reweights the *vote-path*
  gradient by log position (AdamW parts explicitly untouched); G-022
  shortens whole windows (late positions then appear only in long
  batches); G-017/G-018/G-023 change which positions text lands at.
  No entry (a) restricts a step's loss to one position *band* of a
  full-length window, or (b) removes any position band from the *shared*
  loss that trains the FP parts as well as the votes. → NG-007, NG-008.
- **GAP-7 · Time-between-flips enters only as age or count, never as
  trend.** F-025 uses a counter's stall *age* (time since sign change);
  A-008 uses flip *count* in a window (a rate); F-004 uses vote
  consistency since the last flip. No entry uses the *change* in a
  weight's inter-flip interval — acceleration — as a signal or a control
  input. A weight flipping every 40 steps and a weight whose intervals
  run 80 → 40 → 20 are indistinguishable to every pooled rule. → NG-009.
- **GAP-8 · Context length is monotone, random, or fixed — never cyclic.**
  A-045/046: monotone thirds (length confounded with phase, as G-022
  itself notes). G-022: stationary random mix (no order at all). A-089:
  fixed 512. No entry cycles ctx deterministically (64→128→256→128→…),
  the one design that is ordered like a curriculum but phase-balanced
  like a mixture. → NG-010.
- **GAP-9 · Held is sliced by source, never by target-token frequency.**
  Per-source slices exist (G-019, E-021). Token frequency appears only on
  the *training* side (tail-row V, TK-family embedding entries). No entry
  reports held binned by the target token's corpus frequency, so the lab
  does not know which frequency band its 2.8580 is made of — or which
  band any arm's Δ lives in. → NG-011.
- **GAP-10 · Held is sliced by position only inside one entry's arms.**
  G-018 logs per-position held loss as a diagnostic *for its own BOS
  comparison*. No standalone entry bins the standard held eval by
  position bucket for the champion family, so rotary's one confirmed win
  (−0.0411) has never been located inside the window it supposedly
  improves. → NG-012.

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

### NG-001 ★ · Init-seed × stream-seed factorial: unweld the seed and price its two halves
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
id: NG-001
mode: process
run: --arm layered_half --rope --init-seed 1 --stream-seed 0
```

### NG-002 ★ · German dose–response on v2: 0% / 23% / 45.7% at fixed tokens, per-language held
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
id: NG-002
mode: process
run: --arm layered_half --rope --corpus v2 --de-share 0.229
```

### NG-003 ★ · Per-projection gate: Q, K and V stop sharing one median inside the fused qkv
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
id: NG-003
mode: process
run: --arm layered_half --rope --gate-scope proj
```

### NG-004 · Role-split gate quantile: attention admits less, FFN admits more (with its reverse as control)
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
id: NG-004
mode: process
run: --arm layered_half --rope --gate-q-role 0.75,0.5
```

### NG-005 · IQR band gate: counted above Q3, eroded below Q1, silent between
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
id: NG-005
mode: process
run: --arm layered_half --rope --gate-band 0.25,0.75
```

### NG-006 · Phase attribution: one lever (V=16), three windows — first, middle, last
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
id: NG-006
mode: process
run: --arm layered_half --rope --v-window 0.33,0.66 --votes 16
```

### NG-007 · Rotating position-band loss: each step, one quarter of the window casts all the votes
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
id: NG-007
mode: process
run: --arm layered_half --rope --pos-band 64
```

### NG-008 · Drop the first 16 targets from the shared loss (both paths, hard cut)
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
  *for everyone, embeddings included* — if NG-008 wins and F-013
  doesn't (or vice versa), the lab learns which path the noise was
  hurting.
- **train.py:** new flag `--drop-early 16` in the training loop
  (slice targets/positions before the loss; no model change).
- **mode:** process
- **prediction:** −0.005..−0.015 pooled held, with the per-position
  held buckets (NG-012's instrument) showing positions 0–15 *worse*
  by +0.03..+0.08 (never trained) and positions 64+ better by
  −0.01..−0.02 (cleaner structure) — the pooled sign is the bet that
  the second effect outweighs the first at 16/256 of the window.
  At 32 dropped positions the bet is predicted to flip; 16 is the
  dose where the entry expects to win.
- **status:** queued
```mill
id: NG-008
mode: process
run: --arm layered_half --rope --drop-early 16
```

### NG-009 · Flip-acceleration tax: a weight whose flips are speeding up pays more for the next one
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
id: NG-009
mode: process
run: --arm layered_half --rope --flip-accel 1.5
```

### NG-010 · Cyclic context length: 64→128→256→128→64, one full cycle per run
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
id: NG-010
mode: process
run: --arm layered_half --rope --ctx-cycle
```

### NG-011 · Frequency-binned held: report what the 2.8580 is made of
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
id: NG-011
mode: process
run: --arm layered_half --rope --held-bins freq
```

### NG-012 · Position-binned held: locate rotary's win inside the window
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
  reporting mode as NG-011 (the two entries share one instrument
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
id: NG-012
mode: process
run: --arm layered_half --rope --held-bins pos
```

---

## Miner's ranking note

★★★ are NG-001/002/003. NG-001 is first because it is the only entry
whose result re-prices *every other verdict in the ledger*: until the
seed's two halves are priced separately, "seed variance" is an
unanalysed lump inside every ± in the lab. NG-002 is second because
45.7% of the clean corpus is one language and the lab has measured
everything about that fact except its amount. NG-003 is third because
it needs no new corpus, no new flag family — one grouped median where
the code currently takes one median over three jobs at once — and its
own diagnostic can void it for free. NG-011/NG-012 are ranked last as
entries but cost almost nothing (one shared eval instrument, zero
training) and should in practice be *run* first: they are the map
this lens would want before spending probes anywhere else.
