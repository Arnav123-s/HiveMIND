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
