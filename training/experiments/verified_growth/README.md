# Getting from correct worker answers to unseen kinds

HiveMIND's release target is five of ten unseen kinds. Each kind has three fixed questions, and two correct answers earn a pass. G52 delivered one correct question out of thirty and passed zero kinds. Even choosing the right recorded worker with hindsight would have passed just one kind on G52. Pooling every recorded worker from six sittings of G50–G52 would have passed four kinds. Reaching the fifth requires generating at least one new correct answer as well as selecting it. The six sittings reuse the same questions. [Official grades, worker ceiling and records](release/README.md)

The two incorrect G52 pulse deliveries were a CSV with the wrong header and row count, and a cache implementation that failed 44 of 423 checks. Both lacked a passing worker. The wrong even-number and interest answers belonged to a separate 32-job evaluation. [Pulse archive and original task sources](release/README.md)

## Can the hive put a program together?

The earlier program builder received its plan along with each job. This test instead gave each selector an independently written English work order and a CSV. The returned answer had to be correct on two different versions of the input. The handwritten planner solved **13/18** requests, the fitted operator selector and whole-plan classifier each solved **11/18**, and the native 8B planner solved **4/18**. A single operation solved none. Providing **one independently labeled worked example** raised the portfolio to **15/18** and three complete patterns out of six. The library limited to seven previously taught operator pairs also reached 15. The three unresolved requests were withheld. [Transfer study, raw model replies and independent SQL grades](transfer/README.md) · [Runnable file publisher](composer/README.md)

A typed sum can still compute the wrong thing. One version summed occupied days when the user asked for rent and had supplied no prices. On the official exam, the file extractor and table entrants all fell back to the incumbent. A generic inline-table bridge also accepted zero of the thirty official messages. [Grounding failure](inline/README.md) · [File-recovery controls](file_relay/README.md) · [Official fallback results](release/README.md)

## Where the generation time goes

On G51 and G52, **35 of 35 successful slices** stopped on the job clock, after too few row passes to visit even half the eligible rows. Giving those slices half as many rows leaves the same clock. On both generations the longest training job lost its runner. Even halving the measured time of all successful growth steps and resolving the lost-runner tail immediately leaves estimates of **261 minutes on G51 and 221 on G52**. Those are favorable retrospective estimates. A three-hour run also needs a faster preparation or gate phase. [Stage durations and assumptions](budget/README.md)

A rank-four CPU training slice survived a forced process death and produced bit-identical weights and optimizer state after restoring its sampler, random state and last complete update. It consumed 143 row passes against 223 for starting again. A corrupted latest snapshot fell back to the prior one. Hosted runner replacement also needs the snapshot to have left the failed machine and a replacement worker to retrieve it. [Crash, restore and negative control](recovery/README.md)

## What the next cycle sees

Run `python scripts/cycle.py --last 1` to see the fixed unseen-kind goal and `python scripts/cycle.py --closed-trials` for the six configurations retired after the Atlas experiments. A partial fixed sitting or a pulse alone is shown as insufficient to measure the full goal. The release keeps measuring actual successes and losses. [Recorded decisions](../../../docs/KNOWLEDGE.md)
