# CPU training budget and generation wall time

The ordinary line uses a 170-minute slice clock. The `grow.yml` dispatch input `train_minutes` accepts `85`, `110`, or `170` for one CPU run. The explicit 170-minute choice is the CPU control. `auto` retains the ordinary clock and notebook behavior. The next automatic generation starts with its usual defaults.

| Slice clock | Trainer process watchdog | Grow step timeout | Entire train job timeout |
|---|---:|---:|---:|
| 85 min | 110 min | 115 min | 140 min |
| 110 min | 135 min | 140 min | 165 min |
| 170 min | 195 min | 200 min | 225 min |

The watchdog allows a further minute after SIGTERM. The outer timeouts leave room for the final row, held-back loss measurement, weight conversion and upload. Reducing the number of available rows cannot reproduce this change to a time-limited trainer.

Two independent one-run inputs are available on the same CPU path. `shard_policy=cost` changes old-row assignment. `train_plateau=observe` records the stop signal without stopping training, and `train_plateau=stop` enables early termination. Defaults are `hash` and `off`. On runs with an explicit numeric clock, the repository variable `HIVE_ROW_CHECKPOINT=1` enables checkpoint fallback, and `HIVE_CHUNK_CE` can set the number of answer tokens per loss chunk (a nonnegative integer, default 0). Leave both unset or at 0 for a budget-only comparison.

## Observed generation timings

Elapsed times run from each stage's first job start to its last completion. The total runs from the freshness check to the end of record, including transitions, failed slices and its final upload. Practice and dream begin in the same second in both runs. Gather and plan also overlap. Peak observed concurrency was 20 in practice plus dream, 20 in train and 20 in the gate in both generations. [G55 job timestamps](https://api.github.com/repos/Arnav123-s/HiveMIND/actions/runs/44728930517/jobs?per_page=100) · [G56 job timestamps](https://api.github.com/repos/Arnav123-s/HiveMIND/actions/runs/44776442973/jobs?per_page=100)

| Stage, in minutes | G55 | G56 |
|---|---:|---:|
| Practice / dream, simultaneous | 43.20 / 61.00 | 31.00 / 59.03 |
| Gather / plan, simultaneous | 9.30 / 0.25 | 9.13 / 0.32 |
| Train, including lost slices | 175.43 | 205.25 |
| Train through last successful slice | 175.43 | 176.12 |
| Join / merge, successive | 1.72 / 2.62 | 3.57 / 2.68 |
| Gate | 56.97 | 53.45 |
| Record | 1.03 | 1.32 |
| **Observed complete run** | **308.70** | **335.07** |
| If shortening the clock saves exactly 85 minutes | 223.70 | 250.07 |
| Same estimate if both G56 cancellations also finish with the last successful slice | 223.70 | 220.93 |
| **Further savings needed for 180 minutes in that case** | **43.70** | **40.93** |

Practice already reads fresh tasks while dream reads the previous failure archive. Both feed gather. Making them parallel a second time would save zero minutes. G55 delivered all 20 train slices. In G56 two jobs were cancelled, extending the train stage by 29.13 minutes beyond the last successful slice. No shorter-clock generation was run for this study. Clock savings and timely completions in the last three rows are assumptions.

Even if all 16 incumbent exam jobs could run earlier at no cost, the 17 grown-body jobs must wait for the new weights. Their longest measured job took 42.92 minutes in G55 and 41.07 in G56. Running all 17 simultaneously could therefore save at most 14.05 and 12.38 minutes of those historical gate spans. Adding that ideal saving to the estimates above still leaves roughly 29 minutes to find in each generation.

## How much of 85 minutes is available for optimizer updates?

The clock begins inside `grow.train`, before loading weights and preparing rows. The historical trainer first measured the held-back rows, then reserved that elapsed time again for the final measurement. The bounds below bracket the unlogged clock start between the workflow step start and the first slice log. Preparation includes setup inside that window but excludes external job setup. [G55 and G56 s0 excerpts](code-s0-logs.json)

| Code slice 0 | Preparation | Historical first held-back pass and equal reserve | Window for training at 85, replaying the old rule | At 85 with the new precheck limit, nominal |
|---|---:|---:|---:|---:|
| G55 | 25.29–25.43 min | 18.47 + 18.47 min | 22.64–22.77 min | about 29.8 min |
| G56 | 25.42–25.56 min | 18.08 + 18.08 min | 23.27–23.41 min | about 29.7 min |

An explicit 85- or 110-minute run gives the first held-back measurement at most one quarter of the time left after preparation, measured between rows. It then reserves the elapsed measurement time for the final pass. The last column subtracts those two quarters from the clock. A held-back row already running can exceed the first deadline and its elapsed time also increases the final reserve. Finishing the measurement early leaves additional time for training. These are estimates for two archived slices, without measured short-clock update counts.

## Quality and rollback

G55 kept its new body at 52/64 against 51/64. On the paired 32 hard tasks it gained one, finishing 20/32. Its taught-hard score was 20/25. G56 dropped the new body at 48/64 against 51/64, with 16/32 hard tasks and 15/23 taught hard. The fixed unseen exam covered 1/29 and 2/30 individual tasks respectively, and zero of ten kinds in either generation. These generations both used the ordinary budget and different fresh exams. [G55 report](../../../docs/reads/g55.md) · [G56 report](../../../docs/reads/g56.md)

To assess the time/quality tradeoff, compare CPU-only 85 and 170 on the same parents, row bytes, shard policy and evaluation seeds. Record completed slices, optimizer steps, distinct rows and paired gains and losses alongside wall time. Reusing the gate seed alone does not freeze training data because the lesson generator also takes the generation ID. Until those inputs match, comparisons across dispatches remain observational.

The handoff's rollback criterion is a taught-hard drop greater than two percentage points. On 23–25 matched taught-hard tasks even one net lost answer crosses it. Try 110 for the next experiment if 85 crosses the threshold, and repeat on independent matched seeds before changing the line. Missing seats or a different task denominator cannot establish parity.
