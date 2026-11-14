# What published research says about HiveMIND's open problems

Written 2026-11-14 for the session that takes on the research (see `NEXT_SESSION.md`, "The open problems"). Each
section gives the finding, then what it means here. The claims are the papers' own; few have been checked here.
Where a line says "here", it is about this repository.

## The short version

1. **Arnav is right that ternary models do better at about 3B parameters and up.** Below about 1B they lag
   full-precision models; around 3-4B they match them at a fraction of the size. Our DNA is 1.7B, which is below
   that line. A 4B DNA exists (t40, a trial in flight), and so does an **8B ternary model that is 2.2 GB**.
2. **Training only on right answers memorises; learning from right against wrong generalises better.** Our
   nightly loop trains only on right answers, and the body scores 0 on kinds it never practised. The hive
   already holds wrong attempts beside right ones. This is now built (`--pairs`) and waits for a measurement.
3. **Cells that grow from one DNA and specialise by domain are a known, working design** (Branch-Train-Merge,
   Branch-Train-MiX). What the literature adds to ours: combine cells with learned weights instead of picking
   one by keywords, and search those weights by evolution, which needs no gradients and runs on a CPU.
4. **Changing the DNA's own architecture needs pretraining-scale compute.** Converting or pretraining a ternary
   model takes billions of tokens. On free CPU runners, the reachable levers are: a bigger existing ternary DNA,
   better edits on top of it, and how cells are combined.
5. **"Engram" is also the name of a DeepSeek architecture (January 2026)**: a hashed N-gram memory table inside
   the model, looked up in constant time. It needs pretraining. The post-hoc relatives that fit here are
   test-time training (a small edit trained on the task itself) and sparse memory finetuning (continual learning
   with little forgetting).

## 1. Bigger ternary models

- **BitNet b1.58** ([Ma et al. 2024](https://arxiv.org/abs/2402.17764)): ternary weights match full-precision
  LLaMA from 3B parameters (perplexity 9.91 against 10.04; zero-shot average 50.2 against 49.7), at 3.55 times
  less memory and 2.71 times faster. The gap narrows as size grows. One later survey reproduces different 3B
  numbers, so parity at exactly 3B depends on the setup.
- **Spectra / TriLM** ([Kaushal et al. 2024](https://arxiv.org/abs/2407.12327)): 54 models from 99M to 3.9B on the
  same 300B tokens. A ternary 3.9B model matches the float 3.9B model on reasoning and knowledge benchmarks and is
  smaller in bits than a float 830M model. Above 1B, ternary models beat float and quantised models of the same
  size in bits.
- **Ternary Bonsai 8B** ([PrismML](https://huggingface.co/prism-ml/Ternary-Bonsai-8B-gguf), based on Qwen3-8B):
  2.18 GB as GGUF; its unpacked weights are published
  ([unpacked](https://huggingface.co/prism-ml/Ternary-Bonsai-8B-unpacked)), so it can be taught like t17 and t40.

**Here:** run as a DNA, 8B needs about 2.2 GB, well inside the 10 GB the hive may use. Training is the problem:
`training/grow.py` loads the unpacked weights in bf16, which is 16 GB for 8B and does not fit a 16 GB runner. The
way out is the QLoRA idea applied to ternary weights: keep the frozen DNA in memory as int8 values {-1, 0, +1}
with one scale per matrix (8 GB for 8B, 4 GB for 4B), turn one layer back into numbers only while it computes,
and train only the edit. That also makes t40 training fit without swap. It is not built yet. Whether bigger
pays at all is what run 43619078349 (t40) measures first.

## 2. Learning that carries over

- **"SFT memorizes, RL generalizes"** ([Chu et al., ICML 2025](https://arxiv.org/abs/2501.17161)): on unseen rule
  variants, models trained on the right answers (SFT) memorised the training rules and failed. Models trained by
  reinforcement learning with an outcome reward generalised. SFT was still needed first, to fix the output format.
- **Iterative Reasoning Preference Optimization** ([Pang et al., NeurIPS 2024](https://arxiv.org/abs/2404.19733)):
  sample several answers per problem, pair a right one with a wrong one, train with DPO plus a likelihood term on
  the right one, and repeat with the new model as the reference. It beat SFT and plain DPO on GSM8K, MATH and ARC.
  The likelihood term was essential.
- **ReST-EM** ([Singh et al. 2023](https://arxiv.org/abs/2312.06585)): generate, keep what a checker passes,
  fine-tune, repeat. This is our nightly loop. It beat training on human data, and it scales with the number of
  checked solutions per problem. Most of the gain came in the first iteration; more iterations overfit when the
  set of problems is fixed.
- **LoRA without regret** ([Thinking Machines 2025](https://thinkingmachines.ai/blog/lora/)): LoRA matches full
  fine-tuning for RL even at very small ranks. The best LoRA learning rate is about 10 times the full
  fine-tuning rate. Apply LoRA to all layers, including the MLP.

**Here:** our loop is ReST-EM: it trains only on agreed, checked programs (`rows_of`). The practice folders also
hold the members' wrong first attempts at the same tasks. `pair_rows` in `training/grow.py` now records right-
against-wrong pairs during practice, and `grow.py train --pairs` (workflow input `pairs: 1`) trains with DPO plus
the likelihood term. The reference is the DNA with the edit switched off. It is off by default until a gate
shows it helps. Our exam makes fresh problems every night, which avoids ReST-EM's overfitting on a fixed set. A
full RL loop (sample several programs per task, reward by the check, GRPO) is the stronger version of the same
idea. It costs several samples per task on a CPU.

## 3. Cells, organs and evolving the body

- **Branch-Train-Merge / Branch-Train-MiX** ([Sukhbaatar et al. 2024](https://arxiv.org/abs/2403.07816)): copy one
  seed model, train each copy on one domain in parallel, then combine them. BTX makes the experts' feed-forward
  layers the experts of a mixture-of-experts model and learns a router. This is our design (one DNA, organs,
  cells trained in parallel). The difference: our router is a keyword rule (`team/ternary.organ`).
- **LoraHub** ([Huang et al. 2023](https://arxiv.org/abs/2307.13269)): combine several LoRA edits with weights,
  found by gradient-free search on a few examples of a new task. It needs only inference and runs on a CPU. On
  Big-Bench Hard: 34.7% against 27.0% zero-shot.
- **Evolutionary model merging** ([Akiba et al., Sakana 2024](https://arxiv.org/abs/2403.13187)): evolution
  (CMA-ES) searches how to merge models, in weight space and in which layers run in which order. It found
  merges with abilities no single parent had.

**Here:** the shared server can switch on several cells at once, each with its own scale (`POST
/lora-adapters`). A body could therefore answer with a weighted mix of cells instead of one cell. Evolution can
search those weights against practice tasks, scored by the same checks. That is "the hive evolves its own
architecture" at a cost the runners can pay, and it finds its own flaws: the fitness is the tasks it fails.
Agreement between cells is a weak check when all cells come from one DNA. In g10's gate two cells made the same
error and agreed. Cells that differ more, or a check of another kind (foreseeing a program's output), make
agreement worth more.

## 4. The DNA's own architecture

- **BitNet Distillation** ([Wu et al., Microsoft 2025](https://arxiv.org/abs/2510.13998)): turning a float model
  into a ternary one needs extra normalisation layers (SubLN), continued pretraining (about 10B tokens), and
  distillation from the float model. Fine-tuning straight to ternary leaves a gap that grows with model size.
- **LoTA-QAF** ([2025](https://arxiv.org/abs/2505.18724)): ternary edits that merge into the ternary weights with
  no loss, trained with a sign-based optimiser (t-SignSGD), not with the straight-through method. It recovered
  quantised models well (MMLU), but on task-specific tuning 16-bit LoRA was better.

**Here:** g9's ternary edits (straight-through method) scored 13 of 64 against 26 for ordinary edits, which
agrees with LoTA-QAF's task-tuning result. A ternary edit that merges into the DNA is the way to keep the whole
body ternary. It is worth a trial only if a merged body is needed for speed. Changing the DNA's architecture
itself (SubLN, new attention, memory layers) means continued pretraining at billions of tokens, which free CPU
runners cannot do in a night. Earlier sessions confirmed this: every ternary model trained from nothing here
stayed weak.

## 5. Engrams and continual learning

- **DeepSeek Engram** ([2026](https://arxiv.org/abs/2601.07372), [code](https://github.com/deepseek-ai/Engram)):
  "conditional memory" is a large table of embeddings indexed by hashed N-grams of the input. It is looked up in
  constant time and gated into the hidden state. It is added beside mixture-of-experts layers and trained with the
  model; at 27B it beat an equal-size MoE. The table can live in host memory with under 3% overhead.
- **Sparse memory finetuning** ([Lin et al., Meta 2025](https://arxiv.org/abs/2510.15103)): memory layers whose
  update touches only the slots a new batch uses much more than ordinary text does (ranked by TF-IDF). Learning a
  stream of facts, the held-out score fell 89% with full fine-tuning, 71% with LoRA, and 11% with this method.
  Tested on facts, not yet on skills.
- **Test-time training** ([Akyürek et al. 2024](https://arxiv.org/abs/2411.07279)): before answering, train a
  small LoRA on the task's own examples, with augmentations. Large gains on ARC; per-task edits worked better
  than one shared edit there.

**Here:** our engrams (`team/engram.py`) write one small edit per solved task and recall it by shared words. That
fired on 8 of 32 tasks and showed no effect. The research suggests two better forms. (a) Test-time training:
when a task comes, recall checked rows of similar tasks (by the organ, the task kind, or embeddings rather than
shared words) and train a small edit on them for this task. That costs about a minute on a CPU. (b) Engrams as
sparse memory: they hold what the nightly cells did not learn, and they become training rows for the next
night's cells (consolidation, as sleep does). DeepSeek's form needs pretraining and is out of reach here.

## 6. Training faster

- About **10 times** the full fine-tuning learning rate is best for LoRA (Thinking Machines). Our rate is 2e-4;
  test 5e-4 to 1e-3 with fewer passes.
- **Only the answer tokens carry the loss**, and only their logits are computed: `grow.py` already does this.
- Holding the frozen DNA as int8 ternary values (section 1) cuts memory roughly in half against bf16. That allows
  longer rows without recomputation, and larger DNAs.
- Fewer, better rows: pairs and failures teach more per row than another copy of a solved task.
