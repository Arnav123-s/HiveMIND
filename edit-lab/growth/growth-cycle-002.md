# Growth growth-cycle-002 — 2026-11-11 18:36 UTC

Runner: `python3 -m factory.growth_cycle`. Gates: dual pristine held slices (phase-3 held + name-intent held), strict child > parent on both; adoption verified on the served battery + full audit; any regression rolls the births back.

## Births

| target | parent (phase-3 slice) | parent (intent slice) | best child (phase-3) | best child (intent) | verdict |
|---|---|---|---|---|---|
| wrong-operator/expression | 0.8500 (n=20) | 0.6326 (n=694) | 0.9000 | 0.7608 | BORN — bug-wrong-operator-expression-model |

  winning arm: c2-wo-ep1200; child remainder acc 0.5556 (parent 1.0000, informational — routing serves the remainder by the parent)
| off-by-one/index | 0.9500 (n=20) | 0.9566 (n=692) | 1.0000 | 0.9971 | BORN — bug-off-by-one-index-model |

  winning arm: c2-ob-h8-sx2; child remainder acc 0.7778 (parent 0.8889, informational — routing serves the remainder by the parent)

## Served battery (acceptance, Tier-0 sections)

| check | before | after |
|---|---|---|
| classify-secret-line | 0.8333 | 0.8333 |
| classify-error-class | 1.0 | 1.0 |
| classify-commit-type | 1.0 | 1.0 |
| classify-contract-judgment | 0.9167 | 0.9167 |
| classify-gap-move | 1.0 | 1.0 |
| bug-pattern-composed-sealed-v2 | 0.8333 | 0.8333 |
| classify-secret-line-ternary | 0.9167 | 0.9167 |
| tiny-hive-ops | 1.0 | 1.0 |

Overall (Tier-0 sections): 0.9375 -> 0.9375

Full audit after cycle: OK (0 failure(s))

## Learned say (measured, not adopted)

Composed acc on the phase-3 held set by margin rule: {'routed': 0.8276, 'mean': 0.7931, 'learned': 0.7931} (fit on train; judged on a spent surface — see cycle JSON for weights and the adoption note).

## Harvest (parents' measured failures, training-side)

- wrong-operator/expression on phase3_train_slice: acc 1.0 (n=32, 0 wrong)
- wrong-operator/expression on intent_train_slice: acc 0.6803 (n=757, 242 wrong); wrong by intent: {'remainder': 76, 'quotient': 17, 'difference': 16, 'product': 22, 'sum_pair': 54, 'max_of': 19, 'min_of': 18, 'minutes': 6, 'average_pair': 6, 'element_at': 6, 'average_list': 2}
- off-by-one/index on phase3_train_slice: acc 1.0 (n=41, 0 wrong)
- off-by-one/index on intent_train_slice: acc 0.9115 (n=757, 67 wrong); wrong by intent: {'max_of': 5, 'min_of': 3, 'first_two': 12, 'last_element': 6, 'first_k': 13, 'element_at': 14, 'last_two': 14}

## Next

Cycle 3 attacks, in order: (1) whichever dual-gate bar each target's cycle-2 per-config table shows still binding — if a single phase-3 held item (n=20 slice) is the whole blocker for a target, the honest fix is a LARGER pristine phase-3-style held slice (new template families, disjoint names/idioms), not more candidates against the same 20 items; (2) a second name-intent partition (comparison/accumulator intents) so the intent judge is not a fixed surface the grid can overfit; (3) the learned-say adoption step IF cycle 2's v2 fit beat the routed rule. Learned-say v2 (joint fit on the composed objective): held routed 0.8276, mean 0.7931, learned 0.7931. It does not beat the routed rule — the learned-say question is closed unless the representation set itself changes. Runner readiness for a recurring ~6h cron: the cycle runs end to end non-interactively (one command, md+json+ledger written, rollback automatic on any serving regression) — the mechanics are ready. Four changes are needed before scheduling it: (1) cycle-id auto-increment from the ledger (today it is a CLI argument); (2) a single-instance lock + a lab-busy check (this VM runs one heavy job at a time; a cron cycle must skip, not collide, when another lab job is training); (3) per-cycle novelty — training is deterministic, so re-running a fixed grid reproduces the same candidates exactly; a cron'd cycle must rotate its grid or grow its data partitions keyed by cycle number, or it will spend compute re-proving cycle 2 forever; (4) an alert path on rollback or audit failure (today that is only a ledger line). With (1)-(4) it can be scheduled; without (3) it should not be.

## Cycle-2 outcome addendum (post-run, supersedes the generic Next text where they differ)

Both targets were born in their FIRST variant; the raised-cap and slice-repeat fallback variants never ran. The binding constraint has moved: the served headline numbers did NOT move (battery overall 0.9375 -> 0.9375; served sealed 0.8333 -> 0.8333) — the waking-dream layer was already compensating on the served surface. What improved is the raw composition underneath: sealed raw composed 0.4444 -> 0.5278, with sealed raw per-class recalls still weak (wrong-operator 0.40, off-by-one 0.3333, swapped-operands 0.0, clean 0.6364). Cycle 3's real target is therefore the sealed/served gap and the slices still routed "whole" (wrong-operator: accumulator, comparison; off-by-one: range), judged on a LARGER pristine held slice — both cycle-2 births were decided on an n=20 phase-3 slice (off-by-one's win is corroborated by three independent candidates at 1.0000, but the surface is small). Learned-say is closed: the v2 joint fit also failed to beat the routed rule (0.7931 vs 0.8276).
