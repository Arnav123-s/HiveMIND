# FIDELITY — the probe-fidelity ledger (J-025, as filed)

<!-- Muse's work — Muse's side of the BitNet lab. Zero training: pure analysis of the
recorded record, 2026-11-12. Implements CANDIDATES-J.md J-025 and carries the minimal
J-027 lie registry; the pool-wide over-horizon flag list is mill/OVER-HORIZON.md.
Nothing in IDEA-POOL.md, screen.py, or PROMOTE.md was edited. -->

## Verdict, up front

**The probe stage's fidelity does not support the trust the funnel places in it —
and the strongest reason is that the trust has never been measurable from the record
at all.** `runs.jsonl` contains **no probe-budget run**: every comparable record is a
full 8-minute trial. The 75 s → 8 min fidelity the funnel actually spends is therefore
*unmeasured*, not merely weak (this is RIGOR-AUDIT §5a's hole, confirmed from the data
side). What *can* be measured from the record — single-seed fidelity at full budget,
the probe's stand-in as filed in J-025 — separates catastrophes reliably and collapses
exactly where the 0.05 bar operates: **Spearman ρ = 0.934 over all 13 arms, but
ρ = 0.371 in the |Δ| ≤ 0.10 decision band**, with **2/12 champion-relative sign flips**
and the calibration set's **only probe promotion a false promote at the 0.05 bar
(1/12 candidates = 8.3%; 1/1 = 100% of promotions issued)**. Trust the screen to kill
the bottom of the pool. Do not trust it to judge the middle.

## What was scored (and the filed count vs the disk count)

- Source: `runs.jsonl`, snapshotted before analysis (45 rows, sha256
  `74ce48c6c2309a449f3ef81eef2298736076424509441c877c4f3b20825e8b0f`; the file gained a
  1-step preflight row — `layered_half_rope_mill000pf`, held_init 8.3138, matching
  RIGOR-AUDIT §2b's parity value — while this analysis was running; it is not a trial
  and is excluded).
- J-025 was filed against "15 arms × 3 seeds". On disk, the comparable validation set
  is **13 arms × 3 seeds**: the arms with three completed 8-minute runs on the standard
  corpus and held judge. Excluded, with reasons: `layered_rope_scale2m` /
  `layered_rope_scale10m` (different model size, 56 fixed steps, 12/25-minute budgets —
  a different currency, J-036's question, not this one's), `layered_rope_smokecheck`
  (2 steps), `layered_half_rope_mill000pf` (1-step preflight).
- Reference ranking ("the 8-min ranking"): 3-seed mean `held_final`, lower is better.
  Champion: `layered_half_rope`, mean **2.8580 ± 0.0161** — the snapshot reproduces the
  filed champion reference exactly.
- Δ always means champion − arm (positive = arm beats the champion). The bar is
  PROMOTE.md's `PROMOTE_DELTA = 0.05`.
- Caveat carried throughout: `jepa_half_rope`'s held_final (≈7.97) is the token-CE of a
  trunk never trained on token CE (its filed judge was probe CE, RESULTS-JEPA). It is
  kept in the headline set because J-025 says "every observable already recorded", and
  every headline number is also reported with it removed.

### The recorded full-trial ranking (13 arms)

| # | arm | mean held | sd | seed-0 held | Δ (full) |
|---|-----|-----------|------|-------------|----------|
| 1 | ste_half | 2.8205 | 0.0069 | 2.8150 | +0.0374 |
| 2 | layered_half_rope (champion) | 2.8580 | 0.0161 | 2.8765 | 0 |
| 3 | layered_half_rope_carry | 2.8761 | 0.0030 | 2.8751 | −0.0181 |
| 4 | layered_half | 2.8990 | 0.0073 | 2.8937 | −0.0411 |
| 5 | plain_half | 2.9010 | 0.0276 | 2.9179 | −0.0431 |
| 6 | jepa_ctrl_half_rope | 2.9173 | 0.0497 | 2.8631 | −0.0594 |
| 7 | layered_half_rope_cooldown | 2.9707 | 0.0108 | 2.9828 | −0.1127 |
| 8 | ste | 2.9952 | 0.0245 | 2.9838 | −0.1372 |
| 9 | plain | 3.0743 | 0.0316 | 3.1092 | −0.2163 |
| 10 | layered | 3.0977 | 0.0096 | 3.0994 | −0.2397 |
| 11 | mag | 3.1352 | 0.0367 | 3.1761 | −0.2772 |
| 12 | anneal | 3.8503 | 0.0294 | 3.8818 | −0.9923 |
| 13 | jepa_half_rope | 7.9718 | 0.1648 | 7.8124 | −5.1139 |

Note what this table already says about the bar: **no arm in the calibration set beats
the champion by ≥ 0.05 at full trial.** The best true Δ is ste_half's +0.0374 — a `near`,
not a `promote`, by the funnel's own numbers. (ste_half *does* clear the separate
adoption bar, 2.8205 < 2.8258; adoption and probe promotion are different bars and this
ledger judges the probe bar as filed.)

## Scoreboard: every cheap observable in runs.jsonl vs the 8-min ranking

Spearman ρ and Kendall τ of each observable against the 3-seed mean-held ranking.
Loss-like observables are scored raw (positive ρ = lower observable tracks lower held).

| observable | n | ρ | τ | verdict |
|---|---|---|---|---|
| **seed-0 held_final (the probe stand-in)** | 13 | **+0.934** | +0.846 | best cheap observable; see band collapse below |
| seed-1 held_final (reference only) | 13 | +1.000 | +1.000 | the seed lottery: same statistic, different seed |
| seed-2 held_final (reference only) | 13 | +0.984 | +0.949 | " |
| seed-0 `train_last100` | 12 | +0.846 | +0.667 | misranks close arms, as documented; worst τ on the board |
| mean `train_last100` (3 seeds — **not** cheap) | 12 | +0.951 | +0.879 | ceiling reference only; and see its ste_half miss below |
| seed-0 / mean `steps` | 13 | −0.428 / −0.456 | −0.387 / −0.410 | a confound meter (budget), not a judge: more steps ↔ better held is the half/full size split |
| seed-0 / mean `mean_flip_share` | 12 | −0.222 / −0.193 | −0.161 / −0.108 | **no fidelity.** Flip share does not rank arms (J-026's ensemble cannot lean on it alone) |
| seed-0 / mean state_hist entropy | 9 | −0.667 / −0.733 | −0.500 / −0.611 | negative and chassis-confounded (5-level vs 3-level histograms); n=9 (STE arms record no histogram) |
| seed-0 / mean state_hist saturation (extremal-level share) | 9 | +0.367 / +0.300 | +0.278 / +0.167 | weak; not a judge |
| seed-0 / mean `held_init` — **NULL control** | 12 | **+0.730** | +0.660 | a pre-training number ranks at 0.73 — see below |

Missing observables, stated plainly: **held at probe budget / early-step held — n = 0
records.** They do not exist in `runs.jsonl` at any step count below the full trial
(the only sub-trial rows are a 2-step smoke check and the 1-step preflight). J-033's
trajectory observables likewise have no recorded instances. Any future FIDELITY issue
that quotes a 75 s ρ is quoting J-033/G-061 calibration runs that have not happened yet.

### The null control is the warning

`held_init` is measured before a single training step. It cannot contain information
about an arm's mechanism — yet it ranks the 13 arms at ρ = +0.730, because it encodes
the chassis split (half-width arms init at ≈8.29–8.31, full-width at ≈8.35–8.42) and
the ranking is itself strongly chassis-structured. Consequences:

- Any candidate observable must clear **0.73**, not 0, to claim it measures a treatment.
  `train_last100` seed-0 (0.846) clears it by little; flip share, saturation, and
  entropy do not clear it at all.
- A large share of the headline ρ = 0.934 is the screen re-discovering which chassis an
  arm sits on. Within a chassis — where pool entries actually compete — fidelity is
  the near-band number below.

### The decision band is where fidelity goes to die

The funnel's bar operates on arms within ~±0.10 of job zero. Restricting the same
computation to those arms:

| subset | seed-0 held ρ | seed-0 train ρ | mean train ρ |
|---|---|---|---|
| all 13 arms | +0.934 | +0.846 | +0.951 |
| excl. `jepa_half_rope` (12) | +0.916 | +0.846 | +0.951 |
| excl. both JEPA arms (11) | +0.982 | +0.900 | +0.945 |
| excl. jepa_half + anneal (11) | +0.891 | +0.800 | +0.936 |
| **\|Δfull\| ≤ 0.15 (8 arms)** | **+0.738** | +0.643 | +0.976 |
| **\|Δfull\| ≤ 0.10 (6 arms)** | **+0.371** | **+0.257** | +1.000 (n=6; not cheap) |

The global ρ is carried by the catastrophes (anneal at −0.99, jepa at −5.11, mag at
−0.28), which any observable — including the null — separates. In the band where
`promote / near / flat / below` is actually decided, the probe stand-in's ρ falls to
**0.371** (τ 0.333): barely better than chance at ranking the arms the bar exists to
rank. This is J-033's filed observation — every recorded sign flip lives in the near
band — now with the correlation attached.

## The bar audit at PROMOTE_DELTA = 0.05 (champion-relative)

Δ_obs = champion's observable − arm's observable; an arm "promotes" if Δ_obs ≥ 0.05.

### Seed-0 held (the probe stand-in) — 12 non-champion arms

- **Sign flips: 2/12 = 16.7%** — `layered_half_rope_carry` (Δ_seed0 +0.0014 vs Δ_full
  −0.0181) and `jepa_ctrl_half_rope` (Δ_seed0 +0.0134 vs Δ_full −0.0594). Both flips are
  small-|Δ_seed0| arms, and one of them (jepa_ctrl) is a 0.073 error: the probe reads
  *flat* an arm the full trial puts clearly *below*. (Matches J-025's filed prediction
  of 2 sign flips; the filed denominator was 13.)
- **Promotions issued: 1** — ste_half (Δ_seed0 +0.0615).
- **False promotes: 1** — ste_half's full-trial Δ is +0.0374 < 0.05.
  **False-promote rate = 1/12 = 8.3% of candidates; 1/1 = 100% of promotions.**
  Read both ways, because both are true: by candidate share this squeaks under J-028's
  10% target; by precision, *every promotion the screen has ever issued on this record
  is a bar-crossing false promote*. The mitigating fact, also on the record: the arm
  is genuinely the best in the set (rank 1 at full trial, adoption-clearing) — the
  probe got the sign and the rank right and the *size* wrong, overstating Δ by 64%
  (winner's-curse shrinkage 39%: +0.0615 → +0.0374, reproducing J-035's filed anchor
  exactly).
- **False kills: 0** — but vacuously: the calibration set contains no arm with
  Δ_full ≥ 0.05 to kill. The false-kill side of the bar is *untested* by this record,
  not proven safe.
- Mean |Δ_seed0 − Δ_full| = 0.033 across arms (0.020 excluding jepa_half_rope);
  the median arm's own seed range (max−min over 3 seeds) is 0.045 — **seed noise alone
  is the size of the bar.**

### Seed-0 train_last100 — 11 non-champion arms with the field recorded

- Sign flips: **2/11 = 18.2%** (`layered_half`, `jepa_ctrl_half_rope`).
- Promotions issued: 1 (ste_half, Δ +0.0806). **False promotes: 1 → 9.1% of
  candidates; 100% of promotions** (same arm, same overstatement, larger).
- Confirms the filed documentation: train loss separates catastrophes and misranks
  close arms. It must never be a probe's reported companion.

### Mean train_last100 (not cheap — reported because it indicts itself)

- Sign flips 0/11 and it promotes nobody — but its Δ for ste_half is **+0.0011**:
  on train loss, the table's best arm is indistinguishable from the champion it beats
  by 0.0374 on held. Even with all 3 seeds spent, the train-loss witness disagrees
  with the held judge on the single most important comparison in the record.

## J-028 admission test, applied to the stand-in

| target (as filed in J-028) | result |
|---|---|
| Spearman ρ(probe, trial mean) ≥ 0.80 | **PASS** globally (0.934) — **FAIL** in the decision band (0.371) |
| false-promote ≤ 10% | **PASS** by candidate share (8.3%) — **FAIL** by promotion precision (1/1) |
| false-kill of eventual trial winners = 0 | **UNTESTED** — no winner at the bar exists in the calibration set |

Under J-028's own rule (a stage failing any target is demoted to advisory), the probe
stage as represented by its only measurable stand-in is **not admitted as a judge**.
It remains serviceable as what PROMOTE.md says it is — a screen that kills the bottom
(anneal, mag, plain, layered are correctly and deeply below on every observable) —
provided `flat`/`below` verdicts in the near band and all over-horizon entries
(OVER-HORIZON.md) are ledgered as advisory, not as kills.

## The lie registry (minimal J-027 — classes with recorded exemplars)

| lie class | recorded exemplar on this record |
|---|---|
| Late phase / budget split — mechanism's decisive phase is a fraction of the run | FP-first (PROMOTE exception MILL-111/112); hybrid phases MILL-220..222; carry's late-acting +0.018-class behaviour and cooldown's +0.1127 (J-027 validation rows) |
| Counter-bank accumulation — the bank a mechanism spends is thinnest at probe horizon | D-003/D-004/D-005/D-007, filed full-trial-only in J-027; level-population: ±2 share only 3.5% even at full trial on the champion |
| Readout tail — verdict lives in checkpoints/averages of a mature run | Modal readout MILL-218/219 (pooled, untested); Fable's running-mean readout line |
| Schedule cooling — the cooled regime acts on an immature bank at probe scale | vsched family MILL-204..206 (pooled); the closed anneal 8→64 arm (−0.99) shows schedule shape dominates at any horizon |
| Teacher/target maturity — an EMA target or teacher is unformed at probe scale | JEPA: probe CE 3.2428 ≈ init floor 3.2445 while the JEPA loss fell 4–5× (RESULTS-JEPA) |
| Threshold arithmetic — trigger mathematically unreachable in ~25 steps | No recorded arm yet; arithmetic from the vote rule (≤1 counter step per step): any V > 25 flips zero weights in a probe. Pool instances flagged in OVER-HORIZON.md |

## Bottom line for the funnel

1. The 0.05 bar is an assertion (RIGOR-AUDIT §5a) and remains one: there is still no
   measured 75 s noise figure and no recorded probe-budget run to measure fidelity
   against. J-025's ledger can only bound the problem from the seed side.
2. From the seed side, the bound is: global ρ 0.934, decision-band ρ 0.371, sign flips
   2/12, false-promote 8.3% of candidates / 100% of promotions, seed noise ≈ the bar.
3. Therefore: probe verdicts may kill the bottom of the pool (Δ ≤ −0.10 territory is
   reliable on this record) and may promote for trial (a wasted trial is the only cost
   of the ste_half-type error) — but a near-band `flat` is not evidence of absence, and
   for the 95 over-horizon entries in OVER-HORIZON.md it is not evidence at all.

*Method note: Spearman/Kendall computed on the snapshot above; entropy = Shannon
entropy of `state_hist`; saturation = share in the extremal levels. All numbers in
this file are recomputable from the snapshot's 39 comparable rows.*
