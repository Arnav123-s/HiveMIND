# Agents working on HiveMIND

More than one agent works on this repository at once, from different accounts and sessions that cannot message each
other. This file is how they stay out of each other's way. **Read it before starting; add a line to the log when you
start, change what you own, or stop.** Pull requests and their descriptions are the other place to look.

## Who owns what (claim before you change; ask in the log to take something over)

| Agent | Branch | Pull request | Owns now |
|---|---|---|---|
| A (Claude, session nice-bell) | `claude/nice-bell-8a5dm4` | #56 | What a member's program runs in and the member loop: `team/tools/sandbox.py`, `team/solo.py`, `tests/test_given.py`; reading each generation's results; `docs/LOOP.md`, `docs/loop_log.csv` |
| B (second agent) | (its own `claude/...` branch) | | Free to claim, for example: training (`training/grow.py`, `training/merge.py`), teaching the hive to talk (`team/talk.py`, `training/raw.py`), speed of answering (`team/ternary.py`, `docs/KERNELS.md`) |

Files nobody owns (`.github/workflows/grow.yml`, `cells/body.json`, `training/reports/*`, `NEXT_SESSION.md`,
`README.md`): change in small commits, merge `main` into your branch first, and say what you changed in the log.

## Shared rules

- **The line of generations on `main` belongs to nobody.** Do not cancel a run of "The hive teaches its own members"
  on `main`, and do not start one while one is running (they queue on one group). Trials on your own branch are fine.
- **Before a trial, list the artifacts of the run you point it at** (`cells_from_run` must name a run that trained).
- **Merge to `main` only with the owner's go-ahead,** after the tests pass and a real run shows the change works.
  Merge `main` into your branch before asking.
- One branch and one pull request per agent; never push to another agent's branch.
- `cells/body.json` and `training/reports/generations.jsonl` are written by the workflow's record job. Do not hand-edit
  them; a local test that changes them restores them afterwards.
- How to find faults, how to test, what is approved: `NEXT_SESSION.md`. How agent A runs its cycles: `docs/LOOP.md`.

## Log (newest last; one line each: when, who, what)

- 2026-11-15 21:30 UTC, A: started from `main` at g27. PR #56 makes members' programs find given data as files, saves
  modules asked for, says where a missing JSON key is, joins site-less links, catches loops on one page, stops
  programs at 3 GB. Waiting on a re-sit of g27's exam and trial run 43762030863. Generation 28 is running on `main`.
- 2026-11-15 21:55 UTC, A: read B's PR 57 and merged main in (clean, 273 tests pass). Fixed B's open finding
  `lookadvice`. One pass over 132 tasks of g28's practice and the trial found six more causes in the web and JSON a
  member meets, all fixed in PR 56 and written into `docs/knowledge.json`. Trial run 32 re-sits g27's seeds with
  them. Still mine: `deaths`, `files`. The largest open cause is reasoning (members disagree or agree on a wrong
  answer: 45 of 77 failures), which is training's: B's, if B wants it.
