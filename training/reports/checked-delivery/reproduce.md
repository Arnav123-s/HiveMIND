# Checking which worker’s file reaches the user

Two workers can calculate the same total and save different files. This replay gives two revisions of `team.solo.first()` the same finished workers, including their output folders. It allows the normal coordinator to consult its reserve seat. If that seat has no recording, it returns an empty answer. The grader reopens the file in the final delivery directory. It checks the whole table in order, the JSON values or the exact requested text, as well as the printed answer. A job earns one point only when the coordinator confirms it and both checks pass.

| Evidence | Correct jobs, original | Correct jobs, revised | Incorrect confirmations, original → revised |
| --- | ---: | ---: | ---: |
| Recorded rainfall job, original worker order | 0/1 | 1/1 | 1 → 0 |
| Same recording, reversed order | 1/1 | 1/1 | 0 → 0 |
| Constructed controls | 3/13 | 7/13 | 9 → 3 |
| Fresh G47 jobs, first two actual workers | 1/3 | 1/3 | 2 → 1 |

The rainfall workers both printed `21`. One file had three fields in every data row beneath a two-field header. Both revisions stopped after two seats. The revised coordinator delivered the second worker’s exact table. The source records include worker programs, printed answers and decoded CSV rows. The replay serializes those rows with the standard CSV writer. The reverse-order replay uses the same observations and counts as a sensitivity check. [Archived G47 observations](https://github.com/Arnav123-s/HiveMIND/blob/a70eb72a286020e5dceafb451d6d2051756cd44c/training/reports/whole-hive-g47/observations.json)

Of the 13 deliberately constructed cases, nine had a fully correct candidate. There were three abstentions after the change and one before. Both revisions still confirmed three wrong outputs when the workers shared the same error in CSV values, JSON values or prose. The revised coordinator requested 31 seats in total, compared with 27 originally. One CSV header control informed the parser fix. The handoff can receive a constructed state that the real member would normally retry, such as a missing file. These cases measure specific failure modes. They provide no estimate of how often ordinary users encounter them.

Run these commands from the repository root using the Python environment where its tests pass.

```sh
git worktree add --detach /tmp/hive-g47-replay b2133163c40a10d5c8dee8a3debf9a30b1a2aa38
git worktree add --detach /tmp/hive-checked-replay 3a4a6ee
python training/checked_delivery_eval.py --checkout /tmp/hive-g47-replay > /tmp/hive-before.json
python training/checked_delivery_eval.py --checkout /tmp/hive-checked-replay > /tmp/hive-after.json
```

The primary selector was frozen at commit `3a4a6ee` before any follow-up prompted by fresh model failures. `frozen-hashes.json` records its file digests.

`before.json` and `after.json` contain one row per case. `candidate_correct` scores each available candidate against the independent answer key. `requested_seats` counts work requested by the coordinator and `recorded_seats` counts workers available to the replay. The replay substitutes completed worker responses, seat assignment and the memory write. It makes zero inference calls. Text grades use the confirmed worker output before any chat formatting. The separate CLI and live talk checks exercise that formatting.


## Three new jobs on the real model

The prompts and expected outputs in `fresh-tasks.json` were frozen before inference. The G47 CPU hive received only the prompt for each task via `team.talk.reply`, using the five released adapters and normal member-turn budgets. `fresh-members.json` preserves every worker’s final program, file and stdout, the original chat reply, original delivery and run configuration. Replaying the original selection reproduced all three delivered files byte for byte. The next table uses the two workers that G47 actually asked on each job.

| Job | Correct workers | Original G47 | First revised selector |
| --- | ---: | --- | --- |
| Sales ranked by revenue | 1/2 | Printed 41, delivered unsorted rows | Withheld the conflicting tables |
| Bus stops eligible for pickup | 2/2 | Printed 7, delivered the exact JSON | Printed 7, delivered the exact JSON |
| Parcels filtered and sorted | 0/2 | Printed 14, delivered reversed order | Printed 14, delivered the same reversed order |

All six workers printed exactly the requested integer. G47’s original chat layer wrapped it in a sentence, a verification note and the filename on all three jobs. Under a strict whole-message integer check, zero of those chat replies passed. The replay table scores worker stdout and the file, with the displayed reply preserved for separate inspection. The three original live requests took 123 to 241 seconds on a shared four-core CPU. No timing comparison is claimed.

## What transferred to new wording

After observing the reversed parcel rows and the sales disagreement, a second revision recognized certain instructions to sort one numeric column. It can reorder rows without changing their cell values. Replaying the same six workers at `6f4d496` delivered all three original jobs correctly (`after-sort.json`). Two had informed that revision. They are development successes.

A separate grader sealed nine constructed jobs, their candidate files, expected results and expected delivery decisions before the second revision was scored. The SHA256 of `order-cases.json` is `52cd5e830faef47ed56de2454daf2f93f5237efae15418fc58c96802697691f8`. Neither selector solved any of the four newly worded ordering repairs. Both preserved all four already-correct files and withheld one conflicting pair with wrong data. Both scored **5/9 decisions**. The recorded row outputs show three incorrect confirmations and one abstention on those four repair cases. The recognizer declined phrasings including “order rows by,” “in ascending numeric order,” a trailing preservation clause, and an explicit tie instruction. Generalizing from the two observed jobs to natural sorting requests remains an open problem.

```sh
git worktree add --detach /tmp/hive-sort-replay 6f4d496
python training/checked_delivery_eval.py --checkout /tmp/hive-sort-replay > /tmp/after-sort.json
python training/checked_delivery_eval.py --checkout /tmp/hive-checked-replay --cases training/reports/checked-delivery/order-cases.json > /tmp/order-before.json
python training/checked_delivery_eval.py --checkout /tmp/hive-sort-replay --cases training/reports/checked-delivery/order-cases.json > /tmp/order-after.json
```

The market dispute also received the actual reserve worker from the G47 roster in a separate rollout. This third worker spent 159 seconds, printed `14` and wrote unit prices under the revenue heading. With all three available, `3a4a6ee` still withheld an answer. The numeric-sort revision delivered the right job using the first two. The extra rollout was recorded apart from the original live selection. `market-with-reserve.json` and `reserve-results.json` preserve the candidates and all three outcomes. Replay that case with `--cases training/reports/checked-delivery/market-with-reserve.json`.

## One new live CLI job

The independent grader froze a new community-hall request before the ordering change. It asked the hive to subtract returned chairs from each person’s borrowed count, save `chairs.csv` sorted by the outstanding count ascending, and print the total. Both actual G47 workers produced `25` and exactly the same wrong row order, Noor 14, Ada 3, Lin 8. The public `./hive --once` command at `6f4d496` exited 0, wrote exactly `25` and a newline to stdout, and delivered Ada 3, Lin 8, Noor 14 in the CSV. It took 270.713 seconds on this shared CPU. This demonstrates one live repair on a new task with a recognized instruction. The nine-case wording result above shows where it stopped working. Open the [CSV delivered by the actual terminal run](chairs.csv). The sealed wording and answer key are in `live-cli-case.json`. `live-cli-result.json` contains the exact command, terminal output streams, saved file, worker programs and hashes of the serving code.

## Last confirmation on 12 further requests

The nine-case set was released for development following its 5/9 result. The final revision then made the expected decision on 9/9 of those known cases. The evaluator separately froze twelve further requests with expected results and synthetic worker files before testing that revision. Each had the same pool under both selectors. The measured code at `9992ccc` has identical production selection and file-checking sources in published commit `43f8dd7`. There was no further tuning on the twelve cases.

| Independent tasks | Previous numeric-sort revision | Final revision |
| --- | ---: | ---: |
| Deliver the expected numerically ordered CSV | 3/7 | 6/7 |
| Preserve the specified route, text-code order or layout | 3/3 | 3/3 |
| Withhold a conflicting or unsupported result | 2/2 | 2/2 |
| **Correct delivery decisions** | **8/12** | **11/12** |

The remaining error reached the user. With “Please sort the rows by books (lowest first),” both workers saved the same unsorted table and the hive confirmed it. The method handles particular phrasings of single-column numeric sorting. For example, “Sort by cost descending.” worked in the final set. These twelve cases used constructed worker files and measure the coordinator. The chair job above is the independent end-to-end run on the actual model.

`final-order-cases.json` has the frozen inputs and keys. Its SHA256 is `0dc85ab7a85d76f2d210b121ac93a92eab04083785184b8c943ca51d1e6201e6`. Each detailed result includes worker correctness, the final copied file, the worker stdout and the actual decision. `released-order-after.json` is the rerun on the nine cases after they became development examples.

```sh
git worktree add --detach /tmp/hive-final-replay 43f8dd7
python training/checked_delivery_eval.py --checkout /tmp/hive-sort-replay --cases training/reports/checked-delivery/final-order-cases.json > /tmp/final-order-before.json
python training/checked_delivery_eval.py --checkout /tmp/hive-final-replay --cases training/reports/checked-delivery/final-order-cases.json > /tmp/final-order-after.json
```
