# Five verified programming workloads

The panel uses one authentic, non-held first-turn training solution from each of five programming lesson makers in the G56 `all-rows` archive. The archived solutions were independently regenerated from their original seeds, matched against their archived prompt and source, executed and graded with the registered hidden tests. All five returned the requested example values and passed all 907 hidden assertions.

| Maker | Solution entered the archive | Total tokens | Answer tokens | Hidden tests passed |
| --- | --- | ---: | ---: | ---: |
| Bank class | G51 | 521 | 228 | 290/290 |
| Arithmetic parser | G52 | 525 | 223 | 54/54 |
| LRU cache | G56 | 566 | 234 | 426/426 |
| State machine | G56 | 536 | 207 | 76/76 |
| Dependency schedule | G50 | 447 | 174 | 61/61 |

The fresh generation contributed the LRU and state-machine lessons. The other three are inherited training examples assigned to the sources s0 slice. All 58 officially held-back task identities were excluded. These source-program checks establish which outputs were fit to teach. They do not measure whether the model independently generates correct programs after training. [Prospective selection and scoring rules](protocol.md) · [Exact input hashes, seeds and lengths](selection.json) · [Independent source-program grades](checks.json)

## Actual training and export

The ordinary CPU trainer completed all five optimizer updates, each on a different verified source program. It selected checkpointing for all five, made zero skip attempts and used zero swap. The exported FP32 adapter differed from its inherited state in 16,973,807 of 16,973,824 values across all 196 tensors. End-to-end wall time was 604.22 seconds, including loading the T80 model, blending its parent and trunk and exporting the GGUF. Peak process RSS was 9.99 GiB. The minimum available memory sampled by the guard was 4.60 GiB with a 1 GiB reserve.

| Maker | Completed updates | Row wall time | Process RSS peak | Training loss on answer tokens |
| --- | ---: | ---: | ---: | ---: |
| Bank | 1 | 81.86 s | 9.90 GiB | 0.01036 |
| Calc | 1 | 98.62 s | 9.91 GiB | 0.07663 |
| LRU | 1 | 93.74 s | 9.87 GiB | 0.37563 |
| Machine | 1 | 93.52 s | 9.99 GiB | 0.00728 |
| Schedule | 1 | 68.87 s | 9.79 GiB | 0.01272 |

All five exceeded this worker's contemporaneous fixed-cap estimate of 435 tokens. LRU and machine also exceeded the 527-token cap measured in the separate untouched stock worker. The chunked output head retained at most 32 positions per block. The checkpoints and the newly generated adapter are identified in the raw receipt. The independent problem-solving comparison uses the same inherited starting blend and the five-update export. [Per-row results, memory choices, tensor comparison and artifact hashes](results.json)

To replay, prepare the model and both heritage files following the [native CPU instructions](../native-replay.md). The experiment uses the real training entry point, one epoch, five requested passes with each subject tracked during the study's first sweep, two pinned CPU threads and the ordinary 1 GiB reserve. The five rows keep their original subject and generation tags.

```sh
gzip -dc training/experiments/astra_cpu/five_kinds/panel.jsonl.gz > /tmp/astra-inputs/five-rows.jsonl
python -m training.experiments.astra_cpu.five_kinds.recheck
taskset -c 3,4 python training/experiments/astra_cpu/native.py --repo . --arm acceptance --inputs /tmp/astra-inputs --row-file /tmp/astra-inputs/five-rows.jsonl --scratch /tmp/astra-five-kinds
```
