# Weights-Reader v2 — Report

Directive (Arnav, 2026-11-11): "make more training data, make it dream
with the harder things, make it better." Pre-registration: PREREG-V2.md
(locked before any v2 data; 3 amendments logged, all data-integrity
fixes found by measurement, none moving a bar). Every bar below is
scored exactly as pre-registered. Sanity arms reproduced v1's numbers
to the third decimal on all three frozen home exams (HV1 verdict
0.7257 vs v1 0.726; HMAP pooled 0.204 vs 0.204; coordinator score R²
−1.223 vs −1.223), so v2-vs-v1 comparisons are apples-to-apples.

## 1. Corpus built (all labels construction-known or measured)

**Zoo (new, self-generated, verified)** — `v2data/`:
- 360 base models: 6 lineages (deep-relu, wide-tanh, res-relu,
  glu-relu, randfeat, ternary) × 4 tasks (sparse, blobs, bucketed-count,
  smooth) × 15 seeds. Each base actually trained (numpy, gradient-checked)
  and its accuracy measured on a frozen 500-sample exam per task.
  288 train-pool bases, 72 frozen exam bases (seed % 5 == 4; their edits
  never entered reader training).
- 4,102 train-pool edit items + 336 frozen exam items + 348 post-hoc
  hard-exam items: 8 edit kinds (zero/scale/noise/prune-layer,
  permute-trap, swap-layers, quantize-int8, quantize-ternary,
  retrain-brief) × subtlety 0/1/2. Every label measured: accuracy
  before/after on the task exam → verdict (±0.02), score_after, delta;
  planted layer and edit kind known by construction. Probe maps
  (grad/knock/norms) computed from the edited weights. Features:
  v1 featurizer tokens + reader dict, delta tokens vs the base,
  internals-format case dict.
- Trap integrity verified by measurement: all 136 permute-traps measure
  Δ = 0.000 exactly. One real bug was caught by measurement pre-launch:
  permute-traps are NOT function-preserving in residual models
  (Δ = −0.348 observed); fixed and hard-asserted in the generator
  (amendment A3).
- 1,152 control entries: per train base, the original + 3 twins
  (element shuffle, spectrum transplant, moment-matched Gaussian).

**Reused**: v1 home track (1,945 items, frozen splits), v1's local
public features (29 models). The 201 GB public corpus on ashp was NOT
used (laptop unreachable); public numbers come from v1's featurized
files, plus fresh twins of SmolLM2-360M built from local raw weights.

## 2. Architecture change

v1's named flaw — pooled features destroy position — addressed with a
positional readout: per-layer token sequences resampled to 16 positions
per channel + per-channel argmax position + sequence length, in three
blocks: FULL (all 72 channels), STRUCT (spectral channels only:
log-sigma1 + stable rank), and delta-sequence variants (edited − base).
Probe maps got the same treatment. The v1 pooled reader is kept as the
control arm everywhere. Reader model class unchanged (HGB, v1
hyperparameters) so differences are features/data, not the learner.

## 3. Dream rounds (Ripple-style, per Arnav's doctrine)

Loop: evaluate → harvest worst slices → generate concentrated harder
data → retrain → re-measure on the SAME frozen exam. s1 rule applied:
solved kinds (permute-trap, quantize-int8, both 1.000 at stage 0) were
deprioritized — int8 removed from both dream menus entirely, trap kept
as a single anchor slot; freed mass went to subtle defects.

Stage-0 worst slices (W_FULL reader): glu-relu family 0.674, count
task 0.735, noise-layer 0.717, quantize-ternary 0.762, scale-layer
0.776, zero-layer 0.783.

**Round 1** (1,390 items, subtlety-1 zero/scale/noise/prune):
frozen std exam verdict W_FULL 0.833 → 0.827; W_STRUCT 0.786 → 0.801;
score R² 0.637 → 0.668. Targeted slices moved as aimed: scale-layer
0.776 → 0.837, zero-layer 0.783 → 0.848. noise flat (0.717),
quantize-ternary down (0.762 → 0.714), glu down (0.674 → 0.652).

**Round 2** (1,379 items, subtlety-2 + compounds of menu kinds):
verdict W_FULL 0.827 → 0.813; W_STRUCT 0.801 → 0.807 (monotone across
both rounds); score R² 0.668 → 0.664. Round-1 slice gains partly gave
back (scale 0.837 → 0.796, zero 0.848 → 0.804).

**Post-hoc hard exam** (348 subtle items on frozen exam bases,
generated after the std results; labeled supplementary, not a bar):
dream-trained vs round-0-trained reader — verdict W_FULL 0.830 →
0.844, W_STRUCT 0.801 → 0.841. Dreaming bought hard-distribution
accuracy (+1.4 / +4.0) at a small std-exam cost (−2.0 on W_FULL).
That trade is the honest summary of the dream loop on verdicts.

**Dominant-layer anomaly (diagnosed, not explained away):** zoo
planted-layer W_FULL: 0.931 (stage 0) → 0.399 (stage 1) → 0.601
(stage 2); on the hard exam 0.894 → 0.554. Ablations: round-0-only
pool = 0.931, round-1-only pool = 0.931, ANY mixture ≤ 0.40
(r0+r1 0.399; r0+r1-subtle0-only 0.251); on the mixture every single
feature block collapses too (DSEQ 0.409, SEQ 0.325, DIST 0.419).
The failure is in the data mixture, not a feature block and not
either pool. Mechanism unidentified — named v3's top question
(§6). MAPS arm was immune (0.576 → 0.571 → 0.611) and MAPS+W
concatenation was bad throughout (0.512 → 0.571 → 0.207): do not
concatenate probe-map and weight blocks in one HGB.

## 4. Results vs pre-registered bars

| Bar | v1 | v2 | Verdict |
|---|---|---|---|
| B1 edit verdict, HV1 exam | 0.726 | arm a (v1 recipe) 0.726; arm b (+zoo) 0.720; arm c (zoo only) 0.480 | **NOT BEATEN** |
| B2a verdict zoo→coordinator adapters (n=11) | 0.273 | DIST 0.273; FULL 0.364 | **PASS** (marginal; 4/11 vs 3/11, above chance 0.33 by one item) |
| B2b score R² → coordinator | −1.223 | −1.386 | **NOT BEATEN** (zoo data hurt; home-only control reproduces −1.223) |
| B2c within-zoo score R² (aim > 0) | n/a | 0.637 → 0.668 → 0.664 by stage | **PASS** |
| B3 dominant layer, HMAP exam | 0.204 (instrument 0.736) | SEQ 0.257; SEQ+POOLED 0.309 | **PASS** |
| B3-ref zoo planted layer | (v1 pooled position-blind) | 0.931 single-pool; mixture-degraded (see §3) | PASS with warning |
| B4 public LOFO layers R² | −0.170 | −0.475 | **FAIL** (more negative) |
| B4 public LOFO hidden R² | −1.005 | −1.580 | **FAIL** |
| B4 public LOFO log-params R² | −2.115 | −1.668 | PASS (less negative) |
| B5 controls v2 | FAIL (v1) | **FAIL** (detail §5) | **FAIL** |
| B6 secondary: bvi / quant (LOFO) | 0.500 / 0.931 | 0.700 / 0.897 | bvi PASS, quant slight miss |

Zoo internal (not barred): family ID 0.986 on unseen bases; zoo LOFO
config — depth R² = +1.00 for 4 of 6 held-out families (the sequence
reader CAN count layers cross-family inside the zoo; deep-relu 0.15,
wide-tanh −2.0), width R² negative for 5 of 6 (width does not
transfer). Public LOFO shows the counting does not survive real-LLM
featurization differences at n=29 (B4 layers fail above).

## 5. Controls v2 (B5) — FAIL, with a decomposition that matters

Locked criterion: STRUCT-block twin/original true-family probability
ratio ≤ 0.5 averaged over ≥3 sources AND authenticity head ≥ 0.80 on
held-out sources.

- Zoo sources, STRUCT ratio **0.990** — no degradation. DIST 0.818,
  FULL 0.814. Authenticity: STRUCT 0.747 (fail), FULL 0.830 (pass).
- Public source (SmolLM2-360M, v1 protocol): DIST reproduces v1's
  disease (shuffle 0.999, permuted 1.000, moment 0.989 vs orig 1.000).
  STRUCT: shuffle **0.248** (ratio 0.25), moment **0.423** (ratio
  0.42), permuted 0.999 (spectrum-preserving by construction — the
  spectral block seeing through it is expected, not a leak).
- Why zoo STRUCT fails while public STRUCT passes: zoo "families" ARE
  architectures (depth/width/residual pattern), and all three twin
  transforms preserve architecture exactly — the structural block is
  legitimately reading architecture there. The control conflates
  family-as-architecture with family-as-weight-structure on the zoo;
  on the public model, where family must be read from weights, the
  structural block degrades properly under shuffle and moment twins.
- Verdict stands as pre-registered: **FAIL** — the criterion was not
  met, and the pooled/distributional read (v1's disease) is unchanged.

## 6. What shipped, what didn't, what v3 needs

**Shipped (beat their bar):**
- The v2 verified corpus (zoo bases/edits/twins + frozen exams) —
  reusable training/eval infrastructure, all labels measured.
- HMAP dominant-layer reader: SEQ+POOLED 0.309 (was 0.204).
- Coordinator-verdict transfer arm with FULL features: 0.364
  (was 0.273; marginal, n=11 — treat as a lead, not a capability).
- Within-zoo consequence reading: verdict 0.833 (stage-0 W_FULL),
  score R² 0.664, planted-layer 0.931 (single-pool training only).
- Public bvi read 0.700 (was 0.500); log-params LOFO improved.

**Did not ship (losses, kept as measurements):**
- Zoo data does NOT improve the HV1 edit verdict (0.720 < 0.726) and
  does not transfer alone (0.480). More data, wrong substrate.
- Cross-substrate score prediction still fails (−1.386); consequence
  transfer remains the open problem v1 named.
- Public cross-family config regression: sequence features made
  layers/hidden WORSE at n=29 (variance), log-params better.
- Controls v2 fails as locked; the distributional family read is
  still there in DIST/FULL blocks.
- Dream curriculum on the full feature block trades std-exam accuracy
  for hard-exam accuracy; and the domlayer mixture pathology
  (0.931 → 0.399 on mixing two individually-perfect pools) is
  unexplained — the single most important anomaly in v2.

**v3 needs:**
1. Diagnose the mixture pathology first (prime suspect class:
   near-duplicate cross-round items whose positional signatures
   collide at HGB binning resolution; test with a torch sequence
   model and with per-round calibration heads).
2. Public-corpus extension when ashp returns (201 GB, 29+ models
   featurized fresh + behavior labels) — B4 is starved at n=29.
3. A verified behavior-label corpus for the public track (v1's Arm-1
   gap persists: 11 verified labels is not a training set).
4. Consequence transfer needs paired-delta training ACROSS substrates
   (same edit family applied to adapters AND zoo nets), not more
   within-substrate data — B1/B2b both say the boundary is substrate,
   not volume.
5. Controls v3: define family identity excluding architecture
   (within-architecture lineage twins) so the zoo control measures
   weight structure, not shape.

Files: PREREG-V2.md, v2zoo.py, v2gen.py, v2reader.py, v2eval.py,
v2controls_public.py, v2diag_dom.py, v2diag_dom2.py, v2hardexam.py,
v2data/, results_v2.json (+ per-section results_v2_*.json, diag_dom*.json,
results_v2_hardexam.json).
