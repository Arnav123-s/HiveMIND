# Niche expansion niche-expansion-002b — data-format-model

Runner: `python3 -m factory.niche_expansion.expansion_cycle --subject data-format-model --cycle-id niche-expansion-002b`. Steps 1-6 of PLAN.md section 3 only; adoption (section 4) is the coordinator's sitting.

Verdict: **REJECTED**

## Gate

| slice | model | majority | rule | min per-class recall |
|---|---|---|---|---|
| held-A | 0.9111 (n=90) | 0.2 | 0.7333 | 0.6667 |
| held-B | 0.9444 (n=90) | 0.2 | 0.7333 | 0.7222 |

Per-class recall held-A: {'json': 0.8889, 'malformed-json': 0.6667, 'csv': 1.0, 'toml': 1.0, 'plain-text': 1.0}
Per-class recall held-B: {'json': 1.0, 'malformed-json': 0.7222, 'csv': 1.0, 'toml': 1.0, 'plain-text': 1.0}

## Generation (oracle-verified at generation)

- train: 600 kept, drops {}
- held_a: 90 kept, drops {}
- held_b: 90 kept, drops {}

## Contamination filter

- train 600/600 kept; held-A 90/90; held-B 90/90

## Battery BEFORE (through ServingHive)

```
{
 "classify-data-format": {
  "job": "data-format-model",
  "right": 0,
  "n": 10,
  "acc": 0.0,
  "bar": 8,
  "detail": "0/10 correct; bar 8/10; gaps: no specialist registered for job 'data-format-model'"
 }
}
```

Pre-adoption the job is unregistered; the no-specialist result above is the expected BEFORE state, not a failure.

## Methods provenance

dev-split recipe selection on train only (dev n=120): hidden 4 chosen smallest-first within 0.02 of best dev acc 1.0; finalists (hidden 0/4/8) trained on full train (n=600) via executors.retrain_candidates and ranked on held-A; held-B spent once on the winner (hidden 4, 4125 params). Data: three disjoint template partitions, oracle-verified at generation (drops in the generation stats), contamination-filtered against the other partitions and all five existing battery item sets plus this subject's hand-authored battery items.
