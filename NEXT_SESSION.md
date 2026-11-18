# NEXT SESSION: the one current handoff

Written 2026-11-18 04:40 UTC by B and brought up to g45 later that day (session `session_014dX1CNKMMabZ93Sdxn3fSK`, branch
`claude/vigilant-brahmagupta-rz3ab7`). Whoever holds the loop keeps this page true; older handoffs are in
`docs/history/`. How to work is in `CLAUDE.md`; start with `python scripts/cycle.py`. The prompts to start a session are in `docs/START_PROMPT.md`.

## Where the hive stands (2026-11-18, after g45)

- **Newest record: g45** (run 44261362737, 13:22 UTC), kept: 45 against 47 of 64 on its 8 seeds (easy 32/32,
  taught hard kinds 12 of 16 = 0.75, held out 0 of 9), first try 0.35, 5.6 hours, 1 of 20 slices lost.
- **The last five, after (before):** g41 58 (49), g42 54 (54), g43 52 (54), g44 43 (40), g45 45 (47).
  g44 was the first with the 24 new hard kinds (K2): its hard score is not comparable with earlier ones.
- **Talk first sat at g45:** 6.5 of 10 (route 5, fact 7, earlier 8, time 6).
- **First try:** g43 0.53, g44 0.36, g45 0.35. **Hours:** g43 4.4, g44 5.0, g45 5.6.
- **Four generations recorded with nobody's hand** (g42 to g45).
- **Bars against g45:** hard 0.75 (bar 0.78, read as a share since K2), held out 0 of 9 (bar half), first try
  0.35 (bar 0.7), talk 6.5 (bar 8), hours 5.6 (bar 3).

## In flight, and who has it

| What | Where | What to do |
|---|---|---|
| g47 | Actions, the line ("Generation") | When recorded: read `docs/reads/latest.md` and the graphs, check the next started by itself, log a line, tell the owner |
| Changes to the Python files, `grow.yml` and `training/reads.py` | another agent, on its own branch | Judge and merge when the proof is shown |
| The memory test (E1) | done on t17, one seed: hive engram 16/18 on seen kinds, off 6/18; unseen 0-1 of 4 for every arm | Memory stays OFF until a gain shows on t80 |

## Open, from the audit (ids on the board in `docs/PLAN.md`)

- **G1:** the gate kept bodies worse than their before (g43, g45); compare with the best body too.
- **X1:** a fixed held-out exam of about 30 tasks; 3 to 10 tasks is noise. Then **H1:** why held-out kinds fail.
- **P1:** one parent sits the pulse, so "parent alone" is measured; rule 4 can never fire without it.
- **F2:** first try for old and new kinds apart. Then **F1:** its largest cause.
- **T5:** a talk smoke run on the newest body after each record; no person has talked to it since 11-15.
- **C1:** the 8 long kinds train only on the 16-bit runners, or are shortened; no wait on Colab.
- **S1:** hours, 5.6 against 3.
- **M2:** the bookkeeping CSVs (`docs/*.csv`) stopped on 11-15/16.
- Not on the board yet: the 32-bit slices are still joined as equals (`training/merge.py`); HIVE_READ 40 and
  HIVE_JUDGED 10 are still on; the one-line trial never ran (`docs/DECISIONS.md`, status).

## Done, do not redo

- **K1:** one kind per file in `training/kinds/`, with a golden fixture that keeps old exams the same.
  **K2:** 24 new hard kinds, 6 held out (`docs/KINDS.md` says how to add one).
- **M1:** the talk exam (`training/talk_exam.py`), 40 messages checked by code, in the harder version, wired
  into the gate (PR 96). It is written to `training/reports/talk/<gen>.json` and shown in the read and on the
  progress page.
- **Memory pieces** are built but OFF: per-cell engrams with lineage recall, the shared hive engram, notes
  written from failures, the gated engram scale, embedding match, and the hive fold. They are waiting on the
  memory test above.
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
