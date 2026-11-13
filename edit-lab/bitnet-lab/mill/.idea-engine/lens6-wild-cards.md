# Lens 6 — WILD CARDS for the Idea Engine (Muse's work — Muse's side)

<!-- Muse's work — Muse's side of the BitNet lab. Miner 6, wild-cards lens, 2026-11-12.
Champion: layered_half + rotary, held 2.8580 ± 0.0161, V=32, median strong gate,
counters clamp ±V and reset on flip. Mill probe = 75 s / 1 seed (vs job-zero MILL-000,
same champion generation); trial = 3 seeds × 8 min; adoption bar >2 sd AND >0.01.
Every entry below was deduped against mill/IDEA-POOL.md, CANDIDATES-A/B/C/D and
FABLE-CANDIDATES.md. The register's five example shapes (neighbors-only training,
anti-majority phase, heavy-tailed per-weight V, counter stealing, weak-half gate) were
deliberately NOT copied — these are different inversions. Nothing closed is re-proposed
in its original form. Ranked by (payoff if true) × (cheapness of kill test). -->

### WC-001 · ★ The reservoir control: never train the ternary weights at all
- **source:** wild-card reasoning — a careful person filters this because it "isn't training the model": freeze every ternary state at its random init for the whole run and let only the FP parts (embeddings, norms, per-layer scales) learn. They might be wrong to skip it: the lab has never priced what vote training itself earns against a random ternary reservoir with trained scales, and every votes-vs-STE comparison silently assumes the answer is "a lot."
- **mechanism:** random frozen ternary matrices are a fixed random-feature reservoir; the FP parts fit readouts/scales to it. The probe measures the exact size of the hole the vote mechanism fills — the denominator every other entry in the pool is implicitly divided by.
- **train.py:** new flag `--freeze-tern 0.0` on Layered (ternary states and counters frozen from step 0; AdamW group trains normally) — `--arm layered_half --rope --freeze-tern 0.0`
- **mode:** process
- **prediction:** interesting if probe held lands within 0.10 of job-zero — that would mean most of the champion's quality is reservoir + FP fitting, and the entire vote program is fighting over a sliver.
- **kill test:** retire if the one probe lands ≥ job-zero + 0.30 (frozen reservoir catastrophically worse): votes plainly earn their keep, the suspicion dies in 75 seconds, and the number still enters the record as the mechanism's priced floor.
- **status:** queued

### WC-002 · ★ Knowledge lives in the counters: wipe the last block's weights, keep its counters
- **source:** wild-card reasoning — a careful person filters this because deliberately destroying trained weights mid-run looks like sabotage. They might be wrong: the trainer's design says the counters ARE the accumulated evidence and the ternary state is just their readout; if so, a wiped block should be rebuilt by its own banked counters within a few dozen steps, and "training" was never in the weights at all.
- **mechanism:** every 20 steps, re-randomise block 2's ternary states (t1/t2) while leaving c1/c2 untouched. Counters keep voting from their banked positions, so flips re-install approximately the pre-wipe state — unless the knowledge was in the states, in which case each wipe is a real amputation.
- **train.py:** new flag `--wipe-block 2 --wipe-every 20` on Layered (state re-init only; counters, scales, AdamW untouched) — `--arm layered_half --rope --wipe-block 2 --wipe-every 20`
- **mode:** process
- **prediction:** interesting if probe held is within +0.03 of job-zero despite ~5–8 full wipes in a probe run — recovery that fast proves counters carry reconstructable knowledge, a claim no entry in the pool makes.
- **kill test:** retire if probe held ≥ job-zero + 0.10, OR if the logged post-wipe flip share does not spike to ≥3× the run's mean flip share in the 5 steps after a wipe (no spike = the counters are not even trying to rebuild; the mechanism story is dead on its own terms).
- **status:** queued

### WC-003 · ★ Easy-only diet: throw away every hard window, train on what the model already gets right
- **source:** wild-card reasoning — a careful person filters this because training only on mastered material "teaches nothing," and the pool's whole data side pushes the other way (failweight, mistake replay, hard curricula). They might be wrong: a vote counter needs CONSISTENT evidence to reach 32 net votes; hard windows are exactly where per-batch gradient signs contradict each other and cancel in the counter. A coherent, easy gradient field may build clean structure that generalises to hard windows it never saw.
- **mechanism:** score windows once with the init model (the curriculum family's existing scoring pass); exclude every window above the median loss from the stream entirely — not downweighted, not ordered: gone. The run trains on the easy half only, at matched step count.
- **train.py:** new flag `--easy-only 0.5` (sampler exclusion by init-loss percentile; distinct from A-041's ordering, which keeps all data, and A-056's 2% trim) — `--arm layered_half --rope --easy-only 0.5`
- **mode:** process
- **prediction:** interesting if probe held beats job-zero by ≥0.02 — half the corpus, the "useless" half by doctrine, winning would invert the lab's data doctrine and re-read failweight and the dream family.
- **kill test:** retire if probe held ≥ job-zero + 0.02 (outside the flat band on the wrong side): easy evidence is as empty as doctrine says, one probe, done.
- **status:** queued

### WC-004 · Minority readout: ship the LEAST common state of the last 5 checkpoints
- **source:** wild-card reasoning — a careful person filters this because majority/mode readout is "obviously" the right summary and the minority is by definition the states training rejected. They might be wrong: on contested weights the modal state is the one the lattice kept leaving; the minority state is disproportionately the most recent direction of travel. If the checkpoint sequence has momentum, the tail state — not the consensus — is the prediction.
- **mechanism:** save ternary states every N steps as the modal-readout entries already do; at readout, per weight ship the least frequent of the last 5 checkpoint states (ties → the most recent). Eval-side only; the same run also reports its modal readout, so the probe measures the readout delta directly.
- **train.py:** new eval-side flag `--minority-readout 5` on Layered — `--arm layered_half --rope --minority-readout 5`
- **mode:** process
- **prediction:** interesting if minority readout is within 0.01 of modal readout on the same run (consensus was never the active ingredient), and a sensation if it beats modal by >0.01.
- **kill test:** retire if minority readout is ≥0.05 worse than the modal readout measured on the identical run — one eval pass on checkpoints that already exist; the cheapest kill in this file.
- **status:** queued

### WC-005 · Cross-layer vote transplant: each layer votes on its neighbour's gradients
- **source:** wild-card reasoning — a careful person filters this because a weight voting on another layer's gradient signs is a category error. They might be wrong: gradient sign fields across adjacent blocks of the same width are correlated through the residual stream; if transplanted votes train nearly as well, the vote mechanism's value is mostly "any consistent sign pressure," not per-weight evidence — which would demote a shelf of per-weight machinery in the pool.
- **mechanism:** in `Layered.step`, cyclically permute the per-layer gradient tensors before the gate/vote computation: block 1's weights accumulate votes from block 2's gradient signs and vice versa (shapes match at half chassis: both blocks dim 192). Counters, gate, V, and flip rules unchanged; AdamW parts get their true gradients.
- **train.py:** new flag `--vote-xplant` on Layered — `--arm layered_half --rope --vote-xplant`
- **mode:** process
- **prediction:** interesting if probe held is within +0.05 of job-zero — locality of evidence, assumed by every vote entry ever filed, would be falsified at probe cost.
- **kill test:** retire if probe held ≥ job-zero + 0.15: per-weight evidence is as load-bearing as assumed, and the transplant number becomes the locality bound in the record.
- **status:** queued

### WC-006 · Counter diffusion: evidence leaks sideways into neighbouring weights
- **source:** wild-card reasoning — a careful person filters this because counters are per-weight by definition and blurring them "destroys the accounting." They might be wrong: weights in the same row share an input and their true gradient signs are spatially correlated; the pool's leak family only ever decays counters in TIME. A small spatial diffusion is a denoiser matched to the noise structure — each counter borrows its neighbours' evidence the way an image filter borrows pixels.
- **mechanism:** after each step, each counter moves 10% toward the mean of its four nearest neighbours' counters within the same matrix row/column grid (fixed-point, clamp ±V preserved). No change to votes, gate, or flip rule.
- **train.py:** new flag `--counter-diffuse 0.1` on Layered — `--arm layered_half --rope --counter-diffuse 0.1`
- **mode:** process
- **prediction:** interesting if probe held beats job-zero by ≥0.02, especially with a lower flip count (same loss on fewer, surer flips = the denoising story confirmed in the run's own logs).
- **kill test:** retire if probe held ≥ job-zero + 0.02, OR if total flips fall by >50% vs job-zero at flat-or-worse loss (diffusion only smeared the evidence into inaction).
- **status:** queued

### WC-007 · Scalar-feedback votes: no per-weight gradients in the vote path at all
- **source:** wild-card reasoning — a careful person filters this because replacing per-weight gradients with one global bit of feedback ("loss went down / up") throws away nearly all the information in training. They might be wrong: the counter is an integrator, and integrators exist to extract signal from exactly this kind of impoverished stream; 884k weights × thousands of steps is a lot of coin flips for a bandit to learn from.
- **mechanism:** each step, compute the batch loss delta vs the previous batch. Every weight whose counter is non-zero receives a vote in its counter's current direction if loss fell, against it if loss rose (rich-get-richer bandit reinforcement); zero counters receive a random ±1 vote. Gate and magnitudes are not used — the vote path never sees a gradient. AdamW parts train normally on true gradients.
- **train.py:** new flag `--bandit-votes` on Layered — `--arm layered_half --rope --bandit-votes`
- **mode:** process
- **prediction:** interesting if probe held beats the WC-001 reservoir control by ≥0.05 — structure learning from a single bit per step would be a genuinely new fact about this trainer family.
- **kill test:** retire if probe held is within 0.02 of WC-001's frozen-reservoir probe (bandit votes indistinguishable from not training the weights), or ≥ job-zero + 0.20 outright if WC-001 has not run yet.
- **status:** queued

### WC-008 · Reversed-text first half: learn language backwards, then turn around
- **source:** wild-card reasoning — a careful person filters this because language modelling is causal and reversed windows are "garbage data." They might be wrong: the ternary lattice's early phase — the phase the closed anneal arm proved is decisive — may mostly be learning local token statistics, which are nearly direction-symmetric at short range; a reversed first half could pre-build that structure without burning forward-pass evidence on init noise, and rotary's geometry does not care which way the text runs.
- **mechanism:** for the first 50% of steps, every training window is reversed (token order flipped; the model predicts the previous token). At 50% the stream flips to normal forward windows for the remainder. Objective, chassis, and budget unchanged; total steps matched to control.
- **train.py:** new flag `--reverse-first 0.5` (sampler transform) — `--arm layered_half --rope --reverse-first 0.5`
- **mode:** process
- **prediction:** interesting if probe held beats job-zero by ≥0.02 — the reversed phase acted as free pre-structure rather than poison — or if the loss at the 50% flip point recovers to the control's same-step loss within 10 steps (no lasting damage from half a run of "garbage").
- **kill test:** retire if probe held ≥ job-zero + 0.05: backwards pre-training is a real cost the second half cannot repay at any horizon this lab can afford.
- **status:** queued

### WC-009 · Batch 1: one window, one testimony, no averaging anywhere
- **source:** wild-card reasoning — a careful person filters this because batch 1 is "obviously" too noisy and the pooled batch grid stops at 16. They might be wrong: batch-32 pre-averaging destroys exactly the per-example sign disagreement that a counter exists to integrate over time. Averaging first and integrating second is doing the counter's job badly, upstream, with the wrong statistic (mean instead of accumulated sign evidence).
- **mechanism:** batch size 1 for the whole run; every step is one window's unmediated vote. Steps per probe rise sharply (charged honestly: judged per minute like every arm, and the step count is logged).
- **train.py:** no new flag — `--arm layered_half --rope --batch 1` (existing `--batch` in both parsers)
- **mode:** sweep
- **prediction:** interesting if probe held beats job-zero by ≥0.02 at equal minutes — the counter was the right integrator all along and batching was the noise source, not the cure.
- **kill test:** retire if probe held ≥ job-zero + 0.05, OR if flip share exceeds 5× job-zero's (the lattice is thrashing, not integrating — the noise story wins).
- **status:** queued

### WC-010 · The 70% zero cull: impose the sparsity, don't persuade it
- **source:** wild-card reasoning — a careful person filters this because randomly zeroing trained weights every 10 steps is vandalism, and the pool's only sparsity lever is a gentle 1.5× vote nudge toward zero (A-009). They might be wrong: the lab's own record says the ~42% zero fraction is load-bearing feature selection — but that fraction is an emergent accident. If zero-ness is doing real work, forcing it to 70% should either win outright or show exactly where the accident was already optimal.
- **mechanism:** every 10 steps, randomly select currently-nonzero weights and set them to 0 (counters zeroed) until the installed zero fraction is exactly 70%. Between culls, training is untouched champion. The cull is uniform-random — no magnitude ranking — so any win is attributable to the fraction itself, not to pruning skill.
- **train.py:** new flag `--zero-cull 0.7 --cull-every 10` on Layered — `--arm layered_half --rope --zero-cull 0.7 --cull-every 10`
- **mode:** process
- **prediction:** interesting if probe held is within +0.02 of job-zero at 70% zeros — the serving model could then ship far sparser at no cost — and a win (>0.02 better) would indict the natural 42% as under-sparse.
- **kill test:** retire if probe held ≥ job-zero + 0.08: the emergent fraction was near its optimum and imposed sparsity is just damage, priced in one probe.
- **status:** queued

### WC-011 · Backwards rotary: positions run in reverse while the text runs forward
- **source:** wild-card reasoning — a careful person filters this because RoPE's angles encode true position order and negating them "breaks the position signal." They might be wrong: rotary's measured win (−0.0411) was never split into "a consistent relative-position code" vs "the CORRECT code." A sign-flipped rotation is an equally consistent code with reversed geometry — if it also wins, the lab has been crediting position understanding for what is really a conditioning/regularisation effect.
- **mechanism:** negate all RoPE rotation angles (equivalently, rotate by position −t instead of t) for both Q and K; data order, chassis, and everything else unchanged.
- **train.py:** new flag `--rope-neg` in Block (angle sign flip; requires `--rope`) — `--arm layered_half --rope --rope-neg`
- **mode:** process
- **prediction:** interesting if probe held is within +0.02 of job-zero (backwards positions ≈ forwards positions: the win is code-consistency, not order) — a result that re-reads the ROPE results file and the whole partial/NoPE family.
- **kill test:** retire if probe held ≥ the no-rope control (MILL-1114) probe + 0.02: reversed geometry is worse than no geometry, order really is the content, question closed in one probe.
- **status:** queued

### WC-012 · All-+1 init: start from the worst possible histogram
- **source:** wild-card reasoning — a careful person filters this because initialising every ternary weight to +1 (no zeros, no −1s) is a sabotaged start no sane run would use, and the pool's init entries go the other way (match the trained histogram, A-114). They might be wrong: if the vote mechanism is a real attractor, the init histogram should be nearly irrelevant by mid-run, and proving that on the most hostile init available is the strongest robustness evidence the mechanism could own — plus any init-dependence found here bounds every seed-variance argument in the record.
- **mechanism:** all t1 states init to +1, all t2 states to 0 (installed value uniformly +1×scale per weight); counters at 0; everything else champion. The counters must carve the entire {-1,0,+1} structure out of a constant field.
- **train.py:** new flag `--init allpos` in the model builder — `--arm layered_half --rope --init allpos`
- **mode:** process
- **prediction:** interesting if probe held is within +0.05 of job-zero — the mechanism recovers from a maximally wrong start inside 75 seconds, and init engineering (two pooled entries) drops in value accordingly.
- **kill test:** retire if probe held ≥ job-zero + 0.15: init is a first-order variable even for votes, the hostile-init number stands as its priced bound, and A-113/A-114 gain priority instead.
- **status:** queued
