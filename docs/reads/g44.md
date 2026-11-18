# The read of g44

Run [44225157318](https://github.com/Arnav123-s/HiveMIND/actions/runs/44225157318), recorded 2026-11-18 07:45: the body was **kept**. the body grows: after 43 of 64 (easy 32 of 32, hard 11 of 32), before 40 of 64 (easy 32 of 32, hard 8 of 32) on 8 seeds

Written by the record job (`training/reads.py`), with nobody's hand. The rules are those of `docs/DECISIONS.md`.

## The numbers

| What is measured | g44 | g43 (last record) | the body before (same seeds) |
|---|---|---|---|
| Easy kinds passed | 32 of 32 | 32 of 32 | 32 of 32 |
| Hard kinds that have lessons | 9 of 19 | 20 of 26 | 8 of 19 |
| Hard kinds never practised (held out) | 0 of 3 | 0 of 6 | 0 of 3 |
| Right at the first try (practice) | 0.36 (35 of 96) | 0.53 | - |
| Hours for one generation | 5.0 | 4.4 | - |
| Generations recorded with nobody's hand | 3 | 2 | - |

## The chain, by taught hard kind

lessons right by their own check -> rows that fit in training -> loss falls on lessons kept back -> the child alone writes it at the exam -> the body (two agree) passes it.

| kind | lessons right of made | rows left out | kept-back loss before -> after | gap to untaught (points) | child alone right | parent alone right | body right | body before |
|---|---|---|---|---|---|---|---|---|
| a fact from a site and a date sum on it | none made | 40 of 162 (25 skipped for memory) | 0.002 -> 0.003 | -28 | - | - | - | - |
| a join over two small tables | none made | 15 of 23 (6 skipped for memory) | not measured | not measured | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a log read and counted into a file | 12 of 12 | 59 of 522 (70 skipped for memory) | 0.008 -> 0.011 | +0 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a module of two functions, with hidden tests | none made | 53 of 272 (25 skipped for memory) | 0.228 -> 0.219 | +37 | 1 of 4 | - | 1 of 2 | 1 of 2 |
| a number with given properties | none made | 0 of 180 (10 skipped for memory) | 0.472 -> 0.384 | +52 | 2 of 3 | - | 2 of 2 | 2 of 2 |
| a fact read and a date sum on it | none made | 6 of 36 (5 skipped for memory) | 0.003 -> 0.006 | -85 | - | - | - | - |
| the percent change between two columns, rounded by a rule | 12 of 12 | 9 of 432 (89 skipped for memory) | 1.020 -> 0.298 | +104 | - | - | - | - |
| a table cut to one row a key, the latest kept | 13 of 13 | 0 of 414 (14 skipped for memory) | 1.367 -> 0.234 | +116 | 1 of 2 | - | 0 of 1 | 0 of 1 |
| the blanks of a table filled by a rule | 12 of 12 | 0 of 360 (48 skipped for memory) | 1.496 -> 0.391 | +107 | - | - | - | - |
| a table grouped, each group's total and mean saved | 12 of 12 | 12 of 432 (16 skipped for memory) | 0.996 -> 0.162 | +117 | - | - | - | - |
| JSON lines read and counted by a nested field | 12 of 12 | 44 of 414 (83 skipped for memory) | 0.864 -> 0.214 | +109 | 0 of 4 | - | 0 of 2 | 0 of 2 |
| a long table turned wide | 12 of 12 | 0 of 360 (24 skipped for memory) | 1.015 -> 0.220 | +112 | - | - | - | - |
| several facts fetched and laid out as a file | none made | 17 of 108 (14 skipped for memory) | 0.003 -> 0.009 | -180 | 2 of 2 | - | 2 of 2 | 2 of 2 |
| a server log's matching lines counted by class | 12 of 12 | 120 of 360 (92 skipped for memory) | 0.655 -> 0.309 | +86 | 0 of 4 | - | 0 of 2 | 0 of 2 |
| emails and phones found in a messy message | 13 of 13 | 148 of 414 (105 skipped for memory) | 0.465 -> 0.240 | +82 | 0 of 1 | - | 0 of 1 | 0 of 1 |
| a markdown table turned into CSV | 12 of 12 | 0 of 432 (18 skipped for memory) | 1.200 -> 0.212 | +116 | - | - | - | - |
| names turned and sorted | 12 of 12 | 0 of 360 (77 skipped for memory) | 0.736 -> 0.218 | +104 | - | - | - | - |
| a text split into sentences | 13 of 13 | 11 of 414 (86 skipped for memory) | 0.698 -> 0.232 | +100 | 0 of 4 | - | 0 of 3 | 0 of 3 |
| the most frequent words of a text | 12 of 12 | 0 of 360 (82 skipped for memory) | 0.656 -> 0.198 | +103 | - | - | - | - |
| walk a site over several pages | none made | not measured | 0.001 -> 0.003 | -205 | 1 of 1 | - | 1 of 1 | 1 of 1 |
| a fact found on the open web | none made | 22 of 108 (3 skipped for memory) | 0.010 -> 0.010 | +27 | 1 of 1 | - | 1 of 1 | 0 of 1 |

- rows left out: by kind, this generation's rows too long for a slice, of those the slices were given; in brackets those the memory guard skipped every time they came up. Rows not reached before the time was up are not left out
- gap: the kind's fall beside the mean fall of the kinds with no lesson this generation (scrape a page to a file: -33 points)
- child alone: the answers of this generation's cells (8) in the pulse; parent alone: those of their parents (g42code, g42code2, g42data, g42data2, g42sources, g42sources2, g42words, g42words2) in every arm. Two members sit a task, so these are few
- parent alone: not measured; no parent sat a task of a taught hard kind (the pulse seats the trunk and the newest cells first; the paired gate's before arm seats the body before, parents among it)

![The chain by kind](../progress/chain.svg)

## Hours

| step | minutes |
|---|---|
| practice | 42 |
| dream | 54 |
| gather | 13 |
| plan | 0 |
| train | 175 |
| join | 2 |
| merge | 2 |
| gate | 56 |
| record | 0 |

From the first job to the last: **5.05 hours** (the bar is 5). Each step runs from its first job's start to its last job's end; practice and dream run side by side.

Train slices lost: 2 of 20. Pulse seats whose server died: 0.

Colab: not used (notebook not there within the wait)

## Next piece

next piece: T4: shorter lessons (rule 2: more than 1 row in 5 of the kind left out, for 5 of 21 taught hard kinds: a fact from a site and a date sum on it, a join over two small tables, a server log's matching lines counted by class, emails and phones found in a messy message, a fact found on the open web)

| # | the chain shows | holds for |
|---|---|---|
| 1 | lessons right under 8 of 12 | 0 |
| 2 | more than 1 row in 5 of the kind left out | 5: a fact from a site and a date sum on it, a join over two small tables, a server log's matching lines counted by class, emails and phones found in a messy message, a fact found on the open web |
| 3 | kept-back gap under 15 points | 5: a fact from a site and a date sum on it, a log read and counted into a file, a fact read and a date sum on it, several facts fetched and laid out as a file, walk a site over several pages |
| 4 | gap 15 or more, the child alone right more often than its parent, the body not | 0 |
| 5 | gap 15 or more, the child alone not right | 4: JSON lines read and counted by a nested field, a server log's matching lines counted by class, emails and phones found in a messy message, a text split into sentences |
| 6 | taught hard kinds 12 of 23, two generations running | 0 |
