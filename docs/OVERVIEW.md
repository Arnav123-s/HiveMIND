# HiveMIND in one page

Brought up to date 2026-11-18 23:40 UTC by B, the loop holder. This page covers the idea, how the hive works, how the
work is done, the path from day one, where it stands, and what went well and what did not.

## The idea

A **hive** of small **ternary** models (every weight is -1, 0 or +1, so they run on ordinary CPUs). It does what it
is asked (questions, talk, tasks) and **improves itself, generation after generation, on free GitHub runners, with
nobody's hand**.

- **DNA:** t80 (Ternary-Bonsai-8B). The early work used t17 (1.7B).
- **A cell** is a small LoRA edit on the DNA. There are four lines: sources, code, data, words. About 24 cells are
  active, in `cells/body.json`.
- **The trunk** is the average of the cells. A child starts as its parent pulled halfway toward the trunk, so
  cells are never retrained from scratch.
- **The body** is the cells that answer together. Members write and run programs. An answer counts when two
  members agree (on the printed answer, or on the files the task asks for) and the check passes. A coordinator
  then checks the delivered file itself (`team/deliverables.py`).

## The five bars (the final build is all five on one generation)

| Bar | Target | g45 | g47 |
|---|---|---|---|
| Taught hard kinds passed (a share since K2 added kinds) | ≥ 0.78 | 0.75 | 0.74 |
| Held-out kinds passed | half | 0 of 10 | 0 of 6 (pulse); the fixed exam starts at g49 |
| Right at the first try (practice) | 0.7 | 0.35 | 0.39 |
| Talk exam | 8 of 10 | 6.5 | 6.2 |
| Hours for one generation | 3 | 5.6 | 5.2 |

None of the five is met yet. The hard-kinds bar is the closest.

## One generation (`.github/workflows/grow.yml`)

practice + dream → gather lessons and plan → train children (up to 20 slices in parallel) → join → merge with the
trunk → **paired gate** → record.

- **Practice:** the body does tasks of every taught kind. Its checked rows, and fix rows from its failures, become
  training rows. Lessons also come from hand-made lesson makers, one kind per file in `training/kinds/` (57 kinds,
  10 of them held out, never trained).
- **The paired gate:**
  - The body before and the body after sit the same exams on 8 seeds.
  - They also sit a fixed held-out exam of 30 tasks, the talk exam (40 messages), and a three-message talk smoke.
  - **A body is kept only when after ≥ before.** Fewer right on the fixed held-out exam, with no gain elsewhere,
    is a drop.
- **The record:**
  - writes `docs/reads/gNN.md` and `latest.md`, the chain by kind, the next piece, and how many rows the hive
    taught itself;
  - redraws the graphs in `docs/PROGRESS.md` (score, split, carry, kinds, rows, hours, chain);
  - adds a finding to `docs/knowledge.json`;
  - starts the next generation.
- **A nightly backstop** (`nightly.yml`) restarts the line only if it stopped. Three drops in a row pause the line.

## Memory and kept skills

- **Engrams** (per-cell memory edits), a shared hive engram, and notes are built but **off**.
  - Measured on t17, the apparent gain (16/18 against 6/18) came from the short orders, not from memory.
  - The t80 body already uses the short orders.
- **Kept methods** (PR 105, the Codex side): the programming tool saves several verified programs per task, picks
  the one that fits the request's examples, names the bill when they disagree, and can repair one integer
  arithmetic mistake.
  - Invoices: 3/6 → 6/6.
  - Shipping: repaired from 4/100 to 100/100, then reused 16/16 with zero model calls.
- **Chat can now answer from those saved methods** with no model call (PR 107, on when `HIVE_BANK` is set). It is
  not yet live on GitHub.

## How the work is done

- **`CLAUDE.md`** has the bars, the role, the cycle, how agents join, code mode, and the rules. Every session reads
  it first.
- **`python scripts/cycle.py`** shows, in one screen:
  - the bars against the newest generation;
  - the last generations as a table and a text graph;
  - stale graphs;
  - the next piece;
  - the board with claims;
  - who holds the loop.
- **One loop holder** judges each generation and groups its failures by cause from the members' own programs.
  Hands-on work goes to sub-agents. The holder merges once the proof is shown and the full suite passes.
- **Any number of workers**, unaware of each other, each claim one board piece by a pushed log line, work in its
  files, prove it with numbers, and merge it. `scripts/agents_log.py --board` joins every branch's claims.
- **Start prompts** are in `docs/START_PROMPT.md`. The current handoff is `NEXT_SESSION.md`.

## The path

| When | What |
|---|---|
| 11-07 to 11-13 | An agent team (orchestrator, specialists, jury), then trained cells, a school, ternary training tries, regrowth, members that write and run programs |
| 11-14 | The hive became one body (one model, cells as edits). The first generations on t17 were mostly dropped |
| 11-15 | t80 arrived: g24 and g27 kept |
| 11-16 | **The key finding:** each kind was passed always or never, because cells were taught only what they already passed |
| 11-17 | Lessons rebuilt: study until learned, lessons kept back, rows that fit, a memory guard, the paired gate, reads by the record job. **g41: 58/64, the best so far** |
| 11-18 | Kinds one per file. 24 new hard kinds (from g44, so hard scores before and after are not comparable). The talk exam. **Five generations with nobody's hand** (g42 to g45, g47). The drift audit; the strict gate. The CPU rule lab and the checked deliveries (Codex side). Chat from saved methods. g48 running |

In all: 613 commits on main, 107 pull requests, 920 tests.

## What went well

- **The line runs itself.** Each generation is judged, recorded, read, drawn and followed by the next.
- **Fixes are found by cause** from the members' real programs and proven by replaying them (g45: 3 of 4 lost file
  tasks right on replay).
- **Proof before every merge.** Two sides (this loop and the Codex side) build on each other's branches without
  redoing work.

## What went wrong, and the lesson

1. **The gate kept worse bodies** (58 → 54 → 52), which hid a slide. It is now strict. Lesson: judge against the
   best, not only the last.
2. **Changes broke the record job:** K1 lost g43's read, and the board rewrite broke two tests on main. Lesson: run
   every changed script the way the workflow runs it, and run the full suite before every merge.
3. **Too many handoff pages, and a stale board,** made work get redone. There is now one handoff and one board.
4. **Memory was built before it was measured,** and the measurement then credited the wrong cause. Lesson: measure
   the simplest piece first, with a control.
5. **Nothing aimed at held-out kinds,** and 3 to 9 tasks a generation was noise. The fixed exam starts at g49.
6. **Most lessons are still hand-made.** The hive's own verified programs are not yet kept and reused (piece Y1).
7. **Usage limits stopped sub-agents and the loop** for hours. Sub-agents now commit after every step.
8. **The step "group failures by cause" was skipped for two generations.** It is the step that finds the blockers.

## Not done (the board in `docs/PLAN.md`, in order)

1. **V1:** prove g45's cause fixes on g49 (read its failures by cause, beside g45's).
2. **Y1:** the hive keeps its own verified programs and reuses them. This links the kept methods to the line.
3. **H1:** held-out kinds by cause, on the fixed exam.
4. **F1:** first try by cause, split by old and new kinds.
5. **A1:** talk routing, 6 of 10.
6. **S1:** hours, 5.2 against 3.
7. **G1:** the gate against the best body (after ≥ before is done).
8. **C1, J1:** rows too long for the 32-bit runners.
9. **D1:** saved methods live in the GitHub chat.
10. **P1, W2, R1, R3, M2, T3:** smaller pieces.
