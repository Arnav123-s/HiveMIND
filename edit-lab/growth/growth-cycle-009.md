# Growth growth-cycle-009 — 2026-11-13 18:50 UTC

Runner: `python3 -m factory.growth_cycle`. Gates: dual pristine held slices (phase-3 held + name-intent held), strict child > parent on both; then Gate 3′ — the full serving path on the say_dev pool (composer + waking-dream refresh), child vs parent, blocking on any served total fall or a >=1-item served clean-recall fall; adoption verified on the served battery + full audit; any regression rolls the births back.

## Births

| target | parent (phase-3 slice) | parent (intent slice) | best child (phase-3) | best child (intent) | verdict |
|---|---|---|---|---|---|
| wrong-operator/expression | 0.8500 (n=20) | 0.6326 (n=694) | 1.0000 | 0.7795 | BORN — bug-wrong-operator-expression-model — REMOVED at serving verification |

  winning arm: scratch; child remainder acc 0.6667 (parent 1.0000, informational — routing serves the remainder by the parent)
| off-by-one/index | 0.9500 (n=20) | 0.9566 (n=692) | 1.0000 | 0.9957 | no birth |

  gate record: Gate 3′ blocked the birth (the dual pristine gate had passed): serving-dev total fell 135/216 (0.625) -> 133/216 (0.6157). Serving state untouched — the child model file and composer config were restored from pre-attempt byte snapshots before any registry rewrite; no rollback was involved.

## Methods provenance (cycle-3 arms)

### wrong-operator/expression
- Recipe head-to-head (budget 120 epochs, dev split of TRAIN data, dev n=97): scratch-text-h4 dev 0.8454; init-lr03 dev 0.7526; init-lr10 dev 0.7732 -> winner scratch-text-h4 (dev 0.8454). Held slices never used for this choice.
- Breadth edit: probe 300 epochs from parent; thin candidate = alpha 0.3 of the probe delta on EVERY weight group; concentrated control = full delta on 'w' only (largest |delta| 377.8262).
- Dream-first repair (improvised): dream pool 570 -> 202 clean -> slice 78 -> difficulty filter kept 21 (14 the parent got wrong); repaired parent on 271 items (200 epochs), children seeded from it.
- Champion recipe: skipped — not this cycle's designated champion target

### off-by-one/index
- Recipe head-to-head (budget 120 epochs, dev split of TRAIN data, dev n=118): scratch-text-h4 dev 0.9831; init-lr03 dev 0.9831; init-lr10 dev 1.0000 -> winner init-lr10 (dev 1.0000). Held slices never used for this choice.
- Breadth edit: probe 300 epochs from parent; thin candidate = alpha 0.3 of the probe delta on EVERY weight group; concentrated control = full delta on 'w' only (largest |delta| 268.5342).
- Dream-first repair (improvised): dream pool 570 -> 202 clean -> slice 202 -> difficulty filter kept 48 (46 the parent got wrong); repaired parent on 326 items (200 epochs), children seeded from it.
- Champion recipe v1 (Build 1): one-gene mutant (epochs: 800 -> 300); dev champion 1.0000 vs mutant 0.9915 (margin -0.0085); mutant born: False. A crown lands only if the birth is kept after verification.


## Champion recipe (Build 1)

Designated target: off-by-one/index; record v1; crowns applied: 0 — no crowns: the cycle rolled back — a rolled-back birth can never crown a recipe

## Served battery (acceptance, Tier-0 sections)

| check | before | after |
|---|---|---|
| classify-secret-line | 0.8333 | 0.8333 |
| classify-error-class | 1.0 | 1.0 |
| classify-commit-type | 1.0 | 1.0 |
| classify-contract-judgment | 0.9167 | 0.9167 |
| classify-gap-move | 1.0 | 1.0 |
| bug-pattern-composed-sealed-v2 | 0.8611 | 0.8333 |
| classify-secret-line-ternary | 0.9167 | 0.9167 |
| tiny-hive-ops | 1.0 | 1.0 |

Overall (Tier-0 sections): 0.941 -> 0.9375

Full audit after cycle: OK (0 failure(s))

## Learned say (measured, not adopted)

Composed acc on the phase-3 held set by margin rule: {'routed': 0.8276, 'mean': 0.7931, 'learned': 0.7931} (fit on train; judged on a spent surface — see cycle JSON for weights and the adoption note).

## Harvest (parents' measured failures, training-side)

- wrong-operator/expression on phase3_train_slice: acc 1.0 (n=32, 0 wrong)
- wrong-operator/expression on intent_train_slice: acc 0.6803 (n=757, 242 wrong); wrong by intent: {'remainder': 76, 'quotient': 17, 'difference': 16, 'product': 22, 'sum_pair': 54, 'max_of': 19, 'min_of': 18, 'minutes': 6, 'average_pair': 6, 'element_at': 6, 'average_list': 2}
- off-by-one/index on phase3_train_slice: acc 1.0 (n=41, 0 wrong)
- off-by-one/index on intent_train_slice: acc 0.9115 (n=757, 67 wrong); wrong by intent: {'max_of': 5, 'min_of': 3, 'first_two': 12, 'last_element': 6, 'first_k': 13, 'element_at': 14, 'last_two': 14}

## ROLLED BACK

serving verification failed: bug-pattern-composed-sealed-v2: 0.8611 -> 0.8333; audit failures: [{'artifact': 'bug-pattern-composed:sealed-baseline', 'failure': 'score drift: measured 0.5278 vs recorded 0.5'}]

## Novelty rotation (cron mode)

Keyed by cycle number 9: intent-cap sampling seed 71370, dream-pool band counts {1: 30, 2: 30, 3: 34}, grid seed 345446011. keyed by cycle number: intent-cap sampling seed + dream-pool band counts + seeded transforms of the candidate grid (epoch ladder steps, mixture leans, curriculum leans, occasional hidden-size changes). Legacy invocations (explicit --cycle-id, no --rotate) skip all of it and reproduce the cycle-1/2 grids and seeds exactly.

## Next

First cycle under the methods upgrade: read the per-candidate table — which arm (recipe / breadth / concentrated / dream-first vs the standing scratch+init grid) produced each target's best dual-gate candidate names where the next cycle pushes. An arm that never produces a competitive candidate across both targets is dropped from the grid rather than re-proved forever; a winning recipe becomes the next cycle's declared default candidate shape. The accumulator/comparison/range surfaces sealed for the earlier plan remain available when a target's binding bar is judge size, not candidate quality.
