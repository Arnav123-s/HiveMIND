# Scheduling fixed exams around training

The observed G56 gate took **53.45 minutes**. A timing replay that moved incumbent exams into the final training slots and split five candidate seats finished in **33.60 minutes**. G56 supplied an unusually long window while two training slices waited for cancellation. Removing that 29.13-minute wait from the same trace raised the projected gate to **62.18 minutes**. Those two savings cannot be added.

| Generation | Observed gate | F1 paired replay | Incumbents start early | Early + split five candidate seats |
|---|---:|---:|---:|---:|
| G55, schedule calibration | 56.97 | 93.77 | 42.92 | 40.05 |
| G56, forward replay | 53.45 | 116.95 | 41.07 | 33.60 |
| G53, earlier complete gate | 70.92 | 99.00 | 42.43 | 46.98 |
| G54, incomplete held seats | 51.38 | 94.32 | 44.17 | Unscorable |

Times are minutes from availability of the candidate to completion of the grade collection. The observed column uses actual first gate job start and last gate completion on GitHub. The other columns use recorded runner durations with alternative start times. G55 supplied the scheduling rules and priorities. G56 task durations enter only when their simulated jobs finish. G53 and G54 test sensitivity to conditions before calibration. [Results](result.json)

**Overlapping unchanged seats carries the clearest signal.** It helped in all four replays without increasing runner work. Sharding alone gave 44.25 minutes on G55 and 68.77 on G56. The combined policy cost an additional **25.35 runner-minutes** on G55 and **21.23** on G56. G53 got slower when it added the shards to its overlap. The serving and training workflows retain their existing schedules.

## What the replay preserves

- The inputs are the 128 GitHub fresh/held grade ZIPs and 348 job records across four public growth runs. Extraction verifies every ZIP against GitHub's SHA-256, verifies task counts and grade totals, and retains per-item seconds, original seat positions and set digests. The scheduling input contains no prompts, answers or per-task grades. A separate historical statistic determines whether the paired baseline would have stopped. [G53](https://github.com/Arnav123-s/HiveMIND/actions/runs/44649281647) · [G54](https://github.com/Arnav123-s/HiveMIND/actions/runs/44685601437) · [G55](https://github.com/Arnav123-s/HiveMIND/actions/runs/44728930517) · [G56](https://github.com/Arnav123-s/HiveMIND/actions/runs/44776442973)
- All schedules cover the same 128 recorded fresh tasks per generation, every recorded fixed task and the whole talk job. Fresh seat two retains its smoke test. G55 recorded 59 of 60 fixed grades, G56 and G53 recorded 60 each, and G54 recorded 55. One G55 incumbent seat spent another 831 seconds on unfinished work. It stays intact. G54 has incomplete candidate seats, preventing a scored split replay. The whole-seat schedules charge their complete recorded durations, including interrupted work.
- The paired baseline runs the F1 four-seed batch with all fixed seats and talk, then batches 5–6 and 7–8. None of the historical looks crossed its stopping threshold. The replay gives the two look jobs zero checkout, evaluation and dispatch time. The rank rule uses G55 durations and the number is specific to that list schedule.
- All 20 training jobs must have started before any incumbent exam becomes eligible. An incumbent uses only its original body and the run's fixed seeds. The dispatcher caps early exam jobs at 11, reserving nine slots for the eight joins and other upstream work. After the first actual candidate gate start, it allows all 20. Every training, join and merge interval retains its observed start and finish. The simulator checks combined occupancy at every transition. At candidate readiness, 11 incumbent jobs were still running in G55 and three in G56. This preserves the training critical path by construction. GitHub queue priorities and overlap have not been tested on a hosted generation.
- Candidate held seats taking more than 25 minutes in G55 are divided into two contiguous halves. This picked seats 2, 4, 5, 6 and 8. Runner assignment uses the prior G55 durations, with indices preserved in the original seat. Each extra shard pays the original seat's setup, post-exam steps and positive residual time. Observed G56 setup ranged from 146 to 422 seconds, with median 211. The central case adds 60 seconds for another cold start per new shard, 10 seconds between runner assignments and 60 seconds for final reassembly. These extra penalties are assumptions. With no extra cold or reassembly cost, G56 takes 32.60 minutes. Charging 120 seconds each and a 30-second assignment gap gives 34.60.
- Even allowing all measured pre-candidate spare slots to be used perfectly, G55's work needs at least **32.67 minutes** after candidate readiness under this 20-runner budget. This bound assumes conserved historical work and zero new setup. G56's unchanged talk job alone requires 28.73 minutes. Neither run establishes a 30-minute gate or a three-hour generation.

## Reproduce locally

```sh
python -m training.experiments.astra_cpu.gate_timing.replay
pytest -q tests/test_held_halves.py tests/test_held_exam.py tests/test_paired_gate.py tests/test_gate_look.py
```

The replay uses the compact checked-in [timing traces](traces.json). To audit upstream, cache each run's public jobs JSON and original grade ZIPs in `g53/` through `g56/`. Each folder's `index.json` has `run` and `archives` with the GitHub artifact `name`, `id`, `size_in_bytes` and `digest`. Jobs JSON is the response to `actions/runs/RUN/jobs?per_page=100`. The ZIP filenames match each artifact name. [Extractor](extract.py)

```sh
python -m training.experiments.astra_cpu.gate_timing.extract "$ARCHIVES" /tmp/gate-traces.json
cmp /tmp/gate-traces.json training/experiments/astra_cpu/gate_timing/traces.json
python -m training.experiments.astra_cpu.gate_timing.check_join "$ARCHIVES"
```

## Try an isolated held seat

The optional runner uses the normal fixed questions, checks, timeouts, worker selection and empty exam memory. Set `HIVE_MEMBERS` to the same frozen worker roster on both hosts and use a unique run-attempt-and-arm group on both hosts. Each half starts with empty memory. The original seat can read a previous question's saved program when `HIVE_LIBRARY=1`, so that configuration requires the original unsplit seat.

Run the first line with `--half 1` and `--half 2` on separate independent runners, then collect both result files in one directory and run the join. The join checks run identity, worker roster, settings, original task IDs, task text, order and grade totals before it writes the standard seat artifact. Part files have separate names and the normal recorder does not read them. For missing halves or incompatible receipts, retry that half on the same body or run the original complete seat. Rejoining the official archives preserved all 224 full grade rows from 60 complete held seats, and refused the four partial seats. [Reassembly receipt](join-result.json)

A hosted comparison must measure startup, reassembly, all returned grades and the full generation wall clock.

```sh
python -m training.experiments.astra_cpu.gate_timing.halves sit --seat 4 --half 1 --group trial1-after --parts-dir parts
python -m training.experiments.astra_cpu.gate_timing.halves join --seat 4 --group trial1-after --parts-dir parts --out held-after-4
```
