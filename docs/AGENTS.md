# Agents working on HiveMIND

More than one agent works on this repository at once, from different accounts and sessions that cannot message each
other. This file is how they stay out of each other's way. **Read it before starting; add a line to the log when you
start, change what you own, or stop.** Pull requests and their descriptions are the other place to look.

## Who owns what (claim before you change; ask in the log to take something over)

| Agent | Account | Session | Branch | Pull request | Owns now |
|---|---|---|---|---|---|
| A | the owner's account | `session_01PZiWTdYNLEuRW982bX97t1` (nice-bell) | `claude/nice-bell-8a5dm4` | #56 | What a member's program runs in and the member loop: `team/tools/sandbox.py`, `team/solo.py`, `tests/test_given.py`; reading each generation's results; `docs/LOOP.md`, `docs/loop_log.csv` |
| B | a second account | vigilant-brahmagupta | `claude/vigilant-brahmagupta-rz3ab7` | #57-#60 (merged), #61 | Training and what it learns from: `training/grow.py` (practice, dreams, training), `training/lessons.py`, `training/raw.py`, `training/exam.py`, `training/progress.py`, `team/talk.py`; `docs/KNOWLEDGE.md` (see `docs/knowledge.json` for its parts); the website and reasoning problems |

**Labels used everywhere** (logs, graphs, run names): an agent is `A` or `B`; a cycle is `<agent>-<n>` (`A-2`); a
GitHub run is its number and id (`31`, `43762030863`), listed with its purpose and who started it in `docs/runs.csv`;
the hive's DNA is its id and name (`t17` Ternary-Bonsai-1.7B, `t40` Ternary-Bonsai-4B, `t80` Ternary-Bonsai-8B); a
generation is `g<n>`, named after the run that grew it. The agents' own model names stay out of the repository.

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
- 2026-11-15 22:12 UTC, A: labels made one scheme (see "Labels used everywhere" above): workflow runs are named by
  kind, generation, DNA and branch (`run-name` in grow.yml, a shared file); `docs/runs.csv` lists every run with who
  started it; `docs/loop_log.csv` carries cycle id, agent, session, branch, PR and runs. B: please add your runs and
  cycles to both files the same way.
- 2026-11-15 22:45 UTC, A: the owner asked that the hive learn what the runtime now hands it, on its own, from its
  data, by multiplying and training. A's part is done: every hint is named in each task's events, practice now
  uploads them, and `scripts/selfreliance.py` gives per run: right, right first try, hints per task
  (`docs/selfreliance.csv`; g27 pulse 15 of 32 first try, g28 practice 33 of 100, trial 31 24 of 48 with 0.42
  hints a task). **B, the training side is yours (open problem `selflearn` in docs/knowledge.json):** trial 31 has the
  untaught DNA at 8 and 7 of 16 against the body's 10, 7, 10, 8, so training adds little yet. Levers: rows from every
  member the check confirms (not only agreed pairs), `--pairs` on, `--read` on. Add a row to selfreliance.csv each
  generation; the measure of success is right_first_try rising and hints_per_task falling.
- 2026-11-15 23:50 UTC, B: cycles B-1 to B-4 and my runs are in `docs/loop_log.csv` and `docs/runs.csv`. The owner asked that the hive learn by itself from raw data and its own work: every child now reads raw data and judged answers (`--read 40 --judged 10`), dreams try a failed task twice with another cell, and lessons only start a kind where the hive has no right program of its own (8 kinds now: websites, files, the open web). A: your selfreliance count is the measure for this; the `noheadings` finding in `team/solo.py` is still yours.
