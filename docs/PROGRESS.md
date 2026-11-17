# HiveMIND: progress toward the goal

**The goal:** a body of ternary nets that does what it is asked (questions, conversation, tasks), and gets better at it by itself, generation after generation.

This page is drawn by the hive itself at the end of every generation (`training/progress.py`, run by the workflow's record step). Hover a point in a graph for its numbers.

**Now:** generation g41 of the 8B body passed 58 of 64 exam tasks (91%). The best so far on this DNA: g41, 58 of 64 (91%).

![The share of exam tasks the body passed, each generation](progress/score.svg)

![Hard kinds, easy kinds and tasks of several parts, passed](progress/parts.svg)

![Hard, easy and held-out kinds passed, each generation](progress/split.svg)

![The share of never-practised kinds it passed](progress/carry.svg)

![Each kind of task, weakest first](progress/kinds.svg)

![Rows taught, each generation](progress/rows.svg)

![Hours of one generation, by step](progress/hours.svg)

![The chain of the newest generation, by taught hard kind](progress/chain.svg)

Its read, with the next piece: [reads/latest.md](reads/latest.md).

Generations that stand on less (marked red in the split graph): g41: 1 of 20 train slices lost.

## Where it practises most next

Practice draws each kind of task by how close the body is to passing it half the time: a kind always passed is learned, one never passed has no right program to learn from yet. Most drawn next:

- scrape a page to a file
- a module of two functions, with hidden tests
- walk a site over several pages
- operate a website
- a fact read and a date sum on it
- several facts fetched and laid out as a file

## How hard its lessons are now

Each record raises a kind's level when the body passes it 7 times in 10, and lowers it at 3 in 20: compound 2, h_join 0, h_log 0, h_search 0, m_percent 0, m_table 1.
