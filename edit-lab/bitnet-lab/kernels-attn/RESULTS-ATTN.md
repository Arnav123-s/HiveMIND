# Muse's work — kernel strike team B (attention + output head), Muse's side.

**Scope:** the non-matmul hotspots of the lab trainer (`train.py`, read-only):
(1) SDPA attention variants on CPU, (2) LM head + embedding cost share at the
ladder shapes, (3) on-the-fly quantization overhead inside `BitLinear.forward`.
The matmul/LUT territory belongs to the separate kernel stream in `kernels/`;
nothing there or in `train.py` was touched. All runs: torch 2.15.0+cpu,
fp32, OMP/MKL = 2, venv python, batch 32, CTX 256.

**Method + honesty note.** The lab box (1.5 shared vCPU) was heavily loaded
the whole session — the ladder, the mill, and several sprint streams — and the
VM restarted twice mid-session, killing two early passes. Final numbers use
**round-robin interleaved timing with the minimum** (least-contended sample)
so contention hits every variant in a comparison roughly equally. Absolute
milliseconds are inflated vs an empty box; **ratios and shares within one
rotation are the reliable content.** Cross-checks against the ladder's own
records are used where a direct measurement was corrupted (flagged inline).

---

## Verdict in one paragraph

The remaining time does **not** sit in attention. The attention core is
~5–12% of a block's forward, no SDPA variant beats the current default
dispatch on CPU (the explicit MATH backend — timed here for the first time —
is consistently **2–3× slower** than default, and the EFFICIENT backend does
not exist on CPU at all). The two real non-matmul sinks are: **(a) the
output side — head matmul + cross-entropy over the 4096-piece vocabulary is
~32–34% of forward time** (cross-entropy alone rivals or beats the head
matmul, and the embedding lookup is free), and **(b) BitLinear's on-the-fly
quantization, which adds ~35–79% on top of each linear's matmul — almost all
of it the *activation* quantization**, worst on the wide `down` projection.
The weight quantization is nearly free — and in the vote arms it is provably
redundant (see §3).

---

## 1. Attention variants

Current implementation: `F.scaled_dot_product_attention(q, k, v, is_causal=True)`.
Forward, min of interleaved samples (bench_attn_verify.py, one rotation for
all variants). Errors are max abs error of the variant's output vs the
current implementation's output on identical inputs.

| shape | variant | fwd ms (min) | fwd ms (median) | max abs err |
|---|---|---:|---:|---:|
| champion dim 192, hd 48 | default (current) | 364.9 | 421.1 | 0 (itself) |
| | explicit MATH backend | 993.5 | 1973.6 | 1.3e-06 |
| | explicit mask | 292.9 | 523.2 | 0.0 |
| | manual masked softmax | 1713.7 | 2136.7 | 8.3e-07 |
| | RoPE rotate q+k | 333.8 | 475.9 | — |
| ladder 2M dim 288, hd 72 | default (current) | 56.8 | 63.9 | 0 (itself) |
| | explicit MATH backend | 182.2 | 240.2 | 1.7e-06 |
| | explicit mask | 59.5 | 75.8 | 0.0 |
| | manual masked softmax | 185.5 | 274.7 | 9.5e-07 |
| | RoPE rotate q+k | 30.9 | 43.5 | — |
| ladder 10M dim 512, hd 128 | default (current) | 137.0 | 161.8 | 0 (itself) |
| | explicit MATH backend | 302.4 | 480.7 | 2.0e-06 |
| | explicit mask | 97.7 | 198.8 | 0.0 |
| | manual masked softmax | 325.7 | 598.6 | 1.2e-06 |
| | RoPE rotate q+k | 107.9 | 150.9 | — |

Findings:

- **EFFICIENT backend: unavailable on CPU** — `sdpa_kernel(EFFICIENT_ATTENTION)`
  raises "No viable backend for scaled_dot_product_attention was found" at all
  three shapes. There is no fused CPU attention to switch to in this build.
- **Explicit MATH backend is 2.2–3.2× slower than default dispatch** at every
  shape, in the same rotation. Whatever the default CPU dispatch uses, it is
  not the reference math path, and it is faster. **Do not "fix" the trainer by
  pinning MATH.** (Correctness is fine either way: err ~2e-06.)
- **Explicit mask ≈ default** (min slightly better at 2 of 3 shapes, median
  slightly worse; bit-exact same output, err 0.0). No proven gain; it would
  also add a [256×256] mask buffer per call. Not recommended on this evidence.
- **Manual masked softmax is 2.4–4.7× slower** — the hand-rolled form is
  strictly worse, as expected.
- Noncausal SDPA (timed once, first pass) ran at ~the same speed as causal —
  on this CPU path the causal mask does not skip the masked-out FLOPs, so
  there is no causal-discount to recover. (Its "error" vs the causal output
  is ~4.0 by construction — different function, not a correctness signal.)
- **RoPE rotation costs 0.5–0.9× the attention call itself** (rotate q and k:
  stack/flatten elementwise over [32, heads, 256, hd]). Real, but both are
  small next to the block linears — together ≈12% of a 10M block's forward.
- **Forward+backward attention timings were noise-dominated**: two full
  passes disagreed on the default-vs-mask ordering at the 288/512 shapes
  (explicit mask fastest at all shapes in one pass, at 1 of 3 in the other;
  MATH's backward was 2–9× default's in both passes, consistent with its
  forward penalty). No fwd+bwd winner is claimed; the training-step split in
  §2 is the reliable guide, and attention is a small part of it either way.

**Bottom line for §1: keep the attention call exactly as it is.**

## 2. LM head + embedding cost share

`next_piece(ids) = body(ids) @ tok.weight.T` (tied embedding as head), then
cross-entropy over [8192, 4096] logits. Forward split, min of interleaved
samples (bench_head.py); rope on, as the ladder runs.

| ladder 2M (dim 288, 2 blocks) | ms | ladder 10M (dim 512, 3 blocks) | ms |
|---|---:|---|---:|
| embedding lookup | 0.78 | embedding lookup | 0.83 |
| body (embed+blocks+norm) | 4072 | body | 6065 |
| head matmul | 456 | head matmul | 1523 |
| cross-entropy | 1162 | cross-entropy | 1706 |
| next_piece (body+head) | 3589 | next_piece | 8475 |

- **Output side (head matmul + CE) = 34.1% (2M) / 31.7% (10M) of forward
  time.** At 2M the CE is 2.5× the head matmul — CE cost is set by the
  [8192 × 4096] logits and barely moves with dim, while the head matmul
  scales with dim; they are comparable at 10M (1706 vs 1523 ms).
- **Embedding lookup is nothing** (0.8 ms, <0.1%) at both shapes. The `pos`
  table the rope arms carry-but-don't-use costs no measurable time.
- Forward+backward: at 2M, head+CE fwd+bwd = 4002 ms vs full step 17,629 ms
  in the same rotation → **output side ≈ 23% of the training step**. At 10M
  the direct pair measurement was contention-corrupted (full-step min 58 s
  vs the ladder's own recorded 12.9 s/step for 10M seed 0 — the bench never
  got a clean window; rounds in logs/head_fb10m.log). Bracketing from the
  clean forward share (31.7%) and the 2M fwd+bwd share (23%): **the 10M
  output-side share of a training step is ~25–32%.** Either way it is the
  largest single non-block item in the step, and roughly half of it is the
  cross-entropy over full-vocab logits, not the matmul.

## 3. On-the-fly quantization overhead in BitLinear.forward

Every forward call re-quantizes the full weight matrix and per-token
quantizes the activations before `F.linear`. Min ms, interleaved
(bench_quant.py). "quant share" = (full − matmul-on-quantized) / full.
Correctness: BitLinear output vs manually composed quantize-then-linear =
**max abs err 0.0** at every shape (bit-exact decomposition).

**dim 288 (ladder 2M)**

| layer | full | weight-quant | act-quant | matmul(q) | raw fp linear | quant share |
|---|---:|---:|---:|---:|---:|---:|
| qkv | 675.6 | 0.29 | 77.5 | 379.8 | 338.1 | 43.8% |
| out | 321.4 | 1.6 | 75.1 | 123.0 | 122.3 | 61.7% |
| up | 745.4 | 19.1 | 35.8 | 438.7 | 376.1 | 41.1% |
| down | 1813.4 | 21.6 | 621.6 | 381.1 | 394.3 | 79.0% |

**dim 512 (ladder 10M)**

| layer | full | weight-quant | act-quant | matmul(q) | raw fp linear | quant share |
|---|---:|---:|---:|---:|---:|---:|
| qkv | 2160.3 | 56.0 | 192.7 | 1402.4 | 1538.0 | 35.1% |
| out | 718.2 | 2.0 | 100.2 | 377.6 | 561.1 | 47.4% |
| up | 1213.7 | 1.1 | 19.3 | 607.8 | 783.3 | 49.9% |
| down | 1234.3 | 1.5 | 1002.1 | 819.5 | 798.9 | 33.6% |

Findings:

- **Quantization adds ~35–79% (dim 288) / ~34–50% (dim 512) on top of each
  linear's forward.** Summed over a block's four linears at dim 512, the
  quant ops cost ≈2.1 s against ≈3.2 s of matmul in the same (contended)
  window — i.e. on the order of **40% of block-linear forward time is
  quantization overhead, not matmul.**
- **It is the activation quant, not the weight quant.** Per block at dim 512:
  act-quant sums to ≈1.31 s vs weight-quant ≈0.06 s. The activation tensors
  are [32×256, in] — far larger than the weight matrices — and the chain
  (amax → div → round → clamp → mul → sub → add) makes several full passes
  over them. The `down` projection is the worst single item both dims
  (its input is 4·dim wide: act-quant 622 ms @288, 1002 ms @512).
- **The weight quant is redundant in the vote arms.** `Direct.install()` /
  `Layered.install()` already write the exactly-quantized weight
  (ternary × scale) into `m.weight` after every step, so in the forward,
  `(w/scale).round().clamp(-1,1)*scale` reproduces `w` — skipping the weight
  branch when the trainer pre-quantizes would be bit-exact for the plain /
  layered / anneal / mag arms and saves the (small) wquant cost plus its
  backward graph. It is NOT skippable for the STE arm, whose latent weights
  are genuinely unquantized. Small win, free correctness.
- The activation quant cannot be skipped, but it is the fattest target in
  this whole report: fusing the amax+scale+round chain (fewer passes over
  [8192, 4·dim]) attacks ~1.0 s per `down` call at dim 512 before any matmul
  work. That is a bigger lever than anything in §1.

## Where the remaining time actually sits (per training step, ladder shapes)

1. **Block linear matmuls** — the other kernel stream's territory; the
   largest single block, as expected.
2. **Activation quantization inside those same linears** — ~40% on top of
   block-linear forward time; the biggest *non-matmul* sink found.
3. **Output side: head matmul + full-vocab cross-entropy** — ~23–34% of
   the step; about half of it is CE, which no matmul kernel will fix.
4. **Attention core + RoPE** — together ≈12% of a block's forward; the
   current SDPA call is already on the fastest CPU path available here.
5. **Embedding lookup** — negligible.

Scripts: `bench_attn.py`, `bench_attn_verify.py`, `bench_head.py`,
`bench_head_fb.py`, `bench_quant.py`; raw logs in `logs/`.
