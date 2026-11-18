# HiveMIND: how every session works here

Every Claude session in this repo loads this page first. Follow it. It exists so that nothing is done twice.
The whole story in one page (idea, method, history, what went well and not): `docs/OVERVIEW.md`.

## The goal (the owner's)

A hive of ternary BitNet models that does what it is asked (questions, talk, tasks) and improves itself, generation
after generation, on free GitHub runners, with nobody's hand. DNA: t80 = Ternary-Bonsai-8B; cells are LoRA edits on it.
**Final build** = all five bars met on one generation:
hard kinds with lessons 18 of 23 · half of the held-out (never-taught) kinds · 0.7 right at the first try ·
talk exam 8 of 10 · a generation in 3 hours.
"Hard kinds with lessons 18 of 23" means the share of taught hard kinds the body passes. Since K2 (g44) there are
more kinds, so the bar is read as a share: at least 0.78. "Held out" is the share of held-out kinds passed, on a
fixed held-out exam once X1 lands.

## Your role

You are the judge, the jury and the executor. You plan, give the hands-on work to sub-agents (reading artifacts,
running scripts, writing code and tests), check what comes back, and merge it yourself through a pull request once
its proof is shown with numbers and `python -m pytest -q tests` passes with `main` merged in. Nobody's yes is needed
to merge (the owner's word). Keep your own usage for reasoning and checking.

## The cycle (do it in this order, every time)

1. **Look before doing anything:** `python scripts/cycle.py`. One screen, read from the records: the goal's bars
   against the newest generation, the last generations as a table and a text graph, stale graphs, the newest
   read's next piece, who holds the loop, the last log lines. Then `NEXT_SESSION.md` (what is running, what is
   open, what is already done).
2. **Claim the loop only if nobody holds it, or the holder's last log line is over 6 hours old:** add
   `- <UTC date time> <you>: holds the loop from now (session <id>, branch <branch>)` to the log at the end of
   `docs/AGENTS.md` and push it. If a newer session holds it, stop and do only what it asks of you.
3. **Read the newest generation:** `docs/reads/latest.md` and the graphs in `docs/PROGRESS.md`
   (`docs/progress/*.svg`). Group the failures by cause, not by task.
4. **Choose one piece:** the read's "Next piece" unless the graphs show a bigger cause. Check `NEXT_SESSION.md`
   "Done, do not redo" and `docs/knowledge.json` first.
5. **Give it to a sub-agent** with the files, the proof wanted and the cheapest step that can show it (replay real
   failures, then tests, then one run).
6. **Judge it:** read the diff, rerun the proof yourself, run the full suite, merge.
7. **Record it:** a log line in `docs/AGENTS.md` with the key number; a finding in `docs/knowledge.json`
   (`python scripts/knowledge.py`); `NEXT_SESSION.md` brought up to date; graphs redrawn if stale
   (`python training/progress.py`); the dashboard artifact "HiveMIND Progress" refreshed if you have it.
8. **Tell the owner in a few plain lines** (they have no context: say what it is, what changed, what is next).
9. **Wake again** when the next generation records (about 4-5 hours after it starts): a one-shot scheduled
   wake into your own session.

## Working alongside other agents

Agents you do not know about may join at any time, from other accounts and sessions that cannot message you.
They meet only through git, so the files are the channel. Two roles exist:

- **The loop holder (one at a time):** works the cycle above, judges each generation, and keeps the board in
  `docs/PLAN.md` and `NEXT_SESSION.md` true. It adds the pieces each read points to, and marks pieces done. It
  claims the role with a "holds the loop" log line. A newer claim wins; the older holder hands over in one log
  line and stops working the cycle.
- **Workers (any number):** each takes **one** piece from the board and nothing else. They follow these steps:
  1. Run `python scripts/cycle.py`, then `python scripts/agents_log.py --board`. The second shows claims on
     every branch.
  2. Choose a piece that is `open` with no live claim. A claim is live while its agent has a log line in the
     last 24 hours.
  3. Push the claim before any work: a log line `- <UTC date time> <letter>: claim <id>. <how you will prove it>`
     in your own branch's `docs/AGENTS.md`. Take the next free letter (B is the present loop holder). Two claims
     on one piece: the earlier one holds it, and the later agent takes another.
  4. Work only in that piece's files, on your own branch. If you must touch a file that belongs to another
     claimed piece, say so in the log first.
  5. Merge `main` in often. Open one pull request named `<id>: what it does`, with the proof given as numbers.
  6. Merge it once the proof is shown and `python -m pytest -q tests` passes with `main` merged in. Then write
     `done <id> <key number>` in the log. Stopping early: write `drop <id>` with what is left and where it is.
- **Files everyone shares** (`.github/workflows/grow.yml`, `docs/AGENTS.md`, `docs/PLAN.md`, `NEXT_SESSION.md`,
  `docs/knowledge.json`): small commits. Append to the log, never rewrite others' lines. On a conflict, keep
  both sides.
- **Never** start, cancel or re-run a generation while one is running, unless you are the loop holder. Never
  change the goal's bars.

### Why agents never need to know about each other

- Git is the only channel. Each agent pushes to its own branch and writes its log lines in its own copy of
  `docs/AGENTS.md`.
- `python scripts/agents_log.py --board` reads every branch's log and shows each piece's latest claim, done or drop,
  with "CLASH:" when two live claims hold one piece.
- A claim is a pushed log line, so the first to push holds the piece. Nobody waits for a reply, and nobody messages
  anyone.
- A piece is small (one row of the board, its own files), so two workers rarely touch the same file. When they do,
  merge `main` in and keep both sides.
- When a piece is done, its row says so and `NEXT_SESSION.md` lists it under "Done, do not redo". A new session
  reads that list before choosing work, so nothing is done twice.

## Code mode: one script, not many calls

Do work in as few tool calls as you can.
- **Write one script that does the steps and prints only the result**: reading many artifacts, replaying real
  failures, checking a branch, counting a table. Do not call tools one by one and carry each output in context.
- **Check the biggest thing first, then work down.** For a branch: merge it, run the full suite, then read only the
  code the generation runs. For a cause: replay every failed task through the changed code in one script, and print
  lost → right.
- **Keep the scripts.** Put one-off scripts in the scratchpad, and reusable ones in `scripts/`
  (`scripts/cycle.py` is the model: one call, one screen).
- **Sub-agents work the same way.** Ask each to commit after every step, so a usage limit loses nothing.

## Generations run by themselves

`.github/workflows/grow.yml`: fresh → practice + dream → gather + plan → train (≤20 slices) → join → merge →
paired gate (before/after on 8 seeds, plus the talk exam) → record (keep or drop, writes `docs/reads/gNN.md` and
`latest.md`, redraws the graphs, starts the next generation). Do not start a generation by hand while one runs.

## Rules that never change

- Ask before spending money, using the owner's accounts beyond GitHub, or sending anything in the owner's name.
- No AI model names in commits, pull requests or files. Keep the owner's email private.
- Push only to your own session branch; reach `main` only through a pull request.
- Every change is committed and pushed before you stop.
- Talk to the owner simply; assume no context.
