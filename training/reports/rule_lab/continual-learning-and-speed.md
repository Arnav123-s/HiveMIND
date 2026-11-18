# Continual learning and faster CPU inference

## Real 8B inference

The biggest measured latency improvement came from preserving a compatible conversation prefix. Using the server's default Flash Attention setting, median end-to-end latency for the longer conversation fell from **17.08 to 4.92 seconds**. Each of the four settings solved 14/16 cases and all 64 replies were text-identical to the corresponding baseline reply. A repeated deterministic mistake accounts for the two failures in each setting. [Private-server benchmark](../../experiments/hive_runtime_bench.py) · [Timings, answers and learning results](learning-speed-measurements.json)

| Input and setting | Median seconds, full prompt | Median seconds, prefix reused | Median prompt tokens evaluated, full → reused |
|---|---:|---:|---:|
| 224-token request, Flash on | 6.39 | 4.20 | 224 → 102 |
| 708-token conversation, Flash on | **17.08** | **4.92** | 708 → 118 |
| 224-token request, Flash off | 6.64 | 4.11 | 224 → 102 |
| 708-token conversation, Flash off | 17.81 | 4.74 | 708 → 118 |

This was the exact regrown 8B calibration cell, one resident adapter, four CPU threads, a 2,048-token context, greedy decoding, and four distinct calibration worlds. Each timing is the median of six follow-up requests after the first request in each sequence. I reversed configuration and workload order on the second pass. Output generation stayed around 9–10 tokens/s. Fresh server processes took 5.1–6.2 seconds to load with the OS file cache warm, and peaked near 2.73 GiB. The cache saving is specific to overlapping prompts. The production client already allows cache reuse for the same active adapter set and disables it after a switch. Scheduling consecutive dependent turns on that same cell can realize the saving. [Production cache behavior](../../../team/ternary.py)

The pinned binary's help reports Flash Attention on by default. The server logs confirmed explicit on and off for every measured launch. An older 1.7B note recommends turning it on. On this 8B workload it modestly improved full-prompt latency and had mixed effects after caching. Query the deployed binary before changing the setting.

## Scratch-model speed and custom kernels

Moving ternary weight rounding to load time lowered a one-token forward pass from **5.46 to 1.48 ms** on the checked-in 2.6M-parameter stem. Against the original forward pass, the largest difference in any scored output logit was **zero** across 2,841 next-token positions in 96 task prompts. I wired this exact version into the scratch classifier loader and tested a checkpoint refresh through its normal serving entry. This checkout has no jobs assigned to that classifier in its holdings file. The latency numbers are measured on the stem. [Loader](../../../team/cells/tiny.py) · [Regression test](../../../tests/test_hive_cpu_learning.py)

| Prompt length, one sequence | Original scratch | Exact frozen weights | Byte-per-weight VNNI | Two-bit packed VNNI |
|---:|---:|---:|---:|---:|
| 1 token | 5.46 ms | **1.48 ms** | 1.38 ms | 1.43 ms |
| 8 tokens | 6.42 ms | **2.52 ms** | 2.27 ms | 2.23 ms |
| 64 tokens | 9.33 ms | **5.50 ms** | 6.95 ms | 8.66 ms |
| 128 tokens | 13.69 ms | **9.82 ms** | 11.85 ms | 15.02 ms |

These are medians of seven warmed timing blocks on one pinned CPU thread, including embeddings, attention, projections and vocabulary logits. The two custom kernels matched the integer reference on all 945 tested outputs, including signed extremes, all-zero rows and unaligned input widths. Their complete neural models agreed with the original top token on **2,835/2,841** positions. Rounding activation scales in a different arithmetic order can change a close decision. The exact frozen version retains the original sequence of operations and provides the better drop-in choice here.

Packing is worthwhile at a different size. For one 4,096-by-4,096 integer matrix and one input vector, the custom packed kernel took **0.540 ms** and the byte kernel **0.738 ms**. At 768-by-192, the byte path took **0.0100 ms** and packed took **0.0121 ms**. Both are warmed microbenchmarks on this Xeon. At longer prompts the custom code visits the weights separately for every input vector, while the existing float matrix multiplication shares work across the batch. A meaningful next kernel experiment would fuse activation quantization, accumulation and output scaling, then time complete prompts and inspect numerical agreement again. [Raw timing blocks and checks](learning-speed-measurements.json)

At the task level, the existing executable calibration memory solved all 512 affine worlds in a median **21.49 ms for the entire batch**, about **42 microseconds per world**, including its public consistency check. Sensor reads were in-process arithmetic here. This is a practical reason to route a recognized, verifiable procedure to a small cell, while reserving model calls for ambiguous requests, changes in behavior and conversation. [Executable memory](../../experiments/rule_lab_recipe.py)

## What to strengthen as the hive grows

| Mechanism | Strength observed in this hive | Weakness | How to strengthen it |
|---|---|---|---|
| Ternary backbone | The 8B model runs on CPU with a 2.03 GiB weight file shared by its specialists. | Small numeric changes can erase a learned skill. The runtime still reads billions of weights for a generated token. | Keep the backbone's quantization format and a functional test with every checkpoint. Fit scales during offspring training and score the completed task. |
| Exact weight engrams | One 4.26 MiB record regenerated a 38.04 MiB child exactly. | A different lineage cost about 30.4 MiB to reconstruct. Long ancestry chains increase recovery time and the impact of a lost ancestor. | Choose a parent using measured compressed size. Keep periodic standalone snapshots and test recovery with an ancestor offline. |
| Behavioral engrams and distillation | Two jobs fit in one small shared network. Saving low-confidence examples improved rare-case performance. | Examples miss behavior outside their coverage. A trace can exceed the size of the original small model. | Store ordinary experiences, counterexamples and disagreement cases. Compare actual bytes, both jobs' outcomes and the worst retained skill after repeated transfers. |
| Half-network repair | A different cell reconstructed the polarity task at 93.7% on the replication seeds using twelve learned shared channels. | Private hidden signals transferred poorly. The experimental connector had more weights than either original. | Standardize a few communication channels, preserve each cell's private state and try smaller connectors. Include direct use of the original observations as a control. |
| Sparse recall and referrals | Observable examples let the hive recognize a skill even when the user used different words. | Near-identical cues can require opposite actions. Probing a large archive adds latency and chance matches. | Shortlist locally, seek the cheapest distinguishing observation and record uncertainty when the requirement is ambiguous. Cap active specialists per task and let the archive grow separately. |
| Direct signals and sub-hives | Two one-byte messages supported 96.6% joint correctness on two partial-observation tasks. Regional addresses used about 29 link transmissions at 1,024 simulated cells. | Incompatible conventions, stale messages, and the cost of regional replicas can erase the benefit. | Version signals, bind them to the task, keep paired calibration examples and measure traffic including repair and retries. |
| Continual reinforcement | Monitoring delayed outcomes improved routing when a previously reliable assignment stopped working. | Constant exploration lowers utility in stable periods. A defective verifier can reinforce the wrong specialist. | Attach credit to the original decision, keep independent outcome checks, and compare against the frozen route at the same probe price. |
| Checks and executable procedures | A learned, checked affine procedure covered its entire 512-world family. | Some different laws agree on every permitted test point. Two related cells can repeat the same error. | Keep the procedure's assumptions and provenance. Seek a probe where alternatives disagree. Compare a model answer, a deterministic tool and a handoff on new task families. |
| A population with overlapping lives | Cells can survive, reproduce and contribute later even after failing a task. | More descendants consume storage and often share the same blind spots. | Keep population dynamics independent of task scores. Route work and allocate CPU by evidence, retain some exploration, and measure distinct verified skills and time to recover after an outage. |

The measurements behind these comparisons include the full-file checks, transfer failures, public-signal controls and population histories. [Reconstruction experiments](engrams-and-bitnets.md) · [Cell communication and sub-hives](hive-telepathy.md) · [Population experiment](hive-growth.md)

## Where to spend kernel work next

1. **Freeze mature scratch weights once.** The live scratch classifier loads a private evaluation copy when its checkpoint changes. It now computes the exact rounded weights once and releases the training weights in that copy. It keeps the same activation rounding at every call. Loading a new checkpoint rebuilds the evaluation copy. The training code retains its shadow weights and gradients. This optimization affects jobs actually assigned to the scratch classifier. [Serving path](../../../team/cells/tiny.py) · [Exact frozen layer](../../scratch.py)
2. **Choose a kernel for the actual matrix and number of input vectors.** The custom CPU experiment includes a simple byte-per-weight integer dot product and a two-bit version that expands positive and negative bit planes inside AVX-512 VNNI registers. Both subtract the input sum to compensate for the unsigned dot instruction. A portable scalar path supplies a reference. The scratch weights have one scale per layer. The published Bonsai format has scales per 128 weights and an existing interleaved native kernel. Porting this experiment to that format needs scale-aware accumulation and an end-to-end comparison. [C++ kernels](../../experiments/ternary_dot.cpp) · [CPU benchmark and numerical checks](../../experiments/hive_kernel_bench.py)
3. **Target the bottleneck before changing runtimes.** The earlier 1.7B measurements found 40, 64 and 76 total generated tokens/s for one, two and three simultaneous streams, then 28 at four. The tied output matrix took a slower path. A focused next trial is a repacked output-only copy with the original embedding retained for lookup. Charge the duplicate memory to the measurement. The current adapter switch acts on the whole server context. Group equal-adapter requests or verify per-request adapter isolation before batching different specialists. For hardware without VNNI, compare a lookup-table implementation on the same compatible checkpoint, prompts and quality checks. [Existing kernel profile](../../../docs/KERNELS.md) · [Microsoft T-MAC](https://github.com/microsoft/T-MAC) · [Microsoft BitNet runtime](https://github.com/microsoft/BitNet)
4. **Measure correct completed tasks per CPU-minute.** Track time to first token, generation speed, queueing, model starts and recovery separately. A faster token rate helps only when the model produces a valid answer with similar length and retry count. Under a fixed CPU budget, group consecutive calls that use exactly the same adapter set and cache only a matching prompt prefix. Include short, unrelated requests in the benchmark so a conversation-cache benefit is counted where it actually applies.

## A continual-learning design for the whole body

I tested online routing using the two real neural outputs regenerated from the earlier two-teacher memory. Four named stations issued 1,024 requests per stream. The job initially followed its historical assignment, changed at two stations, returned to its first assignment, and finally became unpredictable at those stations. The router saw only the station and observations it requested. Its binary reward arrived eight tasks later. An extra diagnostic observation cost 0.12 units in the chosen utility. That is an experimental price. The evaluator independently knew the correct answer. [Continual routing code](../../experiments/hive_continual_reward.py) · [Per-stream results](continual-streams.json.gz)

| Policy | Initial 24 streams, net points per 100 tasks | Next 24 streams, net points per 100 | Next 24 streams, actual pass rate |
|---|---:|---:|---:|
| Historical assignment, frozen | 85.9 | 86.2 | 86.2% |
| Always request an extra observation | 76.7 | 77.0 | 89.0% |
| Explore and use lifetime mean reward | 84.1 | 84.5 | 85.7% |
| Explore and favor recent reward | 84.5 | 84.8 | 87.4% |
| Same recent rule, feedback attached to the wrong action | 77.1 | 77.2 | 80.9% |
| Online policy gradient with exploration | 81.8 | 82.1 | 84.3% |
| Monitor continuously and switch on evidence of change | **89.5** | **89.5** | **89.5%** |
| Reference given the current job identity | 94.0 | 94.4 | 94.4% |

The better rule checked every returned result but changed the station's assigned specialist only when accumulated failures supported a decline from a 90% to a 55% pass rate. It used a sequential log-likelihood threshold of four and bound every receipt to the assignment in force when the task began. I introduced it after seeing the initial policies' results and repeated it on 24 additional seeds. Its paired gain over the frozen route on the replication was 3.3 net points per 100 tasks, with a 95% bootstrap interval of 2.9 to 3.6 across streams. During the switch phase it got 91.0 net points against the frozen route's 73.2. The unpredictable phase still favored other choices on some streams. The measured improvement applies to task assignments. Online LLM weight updates and open-ended conversation need separate experiments.

**Verifier failure reversed the result.** In a stress test one station accepted anything the second specialist returned. After the original job came back, the change-detecting router received 100% approval there while true success averaged **49.6%** on the replication. With the accurate verifier its true success at the same station was **90.7%**. Continual learning magnifies the quality of the feedback it receives. Use independent spot checks of actual outcomes and keep genuine failures available for rehearsal.

Use verified task outcomes to improve decisions the hive actually makes, such as which specialist to ask, whether to buy another observation and when to hand work to a tool. Give every decision a receipt containing the task, chosen action, active engrams and compute cost. Attach delayed feedback to that receipt. A cell's survival can remain independent of its contribution to this particular result.

A cheap routing policy can learn between completed tasks. For changes to neural weights, train a candidate adapter in occasional batches from verified experience, then compare the candidate and the current adapter on the same fresh tasks. Keep a sample of ordinary older tasks, uncommon skills and recent failures. A recurring environment may make an old skill valuable again. Replay is an established continual-RL method for retaining behavior across tasks. The right balance between old and recent experience still has to be measured for this hive. [Experience Replay for Continual Learning](https://proceedings.neurips.cc/paper/2019/hash/fa7cdfad1a5aaf8370ebeda47a1ff1c3-Abstract.html)

For conversation, record corrections, resolved requests and explicit user preferences separately from the model's confidence. For tool use, the receipt can include an independently checked output or state change. Keep some evaluation cases private from the learners, rotate them over time and score them independently of the reward producer. On a CPU-only system, ingest feedback as it arrives, update cheap routing counts immediately, and give background weight training a measured idle-time budget. Benchmark inference latency with learning active before assigning a permanent training share.

## Reproduce

These commands use the model assets in this worktree. The kernel benchmark needs a C++17 compiler. Run the timed benchmarks sequentially on an otherwise idle CPU. Use the reconstruction report's restore command to populate the exact adapter catalog in a fresh checkout.

```bash
PY=/workspace/HiveMIND/.venv/bin/python
LAB=runs/rule-lab
MEM=training/reports/rule_lab/engrams/two-teachers.npz
RT=/workspace/scratch/hivemind-runtime/ik_llama.cpp/build/bin/llama-server
"$PY" -m training.experiments.hive_runtime_bench --binary "$RT" --base "$LAB/assets/base.gguf" \
  --catalog "$LAB/engram-study/storage/catalog" --out "$LAB/runtime-replay"
"$PY" -m training.experiments.hive_kernel_bench --out "$LAB/kernel-replay"
"$PY" -m training.experiments.hive_continual_reward --memory "$MEM" --out "$LAB/reward-first.json"
"$PY" -m training.experiments.hive_continual_reward --first-seed 891 --memory "$MEM" --out "$LAB/reward-repeat.json"
```
