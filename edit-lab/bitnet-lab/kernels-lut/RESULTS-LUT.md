# RESULTS-LUT — lookup-table ternary×int8 matmul (Muse's work, Muse's side)

Strike team A, 2026-11-12. Code: `bench_lut.py` in this folder. Raw records:
`results.jsonl`. This stream did not touch `kernels/` or `train.py`.

## Verdict (plain)

- **Correctness: PASS, bit-exact.** Both LUT variants reproduce the plain
  torch reference with **max abs error 0.0** at every lab shape tested
  (50 checks, including a full-width N=8192 champion check).
- **Speed: NOT MEASURED — no verdict.** The scale ladder held the lab
  continuously for the whole session (10M seeds, then the 50M rung,
  launched 04:23:15Z with an est. 5100 s run, more rungs queued behind it).
  Per the yield rule, no timing number was recorded under contention rather
  than polluting the table. The timing phase is one command when the lab
  frees (below) and appends to the same `results.jsonl`.
- **Not trainer-ready regardless of speed** — forward-only; see the
  STE-wrapper note at the bottom.

## What was benchmarked

The trainer's BitLinear quantizes weights to ternary {-1, 0, +1} and
activations to int8, then multiplies in fp32 (`F.linear`). The core op is
`Y[n,m] = Σ_k W[m,k]·X[n,k]` with W ternary, X int8-valued. Per-matrix weight
scale and per-token activation scale are scalars applied outside the matmul,
identical for every variant, and excluded. All core values are integers with
|Y| ≤ 2048·127 = 260,096 < 2²⁴, so fp32 arithmetic is **exact** in any
summation order — the reference is an exact oracle and any nonzero error
would be a real bug, not rounding.

Shapes = the four BitLinear matmuls per block (qkv K→3K, out K→K, up K→4K,
down 4K→K), N = 8192 token rows (one trainer step, batch 32 × CTX 256):

| rung | dim × layers | ternary weights | matmul shapes (K→M) |
|---|---|---|---|
| champion (~0.885M) | 192 × 2 | 884,736 | 192→576, 192→192, 192→768, 768→192 |
| scale2m | 288 × 2 | 1,990,656 | 288→864, 288→288, 288→1152, 1152→288 |
| scale10m | 512 × 3 | 9,437,184 | 512→1536, 512→512, 512→2048, 2048→512 |

Ternary weights drawn with the ladder's recorded state distribution
(−1: 0.344, 0: 0.308, +1: 0.344); activations uniform int8. CPU only,
torch 2.15.0+cpu, threads pinned at 2 (OMP/MKL=2), venv python.

## Variants

- **ref** — `F.linear(X_fp32, W_fp32)`, the trainer's actual op. Oracle.
- **lut2** — TL2-style, group g=2. Per token and input pair, a 9-entry table
  of all signed pair sums s₀x₀+s₁x₁ (s ∈ {−1,0,1}²), built with one small
  matmul against the 9 sign patterns. Each output gathers K/2 precomputed
  pair sums by the weight pair's base-3 code and adds them.
- **lut4** — group g=4, 81-entry tables built by combining two pair tables
  (hi pair × lo pair); K/4 gathers per output.
- **int8mm** — context row only (not LUT): `torch._int_mm` with ternary
  weights stored as int8. Included so a future LUT number can be judged
  against a purpose-built integer GEMM, not only against fp32.

Weight base-3 codes are computed once per matrix (in a real deployment the
codes *are* the weight storage) and excluded from timing; table construction
depends on the activations, is per-forward work, and is inside the timed
region.

## Correctness table (max abs error vs ref; 512 rows per shape)

| rung | K→M | ref | lut2 | lut4 | int8mm |
|---|---|---|---|---|---|
| champion | 192→576 | 0.0 | 0.0 | 0.0 | 0.0 |
| champion | 192→192 | 0.0 | 0.0 | 0.0 | 0.0 |
| champion | 192→768 | 0.0 | 0.0 | 0.0 | 0.0 |
| champion | 768→192 | 0.0 | 0.0 | 0.0 | 0.0 |
| scale2m | 288→864 | 0.0 | 0.0 | 0.0 | 0.0 |
| scale2m | 288→288 | 0.0 | 0.0 | 0.0 | 0.0 |
| scale2m | 288→1152 | 0.0 | 0.0 | 0.0 | 0.0 |
| scale2m | 1152→288 | 0.0 | 0.0 | 0.0 | 0.0 |
| scale10m | 512→1536 | 0.0 | 0.0 | 0.0 | 0.0 |
| scale10m | 512→512 | 0.0 | 0.0 | 0.0 | 0.0 |
| scale10m | 512→2048 | 0.0 | 0.0 | 0.0 | 0.0 |
| scale10m | 2048→512 | 0.0 | 0.0 | 0.0 | 0.0 |
| champion (N=8192) | 192→768 | — | 0.0 | 0.0 | — |

50 checks total, 0 nonzero, 0 errors. As predicted by the exactness
argument, the LUT gather path is bit-identical to the fp32 GEMM — a LUT
win, if one exists, costs nothing in output accuracy at these shapes.

## Timing table

**Deferred — lab contention.** Every timing cell is gated on a free lab
(no ladder / mill / growth / foreign train.py process). The gate never
opened during this session: the ladder ran 10M seed 1, waited out another
stream's train.py at 04:21:15Z, then launched 50M seed 0 (est. 5100 s) at
04:23:15Z with plain-2M seeds, 10M seed 2, and 50M seed 1 still queued.
The timing waiter was stopped after ~13 minutes with zero cells recorded,
rather than leaving it polling for hours. Re-run when the ladder drains:

```
cd ~/workspace/edit-lab/bitnet-lab/kernels-lut
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 \
  ~/workspace/edit-lab/fable-validation/venv/bin/python bench_lut.py timing --wait-s 600
```

It times each shape × variant (median ms/call at N=8192, adaptive reps,
1 warmup), appends per-cell records to `results.jsonl`, and writes
per-rung block/full-model totals to `summary_timing.json`.

Design-level expectation, **not a measurement**: in pure PyTorch the gather
path materializes an [rows × outputs × groups] tensor per chunk, while
`ref` is a single BLAS GEMM — T-MAC-style LUT wins in the literature come
from custom SIMD kernels, not framework gathers. Expect lut2/lut4 to lose
to ref in torch; the bench exists to put a number on how much, and the
int8mm row to show the realistic integer-GEMM bar. Do not quote this
paragraph as a result.

## STE-wrapper note (why nothing here is trainer-ready)

These benches are **forward-only**. In the LUT variants the weights enter
only as integer base-3 codes indexing a gather — there is no differentiable
path to the weights at all, so autograd cannot produce a weight gradient
(the activation-side path through the table build exists, but that is not
the gradient a trainer needs). Before any variant could be used in
training it would need a straight-through-estimator wrapper: run the LUT
forward on the quantized weights, and in the backward pass pass the
gradient through to the fp32 shadow weights (and, for the vote trainers,
to the vote counters) as if the quantization were the identity — the same
ease-in STE pattern `train.py`'s BitLinear already uses around its fp32
`F.linear`. Until that wrapper exists and a wrapped run reproduces a
reference training trajectory within seed noise, **no LUT variant is
trainer-ready, whatever the timing table eventually says.**
