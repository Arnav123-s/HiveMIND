# Muse's work — Muse's side

# Q4 — Size × Budget Map: Analysis Output

Source: `/home/hatch/workspace/edit-lab/for-hive/size-budget-map.json` — 2 row(s) with a gate value.

Gate is held-out loss (lower is better). Bar: a gap clears only if `|mean gap| > 2 × SE(diff)` (pooled standard error of the difference) **and** `|mean gap| > 0.01`. Cells are (blocks, grow_to, mult); three starts per cell (seeds 7101–7103) is complete.

## Table — mean gate ± sample sd by size × budget

| size | 1× (6,420 bs) | 4× (25,680 bs) | 16× (102,720 bs) | 64× (410,880 bs) |
|---|---|---|---|---|
| 2 | — | — | — | — |
| 3 | — | — | — | — |
| 4 | 3.2876 (n=1) | — | — | — |
| 6 | 3.3642 (n=1) | — | — | — |
| 8 | — | — | — | — |
| grown 4→6 | — | — | — | — |
| grown 4→8 | — | — | — | — |

“—” = no completed row for that cell. Partial cells note their `n` (complete is n=3). Grown arms are only planned at 16× and 64×; “—” at 1×/4× for a grown row means not run / not planned there.

## Per-budget verdicts (static sizes)

- **1× (6,420 block-steps):** best is **4 blocks** (mean 3.2876, n=1). Adjacent pairs: 4 vs 6: gap 0.0766 — inside noise (SE n/a, n<2 in at least one cell, so the bar cannot be cleared yet).
- **4× (25,680 block-steps):** no static rows yet — no verdict.
- **16× (102,720 block-steps):** no static rows yet — no verdict.
- **64× (410,880 block-steps):** no static rows yet — no verdict.

## Growth vs static (16× and 64×)

No growth-vs-static pair has both arms yet at 16× or 64× — no comparison.

## Cell detail

| blocks | grow_to | mult | n | mean gate | sample sd | seeds |
|---|---|---|---|---|---|---|
| 4 | — | 1 | 1 | 3.2876 | — | 7101 |
| 6 | — | 1 | 1 | 3.3642 | — | 7101 |

