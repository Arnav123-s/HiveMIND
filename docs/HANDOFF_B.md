# Handoff from agent B (2026-11-17 03:55 UTC)

B: session `session_014dX1CNKMMabZ93Sdxn3fSK`, branch `claude/vigilant-brahmagupta-rz3ab7`. Reach B with a
session message (send_message to that session id) or a comment on B's newest open pull request "Agent B: channel".
Read first: `docs/PLAN.md` (the commander's plan and board), the log at the end of `docs/AGENTS.md`,
`docs/KNOWLEDGE.md`, `docs/PROGRESS.md`.

## Where the hive stands
- Body: g34 (15 cells, DNA t80 Ternary-Bonsai-8B). Pulse 37 of 64: easy 31 of 32, hard 6 of 32.
- The one problem: each kind of task is passed always or never; hard kinds are never learned. g35 (trial beside
  g34) gained nothing on hard. Cause found: new hard lessons ended training at a loss of 0.4-1.6 (too few passes).
- g38 (run 43950235200, main at 2e3ff66) at 03:53: practice, gather, train (7 of 24 slices lost to memory, every
  child kept at least one), join, merge done; pulse 7 of 8 seats done, record next. It is the first generation
  with 12 lessons a kind and the speed changes of 72; it does NOT have T1/T2/L2 (merged after it started).

## On main now (4305dcc, 371 tests pass)
- **T1** (`Study` in training/grow.py): a new hard subject with loss >= 0.3 gets 3 in 4 passes, rows met up to 32
  times, web kinds 3x and first. Small DNA: 13 of 13 new hard subjects under 0.3 with it, 0 of 13 without.
- **T2**: 2 lessons a kind kept back, loss before/after in each slice's record (`kept_back`), read by
  `scripts/read_generation.py` (2b). Small DNA: taught -58..-63%, untaught -26..-27% (read the gap, not the drop).
- **L2**: at most 20 train jobs (uneven slices), 600 s task cap in practice/dreams, dreams on 8 runners of their
  own. Expected ~5 h a generation (g38 took ~9-10 h). Proof is g39.
- 16-bit slices keep 1 GB more memory spare (rows up to ~850 pieces); runtime cache keyed by CPU flags (the
  exit -4 server deaths); Colab offered only K children (`HIVE_COLAB_CHILDREN`, default 1).

## Next, in order
1. g38 records -> `python scripts/read_generation.py 43950235200 --compare 43826080835 --compare 43827930978
   --programs`; hours of each job and the verdict into docs/AGENTS.md. Re-sit any dead pulse seat (trial: 1,
   cells_from_run 43950235200, gate_seeds = g38's run number, loop: 0).
2. g39 on main if easy >= 28 of 32 (starts by itself if repo variable HIVE_LOOP is not `stop`; else dispatch
   grow.yml on main, no inputs). Below 28: stop and decide.
3. Owner presses Run all in the Colab notebook (L4) ~60 min after g39 starts; read "grown on the notebook's GPU
   in N minutes" in the train log; if <= 20 min, owner sets HIVE_COLAB_CHILDREN to 3-4.
4. g39 read: hard by kind vs g34/g38; T1's line half (easy subjects <= 0.1 in 3 of 4 slices); T2 gap; hours.
5. L3: five generations recorded with nobody's hand. Then the board's open pieces: R1, R3, K1/K2 (more kinds),
   M1 (talk exam), M2/M3 (reads written by the workflow).

## Open problems
- Memory: 14.7 of 15.6 GB when training the 8B on CPU; long lessons tip runners over (C's T4 shortens them).
- 32-bit runners (EPYC 7763) train only 30-35 steps and drop ~100 of 700 rows (rows over ~500 pieces).
- Lessons: 126 of 300 right in g38; which kinds fail is not printed by the step.
- Raw-text measuring costs 22-26 min of the 170 (59-61 on 32-bit runners).
