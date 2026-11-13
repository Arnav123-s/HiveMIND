# Muse's work — Muse's side

# Dream prototype: consolidation dream (bitnet-lab/dream-proto)

The smallest runnable test of a **consolidation dream** on the champion
chassis — `layered_half` + rotary (`Tiny(layers=2, rotary=True)` +
`Layered`, votes 32), imported from `../train.py`, trained on the lab's
`corpus.u16` exactly as `train.py` handles it (batch 32, CTX 256, windows
via `offsets(random.Random(seed), …)`, which excludes held windows by
construction).

Two phases, one run:

1. **Wake (phase 1, `--steps1` steps).** Ordinary Layered training. On the
   same forward pass used for training, per-window losses are computed
   (`cross_entropy(..., reduction='none')` reshaped per window and averaged
   over its tokens; the batch training loss is that vector's mean — the
   same number `train.py` trains on). The offsets of the highest-loss
   windows are kept in a buffer: top-K by loss (`--buffer-k`, default 512),
   deduped by offset, keeping an offset's highest loss if it is drawn again.
2. **Dream (phase 2, `--steps2` steps).** Batches are drawn *only* from the
   buffer offsets (sampled with replacement, same seeded `Random`), and the
   vote threshold is lowered — `trainer.votes = 8` (`--dream-votes`;
   `Layered.step` reads `self.votes` every step, so this is a clean lever) —
   then restored to 32. Idea: hard windows are where the model is furthest
   from fitting; replaying them while flips are cheaper lets weights that
   were a few votes short consolidate.

Cost note: per-window scoring costs **no extra forward pass** — it reuses
the training forward, only changing the loss reduction. The buffer itself
is at most 512 `(offset, loss)` pairs.

Held loss (`held_loss`, the lab's fixed 128 held windows) is measured at
init, after phase 1, and after phase 2, and printed with the step counts
and buffer stats (buffer size, mean buffered loss vs overall phase-1 mean
loss). Every run appends one JSON line to `proto-runs.jsonl` **in this
directory** — prototype results stay here and are *not* written to the
lab's `runs.jsonl` until/unless the mill adopts the candidate.

## The 2×2 design (why the controls exist)

Phase 2 mixes two changes at once — *which* windows, and *how cheap* flips
are. `--control` separates them; all modes run identical `--steps1` +
`--steps2` totals and build the same buffer in phase 1:

| `--control` | Phase-2 windows | Phase-2 votes | Reads as |
|---|---|---|---|
| `full` (default) | buffer (hardest) | 8 (`--dream-votes`) | the dream itself |
| `target` | buffer (hardest) | 32 | targeting alone |
| `threshold` | random (`offsets()`) | 8 (`--dream-votes`) | lowered threshold alone |
| `none` | random (`offsets()`) | 32 | step-matched baseline: phase 2 is just more ordinary training |

### The freeze axis (attribution control, D-006)

Even a winning `full` run is ambiguous: phase 2 moves the model through
*two* mechanisms at once — ternary vote flips **and** ordinary AdamW drift
on the embeddings, norms and per-layer scales. `--freeze
{none,votes,ternary}` (default `none`) prices them apart:

| `--freeze` | What is held still in phase 2 | What can move |
|---|---|---|
| `votes` | the AdamW parts — `trainer.opt.step` is monkey-patched to a no-op for phase 2 and restored after; the vote-counter logic in `Layered.step` lives outside `opt.step`, so flips still happen | only `t1`/`t2` flips |
| `ternary` | the vote state — `t1`/`t2`/`c1`/`c2` are snapshotted before phase 2 and restored (plus `install()`) after, before held loss is measured | only AdamW |
| `none` | nothing | both, as usual |

`--freeze votes` with `--control full` is the frozen-AdamW dream (design
note D-006): if it keeps most of `full`'s gain, the dream is really vote
consolidation; if `--freeze ternary` keeps the gain instead, it was just
AdamW training on hard windows. The freeze setting is recorded in every
`proto-runs.jsonl` line. A full factorial (4 controls × 3 freezes) is
**not** required for the smoke — the option exists, and one or two freeze
runs alongside the four controls are enough for a first attribution read.

## Real smoke (run on a free lab, one process at a time)

```bash
cd ~/workspace/edit-lab/bitnet-lab
PY=~/workspace/edit-lab/fable-validation/venv/bin/python
for c in full target threshold none; do
  OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 $PY dream-proto/run_dream_proto.py \
    --control $c --seed 0 --steps1 120 --steps2 30
done
# attribution spot-checks (same budgets/seed):
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 $PY dream-proto/run_dream_proto.py \
  --control full --freeze votes    --seed 0 --steps1 120 --steps2 30
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 $PY dream-proto/run_dream_proto.py \
  --control full --freeze ternary  --seed 0 --steps1 120 --steps2 30
```

Suggested budget: `--steps1 120 --steps2 30`, about 5–8 minutes per mode on
a free lab. `--minutes` (default 20) is only a safety cap; a run that hits
it records `"truncated": true` and its numbers are not comparable.

## What to compare

- Within a mode: `held_phase1 → held_phase2` — did phase 2 help at all,
  beyond init?
- Across modes at the same seed: `held_phase2` for `full` vs `target`
  (isolates the threshold lever on hard windows), `full` vs `threshold`
  (isolates targeting at cheap flips), and everything vs `none` (the
  step-matched baseline — a dream mode only counts if it beats simply
  training 30 more ordinary steps).
- Sanity: mean buffered loss should sit clearly above the phase-1 mean
  loss; if it does not, the buffer is not selecting hard windows and the
  targeting reading is void.

One seed is a smoke, not a result. A candidate needs the same pattern over
seeds 0–2 before the mill should look at it.

## Status

Honest status: code verified by compile/import, and the freeze helpers
were exercised on a real `Tiny` + `Layered` (patch → no-op → restore;
snapshot → mutate → restore). A micro dry run (`--steps1 3 --steps2 2`,
base code, before the freeze axis was added) was attempted on a busy lab:
it completed phase 1 and was killed by its own 175 s timeout during
phase 2 — no run was recorded in `proto-runs.jsonl`, and its partial
held numbers are a code-path check only, never results. No result
claimed until run on a free lab.
