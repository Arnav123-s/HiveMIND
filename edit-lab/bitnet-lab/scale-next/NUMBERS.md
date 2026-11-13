# Scale-next numbers — sizing & budgets for the overlap program

> **Muse's work — written by Muse, on Muse's side of the BitNet lab.**
> Fable's side was not touched. `runs.jsonl`, `run_scale_ladder.py`, and `train.py`
> were read only, never modified.
> Date: 2026-11-12. All ladder facts below were re-verified against `runs.jsonl`
> and `run_scale_ladder.py` at writing time. Best recipe throughout:
> **layered + rotary + plain votes** (`layered_rope` arms).

---

## 0. Verified ladder facts (source: `runs.jsonl`, `run_scale_ladder.py`, `train.py`)

Param arithmetic from `train.py`'s model definition (`Tiny` / `Block` / `BitLinear`,
VOCAB = 4096, CTX = 256, HEADS = 4 fixed):

- Ternary weights live only in the `BitLinear` matrices. Per block:
  qkv `dim×3dim` + out `dim×dim` + up `dim×4dim` + down `4dim×dim` = **12·dim²**.
  For L blocks: **ternary = 12 · L · dim²**.
- Non-ternary (FP) params: token embedding `4096·dim` + position embedding `256·dim`
  (carried even with `--rope`, per `train.py`) + final LayerNorm `2·dim`
  + per block `13·dim` (two LayerNorms = `4·dim`; four BitLinear biases
  `3dim + dim + 4dim + dim` = `9·dim`).
  **FP params = 4354·dim + 13·L·dim**. Total params = ternary + FP. ✔ reproduces
  every `total_params` value in `runs.jsonl` exactly.

| Rung | Shape (dim × L) | Ternary weights | FP params | Total params | Measured wall, 56 steps | s/step |
|---|---|---:|---:|---:|---:|---:|
| 2M | 288 × 2 | 1,990,656 | 1,261,440 | 3,252,096 | 287.7 / 281.0 / 281.1 s (mean 283.3 s) | 5.06 |
| 10M | 512 × 3 | 9,437,184 | 2,249,216 | 11,686,400 | 722.9 s (seed 0 only so far) | 12.91 |
| 50M | 768 × 7 | 49,545,216 | 3,413,760 | 52,958,976 | **no completed 56-step run yet** — driver estimate 5,100 s (91.1 s/step), `--ckpt` required (OOM at 5.7 GB without it, per driver comment) | ~91 (est.) |

- Tokens: batch 32 × seq 256 = **8,192 tokens/step**; ladder runs = 56 steps =
  **458,752 tokens**, identical for every rung.
- Corpus = **5,917,236 tokens** (`corpus_pieces` in every record).
- Held loss at 56 steps (layered+rope): 2M mean of 3 seeds = **3.2745**
  (3.2878 / 3.2649 / 3.2709); 10M seed 0 = **2.9472**. 50M has no 56-step loss —
  only a 2-step smoke check (held 6.5932), which is not comparable and is
  excluded from the loss-per-byte picture below.

---

## 1. Serving-bytes accounting

**Stated convention (serving bytes):** ternary weights packed at **0.25 B/weight**
(2 bits, 4 per byte) + non-ternary FP params at **4 B/param** (FP32, as stored).

Serving bytes S(dim, L) = 0.25 · (12·L·dim²) + 4 · (4354·dim + 13·L·dim)
= **3·L·dim² + 17,416·dim + 52·L·dim**.

| Rung | Ternary bytes (0.25 B/w) | FP bytes (4 B/p) | — of which token embedding | — position emb. | — norms + biases | **Total serving bytes** | FP share | Ternary share |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2M (288×2) | 497,664 | 5,045,760 | 4,718,592 | 294,912 | 32,256 | **5,543,424 B = 5.543 MB (5.287 MiB)** | 91.0% | 9.0% |
| 10M (512×3) | 2,359,296 | 8,996,864 | 8,388,608 | 524,288 | 83,968 | **11,356,160 B = 11.356 MB (10.830 MiB)** | 79.2% | 20.8% |
| 50M (768×7) | 12,386,304 | 13,655,040 | 12,582,912 | 786,432 | 285,696 | **26,041,344 B = 26.041 MB (24.834 MiB)** | 52.4% | 47.6% |

**The headline:** at the small rungs, serving bytes are mostly *embedding*, not
ternary weights. The token embedding alone is 85.1% of the 2M rung's serving
bytes and 73.9% of the 10M rung's. Only at 50M do ternary weights approach half
the footprint. Any "per byte" claim that ignores the FP side is measuring the
embedding table, not the ternary body.

*Caveat on the 0.25 B/weight convention:* the layered recipe's effective weight
is t1+t2, a 5-level value (−2…+2), which strictly needs 3 bits packed
(0.375 B/w), or 0.5 B/w if the two components are packed separately. Under
0.375 B/w the totals become 5,792,256 / 12,535,808 / 32,234,496 B; under
0.5 B/w, 6,041,088 / 13,715,456 / 38,427,648 B. The primary tables follow the
stated 0.25 B/w convention; the ranking of rungs does not change under either
sensitivity.

### Loss-per-byte under both conventions

The lab's `mech_state_bytes` for the layered arm = 2 counters (int8, 2 B) +
2 ternary states at 2 bits each (0.5 B) = **2.5 B per ternary weight**, and it
counts *only* the ternary mechanism — no FP params, no AdamW state for them.
It is a training-mechanism state size, not a serving size. Both pictures,
at equal tokens (458,752) and equal steps (56):

| Rung | Held loss (mean) | Perplexity e^loss | Serving MB | Loss / serving-MB | Mech MB (2.5 B/w) | Loss / mech-MB |
|---|---:|---:|---:|---:|---:|---:|
| 2M | 3.2745 | 26.4 | 5.543 | 0.591 | 4.977 | 0.658 |
| 10M | 2.9472 | 19.1 | 11.356 | 0.260 | 23.593 | 0.125 |
| 50M | — (no run yet) | — | 26.041 | — | 123.863 | — |

Marginal cost of the 2M → 10M loss gain (−0.3273, −10.0%):

- Serving convention: bytes grow ×2.05 (+5.813 MB) → **1.78 MB per 0.1 loss**.
- Mech convention: bytes grow ×4.74 (+18.616 MB) → **5.69 MB per 0.1 loss**.

Same runs, same loss gain — the mech convention makes scale look ~3.2× more
expensive per unit of loss, because it counts only the part that grew fastest
(the ternary body, ×4.74) and none of the part that grew slowest (embeddings,
×1.78). Quote loss-per-byte with its convention attached, always.

---

## 2. Equal-bytes system math (overlap program)

### System budget: 4 members at the 10M shape

Per member (512 × 3): 11,356,160 serving bytes (above).
**System total = 4 × 11,356,160 = 45,424,640 B = 45.425 MB (43.32 MiB).**
Of that, 4 × 8,996,864 = 35,987,456 B (79.2%) is FP — i.e. the four-member
system pays the full FP stack, token embedding included, **four times**.
Its ternary payload is 4 × 2,359,296 = 9,437,184 B, carrying 37,748,736
ternary weights.

### Single generalist at equal bytes

Search over dim (multiples of 8, so HEADS = 4 divides dim and rotary pairs are
integral) × L, using S(dim, L) above, target 45,424,640 B (±5% = 43.15–47.70 MB):

| Candidate (dim × L) | Ternary weights | Total params | Serving bytes | Error |
|---|---:|---:|---:|---:|
| 768 × 18 | 127,401,984 | 130,908,672 | 45,944,832 | +1.15% |
| **896 × 12** | **115,605,504** | **119,646,464** | **45,065,216** | **−0.79%** |
| 960 × 10 | 110,592,000 | 114,872,320 | 44,866,560 | −1.23% |
| 1024 × 9 | 113,246,208 | 117,702,656 | 46,624,768 | +2.64% |
| 1024 × 8 | 100,663,296 | 105,119,744 | 43,425,792 | −4.40% |

**Picked generalist: dim 896 × 12 layers** — 45,065,216 B, −0.79% vs the
four-member system. (Near-exact matches <0.1% exist only at extreme shapes,
e.g. 552 × 38; not practical.) Arithmetic for the pick:
ternary = 12 · 12 · 896² = 115,605,504 → ×0.25 = 28,901,376 B;
FP = 4354·896 + 13·12·896 = 3,901,184 + 139,776 = 4,040,960 → ×4 = 16,163,840 B;
total 28,901,376 + 16,163,840 = 45,065,216 B. ✔

Note what equal bytes buys: the generalist carries **115.6M ternary weights vs
the system's 37.7M (3.06×)**, because it pays the embedding once instead of
four times. Equal bytes is *not* equal compute — see §3.

For the 2M-scale smoke (§3a), the same search against 4 × 5,543,424 =
22,173,696 B gives **dim 688 × 7**: ternary = 12 · 7 · 688² = 39,760,896
(→ 9,940,224 B); FP = 4354·688 + 13·7·688 = 2,995,952 + 62,608 = 3,058,560
(→ 12,234,240 B); total **22,172,864 B, −0.00%**. (Runner-up: 576 × 12 at +0.73%.)

### Narrow specialists at equal bytes

The narrow arm is a *data* restriction, not a shape restriction: **4 members,
each trained on one bucket only, each at the member shape 512 × 3** —
11,356,160 B each, **45,424,640 B total, an exact (0.00%) match** to the
tilted-member system. Per-bucket training changes nothing in the param
arithmetic: every specialist still carries the full 4096-token embedding
(8,388,608 B, 73.9% of its serving bytes) even though it only ever trains on
its bucket. Specialization, as shaped here, buys no byte savings.

*Variant worth knowing (not the primary config):* if the four specialists
shared one FP stack and differed only in ternary bodies, the same bodies
would cost 8,996,864 + 4 × 2,359,296 = 18,434,048 B — 40.6% of the system
budget. Spending the full budget in that layout (dim 512 bodies grown to
11 layers each) gives 8,996,864 + 4 × 8,650,752 = 43,599,872 B (−4.02%).
`train.py` as written cannot do this (embedding is per-model, and the LM head
is tied to it) — it would need a code change, so it is costed here only as a
design note.

---

## 3. Wall-clock budgets (this VM, 1.5 vCPU, one heavy job at a time)

**Step-time basis.** Measured pure-training step times (wall ÷ steps, layered+rope):
2M shape 5.06 s/step; 10M shape 12.91 s/step. For unmeasured shapes I use a
linear fit on per-token matmul work (≈ ternary weights + 4096·dim for the tied
LM head), anchored on those two points: s/step ≈ 2.08 + 9.39×10⁻⁷ · MACs/token.
Cross-checks: it predicts the 0.9M half chassis at ~3.7 s/step (measured ~3.0)
and the 50M rung at ~52 s/step *before* checkpointing, vs the driver's 91 s/step
estimate *with* `--ckpt` and overhead — so for checkpointed shapes I quote a
range: fit → fit ×1.3 (ckpt allowance) → driver-anchored (91.07 s/step scaled
by MACs from the 50M point). Treat extrapolated step times as ±30%.
Totals below are training wall only; add ~0.5–1 min per run for startup +
held evals (≈ +10 min on (a), +30 min on (b)).

**Protocol assumption (stated, re-cut freely):** every arm runs 56 steps of
round 1 + 14 steps of exchange round = **70 steps per run**, including the
generalist (56 + 14 continued). If untilted controls skip the exchange round,
subtract 0.16 h from (a) and 1.20 h from (b).

### (a) Overlap smoke — 2M shape, 1 seed

Arms: 4 tilted + 4 untilted controls + 4 narrow, all at 288 × 2 (member shape),
+ 1 generalist at 688 × 7 (39.76M ternary — 50M-rung scale, `--ckpt` required).

| Part | Runs × steps × s/step | Time |
|---|---:|---:|
| Member-shaped arms | 12 × 70 × 5.06 s | 4,250 s = **1.18 h** |
| Generalist (688×7) | 1 × 70 × 42–74 s (fit 42.0; ×1.3 ckpt 54.7; driver-anchored 73.6) | **0.82–1.43 h** |
| **Total (a)** | 13 runs | **≈ 2.0–2.6 h** |

Flags: the single generalist run (0.8–1.4 h) is the long pole and sits near,
not over, the ~2 h single-run guideline. It needs `--ckpt` and a `--minutes`
cap above the ladder's 12-min 2M setting. No member-shaped run is a risk
(~5.9 min each).

### (b) Overlap full — 10M shape, 3 seeds

Arms per seed: 4 tilted + 4 untilted + 4 narrow at 512 × 3, + 1 generalist at
896 × 12 (115.6M ternary). Totals: 36 member runs + 3 generalist runs.

| Part | Runs × steps × s/step | Time |
|---|---:|---:|
| Member-shaped arms | 36 × 70 × 12.91 s | 32,530 s = **9.04 h** |
| Generalist (896×12), per seed | 1 × 70 × 114–206 s (fit 114.0; ×1.3 ckpt 148.2; driver-anchored 206.2) | **2.22–4.01 h per seed** |
| Generalists × 3 seeds | | **6.65–12.02 h** |
| **Total (b)** | 39 runs | **≈ 15.7–21.1 h** |

Flags — read before scheduling:
- **Every generalist run singly exceeds the ~2 h guideline (2.2–4.0 h each).**
  It cannot be run as one job under the lab's current habits; it needs
  chunked/resumable runs or a reduced-step generalist protocol. This is the
  equal-bytes tax: the byte-matched generalist has ~10.3× the member's
  per-token matmul work (119.3M vs 11.5M MACs/token).
- **OOM risk: real but manageable.** The generalist's ternary count (115.6M)
  is 2.33× the 50M rung, which already OOM'd at 5.7 GB *without* `--ckpt`.
  `--ckpt` is mandatory. Estimated trainer state with ckpt: FP32 model
  ~479 MB + t1/t2 ~925 MB + counters ~231 MB + weight grads ~462 MB ≈ 2.1 GB
  plus checkpointed activations — plausibly inside the ~6 GB cap, but
  **unproven: smoke-test the shape (2-step run, like the 50M smokecheck)
  before committing any seed.**
- `--minutes` caps must be raised per run (ladder used 25 min at 10M, 115 min
  at 50M); multi-hour runs also collide with the drivers' growth-cycle window
  guard (~06:50 UTC) — schedule around it.
- Member-shaped runs are individually safe (~15.1 min each).

### (c) Confirmation runs — longer training at fixed rungs

Per-run times scale linearly from the measured s/step (280 steps = 5× the
ladder run; 448 steps = 8×). Tokens: 280 steps = 2,293,760; 448 steps =
3,670,016 (see §4).

| Rung | 280 steps, per seed | 280 steps, 3 seeds | 448 steps, per seed | 448 steps, 3 seeds |
|---|---:|---:|---:|---:|
| 2M (5.06 s/step) | 23.6 min (0.39 h) | 1.18 h | 37.8 min (0.63 h) | 1.89 h |
| 10M (12.91 s/step) | 60.2 min (1.00 h) | 3.01 h | 96.4 min (1.61 h) | 4.82 h |
| 50M (~91.1 s/step, driver est., `--ckpt`) | **425 min (7.08 h)** | **21.25 h** | **680 min (11.33 h)** | **34.00 h** |

- **(c) headline total — 10M + runner-up rung (2M), both step budgets,
  3 seeds each: 1.18 + 3.01 + 1.89 + 4.82 = 10.90 h.**
  (10M alone, both budgets, 3 seeds: 7.83 h. 2M alone: 3.07 h.)
- Flags: the 10M 448-step run at 1.61 h is under but close to the ~2 h
  single-run guideline — with startup/evals it lands ~1.7 h; give it a
  `--minutes` cap of ~120, not the ladder's 25. All 2M/10M singles are fine.
- **If "runner-up rung" means 50M, do not run it as single jobs:** 7.1 h
  (280 steps) and 11.3 h (448 steps) per seed at the driver's own estimate,
  on a rung that has not yet completed even a 56-step run and OOMs without
  `--ckpt`. A 50M confirmation needs chunked training with state save/resume
  (which `train.py` does not currently support) or a smaller step budget.
  Even at the optimistic fit step time (~52 s/step pre-ckpt) these are
  4.0 h / 6.5 h singles.

---

## 4. Corpus-epoch table

Corpus = 5,917,236 tokens. Sampling in `train.py` draws random windows
(held windows excluded), so these are tokens-seen ÷ corpus size, not clean
passes — above 100%, repeats are expected.

| Tokens seen | = steps × 8,192 | Fraction of corpus |
|---:|---:|---:|
| 458,752 (ladder run) | 56 steps | **7.75%** |
| 573,440 (one overlap member, 56 + 14) | 70 steps | 9.69% |
| 2,293,760 (confirmation, short) | 280 steps | **38.76%** |
| 3,670,016 (confirmation, long) | 448 steps | **62.02%** |
| 5,917,236 (full corpus) | ~722 steps | **100.00%** |
| 7,340,032 | 896 steps | **124.04%** |

---

## Headline numbers (for the report back)

- **Serving bytes per rung** (0.25 B/ternary + 4 B/FP): 2M = **5,543,424 B**
  (91.0% FP), 10M = **11,356,160 B** (79.2% FP), 50M = **26,041,344 B**
  (52.4% FP). Mech convention (2.5 B/ternary, ternary only): 4,976,640 /
  23,592,960 / 123,863,040 B.
- **Equal-bytes system:** 4 × 10M members = **45,424,640 B**. Matched single
  generalist: **dim 896 × 12 layers** (45,065,216 B, −0.79%; 115.6M ternary
  weights). Narrow specialists: 4 × 512 × 3 per-bucket, exact match.
  Smoke-scale generalist: dim 688 × 7 (−0.00% of 22,173,696 B).
- **Budgets:** (a) smoke ≈ **2.0–2.6 h**; (b) full ≈ **15.7–21.1 h**
  (generalist-dominated; each generalist run alone is 2.2–4.0 h — over the
  single-run guideline, `--ckpt` + smoke test required); (c) confirmations
  for 10M + 2M at both step budgets, 3 seeds = **10.90 h** (50M variant
  excluded — 7–11 h per single run, not runnable as-is).
