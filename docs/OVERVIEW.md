# HiveMIND in one page

Written 2026-11-18 by B, the session that has held the loop since 2026-11-17. It covers the idea, how the hive
works, how the work is done, the path from day one, where things stand, and an honest account of what went well
and what did not.

## The idea

A **hive** of small **ternary** models (every weight is -1, 0 or +1, so they run on ordinary CPUs). It does what it
is asked (questions, talk, tasks) and **improves itself, generation after generation, on free GitHub runners, with
nobody's hand**.

- **The DNA** is one base model, t80 (Ternary-Bonsai-8B). The earlier work used the small t17.
- **A cell** is a small LoRA edit on the DNA: a data cell, a code cell, a words cell, a sources cell.
- **The trunk** is the average of the cells, cut to rank 32.
- **The body** is the cells that answer together. Two members must agree, and a check confirms the answer.

**The final build** is all five bars met on one generation:

| Bar | Target | Now (g43) |
|---|---|---|
| Hard kinds that have lessons | 18 of 23 (0.78) | 20 of 26 (0.77), nearly |
| Held-out kinds (never taught) | half | 0 of 6 |
| Right at the first try | 0.7 | 0.53 |
| Talk exam | 8 of 10 | first sitting in g44 |
| Hours for one generation | 3 | 4.4 |

## How one generation works (`.github/workflows/grow.yml`)

practice + dream → gather lessons and plan → train children (up to 20 slices, in parallel) → join → merge with the
trunk → **paired gate** → record.

- **Children.** Each child starts as its parent pulled halfway toward the trunk, so cells are never retrained from
  scratch.
- **Paired gate.** The body before and after sit the same exams on 8 seeds, and the talk exam runs too.
- **Record.** Keep or drop the new body, write `docs/reads/gNN.md`, redraw the graphs in `docs/PROGRESS.md`, and
  **start the next generation**.

**Lessons.** Each kind of task is one file in `training/kinds/`: 53 kinds, 6 of them held out. Each kind has a
maker, a check and a lesson that is right by that check. A hard kind is studied until its loss is low. Two lessons
of each kind are kept back to measure whether it was really learned.

**Memory** is built but **off until measured**:
- an engram for each cell (a small memory edit), recalled along its own line of ancestors;
- one shared hive engram that keeps learning with replay;
- notes written from failures.

## How the work is done (since today, for every session)

- **`CLAUDE.md`** holds the bars, the roles and the cycle. Every session reads it first.
- **`python scripts/cycle.py`** is the first step of every cycle. It shows:
  - the bars against the newest generation;
  - a table and a text graph of recent generations;
  - stale graphs;
  - the next piece;
  - the board;
  - who holds the loop.
- **One loop holder** judges each generation, keeps the board (`docs/PLAN.md`) and the handoff
  (`NEXT_SESSION.md`) true, and wakes itself for each record.
- **Any number of workers**, including agents nobody told us about, each claim one piece in the log before
  working. They prove it with numbers and merge once the tests pass (726 tests now).
- **Hands-on work goes to sub-agents.** The holder judges and merges, and nobody's yes is needed.
- **The prompts to start a session** are in `docs/START_PROMPT.md`.

## The path, from day one

| Days | What happened |
|---|---|
| 11-07 to 11-08 | It began as an **agent team**: an orchestrator, six specialists, a jury and memory, on llama.cpp, with weight edits for five specialists. |
| 11-09 to 11-11 | **Cells** were grown and audited. A "school" was added. There were tries at training ternary weights directly (vote counters). Regeneration of lost cells was added. |
| 11-12 to 11-13 | Measurements showed one model tied a body. Members began writing and running programs. Bodies were grown from 4 to 6 blocks. |
| 11-14 | **The hive became one body** (one model in memory, cells as edits). The first recorded generations g9 to g16 ran on t17, and most were dropped. The first engram test showed no gain. |
| 11-15 | The **8B DNA t80** arrived: g24 and g27 were kept. |
| 11-16 | Each child was trained on three runners at once. Several agents (A, B, C) worked in parallel. **The key finding:** each kind was passed always or never, because cells were only taught what they already passed. |
| 11-17 | The lessons were rebuilt: hard kinds studied until learned, lessons kept back, rows that fit the length limit, a memory guard. The paired gate and the reads written by the record job were added. **g39: 38/64 → g41: 58/64, the best so far.** g42 kept (54 = 54). The memory pieces were built, all off. |
| 11-18 | **g43 kept and g44 started by itself, two generations with nobody's hand.** Each kind is now one file, and 24 new hard kinds were added (K1, K2). The talk exam is in the gate (M1). The owner's CPU rule lab was merged: a child trained on 7 rows of a checked procedure solved 4/4 puzzles that its parents solved 0/4. One way of working for all sessions. |

In all: 529 commits, 99 pull requests, 17 recorded generations.

## Running now

- **g44** (the first with the new kinds and the talk exam). Its record is due about 07:20 UTC.
- **The memory test** on t17, with 4 of 5 arms done. On kinds already seen, right on later rounds:

  | Arm | Right on later rounds | Unseen kinds |
  |---|---|---|
  | off | 6/18 | 0/4 |
  | notes | 7/18 | 1/4 |
  | cell engrams | 11/18 | |
  | hive engram | **16/18** | 1/4 |

  No arm copied answers. If this holds, the hive engram is the first memory piece to turn on.

## What went well, and was enough

- **The line runs itself.** Each generation starts the next, and each is recorded, read and drawn without a
  hand.
- **The paired gate** compares before and after on the same seeds, so luck in the exam no longer decides.
- **The finding that unlocked progress:** right work on never-passed kinds had to reach the rows. Once it did,
  hard kinds went from 6/32 (g34) to 26/32 (g41).
- **Tests and proof before every merge.** The tests grew to 726, and each piece was merged with numbers.
- **Kinds in one file each**, so many agents can add work without meeting in one file.

## What I missed, or could have done better

1. **I merged K1 without running `reads.py` the way the record job runs it.** g43's read failed, and its Colab
   facts were lost. The lesson: run every changed script exactly as the workflow calls it.
2. **The scores drift down within the gate's tolerance:** g41 58, g42 54, g43 52 of 64. Each was kept because it
   lay within tolerance of its own "before". Small losses can pile up this way. The gate should also compare
   against the best body (g41), not only the last one.
3. **Too many handoff pages** (NEXT_SESSION, HANDOFF_B, LOOP, AGENTS, PLAN, DECISIONS) caused work to be redone.
   This was fixed only today, and the board was a day out of date before that.
4. **I built six memory pieces before measuring one.** Measuring the simplest piece first would have been
   cheaper.
5. **Held-out kinds stayed at 0**, and nothing aimed at them directly. Every piece aimed at taught kinds.
6. **Eight kinds are too long for the 32-bit runners**, and the fix waits on the owner's Colab. I should have
   offered a fix that needs no one, such as shorter data in those kinds or training them only on the 16-bit
   runners.
7. **The talk exam was too easy at first** (t17 scored 8.5/10), and it never had a full local sitting before going
   into the gate.
8. **Usage limits stopped sub-agents** mid-task (the memory test stalled for a time). Results should be committed
   step by step, not only at the end.

## Next, in order

1. Read g44: the new kinds, the first talk score, held out.
2. Turn on the hive engram if the last arm confirms it, then test it on t80.
3. Compare the gate with the best body, so the drift stops.
4. Work on held out (H1) and first try (F1).
5. Bring the hours down (S1).
6. Train the eight long kinds without waiting on anyone.
