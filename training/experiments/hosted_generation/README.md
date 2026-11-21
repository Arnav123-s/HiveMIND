# G58 hosted CPU generation

GitHub recorded a user cancellation **2 hours 20 minutes 46 seconds after dispatch**. The twenty training jobs started, five finished their optimizer loops, and none uploaded a slice artifact. No model reached the fresh or held-out exam. This run leaves generation time to completion and score unknown. GitHub's check annotation reads “The run was canceled by @Arnav123-s.” [Workflow run](https://github.com/Arnav123-s/HiveMIND/actions/runs/44857277686) · [Annotated check](https://github.com/Arnav123-s/HiveMIND/runs/136718591564) · [Measured receipt](g58.json)

| Observation | Measured result |
| --- | --- |
| Practice and dream | All 12 practice and 8 dream jobs succeeded. Their overlapping phase spans were 32m28s and 41m00s. |
| Checked corpus | The verified ZIP held 9,373 rows, including 553 new G58 rows. |
| Training assignments | All 20 participated. The first started at 03:41:49 UTC and the last at 04:13:50 UTC. The longest wait from job creation to runner assignment was 32m03s. |
| Optimizer progress | At least 255 updates are observable in 11 logs. Five completed-loop logs establish 125 exact updates altogether. Six further jobs logged at least 130. Nine ended without a numbered progress heartbeat. |
| Memory guard | Five complete guard summaries recorded zero skip attempts. Six more showed zero through their latest heartbeat. The final counts for the other 15 jobs are unavailable. |
| Length limit | Across the 20 input slices, 1,512 row presentations exceeded their encoding limit. A repeated row seen by several slices counts several times. |
| Reached before cancellation | No final per-kind row ledger was published. The number of otherwise eligible rows never reached and the number of distinct rows ultimately skipped for memory are unknown. |
| Evaluation | No paired seeds, fixed held-out grades, adapter, or generation-record artifact. |

The 20 logs report nine 16-bit training paths and eleven 32-bit paths. The exact-update calculation uses the run's four-pass gradient accumulation. Once the loop reports its final pass count, it flushes the last partial update before printing its final memory summary. In an interrupted loop the last numbered optimizer heartbeat supplies only a lower bound. G57's production scores belong to a separate run.

## Reproduction

The receipt reads the public workflow run and job metadata, all 20 training logs, and the artifact inventory. Download the original `all-rows` and `lessons` ZIPs without unpacking them. The report checks the GitHub-provided SHA-256 digest before reading them. G58's immutable checkout was `be3a12a70b799dc50f6e0566379176d97762f13f`.

Place the workflow object in `run.json`, the job and artifact arrays in `jobs.json` and `artifacts.json`, and each training log in `<job-id>.log` inside the same local folder as the two ZIPs. An optional `annotations.json` contains the cancellation check ID and GitHub's message. This study used the GitHub artifact and workflow-job-log connectors. The corresponding REST read endpoints are `actions/runs/<id>`, `actions/runs/<id>/jobs`, `actions/runs/<id>/artifacts`, `actions/jobs/<id>/logs`, and `check-runs/<id>/annotations`.

```sh
python -m training.experiments.hosted_generation.receipt /tmp/hive-hosted-g58 --out /tmp/g58.json
```
