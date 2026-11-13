# Muse's work — Muse's side

# WAVE3-LENS1 — ARCHITECTURE SHAPES (Idea Engine, rotation 3, miner 1)

<!-- Muse's work — Muse's side of the BitNet lab. Fable's side read-only, untouched. -->

Territory: block STRUCTURE beyond the pooled uniform shape grid — non-uniform blocks,
mixed ternary/FP placement, depth-varying vote thresholds as an architectural choice,
asymmetric shapes, width concentrated where flip share is highest.

**Champion (control of record):** layered_half + rotary, dim 192 × 2 blocks, 884,736
ternary weights, held **2.8580 ± 0.0161**. Served bytes **3,806,208 B** (= FP32 tied
embedding/pos/final-norm 3,343,872 + layered ternary packed at 4 bits/position
442,368 + block-local FP norms/biases 19,968). Every entry below names its
equal-budget control: same ternary weights ±2%, both served-byte figures stated.
Ternary count per block at dim d, FFN width w: 4d² (attn) + 2·d·w (FFN); champion
block = 442,368 at d=192, w=768. All entries are `mode: process` (each needs a
per-block spec in train.py; sweep_probe.py cannot express non-uniform shapes today).

**Dedupe statement:** read in full — mill/IDEA-POOL.md, CANDIDATES-A/B/C/D/E/F/G,
FABLE-CANDIDATES.md. NOT re-proposed: the uniform shape grid (MILL-1101..1113),
uniform per-layer V (MILL-207/208, A-025 depth ramp, A-026 role ramp), QK-Norm
(MILL-101..103), gated attention (MILL-104..106), DeltaNet/RWKV hybrids
(MILL-116/117), all MoE forms (MILL-120..122), uniform heads 2/8 (MILL-903/904),
uniform component counts (MILL-1401/1402), plain/layered block mix (A-027),
recurrent depth (F-053), SWA ratios on the 4-block chassis (MILL-137/138). Nothing
closed is re-proposed: no carry, no cooldown, no anneal 8→64, no magnitude votes
as specified, no JEPA.

---

### AS-001 ★ · FFN width skew, late-wide: block 1 FFN width 512, block 2 FFN width 1024
- **source:** architecture-shapes lens (this wave); flip-share reasoning — in the champion the late block's FFN is where residual-stream features are already formed, so its down-projection flips carry the most loss signal per flip; width should sit where flip share is highest, not be split evenly by symmetry.
- **mechanism:** Residual dim stays 192 in both blocks; only the FFN intermediate width is redistributed: block 1 w=512 (344,064 ternary), block 2 w=1024 (540,672 ternary). Total exactly 884,736. Attention untouched. This is per-block dim variation on the block's internal dim — the uniform grid only ever moved both blocks together.
- **train.py:** `Block.__init__` gains `ffn_w` (default 4·dim); `Tiny` gains `--block-spec` parsing; exact run line below uses new flag `--ffn-widths 512,1024` threaded Tiny → Block (up = BitLinear(dim, w), down = BitLinear(w, dim)). Layered trainer collects the BitLinears unchanged.
- **mode:** process — code-path change (per-block spec); isolated until a full-trial record exists
- **prediction:** −0.02..−0.06 vs the equal-budget control (champion, 884,736 ternary, 3,806,208 B served; candidate also 3,806,208 B served — block-local FP is unchanged in sum). Kill condition: AS-008 (the reverse skew) beats AS-001 — then width follows depth in the other direction and the flip-share story is backwards.
- **status:** queued
```mill
id: AS-001
mode: process
run: --arm layered_half --rope --ffn-widths 512,1024
```

### AS-002 ★ · Decoupled sublayers: attention and FFN as separate residual sublayers (A–F–A–F)
- **source:** architecture-shapes lens; encoder-style reordering — the champion fuses attn+FFN into one block with two pre-norms; no pooled entry ever separates them into independently-normed residual steps.
- **mechanism:** Four sublayers in sequence, each with its own pre-norm and residual: Attn(d192) → FFN(w512) → Attn(d192) → FFN(w1024). Ternary: 147,456 + 196,608 + 147,456 + 393,216 = exactly 884,736. Each sublayer's output re-enters the residual stream before the next reads it, so the second attention sees FFN-processed features (the champion's block 2 attention also does — but here the first FFN is narrower and earlier, and there are 4 norm/residual boundaries instead of 2×2 fused).
- **train.py:** new `AttnSub` / `FFNSub` modules (split of `Block`), `Tiny` flag `--decoupled` builds [AttnSub, FFNSub(512), AttnSub, FFNSub(1024)] instead of 2 Blocks; rotary lives in AttnSub. Block-local FP identical in sum (4 norms + same bias total) → served bytes identical.
- **mode:** process — new block type; isolated until a full-trial record exists
- **prediction:** −0.01..−0.05 vs the equal-budget control (champion, 884,736 ternary, 3,806,208 B served; candidate 3,806,208 B served). Main risk: 4 sequential sublayers at probe horizon take the same steps but each gradient path is longer; a flat probe does not kill it, a flat full trial does.
- **status:** queued
```mill
id: AS-002
mode: process
run: --arm layered_half --rope --decoupled --ffn-widths 512,1024
```

### AS-003 ★ · One FP block, placed LAST: [ternary, ternary, FP] at exact ternary budget
- **source:** architecture-shapes lens; the mixed-precision placement question — if exactly one block earns FP, the prior says the last one: it writes directly into the final norm/head geometry, where ternary coarseness cannot be corrected downstream.
- **mechanism:** Three blocks at dim 192: blocks 1–2 are champion layered-ternary blocks (442,368 ternary each = 884,736 total, exact), block 3 is a plain FP block (nn.Linear, no BitLinear) trained by the shared AdamW parts path (the Layered trainer already routes every non-BitLinear parameter to its AdamW group). Depth grows 2→3; the FP block is the priced variable.
- **train.py:** `Block` gains `fp=False` (swaps BitLinear → nn.Linear); `Tiny` flag `--fp-block last` with `--layers-n 3` on a new arm variant `layered_2t1f` (arm plumbing mirrors `layered_half`). FP block's weights must be excluded from `n_tern` accounting and included in served bytes (train.py already counts only BitLinear weights for vote arms — verify at wiring).
- **mode:** process — new block variant; isolated until a full-trial record exists
- **prediction:** −0.03..−0.08 on held loss vs the equal-ternary control (champion, 884,736 ternary, 3,806,208 B served) — but candidate served bytes are **5,585,664 B** (+46.7%: FP block weights 1,769,472 B + its local FP 9,984 B). Adoption bar is therefore per-byte: it must beat the champion by ≥0.05 to earn its bytes, else the verdict is "no single block earns FP at this scale" — itself the answer to the placement question. Paired placement arm: AS-006.
- **status:** queued
```mill
id: AS-003
mode: process
run: --arm layered_2t1f --rope --fp-block last
```

### AS-004 · Residual taper, growing: 160 → 224 (narrow entry, wide exit)
- **source:** architecture-shapes lens; asymmetric encoder-style shape — cheap narrow processing first, wide capacity where features are formed; the reverse of the usual pyramid.
- **mechanism:** Embedding/residual entry dim 160; block 1 at d=160, FFN w=520 (268,800); ternary transition projection 160→224 (35,840); block 2 at d=224, FFN w=768 (544,768); ternary return projection 224→160 (35,840) restoring the tied-head dim. Total ternary 885,248 (+0.06% vs champion). Transition projections are BitLinears, vote-trained like everything else.
- **train.py:** `Tiny` gains per-block dims + transition BitLinears via `--block-dims 160,224 --ffn-widths 520,768`; transitions inserted in `Tiny.body` between blocks and before the final norm. Layered trainer picks them up automatically (it collects all BitLinears).
- **mode:** process — shape plumbing change; isolated until a full-trial record exists
- **prediction:** −0.01..−0.05 vs the equal-budget control (champion, 884,736 ternary, 3,806,208 B served). Candidate served bytes **3,249,696 B** (−14.6%: the 160-wide embedding table is 557 kB cheaper, partly repaid by the 224-wide block) — so even a tie on held loss is a per-byte win. Paired direction arm: AS-007 (same ternary count, opposite taper) separates "growth helps" from "any asymmetry helps".
- **status:** queued
```mill
id: AS-004
mode: process
run: --arm layered_half --rope --block-dims 160,224 --ffn-widths 520,768
```

### AS-005 · Asymmetric attention inner width: block 1 bottlenecked (inner 96), block 2 expanded (inner 288)
- **source:** architecture-shapes lens; attention capacity per block has never been varied independently of dim — pooled head-count entries (MILL-903/904) keep inner width = dim in every block.
- **mechanism:** Head count fixed at 4, residual dim 192. Block 1: qkv projects to inner 96 (head_dim 24), out projects 96→192 — attn ternary 73,728. Block 2: inner 288 (head_dim 72), attn ternary 221,184. Attention total 294,912 = champion's, FFN untouched, grand total exactly 884,736. RoPE pair counts follow head_dim per block (12 vs 36 pairs). Early attention is forced into a low-rank summary; late attention gets the wide read.
- **train.py:** `Block` gains `attn_inner` (qkv = BitLinear(dim, 3·attn_inner), out = BitLinear(attn_inner, dim); RoPE buffers built from attn_inner//heads); flag `--attn-inners 96,288`.
- **mode:** process — Block geometry change; isolated until a full-trial record exists
- **prediction:** −0.01..−0.04 vs the equal-budget control (champion, 884,736 ternary, 3,806,208 B served; candidate also 3,806,208 B — bias totals are unchanged in sum). Secondary read: if block-1 bottleneck costs nothing, attention inner width is over-provisioned early — evidence for cheaper early blocks at scale.
- **status:** queued
```mill
id: AS-005
mode: process
run: --arm layered_half --rope --attn-inners 96,288
```

### AS-006 · One FP block, placed FIRST: [FP, ternary, ternary] at exact ternary budget
- **source:** architecture-shapes lens; the other half of AS-003's placement question — the counter-prior: the first block sets the feature basis everything downstream reads, so FP precision there compounds.
- **mechanism:** Identical construction to AS-003 with the FP block at position 1 and the two layered-ternary blocks after it. Ternary exactly 884,736; served bytes identical to AS-003 (5,585,664 B).
- **train.py:** same `--fp-block first` plumbing as AS-003 (shared implementation; this entry is the placement arm, not new code).
- **mode:** process — placement variant; isolated until a full-trial record exists
- **prediction:** −0.01..−0.06 vs the equal-ternary control (champion, 884,736 ternary, 3,806,208 B served). The deliverable is the AS-003 vs AS-006 difference: whichever placement wins prices where precision matters in a 2-ternary-block stack; if both land within noise of each other but above the champion, placement doesn't matter, only the FP block's existence does. Same per-byte adoption bar as AS-003 (≥0.05 over champion).
- **status:** queued
```mill
id: AS-006
mode: process
run: --arm layered_2t1f --rope --fp-block first
```

### AS-007 · Residual taper, shrinking: 224 → 160 (wide entry, narrow exit)
- **source:** architecture-shapes lens; the classic pyramid direction, paired against AS-004 at identical ternary count.
- **mechanism:** Embedding/residual entry dim 224; block 1 at d=224, FFN w=768 (544,768); ternary transition 224→160 (35,840); block 2 at d=160, FFN w=520 (268,800); ternary return projection 160→224 (35,840). Total ternary 885,248 (+0.06%), exactly AS-004's count with the widths swapped by depth.
- **train.py:** same `--block-dims / --ffn-widths` plumbing as AS-004: `--block-dims 224,160 --ffn-widths 768,520`.
- **mode:** process — shape plumbing change (shared with AS-004); isolated until a full-trial record exists
- **prediction:** −0.00..−0.04 vs the equal-budget control (champion, 884,736 ternary, 3,806,208 B served). Candidate served bytes **4,364,320 B** (+14.7%: the 224-wide embedding table dominates) — so this arm must win on loss outright, not per byte; its real job is the direction verdict against AS-004 at equal ternary count.
- **status:** queued
```mill
id: AS-007
mode: process
run: --arm layered_half --rope --block-dims 224,160 --ffn-widths 768,520
```

### AS-008 · FFN width skew, early-wide (reverse of AS-001): block 1 width 1024, block 2 width 512
- **source:** architecture-shapes lens; the direction control for AS-001 — a skew family without its reverse cannot distinguish "late width wins" from "any skew wins".
- **mechanism:** Exact mirror of AS-001: block 1 w=1024 (540,672 ternary), block 2 w=512 (344,064); total exactly 884,736, served bytes identical (3,806,208 B).
- **train.py:** same `--ffn-widths` flag as AS-001: `--ffn-widths 1024,512`.
- **mode:** process — config variant on AS-001's plumbing; isolated until a full-trial record exists
- **prediction:** +0.00..+0.03 vs the equal-budget control (champion, 884,736 ternary, 3,806,208 B served) — expected to lose slightly if the flip-share-late story is right. Its value is falsification: if AS-008 ≥ AS-001, the skew direction claim dies and only total-width redistribution noise remains.
- **status:** queued
```mill
id: AS-008
mode: process
run: --arm layered_half --rope --ffn-widths 1024,512
```

### AS-009 · Per-block component asymmetry: block 1 plain (1 component), block 2 triple (3 components, 7 levels)
- **source:** architecture-shapes lens; level-count as a per-block architectural variable. Pooled neighbours are uniform component counts (MILL-1401/1402: 4–5 everywhere) and the 1-vs-2 block mix (A-027) — a 1-vs-3 split, concentrating all level resolution in the late block, is untested.
- **mechanism:** Same positions in both blocks (884,736 total, exact). Block 1 weights are single ternary (levels −1..+1, 1 counter each); block 2 weights are a sum of three independently vote-trained ternary components (levels −3..+3, 3 counters each, one flip per weight per step, t1-first rule generalised). Packed served bytes are unchanged in sum: block 1 at 2 bits/position (110,592 B) + block 2 at 6 bits/position (331,776 B) = 442,368 B. Trainer state rises (4 counters/position average vs 2) — charged honestly, not a served cost.
- **train.py:** `Layered` gains per-layer component counts: constructor arg `components=[1,3]` mapped from each BitLinear's parent block; flag `--components 1,3`. Install sums the block's components; the one-flip rule iterates components in order.
- **mode:** process — trainer generalisation; isolated until a full-trial record exists
- **prediction:** −0.01..−0.04 vs the equal-budget control (champion, 884,736 ternary, 3,806,208 B served; candidate 3,806,208 B served). Prior from the half-control (levels earn ~nothing when uniform) says the gain, if any, comes from putting resolution only where the residual stream is richest — a null result extends "levels don't earn" to the asymmetric case and closes the component axis.
- **status:** queued
```mill
id: AS-009
mode: process
run: --arm layered_half --rope --components 1,3
```

### AS-010 · Width-coupled vote thresholds on the skewed shape: V=16 on the narrow block, V=48 on the wide block
- **source:** architecture-shapes lens; depth-varying V as an ARCHITECTURAL choice tied to block width, not a schedule (no time variation) and not the pooled forms: MILL-207/208 adapt V to a flip-rate target, A-025 ramps V by depth on identical blocks. Here V is a static function of the block's fan-in, testable only because the blocks differ.
- **mechanism:** On AS-001's shape (FFN widths 512/1024), the narrow block's counters flip at V=16 and the wide block's at V=48 — wide matrices accumulate more conflicting votes per weight, so each flip should demand more net evidence; narrow blocks should stay nimble. Control is AS-001 itself (same shape, uniform V=32): the pair isolates the threshold geometry from the shape.
- **train.py:** `Layered` gains `votes_per_block` (constructor list, applied by parent-block index in `step`); flag `--votes-per-block 16,48` combined with `--ffn-widths 512,1024`.
- **mode:** process — trainer change on AS-001's plumbing; isolated until a full-trial record exists
- **prediction:** −0.01..−0.03 vs its equal-budget control (AS-001: same 884,736 ternary, same 3,806,208 B served, uniform V=32). If it wins, V becomes a shape-derived quantity (V ∝ block width) rather than a global constant — a rule that transfers to the ladder rungs, where fan-in varies 3×.
- **status:** queued
```mill
id: AS-010
mode: process
run: --arm layered_half --rope --ffn-widths 512,1024 --votes-per-block 16,48
```

### AS-011 · Per-block head asymmetry: block 1 has 2 heads (head_dim 96), block 2 has 8 heads (head_dim 24)
- **source:** architecture-shapes lens; head granularity as a per-block variable. Pooled head entries (MILL-903/904) change head count uniformly across all blocks; no entry splits it by depth.
- **mechanism:** Ternary count is exactly unchanged (qkv/out sizes depend on dim only): block 1 attends with 2 wide heads (coarse, long-range mixing), block 2 with 8 narrow heads (fine, specialised matching). RoPE pairs per block follow head_dim (48 vs 12 pairs). Everything else champion.
- **train.py:** `Tiny` threads a per-block `heads` list into `Block(dim, heads=h)` (Block already accepts `heads`); flag `--heads-per-block 2,8`. RoPE buffer construction already derives from dim//heads per block — verify per-block buffers at wiring.
- **mode:** process — model plumbing change; isolated until a full-trial record exists
- **prediction:** −0.01..+0.02 vs the equal-budget control (champion, 884,736 ternary, 3,806,208 B served; candidate identical bytes) — genuinely uncertain direction; the cheap probe prices whether head granularity should be spent early or late, which no uniform-grid point can answer.
- **status:** queued
```mill
id: AS-011
mode: process
run: --arm layered_half --rope --heads-per-block 2,8
```

### AS-012 · Depth-tapered attention window: block 1 global (256), block 2 local (window 64)
- **source:** architecture-shapes lens; window as a per-block depth variable on the 2-block chassis. Distinct from pooled MILL-137/138 (3:1 / 5:1 local:global ratios on a 4-block chassis): here the single late block is local, the single early block is global — a taper, not a ratio.
- **mechanism:** Block 1 attends over the full ctx 256; block 2 attends only to the last 64 positions (causal sliding window). Zero parameter change: ternary exactly 884,736, served bytes identical. Hypothesis: early global mixing builds the context summary; late local attention refines next-token detail, and restricting it removes long-range ternary logit noise from the block closest to the head.
- **train.py:** `Block` gains `window` (forward builds a cached banded causal mask when window < ctx, passed to SDPA as `attn_mask`); flag `--windows 256,64`.
- **mode:** process — attention-mask code path; isolated until a full-trial record exists
- **prediction:** −0.01..+0.02 on held loss vs the equal-budget control (champion, 884,736 ternary, 3,806,208 B served; candidate identical) at ctx 256 — near-flat is the honest prior at this context length; the side readings are the point (KV/attention cost at serve, and whether the local block's flip share rises when its logit field shrinks). A win here re-opens window shape as a depth axis for longer contexts.
- **status:** queued
```mill
id: AS-012
mode: process
run: --arm layered_half --rope --windows 256,64
```

---

## Rank summary

| Rank | ID | Shape move | Ternary vs champion | Served bytes (candidate / control) |
|---|---|---|---|---|
| 1 ★ | AS-001 | FFN width skew, late-wide (512→1024) | 884,736 (exact) | 3,806,208 / 3,806,208 |
| 2 ★ | AS-002 | Decoupled A–F–A–F sublayers | 884,736 (exact) | 3,806,208 / 3,806,208 |
| 3 ★ | AS-003 | FP block last, ternary budget restored | 884,736 (exact) | 5,585,664 / 3,806,208 |
| 4 | AS-004 | Residual taper growing 160→224 | 885,248 (+0.06%) | 3,249,696 / 3,806,208 |
| 5 | AS-005 | Attention inner width 96 / 288 | 884,736 (exact) | 3,806,208 / 3,806,208 |
| 6 | AS-006 | FP block first (placement pair) | 884,736 (exact) | 5,585,664 / 3,806,208 |
| 7 | AS-007 | Residual taper shrinking 224→160 | 885,248 (+0.06%) | 4,364,320 / 3,806,208 |
| 8 | AS-008 | FFN width skew, early-wide (reverse control) | 884,736 (exact) | 3,806,208 / 3,806,208 |
| 9 | AS-009 | Components 1 vs 3 per block | 884,736 (exact) | 3,806,208 / 3,806,208 |
| 10 | AS-010 | Width-coupled V (16 / 48) on AS-001 shape | 884,736 (exact) | 3,806,208 / 3,806,208 |
| 11 | AS-011 | Heads 2 / 8 per block | 884,736 (exact) | 3,806,208 / 3,806,208 |
| 12 | AS-012 | Window taper 256 / 64 per block | 884,736 (exact) | 3,806,208 / 3,806,208 |

Controls: champion (layered_half + rotary, 2.8580 ± 0.0161) for all entries except
AS-010, whose control is AS-001 (same shape, uniform V=32) — stated in its entry.
