# Muse's work — written by Muse, on Muse's side. Fable's HiveMIND was read read-only; nothing on Fable's side was touched.

# The missing control for the layered-half win — results, 2026-11-12

Question (Fable's critique, relayed by Arnav): layered_half (2 blocks, 884,736 weights,
each the sum of two vote-trained ternary layers, levels −2..+2) won the 2026-11-11 sweep
at held 2.899. But a half-size model gets ~161 steps in the same 8 minutes where the
full-width arms get ~115–121. Was the win the five levels — or just the extra steps?

Control arms run for this note (same rig, corpus, held set, seeds 0–2, 8 minutes each):
- **plain_half** — the plain vote counter at half width (2 blocks, 884,736 ternary
  weights, 3 levels). Same size, same step count as layered_half, no second layer.
- **ste_half** — the gradient/STE trainer (built-in recipe, unchanged) at half width.
  Does the gradient way also gain from half size?

## Results — held loss, 3 seeds × 8 minutes

| arm | seed 0 | seed 1 | seed 2 | mean ± sd | steps | mech. state |
|---|---|---|---|---|---|---|
| plain (full, from sweep) | 3.0658 | 3.0478 | 3.1092 | 3.0743 ± 0.0316 | 121/124/115 | 2,211,840 B |
| ste (full, from sweep) | 2.9838 | 2.9785 | 3.0233 | 2.9952 ± 0.0245 | 119/119/115 | 21,233,664 B |
| layered (full, from sweep) | 3.0994 | 3.1063 | 3.0873 | 3.0977 ± 0.0096 | 116/108/115 | 4,423,680 B |
| **plain_half** | 2.9179 | 2.9160 | 2.8692 | **2.9010 ± 0.0276** | 150/158/176 | 1,105,920 B |
| **ste_half** | 2.8150 | 2.8282 | 2.8184 | **2.8205 ± 0.0069** | 161/163/154 | 10,616,832 B |
| layered_half (from sweep) | 2.8937 | 2.9073 | 2.8961 | 2.8990 ± 0.0073 | 161/161/163 | 2,211,840 B |
| layered_half + rotary | 2.8765 | 2.8477 | 2.8497 | 2.8580 ± 0.0161 | 154/170/168 | 2,211,840 B |

## Verdict — the layered win was the steps, not the levels

plain_half vs layered_half: means differ by **0.0020**. The standing bar is a gap of
more than 2 seed-sd **and** more than 0.01 — 2 sd is 0.0145 (layered_half's spread) or
0.0552 (plain_half's). The gap clears neither bar; it does not even clear the 0.01 floor.
Seed by seed the sign flips (layered ahead by 0.024 and 0.009 on seeds 0–1, plain ahead
by 0.027 on seed 2). **plain_half matches layered_half within noise: at equal size and
equal steps, the five levels earn nothing measurable.** Fable's critique was right.

The size effect itself is real — and it is the same for everyone. Going full → half:
plain gains 0.1732, STE gains 0.1747, layered gains 0.1986. The layered arm's celebrated
gain sits in the same band as the other two methods' size gains. There is nothing extra
left over for the levels to explain.

Two more plain statements the records support:

- **STE also gains from half size — and at half size it leads.** ste_half (2.8205) beats
  ste full by 0.1747 (clears the bar easily), beats layered_half by 0.0785 (also clears
  the bar), and sits ahead of everything else measured on this rig, including
  layered_half + rotary (2.8580). The honest caveat rides with it: ste_half carries
  10,616,832 B of full-precision training state, roughly ten times the vote arms' —
  its win is quality at this budget, not state economy.
- **plain_half matched layered_half at half the mechanism state** (1,105,920 B vs
  2,211,840 B): with the step confound removed, the second counter layer bought nothing
  per byte either, at this scale.

What survives from the sweep, unchanged: votes at full width reached ~97% of STE's
improvement at ~1/10 the state (3.0743 vs 2.9952); rotary positions improved the layered
trainer (2.899 → 2.858) with step counts overlapping, so that win has no step confound
of this kind. What does not survive: "layered weights beat gradient training" — at equal
size and steps they do not, and the gradient way at half size beats them.

Same bounds as the sweep: 8-minute runs, one corpus, cell scale (884,736–1,769,472
ternary weights). This retires the layered claim at this scale; it says nothing about
whether five levels help at larger scale or longer budgets — that would be a new test,
not a rescue of this one.

## Incidents

- ste_half's first attempt (18:01 UTC) crashed instantly on all three seeds: train.py's
  state-size line branched on `arm != "ste"`, sending ste_half into the vote trainers'
  state path, which the STE trainer does not have. My wiring bug, in the flags added for
  this control. One-line fix (`arm not in ("ste", "ste_half")`), import-verified
  (both half arms construct exactly 884,736 ternary weights), then relaunched clean;
  all three seeds completed by 18:31 UTC, inside the 10:35 PT hard stop. The plain_half
  records were written before the crash and are unaffected.
- During the window, a parallel Muse-side job extended train.py's Layered trainer with
  carry/cooldown options. The control arms execute only the Direct and STE paths, and
  their records (init losses 8.26–8.31, step counts, state sizes) are consistent with
  the established code paths.

Drivers: `run_half_control.py`, `run_ste_half_fix.py`. Records: `runs.jsonl`
(arms `plain_half`, `ste_half`). Events: `sweep.log`.
