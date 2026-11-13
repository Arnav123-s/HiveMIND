# Wave 2 Lens 5 — MODEL COMPOSITION (Muse's work — Muse's side)

Header: **Muse's work — Muse's side**

<!-- Muse's work — Muse's side of the BitNet lab. Idea Engine wave G, miner 5.
Nothing here is in the pool until the pool's owner merges it. Fable's side untouched. -->

Territory: composing WHOLE vote-trained models — ensembles, logit voting,
weight-space merging, member exchange, distillation between vote models — as
`train.py`-level experiments. The factory has its own composition line
(`factory/COMPOSITION-RESEARCH.md`: voting/routing rules over 16 bug-pattern
classifier margins in `serve.py`); nothing below touches it — every entry here
runs in the BitNet trainer/eval path on language models.

**F-033 is TAKEN and is not re-proposed.** F-033 splits ONE trained layered
checkpoint into its t1/t2 components and votes their logits. Every entry below
composes models that were *trained as wholes* (independent runs, independent
counters) — a different population with different decorrelation.

## Byte accounting — the frozen convention for this file

Served bytes = the full served artifact, counted honestly: ternary bodies
packed at 0.25 B/weight per physical component (a plain body = 1 component;
a layered body = 2), FP parts at 4 B/param (token embedding 4096·dim, position
embedding 256·dim — carried even with `--rope` — final norm, per-block norms
and biases at 13·dim/block). This is the physical-component counting
NUMBERS.md lists as its 0.5 B/w sensitivity for layered arms, applied
uniformly. Training-state bytes are never the budget here; served bytes are.

| artifact | ternary B | FP B | **served B** |
|---|---:|---:|---:|
| plain_half solo (dim 192×2, 884,736 w) | 221,184 | 3,363,840 | **3,585,024** |
| layered_half CHAMPION (2.8580 ± 0.0161) | 442,368 | 3,363,840 | **3,806,208** |
| plain_full solo (dim 192×4) | 442,368 | 3,383,808 | **3,826,176** |
| 2M rung, layered+rope (held 3.2745, 3 seeds) | 995,328 | 5,045,760 | **6,041,088** |
| 2M rung, plain+rope (same shape) | 497,664 | 5,045,760 | **5,543,424** |
| 10M rung, layered+rope (held 2.9472, seed 0 only) | 4,718,592 | 8,996,864 | **13,715,456** |
| 10M rung, plain+rope (same shape) | 2,359,296 | 8,996,864 | **11,356,160** |

Key arithmetic the whole file leans on: at half size the FP stack
(3,363,840 B) is 88–94% of served bytes and the token embedding alone is
3,145,728 B. A second ternary *body* costs only 221,184 B (+ its block-local
norms/biases, 19,968 B) if the artifact genuinely shares one embedding/head.
Composition at this scale is therefore mostly an *embedding-accounting*
question, and every prediction below names its byte-matched baseline.

Baselines named in predictions: champion layered_half+rope **2.8580**
(3,806,208 B); plain_half **2.9010** (no-rope record, RESULTS-HALF-CONTROL;
rope twin re-measured in-run wherever used); 2M rung **3.2745** (task brief
rounds 3.2746); 10M rung **2.9472** (n=1, 56 steps — context only, never a
same-format comparator). Format is full trial (3 seeds × 8 min) unless an
entry says ladder format (56 steps).

**Dedupe, stated once:** MILL-113/114/115 + A-064 distill from an *FP teacher*
into a single student — no entry here uses an FP teacher. MILL-218/219 modal
readout averages checkpoints *within one run* — merges below are *across
runs*. The scale-next overlap program composes *tilted* generalists on
corpus-v2 at 2M/10M shapes under its serialized-artifact rule, with an
untilted ensemble only as its attribution control; entries here are
untilted, champion-scale, corpus-v1 trainer-format experiments whose
questions (counter merging, grafting, transplant, diversity selection) the
overlap program never asks. Its shared-embedding variant is a labelled
sensitivity there; here the shared artifact *is* the proposed architecture,
counted in full above.

---

### MC-001 ★ · Two plain bodies, one shared embedding — an ensemble at exactly the champion's bytes
- **source:** byte arithmetic above + RESULTS-HALF-CONTROL-2026-11-12 (plain_half 2.9010 ≈ layered_half 2.8990: at equal size/steps the second *component* earns nothing summed into the same weight)
- **mechanism:** Train two plain_half+rope bodies (data seeds 0 and 1, same init seed) that share ONE token+position embedding and tied head — the artifact is a single model file: shared FP embedding stack (3,343,872 B incl. final norm) + 2 bodies (each 221,184 B ternary + 19,968 B block-local FP) = **3,826,176 B served, +0.52% vs the champion's 3,806,208** and byte-identical to a plain_full solo. Serve by mean of the two bodies' logits. The bet: the layered idea's missing 0.04 was never about levels — two *decorrelated wholes* at the same bytes vote better than two *summed components*. Sharing the embedding is not an accounting trick: the bodies' only difference is their blocks, and the shared head forces both to speak the same output geometry, which is what makes their logits commensurable.
- **train.py:** new runner `mill/run_compose.py --shared-ens 2` (trains two `plain_half --rope` bodies against one shared `tok`/`pos` embedding module — embedding grads from both bodies summed, one AdamW step per body step, alternating windows) + eval path `--ens-eval` reporting each body solo and the logit-mean on the 128 held windows. Also report the duplicated-embedding control (two fully independent plain_half, 7,170,048 B) once, so the sharing cost is priced, not assumed.
- **mode:** process
- **prediction:** Ensemble held **2.82–2.86 at trial format, beating the byte-matched champion baseline 2.8580 (3,806,208 B)** and each body solo (~2.88–2.92) by ≥0.03; the duplicated-embedding control is predicted within 0.01 of the shared version — i.e. the second embedding's 3.34 MB buys nothing. Kill: ensemble ≥ best body solo − 0.01 (no decorrelation even across data seeds) or shared-vs-duplicated gap > 0.03 (the sharing is doing hidden damage and the honest artifact is the 7.17 MB one).
- **status:** queued
```mill
id: MC-001
mode: process
run: --arm plain_half --rope --shared-ens 2
```

### MC-002 ★ · Counter-sum merge — average the counters, not the weights: do counters merge better than weights?
- **source:** the vote trainer's own structure — a run's knowledge lives in (ternary state t, int8 counter c) pairs, and c is *integrated gradient evidence* that every weight-space merge in the literature throws away; the lab itself discards counters at serving (overlap Fact 1)
- **mechanism:** Train two plain_half+rope runs with the SAME init seed and different data streams (states start identical, diverge only by votes, so counters are commensurable). Each weight's implied latent position is L = 32·t + c ∈ [−64, +64]. Merge: L̄ = (L_A + L_B)/2, then t_m = clamp(round(L̄/32), −1, 1), c_m = round(L̄ − 32·t_m). Per-layer scales and all FP parts are averaged (standard soup on the FP side, same-init so averaging is sound). The merged artifact is ONE plain model: **3,585,024 B served — 221,184 B under the champion**. Companion readout in the same entry: state-only merge (MC-005's rule) on the same two runs, so "counters vs states" is one paired comparison, not two anecdotes.
- **train.py:** new eval/merge path `--counter-merge A.pt B.pt` in train.py (loads two saved trainer states — requires `--save-state` on the donor runs: t, c, log_scales, FP state_dict), writes the merged model and reports held for donor A, donor B, state-only merge, counter merge, on the 128 held windows.
- **mode:** process
- **prediction:** Counter merge held **≤ 2.88 at trial format — beating both donors (~2.90, the plain_half baseline family) and beating the state-only merge by ≥0.015, at 3,585,024 B vs the champion's 3,806,208 (2.8580)**. Reasoning: where donors disagree on a weight, the one whose counter has climbed further toward its next flip holds the fresher evidence; the latent-average rule prices exactly that, while a state majority vote treats a just-flipped weight and a long-settled one as equals. Kill: counter merge ≤ state merge (counters carry no mergeable information beyond states — a clean, quotable negative that also caps F-033-style hopes) or merged ≥ worse donor.
- **status:** queued
```mill
id: MC-002
mode: process
run: --arm plain_half --rope --counter-merge 2
```

### MC-003 ★ · Sequential boosting — model 2 trains only on model 1's residual windows, served as a logit sum
- **source:** task territory (boosting) + the lab's own failweight line (MILL-406: ONE model oversamples its own failures *during* its own training — no second model, no additive serving, exists in the pool)
- **mechanism:** Model 1 = plain_half+rope, champion recipe, full format. Freeze it. Score every training-pool window by model 1's per-window loss; model 2 (same shape, fresh init) trains with window sampling probability ∝ clip(loss₁, 1.0, 6.0) — it spends its whole vote budget where model 1 is provably wrong-but-learnable (windows where loss₁ > 6 are near-irreducible on this corpus and are capped, the known boosting-on-noise guard). Serve shared-embedding (MC-001 accounting): logit = logit₁ + α·logit₂, α ∈ {0.5, 1.0} chosen on 32 validation windows drawn from the training pool, never the 128 judge windows. **Served 3,826,176 B (+0.52% vs champion).** Distinct from the overlap exchange round: that patches *relative* weakness between *tilted generalists* on corpus-v2 at rung shapes; this is a strict sequence — model 2 has no generalist duty at all, only residuals.
- **train.py:** new sampler flag `--boost-from <m1-ckpt>` in train.py (precomputes per-window loss₁ once, ~1 extra pass over the pool, charged) + `--ens-alpha` in the eval path of `mill/run_compose.py`.
- **mode:** process
- **prediction:** Boosted pair held **2.83–2.87 at trial format vs the byte-matched champion 2.8580**, and — the discriminating claim — ≥0.015 better than MC-001's *parallel* pair at identical served bytes: sequential residual training should buy more than a second independent opinion at this scale, because model 2's flips are spent entirely on windows the pair currently loses. Diagnostic reported either way: pair's loss on model-1's worst training decile vs MC-001's pair on the same decile. Kill: boosted ≤ parallel pair (residual targeting earns nothing over independence — boosting joins failweight as a within-noise idea) or model 2 solo < 3.30 (it never became a language model at all, only a patch — then the α-fit is hiding a broken member).
- **status:** queued
```mill
id: MC-003
mode: process
run: --arm plain_half --rope --boost-from m1 --ens-alpha fit
```

### MC-004 · Three fully independent seeds at full price vs one bigger single model at the same bytes
- **source:** task territory (independently-seeded ensembles at equal total bytes vs one bigger model) — the honest-price version of MC-001: NO sharing anywhere
- **mechanism:** Three independent plain_half+rope runs (seeds 0/1/2, own embeddings), served by logit-mean: **3 × 3,585,024 = 10,755,072 B**. Byte-matched single comparator: one plain+rope run at dim 464 × 4 layers = **10,761,088 B (+0.06%)**, same trial format, same tokens. Context baseline: the 10M plain rung serves 11,356,160 B (5.6% MORE than the ensemble) and the 10M layered rung recorded 2.9472 at 56 steps — different format, quoted only to show the ensemble is not sneaking a size advantage.
- **train.py:** no training change (existing flags: members `--arm plain_half --rope`; comparator `--arm plain --rope --dim 464 --layers-n 4`); ensemble read via `--ens-eval` from MC-001's runner.
- **mode:** process
- **prediction:** Ensemble held **2.80–2.85 at trial format, beating the byte-matched 464×4 single by 0.02–0.06** — three decorrelated 0.88M-weight opinions over one 10.6M-weight opinion, because at fixed bytes the single model's extra weights are mostly *more embedding* (its FP stack is ~7.4 MB of its 10.76 MB), not more diverse computation. Kill: single ≤ ensemble (bytes really are fungible into width/depth at this scale, and every shared-embedding entry above inherits a problem: their wins were budget, not composition).
- **status:** queued
```mill
id: MC-004
mode: process
run: --arm plain_half --rope --ens-eval 3 --vs-single 464x4
```

### MC-005 · Ternary majority soup — merge the final states only, counters discarded
- **source:** model-soup literature transplanted to ternary states; the deliberate control twin of MC-002 (same donors, dumber merge) — the pair is the experiment
- **mechanism:** From MC-002's same two donors (plus a third seed for a true majority): per weight, merged state = majority of {t_A, t_B, t_C} (3-way splits and A≠B in the 2-donor read resolve to the better-solo donor's state); per-layer scales averaged; FP parts averaged. Counters are *not read*. Served as ONE plain model: **3,585,024 B, 221,184 B under the champion (2.8580)**; solo baseline plain_half 2.9010 family.
- **train.py:** `--state-merge A.pt B.pt C.pt` in train.py's merge path (sibling of `--counter-merge`; shares the `--save-state` donor plumbing).
- **mode:** process
- **prediction:** Majority soup held **2.88–2.91 at trial format: better than the mean donor, worse than MC-002's counter merge by ≥0.015** — the gap between MC-005 and MC-002 *is* the measured value of the counter as a mergeable object, the lab's first price on its own training state. Kill: soup ≥ mean donor (independent-seed ternary states are not even majority-compatible — same-init divergence is chaos, not diversity; that result would also kill MC-002's premise and must be reported with it).
- **status:** queued
```mill
id: MC-005
mode: process
run: --arm plain_half --rope --state-merge 3
```

### MC-006 · Flip-pattern diversity as a member-selection metric
- **source:** task territory — ensemble folklore says "diversity helps" but the lab has never *measured* diversity in its native unit: the flip pattern (which weights sit where, and which windows members disagree on)
- **mechanism:** Train 6 plain_half+rope members (seeds 0–5, trial format). For every pair compute (a) served-state Hamming distance (fraction of weights with different t) and (b) per-window loss disagreement on 256 training-pool validation windows. Select the 3-member subset by greedy max-min Hamming distance; serve shared-embedding (**4,067,328 B**: shared FP 3,403,776 incl. block-local FP for 3 bodies + 3 × 221,184 ternary). Comparators at identical bytes and identical member pool: best-3-by-solo-loss subset, and the mean of 5 random 3-subsets. The selection metric costs zero training — it spends information the runs already produced.
- **train.py:** `--diversity-select 3` in `mill/run_compose.py` (pairwise Hamming + disagreement tables printed to the record; subset chosen before any held evaluation — selection never sees the 128 judge windows).
- **mode:** process
- **prediction:** Diversity-selected trio held **0.01–0.03 better than the best-by-loss trio at trial format, both read against the champion-bytes neighbourhood (champion 2.8580 at 3,806,208 B; this trio serves +6.9% more bytes and must beat 2.8580 outright to justify itself)**. Predicted side-finding: Hamming distance and window disagreement correlate only weakly (ρ < 0.5) — weight-space diversity and function-space diversity are different goods, and only the functional one should predict ensemble gain. Kill: diversity trio ≤ random-trio mean (the metric selects nothing real) or Hamming predicts gain *better* than disagreement (then selection is trivial and the functional machinery is waste).
- **status:** queued
```mill
id: MC-006
mode: process
run: --arm plain_half --rope --diversity-select 3
```

### MC-007 · Counter transplant — swap two runs' counters at mid-training, keep their states
- **source:** member exchange, trainer-side — the causal test underneath MC-002: if counters from another run can be *dropped into* a live run without damage, counters are fungible evidence and merging them is principled; if the transplant wrecks the run, each counter is married to its own state's history
- **mechanism:** Two plain_half+rope runs, same init seed, different data streams (MC-002's donor configuration, so donors are shared across entries). At 50% of steps, swap the full counter arrays c_A ↔ c_B; states, scales, FP parts stay with their original run. Continue to full format. Controls: the unswapped donor pair (already run for MC-002/005 — zero extra cost). Served: each transplanted model solo at **3,585,024 B**; secondary read: their shared-embedding logit pair at 3,826,176 B vs the control pair from MC-001.
- **train.py:** new flag `--swap-counters <peer-state-file> --swap-at 0.5` on the Direct trainer (state file written at the swap step by a paired-runner mode in `mill/run_compose.py --paired-swap`).
- **mode:** process
- **prediction:** Transplant costs **+0.02..+0.06 vs the unswapped controls (~2.90 solo baseline family)** — counters encode *which evidence this state has already acted on*, so a foreign counter double-counts some flips and orphans others. The size of the cost is the deliverable: cost ≈ 0 would be the more explosive result (counters are pure evidence integrals, fully portable — MC-002's merge becomes the conservative option and mid-run counter *pooling* becomes the obvious next entry). Kill (of the portability claim): cost > +0.10 — counters are state-history, full stop.
- **status:** queued
```mill
id: MC-007
mode: process
run: --arm plain_half --rope --swap-counters peer --swap-at 0.5
```

### MC-008 · Block grafting — serve block 1 from member A and block 2 from member B
- **source:** member exchange at the block level (model surgery between whole vote models; the factory's surgery line works on hive specialists, never on trainer checkpoints)
- **mechanism:** From trained plain_half+rope members, assemble grafts: (block1_A, block2_B) and (block1_B, block2_A), FP parts averaged, no retraining. Two arms: donors share the init seed (states start aligned) vs donors fully independent (different init — permutation misalignment should bite). Then a repair arm: each graft gets 14 steps (25% of a ladder run) of continued vote training at V=32. Served solo: **3,585,024 B** per graft. Baselines: donor solos (~2.90 family) at identical bytes; champion 2.8580 at 3,806,208 B.
- **train.py:** `--graft A.pt B.pt --take-blocks 1,2` in train.py's merge path + standard continued-training invocation for the repair arm (`--init-from graft.pt --steps 14`).
- **mode:** process
- **prediction:** Same-init grafts lose **+0.05..+0.15** vs donors (block 2 was vote-trained on block 1's *evolved* outputs, not its final ones — a real but bounded mismatch); different-init grafts lose **≥ +0.50** (near-collapse: the misalignment price, measured for the first time on vote models); 14 repair steps recover ≥ 70% of the same-init graft's deficit. Kill: same-init grafts ≥ +0.30 (blocks are not modules even under shared init — composition below the whole-model level is dead in this lab, which fences MC-012 too) or different-init grafts lose < +0.10 (alignment doesn't matter, which would contradict everything known about permutation symmetry and demand its own investigation).
- **status:** queued
```mill
id: MC-008
mode: process
run: --arm plain_half --rope --graft A B
```

### MC-009 · Ensemble-into-one distillation — a vote-trained student drinks the ensemble
- **source:** task territory (distillation *between vote models*) — distinct from MILL-113/115/A-064 on both ends: the teacher is a *vote ensemble*, not an FP twin, and the student is *vote-trained*, not STE/layered
- **mechanism:** Teacher = MC-001's shared two-body ensemble (3,826,176 B, teaching-time only). Student = one plain_half body, vote-trained from scratch on the same windows with loss = CE + 1.0 · KL(teacher‖student) at temperature 2 (MILL-113's dose, kept deliberately so the teacher swap is the only change). The vote counters integrate the KD gradient's sign exactly as they integrate CE's — the question is whether a *ternary teacher's* dark knowledge (its per-token uncertainty, produced by two disagreeing ternary bodies) survives the 1-bit vote channel. **Student served solo: 3,585,024 B — 221,184 B under the champion.**
- **train.py:** new flag `--kd-ens <ens-ckpt> --kd 1.0` on the Direct trainer in train.py (teacher forward per step, frozen, charged: expect ~0.7× steps/minute, reported).
- **mode:** process
- **prediction:** Student held **2.86–2.89 at trial format — recovering ≥ 50% of MC-001's ensemble gain over a solo plain body while serving under the champion's 3,806,208 B (champion baseline 2.8580)**; and ≥ 0.01 better than a CE-only student trained identically (the in-entry control). Kill: student ≈ CE-only control (the vote channel cannot carry teacher distributions — KD on this trainer needs the FP teacher's smoother signal, MILL-113's design was right by necessity) or student ≥ 2.92 (distillation actively hurts votes).
- **status:** queued
```mill
id: MC-009
mode: process
run: --arm plain_half --rope --kd-ens shared2 --kd 1.0
```

### MC-010 · Distill the ensemble at the counter level — initialize the student's counters from the teachers' disagreement
- **source:** composition of MC-002 and MC-009 — if counters are evidence (MC-002's claim), a student should be able to *inherit* evidence, not just imitate outputs
- **mechanism:** Student starts from the MC-005 majority-soup states. Its counters initialize NOT at 0 but at c₀ = (c_A + c_B)/2 from MC-002's donors, clipped to ±16 (half of V, so no inherited flip can fire without ≥ 16 fresh agreeing votes — the F-015 warm-start cap logic applied across models). Student then vote-trains on CE only, full format. Control: identical soup init with counters at 0. **Served 3,585,024 B.**
- **train.py:** `--init-counters avg --init-from soup.pt` on the Direct trainer (donor plumbing from `--save-state`).
- **mode:** process
- **prediction:** Counter-inherited student beats the zero-counter control by **0.01–0.03 at trial format** (both vs the plain_half 2.9010 solo family; champion 2.8580 at +221,184 B remains the adoption bar) — inherited counters aim the student's first flips at the weights both teachers were *about* to move, the exact population a cold start wastes its first ~32 steps re-deriving. Kill: inherited ≤ control (teacher counters point at teacher-specific futures; cross-model evidence inheritance is dead even when output distillation in MC-009 works — a clean split between the two distillation channels).
- **status:** queued
```mill
id: MC-010
mode: process
run: --arm plain_half --rope --init-from soup --init-counters avg
```

### MC-011 · Agreement-gated partial merge — merge the blocks where members agree, ensemble only where they don't
- **source:** MC-006's diversity tables + MC-008's grafting question, composed: full ensembles pay a second body for *every* block; if disagreement is concentrated in one block, the agreeing block can be merged for free
- **mechanism:** From MC-001's two bodies: per block, compute served-state agreement (fraction of equal t). Blocks with agreement ≥ τ (τ ∈ {0.85, 0.90, 0.95}, chosen on validation windows) are merged by MC-002's latent-average rule into ONE block; blocks below τ stay as two parallel bodies under the shared embedding. Predicted artifact (block 1 merges, block 2 doesn't): shared FP 3,343,872 + merged block (110,592 ternary + 9,984 FP) + 2 unmerged blocks (2 × 120,576) = **3,705,600 B — 100,608 B under the champion**, with the logit read taken after the unmerged block(s) (both copies forwarded, logits averaged at the head).
- **train.py:** `--gated-merge A.pt B.pt --agree-tau {0.85,0.90,0.95}` in the merge path of train.py / `mill/run_compose.py` (block-wise agreement report is a required output, not a by-product).
- **mode:** process
- **prediction:** The gated artifact lands **within 0.01 of MC-001's full ensemble at trial format while serving fewer bytes than the champion (2.8580 at 3,806,208 B)** — *if* agreement is block-concentrated (predicted: block 1 agreement ≥ 0.90, block 2 ≤ 0.85, because late blocks absorb the data-seed divergence). Kill: agreement is uniform across blocks (within 0.02) — partial merging has no structure to exploit at 2 blocks, and the entry retires until a ≥4-block chassis gives it room; or the gated artifact loses > 0.02 vs the full ensemble at any τ (the merged block was carrying diversity the agreement metric can't see).
- **status:** queued
```mill
id: MC-011
mode: process
run: --arm plain_half --rope --gated-merge --agree-tau 0.90
```

### MC-012 · How the vote is taken — weighted, geometric, and median logit composition of the same members
- **source:** the composition rule itself, never varied in this lab: every ensemble read above assumes uniform arithmetic logit-mean (inherited from F-033's spec and the overlap program's primary read)
- **mechanism:** Eval-only, on MC-004's three independent members (no new training): compare (a) uniform logit-mean [the standing rule], (b) weighted logit-mean — per-member scalar weights + one temperature fitted by minimizing loss on 256 training-pool validation windows (4 scalars total, +16 B served, counted), (c) probability-mean (average softmax, then log), (d) median-of-logits per token (robust rule: one bad member cannot drag a token). Plus a stress read: corrupt one member (shuffle its block-2 rows) and re-read all four rules — the robust rule should degrade least, pricing robustness as a property, not a hope. **Served 10,755,072 B (+16 B for rule (b)) in all arms** — the members are identical; only the read differs. Baselines: members solo (~2.90 family); rule (a) is the number MC-004 stands on.
- **train.py:** `--ens-rule {logit,weighted,prob,median}` in the `--ens-eval` path (weight fit on validation windows only; judge windows untouched by fitting).
- **mode:** process
- **prediction:** On clean members the four rules land **within 0.01 of each other** (members this similar leave the rule nothing to decide — itself the finding that retires rule-shopping at this scale); weighted beats uniform by ≤ 0.01 and its fitted weights stay within [0.7, 1.4] (no member is secretly carrying the trio). Under corruption: median loses ≤ half what logit-mean loses. Kill: any clean-rule gap > 0.02 (the standing uniform read has been leaving real loss on the table in every ensemble number the lab will ever quote — then the winning rule must be retro-applied to MC-001/003/004's reads before their verdicts stand).
- **status:** queued
```mill
id: MC-012
mode: process
run: --arm plain_half --rope --ens-eval 3 --ens-rule all
```

---

## Rank order and the ★ three

1. **MC-001 ★** — the exact-bytes ensemble: two plain bodies on one shared
   embedding serve at 3,826,176 B vs the champion's 3,806,208 B. If
   decorrelated wholes beat summed components at the *same* bytes, the
   layered result gets its explanation and the lab gets a new champion form
   for free. Cheapest decisive composition test available.
2. **MC-002 ★** — counter-sum merge: the only entry that treats the vote
   counter as what it is — integrated evidence — and asks whether it merges
   better than the weights it produced. A win ships a *single* model under
   champion bytes; a loss cleanly closes cross-run merging. Either way the
   lab learns what its training state is worth.
3. **MC-003 ★** — sequential boosting at MC-001's exact bytes: the
   head-to-head (sequential-residual vs parallel-independent) is the
   composition question with the most riding on it, because the overlap
   program's exchange loop is a parallel-patching bet — this prices the
   sequential alternative at 1/12th of its byte budget before it scales.

Then MC-004 (the fungibility control every other entry leans on), MC-009,
MC-006, MC-005, MC-007, MC-011, MC-010, MC-008, MC-012 (eval-only; run it
the moment MC-004's members exist, whatever its rank).

**Best single idea: MC-001.** It needs no new mechanism — two bodies, one
embedding, a logit mean — and its byte match to the champion is exact to
0.52%, so its verdict cannot be argued with on budget grounds. It also
manufactures the donors, checkpoints, and shared-embedding serving path
that MC-003, MC-006, MC-009, and MC-011 all reuse.
