# NEXT SESSION: HiveMIND, handed to Fable 5.2

Written 2026-11-14, 21:10 UTC. This page replaces every earlier handoff. The old ones are in `docs/history/`
for detail only: where they set rules (gates, keeping a body only when it scores higher, strength records,
"measure every change beside a control before merging"), those rules are **retired**. Do not follow them.

You are the owner and long-term maintainer of HiveMIND, and its design is up to you.

## The key points

1. **What HiveMIND is:** one body of BitNet cells from one DNA. The DNA is a published ternary model
   (`prism-ml/Ternary-Bonsai-8B`, weights -1/0/+1, 2.2 GB, run on CPUs by ik_llama.cpp). A cell is the DNA plus a
   small weight edit (LoRA) trained on the hive's own checked work. Two cells must agree on an answer, and a third
   decides a difference (`team/solo.py`).
2. **The body multiplies and never stops growing** (`training/lineage.py`, built and tested 2026-11-14). Every
   grown cell has one child each generation, and the young ones wait a generation, like Fibonacci's rabbits.
   A child starts as an exact copy of its parent's edit (`grow.py train --parent`) and trains further on all the
   checked work: right answers, right-against-wrong pairs (`--pairs`) and its corrected failures (dreams). So it
   inherits what the parent learned, mistakes and fixes included, and goes a degree further. The body keeps
   parents and children. Two limits come from the free runners, not from the idea: 8 children per generation and
   24 cells. When the body is full, the oldest cells whose line goes on in a descendant give up their place.
3. **No gate, no ledger.** Arnav's decision: nothing decides whether a generation is kept, and nothing counts who
   was right on what to steer the body. The body grows every generation. One exam of the grown body (2 seeds) is
   taken as a **pulse**, only to trace problems back from. The choosing belongs to the architecture: engrams,
   learned mixing of cells, a shared trunk. Building that is your main work.
4. **How cells are seated without a ledger** (`team/ternary.seating`): the newest cell of the task's organ sits
   first. The second seat goes to the newest cell of another line, never the first one's own parent or child:
   near-copies that agree on a wrong answer are a false memory that agreement cannot catch.
5. **It runs by itself** (`.github/workflows/grow.yml`, "The hive teaches its own members"): practise, plan the
   children, train them (one runner each), take the pulse, record, then start the next generation at once. To
   stop it, set the repository variable `HIVE_LOOP` to `stop`, or disable the workflow. A generation where no child
   grew stops the line, with an error naming why. The nightly schedule (01:17 UTC) restarts it.

## What Arnav wants

His words, condensed: "Bitnets are capable, strong and small, and can be big with low compute and storage. A
product I can actually use, that runs complete agentic tasks and drives and improves itself: RSI as a hive, by
multiplication." The cells multiply, overlap like organs, train together and depend on each other, and act as
one. Each child is trained on its parent's dreams, which are synthetic tasks the parent can do, made harder over
time, and on what the parent could not do. Each cell knows what it does best, and the rest is left to the
others. Engrams and better BitNet architectures carry this, not bookkeeping. Bigger is fine even before it
scores higher: "they can just do more when bigger".

He does not want to make design decisions or read accounts of numbers. He wants it working and growing. Answer
him short and plain, with the result first.

## What is approved

You may do all of these without asking:
- Rewrite, move or delete any code or document, including anything earlier sessions wrote or decided.
- Start, cancel and re-run GitHub Actions runs on this repository (free for a public repository). Retry calls that
  failed for ordinary reasons.
- Create branches, push, open pull requests, and **merge to main yourself** when the tests pass and a real run of
  the changed path (locally on the 1.7B, or on a runner) shows it works.
- Write advice to Muse (another agent, branch `hivemind_muse`) in `FOR_MUSE.md`.

Ask Arnav first only before you spend money, use his accounts or credentials beyond this session's GitHub access,
or send anything in his name. No model names in commit messages or pull request bodies, apart from the
attribution lines the session requires.

## Finishing work

Please avoid stopping while you still owe work. Carry on with every part that does not depend on Arnav's
answer. Errors, timeouts, busy runners and failing tools are ordinary obstacles: find the cause and work
through them. Long computation belongs on runners or in background jobs; set a `send_later` reminder for when it
is due and do other work meanwhile. **The way to work, in Arnav's words:** build the whole thing, test it, find
and remove the bugs, run it, then trace back from the run when a problem shows. Do not queue many small trial
runs of pieces of an idea.

## State at handoff

- **The line restarts on the 8B** with this code. Its first generation has no parents (a new DNA), so it grows one
  cell per organ from the DNA; from the second generation on, the body multiplies. Look at the most recent run of
  "The hive teaches its own members" on main: the training time and memory of each 8B child, the pulse, and
  whether the next generation started.
- **Run 43629572891 (no. 19)** is a trial training 8B cells. Read its training memory and minutes per row. If it
  ran out of time (170 minutes per cell), lower `--epochs` or use `--minutes` in the train step.
- **The 1.7B body (g11) is on record** (`training/reports/generations.jsonl`). Its cells have no `.safetensors` in
  the release, so they cannot be parents. Every cell grown since 2026-11-14 evening has one.
- **What was measured before** (the 1.7B, four fresh exams of 16 tasks): DNA alone 9 of 64, a body of four cells
  26 of 64; on four more exams 29 against 14. On kinds it never practised: 0 of 11. Nothing so far carries over
  to kinds of task the body never practised. That is the deepest open problem.
- **Tests:** `.venv/bin/python -m pytest -q tests` (about 240 pass in a minute). A fresh machine:
  `bash scripts/cloud_setup.sh`.

## The work that is yours

In order of how much it matters to the goal. How to solve each one is up to you. `docs/RESEARCH.md` gathers the
published research on each, with links, and `docs/KERNELS.md` holds the speed measurements.

1. **Make the body act as one, without a ledger.** Candidates: a shared **trunk**, the cells merged into one
   edit each generation, exactly and cheaply (average the low-rank deltas by stacking their A and B factors, then
   cut back to a set rank by QR of the factors and an SVD of the small core; this is the branch-train-merge
   idea); a **learned mixing** of cells (branch-train-mix: the children become experts and a small router learns
   from the body's own outcomes); **engrams** that carry which line solved which kind of task as memory, not as a
   count. `docs/RESEARCH.md` §0 and §7 hold the designs and the brain's flaws the hive inherits.
2. **Parents make their children's lessons.** Today a child learns from the whole body's checked work and its
   corrected failures. Arnav wants the parent to dream tasks it can do, made harder each generation, and to pass
   on what it could not do. The exam makers (`training/exam.py`, `exam_hard.py`) take a seed and a level and
   give a task with its own check, so a parent can sit them and its right work becomes the child's rows.
3. **Carry-over to kinds never practised** (0 of 11). Learn the skill under a task (track a state, read the
   data, check its own result), not the task.
4. **A better BitNet architecture and bigger bodies** on CPUs and free runners. The 8B trains held ternary in
   memory (`--int8-base`, `training/ternary_base.py`).
5. **Speed.** Read `docs/KERNELS.md`: running two members at once (one cell per request in the server) would
   give 1.6 times the throughput, and a slow scalar kernel on the unrepacked output layer makes 4+ streams slower.

## How to work here

- **Find faults in the members' own programs and outputs, not in a score.** Each pulse uploads `gate-work-*`
  artifacts with every task's `TASK.md`, `REPORT.md`, events and programs (`mcp__github__actions_list`
  `list_workflow_run_artifacts`, then `mcp__github__actions_get` `download_workflow_run_artifact` for a signed URL;
  download with `curl` into its own folder).
- **Run the whole chain locally on the 1.7B before a runner sees it** (minutes, not hours): train two tiny cells
  (`grow.py train --base t17 --limit 4 --epochs 1 --layers last14 --no-checkpoint`), plan the children
  (`python3 training/lineage.py plan g901 t17`), train each with `--parent runs/grow/t17+<parent>/adapter_model.safetensors
  --parent-cell <parent>`, sit `training/exam.py sit --tasks 2` with `HIVE_MEMBERS` set to the cells, and run
  `training/grow_record.py gate <gate folder> <got folder> g901 --dna t17 --grow`. Back up `cells/body.json` and
  the report files first and restore them after.
- **Files that matter:** `training/lineage.py` (who has children, retiring), `training/grow.py` (practice,
  rows, dreams, training a cell, inheritance), `training/grow_record.py` (the record; writes `cells/body.json`),
  `team/ternary.py` (the DNA's server, cells, organs, seating), `team/solo.py` (the members), `team/engram.py`,
  `training/raw.py` (raw web text, code and people's corrections), `training/exam.py`, `training/exam_hard.py`,
  `.github/workflows/grow.yml`.

## Communicating clearly

Write for an intelligent reader with little context: Arnav has not seen your tool calls or files. Put the key
points first, in plain words and full sentences. Do not use terms you made up during the work; say what the
thing is. Keep reports short; leave out details unless he asks.
