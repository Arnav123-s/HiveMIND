# The read of g59

Run [44869053443](https://github.com/Arnav123-s/HiveMIND/actions/runs/44869053443), recorded 2026-11-21 11:47: the body was **kept**. kept: 49 against 47; after 49 of 64 (easy 32 of 32, hard 17 of 32), before 47 of 64 (easy 32 of 32, hard 15 of 32) on 8 seeds; the fixed held-out exam: after 2 of 28, before 3 of 28

Written by the record job (`training/reads.py`), with nobody's hand. The rules are those of `docs/DECISIONS.md`.

## The numbers

| What is measured | g59 | g57 (last record) | the body before (same seeds) |
|---|---|---|---|
| Easy kinds passed | 32 of 32 | 32 of 32 | 32 of 32 |
| Hard kinds that have lessons | 15 of 23 | 17 of 25 | 15 of 23 |
| Hard kinds never practised (held out) | 0 of 10 kinds (2 of 28 tasks of the fixed exam; pulse 2 of 9) | 1 of 10 kinds (3 of 29 tasks of the fixed exam; pulse 0 of 7) | 1 of 10 kinds (3 of 28 tasks of the fixed exam; pulse 0 of 9) |
| Right at the first try (practice) | 0.52 (50 of 96) | 0.72 | - |
| Right at the first try, old kinds and K2's new kinds (practice) | old kinds 0.89 (34 of 38); new kinds (K2) 0.28 (16 of 58) | old kinds 0.93 (43 of 46); new kinds (K2) 0.52 (26 of 50) | - |
| Hours for one generation | 6.4 | 6.7 | - |
| Generations recorded with nobody's hand | 16 | 15 | - |
| Talk (the talk exam, out of 10; the bar is 8) | 7.5 of 10 (route 7 of 10, fact 9 of 10, earlier 8 of 10, time 6 of 10) | 8.0 of 10 (route 8 of 10, fact 8 of 10, earlier 9 of 10, time 7 of 10) | - |

## What members solved and what reached the user

| Exam arm | Scope | Graded for both, of tasks sat | Any recorded member passed | Final delivery passed | Member passed, delivery failed | Delivery passed, no recorded member passed |
|---|---|---:|---:|---:|---:|---:|
| before | all | 64 of 64 | 49 | 47 | 2 | 0 |
| before | hard | 32 of 32 | 17 | 15 | 2 | 0 |
| after | all | 64 of 64 | 50 | 49 | 1 | 0 |
| after | hard | 32 of 32 | 18 | 17 | 1 | 0 |

Counts compare the task checker on recorded member answers and their files with the same checker on the final delivery. Only tasks with a known result on both sides enter the last four columns.

## Which final deliveries changed

Comparable deliveries: 64 matched, from 64 tasks sat before and 64 after. Matching requires the same seat, task ID, prompt, kind and exam revision.

| Gained | Lost | Passed both | Failed both |
|---:|---:|---:|---:|
| 3 | 1 | 46 | 14 |

Lost: `h20000593_01` (a module of two functions, with hidden tests).

Gained: `h20000592_02` (the top rows of each group ranked), `h20000592_03` (a server log's matching lines counted by class), `h20000597_03` (rows kept within a range of dates written in several forms).

## The chain, by taught hard kind

lessons right by their own check -> rows that fit in training -> loss falls on lessons kept back -> the child alone writes it at the exam -> the body (two agree) passes it.

| kind | lessons right of made | rows left out | kept-back loss before -> after | gap to untaught (points) | child alone right | parent alone right | body right | body before |
|---|---|---|---|---|---|---|---|---|
| a fact from a site and a date sum on it | none made | 40 of 162 (10 skipped for memory) | 0.000 -> 0.001 | +158 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a join over two small tables | none made | 141 of 162 (3 skipped for memory) | not measured | not measured | - | - | - | - |
| a log read and counted into a file | none made | 345 of 345 | 0.000 -> 0.001 | +117 | 2 of 2 | - | 2 of 2 | 2 of 2 |
| a module of two functions, with hidden tests | none made | 243 of 597 (49 skipped for memory) | 0.056 -> 0.066 | +165 | 1 of 4 | 1 of 1 | 1 of 2 | 2 of 2 |
| a class with rules, with hidden tests | 12 of 12 | 256 of 693 (38 skipped for memory) | 0.031 -> 0.009 | +253 | - | - | - | - |
| a parser for a tiny language, with hidden tests | 12 of 12 | 191 of 494 (9 skipped for memory) | 0.012 -> 0.008 | +213 | 1 of 1 | 1 of 2 | 1 of 1 | 1 of 1 |
| the regions of a grid, with hidden tests | none made | 237 of 417 (12 skipped for memory) | 0.007 -> 0.004 | +225 | 2 of 2 | - | 2 of 2 | 2 of 2 |
| a cache that forgets the least recently used, with hidden tests | 13 of 13 | 249 of 702 (35 skipped for memory) | 0.031 -> 0.019 | +222 | 0 of 2 | - | 0 of 2 | 0 of 2 |
| a state machine from a table, with hidden tests | 12 of 12 | 107 of 468 (65 skipped for memory) | 0.003 -> 0.002 | +222 | 0 of 3 | - | 0 of 2 | 0 of 2 |
| an order of tasks by their dependencies, with hidden tests | none made | 119 of 343 (88 skipped for memory) | 0.013 -> 0.009 | +215 | 2 of 2 | 1 of 1 | 2 of 2 | 2 of 2 |
| a number with given properties | none made | 0 of 144 (11 skipped for memory) | 0.157 -> 0.130 | +200 | - | - | - | - |
| a fact read and a date sum on it | none made | 29 of 144 (2 skipped for memory) | 0.001 -> 0.001 | +167 | - | - | - | - |
| the percent change between two columns, rounded by a rule | none made | 103 of 234 (38 skipped for memory) | 0.004 -> 0.003 | +216 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a table cut to one row a key, the latest kept | none made | 66 of 108 (12 skipped for memory) | 0.003 -> 0.003 | +170 | - | - | - | - |
| the blanks of a table filled by a rule | 13 of 13 | 96 of 648 (13 skipped for memory) | 0.002 -> 0.002 | +192 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a table grouped, each group's total and mean saved | none made | 111 of 180 (12 skipped for memory) | 0.003 -> 0.005 | +86 | - | - | - | - |
| JSON lines read and counted by a nested field | 13 of 13 | 165 of 615 (3 skipped for memory) | 0.002 -> 0.001 | +219 | - | - | - | - |
| a long table turned wide | none made | 76 of 144 (16 skipped for memory) | 0.001 -> 0.002 | +178 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| several facts fetched and laid out as a file | none made | 22 of 180 (10 skipped for memory) | 0.001 -> 0.001 | +175 | - | - | - | - |
| a server log's matching lines counted by class | 12 of 12 | 18 of 450 (3 skipped for memory) | 0.013 -> 0.014 | +180 | 2 of 2 | 0 of 2 | 1 of 1 | 0 of 1 |
| emails and phones found in a messy message | none made | 231 of 432 (45 skipped for memory) | 0.019 -> 0.014 | +209 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a markdown table turned into CSV | 13 of 13 | 0 of 450 (14 skipped for memory) | 0.732 -> 0.112 | +268 | 0 of 1 | - | 0 of 1 | 0 of 1 |
| names turned and sorted | 12 of 12 | 0 of 396 (1 skipped for memory) | 0.019 -> 0.020 | +177 | 0 of 2 | 0 of 2 | 0 of 2 | 0 of 2 |
| a text split into sentences | none made | 37 of 110 (3 skipped for memory) | 0.042 -> 0.036 | +196 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| the most frequent words of a text | none made | 33 of 236 (13 skipped for memory) | 0.016 -> 0.014 | +197 | - | - | - | - |
| walk a site over several pages | none made | not measured | 0.000 -> 0.001 | -62 | - | - | - | - |
| a fact found on the open web | none made | 29 of 180 | 0.001 -> 0.007 | -320 | - | - | - | - |

- rows left out: by kind, this generation's rows too long for a slice, of those the slices were given; in brackets those the memory guard skipped every time they came up. Rows not reached before the time was up are not left out
- gap: the kind's fall beside the mean fall of the kinds with no lesson this generation (operate a website, scrape a page to a file: -183 points)
- child alone: the answers of this generation's cells (8) in the pulse; parent alone: those of their parents (g55code, g55code2, g55data, g55data2, g55sources, g55sources2, g55words, g55words2) in every arm. Two members sit a task, so these are few

How much the hive taught itself: of this generation's new rows, 361 from the hive's own checked practice and dreams (3 of them fix rows), 278 from the hand-written lesson makers (training/lessons.py, training/kinds/): the hive's own are 56% of those two. Rows trained on: not measured by source (each slice's record says the rows it trained by kind only, rows_by_kind; a field rows_by_source {source: trained} would measure it).

![The chain by kind](../progress/chain.svg)

## Hours

| step | minutes |
|---|---|
| practice | 52 |
| dream | 63 |
| gather | 6 |
| plan | 0 |
| train | 217 |
| join | 2 |
| merge | 2 |
| gate | 89 |
| record | 1 |

From the first job to the last: **6.42 hours** (the bar is 3). Each step runs from its first job's start to its last job's end; practice and dream run side by side.

Train slices lost: 2 of 20. Pulse seats whose server died: 0.

Colab: not used (notebook not there within the wait)

## Next piece

next piece: T3: read 10 of its programs first; then the key lines weigh more (rule 5: gap 15 or more, the child alone not right, for 4 of 27 taught hard kinds: a cache that forgets the least recently used, with hidden tests, a state machine from a table, with hidden tests, a markdown table turned into CSV, names turned and sorted)

Rules that hold but whose piece is done on the board (docs/PLAN.md), so not named: rule 2 (T4); rule 4 (R1); rule 6 (K1).

| # | the chain shows | holds for |
|---|---|---|
| 1 | lessons right under 8 of 12 | 0 |
| 2 | more than 1 row in 5 of the kind left out | 18: a fact from a site and a date sum on it, a join over two small tables, a log read and counted into a file, a module of two functions, with hidden tests, a class with rules, with hidden tests, a parser for a tiny language, with hidden tests, the regions of a grid, with hidden tests, a cache that forgets the least recently used, with hidden tests, a state machine from a table, with hidden tests, an order of tasks by their dependencies, with hidden tests, a fact read and a date sum on it, the percent change between two columns, rounded by a rule, a table cut to one row a key, the latest kept, a table grouped, each group's total and mean saved, JSON lines read and counted by a nested field, a long table turned wide, emails and phones found in a messy message, a text split into sentences (piece done) |
| 3 | kept-back gap under 15 points | 2: walk a site over several pages, a fact found on the open web |
| 4 | gap 15 or more, the child alone right more often than its parent, the body not | 1: a parser for a tiny language, with hidden tests (piece done) |
| 5 | gap 15 or more, the child alone not right | 4: a cache that forgets the least recently used, with hidden tests, a state machine from a table, with hidden tests, a markdown table turned into CSV, names turned and sorted |
| 6 | taught hard kinds 12 of 23, two generations running | 27 (piece done) |
