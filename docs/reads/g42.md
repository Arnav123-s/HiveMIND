# The read of g42

Run [44131701531](https://github.com/Arnav123-s/HiveMIND/actions/runs/44131701531), recorded 2026-11-17 22:16: the body was **kept**. the body grows: after 54 of 64 (easy 31 of 32, hard 23 of 32), before 54 of 64 (easy 31 of 32, hard 23 of 32) on 8 seeds

Written by the record job (`training/reads.py`), with nobody's hand. The rules are those of `docs/DECISIONS.md`.

## The numbers

| What is measured | g42 | g41 (last record) | the body before (same seeds) |
|---|---|---|---|
| Easy kinds passed | 31 of 32 | 32 of 32 | 31 of 32 |
| Hard kinds that have lessons | 18 of 22 | 22 of 25 | 17 of 22 |
| Hard kinds never practised (held out) | 5 of 10 | 4 of 7 | 6 of 10 |
| Right at the first try (practice) | 0.58 (56 of 96) | 0.47 | - |
| Hours for one generation | 5.3 | 5.1 | - |
| Generations recorded with nobody's hand | 1 | 0 | - |

## The chain, by taught hard kind

lessons right by their own check -> rows that fit in training -> loss falls on lessons kept back -> the child alone writes it at the exam -> the body (two agree) passes it.

| kind | lessons right of made | rows left out | kept-back loss before -> after | gap to untaught (points) | child alone right | parent alone right | body right | body before |
|---|---|---|---|---|---|---|---|---|
| a fact from a site and a date sum on it | 13 of 13 | 94 of 414 (estimate) | 0.037 -> 0.005 | +44 | 4 of 4 | - | 4 of 4 | 2 of 4 |
| a join over two small tables | none made | 64 of 108 (estimate) | not measured | not measured | 3 of 3 | - | 3 of 3 | 3 of 3 |
| a log read and counted into a file | 13 of 13 | 1 of 234 (estimate) | 0.489 -> 0.064 | +43 | 3 of 5 | - | 1 of 3 | 0 of 3 |
| a module of two functions, with hidden tests | none made | 46 of 108 (estimate) | 0.314 -> 0.224 | -15 | 2 of 5 | - | 1 of 3 | 3 of 3 |
| a number with given properties | none made | 0 of 18 (estimate) | 0.618 -> 0.533 | -30 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a fact read and a date sum on it | 12 of 12 | 36 of 72 (estimate) | 0.025 -> 0.005 | +35 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| several facts fetched and laid out as a file | none made | not measured | 0.043 -> 0.005 | +45 | - | - | - | - |
| walk a site over several pages | 12 of 12 | 72 of 90 (estimate) | 0.032 -> 0.001 | +52 | 3 of 3 | - | 3 of 3 | 3 of 3 |
| a fact found on the open web | 12 of 12 | 82 of 306 (estimate) | 0.140 -> 0.021 | +41 | 4 of 4 | - | 4 of 4 | 4 of 4 |

- rows left out: an estimate, the slices' records being older than rows_by_kind: by kind, this generation's rows each slice did not study, of those it was given, whether too long, skipped for memory or not reached in time (the slices say only their total too long: 139, 186, 46, 85, 22, 150, 30, 140, 22, 184, 196, 206, 59, 56, 158, 185, 18, 102). Rule 2 counts rows too long only, so it holds on no estimate
- gap: the kind's fall beside the mean fall of the kinds with no lesson this generation (a module of two functions, with hidden tests, a number with given properties, several facts fetched and laid out as a file: 44 points)
- child alone: the answers of this generation's cells (8) in the pulse; parent alone: those of their parents (g34sources, g39code2, g39code3, g39data, g39data2, g39sources, g39words, g39words2) in every arm. Two members sit a task, so these are few
- parent alone: not measured; no parent sat a task of a taught hard kind (the pulse seats the trunk and the newest cells first; the paired gate's before arm seats the body before, parents among it)

![The chain by kind](../progress/chain.svg)

## Hours

| step | minutes |
|---|---|
| practice | 43 |
| dream | 52 |
| gather | 17 |
| plan | 0 |
| train | 213 |
| join | 2 |
| merge | 2 |
| gate | 31 |
| record | 1 |

From the first job to the last: **5.3 hours** (the bar is 5). Each step runs from its first job's start to its last job's end; practice and dream run side by side.

Train slices lost: 2 of 20. Pulse seats whose server died: 0.

Colab: not used (notebook not seen)

## Next piece

next piece: K1: then K2 (wider) and M1 (the talk exam) (rule 6: taught hard kinds 12 of 23, two generations running, for 9 of 9 taught hard kinds: a fact from a site and a date sum on it, a join over two small tables, a log read and counted into a file, a module of two functions, with hidden tests, a number with given properties, a fact read and a date sum on it, several facts fetched and laid out as a file, walk a site over several pages, a fact found on the open web)

| # | the chain shows | holds for |
|---|---|---|
| 1 | lessons right under 8 of 12 | 0 |
| 2 | more than 1 row in 5 of the kind left out | 0 |
| 3 | kept-back gap under 15 points | 2: a module of two functions, with hidden tests, a number with given properties |
| 4 | gap 15 or more, the child alone right more often than its parent, the body not | 0 |
| 5 | gap 15 or more, the child alone not right | 0 |
| 6 | taught hard kinds 12 of 23, two generations running | 9 |

Not measured this generation, so no rule could hold on it: rows left out.
