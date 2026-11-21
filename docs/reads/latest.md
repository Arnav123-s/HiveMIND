# The read of g57

Run [44828061048](https://github.com/Arnav123-s/HiveMIND/actions/runs/44828061048), recorded 2026-11-21 05:03: the body was **kept**. kept: 49 against 48; after 49 of 64 (easy 32 of 32, hard 17 of 32), before 48 of 64 (easy 32 of 32, hard 16 of 32) on 8 seeds; the fixed held-out exam: after 3 of 29, before 1 of 29

Written by the record job (`training/reads.py`), with nobody's hand. The rules are those of `docs/DECISIONS.md`.

## The numbers

| What is measured | g57 | g56 (last record) | the body before (same seeds) |
|---|---|---|---|
| Easy kinds passed | 32 of 32 | 32 of 32 | 32 of 32 |
| Hard kinds that have lessons | 17 of 25 | 15 of 23 | 16 of 25 |
| Hard kinds never practised (held out) | 1 of 10 kinds (3 of 29 tasks of the fixed exam; pulse 0 of 7) | 0 of 10 kinds (2 of 30 tasks of the fixed exam; pulse 1 of 9) | 0 of 10 kinds (1 of 29 tasks of the fixed exam; pulse 0 of 7) |
| Right at the first try (practice) | 0.72 (69 of 96) | 0.65 | - |
| Right at the first try, old kinds and K2's new kinds (practice) | old kinds 0.93 (43 of 46); new kinds (K2) 0.52 (26 of 50) | old kinds 0.88 (35 of 40); new kinds (K2) 0.48 (27 of 56) | - |
| Hours for one generation | 6.7 | 5.6 | - |
| Generations recorded with nobody's hand | 15 | 14 | - |
| Talk (the talk exam, out of 10; the bar is 8) | 8.0 of 10 (route 8 of 10, fact 8 of 10, earlier 9 of 10, time 7 of 10) | 7.8 of 10 (route 8 of 10, fact 9 of 10, earlier 9 of 10, time 5 of 10) | - |

## What members solved and what reached the user

| Exam arm | Scope | Graded for both, of tasks sat | Any recorded member passed | Final delivery passed | Member passed, delivery failed | Delivery passed, no recorded member passed |
|---|---|---:|---:|---:|---:|---:|
| before | all | 64 of 64 | 51 | 48 | 3 | 0 |
| before | hard | 32 of 32 | 19 | 16 | 3 | 0 |
| after | all | 64 of 64 | 50 | 49 | 1 | 0 |
| after | hard | 32 of 32 | 18 | 17 | 1 | 0 |

Counts compare the task checker on recorded member answers and their files with the same checker on the final delivery. Only tasks with a known result on both sides enter the last four columns.

## Which final deliveries changed

Comparable deliveries: 64 matched, from 64 tasks sat before and 64 after. Matching requires the same seat, task ID, prompt, kind and exam revision.

| Gained | Lost | Passed both | Failed both |
|---:|---:|---:|---:|
| 2 | 1 | 47 | 14 |

Lost: `h20000573_01` (a text split into sentences).

Gained: `h20000571_03` (a cache that forgets the least recently used, with hidden tests), `h20000577_00` (a class with rules, with hidden tests).

## The chain, by taught hard kind

lessons right by their own check -> rows that fit in training -> loss falls on lessons kept back -> the child alone writes it at the exam -> the body (two agree) passes it.

| kind | lessons right of made | rows left out | kept-back loss before -> after | gap to untaught (points) | child alone right | parent alone right | body right | body before |
|---|---|---|---|---|---|---|---|---|
| a fact from a site and a date sum on it | none made | 38 of 112 (13 skipped for memory) | 0.001 -> 0.001 | +88 | - | - | - | - |
| a join over two small tables | none made | 83 of 114 (1 skipped for memory) | not measured | not measured | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a log read and counted into a file | none made | 18 of 18 | 0.001 -> 0.001 | +126 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a module of two functions, with hidden tests | none made | 164 of 450 (53 skipped for memory) | 0.044 -> 0.057 | +104 | - | - | - | - |
| a class with rules, with hidden tests | none made | 150 of 325 (42 skipped for memory) | 0.043 -> 0.034 | +155 | 1 of 1 | - | 1 of 1 | 0 of 1 |
| a parser for a tiny language, with hidden tests | 12 of 12 | 192 of 482 (34 skipped for memory) | 0.024 -> 0.012 | +187 | 0 of 1 | - | 0 of 1 | 0 of 1 |
| the regions of a grid, with hidden tests | 13 of 13 | 132 of 581 (142 skipped for memory) | 0.029 -> 0.021 | +161 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a cache that forgets the least recently used, with hidden tests | 12 of 12 | 245 of 553 (28 skipped for memory) | 0.037 -> 0.025 | +166 | 1 of 2 | - | 1 of 2 | 0 of 2 |
| a state machine from a table, with hidden tests | 14 of 14 | 128 of 512 (92 skipped for memory) | 0.006 -> 0.005 | +152 | 0 of 2 | - | 0 of 1 | 0 of 1 |
| an order of tasks by their dependencies, with hidden tests | none made | 162 of 405 (76 skipped for memory) | 0.016 -> 0.013 | +159 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a number with given properties | none made | 0 of 192 (21 skipped for memory) | 0.203 -> 0.185 | +144 | 2 of 2 | - | 2 of 2 | 2 of 2 |
| a fact read and a date sum on it | none made | 27 of 32 | 0.001 -> 0.002 | +4 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| the percent change between two columns, rounded by a rule | none made | 124 of 275 (50 skipped for memory) | 0.006 -> 0.006 | +139 | 2 of 2 | - | 2 of 2 | 2 of 2 |
| a table cut to one row a key, the latest kept | none made | 48 of 96 (15 skipped for memory) | 0.004 -> 0.003 | +167 | 3 of 3 | - | 3 of 3 | 3 of 3 |
| the blanks of a table filled by a rule | none made | 69 of 114 (9 skipped for memory) | 0.004 -> 0.005 | +109 | 0 of 4 | 0 of 2 | 0 of 2 | 0 of 2 |
| a table grouped, each group's total and mean saved | none made | 130 of 208 (18 skipped for memory) | 0.003 -> 0.003 | +145 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| JSON lines read and counted by a nested field | none made | 18 of 18 | 0.023 -> 0.028 | +115 | - | - | - | - |
| a long table turned wide | none made | 72 of 192 (29 skipped for memory) | 0.002 -> 0.003 | +100 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| several facts fetched and laid out as a file | none made | 24 of 192 (12 skipped for memory) | 0.001 -> 0.001 | +120 | - | - | - | - |
| a server log's matching lines counted by class | none made | 80 of 80 | 0.014 -> 0.013 | +142 | - | - | - | - |
| emails and phones found in a messy message | none made | 86 of 128 (17 skipped for memory) | 0.021 -> 0.014 | +167 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a markdown table turned into CSV | 14 of 14 | 0 of 368 (22 skipped for memory) | 1.248 -> 0.235 | +216 | 0 of 1 | - | 0 of 1 | 0 of 1 |
| names turned and sorted | 12 of 12 | 0 of 384 (9 skipped for memory) | 0.021 -> 0.028 | +102 | 1 of 2 | - | 0 of 1 | 0 of 1 |
| a text split into sentences | none made | 38 of 134 (19 skipped for memory) | 0.046 -> 0.045 | +138 | 0 of 1 | - | 0 of 1 | 1 of 1 |
| the most frequent words of a text | none made | 32 of 210 (25 skipped for memory) | 0.021 -> 0.018 | +147 | - | - | - | - |
| walk a site over several pages | none made | not measured | 0.000 -> 0.001 | -2 | - | - | - | - |
| a fact found on the open web | none made | 25 of 224 (4 skipped for memory) | 0.003 -> 0.003 | +120 | - | - | - | - |

- rows left out: by kind, this generation's rows too long for a slice, of those the slices were given; in brackets those the memory guard skipped every time they came up. Rows not reached before the time was up are not left out
- gap: the kind's fall beside the mean fall of the kinds with no lesson this generation (operate a website, scrape a page to a file: -135 points)
- child alone: the answers of this generation's cells (8) in the pulse; parent alone: those of their parents (g53code, g53code2, g53data, g53data2, g53sources, g53sources2, g53words, g53words2) in every arm. Two members sit a task, so these are few

How much the hive taught itself: of this generation's new rows, 322 from the hive's own checked practice and dreams (5 of them fix rows), 203 from the hand-written lesson makers (training/lessons.py, training/kinds/): the hive's own are 61% of those two. Rows trained on: not measured by source (each slice's record says the rows it trained by kind only, rows_by_kind; a field rows_by_source {source: trained} would measure it).

![The chain by kind](../progress/chain.svg)

## Hours

| step | minutes |
|---|---|
| practice | 26 |
| dream | 59 |
| gather | 4 |
| plan | 0 |
| train | 205 |
| join | 9 |
| merge | 3 |
| gate | 71 |
| record | 1 |

From the first job to the last: **6.72 hours** (the bar is 3). Each step runs from its first job's start to its last job's end; practice and dream run side by side.

Train slices lost: 4 of 20. Pulse seats whose server died: 0.

Colab: not used (notebook not there within the wait)

## Next piece

next piece: T3: read 10 of its programs first; then the key lines weigh more (rule 5: gap 15 or more, the child alone not right, for 5 of 27 taught hard kinds: a parser for a tiny language, with hidden tests, a state machine from a table, with hidden tests, the blanks of a table filled by a rule, a markdown table turned into CSV, a text split into sentences)

Rules that hold but whose piece is done on the board (docs/PLAN.md), so not named: rule 2 (T4); rule 6 (K1).

| # | the chain shows | holds for |
|---|---|---|
| 1 | lessons right under 8 of 12 | 0 |
| 2 | more than 1 row in 5 of the kind left out | 20: a fact from a site and a date sum on it, a join over two small tables, a log read and counted into a file, a module of two functions, with hidden tests, a class with rules, with hidden tests, a parser for a tiny language, with hidden tests, the regions of a grid, with hidden tests, a cache that forgets the least recently used, with hidden tests, a state machine from a table, with hidden tests, an order of tasks by their dependencies, with hidden tests, a fact read and a date sum on it, the percent change between two columns, rounded by a rule, a table cut to one row a key, the latest kept, the blanks of a table filled by a rule, a table grouped, each group's total and mean saved, JSON lines read and counted by a nested field, a long table turned wide, a server log's matching lines counted by class, emails and phones found in a messy message, a text split into sentences (piece done) |
| 3 | kept-back gap under 15 points | 2: a fact read and a date sum on it, walk a site over several pages |
| 4 | gap 15 or more, the child alone right more often than its parent, the body not | 0 |
| 5 | gap 15 or more, the child alone not right | 5: a parser for a tiny language, with hidden tests, a state machine from a table, with hidden tests, the blanks of a table filled by a rule, a markdown table turned into CSV, a text split into sentences |
| 6 | taught hard kinds 12 of 23, two generations running | 27 (piece done) |
