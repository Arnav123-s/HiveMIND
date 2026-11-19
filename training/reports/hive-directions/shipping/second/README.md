# Can a less restrictive shipping reader help?

The first trial's reader required explicit rounding language and declined every request. For this second trial the implementer knew that aggregate result and the depot's published tariff. They saw neither evaluation panel. A different agent independently authored and froze 30 new requests and exact argument labels. The revised reader accepted ordinary depot fee requests and attempted to bind weights to units and parcel counts. The runner and saved shipping program were the same as before. All numbers below are at the saved-method entry after a request has been passed in for work. [Decision criteria recorded before scoring](../second-panel-plan.md) · [Fixture and label protocol](protocol.md) · [Cases](cases.json)

| Fresh second panel | Correct jobs / 15 valid | Called with wrong weights | Valid jobs missed | Calls on 15 invalid or unrelated requests | Correct declines | Correct decisions / 30 |
|---|---:|---:|---:|---:|---:|---:|
| Current saved-method reader | 9 | 3 | 3 | 8 | 7 | 16 |
| Second research reader | 5 | 1 | 9 | 0 | 15 | 20 |
| Always decline | 0 | 0 | 15 | 0 | 15 | 15 |

The reader stopped all eight calls on invalid or unrelated requests and reduced mistaken arguments from three to one. Its five completed jobs were short of both requirements. It had to match the current reader's nine completions and complete at least half the valid jobs. It fails the adoption criteria even though its overall decision score increased. In the remaining wrong quote, “a pair of 224 g packets and a 693 g parcel” supplied the solver with only one 224 g packet. Several missed jobs used ordinary constructions, including weights written in words and an explicitly empty shipment. A next experiment can show the interpreted list or ask about exactly the unresolved count, then measure how much valid work one extra turn recovers. [Exact arguments, returned fees and code hashes](observed.json)

As a secondary check we applied this same frozen second reader to the 28 messages from the first trial. It correctly completed five jobs, used wrong arguments on one, missed eight and correctly declined every one of the 14 negatives. The stock reader completed seven, used wrong arguments on five, missed two and made ten calls on negatives. The first trial's aggregate findings influenced the redesign. The 30 fresh messages above are the primary comparison. Both panels are deliberately balanced, constructed sets for one known tariff. [First-panel replay](first-panel-replay.json)

## Reproduce

Use the project environment with the CPython WebAssembly SDK described in the [fieldwork setup](../../../rule_lab/fieldwork/reproduce.md). The compiler or a language model is unnecessary. Run these commands from this directory with the checkout and SDK on your machine.

```sh
python ../first/compare.py --checkout /path/to/HiveMIND --sdk /path/to/wasi --adapter adapter.py --cases cases.json --out replay.json
diff -u observed.json replay.json
python ../first/compare.py --checkout /path/to/HiveMIND --sdk /path/to/wasi --adapter adapter.py --cases ../first/cases.json --out replay-first.json
diff -u first-panel-replay.json replay-first.json
```

The fixed reader SHA-256 is `5b5f43c57e514287d6f27953dc891f610c5edd0592f4a14ee58b8ed84b8d720b`. The second-panel label file SHA-256 is `c08ce69148b1c74fceb586f7f64335b978e94f293579855928dd00780038a131`. Both raw outputs record the hashes of the reader, labels, grading program, interpreter, shipping method and stock router.
