# Greedy second-seat replication on six fresh requests

**Greedy modular instructions confirmed one counter request a seat earlier. With a third seat available, both policies delivered exactly the same three correct answers out of six.** Both withheld three and delivered zero wrong on normal CPython and WASI. The earlier panel's improvement from four to five deliveries did not repeat on the new inputs. The sampling switch stays opt-in.

| Policy | Correct deliveries | Wrong | Withheld | Tasks with at least one correct worker among seats used | First-program calls | Recorded wall seconds | Server CPU seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Short workers, two seats | 0 | 0 | 6 | 3 | 12 | 634 | 994 |
| Greedy modular second, two seats | 1 | 0 | 5 | 3 | 12 | 782 | 1,202 |
| Short workers, up to three seats | 3 | 0 | 3 | 4 | 18 | 940 | 1,492 |
| Greedy modular second, up to three seats | 3 | 0 | 3 | 4 | 17 | 1,034 | 1,615 |

The second worker alone was correct on three requests under greedy modular instructions and two under sampled short instructions. Across the offers each policy used, at least one worker solved each of the same four requests. On one counter input, the first and greedy second worker independently produced the required increments and matching sum. The stock second worker asserted that the entire sequence wrapped at most once. The request allowed one wrap per interval, so the stock policy needed its third worker. Both approaches solved the two scheduling cases on seat three. In the other counter case, only the third worker was right. Neither set of offers produced a correct cold-chain deliverable on either draw. This accounts for all six decisions.

We fixed the six cases, inference settings, per-request checkpoint boundary and independent grader before collecting model output. They use two new random seeds across three previously studied task families. The checked G55 task index classified all six as unfamiliar. The same first and third outputs served both comparisons. Across the six four-offer receipts, generation cost 1,397 seconds of recorded wall time and 2,189 server CPU seconds. The six server startups took another 58 seconds. The policy times sum the actual calls each would use and exclude the intervening pause for another training job. The measurements cover one G55 trunk and one program per seat.

The prespecified promotion test required additional correct deliveries on both runtimes with zero new wrong answers. The three-seat chooser tied on both. The earlier five-of-six result applies to its original panel. The official held-out gate and generation runtime require their own measurements.
## Reproduction

Start with the original G55 pre-exam training artifact. The input-index projection needs the frozen training SHA-256 `c33f707c7120d279c050748a5752067be708687711aa9acc84a4f434208fadfd`. Running the generator with the resulting index in `HIVE_FAMILIAR_TASKS` and empty local memory regenerates `cases.json`. Its SHA-256 is `0b307fa20ab55c4a4cfdae856be3d3d29485dc1829abffd35aaca08e2c5888ac`.

From the repository root, reproduce each question with the previously pinned server, model, and G55 adapter. Use a fresh output location. The native runner verifies the assets and the frozen questions before sending model messages.

```sh
python -m training.experiments.astra_orders.replication.native --case 81171-cold-chain \
  --runtime /path/to/llama-server --model /path/to/model.gguf --lora /path/to/t80.g55trunk.gguf \
  --out /tmp/f2-replication-81171-cold-chain.json --log /tmp/f2-replication-81171-cold-chain.log
python -m training.experiments.astra_orders.replication.replay --sdk /path/to/wasi --out /tmp/f2-replication-scores.json
python -m training.experiments.astra_orders.replication.summarize
```

The replay command uses the committed, reviewed program digests. Each program receives its own directory and writes its own requested deliverables. The independent grader sees the decisions only after the chooser has selected or withheld the answer for each request. [Frozen protocol](protocol.md) · [Cases](cases.json) · [Native offers](offers/) · [Chooser records](scores.json) · [Accounting](summary.json)
