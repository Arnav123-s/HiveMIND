# The read of g48

Run [44371926721](https://github.com/Arnav123-s/HiveMIND/actions/runs/44371926721), recorded 2026-11-19 00:22: the body was **kept**. kept: 53 against 53; after 53 of 64 (easy 32 of 32, hard 21 of 32), before 53 of 64 (easy 32 of 32, hard 21 of 32) on 8 seeds

Written by the record job (`training/reads.py`), with nobody's hand. The rules are those of `docs/DECISIONS.md`.

## The numbers

| What is measured | g48 | g47 (last record) | the body before (same seeds) |
|---|---|---|---|
| Easy kinds passed | 32 of 32 | 31 of 32 | 32 of 32 |
| Hard kinds that have lessons | 21 of 28 | 16 of 25 | 20 of 28 |
| Hard kinds never practised (held out) | 0 of 4 | 0 of 7 | 1 of 4 |
| Right at the first try (practice) | 0.40 (38 of 96) | 0.39 | - |
| Right at the first try, old kinds and K2's new kinds (practice) | old kinds 0.66 (31 of 47); new kinds (K2) 0.14 (7 of 49) | - | - |
| Hours for one generation | 5.7 | 5.2 | - |
| Generations recorded with nobody's hand | 6 | 5 | - |
| Talk (the talk exam, out of 10; the bar is 8) | 6.5 of 10 (route 8 of 10, fact 6 of 10, earlier 7 of 10, time 5 of 10) | 6.2 of 10 (route 6 of 10, fact 7 of 10, earlier 7 of 10, time 5 of 10) | - |

## What members solved and what reached the user

| Exam arm | Scope | Graded for both, of tasks sat | Any recorded member passed | Final delivery passed | Member passed, delivery failed | Delivery passed, no recorded member passed |
|---|---|---:|---:|---:|---:|---:|
| before | all | unrecorded | – | – | – | – |
| before | hard | unrecorded | – | – | – | – |
| after | all | unrecorded | – | – | – | – |
| after | hard | unrecorded | – | – | – | – |

Counts compare the task checker on recorded member answers and their files with the same checker on the final delivery. Only tasks with a known result on both sides enter the last four columns.

## Which final deliveries changed

Individual before/after comparisons were not recorded.

## The chain, by taught hard kind

lessons right by their own check -> rows that fit in training -> loss falls on lessons kept back -> the child alone writes it at the exam -> the body (two agree) passes it.

| kind | lessons right of made | rows left out | kept-back loss before -> after | gap to untaught (points) | child alone right | parent alone right | body right | body before |
|---|---|---|---|---|---|---|---|---|
| a fact from a site and a date sum on it | none made | 30 of 133 (18 skipped for memory) | 0.001 -> 0.001 | +77 | - | - | - | - |
| a join over two small tables | none made | 9 of 19 (4 skipped for memory) | not measured | not measured | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a log read and counted into a file | none made | 18 of 19 (1 skipped for memory) | 0.003 -> 0.002 | +95 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a module of two functions, with hidden tests | none made | 115 of 345 (65 skipped for memory) | 0.118 -> 0.109 | +80 | 4 of 4 | - | 3 of 3 | 3 of 3 |
| a class with rules, with hidden tests | 12 of 12 | 60 of 456 (22 skipped for memory) | 0.300 -> 0.054 | +155 | 3 of 6 | - | 1 of 3 | 0 of 3 |
| a parser for a tiny language, with hidden tests | 13 of 13 | 70 of 513 (22 skipped for memory) | 0.584 -> 0.383 | +107 | 1 of 6 | - | 0 of 3 | 0 of 3 |
| the regions of a grid, with hidden tests | none made | 134 of 209 (2 skipped for memory) | 0.375 -> 0.133 | +137 | 0 of 2 | - | 0 of 1 | 1 of 1 |
| a cache that forgets the least recently used, with hidden tests | 12 of 12 | 60 of 456 (21 skipped for memory) | 0.433 -> 0.305 | +102 | - | - | - | - |
| a state machine from a table, with hidden tests | 13 of 13 | 48 of 437 (19 skipped for memory) | 0.252 -> 0.028 | +161 | - | - | - | - |
| an order of tasks by their dependencies, with hidden tests | 12 of 12 | 22 of 475 (28 skipped for memory) | 0.220 -> 0.057 | +147 | 0 of 1 | - | 1 of 1 | 0 of 1 |
| a number with given properties | none made | 0 of 152 (9 skipped for memory) | 0.291 -> 0.240 | +90 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a fact read and a date sum on it | none made | 23 of 38 (2 skipped for memory) | 0.001 -> 0.001 | +80 | - | - | - | - |
| the percent change between two columns, rounded by a rule | 12 of 12 | 45 of 551 (15 skipped for memory) | 0.164 -> 0.101 | +112 | 1 of 2 | - | 0 of 1 | 1 of 1 |
| a table cut to one row a key, the latest kept | none made | 18 of 76 (17 skipped for memory) | 0.018 -> 0.008 | +127 | 4 of 4 | - | 4 of 4 | 4 of 4 |
| the blanks of a table filled by a rule | none made | 17 of 119 (21 skipped for memory) | 0.061 -> 0.023 | +135 | - | - | - | - |
| a table grouped, each group's total and mean saved | none made | 15 of 38 (13 skipped for memory) | 0.017 -> 0.007 | +132 | 4 of 4 | - | 4 of 4 | 4 of 4 |
| JSON lines read and counted by a nested field | 12 of 12 | 170 of 646 (6 skipped for memory) | 0.056 -> 0.043 | +96 | - | - | - | - |
| a long table turned wide | none made | 10 of 78 (19 skipped for memory) | 0.039 -> 0.006 | +156 | 2 of 2 | - | 2 of 2 | 2 of 2 |
| several facts fetched and laid out as a file | none made | 13 of 38 (15 skipped for memory) | 0.002 -> 0.002 | +64 | 2 of 2 | - | 2 of 2 | 2 of 2 |
| a server log's matching lines counted by class | 14 of 14 | 0 of 513 (16 skipped for memory) | 0.093 -> 0.022 | +149 | - | - | - | - |
| emails and phones found in a messy message | 12 of 12 | 140 of 456 (109 skipped for memory) | 0.141 -> 0.039 | +145 | - | - | - | - |
| a markdown table turned into CSV | none made | not measured | 0.043 -> 0.014 | +140 | - | - | - | - |
| names turned and sorted | 12 of 12 | 0 of 494 (5 skipped for memory) | 0.061 -> 0.026 | +130 | - | - | - | - |
| a text split into sentences | 13 of 13 | 28 of 475 (58 skipped for memory) | 0.084 -> 0.033 | +133 | 1 of 1 | 0 of 1 | 1 of 1 | 0 of 1 |
| the most frequent words of a text | 12 of 12 | 15 of 456 (63 skipped for memory) | 0.096 -> 0.022 | +150 | - | - | - | - |
| walk a site over several pages | none made | not measured | 0.001 -> 0.001 | +42 | - | - | - | - |
| a fact found on the open web | none made | 22 of 38 (3 skipped for memory) | 0.003 -> 0.005 | +14 | - | - | - | - |

- rows left out: by kind, this generation's rows too long for a slice, of those the slices were given; in brackets those the memory guard skipped every time they came up. Rows not reached before the time was up are not left out
- gap: the kind's fall beside the mean fall of the kinds with no lesson this generation (scrape a page to a file: -73 points)
- child alone: the answers of this generation's cells (8) in the pulse; parent alone: those of their parents (g45code, g45code2, g45data, g45data2, g45sources, g45sources2, g45words, g45words2) in every arm. Two members sit a task, so these are few

How much the hive taught itself: of this generation's new rows, 217 from the hive's own checked practice and dreams (11 of them fix rows), 303 from the hand-written lesson makers (training/lessons.py, training/kinds/): the hive's own are 42% of those two. Rows trained on: not measured by source (each slice's record says the rows it trained by kind only, rows_by_kind; a field rows_by_source {source: trained} would measure it).

![The chain by kind](../progress/chain.svg)

## Hours

| step | minutes |
|---|---|
| practice | 53 |
| dream | 52 |
| gather | 11 |
| plan | 0 |
| train | 219 |
| join | 2 |
| merge | 2 |
| gate | 55 |
| record | 1 |

From the first job to the last: **5.72 hours** (the bar is 3). Each step runs from its first job's start to its last job's end; practice and dream run side by side.

Train slices lost: 1 of 20. Pulse seats whose server died: 0.

Colab: not used (notebook not there within the wait)

## Next piece

next piece: T3: read 10 of its programs first; then the key lines weigh more (rule 5: gap 15 or more, the child alone not right, for 2 of 27 taught hard kinds: the regions of a grid, with hidden tests, an order of tasks by their dependencies, with hidden tests)

Rules that hold but whose piece is done on the board (docs/PLAN.md), so not named: rule 2 (T4); rule 6 (K1).

| # | the chain shows | holds for |
|---|---|---|
| 1 | lessons right under 8 of 12 | 0 |
| 2 | more than 1 row in 5 of the kind left out | 12: a fact from a site and a date sum on it, a join over two small tables, a log read and counted into a file, a module of two functions, with hidden tests, the regions of a grid, with hidden tests, a fact read and a date sum on it, a table cut to one row a key, the latest kept, a table grouped, each group's total and mean saved, JSON lines read and counted by a nested field, several facts fetched and laid out as a file, emails and phones found in a messy message, a fact found on the open web (piece done) |
| 3 | kept-back gap under 15 points | 1: a fact found on the open web |
| 4 | gap 15 or more, the child alone right more often than its parent, the body not | 0 |
| 5 | gap 15 or more, the child alone not right | 2: the regions of a grid, with hidden tests, an order of tasks by their dependencies, with hidden tests |
| 6 | taught hard kinds 12 of 23, two generations running | 27 (piece done) |
