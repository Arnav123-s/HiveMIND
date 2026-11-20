# The read of g55

Run [44728930517](https://github.com/Arnav123-s/HiveMIND/actions/runs/44728930517), recorded 2026-11-20 16:44: the body was **kept**. kept: 52 against 51; after 52 of 64 (easy 32 of 32, hard 20 of 32), before 51 of 64 (easy 32 of 32, hard 19 of 32) on 8 seeds; the fixed held-out exam: after 1 of 29, before 1 of 29

Written by the record job (`training/reads.py`), with nobody's hand. The rules are those of `docs/DECISIONS.md`.

## The numbers

| What is measured | g55 | g54 (last record) | the body before (same seeds) |
|---|---|---|---|
| Easy kinds passed | 32 of 32 | 32 of 32 | 32 of 32 |
| Hard kinds that have lessons | 20 of 25 | 18 of 25 | 19 of 25 |
| Hard kinds never practised (held out) | 0 of 10 kinds (1 of 29 tasks of the fixed exam; pulse 0 of 7) | 0 of 10 kinds (1 of 27 tasks of the fixed exam; pulse 0 of 7) | 0 of 10 kinds (1 of 29 tasks of the fixed exam; pulse 0 of 7) |
| Right at the first try (practice) | 0.65 (62 of 96) | 0.44 | - |
| Right at the first try, old kinds and K2's new kinds (practice) | old kinds 0.97 (33 of 34); new kinds (K2) 0.47 (29 of 62) | old kinds 0.60 (26 of 43); new kinds (K2) 0.30 (16 of 53) | - |
| Hours for one generation | 5.1 | 5.5 | - |
| Generations recorded with nobody's hand | 13 | 12 | - |
| Talk (the talk exam, out of 10; the bar is 8) | 8.5 of 10 (route 8 of 10, fact 9 of 10, earlier 9 of 10, time 8 of 10) | 8.0 of 10 (route 7 of 10, fact 10 of 10, earlier 8 of 10, time 7 of 10) | - |

## What members solved and what reached the user

| Exam arm | Scope | Graded for both, of tasks sat | Any recorded member passed | Final delivery passed | Member passed, delivery failed | Delivery passed, no recorded member passed |
|---|---|---:|---:|---:|---:|---:|
| before | all | 64 of 64 | 52 | 51 | 1 | 0 |
| before | hard | 32 of 32 | 20 | 19 | 1 | 0 |
| after | all | 64 of 64 | 54 | 52 | 2 | 0 |
| after | hard | 32 of 32 | 22 | 20 | 2 | 0 |

Counts compare the task checker on recorded member answers and their files with the same checker on the final delivery. Only tasks with a known result on both sides enter the last four columns.

## Which final deliveries changed

Comparable deliveries: 64 matched, from 64 tasks sat before and 64 after. Matching requires the same seat, task ID, prompt, kind and exam revision.

| Gained | Lost | Passed both | Failed both |
|---:|---:|---:|---:|
| 2 | 1 | 50 | 11 |

Lost: `h20000556_01` (the regions of a grid, with hidden tests).

Gained: `h20000553_03` (a server log's matching lines counted by class), `h20000554_00` (the percent change between two columns, rounded by a rule).

## The chain, by taught hard kind

lessons right by their own check -> rows that fit in training -> loss falls on lessons kept back -> the child alone writes it at the exam -> the body (two agree) passes it.

| kind | lessons right of made | rows left out | kept-back loss before -> after | gap to untaught (points) | child alone right | parent alone right | body right | body before |
|---|---|---|---|---|---|---|---|---|
| a fact from a site and a date sum on it | none made | 37 of 180 (11 skipped for memory) | 0.001 -> 0.001 | +54 | - | - | - | - |
| a join over two small tables | none made | 71 of 162 (33 skipped for memory) | not measured | not measured | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a log read and counted into a file | none made | 100 of 100 | 0.001 -> 0.000 | +94 | - | - | - | - |
| a module of two functions, with hidden tests | none made | 170 of 623 (58 skipped for memory) | 0.083 -> 0.088 | +46 | 3 of 4 | 1 of 1 | 3 of 3 | 3 of 3 |
| a class with rules, with hidden tests | none made | 83 of 280 (57 skipped for memory) | 0.041 -> 0.030 | +81 | - | - | - | - |
| a parser for a tiny language, with hidden tests | none made | 31 of 63 | 0.017 -> 0.013 | +74 | 0 of 1 | - | 0 of 1 | 0 of 1 |
| the regions of a grid, with hidden tests | none made | 142 of 220 (1 skipped for memory) | 0.014 -> 0.007 | +100 | 1 of 2 | - | 0 of 1 | 1 of 1 |
| a cache that forgets the least recently used, with hidden tests | 13 of 13 | 116 of 602 (52 skipped for memory) | 0.035 -> 0.037 | +45 | - | - | - | - |
| a state machine from a table, with hidden tests | 15 of 15 | 119 of 700 (107 skipped for memory) | 0.006 -> 0.004 | +93 | - | - | - | - |
| an order of tasks by their dependencies, with hidden tests | none made | 99 of 480 (97 skipped for memory) | 0.015 -> 0.013 | +66 | - | - | - | - |
| a number with given properties | none made | 0 of 240 (13 skipped for memory) | 0.170 -> 0.152 | +63 | 2 of 2 | - | 2 of 2 | 2 of 2 |
| a fact read and a date sum on it | none made | 28 of 60 (3 skipped for memory) | 0.001 -> 0.002 | -66 | 2 of 2 | - | 2 of 2 | 2 of 2 |
| the percent change between two columns, rounded by a rule | none made | 75 of 260 (71 skipped for memory) | 0.008 -> 0.005 | +92 | 3 of 3 | - | 3 of 3 | 2 of 3 |
| a table cut to one row a key, the latest kept | none made | 43 of 120 (20 skipped for memory) | 0.003 -> 0.003 | +52 | 2 of 2 | - | 2 of 2 | 2 of 2 |
| the blanks of a table filled by a rule | 12 of 12 | 25 of 540 (19 skipped for memory) | 0.004 -> 0.002 | +85 | - | - | - | - |
| a table grouped, each group's total and mean saved | none made | 149 of 440 (54 skipped for memory) | 0.003 -> 0.003 | +58 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| JSON lines read and counted by a nested field | none made | 102 of 102 | 0.022 -> 0.020 | +61 | - | - | - | - |
| a long table turned wide | none made | 36 of 160 (22 skipped for memory) | 0.002 -> 0.002 | +82 | - | - | - | - |
| several facts fetched and laid out as a file | none made | 19 of 120 (11 skipped for memory) | 0.001 -> 0.001 | +22 | - | - | - | - |
| a server log's matching lines counted by class | none made | not measured | 0.014 -> 0.015 | +42 | 1 of 2 | - | 1 of 1 | 0 of 1 |
| emails and phones found in a messy message | none made | 210 of 365 (41 skipped for memory) | 0.018 -> 0.022 | +33 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a markdown table turned into CSV | 12 of 12 | 0 of 440 (2 skipped for memory) | 0.003 -> 0.002 | +102 | - | - | - | - |
| names turned and sorted | none made | not measured | 0.015 -> 0.022 | +4 | 0 of 5 | - | 0 of 3 | 0 of 3 |
| a text split into sentences | none made | 56 of 423 (18 skipped for memory) | 0.027 -> 0.046 | -20 | 2 of 2 | - | 2 of 2 | 2 of 2 |
| the most frequent words of a text | none made | 41 of 303 (26 skipped for memory) | 0.049 -> 0.042 | +66 | - | - | - | - |
| walk a site over several pages | none made | not measured | 0.000 -> 0.000 | +14 | 2 of 2 | - | 2 of 2 | 2 of 2 |
| a fact found on the open web | none made | 26 of 120 (1 skipped for memory) | 0.002 -> 0.001 | +54 | - | - | - | - |

- rows left out: by kind, this generation's rows too long for a slice, of those the slices were given; in brackets those the memory guard skipped every time they came up. Rows not reached before the time was up are not left out
- gap: the kind's fall beside the mean fall of the kinds with no lesson this generation (scrape a page to a file: -52 points)
- child alone: the answers of this generation's cells (8) in the pulse; parent alone: those of their parents (g51code, g51code2, g51data, g51data2, g51sources, g51sources2, g51words, g51words2) in every arm. Two members sit a task, so these are few

How much the hive taught itself: of this generation's new rows, 321 from the hive's own checked practice and dreams (6 of them fix rows), 108 from the hand-written lesson makers (training/lessons.py, training/kinds/): the hive's own are 75% of those two. Rows trained on: not measured by source (each slice's record says the rows it trained by kind only, rows_by_kind; a field rows_by_source {source: trained} would measure it).

![The chain by kind](../progress/chain.svg)

## Hours

| step | minutes |
|---|---|
| practice | 43 |
| dream | 61 |
| gather | 9 |
| plan | 0 |
| train | 175 |
| join | 2 |
| merge | 3 |
| gate | 57 |
| record | 1 |

From the first job to the last: **5.14 hours** (the bar is 3). Each step runs from its first job's start to its last job's end; practice and dream run side by side.

Train slices lost: 0 of 20. Pulse seats whose server died: 0.

Colab: not used (notebook not there within the wait)

## Next piece

next piece: dose: one change a generation: raw reading and judged pairs off; slices weighed by steps; the one-line trial (rule 3: kept-back gap under 15 points, for 4 of 27 taught hard kinds: a fact read and a date sum on it, names turned and sorted, a text split into sentences, walk a site over several pages)

Rules that hold but whose piece is done on the board (docs/PLAN.md), so not named: rule 2 (T4); rule 6 (K1).

| # | the chain shows | holds for |
|---|---|---|
| 1 | lessons right under 8 of 12 | 0 |
| 2 | more than 1 row in 5 of the kind left out | 16: a fact from a site and a date sum on it, a join over two small tables, a log read and counted into a file, a module of two functions, with hidden tests, a class with rules, with hidden tests, a parser for a tiny language, with hidden tests, the regions of a grid, with hidden tests, an order of tasks by their dependencies, with hidden tests, a fact read and a date sum on it, the percent change between two columns, rounded by a rule, a table cut to one row a key, the latest kept, a table grouped, each group's total and mean saved, JSON lines read and counted by a nested field, a long table turned wide, emails and phones found in a messy message, a fact found on the open web (piece done) |
| 3 | kept-back gap under 15 points | 4: a fact read and a date sum on it, names turned and sorted, a text split into sentences, walk a site over several pages |
| 4 | gap 15 or more, the child alone right more often than its parent, the body not | 0 |
| 5 | gap 15 or more, the child alone not right | 1: a parser for a tiny language, with hidden tests |
| 6 | taught hard kinds 12 of 23, two generations running | 27 (piece done) |
