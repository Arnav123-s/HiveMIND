# Guarded traces for depot pricing

This experimental wrapper accepts exact decimal kilograms using an existing saved depot tariff. After observing three successful fallback executions on different shipments, it can qualify a sibling program on separately labeled shipments. A named tariff normally needs a convention check and a price calculation. The compiled sibling can deliver the price in one WASI call. The wrapper uses `HIVE_BANK`, a separate experimental bank and zero language-model calls. It models an illustrative depot tariff. [Protocol and controls](protocol.md) · [Implementation](trace.py)

## Prospective result

The independent evaluator replayed the same 32 English requests against two banks. Each configuration had 11 answerable requests and 21 requests that should receive no price. The handwritten and guarded arms answered all 11 and withheld all 21 in each bank. No arm returned an incorrect price. The original saved frontend delivered one of the 11 on the single-parent bank and none on the conflicting bank. The 32 questions were reused across bank configurations. [Raw results](../confirmation/shipping-results.json) · [Protocol](../confirmation/protocol.md)

| Bank | Arm | Correct prices | Justified abstentions | WASI calls in evaluation | Case time |
| --- | --- | ---: | ---: | ---: | ---: |
| One parent | Handwritten adapter | 11/11 | 21/21 | 20 | 7.67 s |
| One parent | Qualified guarded traces | 11/11 | 21/21 | 15 | 4.21 s |
| Competing parents | Handwritten adapter | 11/11 | 21/21 | 39 | 20.54 s |
| Competing parents | Guarded traces | 11/11 | 21/21 | 39 | 15.96 s |

On the single-parent bank, 10 requests used a qualified sibling. Guest inputs fell from 29 to 19, and fuel fell from 20.45 billion to 15.37 billion. Preparing all three rounding scopes cost 14 guest calls and 14.32 billion fuel units. At five calls saved per repeated batch, three batches of the same request mix would repay the startup cost. On the mixed bank the wrapper admitted no siblings and used the original version and disagreement checks on every eligible request. Timing is one sequential run per arm under competing CPU load. The mixed bank illustrates its variability even with identical execution counts.

The new coverage came from the human-specified units and grammar. Compiling qualified siblings reduced the cost of repeated requests in the single-parent case. An uncalibrated guarded wrapper attained the same answer coverage as the handwritten adapter. All arms made zero model calls.

## Try it

Run from the repository root with the project's Python environment and fieldwork SDK installed. Set `HIVE_FIELDWORK_SDK` to the directory containing `python.wasm` and `lib`.

```sh
export HIVE_BANK="$PWD/training/reports/retained-skills/shipping/bank"
python -m training.experiments.atlas.traces.demo --sibling-bank /tmp/hive-trace-demo \
  answer 'Calculate the depot shipping fee for 0.640 kg using per-parcel rounding'
```

The response includes the path taken, the number of WASI calls, inputs evaluated, instruction fuel and wall time. Supplying the same named shipment three times records one distinct exit. On a previously unseen English form, `--mode stock` shows the existing saved dispatcher’s response and `--mode handwritten` directly converts kilograms before invoking that dispatcher. The default `guarded` mode can use the independently qualified sibling. No nightly workflow or ordinary chat route imports this experiment.

## Reproduce the checks

```sh
python -m training.experiments.atlas.traces.check --sdk "$HIVE_FIELDWORK_SDK" \
  --out /tmp/hive-trace-development.json
python -m training.experiments.atlas.confirmation.shipping --sdk "$HIVE_FIELDWORK_SDK" \
  --out /tmp/hive-trace-confirmation.json
```

The development check exercised 15 requests and five promotion decisions. One wrong label prevented publication even though the candidate passed the other three examples. Reopening the bank preserved evidence. Adding a real second WASI tariff forced reevaluation and withheld an ambiguous answer. On a 640 g example, the existing saved frontend abstained on the kilogram wording. The direct handwritten adapter and guarded sibling each returned 430 cents. The direct adapter used two WASI calls and 2.045 billion fuel units. The sibling used one call and 1.026 billion fuel units. One warmed run took 0.97 and 0.44 seconds respectively. Initial WASI compilation took 5.61 seconds. [Development receipts](development.json)

The prospective panel uses a separate evaluator, independently labeled qualification shipments, two bank configurations and 32 previously withheld English requests. Both coverage and timing require a comparison with the direct handwritten adapter, since a developer supplied the grammar and conversion. Three successful exits and an additional external qualification panel are setup costs for each new sibling. [Independent evaluator](../confirmation/shipping.py) · [Frozen confirmation protocol](../confirmation/protocol.md)
