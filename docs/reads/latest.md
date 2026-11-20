# The read of g56

Run [44776442973](https://github.com/Arnav123-s/HiveMIND/actions/runs/44776442973), recorded 2026-11-20 22:19: the body was **dropped**. dropped: 48 against 51; after 48 of 64 (easy 32 of 32, hard 16 of 32), before 51 of 64 (easy 32 of 32, hard 19 of 32) on 8 seeds

Written by the record job (`training/reads.py`), with nobody's hand. The rules are those of `docs/DECISIONS.md`.

## The numbers

| What is measured | g56 | g55 (last record) | the body before (same seeds) |
|---|---|---|---|
| Easy kinds passed | 32 of 32 | 32 of 32 | 32 of 32 |
| Hard kinds that have lessons | 15 of 23 | 20 of 25 | 17 of 23 |
| Hard kinds never practised (held out) | 0 of 10 kinds (2 of 30 tasks of the fixed exam; pulse 1 of 9) | 0 of 10 kinds (1 of 29 tasks of the fixed exam; pulse 0 of 7) | 0 of 10 kinds (2 of 30 tasks of the fixed exam; pulse 2 of 9) |
| Right at the first try (practice) | 0.65 (62 of 96) | 0.65 | - |
| Right at the first try, old kinds and K2's new kinds (practice) | old kinds 0.88 (35 of 40); new kinds (K2) 0.48 (27 of 56) | old kinds 0.97 (33 of 34); new kinds (K2) 0.47 (29 of 62) | - |
| Hours for one generation | 5.6 | 5.1 | - |
| Generations recorded with nobody's hand | 14 | 13 | - |
| Talk (the talk exam, out of 10; the bar is 8) | 7.8 of 10 (route 8 of 10, fact 9 of 10, earlier 9 of 10, time 5 of 10) | 8.5 of 10 (route 8 of 10, fact 9 of 10, earlier 9 of 10, time 8 of 10) | - |

## What members solved and what reached the user

| Exam arm | Scope | Graded for both, of tasks sat | Any recorded member passed | Final delivery passed | Member passed, delivery failed | Delivery passed, no recorded member passed |
|---|---|---:|---:|---:|---:|---:|
| before | all | 64 of 64 | 52 | 51 | 1 | 0 |
| before | hard | 32 of 32 | 20 | 19 | 1 | 0 |
| after | all | 64 of 64 | 50 | 48 | 2 | 0 |
| after | hard | 32 of 32 | 18 | 16 | 2 | 0 |

Counts compare the task checker on recorded member answers and their files with the same checker on the final delivery. Only tasks with a known result on both sides enter the last four columns.

## Which final deliveries changed

Comparable deliveries: 64 matched, from 64 tasks sat before and 64 after. Matching requires the same seat, task ID, prompt, kind and exam revision.

| Gained | Lost | Passed both | Failed both |
|---:|---:|---:|---:|
| 1 | 4 | 47 | 12 |

Lost: `h20000562_01` (walk a site and count into a file), `h20000566_00` (a simulation followed step by step), `h20000567_01` (a module of two functions, with hidden tests), `h20000568_01` (a parser for a tiny language, with hidden tests).

Gained: `h20000562_00` (a file given in the task, edited to a specification).

## The chain, by taught hard kind

lessons right by their own check -> rows that fit in training -> loss falls on lessons kept back -> the child alone writes it at the exam -> the body (two agree) passes it.

| kind | lessons right of made | rows left out | kept-back loss before -> after | gap to untaught (points) | child alone right | parent alone right | body right | body before |
|---|---|---|---|---|---|---|---|---|
| a fact from a site and a date sum on it | none made | 34 of 126 (12 skipped for memory) | 0.001 -> 0.001 | -18 | - | - | - | - |
| a join over two small tables | none made | 37 of 56 (8 skipped for memory) | not measured | not measured | - | - | - | - |
| a log read and counted into a file | none made | 128 of 128 | 0.001 -> 0.001 | +45 | - | - | - | - |
| a module of two functions, with hidden tests | none made | 165 of 720 (81 skipped for memory) | 0.072 -> 0.085 | +31 | 1 of 3 | 1 of 1 | 1 of 2 | 2 of 2 |
| a class with rules, with hidden tests | none made | 115 of 368 (51 skipped for memory) | 0.041 -> 0.024 | +90 | 2 of 2 | - | 1 of 1 | 1 of 1 |
| a parser for a tiny language, with hidden tests | none made | 52 of 164 (5 skipped for memory) | 0.022 -> 0.009 | +109 | 1 of 4 | - | 1 of 3 | 2 of 3 |
| the regions of a grid, with hidden tests | 13 of 13 | 112 of 565 (97 skipped for memory) | 0.026 -> 0.015 | +91 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a cache that forgets the least recently used, with hidden tests | 12 of 12 | 135 of 550 (39 skipped for memory) | 0.036 -> 0.033 | +57 | 0 of 1 | - | 0 of 1 | 0 of 1 |
| a state machine from a table, with hidden tests | 13 of 13 | 101 of 522 (52 skipped for memory) | 0.006 -> 0.003 | +100 | 0 of 6 | 0 of 4 | 0 of 3 | 0 of 3 |
| an order of tasks by their dependencies, with hidden tests | none made | 254 of 561 (51 skipped for memory) | 0.015 -> 0.009 | +90 | - | - | - | - |
| a number with given properties | none made | 0 of 396 (14 skipped for memory) | 0.204 -> 0.181 | +61 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a fact read and a date sum on it | none made | 26 of 54 (1 skipped for memory) | 0.001 -> 0.003 | -202 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| the percent change between two columns, rounded by a rule | none made | 143 of 433 (51 skipped for memory) | 0.006 -> 0.006 | +54 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a table cut to one row a key, the latest kept | none made | 80 of 180 (31 skipped for memory) | 0.004 -> 0.003 | +82 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| the blanks of a table filled by a rule | 13 of 13 | 43 of 576 (20 skipped for memory) | 0.004 -> 0.003 | +69 | - | - | - | - |
| a table grouped, each group's total and mean saved | none made | 51 of 108 (14 skipped for memory) | 0.003 -> 0.003 | +50 | - | - | - | - |
| JSON lines read and counted by a nested field | none made | 93 of 93 | 0.023 -> 0.024 | +46 | 0 of 1 | - | 1 of 1 | 1 of 1 |
| a long table turned wide | none made | 71 of 252 (25 skipped for memory) | 0.002 -> 0.002 | +56 | - | - | - | - |
| several facts fetched and laid out as a file | none made | 20 of 180 (11 skipped for memory) | 0.001 -> 0.002 | -20 | 2 of 2 | - | 2 of 2 | 2 of 2 |
| a server log's matching lines counted by class | none made | 36 of 36 | 0.014 -> 0.011 | +71 | - | - | - | - |
| emails and phones found in a messy message | none made | 110 of 324 (47 skipped for memory) | 0.019 -> 0.019 | +49 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a markdown table turned into CSV | 14 of 14 | 0 of 540 (37 skipped for memory) | 0.003 -> 0.023 | -754 | 0 of 2 | - | 0 of 1 | 0 of 1 |
| names turned and sorted | 14 of 14 | 0 of 540 (22 skipped for memory) | 0.020 -> 0.029 | +5 | - | - | - | - |
| a text split into sentences | none made | 108 of 294 (15 skipped for memory) | 0.046 -> 0.039 | +64 | - | - | - | - |
| the most frequent words of a text | none made | 25 of 237 (22 skipped for memory) | 0.020 -> 0.017 | +63 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| walk a site over several pages | none made | not measured | 0.000 -> 0.001 | -41 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a fact found on the open web | none made | 25 of 72 (1 skipped for memory) | 0.003 -> 0.003 | +51 | 1 of 1 | - | 1 of 1 | 1 of 1 |

- rows left out: by kind, this generation's rows too long for a slice, of those the slices were given; in brackets those the memory guard skipped every time they came up. Rows not reached before the time was up are not left out
- gap: the kind's fall beside the mean fall of the kinds with no lesson this generation (operate a website, scrape a page to a file: -49 points)
- child alone: the answers of this generation's cells (8) in the pulse; parent alone: those of their parents (g53code, g53code2, g53data, g53data2, g53sources, g53sources2, g53words, g53words2) in every arm. Two members sit a task, so these are few

How much the hive taught itself: of this generation's new rows, 367 from the hive's own checked practice and dreams (4 of them fix rows), 206 from the hand-written lesson makers (training/lessons.py, training/kinds/): the hive's own are 64% of those two. Rows trained on: not measured by source (each slice's record says the rows it trained by kind only, rows_by_kind; a field rows_by_source {source: trained} would measure it).

![The chain by kind](../progress/chain.svg)

## Hours

| step | minutes |
|---|---|
| practice | 31 |
| dream | 59 |
| gather | 9 |
| plan | 0 |
| train | 205 |
| join | 4 |
| merge | 3 |
| gate | 53 |
| record | 1 |

From the first job to the last: **5.57 hours** (the bar is 3). Each step runs from its first job's start to its last job's end; practice and dream run side by side.

Train slices lost: 2 of 20. Pulse seats whose server died: 0.

Colab: not used (notebook not seen)

## Next piece

next piece: dose: one change a generation: raw reading and judged pairs off; slices weighed by steps; the one-line trial (rule 3: kept-back gap under 15 points, for 6 of 27 taught hard kinds: a fact from a site and a date sum on it, a fact read and a date sum on it, several facts fetched and laid out as a file, a markdown table turned into CSV, names turned and sorted, walk a site over several pages)

Rules that hold but whose piece is done on the board (docs/PLAN.md), so not named: rule 2 (T4); rule 6 (K1).

| # | the chain shows | holds for |
|---|---|---|
| 1 | lessons right under 8 of 12 | 0 |
| 2 | more than 1 row in 5 of the kind left out | 18: a fact from a site and a date sum on it, a join over two small tables, a log read and counted into a file, a module of two functions, with hidden tests, a class with rules, with hidden tests, a parser for a tiny language, with hidden tests, a cache that forgets the least recently used, with hidden tests, an order of tasks by their dependencies, with hidden tests, a fact read and a date sum on it, the percent change between two columns, rounded by a rule, a table cut to one row a key, the latest kept, a table grouped, each group's total and mean saved, JSON lines read and counted by a nested field, a long table turned wide, a server log's matching lines counted by class, emails and phones found in a messy message, a text split into sentences, a fact found on the open web (piece done) |
| 3 | kept-back gap under 15 points | 6: a fact from a site and a date sum on it, a fact read and a date sum on it, several facts fetched and laid out as a file, a markdown table turned into CSV, names turned and sorted, walk a site over several pages |
| 4 | gap 15 or more, the child alone right more often than its parent, the body not | 0 |
| 5 | gap 15 or more, the child alone not right | 3: a cache that forgets the least recently used, with hidden tests, a state machine from a table, with hidden tests, JSON lines read and counted by a nested field |
| 6 | taught hard kinds 12 of 23, two generations running | 27 (piece done) |
