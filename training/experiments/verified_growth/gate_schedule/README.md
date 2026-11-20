# Schedule the same exam work on the same runners

A simple static schedule lowers the **modeled G52 gate from 66m03s to 52m06s**, a saving of **13m57s**. On G51 it lowers 99m47s to 79m33s, saving **20m14s**. Both projections keep 128 fresh and 60 fixed task executions, original runner start times, eight runners in each arm, and the original talk, smoke, setup and upload work. The largest projected fixed-exam step took 29m33s on G52 and 29m55s on G51, within the existing 40-minute timeout. These are same-work replays on two historical generations; neither schedule was deployed. [Frozen protocol](protocol.md) · [All placements and measured loads](results.json)

The schedule estimates the length of each new easy or hard task from the earlier median for that difficulty. For each previously known fixed task it uses the earlier median for that task. It starts with eight identical empty queues and assigns the longest predicted task to the shortest queue, separately before and after training. G51 uses only G50 timing history. G52 uses G50 and G51. No answers, scores or candidate outputs enter the scheduler. Ties use the task identifier. The task assignment is possible before sitting the exam. The alternative that charges each seat its own last-generation overhead did worse on G52; its G51 allocation would exceed the live fixed-step cap.

| Same 16 runners and tasks | G51 gate | G52 gate |
| --- | ---: | ---: |
| Observed hosted envelope | 99m47s | 66m03s |
| Round robin by task ID | 94m29s | 62m59s |
| Older durations, uniform initial queues | 79m33s | 52m06s |
| Older durations and per-seat overhead forecast | 78m30s, **cap exceeded** | 55m23s |
| Lower bound under the fixed per-arm runner budget | 49m33s | 36m14s |

The necessary bound uses average work per arm, the largest work item and the original non-movable seat overhead. It assumes perfect foreknowledge, divisible work where the average binds, and identical task durations after reassignment. In G52 even assigning by actual future durations, an unavailable hindsight control, only reaches 36m18s. Recovering 24 minutes by rescheduling is arithmetically possible in this model but the blind 16-runner policy recovered under fourteen.

**Calibration.** All three generations had complete per-task `exam.json` times for 188 distinct arm-task pairs. There were sixteen gate jobs each generation. Subtract the task durations from each runner's recorded start-to-finish time and retain the remainder on that original runner. Replaying the original placements therefore reproduces the observed envelope by construction. For a check independent of that identity, using the prior generation's per-seat overheads with the new generation's measured task durations reproduced G51 within 77 seconds and G52 within 43 seconds. The measured fresh and held GitHub step lengths differ from the summed task durations in either step by −1 to +56 seconds on G52. The simulation assumes that cache state, startup, upload, changing cpu/network speed, and differences in worker execution do not change materially when a task moves. Full same-identity execution and per-task process isolation would have to be verified in a real paired gate. [Compact times and job IDs](timings.json) · [Hosted G51](https://github.com/Arnav123-s/HiveMIND/actions/runs/44525337919) · [Hosted G52](https://github.com/Arnav123-s/HiveMIND/actions/runs/44594712108)

## Separate projection for the 33-job workflow

The combined checkout splits 16 fresh jobs, 16 fixed jobs and one talk job. G51 and G52 actually ran the older 16-job layout. For this projection, keep the exact measured fresh, fixed, talk and smoke step lengths on their original seed/arm. Charge each of the 33 jobs the full measured common setup/teardown time of its original host (host wall minus all task-bearing steps). At most 16 or 20 jobs can run. When a runner completes its first job it pulls the next waiting job; thus the second wave, cost of repeated setup, and long talk job are included. Compare an assumed matrix order (fresh first, talk last) with longest predicted job first based solely on the preceding generation’s stage lengths. GitHub queue order, other concurrent jobs and new network/download latency are unmeasured.

| Split job projection | G51 matrix → prior duration order | G52 matrix → prior duration order |
| --- | ---: | ---: |
| 16 simultaneous jobs | 67m10s → 67m38s | 56m39s → 47m31s |
| 20 simultaneous jobs | 61m02s → 61m02s | 51m44s → 40m01s |

On G52 the 20-slot order change saved **11m43s**, with a same-work floor of 39m17s. The estimated 40m01s uses four more simultaneous runners than G52 actually occupied. On G51 this change saved zero under the 20-slot cap; one long fresh job dominates. A talk or smoke suite that times out can also produce misleading speed gains, so completed case IDs remain essential in a live comparison. These split projections retain original within-seed task grouping; they are a different intervention from the 16-runner task reshuffle above. [Workflow](../../../../.github/workflows/grow.yml) · [Simulation](replay.py)

## Reproduce or export a plan

```sh
D=training/experiments/verified_growth/gate_schedule
python "$D/replay.py" --out /tmp/hive-gate-costs.json
python "$D/plan.py" --through g51 --example g52 --out /tmp/hive-g52-seat-plan.json
```

For a new cohort, supply `--ids ids.json` in place of `--example`, with the exact identities already generated for the new gate. The export contains the fresh and fixed IDs per arm and seat. An unknown fixed ID has no prior duration and the current exporter cannot schedule it. The existing grow workflow has no task-manifest importer. Executing a new balanced plan there would require retaining original task/seed identity and producing the same reports despite new execution seats. Original ZIPs and digests are listed in the [pulse archive manifest](../../atlas/pulse/artifacts.json). To rebuild the compact timing receipt, download the archive ZIPs named by ID, then fetch only job identities and step times for each run:

```sh
mkdir -p /tmp/hive-gate-gh
for row in g50:44474079616 g51:44525337919 g52:44594712108; do
  generation=${row%:*}
  run_id=${row#*:}
  gh api "repos/Arnav123-s/HiveMIND/actions/runs/$run_id/jobs?per_page=100" --paginate \
    --jq '.jobs[]|select(.name|startswith("gate ("))|{id,name,started_at,completed_at,steps:[.steps[]|{name,started_at,completed_at,conclusion}]}' \
    > "/tmp/hive-gate-gh/$generation-schedule-jobs.jsonl"
done
python "$D/extract.py" --zips /path/to/checked-zips --job-files /tmp/hive-gate-gh --out /tmp/hive-gate-times.json
```
