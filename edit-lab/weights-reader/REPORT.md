# Weights-Reader Pilot — Report

*2026-11-10. Side lab: `~/workspace/edit-lab/weights-reader/`. The big models are
DATA, never inference — no downloaded model was ever run; only its weight files
were read. Pre-registered gates are in `README.md`; every number below is
held-out under the split stated next to it.*

## The question

The internals surgery round proved its hand-crafted fingerprint instrument was
the ceiling (the ternary scorer sat exactly at its probe's 0.744). This pilot
asks whether a **learned** reader over raw-weight-derived features beats that
instrument — and, in Arnav's AlphaFold framing, whether *function* (what a
model is, what it can do, what an edit did to it) is readable from *structure*
(the weights alone).

## The reader

Per matrix: Frobenius norm, top-16 singular values (bounded randomized SVD,
≤1024² submatrix, float32), stable/effective rank, value quantiles, skew,
kurtosis, zero fraction, sampled unique-value fraction, histogram entropy,
row/col norm statistics. Per layer these become 72-dim tokens (8 statistics ×
8 role slots: q/k/v/o/gate/up/down/experts + layer aggregate), pooled across
layers (mean/std/min/max/early/late/slope) into a 512-dim model vector.
Quantized checkpoints are dequantized first (GPTQ/AWQ paths unit-verified
against reference dequantization after a real bug was found and fixed — see
"Instrument bugs" below; MXFP4 is sampled-decoded and flagged approximate).
The reader itself is gradient boosting over the pooled vector; the baseline —
the bar — is the internals-style ~20-number global fingerprint + a linear
model, on identical splits.

---

## Home track — our own models, our own measured consequences (COMPLETE)

1,945 items mined from the lab: every (weights, measured outcome) pair we have
ever produced — coordinator repair family, internals constructed nets + probe
maps, hive adapters, coding-swarm specialists, tiny-hive members. Sealed sets
respected: the internals real exam was never read; coordinator outcomes are
recorded labels only.

| Task | Split | Learned reader | Baseline / reference | Verdict |
|---|---|---|---|---|
| Edit verdict (HELPS/HURTS/INERT), internals-constructed | their train/held-out (490/175) | **0.726** | hand fingerprint 0.663; majority class 0.480 | **reader wins +6.3** |
| + gold-regime family added to training | same test | 0.709 | — | more home data **hurt** (−1.7): the gold regime's prior (72% HURTS) shifted the boundary |
| Edit verdict transferred to coordinator adapters | train maps → test adapters | 0.273 | chance ≈ 0.33 | **no transfer** across substrates |
| **Edit-kind identification** (which edit made this delta: scale / retrain-thin / synth-retrain / surgery-drop / other) | leave-one-out, n=19 | **0.789** | chance ≈ 0.2–0.35 | **strong read** |
| Specialist niche identification (swarm) | leave-one-out, n=20 | **0.800** | — | **strong read** |
| Absolute score prediction | train swarm+models → test coordinator | R² **−1.22** (MAE 0.091) | — | **fails**: scores don't transfer across families |
| Map read: has a dead layer | their split (451/152) | 1.000 | — | perfect (near-trivial: the answer sits in first-order map statistics) |
| Map read: WHICH layer dominates | same | 0.204 | internals instrument 0.736 | **fails**: pooling destroys position |

**What the home track says.** The reader is a good *attribution* instrument and
a poor *consequence* instrument. What a thing **is** (which niche, which edit
kind) reads clearly from weight statistics. What an edit **will do** reads
within the regime it was trained on (+6.3 over the hand instrument on
constructed edits) but does not cross substrates (maps→adapters: chance;
scores across families: worse than the mean). And one read is positional, not
statistical: dominant-layer identification needs the per-layer vector itself —
pooled summaries structurally cannot answer it, which is exactly the
internals round's lesson from the other side.

### Part-specialist team (Arnav's together-but-separate arm)

Separate trunks per feature-anatomy block (grad / knock / norms / meta),
shared architecture, frozen seeded projections to a common input, trained on
the same verdict task (n=850 train / 175 held-out), against the pre-registered
adoption bar (≥ +3 pts over the single reader, no headline task lost by >2):

| Arm | Accuracy |
|---|---|
| MONO single reader (HGB) | **0.726** |
| MONO single reader (MLP) | 0.686 |
| Team, output-averaged (SHR / IND) | 0.629 / 0.623 |
| Team + consultation stacker (in-sample; optimistic) | 0.674 / 0.651 |
| W1 swapping (learned pick of one trunk) | 0.646 / 0.646 |
| W2 gated weight mixture | 0.623 / 0.566 |
| W3 uniform weight soup | 0.623 / 0.549 |

**Adoption bar failed by every arm — the part-team does not ship**, the same
outcome as internals Phase 5 (composition lost to singles). Two MoE-lab priors
were tested, not assumed: (a) weight-space composition degrades far less under
**shared-init breeding** — soup 0.623 vs 0.549, gated 0.623 vs 0.566, SHR vs
IND — the prior **replicates** in this domain; (b) the MONO anchor held — no
composition beat the single reader, and the single reader itself (0.726)
remains the best verdict instrument we have.

### Surgery arm (Arnav: "surgery on your own models that we just trained")

The lab protocol (validation-only knockout maps → indictments → greedy
guarded edits → one held-out confirm; ship only on ≥ +0.5 pt) run on the
freshly trained readers:

| Subject | Indicted | Applied | Val Δ | Held-out Δ | Verdict |
|---|---|---|---|---|---|
| Single reader (MLP) | 0 | 0 | — | 0.000 | null |
| Trunk: grad | 0 | 0 | — | 0.000 | null |
| Trunk: knock | 0 | 0 | — | 0.000 | null |
| Trunk: norms | 5 | 3 | 0.801→0.816 | **0.600→0.611 (+1.1)** | **SHIPPED** |
| Trunk: meta | 0 | 0 | — | 0.000 | null |

**The contrast with the internals round is the finding.** On constructed-data
specialists, surgery found zero shippable edits in every subject and the
defects proved to live in the data protocol and the instrument. On freshly
*trained* models, 1 of 5 subjects carried real, editable, training-born
defects — three harmful units in the norms trunk, removed for a measured
held-out gain. Small (n=175, ≈2 net cases) and reported as such — but the
direction matches the directive's premise: surgery's proper subject is a
trained model, not a constructed one.

### Masked weight modeling (AlphaFold-style representation bet)

Self-supervised pretraining (mask whole feature groups, reconstruct;
final masked-recon MSE 0.036 — it learned feature structure) then fine-tune
with the embeddings appended: verdict 0.709 = 0.709 (tie), dominant-layer
0.204 → 0.171 (worse), has-dead 1.000 = 1.000. **0 of 3 wins against the
pre-registered majority bar — pretraining does not transfer at this scale.**
AlphaFold learned from millions of solved structures plus physics; we have
1,945 solved items and no physics. The analogy's honest limit is the
data-scale gap, and this arm measured it.

---

## Public track — the open-weight corpus (COMPLETE)

**Corpus as landed: 29 models featurized, 201.1 GB on disk, 10 families**
(qwen, qwen3, llama, mistral, phi, olmo, pythia, smollm, deepseek,
gptoss) — full manifest with repos, licenses, forms and per-model sizes in
`manifest.csv`. Full entries: all 23 small-tier models + Qwen3-4B +
gpt-oss-20b (full MXFP4). Sampled partials: DeepSeek-V2-Lite (shards 1–2/4,
15 of 27 layers), Llama-3.1-70B-Instruct-AWQ (shards 1/5/8/9 of 9, 27
layer-blocks), Qwen3-30B-A3B (4 of 16 shards, 13 of 48 layers). Six
frontier items were **excluded-by-cap** when the corpus hit 201.1 GB
(Kimi-K2, gpt-oss-120b, Moonlight-16B, Qwen3-235B-A22B, Llama-4-Scout,
DeepSeek-R1); Gemma 2/3 remain **blocked-by-gate** (no legitimate ungated
route used). DeepSeek was held out of every training pool — it is the
unseen-family exam.

**Census sanity (the pipeline proof):** layers present in the featurized
features match the published config layer count **exactly for all 26 full
models** (gpt-oss-20b 24/24, Coder-32B 64/64, Mistral 32/32, …), and the
three partials show exactly the layers their downloaded shards contain.
The pre-registered STRUCT regression check (R² = 0.002) is **not** a valid
pipeline proof as implemented — a tree regressor cannot extrapolate layer
counts beyond its training range on a 29-item set, so it collapses to the
mean; the census table replaces it as the sanity evidence.

### Headline: leave-one-family-out (LOFO) vs the hand-crafted baseline

| Task | Learned reader | Hand baseline | |
|---|---|---|---|
| base-vs-instruct (acc) | **0.500** | 0.450 | reader +5.0 |
| quantization class (acc) | 0.931 | 0.931 | tie |
| layers (R²) | **−0.170** | −2.530 | reader far less wrong |
| hidden size (R²) | **−1.005** | −6.545 | reader far less wrong |
| log-params (R²) | **−2.115** | −5.244 | reader far less wrong |

**Pre-registered gate: reader wins ≥4 of the LOFO task set → 4 of 5 —
PILOT GATE PASSED (WIN).** Read the regression rows honestly, though:
every R² is negative for *both* models — on a truly unseen family, nobody
can predict layer counts, hidden sizes, or parameter counts from weight
statistics (worse than predicting the mean). The reader's win is real but
relative: it is consistently much less wrong than the hand instrument.
Base-vs-instruct transfers weakly for everyone (both score 0.0 on the
DeepSeek and Qwen3 folds; the reader's +5 comes mostly from one Mistral
fold). Quantization is the one genuinely readable property cross-family
(0.931 both) — except MXFP4: both fail the gpt-oss fold (0/1), a quant
class neither had seen.

Random splits (secondary, n=29 so folds are ~9 items): family-ID reader
0.333 vs baseline 0.458 (**reader loses**), bvi 0.400 vs 0.333 (reader),
quant 0.750 vs 0.833 (**reader loses**), layers R² −2.17 vs −13.06
(reader less wrong). At this n these are noise-dominated; LOFO is the
headline by pre-registration.

### Probes (measured; they do not move the gate)

- **Size generalization** (train ≤8B → test big/frontier): bvi accuracy
  **0.0** — fails outright. Layers R² 0.157, MAE 16.9 layers — with a
  measurement caveat: for the three partials the target is the *full*
  model's config layer count (e.g. 80) while the features contain only the
  downloaded layers (27); no reader could pass that as posed. As posed,
  the probe says the ≤8B-trained reader does **not** read far-bigger
  weights — Arnav's key question gets a **no, not yet**.
- **Generation shift** (Qwen2.5 → Qwen3): bvi not runnable (Qwen3 items
  carry no base/instruct contrast labels); layers R² −1.56, MAE 7.5.
- **Frontier exam**: gpt-oss-20b is the sole landed frontier entry;
  its LOFO folds are the exam as-run (quant 0/1 both, bvi fold n=1 in the
  qwen3/gptoss folds above). The dedicated frontier probes returned null
  (single-item test set).

### Arm 1 — behavior-profile prediction (the "folding" task)

**Inconclusive by data, not by reader.** Verified per-domain eval labels
exist for only 11 model-domain pairs spread over single-family clusters
(MMLU n=5, GSM8K n=5, HumanEval n=4, BBH n=2); every LOFO fold collapsed
(train side left with <2 classes), so no reader number exists. Majority-
class controls: MMLU 0.60, GSM8K 0.80, HumanEval 0.50. The claim
"function from structure" is therefore carried by the **home track**
(measured consequences on our own models), where it partially holds —
see above. The AlphaFold analogy's limit is exactly this: AlphaFold had
millions of solved structures; we have 29 public entries, 11 with verified
behavior labels, and 1,945 home items.

### Controls (pre-registered gate: NOT passed as specified)

Controls were built from SmolLM2-360M only (a design weakness — one
source family). The family classifier's argmax prediction is **unchanged
('smollm') on shuffled, random-init, and permuted controls** — semantic
predictions do *not* degrade toward chance, so the controls gate fails
as written. The feature-level picture explains why: pooled features are
mostly value-distribution statistics, which are shuffle-invariant *by
construction* (median relative drift under shuffling: 0.002). The
structure-sensitive spectral block does respond — under shuffling, 28%
of features move >10% (p90 drift 0.87); under random-init, 47% move
(median 0.068, p90 4.1×). Permutation drift is small as designed (median
0.0018 — invariance holds at the median; 13% of features move >10%, the
row/col-coupled statistics). Lesson folded into v2 below: in this
feature design, "family" is largely a distributional signature, not a
structural one — a reader that must fail on destroyed structure needs
spectral/positional features to carry more of the vote, and controls
from ≥3 source families with a probability-based degradation metric.

## Instrument bugs found by this pilot (fail-closed value)

1. GPTQ dequantization was wrong twice: qzeros unpacked along the wrong axis
   (hard broadcast failure on Mistral-GPTQ) and `_unpack_int4`'s bare reshape
   scrambled element order for axis-0 unpacks (silent — would have poisoned
   every GPTQ spectrum). Both fixed; both dequant paths now unit-verified to
   ~1e-6 against reference dequantization. AWQ features produced earlier are
   unaffected (its packed axis was already last; verified identical).
2. The first featurizer's full-precision 2048² SVDs made featurization
   ~10–60 min/model; bounded to 1024² float32 randomized spectra.
3. sklearn HGB binning crashes on train columns that are entirely NaN (union
   feature spaces across substrates) — the harness now drops dead columns
   per split.

## Featurization cost (the price of "bigger books")

Total: **8,844 s ≈ 2.46 h for 29 models** on ashp's CPU (median 118 s per
model; per-model seconds for every entry are in `manifest.csv`). The big
books cost real time: Qwen2.5-Coder-32B-AWQ 1,608 s; Llama-3.1-70B-AWQ
partial 1,117 s; Qwen3-30B-A3B partial 610 s; DeepSeek-V2-Lite partial
580 s (~2,800 matrices incl. experts); gpt-oss-20b 467 s. Small models run
33–200 s. Featurization cost scales with matrices × matrix size, not with
parameter count alone — MoE partials are disproportionately expensive per
GB because every expert is a separate matrix.

## Verdict

**Public gate: WIN, narrowly and relatively.** The learned reader beat the
hand-crafted baseline on 4 of 5 pre-registered LOFO tasks (quantization
tied) — the pilot's central claim survives: a learned reader over
raw-weight features **is** a better instrument than the hand-crafted
fingerprint that capped the internals round. But the absolute numbers
bound the claim hard: cross-family architecture regression is negative-R²
for *everyone* (the reader is less wrong, not right), base-vs-instruct
barely transfers, and the size-generalization probe fails as posed — a
reader trained on ≤8B weights does **not** read 20–70B weights. The
**controls gate failed as specified** (family predictions survive weight
shuffling — family is a distributional signature in this feature design).
Home-track verdict: the learned reader **beats the hand-crafted
instrument** where the task is statistical (edit verdict +6.3, attribution
reads 0.79–0.80), and the claim survives only in that bounded form: it
reads *what a thing is* and *what was done to it* far better than it reads
*what will happen* — consequence prediction does not transfer across
substrates, composition does not beat the single reader, surgery found
one small real edit in freshly trained models (vs zero in the internals
round), and pretraining does not transfer at n≈2k.

## What v2 needs

1. **Per-layer token sequence model** (the design's deferred half): the
   dominant-layer failure is a pooling artifact; a set/sequence reader over
   the 72-dim layer tokens is the direct fix and the honest test of the
   "sequence model over weights" idea.
2. **More solved structures**: consequence reads need (weights → measured
   outcome) pairs in the thousands per substrate, not hundreds — the home
   track's transfer failures are data-scale failures first.
3. **Paired deltas as first-class inputs**: edit identification (0.79) worked
   from delta statistics; consequence prediction should train on
   (base weights, delta, outcome) triples within one substrate at a time.
4. Frontier-tier reads stay exam-only until a reader passes the ≤72B gates.
5. **Controls v2**: build shuffled/random controls from ≥3 source families
   and score *probability* degradation, not argmax — and rebalance the
   feature vote toward spectral/positional statistics so destroyed
   structure actually moves predictions (the pilot's controls gate failed
   because family identity here is distributional).
6. **Arm 1 needs a verified-label corpus**: per-domain bands for ≥30
   models across ≥6 families, sourced from papers/leaderboards (not card
   scraping — it proved unreliable); without it the "folding" task cannot
   be examined at all.
7. **Size probe, posed fairly**: score partial entries against the layers
   actually present (the census the reader can see), and add mid-size
   rungs (13B/24B/32B dense) so "reads bigger than it trained on" is
   tested on a ladder, not a cliff.
