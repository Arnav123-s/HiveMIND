# Can 30 matching Python calls confirm correctness?

**The 30-probe rule falsely confirmed all six previously failing lookup submissions when the other candidate implemented the same lookup behavior.** Neither candidate matched the independent reference on any of the 30 probes in any of those six jobs. Requiring the one-argument signature shown in the user's request still falsely confirmed all six constructed pairs. Five jobs had a genuine archived worker to compare against the lookup. In all five, the first probe distinguished the programs. The sixth job had no genuine module among the original accepted candidates. [All paired outputs and probe inputs](results.json)

| Candidate pairing | Pair instances | Matched all 30 | Withheld |
|---|---:|---:|---:|
| Historical failed lookup and same-behavior dictionary peer | 6 | 6 | 0 |
| Two same-behavior lookups with exact one-argument declarations | 6 | 6 | 0 |
| Historical lookup and the available real worker | 5 | 0 | 5 |
| Distinct historically passing workers, same family | 4 | 2 | 2 |

The five worker files had all passed the earlier independent grade. The two Roman workers agreed on every probe. Of the three possible pairings among the duration workers, one agreed on all 30. Both other pairings disagreed on one result. For 61,228 seconds, one worker returned `17h 28s` and the other two returned `17h28s`. The independent reference uses adjacent units, matching the published examples. Four of the five real workers scored 30/30 against it; the fifth scored 29/30. All 13 distinct modules completed all their calls without an exception, for 390 function invocations. The mixed lookup/worker comparisons used the requested one-argument calls; the lookup declares variadic arguments, while the genuine modules have fixed signatures. A strict declaration-only prefilter would also withhold those mixed pairs. Both false-confirmation controls matched declarations on both sides.

Each candidate is an archived Python module or a constructed comparison control. All source execution happens inside the project's read-only CPython WASI guest. The differential decision checks matching values and their declared scalar types, withholding on either error. An independent functional reference scores each result afterward. The probe set has 15 calls to each of two public functions per family, on inputs valid for the duration or Roman-numeral contract. [Protocol frozen before execution](protocol.md) · [Runnable comparison](study.py)

The six historical lookup submissions correspond to two distinct source hashes. They passed the public examples in the earlier study and each failed its original official grade. Each comparison modelled a pair of correlated errors: an original example lookup and a separately written dictionary lookup with the same defaults. The participants in these constructed pairs share the same deliberately limited behavior. These tests measure what differential checking can identify under that condition. They do not estimate how frequently two independently generated workers make that error. [Original sources and grades](fixtures.json) · [Original PR #123 study at its identified commit](https://github.com/Arnav123-s/HiveMIND/tree/c2c71fadc38d28ca85de6a52226ece132c2f194e/training/experiments/verified_growth/delivery_audit/public_examples)

Thirty identical outputs can be evidence that programs behave alike on the chosen inputs. A counterexample can show they disagree without identifying the correct member. An external expected value or a trusted property supplies that distinction. Here two worker files from different archived jobs can also share ancestry or prompts; “distinct” means their source hashes differ. The results carry no official unseen-kind credit.

From the repository root, use its Python environment and installed CPython WASI SDK to reproduce all candidates and comparisons.

```sh
python -m training.experiments.astra_orders.module_checks.study --sdk /path/to/wasi --out /tmp/module-checks.json
```
