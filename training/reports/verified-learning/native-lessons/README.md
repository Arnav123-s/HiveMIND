# Two model-written corrections repair a third program

A local 8B model corrected two failed programs after seeing their public counterexamples. Both corrections changed a count of list entries into a total of the quantities in those entries. Once both corrections independently qualified, the hive applied that edit to a third, previously failed work order with its writer disabled. The deposit calculator then delivered **24 correct answers out of 24**. The same draft delivered zero before either correction, after only one correction, and with learning disabled on the mature bank.

Four tasks and their grading data were frozen before inference. A person supplied each initial failed draft and chose this family of mistakes for the study. The two correct donor programs came from actual generations of Ternary-Bonsai-8B with its G47 coding adapter. Each generation received the existing draft, four public examples, the first public failure and a general instruction to make a minimal edit. The model had no access to the qualification cases, jobs, expected private outputs, other donor, or target contract. Each donor used its own empty bank, and neither received an example of a correct implementation.

| Independent donor | Change made by the 8B writer | Initial public | Corrected public | Qualification | Fresh jobs | Generated tokens |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Garden seedling count | Total the seedlings in the trays | 1/4 | 4/4 | 12/12 | 24/24 | 18 |
| Equipment locker balance | Add the net change from signed transactions to the opening stock | 1/4 | 4/4 | 12/12 | 24/24 | 27 |

The first donor read a dictionary field directly. The second used a local variable inside an addition. Both produced the same expression rule after the system abstracted the names. The live generations took 49.7 and 38.4 seconds on two configured CPU threads. Each qualified on its first correction.

| Recipient, 24 new jobs each | Zero donors | One donor | Both donors | Both donors, learning off |
| --- | ---: | ---: | ---: | ---: |
| Refund seven cents per returned container | 0 delivered | 0 delivered | **24 correct** | 0 delivered |
| Find the longest individual queue wait | 0 delivered | 0 delivered | 0 delivered | 0 delivered |

The two-donor deposit revisit reused the exact failed source and its existing work directory. It tried one public candidate, changing `7 * len(boxes)` to `7 * sum(boxes)`, and passed all four public and twelve qualification cases. No generator was available on either revisit. The queue order also had a counting error, but summing wait times gives the wrong answer for the longest wait. Its public checks rejected the one learned candidate. Every withheld job emitted zero answer files, and no arm delivered an incorrect answer. All 160 task labels were independently recalculated, with unique inputs across the public, qualification and delivery sets within each task.

This prospective test covers two deliberately analogous faulty programs, one positive target and one negative control. It measures repair-knowledge transfer with a fixed model and a bounded grammar. Its task count cannot estimate how often this works on independently occurring errors.

## Try the learned result

After setting up the project's fieldwork runtime, run this from the repository root. The checked-in bank is the exact record earned by the two-donor revisit. The normal CLI returned **112 cents** on this additional input with model inference disabled.

```sh
HIVE_BANK=training/reports/verified-learning/native-lessons/example-bank ./hive --once 'Run refill_deposit with {"returns":[11,0,5]}'
```

## Reproduce the experiment

The evidence replay requires the project's Wasmtime Python environment and WASI guest. It checks the original four donor submissions in the same prompt contexts, reconstructs both independent banks, and grades every recipient stage. Set `HIVE_FIELDWORK_SDK` to the installed WASI directory. Pass a checkout at commit `00630008cf3dd74ce70dade0d330cab7a9d8b40a` via `--checkout` to use the original code snapshot.

```sh
.venv/bin/python training/reports/verified-learning/native-lessons/replay.py --sdk "$HIVE_FIELDWORK_SDK" --output /tmp/hive-native-lessons.json
```

The optional `collect.py` reruns real donor inference. It accepts `--binary`, `--weights`, `--adapter`, `--sdk` and `--output`. The original run used ik_llama.cpp, base model `prism-ml/Ternary-Bonsai-8B-gguf` (SHA-256 `1376f942aa90e60f7b570c1d81b3916fea1315ff85aa1c4d19006af68fb4b922`) and adapter `t80+g47code2.gguf` (`a708720b70b0fe574a6e0184951245337de7fc80ade032b4a2f264d8ac30f381`), greedy decoding, seed 3141, two CPU threads and a 240-token cap per generation.

[Protocol](protocol.md) · [Frozen work orders](orders.json.gz) · [Separate grading answers](keys.json.gz) · [Exact donor messages and raw responses](native-traces.json.gz) · [Original native receipts](native-results.json.gz) · [Transfer receipts and every delivered answer](transfer.json.gz)
