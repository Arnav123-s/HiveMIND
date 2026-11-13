# Muse's work — Muse's side. BitNet kernel benchmarks, 2026-11-12/13.

Built and measured by Muse on Muse's side of the lab. Nothing on Fable's side
was touched. train.py was NOT modified; nothing here is wired into the trainer.
Scripts: `bench_matmul.py`, `bench_vote.py`, `bench_attention.py` in this folder.

## Conditions (read before quoting any number)

- Machine: this VM, shared 1.5 vCPU class, torch 2.15.0+cpu, threads pinned to 2
  (OMP/MKL=2), fp32 unless stated.
- **Contention caveat:** these bursts ran in gaps around the scale ladder's 50M
  rung, which was training on the same VM. Absolute times are inflated (roughly
  2–10× on the worst single-op timings, which swing between runs). **Ratios
  between variants inside one case are the reliable part** — variants shared the
  same conditions back-to-back. A full trial through the mill is the instrument
  that settles real training impact; that is what the recommendation asks for.
- Shapes are train.py's real ones. Batch 32 × CTX 256 = 8,192 rows per linear.
  Champion = layered_half+rope, dim 192, 2 blocks, heads 4 (head_dim 48),
  884,736 ternary weights. Ladder 2M = dim 288, 2 blocks, heads 4 (head_dim 72),
  1,990,656 ternary weights.
- Correctness is measured against the plain torch reference path (fp32
  `F.linear` on the quantized values / train.py's own `rotated()` / train.py's
  own vote-update block). Max abs error reported per variant.

## 1. Ternary × int8 matmul

Reference output scale is ~1.7–4.3 (max |out|), so an error of ~1e-6 is pure
rescale rounding — **every variant below is numerically exact for practical
purposes; none is "fast but wrong."** Times are seconds per call, median.

| Case (rows×K→N) | Direct fp32 (current) | Direct int32 | LUT g=4 (TL2-like) | On-the-fly quant + int32 | Quantize alone |
|---|---|---|---|---|---|
| champ qkv 8192×192→576 | **0.110** | 0.707 (err 1.1e-6) | 8.41 (err 1.1e-6) | 0.822 (err 1.1e-6) | 0.065 |
| champ up 8192×192→768 | **0.305** | 0.925 (err 9.5e-7) | 11.78 (err 9.5e-7) | 1.757 (err 9.5e-7) | 0.128 |
| champ down 8192×768→192 | **0.298** | 1.001 (err 1.3e-6) | 40.41 (err 1.3e-6) | 0.628 (err 1.3e-6) | 0.091 |
| lad2m qkv 8192×288→864 | **0.693** | 1.195 (err 8.3e-7) | 8.09 (err 8.3e-7) | 2.388 (err 8.3e-7) | 0.009 |
| lad2m up 8192×288→1152 | **0.483** | 1.308 (err 8.9e-7) | 48.52 (err 8.9e-7) | 2.501 (err 8.9e-7) | 0.192 |
| lad2m down 8192×1152→288 | **0.597** | 8.213 (err 1.4e-6) | 46.60 (err 1.4e-6) | 4.809 (err 1.4e-6) | 1.324 |
| champ head 2048×192→4096 | 1.562 | 3.621 (err 9.5e-7) | 34.10 (err 9.5e-7) | 0.898 (err 9.5e-7) | 0.206 |
| lad2m head 2048×288→4096 | **1.394** | 4.362 (err 8.2e-7) | 37.63 (err 8.2e-7) | 5.101 (err 8.2e-7) | 0.299 |

Findings:

- **The current direct fp32 `F.linear` wins every block case.** BLAS fp32 beats
  torch's integer matmul path by ~1.7–14× and the torch-emulated LUT by
  ~12–160×. One contended exception (champ head, on-the-fly int 0.898 vs fp32
  1.562) is not corroborated by its sibling case (lad2m head: int loses 3.7×)
  and is treated as noise, not a win.
- **LUT in torch is a dead end on this stack.** The 81-entry tables are exact,
  but gather-bound: 8–49 s per call, plus real memory (the table for one
  8,192×192 linear is 127 MB transient int32). Lookup-table matmul only pays
  in hand-written C (bitnet.cpp-style kernels), which a torch-level trial
  cannot express. Do not trial it here.
- **Integer matmul is exact but slower in torch** — no BLAS-class int8/int32
  GEMM is being hit on this CPU build. The on-the-fly variant (quantize raw
  activations inside the call, per-row absmax exactly as BitLinear does) costs
  the same as pre-quantized int within noise; quantization itself is a minor
  cost next to the matmul. If serving ever moves off torch, the integer path
  is the right design; inside torch it loses.
- Memory/state notes: fp32 path carries weights as fp32 (4 B/weight in the
  training graph); int32 path's persistent state is int8 codes + int8 ternary
  (1 B each) but its transient accumulator is int32 [rows×N]. LUT's transient
  tables dwarf both.

## 2. Vote-counter update step (Layered trainer, V=32)

Baseline = the update block of train.py's `Layered.step`, verbatim. The fused
variant computes the gradient sign once, replaces the flip test
`(t + sign).clamp(-1,1) != t` with the exactly-equivalent
`(sign != 0) & (t != sign)`, writes the flipped value as `t + sign`, and updates
the counters in place. **Resulting state is bitwise identical (max err 0.0) at
both sizes.** Times are per full step over all BitLinear layers; "net" subtracts
the state-cloning cost both arms pay identically in this harness (in the real
trainer there is no clone — counters are updated in place — so gross-vs-net
brackets the true gain).

| Case | Current gross | Fused gross | Current net | Fused net |
|---|---|---|---|---|
| Champion, 884,736 weights | 0.502 s | 0.294 s (1.7×) | 0.467 s | 0.259 s (1.8×) |
| Ladder 2M, 1,990,656 weights | 3.542 s | 0.771 s (4.6×) | 3.027 s | 0.256 s |

The 2M "current" arm caught a contention spike (its clone-only baseline jumped
15× vs the champion case), so the 4.6× gross ratio there is inflated; the
champion's ~1.7–1.8× is the trustworthy figure. No extra persistent state; the
in-place counter update is safe in train.py because the trainer owns the
counters outright.

## 3. Attention + rotary at lab scale

Baseline = train.py's path: `rotated()` (slice/stack/flatten) then
`F.scaled_dot_product_attention(is_causal=True)`. The complex variant computes
the **identical interleaved-pair rotation** as one complex multiply by a
precomputed unit rotor — **max abs error 0.0 (bitwise identical) in both runs,
both shapes.** Manual attention (explicit scores + mask + softmax) is exact to
~2e-7 (fp rounding) but 2–7× slower than SDPA; SDPA's forced math backend is
identical to the default here. QK-norm was not tested: the lab model has no
QK-norm, so it would change the math, not the kernel.

Combined rope+attention path, seconds per call (two separate contended runs):

| Case | Current (run 1) | Complex rope (run 1) | Current (run 2) | Complex rope (run 2) |
|---|---|---|---|---|
| Champion [32,4,256,48] | 0.596 | 0.206 (2.9×) | 0.567 | 0.332 (1.7×) |
| Ladder 2M [32,4,256,72] | 0.557 | 0.393 (1.4×) | 1.504 | 0.579 (2.6×) |

Single-op rope timings alone are contention-unstable (the reference
`rotated()` measured 0.078–0.27 s; the complex path 0.0002–0.007 s), but the
combined path — the number that matters — favors the complex rope in all four
measurements, by 1.4–2.9×.

## Recommendation — the ONE variant for a full mill trial

**Complex-multiplication RoPE as a drop-in replacement for `rotated()`.**

Why this one, under Arnav's criterion (best balance of speed and precision,
not raw speed alone):

1. **Precision is perfect, not approximate.** Bitwise identical output
   (err 0.0) at both lab shapes, in both runs. The trial's success check is
   therefore clean: held loss must match the current stack's numbers seed for
   seed, and any wall-clock gain is pure profit. No other fast variant offers
   exactness — the matmul integer/LUT paths are exact too, but they lose on
   speed, which is the whole point of a kernel.
2. **The speed gain is consistent where it counts.** 1.4–2.9× on the full
   rope+attention path across two runs and both shapes, and the benchmark
   only measures the forward pass — training also pays `rotated()`'s
   slice/stack cost again in the backward pass, so the training gain should
   be at least what is measured here.
3. **Blast radius per unit risk is the largest available.** One small function,
   used by q and k in every block of every rope arm — the champion, every
   ladder rung, and the mill's whole probe fleet all get faster at once,
   which compounds: faster probes = more ideas screened per sprint day.

Runner-up, recorded for the next slot: the fused vote update (§2) — also
bitwise exact, ~1.7–1.8× on a per-step cost every vote arm pays. It was not
picked first because its best measurement is muddier under contention and it
edits the trainer's mechanism loop rather than a self-contained math helper;
it deserves its own trial right after the RoPE one.

Explicitly not recommended: LUT matmul and integer matmul inside torch
(both exact, both slower than the current fp32 path at every lab shape), and
manual attention (slower than SDPA, no precision gain).
