# RIGOR-AUDIT — independent check of the BitNet mill (Muse's work, Muse's side)

<!-- Muse's work — Muse's side of the BitNet lab. Written by the mill's checker
stream, 2026-11-12. This file checks; it does not fix. Nothing in mill/ was edited
by the checker. Where a claim below cites code, the file and line are named. -->

## What was audited, and when

Design-stage audit. At audit time the mill consisted of `IDEA-POOL.md` (176
entries), `screen.py`, `sweep_probe.py`, `bench_concurrency.py`, `PROMOTE.md`,
`CONCURRENCY.md` (study pending), and `run-forever.sh`. **No probe had ever
run**: `ledger.jsonl`, `trials.jsonl`, `champion.json`, and `concurrency.json`
do not exist yet. Everything about runtime behaviour is therefore graded
against the code and the lab's written discipline, and items that only a real
run can settle are marked NOT-YET-CHECKABLE with the exact check to run.

## The yardstick — the lab's standing discipline (from the RESULTS files)

Extracted from `RESULTS-2026-11-11.md`, `RESULTS-ROPE-2026-11-11.md`,
`RESULTS-HALF-CONTROL-2026-11-12.md`, `RESULTS-ROUND2-2026-11-12.md`,
`RESULTS-JEPA-2026-11-12.md`, and `train.py` itself:

- **Held set:** 128 fixed windows, every-40th block (`HELD_EVERY = 40`,
  `train.py:281`), never trained on; the batch sampler `offsets()`
  (`train.py:59`) rejects any window overlapping a held block.
- **Judge:** held loss, pre-registered per experiment, measured by the shared
  `held_loss()` at full rounding; never a train-loss proxy.
- **Seeds:** same seed → same init and same batch stream across arms
  (`torch.manual_seed` before construction, `random.Random(seed)` for the
  stream); 3 seeds per arm at full format; per-seed values always reported.
- **Spreads are sample sd (n−1).** Verified by recomputation: the recorded
  0.0161 for layered_half+rope (seeds 2.8765/2.8477/2.8497) and 0.0316 for
  plain are the n−1 values; the n values are 0.0131 / 0.0258.
- **Adoption bar:** beat the incumbent mean by **>2 sd AND >0.01** (round 2
  operationalised it against the baseline's sd: held < 2.8258). Verdicts were
  also argued per seed (round 2: "every cooldown seed is worse than every
  baseline seed — no overlap"; JEPA's pre-registered rule required wins on
  ≥2 of 3 seeds plus a mean-margin bar).
- **Controls are re-measured in-window when conditions may have drifted:**
  JEPA re-ran its control inside the experiment because "the VM ran slower
  during the re-run window" (step counts 129–139 vs the original 154–170 for
  identical configs). Machine-speed variance is a documented, measured fact
  of this lab, not a hypothetical.
- **Records:** every run lands in `runs.jsonl` with arm (flags encoded in the
  label), seed, steps, wall time, held init/final, state bytes; discarded
  runs are kept in `runs-discarded.jsonl` **with the reason**; re-runs after
  restarts are identical-settings and the incident is written into the
  RESULTS file. Drivers skip jobs already recorded and refuse to start a run
  that cannot finish by the hard stop.

## Verdict summary

| # | Area | Verdict |
|---|------|---------|
| 1a | Held-set leakage, per run | **PASS** |
| 1b | Selection pressure across generations (same 128 windows forever) | **FAIL** — no confirmation set |
| 2a | Comparability of data / eval path | **PASS** (by construction) |
| 2b | Sweep-vs-subprocess parity | **NOT-YET-CHECKABLE** — exact check specified |
| 2c | Baseline freshness & contention symmetry | **FAIL** |
| 3a | Seed discipline at probe and trial | **PASS** |
| 3b | Stored sd convention (gen ≥ 1 champions) | **FAIL** — population sd loosens the bar |
| 4 | Ledger completeness / reproducibility | **FAIL** (4 sub-findings) |
| 5a | Probe promotion bar (Δ ≥ 0.05) | **NOT-YET-CHECKABLE** — noise basis is asserted, not measured |
| 5b | Adoption bar vs the lab's standing rule | **PASS on formula; FAIL on two guards** |
| 6a | Concurrency study design | **PASS** |
| 6b | What the concurrency license actually covers | **FAIL** — trials and baseline outside the verified envelope |
| 6c | Champion-install race under multiple lanes | **FAIL** |

---

## 1. Held-set leakage

**1a. Per run — PASS.** Both execution paths inherit the lab's exclusion by
construction, not by reimplementation:

- `sweep_probe.py` imports `train.held_windows`, `train.held_loss`, and
  `train.offsets` and builds the held set once per batch from the same
  corpus; its per-job loop is a statement-level replica of `train.py`'s
  `main()` (same construction order, same per-job reseeding — see §3a).
- Process-mode probes and all trial seeds run `train.py` itself.
- `held_loss` is eval-only (forces full rounding via `EASE`, restores it);
  no training path in `train.py` reads the held windows. No probe, verdict,
  or promotion step in `screen.py` feeds held performance back into any
  training data — verdicts only gate queueing.
- Watch item, currently safe: pool entries MILL-406/407 (failure-weighted
  sampling, flag `--failweight` not yet implemented) specify scoring
  **training** windows only. When that flag is implemented, the audit
  requirement is that scoring/sampling composes with `offsets()`'s
  exclusion — held windows must never be scored, sampled, or counted in the
  "worst decile". Re-check at implementation time.
- Watch item: MILL-218/219 (modal readout) report both readouts' held loss
  from one run; that is measurement, not leakage, but the readout choice
  must be adopted (if at all) through the trial stage, never picked
  per-run by held loss at probe scale.

**1b. Across generations — FAIL.** The mill automates champion replacement
against the **same 128 windows, indefinitely**: every probe verdict, every
trial, and every generation's new reference is a selection event on one
fixed set. The lab's tradition accepted this for a few dozen hand-run arms;
the mill scales it to 176 entries × unbounded generations, with each new
champion's reference itself selected on the same windows. Nothing in
`screen.py`, `PROMOTE.md`, or the pool provides a confirmation measurement
on disjoint data.
**Fix:** define a confirmation set now — e.g. windows at every-40th block
offset by 20 (disjoint from the held set by construction), never used for
probes or verdicts. Before any gen ≥ 1 champion's reference is used to
judge further work, confirm it once on that set (one 8-minute run per
generation): the champion must not lose to its predecessor there. A
champion that wins on the held set and loses on the confirmation set is
the signature of selection overfitting and must be reported, not silently
installed.

## 2. Comparability

**2a. Data and eval path — PASS.** Same corpus file, same held windows,
same sampler, same batch/CTX defaults, same `held_loss` for baseline,
variants, and trials, in both modes. The sweep's reason to exist (pay
startup once per batch) does not change the per-job training budget: in
both paths the 75-second clock starts after construction and the held-init
eval, exactly as in `train.py`'s `main()`.

**2b. Sweep-vs-subprocess parity — NOT-YET-CHECKABLE.** The design asserts
the sweep loop replicates `main()`; nothing yet proves the two paths
produce the same numbers for the same config, and every sweep-mode verdict
is compared against job zero while process-mode verdicts are compared
against a **sweep-measured** job zero (`measure_baseline` always uses the
sweep path). There is a free, exact invariant for the first pass:
**any seed-0 run of the champion config must report `held_init` = 8.3138**
(the value recorded in `runs.jsonl` for `layered_half_rope` seed 0, and
matched exactly by the JEPA smoke test). Check on the first pass:
(1) sweep job zero's `held_init` == 8.3138 exactly — if not, the sweep's
init/stream replication is broken and no sweep verdict stands;
(2) one process-mode run of the champion config at probe budget, compared
against sweep job zero's `held_final` — must agree within the solo
replicate spread the concurrency bench measures. Until (1) and (2) are
recorded, cross-mode verdicts are provisional.

**2c. Baseline freshness and contention symmetry — FAIL.**
Two asymmetries, both consequences of the lab's documented machine-speed
variance:

- *Job zero is measured once per generation* (`screen.py` `ledger_state` /
  `measure_baseline`), solo, at generation start — then used to judge
  probes run hours or days later under different machine load, with
  wall-clock budgets. The JEPA record is the lab's own precedent that this
  drift is real and material (identical configs, 129–139 vs 154–170 steps);
  its response was an in-experiment control re-run. **Fix:** re-measure
  job zero at the start of every pass (cost: 75 seconds) and judge that
  pass's probes against the freshest baseline; ledger every baseline
  measurement (the schema already supports multiple `baseline` lines per
  generation — `ledger_state` takes the last). At minimum, re-measure
  when the stored baseline is older than the pass by more than an hour.
- *Under workers > 1, the baseline is measured uncontended while probes
  run contended.* `main()` measures job zero **before** lanes spawn; lanes
  then share 1.5 vCPUs, so each probe's wall-clock budget buys fewer steps
  than the baseline's did. Deltas are biased against variants (conservative
  for false promotions, corrosive for true ones) — and the same asymmetry
  applies in reverse to trial seeds judged against a champion reference
  measured in a different contention regime (see §6b). **Fix:** either
  measure job zero inside a lane under the same worker count as the
  probes it judges, or restrict verdict-bearing runs to the solo setting
  until the contention effect at probe budget is itself measured (the
  bench measures it only at 0.75 min — §6b).

Minor: `run_sweep_batch(jobs, omp, deadline)` accepts a `deadline` it
never uses — a hung sweep batch hangs its lane past the pass cap. Wire
the deadline to a kill, or drop the parameter so nobody believes it works.

## 3. Seed discipline

**3a. The discipline itself — PASS.** Probes are seed 0 in both paths
(hard-coded in `run_subprocess_probe` and in the sweep job dicts), and job
zero is seed 0 — so every probe verdict is a **paired** comparison: same
seed → same init and same batch stream as the baseline, per `train.py`'s
construction. That is the strongest comparison this lab's machinery
supports at one seed. Trial seeds are the fixed trio (0, 1, 2), recorded
per seed in `trials.jsonl`. A lucky probe seed cannot fake an adoption: it
can only buy a 3-seed trial, where the mean must clear the adoption bar.
Residual risks, stated plainly: (i) seed 0 is never rotated, so an idea
that is genuinely good but unlucky on seed 0 is ledgered and dead for the
generation — a throughput cost, not a correctness one; (ii) all trials and
all champion references share the same seed trio forever, a mild
selection channel that compounds §1b.

**3b. The stored spread — FAIL.** `screen.py:462` computes a trial's sd as
population sd (÷ n). Every spread in the lab's records is sample sd
(÷ n−1) — verified numerically against RESULTS-ROPE and the 2026-11-11
sweep (§Yardstick). Gen 0's reference (2.8580 ± 0.0161, stored in
`DEFAULT_CHAMPION`) uses the lab convention; every champion the mill
installs will store the smaller population value, so the 2 sd component
of every future adoption bar shrinks by a factor of √(2/3) ≈ 0.82 — the
bar quietly loosens by ~18% wherever 2 sd > 0.01 (e.g. a champion with sd
0.030: bar 0.049 instead of 0.060). **Fix:** divide by (n−1) at
`screen.py:462` (and anywhere else a spread is computed for the record).

## 4. Ledger completeness — FAIL (four sub-findings)

A probe line (`ledger_probe`) carries: id, gen, kind, run string, mode,
held, steps, wall_s, probe_minutes, Δ vs baseline, verdict, ts. Joined
with the pool entry and the `runs.jsonl` record (both modes append there —
sweep included), most of a run is recoverable. Four gaps break full
reproducibility:

1. **No code version anywhere.** Neither the ledger nor `trials.jsonl`
   records any fingerprint of `train.py` / `screen.py` / `sweep_probe.py`.
   This lab edits `train.py` between — and historically *during* —
   campaigns (the half-control record notes a parallel job extended the
   Layered trainer mid-window), and the pool's whole purpose is adding
   flags over time. Two probes of the same id under different code are
   indistinguishable in the ledger. **Fix:** add `code_sha` (sha256 of
   `train.py` + `sweep_probe.py` + `screen.py`, or the invoked file per
   mode) to every ledger and trial line; add the corpus fingerprint
   (size + sha256 of `corpus.u16`, or its recorded `corpus_pieces` plus
   mtime) to baseline lines.
2. **The seed is implicit.** Probe lines omit `seed` entirely (it is 0 by
   code convention today). The lab's `runs.jsonl` records seed on every
   line. **Fix:** write `"seed": 0` on probe lines and the champion's
   config snapshot (run string + gen) on trial lines, so a line is
   self-describing without reading `screen.py`.
3. **Deferrals leave no durable trace.** Entries whose flags don't exist
   yet are counted in a lane's return value (an ephemeral log line) and,
   per the pool's design, never ledgered. An auditor working from the
   ledger cannot reconstruct what was skipped or why — the lab's standard
   keeps even discarded runs, with reasons (`runs-discarded.jsonl`).
   **Fix:** append one `kind: "deferrals"` line per pass per generation
   (ids + reasons), or a line per deferred id. Cheap; makes the ledger
   the complete record PROMOTE.md claims it is.
4. **Error-verdict probes are benched for the generation.** `ledger_state`
   counts any `kind == "probe"` line as done, including `verdict:
   "error"` lines (crashes, argparse rejections). One transient failure
   permanently removes an idea for the generation, indistinguishably from
   a measured result. This compounds a real drift hazard: `sweep_probe.py`'s
   argument parser is a frozen copy of `train.py`'s — when a new flag
   lands in `train.py`, `screen.py`'s validation (which reads the real
   `--help`) will pass sweep entries using it, the sweep parser will
   reject them, and they will be error-benched. **Fix:** treat
   `verdict == "error"` as not-done (retry next pass, cap at 3 attempts,
   then ledger an explicit `benched` line); generate the sweep parser
   from `train.py` rather than copying it, or have the sweep validate
   against `train.py`'s parser at startup.

Also: trial `seed` events in `trials.jsonl` record only `held` — no
steps, no wall time. They are recoverable from `runs.jsonl` only by
reconstructing the derived arm label (`…_mill<id>trial`), which is
fragile. Copy `steps` and `wall_s` into the seed event.

## 5. The promotion bar

**5a. Probe bar (Δ ≥ 0.05 → trial) — NOT-YET-CHECKABLE, with a required
measurement.** PROMOTE.md's rationale is that probe noise at 75 s is "much
larger" than the full-format sd of 0.0161, so the bar is set loose on
purpose and the trial does the judging. The funnel logic is sound — a
loose screen cannot create a false adoption, only a wasted 24-minute
trial — but the noise figure it rests on **has never been measured**: job
zero has never been run at probe budget, on any seed, and the concurrency
bench's replicate spread is same-seed (it measures machine-timing noise,
not seed noise). Until probe noise is a number, nobody can say whether
0.05 is 3σ (a real screen) or 0.5σ (a coin flip that promotes ~a third of
the pool and drowns the trial queue). **Required before the first
generation's verdicts are trusted:** measure job zero at probe budget on
seeds 0, 1, 2 (three 75-second runs) and record the spread in
`CONCURRENCY.md`'s sibling — a `mill/PROBE-NOISE.md` or a ledger baseline
set; then confirm Δ = 0.05 ≥ 2 × that spread, or adjust PROMOTE_DELTA and
say so in PROMOTE.md. Note the asymmetry the current design accepts: with
one seed and a loose bar, false *negatives* (good ideas flat on seed 0)
are the silent cost — §3a (i).

**5b. Adoption bar — formula PASS; two guards FAIL.**

- *Formula:* `screen.py` adopts iff `mean < ref_mean − 2·ref_sd` AND
  `mean < ref_mean − 0.01` — exactly the standing rule, and PROMOTE.md's
  worked gen-0 threshold (2.8258) matches round 2's. ✓ (Subject to the
  §3b sd-convention fix for gen ≥ 1 references.)
- *Missing per-seed guard:* the lab's verdicts never rested on the mean
  alone — round 2 argued seed-by-seed non-overlap, and JEPA's
  pre-registered rule required ≥2 of 3 seed wins. The mill adopts on the
  mean only: a candidate with seeds [−0.09, −0.09, +0.05] relative to the
  champion could adopt while losing outright on one seed. **Fix:** add
  the JEPA-style guard to the adoption test — at least 2 of 3 trial seeds
  must individually beat the champion reference mean.
- *PROMOTE.md's own staleness guard is unimplemented:* PROMOTE.md states
  that if the champion reference is stale ("different corpus, or older
  than the trial by a lab change"), the champion config is re-run as the
  trial's fourth job and the reference updated first. `screen.py`
  implements no staleness check and no control re-run — it cannot, since
  nothing records the corpus/code fingerprints a check would compare
  (§4.1). As written, adoption can proceed against a reference the doc
  itself would call stale. **Fix:** implement the fourth-job control
  (champion config, same 3 seeds, same window as the candidate's trial;
  adopt only against that fresh reference), or implement fingerprint
  comparison plus a forced control re-run on mismatch. Until one exists,
  PROMOTE.md's sentence should be treated as aspirational, and any
  adoption that follows a `train.py` change should be hand-checked
  against a fresh champion run — the JEPA precedent.

**Exceptions list (PROMOTE.md) — partial FAIL.** The listed exceptions
(MILL-111/112, 118, 120–122, 129, 137/138) "go to trial on a human's
word", but no mechanism exists: `screen.py` queues trials only on
`verdict == "promote"`, ledger lines carry no exception flag, and no
documented procedure tells the human how to queue one (the `trials.jsonl`
`queued` event format is discoverable only by reading `queue_trial`).
A flat exception-listed idea is indistinguishable in the ledger from a
dead one. **Fix:** tag exception ids in their ledger lines (parse the
list into `screen.py` or add an `exception: true` key to those pool
blocks) and document the manual queueing procedure in PROMOTE.md.

## 6. Concurrency

**6a. Study design — PASS.** `bench_concurrency.py` refuses a busy lab,
drops a marker `screen.py` yields to, writes **nothing** on any abort (the
interim setting stays 1 — the solo condition every existing lab number was
measured under, and `CONCURRENCY.md` says so honestly), measures a solo
replicate to set a noise floor, requires per-config concurrent results
within max(2 × replicate spread, 0.02) of the solo mean, and requires a
≥10% throughput gain per added worker. `screen.py` defaults to 1 worker
unless a completed study's `concurrency.json` exists. This is the lab's
"measure it, don't assert it" standard applied to the mill itself.

**6b. Coverage of the license — FAIL.** The study, when run, will verify
honesty for **0.75-minute sweep probes only**. The setting it writes then
governs, with no distinction in `screen.py`:
(a) 1.25-minute production probes (different step counts, different
contention profile);
(b) **8-minute trial seeds** — the runs that decide adoptions — executed
inside lanes while sibling lanes probe (see §2c);
(c) a baseline measured solo (§2c).
The tolerance floor of 0.02 in the honesty test is also an asserted
constant, not derived from measured probe seed noise (§5a) — if true
probe noise is larger, the test is stricter than needed (safe direction);
if the *systematic* contention shift is what matters, two same-seed
replicates cannot see seed-level effects at all.
**Fix (any one, in order of preference):** (1) trial seeds and baseline
measurement always run in the solo setting (workers effectively 1 for
verdict-bearing runs; concurrency for screening only) — this keeps every
adoption under the exact conditions the lab's discipline was built on;
(2) extend the study with an 8-minute trial-format honesty leg before
workers > 1 may run trials; (3) at minimum, record the worker count and
omp setting on every ledger/trial line so later auditors can see which
verdicts were measured under contention. (3) should happen regardless.

**6c. Champion-install race — FAIL.** In `lane_work`, the adoption path
re-loads the champion, tests the bar, appends the verdicts, and then
writes `champion.json` under `Locked()` — but the *check* (that the
stored champion is still the generation the trial belongs to) happens
outside the lock, and the write does not re-verify the generation. Two
lanes finishing gen-g trials in the same pass can both adopt: both write
generation g+1 with different configs, the later write silently wins,
`trials.jsonl` records two adoptions, and one champion is lost without a
trace. Low probability per pass (requires two 3-seed trials completing
and passing in one pass), unbounded passes to happen in. **Fix:** move
load + generation check + write into a single `Locked()` section; adopt
only if the current generation still equals the trial's generation,
otherwise ledger the trial as `superseded` and let the next generation
re-queue it. (The claims system itself — flock-guarded, pid-liveness,
per-(id, gen) keys — is sound; one residual: a recycled pid can make a
stale claim look live and stall an entry for a pass. Add a claim
timestamp and treat claims older than the longest possible job as stale
regardless of pid.)

---

## First-pass checklist (run when the mill first runs)

1. Sweep job zero `held_init` == **8.3138** exactly (§2b).
2. Process-mode champion-config probe vs sweep job zero `held_final`:
   agreement within the bench's solo replicate spread (§2b).
3. Job zero at probe budget on seeds 0/1/2 → probe noise number →
   PROMOTE_DELTA sanity (§5a).
4. One full pass with the ledger inspected by hand: every probe line
   present, deferral count reconciled against the pool, no error-benched
   ids (§4).
5. If the concurrency study has run: confirm `concurrency.json`'s ts and
   that no `train.py` change postdates it (§6b).

## Bottom line

The mill's skeleton is the lab's discipline, faithfully carried:
paired-seed probes, a pre-registered judge, the adoption bar copied
exactly, preemption of heavier work, and a concurrency setting that
refuses to exist before it is measured. The failures are at the seams
where automation outruns the hand-run habits it inherited: a baseline
measured once and trusted for days, a fixed held set asked to survive
unbounded selection, spreads recomputed under a different convention,
records that omit the code version in a lab that edits its trainer
mid-campaign, and a concurrency license that covers the cheap runs while
the expensive, verdict-bearing ones run outside the verified envelope.
Each has a named, small fix above. None requires redesigning the mill;
all of them are cheaper to make now, before the first generation's
verdicts are on the record, than to retrofit after.
