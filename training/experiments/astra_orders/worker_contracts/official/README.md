# Official held-out results on the retained G55 body

The G55 hive with F3 worker checks passed **4/30 tasks**, up from **3/30** for stock. It gained three answers and lost two. All three CSV editing tasks passed, moving the hive from zero to one of ten kinds passed. The target for this experiment was four additional tasks. The separately fitted F4 child passed **2/30**, down one from stock, and passed zero kinds.

All three arms faced the same 30 fixed tasks. Each kind has three questions and requires at least two correct whole-task answers. The unchanged grader checked requested files along with the delivered answer. Each arm used the retained 25-member G55 roster, normal worker settings and the same 900-second limit per task. F3 enabled unfamiliar-task inspection, explicit public checks and the private worker HTTP cache. F4 used stock worker settings and replaced only the G55 trunk adapter. The two budget-continuation experiments had no role in these runs. [Per-task grades, member verdicts, and all 24 artifact IDs and hashes](results.json) · [G55 stock and F3 run](https://github.com/Arnav123-s/HiveMIND/actions/runs/44869027245) · [F4 child run](https://github.com/Arnav123-s/HiveMIND/actions/runs/44868991744)

| Result | G55 stock | G55 with F3 | F4 child |
|---|---:|---:|---:|
| Tasks passed out of 30 | 3 | 4 | 2 |
| Kinds passed out of 10 | 0 | 1 | 0 |
| Tasks with a correct checked member | 9 | 6 | 5 |
| Tasks a member solved but the hive failed to deliver | 6 | 2 | 3 |
| Official task timeouts | 4 | 5 | 6 |

## Correct answers by kind

| Task kind | G55 stock | G55 with F3 | F4 child |
|---|---:|---:|---:|
| Edit a CSV and report the result | 1/3 | **3/3** | 1/3 |
| Write a queue module | 0/3 | 0/3 | 0/3 |
| Write a text wrapping module | 0/3 | 0/3 | 0/3 |
| Gather quotes from a website | 0/3 | 0/3 | 0/3 |
| Run a step-by-step simulation | 0/3 | 0/3 | 1/3 |
| Filter a table by date | 0/3 | 1/3 | 0/3 |
| Rank rows within groups | 1/3 | 0/3 | 0/3 |
| Compare two live sources | 1/3 | 0/3 | 0/3 |
| Read a configuration file | 0/3 | 0/3 | 0/3 |
| Redact text and report the count | 0/3 | 0/3 | 0/3 |

## What changed on individual tasks

* **F3 gained** `x_h_edit_0`, `x_h_edit_2`, and `x_h_tab_dates_0`. **It lost** `x_h_tab_topn_2` and `x_h_two_1`. On both newly delivered editing tasks the stock hive had one correct data specialist and withheld the file. With F3, the G55 trunk also passed each task, another member confirmed it, and the hive delivered both files. The F3 workers logged 106 inspection events across all 30 tasks. The log records zero repairs from the explicit public-module example check. The three F3 controls ran together, so their individual effects remain unresolved.
* **F4 gained** `x_h_edit_2` and `x_h_sim_2`. **It lost** `x_h_edit_1`, `x_h_tab_topn_2`, and `x_h_two_1`. On the editing gain the trunk failed in both runs, while two data members confirmed the child's answer. On the simulation gain the trunk was right in both runs, and a second correct member confirmed the child's delivery. These gains are measured at the whole-body level.

The common stock arm and both treatments completed every official task. All 24 first-attempt jobs succeeded. The two scorers verified the task text and shard assignment, G55 history, run identity, member roster and adapter manifests. All 24 downloaded ZIPs matched GitHub's recorded byte counts and SHA-256 digests. Official timeouts remain failures in the totals. This was one run per condition on fixed seeds, with live sources and hosted runners. [F3 scorer](../paired.py) · [F4 frozen child workflow](https://github.com/Arnav123-s/HiveMIND/blob/e24bbea34b7ddbd80ce6456ebbb2aaf40749c97b/.github/workflows/exam.yml)
