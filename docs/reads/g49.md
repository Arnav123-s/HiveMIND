# The read of g49

Run [44428460725](https://github.com/Arnav123-s/HiveMIND/actions/runs/44428460725), recorded 2026-11-19 06:41: the body was **kept**. kept: 49 against 46; after 49 of 64 (easy 31 of 32, hard 18 of 32), before 46 of 64 (easy 30 of 32, hard 16 of 32) on 8 seeds; the fixed held-out exam: after 2 of 30, before 0 of 30

Written by the record job (`training/reads.py`), with nobody's hand. The rules are those of `docs/DECISIONS.md`.

## The numbers

| What is measured | g49 | g48 (last record) | the body before (same seeds) |
|---|---|---|---|
| Easy kinds passed | 31 of 32 | 32 of 32 | 30 of 32 |
| Hard kinds that have lessons | 16 of 22 | 21 of 28 | 16 of 22 |
| Hard kinds never practised (held out) | 0 of 10 kinds (2 of 30 tasks of the fixed exam; pulse 2 of 10) | 0 of 4 | 0 of 10 kinds (0 of 30 tasks of the fixed exam; pulse 0 of 10) |
| Right at the first try (practice) | 0.38 (36 of 96) | 0.40 | - |
| Right at the first try, old kinds and K2's new kinds (practice) | old kinds 0.65 (24 of 37); new kinds (K2) 0.20 (12 of 59) | old kinds 0.66 (31 of 47); new kinds (K2) 0.14 (7 of 49) | - |
| Hours for one generation | 6.3 | 5.7 | - |
| Generations recorded with nobody's hand | 7 | 6 | - |
| Talk (the talk exam, out of 10; the bar is 8) | 7.8 of 10 (route 8 of 10, fact 10 of 10, earlier 10 of 10, time 3 of 10) | 6.5 of 10 (route 8 of 10, fact 6 of 10, earlier 7 of 10, time 5 of 10) | - |

## What members solved and what reached the user

| Exam arm | Scope | Graded for both, of tasks sat | Any recorded member passed | Final delivery passed | Member passed, delivery failed | Delivery passed, no recorded member passed |
|---|---|---:|---:|---:|---:|---:|
| before | all | 64 of 64 | 55 | 46 | 9 | 0 |
| before | hard | 32 of 32 | 24 | 16 | 8 | 0 |
| after | all | 64 of 64 | 53 | 49 | 4 | 0 |
| after | hard | 32 of 32 | 22 | 18 | 4 | 0 |

Counts compare the task checker on recorded member answers and their files with the same checker on the final delivery. Only tasks with a known result on both sides enter the last four columns.

## Which final deliveries changed

Comparable deliveries: 64 matched, from 64 tasks sat before and 64 after. Matching requires the same seat, task ID, prompt, kind and exam revision.

| Gained | Lost | Passed both | Failed both |
|---:|---:|---:|---:|
| 3 | 0 | 46 | 15 |

Gained: `e20000497_01` (scrape a page to a file), `h20000491_00` (a simulation followed step by step), `h20000498_01` (rows kept within a range of dates written in several forms).

## The chain, by taught hard kind

lessons right by their own check -> rows that fit in training -> loss falls on lessons kept back -> the child alone writes it at the exam -> the body (two agree) passes it.

| kind | lessons right of made | rows left out | kept-back loss before -> after | gap to untaught (points) | child alone right | parent alone right | body right | body before |
|---|---|---|---|---|---|---|---|---|
| a fact from a site and a date sum on it | none made | 39 of 162 (17 skipped for memory) | 0.001 -> 0.001 | +202 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a join over two small tables | none made | 103 of 162 (19 skipped for memory) | not measured | not measured | 2 of 2 | - | 2 of 2 | 2 of 2 |
| a log read and counted into a file | none made | 119 of 126 (5 skipped for memory) | 0.002 -> 0.001 | +236 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a module of two functions, with hidden tests | none made | 94 of 216 (31 skipped for memory) | 0.070 -> 0.088 | +179 | 2 of 3 | - | 1 of 2 | 1 of 2 |
| a class with rules, with hidden tests | 12 of 12 | 120 of 432 (26 skipped for memory) | 0.190 -> 0.059 | +274 | - | - | - | - |
| a parser for a tiny language, with hidden tests | 13 of 13 | 150 of 540 (56 skipped for memory) | 0.415 -> 0.362 | +217 | - | - | - | - |
| the regions of a grid, with hidden tests | none made | 161 of 180 (1 skipped for memory) | 0.311 -> 0.195 | +242 | 0 of 2 | - | 0 of 1 | 0 of 1 |
| a cache that forgets the least recently used, with hidden tests | none made | not measured | 0.348 -> 0.282 | +224 | 1 of 2 | - | 0 of 1 | 0 of 1 |
| a state machine from a table, with hidden tests | 12 of 12 | 46 of 432 (101 skipped for memory) | 0.127 -> 0.040 | +273 | - | - | - | - |
| an order of tasks by their dependencies, with hidden tests | 13 of 13 | 70 of 526 (140 skipped for memory) | 0.119 -> 0.062 | +252 | - | - | - | - |
| a number with given properties | none made | 1 of 220 (19 skipped for memory) | 0.261 -> 0.259 | +205 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a fact read and a date sum on it | none made | 86 of 126 (2 skipped for memory) | 0.001 -> 0.001 | +202 | - | - | - | - |
| the percent change between two columns, rounded by a rule | 12 of 12 | 20 of 468 (19 skipped for memory) | 0.116 -> 0.048 | +263 | - | - | - | - |
| a table cut to one row a key, the latest kept | none made | 66 of 108 (12 skipped for memory) | 0.009 -> 0.004 | +261 | 2 of 2 | - | 2 of 2 | 2 of 2 |
| the blanks of a table filled by a rule | none made | 15 of 146 (37 skipped for memory) | 0.023 -> 0.017 | +231 | 2 of 2 | - | 2 of 2 | 2 of 2 |
| a table grouped, each group's total and mean saved | none made | 35 of 108 (19 skipped for memory) | 0.006 -> 0.004 | +241 | - | - | - | - |
| JSON lines read and counted by a nested field | none made | 17 of 18 (1 skipped for memory) | 0.033 -> 0.027 | +220 | - | - | - | - |
| a long table turned wide | none made | 22 of 72 (20 skipped for memory) | 0.009 -> 0.007 | +232 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| several facts fetched and laid out as a file | none made | 35 of 162 (15 skipped for memory) | 0.001 -> 0.002 | +183 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a server log's matching lines counted by class | 12 of 12 | 36 of 468 (10 skipped for memory) | 0.023 -> 0.018 | +225 | 2 of 4 | - | 1 of 2 | 1 of 2 |
| emails and phones found in a messy message | 12 of 12 | 268 of 432 (26 skipped for memory) | 0.090 -> 0.018 | +285 | 0 of 1 | - | 0 of 1 | 0 of 1 |
| a markdown table turned into CSV | none made | 1 of 74 (23 skipped for memory) | 0.013 -> 0.006 | +255 | - | - | - | - |
| names turned and sorted | 12 of 12 | 0 of 432 (5 skipped for memory) | 0.026 -> 0.023 | +216 | - | - | - | - |
| a text split into sentences | 12 of 12 | 29 of 468 (87 skipped for memory) | 0.042 -> 0.029 | +236 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| the most frequent words of a text | 12 of 12 | 25 of 504 (118 skipped for memory) | 0.057 -> 0.026 | +258 | 1 of 1 | - | 0 of 1 | 0 of 1 |
| walk a site over several pages | none made | not measured | 0.000 -> 0.001 | +170 | - | - | - | - |
| a fact found on the open web | none made | 25 of 180 (4 skipped for memory) | 0.003 -> 0.003 | +201 | 2 of 2 | - | 2 of 2 | 2 of 2 |

- rows left out: by kind, this generation's rows too long for a slice, of those the slices were given; in brackets those the memory guard skipped every time they came up. Rows not reached before the time was up are not left out
- gap: the kind's fall beside the mean fall of the kinds with no lesson this generation (scrape a page to a file: -205 points)
- child alone: the answers of this generation's cells (8) in the pulse; parent alone: those of their parents (g45words, g47code, g47code2, g47data, g47data2, g47sources, g47sources2, g47words) in every arm. Two members sit a task, so these are few
- parent alone: not measured; no parent sat a task of a taught hard kind (the pulse seats the trunk and the newest cells first; the paired gate's before arm seats the body before, parents among it)

How much the hive taught itself: of this generation's new rows, 192 from the hive's own checked practice and dreams (7 of them fix rows), 246 from the hand-written lesson makers (training/lessons.py, training/kinds/): the hive's own are 44% of those two. Rows trained on: not measured by source (each slice's record says the rows it trained by kind only, rows_by_kind; a field rows_by_source {source: trained} would measure it).

![The chain by kind](../progress/chain.svg)

## Hours

| step | minutes |
|---|---|
| practice | 66 |
| dream | 53 |
| gather | 10 |
| plan | 0 |
| train | 221 |
| join | 2 |
| merge | 3 |
| gate | 76 |
| record | 1 |

From the first job to the last: **6.32 hours** (the bar is 3). Each step runs from its first job's start to its last job's end; practice and dream run side by side.

Train slices lost: 2 of 20. Pulse seats whose server died: 0.

Colab: not used (notebook not there within the wait)

## Next piece

next piece: T3: read 10 of its programs first; then the key lines weigh more (rule 5: gap 15 or more, the child alone not right, for 2 of 27 taught hard kinds: the regions of a grid, with hidden tests, emails and phones found in a messy message)

Rules that hold but whose piece is done on the board (docs/PLAN.md), so not named: rule 2 (T4); rule 6 (K1).

| # | the chain shows | holds for |
|---|---|---|
| 1 | lessons right under 8 of 12 | 0 |
| 2 | more than 1 row in 5 of the kind left out | 14: a fact from a site and a date sum on it, a join over two small tables, a log read and counted into a file, a module of two functions, with hidden tests, a class with rules, with hidden tests, a parser for a tiny language, with hidden tests, the regions of a grid, with hidden tests, a fact read and a date sum on it, a table cut to one row a key, the latest kept, a table grouped, each group's total and mean saved, JSON lines read and counted by a nested field, a long table turned wide, several facts fetched and laid out as a file, emails and phones found in a messy message (piece done) |
| 3 | kept-back gap under 15 points | 0 |
| 4 | gap 15 or more, the child alone right more often than its parent, the body not | 0 |
| 5 | gap 15 or more, the child alone not right | 2: the regions of a grid, with hidden tests, emails and phones found in a messy message |
| 6 | taught hard kinds 12 of 23, two generations running | 27 (piece done) |
