# CANDIDATES-H — Idea Engine wave H (Muse's work, Muse's side)

<!-- Muse's work — Muse's side of the BitNet lab. Produced 2026-11-12 by the Idea Engine
(rotation 3: architecture shapes, vocabulary, auxiliary signals, robustness, counter
forensics, cross-pollination) under Arnav's no-limit ideation order. CANDIDATE file:
nothing here is in the pool until the pool's owner merges it. IDEA-POOL.md was read by
every miner and NOT edited. Entry ids use the WH- prefix to stay distinct from the
factory file's H-### ids (factory/CANDIDATES-IDEAS.md). Waves F and G are
CANDIDATES-F.md / CANDIDATES-G.md. -->

## Method and de-duplication

Every miner deduped against IDEA-POOL.md (368 entries), CANDIDATES-A/B/C/D/E/F/G and
FABLE-CANDIDATES.md. Nothing closed re-proposed (overshoot carry, AdamW cooldown,
threshold anneal 8→64, magnitude votes as specified, JEPA objective — the auxiliary
lens enforced the JEPA boundary entry by entry). Chassis/bars as in waves F/G:
champion held 2.8580 ± 0.0161; adoption >2sd AND >0.01.

**Cross-wave coherence worth the pool owner's attention:** WH-051 (frustration census)
MEASURES the population that wave F's top entry F-001 wants to reroute — the fraction
of weights saturated at ±32 pushing against a boundary no-op, predicted 4–8% in
champion-family runs vs >15% in catastrophe-class. If the census lands first, F-001's
predicted effect size stops being an estimate.

## Coordinator's top 3 for this wave ★

1. **WH-037 · Serving fault injection — the fragility may live in the FP minority.**
   Ternary flips are predicted graceful (1% → +0.03..+0.10), but a single exponent-bit
   flip in one FP `log_scale` is predicted at Δ ≥ +0.5. If true, hardening priority
   inverts for every model the lab ships: protect a few hundred FP scalars first, at
   ~zero cost, before any ternary redundancy. Eval-side, on copies of trained state.
2. **WH-014 · Embedding rows join the vote trainer.** The tied table is 3,145,728 B —
   ≈83% of the champion's served bytes — and no embedding row has ever voted. Ternary
   vote-trained rows with per-row scales cut served bytes 3.81 MB → ~0.86 MB, with a
   pre-stated per-byte adoption bar (≤ +0.05 nats/token wins; ≥ +0.12 kills the family).
3. **WH-051 · Frustration census.** Exactly computable from one state dump — no fitted
   model, no eval pass — doubles as the scale ladder's mechanism-native capacity gauge
   and a halfway kill signal for doomed runs (frustration still rising at 50% ⇒
   second-half gain < 0.01 in ≥80% of runs, if the signature holds).

**Most honest entry in the wave: WH-063 · Growth shape schedule, dual-currency** —
transplants Fable's side's equal-work verdict (grown 3.1704 vs plain 3.1017 at 6,420
block-steps; grown wins only at equal clock, 3.085) and pre-registers BOTH verdicts:
predicted to lose step-matched (+0.02..+0.05) and win minute-matched (−0.01..−0.03).

---

## Lens 1 — Architecture shapes (was AS-###)

### WH-001 ★ · FFN width skew, late-wide: block 1 FFN width 512, block 2 FFN width 1024
- **source:** architecture-shapes lens (this wave); flip-share reasoning — in the champion the late block's FFN is where residual-stream features are already formed, so its down-projection flips carry the most loss signal per flip; width should sit where flip share is highest, not be split evenly by symmetry.
- **mechanism:** Residual dim stays 192 in both blocks; only the FFN intermediate width is redistributed: block 1 w=512 (344,064 ternary), block 2 w=1024 (540,672 ternary). Total exactly 884,736. Attention untouched. This is per-block dim variation on the block's internal dim — the uniform grid only ever moved both blocks together.
- **train.py:** `Block.__init__` gains `ffn_w` (default 4·dim); `Tiny` gains `--block-spec` parsing; exact run line below uses new flag `--ffn-widths 512,1024` threaded Tiny → Block (up = BitLinear(dim, w), down = BitLinear(w, dim)). Layered trainer collects the BitLinears unchanged.
- **mode:** process — code-path change (per-block spec); isolated until a full-trial record exists
- **prediction:** −0.02..−0.06 vs the equal-budget control (champion, 884,736 ternary, 3,806,208 B served; candidate also 3,806,208 B served — block-local FP is unchanged in sum). Kill condition: WH-008 (the reverse skew) beats WH-001 — then width follows depth in the other direction and the flip-share story is backwards.
- **status:** queued
```mill
id: WH-001
mode: process
run: --arm layered_half --rope --ffn-widths 512,1024
```

### WH-002 ★ · Decoupled sublayers: attention and FFN as separate residual sublayers (A–F–A–F)
- **source:** architecture-shapes lens; encoder-style reordering — the champion fuses attn+FFN into one block with two pre-norms; no pooled entry ever separates them into independently-normed residual steps.
- **mechanism:** Four sublayers in sequence, each with its own pre-norm and residual: Attn(d192) → FFN(w512) → Attn(d192) → FFN(w1024). Ternary: 147,456 + 196,608 + 147,456 + 393,216 = exactly 884,736. Each sublayer's output re-enters the residual stream before the next reads it, so the second attention sees FFN-processed features (the champion's block 2 attention also does — but here the first FFN is narrower and earlier, and there are 4 norm/residual boundaries instead of 2×2 fused).
- **train.py:** new `AttnSub` / `FFNSub` modules (split of `Block`), `Tiny` flag `--decoupled` builds [AttnSub, FFNSub(512), AttnSub, FFNSub(1024)] instead of 2 Blocks; rotary lives in AttnSub. Block-local FP identical in sum (4 norms + same bias total) → served bytes identical.
- **mode:** process — new block type; isolated until a full-trial record exists
- **prediction:** −0.01..−0.05 vs the equal-budget control (champion, 884,736 ternary, 3,806,208 B served; candidate 3,806,208 B served). Main risk: 4 sequential sublayers at probe horizon take the same steps but each gradient path is longer; a flat probe does not kill it, a flat full trial does.
- **status:** queued
```mill
id: WH-002
mode: process
run: --arm layered_half --rope --decoupled --ffn-widths 512,1024
```

### WH-003 ★ · One FP block, placed LAST: [ternary, ternary, FP] at exact ternary budget
- **source:** architecture-shapes lens; the mixed-precision placement question — if exactly one block earns FP, the prior says the last one: it writes directly into the final norm/head geometry, where ternary coarseness cannot be corrected downstream.
- **mechanism:** Three blocks at dim 192: blocks 1–2 are champion layered-ternary blocks (442,368 ternary each = 884,736 total, exact), block 3 is a plain FP block (nn.Linear, no BitLinear) trained by the shared AdamW parts path (the Layered trainer already routes every non-BitLinear parameter to its AdamW group). Depth grows 2→3; the FP block is the priced variable.
- **train.py:** `Block` gains `fp=False` (swaps BitLinear → nn.Linear); `Tiny` flag `--fp-block last` with `--layers-n 3` on a new arm variant `layered_2t1f` (arm plumbing mirrors `layered_half`). FP block's weights must be excluded from `n_tern` accounting and included in served bytes (train.py already counts only BitLinear weights for vote arms — verify at wiring).
- **mode:** process — new block variant; isolated until a full-trial record exists
- **prediction:** −0.03..−0.08 on held loss vs the equal-ternary control (champion, 884,736 ternary, 3,806,208 B served) — but candidate served bytes are **5,585,664 B** (+46.7%: FP block weights 1,769,472 B + its local FP 9,984 B). Adoption bar is therefore per-byte: it must beat the champion by ≥0.05 to earn its bytes, else the verdict is "no single block earns FP at this scale" — itself the answer to the placement question. Paired placement arm: WH-006.
- **status:** queued
```mill
id: WH-003
mode: process
run: --arm layered_2t1f --rope --fp-block last
```

### WH-004 · Residual taper, growing: 160 → 224 (narrow entry, wide exit)
- **source:** architecture-shapes lens; asymmetric encoder-style shape — cheap narrow processing first, wide capacity where features are formed; the reverse of the usual pyramid.
- **mechanism:** Embedding/residual entry dim 160; block 1 at d=160, FFN w=520 (268,800); ternary transition projection 160→224 (35,840); block 2 at d=224, FFN w=768 (544,768); ternary return projection 224→160 (35,840) restoring the tied-head dim. Total ternary 885,248 (+0.06% vs champion). Transition projections are BitLinears, vote-trained like everything else.
- **train.py:** `Tiny` gains per-block dims + transition BitLinears via `--block-dims 160,224 --ffn-widths 520,768`; transitions inserted in `Tiny.body` between blocks and before the final norm. Layered trainer picks them up automatically (it collects all BitLinears).
- **mode:** process — shape plumbing change; isolated until a full-trial record exists
- **prediction:** −0.01..−0.05 vs the equal-budget control (champion, 884,736 ternary, 3,806,208 B served). Candidate served bytes **3,249,696 B** (−14.6%: the 160-wide embedding table is 557 kB cheaper, partly repaid by the 224-wide block) — so even a tie on held loss is a per-byte win. Paired direction arm: WH-007 (same ternary count, opposite taper) separates "growth helps" from "any asymmetry helps".
- **status:** queued
```mill
id: WH-004
mode: process
run: --arm layered_half --rope --block-dims 160,224 --ffn-widths 520,768
```

### WH-005 · Asymmetric attention inner width: block 1 bottlenecked (inner 96), block 2 expanded (inner 288)
- **source:** architecture-shapes lens; attention capacity per block has never been varied independently of dim — pooled head-count entries (MILL-903/904) keep inner width = dim in every block.
- **mechanism:** Head count fixed at 4, residual dim 192. Block 1: qkv projects to inner 96 (head_dim 24), out projects 96→192 — attn ternary 73,728. Block 2: inner 288 (head_dim 72), attn ternary 221,184. Attention total 294,912 = champion's, FFN untouched, grand total exactly 884,736. RoPE pair counts follow head_dim per block (12 vs 36 pairs). Early attention is forced into a low-rank summary; late attention gets the wide read.
- **train.py:** `Block` gains `attn_inner` (qkv = BitLinear(dim, 3·attn_inner), out = BitLinear(attn_inner, dim); RoPE buffers built from attn_inner//heads); flag `--attn-inners 96,288`.
- **mode:** process — Block geometry change; isolated until a full-trial record exists
- **prediction:** −0.01..−0.04 vs the equal-budget control (champion, 884,736 ternary, 3,806,208 B served; candidate also 3,806,208 B — bias totals are unchanged in sum). Secondary read: if block-1 bottleneck costs nothing, attention inner width is over-provisioned early — evidence for cheaper early blocks at scale.
- **status:** queued
```mill
id: WH-005
mode: process
run: --arm layered_half --rope --attn-inners 96,288
```

### WH-006 · One FP block, placed FIRST: [FP, ternary, ternary] at exact ternary budget
- **source:** architecture-shapes lens; the other half of WH-003's placement question — the counter-prior: the first block sets the feature basis everything downstream reads, so FP precision there compounds.
- **mechanism:** Identical construction to WH-003 with the FP block at position 1 and the two layered-ternary blocks after it. Ternary exactly 884,736; served bytes identical to WH-003 (5,585,664 B).
- **train.py:** same `--fp-block first` plumbing as WH-003 (shared implementation; this entry is the placement arm, not new code).
- **mode:** process — placement variant; isolated until a full-trial record exists
- **prediction:** −0.01..−0.06 vs the equal-ternary control (champion, 884,736 ternary, 3,806,208 B served). The deliverable is the WH-003 vs WH-006 difference: whichever placement wins prices where precision matters in a 2-ternary-block stack; if both land within noise of each other but above the champion, placement doesn't matter, only the FP block's existence does. Same per-byte adoption bar as WH-003 (≥0.05 over champion).
- **status:** queued
```mill
id: WH-006
mode: process
run: --arm layered_2t1f --rope --fp-block first
```

### WH-007 · Residual taper, shrinking: 224 → 160 (wide entry, narrow exit)
- **source:** architecture-shapes lens; the classic pyramid direction, paired against WH-004 at identical ternary count.
- **mechanism:** Embedding/residual entry dim 224; block 1 at d=224, FFN w=768 (544,768); ternary transition 224→160 (35,840); block 2 at d=160, FFN w=520 (268,800); ternary return projection 160→224 (35,840). Total ternary 885,248 (+0.06%), exactly WH-004's count with the widths swapped by depth.
- **train.py:** same `--block-dims / --ffn-widths` plumbing as WH-004: `--block-dims 224,160 --ffn-widths 768,520`.
- **mode:** process — shape plumbing change (shared with WH-004); isolated until a full-trial record exists
- **prediction:** −0.00..−0.04 vs the equal-budget control (champion, 884,736 ternary, 3,806,208 B served). Candidate served bytes **4,364,320 B** (+14.7%: the 224-wide embedding table dominates) — so this arm must win on loss outright, not per byte; its real job is the direction verdict against WH-004 at equal ternary count.
- **status:** queued
```mill
id: WH-007
mode: process
run: --arm layered_half --rope --block-dims 224,160 --ffn-widths 768,520
```

### WH-008 · FFN width skew, early-wide (reverse of WH-001): block 1 width 1024, block 2 width 512
- **source:** architecture-shapes lens; the direction control for WH-001 — a skew family without its reverse cannot distinguish "late width wins" from "any skew wins".
- **mechanism:** Exact mirror of WH-001: block 1 w=1024 (540,672 ternary), block 2 w=512 (344,064); total exactly 884,736, served bytes identical (3,806,208 B).
- **train.py:** same `--ffn-widths` flag as WH-001: `--ffn-widths 1024,512`.
- **mode:** process — config variant on WH-001's plumbing; isolated until a full-trial record exists
- **prediction:** +0.00..+0.03 vs the equal-budget control (champion, 884,736 ternary, 3,806,208 B served) — expected to lose slightly if the flip-share-late story is right. Its value is falsification: if WH-008 ≥ WH-001, the skew direction claim dies and only total-width redistribution noise remains.
- **status:** queued
```mill
id: WH-008
mode: process
run: --arm layered_half --rope --ffn-widths 1024,512
```

### WH-009 · Per-block component asymmetry: block 1 plain (1 component), block 2 triple (3 components, 7 levels)
- **source:** architecture-shapes lens; level-count as a per-block architectural variable. Pooled neighbours are uniform component counts (MILL-1401/1402: 4–5 everywhere) and the 1-vs-2 block mix (A-027) — a 1-vs-3 split, concentrating all level resolution in the late block, is untested.
- **mechanism:** Same positions in both blocks (884,736 total, exact). Block 1 weights are single ternary (levels −1..+1, 1 counter each); block 2 weights are a sum of three independently vote-trained ternary components (levels −3..+3, 3 counters each, one flip per weight per step, t1-first rule generalised). Packed served bytes are unchanged in sum: block 1 at 2 bits/position (110,592 B) + block 2 at 6 bits/position (331,776 B) = 442,368 B. Trainer state rises (4 counters/position average vs 2) — charged honestly, not a served cost.
- **train.py:** `Layered` gains per-layer component counts: constructor arg `components=[1,3]` mapped from each BitLinear's parent block; flag `--components 1,3`. Install sums the block's components; the one-flip rule iterates components in order.
- **mode:** process — trainer generalisation; isolated until a full-trial record exists
- **prediction:** −0.01..−0.04 vs the equal-budget control (champion, 884,736 ternary, 3,806,208 B served; candidate 3,806,208 B served). Prior from the half-control (levels earn ~nothing when uniform) says the gain, if any, comes from putting resolution only where the residual stream is richest — a null result extends "levels don't earn" to the asymmetric case and closes the component axis.
- **status:** queued
```mill
id: WH-009
mode: process
run: --arm layered_half --rope --components 1,3
```

### WH-010 · Width-coupled vote thresholds on the skewed shape: V=16 on the narrow block, V=48 on the wide block
- **source:** architecture-shapes lens; depth-varying V as an ARCHITECTURAL choice tied to block width, not a schedule (no time variation) and not the pooled forms: MILL-207/208 adapt V to a flip-rate target, A-025 ramps V by depth on identical blocks. Here V is a static function of the block's fan-in, testable only because the blocks differ.
- **mechanism:** On WH-001's shape (FFN widths 512/1024), the narrow block's counters flip at V=16 and the wide block's at V=48 — wide matrices accumulate more conflicting votes per weight, so each flip should demand more net evidence; narrow blocks should stay nimble. Control is WH-001 itself (same shape, uniform V=32): the pair isolates the threshold geometry from the shape.
- **train.py:** `Layered` gains `votes_per_block` (constructor list, applied by parent-block index in `step`); flag `--votes-per-block 16,48` combined with `--ffn-widths 512,1024`.
- **mode:** process — trainer change on WH-001's plumbing; isolated until a full-trial record exists
- **prediction:** −0.01..−0.03 vs its equal-budget control (WH-001: same 884,736 ternary, same 3,806,208 B served, uniform V=32). If it wins, V becomes a shape-derived quantity (V ∝ block width) rather than a global constant — a rule that transfers to the ladder rungs, where fan-in varies 3×.
- **status:** queued
```mill
id: WH-010
mode: process
run: --arm layered_half --rope --ffn-widths 512,1024 --votes-per-block 16,48
```

### WH-011 · Per-block head asymmetry: block 1 has 2 heads (head_dim 96), block 2 has 8 heads (head_dim 24)
- **source:** architecture-shapes lens; head granularity as a per-block variable. Pooled head entries (MILL-903/904) change head count uniformly across all blocks; no entry splits it by depth.
- **mechanism:** Ternary count is exactly unchanged (qkv/out sizes depend on dim only): block 1 attends with 2 wide heads (coarse, long-range mixing), block 2 with 8 narrow heads (fine, specialised matching). RoPE pairs per block follow head_dim (48 vs 12 pairs). Everything else champion.
- **train.py:** `Tiny` threads a per-block `heads` list into `Block(dim, heads=h)` (Block already accepts `heads`); flag `--heads-per-block 2,8`. RoPE buffer construction already derives from dim//heads per block — verify per-block buffers at wiring.
- **mode:** process — model plumbing change; isolated until a full-trial record exists
- **prediction:** −0.01..+0.02 vs the equal-budget control (champion, 884,736 ternary, 3,806,208 B served; candidate identical bytes) — genuinely uncertain direction; the cheap probe prices whether head granularity should be spent early or late, which no uniform-grid point can answer.
- **status:** queued
```mill
id: WH-011
mode: process
run: --arm layered_half --rope --heads-per-block 2,8
```

### WH-012 · Depth-tapered attention window: block 1 global (256), block 2 local (window 64)
- **source:** architecture-shapes lens; window as a per-block depth variable on the 2-block chassis. Distinct from pooled MILL-137/138 (3:1 / 5:1 local:global ratios on a 4-block chassis): here the single late block is local, the single early block is global — a taper, not a ratio.
- **mechanism:** Block 1 attends over the full ctx 256; block 2 attends only to the last 64 positions (causal sliding window). Zero parameter change: ternary exactly 884,736, served bytes identical. Hypothesis: early global mixing builds the context summary; late local attention refines next-token detail, and restricting it removes long-range ternary logit noise from the block closest to the head.
- **train.py:** `Block` gains `window` (forward builds a cached banded causal mask when window < ctx, passed to SDPA as `attn_mask`); flag `--windows 256,64`.
- **mode:** process — attention-mask code path; isolated until a full-trial record exists
- **prediction:** −0.01..+0.02 on held loss vs the equal-budget control (champion, 884,736 ternary, 3,806,208 B served; candidate identical) at ctx 256 — near-flat is the honest prior at this context length; the side readings are the point (KV/attention cost at serve, and whether the local block's flip share rises when its logit field shrinks). A win here re-opens window shape as a depth axis for longer contexts.
- **status:** queued
```mill
id: WH-012
mode: process
run: --arm layered_half --rope --windows 256,64
```

---

## Rank summary

| Rank | ID | Shape move | Ternary vs champion | Served bytes (candidate / control) |
|---|---|---|---|---|
| 1 ★ | WH-001 | FFN width skew, late-wide (512→1024) | 884,736 (exact) | 3,806,208 / 3,806,208 |
| 2 ★ | WH-002 | Decoupled A–F–A–F sublayers | 884,736 (exact) | 3,806,208 / 3,806,208 |
| 3 ★ | WH-003 | FP block last, ternary budget restored | 884,736 (exact) | 5,585,664 / 3,806,208 |
| 4 | WH-004 | Residual taper growing 160→224 | 885,248 (+0.06%) | 3,249,696 / 3,806,208 |
| 5 | WH-005 | Attention inner width 96 / 288 | 884,736 (exact) | 3,806,208 / 3,806,208 |
| 6 | WH-006 | FP block first (placement pair) | 884,736 (exact) | 5,585,664 / 3,806,208 |
| 7 | WH-007 | Residual taper shrinking 224→160 | 885,248 (+0.06%) | 4,364,320 / 3,806,208 |
| 8 | WH-008 | FFN width skew, early-wide (reverse control) | 884,736 (exact) | 3,806,208 / 3,806,208 |
| 9 | WH-009 | Components 1 vs 3 per block | 884,736 (exact) | 3,806,208 / 3,806,208 |
| 10 | WH-010 | Width-coupled V (16 / 48) on WH-001 shape | 884,736 (exact) | 3,806,208 / 3,806,208 |
| 11 | WH-011 | Heads 2 / 8 per block | 884,736 (exact) | 3,806,208 / 3,806,208 |
| 12 | WH-012 | Window taper 256 / 64 per block | 884,736 (exact) | 3,806,208 / 3,806,208 |

Controls: champion (layered_half + rotary, 2.8580 ± 0.0161) for all entries except
WH-010, whose control is WH-001 (same shape, uniform V=32) — stated in its entry.

## Lens 2 — Vocabulary (was TK-###)

### WH-013 ★ · Vocab 2048 at the champion — the down-dial nobody has run
- **source:** byte grounding above + DATA-AUDIT §2 — at 0.885M ternary weights the FP tied table is ~83% of served bytes and 548 of its rows are dead; F-051 varies vocab only upward and only at 50M. The small end of the dial, where the embedding dominates, has never been touched.
- **mechanism:** Refit the BPE tokenizer at vocab 2048 on the same corpus sources (B-002's refit procedure, different size), rebuild the corpus, run the unchanged champion chassis. Three effects compound: (a) the table halves to 1,572,864 B; (b) pieces get shorter, so at equal BYTES each run casts votes over more positions — vote evidence per byte of text rises; (c) every surviving id is roughly twice as frequent, so the tail-starvation documented in the audit halves with it. Judged at equal bytes (steps rescaled by the measured bytes/piece ratio) and reported in nats/byte.
- **exact change:** new `--vocab N` in train.py (threaded into `Tiny` and the corpus loader) + tokenizer build flag `--tokenizer refit --vocab 2048`; corpus rebuilt as `corpus-v2048.u16`; run `--arm layered_half --rope --vocab 2048` with `--steps` scaled to the equal-byte budget.
- **mode:** process — isolated train.py subprocess (new flag + rebuilt corpus); stays isolated until it has a full-trial record
- **prediction:** nats/token worsens (+0.05..+0.15, expected and irrelevant); **nats/byte −0.01..−0.04 vs the champion's 1.429** at equal bytes, driven by evidence density and table halving. Falsifier: if nats/byte is flat at 2048, the evidence-density story is wrong and WH-022's endpoint is not worth its probe.
- **status:** queued
```mill
id: WH-013
mode: process
run: --arm layered_half --rope --vocab 2048
```

### WH-014 ★ · Embedding rows join the vote trainer (tied, ternary, vote-trained)
- **source:** train.py code audit — the vote trainers vote on every `BitLinear` weight and nothing else; the tied table, 83% of served bytes, is the one large weight matrix still trained by full FP AdamW, the exact arrangement the vote trainer exists to replace.
- **mechanism:** The tied table gets the Layered treatment: each element carries two int8 counters (V=32, median strong gate, one component flip per step), installed as ternary × per-row scale, and the SAME installed table serves both roles (input lookup and head, transposed). Rows flip on accumulated sign evidence exactly like body weights. AdamW keeps only norms, `log_scale`s and the per-row scales. Exact differences from taken entries: MILL-118 quantizes the table to INT8 but keeps it AdamW-trained FP underneath — no counters, no flips, no trainer change; A-081 ternarizes an UNTIED head while the input embedding stays FP — here both roles share one vote-trained table and tying is the point (a flip must earn its keep in both roles at once).
- **exact change:** new trainer path `--emb-vote` on Layered: `model.tok.weight` is removed from the AdamW group, given `t1/t2/c1/c2` state (786,432 × 2 counters ≈ 1.57 MB of trainer state, charged honestly) and an `install()` analogous to BitLinear's, with per-row scales replacing the per-layer scalar.
- **mode:** process — isolated train.py subprocess (trainer code-path change)
- **prediction:** held +0.04..+0.12 nats/token (a real cost — the head is a classifier and ternary classifiers are coarse), against served bytes 3,806,208 → ~860,000 (table becomes 196,608 B packed + 16,384 B of per-row scales). Adoption bar, stated in advance: **a cost ≤ +0.05 buys a 4.4× served-byte cut and is a per-byte win; ≥ +0.12 kills it** and prices FP embeddings as genuinely load-bearing, which retires WH-016/WH-018/WH-019 with it.
- **status:** queued
```mill
id: WH-014
mode: process
run: --arm layered_half --rope --emb-vote
```

### WH-015 ★ · Post-training vocab excision and tail merge (readout-side compression)
- **source:** DATA-AUDIT §2 — 548 of 4,096 ids never occur anywhere in the token stream (train or held; held windows are windows of the same stream), and 1,984 ids occur <100 times. Their rows are 420,864 B (dead ids alone) of served weight that no input can ever address.
- **mechanism:** Readout-only, on a finished champion, in two separately reported steps. (a) **Excision:** delete the 548 never-occurring rows and renumber — zero loss by construction, verified by re-scoring held before/after (any delta at all means the audit's count was wrong, which is itself a finding). (b) **Tail merge:** for ids occurring <10 times, delete the row and retokenize — at build time those pieces are re-segmented into their BPE children, which exist by construction (every merge has parents in the table). The served model never sees the deleted ids because the tokenizer can no longer emit them. No retraining anywhere; the merge step's cost is measured on held in nats/byte (retokenization changes piece counts).
- **exact change:** no training change; new eval/build tooling `mill/vocab_prune.py --drop-dead --merge-below 10` producing a pruned checkpoint + pruned tokenizer; held scored with the standard `held_loss()` body on the retokenized held stream.
- **mode:** process — eval-side runner; stays isolated until it has a full-trial record
- **prediction:** step (a) −420,864 B served (−11.1%) at exactly 0.000 nats cost; step (b) a further −0.4..−0.7 MB at **nats/byte +0.000..+0.005** (the merged pieces carried almost no trained structure — their rows sat near the std-0.02 init). If (b) costs more than +0.01 nats/byte, tail rows were earning real bytes and the starvation picture in WH-019 needs revising downward.
- **status:** queued
```mill
id: WH-015
mode: process
run: --arm layered_half --rope --readout vocab-prune
```

### WH-016 · Frequency-split embedding: frequent rows FP, tail rows vote-ternary
- **source:** DATA-AUDIT §2 frequency split + the task's own question (should embedding rows be ternary *partially*?) — the corpus's frequency distribution is so skewed that a single precision for all 4,096 rows is the one choice nobody would pick from the data.
- **mechanism:** Split the tied table by corpus frequency at rank 1024: the top-1,024 rows (which carry the overwhelming majority of positions) stay FP/AdamW exactly as today; rows 1025–4096 are vote-trained ternary with per-row scales, WH-014's machinery restricted to the tail. The bet: tail rows receive so few input-side updates that they sit near init under AdamW anyway, so ternarizing them destroys almost nothing, while the rows that matter keep full precision. Exact difference from MILL-118: uniform INT8 over all rows, AdamW-trained — this is a *split by frequency* with two different trainers, not one quantizer. Difference from WH-014: WH-014 ternarizes the head-critical frequent rows too; this entry is the conservative half of that bet, and the pair brackets the cost curve.
- **exact change:** new flag `--emb-split 1024` on Layered: tail rows leave the AdamW group and gain counters/install as in WH-014; the split is computed from corpus counts at build time and logged.
- **mode:** process — isolated train.py subprocess (depends on WH-014's embedding-vote plumbing; defer until it lands)
- **prediction:** held +0.00..+0.03 nats/token vs champion, served bytes −~2.2 MB (tail becomes 147,456 B packed + 12,288 B scales, top stays 786,432 B). If the cost lands at the top of that range or above, frequency is not the right split variable and WH-014's uniform form is the honest comparison.
- **status:** queued
```mill
id: WH-016
mode: process
run: --arm layered_half --rope --emb-vote --emb-split 1024
```

### WH-017 · BPE-dropout segmentation: rare pieces testify through their children
- **source:** Provilkov et al., "BPE-dropout" (ACL 2020) and Kudo, "Subword Regularization" (ACL 2018), aimed at the audit's specific pathology: 1,984 ids with <100 occurrences whose rows and whose downstream vote evidence are starved *as units*, even though their sub-pieces are frequent.
- **mechanism:** During training only, each piece is stochastically decomposed: with probability p=0.1 per merge, a token is replaced by its BPE children (recursively), so the same text reaches the model at varied segmentations. Rare long pieces stop being atomic dead ends — their occurrences distribute evidence to their frequent children, and the body learns compositional structure the atomic table cannot express. Eval/held always uses the canonical segmentation, so the judge is unchanged. Exact difference from B-002/B-003: both change the *fixed* tokenizer (refit / superwords) and rebuild one canonical corpus; this keeps the canonical tokenizer and varies segmentation per presentation — the variable is evidence routing inside the vote trainer, not the merge table. Difference from A-052 (span-noise masking): that corrupts inputs with a mask embedding; this re-segments into real pieces.
- **exact change:** corpus pipeline change — training windows are drawn from the source texts and tokenized on the fly with `--bpe-dropout 0.1` (merge-dropout in the tokenizer encode step); held path untouched. Requires the text-side pipeline B-002's refit already implies; the pre-tokenized `corpus.u16` cannot express this arm.
- **mode:** process — isolated train.py subprocess (data-path change); full-trial only, probe horizons under-sample the segmentation variety
- **prediction:** **nats/byte −0.01..−0.04** at equal bytes, with the diagnostic that decides *why*: per-row input-update counts for tail ids' children rise measurably, and held loss on windows containing rare pieces improves more than the global mean. A global win with no rare-window concentration would mean it acted as generic regularization, not as the starvation fix claimed.
- **status:** queued
```mill
id: WH-017
mode: process
run: --arm layered_half --rope --bpe-dropout 0.1
```

### WH-018 · Dual-role counters: a tied row flips only when both its jobs agree
- **source:** train.py code audit — under tying, one row's gradient is the sum of two streams with wildly different characters: head-role evidence is dense (every row, every position, mostly small negative pushes `p_v·h`) and input-role evidence is sparse but large (only on occurrence). A single counter (WH-014's form) lets the dense stream outvote the sparse one ~256:1 per occurrence, so rows would flip to please the classifier role while their input representation is still unformed.
- **mechanism:** On the WH-014 chassis, each row-element carries TWO counters: `c_head` accumulates votes from the head-role gradient component, `c_in` from the input-role component (the two are separable — they arrive through different ops on the same weight). A flip fires when `|c_head + c_in| ≥ 32` AND `sign(c_in) == sign(c_head + c_in)` — the input role holds a veto, the head role cannot flip a row against the direction its occurrences are pulling. Costs one extra int8 per element over WH-014 (~0.79 MB trainer state, charged).
- **exact change:** new flag `--emb-dual` on top of `--emb-vote`: the trainer splits `tok.weight.grad` into its two role components by computing the head gradient from the logits path and taking the input component as the remainder; dual counters, veto flip rule, shared install.
- **mode:** process — isolated train.py subprocess (depends on WH-014's plumbing)
- **prediction:** −0.01..−0.04 nats/token vs WH-014 at identical served bytes — i.e. it recovers a quarter to a third of WH-014's predicted cost if role interference is real. Read against WH-014 directly, never against the champion: a flat result kills the interference story and leaves WH-014 as the simpler truth.
- **status:** queued
```mill
id: WH-018
mode: process
run: --arm layered_half --rope --emb-vote --emb-dual
```

### WH-019 · Tail-row threshold discount: V scaled to the evidence a row can actually receive
- **source:** DATA-AUDIT §2 + F-043's dilution logic applied per-row instead of per-model — F-043 argues a global V=32 starves weights as N grows; a rare token's row is the limiting case: at <8 expected occurrences per run, its elements cannot accumulate 32 net *input-role* votes in a run of any length the lab can afford. Under a uniform V, tail rows are not trained slowly — they are structurally frozen at init while still costing full FP bytes.
- **mechanism:** On the WH-014/WH-016 chassis, the flip threshold becomes per-row: `V_row = clamp(round(32 · sqrt(f_med / f_row)), 4, 32)` for rows below the median frequency `f_med`, 32 above it. A row expecting 1/64th of the median evidence gets V=4 — it can flip a handful of times per run on the evidence it actually receives, no more (the sqrt keeps the discount conservative: full proportional scaling would hand the rarest rows V<1, i.e. flip-on-first-vote). Exact difference from MILL-207/208 (per-LAYER flip-rate feedback) and F-043 (one global V chosen from N): this V is per-ROW, set from corpus frequency before the run, no feedback loop. Difference from A-049: that downweights frequent-token *windows* in sampling; this changes no sampling — it reprices the flip for the rows sampling cannot save.
- **exact change:** new flag `--emb-vfreq` on the embedding-vote trainer: per-row threshold tensor computed from the corpus count table at trainer construction; flip test uses `V_row` broadcast across the row.
- **mode:** process — isolated train.py subprocess (depends on WH-014 or WH-016 landing first)
- **prediction:** −0.005..−0.025 nats/token vs its undiscounted parent arm (WH-014 or WH-016), concentrated in held windows containing tail pieces — report the rare-window split, not just the mean. Failure signature to watch: tail-row flip counts exploding while held worsens = the discounted rows were better frozen, and V=32's "starvation" was actually protection.
- **status:** queued
```mill
id: WH-019
mode: process
run: --arm layered_half --rope --emb-vote --emb-vfreq
```

### WH-020 · Vocab 8192 at the champion and the 2M rung — the small end of the crossover
- **source:** F-051's own framing, completed at the end it skips — F-051 runs 16384 only at 50M and predicts the 10M point negative without running anything between 4,096 and 16,384 or below 10M. The crossover it promises as "the deliverable" cannot be located from one point.
- **mechanism:** Refit at vocab 8192, rebuild, run at BOTH the champion shape (dim 192 × 2) and the 2M rung (dim 288 × 2, ladder format, 56 steps), judged in nats/byte at equal bytes. Longer pieces mean fewer positions per byte (less vote evidence per byte — the anti-WH-013 direction) but each position carries more text and ctx 256 spans ~15–25% more real text. At dim 192 the table doubles to 6,291,456 B — this arm is expected to lose at the champion and is run to *measure* the loss slope, so the dial's curve has three points (2048 / 4096 / 8192) at lab scale instead of opinions.
- **exact change:** `--tokenizer refit --vocab 8192` + `--vocab 8192` runs at both shapes (2M form: `--dim 288 --layers-n 2 --steps 56 --tag scale2m`).
- **mode:** process — isolated train.py subprocess (new flag + rebuilt corpus, shared with WH-013)
- **prediction:** champion shape: **nats/byte +0.02..+0.06 (worse)**; 2M rung: +0.00..+0.04 — the penalty shrinking with dim is the prediction that matters, because its slope extrapolates to F-051's claimed 50M crossover. If the penalty *grows* with dim instead, F-051's premise (vocab gets cheaper as the body grows) is inverted at every scale this lab can reach and F-051 should be re-read before its 50M probe is spent.
- **status:** queued
```mill
id: WH-020
mode: process
run: --arm layered_half --rope --vocab 8192
```

### WH-021 · Untied FP head at the 2M rung (ladder format)
- **source:** MILL-119 (untied FP head) exists only at the champion shape, where untying doubles a 3,145,728 B table to win capacity the shape may not need; CANDIDATES-C's Family A established that several champion-shape readings do not transfer across rungs, and tying is exactly the kind of claim that flips with the table-to-body ratio (at dim 288 the table is 4,718,592 B against 1,990,656 ternary weights).
- **mechanism:** The 2M rung with `--untie-head`: input embedding stays FP/AdamW, the head becomes its own FP table (another 1,179,648 params). Ladder format (56 steps, equal tokens) removes the step-count confound that makes the champion-shape version hard to read. The question is rung-specific: does the head's classification geometry, freed from the input representation, earn more at dim 288 — where each row is wider and the two roles' geometry differs more — than the +4,718,592 B it costs?
- **exact change:** no new flag (MILL-119's `--untie-head`); run `--arm layered --rope --dim 288 --layers-n 2 --steps 56 --untie-head --tag scale2m`. Exact difference from MILL-119: shape (2M rung vs champion), format (ladder vs probe/trial), and verdict (per-byte at the rung vs per-byte at the champion) — a merge should keep both records, not collapse them.
- **mode:** sweep — config-only via the pooled flag once it lands; ladder format only, a 75 s probe is a smoke read and must not be verdicted as a rung result
- **prediction:** −0.01..−0.04 nats/token vs the rung's 3.2745 if untying earns more with width; judged per served byte it must clear the doubled table, so the adoption bar is the strict one: a nats/token win under −0.02 is still a per-byte loss and should be recorded as such.
- **status:** queued
```mill
id: WH-021
mode: sweep
run: --arm layered --rope --dim 288 --layers-n 2 --untie-head
```

### WH-022 · Vocab 1024 — the dial's endpoint
- **source:** WH-013's dose curve — CANDIDATES-C's discipline (a dial is not measured until its extremes are priced) applied to vocab: 2048 tests the direction, 1024 tests whether the direction *keeps paying* or turns over.
- **mechanism:** Refit at vocab 1024, rebuild, champion chassis, equal bytes, nats/byte. At 1024 the table holds 196,608 params (786,432 B FP32 — fewer parameters than the 884,736 ternary weights for the first time), pieces approach character n-grams, and ctx 256 covers the least text of any arm — the context-starvation cost that must eventually beat the evidence-density gain. Where the curve turns over IS the vocab law for this trainer: below the turn, positions are too poor in content; above it, rows are too starved to train.
- **exact change:** `--tokenizer refit --vocab 1024` + `--arm layered_half --rope --vocab 1024`, steps rescaled to the equal-byte budget as in WH-013.
- **mode:** process — isolated train.py subprocess (shares WH-013's plumbing)
- **prediction:** nats/byte +0.01..+0.05 vs WH-013's 2048 point (the turn is expected between 1024 and 2048) but still within ±0.03 of the 4096 champion's 1.429 — i.e. a wide plateau, which would make vocab a *byte-allocation* choice (pick by served bytes, loss barely cares) rather than a quality dial. A continued gain at 1024 instead re-opens the whole dial downward and is the highest-information surprise available in this file.
- **status:** queued
```mill
id: WH-022
mode: process
run: --arm layered_half --rope --vocab 1024
```

### WH-023 · Space-attachment pretokenization: kill the bare-space piece
- **source:** DATA-AUDIT §2 — the corpus's most common piece is a bare space (id 222, 10.2% of all pieces). One position in ten carries no content, casts votes on a whitespace prediction, and shortens every 256-piece window's real span by ~10%.
- **mechanism:** Change only the pretokenization rule: a space attaches to the FOLLOWING piece (the GPT-style `Ġword` convention this tokenizer evidently lacks), then refit merges at the same vocab 4096 and rebuild. Pieces per byte falls ~9–10%; every position in every window is content-bearing, so vote evidence per byte rises by the same fraction with no size, trainer, or budget change. Exact differences: B-002 refits with the SAME rules (the space piece survives its refit); B-003's SuperBPE drops whitespace pretokenization to merge ACROSS words into multi-word superwords — this keeps word boundaries intact and absorbs exactly one leading space, the minimal rule change that removes the waste piece.
- **exact change:** tokenizer build flag `--pretok space-attach` + refit at 4096; run `--arm layered_half --rope --pretok space-attach` at equal bytes vs champion.
- **mode:** process — isolated train.py subprocess (tokenizer build change + rebuilt corpus)
- **prediction:** **nats/byte −0.005..−0.02** — the smallest predicted win in this file, but also the cheapest mechanism per unit effect (one rule, no new parameters, no trainer state), and it stacks multiplicatively with WH-013/WH-022 (the dial arms should be re-read under whichever pretokenization wins). Falsifier: if pieces/byte does not fall by ≥7% at refit, the corpus's spaces are not where the audit's count implied and the entry dies at build time, before any probe.
- **status:** queued
```mill
id: WH-023
mode: process
run: --arm layered_half --rope --pretok space-attach
```

### WH-024 · Byte-metered windows: sample fixed bytes, not fixed pieces (the judging enabler)
- **source:** mill methodology, from this lens's own problem — every cross-vocab verdict above (WH-013/005/008/010/011) compares arms whose windows hold different amounts of text, because train.py samples windows of 256 PIECES (`offsets()` over the piece stream) and the held set is 128 piece-windows. "Equal bytes" is currently an accounting correction applied after the fact, not a property of the runs.
- **mechanism:** The sampler draws windows of a fixed BYTE budget (512 source bytes = the champion's 256 pieces × 2.00 B/piece at vocab 4096; the piece count per window then varies with the tokenizer), and held is rebuilt as fixed-byte windows scored as total nats over total bytes. Two claims: (a) methodological — cross-vocab comparisons become equal-text by construction, removing the rescaling assumption WH-013/WH-020/WH-022 otherwise carry; (b) as a training arm at 4096 itself — windows of uniform *text mass* rather than uniform piece count remove a subtle bias where dense, short-piece regions of the corpus (the audit's boilerplate and number streams tokenize short) are over-represented per window relative to their byte share.
- **exact change:** new sampler flag `--byte-windows 512` in train.py (offsets drawn over a byte-indexed stream; window = the pieces covering the next 512 bytes) + held-set builder emitting `held_bytes` alongside `held_loss` for every arm that runs under it.
- **mode:** process — isolated train.py subprocess (sampler code-path change); the 4096 control arm runs first and must reproduce 2.8580 ± 0.0161 within noise before any cross-vocab reading is trusted
- **prediction:** at 4096, held within ±0.01 of the champion (a flat control is the PASS condition — this entry sells validity, not loss). Its real prediction is about the other entries: at least one of WH-013/WH-020's rescaled verdicts will move by ≥0.01 nats/byte when re-judged under byte-metered windows, because piece-uniform sampling is not byte-uniform sampling on this corpus.
- **status:** queued
```mill
id: WH-024
mode: process
run: --arm layered_half --rope --byte-windows 512
```

---

## Ranking rationale (one line each)

1. **WH-013 ★** — the territory's central untested claim, at the scale where the table is 83% of served bytes; cheap (one refit + one run) and it sets the dial's direction for everything below it.
2. **WH-014 ★** — the largest byte prize in the file (4.4× served) and the only entry that asks whether the lab's founding mechanism should govern its largest matrix; its verdict also gates WH-016/006/007.
3. **WH-015 ★** — the only entry with a zero-risk component: 420,864 B back at exactly 0.000 nats by construction, on already-trained champions, today.
4. **WH-016** — WH-014's conservative half; the likeliest per-byte win among the training entries, ranked below it only because it depends on its plumbing.
5. **WH-017** — attacks starvation from the evidence side rather than the threshold side; the rare-window diagnostic makes it falsifiable in a way pure regularization entries are not.
6. **WH-018** — a genuinely new mechanism (role-veto counters) that only exists because the table is tied; high information whether it wins or reads flat against WH-014.
7. **WH-019** — the direct starvation fix, but it is a companion arm twice-dependent on WH-014/WH-016 landing, and its effect size is bounded by the tail's held share.
8. **WH-020** — expected-negative at the champion by design; its value is the slope toward F-051's crossover, and it is the only entry here that can falsify another file's premise.
9. **WH-021** — completes MILL-119 at the rung where tying is most expensive; cheap in ladder format, but the per-byte bar is strict and a nats/token win may still lose.
10. **WH-022** — prices the dial's endpoint; mostly curve-completion, with a small chance of the file's biggest surprise.
11. **WH-023** — smallest effect, near-zero cost, stacks with everything; ranked low on size, not on efficiency.
12. **WH-024** — sells verdict validity rather than loss; ranked last as an idea, but it should probably be BUILT first, since WH-013/008/010/011 all borrow its judging law.

*End of wave-3 lens 2. 12 entries (WH-013..WH-024), Muse's work, Muse's side. Nothing here edits IDEA-POOL.md or any CANDIDATES file; merge is the pool owner's call.*

## Lens 3 — Auxiliary signals (was AO-###)

### WH-025 ★ · Deep supervision: block-1 same-token auxiliary head (t+1, not t+2)
- **source:** auxiliary-signals lens — deep supervision (intermediate-layer CE) transplanted to a 2-block vote trainer; nearest neighbours MILL-123/124 and A-103 both attach supervision at the FINAL layer for a FUTURE token (t+2).
- **mechanism:** Block 1's output (after block 1, before block 2) is read by the tied head and scored against the SAME next token (t+1) the main head predicts, loss weight 0.1, computed on every 4th position only. Block 1's ternary weights currently receive CE only after it has been filtered through block 2, the final norm, and block 2's own still-moving structure — the longest, noisiest gradient path in a 2-block net. A direct, short-path CE gives block 1's counters evidence about its own output quality, in the same token space and for the same target as the main objective. This is not MTP: horizon is t+1 (identical target), placement is intermediate, and the question is gradient-path length, not supervision density over future tokens.
- **train.py:** new flag `--deep-sup 0.1` — in `Tiny.body` optionally return the block-1 activation; in the training loop compute `F.cross_entropy((h1 @ tok.weight.T)[::4 positions], targets[::4])` and add `0.1 *` it to the loss before `trainer.step(loss, done)`. No new parameters (tied head reused); head discarded at serving (block-1 readout is training-only). **Cost charged:** one extra vocab matmul on 1/4 of positions ≈ +6–9% step time, stated in the record; judged at equal minutes.
- **mode:** process
- **prediction:** −0.02..−0.05 at trial scale; −0.01..−0.03 at probe (acts from step 0, no bank or horizon needed). Side diagnostic: block-1 flip share should rise and its counter-reversal rate fall vs champion — if held improves with neither moving, the gain is extra-head compute, not path shortening, and the entry is re-read as such.
- **kill test:** retire if probe held Δ vs job zero is > +0.02 (worse), or trial mean ≥ 2.8480, or trial mean wins at equal steps but loses at equal minutes (the head's matmul ate the gain).
- **status:** queued
```mill
id: WH-025
mode: process
run: --arm layered_half --rope --deep-sup 0.1
```

### WH-026 ★ · Checkpoint self-distillation: the 50% snapshot teaches the second half (token space)
- **source:** auxiliary-signals lens — teacher-free self-distillation from the model's own earlier checkpoint, as named in the lens territory; nearest neighbours A-104 (EMA teacher, updated EVERY step, decay 0.99, w 0.5), MILL-113 (separately trained FP teacher), G-057 (ensemble teacher). This teacher is none of those: one frozen snapshot of THIS run, taken once.
- **mechanism:** At 50% of steps the runner snapshots the full model + trainer state (ternary states, scales, FP parts) and freezes it as the teacher. For the remaining 50% of steps, each batch is also forwarded through the frozen snapshot (no gradient) and the loss becomes CE + 0.3 · KL(teacher ‖ student) at temperature 2 on the same windows, same ground-truth stream. The snapshot is a worse model than the student will become, but it is a STABLE one: its distribution is the student's own past consensus, so the KL term specifically penalises late-run churn — flips that move predictions away from what the first half had already settled — while CE keeps pulling toward the tokens. No representation target, no EMA, no external teacher; the snapshot's own training cost is zero (it is a by-product of the run's first half).
- **train.py:** new flag `--ckpt-distill 0.3` — runner snapshots `model.state_dict()` + `trainer.t1/t2/log_scale` at `done >= 0.5` into a frozen copy of `Tiny`; second-half loop adds the teacher forward (under `torch.no_grad()`, `EASE=1.0`) and the KL term before `trainer.step`. **Cost charged:** one extra forward (no backward) per second-half step ≈ +15–18% total wall; snapshot storage ~7 MB training-only, 0 B at serving. Judged at equal minutes.
- **mode:** process
- **prediction:** −0.02..−0.05 at trial scale. Reasoning: the champion's late flip share stays ~0.11%/step to the end, so a measurable share of late steps is spent re-deciding settled structure; an anchor priced in token space should convert some of that churn into consolidation — the output-space analogue of D-003's counter-bank argument, priced independently. Probe is a plumbing/danger check only (the teacher does not exist until 50%, so a 75 s probe's second half is ~12 steps of distillation — a flat probe does NOT kill).
- **kill test:** retire if the trial mean ≥ 2.8480; or if second-half held (logged at the 50% boundary and at the end, diagnostic only) improves LESS in the distill arm than in its paired step-matched control in ≥2 of 3 seeds; or if the KL term collapses to ~0 by 75% of the run (teacher and student identical — the snapshot was taken too late to differ, and the entry's premise is measured false).
- **status:** queued
```mill
id: WH-026
mode: process
run: --arm layered_half --rope --ckpt-distill 0.3
```

### WH-027 ★ · Self-normalised surprise gate: per-weight gradient shaping before the vote
- **source:** auxiliary-signals lens — gradient shaping (per-layer gradient transforms before the vote); nearest neighbours the champion's per-layer median gate (selects by |g| relative to the LAYER), A-002 per-row gate (relative to the ROW), F-005 state gate (relative to the installed STATE), MILL-232 whitening (second-moment rotation of the whole field). None normalises a weight's gradient by that weight's OWN history.
- **mechanism:** Each weight carries an EMA of its own |g| (β=0.95, fp32, 4 B/weight charged). The vote-path gradient is shaped per weight as `g_shaped = g / (ema|g| + eps)` and the strong/weak gate is taken on |g_shaped| at its per-layer median: a weight now votes when its gradient is unusually large FOR IT, not when it is large for the layer. Chronically small-gradient weights — systematically disenfranchised by every pooled gate, because the layer median is set by other weights — get a fair evidence channel; chronically large weights must exceed their own baseline. Sign is untouched (sign(g_shaped) = sign(g)); only gate admission changes. AdamW parts and the `log_scale` gradient keep the UNshaped gradient, so the shaping is vote-path only and its effect is attributable.
- **train.py:** new flag `--surprise-gate` on `Layered` (and `Direct`): per-layer EMA buffers updated inside `step()` from `m.weight.grad` before the `strong =` line; `strong` computed on the shaped magnitudes. One EMA buffer per BitLinear, no extra forward or backward.
- **mode:** process
- **prediction:** −0.01..−0.04 at probe and trial scale (acts from the first steps, like F-005). Diagnostic that must accompany any win: the share of weights that cast ≥1 vote in the run should rise vs champion (the disenfranchised population is the claimed mechanism); a held win with no rise in voter coverage is not this mechanism and is reported as an unexplained win, not a confirmation.
- **kill test:** retire if probe held Δ vs job zero > +0.02, or trial mean ≥ 2.8480, or voter-coverage rise is <2 points while held is flat (the shaping changed nothing it claims to change).
- **status:** queued
```mill
id: WH-027
mode: process
run: --arm layered_half --rope --surprise-gate
```

### WH-028 · Born-again vote model: a fresh run distilled from the champion run's final checkpoint
- **source:** auxiliary-signals lens — sequential self-distillation (born-again networks) applied to the vote trainer; distinct from MILL-113 (teacher is an FP twin), G-057 (teacher is an ensemble), WH-026 (teacher is a mid-run snapshot inside the same run). Here the teacher is the student's own COMPLETED previous generation, same architecture, same ternary format.
- **mechanism:** Generation 1 is an ordinary champion run. Generation 2 starts from the SAME seed init and fresh counters, trains on the same corpus with loss CE + 0.5 · KL(gen-1 final ‖ gen-2) at temperature 2, teacher frozen throughout. A vote trainer's final model encodes its structure in a discrete code whose training trajectory cannot be replayed; the KL term lets generation 2's counters integrate the first generation's settled output geometry as evidence from step 0, instead of re-deriving it from one-hot tokens alone.
- **train.py:** new flag `--born-again 0.5` + `--teacher-state <path>` — runner loads the recorded champion final state into a frozen `Tiny` copy; training loop identical in shape to WH-026's KL term but active from step 0. **Cost charged at equal TOTAL compute, stated as the bar:** gen-1 (8 min) + gen-2 (8 min) must beat a 16-minute champion control, not the 8-minute 2.8580 — a win against 2.8580 alone is a compute artefact and is stamped as such.
- **mode:** process — full trial only (two full runs per seed; a probe cannot price a generational effect)
- **prediction:** Gen-2 held −0.01..−0.04 vs the equal-total-compute 16-min control; larger vs the 8-min champion (expected, and not the claim). If born-again transfer works for votes at all, this is its cleanest form: teacher and student share init, format, and corpus, so only the distillation channel varies.
- **kill test:** retire if gen-2 fails to beat the 16-min control by >0.01 on the 3-seed mean, or if gen-2 ≈ a CE-only 8-min student trained identically without the teacher (the in-entry ablation — the KL channel carried nothing).
- **status:** queued
```mill
id: WH-028
mode: process
run: --arm layered_half --rope --born-again 0.5
```

### WH-029 · Conflict-projected auxiliary gradients in the vote path (PCGrad for votes)
- **source:** auxiliary-signals lens — gradient shaping for multi-signal training (PCGrad, Yu et al. 2020), translated to the vote path; no pooled entry projects one signal's gradient against another's anywhere in the trainer.
- **mechanism:** Carrier signal is the pooled MTP head (MILL-123, w 0.1, t+2). Per BitLinear layer, the loop computes the CE gradient g_ce and the MTP gradient g_aux separately. If their per-layer dot product is negative, g_aux is projected orthogonal to g_ce (`g_aux -= (g_aux·g_ce/|g_ce|²) g_ce`) before the two are summed for the VOTE path; the AdamW parts receive the plain unprojected sum. The auxiliary signal may therefore add evidence in any direction except the one that directly fights the main objective that step, and the shaping is applied only where the lab's claim lives — the discrete structure. Whether MTP helps votes at all is MILL-123's question; whether a conflict-free MTP helps MORE is this one, and the entry is only interpretable alongside MILL-123's reading.
- **train.py:** new flags `--mtp 0.1 --pcgrad-vote` — training loop does two backwards on retained graph (or two half-forwards) to obtain per-layer g_ce / g_aux for the BitLinear weights, projects per layer, writes the summed projected gradient into `m.weight.grad` before `Layered.step`'s vote block; FP-part gradients restored from the unprojected sum (runner-level gradient surgery, no change to `step()`'s vote rule itself). **Cost charged:** ≈ +60–80% step time (second backward); judged at equal minutes AND equal steps, both reported.
- **mode:** process — full trial only (depends on MILL-123's flag landing and its single reading first)
- **prediction:** Conditional: if MILL-123 reads flat or slightly negative, projection recovers −0.01..−0.03 of that flatness (the harm was conflict, not the signal); if MILL-123 already wins cleanly, projection adds ~0 and this entry retires on its own condition. Per-layer conflict rate (fraction of layers with negative dot per step) is logged — if it is <5% of layer-steps, there was no conflict to shape and the entry is void, not failed.
- **kill test:** retire if the conflict rate is <5% (void), or if the projected arm fails to beat the unprojected MILL-123 arm by >0.01 at equal steps at trial, or loses to it at equal minutes by >0.02.
- **status:** queued
```mill
id: WH-029
mode: process
run: --arm layered_half --rope --mtp 0.1 --pcgrad-vote
```

### WH-030 · Flip-consistency KL anchor: predictions may not churn for free when structure flips
- **source:** auxiliary-signals lens — flip-consistency penalties, expressed in output space; distinct from A-105 (consistency between two DROPOUT passes of the same weights), WH-026 (anchor is a 50%-of-run snapshot, always on in phase 2), and every counter-side anti-thrash entry (A-008/F-016/A-019 act on counters and thresholds, never on predictions).
- **mechanism:** Whenever a step's flip share exceeds 0.2% (≈2× the champion mean 0.0011), the NEXT step carries an extra term: the batch is forwarded once under the pre-flip installed weights (snapshot taken before that flip step's `install()`) and the loss gains 0.2 · KL(pre-flip ‖ current) on the next step's windows. Ordinary low-flip steps carry no penalty and pay no extra forward. The penalty prices prediction churn at the moment it happens: a flip burst that genuinely improves fit can pay the small KL and move on (CE dominates at w 0.2); a burst that merely rearranges predictions pays and earns nothing, and its gradient — flowing into both the vote path and the FP parts on the following step — pushes the structure back toward predictive continuity.
- **train.py:** new flag `--flip-anchor 0.2` — runner keeps the previous step's installed weight tensors (the `m.weight` copies `install()` writes, ~3.5 MB); on a trigger step it computes the anchor forward under `no_grad` for the teacher side on the next batch and adds the KL term before `trainer.step`. **Cost charged:** one extra forward only on steps following a >0.2% flip step (logged trigger rate; expected <20% of steps, ≈ +5–7% total wall).
- **mode:** process
- **prediction:** −0.01..−0.03 at trial scale, concentrated in variance: seed sd should shrink vs 0.0161 even at a flat mean, because the penalised events are the high-churn steps where seeds diverge. A flat mean with halved sd still promotes (it sharpens every other probe in the mill, cf. G-003's stated logic).
- **kill test:** retire if the trigger rate is <2% of steps (void — flip bursts that large do not occur and there is nothing to anchor), or trial mean ≥ 2.8480 with no sd improvement, or the anchor KL stays >0.05 to the end of the run (the penalty is fighting CE permanently, not taxing bursts).
- **status:** queued
```mill
id: WH-030
mode: process
run: --arm layered_half --rope --flip-anchor 0.2
```

### WH-031 · Masked-token CE head: predict the actual masked tokens (ground-truth targets, no representations)
- **source:** auxiliary-signals lens — auxiliary prediction heads; the BERT/MLM signal re-expressed under this lab's hard boundary. Explicitly NOT JEPA: the target is the ground-truth token ID scored by ordinary cross-entropy through the tied head — no predictor MLP, no EMA target encoder, no representation matching, no stop-gradient target network. The JEPA record's failure was a representation target carrying no token information; this entry's target IS token information, by construction.
- **mechanism:** Each training window has 32 scattered positions (12.5%, never the first or last 8) replaced in the INPUT by the learned mask embedding (the one piece of plumbing `run_jepa.py` already proved on this chassis). The main next-token CE runs unchanged on all positions. An auxiliary CE, weight 0.1, scores the model's prediction OF the masked token AT each masked position (same tied head, position's own hidden state). The trunk must therefore carry token-identity information at positions where the input gave it nothing — in-context inference of a missing word — a signal the left-to-right objective never asks for directly, since next-token CE always sees the true previous tokens.
- **train.py:** new flags `--mask-aux 0.1 --mask-n 32` — `Tiny` gains a mask embedding vector (192 params); batch builder masks input ids at 32 seeded positions per window (targets and main CE untouched); loop adds `0.1 * CE(head(h[masked]), true_ids[masked])`. **Cost charged:** negligible compute (positions already forwarded); the input corruption itself is the risk being priced. Mask positions are drawn from the run's own RNG stream, held windows never masked or trained on.
- **mode:** process
- **prediction:** −0.01..−0.04 at trial scale; two-sided at probe (input corruption costs before the inference skill pays). Reasoning: at 0.885M weights the model is capacity-starved, and a second, differently-conditioned view of the same token stream is the cheapest supervision-density increase available that adds no parameters at serving (mask embedding is training-only scaffolding, discarded like the MTP head).
- **kill test:** retire if trial mean ≥ 2.8480, or if a dose control at `--mask-n 8` beats `--mask-n 32` by >0.02 (the corruption cost scales faster than the signal — the family is priced and closed at the low dose), or if train CE on UNmasked positions worsens ≥0.05 vs champion at matched steps (the auxiliary is eating the main objective, not serving it).
- **status:** queued
```mill
id: WH-031
mode: process
run: --arm layered_half --rope --mask-aux 0.1 --mask-n 32
```

### WH-032 · Past-token auxiliary head: predict t−1 from position t (shared head, w 0.05)
- **source:** auxiliary-signals lens — auxiliary prediction heads beyond the pooled MTP entries: every pooled/auxiliary head in the record predicts FORWARD (t+1 main, t+2 MTP/A-103). No head has ever asked the trunk to retain where it has been.
- **mechanism:** The final hidden state at position t is scored, through the same tied head, against token t−1 (the token two steps back from the main target at that position), loss weight 0.05, on every 4th position. A causal trunk can in principle discard a token once it has been consumed as context; the past-token loss pays it to keep a readable trace of the recent past in the residual stream — the same stream block 2 and the head read — which is also the substrate position-to-position information flows through in a 2-block model with no other memory. Targets are ground-truth tokens, CE-scored; the head and target direction are the only novelties.
- **train.py:** new flag `--past-aux 0.05` — training loop only: `CE((h @ tok.weight.T)[positions ::4], ids shifted +1 relative to the main target alignment)`, added to the loss before `trainer.step`. No new parameters. **Cost charged:** one extra vocab matmul on 1/4 of positions ≈ +6–9% step time, as WH-025.
- **mode:** process
- **prediction:** −0.005..−0.03 at trial scale — honestly the weakest prior among the head entries, included because the direction axis (past vs future supervision) is completely unmeasured in this lab and one probe prices it. A win would say the trunk under-retains context; a flat result closes the direction axis cheaply.
- **kill test:** retire if probe held Δ vs job zero > +0.02, or trial mean ≥ 2.8480, or the past-token auxiliary CE itself fails to fall below its init value by ≥20% over the run (the trunk cannot even express the signal — the head is decoration).
- **status:** queued
```mill
id: WH-032
mode: process
run: --arm layered_half --rope --past-aux 0.05
```

### WH-033 · Homeostatic histogram regularizer, expressed through the vote path
- **source:** auxiliary-signals lens — loss-side regularizers expressed through the vote path; nearest neighbours A-009 (FIXED 1.5× bonus on votes toward 0, open-loop, always on) and F-024 (homeostatic servo on per-row SCALES, never on votes or level histograms). This entry is a closed-loop controller on the installed histogram, acting only through vote admission.
- **mechanism:** The trained champion's installed histogram sits near ~42% zeros — the zero state is load-bearing (built-in feature selection), but nothing in the trainer defends that fraction: it drifts wherever the evidence pushes it. Every 20 steps the runner measures the global zero fraction z. While z is inside the band [0.38, 0.46], nothing changes. Outside it, a per-step vote bonus engages in the restoring direction only: if z > 0.46, strong votes that move a weight AWAY from 0 count 2 (one extra count); if z < 0.38, strong votes TOWARD 0 count 2. The bonus disengages the moment z re-enters the band. It is a regularizer whose loss is the histogram deviation and whose gradient is a vote — the only channel a vote trainer has for a discrete-state prior. Band edges are set from the champion's own recorded histogram, not tuned.
- **train.py:** new flag `--hist-homeo 0.38,0.46` on `Layered` — in `step()`, a per-run scalar `bonus_dir ∈ {-1, 0, +1}` refreshed every 20 steps from the installed states `t1+t2`; qualifying votes (sign matching the restoring direction relative to the weight's current installed value) add 2 instead of 1 to `c1/c2` before clamping. No new parameters, no extra forward/backward.
- **mode:** process
- **prediction:** −0.005..−0.025 at trial scale; ~0 at probe (the histogram barely moves in 25 steps — probe is a plumbing check, flat does not kill). The deliverable is partly the trace: if the bonus is engaged <5% of steps at trial, the histogram is already self-regulating and the regularizer axis closes with a measurement; if it is engaged >50%, the band is wrong, not the idea, and it is re-set once from the trace, not tuned silently.
- **kill test:** retire if trial mean ≥ 2.8480, or if the engaged-direction flip share shows the bonus manufacturing flips (bonus-assisted flips >30% of all flips while held is flat — the controller is doing the learning, badly), or if z exits the band and never returns in ≥2 of 3 seeds (the vote channel is too weak to express this regularizer at V=32).
- **status:** queued
```mill
id: WH-033
mode: process
run: --arm layered_half --rope --hist-homeo 0.38,0.46
```

### WH-034 · Two-snapshot checkpoint distillation: averaged 33% + 66% teachers (dose variant of WH-026)
- **source:** auxiliary-signals lens — the multi-teacher form of WH-026's mechanism; distinct from G-057/MC-009 (teachers are independent RUNS in an ensemble) — both teachers here are earlier checkpoints of the SAME trajectory, so their average is a time-average of one model's beliefs, not an ensemble of models.
- **mechanism:** Snapshots are frozen at 33% and 66% of steps. In the final third, the auxiliary term is 0.3 · KL(mean of the two snapshots' token distributions ‖ student) at temperature 2, added to unchanged CE. The 33% snapshot is structurally distant (many flips ago) and the 66% snapshot is close; their averaged distribution is a smoother, less idiosyncratic target than either alone — the discrete analogue of averaging checkpoints in output space, applied as a training signal rather than a readout (readout averaging is G-026/A-094's territory; this entry never averages weights).
- **train.py:** new flag `--ckpt-distill2 0.3` — as WH-026, with two frozen `Tiny` copies and a probability-mean of their logits before the KL. **Cost charged:** two extra no-gradient forwards per step in the final third only ≈ +20–25% of that phase's wall (≈ +7–9% total), plus ~14 MB training-only snapshot storage. Only run if WH-026's single-snapshot reading is at least flat-positive — this entry prices the averaging increment, not the base effect.
- **mode:** process — full trial only, sequenced after WH-026
- **prediction:** −0.005..−0.02 INCREMENTAL over WH-026's arm at trial scale (not over champion — the entry's claim is the increment). Reasoning: if WH-026's gain is churn reduction, a smoother target should reduce churn slightly better; if WH-026 is flat, this entry is not run and costs nothing.
- **kill test:** retire if it fails to beat WH-026's trial mean by >0.01, or if either snapshot's individual KL to the student collapses to ~0 before its phase ends (that snapshot stopped being a distinct teacher).
- **status:** queued
```mill
id: WH-034
mode: process
run: --arm layered_half --rope --ckpt-distill2 0.3
```

### WH-035 · Far-horizon MTP head: t+4 only, separate head, w 0.05 (horizon bracket)
- **source:** auxiliary-signals lens — auxiliary prediction heads beyond the pooled MTP entries: the pooled horizon is exactly t+2 at two weights (MILL-123/124) plus A-103's same-head t+2. The horizon axis itself — how far ahead an auxiliary target can sit before it stops serving t+1 — has never been varied.
- **mechanism:** One separate auxiliary head (a second tied-head readout with its own small pre-norm, training-only, discarded at serving) predicts token t+4 from position t, loss weight 0.05, with NO t+2 head present. Predicting four steps ahead cannot be solved by local collocation statistics the way t+2 partly can; it pays only for representations that carry topic, syntax state, and source style — the slow features. At w 0.05 its gradient is a minority signal by design: it shapes the trunk's evidence stream without competing with CE for the counters.
- **train.py:** new flag `--mtp4 0.05` — model builder adds the auxiliary head module (head params training-only, ~0.8 MB AdamW state charged, 0 B serving); loop adds `0.05 * CE(aux_head(h), targets shifted −4)` on positions with a valid t+4 target. **Cost charged:** one extra vocab matmul on all positions ≈ +25–30% step time — the most expensive head entry here, stated plainly; judged at equal minutes.
- **mode:** process
- **prediction:** −0.005..−0.03 at trial scale, two-sided: at 0.885M weights a t+4 target may simply be too hard to carry signal (its auxiliary CE may sit near the floor all run, in which case its gradient is near-noise and the entry should read flat-to-worse). With MILL-123/124 this completes the horizon curve {t+2 at 0.1/0.3, t+4 at 0.05} from which the useful horizon at this scale can be read off, whichever way it lands.
- **kill test:** retire if trial mean ≥ 2.8480, or if the t+4 auxiliary CE falls <5% from its init value over the full run (target unreachable at this scale — no signal was ever transmitted, and higher doses are not worth probing), or if it wins at equal steps but loses at equal minutes (the head matmul ate it, as priced).
- **status:** queued
```mill
id: WH-035
mode: process
run: --arm layered_half --rope --mtp4 0.05
```

### WH-036 · Coarse-class auxiliary head: predict the next token's class (16 classes, tiny head)
- **source:** auxiliary-signals lens — auxiliary prediction heads at the opposite granularity from WH-035: instead of a harder fine target, an easier coarse one. No pooled entry supervises any target coarser than the token itself.
- **mechanism:** A fixed, deterministic map sends each vocab token to one of 16 classes (digit-led, capital-led, lower-case, punctuation-led, whitespace-led, German-specific characters, other scripts, etc., derived from the tokenizer's piece strings at build time). A tiny head (192→16, ~3k parameters) on the final hidden state predicts the class of the NEXT token, loss weight 0.05. Ternary QK/FFN logits are coarse, and full-vocab CE spends most of its gradient mass separating near-identical pieces; the class loss gives every position a low-variance, almost-always-learnable signal about the syntactic SHAPE of what comes next — signal whose gradient direction is stable across batches, which is exactly the property a sign-integrating vote counter can accumulate, in a way it cannot accumulate the high-variance fine-grained gradient.
- **train.py:** new flag `--class-aux 0.05` — build-time class table `piece_class[4096]` stored as a buffer; model gains the 192→16 head (training-only, discarded at serving); loop adds `0.05 * CE(class_head(h), piece_class[targets])`. **Cost charged:** negligible (16-way matmul); head state ~25 KB training-only.
- **mode:** process
- **prediction:** −0.005..−0.02 at probe and trial scale — the smallest expected effect in this file, and the cheapest: its value is partly diagnostic, since class accuracy per position is a readable proxy for whether the trunk tracks syntax state at all, logged alongside held either way. If a stable low-variance signal is what votes are starved of (the premise WH-027 tests from the gate side), this is the loss-side version of the same bet, and the pair read together.
- **kill test:** retire if probe held Δ vs job zero > +0.02, or trial mean ≥ 2.8480, or class-head accuracy fails to exceed its majority-class baseline by ≥10 points (the trunk carries no class information and the gradient was noise).
- **status:** queued
```mill
id: WH-036
mode: process
run: --arm layered_half --rope --class-aux 0.05
```

---

## Miner's ranking note

Top 3 (★): **WH-025** deep supervision — the densest new CE signal per unit compute in the
file, acting on the longest gradient path in the net, from step 0, with no teacher and no
extra parameters. **WH-026** checkpoint self-distillation — the only teacher that costs no
training run of its own, aimed at the champion's measured late-run churn, with a token-space
target that stays strictly inside the JEPA boundary. **WH-027** surprise gate — zero extra
passes, vote-path only, and it repairs a disenfranchisement that every pooled gate shares
by construction; its voter-coverage diagnostic makes even a flat reading informative.

The best single idea in this file is **WH-025**: in a 2-block model, half the ternary
structure (block 1) has only ever been trained through the other half's moving, coarse
output. Giving block 1 its own direct next-token loss — the same target, the same head, a
shorter path — is the auxiliary signal most tightly coupled to the objective it serves,
the cheapest to implement honestly (subsampled positions, tied head, no new parameters),
and the one whose mechanism (flip share and reversal rate in block 1 specifically) can be
verified in the run's own logs rather than inferred from the held number alone.

*End of wave3-lens3. 12 entries (WH-025..WH-036), all queued, all `process` mode, all on
the champion chassis unless an entry says otherwise. Coverage of the lens territory:
gradient shaping — WH-027, WH-029; auxiliary heads beyond pooled MTP — WH-025, WH-031,
WH-032, WH-035, WH-036; loss-side regularizers through the vote path — WH-030, WH-033;
teacher-free self-distillation from own earlier checkpoints — WH-026, WH-028, WH-034;
flip-consistency penalties — WH-030. JEPA objective: not re-proposed in any form;
F-031 (JEPA-as-initializer): not duplicated.*

## Lens 4 — Robustness (was RB-###)

### WH-037 ★ · Serving fault injection: ternary flips are cheap, one FP-scale flip may not be
- **source:** territory brief (bit-flips in counters at serving) + train.py structure: the served model is 884,736 ternary weights *plus* a small set of FP parts — per-layer `log_scale`, norms, and the tied FP embedding/head — trained by AdamW. Every robustness intuition in the lab is about the ternary majority; nobody has priced the FP minority, which has no majority to hide in.
- **mechanism:** Take the trained champion state (3 seeds), copy it, and inject faults into the copy at eval only, in four separate families: (a) random ternary level flips at f = 0.01%, 0.1%, 1%, 5% of weights; (b) random int8 counter bit-flips applied to the counters *before* a final readout/install (simulating a corrupted resume-from-checkpoint); (c) single bit-flips in FP parts — one exponent-bit flip in one layer's `log_scale`, one in the embedding, one in a norm gain (n=1 per family, swept over layers); (d) whole-`log_scale` sign flip per layer. Held loss measured clean after each injection.
- **exact change:** new eval-side script flag `--fault-inject {ternary|counter|scale|embed} --rate f --seed s` operating on a checkpoint copy; no training code touched. Hardening variant, run only if (c)/(d) breaks: per-layer scale stored redundantly (median of 3 copies) + scale clamped to the training-observed range at load — one extra flag `--scale-guard`.
- **mode:** process — eval-side code path, isolated.
- **prediction (quantified):** ternary flips degrade gracefully — f=0.1% (~885 weights) Δheld < +0.01, f=1% Δ +0.03..+0.10, f=5% Δ > +0.30. Counter bit-flips are worse per event than ternary flips (an MSB flip in an int8 counter moves it by 64–128, i.e. ≥2 thresholds of phantom evidence) but still bounded: 0.1% of counters Δ < +0.05. **The FP families are the cliff: a single exponent-bit flip in one `log_scale` is predicted to cost Δ ≥ +0.5, plausibly total loss of that layer's contribution (held > 3.5); a `log_scale` sign flip makes the layer's install scale negative — predicted held > 4.0 from ONE flipped bit.**
- **what the number teaches either way:** if the ternary curve is as flat as predicted, the 1.58-bit serving story is genuinely fault-tolerant and that becomes a citable property at 50M. If the FP cliff is real, the lab's hardening priority is inverted: protect ~a few hundred FP scalars (redundancy + clamp, ~zero cost) before spending anything on ternary redundancy. If even the FP flips are absorbed (norms rescaling downstream), the whole stack is more redundant than its structure suggests and serving on unreliable hardware is de-risked in one experiment.
- **status:** queued

### WH-038 ★ · Label (target-token) noise dose–response: find p where votes stop learning
- **source:** territory brief (label noise) + the vote mechanism itself: a vote is the *sign* of a gated gradient, accumulated to ±32 before anything moves. Sign-aggregation is a majority filter — random wrong targets should cast near-random votes that cancel, while true targets vote coherently. STE has no such filter: every wrong label moves its latents at full lr.
- **mechanism:** With probability p per position, replace the training target token with a uniform-random vocab token (input untouched). Doses p = 0.01, 0.05, 0.10, 0.20, 0.30, 0.40 on the champion chassis; one matched ste_half arm at p = 0.10, 0.20 as the cross-trainer control. Theory: coherent signal scales as (1−2p), so evidence-per-flip inflates by 1/(1−2p) — at p=0.20 flips need ~1.67× the steps; at p=0.50 signal is exactly zero.
- **exact change:** new flag `--label-noise p` in the loss path (target replacement after window sampling, seeded separately so batch streams stay paired across doses). Hardening variant at the breaking dose: `--label-noise p --vlayer`-style flip-rate servo is NOT used; the hardening tested is simply raising V 32→48 at that dose (more votes = stronger majority filter) — flag `--votes 48`.
- **mode:** process — isolated subprocess per dose.
- **prediction (quantified):** champion holds Δ < +0.032 (inside the break bar) through p=0.10; Δ +0.05..+0.12 at p=0.20; **breaking point p* ≈ 0.30 ± 0.05**, where Δ crosses +0.20 and flip share collapses below ~0.0004/step (votes drowning, not votes erring). ste_half at p=0.20 is predicted to degrade ≥2× the vote arm's Δ at the same dose. The V=48 hardening at p* is predicted to recover roughly half the Δ at ~⅔ the flip share.
- **what the number teaches either way:** p* is the single most portable robustness number the lab can own — it converts directly into a data-cleaning budget (below p*, cleaning buys nothing; above it, nothing else matters). If votes break *earlier* than STE, the majority-filter story is wrong at this scale — the median gate, not the counter, was doing the work — and every downstream vote-trainer claim gets re-read. If V=48 rescues p*, threshold becomes a *noise-adaptive* knob, set from a measured corpus-noise estimate rather than by habit.
- **status:** queued

### WH-039 ★ · Mid-run distribution shift: how many steps does a 32-vote memory take to turn around?
- **source:** territory brief (distribution shift mid-run) + DATA-AUDIT.md §7: v1 and v2 are two real, already-built distributions differing maximally (v1: 79% junk, median line 9 pieces; v2: clean, median 36) — a ready-made shift pair no synthetic construction has to invent. A counter at ±32 is up to 32 steps of committed evidence *against* the new distribution; the trainer's inertia is exactly measurable.
- **mechanism:** Train on v1 for the first 50% of steps, then switch the sampler to v2 (clean) for the second 50% — and the reverse direction (v2→v1) as the second arm. Log held loss (clean held set, fixed throughout) every 10 steps post-shift to trace the recovery curve: steps-to-return-to-pre-shift-slope, and final held vs both no-shift controls. Hardening variants at the shift point: (a) counters zeroed (weights kept), (b) counters halved, (c) counters kept (control = the base arm).
- **exact change:** new flags `--shift-at 0.5 --shift-corpus corpus-v2/corpus-v2.u16` in the sampler; `--shift-counters {keep|zero|half}` in Layered at the shift step.
- **mode:** process — isolated; shift is a code-path change.
- **prediction (quantified):** v1→v2: a post-shift held *worsening* of +0.05..+0.15 lasting ~30–60 steps (the counter-turnaround window: at flip share 0.0011/step, re-flipping even 5% of weights takes ~45 steps), then recovery to beat the pure-v1 control by ≥0.05 by run end — but NOT catch the pure-v2 control (E-018's re-baseline, when run) within one budget. Counter-zeroing is predicted to shorten the worsening window by ~40% at a cost of +0.02 final held (forgotten still-valid evidence); halving dominates: ~25% shorter window, no final cost. v2→v1 degrades monotonically post-shift with no recovery — direction asymmetry is part of the prediction.
- **what the number teaches either way:** the recovery-step count *is* the trainer's effective memory horizon, measured instead of inferred from V — the number that decides whether curriculum changes, corpus upgrades (the v2 adoption question), or mixture re-weighting mid-run are cheap or ruinous at 50M, where a run is too long to restart on a data fix. If zeroing counters wins outright, "counters are a liability at a regime change" becomes a standing rule for every future corpus swap; if keeping them wins, the inertia is a feature (shift-robustness for free) and v2 adoption mid-series stops being feared.
- **status:** queued

### WH-040 · Input-token corruption dose–response (uniform random replacement, inputs only)
- **source:** territory brief (corrupted data injection). Distinct from A-052: that masks ONE contiguous 8-token span with a mask embedding at one fixed dose; this corrupts a *measured fraction of all positions* with *real random tokens* — the model sees plausible-but-wrong context everywhere, not an obvious hole somewhere.
- **mechanism:** With probability q per input position, replace the input token with a uniform-random token; targets stay true (the model must predict the real continuation from damaged context). Doses q = 0.01, 0.05, 0.10, 0.25. This is the deployment-realistic corruption: tokeniser damage, transmission errors, upstream pipeline bugs corrupt inputs, not labels.
- **exact change:** new flag `--input-noise q` in the sampler's window transform (seeded, paired across doses).
- **mode:** process — isolated per dose.
- **prediction (quantified):** flatter curve than WH-038 at equal rate — attention can route around scattered wrong tokens, and no wrong evidence is written into counters as *targets*: Δ < +0.032 through q=0.10, Δ +0.04..+0.09 at q=0.25, no sharp breaking point below q=0.40. Secondary prediction: input noise at q=0.05 *helps* clean held by −0.01..−0.03 (regularisation — the corrupted-context model cannot lean on surface collocations, which on a boilerplate-heavy corpus are exactly the overfittable part).
- **what the number teaches either way:** the WH-038/WH-040 asymmetry (labels break it, inputs don't — or the reverse) locates the trainer's fragility in the *evidence path* vs the *representation path*, which dictates where hardening money goes: label filtering vs input denoising. If q=0.05 genuinely improves clean held, the lab gains a free regulariser discovered by trying to break the model — and a suspicion that part of v1's junk was acting as exactly this all along.
- **status:** queued

### WH-041 · Byzantine batches: what fraction of sign-reversed batches can votes absorb?
- **source:** territory brief (adversarial / gradient noise) + F-018 (Byzantine quorum, a mechanism looking for its justification). Before building quorum machinery, price the threat: a bad data shard, a corrupted worker, or a poisoned slice of corpus does not add random noise — it votes *coherently backwards*.
- **mechanism:** A fraction b of batches have their gradients sign-reversed before voting (worst-case coherent adversary, strictly stronger than random corruption at the same rate). Doses b = 0.05, 0.10, 0.20, 0.30, both scattered (random batches) and concentrated (one contiguous block, same total). Median-gate note: reversed batches still pass the gate — their |g| is unchanged — so the gate offers no protection here by construction.
- **exact change:** new flag `--byzantine b --byzantine-mode {scatter|block}` in the trainer step (sign flip applied to g before the vote increment, on the affected batches only).
- **mode:** process — isolated per dose/mode.
- **prediction (quantified):** scattered: signal scales as (1−2b) as in WH-038 but with full-magnitude coherent votes, so the curve is steeper — Δ < +0.032 through b=0.10, **breaking point b* ≈ 0.20 ± 0.05** (Δ > +0.20, flip share toward the *wrong* states measurable in the state histogram). Block mode at b=0.20 is predicted *less* damaging than scatter (the block's damage is partially un-done by the clean 80% re-voting afterwards; net Δ roughly half of scatter's). 
- **what the number teaches either way:** b* is the lab's data-provenance requirement, stated as a number: if b* ≈ 0.20, a corpus that is <20% coherently hostile is safe and F-018's quorum is insurance against a threat already priced as remote; if b* ≤ 0.05, quorum/trimmed-vote hardening jumps the queue ahead of every quality lever, because one bad source file in a v3 build could exceed it. Block-vs-scatter tells whether *auditing for contiguous bad regions* (cheap, file-level) is sufficient, or per-batch defence (expensive) is required.
- **status:** queued

### WH-042 · Single-window duplication poison: how many repeats hijack a weight population?
- **source:** territory brief (duplicated data injection) + DATA-AUDIT.md §4: v1 already spends 30.8% of pieces on duplicates — but spread over ~165k duplicated lines. The untested case is *concentration*: one window, repeated deliberately, the classic memorisation/poison probe.
- **mechanism:** Pick one fixed 256-piece training window (mid-loss, ordinary prose). Inject extra copies so it occupies r = 0.1%, 1%, 5% of all training steps (on top of its natural occurrence). Measure (a) clean held loss, (b) the model's loss on the poison window itself (memorisation depth), (c) flip share attributable during poison steps. Distinct from B-009 (uniform epoch repetition of everything) and WH-048 (bulk fraction of *random* windows).
- **exact change:** new flag `--poison-window <offset> --poison-rate r` in the sampler (deterministic interleave, e.g. every ⌈1/r⌉-th batch has one slot replaced).
- **mode:** process — isolated per dose.
- **prediction (quantified):** at r=0.1% (~5 extra presentations at probe scale, ~160 at full format) poison-window loss falls ≥1.0 nat while clean held moves < +0.01 — memorisation is *local*, the trainer absorbs it. At r=1%: poison loss < 0.5, clean held Δ +0.01..+0.04. **At r=5%: clean held Δ > +0.10** — the repeated window's votes start flipping weights the general distribution needs, i.e. the breaking point for a single source is between 1% and 5% of steps.
- **what the number teaches either way:** this prices the worst case hiding inside v1's duplication statistic: no single v1 source plausibly exceeds ~1–2% of steps except the numeric dumps and merge tables (~23% and ~10%+ of pieces respectively — *above* the predicted breaking band, which would mean the champion was trained *past* a poison threshold by two sources and still won; that reframes the audit's "junk" as active opposition the trainer overcame). Either way the v3 corpus builder gets a hard per-source cap derived from measurement, not taste.
- **status:** queued

### WH-043 · Gradient-noise tolerance: how much noise can a sign vote survive that STE cannot?
- **source:** territory brief (gradient noise) + the core claim of the vote design: votes keep only sign + a median gate, discarding magnitude — so additive gradient noise should be nearly free until it flips signs, whereas STE integrates the noisy magnitude directly into latents.
- **mechanism:** Two noise forms, doses each: (a) Gaussian noise added to g before signing, σ = 0.25×, 0.5×, 1.0×, 2.0× the per-layer mean|g|; (b) per-weight sign-flip probability s = 0.05, 0.10, 0.20, 0.30 applied to the vote increment only. Matched ste_half arm under form (a) at σ = 0.5×, 1.0×. Note form (b) at s is *equivalent* to label noise only in expectation — it bypasses the gate and the loss, isolating the counter's own noise floor.
- **exact change:** new flags `--grad-noise sigma_mult` and `--vote-signflip s` in Layered.step (noise applied after backward, before the gate for (a); after the gate for (b)).
- **mode:** process — isolated per dose/form.
- **prediction (quantified):** form (a): Δ < +0.032 through σ=0.5× (the median gate discards the noisy weak half by construction), Δ +0.05..+0.10 at σ=1.0×, break (Δ>+0.20) near σ≈1.5–2.0×. ste_half at σ=1.0× predicted Δ ≥ +0.15 — votes win the comparison at high noise, lose nothing at low. Form (b): near-linear degradation, Δ ≈ +0.3·s, breaking at s≈0.30 consistent with WH-038's p* (a cross-check: two independent injections should agree on the counter's effective noise ceiling ≈30%).
- **what the number teaches either way:** if the σ-curve is flat to 1.0×, the vote trainer is *the* trainer for noisy-gradient regimes — cheap hardware, aggressive kernel approximations, low-precision backward passes all become permissible, which feeds directly back into the kernels work (an approximate matmul that perturbs g by <0.5× mean|g| is *free*). If form (b) breaks far below s=0.30 while WH-038 doesn't, the gate — not the counter — is the noise defence, and kernel noise that enters *after* the gate (i.e. in the counter update itself) is the dangerous kind. Either result draws the exact line an approximate kernel must stay under.
- **status:** queued

### WH-044 · Junk-burst timing on clean v2: does WHEN the junk lands matter?
- **source:** territory brief (corrupted data injection, distribution shift) + F-032 (junk-first curriculum — order claimed to matter, on v1) + E-020 (numeric ablation). This entry inverts both: start from *clean* v2, inject v1-style junk (numeric-dump + merge-table windows) as one contiguous burst occupying 20% of the run, placed early (steps 0–20%), mid (40–60%), or late (80–100%), plus a scattered-20% control at the same total dose.
- **mechanism:** Same corruption, same dose, four placements. The vote counter's memory (≤32 net votes, reset on flip) predicts placement matters asymmetrically: early junk is voted *away* by the clean 80% that follows; late junk lands on a converged counter population with the fewest remaining steps to repair it; mid junk is partially repaired.
- **exact change:** new flags `--junk-burst 0.20 --junk-at {0.0|0.4|0.8|scatter} --junk-corpus corpus.u16` in the sampler (burst steps draw from v1's numeric/merge regions only, identified by the audit's line offsets).
- **mode:** process — isolated per placement.
- **prediction (quantified):** early burst: final Δ vs pure-v2 control < +0.02 (fully repaired — and possibly −0.01, if F-032's junk-as-regulariser suspicion is real). Mid: Δ +0.02..+0.05. **Late: Δ +0.08..+0.15 — the worst placement, 4–7× the early cost at identical dose.** Scatter sits between mid and late. 
- **what the number teaches either way:** a placement curve converts "data quality" from a static property into a *schedule* property: it tells the v3 builder whether junk must be excluded (if even early bursts cost) or merely *front-loaded and diluted* (if early is free) — the difference between a filtering project and an ordering flag. It also directly tests F-032's premise from the clean side: if late junk costs 5× early junk on v2, then v1's champion number was earned *despite* its junk being uniformly scattered — the worst-but-one arrangement — and a junk-first v1 re-run should beat 2.8580, a falsifiable follow-on.
- **status:** queued

### WH-045 · Stuck-at counters during training: frozen evidence, live weights
- **source:** territory brief (bit-flips/faults in counters) + a fault class WH-037 does not cover: not flipped bits at serving, but counters that *stop updating* during training — the realistic failure of a corrupted checkpoint resume, a buggy fused kernel (cf. C-C04), or a partially-written state file at 50M where state is ~125 MB and a torn write is plausible.
- **mechanism:** At step 25%, freeze a fraction f of counters (both components, chosen at random) at their current values — they never vote again; their weights can therefore never flip again. f = 1%, 5%, 10%, 25%. Second form at f=10%: counters frozen *at ±32 specifically* (stuck at threshold — these weights flip once immediately, then freeze), the nastier stuck-at value.
- **exact change:** new flag `--counter-freeze f --freeze-at 0.25 --freeze-value {current|sat}` in Layered (a boolean mask applied in step; mask excluded from state-bytes accounting, noted in the run line).
- **mode:** process — isolated per dose/form.
- **prediction (quantified):** graceful to f=10%: Δ +0.01..+0.03 (at 25% of the run, most weights that will flip have begun to; freezing 10% of counters strands ≈10% of the *remaining* flip capacity, and flip share is already only 0.0011/step). f=25%: Δ +0.05..+0.10. Stuck-at-±32 at f=10% is the exception: predicted Δ +0.08..+0.15, worse than f=25% frozen-at-current — one forced wrong flip per stuck weight, applied instantly.
- **what the number teaches either way:** the f-curve is the checkpoint-integrity requirement for long runs: if f=10% is nearly free, torn writes and silent counter corruption at 50M are a nuisance, not a catastrophe, and checksumming state is optional; if stuck-at-sat is as bad as predicted, the *value* counters are stuck at matters more than the count — and a cheap load-time guard (reject/resample counters at exactly ±32 beyond the expected saturated fraction) becomes a standing rule. It also measures, as a by-product, how much of the run's remaining gain after 25% is carried by how small a minority of weights — a plasticity census the lab has never taken.
- **status:** queued

### WH-046 · Adversarial windows: max-loss replay as an attack, not a curriculum
- **source:** territory brief (adversarial windows) + A-056 / F-family failweight entries, which train *more* on hard windows as a *remedy* at mild doses. This entry pushes the same lever to attack doses and adversarial *selection*: windows chosen to maximise damage, not representativeness.
- **mechanism:** Mine the 32 training windows with highest loss under the *initial* model (fixed adversary — chosen before training, no adaptation). Replay them at rate a = 1%, 5%, 10% of steps replacing ordinary batches. A second, adaptive form re-mines every 25% of the run against the *current* model (the adversary tracks the defence). Ordinary hard-window replay at these rates is the point where "hard example mining" and "poisoning" become the same operation viewed from different intentions — the curve locates the boundary.
- **exact change:** new flag `--adv-replay a --adv-mode {fixed|adaptive}` in the sampler (mining pass at init / at quarter points, cost charged to the run's wall time and ledgered).
- **mode:** process — isolated per dose/mode.
- **prediction (quantified):** fixed adversary: a=1% Δ −0.01..+0.02 (indistinguishable from failweight's mild benefit); a=5% Δ +0.03..+0.07; **a=10% Δ > +0.12 — replay of 32 fixed windows at 10% is a poison, not a curriculum.** Adaptive adversary is worse at every dose by ~1.5× (it keeps finding the current model's wounds): break (Δ>+0.20) predicted at a≈10%.
- **what the number teaches either way:** the crossover dose where hard-window emphasis flips from remedy to attack is a safety bound on *every* hard-example idea already in the pool (failweight, D-family dream replay, A-054 regression-weighted sampling all inherit it — none of them states a ceiling). If no crossover appears even at 10% adaptive, the vote trainer is unusually replay-proof (plausible: a replayed window's votes saturate its counters, then the flip resets them — the mechanism has a built-in per-window rate limit), and that becomes a named structural property worth testing at 50M before any dream/replay system is trusted there.
- **status:** queued

### WH-047 · Counter bit-flips during training: single-event upsets in the evidence itself
- **source:** territory brief (bit-flips in counters) — the training-time twin of WH-037(b). At 50M weights the counter store is the largest single state object; on commodity hardware, silent bit errors are a rate, not a hypothetical. Nobody knows the rate the trainer tolerates because nobody has injected one.
- **mechanism:** Each step, each counter independently suffers a random single-bit flip with probability u per counter-step, u = 1e-6, 1e-5, 1e-4, 1e-3. Effect size is position-dependent by construction: a bit-0 flip moves a counter by 1 (one vote — nothing); a bit-6/7 flip moves it by 64/128 — across the ±32 threshold instantly, forcing a flip next step and a reset. So the *effective* spurious-flip rate is ≈ u × P(high bit) × N, directly computable and directly observable in flip-share telemetry.
- **exact change:** new flag `--counter-seu u` in Layered.step (XOR with a sparse random bit mask after the clamp; mask generation seeded and vectorised — cost noted, this flag is a probe tool, not a serving feature).
- **mode:** process — isolated per dose.
- **prediction (quantified):** u=1e-6 and 1e-5: Δ < +0.01 (at half width, 1e-5 × 1.77M counter-steps ≈ 18 upsets/step, of which ~¼ are high-bit — a handful of spurious flips/step against a natural ~973 — absorbed). u=1e-4: flip share measurably inflated (+10–25%) but Δ still < +0.032 — the clean majority out-votes the damage. **u=1e-3: break — spurious flips rival natural flips (~50%+ inflation), Δ > +0.10, state histogram visibly smeared toward uniform.** Breaking point u* ≈ 3e-4 ± half a decade.
- **what the number teaches either way:** u* converts into a hardware requirement in one line: at 50M counters × ~10⁴ steps, u* ≈ 3e-4/step tolerates ~10⁸ total upsets per run — orders of magnitude above any realistic silent-error rate, which would *close* the ECC question for the counter store permanently. If instead u* lands at 1e-5, the opposite follows: counters need protection (parity per row is 1 bit per 8 — cheap, but only worth building on this evidence), and the high-bit asymmetry argues for a specific redesign — sign-magnitude or Gray-coded counters, where no single bit is worth 64 votes. Either way a design decision currently made by default gets made by measurement.
- **status:** queued

### WH-048 · Bulk duplication dose on clean v2: price the accident that built v1
- **source:** territory brief (duplicated data injection at measured rates) + DATA-AUDIT.md §4/§5: v1's 30.8% duplicate-piece share was an *accident* whose cost has never been isolated — E-019 prices the held-set *leakage* flattery, but the training-side cost of duplication itself (effective epochs on the duplicated fraction, wasted steps on zero-new-evidence windows) is unmeasured. WH-042 covers one targeted window; this covers the global dose.
- **mechanism:** On clean v2 (zero duplicates by construction), duplicate a random fraction d of windows exactly once each (each chosen window appears twice per epoch-equivalent), d = 10%, 30%, 50% — d=30% deliberately reproduces v1's measured duplicate share, on clean text, with the held set untouched and unleaked. Sampler otherwise unchanged.
- **exact change:** new flag `--dup-dose d` in the v2 sampler (duplicated set chosen once, seeded, ledgered as a window-id list hash).
- **mode:** process — isolated per dose, v2 chassis (champion configuration, v2 corpus).
- **prediction (quantified):** mild and monotone: d=10% Δ +0.00..+0.02, d=30% Δ +0.02..+0.05, d=50% Δ +0.04..+0.08 — duplication wastes steps rather than poisoning them (a duplicate's second presentation votes with evidence the counters already spent; after the flip-and-reset, the same window re-earns its flips slowly). No sharp break predicted below d=50%.
- **what the number teaches either way:** at d=30% this isolates the exact price of v1's best-documented flaw: combined with E-018 (v2 re-baseline) and E-019 (leakage price), it completes the decomposition of "how much of the v1↔v2 gap is leakage, how much is duplication, how much is junk content" — three numbers the lab currently lumps into one shrug. If the dose curve is instead *negative* (duplication helps — mild repetition as implicit curriculum on a 0.91M-piece corpus that is starved, not saturated), then v2's aggressive dedup threw away the one free lunch a tiny corpus had, and the v3 builder should duplicate *deliberately* at the measured optimum rather than dedup by reflex.
- **status:** queued

---

## Ranking rationale (one line each)

WH-037 first because its predicted failure is *catastrophic and singular* (one bit,
one layer) while everything else degrades in doses. WH-038 second because p* is the
most portable number here — it sets the data-cleaning budget for every future corpus.
WH-039 third because the shift-recovery horizon decides the v2-adoption and
corpus-swap questions the lab already owes answers to. WH-040–WH-048 follow by
(blindness of the lab today) × (cost if the bad case is true at 50M): coherent
attack (WH-041) before random noise (WH-043), targeted poison (WH-042) before bulk
dose (WH-048), timing (WH-044) and replay (WH-046) as the two order-effects, and the
two counter-fault entries (WH-045, WH-047) last only because their predicted
tolerances are the widest — if either prediction is wrong, it promotes itself.

## Lens 5 — Counter forensics (was IC-###)

### WH-049 ★ · Counter-histogram forecast: predict final held loss from the field at 25% and 50%
- **source:** counter-forensics derivation — the mill currently learns a probe's fate only by finishing it (75 s) and a trial's only by running all 3 seeds (24 min). The counter field at mid-run is an integral of every gradient sign the run has seen; if its *shape* encodes how much unresolved disagreement remains, it encodes how much loss is left to win.
- **mechanism:** Offline first, kill rule second. From `--dump-at` dumps of ≥20 completed runs (champion re-runs + ledgered arms, all with known final held), extract per-dump features: histogram entropy, mean |c|, kurtosis, mass in |c| ∈ [24, 32] (near-flip band), mass at exactly 0, per-layer mean |c| spread (max/min across the 8 BitLinear layers). Fit a ridge regression from the 25% and 50% feature vectors to final held. Only if out-of-sample (leave-one-arm-out) R² clears the bar does it become a runner hook: a probe/trial whose 50% forecast CI lies entirely above the adoption threshold is stopped and ledgered `forecast_dead` with its forecast attached.
- **exact change:** new analysis script `mill/counter_forecast.py` (reads dumps + runs.jsonl, writes the fit + per-run forecast table to `mill/COUNTER-FORECAST.md`); runner hook in `mill/screen.py` gated on the script's reported R², exactly as G-065's kill is gated on its measured precision.
- **mode:** process — analysis script + gated runner hook; no train.py change beyond the shared `--dump-state` plumbing.
- **prediction:** the 50% feature vector forecasts final held with leave-one-arm-out R² ≥ 0.7 and mean absolute error ≤ 0.03 — tight enough to kill the worst third of trials at half price (≈4 min saved per killed trial seed, ≈12 min per killed trial). The single strongest feature will be near-flip-band mass at 50%: a run still carrying >12% of counters in [24, 32] at halfway is a run whose structure is still churning, and churn at halfway has never ended well in this lab. At 25% the forecast will be weaker (R² ≈ 0.4–0.55) — reported honestly, used only for queue ordering, never for killing. **Distinction from G-065:** that kills at step 10 on flip share + train slope (motion signals, catastrophe band only); this forecasts a *continuous* final-loss value at 25–50% from distribution shape and is aimed at the near/promote band G-065 explicitly does not touch.
- **cost:** zero training cost — dumps ride on runs the mill already pays for; the fit is seconds of CPU. The hook, once active, only saves time.
- **status:** queued

### WH-050 ★ · Counter-field divergence as a verdict signal: rank arms by their distance from the champion's field, before any held eval
- **source:** counter-forensics derivation — every probe verdict today costs a held eval, and held is the lab's scarcest epistemic resource (the same 128 windows judge everything; RIGOR-AUDIT §1b counts each verdict as a selection event on them). Two runs on the same seed see the *identical* batch stream, so their counter fields are paired observations: an arm that changes nothing real should produce a near-champion field, and an arm that helps should move the field in the direction the champion's own later field moves.
- **mechanism:** For a probe arm and its paired job-zero run (same seed, same stream), compute at matched steps: (a) per-layer Jensen–Shannon divergence between the arm's and champion's counter histograms, and (b) **field velocity alignment** — cosine similarity between the arm's counter displacement (dump at 50% → dump at 100%) and the champion's displacement over the same interval, per weight, aggregated. Test, across ≥20 ledgered arms with known held Δ, whether (a)+(b) rank arms the way held Δ does. If they do, the mill gains a held-free pre-verdict: arms whose field is both far from champion *and* misaligned with champion velocity are demoted in the queue without spending a held read; held still renders every actual verdict.
- **exact change:** new analysis script `mill/counter_divergence.py` (paired-dump comparison, Spearman ρ of the divergence ranking vs held-Δ ranking printed per generation into `mill/COUNTER-FORECAST.md` alongside WH-049's table — the two share one report because they share one question: does the field know the verdict early?).
- **mode:** process — analysis script only; a queue-ordering hook in screen.py is proposed *inside* the entry but activates only on the measured ρ, as in G-042's backtest gate.
- **prediction:** Spearman ρ ≥ 0.75 between the combined divergence/alignment score and held Δ across arms — the counter field is downstream of every gradient the arm produced, so a mechanism that truly changes learning must move it, and one that moves it *against* the champion's own trajectory is spending votes unlearning. The falsifiable edge: readout-only and continuous-parts arms (G-001 family) move the field least per unit of held gain, so the score will *underrate* them — the report must print the ranking split by family, and the hook, if any, applies only within trainer/sampler families. A ρ < 0.4 result is equally valuable: it proves the field is mechanism-noise, not verdict signal, and retires WH-049's premise with it.
- **cost:** zero training cost; pairwise dump comparison is ~1 s per arm pair.
- **status:** queued

### WH-051 ★ · Frustration census: the saturated, boundary-blocked counter population as the good/bad run separator
- **source:** train.py code audit — in `Layered.step`, a counter at ±32 flips its component only if the flip moves the state; when t is already at the boundary the vote pushes against, the flip is a no-op and the counter **stays pinned at ±32**, absorbing further agreeing votes invisibly (clamp). This population — call it *frustrated* — is the only counter subpopulation whose size is exactly computable from a dump (sign(c) pointing outward from a boundary state) and it has never been counted. F-001 *reroutes* this pressure into log_scale; nobody has first *measured* whether the pressure distinguishes good runs from bad ones.
- **mechanism:** From end-of-run dumps (and 50% dumps where available), compute per layer and globally: frustrated fraction = #{weights with a component at boundary, its counter saturated with outward sign} / 442,368. Correlate with final held across all dumped runs, and track its trajectory shape (rising / flat / falling over the run's second half) as a run-quality signature.
- **exact change:** new analysis script `mill/counter_anatomy.py` (shared by WH-051/004/009/010/012 — one pass over a dump emits the full anatomy table); frustration census is its first report section.
- **mode:** process — analysis script only; no trainer, readout, or runner change.
- **prediction:** frustrated fraction at end of run separates the lab's known arms cleanly: champion-family runs land at 4–8%, catastrophe-class runs (anneal-class dynamics, if re-dumped) above 15%, and across ordinary arms frustrated fraction correlates with held at ρ ≥ 0.6 — a weight begging to leave the ternary alphabet is a weight the alphabet is failing, and a run full of them is a run whose capacity is mis-shaped, not undertrained. The sharper, decision-changing version: frustrated fraction at **50%** predicts the *sign* of the second half's held improvement (runs whose frustration is still rising at halfway gain < 0.01 in their second half in ≥80% of cases) — if true, the mill can stop paying second halves for first halves that have already announced themselves. Per-layer readout included: frustration is predicted to concentrate in `down` projections (fan-in 768, the coarsest sums) by ≥2× over `qkv`.
- **cost:** zero training cost; one dump pass per run.
- **status:** queued

### WH-052 · Per-weight counter validity: does a counter at step k actually predict its weight's final state?
- **source:** counter-forensics derivation — every counter-based idea in every wave (readout, merge, inherit, forecast) rests on one unmeasured assumption: that a counter's value carries information about where its weight *should* end up, rather than being a random walk with resets. That assumption is directly testable per weight, per layer, from dumps alone.
- **mechanism:** Across ≥10 runs with 25/50/75/100% dumps: for each weight, score how well sign(c) and |c| at step k predict (a) whether the weight flips again before end of run, and (b) its final state relative to its state at k. Report AUC per layer, per component, per k. Also report the **counter half-life**: the lag at which a counter's sign stops predicting the next flip's direction better than chance.
- **exact change:** analysis only, in `mill/counter_anatomy.py` (validity section); output is a layer × horizon AUC table.
- **mode:** process — analysis script only.
- **prediction:** AUC at 50% for "flips again before end" lands at 0.72–0.82 for `down`/`up` layers but only 0.55–0.65 for `qkv` (attention weights receive the noisiest, most context-dependent gradients) — i.e. the counter is a strong witness in the FFN and a weak one in attention, a fact that would re-price every counter entry in the pool per layer: G-026-style resolution restricted to high-AUC layers should beat its whole-field form, and WH-049's features should be FFN-weighted. Counter half-life is predicted at ~60–90 steps (roughly half a trial run) — evidence older than that is archaeology. If AUC ≈ 0.5 everywhere, the honest headline is that counters are near-memoryless at flip horizons and the entire counter research line should be re-based on short horizons only.
- **cost:** zero training cost.
- **status:** queued

### WH-053 · Counter fingerprint I — duplicate/contaminated run detection from field correlation
- **source:** mill-integrity derivation — the mill's ledger trusts that each ledgered run is the run its line claims: distinct seed, clean data, no accidental re-run of an earlier config under a new id, no held windows in the training stream. Today nothing could detect a violation after the fact. Two runs sharing an init seed start from identical states; their per-weight counters then integrate their respective batch streams — so the **per-weight counter correlation between two same-init runs is a direct meter of how much training stream they shared**, computable from two dumps and nothing else.
- **mechanism:** Calibration first: run same-init pairs at known stream overlaps (0%, 25%, 50%, 100% shared windows, constructed by the runner from legal offsets) and measure per-weight counter Pearson ρ per overlap. Then the forensic use: any two ledgered runs claiming different data/seeds whose dump-pair ρ sits in the calibrated "shared stream" band are flagged in a `mill/COUNTER-AUDIT.md` report — this catches duplicated runs, seed-reuse accidents, and, pointed at a deliberately contaminated calibration arm (5% held windows mixed into training), tests whether training-on-held leaves a counter signature distinguishable from clean training at the same init.
- **exact change:** new script `mill/counter_fingerprint.py` + four short calibration runs (probe budget, same init, runner flag `--stream-overlap F` in the *runner's* sampler, not train.py's trainer); audit mode runs over existing dumps pairwise.
- **mode:** process — analysis script + 4 probe-budget calibration runs.
- **prediction:** per-weight counter ρ tracks stream overlap near-linearly: ≈0.05 at 0% overlap (shared init only), ≈0.45–0.55 at 50%, ≥0.9 at 100% (identical runs are bit-identical, ρ = 1 by construction — the calibration's real content is the middle). The contamination arm is the gamble: a 5% held admixture is predicted to be detectable not by field ρ (too diffuse) but by a **held-window counter shadow** — weights whose counters move anomalously on held-content gradients — honestly predicted weak (AUC 0.6–0.7); even a null there is a quotable bound on what post-hoc forensics can certify. The duplicate-detection half needs no luck: it is arithmetic.
- **cost:** 4 × 75 s calibration probes; audit passes over dumps are seconds.
- **status:** queued

### WH-054 · Counter-settled checkpoint selection: pick the checkpoint whose field has stopped arguing, with zero eval passes
- **source:** gap inside G-031 — it selects among the last 9 checkpoints by calibration-window loss (10 eval passes, and one more selection pressure on legal-but-finite calibration data). A checkpoint's *own* counters offer a selection signal that costs no forward passes at all: total pending evidence P = Σ|c| over the field is the run's own measure of how much of its current state its evidence still disputes.
- **mechanism:** From the last-9 `--dump-state` saves of completed runs, compute P (and its near-flip component, mass in |c| ≥ 24) per checkpoint. Offline: compare the checkpoint each statistic selects against (a) the final checkpoint and (b) G-031's calibration-selected checkpoint, on held, across ≥8 runs. If settledness selection captures most of loss selection's gain, it becomes the default first pass — loss selection runs only when settledness is ambiguous (two checkpoints within 2% P).
- **exact change:** analysis in `mill/counter_anatomy.py` (settledness section, reads the same multi-save dumps G-031 already requires); no new dumps, no new eval passes in the analysis phase.
- **mode:** process — analysis script only in this entry; adoption as a readout is a follow-up the numbers would justify, not this entry.
- **prediction:** P falls monotonically over the last 9 checkpoints in <60% of runs — vote training keeps arguing late — and the P-minimum checkpoint beats the final checkpoint by −0.005..−0.02 on held while landing within 0.01 of the calibration-selected checkpoint in ≥6 of 8 runs. The decision-changing case is the disagreement runs: where P-minimum and loss-minimum pick *different* checkpoints, the P pick is predicted to generalise at least as well, because it never touched any eval windows to make its choice. If P is monotone in ≥90% of runs, settledness selection is vacuous (it always picks the last save) and the entry retires itself in one table.
- **cost:** zero — rides G-031's dumps; pure arithmetic per checkpoint.
- **status:** queued

### WH-055 · Counter entropy clock: histogram entropy as a convergence measure that prices run length
- **source:** counter-forensics derivation — the lab sets run length by wall clock and steps, two currencies the half-control proved treacherous (layered's "win" was its step count). The counter field offers a mechanism-native clock: at init all counters are 0 (entropy 0); evidence polarises the field (entropy rises as mass spreads over 65 bins, then falls as flips reset counters and surviving evidence concentrates). Where a run sits on that curve is a statement about its training, not about the machine it ran on.
- **mechanism:** From fractional dumps across arms and rungs (including scale-ladder dumps), plot field entropy and mean |c| against *held improvement remaining* (final held minus held-at-dump, from paired eval reads on the same dumps). Test whether "entropy within 5% of its run-final value" is a transferable stopping state across arms and sizes — a state-based budget rule ("train until the field settles to X") instead of a time-based one.
- **exact change:** analysis in `mill/counter_anatomy.py` (entropy section); requires held reads at dump points, which the readout runner already performs for G-031's saves — shared, not new, eval cost.
- **mode:** process — analysis script only.
- **prediction:** entropy at 50% of a run already sits within 8% of its final value for champion-family runs, while held still improves by 0.03–0.06 in the second half — i.e. **the field settles before the loss does**, because the AdamW parts keep fitting a structure the counters have stopped disputing. If that ordering holds across arms, entropy is a *leading* indicator and the ladder can price rungs by "steps to field-settling" (predicted: settling steps grow sublinearly with size, ~N^0.5, so larger rungs are relatively *less* undertrained at equal steps than the lab assumes). The negative result is also priced: if entropy and held plateau together within noise, the field carries no timing information beyond the loss curve and WH-049 loses its cheapest feature family.
- **cost:** zero training cost; dump-point held reads shared with G-031.
- **status:** queued

### WH-056 · Cross-arm field taxonomy: which layers' counter fields are data-driven and which are mechanism-driven
- **source:** counter-forensics derivation — when an arm wins or loses, the lab learns *that*, never *where in the network the mechanism acted*. Counter dumps give a per-layer witness: compare each arm's end-of-run field against the champion's per layer (same seed/stream pairing as WH-050) and cluster the 8 layers by how much each arm family moves them.
- **mechanism:** Build the arm × layer divergence matrix (Jensen–Shannon per layer, from WH-050's machinery) over ≥15 ledgered arms spanning families (vote-rule, sampler, architecture, continuous-parts). Read the matrix two ways: layers whose fields barely move under *any* arm are data-determined (their evidence is overwhelming and mechanism-proof); layers whose fields move under one family only localise that family's action.
- **exact change:** analysis output of `mill/counter_divergence.py` (taxonomy section — same computation as WH-050, aggregated across arms instead of ranked per arm).
- **mode:** process — analysis script only.
- **prediction:** block-1 `qkv`/`out` fields will prove the most data-determined (JS < 0.05 under every family — early attention evidence is dominated by local syntax every mechanism agrees on), while block-2 `down` is the most mechanism-sensitive layer in the model (JS > 0.25 under vote-rule arms) — meaning vote-rule innovation is effectively acting on one layer and the other seven are passengers. The actionable consequence, stated as the prediction's second half: at least two pooled vote-rule variants whose *global* held Δ was flat will show a clean block-2-`down`-only field signature — localised action with no global payoff — marking them as layer-targeted-retest candidates rather than dead ideas. If instead divergence is uniform across layers for all families, mechanisms act globally and per-layer targeting is a dead axis — also worth one table to know.
- **cost:** zero training cost; reuses WH-050's pairwise computations.
- **status:** queued

### WH-057 · Dead-counter census: the silent-weight population and what it says about wasted capacity
- **source:** train.py code audit — a counter only moves when its weight's gradient passes the median gate with a consistent sign; nothing in any record counts how many of the 884,736 counters end a run having barely moved (|c_final| ≤ 4 *and* never flipped — the second clause needs the flip history, available from multi-point dumps as state-change counting). MILL-215 logs flip counts *during* training as a freezing diagnostic; the end-state census of never-engaged weights, per layer, has never been taken. F-045 proposes *evicting* near-zero counters for storage; this entry measures whether the silent population is large and structured enough for that question — or a pruning question — to be worth asking at all.
- **mechanism:** From dumps + state-change reconstruction: per layer, dead fraction (never flipped, |c| never ≥ 8 at any dump), dormant fraction (flipped exactly once, early, then silent), and their overlap with the final zero-state population. Cross-arm comparison: does dead fraction predict held (capacity wasted) or anti-predict it (sparsity earned)?
- **exact change:** analysis in `mill/counter_anatomy.py` (census section).
- **mode:** process — analysis script only.
- **prediction:** dead fraction is large and layer-structured: 25–40% of block-1 counters never engage, vs 8–15% in block 2 — early layers converge to their (mostly local-syntax) structure fast and then sit out the run. Across arms, dead fraction will *anti*-correlate with held at ρ ≈ −0.4..−0.6 within the champion family (a run that engages more of its field uses more of its capacity) but the relation inverts for catastrophe arms (frantic engagement = thrash) — the census's real deliverable is that two-regime picture, which no single correlation states. Either way the number disciplines F-045: eviction is worth building only if the truly-dead share (not merely near-zero at one instant) exceeds ~20%.
- **cost:** zero training cost.
- **status:** queued

### WH-058 · Sub-flip oscillation anatomy: the argument underneath the flips
- **source:** counter-forensics derivation — flip counts (MILL-215's diagnostic, A-008's thrash tax) see only arguments that *ended*: a weight whose counter swings +28 → −28 → +28 without ever reaching 32 is in violent disagreement with itself and is invisible to every flip-based statistic the lab owns. Only multi-point counter dumps can see it.
- **mechanism:** From dumps at 25/50/75/100%: per weight, count counter sign changes and total counter path length Σ|Δc| between dumps; define the **hidden-thrash population** as weights with ≥2 sign changes and path length ≥ 64 but zero flips. Report its size per layer, and test whether hidden-thrash share at 50% predicts a run's second-half held gain better than its flip share does (the head-to-head against the throughput lens's scalar, run on forensics turf: same runs, same outcome, two predictors).
- **exact change:** analysis in `mill/counter_anatomy.py` (oscillation section).
- **mode:** process — analysis script only.
- **prediction:** the hidden-thrash population is 3–6% of weights, concentrated in block-2 `qkv`, and its 50% share predicts second-half gain with ρ ≈ −0.6, beating flip share's ρ on the same runs by ≥0.2 — because flip share measures *resolved* churn (often healthy late training) while hidden thrash measures *unresolvable* churn (two data regimes voting one weight in opposite directions, the signature G-016's mixture-order entry predicts block-grain rotation would create — this census is that entry's cheapest possible pilot: if hidden thrash does not spike under conflicting evidence, mixture order has no counter-level mechanism to act through). A hidden-thrash share under 1% everywhere retires the concept and strengthens flip share's claim to be the whole motion story.
- **cost:** zero training cost; needs the 4-point dumps of the shared plumbing.
- **status:** queued

### WH-059 · Counter-kurtosis early warning: field shape spikes before loss spikes
- **source:** failure-forensics derivation — the lab discovers a diverging or destabilised run at its end (held read) or not at all. A destabilising run should deform its counter field *before* the deformation reaches held loss: a few weights receiving extreme one-sided evidence (kurtosis spike in the |c| distribution, mass suddenly piling into the near-flip band in one layer) is the field-level shape of a gradient pathology, and counters integrate it within a few steps.
- **mechanism:** Retrospective study on dumps from the lab's known bad runs (anneal-class and any ledgered divergence, re-dumped at 10% intervals for this entry — the one place this file asks for short re-runs) plus champion controls: compute per-dump excess kurtosis of |c| and single-layer near-flip-band mass; measure lead time between the first dump where either statistic exits the champion family's band and the first dump where paired held-at-dump exits its band.
- **exact change:** 3–4 probe-budget re-runs of known-bad configs with `--dump-at 0.1,0.2,…,1.0` + analysis section in `mill/counter_anatomy.py`; if lead time is real, a runner hook (warn-only, never kill — killing stays WH-049/G-065's gated business) is the stated follow-up, not part of this entry.
- **mode:** process — analysis script + ≤4 short re-runs.
- **prediction:** kurtosis exits the champion band 15–25% of a run *before* held does in the anneal-class failure (its hot start fires flips on weak evidence, which must show as a field-wide |c| pile-up within the first fifth), giving a genuine early-warning window; for slow failures (cooldown-class starvation, a continuous-parts pathology) the counter field is predicted to show **nothing** — the counters are healthy while the FP parts starve — and that blind spot, measured rather than assumed, is half the deliverable: it fences exactly which failure classes counter forensics can ever police.
- **cost:** ≤4 × 75 s re-runs; rest is dump arithmetic.
- **status:** queued

### WH-060 · c1/c2 disagreement anatomy: the layered chassis's internal contested population
- **source:** train.py code audit — `Layered` feeds both components the *same* vote; `c1` and `c2` diverge only because flips reset them at different times and t1 has flip priority. Their per-weight sign disagreement is therefore a quantity no other chassis produces: a direct census of weights where the two components' recent evidence points in opposite directions — weights the summed code (levels −2..+2) is internally undecided about. The half-control proved the second component earns nothing *on average*; this anatomy asks whether it earns something on an identifiable subpopulation and is pure noise elsewhere.
- **mechanism:** From champion dumps: per layer, contested fraction = #{sign(c1) ≠ sign(c2), both |c| ≥ 8} / 442,368, tracked over the run; and the retrospective test — do contested weights at 75% account for a disproportionate share of the flips and held-relevant state changes in the final quarter (measurable from the 100% dump's state diff)? Compare against plain_half dumps, where the analogous quantity (single counter near zero with high path length, from WH-058) defines its contested set, so the two chassis' indecision can be priced in the same units.
- **exact change:** analysis in `mill/counter_anatomy.py` (disagreement section; the plain-chassis comparison reuses WH-058's outputs).
- **mode:** process — analysis script only.
- **prediction:** contested fraction settles at 10–16% of weights and is *not* uniform: it concentrates where |t1 + t2| ∈ {0, 2} (the levels the forward rounding treats most coarsely) and in block 2. Contested weights at 75% will account for ≥35% of final-quarter flips from ~13% of the population — the second component's real job, if it has one, is arbitrating exactly this set. The decision this prices: a future layered variant that spends its second component *only* on the contested population (and runs plain elsewhere, at plain's state bytes) is worth pooling iff the contested set carries ≥2× its share of late flips; below that, the layered idea has no anatomical refuge left and the half-control's verdict stands unqualified.
- **cost:** zero training cost.
- **status:** queued

---

## Miner's ranking note

Ranked by (decision changed) × (probability the signal is real) ÷ (cost — which is
near zero throughout, so ranking is almost purely about consequence):

1. **WH-049 ★** — a working 50% forecast converts every trial from a fixed 24 min
   purchase into a sequential decision; it is the only entry here that pays for
   itself in the mill's own currency from its first generation.
2. **WH-050 ★** — if field divergence ranks arms, held stops being spent on
   pre-verdicts and survives longer as a judge; if it doesn't, WH-049's premise
   dies cheaply alongside it. The pair stand or fall together, by design.
3. **WH-051 ★** — the frustration census is the cheapest statistic in the file
   (one dump, one pass, exact definition) with the sharpest predicted separation,
   and its 50% form doubles as a second-half kill signal independent of WH-049's
   regression.
4. WH-052 — the validity bedrock: every counter idea in every wave silently
   assumes what this measures.
5. WH-053 — the integrity instrument; duplicate detection is arithmetic, the
   contamination bound is a bonus.
6. WH-054 through WH-060 — anatomy that re-prices existing pool entries
   (G-031, F-045, MILL-215, G-016, the layered chassis itself) rather than
   proposing new mechanisms; each is one section of two shared scripts, so the
   marginal cost of the whole tail is a few hours of analysis over dumps the
   shared plumbing produces anyway.

**The most decision-changing counter signal, if I must name one:** the
**frustrated fraction at 50%** (WH-051) — the share of weights whose counters are
pinned at ±32 begging for a flip the ternary alphabet forbids. It is exactly
computable, needs no fitted model and no eval pass, and if its predicted
signature holds (rising frustration at halfway ⇒ a second half that gains
< 0.01), it simultaneously (a) kills doomed second halves across the whole mill,
(b) turns "is the ternary alphabet the binding constraint?" from a philosophy
question into a per-layer number, and (c) gives the scale ladder its first
mechanism-native capacity gauge — larger rungs should show *falling* frustration
if width is what the frustrated weights were asking for.

*End of wave-3 lens 5 (counter forensics). 12 entries, WH-049..WH-060, all queued,
none duplicating IDEA-POOL.md or CANDIDATES-A/B/C/D/E/F/G or FABLE-CANDIDATES.md.
Shared assumption, stated once in the header: `--dump-state` with fractional
`--dump-at` points persisting `c1/c2` alongside `t1/t2`.*

## Lens 6 — Cross-pollination (was XP-###)

### WH-061 ★ · Learned say for the layered components (per-layer t1/t2 standings, re-fit on fresh windows)
- **source:** Fable's side (growing hive) — the learned say, `body.learn_say` /
  `body._say`, commits `bea40f6` / `06b536a` / `7a11fcc`, FABLE-STUDY §2.5: first
  full unattended turn, bodies as one scored **2.4807** under the learned say —
  the first time the ensemble beat its best member (2.5715) — while the same
  population under the old winner-take-all rule scored **2.5754** as one, i.e.
  combining hurt. The say is re-made at every measurement and deliberately never
  kept in git. Muse's side's factory has the same idea only as a *serving*
  composition fit (learned say, currently SHADOW after its sealed regression,
  factory H-001/E-001); it has never been applied inside a trainer.
- **mechanism:** `Layered.install()` currently sums the two components at fixed
  standing (1, 1): installed `s = t1 + t2`. Replace the fixed sum with a learned
  per-layer say: installed `s = α_l · t1 + β_l · t2`, where (α_l, β_l) are
  re-fit every 50 steps by coordinate ascent on *fresh training windows only*
  (drawn via `offsets()`, never held windows), minimising next-token CE of the
  installed model; the fit starts from (1, 1) each time, moves only on strict
  improvement, and the standings are a function of the current state — logged
  per fit, never carried as a tuned artifact across runs. Export/serving strips
  the say exactly as Fable's does: the shipped weights are the plain ternary
  states at the final standings folded into `log_scale`.
- **train.py:** new flag `--say-fit 50` on Layered — `install()` gains per-layer
  `self.say` pairs (init (1.0, 1.0)); a `_refit_say()` helper called from `step()`
  every 50 steps scores candidate standings on 4 fresh `offsets()` batches
  (scoring passes charged to wall-clock and logged as overhead, per the D-wave
  protocol's honesty rule).
- **mode:** process
- **prediction:** −0.02..−0.05 at trial scale. The half-control proved the two
  components fed one stream earn nothing *summed equally* (gap 0.0020); Fable's
  record says the combination rule itself was the missing variable there —
  winner-take-all also earned nothing (worse than nothing) until the say was
  learned. If WH-061 also ties plain, the levels question closes for a deeper
  reason than F-003's bandwidth argument, and that is worth one trial.
- **status:** queued
```mill
id: WH-061
mode: process
run: --arm layered_half --rope --say-fit 50
```

### WH-062 ★ · Cross-family agreement flips (vote counter × STE shadow: agree = fast track, disagree = verify)
- **source:** Fable's side (working hive) — cross-family agreement as a free
  verifier, `training/diverse.py`, FABLE-STUDY §2.11: recruits from other families
  share fewer mistakes (joint-error overlap near chance vs ~2× chance for
  same-model pairs); voting gained nothing overall (27/32 = best alone), **but
  whenever two different families printed the same program output it was right —
  58/58 across five pairs**. Agreement = trust without a jury; disagreement =
  where to spend effort. Explicitly "not built into the run loop yet" on Fable's
  side. Muse's side's factory translation table (#19) has the same idea only as
  a measurement log between Tier-1 and Tier-0 — never inside a trainer.
- **mechanism:** The trainer runs a cheap second family alongside the votes: an
  STE shadow latent for each ternary weight, updated *only* as a direction
  witness (one fp32 EMA of the latent's implied pull, `sign(latent − installed)`,
  β=0.9 — no STE training of the model itself). Per step, per weight: where the
  shadow's pull agrees with the gated vote's sign, the vote counts **2** (the two
  families concur — the 58/58 population); where they disagree, the vote counts
  **1** as champion and the weight is added to a disagreement list. Every 100
  steps, the disagreement list's pending flips (largest |counter| first, cap
  0.1% of weights) are verified by measured delta-loss on a fresh batch before
  firing — verification effort is spent exactly where the families split, which
  is the source lesson's allocation rule. Distinct from A-012 (agreement between
  two EMAs of the *same* gradient stream — one family, two timescales), F-018
  (quorum among sub-batches of the *same* batch — one family), and MILL-231
  (verify-flips spends its budget by counter proximity, with no agreement
  signal deciding where to look).
- **train.py:** new flag `--xfamily` on Layered — shadow pull EMA buffer in
  `__init__` (4 B/weight, charged in the record's state bytes), agreement-weighted
  increment in `step()`, disagreement verification pass every 100 steps reusing
  the fresh-batch delta-loss pattern of the fisherflip entries.
- **mode:** process
- **prediction:** −0.02..−0.05 at trial scale. Mechanism check logged either way:
  audited flip accuracy split by agreement class — the source predicts agreed
  flips are near-error-free and the entire error mass sits in the disagreed
  class; if the lab's split does not show that shape, the transplant's premise
  is false here and the entry retires on its own log.
- **status:** queued
```mill
id: WH-062
mode: process
run: --arm layered_half --rope --xfamily
```

### WH-063 ★ · Growth shape schedule on the champion chassis, judged at equal steps AND equal minutes (2 blocks → 4 blocks at 50%)
- **source:** Fable's side (growing hive) — the growth-at-equal-work verdict,
  restated in the 2026-11-13 HANDOFF (FABLE-CANDIDATES, "checked — not new"
  section) and FABLE-STUDY §2.8/§3.3's equal-budget discipline: at **equal work**
  (6,420 block-steps) plain 4 blocks **3.1017**, grown 4→6 **3.1704**, fixed 6
  blocks **3.2837** — growing *loses*; at **equal clock time** the grown body
  wins (**3.085**) because the small body is cheaper per step. The verdict is a
  function of the currency, and Fable's side reports both. Muse's side's
  trainer record has never judged any shape change in both currencies: the
  scale ladder is step-boxed only, the mill probes are minute-boxed only.
- **mechanism:** Champion chassis grows mid-run: steps 0–50% run layered_half
  (2 blocks); at 50% two fresh blocks are appended (ternary states rounded from
  the current init distribution, counters at 0) and the run finishes as full
  layered (4 blocks) — total ternary weights 884,736 → 1,769,472. Following
  Fable's age-dependent recipe (newborn cells keep the *old* rate: 5e-4 beat
  3e-3 locally, FABLE-STUDY §3.3), the newborn blocks' counters run **V=48**
  for their first 25% of life while inherited blocks stay at V=32. The entry
  is judged **twice, as two separate verdicts**: (a) step-matched vs the
  layered full arm capped at the same total steps; (b) minute-matched vs both
  layered_half and layered at 8 min. The Fable prediction is imported as the
  hypothesis, not assumed: (a) loses, (b) wins — any other pattern is the
  finding. Distinct from F-047 (depth growth 3→6 by block *duplication* with
  counters *halved*, at 10M scale, single-currency) and A-035 (grows the
  second *component* of existing weights, not the model's depth).
- **train.py:** new flag `--grow-at 0.5` on Layered — model builder appends two
  `Block`s at the phase boundary; trainer extends `t1/t2/c1/c2/log_scale` lists
  for the new blocks (fresh counters, V=48 probation via a per-block votes
  array), existing blocks' state untouched byte-for-byte.
- **mode:** process — full trial only in both currencies (a 75 s probe cannot
  hold a 50% growth point and two judgements); paired side-by-side re-runs per
  FABLE-CAND-01 wherever a minutes verdict is claimed.
- **prediction:** Step-matched: **+0.02..+0.05** vs full layered (growing loses
  at equal work, per source). Minute-matched: **−0.01..−0.03** vs layered_half's
  2.8580 (the cheap early half buys steps the fixed shapes cannot). Adoption
  requires the minute-matched win AND a step-matched loss no worse than the
  source's own growth penalty (+0.069 at their scale) — the entry's product is
  the dual-currency number itself, which every future shape entry inherits.
- **status:** queued
```mill
id: WH-063
mode: process
run: --arm layered_half --rope --grow-at 0.5
```

### WH-064 · Members-first correction: the second component exists only where plain votes cannot confirm
- **source:** Fable's side — members-first routing, commit `61fb325`, seed 9007
  clean sitting (FABLE-CAND-03): **members first 10/16 in 179 min; roles alone
  9/16 in 178 min; members alone 9/16 in 69 min** — the generalist attempting
  the whole task first, with the specialist pipeline taking only what it cannot
  confirm, matched the full pipeline at ~40% of the wall time and beat it when
  combined. Filed for Muse's side's *factory* serving (factory/CANDIDATES-IDEAS,
  FABLE-CAND-03 entry); never transplanted into the trainer. Fable's caveat is
  carried with it: two members agreeing *by the same method* is not independent
  verification — so "cannot confirm" below is judged on fresh windows, not on
  the windows that produced the indecision.
- **mechanism:** Plain votes are the member; the layered correction (t2) is the
  specialist pipeline, engaged per weight only where the member cannot confirm:
  a weight's t2 counter activates when, by 60% of the run, its plain counter
  has either (a) never fired a flip, or (b) fired and reversed ≥2 times
  (oscillation = unconfirmed). All other weights keep t2 ≡ 0 for the whole run
  — the model serves as plain + a sparse correction population. Activation is
  judged at the 60% boundary on the counter record; whether an activated t2
  *earns* its place is judged at trial on fresh held windows (different method,
  per the caveat). Distinct from A-035 (t2 grown for *every* weight at 25%)
  and F-003 (t2 fed a different stream for every weight): here the specialist's
  *existence*, not its diet, is what is routed.
- **train.py:** new flag `--members-first 0.6` on Layered — t2 counters masked
  to zero until activation; activation pass at the phase boundary reads the
  plain counter's flip history (a per-weight flip/reversal log, new int8
  buffer); state bytes reported as plain + activated-fraction × t2 cost.
- **mode:** process
- **prediction:** Within ±0.015 of the full layered champion at trial scale at
  a predicted 30–55% of the t2 state — the win condition is the members-alone
  shape (same score, fraction of the cost), judged per byte. If the activated
  fraction exceeds ~70%, plain confirms almost nothing at this scale and the
  routing premise is false here — that number is reported either way.
- **status:** queued
```mill
id: WH-064
mode: process
run: --arm layered_half --rope --members-first 0.6
```

### WH-065 · Snapshot-and-immune rollback for flip cohorts (the cycle-6/7 repair, inside the trainer)
- **source:** Muse's side's factory — growth cycles 6 and 7 (2026-11-12): births
  passed both pristine gates, serving regressed (battery 0.941 → 0.934, then
  0.941 → 0.9375), and cycle 6's rollback *deleted the two serving model files
  instead of restoring them*. The repair (`growth/REPAIR-cycle-006-2026-11-12.md`)
  fixed `growth_cycle.py` to **snapshot target files before any birth and
  restore byte-for-byte on rollback**, with a regression test (suite 78/78);
  cycle 7's repair found the fix had covered only one of three cycle paths.
  Paired source: Fable's side §2.4 immune check — a newborn is refused if *any*
  known territory gets worse (`judge_local`, `e5ff3eb`). The vote trainer has
  no snapshot, no local judgement, and no rollback anywhere: a bad flip cohort
  is permanent the moment it lands.
- **mechanism:** Every 200 steps the runner snapshots the full trainer state
  (t1/t2/c1/c2 + AdamW moments + log_scale) to a ring of 2 snapshots. At each
  snapshot point, the *outgoing* 200-step cohort is judged locally: fresh-window
  training loss (never held) is split by block — cohort kept only if the pooled
  fresh loss did not regress >0.02 vs the previous snapshot point AND no single
  block's territory windows (fresh windows routed by lowest per-block loss
  contribution, the judge_local analogue) regressed >0.05. On failure: restore
  the snapshot byte-for-byte and halve the next cohort's flip budget (the
  A-017 dial, used as the immune response). All three judgement paths (pooled,
  per-block, restore) are covered by the snapshot — the cycle-7 lesson (a fix
  on one path is not a fix) is written into the entry as a completeness
  requirement, not left as commentary.
- **train.py:** new flag `--immune 200` on Layered — snapshot/restore helpers on
  the trainer (state_dict over its own tensors, not the model's), cohort
  judgement in the training loop on `offsets()` draws, restore path exercised
  by a forced-failure smoke test before any trial counts.
- **mode:** process — full trial only (cohorts of 200 steps do not exist at
  probe horizon).
- **prediction:** −0.01..−0.03 at trial scale, concentrated in seed variance:
  the champion's sd (0.0161) should shrink because the catastrophic-cohort tail
  is exactly what rollback removes. If restores fire on >1 cohort per run on
  average, the cohort is too large or the thresholds too tight — reported, not
  tuned mid-trial.
- **status:** queued
```mill
id: WH-065
mode: process
run: --arm layered_half --rope --immune 200
```

### WH-066 · Breadth flips: the per-step flip budget is spread thin across every layer before it concentrates anywhere
- **source:** The Opus method, studied on Arnav's order and adopted into Muse's
  side's repair work 2026-11-09 (`~/workspace/edit-lab/METHODS-FROM-MAKE-IT-WORK.md`):
  **breadth beats concentration — thin rank-2 edits across every module beat
  concentrated rank-8 edits**, winners chosen on a dev split. It was adopted for
  weight *editing* on Muse's side and for the factory's repair job; it has
  never been applied to the vote trainer's flips, which currently concentrate
  freely: whichever layer's counters cross in a step takes the whole step's
  flip volume.
- **mechanism:** A per-step flip budget of 0.1% of weights (the chassis's own
  measured mean flip share, ≈0.11%) is allocated **breadth-first**: each
  BitLinear layer first receives an equal share (budget / n_layers) spent on
  its largest-overshoot pending flips; only unspent share (a layer with fewer
  pending flips than its share) pools upward for a second pass. No layer may
  flip more than 2× its equal share in one step. Distinct from A-017 (a single
  global cap — concentration *within* the cap is unrestricted, which is
  precisely what the source lesson says loses) and A-018 (staggering
  *concentrates* flips into one block per step — the opposite allocation,
  already filed; WH-066 vs A-018 is a clean breadth-vs-concentration head-to-head
  the pool currently cannot run because only one side exists).
- **train.py:** new flag `--breadth-flips` on Layered — two-pass allocation in
  the flip application inside `step()` (pending sets are already computed as
  `go1/go2`; the change is the selection among them when they exceed budget).
- **mode:** process
- **prediction:** −0.01..−0.03 at trial scale; ~0 at probe (pending sets rarely
  exceed budget in the first steps). Side measurement that decides the
  mechanism even on a flat loss: per-layer flip-share variance across the run
  should fall sharply vs champion; if it does not, the budget never bound and
  the entry is void, not wrong.
- **status:** queued
```mill
id: WH-066
mode: process
run: --arm layered_half --rope --breadth-flips
```

### WH-067 · Per-direction flip switch-on with live audit and automatic retirement (the spawn trainer, per flip direction)
- **source:** Fable's side (working hive) — the spawn trainer, `team/cells/spawn.py`,
  FABLE-STUDY §2.6: a noticed job is staffed **per label** — a label switches on
  only if the newest decisions contain ≥3 cases where the member chose a
  different label, the cell is wrong at most half as often as blind answering,
  then ≥95% agreement on what it answers; at work, **1 sure call in 10 is also
  sent to the member, and live agreement under 93% (RETIRE = 0.93) retires the
  cell automatically**. The first round stayed off for lack of evidence — the
  gate refusing to fire was itself reported as a result. Muse's side's factory
  lacks per-label adoption entirely (translation table #9); the trainer has
  never gated anything per direction.
- **mechanism:** The trainer's "labels" are its four flip directions per
  component (0→+1, 0→−1, +1→0, −1→0). All directions start ON (champion
  behaviour) but are audited: 1 in 10 flips of each direction is shadow-checked
  — the flip is applied to a scratch copy of that one weight, and the fresh
  batch's loss is measured with and without it (two extra forward passes on a
  32-window batch, charged). A direction whose audited flips *hurt* the batch
  loss in >7% of audits over a trailing 50-audit window (the RETIRE=0.93
  transplant) is switched OFF for the next 200 steps: its counters keep
  accumulating (evidence is not destroyed) but its flips cannot fire. A
  direction may also be switched off *from the start* per layer if a 20-flip
  pre-audit at step 100 shows the hurt rate already >7% — the per-label
  evidence gate, with "too little evidence" (fewer than 20 audits) reported
  as exactly that, never as failure.
- **train.py:** new flag `--dir-audit` on Layered — per-direction audit
  counters and enable masks in `step()`; shadow check reuses a single-weight
  install perturbation (no full reinstall: the weight's contribution is
  recomputed for the audit batch only).
- **mode:** process — full trial only (audit statistics need hundreds of flips).
- **prediction:** −0.01..−0.04 at trial scale, with the diagnostic as the real
  product: the per-direction hurt-rate table. Prior from the state histograms:
  flips *into* 0 (feature deletion) are the likeliest chronic losers; if all
  four directions audit clean, the trainer's flip quality is uniform and that
  is a finding the lab has never had.
- **status:** queued
```mill
id: WH-067
mode: process
run: --arm layered_half --rope --dir-audit
```

### WH-068 · Gate/report split of the held set, plus a frozen yardstick that never gates (trainer-side)
- **source:** Fable's side — two linked disciplines: (i) the **gate/report
  split** (§2.4): a newborn is judged on a gate set of never-trained passages,
  while a separate report set "is only ever reported, never gated on — the
  split keeps the judging set from becoming a training target"; (ii) the
  **fixed yardstick** (§2.7, `body.YARD`): the same 300 held passages every
  time, because the all-its-text number moves whenever the harvest grows — "only
  the yardstick says whether the hive got better." Muse's side's factory
  translation table (#2/#3) records Muse's side as *weaker* on both (its held
  slices both act as gates; nothing is report-only). The BitNet mill is weaker
  still: its single 128-window held set is simultaneously the probe gate, the
  trial gate, and the reported number for every entry in the pool.
- **mechanism:** Split the judging surface three ways, permanently:
  **GATE-64** (the first 64 of the current 128 held windows) — the only surface
  probes and trials may gate/promote/adopt on. **REPORT-64** (the remaining 64)
  — computed and recorded on every verdict-bearing run, *never* read by any
  gate, promotion rule, or kill criterion. **YARD** — 128 windows drawn once
  from the corpus-v3 stream's tail (never trained on by any v1/v2 series),
  frozen in a sealed file, reported once per champion generation and never
  gated on. A GATE win that REPORT contradicts by >0.03 is stamped
  `GATE-OVERFIT SUSPECT` in the ledger — the split's whole purpose is making
  that stamp possible. Distinct from G-047 (rotating confirmation subsets —
  rotation eventually gates on everything, which is the opposite discipline)
  and E-018 (a one-off honest re-baseline on v2; WH-068 is the standing split
  every future run inherits).
- **train.py:** no trainer change; runner change in `held_windows()` usage —
  new flags `--held-split gate|report|yard` selecting which surface a run
  *reports*, with screen.py's promotion path hard-wired to `gate` (the wiring,
  not a convention, is the entry: a run that gates on report/yard is invalid
  by construction).
- **mode:** process — methodology arm; judged on the first champion generation
  run under it (GATE/REPORT divergence on the existing champion is the first
  measurement).
- **prediction:** No held-loss gain is claimed — the prediction is about the
  numbers' honesty: GATE−REPORT divergence on already-promoted arms will read
  0.01–0.03 (the selection pressure the single-set mill has silently absorbed),
  and at least one historical close verdict (margin <0.03) will fall inside
  that band. If divergence reads <0.005 across a full generation, the single
  set was honest and the split retires to a cheap permanent safeguard.
- **status:** queued
```mill
id: WH-068
mode: process
run: --arm layered_half --rope --held-split gate
```

### WH-069 · Checker-verified synthetic spans (D-002 gains a different-family filter — the coordinator-repair lesson)
- **source:** Two records, one lesson — verification must come from a *different
  method* than the thing being verified: (i) Muse's side's HiveMIND coordinator
  repair, WON and closed 2026-11-10 — the r4 finalist scored **0.954 on the
  pristine test vs the 0.930 gate/base**, and "the winning path was
  **checker-verified self-generated data, not surgery**"; (ii) Fable's side's
  members-first caveat (FABLE-CAND-03): members who ran the same broken program
  *agreed on its wrong output* — same-method agreement is not verification.
  The trainer's only self-generated-data entry, D-002, filters its spans by
  the *generating model's own* vote dynamics and its *own* CE guard band
  [1.8, 4.5] — self-verification by construction, exactly the shape both
  records warn against.
- **mechanism:** A fourth filter variant inside D-002's existing machinery
  (same generation, same 50%→85% mixing, same guard band, same pre-trial
  gates): a candidate span is kept only if a **checker from a different
  family** — the FP/STE twin of the chassis, trained once on the same corpus
  and frozen — also places the span in a usable band: checker CE ∈ [1.8, 4.5]
  AND |checker CE − generator CE| ≤ 0.75. Spans the generator loves but the
  checker finds alien (the echo-chamber signature D-002's own kill criteria
  watch for) are rejected *before* the vote-dynamic filter runs. The checker
  is never trained on synthetic data and never gates on held windows.
- **train.py:** no change; companion-runner variant of D-002 — new flag
  `--synth-filter checker` on `run_dream.py` alongside `flipband|agree|strongmass`,
  plus the one-time FP-twin checkpoint (its training cost charged to the entry,
  as MILL-113 charges its teacher).
- **mode:** process — full trial only, inheriting D-002's protocol wholesale
  (step-boxed, CONTROL-D paired, 2×2 source × filter factorial with this as
  the filtered cell).
- **prediction:** −0.01..−0.03 vs D-002a (the strongest self-filter) at trial
  scale, *if* D-002 survives its own pre-trial gates at all. If the checker's
  acceptance rate diverges wildly from the self-filters' (<5% or >80% overlap
  disagreement), that divergence is itself the measurement: it prices how much
  of D-002's "frontier band" is the generator grading its own homework.
- **status:** queued
```mill
id: WH-069
mode: process
run: --arm layered_half --rope --dream synth --synth-filter checker
```

### WH-070 · Surgery-mapped repair window (ablation map indicts one block; only its counters train)
- **source:** Arnav's surgery doctrine for Muse's side (2026-11-08): "if
  training is performing bad then surgery after mapping is necessary — map
  first (per-unit ablation), then surgery on only what the map indicts;
  training is demoted to repairing indicted units, never the blind default."
  Fable's side ran the mapping half literally (`training/cells_cut.py`,
  FABLE-STUDY §3.3): a knockout map indicted 8 near-dead layers — and its
  *removal* edit was then **rejected** on measurement (retrained cells dropped
  0.936 → 0.789), which is why this entry's surgery is repair-training of the
  indicted unit, never removal. The vote trainer has never frozen a healthy
  part to concentrate repair on an indicted one; its phases (A-038) alternate
  by clock, not by indictment.
- **mechanism:** At 50% of steps, build the map: for each block, measure the
  fresh-window loss increase when that block's ternary states are temporarily
  zeroed (ablation pass over 8 `offsets()` batches, charged as overhead). The
  block whose ablation costs the *least* loss is the indicted (near-dead /
  under-contributing) block — Fable's knockout criterion. For the next 20% of
  steps, only the indicted block's counters integrate and flip; every other
  block's counters and states freeze (AdamW parts keep training throughout —
  the frame stays live, as in D-006's lesson that the parts must be separable).
  Final 30%: normal champion training. One indictment, one repair window, no
  re-mapping — the doctrine's discipline is that the map is taken once and
  the repair is judged as a whole.
- **train.py:** new flag `--surgery 0.5,0.2` on Layered — ablation hook in the
  training loop at the phase boundary; per-block counter freeze masks in
  `step()` during the repair window.
- **mode:** process — full trial only (the map needs a trained-enough model to
  indict anything real).
- **prediction:** −0.01..−0.03 at trial scale if a near-dead block exists at
  champion scale (2 blocks: the map has only two suspects, so the prior is
  honestly weaker than at Fable's depth — a flat result plus a map showing
  both blocks load-bearing is a clean negative that retires the surgery line
  for this chassis size, which is also a deliverable).
- **status:** queued
```mill
id: WH-070
mode: process
run: --arm layered_half --rope --surgery 0.5,0.2
```

### WH-071 · Precision ladder by saturation indictment (no wider counters when the evidence, not the counter, is what is missing)
- **source:** Fable's side — the spawn trainer's size ladder (FABLE-STUDY §2.6,
  commit `47960f0`): a bigger base is tried **only if the smaller one cannot
  hold the job**, and "*no bigger base when the evidence, not the cell, is
  what is missing*." The trainer's accumulator-precision family violates this
  in both directions today: MILL-201..203 widen the increment globally by
  prescription, MILL-226/227 change the accumulator globally by prescription,
  and A-031 allocates int16 by a fixed depth prior — none of them first
  measures whether int8 evidence is actually being *clipped* anywhere.
- **mechanism:** Measure first, widen only where indicted. During the first
  25% of steps, log per layer the **saturation rate**: the share of steps on
  which a layer's counters sit at the ±V clamp while same-sign votes keep
  arriving (evidence that exists but cannot be stored — the counter, not the
  evidence, is the binding constraint, in the source's terms). At 25%, layers
  whose saturation rate exceeds 2% are widened for the rest of the run
  (counters re-cast to int16, clamp raised to ±64, flip threshold unchanged
  at 32 net votes — only the *storage* grows); all other layers stay int8 at
  champion cost. If no layer is indicted, the run is byte-identical to the
  champion and the entry reports exactly that.
- **train.py:** new flag `--ladder-precision 0.02` on Layered — saturation
  counters in `step()` (one int per layer), one-time counter re-cast at the
  phase boundary; state bytes reported as champion + widened layers only.
- **mode:** process
- **prediction:** −0.01..−0.03 at trial scale *conditional on an indictment
  existing*; the unconditional prediction is that ≤ half the layers indict
  (early blocks saturate on large early gradients; late blocks rarely do), so
  most of any global-widening gain should be buyable at a fraction of the
  global state cost. If saturation reads <0.5% everywhere, the whole
  precision-dial family (MILL-201/226/227 included) is re-priced downward
  with a measurement instead of an assumption.
- **status:** queued
```mill
id: WH-071
mode: process
run: --arm layered_half --rope --ladder-precision 0.02
```

### WH-072 · The library analogue, priced as a negative control: counter-archive restore on flip-back
- **source:** Fable's side — the library turned **off by default**: members
  *with* the library (stored material consulted instead of learned) did
  **worse than members who learned nothing, on two seeds** (Fable trace /
  HANDOFF record as carried in Muse's side's records, 2026-11-12). The
  trainer-side analogue of "data the model consults that hurts": the vote
  trainer's only consultable store is its own archived evidence. Today a flip
  *resets* the flipped component's counter to 0 — the trainer consults
  nothing. The library form would archive each counter's pre-flip value and,
  if the weight later flips *back* to the state it left, restore the archived
  counter instead of starting from 0 — the weight "consults its file" on the
  state instead of re-learning it.
- **mechanism:** One extra int8 archive per component (the counter's value at
  its last departure from the state it is now re-entering; overwritten on each
  departure). On a flip into a previously occupied state with an archive
  entry, the counter initialises to the archived value (clamped to ±(V−8) so
  restored evidence alone can never immediately re-flip) instead of 0. Every
  other rule is champion. This is not the closed overshoot carry: carry keeps
  *leftover* evidence from the *same* crossing in the *same* direction of
  travel; the archive restores evidence from a *previous visit* to a state,
  across an intervening occupation of a different state — the consultation
  event is the return, which carry never models.
- **train.py:** new flag `--counter-library` on Layered — archive buffers
  alongside `c1/c2`, restore branch in the flip application inside `step()`;
  +2 B/weight state, charged.
- **mode:** process
- **prediction:** **+0.00..+0.04 (expected flat-to-worse)** — a priced negative
  control, filed because the source result is a measured negative and the
  transplant exists to test whether it generalises: Fable's lesson predicts
  consulted stale evidence hurts *because the world (here: the rest of the
  network) changed while the file sat still*. A win here would be the more
  interesting result — it would bound the library lesson to retrieval-style
  consultation and clear counter memory as safe — and the entry is cheap
  enough that either verdict earns its probe.
- **status:** queued
```mill
id: WH-072
mode: process
run: --arm layered_half --rope --counter-library
```

---

*End of wave-3 lens 6 (cross-pollination). 12 entries, WH-061..WH-072, ranked;
★ = WH-061, WH-062, WH-063. Every entry names its source lesson with the
originating program and record, the exact transplant mechanism, and the nearest
already-filed neighbour it must not be confused with. Strongest source evidence:
WH-063 (growth at equal work vs equal minutes — a controlled three-arm verdict
measured on BitNet bodies, reported in both currencies by Fable's side itself).*

---

## Appendix — working-id mapping (miners -> wave H)

- AS-001 -> WH-001
- AS-002 -> WH-002
- AS-003 -> WH-003
- AS-004 -> WH-004
- AS-005 -> WH-005
- AS-006 -> WH-006
- AS-007 -> WH-007
- AS-008 -> WH-008
- AS-009 -> WH-009
- AS-010 -> WH-010
- AS-011 -> WH-011
- AS-012 -> WH-012
- TK-001 -> WH-013
- TK-002 -> WH-014
- TK-003 -> WH-015
- TK-004 -> WH-016
- TK-005 -> WH-017
- TK-006 -> WH-018
- TK-007 -> WH-019
- TK-008 -> WH-020
- TK-009 -> WH-021
- TK-010 -> WH-022
- TK-011 -> WH-023
- TK-012 -> WH-024
- AO-001 -> WH-025
- AO-002 -> WH-026
- AO-003 -> WH-027
- AO-004 -> WH-028
- AO-005 -> WH-029
- AO-006 -> WH-030
- AO-007 -> WH-031
- AO-008 -> WH-032
- AO-009 -> WH-033
- AO-010 -> WH-034
- AO-011 -> WH-035
- AO-012 -> WH-036
- RB-001 -> WH-037
- RB-002 -> WH-038
- RB-003 -> WH-039
- RB-004 -> WH-040
- RB-005 -> WH-041
- RB-006 -> WH-042
- RB-007 -> WH-043
- RB-008 -> WH-044
- RB-009 -> WH-045
- RB-010 -> WH-046
- RB-011 -> WH-047
- RB-012 -> WH-048
- IC-001 -> WH-049
- IC-002 -> WH-050
- IC-003 -> WH-051
- IC-004 -> WH-052
- IC-005 -> WH-053
- IC-006 -> WH-054
- IC-007 -> WH-055
- IC-008 -> WH-056
- IC-009 -> WH-057
- IC-010 -> WH-058
- IC-011 -> WH-059
- IC-012 -> WH-060
- XP-001 -> WH-061
- XP-002 -> WH-062
- XP-003 -> WH-063
- XP-004 -> WH-064
- XP-005 -> WH-065
- XP-006 -> WH-066
- XP-007 -> WH-067
- XP-008 -> WH-068
- XP-009 -> WH-069
- XP-010 -> WH-070
- XP-011 -> WH-071
- XP-012 -> WH-072
