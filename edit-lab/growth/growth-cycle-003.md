# Growth growth-cycle-003 — 2026-11-12 00:50 UTC

Runner: `python3 -m factory.growth_cycle`. Gates: dual pristine held slices (phase-3 held + name-intent held), strict child > parent on both; adoption verified on the served battery + full audit; any regression rolls the births back.

## Births

| target | parent (phase-3 slice) | parent (intent slice) | best child (phase-3) | best child (intent) | verdict |
|---|---|---|---|---|---|
| wrong-operator/expression | 0.8500 (n=20) | 0.6326 (n=694) | 0.9000 | 0.7680 | BORN — bug-wrong-operator-expression-model |

  winning arm: init; child remainder acc 0.7778 (parent 1.0000, informational — routing serves the remainder by the parent)
| off-by-one/index | 0.9500 (n=20) | 0.9566 (n=692) | 0.9500 | 0.9957 | no birth |

  gate record: gate failed: no candidate beat the parent on both held slices (phase-3 slice: parent 0.95, best child 0.95; name-intent slice: parent 0.9566, best child 0.9957) — no birth

## Served battery (acceptance, Tier-0 sections)

| check | before | after |
|---|---|---|
| classify-secret-line | 0.8333 | 0.8333 |
| classify-error-class | 1.0 | 1.0 |
| classify-commit-type | 1.0 | 1.0 |
| classify-contract-judgment | 0.9167 | 0.9167 |
| classify-gap-move | 1.0 | 1.0 |
| bug-pattern-composed-sealed-v2 | 0.8333 | 0.8611 |
| classify-secret-line-ternary | 0.9167 | 0.9167 |
| tiny-hive-ops | 1.0 | 1.0 |

Overall (Tier-0 sections): 0.9375 -> 0.941

Full audit after cycle: OK (0 failure(s))

## Learned say (measured, not adopted)

Composed acc on the phase-3 held set by margin rule: {'routed': 0.8621, 'mean': 0.7931, 'learned': 0.7931} (fit on train; judged on a spent surface — see cycle JSON for weights and the adoption note).

## Harvest (parents' measured failures, training-side)

- wrong-operator/expression on phase3_train_slice: acc 1.0 (n=32, 0 wrong)
- wrong-operator/expression on intent_train_slice: acc 0.6803 (n=757, 242 wrong); wrong by intent: {'remainder': 76, 'quotient': 17, 'difference': 16, 'product': 22, 'sum_pair': 54, 'max_of': 19, 'min_of': 18, 'minutes': 6, 'average_pair': 6, 'element_at': 6, 'average_list': 2}
- off-by-one/index on phase3_train_slice: acc 1.0 (n=41, 0 wrong)
- off-by-one/index on intent_train_slice: acc 0.9115 (n=757, 67 wrong); wrong by intent: {'max_of': 5, 'min_of': 3, 'first_two': 12, 'last_element': 6, 'first_k': 13, 'element_at': 14, 'last_two': 14}

## Novelty rotation (cron mode)

Keyed by cycle number 3: intent-cap sampling seed 23856, dream-pool band counts {1: 30, 2: 30, 3: 34}, grid seed 594006318. keyed by cycle number: intent-cap sampling seed + dream-pool band counts + seeded transforms of the candidate grid (epoch ladder steps, mixture leans, curriculum leans, occasional hidden-size changes). Legacy invocations (explicit --cycle-id, no --rotate) skip all of it and reproduce the cycle-1/2 grids and seeds exactly.

## Next

Extend the loop: the remaining slices from the intake scan, the learned-say adoption step under its own battery gate, and a second name-intent partition (comparison/accumulator slices) so growth is not a one-cycle event.
