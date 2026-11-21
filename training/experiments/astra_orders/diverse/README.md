# Contrasting instructions and checking module disagreements

**The prespecified two-seat policy delivered 4/6 on CPython and 4/6 on WASI, tied with short instructions.** Each delivered four right answers, abstained twice and shipped zero wrong answers. Allowing a third sampled short offer used 14 calls instead of 12 and still delivered 4/6. On the pulse counter a third short offer was right but lacked an independent witness. The modular second offer wrote the raw readings as increments, exited cleanly and printed the wrong sum. Delivering the clean survivor would be an error.

The preplanned greedy single-offer contrast scored 5/6 on both runtimes, compared with 4/6 for a greedy short worker. The greedy modular worker solved the counter and scheduling questions. The cold-chain file contained objects rather than lot-code strings. After inspecting the native programs we tried greedy modular in seat two plus the already frozen short third offer on disagreement. This **exploratory** chooser delivered 5/6 on both runtimes, with 14 programs, zero wrong and one withheld. With just two seats the exploratory policy still delivered 4/6. The counter gain came from independent file contents and printed totals matching. It requires replication on different input draws.

| Six-panel policy | Right | Wrong | Withheld | Calls | Seconds summed across recorded calls |
| --- | ---: | ---: | ---: | ---: | ---: |
| Two short seats | 4 | 0 | 2 | 12 | 325 |
| Short + sampled modular | 4 | 0 | 2 | 12 | 480 |
| Short seats with a third on disagreement | 4 | 0 | 2 | 14 | 453 |
| Short + sampled modular with a third | 4 | 0 | 2 | 14 | 608 |
| Exploratory greedy modular with a third | 5 | 0 | 1 | 14 | 671 |

Eighteen new offers plus the six archived short offers populated these comparisons. The new offers cost 1,020 wall seconds and 1,342 server CPU seconds on the two-core allocation, with 4,990 input tokens and 1,568 output tokens. The times combine stored per-call measurements from different runs under different system loads. They are not estimates of an entire generation. No official gate or held-out-kind credit follows from the six-request panel. [Per-case decisions and outputs](scores.json) · [Timing and policy totals](summary.json) · [Native replies](native.json)

`HIVE_DIVERSE_ORDERS=1` sends an unfamiliar request to the first worker with SHORT and to the second worker with the modular instructions. The module includes the existing web/API guidance only on web-related requests, and the datetime guidance only on date-related requests. Familiarity compares the request with previously checked task wording at a Jaccard threshold of 0.30. The gate can load a frozen request-only index alongside local checked memory through `HIVE_FAMILIAR_TASKS`. Gather projects it from first-program rows before training and exams, uploads a separate artifact with no programs, answers, labels or messages, and supplies the same file to both enabled fresh/held arms. A re-sit of an earlier body uses that source run's pre-exam training artifact. On G55, starting with empty local memory reproduced all six original nearest-neighbor scores and routes from 2,852 requests. With neither a designated index nor local checked memory, the worker classifies each request as unfamiliar. A designated but unreadable index fails the enabled run. The choice preserves adapter seating, explicit practice arms, and the short prompt used with an engram. A worker with an empty answer cannot confirm a diverse peer. A third seat can resolve disagreement and costs another call.

`HIVE_DIFF_EQUIV=1` checks a single requested Python module in the CPython WASI guest selected by `HIVE_FIELDWORK_SDK`. On an opted-in hosted gate, the workflow loads the checked CPython archive from cache or a bounded download, verifies its SHA-256, and installs Wasmtime 36.0.0. The enabled leg fails explicitly if the dependency is unavailable. The default gate skips this setup. The guest supplies only public positional arguments to each candidate. On requests that declare order independence it can test up to 30 permutations of whole records. It tries smaller inputs only with explicit permission in the request to take a subset. When two successful returns differ it gives the third worker the shortest observed differing call, without either candidate's result. An unsuccessful guest invocation or an unsupported contract supplies no confirmation. In the original chooser, requested Python files were excluded from the file comparison and matching printed text could confirm them. Their SHA-256 digest protected a recorded artifact against a later change.

For a module whose **entire required behavior** consists of one specified sequence on a fresh instance, the chooser can additionally check the external expected results. The supported declaration is deliberately narrow. It uses the line `The complete required behavior is one run of the checks below, in order, on a fresh module.`, followed by `Required checks:` and a fenced Python block of standalone literal positional assertions. The returned values must agree with the supplied results; ordinary printed agreement and integrity checks still apply. The historical queue request covers additional valid calls and gets no such blanket confirmation.

The six correlated lookup pairs from PR #123 were all withheld. The module guard abstained because the original requests did not declare a complete finite check. The replay records zero probes on those six requests, so this result supplies no evidence that it identified each implementation error. Two genuine desk implementations differing only by a local name matched on 30/30 permitted calls but were withheld on the original queue contract. The same files passed the two-call, explicitly complete sequence on a fresh module. A different pair whose request allowed deleting whole records produced a one-item witness. All rollout switches default off. `HIVE_DIVERSE_GREEDY=1` together with `HIVE_DIVERSE_ORDERS=1` enables the exploratory greedy second seat in the normal worker. The prospective replication uses six different input draws. [Frozen replication protocol](../replication/protocol.md)

## Reproduction

Use the repository's Python environment, packed T80 server and G55 trunk whose SHA-256 digests appear in `native.json`. The program refuses mismatched runtime assets and a pre-existing output file. The normal-CPython replay is limited to the exact manually inspected output files in `reviewed.json`. When regenerating offers, inspect new programs for host side effects before enabling their immutable digest for host replay. The separate WASI guest lacks the Requests package and network access.

```sh
taskset -c 3,4 python -m training.experiments.astra_orders.diverse.native \
  --runtime /path/to/llama-server --model /path/to/model.gguf --lora /path/to/t80.g55trunk.gguf \
  --out /tmp/native-diverse.json --log /tmp/native-diverse.log
python -m training.experiments.astra_orders.diverse.replay --sdk /path/to/wasi --out /tmp/paired-scores.json
python -m training.experiments.astra_orders.diverse.controls --sdk /path/to/wasi --out /tmp/module-controls.json
python -m training.experiments.astra_orders.diverse.history /path/to/g55-rows.jsonl /tmp/g55-wording-scores.json
python -m pytest -q tests/test_diverse_orders.py tests/test_deliverables.py
```

The production worker code does not import the fixed panel, the queue reference implementation or the historical grader. The queue reference implementation and its renamed copy occur only as test candidates in the isolated control.
