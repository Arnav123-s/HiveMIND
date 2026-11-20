# Can choosing existing answers get the hive to five unseen kinds?

Across six recorded sittings, even a chooser with the answer key could cover **4/10 kinds** by selecting among every distinct answer actually observed. The G52 after-body alone produced correct worker answers to five questions, enough for **1/10 kinds**, and delivered one question correctly, enough for **0/10 kinds**. Within the G52 after-body alone, reaching five kinds would require at least five additional distinct correct worker answers even with perfect selection. Across all six archives, the analogous minimum is one additional correct answer in a partially solved family and a chooser that delivers the right answers. A new worker, a repaired program or a computation that combines old programs can expand that supply. [Protocol](protocol.md) · [Case-level provenance](ledger.json) · [All per-kind counts](historical.json)

## How the target is scored

The fixed official exam contains three questions from each of ten kinds that training excludes. A kind passes when at least two of its three answers are correct. The gate measures a retained body against a candidate on that same public exam each generation. In G52, 1/30 describes questions answered correctly. The separate 5/10 goal requires passing five kinds. The candidate G52 was dropped and G51 remained the release in the audited revision. [Exam generator](../../../exam.py) · [Kind criterion](../../../grow_record.py) · [G52 release decision](../../../../docs/reads/g52.md) · [Retained body](../../../../cells/body.json)

| Recorded sitting | Delivered questions /30 | Delivered kinds /10 | Any recorded worker right /30 | Kinds a perfect recorded-worker chooser could pass /10 |
| --- | ---: | ---: | ---: | ---: |
| G50 before | 3 | 1 | 5 | 1 |
| G50 after | 3 | 0 | 6 | 1 |
| G51 before | 1 | 0 | 4 | 1 |
| G51 after | 3 | 1 | 5 | 2 |
| G52 before | 2 | 1 | 2 | 1 |
| G52 after | 1 | 0 | 5 | 1 |
| Best possible choice across all six archives | 4 distinct questions ever delivered correctly | 1 | 10 distinct questions | 4 |

The last line combines the same 30 prompts across generations by taking any observed success per question. The six rows above it represent separate executions. Before/after results on the same base can vary. Every sitting lacked a recorded member verdict on one or two tasks; the ceiling includes only observable answers. It does not predict what those workers would say on a fresh attempt. We verified all 48 archive digests and matched the prompt hash of all 30 questions across all six arms. [ZIPs and original GitHub runs](../../atlas/pulse/artifacts.json) · [Archive rebuild](audit.py)

## What the frozen entrants actually returned

The new typed table composer and the worker-file recovery route were evaluated on the real input each user provided. The official runner starts a new directory and passes the request text. It provides no separate input attachments. Before inspecting any key, the selector received the raw, anonymous message and initially empty file map. The post-worker route also received only the same sitting's raw Python attempts and visible report. Independently, an examiner regenerated each official question, matched the prompt hash, and scored the sealed submissions. A withheld proposal falls back to the archived body in the combined result. [Grade-free extraction](observations.py) · [Frozen submissions](decisions.json) · [Official case scores](results.json)

| Solver or archive | G51 after | G52 after |
| --- | --- | --- |
| Typed composer alone | 0/30 correct, 30 withheld | 0/30 correct, 30 withheld |
| Existing full hive | 3 correct, 9 wrong, 18 withheld | 1 correct, 13 wrong, 16 withheld |
| Composer, original workers and qualified recovery | 3 correct, 9 wrong, 18 withheld | 1 correct, 13 wrong, 16 withheld |

The table entry point required a separate flat input file on all 30 requests. The relay's public-example contract fit none of the 30 user questions. It had 236 existing Python attempts across the G51 requests and 206 across G52, and 18 and 16 visible declines respectively. Consequently no replacement file or answer reached the official checker from either route. This is a measured interface and task-coverage gap. The typed composer's performance on independently supplied tables can still reward real planning within that input contract. [Entrant source and frozen hashes](run_entrants.py) · [Grading and fallback rule](score.py)

### Post-audit inline-table retest

After seeing the initial input mismatch, a separate developer built one inline-table transport without access to official questions or answers. Its frozen version accepted named, unambiguous table blocks in development. The grader called its ordinary entry point on the same thirty complete messages before opening the score ledger. The transport bound **0/30** official questions. Both the unmodified rules planner and the transport plus rules planner withheld all thirty. G51 and G52 fallback scores and every original per-task grade stayed identical. No further parsing rule was added. This measures the proposed bridge's coverage on a previously examined exam. [Retest protocol](transport-protocol.md) · [Frozen decisions](transport-decisions.json) · [Official retest](transport-results.json)

## Fresh direct native trial

A separate bare-model trial generated one new, non-release request from each held-out family and supplied the original raw user text to t80. All ten true native replies were sealed before grading. The grade moved from **0/10 tasks** as reports to **1/10** when a complete, generically bound file was delivered. Six outputs reached the 128-token limit. This one new draw per family measures candidate supply and delivery; the 30-task official kind count stays as reported above. [Fresh-score report and actual working CSV](native_probe/README.md)

## Which two G52 pulse deliveries were wrong?

The original two wrong deliveries came from the **separate 64-job pulse**. On `h20000524_00`, the hive delivered a CSV with the wrong heading and eleven rows when four were requested. On `h20000525_02`, the delivered LRU cache passed 379 of 423 hidden checks; its key ordering failed. In both jobs all three recorded workers failed the full task. The other ten failed G52 pulse jobs originally withheld a result. Two of those withheld duration files were recovered in PR #122. [Actual reports, reasons and source digests](ledger.json) · [Original pulse comparison](../../atlas/pulse/composed/README.md)

The four-even-numbers answer and the 8.0432-year compound-interest answer came from a different 32-request archived school comparison. The fast specialist even supplied the correct interest time, about 7.7016 years, in its archived proposal. Neither school example establishes the cause of the G52 pulse failures. [Separate school replay](../../atlas/dissent/README.md) · [School proposals](../../atlas/dissent/results.json)

## Reproduce

From the repository root, use the repo's Python environment.

```sh
P=training/experiments/verified_growth/release
python "$P/audit.py" --out /tmp/hive-fixed-history.json
python "$P/run_entrants.py" --sdk /path/to/python-wasi-sdk --out /tmp/hive-fixed-decisions.json
python "$P/score.py" --decisions /tmp/hive-fixed-decisions.json --sdk /path/to/python-wasi-sdk --out /tmp/hive-fixed-scores.json
```

The optional post-audit transport comparison uses the same two-stage selection and grading.

```sh
python "$P/run_transport.py" --bridge-sha256 17d058b893caf48ce7e1f9c756c6de8101bdcf4e750fd19410461b7d1ba51498 --out /tmp/hive-transport-decisions.json
python "$P/grade_transport.py" --decisions /tmp/hive-transport-decisions.json --out /tmp/hive-transport-scores.json
```

To rebuild the public compact ledger and grade-free inputs from the original worker ZIPs, download the 48 records in the linked manifest as `<artifact-id>.zip`. The raw inputs store question text and the two sittings' worker drafts; only the historical ledger has job IDs, verdicts and kind identifiers.

```sh
python "$P/audit.py" --archives /path/to/zips --write-ledger /tmp/hive-fixed-ledger.json --out /tmp/hive-fixed-history.json
python "$P/observations.py" --archives /path/to/zips --out /tmp/hive-fixed-inputs.json.gz
```
