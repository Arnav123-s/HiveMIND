# Growth growth-cycle-001 — 2026-11-11 17:27 UTC

Runner: `python3 -m factory.growth_cycle`. Gates: dual pristine held slices (phase-3 held + name-intent held), strict child > parent on both; adoption verified on the served battery + full audit; any regression rolls the births back.

## Births

| target | parent (phase-3 slice) | parent (intent slice) | best child (phase-3) | best child (intent) | verdict |
|---|---|---|---|---|---|
| wrong-operator/expression | 0.8500 (n=20) | 0.6326 (n=694) | 0.9000 | 0.7882 | no birth |

  gate record: gate failed: no candidate beat the parent on both held slices (phase-3 slice: parent 0.85, best child 0.9; name-intent slice: parent 0.6326, best child 0.7882) — no birth
| off-by-one/index | 0.9500 (n=20) | 0.9566 (n=692) | 0.9500 | 0.9971 | no birth |

  gate record: gate failed: no candidate beat the parent on both held slices (phase-3 slice: parent 0.95, best child 0.95; name-intent slice: parent 0.9566, best child 0.9971) — no birth

## Served battery (acceptance, Tier-0 sections)

| check | before | after |
|---|---|---|
| classify-secret-line | 0.8333 | — |
| classify-error-class | 1.0 | — |
| classify-commit-type | 1.0 | — |
| classify-contract-judgment | 0.9167 | — |
| classify-gap-move | 1.0 | — |
| bug-pattern-composed-sealed-v2 | 0.8333 | — |
| classify-secret-line-ternary | 0.9167 | — |
| tiny-hive-ops | 1.0 | — |

Overall (Tier-0 sections): 0.9375 (unchanged — no adoption)

Full audit after cycle: OK (0 failure(s))

## Learned say (measured, not adopted)

Composed acc on the phase-3 held set by margin rule: {'routed': 0.8276, 'mean': 0.7931, 'learned': 0.7931} (fit on train; judged on a spent surface — see cycle JSON for weights and the adoption note).

## Harvest (parents' measured failures, training-side)

- wrong-operator/expression on phase3_train_slice: acc 1.0 (n=32, 0 wrong)
- wrong-operator/expression on intent_train_slice: acc 0.6803 (n=757, 242 wrong); wrong by intent: {'remainder': 76, 'quotient': 17, 'difference': 16, 'product': 22, 'sum_pair': 54, 'max_of': 19, 'min_of': 18, 'minutes': 6, 'average_pair': 6, 'element_at': 6, 'average_list': 2}
- off-by-one/index on phase3_train_slice: acc 1.0 (n=41, 0 wrong)
- off-by-one/index on intent_train_slice: acc 0.9115 (n=757, 67 wrong); wrong by intent: {'max_of': 5, 'min_of': 3, 'first_two': 12, 'last_element': 6, 'first_k': 13, 'element_at': 14, 'last_two': 14}

## Next

No birth under the dual gate. Read the per-config table in the cycle JSON: whichever gate each best candidate failed names cycle 2's target (intent-slice supply quality vs template-slice capacity), plus the learned-say adoption step if its held margin holds.
