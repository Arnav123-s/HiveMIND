# Getting from correct worker answers to unseen kinds

HiveMIND's release target is five of ten unseen kinds. Each kind has three fixed questions, and two correct answers earn a pass. The retained G51 body passed one kind on its own fixed sitting (3/30 tasks). The rejected G52 candidate delivered one correct question and passed zero kinds. Even choosing the right recorded worker with hindsight would have passed just one kind on G52. Pooling every recorded worker from six sittings of G50–G52 would have passed four kinds. Reaching the fifth requires generating at least one new correct answer as well as selecting it. The six sittings reuse the same questions. [Official grades, worker ceiling and records](release/README.md)

| Goal | Direct measurement | What is still missing |
| --- | --- | --- |
| Five of ten unseen kinds | G52 delivered 0/10. The available workers from six archived sittings could cover at most 4/10. | A new correct candidate in at least one additional kind, and a way to deliver the correct candidates. |
| Improvement that lasts | The archive chooser gained two and lost zero on 18 fresh questions. It gained four and lost two on an older set of 48. | Multiple successive updates that retain earlier wins on independent trials. |
| Three hours per generation | G51 took 390 minutes and G52 took 347. | Reduce the longest dependent stages and validate the resulting body on the complete release exam. |

The two incorrect G52 pulse deliveries were a CSV with the wrong header and row count, and a cache implementation that failed 44 of 423 checks. Both lacked a passing worker. The wrong even-number and interest answers belonged to a separate 32-job evaluation. [Pulse archive and original task sources](release/README.md)

## Why the G52 duration replay gained two answers

In both jobs, worker 3 had already executed a program and saved the requested module. Its peers failed to import that module in their own directories. The live handoff required a second worker to confirm the answer. The examiner later passed worker 3 on its hidden examples. The earlier 52-to-54 replay supplied a handwritten duration checker at selection time, so its two additional deliveries cannot count as evidence of general improvement. The 142-to-133 call estimate is a different replay of early stopping and still needs an independent live comparison. [Original events and control handoffs](delivery_audit/README.md)

The gate's diagnostic ZIP also omitted the named files. On 12 independent scenarios, a separate post-grading collector retained all 18 available worker files, compared with zero under the existing upload patterns. It preserved incompatible and wrong submissions too. In both replays, four jobs delivered the correct file or response, two were wrong and six were withheld. [Independent reproduction](delivery_confirmation/README.md) · [Diagnostic change for review](https://github.com/Arnav123-s/HiveMIND/pull/124)

On 12 other staged Python jobs, two workers always gave the same printed example when both submitted a file. Running their files on additional valid inputs exposed four disagreements. Withholding those four removed two wrong deliveries and two correct ones. Two of the three pairs that matched on every additional input still gave a wrong file. The comparisons identify contradictions without supplying an answer key. Selecting the right program still requires independent evidence. [Sandbox runs and independently sealed grading](delivery_audit/probes/README.md)

A separate live CPU trial tested whether writing a file that the model had already returned could ever change a real grade. It used ten newly drawn questions, one per held-out family, and a frozen rule that writes complete, explicitly named file blocks. Plain text scored 0/10. Writing the same answers' files scored 1/10. One delivered CSV had all six required rows and named the correct winner. A second file had ten rows where five were required. Six replies reached the 128-token limit. This one-per-family test cannot establish a release kind pass. [Native responses, physical CSVs and independent grades](release/native_probe/README.md)

## Can the hive put a program together?

The earlier program builder received its plan along with each job. This test instead gave each selector an independently written English work order and a CSV. The returned answer had to be correct on two different versions of the input. The handwritten planner solved **13/18** requests, the fitted operator selector and whole-plan classifier each solved **11/18**, and the native 8B planner solved **4/18**. A single operation solved none. Providing **one independently labeled worked example** raised the portfolio to **15/18** and three complete patterns out of six. The library limited to seven previously taught operator pairs also reached 15. The three unresolved requests were withheld. [Transfer study, raw model replies and independent SQL grades](transfer/README.md) · [Runnable file publisher](composer/README.md)

The final publish command was checked through 156 fresh invocations. On the 54 table inputs the version without examples wrote 33 correct files and nine wrong files, and withheld 12 times. On the 48 answerable inputs for which an external example was supplied, it produced 36 correct files, zero wrong files and 12 abstentions. The six underspecified inputs had no examples and were excluded from that second comparison. [Physical file and abstention audit](transfer/checked_delivery/README.md)

A typed sum can still compute the wrong thing. One version summed occupied days when the user asked for rent and had supplied no prices. On the official exam, the file extractor and table entrants all fell back to the incumbent. A generic inline-table bridge also accepted zero of the thirty official messages. [Grounding failure](inline/README.md) · [File-recovery controls](file_relay/README.md) · [Official fallback results](release/README.md)

## Can an archive chooser improve without losing skills?

On 18 separately written questions scored from actual native t80 outputs, the incumbent answered 15 correctly. Choosing the archived worker whose earlier labeled example was closest reached **17/18**, with two gains and no losses. That was the most the stored workers could deliver. They all chose the wrong phase of water at 121 °C and one atmosphere. A direct nearest-label memory reached **18/18** when allowed the historical feedback. These were genuinely new questions in six familiar, short-answer domains. They do not measure unseen task kinds.

Across an earlier 48-question sequence, the same chooser reached 40 versus the incumbent's 38, with four gains and two regressions. Keeping the chooser's original 42 labeled examples produced the same correctness on both cohorts as updating its memory after each wave. The direct label classifier gained one fresh answer from feedback, but lost one in the earlier cohort. This distinction matters for the goal of sustained improvement. [Questions, native readouts and time-ordered controls](routing/README.md)

## Where the generation time goes

On G51 and G52, **35 of 35 successful slices** stopped on the job clock, after too few row passes to visit even half the eligible rows. Giving those slices half as many rows leaves the same clock. On both generations the longest training job lost its runner. Even halving the measured time of all successful growth steps and resolving the lost-runner tail immediately leaves estimates of **261 minutes on G51 and 221 on G52**. Those are favorable retrospective estimates. A three-hour run also needs a faster preparation or gate phase. [Stage durations and assumptions](budget/README.md)

In a separate matched run of the released 8B CPU trainer, halving scheduled passes from eight to four reduced wall time from 603 to 491 seconds (19%). It also reduced the optimizer updates from two to one, and both reserved examples had worse prediction loss afterward than with the longer fit. Both runs included model setup, evaluation and adapter export. Shuffling the same 188 archived exam jobs among the same 16 runners yields a projected G52 gate of 52 minutes against the observed 66. A live generation remains necessary to measure schedule savings. [Matched training receipts](budget/README.md) · [Fixed-work gate replay](gate_schedule/README.md)

A rank-four CPU training slice survived a forced process death and produced bit-identical weights and optimizer state after restoring its sampler, random state and last complete update. It consumed 143 row passes against 223 for starting again. A corrupted latest snapshot fell back to the prior one. Hosted runner replacement also needs the snapshot to have left the failed machine and a replacement worker to retrieve it. [Crash, restore and negative control](recovery/README.md)

## What the next cycle sees

Run `python scripts/cycle.py --last 1` to see the fixed unseen-kind goal and `python scripts/cycle.py --closed-trials` for the six configurations retired after the Atlas experiments. A partial fixed sitting or a pulse alone is shown as insufficient to measure the full goal. The release keeps measuring actual successes and losses. [Recorded decisions](../../../docs/KNOWLEDGE.md)
