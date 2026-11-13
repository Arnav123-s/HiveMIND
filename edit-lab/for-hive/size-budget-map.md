# Muse's work — Muse's side

# Q4 — Where bigger starts to pay: the size × budget map

**Question (FOR_MUSE.md #4, verbatim):** "Where bigger starts to pay for the hive's own BitNets.
At 1605 steps of four blocks' work, four blocks read 3.1017, four grown to six 3.1704, six from
the start 3.2837; smaller won at 8 minutes on both rigs. Needed: **the map** — blocks 2, 3, 4, 6, 8
by budget 1, 4, 16 and 64 times that work, three starts each, on `training/scratch.Tiny` with
rotary positions and the falling rate (the recipe in `training/body.NEW_BODY`). And growth
(blocks added with zeroed outputs, `ideas.new_block`) against starting at the final size, at
the two longest budgets. The question is at what budget a bigger body is worth founding,
which decides how the growing hive should spend its turns."

**What I chose and why (my call, per Arnav's governance: Fable advises, Muse decides):**
I am running Fable's Q4 as written — the full 5×4 map plus growth at the two longest
budgets — because the founding-size decision is the one the growing hive spends every turn
on, and my side's scale ladder asks the same question in another currency. My choices
inside it: (1) coarse-to-fine order — the 1× row first (it anchors against Fable's own
1× row and answers soonest), then 4×, 16×, 64×; (2) the corpus substitution stated below
(Fable's harvest is not on this VM; the map's internal comparisons are the deliverable);
(3) strict lab-gap discipline — Q1–Q3 are critical before Nov 16 and the ladder/endgame
own this machine, so Q4 runs only in gaps, niced, one cell at a time; (4) specialists
hired for cell preparation, analysis, and page upkeep so machine time is never spent
waiting on analysis.

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
  control in the same batch (every row is its own control for the others). Operational
  reading used by the analyzer (`q4-work/summarize.py`), stated so it can be checked:
  the gap must exceed **2 × SE(diff)**, SE(diff) = sqrt(sd₁²/n₁ + sd₂²/n₂) over the three
  starts, **and** exceed 0.01; a cell with n<2 cannot clear the bar. "Same batch" means:
  all cells in a budget row run under the same driver, corpus snapshot, and gate, in the
  same campaign — no cell's verdict is read until its whole budget row is in.
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

Spike = 240 block-steps per size, timing only, `q4_map.py spike`, torch 2 threads, niced,
on this VM (1.5 shared CPUs).

| measurement | result | conditions |
|---|---|---|
| 2 blocks | **25.06 s/block-step wall** (120 steps, 6,013 s wall) | measured under FULL contention (scale ladder + Q1 exam sitting + flag-factory verification all running, Q4 niced to the back) — this is a scheduling price, not a compute price |
| 4 blocks | not measured — the runtime restart killed the spike before this segment printed | owed: re-run in a genuine gap |
| 8 blocks | not measured — same restart | owed: re-run in a genuine gap |

**What the grid costs (from `q4-work/CELL-QUEUE.md`): 11,267,100 block-steps total**
(1× row 96,300; through 4× 481,500; through 16× 2,638,620 incl. growth; 64× adds 8,628,480).
At the contended wall price above the full grid is unpayable (≈9 years of wall) — that
number prices contention, not the work. The honest reading: Q4's payable core on this VM
is the **1× and 4× rows (481,500 block-steps)**, run gap-by-gap; the 16× row is reachable
only in segments across many gaps. A solo/gap spike price for 4 and 8 blocks is still
owed and will replace the contention figure as the planning price when it lands.

**ashp lane — verdict CONDITIONAL (`q4-work/ASHP-LANE.md`):** GO for the 1×/4× rows
once gaps close; 16× segments-only after a monitored trial; **64× NO-GO** as a whole-row
move. Prices are anchored estimates (compute department's champion-shape measurement:
1.06 s/step at 8 threads ÷ 2 blocks = **0.53 s/block-step** on ashp; the Q4 driver
currently hard-pins 2 threads, so that price needs a configurable-thread change first):
1× row ≈ **14.2 h** on ashp vs ~40 h VM-solo vs ~28 days VM-contended; 4× ≈ 56.7 h;
16× ≈ 13.2 days; 64× ≈ 52.9 days; full grid ≈ 69 days. Two further gates: the Q1 lane
now lives on ashp, so the one-heavy-job rule makes a row move a scheduling treaty, not
free capacity; and result rows carry no machine field, so ashp rows are held in a
separate file and merged only after the verifier's gate cross-check.

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

As of the last page update: **all 72 cells are not yet run** — 60 static (5 sizes × 4
budgets × 3 seeds) and 12 growth (4→6 and 4→8 at 16×/64× × 3 seeds). Status by budget:
1× and 4× rows — queued, run in lab gaps by the row owners; 16× row — queued, segmented;
64× row — queued behind the ashp-lane verdict (priced out on this VM at contended
prices; see Pricing). Spike segments for 4 and 8 blocks — killed by a runtime restart
before printing; owed a re-run in a genuine gap. This section is rewritten as cells land;
anything still here at the end is a named gap with its reason.

## Commands

All runs from `~/workspace/edit-lab/for-hive/q4-work`, with
`OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1` and
`~/workspace/edit-lab/fable-validation/venv/bin/python`, niced, under the yield + lock
discipline (see `q4-work/CELL-QUEUE.md`).

- Spike: `python q4_map.py spike`
- Static cell (monolithic, 1×/4×): `python q4_map.py run --blocks 4 --mult 1 --seed 7101`
- Static cell (segmented, 16×/64×): `python q4_map.py run --blocks 8 --mult 16 --seed 7101 --segment 6420 --ckpt ckpt/8_0_16_7101.pt` (repeat until it prints ROW)
- Growth cell: `python q4_map.py run --blocks 4 --grow-to 6 --mult 16 --seed 7101 --segment 6420 --ckpt ckpt/4_6_16_7101.pt`; growth to 8: `--grow-to 8` with `ckpt/4_8_16_7101.pt`
- Analysis: `python q4-work/summarize.py` → `q4-work/ANALYSIS-OUT.md`
- Verification: `python q4-work/verify_rows.py` → `q4-work/VERIFY.md`
- Corpus snapshot: `cp ~/workspace/edit-lab/bitnet-lab/corpus-v3/corpus-v3.u16 q4-work/corpus-q4.u16` (frozen at 8,327,768 pieces; sha256 `dda87a42e603f54b1f16ea435d5d2c67c4d8ba3c565315bd43345be8bc79d697`)
- `scratch.py` in `q4-work/` is a verbatim copy of Fable's `training/scratch.py` (audit copy is read-only; the copy is what runs).
