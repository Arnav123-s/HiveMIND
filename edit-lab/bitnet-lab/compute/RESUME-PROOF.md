# RESUME-PROOF — checkpoint-resume, proven or not (Muse's work, Muse's side)

Question: does a run killed mid-training and resumed from its last checkpoint
reproduce the trajectory of the same run left uninterrupted? If yes, an
interrupted lab run stops costing its full length, and the 7–11 h confirmation
runs the scale program needs become possible on a VM that restarts.

## Setup

- Trainer: `compute/train_ckpt.py` (checkpointing copy of the lab trainer;
  `train.py` untouched). Checkpoints carry weights + vote counters + optimizer
  state + step/schedule position; a checkpoint retires (is deleted) when its
  run completes.
- Shape/recipe: champion — `--arm layered_half --rope`, seed 0, batch 16,
  held-n 32, 40 steps, checkpoints every 10 steps. OMP/MKL = 2 (lab pinning).
- **Run A (control):** uninterrupted, `proof/runA.log`. Complete: steps
  10/20/30/40 logged.
- **Run B (test):** `proof/runB.sh` — phase 1 trains with checkpoints, is
  `kill -9`'d ~2 s after the step-20 checkpoint lands (mid-training, not on a
  boundary), then phase 2 resumes in a fresh process from the surviving
  checkpoint to step 40. Success also requires the checkpoint file to be
  retired on completion.
- Pass bar: same seed both runs, so the resumed trajectory should agree with
  the control near-exactly; any divergence must be located (which step it
  enters at) and explained (e.g. the kill landing mid-step, RNG/data-order
  state), not waved at.

## Run A — control trajectory (from proof/runA.log)

| step | train loss | flips |
|---|---|---|
| 10 | 7.282 | 0.000% |
| 20 | 5.636 | 0.000% |
| 30 | 4.957 | 0.000% |
| 40 | 4.649 | 0.154% |

## Run B — kill/resume execution

Launched 2026-11-12 ~20:58 PT under heavy sprint contention (weights-reader
v3, kernels-attn bench, factory run, corpus-v3 build all sharing the 1.5 vCPU
quota — wall times below are contention-inflated; the trajectory math is not
affected by contention).

- Step 10 checkpoint saved: `proof/ckptB.pt`, 22,136,239 bytes, save time
  0.415 s. Step 10 line: **train 7.282, flips 0.000% — identical to Run A.**
- Step 20 checkpoint saved: 22,136,431 bytes, save time 0.499 s. Step 20
  line: **train 5.636, flips 0.000% — identical to Run A.**
- Driver then waited 2 s (phase 1 partway into steps 21+) and `kill -9`'d it.
  **The step-20 checkpoint survived the -9 on disk** (22,136,431 bytes —
  `ls` verified by the driver after the kill).
- Phase 2 relaunched in a fresh process with `--resume-from` that checkpoint:
  log line `RESUMED from proof/ckptB.pt at step 20 (elapsed 531.2s restored)`
  — step position and elapsed schedule both restored, not just weights.
- Post-resume step 30 checkpoint saved (22,136,687 bytes, 0.578 s). Step 30
  line: **train 4.957, flips 0.000% — identical to Run A.**
- _(step 40 + completion/retirement: pending)_

## A vs B — step-by-step comparison

_(pending)_

## Verdict

_(pending)_
