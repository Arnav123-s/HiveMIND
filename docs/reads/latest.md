# The read of g50

Run [44474079616](https://github.com/Arnav123-s/HiveMIND/actions/runs/44474079616), recorded 2026-11-19 12:35: the body was **dropped**. dropped: 54 against 55; after 54 of 64 (easy 32 of 32, hard 22 of 32), before 55 of 64 (easy 32 of 32, hard 23 of 32) on 8 seeds

Written by the record job (`training/reads.py`), with nobody's hand. The rules are those of `docs/DECISIONS.md`.

## The numbers

| What is measured | g50 | g49 (last record) | the body before (same seeds) |
|---|---|---|---|
| Easy kinds passed | 32 of 32 | 31 of 32 | 32 of 32 |
| Hard kinds that have lessons | 22 of 28 | 16 of 22 | 22 of 28 |
| Hard kinds never practised (held out) | 0 of 10 kinds (3 of 30 tasks of the fixed exam; pulse 0 of 4) | 0 of 10 kinds (2 of 30 tasks of the fixed exam; pulse 2 of 10) | 1 of 10 kinds (3 of 30 tasks of the fixed exam; pulse 1 of 4) |
| Right at the first try (practice) | 0.46 (44 of 96) | 0.38 | - |
| Right at the first try, old kinds and K2's new kinds (practice) | old kinds 0.68 (28 of 41); new kinds (K2) 0.29 (16 of 55) | old kinds 0.65 (24 of 37); new kinds (K2) 0.20 (12 of 59) | - |
| Hours for one generation | 5.9 | 6.3 | - |
| Generations recorded with nobody's hand | 8 | 7 | - |
| Talk (the talk exam, out of 10; the bar is 8) | 8.0 of 10 (route 8 of 10, fact 9 of 10, earlier 10 of 10, time 5 of 10) | 7.8 of 10 (route 8 of 10, fact 10 of 10, earlier 10 of 10, time 3 of 10) | - |

## What members solved and what reached the user

| Exam arm | Scope | Graded for both, of tasks sat | Any recorded member passed | Final delivery passed | Member passed, delivery failed | Delivery passed, no recorded member passed |
|---|---|---:|---:|---:|---:|---:|
| before | all | 64 of 64 | 60 | 55 | 5 | 0 |
| before | hard | 32 of 32 | 28 | 23 | 5 | 0 |
| after | all | 64 of 64 | 60 | 54 | 6 | 0 |
| after | hard | 32 of 32 | 28 | 22 | 6 | 0 |

Counts compare the task checker on recorded member answers and their files with the same checker on the final delivery. Only tasks with a known result on both sides enter the last four columns.

## Which final deliveries changed

Comparable deliveries: 64 matched, from 64 tasks sat before and 64 after. Matching requires the same seat, task ID, prompt, kind and exam revision.

| Gained | Lost | Passed both | Failed both |
|---:|---:|---:|---:|
| 2 | 3 | 52 | 7 |

Lost: `h20000505_00` (a state machine from a table, with hidden tests), `h20000506_02` (a state machine from a table, with hidden tests), `h20000506_03` (a simulation followed step by step).

Gained: `h20000503_03` (a text split into sentences), `h20000507_03` (the percent change between two columns, rounded by a rule).

## The chain, by taught hard kind

lessons right by their own check -> rows that fit in training -> loss falls on lessons kept back -> the child alone writes it at the exam -> the body (two agree) passes it.

| kind | lessons right of made | rows left out | kept-back loss before -> after | gap to untaught (points) | child alone right | parent alone right | body right | body before |
|---|---|---|---|---|---|---|---|---|
| a fact from a site and a date sum on it | none made | 37 of 51 (6 skipped for memory) | 0.001 -> 0.001 | +19 | - | - | - | - |
| a join over two small tables | none made | 50 of 85 (6 skipped for memory) | not measured | not measured | 2 of 5 | - | 3 of 3 | 3 of 3 |
| a log read and counted into a file | none made | 51 of 51 | 0.001 -> 0.001 | +95 | - | - | - | - |
| a module of two functions, with hidden tests | none made | 116 of 408 (47 skipped for memory) | 0.069 -> 0.071 | +62 | 1 of 4 | - | 0 of 2 | 0 of 2 |
| a class with rules, with hidden tests | 13 of 13 | 170 of 544 (17 skipped for memory) | 0.103 -> 0.018 | +146 | 2 of 3 | - | 1 of 2 | 1 of 2 |
| a parser for a tiny language, with hidden tests | 12 of 12 | 136 of 425 (9 skipped for memory) | 0.383 -> 0.381 | +65 | - | - | - | - |
| the regions of a grid, with hidden tests | 12 of 12 | 103 of 476 (102 skipped for memory) | 0.070 -> 0.038 | +110 | 1 of 2 | - | 1 of 1 | 1 of 1 |
| a cache that forgets the least recently used, with hidden tests | 14 of 14 | 180 of 561 (20 skipped for memory) | 0.319 -> 0.268 | +80 | - | - | - | - |
| a state machine from a table, with hidden tests | none made | 80 of 153 (2 skipped for memory) | 0.041 -> 0.014 | +129 | 2 of 4 | - | 0 of 2 | 2 of 2 |
| an order of tasks by their dependencies, with hidden tests | 12 of 12 | 46 of 493 (144 skipped for memory) | 0.027 -> 0.015 | +107 | 2 of 2 | - | 2 of 2 | 2 of 2 |
| a number with given properties | none made | 0 of 170 (16 skipped for memory) | 0.228 -> 0.200 | +76 | - | - | - | - |
| a fact read and a date sum on it | none made | 27 of 51 | 0.001 -> 0.001 | -24 | 2 of 2 | - | 2 of 2 | 2 of 2 |
| the percent change between two columns, rounded by a rule | 12 of 12 | 52 of 462 (35 skipped for memory) | 0.018 -> 0.006 | +134 | 3 of 3 | - | 3 of 3 | 2 of 3 |
| a table cut to one row a key, the latest kept | none made | 20 of 34 (7 skipped for memory) | 0.006 -> 0.003 | +114 | 2 of 2 | - | 2 of 2 | 2 of 2 |
| the blanks of a table filled by a rule | none made | not measured | 0.014 -> 0.014 | +65 | - | - | - | - |
| a table grouped, each group's total and mean saved | none made | 20 of 68 (17 skipped for memory) | 0.004 -> 0.003 | +84 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| JSON lines read and counted by a nested field | none made | 85 of 85 | 0.026 -> 0.025 | +69 | - | - | - | - |
| a long table turned wide | none made | 20 of 136 (32 skipped for memory) | 0.004 -> 0.003 | +90 | - | - | - | - |
| several facts fetched and laid out as a file | none made | 20 of 34 (8 skipped for memory) | 0.001 -> 0.002 | +28 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a server log's matching lines counted by class | 12 of 12 | 0 of 408 (26 skipped for memory) | 0.014 -> 0.018 | +39 | - | - | - | - |
| emails and phones found in a messy message | 12 of 12 | 240 of 408 (31 skipped for memory) | 0.050 -> 0.008 | +148 | - | - | - | - |
| a markdown table turned into CSV | none made | 2 of 36 (10 skipped for memory) | 0.008 -> 0.006 | +92 | - | - | - | - |
| names turned and sorted | 12 of 12 | 0 of 442 (11 skipped for memory) | 0.017 -> 0.017 | +68 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a text split into sentences | 12 of 12 | 16 of 442 (81 skipped for memory) | 0.026 -> 0.038 | +20 | 5 of 5 | - | 4 of 4 | 3 of 4 |
| the most frequent words of a text | none made | 12 of 51 (10 skipped for memory) | 0.013 -> 0.011 | +83 | 1 of 1 | - | 0 of 1 | 0 of 1 |
| walk a site over several pages | none made | not measured | 0.000 -> 0.000 | +41 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a fact found on the open web | none made | 27 of 173 (4 skipped for memory) | 0.002 -> 0.003 | +17 | - | - | - | - |

- rows left out: by kind, this generation's rows too long for a slice, of those the slices were given; in brackets those the memory guard skipped every time they came up. Rows not reached before the time was up are not left out
- gap: the kind's fall beside the mean fall of the kinds with no lesson this generation (operate a website, scrape a page to a file: -64 points)
- child alone: the answers of this generation's cells (8) in the pulse; parent alone: those of their parents (g48code, g48code2, g48data, g48data2, g48sources, g48sources2, g48words, g48words2) in every arm. Two members sit a task, so these are few
- parent alone: not measured; no parent sat a task of a taught hard kind (the pulse seats the trunk and the newest cells first; the paired gate's before arm seats the body before, parents among it)

How much the hive taught itself: of this generation's new rows, 180 from the hive's own checked practice and dreams (6 of them fix rows), 249 from the hand-written lesson makers (training/lessons.py, training/kinds/): the hive's own are 42% of those two. Rows trained on: not measured by source (each slice's record says the rows it trained by kind only, rows_by_kind; a field rows_by_source {source: trained} would measure it).

![The chain by kind](../progress/chain.svg)

## Hours

| step | minutes |
|---|---|
| practice | 49 |
| dream | 53 |
| gather | 8 |
| plan | 0 |
| train | 217 |
| join | 2 |
| merge | 2 |
| gate | 70 |
| record | 1 |

From the first job to the last: **5.88 hours** (the bar is 3). Each step runs from its first job's start to its last job's end; practice and dream run side by side.

Train slices lost: 3 of 20. Pulse seats whose server died: 0.

Colab: not used (notebook not there within the wait)

## Next piece

next piece: dose: one change a generation: raw reading and judged pairs off; slices weighed by steps; the one-line trial (rule 3: kept-back gap under 15 points, for 1 of 27 taught hard kinds: a fact read and a date sum on it)

Rules that hold but whose piece is done on the board (docs/PLAN.md), so not named: rule 2 (T4); rule 6 (K1).

| # | the chain shows | holds for |
|---|---|---|
| 1 | lessons right under 8 of 12 | 0 |
| 2 | more than 1 row in 5 of the kind left out | 16: a fact from a site and a date sum on it, a join over two small tables, a log read and counted into a file, a module of two functions, with hidden tests, a class with rules, with hidden tests, a parser for a tiny language, with hidden tests, the regions of a grid, with hidden tests, a cache that forgets the least recently used, with hidden tests, a state machine from a table, with hidden tests, a fact read and a date sum on it, a table cut to one row a key, the latest kept, a table grouped, each group's total and mean saved, JSON lines read and counted by a nested field, several facts fetched and laid out as a file, emails and phones found in a messy message, the most frequent words of a text (piece done) |
| 3 | kept-back gap under 15 points | 1: a fact read and a date sum on it |
| 4 | gap 15 or more, the child alone right more often than its parent, the body not | 0 |
| 5 | gap 15 or more, the child alone not right | 0 |
| 6 | taught hard kinds 12 of 23, two generations running | 27 (piece done) |
