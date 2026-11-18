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

| Bar | Target | Now (g45) |
|---|---|---|
| Hard kinds that have lessons | 18 of 23, read as a share: 0.78 | 12 of 16 (0.75); the hard set changed at g44 (K2), so this is not comparable with g43 and earlier |
| Held-out kinds (never taught) | half | 0 of 9 |
| Right at the first try | 0.7 | 0.35 |
| Talk exam | 8 of 10 | 6.5 of 10 (first sat at g45) |
| Hours for one generation | 3 | 5.6 |

## How one generation works (`.github/workflows/grow.yml`)

practice + dream → gather lessons and plan → train children (up to 20 slices, in parallel) → join → merge with the
trunk → **paired gate** → record.

- **Children.** Each child starts as its parent pulled halfway toward the trunk, so cells are never retrained from
  scratch.
- **Paired gate.** The body before and after sit the same exams on 8 seeds, and the talk exam runs too.
- **Record.** Keep or drop the new body, write `docs/reads/gNN.md`, redraw the graphs in `docs/PROGRESS.md`, and
  **start the next generation**.

**Lessons.** Each kind of task is one file in `training/kinds/`: 53 kinds, 10 of them held out (`training/kinds`, `HELD_OUT`). Each kind has a
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
| 11-18 | **g44 kept** (43 against 40 of 64), the first with the 24 new hard kinds, so its hard score is not comparable with earlier ones; first try fell to 0.36. **g45 kept** (45 against 47): the gate kept a body below its own before. Talk first sat: 6.5 of 10. Four generations recorded with nobody's hand (g42 to g45). |

In all (at g43): 529 commits, 99 pull requests; 19 generations recorded by g45.

## Running now

- **g47** is running. g45 is the newest record.
- **The memory test** on t17 is done, all five arms, one seed. Right on later rounds:

  | Arm | Seen kinds | Unseen kinds |
  |---|---|---|
  | off | 6/18 | 0 or 1 of 4 |
  | notes | 7/18 | 0 or 1 of 4 |
  | cell engrams | 11/18 | 0 or 1 of 4 |
  | hive engram | **16/18** | 0 or 1 of 4 |
  | all | 11/18 | 0 or 1 of 4 |

  No arm copied answers (copying 0). The hive engram helps on kinds already seen; no arm helps on unseen kinds.
  It is one seed on the small DNA, so it still has to be shown on t80. The engrams were never switched on in a real
  generation.

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
9. **The gate kept bodies worse than their before.** g43 was kept at 52 against 54, g45 at 45 against 47. This is
   being fixed (G1).
10. **Nothing aimed at held-out kinds.** They stayed at 0 (H1, X1 are open).
11. **Most lessons are still written by hand-made lesson makers**, not learned from the hive's own work.
12. **No person has talked to the body since 11-15** (T5 is open).
13. **The engrams were never switched on in a real generation.**
14. **The bookkeeping CSVs stopped on 11-15/16** (`docs/*.csv`).
15. **`docs/DECISIONS.md` was left unfinished**; its status is now at its top.

## Next, in order (the ids are on the board in `docs/PLAN.md`)

1. The gate also against the best body, so the drift stops (G1).
2. Held out: a fixed exam of about 30 tasks (X1), then work on why they fail (H1).
3. First try, for old and new kinds apart (F2), then its largest cause (F1).
4. Measure the "parent alone" link (P1), and a talk smoke run after each record (T5).
5. Turn on the hive engram only after it gains on t80.
6. Bring the hours down (S1), and train the eight long kinds without waiting on anyone (C1).
