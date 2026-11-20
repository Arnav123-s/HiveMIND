# Selecting and running a table program from an English request

The earlier Atlas proposer received its own generated program with each assignment. Here the solver receives only a person's request and the contents of one CSV. Six frozen selectors receive identical requests, ground column and category names through the same binder, then run a typed program. An independently written SQLite query grades the returned JSON. No selector receives an operation label, family ID, grade or answer key. [Original 72-case study](../../atlas/proposer/README.md) · [New frozen protocol](protocol.md) · [Solver](../composer/solver.py)

Each of the six primary patterns has three requests, one each about an orchard, helpdesk and clinic. The same question must work on two differently sized and ordered tables. A correct answer on both tables earns a request pass. All three requests must pass to count a complete pattern. Sixteen of the 18 primary questions produce different correct values on the two inputs. The 54 table evaluations share three schemas and two base row layouts, so they do not represent 54 independent samples of real traffic. The nine extra requests include three earlier capabilities, three answerable adjacent requests, and three questions that require clarification. The group names and numbers are invented. Both wordings and expected values were withheld from the solver author through its source freeze. [Sealed fixtures](manifest.sha256) · [Questions](panel/requests.json) · [SQL examiner](panel/freeze.py) · [Independent arithmetic cross-check](panel/check_keys.py)

The solver author’s teaching and development examples included an equality filter followed by a scalar sum and unfiltered grouped count and rank. They omitted filtered group sums and filtered group rankings by count and sum. Those latter three patterns account for nine requests. The grammar of this particular task set is related to the task description agreed upon before the test. It is separate from HiveMIND's official held-out release exam. [Training examples](../composer/learner.py) · [Solver protocol](../composer/protocol.md)

## No external example

| Selector | Paired requests correct /18 | Complete patterns /6 | New-combination requests /9 | Correct / wrong / withheld on 36 primary tables |
| --- | ---: | ---: | ---: | --- |
| One operation at most | 0 | 0 | 0 | 0 / 0 / 36 |
| Learned whole operation pair | 11 | 0 | 5 | 23 / 9 / 4 |
| Learned operations separately | 11 | 0 | 6 | 22 / 10 / 4 |
| Handwritten English cues | 13 | 1 | 6 | 27 / 5 / 4 |
| Require learned and handwritten planners to agree | 10 | 0 | 5 | 20 / 2 / 14 |
| Native 8B model selects the operation pair | 4 | 0 | 2 | 10 / 16 / 10 |

The handwritten cues passed all three unfiltered grouped count requests. Every selector missed at least one wording in each new pattern. Given “total number of visits,” several programs counted table rows even though one row can record multiple visits. All selectors except the one-operation control preserved all three simple anchors. All withheld the three answerable adjacent requests for a distinct count, a threshold count or a median. On questions lacking evidence the handwritten planner returned two unsupported numbers, including purported revenue from visits without billing rates. The native selector withheld all three such requests. [All returned plans and values](decisions.json) · [Paired and per-pattern grades](results.json)

The native engine selected the intended structural code on 6 of 18 primary requests. Across all 27 requests, it used 27 real calls and 74 predicted tokens in 526.751 seconds of summed HTTP completion time. Its grammar confines the model to the allowed operation codes or a refusal. It saw the English request and sorted header names, with zero row values or labels. The same choice applied to both CSV versions. The model never issued Python or SQL. The native chooser was frozen before its first call. Collecting choices began before the separate column binder was ready. The complete binder was frozen before any response was combined with it or graded. [Native receipts](native.jsonl) · [Frozen native client](../composer/native.py)

With perfect knowledge of which existing selector to use, one could obtain 15/18. Providing the correct structural code directly to the frozen binder gave 16/18. It still could not match the words of two grouped ranking requests to an executable plan. These are after-the-fact ceilings with access to the answer or intended structure. [Case-level diagnostics](diagnostics.json)

## One worked example from an external teacher

After the zero-shot controls were fixed, we tried giving each selector one example of the same request answered on a third table. A new 19-row table per domain came from a hash of the original frozen-panel manifest and the domain name. There was no trial selection or seed search. The independent SQLite examiner labeled each answerable request. Each teacher value was computed on data separate from both evaluation tables. No example exists for the three requests missing information, which are excluded from this comparison. Choosing this follow-up after seeing zero-shot outcomes makes it exploratory. [Teacher inputs and labels](teacher.json) · [Teacher construction](teacher.py) · [Selection protocol](../composer/qualification.md)

| Method | Correct on both tables /18 | Complete patterns /6 | Correct on new combinations /9 | Wrong / withheld paired requests |
| --- | ---: | ---: | ---: | --- |
| Existing selectors must agree, without an example | 4 | 0 | 2 | 0 / 14 |
| Repeat the example's answer | 0 | 0 | 0 | 18 / 0 |
| Qualify the plans proposed by the selectors against the example | 15 | 3 | 7 | 0 / 3 |
| Qualify the seven whole operation pairs already taught | 15 | 3 | 7 | 0 / 3 |
| Qualify all eight typed operation pairs | 15 | 3 | 7 | 0 / 3 |

The qualifying program runs on the original user's new table only if the example distinguishes a consistent choice or all qualified programs return the same target value. The three qualification methods delivered 30 correct table results and withheld six. The selector portfolio completed all three filtered sum-ranking requests. The fixed libraries instead completed all three filtered grouped-sum requests. Neither fixed library could tell two different programs apart on the teaching table for one clinic ranking question, and those programs disagreed on the new data. All three qualification methods preserved three earlier capabilities and withheld all three adjacent tasks. An external label improved this use of the existing programs. Adding the eighth structural code produced no additional correct table jobs. [Demo-qualified decisions and results](one-shot-results.json)

## Real file outputs and reproduction

A separate file check collected the first request from each primary pattern, appended “Save the answer as result.json.” and ran the real publishing CLI on both table editions. All twelve files were valid JSON and correct. Repeating all twelve requests against existing files refused the overwrite and preserved their original bytes. The whole subset uses the orchard schema. This integration check covers the file path and is separate from the blind language scores. [Captured files, return codes and overwrite checks](file-results.json)

From the repository root, run the following commands with standard Python.

```sh
D=training/experiments/verified_growth/transfer
python "$D/panel/check_keys.py"
python "$D/collect.py" --out /tmp/hive-table-decisions.json
python "$D/score.py" --records /tmp/hive-table-decisions.json --out /tmp/hive-table-grades.json
python "$D/diagnose.py" --grades /tmp/hive-table-grades.json --out /tmp/hive-table-diagnostics.json
python "$D/one_shot.py" --out /tmp/hive-table-one-shot.json
python "$D/file_check.py" --out /tmp/hive-table-files.json
```

These commands use the captured native choices. To generate new choices, start the pinned CPU server and run `python "$D/native_collect.py" --url http://127.0.0.1:18852 --out /tmp/hive-table-native.jsonl`. The collector records one answer per request and resumes after a transport failure. Use a fresh output filename for a new independent run. Pass that file to `collect.py --native`, `one_shot.py --native`, or `diagnose.py --native`.
