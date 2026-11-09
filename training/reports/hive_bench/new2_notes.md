# Hive bench "new2": notes

All 16 development tasks again, started at commit 1524c31 with every fix from the "new" run. **12/16 pass** with the
checks as they stand now (`--recheck`: the arxiv check was made stricter after this run and its pass became a fail).

What to discount, found after the run:
- **percent (pass) is not a clean pass**: the calculator's prompt carried this very task's numbers as its example
  ("17.5% of 2340"), removed in 6fd5f40. Re-run in `new3`.
- **units (fail)** came from the same leak: the 1.7B copied the example into an unrelated task.
- **quotes (fail)** never ran: it started while I was in the middle of an edit (ImportError); the bench ran from the
  working tree. The held-out run and `new3` run from a frozen copy of the code.
- chart, quotes and csv are dev tasks whose specific entities were in older member training data (the browser's,
  coordinator's: training/reports/hive_bench/contamination.json); they are development tasks, but their passes are
  not evidence of generalisation.

Fixed after this run: arxiv (the researcher lists spare candidates, so one rejected paper does not leave two; the
checklist keeps "with their titles and dates"), csv (the coder sees the listing the task names and that it has more
pages), units and percent (the prompt leak).
