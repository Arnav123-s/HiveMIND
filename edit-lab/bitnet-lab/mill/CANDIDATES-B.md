# CANDIDATES-B — Idea-mining stream B (literature)

> **Muse's work, Muse's side.** Written by Muse for the BitNet mill on Muse's side.
> This file complements `IDEA-POOL.md` (owned by another agent — not edited here) and
> `FABLE-CANDIDATES.md`. Every entry below was checked against the pool and the lab's two
> research docs (`BITNET-DIRECT-TRAINER-STUDY-2026-11-11.md`, the 2026-11-12 architecture
> report) so nothing already queued is re-mined. Sources are primary only (papers, official
> repos), per Arnav's sourcing rule. Entries flagged ⚠ need a verification pass before anyone
> builds on them.

**Lab context used in the "how tried" lines:** `train.py` — Tiny transformer (default 4 layers,
rotary flag); trainers `Direct` (vote counter, votes=32, strong-gate median), `Layered`
(layered votes), `STE` (lr 3e-3, warm=200); shared non-ternary parts trained by AdamW;
held_loss on 128 held windows; corpus ~5.92M pieces (`corpus.u16`, built by `make_corpus.py`
from harvested hive text). Mill probe = 60–90 s / 1 seed; full trial = 3 seeds × 8 min;
win bar >2 sd and >0.01. Where an idea changes tokenization, judge in **nats/byte**, not
nats/token.

---

## Family 1 — Data and tokenizer (the pool's widest-open territory: zero entries today)

### B-001 — Staged data-mixture ablation for a ternary model
- **Source:** SmolLM2 — Allal et al., arXiv:2502.02737, 2025-02-04.
- **Mechanism:** Train in stages with different data mixtures per stage (SmolLM2 ran 4 stages,
  shifting web/code/math ratios, reserving the best math+code for the final decay stage).
- **How tried:** Split the harvested corpus into its natural source classes, run the champion
  chassis (layered + rotary + plain votes) on 2–3 stage schedules (e.g. uniform → HQ-heavy
  final third) at equal total tokens vs the single-mixture control.
- **Fit:** Data-level. The 2026-11-12 architecture report explicitly flags that **no
  ternary-specific data-mixture ablation exists in primary sources** — this is a genuine
  literature gap, not a re-test.

### B-002 — Tokenizer trained on the exact training mixture
- **Source:** SmolLM2, arXiv:2502.02737, 2025-02-04 (their tokenizer was trained on the final
  mixture, ~70/15/8/5/2 across sources).
- **Mechanism:** A tokenizer fitted to the actual data mix allocates merges where the training
  data actually lives, instead of a generic corpus's statistics.
- **How tried:** Retrain the lab's word-piece vocab on the harvested corpus itself (same vocab
  size), rebuild `corpus.u16`, rerun champion; compare in nats/byte.
- **Fit:** Data-level (tokenizer). Cheap, one-time; the current corpus's tokenizer provenance
  is inherited, not fitted.

### B-003 — SuperBPE: superword merges past whitespace
- **Source:** SuperBPE — Liu, Hayase, Hofmann, Oh, Smith, Choi, arXiv:2503.13423, 2025-03-17,
  COLM 2025.
- **Mechanism:** Two-stage tokenizer curriculum — learn normal subwords, then drop whitespace
  pretokenization and learn cross-word "superwords" (up to 33% fewer tokens at fixed 200k
  vocab; +4.0% avg over 30 tasks at 8B, −27% inference compute).
- **How tried:** Add a superword merge stage at lab vocab size, rebuild the corpus, rerun
  champion at equal *bytes* (not equal tokens); judge in nats/byte.
- **Fit:** Data-level (tokenizer). Directly attacks the lab's fixed piece budget: fewer pieces
  per byte means each 458k-token run sees more actual text.

### B-004 — Byte Latent Transformer (mini-BLT): entropy patches, no vocab
- **Source:** BLT — Pagnoni et al., arXiv:2412.09871, 2024-12-16, ACL 2025.
- **Mechanism:** Bytes are grouped into variable-length patches by the entropy of a small
  auxiliary byte LM; a light local encoder/decoder wraps a latent transformer — no fixed
  vocabulary, and no large FP embedding table.
- **How tried:** Smallest viable version: byte input, fixed small patcher (entropy threshold
  from a tiny byte model), latent Tiny as-is. Compare nats/byte and total bytes vs champion.
- **Fit:** Architecture-level. **Honest note: this is a build, not a flag — the highest-effort
  entry in this file.** The payoff case is real: at lab scale the FP embedding table is a
  large share of model bytes, and BLT deletes it.

### B-005 — Model-based quality filtering of the harvested corpus (DCLM-style)
- **Source:** DCLM — Li et al., arXiv:2406.11794, 2024-06-18, NeurIPS 2024 Datasets & Benchmarks.
- **Mechanism:** A fastText-style classifier scores documents for instruction-like quality;
  in DCLM's controlled pools, filtering was *the* lever (7B reached 64% MMLU on 2.6T tokens,
  +6.6 pts at 40% less compute).
- **How tried:** Train a small n-gram classifier to separate the corpus's cleanest slice from
  the rest, keep the top fraction, rerun champion at equal tokens; sweep keep-fraction as a
  paired variable (see B-008).
- **Fit:** Data-level. Untested territory in the pool; the lab corpus is small and harvested,
  so its quality distribution is exactly what filtering acts on.

### B-006 — Educational-value filtering (FineWeb-Edu-style)
- **Source:** FineWeb / FineWeb-Edu — Penedo et al., arXiv:2406.17557, 2024, NeurIPS 2024
  Datasets & Benchmarks.
- **Mechanism:** A classifier distilled from LLM annotations scores text 0–5 for educational
  value; keeping ≥3 produced a 1.3T-token subset that beat the 15T raw pool at small budgets.
- **How tried:** Score the harvested corpus with a small local scorer, keep the top slice,
  rerun champion at equal tokens; compare against B-005's filter (different scoring target:
  educational value vs instruction-likeness).
- **Fit:** Data-level. Two different filters on the same corpus is a clean A/B the pool has
  no equivalent of.

### B-007 — Near-duplicate removal pass in corpus building
- **Source:** FineWeb pipeline, arXiv:2406.17557, 2024 (notably: per-snapshot MinHash dedup —
  their *global* dedup measured worse, so scope of dedup is itself a variable).
- **Mechanism:** Near-duplicate documents waste a small corpus's budget and inflate memorized
  spans; MinHash-style dedup removes them.
- **How tried:** Add a MinHash near-dedup stage to `make_corpus.py`, rebuild, rerun champion
  at equal tokens. First measure the corpus's current duplicate rate — it is unmeasured today,
  so the first deliverable is the number itself.
- **Fit:** Data-level. Cheapest entry in this family; also a hygiene fix independent of the
  loss result.

### B-008 — Filter-strength sweep: when filtering stops helping (the caution arm)
- **Source:** Mohri et al., "A Bitter Lesson for Data Filtering," arXiv:2605.19407, 2026; and
  Goyal et al., "Scaling Laws for Data Filtering," arXiv:2404.07177, 2024.
- **Mechanism:** In the data-scarce / high-compute regime, aggressive quality filtering can
  *hurt* — quality pools decay faster under repetition, and the optimal filter tends toward
  no filter as compute-per-data rises.
- **How tried:** Run B-005/B-006 at keep-fractions 100% / 50% / 25% with matched total tokens
  (so smaller pools repeat more). The lab — ~5.92M pieces, many epochs — sits exactly in the
  regime where the caution bites.
- **Fit:** Data-level. This is the control that keeps the filtering entries honest; without
  it, a filter "win" at one keep-fraction proves little.

### B-009 — Epoch / repetition scaling on a fixed small corpus
- **Source:** Muennighoff et al., "Scaling Data-Constrained Language Models,"
  arXiv:2305.16264, NeurIPS 2023; JMLR 26, 2025-02. ⚠ *2023 origin — included because the
  lab's regime makes it first-order and the pool has zero epoch entries.*
- **Mechanism:** Up to ~4 epochs of repeated data is nearly as good as fresh data; beyond
  that returns decay with a measurable effective-data law (R*_D ≈ 15, ~16-epoch half-life),
  and data-constrained runs should scale epochs slightly faster than parameters.
- **How tried:** Champion chassis at 1 / 2 / 4 / 8 epochs over the fixed corpus at equal total
  tokens (adjusting steps), plus one arm pairing epoch count with the ~2M ladder rung to test
  their "epochs slightly faster than params" prescription at ternary scale.
- **Fit:** Data-level / schedule-level. Directly informs the scale ladder, whose big rungs are
  token-starved by construction.

### B-010 — Rewrite the discards instead of dropping them (REWIRE)
- **Source:** REWIRE — Nguyen, Li, Golovneva et al., arXiv:2506.04689, COLM 2025.
- **Mechanism:** Documents a quality filter would discard are *rewritten* into clean text by a
  guide model and mixed back with high-quality raw data (+1.0/+1.3/+2.5 pts at 1B/3B/7B on
  DCLM tasks) — recycling beats discarding when data is scarce.
- **How tried:** Take the slice B-005's filter rejects, produce a small rewritten version of
  it, mix rewrites + kept raw at equal tokens vs both the filtered-only and unfiltered arms.
- **Fit:** Data-level. The opposite arm to filtering — the pair brackets the design space.
  Honest caveat: needs a generator; the lab's own FP models are tiny, so a small
  externally generated rewrite set is the practical route.

### B-011 — Small synthetic-textbook slice in the mix (Cosmopedia-style)
- **Source:** Cosmopedia v2 (28B tokens of generated textbook/story/code across ~34k topics),
  as used at 4% of SmolLM2's decay stage, arXiv:2502.02737, 2025; phi "textbooks" lineage.
- **Mechanism:** Generated, textbook-style text concentrates clean explanatory signal that
  raw harvested text dilutes.
- **How tried:** Generate or source a small textbook-style set sized to ~5–10% of the corpus,
  mix in for the final training phase (pairs naturally with B-001's staged schedule), equal
  tokens vs control.
- **Fit:** Data-level. Distinct from B-010: generation from seed topics vs rewriting real
  documents. Keep the fraction small — synthetic-heavy mixes are their own failure mode.

### B-012 — Automatic mixture weights from a tiny proxy (DoReMi)
- **Source:** DoReMi — Xie et al., arXiv:2305.10429, NeurIPS 2023. ⚠ *2023 — included as the
  automatic counterpart to B-001's manual stages.*
- **Mechanism:** A small proxy model trained with group-DRO learns per-domain mixture weights
  that transfer to models ~30× larger (2.6× fewer steps, +6.5 pts in the original).
- **How tried:** The lab's own Tiny *is* proxy-scale: run group-DRO over the harvested
  corpus's source domains with a small Tiny, take the learned weights, rerun champion with
  them vs the uniform mix.
- **Fit:** Data-level. If B-001 shows mixture matters at all for ternary, this is the cheap
  way to search the mixture space instead of hand-picking stages.

---

## Family 2 — Optimizers (for STE and the shared FP parts; two arms reach the vote-trainer)

### B-013 — Cautious AdamW on gradient-trained parts
- **Source:** Cautious Optimizers — Liang, Chen, Liu, Liu, arXiv:2411.16085, 2024-11-25
  (v4 2026-02-15), ICLR 2026.
- **Mechanism:** One-line mask on any Adam-family update: zero every coordinate where the
  update disagrees in sign with the current gradient, rescale by 1/mean(mask). Reported
  1.47× speedup for C-AdamW on LLaMA-1B with convergence guarantees preserved.
- **How tried:** Flag on the STE trainer's optimizer and on the AdamW that trains shared
  parts in the vote arms. Near-zero implementation cost (a mask in the step function).
- **Fit:** Needs gradient training (STE latents + shared parts). No interaction with the vote
  counter itself.

### B-014 — Cautious masking translated to votes
- **Source:** Same paper as B-013 (arXiv:2411.16085), mechanism translated to the vote domain.
- **Mechanism:** Count a weight's incoming votes only while they agree with the counter's
  accumulated direction; dissenting votes are masked rather than subtracted.
- **How tried:** Variant of `Direct`/`Layered` where the counter accumulates agreeing evidence
  only, flip rule unchanged. Probe against plain votes on the champion chassis.
- **Fit:** Fits the vote-trainer — the only optimizer-family idea here that does. Honest note:
  it is a cousin of Fable's `agree` variant and the pool's sign-agree flip rule (MILL-623),
  but it acts on *evidence accumulation*, not the flip rule; the mill owner should dedupe at
  queue time if judged too close.

### B-015 — AdEMAMix for token-hungry runs
- **Source:** AdEMAMix — Pagliardini, Ablin, Grangier, arXiv:2409.03137, 2024-09-05, ICLR 2025.
- **Mechanism:** Adam with two EMAs of the gradient — a fast one (β≈0.9) and a very slow one
  (β up to 0.9999) — mixed into the update; old gradients stay useful for tens of thousands
  of steps, so a 1.3B model on 101B tokens matched AdamW on 197B, with slower forgetting.
- **How tried:** Swap in for STE and for shared parts on the longest runs (ladder rungs,
  multi-epoch arms from B-009), where its long-memory advantage should be largest.
- **Fit:** Needs gradient training. Honest tension worth stating: AdEMAMix's extra state is
  exactly what the vote counter exists to avoid — this is an STE-side entry, not a vote-side
  one.

### B-016 — APOLLO-Mini: tensor-wise optimizer scaling at SGD-level state
- **Source:** APOLLO / APOLLO-Mini — Zhu et al., arXiv:2412.05270, 2024-12-06, MLSys 2025.
- **Mechanism:** AdamW-quality training with the per-coordinate state replaced by structured
  approximations — channel/tensor-wise learning-rate scaling from low-rank random projections;
  Mini uses rank-1 tensor-wise scaling at SGD-level memory and composes with weight
  quantization in their tests.
- **How tried:** Optimizer swap for STE/shared parts; the interesting measurement is held
  loss at ~1 byte/param of optimizer state vs AdamW's ~8, extending the lab's state-economy
  comparison from the vote counter to the optimizer itself.
- **Fit:** Needs gradient training. Thematic fit is strong (state economy is the lab's home
  metric) even though it doesn't touch votes.

### B-017 — Schedule-Free training for the mill's arbitrary-budget probes
- **Source:** Schedule-Free — Defazio et al., "The Road Less Scheduled," arXiv:2405.15682,
  2024-05-24, NeurIPS 2024 (won the MLCommons 2024 AlgoPerf self-tuning track); follow-up
  ScheduleFree+, arXiv:2605.19095, 2026-05-20 (scales to LLMs, beats WSD, +31% at 1000
  tokens/param).
- **Mechanism:** Iterate averaging replaces the LR schedule entirely — no horizon T to set,
  so a run stopped at any budget is already near its averaged optimum.
- **How tried:** STE arms in the mill run under Schedule-Free AdamW; compare probe rankings
  against the scheduled runs. The real target is methodological: mill probes run 60–90 s
  while full trials run 8 min, and a horizon-dependent schedule makes probe results a biased
  predictor of full-trial results. Schedule-Free removes that confound.
- **Fit:** Needs gradient training (STE/shared parts). Uniquely valuable to the *mill itself*,
  not just to one chassis. Its FP iterate-averaging is the continuous cousin of the pool's
  modal readout for votes.

### B-018 — EWGS: discretization-error-scaled gradients for STE
- **Source:** EWGS — Lee, Kim, Ham, arXiv:2104.00903, CVPR 2021. ⚠ *2021, outside the stated
  window — included because it is the canonical STE repair, is absent from both lab docs, and
  the pool's STE recipe grid never varies the backward pass itself.*
- **Mechanism:** Scale each gradient element up or down by the sign agreement between the
  gradient and the weight's discretization error (w − Q(w)), with the factor adapted from
  Hessian information — directly attacks the damage STE does where quantization error and
  gradient fight.
- **How tried:** STE trainer variant with the EWGS backward scaling on BitLinear weights only;
  same recipe otherwise. A second, vote-side arm exists (weight votes by discretization error
  rather than |g|) if the first shows signal.
- **Fit:** Needs gradient training (a backward-pass change, not an optimizer swap).

### B-019 — ⚠ Adam-mini: block-wise second moments
- **Source:** Adam-mini — Zhang et al., 2024 (encountered via the APOLLO paper's discussion;
  **snippet-level sourcing only — verify the primary paper before building**).
- **Mechanism:** Replace per-coordinate second moments with one value per parameter block
  (per attention head, per neuron block), keeping Adam-like quality at much lower state.
- **How tried:** If verified: optimizer swap for STE/shared parts, same state-economy framing
  as B-016 — the two entries are alternative points on the same dial and should race.
- **Fit:** Needs gradient training.

### B-020 — ⚠ SCALE: column-normalized SGD with last-layer momentum
- **Source:** SCALE — Glentis et al., 2025-06-20 (**snippet-level sourcing — verify before
  building**).
- **Mechanism:** SGD with per-column gradient normalization plus momentum only on the last
  layer reportedly matches/beats Adam at 35–45% of the memory on LLaMA 60M–1B.
- **How tried:** If verified: a near-zero-state gradient baseline for STE — the control that
  tells the lab how much of STE's quality is Adam and how much is the latent weights
  themselves.
- **Fit:** Needs gradient training.

---

## Family 3 — Rotations: learned and online (beyond the pool's fixed Hadamard)

### B-021 — SpinQuant: *learned* rotations before ternarization
- **Source:** SpinQuant — Liu et al., arXiv:2405.16406, 2024-05-26 (v4 2025-02-20), ICLR 2025.
  Official repo: facebookresearch/SpinQuant.
- **Mechanism:** The orthogonal rotations that spread outliers are *learned* (Cayley-parameterized
  SGD) instead of random/fixed; the input-side rotation folds into the weights at zero runtime
  cost. Random rotations varied by up to 13 points in their tests; learned ones cut the
  remaining W4A4 gap to FP to 2.9 pts and beat fixed-rotation QuaRot's gap by up to 45.1%.
- **How tried:** Short gradient stage that learns one rotation per BitLinear input on the
  champion chassis, fold it in, then run the vote-trainer as usual on the rotated weights.
- **Fit:** Needs gradient training for the rotation-fitting stage only; the vote-trainer then
  runs unchanged. Distinct from the pool's MILL-129 (BitNet v2's *fixed* Hadamard at two
  sites) — learned-vs-fixed is the variable.

### B-022 — QuaRot placement: rotations through the residual stream + online Q/K rotation
- **Source:** QuaRot — Ashkboos et al., arXiv:2404.00456, Apr 2024, NeurIPS 2024.
- **Mechanism:** Randomized Hadamard rotations are pushed through the *whole* model including
  the residual stream (folded into adjacent weights), with an online Hadamard applied at the
  FFN down-projection input and to Q/K after RoPE — making every quantization site
  outlier-free rather than only the worst projections.
- **How tried:** Fixed-rotation arm with QuaRot's full placement (residual-stream folding +
  post-RoPE Q/K rotation) on the champion chassis, vs MILL-129's two-site placement.
- **Fit:** Fits the vote-trainer (rotations are fixed and folded; training is untouched).
  Honest note: facts here come via the SpinQuant paper's comparisons and survey snippets
  rather than a full read of the QuaRot paper — solid, but a skim of the original is cheap
  insurance before building.

---

## Family 4 — Attention forms that tolerate coarse logits

### B-023 — Sigmoid attention (drop softmax entirely)
- **Source:** Ramapuram et al. (Apple), "Theory, Analysis, and Best Practices for Sigmoid
  Self-Attention," arXiv:2409.04431, ICLR 2025. Code: github.com/apple/ml-sigmoid-attention.
- **Mechanism:** Replace row-wise softmax with element-wise sigmoid plus a −log(n) bias and
  normalization companions (QK-norm, LayerScale in their recipe). No sum-to-1 competition:
  each logit is judged on its own, attention sinks disappear by construction, and their
  FlashSigmoid kernel ran 17% faster than FlashAttention-2.
- **How tried:** Attention variant flag on the Tiny (sigmoid + −log n bias, with and without
  the pool's QK-norm), champion chassis, standard probe → full trial path.
- **Fit:** Architecture-level; trainer-agnostic (votes or STE). The lab-specific hypothesis:
  softmax's winner-take-all sharpening amplifies exactly the logit noise ternary Q/K
  projections produce; sigmoid's independent gating should degrade more gracefully. Distinct
  from the pool's gated attention (which keeps softmax and gates the *output*).

### B-024 — Differential attention (subtract a second softmax map)
- **Source:** Ye et al. (Microsoft Research / Tsinghua), "Differential Transformer,"
  arXiv:2410.05258, Oct 2024, ICLR 2025. Code: microsoft/unilm, Diff-Transformer.
- **Mechanism:** Each head computes two softmax maps from split Q/K halves and subtracts
  them (scaled by a learnable λ): common-mode attention noise cancels, relevant context is
  amplified (attention SNR 0.31 vs 0.03 reported); matched Transformer quality at ~65% of
  the parameters or tokens, with reduced activation outliers.
- **How tried:** Diff-attention flag on the Tiny at equal parameter count (halved head dim,
  paired maps), champion chassis. Logit/outlier reduction is measurable directly in the lab's
  activation instrumentation.
- **Fit:** Architecture-level; trainer-agnostic. Doubled softmax cost at lab context lengths
  (256) is negligible. The outlier-reduction claim is the quantization-relevant part — fewer
  activation outliers is precisely what 8-bit activation quantizers need.

---

## Family 5 — CPU inference kernels

### B-025 — T-MAC: bit-plane LUT matmul (look up by bits, never dequantize)
- **Source:** T-MAC — Wei et al., arXiv:2407.00088, 2024-06-25, EuroSys 2025.
  Repo: github.com/microsoft/T-MAC.
- **Mechanism:** Mixed-precision GEMM done with lookup tables over *bit planes* of the
  weights — no dequantization step, and cost scales linearly with weight bit-width. Reported
  up to 4× throughput and −70% energy vs llama.cpp; BitNet-b1.58-3B at 30 tok/s on 1 core,
  71 tok/s on 8 cores (M2 Ultra).
- **How tried:** Feed its bit-plane decomposition into the kernels stream's own bench
  (`kernels/bench_matmul.py`) as a third arm beside direct and TL-style LUT: ternary weights
  as sign-plane + magnitude-plane tables against int8 activations.
- **Fit:** Kernel-level. Distinct from bitnet.cpp's TL1/TL2 (already in the pool's background):
  T-MAC's per-bit-plane tables generalize the LUT idea and are the current CPU reference
  point to beat or adopt.

### B-026 — TEAL: training-free activation sparsity at decode
- **Source:** TEAL — Liu et al., arXiv:2408.14690, 2024-08-28, ICLR 2025.
- **Mechanism:** Zero out activations below a per-matrix magnitude threshold at inference —
  40–50% sparsity across *all* matrices (not just FFN gates), 1.53×/1.8× decode speedups at
  40%/50% sparsity in their tests, no training or calibration set required; composes with
  weight quantization.
- **How tried:** In the lab's decode bench: threshold-sparsify inputs to each ternary GEMV
  and skip the corresponding weight columns; measure the accuracy/speed frontier at several
  thresholds on a trained champion.
- **Fit:** Kernel-level. Composes with the chassis's ReLU² zeros (which are structural; TEAL's
  are threshold-induced and apply at sites ReLU² doesn't touch). Honest note: published gains
  are batch-1 GPU decode — the CPU payoff must be re-measured in the lab's own bench, and
  only counts with a column-skip kernel behind it.

### B-027 — PowerInfer-2: predicted hot/cold neuron scheduling
- **Source:** PowerInfer-2 — Xue et al., arXiv:2406.06282, 2024-06-10, MobiCom '24.
- **Mechanism:** Activation sparsity is *predicted* ahead of time (neuron-cluster abstraction)
  and the compute schedule is built around the prediction — hot neurons resident and dense,
  cold neurons handled sparsely — rather than discovered after the fact (up to 27.8× vs
  llama.cpp on one phone workload; 47B at 11.68 tok/s).
- **How tried:** At lab scale the transferable piece is cluster-level activation prediction:
  profile a trained champion's FFN activation patterns, test whether a cheap predictor can
  name the active set before the GEMV runs.
- **Fit:** Kernel/systems-level. **Honest weak-fit note:** a <2M-weight model is cache-resident,
  so PowerInfer-2's I/O pipelining — its main win — doesn't transfer; only the prediction
  idea does, and it races B-026's simpler thresholding for the same prize.

### B-028 — Ladder/BitBLAS: offline weight-layout transformation as the kernel trick
- **Source:** Ladder — Wang et al., OSDI '24; microsoft/BitBLAS repo (first W_INT2A_INT8
  GEMV/GEMM built for BitNet-b1.58; W_INT1A_INT8 up to 8.8× vs FP16 baselines on A100).
- **Mechanism:** Instead of writing a smarter runtime kernel, *transform the weights offline*
  (interleave/permute into the layout the hardware consumes) so the runtime operation becomes
  trivial.
- **How tried:** Apply the principle on CPU: pre-permute the lab's packed ternary weights into
  exactly the order the lab's fastest kernel consumes, so inference does zero unpacking or
  shuffling at run time.
- **Fit:** Kernel-level — **with the honest caveat that the library itself is GPU-only and
  does not run on the lab's CPU.** What transfers is the layout principle, feeding the same
  kernel bench as B-025.

### B-029 — FLUTE-style offline restructuring for LUT kernels
- **Source:** FLUTE — Guo et al., arXiv:2407.10960, 2024-07-15, Findings of EMNLP 2024.
- **Mechanism:** A flexible LUT engine that restructures weights *offline* to minimize
  unpacking cost and duplicates lookup tables against the actual bandwidth bottleneck
  (2–4× GEMM at batch <32, 1.5–2× end-to-end in their GPU tests).
- **How tried:** Same bench as B-025/B-028: test whether a restructured/duplicated table
  layout beats the naive one for the lab's ternary×int8 GEMV at batch 1.
- **Fit:** Kernel-level, GPU-origin like B-028 — included as a *design principle* for the CPU
  LUT family (T-MAC line), not as a port. If the kernels stream judges two GPU-principle
  entries one too many, this is the one to drop first.

### B-030 — Sparse-BitNet: joint 1.58-bit + N:M structured sparsity
- **Source:** Sparse-BitNet, arXiv:2603.05168, 2026. ⚠ *Preprint, single-source — treat
  numbers as unverified until replicated.*
- **Mechanism:** Train 1.58-bit quantization and dynamic N:M semi-structured weight sparsity
  in one stable framework; ternary weights degrade *less* than BF16 at equal sparsity, and a
  custom sparse tensor core converts the regular zero pattern into real speed (~1.30×).
- **How tried:** Two arms: (a) gradient-side — N:M mask constraint during STE training at
  2:4 and 4:8; (b) vote-side (speculative) — restrict vote accumulation/flips to within N:M
  blocks so the resulting zero pattern is block-regular by construction.
- **Fit:** (a) needs gradient training today; (b) fits the vote-trainer but is a translation,
  not a replication. The durable idea either way: make the zero structure *regular* so
  skipping it is predictable — ~42% of ternary weights are already zero, just irregularly.

---

## Family 6 — Measurement / planning

### B-031 — Fit the lab's results to the precision scaling law
- **Source:** Kumar et al., "Scaling Laws for Precision," arXiv:2411.04330, 2024-11-07,
  ICLR 2025 (law fitted on 465 runs up to 1.7B params / 26B tokens).
- **Mechanism:** Low training precision acts as a *reduced effective parameter count*, and
  post-training quantization degradation grows with the tokens-per-parameter ratio —
  overtraining a small model makes it harder to quantize after the fact.
- **How tried:** No new training: fit the lab's existing ladder + vote/STE results to the
  effective-parameter form and predict (a) whether the votes-vs-STE gap closes or widens at
  the ~12M+ rungs, and (b) the token budget at which convert-late (FP-then-ternarize) stops
  being viable. Check predictions against the next ladder rungs as they land.
- **Fit:** Modeling/measurement — neither trainer. Cheap (analysis only) and it prices
  several queued arms before the mill spends probes on them.

---

## Deliberately excluded (checked, and why)

- **QuaRot as a standalone fixed-rotation entry** — folded into B-022 by placement; a plain
  fixed-Hadamard arm already exists as MILL-129.
- **SOAP and other Muon successors** — the pool already carries Muon; marginal novelty at lab
  scale did not clear the bar.
- **Softpick / rectified-softmax sink fixes** — the pool's gated-attention and sink-logit arms
  already cover the sink problem; B-023/B-024 attack the same problem from stronger,
  better-sourced directions.
- **Length/difficulty curricula** — plausible, but the sourcing found was too thin to cite
  responsibly; revisit only with a primary source in hand.

## Flags summary (verify before building)

- ⚠ **B-019 (Adam-mini)** and **B-020 (SCALE)** — snippet-level sourcing; confirm the primary
  papers first.
- ⚠ **B-009 (Muennighoff)** and **B-012 (DoReMi)** — 2023 papers, included on regime-fit.
- ⚠ **B-018 (EWGS)** — 2021, included as the canonical STE backward-pass repair.
- ⚠ **B-030 (Sparse-BitNet)** — 2026 preprint, single source.
- **B-022 (QuaRot)** — facts via SpinQuant's comparisons; skim the original before building.

*End of CANDIDATES-B. 31 entries: 12 data/tokenizer, 8 optimizer, 2 rotation, 2 attention,
6 kernel, 1 measurement. Nothing here edits or duplicates IDEA-POOL.md; dedupe at queue time
is the mill owner's call, as with MILL-623 vs B-014.*
