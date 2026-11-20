# What worked in the HiveMIND CPU trials

On two archived tasks, the hive could have returned working Python files after reporting that it could not deliver them. In both cases a worker had already written the functions. Checking those files and returning the first one that passed raised the generation 52 replay from **52 to 54 correct deliveries out of 64**. It used the original worker code, with no new model calls. Both files passed all 60 independently written inputs. These were known failures for one duration-conversion task. [Files, original prompts and independent checks](module_recovery/README.md)

On the same 64 G52 requests, combining file recovery with first-answer checks raised correct deliveries from **52 to 54** while reducing worker calls from **142 to 133**, plus two WebAssembly verification batches. The two original wrong deliveries remained. Direct calculation for the certified cases achieved 54 correct in **124 worker calls**. Across G50–52, the first-answer-plus-recovery approach raised 156/192 to 158/192 and reduced 428 calls to 404. [Same-job comparison and costs](pulse/composed/README.md)

The experiment checkout combines main at `4cbd41c` with the earlier engram and verified-learning work at `70d0f3b`. The fixed comparison commit is `896d7c8`. The trials live under this directory. The ordinary training and chat workflows still use their existing behavior.

## Try a question

From a checkout of the experiment branch, run the following command. It returns `Thursday`.

```sh
python -m training.experiments.atlas.service.ask 'Which day of the week is 2024-02-29?'
```

On an independent mixed panel, the combined local tool answered 10 of 12 answerable requests, versus one for the stock local route. Both withheld all six requests judged out of scope and gave zero wrong answers. The combined tool missed two ordinary paraphrases. The frozen study ran the local model-free routes. The ordinary model-backed chat can also attempt questions outside this comparison. [Mixed panel](service/judge/results.json)

Removing a model-library import from the calculator preserved its answers and cut median fresh-process wall time from 4.870 seconds to 0.073 seconds over 18 matched invocations for three recurring questions, using one CPU. WebAssembly shipping has separate costs. [Cold process timing](service/cold-start.json)

The same command handles supported price changes, date differences, unit conversions and depot shipping questions. Shipping executes the saved tariff inside WebAssembly and needs the project's WASI SDK. [Supported wording, examples and setup](service/README.md)

## How the cells share skills

The G51 body has one 8-billion-parameter base model and 24 specialist cells. Each cell changes a small part of how that same model responds. Their training overlaps, with extra practice in code, data, writing or finding sources. The hive can ask a second cell or call a previously checked program. A small learned memory, called an engram, can be applied for matching tasks. The earlier work on sharing learned signals and engrams is part of the combined comparison. [Active body](../../../cells/body.json) · [Runtime routing](../../../team/solo.py) · [Earlier learning and communication trials](../../reports/verified-learning/README.md)

Keeping both versions matters when the rule changes. In the earlier invoice trial, the newer rounding method was correct for one type of invoice and the older method for another. When examples left both interpretations possible and the totals differed, the hive showed the difference and withheld the batch. The shipping study below builds on that behavior. [Versioned invoice and shipping checks](../../reports/retained-skills/README.md)

## Results by problem

| Problem | What we measured | What happened |
| --- | --- | --- |
| Reuse a saved skill under different wording | One real shipping tariff, 32 English requests, two bank configurations | The original lookup priced 1 of 11 eligible requests in the single bank. A handwritten kilograms adapter priced all 11 and withheld all 21 ineligible requests. Compiling a guarded shortcut preserved that coverage and cut warm sandbox calls from 20 to 15. Qualification cost 14 calls. [Try a shipment](traces/README.md) |
| Deliver a correct file after disagreement | Actual responses from three generations, plus independent candidate checks | The two G52 file recoveries were the only changes across 192 deliveries. On another, harder 84-job program panel, verification reduced wrong answers from 49 to zero but also reduced correct answers from 35 to 28. Requiring different worker lineages lost four correct deliveries on a 32-job replay. [File recovery](module_recovery/README.md) · [Disagreement](dissent/README.md) |
| Spend fewer workers on easy questions | Real G49 first answers and independently computed arithmetic or calendar results | Keeping a first worker and verifying its whole answer reduced calls from 141 to 133, with the same 49 correct, 7 wrong and 8 withheld. The exact calculator could deliver those eight directly, for 125 calls. In the other pulse trial, the current reserve already achieved the proposed two-worker saving. [First-answer checks](pulse/one_checked/README.md) · [Reserve comparison](pulse/README.md) |
| Speed up the language model | Three native CPU prompts, 64 emitted tokens, five decoding configurations | Every arm emitted the same tokens. The ordinary model took 13.36 and 17.94 seconds in two runs. Adding a four-billion-parameter draft took 37.30 seconds. The smaller draft took 23.36 seconds. Reusing repeated prompt text took 20.04 seconds. [Model hashes, token IDs and timing](decoding/README.md) |
| Produce machine-readable answers | Same eight prompts and greedy native 8B model, with and without a grammar | Valid outputs rose from 5 to 8. Correct, parseable answers rose from 2 to 4. The same four answers had identifiable correct content in both arms. One grammatically valid list still had the wrong values. [Prompts and native outputs](grammar/README.md) |
| Estimate when to abstain | Fit on G50, calibrate on G51, evaluate on 28 new G52 requests | Confidence-based release withheld six right answers and delivered the shared wrong one. The actual after-body delivered 27 correct and withheld one. There were only eight calibration seeds. [Coverage and risk](calibration/README.md) |
| Compose skills for an unfamiliar task | Seven native 8B configurations on two withheld combinations, three phrasings each | All seven scored 0/6. On a different 18-question, output-layer replay, routing to the top two specialists raised normalized label accuracy from 14 to 15. A typed program builder assembled six event-log tasks and tied a handwritten solver at 72/72 against SQL. [Native composition and routing](composition/README.md) · [Executable proposer](proposer/README.md) |
| Repair new mistakes while keeping earlier skills | Equal-size replay updates, six specialists, 48 questions withheld from fitting | Prioritizing failures repaired six of nine observed mistakes. It simultaneously gained five and lost five on withheld questions, finishing at the incumbent's 38/48. Rehearsing six old examples preserved all six. A small archive preserved some specialists, but its chooser missed the additional case they could solve. [Retention](retention/README.md) · [Archive](archive/README.md) |
| Change the training budget and merge specialists | Real cached 8B states, 30 previously published evaluation questions | Fitting half the examples gave 24/30 with the correct domain supplied, versus 23/30 with all examples. Random half-samples reached 23–24. Lowering exchange between groups hurt the shared head by one. Plain addition scored 24/30, TIES scored 23, and DARE plus averaging scored 22. Forward-only tuning of one scale did not beat plain addition. [Budget and isolation](islands/README.md) · [Selection controls](islands/selection/README.md) · [Merge and rank controls](merging/README.md) |

The earlier generation 50 duration request also received no file. After generation 52 had produced a working version, either saved module could fill that earlier request in a backward replay. Each returned `69577` and `0s`, passed the original G50 tests, and completed eight new requests for the same contract. The handwritten reference matched both. A differently worded, valid request fell outside the guard. [Recovered G50 file and transfer panel](module_recovery/transfer/README.md)

## What a test can miss

A deliberately incorrect clock used 61 seconds per minute. It passed all 24 round-trip and consistency checks because its parser and formatter made the same mistake. Both real G52 programs passed the same 24 checks. Independent known values separated them. The wrong clock passed 8/60 and each real program passed 60/60. [Executable counterexample](grammar/metamorphic/README.md)

The release record and these studies answer different questions. G41 scored 58/64 on its own cohort. G52 scored 1/30 on its fixed unseen exam. This sprint measured neither a new whole-body release score nor an end-to-end generation under three hours. Models trained on newly separated transformer layers, an archive of eight actual bodies, and sustained improvement across generations still require new paired runs. [Earlier record, research sources and open comparisons](atlas.md)


## Verification and the live run

The combined baseline passed 1,275 repository tests and nine subtests. From a clean checkout of the public experiment branch we independently reproduced the two-file recovery, all 192 replay decisions, the independently graded grammar scores, the conformal results, the executable proposer and the merged-head rankings. The native timing and raw model outputs have separate reproduction commands in their study directories.

During the experiment, the independent hosted G53 run was in progress. GitHub reported lost communication with two training runners, for data and writing slices. Those annotations do not identify the underlying cause. A live generation requires collecting or recovering its slices before its runtime or score can be compared fairly. [Data slice](https://github.com/Arnav123-s/HiveMIND/actions/runs/44649281647/job/136025526418) · [Writing slice](https://github.com/Arnav123-s/HiveMIND/actions/runs/44649281647/job/136025526657)
