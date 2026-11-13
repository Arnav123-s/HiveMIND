# Niche expansion niche-expansion-003b — sql-statement-model

Runner: `python3 -m factory.niche_expansion.expansion_cycle --subject sql-statement-model --cycle-id niche-expansion-003b`. Steps 1-6 of PLAN.md section 3 only; adoption (section 4) is the coordinator's sitting.

Verdict: **BORN-STAGED**

## Gate

| slice | model | majority | rule | min per-class recall |
|---|---|---|---|---|
| held-A | 1.0 (n=126) | 0.1429 | 1.0 | 1.0 |
| held-B | 1.0 (n=126) | 0.1429 | 1.0 | 1.0 |

Per-class recall held-A: {'select': 1.0, 'insert': 1.0, 'update': 1.0, 'delete': 1.0, 'create': 1.0, 'alter': 1.0, 'drop': 1.0}
Per-class recall held-B: {'select': 1.0, 'insert': 1.0, 'update': 1.0, 'delete': 1.0, 'create': 1.0, 'alter': 1.0, 'drop': 1.0}

## Generation (oracle-verified at generation)

- train: 280 kept, drops {}
- held_a: 126 kept, drops {}
- held_b: 126 kept, drops {}

## Contamination filter

- train 280/280 kept; held-A 126/126; held-B 126/126

## Battery BEFORE (through ServingHive)

```
{
 "classify-sql-statement": {
  "job": "sql-statement-model",
  "right": 0,
  "n": 14,
  "acc": 0.0,
  "bar": 11,
  "detail": "0/14 correct; bar 11/14; gaps: no specialist registered for job 'sql-statement-model'; update/delete-without-where subset: 0/2 correct"
 }
}
```

Pre-adoption the job is unregistered; the no-specialist result above is the expected BEFORE state, not a failure.

## Methods provenance

dev-split recipe selection on train only (dev n=56): hidden 4 chosen smallest-first within 0.02 of best dev acc 1.0; finalists (hidden 0/4/8) trained on full train (n=280) via executors.retrain_candidates and ranked on held-A; held-B spent once on the winner (hidden 4, 1287 params). Data: three disjoint template partitions, oracle-verified at generation (drops in the generation stats), contamination-filtered against the other partitions and all five existing battery item sets plus this subject's hand-authored battery items.

## Staged model

- coding/swarm/models/sql-statement-model.json sha256 7fcc2f706da53932e881d5bfef88b291bf89b7834f088c5920dc598275af96da
