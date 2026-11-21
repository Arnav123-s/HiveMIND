# CPU training budget and generation wall time

The proposed CPU profile gives each training slice 85 minutes. The repository variable `HIVE_TRAIN_MIN` and the one-run input `train_minutes` accept 85, 110 or 170. A numeric input overrides the variable. The `notebook` input restores the 170-minute clock and Colab option.

| Slice clock | Trainer process watchdog | Grow step timeout | Entire train job timeout |
|---|---:|---:|---:|
| 85 min | 110 min | 115 min | 140 min |
| 110 min | 135 min | 140 min | 165 min |
| 170 min | 195 min | 200 min | 225 min |

The watchdog allows a further minute after SIGTERM. The outer timeouts leave room for the final row, held-back loss measurement, weight conversion and upload. Reducing the number of available rows cannot reproduce this change to a time-limited trainer.

The CPU defaults are `HIVE_ROW_CHECKPOINT=1` and `HIVE_CHUNK_CE=128`. Setting either repository variable to `0` disables that feature. The notebook profile disables both. Independent one-run inputs select cost-based shards (`shard_policy=cost`) or observe or stop on a plateau (`train_plateau=observe|stop`). The defaults remain `hash` and `off`.

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

### Dream budget and sequential-gate replay

The workflow reserves 43 minutes per dream job, including setup, and leaves 90 seconds for log and artifact uploads. Set `HIVE_DREAM_MIN=61` to restore the historical wall-time allowance. A dream gives verified member-only failures twice the weight of otherwise identical failures. Recency adds a factor from one to two within the last 400 records. Each selected kind retains a positive weight. The log counts attempts actually started and saves checked rows after each try.

Set `HIVE_GATE_SPRT=1` to try the blocked fresh gate for a growing body. The first four before/after seed pairs run together. At four and six pairs a matched conditional likelihood test compares 60:40 and 40:60 on discordant grades. A net difference of eight crosses the nominal 5% boundaries. A crossing skips the remaining fresh pairs. All sixteen fixed-exam seats and the talk job still run. The recorder applies its usual guards on the completed evidence. Trials and the default `HIVE_GATE_SPRT=0` launch all fresh seeds together. [Rule and assumptions](../../../training/gate_look.py)

Replay of the nine complete G45–G55 cohorts reproduced all nine full-length fresh verdicts. Every prefix needed all eight seeds. There were **zero early decisions and zero jobs saved** across 576 pairs. G45 had one mismatched prompt and G46 was cancelled. Seven generations' four- and six-seed looks were checked directly from the grade archives. G50–G52 used the archived, digest-checked per-seed ledger. Serial blocks add waits on close contests, so the option starts off. [Paired grades and recorded decisions](handoff_audit/README.md)

On G55, an assumed 85-minute train saving and a 43-minute dream stage yield **205.90 minutes**. Practice still takes 43.20 minutes, limiting the dream saving to 17.80. Reaching 180 minutes would require another 25.90 minutes. A replay cannot establish complete hosted wall time, zero skipped rows or the capability of a body trained on the shorter clock.

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
