# NEXT SESSION: the one current handoff

Written 2026-11-18 23:40 UTC by B (session `session_014dX1CNKMMabZ93Sdxn3fSK`, branch
`claude/vigilant-brahmagupta-rz3ab7`). Whoever holds the loop keeps this page true. Older handoffs are in
`docs/history/`. How to work is in `CLAUDE.md`, and the whole story is in `docs/OVERVIEW.md`. Start with
`python scripts/cycle.py`. The prompts to start a session are in `docs/START_PROMPT.md`.

## Where the hive stands (2026-11-18 23:40 UTC)

- **Newest record: g47** (run 44313055326), kept at a tie: 47 against 47 of 64. Easy 31/32, hard 16/32, held
  out 0 of 6 (pulse). First try 0.39. Talk 6.2 of 10 (route 6, fact 7, earlier 7, time 5). 5.2 hours.
- **Five generations were recorded with nobody's hand** (g42 to g45, g47). The g46 run was a cancelled
  duplicate from the old cron.
- **g48 is running** (run 44371926721, started 18:38 UTC; its record is due about 00:00 UTC). It runs with the
  strict gate (after >= before) and the fixed reads.
- **g49 will be the first generation with all of PR 106:**
  - the fixed held-out exam (30 tasks);
  - the talk exam's 45-minute budget;
  - the talk smoke;
  - g45's cause fixes;
  - the checked deliveries of PR 105.
- **Bars against g47:** none of the five is met. Hard 0.74 (≥ 0.78), held out 0 (half), first try 0.39 (0.7),
  talk 6.2 (8), hours 5.2 (3).

## In flight, and who has it

| What | Where | What to do |
|---|---|---|
| g48's record | Actions run 44371926721 | Read it; check that g49 started by itself; group failures by cause (V1 starts at g49) |
| B's scheduled wake | 2026-11-19 00:15 UTC, into B's session | B reads g48. If a newer session holds the loop by then, B hands over and stops |

## Open, in order (the board in `docs/PLAN.md` has each row)

1. **V1:** prove g45's cause fixes on g49. Group g49's failures by cause from its gate artifacts and set them
   beside g45's:
   - module kinds stopping on the same error: 6;
   - answer shape: 4;
   - a right member lost at agreement: 3, plus 3 in practice;
   - a lesson template pasted onto another question: 2;
   - dates and header rows: 2;
   - one-line data not given: 1;
   - site walk: 1.
2. **Y1:** the hive keeps its own verified programs (practice → the fieldwork bank) and answers from them before
   calling members. This is where the hive starts to learn from its own work, not only from hand-made lessons.
3. **H1:** held-out kinds by cause, on the fixed exam (from g49).
4. **F1:** first try by cause. Practice now records old and new kinds apart. Compound tasks were 48 of 96 with
   8 right at g45.
5. **A1:** talk routing, 6 of 10. "What's 8 plus 4?" was sent to work.
6. **S1:** hours, 5.2 against 3. The gate grows by about 10 to 25 minutes from g49.
7. **G1:** also compare against the best body (g41, 58/64).
8. **C1 and J1:** rows too long for the 32-bit runners. No wait on Colab.
9. **D1:** saved methods live in the GitHub chat (the WebAssembly runtime on talk.yml, and `HIVE_BANK`).
10. **P1, W2, R1, R3, M2, T3.**

## Done, do not redo

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
- **Memory.** E1 found that short orders explained the apparent gain on t17. This review branch enables compatible engram recall in normal chat and work and adds an advisory channel for six subjects. The current tests cover emitted advice, actual answers, and retention of local lessons. [Results and scope](training/reports/domain-memory/README.md)
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
