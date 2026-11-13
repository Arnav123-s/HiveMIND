# Muse's work — Muse's side

# Wave 7 · Lens 2 (Sprint Endgame) — The Endgame Plan: what must close by Sun Nov 15

<!-- Muse's work — Muse's side of the BitNet lab. Rotation-7 miner 2, SPRINT ENDGAME lens.
This is NOT new arms. It is the closure plan for the Sunday bundle (tried / killed / promoted /
adopted): which open questions must be closed for those four words to mean anything, in what
order, at what cost, and what each closure lets the bundle claim vs confess.
Sources read in full or header: mill/PRIORITIES.md (top 40), coordinator notes of
CANDIDATES-F..K, mill/PREFLIGHT.md, mill/PROMOTE.md, mill/RIGOR-AUDIT.md, mill/FLAGS-BUILT.md,
mill/CONCURRENCY.md, DATA-AUDIT.md, ~/workspace/edit-lab/SPRINT.md — cross-checked against
disk state Thu 2026-11-12 ~20:54 PT. Nothing here merges, probes, or trials anything. -->

---

## 0. The state the endgame starts from (disk, not intention)

The bundle's four verbs currently have these counts: **tried 0, killed 0, promoted 0,
adopted 0.** That is not rhetoric; it is the filesystem:

- `mill/ledger.jsonl` does not exist. Neither do `mill/trials.jsonl`, `mill/champion.json`,
  `mill/mill-loop.log`, `mill/PROBE-NOISE.md`, `mill/PREFLIGHT-RESULTS.md`,
  `mill/FIDELITY.md`, `mill/concurrency.json`. **The mill has never run a probe.**
  `screen.py`, `sweep_probe.py`, `PROMOTE.md` and `run-forever.sh` exist and are built —
  the engine is assembled, fuelled (pool below), and has never turned over.
- The pool the mill *can* judge is `IDEA-POOL.md`: **380 entries** after the round-2 merge.
  Waves F–K filed **380 more** (F 66, G 72, H/WH 72, I 62, J 48, K 60) and **none of them
  are in the pool** (grep: F-001/G-001 appear 0 times in IDEA-POOL.md; every candidate file
  says so itself). PRIORITIES.md ranks only F–I (270). J and K are unranked except by their
  own coordinator top-3s.
- Of the 380 pooled entries, only **35 are runnable against live `train.py`**
  (FLAGS-BUILT.md). The flag factory built the rest into the staging copy
  `train_next.py` — **222 of 380** runnable there — but `train_next.py` has **not been
  merged** into `train.py`, and the scale ladder is still running against live `train.py`,
  which is why. Every hour the merge waits, the mill's reachable universe is 9% of its pool.
- The lab itself is contended: the scale ladder still owns slots (10M seed 1 finished
  short at 39/56 steps; 50M seed 0 was killed, rc=-9; a plain-rope rung timed out), and
  the mill yields to the ladder and to growth cycles by design. Endgame hours below are
  *machine* hours on a 1.5-CPU VM that does not belong to the mill alone.

**Consequence that frames everything below:** Sunday's bundle cannot be a report on
waves F–K. At best it is a report on **generation 0 of the merged pool**, plus a priced
set of corrections to the number every verdict is denominated in (2.8580), plus an honest
list of what was filed-but-never-tried. The must-close list is ordered to make exactly
that bundle true.

**Cost units (filed, used throughout):** probe = 75 s / 1 seed · trial = 24 min
(3 seeds × 8 min) · eval-only = minutes on existing checkpoints, no training ·
one full pass over the 380-entry pool ≈ 7.7 h of probes at the old 368-entry size
(PRIORITIES.md arithmetic); over the 222 newly-runnable subset ≈ 4.6 h of probes.

---

## 1. The must-close list — 11 items, in execution order

Order is dependency order, not importance order: each item either gates the items after
it or reprices them. Skipping upward is how the bundle ends up confessing things it
could have claimed.

---

### E-1 · Preflight: parity + probe-noise — the licence for every probe verdict

- **Question:** Does the sweep reproduce the lab's own init exactly, and is the 0.05
  promotion bar at least 2× the measured probe noise — or is the funnel a coin flip?
- **Cheapest closing action:** Run `mill/preflight.py` in the first free slot, exactly as
  `mill/PREFLIGHT.md` specifies: one 15 s parity run (sweep job-zero `held_init` must equal
  **8.3138** exactly — the value on disk in `runs.jsonl` for `layered_half_rope` seed 0,
  verified for this plan) plus three 75 s job-zero noise runs on seeds 0/1/2, writing
  `PROBE-NOISE.md` + `PREFLIGHT-RESULTS.md`. If the bar fails, raise `PROMOTE_DELTA` to
  the printed ceil(2×sd) in **both** places it lives (`screen.py`, `PROMOTE.md`) before
  any pass is judged.
- **Cost:** ~5 min machine, solo. Zero design work — scripted since the rigor-fix pass,
  never run because the ladder owned the lab.
- **Closed, the bundle can claim:** "Every probe verdict below was issued by a sweep
  proven bit-faithful at init, under a promotion bar measured against this VM's noise."
- **Open, it must confess:** Every tried/killed count in the bundle is unlicensed —
  RIGOR-AUDIT §2b/§5a both sit at NOT-YET-CHECKABLE, and a parity failure discovered
  *after* Sunday would retroactively void the whole table, not just embarrass it.

### E-2 · The mill's first pass, on a ledger that can survive audit

- **Question:** Do the words tried/killed/promoted/adopted refer to a complete,
  reproducible record — or to whatever a log line happened to say?
- **Cheapest closing action:** Before the first pass (not after), land RIGOR-AUDIT §4's
  four small fixes in `screen.py`: `code_sha` on every ledger/trial line; explicit
  `"seed": 0` on probe lines; one `kind: "deferrals"` ledger line per pass (ids +
  reasons — today deferrals leave *no durable trace*); `verdict == "error"` treated as
  not-done (retry ≤3, then an explicit `benched` line) instead of silently consuming an
  idea for the generation. Then run **one complete gen-0 pass** in pool order and
  hand-inspect the ledger once (RIGOR first-pass checklist item 4: every probe line
  present, deferral count reconciled against the pool, no error-benched ids).
- **Cost:** ~1–2 h of careful code work (no machine time) + the pass itself (see E-3 for
  its size). The fixes are each a few lines; retrofitting them after gen 0 is on the
  record is the expensive version.
- **Closed, the bundle can claim:** Tried/killed/promoted/adopted as *auditable counts*
  with a code fingerprint, including an honest deferred count with reasons — the bundle
  can say what it did **not** try and why, from the same ledger.
- **Open, it must confess:** Counts reconstructed from ephemeral logs; skipped ideas
  indistinguishable from measured ones; a transient crash permanently filed as a
  verdict. Any external reader (Fable's side, Arnav in a month) cannot reproduce a
  single line of the bundle.

### E-3 · Corpus plumbing: merge `train_next.py`, fix the resolvers, unblock the v2 subset

- **Question:** Can the mill actually execute the corpus entries its own priorities
  rank in the top 10 — or does the live trainer only know one corpus?
- **Facts on disk:** Live `train.py` has **no `--corpus` flag at all** — it hardcodes
  `corpus.u16`. `--corpus` exists only in staging `train_next.py`; `sweep_probe.py`
  carries a frozen copy of the chassis parser with **neither `--corpus` nor `--votes`
  nor `--wd`** (so even merged, sweep-mode corpus entries validate and then fail —
  exactly the error-bench trap of E-2). And the staging v3 resolver is **broken as
  filed in K-001**: for `--corpus v3` it looks for `LAB/corpus-v3.u16`,
  `LAB/v3.u16`, `LAB/corpus-v2/corpus-v3.u16` — the real file is
  `LAB/corpus-v3/corpus-v3.u16`, which is on none of those paths.
- **Cheapest closing action:** (1) Merge `train_next.py` → `train.py` in the first
  ladder-free window, re-running FLAGS-BUILT's baseline-identity suite (8 arm configs,
  held_init/held_final/state_hist identical) as the merge gate. (2) Add the missing
  directory form to the resolver (`LAB / "corpus-v3" / "corpus-v3.u16"`, general:
  `corpus-<name>/corpus-<name>.u16`). (3) Give `sweep_probe.py` the same three flags —
  or generate its parser from `train.py`'s, per RIGOR §4.4, so this class of drift
  cannot recur mid-sprint. (4) Smoke `--corpus v2` and `--corpus v3` once each at tiny
  config and confirm the record's `corpus` field and `corpus_pieces` are the intended
  streams.
- **Cost:** ~2–3 h dev + ~15 min of smoke/identity runs. No trials. This is the single
  largest runnable-count move available: **35 → 222 of 380**.
- **Closed, the bundle can claim:** Its gen-0 pass actually covered the pool it names,
  and the corpus-denominated entries (E-018, E-019/020/021 variants, the whole blocked
  subset below) were *runnable and either run or explicitly deferred with a reason*.
- **Open, it must confess:** The silently blocked subset stays silent: per K-038's
  premise graph, the missing live `--corpus v2` path blocks **G-013–G-024's v2 subset,
  I-002, WH-039/044/048** (and G-024's v3 successor) — roughly a score of entries the
  bundle would otherwise list as "queued" when the truth is "unexecutable." A bundle
  that reports a 380-entry pool while 345 of them could not have run is misreporting
  its denominator.

### E-4 · Corpus-v3 verification (FD-001's first job, feeding K-001)

- **Question:** What *is* corpus-v3, as built — because every FD/K number is currently
  written against a corpus that may not exist in its stated form.
- **Facts on disk:** Wave K's own method note: when the FD miner read it,
  `corpus-v3.u16` held **1,777,325 pieces** with `build.log` showing **only the
  blocklist step**, and `corpus-v3/SOURCES.md` **does not exist**. That is still the
  disk state today: the file is 3,554,650 bytes = 1,777,325 pieces, `build.log` is the
  single blocklist line (18,706 segment keys), there is **no `corpus-v3.json`**, and
  the FD entries' economics are written against a stated **~21.4M pieces — 12× the
  built size**. The split-verification script `check_v3_split.py` exists; its output
  `corpus-v3/split-check.json` does not — the verification has not run.
- **Cheapest closing action:** (1) Establish the finished count from the file itself
  and state it wherever "~21.4M" was assumed; if the build is incomplete, either finish
  it or formally re-scope v3 to what exists. (2) Write `SOURCES.md` from the raw tree
  (`raw/gutenberg/`, `raw/wikitext/` are on disk). (3) Run `check_v3_split.py` —
  it verifies, with the lab's own `held_windows` construction, that no held window,
  aligned block, or BOS-line leaks into training, plus a 2,000-shingle spot check —
  and file `split-check.json`. (4) Note K-004/005/006's construction defects
  (document-level leakage past the line guard, hard-wrapped Gutenberg tokenized
  BOS-per-line, WikiText valid/test splits inside the stream) as *known defects with
  filed fixes*, not as surprises.
- **Cost:** ~30–60 min, analysis + one script run. No training.
- **Closed, the bundle can claim:** "v3 is N pieces (measured), split-verified clean at
  line level by the lab's own construction, with three named construction defects
  priced or pending" — and K-001's number (E-8) is denominated in a real corpus.
- **Open, it must confess:** Every v3 sentence in the bundle is denominated in an
  unverified, possibly 12×-overstated corpus whose held split has never been checked —
  i.e. v1's original sin (an unaudited stream treated as ground truth) repeated on the
  corpus that was built to fix it.

### E-5 · Price the v1 leak — and fix the citation before the bundle inherits it

- **Question:** How much of 2.8580 is held content the model already read in training?
  DATA-AUDIT §4 measured the exposure (30.8% of pieces are exact-duplicate copies;
  93.2% of lines sit in a duplicated group) and stated the consequence plainly: all v1
  held losses are "flattered by an unknown amount." Unknown is the problem.
- **⚠ Citation hazard the bundle must not inherit:** Wave J's coordinator note calls
  this entry **"J-037 · Dosed-leak calibration."** The filed body under J-037 is a
  *different* experiment (the votes-vs-STE accounting audit). The dosed-leak calibration
  as actually filed is **J-042** ("Held windows are clean": filed / excised / dosed
  runs + leaked-vs-clean slice split). Any bundle, priority list, or Slack post that
  cites "J-037" for the leak will be wrong in a way a reader can check in one minute.
  Cheapest fix: one errata line in the bundle itself, citing **J-042** (calibration),
  **J-022** (anatomy), **E-019** (excision).
- **Cheapest closing action, in two steps:** (a) **J-022 first** — eval-only on the
  existing champion: tag every held target leaked vs unique via the sidecar, report
  leaked share, both means, and the implied unique-only held (predicted: leaked
  28–34% of targets at ≈1.9–2.1 vs unique ≈3.3–3.5; unique-only held ≈3.35). Minutes,
  no training, and it either confirms the exposure is judge-sized or retires it.
  (b) If (a) lands anywhere near prediction, **J-042's excised + dosed pair**
  (E-019's construction for the excised arm; +5%-of-pieces synthetic leak for the
  dosed arm; filed run (a) is the control and its slice split comes free from the
  same runs). Kill thresholds are pre-filed: calibrated share ≥2%, **or** excision
  Δ ≥ **0.0411** (rotary's entire margin — the leak would swallow the lab's one
  confirmed win), **or** slice gap > 0.10.
- **Cost:** (a) ≤1 eval pass, minutes. (b) 2 trials = **48 min** (control already
  filed; 72 min if it must be re-run in-window). 
- **Closed, the bundle can claim:** "2.8580 carries a measured leak of X (calibrated,
  two independent estimates agreeing or their disagreement reported)" — every other
  verdict in the bundle can then be quoted with the leak band attached, and rotary's
  win either survives its band or is honestly re-filed as inside it.
- **Open, it must confess:** The bundle's reference number is flattered by an amount
  the lab has *admitted in writing* it cannot bound, while margins it trades in
  (0.0411, 0.0375, 0.0020) are smaller than the plausible leak. That confession, if
  it has to be made, belongs on the bundle's first page, not in a footnote.

### E-6 · Price the prose dilution (J-013, with J-047 as its ranking check)

- **Question:** What is 2.8580 *made of*? J-013's filed prediction: ≥35–45% of held
  targets sit in junk-class windows (numeric dumps / `merges.txt` gibberish /
  boilerplate) at mean loss ≤1.5, while real prose + lab-notes windows sit at
  ≈3.4–3.7 — i.e. the prose-only number the lab actually cares about is ≈**3.3–3.6**,
  roughly 0.5 worse than the headline it reports.
- **Cheapest closing action:** J-013 as filed — classify each of the 128 held windows
  by dominant source class via the offsets sidecar; one eval pass over the existing
  champion checkpoints (seeds 0–2); report per-class target share, mean loss, and
  loss-mass share. No retraining. Pair it with **J-047** (same eval-only re-scoring,
  GATE0 buckets, on champion / plain_half / ste_half) which asks the sharper question:
  does the pooled *ranking* survive on the prose bucket, or is the champion's edge
  carried by gibberish+numeric? J-013 has a pre-filed "pointless if" (class means
  within 0.15, or junk <10% of held) — a null result closes it just as cleanly.
- **Cost:** 1–2 eval passes, well under an hour total for both. The cheapest
  headline-sized fact available anywhere in waves F–K.
- **Closed, the bundle can claim:** Either "the pooled number is an honest average
  (classes within 0.15)" — a vindication worth having in writing — or it adopts
  J-013's licensed consequence: **`prose_held` reported beside every verdict**, with
  adoption judged on it. The bundle then knows whether its promoted/adopted entries
  won at language or at boilerplate.
- **Open, it must confess:** Every promoted/adopted claim in the bundle is a claim
  about a pooled average over a held set whose composition nobody has measured —
  the bundle cannot say what its winners are good *at*.

### E-7 · E-018 — the corpus-v2 re-baseline (PRIORITIES #9)

- **Question:** What is the champion's number in an honest currency? Every mill
  verdict is denominated in v1 held loss; v2 (0.907M clean pieces, built, on disk)
  removes the duplicate leakage and the easy junk wins. No arm has ever been
  measured on it.
- **Cheapest closing action:** E-018 as filed, the moment E-3 lands: champion config
  on corpus-v2 with v2-native held windows (every-40th rule on the v2 stream),
  3 seeds × 8 min. Filed prediction: v2 held reads worse than 2.8580 by 0.15–0.45.
  There is no cheaper honest version — it is one indivisible trial — and no probe
  substitutes, because the deliverable is a *reference*, not a screen.
- **Cost:** **24 min** machine, gated entirely on E-3.
- **Closed, the bundle can claim:** "Gen-0 verdicts are denominated in v1 (leaked,
  priced in E-5); the champion's clean-corpus reference is X on v2" — the level is
  known even though gen-0's *rankings* were earned on v1. (Whether rankings survive
  the corpus change is J-040's 3-arm transfer matrix — a should-close, §2, not a
  must: the bundle may not *claim* ranking transfer without it, but it can honestly
  report a level.)
- **Open, it must confess:** The bundle's champion number is a v1 point estimate
  with no clean-corpus counterpart at all — the "honest champion number" that
  PRIORITIES.md ranked #9 of 270 was still unmeasured when the sprint closed.

### E-8 · K-001 — the corpus-v3 re-baseline

- **Question:** What does the champion score on real text — the first corpus that is
  (pending E-4) clean *and* comparatively large, with per-source anatomy?
- **Cheapest closing action:** K-001 as filed, only after E-3 (resolver) and E-4
  (verification): `--arm layered_half --rope --corpus v3 --steps 160`, 3 seeds,
  pooled held **and** Gutenberg-held vs WikiText-held slices (the split is part of
  the deliverable — a pooled v3 number would hide exactly what J-013 exposed on v1).
  Filed prediction, denominated in v3 held: **3.10–3.45** at 160 steps; Gutenberg
  slice +0.05..+0.25 worse than WikiText (the K-005 wrap-BOS tax is the predicted
  reason, and K-005's paired run is the check if the slice lands that way).
- **Cost:** 3 × 160 steps at champion format ≈ **24 min** machine (160-step runs are
  the filed 8-min format's step count), plus the E-3/E-4 prerequisites.
- **Closed, the bundle can claim:** The sprint ends with the champion measured on
  all three currencies — v1 (native, leak-priced), v2 (clean, tiny), v3 (real text,
  sliced) — and every future series has an honest denominator to be judged against.
- **Open, it must confess:** v3 was built, announced at ~21.4M pieces, and never
  produced a single number; the ladder's starvation question (K-002) and every FD
  entry remain speculation denominated in the corpus nobody verified.

### E-9 · The counter question (J-002) — what the founding mechanism *is*

- **Question:** Is per-weight counter memory the mechanism (a weight improves because
  *its own* counter integrates *its own* evidence — the story behind "1 byte rivals
  12"), or is only the counter field's *statistics* doing the work? This is the
  cleanest discriminator in any wave, and it is binary by construction.
- **Cheapest closing action:** J-002 as filed: champion config, one change — every
  10 steps, permute each BitLinear's counter array within its layer (histogram, gate,
  V, flip rate all exactly preserved; only weight↔counter ownership broken).
  3 seeds × 8 min. Needs one small process flag in the merged trainer (bundle it into
  E-3's merge window so it is smoke-tested with the same identity suite). Filed
  predictions: memory theory → degradation **≥ +0.05** (toward/past 2.91);
  statistics-only → within **±0.015** of 2.8580. Optional corroboration at probe
  price: K-051 (lottery flips — delete the counters, spend the same flip budget by
  lottery; costs ≥ +0.15 at probe would corroborate memory more strongly than the
  shuffle itself).
- **Cost:** **24 min** machine + ~1 h flag work inside E-3's window.
- **Closed, the bundle can claim:** The sprint's central mechanism claim is stated
  as a *measured* fact in whichever direction it lands — and the direction reprices
  a family either way (G-026/G-030/G-050 counter-space entries presuppose memory;
  K-051-class deletions presuppose statistics).
- **Open, it must confess:** The bundle reports dozens of verdicts about a trainer
  whose core noun — "the counter remembers" — was never discriminated from its
  null, despite the discriminating experiment costing one trial and being filed
  as wave J's #2.

### E-10 · F-043 — the vote-threshold scaling law (gates the scale story)

- **Question:** Must V fall as N rises? Flip share already fell ~5× from 0.885M to
  10M at fixed V=32; if that trend is real, every ladder rung above 2M was measured
  against a near-frozen trainer, and at 50M most weights would never flip at all.
- **Cheapest closing action:** F-043 as filed (PRIORITIES #5): sweep at 10M,
  V ∈ {32, 16, 8, 4}, with 2M as the flat negative control. Do **not** substitute
  more ladder rungs — K-002's v3 ladder re-run is the expensive version of a
  neighbouring question and is explicitly a should-close (§2).
- **Cost:** A sweep — the cheapest process-class item in the top 40; filed as
  sweep-mode, tens of minutes at 10M step prices, not trials.
- **Closed, the bundle can claim:** The scale-ladder section of the wider sprint
  bundle can say whether its big-rung numbers describe architecture or a frozen
  trainer — and the premise graph (K-038) unblocks honestly: F-043 gates
  **F-051/052/053/054** (all four 50M entries), F-044/046/047/050, and the
  F-002 × F-043 interaction (I-018) on which PRIORITIES' hardest deferral rests.
- **Open, it must confess:** Every scale claim in the sprint is conditional on an
  untested scaling assumption, and ~9 filed entries were probed (or deferred)
  against a premise nobody measured — the bundle's "killed" list may contain
  entries killed by the ruler, not by their mechanisms.

### E-11 · The fidelity floor: J-025 + the lie registry, and the concurrency confession

- **Question (two halves of one honesty problem):** (a) Does the probe stage deserve
  the trust the funnel places in it? (b) At what concurrency were the bundle's
  numbers produced, and was that setting ever validated?
- **Cheapest closing actions:** (a) **J-025 as filed** — zero training: score every
  cheap observable already in `runs.jsonl` (15 arms × 3 seeds) against the recorded
  ranking; write `mill/FIDELITY.md` with Spearman ρ, sign-flip and false-promote
  rates at the 0.05 bar. Then the minimal form of **J-027**: flag the pool's
  over-horizon families (filed estimate: **15–25% of entries** have mechanism onset
  beyond the probe's ~25 steps) so their flat probes ledger as `INCONCLUSIVE —
  horizon`, never as kills. The full registry/schema change is a should-close; the
  *flagging* is what Sunday needs, because without it the bundle's "killed" count
  silently includes an unknown number of ideas the probe could not have seen.
  (b) Either run `bench_concurrency.py` in a free slot (it writes nothing unless
  the whole study completes) or print the truth in the bundle: **all gen-0 numbers
  are CONCURRENCY=1, the only setting with honesty evidence** — CONCURRENCY.md's
  own standing warning is that any figure quoted before the study completes is
  invented. SPRINT.md's Sunday checklist demands a concurrency verdict; "ran at 1,
  study still pending" *is* a verdict if it is stated, and a gap if it is not.
- **Cost:** (a) ~1–2 h analysis, zero machine. (b) One study run (6 probes × 3
  worker counts at 0.75 min + replicates — under an hour of free-slot machine) or
  zero, if confessed instead of run.
- **Closed, the bundle can claim:** "Killed" means killed: probe fidelity is a
  measured ρ with a known false-promote rate, over-horizon entries are counted
  separately as unjudged, and the concurrency basis of every number is named.
- **Open, it must confess:** The bundle's largest verb — killed — rests on an
  asserted bar (RIGOR §5a), an unmeasured fidelity, and a known 15–25% blind spot
  that files blindness as death.

---

## 2. Should-close if hours remain (in order; none gates the bundle's honesty)

1. **G-037 futility stop + G-039 two-stage gate + G-044 near-band extension**
   (PRIORITIES #1/#6/#7, all mill-changes): pure savings and queue hygiene — 8 min
   per doomed trial, insurance against seed-0-luck trials, and verdicts instead of
   a parked near-band graveyard. Valuable for the *next* generation; gen-0's bundle
   is honest without them if E-2/E-11 landed.
2. **The eval-only readout batch — G-026, G-027, G-036, WH-051, WH-037**
   (PRIORITIES #3/#11/#23/#4/#15): minutes each on existing weights; G-026
   (counter-resolved readout, −0.01..−0.04 predicted) also feeds E-9's interpretation,
   WH-051 prices F-001's target population, WH-037 could invert the lab's hardening
   priorities (one FP `log_scale` exponent flip predicted at Δ ≥ +0.5). Highest
   information-per-minute in the pool after E-5/E-6; they enrich the bundle but do
   not gate it.
3. **J-040 transfer matrix** (3 arms × 2 corpora): upgrades E-7's *level* into a
   *ranking-preservation* claim. 3 v2 trials ≈ 72 min.
4. **The filed J-037 (body)** — the votes-vs-STE accounting audit ("≈97% of STE's
   gain at ~1/10 the state"): a 2×2 (equal-minutes × equal-steps) with both state
   accountings printed; either kill condition (total-state ratio >25%, or
   equal-steps gap >0.12) re-files the lab's most-quoted sentence. ~4 trials.
   Worth doing precisely because E-5's errata will already have taught the bundle
   to cite carefully.
5. **K-037 family budgets + K-038 premise graph as machinery** (the *facts* of both
   are already used in E-3/E-10; the schema/screen.py automation is next-generation
   rent, ~0.9–1.3 mill-hours saved per pass per generation once live).
6. **K-002 v3 ladder re-run, J-038 rotary replication, F-055 reservoir control**
   (PRIORITIES #10): real questions, real prices (F-055 is one probe; J-038 is
   6 fixed-step runs; K-002 is full-trial-only at two budgets) — each strengthens a
   neighbouring bundle section without gating the mill bundle itself.

## 3. Explicitly NOT must-close (do not let these eat the weekend)

- **Merging waves F–K into the pool.** 380 unmerged candidates are a *filing*
  backlog, not a bundle defect. The bundle scopes itself to the 380-entry pool's
  gen 0 and lists F–K as filed-not-tried, with PRIORITIES' top 40 as the standing
  attack order. Merging without probing doubles every future pass's rent
  (PRIORITIES: +5.6 h of probes per pass) and buys Sunday nothing.
- **Any 50M work.** The rung died once already (rc=-9), F-043 (E-10) hasn't read,
  and K-002 itself declines to claim 560 steps at 50M (~14 h). Confess and move on.
- **The top-40 as a checklist.** Its own arithmetic prices a *first pass* at
  under 3 h, but Sunday needs the pass over the *pool* (E-2/E-3) more than it
  needs any individual arm in the 40. The 40 is the order for Monday, not the
  price of an honest Sunday.

## 4. The weekend schedule the list implies

| Slot | Work | Machine cost |
|---|---|---|
| Fri, first free slot | E-1 preflight (before anything is judged) | ~5 min |
| Fri | E-2 ledger fixes; E-3 merge + resolver + sweep parity + smokes (incl. J-002's flag) | dev hours; ~15 min |
| Fri–Sat | E-5a J-022 + E-6 J-013/J-047 (eval-only; run whenever the VM breathes) | <1 h total |
| Sat | Gen-0 pass over the runnable pool subset (E-2/E-3) — the bundle's body | ~4.6 h probes + inline trials as promoted |
| Sat | E-7 E-018; E-9 J-002; E-5b J-042 pair — the three priced trials | 24 + 24 + 48 min |
| Sat–Sun | E-4 v3 verification, then E-8 K-001; E-10 F-043 sweep | ~1 h + ~24 min + sweep |
| Sun | E-11 J-025 analysis + over-horizon flagging; concurrency study *or* confession; bundle assembly with deferral counts from the ledger | analysis hours; ≤1 h machine |

Total priced training exposure for all 11 must-closes, excluding the gen-0 pass
itself: **≈ 3 hours.** The pass is the long pole (~4.6 h of probes at 222 runnable),
which is why everything else on this page is deliberately eval-only, dev-only, or a
single trial — the endgame is affordable *only* in this order, and only because the
expensive questions (leak calibration, counter identity, both re-baselines) were
each filed in their cheapest honest form.

## 5. What the finished bundle gets to say

With E-1…E-11 closed, the Sunday bundle can claim, in one breath: *the mill ran its
first complete, preflight-licensed, ledger-auditable generation over a named pool at
a named concurrency; its reference number carries a measured leak (E-5), a measured
composition (E-6), a clean-v2 counterpart (E-7) and a real-text v3 counterpart with
source slices (E-8) on a verified corpus (E-4); its founding mechanism survived or
failed a binary discriminator (E-9); its scale numbers carry a tested V-scaling
premise (E-10); and its killed list is fidelity-bounded with the unjudged counted
separately (E-11).* Every clause of that sentence is one E-item. Remove an item and
the corresponding clause converts, mechanically, into the confession stated under it.
That conversion table — not any single arm — is this plan's deliverable.
