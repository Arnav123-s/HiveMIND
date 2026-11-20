# An eight-cell archive of candidate heads

The archive found three behavior niches and kept three existing heads. Its runnable router answered **10/15** terminal questions, exactly matching the bare body and the best single development head. One retained head could answer an additional water question, but the router selected a different head. The archive's **11/15** hindsight ceiling therefore did not become an answer for a user.

| Retention policy | Deployed heads | Earlier checks /9 | Supplementary /6 | Total /15 | Hindsight ceiling /15 |
|---|---:|---:|---:|---:|---:|
| Bare body | 1 | 8.00 | 2.00 | 10.00 | 10.00 |
| Highest development score | 1 | 8.00 | 2.00 | 10.00 | 10.00 |
| Final proposal only | 1 | 8.00 | 2.33 | 10.33 | 10.33 |
| MAP-Elites archive | 3 | 8.00 | 2.00 | 10.00 | 11.00 |
| Random size-matched archive | 3 | 7.90 | 2.33 | 10.23 | 11.27 |

Means use the same 15 terminal questions in all 12 search streams. Random retention uses five fixed draws from each stream. None of these repeated routes constitute additional independent test questions. The last proposal scored 11 in four streams and 10 in eight. Random routing scored 10 in 50 selections, 11 in six and 12 in four. [Terminal choices and paired gains/losses](results.json)

## Search and deployment

Every search evaluated the bare model, one pooled head and six existing fitted specialist heads. It then fitted 24 broad proposals from equal-sized, class-balanced training subsets using real 4,096-component Ternary-Bonsai-8B endpoint states. Each of three behavior bits records whether a head changes at least one third of the development token IDs within a particular domain pair. Each occupied cell retains the highest development scorer seen there, keeping the earlier arrival on a tie. Only the current champions can supply a parent for later exploration. The archived audit records all candidates for the matched single, last and random comparisons. This is conditional on the same proposal stream; a different parent-selection algorithm could generate different proposals. [Protocol](protocol.md) · [Candidate lineage and weights digests](frozen-plan.json)

The original bare, pooled and conversation heads occupied three cells. They scored 11, 11 and 12 out of 15 during development. No later broad proposal entered an empty cell or improved on the incumbent in its own cell. All 288 proposal slots across streams corresponded to 148 unique fitted weight arrays. At deployment, a nearest-centroid model inferred the domain directly from the input's frozen features. It inferred all 15 terminal domains correctly. The decision table learned on development still assigned the same conversation head to every inferred domain, losing the one useful contribution from another retained head. The oracle used terminal correctness to see which retained member could answer each case; the executable routing policy never accessed those labels.

| Exploratory lineages | Factor noise | Archive /15 | Final proposal /15 | Mean random archive /15 | Occupied cells |
|---:|---:|---:|---:|---:|---:|
| 1 | 0% | 10.00 | 10.33 | 10.27 | 3 |
| 1 | 5% | 10.00 | 10.33 | 10.20 | 3 |
| 2 | 0% | 10.00 | 10.33 | 10.27 | 3 |
| 2 | 5% | 10.00 | 10.33 | 10.20 | 3 |

Each arm made 24 proposals, used 18 teaching cases per proposal, and checked 32 candidate heads on the same 15 development cases. The two-lineage setting gave each lane an independent bare start, then admitted parents only from its surviving champions, falling back to the shared archive. When no new contestant survived, further candidates descended from the starting champions. The experiment therefore supplies no positive evidence for persistent cooperating explorers. Gaussian perturbations at 5% of the input factor's Frobenius norm gave no archive gain. There was no new task generation, noise sweep, physics experiment, G41 evaluation or evidence of stochastic resonance.

## Reproduce the freeze and score

The 60 training cases, 15 development cases and 15 terminal cases were disjoint. The terminal questions had been published and used in previous studies. The new search never consulted terminal correctness before its candidate weight hashes, archive membership, parents, and all deployable routing decisions were frozen. The two-phase runner rejects any mismatch before opening terminal scoring. Reproduction requires NumPy and the checked-in island feature cache. Development took 3.625 single-thread process CPU seconds in the recorded run. No live 8B process was started. [Prior native token calibration](../islands/calibration.json)

```sh
python training/experiments/atlas/archive/experiment.py prepare --plan /tmp/hive-archive-plan.json
python training/experiments/atlas/archive/experiment.py score --plan /tmp/hive-archive-plan.json --out /tmp/hive-archive-results.json
```

The plan SHA-256 was `73fe071243489e6375e9c99215a24cee73c6db1fa74f20df9da2f0ee4e58e184`. [Experiment source](experiment.py)
