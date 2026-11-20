# The read of g52

Run [44594712108](https://github.com/Arnav123-s/HiveMIND/actions/runs/44594712108), recorded 2026-11-20 00:51: the body was **dropped**. dropped: 52 against 52, the fixed held-out exam 1 against 2 with no gain on the pulse; after 52 of 64 (easy 32 of 32, hard 20 of 32), before 52 of 64 (easy 32 of 32, hard 20 of 32) on 8 seeds; the fixed held-out exam: after 1 of 30, before 2 of 30

Written by the record job (`training/reads.py`), with nobody's hand. The rules are those of `docs/DECISIONS.md`.

## The numbers

| What is measured | g52 | g51 (last record) | the body before (same seeds) |
|---|---|---|---|
| Easy kinds passed | 32 of 32 | 31 of 32 | 32 of 32 |
| Hard kinds that have lessons | 20 of 25 | 19 of 24 | 20 of 25 |
| Hard kinds never practised (held out) | 0 of 10 kinds (1 of 30 tasks of the fixed exam; pulse 0 of 7) | 1 of 10 kinds (3 of 30 tasks of the fixed exam; pulse 0 of 8) | 1 of 10 kinds (2 of 30 tasks of the fixed exam; pulse 0 of 7) |
| Right at the first try (practice) | 0.41 (39 of 96) | 0.45 | - |
| Right at the first try, old kinds and K2's new kinds (practice) | old kinds 0.65 (28 of 43); new kinds (K2) 0.21 (11 of 53) | old kinds 0.72 (29 of 40); new kinds (K2) 0.25 (14 of 56) | - |
| Hours for one generation | 5.8 | 6.5 | - |
| Generations recorded with nobody's hand | 10 | 9 | - |
| Talk (the talk exam, out of 10; the bar is 8) | 8.8 of 10 (route 8 of 10, fact 10 of 10, earlier 10 of 10, time 7 of 10) | 8.2 of 10 (route 8 of 10, fact 9 of 10, earlier 9 of 10, time 7 of 10) | - |

## What members solved and what reached the user

| Exam arm | Scope | Graded for both, of tasks sat | Any recorded member passed | Final delivery passed | Member passed, delivery failed | Delivery passed, no recorded member passed |
|---|---|---:|---:|---:|---:|---:|
| before | all | 64 of 64 | 55 | 52 | 3 | 0 |
| before | hard | 32 of 32 | 23 | 20 | 3 | 0 |
| after | all | 64 of 64 | 54 | 52 | 2 | 0 |
| after | hard | 32 of 32 | 22 | 20 | 2 | 0 |

Counts compare the task checker on recorded member answers and their files with the same checker on the final delivery. Only tasks with a known result on both sides enter the last four columns.

## Which final deliveries changed

Comparable deliveries: 64 matched, from 64 tasks sat before and 64 after. Matching requires the same seat, task ID, prompt, kind and exam revision.

| Gained | Lost | Passed both | Failed both |
|---:|---:|---:|---:|
| 2 | 2 | 50 | 10 |

Lost: `h20000523_03` (a module of two functions, with hidden tests), `h20000527_03` (a module of two functions, with hidden tests).

Gained: `h20000521_02` (the most frequent words of a text), `h20000524_03` (a class with rules, with hidden tests).

## The chain, by taught hard kind

lessons right by their own check -> rows that fit in training -> loss falls on lessons kept back -> the child alone writes it at the exam -> the body (two agree) passes it.

| kind | lessons right of made | rows left out | kept-back loss before -> after | gap to untaught (points) | child alone right | parent alone right | body right | body before |
|---|---|---|---|---|---|---|---|---|
| a fact from a site and a date sum on it | none made | 32 of 85 (14 skipped for memory) | 0.000 -> 0.001 | +35 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a join over two small tables | none made | 27 of 52 (8 skipped for memory) | not measured | not measured | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a log read and counted into a file | none made | 15 of 17 (2 skipped for memory) | 0.001 -> 0.001 | +52 | 2 of 2 | - | 2 of 2 | 2 of 2 |
| a module of two functions, with hidden tests | 12 of 12 | 113 of 685 (75 skipped for memory) | 0.084 -> 0.080 | +58 | 2 of 4 | - | 0 of 2 | 2 of 2 |
| a class with rules, with hidden tests | none made | 17 of 53 (5 skipped for memory) | 0.067 -> 0.030 | +109 | 2 of 2 | - | 1 of 1 | 0 of 1 |
| a parser for a tiny language, with hidden tests | 12 of 12 | 84 of 391 (47 skipped for memory) | 0.046 -> 0.012 | +128 | - | - | - | - |
| the regions of a grid, with hidden tests | none made | 85 of 123 (4 skipped for memory) | 0.066 -> 0.027 | +111 | - | - | - | - |
| a cache that forgets the least recently used, with hidden tests | 12 of 12 | 88 of 393 (38 skipped for memory) | 0.277 -> 0.287 | +49 | 0 of 2 | - | 0 of 1 | 0 of 1 |
| a state machine from a table, with hidden tests | 12 of 12 | 53 of 408 (87 skipped for memory) | 0.015 -> 0.009 | +88 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| an order of tasks by their dependencies, with hidden tests | none made | 50 of 140 (34 skipped for memory) | 0.022 -> 0.015 | +82 | 2 of 2 | - | 2 of 2 | 2 of 2 |
| a number with given properties | none made | 0 of 34 (13 skipped for memory) | 0.231 -> 0.196 | +68 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a fact read and a date sum on it | none made | 23 of 34 (4 skipped for memory) | 0.001 -> 0.001 | +28 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| the percent change between two columns, rounded by a rule | none made | 41 of 156 (48 skipped for memory) | 0.010 -> 0.005 | +104 | - | - | - | - |
| a table cut to one row a key, the latest kept | none made | 41 of 102 (17 skipped for memory) | 0.003 -> 0.002 | +80 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| the blanks of a table filled by a rule | none made | 15 of 34 | 0.011 -> 0.009 | +69 | - | - | - | - |
| a table grouped, each group's total and mean saved | none made | 19 of 102 (19 skipped for memory) | 0.003 -> 0.002 | +84 | - | - | - | - |
| JSON lines read and counted by a nested field | 12 of 12 | 15 of 391 (5 skipped for memory) | 0.021 -> 0.028 | +24 | 1 of 5 | - | 1 of 3 | 1 of 3 |
| a long table turned wide | none made | 16 of 68 (18 skipped for memory) | 0.003 -> 0.003 | +48 | 2 of 2 | - | 2 of 2 | 2 of 2 |
| several facts fetched and laid out as a file | none made | 19 of 136 (13 skipped for memory) | 0.001 -> 0.001 | +51 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a server log's matching lines counted by class | none made | 102 of 102 | 0.015 -> 0.021 | +13 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| emails and phones found in a messy message | 12 of 12 | 206 of 408 (54 skipped for memory) | 0.037 -> 0.016 | +111 | - | - | - | - |
| a markdown table turned into CSV | none made | 0 of 34 (1 skipped for memory) | 0.005 -> 0.002 | +112 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| names turned and sorted | none made | 0 of 102 (3 skipped for memory) | 0.017 -> 0.017 | +53 | - | - | - | - |
| a text split into sentences | 12 of 12 | 4 of 410 (86 skipped for memory) | 0.026 -> 0.028 | +47 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| the most frequent words of a text | 13 of 13 | 28 of 493 (101 skipped for memory) | 0.021 -> 0.008 | +115 | 1 of 1 | - | 1 of 1 | 0 of 1 |
| walk a site over several pages | none made | not measured | 0.000 -> 0.000 | +20 | - | - | - | - |
| a fact found on the open web | none made | 22 of 136 (6 skipped for memory) | 0.001 -> 0.002 | -5 | 1 of 1 | - | 1 of 1 | 1 of 1 |

- rows left out: by kind, this generation's rows too long for a slice, of those the slices were given; in brackets those the memory guard skipped every time they came up. Rows not reached before the time was up are not left out
- gap: the kind's fall beside the mean fall of the kinds with no lesson this generation (scrape a page to a file: -53 points)
- child alone: the answers of this generation's cells (8) in the pulse; parent alone: those of their parents (g49code, g49code2, g49data, g49data2, g49sources, g49sources2, g49words, g49words2) in every arm. Two members sit a task, so these are few
- parent alone: not measured; no parent sat a task of a taught hard kind (the pulse seats the trunk and the newest cells first; the paired gate's before arm seats the body before, parents among it)

How much the hive taught itself: of this generation's new rows, 194 from the hive's own checked practice and dreams (9 of them fix rows), 195 from the hand-written lesson makers (training/lessons.py, training/kinds/): the hive's own are 50% of those two. Rows trained on: not measured by source (each slice's record says the rows it trained by kind only, rows_by_kind; a field rows_by_source {source: trained} would measure it).

![The chain by kind](../progress/chain.svg)

## Hours

| step | minutes |
|---|---|
| practice | 48 |
| dream | 48 |
| gather | 11 |
| plan | 0 |
| train | 215 |
| join | 2 |
| merge | 2 |
| gate | 66 |
| record | 1 |

From the first job to the last: **5.76 hours** (the bar is 3). Each step runs from its first job's start to its last job's end; practice and dream run side by side.

Train slices lost: 3 of 20. Pulse seats whose server died: 0.

Colab: not used (notebook not there within the wait)

## Next piece

next piece: dose: one change a generation: raw reading and judged pairs off; slices weighed by steps; the one-line trial (rule 3: kept-back gap under 15 points, for 2 of 27 taught hard kinds: a server log's matching lines counted by class, a fact found on the open web)

Rules that hold but whose piece is done on the board (docs/PLAN.md), so not named: rule 2 (T4); rule 6 (K1).

| # | the chain shows | holds for |
|---|---|---|
| 1 | lessons right under 8 of 12 | 0 |
| 2 | more than 1 row in 5 of the kind left out | 15: a fact from a site and a date sum on it, a join over two small tables, a log read and counted into a file, a class with rules, with hidden tests, a parser for a tiny language, with hidden tests, the regions of a grid, with hidden tests, a cache that forgets the least recently used, with hidden tests, an order of tasks by their dependencies, with hidden tests, a fact read and a date sum on it, the percent change between two columns, rounded by a rule, a table cut to one row a key, the latest kept, the blanks of a table filled by a rule, a long table turned wide, a server log's matching lines counted by class, emails and phones found in a messy message (piece done) |
| 3 | kept-back gap under 15 points | 2: a server log's matching lines counted by class, a fact found on the open web |
| 4 | gap 15 or more, the child alone right more often than its parent, the body not | 0 |
| 5 | gap 15 or more, the child alone not right | 1: a cache that forgets the least recently used, with hidden tests |
| 6 | taught hard kinds 12 of 23, two generations running | 27 (piece done) |
