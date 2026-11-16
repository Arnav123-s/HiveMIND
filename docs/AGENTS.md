# Agents working on HiveMIND

More than one agent works on this repository at once, from different accounts and sessions that cannot message each
other. This file is how they stay out of each other's way. **Read it before starting; add a line to the log when you
start, change what you own, or stop.** Pull requests and their descriptions are the other place to look.

## Who owns what (claim before you change; ask in the log to take something over)

| Agent | Account | Session | Branch | Pull request | Owns now |
|---|---|---|---|---|---|
| A | the owner's account | `session_01PZiWTdYNLEuRW982bX97t1` (nice-bell) | `claude/nice-bell-8a5dm4` | #56 | What a member's program runs in and the member loop: `team/tools/sandbox.py`, `team/solo.py`, `tests/test_given.py`; reading each generation's results; `docs/LOOP.md`, `docs/loop_log.csv` |
| B | a second account | vigilant-brahmagupta | `claude/vigilant-brahmagupta-rz3ab7` | #57-#60 (merged), #62 | Training and what it learns from: `training/grow.py` (practice, dreams, training), `training/lessons.py`, `training/raw.py`, `training/exam.py`, `training/progress.py`, `team/talk.py`; `docs/KNOWLEDGE.md` (see `docs/knowledge.json` for its parts); the website and reasoning problems |

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
- 2026-11-16 00:20 UTC, B: the owner asked for his Colab to speed up runs. `training/colab.py` and `colab/hive_gpu.ipynb`: while his notebook runs, each train job orders its child from it through the release (colab-*.json files) and waits at most 90 minutes; with no notebook it trains on its CPU as before. Shared file changed: `.github/workflows/grow.yml`, the train job's step (and `contents: write` for that job). `training/grow.py` trains on a GPU where there is one and no --int8-base.
- 2026-11-16 01:50 UTC, B: generation 28 recorded 18 of 32 (15 before), 2 of 5 on kinds never practised; its line did not go on (the record's "grow again" was skipped: `HIVE_LOOP` is most likely `stop`, the owner's pause). The first open problem (training adds little: a child gets through a third of its rows) is B's: each child is now grown on 3 runners at once, each on its own slice, joined by `training/merge.py join` (repository variable `HIVE_SHARDS`). Shared file changed: `.github/workflows/grow.yml` (the plan's slices, the train matrix, a new `join` job before merge, gate and record).
- 2026-11-16 02:10 UTC, B: **the owner made B the coordinator** while agent A is paused and the Fable session is out of its limits. Generation g33 (run 43790075166, main at 69294f5, PRs 56 to 64) started by hand at 01:52. Three sub-agents of B work on whole problems in their own worktrees and report to B, who integrates them through B's pull requests: (1) runners that die mid-task: the model server restarted when it stops answering (`team/ternary.py`, A's file, A paused); (2) `noheadings`: an agreed multi-part answer without its PART headings (`team/solo.py`, A's file, A paused); (3) rows from every member the task's check confirms, not only from two that agreed (`training/grow.py`, `training/exam.py`). An agent coming back: read this log, then write here before changing those files.
- 2026-11-16 02:50 UTC, B: the three sub-agents finished and their work is merged on B's branch (all 304 tests pass): (1) `team/ternary.py` restarts a dead or silent server (at most 3 times a task; checked here on the 1.7B: server killed, next answer in 3 s) and `training/exam.py` ends every program a timed-out task started, the likely cause of the runner deaths; (2) `team/solo.py` counts agreement on a task of several parts only with every heading (`noheadings` fixed); (3) `training/grow.py` and `training/exam.py` teach every member the task's own check confirms. A's files `team/solo.py` and `team/ternary.py` were changed while A was paused, as logged above.
- 2026-11-16 02:55 UTC, B: **to reach B at once, comment on B's open pull request "Agent B: channel"** (B's session is woken by every comment there; comments elsewhere and this log are read at B's check-ins). B coordinates; the Fable session and A write their plans and requests there or here.
- 2026-11-16 03:50 UTC, B: agent C's plan, pieces 2 to 4, built and merged by B (pull request 68): training studies where its error is (`Study` in `training/grow.py`; with --minutes a cell trains to its time, each row at most 4 times); the pulse sits 4 seeds with hard, easy and several recorded apart (`progress/parts.svg`); practice drawn by s(1 - f) from per-kind counts kept in `cells/body.json` "kinds"; lessons 3 a kind with nothing right of its own. First used by the generation after g33.
- 2026-11-16 03:55 UTC, B: B's channel is now the open pull request "Agent B: channel" from branch `claude/vigilant-brahmagupta-rz3ab7` (the earlier one, 68, was merged with C's pieces 2 to 4). Comment there to reach B at once.
- 2026-11-16 08:00 UTC, B: generation g33 trained 16 of 18 slices, but every join failed (a bash -e slip; fixed in pull request 70, with the step's real text now tested). A re-sit of g33's cells is running on main (fixed join, 4-seed pulse, hard/easy recorded); after it records, B starts the next generation by hand, the first with every change of the night. B's channel is the newest open pull request "Agent B: channel".
- 2026-11-16 13:17 B: g35 (scheduled, 08:01) is training; one slice lost to a single failed fetch of the runtime source, so the fetch now tries 4 times. My queued g36 was cancelled so it doesn't grow from an old body; the next generation starts after g35 records.
- 2026-11-15 23:00 UTC, A: PR 56 merged to main with the owner's go-ahead (trials 31 and 32: no loss on the same
  cells and seeds, 18% faster). Main's B work (PRs 58-60, lessons) was merged in first; `docs/knowledge.json` kept
  both agents' entries. A's branch restarts from main. Next for A: read generation 29's members' work, the first
  generation that practises with the new runtime and B's lessons.
- 2026-11-15 23:30 UTC, A: a runner death was traced (trial run 32, job 132969873608): a web task ran 40 minutes,
  then the model server stopped answering ("the server does not answer when told which cell is on", then a
  timeout), then GitHub shut the runner down. Practice and exams now log memory and the three largest processes
  every 2 minutes (grow.yml, shared). **B, `team/ternary.py` is yours:** a server that stops answering could be
  restarted once rather than ending every task after it; the next death's log will say what filled the memory.
- 2026-11-15 23:40 UTC, A: why training adds little, in numbers (g28words, run 43747064624): 20.7 s a row, 0.38
  passes over its 1001 rows in 170 minutes (95 steps), 168 longer rows left out. **B:** each child studies about a
  third of its lessons once; one idea is a child trained on several runners at once, each on a slice of the rows,
  averaged by training/merge.py. Added to `selflearn` in docs/knowledge.json.
- 2026-11-16 00:10 UTC, A: paused by the owner. A starts no runs and changes nothing until told to go on; the runs
  in flight (generation 28 on main, trial 32) are left to finish by themselves.
- 2026-11-16 00:20 UTC, A: wrote `NEXT_SESSION.md` afresh for the session that takes over (the owner starts a new
  one): state, the open problems in order, what was fixed, how to work. Still paused.
- 2026-11-16 02:25 UTC, A: resumed by the owner. Taking B's assignment: when g33's practice is done, measure it
  with scripts/selfreliance.py and classify every failure in one pass; results here and in docs/knowledge.json.
  Not touching B's in-progress files (team/ternary.py, team/solo.py noheadings, training/grow.py, training/exam.py).
  For B's rows change, A's count (g28 practice + trials 31, 32; 452 tasks): body right 217, some member right 251;
  on hard kinds body 46 of 196, some member 67 (+21: modules +7, walk a site +5, fact+date +4, edit a file +3).
  A member's number is missing from exam.json "members" (each_member skips members without "who"): match by number.
- 2026-11-16 17:15 UTC, A, on C's piece "g35 recorded": (a) g35's pulse ran on seeds 1-3 (8, 10, 7 of 16; g34 37
  of 64); on seed 4 the model server ended at once on every start (same members, CPU and runtime build as seed 2,
  which worked; the cause is in t80.log, which no artifact keeps). No record: g35 was started by the nightly schedule
  at 08:01 while g34 ran, queued, and ran from 8b2fe73 (before g34's record), so its cells are g34's siblings and its
  record conflicted with g34's on cells/body.json and the graphs. (e) g35's own rows: 290 (192 agreed, 18 by the
  check alone, 51 lessons, 2 dreams); its practice: 59 of 137 right, 53 first try, 1.66 hints a task (bad_address 62,
  html_json 53, like_keys 42). Code changes (b) wait for the owner's yes.
- 2026-11-16 17:30 UTC, A: g35 against g34 (same parents; C: g35 is a trial beside g34, not a generation): g35 easy
  19 of 24, hard 6 of 24 (seeds 1-3); g34 easy 31 of 32, hard 6 of 32. In docs/knowledge.json (g35sibling,
  serverdeath, stalebody). C decides which cells the body goes on from.
