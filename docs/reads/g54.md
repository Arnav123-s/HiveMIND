# The read of g54

Run [44685601437](https://github.com/Arnav123-s/HiveMIND/actions/runs/44685601437), recorded 2026-11-20 11:35: the body was **dropped**. dropped: 50 against 52; after 50 of 64 (easy 32 of 32, hard 18 of 32), before 52 of 64 (easy 32 of 32, hard 20 of 32) on 8 seeds

Written by the record job (`training/reads.py`), with nobody's hand. The rules are those of `docs/DECISIONS.md`.

## The numbers

| What is measured | g54 | g53 (last record) | the body before (same seeds) |
|---|---|---|---|
| Easy kinds passed | 32 of 32 | 31 of 32 | 32 of 32 |
| Hard kinds that have lessons | 18 of 25 | 17 of 23 | 19 of 25 |
| Hard kinds never practised (held out) | 0 of 10 kinds (1 of 27 tasks of the fixed exam; pulse 0 of 7) | 1 of 10 kinds (3 of 30 tasks of the fixed exam; pulse 2 of 9) | 0 of 10 kinds (1 of 27 tasks of the fixed exam; pulse 1 of 7) |
| Right at the first try (practice) | 0.44 (42 of 96) | 0.43 | - |
| Right at the first try, old kinds and K2's new kinds (practice) | old kinds 0.60 (26 of 43); new kinds (K2) 0.30 (16 of 53) | old kinds 0.65 (30 of 46); new kinds (K2) 0.22 (11 of 50) | - |
| Hours for one generation | 5.5 | 5.2 | - |
| Generations recorded with nobody's hand | 12 | 11 | - |
| Talk (the talk exam, out of 10; the bar is 8) | 8.0 of 10 (route 7 of 10, fact 10 of 10, earlier 8 of 10, time 7 of 10) | 8.0 of 10 (route 9 of 10, fact 10 of 10, earlier 8 of 10, time 5 of 10) | - |

## What members solved and what reached the user

| Exam arm | Scope | Graded for both, of tasks sat | Any recorded member passed | Final delivery passed | Member passed, delivery failed | Delivery passed, no recorded member passed |
|---|---|---:|---:|---:|---:|---:|
| before | all | 64 of 64 | 53 | 52 | 1 | 0 |
| before | hard | 32 of 32 | 21 | 20 | 1 | 0 |
| after | all | 64 of 64 | 52 | 50 | 2 | 0 |
| after | hard | 32 of 32 | 20 | 18 | 2 | 0 |

Counts compare the task checker on recorded member answers and their files with the same checker on the final delivery. Only tasks with a known result on both sides enter the last four columns.

## Which final deliveries changed

Comparable deliveries: 64 matched, from 64 tasks sat before and 64 after. Matching requires the same seat, task ID, prompt, kind and exam revision.

| Gained | Lost | Passed both | Failed both |
|---:|---:|---:|---:|
| 0 | 2 | 50 | 12 |

Lost: `h20000546_01` (a file given in the task, edited to a specification), `h20000548_00` (a cache that forgets the least recently used, with hidden tests).

## The chain, by taught hard kind

lessons right by their own check -> rows that fit in training -> loss falls on lessons kept back -> the child alone writes it at the exam -> the body (two agree) passes it.

| kind | lessons right of made | rows left out | kept-back loss before -> after | gap to untaught (points) | child alone right | parent alone right | body right | body before |
|---|---|---|---|---|---|---|---|---|
| a fact from a site and a date sum on it | none made | 30 of 51 (12 skipped for memory) | 0.001 -> 0.001 | +13 | 2 of 2 | - | 2 of 2 | 2 of 2 |
| a join over two small tables | none made | 12 of 20 (2 skipped for memory) | not measured | not measured | 1 of 1 | 1 of 1 | 1 of 1 | 1 of 1 |
| a log read and counted into a file | none made | 48 of 51 (2 skipped for memory) | 0.001 -> 0.001 | +60 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a module of two functions, with hidden tests | 13 of 13 | 157 of 938 (60 skipped for memory) | 0.087 -> 0.090 | +41 | 2 of 2 | - | 2 of 2 | 2 of 2 |
| a class with rules, with hidden tests | none made | 50 of 170 (32 skipped for memory) | 0.041 -> 0.024 | +85 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a parser for a tiny language, with hidden tests | none made | 32 of 88 (4 skipped for memory) | 0.018 -> 0.008 | +103 | - | - | - | - |
| the regions of a grid, with hidden tests | none made | 84 of 119 (2 skipped for memory) | 0.015 -> 0.008 | +92 | 0 of 2 | 0 of 2 | 0 of 1 | 0 of 1 |
| a cache that forgets the least recently used, with hidden tests | 12 of 12 | 112 of 512 (33 skipped for memory) | 0.276 -> 0.288 | +40 | 0 of 2 | - | 0 of 2 | 1 of 2 |
| a state machine from a table, with hidden tests | none made | 23 of 34 (2 skipped for memory) | 0.006 -> 0.003 | +93 | 0 of 6 | 0 of 2 | 0 of 3 | 0 of 3 |
| an order of tasks by their dependencies, with hidden tests | none made | 35 of 136 (41 skipped for memory) | 0.016 -> 0.010 | +86 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a number with given properties | none made | 0 of 34 (10 skipped for memory) | 0.184 -> 0.151 | +62 | 2 of 3 | - | 2 of 2 | 2 of 2 |
| a fact read and a date sum on it | none made | 23 of 51 (2 skipped for memory) | 0.001 -> 0.002 | -84 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| the percent change between two columns, rounded by a rule | none made | 35 of 153 (54 skipped for memory) | 0.008 -> 0.004 | +87 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a table cut to one row a key, the latest kept | none made | 28 of 68 (11 skipped for memory) | 0.003 -> 0.004 | +32 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| the blanks of a table filled by a rule | 12 of 12 | 7 of 391 (11 skipped for memory) | 0.004 -> 0.002 | +92 | - | - | - | - |
| a table grouped, each group's total and mean saved | none made | 52 of 170 (24 skipped for memory) | 0.003 -> 0.003 | +59 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| JSON lines read and counted by a nested field | none made | 63 of 85 (3 skipped for memory) | 0.024 -> 0.029 | +22 | 2 of 2 | - | 2 of 2 | 2 of 2 |
| a long table turned wide | none made | 14 of 34 (10 skipped for memory) | 0.002 -> 0.002 | +42 | - | - | - | - |
| several facts fetched and laid out as a file | none made | 15 of 34 (11 skipped for memory) | 0.001 -> 0.001 | +33 | - | - | - | - |
| a server log's matching lines counted by class | none made | not measured | 0.015 -> 0.017 | +30 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| emails and phones found in a messy message | 12 of 12 | 29 of 476 (15 skipped for memory) | 0.018 -> 0.017 | +51 | - | - | - | - |
| a markdown table turned into CSV | none made | not measured | 0.005 -> 0.004 | +51 | 0 of 2 | - | 0 of 1 | 0 of 1 |
| names turned and sorted | none made | not measured | 0.015 -> 0.024 | -17 | - | - | - | - |
| a text split into sentences | none made | 7 of 68 (7 skipped for memory) | 0.028 -> 0.050 | -38 | - | - | - | - |
| the most frequent words of a text | none made | 22 of 122 (22 skipped for memory) | 0.051 -> 0.035 | +75 | - | - | - | - |
| walk a site over several pages | none made | 0 of 34 (1 skipped for memory) | 0.000 -> 0.000 | -2 | - | - | - | - |
| a fact found on the open web | none made | 21 of 34 (3 skipped for memory) | 0.001 -> 0.002 | +5 | 1 of 1 | - | 1 of 1 | 1 of 1 |

- rows left out: by kind, this generation's rows too long for a slice, of those the slices were given; in brackets those the memory guard skipped every time they came up. Rows not reached before the time was up are not left out
- gap: the kind's fall beside the mean fall of the kinds with no lesson this generation (scrape a page to a file: -45 points)
- child alone: the answers of this generation's cells (8) in the pulse; parent alone: those of their parents (g51code, g51code2, g51data, g51data2, g51sources, g51sources2, g51words, g51words2) in every arm. Two members sit a task, so these are few

How much the hive taught itself: of this generation's new rows, 174 from the hive's own checked practice and dreams (6 of them fix rows), 99 from the hand-written lesson makers (training/lessons.py, training/kinds/): the hive's own are 64% of those two. Rows trained on: not measured by source (each slice's record says the rows it trained by kind only, rows_by_kind; a field rows_by_source {source: trained} would measure it).

![The chain by kind](../progress/chain.svg)

## Hours

| step | minutes |
|---|---|
| practice | 53 |
| dream | 61 |
| gather | 5 |
| plan | 0 |
| train | 205 |
| join | 2 |
| merge | 2 |
| gate | 51 |
| record | 1 |

From the first job to the last: **5.46 hours** (the bar is 3). Each step runs from its first job's start to its last job's end; practice and dream run side by side.

Train slices lost: 3 of 20. Pulse seats whose server died: 0.

Colab: not used (notebook not there within the wait)

## Next piece

next piece: dose: one change a generation: raw reading and judged pairs off; slices weighed by steps; the one-line trial (rule 3: kept-back gap under 15 points, for 6 of 27 taught hard kinds: a fact from a site and a date sum on it, a fact read and a date sum on it, names turned and sorted, a text split into sentences, walk a site over several pages, a fact found on the open web)

Rules that hold but whose piece is done on the board (docs/PLAN.md), so not named: rule 2 (T4); rule 6 (K1).

| # | the chain shows | holds for |
|---|---|---|
| 1 | lessons right under 8 of 12 | 0 |
| 2 | more than 1 row in 5 of the kind left out | 17: a fact from a site and a date sum on it, a join over two small tables, a log read and counted into a file, a class with rules, with hidden tests, a parser for a tiny language, with hidden tests, the regions of a grid, with hidden tests, a cache that forgets the least recently used, with hidden tests, a state machine from a table, with hidden tests, an order of tasks by their dependencies, with hidden tests, a fact read and a date sum on it, the percent change between two columns, rounded by a rule, a table cut to one row a key, the latest kept, a table grouped, each group's total and mean saved, JSON lines read and counted by a nested field, a long table turned wide, several facts fetched and laid out as a file, a fact found on the open web (piece done) |
| 3 | kept-back gap under 15 points | 6: a fact from a site and a date sum on it, a fact read and a date sum on it, names turned and sorted, a text split into sentences, walk a site over several pages, a fact found on the open web |
| 4 | gap 15 or more, the child alone right more often than its parent, the body not | 0 |
| 5 | gap 15 or more, the child alone not right | 4: the regions of a grid, with hidden tests, a cache that forgets the least recently used, with hidden tests, a state machine from a table, with hidden tests, a markdown table turned into CSV |
| 6 | taught hard kinds 12 of 23, two generations running | 27 (piece done) |
