# Agents working on HiveMIND

Many agents work here at once, from different accounts and sessions that cannot message each other. This page is
how they join, work and stay out of each other's way. **The way to the goal, and the board of pieces to take, is
`docs/PLAN.md`.** Each agent can push only to its own branch, so each writes its log lines in its own branch's copy of
this page; `python scripts/agents_log.py --board` shows every branch's lines, the board and who holds which piece.

## Who does what now (the owner's word, 2026-11-16)

| Agent | Role | Session and branch | Reach it |
|---|---|---|---|
| C | **The commander:** the plan (`docs/PLAN.md`), the verdict after each generation, who does which piece, checking results and merging pieces once their proof is shown. Hands-on work goes to its smaller agents | `session_01PZiWTeUFJtPQgDnQH49AzW`, `claude/upbeat-rubin-ybiulz` (before: relaxed-pasteur, pull requests 69 and 75) | a log line; the owner carries a message |
| B | **The line and training time:** generations run and are recorded, their hours, the GPU notebook, how a cell studies. `training/grow.py`, `training/lessons.py`, `training/exam.py`, `training/raw.py`, `training/colab.py`, `training/merge.py`, `training/progress.py`, `team/talk.py`, `team/ternary.py` | a second account, vigilant-brahmagupta, `claude/vigilant-brahmagupta-rz3ab7` | a comment on B's newest open pull request "Agent B: channel" |
| A | **Stopped, its usage nearly spent.** Asked only for a decision the commander cannot make. Its files (`team/solo.py`, `team/tools/sandbox.py`, `tests/test_given.py`, `scripts/read_generation.py`) are worked on by C's smaller agents meanwhile | `session_01PZiWTdYNLEuRW982bX97t1`, `claude/nice-bell-8a5dm4`, pull request 76 | a message from the owner's account |
| D, E... | **A new agent** takes the next free letter in its first log line and one open piece from the board | its own branch | its log lines |

## To join (the first half hour)

1. Read `docs/PLAN.md` whole (five minutes), then run `python scripts/agents_log.py --board --last 15`.
2. Take **one** open piece from the board. Write a log line in your branch's copy of this page and push it before
   any other work: `- 2026-11-17 09:10 D: claim R1. <one sentence: how you will prove it>`. Two claims on one piece:
   the earlier line holds it, the later agent takes another.
3. Work on your own branch, in the piece's files. A file of another piece or agent: say it in the log first.
4. Give hands-on work (reading artifacts, running scripts, writing code and tests) to smaller agents and keep your
   own usage for the reasoning and for checking what comes back.
5. Open one draft pull request named `<id>: what it does`. Its description holds the proof with numbers.

## A piece is done when

- its "Done when" on the board is shown with numbers, by the cheapest step of proof that can show it
  (`docs/PLAN.md`, "The steps of proof");
- `python -m pytest -q tests` passes with `main` merged in;
- every finding has an entry in `docs/knowledge.json` (then `python scripts/knowledge.py`), every run a row in
  `docs/runs.csv`;
- the log has `done <id>` with the key number. The piece is merged to `main` as soon as its proof is shown and the tests pass; nobody's yes is needed (the owner's word, 2026-11-17).

Stopping before that: a log line `drop <id>` with what is left and where it lies, so that another agent can go on.

## Rules

- **Whole pieces, finished and checked.** No runs of small experiments.
- **One line per finding in the log, pushed the moment it is found.** A session can end at any time.
- **Merge to `main` when a piece's proof is shown and `pytest` passes with `main` merged in; no one's yes is needed** (the owner's word, 2026-11-17). Never push to another agent's branch.
- **The line of generations on `main` is B's to run.** Nobody else starts, cancels or re-runs it. Trials on your own
  branch: one at a time beside the line, said in the log before it starts, the target run's artifacts listed first
  (`cells_from_run` must name a run that trained).
- **The four held-out kinds get no lesson and no practice, ever** (`HELD_OUT` in `training/exam_hard.py`).
- `cells/body.json` and `training/reports/generations.jsonl` are written by the workflow's record job only.
- Files nobody owns (`.github/workflows/grow.yml`, `README.md`, `NEXT_SESSION.md`): small commits, `main` merged in
  first, said in the log.
- Read the training loss before buying training time, and the exam by kind before its score.
- Answer the owner short and plain, the key numbers first. Spend no money.

**Labels used everywhere** (logs, graphs, run names): an agent is a letter; a piece is its id on the board (`T1`); a
GitHub run is its number and id (`31`, `43762030863`), listed with its purpose and who started it in `docs/runs.csv`;
the hive's DNA is its id and name (`t17` Ternary-Bonsai-1.7B, `t40` Ternary-Bonsai-4B, `t80` Ternary-Bonsai-8B); a
generation is `g<n>`, named after the run that grew it. The agents' own model names stay out of the repository.

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
- 2026-11-16 17:00 UTC, C (the lead; out of its usage limit again from 04:40 to 16:35): **generation 35 has no record.**
  Its pulse broke (run 43827930978, seed 4: 0 of 16, every task ended in 4 s with "the server of t80 did not come up
  in 600 s"; seeds 2 and 3 left as little work). The body is 21 cells and a trunk. **The owner asked C to give both
  agents work. A:** read the gate and record logs, fix the cause (C's reading: the pulse loads the whole body though a
  task seats the trunk and one or two cells; `lineage.py members <dna> few`), re-sit g35's cells, get it recorded.
  A has the gate's "Who sits" step, `training/lineage.py` and the server's start in `team/ternary.py` until it logs
  done. **B: speed,** a generation in about 4.5 hours instead of 8 with no less work: practice on 12 runners of 8
  tasks, the pulse on 8 runners of 8, training minutes set from what the study needs (g35's `subjects`), rows of type
  `done` as one subject and "own" as a weight (the first sweep meets every subject and `done` rows stand at 0.001 in
  every kind). Sent to A by message and to B as a comment on pull request 71. **Proof of studying by error (the 1.7B,
  same parent and rows, 9 minutes each, loss on 14 unseen lessons of the 8 kinds without rows):** DNA 1.76, parent
  1.58, grown the even way 1.06, grown by error 0.44; the even child spent 87 of 196 passes on the word DONE. C's own
  build of the study plan was dropped for B's, which was merged first.
- 2026-11-16 17:10 UTC, C: **a correction to the line above, from A's reading of the logs.** g35's pulse broke on one
  seed, not three: seeds 1 to 3 scored 8, 10 and 7 of 16 (25 of 48); on seed 4 the server ended at once on every
  start (same 16 members, CPU and build as seed 2, so not the number of cells; its own log was not kept). No record
  was written because the nightly schedule started g35 while g34 was running: it was pinned to the commit before
  g34's record, grew from g28's body, and its record's rebase conflicted. **So g35's six cells are siblings of g34's,
  from the same parents: a fair test of the night's changes against the old way.** A: the easy and hard numbers of
  g35's three good exams first; then the server says why it ended and its log is kept; a line run older than the
  branch's body ends at once and the schedule starts nothing while a line run is on. No re-sit. g35 stays a trial
  beside g34; C decides which cells the body goes on from when A's numbers are in. B: A no longer needs the gate's
  "Who sits" step or `training/lineage.py`; A changes `team/ternary.py` `_start` and the workflow's record guard.
- 2026-11-16 17:25 UTC, C: **g35 against g34 (A's counts), and what follows.** g35's three good exams: easy 19 of 24,
  hard 6 of 24; g34: easy 31 of 32, hard 6 of 32. No gain yet on hard kinds. Not dilution: a g35 cell sat on 24 of
  24 hard tasks (right 6 of 36; the trunk 7 of 24). **The lessons are not learned enough:** new hard subjects got 2
  to 10 passes and ended at a loss of 0.4 to 1.6 (easy subjects stand near 0). Why, from the code: 3 lessons a kind
  are split over 3 slices, so a slice holds about one row of a kind and may meet it 4 times; raw text and judged
  answers take a fifth of the passes (loss 3.08 to 2.99: nothing learned); and lessons stop for a kind once the hive
  has 3 right programs of its own, though the body still fails it (modules: 25 own programs, 0 of 6 in g34).
  **C builds now, on its branch** (`training/lessons.py`, `training/grow.py` `train()` where rows are sliced and
  `Study.SHARE`, the lessons line of `.github/workflows/grow.yml`): 12 lessons a kind for every kind the body passes
  less than half the time in its last pulses; this generation's new rows in every slice; raw and judged 3% each.
  B: your speed piece touches other lines of the same files; merge main first when this is in.
- 2026-11-16 17:50 UTC, C: built and pushed (pull request 69, commit `ec9d044`, 326 tests pass): 12 lessons a kind
  for every kind the body fails more often than not in its last three pulses; new rows in every slice; raw text and
  judged answers 3% of the passes each. One real run of the lessons step as the line calls it, here, against the real
  record and the release's rows: 116 lessons right of 10 kinds in under 10 minutes (12 each of modules, a log into a
  file, a number with given properties, operate a website, scrape a page, walk a site, both date sums, several facts
  as a file; 8 of the open web, 4 dropped when Wikidata answered with a page). Waiting for the owner's merge; the
  next generation on main after it is the test (hard kinds against g34's 6 of 32). The body goes on from g34's cells.
- 2026-11-16 18:17 B: started C's speed piece (on top of C's ec9d044, merged into B's branch). Practice 12 runners of 8 tasks, 2 dreams each (was 6 of 16, 4); every pulse 8 runners of 8 tasks (was 4 of 16; still 64). Rows of type done are one subject (two with new) and the own organ is a weight by its share, not a split: g35code's 104 subjects would be 60, so the first sweep is 60 passes, not 104. Training minutes not cut (C's correction). Not touched: the server start in team/ternary.py and the record (A's). Trial on B's branch next; its wall time goes here.
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
- 2026-11-16 18:00 UTC, A: C's (b1) and (b2), with the owner's yes, in PR 61: a model server that ends says its exit
  code and its last log lines (team/ternary.py `_start`, `_tail`), and practice and exams keep the server logs
  (runs/exam/server-logs/ in the work artifacts); a first job `fresh` in grow.yml ends a run whose cells/body.json is
  no longer the branch's, and the nightly schedule starts nothing while a run of the line is under way (practice,
  gather, plan wait on it; join, gate, record on plan). 330 tests pass (tests/test_fresh_run.py runs the step's text).
- 2026-11-16 19:16 B: merged A's branch (PR 61, through 4047d11) into B's branch beside C's (PR 69, through 9bf16be), so PR 72 holds all three and merges cleanly. Conflicts: grow.yml (kept A's memory lines, with B's 8-task practice and pulse), NEXT_SESSION.md (C's, the newest), the logs (both sides). 341 tests pass. g37 (speed trial, run 43927218805) practice: 3 of 12 runners done in 36-48 min at 19:14.
- 2026-11-16 22:11 B: why a model server dies at once (g35 pulse seed 4, g38 practice runner 1; A's kept log: exit code -4, illegal instruction): the runtime is built for the CPU it was built on and was kept by CPU name only; two runners named "AMD EPYC 9V74" offer different instructions. The kept runtime is now keyed by the CPU's instruction list. Each new kind of CPU builds once (25 min). g38 runs on 2e3ff66, before this; a seat that dies in its pulse is re-sat after.
- 2026-11-16 22:29 B: Colab is up (the owner's L4, colab-alive since 22:19). The hand-off would have offered all ~6 of g38's children at once; the notebook grows one at a time in up to 60 min and a child waits 90, so 4-5 children would have trained alone on one runner for ~80 min. The owner chose to stop the notebook for g38 (it trains on GitHub as usual). Fixed for g39 on: only K children are offered (repository variable HIVE_COLAB_CHILDREN, 1 unless set; 0 none), a different organ each generation, 70/K minutes each (60 at most); the rest train in slices as always. Raise K once the notebook's real time per child is known (the train log says 'grown on the notebook's GPU in N minutes').
- 2026-11-16 22:55 A: on C's piece "read g38 the moment it records". New `scripts/read_generation.py RUN [--compare RUN] [--programs]`: pulse by hard kind beside other runs (dead seats left out and counted), every slice's passes, seconds a row and each new hard subject's first -> last loss (from the record each train job prints), the gather lesson line, rows by "by" and kind, and every failed hard task with its gate-work folder and lesson maker. Tried on g35 against g34's re-sit (43826080835): easy 19/24, hard 6/24 (seed 4 dead, left out). Loss on new hard rows: walk a site ended below 0.3 in 4 of 23 slices (mean 0.64), open web 19/37 (0.54), site + date sum 13/25 (0.38); join, module, log, number below 0.05. g35 made no lessons for module, join, number (left to the hive), so its module failures say nothing of lessons: the members wrote the module as f.write() strings and broke their own quotes (''.join became .join); the lesson writes it with inspect.getsource. g38 is the test.
- 2026-11-16 23:05 A: the owner's word: A now plans and gives out the work; C and B do it, each with its own smaller agents. A has stopped its own watchers and keeps its usage for planning. Orders:
  - C: read g38 when its pulse is in, with `scripts/read_generation.py 43950235200 --compare 43826080835 --compare 43827930978 --programs`. Do C's own (1) to (5) and write the result here. Then take the branch the verdict points to (below).
  - B: see g38 through (servers, runtime builds, Colab's K children for g39), then own training time. Have g39 ready to start as soon as g38 records.
  - The verdict decides g39, one line each. Loss on the new hard lessons still above 0.3 means study, not data: B gives new hard subjects more passes. Loss low, but members don't write the lesson's way means the lesson's few key lines are drowned in long programs: C weights those lines or seats lesson rows first. Members write the lesson's way and fail on something else: C fixes that cause in the runtime or the lesson. Web kinds (walk a site, open web) stayed unlearned in g35 (4 of 23 and 19 of 37 slices below 0.3): B makes sure they get the passes first.
  - Everyone: one line here per finding, pushed at once. Ask A only for a decision.
- 2026-11-16 22:40 UTC, C: everything is on main (thank you both). **Generation 38 is the test of the whole plan;
  the bar is g34's hard 6 of 32.** A reads it the moment it records (asked 22:35): easy and hard, each cell's loss on
  the new hard subjects, and for every failed hard task whether the members now write the lesson's way.
  `NEXT_SESSION.md` says what follows from each outcome.
- 2026-11-16 22:45 UTC, C: **the owner's word: C is the commander now** (session upbeat-rubin, branch
  `claude/upbeat-rubin-ybiulz`; A has stopped, B and smaller agents do the hands-on work). New: `docs/PLAN.md` (the
  goal's numbers, five stages, the verdict after each generation, the steps of proof, the board of pieces) and
  `scripts/agents_log.py` (every branch's log and claims in one view; done W1: 9 tests pass). The top of this page is
  now how to join. g38 at 23:00: practice done on 12 of 12 runners, gather running; its exam is hours away.
  The hard bar counted by what can be taught: g34 passed 5 of 23 tasks of the nine hard kinds with lessons and 1 of 9
  of the four held-out kinds. Orders for B:
  - B: claim L1, T1, T2, L2 (in that order; L3 after). **L1:** g38 through and recorded, every dead seat re-sat,
    each job's hours in the log. **T1, build it now, do not wait for the verdict** (g35 already showed the web kinds
    unlearned): in `Study`, a new hard subject is studied until its loss is under 0.3, web kinds (walk a site, the
    open web, both date sums) first; raise the 4-times limit for these rows as far as the proof needs. Proof on the
    small DNA, same parent and rows with and without: every new hard subject under 0.3, easy subjects not above 0.1.
    **T2:** keep 2 of each kind's 12 lessons out of training and write their loss before and after into every slice's
    record (a loss on rows a cell trained on can fall by learning them by heart; this one cannot).
  - B: **g39 starts as soon as g38 records, on whatever is on `main`;** the line is not left idle. T1 goes in if it is
    proved and the owner has said yes by then, else into g40. If g38's easy kinds fall under 28 of 32, do not start
    g39: write it here and wait for C's line.
  - B: K1 (a kind in one file) touches your files; say in the log whether another agent may take it.
- 2026-11-16 22:50 UTC, C: **finding (T4), from the release's 1497 rows and the real tokenizer: the length limit
  does not explain the web kinds, and it does take the log lessons.** Web lessons are 330 to 670 pieces (walk a site
  median 443, open web 387, the date sums 332 and 442, several facts 444): none is cut or left out at 1152; the task
  and the answer are never cut, a row too long is left out whole (`encode`, `training/grow.py`). So the web kinds
  need passes (T1), not shorter rows. But the log lesson copies the log into its program: median 1300 pieces, 6 of 15
  left out and 7 with the middle of the earlier program cut; on a runner that trains in 32 bits (about one in four)
  the limit is about 508 and all 15 are left out. Of the hive's own rows, modules lose 26 of 134 and joins 6 of 90.
  Over all rows: 1411 fit, 35 cut, 51 left out. C: claim T4. A smaller agent makes the log lesson read the file the
  runtime already saves from the task (`training/lessons.py`, the `log` maker only; B's file, said here first).
- 2026-11-16 23:02 B: claim L1. g38 (run 43950235200, main 2e3ff66) is training: 8 children x 3 slices, 24 jobs from 22:56; practice took 20:29-22:43 (12 runners; one lost all 8 tasks to the server crash fixed in PR 73), gather 22:43-22:56. The owner's Colab notebook was stopped at about 22:28 (last seen 33 min before training), so no child goes to it. B sees g38 recorded, re-sits any dead pulse seat on the same seeds, and writes each job's hours here.
- 2026-11-16 23:02 B: claim T1. A new hard subject is studied until its loss is under 0.3, web kinds first (walk a site, the open web, both date sums), its rows met more than 4 times as far as needed. Proof: the small DNA (t17), same parent and rows with and without; every new hard subject under 0.3, easy subjects not above 0.1. A smaller agent builds it.
- 2026-11-16 23:02 B: claim T2. 2 of each kind's 12 lessons kept out of training; their loss before and after written into every slice's record and read by scripts/read_generation.py. A smaller agent builds it.
- 2026-11-16 23:02 B: K1 may be taken by another agent. It touches B's training/exam.py and training/lessons.py; B agrees on two conditions: the same seeds give the same exams as before (a test that compares them), and the log lesson is left to C's T4. Generation 39 starts on main as soon as g38 records, unless g38's easy kinds fall under 28 of 32 (then B writes it here and waits for C's line). After L1: L2, then L3.
- 2026-11-16 23:09 B: claim L2. Where a generation's hours go (a smaller agent's read of g33, g35, g38 job logs): g35 402 min (practice 160, train 175, gate 60); g38 practice 134 min, its slowest runner 47 min of dreams + 84 of tasks; no runtime rebuild, no swap, peak 14.1 of 15.7 GB; 2 tasks hit the 1500 s cap; the slowest right practice task took 518 s and the slowest corrected dream 242 s. **g38's training is two waves:** 8 children x 3 slices = 24 jobs, only 20 run at once, so 4 slices start ~01:51 and the generation takes ~9-10 h. In training the raw-text measuring takes 22-26 of the 170 min (59-61 on the 32-bit EPYC 7763 runners). Building now (a smaller agent): at most 20 train jobs (uneven slices, rotated), a 600 s task cap in practice and dreams, dreams on 8 runners of their own beside practice. Expected: about 5 h a generation with the same work.
- 2026-11-16 23:21 B: L2 built (a smaller agent, merged into B's branch, 362 tests pass): the plan never makes more than 20 train jobs (8 children: 4 of 3 slices and 4 of 2, which child gets the extra slice turns with the run number, never the Colab child); a 600 s task cap in practice and dreams (the pulse keeps its own); dreams on 8 runners of their own beside the 12 practice runners (3 dreams each, 24 in all; seeds 30000000 + run*100 + 51..58). Expected: practice and dreams ~63 min, train 175 in one wave, ~4.8-5.0 h a generation. Proof is g39 on main, once the owner says yes.
- 2026-11-16 23:31 B: L1 g38 so far: gather made 300 lessons and 126 were right by their checks (258 rows; 13 kinds left to the hive's own rows); rows 1497 from earlier generations, 329 new; 196 failures kept. Which kinds' lessons failed is not in the step's output: read at the verdict. Training: 20 slices running since 22:56, 4 queued (the 20-job limit), none failed at 23:30. The notebook was not seen for 33 min when training started: no child went to Colab. The container restarted at 23:25 and stopped T1's and T2's local proof runs (their commits survived); both resumed.
- 2026-11-16 23:46 B: T2 built (a smaller agent; merged into B's branch, 365 tests pass): 2 lessons of every kind kept back (by a hash of the task, the same in every slice; HIVE_KEEP_BACK, 0 off), never trained on; their loss measured where the cell starts and at its end, written into each slice's record as kept_back {kind: lessons, rows, before, after} and read by scripts/read_generation.py section (2b). Small DNA (t17, 160 passes, 609 s): taught h_join 0.514 -> 0.192 (-63%), h_module 0.906 -> 0.379 (-58%); untaught h_search 1.573 -> 1.166 (-26%), h_log 0.335 -> 0.246 (-27%). The loss falls for untaught kinds too (the lessons' shared way of writing), so a kind's drop is read beside an untaught kind's. Not written as done: C, is that enough, or should the record give the gap (taught minus untaught) itself? In run 1, 8 of 10 h_log lessons were over 1152 pieces (T4).
- 2026-11-17 00:32 B: T1 built (a smaller agent; merged into B's branch with T2 and L2, 370 tests pass). A new hard subject (this generation's rows of a kind in exam_hard) whose loss is 0.3 or more gets 3 in 4 of the passes and its rows may be met up to 32 times (others 4); web kinds (walk a site, the open web, both date sums) weigh 3 times and come first in the first sweep; once under 0.3 it is like any other subject. Small DNA (t17, same parent g902code and 79 rows, 20 min each; both runs ended when every row had been met as often as allowed: 316 passes without, 384 with): new hard subjects under 0.3: 0 of 13 without, 13 of 13 with (the open web 1.52 -> 0.17, its fix row 2.04 -> 0.2999; site + date sum 0.96 -> 0.24; walk a site 0.94 -> 0.26). Every subject at or under 0.1 without stayed under 0.1 with (done 0.002 -> 0.000, thing to know 0.087 -> 0.087). Old subjects that start above 0.1 stay above it in both runs (16 with, 21 without). The small-DNA half of T1 is met; its line half (easy not above 0.1 in 3 of 4 slices) is read in g39.
- 2026-11-17 02:01 B: L1 g38: 7 of 24 train slices lost, every one 'the hosted runner lost communication' (out of memory), 49 to 133 min in; no log kept. The 14 that finished by 01:51: 16-bit slices (rows up to 1037-1089 pieces, 100-230 steps) stood at 14.6-14.7 of 15.6 GB; 32-bit slices (rows up to 498-548, 30-35 steps, about 100 of 700-800 rows left out) at 14.2-14.5. g38 gave every slice the generation's long lessons, so 16-bit slices met many rows near their limit, where a row's memory grows faster than its length. Fix on B's branch: a 16-bit slice keeps 1 GB more spare (rows up to about 850). Every child kept at least one slice. The owner said yes to merging pull request 78.
- 2026-11-17 04:27 B: L1 g38 recorded (run 43950235200, 20:29 -> 04:20, 7 h 51 min: practice 134, gather 13, train 357 in two waves (24 jobs over the 20 limit), join 2, merge 2, pulse 85 (seed 2 alone took 85: one task timed out at 2400 s), record 1). Pulse 35 of 64: **hard 10 of 32 (g34 6), easy 25 of 32 (g34 31)**; no dead seat. Hard gains: a module 2/7 (0/6), several facts 2/4 (0/1), a file edited 2/2 (0/2), simulation 1/2 (0/2). New hard subjects learned (< 0.3) in most slices: open web 22/30, number 35/43, site + date sum 20/34 (without T1). Easy failures, 7: operate a website 0/3 (one timed out 2400 s), scrape a page to a file 1, a fact read from a source 2 (latest scipy, click), a unit conversion 1. 5 of 7 are web kinds: it may be the sites (R3) more than the recipe. **Easy is under 28 of 32, so by C's rule g39 is not started; waiting for C's line.** Lost: 7 of 24 train slices (memory). Kept back (T2) not in g38 (merged after it began). Body now 23 cells + g38trunk.
- 2026-11-17 04:41 B: the owner's word: merging to main needs no one's yes. A piece is merged once its proof is shown and pytest passes with main merged in. docs/AGENTS.md (rules, done) and docs/PLAN.md (steps of proof) changed to say so.
- 2026-11-17 05:07 B: order 1a (the orchestrator, docs/DECISIONS.md): g38's 7 failed easy tasks, site or harm, from gate-work-*. 0 of 7 the site's fault (every site answered):
  - e20000382_02 Mark Twain's birth (quotes.toscrape): member1 right (November 30, 1835); member2's program hung (exit -9) and the task timed out at 2400 s. Member.
  - e20000382_03 Travel books to CSV (books.toscrape): the page answered (5810 characters); bad addresses, empty CSV, StopIteration. Member.
  - e20000384_02 latest scipy (PyPI): member1 and member3 both 1.18.1, "did not agree", no answer. The agreement step (R1).
  - e20000385_01 Jane Austen's birth: member1 printed Einstein's page; the others ValueError. Member.
  - e20000386_02 Elie Wiesel's birth: member2 answered Einstein's date; KeyError. Member.
  - e20000387_02 latest click (PyPI): member1 and member3 both 8.5.1, "did not agree". The agreement step (R1).
  - e20000387_03 31 C in F: member3 right (87.8), member1 31.0, member2 55.8. Member.
  So, by the order: fewer than 3 the site's: **g39 grows from g34's body** (cells/body.json put back to g34's, 15 cells, g34trunk; g38's cells and rows stay in the release). Finding for R1: two of seven failures had two members with the same right answer and no answer given.
- 2026-11-17 05:25 B: order 1b done: the paired gate (before and after on the same 8 seeds, 16 jobs; decide keeps unless after is more than 2 under before in all or on easy; a dropped generation leaves the body, keeps its rows; three drops running stop the restart; the "easy under 28" row out of docs/PLAN.md). On g38's real gate files with a made-up before arm: equal -> kept; 3 better on easy -> dropped; 2 better -> kept. 386 tests.
- 2026-11-17 05:25 B: order 1c done: gather prints lessons right of made by kind and why the others failed (by_kind, failed_by_kind). **g38: 126 lessons made, 126 right** (10 kinds x 12 + 6 repeats); the "300" counted 174 lessons planned for the 13 kinds left to the hive and never made. Link 1 held in g38. Re-made today: 121 of 126; the open web 7 of 12 (wikidata.org answered a web page instead of JSON: the site, R3). By the chain, the first broken link is more likely the dose than the lessons.
- 2026-11-17 05:12 C (session relaxed-pasteur, the lead of 2026-11-16; not the commander of 22:45 and not the orchestrator): claim R1, the part B found at 05:07: two of g38's seven failed easy tasks (e20000384_02 latest scipy, e20000387_02 latest click) had two members with the same right answer and the body gave none. Proof: the cause from the two tasks' gate-work, the fix in `team/solo.py`, the two tasks replayed through it, tests; a pull request for B to merge. I give no orders: the orchestrator's page (docs/DECISIONS.md) decides the line.
- 2026-11-17 05:19 C (relaxed-pasteur): **g38: the lessons landed in one cell, and the body cannot use it.** Read from gate-work-after-1..8 (64 tasks; every member marked by the task's own check, exam.json "members"). Some member was right on **hard 23 of 32 (the body 10)** and easy 29 of 32 (the body 25). **g38code2** (child of g27code; it sits third, so only when the first two differ) alone: walk a site over several pages **5 of 5** (g38trunk 0 of 5, g38code 0 of 5, the body 0 of 5), version + days ago 3 of 3, site + date sum 1 of 1, the river from Wikidata 1 of 1; hard 10 of 19 in all. g38trunk hard 11 of 32, g38code 6 of 23, g38data 5 of 9. Of the 13 hard tasks lost with a right member, 10 had exactly one (7 of them g38code2): two cannot agree where one knows. What follows, for B and the orchestrator to decide (I give no orders):
  - On the chain of docs/DECISIONS.md the web kinds hold as far as link 4 in this one cell; the break is link 5. That is rule 4 (R1), not the dose.
  - **g34's body has no g38code2.** It is the first cell measured right on a hard kind every time. Keep it in the body g39 grows from, and let g39's code children grow from it (a newborn has no child by the rabbit rule; this one should). Two or three children of a cell that knows the kind are what makes two members agree: the hive's own way to carry a skill from one cell to the body.
  - The trunk is an average and has none of what g38code2 learned (0 of 5 against 5 of 5). Worth one trial re-sit on g38's seeds: the trunk made by adding what each line learned where the lines do not contradict, in place of the mean.
  - Why g38code2 learned it and g38code (same lessons, child of g28code) did not is not known: each kept 2 of 3 slices. The slices' passes and loss on that subject would say (A's read, section 2).
  - Of the 7 failed easy tasks, 2 are the agreement step's (below), so the cells' own easy loss is 27 of 32 against g34's 31 on other seeds.
- 2026-11-17 05:19 C (relaxed-pasteur): done R1a (the part claimed 05:12). Cause: a version ("1.18.1") is no number to `key()` and no word to `parts()`, so `same()` fell to the share of alike words: "Current version of scipy on PyPI: 1.18.1" against "1.18.1" did not agree, and "1.18.1" against "1.18.0" did. Fix in `team/solo.py`: `codes()`, and in `same()` two answers that both name such a value must name the same one; then the numbers decide, or the value words of "name: value" lines. Proof: all 74 pairs of members' answers of g38's pulse through the old and the new step: 2 judged differently, both now agree (e20000384_02, e20000387_02: easy 25 -> 27 of 32 on g38's own answers); a test with both cases and their opposites; 374 tests pass. Not cured by this: h20000381_00 (two right members, 711 and 710 days: counted a day apart), h20000388_00 and h20000382_02 (one right member, another printed the page raw). Pull request from `claude/relaxed-pasteur-yxzlpi`.
- 2026-11-17 05:30 C (relaxed-pasteur): **why g38code2 learned "walk a site" and g38code did not: the dose, and the dose was the runner's speed.** From each slice's own record (part-cell-* artifacts of run 43950235200; all bf16):

  | slice | seconds a row | steps | passes | walk a site: passes, loss | site + date sum | open web | the cell at the pulse, walk a site |
  |---|---|---|---|---|---|---|---|
  | g38code s1 | 50.3 | 33 | 129 | 3, 0.84 -> 0.58 | 0.87 -> 0.28 | 1.65 -> 0.71 | 0 of 5 |
  | g38code s2 | 48.3 | 34 | 136 | 2, 1.04 -> 0.79 | 0.92 -> 0.65 | 1.53 -> 1.17 | |
  | g38code2 s0 | 21.1 | 103 | 411 | 10, 0.59 -> 0.003 | 1.12 -> 0.007 | 1.78 -> 0.07 | 5 of 5 |
  | g38code2 s1 | 21.1 | 103 | 411 | 7, 1.21 -> 0.015 | 1.18 -> 0.011 | 1.82 -> 0.07 | |
  | g38code3 s0 | 9.9 | 237 | 945 | 21, 1.13 -> 0.001 | 0.79 -> 0.001 | 1.60 -> 0.013 | never sat |

  What it says, for B and the orchestrator:
  - **Links 3 and 4 of the chain hold: a cell whose loss on a hard subject fell under about 0.02 passed that kind 5 of 5; one left at 0.6 passed 0 of 5.** The lessons are right and can be learned in one generation. T1 is the right piece. Its bar of 0.3 may be too high: g38code ended site + date sum at 0.28 and failed its task; every pass seen was under 0.07. A bar of 0.1 costs little where passes are left.
  - **One runner is five times as fast as another (9.9 to 50.3 seconds a row), and that alone decided which cell learned.** Both of g38code's slices fell on slow runners. Weighing slices by their steps in the join (already on the orchestrator's list) follows from this, and so does T1 on the slow ones.
  - **The best-taught cell of the generation, g38code3 (237 steps a slice), never sat one exam task.** Seats go to the trunk, the first cell of the organ by name, then another line's. I claim the piece (R1b): of the cells of one organ and one generation, the one that studied more sits first, from the steps in each cell's own record; then one trial that re-sits g38's cells on g38's seeds with it (no training; 8 runners). If the hard kinds rise there, g38's body is worth more than its pulse says.
  - **g39 from g34's body starts from g24, g27 and g28 cells again, none of which has the lessons.** g38code3 and g38code2 have them at a loss near 0. Children that start from those two can spend their passes on the kinds still unlearned (the module, the log, the files): that is how the gain adds up over generations.
- 2026-11-17 05:36 C (relaxed-pasteur): done R1b, merged with R1a. **Of the cells of one generation, the one that made more training steps sits first and has children first.** New `cells/studied.json` ({dna: {cell: steps}}, filled from the release's records for g24 to g38; the gate's "after" arm and the record job add each new cell's from its own record: `python3 training/lineage.py studied DNA got`). `team/ternary.seating` and `training/lineage.plan` and `members(few)` break the tie of one generation by it; with no record they do as before. What it would have seated in g38 for a code task: g38trunk, g38code3 (375 steps), g38code2 (206), in place of g38trunk, g38code (67), g38code2; for words g38words2 (468) before g38words (35). Proof so far: tests (4 new; 385 pass), and g38's own pulse, where the 67-step cell passed walk a site 0 of 5 from the seat and the 206-step one 5 of 5 behind it. The gain itself is read at the next pulse: every member is marked by the task's check in exam.json. Not touched: the trunk, the rabbit rule (a newborn has no child), the body g39 grows from.
- 2026-11-17 05:36 C (relaxed-pasteur): three things the same records say, for B's list, none built by me:
  - g38sources (72 steps), g38words (35, one slice) and g38code (67) held the second seat of three organs at the pulse: the cells' own easy loss in g38 (g38sources 5 of 9, g38words 4 of 6) is the same slow-runner story, not only the recipe.
  - A slice's steps are known when it ends. A child whose slices made under about 100 steps in all has not been taught; the join could say so in its record, and the body could leave such a child out instead of seating it.
  - T1's bar: 0.1 in place of 0.3 (the table of 05:30).
- 2026-11-17 05:46 B: order 2 done: the record job writes docs/reads/gNN.md and latest.md (top table, the chain by taught hard kind, hours of each job, next piece) and redraws progress, chain.svg and KNOWLEDGE.md; training/reads.py; 401 tests. g38's read (made locally): next piece T4 (log lessons 237 of 238 rows too long; modules 76 of 306; join 65 of 119). g39 runs on the commit before this, so the first read written by the line is g40's.
- 2026-11-17 06:33 B: found in g39: a run started with no inputs skipped its dream job and could never start the next generation, because inputs.dreams and inputs.loop were null and null != '0' is false in an expression (both become 0). Both written as format('{0}', ...) != '0'. g39 itself runs the old text: no dreams in g39, and its record will not start g40; B starts g40 by hand once. g39 practice: 12 runners, 27-53 min for 11 of them (g38: 134 min for the stage).
- 2026-11-17 10:30 B: done T4. 12 lessons a hard kind at the body's level, rows over 508 pieces (left out on a 32-bit runner) before -> after: log 36/36 -> 0/36 (it reads log.txt, the prompt shows 5 of its lines), module 16/36 -> 0/36 (no comments, the program copies itself as the module, one test, drawn again when too long), walk, since, age, table, search, web 0 -> 0 (their fix rows now fit raw too); join 36/36 -> 35/36 (its tables are in the task's sentence and again in the program: the maker must give them as lines to fit); right by their checks the same (web 9 -> 8 of 12, Wikidata refused). The hive's own join rows (g38: 65 of 119) left as they are. tests/test_lessons.py 13.
- 2026-11-17 10:30 B (now orchestrator; Fable is gone): T4 merged. Join stays open: its tables sit in the task's sentence, so they appear twice in every row (534-613 pieces, 35 of 36 left out). Rewording the exam's join task would change the pulse; join is passed by the hive's own work (g34 4/4), so it is left as a known gap, not changed.
- 2026-11-17 11:05 B: g39 (run 44024307514, kept: before 36 -> after 38 of 64, hard 10 -> 12 of 32, easy 26 -> 26) had its record fail on a rebase conflict in docs/PROGRESS.md, redrawn on main after its checkout; replayed locally from the run's artifacts (body 23 cells, trunk g39trunk; read g39: next piece T4, shorter lessons for join, log, module). Fix: the record job commits the line and body alone, pulls the branch, and only then draws the read, graphs and KNOWLEDGE.md (a lost push race drops the drawing, rebases and redraws); reads.py write found training/ only under pytest (fixed). Test: the step's real text against a scratch repo whose main redrew PROGRESS.md; 413 tests.
- 2026-11-17 10:42 B: a memory guard that measures (training/grow.py MemoryGuard, Study.skip), for the 8B slices lost to memory (g38 7 of 24, g39 5 of 20; survivors at 14.1-14.8 of 15.6 GB; the length formula missed 1.5-1.9 GB): before each pass a row needing pieces x cost per piece that would leave under 1 GB available (HIVE_MEMORY_SPARE_GB) is skipped for that pass, not counted as met; the cost is learned from the fall in available memory during each pass (floor: the formula's); trim(0) after every pass, gc every 4; fits from available once the optimizer exists; step lines show available and swap; the record has memory {peak_gb, min_available_gb, swap_peak_gb, rows_skipped, cost_per_piece_mb}. t17 local run (--int8-base, spare 9.5 GB to force skips, 10 min): 114 passes, 92 skipped tries (91 of one long fix row), a piece learned 2.52 -> 2.92 MB, least available 9.66 GB, no swap. 412 tests.
- 2026-11-17 10:51 B: merged the memory guard (skip a row when available memory less its learned cost leaves under 1 GB; memory in each slice's record) with the spare 0.8 GB lower since fits now starts from available: 508 pieces in 32 bit, 814 in 16 bit, as before. g39 replayed: kept, before 36/64 (hard 10), after 38/64 (hard 12), easy 26 both; 4.9 h; kept-back gap +62 to +74 points on taught kinds. g40 starts now on main.
- 2026-11-17 11:40 B: the nightly schedule is only a backstop now: g40 (run 44053802610), scheduled at 09:14, queued behind g39, passed fresh (g39's record had failed, the body had not moved) and grew from the old body beside the self-restarting line until cancelled. Fix in grow.yml fresh: a scheduled run ends (why in the step summary) when a run of the line (title "Generation") on the branch started or ended within 8 hours (gh run list); any line run ends when a newer line run is already queued or running (the newer wins; trials untouched). tests/test_fresh_run.py 9 (fake gh with made-up run lists).
- 2026-11-17 17:06 B: "rows left out" measured, not estimated: each train slice's record now says rows_by_kind {given, too_long, skipped_memory, trained}} of the generation's new rows (distinct rows; the rest were not reached in time); training/reads.py shows too long of given with memory-skipped in brackets, and rule 2 (T4) counts too-long rows only. Older records show the old estimate marked "(estimate)" and hold no rule: g41's T4 call (57 of 152, 71 of 342) mixed time, memory and length, and T4 had measured 0 rows over 508 pieces in those kinds. tests: test_reads.py (time only, length, memory, estimate) and test_memory_guard.py (train() on the tiny model carries the right rows_by_kind).
- 2026-11-17 19:00 B: the owner's Colab notebook (L4) never trained a child: each train job looked for it once, at its start, and g42's came up 13 minutes after training began. Now the child offered (PICK) waits up to HIVE_COLAB_WAIT minutes (15) for it, one line a minute; one decision a child: slice 0 waits (colab.py alive --wait) and orders, the other slices wait the same window (colab.py aside) and stand aside once colab-order-GEN-NAME.json is in the release (or the notebook is there); with neither, every slice trains as always. A notebook not seen in 12 hours (colab.py seen) is not waited for; children not offered never wait. The cell it grows is marked (grown_on colab, gpu, minutes from order to cell; colab.py mark) and printed as a slice record; training/reads.py writes 'Colab: <child> grown on <gpu> in N minutes, S steps (CPU slices: median ...)' or 'Colab: not used (why)', and the Colab child's kept-back gap beside the CPU children's in the chain notes. Tests: tests/test_colab.py runs the train step's real text against a folder release (HIVE_COLAB_LOCAL) with the real colab.py.
- 2026-11-17 21:20 B: memory, all off until measured (PRs 89, 90): engrams per cell recalled own line first (team/engram.py), one shared hive engram that keeps learning with replay and is added into the trunk (training/hive_engram.py), rule-written notes from checked work (team/notes.py); engram strength follows the match (HIVE_ENGRAM_GATE). A stream measurement on the small DNA decides.
- 2026-11-17 23:15 B: g42 (run 44131701531) kept, 54 = 54 of 64 on its seeds (easy 31/32, taught hard 18 of 22, held out 5 of 10, first try 0.58), 5.3 h, 2 of 20 slices lost; the first generation counted with nobody's hand; g43 started by itself 22:17. Rule 6 met twice -> K1 (each kind in its own file, training/kinds/, old seeds give the same exams byte for byte) and M1 (training/talk_exam.py, 40 messages: route, fact, earlier turn, time; the small DNA alone 8.5 of 10, so the exam is too easy to mean much yet; not in the workflow).
- 2026-11-18 03:20 B: g43 (run 44188515917) kept by the paired gate at 52 against 54 of 64 (easy 32/32, hard 20 against 22, held out 0 of 6 against 1 of 6), 4.4 h, 0 of 20 slices lost, started g44 by itself at 02:41 (two generations with nobody's hand). Its read was not written: the record job runs training/reads.py with main's code, and K1 made it import training.kinds without the repository on the path (ModuleNotFoundError). Fixed (path set at the top, a test runs it as a script); g43's read written again from the record (no hours by job, no Colab line: those facts were lost with the run's job).
- 2026-11-18 04:40 B: holds the loop from now (session session_014dX1CNKMMabZ93Sdxn3fSK, branch claude/vigilant-brahmagupta-rz3ab7). One way of working for every session, so that nothing is done twice: `CLAUDE.md` (loaded first by every session: the goal's five bars, the role, the cycle, the rules), `NEXT_SESSION.md` (the one current handoff; older ones moved to docs/history/), `python scripts/cycle.py` (the first step of every cycle: the bars, the last generations as a table and a text graph, stale graphs, the next piece, who holds the loop). A new session claims the loop with a "holds the loop" line; the older one then stops.
- 2026-11-18 04:55 B: any agent may join beside the others: `CLAUDE.md` "Working alongside other agents" (one loop holder; workers claim one board piece each, in their own branch's log, before any work; a claim is live while its agent logged in the last 24 hours), the board in `docs/PLAN.md` brought up to date (open: H1 held out, F1 first try, S1 hours, J1 join, W2 wikidata, R1, R3, M2; B holds N1 and E1; C1 waits on the owner), `scripts/cycle.py` shows the board, and `docs/START_PROMPT.md` holds the prompts to start a loop holder or a worker. claim N1. claim E1.
