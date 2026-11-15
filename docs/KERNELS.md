# Where the hive's time goes, and what the kernels do (measured 2026-11-14)

All numbers are from this repository's machines: a 4-core Intel Xeon at 2.1 GHz with AVX2, AVX-512 BF16, AVX-512
VNNI and AVX-VNNI, like GitHub's runners, running the ternary runtime ik_llama.cpp at the pinned commit 7aa7e01. Model
t17 (Ternary-Bonsai-1.7B, PQ2_0), 4 threads, `-rtr`.

## The short version

1. **Generation is near what the memory can deliver.** About 37 tokens a second, reading the 436 MB model once
   per token: about 16.6 GB/s. The ternary matmul kernel is already good, so rewriting it would gain little for one
   stream.
2. **Several streams at once is the big lever: 1.64 times the throughput for two, 1.9 times for three.** The CPU
   reads the weights once for all streams. Members now run one after another. Running the first two at once needs
   one change in the runtime (below).
3. **A slow kernel makes four or more streams slower than one** (27.6 tokens a second for four, against 40 for
   one). The hive does not hit it today, but it will as soon as it decodes four streams at once.
4. **Cells cost little at inference:** about 5% slower generation with a cell on (36.0 against 38.1 tokens a
   second); prompt speed is unchanged.
5. **Flash attention (`-fa`) speeds prompts up by about 18%** (282 against 240 tokens a second for 512 tokens)
   and leaves generation unchanged. The hive's server does not use it yet; members' output is long, so the gain
   to a whole task is a few percent.
6. **Training: the frozen layers' work is now done once per row** instead of once per pass (`grow._Prefix`).
   The cell comes out identical (difference 0.0).

## 1. The ternary matmul (good)

- Weights: PQ2_0, 2 bits a weight and an fp16 scale per 128 (`ggml/src/ggml-common.h`, `block_pq2_0`). With `-rtr`
  the layers' 196 tensors are repacked to PQ2_0_R8 (8 rows interleaved).
- Kernel: `mul_mat_T_q8_k128` in `ggml/src/iqk/iqk_gemm_1bit.cpp` (about line 1830). It unpacks the 2-bit codes
  with AVX-512 shifts and masks, and multiplies with `_mm512_dpbusd_epi32` (VNNI int8 dot products) against
  activations quantised to Q8_K128. It handles 1 to 8 activation rows with the same fast code (templated `nrc_y`).
- Measured: one sequence, prompts of 1, 2, 3, 4, 5 and 8 tokens: 34, 72, 93, 130, 153 and 194 tokens a second. It
  scales smoothly.

## 2. The cliff at four streams (a slow kernel on the output layer)

`llama-batched-bench`, a prompt of 128 then 32 generated tokens per stream, generation tokens a second in all:

| streams | 1 | 2 | 3 | 4 | 6 | 8 |
|---|---|---|---|---|---|---|
| tokens/s | 40.1 | 64.0 | 76.5 | **27.6** | 37.6 | 48.8 |

Flash attention does not change it (25.7 at four streams). The cause:
- The tied embedding (`token_embd`, 151,669 x 2048, also the output layer) is **not repacked**. It is used for
  embedding lookups as well, so it stays PQ2_0 (`Repacked 196 tensors` in the server log: the layers only).
- Unrepacked PQ2_0 goes through ggml's generic path. `ggml/src/ggml.c` about line 18955: "If there are more than
  three rows in src1, use gemm; otherwise, use gemv". With four or more output rows (four streams decoding) it
  takes `ggml_gemm_pq2_0_q8_K` (`ggml/src/ggml-quants.c` about line 16514). That kernel unpacks the 2-bit codes
  one element at a time in a scalar loop and uses 128-bit SSSE3, on the largest matrix in the model.
- Fixes, from small to proper: (a) give PQ2_0 no `gemm` (`ggml.c` type traits about line 1819), so all rows take
  the vectorised `gemv` path; (b) keep a repacked copy of the output layer for the matmul (about 79 MB more);
  (c) write an AVX-512 `gemm` for PQ2_0 that unpacks the way `DequantPQ2_0_R8::dequant_avx512` does and reuses each
  unpacked block for all rows.

## 3. Several cells in one batch (the change that makes members run at once)

The runtime applies cells globally. `llama_lora_adapters_apply(ctx, lora_adapters)` in
`examples/server/server-context.cpp` (about line 3306) sets one scale per adapter for everything the context
computes, and `/lora-adapters` changes it. Two members with different cells therefore cannot decode in one batch.
What it takes:
- In the graph (`src/llama.cpp`, where each adapter's `B(A x)` is added to a projection): multiply each adapter's
  contribution by a per-token scale (an input tensor of shape `[1, n_tokens]`, set for every batch from each token's
  sequence), with `ggml_mul` broadcasting it.
- In the server: a cell per request (slot), as recent llama.cpp servers take a `lora` field per request, and
  `--parallel 2` or more.
- In `team/solo.py`: start members 1 and 2 at once (threads), each on its own slot with its own cell.

Expected: about 1.6 times the speed on every sitting, practice and gate, where two members work. With fix 2 in
place, more tasks can run at once beyond that.

## 4. Training (PyTorch on the CPU)

- A cell trains LoRA on the last 14 layers. The layers below are frozen, so for a given row they compute the same
  thing on every pass. `grow._Prefix` keeps their output from the first pass of each row and skips them on later
  passes. Checked: training three passes with and without it gives identical cells (difference 0.0); a test on a
  small model is in `tests/test_prefix_cache.py`. The saving is a quarter to a third of the forward work from the
  second pass on, more for t40 and t80, which have more frozen layers. It is not used with recomputation
  (`checkpoint`), where a layer recomputed on the way back would be fed the wrong input.
- The DNA can be held ternary while training (`training/ternary_base.py`, `--int8-base`): one byte a weight, and
  the numbers are rebuilt per layer on the way forward and back. Possible next step: a matmul that uses the int8
  codes directly (`torch._int_mm` or a small C++ extension with VNNI), instead of rebuilding bf16 weights at every
  call.
- Rows: the loss and the logits are computed on the answer tokens only (`logits_to_keep`), already.

## 5. Training an 8B cell on a 16 GB machine (measured 2026-11-15, the real Ternary-Bonsai-8B, 4 cores)

The first 8B cells trained at 14 to 162 seconds a row and one in four died: the DNA was loaded as 16-bit numbers
first (16 GB), then held with its word vectors and output layer as numbers, and a long row pushed the runner into
its swap. What is held now, and what a row costs (`training/ternary_base.py`, LoRA rank 16 on the last 14 layers):

| | before | now |
|---|---|---|
| held after loading | 9.4 GB, after a peak above 16 | 8.1 GB, never more while loading |
| time to load | about 8 minutes | 80 seconds |
| a row of about 470 pieces, first pass | 14 s on a runner that did not swap, 30 to 162 s on those that did | 9 s |
| the same row on later passes (frozen layers' output kept, on disk) | | 4 to 5 s |
| memory while training | 14.9 GB and swap | 10.8 GB at 256 pieces, 13.3 GB at 1024 |

- Every piece of a row costs about 5 MB while it is trained on (46 values of the hidden size for each trained
  layer). Rows are capped to what fits the machine: about 1000 pieces on 16 GB. A row of 1152 pieces ran this
  15 GB machine out of memory.
- Where a row's time goes now (400 pieces, 8.5 s): rebuilding numbers from codes 2.8 s, multiplying 2.3 s forward
  and 0.5 s back, the output layer and the two widest projections 2.5 s, the rest about 2 s.
- The C routine that rebuilds a matrix from its codes (`ternary_base._C`) takes 6 ms for 50 million weights where
  PyTorch takes 57 ms. Alone it moved a row's time little; what remains is spread over many parts.
- Tried and not better: jemalloc that never returns memory (out of memory), huge pages always (25% slower),
  not giving memory back after each step (4% faster).
- Not tried: several rows in one forward pass (one rebuild of the weights for all of them; needs padding and
  about 5 MB a piece of memory for every row in the batch).
