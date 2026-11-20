# Recovering a training slice after its process disappears

A one-CPU training slice completed exactly the same 32 optimizer updates after losing its process in the middle of row 95. With a retained checkpoint every five updates it executed **143 rows total**, versus **223** for an ordinary restart. That saved **80 row passes (35.9% of restart work)**. An uninterrupted run needed 128. The final trainable tensors, AdamW moments and step, adaptive sampler, entire row/loss history and random states were bit-identical. The three gradients accumulated after update 23 were discarded with the failed process. Restarting at the last published update, 20, recomputed all 15 rows after it. [Exact outcomes and costs](results.json) · [Frozen comparison](protocol.md)

| Trajectory | Rows lost or replayed beyond uninterrupted | Total rows |
|---|---:|---:|
| Uninterrupted | 0 | 128 |
| Process lost, restart from scratch | 95 | 223 |
| Restore update 20 | 15 | 143 |
| Newest snapshot truncated, restore update 15 | 35 | 163 |

The model trained 16,456 low-rank parameters on the 60 training examples from the six-domain T80 endpoint archive. The optimizer, clipping, learning-rate curve, adaptive subject picker and rank-four ternary layer come from the growth code. This small head uses cached 8B hidden states and base logits, cross-entropy over the 18 candidate tokens, and dropout to exercise PyTorch’s random state. Four microbatches contribute to an update. The experiment covers fixed work. The actual G53 training job updates transformer blocks under a time budget, a different workload. No release exam was involved. [Training slice](slice.py) · [Underlying 8B states](../../atlas/islands/README.md)

## What failed on G53

At the GitHub observation on 2026-11-20 at 03:58 UTC, two of twenty training jobs had failed; the other eighteen were still running. GitHub reported lost runner communication during “Grow the cell” for data shard 2/3 and writing shard 2/3. Their job lifetimes were 50:00 and 60:01. Time from starting the grow step until GitHub marked the job failed was 46:33 and 57:17. The record gives neither the last completed optimizer step nor the exact time the runner stopped computing. The two durations overlapped. The annotation lists several possible causes and does not diagnose an out-of-memory condition. Both artifact-upload steps were still marked pending. [Timestamped GitHub snapshot](hosted.json) · [Data slice](https://github.com/Arnav123-s/HiveMIND/actions/runs/44649281647/job/136025526418) · [Writing slice](https://github.com/Arnav123-s/HiveMIND/actions/runs/44649281647/job/136025526657)

The current workflow can join surviving sibling slices or reuse whole artifacts from another run. A clean training timeout can also return a finished adapter. Its `--checkpoint` switch controls recomputing intermediate activations to save memory. Its practice cache in PR #111 retains checked local lessons. Neither carries a running optimizer to another machine. The captured workflow copies files into `out/` after the training command returns, then uploads the completed part. [Workflow on the observed G53 commit](https://github.com/Arnav123-s/HiveMIND/blob/c2bd7a3d56e6728fe434b40118eda5c4abcd5ab6/.github/workflows/grow.yml#L577) · [Training update and final adapter write](../../../grow.py) · [PR #111](https://github.com/Arnav123-s/HiveMIND/pull/111)

## What survives

The prototype publishes only after optimizer update and gradient reset. Each checkpoint includes trainable parameters, AdamW state, the sampler’s remaining shuffled queues and feedback, RNG states, completed-update count, and the experiment’s row history. Input order, tensors, training configuration, source digests and PyTorch version bind the checkpoint to its original slice. The local store uses a single-writer lock, a flushed temporary file, a SHA-256 filename and atomic publication. Restoration checks newest complete objects first. An incomplete temporary file is ignored; a damaged newest object falls back to the previous one. A valid object from a different shard raises an error. The experiment actually terminates a worker process inside gradient accumulation, removes its working directory, and starts another Python process with a different hash seed. Only the separate retained directory and immutable source data are shared with the new process. [Publisher and loader](checkpoint.py) · [Fresh-process comparison](experiment.py)

In a separate control, restoring the same weights, row cursor, sampler and RNG while clearing only the AdamW moments produced different final weights. The six primary local publications occupied 216,073–218,761 bytes apiece and took a median of 6.21 ms to write, hash and publish. Those timings exclude any remote upload.

A hosted runner needs a durable destination that acknowledges each completed checkpoint **while the training job is alive**, and a replacement process that downloads a matching snapshot. The prototype's retained directory was on the same machine. Real deployment also needs to persist the exact encoded rows (including downloaded and judged examples), parent/trunk fingerprints, memory-guard state and any training counters that affect its gate. The current time-based learning-rate schedule must carry elapsed active budget across attempts; a different host’s free memory can change its sequence of skipped rows. Snapshot retention, transfer latency, scheduler wait and artifact storage must enter a hosted timing trial. This study measures avoided training work and local snapshot writing. It provides no observed reduction in generation wall time.

## Reproduce

From the repository root, with the repository’s CPU PyTorch environment:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python -m training.experiments.verified_growth.recovery.experiment --out /tmp/hive-resume-study.json
```

For a manual interruption, create the retained directory on a separate persistent filesystem and use distinct paths for the final models. The demonstration first exits with status 75. Run the two commands separately.

```sh
python -m training.experiments.verified_growth.recovery.slice --store /tmp/hive-checkpoint-demo --fail-row 95 --out /tmp/first.pt
python -m training.experiments.verified_growth.recovery.slice --store /tmp/hive-checkpoint-demo --resume --out /tmp/resumed.pt
```
