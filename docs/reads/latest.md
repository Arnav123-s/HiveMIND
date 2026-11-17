# The read of g41

Run [44068651860](https://github.com/Arnav123-s/HiveMIND/actions/runs/44068651860), recorded 2026-11-17 16:57: the body was **kept**. the body grows: after 58 of 64 (easy 32 of 32, hard 26 of 32), before 49 of 64 (easy 29 of 32, hard 20 of 32) on 8 seeds

Written by the record job (`training/reads.py`), with nobody's hand. The rules are those of `docs/DECISIONS.md`.

## The numbers

| What is measured | g41 | g39 (last record) | the body before (same seeds) |
|---|---|---|---|
| Easy kinds passed | 32 of 32 | 26 of 32 | 29 of 32 |
| Hard kinds that have lessons | 22 of 25 | 7 of 22 | 17 of 25 |
| Hard kinds never practised (held out) | 4 of 7 | 5 of 10 | 3 of 7 |
| Right at the first try (practice) | 0.47 (45 of 96) | - | - |
| Hours for one generation | 5.1 | - | - |
| Generations recorded with nobody's hand | 0 | 0 | - |

## The chain, by taught hard kind

lessons right by their own check -> rows that fit in training -> loss falls on lessons kept back -> the child alone writes it at the exam -> the body (two agree) passes it.

| kind | lessons right of made | rows left out | kept-back loss before -> after | gap to untaught (points) | child alone right | parent alone right | body right | body before |
|---|---|---|---|---|---|---|---|---|
| a fact from a site and a date sum on it | 12 of 12 | 45 of 266 | 0.451 -> 0.030 | +63 | 3 of 3 | - | 3 of 3 | 2 of 3 |
| a join over two small tables | none made | not measured | not measured | not measured | 2 of 2 | - | 1 of 1 | 1 of 1 |
| a log read and counted into a file | 12 of 12 | 0 of 190 | 0.823 -> 0.222 | +43 | 0 of 1 | - | 0 of 1 | 0 of 1 |
| a module of two functions, with hidden tests | 13 of 13 | 35 of 380 | 0.632 -> 0.382 | +9 | 7 of 9 | - | 5 of 6 | 3 of 6 |
| a number with given properties | none made | 0 of 38 | 0.750 -> 0.522 | +0 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a fact read and a date sum on it | 13 of 13 | 57 of 152 | 0.294 -> 0.012 | +66 | 3 of 3 | - | 3 of 3 | 3 of 3 |
| several facts fetched and laid out as a file | 12 of 12 | 71 of 342 | 0.377 -> 0.016 | +65 | 3 of 3 | - | 3 of 3 | 2 of 3 |
| walk a site over several pages | 12 of 12 | not measured | 0.492 -> 0.022 | +65 | 5 of 5 | - | 5 of 5 | 5 of 5 |
| a fact found on the open web | 12 of 12 | 0 of 209 | 1.027 -> 0.040 | +66 | 2 of 3 | - | 1 of 2 | 0 of 2 |

- rows left out: by kind, this generation's rows each slice did not study, of those it was given (the slices say only their total too long: 52, 52, 18, 72, 149, 41, 143, 80, 15, 171, 141, 18, 52, 18, 15, 183, 136, 80, 177)
- gap: the kind's fall beside the mean fall of the kinds with no lesson this generation (a number with given properties: 30 points)
- child alone: the answers of this generation's cells (8) in the pulse; parent alone: those of their parents (g27sources, g28data, g34code, g34code2, g34data, g34sources, g34words, g34words2) in every arm. Two members sit a task, so these are few

![The chain by kind](../progress/chain.svg)

## Hours

| step | minutes |
|---|---|
| practice | 48 |
| dream | 59 |
| gather | 16 |
| plan | 0 |
| train | 175 |
| join | 2 |
| merge | 2 |
| gate | 54 |
| record | 1 |

From the first job to the last: **5.14 hours** (the bar is 5). Each step runs from its first job's start to its last job's end; practice and dream run side by side.

Train slices lost: 1 of 20. Pulse seats whose server died: 0.

## Next piece

next piece: T4: shorter lessons (rule 2: more than 1 row in 5 of the kind left out, for 2 of 9 taught hard kinds: a fact read and a date sum on it, several facts fetched and laid out as a file)

| # | the chain shows | holds for |
|---|---|---|
| 1 | lessons right under 8 of 12 | 0 |
| 2 | more than 1 row in 5 of the kind left out | 2: a fact read and a date sum on it, several facts fetched and laid out as a file |
| 3 | kept-back gap under 15 points | 2: a module of two functions, with hidden tests, a number with given properties |
| 4 | gap 15 or more, the child alone right more often than its parent, the body not | 0 |
| 5 | gap 15 or more, the child alone not right | 1: a log read and counted into a file |
| 6 | taught hard kinds 12 of 23, two generations running | 0 |
