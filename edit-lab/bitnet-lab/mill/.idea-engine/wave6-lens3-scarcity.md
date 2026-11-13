# Muse's work — Muse's side

# Wave 6 · Lens 3 — SCARCITY: sample efficiency per token (Idea Engine, rotation 6, miner 3)

<!-- Muse's work — Muse's side of the BitNet lab. Fable's side read-only, untouched. -->

Filed 2026-11-12. Premise (DATA-AUDIT.md): the lab is data-scarce — ~0.91M unique real
pieces in v1, 458,752 pieces/run (56 steps × 32 batch × ctx 256), 0.14 pieces/param at the
2M rung vs the ~20 pieces/param rule of thumb. When tokens are the scarce resource, the
objective is **held-loss gain per token at an equal-token control** — never per minute
(the throughput lens owns per-minute), never per step at a different token count.

**Accounting rules for every entry below.**
1. Control = champion (layered_half + rotary, held 2.8580 ± 0.0161 full format) run at the
   SAME number of training pieces (458,752 at ladder/probe-equivalent budget). Any extra
   forward/backward the mechanism spends is charged as tokens: a mechanism that re-reads a
   batch pays for the re-read in the comparison, or the entry says explicitly why the
   re-read is free (cached tensors, no new forward/backward).
2. Correlation is priced, not hidden: extractions drawn from the same gradient are NOT
   independent samples, and no entry claims √K gains from K correlated reads.
3. Dedupe, checked against IDEA-POOL.md, CANDIDATES-A/B/C/D/E/F/G/H/I/J and
   FABLE-CANDIDATES.md: the D-wave owns replay/dreaming of old windows (D-001..D-007) —
   no entry here replays data. A-013 owns loss-weighted token votes; A-041..A-056 own
   curricula/sampling ordered by loss level, Δloss, coverage and source; G-013..G-024 own
   data construction (packing, stream walk, overlap lattice, epoch deck, ctx mixture);
   F-002/F-011/F-017/F-018 own gate-quantile, dither and quorum variants of WHICH votes
   count; MILL-123/124 own MTP and MILL-113..115 own KD (denser targets per token — taken,
   not re-filed). What remains, and what this file owns, is the **efficiency accounting of
   the vote extraction itself**: how much usable signal one backward pass, one token
   position, and one batch actually yield, and what is currently thrown away.

---

## ★ Top 3

### SC-001 ★ · Multi-threshold shadow counters — one gradient, three vote extractions (V = 8 / 32 / 128)
- **source:** vote-trainer structure + DATA-AUDIT scarcity premise. The champion commits
  every weight to a single flip threshold V=32. A gradient read at V=8 extracts fast,
  noisy flips; at V=128, slow, high-confidence flips. Today two of those three reads are
  computed (the signed vote exists) and then discarded by the single-threshold choice.
- **mechanism:** Each step's signed vote feeds THREE independent int8 shadow counters per
  weight, at thresholds 8, 32 and 128. Only one counter set is *live* (its flips change
  the weights); the other two run as shadows — they flip a shadow ternary state that is
  never installed. Every 200 steps, each layer's live threshold is re-chosen as the shadow
  whose shadow-state, scored on a fixed 8-window dev micro-batch (already in memory, no
  training tokens spent), has the lowest loss. No extra forward/backward on training data:
  the vote is extracted three ways from the one gradient already computed.
- **exact change:** new flag `--shadow-v 8,32,128 --shadow-eval 200` on Layered in
  train.py: triple counter arrays (state cost +2 B/weight, reported, not hidden), shadow
  flip bookkeeping, periodic per-layer threshold selection on the dev micro-batch.
- **mode:** process — isolated train.py subprocess (code-path change)
- **prediction (per token):** **−0.02..−0.05 held loss vs the equal-token champion control**
  (same 458,752 pieces, same steps). Honest correlation price: the three extractions share
  one sign stream, so this is NOT three independent runs' worth of evidence — the
  effective extra information is the *threshold-selection* signal only, worth roughly one
  free hyperparameter search over V per layer, which is why the claim is −0.02..−0.05 and
  not the −0.08+ a naive "3× the reads" story would suggest. Distinct from F-022
  (Benna–Fusi cascade: fast counter *drives* a slow one, serial transfer) — here the
  counters are parallel, independent, and selection is by measured dev loss; distinct
  from MILL-207/208 (one adaptive V targeting a flip rate — here V is discrete-chosen by
  loss, not servoed by flip count).
- **status:** queued

### SC-002 ★ · Gradient-alignment curriculum — order fresh windows by transfer value, not by loss
- **source:** scarcity premise + the gap in A-041..A-056: every pooled curriculum orders
  or samples by a property of the window ITSELF (its init loss, its Δloss, its coverage).
  None measures what a scarce-token regime actually needs: what training on this window
  does to the REST of the distribution.
- **mechanism:** Maintain a fixed probe gradient g_probe = mean gradient over 16 held-out
  (never-trained) windows, refreshed every 200 steps from the current weights (one extra
  backward per 200 steps = 0.5% token overhead, charged below). Each candidate fresh
  window is scored once, forward+backward on its first appearance, by
  value = cos(g_window, g_probe). Windows are then trained in descending value order
  within each 512-window block. A window whose gradient points where the probe gradient
  points teaches generalisable signal; a window with high loss but orthogonal gradient
  teaches only itself — in a 0.91M-piece corpus, the second kind is the waste.
- **exact change:** new flag `--align-curriculum 512` in the sampler: probe-gradient
  computation, per-window cosine scoring at first sight, block-local descending sort.
  Fresh windows only — no window is ever re-trained by this entry (replay is D-wave
  territory, deliberately excluded).
- **mode:** process — isolated train.py subprocess (code-path change)
- **prediction (per token):** **−0.03..−0.08 held loss vs the equal-token control**
  (random-order champion, same 458,752 pieces, control credited with the same 0.5%
  probe overhead as extra training tokens). The wide range is honest: alignment scoring
  is one backward per window that the control spends on a second training pass instead,
  so the net claim already nets out that cost; the effect should be largest exactly
  because the corpus is small and heterogeneous (German sentences vs project prose vs
  residual boilerplate want very different things from the weights).
- **status:** queued

### SC-003 ★ · Entropy-selected loss positions — spend the vote budget where the model is actually uncertain
- **source:** DATA-AUDIT §2: median line is 9 pieces in v1 (36 in v2); a 256-piece window
  is mostly collage, and a large share of its positions are near-deterministic (spaces —
  token 222 alone is 10.2% of all pieces — boilerplate continuations, separator runs).
  The champion extracts votes from all 256 positions equally, so most of each batch's
  vote mass is spent confirming what is already known.
- **mechanism:** Per window, run the forward pass as usual; compute per-position entropy
  of the predictive distribution; the loss (and therefore every vote and every FP-part
  gradient) is taken over only the top-50% entropy positions of that window. The other
  positions still serve as context — they are simply not paid for as targets. This is
  credit-assignment sharpening at the position level: the same tokens, half the target
  positions, all of the vote mass concentrated on positions carrying information.
- **exact change:** new flag `--loss-topk-entropy 0.5` in train.py: per-position entropy
  from the existing logits (no extra forward), top-k mask applied to the CE before
  backward. Positions are selected per window, per step, from the current model — not
  from a static list.
- **mode:** process — isolated train.py subprocess (code-path change)
- **prediction (per token):** **−0.01..−0.04 held loss vs the equal-token champion control**
  (same windows, same pieces seen as context; control takes loss on all positions).
  Priced honestly: halving target positions halves the gradient's token count in the
  statistical sense, so part of the concentration gain is paid back in gradient variance —
  the claim survives only if the discarded positions were really near-zero-information,
  which the audit's token distribution says they mostly are. Distinct from A-052
  (span-noise *input* masking, objective unchanged) and A-049 (frequency-based loss
  downweighting — a static token property; entropy here is the model's own live
  uncertainty at that position, so a rare-but-predictable position is also skipped).
- **status:** queued

---

## Remaining entries

### SC-004 · Second-read voting — re-vote the same gradient after the flips it caused have landed
- **source:** vote mechanics: a step's votes are computed against the pre-flip weights.
  When a batch of flips fires, the loss surface changes, and part of the gradient's
  signal was "spent" pushing weights that have now moved — the residual signal in that
  same gradient (its push on the weights that did NOT flip, re-read against the new
  state and the layered gate) is currently discarded and the batch is never seen again.
- **mechanism:** After each step's flips are installed, re-apply the SAME cached signed
  vote vector once, through the gate, against the new ternary state, into the counters
  only (no flip check on the second read — counters accumulate, flips wait for the next
  real gradient). No new forward, no new backward, no data replay: the tokens are not
  re-seen, only their already-paid-for gradient is read a second time against the state
  it changed.
- **exact change:** new flag `--second-read` on Layered: cache the step's signed vote
  tensor, one extra gate+counter pass post-flip per step.
- **mode:** process — isolated train.py subprocess (code-path change)
- **prediction (per token):** **−0.005..−0.02 held loss vs the equal-token champion
  control.** Correlation priced at its harshest: the second read is ~fully correlated
  with the first, so the claim is only the small state-dependence term — if the gate's
  state-dependence is weak at this scale this reads ~0, and that null is itself the
  measurement of how state-dependent the vote extraction really is. Distinct from
  D-wave replay (no data is re-presented, no extra forward) and from A-003
  (batch-aggregated votes change WHEN votes fire; this changes how many times one
  gradient is read).
- **status:** queued

### SC-005 · Per-token vote-mass normalisation — every position gets an equal say in total
- **source:** gradient anatomy: a position's contribution to a weight's gradient scales
  with its activation and error magnitude, so a few loud positions (number streams,
  boilerplate with large errors) can dominate a batch's entire vote while quiet,
  informative positions are outvoted. A-040 clips the GLOBAL gradient norm before
  signing — one budget for the whole batch. Nothing gives each token position its own
  budget.
- **mechanism:** Before signing, rescale each position's per-token gradient contribution
  so that every position contributes equal total L1 vote mass across weights
  (per-position normalisation of the token-gradient outer products, applied in the
  backward hook where per-token gradients are still separable — first and last layers
  exactly, middle layers via the standard per-token activation×delta factorisation).
  Loud positions keep their direction; they lose their volume advantage.
- **exact change:** new flag `--vote-mass-norm` in train.py's vote extraction path.
- **mode:** process — isolated train.py subprocess (code-path change)
- **prediction (per token):** **−0.01..−0.03 held loss vs the equal-token champion
  control**, concentrated in the v1 corpus where numeric/boilerplate positions are
  loudest; expected smaller on v2. Distinct from A-013 (weights votes by the token's
  LOSS level — loud tokens get MORE say there; here every token gets the SAME total
  say, direction only) and from A-049 (frequency downweighting — a corpus statistic,
  not a per-batch mass budget).
- **status:** queued

### SC-006 · Gradient-diversity batch composition — assemble batches whose windows disagree usefully
- **source:** batch statistics: 32 randomly drawn windows from a collage corpus often
  carry near-duplicate gradient content (the audit: 93.2% of lines belong to a duplicated
  group), so a random batch's effective information is well under 32 windows' worth.
  A-053 diversifies by SOURCE FILE; file diversity is a proxy — two files can teach the
  same thing, one file can teach two.
- **mechanism:** Keep a cheap gradient sketch per candidate window: the sign vector of
  its last-layer gradient from its most recent scoring pass (256-dim projection, stored
  int8). Assemble each batch greedily: start from a random window, then repeatedly add
  the candidate whose sketch has the lowest mean cosine similarity to those already in
  the batch, from a candidate pool of 128. Batch size, token count and step count are
  unchanged — only WHICH windows share a batch changes.
- **exact change:** new flag `--diverse-batch 128` in the sampler: sketch store,
  greedy min-similarity assembly per step.
- **mode:** process — isolated train.py subprocess (code-path change)
- **prediction (per token):** **−0.01..−0.03 held loss vs the equal-token champion
  control** (random batches, same pieces per run in expectation — the sampler draws
  without replacement within each pass so total token exposure matches). Honest cost:
  sketches are one step stale, so the diversity is approximate; the claim is sized for
  approximate, not oracle, decorrelation.
- **status:** queued

### SC-007 · Rare-token-density window upsampling — pay more visits to the windows that carry the tail
- **source:** DATA-AUDIT §2: 1,984 of 3,548 used tokens appear <100 times in the whole
  corpus. Under uniform sampling those tokens' embeddings and head rows receive almost
  no gradient, while token 222 (space, 10.2%) is trained to exhaustion. The information
  per token of a window scales with how much of the tail it carries.
- **mechanism:** Score each window once by rare-token density = fraction of its pieces
  whose corpus frequency is <100. Sampling probability ∝ (1 + 2 × density), normalised,
  drawn with replacement caps so no window exceeds 3 visits per pass. Loss and votes are
  untouched — this is purely which windows the token budget is spent on.
- **exact change:** new flag `--rare-upsample 2.0` in the sampler, using corpus
  frequency counts computed at load.
- **mode:** process — isolated train.py subprocess (code-path change)
- **prediction (per token):** **−0.01..−0.03 held loss vs the equal-token champion
  control** (uniform sampling, same total pieces trained). Nearest neighbour A-049
  downweights frequent tokens INSIDE the loss; this upsamples tail-carrying WINDOWS
  in the sampler and leaves the loss alone — the two compose, and either can win alone.
  Risk priced in: over-visiting tail windows can overfit their specific contexts; the
  3-visit cap is the guard, and the low end of the range assumes it binds.
- **status:** queued

### SC-008 · Probe-aligned per-layer vote scaling — layers that teach the probe get louder votes
- **source:** credit assignment across depth: all layers receive votes at the same
  threshold economics (MILL-207 varies V by flip RATE — a layer-local statistic). No
  entry scales a layer's vote increments by whether that layer's gradient agrees with
  the direction the whole model needs to move.
- **mechanism:** Using SC-002's probe gradient (or a standalone 16-window probe,
  refreshed every 200 steps, 0.5% overhead charged), compute per-layer alignment
  a_l = cos(g_l, g_probe,l). Scale layer l's vote increments by (1 + a_l), clipped to
  [0.5, 1.5]. Layers pushing with the generalisable gradient accumulate evidence
  faster; layers pushing against it must prove themselves over more tokens.
- **exact change:** new flag `--probe-vote-scale` on Layered: per-layer alignment
  computation at refresh, increment multiplier in the vote step. Usable without
  SC-002 (own probe), additive with it (shared probe, overhead counted once).
- **mode:** process — isolated train.py subprocess (code-path change)
- **prediction (per token):** **−0.005..−0.025 held loss vs the equal-token champion
  control** credited with the probe overhead as training tokens. Expected to be the
  smaller sibling of SC-002: it reweights evidence instead of choosing data, so its
  ceiling is lower and its variance is lower too.
- **status:** queued

### SC-009 · In-batch n-gram loss deduplication — a repeated span inside one batch teaches once
- **source:** DATA-AUDIT §4: duplication is usually handled BETWEEN windows (A-047
  removes near-duplicate windows; G-015 moats the held set). But within a single batch
  of 32 collage windows, the same boilerplate 8-grams recur across windows, and each
  recurrence casts its own votes — the batch pays full price repeatedly for one piece
  of information.
- **mechanism:** Within each assembled batch, hash every 8-gram of target pieces; for
  any 8-gram occurring in more than one window of the batch, keep the loss (and votes)
  only at its first occurrence's positions and mask the later occurrences' positions
  out of the loss. Context is untouched; only duplicate target positions stop voting.
- **exact change:** new flag `--batch-dedup-ngram 8` in train.py: per-batch 8-gram
  hash pass over the target tensor, position mask merged with the CE mask.
- **mode:** process — isolated train.py subprocess (code-path change)
- **prediction (per token):** **−0.005..−0.02 held loss vs the equal-token champion
  control** on v1 (where in-batch duplication is rampant); expected ~0 on v2, and the
  entry should be run on v1 first precisely because that contrast prices how much of
  v1's token budget is intra-batch waste. Distinct from SC-003 (entropy selects by
  model uncertainty; this removes by exact content repetition, model-free).
- **status:** queued

### SC-010 · Ultra-frequent-target vote muting — positions predicting space cast no votes
- **source:** DATA-AUDIT §2: the top targets (space 10.2%, BOS, newline) are learned
  almost immediately and thereafter generate large volumes of near-zero-information
  votes that still move counters — noise with a voting franchise. A-049 downweights
  frequent tokens in the LOSS for all parameters; the FP parts (embeddings, norms,
  scales) may still want that loss. The ternary side is where the waste is.
- **mechanism:** For target positions whose gold token is in the corpus top-5 by
  frequency, the position contributes to the FP-part loss as usual but its gradient
  is excluded from the VOTE extraction (ternary counters see nothing from it). One
  mask, applied only at the vote step.
- **exact change:** new flag `--vote-mute-topk 5` on Layered/Direct trainers: target-
  frequency mask in the vote path only.
- **mode:** process — isolated train.py subprocess (code-path change)
- **prediction (per token):** **−0.005..−0.02 held loss vs the equal-token champion
  control.** Small, cheap, and honestly bounded: it can only recover the counter-noise
  those positions inject, and if the champion's counters are not in fact polluted by
  them this reads 0 — a clean diagnostic either way.
- **status:** queued

### SC-011 · Equal-token batch ramp — batch 16 early, 64 late, same total pieces
- **source:** step economics: at fixed tokens, batch size trades steps against gradient
  noise. Early training wants many steps (structure finding); late training wants
  low-noise gradients (fine convergence). MILL-1201..1203 and C-B05/B06 measure FIXED
  batch sizes; no entry spends the same tokens as a RAMP.
- **mechanism:** Batch 16 for the first third of the token budget, 32 for the middle
  third, 64 for the final third. Total pieces identical to the control (458,752);
  step count differs by design (that IS the mechanism) and is reported, not hidden.
- **exact change:** new flag `--batch-ramp 16,32,64` in train.py's step loop.
- **mode:** process — isolated train.py subprocess (code-path change)
- **prediction (per token):** **−0.01..−0.03 held loss vs the equal-token champion
  control** (fixed batch 32, same pieces). This is the one entry whose gain, if any,
  is purely an allocation effect — same tokens, same model, same votes, different
  grouping — which makes it the cleanest test in the file of whether grouping alone
  carries information value.
- **status:** queued

### SC-012 · Anti-correlated window pairing — cancel the batch's common-mode gradient
- **source:** F-009 subtracts the layer's MEAN VOTE (common-mode rejection inside the
  counter). The data-side analogue is unclaimed: if a batch's windows share a strong
  common gradient component (same boilerplate, same source dialect), that component is
  counted 32 times while the windows' individual signals are counted once.
- **mechanism:** Assemble each batch as 16 PAIRS: for each seed window, pair it with
  the candidate window (from a 128-pool, using SC-006-style last-layer gradient
  sketches) whose sketch is most NEGATIVELY correlated with the seed's. Paired windows
  are trained in the same step, so their shared common-mode components cancel in the
  batch-mean gradient while their opposed, window-specific components survive signing
  with relatively more weight.
- **exact change:** new flag `--anticorr-pairs 128` in the sampler: sketch store
  (shared implementation with SC-006 if both land), pair assembly per step. Batch
  size and token count unchanged.
- **mode:** process — isolated train.py subprocess (code-path change)
- **prediction (per token):** **−0.005..−0.02 held loss vs the equal-token champion
  control.** Deliberately the most conservative claim in the file: cancellation also
  removes genuinely shared signal (the language's common structure IS partly
  common-mode), so the net could be ~0; the pairing is the experiment that prices how
  much of the batch gradient is corpus dialect versus transferable structure.
- **status:** queued

---

## Honest summary

- **Count:** 12 entries (SC-001..SC-012), all `process` mode, all judged per token
  against the same equal-token champion control (458,752 pieces).
- **Largest per-token gain I can defend:** **≈ −0.05 held loss** — the top of SC-001's
  range, with SC-002's −0.08 upper end explicitly NOT defended as a point claim (its
  alignment-scoring cost and corpus heterogeneity make the wide range the honest
  statement; its defensible centre is ≈ −0.04). No entry claims √K scaling from
  correlated reads: SC-001's three extractions share one gradient and are priced as a
  per-layer threshold search, SC-004's second read is priced as a near-null diagnostic
  with a small positive tail.
- **What this lens deliberately did not file:** replay/dreaming variants (D-wave),
  loss-ordered curricula and coverage sampling (A-041..A-056), packing/overlap/deck
  constructions (G-wave), MTP/KD dense-target schemes (MILL-113..124), and any
  per-minute claim (throughput lens). If SC-002 and SC-006/SC-012 both land, their
  sketch/probe infrastructure is shared and the second one's overhead should be
  re-ledgered at the shared cost, not the standalone cost.
