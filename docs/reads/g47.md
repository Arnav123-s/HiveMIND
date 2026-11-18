# The read of g47

Run [44313055326](https://github.com/Arnav123-s/HiveMIND/actions/runs/44313055326), recorded 2026-11-18 18:38: the body was **kept**. the body grows: after 47 of 64 (easy 31 of 32, hard 16 of 32), before 47 of 64 (easy 31 of 32, hard 16 of 32) on 8 seeds

Written by the record job (`training/reads.py`), with nobody's hand. The rules are those of `docs/DECISIONS.md`.

## The numbers

| What is measured | g47 | g45 (last record) | the body before (same seeds) |
|---|---|---|---|
| Easy kinds passed | 31 of 32 | 32 of 32 | 31 of 32 |
| Hard kinds that have lessons | 16 of 25 | 13 of 22 | 15 of 25 |
| Hard kinds never practised (held out) | 0 of 7 | 0 of 10 | 1 of 7 |
| Right at the first try (practice) | 0.39 (37 of 96) | 0.35 | - |
| Right at the first try, old kinds and K2's new kinds (practice) | not measured | - | - |
| Hours for one generation | 5.2 | 5.6 | - |
| Generations recorded with nobody's hand | 5 | 4 | - |
| Talk (the talk exam, out of 10; the bar is 8) | 6.2 of 10 (route 6 of 10, fact 7 of 10, earlier 7 of 10, time 5 of 10) | 6.5 of 10 (route 5 of 10, fact 7 of 10, earlier 8 of 10, time 6 of 10) | - |

The two hard-task rows above were recounted from the recorded per-kind scores. The training chain and next-piece decision below are the original run report.

## The chain, by taught hard kind

lessons right by their own check -> rows that fit in training -> loss falls on lessons kept back -> the child alone writes it at the exam -> the body (two agree) passes it.

| kind | lessons right of made | rows left out | kept-back loss before -> after | gap to untaught (points) | child alone right | parent alone right | body right | body before |
|---|---|---|---|---|---|---|---|---|
| a fact from a site and a date sum on it | none made | 38 of 54 (3 skipped for memory) | 0.001 -> 0.002 | -22 | - | - | - | - |
| a join over two small tables | none made | 11 of 18 (1 skipped for memory) | not measured | not measured | 0 of 1 | - | 1 of 1 | 1 of 1 |
| a log read and counted into a file | none made | 145 of 198 (8 skipped for memory) | 0.002 -> 0.004 | -69 | - | - | - | - |
| a module of two functions, with hidden tests | 13 of 13 | 102 of 684 (30 skipped for memory) | 0.098 -> 0.086 | +45 | - | - | - | - |
| a number with given properties | none made | 0 of 36 (19 skipped for memory) | 0.307 -> 0.301 | +35 | 2 of 2 | - | 2 of 2 | 2 of 2 |
| a fact read and a date sum on it | none made | 49 of 147 (20 skipped for memory) | 0.002 -> 0.003 | -68 | - | - | - | - |
| the percent change between two columns, rounded by a rule | 13 of 13 | 88 of 763 (62 skipped for memory) | 0.173 -> 0.153 | +44 | 1 of 4 | - | 0 of 2 | 1 of 2 |
| a table cut to one row a key, the latest kept | none made | 60 of 144 (16 skipped for memory) | 0.070 -> 0.022 | +102 | - | - | - | - |
| the blanks of a table filled by a rule | none made | 62 of 147 (3 skipped for memory) | 0.162 -> 0.056 | +98 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a table grouped, each group's total and mean saved | none made | 22 of 72 (8 skipped for memory) | 0.050 -> 0.015 | +104 | 2 of 2 | - | 2 of 2 | 2 of 2 |
| JSON lines read and counted by a nested field | 12 of 12 | 173 of 630 (15 skipped for memory) | 0.286 -> 0.071 | +108 | - | - | - | - |
| a long table turned wide | none made | 59 of 234 (32 skipped for memory) | 0.079 -> 0.044 | +78 | - | - | - | - |
| several facts fetched and laid out as a file | none made | 21 of 72 (9 skipped for memory) | 0.002 -> 0.003 | +7 | 2 of 2 | - | 2 of 2 | 2 of 2 |
| a server log's matching lines counted by class | 12 of 12 | 0 of 360 (23 skipped for memory) | 0.690 -> 0.101 | +118 | - | - | - | - |
| emails and phones found in a messy message | 13 of 13 | 249 of 414 (19 skipped for memory) | 0.261 -> 0.048 | +114 | 0 of 1 | - | 0 of 1 | 0 of 1 |
| a markdown table turned into CSV | none made | 0 of 72 (22 skipped for memory) | 0.085 -> 0.033 | +94 | 2 of 2 | - | 2 of 2 | 2 of 2 |
| names turned and sorted | 13 of 13 | 0 of 450 (19 skipped for memory) | 0.416 -> 0.102 | +108 | - | - | - | - |
| a text split into sentences | 13 of 13 | 11 of 486 (124 skipped for memory) | 0.270 -> 0.144 | +80 | 0 of 2 | - | 0 of 2 | 0 of 2 |
| the most frequent words of a text | 12 of 12 | 13 of 432 (100 skipped for memory) | 0.289 -> 0.143 | +83 | 1 of 2 | - | 1 of 1 | 1 of 1 |
| walk a site over several pages | none made | not measured | 0.001 -> 0.002 | -114 | 3 of 3 | - | 3 of 3 | 3 of 3 |
| a fact found on the open web | none made | 27 of 36 | 0.004 -> 0.008 | -77 | - | - | - | - |

- rows left out: by kind, this generation's rows too long for a slice, of those the slices were given; in brackets those the memory guard skipped every time they came up. Rows not reached before the time was up are not left out
- gap: the kind's fall beside the mean fall of the kinds with no lesson this generation (scrape a page to a file, the regions of a grid, with hidden tests: -33 points)
- child alone: the answers of this generation's cells (7) in the pulse; parent alone: those of their parents (g44code, g44code2, g44data, g44data2, g44sources, g44sources2, g44words) in every arm. Two members sit a task, so these are few
- parent alone: not measured; no parent sat a task of a taught hard kind (the pulse seats the trunk and the newest cells first; the paired gate's before arm seats the body before, parents among it)

How much the hive taught itself: of this generation's new rows, 219 from the hive's own checked practice and dreams (8 of them fix rows), 330 from the hand-written lesson makers (training/lessons.py, training/kinds/): the hive's own are 40% of those two. Rows trained on: not measured by source (each slice's record says the rows it trained by kind only, rows_by_kind; a field rows_by_source {source: trained} would measure it).

![The chain by kind](../progress/chain.svg)

## Hours

| step | minutes |
|---|---|
| practice | 49 |
| dream | 48 |
| gather | 8 |
| plan | 0 |
| train | 217 |
| join | 2 |
| merge | 2 |
| gate | 36 |
| record | 1 |

From the first job to the last: **5.25 hours** (the bar is 3). Each step runs from its first job's start to its last job's end; practice and dream run side by side.

Train slices lost: 2 of 20. Pulse seats whose server died: 0.

Colab: not used (notebook not seen)

## Next piece

next piece: dose: one change a generation: raw reading and judged pairs off; slices weighed by steps; the one-line trial (rule 3: kept-back gap under 15 points, for 6 of 21 taught hard kinds: a fact from a site and a date sum on it, a log read and counted into a file, a fact read and a date sum on it, several facts fetched and laid out as a file, walk a site over several pages, a fact found on the open web)

Rules that hold but whose piece is done on the board (docs/PLAN.md), so not named: rule 2 (T4); rule 6 (K1).

| # | the chain shows | holds for |
|---|---|---|
| 1 | lessons right under 8 of 12 | 0 |
| 2 | more than 1 row in 5 of the kind left out | 12: a fact from a site and a date sum on it, a join over two small tables, a log read and counted into a file, a fact read and a date sum on it, a table cut to one row a key, the latest kept, the blanks of a table filled by a rule, a table grouped, each group's total and mean saved, JSON lines read and counted by a nested field, a long table turned wide, several facts fetched and laid out as a file, emails and phones found in a messy message, a fact found on the open web (piece done) |
| 3 | kept-back gap under 15 points | 6: a fact from a site and a date sum on it, a log read and counted into a file, a fact read and a date sum on it, several facts fetched and laid out as a file, walk a site over several pages, a fact found on the open web |
| 4 | gap 15 or more, the child alone right more often than its parent, the body not | 0 |
| 5 | gap 15 or more, the child alone not right | 2: emails and phones found in a messy message, a text split into sentences |
| 6 | taught hard kinds 12 of 23, two generations running | 21 (piece done) |
