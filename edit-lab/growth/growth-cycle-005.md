# Growth growth-cycle-005 — 2026-11-12 12:50 UTC

Runner: `python3 -m factory.growth_cycle`. Gates: dual pristine held slices (phase-3 held + name-intent held), strict child > parent on both; adoption verified on the served battery + full audit; any regression rolls the births back.

## Births

| target | parent (phase-3 slice) | parent (intent slice) | best child (phase-3) | best child (intent) | verdict |
|---|---|---|---|---|---|
| wrong-operator/expression | 0.8500 (n=20) | 0.6326 (n=694) | 1.0000 | 0.7651 | BORN — bug-wrong-operator-expression-model |

  winning arm: scratch; child remainder acc 0.6667 (parent 1.0000, informational — routing serves the remainder by the parent)
| off-by-one/index | 0.9500 (n=20) | 0.9566 (n=692) | 1.0000 | 1.0000 | BORN — bug-off-by-one-index-model |

  winning arm: init; child remainder acc 0.6667 (parent 0.8889, informational — routing serves the remainder by the parent)

## Methods provenance (cycle-3 arms)

### wrong-operator/expression
- Recipe head-to-head (budget 120 epochs, dev split of TRAIN data, dev n=108): scratch-text-h4 dev 0.8519; init-lr03 dev 0.7963; init-lr10 dev 0.7778 -> winner scratch-text-h4 (dev 0.8519). Held slices never used for this choice.
- Breadth edit: probe 300 epochs from parent; thin candidate = alpha 0.3 of the probe delta on EVERY weight group; concentrated control = full delta on 'w' only (largest |delta| 372.3428).
- Dream-first repair (improvised): dream pool 544 -> 170 clean -> slice 78 -> difficulty filter kept 21 (13 the parent got wrong); repaired parent on 307 items (200 epochs), children seeded from it.

### off-by-one/index
- Recipe head-to-head (budget 120 epochs, dev split of TRAIN data, dev n=122): scratch-text-h4 dev 0.9836; init-lr03 dev 0.9590; init-lr10 dev 0.9672 -> winner scratch-text-h4 (dev 0.9836). Held slices never used for this choice.
- Breadth edit: probe 300 epochs from parent; thin candidate = alpha 0.3 of the probe delta on EVERY weight group; concentrated control = full delta on 'w' only (largest |delta| 283.498).
- Dream-first repair (improvised): dream pool 544 -> 170 clean -> slice 170 -> difficulty filter kept 29 (27 the parent got wrong); repaired parent on 307 items (200 epochs), children seeded from it.


## Served battery (acceptance, Tier-0 sections)

| check | before | after |
|---|---|---|
| classify-secret-line | 0.8333 | 0.8333 |
| classify-error-class | 1.0 | 1.0 |
| classify-commit-type | 1.0 | 1.0 |
| classify-contract-judgment | 0.9167 | 0.9167 |
| classify-gap-move | 1.0 | 1.0 |
| bug-pattern-composed-sealed-v2 | 0.8611 | 0.8611 |
| classify-secret-line-ternary | 0.9167 | 0.9167 |
| tiny-hive-ops | 1.0 | 1.0 |

Overall (Tier-0 sections): 0.941 -> 0.941

Full audit after cycle: OK (0 failure(s))

## Learned say (measured, not adopted)

Composed acc on the phase-3 held set by margin rule: {'routed': 0.8621, 'mean': 0.7931, 'learned': 0.7931} (fit on train; judged on a spent surface — see cycle JSON for weights and the adoption note).

## Harvest (parents' measured failures, training-side)

- wrong-operator/expression on phase3_train_slice: acc 1.0 (n=32, 0 wrong)
- wrong-operator/expression on intent_train_slice: acc 0.6803 (n=757, 242 wrong); wrong by intent: {'remainder': 76, 'quotient': 17, 'difference': 16, 'product': 22, 'sum_pair': 54, 'max_of': 19, 'min_of': 18, 'minutes': 6, 'average_pair': 6, 'element_at': 6, 'average_list': 2}
- off-by-one/index on phase3_train_slice: acc 1.0 (n=41, 0 wrong)
- off-by-one/index on intent_train_slice: acc 0.9115 (n=757, 67 wrong); wrong by intent: {'max_of': 5, 'min_of': 3, 'first_two': 12, 'last_element': 6, 'first_k': 13, 'element_at': 14, 'last_two': 14}

## Novelty rotation (cron mode)

Keyed by cycle number 5: intent-cap sampling seed 39694, dream-pool band counts {1: 38, 2: 26, 3: 30}, grid seed 581537310. keyed by cycle number: intent-cap sampling seed + dream-pool band counts + seeded transforms of the candidate grid (epoch ladder steps, mixture leans, curriculum leans, occasional hidden-size changes). Legacy invocations (explicit --cycle-id, no --rotate) skip all of it and reproduce the cycle-1/2 grids and seeds exactly.

## Next

First cycle under the methods upgrade: read the per-candidate table — which arm (recipe / breadth / concentrated / dream-first vs the standing scratch+init grid) produced each target's best dual-gate candidate names where the next cycle pushes. An arm that never produces a competitive candidate across both targets is dropped from the grid rather than re-proved forever; a winning recipe becomes the next cycle's declared default candidate shape. The accumulator/comparison/range surfaces sealed for the earlier plan remain available when a target's binding bar is judge size, not candidate quality.
