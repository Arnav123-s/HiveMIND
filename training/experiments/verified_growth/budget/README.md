# Will half the examples save 110 minutes?

Every successful G51 and G52 training slice ran until its time limit. All 35 stopped before making enough passes to visit half their eligible examples once. The median slice made 0.120 passes per eligible example on G51 and 0.100 on G52. An example can be repeated, so those ratios are upper bounds on unique coverage. The elapsed time of the last training job in each generation was determined by a failed runner. These are direct observations from the two completed 8B generations. [Training log excerpts and job IDs](training-logs.json) · [Counts](log-summary.json) · [G51](https://github.com/Arnav123-s/HiveMIND/actions/runs/44525337919) · [G52](https://github.com/Arnav123-s/HiveMIND/actions/runs/44594712108)

## The wall clock

The following minutes are nonoverlapping intervals from the first hosted job start to final completion. Preparation includes the parallel practice and dream branches, gather and plan, and inter-job waits. The training barrier runs from the first train job's start to the last train job's finish. The remaining columns separate the training-to-gate interval, the full gate, and the time from its completion to the end. The GitHub job API supplied every timestamp. [Snapshot](jobs.json) · [Reconstructed spans](timeline.json)

| Generation | Prepare | Train barrier | Join / merge / wait | Gate | Finish | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| G51 | 64.00 | 220.32 | 4.53 | 99.78 | 1.30 | 389.93 |
| G52 | 59.70 | 214.92 | 4.20 | 66.05 | 1.65 | 346.52 |

The slower failed job held the barrier open 43.50 minutes after the last successful G51 trainer, and 40.03 minutes after the last successful G52 trainer. A hypothetical earlier failure signal alone would leave 346.43 and 306.48 minutes. Restoring an interrupted slice and completing it may take longer. The simulation retains every recorded start and all time outside training.

| Counterfactual total minutes | G51 | G52 |
| --- | ---: | ---: |
| All recorded timings | 389.93 | 346.52 |
| Halve completed successful Grow steps only, retain failed jobs' observed endings | 389.93 | 346.52 |
| Halve the entire barrier, including all losses and overhead | 279.78 | 239.06 |
| Halve successful Grow steps and finish all failures by the new last successful completion | 261.20 | 220.91 |

That last, favorable scenario still needs 81.20 or 40.91 minutes. An explicit three-hour envelope would give preparation 40 minutes, training through its last worker 90 minutes, the complete gate 42 minutes, and join/merge/final waits 8 minutes. Applying that envelope to G52 would require saving about 20 preparation minutes, 125 training-barrier minutes and 24 gate minutes. A trial would need the same release questions, recovered slices and delivered grades to establish preserved quality. The envelope has not been run.

The archive’s nine G52 early stops applied to after-body jobs. The gate job that finished last was **before, seed 2**. Applying exactly those stops to the recorded after jobs would save zero gate wall time on that fixed schedule. G51’s critical gate was **after, seed 2**. Its two eligible tasks occupied 38 and 27 seconds in total. Even removing each entire task would save at most 65 seconds from the G51 gate. A prospective policy can also be tested symmetrically on the before arm. [Critical-job receipts](gate-bound.json) · [Original worker policy](../../atlas/pulse/composed/README.md)

There is a specific way to test shortening a gate while preserving its questions. The historical workflow ran the fresh exam and fixed held-out exam serially on each seat. We split their recorded step durations into 33 parts, retain all observed smoke/talk work, charge the original job overhead anew on each new part, and schedule on 20 slots. G52 takes **49.83 minutes** when all fresh parts are queued first, or **40.02 minutes** when queued by the previous generation’s part durations, compared with **66.05 observed**. The hindsight lower bound is 39.28 minutes. Only the G51-to-G52 transition was available to test this previous-generation ordering. The simulation assumes immediate runner availability, unchanged task durations and independent part execution. The earlier PR already defines split jobs. [Next candidate queue](next-gate-order.json) contains all 33 growing-body matrix entries, ordered by the latest observed G52 costs. It preserves the 16 fresh, 16 held-out and one conversation job. The separate DNA/versus trial matrix has different arms. Their real queueing, cache state, shared specialist versions and grading still need an end-to-end comparison. On G51, even the single longest preserved fresh part takes 61.03 minutes including overhead. Splitting fresh from held-out work alone cannot meet 42 minutes on that workload. [Per-step timestamps](gate-steps.json) · [20-slot queue simulation](gate-replay.json) · [Executable replay](replay_gate.py)

Combining the two favorable G52 changes gives **194.88 minutes**, comprising 59.70 preparation, 89.31 training, 5.85 intervening and final delays, and 40.02 for the complete gate. With the other assumptions fixed, preparation would still need to fall to **44.83 minutes or less**. For G51 the favorable training scenario plus the split gate is 222.45 minutes. That leaves 42.45 minutes still to save on G51.

At the recorded lengths of all other stages, training could consume only **10.38 minutes on G51 or 48.40 on G52** to satisfy three hours. The successful G52 slice's median first measurement of held-back lessons alone took 17.55 minutes. From job start through that first measurement, plus its equal time reserve for the end measurement, the median cost was 62.37 minutes. Under the unchanged setup and reserve, 11/17 successful G52 slices would have had no remaining update window in a 48.40-minute barrier. Changed sampling or hardware could change those costs. The reference checks also detect forgetting, so compressing them requires measuring the reliability of their replacements.

At the G53 snapshot two of 20 scheduled trainers had already failed and 18 were in progress. GitHub reported lost communication on those two runners. This partial generation supplies no total duration. [G53](https://github.com/Arnav123-s/HiveMIND/actions/runs/44649281647)

## Why example count and minutes diverge

The hosted workflow invokes the trainer with a positive minute limit, normally 170 on its CPU branch. With that limit, the ordinary sampler can revisit rows until the clock runs out, the allowed visit count is exhausted, or every available row is rejected by its memory guard. Without a minute limit, epochs bound completed row passes. Several row passes accumulate into an optimizer step. New-generation and repair rows are copied to every child slice; older rows are sharded. Subsampling inputs and shortening the update clock are different interventions. [Training loop](../../../grow.py) · [Workflow](../../../../.github/workflows/grow.yml)

The `--no-checkpoint` training flag controls gradient recomputation. A restartable checkpoint would also need the adapter, optimizer state, sampler and RNG position plus durable storage that survives loss of the runner. The workflow uploads the finished cell after the Grow step. Saving a recovery point can avoid repeating work after recovery. Measuring the improvement also requires timing failure detection and rescheduling through to a usable cell. [Growth and upload](../../../../.github/workflows/grow.yml)

The earlier 24/30 result came from cached output-head fits with the domain supplied for every question. Random half-samples also reached 24/30. In that study even total fit-plus-selection CPU changed by only about −4% to +4%. The corresponding costs and scores of an entire 8B slice require a separate measurement. [Atlas budget study](../../atlas/islands/README.md)

## Reproduce the timing audit

From the repository root, run the following commands with Python's standard library.

```sh
B=training/experiments/verified_growth/budget
python "$B/timeline.py" --out /tmp/hive-growth-timeline.json
python "$B/audit_logs.py" --out /tmp/hive-growth-log-summary.json
python "$B/replay_gate.py" --out /tmp/hive-growth-split-gate.json --next-order /tmp/hive-growth-next-queue.json
```

`timeline.py --capture /tmp/new-jobs.json --out /tmp/new-timeline.json` queries the public GitHub API through `gh` and refreshes the incomplete G53 view. `audit_logs.py --fetch /tmp/new-logs.json --out /tmp/new-log-summary.json` retrieves the 35 recorded G51/G52 job logs while they remain available. The compact checked-in records contain only relevant timings, sampling counts and IDs.

## A matched fit on the actual 8B CPU trainer

Both arms ran the complete released 36-block T80 model, updated rank-16 weights on its last 14 blocks with the stock optimizer, measured the same two reserved exchanges before and after, and exported real GGUF adapters. We explicitly selected one epoch and zero minute limit. This gives the smaller arm a shorter update schedule. The input pool was a subset of archived G11 practice and both arms started from the same published base. [Paired receipts](paired-results.json) · [Integrity check](verify_pair.py)

| Available rows | Row passes | Optimizer steps | Wall, seconds | CPU, seconds | Date loss before → after | Form loss before → after |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 8 | 8 | 2 | 602.82 | 1101.94 | 0.3184 → 0.2816 | 1.2093 → 1.1076 |
| 4 | 4 | 1 | 490.78 | 772.05 | 0.3184 → 0.3138 | 1.2093 → 1.2032 |

Halving the available examples and the scheduled passes saved 112.04 wall seconds (18.6%) and 329.89 CPU seconds (29.9%) in this single ordered pair. The four-row run came first. Both runs paid for model packing, held-back measurements and export. Another one-thread inference job overlapped early parts of the half run. A separate inference attempt overlapped its tail and the start of the full run. Each training worker stayed on the same two cores. The machine used the stock FP32 fallback since it lacks fast BF16 instructions. There were zero memory-skipped passes in either arm. The frozen-prefix cache recorded one repeat under each schedule. Both exports contained the expected 196 LoRA tensors. [Half-run stdout](half-trainer.log) · [Full-run stdout](full-trainer.log)

These scores are mean target-token losses, one question per topic. The full and half arms applied different numbers of updates as well as different samples and learning-rate schedules. Both measured losses were lower with eight rows. The cohort size and execution order limit the timing comparison. This pair supplies no estimate of whole-generation elapsed time, unseen-kind accuracy, or how long a half-dataset arm would run with the original positive 170-minute limit. The successful hosted slices above all stopped on time.

## Reproduce the paired stock-trainer pilot

The local pilot uses the same ternary 8B architecture, integer frozen base loader, rank 16, seven trainable projection pairs on each of the last 14 layers, gradient accumulation of four and the real GGUF exporter used by the CPU workflow. It starts from the released base, with no parent edit, no extra reading or judged pairs. Four versus eight available real G11 examples are trained with one epoch and zero minute limit. The trainer samples the order and can repeat examples, so a pass count alone does not establish unique exposure. The same two separately reserved G11 examples supply before/after teacher-forced loss. The checks measure predicted answer-token loss on two topics. Delivered outcomes require a separate gate. [Frozen design](protocol.md) · [Executable wrapper](paired.py) · [Exact stock training call](slice_bench.py) · [Environment and input identities](environment.json)

Use the repository's Python environment, the pinned native runtime checkout with its GGUF converter, and sufficient CPU memory and disk for the 16.4 GB unpacked checkpoint. Prepare an isolated Hugging Face cache, so its `main` reference can point at the study revision independently of any other project. The reproducible worker executes offline after this one download.

```sh
export HF_HOME="$(mktemp -d)"
export HIVE_TERNARY_HOME=/path/to/directory/containing/ik_llama.cpp
python - <<'PY'
from huggingface_hub import snapshot_download
from pathlib import Path
rev = "ac20f03fc62e872399218b659c8e949dfca05769"
snapshot = Path(snapshot_download("prism-ml/Ternary-Bonsai-8B-unpacked", revision=rev))
ref = snapshot.parent.parent / "refs" / "main"
ref.parent.mkdir(parents=True, exist_ok=True)
ref.write_text(rev)
PY
B=training/experiments/verified_growth/budget
python "$B/paired.py" --scratch /tmp/hive-paired-new --result /tmp/hive-paired-result.json
python "$B/verify_pair.py" --results /tmp/hive-paired-result.json --scratch /tmp/hive-paired-new
```

Use a fresh scratch directory. Each arm keeps its adapter, exported GGUF, source rows and training log. The paired launcher pins both workers to the same two available CPUs, records process CPU and wall time separately and stops its own worker if the shared Linux cgroup's estimated nonreclaimable charge approaches 14.5 GiB. The reported memory charge includes concurrent processes. Actual timing depends on host and cache state.
