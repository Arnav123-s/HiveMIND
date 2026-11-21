# Can a dissenting third worker fix the delivered answer?

On the four later generations, **the hive delivered 200 of 256 fresh jobs correctly. Always taking the minority on the six eligible text jobs would have delivered 197**. It fixed one answer, spoiled four and replaced one correct answer with another correct answer. The frozen public-format and worker-history checks found no supported switches. A selector with all the answer keys could have added only one correct answer on the six text splits. [Selection protocol frozen before grading](protocol.md) · [Outcome counts](results.json)

The sole recoverable case was a G56 account simulation with refused withdrawals and periodic interest. The three workers each finished in one successful program execution with no hints. The two-to-one majority gave the wrong final balance. The minority gave the right one. All three answers had the requested structure. Event counts and answer format give the chooser no reason to break this tie in quality. Verifying the order of the transactions would require an independent reading of the stated account rules. This example was inspected after grading. [Fresh G56 record](../../../../docs/reads/g56.md)

| Generation group | Jobs | Stock correct | Final wrong with any recorded worker right | Confirmed, identifiable 2–1 splits, text / files | Switch every text minority, gains / losses | Resulting correct |
|---|---:|---:|---:|---:|---:|---:|
| Development G50–52, after | 192 | 156 | 11 | 11 / 3 | 0 / 4 | 152 |
| Development G50–52, before | 192 | 156 | 13 | 7 / 5 | 0 / 1 | 155 |
| Evaluation G53–56, after | 256 | 200 | 6 | 6 / 4 | 1 / 4 | 197 |
| Evaluation G53–56, before | 256 | 202 | 6 | 5 / 5 | 0 / 1 | 201 |

Among the six later after-body jobs where any worker was correct but the final delivery failed, **five had no confirmed delivery to overturn**. The one remaining job was the account simulation. Of the 256 jobs, 206 lacked three complete worker answers on an otherwise confirmed delivery, 36 had no confirmed delivery, three lacked a unique voting pair, and one had a truncated answer or later retry. Ten met the observable split conditions. Each had a recorded grade for the minority. On both earlier and later records, the hypothesis that a worker with fewer execution failures and hints would beat both voting peers produced zero switches. The extra calibration-gated rule consequently stayed off. We did not fit LightGBM on such few switch opportunities. [Runtime-to-grade ledger](records.json.gz)

The observed gain rate from automatically switching an eligible text answer on the later after bodies was **1/6 (16.7%)**. Its two-sided exact 95% binomial interval spans **0.4% to 64.1%**. The same rule in the before arms gained 0/5, with an interval from 0% to 52.2%. No precision can be estimated for a selector that made zero switches. The arms share prompts and ancestors, so combining them as independent draws would misstate uncertainty. For the four later file splits, the archived individual grader recorded zero opportunities to fix an incorrect final file via the minority and one previously correct case that substitution could spoil. A worker grade alone does not reconstruct the bytes the user would have received. [Scores and full denominators](results.json)

## Where the evidence comes from

We verified the SHA-256 of 112 uploaded archives, 16 per generation across G50–G56. The collector opens only the eight fresh jobs for each arm and seed, for 896 graded deliveries in total. No fixed-exam files are opened. Both earlier aggregate grades and some individual jobs had been published before this study; the split is chronological retrospective evidence. The later generation totals were not used to select features or thresholds. Each worker earned its historical grade on its own answer and available files. Different printed answers can both pass a task. Individual tests are not exposed to the selector. [GitHub artifact IDs and digests](artifacts.json) · [Historical grading implementation](../../../exam.py)

The runtime stage uses the user request, the recorded worker answer events, execution-failure and hint counts and the stock delivery report. It requires exactly three complete worker answers, exactly one pair under the hive's text-agreement function, and a stock answer supported by both in that pair. It excludes truncated visible event payloads, later retries, multi-part streams and ambiguous agreements. Text switching requires a job with no evident requested file. The public contract recognizes only explicit exact line counts or a requirement for JSON-only output. Violating the same declared rule on both majority answers while the minority satisfies it is eligible evidence. The chronology-gated variant also requires a strictly better execution history than both majority members and at least five development switches with 80% observed gain precision. Reconstructing the existing delivery tells us whether there is a stock majority to challenge; its correctness comes only from the scoring stage. No worker code runs during this study. [Replay and independent scoring](replay.py)

## Reproduce

From the repository root, re-score the committed observations using Python's standard library.

```sh
python -m training.experiments.astra_retention.minority.replay --out /tmp/hive-minority.json
```

To reconstruct the ledger from original ZIP files, name each archive with its GitHub artifact ID followed by `.zip`, use the repository's Python environment and supply one or more archive directories.

```sh
python -m training.experiments.astra_retention.minority.replay --archives /path/to/zips --ledger /tmp/minority-records.json.gz --out /tmp/hive-minority.json
```

This study measures opportunities to change an already delivered fresh answer. It provides no new worker capability, official held-out credits, inference-speed measurement or production change.
