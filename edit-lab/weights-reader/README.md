# Weights-Reader Pilot — design and PRE-REGISTERED gates

Written 2026-11-10 (v1 gates registered before any featurization or
training; scope additions of 13:17–13:24 PT appended the same day, still
before any training — they extend the registration, they do not move
v1's bars). Results will be reported against these gates as-is,
losses included.

## Question

The internals surgery round (../internals-specialist/SURGERY.md) concluded
that the hand-crafted fingerprint instrument was the ceiling (the ternary
verdict model sat exactly at its probe's 0.744 ceiling). This pilot tests
the direct answer: **can a LEARNED reader over raw-weight-derived features
beat a hand-crafted fingerprint baseline at reading what a model is from
its weights alone?** The big LLMs are data, never inference — no corpus
model is ever run; only its weight files are read.

## Corpus — public track (weights only, safetensors; ashp D:\muse\data\weight-corpus)

Disk reality governs: ashp D: measured **220.9 GB free** on 2026-11-10.
Hard cap in the downloader: **208 GB** (≥12 GB margin kept). Forms are
honest per entry: full / full-quantized / sampled-partial (embeddings +
early/mid/late layer-band shards chosen from the repo's own
model.safetensors.index.json; exact shards logged in the manifest).
~199 GB expected for the committed list; stretch items download only
if the running total leaves room.

**Small tier (training core, all full reads; 25 items, 7 families):**
- **qwen** (Qwen2.5; Apache-2.0, 3B under Qwen license): 0.5B, 0.5B-Instruct,
  1.5B, 1.5B-Instruct, 3B-Instruct, 3B-Instruct-GPTQ-Int4, 3B-Instruct-AWQ
- **llama** (Llama community licenses; unsloth mirrors of identical
  weights — meta-llama repos are manual-gated, no HF token): Llama-3.2-1B-
  Instruct, 3.2-3B, 3.2-3B-Instruct, 3.1-8B-Instruct-AWQ-INT4 (hugging-quants)
- **mistral** (Apache-2.0): Mistral-7B-Instruct-v0.3, Mistral-7B-Instruct-
  v0.2-GPTQ (TheBloke)
- **phi** (MIT): phi-2, Phi-3-mini-4k-instruct
- **olmo** (Apache-2.0): OLMo-2-0425-1B, OLMo-2-0425-1B-Instruct
- **pythia** (Apache-2.0): pythia-1.4b final, pythia-1.4b @ step3000
  (intermediate checkpoint), pythia-410m
- **smollm** (Apache-2.0): SmolLM2-1.7B-Instruct, SmolLM2-360M, 360M-Instruct

**Big / frontier tier (exam-leaning; forms noted):**
- Qwen3-4B (full, Apache-2.0) — Qwen3 low end; generation-shift anchor
- Qwen2.5-Coder-32B-Instruct-AWQ (full-quant, Apache-2.0) — capability-
  specialized sibling: does the reader see "coder" in the weights?
- openai/gpt-oss-20b (full MXFP4 root shards only — the repo also carries
  a bf16 `original/` copy, deliberately not downloaded; Apache-2.0)
- deepseek-ai/DeepSeek-V2-Lite (sampled-partial, 2 of 4 shards: embed/
  head/early + late band) — **the deepseek family is HELD OUT entirely
  as an unseen-family exam set** (decision logged per Arnav's option)
- Llama-3.1-70B-Instruct-AWQ-INT4 (sampled-partial, 4 of 9 shards:
  embed + mid + late + lm_head)
- Qwen3-30B-A3B (sampled-partial, 4 of 16 shards: embed + L25 + L50 +
  last) — Qwen's MoE class
- moonshotai/Kimi-K2-Instruct (sampled-partial, 2 of 61 shards: shard 1
  = embeddings + layer 0; shard 31 = layer-30 band; modified-MIT license;
  ~1.9% of shards, ~2% of parameters — stated plainly, not rounded up)
- openai/gpt-oss-120b (sampled-partial, 3 of 15 MXFP4 shards: embed/head
  + L0 + L50 bands)

**Stretch (space-gated, in this order):** Moonlight-16B-A3B partial,
Qwen3-235B-A22B partial, Llama-4-Scout partial (unsloth bf16), DeepSeek-R1
partial. Each downloads only if cap headroom ≥ its size + margin.

**Excluded, with reasons (never silent):**
- excluded-by-space: Qwen2.5-32B (no official AWQ; BF16 65.5 GB doesn't
  fit — Qwen3-32B-AWQ also yielded to Coder-32B-AWQ for the same slot),
  Qwen2.5-72B-Instruct-AWQ (Llama-70B partial fills the 70B slot),
  DeepSeek-Coder-V2-Lite, Moonlight-Instruct, Mistral-Small-24B (94 GB
  on disk — does not "fit cleanly"), Mistral-Large-2411, GLM-4.5/4.6,
  MiniMax-M2, Llama-4-Maverick, DeepSeek-V3 (R1 covers the family as
  stretch), Qwen2.5-7B, Mistral-7B-v0.3 base, and the small-tier trims
  (Qwen2.5-3B base, Llama-3.2-1B base, SmolLM2-1.7B base — one base/
  instruct pair per family retained at another size).
- blocked-by-gate: Gemma-2-2b/-it and Gemma-3-27b-it (Google manual
  license gate, no token; ungated mirrors exist but were NOT used for
  Google models — the mirror route was sanctioned for Llama only).
- LoRA adapters as a public-corpus variant class: still not included
  (no clean licensed set verified); adapters DO enter via the home
  track below, where they are ours.

**Controls** (computed at featurization time, no extra storage):
(a) element-shuffled copy of a real model — same values, destroyed
structure; (b) synthetic random-init tensors with a real model's shapes.

## Corpus — home track (our own lab's weights + OUR measured outcomes)

Mined from ~/workspace/edit-lab and the hivemind-muse clone. Every item
pairs weights with a consequence WE measured (lineage.jsonl is the index):
coordinator repair family (base, thin-r2/r4/r16, orig-rejected,
surg-drop14/15/23/27, coord-soup50, synthv1-r2/r4/r16, dose arms
coord-s25/50/75, res-*), internals specialist (constructed nets with
planted truth, probe maps, T1–T4 + t3_regime + t3_consult + ternaries,
historical gate decisions), hive brain LoRAs (browser kept 0.43→0.79;
coordinator/researcher rejected; verifier/writer/order_reader), coding
swarm specialists (v1s, Phase B v2s, v3, ternary secret-line, bug-*
family) with held-out/battery scores and v1→v2 deltas, tiny-hive
constructed specialists (exhaustively verified), weight-moe-lab experts
(IND/SHR arms + shell outcomes).

Home tasks (consequence-reading): (H1) outcome class from weights
(+maps where available) — HELPS/HURTS/INERT-style verdicts and
kept/rejected gate outcomes; (H2) score band prediction; (H3) identify
which edit was applied, from the weight delta. **Split discipline:
hold out entire experiment families** (e.g. train internals+swarm,
test coordinator family). Headline comparison, per Arnav's addition:
**does adding home data improve the reader on the shared task type
(edit-verdict) versus public-only training?** Sealed sets respected:
the internals real exam stays sealed; the coordinator test set is
spent — recorded outcomes are labels only, never re-run or tuned toward.

## Labels (metadata / model cards / published evals only — no inference)

family; variant (base / instruct / quant-gptq / quant-awq / mxfp4 /
checkpoint / coder); architecture from config.json (layers, hidden size,
heads, context length); parameter count from tensor census where the
entry is full, from config where partial (flagged); MMLU (published
value for that exact variant, source recorded per model in the
manifest) mapped to a band: **low <45, mid 45–58, high >58**.
Partial entries: labels are the model's own (config/card); features
come only from the shards actually read — the manifest states the
fraction for every partial entry.

## Features (from raw weight VALUES; numpy only)

Per weight matrix: Frobenius norm, top singular values (randomized SVD,
top-16 + tail energy), stable rank, effective rank, value quantiles,
skew/kurtosis, zero fraction, sampled unique-value fraction and histogram
entropy, row/column norm stats. GPTQ/AWQ tensors are dequantized first
(the statistics used are invariant to the pack-order column
permutation); MXFP4 tensors are unpacked via the FP4 LUT × block scales;
FP8 (if any) read as stored values. Per-layer tokens aggregate the
layer's matrices into fixed slots (q,k,v,o,gate,up,down + fused/MoE
expert-aggregate variants) with presence masks; model-level features
pool across layers (mean/std/min/max/early/late/slope over normalized
layer position). Partial entries pool over the layers actually read,
with a coverage feature recording which bands were present. **No
shapes, counts, or tensor names enter the reader's feature set** —
those live in a separate STRUCT set.

**Baseline (the bar)** — an internals-style hand-crafted fingerprint:
~20 global summary numbers only (global weight mean/std/kurtosis, mean
per-type Frobenius norms, mean stable rank, zero fraction, global
quantile spread; no per-layer resolution, no spectra beyond a global
σ1 mean) + a linear/logistic model. Same tasks, same splits.

## Tasks v1 (public track)

1. family identification — random split only (an unseen family is not a
   class the reader could name; claiming otherwise would be dishonest).
2. base-vs-instruct (binary; quant/checkpoint items excluded).
3. quantization detection (binary quant-vs-full; 3-way reported secondarily).
4. architecture regression: layers, hidden size, log10(params) —
   reported under STRUCT features as a pipeline sanity (must be ~exact)
   AND under the reader's values-only features as the honest attempt.
5. benchmark band (3-class MMLU band) — stretch task.

## Splits and probes

(a) stratified random 70/30, 3 seeds; (b) **leave-one-family-out (LOFO)**
— **split (b) is the headline** for the public track.
(c) **Size-generalization probe**: reader trained ONLY on ≤8B full
entries, tested on the big/frontier tier's properties (variant, quant,
arch regression, band). This is the "can it read weights far bigger
than anything it trained on" test.
(d) **Generation-shift probe**: Qwen3 entries (4B full, 30B-A3B partial)
held out against Qwen2.5-trained readers.
(e) **Frontier exam**: big/frontier tier as exam material for readers
trained on the ≤72B corpus (overlaps (c); reported per entry).
(f) **Unseen-family exam**: deepseek (V2-Lite partial) never in any
training pool for headline numbers.

## Pre-registered gates

- **PILOT WIN** iff the learned reader beats the baseline on the
  **majority of the LOFO tasks** {base-vs-instruct, quant-binary,
  layers-R², hidden-R², logparams-R², mmlu-band} (≥4 of 6), regression
  compared on R², classification on accuracy.
- **Controls gate**: on shuffled/random-init controls, the reader's
  semantic predictions (family, base-vs-instruct) must degrade
  materially toward chance — otherwise it reads file artifacts, not
  structure, and the pilot FAILS regardless of headline scores.
  (Quant unique-value signals are exempt: they survive shuffling
  legitimately.)
- **Permutation sanity**: permuting rows/columns of every matrix in a
  copy must leave predictions ~unchanged (features are permutation-
  invariant statistics by construction; this verifies the code).
- **Probes** (c)–(f) are reported as measured, pass/fail against
  chance + baseline on the same entries; they inform the verdict but
  do not move the PILOT WIN gate.
- Losses reported plainly; per-fold LOFO numbers shown individually.
  n is small (≈30 public entries); this is a pilot, and its CIs are
  wide — stated, not hidden.

## Arm 2 — part-specialist reader team (after the single reader)

Per Arnav's together-but-separate pattern: separate small readers, each
owning one PART of the anatomy — embeddings/norms, attention (Q/K/V/O),
MLP (gate/up/down), layer-band (early/mid/late pooled views), and a
delta reader (home track only — public entries have no deltas) —
trained together (consultation inputs: each part-reader also sees the
other parts' summary scores) with separate weights, composing into one
verdict. Same exams/splits as the single reader.

**Alignment spec for composition arms:** every part-reader is an MLP
with an IDENTICAL trunk shape (common hidden width, task-specific out
dim). Each part's native feature block reaches the trunk through a
FIXED, frozen, seeded random projection to the common input dim —
projections are part of the input spec (never mixed); only trunk
weights are composed. A part that cannot meet the spec is excluded
from the weight-space arms and the exclusion is stated.

**Composition arms** (all on the part-team, per task):
- **MONO** — the single general reader (anchor; every arm answers to it).
- **TEAM-OUT** — output-level composition (average/ vote of part verdicts).
- **W1 SWAPPING** — learned router loads ONE part-reader's trunk per
  case; single forward pass.
- **W2 GATED MIXTURE** — per-case convex combination of part-reader
  trunk weights; one forward pass.
- **W3 UNIFORM SOUP** — static average of all part-reader trunks
  (control; it lost in the MoE lab — included to test whether this
  domain differs).
**Breeding:** part-readers for the W arms are fine-tuned from ONE
SHARED INIT (SHR — the MoE lab's measured precondition for weight-space
methods having legs). If budget allows, an IND (independent-init)
contrast runs on the edit-verdict task only; if not, the prior is
stated and SHR runs alone.

**Pre-registered bars for Arm 2:**
- Part-team adoption: TEAM-OUT or the best W arm beats MONO by
  **≥ +3 pts average** across the headline splits it runs on, and
  loses no headline task by >2 pts. (Internals Phase 5's lesson:
  consultation composition LOST to singles there — the team must
  earn its place, not inherit it.)
- W-arm bar (from the MoE lab, adapted): a W arm earns anything only
  by **beating TEAM-OUT paired on the headline splits** (majority of
  part-team tasks), with its memory/latency advantage reported
  alongside. Matching TEAM-OUT at lower active memory is reported as
  an efficiency result, not an accuracy win.
- If budget cannot carry the full Arm 2, it is implemented on the two
  most promising task families (home edit-verdict + public
  base-vs-instruct) and the rest is spec'd here as the protocol for
  a later run. REPORT.md carries the single-vs-part-team table or
  the explicit deferral with reasons.

## Boundary

Side lab only. Nothing written to Fable's side; no factory adoption on
the strength of this pilot — a verdict for Arnav, then his call. The
MoE shell artifact itself remains walled off in weight-moe-lab; only
its METHODS transfer here. Weights are research data under their
licenses; nothing redistributed.

## Arm 3 — the AlphaFold framing (Arnav, 2026-11-10 13:25 PT)

AlphaFold: amino-acid sequence in → folded structure/function out,
learned from a corpus of solved structures. Ours: **raw weights in →
the model's capability structure out** — what it is, what it can do,
what will happen if you edit it — learned from the corpus of known
models + our measured lab history. Two testable arms, side-lab scope,
same split discipline as everything above.

**ARM 1 — BEHAVIOR-PROFILE PREDICTION (the "folding" task; headline).**
From weights alone, predict a model's measured BEHAVIOR PROFILE, not
just identity labels. Public entries → published per-domain eval bands
(multi-output; domains: knowledge = MMLU, code = HumanEval, math =
GSM8K, reasoning = BBH or ARC-c where the card publishes it; band edges
fixed in labels.py before any Arm-1 training; missing domains are
masked outputs, never imputed). Home entries → our measured
scores/verdicts (Arm 1 is where the home track's H1/H2 tasks live).
Report per-domain error vs the baseline reader AND vs a
predict-the-mean control, on held-out families + the frontier tier.
This is the strongest form of the claim: function from structure.

**ARM 2 — MASKED WEIGHT MODELING (the representation bet).**
Self-supervised pretraining: mask parts of a model's weight features
(whole layers, matrix blocks, expert subsets) and train the reader to
reconstruct the masked parts' statistics from the rest; then fine-tune
the pretrained reader on the pilot's tasks and compare against the
direct (non-pretrained) reader on identical exams. **Pre-registered:
the arm is interesting only if pretraining transfers — beats the
direct reader on the majority of tasks on the headline splits.**
Priority if budget forces a choice: Arm 1 first (it IS the claim);
Arm 2 may land as a small run + full spec in REPORT.md.

**Analogy honesty (for REPORT.md):** AlphaFold had physics underneath
and millions of solved structures; we have ~35 public entries + our
lab history. The data-scale gap is orders of magnitude and will be
stated plainly — the arms test whether the *shape* of the idea
(structure → function, learned) shows any signal at our scale, not
whether we have replicated AlphaFold.

## Arm 4 — surgery on our own freshly trained readers (Arnav, 2026-11-10 13:46 PT)

Surgery's proper subject is OUR OWN models, trained minutes earlier —
capability first (from training), then edits. Once the single reader
and the part-specialists are trained, run the lab's surgery protocol
on them, identical in discipline to the internals round: per-weight
gradient/knockout maps on a VALIDATION split only -> indictments ->
candidate edits (zeroing for fp weights; value flips where a ternary
variant exists) -> validation re-check with recall guards -> ONE
held-out confirm. **An edit ships only on a measured held-out win
(>= +0.5 pt over the unedited model, no class recall dropping >2 pts);
otherwise it is reverted and recorded as NULL.** The held-out exam is
never used for mapping or selection.

Subjects, in priority order: (1) the part-specialist trunks
(shared-init bred — training-born defects are the plausible kind);
(2) the neural single reader (an MLP twin of the tabular reader,
trained for this arm and Arm 3's pretraining; the gradient-boosted
reader has no weights to edit and is reported as not-applicable,
not silently skipped).

Report per model: indicted weights/flips, validation delta, held-out
verdict (shipped / reverted), and the explicit contrast with the
internals round — where surgery on constructed-data specialists
found NO shippable edit in 3 models and the defects proved to live
in the data protocol and the probe instrument. Whether freshly
trained readers show a different yield is the question of this arm;
both answers (yield > 0, or another clean null) are reportable
results, recorded either way.

## Corpus as landed (2026-11-10, post-download record)

Downloader finished 17:33 PT: **201.1 GB, 29 models**. All 23 small-tier
items + qwen3-4b, gpt-oss-20b (full MXFP4), qwen2.5-coder-32b-instruct-awq,
deepseek-v2-lite (partial, shards 1-2/4), llama3.1-70b-instruct-awq
(partial, shards 1/5/8/9 of 9), qwen3-30b-a3b (partial, 4 of 16 shards).
Cap-skipped at 201.1 GB (est. would exceed the 209 GB cap), recorded
excluded-by-cap: kimi-k2-instruct, gpt-oss-120b, moonlight-16b-a3b,
qwen3-235b-a22b, llama4-scout, deepseek-r1. Consequences: Moonshot is
absent as a family; DeepSeek (held out throughout) is the unseen-family
exam, joined by gpt-oss (single-member family); the frontier exam rests
on gpt-oss-20b full + the big partials. Mistral-7B-v0.3 occupies
28.99 GB on disk (the repo ships duplicate shard sets).
