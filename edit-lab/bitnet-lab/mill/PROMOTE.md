# PROMOTE — the mill's funnel rules (Muse's work, Muse's side)

<!-- Muse's work — Muse's side of the BitNet lab. -->

One page of law for how an idea travels from the pool to the champion recipe.
Everything the mill does is an application of the lab's standing discipline;
where this page and a RESULTS file disagree, the RESULTS file wins and this
page gets corrected.

## The funnel

```
IDEA-POOL.md (queued)
  -> PROBE    75 seconds, 1 seed (seed 0), standard 128 held windows,
              layered+rotary chassis unless the entry changes the chassis.
              Sweep-mode entries share one data load (mill/sweep_probe.py);
              process-mode entries run isolated.
  -> TRIAL    queued INLINE by screen.py the moment a probe promotes;
              a later pass runs it automatically.
  -> ADOPT    trial beats the bar -> mill/champion.json generation + 1,
              job zero re-measured, the whole pool re-opens under the
              new generation (ledger keys are (idea, generation)).
  -> CONFIRM  gen >= 1 champions only: before the new champion's reference
              may judge any further work, ONE confirmation evaluation on
              the confirmation windows (below) must show its config not
              losing to the predecessor's there.
```

## Probe bar (promotion)

Verdicts are relative to **job zero** — the unchanged champion config at the
same probe budget, **re-measured fresh at the start of every pass** (ledger
kind `baseline`; a pass's probes are judged against that pass's measurement,
never an older one — this VM's speed drifts, and the lab's own record shows
identical configs earning different step counts under different load). Let
Δ = job-zero held − probe held (positive = probe is better):

- **Δ ≥ 0.05 → `promote`** — a full trial is queued inline.
- **0.02 ≤ Δ < 0.05 → `near`** — recorded, no trial. A human may re-probe a
  `near` entry at a longer probe budget; the mill does not on its own.
- **|Δ| < 0.02 → `flat`** — recorded; the idea is done unless it is on the
  exception list below.
- **Δ ≤ −0.02 → `below`** — recorded; done.

Why 0.05: probe noise at 75 seconds is much larger than the full-format seed
sd (0.0161), so the bar is set loose on purpose — the probe is a screen, not
a judge. Its job is to spend 75 seconds killing the bottom of the pool and
passing anything plausible upward; the trial does the real judging. A tight
probe bar would throw away real effects smaller than probe noise.

**Exceptions — a flat probe does NOT kill these** (their mechanisms pay off
outside the probe's horizon or on a different axis; they go to trial on a
human's word, judged by their stated criteria): MILL-111/112 (FP-first split —
pays at longer budgets), MILL-118 (embedding INT8 — a byte-pricing probe),
MILL-120..122 (MoE — must be judged on loss AND speed), MILL-129 (Hadamard —
must survive a speed report), MILL-137/138 (SWA hybrid — meaningless at
ctx 256 without a long-context check). Exception-listed entries are marked
`"exception": true` on every ledger line, so a flat exception is never
indistinguishable from a dead idea. To send one to trial, a human appends
one line to `mill/trials.jsonl`:
`{"event": "queued", "idea": "MILL-111", "run": "<the pool entry's run string>", "gen": <current champion generation>, "ts": <epoch seconds>}`
— the next pass runs its trial automatically under the normal rules.

## Full-trial format

The lab's standing discipline, unchanged: **3 seeds × 8 minutes**, same
corpus, same 128 held windows, recipe-matched. Chassis-changing entries are
controlled against the current champion configuration at the same format —
the champion's recorded reference (`mill/champion.json`: currently
2.8580 ± 0.0161, gen 0) is the control. Trial seeds always run **solo** (one
at a time, OMP/MKL = 2, in the coordinator) — the concurrency setting
governs probes only, so every adoption is measured under the exact solo
conditions the lab's discipline was built on.

**Stale-reference guard (implemented, not aspirational):** a mill-installed
champion's record carries the fingerprints of the moment its reference was
established — `code_sha` (sha256 of train.py + screen.py + sweep_probe.py)
and `corpus_sha` (sha256 of corpus.u16). At judging time, if either
fingerprint has moved, the champion config is first re-run as a **control**
(same 3 seeds × 8 min, solo), the reference is refreshed from that re-run,
and only then is the candidate judged — a ledger line of kind `control`
records the re-run. Gen 0's reference is the lab's recorded one
(RESULTS-ROPE-2026-11-11) and carries no fingerprint; fingerprints begin
with the first mill-installed champion.

## Adoption rule

The lab's existing bar, unchanged: a trial is adopted only if its mean held
loss beats the champion mean by **more than 2 sd AND more than 0.01**
(for gen 0: held mean < 2.8580 − max(2 × 0.0161, 0.01) = **2.8258** — the
same bar round 2 was judged against), **and at least 2 of its 3 seeds
individually beat the champion reference mean** (the per-seed guard: a
mean carried by one lucky seed does not adopt). All spreads the mill
stores are **sample sd (÷ n−1)**, the lab's convention. Adoption is
automatic in the mill (champion.json generation + 1, recorded in the
ledger as kind `trial`, verdict `adopt`; the install — load + generation
check + write — happens inside a single locked section, and a trial whose
generation has already moved is ledgered `superseded`, never silently
overwritten); changing train.py's defaults to match is a lab edit that
follows the adoption, never precedes it.

## Confirmation set (selection-pressure guard)

Every probe verdict, trial, and generation reference is a selection event
on the same 128 held windows; unbounded generations would overfit them.
The confirmation set is the disjoint neighbour: **every-40th blocks offset
by 20** (residue 20, where the held set is residue 0), 128 windows picked
the same way, used for nothing else — never probed on, never a verdict.
Once per gen ≥ 1 champion, before its reference judges further work, the
coordinator runs ONE confirmation evaluation (solo): the new champion's
config and its predecessor's config each get one 8-min seed-0 run whose
training excludes BOTH window sets, scored on the confirmation windows
(ledger kind `confirmation`). The gate passes if the champion's
confirmation loss does not lose to the predecessor's. A champion that wins
on the held set and loses on the confirmation set is the signature of
selection overfitting: the failure is ledgered, the champion's reference
is frozen (passes stop judging), and the result is reported — never
silently installed over.

## Execution + preemption

The mill runs continuously (`mill/run-forever.sh` re-invokes screen.py until
2026-11-15). **The scale ladder and the growth cycles preempt the mill
entirely** — screen.py checks before every batch and stops cleanly between
jobs. Concurrency among mill workers is set by the measured study in
`mill/CONCURRENCY.md`, never by assertion, and it governs **probes only**:
job zero, trial seeds, confirmation runs, and control re-runs always run
solo in the coordinator (workers effectively 1, OMP/MKL = 2).

**Ledger completeness:** every ledger and trial line carries `code_sha`
(the code fingerprint above); run lines also carry their `seed` and the
`workers`/`omp` they were actually measured under; baseline lines carry
the corpus fingerprint. Deferrals are ledgered once per pass per
generation (kind `deferrals`, ids + reasons). A probe that ends in an
`error` verdict is **not** done — it re-queues next pass — and after 3
error verdicts in a generation the idea is benched with an explicit
`benched` line rather than retried forever.

CONCURRENCY: see mill/CONCURRENCY.md (marked line `CONCURRENCY=<n>` there;
interim value 1 — the only honesty-verified setting until the study runs).

## Reporting cadence

Results are **bundled into the lab's regular reports** (the same reports that
carry RESULTS files to Arnav, Slack #all-agenthq, and the laptop) — never
reported per-probe. Surface something early only when (a) a trial ADOPTS a
new champion, or (b) a verdict contradicts a standing claim in the record.
The ledger (`mill/ledger.jsonl`) and trial log (`mill/trials.jsonl`) are the
complete record; reports summarise them, they do not replace them.
