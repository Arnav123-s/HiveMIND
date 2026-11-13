# Lens 4 — SCALE EXTRAPOLATION (Muse's work — Muse's side)

<!-- Muse's work — Muse's side of the BitNet lab. Miner 4, Idea Engine. -->

Header: **Muse's work — Muse's side**

Premise of this lens: every dial in the lab was tuned at 0.885M ternary weights
(dim 192 × 2 blocks). The measured ladder already shows the ground moving —
2M rung held ≈3.2746 (3 seeds, 56 steps), 10M seed 0 = 2.9472 at equal tokens,
and flip share FALLS with size (≈0.00021/step at 10M, so a specialty weight needs
~190 tilted steps to earn one flip — longer than any ladder run). Each entry below
rests on a scaling fact, predicts a sign or optimum that DIFFERS from the 0.885M
reading, and names the smallest rung where the difference is detectable. Nothing
here re-proposes a closed arm (carry, cooldown, anneal, magnitude votes as
specified, JEPA) or a pooled item (small-size V/gate/batch grids, MoE forms,
Hadamard, embedding pricing, ladder trainer crosses, B-031's precision-law fit) —
several entries deliberately test those dials' *interaction with N*, which no
existing entry does.

Rung references: 2M champion = layered+rope, dim 288 × 2, 1,990,656 weights,
3.2746. 10M champion = layered+rope, dim 512 × 3, 9,437,184 weights, 2.9472
(n=1). 50M champion = the same recipe extrapolated to dim 1024 × 4, 50,331,648
weights, 56 steps — unmeasured; predictions at 50M are vs that configuration
run at 50M, not vs a recorded number.

---

### SX-001 · Vote-threshold scaling law: V must FALL as N rises ★
- **source:** scale reasoning — per-weight vote evidence dilutes as weights multiply at fixed tokens: flip share fell from ~0.0011/step (0.885M champion) to ≈0.00021/step at 10M, i.e. at fixed V=32 the trainer gets ~5× colder per 10× of weights. Extrapolated to 50M/500M, V=32 leaves most weights unflipped for the entire run — the model ships near its init.
- **mechanism:** Open-loop threshold law V(N) set to hold flip share ≈0.001/step: V ≈ 32 at 0.885M, ≈16 at 2M, ≈8 at 10M, ≈4 at 50M (int16 counters not needed; hotter, not colder). Distinct from MILL-501..509 (V grid at ONE size), MILL-207/208 (per-layer feedback to a flip-rate target within a run), and A-025 (depth prior): this is a single global V chosen from N before the run, and its claim is that the V-curve's minimum MOVES with N.
- **train.py:** sweep config, no new mechanism — `--arm layered --rope --votes {32,16,8,4}` crossed with rung shapes `--dim 288 --layers-n 2` / `--dim 512 --layers-n 3` / `--dim 1024 --layers-n 4`, ladder format `--steps 56`. Smallest rung where detectable: **10M** (at 2M the dilution is only ~2× and V=16 vs 32 is expected within noise; include 2M as the negative control).
- **mode:** sweep
- **prediction:** At 10M, V=8 beats the rung champion 2.9472 by −0.04..−0.10 and V=16 by −0.02..−0.05, reversing the 0.885M expectation that colder is safer; at 2M all three sit within ±0.02 of 3.2746. At 50M the V=32 champion-config is predicted ≥0.15 worse than V=4.
- **status:** queued
- ★ Top-3 reason: if this law is real and untested, every rung above 2M is being trained with a systematically frozen trainer — the single most expensive silent error available at scale.

### SX-002 · Rotating eligibility phases: concentrate evidence on a subset ★
- **source:** scale reasoning — total gradient mass per step is fixed by tokens, not by N, so mean evidence per weight falls as 1/N; at 10M a weight already needs ~190 tilted steps per flip, and at 50M/500M uniform eligibility means almost no weight ever accumulates 32 net votes inside a feasible run.
- **mechanism:** Only 1/k of weights are vote-eligible in each phase (k=5 at 10M, k=10 at 50M); eligibility rotates by weight-index hash every 20 steps so every weight gets focused windows, and ineligible weights' counters are paused (not decayed). Eligible weights receive the full batch's evidence with no dilution across the frozen majority's noise votes. Distinct from A-018 (per-step block rotation of flip *application*; counters still accumulate everywhere) and A-017 (a cap on flips, evidence still uniform): here the *evidence stream itself* is concentrated.
- **train.py:** new flag `--eligible-k 5 --eligible-phase 20` on Layered (hash-partitioned mask over flattened weight index, rotated per phase). Smallest rung where detectable: **10M** (at 0.885M/2M uniform evidence is already sufficient — the mask only throws away signal there).
- **mode:** process
- **prediction:** At 10M ladder format, −0.03..−0.08 vs 2.9472, with eligible-phase flip share ≥4× the champion's 0.00021/step; at 2M, +0.00..+0.04 (expected slightly worse — the control that proves it is a scale effect, not a free win).
- **status:** queued
- ★ Top-3 reason: it is the only entry that attacks evidence dilution structurally instead of retuning around it, and it gets *more* necessary, not less, at 500M.

### SX-003 · Sparse counter store: evict near-zero counters ★
- **source:** scale reasoning — counter state (~1 B/weight per component, ~2 B layered) scales linearly with N while the shared parts' AdamW state does not grow with ternary count; at 500M the counters alone are ~1 GB, exceeding the served ternary bytes (~100 MB packed) by ~10×. Simultaneously, evidence sparsity means the large majority of counters sit at |c| < 4 at any moment at scale.
- **mechanism:** Counters live in a sparse store: a weight's counter is materialised only once |c| would reach 4, and evicted back to 0 if it decays below 2 (hysteresis band prevents thrash). Evicted evidence is genuinely discarded — the claim is that at scale, sub-4 evidence is noise-dominated and its loss costs less than the state it occupies. At 0.885M the dense store is trivially cheap, so this is pointless there by construction.
- **train.py:** new flag `--counter-sparse 4,2` on Layered (sparse dict/hash storage for c1/c2, dense fallback below 2M weights). Report state bytes alongside held loss; judged per byte. Smallest rung where detectable: **10M** (state saving ≈5–8× there; loss cost is the measurement).
- **mode:** process
- **prediction:** At 10M, held within +0.00..+0.02 of 2.9472 at ≤25% of the champion's counter bytes — a per-byte win. Falsifier: if the loss cost exceeds +0.03, weak evidence was load-bearing and the dilution picture in SX-001/SX-002 needs revising.
- **status:** queued
- ★ Top-3 reason: at 500M the vote trainer's state economy — its founding claim vs STE's ~12 B/weight — quietly inverts unless the counter store stops being dense; nobody else in the pool prices counter bytes at scale.

### SX-004 · Function-preserving width growth: 2M → 10M with inherited counters
- **source:** scale reasoning — training cost per step grows with N, but a 10M model trained from scratch spends its scarce 56 ladder steps re-learning what a 2M model already knows; at fixed total tokens, growing a trained small net should beat a fresh big one, and the gap widens with the size ratio (invisible at 0.885M, where from-scratch is cheap).
- **mechanism:** Train the 2M rung to its 56 steps, then widen dim 288 → 512 by duplicating each ternary weight's row/column with ±1-level perturbations (installed values preserved in expectation), inheriting counters scaled ×0.5, and train the remaining token budget at 10M shape. Control: 10M from scratch at equal TOTAL tokens (2M phase tokens charged to the growth arm).
- **train.py:** new runner path `--grow-from <2m-ckpt> --grow-width 512` (weight duplication + counter inheritance in the Layered trainer). Smallest rung where detectable: **10M** (growth target; the 2M source is the measured rung).
- **mode:** process
- **prediction:** −0.05..−0.12 vs 2.9472 at equal total tokens. If growth merely ties, from-scratch scaling is healthier than the step-scarcity argument assumes — also a load-bearing answer for the 50M/500M rungs, where from-scratch may be unaffordable outright.

### SX-005 · Depth growth by block duplication: 3 blocks → 6, counters halved
- **source:** scale reasoning — depth is the axis where a vote-trained net can add capacity without diluting per-weight evidence as fast as width does (new blocks get fresh weights; existing blocks keep their evidence), but from-scratch depth at 50M pays full price for early blocks that a shallower trained net already solved.
- **mechanism:** Train the 10M shape (dim 512 × 3), then duplicate each block once (6 blocks, ~18.9M weights) with the copy's counters set to half the source's and its ternary states perturbed on 5% of weights; finish at equal total tokens vs an 18.9M from-scratch control. Distinct from A-035 (growing *components* within a weight) and from Fable-side block growth (FP/STE chassis, no counter inheritance — the vote-specific question is whether banked evidence survives duplication).
- **train.py:** new runner path `--grow-depth 2` on Layered. Smallest rung where detectable: **10M** (as the source; effect read at the ~19M target).
- **mode:** process
- **prediction:** −0.03..−0.09 vs the from-scratch ~19M control at equal tokens; the diagnostic that matters is post-growth flip share in duplicated blocks — if it collapses to the 50M-style starved regime, depth growth inherits SX-001's problem instead of dodging it.

### SX-006 · Repetition-discounted votes: evidence decays with window visits
- **source:** scale reasoning — the corpus holds only ~0.91M unique real pieces (corpus-v2: 907,409 unique); at 0.885M a run barely repeats data, but any serious 50M/500M training is necessarily multi-epoch, and a vote counter cannot distinguish "32 independent windows agree" from "the same window seen 32 times" — repeated windows can single-handedly flip weights, manufacturing structure that is memorisation, not evidence.
- **mechanism:** Each training window carries a visit count; a vote cast from a window on its n-th visit is counted with probability 1/n (stochastic discount, expectation-exact). Fresh windows vote at full strength forever. Distinct from B-009 (measures epoch scaling, changes no rule), B-007/B-008 (corpus-side dedup/filtering), and MILL-406 failweight (oversamples by loss): this discounts by *repetition*, inside the vote accounting.
- **train.py:** new flag `--rep-discount` on Layered/Direct (sampler exposes per-window visit counts to the vote path). Requires a multi-epoch format: 10M shape, 4 epochs over a fixed 25% corpus slice, steps-matched control. Smallest rung where detectable: **10M**, long format only — undetectable in 56-step ladder format at any rung, stated plainly.
- **mode:** process
- **prediction:** In epochs 3–4, held −0.03..−0.08 vs the undiscounted control (which is predicted to *gain* train loss while losing held — the memorisation signature); epochs 1–2 within noise of control.

### SX-007 · Gate quantile × width crossover: q must RISE with fan-in
- **source:** scale reasoning — batch-level gradient statistics change character with width: as fan-in grows, per-weight gradient magnitudes concentrate (relative spread shrinks ~1/√fan-in), so the median gate at q=0.5 increasingly admits weights whose |g| is barely above a tightening median — the "stronger half" becomes a weaker filter exactly as the weight count explodes.
- **mechanism:** The gate quantile becomes a width-dependent setting: q=0.5 at dim 192, q=0.75 at dim 512, q=0.9 at dim 1024. Distinct from MILL-601..606 (q grid at the champion shape only): the claim is an interaction — q=0.9 is expected to *lose* at 0.885M (too little evidence survives) and *win* at 10M+.
- **train.py:** sweep of existing-style flags at rung shapes: `--arm layered --rope --gate-q {0.5,0.75,0.9} --dim 512 --layers-n 3 --steps 56` (gate-q flag per MILL-601 family). Smallest rung where detectable: **10M**.
- **mode:** process
- **prediction:** At 10M, q=0.75 beats 2.9472 by −0.02..−0.06 and q=0.9 by −0.01..−0.05; at 0.885M the pooled q grid is expected to show the reverse ordering. A flat q-response at 10M falsifies the gradient-concentration story.

### SX-008 · Large-batch vote regime: batch 256–512 with step-matched judging
- **source:** scale reasoning — at 50M+ a step is expensive and tokens are the budget; large batches are the only way to spend tokens, but one vote per weight per step throws away the extra evidence a 512-batch carries (per-step gradient SNR rises ~√batch while the counter still increments by ±1). The batch grid pooled at champion shape (16/64/128, judged per-minute) cannot see this regime.
- **mechanism:** At the 10M rung, run batch {32, 128, 512} judged at EQUAL STEPS (56) and equal tokens separately — two verdicts, not one. The scale claim: batch 128–512, which loses per-minute at 0.885M, wins per-step at 10M because each vote is cast on far cleaner evidence, partially compensating the dilution in SX-001.
- **train.py:** sweep config only — `--arm layered --rope --dim 512 --layers-n 3 --steps 56 --batch {32,128,512}`. Smallest rung where detectable: **10M**.
- **mode:** sweep
- **prediction:** Per-step at 10M: batch 128 held −0.03..−0.07 vs the batch-32 champion's 2.9472; batch 512 a further −0.00..−0.03 per-step but clearly worse per-token. If per-step ordering at 10M matches the 0.885M per-minute ordering, batch is not a scale lever and SX-001's law must carry the dilution alone.

### SX-009 · Vocabulary scaling at fixed ternary budget: 4096 → 16384 at 50M
- **source:** scale reasoning — served bytes flip composition with scale: at 0.885M the FP tied embedding (4096 × 192) rivals the ternary body, but at 50M the ternary share dominates, so vocabulary — unaffordable at lab size — becomes cheap per byte exactly when a bigger vocab's shorter sequences (fewer pieces per byte of text) start paying. Nobody has varied vocab size at any size (B-002 refits the tokenizer at the SAME size; MILL-118/119 price embedding precision/tying at 4096).
- **mechanism:** At the 50M shape, vocab 16384 with a tokenizer refit at that size on corpus-v2, ternary count held at ~50M (dim trimmed 1024 → 960 to pay the embedding). Judged in nats/byte, not nats/token.
- **train.py:** config + corpus rebuild — `--vocab 16384 --dim 960 --layers-n 4 --steps 56` on the 50M shape, corpus-v2 rebuilt at the new vocab. Smallest rung where detectable: **50M** (at 10M the embedding still eats the win — run 10M as the predicted-negative control).
- **mode:** process
- **prediction:** At 50M, nats/byte −0.02..−0.05 vs the 4096-vocab champion-config despite flat-to-worse nats/token; at 10M, nats/byte +0.01..+0.04 (worse). The crossover itself is the deliverable — it sets the vocab for every rung above 50M.

### SX-010 · Iso-weight shape reversal at 50M: deep-narrow beats wide-shallow
- **source:** scale reasoning — the shape grid (MILL-1101..1113) and its stated prior ("wider-shallower has the better prior at fixed weights") were established at ≤1.33M weights, where a block is cheap and depth's compounding of ternary error is short. At 50M the terms trade places: wide layers dilute per-weight evidence (SX-001) across more weights per block, while depth reuses each block's evidence through more composition.
- **mechanism:** One iso-weight pair at ~50.3M ternary weights, same recipe, ladder format: wide = dim 1024 × 4 blocks; deep = dim 512 × 16 blocks. Nothing else varies.
- **train.py:** sweep config only — `--arm layered --rope --dim {1024,512} --layers-n {4,16} --steps 56`. Smallest rung where detectable: **50M** (a 10M version — 512×3 vs 362×6 — is a legitimate cheap pre-read but the claimed reversal is a 50M claim).
- **mode:** sweep
- **prediction:** Deep beats wide by −0.04..−0.10 at 50M, reversing the small-shape prior; if wide still wins at 50M, the prior is scale-free and the 500M shape is settled cheaply — either outcome retires a whole axis of guessing.

### SX-011 · Recurrent depth: block sharing ×2 at 10M, judged per byte
- **source:** scale reasoning — redundancy grows with size: at 0.885M every block is load-bearing, but at 10M+ adjacent blocks in trained transformers are measurably similar, so applying one 10M block-stack twice (effective depth 6, stored depth 3) should cost little loss while halving stored ternary bytes — a trade that only exists once the model is big enough to have slack.
- **mechanism:** The 10M shape (dim 512 × 3 stored blocks) with each block applied twice in sequence; votes accumulate from both applications into the shared block's counters (evidence per stored weight doubles — a side benefit under dilution). Judged per served byte against the unshared 10M champion and against a stored-3/applied-3 control at equal steps.
- **train.py:** new flag `--share-blocks 2` in the model builder. Smallest rung where detectable: **10M**.
- **mode:** process
- **prediction:** Held +0.01..+0.04 vs 2.9472 (a small cost) at 50% of the ternary bytes — a per-byte win; at 0.885M the same trick is predicted to cost +0.08 or more, which is why it was never worth pooling there.

### SX-012 · Depth-graded freezing at depth ≥6: bottom half sets early
- **source:** scale reasoning — with depth, early blocks' flips perturb every downstream block's evidence stream; at 2 blocks freezing half the net is absurd, but at 6–16 blocks the bottom half converges first (its gradients are the least diluted — shortest path from the loss through shared structure) and its late flip noise is pure cost imposed on all blocks above it.
- **mechanism:** On a depth-6+ shape, the bottom half of blocks stop flipping after 50% of steps (counters keep recording, flips are suppressed — so the freeze is reversible and auditable), while the top half trains to the end. Distinct from A-037/D-006 (whole-structure or AdamW freezes at 2 blocks) — the claim is specifically that the freeze boundary should sit mid-depth and only exists at depth.
- **train.py:** new flag `--freeze-bottom 0.5,0.5` (fraction of blocks, fraction of run) on Layered, run at dim 768 × 6 (~42M) or the SX-010 deep shape. Smallest rung where detectable: **50M** (depth 6 at ~42–50M; at the 10M rung's depth 3 the "bottom half" is 1–2 blocks and the effect is not separable from noise).
- **mode:** process
- **prediction:** −0.02..−0.06 vs the 50M champion-config at equal steps, with top-half flip share rising after the freeze (evidence stops being scrambled from below). A loss would mean early-block plasticity is still earning at depth — which would re-rank SX-005's depth-growth assumptions.

---

*End of lens 4. 12 entries (SX-001..SX-012), ranked; ★ = SX-001, SX-002, SX-003.*
