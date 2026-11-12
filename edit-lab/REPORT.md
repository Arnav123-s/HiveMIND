# Rejected-edit repair — status report (2026-11-08)

**Job:** beat the reproduced base scores of HiveMIND's two rejected LoRA edits
(coordinator, researcher), judged on the repo's own held-out evals
(`training/observe.py`, greedy, unmodified) in a copied tree. The repo itself
is never modified; everything here is additive.

**Win rules:** coordinator > 0.930 · researcher extract > 0.733 with plan ≥ 1.000.

## Results so far (coordinator, n=14)

| candidate | score |
|---|---|
| base (the bar) | **0.930** |
| rejected adapter ×0.5 (dose sweep) | 0.894 |
| specialized retrain, 1 epoch (56-row contrast set) | 0.849 |
| rejected adapter ×1.0 (as published) | 0.791 |

The specialized retrain fixed the targeted plan-size defect (case 1:
0.50 → 0.83) but scattered damage (case 14: 0.00, no parseable plan).
Scaling the rejected adapter interpolates toward base and never crosses it.
**No coordinator win yet.**

## Researcher

Anchors reproduced: plan 1.000 (n=10), extract 0.733 (n=5).
A gentle retrain (71 rows, 1 epoch, lr 1e-4 — a sixth of the dose that
cooked the original) is prepared and checkpointed but **not yet evaluated**.

## Decomposition attack (designed, data built, untrained)

Six micro-specialists split from the eval's own checks: `size_band`,
`pick_researcher`, `pick_browser`, `pick_coder`, `for_each`, plus the
specialized monolith as a 0.25-weighted style anchor. Rank-4 micro-LoRAs
composed by exact block-merge (`merge_n.py`) into one adapter the
unmodified harness can load. `run_micro.sh` trains, merges, evals.

## Also established

- Branch mining: coordinator/researcher adapters and training data are
  byte-identical on every branch. Nothing better exists upstream.
- Full trail, anchors, and incident log: `LEDGER.md`.

## Status: OPEN — blocked on compute, moving hosts

The VM's CPU throughput collapsed ~30–100× after a reboot (measured
1.3–2.1 GFLOPS; not fixable from inside the cell). Per Arnav's direction
the remaining compute (researcher train+eval, five micro-cell trains,
composite eval) is moving to ashp (GTX 1650 Ti, 32 GB RAM), where this
lab is already backed up. The job is **not closed** and no win is claimed.

## Coordinator repair contest — FINAL VERDICT (2026-11-10)
- WIN: synthv1-r4 pristine test 0.954 vs gate/base 0.930 (n=14, observe.py anchor protocol); paired 2W/12T/0L vs base. Dev: r2 0.8511, r4 0.9483, r16 0.9483 (base dev 0.7479), all regression-clean.
- Method that won: checker-in-the-loop synthetic data (240 attempts / 106 kept) + 11 micro rows = 117-row mix; thin LoRA retrain family. All surgery/dose/soup variants on the original adapter family remained below base (rejected 0.791, s50 0.894, coord-spec 0.849, drop14/soup50 dead by ceiling).
- Administration: first test run VM-restart-killed at 10/14 (running 0.936, ceiling 0.9543); completed via one identical-protocol rerun; partial preserved at results/test_synthv1_r4_partial10.log.
- Contest CLOSED per Arnav's 2026-11-09 18:46 PT decision. Researcher contest state stands as previously recorded (res-spec2 NO WIN, borderline).

## Overnight 2026-11-09/10 addendum
- Whole-hive battery: Part A specialists 5/7 bars met (tiny-hive 21/21 + 3/3 fail-closed; error-class 12/12; secret-line 10/12; commit-type 10/12; contract-judgment 7/12 PARTIAL; gap-move 4/10 PARTIAL). Part B composites: b1 arXiv lookup COMPLETED 1.0; b4 coder task FAILED (plan's unneeded research step + unreachable HF search host); b6 three-paper lookup FAILED (arXiv API 400/429/timeouts). b2/b3/b5 not run (time).
- Defect hunt Phase 0 (math dev): Qwen3-4B base 187/189 (98.9%), both fails capability-class, defect share 0% — Phase 2 ablation not triggered on math. IF base run unfinished tonight.
- Morning report: MORNING-REPORT-2026-11-10.md (full account, incl. the 93C thermal incident and the chunk+cool rule it produced).
