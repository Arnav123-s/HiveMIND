# Can two packing specialists share a stream of arrivals?

**Keep best-fit as the default.** The learned team saved 82 bins on its 36 development streams but used 4,368 more bins than best-fit on 120 external test streams. Every packing was feasible. First-fit and best-fit remain available as baselines. The constrained follow-up recovered on a fresh external exam, using 6,340 bins to best-fit's 6,342. Its margin varied by family. The experiment did not change the live hive. [Independent exam and paired comparisons](eval.json) · [Predeclared protocol](eval-protocol.md)

An item arrives with an integer size. The packer must commit it to one bin immediately, without seeing future items or moving earlier placements. Fewer bins is better. First-fit takes the first open bin with room. Best-fit takes the open bin that would leave the least unused space. Both open a new bin if necessary.

We tested a second kind of worker that sometimes opens a bin early to preserve a large gap for a later item. We searched over the size of the gap and the maximum number of gaps worth preserving. A router can choose one worker for each arrival using only the sizes it has already seen. All three strategies receive the same items in the same order. The comparison measures bin inspections and running time as well as bins used. This is a small search over human-written policies inspired by prior work on program search for online packing. [FunSearch](https://www.nature.com/articles/s41586-023-06924-6)

## Development and freeze

Six public seeds generated six families of 80 items each, for 2,880 items across 36 streams. We evaluated 27 single policies. We shortlisted the strongest overall policies and the best specialist for each development family. Coordinate descent evaluated 40 distinct assignments of specialists to four observable states. We added a state for streams containing few very small items after examining development results. Development traces could influence the design. The independent evaluator ran after the policy freeze.

| Development family | First-fit | Best-fit | Best single policy | Sparse team |
| --- | ---: | ---: | ---: | ---: |
| Uniform | 263 | 257 | 257 | 272 |
| Mostly small | 127 | 127 | 127 | 127 |
| Shuffled near-complements | 269 | 264 | 264 | 261 |
| Small items followed by large | 335 | 335 | 335 | 253 |
| Short batches | 283 | 276 | 276 | 265 |
| Weighted mix of fixed sizes | 286 | 286 | 286 | 285 |
| **Total bins** | **1,563** | **1,545** | **1,545** | **1,463** |

The best single policy was best-fit. The four-state router chose between best-fit and a worker that can preserve gaps of at least half the bin capacity. Every item activates exactly one of those two. The team spent 20.61 bin inspections per development item, compared with 19.93 for best-fit and 18.58 for first-fit. A local five-repeat timing gave 10.39, 7.94 and 5.84 microseconds per item, respectively. These timings include instrumenting the serial Python implementation and depend on the machine.

The policy file frozen before independent grading has SHA-256 `67b227417ad89251f1462315dd8d1cb9ee55cb706bc782d5fb68ce2f1a285059`. The implementation at freeze has SHA-256 `31a4ffa8a68b848424dcca78d3df2191d415fe4ee72ad8c5c6b6c64b764a267d`.

## Why the team failed the external test

The sparse team used 10,499 bins on the public OR-Library instances across three arrival orders. Best-fit used 6,131. The team won three streams, tied 18 and lost 99. Over the full exam of 360 streams, including five generated families, the totals were 22,667 and 16,443. Several orderings share the same underlying items. The independent grade accounts for these repeated observations. [All stream scores](eval-rows.jsonl.gz) · [External benchmark data](https://people.brunel.ac.uk/~mastjjb/jeb/orlib/binpackinfo.html)

The failure has a simple example. If a long run consists of items occupying a little more than one third of a bin, two fit together. A worker preserving half-empty bins can keep opening new bins in anticipation of larger items that never come. The external triplet instances exposed this tendency. The learned policy improved on some arrival patterns, but its historical size counts could not consistently tell when reserving space would pay off. No policy was refitted after the independent results arrived.

## Reproduce

```sh
python -m training.experiments.packing_hive fit > /tmp/packing-policy.json
cmp /tmp/packing-policy.json training/reports/packing-hive/policies.json
python -m training.experiments.packing_hive run 100 40 40 60 60
python -m training.experiments.packing_grade --help
```

The `run` command returns each policy's bin count, the zero-based bin assigned to each item at its arrival, and the work counters. The policy search and solver use the Python standard library. [Search, solver and online interface](../../experiments/packing_hive.py) · [Frozen policies and development counts](policies.json) · [Independent grader](../../experiments/packing_grade.py)

## One follow-up with a hard placement rule

The first exam exposed a specific failure. The team opened new bins while an earlier one still had room. We constrained the follow-up to **Any Fit**. It must choose an existing feasible bin whenever one exists. All development instances and router inputs stayed the same. The first external exam was used to identify the failure. A separate confirmation exam judges the revised policy.

The original 25 gap-preserving settings all reduce to best-fit under this constraint. With Any Fit, at most one bin can be at least half empty. To open another bin at least half empty, its first item would have had to fit the existing half-empty bin. If best-fit would use up the single protected gap, no alternative feasible bin could preserve that gap. All 25 settings matched best-fit's development bin counts on every stream.

Before external confirmation, we extended the search to thresholds from 20% to 45%, where two existing bins can leave qualifying gaps. The fit tested 57 singles and 29 sparse assignments. The frozen team preserved a gap of 25% or 30% of capacity depending on its observed state. It used 1,543 development bins to best-fit's 1,545. We independently replayed all 4,096 four-item streams of capacity eight plus the 36 development streams and verified all 19,264 placement decisions obeyed both capacity and Any Fit.

The revised solver has SHA-256 `aaac09bcbdaf3dde2671518157bd5ca076c17323084f202cf5ffa4e1bffe3d57` and the frozen follow-up policy has SHA-256 `60c3d40dedd4cef6932c46fb5de4d4bbd03ecf3fba60054d34a96d459347d9b4`. [Follow-up solver](../../experiments/packing_any_fit.py) · [Frozen follow-up policy](any-fit-policy.json)

```sh
python -m training.experiments.packing_any_fit fit > /tmp/any-fit-policy.json
cmp /tmp/any-fit-policy.json training/reports/packing-hive/any-fit-policy.json
```

On 60 fresh external streams, the constrained team used 6,340 bins. Best-fit used 6,342 and the original team used 11,006. The constrained team saved five bins across the triplet family and lost three across the uniform family. Across all 204 confirmation streams it used 15,552 bins, versus 15,563 for best-fit, 15,582 for first-fit and 24,086 for the original team. The check on each new-bin action also passed. The constraint fixes the earlier failure. These results do not establish a consistent advantage over best-fit. The follow-up ends here. [Confirmation protocol](eval-confirmation-protocol.md) · [Independent confirmation](eval-confirmation.json) · [Every confirmation stream](eval-confirmation-rows.jsonl.gz)
