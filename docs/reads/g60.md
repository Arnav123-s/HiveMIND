# The read of g60

Run [44900825077](https://github.com/Arnav123-s/HiveMIND/actions/runs/44900825077), recorded 2026-11-21 18:04: the body was **kept**. kept: 48 against 47; after 48 of 64 (easy 30 of 32, hard 18 of 32), before 47 of 64 (easy 30 of 32, hard 17 of 32) on 8 seeds; the fixed held-out exam: after 1 of 30, before 2 of 30

Written by the record job (`training/reads.py`), with nobody's hand. The rules are those of `docs/DECISIONS.md`.

## The numbers

| What is measured | g60 | g59 (last record) | the body before (same seeds) |
|---|---|---|---|
| Easy kinds passed | 30 of 32 | 32 of 32 | 30 of 32 |
| Hard kinds that have lessons | 18 of 23 | 15 of 23 | 17 of 23 |
| Hard kinds never practised (held out) | 0 of 10 kinds (1 of 30 tasks of the fixed exam; pulse 0 of 9) | 0 of 10 kinds (2 of 28 tasks of the fixed exam; pulse 2 of 9) | 0 of 10 kinds (2 of 30 tasks of the fixed exam; pulse 0 of 9) |
| Right at the first try (practice) | 0.53 (51 of 96) | 0.52 | - |
| Right at the first try, old kinds and K2's new kinds (practice) | old kinds 0.92 (33 of 36); new kinds (K2) 0.30 (18 of 60) | old kinds 0.89 (34 of 38); new kinds (K2) 0.28 (16 of 58) | - |
| Hours for one generation | 6.3 | 6.4 | - |
| Generations recorded with nobody's hand | 17 | 16 | - |
| Talk (the talk exam, out of 10; the bar is 8) | 8.2 of 10 (route 8 of 10, fact 9 of 10, earlier 9 of 10, time 7 of 10) | 7.5 of 10 (route 7 of 10, fact 9 of 10, earlier 8 of 10, time 6 of 10) | - |

## What members solved and what reached the user

| Exam arm | Scope | Graded for both, of tasks sat | Any recorded member passed | Final delivery passed | Member passed, delivery failed | Delivery passed, no recorded member passed |
|---|---|---:|---:|---:|---:|---:|
| before | all | 64 of 64 | 53 | 47 | 6 | 0 |
| before | hard | 32 of 32 | 22 | 17 | 5 | 0 |
| after | all | 64 of 64 | 50 | 48 | 2 | 0 |
| after | hard | 32 of 32 | 19 | 18 | 1 | 0 |

Counts compare the task checker on recorded member answers and their files with the same checker on the final delivery. Only tasks with a known result on both sides enter the last four columns.

## Which final deliveries changed

Comparable deliveries: 64 matched, from 64 tasks sat before and 64 after. Matching requires the same seat, task ID, prompt, kind and exam revision.

| Gained | Lost | Passed both | Failed both |
|---:|---:|---:|---:|
| 2 | 1 | 46 | 15 |

Lost: `e20000607_01` (scrape a page to a file).

Gained: `e20000607_02` (a thing to know), `h20000603_01` (a parser for a tiny language, with hidden tests).

## The chain, by taught hard kind

lessons right by their own check -> rows that fit in training -> loss falls on lessons kept back -> the child alone writes it at the exam -> the body (two agree) passes it.

| kind | lessons right of made | rows left out | kept-back loss before -> after | gap to untaught (points) | child alone right | parent alone right | body right | body before |
|---|---|---|---|---|---|---|---|---|
| a fact from a site and a date sum on it | none made | 26 of 240 (17 skipped for memory) | 0.000 -> 0.001 | +36 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a join over two small tables | none made | 107 of 195 (22 skipped for memory) | not measured | not measured | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a log read and counted into a file | none made | 210 of 240 (16 skipped for memory) | 0.001 -> 0.001 | +103 | - | - | - | - |
| a module of two functions, with hidden tests | none made | 122 of 499 (85 skipped for memory) | 0.120 -> 0.132 | +73 | 2 of 2 | - | 2 of 2 | 2 of 2 |
| a class with rules, with hidden tests | 12 of 12 | 156 of 656 (89 skipped for memory) | 0.046 -> 0.033 | +111 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a parser for a tiny language, with hidden tests | 12 of 12 | 162 of 688 (58 skipped for memory) | 0.010 -> 0.005 | +128 | 1 of 2 | - | 1 of 2 | 0 of 2 |
| the regions of a grid, with hidden tests | 12 of 12 | 163 of 608 (102 skipped for memory) | 0.011 -> 0.003 | +152 | 2 of 3 | - | 2 of 2 | 2 of 2 |
| a cache that forgets the least recently used, with hidden tests | 12 of 12 | 158 of 496 (51 skipped for memory) | 0.094 -> 0.041 | +138 | - | - | - | - |
| a state machine from a table, with hidden tests | 13 of 13 | 60 of 432 (76 skipped for memory) | 0.005 -> 0.003 | +123 | 0 of 2 | 0 of 1 | 0 of 1 | 0 of 1 |
| an order of tasks by their dependencies, with hidden tests | 12 of 12 | 83 of 592 (150 skipped for memory) | 0.012 -> 0.010 | +98 | 0 of 2 | 0 of 2 | 0 of 1 | 0 of 1 |
| a number with given properties | none made | 0 of 480 (5 skipped for memory) | 0.172 -> 0.151 | +94 | - | - | - | - |
| a fact read and a date sum on it | none made | 20 of 80 (5 skipped for memory) | 0.001 -> 0.007 | -704 | - | - | - | - |
| the percent change between two columns, rounded by a rule | none made | 49 of 146 (48 skipped for memory) | 0.005 -> 0.002 | +135 | - | - | - | - |
| a table cut to one row a key, the latest kept | none made | 24 of 64 (11 skipped for memory) | 0.002 -> 0.008 | -177 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| the blanks of a table filled by a rule | 12 of 12 | 89 of 592 (29 skipped for memory) | 0.002 -> 0.002 | +104 | - | - | - | - |
| a table grouped, each group's total and mean saved | none made | 31 of 96 (19 skipped for memory) | 0.002 -> 0.001 | +119 | - | - | - | - |
| JSON lines read and counted by a nested field | 13 of 13 | 103 of 562 (13 skipped for memory) | 0.001 -> 0.001 | +145 | - | - | - | - |
| a long table turned wide | none made | 24 of 64 (20 skipped for memory) | 0.002 -> 0.001 | +104 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| several facts fetched and laid out as a file | none made | 14 of 192 (11 skipped for memory) | 0.001 -> 0.006 | -412 | - | - | - | - |
| a server log's matching lines counted by class | 13 of 13 | 224 of 624 (10 skipped for memory) | 0.013 -> 0.015 | +63 | - | - | - | - |
| emails and phones found in a messy message | none made | 30 of 128 (22 skipped for memory) | 0.017 -> 0.018 | +73 | 2 of 2 | - | 2 of 2 | 2 of 2 |
| a markdown table turned into CSV | 14 of 14 | 0 of 480 (16 skipped for memory) | 0.062 -> 0.002 | +178 | 1 of 2 | - | 0 of 1 | 0 of 1 |
| names turned and sorted | 14 of 14 | 0 of 480 (17 skipped for memory) | 0.027 -> 0.030 | +70 | 0 of 1 | - | 0 of 1 | 0 of 1 |
| a text split into sentences | none made | 52 of 224 (18 skipped for memory) | 0.043 -> 0.038 | +94 | - | - | - | - |
| the most frequent words of a text | none made | 18 of 240 (23 skipped for memory) | 0.021 -> 0.025 | +61 | 2 of 2 | - | 2 of 2 | 2 of 2 |
| walk a site over several pages | none made | not measured | 0.000 -> 0.000 | +60 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a fact found on the open web | none made | 61 of 325 (14 skipped for memory) | 0.002 -> 0.003 | +22 | 3 of 3 | - | 3 of 3 | 3 of 3 |

- rows left out: by kind, this generation's rows too long for a slice, of those the slices were given; in brackets those the memory guard skipped every time they came up. Rows not reached before the time was up are not left out
- gap: the kind's fall beside the mean fall of the kinds with no lesson this generation (operate a website, scrape a page to a file: -82 points)
- child alone: the answers of this generation's cells (8) in the pulse; parent alone: those of their parents (g57code, g57code2, g57data, g57data2, g57sources, g57sources2, g57words, g57words2) in every arm. Two members sit a task, so these are few

How much the hive taught itself: of this generation's new rows, 342 from the hive's own checked practice and dreams (5 of them fix rows), 330 from the hand-written lesson makers (training/lessons.py, training/kinds/): the hive's own are 51% of those two. Rows trained on: not measured by source (each slice's record says the rows it trained by kind only, rows_by_kind; a field rows_by_source {source: trained} would measure it).

![The chain by kind](../progress/chain.svg)

## Hours

| step | minutes |
|---|---|
| practice | 36 |
| dream | 60 |
| gather | 10 |
| plan | 0 |
| train | 220 |
| join | 2 |
| merge | 2 |
| gate | 81 |
| record | 1 |

From the first job to the last: **6.26 hours** (the bar is 3). Each step runs from its first job's start to its last job's end; practice and dream run side by side.

Train slices lost: 4 of 20. Pulse seats whose server died: 0.

Colab: not used (notebook not there within the wait)

## Next piece

next piece: dose: one change a generation: raw reading and judged pairs off; slices weighed by steps; the one-line trial (rule 3: kept-back gap under 15 points, for 3 of 27 taught hard kinds: a fact read and a date sum on it, a table cut to one row a key, the latest kept, several facts fetched and laid out as a file)

Rules that hold but whose piece is done on the board (docs/PLAN.md), so not named: rule 2 (T4); rule 6 (K1).

| # | the chain shows | holds for |
|---|---|---|
| 1 | lessons right under 8 of 12 | 0 |
| 2 | more than 1 row in 5 of the kind left out | 15: a join over two small tables, a log read and counted into a file, a module of two functions, with hidden tests, a class with rules, with hidden tests, a parser for a tiny language, with hidden tests, the regions of a grid, with hidden tests, a cache that forgets the least recently used, with hidden tests, a fact read and a date sum on it, the percent change between two columns, rounded by a rule, a table cut to one row a key, the latest kept, a table grouped, each group's total and mean saved, a long table turned wide, a server log's matching lines counted by class, emails and phones found in a messy message, a text split into sentences (piece done) |
| 3 | kept-back gap under 15 points | 3: a fact read and a date sum on it, a table cut to one row a key, the latest kept, several facts fetched and laid out as a file |
| 4 | gap 15 or more, the child alone right more often than its parent, the body not | 0 |
| 5 | gap 15 or more, the child alone not right | 3: a state machine from a table, with hidden tests, an order of tasks by their dependencies, with hidden tests, names turned and sorted |
| 6 | taught hard kinds 12 of 23, two generations running | 27 (piece done) |
