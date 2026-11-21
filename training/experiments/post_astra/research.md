# What the external results tell us about HiveMIND

## Choosing a program

Shi and colleagues added irrelevant facts to arithmetic word problems. That establishes a reason to test shorter instructions. A stray import in one generated Python file does not identify its cause. Repeat sampling with the same model and actually execute the chosen output on the target interpreter. [ICML paper](https://proceedings.mlr.press/v202/shi23a.html)

RAV reports MBPP Full pass@1 of 75.28% for its base, 76.40% with routing and aligned training, 85.00% with routing and verification, and 85.20% with all three. Its candidate pool and verification budget matter. S* spends extra inference on diverse programs and distinguishing inputs. ZeroCoder reports up to 14.5% improvement over its 7B base in its label-free setting and 21.6% with DyB4. Neither paper makes agreement between two programs a guarantee. An input where two programs differ identifies a real choice. An independently specified expected answer can resolve it. [RAV ablation, Table III](https://arxiv.org/html/2608.03341v1) · [S*](https://aclanthology.org/2025.findings-emnlp.865/) · [ZeroCoder](https://arxiv.org/abs/2604.07864)

## Learning from generated work

SPADE jointly trains a proposer and a solver. It reports a 5.3-point average gain over its strongest fixed-environment baseline at a scale up to 30B parameters. Absolute Zero Reasoner reports a 15.2-point math-average improvement for its 7B coder trained with executor rewards. PopuLoRA studies populations of adapters trained through reinforcement learning. A CPU imitation of a verified, hinted completion uses a different update. For HiveMIND, measure the fraction of paired prompts where a hint changes failure into success, remove the hint from the training example and grade the trained adapter on separate tasks. [SPADE](https://arxiv.org/abs/2608.19197) · [Absolute Zero Reasoner](https://arxiv.org/abs/2505.03335) · [PopuLoRA](https://arxiv.org/abs/2605.16727)

## Keeping old skills

OpenBMB's 4:1 ratio means four **new task samples for each replay sample**, giving 20% replay. Its reported 80–99% reduction is relative to the general-score drop under ordinary fine-tuning on its four vision-language models. Inspect the denominator when reporting forgetting. With 64 questions, a single newly lost answer is already 1.56% of all questions. For a claim about old skills, report the actual previously solved denominator, gains and losses. [Self-Replay Fine-Tuning](https://openbmb.cn/en/blog/self-replay-fine-tuning)

HyperAgents reports 0.084 to 0.267 on full Polyglot with the final system. ELITE reports 60.0% to 85.6% on SWE-bench Pro through changes to an agent's implementation. HiveMIND stores numerical adapters. To establish a benefit from archiving these, load the actual weight files, compare each worker's behavior on the same independent development prompts and measure whether the chooser delivers more correct answers on new inputs. A list of bodies alone cannot establish retention. [HyperAgents](https://arxiv.org/abs/2603.19461) · [ELITE](https://arxiv.org/abs/2611.21056)

## Time and stopping

Stockfish pairs games to reduce differences caused by opening positions and evaluates evidence under an explicit probability model. A fixed-alternative likelihood ratio on changed answers has different assumptions from its generalized test. HiveMIND also uses a final keep/drop rule over completed paired seeds. Count changed historical verdicts, early exits and elapsed minutes separately. A test that always continues preserves every historical verdict by construction and saves no work. [Fishtest mathematics](https://official-stockfish.github.io/docs/fishtest-wiki/Fishtest-Mathematics.html) · [Improving Wald's approximate SPRT](https://arxiv.org/abs/2410.16076)

The prior Atlas measurements cover the tested CPU/model configurations for speculative decoding, steering, merge variants, conformal abstention, forced lineage diversity and weight-space composition. PR #132's inherited worker profiles and PR #134's pre-execution choice also have measured outcomes. These baselines are enough to retire those exact implementations. None of their scores measures the five new tickets. [Atlas studies](https://github.com/Arnav123-s/HiveMIND/pull/122) · [Inherited profiles](https://github.com/Arnav123-s/HiveMIND/pull/132) · [Worker instructions](https://github.com/Arnav123-s/HiveMIND/pull/134)
