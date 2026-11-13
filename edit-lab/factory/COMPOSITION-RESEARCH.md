# Composition Research — Muse's work, Muse's side

Prototypes of composition rules **beyond the learned say** for the
bug-pattern composition (16 adopted members, 5 defect classes +
clean). The learned say is a separate build: none of its files were
read for fitting, edited, or reused here, and the serving
composer config was checked to carry no `say` payload before any
number below was measured. Promotion of anything below into the
real composer is **out of scope** here — `serve.py` /
`swarm/composers.py` are not touched; this file only recommends.

Code: `factory/compose_research.py` (new file, the only code
written). Reproduce:

```
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 python3 -m factory.compose_research            # primary split
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 python3 -m factory.compose_research --split group  # sensitivity
```

Each run takes ~20 s, writes nothing, and was verified
deterministic (two primary runs produced byte-identical JSON).

## Data — what was fitted on, what judged, what was never touched

One dev pool, train/dream material only, reachable via the
`factory.dream` / `factory.subjects` loaders' sources:

| source | raw | after exact-text dedupe |
|---|---|---|
| phase-3 **train** templates (`swarm.phase3`, seed 21) | 48 | — |
| swarm phase-4 dream corpus (`swarm.dream`, seed 77) | 37 | — |
| factory dream **train** pool (`dream_gen.gen_pool`, seed 4200, `{1:40, 2:34, 3:34}`, prefix `dreamtrain` — the exact call `factory.dream` makes) | 628 | — |
| **pool total** | 713 | **625** |

**Primary split** (split seed **20261113**): stratified by label —
items of each label ordered by `md5(seed:label:text)`, first half
to fit, rest to judge. **Fit n=315, judge n=310.** Judge labels:
off-by-one 43, wrong-operator 84, swapped-operands 43,
mutable-default 7, missing-return 28, clean 105.

**Sensitivity split** (`--split group`): whole generator-kind
groups assigned greedily (label-balanced) to one side — fit n=305,
judge n=320. This is a leave-kinds-out test: the pool holds only
~52 distinct code skeletons, so it is much harsher than the
primary split and is reported alongside every headline number.

**Sealed sets stay sealed.** `bug_heldout_v2.py`,
`held_slice_v2.py` and all sealed battery data were never
imported, fitted on, or judged on. The phase-3 *held* templates
were not used either — train splits only.

**Caveats that apply to every absolute number below**

1. Parts of this pool are material some members were trained or
   dream-practised on, so member margins here are partly memory.
   Every rule (baselines included) is inflated by a shared,
   unknown amount. The *comparison* between rules on the same
   judge split is the finding; no absolute here is a sealed
   estimate and none should be quoted as one.
2. On the primary split, generator kinds straddle fit/judge, so
   fitted rules can exploit kind-specific margin patterns. The
   group split exists precisely to expose that — and it does
   (Approaches 3–4). Read the two splits as brackets, not rivals.
3. mutable-default has a single member and judge n=7 (primary) —
   its per-class numbers are near-anecdotal everywhere below.

Members: all 16 adopted `bug-*` models from
`factory.dream.load_bug_registry()` — off-by-one ×4,
wrong-operator ×5, swapped-operands ×4, mutable-default ×1,
missing-return ×2. A member's evidence is its binary margin
`logit(cls) − logit(other)` (`swarm.composers._model_margin`);
its implied probability is `sigmoid(margin)`; its **solo
verdict** is its class when margin > 0, else `clean`.

## Baselines — primary judge split (n=310)

| rule | judge acc |
|---|---|
| member-alone **oracle** (any member's solo verdict is right — upper bound on selection, not a rule) | **0.8871** |
| mean-probability argmax (per class: mean of members' sigmoid(margin), argmax if > 0.5 else clean) | 0.6806 |
| margin-routed (the serving rule: strengths/variant routing, threshold 0) | 0.6742 |
| mean-margin voting (per class: mean margin, argmax if > 0 else clean) | 0.6645 |
| majority vote (members with margin > 0 vote their class; ties by mean margin) | 0.5677 |
| best single member as a solo composer (`bug-wrong-operator-harvest-model`) | 0.5065 |

Group split, same rules: oracle 0.8594, routed 0.6250,
mean-margin 0.6156, mean-probability 0.5938, majority 0.5125.
Context from the cycle records, on their (different, spent/held)
surfaces: routed 0.8621 / mean 0.7931 — those surfaces are far
easier for these members than this dream-heavy pool; do not
compare absolutes across surfaces.

The recurring weakness, in every rule on both splits:
**swapped-operands recall**. Routed gets 0.1163 of judge
swapped-operands right (primary); no baseline exceeds 0.21.
Composition is not where that class is lost — its members
rarely fire correctly in the first place (oracle aside).

## Approach 1 — Confidence routing with abstention

**Mechanism.** Trust the single highest-margin member across all
16, but only when its margin clears a threshold τ. Below τ,
abstain to the serving margin-routed rule (the defined fallback).
τ was fitted on the fit split only: a grid sweep maximising fit
accuracy chose **τ\* = 12** (fit 0.6889 vs routed's fit 0.6730;
ties in the sweep break toward the larger τ, the more selective
rule).

**Judge results (primary, n=310)** — the full tradeoff curve,
not one point:

| τ | coverage (solo route taken) | acc on covered | overall acc (with routed fallback) |
|---|---|---|---|
| 0 | 0.9677 | 0.4900 | 0.5032 |
| 0.5 | 0.8258 | 0.5508 | 0.5839 |
| 1 | 0.8194 | 0.5512 | 0.5839 |
| 2 | 0.7903 | 0.5633 | 0.6000 |
| 3 | 0.6968 | 0.6019 | 0.6419 |
| 4 | 0.6226 | 0.6736 | 0.6710 |
| 5 | 0.5806 | 0.6778 | 0.6710 |
| 6 | 0.4452 | 0.7029 | 0.6581 |
| 8 | 0.2645 | 0.7561 | 0.6903 |
| 10 | 0.1613 | 0.6200 | 0.6839 |
| **12 (= τ\*)** | **0.1065** | **0.7576** | **0.6968** |
| 15 | 0.0226 | 0.8571 | 0.6710 |
| 20 | 0.0194 | 1.0000 (n=6) | 0.6742 (= pure routed) |

**Group split:** τ\*=12 again (fit independently), judge
**0.6531** vs routed 0.6250, coverage 0.0437, covered acc 0.9286.

**Honest failure notes.** Trusting a single member at low τ is
actively harmful — at τ=0 the "best member" is right only 49% of
the time it fires, far below the routed ensemble. The gain lives
entirely in the high-margin tail, the tail is small (11% coverage
at τ\*), and the curve is noisy past τ=8 (the τ=10 covered-acc
dip is n=50 noise). Per-class at τ\* (primary): wrong-operator
recall rises 0.631 → 0.726 vs routed; every other class is
unchanged or ±0.01 — this is a small, targeted override, not a
new composer.

## Approach 2 — Calibrated voting (Platt scaling)

**Mechanism.** Per member, fit Platt scaling
`p = sigmoid(a·margin + b)` on the fit split (binary target:
label == member's class; a is an inverse temperature, b a shift —
fitted on standardised margins by regularised gradient descent,
after a raw Newton fit diverged to a ≈ 3×10⁵ on near-separable
members; that failed first pass is recorded in the code). Then
per class, a weighted mean of members' calibrated logits
(log-probability voting), weights = each member's fit-split
balanced binary accuracy mapped to [0, 1]. Verdict: argmax class
score if > 0, else clean. Calibrated logits are clipped to ±12 so
one saturated member cannot veto a vote.

**Judge results (primary, n=310): 0.6258** — *worse* than both
uncalibrated comparators on the same split: mean-margin voting
0.6645, mean-probability 0.6806. **Group split: 0.5312**, again
below mean-margin's 0.6156.

**Honest failure notes — this approach fails as formulated, and
the failure is diagnostic.** Every fitted a lands in
[0.023, 0.290]: the members' margins are wildly overconfident in
scale, so calibration shrinks them toward 0 — and most b's land
negative, because the binary fit target is "this class vs
everything else", where "everything else" dominates. A
well-calibrated *binary* member therefore says "probably not my
class" almost everywhere, and under the multiclass > 0 gate whole
classes go silent: judge recall for mutable-default is **0.0000**
(its only member got a = 0.098, b = −1.11, weight 0.87 — the
weight cannot rescue a logit that never crosses 0), off-by-one
0.1395, swapped-operands 0.0930, while clean recall inflates to
0.9619. Calibration fitted for the binary task is the wrong
object for a multiclass gate; fixing it needs joint
re-centring/threshold refit after scaling — a new prototype, not
a parameter tweak.

## Approach 3 — Feature-based specialist selection (router)

**Mechanism.** A small router learns, per snippet, *which
member's solo verdict to trust* — 17 actions: the 16 members,
plus NONE → `clean`. Training targets on the fit split are
deterministic: for a defect example, the true class's
highest-margin firing member; for clean, NONE. Features (50):
text statistics (length, line/token counts, operator and
`return`/`print`/`range` counts, `[]`/`{}` presence) + all 16
member margins + per-class mean/max margins + the 5 routed
margins + top-1/top-2 margin and their gap. Model: multinomial
logistic regression implemented as numpy softmax regression
(full-batch GD, 800 epochs, L2 1e-3, features standardised on
fit). Justification for not using the factory's TinyNet or
torch: the router's inputs are a numeric feature vector, not
text (TinyNet's featuriser is a text bag — the wrong input
type), and the factory interpreter is system python3, which has
numpy but no torch. Same model class, 50×17 parameters.

**Judge results (primary, n=310): 0.8032** (fit 0.8317) — the
best measured rule, +0.129 over routed, within 0.084 of the
0.8871 oracle. Judge picks are spread (NONE 156/310; the most
picked member, `bug-wrong-operator-accumulator-model`, 29).
Per-class (primary): wrong-operator 0.9286, clean 0.9810,
off-by-one 0.6279, missing-return 0.9643, mutable-default
0.8571 — but swapped-operands still only 0.1860.

**Group split: 0.5813 — below routed's 0.6250.** That is the
finding about this approach: most of its primary-split win is
kind-specific margin-pattern knowledge, and it does not survive
leave-kinds-out. **Honest failure note:** with ~52 skeletons in
the pool, a 50-feature router has more than enough capacity to
learn "what margins look like on kind X" instead of "which
member is trustworthy", and the group split says that is largely
what it did. Promising ceiling, unproven generalisation.

## Approach 4 (bonus) — Stacking on margin summaries

**Mechanism.** Multinomial logistic regression (same numpy
softmax trainer) directly to the 6 verdicts, over 25 margin
summaries only: per class routed / mean / max margin,
mean probability, vote count. A 5-fold out-of-fold pass over the
fit split is reported as a sanity estimate; the judged stacker
is refit on all of fit.

**Judge results (primary, n=310): 0.7710** (fit OOF 0.6794 —
fold models train on 4/5 of fit at half the epochs, so OOF
understates the refit model here). **Group split: 0.5563**
(fit OOF 0.8492 — the overfit signature in one line: it
memorised its fit kinds and lost to every baseline on unseen
kinds). Same disease as the router, less interpretable.
Reported for completeness; not a candidate.

## Summary table

| approach | primary judge (n=310) | group judge (n=320) | vs routed (same split) |
|---|---|---|---|
| routed baseline | 0.6742 | 0.6250 | — |
| mean-probability baseline | 0.6806 | 0.5938 | +0.006 / −0.031 |
| 1. confidence routing (τ\*=12) | **0.6968** | **0.6531** | **+0.023 / +0.028** |
| 2. calibrated voting | 0.6258 | 0.5312 | −0.048 / −0.094 |
| 3. feature router | 0.8032 | 0.5813 | +0.129 / −0.044 |
| 4. stacking | 0.7710 | 0.5563 | +0.097 / −0.069 |
| oracle (bound) | 0.8871 | 0.8594 | — |

## Closing — what deserves promotion, and what it would take

**Nothing here is promoted, and only one approach earns a next
step.**

- **Approach 1 (confidence routing) is the only rule that beat
  its baseline on both splits**, with a mechanism too simple to
  be memorising kinds (one threshold over an existing margin,
  fallback = today's serving rule for ~89–96% of inputs). It is
  a *candidate for a validation step*, not for serving. What it
  would take: (i) re-fit τ on a freshly generated dream pool
  (new seed, same generators) and confirm the gain survives —
  pick τ from the 8–12 plateau by fit score rather than the
  grid point-max, to cut tail variance; (ii) a per-class
  no-regression check on that fresh judge, swapped-operands and
  mutable-default named explicitly; (iii) only then implement
  it as a config-gated override in the composer and put it
  through the normal battery gate as a serving change (that
  edit belongs to whoever owns `serve.py` / `composers.py` —
  not this research).
- **Approach 3 (router) has the highest ceiling and a failed
  generalisation test.** Do not promote. Revisit only if the
  training material gains real kind diversity (more generator
  families, not more draws of the same ~52), with group-disjoint
  validation built into the experiment from the start. If a
  future router holds ≥ routed on a kind-disjoint judge *and*
  keeps most of its in-distribution gain, it becomes the
  interesting candidate — the 0.887 oracle says selection, done
  right, is worth ~+0.2 over today's routed rule.
- **Approach 2 (calibrated voting): reject as formulated.**
  Binary Platt scaling actively damages the multiclass gate
  (mutable-default recall 0.0). A multiclass-aware variant
  (scale, then jointly refit per-class offsets on fit) is
  legitimate future work but is a new prototype, not a fix to
  ship from these numbers.
- **Approach 4 (stacking): reject.** Same overfit as the router
  with less interpretability and no advantage over it anywhere.

And the standing caveat for whoever picks this up: no
composition rule measured here fixes swapped-operands (best
recall anywhere: stacking's 0.4651 on the primary split, 0.3043
on the group split). The oracle shows the right answer is
usually *present* in some member's margins — but for
swapped-operands it usually is not. That class needs member-side
work (data or surgery), not a cleverer vote.
