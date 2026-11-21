# NEXT SESSION: the one current handoff

Written 2026-11-21 18:15 UTC by D (session `session_014dX1CN76uUHTTTA9X1ZCHA`), who hands over the loop. How to work is
in `CLAUDE.md`; the story is in `docs/OVERVIEW.md`. Start with `python scripts/cycle.py`. GitHub here: `gh api` REST
only (the GitHub MCP tools are retired). Older handoffs: `docs/history/`.

## Where the hive stands (g60, recorded 2026-11-21 18:04 UTC)

- **g60 kept**, 48 against 47. **Met:** hard kinds 0.78 (bar 0.78), talk 8.2 (bar 8). **Not met:** first try 0.53
  (bar 0.7; old kinds 0.92, new 0.30), held out 1 of 30 on the fixed exam (0 of 10 kinds; bar half), 6.3 h (bar 3).
- Best readings so far: hard 0.80 (g55), first try 0.72 (g57), talk 8.8 (g52). First try and talk swing a lot
  between generations (96 practice tasks, 40 talk messages): five bars on one generation needs margin above each.
- The line runs by itself: g61 started 18:04 UTC on main (same code as g60).

## In flight

| What | Where | Note |
|---|---|---|
| g61 | grow.yml run 61, started 18:04 UTC 21 Nov | record due about 00:30 UTC 22 Nov |
| No helper, no scheduled wake | - | D's helper on the runner memory cap was stopped unfinished (its work was local only) |

## Open, in order

1. **Runners lost to memory starvation (S1).** 2-4 of 20 train slices are lost every generation (g60: data s1/3,
   data s2/3, words s1/3, code2 s0/2). GitHub's annotation: "The hosted runner lost communication ... starves it for
   CPU/Memory". The step never ends, no log survives, so PR 130's timeouts cannot act. Fix: run `grow.py train` in
   the train job at low priority (nice, ionice) inside a memory-capped cgroup (`sudo systemd-run --scope -p
   MemoryHigh/MemoryMax` sized from `free -m`, with a fallback), so the kernel kills the trainer, not the runner;
   MemoryGuard should read the cgroup limit. Then consider PR 135's trainer memory cut alone (peak 12.17 -> 10.48 GiB
   on a matched pair, identical updates).
2. **Hours (S1).** 5.1-6.7 h. PR 138 capped the measuring before training (it took 92 of 170 min); train is ~175 min
   when no slice is lost, gate ~55-90. Next: if more training time per slice does not lift hard kinds, cut the
   170-minute budget; practice 26-53 and dream ~60 run side by side.
3. **Held-out kinds (H1).** 0-1 of 10 kinds for weeks. g51 study: 16 of 27 failures near (shape, pasted template,
   overwritten value; general repairs merged, PRs 117, 125), 11 far (no grasp of the method). Exam workers' own
   files are now kept (PR 129: gate-work `runs/exam/worker-evidence`): read them by cause first.
4. **First try on new kinds (F1).** Old kinds ~0.9, new (K2) 0.28-0.52. First try counts one program, no hint
   (`scripts/selfreliance.one`): only lessons move it, not repairs. Compound tasks are solved part by part (PR 126).
5. Board rows in `docs/PLAN.md`: Y1, A1, G1, C1 (lru rows still over 508 pieces), J1, D1, P1, W2, R3, M2, T3.

## Codex side (other agent, same account)

Judged, not taken into the line: PR 122 (a one-kind answer key), 131 (merged anyway from the owner's account;
checked: inert by default, tests pass), 135 and 136 (their own numbers show no held-out gain: 2/30 and 4/30 against
3/30). Research only: 123, 132-134. Taken: PR 124 (worker files kept). A trial run on the shared 20 runners stalls
the line (run 58 was cancelled on the owner's word): start one only between generations.

## Done, do not redo (D, 19-21 Nov)

PRs 112-121, 125-130, 137-139: main's tests green; g48's practice causes (answers kept at the cap, guard on spending
code, two-part agreement, data as a file); three text kinds' rows fit; extra seats when a member crashed (R1); held-out
general repairs; the gate split into 33 jobs; slices end near their budget and are killed from outside at MIN+25;
data-format notes and hints; compound tasks part by part with rows per part; spec-detail lessons; measuring before
training capped. Earlier: see `docs/history/` and the log in `docs/AGENTS.md`.
