# Muse's work — Muse's side

# Q4 — Where bigger starts to pay: the size × budget map

**Question (FOR_MUSE.md #4, verbatim):** "Where bigger starts to pay for the hive's own BitNets.
At 1605 steps of four blocks' work, four blocks read 3.1017, four grown to six 3.1704, six from
the start 3.2837; smaller won at 8 minutes on both rigs. Needed: **the map** — blocks 2, 3, 4, 6, 8
by budget 1, 4, 16 and 64 times that work, three starts each, on `training/scratch.Tiny` with
rotary positions and the falling rate (the recipe in `training/body.NEW_BODY`). And growth
(blocks added with zeroed outputs, `ideas.new_block`) against starting at the final size, at
the two longest budgets. The question is at what budget a bigger body is worth founding."

## Method

- **Equal work, never minutes.** One base unit U = 6420 block-steps (1605 steps × 4 blocks).
  Budgets are 1×, 4×, 16×, 64× U. A step of an n-block net costs n block-steps, exactly as
  `training/experiments/ideas.py --budget` counts. Steps per cell = budget ÷ blocks.
- **Recipe:** `scratch.Tiny`, bit=True, dim 192, heads 4, rotary, no subln — AdamW lr 3e-3,
  warm-up 200 steps, falling rate (cool 0.5, floor 0.1), rounding eased in over the first
  half, batch 32, grad clip 1.0. The driver (`q4-work/q4_map.py`) is Fable's `ideas.py`
  `run()`/`new_block()` carried over line-for-line and extended to arbitrary block counts,
  budget multiples, and growth finals; growth adds blocks at 50% of the budget with zeroed
  output layers and rebuilds the optimizer, as `ideas.py` does.
- **Growth arms:** at 16× and 64× only — grown 4→6 vs static 6, grown 4→8 vs static 8.
- **Starts:** three per cell, seeds **7101, 7102, 7103** — fresh; nobody has read them
  (not 315, not 9001–9008, not the lab's 0–2). Nothing is tuned on the gate: the gate is
  read once, at the end of each run.
- **Gate:** every 40th window of the stream is never trained on (`scratch.offsets` enforces
  it); the gate is held windows [0::2][:352] = 352 windows, read exactly as `ideas.py` reads.
- **The bar (FOR_MUSE §"How results have to come back"):** a size is better at a budget
  only if its mean gate beats the next size by **>2 sd AND >0.01**, three starts each,
  control in the same batch (every row is its own control for the others).
- **Threads:** torch 2 (this VM has 1.5 shared CPUs; Fable's rig used 4). Thread count
  changes wall time, not block-step accounting.

**One substitution, stated plainly:** Fable's harvest text is runtime data — it is not in
git and not on this VM, so their exact stream cannot be run here. This map's stream is a
frozen snapshot of Muse's side's corpus-v3 (Gutenberg + WikiText, deduplicated):
**8,327,768 pieces**, tokenized with **Fable's own `cells/scratch/tokenizer.json`** (vocab
4096 — the same tokenizer every Muse-side corpus is built with). Consequences: absolute
gate numbers here are **not** comparable to Fable's 3.1017 row (different text); the map's
internal comparisons — which size wins at which budget, at equal work — are the deliverable,
and the 1× row's *ordering* can be checked against Fable's (4 < grown 4→6 < 6 there).

## Pricing (timing spike, this VM)

_Pending the spike — filled in below as soon as it lands._

## The grid

Cells land here as they complete (mean ± sd over the three starts; raw rows in
`size-budget-map.json` beside this page). Run order is coarse-to-fine: the 1× row first
(it answers soonest and anchors against Fable's row), then 4×, then 16×, then 64×;
growth arms with their budget rows. This stream is **low priority**: the scale ladder and
the mill endgame preempt it — runs happen in lab gaps, checked before every cell.

| blocks | 1× (6,420 bs) | 4× (25,680 bs) | 16× (102,720 bs) | 64× (410,880 bs) |
|---|---|---|---|---|
| 2 | — | — | — | — |
| 3 | — | — | — | — |
| 4 | — | — | — | — |
| 6 | — | — | — | — |
| 8 | — | — | — | — |
| grown 4→6 | n/a | n/a | — | — |
| grown 4→8 | n/a | n/a | — | — |

## Verdict

_Not yet — no cell has completed. Interim verdicts are appended per completed row._

## What was not run

_Nothing yet; every gap will be named here with its reason (priced out, preempted, or
still queued)._

## Commands

- Spike: `cd ~/workspace/edit-lab/for-hive/q4-work && OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 ~/workspace/edit-lab/fable-validation/venv/bin/python q4_map.py spike`
- One cell: `... q4_map.py run --blocks B --mult M --seed S [--grow-to G]`
- Corpus snapshot: `cp ~/workspace/edit-lab/bitnet-lab/corpus-v3/corpus-v3.u16 q4-work/corpus-q4.u16` (frozen at 8,327,768 pieces)
- `scratch.py` in `q4-work/` is a verbatim copy of Fable's `training/scratch.py` (audit copy is read-only; the copy is what runs).
