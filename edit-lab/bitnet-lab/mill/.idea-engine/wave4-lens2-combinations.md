# Wave 4 — Lens 2: Second-Order Combinations (Muse's work — Muse's side)

<!-- Muse's work — Muse's side of the BitNet lab. Rotation-4 miner 2, SECOND-ORDER
COMBINATIONS lens. Every entry is a PAIR of already-filed, still-untested candidates
from CANDIDATES-F.md / CANDIDATES-G.md / CANDIDATES-H.md (210 entries) whose mechanisms
share a channel, a reset, a partition, or a trigger — so the pair is not the sum of its
parts. Each entry states the interaction hypothesis, the exact combined change, a 2×2
prediction (champion / A alone / B alone / both), and a kill criterion for the PAIR
claim: if both ≈ the better single (within 0.01), the interaction claim dies even if
the pair wins on loss. Distinct from G-046 (ledger-mined mill-side pairs): these are
trainer-arm pairs chosen from mechanism reasoning, before any ledger exists.
Deduped against every source file: no pair below is proposed, depended on, or implied
in either member's own text (deliberate pairs already in the files — F-001×F-016,
WH-001×WH-010, WH-014×WH-018/WH-019, G-001×G-005/G-007 — are excluded for that reason,
as are the three register examples in the assignment brief).
Chassis/bars as in waves F/G/H: champion held 2.8580 ± 0.0161; adoption >2sd AND >0.01;
singles' ranges below are the members' own filed predictions. Ranked by expected
interaction size |both − better single|. -->

---

### CB-001 ★ · F-001 × F-024 — the rerouting's exit channel is deleted and rebuilt per-row
- **source:** F-001 · Boundary-pressure rerouting — outward votes on saturated weights are destroyed by the boundary no-op; reroute them into the layer's `log_scale`. / F-024 · Homeostatic scaling — per-output-row scales servoed to an activity set-point, *replacing* the gradient-trained per-layer `log_scale` entirely.
- **interaction hypothesis:** F-024 abolishes the exact parameter F-001 reroutes into. That is not additive, it is structural: under F-024 there is no per-layer scalar to receive boundary pressure, so the pressure must land on the saturated weight's *own row scale* — a finer, local channel F-001 alone does not have. The servo also fights back: it pulls every row toward the median RMS, so rerouted pressure that inflates one row is partly taxed away every 10 steps. The pair therefore tests a new mechanism (local magnitude escape under a conserving servo), not two stacked ones.
- **exact combined change:** `--boundary-scale --homeo 0.05` on Layered: boundary-strong votes add their 1/V quantum to the accumulator of the weight's output row; the servo update every 10 steps applies (servo delta + accumulated boundary delta) to that row's scale, accumulator then resets. No per-layer `log_scale` exists in this arm.
- **mode:** process
- **2×2 prediction:** champion 2.8580 · F-001 alone −0.02..−0.05 · F-024 alone −0.01..−0.05 · **both −0.05..−0.09** if per-row escape beats per-layer escape (saturated weights cluster in high-activity rows, whose scales are exactly the ones that should move); both ≈ −0.01..−0.03 if the servo tax eats the rerouted signal.
- **kill criterion:** pair claim dies if both lands within 0.01 of the better single, OR if the logged boundary-pressure reaching row scales is <20% of what F-001 alone delivers to `log_scale` (the servo tax, not locality, was the whole story).
- **status:** queued
```mill
id: CB-001
mode: process
run: --arm layered_half --rope --boundary-scale --homeo 0.05
```

### CB-002 ★ · F-007 × G-030 — train with the lean, serve with the lean: the counter equilibrium moves
- **source:** F-007 · Counter-confidence install — during training the forward weight leans by its counter, effective = γ·(t + 0.25·c/V). / G-030 · Counter-soft install — eval-only readout installing t + α·(c/V), α fitted on calibration windows, on champion-trained weights.
- **interaction hypothesis:** one-entry-fixes-the-other's-weakness, with a twist. G-030 alone suffers a train/serve mismatch: the network never trained with leaned weights. F-007 removes that mismatch — but it also changes the *equilibrium* the counters reach: if the forward already expresses a fraction of the pending evidence, gradient pressure to complete the flip falls, so final counters should sit systematically closer to threshold than champion counters do. G-030's α, fitted on champion dumps, therefore mis-transfers to F-007 dumps in a predictable direction (the pair needs a *smaller* α for the same served offset). Neither single can see this; only the pair measures it.
- **exact combined change:** train `--conf-install 0.25` (F-007 as filed), dump final state, then readout `--counter-soft` with α refit on calibration windows *from the F-007 run* (α ∈ {0.15, 0.3, 0.5}); the 2×2's other cells are F-007 + plain readout and champion training + G-030 at its filed α grid.
- **mode:** process
- **2×2 prediction:** champion 2.8580 · F-007 alone −0.02..−0.05 · G-030 alone −0.005..−0.03 · **both −0.04..−0.08**, with the fitted α_pair measurably below α_champion-fit and the final |c| distribution shifted toward threshold vs the F-007-alone dump.
- **kill criterion:** pair claim dies if both is within 0.01 of F-007 alone with plain readout (the soft serve added nothing once training matched it), OR if α_pair ≈ α_champion-fit and the counter distributions are indistinguishable (no equilibrium shift — the mismatch story was wrong).
- **status:** queued
```mill
id: CB-002
mode: process
run: --arm layered_half --rope --conf-install 0.25 --readout counter-soft
```

### CB-003 ★ · G-014 × F-022 — coherent evidence is the fuel the cascade is starved of
- **source:** G-014 · Sequential stream walk — replace i.i.d. offsets with a contiguous tile walk (stream-shuffled arm), giving counters long temporally-coherent evidence runs. / F-022 · Benna–Fusi cascade — a fast counter (clamp ±8) must saturate repeatedly to feed a slow counter; the weight flips only at |cs| ≥ 4, so one-off bursts die and only persistent evidence becomes durable.
- **interaction hypothesis:** pure synergy with a stated mechanism. The cascade's transfer rule rewards *persistence across time*; i.i.d. sampling is the zero-coherence stream, the worst possible input for it — F-022's own filed prediction is two-sided (−0.02..+0.02) precisely because the chassis starves it. The stream walk manufactures exactly the long agreeing runs that push cf to saturation again and again. Conversely the walk's known risk (a locally one-topic stretch stampedes counters) is what the cascade's fast stage absorbs. Each entry covers the other's filed weakness.
- **exact combined change:** `--sampler stream-shuffled --cascade 8:4` on the plain_half chassis (F-022's chassis, as filed): contiguous shuffled-tile batches feeding the two-stage cascade trainer; all other settings champion.
- **mode:** process
- **2×2 prediction:** champion (i.i.d., plain counters) = rung control · G-014 alone −0.01..−0.05 · F-022 alone −0.02..+0.02 · **both −0.04..−0.08**, i.e. strictly better than either single by ≥0.02, with cs-transfer counts per step at least 2× the F-022-alone rate.
- **kill criterion:** pair claim dies if both is within 0.01 of G-014 alone (coherence helped, the cascade was inert decoration), OR if the cs-transfer rate under the walk is not measurably higher than under i.i.d. (the fuel story never happened, whatever the loss says).
- **status:** queued
```mill
id: CB-003
mode: process
run: --arm plain_half --rope --sampler stream-shuffled --cascade 8:4
```

### CB-004 · F-003 × F-006 — canonicalization assumes the components are interchangeable; the innovation channel says they are not
- **source:** F-003 · Orthogonal second channel — c1 integrates sign(g); c2 integrates sign of the gradient *innovation* sign(g − EMA(g)), a different bit of information. / F-006 · Canonicalization — every 32 steps each (t1, t2) pair is rewritten to its canonical representative, counters remapped as c_backbone = clip(c1 + c2), c_corr = 0, installed value unchanged.
- **interaction hypothesis:** predicted *interference*, and the most falsifying pair in this file. F-006's remap is only harmless if c1 and c2 are two piles of the same evidence — true on the champion, false by construction under F-003, where summing the counters mixes a level signal with a change signal and zeroing c2 erases the innovation integrator every 32 steps. If the pair collapses to F-006-alone or worse, F-003's bandwidth claim survives a hard test; if the pair wins anyway, the innovation channel was never carrying distinct information and F-003's premise dies instead. One of the two premises must lose.
- **exact combined change:** `--t2-innov --canon 32` on Layered, both exactly as filed; log the post-canon c2 regrowth curve as the mechanism diagnostic.
- **mode:** process
- **2×2 prediction:** champion 2.8580 · F-003 alone −0.02..−0.06 · F-006 alone −0.01..−0.03 · **both −0.00..−0.02** (canon strips most of F-003's gain; the residual is F-006's own churn reduction) — a negative interaction of 0.02–0.04 against the better single.
- **kill criterion:** pair claim (interference) dies if both ≥ F-003 alone − 0.01, i.e. canonicalization costs the innovation channel nothing; in that case F-003's "independent second bit" claim is what dies, and that verdict must be written onto F-003's record.
- **status:** queued
```mill
id: CB-004
mode: process
run: --arm layered_half --rope --t2-innov --canon 32
```

### CB-005 · F-013 × G-022 — two entries with opposite premises about early positions, forced to share a run
- **source:** F-013 · Position-information-weighted votes — early positions have tiny context, so their vote-path loss is down-weighted by w_t = log2(t+2)/log2(258). / G-022 · Stationary mixed context lengths — each batch draws ctx ∈ {64, 128, 256}, so positions 0–63 receive ~3× the gradient exposure of positions 192–255.
- **interaction hypothesis:** the premises collide on the same quantity. G-022's stated bet is that early positions are *undertrained* and deserve more exposure; F-013's stated bet is that early-position evidence is *low-quality* and deserves less vote weight. Run together, G-022 triples the supply of exactly the evidence F-013 discounts. If F-013 is right, it should rescue G-022 from its own side effect (exposure without quality) and the pair beats both; if G-022 is right, F-013's discount throws away the extra exposure and the pair falls back to F-013 alone. The pair adjudicates a premise, not just a loss.
- **exact combined change:** `--ctx-mix 64,128,256 --posw-vote` on Layered, both as filed; verdict at equal steps (G-022's primary currency), per-position held loss logged for positions 0–63 vs 192–255.
- **mode:** process
- **2×2 prediction:** champion 2.8580 · F-013 alone −0.01..−0.03 · G-022 alone −0.01..−0.03 · **both −0.03..−0.06** under the F-013-premise (discounted-but-frequent early evidence is the best of both), with the early-position held slice improving more than the global mean; under the G-022-premise both ≈ −0.01..−0.02.
- **kill criterion:** pair claim dies if both is within 0.01 of the better single AND the early-position slice moves with the global mean (no position-specific mechanism fired — the two dials were simply independent).
- **status:** queued
```mill
id: CB-005
mode: process
run: --arm layered_half --rope --ctx-mix 64,128,256 --posw-vote
```

### CB-006 · F-002 × F-043 — at the V the scaling law demands, the slow counter is reset to death
- **source:** F-002 · Weak-half slow counter — gated-out weak votes feed a second counter at V_slow = 128; *any* flip (fast or slow) resets both counters. / F-043 · Vote-threshold scaling law — V must fall as N rises: V ≈ 8 at the 10M rung to hold flip share ≈ 0.001/step.
- **interaction hypothesis:** interference through the shared reset, invisible at champion scale. F-002's slow counter needs 128 net weak votes *uninterrupted*; every fast flip wipes it. At V = 32 fast flips are rare enough that some slow climbs survive. At F-043's 10M setting (V = 8) fast flips fire ~4× as often per weight, so the slow counter's expected uninterrupted run collapses and its contribution should vanish — F-002's benefit is a *function of V*, and the pair maps that function at the one rung where both entries are detectable. The combined arm also forces a design question neither file asks: should V_slow scale with V (128 → 32) or stay absolute?
- **exact combined change:** 10M rung, ladder/long format as in F-043: `--votes 8 --weak-slow 128` (absolute arm) and `--votes 8 --weak-slow 32` (proportional arm) against `--votes 8` alone and the champion-scale F-002 record; slow-flip count logged separately from fast flips.
- **mode:** process
- **2×2 prediction:** rung control (10M, V=32) 2.9472 · F-002 alone (champion scale) −0.01..−0.04 · F-043 alone (10M, V=8) −0.04..−0.10 vs rung control · **both (absolute 128) ≈ F-043 alone ± 0.01 with slow flips ≈ 0**; both (proportional 32) recovers −0.01..−0.03 beyond F-043 alone if the reset-starvation account is right.
- **kill criterion:** pair claim dies if the absolute arm's slow-flip count is comparable (within 25%) to its champion-scale rate — then fast flips do not starve the slow counter and there is no interaction to price — or if the proportional arm also adds nothing, in which case F-002's evidence simply does not exist at 10M regardless of resets.
- **status:** queued
```mill
id: CB-006
mode: process
run: --arm layered --rope --dim 512 --layers-n 3 --votes 8 --weak-slow 128
```

### CB-007 · WH-025 × F-010 — deep supervision manufactures the upstream flip volume that triggers the discount
- **source:** WH-025 · Deep supervision — block 1 gets a direct same-token CE (weight 0.1, every 4th position), shortening its gradient path. / F-010 · Cross-layer staleness discount — whenever block 1's per-step flip share exceeds 0.2%, block 2's counters are written down ×0.75, because upstream flips stale downstream evidence.
- **interaction hypothesis:** a causal chain through a measured trigger. WH-025's own filed diagnostic predicts block-1 flip share *rises* under deep supervision. F-010's discount fires only on steps above the 0.2% trigger — a rate set from champion flip share (~0.11% mean), which WH-025 deliberately inflates. So the pair should discount block 2 far more often than F-010 alone ever does: either that is exactly right (block 2's evidence really is staler when block 1 is learning faster — synergy), or the discount becomes a near-constant leak that taxes block 2 for block 1's improvement (interference). F-010 alone cannot distinguish "fires rarely because staleness is rare" from "fires rarely because the trigger was calibrated to a slow block 1."
- **exact combined change:** `--deep-sup 0.1 --xstale 0.75` on Layered, both as filed; trigger-fire rate and block-2 counter mass logged per phase.
- **mode:** process
- **2×2 prediction:** champion 2.8580 · WH-025 alone −0.02..−0.05 · F-010 alone −0.01..−0.03 · **both −0.04..−0.07** if the discount rate rises to match real staleness (fire rate 2–4× F-010-alone); both ≈ −0.00..−0.02 if the write-downs become a constant tax (fire rate >8× with block-2 flip share collapsing).
- **kill criterion:** pair claim dies if the trigger-fire rate under the pair is within 25% of F-010 alone (deep supervision did not move the quantity the discount prices — the chain never closed), whatever the held loss does.
- **status:** queued
```mill
id: CB-007
mode: process
run: --arm layered_half --rope --deep-sup 0.1 --xstale 0.75
```

### CB-008 · WH-014 × G-001 — the per-part ratio loses its biggest member and gains 4,096 new ones
- **source:** WH-014 · Embedding rows join the vote trainer — the tied table leaves AdamW, becomes ternary with per-row scales; served bytes 3.81 MB → ~0.86 MB at a predicted +0.04..+0.12 nats/token cost (per-byte win if ≤ +0.05). / G-001 · Per-part lr ratio — log_scale hot at 3e-3, embedding cold at 3e-4, norms at 1e-3, instead of one pooled lr.
- **interaction hypothesis:** G-001's ratio was designed for 8 log_scale scalars and one FP embedding table. Under WH-014 the embedding group *ceases to exist* in AdamW, and the "scale" group grows from 8 scalars to 4,096 per-row scales — the only continuous degrees of freedom the ternary table has. Running those at G-001's hot 3e-3 could either compensate the ternary table's coarseness (the scales do all the fine fitting, faster — shrinking WH-014's filed cost below its per-byte bar) or destabilise it (4,096 hot scalars chasing a still-flipping code). G-001 alone says nothing about this: its hot group was 8 parameters, not 4,096.
- **exact combined change:** `--emb-vote --part-lr scale:3e-3,emb:3e-4,norm:1e-3` on Layered, where the part-lr "scale" group is defined to include the per-row embedding scales alongside the 8 layer log_scales; norms at champion; judged on WH-014's pre-stated per-byte bar, not raw loss.
- **mode:** process
- **2×2 prediction:** champion 2.8580 at 3,806,208 B · WH-014 alone +0.04..+0.12 at ~860,000 B · G-001 alone −0.02..−0.05 at full bytes · **both +0.00..+0.06 at ~860,000 B** — i.e. the hot-scale ratio claws back roughly half of WH-014's cost, landing the pair at or inside the ≤ +0.05 per-byte adoption bar that WH-014 alone is predicted to straddle.
- **kill criterion:** pair claim dies if both's cost vs champion is within 0.01 of WH-014 alone's cost (the ratio did nothing for the row scales — G-001's effect lives only in its original 8 scalars), or if both is *worse* than WH-014 alone by >0.02 with row-scale path length exploding (hot scales are a liability at 4,096-wide, closing the transfer).
- **status:** queued
```mill
id: CB-008
mode: process
run: --arm layered_half --rope --emb-vote --part-lr scale:3e-3,emb:3e-4,norm:1e-3
```

### CB-009 · G-013 × F-018 — does the quorum already eat the seams, or only their votes?
- **source:** G-013 · Boundary-masked line packing — pack whole lines, mask the ~7 seam targets per window out of the CE entirely (no loss, no gradient, no vote). / F-018 · Byzantine quorum — split each batch into 4 sub-electorates; a counter moves only when ≥3 of 4 sub-batches agree on the sign.
- **interaction hypothesis:** redundancy-vs-complementarity on the same noise source. Seam positions are the highest-loss, most contradictory gradients in every window — exactly the evidence most likely to split sub-electorates 2–2 and force abstentions. If the quorum is already neutralising seams *in the vote path*, G-013 adds nothing under F-018 (pair ≈ F-018 alone). But F-018 leaves the AdamW path untouched — the FP parts still step on the summed gradient including seams — while G-013 removes seams from both paths. The pair's margin over F-018 alone therefore prices the seam damage done through AdamW specifically, a quantity no single entry isolates.
- **exact combined change:** `--pack-mask --byz 4:3` on Layered (v2 corpus, as G-013 specifies), both as filed; quorum agreement rate and abstention rate logged per phase.
- **mode:** process
- **2×2 prediction:** champion 2.8580 · G-013 alone −0.02..−0.06 · F-018 alone −0.01..−0.05 per step · **both −0.04..−0.08** if the AdamW-path seam damage is real (sub-additive vs the naive sum, super-additive vs either single), with the quorum abstention rate falling measurably vs F-018 alone because the surviving evidence agrees more.
- **kill criterion:** pair claim dies if both is within 0.01 of the better single AND the abstention rate is unchanged from F-018 alone (the two mechanisms were eating the same noise through the same path — full redundancy, and one of the two entries should be retired in the other's favour).
- **status:** queued
```mill
id: CB-009
mode: process
run: --arm layered_half --rope --corpus v2 --pack-mask --byz 4:3
```

### CB-010 · G-017 × F-048 — the discount deletes the repetition, leaving only the phase: a decomposition pair
- **source:** G-017 · Stride-64 overlap lattice — every token appears in exactly 4 windows at 4 different window positions; predicted −0.01..−0.04 if phase diversity is the active ingredient, +0.02..+0.05 if unique coverage dominates. / F-048 · Repetition-discounted votes — a vote from a window on its n-th visit counts with probability 1/n, so repeated evidence cannot masquerade as independent evidence (10M multi-epoch format).
- **interaction hypothesis:** the pair is a scalpel for G-017's own ambiguity. G-017 bundles two effects — 4× repetition of each token and 4-phase diversity — and its filed prediction cannot separate them. F-048 prices repetition at its actuarial value (the 4 testimonies of one token count as ~1 + 1/2 + 1/3 + 1/4 ≈ 2.08, not 4). Under the pair, whatever gain survives *is* the phase-diversity effect, and whatever vanishes was repetition inflation. That attribution is the deliverable; it exists in neither single.
- **exact combined change:** F-048's multi-epoch format (10M shape, fixed corpus slice) with the sampler restricted to the stride-64 lattice and per-window visit counts fed to `--rep-discount`, both mechanisms exactly as filed; judged at equal steps against the format's undiscounted, non-lattice control.
- **mode:** process
- **2×2 prediction:** format control = baseline · G-017 alone (in-format) −0.01..−0.04 · F-048 alone −0.03..−0.08 in epochs 3–4 · **both −0.03..−0.06**, sitting strictly between the singles if phase diversity is worth about half of G-017's effect; both ≈ F-048 alone if G-017 was pure repetition.
- **kill criterion:** pair claim (that the pair decomposes G-017) dies only if the lattice's visit structure cannot be logged cleanly in the multi-epoch format — on the numbers, every outcome is a verdict: both ≈ G-017-alone-plus-F-048's epoch gain means phase and repetition were independent after all, and *that* equality, if it lands within 0.01 of the additive prediction, is the result that kills the interaction claim.
- **status:** queued
```mill
id: CB-010
mode: process
run: --arm layered --rope --dim 512 --layers-n 3 --stride 64 --rep-discount
```

### CB-011 · WH-027 × F-002 — which "weak" deserves a slow counter: weak-for-the-layer or weak-for-itself?
- **source:** WH-027 · Self-normalised surprise gate — the gate is taken on g / (per-weight EMA of |g|): a weight votes when its gradient is large *for it*, not for its layer. / F-002 · Weak-half slow counter — the gate's rejected half feeds a slow counter at V_slow = 128 instead of being discarded.
- **interaction hypothesis:** both entries act on the same object — the gate partition — but they define its halves differently, and F-002's premise is partition-specific. F-002 argues the rejected half carries the same sign bias as the accepted half, only noisier. That was derived for *layer-relative* weakness. Under WH-027 the rejected population is a different set: weights having a typical-for-them step, including chronically-large weights on quiet steps — a population whose sign bias has never been argued for by anyone. The pair tests whether "the discarded half is evidence" is a property of discarding, or of *this particular* discard rule; the slow flips under the pair should come from a measurably different weight population than under F-002 alone.
- **exact combined change:** `--surprise-gate --weak-slow 128` on Layered: the slow counter is fed by WH-027's shaped-gate rejects (the gate already computes the partition inside `step()`); slow-flip population logged by layer-relative |g| rank so the two arms' flip populations can be compared directly.
- **mode:** process
- **2×2 prediction:** champion 2.8580 · WH-027 alone a modest gate-partition gain (its file's class: −0.01..−0.03) · F-002 alone −0.01..−0.04 · **both −0.03..−0.06** if self-relative rejects carry at least as much slow evidence as layer-relative ones (the union of two differently-defined weak sets is larger than either); both ≈ WH-027 alone if the surprise-gate's rejects are genuinely empty of signal.
- **kill criterion:** pair claim dies if both is within 0.01 of the better single AND the slow-flip population under the pair is the same population (same weights, same layers, within sampling noise) as under F-002 alone — then the partition definition never mattered and the interaction was illusory.
- **status:** queued
```mill
id: CB-011
mode: process
run: --arm layered_half --rope --surprise-gate --weak-slow 128
```

### CB-012 · F-064 × WH-033 — a cull that imposes 70% zeros meets a controller that defends 42%
- **source:** F-064 · The 70% zero cull — every 10 steps, randomly zero currently-nonzero weights (counters zeroed) until the installed zero fraction is exactly 70%. / WH-033 · Homeostatic histogram regularizer — every 20 steps, if the zero fraction leaves the band [0.38, 0.46], votes in the restoring direction count double until it re-enters.
- **interaction hypothesis:** two opposed forces create a selection process neither has alone. The cull is deliberately skill-free (uniform random), and the homeostat is deliberately blind (it defends a fraction, not particular weights). Together they form a ratchet: the cull knocks weights to zero at random; between culls the homeostat, seeing z = 0.70 ≫ 0.46, doubles every away-from-zero vote, so the weights that regrow first are the ones with the strongest live evidence, while unevidenced culled weights stay zero. Random destruction + evidence-priced regrowth = a sparsity *selection* mechanism assembled from two entries that each claim to have no selection in them. The steady state should sit between 46% and 70% zeros, occupied by a better-chosen population than either endpoint's.
- **exact combined change:** `--zero-cull 0.7 --cull-every 10 --hist-homeo 0.38,0.46` on Layered, both exactly as filed; zero fraction and the identity overlap between successive post-cull regrowth sets logged per cull cycle.
- **mode:** process
- **2×2 prediction:** champion 2.8580 · F-064 alone within +0.02 of champion counts as its filed "interesting" outcome · WH-033 alone ~0..−0.02 (the band rarely binds on champion runs) · **both −0.01..−0.04 at a served zero fraction of ~50–60%** — a loss win F-064 alone does not predict and a sparsity level WH-033 alone never reaches; the pessimistic branch is an oscillator (z sawtooths 0.46↔0.70, held +0.02..+0.05) if the doubled votes regrow everything indiscriminately.
- **kill criterion:** pair claim dies if both is within 0.01 of F-064 alone at the same final zero fraction (the homeostat contributed nothing but arithmetic), OR if the regrowth sets show no evidence concentration — post-cull regrown weights' mean |counter| no higher than a random nonzero set's — in which case the ratchet never existed.
- **status:** queued
```mill
id: CB-012
mode: process
run: --arm layered_half --rope --zero-cull 0.7 --cull-every 10 --hist-homeo 0.38,0.46
```

---

## Miner's note

The pair I would bet on most is **CB-003 (G-014 × F-022)**: it is the only pair here
where each member's filed prediction already names the other's absence as its limiting
factor — the cascade is two-sided *because* i.i.d. evidence cannot persist, and the
stream walk's stampede risk is exactly what a fast-saturating first stage absorbs.
CB-001 is the largest predicted swing but carries redesign risk (the rerouted channel
has to be rebuilt per-row before it can be tested); CB-004 is the cheapest certain
information — one of two filed premises must lose, and the mill learns which for the
price of one trial.
