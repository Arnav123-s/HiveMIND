# Confirmation on fresh packing instances

On the 60 public arrival streams, the constrained refit used **6,340 bins**, the original router used **11,006**, and best-fit used **6,342**. Enforcing the new-bin rule eliminated the large measured failure. The two-bin difference from best-fit is 0.032%. The family results go in opposite directions.

Each of the 20 public multisets had three arrival orders. The constrained policy beat best-fit on 8 streams, tied on 48, and lost on 4. All five triplet wins occurred with shuffled arrivals. All ten original triplet streams reached the certified optimum of 83 bins with both methods. Across these public instances, the average difference from best-fit was -0.033 bins per stream, with a descriptive 95% instance-cluster bootstrap interval of -0.167 to 0.117.

| Workload | Streams | Original router | Best-fit | Constrained | Mean extra bins vs best-fit [95% interval] | Wins / ties / losses |
|---|---:|---:|---:|---:|---:|---:|
| Falkenauer triplet 249 | 30 | 7,050 | 2,757 | 2,752 | -0.17 [-0.27, -0.07] | 5 / 25 / 0 |
| Falkenauer uniform 250 | 30 | 3,956 | 3,585 | 3,588 | +0.10 [-0.17, +0.33] | 3 / 23 / 4 |
| Fraction mixture | 48 | 2,491 | 2,491 | 2,491 | +0.00 [-0.06, +0.06] | 1 / 46 / 1 |
| Medium band | 48 | 6,835 | 2,968 | 2,958 | -0.21 [-0.31, -0.10] | 12 / 33 / 3 |
| Two regimes in reverse | 48 | 3,754 | 3,762 | 3,763 | +0.02 [+0.00, +0.06] | 0 / 47 / 1 |

Across 204 streams, best-fit used 15,563 bins, the constrained router 15,552, first-fit 15,582 and the original router 24,086. Every placement was feasible. An independent checker verified that every new bin opened by the constrained policy was necessary given the existing free capacities. The constrained router inspected 1,358,385 bins, compared with 1,358,970 for best-fit. Equal scan counts can involve different CPU work. Grading took 1.64 CPU seconds, excluding bootstrap analysis and file download.

This was one diagnostic repair followed by one confirmation with different sizes and synthetic generators. The public interval includes both gains and losses against best-fit. The development code represents the specialists as small policies, and this comparison measures their router on these workloads.

Reproduce with `python -m training.experiments.packing_confirmation` from the repository root. [Confirmation protocol](eval-confirmation-protocol.md) · [Machine-readable evidence](eval-confirmation.json) · [Every stream](eval-confirmation-rows.jsonl.gz) · [First exam](eval-results.md)
