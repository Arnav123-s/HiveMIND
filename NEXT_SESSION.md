# NEXT SESSION: the handoff to the next Claude session on HiveMIND

Written 2026-11-14 at 17:40 UTC by a Claude session that did the bookkeeping, measurement and repair work, for a
Fable 5.2 session that does the hard research. The earlier handoff, with the full history of 2026-11-13 and
2026-11-14, is kept unchanged in `docs/history/NEXT_SESSION_2026-11-14.md`. Read it only when you need a detail;
where it disagrees with this page, this page is newer.

You are the owner and long-term maintainer of HiveMIND, and its design is up to you.

## The key points

1. **The hive now works as one body of BitNet cells, and it is measurably better than its DNA alone.** One
   ternary model (the DNA, `Ternary-Bonsai-1.7B`, 0.43 GB) plus four cells. Each cell is the DNA with a small
   weight edit trained on the hive's own checked work. On four fresh exams of 16 mixed tasks, the body passed
   26 of 64 in 50 minutes, and the DNA alone passed 9 of 64 in 139 minutes.
2. **The body does not yet carry anything over to kinds of task it never practised: 0 of 11.** This is the main
   gap between "it learns what it is shown" and "it gets more intelligent". It is the most important open
   problem, and it is yours.
3. **Five measurements run on GitHub now.** Their results come in between about 19:00 and 22:00 UTC on
   2026-11-14. The table in "Runs in flight" says what each one answers.
4. **The hive grows by itself every night** (01:17 UTC on main). It practises, trains new cells from its own
   checked work, and keeps them only if they beat both the DNA and the body before.

## What Arnav wants (his words, condensed)

"A hive is many same-sized models, like cells in a body: they multiply, overlap like organs, each leaning to a
different strength, train together as one from their own checked work, and keep growing." Every component is a
BitNet cell. The body regenerates from the same DNA. It does not need to know everything; it must keep getting
better at all tasks, more efficient and stronger. He wants a better BitNet architecture, more intelligence and
better learning, and faster and better training. He also asked for **engrams**: BitNet edits as continual memory
modules, so the hive learns continually between the nightly regrowths. He wants a product he can use, which runs
complete agentic tasks and improves itself: "RSI as a hive, by multiplication". He does not want to make design
decisions; he wants results.

Talking to Arnav: he writes fast and informally. Answer short and plain. Put the result first. Say what is
measured and what is not. When you explain a mechanism, use plain words and say how the pieces fit together.

## What you may do without asking

- Rewrite, move or delete any code or document, including what earlier sessions wrote.
- Start, cancel and re-run GitHub Actions runs on this repository. They cost Arnav nothing; they are already
  approved. Retry a call that failed for an ordinary reason (timeout, busy runner, network).
- Create branches, push, open pull requests, and **merge into main yourself once a change is measured** (an exam
  number on fresh seeds, beside a control). A change that measures no worse and fixes a real fault may also go in.
- Create cloud sessions, and write advice to Muse in `FOR_MUSE.md`.

Ask Arnav first only before you spend money, use his accounts or credentials beyond the GitHub access this
session already has, or send anything in his name.

Standing rule: no model names in commit messages or pull request bodies, except the attribution lines the session
requires.

## Finishing work

Do not stop while you still owe work. Status notes are welcome, and so are questions on decisions that are truly
his, but carry on with every part that does not depend on his answer. Errors, timeouts, empty results and failing
tools are ordinary obstacles: find the cause and work through them. Long computation belongs on GitHub runners or
in background jobs: start it, set a `send_later` reminder for when it is due, and do other work meanwhile.

## Where it stands, measured

All numbers are from the gate of `.github/workflows/grow.yml`. Each arm sits the same four fresh seeds of the
mixed exam (16 tasks each: half basic kinds, half hard multi-step kinds; `training/exam.py --level mixed`), as
members alone. `python3 training/results.py` prints every recorded generation and trial from every branch.

| run | cells | DNA alone | body | never-practised kinds |
|---|---|---|---|---|
| g10 (the body on main) | ordinary LoRA edits on t17, 222 checked rows | 9 of 64, 139 min | **26 of 64, 50 min** | 0 of 11 |
| g9 (trial) | ternary edits, the same 222 rows | 7 of 64, 124 min | 13 of 64, 231 min | 0 of 9 |

- **Ordinary edits beat ternary edits** on the same rows: twice the tasks in a quarter of the time. The
  workflow therefore grows ordinary edits by default (`ternary: 1` still selects ternary edits).
- **Noise:** two runs of the same hive on the same 24 tasks differed by 5 tasks. A gate of 64 tasks can see a
  difference like 26 against 9, but not one of 2 or 3 tasks. Use more seeds before you trust a small gain.
- **Engrams, first form** (`team/engram.py`): one checked task becomes one tiny ternary edit (rank 4, the last 8
  layers, 2.5 MB). It is recalled by the words a new task shares with the old one, and switched on beside the
  working cell (`HIVE_ENGRAMS=1`). On one stream of 32 tasks it showed no effect. Recall fired on only 8 tasks,
  and on those 8 both arms passed 6. Recall by shared words is too weak.
- **Training speed on a runner:** 4.0 seconds a row, bf16, the last 14 layers, no recomputation, 7 GB. Four
  cells from 222 rows take about 70 minutes each.
- **The 4B DNA (t40):** trains here only with swap (13.2 GB peak, about 30 s a row). Its first GitHub run is in
  flight.

### Why the never-practised kinds fail

Read from the members' own programs in g10's gate (seed 20009012). The tools worked; the model's reasoning
failed.
- A robot follows a program of moves and turns. The members' code moved `x` on every step and ignored the turns
  and the repeat counts. Two members made the same error and so "agreed" on the wrong answer.
- Compare the release dates of two packages. The code made up a key (`pypi_version`), or read a project's web
  page as if it were JSON, and gave up after the same error twice.

Since then, a program that asks for a key that is not there is told which keys exist, and a reply that is not
JSON says what it begins with (`team/tools/sandbox.py`). It is on main; run 16 below measures it.

## Runs in flight (started 2026-11-14 about 17:05 UTC)

Each run appends one line to `training/reports/generations.jsonl` on the branch it was started from;
`training/results.py` reads them all. Seeds "901" are the same four exams g10 sat (20009011-14).

| run id | what it is | branch, seeds | it answers |
|---|---|---|---|
| 43599778796 (g11) | the first generation trained on the body's own practice (ternary edits: it started before the default changed) | make-it-work, own | does self-practice beat g10? If it was kept, merge make-it-work into main before 01:17 UTC; `generations.jsonl` merges as a union of lines (`.gitattributes`) |
| 43619078349 (no. 12) | the 4B DNA, ordinary cells from the 222 rows | main, 901 | does a bigger DNA lift the score and the 0? |
| 43619106252 (no. 14) | t17 cells also trained to foresee what a program prints | main, 901 | does foreseeing help simulation and code? |
| 43619155775 (no. 15) | g10's cells (from run 43569009099) on four new exams | main, 902 | does 26 against 9 hold on unseen exams? |
| 43619621791 (no. 16) | g10's cells with the new error feedback | claude/sleepy-johnson-lrm62n, 901 | does the feedback help? It is already on main (commit b1a4730). If the body passes clearly fewer than 26 (say 21 or fewer), revert that commit |

If a record job is red, its log holds the line it could not write: put it into `generations.jsonl` by hand.

## The open problems, for you to decide how to attack

These are the parts that need deep research rather than bookkeeping. They are listed by how much they matter
to Arnav's goal. How to solve them is up to you. **`docs/RESEARCH.md` gathers what published research says about
each one, with links**, so you need not search for it again. One lever from it is already built and waits for a
measurement: `grow.py train --pairs` (workflow input `pairs: "1"`), which learns from a right program beside a
wrong one for the same task. Practice records these pairs from 2026-11-14 evening on.

1. **Carry-over to new kinds of task.** The body learns what it practises and nothing else. What would make a
   cell learn the skill under a task (read the data, track a state, check its own result) rather than the task?
   Candidates already in the code: foresee rows (run 14), a bigger DNA (run 12). Neither is known to work.
2. **A better BitNet architecture.** Today the hive only adds edits to a fixed ternary DNA. Arnav wants the
   architecture itself improved, and bodies that can grow large on little compute. Training a ternary model
   from nothing on a CPU stayed weak in every recipe tried (see the history file). Find what a CPU and free
   runners can really do here.
3. **Engrams as continual memory.** The first form recalls too rarely to matter. Make engrams a real continual
   learning mechanism, and measure it the same way as the cells.
4. **The improvement loop itself.** The nightly loop runs. Whether it improves the body night after night is
   measured by its own gate; g11 is the first data point. Make the loop faster and its gains larger.
5. **Training speed.** 4 seconds a row limits how much the body can learn in a night.

## How to work here

- **Find faults by reading the members' own programs and outputs, not from the score.** Every gate uploads
  `gate-work-<arm>-<seed>` artifacts. Each task folder has `TASK.md`, `REPORT.md`, `members/events.jsonl` and
  the members' programs. To read one, use `mcp__github__actions_list` (`list_workflow_run_artifacts`), then
  `mcp__github__actions_get` (`download_workflow_run_artifact`, which gives a signed URL). Download it with
  `curl` into its own scratch folder and unzip it.
- **Compare two ideas fairly in one run:** input `versus` with training flags (for example `"--pairs"`,
  `"--foresee"`, `"--lr 0.0005"`). The run practises once, grows the usual cells and a second kind with those flags
  from the very same rows, and sits both on the same exams beside the DNA (a fourth gate arm). It is always a
  trial. Use it instead of two separate trials: separate trials practise separately and read a shared row file
  that other runs overwrite, so their rows differ.
- **Practice at the edge (a curriculum, built 2026-11-14, not yet measured):** input `practice_level: "edge"`
  practises kinds of task in proportion to p(1 - p), where p is the body's pass rate on the kind in its last three
  gates (`grow.edge_weights`; the gate records pass counts per kind from 2026-11-15 on). Kinds always passed
  (learned) and never passed (no right program to learn from yet) drop out; harder kinds come in as the body
  improves. To measure it, start two trials with the same `gate_seeds`, both with `fresh_rows: "1"` (train only on
  that run's own practice), one with `practice_level: "edge"` and one without. Do this after a night has recorded
  per-kind counts, or the edge has nothing to steer by.
- **Weaknesses go to the nearest strength (Arnav's idea; built 2026-11-14, not yet measured).** Every exam and
  practice task now puts each member's own answer to the task's check (`exam.each_member`). The nightly gate
  writes, per cell's leaning, how often it was right by itself on each kind and each organ (`cells/strengths.json`).
  With `HIVE_SEATING=strength` (workflow input `seating: "strength"`), a task is seated with the cells most likely
  right on its kind, whichever organ they lean to. A kind never met backs off to the cell's record on the task's
  organ (the nearer degree), then to one half. To measure it after a night has written `cells/strengths.json`, re-sit
  that night's cells twice on the same seeds (`cells_from_run`, the same `gate_seeds`), once with
  `seating: "strength"`. No training is needed.
- **Start a run:** `mcp__github__actions_run_trigger`, `run_workflow`, workflow `grow.yml`. Its inputs are
  described in the file. The useful ones: `trial: "1"` (record only, the body does not change), `gate_seeds`
  (the same number means the same exams), `skip_practice: "1"`, `cells_from_run` (re-sit stored cells without
  training), `dna: "t40"`, `foresee: "1"`, `ternary: "1"`. Trials run in parallel. The nightly line and runs
  without `trial` take turns.
- **Tests:** `.venv/bin/python -m pytest -q tests` (209 pass, about 1 minute). Set up a fresh machine with
  `bash scripts/cloud_setup.sh`.
- **Files that matter:** `team/ternary.py` (the DNA, the cells, organs and seating, the shared server),
  `team/solo.py` (the members: two must agree, a third decides), `team/engram.py`, `team/tools/sandbox.py`
  (where programs run), `training/grow.py` (practice, training rows, training a cell), `training/grow_record.py`
  (the gate decides; it writes `cells/body.json`), `training/exam.py` and `training/exam_hard.py` (the exam;
  `HELD_OUT` lists the four never-practised kinds), `.github/workflows/grow.yml` (the nightly loop and trials).
- **Muse** is another agent (not Claude) on branch `hivemind_muse` with many workers but a weak machine. Your
  advice to it is `FOR_MUSE.md`. Treat its results as ideas to re-measure.

## For Arnav: the prompt to start the next session

Start the session at effort `high`. Paste:

```
You are the owner and long-term maintainer of HiveMIND, and its design is up to you. Read NEXT_SESSION.md
first. The goal: one body of BitNet cells, many same-sized models from one DNA, that multiply, overlap like
organs, train together as one from their own checked work, and keep getting better at all tasks; a better
BitNet architecture; engrams as continual memory; faster and better training; a product I can use that runs
complete agentic tasks and improves itself. Read the results of the runs in flight, then work on the open
problems, hardest and most important first. Ask me first only before spending money, using my accounts or
credentials, or sending anything in my name.
```
