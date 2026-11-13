# Muse's work — Muse's side

# Wave 6 · Lens 4 — POOL GOVERNANCE: governing the 700+-entry pool's structure (Idea Engine, rotation 6, miner 4)

<!-- Muse's work — Muse's side of the BitNet lab. Nothing here merges, edits or retires
anything — screen.py reads only mill/IDEA-POOL.md, and PRIORITIES.md already ranked the top 40.
This file governs the REST: the ~640 entries below the top 40, and the structure they form.
Counts below were taken directly from the files on 2026-11-12. -->

**The pool as counted.** IDEA-POOL.md: 368 entries (MILL-000 + MILL-1xx–19xx families).
Unmerged candidates: CANDIDATES-F 66 + G 72 + H/WH 72 + I 60 + J 48 = **318**, for a union of
**~686 entries** before CANDIDATES-A–E stragglers are even counted — i.e. the 700+ pool of the
brief. PRIORITIES.md prices the consequence: one full pass at 368 entries ≈ 7.7 h; probing the
270 F–I newcomers alone ≈ 5.6 h/pass/generation, before a single 24-min trial. The pool's problem
is no longer idea supply. It is that the pool has **no family budgets, no deduplication, no
retirement, no premise tracking, and a coverage map one wave stale** — five missing organs, all
structural, all cheap to build relative to the probe-hours they save every generation, forever.

**The grid that created the problem (verified).** Waves G, H and I are not organic piles; they
are exact 12-per-lens grids — G: 6 lenses × 12 (G-001–012 FP-parts · 013–024 data-order ·
025–036 readout · 037–048 mill-economy · 049–060 composition · 061–072 funnel-2), H/WH: 6 × 12
(001–012 shapes · 013–024 vocab/embedding · 025–036 auxiliary · 037–048 robustness · 049–060
counter-forensics · 061–072 hive-2), I: 5 × 12 (001–012 verified gaps · 013–024 combinations ·
025–036 long-horizon · 037–048 discrete search · 049–060 kernel semantics). Every lens got 12
slots whether its family deserved 12 or 2. Uniform quota, not expected value, set the pool's
shape. Most entries below are repairs to that one fact.

★ = top 3.

---

### GV-001 ★ · Family budget: one slot per dose family per pass, siblings earn entry on signal
- **Structural problem:** Dose-stacking is the pool's default waste. PRIORITIES.md already had
  to hand-pick one point per family (WH-013 over dose siblings WH-020/WH-022; I-038 at 21 EP
  over I-037 at 97 EP and I-039 at 121 EP; G-066 sequential dosing praised precisely because it
  is the exception). Unbudgeted families in the files: vocab dial WH-013/020/022 (3 runs for one
  direction), leak MILL-209/210/211 + integer-leak MILL-212/213 (5), thrash-freeze
  MILL-215/216/217 (3), magnitude-calibrated MILL-201/202/203 (3), V-schedule MILL-204/205/206
  (3), modal readout MILL-218/219 (2), Fisher-flip share MILL-228/229/230 (3). At 75 s/probe a
  dead 3-dose family burns 3 probes to learn one fact; across ~30 dose families in the union
  that is roughly a full probe-pass of rent per generation.
- **Governance mechanism:** A per-pass **family budget**: each named dose family gets exactly
  **1 probe slot per pass** (its central/filed-best dose); a sibling unlocks only when the
  representative lands `promote` or `near` (Δ ≥ 0.02) — the G-066 rule, made pool law instead of
  one entry's private virtue. Families are identified by a `family:` tag (see GV-004), not by
  judgement at merge time.
- **Exact change:** Add `family:` + `dose:` fields to the fenced `mill` block schema in
  IDEA-POOL.md; add a pass-planner step in `mill/screen.py` that groups queued entries by
  `family:` and admits only the family's designated representative until its ledger verdict is
  `promote`/`near`. PROMOTE.md gains one paragraph stating the rule and the unlock condition.
- **Payoff:** ~40–60 probes/pass saved at current pool size ≈ **0.9–1.3 mill-hours per pass,
  per generation**, compounding at every champion change (ledger keys are (idea, generation),
  so every generation currently re-buys every dose).
- **Risk:** A non-monotone dose curve (middle dead, extreme alive) is missed for one pass.
  Mitigated by the `near` unlock and by PROMOTE.md's existing human-exception path to trial.

### GV-002 ★ · Premise graph: every entry declares its premises; a killed premise cascades
- **Structural problem:** Entries already depend on each other — the files say so, ad hoc, in
  prose nobody can execute on. Real, named dependencies found in F–J: **F-043** (V-scaling law)
  gates F-051/052/053/054 (all four 50M entries presuppose its answer), F-044/046/047/050 and
  I-018 (F-002 × F-043: "at the V the scaling law demands, the slow counter is reset to death");
  **WH-014** (embedding rows join the vote trainer; the 3.81 MB → ~0.86 MB byte claim and its
  ≤ +0.05-nat per-byte bar) is the stated plumbing premise of WH-016 ("depends on WH-014's
  embedding-vote plumbing; defer until it lands"), WH-018, WH-019 and combination I-020;
  **F-055** (reservoir control) is F-061's literal kill test ("retires if within 0.02 of
  F-055") and the premise of headline audit J-046; **G-026/G-030** gate G-035, whose own entry
  says it is "only worth its passes if at least one of them shows the counter field carries
  signal"; **WH-051** prices F-001's target population before F-001 may spend; the missing
  `--corpus v2` flag (E-018's path) silently blocks G-013–024's v2 subset, I-002, WH-039/044/048
  and G-024's v3 successor. Today, if F-043 reads flat or WH-014 fails its bar, nothing stops
  the mill from probing ~10 dependents against a dead premise and ledgering the noise as verdicts.
- **Governance mechanism:** A machine-readable **premise edge**: `premises: [F-043, WH-014]`
  plus `premise_kind: gates|prices|kill-test|plumbing`. When a premise entry's trial verdict is
  `below`/killed, every dependent is auto-flagged `premise-dead` in the ledger and skipped by
  screen.py until a human clears the flag — the cascade is a status, not a deletion.
- **Exact change:** `premises:` field in the `mill` block; a `mill/premises.json` edge list
  seeded with the ~25 edges named above (extracted verbatim from the candidate files' own
  "depends on / gates / ranked below deliberately" sentences); screen.py checks the edge list
  before queueing a probe and writes `premise-dead` skips to `mill/ledger.jsonl`.
- **Payoff:** Prevents the single most expensive failure mode available to this pool: a full
  dependent subtree probed against a dead premise. The F-043 subtree alone is ~9 entries
  (≈ 0.2 probe-hours/pass) plus up to three 24-min trials at 50M format — **~1–2 mill-hours
  saved per killed hub premise**, and verdict quality rises because dependents are never
  "measured" in a regime their own files call uninterpretable.
- **Risk:** A premise read as flat at probe scale may still hold at trial scale (the F-002
  lesson). Cascade therefore flags and skips — it never retires — and PROMOTE.md's exception
  path can clear any flag by name.

### GV-003 ★ · Representative-entry clustering: collapse the 12-member readout cluster to 3 entries + variant notes
- **Structural problem:** The largest real near-duplicate cluster in the pool is the
  **post-training readout cluster, G-025–G-036 — all 12 members**: G-025 per-layer install-scale
  calibration · G-026 counter-resolved readout · G-027 checkpoint logit-ensemble · G-028 logit
  temperature · G-029 full-state checkpoint averaging · G-030 counter-soft install · G-031
  validation-selected checkpoint · G-032 disagreement-gated zeroing · G-033 per-head attention
  temperature · G-034 unigram prior-correction · G-035 measured greedy flip polish · G-036
  cross-seed logit ensemble. Twelve separate queue slots, ledger lines and report sentences for
  what is operationally **one eval session on the same existing checkpoints**, differing only in
  readout transform. PRIORITIES.md already collapsed two of them by hand (G-028 "fold into
  G-027's eval batch"; G-035 gated behind G-026/G-030) — proof the cluster is real and the fix
  is manual today. Cross-wave echoes widen it to 16: F-033 (split-stack ensemble), F-058
  (minority readout), I-034 (era-stratified modal readout), MILL-218/219 (modal readout).
- **Governance mechanism:** **Cluster entries**: one representative entry per cluster carries
  the queue slot; siblings become numbered **variant notes** inside it, executed in the same
  eval session in a filed order, each still ledgered under its own id so no verdict is lost.
  Cluster rule: same input state, same cost class, transforms that commute or are explicitly
  ordered — readout qualifies; training arms never cluster.
- **Exact change:** Merge G-025–G-036 into three representatives in IDEA-POOL.md —
  `G-026-cluster` (counter-field readouts: G-026, G-030, G-035, G-032), `G-027-cluster`
  (prediction-space readouts: G-027, G-036, G-028, G-033, G-034) and `G-025-cluster`
  (state-space readouts: G-025, G-029, G-031) — with the other nine ids preserved as variant
  notes; screen.py gains a `variant_of:` ledger key so variants share one session, not one verdict.
- **Payoff:** 9 queue slots and ~9 × (session setup + held eval) removed per pass; at
  eval-only prices this is **~0.5–1.0 mill-hour/pass**, and verdict quality improves because
  all 12 transforms are finally read against the *same* checkpoints in the *same* session —
  today they can drift across generations and become incomparable.
- **Risk:** Variant ordering effects (e.g. G-025's scale search before vs after G-026's
  resolution confounds both — PRIORITIES.md flags exactly this pair). The filed order inside
  the representative is therefore part of the entry, and any variant may be split back out by
  name if its interaction is the question.

### GV-004 · Family census tag: no entry merges without a family, a lens and a cost class
- **Structural problem:** Nobody can currently answer "how much of the pool is X?" without
  re-reading 686 entries. The counts exist only as lens headers inside each wave file, and they
  already reveal skew the pool never chose: counter-centric entries dominate (the word "counter"
  appears 658 times across F–J; WH-049–060 is a 12-entry counter-forensics lens, I-025–036 a
  12-entry counter-ageing lens, and F-001–030 a 30-entry vote-mechanics block — together
  ~54 entries, ~17% of all candidates, orbit one int8 field), while whole axes (serving cost,
  safety) survive on single entries (WH-037, WH-015). PRIORITIES.md's top 40 had to be built by
  hand because the pool carries no census of itself.
- **Governance mechanism:** Mandatory merge-time metadata: `family:`, `lens_origin:`,
  `cost_class:` (sweep / process-flag / eval-only / full-trial-only / mill-change — the classes
  PRIORITIES.md already defined) on every entry, plus an auto-generated census table.
- **Exact change:** Extend the `mill` block schema in IDEA-POOL.md; add `mill/census.py`
  (counts entries by family × cost class × status, run at each merge) writing
  `mill/CENSUS.md`; CANDIDATES-F–J merges are blocked (by convention in PROMOTE.md) on the
  three fields being present.
- **Payoff:** Every future prioritisation, budget and coverage decision drops from hours of
  re-reading to one file read — conservatively **2–4 mill-hours saved per wave review**, and
  GV-001/GV-005/GV-009 all become enforceable instead of aspirational.
- **Risk:** Tagging debt on the existing 368 pooled entries. Bounded: census.py can seed tags
  from the MILL number ranges (1xx research, 2xx vote-trainer, 6xx gate, 11xx shape…) and lens
  headers, leaving only genuinely ambiguous entries for a human pass.

### GV-005 · Lens-quota abolition: waves file by expected value, not by 12-slot grids
- **Structural problem:** The 12-per-lens grid (GV preamble) guarantees over-supply of whatever
  a lens can generate 12 of, regardless of value: kernel-semantics I-049–060 includes I-050
  (own prediction: +0..+2% end-to-end) and I-060 (own prediction: likely worse than the
  champion) — entries PRIORITIES.md retired on sight — yet they consumed the same filing effort
  and will consume the same merge review as I-038. Conversely a lens with 20 strong ideas is
  capped at 12 and pushes its overflow into the next wave as "combinations" (I-013–024 is
  substantially wave F/G/H overflow wearing a × sign).
- **Governance mechanism:** Replace the per-lens quota with a **per-wave family budget**:
  a wave may file at most **6 entries per mechanism family** and at most **2 predicted-flat or
  predicted-negative controls** (controls are valuable — MILL-136, WH-072 — but they are a
  budget line, not a discovery), with any excess filed to a clearly-marked overflow annex that
  does not enter merge review until a family slot frees.
- **Exact change:** Protocol only: amend the Idea Engine wave brief template (the rotation
  instructions under `mill/.idea-engine/`) to state the 6-per-family / 2-control budget and
  the annex rule; no code change.
- **Payoff:** At wave-5/6 filing rates (~60–72 entries/wave), cutting grid-filler by even a
  third saves **~0.5 mill-hour of probes/pass** plus the larger, unpriced saving: merge-review
  and prioritisation time per wave.
- **Risk:** A miner self-censors a genuinely odd idea to fit its family budget. The annex
  preserves it verbatim; the budget governs merge order, never existence.

### GV-006 · Retirement by supersession: a closed question retires its re-filings automatically
- **Structural problem:** IDEA-POOL.md states the pool "only gains entries, it never loses
  them", and its header lists questions already CLOSED with numbers (vote-threshold annealing
  8→64; AdamW cooldown on the layered chassis; the JEPA objective; magnitude votes as
  specified). Yet the candidate waves re-file against closed ground with no supersession
  marker: F-040 (descending V 64→8) re-opens the closed anneal with its sign reversed;
  F-031 re-files JEPA as an initializer; MILL-201–203 exist precisely because the closed
  magnitude-vote verdict needed a "calibrated retest" carve-out argued by hand. Each re-filing
  currently costs a full human adjudication of "is this the closed thing or a different arm?"
- **Governance mechanism:** A **supersession registry**: every closed verdict gets a registry
  line naming the mechanism, the closing numbers, and the exact carve-out that would make a
  re-filing a *different* arm (e.g. "anneal: closed for hot starts; cold-first is a different
  arm only if it never goes below V=32" — the MILL-204 distinction, generalised). A candidate
  matching a registry line without satisfying its carve-out is retired at merge, citing the line.
- **Exact change:** New file `mill/CLOSED.md` seeded from IDEA-POOL.md's appendix of
  already-tested arms + PRIORITIES.md's retire table (G-063, G-062, G-053, G-028, I-060,
  I-050, WH-072, F-065); PROMOTE.md's merge checklist gains "check CLOSED.md first".
- **Payoff:** Kills repeat adjudication and repeat probing of settled ground — the 8 entries
  PRIORITIES.md retired by hand would have been retired at merge; **~0.3–0.6 mill-hours/pass**
  plus the verdict-quality gain of never re-litigating a number the lab already owns.
- **Risk:** A registry line drawn too broadly retires a genuinely different arm (the
  MILL-201 failure mode, in reverse). Carve-outs must therefore quote the closing entry's own
  numbers, and retirement is appealable by naming the differing mechanism in one sentence.

### GV-007 · Retirement by premise death and age: the two-generation sunset
- **Structural problem:** Beyond supersession, nothing ever expires. An entry whose premise was
  a *champion property* (e.g. entries premised on V=32 at 0.885M weights, on corpus v1's held
  set, or on the layered stack summing its levels — a premise the half-control already killed:
  plain 2.9010 vs layered 2.8990) survives every generation change untouched, because ledger
  keys are (idea, generation) and a new generation simply re-opens everything. PRIORITIES.md's
  deferral table is a manual, one-off version of the policy the pool needs permanently: F-051–054
  deferred behind F-043, I-013–024 deferred behind both parents' probe records, WH-006 deferred
  behind WH-003 — ~27 entries parked by hand, with named triggers stored only in that file.
- **Governance mechanism:** Two automatic sunsets. **(a) Premise-death:** when GV-002's graph
  marks a premise killed, dependents older than that verdict retire unless re-filed against
  the new premise. **(b) Age:** an entry that has survived **two champion generations** without
  a probe record moves to `mill/RETIRED.md` (full text preserved) and leaves the active pool;
  re-filing it is free and explicit. Deferral triggers from PRIORITIES.md become ledger fields
  (`deferred_until: <entry-id + verdict>`), checked by screen.py each pass.
- **Exact change:** `mill/RETIRED.md` + a generation-boundary step in screen.py implementing
  (a)/(b); PROMOTE.md's funnel diagram gains the RETIRE exit it currently lacks.
- **Payoff:** Bounds pool growth: without a sunset the pool doubles roughly every two waves
  and pass cost (7.7 h at 368) scales with it — the sunset is worth **~3–4 mill-hours/pass by
  wave 8** against the no-policy baseline, and keeps the active pool's average premise alive.
- **Risk:** Retiring a slow-burn entry whose moment comes at a larger scale (F-051-class).
  Retirement is archival, not deletion, and the scale-ladder rungs are named re-filing triggers
  in RETIRED.md itself.

### GV-008 · Combination quarantine: I-013–I-024 may not merge until both parents hold probe records
- **Structural problem:** Wave I's combination lens filed 12 second-order entries (I-013–024)
  over parents that are themselves unprobed — F-001, F-024, F-007, G-030, G-014, F-022, F-003,
  F-006, F-013, G-022, F-002, F-043, WH-025, F-010, WH-014, G-001, G-013, F-018, G-017, F-048,
  WH-027, F-064, WH-033. PRIORITIES.md admitted exactly one (I-015) and deferred the other 11
  for the right reason: "combining two unmeasured parents produces an unattributable number
  whatever it shows" — and I-013 is worse, deleting the very channel F-001 creates. But that
  deferral lives in one prioritisation file; the next merge pass can still ingest all 12.
- **Governance mechanism:** A hard merge rule for combinations: a `×` entry merges only when
  **both parents hold at least a probe verdict** in the ledger, and its own probe is scheduled
  in the same pass as (or after) the later parent's — the I-015 sequencing, as law. Combinations
  whose parents conflict mechanically (I-013, I-017, I-018, I-024 — the four filed *because*
  the parents fight) are exempt from the ban but reclassified as **collision experiments**,
  judged on their filed interaction prediction, not on Δ alone.
- **Exact change:** PROMOTE.md gains the combination rule; IDEA-POOL.md's `mill` block gains
  `parents: [F-001, F-024]` for combination entries; screen.py refuses (ledgers as
  `quarantined`) a combination whose parents lack probe records.
- **Payoff:** Saves up to **11 probes (~0.25 mill-hours) plus any inline trials** on numbers
  that cannot be attributed, and — the larger prize — protects verdict quality pool-wide: one
  unattributable combination "win" adopted as champion would re-denominate every later verdict.
- **Risk:** Slows a genuinely urgent synergy by one pass. Accepted deliberately; I-015's own
  entry already accepts the same sequencing voluntarily.

### GV-009 · Mill-change budget: the 24-entry machinery family competes for one slot per pass
- **Structural problem:** Wave G filed **24 mill-change entries** — G-037–048 (futility stop,
  probe ladder, two-stage gate, near-band extension, drift sentinels, re-screen triage,
  surrogate queue, step-count gate, budget partitioning, interaction mining, champion defence,
  deferral ledger) and G-061–072 (calibration funnel, banded second seed, sequential trials,
  held-eval economy, step-10 kill, dose sequencing, fork screening, steps covariate,
  proxy-context, dual-read, proxy judge, caravan) — plus wave J's fidelity family J-025–036
  (12 more) proposing changes to the same funnel. These are not 36 independent ideas; they are
  36 competing amendments to one small codebase (`screen.py`, `sweep_probe.py`, PROMOTE.md),
  several mutually exclusive (G-039 vs G-062: same purchase, PRIORITIES.md picked one; G-037
  vs G-063: same theorem, filed twice) and each carrying regression risk to every verdict the
  mill issues. PRIORITIES.md's top 40 already spends 5 of its 40 slots on this family — the
  correct instinct, with no standing rule behind it.
- **Governance mechanism:** Mill-changes get their own budget line: **at most 2 machinery
  changes land per pass**, ranked by PRIORITIES-style leverage (saving × pool size), and a
  machinery change may not land in the same pass as a champion adoption (verdict machinery and
  judged population never move together — the stale-reference guard's spirit, extended).
- **Exact change:** PROMOTE.md gains a "machinery budget" section; `mill/CENSUS.md` (GV-004)
  reports the mill-change family's size and landed count per pass; duplicate-theorem pairs
  (G-037/G-063 class) are merged at filing under GV-006's registry.
- **Payoff:** Verdict comparability across a pass is preserved — worth more than hours: a
  mid-pass funnel change silently splits one pass into two incomparable half-passes. Direct
  saving **~0.5 mill-hour/pass** in avoided duplicate machinery probes (G-062/G-063 class).
- **Risk:** A high-leverage fix (G-038's ladder) waits a pass behind a lesser one. Ranking by
  leverage, not filing order, is the stated tiebreak.

### GV-010 · Coverage ledger: the wave-I negative-space map becomes a living file, re-issued every wave
- **Structural problem:** The pool's only coverage map is wave 4 lens 1's negative-space file
  (`.idea-engine/wave4-lens1-negative-space.md`), which mapped IDEA-POOL + CANDIDATES-A–H and
  filed its verified gaps as wave I (I-001–012). It has not been updated since: **wave J (48
  entries) opened an entirely new dimension the map does not contain** — headline falsification
  (J-037–048 audit the lab's own claims: "votes reach ≈97% of STE's gain", "the rotary win is
  real", "held windows are clean") — and waves F–J closed some mapped gaps while opening
  others (e.g. the gate-statistic cell, "open" in the map, was hit independently by F-005,
  I-003, I-004, I-005 and I-050 — five entries, no coordination). A stale map actively misleads:
  the next negative-space miner will re-derive filled cells as "gaps" and file duplicates.
- **Governance mechanism:** Coverage becomes a **ledger, not a wave**: a dimension × state
  table (state ∈ covered / probed / closed / open-verified) regenerated from CENSUS.md +
  ledger.jsonl after every wave lands, with each wave's miner required to file against the
  current table and to mark the cells their wave changed.
- **Exact change:** New file `mill/COVERAGE.md` seeded from wave4-lens1's verified/rejected
  gap lists, extended with J's falsification dimension and the governance dimension (this
  file); the wave brief template gains "update COVERAGE.md" as a deliverable line.
- **Payoff:** Prevents the recurring cost of re-deriving coverage by hand (wave 4 spent a
  full miner on it) and of duplicate filings into filled cells — **~1 miner-wave per two
  waves saved**, and every future "gap" claim becomes checkable in one read.
- **Risk:** The table rots if a wave skips its update. Making the update a named deliverable
  of the wave brief (not a favour) is the enforcement; a stale COVERAGE.md must print its
  own last-updated wave at the top.

### GV-011 · The counter-forensics session: WH-049–WH-060 run as one dump, one script, twelve reports
- **Structural problem:** Wave H's counter-forensics lens (WH-049 forecast · WH-050 divergence ·
  WH-051 frustration census · WH-052 per-weight validity · WH-053 fingerprint · WH-054 settled
  selection · WH-055 entropy clock · WH-056 field taxonomy · WH-057 dead-counter census ·
  WH-058 oscillation anatomy · WH-059 kurtosis warning · WH-060 c1/c2 disagreement) is 12
  entries that all read **the same counter-field dump** — WH-051's own entry already names the
  shared vehicle: one `mill/counter_anatomy.py` pass "shared by WH-051/004/009/010/012 — one
  pass over a dump emits the full anatomy table". Filed as 12 pool entries, they will be
  merged, queued and reported as 12 ideas; run as filed, the dump is re-produced and re-loaded
  per entry. The same pattern repeats smaller in J-013–024 (12 held-anatomy slicings of the
  same eval outputs) and I-011/I-012.
- **Governance mechanism:** Generalise GV-003's cluster rule to analysis families: entries
  sharing one input artefact and one script merge into **one session entry** with per-report
  sections; each report keeps its own falsifiable prediction and its own ledger line, but the
  artefact is produced once. Rule of thumb for merge review: *same dump, same day, one entry*.
- **Exact change:** Merge WH-049–060 into one IDEA-POOL entry (`WH-049-session`,
  variants WH-050–060) whose run string invokes `mill/counter_anatomy.py --full`; likewise
  bundle J-013–024's slicings behind J-013 as variants when wave J merges.
- **Payoff:** 11 queue slots and 11 artefact productions removed; **~0.3–0.5 mill-hour/pass**
  at analysis prices, and the twelve reports become mutually consistent (same dump, same
  champion generation) instead of twelve readings of twelve slightly different states.
- **Risk:** One buggy shared script corrupts twelve reports at once instead of one. Mitigated
  by WH-053's fingerprint report acting as the session's own sanity check, filed first inside
  the session.

### GV-012 · Headline-premise insurance: J-037–J-048 audits are premises, and the pool re-prices when one falls
- **Structural problem:** Twelve wave-J entries (J-037–048) audit claims the *entire pool*
  silently treats as premises: that votes earn ≈97% of STE's gain at ~1/10 state (J-037),
  that rotary's win is real (J-038 — every one of the 686 entries runs `--rope`), that held
  windows are clean (J-042 — every Δ in every ledger line is denominated in them), that equal
  minutes is a fair currency (J-043), that the probe funnel can tell signal from noise (J-044),
  that 8-minute verdicts extrapolate (J-045). These are filed as ordinary candidates in a
  48-entry wave, competing for probes with ordinary arms — yet if J-042 finds the leak large,
  or E-018's corpus-v2 re-baseline (PRIORITIES #9) moves the champion number, **every queued
  entry's prediction interval is denominated in a currency that just changed**, and nothing in
  the pool marks which entries were priced in the old one.
- **Governance mechanism:** Promote headline audits to **premise class** in GV-002's graph:
  J-037/038/042/043/044/045 become named hub premises of the whole pool (alongside F-043 and
  WH-014). When a hub premise's verdict lands, census.py re-stamps every active entry with
  the premise generation it was priced under; entries priced under a *fallen* hub premise are
  not killed — they are queued for a one-line re-price note before their next probe.
- **Exact change:** `mill/premises.json` gains the six hub entries with `scope: pool`;
  PROMOTE.md's generation-change procedure (currently: re-measure job zero) gains "re-stamp
  premise generations"; J-037–048 merge ahead of wave J's ordinary arms, by protocol.
- **Payoff:** Verdict quality, priced honestly: it converts a future "half the ledger was
  measured against a leak" discovery from a pool-wide write-off (potentially **tens of
  mill-hours** of verdicts) into a bounded re-pricing pass over only the affected entries.
- **Risk:** Over-centralisation — if everything depends on six hubs, one slow audit stalls
  the pool. Hub status therefore flags and re-stamps only; it never blocks a probe the way
  a plumbing premise (GV-002) does.

---

*End of wave-6 lens-4 governance. 12 entries (GV-001–GV-012); ★ = GV-001 (family budgets),
GV-002 (premise graph + cascade), GV-003 (representative clustering of the readout cluster).
Largest duplicate cluster found: the G-025–G-036 readout cluster, 12 members, named in GV-003
(16 with its F/I/MILL echoes). Largest premise hubs: F-043 (~9 dependents), WH-014
(4 dependents + its byte claim reused pool-wide), and the six pool-scope headline premises
of GV-012. Nothing here edits the pool — adoption of any rule above is the pool owner's call,
executed through PROMOTE.md, screen.py and the merge checklist as each entry specifies.*
