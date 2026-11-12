# No-gradient weight editing of Qwen — what "edited with a prompt" actually was, what the evidence supports, and a plan for Qwen3-4B

Research note, 2026-11-09. Commissioned by Arnav after the "GPT-6 edited Qwen's weights with a
prompt" claim. Question order follows his correction: (1) the prompt-only claim itself — real
instances, real mechanism, real limits; (2) no-gradient composition methods as the supporting cast;
(3) an experiment plan for our Qwen3-4B under the lab's existing hygiene (dev selects, test
confirms once, held-out decides). Nothing here was run; this is research and plan only.

---

## 1. The claim Arnav saw — it exists, it has names, and it is narrower than the headline

### 1.1 The source

**"Sparks of Weight-Space Programming"** — Rikiya Takehi, Jayden Teoh, Alex Zhang, Omar Khattab
(MIT CSAIL), personal blog post, 2026-11-02. Not peer-reviewed; no arXiv paper as of the coverage.
Full logs public: github.com/RikiyaT/lm_understand-logs (`exp8_math/`), and the edited checkpoint
was rebuilt from the released bit-exact diff and hash-verified, then re-evaluated independently
(see 1.4). Blog: rikiyat.github.io/blog/weight-space-programming (URL as given on the HF model
card, [ML-Intern-lab/Qwen3.5-0.8B-weight-space-programming](https://huggingface.co/ML-Intern-lab/Qwen3.5-0.8B-weight-space-programming)).

The editor model is OpenAI's **GPT-6 "Astra."** The target in the headline experiment (their
Experiment 8) is **Qwen3.5-0.8B** — a 24-layer, ~0.8B model. Arnav's memory of the claim is
accurate: it was Qwen, it was math + instruction following, and there was no training run.

### 1.2 What was claimed

Asked to "make Qwen3.5-0.8B better at math without gradients," Astra reportedly diagnosed a
defect in the weights and fixed it by "natively editing 0.016% of the weights." Reported results
at the largest budget, identical sampling (thinking on, temp 0.6, top-p 0.95, top-k 20):

| Metric | Base | Edited (50 forward passes) | Edited (10 passes) | Edited (25 passes) |
|---|---|---|---|---|
| MATH-500 | 7.9% | **48.1%** | 12.3% | 14.1% |
| GSM8K | 13.8% | **67.1%** | — | — |
| IFEval | 21.0% | **62.3%** | 49.0% | — |
| Answers hitting the 32,768-token limit | 93% | **33.1%** | 87.2% | — |

Sources: the post's results table as reproduced in
[letsdatascience coverage](https://letsdatascience.com/blog/gpt-6-astra-edited-0-016-percent-qwen-weights-math-sixfold)
and the [Groundy claim-by-claim re-grade](https://groundy.com/articles/can-you-improve-qwen-by-editing-weights-directly-what-astra-shows/).

### 1.3 What was actually done underneath

This is the part the headline drops. Per the post's own setup boxes (as re-read by the critique):

- Astra worked **in a Python kernel with the weights loaded as tensors, no GPU**. It did **not**
  read 0.8B floats in context and did **not** write floats back as text. The "raw floats in
  context, no tools" access path appears only in the post's small-network experiments
  (17K–172K weights). Every experiment on a real language model ran through Python.
- It was given **practice problems** (7,469 GSM8K-train + 7,275 MATH-train items) and a **budget
  of forward passes**: 10, 25, or 50 batches of up to 512 problems each. Training loops were
  forbidden; gradients were never computed. "Without gradients" is accurate.
- Diagnosis: Qwen3.5-0.8B in thinking mode **loops** — Qwen's own model card warns it is "more
  prone to entering thinking loops… which may prevent it from terminating generation properly."
  On Astra's first 96 practice problems, 85 answers were truncated at the token limit and **zero
  were plain wrong answers**. The 7.9% baseline is mostly a truncation artifact, not a math
  knowledge measure.
- The edit: Astra generated looping vs. non-looping texts, found **one direction** carried by the
  MLPs of **layers 15 and 19**, and subtracted it from **64 output columns of `mlp.down_proj` in
  each layer** — 131,072 weights total (0.016%). An independent diff of the two public checkpoints
  confirms exactly two tensors differ, and the difference is **rank-1 per layer**:
  `W′ = W − 6·u·uᵀ·W` on those columns (the factor 6 means the direction is overshot/reversed
  rather than merely removed)
  ([checkpoint diff analysis](https://gnana70.medium.com/an-ai-edited-0-016-of-another-ais-weights-i-opened-both-models-to-see-what-it-changed-adc50cf1b52e)).
  Mechanically this is **directional ablation** — the recipe published in 2024 for the
  refusal direction (Arditi et al., "Refusal in Language Models Is Mediated by a Single
  Direction") and since productized by tools like Heretic — executed here by a prompted agent
  instead of a human.
- Where the gains came from: on 1,152 held-out practice problems, 579 answers flipped
  wrong→right and 5 flipped right→wrong; **576 of the 579 fixes were previously truncated
  answers**. The edit recovered completions; it did not add math
  ([BestHub re-analysis](https://www.besthub.dev/articles/debunked-0-016-weight-edit-fixed-qwen-s-reasoning-loops-not-math-ability-da799f8e4aaa)).
- Negative control, in the same post: **Gemma 3 270M**, which rarely loops (8.5% truncation),
  could not be improved — best edit moved MATH-500 6.8% → 7.7%, "not established." The authors'
  own sentence is the honest summary: **weight editing can remove an obstacle that hides an
  ability; it cannot add an ability the model never learned.**

### 1.4 What is verified vs. author-reported

- **Verified independently:** the edited checkpoint itself. Ahsen Khaliq (HF) rebuilt it from
  the released diff with the authors' `apply_edit.py`, sha256-verified every rebuilt tensor
  against the evaluated checkpoint, and re-ran the full MATH-500 protocol (500 problems × 4
  samples, vLLM, H200): **51.0%**, 31.6% token-limit rate — consistent with the claimed 48.1%.
  Checkpoints: [ML-Intern-lab/Qwen3.5-0.8B-weight-space-programming](https://huggingface.co/ML-Intern-lab/Qwen3.5-0.8B-weight-space-programming),
  [JonathanColetti/Qwen3.5-0.8B-Astra-WeightEdit](https://huggingface.co/JonathanColetti/Qwen3.5-0.8B-Astra-WeightEdit).
- **Author-reported only:** that Astra's *process* went as described (the logs are public, which
  is stronger than most demos, but the method has had no outside replication and no durability
  data — e.g., whether the fix survives further edits).
- **The critique:** Matthew Honnibal (spaCy/Explosion), 2026-11-03, called the post "massively
  misleading" — not on the numbers (his re-grade reproduces them) but on the packaging: the post
  blends two different techniques — raw-float reading/writing on ≤172K-weight toy nets, and
  Python-mediated repair of a real LM — under one banner of models "natively" reading and writing
  weights. His concession is the correct takeaway: **"What the Qwen result actually shows is that
  Astra can be prompted to devise and perform tasks that a human ML engineer could do."**
  (Critique at honnibal.dev; analysis via [Groundy](https://groundy.com/articles/can-you-improve-qwen-by-editing-weights-directly-what-astra-shows/)
  and [letsdatascience](https://letsdatascience.com/blog/gpt-6-astra-edited-0-016-percent-qwen-weights-math-sixfold).)
- Adjacent same-week claims, same shape, weaker evidence: Chandan Singh had Claude (as a coding
  agent) write weight-space programs for a blank transformer — 13 toy tasks, 10 algorithmic tasks
  to 100% within 3 attempts (informal write-up). Legora's CTO reported Claude Fable hand-writing
  a ~100K-param legal-citation classifier (3,793 nonzero params, 97.8% test accuracy with zero
  labeled examples; his own figures, unverified)
  ([dealroom roundup](https://dealroom.co/news/169058-mit-gpt-6-edited-a-rival-ai-s-weights-by-hand-lifting-its-math-score-to-/)).

### 1.5 The reduction, in one paragraph

"GPT-6 edited Qwen's weights with a prompt, nothing else" reduces to: **a frontier model, acting
as an ML engineer inside a Python harness, ran the target on practice problems under a forward-
pass budget, used activation statistics to localize a known, single-direction pathology
(reasoning loops), applied the standard directional-ablation recipe at a swept strength to 128
columns in two layers, and kept the result because evals improved.** No tensor was read or
written as in-context text in the Qwen experiment; no eval "loop" in the gradient sense existed,
but there *was* an evaluate→diagnose→edit→re-evaluate loop driven by the model — the forward-pass
budget ablation (10 passes: 12.3%, 25: 14.1%, 50: 48.1%) shows the loop, not the single prompt,
did the work. And the capability changed was a *defect* (failure to terminate), which is why the
gain could be 6×: the math was already in the model.

---

## 2. Feasibility, stated precisely: what a prompt can and cannot do to a 4B model's weights

### 2.1 The hard arithmetic

Qwen3-4B has ~4.0B parameters. As decimal text, one weight costs roughly 8–20 characters
(sign, digits, exponent, separator) → the full model is **~40–80 GB of text, on the order of
10^10 tokens**. Frontier context windows are ~10^6 tokens; single responses are ~10^5 tokens.
So a frontier model can hold at most **~0.01% of a 4B model's weights in context at once**, and
could not emit even one full layer's tensor as text in a single reply. Literal "the model reads
the weights and writes corrected weights" is impossible at 4B scale by about four orders of
magnitude — and, notably, it is not what happened even at 0.8B. The demonstrated in-context
ceiling is far lower: raw-float *reading* impressed at ≤24K weights (game identification from
17,253 weights); the largest raw read/write was the 172K-weight Kinetix policy repair. The
7.2M-weight transformer experiment already used Python analysis, not in-context floats.

### 2.2 The three access paths (keep them separate in every claim)

1. **Raw floats in context** — real, but only for small constructed/toy networks (≤~10^5–10^6
   weights with tool help). This is the regime of Arnav's Nov 7 specialist-model work and of the
   WSP post's Experiments 1–5.
2. **Python-mediated editing** — the frontier model writes and runs code over tensors: probe
   activations, compute contrast directions, score neurons/columns, apply a parameterized edit,
   run evals, iterate. The model supplies *decisions and code*; arithmetic happens in the kernel.
   This is the regime of the Qwen result, and of our edit-lab surgery with a frontier model in
   the map→indict loop.
3. **Generated parameters** — a trained hypernetwork emits weights from text: Text-to-LoRA
   (Sakana, ICML 2025) generates a task's LoRA from a natural-language description in one forward
   pass, zero-shot to unseen tasks; Doc-to-LoRA does the same for documents. This is genuinely
   "text → weights," but the *generator* was itself gradient-trained to do it; a prompted
   frontier model does not have this ability off the shelf
   ([T2L paper](https://pub-fad10fba280c45dba0823fd585acc08c.r2.dev/pdf/fe086fa313c044bb33dc4518564d16d14a4bdb12.pdf?v=1789148551)).

### 2.3 The mechanisms that make "prompt → edited weights" real in practice

- **Model-authored edit scripts** (path 2): the model writes `apply_edit.py`-style code; the
  edit itself is a closed-form tensor op. Proven at 0.8B (WSP) and trivially extensible in code
  to 4B — the *code* scales, the *diagnosis* is the open question.
- **Directional ablation baked into weights**: compute a contrast direction u (mean activation
  difference between defect and clean traces), then edit `W ← W − α·u·uᵀ·W` on selected output
  columns of `down_proj`. This converts an inference-time steering vector into a permanent
  weight change. It is the single most proven "skill-adjacent" weight edit: refusal ablation
  (2024), the WSP loop fix (2026). Requirement: **a single direction must actually carry the
  defect.**
- **Adapter/dose specification**: the model picks per-layer scales, merge coefficients, which
  adapters to combine at what dose — a scalar decision problem (tens of numbers), well inside
  what a prompted model can reason about and what black-box search can optimize (Section 3.2).
- **Defect repair by reasoning**: diagnose from behavior first (what do failures look like?),
  localize with cheap maps, indict, edit, verify. This is the lab's surgery doctrine with the
  frontier model as surgeon-of-record.

### 2.4 How far does the defect-repair pattern scale? (Arnav's Nov 7 result → Qwen)

Arnav's Nov 7 specialist work is the same pattern at the smallest scale: an optimizer model
fixed 8 planted weight defects in constructed specialist networks by reasoning, verified
exhaustively. It worked because the regime was maximally favorable: weights few enough to
inspect, defects *planted* (discrete, localizable, each with a definite correct value), and an
exact verifier. Our edit-lab surgery is the pattern at 4B: gradient + knockout maps over the
coordinator's layers 14–27 found **no dead layers, no dominant layer, all-positive knockout
deltas — capability diffuse across all 14 layers** (lineage: locator probes, 2026-11-09). That is
the general case for *skills*, and it is the opposite of the WSP case.

What breaks first as you scale the pattern from planted defects to Qwen-size skill gains:

1. **Indictment.** Defect repair needs a defect: a behavior whose failures share one mechanism
   (loops → one direction). Skill shortfalls (wrong arithmetic steps, missed instruction
   constraints) are distributional — many mechanisms, no single direction. The WSP authors'
   Gemma control is exactly this failure: no loop, no fix, +0.9 points of noise.
2. **Verification cost and noise.** Each candidate edit is cheap to apply but expensive to
   judge: generation evals on hundreds of items, and at our current suite sizes (coordinator
   n=14) one case is ~7 points — plausible edit gains drown in noise unless suites grow
   (Section 5). The WSP run spent up to 50×512 ≈ 25K generations to earn its verdict.
3. **Diagnosis bandwidth.** The editor never sees the weights; it sees statistics that code
   computes (activation means, alignment scores, per-case failure clusters). Choosing *which*
   statistics to compute is the real skill, and it is where a frontier model genuinely helps —
   it is also where it can confidently indict the wrong thing. Our dev/test divergence
   (rejected adapter leads dev, loses test by 0.139) is the local reminder that diagnosis and
   selection must stay on dev, with test confirming once.

**Net:** the pattern scales as a *workflow* (frontier model + Python harness + eval gates) to
any model size. It does not scale as a *capability claim*: it repairs indictable defects; it
has never been shown to raise a model's underlying math or instruction-following skill, by the
WSP authors' own negative control.

---

## 3. The supporting cast: no-gradient composition, method by method

Context for expectations: our lab has already measured the two ends of this space on the
coordinator — dose-scaling a LoRA adapter interpolates monotonically toward base and **never
crosses it** (0.791 @1.0 → 0.894 @0.5 → base 0.930), and soup-50 (50/50 average of the two
failed adapters) is **dead by ceiling** (partial mean 0.819, cap 0.884 < 0.930): averaging two
models that share a base and share failure modes averages the failure modes. The literature
below is consistent with both facts.

### 3.1 Weight-space composition (soups, task vectors, TIES/DARE, variants)

- **Model soups / weight averaging** (Wortsman et al. 2022): averaging fine-tunes of one base
  reliably helps in vision; for LLMs it helps when the ingredients are strong and diverse.
  Our soup-50 is the counterexample that defines the boundary: same-base, same-task, both
  ingredients *below* base → soup below base.
- **Task Arithmetic** (Ilharco et al. 2023): add/subtract task vectors (fine-tune minus base).
  In the largest in-the-wild study to date (TMLR 03/2026; Qwen3 + Llama3 at 3B/4B/8B, 12
  checkpoints per base, 16 benchmarks), **Task Arithmetic was the only method that reliably
  produced merges beating the base model — and the gains were limited** (average relative
  improvement ~+0.17, plateauing quickly). Fewer than 50% of individual fine-tuned checkpoints
  beat their own base at all
  ([TMLR study](https://push-zb.helmholtz-munich.de/deliver.php?id=45146)).
- **TIES / DARE** (Yadav et al. 2023; Yu et al. 2024): trim/sign-resolve or drop-and-rescale
  deltas to reduce interference. Same TMLR study: TIES turned **unstable at higher merge
  counts** (Qwen-8B: +0.16 at n=4 → −0.08 at n=12). MergeBench (Llama/Gemma 2–9B, five domains
  incl. math + instruction following, 8 methods) concurs: merging works better on stronger
  bases, coefficient tuning + sparsification reduce forgetting, DARE ranks lower on larger
  models, and merged models still trail jointly multi-task-trained models in-domain
  ([MergeBench](https://yifei-he.github.io/mergebench/)).
- **Where math/IF gains on Qwen are actually published:**
  - *Long-to-short merging* (Qwen2.5-Math-7B + DeepSeek-R1-Distill-Qwen-7B): TA/TIES hold or
    slightly improve math accuracy while cutting response length ~50% (GSM8K 88.9 → 90.5/90.6;
    6-benchmark average 32.8 → 53.5/54.8 — the average jump is mostly the short model acquiring
    the long model's hard-benchmark ability, i.e., capability *transfer between ingredients*,
    not creation). Activation-guided ACM-TIES does best: avg 55.8, +1.3 reasoning points
    ([ACM paper](https://arxiv.org/html/2505.14009v2);
    [L2S merging](https://arxiv.org/pdf/2503.20641)).
  - *Mixture-Trained Merging* (2026): on **Qwen3-4B-Base** specifically, linear/TIES merges of
    math/code/IF experts land at ~67–69 average across GSM8K/MATH/MBPP+/LCB/IFEval — but the
    paper's point is that hard single-objective experts interfere (mode collapse in think/
    non-think merges); the gains come when branches are *trained* on objective-biased mixtures.
    The merge step itself is not where the win is manufactured
    ([MTM](https://arxiv.org/pdf/2610.01238.pdf)).
  - *Heterogeneous (cross-size) merging* on Qwen pairs: small-ratio interpolation can beat the
    stronger source (Qwen3-14B+32B union: IFEval 0.4652 → 0.5635, avg 0.7474 → 0.7744), but
    **near-balanced interpolation often collapses** and per-task results show a seesaw — gains
    on some capabilities coexist with regressions on others
    ([weighted averaging perspective](https://arxiv.org/html/2607.18026)).
  - *Medical multi-task merges* on Qwen2-7B (Hi-Merging, ACL 2025): merging a medical model with
    Qwen2-Math-7B recovered GSM8K to 77.45 vs. the math model's own 79.00 — i.e., merging
    *preserved* most of a donor skill while adding another; it did not exceed the donor
    ([Hi-Merging](https://pub-fad10fba280c45dba0823fd585acc08c.r2.dev/pdf/2506.12379.pdf?v=1789086824)).
- **Model Stock / WARM / frankenmerging** (cited conservatively): Model Stock (Jang et al.
  2024) averages checkpoints along the fine-tuning trajectory geometry — a soup refinement, not
  a skill source. WARM (Ramé et al. 2024) averages multiple RLHF runs to gain robustness/reward
  — needs multiple trained ingredients. Frankenmerging / layer stacking (e.g., Yadav et al.'s
  SOLAR-style depth up-scaling) splices layers from donors to grow a model — changes the
  architecture, evaluated as a new base, not an edit of ours. None changes the headline:
  **composition redistributes capability that training put into the ingredients.**

### 3.2 Evolutionary / black-box search over edits

- **Sakana Evolutionary Model Merge** (Akiba et al., Nature Machine Intelligence 2025): CMA-ES
  over merge coefficients (parameter-space: per-model/per-layer weights) and data-flow space
  (which layer takes which model's output). EvoLLM-JP (Shisa-Gamma + WizardMath + Abel, all 7B)
  topped Japanese benchmarks incl. MGSM-JA, beating all <70B Japanese models. Budget: the search
  ran **~100–150 generations**, each generation evaluating a population of merged candidates on
  a training split, best candidate evaluated once on held-out test — the same dev-selects /
  test-confirms hygiene this lab uses
  ([summary](https://www.promptsicle.com/tips/evolutionary-outperforms-backprop-in-llm-fine-tuning)).
  Note what it optimized: coefficients over *already-trained, complementary* donors. The search
  found a combination; it did not create capability.
- **Scalar search is the version that fits our compute.** Optimizing ≤~50 scalars (per-layer
  merge coefficients, adapter doses, ablation strengths α) with CMA-ES or even random search
  needs hundreds of *dev* evals, not thousands of generations. TRINITY (Sakana, ICLR 2026)
  makes the budget point generally: sep-CMA-ES beat RL and random search in the tight-budget
  regime (1.5K–40K evaluations for a ~10K-dim problem) because the objective is near-separable —
  at our scalar counts the budget is far friendlier
  ([TRINITY](https://proceedings.iclr.cc/paper_files/paper/2026/file/727658ad24ba28e02dffd379bdc69448-Paper-Conference.pdf)).
  The named risk is **eval overfitting**: a search that sees dev thousands of times will find
  dev's noise. Mitigate with a capped eval budget, a dev/dev-confirm split, and test exactly once.

### 3.3 Direct weight surgery: ROME/MEMIT and the facts-vs-skills line

- ROME (Meng et al. 2022): rank-1 update to one MLP layer writes one factual association;
  ~99–100% efficacy on the edited fact, 75–79% neighborhood specificity. MEMIT (2023): batch
  version, 10,000 simultaneous facts at ~96% recall. **Scope: directional entity–relation–object
  triples.** That linear-subspace assumption is the documented boundary — it cannot encode
  non-linear constraints, and edited facts do not propagate: ROME-edited GPT-J falls 40.5% →
  7.4% on multi-hop MQuAKE-CF; MEMIT-edited Vicuna-7B 30.2% → 4.9%
  ([knowledge-editing belief synthesis](https://wiki.llmeem.ai/llm-eem/topic/knowledge-editing/)).
- Sequential edits degrade the substrate: gradual-then-catastrophic forgetting (Gupta et al.
  2024); spectral analyses show repeated updates distort the dominant singular directions that
  carry general ability; past ~1,000 sequential MEMIT edits, downstream performance approaches
  collapse (CommonsenseQA to ~random). One 2025 medical-editing eval: 50 ROME edits took a 3B
  Llama from 60.7 → 24.1 MMLU (citations via [Groundy](https://groundy.com/articles/can-you-improve-qwen-by-editing-weights-directly-what-astra-shows/)).
- **Verdict for our targets:** there is no credible evidence ROME/MEMIT-style edits move *skills*
  (math reasoning, instruction following). They write facts into key-value slots; a skill is not
  a fact, and our own knockout maps show the coordinator's skill is not stored in an indictable
  slot anyway. Not a candidate for this program.

### 3.4 Steering vectors (contrast-pair, no training) — and the persistence question

- Difference-of-means steering from contrast pairs is the parent technique of the WSP edit:
  ITI (Li et al. 2023) steers toward truthfulness; function vectors (Todd et al. 2024) carry
  in-context-learned tasks; refusal ablation (Arditi et al. 2024) removes a behavior by erasing
  one direction. All are **inference-time** interventions: the vector must be injected on every
  forward pass, forever. Effects are real but modest and layer/strength-sensitive, and they do
  not transfer across models.
- Recent math-specific results on Qwen-family small models: **DenseSteer** (ICML 2026) builds a
  "dense reasoning" vector from as few as 50 contrastive rewrites and improves small Qwen2.5
  models' math accuracy at inference time, training-free
  ([DenseSteer](https://raw.githubusercontent.com/mlresearch/v306/main/assets/ouyang26d/ouyang26d.pdf)).
  **ASC** (ACL 2026 Findings) learns one vector from 100 verbose–concise pairs and cuts CoT
  length up to 69.4% across MATH500/GSM8K/LiveCodeBench with a KL trust region to protect
  utility ([ASC](https://olo.0l0.workers.dev:443/https/aclanthology.org/2026.findings-acl.1828.pdf)).
- **Persistence/transfer, honestly:** a steering vector persists exactly as long as the serving
  stack applies it — it is a runtime patch, not a model property; it transfers across prompts
  within the model, not across models or fine-tunes. The WSP edit shows the one way to make it
  permanent: **bake it into the weights** (project the direction out of `down_proj`). Baking is
  stronger (no runtime hook, survives serving anywhere) and riskier (no off switch; the α=6
  overshoot in the actual edit would be hard to justify without their eval budget). Our plan
  treats steering as the *measurement* (does a direction exist that moves the behavior?) and
  baking as the *commit step* only after dev proves the direction.

### 3.5 Frontier-model-in-the-loop editing — does the exact loop exist in print?

The full loop (frontier model writes eval suites → diagnoses per-case failures → proposes edit
candidates → search keeps only verified wins) has **not** been published as a named, replicated
system for skill improvement. What exists:
- The WSP post: frontier model as diagnostician + editor over a fixed practice set, with a
  human-designed harness and budget (Section 1). The suites were existing benchmarks, not
  model-written.
- Evolutionary merge search (3.2): the *search* is algorithmic (CMA-ES), not model-proposed;
  frontier models are not in that loop.
- Singh's Claude weight-program runs and the Legora classifier: frontier model authoring small
  networks from scratch with a few feedback rounds — toy scale, informal.
So the loop Arnav describes is **assembled, not found**: WSP diagnosis + our lab's dev/test
gates + scalar search + WAYS-OVER-style model-generated suites. That assembly is legitimate
engineering, but nobody should cite it as established. Its weakest joint is the one the WSP
post itself exposes: the diagnosis step only pays when an indictable defect exists.

---

## 4. Failure modes and honesty checks (applies to everything above)

1. **Defect/capability confusion** — the WSP headline itself. Before claiming any edit "improves
   math," decompose the gains: how many fixed cases were truncations/format failures vs. genuine
   wrong answers? Report the decomposition, as the re-analyses did (576/579).
2. **Catastrophic forgetting / blast radius from merges and edits** — MergeBench measures
   forgetting explicitly; heterogeneous merging shows the seesaw (one benchmark up, another
   down); sequential parametric edits collapse general ability. Every candidate in Section 5
   carries a regression suite (the lab's coordinator 0.930 / researcher plan 1.000 / extract
   0.733 gates stay in force) and a general-capability spot check.
3. **Benchmark contamination** — GSM8K/MATH test items circulate in training data and on the
   open web; a frontier model writing "fresh" problems may regenerate near-duplicates of test
   items from memory. Our synth pipeline already runs n-gram contamination checks against
   training corpora; the new suites get the same check against *themselves* (dev vs. test) and
   against GSM8K/MATH test sets.
4. **Eval overfitting in search** — dev-selected winners regress on test (our rejected adapter:
   dev 0.7896, test 0.791 vs. base 0.930 — dev and test disagreed about everything). Cap search
   evaluations, keep a confirm split, run test once per finalist, report paired per-case deltas
   (sign test), not just means.
5. **Environment sensitivity** — the lab has already recorded the same adapter scoring
   plan 0.975/extract 0.767 under one thread env and 1.000/1.000 under another. Pin the protocol
   (OMP=2, greedy, fixed harness) and re-verify any claimed win under the alternate env before
   believing it.
6. **"No gradient" ≠ "no optimization."** Forward-pass budgets, strength sweeps, and coefficient
   searches are optimization with extra steps. Claims should state the eval budget spent, the
   way the WSP budget ablation (10/25/50) honestly does.

---

## 5. Experiment plan for our stack (Qwen3-4B first; math + instruction following)

Doctrine carried over unchanged: map → indict → edit only what the map indicts; dev selects,
test confirms once; observe.py-style pristine measurement for anything touching existing gates;
one heavy job at a time; ashp GPU under thermal discipline (bursts from a cooled box, idle
<60 °C start, pause at the 82 °C tripwire, SM clock lock 1155 MHz) — the synth legs already run
this way; VM evals chunked to survive the ~2-hour VM restart cadence.

### Phase 0 — Defect hunt before skill hunt (cheap; decides everything downstream)
Run base Qwen3-4B on the new dev suites (Phase 1) and classify every failure:
- **Class D (defect):** truncation/looping, format collapse, refusal, constraint-blindness with
  a repeated surface signature — failures that share a mechanism.
- **Class C (capability):** completed, well-formed, wrong.
If Class D is a meaningful share (rule of thumb: ≥15% of failures), the Astra play is live.
If failures are ~all Class C, prompt-guided editing has nothing to indict — record that and
route effort to the coefficient search (Phase 3) and the existing WAYS-OVER synth retrain.
*The frontier model's job in this phase:* cluster the failures, name candidate mechanisms,
propose which statistics to compute. Humans/lab verify the clusters against raw outputs.

### Phase 1 — Suites (build once, seal the tests)
- **Math dev (n≈200)** and **math test (n≈200)**: fresh GSM-style word problems, frontier-model
  drafted, every item's answer verified by an independent solver path (symbolic check /
  second-model solve with agreement), difficulty-stratified. Contamination-checked (n-gram)
  against GSM8K/MATH test sets, against all lab training corpora, and dev↔test against each
  other (the METHODS addendum's contamination rule).
- **IF dev (n≈150)** and **IF test (n≈150)**: IFEval-style programmatically verifiable
  constraints (length, format, keyword, structure), generated fresh, checker code written and
  unit-tested before any model sees the suites.
- **Regression pack:** the existing pristine coordinator suite + researcher gates, unchanged;
  plus a 100-item general spot check. Any candidate that breaks a gate is dead regardless of
  math/IF gains.
- Dev/test are separate files from day one; test files are not opened during selection.

### Phase 2 — Candidate A: frontier-guided directional ablation (only if Phase 0 finds a defect)
1. Build contrast pairs from dev failures: defect traces vs. the same prompts answered cleanly
   (or clean traces from sibling prompts). Compute per-layer mean-difference directions from
   residual-stream activations on ashp GPU (one burst; statistics are small).
2. The frontier model reviews the map (per-layer direction norms, alignment of the direction
   with `down_proj` columns — the same statistics Astra's harness computed) and indicts:
   layers, column sets, and a strength grid α ∈ {1, 2, 4, 6}.
3. First measure the direction **as inference-time steering** (cheap, reversible): does
   subtracting it move dev Class-D failures without hurting Class-C or the regression pack?
   Only if steering works do we **bake**: `W ← W − α·u·uᵀ·W` on the indicted columns, as a new
   checkpoint, bit-diffed against base so the edit is exactly auditable (the WSP checkpoint
   standard).
4. Dev-select α (and column count) on the dev suites; the winner gets **one** test run.

### Phase 3 — Candidate B: scalar evolutionary search over compositions (runs regardless)
Search space (≤~50 scalars, all no-gradient):
- doses of the lab's existing LoRA task vectors (researcher/coordinator adapters as vectors,
  per-layer-group scales) — knowing dose-response is monotone toward base on the coordinator,
  the search's honest job is finding whether *combinations* cross it anywhere dev can see;
- merge coefficients if a same-base donor checkpoint is admitted (e.g., a sibling Qwen3-4B
  fine-tune from the same base — donor must share the exact base or the vector arithmetic is
  meaningless);
- ablation strengths from Phase 2, jointly with the above.
Optimizer: CMA-ES (small population) or coordinate random search; fitness = dev math + dev IF
minus regression-pack penalties. **Budget cap: 300 dev evaluations**, logged in lineage with
the running best; a dev-confirm split (held out from the search) sanity-checks the winner
before its single test run. This is Sakana's pattern at scalar scale, with our gates.

### Phase 4 — Verdict runs
Each finalist (≤2) gets: one math test run, one IF test run, full regression pack, and a
re-run under the alternate thread environment. Paired per-case deltas vs. base reported with a
sign test. Results appended to results/lineage.jsonl and REPORT.md with the gain decomposition
(defect-fixed vs. capability-flipped) mandatory.

### Compute plan
- Direction statistics + steering probes: ashp GPU, single bursts (~minutes each), cooled-box
  starts; checkpoint every candidate edit to disk before eval (edits are cheap; evals are the
  budget).
- Dev evals: batched generation on ashp GPU where the harness allows; otherwise VM CPU in
  restart-proof chunks (the lab's dev_eval pattern), OMP=2 pinned.
- Frontier-model calls: failure clustering, indictment proposals, suite drafting — text-scale
  work, no GPU. Every proposal it makes is logged verbatim in lineage (their locator_log
  pattern) so the surgeon's reasoning is auditable, not just its picks.

---

## 6. Blunt verdict

**Worth running first (in this order):**

1. **Phase 0 + Candidate A — defect-first diagnosis with frontier-guided directional ablation.**
   It is the only prompt-guided edit with a verified, real-model result behind it (WSP, with an
   independently rebuilt and re-scored checkpoint), it is cheap (statistics + a handful of
   evals), and our target models are exactly the family it worked on. Its condition is strict
   and knowable within a day: **if Qwen3-4B's dev failures contain an indictable defect, this
   can win; if they don't, it will do nothing, and the Gemma control says to believe that
   quickly rather than sweep strengths hoping.**
2. **Candidate B — capped scalar search over doses/coefficients.** Unglamorous, bounded,
   honest: the literature (Sakana; TMLR; MergeBench) says composition gains over a strong base
   are real but small, and Task Arithmetic-style moves are the only reliably positive ones. It
   will either find a small verified win or produce a clean negative — both are useful, and it
   cannot silently overfit if the budget cap and confirm split hold.

**Not worth running:** ROME/MEMIT for skills (facts only; multi-hop and sequential collapse);
raw in-context weight writing at 4B (arithmetically impossible, §2.1); multi-model soups
expecting skill creation (our soup-50 already died by ceiling; the literature agrees the
ingredients' capability is the ceiling); strength-sweeping an ablation against a capability gap
(the Gemma failure mode).

**What counts as a real win (pre-registered):** on the sealed test suites, a candidate beats
base Qwen3-4B by **≥ +3 points on math test AND no regression beyond noise on IF test**, with
paired per-case deltas positive by sign test, **all existing lab gates unbroken** (coordinator
0.930, researcher plan ≥ 1.000 / extract > 0.733 under the anchor protocol), the win **replicating
under the alternate thread environment**, and the gain decomposition showing the improvement is
not a single-case artifact. Anything smaller is noise at our suite sizes and gets recorded as
"no win," the same standard every prior candidate in this lab was held to.
