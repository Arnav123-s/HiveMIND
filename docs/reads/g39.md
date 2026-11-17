# The read of g39

Run [44024307514](https://github.com/Arnav123-s/HiveMIND/actions/runs/44024307514), recorded 2026-11-17 10:37: the body was **kept**. the body grows: after 38 of 64 (easy 26 of 32, hard 12 of 32), before 36 of 64 (easy 26 of 32, hard 10 of 32) on 8 seeds

Written by the record job (`training/reads.py`), with nobody's hand. The rules are those of `docs/DECISIONS.md`.

## The numbers

| What is measured | g39 | g38 (last record) | the body before (same seeds) |
|---|---|---|---|
| Easy kinds passed | 26 of 32 | 25 of 32 | 26 of 32 |
| Hard kinds that have lessons | 7 of 22 | 7 of 25 | 6 of 22 |
| Hard kinds never practised (held out) | 5 of 10 | 3 of 7 | 4 of 10 |
| Right at the first try (practice) | 0.39 (37 of 96) | - | - |
| Hours for one generation | 4.9 | - | - |
| Generations recorded with nobody's hand | 0 | 0 | - |

## The chain, by taught hard kind

lessons right by their own check -> rows that fit in training -> loss falls on lessons kept back -> the child alone writes it at the exam -> the body (two agree) passes it.

| kind | lessons right of made | rows left out | kept-back loss before -> after | gap to untaught (points) | child alone right | parent alone right | body right | body before |
|---|---|---|---|---|---|---|---|---|
| a fact from a site and a date sum on it | 13 of 13 | 30 of 240 | 1.157 -> 0.156 | +70 | 3 of 6 | - | 0 of 3 | 0 of 3 |
| a join over two small tables | none made | 94 of 105 | not measured | not measured | 2 of 2 | - | 2 of 2 | 2 of 2 |
| a log read and counted into a file | 12 of 12 | 180 of 180 | not measured | not measured | 0 of 4 | - | 0 of 2 | 0 of 2 |
| a module of two functions, with hidden tests | 15 of 15 | 90 of 255 | 0.794 -> 0.148 | +65 | 3 of 9 | - | 3 of 6 | 3 of 6 |
| a number with given properties | none made | not measured | 0.830 -> 0.692 | +0 | 2 of 3 | - | 2 of 2 | 1 of 2 |
| a fact read and a date sum on it | 12 of 12 | 0 of 75 | 0.972 -> 0.097 | +74 | 2 of 6 | - | 0 of 3 | 0 of 3 |
| several facts fetched and laid out as a file | 13 of 13 | 30 of 240 | 0.901 -> 0.112 | +71 | - | - | - | - |
| walk a site over several pages | 13 of 13 | 0 of 75 | 1.237 -> 0.171 | +70 | 1 of 2 | - | 0 of 1 | 0 of 1 |
| a fact found on the open web | 12 of 12 | 0 of 180 | 1.776 -> 0.380 | +62 | 0 of 6 | - | 0 of 3 | 0 of 3 |

- rows left out: by kind, this generation's rows each slice did not study, of those it was given (the slices say only their total too long: 57, 141, 37, 127, 124, 118, 119, 115, 111, 49, 43, 64, 155, 49, 43)
- gap: the kind's fall beside the mean fall of the kinds with no lesson this generation (a number with given properties: 17 points)
- child alone: the answers of this generation's cells (8) in the pulse; parent alone: those of their parents (g24code, g24data, g27code, g27sources, g27words, g28code, g28data, g28words) in every arm. Two members sit a task, so these are few

![The chain by kind](../progress/chain.svg)

## Hours

| step | minutes |
|---|---|
| practice | 58 |
| gather | 12 |
| plan | 0 |
| train | 175 |
| join | 2 |
| merge | 2 |
| gate | 44 |
| record | 1 |

From the first job to the last: **4.91 hours** (the bar is 5). Each step runs from its first job's start to its last job's end; practice and dream run side by side.

Train slices lost: 5 of 20. Pulse seats whose server died: 0.

## Next piece

next piece: T4: shorter lessons (rule 2: more than 1 row in 5 of the kind left out, for 3 of 9 taught hard kinds: a join over two small tables, a log read and counted into a file, a module of two functions, with hidden tests)

| # | the chain shows | holds for |
|---|---|---|
| 1 | lessons right under 8 of 12 | 0 |
| 2 | more than 1 row in 5 of the kind left out | 3: a join over two small tables, a log read and counted into a file, a module of two functions, with hidden tests |
| 3 | kept-back gap under 15 points | 1: a number with given properties |
| 4 | gap 15 or more, the child alone right more often than its parent, the body not | 0 |
| 5 | gap 15 or more, the child alone not right | 1: a fact found on the open web |
| 6 | taught hard kinds 12 of 23, two generations running | 0 |
