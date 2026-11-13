# Niche expansion niche-expansion-001 — sec-code-model

Runner: `python3 -m factory.niche_expansion.expansion_cycle --subject sec-code-model --cycle-id niche-expansion-001`. Steps 1-6 of PLAN.md section 3 only; adoption (section 4) is the coordinator's sitting.

Verdict: **BORN-STAGED**

## Gate

| slice | model | majority | rule | min per-class recall |
|---|---|---|---|---|
| held-A | 0.9703 (n=101) | 0.1782 | 0.8713 | 0.8333 |
| held-B | 0.9811 (n=106) | 0.1698 | 0.8868 | 0.8824 |

Per-class recall held-A: {'clean': 1.0, 'path-traversal': 0.9444, 'insecure-random': 0.8333, 'unsafe-yaml-load': 1.0, 'tls-verify-off': 1.0, 'ssrf': 1.0}
Per-class recall held-B: {'clean': 0.8824, 'path-traversal': 1.0, 'insecure-random': 1.0, 'unsafe-yaml-load': 1.0, 'tls-verify-off': 1.0, 'ssrf': 1.0}

## Generation (oracle-verified at generation)

- train: 239 kept, drops {'oracle_fired_insecure-random': 1}
- held_a: 107 kept, drops {'oracle_fired_insecure-random': 1}
- held_b: 107 kept, drops {'oracle_fired_insecure-random': 1}

## Contamination filter

- train 213/239 kept; held-A 101/107; held-B 106/107

## Battery BEFORE (through ServingHive)

```
{
 "classify-sec-code": {
  "job": "sec-code-model",
  "right": 0,
  "n": 12,
  "acc": 0.0,
  "bar": 9,
  "detail": "0/12 correct; bar 9/12; gaps: no specialist registered for job 'sec-code-model'"
 }
}
```

Pre-adoption the job is unregistered; the no-specialist result above is the expected BEFORE state, not a failure.

## Methods provenance

dev-split recipe selection on train only (dev n=41): hidden 0 chosen smallest-first within 0.02 of best dev acc 1.0; finalists (hidden 0/4/8) trained on full train (n=213) via executors.retrain_candidates and ranked on held-A; held-B spent once on the winner (hidden 8, 8076 params). Data: three disjoint template partitions, oracle-verified at generation (drops in the generation stats), contamination-filtered against the other partitions and all five existing battery item sets plus this subject's hand-authored battery items.

## Staged model

- coding/swarm/models/sec-code-model.json sha256 b1fead6f44019898fe7019f8d7cc1b0d565dd713d1e2f1a0cbfdf68ff09e69ca
