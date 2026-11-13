# Muse's work — Muse's side

# Wave 7 · Lens 4 (Portfolio Economics) — The Mill as an Investment Problem

<!-- Muse's work — Muse's side of the BitNet lab. Rotation-7 miner 4, portfolio-economics lens.
This is the economics layer ABOVE the existing lenses, not a repeat of them: K-037–K-048
(governance) decides what may enter and what retires; G-037–G-048 (methodology) decides how the
funnel runs; J-025–J-036 (fidelity) decides whether a probe reading can be trusted. None of them
prices the PORTFOLIO: what a pass is worth against a finite horizon, how correlated the 686
entries really are, how probe budget should be sized across families, what it costs if the
champion is wrong, and when the whole program should stop buying breadth and buy depth instead.
Every entry below is a mill-policy mechanism stated as an exact rule change with its arithmetic
shown on filed numbers. Filed constants used throughout: pool = 686 entries (K-040/K-048);
probe = 75 s; trial = 24 min (3 seeds × 8 min) = 19.2 probe-equivalents; champion 2.8580 ± 0.0161;
adoption bar = beat by > max(2 sd, 0.01) = 0.0322 plus the ≥2-of-3 per-seed guard; probe bar
Δ ≥ 0.05 promote / 0.02–0.05 near; pass = 45 min wall, ~30–35 probes delivered (G-042);
the mill runs until 2026-11-15 (PROMOTE.md) and is preempted entire by the ladder and the
growth cycles. -->

## The three numbers the current queue never quotes

1. **A full pass now costs 14.3 h, not 7.7 h.** PRIORITIES.md's 7.7 h was priced at 368 entries.
   At 686 entries: 686 × 75 s = 51,450 s ≈ **14.3 h of probing per pass, per generation** —
   before one trial. The pool grew 86% since the price was last quoted; the queue still
   behaves as if a pass were cheap.
2. **The mill has ~51 h of life left.** From 2026-11-12 ~21:00 PT to the 2026-11-15 stop in
   PROMOTE.md is ~51 wall-hours, minus total preemption by the scale ladder and growth cycles.
   At ~35 probes per 45-min pass, the remaining life buys **at most ~3 full pool passes** —
   and one champion adoption's re-screen (CN-009) consumes one of them. Breadth is nearly
   exhausted as a strategy whether anyone votes for depth or not.
3. **The 686 entries are not 686 bets.** K-039's readout cluster is 12 entries carrying ~1
   independent verdict (16 with its F/I/MILL echoes); K-037 counts ~30 dose families whose
   members win or die together; K-038/K-048 name ~8 hub premises (F-043 with ~9 dependents,
   WH-014 with 4+, and the six pool-scope premises J-037/038/042/043/044/045) on which whole
   subtrees are jointly levered. Priced honestly, the pool is a few hundred correlated
   positions concentrated on a handful of premises — and it is allocated as if it were 686
   independent coin flips in pool order.

---

### CN-001 ★ · Horizon-denominated budgeting: every queue decision is priced against 2026-11-15, not against an infinite future

- **Economic principle:** A portfolio with a known liquidation date is managed backward from
  the date. An asset (probe, trial, re-screen) whose payoff lands after the horizon is worth
  zero no matter how good its expected value is in the abstract; an asset bought early in the
  life compounds (its verdict reprices everything after it), the same asset bought late does not.
- **Mill rule (exact):** `screen.py` maintains a **horizon ledger**: remaining wall budget
  `H = deadline − now − reserved_preemption`, recomputed each pass from the trailing passes'
  delivered probe throughput (not nominal). Every queued action is ledgered with
  `cost ÷ H`. Two hard switches: when `H < 28.6 h` (two full re-screens), the mill enters
  **conversion mode** — no new wave merges, no full-pass re-screens; budget goes to trials of
  already-promoted entries, near-band resolution (CN-006) and premise audits (CN-005). When
  `H < 1 h`, **liquidation mode** (CN-012) — no new probes at all.
- **Arithmetic:** H today ≈ 51 h. One full pass = 14.3 h = **28% of remaining life**. The
  top-40 first pass in PRIORITIES.md costs < 3 h ≈ 6% — correctly sized. But the standing
  default (probe the pool in order, re-open everything on adoption, merge the next wave when
  it files) silently commits ~14.3 h per pass and ~14.3 h per generation with no point at
  which anyone asks whether the remaining life can pay for the *consequences* of the spend.
  Under conversion mode at H < 28.6 h, the same hours buy ~85 near-band extensions and gated
  trials (CN-006) instead of a third correlated re-read of entries already verdicted twice.
- **What it replaces:** The implicit infinite-horizon assumption in PROMOTE.md's funnel
  ("the whole pool re-opens under the new generation", passes repeat until stopped) and
  G-045's within-pass partition, which budgets 45 minutes at a time and never the program's life.
- **Risk:** The 2026-11-15 stop is a config line, not a law of nature — if the mill's run is
  extended, conversion mode triggers early and costs some breadth. The mode is a ledgered,
  reversible switch (H is recomputed, not latched), so an extension un-triggers it next pass.

### CN-002 ★ · Kelly sizing across families: probe budget is allocated by edge ÷ variance, never by headcount

- **Economic principle:** Kelly sizing: the fraction of capital staked on a bet scales with its
  edge and inversely with its variance — and *correlated bets count as one bet for sizing*.
  A family with 54 entries and one shared premise has the information content of its premise
  count, not its entry count; staking 54 slots on it is over-betting a single idea 54 times.
- **Mill rule (exact):** Each pass, probe slots are allocated across mechanism families by
  **fractional Kelly on filed numbers**: family stake ∝ (filed mean Δ of the family's
  unprobed entries × family's historical promote rate) ÷ (family's filed Δ spread), computed
  from the ledger + candidate files by the census (K-040's tags supply the families), with
  two clamps: no family exceeds **25% of a pass's probes**, and every family with unprobed
  entries keeps a **floor of 1 probe per pass** (the anti-starvation floor G-042's 20%
  exploration slice gestures at, here priced per family instead of globally). Dose families
  remain capped by K-037's one-slot rule *inside* their Kelly stake.
- **Arithmetic:** The counter-centric sleeve is ~54 entries ≈ 17% of all candidates (K-040)
  orbiting one int8 field and effectively a handful of premises (counter ownership, clamp,
  reset — the premises J-002/J-037 audit). At pool-order/natural share it draws ~6 of a
  35-probe pass, every pass, every generation: 6 × 75 s × ~20 passes ≈ **2.5 h of the
  remaining 51 h staked on one unaudited premise cluster**. Kelly on filed spreads (counter
  entries file Δ from −0.06 to +0.02 with several predicted-flat members — high variance,
  modest mean) sizes the sleeve nearer 3 probes/pass until J-002/J-037 land, freeing ~1.2 h
  for families whose filed mean/spread ratio is better (readouts: several file −0.02..−0.08
  at eval-only cost; data-order: G-014 class files −0.01..−0.05 with a mechanism, not a dial).
- **What it replaces:** Pool order as the allocation policy (G-042's diagnosis) and K-041's
  filing-side family budget — K-041 limits what a wave may *file*; nothing until now limits
  what a pass may *spend* per family in proportion to filed value. G-042's surrogate ranks
  entries; CN-002 sizes the family stakes the surrogate then ranks within.
- **Risk:** Filed Δ midpoints are miners' estimates, and Kelly on bad estimates over-bets
  confident families. Mitigations are the 25% cap, the per-family floor, and re-fitting the
  promote-rate term from the ledger each generation (estimates decay, ledger rates don't).

### CN-003 ★ · The correlation haircut: plan, report and cap against effective N, not entry count

- **Economic principle:** Portfolio variance is set by correlations, not positions. Twelve
  readouts of the same checkpoints are one bet with twelve ledger lines; nine entries gated
  on F-043 are one levered bet on the V-scaling law. Reporting "686 entries screened" overstates
  diversification by the correlation factor and hides where the portfolio actually dies.
- **Mill rule (exact):** (a) `mill/CENSUS.md` reports **N_eff** beside N: each K-039 cluster
  counts as 1 + 0.1 per extra member, each K-037 dose family likewise, each K-038 premise
  subtree is listed with its dependent count. (b) **Hub concentration cap:** no single hub
  premise (F-043, WH-014, the six K-048 pool-scope premises) may carry more than **30% of a
  pass's probe budget** in dependents until that premise's own verdict has landed — dependents
  beyond the cap are ledgered `hub_capped` and deferred one pass, not killed. (c) Every pass
  report states the portfolio's largest single-premise exposure in mill-hours.
- **Arithmetic:** Readout cluster: 12 probes × 75 s = 15 min buys, at the transforms' filed
  overlap, ≈ 1 independent verdict + 11 echoes — the marginal information of the k-th
  correlated probe at ρ ≈ 0.9 is ~1/(1 + 0.9(k−1)): the 12th probe is worth ~9% of a fresh
  bet but is charged at 100%. F-043's subtree: ~9 dependents ≈ 11 min/pass of probing plus
  up to three 24-min 50M trials (K-038) — **~1.4 h of exposure riding on one 75-second sweep
  (F-043 itself, PRIORITIES #5) that hasn't run yet**. The hub cap sequences the cheap hub
  verdict ahead of its levered dependents instead of letting pool order spend the leverage first.
- **What it replaces:** The unit-of-account error shared by PRIORITIES.md (entries ranked as
  independent line items), K-039 (clustering as a *queue-slot* saving — CN-003 keeps the
  cluster but prices it as one bet for *risk* purposes too) and K-048 (hub premises flagged
  for re-pricing after they fall — CN-003 caps exposure *before* they fall).
- **Risk:** ρ is estimated from filed overlap, not measured; a cluster whose members are less
  correlated than filed (G-025 vs G-026's known interaction) is under-bought for a pass.
  The cap defers, never retires, and any member can be split out by name — the same escape
  K-039 already files.

### CN-004 · Certain-information pairs are priced on avoided waste, not on their own Δ (the I-016 rule)

- **Economic principle:** A test that pays in *both* branches is not a bet, it's an arbitrage:
  its value is the expected waste it deletes, which can exceed any single arm's Δ. I-016
  (F-003 × F-006) is filed as "the cheapest certain information" in wave I — one of two filed
  premises *must* lose, so the mill learns a structural fact with probability 1. The queue
  currently prices it as an ordinary combination with a predicted *negative* interaction
  (−0.00..−0.02 combined) — i.e., near the bottom by Δ, at the top by information.
- **Mill rule (exact):** Any entry whose kill criterion fires a premise verdict in both
  outcomes (both-branches-informative, declared in its `mill` block as `info_class: pair_kill`)
  is ranked by **avoided-waste value** = (cost of trialling/probing the losing premise's
  dependents as filed) instead of predicted Δ, and is scheduled in the same pass as — never
  after — the dependents it adjudicates. K-044's quarantine is amended: pair-kill combinations
  are *exempt* from the both-parents-probed rule when the parents' solo probes are scheduled
  in the same pass, because the pair's 2×2 *is* the parents' cheapest joint reading.
- **Arithmetic:** I-016's full 2×2 = pair probe + the two parents' probes = 3 × 75 s = **225 s**
  to kill one of two premises with certainty. The alternative path — letting F-003's and
  F-006's families each earn trials on their own predictions — costs 2 × 24 min = 48 min of
  trials plus their dependents' probes before the same fact surfaces, a **~13× price ratio**
  for identical information. Generalised: the pool files ~12 combination pairs (I-013–024);
  the subset whose filed 2×2s are premise-adjudicating (I-016, I-017, I-018, I-021, I-024 by
  their own interaction hypotheses) is worth ≈ 5 × 225 s ≈ 19 min to resolve five premise
  disputes that currently sit underneath dozens of dependent entries.
- **What it replaces:** Δ-only ranking for combinations (PRIORITIES.md admitted exactly one
  combination, I-015, on Δ grounds and deferred the rest as "unattributable" — true for
  Δ-chasing pairs, false for pair-kills, whose deliverable is the attribution itself).
- **Risk:** A pair whose interaction hypothesis is wrong in a third way (both premises survive,
  the *combination* was broken) yields a muddy read. The filed kill criteria are the guard:
  I-016's criterion names the diagnostic (post-canon c2 regrowth) that separates the branches,
  and pair-kill status requires that named diagnostic at filing time.

### CN-005 · Gen-0 lock-in insurance: cap the cost of the champion being wrong before generation 2, not after

- **Economic principle:** Every verdict in the ledger is denominated in one asset: champion
  2.8580 on corpus v1 — a currency the data audit already proved is flattered by duplicate
  leakage of unknown size (E-018), with J-042 filed to measure the leak and J-041 to audit
  whether gen-0 is even the right chassis. If the currency is debased, the loss is not one
  entry's Δ; it is the *entire ledger*, and it grows with every pass issued in the bad currency.
  Insurance is bought when the premium is small against the insured sum — i.e., now, while the
  ledger is young.
- **Mill rule (exact):** Before any generation-2 adoption may install, the mill must hold
  landed verdicts on the two currency audits: **E-018** (corpus-v2 re-baseline, 1 trial,
  24 min) and **J-042's excised arm** (leak-removed champion run, 24 min; the dosed calibration
  arm may follow). Premium cap: if both audits together exceed **4% of H** they are still
  bought — the cap instead binds the *consequence*: a champion installed without them is
  ledgered `uninsured`, and its generation's verdicts are stamped as re-measurable at the
  audits' landing (K-048's re-stamp, given a deadline instead of an intention).
- **Arithmetic:** Premium = 48 min ≈ **1.6% of the remaining ~51 h**. Insured sum: every
  verdict the mill will ever issue under gen-0/gen-1 references — at ~14.3 h per full pass
  and ~3 passes of remaining life, ≈ **43 h of probing plus all trials** are denominated in
  the v1 number. K-048 prices a late leak discovery as "potentially tens of mill-hours of
  verdicts" written off; CN-005 simply notes the premium-to-cover ratio is roughly **1:50**
  and that no other purchase in the pool offers it. Sequencing note: E-018 already sits at
  PRIORITIES #9 — CN-005 promotes the pair to a *gate on generation 2*, which is where the
  lock-in actually compounds (gen-1 verdicts re-judged under a gen-2 reference inherit the
  debasement twice).
- **What it replaces:** PRIORITIES.md's treatment of E-018 as one expensive line item among
  40 ("expensive, indivisible, and worth more than any ten arms" — agreed, and therefore it
  should be a gate, not a rank) and K-048's flag-and-restamp with no purchase attached.
- **Risk:** The audits may land clean (leak small, champion honest) — then 48 min bought
  certainty, which is what insurance is. The real risk is the gate delaying a gen-2 install
  by ≤ 48 min of trial time; bounded, and stated on the ledger line.

### CN-006 · The program stopping rule: depth converts at ~2× breadth's rate — exhaust the near band before any new wave is bought

- **Economic principle:** A research program should stop expanding its idea inventory when the
  marginal hour earns more resolving old inventory than screening new. The mill currently does
  the opposite by default: `near` verdicts (0.02 ≤ Δ < 0.05) are "recorded, no trial — a human
  may re-probe" (PROMOTE.md), i.e. the highest-posterior inventory in the building is parked
  for a human who may never come, while fresh waves of ~5%-base-rate ideas keep arriving.
- **Mill rule (exact):** **No new wave merges while the un-resolved upper-near inventory
  (Δ ∈ [0.035, 0.05)) exceeds 8 entries**, and each pass must spend its first probe budget on
  G-044 extensions until the upper-near count is < 8 or the pass's extension cap (4 × 3 min)
  is hit. Program-level stop: when the best remaining unprobed entry's surrogate/family-prior
  expected Δ (CN-002's inputs) falls below the trial noise floor (0.0161), new screening stops
  entirely and H is spent on trials, confirmations and audits only.
- **Arithmetic:** G-044's filed numbers: ~20 upper-near per generation, 3-min extensions,
  ~25% promote → **5 trial candidates per 60 min of extensions ≈ one candidate per 12 min**.
  Fresh breadth: G-042's ~5% promoter base rate at 75 s/probe = 48 probes/h × 5% ≈ **2.4
  promoters per hour ≈ one per 25 min** — and each fresh promoter still owes a second-seed
  gate (G-039) and carries full false-positive risk, while an extended near has already
  survived one screen. Depth therefore converts at roughly **2× breadth's rate per mill-hour**,
  before counting that wave-7/8 filing also costs miner and merge-review time the mill never
  ledgers. A wave that files 60 new entries (wave-5/6 rate) commits 60 × 75 s = 75 min of
  probes to earn ~3 promoters; the same 75 min in extensions resolves the entire upper-near
  band ~1.25× over.
- **What it replaces:** G-044 as an optional coordinator step (it becomes the pass's first
  obligation, with a merge-blocking inventory threshold), and the Idea Engine's standing
  assumption that the next wave is always the next purchase.
- **Risk:** Near-band effects are the ones most exposed to horizon bias (a 3-min extension is
  still not the 8-min trial format — G-044's own caveat). The extension can only queue trials,
  never adopt, so the failure mode costs 24 min, and the extension promote rate is ledgered
  separately so the 25% assumption is itself re-priced after one generation.

### CN-007 · The wild-card mandate: a fixed 15% longshot sleeve, because wild cards are the portfolio's only negatively-correlated asset

- **Economic principle:** Diversification is bought where payoffs are *negatively* correlated
  with the core book. The grid's 686 entries nearly all pay in the same world — the world
  where the F–J premises hold. The wild cards (F-055..066, DW-001..012, the WC lens) are filed
  as explicit premise bets: each pays *precisely in the world where a consensus premise is
  false* (DW's premise map: 12 entries shorting ~6 shared F–J premises). A sleeve that pays
  when the core book's premises die is worth more than its standalone hit rate — it is the
  hedge, and hedges are sized by mandate, not by expected value contests they will always lose.
- **Mill rule (exact):** **15% of every pass's probe slots (≈ 5 of 35) are reserved for
  wild-card / premise-inversion entries**, drawn in filed kill-test-cheapness order, exempt
  from CN-002's Kelly sizing and from any surrogate ranking (G-042) — a surrogate trained on
  the ledger of the consensus world will systematically price the hedge at zero, which is the
  failure the mandate exists to prevent. The sleeve's hit rate is reported per wave against
  its filed expectation (below) so the mandate itself is re-priced on evidence.
- **Arithmetic:** Cost: 5 × 75 s ≈ 6.3 min per pass ≈ **2.1 h across the remaining ~20 passes**
  (≈ 4% of H) for complete coverage of all ~36 filed wild cards, most twice over across
  generations. Filed expectations: the grid's own base rate is ~5% promoters (G-042) with
  payoffs of one arm's Δ (filed midpoints mostly −0.02..−0.05). The wild cards file no
  hit-rate — itself a gap CN-007's reporting fixes — but their payoff unit is different: a
  single wild hit that kills a hub premise reprices every dependent (F-043's subtree alone is
  ~9 entries + up to 3 trials ≈ 1.4 h of avoided or redirected spend, CN-003), and F-055 (the
  reservoir control, PRIORITIES #10) prices *the whole program's effect size* — the one
  number every votes-vs-STE claim in the record silently assumes. At even a 1-in-12 hit rate
  per wave (below the grid's per-entry rate, against filed payoff multiples of 10–50× a
  normal arm's), the sleeve's expected value per probe exceeds a median grid probe's.
- **What it replaces:** The current allocation, in which wild cards compete slot-for-slot with
  grid entries on predicted Δ and predictably starve (F-065 was retired on sight in
  PRIORITIES.md for lacking an interpretable win — the correct call for *that* entry, and the
  reason the mandate requires a filed kill test as the sleeve's entry ticket, exactly as
  DW-003/F-061 carry one).
- **Risk:** A mandate spends on schedule regardless of quality drift in later wild waves.
  Guard: the ticket is a filed one-probe kill test (entries without one, F-065-class, are
  ineligible), and the per-wave hit-rate report gives the pool owner the number needed to
  cut the mandate to 10% or raise it to 20% on evidence rather than taste.

### CN-008 · Trial-exposure cap: the trial queue is a capped line item, because false trials are the portfolio's largest single leak

- **Economic principle:** Probes are cheap options; trials are exercised options at 19.2× the
  price. A screen run over hundreds of nulls at a ~2σ bar manufactures false exercises by
  arithmetic, not by anyone's error (J-035's winner's curse, at portfolio scale). What is
  missing is not a better gate — G-039 files one — it is a *budget*: a maximum share of the
  portfolio that may be exercised through the noisy band per generation.
- **Mill rule (exact):** Per generation, trials whose promoting probe Δ < 0.10 (the noise
  band, G-039's own split) are capped at **8 trials = 3.2 h**; Δ ≥ 0.10 promoters are
  uncapped. Band entries beyond the cap wait, ledgered `trial_capped`, in Δ order — they are
  the first claim on the *next* generation's cap. Confirmation runs, stale-reference controls
  and futility-stopped seeds all draw against a separate, visible **verdict-overhead line**
  capped at 20% of H per generation (G-045 showed verdict work can silently eat a whole pass;
  CN-008 makes the eating a budget with a number).
- **Arithmetic:** G-039 files 8–15 false trials per generation at ~380 screened entries
  (3–6 solo hours). Scale to the current pool: 686 nulls at a one-sided ~2.5% false-promote
  rate ≈ **17 false trials ≈ 6.8 h ≈ 13% of remaining life**, spent exercising options on
  noise. The cap bounds band-trial spend at 3.2 h/generation and forces the marginal band
  entry to compete against the band's own best (Δ order) instead of against the clock. Each
  futility stop (G-037) and second-seed gate (G-039) that lands *raises* the cap's real value;
  the cap is the backstop for the generations where they don't.
- **What it replaces:** PROMOTE.md's uncapped inline trial queueing ("a full trial is queued
  inline the moment a probe promotes") — queueing is free in the current rules and 24 min in
  reality.
- **Risk:** A genuine small effect (true Δ ≈ 0.06) waits a generation behind noise that
  out-ranked it on a lucky probe. Accepted deliberately: it is delayed, not killed, and the
  alternative — uncapped exercise — is the filed 6.8 h leak.

### CN-009 · The generation tax: an adoption is priced at trial + re-screen liability, and small-gain adoptions must buy triage with the install

- **Economic principle:** Switching the portfolio's benchmark is a transaction with a large
  fixed cost: adoption re-opens the whole pool under the new generation. A champion that gains
  0.033 (the minimum adoptable) and triggers a 14.3 h re-measurement has spent the mill's
  scarcest asset to bank a gain inside two seed-sds of the noise it was measured against.
  The adoption bar in PROMOTE.md prices the trial; nothing prices the switch.
- **Mill rule (exact):** Every adoption ledger line carries `switch_cost` = the re-screen it
  triggers, computed at install time (pool size × 75 s, triage-adjusted). **Adoptions with
  gain < 0.05 install only with G-041 triage attached** (entries that lost to the old champion
  by more than gain + 0.10 are deferred_by_triage with the 10% audit sample); adoptions with
  gain ≥ 0.05 may re-open the pool fully. The 0.05 threshold is the probe bar's own number:
  a gain smaller than the screen's resolution does not earn an un-triaged re-screen.
- **Arithmetic:** At 686 entries the full re-screen is 14.3 h; G-041's triage at its filed
  ~50% deferral rate cuts it to ~7.2 h + ~24 min audit ≈ **7.6 h, saving ~6.7 h per small-gain
  generation** — roughly 13% of remaining life, per adoption. Cost per nat banked makes the
  point bluntly: a minimum-gain adoption (0.0322) at full re-screen spends 14.3 h / 0.0322 ≈
  **444 mill-hours per nat**; the same adoption triaged spends ~236; a 0.05-gain adoption
  spends ~286 untriaged. Small-gain churn is the most expensive habit available to the mill,
  and it is currently free.
- **What it replaces:** PROMOTE.md's adoption section, which re-opens the pool unconditionally,
  and G-041 as a standalone proposal (CN-009 makes triage the *price of installing a small
  gain*, so it lands exactly when its saving is realised, instead of competing for a
  mill-change slot under K-045's budget).
- **Risk:** Triage's known failure is non-additivity (an entry that lost to champion g can
  beat g+1 through interaction). G-041's guards carry over unchanged: the wide margin
  (gain + 0.10), the 10% audit sample, and human-named entries always full-probed.

### CN-010 · One-premise concentration limit: no unaudited premise may carry more than a fifth of a pass

- **Economic principle:** This is CN-003's cap applied at the mechanism level, where the
  correlation is physical, not statistical: ~54 entries orbit a single int8 counter field
  (K-040). If J-002's rival wins (counter *statistics*, not per-weight memory, do the work) or
  J-037's audit cuts the "≈97% of STE at ~1/10 state" claim, that sleeve's filed predictions
  do not degrade independently — they were all the same prediction wearing different dials.
- **Mill rule (exact):** Until a mechanism family's hub audit has landed, that family is
  capped at **20% of a pass's probes**; the audit itself (for the counter family: J-002 at
  one 75 s probe, J-037 as a readout on existing runs) is scheduled *before* the family's
  next pass allocation, as a pass's first probe. After the audit lands `survives`, the cap
  lifts; after `falls`, CN-003's/K-038's cascade prices the write-down.
- **Arithmetic:** The counter sleeve at natural share draws ~6 probes/pass (CN-002). The
  audit that de-risks it costs **75 s once**. Every pass run *before* the audit stakes
  6 × 75 s = 7.5 min on an unexamined premise; across the ~20 remaining passes that is 2.5 h
  of levered exposure versus a 75-second hedge — a 120:1 ratio of exposure to insurance,
  worse than CN-005's because this audit is probe-priced, not trial-priced. The same rule
  applied to the rotary premise (J-038: every one of the 686 entries runs `--rope`) and the
  held-cleanliness premise (J-042) is what CN-005 buys at trial price for the two that need it.
- **What it replaces:** K-048's post-hoc re-pricing (necessary, but it pays out after the
  loss) and the pool's habit of treating premise audits as ordinary candidates competing for
  slots (J-037–048 filed inside a 48-entry wave, ranked by the same Δ logic as arms — an
  audit's value is the exposure it removes, which no Δ ranking can see).
- **Risk:** The cap could slow a family that is genuinely the frontier (the counter family
  produced the champion). The audit-first sequencing bounds the delay to one probe; the cap
  binds only until that probe reads.

### CN-011 · Full-trial-only entries pay in probe-equivalents and must name what they displace

- **Economic principle:** Opportunity cost is only real if it is itemised. A full-trial-only
  entry (no honest probe exists; first reading costs 24 min) consumes 19.2 probe slots of the
  scarcest, solo-only, coordinator-only time in the lab — and under preemption (ladder, growth
  cycles) it consumes them from a pass that may deliver only ~35 probes total. Priced in
  minutes it looks like a line item; priced in displaced probes it is half a pass.
- **Mill rule (exact):** A full-trial-only entry may queue only with a filed
  `displaces:` note naming, from the current queue order, the ~19 probes its 24 min removes,
  and full-trial-only spend is capped at **10% of H per generation** (≈ 5 h now, ≈ 12 trials —
  the cap binds the tail, not the head). Within the cap, full-trial-only entries run after
  the pass's probe-able queue, never before (they are the least interruptible spend in a
  preemptible mill).
- **Arithmetic:** The top-40's three full-trial-only entries (E-018, G-049, G-050) cost
  3 × 24 min = 72 min ≈ 58 probe-equivalents — defensible, and CN-011 says so on their ledger
  lines instead of letting them hide inside a "< 3 h total" summary. The tail is the problem:
  I-039 files 121 evaluation points, I-037 97 EP, G-052 pays 3× full price for a question
  G-049 answers at champion bytes — unpriced, these queue by filing order and each silently
  deletes ~19 probes (≈ one expected promoter at the 5% base rate: 19 × 5% ≈ 0.95) from the
  generation that hosts them. The rule's test is simple: an entry that cannot name a prize
  worth ~1 forgone promoter does not get 24 solo minutes.
- **What it replaces:** PRIORITIES.md's cost-class label `full-trial-only` as a passive
  descriptor (the class exists; its price was never charged) and the deferral-by-fiat of
  I-037/I-039/G-052 — CN-011 gives them a priced route back in instead of a verdict-shaped hole.
- **Risk:** `displaces:` names a moving queue; the note is a snapshot at queue time and is
  ledgered as such. The cap's 10% is a policy dial — stated, visible, and adjustable by the
  pool owner, which is the improvement over today's implicit cap of "however many file".

### CN-012 · Liquidation schedule: backward-plan the last day so no verdict is bought that can never be spent

- **Economic principle:** At a hard horizon, asset maturities must ladder to the date. A probe
  fired in the final hour buys a promotion whose trial cannot run; a trial started in the
  final hours may never be judged; an adopted champion that never confirms is a liability
  dressed as a result (PROMOTE.md freezes an unconfirmed champion's reference — an unjudged
  expiry leaves the *next* operator holding a frozen or unverified book).
- **Mill rule (exact):** Backward from the 2026-11-15 stop: **T-24 h** — no new full-trial-only
  queues (CN-011's class matures too slowly); **T-8 h** — no new first probes of entries with
  no probe record (a fresh probe → gate → trial → confirmation chain cannot complete:
  75 s + 2.5 min gate + 24 min trial + 16 min two-sided confirmation + job-zero re-measure
  ≈ 45–60 min minimum, and the chain must also survive preemption); **T-2 h** — probes stop;
  remaining time is reserved for judging completed trials, running pending confirmations, and
  closing the ledger with a final census + premise-exposure statement (CN-003c). Any trial
  incomplete at T-0 is ledgered `expired_unjudged` with its seeds' partial record — never
  silently dropped, never judged on a partial trio.
- **Arithmetic:** The minimum spendable chain is ~45–60 min; every probe fired inside the last
  hour therefore has an expected spendable value of ~0 while costing the same 75 s as a probe
  fired today that can compound through ~3 generations. Symmetrically, one unjudged trial at
  expiry wastes 24 min = 19.2 probes ≈ **0.8% of remaining life per occurrence** — and
  PROMOTE.md's reporting rule (surface adoptions early) means an unconfirmed last-minute
  adoption is the single most misleading artefact the mill could leave behind.
- **What it replaces:** `run-forever.sh`'s flat stop (run until the date, then halt wherever
  the queue happens to be) — the current design has a deadline and no maturity structure
  in front of it.
- **Risk:** If the run is extended past 2026-11-15, the T-minus schedule idles some late
  capacity. The schedule keys off the configured deadline each pass (like CN-001's H), so an
  extension moves the whole ladder; the cost of a false alarm is a few hours of shallower
  late work, against the cost of the alternative being an unjudged book.

---

## The current queue's biggest mispricing (summary for the pool owner)

The queue prices everything in **probes (75 s)** while the portfolio's real prices are in
**generations (14.3 h per re-screen)** and **horizon (51 h left, hard stop 2026-11-15)**.
Three consequences, in order of size:

1. **Breadth is bought at depth's price and depth is left unbought.** Fresh screening converts
   at ~2.4 promoters/hour (G-042's 5% base rate); the parked upper-near band converts at
   ~5 trial candidates/hour (G-044's filed numbers) — yet PROMOTE.md parks the near band for
   a human and the waves keep filing. CN-006.
2. **Correlation is unpriced.** 686 entries are ~a few hundred effective bets levered on ~8
   hub premises; the F-043 subtree alone carries ~1.4 h of exposure behind one unrun 75 s
   sweep, and ~17% of all candidates ride one counter premise whose audit costs one probe.
   CN-003, CN-010.
3. **The currency is uninsured.** ~43 h of remaining verdicts will be denominated in a v1
   champion number with a filed, unmeasured leak; the insurance costs 48 min (1.6% of H,
   ~1:50 cover). CN-005.

*End of wave-7 lens-4 portfolio economics. 12 entries (CN-001–CN-012); ★ = CN-001
(horizon-denominated budgeting), CN-002 (Kelly sizing across families), CN-003 (correlation
haircut / effective N / hub cap). Nothing here edits the pool, PROMOTE.md or screen.py —
adoption of any rule is the pool owner's call, executed as each entry specifies.*
