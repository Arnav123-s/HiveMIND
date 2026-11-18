# HiveMIND: progress toward the goal

**The goal:** a body of ternary nets that does what it is asked (questions, conversation, tasks), and gets better at it by itself, generation after generation.

This page is drawn by the hive itself at the end of every generation (`training/progress.py`, run by the workflow's record step). Hover a point in a graph for its numbers.

**Now:** generation g47 of the 8B body passed 47 of 64 exam tasks (73%). The best so far on this DNA: g41, 58 of 64 (91%).

**Talk:** generation g47 sat the talk exam (seed 30000047): 6.2 of 10 (25 of 40 messages right: route 6 of 10, fact 7 of 10, earlier 7 of 10, time 5 of 10). The bar: 8 of 10.

![The share of exam tasks the body passed, each generation](progress/score.svg)

![Hard kinds, easy kinds and tasks of several parts, passed](progress/parts.svg)

![Hard, easy and held-out kinds passed, each generation](progress/split.svg)

![The share of never-practised kinds it passed](progress/carry.svg)

![Each kind of task, weakest first](progress/kinds.svg)

![Rows taught, each generation](progress/rows.svg)

![Hours of one generation, by step](progress/hours.svg)

![The chain of the newest generation, by taught hard kind](progress/chain.svg)

Its read, with the next piece: [reads/latest.md](reads/latest.md).

Generations that stand on less (marked red in the split graph): g41: 1 of 20 train slices lost; g42: 2 of 20 train slices lost; g44: 2 of 20 train slices lost; g45: 1 of 20 train slices lost; g47: 2 of 20 train slices lost.

## Where it practises most next

Practice draws each kind of task by how close the body is to passing it half the time: a kind always passed is learned, one never passed has no right program to learn from yet. Most drawn next:

- the regions of a grid, with hidden tests
- a module of two functions, with hidden tests
- JSON lines read and counted by a nested field
- the blanks of a table filled by a rule
- a table cut to one row a key, the latest kept
- the percent change between two columns, rounded by a rule

## How hard its lessons are now

Each record raises a kind's level when the body passes it 7 times in 10, and lowers it at 3 in 20: compound 2, h_join 1, h_log 1, h_search 0, m_percent 1, m_table 1.
