# Can an old practice win guide a new child?

**Parent history gave six new workers a usable profile on 60 of 235 later requests. It changed zero choices and added zero correct answers.** The first worker on every after-body request was a newly merged trunk. Its original merge receipt listed 18 contributors, so there was no single parent profile to use. Among the 60 jobs with a newly profiled second worker, the first and second workers both scored 39/60. Always choosing the child there would have fixed two answers and spoiled two. On the other 175 jobs neither initial worker could reach a verified G50–52 practice profile. [Frozen follow-up protocol](protocol.md) · [Decisions, coverage and complete actor paths](results.json)

| G53–56 fresh requests | First worker | Prior direct chooser | Parent-profile chooser | Official delivery | Correct chooser / wrong delivery | Wrong chooser / correct delivery |
|---|---:|---:|---:|---:|---:|---:|
| After bodies, 235 common grades | 176 | 176 | 176 | 180 | 1 | 5 |
| Before bodies, 234 common grades | 176 | 176 | 176 | 182 | 3 | 9 |

The before-arm control obtained 40 additional second-worker profiles from parent history. First and second each scored 25/40 on those jobs, again with two gains and two losses if the child were always chosen. Nineteen further before-arm jobs had two directly verified profiles. Their original nine switches were preserved, with zero gains and zero losses relative to the first worker. The inherited chooser matched every selection of the prior direct chooser in both arms. The earlier study's exact-overlap rules and one missing second-worker grade in the before arm still apply. [Original study and denominators](../README.md)

### Which histories actually existed

Each gate used its own launch commit. We read prior released `cells/body.json` snapshots reachable on that commit's first-parent Git history and the recorded pre-gate child plan for that generation. A later decision to drop a body cannot supply an ancestry link. The plan for a candidate applied only to its after arm. We verified the source snapshots by SHA-256 and checked the 32 child assignments against one successful training slice per child: each logged the named parent download, mixture with the trunk, and 98 adapter matrices inherited. The four original trunk receipts each listed 18 inputs. This establishes the actual parent starting path for those slices; subsequent training, mixing and joining slices can all change behavior. [Run IDs, job IDs, pre-gate timestamps, parents and merge receipts](lineage.json) · [Evidence verification](collect.py)

| New child with a usable profile | Nearest named actor with a verified practice win | Parent links followed |
|---|---|---:|
| g53data2 | g49data | 1 |
| g54data | g51data | 1 |
| g55data | g51data | 1 |
| g55words | g51words2 | 1 |
| g56data | g49data | 2 |
| g56sources2 | g47sources | 3 |

The live plan receipts and generation-specific merge logs are accessible directly. [G53 plan](https://github.com/Arnav123-s/HiveMIND/actions/runs/44649281647/job/136024022482) · [G54 plan](https://github.com/Arnav123-s/HiveMIND/actions/runs/44685601437/job/136142373190) · [G55 plan](https://github.com/Arnav123-s/HiveMIND/actions/runs/44728930517/job/136291931426) · [G56 plan](https://github.com/Arnav123-s/HiveMIND/actions/runs/44776442973/job/136461401746) · [G56 actual trunk merge](https://github.com/Arnav123-s/HiveMIND/actions/runs/44776442973/job/136577232476)

This is a retrospective follow-up after seeing the earlier missing-profile counts and aggregate grades. We froze the ancestor rule before associating ancestry with the outcomes. It uses the same nine verified practice wins and word profiles, preferring exact worker identity, then the nearest documented single-cell ancestor. Two usable profiles are required to rank the first two workers. A merged trunk with its own verified profile can use it directly. A new trunk with several parents gets no assigned predecessor. After choosing from the pre-run roster we scored the actual archived worker outputs. Inverting every later worker and final grade preserved every route and inverted the number right as expected. No new model, inference-time reordering or release credit resulted. [Chooser and grade-independence check](replay.py)

From the repository root, reproduce the study and check the release snapshots against the local Git history:

```sh
python -m training.experiments.astra_retention.specialists.heritage.collect
python -m training.experiments.astra_retention.specialists.heritage.replay --check-label-independence --out /tmp/hive-heritage.json
```
