# Does a verification steering vector improve judgment?

Six contrastive prompt pairs describe checking versus accepting an answer. A CPU-native T80 generator computed a direction in each available transformer block from the difference in their activations. On eight separate short claims, the same 8B model returned its first greedy token under four conditions. The two vector arms used the same learned file in fresh servers with opposite scales. Applying its 11 selected vectors adds 45,056 scalar residual components per token (11 layers × 4096 components). The text reminder used an ordinary unmodified model. [Frozen protocol](protocol.md) · [All fitting pairs and test claims](study.json)

**All four arms made the same eight decisions and scored 2/8.** Positive and negative steering both changed the top-five token probabilities on every prompt. Neither changed the greedy answer. On the shipment claim the bare model assigned A a probability of about 0.50, versus 0.48 with positive steering. The proposed verification vector produced a measurable model effect with zero recovered mistakes. This evidence does not support enabling it by default.

| Native arm | Correct, /8 | Corrected bare mistakes | Changed top-five probabilities, /8 | Median seconds per request |
|---|---:|---:|---:|---:|
| Bare T80 | 2 | 0 | 0 | 17.66 |
| Prompt reminder | 2 | 0 | 8 | 18.75 |
| Positive vector, +1 | 2 | 0 | 8 | 19.77 |
| Negative vector, −1 | 2 | 0 | 8 | 16.63 |

All arms emitted A, A, A, A, B, A, A, B. Only the shipment count and 75% accuracy claims were judged correctly. For example, every arm incorrectly accepted the proposed value 9 for a counter that starts at 5, gains 12 and loses 9. Timing is descriptive. Arm order was fixed, all 32 prompts had zero cached tokens and the reminder adds text. This study gives no controlled latency advantage to either sign.

The claims cover arithmetic, aligned cache lines, classification accuracy, equilibrium water phase, cube volume, units and an inclusive byte range. Four are true and four are false. The user prompt requests A for a correct claim and B for an incorrect claim. Any other token misses. We independently recomputed the answer keys. A changed answer or log probability cannot establish that an internal verification procedure ran. This small fixed panel measures the first decision token, with no tool calls or written solution.

## Native intervention

The generator processed six paired inputs, space-padded unequal token lengths, collected nonzero per-token residual differences and normalized the mean direction within each layer. All 35 stored FP32 vectors have width 4096 and norm between 0.9999989 and 1.0000010. Fitting took 107.05 seconds using two CPU threads. The GGUF is 575,168 bytes, SHA-256 `03c7a911246184bf9a23aceea7481007294e30644ee5ce7a5dd44237b36d89f9`. This implementation pools activation differences over token positions. The original CAA paper uses contrasts at a designated position. [Generator implementation](https://github.com/ikawrakow/ik_llama.cpp/blob/7aa7e01482db892b023bb9aace9a40567ab5297a/examples/cvector-generator/cvector-generator.cpp) · [CAA paper](https://aclanthology.org/2024.acl-long.828/)

For each vector arm we started a fresh graph-reuse-disabled native server, loaded the GGUF once at the frozen scale, and selected the inclusive layer range 20–30. The loader scales the direction tensors and passes the range into the context when it creates the model. On Qwen3 the graph adds the selected direction to the residual after each selected transformer block. All four arms used greedy sampling, seed 991, no prompt caching and a one-token output budget with five log probabilities recorded for diagnostics. Every measured row retains the launch log name, prompt-token usage, output and latency. [Pinned loader](https://github.com/ikawrakow/ik_llama.cpp/blob/7aa7e01482db892b023bb9aace9a40567ab5297a/common/common.cpp#L4514) · [Qwen3 graph](https://github.com/ikawrakow/ik_llama.cpp/blob/7aa7e01482db892b023bb9aace9a40567ab5297a/src/graphs/build_qwen3.cpp#L91)

## Reproduce

From this directory, run `python verify.py` for a CPU-light integrity check and summary. The archive contains the actual trained vector and exact native fit/server logs. The raw JSON includes the SHA-256 of each original log, model, executable, vector and frozen panel.

```sh
python run.py --model "$HIVE_MODEL" --runtime "$HIVE_LLAMA_SERVER" \
  --generator "$HIVE_CVECTOR_GENERATOR" --threads 2 \
  --scratch "$TMPDIR/hive-steering-new" --out "$TMPDIR/hive-steering-results.json"
```

Use a new scratch directory. Add `--resume` to resume the same run after interruption. Building the pinned `llama-cvector-generator` target and reading the vector require the repository's native runtime and Python GGUF dependencies. [Native runner](run.py) · [Checked outputs](results.json) · [Vector and original logs](native-evidence.zip) · [Independent score check](verify.py)
