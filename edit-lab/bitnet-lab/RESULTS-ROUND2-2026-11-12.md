# Muse's work — written by Muse, on Muse's side. Fable's HiveMIND was read read-only; nothing on Fable's side was touched.

# BitNet round 2 — overshoot carry + two-stage cooldown (2026-11-12)

Arnav's order: "find how to make bitnets better, work on bitnets." Two improvement
levers, each tested as ONE change on top of the current best stack, 3 seeds × 8 min,
same corpus (~5.92M pieces), same held set (128 windows), same seeds and discipline
as every prior arm. No tuning between seeds, no extra seeds.

**Baseline (not re-run): layered_half + rotary + plain votes — held 2.8580 ± 0.0161**
(seeds 2.8765 / 2.8477 / 2.8497; steps 154–170; mechanism state 2,211,840 B).

**Standing bar for adoption: beat the baseline mean by >2 sd AND >0.01, i.e. held < 2.8258.**

## ARM A — overshoot carry (`layered_half_rope_carry`)

The change: in the layered vote trainer, counters no longer clamp at ±V and no
longer reset to zero on a flip — a flip keeps `count − sign·V`, so leftover vote
evidence carries into the new counter (the direct-trainer study's top untested
lever). Counters widen int8 → int16 so they can hold the overshoot.

| seed | held loss | steps |
|------|-----------|-------|
| 0 | 2.8751 | 154 |
| 1 | 2.8794 | 158 |
| 2 | 2.8737 | 158 |

**Mean 2.8761 ± 0.0030 — that is +0.0181 WORSE than baseline. REJECTED.**

Notes: every carry seed sits at or above the baseline's worst seed, and the three
seeds cluster very tightly, so this is not noise in carry's favour waiting on more
seeds. Flip share (0.0011) and the final state histogram are nearly identical to
baseline — at V=32 with the one-flip-per-step rule, discarded overshoot was
apparently never the bottleneck. Carry also costs more state: 3,981,312 B vs
2,211,840 B (+80%, the int16 counters). Worse result at higher cost; nothing to keep.

## ARM B — two-stage cooldown (`layered_half_rope_cooldown`)

The change: Microsoft b1.58-style cooldown applied to the AdamW-trained parts ONLY
(embeddings, norms, per-layer scales). Stage 1 (first half of the run) at the
current constant lr 1e-3; stage 2 (second half) with lr decayed linearly toward
zero. **The vote rule — threshold V=32 and the median gate — never changes. This is
NOT vote-threshold annealing: the earlier `anneal` arm moved the vote threshold and
lost badly (3.85); it was not retested here.** Honest caveat: this trainer is built
with weight decay 0, so the schedule's weight-decay component scaled a zero —
weight decay was a no-op in this arm; only the lr actually decayed.

| seed | held loss | steps |
|------|-----------|-------|
| 0 | 2.9828 | 148 |
| 1 | 2.9622 | 155 |
| 2 | 2.9671 | 152 |

**Mean 2.9707 ± 0.0108 — that is +0.1127 WORSE than baseline. REJECTED, clearly.**

Notes: every cooldown seed is worse than every baseline seed (best cooldown 2.9622
vs worst baseline 2.8765) — no overlap at all. Cooldown runs took slightly fewer
steps (148–155 vs baseline 154–170), but step differences elsewhere in this lab
move held loss by ~0.05 at most; a 0.113 gap is the schedule itself: halving the
AdamW parts' effective learning in the second half starves the embeddings, norms
and scales that the vote-trained weights depend on. On this rig, at this budget,
the published-recipe cooldown hurts. The constant-lr best stack stands.

## Verdict

**Neither lever is adopted. The best stack is unchanged: layered_half + rotary +
plain votes, held 2.8580 ± 0.0161, state 2,211,840 B.** Both levers are now tested
and closed — carry (evidence discarded at flips is not the bottleneck) and
AdamW-side cooldown (hurts at this scale/budget). Remaining untested directions
from the study stand as before: train on measured failures, longer/fairer trials.

## Code changed (all in this lab, Muse's side only)

- `train.py`: `--carry` and `--cooldown` flags on the `Layered` trainer (layered
  arms only; labels recorded as `layered_half_rope_carry` /
  `layered_half_rope_cooldown`). Carry: int16 counters, no ±V clamp, flip keeps
  `count − sign·V`, state-bytes formula updated (4·n + n//2). Cooldown: per-step
  lr/wd multiplier on the AdamW param groups only (1.0 in stage 1, linear to 0 in
  stage 2); the vote block never sees the schedule.
- `run_round2.py`: the driver — waits for a free lab past 11:05 PT, skips jobs
  already in `runs.jsonl`, one run at a time, OMP/MKL pinned to 2, refuses to
  start a run that cannot finish by the 13:00 PT hard stop.
- `runs.jsonl`: all six round-2 records appended (3 carry + 3 cooldown).
- Logs: `round2-driver.log`, `sweep.log`.

## Run-integrity note

Two runtime restarts killed in-flight runs (cooldown seed 0's first attempt at
~11:32 PT and seed 1's first attempt at ~11:48 PT). Both were re-run from scratch
under identical settings — same seeds, same 8-minute budget, no changes of any
kind between attempts — and only the completed re-runs are recorded in
`runs.jsonl`. All six recorded runs finished before the 13:00 PT hard stop
(last run done 12:10 PT).
