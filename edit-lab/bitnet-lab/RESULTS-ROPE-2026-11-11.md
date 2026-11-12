# Muse's work — written by Muse, on Muse's side. Fable's HiveMIND was read read-only; nothing on Fable's side was touched.

# Rotary positions (RoPE) on Muse's side — results, 2026-11-11

Question (Arnav): Fable's bodies just measured a big win from rotary positions (their recipe7:
3.6940 against 3.9636 as built in). Arnav's criterion is compatibility — "if Fable's work is
compatible to ours, try it that way." So: is their rotary method compatible with our lab model,
and if it is, does it improve our best trainer (layered_half votes, baseline held 2.899)?

## What Fable does (read in the audit copy at make-it-work 4bd8308, commits 30eb4a5 + 4bd8308)

- `scratch.rotated(x, cos, sin)`: each **interleaved pair** (even/odd numbers) of a query or key
  is rotated by an angle that grows with the position: pair *i* at place *p* turns by
  `p / 10000^(2i / head_dim)`. Full rotary — every pair of the head's numbers is rotated
  (head_dim 48 → 24 pairs). No partial-rotary fraction.
- Angles are precomputed for all CTX places in each Block as non-persistent cos/sin buffers.
- Applied to **q and k only**, after the qkv BitLinear projection (on its output activations),
  before scaled-dot-product attention. v is untouched. Nothing else in the block changes.
- When rotary is on, the body no longer adds the table of places (`pos`) to the token embedding —
  **but the table is still carried**: constructed, present in the model's parameters and files,
  simply not used ("so a cell's file and the stem cell's table are as before").
- It is a founding **shape setting** (`shape.rotary`, default off for every existing body),
  measured at 600 steps with their fp recipe (lr 3e-3) on their full 4-block stem shape and
  their corpus: held gate 3.6940 vs ~3.9636 as built in.

## Compatibility check against our lab model — COMPATIBLE, adopted as-is

Our lab stem is the same shape family (dim 192, 4 heads → head_dim 48, ctx 256, vocab 4096;
layered_half runs 2 blocks), the same Block structure (qkv BitLinear → view/permute → SDPA),
and our trainers build their AdamW group exactly as Fable's Direct does
(`[p for p in model.parameters() if not a BitLinear weight] + log_scales`). Point by point:

| Fable's piece | Fits ours? | What was done |
|---|---|---|
| `rotated()` interleaved-pair rotation | Yes, unchanged | Reimplemented identically; verified bit-equal to a literal transcription of theirs on test tensors |
| Angle table `p / 10000^(2i/48)`, per-Block cos/sin buffers, non-persistent | Yes, unchanged | Same formula; buffers verified bit-equal to theirs |
| Applied to q, k after the qkv projection, before attention; v untouched | Yes, unchanged | Same insertion point in our Block.forward |
| pos table carried but not used | Yes, unchanged | `Tiny` still constructs `pos`; `body()` skips adding it when rotary is on. It stays in the trainers' AdamW group exactly as in Fable's Direct; its gradient is None and AdamW skips it (verified) |
| Shape setting, default off | Yes | `--rope` flag on train.py, default off; the baseline path is untouched (shared initial weights bit-identical with the flag on or off — verified, 28/28 tensors) |

**Differences — all in the test rig around the mechanism, none in the mechanism:**

1. **The arm it rides on is ours.** Fable measured rotary on their full 4-block shape with their
   fp recipe at a fixed 600 steps. This test puts the identical mechanism on our winning
   layered_half vote trainer (2 blocks, vote counters) at our standard 8-minute budget, our
   corpus, our held set — because the question was whether it improves *our* best trainer.
2. **Our Block has no subln norms** (a pre-existing lab-wide simplification, true of the
   baseline arm too). Rotary does not interact with subln — Fable applies it before attention,
   subln sits after — so this does not affect the transplant.
3. **Parameter count: no difference, and that is Fable's design, not a shortcut.** Because the
   pos table is carried, total parameters are identical (1,725,696 both arms; pos's 49,152
   parameters ride along unused and untrained). Ternary weights (884,736) and vote-trainer
   state bytes (2,211,840 B) are also identical. The only new memory is the derived cos/sin
   constants: 2 buffers × 256×24 floats × 2 blocks = 98,304 B, non-persistent, never trained.
   (Had we instead *removed* the table, we would have freed 49,152 parameters but broken
   compatibility with Fable's carried-table shape and changed the init stream — not their way.)

Nothing was fundamentally incompatible, so nothing was forced and no variant was substituted.

## Results — held loss, 3 seeds × 8 minutes, same seeds/budget/corpus/held set as the baseline

| arm | seed 0 | seed 1 | seed 2 | mean ± sd | steps |
|---|---|---|---|---|---|
| layered_half (baseline, built-in positions) | 2.8937 | 2.9073 | 2.8961 | 2.8990 ± 0.0073 | 161–163 |
| **layered_half + rotary (Fable's way)** | **2.8765** | **2.8477** | **2.8497** | **2.8580 ± 0.0161** | 154–170 |

Per-seed paired gains: +0.0172 / +0.0596 / +0.0464 — every rotary seed beat every baseline seed.
Step counts overlap, so unlike the layered_half-vs-full comparison there is no "more steps per
minute" confound to explain this away; seed 0 in fact won in *fewer* steps (154 vs 161).
Flip share and final state histograms are in line with the baseline arm (runs.jsonl).

## Verdict — WIN, under the standing bar

The bar: beat the baseline mean by more than 2 seed-sd **and** more than 0.01.
Gain = **0.0411**, which clears 2× the baseline sd (0.0145), 2× the rotary arm's own sd
(0.0322), and the 0.01 floor. **Rotary positions, done Fable's way, improve our best trainer.**

Honest bounds:

- The direction matches Fable's result; the size does not transfer. Their gain was ~0.27 on
  their rig (fp recipe, 600 steps, 4 blocks, their corpus); ours is 0.041 (vote trainer,
  8-minute wall-clock budget, 2 blocks, our corpus). Same mechanism, different rig — the
  numbers are not expected to match, and theirs must not be quoted as ours.
- Held loss at initialisation differs between arms only at the third decimal (8.3138 vs
  8.3139 etc.): all initial weights are bit-identical, but the forward pass already differs
  (rotation vs added table), so a small init-loss difference is expected.
- Same lab-wide limits as the 2026-11-11 sweep: 8-minute runs, one corpus, cell scale
  (884,736 ternary weights). This is a win at this scale, not a claim about LLM scale.

## Incident

A runtime restart killed seed 1's first attempt ~7 minutes in (07:33Z); nothing from it was
recorded (records are written only at the end of a run). It was re-run cleanly from scratch
and completed at 07:42Z. Seeds 0 and 2 were unaffected. Handling matches the baseline sweep's
restart incidents. Full event trail: `sweep.log`; per-run records: `runs.jsonl`
(arm `layered_half_rope`). Driver: `run_rope.py`.
