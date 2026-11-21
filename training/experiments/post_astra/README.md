# HiveMIND after PRs 131–134

The hive can reuse an earlier worker's tested function in an ordinary local chat, even on a machine without model weights. Its native 8B trainer used less memory on the matched two-row test and produced the same model update. The open capability question is whether verified corrections improve later answers on unseen tasks.

| Requested result | Measurement |
| --- | --- |
| Full CPU generation under 180 minutes with no skipped rows | [G58 full-size timing trial](https://github.com/Arnav123-s/HiveMIND/actions/runs/44857277686). Before the trial, the sequential gate saved zero jobs across nine complete historical generations. |
| At least five deliveries on the original six requests | The prespecified two-worker choice delivered 4/6 in CPython and WASI. Using deterministic generation for the second worker and allowing an independent third worker delivered 5/6 in both, with no wrong deliveries. This was an exploratory choice and took 14 first-program calls. Its stock three-worker control also used 14. [Frozen programs and grading](https://github.com/Arnav123-s/HiveMIND/tree/e3d92b2/training/experiments/astra_orders/diverse) |
| Four more official fixed tasks | On the G55 pulse, the extra inspect instruction would have applied to seven of the 12 failures and zero of the 52 passes. None of those 64 requests specified an input that licensed automatic module/URL rejection. All 30 official held-out prompts qualified for the inspect instruction. The paired diagnostic measures actual outcomes. [Protocol and scoring](https://github.com/Arnav123-s/HiveMIND/tree/c5214ed/training/experiments/astra_orders/worker_contracts) |
| New examples that the hive can learn from | On the first six generated specifications, one produced a verified training row. The unhinted JSON program passed 13/24 cases and its hinted version passed 24/24. A second implementation checked new cases, with results of 10/64 and 64/64. [Generator and training evidence](../hint_dream/README.md) |
| Keep older skills over three generations | On 107 reserved old program preferences after three chronological proxy updates, fresh-only averaged 76.7, 2:1 replay averaged 76.7 and 4:1 replay averaged 76.3. On 21 requests with independently graded worker scripts, the scores were 13.3, 13.3 and 13.7. The original live gate dropped two historical bodies. [Three-update audit](../replay_archive/chronology/README.md) |

## Try a verified worker

The bank admitted an unchanged prime checker, a decimal digit sum and a base converter after 12,041 comparisons with independent expected results. It rejected a different base converter on zero. The stored methods carry their own input limits. The example below returns **16**, identifies the worker and reports its 1,000 successful checks. [Set up the bank and WASI runtime](../astra_transfer/bank_admission/README.md)

```sh
./hive --local --once 'Calculate the decimal digit sum of 907.'
```

## What the CPU result buys

The matched 8B native run lowered peak worker memory from **12.17 GiB to 10.48 GiB**. It processed both rows, skipped no passes and reproduced all 16,973,824 final FP32 values and the exported adapter hash. Elapsed time rose from 204.75 to 233.80 seconds. A longer answer really did split into spans of 128 and 60 tokens. The resulting memory headroom is directly measured. The whole-generation clock depends on training work, scheduling, setup and all exam seats. [Native comparison](../astra_cpu/measurement.md) · [Historical schedule counterfactuals](../astra_cpu/gate_timing/README.md)

The pull requests contain the implementations, counts and reproduction commands. [Merged CPU training](https://github.com/Arnav123-s/HiveMIND/pull/131) · [Closed inherited-profile experiment](https://github.com/Arnav123-s/HiveMIND/pull/132) · [Merged worker transfer](https://github.com/Arnav123-s/HiveMIND/pull/133) · [Worker selection](https://github.com/Arnav123-s/HiveMIND/pull/134) · [Integrated training, archive and bank](https://github.com/Arnav123-s/HiveMIND/pull/135) · [Paired worker contract checks](https://github.com/Arnav123-s/HiveMIND/pull/136) · [Primary research](research.md) · [Measurement rules](measurement.md)
