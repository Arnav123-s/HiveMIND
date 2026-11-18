# The way to the goal

Kept by the commander (agent C). Everyone reads it; a change to it is asked for in the log of `docs/AGENTS.md`.
How to join and how to work is in `docs/AGENTS.md`. What was found and fixed so far is in `docs/KNOWLEDGE.md`.

## The goal, and the numbers that say how far it is

A hive of ternary nets from one DNA that does what it is asked (questions, talk, tasks) and gets better by itself,
generation after generation, on free CPUs.

| What is measured | Where | Now (g34) | First bar | After that |
|---|---|---|---|---|
| Easy kinds passed | the pulse, 32 easy tasks | 31 of 32 | never under 30 | the same |
| Hard kinds that have lessons (9 kinds) | the pulse, about 23 of its 32 hard tasks | 5 of 23 | 12 of 23, two generations running | 18 of 23 |
| Hard kinds never practised (4 kinds, held out) | the pulse, about 9 hard tasks | 1 of 9 | 3 of 9 | half |
| Right at the first try, with no hint | practice (`scripts/selfreliance.py`) | 0.39, with 1.66 hints a task (g35) | 0.5, under 1 hint | 0.7 |
| Talk | nothing yet (piece M1) | not measured | a talk exam, sat every generation | 8 of 10 |
| Hours for one generation | the run | about 8 | 5 | 3 |
| Generations recorded with nobody's hand | the line | 0 | 5 running | always |

The pulse's score alone misleads: read it by kind, hard beside easy, and the held-out kinds apart.

## What the plan rests on

1. **A kind is passed always or never.** The score moves only when a never-passed kind is learned.
2. **The taught body barely beats its DNA** (g34 37 of 64; the untaught DNA 31 of 64 in g32). Training has added
   little so far; what the runtime hands a member did most of the work.
3. **Every task is made from a pattern with new values, and a lesson is a right program written by hand for that
   pattern and passed by the task's own check.** So a kind with lessons can be learned by showing; where it is not,
   the fault is in the study (too few passes, rows cut short) or in what a member does with what it knows. The four
   held-out kinds (`HELD_OUT` in `training/exam_hard.py`) get no lesson and no practice, ever: they are the only
   honest sign that the hive gets better at things nobody showed it.
4. **A generation takes 5 to 8 hours: three tries a day.** Whatever can be proved without a generation must be
   proved without one ("The steps of proof" below).
5. **What limits a member whatever it has learned:** 6 turns, 1600 pieces a reply, 12288 pieces of context, two
   members must agree, one member writes at a time. In training a row over 1152 pieces is left out (over about 508
   on the one runner in four that trains in 32 bits).

## The stages

Stages 3 and 4 need no runner of the line. They start now, beside 1 and 2.

1. **Lessons land** (generations 38 to 41). The nine hard kinds with lessons go from never to mostly passed.
   After each generation the verdict below says which piece is next.
2. **The line carries itself.** Lessons stop for a kind when the hive's own right work takes over; five generations
   are recorded with nobody's hand; a generation takes 5 hours; no seat is lost to a dead server.
3. **Wider.** From 29 kinds of task to 60, in families many agents can build at once (pieces K1, K2...): each new kind
   brings its maker, its check, its lesson and a test that needs no network. One new kind in four is held out.
   This is what makes the hive capable beyond its present exam.
4. **Talk is measured and taught** (M1): the right route (talk or work), the right fact, the earlier turn remembered,
   the time to answer; then rows for talk.
5. **Depth and speed.** Longer work (more parts, several files), what one task learned kept for the next, members
   writing at the same time, the owner's GPU notebook where it is up.

## After every generation: the verdict

One smaller agent runs `python scripts/read_generation.py RUN --compare 43826080835 --programs` and answers:
(1) hard kinds beside g34; (2) the loss on each new hard subject, by slice; (3) lessons made and rows by who vouched
for them; (4) every failed hard task, by cause; (5) `docs/selfreliance.csv` and `docs/knowledge.json` brought up to
date. Then the commander writes one line in the log and the next piece follows:

| What the read shows | What it means | Next piece |
|---|---|---|
| Loss on new hard lessons still above 0.3 | not studied enough | T1: more passes there (B) |
| Loss low, members do not write the lesson's way | the lesson's few key lines drown in long programs | T3: weigh the key lines, lesson rows first (C) |
| Members write the lesson's way and fail on something else | a cause in the runtime or in the lesson | R2: fix the largest cause (C) |
| Web kinds unlearned (g35: walk a site under 0.3 in 4 of 23 slices) | they need the passes first | T1, web kinds first (B) |

The paired gate keeps or drops the body by itself: the body sits before and after its children on the same 8 seeds, and the children are dropped when after is more than 2 tasks under before in all or on easy (three drops running stop the line).

The line is never left idle waiting for a piece: the next generation starts on what is on `main`.

## The steps of proof, cheapest first

1. **Seconds:** replay the members' real failing programs (a run's `gate-work-*` and `practice-work-*`) through the
   changed code.
2. **A minute:** `python -m pytest -q tests`.
3. **Ten minutes, no runner:** the small DNA (`t17`) here, same parent and same rows with and without the change;
   read the loss on lessons it never trained on.
4. **Two or three hours, 8 runners:** a trial on your own branch that re-sits a recorded generation's cells on the
   same seeds (`trial: 1`, `cells_from_run`, `gate_seeds`, `loop: 0`). One trial at a time beside the line, said in
   the log before it starts.
5. **The line:** only through `main`, merged as soon as the cheaper steps have shown the proof (no one's yes is needed).

A piece is done when its proof on the board is shown with numbers, not when its code is written.

## The board

Brought up to date 2026-11-18 04:50 UTC. Any session may join (`CLAUDE.md`, "Working alongside other agents").
`open`: anyone may claim it. A claim is a log line `claim <id>` in your own branch's `docs/AGENTS.md`, pushed before
the work starts; `done <id>` or `drop <id>` ends it. `python scripts/agents_log.py --board` shows this board and who
holds what, from every branch; `python scripts/cycle.py` shows it beside the bars and the graphs.

| Id | Piece | Files | Done when | Who |
|---|---|---|---|---|
| L3 | The line runs five generations with nobody's hand (g42, g43 so far) | the workflow | five records in a row, no run started or mended by hand | the loop holder (watch only) |
| N1 | The read's next piece moves on: rule 6 still names K1, which is done | `training/reads.py`, `tests/test_reads.py` | the read of g44 names a piece that is open on this board | B |
| E1 | Memory measured: none, notes, cell engrams, hive engram, all; taught and unseen kinds | `team/engram.py`, `training/hive_engram.py`, `team/notes.py`, `docs/RESEARCH.md` | a table in `docs/RESEARCH.md`; memory turned on only for an arm that gains | B (a sub-agent, running) |
| H1 | Held-out kinds: 0 of 6 at g43 (bar: half). Why the never-taught kinds fail, by cause from the members' programs | `team/solo.py`, `training/kinds/`, `docs/knowledge.json` | each failed held-out task of g44 has a cause; the largest is fixed and a re-sit gains | open |
| F1 | Right at the first try: 0.53 at g43 (bar 0.7) | `team/solo.py`, `training/lessons.py` | the first-try failures of g44's practice by cause; the largest fixed; the next generation's first try rises | open |
| S1 | Hours: 4.4 at g43 (bar 3). Practice 51, dream 51, train 176 minutes | `.github/workflows/grow.yml`, `training/grow.py` | one generation recorded under 3.5 hours with no fewer rows trained | open |
| C1 | Eight taught kinds' rows are too long for the 32-bit runners (508 pieces): contacts, words, sentences, bank, lru, calc, machine, schedule | `colab/`, `training/colab.py`, `training/lessons.py` | every taught kind has rows that train somewhere; counted by kind | waits on the owner (the Colab notebook is not started) |
| J1 | The join lessons are too long | `training/lessons.py` | join rows under 508 pieces and still right by their check | open |
| W2 | Wikidata sometimes returns a web page, not data | `team/tools/`, `training/kinds/` | the fetch retries or fails clearly; counted over one pulse | open |
| R1 | A right member is not lost: some member right, the body not | `team/solo.py` | the lost tasks of g44 by cause; the largest fixed; a re-sit on the same seeds gains | open |
| R3 | How many failures are a public site's fault (refused, slow, changed) | `training/exam.py`, the sandbox | counted over three pulses; above 1 in 20, the test sites are served on the runner | open |
| M2 | The self-reliance row written by the record job, not by hand | `scripts/selfreliance.py`, the workflow | a row for the newest generation appears by itself | open |
| T3 | The lesson's key lines weigh more (only if a verdict asks) | `training/grow.py`, `training/lessons.py` | members write the lesson's way in a re-sit; the kind's tasks pass | open, only on a verdict |

Done (do not redo): L1, L2, T1, T2, T4, K1, K2, M1, M3, W1; the memory pieces built (off); the CPU rule lab (PR 97);
the read fixed (PR 93); one way of working (`CLAUDE.md`, `NEXT_SESSION.md`, `scripts/cycle.py`, PR 98).

A piece missing here: propose it in the log with what it would move in the bars, then add its row.
