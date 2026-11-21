# Training slice balance and stopping evidence

**Balancing historical row lengths reduced uneven token assignments most consistently at eight slices.** At the 1,152-token cap, the G55 spread fell from 7.75% to 1.35% and the G56 spread from 8.10% to 1.38%. The cost policy reduced the spread in 10 of the 12 generation, cap and slice-count combinations. G56 with three slices at a 508-token cap regressed from 0.66% to 3.27%. The normal policy remains the existing content hash. [All per-slice counts](shard-results.json)

Practice jobs already sit different independently seeded exams. The common worklist appears later when a child trains. Training removes held-back lesson tasks before partitioning and replicates all fresh generation rows and parent corrections on every slice. The cost policy partitions only the historical pool. It estimates the amount of UTF-8 text per exchange and accounts for a preference pair's chosen, rejected and reference passes. It places the most expensive remaining group on the currently lightest slice. Frozen common system overhead makes sibling workers agree even if they start on different dates. Duplicate training examples stay together. Their absence or multiplicity on intake is preserved. [Scheduler and convergence rule](../../shard_budget.py)

## What the replay measured

We replayed 8,247 published G55 rows and 8,820 G56 rows with the T80 tokenizer and the trainer's shortening rules. These are successive generations with overlapping historical material. We used ordinary supervised rows with no parent-specific corrections, raw reading or preference pairs. After eligibility filtering, 6,950 historical and 388 replicated rows were assigned in G55, and 7,340 historical and 530 replicated rows in G56, before per-machine token caps. Every policy covered the identical input multiset. Oversize rows contributed zero work at the cap where the real encoder would reject them.

The table shows `100 × (largest − smallest) / mean` on tokenized sequence lengths for one full traversal, including replicated rows. The cutoff is uniform across the simulated workers. The fixed serpentine schedule is the handoff's proposed draft, while dynamic lightest-first placement is classical longest-processing-time scheduling. Hashing uses the same CRC32 membership as the trainer. These are token totals, not observed elapsed training time. The live trainer revisits subjects adaptively, and wall-clock budgets, dtype, memory skips, held-back evaluation and shared fresh rows can dominate. The replay cannot demonstrate a two-percent wall-clock threshold or unchanged model quality. [Replay](shards.py) · [G55 run](https://github.com/Arnav123-s/HiveMIND/actions/runs/44728930517) · [G56 run](https://github.com/Arnav123-s/HiveMIND/actions/runs/44776442973)

| Gen | Token cap | Slices | Default hash | Serpentine draft | Cost policy |
|---|---:|---:|---:|---:|---:|
| g55 | 508 | 2 | 1.90% | 0.50% | 0.45% |
| g55 | 508 | 3 | 1.71% | 1.07% | 1.65% |
| g55 | 508 | 8 | 11.91% | 2.68% | 4.20% |
| g55 | 1152 | 2 | 0.95% | 0.75% | 0.30% |
| g55 | 1152 | 3 | 3.75% | 0.58% | 1.19% |
| g55 | 1152 | 8 | 7.75% | 2.11% | 1.35% |
| g56 | 508 | 2 | 1.32% | 0.97% | 0.33% |
| g56 | 508 | 3 | 0.66% | 2.28% | 3.27% |
| g56 | 508 | 8 | 10.49% | 2.75% | 2.49% |
| g56 | 1152 | 2 | 0.33% | 0.12% | 0.42% |
| g56 | 1152 | 3 | 2.83% | 0.42% | 0.50% |
| g56 | 1152 | 8 | 8.10% | 1.44% | 1.38% |

## Can historical training plateau after half the rows?

On code slice zero, G51 completed 54 passes on 1,836 eligible rows, G55 completed 260 on 3,797, and G56 completed 269 on 4,061. Even if every pass were unique, coverage would have reached only 2.94%, 6.85% and 6.62%. Those three real slices could never meet the proposed 50% unique-row threshold. The existing training log periodically reports a running mixed loss, including any preference term, and the member summary keeps aggregate initial/final summaries. Neither tells us whether the same training rows stopped improving. No wall time is credited to plateau stopping in these runs. [Original job excerpts and URLs](code-s0-logs.json)

For an experimental run, `HIVE_TRAIN_PLATEAU=observe` records a signal and spends its existing budget. `stop` can finish only at a complete optimizer update. A 30-update block compares its first and second 15 updates on the same row IDs, using the actual unrounded optimizer objective per row, including the rejected alternative and reference term for a preference pair. It requires at least 50% total unique eligible-row coverage, four rows in both halves, and a match covering at least half the distinct rows in each half. An invalid loss or an insufficient match invalidates that block. Two consecutive nonoverlapping qualified blocks with mean absolute per-row relative change below 0.5% (equal weight per matched row, so opposite movements cannot cancel) trigger the signal, making 60 full optimizer updates the earliest stop. Skipped rows and a final partial accumulation cannot advance it. It is a training-loss convergence heuristic. It provides no held-out quality measurement.

The grow workflow supports a per-dispatch `shard_policy=cost` trial and `train_plateau=observe` or `stop`. Local training reads the corresponding `HIVE_SHARD_POLICY` and `HIVE_TRAIN_PLATEAU` settings. Default training uses `hash` and `off`. Manually launched sibling slices must use the same complete archive and policy. The join checks every slice policy before writing a child and refuses a mixture. A legacy slice without recorded policy is treated as hash.

## Reproduce

The Actions all-rows artifact IDs are 14630086449 and 14653659254. Extract `rows.jsonl` from each and compare its SHA-256 with the result. Use the tokenizer files from `prism-ml/Ternary-Bonsai-8B-unpacked` at revision `ac20f03fc62e872399218b659c8e949dfca05769`. From the checkout root run

```sh
python -m training.experiments.astra_cpu.shards \
  --archive g55 "$G55_ROWS" --archive g56 "$G56_ROWS" \
  --tokenizer "$T80_TOKENIZER" --out /tmp/hive-shard-results.json
python -m pytest -q tests/test_shard_budget.py tests/test_slices.py tests/test_held_out.py
```
