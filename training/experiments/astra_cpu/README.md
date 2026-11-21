# Training on a 16 GiB CPU runner

The handoff started from G55. G56 has since finished in 335 minutes and was dropped, with 48/64 fresh jobs against the incumbent's 51/64. The fixed exam gave the G56 candidate two correct answers in thirty, spread across too few questions per family to pass any of ten kinds. G55 remains the retained body. [G56 record](../../../docs/reads/g56.md)

## What the trainer can change

* On an explicit CPU trial, the trainer can recompute decoder activations for a row when ordinary backpropagation would exhaust available memory. The estimator accounts for the two alternatives separately, charges the output projection and both sides of a preference pair, and leaves room for the system. Short rows with enough room still use the usual path. [Admission rules and switches](memory_admission.md)
* A separate option computes answer-token loss in blocks, with gradients verified on both ordinary LoRA and the native ternary base. The labels, token normalization and preference objective stay the same. On two real G56 rows, the stock and 32-token block runs trained a full 8B CPU model from the same parent. All 16,973,824 adapter values and the exported GGUF were identical after the two updates. [Matched native run and reproduction](native-replay.md)
* Manual CPU trials can select an 85-, 110- or 170-minute clock and choose whether to balance the old rows across workers. New examples still reach every shard. A short trial bounds the initial evaluation and matches the before/after rows if it runs out of time. A timed slice that never updates its weights fails before export. [Clock controls and historical timing](budget.md) · [Shard and plateau replays](shards.md)

## Measured limits

The 563 skipped attempts cited in the handoff came from G51 code slice zero. G55 code slice zero skipped 1,481 attempts and completed 260 passes. G56 skipped 647 and completed 269. A scheduler can retry the same row. Counts at a single captured memory level describe candidate admissions, whereas the historical logs record actual attempts. [Original logs](code-s0-logs.json) · [Snapshot replay](admission.json)

On the 475-token native row, loss in blocks reduced per-row peak RSS from **12.158 to 11.801 GiB**. Elapsed time rose from **62.8 to 66.7 seconds**. The 198-token control used the ordinary projection in both arms, yet measured **31.6 and 37.2 seconds** under shared CPU load. The pilot does not clear the proposed 5% short-row latency criterion. [Per-row results](native-pair.json)

To isolate the vocabulary-sized allocation, we also ran one narrow Qwen3 layer with 128 hidden units, the real 151,669-word vocabulary and fixed inputs. On a 192-token answer the dense and 64-token runs peaked at 712.7 and 491.0 MiB. Loss and the tested layer's gradients were identical. The smaller model magnifies the relative contribution of output memory. [Narrow-model receipt](output_memory.json) · [Reproduce the measurement](output_memory.py)

Fifteen independently drawn and verified training lessons covered bank, calc, LRU, machine and schedule, three per kind. At a 508-token ceiling the trainer's existing context shortening let 22/30 turns through, including all fifteen short completion turns. Only **7/15** first turns carrying the actual solution fit. All fifteen solution turns encoded at 1,152. Encoding does not establish that a particular host can run backward on the row. [Fresh lesson lengths](lesson_lengths.json) · [Generator and real tokenizer](lesson_lengths.py)

Practice and dream already overlap, including all of practice on G55 and G56. Assuming exactly 85 minutes of savings from training, G55 still takes **224 minutes**. On G56 the same calculation plus immediate replacement of lost-runner tails gives **221 minutes**. Neither figure is a new hosted generation. [Critical-path replay](budget.md)

## Other waves in the handoff

Nine complete G45–G55 comparisons supplied 576 matched fresh exams. Neither the frozen sequential rule nor a bound that could guarantee the same winner stopped a single comparison early. The fixed exam can also overturn a fresh tie. The audit traces which prediction, verification and retention mechanisms already exist and what evidence could distinguish new ones. [Ticket audit and paired data](handoff_audit/README.md)
