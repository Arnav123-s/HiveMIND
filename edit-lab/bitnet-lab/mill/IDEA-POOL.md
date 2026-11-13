# IDEA-POOL — the mill's master pool (Muse's work, Muse's side)

<!-- Muse's work — Muse's side of the BitNet lab. Not Fable's side; nothing here touches it. -->

Built 2026-11-12 under Arnav's mass-testing directive: thousands of variations screened
cheaply, winners promoted to full trials, everything ledgered. This file is the queue's
source of truth: `mill/screen.py` reads the fenced `mill` blocks, works entries in order,
skips any (id, champion-generation) already in `mill/ledger.jsonl`, and queues full trials
inline when a probe beats the bar (see `mill/PROMOTE.md`).

**Execution modes.** Every entry carries a `mode`:
- **sweep** — a same-chassis CONFIG variant (arm/dim/layers/batch/rope combinations using
  flags train.py already has). These run inside ONE shared-data sweep process
  (`mill/sweep_probe.py`): the corpus memmap and the 128 held windows are built once, then
  variants run back-to-back in-process. On this VM, process startup (torch import) plus
  data setup is a large share of a 75-second probe's cost — the sweep removes it per-probe.
  Sweep is the DEFAULT execution path for config variants.
- **process** — anything that changes a code path (a new flag, trainer, block type, or
  sampler). These run as isolated train.py subprocesses, one per probe, and STAY isolated
  even after their flag is implemented: a code change earns isolation until it has a
  full-trial record. Entries needing flags train.py does not have yet are reported
  DEFERRED by screen.py (never ledgered) until the flag lands.

**The chassis.** Unless an entry says otherwise, probes run on the lab's best stack:
layered_half + rotary (held 2.8580 ± 0.0161 at full format). Job zero (MILL-000) is the
unchanged chassis at probe budget and is always measured first in each champion
generation; every verdict is relative to it.

**Status.** Every entry below is `queued`. Screened/promoted state lives in the ledger
and `mill/trials.jsonl`, not here — this file only gains entries, it never loses them.

**Already tested and CLOSED — deliberately NOT in this pool** (full list with numbers in
the appendix): overshoot carry, AdamW two-stage cooldown on the layered chassis,
vote-threshold annealing 8→64, magnitude-weighted votes AS SPECIFIED (un-calibrated
±96 threshold; the calibrated retest MILL-201..203 is a different arm and IS pooled),
the JEPA objective, magnitude votes at full size, and every arm already measured at
full format in the lab's RESULTS files.



## Job zero — the probe-scale baseline (always first in each champion generation)

### MILL-000 · Job zero: unchanged chassis at probe budget
- **source:** mill design (screen.py's baseline job)
- **mechanism:** the current champion configuration (default: layered_half + rotary) run at probe budget, unchanged. Every probe verdict in the ledger is relative to this number, per champion generation — when a full trial adopts a new champion, job zero is re-measured under the new configuration before any further verdicts are issued.
- **train.py:** no change; champion config from `mill/champion.json` (default below)
- **mode:** sweep — same-chassis config variant; runs inside the shared-data sweep process (corpus loaded once)
- **prediction:** defines the baseline; expected to sit well above the full-format 2.8580 (75 seconds buys far fewer steps).
- **status:** queued
```mill
id: MILL-000
mode: sweep
run: --arm layered_half --rope
```


## A — Research-ranked tests (report 2026-11-12 §4 and its evidence sections)

### MILL-101 · QK-Norm (per-head RMSNorm on Q and K)
- **source:** research report 2026-11-12 §4 rank 1
- **mechanism:** RMSNorm on Q,K per head before the dot product; bounds the coarse ternary QK logits that softmax exponentiates. Norms stay FP; no ternary matmul added.
- **train.py:** new flag `--qk-norm` in Block (apply to q,k after qkv projection, before RoPE)
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.03..-0.10 at probe scale. Strongest single prior in the pool (near-universal in 2025-26 flagships; attacks the lab's known logit-coarseness).
- **status:** queued
```mill
id: MILL-101
mode: process
run: --arm layered_half --rope --qk-norm
```

### MILL-102 · QK-Norm on Q only
- **source:** research report 2026-11-12 §4 rank 1 (placement variant)
- **mechanism:** Q-only half of MILL-101: normalising the query side alone bounds logit scale from one side; cheaper, tests whether both sides are needed.
- **train.py:** new flag `--qk-norm-q`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.01..-0.06; if it matches MILL-101, both-side norming is unnecessary here.
- **status:** queued
```mill
id: MILL-102
mode: process
run: --arm layered_half --rope --qk-norm-q
```

### MILL-103 · QK-Norm on K only
- **source:** research report 2026-11-12 §4 rank 1 (placement variant)
- **mechanism:** K-only half of MILL-101: key norms set each position's logit ceiling; tests the other side of the placement question.
- **train.py:** new flag `--qk-norm-k`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.01..-0.06; placement answer feeds whichever of 101-103 promotes.
- **status:** queued
```mill
id: MILL-103
mode: process
run: --arm layered_half --rope --qk-norm-k
```

### MILL-104 · Gated attention (sigmoid gate on attention output)
- **source:** research report 2026-11-12 §4 rank 2
- **mechanism:** Head-specific FP gate Y' = Y * sigmoid(X W_theta) after SDPA, before the output projection; lets a head output nothing instead of dumping mass on a sink token, suppressing the massive activations that break INT8 absmax quant.
- **train.py:** new flag `--gated-attn` (gate projection kept FP, per-head)
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.02..-0.08; strong published evidence (NeurIPS'25 best paper, 3.5T tokens); watch activation-max side metrics at full trial.
- **status:** queued
```mill
id: MILL-104
mode: process
run: --arm layered_half --rope --gated-attn
```

### MILL-105 · Attention sink logit (gpt-oss style)
- **source:** research report 2026-11-12 §4 rank 2 fallback arm
- **mechanism:** One learned per-head scalar added to the softmax denominator; a head can attend to nothing with zero extra matmuls. The cheap sibling of MILL-104.
- **train.py:** new flag `--sink-logit`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.01..-0.05 at ~zero cost; if it captures most of 104's gain it is the better buy at this scale.
- **status:** queued
```mill
id: MILL-105
mode: process
run: --arm layered_half --rope --sink-logit
```

### MILL-106 · Gated attention, low-rank gate
- **source:** research report 2026-11-12 §4 rank 2 (cost variant)
- **mechanism:** Gate projection factorised (dim -> 16 -> dim per head group); tests whether the gate needs full rank to do its work.
- **train.py:** new flag `--gated-attn-lr 16`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.01..-0.06; mainly a cost probe for 104.
- **status:** queued
```mill
id: MILL-106
mode: process
run: --arm layered_half --rope --gated-attn-lr 16
```

### MILL-107 · Per-output-channel absmean scales
- **source:** research report 2026-11-12 §4 rank 3
- **mechanism:** Scale granularity per-tensor -> per-output-channel for every BitLinear (and the vote trainers' install scale). All magnitude information lives in the scales; per-channel cuts error where rows have heterogeneous latent magnitudes, at one FP multiply per output.
- **train.py:** new flag `--scale-gran channel` in BitLinear + Layered/Direct install
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.02..-0.07; ParetoQ says quant-function/granularity choice alone can flip conclusions at sub-4-bit.
- **status:** queued
```mill
id: MILL-107
mode: process
run: --arm layered_half --rope --scale-gran channel
```

### MILL-108 · Per-group-64 absmean scales
- **source:** research report 2026-11-12 §4 rank 3 (granularity variant)
- **mechanism:** Scales per 64-weight group: between per-tensor and per-channel; tests where the granularity payoff saturates.
- **train.py:** new flag `--scale-gran group64`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.01..-0.05; with 107 and the tensor default this traces the granularity curve.
- **status:** queued
```mill
id: MILL-108
mode: process
run: --arm layered_half --rope --scale-gran group64
```

### MILL-109 · Two-stage LR on the STE chassis (abrupt mid-run drop)
- **source:** research report 2026-11-12 §4 rank 5 (recipe bundle, part 1)
- **mechanism:** STE chassis: stage 1 at lr 3e-3, at 50% an abrupt drop to 3e-4 for stage 2 (the official BitNet pattern: the loss drop appears AT the mid-training decay). Distinct from the closed round-2 cooldown: that was a linear decay on the LAYERED chassis's AdamW parts only.
- **train.py:** new flag `--two-stage` on the STE trainer (chassis-changing entry: arm ste_half + rope)
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.02..-0.06 vs the ste_half+rope control (MILL-1903); official-recipe evidence at 700M-3.9B.
- **status:** queued
```mill
id: MILL-109
mode: process
run: --arm ste_half --rope --two-stage
```

### MILL-110 · Two-stage LR + WD (WD 0.1 in stage 1, 0 in stage 2)
- **source:** research report 2026-11-12 §4 rank 5 (recipe bundle, part 2)
- **mechanism:** The full official two-stage: weight decay cosines to 0.1 during stage 1 and switches OFF in stage 2 — in a BitNet, WD edits the discrete code, so leaving it on late actively harms convergence.
- **train.py:** new flag `--two-stage-wd` on the STE trainer
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.02..-0.07; the WD-off half is the ternary-specific part and has never run in this lab in any form.
- **status:** queued
```mill
id: MILL-110
mode: process
run: --arm ste_half --rope --two-stage-wd
```

### MILL-111 · FP-first budget split 90/10 (ParetoQ)
- **source:** research report 2026-11-12 §4 rank 5 (recipe bundle, part 3)
- **mechanism:** Train the chassis as a plain FP model for the first 90% of steps, then switch the forward to ternary for the last 10% (compensation before reconstruction). At fixed budget ParetoQ found this beats ternary-from-scratch at every width tested.
- **train.py:** new flag `--fp-first 0.9` (EASE schedule variant: rounding eased in only in the final 10%)
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.01..-0.06 at probe scale, growing with budget; the probe under-measures it (the split pays at longer horizons), so a flat probe does NOT kill it — see PROMOTE.md exception list.
- **status:** queued
```mill
id: MILL-111
mode: process
run: --arm layered_half --rope --fp-first 0.9
```

### MILL-112 · FP-first budget split 75/25
- **source:** research report 2026-11-12 §4 rank 5 (split variant)
- **mechanism:** Same mechanism as MILL-111 with a longer ternary phase; brackets the split point.
- **train.py:** new flag `--fp-first 0.75`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.01..-0.05; together with 111 and the 100%-ternary chassis this traces the split curve.
- **status:** queued
```mill
id: MILL-112
mode: process
run: --arm layered_half --rope --fp-first 0.75
```

### MILL-113 · Distillation: logits KD from a same-lab FP teacher (alpha 1.0)
- **source:** research report 2026-11-12 §4 rank 7
- **mechanism:** Teacher = the FP twin of the chassis trained on the same corpus; student loss = CE + 1.0 * KL(teacher||student) at temperature 2. Teacher logits give the ternary student a denser target than one-hot labels, compensating STE's coarse gradient information.
- **train.py:** new flag `--kd 1.0` + teacher checkpoint plumbing in train.py
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.02..-0.08 on held loss, more on probe tasks (BitDistill: gains show on tasks first); costs a teacher run per trial, charged to the idea.
- **status:** queued
```mill
id: MILL-113
mode: process
run: --arm layered_half --rope --kd 1.0
```

### MILL-114 · Distillation: logits KD (alpha 0.5)
- **source:** research report 2026-11-12 §4 rank 7 (dose variant)
- **mechanism:** Half-dose version of MILL-113; brackets the KD weight.
- **train.py:** new flag `--kd 0.5`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.01..-0.06; dose answer for 113.
- **status:** queued
```mill
id: MILL-114
mode: process
run: --arm layered_half --rope --kd 0.5
```

### MILL-115 · Distillation: logits + attention-relation KD
- **source:** research report 2026-11-12 §4 rank 7 (BitDistill full form)
- **mechanism:** MILL-113 plus MiniLM-style attention-relation KD on the last layer only (single-layer beat multi-layer in BitDistill).
- **train.py:** new flag `--kd 1.0 --kd-attn`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.03..-0.09 if attention relations transfer at this scale; the most faithful BitDistill transplant in the pool.
- **status:** queued
```mill
id: MILL-115
mode: process
run: --arm layered_half --rope --kd 1.0 --kd-attn
```

### MILL-116 · Hybrid Gated-DeltaNet 3:1 (FP state and gates, ternary projections)
- **source:** research report 2026-11-12 §4 rank 8
- **mechanism:** Replace 3 of 4 blocks with Gated-DeltaNet recurrent blocks (state S, beta and decay gates stay FP; only Q/K/V/gate/output projections ternarize); 1 full-attention block keeps exact recall. Removes KV growth; the report's biggest upside/risk item.
- **train.py:** new block type + flag `--deltanet 3` (chassis-changing entry)
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** High variance: -0.05..+0.15. No ternary evidence exists; CPU training of the recurrent form is slower per token, charged honestly at equal minutes.
- **status:** queued
```mill
id: MILL-116
mode: process
run: --arm layered_half --rope --deltanet 3
```

### MILL-117 · RWKV-7-style recurrent blocks 3:1 (FP state)
- **source:** research report 2026-11-12 §4 §3.5 (unranked sibling of rank 8)
- **mechanism:** Same hybrid slot as MILL-116 with RWKV-7 time-mix/channel-mix blocks (generalised delta rule, vector gating, token-shift); state stays FP.
- **train.py:** new block type + flag `--rwkv 3` (chassis-changing entry)
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** High variance, slightly worse prior than 116 (no ternary precedent, more multiplicative gate interactions). Only worth its probe after 116 reads.
- **status:** queued
```mill
id: MILL-117
mode: process
run: --arm layered_half --rope --rwkv 3
```

### MILL-118 · Embedding: tied INT8 instead of FP
- **source:** research report 2026-11-12 §4 rank 9
- **mechanism:** Quantize the tied embedding/head table to INT8 (per-row scales). Embeddings dominate small-model bytes; this measures the precision cost at the exact place the report says to measure, not assume.
- **train.py:** new flag `--emb-int8`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Held loss +0.00..+0.04 expected (a cost, not a gain) — the probe's job is pricing the byte saving honestly; judged per byte at trial.
- **status:** queued
```mill
id: MILL-118
mode: process
run: --arm layered_half --rope --emb-int8
```

### MILL-119 · Embedding: untied FP head
- **source:** research report 2026-11-12 §4 rank 9 (variant)
- **mechanism:** Untie the LM head from the embedding (head gets its own FP table). Tests whether tying is costing the small model capacity.
- **train.py:** new flag `--untie-head`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.01..+0.03; parameter cost is large at this scale, so it must win clearly to matter.
- **status:** queued
```mill
id: MILL-119
mode: process
run: --arm layered_half --rope --untie-head
```

### MILL-120 · Coarse MoE: 4 experts, top-1 + shared expert
- **source:** research report 2026-11-12 §4 rank 10
- **mechanism:** FFN becomes 4 expert FFNs + 1 always-on shared expert, top-1 routing, router in FP, experts counted inside the same total weight budget. The only MoE form whose capacity gain can beat its CPU gather/cache cost at this scale.
- **train.py:** new flag `--moe 4 --moe-top 1 --moe-shared` (chassis-changing entry)
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.02..+0.06 at equal total weights; expect a speed loss — the probe reports held only, the trial must report both.
- **status:** queued
```mill
id: MILL-120
mode: process
run: --arm layered_half --rope --moe 4 --moe-top 1 --moe-shared
```

### MILL-121 · Coarse MoE: 8 experts, top-2 + shared expert
- **source:** research report 2026-11-12 §4 rank 10 (variant)
- **mechanism:** Wider/sparser sibling of MILL-120.
- **train.py:** new flag `--moe 8 --moe-top 2 --moe-shared`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.01..+0.08; expert starvation risk rises with expert count at fixed tokens.
- **status:** queued
```mill
id: MILL-121
mode: process
run: --arm layered_half --rope --moe 8 --moe-top 2 --moe-shared
```

### MILL-122 · Coarse MoE: 4 experts, hash routing (first block)
- **source:** research report 2026-11-12 §4 rank 10 + §3.7l
- **mechanism:** MILL-120 but the first block's router is replaced by token-ID hash routing — no router matmul for ternary noise to corrupt, and collapse is impossible by construction.
- **train.py:** new flag `--moe 4 --moe-top 1 --moe-shared --moe-hash-first`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Within noise of 120 on loss; wins if it removes routing pathology (check expert utilisation at trial).
- **status:** queued
```mill
id: MILL-122
mode: process
run: --arm layered_half --rope --moe 4 --moe-top 1 --moe-shared --moe-hash-first
```

### MILL-123 · MTP: one extra prediction head, loss weight 0.1 (training-only)
- **source:** research report 2026-11-12 §4 rank 11
- **mechanism:** An auxiliary head predicts token t+2 during training and is discarded at inference — denser supervision per token for a token-hungry model, at zero inference cost.
- **train.py:** new flag `--mtp 0.1`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Coin-flip at this scale (the source paper warns the benefit can reverse for small models): -0.03..+0.03.
- **status:** queued
```mill
id: MILL-123
mode: process
run: --arm layered_half --rope --mtp 0.1
```

### MILL-124 · MTP: loss weight 0.3
- **source:** research report 2026-11-12 §4 rank 11 (dose variant)
- **mechanism:** Stronger-dose sibling of MILL-123.
- **train.py:** new flag `--mtp 0.3`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.02..+0.04; dose bracket for 123.
- **status:** queued
```mill
id: MILL-124
mode: process
run: --arm layered_half --rope --mtp 0.3
```

### MILL-125 · Muon optimizer for the latent/ternary-side parameters
- **source:** research report 2026-11-12 §4 rank 12
- **mechanism:** Newton-Schulz-orthogonalised momentum replaces AdamW for the matrix parameters (AdamW kept for embeddings/norms/scales). Orthogonalised updates might move latents across STE thresholds more uniformly; completely untested with ternary latents.
- **train.py:** new flag `--muon` on the STE trainer (chassis-changing entry)
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Unknown: -0.04..+0.04. Watch max-logit growth (the side effect that forced QK-Clip into existence).
- **status:** queued
```mill
id: MILL-125
mode: process
run: --arm ste_half --rope --muon
```

### MILL-126 · Muon with per-head split for attention projections
- **source:** research report 2026-11-12 §4 rank 12 (GLM-5 Muon Split form)
- **mechanism:** MILL-125 but attention projections are orthogonalised per head rather than per matrix — the form GLM-5 found necessary.
- **train.py:** new flag `--muon --muon-split`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Unknown; only meaningful relative to 125's reading.
- **status:** queued
```mill
id: MILL-126
mode: process
run: --arm ste_half --rope --muon --muon-split
```

### MILL-127 · SubLN: add norms before attention-output and FFN-output projections
- **source:** research report §2.3/§2.4 (BitDistill step 1; original BitNet)
- **mechanism:** Extra LayerNorms inside the sublayers at the two points BitDistill inserts them before distilling — bounds activation variance at the projections whose outputs feed the next quantizer.
- **train.py:** new flag `--subln` in Block
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.01..-0.05; the SubLN direction is contested (see MILL-128), this pair is one experiment, not two.
- **status:** queued
```mill
id: MILL-127
mode: process
run: --arm layered_half --rope --subln
```

### MILL-128 · Norm removal: drop the blocks' inner pre-norms (Falcon-E direction)
- **source:** research report §2.3 (Falcon-E, blog source — flagged)
- **mechanism:** The opposite SubLN direction: Falcon-E removed the LayerNorms inside BitLinear layers and trained fine at 1-3B. Here: remove n2 (FFN pre-norm), keep n1 — the partial form that fits this code's shape.
- **train.py:** new flag `--no-ffn-norm` in Block
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** +0.00..+0.08 expected (likely worse); run as the contested-direction control for 127, cheap at probe scale.
- **status:** queued
```mill
id: MILL-128
mode: process
run: --arm layered_half --rope --no-ffn-norm
```

### MILL-129 · Hadamard rotation before activation quantization (BitNet v2)
- **source:** research report §2.1 (BitNet v2, preprint)
- **mechanism:** Apply an online Hadamard rotation to the outlier-heavy projections (attention output, FFN down) before INT8 absmax activation quant — spreads outliers across channels so per-token absmax stops being destroyed by single channels.
- **train.py:** new flag `--hadamard` in BitLinear forward for out/down projections
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.01..-0.05; CPU cost is real (FWHT per token) — a win must survive the trial's speed report.
- **status:** queued
```mill
id: MILL-129
mode: process
run: --arm layered_half --rope --hadamard
```

### MILL-130 · Activation sparsification, second stage (a4.8-style)
- **source:** research report §2.1 (BitNet a4.8)
- **mechanism:** After 75% of steps, switch FFN intermediate states to sparsify+8-bit (top-magnitude kept) while other activations stay 8-bit; exploits ReLU-family zero-heavy intermediates.
- **train.py:** new flag `--act-sparsify 0.75`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.00..-0.03 on loss; the real claim is inference-side, so this is a cheap existence probe only.
- **status:** queued
```mill
id: MILL-130
mode: process
run: --arm layered_half --rope --act-sparsify 0.75
```

### MILL-131 · QK-Clip (threshold 100)
- **source:** research report §3.7i (Kimi MuonClip)
- **mechanism:** Rescale a head's Q/K projections when its max attention logit exceeds tau=100 — a cheap, targeted logit governor in the same family as QK-Norm but event-driven instead of always-on.
- **train.py:** new flag `--qk-clip 100`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.00..-0.03 at this scale (logits rarely reach 100 in 75 s); mainly insurance data for the Muon entries.
- **status:** queued
```mill
id: MILL-131
mode: process
run: --arm layered_half --rope --qk-clip 100
```

### MILL-132 · QK-Clip (threshold 30)
- **source:** research report §3.7i (dose variant)
- **mechanism:** Lower-threshold sibling of MILL-131; at tau=30 the clip actually fires at lab scale.
- **train.py:** new flag `--qk-clip 30`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.01..-0.04; if 132 >> 131, logit spikes are a live problem here, which re-ranks 101.
- **status:** queued
```mill
id: MILL-132
mode: process
run: --arm layered_half --rope --qk-clip 30
```

### MILL-133 · Partial RoPE (25% of head dims rotated)
- **source:** research report §3.7e (Qwen3-Next form)
- **mechanism:** Rotate only the first quarter of each head's dims; the rest do pure content matching. Zero parameters, zero matmuls; reduces the chance rotation of coarsely-quantized Q/K scrambles long-range logits.
- **train.py:** new flag `--rope-frac 0.25`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** ~0 at matched train/serve length (the report is explicit); included because it is free and the lab's ctx may grow — a flat probe is the expected, acceptable answer.
- **status:** queued
```mill
id: MILL-133
mode: process
run: --arm layered_half --rope --rope-frac 0.25
```

### MILL-134 · Partial RoPE (50%)
- **source:** research report §3.7e (dose variant)
- **mechanism:** Half-rotated sibling of MILL-133.
- **train.py:** new flag `--rope-frac 0.5`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** ~0 expected; dose bracket for 133.
- **status:** queued
```mill
id: MILL-134
mode: process
run: --arm layered_half --rope --rope-frac 0.5
```

### MILL-135 · NoPE interleaving (every 4th block position-free)
- **source:** research report §3.7e (Llama 4 iRoPE form)
- **mechanism:** Blocks 4, 8, ... use no position information at all (NoPE); position is carried by the RoPE blocks. Zero cost.
- **train.py:** new flag `--nope-every 4`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** ~0 at ctx 256; same reasoning as 133 — cheap insurance data, not an expectation.
- **status:** queued
```mill
id: MILL-135
mode: process
run: --arm layered_half --rope --nope-every 4
```

### MILL-136 · SwiGLU in place of GELU (negative control)
- **source:** research report §3.7f (explicitly sanctioned as a negative control)
- **mechanism:** Replace the FFN's GELU with SwiGLU. Frontier-universal but mechanistically wrong for ternary: it multiplies two coarsely-quantized branches and destroys the zero-sparsity the down-projection exploits. Run once so the pool owns the number.
- **train.py:** new flag `--ffn swiglu`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** +0.02..+0.10 (expected WORSE). A control, not a candidate: if it wins, something in our mechanistic picture is wrong and that is worth knowing.
- **status:** queued
```mill
id: MILL-136
mode: process
run: --arm layered_half --rope --ffn swiglu
```

### MILL-137 · Sliding-window/global hybrid 3:1, window 128
- **source:** research report §4 rank 6
- **mechanism:** 3 local blocks (window = half of ctx 256) : 1 global block. Bounds the unquantized KV/softmax cost and confines logit noise locally. NOTE: the report ranks this only for ctx >= 1024; at ctx 256 this is a down-payment probe whose loss reading is expected flat — its trial must include a long-context check or not happen.
- **train.py:** new flag `--swa 3:1:128`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** ~0 on held loss at ctx 256 (expected); value is the tok/s + KV-bytes side reading at trial.
- **status:** queued
```mill
id: MILL-137
mode: process
run: --arm layered_half --rope --swa 3:1:128
```

### MILL-138 · Sliding-window/global hybrid 5:1, window 64
- **source:** research report §4 rank 6 (dose variant)
- **mechanism:** More aggressive locality sibling of MILL-137.
- **train.py:** new flag `--swa 5:1:64`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** ~0..+0.03 on loss; efficiency-side bracket for 137.
- **status:** queued
```mill
id: MILL-138
mode: process
run: --arm layered_half --rope --swa 5:1:64
```


## B — Direct-trainer study: untested vote-trainer levers

### MILL-201 · Magnitude-weighted votes, CALIBRATED threshold (x1)
- **source:** direct-trainer study 2026-11-11 C1 (fair retest)
- **mechanism:** The study's top candidate, re-set fairly: increments clip(round(-g/mean|g|), -3, +3) with NO median gate, and the flip threshold calibrated to the measured mean |increment| (the as-specified +-96 threshold made the original arm ~3x too cold — its measured loss, 3.135, is a verdict on that setting, not this one). This entry is the calibrated x1 point.
- **train.py:** new flag `--mag-cal 1.0` on Direct (int16 counters)
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.02..-0.07 vs plain votes; the 2-bit point on the accumulator-precision dial is where the STE gap should shrink most per added bit.
- **status:** queued
```mill
id: MILL-201
mode: process
run: --arm plain_half --rope --mag-cal 1.0
```

### MILL-202 · Magnitude-weighted votes, calibrated threshold (x0.5, hotter)
- **source:** direct-trainer study 2026-11-11 C1 (dose variant)
- **mechanism:** Half the calibrated threshold of MILL-201: flips roughly twice as often.
- **train.py:** new flag `--mag-cal 0.5`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Dose bracket for 201; if 202 > 201 > plain, the dial point is hotter than calibrated.
- **status:** queued
```mill
id: MILL-202
mode: process
run: --arm plain_half --rope --mag-cal 0.5
```

### MILL-203 · Magnitude-weighted votes, calibrated threshold (x2, colder)
- **source:** direct-trainer study 2026-11-11 C1 (dose variant)
- **mechanism:** Twice the calibrated threshold of MILL-201: flips roughly half as often.
- **train.py:** new flag `--mag-cal 2.0`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Dose bracket for 201.
- **status:** queued
```mill
id: MILL-203
mode: process
run: --arm plain_half --rope --mag-cal 2.0
```

### MILL-204 · Vote-threshold schedule 32 -> 64 (never hot)
- **source:** direct-trainer study 2026-11-11 C2 (repaired form)
- **mechanism:** V rises linearly 32->64 over the run: starts AT the proven setting and cools. Distinct from the closed anneal arm (8->64, lost 3.850) whose failure was the hot start firing flips on weak early evidence; this schedule never goes below the proven floor.
- **train.py:** new flag `--vsched 32:64` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.01..-0.04; the cool-down is the largest cheap effect in Fable's trace (0.24 at founding length on the STE side) — this tests its vote-side form without the known poison.
- **status:** queued
```mill
id: MILL-204
mode: process
run: --arm layered_half --rope --vsched 32:64
```

### MILL-205 · Vote-threshold schedule 32 -> 96
- **source:** direct-trainer study 2026-11-11 C2 (dose variant)
- **mechanism:** Deeper-cooling sibling of MILL-204.
- **train.py:** new flag `--vsched 32:96`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Dose bracket for 204.
- **status:** queued
```mill
id: MILL-205
mode: process
run: --arm layered_half --rope --vsched 32:96
```

### MILL-206 · Vote-threshold schedule 24 -> 48
- **source:** direct-trainer study 2026-11-11 C2 (dose variant)
- **mechanism:** Milder, slightly-hotter-start sibling; starts just under the proven 32, far above the poisoned 8.
- **train.py:** new flag `--vsched 24:48`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Dose bracket; together 204-206 map the schedule family without re-entering the closed 8->64 form.
- **status:** queued
```mill
id: MILL-206
mode: process
run: --arm layered_half --rope --vsched 24:48
```

### MILL-207 · Per-layer vote threshold (flip-rate target 0.1%/step)
- **source:** direct-trainer study 2026-11-11 C2 (per-layer form)
- **mechanism:** Each layer's V adapts so its flip rate tracks 0.1% of weights/step — layers differ widely in gradient distribution, and one global V spends the flip budget unevenly across them.
- **train.py:** new flag `--vlayer 0.001` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.01..-0.04; the mechanism (equalise flip rates) is independent of the schedule question in 204.
- **status:** queued
```mill
id: MILL-207
mode: process
run: --arm layered_half --rope --vlayer 0.001
```

### MILL-208 · Per-layer vote threshold (flip-rate target 0.3%/step)
- **source:** direct-trainer study 2026-11-11 C2 (dose variant)
- **mechanism:** Hotter per-layer target sibling of MILL-207.
- **train.py:** new flag `--vlayer 0.003`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Dose bracket for 207.
- **status:** queued
```mill
id: MILL-208
mode: process
run: --arm layered_half --rope --vlayer 0.003
```

### MILL-209 · Fractional leak lambda=0.99 (true momentum on the vote stream)
- **source:** direct-trainer study 2026-11-11 C3
- **mechanism:** Replace integer lockstep leak with per-step fractional decay count <- 0.99*count + vote in fixed point: a leaky integrator = exponential momentum over sign evidence. Sign-descent-with-momentum provably converges where plain sign descent fails (Safaryan & Richtarik). Fable's integer leak was confounded, never cleanly tried; this lab has never run any leak.
- **train.py:** new flag `--leak 0.99` on Layered (fixed-point counters)
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.01..-0.05; theory-backed and cheap.
- **status:** queued
```mill
id: MILL-209
mode: process
run: --arm layered_half --rope --leak 0.99
```

### MILL-210 · Fractional leak lambda=0.98
- **source:** direct-trainer study 2026-11-11 C3 (dose variant)
- **mechanism:** Stronger-forgetting sibling of MILL-209.
- **train.py:** new flag `--leak 0.98`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Dose bracket for 209; the study names 0.98 in its experiment sketch.
- **status:** queued
```mill
id: MILL-210
mode: process
run: --arm layered_half --rope --leak 0.98
```

### MILL-211 · Fractional leak lambda=0.95
- **source:** direct-trainer study 2026-11-11 C3 (dose variant)
- **mechanism:** Strongest-forgetting sibling; effective evidence horizon ~20 steps.
- **train.py:** new flag `--leak 0.95`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Dose bracket; if the leak family has a peak it is likely at 0.98-0.99, this bounds the curve.
- **status:** queued
```mill
id: MILL-211
mode: process
run: --arm layered_half --rope --leak 0.95
```

### MILL-212 · Integer leak every 50 steps (clean retest of Fable's variant)
- **source:** direct-trainer study 2026-11-11 C3 (Fable variant, de-confounded)
- **mechanism:** Every 50 steps every counter moves one step toward 0 — Fable's exact leak form, but run clean (solo machine, equal steps, held metric) instead of under CPU contention.
- **train.py:** new flag `--ileak 50` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.00..-0.03; a provenance retest — the idea was never refuted, only never fairly run.
- **status:** queued
```mill
id: MILL-212
mode: process
run: --arm layered_half --rope --ileak 50
```

### MILL-213 · Integer leak every 10 steps
- **source:** direct-trainer study 2026-11-11 C3 (dose variant)
- **mechanism:** Faster-forgetting sibling of MILL-212.
- **train.py:** new flag `--ileak 10`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Dose bracket for 212.
- **status:** queued
```mill
id: MILL-213
mode: process
run: --arm layered_half --rope --ileak 10
```

### MILL-214 · Votes-must-agree (clean retest of Fable's variant)
- **source:** direct-trainer study 2026-11-11 §1.2/§2 (Fable variant, de-confounded)
- **mechanism:** A weight's vote counts only if it matches last step's pull for that weight (the `agree` variant). Fable measured it worse (4.28-4.38 band) on shared-CPU runs its own README calls not a clean comparison; the lab's discipline exists to re-ask exactly such questions.
- **train.py:** new flag `--agree` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.01..+0.02; expected near-flat — the value is retiring or vindicating a confounded verdict with a clean number.
- **status:** queued
```mill
id: MILL-214
mode: process
run: --arm layered_half --rope --agree
```

### MILL-215 · Thrash freezing: freeze after 3 flips in a window
- **source:** direct-trainer study 2026-11-11 C4 / A7 (Nagel et al.)
- **mechanism:** One extra int8 per weight counts flips; a weight flipping >=3 times inside a trailing window freezes at its modal value for the rest of the run. Oscillation around a threshold is THE documented pathology of low-bit training; freezing converts wasted flips into stability.
- **train.py:** new flag `--freeze 3` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.01..-0.04, plus a diagnostic the lab has never had: the per-weight flip-count distribution (logged at trial).
- **status:** queued
```mill
id: MILL-215
mode: process
run: --arm layered_half --rope --freeze 3
```

### MILL-216 · Thrash freezing: freeze after 5 flips
- **source:** direct-trainer study 2026-11-11 C4 (dose variant)
- **mechanism:** Gentler sibling of MILL-215.
- **train.py:** new flag `--freeze 5`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Dose bracket for 215.
- **status:** queued
```mill
id: MILL-216
mode: process
run: --arm layered_half --rope --freeze 5
```

### MILL-217 · Thrash freezing: freeze after 8 flips
- **source:** direct-trainer study 2026-11-11 C4 (dose variant)
- **mechanism:** Gentlest sibling; only the worst oscillators freeze.
- **train.py:** new flag `--freeze 8`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Dose bracket; 215-217 together price the oscillation pathology at this scale.
- **status:** queued
```mill
id: MILL-217
mode: process
run: --arm layered_half --rope --freeze 8
```

### MILL-218 · Modal readout, last 5 checkpoints (discrete EMA)
- **source:** direct-trainer study 2026-11-11 B5
- **mechanism:** Save the ternary state every N steps; at the end, read out the per-weight MODAL (majority) state across the last 5 saves instead of the final state. The discrete analogue of Fable's running-mean readout, which a vote-trained net otherwise cannot take. Readout-only: the same run also reports its final-state loss, so the probe measures the readout delta directly.
- **train.py:** new flag `--modal 5` (eval-side, Layered)
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.005..-0.03 for free (no training change, ~zero cost); the cheapest expected value in the pool after the shape entries.
- **status:** queued
```mill
id: MILL-218
mode: process
run: --arm layered_half --rope --modal 5
```

### MILL-219 · Modal readout, last 9 checkpoints
- **source:** direct-trainer study 2026-11-11 B5 (dose variant)
- **mechanism:** Longer-window sibling of MILL-218.
- **train.py:** new flag `--modal 9`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Dose bracket for 218.
- **status:** queued
```mill
id: MILL-219
mode: process
run: --arm layered_half --rope --modal 9
```

### MILL-220 · Hybrid phases: votes 70% -> STE 30%
- **source:** direct-trainer study 2026-11-11 C5
- **mechanism:** Votes from random init for the first 70% of steps (cheap state, big structural moves), then materialise latent weights at t*scale and finish with STE at low rate. Votes' weakness is fine convergence; STE's is cost and early oscillation — the phases attack different regimes.
- **train.py:** new flag `--hybrid 0.7:ste` (trainer hand-off in train.py)
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.02..-0.06 vs both pure arms is the win condition; the study is explicit that a hybrid must beat BOTH parents or it is just a compromise.
- **status:** queued
```mill
id: MILL-220
mode: process
run: --arm layered_half --rope --hybrid 0.7:ste
```

### MILL-221 · Hybrid phases: votes 50% -> STE 50%
- **source:** direct-trainer study 2026-11-11 C5 (split variant)
- **mechanism:** Even-split sibling of MILL-220.
- **train.py:** new flag `--hybrid 0.5:ste`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Split bracket for 220.
- **status:** queued
```mill
id: MILL-221
mode: process
run: --arm layered_half --rope --hybrid 0.5:ste
```

### MILL-222 · Hybrid phases: STE 70% -> votes 30% (reverse control)
- **source:** direct-trainer study 2026-11-11 C5 (reverse order)
- **mechanism:** The reverse order as control: STE first, votes as the finisher. Expected worse (votes cannot fine-converge), included so the phase ORDER is measured, not assumed.
- **train.py:** new flag `--hybrid 0.7:votes`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** +0.00..+0.05 expected; a control that makes 220/221 interpretable.
- **status:** queued
```mill
id: MILL-222
mode: process
run: --arm layered_half --rope --hybrid 0.7:votes
```

### MILL-223 · Annealed stochastic flips (Metropolis), T: 1.0 -> 0.05
- **source:** direct-trainer study 2026-11-11 A1
- **mechanism:** Per weight, estimate the flip's loss change from the gradient already computed (dL ~ g*(w_new - w)*scale, free); flip with probability min(1, exp(-dL/T)), T annealed over the run. This is what Fable's v1 was reaching for — it flipped proportional to |g| with NO acceptance test and measured nothing learned; the acceptance test is the difference between noise and annealing.
- **train.py:** new trainer mode `--arm annealflip` (chassis-changing entry; name avoids the closed `anneal` arm)
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** High variance: -0.05..+0.05. The most principled repair in the study; its machinery must pay rent immediately or it dies at probe.
- **status:** queued
```mill
id: MILL-223
mode: process
run: --arm annealflip --rope --temp 1.0:0.05
```

### MILL-224 · Annealed stochastic flips, T: 0.3 -> 0.02
- **source:** direct-trainer study 2026-11-11 A1 (dose variant)
- **mechanism:** Colder sibling of MILL-223.
- **train.py:** --arm annealflip --rope --temp 0.3:0.02
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Dose bracket for 223.
- **status:** queued
```mill
id: MILL-224
mode: process
run: --arm annealflip --rope --temp 0.3:0.02
```

### MILL-225 · DisARM probability state (unbiased discrete estimator)
- **source:** direct-trainer study 2026-11-11 A2
- **mechanism:** Each weight carries two fp logits over {-1,0,+1}; weights are sampled each step and logits updated with the DisARM antithetic estimator (two forward passes with mirrored randomness) — an UNBIASED gradient for the discrete variables, fixing STE's bias. 8 B/weight of state: more than votes (1), less than STE (12).
- **train.py:** new trainer mode `--arm disarm` (chassis-changing entry; 2x step cost charged at equal minutes)
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Unknown: -0.03..+0.06 at equal minutes (its 2x pass cost is the whole ballgame). The strongest published alternative-estimator family, never tried for ternary LM pretraining.
- **status:** queued
```mill
id: MILL-225
mode: process
run: --arm disarm --rope
```

### MILL-226 · Accumulator dial: int8 residual (error feedback)
- **source:** direct-trainer study 2026-11-11 A3
- **mechanism:** Per weight, an int8 residual r: r += -lr*g each step; when r crosses +-scale the weight flips one step and the quantum is subtracted from r. Full magnitude evidence, integrated exactly, overshoot never discarded — the dial point between votes (1-bit evidence) and STE (fp32).
- **train.py:** new trainer mode `--arm resid8` (chassis-changing entry)
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.02..-0.06 vs votes; with 201 (2-bit) and STE (fp32) this maps the accumulator-precision curve nobody has measured.
- **status:** queued
```mill
id: MILL-226
mode: process
run: --arm resid8 --rope
```

### MILL-227 · Accumulator dial: fp16 residual
- **source:** direct-trainer study 2026-11-11 A3 (dial variant)
- **mechanism:** fp16-residual sibling of MILL-226 — one step below STE on the dial.
- **train.py:** new trainer mode `--arm resid16`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Should sit between 226 and STE; the pair prices how much accumulator precision is enough.
- **status:** queued
```mill
id: MILL-227
mode: process
run: --arm resid16 --rope
```

### MILL-228 · Measured greedy flips, Fisher-ranked, share 0.2%
- **source:** direct-trainer study 2026-11-11 A5 (pretraining-scale form)
- **mechanism:** _flip_read grown up: accumulate gradients over 4 batches, rank candidate flips by estimated loss change with a diagonal-Fisher curvature penalty, flip the top 0.2% at once, keep or undo by measured held-batch loss, halve the share on rejection. Flips are chosen by how much they should help AND kept only if they measurably did.
- **train.py:** new trainer mode `--arm fisherflip --share 0.002` (chassis-changing entry)
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Unknown at pretraining scale (its evidence is cell-scale); per-step cost is ~6 passes per round, charged at equal minutes.
- **status:** queued
```mill
id: MILL-228
mode: process
run: --arm fisherflip --rope --share 0.002
```

### MILL-229 · Measured greedy flips, Fisher-ranked, share 0.1%
- **source:** direct-trainer study 2026-11-11 A5 (dose variant)
- **mechanism:** Smaller-batch sibling of MILL-228.
- **train.py:** --arm fisherflip --rope --share 0.001
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Dose bracket for 228.
- **status:** queued
```mill
id: MILL-229
mode: process
run: --arm fisherflip --rope --share 0.001
```

### MILL-230 · Measured greedy flips, Fisher-ranked, share 0.5%
- **source:** direct-trainer study 2026-11-11 A5 (dose variant)
- **mechanism:** Larger-batch sibling of MILL-228.
- **train.py:** --arm fisherflip --rope --share 0.005
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Dose bracket for 228.
- **status:** queued
```mill
id: MILL-230
mode: process
run: --arm fisherflip --rope --share 0.005
```

### MILL-231 · Votes + measured verification of pending flips
- **source:** direct-trainer study 2026-11-11 C6
- **mechanism:** Votes run as the engine, but every N steps the weights nearest their flip threshold get their candidate flips ranked by measured delta-loss on a check batch, and only verified ones fire early. Votes never check a flip helped; flips never accumulate evidence — each covers the other's hole.
- **train.py:** new flag `--verify-flips 200` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.01..-0.04; sequenced after the C1/C2 family by the study — the mill's order already does that.
- **status:** queued
```mill
id: MILL-231
mode: process
run: --arm layered_half --rope --verify-flips 200
```

### MILL-232 · Gradient whitening before signing (vote-side Muon analogue)
- **source:** direct-trainer study 2026-11-11 B3
- **mechanism:** Whiten each layer's gradient field (per-layer second-moment normalisation in a rotated basis) before the vote is taken, so the counter integrates evidence in a basis where directions are balanced.
- **train.py:** new flag `--whiten` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Speculative: -0.02..+0.02. One arm, cheap, clearly labelled speculative in the study itself.
- **status:** queued
```mill
id: MILL-232
mode: process
run: --arm layered_half --rope --whiten
```

### MILL-233 · Low-rank FP side term, rank 4 (serving-format candidate)
- **source:** direct-trainer study 2026-11-11 B4
- **mechanism:** Every ternary layer gains a rank-4 fp side path (ternary + low-rank patch), ~+20% disk. Fable's recipe7 tests it as a training recipe; here it is judged as a candidate SERVING format for Muse's ternary specialists, by held loss per byte at trial.
- **train.py:** new flag `--lowrank 4` in BitLinear
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.02..-0.05 on loss; the trial verdict must be per-byte (it spends bytes to buy loss).
- **status:** queued
```mill
id: MILL-233
mode: process
run: --arm layered_half --rope --lowrank 4
```

### MILL-234 · Low-rank FP side term, rank 8
- **source:** direct-trainer study 2026-11-11 B4 (dose variant)
- **mechanism:** Wider-patch sibling of MILL-233.
- **train.py:** new flag `--lowrank 8`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Dose bracket for 233; per-byte judgement applies even harder.
- **status:** queued
```mill
id: MILL-234
mode: process
run: --arm layered_half --rope --lowrank 8
```


## C — Fable-trace transfers (recipe level)

### MILL-301 · Rounding ease-in for VOTE arms, first 25%
- **source:** Fable trace (via direct-trainer study §5 / FABLE-STUDY §3.3) (recipe transfer)
- **mechanism:** Fable's recipe search won with rounding-to-ternary eased in over the first half — for the STE way (3.9963 vs 4.0220). This lab's vote arms have always run EASE=1.0 from step 0: the transfer to votes was never tested. Ease over the first 25% here.
- **train.py:** new flag `--ease 0.25` (EASE schedule for vote arms)
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.01..-0.04; a one-flag change with a measured STE-side precedent.
- **status:** queued
```mill
id: MILL-301
mode: process
run: --arm layered_half --rope --ease 0.25
```

### MILL-302 · Rounding ease-in for VOTE arms, first 50%
- **source:** Fable trace (via direct-trainer study §5 / FABLE-STUDY §3.3) (dose variant)
- **mechanism:** Fable's exact fraction (first half) as the sibling point.
- **train.py:** new flag `--ease 0.5`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Dose bracket for 301.
- **status:** queued
```mill
id: MILL-302
mode: process
run: --arm layered_half --rope --ease 0.5
```

### MILL-303 · Rounding ease-in for plain votes, first 50%
- **source:** Fable trace (via direct-trainer study §5 / FABLE-STUDY §3.3) (arm variant)
- **mechanism:** The ease-in transfer applied to the plain (single-component) vote trainer, to see whether the effect needs the layered structure.
- **train.py:** new flag `--ease 0.5` on Direct
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Arm bracket for 301/302.
- **status:** queued
```mill
id: MILL-303
mode: process
run: --arm plain_half --rope --ease 0.5
```

### MILL-304 · Shared-parts AdamW lr 3e-3 for vote arms (recipe-matching)
- **source:** Fable trace (via direct-trainer study §5 / FABLE-STUDY §3.3) (study limit #2 repair)
- **mechanism:** The vote arms' non-ternary parts (embeddings, norms, scales) have always trained at Fable's Direct default lr 1e-3, while the recipe sweep showed 3e-3 is worth ~0.2 on the STE side. How much of the votes-vs-STE gap is recipe rather than mechanism was never separable; this entry prices the lr half of that question.
- **train.py:** new flag `--opt-lr 3e-3` (AdamW lr for the shared parts in Direct/Layered)
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.01..-0.05; high information value regardless of sign — it de-confounds every vote-arm comparison in the record.
- **status:** queued
```mill
id: MILL-304
mode: process
run: --arm layered_half --rope --opt-lr 3e-3
```

### MILL-305 · Shared-parts AdamW lr 3e-4 for vote arms
- **source:** Fable trace (via direct-trainer study §5 / FABLE-STUDY §3.3) (dose variant)
- **mechanism:** Colder sibling of MILL-304; brackets the shared-parts lr from below.
- **train.py:** new flag `--opt-lr 3e-4`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Dose bracket for 304.
- **status:** queued
```mill
id: MILL-305
mode: process
run: --arm layered_half --rope --opt-lr 3e-4
```

### MILL-306 · Polish phase: +25% steps at lr 3e-4 (STE chassis)
- **source:** Fable trace (via direct-trainer study §5 / FABLE-STUDY §3.3) (sleep-experiment transfer)
- **mechanism:** Fable's sleep experiment: plain continued reading at 3e-4 beat five fancier options (3.380 -> 3.190). As a mill entry: after the standard STE run, continue at 3e-4 for 25% more steps. Distinct from the closed layered cooldown — different chassis, constant low rate, ADDED steps rather than a decayed share of the same budget.
- **train.py:** new flag `--polish 0.25` on the STE trainer
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.01..-0.04 at +25% time (charged); per-minute it may still lose — the probe reports held only, the trial judges per-minute too.
- **status:** queued
```mill
id: MILL-306
mode: process
run: --arm ste_half --rope --polish 0.25
```


## D — Arnav's own directions, not yet closed

### MILL-401 · Three-component layered votes (7 levels)
- **source:** Arnav (IDEA-LOG / lab record) — the lab's own named next test
- **mechanism:** Layered votes with THREE counter/state component pairs per weight: installed value = t1+t2+t3 in {-3..3}, seven levels instead of five, each component with its own V=32 counter. The direct extension of the mechanism that produced the lab's best number; the study's ranked list and the half-control record both leave the component count itself untested.
- **train.py:** new flag `--comps 3` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.01..-0.05; if levels earn anything at equal size/steps (the half-control says the five-level form did NOT vs plain), this is where it would show.
- **status:** queued
```mill
id: MILL-401
mode: process
run: --arm layered_half --rope --comps 3
```

### MILL-402 · Three-component layered votes, V=16
- **source:** Arnav (IDEA-LOG / lab record) (dose variant)
- **mechanism:** MILL-401 with hotter counters (V=16): more components flip more readily; brackets the component-count x threshold interaction.
- **train.py:** new flag `--comps 3 --votes 16`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Dose bracket for 401.
- **status:** queued
```mill
id: MILL-402
mode: process
run: --arm layered_half --rope --comps 3 --votes 16
```

### MILL-403 · Per-component thresholds (t1 V=32, t2 V=16)
- **source:** Arnav (IDEA-LOG / lab record) (asymmetric form)
- **mechanism:** The two existing components get different thresholds: the first is the stable backbone, the second a fast correction layer. Asymmetry is untested — every run so far gave both components the same V.
- **train.py:** new flag `--comp-v 32,16` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.01..-0.04; a backbone+correction split is how multi-level quantizers usually earn their levels.
- **status:** queued
```mill
id: MILL-403
mode: process
run: --arm layered_half --rope --comp-v 32,16
```

### MILL-404 · Per-component thresholds (t1 V=16, t2 V=32)
- **source:** Arnav (IDEA-LOG / lab record) (reverse asymmetry)
- **mechanism:** Reverse assignment of MILL-403: fast backbone, stable correction. Included so the direction of the asymmetry is measured, not guessed.
- **train.py:** new flag `--comp-v 16,32`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Bracket for 403; expected weaker than 403 if the backbone story is right.
- **status:** queued
```mill
id: MILL-404
mode: process
run: --arm layered_half --rope --comp-v 16,32
```

### MILL-405 · One-component control via the structure flag (V=32)
- **source:** Arnav (IDEA-LOG / lab record) (structural control)
- **mechanism:** Layered with `--comps 1` is plain votes reached through the layered code path — a control proving the structure flag itself changes nothing when the count is 1.
- **train.py:** new flag `--comps 1` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Must land within noise of the plain_half+rope control (MILL-1901); if it doesn't, the code paths differ somewhere unrecorded and every layered comparison inherits the doubt.
- **status:** queued
```mill
id: MILL-405
mode: process
run: --arm layered_half --rope --comps 1
```

### MILL-406 · Failure-weighted window sampling (2x worst-decile)
- **source:** Arnav (IDEA-LOG / lab record) — 'train on measured failures' (round-2 record's named direction)
- **mechanism:** Periodically score training windows by current loss; oversample the worst decile 2x in the batch stream. The lab has only ever sampled uniformly; Arnav's weakness-targeting doctrine (dream on measured weak spots) applied to the data stream instead of the weights.
- **train.py:** new flag `--failweight 2` (sampler change in the training loop)
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** -0.01..-0.05 on held loss IF the held windows resemble the hard training windows; risk: distribution skew — the trial watches held_init-relative gain, not just final.
- **status:** queued
```mill
id: MILL-406
mode: process
run: --arm layered_half --rope --failweight 2
```

### MILL-407 · Failure-weighted window sampling (4x worst-decile)
- **source:** Arnav (IDEA-LOG / lab record) (dose variant)
- **mechanism:** Stronger-dose sibling of MILL-406.
- **train.py:** new flag `--failweight 4`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Dose bracket for 406; skew risk grows with dose.
- **status:** queued
```mill
id: MILL-407
mode: process
run: --arm layered_half --rope --failweight 4
```


## E — Systematic single-variable grids

### MILL-501 · Vote threshold V=4 (layered chassis)
- **source:** systematic grid: vote threshold
- **mechanism:** Flip threshold V=4 net votes on the layered trainer (chassis default 32). Lower V = hotter flips (more responsive, more thrash); higher V = colder (more stable, slower structure learning). One variable moved; everything else is the chassis.
- **train.py:** new flag `--votes N` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** The V curve is the vote mechanism's central dial and only its 32 point is measured. Expect a shallow U with the minimum somewhere in 12..64; each point is one probe.
- **status:** queued
```mill
id: MILL-501
mode: process
run: --arm layered_half --rope --votes 4
```

### MILL-502 · Vote threshold V=8 (layered chassis)
- **source:** systematic grid: vote threshold
- **mechanism:** Flip threshold V=8 net votes on the layered trainer (chassis default 32). Lower V = hotter flips (more responsive, more thrash); higher V = colder (more stable, slower structure learning). One variable moved; everything else is the chassis.
- **train.py:** new flag `--votes N` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** The V curve is the vote mechanism's central dial and only its 32 point is measured. Expect a shallow U with the minimum somewhere in 12..64; each point is one probe.
- **status:** queued
```mill
id: MILL-502
mode: process
run: --arm layered_half --rope --votes 8
```

### MILL-503 · Vote threshold V=12 (layered chassis)
- **source:** systematic grid: vote threshold
- **mechanism:** Flip threshold V=12 net votes on the layered trainer (chassis default 32). Lower V = hotter flips (more responsive, more thrash); higher V = colder (more stable, slower structure learning). One variable moved; everything else is the chassis.
- **train.py:** new flag `--votes N` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** The V curve is the vote mechanism's central dial and only its 32 point is measured. Expect a shallow U with the minimum somewhere in 12..64; each point is one probe.
- **status:** queued
```mill
id: MILL-503
mode: process
run: --arm layered_half --rope --votes 12
```

### MILL-504 · Vote threshold V=16 (layered chassis)
- **source:** systematic grid: vote threshold
- **mechanism:** Flip threshold V=16 net votes on the layered trainer (chassis default 32). Lower V = hotter flips (more responsive, more thrash); higher V = colder (more stable, slower structure learning). One variable moved; everything else is the chassis.
- **train.py:** new flag `--votes N` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** The V curve is the vote mechanism's central dial and only its 32 point is measured. Expect a shallow U with the minimum somewhere in 12..64; each point is one probe.
- **status:** queued
```mill
id: MILL-504
mode: process
run: --arm layered_half --rope --votes 16
```

### MILL-505 · Vote threshold V=24 (layered chassis)
- **source:** systematic grid: vote threshold
- **mechanism:** Flip threshold V=24 net votes on the layered trainer (chassis default 32). Lower V = hotter flips (more responsive, more thrash); higher V = colder (more stable, slower structure learning). One variable moved; everything else is the chassis.
- **train.py:** new flag `--votes N` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** The V curve is the vote mechanism's central dial and only its 32 point is measured. Expect a shallow U with the minimum somewhere in 12..64; each point is one probe.
- **status:** queued
```mill
id: MILL-505
mode: process
run: --arm layered_half --rope --votes 24
```

### MILL-506 · Vote threshold V=48 (layered chassis)
- **source:** systematic grid: vote threshold
- **mechanism:** Flip threshold V=48 net votes on the layered trainer (chassis default 32). Lower V = hotter flips (more responsive, more thrash); higher V = colder (more stable, slower structure learning). One variable moved; everything else is the chassis.
- **train.py:** new flag `--votes N` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** The V curve is the vote mechanism's central dial and only its 32 point is measured. Expect a shallow U with the minimum somewhere in 12..64; each point is one probe.
- **status:** queued
```mill
id: MILL-506
mode: process
run: --arm layered_half --rope --votes 48
```

### MILL-507 · Vote threshold V=64 (layered chassis)
- **source:** systematic grid: vote threshold
- **mechanism:** Flip threshold V=64 net votes on the layered trainer (chassis default 32). Lower V = hotter flips (more responsive, more thrash); higher V = colder (more stable, slower structure learning). One variable moved; everything else is the chassis.
- **train.py:** new flag `--votes N` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** The V curve is the vote mechanism's central dial and only its 32 point is measured. Expect a shallow U with the minimum somewhere in 12..64; each point is one probe.
- **status:** queued
```mill
id: MILL-507
mode: process
run: --arm layered_half --rope --votes 64
```

### MILL-508 · Vote threshold V=96 (layered chassis)
- **source:** systematic grid: vote threshold
- **mechanism:** Flip threshold V=96 net votes on the layered trainer (chassis default 32). Lower V = hotter flips (more responsive, more thrash); higher V = colder (more stable, slower structure learning). One variable moved; everything else is the chassis.
- **train.py:** new flag `--votes N` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** The V curve is the vote mechanism's central dial and only its 32 point is measured. Expect a shallow U with the minimum somewhere in 12..64; each point is one probe.
- **status:** queued
```mill
id: MILL-508
mode: process
run: --arm layered_half --rope --votes 96
```

### MILL-509 · Vote threshold V=128 (layered chassis)
- **source:** systematic grid: vote threshold
- **mechanism:** Flip threshold V=128 net votes on the layered trainer (chassis default 32). Lower V = hotter flips (more responsive, more thrash); higher V = colder (more stable, slower structure learning). One variable moved; everything else is the chassis.
- **train.py:** new flag `--votes N` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** The V curve is the vote mechanism's central dial and only its 32 point is measured. Expect a shallow U with the minimum somewhere in 12..64; each point is one probe.
- **status:** queued
```mill
id: MILL-509
mode: process
run: --arm layered_half --rope --votes 128
```

### MILL-511 · Vote threshold V=8 (plain votes)
- **source:** systematic grid: vote threshold x arm
- **mechanism:** Same dial as the MILL-50x grid on the single-component Direct trainer: tests whether the optimal V depends on the component structure.
- **train.py:** new flag `--votes N` on Direct
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** If the plain and layered optima differ, threshold is a per-structure setting, not a universal constant.
- **status:** queued
```mill
id: MILL-511
mode: process
run: --arm plain_half --rope --votes 8
```

### MILL-512 · Vote threshold V=16 (plain votes)
- **source:** systematic grid: vote threshold x arm
- **mechanism:** Same dial as the MILL-50x grid on the single-component Direct trainer: tests whether the optimal V depends on the component structure.
- **train.py:** new flag `--votes N` on Direct
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** If the plain and layered optima differ, threshold is a per-structure setting, not a universal constant.
- **status:** queued
```mill
id: MILL-512
mode: process
run: --arm plain_half --rope --votes 16
```

### MILL-513 · Vote threshold V=24 (plain votes)
- **source:** systematic grid: vote threshold x arm
- **mechanism:** Same dial as the MILL-50x grid on the single-component Direct trainer: tests whether the optimal V depends on the component structure.
- **train.py:** new flag `--votes N` on Direct
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** If the plain and layered optima differ, threshold is a per-structure setting, not a universal constant.
- **status:** queued
```mill
id: MILL-513
mode: process
run: --arm plain_half --rope --votes 24
```

### MILL-514 · Vote threshold V=48 (plain votes)
- **source:** systematic grid: vote threshold x arm
- **mechanism:** Same dial as the MILL-50x grid on the single-component Direct trainer: tests whether the optimal V depends on the component structure.
- **train.py:** new flag `--votes N` on Direct
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** If the plain and layered optima differ, threshold is a per-structure setting, not a universal constant.
- **status:** queued
```mill
id: MILL-514
mode: process
run: --arm plain_half --rope --votes 48
```

### MILL-515 · Vote threshold V=64 (plain votes)
- **source:** systematic grid: vote threshold x arm
- **mechanism:** Same dial as the MILL-50x grid on the single-component Direct trainer: tests whether the optimal V depends on the component structure.
- **train.py:** new flag `--votes N` on Direct
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** If the plain and layered optima differ, threshold is a per-structure setting, not a universal constant.
- **status:** queued
```mill
id: MILL-515
mode: process
run: --arm plain_half --rope --votes 64
```

### MILL-601 · Strong-gate quantile q=0.0 (layered)
- **source:** systematic grid: gate quantile
- **mechanism:** The layered gate counts a vote only when |g| clears the layer's q-quantile (chassis default 0.5, Fable's stronger-half rule). q=0.0 is the gate REMOVED — every gradient votes; doubles as the repair control for the plain-vote comparison (plain's missing gate was a named confound in the study).
- **train.py:** new flag `--gate-q Q` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** q=0.0 is the highest-information point (it closes a named confound). The rest trace whether stronger-half is the right bar.
- **status:** queued
```mill
id: MILL-601
mode: process
run: --arm layered_half --rope --gate-q 0.0
```

### MILL-602 · Strong-gate quantile q=0.25 (layered)
- **source:** systematic grid: gate quantile
- **mechanism:** The layered gate counts a vote only when |g| clears the layer's q-quantile (chassis default 0.5, Fable's stronger-half rule). q=0.25 moves the evidence bar for what counts as a vote.
- **train.py:** new flag `--gate-q Q` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** q=0.0 is the highest-information point (it closes a named confound). The rest trace whether stronger-half is the right bar.
- **status:** queued
```mill
id: MILL-602
mode: process
run: --arm layered_half --rope --gate-q 0.25
```

### MILL-603 · Strong-gate quantile q=0.6 (layered)
- **source:** systematic grid: gate quantile
- **mechanism:** The layered gate counts a vote only when |g| clears the layer's q-quantile (chassis default 0.5, Fable's stronger-half rule). q=0.6 moves the evidence bar for what counts as a vote.
- **train.py:** new flag `--gate-q Q` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** q=0.0 is the highest-information point (it closes a named confound). The rest trace whether stronger-half is the right bar.
- **status:** queued
```mill
id: MILL-603
mode: process
run: --arm layered_half --rope --gate-q 0.6
```

### MILL-604 · Strong-gate quantile q=0.7 (layered)
- **source:** systematic grid: gate quantile
- **mechanism:** The layered gate counts a vote only when |g| clears the layer's q-quantile (chassis default 0.5, Fable's stronger-half rule). q=0.7 moves the evidence bar for what counts as a vote.
- **train.py:** new flag `--gate-q Q` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** q=0.0 is the highest-information point (it closes a named confound). The rest trace whether stronger-half is the right bar.
- **status:** queued
```mill
id: MILL-604
mode: process
run: --arm layered_half --rope --gate-q 0.7
```

### MILL-605 · Strong-gate quantile q=0.8 (layered)
- **source:** systematic grid: gate quantile
- **mechanism:** The layered gate counts a vote only when |g| clears the layer's q-quantile (chassis default 0.5, Fable's stronger-half rule). q=0.8 moves the evidence bar for what counts as a vote.
- **train.py:** new flag `--gate-q Q` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** q=0.0 is the highest-information point (it closes a named confound). The rest trace whether stronger-half is the right bar.
- **status:** queued
```mill
id: MILL-605
mode: process
run: --arm layered_half --rope --gate-q 0.8
```

### MILL-606 · Strong-gate quantile q=0.9 (layered)
- **source:** systematic grid: gate quantile
- **mechanism:** The layered gate counts a vote only when |g| clears the layer's q-quantile (chassis default 0.5, Fable's stronger-half rule). q=0.9 moves the evidence bar for what counts as a vote.
- **train.py:** new flag `--gate-q Q` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** q=0.0 is the highest-information point (it closes a named confound). The rest trace whether stronger-half is the right bar.
- **status:** queued
```mill
id: MILL-606
mode: process
run: --arm layered_half --rope --gate-q 0.9
```

### MILL-611 · Strong-gate quantile q=0.25 (plain votes, gate added)
- **source:** systematic grid: gate x arm
- **mechanism:** Give the Direct trainer the layered gate at q=0.25: isolates the gate's contribution from the component structure's.
- **train.py:** new flag `--gate-q Q` on Direct
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** With MILL-601 (q=0 on layered) this completes the 2x2 of {gate, structure}.
- **status:** queued
```mill
id: MILL-611
mode: process
run: --arm plain_half --rope --gate-q 0.25
```

### MILL-612 · Strong-gate quantile q=0.75 (plain votes, gate added)
- **source:** systematic grid: gate x arm
- **mechanism:** Give the Direct trainer the layered gate at q=0.75: isolates the gate's contribution from the component structure's.
- **train.py:** new flag `--gate-q Q` on Direct
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** With MILL-601 (q=0 on layered) this completes the 2x2 of {gate, structure}.
- **status:** queued
```mill
id: MILL-612
mode: process
run: --arm plain_half --rope --gate-q 0.75
```

### MILL-621 · Flip rule: counter
- **source:** systematic grid: flip arbitration
- **mechanism:** Arbitration when several components want to flip at once: when both components sit at threshold, flip only the one whose counter has the larger overshoot (chassis flips both — this spends one flip where the chassis spends two). The chassis's both-flip default has never been varied.
- **train.py:** new flag `--flip-rule counter` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Small effects expected (-0.01..-0.03); arbitration is a real degree of freedom nobody has priced.
- **status:** queued
```mill
id: MILL-621
mode: process
run: --arm layered_half --rope --flip-rule counter
```

### MILL-622 · Flip rule: t1-first
- **source:** systematic grid: flip arbitration
- **mechanism:** Arbitration when several components want to flip at once: component 1 has flip priority; component 2 flips only when component 1 is not at threshold (serialises the levels). The chassis's both-flip default has never been varied.
- **train.py:** new flag `--flip-rule t1-first` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Small effects expected (-0.01..-0.03); arbitration is a real degree of freedom nobody has priced.
- **status:** queued
```mill
id: MILL-622
mode: process
run: --arm layered_half --rope --flip-rule t1-first
```

### MILL-623 · Flip rule: sign-agree
- **source:** systematic grid: flip arbitration
- **mechanism:** Arbitration when several components want to flip at once: a component flips only if the other's current gradient pull agrees in sign (cross-component agreement, distinct from MILL-214's time-agreement). The chassis's both-flip default has never been varied.
- **train.py:** new flag `--flip-rule sign-agree` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Small effects expected (-0.01..-0.03); arbitration is a real degree of freedom nobody has priced.
- **status:** queued
```mill
id: MILL-623
mode: process
run: --arm layered_half --rope --flip-rule sign-agree
```

### MILL-624 · Flip rule: alternate
- **source:** systematic grid: flip arbitration
- **mechanism:** Arbitration when several components want to flip at once: components alternate flip eligibility step by step (round-robin), halving simultaneous-flip noise. The chassis's both-flip default has never been varied.
- **train.py:** new flag `--flip-rule alternate` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Small effects expected (-0.01..-0.03); arbitration is a real degree of freedom nobody has priced.
- **status:** queued
```mill
id: MILL-624
mode: process
run: --arm layered_half --rope --flip-rule alternate
```

### MILL-631 · Counter clamp: 2xV (int16 counters)
- **source:** systematic grid: counter policy
- **mechanism:** Counter policy on int16 counters with V=32: counters clamp at +-2V: evidence saturates at twice the flip threshold, bounding stale conviction.
- **train.py:** new flag `--clamp 2` on Layered (requires int16 counters)
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Counter policy is unexamined in every record the lab owns; any of the three could plausibly matter at the +-0.02 level.
- **status:** queued
```mill
id: MILL-631
mode: process
run: --arm layered_half --rope --clamp 2
```

### MILL-632 · Counter clamp: nonexV (int16 counters)
- **source:** systematic grid: counter policy
- **mechanism:** Counter policy on int16 counters with V=32: no clamp and no reset on flip: counters free-run (the carry failure mode was about the STATE value, not the counter; this isolates counter policy).
- **train.py:** new flag `--clamp none` on Layered (requires int16 counters)
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Counter policy is unexamined in every record the lab owns; any of the three could plausibly matter at the +-0.02 level.
- **status:** queued
```mill
id: MILL-632
mode: process
run: --arm layered_half --rope --clamp none
```

### MILL-633 · Counter clamp: 0.5xV (int16 counters)
- **source:** systematic grid: counter policy
- **mechanism:** Counter policy on int16 counters with V=32: counters clamp at +-V/2: sub-threshold saturation — a weight can never be more than half-convinced; maximally forgetful.
- **train.py:** new flag `--clamp 0.5` on Layered (requires int16 counters)
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Counter policy is unexamined in every record the lab owns; any of the three could plausibly matter at the +-0.02 level.
- **status:** queued
```mill
id: MILL-633
mode: process
run: --arm layered_half --rope --clamp 0.5
```

### MILL-641 · Vote threshold V=128 with int16 counters
- **source:** systematic grid: evidence width
- **mechanism:** V=128 needs the int16 counter width to be meaningful (at V=32 the int8 range already binds). Tests whether much colder flips help once the counter can hold the evidence.
- **train.py:** new flag `--votes N` (int16 counters) on Layered
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Extends the MILL-50x curve into the cold tail; expected worse than the U's minimum — the point is bounding the curve.
- **status:** queued
```mill
id: MILL-641
mode: process
run: --arm layered_half --rope --votes 128
```

### MILL-642 · Vote threshold V=256 with int16 counters
- **source:** systematic grid: evidence width
- **mechanism:** V=256 needs the int16 counter width to be meaningful (at V=32 the int8 range already binds). Tests whether much colder flips help once the counter can hold the evidence.
- **train.py:** new flag `--votes N` (int16 counters) on Layered
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Extends the MILL-50x curve into the cold tail; expected worse than the U's minimum — the point is bounding the curve.
- **status:** queued
```mill
id: MILL-642
mode: process
run: --arm layered_half --rope --votes 256
```

### MILL-651 · Interaction point: V=16, gate q=0.75
- **source:** systematic grid: two-variable corners
- **mechanism:** Corner of the threshold x gate grid (V=16, q=0.75): the two dials both control flip economics, so their interaction is the first two-variable question worth asking after the single-variable curves land.
- **train.py:** new flags `--votes N --gate-q Q` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Read only against the single-variable points; a corner beating BOTH parents' curves is a genuine interaction, anything less is arithmetic.
- **status:** queued
```mill
id: MILL-651
mode: process
run: --arm layered_half --rope --votes 16 --gate-q 0.75
```

### MILL-652 · Interaction point: V=64, gate q=0.25
- **source:** systematic grid: two-variable corners
- **mechanism:** Corner of the threshold x gate grid (V=64, q=0.25): the two dials both control flip economics, so their interaction is the first two-variable question worth asking after the single-variable curves land.
- **train.py:** new flags `--votes N --gate-q Q` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Read only against the single-variable points; a corner beating BOTH parents' curves is a genuine interaction, anything less is arithmetic.
- **status:** queued
```mill
id: MILL-652
mode: process
run: --arm layered_half --rope --votes 64 --gate-q 0.25
```

### MILL-653 · Interaction point: V=16, gate q=0.25
- **source:** systematic grid: two-variable corners
- **mechanism:** Corner of the threshold x gate grid (V=16, q=0.25): the two dials both control flip economics, so their interaction is the first two-variable question worth asking after the single-variable curves land.
- **train.py:** new flags `--votes N --gate-q Q` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Read only against the single-variable points; a corner beating BOTH parents' curves is a genuine interaction, anything less is arithmetic.
- **status:** queued
```mill
id: MILL-653
mode: process
run: --arm layered_half --rope --votes 16 --gate-q 0.25
```

### MILL-654 · Interaction point: V=64, gate q=0.75
- **source:** systematic grid: two-variable corners
- **mechanism:** Corner of the threshold x gate grid (V=64, q=0.75): the two dials both control flip economics, so their interaction is the first two-variable question worth asking after the single-variable curves land.
- **train.py:** new flags `--votes N --gate-q Q` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Read only against the single-variable points; a corner beating BOTH parents' curves is a genuine interaction, anything less is arithmetic.
- **status:** queued
```mill
id: MILL-654
mode: process
run: --arm layered_half --rope --votes 64 --gate-q 0.75
```

### MILL-701 · Scale granularity: group128
- **source:** systematic grid: scale granularity
- **mechanism:** per-128-weight-group scales: the coarse end of the granularity curve. With MILL-107 (channel) and MILL-108 (group64) this completes the granularity curve.
- **train.py:** new flag `--scale-gran group128`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** The curve's shape (where payoff saturates) is the deliverable; boundary is the cost-engineered point.
- **status:** queued
```mill
id: MILL-701
mode: process
run: --arm layered_half --rope --scale-gran group128
```

### MILL-702 · Scale granularity: group32
- **source:** systematic grid: scale granularity
- **mechanism:** per-32-weight-group scales: finer than channel-count parity for the 192-wide rows. With MILL-107 (channel) and MILL-108 (group64) this completes the granularity curve.
- **train.py:** new flag `--scale-gran group32`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** The curve's shape (where payoff saturates) is the deliverable; boundary is the cost-engineered point.
- **status:** queued
```mill
id: MILL-702
mode: process
run: --arm layered_half --rope --scale-gran group32
```

### MILL-703 · Scale granularity: boundary
- **source:** systematic grid: scale granularity
- **mechanism:** per-channel scales ONLY on the boundary projections (qkv, attention out, FFN down) where the report says activation outliers live; per-tensor elsewhere. With MILL-107 (channel) and MILL-108 (group64) this completes the granularity curve.
- **train.py:** new flag `--scale-gran boundary`
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** The curve's shape (where payoff saturates) is the deliverable; boundary is the cost-engineered point.
- **status:** queued
```mill
id: MILL-703
mode: process
run: --arm layered_half --rope --scale-gran boundary
```

### MILL-801 · Norm family: rms
- **source:** systematic grid: norm placement/type
- **mechanism:** RMSNorm everywhere LayerNorm sits now (no mean-centering, no bias): one less reduction per norm, and the form Qwen/Llama standardised. Norms are FP and cheap; placement interacts with quant because the norms set the activation distribution the absmax quantizer sees.
- **train.py:** new flag `--norm rms` in Tiny/Block
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** rms ~flat expected (a cost probe); prepost/post are placement controls; none is expected worse (+0.03..+0.15) and bounds how much the norms earn.
- **status:** queued
```mill
id: MILL-801
mode: process
run: --arm layered_half --rope --norm rms
```

### MILL-802 · Norm family: prepost
- **source:** systematic grid: norm placement/type
- **mechanism:** post-norms added after each sublayer output (pre+post sandwich): bounds the residual stream's growth at the cost of the classic post-norm warmup sensitivity. Norms are FP and cheap; placement interacts with quant because the norms set the activation distribution the absmax quantizer sees.
- **train.py:** new flag `--norm prepost` in Tiny/Block
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** rms ~flat expected (a cost probe); prepost/post are placement controls; none is expected worse (+0.03..+0.15) and bounds how much the norms earn.
- **status:** queued
```mill
id: MILL-802
mode: process
run: --arm layered_half --rope --norm prepost
```

### MILL-803 · Norm family: post
- **source:** systematic grid: norm placement/type
- **mechanism:** pure post-norm (norms move after the residual adds): the original Transformer placement, as a control for the pre-norm default. Norms are FP and cheap; placement interacts with quant because the norms set the activation distribution the absmax quantizer sees.
- **train.py:** new flag `--norm post` in Tiny/Block
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** rms ~flat expected (a cost probe); prepost/post are placement controls; none is expected worse (+0.03..+0.15) and bounds how much the norms earn.
- **status:** queued
```mill
id: MILL-803
mode: process
run: --arm layered_half --rope --norm post
```

### MILL-804 · Norm family: none
- **source:** systematic grid: norm placement/type
- **mechanism:** no norms at all: the extreme Falcon-E direction (MILL-128 removes only the FFN pre-norm; this removes n1, n2 and the final norm). Norms are FP and cheap; placement interacts with quant because the norms set the activation distribution the absmax quantizer sees.
- **train.py:** new flag `--norm none` in Tiny/Block
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** rms ~flat expected (a cost probe); prepost/post are placement controls; none is expected worse (+0.03..+0.15) and bounds how much the norms earn.
- **status:** queued
```mill
id: MILL-804
mode: process
run: --arm layered_half --rope --norm none
```

### MILL-901 · Attention variant: GQA 2 KV heads
- **source:** systematic grid: attention family
- **mechanism:** 4 query heads share 2 KV heads: halves the K/V projection width (ternary weights drop ~8%); tests whether K/V need full head count at this scale.
- **train.py:** new flag `--gqa N` in Block/Tiny
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Mostly ~flat priors at ctx 256; RoPE base is the live one (the base was inherited, never tuned to this ctx).
- **status:** queued
```mill
id: MILL-901
mode: process
run: --arm layered_half --rope --gqa 2
```

### MILL-902 · Attention variant: MQA 1 KV head
- **source:** systematic grid: attention family
- **mechanism:** all query heads share one KV head: the aggressive end of the GQA dial.
- **train.py:** new flag `--gqa N` in Block/Tiny
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Mostly ~flat priors at ctx 256; RoPE base is the live one (the base was inherited, never tuned to this ctx).
- **status:** queued
```mill
id: MILL-902
mode: process
run: --arm layered_half --rope --gqa 1
```

### MILL-903 · Attention variant: 2 heads
- **source:** systematic grid: attention family
- **mechanism:** head count 4 -> 2 at fixed dim (head dim 48 -> 96): fewer, wider heads.
- **train.py:** new flag `--heads N` in Block/Tiny
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Mostly ~flat priors at ctx 256; RoPE base is the live one (the base was inherited, never tuned to this ctx).
- **status:** queued
```mill
id: MILL-903
mode: process
run: --arm layered_half --rope --heads 2
```

### MILL-904 · Attention variant: 8 heads
- **source:** systematic grid: attention family
- **mechanism:** head count 4 -> 8 (head dim 24 -> 12): more, narrower heads; RoPE pair count shrinks.
- **train.py:** new flag `--heads N` in Block/Tiny
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Mostly ~flat priors at ctx 256; RoPE base is the live one (the base was inherited, never tuned to this ctx).
- **status:** queued
```mill
id: MILL-904
mode: process
run: --arm layered_half --rope --heads 8
```

### MILL-905 · Attention variant: RoPE base 500
- **source:** systematic grid: attention family
- **mechanism:** rotation base 10000 -> 500: positions rotate much faster; at ctx 256 the long-range angles barely exist at base 10000.
- **train.py:** new flag `--rope-base N` in Block/Tiny
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Mostly ~flat priors at ctx 256; RoPE base is the live one (the base was inherited, never tuned to this ctx).
- **status:** queued
```mill
id: MILL-905
mode: process
run: --arm layered_half --rope --rope-base 500
```

### MILL-906 · Attention variant: RoPE base 50000
- **source:** systematic grid: attention family
- **mechanism:** rotation base 10000 -> 50000: slower rotation, positions more alike.
- **train.py:** new flag `--rope-base N` in Block/Tiny
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Mostly ~flat priors at ctx 256; RoPE base is the live one (the base was inherited, never tuned to this ctx).
- **status:** queued
```mill
id: MILL-906
mode: process
run: --arm layered_half --rope --rope-base 50000
```

### MILL-1001 · FFN variant: ReLU squared
- **source:** systematic grid: FFN family
- **mechanism:** ReLU^2 in place of GELU — the activation the ORIGINAL BitNet chose (squared ReLU sharpens selectivity and its exact zeros feed the down-projection's sparsity); the lab has run GELU throughout.
- **train.py:** new flag `--ffn` in Block
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** relu2 has the strongest prior here (it is the recipe's own original choice, never A/B'd in this lab).
- **status:** queued
```mill
id: MILL-1001
mode: process
run: --arm layered_half --rope --ffn relu2
```

### MILL-1002 · FFN variant: ReLU
- **source:** systematic grid: FFN family
- **mechanism:** plain ReLU: the sparsity-maximal cheap point, as GELU's control.
- **train.py:** new flag `--ffn` in Block
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** relu2 has the strongest prior here (it is the recipe's own original choice, never A/B'd in this lab).
- **status:** queued
```mill
id: MILL-1002
mode: process
run: --arm layered_half --rope --ffn relu
```

### MILL-1003 · FFN variant: FFN width x2.67
- **source:** systematic grid: FFN family
- **mechanism:** inner width 4x -> 2.67x dim (Llama-style ratio): moves ~15% of weights from FFN to nowhere (total drops) — a shape point reached through the FFN rather than the block count.
- **train.py:** new flag `--ffn-width` in Block
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** relu2 has the strongest prior here (it is the recipe's own original choice, never A/B'd in this lab).
- **status:** queued
```mill
id: MILL-1003
mode: process
run: --arm layered_half --rope --ffn-width 2.67
```

### MILL-1004 · FFN variant: FFN width x6
- **source:** systematic grid: FFN family
- **mechanism:** inner width 4x -> 6x: FFN-heavier shape at +~30% weights.
- **train.py:** new flag `--ffn-width` in Block
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** relu2 has the strongest prior here (it is the recipe's own original choice, never A/B'd in this lab).
- **status:** queued
```mill
id: MILL-1004
mode: process
run: --arm layered_half --rope --ffn-width 6
```

### MILL-1011 · Quant function: absmax weight quant
- **source:** systematic grid: quantizer choice
- **mechanism:** weights quantized by absmax/127-style scaling to {-1,0,1} thresholds instead of absmean: ParetoQ's warning that the quant function matters as much as the bit-width.
- **train.py:** new flag `--wquant` in BitLinear
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** ParetoQ effect sizes suggest +-0.02..0.05 is available in this family; learn-scale interacts with the vote install scale and needs care at trial.
- **status:** queued
```mill
id: MILL-1011
mode: process
run: --arm layered_half --rope --wquant absmax
```

### MILL-1012 · Quant function: balanced activation grid
- **source:** systematic grid: quantizer choice
- **mechanism:** activation quantizer uses a balanced (median-centred) grid instead of absmax: attacks the outlier-stretched grid from the centre.
- **train.py:** new flag `--agrid` in BitLinear
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** ParetoQ effect sizes suggest +-0.02..0.05 is available in this family; learn-scale interacts with the vote install scale and needs care at trial.
- **status:** queued
```mill
id: MILL-1012
mode: process
run: --arm layered_half --rope --agrid balanced
```

### MILL-1013 · Quant function: learnable per-layer scale
- **source:** systematic grid: quantizer choice
- **mechanism:** the BitLinear scale becomes a learned parameter (gradient-updated) instead of the absmean statistic.
- **train.py:** new flag `--learn-scale` in BitLinear
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** ParetoQ effect sizes suggest +-0.02..0.05 is available in this family; learn-scale interacts with the vote install scale and needs care at trial.
- **status:** queued
```mill
id: MILL-1013
mode: process
run: --arm layered_half --rope --learn-scale
```

### MILL-1021 · Init std 0.01
- **source:** systematic grid: initialisation
- **mechanism:** Weight init std 0.01 instead of the chassis's 0.02: init scale sets the early vote landscape (how many weights start near a flip boundary).
- **train.py:** new flag `--init-std S` in Tiny
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** ~flat priors; included because init is a free variable nobody has touched and vote dynamics are unusually init-sensitive.
- **status:** queued
```mill
id: MILL-1021
mode: process
run: --arm layered_half --rope --init-std 0.01
```

### MILL-1022 · Init std 0.05
- **source:** systematic grid: initialisation
- **mechanism:** Weight init std 0.05 instead of the chassis's 0.02: init scale sets the early vote landscape (how many weights start near a flip boundary).
- **train.py:** new flag `--init-std S` in Tiny
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** ~flat priors; included because init is a free variable nobody has touched and vote dynamics are unusually init-sensitive.
- **status:** queued
```mill
id: MILL-1022
mode: process
run: --arm layered_half --rope --init-std 0.05
```

### MILL-1301 · STE recipe: STE lr 1e-3
- **source:** systematic grid: STE chassis recipe
- **mechanism:** STE latent lr 1e-3 (below the 3e-3 default): the STE recipe point under the shared-parts setting. The STE chassis is the mill's reference gradient method; its recipe points are as unmeasured as the vote dials.
- **train.py:** new flag `--ste-lr` on the STE trainer
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Recipe points, +-0.03 priors; warmup points matter most at probe scale (budget share), lr points at trial scale.
- **status:** queued
```mill
id: MILL-1301
mode: process
run: --arm ste_half --rope --ste-lr 1e-3
```

### MILL-1302 · STE recipe: STE lr 6e-3
- **source:** systematic grid: STE chassis recipe
- **mechanism:** STE latent lr 6e-3: hotter than default. The STE chassis is the mill's reference gradient method; its recipe points are as unmeasured as the vote dials.
- **train.py:** new flag `--ste-lr` on the STE trainer
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Recipe points, +-0.03 priors; warmup points matter most at probe scale (budget share), lr points at trial scale.
- **status:** queued
```mill
id: MILL-1302
mode: process
run: --arm ste_half --rope --ste-lr 6e-3
```

### MILL-1303 · STE recipe: STE lr 1e-2
- **source:** systematic grid: STE chassis recipe
- **mechanism:** STE latent lr 1e-2: the hot end of the recipe dial. The STE chassis is the mill's reference gradient method; its recipe points are as unmeasured as the vote dials.
- **train.py:** new flag `--ste-lr` on the STE trainer
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Recipe points, +-0.03 priors; warmup points matter most at probe scale (budget share), lr points at trial scale.
- **status:** queued
```mill
id: MILL-1303
mode: process
run: --arm ste_half --rope --ste-lr 1e-2
```

### MILL-1304 · STE recipe: STE warmup 50 steps
- **source:** systematic grid: STE chassis recipe
- **mechanism:** warmup 200 -> 50 steps: at probe scale 200 warmup steps is a large share of the run. The STE chassis is the mill's reference gradient method; its recipe points are as unmeasured as the vote dials.
- **train.py:** new flag `--ste-warmup` on the STE trainer
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Recipe points, +-0.03 priors; warmup points matter most at probe scale (budget share), lr points at trial scale.
- **status:** queued
```mill
id: MILL-1304
mode: process
run: --arm ste_half --rope --ste-warmup 50
```

### MILL-1305 · STE recipe: STE warmup 400 steps
- **source:** systematic grid: STE chassis recipe
- **mechanism:** warmup 200 -> 400 steps: the other bracket. The STE chassis is the mill's reference gradient method; its recipe points are as unmeasured as the vote dials.
- **train.py:** new flag `--ste-warmup` on the STE trainer
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Recipe points, +-0.03 priors; warmup points matter most at probe scale (budget share), lr points at trial scale.
- **status:** queued
```mill
id: MILL-1305
mode: process
run: --arm ste_half --rope --ste-warmup 400
```

### MILL-1306 · STE recipe: STE weight decay 0
- **source:** systematic grid: STE chassis recipe
- **mechanism:** STE weight decay 0.01 -> 0: isolates WD's code-editing effect on the STE chassis. The STE chassis is the mill's reference gradient method; its recipe points are as unmeasured as the vote dials.
- **train.py:** new flag `--ste-wd` on the STE trainer
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Recipe points, +-0.03 priors; warmup points matter most at probe scale (budget share), lr points at trial scale.
- **status:** queued
```mill
id: MILL-1306
mode: process
run: --arm ste_half --rope --ste-wd 0
```

### MILL-1307 · STE recipe: STE weight decay 0.05
- **source:** systematic grid: STE chassis recipe
- **mechanism:** STE weight decay 0.01 -> 0.05: stronger code editing. The STE chassis is the mill's reference gradient method; its recipe points are as unmeasured as the vote dials.
- **train.py:** new flag `--ste-wd` on the STE trainer
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Recipe points, +-0.03 priors; warmup points matter most at probe scale (budget share), lr points at trial scale.
- **status:** queued
```mill
id: MILL-1307
mode: process
run: --arm ste_half --rope --ste-wd 0.05
```

### MILL-1308 · STE recipe: STE ease OFF (EASE=1 from step 0)
- **source:** systematic grid: STE chassis recipe
- **mechanism:** removes the STE rounding ease-in entirely: the control beneath MILL-301/302's vote-side transfer and Fable's STE-side finding. The STE chassis is the mill's reference gradient method; its recipe points are as unmeasured as the vote dials.
- **train.py:** new flag `--ease-off` on the STE trainer
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Recipe points, +-0.03 priors; warmup points matter most at probe scale (budget share), lr points at trial scale.
- **status:** queued
```mill
id: MILL-1308
mode: process
run: --arm ste_half --rope --ease-off
```

### MILL-1309 · STE recipe: STE ease-in 25%
- **source:** systematic grid: STE chassis recipe
- **mechanism:** STE ease-in compressed to the first 25%: Fable's winning fraction was 50%; this brackets it on the STE side. The STE chassis is the mill's reference gradient method; its recipe points are as unmeasured as the vote dials.
- **train.py:** new flag `--ease` on the STE trainer
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Recipe points, +-0.03 priors; warmup points matter most at probe scale (budget share), lr points at trial scale.
- **status:** queued
```mill
id: MILL-1309
mode: process
run: --arm ste_half --rope --ease 0.25
```

### MILL-1401 · four components (9 levels)
- **source:** systematic grid: component count
- **mechanism:** four component pairs: installed values in {-4..4}; extends MILL-401's component curve.
- **train.py:** new flag `--comps N` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Component-count curve points; read with MILL-401/402/405.
- **status:** queued
```mill
id: MILL-1401
mode: process
run: --arm layered_half --rope --comps 4
```

### MILL-1402 · five components at V=16 (11 levels)
- **source:** systematic grid: component count
- **mechanism:** five hotter components: the far end of the levels dial — if levels earn anything, the curve's shape shows by here.
- **train.py:** new flag `--comps N` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Component-count curve points; read with MILL-401/402/405.
- **status:** queued
```mill
id: MILL-1402
mode: process
run: --arm layered_half --rope --comps 5 --votes 16
```

### MILL-1101 · Shape: dim 256 x 1 blocks (0.79M ternary)
- **source:** systematic grid: shape (runnable now)
- **mechanism:** Shape point at fixed recipe: wider-shallower flagship: same weights, one block — the report's shape question in its purest form. Ternary weights ~786,432 vs the chassis's 884,736.
- **train.py:** RUNNABLE NOW: existing `--dim/--layers-n` flags only
- **mode:** sweep — same-chassis config variant; runs inside the shared-data sweep process (corpus loaded once)
- **prediction:** Shape is one of the report's top-5 tests and the cheapest to run. Wider-shallower has the better prior at fixed weights for quant (more parallel evidence per layer); the grid prices it.
- **status:** queued
```mill
id: MILL-1101
mode: sweep
run: --arm layered_half --rope --dim 256 --layers-n 1
```

### MILL-1102 · Shape: dim 288 x 1 blocks (1.00M ternary)
- **source:** systematic grid: shape (runnable now)
- **mechanism:** Shape point at fixed recipe: single block at ~1.0M: the wide-shallow point nearest the champion's weight count. Ternary weights ~995,328 vs the chassis's 884,736.
- **train.py:** RUNNABLE NOW: existing `--dim/--layers-n` flags only
- **mode:** sweep — same-chassis config variant; runs inside the shared-data sweep process (corpus loaded once)
- **prediction:** Shape is one of the report's top-5 tests and the cheapest to run. Wider-shallower has the better prior at fixed weights for quant (more parallel evidence per layer); the grid prices it.
- **status:** queued
```mill
id: MILL-1102
mode: sweep
run: --arm layered_half --rope --dim 288 --layers-n 1
```

### MILL-1103 · Shape: dim 160 x 3 blocks (0.92M ternary)
- **source:** systematic grid: shape (runnable now)
- **mechanism:** Shape point at fixed recipe: narrower-deeper at ~0.92M. Ternary weights ~921,600 vs the chassis's 884,736.
- **train.py:** RUNNABLE NOW: existing `--dim/--layers-n` flags only
- **mode:** sweep — same-chassis config variant; runs inside the shared-data sweep process (corpus loaded once)
- **prediction:** Shape is one of the report's top-5 tests and the cheapest to run. Wider-shallower has the better prior at fixed weights for quant (more parallel evidence per layer); the grid prices it.
- **status:** queued
```mill
id: MILL-1103
mode: sweep
run: --arm layered_half --rope --dim 160 --layers-n 3
```

### MILL-1104 · Shape: dim 144 x 3 blocks (0.75M ternary)
- **source:** systematic grid: shape (runnable now)
- **mechanism:** Shape point at fixed recipe: narrower-deeper at ~0.75M. Ternary weights ~746,496 vs the chassis's 884,736.
- **train.py:** RUNNABLE NOW: existing `--dim/--layers-n` flags only
- **mode:** sweep — same-chassis config variant; runs inside the shared-data sweep process (corpus loaded once)
- **prediction:** Shape is one of the report's top-5 tests and the cheapest to run. Wider-shallower has the better prior at fixed weights for quant (more parallel evidence per layer); the grid prices it.
- **status:** queued
```mill
id: MILL-1104
mode: sweep
run: --arm layered_half --rope --dim 144 --layers-n 3
```

### MILL-1105 · Shape: dim 128 x 4 blocks (0.79M ternary)
- **source:** systematic grid: shape (runnable now)
- **mechanism:** Shape point at fixed recipe: the FP champion's depth at 0.79M ternary weights. Ternary weights ~786,432 vs the chassis's 884,736.
- **train.py:** RUNNABLE NOW: existing `--dim/--layers-n` flags only
- **mode:** sweep — same-chassis config variant; runs inside the shared-data sweep process (corpus loaded once)
- **prediction:** Shape is one of the report's top-5 tests and the cheapest to run. Wider-shallower has the better prior at fixed weights for quant (more parallel evidence per layer); the grid prices it.
- **status:** queued
```mill
id: MILL-1105
mode: sweep
run: --arm layered_half --rope --dim 128 --layers-n 4
```

### MILL-1106 · Shape: dim 96 x 6 blocks (0.66M ternary)
- **source:** systematic grid: shape (runnable now)
- **mechanism:** Shape point at fixed recipe: deep-narrow extreme: 6 blocks, 0.66M. Ternary weights ~663,552 vs the chassis's 884,736.
- **train.py:** RUNNABLE NOW: existing `--dim/--layers-n` flags only
- **mode:** sweep — same-chassis config variant; runs inside the shared-data sweep process (corpus loaded once)
- **prediction:** Shape is one of the report's top-5 tests and the cheapest to run. Wider-shallower has the better prior at fixed weights for quant (more parallel evidence per layer); the grid prices it.
- **status:** queued
```mill
id: MILL-1106
mode: sweep
run: --arm layered_half --rope --dim 96 --layers-n 6
```

### MILL-1107 · Shape: dim 192 x 3 blocks (1.33M ternary)
- **source:** systematic grid: shape (runnable now)
- **mechanism:** Shape point at fixed recipe: champion width, 3 blocks (1.33M): depth at fixed width. Ternary weights ~1,327,104 vs the chassis's 884,736.
- **train.py:** RUNNABLE NOW: existing `--dim/--layers-n` flags only
- **mode:** sweep — same-chassis config variant; runs inside the shared-data sweep process (corpus loaded once)
- **prediction:** Shape is one of the report's top-5 tests and the cheapest to run. Wider-shallower has the better prior at fixed weights for quant (more parallel evidence per layer); the grid prices it.
- **status:** queued
```mill
id: MILL-1107
mode: sweep
run: --arm layered_half --rope --dim 192 --layers-n 3
```

### MILL-1108 · Shape: dim 224 x 2 blocks (1.20M ternary)
- **source:** systematic grid: shape (runnable now)
- **mechanism:** Shape point at fixed recipe: champion depth, wider (1.20M). Ternary weights ~1,204,224 vs the chassis's 884,736.
- **train.py:** RUNNABLE NOW: existing `--dim/--layers-n` flags only
- **mode:** sweep — same-chassis config variant; runs inside the shared-data sweep process (corpus loaded once)
- **prediction:** Shape is one of the report's top-5 tests and the cheapest to run. Wider-shallower has the better prior at fixed weights for quant (more parallel evidence per layer); the grid prices it.
- **status:** queued
```mill
id: MILL-1108
mode: sweep
run: --arm layered_half --rope --dim 224 --layers-n 2
```

### MILL-1109 · Shape: dim 192 x 1 blocks (0.44M ternary)
- **source:** systematic grid: shape (runnable now)
- **mechanism:** Shape point at fixed recipe: single block at champion width (0.44M): the shallow floor. Ternary weights ~442,368 vs the chassis's 884,736.
- **train.py:** RUNNABLE NOW: existing `--dim/--layers-n` flags only
- **mode:** sweep — same-chassis config variant; runs inside the shared-data sweep process (corpus loaded once)
- **prediction:** Shape is one of the report's top-5 tests and the cheapest to run. Wider-shallower has the better prior at fixed weights for quant (more parallel evidence per layer); the grid prices it.
- **status:** queued
```mill
id: MILL-1109
mode: sweep
run: --arm layered_half --rope --dim 192 --layers-n 1
```

### MILL-1110 · Shape: dim 320 x 1 blocks (1.23M ternary)
- **source:** systematic grid: shape (runnable now)
- **mechanism:** Shape point at fixed recipe: widest single block probed (1.23M). Ternary weights ~1,228,800 vs the chassis's 884,736.
- **train.py:** RUNNABLE NOW: existing `--dim/--layers-n` flags only
- **mode:** sweep — same-chassis config variant; runs inside the shared-data sweep process (corpus loaded once)
- **prediction:** Shape is one of the report's top-5 tests and the cheapest to run. Wider-shallower has the better prior at fixed weights for quant (more parallel evidence per layer); the grid prices it.
- **status:** queued
```mill
id: MILL-1110
mode: sweep
run: --arm layered_half --rope --dim 320 --layers-n 1
```

### MILL-1111 · Shape: dim 176 x 2 blocks (0.74M ternary)
- **source:** systematic grid: shape (runnable now)
- **mechanism:** Shape point at fixed recipe: fine grid: just under champion width. Ternary weights ~743,424 vs the chassis's 884,736.
- **train.py:** RUNNABLE NOW: existing `--dim/--layers-n` flags only
- **mode:** sweep — same-chassis config variant; runs inside the shared-data sweep process (corpus loaded once)
- **prediction:** Shape is one of the report's top-5 tests and the cheapest to run. Wider-shallower has the better prior at fixed weights for quant (more parallel evidence per layer); the grid prices it.
- **status:** queued
```mill
id: MILL-1111
mode: sweep
run: --arm layered_half --rope --dim 176 --layers-n 2
```

### MILL-1112 · Shape: dim 208 x 2 blocks (1.04M ternary)
- **source:** systematic grid: shape (runnable now)
- **mechanism:** Shape point at fixed recipe: fine grid: just over champion width. Ternary weights ~1,038,336 vs the chassis's 884,736.
- **train.py:** RUNNABLE NOW: existing `--dim/--layers-n` flags only
- **mode:** sweep — same-chassis config variant; runs inside the shared-data sweep process (corpus loaded once)
- **prediction:** Shape is one of the report's top-5 tests and the cheapest to run. Wider-shallower has the better prior at fixed weights for quant (more parallel evidence per layer); the grid prices it.
- **status:** queued
```mill
id: MILL-1112
mode: sweep
run: --arm layered_half --rope --dim 208 --layers-n 2
```

### MILL-1113 · Shape: dim 160 x 2 blocks (0.61M ternary)
- **source:** systematic grid: shape (runnable now)
- **mechanism:** Shape point at fixed recipe: fine grid: champion depth, narrower. Ternary weights ~614,400 vs the chassis's 884,736.
- **train.py:** RUNNABLE NOW: existing `--dim/--layers-n` flags only
- **mode:** sweep — same-chassis config variant; runs inside the shared-data sweep process (corpus loaded once)
- **prediction:** Shape is one of the report's top-5 tests and the cheapest to run. Wider-shallower has the better prior at fixed weights for quant (more parallel evidence per layer); the grid prices it.
- **status:** queued
```mill
id: MILL-1113
mode: sweep
run: --arm layered_half --rope --dim 160 --layers-n 2
```

### MILL-1114 · Rope control at the exact chassis shape (no --rope)
- **source:** systematic grid: probe-format control
- **mechanism:** The chassis WITHOUT rotary at probe budget: prices the rotary win at probe scale (the 8-minute win is recorded; the probe-scale delta calibrates how much of any probe verdict could be position noise).
- **train.py:** RUNNABLE NOW: existing flags only
- **mode:** sweep — same-chassis config variant; runs inside the shared-data sweep process (corpus loaded once)
- **prediction:** Expected +0.03..+0.06 vs job zero (worse): a calibration entry, not a candidate.
- **status:** queued
```mill
id: MILL-1114
mode: sweep
run: --arm layered_half --dim 192 --layers-n 2
```

### MILL-1201 · Batch size 16
- **source:** systematic grid: batch (runnable now)
- **mechanism:** Batch 16 instead of 32 at fixed minutes: batch size changes steps-per-minute AND gradient-noise per vote — for a vote trainer it is effectively a vote-statistics dial, not just a throughput dial.
- **train.py:** RUNNABLE NOW: existing `--batch` flag only
- **mode:** sweep — same-chassis config variant; runs inside the shared-data sweep process (corpus loaded once)
- **prediction:** Batch 64 has a real prior (smoother gate quantiles per step); 16 tests the noisy end.
- **status:** queued
```mill
id: MILL-1201
mode: sweep
run: --arm layered_half --rope --batch 16
```

### MILL-1202 · Batch size 64
- **source:** systematic grid: batch (runnable now)
- **mechanism:** Batch 64 instead of 32 at fixed minutes: batch size changes steps-per-minute AND gradient-noise per vote — for a vote trainer it is effectively a vote-statistics dial, not just a throughput dial.
- **train.py:** RUNNABLE NOW: existing `--batch` flag only
- **mode:** sweep — same-chassis config variant; runs inside the shared-data sweep process (corpus loaded once)
- **prediction:** Batch 64 has a real prior (smoother gate quantiles per step); 16 tests the noisy end.
- **status:** queued
```mill
id: MILL-1202
mode: sweep
run: --arm layered_half --rope --batch 64
```

### MILL-1203 · Batch size 128
- **source:** systematic grid: batch (runnable now)
- **mechanism:** Batch 128 instead of 32 at fixed minutes: batch size changes steps-per-minute AND gradient-noise per vote — for a vote trainer it is effectively a vote-statistics dial, not just a throughput dial.
- **train.py:** RUNNABLE NOW: existing `--batch` flag only
- **mode:** sweep — same-chassis config variant; runs inside the shared-data sweep process (corpus loaded once)
- **prediction:** Batch 64 has a real prior (smoother gate quantiles per step); 16 tests the noisy end.
- **status:** queued
```mill
id: MILL-1203
mode: sweep
run: --arm layered_half --rope --batch 128
```

### MILL-1901 · Control: plain votes + rotary (probe format)
- **source:** mill control (runnable now)
- **mechanism:** The plain single-component vote trainer WITH rotary at probe budget — never run in this combination (the half-control ran without rope, at 8 minutes). Anchors every vote-family probe verdict.
- **train.py:** RUNNABLE NOW: existing flags only
- **mode:** sweep — same-chassis config variant; runs inside the shared-data sweep process (corpus loaded once)
- **prediction:** Expected +0.03..+0.06 vs job zero at probe scale if the half-control's 'levels earn nothing' holds at this budget too.
- **status:** queued
```mill
id: MILL-1901
mode: sweep
run: --arm plain_half --rope
```

### MILL-1902 · Control: full-size layered + rotary (probe format)
- **source:** mill control (runnable now)
- **mechanism:** The 4-block layered trainer with rotary at probe budget: the size axis at probe scale (the ladder measures it at fixed steps; this measures it at fixed seconds).
- **train.py:** RUNNABLE NOW: existing flags only
- **mode:** sweep — same-chassis config variant; runs inside the shared-data sweep process (corpus loaded once)
- **prediction:** Expected worse than job zero per-second (fewer steps), better per-step; the pair prices the probe format itself.
- **status:** queued
```mill
id: MILL-1902
mode: sweep
run: --arm layered --rope
```

### MILL-1903 · Control: STE half + rotary (probe format)
- **source:** mill control (runnable now)
- **mechanism:** The gradient reference WITH rotary at probe budget — the number every vote-family probe is implicitly compared against, measured in the mill's own format.
- **train.py:** RUNNABLE NOW: existing flags only
- **mode:** sweep — same-chassis config variant; runs inside the shared-data sweep process (corpus loaded once)
- **prediction:** Expected to beat job zero (STE led the half-control); if it does NOT at probe scale, probe verdicts for vote ideas need a budget caveat in every report.
- **status:** queued
```mill
id: MILL-1903
mode: sweep
run: --arm ste_half --rope
```

### MILL-1601 · Interaction point: batch 64, V=16
- **source:** systematic grid: batch x threshold
- **mechanism:** Batch 64 with V=16: batch smooths the per-step gradient, which changes the vote stream's statistics; the threshold that is optimal at batch 32 need not be optimal at 64.
- **train.py:** new flag `--votes N` on Layered (batch flag exists)
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Read against MILL-1202 (batch 64) and the V grid; interaction check only.
- **status:** queued
```mill
id: MILL-1601
mode: process
run: --arm layered_half --rope --batch 64 --votes 16
```

### MILL-1602 · Interaction point: batch 64, V=64
- **source:** systematic grid: batch x threshold
- **mechanism:** Batch 64 with V=64: batch smooths the per-step gradient, which changes the vote stream's statistics; the threshold that is optimal at batch 32 need not be optimal at 64.
- **train.py:** new flag `--votes N` on Layered (batch flag exists)
- **mode:** process — isolated train.py subprocess (code-path change); stays isolated until it has a full-trial record
- **prediction:** Read against MILL-1202 (batch 64) and the V grid; interaction check only.
- **status:** queued
```mill
id: MILL-1602
mode: process
run: --arm layered_half --rope --batch 64 --votes 64
```



## F — Idea-mining stream A (merged from CANDIDATES-A.md, 2026-11-12)

114 entries (A-001..A-114) mined against the pool and the lab's RESULTS files under a
zero-duplicate rule — nothing here restates a pooled MILL entry or a closed arm.
Chassis unless an entry says otherwise: layered_half + rotary, V=32, gate q=0.5.
Cost key carried from the candidate file: *cheap probe* = standard ~75 s probe;
*full trial only* = a probe reading is uninformative — those entries (A-028, A-032,
A-064, A-065, A-068, A-083, A-109) are marked FULL TRIAL ONLY in their mode line and
are never probe-eligible. Every A entry names at least one flag train.py does not
have yet, so all 114 sit deferred until their flag lands (see FLAGS-BUILT staging).
Stream A's own top 15: A-023, A-022, A-001, A-094, A-011, A-007, A-098, A-037, A-099,
A-017, A-041, A-086, A-104, A-035, A-059.
Readout entries A-093/A-094/A-095 and A-057 can ride checkpoints from runs already
queued; they should not each consume a full probe slot if the harness supports
eval-only attachments. Several S6 combinations are explicitly sequenced (A-062/A-063
after their singles read).

### F-S1 — Vote accounting and evidence shaping

### A-001 · Soft gate (continuous evidence weighting)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S1 — vote accounting and evidence shaping
- **mechanism:** a vote's increment scales continuously with how far |g| exceeds the layer median (0 at the median, 1 at 2x median) instead of the hard pass/fail cliff.
- **train.py:** new flag `--soft-gate` on Layered/Direct (replaces the `--gate-q` step function)
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** the direct-trainer study names the hard median cliff as a core defect of the shipped mechanism; this removes the cliff itself while keeping increments ±1-shaped. Stream A rank 3.
- **status:** queued
```mill
id: A-001
mode: process
run: --arm layered_half --rope --soft-gate
```

### A-002 · Per-row gate (gate scope = output neuron)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S1 — vote accounting and evidence shaping
- **mechanism:** the gate quantile is computed per output row of each matrix instead of per layer, so rows with small gradient scales still get their stronger half counted.
- **train.py:** new flag `--gate-scope row` alongside `--gate-q`
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** per-layer gating silently disenfranchises low-scale rows; their weights then flip on stale evidence. Row scope is the granularity fix one level down from the pooled per-layer threshold idea.
- **status:** queued
```mill
id: A-002
mode: process
run: --arm layered_half --rope --gate-q 0.5 --gate-scope row
```

### A-003 · Batch-aggregated votes (one vote per 4 micro-batches)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S1 — vote accounting and evidence shaping
- **mechanism:** gradient signs accumulate over 4 micro-batches and each weight casts a single vote from the accumulated sign, so votes reflect batch-level consensus instead of single-batch noise.
- **train.py:** new flag `--vote-every 4` on Layered/Direct
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** at batch 32 the per-step sign is a noisy witness; pre-aggregating raises the evidence quality per count rather than the count rate.
- **status:** queued
```mill
id: A-003
mode: process
run: --arm layered_half --rope --vote-every 4
```

### A-004 · Vote statistic: sign of batch-mean gradient
- **source:** idea-mining stream A (CANDIDATES-A.md), family S1 — vote accounting and evidence shaping
- **mechanism:** the vote direction is sign(mean gradient over the batch) rather than the summed per-sample signs (mean-of-signs) the counter effectively integrates.
- **train.py:** new flag `--vote-stat batchmean`
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** mean-of-signs lets a majority of tiny gradients outvote a few large correct ones; the two statistics disagree exactly on the contested weights, and only one has ever been run.
- **status:** queued
```mill
id: A-004
mode: process
run: --arm layered_half --rope --vote-stat batchmean
```

### A-005 · Deadband with active forgetting
- **source:** idea-mining stream A (CANDIDATES-A.md), family S1 — vote accounting and evidence shaping
- **mechanism:** gradients below 0.25x the layer median cast no vote AND pull the counter one step toward zero — non-evidence actively erases stale conviction instead of merely pausing it.
- **train.py:** new flag `--deadband 0.25` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** counters currently hold early convictions indefinitely through quiet periods; a deadband is the standard control-theory fix and is distinct from leak (which decays regardless of evidence).
- **status:** queued
```mill
id: A-005
mode: process
run: --arm layered_half --rope --deadband 0.25
```

### A-006 · Two-counter race (sustained-evidence flips)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S1 — vote accounting and evidence shaping
- **mechanism:** separate up and down counters per weight; a flip needs net >= V AND total votes >= 2V, so a weight cannot flip on a short one-sided burst.
- **train.py:** new flag `--race` on Layered (int16 counters x2)
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** net-only accounting can't distinguish 32-for/0-against from 500-for/468-against; the second is a contested weight whose flip is a coin toss. The race prices contestedness.
- **status:** queued
```mill
id: A-006
mode: process
run: --arm layered_half --rope --race
```

### A-007 · Hysteresis band on levels (sticky ±1)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S1 — vote accounting and evidence shaping
- **mechanism:** leaving 0 for ±1 costs the full V, but returning from ±1 to 0 costs only V/2 of contrary evidence — earned levels are sticky, unearned ones are cheap to try.
- **train.py:** new flag `--hyst 0.5` on Layered/Direct
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** study candidate C4 pairs hysteresis with thrash freezing, but only freezing was pooled; hysteresis is the half that acts BEFORE oscillation starts. Stream A rank 6.
- **status:** queued
```mill
id: A-007
mode: process
run: --arm layered_half --rope --hyst 0.5
```

### A-008 · Thrash tax (per-weight adaptive threshold from own flip count)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S1 — vote accounting and evidence shaping
- **mechanism:** after each flip, a weight's personal V multiplies by 1.5, decaying back toward the global V over ~200 steps; chronic flippers need progressively stronger evidence but are never frozen outright.
- **train.py:** new flag `--thrash-tax 1.5` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** freezing (pooled) is a hard stop after k flips; a tax is the soft version — it preserves the option value of a genuinely contested weight while damping the documented oscillation pathology.
- **status:** queued
```mill
id: A-008
mode: process
run: --arm layered_half --rope --thrash-tax 1.5
```

### A-009 · Zero-state bias (sparsity pressure through the counter)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S1 — vote accounting and evidence shaping
- **mechanism:** votes that move a weight TOWARD 0 count 1.5x; votes away from 0 count 1x — a sparsity prior expressed inside the vote accounting.
- **train.py:** new flag `--zero-bias 1.5` on Layered/Direct
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** the ~42% zero fraction is load-bearing for BitNet quality (built-in feature selection) and the current mechanism reaches it only as a by-product; pricing zero-ward evidence higher tests whether more deliberate sparsity helps at fixed size.
- **status:** queued
```mill
id: A-009
mode: process
run: --arm layered_half --rope --zero-bias 1.5
```

### A-010 · Layer-normalized vote increments (fixed V, equal flip pressure)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S1 — vote accounting and evidence shaping
- **mechanism:** each layer's increments are rescaled so every layer expects the same flip share per step, while V itself stays the global 32 — normalization on the evidence, not the threshold.
- **train.py:** new flag `--vote-norm` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** the pooled per-layer-V entries adapt the threshold to hit a flip-rate target; this reaches a similar equalization by the dual route and the two need not agree — the comparison itself is informative.
- **status:** queued
```mill
id: A-010
mode: process
run: --arm layered_half --rope --vote-norm
```

### A-011 · Momentum-filtered evidence (EMA-signed votes)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S1 — vote accounting and evidence shaping
- **mechanism:** the vote direction is the sign of a per-weight EMA of gradients (beta=0.9); the counter, gate, and threshold are untouched — momentum filters the EVIDENCE instead of decaying the counter.
- **train.py:** new flag `--vote-ema 0.9` on Layered/Direct (4 B/weight of fp state, charged honestly)
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** the pooled leak family decays accumulated counts; nothing has smoothed the incoming stream. Sign-of-EMA is the direct transplant of why momentum helps signSGD-style updates. Stream A rank 5.
- **status:** queued
```mill
id: A-011
mode: process
run: --arm layered_half --rope --vote-ema 0.9
```

### A-012 · Agreement-weighted votes (fast/slow EMA)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S1 — vote accounting and evidence shaping
- **mechanism:** two gradient EMAs (beta=0.5 and beta=0.99) per weight; when they agree the vote counts 2, when they disagree it counts 1 — agreement amplifies, never vetoes.
- **train.py:** new flag `--vote-ema2` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** the pooled `--agree` retest gates votes OFF on disagreement (Fable's form); weighting instead of gating keeps weak evidence flowing while still pricing multi-timescale consensus — a genuinely different rule.
- **status:** queued
```mill
id: A-012
mode: process
run: --arm layered_half --rope --vote-ema2
```

### A-013 · Loss-weighted token votes
- **source:** idea-mining stream A (CANDIDATES-A.md), family S1 — vote accounting and evidence shaping
- **mechanism:** each token position's contribution to a weight's vote is weighted by that token's current loss, so the positions the model gets wrong drive the discrete structure.
- **train.py:** new flag `--tokw-loss` in the training loop (per-position loss weights into the vote path only; the AdamW parts keep the plain loss)
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** failweight (pooled) reweights whole WINDOWS in the sampler; this is the finer, per-position form inside the vote mechanism itself, and it leaves the shared parts' training distribution untouched.
- **status:** queued
```mill
id: A-013
mode: process
run: --arm layered_half --rope --tokw-loss
```

### A-014 · Shared counter across layered components
- **source:** idea-mining stream A (CANDIDATES-A.md), family S1 — vote accounting and evidence shaping
- **mechanism:** one counter per weight serves both ternary components; when it crosses V the flip is spent on the cheaper component first (t2 until it saturates, then t1).
- **train.py:** new flag `--shared-counter` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** separate counters can push t1 and t2 in cancelling directions (the arbitration entries only govern simultaneous crossings); a shared evidence stream makes cancellation impossible by construction and halves counter state.
- **status:** queued
```mill
id: A-014
mode: process
run: --arm layered_half --rope --shared-counter
```

### F-S2 — Flip rules and state dynamics

### A-015 · Probabilistic flip on threshold crossing
- **source:** idea-mining stream A (CANDIDATES-A.md), family S2 — flip rules and state dynamics
- **mechanism:** when |count| crosses V the weight flips with probability |count|/(2V) (counter resets either way) — deep conviction flips surely, marginal conviction flips sometimes.
- **train.py:** new flag `--flip-prob` on Layered (needs the int16 counter path, no overshoot retention)
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** overshoot carry (deterministic retention of leftover evidence) is closed, but stochastic throttling of marginal flips is a different use of the overshoot signal: it rations exactly the flips the evidence is least sure about.
- **status:** queued
```mill
id: A-015
mode: process
run: --arm layered_half --rope --flip-prob
```

### A-016 · Batched flips (structure updates every 8 steps)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S2 — flip rules and state dynamics
- **mechanism:** counters accumulate continuously but flips are APPLIED only every 8 steps, so the network the gradients describe is stable between structure rounds.
- **train.py:** new flag `--flip-batch 8` on Layered/Direct
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** per-step flipping means every gradient is computed against a network that just changed in ~0.1% of its weights; block-updating the discrete side is the discrete analogue of target networks / block coordinate descent and has never been tried here.
- **status:** queued
```mill
id: A-016
mode: process
run: --arm layered_half --rope --flip-batch 8
```

### A-017 · Global flip budget (rationed flips per step)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S2 — flip rules and state dynamics
- **mechanism:** at most 0.05% of weights may flip per step; if more cross V, the largest-overshoot counters win and the rest keep accumulating.
- **train.py:** new flag `--flip-cap 0.0005` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** flip RATE is currently an emergent by-product nobody controls; the ladder records show flip share varying 2x between arms with no design intent. A budget makes the structure's learning rate an explicit dial, orthogonal to V. Stream A rank 10.
- **status:** queued
```mill
id: A-017
mode: process
run: --arm layered_half --rope --flip-cap 0.0005
```

### A-018 · Block-staggered flips (one block flips per step, rotating)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S2 — flip rules and state dynamics
- **mechanism:** flip eligibility rotates across blocks — on any step only one block's threshold crossings are applied; other blocks' counters keep accumulating.
- **train.py:** new flag `--flip-stagger` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** simultaneous flips in adjacent blocks interact (a flip in block 1 changes what block 2's gradients meant); staggering serializes the interaction, the same reason coordinate descent can beat joint updates on coupled problems.
- **status:** queued
```mill
id: A-018
mode: process
run: --arm layered_half --rope --flip-stagger
```

### A-019 · Flip-flop quarantine
- **source:** idea-mining stream A (CANDIDATES-A.md), family S2 — flip rules and state dynamics
- **mechanism:** a weight that flips and flips back within 20 steps has its counter zeroed and its personal V doubled for the next 100 steps, then released.
- **train.py:** new flag `--quarantine` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** freezing (pooled) punishes flip COUNT over a window and is permanent; quarantine punishes the specific flip-FLOP signature (immediate reversal = the flip was noise) and is temporary and targeted.
- **status:** queued
```mill
id: A-019
mode: process
run: --arm layered_half --rope --quarantine
```

### A-020 · Component coupling on flip (sibling counter reset)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S2 — flip rules and state dynamics
- **mechanism:** when one layered component flips, the OTHER component's counter resets to 0 — a flip restarts the sibling's evidence from scratch.
- **train.py:** new flag `--comp-reset` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** after t1 flips, t2's accumulated evidence was gathered against the old installed value and is partly stale; the pooled arbitration rules govern simultaneous flips only, never this cross-time staleness.
- **status:** queued
```mill
id: A-020
mode: process
run: --arm layered_half --rope --comp-reset
```

### A-021 · Post-flip rebound damping
- **source:** idea-mining stream A (CANDIDATES-A.md), family S2 — flip rules and state dynamics
- **mechanism:** for 10 steps after a weight flips, its incoming votes count half — the new state gets a settling period before contrary evidence can accumulate at full strength.
- **train.py:** new flag `--rebound 10` on Layered/Direct
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** the cheapest possible anti-oscillation device: no thresholds, no freezing, just a refractory period — the neural-dynamics answer to the same pathology freezing attacks statistically.
- **status:** queued
```mill
id: A-021
mode: process
run: --arm layered_half --rope --rebound 10
```

### A-022 · Tail freeze (V x3 for the last 10% of steps)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S2 — flip rules and state dynamics
- **mechanism:** V triples for the final 10% of the run while everything else (including AdamW parts) continues unchanged — the discrete structure sets like cooling metal at the end.
- **train.py:** new flag `--vtail 3` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** the pooled schedules move V linearly across the whole run; this is a step change confined to the tail, and the closed anneal arm's lesson (hot starts poison) says nothing about cold ENDINGS. It is the vote-side form of Fable's cool-down finding, in its most conservative shape. Stream A rank 2.
- **status:** queued
```mill
id: A-022
mode: process
run: --arm layered_half --rope --vtail 3
```

### A-023 · Vote warmup (no flips for the first 5% of steps)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S2 — flip rules and state dynamics
- **mechanism:** counters accumulate from step 0 but NO flip may fire during the first 5% of steps; structure commits only on banked evidence.
- **train.py:** new flag `--vwarm 0.05` on Layered/Direct
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** the anneal disaster (3.850) proved early flips on weak evidence are the mechanism's worst failure; every pooled schedule still flips from step 0. A pure delay is the most direct repair and has literally never been run in this lab. Stream A rank 1.
- **status:** queued
```mill
id: A-023
mode: process
run: --arm layered_half --rope --vwarm 0.05
```

### A-024 · epsilon-greedy random flips (lattice exploration)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S2 — flip rules and state dynamics
- **mechanism:** each step, a random 0.1% of weights flip to a random other level regardless of counters.
- **train.py:** new flag `--flip-eps 0.001` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** vote dynamics are purely exploitative — a weight whose early evidence was unlucky may never revisit a better level; a small exploration rate is the standard bandit fix and its cost at 0.1% is measurable, not assumed.
- **status:** queued
```mill
id: A-024
mode: process
run: --arm layered_half --rope --flip-eps 0.001
```

### F-S3 — Per-layer, per-role, per-head treatment

### A-025 · Depth-scaled V (fixed depth prior: 16 -> 48)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S3 — per-layer, per-role, per-head treatment
- **mechanism:** block 1 runs V=16, block 2 runs V=48 — deeper blocks flip colder because their errors compound through everything downstream.
- **train.py:** new flag `--vdepth 16,48` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** pooled per-layer entries ADAPT V to a flip-rate target (feedback); this is the open-loop prior from error-compounding theory. If the prior alone captures the gain, the adaptive machinery is unnecessary.
- **status:** queued
```mill
id: A-025
mode: process
run: --arm layered_half --rope --vdepth 16,48
```

### A-026 · Role-scaled V (attention cold, FFN hot)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S3 — per-layer, per-role, per-head treatment
- **mechanism:** attention projections run V=48, FFN projections V=24.
- **train.py:** new flag `--vrole 48,24` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** every record agrees attention logits are the fragile side of a ternary net (coarse QK products get exponentiated); the FFN is a sum where flip noise averages out. One global V prices both the same today.
- **status:** queued
```mill
id: A-026
mode: process
run: --arm layered_half --rope --vrole 48,24
```

### A-027 · Mixed structure by depth (block 1 plain, block 2 layered)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S3 — per-layer, per-role, per-head treatment
- **mechanism:** the first block uses single-component ternary weights, the second uses two-component layered weights (same total ternary count rebalanced).
- **train.py:** new flag `--mixed-depth` in the model builder
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** the half-control settled that levels earn nothing UNIFORMLY at equal size/steps; it never tested levels concentrated where representation is richest (the last block). Placement is a different question from count.
- **status:** queued
```mill
id: A-027
mode: process
run: --arm layered_half --rope --mixed-depth
```

### A-028 · Hybrid by depth (block 1 STE, block 2 votes)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S3 — per-layer, per-role, per-head treatment
- **mechanism:** the first block's ternary weights train by STE, the second block's by votes, simultaneously — trainer assignment by depth instead of by phase.
- **train.py:** new flag `--hybrid-depth ste,votes` (both trainers active in one run)
- **mode:** process — FULL TRIAL ONLY per the candidate file's cost line: never probe-eligible; enters only by a human's word. The named flag is not in train.py yet, so screen.py defers this entry until the flag lands in any case
- **prediction:** pooled hybrids switch trainers over TIME; the phase switch forces one mechanism to inherit the other's half-trained state. Depth-splitting lets each mechanism own the territory it suits, with no hand-off.
- **status:** queued
```mill
id: A-028
mode: process
run: --arm layered_half --rope --hybrid-depth ste,votes
```

### A-029 · Per-head temperature spread (V = 16/24/32/48 across heads)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S3 — per-layer, per-role, per-head treatment
- **mechanism:** the four attention heads' QKVO weights run four different fixed thresholds, giving the model a built-in diversity of flip temperatures.
- **train.py:** new flag `--vhead` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** heads specialize; a single V forces identical evidence standards on heads doing different jobs. A spread is also a cheap ensemble-inside-one-layer: at least one head sits near the (unknown) optimal temperature.
- **status:** queued
```mill
id: A-029
mode: process
run: --arm layered_half --rope --vhead
```

### A-030 · Scale-coupled V (V proportional to layer gamma)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S3 — per-layer, per-role, per-head treatment
- **mechanism:** each layer's V is set proportional to its absmean scale gamma (recomputed as gamma drifts), so layers whose installed steps are physically larger demand proportionally more evidence.
- **train.py:** new flag `--vscale` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** a flip changes the output by ~gamma; equal V across layers means unequal physical step sizes per unit evidence. Coupling V to gamma equalizes the evidence-per-physical-change ratio — a units argument, not a tuning guess.
- **status:** queued
```mill
id: A-030
mode: process
run: --arm layered_half --rope --vscale
```

### A-031 · Counter width by depth (int8 early, int16 late)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S3 — per-layer, per-role, per-head treatment
- **mechanism:** block 1 keeps int8 counters, block 2 gets int16 counters (with V=64 there) — state bytes allocated where the network is deepest.
- **train.py:** new flags `--width-depth` + per-block `--votes`
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** the accumulator-precision dial has only been turned uniformly; if precision matters, it should matter most where errors compound. This prices the dial's placement at ~half the cost of widening everywhere.
- **status:** queued
```mill
id: A-031
mode: process
run: --arm layered_half --rope --width-depth --votes 64
```

### A-032 · Role-split trainers (votes on QK, STE on V/O/FFN)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S3 — per-layer, per-role, per-head treatment
- **mechanism:** votes train the Q and K projections only; STE trains V, O, and FFN projections.
- **train.py:** new flag `--role-split qk`
- **mode:** process — FULL TRIAL ONLY per the candidate file's cost line: never probe-eligible; enters only by a human's word. The named flag is not in train.py yet, so screen.py defers this entry until the flag lands in any case
- **prediction:** QK products are where ternary coarseness is exponentiated — arguably where the vote counter's patience helps most — while the value/FFN path is a plain sum where STE's fine convergence is strongest. Nobody has split the mechanisms by projection role.
- **status:** queued
```mill
id: A-032
mode: process
run: --arm layered_half --rope --role-split qk
```

### F-S4 — Schedules and phases specific to votes

### A-033 · Cyclic V (16 -> 48 -> 16, twice per run)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S4 — schedules and phases specific to votes
- **mechanism:** V follows a triangular cycle over the run instead of a monotone schedule — periodic reheating lets settled structure re-open, cooling re-sets it.
- **train.py:** new flag `--vcycle` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** pooled schedules are monotone (cool only); cyclical schedules (SGDR) exist in FP training precisely because monotone cooling strands models in early basins. The vote lattice is at least as basin-prone.
- **status:** queued
```mill
id: A-033
mode: process
run: --arm layered_half --rope --vcycle
```

### A-034 · Gate ease-in (quantile ramps 0 -> 0.5 over the first 25%)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S4 — schedules and phases specific to votes
- **mechanism:** the gate starts OPEN (every gradient votes) and tightens to the standard stronger-half rule over the first quarter of the run.
- **train.py:** new flag `--gate-ease 0.25` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** pooled ease-in entries ease the ROUNDING (STE-side concept ported to votes); easing the GATE is the vote-native version — early training gets maximum evidence flow while gradients are large and informative, selectivity arrives as they shrink.
- **status:** queued
```mill
id: A-034
mode: process
run: --arm layered_half --rope --gate-ease 0.25
```

### A-035 · Grow components mid-run (plain -> layered at 25%)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S4 — schedules and phases specific to votes
- **mechanism:** train plain votes for the first 25%, then split each weight: t1 keeps the trained state, t2 enters at 0 with fresh counters — the layered structure is GROWN from a trained plain net.
- **train.py:** new flag `--grow-comps 0.25` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** layered-from-scratch wastes early steps populating levels (the sweep record: ±2 barely populated at 8 min); growing gives the second component a meaningful backbone to correct from step one of its life. It is the layered idea's best-case entry point, never tested. Stream A rank 14.
- **status:** queued
```mill
id: A-035
mode: process
run: --arm layered_half --rope --grow-comps 0.25
```

### A-036 · Collapse components late (layered -> plain at 75%)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S4 — schedules and phases specific to votes
- **mechanism:** at 75% of the run, t2 folds into t1 by rounding the installed sum back to {-1,0,1} and training finishes as plain votes.
- **train.py:** new flag `--collapse 0.75` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** tests whether the levels' value is as early-training scaffolding (extra expressiveness while structure forms) rather than as a serving format — if collapse matches layered, the serving model can ship at half the mechanism state.
- **status:** queued
```mill
id: A-036
mode: process
run: --arm layered_half --rope --collapse 0.75
```

### A-037 · Frozen-structure polish (votes off at 60%, AdamW parts finish)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S4 — schedules and phases specific to votes
- **mechanism:** after 60% of steps the ternary state freezes completely and only embeddings, norms, and scales train for the remaining 40%.
- **train.py:** new flag `--freeze-tern 0.6` on Layered/Direct
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** prices the structure-vs-calibration split directly: how much of the remaining loss is the discrete structure vs the FP parts' fit to it? Freezing ONLY the discrete side is the vote-native form of Fable's polish. Stream A rank 8.
- **status:** queued
```mill
id: A-037
mode: process
run: --arm layered_half --rope --freeze-tern 0.6
```

### A-038 · Alternating update phases (200-step blocks)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S4 — schedules and phases specific to votes
- **mechanism:** alternate 200 steps of votes-only updates (AdamW parts frozen) with 200 steps of AdamW-only updates (counters frozen).
- **train.py:** new flag `--alt-phase 200` in the training loop
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** simultaneous updating means each side perpetually chases the other's motion; alternation is block coordinate descent across the discrete/continuous split.
- **status:** queued
```mill
id: A-038
mode: process
run: --arm layered_half --rope --alt-phase 200
```

### A-039 · AdamW warmup for the shared parts (vote arms)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S4 — schedules and phases specific to votes
- **mechanism:** the shared parts' lr warms 0 -> 1e-3 over the first 100 steps while votes run at full rate from step 0.
- **train.py:** new flag `--opt-warmup 100` on Direct/Layered
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** STE arms have always had warmup (200 steps, in the built-in recipe); vote arms never have — an unexamined recipe asymmetry between the two families whose comparison is the lab's central question. Nearly free to test.
- **status:** queued
```mill
id: A-039
mode: process
run: --arm layered_half --rope --opt-warmup 100
```

### A-040 · Gradient-norm clipping before signing
- **source:** idea-mining stream A (CANDIDATES-A.md), family S4 — schedules and phases specific to votes
- **mechanism:** each layer's gradient is norm-clipped (to 1.0) before its sign/magnitude feeds the vote path; the AdamW parts see the unclipped gradient.
- **train.py:** new flag `--gclip 1.0` on Layered/Direct
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** a single outlier batch currently casts a full-strength vote storm; clipping bounds any one batch's say over the discrete structure without touching the continuous parts' training.
- **status:** queued
```mill
id: A-040
mode: process
run: --arm layered_half --rope --gclip 1.0
```

### F-S5 — Training-data side: curricula, ordering, mixture

### A-041 · Easy-to-hard curriculum (windows ordered by init loss)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S5 — training-data side: curricula, ordering, mixture
- **mechanism:** training windows are scored once by the init model and presented in ascending-loss order across the run (uniform sampling within decile bands to avoid pure sorting).
- **train.py:** new flag `--curr asc` (sampler change; one init pass over the corpus, charged)
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** the lab has only ever sampled uniformly; a vote counter forming structure early benefits from clean signal first — the curriculum hypothesis applied to exactly the phase where the anneal arm showed early evidence quality is decisive. Stream A rank 11 (A-042 rides as its control).
- **status:** queued
```mill
id: A-041
mode: process
run: --arm layered_half --rope --curr asc
```

### A-042 · Hard-to-easy anti-curriculum (control)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S5 — training-data side: curricula, ordering, mixture
- **mechanism:** the reverse ordering of A-041 (descending init loss).
- **train.py:** new flag `--curr desc`
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** curriculum claims are unfalsifiable without the reverse control; if desc >= asc, ordering effects here are about recency, not difficulty — either answer disciplines A-041's interpretation.
- **status:** queued
```mill
id: A-042
mode: process
run: --arm layered_half --rope --curr desc
```

### A-043 · Middle-out curriculum
- **source:** idea-mining stream A (CANDIDATES-A.md), family S5 — training-data side: curricula, ordering, mixture
- **mechanism:** start from median-difficulty windows and expand the band symmetrically toward easy and hard extremes.
- **train.py:** new flag `--curr mid`
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** median windows are where the model's errors are most informative (not yet mastered, not hopeless); both pure orderings spend early steps on one uninformative extreme.
- **status:** queued
```mill
id: A-043
mode: process
run: --arm layered_half --rope --curr mid
```

### A-044 · Paired repetition (each window twice in a row)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S5 — training-data side: curricula, ordering, mixture
- **mechanism:** every sampled window is trained on twice consecutively before the stream moves on.
- **train.py:** new flag `--repeat 2` (sampler)
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** the second pass's gradients are computed against a network that just absorbed the first pass — for a counter integrating signs, paired passes turn single noisy votes into before/after comparisons. Ordering has never been varied at all in this lab.
- **status:** queued
```mill
id: A-044
mode: process
run: --arm layered_half --rope --repeat 2
```

### A-045 · Context-length curriculum (64 -> 128 -> 256 by thirds)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S5 — training-data side: curricula, ordering, mixture
- **mechanism:** the run trains at ctx 64 for the first third, 128 for the second, 256 for the last (RoPE positions span each range as it arrives).
- **train.py:** new flag `--ctx-curr` (window slicing in the sampler)
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** short contexts are cheaper per step and teach local structure first; the final third still trains at full length. Even at equal minutes the step count rises — charged honestly, judged per minute like every arm.
- **status:** queued
```mill
id: A-045
mode: process
run: --arm layered_half --rope --ctx-curr
```

### A-046 · Reverse context curriculum (256 -> 128 -> 64, control)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S5 — training-data side: curricula, ordering, mixture
- **mechanism:** the reverse schedule of A-045.
- **train.py:** new flag `--ctx-curr rev`
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** control for A-045 — separates 'ends at the tested length' from 'short first helps'; read together, the pair isolates the ordering effect from the endpoint effect.
- **status:** queued
```mill
id: A-046
mode: process
run: --arm layered_half --rope --ctx-curr rev
```

### A-047 · Near-duplicate window removal
- **source:** idea-mining stream A (CANDIDATES-A.md), family S5 — training-data side: curricula, ordering, mixture
- **mechanism:** windows whose token stream is a near-duplicate of an earlier window (hash of sorted 8-gram shingles) are dropped from the stream.
- **train.py:** new flag `--dedup` (sampler preprocessing, charged)
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** the corpus is harvested prose — boilerplate and repeated passages are plausible; duplicated windows are invisible oversampling of whatever they contain, and uniform sampling has never been audited for it.
- **status:** queued
```mill
id: A-047
mode: process
run: --arm layered_half --rope --dedup
```

### A-048 · Source-balanced mixture (equal weight per source file)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S5 — training-data side: curricula, ordering, mixture
- **mechanism:** sampling weights are set so each of the ~393 source files contributes equally, instead of in proportion to its length.
- **train.py:** new flag `--src-balance` (sampler weights)
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** length-proportional sampling lets the longest files dominate the structure the votes build; mixture is a first-class lever in the recipe literature and this lab has never moved it. Failweight (pooled) reweights by LOSS; this reweights by PROVENANCE — different axis.
- **status:** queued
```mill
id: A-048
mode: process
run: --arm layered_half --rope --src-balance
```

### A-049 · Frequent-token downweighting
- **source:** idea-mining stream A (CANDIDATES-A.md), family S5 — training-data side: curricula, ordering, mixture
- **mechanism:** windows where the 100 most frequent tokens make up >60% of positions are sampled at half rate.
- **train.py:** new flag `--freq-balance` (sampler weights)
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** stopword-dominated windows carry little structural signal per step but consume the same vote budget; this is a content-based mixture correction that needs no loss measurements and cannot chase the model's own biases (unlike failweight).
- **status:** queued
```mill
id: A-049
mode: process
run: --arm layered_half --rope --freq-balance
```

### A-050 · Held-adjacency buffer (leak-tightening control)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S5 — **METHODS AUDIT entry, not a performance candidate** (kept visible per the candidate file's own note: run it once early — its result re-prices confidence in every existing margin)
- **mechanism:** training windows within ±2 window positions of any held window are excluded from the stream.
- **train.py:** new flag `--buffer 2` (sampler exclusion)
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** held windows were chosen by an every-40th rule, so their immediate neighbours ARE trained on — near-duplicate context could inflate every held number the lab owns. This is a methods audit priced as one probe: if the loss moves, all prior margins get re-read.
- **status:** queued
```mill
id: A-050
mode: process
run: --arm layered_half --rope --buffer 2
```

### A-051 · Cyclic-shift augmentation
- **source:** idea-mining stream A (CANDIDATES-A.md), family S5 — training-data side: curricula, ordering, mixture
- **mechanism:** each window is cyclically shifted by a random offset when sampled (the token ring rotates; RoPE sees the same content at different absolute phases).
- **train.py:** new flag `--shift-aug` (sampler transform)
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** with only ~8 minutes of unique stream, augmentation multiplies the effective data; rotation specifically attacks position overfitting, which a carried position table + rotary hybrid could plausibly suffer.
- **status:** queued
```mill
id: A-051
mode: process
run: --arm layered_half --rope --shift-aug
```

### A-052 · Span-noise input masking (objective unchanged)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S5 — training-data side: curricula, ordering, mixture
- **mechanism:** one random 8-token span per window is replaced by a mask embedding in the INPUT; targets remain the true next tokens everywhere — pure input-noise regularization under the standard token loss.
- **train.py:** new flag `--span-noise 8` in the model input path
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** the JEPA objective is closed, and this is NOT it — the loss, targets, and yardstick are unchanged. It tests only whether input corruption regularizes a vote-trained trunk (whose discrete weights may overfit surface patterns faster than FP weights).
- **status:** queued
```mill
id: A-052
mode: process
run: --arm layered_half --rope --span-noise 8
```

### A-053 · Source-diverse batches (>=8 files per batch)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S5 — training-data side: curricula, ordering, mixture
- **mechanism:** batch construction deliberately mixes windows from at least 8 different source files, instead of whatever consecutive sampling produces.
- **train.py:** new flag `--batch-mix` (batch builder)
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** for a sign-integrating trainer, batch composition IS the evidence distribution; homogeneous batches cast correlated votes. Diversity per batch is the mixture lever at the finest grain, distinct from global sampling weights.
- **status:** queued
```mill
id: A-053
mode: process
run: --arm layered_half --rope --batch-mix
```

### A-054 · Regression-weighted sampling (delta-loss, not loss level)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S5 — training-data side: curricula, ordering, mixture
- **mechanism:** windows are re-scored periodically; those whose loss INCREASED since their last scoring are oversampled 2x — targeting forgetting, not difficulty.
- **train.py:** new flag `--regress-weight 2` (sampler)
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** failweight (pooled) oversamples the statically worst decile; regression weighting targets what training is actively LOSING — catastrophic-forgetting repair aimed at the discrete structure's known weakness (flips erase as well as write).
- **status:** queued
```mill
id: A-054
mode: process
run: --arm layered_half --rope --regress-weight 2
```

### A-055 · Coverage-first sampling (unseen windows preferred)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S5 — training-data side: curricula, ordering, mixture
- **mechanism:** sampling weight is highest for windows never yet sampled and drops after each visit, maximizing unique-window coverage within the budget.
- **train.py:** new flag `--coverage` (sampler)
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** at 8 minutes the run sees a fraction of the corpus; uniform sampling revisits some windows while never touching others. For a token-hungry model family, breadth of unique tokens is the scarcest resource — this spends the budget on it directly.
- **status:** queued
```mill
id: A-055
mode: process
run: --arm layered_half --rope --coverage
```

### A-056 · Corrupt-window filtering (drop worst 2% by init loss)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S5 — training-data side: curricula, ordering, mixture
- **mechanism:** the 2% of windows with the highest init-model loss are removed from the stream entirely (likely boilerplate, markup wreckage, or foreign text).
- **train.py:** new flag `--drop-worst 0.02` (sampler preprocessing, shares A-041's scoring pass)
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** the mirror image of failweight: instead of training MORE on the hardest windows, test whether the hardest sliver is noise rather than signal. The pair (MILL-406/A-056) brackets the hardest-window question from both directions.
- **status:** queued
```mill
id: A-056
mode: process
run: --arm layered_half --rope --drop-worst 0.02
```

### F-S6 — Combinations of known-good or neutral elements, never tried together

### A-057 · STE-half + rotary + EMA (running-mean) readout
- **source:** idea-mining stream A (CANDIDATES-A.md), family S6 — combinations of known-good or neutral elements
- **mechanism:** ste_half with rotary, evaluated at an exponential moving average of the latent weights (decay 0.999) as well as at the final weights.
- **train.py:** new flag `--ema-readout 0.999` on the STE trainer (eval-side, like the pooled modal readout but for the FP trainer)
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** Fable's recipe line reads EVERY run at running-mean weights and the modal readout (pooled) imports the idea for votes; the STE side of THIS lab has never had its readout measured, yet ste_half currently leads the whole table (2.8205) — its readout delta is unpriced.
- **status:** queued
```mill
id: A-057
mode: process
run: --arm ste_half --rope --ema-readout 0.999
```

### A-058 · Fractional leak 0.99 + thrash freeze 5
- **source:** idea-mining stream A (CANDIDATES-A.md), family S6 — combinations of known-good or neutral elements
- **mechanism:** the direct-trainer study's C3 and C4 add-ons stacked on the layered chassis.
- **train.py:** `--leak 0.99 --freeze 5` (both flags pooled separately as MILL-209/MILL-213 family; the combination is new)
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** leak smooths evidence over time; freezing removes proven oscillators. They attack the same pathology at different points (input vs state) and the study's own ordering presents them as a pair — the pair has never run.
- **status:** queued
```mill
id: A-058
mode: process
run: --arm layered_half --rope --leak 0.99 --freeze 5
```

### A-059 · Calibrated magnitude votes at FULL width + rotary
- **source:** idea-mining stream A (CANDIDATES-A.md), family S6 — combinations of known-good or neutral elements
- **mechanism:** `--mag-cal 1.0` on the full-width plain trainer with rotary.
- **train.py:** `--arm plain --rope --mag-cal 1.0`
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** calibrated magnitude votes are pooled only at half width; the as-specified full-width arm is closed but the pool's own precedent says a calibrated re-set is a different arm. Width interacts with the accumulator dial, so the half result cannot simply be assumed to transfer. Stream A rank 15.
- **status:** queued
```mill
id: A-059
mode: process
run: --arm plain --rope --mag-cal 1.0
```

### A-060 · Rounding ease-in 0.5 + vote schedule 32->64
- **source:** idea-mining stream A (CANDIDATES-A.md), family S6 — combinations of known-good or neutral elements
- **mechanism:** the two Fable-trace transfers for votes stacked: `--ease 0.5 --vsched 32:64`.
- **train.py:** both flags pooled separately (MILL-301 family / MILL-204 family); combination new
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** ease-in protects early structure formation; the schedule cools late flips. They act on disjoint phases of the run, so additivity is plausible — and if they interfere, that interaction is itself a finding about phase overlap.
- **status:** queued
```mill
id: A-060
mode: process
run: --arm layered_half --rope --ease 0.5 --vsched 32:64
```

### A-061 · Failweight 2 + modal readout 5
- **source:** idea-mining stream A (CANDIDATES-A.md), family S6 — combinations of known-good or neutral elements
- **mechanism:** weakness-targeted sampling with the discrete-EMA readout: `--failweight 2 --modal 5`.
- **train.py:** both flags pooled separately (MILL-406 / MILL-218 family); combination new
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** failweight changes what the structure learns; modal readout reduces the variance of what gets shipped. Training-side and readout-side gains are the most likely pair in the pool to be purely additive.
- **status:** queued
```mill
id: A-061
mode: process
run: --arm layered_half --rope --failweight 2 --modal 5
```

### A-062 · QK-Norm + gated attention
- **source:** idea-mining stream A (CANDIDATES-A.md), family S6 — combinations of known-good or neutral elements
- **mechanism:** the research report's rank-1 and rank-2 items stacked: `--qk-norm --gated-attn`.
- **train.py:** both flags pooled separately (MILL-101 / MILL-104); combination new. Sequenced: run once both singles have read
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** QK-Norm bounds logits before the softmax; the gate suppresses sink-dumping after it. They guard the same pathway at two different stations — the report ranks both top-2 but the lab tests singles first; this is the designated first stack.
- **status:** queued
```mill
id: A-062
mode: process
run: --arm layered_half --rope --qk-norm --gated-attn
```

### A-063 · Per-channel scales + Hadamard rotation
- **source:** idea-mining stream A (CANDIDATES-A.md), family S6 — combinations of known-good or neutral elements
- **mechanism:** `--scale-gran channel --hadamard` — finer weight scales plus activation-outlier spreading.
- **train.py:** both flags pooled separately (MILL-107 family / MILL-129); combination new
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** both are magnitude-management moves but on opposite sides of the matmul (weights vs activations); ternary error lives in their interaction, so the stack could compound — or reveal that one makes the other redundant.
- **status:** queued
```mill
id: A-063
mode: process
run: --arm layered_half --rope --scale-gran channel --hadamard
```

### A-064 · SubLN + logits KD (BitDistill's actual pairing)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S6 — combinations of known-good or neutral elements
- **mechanism:** `--subln --kd 1.0` — SubLN inserted exactly as BitDistill's stage-1 precondition for its stage-3 distillation.
- **train.py:** both flags pooled separately (MILL-125 family / MILL-113 family); combination new (and it is the published recipe's real form)
- **mode:** process — FULL TRIAL ONLY per the candidate file's cost line: never probe-eligible; enters only by a human's word. The named flag is not in train.py yet, so screen.py defers this entry until the flag lands in any case
- **prediction:** BitDistill's evidence is for the SEQUENCE, not for either piece alone; testing KD without its designed preconditioner (the pooled singles) may underprice both. This entry is the faithful transplant.
- **status:** queued
```mill
id: A-064
mode: process
run: --arm layered_half --rope --subln --kd 1.0
```

### A-065 · FP-first 0.9 + two-stage weight decay (STE)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S6 — combinations of known-good or neutral elements
- **mechanism:** ParetoQ's split with the official recipe's WD shape: WD cosines to 0.1 during the FP phase and switches off for the ternary phase.
- **train.py:** `--fp-first 0.9 --two-stage-wd` on the STE trainer (pieces pooled separately as MILL-111/MILL-109 family)
- **mode:** process — FULL TRIAL ONLY per the candidate file's cost line: never probe-eligible; enters only by a human's word. The named flag is not in train.py yet, so screen.py defers this entry until the flag lands in any case
- **prediction:** the pooled entries test the split and the two-stage recipe separately; the published recipes were designed together, so the combination is the honest form of both.
- **status:** queued
```mill
id: A-065
mode: process
run: --arm ste_half --rope --fp-first 0.9 --two-stage-wd
```

### A-066 · Three components + descending per-component V (32, 16, 8)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S6 — combinations of known-good or neutral elements
- **mechanism:** `--comps 3 --comp-v 32,16,8` — each successive component flips hotter than the last.
- **train.py:** pooled pieces (MILL-402 comps 3; MILL-1401/1402 comp-v pairs) extended to a 3-term descending ladder; combination new
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** the pooled pair (32,16) tests backbone+correction; a descending ladder is the multigrid version — coarse stable structure, then progressively finer/faster corrections — which is how residual quantizers are actually built.
- **status:** queued
```mill
id: A-066
mode: process
run: --arm layered_half --rope --comps 3 --comp-v 32,16,8
```

### A-067 · Ungated calibrated magnitude votes (plain, q removed entirely)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S6 — combinations of known-good or neutral elements
- **mechanism:** `--arm plain_half --rope --mag-cal 1.0 --gate-q 0.0` — calibrated increments with NO median gate anywhere in the path.
- **train.py:** combination new (gate-off exists pooled only on layered with plain increments)
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** completes the 2x2 of {gate, increment type} for the calibrated family: if ungated-calibrated wins, the gate was the problem all along and several pooled gate entries get re-read.
- **status:** queued
```mill
id: A-067
mode: process
run: --arm plain_half --rope --mag-cal 1.0 --gate-q 0.0
```

### A-068 · Gradient whitening + Muon (hybrid arm)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S6 — combinations of known-good or neutral elements
- **mechanism:** on the votes->STE hybrid, the vote phase uses whitened gradients and the STE phase uses Muon: `--hybrid 0.7:ste --whiten --muon`.
- **train.py:** all three flags pooled separately (MILL-220 / MILL-230 / MILL-124 family); combination new
- **mode:** process — FULL TRIAL ONLY per the candidate file's cost line: never probe-eligible; enters only by a human's word. The named flag is not in train.py yet, so screen.py defers this entry until the flag lands in any case
- **prediction:** whitening and Muon are the same idea (orthogonalize the update geometry) expressed for the two trainer families; running them in their respective phases tests whether update-geometry is the hybrid's binding constraint.
- **status:** queued
```mill
id: A-068
mode: process
run: --arm layered_half --rope --hybrid 0.7:ste --whiten --muon
```

### A-069 · Verify-flips with Fisher-ranked queue
- **source:** idea-mining stream A (CANDIDATES-A.md), family S6 — combinations of known-good or neutral elements
- **mechanism:** `--verify-flips 200 --share 0.001` semantics merged: the periodic verification budget is spent on the Fisher-ranked candidate queue instead of merely the nearest-to-threshold weights.
- **train.py:** combination of pooled MILL-231 and MILL-229 mechanics; new joint flag `--verify-fisher`
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** verify-flips picks candidates by counter proximity (cheap, myopic); Fisher ranking picks by estimated loss effect. Verification is the scarce resource — aiming it better is the obvious joint upgrade.
- **status:** queued
```mill
id: A-069
mode: process
run: --arm layered_half --rope --verify-fisher
```

### A-070 · Modal readout during a vote polish phase
- **source:** idea-mining stream A (CANDIDATES-A.md), family S6 — combinations of known-good or neutral elements
- **mechanism:** after the standard layered run, a 25% polish phase at V=64 with modal readout taken over the polish checkpoints: cold vote polish + `--modal 5` restricted to the polish window.
- **train.py:** new flag `--polish-votes 0.25` combining pooled pieces (polish exists for STE as MILL-132 family; modal for votes as MILL-218 family; the vote-polish is new)
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** Fable's sleep experiment says plain continued training at low rate beat fancier options; the vote analogue — colder votes, modal-read — has never been assembled, and readout-over-polish averages exactly the most-settled states.
- **status:** queued
```mill
id: A-070
mode: process
run: --arm layered_half --rope --polish-votes 0.25 --modal 5
```

### A-071 · RoPE base 1000 + partial RoPE 0.5
- **source:** idea-mining stream A (CANDIDATES-A.md), family S6 — combinations of known-good or neutral elements
- **mechanism:** `--rope-base 1000 --rope-frac 0.5` — a mid-range base (the pooled grid has 500 and 50000) with half the head dims rotated.
- **train.py:** combination new; base 1000 itself is also unpooled (pooled: MILL-905/906 bases, MILL-133 partial RoPE)
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** base and fraction both reshape the rotation spectrum; at ctx 256 the standard base 10000 leaves the fastest pairs nearly unrotated — a smaller base makes rotation actually engage at lab context lengths, and the fraction hedges the scramble risk.
- **status:** queued
```mill
id: A-071
mode: process
run: --arm layered_half --rope --rope-base 1000 --rope-frac 0.5
```

### A-072 · Thrash freeze 5 + zero-bias 1.5
- **source:** idea-mining stream A (CANDIDATES-A.md), family S6 — combinations of known-good or neutral elements
- **mechanism:** `--freeze 5 --zero-bias 1.5` — stability machinery plus the sparsity prior.
- **train.py:** freeze pooled (MILL-213 family); zero-bias is A-009; combination new
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** freezing stabilizes the weights that oscillate; zero-bias decides WHERE stabilized weights prefer to sit. If sparsity is good, frozen-at-nonzero oscillators are the ones wasting it.
- **status:** queued
```mill
id: A-072
mode: process
run: --arm layered_half --rope --freeze 5 --zero-bias 1.5
```

### F-S7 — Architecture micro-variants (ternary-compatible)

### A-073 · Zero-init output projections
- **source:** idea-mining stream A (CANDIDATES-A.md), family S7 — architecture micro-variants (ternary-compatible)
- **mechanism:** the attention-output and FFN-down ternary states initialize to all zeros, so each block starts as a near-identity residual and votes grow its output structure from nothing.
- **train.py:** new flag `--zero-init-out` in the model builder
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** random-init ternary outputs inject full-strength noise into the residual stream from step 0; zero-init (the ReZero/Fixup insight) lets early training organize around a clean signal — and vote counters, which need consistent evidence, should benefit most.
- **status:** queued
```mill
id: A-073
mode: process
run: --arm layered_half --rope --zero-init-out
```

### A-074 · Depth-scaled residual gains (1/sqrt(2L))
- **source:** idea-mining stream A (CANDIDATES-A.md), family S7 — architecture micro-variants (ternary-compatible)
- **mechanism:** each block's output is scaled by 1/sqrt(2*blocks) before joining the residual stream (DeepNet-style).
- **train.py:** new flag `--deepnet-scale` in Block
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** ternary block outputs have quantized, scale-quantized magnitudes; residual variance growth across blocks is currently unmanaged. This is the norm family's missing member (the pooled norm entries move norms around; none scale the residual contribution).
- **status:** queued
```mill
id: A-074
mode: process
run: --arm layered_half --rope --deepnet-scale
```

### A-075 · Attention logit softcap (tanh, cap 30)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S7 — architecture micro-variants (ternary-compatible)
- **mechanism:** attention logits pass through 30*tanh(logits/30) before the softmax — smooth bounding instead of norming or clipping.
- **train.py:** new flag `--softcap 30` in attention
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** QK-Norm (pooled) renormalizes Q/K; QK-Clip (pooled) rescales after the fact; softcap bounds the logit itself differentiably (Gemma-2's choice) and interacts with gradients during training, not just the forward range. Three different governors — the lab should own all three numbers.
- **status:** queued
```mill
id: A-075
mode: process
run: --arm layered_half --rope --softcap 30
```

### A-076 · Ternary value activations (V path only)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S7 — architecture micro-variants (ternary-compatible)
- **mechanism:** the V projection's OUTPUT activations are quantized to {-1,0,1} x per-head scale before the attention weighted sum (weights and all other activations unchanged, still INT8 elsewhere).
- **train.py:** new flag `--act-ternary-v` in attention
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** attention outputs are convex combinations of value vectors; ternarizing values tests how much of attention's work is routing (which survives) vs content (which degrades). A scoping probe for how far activation ternarization can go on the safest path first.
- **status:** queued
```mill
id: A-076
mode: process
run: --arm layered_half --rope --act-ternary-v
```

### A-077 · Per-head QK scales
- **source:** idea-mining stream A (CANDIDATES-A.md), family S7 — architecture micro-variants (ternary-compatible)
- **mechanism:** Q and K projections get per-HEAD absmean scales instead of per-layer scales.
- **train.py:** new flag `--qk-scale head` in BitLinear usage for qkv
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** heads with different roles develop different magnitude profiles; a single per-layer gamma forces one compromise. This is scale granularity (pooled for whole layers) applied at the granularity attention actually varies at.
- **status:** queued
```mill
id: A-077
mode: process
run: --arm layered_half --rope --qk-scale head
```

### A-078 · Learned per-head attention temperature
- **source:** idea-mining stream A (CANDIDATES-A.md), family S7 — architecture micro-variants (ternary-compatible)
- **mechanism:** each head's logits are divided by a learned FP temperature (init 1.0, AdamW-trained).
- **train.py:** new flag `--attn-temp` in attention
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** ternary QK dot products have a coarse, layer-dependent natural scale; a per-head temperature is the cheapest possible calibration (4 scalars) and the pooled QK entries all constrain the DISTRIBUTION, never the softmax's sharpness directly.
- **status:** queued
```mill
id: A-078
mode: process
run: --arm layered_half --rope --attn-temp
```

### A-079 · Half-gated FFN (ternary gate, FP value path)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S7 — architecture micro-variants (ternary-compatible)
- **mechanism:** FFN becomes gate(x) * value(x) where the gate branch is ternary but the value branch stays FP until the down projection.
- **train.py:** new flag `--ffn halfglu` in Block
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** SwiGLU (pooled as negative control) multiplies TWO coarse branches — the stated objection; half-gating keeps the selection mechanism (which is where GLU gains live) while letting one branch carry full precision, at partial byte cost charged honestly.
- **status:** queued
```mill
id: A-079
mode: process
run: --arm layered_half --rope --ffn halfglu
```

### A-080 · RoPE with the position table REMOVED
- **source:** idea-mining stream A (CANDIDATES-A.md), family S7 — architecture micro-variants (ternary-compatible)
- **mechanism:** rotary on, and the carried `pos` table is deleted from the model entirely (49,152 fewer parameters) instead of carried unused Fable-style.
- **train.py:** new flag `--rope-nopos` in the model builder
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** the ROPE results note explicitly chose to carry the table for compatibility and flagged removal as the untested variant; at lab scale 49K FP parameters is ~3% of the model, and per-byte judging needs this number.
- **status:** queued
```mill
id: A-080
mode: process
run: --arm layered_half --rope --rope-nopos
```

### A-081 · Ternary LM head (embeddings stay FP)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S7 — architecture micro-variants (ternary-compatible)
- **mechanism:** the output head becomes a BitLinear (ternary weights, per-row scales) while the input embedding stays FP and untied-for-this-purpose.
- **train.py:** new flag `--head-ternary` in the model builder
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** the pooled embedding entries price the TIED table; the head and the embedding have opposite jobs (classification geometry vs input representation) and the head is the larger consumer at vocab 4096. Pricing the head alone completes the map.
- **status:** queued
```mill
id: A-081
mode: process
run: --arm layered_half --rope --head-ternary
```

### A-082 · Fixed local pre-mix before block 1
- **source:** idea-mining stream A (CANDIDATES-A.md), family S7 — architecture micro-variants (ternary-compatible)
- **mechanism:** token embeddings pass through a fixed (non-learned) average over positions ±1 before the first block — a zero-parameter local smoothing.
- **train.py:** new flag `--premix` in the model builder
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** the first ternary block sees raw embeddings; a fixed local average gives it bigram-ish context for free, testing whether the first block's ternary capacity is being spent re-deriving local context that a fixed filter supplies.
- **status:** queued
```mill
id: A-082
mode: process
run: --arm layered_half --rope --premix
```

### A-083 · Bigram hash embedding (small FP side table)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S7 — architecture micro-variants (ternary-compatible)
- **mechanism:** an FP embedding of the hashed previous-token pair (512 buckets x dim/4, projected and added) supplements the token embedding.
- **train.py:** new flag `--bigram-emb 512` in the model builder
- **mode:** process — FULL TRIAL ONLY per the candidate file's cost line: never probe-eligible; enters only by a human's word. The named flag is not in train.py yet, so screen.py defers this entry until the flag lands in any case
- **prediction:** embeddings are the FP part of this model and local word-pair statistics are the cheapest predictive signal in prose; if a tiny side table buys loss, it prices where FP bytes earn most — the complement question to A-081.
- **status:** queued
```mill
id: A-083
mode: process
run: --arm layered_half --rope --bigram-emb 512
```

### A-084 · FFN activation clipping at 6
- **source:** idea-mining stream A (CANDIDATES-A.md), family S7 — architecture micro-variants (ternary-compatible)
- **mechanism:** FFN intermediate activations are clipped to [-6, 6] before the down projection's INT8 quantization.
- **train.py:** new flag `--act-clip 6` in Block
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** INT8 absmax quantization is destroyed by rare huge activations (the same outlier story as Hadamard, attacked by truncation instead of rotation); clipping is one line and its loss cost at 6 is measurable, making it the cheapest member of the outlier family to price.
- **status:** queued
```mill
id: A-084
mode: process
run: --arm layered_half --rope --act-clip 6
```

### A-085 · LayerScale on blocks (learnable residual gains, init 0.1)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S7 — architecture micro-variants (ternary-compatible)
- **mechanism:** each sublayer output is multiplied by a learned per-channel FP gain initialized at 0.1.
- **train.py:** new flag `--layerscale` in Block
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** A-074 fixes the gain by formula; LayerScale learns it — together they test whether residual-stream budgeting matters for ternary blocks and whether the right budget is learnable at this scale.
- **status:** queued
```mill
id: A-085
mode: process
run: --arm layered_half --rope --layerscale
```

### A-086 · QK-Norm AFTER RoPE (placement variant)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S7 — architecture micro-variants (ternary-compatible)
- **mechanism:** RMSNorm applied to q,k after the rotary rotation instead of before it.
- **train.py:** new flag `--qk-norm-post`
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** the pooled QK-Norm specifies pre-RoPE placement; rotation preserves norms per pair but redistributes them across dims, so post-RoPE norming constrains the quantities the softmax actually sees. Placement was decisive for RoPE itself in this lab. Stream A rank 12.
- **status:** queued
```mill
id: A-086
mode: process
run: --arm layered_half --rope --qk-norm-post
```

### A-087 · Rotary on V (values rotated too)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S7 — architecture micro-variants (ternary-compatible)
- **mechanism:** the rotary rotation is applied to v as well as q,k.
- **train.py:** new flag `--rope-v`
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** almost certainly a falsification probe: rotating values should scramble content — but 'should' is doing the work in that sentence, the cost is one probe, and a surprise here would rewrite the lab's understanding of what rotary contributes.
- **status:** queued
```mill
id: A-087
mode: process
run: --arm layered_half --rope --rope-v
```

### A-088 · Head dim 32 x 6 heads
- **source:** idea-mining stream A (CANDIDATES-A.md), family S7 — architecture micro-variants (ternary-compatible)
- **mechanism:** attention restructured to 6 heads of dim 32 (from 4 of 48), same total width.
- **train.py:** new flag `--head-dim 32` in the model builder
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** pooled head-count entries (2/8) keep the model dim and change head dim implicitly the other way; this point fills the geometry grid between them and tests whether per-head dim (rotation pairs: 16 vs 24) matters to ternary QK quality.
- **status:** queued
```mill
id: A-088
mode: process
run: --arm layered_half --rope --head-dim 32
```

### A-089 · Context 512 at the chassis shape
- **source:** idea-mining stream A (CANDIDATES-A.md), family S7 — architecture micro-variants (ternary-compatible)
- **mechanism:** the chassis trained and evaluated at ctx 512 instead of 256 (nothing else changes).
- **train.py:** `--ctx 512` run configuration (steps will fall at equal minutes; charged)
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** the scale ladder varies WEIGHT count; context length is a different axis and the lab's rope/SWA entries all carry 'expected flat at ctx 256' caveats. This prices the length axis once, honestly, on the champion. Judged per minute.
- **status:** queued
```mill
id: A-089
mode: process
run: --arm layered_half --rope --ctx 512
```

### A-090 · Learned scalar gates on sublayer outputs (init 1)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S7 — architecture micro-variants (ternary-compatible)
- **mechanism:** one FP scalar per sublayer multiplies its output before the residual add, learned by AdamW.
- **train.py:** new flag `--gate-resid` in Block
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** the scalar version of A-085 — 4 scalars per block total. If even scalars move the loss, residual budgeting is a real ternary lever; if not, A-074/A-085's chances fall together. Cheap joint information.
- **status:** queued
```mill
id: A-090
mode: process
run: --arm layered_half --rope --gate-resid
```

### A-091 · Embedding-output norm
- **source:** idea-mining stream A (CANDIDATES-A.md), family S7 — architecture micro-variants (ternary-compatible)
- **mechanism:** an RMSNorm on the token+position embedding sum before block 1.
- **train.py:** new flag `--emb-norm` in the model builder
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** every norm entry in the pool lives inside blocks; the embedding output is the one unnormalized input to the first ternary matmul, and its scale sets the first block's activation-quantization range.
- **status:** queued
```mill
id: A-091
mode: process
run: --arm layered_half --rope --emb-norm
```

### A-092 · No final norm (head reads the raw residual)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S7 — architecture micro-variants (ternary-compatible)
- **mechanism:** the final RMSNorm before the LM head is removed and replaced by a single learned scalar.
- **train.py:** new flag `--no-final-norm` in the model builder
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** a falsification/pricing probe in the Falcon-E spirit (norm removal direction): the final norm is where residual scale meets the FP head; if a scalar suffices, the norm's per-channel freedom was costing or earning something measurable either way.
- **status:** queued
```mill
id: A-092
mode: process
run: --arm layered_half --rope --no-final-norm
```

### F-S8 — Readout, evaluation-side, and state economy

### A-093 · Median readout (last 5 checkpoints)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S8 — readout, evaluation-side, and state economy
- **mechanism:** the shipped state is the per-weight MEDIAN of the last 5 checkpoint states instead of the mode.
- **train.py:** new flag `--median-readout 5` (eval-side; rides any layered run's checkpoints)
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** for two-component layered weights the median and mode differ exactly on the contested weights; the pooled modal readout assumes majority is right, the median is the robust-statistics alternative — one extra eval on the same run prices both.
- **status:** queued
```mill
id: A-093
mode: process
run: --arm layered_half --rope --median-readout 5
```

### A-094 · Average-then-round readout (last 5 checkpoints)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S8 — readout, evaluation-side, and state economy
- **mechanism:** average the last 5 ternary states per weight in FP, then round to the nearest installed level — the closest possible analogue of Fable's running-mean readout for a discrete model.
- **train.py:** new flag `--avg-readout 5` (eval-side; rides any layered run's checkpoints)
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** modal readout (pooled) takes a majority vote of states; averaging preserves HOW contested each weight was (a 3-2 split rounds differently from 5-0). Fable's proven readout is an average, not a vote — this is its faithful discrete translation, and it has not been run. Stream A rank 4.
- **status:** queued
```mill
id: A-094
mode: process
run: --arm layered_half --rope --avg-readout 5
```

### A-095 · Best-checkpoint readout (selection upper bound)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S8 — readout, evaluation-side, and state economy
- **mechanism:** evaluate held loss at each of the last 5 checkpoints and report the best, as a diagnostic only.
- **train.py:** new flag `--best-ckpt` (eval-side)
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** prices the ceiling of ALL readout games (modal/median/average) before the mill invests in them: if best-ckpt ≈ final state, readout variance is small and the whole family drops in priority; if the gap is large, readout is a real lever. Methodological, one eval pass.
- **status:** queued
```mill
id: A-095
mode: process
run: --arm layered_half --rope --best-ckpt
```

### A-096 · int8 counters at V=16 (state-halved hot point)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S8 — readout, evaluation-side, and state economy
- **mechanism:** the V=16 point of the pooled threshold grid, but with counter width explicitly cut to int8 (the grid runs the standard width) — mechanism state per weight halves vs the int16 path.
- **train.py:** `--votes 16 --counter-w 8` on Plain
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** judged per byte of mechanism state, a slightly-worse-but-half-state arm can win the lab's actual objective (the vote counter's whole claim is state economy). The grid measures loss; this measures the loss/state trade at the hot end.
- **status:** queued
```mill
id: A-096
mode: process
run: --arm plain --rope --votes 16 --counter-w 8
```

### A-097 · SGD-momentum for the shared parts (no AdamW)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S8 — readout, evaluation-side, and state economy
- **mechanism:** embeddings, norms, and scales train with plain momentum SGD (lr tuned to 3e-2, momentum 0.9) instead of AdamW in the vote arms.
- **train.py:** new flag `--opt sgd` on Direct/Layered
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** AdamW's per-parameter adaptivity is 8 B/param of state the vote story never accounts for; if momentum-SGD matches it, the direct trainer's true state advantage over STE grows — a verdict about the mechanism's honesty, priced in one probe.
- **status:** queued
```mill
id: A-097
mode: process
run: --arm layered_half --rope --opt sgd
```

### A-098 · Weight decay 0.01 on the shared parts (vote arms)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S8 — readout, evaluation-side, and state economy
- **mechanism:** AdamW weight decay set to 0.01 for the non-ternary parts of the vote trainers (they have always run wd=0).
- **train.py:** new flag `--opt-wd 0.01` on Direct/Layered
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** the STE recipe grid (pooled) varies wd on the STE chassis; the winning family's own recipe cell is empty. In a model whose ternary weights can't decay, the FP parts' decay shapes everything the ternary side must fit. Stream A rank 7.
- **status:** queued
```mill
id: A-098
mode: process
run: --arm layered_half --rope --opt-wd 0.01
```

### A-099 · AdamW betas (0.9, 0.99) for the shared parts
- **source:** idea-mining stream A (CANDIDATES-A.md), family S8 — readout, evaluation-side, and state economy
- **mechanism:** the second beta rises from the lab-standard 0.95 to 0.99 in the vote arms' AdamW.
- **train.py:** new flag `--betas 0.9,0.99`
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** beta2=0.95 was inherited from Fable's Direct defaults and never varied on ANY arm in the lab; with ~160-step runs, beta2 sets the effective averaging window of the second moment (≈20 steps at 0.95 vs ≈100 at 0.99) — at this horizon that is a materially different optimizer, hiding inside a 'default'. Stream A rank 9.
- **status:** queued
```mill
id: A-099
mode: process
run: --arm layered_half --rope --betas 0.9,0.99
```

### A-100 · Gradient accumulation x2 for votes (effective batch 64)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S8 — readout, evaluation-side, and state economy
- **mechanism:** two micro-batches accumulate before each optimizer/vote step — effective batch 64 reached by accumulation rather than by batch size.
- **train.py:** new flag `--accum 2` in the training loop
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** the pooled batch grid (MILL-1201..1203) changes batch size directly, which changes per-step gradient noise AND step count together; accumulation changes the vote evidence per count while holding micro-batch statistics fixed — for a counter, evidence-per-count is the operative variable, so these are not the same experiment.
- **status:** queued
```mill
id: A-100
mode: process
run: --arm layered_half --rope --accum 2
```

### F-S9 — Objective-adjacent (token loss stays the objective)

### A-101 · Label smoothing 0.05
- **source:** idea-mining stream A (CANDIDATES-A.md), family S9 — objective-adjacent (token loss stays the objective)
- **mechanism:** the token loss uses 0.05 label smoothing.
- **train.py:** new flag `--ls 0.05` in the loss
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** ternary heads produce coarse logits; smoothing caps the gradient any single confident-wrong token can inject into the vote stream. Never tried on any arm here, one line, and the vote path is exactly where outlier gradients do structural damage.
- **status:** queued
```mill
id: A-101
mode: process
run: --arm layered_half --rope --ls 0.05
```

### A-102 · Z-loss on the head logits (1e-4)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S9 — objective-adjacent (token loss stays the objective)
- **mechanism:** a penalty of 1e-4 * logsumexp^2(logits) added to the loss, keeping logit norms bounded.
- **train.py:** new flag `--zloss 1e-4` in the loss
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** logit growth is the failure mode QK-Clip/MuonClip exist to fight on the attention side; the HEAD side has no governor at all in this lab, and z-loss is the standard one (PaLM lineage). It also stabilizes the loss scale the vote gate's quantiles are computed from.
- **status:** queued
```mill
id: A-102
mode: process
run: --arm layered_half --rope --zloss 1e-4
```

### A-103 · Same-head auxiliary next-next-token loss (weight 0.05)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S9 — objective-adjacent (token loss stays the objective)
- **mechanism:** the existing head also predicts token t+2 from position t, with loss weight 0.05 — no extra head, no extra parameters.
- **train.py:** new flag `--aux-nn 0.05` in the loss
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** pooled MTP entries add a separate head (parameters + plumbing); the same-head version isolates the pure SUPERVISION-density effect (more signal per window for a token-hungry trainer) from the capacity effect, at zero serving cost.
- **status:** queued
```mill
id: A-103
mode: process
run: --arm layered_half --rope --aux-nn 0.05
```

### A-104 · EMA self-teacher on the token loss (mean teacher)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S9 — objective-adjacent (token loss stays the objective)
- **mechanism:** an EMA copy of the model (decay 0.99) produces soft targets on the same windows; loss = CE + 0.5*KL(EMA || student), all in token space.
- **train.py:** new flag `--ema-teach 0.99` in the training loop (EMA state charged, ~7 MB training-only)
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** JEPA is closed — it failed in REPRESENTATION space against a token yardstick. This keeps the teacher idea but stays in token space with the standard loss: it tests whether ANY teacher signal helps votes, without re-opening the JEPA question. Stream A rank 13.
- **status:** queued
```mill
id: A-104
mode: process
run: --arm layered_half --rope --ema-teach 0.99
```

### A-105 · Consistency regularization (two-pass KL, dropout 0.05)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S9 — objective-adjacent (token loss stays the objective)
- **mechanism:** dropout 0.05 is enabled; each batch is forwarded twice with different dropout masks and a KL penalty between the two predictive distributions is added (weight 0.5).
- **train.py:** new flags `--dropout 0.05 --rdrop 0.5` in the model/loss
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** the lab runs dropout nowhere; discrete weights + no dropout is an unusual regularization vacuum. Consistency loss specifically penalizes predictions that hinge on individual activations — the ones INT8 quantization perturbs.
- **status:** queued
```mill
id: A-105
mode: process
run: --arm layered_half --rope --dropout 0.05 --rdrop 0.5
```

### A-106 · Per-token loss clipping (cap 8 nats)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S9 — objective-adjacent (token loss stays the objective)
- **mechanism:** each token's loss contribution is clipped at 8 nats before averaging (gradients flow through the clipped value as a constant beyond the cap).
- **train.py:** new flag `--loss-clip 8` in the loss
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** a handful of catastrophic tokens (rare words, markup) can dominate a batch's gradient and therefore its votes; clipping bounds any token's structural say. Distinct from A-040 (norm clipping per layer) — this acts per token, before aggregation.
- **status:** queued
```mill
id: A-106
mode: process
run: --arm layered_half --rope --loss-clip 8
```

### A-107 · Focal-style token weighting (gamma=0.5, loss-side)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S9 — objective-adjacent (token loss stays the objective)
- **mechanism:** each token's loss is weighted by (1 - p_token)^0.5, down-weighting tokens the model already predicts well — inside the loss, with sampling untouched.
- **train.py:** new flag `--focal 0.5` in the loss
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** failweight (pooled) moves the SAMPLER toward hard windows, changing what the AdamW parts see too; focal weighting moves only the loss geometry, continuously, per token. The pair separates 'see hard examples more' from 'weight hard examples more' — currently conflated.
- **status:** queued
```mill
id: A-107
mode: process
run: --arm layered_half --rope --focal 0.5
```

### A-108 · Attention entropy bonus (1e-3)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S9 — objective-adjacent (token loss stays the objective)
- **mechanism:** a small bonus (+1e-3 x mean attention entropy) added to the loss, discouraging attention collapse onto single positions.
- **train.py:** new flag `--attn-ent 1e-3` in the loss
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** ternary QK logits are coarse, so attention distributions can collapse early and freeze (the votes then train around a dead routing pattern); a tiny entropy pressure keeps routing plastic. The sink/gate entries treat the symptom architecturally; this treats it in the objective.
- **status:** queued
```mill
id: A-108
mode: process
run: --arm layered_half --rope --attn-ent 1e-3
```

### F-S10 — Trainer-level structure: populations, resets, inits

### A-109 · Dual evidence streams (two counters, alternating batches)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S10 — trainer-level structure: populations, resets, inits
- **mechanism:** two independent counters per weight; even batches vote into counter A, odd into counter B; a flip requires BOTH counters past V/2 in the same direction (consensus of two evidence streams over one shared lattice).
- **train.py:** new flag `--dual-vote` on Layered
- **mode:** process — FULL TRIAL ONLY per the candidate file's cost line: never probe-eligible; enters only by a human's word. The named flag is not in train.py yet, so screen.py defers this entry until the flag lands in any case
- **prediction:** a single counter can be stampeded by a correlated run of batches; two streams fed disjoint data that must agree is bagging inside the trainer — variance reduction at the evidence level rather than the readout level.
- **status:** queued
```mill
id: A-109
mode: process
run: --arm layered_half --rope --dual-vote
```

### A-110 · Counter reset at halfway (weights kept)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S10 — trainer-level structure: populations, resets, inits
- **mechanism:** at 50% of the run all counters zero out while the ternary state is untouched — the second half's structure is decided by fresh evidence only.
- **train.py:** new flag `--counter-reset 0.5` on Layered/Direct
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** counters integrate from step 0, so early (near-random-network) evidence still sits in them at the end; a mid-run reset asks whether the first half's evidence is an asset or a contaminant. One flag, and the answer reinterprets every long-run dynamic the lab has recorded.
- **status:** queued
```mill
id: A-110
mode: process
run: --arm layered_half --rope --counter-reset 0.5
```

### A-111 · Dead-weight revival at halfway
- **source:** idea-mining stream A (CANDIDATES-A.md), family S10 — trainer-level structure: populations, resets, inits
- **mechanism:** at 50%, weights sitting at 0 whose |count| < 4 are randomly re-seeded to ±1 (counters zeroed).
- **train.py:** new flag `--revive 0.5` on Layered
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** a weight at 0 with no accumulated evidence is a dead slot — the counter never found a reason to move it, which at init-noise levels means it never got a fair trial. Revival is the population-genetics fix (mutation of the unfit) inside one network.
- **status:** queued
```mill
id: A-111
mode: process
run: --arm layered_half --rope --revive 0.5
```

### A-112 · Scale-only polish for STE (freeze ternary, retrain scales/norms)
- **source:** idea-mining stream A (CANDIDATES-A.md), family S10 — trainer-level structure: populations, resets, inits
- **mechanism:** after a standard ste_half run, the ternary weights freeze and only scales + norms train for 10% extra steps.
- **train.py:** new flag `--scale-polish` on the STE trainer
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** A-037 prices this split for votes; the STE version prices how much of ste_half's table-leading 2.8205 is its scale freedom rather than its weight path — a number that bounds what ANY vote variant can hope to win back.
- **status:** queued
```mill
id: A-112
mode: process
run: --arm ste_half --rope --scale-polish
```

### A-113 · Majority-of-3 inits
- **source:** idea-mining stream A (CANDIDATES-A.md), family S10 — trainer-level structure: populations, resets, inits
- **mechanism:** three random ternary inits are drawn per run and the starting state is their per-weight majority; counters start at 0.
- **train.py:** new flag `--init-majority` in the model builder
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** init variance is a known share of seed variance in this lab's tables; a majority init is the cheapest variance cut available and, if seed spread shrinks, every subsequent comparison in the mill gets sharper for free.
- **status:** queued
```mill
id: A-113
mode: process
run: --arm layered_half --rope --init-majority
```

### A-114 · Histogram-matched init
- **source:** idea-mining stream A (CANDIDATES-A.md), family S10 — trainer-level structure: populations, resets, inits
- **mechanism:** the init ternary state is drawn to match the final state histogram of a trained plain model (~30% zeros / 35% / 35%) instead of the symmetric random split.
- **train.py:** new flag `--init-hist` in the model builder
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** trained nets converge to a characteristic level histogram; starting there skips the phase where votes merely redistribute mass among levels. Tests whether the histogram itself is part of what training 'learns' early.
- **status:** queued
```mill
id: A-114
mode: process
run: --arm layered_half --rope --init-hist
```


## G — Literature mining stream B (merged from CANDIDATES-B.md, 2026-11-12)

31 entries (B-001..B-031) from primary sources only (papers, official repos), each
checked against the pool and the lab's two research docs so nothing already queued
is re-mined. Where an idea changes tokenization, judge in **nats/byte**, not
nats/token. Family 1 (data/tokenizer) was the pool's widest-open territory: zero
entries before this merge. Stream B's strongest: B-001 (a genuine literature gap),
B-017 (removes the probe-vs-trial horizon confound), B-003, B-021, B-031.
Verification flags carried in the entries' source lines: B-019/B-020 are
snippet-level sourcing — VERIFY THE PRIMARY SOURCE BEFORE BUILDING; B-009/B-012 are
2023 and B-018 is 2021 (regime-fit inclusions); B-030 is a 2026 single-source
preprint; B-022's QuaRot facts come via SpinQuant's comparisons (skim the original
before building). Kernel-family entries (B-025..B-029) are kernels-bench arms, not
train.py training flags; they defer until the bench arm exists.

### B-001 · Staged data-mixture ablation for a ternary model
- **source:** literature mining stream B (CANDIDATES-B.md), family 1 — data and tokenizer — SmolLM2 — Allal et al., arXiv:2502.02737, 2025-02-04
- **mechanism:** train in stages with different data mixtures per stage (SmolLM2 ran 4 stages, shifting web/code/math ratios, reserving the best data for the final decay stage).
- **train.py:** new corpus-schedule flag `--mixture staged`: split the harvested corpus into its natural source classes, run the champion chassis on 2-3 stage schedules (e.g. uniform -> HQ-heavy final third) at equal total tokens vs the single-mixture control
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** the 2026-11-12 architecture report explicitly flags that NO ternary-specific data-mixture ablation exists in primary sources — a genuine literature gap, not a re-test. Stream B ranks this among its strongest entries.
- **status:** queued
```mill
id: B-001
mode: process
run: --arm layered_half --rope --mixture staged
```

### B-002 · Tokenizer trained on the exact training mixture
- **source:** literature mining stream B (CANDIDATES-B.md), family 1 — data and tokenizer — SmolLM2, arXiv:2502.02737, 2025-02-04
- **mechanism:** a tokenizer fitted to the actual data mix allocates merges where the training data actually lives, instead of a generic corpus's statistics.
- **train.py:** new tokenizer build flag `--tokenizer refit`: retrain the lab's word-piece vocab on the harvested corpus itself (same vocab size), rebuild corpus.u16, rerun champion; compare in nats/byte (tokenization changed — nats/token is not comparable)
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** data-level, cheap, one-time; the current corpus's tokenizer provenance is inherited, not fitted.
- **status:** queued
```mill
id: B-002
mode: process
run: --arm layered_half --rope --tokenizer refit
```

### B-003 · SuperBPE: superword merges past whitespace
- **source:** literature mining stream B (CANDIDATES-B.md), family 1 — data and tokenizer — SuperBPE — Liu, Hayase, Hofmann, Oh, Smith, Choi, arXiv:2503.13423, 2025-03-17, COLM 2025
- **mechanism:** two-stage tokenizer curriculum — learn normal subwords, then drop whitespace pretokenization and learn cross-word 'superwords' (up to 33% fewer tokens at fixed 200k vocab; +4.0% avg over 30 tasks at 8B, -27% inference compute).
- **train.py:** new tokenizer build flag `--tokenizer super`: add a superword merge stage at lab vocab size, rebuild the corpus, rerun champion at equal BYTES (not equal tokens); judge in nats/byte
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** directly attacks the lab's fixed piece budget: fewer pieces per byte means each 458k-token run sees more actual text. One of stream B's strongest entries.
- **status:** queued
```mill
id: B-003
mode: process
run: --arm layered_half --rope --tokenizer super
```

### B-004 · Byte Latent Transformer (mini-BLT): entropy patches, no vocab
- **source:** literature mining stream B (CANDIDATES-B.md), family 1 — data and tokenizer — BLT — Pagnoni et al., arXiv:2412.09871, 2024-12-16, ACL 2025
- **mechanism:** bytes are grouped into variable-length patches by the entropy of a small auxiliary byte LM; a light local encoder/decoder wraps a latent transformer — no fixed vocabulary, and no large FP embedding table.
- **train.py:** new architecture flag `--arch blt`: smallest viable version — byte input, fixed small patcher (entropy threshold from a tiny byte model), latent Tiny as-is. Compare nats/byte and total bytes vs champion. HONEST NOTE from the candidate file: this is a BUILD, not a flag — the highest-effort entry in family B
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** architecture-level. The payoff case is real: at lab scale the FP embedding table is a large share of model bytes, and BLT deletes it.
- **status:** queued
```mill
id: B-004
mode: process
run: --arm layered_half --rope --arch blt
```

### B-005 · Model-based quality filtering of the harvested corpus (DCLM-style)
- **source:** literature mining stream B (CANDIDATES-B.md), family 1 — data and tokenizer — DCLM — Li et al., arXiv:2406.11794, 2024-06-18, NeurIPS 2024 Datasets & Benchmarks
- **mechanism:** a fastText-style classifier scores documents for instruction-like quality; in DCLM's controlled pools, filtering was THE lever (7B reached 64% MMLU on 2.6T tokens, +6.6 pts at 40% less compute).
- **train.py:** new corpus flag `--corpus-filter dclm`: train a small n-gram classifier to separate the corpus's cleanest slice from the rest, keep the top fraction, rerun champion at equal tokens; sweep keep-fraction as a paired variable (see B-008)
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** data-level, untested territory in the pool; the lab corpus is small and harvested, so its quality distribution is exactly what filtering acts on.
- **status:** queued
```mill
id: B-005
mode: process
run: --arm layered_half --rope --corpus-filter dclm
```

### B-006 · Educational-value filtering (FineWeb-Edu-style)
- **source:** literature mining stream B (CANDIDATES-B.md), family 1 — data and tokenizer — FineWeb / FineWeb-Edu — Penedo et al., arXiv:2406.17557, 2024, NeurIPS 2024 Datasets & Benchmarks
- **mechanism:** a classifier distilled from LLM annotations scores text 0-5 for educational value; keeping >=3 produced a 1.3T-token subset that beat the 15T raw pool at small budgets.
- **train.py:** new corpus flag `--corpus-filter edu`: score the harvested corpus with a small local scorer, keep the top slice, rerun champion at equal tokens; compare against B-005's filter (different scoring target: educational value vs instruction-likeness)
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** two different filters on the same corpus is a clean A/B the pool has no equivalent of.
- **status:** queued
```mill
id: B-006
mode: process
run: --arm layered_half --rope --corpus-filter edu
```

### B-007 · Near-duplicate removal pass in corpus building
- **source:** literature mining stream B (CANDIDATES-B.md), family 1 — data and tokenizer — FineWeb pipeline, arXiv:2406.17557, 2024 (per-snapshot MinHash dedup — their GLOBAL dedup measured worse, so scope of dedup is itself a variable)
- **mechanism:** near-duplicate documents waste a small corpus's budget and inflate memorized spans; MinHash-style dedup removes them.
- **train.py:** new corpus flag `--corpus-dedup minhash`: add a MinHash near-dedup stage to make_corpus.py, rebuild, rerun champion at equal tokens. First measure the corpus's current duplicate rate — it is unmeasured today, so the first deliverable is the number itself
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** cheapest entry in this family; also a hygiene fix independent of the loss result.
- **status:** queued
```mill
id: B-007
mode: process
run: --arm layered_half --rope --corpus-dedup minhash
```

### B-008 · Filter-strength sweep: when filtering stops helping (the caution arm)
- **source:** literature mining stream B (CANDIDATES-B.md), family 1 — data and tokenizer — Mohri et al., 'A Bitter Lesson for Data Filtering,' arXiv:2605.19407, 2026; and Goyal et al., 'Scaling Laws for Data Filtering,' arXiv:2404.07177, 2024
- **mechanism:** in the data-scarce / high-compute regime, aggressive quality filtering can HURT — quality pools decay faster under repetition, and the optimal filter tends toward no filter as compute-per-data rises.
- **train.py:** new sweep flag `--filter-sweep 1.0,0.5,0.25`: run B-005/B-006 at keep-fractions 100% / 50% / 25% with matched total tokens (so smaller pools repeat more). The lab — ~5.92M pieces, many epochs — sits exactly in the regime where the caution bites
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** this is the control that keeps the filtering entries honest; without it, a filter 'win' at one keep-fraction proves little.
- **status:** queued
```mill
id: B-008
mode: process
run: --arm layered_half --rope --filter-sweep 1.0,0.5,0.25
```

### B-009 · Epoch / repetition scaling on a fixed small corpus
- **source:** literature mining stream B (CANDIDATES-B.md), family 1 — data and tokenizer — Muennighoff et al., 'Scaling Data-Constrained Language Models,' arXiv:2305.16264, NeurIPS 2023; JMLR 26, 2025-02. NOTE: 2023 origin — included because the lab's regime makes it first-order and the pool has zero epoch entries
- **mechanism:** up to ~4 epochs of repeated data is nearly as good as fresh data; beyond that returns decay with a measurable effective-data law (R*_D ≈ 15, ~16-epoch half-life), and data-constrained runs should scale epochs slightly faster than parameters.
- **train.py:** new schedule flag `--epochs 4` (representative point; the candidate grids 1 / 2 / 4 / 8 epochs over the fixed corpus at equal total tokens by adjusting steps, plus one arm pairing epoch count with the ~2M ladder rung)
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** data/schedule-level. Directly informs the scale ladder, whose big rungs are token-starved by construction.
- **status:** queued
```mill
id: B-009
mode: process
run: --arm layered_half --rope --epochs 4
```

### B-010 · Rewrite the discards instead of dropping them (REWIRE)
- **source:** literature mining stream B (CANDIDATES-B.md), family 1 — data and tokenizer — REWIRE — Nguyen, Li, Golovneva et al., arXiv:2506.04689, COLM 2025
- **mechanism:** documents a quality filter would discard are REWRITTEN into clean text by a guide model and mixed back with high-quality raw data (+1.0/+1.3/+2.5 pts at 1B/3B/7B on DCLM tasks) — recycling beats discarding when data is scarce.
- **train.py:** new corpus flag `--corpus-rewrite rewire`: take the slice B-005's filter rejects, produce a small rewritten version of it, mix rewrites + kept raw at equal tokens vs both the filtered-only and unfiltered arms. Honest caveat: needs a generator; the lab's own FP models are tiny, so a small externally generated rewrite set is the practical route
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** the opposite arm to filtering — the pair brackets the design space.
- **status:** queued
```mill
id: B-010
mode: process
run: --arm layered_half --rope --corpus-rewrite rewire
```

### B-011 · Small synthetic-textbook slice in the mix (Cosmopedia-style)
- **source:** literature mining stream B (CANDIDATES-B.md), family 1 — data and tokenizer — Cosmopedia v2 (28B tokens of generated textbook/story/code across ~34k topics), as used at 4% of SmolLM2's decay stage, arXiv:2502.02737, 2025; phi 'textbooks' lineage
- **mechanism:** generated, textbook-style text concentrates clean explanatory signal that raw harvested text dilutes.
- **train.py:** new mixture flag `--mix-synth 0.07`: generate or source a small textbook-style set sized to ~5-10% of the corpus, mix in for the final training phase (pairs naturally with B-001's staged schedule), equal tokens vs control
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** distinct from B-010: generation from seed topics vs rewriting real documents. Keep the fraction small — synthetic-heavy mixes are their own failure mode.
- **status:** queued
```mill
id: B-011
mode: process
run: --arm layered_half --rope --mix-synth 0.07
```

### B-012 · Automatic mixture weights from a tiny proxy (DoReMi)
- **source:** literature mining stream B (CANDIDATES-B.md), family 1 — data and tokenizer — DoReMi — Xie et al., arXiv:2305.10429, NeurIPS 2023. NOTE: 2023 — included as the automatic counterpart to B-001's manual stages
- **mechanism:** a small proxy model trained with group-DRO learns per-domain mixture weights that transfer to models ~30x larger (2.6x fewer steps, +6.5 pts in the original).
- **train.py:** new mixture flag `--mixture doremi`: the lab's own Tiny IS proxy-scale — run group-DRO over the harvested corpus's source domains with a small Tiny, take the learned weights, rerun champion with them vs the uniform mix
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** if B-001 shows mixture matters at all for ternary, this is the cheap way to search the mixture space instead of hand-picking stages.
- **status:** queued
```mill
id: B-012
mode: process
run: --arm layered_half --rope --mixture doremi
```

### B-013 · Cautious AdamW on gradient-trained parts
- **source:** literature mining stream B (CANDIDATES-B.md), family 2 — optimizers — Cautious Optimizers — Liang, Chen, Liu, Liu, arXiv:2411.16085, 2024-11-25 (v4 2026-02-15), ICLR 2026
- **mechanism:** one-line mask on any Adam-family update: zero every coordinate where the update disagrees in sign with the current gradient, rescale by 1/mean(mask). Reported 1.47x speedup for C-AdamW on LLaMA-1B with convergence guarantees preserved.
- **train.py:** new optimizer flag `--opt cautious`: apply on the STE trainer's optimizer and on the AdamW that trains shared parts in the vote arms (encoded here on the champion chassis). Near-zero implementation cost (a mask in the step function)
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** needs gradient training (STE latents + shared parts). No interaction with the vote counter itself.
- **status:** queued
```mill
id: B-013
mode: process
run: --arm layered_half --rope --opt cautious
```

### B-014 · Cautious masking translated to votes
- **source:** literature mining stream B (CANDIDATES-B.md), family 2 — optimizers — same paper as B-013 (arXiv:2411.16085), mechanism translated to the vote domain
- **mechanism:** count a weight's incoming votes only while they agree with the counter's accumulated direction; dissenting votes are masked rather than subtracted.
- **train.py:** new flag `--cautious-votes` on Direct/Layered: the counter accumulates agreeing evidence only, flip rule unchanged; probe against plain votes on the champion chassis
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** the only optimizer-family idea here that fits the vote-trainer. Honest note from the candidate file: it is a cousin of Fable's `agree` variant and the pool's sign-agree flip rule (MILL-623 family), but it acts on EVIDENCE ACCUMULATION, not the flip rule.
- **status:** queued
```mill
id: B-014
mode: process
run: --arm layered_half --rope --cautious-votes
```

### B-015 · AdEMAMix for token-hungry runs
- **source:** literature mining stream B (CANDIDATES-B.md), family 2 — optimizers — AdEMAMix — Pagliardini, Ablin, Grangier, arXiv:2409.03137, 2024-09-05, ICLR 2025
- **mechanism:** Adam with two EMAs of the gradient — a fast one (beta≈0.9) and a very slow one (beta up to 0.9999) — mixed into the update; old gradients stay useful for tens of thousands of steps, so a 1.3B model on 101B tokens matched AdamW on 197B, with slower forgetting.
- **train.py:** new optimizer flag `--opt ademamix`: swap in for STE and for shared parts on the longest runs (ladder rungs, multi-epoch arms from B-009), where its long-memory advantage should be largest
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** needs gradient training. Honest tension: AdEMAMix's extra state is exactly what the vote counter exists to avoid — this is an STE-side entry, not a vote-side one.
- **status:** queued
```mill
id: B-015
mode: process
run: --arm layered_half --rope --opt ademamix
```

### B-016 · APOLLO-Mini: tensor-wise optimizer scaling at SGD-level state
- **source:** literature mining stream B (CANDIDATES-B.md), family 2 — optimizers — APOLLO / APOLLO-Mini — Zhu et al., arXiv:2412.05270, 2024-12-06, MLSys 2025
- **mechanism:** AdamW-quality training with the per-coordinate state replaced by structured approximations — channel/tensor-wise learning-rate scaling from low-rank random projections; Mini uses rank-1 tensor-wise scaling at SGD-level memory and composes with weight quantization in their tests.
- **train.py:** new optimizer flag `--opt apollo-mini`: optimizer swap for STE/shared parts; the interesting measurement is held loss at ~1 byte/param of optimizer state vs AdamW's ~8, extending the lab's state-economy comparison from the vote counter to the optimizer itself
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** thematic fit is strong (state economy is the lab's home metric) even though it doesn't touch votes.
- **status:** queued
```mill
id: B-016
mode: process
run: --arm layered_half --rope --opt apollo-mini
```

### B-017 · Schedule-Free training for the mill's arbitrary-budget probes
- **source:** literature mining stream B (CANDIDATES-B.md), family 2 — optimizers — Schedule-Free — Defazio et al., 'The Road Less Scheduled,' arXiv:2405.15682, 2024-05-24, NeurIPS 2024 (won the MLCommons 2024 AlgoPerf self-tuning track); follow-up ScheduleFree+, arXiv:2605.19095, 2026-05-20
- **mechanism:** iterate averaging replaces the LR schedule entirely — no horizon T to set, so a run stopped at any budget is already near its averaged optimum.
- **train.py:** new optimizer flag `--opt schedulefree`: STE arms in the mill run under Schedule-Free AdamW; compare probe rankings against the scheduled runs
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** the real target is methodological: mill probes run 60-90 s while full trials run 8 min, and a horizon-dependent schedule makes probe results a biased predictor of full-trial results. Schedule-Free removes that confound — uniquely valuable to the MILL ITSELF. One of stream B's strongest entries.
- **status:** queued
```mill
id: B-017
mode: process
run: --arm layered_half --rope --opt schedulefree
```

### B-018 · EWGS: discretization-error-scaled gradients for STE
- **source:** literature mining stream B (CANDIDATES-B.md), family 2 — optimizers — EWGS — Lee, Kim, Ham, arXiv:2104.00903, CVPR 2021. NOTE: 2021, outside the stated window — included because it is the canonical STE repair, is absent from both lab docs, and the pool's STE recipe grid never varies the backward pass itself
- **mechanism:** scale each gradient element up or down by the sign agreement between the gradient and the weight's discretization error (w - Q(w)), with the factor adapted from Hessian information — directly attacks the damage STE does where quantization error and gradient fight.
- **train.py:** new backward-pass flag `--ewgs` on the STE trainer: EWGS backward scaling on BitLinear weights only, same recipe otherwise (encoded on ste_half). A second, vote-side arm exists (weight votes by discretization error rather than |g|) if the first shows signal
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** needs gradient training (a backward-pass change, not an optimizer swap).
- **status:** queued
```mill
id: B-018
mode: process
run: --arm ste_half --rope --ewgs
```

### B-019 · Adam-mini: block-wise second moments
- **source:** literature mining stream B (CANDIDATES-B.md), family 2 — optimizers — Adam-mini — Zhang et al., 2024 (encountered via the APOLLO paper's discussion). **VERIFY PRIMARY SOURCE BEFORE BUILDING: snippet-level sourcing only — confirm the primary paper first (per CANDIDATES-B flags summary)**
- **mechanism:** replace per-coordinate second moments with one value per parameter block (per attention head, per neuron block), keeping Adam-like quality at much lower state.
- **train.py:** new optimizer flag `--opt adam-mini` — IF VERIFIED: optimizer swap for STE/shared parts, same state-economy framing as B-016; the two entries are alternative points on the same dial and should race
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** needs gradient training. Deferred additionally on the verification note in the source line: do not build until the primary paper is confirmed.
- **status:** queued
```mill
id: B-019
mode: process
run: --arm layered_half --rope --opt adam-mini
```

### B-020 · SCALE: column-normalized SGD with last-layer momentum
- **source:** literature mining stream B (CANDIDATES-B.md), family 2 — optimizers — SCALE — Glentis et al., 2025-06-20. **VERIFY PRIMARY SOURCE BEFORE BUILDING: snippet-level sourcing — confirm the primary paper first (per CANDIDATES-B flags summary)**
- **mechanism:** SGD with per-column gradient normalization plus momentum only on the last layer reportedly matches/beats Adam at 35-45% of the memory on LLaMA 60M-1B.
- **train.py:** new optimizer flag `--opt scale-sgd` — IF VERIFIED: a near-zero-state gradient baseline for STE (encoded on ste_half)
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** the control that tells the lab how much of STE's quality is Adam and how much is the latent weights themselves. Deferred additionally on the verification note in the source line.
- **status:** queued
```mill
id: B-020
mode: process
run: --arm ste_half --rope --opt scale-sgd
```

### B-021 · SpinQuant: LEARNED rotations before ternarization
- **source:** literature mining stream B (CANDIDATES-B.md), family 3 — rotations: learned and online — SpinQuant — Liu et al., arXiv:2405.16406, 2024-05-26 (v4 2025-02-20), ICLR 2025. Official repo: facebookresearch/SpinQuant
- **mechanism:** the orthogonal rotations that spread outliers are LEARNED (Cayley-parameterized SGD) instead of random/fixed; the input-side rotation folds into the weights at zero runtime cost. Random rotations varied by up to 13 points in their tests; learned ones cut the remaining W4A4 gap to FP to 2.9 pts and beat fixed-rotation QuaRot's gap by up to 45.1%.
- **train.py:** new flag `--spinquant`: short gradient stage that learns one rotation per BitLinear input on the champion chassis, fold it in, then run the vote-trainer as usual on the rotated weights
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** needs gradient training for the rotation-fitting stage only; the vote-trainer then runs unchanged. Distinct from the pool's MILL-129 (BitNet v2's FIXED Hadamard at two sites) — learned-vs-fixed is the variable. One of stream B's strongest entries.
- **status:** queued
```mill
id: B-021
mode: process
run: --arm layered_half --rope --spinquant
```

### B-022 · QuaRot placement: rotations through the residual stream + online Q/K rotation
- **source:** literature mining stream B (CANDIDATES-B.md), family 3 — rotations: learned and online — QuaRot — Ashkboos et al., arXiv:2404.00456, Apr 2024, NeurIPS 2024. NOTE: facts here come via the SpinQuant paper's comparisons and survey snippets rather than a full read of the QuaRot paper — solid, but a skim of the original is cheap insurance before building
- **mechanism:** randomized Hadamard rotations are pushed through the WHOLE model including the residual stream (folded into adjacent weights), with an online Hadamard applied at the FFN down-projection input and to Q/K after RoPE — making every quantization site outlier-free rather than only the worst projections.
- **train.py:** new flag `--quarot-full`: fixed-rotation arm with QuaRot's full placement (residual-stream folding + post-RoPE Q/K rotation) on the champion chassis, vs MILL-129's two-site placement
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** fits the vote-trainer (rotations are fixed and folded; training is untouched).
- **status:** queued
```mill
id: B-022
mode: process
run: --arm layered_half --rope --quarot-full
```

### B-023 · Sigmoid attention (drop softmax entirely)
- **source:** literature mining stream B (CANDIDATES-B.md), family 4 — attention forms that tolerate coarse logits — Ramapuram et al. (Apple), 'Theory, Analysis, and Best Practices for Sigmoid Self-Attention,' arXiv:2409.04431, ICLR 2025. Code: github.com/apple/ml-sigmoid-attention
- **mechanism:** replace row-wise softmax with element-wise sigmoid plus a -log(n) bias and normalization companions (QK-norm, LayerScale in their recipe). No sum-to-1 competition: each logit is judged on its own, attention sinks disappear by construction, and their FlashSigmoid kernel ran 17% faster than FlashAttention-2.
- **train.py:** new attention flag `--attn sigmoid`: sigmoid + -log n bias, with and without the pool's QK-norm, champion chassis, standard probe -> full trial path
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** architecture-level; trainer-agnostic (votes or STE). The lab-specific hypothesis: softmax's winner-take-all sharpening amplifies exactly the logit noise ternary Q/K projections produce; sigmoid's independent gating should degrade more gracefully. Distinct from the pool's gated attention (which keeps softmax and gates the OUTPUT).
- **status:** queued
```mill
id: B-023
mode: process
run: --arm layered_half --rope --attn sigmoid
```

### B-024 · Differential attention (subtract a second softmax map)
- **source:** literature mining stream B (CANDIDATES-B.md), family 4 — attention forms that tolerate coarse logits — Ye et al. (Microsoft Research / Tsinghua), 'Differential Transformer,' arXiv:2410.05258, Oct 2024, ICLR 2025. Code: microsoft/unilm, Diff-Transformer
- **mechanism:** each head computes two softmax maps from split Q/K halves and subtracts them (scaled by a learnable lambda): common-mode attention noise cancels, relevant context is amplified (attention SNR 0.31 vs 0.03 reported); matched Transformer quality at ~65% of the parameters or tokens, with reduced activation outliers.
- **train.py:** new attention flag `--attn diff`: diff-attention on the Tiny at equal parameter count (halved head dim, paired maps), champion chassis. Logit/outlier reduction is measurable directly in the lab's activation instrumentation
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** architecture-level; trainer-agnostic. Doubled softmax cost at lab context lengths (256) is negligible. The outlier-reduction claim is the quantization-relevant part — fewer activation outliers is precisely what 8-bit activation quantizers need.
- **status:** queued
```mill
id: B-024
mode: process
run: --arm layered_half --rope --attn diff
```

### B-025 · T-MAC: bit-plane LUT matmul (look up by bits, never dequantize)
- **source:** literature mining stream B (CANDIDATES-B.md), family 5 — CPU inference kernels — T-MAC — Wei et al., arXiv:2407.00088, 2024-06-25, EuroSys 2025. Repo: github.com/microsoft/T-MAC
- **mechanism:** mixed-precision GEMM done with lookup tables over BIT PLANES of the weights — no dequantization step, and cost scales linearly with weight bit-width. Reported up to 4x throughput and -70% energy vs llama.cpp; BitNet-b1.58-3B at 30 tok/s on 1 core, 71 tok/s on 8 cores (M2 Ultra).
- **train.py:** kernel-bench flag `--kernel-bench tmac`: feed its bit-plane decomposition into the kernels stream's own bench (kernels/bench_matmul.py) as a third arm beside direct and TL-style LUT — ternary weights as sign-plane + magnitude-plane tables against int8 activations. This is a KERNELS-bench entry, not a train.py training flag; it defers until the kernels bench arm exists
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** kernel-level. Distinct from bitnet.cpp's TL1/TL2 (already in the pool's background): T-MAC's per-bit-plane tables generalize the LUT idea and are the current CPU reference point to beat or adopt.
- **status:** queued
```mill
id: B-025
mode: process
run: --arm layered_half --rope --kernel-bench tmac
```

### B-026 · TEAL: training-free activation sparsity at decode
- **source:** literature mining stream B (CANDIDATES-B.md), family 5 — CPU inference kernels — TEAL — Liu et al., arXiv:2408.14690, 2024-08-28, ICLR 2025
- **mechanism:** zero out activations below a per-matrix magnitude threshold at inference — 40-50% sparsity across ALL matrices (not just FFN gates), 1.53x/1.8x decode speedups at 40%/50% sparsity in their tests, no training or calibration set required; composes with weight quantization.
- **train.py:** kernel-bench flag `--decode-sparsity teal`: in the lab's decode bench, threshold-sparsify inputs to each ternary GEMV and skip the corresponding weight columns; measure the accuracy/speed frontier at several thresholds on a trained champion. Decode-bench entry, not a train.py training flag
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** kernel-level. Composes with the chassis's ReLU^2 zeros (structural; TEAL's are threshold-induced and apply at sites ReLU^2 doesn't touch). Honest note: published gains are batch-1 GPU decode — the CPU payoff must be re-measured in the lab's own bench, and only counts with a column-skip kernel behind it.
- **status:** queued
```mill
id: B-026
mode: process
run: --arm layered_half --rope --decode-sparsity teal
```

### B-027 · PowerInfer-2: predicted hot/cold neuron scheduling
- **source:** literature mining stream B (CANDIDATES-B.md), family 5 — CPU inference kernels — PowerInfer-2 — Xue et al., arXiv:2406.06282, 2024-06-10, MobiCom '24
- **mechanism:** activation sparsity is PREDICTED ahead of time (neuron-cluster abstraction) and the compute schedule is built around the prediction — hot neurons resident and dense, cold neurons handled sparsely — rather than discovered after the fact (up to 27.8x vs llama.cpp on one phone workload; 47B at 11.68 tok/s).
- **train.py:** kernel-bench flag `--decode-predict powerinfer`: at lab scale the transferable piece is cluster-level activation prediction — profile a trained champion's FFN activation patterns, test whether a cheap predictor can name the active set before the GEMV runs. Decode-bench entry, not a train.py training flag
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** kernel/systems-level. HONEST WEAK-FIT NOTE from the candidate file: a <2M-weight model is cache-resident, so PowerInfer-2's I/O pipelining — its main win — doesn't transfer; only the prediction idea does, and it races B-026's simpler thresholding for the same prize.
- **status:** queued
```mill
id: B-027
mode: process
run: --arm layered_half --rope --decode-predict powerinfer
```

### B-028 · Ladder/BitBLAS: offline weight-layout transformation as the kernel trick
- **source:** literature mining stream B (CANDIDATES-B.md), family 5 — CPU inference kernels — Ladder — Wang et al., OSDI '24; microsoft/BitBLAS repo (first W_INT2A_INT8 GEMV/GEMM built for BitNet-b1.58; W_INT1A_INT8 up to 8.8x vs FP16 baselines on A100)
- **mechanism:** instead of writing a smarter runtime kernel, TRANSFORM THE WEIGHTS OFFLINE (interleave/permute into the layout the hardware consumes) so the runtime operation becomes trivial.
- **train.py:** kernel-bench flag `--weight-layout ladder`: apply the principle on CPU — pre-permute the lab's packed ternary weights into exactly the order the lab's fastest kernel consumes, so inference does zero unpacking or shuffling at run time. Feeds the same kernel bench as B-025
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** kernel-level — with the honest caveat that the library itself is GPU-only and does not run on the lab's CPU. What transfers is the layout principle.
- **status:** queued
```mill
id: B-028
mode: process
run: --arm layered_half --rope --weight-layout ladder
```

### B-029 · FLUTE-style offline restructuring for LUT kernels
- **source:** literature mining stream B (CANDIDATES-B.md), family 5 — CPU inference kernels — FLUTE — Guo et al., arXiv:2407.10960, 2024-07-15, Findings of EMNLP 2024
- **mechanism:** a flexible LUT engine that restructures weights OFFLINE to minimize unpacking cost and duplicates lookup tables against the actual bandwidth bottleneck (2-4x GEMM at batch <32, 1.5-2x end-to-end in their GPU tests).
- **train.py:** kernel-bench flag `--weight-layout flute`: same bench as B-025/B-028 — test whether a restructured/duplicated table layout beats the naive one for the lab's ternary x int8 GEMV at batch 1
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** kernel-level, GPU-origin like B-028 — included as a DESIGN PRINCIPLE for the CPU LUT family (T-MAC line), not as a port. The candidate file itself flags this as the one to drop first if the kernels stream judges two GPU-principle entries one too many; kept here for completeness of the merge.
- **status:** queued
```mill
id: B-029
mode: process
run: --arm layered_half --rope --weight-layout flute
```

### B-030 · Sparse-BitNet: joint 1.58-bit + N:M structured sparsity
- **source:** literature mining stream B (CANDIDATES-B.md), family 5 — CPU inference kernels — Sparse-BitNet, arXiv:2603.05168, 2026. NOTE: preprint, single-source — treat numbers as unverified until replicated
- **mechanism:** train 1.58-bit quantization and dynamic N:M semi-structured weight sparsity in one stable framework; ternary weights degrade LESS than BF16 at equal sparsity, and a custom sparse tensor core converts the regular zero pattern into real speed (~1.30x).
- **train.py:** new flag `--nm-sparsity 2:4`: two arms — (a) gradient-side: N:M mask constraint during STE training at 2:4 and 4:8; (b) vote-side (speculative): restrict vote accumulation/flips to within N:M blocks so the resulting zero pattern is block-regular by construction. Encoded on the champion chassis; arm (a) re-encodes on ste_half when built
- **mode:** process — isolated train.py subprocess (code-path change); the named flag is not in train.py yet, so screen.py defers this entry until the flag lands
- **prediction:** the durable idea either way: make the zero structure REGULAR so skipping it is predictable — ~42% of ternary weights are already zero, just irregularly. (a) needs gradient training today; (b) fits the vote-trainer but is a translation, not a replication.
- **status:** queued
```mill
id: B-030
mode: process
run: --arm layered_half --rope --nm-sparsity 2:4
```

### B-031 · Fit the lab's results to the precision scaling law
- **source:** literature mining stream B (CANDIDATES-B.md), family 6 — measurement / planning — Kumar et al., 'Scaling Laws for Precision,' arXiv:2411.04330, 2024-11-07, ICLR 2025 (law fitted on 465 runs up to 1.7B params / 26B tokens)
- **mechanism:** low training precision acts as a REDUCED EFFECTIVE PARAMETER COUNT, and post-training quantization degradation grows with the tokens-per-parameter ratio — overtraining a small model makes it harder to quantize after the fact.
- **train.py:** analysis-only flag `--precision-law-fit`: NO new training — fit the lab's existing ladder + vote/STE results to the effective-parameter form and predict (a) whether the votes-vs-STE gap closes or widens at the ~12M+ rungs, and (b) the token budget at which convert-late (FP-then-ternarize) stops being viable. Check predictions against the next ladder rungs as they land
- **mode:** process — ANALYSIS entry (no training run): it defers until the fitting script lands, and it prices several queued arms before the mill spends probes on them
- **prediction:** cheap (analysis only) and it prices several queued arms before the mill spends probes on them. One of stream B's strongest entries.
- **status:** queued
```mill
id: B-031
mode: process
run: --arm layered_half --rope --precision-law-fit
```


## H — Second-order candidates (merged from CANDIDATES-C.md, 2026-11-12)

27 entries transplanted VERBATIM from CANDIDATES-C.md (mill-expansion department:
coordinator + four specialists). Family A: the complete remainder of the trainers
{plain, layered, STE} x sizes {half, full, 2M, 10M} x rotary grid — all config-only
with existing flags, all sweep, all queued now. NOTE: C-A03 is also queued as a
ride-along in run_scale_ladder.py — merge the record, don't double-run it. Family B:
one-gene champion mutations; `--opt-lr` / `--opt-wd` / `--betas` are the pool's own
flag names (one implementation serves MILL-304/305, A-098/A-099, C-B01..04/07..09);
batch points C-B05/C-B06 are sweep-runnable today. Family C: kernel-informed
variants, ALL status `pending-kernel-results` — they must NOT be wired or probed
until kernels/RESULTS-KERNELS.md lands and passes the mechanical flip protocol
summarised after C-C06 (full protocol text: CANDIDATES-C.md). Coordinator's top 10:
C-A01, C-B04, C-A02, C-B07, C-A03, C-B06, C-C04 (pending), C-B08, C-A08, C-C01
(pending). Premise correction carried from the candidate file: QK-Norm / per-channel
scales / gated attention are UNTESTED research-ranked items (MILL-101+), not
confirmed winners; Family A therefore uses only MEASURED elements.

### H-A — Combinations of measured elements (the complete remainder of the grid)

### C-A01 · STE at the 2M ladder rung, with rotary
- **source:** combination of measured elements (STE: `ste_half` 2.8205 ± 0.0069, best quality in RESULTS-HALF-CONTROL-2026-11-12, and `ste` 2.9952 in RESULTS-2026-11-11; scale2m rung + rotary: `layered_rope_scale2m` 3.2745 ± 0.0119, 3 seeds × 56 steps, runs.jsonl)
- **mechanism:** The gradient trainer rides the one fully-measured ladder rung with rotary. At 56 fixed steps there is no steps-per-minute confound — this is the cleanest per-step trainer comparison the lab has never had above half size.
- **train.py:** no change; existing flags only — `--arm ste --rope --dim 288 --layers-n 2`. Full-trial form is ladder format: add `--steps 56 --minutes 12 --tag scale2m` (recorded as `ste_rope_scale2m`, mirroring run_scale_ladder.py). STE state at this rung: 23,887,872 B.
- **mode:** sweep — config-only via existing flags; runs in mill/sweep_probe.py
- **prediction:** At probe scale (75 s, time-boxed) expect it to beat the layered-rung direction but read noisy; at ladder format expect held ~3.15–3.22, i.e. −0.05..−0.12 vs the rung's 3.2745 — the STE-vs-layered gap at equal steps was 0.0785 at half size (2.8205 vs 2.8990, step counts overlapping), and rotary is already in both sides of this comparison.
- **status:** queued
```mill
id: C-A01
mode: sweep
run: --arm ste --rope --dim 288 --layers-n 2
```

### C-A02 · STE at full size, with rotary
- **source:** combination of measured elements (STE full: 2.9952 ± 0.0245, RESULTS-2026-11-11 / RESULTS-HALF-CONTROL-2026-11-12; rotary: −0.0411 on the layered_half chassis, 2.8990 → 2.8580, RESULTS-ROPE-2026-11-11)
- **mechanism:** Rotary has only ever ridden a vote trainer. This tests whether the lab's one confirmed win transfers to the gradient trainer at the size where STE's recipe was actually tuned (lr 3e-3, warmup 200, wd 0.01).
- **train.py:** no change; existing flags only — `--arm ste --rope` (dim 192, 4 blocks defaults reproduce the measured `ste` arm exactly). STE state 21,233,664 B.
- **mode:** sweep — config-only via existing flags; runs in mill/sweep_probe.py
- **prediction:** −0.02..−0.05 vs the `ste` arm's 2.9952 at full format (rotary's vote-side gain was 0.0411 with no step confound); at probe scale the same direction, smaller and noisier because the 4-block arm takes few steps in 75 s. A flat result is also valuable: it would make rotary a vote-trainer-specific win.
- **status:** queued
```mill
id: C-A02
mode: sweep
run: --arm ste --rope
```

### C-A03 · Plain votes at the 2M ladder rung, with rotary
- **source:** combination of measured elements (plain votes: `plain_half` 2.9010 vs `layered_half` 2.8990 — equal within 0.0020, RESULTS-HALF-CONTROL-2026-11-12; scale2m rung + rotary: `layered_rope_scale2m` 3.2745 ± 0.0119, runs.jsonl)
- **mechanism:** The single-component trainer on the measured rung. If plain ties layered at scale as it did at half size, the rung's result is available at half the mechanism state (2,488,320 B vs 4,976,640 B). NOTE: already queued as the ride-along in run_scale_ladder.py — merge, don't duplicate the run.
- **train.py:** no change; existing flags only — `--arm plain --rope --dim 288 --layers-n 2`. Full-trial form is ladder format: add `--steps 56 --minutes 12 --tag scale2m` (recorded as `plain_rope_scale2m`).
- **mode:** sweep — config-only via existing flags; runs in mill/sweep_probe.py
- **prediction:** Held within ±0.03 of the rung's 3.2745 at ladder format — the half-control showed levels earn nothing at equal size/steps (gap 0.0020, sign flips per seed), and nothing about dim 288×2 should change that. The win condition is a tie at half the state, judged per byte.
- **status:** queued
```mill
id: C-A03
mode: sweep
run: --arm plain --rope --dim 288 --layers-n 2
```

### C-A04 · Plain votes at full size, with rotary
- **source:** combination of measured elements (plain full: 3.0743 ± 0.0316, RESULTS-2026-11-11; rotary: −0.0411 on layered_half, RESULTS-ROPE-2026-11-11)
- **mechanism:** Completes rotary × plain votes (the half-size cross is already pooled as MILL-1901). Tests whether rotary's gain survives at the size where plain votes take only ~115–124 steps in 8 minutes.
- **train.py:** no change; existing flags only — `--arm plain --rope` (defaults reproduce the measured `plain` arm). State 2,211,840 B.
- **mode:** sweep — config-only via existing flags; runs in mill/sweep_probe.py
- **prediction:** −0.02..−0.05 vs 3.0743 at full format; at probe scale expect a smaller, noisier gain in the same direction (fewer steps per probe at full size). If the gain vanishes here but holds at half, rotary's value is step-count-dependent — a real finding either way.
- **status:** queued
```mill
id: C-A04
mode: sweep
run: --arm plain --rope
```

### C-A05 · Layered votes at the 2M ladder rung, NO rotary (rung ablation)
- **source:** combination of measured elements (the rung itself: `layered_rope_scale2m` 3.2745 ± 0.0119 at 56 steps, runs.jsonl; rotary's only measurement is at half size: −0.0411, RESULTS-ROPE-2026-11-11)
- **mechanism:** The exact rung configuration minus `--rope` — the built-in position table returns. This is the control that prices rotary at scale; every other scale entry in this family is read against a rung whose rotary contribution is currently assumed, not measured.
- **train.py:** no change; existing flags only — `--arm layered --dim 288 --layers-n 2` (no `--rope`). Full-trial form: add `--steps 56 --minutes 12 --tag scale2m`.
- **mode:** sweep — config-only via existing flags; runs in mill/sweep_probe.py
- **prediction:** +0.03..+0.06 vs 3.2745 at ladder format (worse without rotary, by roughly the half-size gain); if the gap is ~0, rotary's win does not scale and the ladder's per-byte story needs re-reading.
- **status:** queued
```mill
id: C-A05
mode: sweep
run: --arm layered --dim 288 --layers-n 2
```

### C-A06 · Plain votes at the 2M ladder rung, NO rotary
- **source:** combination of measured elements (plain votes at half/full without rotary: 2.9010 / 3.0743, RESULTS-HALF-CONTROL-2026-11-12 and RESULTS-2026-11-11; scale2m shape: dim 288×2, 1,990,656 ternary weights, runs.jsonl scale records)
- **mechanism:** Plain trainer × ladder size with the position table. Paired with C-A03 it isolates rotary for the plain trainer at scale; paired with C-A05 it isolates trainer (plain vs layered) at scale without rotary.
- **train.py:** no change; existing flags only — `--arm plain --dim 288 --layers-n 2`. Full-trial form: add `--steps 56 --minutes 12 --tag scale2m`. State 2,488,320 B.
- **mode:** sweep — config-only via existing flags; runs in mill/sweep_probe.py
- **prediction:** ~3.30–3.36 at ladder format: the rung's 3.2745 plus rotary's ~0.04, with plain≈layered (0.0020 at half) contributing ~0. Primarily a cell-completing control — its value is making C-A03/C-A05 interpretable.
- **status:** queued
```mill
id: C-A06
mode: sweep
run: --arm plain --dim 288 --layers-n 2
```

### C-A07 · STE at the 2M ladder rung, NO rotary
- **source:** combination of measured elements (STE without rotary at half/full: 2.8205 / 2.9952, RESULTS-HALF-CONTROL-2026-11-12; scale2m shape from runs.jsonl scale records)
- **mechanism:** Completes the 2×2 {STE, layered} × {rotary, table} at the 2M rung with C-A01 and C-A05. Without it, a C-A01 win cannot be split into "STE is better per step" vs "STE uses rotary better."
- **train.py:** no change; existing flags only — `--arm ste --dim 288 --layers-n 2`. Full-trial form: add `--steps 56 --minutes 12 --tag scale2m`. STE state 23,887,872 B.
- **mode:** sweep — config-only via existing flags; runs in mill/sweep_probe.py
- **prediction:** ~3.19–3.27 at ladder format (C-A01's expectation plus rotary's ~0.04). Expected to still beat the layered rung's 3.2745 if the STE per-step advantage is real.
- **status:** queued
```mill
id: C-A07
mode: sweep
run: --arm ste --dim 288 --layers-n 2
```

### C-A08 · STE at the 10M ladder rung, with rotary
- **source:** combination of measured elements (STE: 2.8205 half / 2.9952 full, RESULTS-HALF-CONTROL-2026-11-12; 10M rung + rotary: `layered_rope_scale10m` seed 0 only, 2.9472 at 56 steps, 9,437,184 ternary weights, runs.jsonl)
- **mechanism:** The best-quality trainer at the largest measured size. The 10M rung already showed scale helps at equal tokens (2.9472 vs the 2M rung's 3.2745, albeit n=1); this asks whether STE's per-step advantage survives — or grows — at 9.44M weights.
- **train.py:** no change; existing flags only — `--arm ste --rope --dim 512 --layers-n 3`. Full-trial form is ladder format ONLY: add `--steps 56 --minutes 25 --tag scale10m` (~12 min/seed for the layered rung; STE state 113,246,208 B). A 75 s probe is a smoke/direction read only — it cannot reach 56 steps and must not be verdicted as a rung result.
- **mode:** sweep — config-only via existing flags; runs in mill/sweep_probe.py
- **prediction:** ~2.85–2.92 at ladder format, −0.03..−0.10 vs the rung's single-seed 2.9472 (STE's equal-step advantage was 0.0785 at half size; wider models give STE's latent weights more room, but n=1 comparator means wide error bars).
- **status:** queued
```mill
id: C-A08
mode: sweep
run: --arm ste --rope --dim 512 --layers-n 3
```

### C-A09 · Plain votes at the 10M ladder rung, with rotary
- **source:** combination of measured elements (plain votes: `plain_half` 2.9010 ≈ `layered_half` 2.8990, RESULTS-HALF-CONTROL-2026-11-12; 10M rung: `layered_rope_scale10m` seed 0, 2.9472, runs.jsonl)
- **mechanism:** The state-economy test at the largest measured size: plain at this rung costs 11,796,480 B of mechanism state vs layered's 23,592,960 B. If the half-control's tie repeats at 10M, the levels earn nothing at any measured size.
- **train.py:** no change; existing flags only — `--arm plain --rope --dim 512 --layers-n 3`. Full-trial form is ladder format ONLY: add `--steps 56 --minutes 25 --tag scale10m`. Probe is a smoke read only (see C-A08).
- **mode:** sweep — config-only via existing flags; runs in mill/sweep_probe.py
- **prediction:** Within ±0.04 of 2.9472 at ladder format (tie expected, per the 0.0020 half-size precedent), at half the mechanism state — a per-byte win if it ties, a genuine levels-at-scale finding if it doesn't.
- **status:** queued
```mill
id: C-A09
mode: sweep
run: --arm plain --rope --dim 512 --layers-n 3
```

### C-A10 · Layered votes at the 10M ladder rung, NO rotary (rung ablation)
- **source:** combination of measured elements (the rung: `layered_rope_scale10m` seed 0, 2.9472 at 56 steps, runs.jsonl; rotary gain at half size −0.0411, RESULTS-ROPE-2026-11-11)
- **mechanism:** The 10M analogue of C-A05: prices rotary at the largest measured size, where longer effective capacity might make position handling worth more — or less — than at 0.88M.
- **train.py:** no change; existing flags only — `--arm layered --dim 512 --layers-n 3` (no `--rope`). Full-trial form: add `--steps 56 --minutes 25 --tag scale10m`. Probe is a smoke read only.
- **mode:** sweep — config-only via existing flags; runs in mill/sweep_probe.py
- **prediction:** +0.03..+0.07 vs 2.9472 at ladder format — but the comparator is n=1, so this entry's real deliverable is a paired seed-0 reading, not a mean difference.
- **status:** queued
```mill
id: C-A10
mode: sweep
run: --arm layered --dim 512 --layers-n 3
```

### C-A11 · Plain votes at the 10M ladder rung, NO rotary
- **source:** combination of measured elements (plain votes without rotary: 2.9010 half / 3.0743 full; 10M shape: dim 512×3, 9,437,184 ternary weights, runs.jsonl)
- **mechanism:** Completes plain × 10M: with C-A09 it isolates rotary for plain at 10M; with C-A10 it isolates trainer at 10M without rotary. State 11,796,480 B.
- **train.py:** no change; existing flags only — `--arm plain --dim 512 --layers-n 3`. Full-trial form: add `--steps 56 --minutes 25 --tag scale10m`. Probe is a smoke read only.
- **mode:** sweep — config-only via existing flags; runs in mill/sweep_probe.py
- **prediction:** ~2.98–3.03 at ladder format (rung 2.9472 + rotary's ~0.04 + plain≈layered ~0). Lowest information per minute in the 10M block; included for grid completeness.
- **status:** queued
```mill
id: C-A11
mode: sweep
run: --arm plain --dim 512 --layers-n 3
```

### C-A12 · STE at the 10M ladder rung, NO rotary
- **source:** combination of measured elements (STE without rotary: 2.8205 half / 2.9952 full, RESULTS-HALF-CONTROL-2026-11-12; 10M shape from runs.jsonl)
- **mechanism:** Completes the grid's last cell: with C-A08/C-A10 it finishes the {STE, layered} × {rotary, table} 2×2 at 10M. STE state 113,246,208 B.
- **train.py:** no change; existing flags only — `--arm ste --dim 512 --layers-n 3`. Full-trial form: add `--steps 56 --minutes 25 --tag scale10m`. Probe is a smoke read only.
- **mode:** sweep — config-only via existing flags; runs in mill/sweep_probe.py
- **prediction:** ~2.89–2.96 at ladder format (C-A08's expectation plus rotary's ~0.04). Ranked last: most expensive cell, read against an n=1 comparator, and its information is largely implied once C-A08 and C-A10 land.
- **status:** queued
```mill
id: C-A12
mode: sweep
run: --arm ste --dim 512 --layers-n 3
```

### H-B — Champion mutations (one gene at a time; the completion set)

### C-B01 · AdamW lr -> 5e-4
- **source:** champion mutation grid (gene: opt-lr, champion value: 1e-3)
- **mechanism:** Cold-side interior point of the shared-parts lr curve (pooled: 3e-4, 3e-3; champion: 1e-3). Tests whether 1e-3 is even a local optimum for the FP parts, or whether the curve is flat/monotone through it.
- **train.py:** `--arm layered_half --rope --opt-lr 5e-4` — `--opt-lr` is NOT a CLI flag. One-line pass-through needed in both runners: `Layered(model, lr=a.opt_lr, carry=…, cooldown=…)` (constructor already accepts `lr=`; main() and sweep `run_one()` currently never pass it) + the argparse line in both parsers. Mark mode process.
- **mode:** process
- **prediction:** +0.00..+0.03 at probe scale (FP parts undertrained at short horizon; may invert at full trial). Risk: lr touches only embeddings/norms/scales — the vote path never sees it — so a flat reading bounds the FP parts' share, it does not indict votes.
- **status:** queued
```mill
id: C-B01
mode: process
run: --arm layered_half --rope --opt-lr 5e-4
```

### C-B02 · AdamW lr -> 7e-4
- **source:** champion mutation grid (gene: opt-lr, champion value: 1e-3)
- **mechanism:** Near-champion cold point: with C-B01 this resolves the curve's shape between pooled 3e-4 and the champion — a smooth slope vs a cliff just below 1e-3 read differently (cliff = champion sits on an edge).
- **train.py:** `--arm layered_half --rope --opt-lr 7e-4` — same `--opt-lr` pass-through as C-B01 (constructor arg exists, no CLI flag in either parser). Mark mode process.
- **mode:** process
- **prediction:** ~0 ± 0.02 expected; its value is curve shape, not a win. Same FP-parts-only risk as C-B01.
- **status:** queued
```mill
id: C-B02
mode: process
run: --arm layered_half --rope --opt-lr 7e-4
```

### C-B03 · AdamW lr -> 1.5e-3
- **source:** champion mutation grid (gene: opt-lr, champion value: 1e-3)
- **mechanism:** First hot-side step above the champion: tests whether the shared parts are lr-starved at 1e-3 before jumping to the pooled 3e-3 recipe-matching point (MILL-304).
- **train.py:** `--arm layered_half --rope --opt-lr 1.5e-3` — same `--opt-lr` pass-through as C-B01. Mark mode process.
- **mode:** process
- **prediction:** -0.01..+0.02. Risk: at probe horizon a hotter lr mostly buys faster early fitting of embeddings/scales; a probe win here must be re-read at full trial before it means the recipe was wrong.
- **status:** queued
```mill
id: C-B03
mode: process
run: --arm layered_half --rope --opt-lr 1.5e-3
```

### C-B04 · AdamW lr -> 2e-3
- **source:** champion mutation grid (gene: opt-lr, champion value: 1e-3)
- **mechanism:** Hot-side interior point between champion 1e-3 and pooled 3e-3 (MILL-304): together they trace whether the STE side's 3e-3 advantage (~0.2 there) transfers to the vote arms' shared parts gradually or not at all — the de-confounding question behind every votes-vs-STE comparison in the record.
- **train.py:** `--arm layered_half --rope --opt-lr 2e-3` — same `--opt-lr` pass-through as C-B01. Mark mode process.
- **mode:** process
- **prediction:** -0.02..+0.02; highest-variance lr point (AdamW instability on the log_scale params shows up here first if it exists). Same FP-parts-only risk as C-B01.
- **status:** queued
```mill
id: C-B04
mode: process
run: --arm layered_half --rope --opt-lr 2e-3
```

### C-B05 · batch -> 24
- **source:** champion mutation grid (gene: batch, champion value: 32)
- **mechanism:** Interior cold point of the batch curve (pooled: 16, 64, 128). For a vote trainer batch is a vote-statistics dial: 24 = more steps, noisier per-step gradients, more votes cast per minute. Tests whether the 32→16 direction is monotone or already turning.
- **train.py:** `--arm layered_half --rope --batch 24` — `--batch` is a real CLI flag in train.py AND in sweep_probe.py's parser; runnable in sweep mode today, no code change.
- **mode:** sweep
- **prediction:** ±0.03, direction genuinely uncertain. CONFOUND (not a pure gene effect): at fixed minutes, steps/minute rises and tokens/step falls, so this reads batch+steps+vote-noise together; a --steps-matched companion is required before any promotion.
- **status:** queued
```mill
id: C-B05
mode: sweep
run: --arm layered_half --rope --batch 24
```

### C-B06 · batch -> 48
- **source:** champion mutation grid (gene: batch, champion value: 32)
- **mechanism:** Interior hot point between champion 32 and pooled 64: fewer, cleaner votes per minute. With C-B05 it brackets the champion on the only trainer gene the sweep can move today; if both interiors are flat, the batch curve is a plateau and MILL-1201–1203's extremes are edge effects.
- **train.py:** `--arm layered_half --rope --batch 48` — `--batch` exists in both parsers; sweep-runnable today, no code change.
- **mode:** sweep
- **prediction:** ±0.03. Same confound as C-B05, mirrored: fewer steps/minute at fixed minutes; median-gate statistics also shift with batch size, so the vote stream itself changes, not just its rate.
- **status:** queued
```mill
id: C-B06
mode: sweep
run: --arm layered_half --rope --batch 48
```

### C-B07 · weight_decay -> 0.1
- **source:** champion mutation grid (gene: opt-wd, champion value: 0.0)
- **mechanism:** The strong-dose point for a dial never tried alone on this chassis (A-098 proposes only 0.01; the round-2 cooldown's wd component multiplied base_wd = 0.0 and was a no-op). At 0.1 the question becomes binary: if even this is flat, wd is a dead dial on the vote chassis; if it moves, dose matters and 0.01 is worth its probe.
- **train.py:** `--arm layered_half --rope --opt-wd 0.1` — NOT reachable today: Layered has NO wd constructor arg (AdamW `weight_decay=0.0` and `self.base_wd = 0.0` are hardcoded). Needs: constructor param `wd=0.0` wired to both `weight_decay=wd` and `self.base_wd = wd` (else a future cooldown rescales from 0), `--opt-wd` argparse line + pass-through in both runners. Mark mode process.
- **mode:** process
- **prediction:** +0.00..+0.04 (slightly worse is the prior — strong decay on embeddings at this scale). Mechanism caveat: decoupled decay also shrinks the `log_scale` params, i.e. the installed ternary step sizes — a move here is partly a scale-shrink effect, not pure regularization.
- **status:** queued
```mill
id: C-B07
mode: process
run: --arm layered_half --rope --opt-wd 0.1
```

### C-B08 · betas -> (0.9, 0.999)
- **source:** champion mutation grid (gene: betas, champion value: (0.9, 0.95))
- **mechanism:** β2 0.95 → 0.999 pushes the second-moment horizon from ~20 steps to ~1000 — longer than any run this lab makes (~160 steps full format, far fewer at probe). A-099 proposes 0.99 (~100 steps); 0.999 is the distinct regime where v̂ never equilibrates, which is the actual methodological question.
- **train.py:** `--arm layered_half --rope --betas 0.9,0.999` — NOT reachable today: betas are hardcoded `(0.9, 0.95)` in the Layered/Direct/STE AdamW calls, no constructor arg. Needs: `betas=` param on Layered, `--betas` argparse line + pass-through in both runners (flag form follows A-099). Mark mode process.
- **mode:** process
- **prediction:** ±0.04 with high seed variance expected (bias-corrected v̂ is dominated by early gradients for the whole run). Risk: a noisy probe here is uninformative in both directions — this entry earns its keep at full trial, not probe.
- **status:** queued
```mill
id: C-B08
mode: process
run: --arm layered_half --rope --betas 0.9,0.999
```

### C-B09 · betas -> (0.85, 0.95)
- **source:** champion mutation grid (gene: betas, champion value: (0.9, 0.95))
- **mechanism:** The β1 move nobody has proposed anywhere (A-099 moves only β2): momentum horizon 10 → ~6.7 steps on the shared parts. Tests whether the FP parts want fresher gradient averages when the ternary side they serve is itself re-deciding structure every step.
- **train.py:** `--arm layered_half --rope --betas 0.85,0.95` — same `--betas` plumbing as C-B08. Mark mode process.
- **mode:** process
- **prediction:** ~0 ± 0.02; the cleanest optimizer-geometry read in the family (size-, state-, and step-neutral, horizon well inside the run length, unlike C-B08).
- **status:** queued
```mill
id: C-B09
mode: process
run: --arm layered_half --rope --betas 0.85,0.95
```

### H-C — Kernel-informed variants (ALL pending: no kernels/RESULTS-KERNELS.md yet)

### C-C01 · Integer matmul, direct int32 (codes @ ternary, rescale once)
- **source:** kernel stream (kernels/bench_matmul.py) — STATUS: PENDING results
- **mechanism:** Each BitLinear forward stops materialising dequantized fp32 operands. Activation int8 codes `xi` and ternary weights as int8 `wi` are multiplied as an exact int32 matmul `xi.int32 @ wi.T.int32`, then rescaled once by `(xscale * s)` — one rescale instead of an fp32 GEMM over already-quantized values. Bit-exact integer accumulation; the only error vs the bench ref is fp32 rounding in the reference itself.
- **train.py:** new flag `--matmul int32` in `BitLinear.forward`, vote arms only (see discrepancy 2), plus a custom autograd/STE wrapper reproducing the current detach-trick gradients (discrepancy 1) and the bias add-back. Must NOT be wired until `kernels/RESULTS-KERNELS.md` lands and this variant passes the protocol below.
- **mode:** process
- **prediction:** Pure kernel swap — at equal steps the held loss must be identical within rounding (trajectory-preserving). Mill probe (1.25 min, seed 0, vs job-zero baseline at the same generation) is a correctness/speed gate, not a loss hunt: **PASS if held_final ≤ baseline + 0.02 (the mill's "flat" band) AND steps ≥ 1.10× baseline steps** in the same wall time. A loss *improvement* beyond flat would come only from the extra steps, never from the math.
- **status:** pending-kernel-results
```mill
id: C-C01
mode: process
run: --arm layered_half --rope --matmul int32
```

### C-C02 · LUT matmul, TL2-like groups of 4 (lut_g4)
- **source:** kernel stream (kernels/bench_matmul.py) — STATUS: PENDING results
- **mechanism:** K is grouped in 4s; for each (row, group) a table of all 3⁴=81 ternary combinations of the 4 int8 codes is built by DP (`einsum` with the combo matrix), weights are pre-encoded as base-3 indices `widx ∈ 0..80`, and the output is a sum of `gather`s from the tables, rescaled once. Trades the multiply-accumulate for table-build + gather; also exact integer arithmetic.
- **train.py:** new flag `--matmul lut4` in `BitLinear.forward`, vote arms only, same STE-wrapper and bias requirements as C-C01, plus pre-encoding each layer's `widx` once per `install()` (weights only change on flips) rather than per forward. Must NOT be wired until the kernel results land and pass correctness — and note the bench implementation (per-call `[rows, groups, 81]` tables, Python group loop, `reps=3`) is a prototype; wiring the bench code as-is is not the proposal, a production version must at least pre-build weight indices.
- **mode:** process
- **prediction:** Same correctness gate as C-C01 (held loss unchanged at equal steps — exact integer math), but a **higher speed bar because of table memory and build cost: PASS if probe held_final ≤ baseline + 0.02 AND steps ≥ 1.20× baseline steps.** Anything less does not pay for the table footprint at 8192 training rows.
- **status:** pending-kernel-results
```mill
id: C-C02
mode: process
run: --arm layered_half --rope --matmul lut4
```

### C-C03 · On-the-fly integer matmul (quantize inside the kernel)
- **source:** kernel stream (kernels/bench_matmul.py) — STATUS: PENDING results
- **mechanism:** Starts from raw fp32 `x` each call: per-row absmax quantize to int8 codes happens *inside* the path, followed by the same exact int32 matmul and single rescale as C-C01. This is the closest drop-in for `train.py`, whose `BitLinear.forward` already re-quantizes activations on every forward — C-C01 assumes codes already exist, C-C03 pays the quantization itself, and the bench's `quantize_only` timing exists precisely to price that difference.
- **train.py:** new flag `--matmul otf` in `BitLinear.forward`, vote arms only, same STE-wrapper and bias requirements as C-C01. Must NOT be wired until the kernel results land and pass correctness.
- **mode:** process
- **prediction:** Held loss unchanged at equal steps (it performs the identical quantization `train.py` already performs, then exact integer math). **PASS if probe held_final ≤ baseline + 0.02 AND steps ≥ 1.10× baseline steps.** The honest kernel-level comparison for this variant is `onthefly_int` vs `direct_fp32 + quantize_only`, not vs `direct_fp32` alone.
- **status:** pending-kernel-results
```mill
id: C-C03
mode: process
run: --arm layered_half --rope --matmul otf
```

### C-C04 · Fused vote-counter update (step_fused)
- **source:** kernel stream (kernels/bench_vote.py) — STATUS: PENDING results
- **mechanism:** Only the elementwise vote update inside `Layered.step` changes (AdamW and backward untouched — the bench does not time them and neither does this entry). Sign computed once; counters updated in place (`add_` / `clamp_`); the flip test `(t + c.sign()).clamp(-1,1) != t` is replaced by the exactly-equivalent `(s != 0) & (t != s)`; on a flip the new value is `t + s` directly; `where` writes reuse preallocated state where the current code allocates. Same median gate, same vote, same clamp/reset, V=32, same t1-before-t2 one-flip rule.
- **train.py:** new flag `--vote-kernel fused` on `Layered` (and `Direct` only after its own equivalence check — the bench validates `Layered` semantics only; explicitly NOT `--carry`, see discrepancy 4). Must NOT be wired until the kernel results land and show exact state equivalence.
- **mode:** process
- **prediction:** This variant claims *exact* equivalence, so the probe gate is the tightest in Family C: at equal steps the training trajectory should be bit-identical. **PASS if probe held_final ≤ baseline + 0.01 AND steps ≥ 1.03× baseline steps** (the vote update is a small share of step time next to backward, so even a large kernel-level win dilutes to a few percent end-to-end — 3% is the honest adoption floor).
- **status:** pending-kernel-results
```mill
id: C-C04
mode: process
run: --arm layered_half --rope --vote-kernel fused
```

### C-C05 · Complex-multiplication rotary (rotated_cplx)
- **source:** kernel stream (kernels/bench_attention.py) — STATUS: PENDING results
- **mechanism:** `train.py`'s `rotated()` (slice pairs → `stack([a·cos − b·sin, a·sin + b·cos])` → `flatten`) is replaced by the identical interleaved-pair rotation done as one complex multiply: pairs viewed as `a+bi`, times a precomputed unit rotor `cos + i·sin`, `view_as_real` back to interleaved layout. Same rotation, same angles, applied to q and k only; SDPA itself unchanged. The bench's `rope+sdpa_cplx_s` composite is this entry's end-to-end timing.
- **train.py:** new flag `--rope-impl cplx` selecting the `rotated()` implementation inside `Block` (rotor registered as a complex buffer alongside the existing `cos`/`sin` buffers; only meaningful with `--rope`). Autograd flows through `view_as_complex`/`view_as_real`, but gradient equivalence vs the reference rotation must be sanity-checked at wiring time — the bench is forward-only. Must NOT be wired until the kernel results land and pass correctness.
- **mode:** process
- **prediction:** Held loss unchanged within fp rounding at equal steps (complex vs real arithmetic reorder rounding only; small trajectory drift over a probe is expected and acceptable inside the flat band). **PASS if probe held_final ≤ baseline + 0.02 AND steps ≥ 1.05× baseline steps** (rotary is applied twice per block per forward, but attention+MLP dominate step time).
- **status:** pending-kernel-results
```mill
id: C-C05
mode: process
run: --arm layered_half --rope --rope-impl cplx
```

### C-C06 · Manual attention (explicit QKᵀ, mask, softmax, @V)
- **source:** kernel stream (kernels/bench_attention.py) — STATUS: PENDING results
- **mechanism:** `F.scaled_dot_product_attention(is_causal=True)` in `Block.forward` is replaced by the explicit form: `att = (q @ kᵀ)·hd^-0.5`, causal mask via `triu(1)` bool `masked_fill(-inf)`, `softmax @ v`. Identical math; materialises the `[b, h, 256, 256]` logits that SDPA's backends avoid. Included for completeness as a falsification/speed gate — the prior is that it is **slower**, and the bench even overstates its cost by rebuilding the mask per timed call (a wiring would cache the mask).
- **train.py:** new flag `--attn manual` in `Block.forward`, mask cached as a buffer. Must NOT be wired until the kernel results land and pass correctness.
- **mode:** process
- **prediction:** Held loss unchanged within fp rounding at equal steps. **PASS if probe held_final ≤ baseline + 0.02 AND steps ≥ 1.05× baseline steps.** Expected outcome is FAIL on speed; if the kernel results confirm `manual_s > sdpa_s`, this entry should never flip (see protocol) and the probe should not be spent on it.
- **status:** pending-kernel-results
```mill
id: C-C06
mode: process
run: --arm layered_half --rope --attn manual
```

**Pending protocol — mechanical flip conditions (summary; full text in
CANDIDATES-C.md).** A Family C entry's status may flip to `queued` ONLY when ALL
hold; any failure, missing field, or missing case = stays `pending-kernel-results`.
Gate 0 (existence & completeness): kernels/RESULTS-KERNELS.md exists with one result
line per bench case (matmul 8 cases, vote 2, attention 2; head cases present but
EXCLUDED from all decisions). Gate 1 (correctness, hard, per variant, every non-head
case): direct_int32_err <= 1e-3; lut_g4_err <= 1e-3; onthefly_int_err <= 1e-3;
fused_max_state_err == 0.0 exactly, both cases; rope_cplx_err <= 1e-4;
manual_err <= 1e-4. Gate 2 (speed, per variant, median seconds as printed by the
benches): C-C01 direct_int32 <= 0.90x direct_fp32 on each champion block case and
<= 1.00x on each ladder block case; C-C02 lut_g4 <= 0.80x direct_fp32 on each
champion block case (0.80x-1.00x stays pending pending a re-bench at reps=9);
C-C03 onthefly_int <= 0.90x (direct_fp32 + quantize_only) on each champion block
case; C-C04 fused_net_s <= 0.80x current_net_s on BOTH vote cases; C-C05
rope_cplx_s <= 0.90x rope_ref_s AND rope+sdpa_cplx_s <= 0.95x rope+sdpa_ref_s, both
attention cases; C-C06 manual_s <= 0.90x sdpa_s, both cases (expected to fail — that
is the designed outcome). Gate 3 (scope): even after flipping, C-C01/02/03 wire only
for the vote arms with the STE-gradient wrapper, and C-C04 only for non-carry
Layered; if wiring reveals the wrapper cannot reproduce the current detach-trick
gradients exactly, the entry returns to pending regardless of kernel results.
Flipping authorises wiring + probing only; adoption still goes through PROMOTE.md.
`sdpa_math` has NO entry (the bench never timed it).



## I — Dream/replay candidates (merged from CANDIDATES-D.md, 2026-11-12)

7 entries (D-001..D-007) from the dreaming department. Every entry runs as a
COMPANION RUNNER (run_dream.py / dream.py) importing Tiny, Layered, offsets,
held_windows, held_loss from train.py — train.py itself is untouched, so all seven
defer until the runner lands. Chassis: layered_half + rotary, V=32, batch 32,
CTX 256, judged on the standard 128 held windows vs champion 2.8580 ± 0.0161.
**Evaluation protocol (CANDIDATES-D.md, final section) governs this family and wins
over PROMOTE.md where they disagree:** judged on STEPS, never minutes — S_total =
160 steps for every arm (candidate, CONTROL-D, every factorial cell), tokens
T = S_total x 8,192 identical in every arm (replayed windows count in full every
time; self-generated text counts 1:1 when stepped on; scoring/mining/generation
passes count 0 steps but their compute is inside wall_s with overhead_s logged; a
win at >1.5x the paired control's wall carries a COST flag). CONTROL-D is mandatory
per candidate per seed (champion chassis to the same S_total, dream-phase steps
spent on ordinary offsets() windows). Adoption requires BOTH mean < 2.8258 AND
beating paired CONTROL-D mean by >0.01 with >=2/3 seeds paired-better; beating the
champion but not CONTROL-D is stamped STEPS-ARTEFACT and rejected. Seeds 0/1/2
only; dream randomness on its own stream (random.Random(10_000 + seed)).
Contamination law: buffer offsets asserted held_overlap = 0 at build and at draw;
D-002 prompts only from offsets() (prompt_overlap = 0 logged); held_loss at phase
boundaries is log-only, never feeds back; FLIP-STORM and NOISE-CHASE SUSPECT stamps
as defined in the protocol. Full-trial-only entries (D-002, D-004, D-005, D-007)
enter by a human's word only and are ledgered `probe: skipped (full-trial-only)`.
Factorials: D-003 targeting x threshold 2x2 (all 4 cells mandatory at trial);
D-005 trigger x content 2x2, yoked; D-006 freeze-side x content (candidate freezes
the AdamW side; inverse control freezes the ternary side); D-002 source x filter
2x2 (all 4 mandatory if the claim mentions filtering). Coordinator ranking: D-003
strongest; D-001 safest, prototype next; D-006 the unskippable control; D-004
highest ceiling among the novel four; D-002 highest risk; D-005/D-007 are schedule
claims.

### D-001 · Mistake replay (dream the errors, then re-sit them)
- **source:** dreaming department (CANDIDATES-D.md); factory precedent: the waking dream was a clear WIN (sealed composed 0.4444 -> 0.8333)
- **mechanism:** phase 1 (first 70% of steps) trains exactly as champion, except per-window losses are recorded (offset -> max per-window loss seen, riding the same forward pass). At the boundary the runner takes the top-K=512 distinct offsets, drops the top 8 as presumed corrupt/noise — the mistake buffer. Phase 2 (final 30%): every batch is 24 fresh windows from offsets() + 8 replay windows sampled UNIFORMLY over the buffer; each buffer window may be replayed at most 4 times, then evicted. Counters during replay: normal V=32, normal gate, AdamW live. Buffer offsets are asserted held_overlap = 0 at build and at draw (protocol §4).
- **train.py:** new runner flags `--dream replay --buffer-k 512 --phase1-frac 0.70 --replay-per-batch 8 --replay-cap 4 --trim-top 8` on run_dream.py; recorded arm label layered_half_rope_dream-replay
- **mode:** process — probeable as a WEAK SCREEN only (protocol §3): a 75s step-boxed smoke (compressed 60/40 split, K=256) is a plumbing/sign check; delta >= 0.05 vs CONTROL-D promotes, but a flat probe is INCONCLUSIVE, not a kill (proposed PROMOTE.md exception). companion runner (run_dream.py / dream.py) importing train.py — train.py itself is untouched; all --dream flags are new runner flags, so screen.py defers this entry until the runner lands
- **prediction:** the model's residual loss is concentrated in windows it demonstrably gets wrong IN ITS CURRENT STATE (the buffer is scored online by this run's model, not pre-scored by an init model as in static failweight). A vote counter needs ~32 net strong votes to move a weight; re-sitting a hard window is how its evidence ever accumulates. Trial judged under the D protocol: S_total=160 steps for every arm, CONTROL-D mandatory per seed, adoption needs BOTH mean < 2.8258 AND beating paired CONTROL-D by >0.01 with >=2/3 seeds paired-better. Kill: trial mean >= 2.8480, or buffer replay loss falls >=20% in phase 2 while held is flat/worse in >=2/3 seeds (memorisation signature). Coordinator: safest of the family, prototype next (shares D-003's buffer machinery).
- **status:** queued
```mill
id: D-001
mode: process
run: --arm layered_half --rope --dream replay --buffer-k 512 --phase1-frac 0.70 --replay-per-batch 8 --replay-cap 4 --trim-top 8
```

### D-002 · Self-generated practice text, filtered by vote dynamics
- **source:** dreaming department (CANDIDATES-D.md) — the only dream entry that creates new training MATERIAL
- **mechanism:** train on real text to 50% of steps; then generate a candidate pool (prompts = first 64 tokens of non-held windows via offsets() ONLY, prompt_overlap = 0 logged; continuations of 193 tokens, temperature 1.0, top-k 50). Each candidate span is scored by a batch=1 dry run replicating the Layered.step vote computation against a SNAPSHOT of t1/t2/c1/c2 without mutating the trainer. One filter variant per arm — never stacked: (a) flipband [primary]: predicted flip share within [0.5x, 2x] the median flip share of the trailing 100 real batches; (b) agree: strong-vote agreement with existing counter signs within [0.55, 0.85]; (c) strongmass: strong-half |g| mass concentration within ±25% of its median over 16 real batches. Every variant also applies the guard band (not the filter): candidate mean CE in [1.8, 4.5]. Filter until 256 spans accepted or 2,048 candidates exhausted. From 50% to 85% of steps batches are 28 real + 4 synthetic; final 15% is real text only. The run string encodes the primary variant (a); variants (b) and (c) are separate trial arms of this same entry, and the source x filter 2x2 factorial (protocol §2) is mandatory at trial if the claim mentions filtering.
- **train.py:** new runner flags `--dream synth --synth-filter flipband|agree|strongmass --gen-at 0.50 --synth-per-batch 4 --synth-until 0.85 --pool 256 --cand-budget 2048 --temp 1.0 --topk 50` on run_dream.py (generation loop and dry-run vote simulator are new runner code)
- **mode:** process — FULL TRIAL ONLY per CANDIDATES-D.md's evaluation protocol §3: never probe-eligible; enters only by a human's word and is ledgered `probe: skipped (full-trial-only)`. companion runner (run_dream.py / dream.py) importing train.py — train.py itself is untouched; all --dream flags are new runner flags, so screen.py defers this entry until the runner lands
- **prediction:** spans the current model half-believes, whose gradients push in directions its counters already lean toward, are precisely the spans a vote trainer can convert into flips with the least wasted evidence. Differs from the closed JEPA experiment in kind: the objective stays next-token CE on tokens; self-reference enters only through WHICH data is selected. Honestly charged: generation + dry runs are paid out of the same 8-minute wall clock, so the arm trains on fewer real steps — that handicap is part of the measurement. Pre-trial gates (either retires it without a trial): filter acceptance <5% or >80%; or a 100-step synthetic-heavy smoke segment worsens held by >=0.05. Trial kill: mean >= 2.8480, or accepted-pool statistics drift toward the guard-band edges (echo-chamber signature). Coordinator: highest risk in the family.
- **status:** queued
```mill
id: D-002
mode: process
run: --arm layered_half --rope --dream synth --synth-filter flipband --gen-at 0.50 --synth-per-batch 4 --synth-until 0.85 --pool 256 --cand-budget 2048 --temp 1.0 --topk 50
```

### D-003 · Consolidation pass (low-V finish on hard windows)
- **source:** dreaming department (CANDIDATES-D.md) — prototyped: companion DREAM-PROTOTYPE.md + dream-proto/ implement its 4 factorial cells as --control {none,threshold,target,full}, with D-006 folded in as a --freeze axis
- **mechanism:** main phase (first 90% of steps) is champion training at V=32, with the D-001 buffer collected in parallel (K=512, top 8 trimmed). For the final 10% of steps the runner sets trainer.votes = 8 (Layered.step reads self.votes every step, so this takes effect immediately) and batches become 24 hard-buffer windows + 8 fresh. AdamW parts keep training at lr 1e-3 — NOT the closed cooldown (no lr schedule is applied). Coupled effect, specified not hidden: the same V clamps the counters, so the first consolidation step truncates every counter to ±8 and every weight with |c| >= 8 and a non-no-op direction flips — a deliberate bank-resolution step; the runner logs the pre-phase counter histogram and that step's flip share separately as the resolution wave.
- **train.py:** new runner flags `--dream consolidate --buffer-k 512 --consol-frac 0.10 --consol-votes 8 --consol-hard-per-batch 24` on run_dream.py (the entire change is the runner assigning trainer.votes = 8 at the phase boundary and changing batch composition)
- **mode:** process — probeable as a DANGER CHECK only (protocol §3 [R3]): kill signatures can fire at probe scale, but a flat probe is INCONCLUSIVE, not a kill (the bank mass in [8,32) is thinnest at probe horizon); delta >= 0.05 vs CONTROL-D still promotes. Trial is the full targeting x threshold 2x2 — all 4 cells mandatory, candidate must beat BOTH single-factor cells by >0.01 or the claim renames (protocol §2). companion runner (run_dream.py / dream.py) importing train.py — train.py itself is untouched; all --dream flags are new runner flags, so screen.py defers this entry until the runner lands
- **prediction:** at any moment in a V=32 run, a large mass of counters sits at |c| in [8, 32) — real, accumulated, majority-signed evidence that has not resolved and mostly never will. A short low-V pass lets that evidence act where it matters (hard-window batch majority). This is NOT the closed 8->64 anneal: that started at 8 from step 0 with no bank and raised V across the whole run; consolidation holds V=32 for 90% and lowers it only at the end, only briefly, only on hard windows — the bank's existence is the mechanism. Kill: trial mean >= 2.8480; or the consolidation segment itself is net-negative (boundary vs end held worsens >0.02 across seeds); or resolution-wave flip share >10% of weights with held not recovered to the boundary value by the end in >=2/3 seeds. Coordinator: strongest entry in the family.
- **status:** queued
```mill
id: D-003
mode: process
run: --arm layered_half --rope --dream consolidate --buffer-k 512 --consol-frac 0.10 --consol-votes 8 --consol-hard-per-batch 24
```

### D-004 · Counter-pressure mining (dream the windows that resolve stuck evidence)
- **source:** dreaming department (CANDIDATES-D.md) — the only selection rule no STE trainer can imitate
- **mechanism:** at dream onset (60% of step budget), snapshot c1/c2. Draw a candidate pool of 8 batches via offsets() and score each with ONE forward/backward and NO step, replicating the vote rule read-only (vote = -sign(g), gated at per-layer median |g|). Score per batch = sum over weights with 16 <= |c| < 32 of 1[vote = sign(c)]*(|c|/32) - 0.5*1[vote = -sign(c)]*(|c|/32), normalised by the batch's near-threshold mass. Dream 12 steps cycling the top-2 scoring batches, V=32 unchanged, AdamW live. Runner logs near-threshold mass and dream-phase flip share. This selects windows by what they do to the trainer's UNRESOLVED EVIDENCE, not by loss.
- **train.py:** companion runner only — `dream.py --dream counter-pressure --dream-at 0.6 --pool-batches 8 --keep-batches 2 --dream-steps 12`; no train.py change
- **mode:** process — FULL TRIAL ONLY per CANDIDATES-D.md's evaluation protocol §3: never probe-eligible; enters only by a human's word and is ledgered `probe: skipped (full-trial-only)`. companion runner (run_dream.py / dream.py) importing train.py — train.py itself is untouched; all --dream flags are new runner flags, so screen.py defers this entry until the runner lands (The candidate's own cost line says 'cheap probe', but the CANDIDATES-D evaluation protocol §3 classifies D-004 full-trial-only FOR ADOPTION — counter pressure barely exists at probe scale; a probe may still be run as a plumbing check, never as the adoption path.)
- **prediction:** a flip is the only discrete unit of learning this trainer has, and the chassis's flip rate is ~0.11%/step — dream steps are too scarce to spend on windows chosen by a proxy (loss) when the actual bottleneck variable, the counter distribution, is directly observable for free. A win here is evidence FOR the vote mechanism itself, not just for more training. Kill: probe held delta vs job zero < 0.02, OR dream-phase flip share < 1.5x the preceding 50 steps' mean flip share — if it does not even move the mechanism it claims to move, it does not earn a trial regardless of the loss reading. Coordinator: highest ceiling among the novel four.
- **status:** queued
```mill
id: D-004
mode: process
run: --arm layered_half --rope --dream counter-pressure --dream-at 0.6 --pool-batches 8 --keep-batches 2 --dream-steps 12
```

### D-005 · Flip-share-triggered repetition dream (dream exactly when the mechanism goes quiet)
- **source:** dreaming department (CANDIDATES-D.md) — a schedule claim (trigger), not a content claim
- **mechanism:** no phase schedule. The runner tracks the rolling mean of step()'s returned flip share over the last 50 steps; when it falls below 0.0008 (≈30% under the chassis's measured full-run mean of 0.0011-0.0012), at least 100 steps have elapsed, and at least 100 steps have passed since the last dream, a dream fires: draw 2 fresh batches via offsets() and repeat each 6 times consecutively (12 dream steps), V=32, AdamW live, max 6 dreams per run. Repetition is the active ingredient: six consecutive identical votes move a contested counter up to 6 steps with no interleaved cancellation. Runner logs every trigger (step, rolling flip share, dream flip share). Trial is the trigger x content 2x2, YOKED: the fixed-schedule cell fires the same number of episodes/steps the triggered cell recorded for that seed (protocol §2).
- **train.py:** companion runner only — `dream.py --dream flip-trigger --trigger-window 50 --trigger-floor 0.0008 --trigger-set 2 --trigger-reps 6 --trigger-max 6`; no train.py change
- **mode:** process — FULL TRIAL ONLY per CANDIDATES-D.md's evaluation protocol §3: never probe-eligible; enters only by a human's word and is ledgered `probe: skipped (full-trial-only)`. companion runner (run_dream.py / dream.py) importing train.py — train.py itself is untouched; all --dream flags are new runner flags, so screen.py defers this entry until the runner lands (Its probe-based kill lines apply to trigger BEHAVIOUR — never fires / hits the 6-dream cap — not to held delta: flip-share in the first ~25 steps is the startup transient, never the designed steady-state regime.)
- **prediction:** D-001/D-003 dream on a clock, but the chassis does not stall on a clock — it stalls when the easy flips are exhausted, which is exactly what flip share measures. Triggering there concentrates the scarcest resource (repeated, uncontested evidence) at the moment marginal normal steps return the least, and the trigger is self-calibrating across seeds and scales where a fixed phase point is not. Kill: the trigger never fires (floor is fiction), or it hits the 6-dream cap (a disguised fixed schedule), per the entry's probe-behaviour lines.
- **status:** queued
```mill
id: D-005
mode: process
run: --arm layered_half --rope --dream flip-trigger --trigger-window 50 --trigger-floor 0.0008 --trigger-set 2 --trigger-reps 6 --trigger-max 6
```

### D-006 · Frozen-AdamW dream (pure ternary consolidation, nothing continuous moves)
- **source:** dreaming department (CANDIDATES-D.md) — the attribution control the whole dream family needs; folded into the D-003 prototype as its --freeze axis
- **mechanism:** two dream phases (at 50% and 80% of steps, 15 steps each) on fresh uniform windows via offsets(), V=32, selection deliberately neutral — the ONLY change is that during dream steps the runner patches trainer.opt.step to a no-op and restores it after, so embeddings, norms, and log_scale are bit-frozen and only t1/t2 flips move. Built-in inverse control in the same runner (--dream frozen-ternary): snapshot t1/t2/c1/c2 before the phase and restore after, so votes cannot move and only AdamW trains, at identical step counts. The pair attributes any effect to the vote side, the continuous side, or neither. Runner calls held_loss immediately before and after each dream (logged diagnostic only, protocol §4) and logs the delta.
- **train.py:** companion runner only — `dream.py --dream frozen-votes --dream-at 0.5,0.8 --dream-steps 15` and `--dream frozen-ternary` for the inverse control; no train.py change. The run string encodes the candidate arm; the inverse control is the same entry's second arm
- **mode:** process — probeable as a SCREEN only (protocol §3): a probe runs candidate-vs-control only, so it can promote and can never attribute — no freeze claim from a probe, and delta < 0.05 is INCONCLUSIVE, not a kill. Trial = 3 seeds x 8 min x 2 arms (candidate + inverse control), judged under the D protocol (CONTROL-D mandatory). companion runner (run_dream.py / dream.py) importing train.py — train.py itself is untouched; all --dream flags are new runner flags, so screen.py defers this entry until the runner lands
- **prediction:** in every normal step, a vote flip is instantly followed by install() rescaling and an AdamW move of the embeddings, norms, and scales — the frame the votes voted in shifts under the flip, and log_scale in particular can absorb a flip's effect by shrinking. A frozen frame lets the ternary structure settle against fixed continuous parameters. D-001..D-005 and D-007 all dream with AdamW live, so any win they show is ambiguous between vote consolidation and ordinary continuous drift until this entry prices the two apart. Kill: probe held delta vs job zero < 0.02, OR held immediately after either dream is worse than immediately before it in the probe.
- **status:** queued
```mill
id: D-006
mode: process
run: --arm layered_half --rope --dream frozen-votes --dream-at 0.5,0.8 --dream-steps 15
```

### D-007 · Interleaved micro-dreams (placement is the claim, content held fixed)
- **source:** dreaming department (CANDIDATES-D.md) — a schedule claim (placement), not a content claim
- **mechanism:** the runner keeps a ring buffer of only the last 25 steps' batches (offsets + the loss recorded when each was first seen — no rescoring, no run-long memory). Every 25 normal steps it runs a 5-step micro-dream replaying the highest-loss batches from that short window only, then clears the buffer; total dream steps ≈ 1/6 of the run, V=32, AdamW live. The same runner carries the placement control --dream-place end, which applies the identical selection rule and identical total dream-step count as one end-phase from a run-long buffer. Content, dose, and rule are held fixed between the two arms; the only variable is WHEN the dream steps sit. Deliberately not D-001: D-007's buffer horizon is 25 steps, its selection is incidental, and its claim survives only if placement itself pays.
- **train.py:** companion runner only — `dream.py --dream micro --dream-every 25 --dream-steps 5 --buffer 25 --dream-place interleaved|end`; no train.py change. The run string encodes the interleaved (candidate) arm; the end-placement control is the same entry's second arm
- **mode:** process — FULL TRIAL ONLY per CANDIDATES-D.md's evaluation protocol §3: never probe-eligible; enters only by a human's word and is ledgered `probe: skipped (full-trial-only)`. companion runner (run_dream.py / dream.py) importing train.py — train.py itself is untouched; all --dream flags are new runner flags, so screen.py defers this entry until the runner lands
- **prediction:** the factory's waking dream — the precedent win — was woven into the loop, not appended to it, and the doctrine was earned in that woven form. Mechanistically: an end-phase dream's flips are never tested — the run ends before normal steps can counter-vote a bad flip — while a micro-dream's flips face the next 25 normal steps as an immediate audit, and replay happens while those windows' gradients are still aligned with the current AdamW state. Kill: probe held delta vs job zero < 0.02, OR at trial the interleaved arm does not beat its own end-placement control by > 0.01 — if placement does not pay, any gain belongs to replay itself, which is D-001's claim, and D-007 is dead even if the numbers look good.
- **status:** queued
```mill
id: D-007
mode: process
run: --arm layered_half --rope --dream micro --dream-every 25 --dream-steps 5 --buffer 25 --dream-place interleaved
```

---
Merge note (2026-11-12, pool merge stream): sections F-I add 179 entries
(A-001..A-114, B-001..B-031, C-A01..C-A12 + C-B01..C-B09 + C-C01..C-C06,
D-001..D-007) merged from mill/CANDIDATES-A.md, CANDIDATES-B.md, CANDIDATES-C.md and
CANDIDATES-D.md. No existing MILL- entry was dropped, renumbered, or edited; the
original pool text above (through section E) is byte-identical to the pre-merge
file (backup: mill/IDEA-POOL.pre-merge.md). mill/FABLE-CANDIDATES.md does not exist
(the Fable trace found nothing new), so nothing was folded in from it. Pool size
after merge: **355 entries** (176 + 179).

## J — Failure-driven candidates (merged from CANDIDATES-E.md, 2026-11-12)

24 entries (E-001..E-024) mined by idea-mining wave E from the lab's own documented
failures, regressions, retractions, and unexplained gaps — every entry is the follow-up
test a failure implies. Families 1–3 and 9 are FACTORY work (learned say, spawn mining,
growth gates, substrate): their run strings carry a `--factory` marker, screen.py defers
them on that marker, and execution belongs to the factory queue — the mill never probes
them. Families 4–8 are BitNet-lab and mill-methodology work. Entries marked FULL TRIAL
ONLY in their mode line (E-011, E-012, E-014, E-018, E-019, E-020) are never
probe-eligible. Wave E's own top 5: E-018, E-007, E-001, E-005, E-014.

### J-F1 — The learned say's clean-recall collapse (factory)

### E-001 · Waking-in-the-loop say fit
- **source:** idea-mining wave E (CANDIDATES-E.md), Family 1 — `learned-say-2026-11-12.md` — "A future attempt should fit with the waking layer in the loop on dev (fit on dev-path outcomes, not raw verdicts) — recorded as the next attack, not attempted here."
- **mechanism:** Refit the say's seat standings + thresholds by coordinate ascent where the objective is the accuracy of the **full dev serving path** (composer → waking layer → verdict) instead of raw composed verdicts. Same dev pool (216 items), same ascent discipline (strict improvements only).
- **train.py:** no change — factory change in `factory/learned_say.py` (fit objective). The run string's `--factory` marker names the factory surface; it is an encoding marker, not a trainer flag.
- **mode:** process — factory (`factory/learned_say.py` fit objective change; judged by the existing battery `a1s` path, sealed set untouched during fitting). NOT a train.py probe: screen.py defers this entry on the `--factory` marker (flag not in train.py); execution belongs to the factory queue.
- **prediction:** If the collapse was a fit-objective mismatch, dev-path fitting recovers most of the clean loss: sealed ≥ 0.8472 (within 1 item of incumbent) while keeping some dev gain. If sealed still drops ≥ 2 clean items, the problem is margin *scale* itself → E-003 decides.
- **status:** queued
```mill
id: E-001
mode: process
run: --factory learned-say --say-fit waking-loop
```

### E-002 · Clean-floor constrained say fit
- **source:** idea-mining wave E (CANDIDATES-E.md), Family 1 — same report (`learned-say-2026-11-12.md`): the say traded exactly one thing (clean recall) for its dev gain; nothing in the fit priced that trade.
- **mechanism:** Coordinate ascent as in the original build, but any step that drops **dev clean recall below the incumbent rule's dev clean recall** is rejected, however much it raises total dev accuracy. The say may only win on defect classes.
- **train.py:** no change — factory change in `factory/learned_say.py` (one constraint in the ascent acceptance rule). The run string's `--factory` marker names the factory surface; it is an encoding marker, not a trainer flag.
- **mode:** process — factory (`factory/learned_say.py`, one constraint in the ascent acceptance rule). NOT a train.py probe: screen.py defers this entry on the `--factory` marker (flag not in train.py); execution belongs to the factory queue.
- **prediction:** Dev gain shrinks (expect 0.62–0.64 vs 0.6528 unconstrained) but sealed clean recall holds at ≥ 0.7727 and sealed total lands 0.8472–0.8750 — i.e. this is the version that could actually adopt. A sealed win here + a loss in E-001 would say the constraint, not the loop, was the missing piece.
- **status:** queued
```mill
id: E-002
mode: process
run: --factory learned-say --say-fit clean-floor
```

### E-003 · Margin-scale decoupling diagnostic (is it direction or scale?)
- **source:** idea-mining wave E (CANDIDATES-E.md), Family 1 — same report: "here the say feeds a verify-by-execution layer whose gates key off margin scale, so combination changes move the verification behaviour, not just the verdict."
- **mechanism:** Two-arm diagnostic on the existing fitted say, no refitting: (a) say directions with margins **renormalized to the incumbent's per-class margin-scale distribution** on dev; (b) the say as fitted. Compare sealed clean recall across arms. This separates "the say points the wrong way on clean code" from "the say points the right way at a scale the waking gates misread."
- **train.py:** no change — factory serving-path evaluation only. The run string's `--factory` marker names the factory surface; it is an encoding marker, not a trainer flag.
- **mode:** process — factory (serving-path evaluation only; a measurement, not a new model). NOT a train.py probe: screen.py defers this entry on the `--factory` marker (flag not in train.py); execution belongs to the factory queue.
- **prediction:** Arm (a) recovers ≥ 1 of the 2 lost clean items if scale is the culprit. If arm (a) changes nothing, the say's directions on clean code are genuinely defect-leaning and Family 1 should stop at E-001/E-002 rather than grow more variants.
- **status:** queued
```mill
id: E-003
mode: process
run: --factory learned-say --say-diag margin-scale
```

### J-F2 — Swapped-operands: total raw blindness, perfectly masked (factory)

### E-004 · Forced-route diagnostic (route plain slice to the plain seat)
- **source:** idea-mining wave E (CANDIDATES-E.md), Family 2 — `spawn-mining-2026-11-13.md` failure shape #1.
- **mechanism:** Override the strengths table for one evaluation: route the swapped/plain slice to the plain seat instead of "whole", on dev + the sealed-proxy surfaces, everything else unchanged. Measures whether the seat's binary strength (0.88–0.96) survives routing, i.e. whether the 0.0 is a routing artefact.
- **train.py:** no change — factory evaluation-only routing override. The run string's `--factory` marker names the factory surface; it is an encoding marker, not a trainer flag.
- **mode:** process — factory (evaluation-only routing override; no training). NOT a train.py probe: screen.py defers this entry on the `--factory` marker (flag not in train.py); execution belongs to the factory queue.
- **prediction:** If routing is the failure, forced-route raw recall on the plain slice jumps from ~0.0 to ≥ 0.5. If it stays near 0.0, the seat's binary accuracy does not transfer to the composed setting and E-005's margin story is next.
- **status:** queued
```mill
id: E-004
mode: process
run: --factory spawn-mining --route-override plain-seat
```

### E-005 · Margin-competition autopsy + per-seat margin normalization
- **source:** idea-mining wave E (CANDIDATES-E.md), Family 2 — same (`spawn-mining-2026-11-13.md`): seats strong alone, class invisible in composition — the signature of a margin-scale competition loss, the same mechanism suspected in Family 1.
- **mechanism:** Step 1 (measurement): log every seat's margin on dev plain-slice swapped items; check whether the correct seat's margin is right-signed but systematically smaller in scale than the winning seats'. Step 2 (the test): z-normalize each seat's margins by its own dev margin distribution before composition and re-measure raw recall on dev, then sealed.
- **train.py:** no change — factory composer-level change in `swarm/composers.class_margins` (dev-fitted normalization constants only). The run string's `--factory` marker names the factory surface; it is an encoding marker, not a trainer flag.
- **mode:** process — factory (composer-level change in `swarm/composers.class_margins`; dev-fitted normalization constants only). NOT a train.py probe: screen.py defers this entry on the `--factory` marker (flag not in train.py); execution belongs to the factory queue.
- **prediction:** Step 1 shows the plain seat right-signed on ≥ 60% of items it "misses". Step 2 lifts dev routed plain recall from 0.0667 toward ≥ 0.4. If step 1 shows the seat is simply wrong-signed in composition, both Family 2 composition entries die and the class goes back to corpus-scale growth, as the mining report concluded.
- **status:** queued
```mill
id: E-005
mode: process
run: --factory composer --margin-norm zscore
```

### E-006 · Verification-ablation audit (price the single point of failure)
- **source:** idea-mining wave E (CANDIDATES-E.md), Family 2 — same: sealed recall 1.0 is *entirely* execution verification; the raw composer's 0.0 means any input the execution layer cannot decide is silently unprotected.
- **mechanism:** Run the sealed battery with the waking/execution layer disabled, per class, and record the true raw-only serving profile. No model change — this prices how much of the headline 0.8611 is the composer and how much is the verifier, class by class.
- **train.py:** no change — factory battery configuration ablation. The run string's `--factory` marker names the factory surface; it is an encoding marker, not a trainer flag.
- **mode:** process — factory (battery configuration ablation). NOT a train.py probe: screen.py defers this entry on the `--factory` marker (flag not in train.py); execution belongs to the factory queue.
- **prediction:** Bug-pattern sealed falls from 0.8611 to the raw composed band (~0.50–0.56), with swapped at 0.0 and clean inflated (everything leans defect-ward without verification). The number this produces is the one future composition work should be judged against — not the verification-masked headline.
- **status:** queued
```mill
id: E-006
mode: process
run: --factory battery --ablate verification
```

### J-F3 — Growth gates pass, serving regresses (factory growth)

### E-007 · Composed-dev third gate for births
- **source:** idea-mining wave E (CANDIDATES-E.md), Family 3 — `growth-cycle-006.md` / `REPAIR-cycle-007-2026-11-12.md` — dual-gate births regressed serving in 2 of 2 rollback cycles.
- **mechanism:** Before a birth is adopted, run the candidate configuration through the **raw composed path on the existing dev pool** (the say_dev 216-item surface, not the sealed set): the composed raw score with the child installed must not fall below the composed raw score with the parent installed. Only then does serving verification run.
- **train.py:** no change — factory change in `factory/growth_cycle.py` (adoption sequence; dev pool already exists and is contamination-filtered). The run string's `--factory` marker names the factory surface; it is an encoding marker, not a trainer flag.
- **mode:** process — factory (`factory/growth_cycle.py` adoption sequence; dev pool already exists and is contamination-filtered). NOT a train.py probe: screen.py defers this entry on the `--factory` marker (flag not in train.py); execution belongs to the factory queue.
- **prediction:** Retro-check first: both cycle-6 and cycle-7 children would have failed this gate (their serving regressions were clean-recall/composition effects visible in the raw path). Prospectively, expect it to block roughly the cycles that would have rolled back, at the cost of occasionally blocking a birth serving would have accepted.
- **status:** queued
```mill
id: E-007
mode: process
run: --factory growth-cycle --gate composed-dev
```

### E-008 · Remainder-floor gate (stop birthing hollow specialists)
- **source:** idea-mining wave E (CANDIDATES-E.md), Family 3 — `growth-cycle-002/004/006.md` — child remainder acc 0.7778 / 0.3333 / 0.4444 vs parent 0.8889–1.0000, waved through as "informational — routing serves the remainder by the parent."
- **mechanism:** A birth must also clear a remainder floor: child remainder-slice accuracy ≥ parent − 0.15 on the intent surface. Children that specialize by abandoning the rest of their slice are rejected even if both pristine slices pass.
- **train.py:** no change — factory change in `factory/growth_cycle.py` (gate; remainder slices already measured every cycle). The run string's `--factory` marker names the factory surface; it is an encoding marker, not a trainer flag.
- **mode:** process — factory (`factory/growth_cycle.py` gate; remainder slices already measured every cycle). NOT a train.py probe: screen.py defers this entry on the `--factory` marker (flag not in train.py); execution belongs to the factory queue.
- **prediction:** Under this floor, cycle 4's index child (0.3333) and cycle 6's expression child (0.4444) would not have been born. The open question it answers: do floored children exist in the same grids (the per-config tables say the grids are wide), or is remainder collapse the *only* way these grids win — in which case the routing-serves-remainder arrangement is load-bearing and should be made explicit, not accidental.
- **status:** queued
```mill
id: E-008
mode: process
run: --factory growth-cycle --gate remainder-floor
```

### E-009 · Gate-slice enlargement retro-judgement (n=20 decides births)
- **source:** idea-mining wave E (CANDIDATES-E.md), Family 3 — `growth-cycle-001/003.md` — births repeatedly decided by a single item on the n=20 phase-3 slice (0.9500 vs 0.9500 ties = no birth); cycle 2's own note flags it: "the honest fix is a LARGER pristine phase-3-style held slice… not more candidates against the same 20 items."
- **mechanism:** Build a new pristine phase-3-style held slice, n ≥ 100, from fresh template families (disjoint names/idioms, contamination-filtered), then **retro-judge the recorded winning children of cycles 2–6** against their parents on it. No new training — the children are on disk.
- **train.py:** no change — factory work (new held surface + evaluation of recorded models). The run string's `--factory` marker names the factory surface; it is an encoding marker, not a trainer flag.
- **mode:** process — factory (new held surface + evaluation of recorded models). NOT a train.py probe: screen.py defers this entry on the `--factory` marker (flag not in train.py); execution belongs to the factory queue.
- **prediction:** At least one historical birth verdict flips or ties at n ≥ 100 (the n=20 wins at exactly 1.0000 have nowhere to go but down). Whatever the outcome, every future cycle's gate inherits a slice where one item is worth 0.01, not 0.05.
- **status:** queued
```mill
id: E-009
mode: process
run: --factory growth-gate --held-slice phase3-n100
```

### J-F4 — JEPA: representations equal to random init (BitNet, diagnostic)

### E-010 · Non-token yardsticks on the saved JEPA trunks
- **source:** idea-mining wave E (CANDIDATES-E.md), Family 4 — `RESULTS-JEPA-2026-11-12.md` — "It does not test JEPA's home metric… this lab has no such yardstick built."
- **mechanism:** The six saved trunks (`jepa-states/`) already exist. Probe them with (a) a 2-layer MLP readout instead of the linear probe, and (b) a span-retrieval/alignment probe (representations of two halves of one window vs mismatched windows). No training of trunks; probes only.
- **train.py:** no change — probe scripts against saved state dicts. The run string's `--probe-trunks` flag names the probe-runner surface; it is not in train.py yet, so screen.py defers this entry until that runner lands.
- **mode:** process — BitNet lab (probe scripts against saved state dicts; cheap).
- **prediction:** If JEPA learned *something* the linear token probe can't read, the MLP probe separates JEPA from the init floor by ≥ 0.05. If JEPA ≈ floor on every yardstick, the no-information verdict is total at this scale and Family 4 closes permanently.
- **status:** queued
```mill
id: E-010
mode: process
run: --probe-trunks jepa-states --probe-readouts mlp,span
```

### E-011 · Mature-target ablation (was the EMA target the poison?)
- **source:** idea-mining wave E (CANDIDATES-E.md), Family 4 — same (`RESULTS-JEPA-2026-11-12.md`): "the trunk spends much of its budget learning to match a moving, partly-random target's geometry."
- **mechanism:** One JEPA arm, one change: the target encoder is **frozen at the control arm's trained trunk** (same seed) instead of an EMA of the student from init. Everything else identical to `jepa_half_rope`. This is a mechanism test, not a proposed trainer — the target now has information by construction.
- **train.py:** companion runner only — `run_jepa.py` variant; no train.py change. The run string encodes the variant; its arm/flags are runner-side, so screen.py defers this entry until the runner lands.
- **mode:** process — BitNet lab (`run_jepa.py` variant; FULL TRIAL ONLY, 3 seeds × 8 min: never probe-eligible). Diagnostics of a closed result — the JEPA objective itself stays closed.
- **prediction:** If the partly-random target was the failure, probe CE improves from 3.2428 toward ≤ 3.05 (still likely behind the 2.8935 control — the claim is about the mechanism, not adoption). If it stays ≈ 3.24, target maturity is exonerated and the sparse-signal clause (E-012) is the whole story.
- **status:** queued
```mill
id: E-011
mode: process
run: --arm jepa_half_rope --target frozen-control
```

### E-012 · Mask-density sweep (was the signal too sparse?)
- **source:** idea-mining wave E (CANDIDATES-E.md), Family 4 — same: signal reaches the trunk "only through 64 masked positions per window" of 256.
- **mechanism:** JEPA arms at 128 and 192 masked positions (contiguous blocks, same recipe otherwise), judged by the same linear probe against the existing 64-position records and the init floor.
- **train.py:** companion runner only — `run_jepa.py --mask-len 128|192`; no train.py change. The run string encodes the 128 arm; the 192 arm is the same entry's second arm. screen.py defers this entry until the runner lands.
- **mode:** process — BitNet lab (`run_jepa.py --mask-len 128|192`; FULL TRIAL ONLY: never probe-eligible).
- **prediction:** Monotone improvement with density (192-mask probe ≤ 3.10) would confirm sparsity as a first-order cause. Flat ≈ 3.24 at all densities kills the sparsity clause and, with E-011, closes the JEPA explanation: at 0.885M weights / 8 min the objective itself carries nothing.
- **status:** queued
```mill
id: E-012
mode: process
run: --arm jepa_half_rope --mask-len 128
```

### J-F5 — The layered retraction's open edge (BitNet)

### E-013 · Level-population dynamics (does the second layer ever wake up?)
- **source:** idea-mining wave E (CANDIDATES-E.md), Family 5 — `RESULTS-2026-11-11.md` — "the second ternary layer had only begun to be used, so this is a verdict about 8 minutes, not about the idea's ceiling."
- **mechanism:** Instrument one layered full-width run at 8 / 20 / 40 minutes: log the ±2 population share and per-level flip rates at each checkpoint. Pure measurement; decides whether E-014 is worth its cost.
- **train.py:** layered arm with histogram logging; new flag `--log-level-hist` — not in train.py yet, so screen.py defers this entry until the flag lands.
- **mode:** process — BitNet lab (`train.py` layered arm with histogram logging; one seed suffices for the dynamics question).
- **prediction:** ±2 share grows from 1.7% toward ≥ 6% by 40 min if time is the missing ingredient. If it plateaus ≤ 2.5% by 20 min, the levels are structurally starved (the vote rule rarely pushes a second component across), E-014 is cancelled, and the retraction stands at all budgets.
- **status:** queued
```mill
id: E-013
mode: process
run: --arm layered --rope --log-level-hist
```

### E-014 · Founding-length layered vs plain (40 min, equal steps)
- **source:** idea-mining wave E (CANDIDATES-E.md), Family 5 — `RESULTS-2026-11-11.md` "What I would run next" #2; bounded explicitly in `RESULTS-HALF-CONTROL-2026-11-12.md` ("that would be a new test, not a rescue of this one").
- **mechanism:** Layered (full width) vs plain votes (full width) at 40 minutes, judged at **equal steps** (cap both at the plain arm's step count) so the half-control's step confound cannot re-enter. 3 seeds.
- **train.py:** no flag change — a long-format full trial; the run string's `--long-format` marker is not in train.py, so screen.py defers this entry until the trial is scheduled by hand in a free lab window.
- **mode:** process — BitNet lab (FULL TRIAL ONLY, long format: never probe-eligible; schedule in a free lab window). Contingent on E-013 showing population growth.
- **prediction:** Contingent on E-013 showing population growth: layered closes at most half the 8-minute gap (3.098 → ~3.06 vs plain ~3.05) — a tie at the bar, not a win. A genuine win (layered < plain by > 2 sd and > 0.01) would be the first evidence the levels earn anything anywhere, and would reopen the layered line at long budgets only.
- **status:** queued
```mill
id: E-014
mode: process
run: --arm layered --rope --long-format equal-steps
```

### J-F6 — Round-2 rejects with a confound still inside them (BitNet)

### E-015 · Cooldown as actually published (weight decay was a no-op)
- **source:** idea-mining wave E (CANDIDATES-E.md), Family 6 — `RESULTS-ROUND2-2026-11-12.md` — "this trainer is built with weight decay 0, so the schedule's weight-decay component scaled a zero — weight decay was a no-op in this arm."
- **mechanism:** The cooldown arm re-run with the one change that makes it the published recipe: `--wd 0.1` on the AdamW parts (C-B07 tests wd 0.1 *without* the schedule; the combination has never run). Same two-stage lr decay, same chassis.
- **train.py:** existing flags combined — `--arm layered_half --rope --cooldown --wd 0.1`; no new flag (mill block below is CANDIDATES-E.md's own).
- **mode:** sweep — same-chassis config variant (existing flags combined, per CANDIDATES-E.md); runs inside the shared-data sweep process (corpus loaded once).
- **prediction:** Still a loss, but a smaller one (2.90–2.94 vs cooldown's 2.9707): wd gives the decay phase something real to anneal. If it instead beats 2.8580, the round-2 verdict was an artefact of a half-implemented recipe and the record needs correcting.
- **status:** queued
```mill
id: E-015
mode: sweep
run: --arm layered_half --rope --cooldown --wd 0.1
```

### E-016 · Embedding-exempt cooldown (which part starved?)
- **source:** idea-mining wave E (CANDIDATES-E.md), Family 6 — same (`RESULTS-ROUND2-2026-11-12.md`): the record's diagnosis — decay "starves the embeddings, norms and scales that the vote-trained weights depend on," untested as separate parts.
- **mechanism:** Two-stage cooldown applied to norms + `log_scale`s only; **embeddings keep the constant lr 1e-3** for the whole run. One change from the rejected arm, aimed at its named mechanism.
- **train.py:** new flag `--cooldown-noemb` on the Layered trainer's AdamW groups; not in train.py yet, so screen.py defers this entry until the flag lands.
- **mode:** process — isolated train.py subprocess (code-path change); per CANDIDATES-E.md, process until the flag lands.
- **prediction:** Recovers at least half the cooldown gap (≤ 2.9143) if embedding starvation was the main clause. Recovery to ≤ 2.8580 is not predicted — the scales/norms clause may share the blame — but the split of the 0.1127 gap between parts is the deliverable either way.
- **status:** queued
```mill
id: E-016
mode: process
run: --arm layered_half --rope --cooldown --cooldown-noemb
```

### E-017 · Overshoot carry at V=8 (carry where overshoot is large)
- **source:** idea-mining wave E (CANDIDATES-E.md), Family 6 — `RESULTS-ROUND2-2026-11-12.md` — carry rejected at V=32 with flip share and histograms "nearly identical to baseline… discarded overshoot was apparently never the bottleneck" *at V=32*.
- **mechanism:** Carry's discarded evidence scales with overshoot/V; at V=8 the same gradient stream produces proportionally ~4× the relative overshoot. Arm: layered_half + rope at V=8 with `--carry`, judged against a V=8 no-carry control run in the same window (the control is part of the entry — V=8 alone is pooled, the interaction is not).
- **train.py:** existing flags combined — `--arm layered_half --rope --votes 8 --carry` vs `--votes 8`; no new flag (mill block below is CANDIDATES-E.md's own).
- **mode:** sweep — same-chassis config variants (a pair: the carry arm and its V=8 no-carry control, per CANDIDATES-E.md); runs inside the shared-data sweep process.
- **prediction:** Carry's delta vs its control is ≥ 0.01 in *some* direction at V=8 (vs +0.0181 worse at V=32) — the entry tests whether carry has a regime at all. A flat result at V=8 too closes carry at every threshold, finally.
- **status:** queued
```mill
id: E-017
mode: sweep
run: --arm layered_half --rope --votes 8 --carry
```

### J-F7 — The corpus itself (BitNet, from DATA-AUDIT)

### E-018 · Corpus-v2 re-baseline (the honest champion number)
- **source:** idea-mining wave E (CANDIDATES-E.md), Family 7 — `DATA-AUDIT.md` §4/§7 — v2 "fixes honesty, not volume"; recommendation was to adopt v2 for new series, but the champion has never been measured on it.
- **mechanism:** Champion config (layered_half + rope, plain votes) trained on corpus-v2 with v2-native held windows (same every-40th rule on the v2 stream), 3 seeds × 8 min. Produces the leakage-free reference every future v2 series will be judged against, and — against 2.8580 — the first estimate of the v1 flattery.
- **train.py:** new corpus path in the runner (`--corpus v2`, v2-native held windows); the flag is not in train.py yet, so screen.py defers this entry until the corpus path lands.
- **mode:** process — BitNet lab (new corpus path in the runner; FULL TRIAL ONLY: never probe-eligible).
- **prediction:** v2 held reads **worse** than 2.8580 by 0.15–0.45 (no duplicate leakage, no number-stream easy wins, but also far fewer unique pieces per run — the two effects oppose; the range is honest). The deliverable is the number itself: until it exists, every mill verdict is denominated in a currency known to be inflated.
- **status:** queued
```mill
id: E-018
mode: process
run: --arm layered_half --rope --corpus v2
```

### E-019 · Leakage excision on v1 (price the flattery exactly)
- **source:** idea-mining wave E (CANDIDATES-E.md), Family 7 — `DATA-AUDIT.md` §4 — "held-out content routinely also appears in training windows, so all v1 held losses are flattered by an unknown amount."
- **mechanism:** Minimal-change control: rebuild the v1 stream with **only** the lines that duplicate held-window content removed from the training side (held windows untouched, all other junk left in). Champion re-run, 3 seeds. Δ vs 2.8580 isolates leakage from every other v1 defect — which E-018 deliberately bundles together.
- **train.py:** corpus variant + champion re-run; the run string's `--corpus` value names the variant stream (`v1-leak-excised`), which does not exist yet, so screen.py defers this entry until the variant is built.
- **mode:** process — BitNet lab (corpus variant + champion re-run; FULL TRIAL ONLY: never probe-eligible).
- **prediction:** Held worsens by 0.03–0.12. A Δ at the low end says arm-vs-arm v1 verdicts were barely distorted; at the high end, close verdicts in the record (RoPE's +0.0411 margin) fall inside the leakage band and must be re-read.
- **status:** queued
```mill
id: E-019
mode: process
run: --arm layered_half --rope --corpus v1-leak-excised
```

### E-020 · Numeric-dump ablation (23% of the corpus is float streams)
- **source:** idea-mining wave E (CANDIDATES-E.md), Family 7 — `DATA-AUDIT.md` §5.1 — nine "lines" of 120k–154k pieces of scipy test matrices "teach number-stream statistics, not language, and… fill entire training windows by themselves."
- **mechanism:** v1 minus the mega-lines (> 1,000-piece lines: 23.0% of pieces), champion re-run at equal tokens, 3 seeds. A-047 removes near-duplicate *windows* and B-007 dedups documents; neither touches the mega-line dumps specifically.
- **train.py:** corpus variant + champion re-run; the run string's `--corpus` value names the variant stream (`v1-nomega`), which does not exist yet, so screen.py defers this entry until the variant is built.
- **mode:** process — BitNet lab (corpus variant + champion re-run; FULL TRIAL ONLY: never probe-eligible).
- **prediction:** Held improves slightly (≤ 0.05) or stays flat — the dumps are easy loss (predictable floats) but consume a quarter of all windows. If held *worsens* materially, the float streams were secretly load-bearing as a low-entropy training stabilizer, which would be a finding about the vote trainer, not the corpus.
- **status:** queued
```mill
id: E-020
mode: process
run: --arm layered_half --rope --corpus v1-nomega
```

### E-021 · German-test excision (a test split inside training data)
- **source:** idea-mining wave E (CANDIDATES-E.md), Family 7 — `DATA-AUDIT.md` §5.5 — `de_sentences_test.txt` was included as training text in v1 and kept in v2 "for parity — flagged, not silently fixed."
- **mechanism:** Remove the German test file's lines from the training stream (v1 variant), champion re-run, and report held on German-source windows separately from the global held number — the contamination only matters if German windows are in or near the held set.
- **train.py:** corpus variant + champion re-run; the run string's `--corpus` value names the variant stream (`v1-node-test`), which does not exist yet, so screen.py defers this entry until the variant is built.
- **mode:** process — BitNet lab (corpus variant + champion re-run; cheap at probe scale first).
- **prediction:** Global held moves < 0.01 (the file is a small share), but the German-window slice moves measurably. The entry's real product is procedural: a corpus build rule (no *_test source ever enters a training stream) with one measured instance behind it.
- **status:** queued
```mill
id: E-021
mode: process
run: --arm layered_half --rope --corpus v1-node-test
```

### J-F8 — Mill methodology failures (from RIGOR-AUDIT)

### E-022 · Seed-0 false-negative audit (what did the screen silently kill?)
- **source:** idea-mining wave E (CANDIDATES-E.md), Family 8 — `RIGOR-AUDIT.md` §3a(i) — "seed 0 is never rotated, so an idea that is genuinely good but unlucky on seed 0 is ledgered and dead for the generation."
- **mechanism:** After the mill's first generation completes, take every probe ledgered `flat` or `below` within Δ 0.10 of job zero and re-probe it on seeds 1 and 2 (same budget, same pass conditions). Count how many would have promoted under a 2-of-3-seeds probe rule.
- **train.py:** no change — a mill audit pass over `mill/ledger.jsonl`. The run string's `--audit` marker is a methodology marker, not a trainer flag; it is not in train.py, so screen.py defers this entry, and the audit runs by hand after the first generation completes.
- **mode:** process — mill (post-generation audit pass over `ledger.jsonl`; no pool change). METHODOLOGY/audit entry: never a training probe.
- **prediction:** 5–15% of near-miss entries flip to promote on another seed. If the rate is ≥ 20%, single-seed screening is the mill's biggest throughput leak and probe format should change to 2 seeds at half budget; if ≤ 2%, seed-0 screening is vindicated with a number instead of an assumption.
- **status:** queued
```mill
id: E-022
mode: process
run: --arm layered_half --rope --audit seed-rotation
```

### E-023 · Fixed-step probes (remove the machine-speed confound)
- **source:** idea-mining wave E (CANDIDATES-E.md), Family 8 — `RIGOR-AUDIT.md` §2c + `RESULTS-JEPA-2026-11-12.md` — identical configs took 129–139 vs 154–170 steps in different windows; every wall-clock probe verdict inherits that variance, and one 2026-11-11 run was discarded outright for contention (52 steps vs 121–124 clean).
- **mechanism:** A probe-format variant judged at **equal steps** (e.g. 40 steps, however long they take) instead of equal wall time, run head-to-head against the standard 75 s probe on job zero + the first five queued entries: compare verdict agreement and verdict spread across repeated passes at different machine loads.
- **train.py:** no change — a screening-format experiment in `mill/sweep_probe.py`. The run string's `--probe-format` marker is not in train.py, so screen.py defers this entry; its verdicts are recorded as method data, not pool verdicts.
- **mode:** process — mill (screening-format experiment in `sweep_probe.py`; verdicts recorded as method data, not pool verdicts). METHODOLOGY entry: never a training probe.
- **prediction:** Fixed-step verdicts show ≥ 30% lower pass-to-pass spread under load, at the cost of unbounded probe wall time when the machine is busy. If spread does not improve, wall-clock probing stands and the step-count variance is smaller in practice than the JEPA window suggested.
- **status:** queued
```mill
id: E-023
mode: process
run: --arm layered_half --rope --probe-format fixed-steps
```

### J-F9 — Ternary substrate collapse, one niche only (factory)

### E-024 · Commit-type ternary autopsy + disagreement-harvest QAT
- **source:** idea-mining wave E (CANDIDATES-E.md), Family 9 — `factory/reports/factory-report.md` substrate line — commit-type-model is the lone substrate failure (fp 0.9625 → ternary 0.7625, cross-substrate agreement 0.7375).
- **mechanism:** Step 1 (measurement): per-class fp-vs-ternary confusion on the commit-type dev surface — is the 0.20 gap one class or uniform? Step 2 (the test): QAT for the ternary commit-type model with its training mix **harvested from fp/ternary disagreement items** (the factory's own dream/harvest machinery aimed at exactly the inputs the substrate change breaks), same candidate budget as the original ternary attempt.
- **train.py:** no change — factory substrate/QAT path. The run string's `--factory` marker names the factory surface; it is an encoding marker, not a trainer flag.
- **mode:** process — factory (substrate/QAT path; dev surfaces only, sealed untouched). NOT a train.py probe: screen.py defers this entry on the `--factory` marker (flag not in train.py); execution belongs to the factory queue.
- **prediction:** Step 1 shows the gap concentrated in ≤ 2 commit classes (the substrate pattern elsewhere is class-specific, cf. contract's ok→no-empty-guard cluster). Step 2 recovers ternary accuracy to ≥ 0.90 if disagreement harvesting works; if it stalls ≤ 0.82, commit-type has a genuine substrate capacity wall and the fp default is a finding, not a placeholder.
- **status:** queued
```mill
id: E-024
mode: process
run: --factory commit-type --substrate qat-disagreement
```

## K — Fable-trace methodology (merged from FABLE-CANDIDATES.md, 2026-11-12)

One entry: FABLE-CAND-01, a methodology rule for the mill itself, filed by the Fable
trace re-check (Fable's side commit 61fb325) and encoded here as a visible, permanently
deferred pool entry — never a training probe. The file's other two candidates were
routed OUT of the mill pool and are deliberately not entries here: FABLE-CAND-02
(Microsoft BitNet runtime validation recipe) belongs to the kernel/runtime cross-check
notes, and FABLE-CAND-03 (members-first routing) belongs to the factory composition
queue.

### FABLE-CAND-01 · Paired side-by-side timing (wall-clock comparisons are only valid between concurrent runs)
- **source:** Fable trace re-check (mill/FABLE-CANDIDATES.md) — Fable's side commit `61fb325`, HANDOFF.md 2026-11-13 04:15 UTC — **METHODOLOGY entry, not a performance candidate and not a training arm** (kept visible in the pool, where the mill's verdicts are made)
- **mechanism:** shared/contended CPU makes a fixed `--minutes` budget buy a variable number of steps (Fable's side: the same trivial sum took 22 s in one members sitting and 594 s in another — same code `baabc10`, seeds 9005 and 9006 — with many sittings running at once; a 27× swing on identical work). Any speed or equal-minutes comparison made across non-concurrent runs is measuring load, not the arm. Adoption on Muse's side: (a) any future "X is faster / equal-minutes" claim in the lab requires a paired, side-by-side re-run of both arms (the concurrency study's honesty protocol already pairs solo-vs-concurrent; extend the same pairing rule to arm-vs-arm timing claims); (b) ledger lines for verdict-bearing runs should be read alongside concurrent load — a held-loss delta from a contended window is suspect until re-run solo. This independently confirms the rigor audit's contention-asymmetry finding with an external, quantified example.
- **train.py:** no change, and no trainer flag should ever be created for this — the run string below carries a `--paired-timing` MARKER solely so screen.py lists the entry as deferred with a named reason instead of dropping it; the marker is not a flag to implement.
- **mode:** methods — METHODOLOGY: this entry is never a training probe and never becomes one; it states a judging rule for the mill (paired side-by-side timing; solo re-runs for contended verdicts). screen.py defers it on the marker flag (not in train.py), which is its intended permanent state.
- **prediction:** if the rule is ignored, expect occasional large false verdicts on timing-sensitive comparisons (observed swing: 27× on identical work); if applied, equal-minutes claims in the lab are load-independent by construction.
- **status:** deferred — methodology rule (adopted as judging practice; the pool entry exists for visibility only, never queued as a probe)
```mill
id: FABLE-CAND-01
mode: methods
run: --arm layered_half --rope --paired-timing
```

---
Merge note (round 2, 2026-11-12, pool merge stream): sections J–K add 25 entries
(E-001..E-024, FABLE-CAND-01) merged from mill/CANDIDATES-E.md and
mill/FABLE-CANDIDATES.md. Routed OUT of the pool per the routing instructions:
FABLE-CAND-02 (runtime validation recipe — belongs to the kernel/runtime cross-check
notes, not the mill) and FABLE-CAND-03 (members-first routing — belongs to the factory
composition queue, not the mill). No existing entry was dropped, renumbered, or
edited; the pool text above (through the round-1 merge note) and the appendix below
are byte-identical to the pre-merge file (backup: mill/IDEA-POOL.pre-merge2.md).
Pool size after merge: **380 entries** (355 + 25).

## Appendix — already tested and excluded (do not re-queue)

Measured in the lab's own RESULTS files; excluded so the mill never spends a probe
re-asking a settled question. (Calibrated/variant retests that change the mechanism's
setting are pooled as NEW entries and say so in their mechanism line.)

| Excluded | Where settled | Number |
|---|---|---|
| Overshoot carry (layered) | RESULTS-ROUND2-2026-11-12 | 2.8761 ± 0.0030 vs 2.8580 baseline — worse, +80% state. CLOSED. |
| AdamW two-stage cooldown (layered chassis) | RESULTS-ROUND2-2026-11-12 | 2.9707 ± 0.0108. CLOSED. (The STE-chassis two-stage recipe MILL-109/110 is a different, untested form.) |
| Vote-threshold annealing 8→64 | RESULTS-2026-11-11 | 3.850. CLOSED — the hot start was the poison; repaired schedules that never go below 32 are pooled (MILL-204..206). |
| Magnitude-weighted votes AS SPECIFIED (±96 threshold) | RESULTS-2026-11-11 | 3.135. The threshold was ~3x too cold for its increments; the calibrated retest is pooled (MILL-201..203). |
| JEPA objective (I-JEPA on this trunk) | RESULTS-JEPA-2026-11-12 | probe 3.2428 vs control 2.8935 vs untrained 3.2445. CLOSED at this scale/budget on the token yardstick. |
| Magnitude votes at full size | RESULTS-2026-11-11 | same arm as the ±96 row at full width. CLOSED. |
| Layered (full width) no-rope, plain/ste/mag/anneal arms at full format | RESULTS-2026-11-11 | measured: layered ~3.098, STE 2.995, plain ~3.074–3.09. Probe-format/rope combinations of the half arms are pooled as controls (MILL-1901..1903) because the mill's format differs. |
| RoPE adoption itself | RESULTS-ROPE-2026-11-11 | 2.8580 vs 2.8990 — adopted into the chassis; not re-litigated per probe. |
| Half-size control question | RESULTS-HALF-CONTROL-2026-11-12 | plain_half 2.9010 vs layered_half 2.8990 — settled: levels earn nothing at equal size/steps; the pool's component entries (MILL-401..405, 1401..1402) test NEW component counts/settings, not that settled comparison. |

Also excluded by the research report's do-not-test list: MLA/NSA/DSA/CSA at lab context,
Mixture-of-Depths for decode, mHC, activation quantization at 4 bits on CPU, FP4/FP8
training, quantizing recurrent state or gates, ternarizing embeddings before MILL-118
prices the table, ultra-sparse MoE (<8% activation), weight packing (kernel phase — it
changes speed, not loss), and the scale ladder's own rungs (the ladder owns them).


---
Pool size at build: **175 entries + job zero (MILL-000)**. Sweep-mode entries: 21 (incl. job zero). All status: queued.
