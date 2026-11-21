# How much of a retained body can teach the next one?

At equal target-token cost, mixing past successful programs into a small CPU learner rescued **one net old program choice out of 169** under an imposed forgetting rate. The newer questions scored 6/7 in every arm. Removing the forgetting assumption reversed the old result. These results give little support for imposing a 4:1 replay schedule on the 8B trainer. [Study protocol](protocol.md) · [Exposure and paired scores](summary.json)

## The source of the examples

G55 was kept. Its practice rows were collected before it was trained, when the trunk was G53. G56 practice used the retained G55 body. The G56 challenger was subsequently dropped. The two cumulative archives contain 8,247 and 8,820 rows across program, completion and preference formats. The comparison takes G55's recorded final roster, checks that it matches G56's starting roster, and matches exact named worker IDs. Worker weights may be older than the collection generation. [Generation decisions](../../reports/generations.jsonl) · [G56 history](../../../docs/reads/g56.md)

| Data available | Named first/fix candidates from kept members | Individually evidenced, distinct task/programs | Named / individually evidenced from G55 trunk |
| --- | ---: | ---: | ---: |
| Before G56 collection | 105 | 20 | 0 / 0 |
| Fresh G56 | 163 | 3 | 106 / 1 |
| Cumulative through G56 | 268 | 23 | 106 / 1 |

The combined archives omit individual checker receipts. The row writer admits individually checked programs and has a fallback for members in an agreeing group. An emitted first/fix row marked `agreed=false` therefore establishes an individual pass under this writer. Agreement alone leaves the source of the positive label ambiguous. This conservative test yields 20 older task/program pairs from nine workers in eight kinds. The three newly evidenced programs came from G55 trunk, G55 code and G53 data. Across both captures, 11 of the 23 programs cover data, nine code, two sources and one words. The 400-place reservoir could fill only 23 positions even after adding the later capture. [Admission and row writer](../../grow.py) · [Actor and program hashes in primary results](results.json.gz)

## Fixed exposure, then fixed target-token cost

The learner predicts the next byte of Python from its two preceding bytes, conditioned on a kind predicted from the question. It ranks the archived chosen and rejected programs by mean likelihood. Both candidate texts are already available at scoring time. The targets measure agreement with the historical preference record. A separate model that generates and executes a program would be needed to measure task completion.

The time boundary is the generation archive. Within each archive, a fixed hash assigns complete normalized questions to a 25% holdout. Both programs in every scored pair were excluded by exact text from training across both generations. Seven G56 preference questions were absent from G55. The 169 old pairs span 111 questions, so changes on those pairs need not be statistically independent. Near-duplicates may remain. The base learned from 1,313 old program demonstrations. The adaptation pool contained 195 fresh programs, including 70 checked teacher lessons, and 19 older individually evidenced replay programs after holdout exclusions. Sampling cycles through task organs and kinds. No archived program is executed. [Runnable learner and split](replay.py)

| Adaptation | New / old rows in primary | New / old target bytes | Old correct with decay | Old correct without decay | Fresh correct, either decay |
| --- | ---: | ---: | ---: | ---: | ---: |
| Frozen | 0 / 0 | 0 / 0 | 110/169 | 110/169 | 6/7 |
| New only | 120 / 0 | 60,887 / 0 | 106/169 | 110/169 | 6/7 |
| Two old per new | 40 / 80 | 19,244 / 81,449 | 107/169 | 109/169 | 6/7 |
| Four old per new | 24 / 96 | 10,222 / 98,471 | 108/169 | 109/169 | 6/7 |

At 2% decay per row, the 4:1 arm cost 79% more target-byte updates than new-only and displaced 96 distinct fresh rows. It corrected 17 of new-only’s old choices and spoiled 15. The 2:1 arm gained 15 and lost 14. Without decay, both ratios gained 12 and lost 13. All arms made the same individual decisions on the seven fresh pairs. [Primary per-pair scores](results.json.gz)

We then fixed the secondary comparison at **60,887 target-byte updates** before scoring it. The 2:1 stream reached 25 fresh and 48 replay programs, and the 4:1 stream reached 14 fresh and 54 replay programs. Each ended partway through its last program. At matched cost, both scored 107 old with decay against 106 new-only, with 14 gains and 13 losses. Both scored 109 against 110 without decay. A byte is a target token for this learner. The lookup cost, prompt processing and tokenization of a transformer differ. [Supplemental protocol](dose-protocol.md) · [Equal-cost scores](dose-results.json.gz)

## Where failure feedback can enter safely

The practice ledger contains 881 G55 failures with unknown delivery status. G56 added 19 failures with an explicit status. Eleven had delivered a wrong answer, including seven compound tasks, two name sorts and two Markdown-to-CSV tasks. Eight produced no delivery. Existing dreams revisit recorded failures, and lesson selection already recognizes kinds with known wrong deliveries. The 687 historical and 35 fresh preference rows contain no complete worker-verdict vector. A right answer outside the agreeing group or a chosen/rejected pair alone cannot establish that exactly two other workers were wrong. [Failure recorder](../../grow.py) · [Lesson selection](../../lessons.py) · [Independent G53–G56 minority replay](minority/README.md)

The diagnostic dry run assigns whole normalized questions by hash, checks a trusted collection-source field and practice seed, and rejects unregistered makers, release-only families and compound tasks containing them before opening feedback. Applied retrospectively to the 900 **already public practice failures**, it assigned 653 distinct questions to diagnostic use and 228 to reserve. The admitted side contained 10 delivered-wrong and six undelivered records with usable feedback. Eight canaries exercised rejection and reservation without reading a feedback payload. This is an admission-path check. A genuine prospective assessment requires separately sourced diagnostic tasks and privately retained release families, inputs and labels. [Replayer](diagnostics.py) · [Counts and controls](diagnostic-results.json)

An earlier alternative chose among already available workers using previously labeled examples. On 18 fresh short-answer questions in six familiar domains it reached 17/18 against 15/18 for the incumbent. On 48 earlier questions it gained four answers and lost two. Its substrate, task and population differ from the chronological program ranker measured here. [PR 123 research](https://github.com/Arnav123-s/HiveMIND/pull/123)

The separate G53–G56 replay found six eligible majority/minority text decisions. Always choosing the minority gained one answer and spoiled four, reducing delivery from 200/256 to 197/256. An independent attempt to choose the best specialist before seeing the request's answers had only nine earlier, sole-worker practice wins across six workers. It tied the first worker at 176/235, against 180/235 for stock multi-worker delivery. [Minority outcomes](minority/README.md) · [Specialist choice and coverage](specialists/README.md)

A retrospective parent-history check supplied prior records for six new workers on 60 later requests. The child and the first worker each scored 39/60 there. Following the documented parents recovered information but produced zero additional correct selections under the frozen two-profile rule. [Inherited worker history](specialists/heritage/README.md)

## Reproduction

The original all-rows ZIPs each contain `rows.jsonl` and `failures.jsonl`. The primary result records both row checksums, and the diagnostic result records both failure-ledger checksums. Use the repository's Python environment, save the two ZIPs under the names below and run from the repository root. [G55 run and artifact](https://github.com/Arnav123-s/HiveMIND/actions/runs/44728930517/artifacts/14630086449) · [G56 run and artifact](https://github.com/Arnav123-s/HiveMIND/actions/runs/44776442973/artifacts/14653659254)

```sh
unzip -p g55-all.zip rows.jsonl > /tmp/hive-g55-rows.jsonl
unzip -p g56-all.zip rows.jsonl > /tmp/hive-g56-rows.jsonl
python -m training.experiments.astra_retention.replay --g55 /tmp/hive-g55-rows.jsonl --g56 /tmp/hive-g56-rows.jsonl --out /tmp/replay.json.gz
python -m training.experiments.astra_retention.replay --g55 /tmp/hive-g55-rows.jsonl --g56 /tmp/hive-g56-rows.jsonl --target-bytes 60887 --out /tmp/dose.json.gz
python -m training.experiments.astra_retention.diagnostics --g55-zip g55-all.zip --g56-zip g56-all.zip --out /tmp/diagnostic.json
```
