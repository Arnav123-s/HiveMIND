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

To replay, prepare the model and both heritage files following the [native CPU instructions](../native-replay.md). The experiment uses the real training entry point, one epoch, a maximum of one step per row under the study's first sweep, two pinned CPU threads and the ordinary 1 GiB reserve. The five rows keep their original subject and generation tags.

```sh
gzip -dc training/experiments/astra_cpu/five_kinds/panel.jsonl.gz > /tmp/astra-inputs/five-rows.jsonl
python -m training.experiments.astra_cpu.five_kinds.recheck
taskset -c 3,4 python training/experiments/astra_cpu/native.py --repo . --arm acceptance --inputs /tmp/astra-inputs --row-file /tmp/astra-inputs/five-rows.jsonl --scratch /tmp/astra-five-kinds
```
