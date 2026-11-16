# NEXT SESSION: HiveMIND

Written 2026-11-16, 03:10 UTC, and brought up to date at 22:40 UTC, by agent C (the lead session, `session_01PZiWThbrn8cykQKW6mTcdp`, branch
`claude/relaxed-pasteur-yxzlpi`) at the owner's request, for the lead session that takes over next from another
account. It replaces every earlier handoff (agent A's of 00:20 UTC is in pull request 61; older ones in
`docs/history/` and in git). Read this page, then `docs/AGENTS.md` (its log, newest last), `docs/KNOWLEDGE.md` and
`docs/LOOP.md`.

You are the lead maintainer. The owner's words: understand the goal, do the reasoning, make the decisions, direct
the other agents, and make the hive a success. The earlier sessions' working rules are not yours; the goal is.

## The key points

1. **The goal:** a hive of BitNet (ternary) nets from one DNA that does what it is asked (questions, talk, tasks)
   and gets better by itself, generation after generation, on free CPUs.
2. **Where it stands:** generation 28 passed 18 of 32 exam tasks, generation 27 passed 15. The untaught DNA scores
   about the same. Generation 33 is running now (run 43790075166, started 02:05 UTC).
3. **Why it does not improve (found 2026-11-16, the main finding of this session):**
   - **Each kind of task is passed either always or never.** g27: twelve kinds passed every time (15 of 15 tasks),
     twelve kinds never (0 of 17). g28: thirteen kinds always (17 of 17), ten never (0 of 13), one in between.
     The score moves only when a never-passed kind is learned.
   - **The cells have nothing left to learn from their rows.** Training loss: the first cell fell from 1.23 to 0.16
     in 83 steps (g24code); a child starts at 0.04 (g25code); g28code went from 0.096 to 0.048. The rows were taken
     only from tasks two members agreed on and the check confirmed: the kinds already passed.
   - **So more study time adds nothing.** Agent B's three runners a child (pull request 64) triple the time spent on
     rows already learned. It does no harm and is not the lever.
4. **The lever:** right work on the never-passed kinds must reach the rows, and training must spend its passes
   there. Four pieces, below ("The plan"). All four are built and merged since 03:30 UTC (agent B); generation 35 is
   the first grown with them, and its pulse is not sat yet ("State").
5. **Three agents, three accounts' worth of limits.** Agent B (another account) is the coordinator since 02:10 UTC
   and merges fast. Agent A (the owner's account) measures. You will be on a third seat: you reach both only through
   `docs/AGENTS.md`, `docs/knowledge.json` and pull requests, unless the owner carries a message.

## The plan, in order

**1. Rows from every member the task's check confirms (built by B, pull request 66, on main).** In practice the check
is the judge, not agreement. Agent A's count over 452 tasks: the body was right on 46 of 196 hard tasks, some member
on 67 (21 more: modules 7, walking a site 5, a fact and a date sum 4, editing a file 3). Generation 33 started
before this was merged, so **the generation after g33 is the first to use it**. Check there: rows with
`"by": "check"`, by kind.

**2. Training studies where its error is (built by B, pull request 68; `Study` in `training/grow.py`).** The design was: In `training/grow.py`, `train()`:
- Sort the encoded rows into subjects: the kind of task, the row's type (`first`, `fix`, `mend`, `done`), and
  whether the row is new this generation.
- Each pass: pick a subject with probability in proportion to its loss (never below 0.05, times 3 for the cell's own
  organ), take its next row, train on it, and set the subject's loss to the mean of its last losses. A subject not
  measured yet starts at 1.0, so every subject is met early; that first sweep is also the rehearsal of old work.
  A row is met at most 4 times in one training.
- Raw text and judged pairs get a fixed share of the passes (their loss does not say what is left to learn).
- The learning rate follows the share of the time used, and the loop runs to the time limit (rows met again skip
  the frozen layers, so more passes fit than one timed row says).
- Record for each subject: rows, passes, first and last loss, in the cell's JSON. This is also a progress measure
  that an exam's noise does not touch: the first loss on a kind's new rows falls when the kind is being learned.
- With B's slices, each slice does this on its own rows.
- Proof: a test with a small model (the unlearned subject gets most passes, every subject is met); then one trial
  run (`trial: 1`, `skip_practice: 1`): its gather makes lessons, its children study them, and the gate's "after"
  arm is read against "before" on the kinds that have lessons.

**3. A measure that can show it (built by B, pull request 68).** The pulse is 32 tasks: one generation differs from the next by
several tasks from chance alone. Sit 4 seeds (64 tasks) in the line's gate (`grow.yml`, the gate matrix: `[1,2]` to
`[1,2,3,4]`, two more runners, free), and record the hard kinds apart from the easy ones (an exam task's id begins
with `h` or `e`), drawn in `training/progress.py`.

**4. Practice where it can pay (built by B, pull request 68).** Practice draws kinds by p(1 - p) of the body's pass rate with one pass
and one failure added, so a kind passed 2 of 2 and one passed 0 of 2 weigh the same (0.19) and half the practice
goes to kinds already learned. Draw by s(1 - f) instead: s, how often some member is right on the kind; f, how
often the body is. That is high exactly where practice makes a new row (`training/grow.edge_weights`; practice.json
needs the kind and whether some member was right).

**Also to decide:** lessons give one right program for each never-passed kind a generation (`--per-kind 1` in
`grow.yml`, gather). A kind needs several examples before practice can carry it; 3 a kind would start kinds in one
generation instead of several. Lessons already stop for a kind once the hive has 3 right programs of its own.

## State at handoff (2026-11-16 22:40 UTC)

- **Main** is at `b75a8cf`: every agent's work is merged (pull requests 56 to 72). 341 tests pass.
- **Generation 34** (the recorded body, 4 seeds): 37 of 64. **Easy kinds 31 of 32, hard kinds 6 of 32.** That is the
  bar. Generation 35 (the night's first changes; siblings of g34's cells, a trial, not recorded) got hard 6 of 24:
  no gain. Why: its lessons were not learned enough (2 to 10 passes a hard subject, loss ending at 0.4 to 1.6).
- **Generation 38 is running** (started about 20:30 UTC on `2e3ff66`). It is the test of the whole plan: rows from
  confirmed members, study by error, 12 lessons a kind for every kind the body fails more often than not, new rows
  in every slice, raw text 3% of the passes, practice on 12 runners of 8 tasks, the pulse on 8 seats of 8.
  **Read its hard kinds against 6 of 32.** Agent A was asked (22:35 UTC) to read it the moment it records: easy and
  hard, each cell's loss on the new hard subjects, and for every failed hard task whether the members now write the
  lesson's way.
- **Fixed today:** a model server that died at once (a kept runtime built for another CPU's instructions; B); a run
  growing from an old body, and the schedule starting a run while one is on (A); the join step (B).
- **Agent B** coordinates merges and built the speed piece (pull request 72). Its channel: its newest open pull
  request, or a comment on its last one.
- **The line:** check that the generation after g38 starts by itself; if not, `HIVE_LOOP` is still `stop`.

## Working with the other agents

- Write to them in `docs/AGENTS.md` (a log line, newest last) and in your pull request's description; they read both
  at the start of every cycle. Read theirs the same way before you change a file.
- From the owner's own account a session can message agent A (`send_message` with A's session id) and read its
  transcript (`list_events`). **A's permission check refuses a change asked for by another session** until the owner
  says yes to A himself: tell the owner what you asked A, so that he can say yes.
- Who owns which file is in `docs/AGENTS.md`. B changed A's files while A was paused and logged it; do the same:
  say it in the log first, then change.

## What the owner wants, and what holds

A hive that is capable and keeps getting better by itself; he talks with it and gives it tasks. Cells multiply from
one DNA and learn from their work, their mistakes, dreams and raw data; the hive acts and learns as one. His method
is a proposal: change what works better. Engrams and other architectures are welcome where they help.

- First principles. Whole pieces of work, finished, then checked. No runs of small experiments.
- Spend no money. Ask before using his accounts beyond this repository.
- Merging to main: ask him once when a change is ready (tests pass, one real run of the changed path shows no loss).
- Answer him short and plain, key points first, in words he already knows.
- No model names in commits, pull requests or files, apart from the attribution lines a session requires. Agents
  are A, B, C by session, branch and pull request.
- He likes graphs of progress and clean labels on every run.

## First hour

1. Merge main into your branch. Read the log in `docs/AGENTS.md` from 2026-11-16 22:00 on.
2. Generation 38's record (`training/reports/generations.jsonl`, the last line): `arms.after.hard` against 6 of 32,
   and agent A's reading of it in the log.
3. If the hard kinds moved: let the line run; the next weakest things are the held-out kinds, talk, and time.
4. If the losses on the new hard subjects fell (below about 0.3) and the tasks still fail: the fault is in what a
   member does with what it knows. Read A's classification of the failed hard tasks and fix the largest cause.
5. If the losses did not fall: the cells need more passes on lessons than a runner gives. The owner's Colab notebook
   (`colab/hive_gpu.ipynb`) trains a child whole on a GPU in minutes; or fewer, longer-trained children.

## How to work here

- **Read the training loss before buying training time, and the exam by kind before reading its score.** Both were
  in the record for two days while the work went into training speed.
- **Write a finding into `docs/AGENTS.md` and push it the moment it is found.** This session reached its usage limit
  an hour in, with its finding only in its own head; two agents then built on the older picture.
- Find faults in the members' own programs and outputs: `gate-work-*` and `practice-work-*` artifacts of a run, each
  unpacked into its own folder (`exam.json`, `members/TASK.md`, `events.jsonl`, the programs, their `.out`/`.err`).
- Replay real failing programs through changed code (seconds), then the tests (a minute), then one whole real run.
  A trial on your branch (`trial: 1`, with `cells_from_run`, `gate_seeds`, `skip_practice: 1`, `loop: 0` as needed)
  is free and does not touch the line. List a run's artifacts before pointing a trial at it.
- Record every cycle (`docs/loop_log.csv`), every run (`docs/runs.csv`), every finding and rule
  (`docs/knowledge.json`, then `python scripts/knowledge.py`), and a line in `docs/AGENTS.md`.
- A fresh machine: `python3 -m venv .venv`, CPU torch, `pip install -r requirements.txt` (5 minutes; enough for the
  tests). The whole hive with its runtime: `bash scripts/cloud_setup.sh` (30 minutes).
- **Files that matter:** `training/grow.py` (practice, rows, dreams, training), `training/lessons.py`,
  `training/raw.py`, `training/merge.py`, `training/lineage.py`, `training/grow_record.py`,
  `training/ternary_base.py`, `training/exam.py` and `exam_hard.py`, `training/progress.py`, `team/ternary.py` (the
  runtime), `team/solo.py` (the members), `team/tools/sandbox.py` (what a program runs in), `team/talk.py`,
  `.github/workflows/grow.yml`.
