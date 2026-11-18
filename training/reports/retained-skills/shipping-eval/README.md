# Fresh shipping-fee exam

A depot charges 250 cents per shipment and 90 cents per started 500 grams. Under convention A it rounds each parcel up before adding its units. Under B it rounds up the combined shipment weight. The instructions described the fee and the examples specified the convention. This replay uses all four program drafts that the G47 specialist actually returned. [Original replies](../shipping-live.json)

| Draft and method | Public examples | Earlier qualification | Fresh shipments |
|---|---:|---:|---:|
| A, each of two identical raw drafts | 2/8 | 0/12 | 4/100 |
| A, first edit passing every public example | 8/8 | 12/12 | 100/100 |
| A, take the first edit without checking | 8/8 | 12/12 | 100/100 |
| B, either raw draft or its first edit | 0/8 | 0/12 | 0/100 |

The A edit changes when integer rounding happens. The raw program multiplied by the price before integer division. The repaired program computes billable units first. There was exactly one proposed edit for each draft, so the blind and checked choices tied on A. The B drafts failed on the supplied input type, and no arithmetic edit passed the public examples. Applying A’s winning program to the B shipments scored 38/100. The replay used zero additional model calls.

Three correct control programs kept their original bytes and passed 72/72 hidden inputs. A separate control used an equivalent version of the net-fee program with a multiply/divide expression eligible for editing. The public check kept that code and it passed 24/24. Blindly taking its sole edit gave 0/24 on the same 24 inputs.

## Reproduce

From the repository root, use the project Python environment with Wasmtime installed and the pinned CPython WASI SDK. [SDK download and setup](../../rule_lab/fieldwork/reproduce.md)

```sh
python training/reports/retained-skills/shipping-eval/score.py --sdk /path/to/wasi
```

The command reads both raw attempts and their public examples directly from the original replies. The compressed fixture includes all 200 new shipments, the three control sets, the earlier qualification examples and 128 distinct prior shipment multisets used for exclusion. The grader verifies the frozen input hashes, recomputes each expected shipping fee with decimal ceiling arithmetic, and rejects reused input multisets, including permutations. The original empty input had already appeared in the public examples. The five fresh strata each contribute 20 jobs per convention.

Every candidate runs in the same WebAssembly guest. The public selector can try at most eight single edits per raw program. The blind control always takes the first generated edit. Source programs are fixed before qualification or fresh grades are read. The replay checks recorded scores and output hashes for both policies and all controls. [Freeze protocol](protocol.json) · [Frozen cases](fixtures.json.gz) · [Grader](score.py) · [Scores](results.json)
