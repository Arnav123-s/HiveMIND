# Cells: confidence thresholds and the cell → member cascade

Measured on 2026-11-08. Every threshold below was chosen on the dev split and is only reported on test.

## Triage: the task_kind cell (switched on)

The cell names the cheapest way through the hive. A template plan then replaces the 4B coordinator and plan reviewer.
It was retrained with 300 steps; two recipes tied on dev, and the lower dev loss won. As served through llama.cpp it
scores **0.913** on test (the first version scored 0.756), at 62 ms per call.

A shortcut is taken only when the cell names a kind other than `plan` with at least that kind's threshold
(`training/cells_triage_threshold.py`). Each threshold is the lowest one at which the cell's confident dev answers
for that kind are all right. Every wrong shortcut, on dev and on test, was a `write`: writer only, with no research
and no calculation.

| | thresholds | shortcut taken | right |
|---|---|---|---|
| flat 0.9, dev | all 0.9 | 46/55 | 45 (0.978) |
| flat 0.9, test | all 0.9 | 91/127 | 86 (0.945): 3 lookup→write, 2 plan→write |
| **per kind, dev** | write 0.97, others 0.9 | 45/55 | 45 (1.0) |
| **per kind, test** | write 0.97, others 0.9 | 89/127 (70%) | 86 (0.966): 3 lookup→write |

The rule for switching triage on was fixed before the measurement: the shortcut's dev precision must be at least 0.95.
It is 1.0, so triage is on (`cells/wins.json`). The remaining error is a lookup that the cell confidently calls a
writing task, so the writer answers from its own knowledge. The writer's critic then marks the unbacked claims, and
an until-done round re-plans with the coordinator (later rounds never take the shortcut).

## Family check: no threshold helps (unchanged)

`training/cells_family_threshold.py`: on dev the cell is perfect at every threshold from 0.5 to 0.95, so dev cannot
choose one. On test it falsely blocks 9 or 10 legitimate steps at every threshold (precision 0.76 to 0.77). The cell
is confidently wrong on unseen phrasings, so a threshold cannot remove those false blocks. Nothing changed: the cell
only ever adds blocks to the rule's, and the writer's step is judged by the rule alone (the cell had dropped writer
steps in the hive bench). The guard can now read a threshold from `cells/wins.json`; none is set.

## Cascade: the cell answers when sure, unsure cases go to the bigger member

`training/cells_cascade.py`, on the cells whose incumbent's per-input errors were stored. The threshold chosen on dev
was 0.5 every time: the cells' dev answers were already at least as accurate as the member, so nothing is sent up and
the cascade equals the cell. No cascade is wired in.

| cell | cell | member | cascade | sent up | cell ms | member ms |
|---|---|---|---|---|---|---|
| orders_spend | 0.984 | 0.918 | 0.984 | 0% | 41 | 1162 |
| orders_delete | 0.934 | 0.885 | 0.934 | 0% | 43 | - |
| orders_send | 0.885 | 0.918 | 0.885 | 0% | 44 | - |
| orders_login | 0.984 | 1.0 | 0.984 | 0% | 42 | - |
| orders_signup | 1.0 | 0.984 | 1.0 | 0% | 42 | - |
| route_step | 0.992 | 0.975 | 0.992 | 0% | 34 | 7095 |

Skipped: claim_support, licence_open, pick_source, next_move and family_topic, because their incumbent measurement
kept only 6 errors. `training/cells_incumbents.py` now keeps every error, so they can be measured again. The likely
gain is in claim_support (cell 0.83, verifier 0.88, about 10 s per verifier call) and licence_open. **Not measured yet.**

The order cells' spend timing above comes from a clean re-run. The first run overlapped with another model job and
showed 5367 ms per call.

## What this says about dev

Dev holds out about 20% of the training words but keeps the training frames. Several cells reach 1.0 on dev and score
lower on test, where the frames are new: family_topic 0.79, licence_open 0.76, next_move 0.88, orders_send 0.89. A
threshold or cascade chosen on such a dev split cannot see the errors that test shows. A dev split built from
held-out frames is the general fix. It has not been done.
