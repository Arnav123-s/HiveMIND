# Worker instructions and HTTP page counts on G55

**The normal CPU worker passed 4/6 with short instructions, full instructions, the familiarity gate, and the scaffold.** Full instructions solved a counter-wrap task that short instructions missed, and lost a scheduling task that short instructions solved. The familiarity gate made the same trade and took 297 seconds across six first programs, compared with 159 seconds for short instructions. This paired trial gives no net gain to justify making full instructions the default on unfamiliar requests.

The revised paired trial tested the normal chooser, modular instructions and a third independent worker on these six requests. The prespecified variant tied the short control at 4/6. An exploratory greedy variant with a third seat reached 5/6 on both Python runtimes. [Paired results and conditions](diverse/README.md)

## What the old results measure

G55's 33/34 on older practice kinds and 29/62 on newer practice kinds add to 62/96. G56 scored 35/40 and 27/56, also 62/96. Both age groups had practice generators. G55 graded 1/29 fixed held-out tasks and G56 graded 2/30; each passed 0/10 held-out kinds. G55 was kept, and G56 was dropped. The generation records include no `orders_ab` measurements for either body. The older 1.7B experiment gives a separate comparison: on the same later-practice stream, the short-prompt control reached 16/18 and the memory-off full prompt reached 6/18. That smaller model scored 1/4 versus 0/4 on unseen kinds, with shared CPU time and two timeouts across the study. [G55](../../../docs/reads/g55.md) · [G56](../../../docs/reads/g56.md) · [Prior prompt experiment](../../../docs/RESEARCH.md#8-do-the-hives-memories-help-measured-on-one-stream-2026-11-18)

A trained member normally receives `SHORT`. `HIVE_FULL_ORDERS=1` supplies `MEMBER` when no engram or forced-short setting takes precedence. Both prompts receive the task and the usual notice when the engine materializes supplied data. The growth workflow already supports a practice-only split by runner through `HIVE_SHORT_ORDERS_AB`. [Member](../../../team/solo.py) · [Given data](../../../team/tools/sandbox.py) · [Practice split](../../practice_arms.py)

## Six paired first programs

One member of the kept G55 body answered six offline requests using full and short worker instructions. Three were fresh draws from taught families, three were independently authored contracts. A separate frozen scaffold changed two prompts; the other four use their identical short-arm response. The SHA-256 checks in `generate.py` identify the repacked native Bonsai 8B CPU runtime, base and G55 trunk. Each call has one unassisted program, greedy sampling, a fresh prompt cache and a 192-token generation cap. Programs run with the normal source extractor, the original sandbox hooks, writable task files and read-only CPython WASI standard library. The three taught requests use their original graders. The other three are checked for exact stated output and files. The trial excludes retries, multi-seat agreement and the official fixed exam. [Frozen protocol](protocol.md) · [Panel and independent graders](panel.py) · [Frozen prompts](inputs.json)

The familiarity check uses the existing token-Jaccard method, its original 0.30 threshold and 2,852 distinct G55 `first` lesson requests. None of the six texts occurred verbatim. Top similarity was 0.632–1.000 for the practiced formats and 0.071–0.113 for the new contracts. The weekday control has a perfect token-set match because the tokenizer ignores short numbers. Prior lessons supply only resemblance scores for this policy; the model receives no recalled examples.

All 14 native calls completed, with zero prompt-cache hits and zero truncated responses. Total time including model load was 10 minutes 36 seconds. The first table uses comparable six-task totals, reusing the same logged response when policies agree. CPU and wall times measure this two-core first-program run only.

| Policy | Frozen WASI passes | Normal CPython passes | Prompt / output tokens | Model wall seconds | Model CPU seconds |
|---|---:|---:|---:|---:|---:|
| Short | 4/6 | 4/6 | 967 / 486 | 159 | 312 |
| Full | 3/6 | 4/6 | 4,621 / 635 | 384 | 742 |
| Familiarity gate | 3/6 | 4/6 | 2,794 / 630 | 297 | 570 |
| Short plus scaffold | 4/6 | 4/6 | 1,057 / 547 | 176 | 343 |

The original checker had a runtime mismatch. The full instruction response correctly computed `[7, 6, 22, 3]` and 38 pulses, but made an unused `requests` import unavailable in CPython WASI. We retained that grade and reran **all 14 unchanged programs** through the repository's normal CPython worker. This secondary replay accepts only the digest of the 14 inspected local programs, with fresh temporary folders. It changed exactly that one verdict. Each policy passed all three practice controls and one of three unfamiliar requests on the normal worker. Full and gated instructions gained the counter and lost the scheduling problem on an invalid `datetime` keyword. Short instructions printed the correct 5 waiting minutes and exit minute 34. The union of the short and full successes covers 5/6; the frozen chooser delivered 4/6. [Raw programs and native timings](native.json) · [Primary grades](grades.json) · [Primary policy totals](summary.json) · [Normal worker replay](production.json)

The scaffold changed two of six asks and gained no complete task. It produced the missing cold-chain file with the correct rows, but wrote whole records instead of the requested lot codes. On the meter it handled wrapping with 31 instead of 32. The file and stdout both failed. [Requested outputs and independent checks](panel.py) · [Actual written files](production.json)

## Can a URL count enforce pagination?

Eight G55 after-body pulse archives contain three requests mentioning pages. Both book-category jobs that asked for “several pages” passed without an explicit numeric target. The quotes request explicitly asked for the first five pages, an author-count JSON file and the leading author. Five members used 26 program turns. Twenty turns raised exceptions, including seven type errors, four value errors and three exhausted searches. Six returned normally. One printed `Albert Einstein`; the final report recorded a missing `authors.json` from all five. The archived stderr streams contain zero `HIVE-SAME` notices and zero `HIVE-HTTP` errors. The existing hooks log repeated addresses and HTTP errors, so successful page coverage cannot be reconstructed from these notices. The candidate failure already carried actionable feedback on most turns. [Original G55 run](https://github.com/Arnav123-s/HiveMIND/actions/runs/44728930517) · [Per-turn archived reasons and checksums](web.json)

A local HTTP server served a five-page version of the same count-and-file request. Every fetch used a real loopback GET. The table compares the proposed rule, “five distinct URLs fetched”, against independently specified author counts. These four deliberately chosen cases check logical validity. They do not estimate prevalence in live browsing.

| Worker behavior | Distinct URLs | Rule accepts | Counts correct |
|---|---:|---|---|
| Parse five pages at five addresses | 5 | Yes | Yes |
| Parse the first page five times | 1 | No | No |
| Parse one page and fetch four assets | 5 | Yes | No |
| Parse five representations at one endpoint with a public cursor header | 1 | No | Yes |

A cache keyed only by URL returned the first cursor response four more times. The same client with uncached reads returned all correct counts. The endpoint specified `Vary: X-Cursor`. An explicit numeric request, an observable pagination contract and checked output are separate pieces of evidence. The handoff's forced retry and URL-only cache fail these controls. The separate conservative cache experiment runs the same cursor endpoint twice: it fetches ten times without an explicit public freshness lifetime and five times when the server authorizes reuse. Both traversals preserve the exact counts. This trial leaves user modules untouched. [HTTP replay](web_pages.py) · [Traces and reference values](web.json) · [Conservative cache experiment](http_cache/)

## Module boundaries

The Wave 1 T4 audit exercised the actual Python-file chooser. Different correct modules could pass when both workers printed the same notice. Mutually wrong modules and conflicting modules could also pass with that shared notice. A generated input can expose a difference, but a trusted contract must tell the chooser what to expect. In particular, an undocumented empty list need not be a legal argument. The companion WASI study executed 30 type-valid calls per pair. All six previously failing lookup submissions passed the matching-output rule when a second candidate implemented the same wrong behavior. [Archived candidates, reference checks and results](module_checks/README.md) [T4 audit and four observed cases in PR #131](https://github.com/Arnav123-s/HiveMIND/blob/review/astra-cpu-wave/training/experiments/astra_cpu/handoff_audit/README.md) · [PR #131](https://github.com/Arnav123-s/HiveMIND/pull/131)

## Reproduce

Run from the repository root in the HiveMIND Python environment with `wasmtime`. `CELL` is the public `t80.g55trunk.gguf` asset in the `hive-grown` release, `BASE` is the Prism Ternary-Bonsai-8B GGUF named by SHA in `generate.py`, `LLAMA` is the ik_llama.cpp `llama-server` executable from revision `7aa7e01482db892b023bb9aace9a40567ab5297a`, and `SDK` contains `python.wasm` and its `lib` directory. Give the server two available CPU cores. `native.json` is created once, with per-call checkpoints.

```bash
D=training/experiments/astra_orders
python -m training.experiments.astra_orders.generate --runtime "$LLAMA" --model "$BASE" --lora "$CELL" --out /tmp/native-orders.json --log /tmp/native-orders.log
python -m training.experiments.astra_orders.grade --panel "$D/panel.json" --inputs "$D/inputs.json" --native /tmp/native-orders.json --sdk "$SDK" --out /tmp/order-grades.json
python -m training.experiments.astra_orders.production_replay --out /tmp/production-order-grades.json
```

To rebuild the frozen input file, use `prepare.py` with `rows.jsonl` extracted from G55 `all-rows` artifact 14630086449, frozen `astra_transfer/scaffolds.py`, and the desired output path. The committed prompts also permit replay without retrieving history or rebuilding the scaffold. To replay the HTTP checks, pass the eight `gate-after-*.zip` files' directory, `gate-work-after-6` artifact 14644824529 and an output path to `python -m training.experiments.astra_orders.web_pages`. [Public adapter](https://github.com/Arnav123-s/HiveMIND/releases/download/hive-grown/t80.g55trunk.gguf) · [G55 archives](https://github.com/Arnav123-s/HiveMIND/actions/runs/44728930517)
