# Niche expansion niche-expansion-002 — data-format-model

Runner: `python3 -m factory.niche_expansion.expansion_cycle --subject data-format-model --cycle-id niche-expansion-002`. Steps 1-6 of PLAN.md section 3 only; adoption (section 4) is the coordinator's sitting.

Verdict: **REJECTED**

## Gate

| slice | model | majority | rule | min per-class recall |
|---|---|---|---|---|
| held-A | 0.8778 (n=90) | 0.2 | 0.7333 | 0.6111 |
| held-B | 0.8444 (n=90) | 0.2 | 0.7333 | 0.6667 |

Per-class recall held-A: {'json': 0.8889, 'malformed-json': 0.6111, 'csv': 0.8889, 'toml': 1.0, 'plain-text': 1.0}
Per-class recall held-B: {'json': 0.8889, 'malformed-json': 0.6667, 'csv': 0.6667, 'toml': 1.0, 'plain-text': 1.0}

## Generation (oracle-verified at generation)

- train: 300 kept, drops {}
- held_a: 90 kept, drops {}
- held_b: 90 kept, drops {}

## Contamination filter

- train 300/300 kept; held-A 90/90; held-B 90/90

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

dev-split recipe selection on train only (dev n=60): hidden 0 chosen smallest-first within 0.02 of best dev acc 0.9167; finalists (hidden 0/4/8) trained on full train (n=300) via executors.retrain_candidates and ranked on held-A; held-B spent once on the winner (hidden 8, 7733 params). Data: three disjoint template partitions, oracle-verified at generation (drops in the generation stats), contamination-filtered against the other partitions and all five existing battery item sets plus this subject's hand-authored battery items.

## Attempt history (builder note, appended after the run)

- Attempt 1 (record preserved as niche-expansion-002-attempt1-rejected.json): held-A 0.6667 / held-B 0.6000, csv recall 0.0, json recall 0.3333. REJECTED. Design flaw found: formatting style was partition-exclusive (train JSON pretty-printed, held JSON compact — "compact" became a malformed cue) and each partition had a single CSV theme / key vocabulary, so held items' unseen words left the shape signal too thin.
- Fix applied to gen_data_format.py: three internal key-sets / CSV themes / TOML styles / plain topics per partition (still disjoint across partitions); JSON formatting (compact / indented / spaced) rotates by variant in every partition and band for valid and malformed items alike; train partition enlarged to 300 items.
- Attempt 3 (diagnostic only, never an official run): exact valid/malformed contrast pairs — hurt (malformed recall fell; the shared base's features drowned the fault's). Reverted before this attempt-2 run; malformed items use the json family's shapes at a shifted variant.
- Attempt 2 (this record): held-A 0.8778 / held-B 0.8444, both above both baselines, but malformed-json recall 0.6111 / 0.6667 < 0.80 and both accuracies < 0.90. REJECTED — the binding failure is valid-vs-malformed JSON discrimination across disjoint vocabularies under a bag-of-trigrams featurizer. No model file was written.
