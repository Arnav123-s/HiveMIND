# The read of g51

Run [44525337919](https://github.com/Arnav123-s/HiveMIND/actions/runs/44525337919), recorded 2026-11-19 19:05: the body was **kept**. kept: 50 against 49; after 50 of 64 (easy 31 of 32, hard 19 of 32), before 49 of 64 (easy 31 of 32, hard 18 of 32) on 8 seeds; the fixed held-out exam: after 3 of 30, before 1 of 30

Written by the record job (`training/reads.py`), with nobody's hand. The rules are those of `docs/DECISIONS.md`.

## The numbers

| What is measured | g51 | g50 (last record) | the body before (same seeds) |
|---|---|---|---|
| Easy kinds passed | 31 of 32 | 32 of 32 | 31 of 32 |
| Hard kinds that have lessons | 19 of 24 | 22 of 28 | 18 of 24 |
| Hard kinds never practised (held out) | 1 of 10 kinds (3 of 30 tasks of the fixed exam; pulse 0 of 8) | 0 of 10 kinds (3 of 30 tasks of the fixed exam; pulse 0 of 4) | 0 of 10 kinds (1 of 30 tasks of the fixed exam; pulse 0 of 8) |
| Right at the first try (practice) | 0.45 (43 of 96) | 0.46 | - |
| Right at the first try, old kinds and K2's new kinds (practice) | old kinds 0.72 (29 of 40); new kinds (K2) 0.25 (14 of 56) | old kinds 0.68 (28 of 41); new kinds (K2) 0.29 (16 of 55) | - |
| Hours for one generation | 6.5 | 5.9 | - |
| Generations recorded with nobody's hand | 9 | 8 | - |
| Talk (the talk exam, out of 10; the bar is 8) | 8.2 of 10 (route 8 of 10, fact 9 of 10, earlier 9 of 10, time 7 of 10) | 8.0 of 10 (route 8 of 10, fact 9 of 10, earlier 10 of 10, time 5 of 10) | - |

## What members solved and what reached the user

| Exam arm | Scope | Graded for both, of tasks sat | Any recorded member passed | Final delivery passed | Member passed, delivery failed | Delivery passed, no recorded member passed |
|---|---|---:|---:|---:|---:|---:|
| before | all | 64 of 64 | 54 | 49 | 5 | 0 |
| before | hard | 32 of 32 | 22 | 18 | 4 | 0 |
| after | all | 64 of 64 | 53 | 50 | 3 | 0 |
| after | hard | 32 of 32 | 22 | 19 | 3 | 0 |

Counts compare the task checker on recorded member answers and their files with the same checker on the final delivery. Only tasks with a known result on both sides enter the last four columns.

## Which final deliveries changed

Comparable deliveries: 64 matched, from 64 tasks sat before and 64 after. Matching requires the same seat, task ID, prompt, kind and exam revision.

| Gained | Lost | Passed both | Failed both |
|---:|---:|---:|---:|
| 1 | 0 | 49 | 14 |

Gained: `h20000518_00` (a class with rules, with hidden tests).

## The chain, by taught hard kind

lessons right by their own check -> rows that fit in training -> loss falls on lessons kept back -> the child alone writes it at the exam -> the body (two agree) passes it.

| kind | lessons right of made | rows left out | kept-back loss before -> after | gap to untaught (points) | child alone right | parent alone right | body right | body before |
|---|---|---|---|---|---|---|---|---|
| a fact from a site and a date sum on it | none made | 38 of 54 (10 skipped for memory) | 0.001 -> 0.001 | -6 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a join over two small tables | none made | 11 of 18 (4 skipped for memory) | not measured | not measured | - | - | - | - |
| a log read and counted into a file | none made | 18 of 18 | 0.001 -> 0.001 | +38 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a module of two functions, with hidden tests | none made | 101 of 234 (47 skipped for memory) | 0.083 -> 0.093 | +5 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a class with rules, with hidden tests | 12 of 12 | 89 of 486 (61 skipped for memory) | 0.067 -> 0.030 | +72 | 2 of 2 | - | 1 of 2 | 0 of 2 |
| a parser for a tiny language, with hidden tests | 14 of 14 | 115 of 558 (68 skipped for memory) | 0.317 -> 0.341 | +9 | - | - | - | - |
| the regions of a grid, with hidden tests | 12 of 12 | 72 of 522 (110 skipped for memory) | 0.060 -> 0.028 | +69 | 1 of 2 | - | 1 of 1 | 1 of 1 |
| a cache that forgets the least recently used, with hidden tests | 13 of 13 | 111 of 576 (73 skipped for memory) | 0.284 -> 0.307 | +8 | - | - | - | - |
| a state machine from a table, with hidden tests | 13 of 13 | 71 of 522 (106 skipped for memory) | 0.021 -> 0.007 | +84 | 2 of 3 | - | 1 of 2 | 1 of 2 |
| an order of tasks by their dependencies, with hidden tests | none made | 31 of 126 (35 skipped for memory) | 0.022 -> 0.016 | +44 | - | - | - | - |
| a number with given properties | none made | 0 of 180 (12 skipped for memory) | 0.230 -> 0.183 | +37 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a fact read and a date sum on it | none made | 25 of 36 (2 skipped for memory) | 0.001 -> 0.004 | -460 | - | - | - | - |
| the percent change between two columns, rounded by a rule | none made | 28 of 183 (58 skipped for memory) | 0.016 -> 0.008 | +66 | 2 of 2 | - | 1 of 1 | 1 of 1 |
| a table cut to one row a key, the latest kept | none made | 21 of 72 (14 skipped for memory) | 0.006 -> 0.003 | +65 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| the blanks of a table filled by a rule | none made | 68 of 144 (25 skipped for memory) | 0.013 -> 0.013 | +18 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a table grouped, each group's total and mean saved | none made | 19 of 36 (11 skipped for memory) | 0.004 -> 0.004 | +17 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| JSON lines read and counted by a nested field | none made | 32 of 54 (3 skipped for memory) | 0.026 -> 0.029 | +5 | 0 of 2 | - | 0 of 1 | 0 of 1 |
| a long table turned wide | none made | 64 of 180 (31 skipped for memory) | 0.004 -> 0.003 | +36 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| several facts fetched and laid out as a file | none made | 17 of 72 (13 skipped for memory) | 0.001 -> 0.002 | -66 | - | - | - | - |
| a server log's matching lines counted by class | 12 of 12 | 0 of 432 (21 skipped for memory) | 0.014 -> 0.019 | -15 | - | - | - | - |
| emails and phones found in a messy message | 12 of 12 | 176 of 396 (69 skipped for memory) | 0.039 -> 0.015 | +78 | 0 of 2 | - | 0 of 1 | 0 of 1 |
| a markdown table turned into CSV | none made | 2 of 75 (14 skipped for memory) | 0.008 -> 0.006 | +41 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| names turned and sorted | 12 of 12 | 0 of 432 (8 skipped for memory) | 0.017 -> 0.016 | +20 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a text split into sentences | 12 of 12 | 1 of 432 (102 skipped for memory) | 0.027 -> 0.028 | +11 | 3 of 3 | - | 3 of 3 | 3 of 3 |
| the most frequent words of a text | 12 of 12 | 12 of 414 (88 skipped for memory) | 0.016 -> 0.009 | +61 | 1 of 1 | - | 0 of 1 | 0 of 1 |
| walk a site over several pages | none made | not measured | 0.000 -> 0.000 | -6 | 2 of 2 | - | 2 of 2 | 2 of 2 |
| a fact found on the open web | none made | 24 of 75 (4 skipped for memory) | 0.002 -> 0.004 | -118 | - | - | - | - |

- rows left out: by kind, this generation's rows too long for a slice, of those the slices were given; in brackets those the memory guard skipped every time they came up. Rows not reached before the time was up are not left out
- gap: the kind's fall beside the mean fall of the kinds with no lesson this generation (scrape a page to a file: -16 points)
- child alone: the answers of this generation's cells (8) in the pulse; parent alone: those of their parents (g48code, g48code2, g48data, g48data2, g48sources, g48sources2, g48words, g48words2) in every arm. Two members sit a task, so these are few
- parent alone: not measured; no parent sat a task of a taught hard kind (the pulse seats the trunk and the newest cells first; the paired gate's before arm seats the body before, parents among it)

How much the hive taught itself: of this generation's new rows, 192 from the hive's own checked practice and dreams (7 of them fix rows), 252 from the hand-written lesson makers (training/lessons.py, training/kinds/): the hive's own are 43% of those two. Rows trained on: not measured by source (each slice's record says the rows it trained by kind only, rows_by_kind; a field rows_by_source {source: trained} would measure it).

![The chain by kind](../progress/chain.svg)

## Hours

| step | minutes |
|---|---|
| practice | 54 |
| dream | 47 |
| gather | 9 |
| plan | 0 |
| train | 220 |
| join | 2 |
| merge | 2 |
| gate | 100 |
| record | 1 |

From the first job to the last: **6.49 hours** (the bar is 3). Each step runs from its first job's start to its last job's end; practice and dream run side by side.

Train slices lost: 2 of 20. Pulse seats whose server died: 0.

Colab: not used (notebook not there within the wait)

## Next piece

next piece: dose: one change a generation: raw reading and judged pairs off; slices weighed by steps; the one-line trial (rule 3: kept-back gap under 15 points, for 11 of 27 taught hard kinds: a fact from a site and a date sum on it, a module of two functions, with hidden tests, a parser for a tiny language, with hidden tests, a cache that forgets the least recently used, with hidden tests, a fact read and a date sum on it, JSON lines read and counted by a nested field, several facts fetched and laid out as a file, a server log's matching lines counted by class, a text split into sentences, walk a site over several pages, a fact found on the open web)

Rules that hold but whose piece is done on the board (docs/PLAN.md), so not named: rule 2 (T4); rule 6 (K1).

| # | the chain shows | holds for |
|---|---|---|
| 1 | lessons right under 8 of 12 | 0 |
| 2 | more than 1 row in 5 of the kind left out | 15: a fact from a site and a date sum on it, a join over two small tables, a log read and counted into a file, a module of two functions, with hidden tests, a parser for a tiny language, with hidden tests, an order of tasks by their dependencies, with hidden tests, a fact read and a date sum on it, a table cut to one row a key, the latest kept, the blanks of a table filled by a rule, a table grouped, each group's total and mean saved, JSON lines read and counted by a nested field, a long table turned wide, several facts fetched and laid out as a file, emails and phones found in a messy message, a fact found on the open web (piece done) |
| 3 | kept-back gap under 15 points | 11: a fact from a site and a date sum on it, a module of two functions, with hidden tests, a parser for a tiny language, with hidden tests, a cache that forgets the least recently used, with hidden tests, a fact read and a date sum on it, JSON lines read and counted by a nested field, several facts fetched and laid out as a file, a server log's matching lines counted by class, a text split into sentences, walk a site over several pages, a fact found on the open web |
| 4 | gap 15 or more, the child alone right more often than its parent, the body not | 0 |
| 5 | gap 15 or more, the child alone not right | 1: emails and phones found in a messy message |
| 6 | taught hard kinds 12 of 23, two generations running | 27 (piece done) |
