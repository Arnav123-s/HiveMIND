# WAVE3-LENS3 — Auxiliary signals (Muse's work — Muse's side)

Muse's work — Muse's side of the BitNet lab. Rotation-3 miner 3, AUXILIARY SIGNALS lens,
Idea Engine wave 3, 2026-11-12. This is a CANDIDATE file: nothing here is in the pool until
the pool's owner merges it. IDEA-POOL.md, CANDIDATES-A/B/C/D/E/F/G and FABLE-CANDIDATES.md
were read in full for dedupe and NOT edited.

## Territory and hard boundary

Every entry SERVES the next-token CE objective: the main loss, its targets, and the yardstick
(held CE on the standard 128 windows) are unchanged in all 12 entries. An auxiliary signal
may add a gradient, a head, a regularizer, or a teacher — it may never replace CE.

**JEPA boundary, exact:** the JEPA objective is CLOSED (RESULTS-JEPA-2026-11-12: probe CE
3.2428 vs untrained floor 3.2445, paired mean −0.0017; control 2.8935; prediction loss fell
~4–5× with no collapse, and the representations still carried no linearly readable token
information). Nothing below trains toward a representation target, an EMA target encoder, a
masked-span representation, or any quantity the model itself defines in hidden space. Where
a teacher appears (AO-002/004/010) it is a frozen, CE-trained checkpoint of the champion
itself and its target is a **token distribution over the real vocabulary on real windows** —
the limited, token-space form A-104 already legitimised, never a hidden-state target.
**F-031 is not duplicated:** F-031 uses a JEPA trunk as INITIALIZER only; no entry here uses
a JEPA trunk, a JEPA checkpoint, or JEPA pretraining in any role.

**Champion / bars:** layered_half + rotary + plain votes, held **2.8580 ± 0.0161**, V=32,
batch 32, ctx 256, dim 192, 2 blocks, 884,736 ternary weights. Probe = 75 s / seed 0 vs job
zero; trial = 3 seeds × 8 min; adoption = trial mean < 2.8258 (>2 sd AND >0.01) unless an
entry states an equal-total-compute bar. **Compute honesty:** every entry states its extra
cost in its own text; teacher forwards, extra heads, and extra passes are charged against
the entry at equal minutes, and any entry that wins only at equal steps is reported as such.

**Dedupe, stated once:** pooled MTP is a *separate final-layer head predicting t+2*
(MILL-123/124, w 0.1/0.3) and A-103 is the *same final head predicting t+2* (w 0.05);
FP-teacher KD is MILL-113/114/115 (+ A-064), ensemble-into-one distillation is G-057/MC-009,
counter-inheritance from ensemble teachers is G-058/MC-010, the concurrent EMA mean-teacher
is A-104, dropout two-pass consistency is A-105, label smoothing / z-loss / loss-clip /
focal / attention-entropy are A-101/102/106/107/108, span-noise input masking under the
ordinary next-token targets is A-052, gradient whitening is MILL-232, per-layer median /
per-row / per-state gates are the champion gate / A-002 / F-005, fixed zero-bias votes are
A-009, measured delta-loss flip verification is MILL-231 (+ Fisher queue A-069). Each entry
names its nearest neighbour and the difference.

---

### AO-001 ★ · Deep supervision: block-1 same-token auxiliary head (t+1, not t+2)
- **source:** auxiliary-signals lens — deep supervision (intermediate-layer CE) transplanted to a 2-block vote trainer; nearest neighbours MILL-123/124 and A-103 both attach supervision at the FINAL layer for a FUTURE token (t+2).
- **mechanism:** Block 1's output (after block 1, before block 2) is read by the tied head and scored against the SAME next token (t+1) the main head predicts, loss weight 0.1, computed on every 4th position only. Block 1's ternary weights currently receive CE only after it has been filtered through block 2, the final norm, and block 2's own still-moving structure — the longest, noisiest gradient path in a 2-block net. A direct, short-path CE gives block 1's counters evidence about its own output quality, in the same token space and for the same target as the main objective. This is not MTP: horizon is t+1 (identical target), placement is intermediate, and the question is gradient-path length, not supervision density over future tokens.
- **train.py:** new flag `--deep-sup 0.1` — in `Tiny.body` optionally return the block-1 activation; in the training loop compute `F.cross_entropy((h1 @ tok.weight.T)[::4 positions], targets[::4])` and add `0.1 *` it to the loss before `trainer.step(loss, done)`. No new parameters (tied head reused); head discarded at serving (block-1 readout is training-only). **Cost charged:** one extra vocab matmul on 1/4 of positions ≈ +6–9% step time, stated in the record; judged at equal minutes.
- **mode:** process
- **prediction:** −0.02..−0.05 at trial scale; −0.01..−0.03 at probe (acts from step 0, no bank or horizon needed). Side diagnostic: block-1 flip share should rise and its counter-reversal rate fall vs champion — if held improves with neither moving, the gain is extra-head compute, not path shortening, and the entry is re-read as such.
- **kill test:** retire if probe held Δ vs job zero is > +0.02 (worse), or trial mean ≥ 2.8480, or trial mean wins at equal steps but loses at equal minutes (the head's matmul ate the gain).
- **status:** queued
```mill
id: AO-001
mode: process
run: --arm layered_half --rope --deep-sup 0.1
```

### AO-002 ★ · Checkpoint self-distillation: the 50% snapshot teaches the second half (token space)
- **source:** auxiliary-signals lens — teacher-free self-distillation from the model's own earlier checkpoint, as named in the lens territory; nearest neighbours A-104 (EMA teacher, updated EVERY step, decay 0.99, w 0.5), MILL-113 (separately trained FP teacher), G-057 (ensemble teacher). This teacher is none of those: one frozen snapshot of THIS run, taken once.
- **mechanism:** At 50% of steps the runner snapshots the full model + trainer state (ternary states, scales, FP parts) and freezes it as the teacher. For the remaining 50% of steps, each batch is also forwarded through the frozen snapshot (no gradient) and the loss becomes CE + 0.3 · KL(teacher ‖ student) at temperature 2 on the same windows, same ground-truth stream. The snapshot is a worse model than the student will become, but it is a STABLE one: its distribution is the student's own past consensus, so the KL term specifically penalises late-run churn — flips that move predictions away from what the first half had already settled — while CE keeps pulling toward the tokens. No representation target, no EMA, no external teacher; the snapshot's own training cost is zero (it is a by-product of the run's first half).
- **train.py:** new flag `--ckpt-distill 0.3` — runner snapshots `model.state_dict()` + `trainer.t1/t2/log_scale` at `done >= 0.5` into a frozen copy of `Tiny`; second-half loop adds the teacher forward (under `torch.no_grad()`, `EASE=1.0`) and the KL term before `trainer.step`. **Cost charged:** one extra forward (no backward) per second-half step ≈ +15–18% total wall; snapshot storage ~7 MB training-only, 0 B at serving. Judged at equal minutes.
- **mode:** process
- **prediction:** −0.02..−0.05 at trial scale. Reasoning: the champion's late flip share stays ~0.11%/step to the end, so a measurable share of late steps is spent re-deciding settled structure; an anchor priced in token space should convert some of that churn into consolidation — the output-space analogue of D-003's counter-bank argument, priced independently. Probe is a plumbing/danger check only (the teacher does not exist until 50%, so a 75 s probe's second half is ~12 steps of distillation — a flat probe does NOT kill).
- **kill test:** retire if the trial mean ≥ 2.8480; or if second-half held (logged at the 50% boundary and at the end, diagnostic only) improves LESS in the distill arm than in its paired step-matched control in ≥2 of 3 seeds; or if the KL term collapses to ~0 by 75% of the run (teacher and student identical — the snapshot was taken too late to differ, and the entry's premise is measured false).
- **status:** queued
```mill
id: AO-002
mode: process
run: --arm layered_half --rope --ckpt-distill 0.3
```

### AO-003 ★ · Self-normalised surprise gate: per-weight gradient shaping before the vote
- **source:** auxiliary-signals lens — gradient shaping (per-layer gradient transforms before the vote); nearest neighbours the champion's per-layer median gate (selects by |g| relative to the LAYER), A-002 per-row gate (relative to the ROW), F-005 state gate (relative to the installed STATE), MILL-232 whitening (second-moment rotation of the whole field). None normalises a weight's gradient by that weight's OWN history.
- **mechanism:** Each weight carries an EMA of its own |g| (β=0.95, fp32, 4 B/weight charged). The vote-path gradient is shaped per weight as `g_shaped = g / (ema|g| + eps)` and the strong/weak gate is taken on |g_shaped| at its per-layer median: a weight now votes when its gradient is unusually large FOR IT, not when it is large for the layer. Chronically small-gradient weights — systematically disenfranchised by every pooled gate, because the layer median is set by other weights — get a fair evidence channel; chronically large weights must exceed their own baseline. Sign is untouched (sign(g_shaped) = sign(g)); only gate admission changes. AdamW parts and the `log_scale` gradient keep the UNshaped gradient, so the shaping is vote-path only and its effect is attributable.
- **train.py:** new flag `--surprise-gate` on `Layered` (and `Direct`): per-layer EMA buffers updated inside `step()` from `m.weight.grad` before the `strong =` line; `strong` computed on the shaped magnitudes. One EMA buffer per BitLinear, no extra forward or backward.
- **mode:** process
- **prediction:** −0.01..−0.04 at probe and trial scale (acts from the first steps, like F-005). Diagnostic that must accompany any win: the share of weights that cast ≥1 vote in the run should rise vs champion (the disenfranchised population is the claimed mechanism); a held win with no rise in voter coverage is not this mechanism and is reported as an unexplained win, not a confirmation.
- **kill test:** retire if probe held Δ vs job zero > +0.02, or trial mean ≥ 2.8480, or voter-coverage rise is <2 points while held is flat (the shaping changed nothing it claims to change).
- **status:** queued
```mill
id: AO-003
mode: process
run: --arm layered_half --rope --surprise-gate
```

### AO-004 · Born-again vote model: a fresh run distilled from the champion run's final checkpoint
- **source:** auxiliary-signals lens — sequential self-distillation (born-again networks) applied to the vote trainer; distinct from MILL-113 (teacher is an FP twin), G-057 (teacher is an ensemble), AO-002 (teacher is a mid-run snapshot inside the same run). Here the teacher is the student's own COMPLETED previous generation, same architecture, same ternary format.
- **mechanism:** Generation 1 is an ordinary champion run. Generation 2 starts from the SAME seed init and fresh counters, trains on the same corpus with loss CE + 0.5 · KL(gen-1 final ‖ gen-2) at temperature 2, teacher frozen throughout. A vote trainer's final model encodes its structure in a discrete code whose training trajectory cannot be replayed; the KL term lets generation 2's counters integrate the first generation's settled output geometry as evidence from step 0, instead of re-deriving it from one-hot tokens alone.
- **train.py:** new flag `--born-again 0.5` + `--teacher-state <path>` — runner loads the recorded champion final state into a frozen `Tiny` copy; training loop identical in shape to AO-002's KL term but active from step 0. **Cost charged at equal TOTAL compute, stated as the bar:** gen-1 (8 min) + gen-2 (8 min) must beat a 16-minute champion control, not the 8-minute 2.8580 — a win against 2.8580 alone is a compute artefact and is stamped as such.
- **mode:** process — full trial only (two full runs per seed; a probe cannot price a generational effect)
- **prediction:** Gen-2 held −0.01..−0.04 vs the equal-total-compute 16-min control; larger vs the 8-min champion (expected, and not the claim). If born-again transfer works for votes at all, this is its cleanest form: teacher and student share init, format, and corpus, so only the distillation channel varies.
- **kill test:** retire if gen-2 fails to beat the 16-min control by >0.01 on the 3-seed mean, or if gen-2 ≈ a CE-only 8-min student trained identically without the teacher (the in-entry ablation — the KL channel carried nothing).
- **status:** queued
```mill
id: AO-004
mode: process
run: --arm layered_half --rope --born-again 0.5
```

### AO-005 · Conflict-projected auxiliary gradients in the vote path (PCGrad for votes)
- **source:** auxiliary-signals lens — gradient shaping for multi-signal training (PCGrad, Yu et al. 2020), translated to the vote path; no pooled entry projects one signal's gradient against another's anywhere in the trainer.
- **mechanism:** Carrier signal is the pooled MTP head (MILL-123, w 0.1, t+2). Per BitLinear layer, the loop computes the CE gradient g_ce and the MTP gradient g_aux separately. If their per-layer dot product is negative, g_aux is projected orthogonal to g_ce (`g_aux -= (g_aux·g_ce/|g_ce|²) g_ce`) before the two are summed for the VOTE path; the AdamW parts receive the plain unprojected sum. The auxiliary signal may therefore add evidence in any direction except the one that directly fights the main objective that step, and the shaping is applied only where the lab's claim lives — the discrete structure. Whether MTP helps votes at all is MILL-123's question; whether a conflict-free MTP helps MORE is this one, and the entry is only interpretable alongside MILL-123's reading.
- **train.py:** new flags `--mtp 0.1 --pcgrad-vote` — training loop does two backwards on retained graph (or two half-forwards) to obtain per-layer g_ce / g_aux for the BitLinear weights, projects per layer, writes the summed projected gradient into `m.weight.grad` before `Layered.step`'s vote block; FP-part gradients restored from the unprojected sum (runner-level gradient surgery, no change to `step()`'s vote rule itself). **Cost charged:** ≈ +60–80% step time (second backward); judged at equal minutes AND equal steps, both reported.
- **mode:** process — full trial only (depends on MILL-123's flag landing and its single reading first)
- **prediction:** Conditional: if MILL-123 reads flat or slightly negative, projection recovers −0.01..−0.03 of that flatness (the harm was conflict, not the signal); if MILL-123 already wins cleanly, projection adds ~0 and this entry retires on its own condition. Per-layer conflict rate (fraction of layers with negative dot per step) is logged — if it is <5% of layer-steps, there was no conflict to shape and the entry is void, not failed.
- **kill test:** retire if the conflict rate is <5% (void), or if the projected arm fails to beat the unprojected MILL-123 arm by >0.01 at equal steps at trial, or loses to it at equal minutes by >0.02.
- **status:** queued
```mill
id: AO-005
mode: process
run: --arm layered_half --rope --mtp 0.1 --pcgrad-vote
```

### AO-006 · Flip-consistency KL anchor: predictions may not churn for free when structure flips
- **source:** auxiliary-signals lens — flip-consistency penalties, expressed in output space; distinct from A-105 (consistency between two DROPOUT passes of the same weights), AO-002 (anchor is a 50%-of-run snapshot, always on in phase 2), and every counter-side anti-thrash entry (A-008/F-016/A-019 act on counters and thresholds, never on predictions).
- **mechanism:** Whenever a step's flip share exceeds 0.2% (≈2× the champion mean 0.0011), the NEXT step carries an extra term: the batch is forwarded once under the pre-flip installed weights (snapshot taken before that flip step's `install()`) and the loss gains 0.2 · KL(pre-flip ‖ current) on the next step's windows. Ordinary low-flip steps carry no penalty and pay no extra forward. The penalty prices prediction churn at the moment it happens: a flip burst that genuinely improves fit can pay the small KL and move on (CE dominates at w 0.2); a burst that merely rearranges predictions pays and earns nothing, and its gradient — flowing into both the vote path and the FP parts on the following step — pushes the structure back toward predictive continuity.
- **train.py:** new flag `--flip-anchor 0.2` — runner keeps the previous step's installed weight tensors (the `m.weight` copies `install()` writes, ~3.5 MB); on a trigger step it computes the anchor forward under `no_grad` for the teacher side on the next batch and adds the KL term before `trainer.step`. **Cost charged:** one extra forward only on steps following a >0.2% flip step (logged trigger rate; expected <20% of steps, ≈ +5–7% total wall).
- **mode:** process
- **prediction:** −0.01..−0.03 at trial scale, concentrated in variance: seed sd should shrink vs 0.0161 even at a flat mean, because the penalised events are the high-churn steps where seeds diverge. A flat mean with halved sd still promotes (it sharpens every other probe in the mill, cf. G-003's stated logic).
- **kill test:** retire if the trigger rate is <2% of steps (void — flip bursts that large do not occur and there is nothing to anchor), or trial mean ≥ 2.8480 with no sd improvement, or the anchor KL stays >0.05 to the end of the run (the penalty is fighting CE permanently, not taxing bursts).
- **status:** queued
```mill
id: AO-006
mode: process
run: --arm layered_half --rope --flip-anchor 0.2
```

### AO-007 · Masked-token CE head: predict the actual masked tokens (ground-truth targets, no representations)
- **source:** auxiliary-signals lens — auxiliary prediction heads; the BERT/MLM signal re-expressed under this lab's hard boundary. Explicitly NOT JEPA: the target is the ground-truth token ID scored by ordinary cross-entropy through the tied head — no predictor MLP, no EMA target encoder, no representation matching, no stop-gradient target network. The JEPA record's failure was a representation target carrying no token information; this entry's target IS token information, by construction.
- **mechanism:** Each training window has 32 scattered positions (12.5%, never the first or last 8) replaced in the INPUT by the learned mask embedding (the one piece of plumbing `run_jepa.py` already proved on this chassis). The main next-token CE runs unchanged on all positions. An auxiliary CE, weight 0.1, scores the model's prediction OF the masked token AT each masked position (same tied head, position's own hidden state). The trunk must therefore carry token-identity information at positions where the input gave it nothing — in-context inference of a missing word — a signal the left-to-right objective never asks for directly, since next-token CE always sees the true previous tokens.
- **train.py:** new flags `--mask-aux 0.1 --mask-n 32` — `Tiny` gains a mask embedding vector (192 params); batch builder masks input ids at 32 seeded positions per window (targets and main CE untouched); loop adds `0.1 * CE(head(h[masked]), true_ids[masked])`. **Cost charged:** negligible compute (positions already forwarded); the input corruption itself is the risk being priced. Mask positions are drawn from the run's own RNG stream, held windows never masked or trained on.
- **mode:** process
- **prediction:** −0.01..−0.04 at trial scale; two-sided at probe (input corruption costs before the inference skill pays). Reasoning: at 0.885M weights the model is capacity-starved, and a second, differently-conditioned view of the same token stream is the cheapest supervision-density increase available that adds no parameters at serving (mask embedding is training-only scaffolding, discarded like the MTP head).
- **kill test:** retire if trial mean ≥ 2.8480, or if a dose control at `--mask-n 8` beats `--mask-n 32` by >0.02 (the corruption cost scales faster than the signal — the family is priced and closed at the low dose), or if train CE on UNmasked positions worsens ≥0.05 vs champion at matched steps (the auxiliary is eating the main objective, not serving it).
- **status:** queued
```mill
id: AO-007
mode: process
run: --arm layered_half --rope --mask-aux 0.1 --mask-n 32
```

### AO-008 · Past-token auxiliary head: predict t−1 from position t (shared head, w 0.05)
- **source:** auxiliary-signals lens — auxiliary prediction heads beyond the pooled MTP entries: every pooled/auxiliary head in the record predicts FORWARD (t+1 main, t+2 MTP/A-103). No head has ever asked the trunk to retain where it has been.
- **mechanism:** The final hidden state at position t is scored, through the same tied head, against token t−1 (the token two steps back from the main target at that position), loss weight 0.05, on every 4th position. A causal trunk can in principle discard a token once it has been consumed as context; the past-token loss pays it to keep a readable trace of the recent past in the residual stream — the same stream block 2 and the head read — which is also the substrate position-to-position information flows through in a 2-block model with no other memory. Targets are ground-truth tokens, CE-scored; the head and target direction are the only novelties.
- **train.py:** new flag `--past-aux 0.05` — training loop only: `CE((h @ tok.weight.T)[positions ::4], ids shifted +1 relative to the main target alignment)`, added to the loss before `trainer.step`. No new parameters. **Cost charged:** one extra vocab matmul on 1/4 of positions ≈ +6–9% step time, as AO-001.
- **mode:** process
- **prediction:** −0.005..−0.03 at trial scale — honestly the weakest prior among the head entries, included because the direction axis (past vs future supervision) is completely unmeasured in this lab and one probe prices it. A win would say the trunk under-retains context; a flat result closes the direction axis cheaply.
- **kill test:** retire if probe held Δ vs job zero > +0.02, or trial mean ≥ 2.8480, or the past-token auxiliary CE itself fails to fall below its init value by ≥20% over the run (the trunk cannot even express the signal — the head is decoration).
- **status:** queued
```mill
id: AO-008
mode: process
run: --arm layered_half --rope --past-aux 0.05
```

### AO-009 · Homeostatic histogram regularizer, expressed through the vote path
- **source:** auxiliary-signals lens — loss-side regularizers expressed through the vote path; nearest neighbours A-009 (FIXED 1.5× bonus on votes toward 0, open-loop, always on) and F-024 (homeostatic servo on per-row SCALES, never on votes or level histograms). This entry is a closed-loop controller on the installed histogram, acting only through vote admission.
- **mechanism:** The trained champion's installed histogram sits near ~42% zeros — the zero state is load-bearing (built-in feature selection), but nothing in the trainer defends that fraction: it drifts wherever the evidence pushes it. Every 20 steps the runner measures the global zero fraction z. While z is inside the band [0.38, 0.46], nothing changes. Outside it, a per-step vote bonus engages in the restoring direction only: if z > 0.46, strong votes that move a weight AWAY from 0 count 2 (one extra count); if z < 0.38, strong votes TOWARD 0 count 2. The bonus disengages the moment z re-enters the band. It is a regularizer whose loss is the histogram deviation and whose gradient is a vote — the only channel a vote trainer has for a discrete-state prior. Band edges are set from the champion's own recorded histogram, not tuned.
- **train.py:** new flag `--hist-homeo 0.38,0.46` on `Layered` — in `step()`, a per-run scalar `bonus_dir ∈ {-1, 0, +1}` refreshed every 20 steps from the installed states `t1+t2`; qualifying votes (sign matching the restoring direction relative to the weight's current installed value) add 2 instead of 1 to `c1/c2` before clamping. No new parameters, no extra forward/backward.
- **mode:** process
- **prediction:** −0.005..−0.025 at trial scale; ~0 at probe (the histogram barely moves in 25 steps — probe is a plumbing check, flat does not kill). The deliverable is partly the trace: if the bonus is engaged <5% of steps at trial, the histogram is already self-regulating and the regularizer axis closes with a measurement; if it is engaged >50%, the band is wrong, not the idea, and it is re-set once from the trace, not tuned silently.
- **kill test:** retire if trial mean ≥ 2.8480, or if the engaged-direction flip share shows the bonus manufacturing flips (bonus-assisted flips >30% of all flips while held is flat — the controller is doing the learning, badly), or if z exits the band and never returns in ≥2 of 3 seeds (the vote channel is too weak to express this regularizer at V=32).
- **status:** queued
```mill
id: AO-009
mode: process
run: --arm layered_half --rope --hist-homeo 0.38,0.46
```

### AO-010 · Two-snapshot checkpoint distillation: averaged 33% + 66% teachers (dose variant of AO-002)
- **source:** auxiliary-signals lens — the multi-teacher form of AO-002's mechanism; distinct from G-057/MC-009 (teachers are independent RUNS in an ensemble) — both teachers here are earlier checkpoints of the SAME trajectory, so their average is a time-average of one model's beliefs, not an ensemble of models.
- **mechanism:** Snapshots are frozen at 33% and 66% of steps. In the final third, the auxiliary term is 0.3 · KL(mean of the two snapshots' token distributions ‖ student) at temperature 2, added to unchanged CE. The 33% snapshot is structurally distant (many flips ago) and the 66% snapshot is close; their averaged distribution is a smoother, less idiosyncratic target than either alone — the discrete analogue of averaging checkpoints in output space, applied as a training signal rather than a readout (readout averaging is G-026/A-094's territory; this entry never averages weights).
- **train.py:** new flag `--ckpt-distill2 0.3` — as AO-002, with two frozen `Tiny` copies and a probability-mean of their logits before the KL. **Cost charged:** two extra no-gradient forwards per step in the final third only ≈ +20–25% of that phase's wall (≈ +7–9% total), plus ~14 MB training-only snapshot storage. Only run if AO-002's single-snapshot reading is at least flat-positive — this entry prices the averaging increment, not the base effect.
- **mode:** process — full trial only, sequenced after AO-002
- **prediction:** −0.005..−0.02 INCREMENTAL over AO-002's arm at trial scale (not over champion — the entry's claim is the increment). Reasoning: if AO-002's gain is churn reduction, a smoother target should reduce churn slightly better; if AO-002 is flat, this entry is not run and costs nothing.
- **kill test:** retire if it fails to beat AO-002's trial mean by >0.01, or if either snapshot's individual KL to the student collapses to ~0 before its phase ends (that snapshot stopped being a distinct teacher).
- **status:** queued
```mill
id: AO-010
mode: process
run: --arm layered_half --rope --ckpt-distill2 0.3
```

### AO-011 · Far-horizon MTP head: t+4 only, separate head, w 0.05 (horizon bracket)
- **source:** auxiliary-signals lens — auxiliary prediction heads beyond the pooled MTP entries: the pooled horizon is exactly t+2 at two weights (MILL-123/124) plus A-103's same-head t+2. The horizon axis itself — how far ahead an auxiliary target can sit before it stops serving t+1 — has never been varied.
- **mechanism:** One separate auxiliary head (a second tied-head readout with its own small pre-norm, training-only, discarded at serving) predicts token t+4 from position t, loss weight 0.05, with NO t+2 head present. Predicting four steps ahead cannot be solved by local collocation statistics the way t+2 partly can; it pays only for representations that carry topic, syntax state, and source style — the slow features. At w 0.05 its gradient is a minority signal by design: it shapes the trunk's evidence stream without competing with CE for the counters.
- **train.py:** new flag `--mtp4 0.05` — model builder adds the auxiliary head module (head params training-only, ~0.8 MB AdamW state charged, 0 B serving); loop adds `0.05 * CE(aux_head(h), targets shifted −4)` on positions with a valid t+4 target. **Cost charged:** one extra vocab matmul on all positions ≈ +25–30% step time — the most expensive head entry here, stated plainly; judged at equal minutes.
- **mode:** process
- **prediction:** −0.005..−0.03 at trial scale, two-sided: at 0.885M weights a t+4 target may simply be too hard to carry signal (its auxiliary CE may sit near the floor all run, in which case its gradient is near-noise and the entry should read flat-to-worse). With MILL-123/124 this completes the horizon curve {t+2 at 0.1/0.3, t+4 at 0.05} from which the useful horizon at this scale can be read off, whichever way it lands.
- **kill test:** retire if trial mean ≥ 2.8480, or if the t+4 auxiliary CE falls <5% from its init value over the full run (target unreachable at this scale — no signal was ever transmitted, and higher doses are not worth probing), or if it wins at equal steps but loses at equal minutes (the head matmul ate it, as priced).
- **status:** queued
```mill
id: AO-011
mode: process
run: --arm layered_half --rope --mtp4 0.05
```

### AO-012 · Coarse-class auxiliary head: predict the next token's class (16 classes, tiny head)
- **source:** auxiliary-signals lens — auxiliary prediction heads at the opposite granularity from AO-011: instead of a harder fine target, an easier coarse one. No pooled entry supervises any target coarser than the token itself.
- **mechanism:** A fixed, deterministic map sends each vocab token to one of 16 classes (digit-led, capital-led, lower-case, punctuation-led, whitespace-led, German-specific characters, other scripts, etc., derived from the tokenizer's piece strings at build time). A tiny head (192→16, ~3k parameters) on the final hidden state predicts the class of the NEXT token, loss weight 0.05. Ternary QK/FFN logits are coarse, and full-vocab CE spends most of its gradient mass separating near-identical pieces; the class loss gives every position a low-variance, almost-always-learnable signal about the syntactic SHAPE of what comes next — signal whose gradient direction is stable across batches, which is exactly the property a sign-integrating vote counter can accumulate, in a way it cannot accumulate the high-variance fine-grained gradient.
- **train.py:** new flag `--class-aux 0.05` — build-time class table `piece_class[4096]` stored as a buffer; model gains the 192→16 head (training-only, discarded at serving); loop adds `0.05 * CE(class_head(h), piece_class[targets])`. **Cost charged:** negligible (16-way matmul); head state ~25 KB training-only.
- **mode:** process
- **prediction:** −0.005..−0.02 at probe and trial scale — the smallest expected effect in this file, and the cheapest: its value is partly diagnostic, since class accuracy per position is a readable proxy for whether the trunk tracks syntax state at all, logged alongside held either way. If a stable low-variance signal is what votes are starved of (the premise AO-003 tests from the gate side), this is the loss-side version of the same bet, and the pair read together.
- **kill test:** retire if probe held Δ vs job zero > +0.02, or trial mean ≥ 2.8480, or class-head accuracy fails to exceed its majority-class baseline by ≥10 points (the trunk carries no class information and the gradient was noise).
- **status:** queued
```mill
id: AO-012
mode: process
run: --arm layered_half --rope --class-aux 0.05
```

---

## Miner's ranking note

Top 3 (★): **AO-001** deep supervision — the densest new CE signal per unit compute in the
file, acting on the longest gradient path in the net, from step 0, with no teacher and no
extra parameters. **AO-002** checkpoint self-distillation — the only teacher that costs no
training run of its own, aimed at the champion's measured late-run churn, with a token-space
target that stays strictly inside the JEPA boundary. **AO-003** surprise gate — zero extra
passes, vote-path only, and it repairs a disenfranchisement that every pooled gate shares
by construction; its voter-coverage diagnostic makes even a flat reading informative.

The best single idea in this file is **AO-001**: in a 2-block model, half the ternary
structure (block 1) has only ever been trained through the other half's moving, coarse
output. Giving block 1 its own direct next-token loss — the same target, the same head, a
shorter path — is the auxiliary signal most tightly coupled to the objective it serves,
the cheapest to implement honestly (subsampled positions, tied head, no new parameters),
and the one whose mechanism (flip share and reversal rate in block 1 specifically) can be
verified in the run's own logs rather than inferred from the held number alone.

*End of wave3-lens3. 12 entries (AO-001..AO-012), all queued, all `process` mode, all on
the champion chassis unless an entry says otherwise. Coverage of the lens territory:
gradient shaping — AO-003, AO-005; auxiliary heads beyond pooled MTP — AO-001, AO-007,
AO-008, AO-011, AO-012; loss-side regularizers through the vote path — AO-006, AO-009;
teacher-free self-distillation from own earlier checkpoints — AO-002, AO-004, AO-010;
flip-consistency penalties — AO-006. JEPA objective: not re-proposed in any form;
F-031 (JEPA-as-initializer): not duplicated.*
