# Completing the CSV under the same total budget

The ordinary inspect worker wrote the correct CSV but exhausted the 192-token per-reply limit before it printed the count. Prompting it to read its own saved file with the same 192-token cap also failed. On this selected case, allowing that prompted turn to draw on the remaining budget changed the official whole-task result from **fail to pass**.

| Matched continuation on `x_h_edit_0` | Per-call caps | Output tokens used | Saved CSV | Printed result | Official grade |
|---|---|---|---|---|---|
| Original allowance | 192, 192, 192 | 192 + 192 + 192 = 576 | Correct | Empty | Fail |
| Remaining allowance | 192, 384, 156 | 192 + 228 + 2 = 422 | Identical bytes | `8` | Pass |

Both matched runs re-executed the same frozen first native response and charged all 192 tokens. Each then generated two fresh native replies on the same G55 adapter with the same greedy settings and three-turn, 576-token budget. Both gave the same follow-up message. The longer reply started with the entire earlier clipped response and then generated the code to reopen the CSV, count its records, and print the count. Its final reply was `DONE`. The worker used 154 fewer output tokens overall, about 27%. The two runs used different pairs of cores on the same host, so this comparison measures output and tokens. [Fixed-allowance receipt](../continue_stdout/native.json) · [Remaining-allowance receipt](native.json)

The implementation sets the existing larger-next-call option only after an eligible full-length response has run successfully, saved the requested file, and produced no explicitly requested stdout. The remaining global token budget bounds the larger call. Both `HIVE_CUTOFF_CONTINUE=1` and `HIVE_CUTOFF_CONTINUE_BORROW=1` are required. The worker sees the user's task and its own work. It generated the calculation itself.

This targeted case was chosen after observing its failure. It measures one recovery. Independent held-out outcomes require a separate run. The official F3 hosted comparison uses its original configuration and excludes both continuation options. [Frozen protocol](protocol.md)
