# How the hosted and native comparisons are scored

## Generation time

Run 44857277686 takes the full growing-body path on G55's retained body. Its input training archive comes from G56 run 44776442973. The SHA-256 of the original archive is `24775857ee256269a5129cfe9c375b60d84c23b2cbc06a4293f046c02a59d492`. The branch checks the extracted rows and failures before use. It does all 20 CPU slices with a budget of 85 minutes each. Dream jobs have 43 minutes including setup. The gate uses G55's fresh-exam seeds, checks those results in blocks, and also sits the official fixed held-out and chat exams. The branch token has read-only permissions and the run writes its proposed body and verdict to a run artifact. [Pinned workflow](https://github.com/Arnav123-s/HiveMIND/blob/be3a12a/.github/workflows/grow.yml) · [Run](https://github.com/Arnav123-s/HiveMIND/actions/runs/44857277686)

Measure elapsed wall time from dispatch to the last required job's completion. Report queue time separately where job timing permits. Count every requested slice, its completion status, optimizer steps, memory-guard passes skipped, examples excluded by maximum length, and study rows untouched when the clock expires. A missing slice or missing record gives an unknown skip count. It cannot be interpreted as zero. The historical clock for comparison is G55's 308.70 minutes. Because the trial shares runners with the live G57 generation and draws fresh practice, the wall-clock difference is observational. [Historical timing breakdown](../astra_cpu/budget.md)

## Fixed held-out exam

Use the unchanged official task generator, task identifier and grader, with three instances per kind. A generation's fixed exam nominally contains 30 instances across ten kinds. Report available paired tasks, missing results and passes per kind for both arms. The existing generation read defines kind-level success. Keep this metric separate from the six-item worker-order panel and from the new synthetic training prompts. [Official exam implementation](../../exam.py)

The paired worker harness pins the roster to the 25 adapters in the kept G55 body and verifies their file digests. Both arms use the same runtime, 900-second task cap, eight-way task assignment, empty working memory, and checked training-task text index. The treatment enables a first-turn request to inspect inputs and assert examples, scoped GET reuse and public contract checks. The grader runs after the worker. A hard boundary call is eligible only where the request licenses it. The six-task panel and this fixed exam have separate outcome claims. [Pinned paired diagnostic](https://github.com/Arnav123-s/HiveMIND/blob/ac77ff3/.github/workflows/exam.yml)

## Training and retention

Count one generated specification once, after both the hinted and unhinted offers run on the same model. Only a failed unhinted offer paired with a fully verified hinted program produces a training row. One example passing 24 input cases counts as one admitted specification. Evaluate distinct post-training prompts against the exact parent, with all parameters other than the adapter fixed. [Training protocol](../hint_dream/protocol.md) · [Withheld transfer commitments](../hint_dream/transfer-manifest.json)

For the archive, a correct answer available somewhere in a recorded pair counts as candidate availability. An improvement in delivery requires the hive actually choose and return the answer and an independent check pass. A training preference score measures a proxy for a model update. Report these independently of three consecutive live generations' old-kind gains and losses. [Replay and archive design](../replay_archive/README.md)
