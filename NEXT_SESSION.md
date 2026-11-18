# NEXT SESSION: the one current handoff

Written 2026-11-18 04:40 UTC by B (session `session_014dX1CNKMMabZ93Sdxn3fSK`, branch
`claude/vigilant-brahmagupta-rz3ab7`). Whoever holds the loop keeps this page true; older handoffs are in
`docs/history/`. How to work is in `CLAUDE.md`; start with `python scripts/cycle.py`. The prompts to start a session are in `docs/START_PROMPT.md`.

## Where the hive stands (2026-11-18 04:40 UTC)

- **Newest record: g43** (run 44188515917), kept by the paired gate: 52 against 54 of 64 (easy 32/32, hard 20
  against 22, held out 0 of 6 against 1 of 6), first try 0.53, 4.4 hours, 0 of 20 slices lost.
- **g42 and g43 were each started by the one before**, with nobody's hand.
- **g44 is running** (run 44225157318, started 02:41 UTC). It is the first generation with the 24 new hard kinds
  (K2) and the first with the talk exam in its gate. Its record is due about 07:20 UTC.
- **Bars against g43:** hard kinds with lessons 20 of 26 = 0.77 (bar 18/23 = 0.78), held out 0 of 6 (bar half),
  first try 0.53 (bar 0.7), talk not measured yet (bar 8 of 10), hours 4.4 (bar 3).

## In flight, and who has it

| What | Where | What to do |
|---|---|---|
| g44's record | Actions run 44225157318 | When recorded: read `docs/reads/latest.md` and the graphs, check g45 started by itself, log a line, tell the owner |
| A memory test: none / notes / cell engrams / hive engram / all, on taught and unseen kinds | Running in B's session (a local sub-agent); not pushed yet | B merges it when it reports. Memory stays OFF (`HIVE_ENGRAM*`, `HIVE_NOTES` unset) unless it shows a gain |
| A scheduled wake at 07:25 UTC | Into B's session | B reads g44. If a newer session holds the loop by then, B only hands over and stops |

## Open, in the order to take them

1. **Rule 6 of the read's next-piece logic** (`training/reads.py`) still names K1 as next, but K1, K2 and M1 are
   done. Advance it: next pieces come from what g44's chain shows for the new kinds.
2. **Eight taught kinds have rows too long for the 32-bit runners** (508 pieces): contacts, words, sentences,
   bank, lru, calc, machine, schedule. All but contacts fit a 16-bit runner (about 814). The fix is the owner's
   Colab notebook (`colab/`): **the owner has not started it yet.** Ask once, plainly. If it runs fast, the owner
   raises the repo variable `HIVE_COLAB_CHILDREN`.
3. **Held out is the weakest bar** (0 of 6). The new hard kinds hold 6 back on purpose; see whether g44 carries
   any.
4. **Hours:** 4.4 against 3. Train is 176 of 264 minutes; practice and dream are 51 each.
5. Small open items:
   - the join lessons are too long;
   - wikidata sometimes returns a web page, not data;
   - 32-bit runners train fewer steps;
   - g42 and g43 have no finding in `docs/knowledge.json` yet.

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
