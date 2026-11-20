# Generating small, solvable work orders from four operations

Four typed operations produced six different work orders for an event log. One generated request restricted the ledger to a given site, summed quantities by label, then returned the highest-total label. Across twelve independently authored ledgers, the generated programs returned **72/72 correct answers**, tying a hand-written six-task solver. A one-operation system could answer **24/72**. [All generated questions and returned answers](results.json)

| Solver | Correct | Wrong | Unsupported |
|---|---:|---:|---:|
| One operation | 24 | 0 | 48 |
| One operation returning the requested type when available | 33 | 15 | 24 |
| Execute the generated sequence | 72 | 0 | 0 |
| Hand-written six-task solver | 72 | 0 | 0 |

The proposer enumerates sequences of compatible operators and turns each into an instruction. It generated two one-step, three two-step, and one three-step job from row filtering, counting, grouping/summing, and selecting a winner. Adding the site filter changed the independently expected count on five ledgers, the totals on ten, and the winning label on five. A tie, an empty ledger, negative quantities, zero sums, case-sensitive labels and an absent site were represented. The independent evaluator used SQLite to supply expected outputs. The frozen solver never consulted the key to select a plan. [Generation protocol](protocol.md) · [Independent inputs](panel/cases.json) · [SQL examiner](panel/freeze.py) · [Answer key](panel/keys.json)

**Scope.** The generated abstract syntax tree supplied both the wording and the executable plan. The grader supplied new inputs for six known contracts. It did not supply new natural-language requests to parse. The comparison establishes bounded task variety and exact execution. It does not measure the ability to invent new primitive operations, select valuable exercises for a learner, or improve a model. The cases are twelve independent scenarios, reused for each of six jobs. They represent stipulated practical data, not recordings of production events.

Run from the repository root with Python's standard library.

```sh
python training/experiments/atlas/proposer/study.py --output /tmp/atlas-proposer.json
```
