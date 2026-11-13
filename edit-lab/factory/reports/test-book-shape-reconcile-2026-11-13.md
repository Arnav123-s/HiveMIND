# test_book_shape reconciliation — 2026-11-13

Muse's work, Muse's side. Overnight lane: reconcile the stale-count
failure reported against `factory/tests/test_phase_d.py::test_book_shape`.

## Verdict: already passing — nothing changed

The earlier failure no longer reproduces. No file was edited: not the
test, not the registry, no model, serving config, or threshold.

## What the test asserts now

`test_book_shape` no longer expects 5 specialists. The test file carries
its own explanation, written by the niche-expansion wave that adopted
the two new specialists:

> niche-expansion wave 1 (2026-11-13): sec-code-model and
> sql-statement-model adopted through the dual held gate + battery +
> full audit (factory/niche_expansion/records/); the book grows
> 5 -> 7 specialist jobs.

The test asserts `len(reg["specialists"]) == 7` and that both
`sec-code-model` and `sql-statement-model` are present. The live
registry agrees: `factory/registry.json` holds exactly 7 specialists.

## Why the earlier report said it failed

The Gate 3′ run (2026-11-12 ~20:51 PT) recorded the suite at 108
passed / 1 failed, the failure being this test expecting the frozen
count 5 against a registry that already had 7. That was true at that
moment. The niche-expansion wave subsequently updated the test's
expected count to 7 as part of adopting the two specialists, so the
failure was already repaired before this reconciliation ran — which is
also why the verifier-fix run later the same night reported the test
passing in both of its suite runs.

## Suite counts

- Before (Gate 3′ run, 2026-11-12): **108 passed, 1 failed**
  (test_book_shape, stale count 5 vs 7).
- Verifier-fix run (2026-11-12): **115 passed, 0 failed**
  (suite grew by the 6 new verifier-timeout tests).
- This reconciliation (2026-11-13, independently re-run):
  - single test: **1 passed** (test_phase_d.py -k test_book_shape)
  - full suite (`pytest factory/tests/`): **115 passed,
    7 subtests passed, 0 failed** — exact agreement with the
    verifier-fix run's numbers.

## Standing note (no action taken)

The assertion is still a literal count — now 7 instead of 5 — rather
than a shape derived from the registry structure. It is correct today
and the reconcile brief was to change nothing that passes, so it was
left as is. A future specialist adoption will stale it again the same
way unless the assertion is reworked to derive the expected book from
the registry/book structure at that time.
