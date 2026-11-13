# DREAM-PROTOTYPE — the BitNet vote trainer's first dream (Muse's work, Muse's side)

<!-- Muse's work — Muse's side of the BitNet lab. Written 2026-11-12 by the dreaming
department coordinator from the department's four specialist returns. Companion to
mill/CANDIDATES-D.md (the full candidate family + evaluation protocol). train.py was read
in full and NOT edited; IDEA-POOL.md NOT edited; nothing on Fable's side touched. -->

## The judgment: which dream is strongest

**D-003 — the consolidation pass** (hard-window replay at a lowered vote threshold) is the
department's pick for first prototype, and it is what was built.

Why: it is the only variant whose mechanism is *native* to the vote trainer. During any
V=32 run, a large mass of vote counters sits at |c| ∈ [8, 32) — real, accumulated,
majority-signed evidence that never resolves before the run ends, leaving those weights
governed by stale early structure. That bank is not a metaphor: it is directly readable off
`trainer.c1/c2`, and the lever that spends it already exists in train.py — `Layered.step()`
re-reads `self.votes` every step for both the counter clamp and the flip threshold, so a
runner lowers the threshold mid-run with one assignment. D-003 spends the bank where it
matters (batches with a 24/32 hard-window majority, the buffer being the run's own worst
windows) for a short final phase, and its kill criteria are written around its own segment
(net-negative phase, unrecovered resolution wave), so it can fail cheaply and informatively.

The department's honest disagreements, and how they were resolved:

- The core-variants specialist ranked **D-001 (mistake replay) first** — it is the closest
  relative of the factory's proven waking-dream win and its downside is bounded. Resolution:
  D-001 shares its entire buffer machinery with D-003 (the prototype's phase-1 buffer *is*
  D-001's buffer), so D-001 is the prototype's `--control target` cell away from existing;
  it runs second at near-zero extra build cost.
- The novel-variants specialist argued **D-006 (frozen-AdamW) should be prototyped first**,
  because every other dream runs with AdamW live and so cannot attribute a win to ternary
  consolidation vs ordinary continuous-parameter drift. The argument is correct — and it is
  answered inside this prototype rather than before it: D-006 is implemented as the
  prototype's `--freeze` axis (below), so the attribution question is priced in the first
  smoke instead of after a family of ambiguous results.

## What was built

`dream-proto/run_dream_proto.py` (+ `dream-proto/README.md` with the full design) — a
two-phase runner on the champion chassis (`Tiny(layers=2, rotary=True)`, `Layered`,
batch 32, CTX 256), importing `Tiny, Layered, offsets, held_windows, held_loss` from
train.py. train.py is not modified; results go to `dream-proto/proto-runs.jsonl`, never to
the lab's `runs.jsonl`.

- **Phase 1 (wake):** ordinary V=32 training for `--steps1` steps. Per-window losses are
  computed on the *same* forward pass used for training (`reduction='none'` reshaped per
  window — zero extra forwards), and a top-K buffer of worst window offsets is maintained
  (default K=512, deduped, each offset keeping its worst loss). Buffer offsets come only
  from `offsets()` draws, so held windows are excluded by construction.
- **Phase 2 (dream):** `trainer.votes` is set to `--dream-votes` (default 8) and the runner
  trains `--steps2` steps on buffer windows only, then restores V=32 (in a `finally`).
- **Held loss is measured at init, after phase 1, and after phase 2** and printed/recorded
  with step counts and buffer stats (size; mean buffered loss vs phase-1 mean loss — the
  sanity check that the buffer really is the hard tail).

**Controls — the 2×2 from CANDIDATES-D §2 is built in** via `--control`:

| mode | phase-2 windows | phase-2 V | reads as |
|---|---|---|---|
| `none` | fresh `offsets()` | 32 | CONTROL-D (step-matched baseline) |
| `target` | buffer (hard) | 32 | targeting-only cell |
| `threshold` | fresh `offsets()` | 8 | threshold-only cell |
| `full` | buffer (hard) | 8 | **D-003 candidate** |

All modes build the identical phase-1 buffer and run identical total steps, so the four
cells separate targeting, threshold, and their interaction at equal budget — the exact
control structure whose absence forced the layered-votes retraction.

**Freeze axis (D-006 folded in)** via `--freeze {none,votes,ternary}`: `votes` patches
`trainer.opt.step` to a no-op during phase 2 (AdamW parts bit-frozen; only flips move),
`ternary` snapshots `t1/t2/c1/c2` before phase 2 and restores them after (plus `install()`,
see deviations) so only AdamW trains. The freeze setting is recorded in every run line.

## Verification performed

- `py_compile` with the lab venv: **OK** (run twice — before and after the freeze edit).
- Import check: **OK** — `Tiny/Layered/offsets/held_windows/held_loss` all resolve from
  train.py; BATCH 32, CTX 256 confirmed.
- Freeze helpers exercised on a real `Tiny(layers=2, rotary=True)` + `Layered` (no training
  steps): patched `opt.step` verified a true no-op with clean restore; ternary
  snapshot→mutate→restore verified bit-exact.
- File placement verified by the coordinator: `dream-proto/run_dream_proto.py` (9,699 B)
  and `dream-proto/README.md` (6,270 B). No `proto-runs.jsonl` exists yet — correctly,
  since no run has completed.

## Smoke status: NOT RUN — and no numbers are claimed

**The prototype has not been smoke-run. The lab had no genuinely free slot at any point
during this department's work** (checked at 03:54, ~04:00, and 04:03 UTC): the scale ladder
was mid-run on its 10M rung (a single `train.py` process with a 25-minute budget), a
weights-reader v3 job and another department's baseline runs were also active, and load
averaged 4.4–7.9 (spiking to 13.4) on a 1.5-CPU VM. Per the department's orders, the
prototype yields to ladder/mill/growth work rather than contaminating their measurements
or its own.

One micro dry-run was attempted by the builder (`--steps1 3 --steps2 2 --control full`) to
prove the code path under load: it printed held-init, completed phase 1 (buffer filled),
and was then killed by a 175 s timeout during phase 2 as load spiked. It wrote **no**
results line, and **none of its partial numbers are reported here or anywhere as results** —
it established only that the phase-1 path executes; even the phase-2 path rests on compile,
import, and helper tests until a real run completes it.

**Run this when a slot is genuinely free** (no ladder/mill/growth processes), one line per
2×2 cell, seed 0 first (≈5–8 min each on a free lab):

```
cd ~/workspace/edit-lab/bitnet-lab/dream-proto
PY=~/workspace/edit-lab/fable-validation/venv/bin/python
for c in none target threshold full; do
  OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 $PY run_dream_proto.py --control $c --seed 0 --steps1 120 --steps2 30
done
```

Read it by the protocol (CANDIDATES-D, Evaluation protocol §1/§2): `full` earns a trial
only if it beats `none` (CONTROL-D) at equal steps AND beats both single-factor cells;
a `full` ≈ `threshold` result renames the idea to a V=8 arm, `full` ≈ `target` renames it
to hard-window replay. Then the freeze spot-checks in the README price the AdamW question.

## Deviations forced by train.py's actual code

1. There is no `layered_half` class in train.py — the arm is `Tiny(layers=2)`; the
   prototype constructs exactly that, with `rotary=True`.
2. train.py's batch loss is `cross_entropy` over logits reshaped to `(-1, VOCAB)`; the
   per-window losses are derived from that same reshaped call.
3. `--freeze ternary` restore also calls `trainer.install()` after restoring
   `t1/t2/c1/c2` — train.py syncs model weights from the ternary states only via
   `install()`, so without it the restored state would not be what held loss measures.
4. Buffer-mean sanity check caveat: at micro scale (a handful of batches, K=512) buffered
   mean ≈ phase-1 mean trivially since nothing is evicted; the check only bites at real
   run lengths.
