# Does replay protect old work across three updates?

At G56, fresh-only and 2:1 replay averaged **76.7/107** old program preferences correct. The 4:1 arm averaged **76.3/107**. The larger loss observed in the earlier single-cohort test did not recur on these separately reserved questions. The clearest implementation finding was a difference between row counts and the amount of training spent on them. Correcting that discrepancy recovered fresh-program exposure and gave no consistent accuracy gain. Production settings retain their existing defaults. [Frozen protocol](protocol.md) · [All 126 measurements and 63 training ledgers](results.json.gz)

We loaded the four original G53–G56 all-rows artifacts, with 7,545, 7,818, 8,247 and 8,820 rows respectively. Each arm started with the same conditional byte model trained on G53 positives. Each subsequent update got 30,000 target bytes. G54 was dropped, G55 was accepted and G56 was dropped. Thus the model tested for G55 starts again from G53, and the model tested for G56 starts from its own arm's G55 state. The historical release decisions were fixed for every arm. Model fitting, allocations and receipt matching used only evidence available at the corresponding stage. We froze the study before scoring. The new practice partition shares no question with the previous study's partition.

## Retention and new preferences

The main panel contains 107 distinct old practice requests. One recorded preferred and one rejected existing program were compared per request. Both programs and the question were excluded from training throughout. The separate 21-question old panel used original G50–52 gate work. Here each program had an individual actor grade, a pre-run actor/seat match, a single identifiable script and matching captured output. Neither exact question nor candidate program appeared in the training pools. Requests with incomplete or ambiguous evidence could not enter this panel.

| Completed candidate update | Fresh only, old practice | 2 fresh per replay | 4 fresh per replay | Fresh only, independent old | 2 fresh per replay | 4 fresh per replay |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| G54 | 76.0/107 | 76.0 | 76.3 | 14.0/21 | 14.0 | 14.0 |
| G55 | 76.3/107 | 75.3 | 75.7 | 13.3/21 | 13.3 | 13.7 |
| G56 | 76.7/107 | 76.7 | 76.3 | 13.3/21 | 13.3 | 13.7 |

Entries are means of three predetermined data-order seeds on the same questions. Seed runs are dependent repeats. The 2:1 arm lost one previously correct old practice preference per seed at G54 and G55, and zero at G56. Fresh-only lost two per seed at G54, between one and two at G55, and between zero and one at G56. Fewer lost preferences sometimes came with fewer gains. All arms scored 3/4, 2/4, and 6/7 on the newly appearing practice preferences for G54, G55, and G56. The stricter new gate-script subset had only one, three, and five cases respectively and produced no between-arm differences at the principal no-decay setting.

## Why counting rows can be misleading

Only 15, 21 and 12 older questions qualified at the three successive updates. Older programs can be longer than fresh programs. For G56 the live 2:1 scheduler spent **47.6%** of training bytes on replay, compared with its nominal one-third row share. The 4:1 scheduler spent **29.8%**, compared with one-fifth of rows. The earlier single-stage test showed a similar discrepancy. Adding subjects also advances the shared sampler's random state, so a seed alone does not hold the fresh-row sequence fixed across arms.

We isolated those effects by giving fresh and archived work separate, identical-order source streams. On G56 a 2:1 row schedule used 48.6% of bytes for replay and reached 37.7 distinct fresh programs on average. Selecting by consumed bytes used 35.4% for replay and reached 44.3 distinct fresh programs. Mean final old practice scores were 76.7 and 76.3 respectively. At 4:1, the corresponding values were 30.1% versus 21.7% replay bytes, 46.7 versus 48.3 fresh programs, and 76.3 versus 76.7 old preferences. Neither diagnostic adjustment improved both primary and independent retention reliably. With an imposed 0.98 decay per row, the final live 4:1 arm scored 70–71 old practice preferences across seeds and fresh-only scored 72–73. That decay is an experimental parameter.

Archived grades establish the outcomes of the original workers. They cannot grade the counterfactual answers a newly trained native t80 would produce. This experiment therefore measures a program preference proxy. Official three-generation retention, a live delivery gain, and native wall-clock savings remain unmeasured.

## Reproduce

Each source archive is available from its original Actions run. The all-rows artifact IDs for G53 and G54 are 14594380286 and 14609313136. The four extracted JSONL SHA-256 hashes are in the result. Use the pinned byte ranker and gate-work manifest from commit `7fb2786e2203676238fcac5b301d0c3e232570d7` of PR 132. The runner verifies the ranker and each gate ZIP. It accepts gate archives named numerically in a cache, or files named `minority-ID.zip` in per-attachment directories. A complete reproduction uses all 96 archived gate-work ZIPs from G50–52 and G54–56. The principal scores can be read as standard gzip-compressed JSON. [Source cohort](https://github.com/Arnav123-s/HiveMIND/pull/132)

```sh
python -m training.experiments.replay_archive.chronology.run --measure /tmp/pr132_measure.py --rows /tmp/hive-astra-archives --manifest /tmp/pr132/artifacts.json --attachments /workspace/attachments --cache /tmp/hive-atlas-recovery-archives --out /tmp/chronology.json
```
