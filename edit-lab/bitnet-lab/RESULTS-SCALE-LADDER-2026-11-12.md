# Muse's work — written by Muse, on Muse's side. Fable's side was read read-only; nothing on Fable's side was touched.

# Scale ladder — final record, 2026-11-12

Question (Arnav's, 2026-11-12): does the champion recipe — **layered + rotary +
plain votes** (`layered_rope` arms) — get better **per byte** as the model grows?

This is the ladder's final record as it stands. It is a write-up from records
on disk only; no training was run for this record.

Sources, verified for this record:

- `runs.jsonl` — the recorded runs (the source of truth for completed runs)
- `ladder-driver.log` — the driver's own log (attempts, failures, timeouts)
- `run_scale_ladder.py` — the 12-job ladder definition and job order
- `scale-next/NUMBERS.md` — sizing, serving-bytes accounting, and budgets
- `scale-next/CONFIRM-PLAN.md` — the confirmation mechanism (§6 below)

## Method — equal tokens, every rung

- Every ladder run: **56 steps = 458,752 tokens** (batch 32 × seq 256 =
  8,192 tokens/step), identical for every rung.
- Same corpus throughout: **corpus v1, 5,917,236 tokens** (`corpus_pieces`
  in every record). A ladder run sees 7.75% of the corpus.
- Same held set throughout: the standard fixed 128 held windows.
- Recipe unchanged across rungs: layered + rotary + plain votes. Only the
  shape changes.

| Rung | Shape (dim × layers) | Ternary weights | Total params |
|---|---|---:|---:|
| 2M | 288 × 2 | 1,990,656 | 3,252,096 |
| 10M | 512 × 3 | 9,437,184 | 11,686,400 |
| 50M | 768 × 7 | 49,545,216 | 52,958,976 |

Ternary arithmetic: 12 · L · dim² per rung, per `NUMBERS.md` §0 — it
reproduces every `total_params` value in `runs.jsonl` exactly.

## Results — held loss at 56 steps

| Rung | Seed 0 | Seed 1 | Seed 2 | Mean | n |
|---|---|---|---|---:|---|
| 2M | 3.2878 | 3.2649 | 3.2709 | **3.2745** | **3, complete** |
| 10M | 2.9472 | — (partial, see below) | — (never ran) | 2.9472 (single seed) | **1** |
| 50M | — (killed) | — (never ran) | — | — | **0 — UNMEASURED** |

Exact 2M mean, re-derived from `runs.jsonl`: (3.2878 + 3.2649 + 3.2709) / 3 =
**3.27453…**, i.e. 3.2745 to four decimals (sample sd 0.0119). Walls for the
2M seeds: 287.7 / 281.0 / 281.1 s (mean 283.3 s, 5.06 s/step). The 10M seed-0
wall was 722.9 s (12.91 s/step).

> **Rounding note:** `CONFIRM-PLAN.md` quotes the 2M mean as 3.2746;
> `NUMBERS.md` quotes 3.2745. The exact value from `runs.jsonl` is
> 3.27453…, which rounds to **3.2745**. The 0.0001 difference is immaterial
> to every conclusion below, but the record carries the derived value.

### Per-byte framing (per `NUMBERS.md`)

Serving bytes, stated convention: ternary weights packed at 0.25 B/weight +
non-ternary FP params at 4 B/param.

| Rung | Held loss | Serving bytes | Loss / serving-MB | Mech state (2.5 B/ternary w) | Loss / mech-MB |
|---|---:|---:|---:|---:|---:|
| 2M | 3.2745 | 5,543,424 B (5.543 MB; 91.0% FP) | 0.591 | 4,976,640 B | 0.658 |
| 10M | 2.9472 | 11,356,160 B (11.356 MB; 79.2% FP) | 0.260 | 23,592,960 B | 0.125 |
| 50M | — | 26,041,344 B (26.041 MB; 52.4% FP) | — | 123,863,040 B | — |

The 2M → 10M gain is **−0.3273 held loss (−10.0%)** for ×2.05 serving bytes
(1.78 MB per 0.1 loss, serving convention) or ×4.74 mechanism bytes
(5.69 MB per 0.1 loss, mech convention). Quote loss-per-byte with its
convention attached, always — at these rungs serving bytes are mostly the
FP embedding, not the ternary body (the token embedding alone is 85.1% of
the 2M rung's serving bytes and 73.9% of the 10M rung's).

## Verdict

**VERDICT: 10M is the provisional winner (n=1) over 2M (n=3) at equal tokens — held 2.9472 vs 3.2745, and better per byte under both accounting conventions in `NUMBERS.md`. 50M is unmeasured. The verdict is provisional until CONFIRM-PLAN Set A lands.**

## What did not complete — the full confession

The ladder planned 12 jobs (`run_scale_ladder.py`, in order: 2M ×3,
10M ×2, 50M seed 0, plain+rope 2M ×3, the 0.9M calibration, then the extra
seeds 10M seed 2 and 50M seed 1). Only 4 of the 12 landed as completed runs
in `runs.jsonl`. The rest, exactly as the driver log records them:

### 10M rung — one complete seed, one partial, one kill, one no-show

- **Seed 0 — complete:** held **2.9472**, 56/56 steps, in `runs.jsonl`.
  The driver log shows it was started twice: a first attempt at 02:17:19Z
  produced no outcome line before the driver restarted at 03:35:46Z; the
  second attempt completed at 03:48:46Z and is the recorded run.
- **Seed 1 — finished SHORT, partial only:** the driver log records
  `done layered_rope_scale10m s1 rc=0` with a RESULT of **39/56 steps,
  held 3.2069, wall 1,554.6 s** (319,488 tokens, not the ladder's 458,752).
  **That RESULT never landed in `runs.jsonl`** — it exists in
  `ladder-driver.log` only. It is reported here as a **partial, not a rung
  measurement**: short on steps and on tokens, it is not comparable to the
  56-step runs and is excluded from the verdict.
- **Seed 1 re-run — killed:** after the driver restarted at 05:04:43Z it
  re-ran seed 1 (not in `runs.jsonl`, so not skipped); that attempt ended
  `rc=-9` at 05:31:56Z with no RESULT.
- **Seed 2 — never ran.** It was the 11th job in the queue; the driver
  never reached it.

### 50M rung — UNMEASURED, excluded, not retried

- **No completed run.** Seed 0 was started at 04:23:15Z and killed
  `rc=-9` at 04:35:31Z, ~12 minutes in, with no RESULT and no entry in
  `runs.jsonl`. Seed 1 (the 12th, extra-seed job) never ran.
- The only other 50M-shape number on disk is a separate 2-step smoke check
  (`layered_rope_smokecheck`, held 6.5932) — not a ladder run, not
  comparable, and excluded from every table above.
- Per the endgame plan the rung is **excluded, not retried**. This record
  confesses 50M as **UNMEASURED**: the ladder says nothing about whether
  the per-byte ranking continues, flattens, or reverses at 50M.

### Ride-along and calibration — never completed

- **Plain+rope at 2M** (`plain_rope_scale2m`, the plain-votes control at
  ladder size/steps): seed 0 **timed out at 894 s** under contention
  (driver log, 04:52:27Z, `TIMEOUT … after 894s`). Seed 1 was started at
  04:52:27Z and produced no outcome before the driver restarted at
  05:04:43Z. Seeds 1 and 2 **never completed**; there is no plain+rope
  entry in `runs.jsonl`. The ladder therefore has no plain-vs-layered
  comparison at scale.
- **Calibration run** (`layered_half` at ladder steps, job 10 — the record
  rung's 0.9M config at the ladder's 56-step budget): **never ran.** The
  driver never reached it.

### The driver died silently, and was not relaunched — by decision

The driver log ends at **2026-11-13 ~07:10Z**, parked in the growth-cycle
window guard — `waiting out the growth-cycle window before
layered_rope_scale50m s0`, repeated from 05:31:57Z to the final line at
07:10:35Z — with no completion line and no error. It died silently there.

It was **not relaunched**, by the endgame executor's recorded decision:
a relaunch would have run the excluded 50M seed-0 job first (it was the
next job the parked driver was waiting on), and the informative remainder
(the plain ride-along, the calibration, the extra seeds) is superseded by
CONFIRM-PLAN Set A (§6). The ladder is closed in this state deliberately,
not by oversight.

## Caveats — read with the verdict

1. **The champion's 2.8580 is NOT comparable head-to-head.** The standing
   champion number — layered_half + rotary, mean held **2.8580 ± 0.0161**
   over 3 seeds (`RESULTS-ROPE-2026-11-11.md`) — came from runs of
   154 / 170 / 168 steps, a mean of 1,343,488 tokens, **~2.93× the ladder's
   458,752-token budget**. It must not be quoted against the ladder's
   56-step numbers as if the budgets matched. (For the same reason the
   ladder's 2M/10M losses look worse than the champion's despite the
   larger shapes — they were given far fewer tokens.)
2. **Big-rung numbers are lower bounds under data starvation.** Every rung
   got the same 458,752 tokens — 7.75% of the corpus. Bigger ternary
   models are more token-hungry, so the 10M figure (and any future 50M
   figure at this budget) understates what the rung does at a fair token
   dose. The ranking at 459K tokens can flip at several million tokens;
   that is exactly what the confirmation runs exist to test.
3. **The 10M comparator is n=1 until CONFIRM Set A lands.** One seed, no
   spread, no seed-sd. The 2M side is n=3 with sd 0.0119, so the 0.3273
   gap is large against the 2M spread — but a single-seed winner is a
   provisional winner, and this record labels it that way everywhere.

## Discrepancies found between the driver log and `runs.jsonl`

- **10M seed 1 partial (the material one):** `ladder-driver.log` holds a
  complete RESULT line for `layered_rope_scale10m` seed 1 (39 steps, held
  3.2069, rc=0) that **has no counterpart in `runs.jsonl`**. Anyone reading
  only `runs.jsonl` sees n=1 at 10M with no trace of the partial; anyone
  reading only the log could mistake the partial for a rung measurement.
  This record resolves it as: partial, log-only, excluded.
- **Attempts with no outcome in either record's terms:** the first 10M
  seed-0 attempt (02:17:19Z) and plain+rope seed 1 (04:52:27Z) were each
  started and then silently superseded by a driver restart — no done,
  timeout, or kill line for either. Their absence from `runs.jsonl` is
  correct (neither completed), but the log alone does not say why they
  stopped.
- **Everything else agrees:** all four completed ladder runs in
  `runs.jsonl` (2M ×3, 10M seed 0) match their driver-log RESULT lines
  exactly — arm, seed, steps, held loss, wall, and weights. The 50M kill
  (rc=-9, no RESULT) and the plain seed-0 timeout (894 s, no RESULT) are
  consistently absent from `runs.jsonl`.
- **Rounding (immaterial):** the 2M mean is quoted as 3.2746 in
  `CONFIRM-PLAN.md` and 3.2745 in `NUMBERS.md`; the derived value is
  3.27453…, i.e. 3.2745. Noted above; no conclusion is affected.

## What happens next

- **CONFIRM-PLAN Set A is the confirmation mechanism:** 10M vs 2M at
  **280 steps (2,293,760 tokens, 38.8% of corpus) × 3 seeds each**,
  same recipe, same held set — ~4.2 h of VM time (~1.2 h at 2M + ~3.0 h
  at 10M, per `NUMBERS.md`). Its pre-registered decision rules
  (`CONFIRM-PLAN.md` §3) decide whether the ranking holds, flips, or has
  saturated, and which shape the overlap program builds its members at.
  Set B (448 steps × 3 seeds) is staged behind a checkpoint after Set A.
- **Gate 0 fires independently at the 2M shape.** It does not wait for
  Set A and is not gated by this verdict (see `scale-next/GATE0-READY.md`:
  READY TO FIRE on corpus v1, labeled). The overlap smoke waits for both
  Gate 0 and Set A/B.
- **50M stays excluded** unless a separate decision revives it; its
  confirmation as specified in `CONFIRM-PLAN.md` §4 is not runnable as
  single jobs on this VM in any case.

---

Records: `runs.jsonl` (arms `layered_rope_scale2m`, `layered_rope_scale10m`).
Events: `ladder-driver.log` (also mirrored in `sweep.log`). Driver:
`run_scale_ladder.py`. Sizing/per-byte: `scale-next/NUMBERS.md`.
Confirmation: `scale-next/CONFIRM-PLAN.md`.

---

# ADDENDUM — continuation after this record's 07:10Z snapshot

**Also Muse's work, Muse's side** — appended 2026-11-13 ~10:00Z by the
subagent tasked with resuming the ladder, to reconcile this file with
work that ran in parallel with (and after) the endgame write-up above.
Nothing above was edited; where the addendum and the record differ, the
addendum is the later state of the lab.

1. **The driver WAS relaunched, twice, and the queue was then continued
   manually.** A second driver instance (05:04:43Z) re-ran 10M seed 1
   (SIGKILL, rc −9, 05:31:56Z — the "Seed 1 re-run — killed" entry
   above) and then parked in the growth-cycle window guard until a
   runtime restart killed it (~07:10Z — the silent death above). A
   third instance was launched detached at 07:35:07Z; it spent **85
   minutes in the busy-wait** on back-to-back `python -m team` exam
   sittings without launching a single job, and was stopped at 09:01Z.
   The remaining jobs were then run manually, one at a time, with the
   driver's exact `train.py` invocations (noted in `ladder-driver.log`).
2. **Correction — the 10M seed-1 partial.** At the resume point the
   39-step RESULT (held 3.2069) **was present in `runs.jsonl`**, not
   only in the driver log. It was removed by the resuming subagent to
   permit the redo (the driver's skip logic keys on `runs.jsonl`); the
   original line is preserved verbatim in **`runs.jsonl.bak-pre-s1-redo`**.
   Its status is unchanged: partial, not comparable, excluded.
3. **Two further 10M seed-1 attempts, both killed.** A manual run was
   cut at ~3 min by a runtime restart (no effect, verified); a detached
   rerun was SIGKILLed silently (~09:07–09:26Z, 0-byte job log). Seed 1
   therefore has three failed redo attempts in total and still no clean
   record. Seed 2 was never attempted by the continuation.
4. **Plain+rope seed 0 now HAS a `runs.jsonl` entry — a partial.** The
   manual run recorded **15/56 steps, held 4.8402, wall 727.1 s, mech
   state 2,488,320 B** (12-min cap under peak sibling load; ~45 s/step
   vs ~5 s/step in the ladder's quiet window). It is an attempt record,
   **not** a ladder measurement, and does not change the record's
   conclusion that the ladder has no plain-vs-layered comparison at
   scale. Plain seeds 1–2 and the calibration run were not attempted by
   the continuation; the environment had degraded past the point where
   even the smallest rung could finish (see the 15-step partial).
5. **50M:** the continuation made no further attempt — consistent with
   the exclusion decision recorded above. 50M remains **UNMEASURED**.

**Net effect on the verdict: none.** The completed measurements are
unchanged (2M n=3, mean 3.2745 ± 0.0119; 10M n=1, 2.9472; 50M
unmeasured), and the provisional-winner verdict and its caveats stand
exactly as written above. The continuation's only additions are failed
attempts and one flagged partial, all disclosed here.

