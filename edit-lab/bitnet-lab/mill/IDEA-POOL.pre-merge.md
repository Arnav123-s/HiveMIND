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
