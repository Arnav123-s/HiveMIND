# Independent packing results

Use best-fit for these workloads. The sparse router used 10,499 bins on the published sets. Best-fit used 6,131. All 3 of the router’s public wins occurred on the ascending uniform stress test. It lost all 40 public instances in their original order.

Each family below includes three orders per instance. Negative differences favor the sparse router. The interval resamples whole instances, with their orderings kept together.

| Family | Streams | Next-fit | First-fit | Best-fit | Sparse | Mean extra bins [95% interval] | Sparse wins / ties / losses |
|---|---:|---:|---:|---:|---:|---:|---:|
| Falkenauer triplet | 60 | 2,749 | 2,672 | 2,672 | 6,725 | +67.55 [+65.67, +69.23] | 0 / 0 / 60 |
| Falkenauer uniform | 60 | 3,943 | 3,469 | 3,459 | 3,774 | +5.25 [+4.37, +6.17] | 3 / 18 / 39 |
| Complementary pairs | 48 | 3,036 | 2,670 | 2,644 | 2,629 | -0.31 [-0.52, -0.10] | 15 / 31 / 2 |
| Identical items | 48 | 1,860 | 1,860 | 1,860 | 3,687 | +38.06 [+27.25, +47.81] | 0 / 12 / 36 |
| Small items | 48 | 523 | 504 | 504 | 504 | +0.00 [+0.00, +0.00] | 0 / 48 / 0 |
| Small then large | 48 | 2,865 | 2,698 | 2,696 | 2,685 | -0.23 [-0.38, -0.08] | 10 / 36 / 2 |
| Uniform | 48 | 2,983 | 2,631 | 2,608 | 2,663 | +1.15 [+0.31, +2.08] | 6 / 27 / 15 |

On the first triplet instance in its published order, there are 120 items and the proven optimum is 40 bins. Next-fit, first-fit, best-fit and the learned single policy all used 40. The sparse policy used 117. The file starts with sizes 36.6, 26.8 and 36.6, which sum to one full 100-unit bin. Many triplets arrive together in the published order. After a shuffle, the sparse policy still lost all 20 comparisons. Its gap-reserving specialist can repeatedly open a bin to preserve a half-empty bin for a large item, even when no large items arrive.

The learned single policy coincided with best-fit and tied it on every stream. The sparse policy did save 15 bins across the 48 complementary-pair streams and 11 across the 48 small-then-large streams. On identical items, the conventional algorithms matched the construction’s optimum in all 48 streams. The sparse policy matched it in 12.

All five methods produced feasible placements across 37,440 arrivals in 360 streams. Across the full exam, best-fit inspected 761,658 bins and the sparse policy inspected 1,091,874, about 43% more. Grading, including independent feasibility checks and baseline reproduction, used 0.80 CPU seconds on this machine before bootstrap analysis and excluding dataset download. These observations cover the stated input generators and orders. The experiment measures an online packing heuristic and supplies no new optimality guarantee.

Run `python -m training.experiments.packing_grade` at the repository root. The grader fetches the two source files into a temporary cache and verifies their SHA-256 hashes. Per-instance compressed JSON lines include the exact arrival-stream hash, bounds, feasible bin counts, and work counters. The summary includes every comparison by family and the primary comparison by arrival order. [Protocol](eval-protocol.md) · [Summary](eval.json) · [All stream scores](eval-rows.jsonl.gz) · [OR-Library](https://people.brunel.ac.uk/~mastjjb/jeb/orlib/binpackinfo.html)
