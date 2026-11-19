# NEXT SESSION: the one current handoff

Written 2026-11-19 22:10 UTC by D (session `session_014dX1CN76uUHTTTA9X1ZCHA`, branch
`claude/blissful-mccarthy-32ekqy`), the loop holder since B handed over. Whoever holds the loop keeps this page true. Older
handoffs are in `docs/history/`. How to work is in `CLAUDE.md`, and the whole story is in `docs/OVERVIEW.md`. Start with
`python scripts/cycle.py`. The prompts to start a session are in `docs/START_PROMPT.md`.

## Where the hive stands (2026-11-19 22:10 UTC)

- **Newest record: g51**, kept 50 against 49 of 64. **Two bars met for the first time:** hard kinds 0.79 (bar 0.78)
  and talk 8.2 of 10 (bar 8). Not met: held out 0 (half), first try 0.45 (0.7; old kinds 0.72, new kinds 0.25),
  hours 6.5 (3). g49 kept 49/64, g50 dropped (54 against 55).
- **g52 is running** (run 44594712108, started 19:05 UTC, record about 01:30 UTC). It runs main before PRs 112-117.
- **g53 is the first with PRs 113-117:** g48's practice fixes, the three text kinds' rows, extra seats on a crash
  (R1), and the general repairs for never-taught kinds (H1). Judge g53 against g51 on: new-kind first try (0.25),
  held out on the fixed exam (3 of 30), hard (0.79), and the hours (extra seats cost about 0.4 calls a hard task).

## In flight, and who has it

| What | Where | What to do |
|---|---|---|
| g52's record | Actions run 44594712108 | Read it; group its failures by cause beside g48's (the script `g48_causes.py` was the model) |
| D's scheduled wake | 2026-11-20 01:45 UTC | D reads g52 |

## Open, in order (the board in `docs/PLAN.md` has each row)

1. **CX:** the Codex side's `improve/verified-learning-loop` in small PRs, never whole (P1 done, PR 112). Next P3
   (schedule solver, off the path), P6 (delivered-answer checks, after a replay), P5a (engram fixes, engrams off).
   Hold back: engrams on by default and the subject hint in every exam prompt (only as one flagged generation);
   the saved-program bank in public chat (the owner's call, and its wrong-number problem first). Do not take its
   NEXT_SESSION/OVERVIEW edits (they say memory is on).
2. **H1:** held-out kinds: g51 3 of 30 on the fixed exam; 16 of 27 failed were near. General repairs merged (PR 117);
   next by g53's causes. The 11 far ones (no grasp of the method: edit, quotes, queue) need more than repairs.
4. **S1:** hours, 6.5 against 3 (train 219 minutes at g48).
5. **F1:** first try on new kinds (0.25 at g51), after g53 shows what PR 113 moved.
6. **V1:** g45's cause fixes: at g48, same-error stops fell 6 -> 2, dates/header and one-line data 2+1 -> 0;
   lesson templates pasted 2 -> 3, lone right member 3 -> 5 (R1).
7. **Y1, A1, G1, C1 (bank, calc, lru, machine, schedule still over 508), J1, D1, P1, W2, R3, M2, T3.**

## Done, do not redo

- **19 Nov late (D):** R1, extra seats when one answer is in and a member crashed (PR 116); H1's general repairs:
  text-as-number hint, overwritten value, slot values (PR 117). A fill lesson taking columns by position was
  rejected (brittle when pasted).
- **19 Nov (D):** main's tests green and the knowledge test isolated (PR 112, CX-P1); g48's four practice causes
  (PR 113, G48F); why K2 kinds had no lessons, three text kinds' rows fixed (PR 114, K2L). 6 held-out K2 kinds stay
  untaught on purpose; 6 'none made' kinds are left to the hive by design.

- **18 Nov evening:**
  - the strict gate and the read fixes (PR 102);
  - first try split by old and new kinds (PR 104);
  - the CPU rule lab's newer work (PR 103);
  - the checked deliveries and kept methods (PR 105);
  - the fixed held-out exam, the talk exam budget, the talk smoke and g45's cause fixes (PR 106);
  - chat from saved methods (PR 107);
  - the memory test: the gain was the short orders, memory stays off (E1).
  The orders A/B is built but off: it is moot on t80.
- **K1:** one kind per file in `training/kinds/`, with a golden fixture that keeps old exams the same.
  **K2:** 24 new hard kinds, 6 held out (`docs/KINDS.md` says how to add one).
- **M1:** the talk exam (`training/talk_exam.py`), 40 messages checked by code, in the harder version, wired
  into the gate (PR 96). It is written to `training/reports/talk/<gen>.json` and shown in the read and on the
  progress page.
- **Memory pieces** are built but OFF: per-cell engrams with lineage recall, the shared hive engram, notes
  written from failures, the gated engram scale, embedding match, and the hive fold. Measured (E1): no gain beyond the short orders.
- **The CPU rule lab** (the owner's experiment, PR 97, `training/reports/rule_lab/`): a child trained on 7 rows
  of a checked procedure solved 4 of 4 hidden-rule puzzles that its parents solved 0 of 4. All 81 recorded runs
  were re-scored and agree. This is research, not on the generation's path.
- **The read is written by the record job again.** The fix is a sys.path insert in `training/reads.py`, PR 93,
  with a regression test. g43's read was rewritten by hand.
- **Colab child waiting, memory guard, rows-left-out measured, paired gate, T1/T2/T4/L2** are all done; see
  `docs/AGENTS.md` and `docs/knowledge.json`.

## The owner

- Works from a phone and has no context. Give a few plain lines: what it is, what changed, what is next.
- Wants the hive to improve by itself until the final build (the five bars in `CLAUDE.md`).
- Wants sub-agents to do the hands-on work, while the loop holder judges and merges.
- The dashboard artifact "HiveMIND Progress" (claude.ai artifact Xi5BfLZnLLzvkhZJK72Hvr) draws the generations;
  refresh it after a record if your session has it.
