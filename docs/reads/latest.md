# The read of g53

Run [44649281647](https://github.com/Arnav123-s/HiveMIND/actions/runs/44649281647), recorded 2026-11-20 06:07: the body was **kept**. kept: 50 against 48; after 50 of 64 (easy 31 of 32, hard 19 of 32), before 48 of 64 (easy 31 of 32, hard 17 of 32) on 8 seeds; the fixed held-out exam: after 3 of 30, before 2 of 30

Written by the record job (`training/reads.py`), with nobody's hand. The rules are those of `docs/DECISIONS.md`.

## The numbers

| What is measured | g53 | g52 (last record) | the body before (same seeds) |
|---|---|---|---|
| Easy kinds passed | 31 of 32 | 32 of 32 | 31 of 32 |
| Hard kinds that have lessons | 17 of 23 | 20 of 25 | 17 of 23 |
| Hard kinds never practised (held out) | 1 of 10 kinds (3 of 30 tasks of the fixed exam; pulse 2 of 9) | 0 of 10 kinds (1 of 30 tasks of the fixed exam; pulse 0 of 7) | 0 of 10 kinds (2 of 30 tasks of the fixed exam; pulse 0 of 9) |
| Right at the first try (practice) | 0.43 (41 of 96) | 0.41 | - |
| Right at the first try, old kinds and K2's new kinds (practice) | old kinds 0.65 (30 of 46); new kinds (K2) 0.22 (11 of 50) | old kinds 0.65 (28 of 43); new kinds (K2) 0.21 (11 of 53) | - |
| Hours for one generation | 5.2 | 5.8 | - |
| Generations recorded with nobody's hand | 11 | 10 | - |
| Talk (the talk exam, out of 10; the bar is 8) | 8.0 of 10 (route 9 of 10, fact 10 of 10, earlier 8 of 10, time 5 of 10) | 8.8 of 10 (route 8 of 10, fact 10 of 10, earlier 10 of 10, time 7 of 10) | - |

## What members solved and what reached the user

| Exam arm | Scope | Graded for both, of tasks sat | Any recorded member passed | Final delivery passed | Member passed, delivery failed | Delivery passed, no recorded member passed |
|---|---|---:|---:|---:|---:|---:|
| before | all | 64 of 64 | 51 | 48 | 3 | 0 |
| before | hard | 32 of 32 | 20 | 17 | 3 | 0 |
| after | all | 64 of 64 | 50 | 50 | 0 | 0 |
| after | hard | 32 of 32 | 19 | 19 | 0 | 0 |

Counts compare the task checker on recorded member answers and their files with the same checker on the final delivery. Only tasks with a known result on both sides enter the last four columns.

## Which final deliveries changed

Comparable deliveries: 64 matched, from 64 tasks sat before and 64 after. Matching requires the same seat, task ID, prompt, kind and exam revision.

| Gained | Lost | Passed both | Failed both |
|---:|---:|---:|---:|
| 3 | 1 | 47 | 13 |

Lost: `h20000538_00` (the blanks of a table filled by a rule).

Gained: `h20000531_03` (a simulation followed step by step), `h20000533_03` (a simulation followed step by step), `h20000537_02` (a parser for a tiny language, with hidden tests).

## The chain, by taught hard kind

lessons right by their own check -> rows that fit in training -> loss falls on lessons kept back -> the child alone writes it at the exam -> the body (two agree) passes it.

| kind | lessons right of made | rows left out | kept-back loss before -> after | gap to untaught (points) | child alone right | parent alone right | body right | body before |
|---|---|---|---|---|---|---|---|---|
| a fact from a site and a date sum on it | none made | 39 of 85 (7 skipped for memory) | 0.001 -> 0.001 | -56 | - | - | - | - |
| a join over two small tables | none made | 40 of 52 (5 skipped for memory) | not measured | not measured | 1 of 2 | - | 1 of 1 | 1 of 1 |
| a log read and counted into a file | none made | 48 of 51 (2 skipped for memory) | 0.001 -> 0.002 | -119 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a module of two functions, with hidden tests | 13 of 13 | 154 of 770 (72 skipped for memory) | 0.068 -> 0.064 | +5 | - | - | - | - |
| a class with rules, with hidden tests | none made | 32 of 70 (8 skipped for memory) | 0.073 -> 0.032 | +54 | - | - | - | - |
| a parser for a tiny language, with hidden tests | none made | 67 of 119 (7 skipped for memory) | 0.053 -> 0.014 | +72 | 1 of 1 | 0 of 2 | 1 of 1 | 0 of 1 |
| the regions of a grid, with hidden tests | none made | 105 of 158 (3 skipped for memory) | 0.083 -> 0.065 | +20 | 1 of 2 | 1 of 2 | 1 of 1 | 1 of 1 |
| a cache that forgets the least recently used, with hidden tests | 13 of 13 | 165 of 547 (45 skipped for memory) | 0.301 -> 0.313 | -6 | 1 of 3 | - | 1 of 2 | 1 of 2 |
| a state machine from a table, with hidden tests | 12 of 12 | 86 of 408 (74 skipped for memory) | 0.021 -> 0.015 | +30 | 0 of 2 | - | 0 of 1 | 0 of 1 |
| an order of tasks by their dependencies, with hidden tests | none made | 55 of 107 (21 skipped for memory) | 0.027 -> 0.023 | +14 | - | - | - | - |
| a number with given properties | none made | 0 of 68 (15 skipped for memory) | 0.231 -> 0.221 | +2 | 2 of 2 | - | 2 of 2 | 2 of 2 |
| a fact read and a date sum on it | none made | 26 of 68 (3 skipped for memory) | 0.001 -> 0.001 | -50 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| the percent change between two columns, rounded by a rule | none made | 52 of 122 (37 skipped for memory) | 0.011 -> 0.008 | +28 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a table cut to one row a key, the latest kept | none made | 60 of 136 (23 skipped for memory) | 0.003 -> 0.004 | -48 | - | - | - | - |
| the blanks of a table filled by a rule | none made | not measured | 0.011 -> 0.010 | +9 | 0 of 4 | - | 0 of 2 | 1 of 2 |
| a table grouped, each group's total and mean saved | none made | 24 of 34 (7 skipped for memory) | 0.003 -> 0.004 | -19 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| JSON lines read and counted by a nested field | 12 of 12 | 46 of 459 (6 skipped for memory) | 0.021 -> 0.030 | -40 | 2 of 2 | - | 2 of 2 | 2 of 2 |
| a long table turned wide | none made | 26 of 102 (24 skipped for memory) | 0.003 -> 0.003 | -6 | - | - | - | - |
| several facts fetched and laid out as a file | none made | 24 of 102 (4 skipped for memory) | 0.001 -> 0.001 | -15 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a server log's matching lines counted by class | none made | 37 of 37 | 0.015 -> 0.025 | -66 | 2 of 2 | - | 2 of 2 | 2 of 2 |
| emails and phones found in a messy message | 12 of 12 | 0 of 408 (6 skipped for memory) | 0.039 -> 0.019 | +51 | - | - | - | - |
| a markdown table turned into CSV | none made | not measured | 0.005 -> 0.006 | -21 | 0 of 4 | - | 0 of 2 | 0 of 2 |
| names turned and sorted | none made | not measured | 0.017 -> 0.028 | -67 | - | - | - | - |
| a text split into sentences | 12 of 12 | 2 of 410 (25 skipped for memory) | 0.025 -> 0.049 | -94 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| the most frequent words of a text | 13 of 13 | 35 of 493 (27 skipped for memory) | 0.201 -> 0.033 | +82 | - | - | - | - |
| walk a site over several pages | none made | not measured | 0.000 -> 0.000 | -38 | - | - | - | - |
| a fact found on the open web | none made | 25 of 68 (3 skipped for memory) | 0.001 -> 0.003 | -125 | 1 of 1 | - | 1 of 1 | 1 of 1 |

- rows left out: by kind, this generation's rows too long for a slice, of those the slices were given; in brackets those the memory guard skipped every time they came up. Rows not reached before the time was up are not left out
- gap: the kind's fall beside the mean fall of the kinds with no lesson this generation (scrape a page to a file: 2 points)
- child alone: the answers of this generation's cells (8) in the pulse; parent alone: those of their parents (g49code, g49code2, g49data, g49data2, g49sources, g49sources2, g49words, g49words2) in every arm. Two members sit a task, so these are few

How much the hive taught itself: of this generation's new rows, 222 from the hive's own checked practice and dreams (18 of them fix rows), 177 from the hand-written lesson makers (training/lessons.py, training/kinds/): the hive's own are 56% of those two. Rows trained on: not measured by source (each slice's record says the rows it trained by kind only, rows_by_kind; a field rows_by_source {source: trained} would measure it).

![The chain by kind](../progress/chain.svg)

## Hours

| step | minutes |
|---|---|
| practice | 48 |
| dream | 58 |
| gather | 4 |
| plan | 0 |
| train | 176 |
| join | 3 |
| merge | 2 |
| gate | 71 |
| record | 1 |

From the first job to the last: **5.25 hours** (the bar is 3). Each step runs from its first job's start to its last job's end; practice and dream run side by side.

Train slices lost: 3 of 20. Pulse seats whose server died: 0.

Colab: not used (notebook not there within the wait)

## Next piece

next piece: dose: one change a generation: raw reading and judged pairs off; slices weighed by steps; the one-line trial (rule 3: kept-back gap under 15 points, for 19 of 27 taught hard kinds: a fact from a site and a date sum on it, a log read and counted into a file, a module of two functions, with hidden tests, a cache that forgets the least recently used, with hidden tests, an order of tasks by their dependencies, with hidden tests, a number with given properties, a fact read and a date sum on it, a table cut to one row a key, the latest kept, the blanks of a table filled by a rule, a table grouped, each group's total and mean saved, JSON lines read and counted by a nested field, a long table turned wide, several facts fetched and laid out as a file, a server log's matching lines counted by class, a markdown table turned into CSV, names turned and sorted, a text split into sentences, walk a site over several pages, a fact found on the open web)

Rules that hold but whose piece is done on the board (docs/PLAN.md), so not named: rule 2 (T4); rule 6 (K1).

| # | the chain shows | holds for |
|---|---|---|
| 1 | lessons right under 8 of 12 | 0 |
| 2 | more than 1 row in 5 of the kind left out | 17: a fact from a site and a date sum on it, a join over two small tables, a log read and counted into a file, a class with rules, with hidden tests, a parser for a tiny language, with hidden tests, the regions of a grid, with hidden tests, a cache that forgets the least recently used, with hidden tests, a state machine from a table, with hidden tests, an order of tasks by their dependencies, with hidden tests, a fact read and a date sum on it, the percent change between two columns, rounded by a rule, a table cut to one row a key, the latest kept, a table grouped, each group's total and mean saved, a long table turned wide, several facts fetched and laid out as a file, a server log's matching lines counted by class, a fact found on the open web (piece done) |
| 3 | kept-back gap under 15 points | 19: a fact from a site and a date sum on it, a log read and counted into a file, a module of two functions, with hidden tests, a cache that forgets the least recently used, with hidden tests, an order of tasks by their dependencies, with hidden tests, a number with given properties, a fact read and a date sum on it, a table cut to one row a key, the latest kept, the blanks of a table filled by a rule, a table grouped, each group's total and mean saved, JSON lines read and counted by a nested field, a long table turned wide, several facts fetched and laid out as a file, a server log's matching lines counted by class, a markdown table turned into CSV, names turned and sorted, a text split into sentences, walk a site over several pages, a fact found on the open web |
| 4 | gap 15 or more, the child alone right more often than its parent, the body not | 0 |
| 5 | gap 15 or more, the child alone not right | 1: a state machine from a table, with hidden tests |
| 6 | taught hard kinds 12 of 23, two generations running | 27 (piece done) |
