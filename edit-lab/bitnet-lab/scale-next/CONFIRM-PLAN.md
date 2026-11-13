# CONFIRM-PLAN.md — Long-Token Confirmation of the Ladder Verdict (Muse's work, Muse's side)

## 1. The decision this settles

The scale ladder ran every rung at **56 steps = 458,752 tokens** (7.75% of the 5,917,236-token corpus). Its headline — which rung wins per byte (2M held 3.2746 over 3 seeds; 10M seed 0 = 2.9472; 50M pending) — is a *small-token* result. Bigger ternary models are more token-hungry (the architecture study: Spectra data exponent 0.81 vs parameter exponent 0.32), so the per-byte ranking at 459K tokens **can flip** at several million tokens, and the lab has already retracted one headline once (the layered-votes half-size control) for trusting a confounded comparison.

The confirmation runs settle exactly three things:

1. **Ranking stability:** does the ladder's per-byte winner at 459K tokens still win at ~2.3M and ~3.7M tokens?
2. **Saturation dose:** how much of the gain is already there by 280 steps — i.e., what token dose the overlap program's rounds should actually use.
3. **Member size:** which rung's shape the overlap program (OVERLAP-DESIGN.md) builds its members at.

If the ranking flips, the ladder headline gets a correction note in its record, the same way the layered headline was corrected. That is a success outcome for this plan, not a failure.

## 2. The runs

Planning assumption (from the ladder's partial state): winner = **10M rung** (dim 512 × 3), runner-up = **2M rung** (dim 288 × 2). If the finished ladder crowns a different pair, substitute those shapes — the structure does not change. Recipe is the ladder's own: layered + rotary + plain votes, `--steps` mode, the standard fixed 128 held windows, seeds recorded in runs.jsonl by the same record format. No recipe changes: a confirmation that changes two variables confirms nothing.

| Set | Rung | Steps | Tokens | % of corpus | Seeds | Per-run wall | Set total |
|---|---|---|---|---|---|---|---|
| A | runner-up (2M) | 280 | 2,293,760 | 38.8% | 3 | ~24 min | ~1.2 h |
| A | winner (10M) | 280 | 2,293,760 | 38.8% | 3 | ~60 min | ~3.0 h |
| B | runner-up (2M) | 448 | 3,670,016 | 62.0% | 3 | ~38 min | ~1.9 h |
| B | winner (10M) | 448 | 3,670,016 | 62.0% | 3 | ~1.61 h | ~4.8 h |

**Total ≈ 10.9 h** of VM time (NUMBERS.md), queued behind the ladder and growth cycles like all lab work. No run exceeds ~1.7 h singly. Corpus note: even the longest set stays under one epoch (62%), so no run trains on repeated data — the comparison stays clean. Anything beyond ~723 steps would cross one epoch and is explicitly out of scope here.

**Staging:** Set A fires first. There is a decision checkpoint after Set A (§3) before Set B is committed — Set B costs ~6.7 h and should not run on autopilot if Set A already flipped the ranking decisively (in that case Set B re-runs with the *new* winner substituted as "winner" — the plan follows the evidence, not the original labels).

## 3. Decision rules (pre-registered)

Let L(rung, steps) = mean held loss across the 3 seeds, and per-byte ranking computed under the ladder record's own convention, recomputed identically at each token scale.

- **Ranking holds** (same winner at 280 and 448 steps, margin > 2 sd of the seed difference): member size = winner rung. Ladder headline confirmed at long tokens; quote it with the token range attached.
- **Ranking flips at Set A and holds at Set B:** member size = the long-token winner. A correction note is appended to the ladder record: the 459K-token ranking does not survive at ≥ 2.3M tokens. The overlap program proceeds at the corrected size.
- **Ranking flips only at Set B:** token scale is a load-bearing variable, not a detail — member size = Set B winner, and every future ladder-style claim in the lab must state its token budget. 
- **Saturation:** if L(winner, 448) − L(winner, 280) < 0.02, gains have saturated by ~2.3M tokens at this corpus size; the overlap program's round budgets are capped at the 280-step-equivalent flip dose, and "more tokens" stops being the lab's default answer to scale questions on this corpus.
- **Both rungs degrade or stall vs their 56-step trajectory** (held loss at 280 steps not better than the 56-step value by > 0.05): something is wrong beyond ranking (corpus exhaustion, recipe instability at long horizons) — stop, diagnose before any overlap work. This outcome blocks the overlap smoke regardless of Gate 0.

## 4. The 50M clause

If the finished ladder crowns the **50M rung** per byte, its confirmation as specified here is **not runnable**: a single 280-step run at the driver's measured ~91 s/step is ~7.1 h, and 448 steps ~11.3 h — single jobs of that length on this VM are not a plan, and train.py has no checkpoint-resume (its `--ckpt` is gradient checkpointing against OOM, not resumability). Options, in order:

1. Confirm 10M vs 2M as above and treat the 50M result as **unconfirmed** — every claim quoting it says so, and the overlap program builds at the 10M shape (the largest *confirmed* rung).
2. Only if Arnav wants the 50M claim settled: a small separate engineering task adds save/resume to train.py, the 50M confirmation runs as checkpointed chunks, and this plan's Sets A/B apply unchanged. That task is not assumed, scheduled, or bundled into this plan.

## 5. Relation to the overlap program

Gate 0 (divergence test) and Set A are independent and both fire when the ladder verdict lands; neither waits for the other. The overlap **smoke** waits for both: Gate 0 sets the flip dose, Set A/B set the member shape and token regime. If §3's stall outcome triggers, the smoke is blocked until the diagnosis lands.
