# Switching between saved billing rules

A customer can ask for a different rounding convention and then switch back in a later process. In this replay the normal `./hive --once` command returned **all seven requested amounts correctly**. It withheld three requests that lacked a matching version, enough information to select one, or a valid contract ID. Each request started a fresh process with the local models and adapters unavailable. [Inputs and terminal replies](results.json)

| Request sequence | Bills in order | Returned cents |
| --- | --- | --- |
| Shipping, per parcel → pooled → per parcel | 130 and 170 g · 620 and 630 g · 119 and 230 g | 430 → 520 → 430 |
| Invoice tax, per line → invoice total → per line | 14, 14 and 14 cents · 16 and 10 cents · 4 and 7 cents | 3 → 1 → 0 |

The six bills above differ from the public examples, qualification cases and bills used to select a convention. Every bill also produces a different amount under the other rounding rule. On an invoice of 4 and 7 cents with the convention omitted, the hive reported that its versions returned 0 and 1 and withheld the answer. On an invoice of 20 and 40 cents they agreed at 3 cents, which it released. Before the per-parcel version was installed, it withheld an explicitly per-parcel bill. It also rejected an unavailable contract ID.

All four programs passed two public examples and two independent qualification cases apiece in the CPython WebAssembly guest. The per-parcel program came from the released, corrected G47 draft. The two invoice programs and the pooled program were supplied for this test. The experiment measures selection of already-qualified code and uses zero model calls. [Shipping source](../../retained-skills/shipping/bank/) · [Invoice sources](../../retained-skills/work-order-cases.json)

When a customer names a convention, each candidate runs on two fixed bills with known results from that convention. For two 11-cent lines, rounding the 5% tax on each line gives 2 cents in total. Rounding the tax on the combined invoice gives 1 cent. A second example checks half-up ties. Two 1 g parcels cost 430 cents when rounded separately and 340 cents under pooled rounding. Candidates that pass both examples then compute the actual bill in WebAssembly. If more than one survives, their answers must agree. This test covers the documented tariffs and the request forms exercised here.

## Reproduce

From the repository root, run the opt-in guest setup once. The replay creates a temporary bank, qualifies the supplied sources, runs ten independent terminal commands, and checks their exit codes and outputs.

```sh
python scripts/setup_fieldwork.py
.venv/bin/python training/reports/verified-learning/switching/replay.py --out /tmp/switching.json
```

Set `HIVE_FIELDWORK_SDK` or pass `--sdk` to use an existing guest. If you installed Wasmtime into another virtual environment, run the replay with that environment's Python. [Replay script](replay.py)
