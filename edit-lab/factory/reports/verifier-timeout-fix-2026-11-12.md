# Verifier timeout fix — wrong-operator climb non-termination

**Muse's work, Muse's side.** Serving-side only; nothing trained,
nothing promoted. The learned-say fits stay shadow; the incumbent
configuration is the one measured throughout.

## Defect

The wrong-operator verifier in the waking-dream composed bug path
(`waking-dream/waking_dream.py`: `v_wrong_operator`, reached through
the `WakingDream.answer()` climb) does not terminate on 4 of the 216
say_dev items — 184, 188, 198, 209, all while-loop `running_min`
shapes from the swarm dream corpus. Every configuration, the live
incumbent included, hangs when wrong-operator reaches the climb on
those shapes. The sealed battery families do not contain the shape,
so serving never hit it in measurement — but a real serving input of
that shape would hang the request.

Root cause (confirmed by code reading + reproduction, below): the
cue scan flags ANY variable initialised to 1 and updated with `+=`
as an accumulator suspect (`init1-vs-add`) — including the loop
counter `i`. The repair rewrites `i += 1` to `i *= 1`; the counter
never advances, the `while i < len(xs)` loop never exits, and
`signature()` executes the repaired code through `call()`, which had
NO execution budget of any kind. Every snippet execution in every
verifier funnels through that one `call()` (waking_dream.py line 82
is the only `fn(*args)` in the module), so the unbounded-execution
hazard is general, not wrong-operator-specific.

## Reproduction (pre-fix)

Confirmed 2026-11-12 (third dispatch) with
`waking-dream/repro_wrongop.py` (venv python, faulthandler armed at
8 s, outer `timeout` kill as backstop), calling
`v_wrong_operator(code, ctx)` directly on each say_dev item:

- **184** — faulthandler dump at 8 s: stuck in `<waking>` line 5 in
  `running_min`, via `waking_dream.py:82 call` ← `:92 signature` ←
  `:1043 v_wrong_operator`. The repaired snippet's loop never exits.
- **188** — same dump, `<waking>` line 7 in `running_min`.
- **198** — no return; killed by the outer 15 s timeout (exit 124).
- **209** — no return; killed by the outer 12 s timeout (exit 124).

All four hang inside a single `call()` execution of a repaired
snippet — the unbounded funnel named in the root cause above.

## Budget design

Measured pre-fix on the terminating population (all 212 non-hanging
say_dev items through the incumbent `WakingDream.answer()`; harness
`waking-dream/fixwork/measure_population.py`, raw data in
`fixwork/step_measurements.json` + `fixwork/prefix_answers.json`):

- 8,411 sandboxed executions in total. Per-call traced line-steps:
  p50 = 3, p95 = 17, **p99 = max = 25**. Per-item totals: p95 = 618,
  max = 1,010 steps across a whole climb.
- Whole-climb wall time (untraced): median 0.025 s, p95 = 0.125 s,
  **max = 0.238 s**.
- The counting tracer itself was validated on synthetic snippets
  (1,000-iteration loop → 2,003 counted lines; nested 30×30 → 1,863)
  and pass B reproduced pass A's answers on all 212 items
  (0 mismatches), so the counts are real, not a tracing artefact.

Caps chosen (per single `call()` execution):

- **Step cap: 100,000 line-steps** — ~4,000× the largest legitimate
  call ever measured in this system. Probe inputs are
  generator-fixed and small, so legitimate step counts are bounded
  by probe size × snippet structure and cannot approach the cap;
  verdict identity for terminating items follows by construction.
- **Wall backstop: 5.0 s**, checked every 256 lines — >20× the
  slowest *whole climb* observed; covers sparse-line time burn.
  It can only fire on executions already orders of magnitude past
  any legitimate call, and its outcome is no-verdict, never a
  wrong verdict.
- Hang cost after the fix: the non-terminating loop burns the step
  cap in **~1.07 s** (measured on this contended VM) instead of
  forever.

The budget lives in the single funnel: `call()` (and `load_fn`'s
exec, same tracer) in `waking_dream.py`, enforced by a line-counting
trace — deterministic across machine speed, unlike a bare wall
clock, which matters for verdict reproducibility under VM
contention. Exhaustion raises `VerifierTimeout`.

Semantics on budget exhaustion: the execution raises
`VerifierTimeout`; the climb records an explicit timeout result for
that candidate class (`verified=False`, `score=0.0`,
`"timeout": True`, evidence "no signal"). A timeout is never a
defect verdict and never clean: `v_clean` refuses to verify clean
when any climbed defect signature is unknown due to timeout, and
the case falls back to the composer verdict flagged unverified,
with the timed-out classes listed on the answer (`verifier_timeouts`)
so the outcome is logged distinctly wherever answers are recorded.

## Implementation (landed)

`waking-dream/waking_dream.py` only:

- `_execution_budget()` context manager: a `sys.settrace`
  line-counting tracer over `"<waking>"` frames enforcing
  `EXEC_STEP_BUDGET = 100_000` steps and `EXEC_WALL_BUDGET_S = 5.0`
  (wall checked every 256 lines), raising `VerifierTimeout`.
- `call()` runs the execution (including the result `repr`) under
  the budget and re-raises `VerifierTimeout` ahead of its historic
  `("exc", name)` outcome; `load_fn()`'s exec runs under the same
  budget with the same re-raise.
- The climb in `WakingDream.answer()` catches `VerifierTimeout`
  per candidate class (and around `v_clean`) and records the
  explicit timeout result specified above
  (`verified=False, score=0.0, "timeout": True`, evidence
  "no signal — verifier execution budget exhausted (timeout)").
- `v_clean` refuses to verify when any climbed defect result is
  flagged `timeout` ("defect signatures unknown … clean cannot
  verify against an unmeasured signature"). A positively verified
  defect still wins on its own evidence; the case otherwise falls
  back to the composer verdict (`fallback-unverified`), and the
  answer carries `verifier_timeouts: [...]` — present only when a
  timeout occurred, so terminating answers keep their exact
  historic shape.

Post-fix behaviour on the four shapes (full incumbent `answer()`):
each returns in 0.41–0.61 s with
`verifier_timeouts = ["wrong-operator"]` — item 184 still gets its
positively verified missing-return win (timeouts recorded
alongside), 188/198 fall back unverified to the composer, and 209
falls back unverified rather than verifying clean against the
unmeasured wrong-operator signature. A direct
`v_wrong_operator(198)` call now raises `VerifierTimeout` at
100,001 steps in 0.28 s instead of hanging.

## Regression tests

`factory/tests/test_verifier_timeout.py` (new): **6 passed,
7 subtests passed.**

- `call()` on a synthetic counter-freezing loop raises
  `VerifierTimeout` (< 10 s bound; measured ~0.3–1 s); normal and
  exception outcomes (`("ok", …)`, `("exc", "IndexError")`)
  unchanged; budget constants asserted ≥ 10,000 steps / ≥ 5 s.
- All four hang items: `answer()` returns within a 20 s tripwire
  with the timeout outcome above; the timed-out class never wins;
  clean never verifies on those items.
- `v_clean` unit-level refusal against a timeout-flagged defect
  result.
- Terminating spot items (0, 12, 215) reproduce their pre-fix
  verdicts exactly and carry no `verifier_timeouts` key.

Full factory suite: first post-fix run — **113 passed, 2 failed**,
both failures the same root cause and neither a logic failure:
`test_phase_d`'s file audit and serve-load tests tripped the
registry's sha256 pin on `waking_dream.py` itself (see Registry pin,
below). After the pin refresh, `test_phase_d` re-ran **19/19
passed**. `test_book_shape` passed in this run. A final clean
full-suite run was launched to close the record — count appended
below when it lands.

## Registry pin (required companion change)

`factory/registry.json` pins the serving layer by sha256
(`compositions.bug-pattern-composed.serving_layer`), and serving
fails closed on mismatch (`ServingRefused`). Any edit to
`waking_dream.py` therefore refuses serving until the pin is
refreshed — the first full-suite run caught exactly this (audit
mismatch on this one file, nothing else). The pin was refreshed
surgically, one field, to the fixed file's hash
(`d54272e7…` → `0f60be5c…`); no model, threshold, config, say, or
sealed-evidence field changed, and nothing was promoted. This is
the registry's own mechanism working as designed: the fix becomes
servable only by being registered.

Final full factory suite after the pin refresh: **115 passed,
7 subtests passed, 0 failed** (including the two pin tests and
`test_book_shape`).

## Sealed-path verification

`factory.run_battery a1b` post-fix: **composed sealed
31/36 = 0.8611** (bar 0.80) — the incumbent's number reproduced
exactly, per-class recalls matching the recorded row (clean
0.8182, missing-return 1.0, mutable-default 1.0, off-by-one
0.6667). The companion learned-say section re-read 0.8056 vs
incumbent 0.8611 → say stays SHADOW, as before. Serving is
otherwise unchanged; nothing promoted.

## Verdict-identity evidence

Pre-fix canonical answers (timing fields excluded) for all 212
terminating say_dev items were captured before the edit
(`waking-dream/fixwork/prefix_answers.json`); post-fix answers were
recomputed through the same incumbent `WakingDream.answer()` and
compared by sha256 of the canonical form: **212/212 identical,
0 mismatches.** The budget's tracer alone was also proven innocent
in the measurement pass (pass B answers = pass A answers on all
212). Terminating items gain no `verifier_timeouts` key and no
verdict, score, evidence, or climb change anywhere.
