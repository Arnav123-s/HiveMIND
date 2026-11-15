# NEXT SESSION: HiveMIND

Written 2026-11-15, 07:40 UTC. This page replaces every earlier handoff. The old ones are in `docs/history/` for
detail only; where they set rules, those rules are retired.

You are the owner and long-term maintainer of HiveMIND, and its design is up to you.

## The key points

1. **What HiveMIND is:** one body of BitNet cells from one DNA. The DNA is a published ternary model
   (`prism-ml/Ternary-Bonsai-8B`, weights -1/0/+1, 2.2 GB, run on CPUs by ik_llama.cpp). A cell is the DNA plus a
   small weight edit (LoRA, rank 16, last 14 layers) trained on the hive's own checked work.
2. **The body acts as one through its trunk** (`training/merge.py`, new 2026-11-15). Each generation the newest
   cell of every line of descent is averaged into one edit, exactly, and cut back to rank 32. The trunk answers
   every task first; a cell gives the second opinion and a third member decides a difference (`team/solo.py`,
   `team/ternary.seating`). A child starts as its parent pulled halfway toward the trunk, so the lines of descent
   explore apart and stay one body. Nothing is counted to make it: every cell weighs the same.
3. **The body multiplies and never stops growing** (`training/lineage.py`). Every grown cell has one child each
   generation; the young wait a generation (Fibonacci). Limits from the free runners: 8 children a generation, 24
   cells. An organ with no cell gets a first cell. No gate, no ledger: one exam of the grown body (2 seeds) is its
   **pulse**, only to trace problems back from.
4. **Its lessons grow harder** (`training/exam.py`, `team/parts.py`). Practice level `ladder`: half single tasks,
   half several tasks in one message, checked part by part. `cells/body.json` holds the levels (`compound`: how
   many parts; five kinds have harder forms of their own). Each record raises a level the body passes 7 times in
   10 and lowers one it passes 3 times in 20 (`grow_record.levels`). Each practice runner also goes back to 4
   tasks the body got wrong before, and a child is taught its own parent's mistakes with the program that was
   right (`grow.train`: "mend" rows).
5. **You can talk to it** (`team/talk.py`). One word from the DNA decides: talk is answered at once; anything to
   work out goes to the body's checked programs, in the user's own words, and comes back in plain words with the
   values as the programs printed them. Three doors: `./hive` or `python -m team chat` on a device; the workflow
   **Talk to the hive** (open an issue in the repository, the hive replies as a comment, only to the owner);
   **Ask the hive** in the Actions tab for one task.
6. **It runs by itself** (`.github/workflows/grow.yml`): practise, gather, plan, train (one runner a child), merge
   (the trunk), pulse, record, then the next generation at once. The nightly schedule (01:17 UTC) restarts a line
   that stopped. To stop it: set the repository variable `HIVE_LOOP` to `stop`, or disable the workflow.

## What Arnav wants

A hive of BitNet nets that are capable and keep getting better by themselves: he asks it questions, talks with it
or gives it tasks, and it does them. Cells multiply from one DNA, children learn from their parents' work, dreams
and mistakes, and the hive acts and learns as one. Bigger is fine. Engrams and better architectures are welcome
where they help. His method is a proposal, not a rule: change what works better.

He does not want to make design decisions or read accounts of numbers. **How to work, in his words:** build whole
things, test them, remove the bugs, run them, then trace back from the run when a problem shows. Do not queue many
small trial runs of pieces of an idea. Do not spend money. Answer him short and plain, key points first, without
terms made up during the work.

## What is approved

Without asking: rewrite or delete any code or document; start, cancel and re-run GitHub Actions runs on this
repository; push, open pull requests and **merge to main yourself** when the tests pass and a real run of the
changed path shows it works. Ask first only before spending money, using his accounts beyond this session's
GitHub access, or sending anything in his name. No model names in commits or pull requests apart from the
attribution lines the session requires.

## State at handoff

- **Generation 25 is running** on the new code (run 43689907158, started 07:25 UTC): the first with the ladder,
  dreams, a first `sources` cell, and a trunk at its end. **Read it first.** A generation takes about 6 hours.
  Check: every train job's `seconds_a_row` (expected under 15) and that none died; the merge job's
  `least_energy_kept`; the pulse; the record's line about levels; that generation 26 started.
- **Generation 24** (old code) left three 8B cells, `g24code`, `g24data`, `g24words`; its `sources` runner died.
  Pulse 11 of 32, and 1 of 5 on kinds never practised. Those cells are barely trained: their runners were swapping
  (30, 40 and 162 seconds a row; `g24words` got 14 steps).
- **Whether the line loops is not confirmed.** Generation 24's last step ("Grow again at once") was skipped, so
  either the repository variable `HIVE_LOOP` is `stop` or that run was started with `loop: 0`. If generation 25
  does not start generation 26, start it by hand (Actions, "The hive teaches its own members", Run workflow) and
  tell Arnav the variable has to be cleared.
- **Tests:** `.venv/bin/python -m pytest -q tests` (253 pass in a minute). A fresh machine: `bash
  scripts/cloud_setup.sh` (about 30 minutes; builds the ternary runtime).

## What was found on 2026-11-15, so it is not found again

- **8B training on a 16 GB runner** died or crawled because the whole DNA was first loaded as 16-bit numbers and a
  long row then pushed it into swap. Now (`training/ternary_base.py`): every matrix is read by itself straight
  into codes, the word vectors and the output layer too (8.1 GB held, 80 s to load); rows are capped to what the
  machine fits (about 1000 pieces on 16 GB; every piece costs about 5 MB while trained on); the kept outputs of
  frozen layers are on disk. Measured here on the real 8B: 9 s a row on a first pass, 4 s on later passes, 10.8
  GB at the most. A C routine rebuilds a layer's numbers from its codes 8 times faster than PyTorch; by itself it
  changed a row's time little (the multiplying and the rest dominate now).
- **Tried and not better:** another memory allocator (ran out of memory), huge pages always (slower), keeping
  memory instead of giving it back each step (4%).
- **The release's rows were overwritten by an older copy** (a trial that had read them hours before). The record
  now joins with what the release holds at that moment before uploading (`grow_record.union`).
- **The first way of talking** let the DNA hand a task over by writing it out. It wrote its own answer there. The
  decision is one word now and the task is always the user's own message.
- **The members looked up what they know** (14 minutes on the capital of Portugal). The orders now say that what
  does not change and is known needs no source (`team/solo.MEMBER`). Cells answer under the short orders
  (`solo.SHORT`), which do not say this: they learn it from rows.

## The work that is yours

In order of how much it matters to the goal. How to solve each is up to you. `docs/RESEARCH.md` gathers the
published research, `docs/KERNELS.md` the speed measurements.

1. **Read generation 25 and fix what broke.** It is the first run of much new code in the workflow (merge job,
   levels, rows joined at record). Then read the members' own programs in the pulse's `gate-work-*` artifacts.
2. **Web tasks are the body's weakest kind.** In generation 24's practice the 8B failed nearly every task that
   reads a site (made-up addresses, HTML dumped as the answer, 10 to 20 minutes each). A better `look`, a search
   helper, or rows from the few it gets right would lift many kinds at once.
3. **Carry-over to kinds never practised** (1 of 5 in generation 24, 0 of 11 on the 1.7B). The ladder and the
   trunk are the first two answers; watch `unpractised` in the pulse over the next generations.
4. **Talking, taught.** The DNA talks untaught. Rows for talk could come from answers people voted on
   (`training/raw.judged`) or from the hive's own conversations once there are some.
5. **Speed of answering.** Two members decoded at once would give 1.6 times the throughput; it needs one change in
   the runtime (a cell per request; `docs/KERNELS.md` section 3). The trunk and a cell cannot share a batch today.
6. **Engrams and reading raw text** (`team/engram.py`, `training/raw.py`, `--read`) are built and off: neither has
   shown a gain yet.

## How to work here

- **Find faults in the members' own programs and outputs, not in a score.** Each pulse and practice runner uploads
  its work (`gate-work-*`, `practice-work-*`): every task's `TASK.md`, `REPORT.md`, programs and what they
  printed. List artifacts with `mcp__github__actions_list` (`list_workflow_run_artifacts`), get a signed link with
  `mcp__github__actions_get` (`download_workflow_run_artifact`), download with `curl` into its own folder.
- **Run the whole chain locally on the 1.7B before a runner sees it** (20 minutes): train two tiny cells, merge
  their trunk, practise at the ladder level, dream, gather, train children with `--parent --trunk --gen`, merge,
  sit `training/exam.py sit --tasks 2`, record with `grow_record.py gate ... --grow --practice`. Back up
  `cells/body.json` and `training/reports/generations.jsonl` first and restore them after.
- **The real 8B fits this kind of machine** (15 GB, no swap) for training rows up to about 1000 pieces and for
  answering: `python training/grow.py train --base t80 --int8-base --layers last14 --no-checkpoint --limit 16`.
- **Files that matter:** `training/grow.py` (practice, rows, dreams, training), `training/merge.py` (the trunk),
  `training/lineage.py` (who has children, who the trunk is made of, who works), `training/grow_record.py` (the
  record, the levels, joining rows), `training/ternary_base.py` (the DNA held ternary), `training/exam.py` and
  `exam_hard.py` (tasks and their checks), `team/ternary.py` (the runtime, seating), `team/solo.py` (the
  members), `team/talk.py` (the front door), `.github/workflows/grow.yml` and `talk.yml`.
