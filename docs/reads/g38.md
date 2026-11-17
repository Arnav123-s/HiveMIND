# The read of g38

Run [43950235200](https://github.com/Arnav123-s/HiveMIND/actions/runs/43950235200), recorded 2026-11-17 04:20: the body was **kept**. the body grows; its pulse: 35 of 64 with its children

Written by the record job (`training/reads.py`), with nobody's hand. The rules are those of `docs/DECISIONS.md`.

## The numbers

| What is measured | g38 | g34 (last record) | the body before (same seeds) |
|---|---|---|---|
| Easy kinds passed | 25 of 32 | 31 of 32 | - |
| Hard kinds that have lessons | 7 of 25 | 5 of 23 | - |
| Hard kinds never practised (held out) | 3 of 7 | 1 of 9 | - |
| Right at the first try (practice) | 0.25 (35 of 142) | - | - |
| Hours for one generation | 7.9 | - | - |
| Generations recorded with nobody's hand | 0 | 0 | - |

## The chain, by taught hard kind

lessons right by their own check -> rows that fit in training -> loss falls on lessons kept back -> the child alone writes it at the exam -> the body (two agree) passes it.

| kind | lessons right of made | rows left out | kept-back loss before -> after | gap to untaught (points) | child alone right | parent alone right | body right | body before |
|---|---|---|---|---|---|---|---|---|
| a fact from a site and a date sum on it | 14 of 14 | 0 of 272 | not measured | not measured | 1 of 2 | - | 0 of 1 | - |
| a join over two small tables | none made | 65 of 119 | not measured | not measured | 1 of 1 | - | 1 of 1 | - |
| a log read and counted into a file | 13 of 13 | 237 of 238 | not measured | not measured | 0 of 2 | - | 0 of 1 | - |
| a module of two functions, with hidden tests | 12 of 12 | 76 of 306 | not measured | not measured | 2 of 12 | - | 2 of 7 | - |
| a number with given properties | 12 of 12 | 8 of 255 | not measured | not measured | 1 of 1 | - | 1 of 1 | - |
| a fact read and a date sum on it | 9 of 9 | 0 of 153 | not measured | not measured | 5 of 6 | - | 1 of 3 | - |
| several facts fetched and laid out as a file | 12 of 12 | 0 of 204 | not measured | not measured | 4 of 5 | - | 2 of 4 | - |
| walk a site over several pages | 6 of 6 | 0 of 102 | not measured | not measured | 5 of 10 | - | 0 of 5 | - |
| a fact found on the open web | 11 of 11 | 0 of 187 | not measured | not measured | 1 of 4 | - | 0 of 2 | - |

- lessons: gather printed no count by kind this generation; the right ones are counted from the lesson rows (rows with the same exchange are kept once, so this is at least), the failed ones from its dropped list
- rows left out: by kind, this generation's rows each slice did not study, of those it was given (the slices say only their total too long: 112, 26, 33, 25, 105, 28, 107, 99, 99, 27, 108, 104, 27, 108, 24, 26, 24)
- kept-back loss: no slice's record has lessons kept back (training/grow.py kept_back, from generation 39)
- child alone: the answers of this generation's cells (8) in the pulse; parent alone: those of their parents (g24code, g24data, g27code, g27sources, g27words, g28code, g28data, g28words) in every arm. Two members sit a task, so these are few
- parent alone: not measured; no parent sat a task of a taught hard kind (the pulse seats the trunk and the newest cells first; the paired gate's before arm seats the body before, parents among it)

![The chain by kind](../progress/chain.svg)

## Hours

| step | minutes |
|---|---|
| practice | 134 |
| gather | 13 |
| plan | 0 |
| train | 236 |
| join | 2 |
| merge | 2 |
| gate | 84 |
| record | 1 |

From the first job to the last: **7.86 hours** (the bar is 5). Each step runs from its first job's start to its last job's end; practice and dream run side by side.

Train slices lost: 7 of 24. Pulse seats whose server died: 0.

## Next piece

next piece: T4: shorter lessons (rule 2: more than 1 row in 5 of the kind left out, for 3 of 9 taught hard kinds: a join over two small tables, a log read and counted into a file, a module of two functions, with hidden tests)

| # | the chain shows | holds for |
|---|---|---|
| 1 | lessons right under 8 of 12 | 0 |
| 2 | more than 1 row in 5 of the kind left out | 3: a join over two small tables, a log read and counted into a file, a module of two functions, with hidden tests |
| 3 | kept-back gap under 15 points | 0 |
| 4 | gap 15 or more, the child alone right more often than its parent, the body not | 0 |
| 5 | gap 15 or more, the child alone not right | 0 |
| 6 | taught hard kinds 12 of 23, two generations running | 0 |

Not measured this generation, so no rule could hold on it: kept-back gap.
