# Short practical answers on the CPU hive

All three versions gave the same seven correctly formatted answers across 16 real CPU requests. They solved three of twelve practical questions and retained all four elementary controls. The four qualified weight edits were available to the integrated version. The native server activated none on these requests. [All 48 replies, native calls and worker programs](results.json)

| Measured outcome | Original hive | Signals only | Signals + four qualified weights |
| --- | ---: | ---: | ---: |
| Practical answers in the requested format | 3/12 | 3/12 | 3/12 |
| Practical answers including confirmed numeric prose | 5/12 | 4/12 | 3/12 |
| Elementary retention | 4/4 | 4/4 | 4/4 |
| Requests exceeding 150 seconds | 3/16 | 4/16 | 5/16 |
| Completed native inference calls observed | 58 | 46 | 45 |
| Total recorded time | 1,127 s | 1,306 s | 1,348 s |

The three practical successes were two conversation choices and a machine-learning evaluation question. Each version missed both coding, math, physical science and computer-engineering questions on the strict measure. Every arm started eight program-work jobs. The original hive delivered the correct numbers 42 and 60 in prose after workers checked calculations for venue capacity and classifier recall. With signals only, the venue job hit its deadline. In the integrated run both jobs timed out. Two integrated workers computed 60 for recall, and the caller still received no answer. Concurrent CPU load varied across runs. These measurements support conclusions about delivered answers under a time limit and leave the causes of timing differences unresolved. [Per-domain and per-case results](results.json)

A subsequent native-engine check found that the pinned CPU server could reuse a computation graph after switching adapter scales. The native scales in these 48 traces show what the server reported. Effective switching between generation-47 worker weights on every call remains unverified in this first study. No domain weight was requested. The frozen rows remain available for comparison with the final server setting.

All three versions confirmed a wrong answer on a four-byte load starting at address 62 with 64-byte cache lines. Both workers generated `print(1)`. Bytes 62–63 occupy one line and 64–65 occupy the next. A separately developed arithmetic handler subsequently returned `2` from the ordinary `./hive --once` command on the original wording. It also answered five of six independent new eligible requests, declined all three underdetermined or unrelated requests, and matched an enumeration oracle on 2,048 fixed-grammar inputs. The missed new request described a 40-byte read in prose. This repair came after the model study and has its own measurements. [Fresh questions, sweep and actual CLI results](../cache-lines/results.json)

## Final production repeat

On the twelve previously scored practical questions, the integrated system with the checked cache calculator, integer formatter, five qualifying weights and corrected native graph handling answered five in the requested format. All three earlier arms answered three. Both new successes came from previously diagnosed cases. The cache access returned `2` with zero native calls. For classifier recall, the two workers printed `60.0` and `60`. The agreed work report began with `60.0` and the final reply delivered `60`. The venue-capacity job still timed out. On the other nine practical questions, the original and final systems both answered the same three correctly. [Frozen repeat protocol](final-protocol.md) · [All 16 final replies, programs and paired comparisons](final-results.json)

The final version retained all four elementary answers. It produced 45 completed native calls across 16 requests, took 1,241 seconds in total, and hit four deadlines. With the supplemental content criterion, both the original and final systems scored 5/12. The original delivered the venue result in prose and missed the cache question. The final version gained the cache result and missed the venue deadline. Its native launch included the five qualified files and disabled graph reuse. No domain weight activated on these broad tasks. The final serving signal correctly labeled seven of the nine questions for which it emitted a label. The cache calculator answered before subject classification. [Live server configuration](environment.json) · [Raw final results](final-results.json)

The independently authored panel asks two questions each about coding, math, physical science, conversation, machine learning and computer engineering. Four elementary questions in the original domains test retention. Each question starts an empty conversation. Neither the model nor the router sees the expected answer. [Frozen questions](panel.json) · [Separate answer key](keys.json) · [Preregistered protocol](protocol.md)

## What the test measures

The primary score requires the requested integer or letter as the first answer. Work must reach agreement to count as a correct delivery. The secondary score also accepts prose whose only numeric quantity is the correct whole-valued result. This secondary measure was added after seeing a baseline response express a confirmed integer in prose as a decimal, before scoring the new system. Each grading rule is applied to every arm. Raw replies allow readers to check answers that the automatic grader could not interpret.

The integrated bank included qualified coding, math, conversation and machine-learning heads. Its first physical-science and computer-engineering candidates fell short of the admission criterion. The scope study separately probes the decisions these heads were trained for. [Frozen v1 index](index-v1.jsonl) · [Paired qualification](../../domain-engrams/results.json)

The baseline runs the pre-change checkout at `87247068` with signals and engrams off. The integrated arm runs the normal chat/work path, including the two-sender domain signal and any compatible learned memory loaded by the native server. The signal-only arm uses the new serving signals with all engrams disabled. Every arm retains the common pre-study integer formatter. The results record the final classification, inference requests, actual native adapter scales and checked worker programs separately. Merely enabling memory does not count as an activation. [Runtime parameters and model digests](environment.json) · [Grader](grade.py)

All three arms use the same CPU Ternary Bonsai 8B base and five available generation 47 member edits. Each model request has two CPU threads. A work order has two seats and the ordinary third seat for disagreement, at most two turns per member, and 120 generated tokens per work turn. The conversational limit is 80 tokens. Each question has a 150-second wall-clock limit, including normal routing and checks. Fixed per-call seeds are shared across arms. Timeout and unconfirmed work count as failures. These limits make the experiment practical and can affect which requests finish.

## Reproduce

Rescore every recorded user-facing reply against the separate frozen keys with standard Python.

```sh
python training/reports/domain-memory/answers/rescore.py
```

Use the project's Python environment, the pinned CPU runtime and base model, and the five members listed in `environment.json`. Set `HF_HOME`, `HIVE_TERNARY_BIN`, `HIVE_ADAPTERS_HOME` and `HIVE_MEMBERS` to the installation that supplies those files. The preparation script rebuilds the measured source snapshots from immutable Git commits and verifies the SHA-256 digest of every changed runtime file. Use an unused localhost port dedicated to this benchmark. The bank preparation command copies the four original qualified weights and checks their digests. It uses the frozen index even if other weights subsequently qualify. The script invokes the real `team.talk.reply`, runs generated work through the ordinary workers and writes each user-visible reply in its own directory.

```sh
python training/reports/domain-memory/answers/prepare.py baseline /tmp/hive-practical-old
python training/reports/domain-memory/answers/prepare.py signal_only /tmp/hive-practical-signals
python training/reports/domain-memory/answers/prepare.py integrated /tmp/hive-practical-integrated
python training/reports/domain-memory/answers/run.py --arm baseline --checkout /tmp/hive-practical-old --out /tmp/hive-practical
python training/reports/domain-memory/answers/run.py --arm signal_only --checkout /tmp/hive-practical-signals --out /tmp/hive-practical
python training/reports/domain-memory/answers/prepare.py bank_v1 /tmp/hive-practical-bank-v1
HIVE_ENGRAMS_HOME=/tmp/hive-practical-bank-v1 python training/reports/domain-memory/answers/run.py --arm integrated --checkout /tmp/hive-practical-integrated --out /tmp/hive-practical
python training/reports/domain-memory/answers/grade.py /tmp/hive-practical baseline integrated signal_only --out /tmp/hive-practical-results.json
```

The diagnostic below runs the two learned senders and the final serving consensus on all 16 questions without generating answers. The frozen senders labeled 11 correctly, mislabeled three and abstained twice. The consensus labeled seven correctly, mislabeled two and abstained seven times. [Per-question routing decisions](routing.json)

```sh
python training/reports/domain-memory/answers/run.py --routes-only --checkout /tmp/hive-practical-signals --out /tmp/hive-route-check
```

The final production repeat uses the five-entry catalog and disables compute-graph reuse in the native server. Run it in a fresh native-runtime home so that startup records the expected new command and files. [Frozen repeat protocol](final-protocol.md) · [Final catalog](index-final.jsonl)

```sh
python training/reports/domain-memory/answers/prepare.py final_system /tmp/hive-practical-final
python training/reports/domain-memory/answers/prepare.py bank_final /tmp/hive-practical-final-bank --weights /tmp/hive-practical-final/cells/engrams
HIVE_TERNARY_HOME=/tmp/hive-practical-final-native HIVE_ENGRAMS_HOME=/tmp/hive-practical-final-bank python training/reports/domain-memory/answers/run.py --arm final_system --checkout /tmp/hive-practical-final --out /tmp/hive-practical
python training/reports/domain-memory/answers/final_replay.py /tmp/hive-practical --out /tmp/hive-practical-final-results.json
python training/reports/domain-memory/answers/rescore.py /tmp/hive-practical-final-results.json
```

The no-inference comparison exercised both talk and work eligibility for all 16 questions. The initial and final banks selected no weight on any of those 32 branches. A separate, explicit Python operation question selected the coding weight with both versions and recorded their respective eight-token and one-token consultation budgets. Subsequent release guards for named local conventions and standalone pure-water phase questions also left these 16 surfaces unchanged. The cache question remained the sole early checked answer. The final water-output guard at commit `ffc0afb` also left every recorded output unchanged. Its no-generation replay checked 48 nonempty visible replies and 45 nonempty worker outputs across the 64 requests. Questions with deadlines retain their failed-delivery score. The native final repeat used `19992ca`; the later guard comparison applied the actual release functions to the same questions and stored outputs. [Per-request eligibility, control and guard receipts](scope-followup.json) · [Recorded-output replayer](output_delta.py)

The runner resumes completed questions. Use a fresh output location for an independent repetition. Server initialization, competing CPU load and sampling can affect timing and whether a work order reaches its limit. [Runner](run.py)
