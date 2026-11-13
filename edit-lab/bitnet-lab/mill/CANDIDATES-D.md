# CANDIDATES-D — dream/replay candidates for the BitNet vote trainer (Muse's work, Muse's side)

<!-- Muse's work — Muse's side of the BitNet lab. Produced 2026-11-12 by the dreaming
department (coordinator + 4 specialists) under Arnav's mass-testing directive. This is a
CANDIDATE file: nothing here is in the pool until the pool's owner merges it. IDEA-POOL.md
was read and NOT edited. train.py was read in full and NOT edited. -->

## Why this family exists

The BitNet vote trainer has never had a dream mechanism. The factory specialists have one,
and it was a clear WIN (waking dream: sealed composed 0.4444 → 0.8333). Arnav's doctrine:
"data problems' biggest fix is dreaming." This file specs the transposition of that mechanism
onto the vote trainer, grounded in what `train.py` actually exposes — not in generic
replay/dreaming lore.

**Grounding facts (verified against train.py, 389 lines):**
- Chassis for every entry: the champion — `layered_half` + `--rope`, V=32, batch 32, CTX 256,
  judged on the standard 128 held windows against champion 2.8580 ± 0.0161.
- `Layered.step()` reads `self.votes` **every step** and uses it for both the counter clamp
  (±V) and the flip threshold — a runner can change V mid-run with a plain assignment.
- Counters `c1`/`c2` are readable int8 tensors; `step()` returns flip share (chassis full-run
  mean ≈ 0.0011–0.0012 in `runs.jsonl`). A flip resets only the flipped component's counter.
- `offsets()` excludes held windows by construction (the `(i // CTX) % 40` predicate) — a
  replay buffer built from `offsets()` draws can only contain non-held windows.
- The AdamW group is exactly {non-BitLinear params + `log_scale`}; vote flips are computed
  outside `opt.step()`, so freezing either side independently is a clean runner-level patch.
- train.py has NO checkpoint/resume, NO per-example loss tracking, NO generation helper.
  Every dream mechanism therefore ships as a **companion runner `run_dream.py`** importing
  `Tiny, Layered, offsets, held_windows, held_loss` from train.py. All flags below are new
  flags on that runner; train.py itself is untouched.
- Closed forever, not re-opened by any entry: `--carry` (overshoot), `--cooldown`, threshold
  anneal 8→64, magnitude votes as specified, the JEPA objective. Every dream below trains on
  real corpus windows (or, D-002 only, model-generated windows) against the true next-token
  loss — no self-referential objective anywhere.

**Common protocol for all D-entries:** total trainer steps and total tokens are matched to
the control in every arm — dream phases *replace* fresh steps, never add on top. The runner
may call `held_loss()` at phase boundaries as a logged diagnostic only; phase decisions
never use held data. The full evaluation law (equal budgets, factorial controls, probe
adaptation, contamination checks, verdict stamp) is the final section of this file and
governs every entry.

---

### D-001 · Mistake replay (dream the errors, then re-sit them)
- **mechanism:** Phase 1 (first 70% of steps) trains exactly as champion, except the runner computes the loss with `reduction="none"`, reshaped per window — the bookkeeping rides the same forward pass that produces the scalar loss for `trainer.step()`, so it costs no extra forward. Each drawn window's offset is recorded in a dict `offset → max per-window loss seen`. At the phase boundary the runner takes the top-K = 512 distinct offsets, **drops the top 8** as presumed corrupt/noise, and that is the mistake buffer. Phase 2 (final 30% of steps): every batch is 24 fresh windows from `offsets()` + 8 replay windows sampled **uniformly** over the buffer (uniform, not loss-weighted — selection already encodes difficulty; weighting would double-count it and amplify outliers). Each buffer window may be replayed at most 4 times, then it is evicted. Counters during replay: nothing special — normal V=32, normal gate, AdamW parts train normally throughout.
- **flag-level change:** new runner flags `--dream replay --buffer-k 512 --phase1-frac 0.70 --replay-per-batch 8 --replay-cap 4 --trim-top 8` on `run_dream.py`; recorded arm label `layered_half_rope_dream-replay`.
- **why it might win:** the factory precedent — the waking dream was a clear WIN (0.4444 → 0.8333), and the doctrine is that data problems' biggest fix is dreaming. Uniform sampling spends the whole run on the average window; the model's residual loss is concentrated in windows it demonstrably gets wrong *in its current state* (the buffer is scored online by this run's model, not pre-scored by an init model as in static failweight sampling). Replay gives those windows the repeated exposure a vote counter — which needs ~32 net strong votes to move a weight — is structurally built to exploit: one pass over a hard window casts one vote; re-sitting it is how its evidence ever accumulates.
- **cost:** full trial only. Probe adaptation note: a 75s smoke run with a compressed 60/40 phase split and K=256 is useful as a plumbing/sign check, but a flat smoke reading does **not** kill this entry — at 75s the buffer reflects the near-init model's mistakes, not the trained model's, and the replay share is too small for the effect the trial measures.
- **kill criterion:** retire if the 3-seed × 8-min trial mean held ≥ 2.8480 (fails to beat champion by even 0.01), **or** if in ≥2 of 3 seeds the buffer windows' replay loss falls ≥20% across phase 2 while held loss is flat or worse — the memorisation signature: the buffer was noise, not signal.

### D-002 · Self-generated practice text, filtered by vote dynamics
- **mechanism:** Train on real text to 50% of steps. Then the runner generates a candidate pool: seed prompts are the first 64 tokens of non-held windows drawn via `offsets()`; continuations of 193 tokens are sampled autoregressively from `Tiny.next_piece()`, temperature 1.0, top-k 50, batched 32 sequences at a time, giving windows in exactly the training shape. Each candidate span is scored by a **dry run, batch=1**: forward/backward on that span alone, replicate the `Layered.step` vote computation per layer, and simulate the flips against a *snapshot* of the current `t1/t2/c1/c2` (including t1-priority and the boundary no-op rule) **without mutating the trainer**. One filter variant per arm — never stacked, so the result is attributable:
  - **D-002a · Flip-share band (primary):** keep the span iff its predicted flip share lies in [0.5×, 2×] the median flip share of the trailing 100 real batches. Too low = the span teaches nothing unsettled; too high = alien enough to destabilise the lattice.
  - **D-002b · Counter agreement:** keep the span iff, over weights with a non-zero counter, the fraction of strong votes agreeing with the existing counter's sign lies in [0.55, 0.85]. Below 0.5 the model's own text would mostly *undo* its accumulated evidence; above 0.9 it is pure redundancy.
  - **D-002c · Strong-mass concentration:** per layer, the share of total |g| mass carried by the strong half, averaged over layers; keep the span iff within ±25% of the same statistic's median over 16 real batches. (The strong *fraction* is tautologically ~50% under a median gate, so the filter uses mass concentration, which is not.)
  Every variant also applies a guard band that is *not* the filter: candidate mean CE must lie in [1.8, 4.5] (reject the mastered and the incoherent). Filtering continues until 256 spans are accepted or 2,048 candidates are exhausted. From 50% to 85% of steps, batches are 28 real + 4 synthetic; the final 15% is real text only, so the run always finishes on the true distribution. Synthetic steps are ordinary steps at normal V=32 — vote dynamics act as the *selection* criterion, never as a target.
- **flag-level change:** new runner flags `--dream synth --synth-filter flipband|agree|strongmass --gen-at 0.50 --synth-per-batch 4 --synth-until 0.85 --pool 256 --cand-budget 2048 --temp 1.0 --topk 50` on `run_dream.py` (generation loop and dry-run vote simulator are new runner code).
- **why it might win:** the only dream entry that creates new training *material* aimed at the model's own frontier: spans the current model half-believes, whose gradients push in directions its counters already lean toward, are precisely the spans a vote trainer can convert into flips with the least wasted evidence. It differs from the closed JEPA experiment in kind, not degree: JEPA changed the *objective* to a self-referential representation loss and lost badly; here the objective is untouched next-token CE, targets are tokens (not the model's own hidden states), and self-reference enters only through *which data is selected* — the same limited role dreaming plays in the factory win.
- **cost:** full trial only, honestly charged: generation (2,048-candidate budget) plus per-span batch=1 dry runs are paid out of the same 8-minute wall clock as training, so the arm trains on fewer real steps than the control — that handicap is part of the measurement. A 75s probe is uninformative.
- **kill criterion:** two pre-trial gates, either of which retires it without spending a trial: (1) filter acceptance rate <5% or >80% (the filter is not discriminating); (2) in a smoke run, held loss immediately before vs. after a 100-step synthetic-heavy segment worsens by ≥0.05. At trial: retire if the 3-seed mean held ≥ 2.8480, or if accepted-pool statistics drift across seeds toward the guard-band edges (echo-chamber signature). The head-on risk stands in the record: at held ≈2.86 the model's samples are poor text; if the filter cannot find a usable frontier band in them, gate (1) is expected to fire and this entry should die cheap.

### D-003 · Consolidation pass (low-V finish on hard windows)
- **mechanism:** Main phase (first 90% of steps) is champion training at V=32, with the D-001 buffer collected in parallel (same per-window bookkeeping, K=512, top 8 trimmed). For the final 10% of steps the runner sets `trainer.votes = 8` — `Layered.step` reads `self.votes` every step, so this takes effect immediately — and batches become 24 hard-buffer windows + 8 fresh windows. Everything else is unchanged: median strong gate, t1-priority single-flip rule, flipped counter resets to 0. **AdamW parts keep training at the unchanged lr 1e-3** — embeddings, norms and per-layer `log_scale`s must be free to re-fit the installed weights as consolidation flips land (`install()` rescales by `log_scale`; frozen scales would leave the model calibrated to a structure it no longer has). This is not the closed cooldown, which was an lr *schedule*; no schedule is applied here. One coupled effect is specified, not hidden: in `Layered.step` the same V clamps the counters and sets the flip threshold, so lowering V truncates every counter to ±8 on the first consolidation step, and every weight whose banked counter satisfies |c| ≥ 8 with a non-no-op direction flips on that step. That first step is a deliberate **bank-resolution step**: its direction per weight is the sign of evidence accumulated over the whole main phase, and the runner logs the pre-phase counter histogram and that step's flip share separately as the "resolution wave." Subsequent consolidation steps are true V=8 learning.
- **flag-level change:** new runner flags `--dream consolidate --buffer-k 512 --consol-frac 0.10 --consol-votes 8 --consol-hard-per-batch 24` on `run_dream.py` (the entire change is the runner assigning `trainer.votes = 8` at the phase boundary and changing batch composition).
- **why it might win:** at any moment in a V=32 run, a large mass of counters sits at |c| ∈ [8, 32) — real, accumulated, majority-signed evidence that has not resolved and, on the run's remaining horizon, mostly never will; those weights finish the run governed by stale early structure while their evidence sits inert. A short low-V pass lets that evidence act, and it acts *where it matters*: V cannot be scoped per-example inside a step (votes come from the batch-aggregated gradient), so hard-window targeting is done by batch composition — a 24/32 hard majority means the gradients resolving the bank are dominated by the examples the model is worst on. V=8, not lower: a quarter of 32, still demanding 8 net strong votes from a reset state (one noisy batch cannot flip a weight), and the [8, 32) band is where the unresolved mass is thickest. This is not the closed 8→64 anneal: that schedule *started* at 8 from step 0 with no bank, on all data, and raised V across the whole run; consolidation holds V=32 for 90% of the run and lowers it only at the end, only briefly, and only on hard windows — the bank's existence is the mechanism.
- **cost:** full trial only. Probe adaptation note: a 75s smoke run (V=8 for its final 10%) is a valid *danger* check — the kill signatures below can fire there — but a flat smoke reading does not kill, because the bank mass in [8, 32) that this mechanism spends grows with run length and is thinnest exactly at probe horizon (see the reconciled probe table in the evaluation protocol).
- **kill criterion:** retire if the 3-seed trial mean held ≥ 2.8480; **or** if the consolidation segment itself is net-negative (mean held at the phase boundary vs. at the end worsens by >0.02 across seeds); **or** if the resolution-wave flip share exceeds 10% of weights and held has not recovered to its phase-boundary value by the end in ≥2 of 3 seeds (the wave was a shock, not a resolution). The stated interaction risk is why the guards exist: at V=8 noise flips weights far more easily than at V=32, and the only things standing between that noise and the structure are the short phase, the V=8 floor, and the hard-window majority in every batch.


### D-004 · Counter-pressure mining (dream the windows that resolve stuck evidence)
- **mechanism:** At dream onset (60% of step budget), snapshot `c1`/`c2`. Draw a candidate pool of 8 batches via `offsets()` and score each with ONE forward/backward and NO step, replicating the vote rule read-only (vote = −sign(g), gated at per-layer median |g|). Score per batch = Σ over weights with 16 ≤ |c| < 32 in either counter of 𝟙[vote = sign(c)]·(|c|/32) − 0.5·𝟙[vote = −sign(c)]·(|c|/32), normalised by the batch's near-threshold mass. Dream 12 steps cycling the top-2 scoring batches, V = 32 unchanged, AdamW live. This selects windows by what they do to the trainer's *unresolved evidence*, not by loss: a window can be low-loss and still be the one that pushes 5% of the network across a flip threshold, and a high-loss window (D-001's pick) can mostly push counters at |c| ≈ 0 that will never resolve in 12 steps.
- **flag-level change:** companion runner only — `dream.py --dream counter-pressure --dream-at 0.6 --pool-batches 8 --keep-batches 2 --dream-steps 12`; runner logs near-threshold mass (|c| ∈ [16,32) share of all counters) and dream-phase flip share. No `train.py` change.
- **why it might win:** a flip is the only discrete unit of learning this trainer has, and the chassis's flip rate is ~0.11%/step — dream steps are too scarce to spend on windows chosen by a proxy (loss) when the actual bottleneck variable, the counter distribution, is directly observable for free. Tie-breaking stuck evidence is also the one selection rule no STE trainer can imitate, so a win here is evidence *for* the vote mechanism itself, not just for more training.
- **cost:** cheap probe (the 8 scoring passes are charged inside the standard 75s probe — roughly 8 step-equivalents of overhead, stated honestly); trial = 3 seeds × 8 min, adoption >2sd and >0.01 over 2.8580. Note the evaluation protocol classifies D-004 full-trial-only for *adoption* purposes (counter pressure barely exists at probe scale); the probe may still be run as a plumbing check.
- **kill criterion:** kill if the probe held Δ vs job zero is < 0.02, OR if the dream-phase flip share is < 1.5× the preceding 50 normal steps' mean flip share — if it does not even move the mechanism it claims to move, it does not earn a trial regardless of the loss reading.

### D-005 · Flip-share-triggered repetition dream (dream exactly when the mechanism goes quiet)
- **mechanism:** No phase schedule. The runner tracks the rolling mean of `step()`'s returned flip share over the last 50 steps; when it falls below 0.0008 (≈30% under the chassis's measured full-run mean of 0.0011–0.0012), at least 100 steps have elapsed, and at least 100 steps have passed since the last dream, a dream fires: draw 2 fresh batches via `offsets()` and repeat each 6 times consecutively (12 dream steps), V = 32, AdamW live, max 6 dreams per run. Repetition is the active ingredient: in the normal stream each window is seen once, so a weight whose evidence is real but contested accumulates +1/−1 votes from unrelated windows and nets to zero below threshold; six consecutive identical votes move its counter up to 6 steps with no interleaved cancellation.
- **flag-level change:** companion runner only — `dream.py --dream flip-trigger --trigger-window 50 --trigger-floor 0.0008 --trigger-set 2 --trigger-reps 6 --trigger-max 6`; runner logs every trigger (step, rolling flip share, dream flip share). No `train.py` change.
- **why it might win:** D-001/D-003 dream on a clock, but the chassis does not stall on a clock — it stalls when the easy flips are exhausted, which is exactly what flip share measures and nothing else in the run does. Triggering there concentrates the scarcest resource (repeated, uncontested evidence) at the moment marginal normal steps are returning the least, and the trigger is self-calibrating across seeds and scales where a fixed phase point is not.
- **cost:** cheap probe = standard 75s probe; trial = 3 seeds × 8 min, adoption >2sd and >0.01 over 2.8580. (Protocol note: trigger behaviour at probe scale is the startup transient; trial judgement is what counts — see the protocol's probe table.)
- **kill criterion:** kill if the trigger never fires in the probe (floor is fiction, not a stall detector), if it hits the 6-dream cap in the probe (a disguised fixed schedule, not a trigger), or if probe held Δ vs job zero is < 0.02.

### D-006 · Frozen-AdamW dream (pure ternary consolidation, nothing continuous moves)
- **mechanism:** Two dream phases (at 50% and 80% of steps, 15 steps each) on fresh uniform windows via `offsets()`, V = 32, selection deliberately neutral — the ONLY change is that during dream steps the runner patches `trainer.opt.step` to a no-op and restores it after, so embeddings, norms, and `log_scale` are bit-frozen and only `t1`/`t2` flips move. Built-in inverse control in the same runner: the ternary-frozen dream (runner snapshots `t1`/`t2`/`c1`/`c2` before the phase and restores them after, so votes cannot move and only AdamW trains) at identical step counts, so the pair attributes any effect to the vote side, the continuous side, or neither.
- **flag-level change:** companion runner only — `dream.py --dream frozen-votes --dream-at 0.5,0.8 --dream-steps 15` and `--dream frozen-ternary` for the inverse control; runner calls `held_loss` immediately before and after each dream (logged diagnostic only, per protocol §4) and logs the delta. No `train.py` change.
- **why it might win:** in every normal step, a vote flip is instantly followed by `install()` rescaling and an AdamW move of the embeddings, norms, and per-layer scales — the frame the votes voted in shifts under the flip, and `log_scale` in particular can absorb a flip's effect by shrinking. A frozen frame lets the ternary structure settle against fixed continuous parameters, the closest analogue this chassis has to what "consolidation" means in the factory precedent. It is also the control the whole dream family is missing: D-001–D-005 and D-007 all dream with AdamW live, so any win they show is ambiguous between vote consolidation and ordinary continuous drift until this entry prices the two apart.
- **cost:** cheap probe = standard 75s probe, zero extra compute (a dream step costs exactly a normal step); trial = 3 seeds × 8 min × 2 arms (candidate + inverse control), adoption >2sd and >0.01 over 2.8580.
- **kill criterion:** kill if probe held Δ vs job zero is < 0.02, OR if held loss measured immediately after either dream is worse than immediately before it in the probe — consolidation that hurts on contact is not consolidating, and a later recovery would be the normal stream's doing, not the dream's.

### D-007 · Interleaved micro-dreams (placement is the claim, content held fixed)
- **mechanism:** The runner keeps a ring buffer of only the last 25 steps' batches (offsets + the loss recorded when each was first seen — no rescoring, no run-long memory). Every 25 normal steps it runs a 5-step micro-dream replaying the highest-loss batches from that short window only, then clears the buffer; total dream steps ≈ 1/6 of the run, V = 32, AdamW live. The same runner carries the placement control `--dream-place end`, which applies the identical selection rule and identical total dream-step count as one end-phase from a run-long buffer. Content, dose, and rule are held fixed between the two arms; the only variable is *when* the dream steps sit. This is deliberately not D-001: D-001's claim is its global top-loss buffer replayed between phases; D-007's buffer horizon is 25 steps, its selection is incidental, and its claim survives only if placement itself pays.
- **flag-level change:** companion runner only — `dream.py --dream micro --dream-every 25 --dream-steps 5 --buffer 25 --dream-place interleaved|end`. No `train.py` change.
- **why it might win:** the factory's waking dream — the precedent win — was woven into the loop, not appended to it, and the doctrine was earned in that woven form. Mechanistically: an end-phase dream's flips are never tested — the run ends before normal steps can counter-vote a bad flip — while a micro-dream's flips face the next 25 normal steps as an immediate audit, and replay happens while those windows' gradients are still aligned with the current AdamW state instead of a drifted one.
- **cost:** cheap probe = standard 75s probe (interleaved arm); trial = 3 seeds × 8 min × 2 arms (interleaved vs its own end-placement control), adoption >2sd and >0.01 over 2.8580.
- **kill criterion:** kill if probe held Δ vs job zero is < 0.02, OR if at trial the interleaved arm does not beat its own end-placement control by > 0.01 — if placement does not pay, any gain belongs to replay itself, which is D-001's claim, and D-007 is dead even if the numbers look good.

---

## Evaluation protocol — dream candidates

<!-- Muse's work — Muse's side of the BitNet lab. Applies to D-001..D-007, all run as
companion runners importing train.py. Where this section and PROMOTE.md disagree for a
dream entry, this section wins: it is PROMOTE.md plus the controls the half-size retraction
(RESULTS-HALF-CONTROL-2026-11-12) proved necessary. A dream phase spends steps, so a naive
dream-vs-baseline comparison measures "more training", not "dreaming".

Coordinator reconciliations applied when merging the department's three design documents
(marked [R1]..[R3] inline): [R1] dream dose follows each candidate's own spec rather than
one universal 25% split — what is fixed is total steps, and every control is dose-matched;
[R2] the D-006 factorial is written with the freeze direction as D-006 itself specifies it
(candidate = AdamW frozen, votes live; the ternary-frozen arm is its inverse control);
[R3] D-003's probe row follows its own kill criteria — danger signatures kill at probe
scale, flatness does not, because the counter bank it spends is thinnest at probe horizon. -->

### 1. The equal-budget law

- **Judged on steps, never on minutes.** Dream trials are step-boxed (`--steps`), with `--minutes` demoted to a safety cap only. Time-boxing a dream arm silently cuts its steps by exactly its scoring / generation / mining overhead — the half-control confound in reverse.
- **Fixed total budget.** Trial: `S_total = 160` steps (the champion's 8-min band is 150–170) for EVERY arm — candidate, CONTROL-D, and every factorial cell. [R1] The wake/dream split inside those 160 steps is part of each candidate's own spec (D-001: 30% dream; D-003: 10%; D-006: 2×15 steps; D-007: ~1/6 interleaved; D-005: triggered, yoked per §2) — and every control for that candidate uses the *same* split and the *same* dream-step positions/count, spent on its control content. Safety cap `--minutes 12`; a seed that hits the cap before 160 steps is **void and re-run**, never compared partial.
- **Tokens-seen.** `T = S_total × 32 × 256 = S_total × 8,192` (batch × CTX), identical in every arm. Three counting rules, no exceptions:
  - *Replayed windows count in full, every time.* A replay step is 8,192 tokens-seen of re-exposure. Unique tokens `U` is logged separately and never substituted for `T` — "re-exposure beats fresh breadth at equal `T`" is the hypothesis being tested, not a discount to be granted.
  - *Self-generated text counts 1:1 when stepped on*, same as corpus text. Generated-but-discarded tokens do not count in `T`; they are logged as `gen_tokens_discarded` with the kept:generated ratio, and their compute is charged under wall-clock below.
  - *Scoring / mining / filtering passes count 0 steps and 0 tokens* — they are not training — but they are never free: see wall-clock.
- **Wall-clock.** `wall_s` runs from before any buffer build, scoring, mining, or generation to the final held eval, and `overhead_s` (all non-stepping compute) is logged as a separate field inside it. Nothing dream-related may be precomputed before `t0`. Step-matched is the primary verdict; if a dream arm's `wall_s` exceeds its paired control's by >1.5×, the verdict stamp carries a `COST` flag — a win at >1.5× wall is a per-minute loss and is reported as one.
- **The step-matched control (CONTROL-D) — mandatory, per candidate, per seed.** Champion chassis (layered_half + rope, V=32, no freeze, no threshold change) run to the *same* `S_total`, with the dream-phase steps spent on ordinary random windows drawn by `offsets()`. Every dream number is judged first against its own paired CONTROL-D, second against the champion. **Adoption requires both:** mean < 2.8258 (the standing PROMOTE bar vs 2.8580 ± 0.0161) **and** mean beats paired CONTROL-D mean by >0.01 with ≥2 of 3 seeds paired-better. Beating the champion reference but not CONTROL-D is the half-control pattern — the champion reference is time-boxed at variable steps (154/170/168) — and is a reject, stamped `STEPS-ARTEFACT`.
- **Seed discipline.** Seeds 0, 1, 2 only; all three, always. Same seed ⇒ same init (`torch.manual_seed(seed)`) and identical wake history: dream onset is at a fixed *step*, never a wall second, and any randomness inside dream machinery uses its own stream (`random.Random(10_000 + seed)`), never the wake stream, so buffer construction cannot shift later draws. Dream fraction, buffer size, thresholds, and trigger values are fixed before seed 0's held loss is seen; changing any of them re-runs all seeds and all factorial cells. No dropped seeds, no rescue seeds, no best-seed reporting — per-seed held, mean ± sd, and the paired sign pattern are all in the record.

### 2. Factorial controls for fused mechanisms

A candidate with two moving parts may not be judged as one arm. The candidate cell must beat **both** single-factor cells by >0.01, or the claim is renamed to whichever single factor earned it.

**D-003 consolidation = targeting × threshold — full 2×2, all cells at equal `S_total`:**

| | V=32 | V=8 |
|---|---|---|
| random windows | CONTROL-D | threshold-only |
| hard windows | targeting-only | **candidate** |

- Trial: **all 4 cells mandatory**, 3 seeds each (12 runs). No adoption, and no "consolidation" claim, from the candidate cell alone. Candidate ≈ threshold-only ⇒ it is a V=8 arm; candidate ≈ targeting-only ⇒ it is a hard-window arm; either renames the entry and closes the fused claim.
- Probe: may run **candidate vs CONTROL-D only** (skips both single-factor cells). A probe promote queues the full 2×2 trial; the ledger line is stamped `FACTORIAL-INCOMPLETE`.
- (The dream-proto prototype already implements exactly these four cells as `--control {none,threshold,target,full}` — see DREAM-PROTOTYPE.md.)

**D-005 triggered dreaming = trigger × phase content — 2×2, yoked:**

- Cells: triggered × dream (candidate), triggered × ordinary windows, fixed-schedule × dream, fixed × ordinary (= CONTROL-D, not re-run). Trial: the two off-diagonal cells are **mandatory**; probe may skip fixed × dream.
- Yoking rule: the fixed-schedule cell fires the *same number of dream episodes and dream steps* as the triggered cell recorded for that seed, at pre-set steps. An unyoked fixed cell compares different dream doses and is invalid.

**D-006 frozen-parts dream = freeze-side × content — [R2] as D-006 specifies it:**

- The candidate freezes the **AdamW side** (embeddings, norms, `log_scale` bit-frozen; only `t1`/`t2` flips move). Its built-in inverse control freezes the **ternary side** (states + counters snapshotted and restored; only AdamW trains). Cells: AdamW-frozen × neutral windows (candidate), AdamW-frozen × replay, ternary-frozen × neutral (inverse control), live × random (= CONTROL-D). Trial: candidate, inverse control, and CONTROL-D mandatory; AdamW-frozen × replay may be shared with D-001's frozen follow-up if run under identical budget/seed. A candidate win that the inverse control reproduces is an AdamW effect wearing a vote costume — the claim renames accordingly.

**D-002 self-generated text = source × filter — 2×2, brief:** self-gen × filtered (candidate), self-gen × unfiltered, real windows × same filter, real × unfiltered (= CONTROL-D). Trial: all 4 mandatory if the claim mentions filtering; probe may skip both off-diagonal cells.

D-001 (mistake replay), D-004 (counter-pressure mining), D-007 (interleaved micro-dreams) each move one part against CONTROL-D and need no factorial — their control is §1's. (D-007 additionally owes its own end-placement control, which is written into its entry.)

### 3. Probe adaptation — can 75 seconds read a dream effect at all?

Standard probes stay as in PROMOTE.md (75 s, seed 0), with one change: **dream probes are step-boxed to job zero.** Job zero is measured first, time-boxed, as usual; its step count `S0` (≈25 at the champion's rate — measure it, never assume it) becomes the budget. Dream probe and its CONTROL-D probe both run `--steps S0`, dream occupying the **final 25%** (`S_dream = round(0.25 × S0)` ≈ 6 steps, onset at step `S0 − S_dream`) unless the candidate's spec fixes a different probe form. Promotion bar unchanged: Δ = CONTROL-D held − dream held ≥ 0.05 promotes. A time-boxed dream probe is invalid — its step count is whatever its overhead left over.

| class | candidate | verdict | why / what a flat probe means |
|---|---|---|---|
| replay | D-001 | **Probeable — weak screen** | Re-exposure acts immediately, but the buffer is ranked from ~19 wake steps of one-pass losses: noisy. Δ ≥ 0.05 promotes; Δ < 0.05 is `INCONCLUSIVE`, not a kill (propose as a PROMOTE.md exception). |
| generation | D-002 | **Full-trial-only** | At ~25 steps the generator is near-untrained — its text is not the text the mechanism is designed around — and generation + filtering overhead breaks the 75 s budget outright. No probe is run; a flat probe would measure the startup model, not the candidate. |
| consolidation | D-003 | **Probeable — danger check only** [R3] | The V=8 segment can fire its kill signatures (net-negative segment, unrecovered resolution wave) at any scale, so the probe is a valid safety screen. But the bank mass in [8, 32) grows with run length and is thinnest at probe horizon, so a flat probe is `INCONCLUSIVE`, not a kill; Δ ≥ 0.05 still promotes. |
| counter-state | D-004 | **Full-trial-only** | The miner reads counter pressure that does not exist at probe scale: after ~19 wake steps few counters sit anywhere near V=32, so the mined set is a startup artifact. Needs the full wake to have a distribution worth mining. |
| triggered | D-005 | **Full-trial-only** | Flip-share in the first ~25 steps is the startup transient; the trigger fires on the transient or not at all, never in its designed steady-state regime (~100+ steps). A probe would grade the trigger's first seconds, not the trigger. (Its entry's probe-based kill lines apply to trigger *behaviour* — never fires / caps out — not to held Δ.) |
| frozen-parts | D-006 | **Probeable — screen only** | The AdamW parts move at lr 1e-3, fast enough for 6 frozen dream steps to show a direction vs CONTROL-D. But a probe runs candidate-vs-control only, so it can promote and can never attribute: no freeze claim from a probe, and Δ < 0.05 is `INCONCLUSIVE`, not a kill. |
| interleaved | D-007 | **Full-trial-only** | The mechanism *is* the whole-run alternation; the tail-25% probe form cannot represent it, and at `S0` ≈ 25 steps rounding leaves 1–2 micro-dreams. Interleaving needs the full 160-step schedule to exist. |

Full-trial-only candidates enter by a human's word, are ledgered `probe: skipped (full-trial-only)`, and are judged solely by the §1 trial bar. Probeable candidates that promote still owe the full factorial of §2 at trial.

### 4. Contamination and honesty checks

Every dream record (probe, trial, every factorial cell, CONTROL-D) is invalid unless all of these are logged and pass:

- **Held exclusion, asserted — not inherited.** Held windows are safe from `offsets()` draws by construction, but a replay buffer is a new code path and inherits nothing. At buffer build *and* at dream draw, the runner asserts `held_overlap = 0`: no buffer offset `i` with `(i // CTX) % 40 == 0` or `((i + CTX) // CTX) % 40 == 0` — the `offsets()` predicate applied to the buffer itself. Buffer offsets are used verbatim; any shift/jitter/augmentation of a stored offset voids the assertion and must be re-checked after the transform. Log `buffer_size` and `held_overlap` per run.
- **Self-generated text: training prompts only.** Prompts are drawn via `offsets()` from training windows, full stop — never from held windows, never scored, filtered, or selected against held windows or held loss. The filter may use only training-window loss / model likelihood / trainer state. Log `prompt_source = offsets`, `prompt_overlap = 0` (same predicate), and the generation seed (derived from the run seed).
- **No held-informed anything.** Hard-window scoring, mining scores, trigger values, and thresholds are computed from training windows and training state only. `held_loss` is called at init and final, and MAY be called at phase boundaries **strictly for logging** (D-003's resolution-wave record, D-006's contact check, the prototype's phase readout) — a boundary value may never feed back into the run: any mid-run held value used to time a trigger, pick a checkpoint, size a buffer, choose a phase length, or stop early invalidates the run. Kill criteria that read boundary held values are applied *post-hoc, across completed runs*, never inside one.
- **Flip-storm visibility.** Log `state_hist` (`{-2..+2}` shares) and `mean_flip_share` split by phase (`_wake`, `_dream`), plus `steps`, `tokens_seen`, `unique_tokens`, `wall_s`, `overhead_s`. Flag `FLIP-STORM` if dream-phase flip share > 3× the same run's wake share **and** the final zero-share in `state_hist` moves >5 points vs CONTROL-D: such a "win" is priced as churn, not consolidation, until a factorial cell shows otherwise. (The V=8 cells are *expected* to flip hot — the flag compares D-003's candidate against its own random × V=8 cell, not against V=32.)
- **Noise-chasing signature — the suspicion rule.** On hard-window-heavy arms (D-001, D-003 hard cells, D-004): train loss down, held flat or up — formally, `train_last100` ≥ 0.05 below CONTROL-D while Δheld ≤ 0.01 — means the arm is memorising its rehearsed windows, not learning. Stamp `NOISE-CHASE SUSPECT`; it cannot promote or adopt on that trial regardless of any single seed. Same verdict, any arm, for the layered_half pattern: a seed-0-only win whose sign flips on seeds 1–2. To clear the stamp, the runner logs train loss on *fresh* (never-replayed) windows separately from dream-window train loss — a real effect lowers both.

### 5. Verdict stamp

One line per dream trial, stamped verbatim in the ledger / CANDIDATES-D entry:

```
D-00X <name>: dream <mean>±<sd> vs CONTROL-D <mean>±<sd> (Δ <±0.0000>, <k>/3 seeds paired-better) vs champion 2.8580±0.0161 — <ADOPT|REJECT|INCONCLUSIVE> — steps <S>/<S> equal · tokens <T>/<T> equal · wall <s>s (+<overhead>s overhead) · held_overlap 0 · flip_share wake/dream <x>/<y> · factorial <interaction|main-effect: <factor>|incomplete|n/a> <flags: STEPS-ARTEFACT|FLIP-STORM|NOISE-CHASE|COST, if any>
```

---

## Coordinator's ranking and merge notes (Muse's side, dreaming department)

The department's two design specialists disagreed productively; the coordinator's synthesis:

- **Strongest overall: D-003 (consolidation).** It is the only variant whose mechanism is
  *native* to the vote trainer: the bank of unresolved counter evidence in [8, 32) is a real,
  measurable object in the trainer's own state — not an analogy imported from FP training —
  and the lever that spends it (`trainer.votes`, read every step) already exists. It also has
  the sharpest kill criteria of the family, written around its own segment, so it can fail
  cheaply and informatively. **This is the variant prototyped** (see DREAM-PROTOTYPE.md),
  with D-006 folded in as the prototype's freeze axis rather than built separately.
- **Safest, prototype next: D-001 (mistake replay).** Closest relative of the one proven dream
  win in this house (the factory's), bounded downside (fresh-window majority, repeat cap,
  top-8 trim). It shares its entire buffer machinery with D-003 — the prototype runner's
  buffer is D-001's buffer — so it costs almost nothing to run second.
- **The control the family cannot skip: D-006 (frozen-AdamW).** The novel-variants specialist
  argued it should be prototyped *first*, because every other variant dreams with AdamW live
  and therefore cannot attribute a win to vote consolidation vs continuous drift. The
  coordinator's resolution: D-006 is not a separate first build — it is a `--freeze` axis on
  the D-003 prototype (already implemented and helper-tested), so the attribution question is
  priced inside the first smoke instead of after it.
- **Highest ceiling among the novel four: D-004 (counter-pressure mining)** — the only
  selection rule no STE trainer can imitate; if it wins, it is evidence for the vote mechanism
  itself. Full-trial-only by the protocol (counter pressure barely exists at probe scale).
- **Highest risk: D-002 (self-generated text).** Genuinely novel and the only entry creating
  new material, but it pays generation out of its own training budget, starts from poor
  samples at held ≈2.86, and lives next door to the JEPA failure mode. Its pre-trial gates
  exist so it dies cheap if it dies.
- D-005 and D-007 are schedule claims (trigger, placement) rather than content claims; both
  are honestly specified with yoked/placement controls, and both are full-trial-only.

*End of CANDIDATES-D. Companion document: `../DREAM-PROTOTYPE.md`; prototype code:
`../dream-proto/`.*
