# Different seats and checked dissent

A third model family reduced teacher-key matches from **28 to 24 of 32** on recorded coding exercises and consumed ten more seat responses. Checking answers against a bounded exact reference saved five seats on that archive with the same 28 matches. On a separate 26-request language panel it recovered one additional correct answer. The verifier recognized only two requests on that panel.

## Real worker responses

Four previously measured small checkpoints wrote programs for the same 32 school exercises. We replayed their logged stdout and missing responses through the actual `team.solo.agreeing` and `_winner` functions. We fixed these seat orders for this experiment. Installed production teams can seat different members. No models were called in the replay. [Archive](../../../data/school/coder_answers.json) · [Original school evaluation](../../../reports/diverse_coders.json) · [Protocol](PROTOCOL.md)

| Selection | Teacher-key matches | Other deliveries | Abstained | Seats | WASI calls |
|---|---:|---:|---:|---:|---:|
| Current decision rule, tuned Qwen / stock sibling / fast Qwen | 28 | 2 | 2 | 74 | 0 |
| Forced diversity, tuned Qwen / Yi / fast Qwen | 24 | 1 | 7 | 84 | 0 |
| Same seats reordered, tuned / fast / stock | 27 | 3 | 2 | 76 | 0 |
| Current seats with verified dissent | 28 | 2 | 2 | 69 | 19 |

The tuned coder missed five keys and the stock sibling missed eleven. Four failures overlapped, against 1.72 expected if their errors were independent at these marginal success rates. The tuned coder and Yi also shared four failures, while Yi missed twenty keys. Across all six pairs the observed joint failures exceeded the independence calculation. This small benchmark mixes task difficulty, model quality and family membership. The result cautions against replacing a stronger seat purely for architectural variety. [All pair counts and saved decisions](results.json) · [Knight and Leveson on common failures in independently developed programs](https://doi.org/10.1109/TSE.1986.6312924)

The verifier bound 19 of 32 archive prompts. All 19 delivered a teacher-key match, and all 19 had already been answerable by ordinary agreement. The two false confirmations elsewhere in the archive persisted. One returned four items in a request for the first five even numbers. Another reported 8.0432 years to double at 9% continuously compounded interest, where the answer is about 7.7016 years. School keys themselves can be faulty. For the 10-year investment task the stored teacher ignored the monthly contribution of $200 and applied the annuity formula to $10,000. It stored $1,638,793.47, whereas end-of-month contributions and monthly compounding give about $50,969.84. All four policies abstained on that task.

## Sealed language panel

Another researcher froze four scripted seat replies for each of 26 new requests before seeing the decision implementation. Eighteen asked a closed question, five changed the meaning of an apparent arithmetic request and three were unsupported or underspecified. These cases test the decision rule under stipulated proposals. They do not measure how often a deployed model generates the right proposal. [Independent protocol](../confirmation/protocol.md) · [Sealed prompts](../confirmation/dissent.json) · [All four decision traces](../confirmation/dissent-results.json)

| Selection | Correct | Wrong | Missed | Unjustified |
|---|---:|---:|---:|---:|
| Current | 6 | 14 | 3 | 3 |
| Forced diversity | 4 | 16 | 3 | 3 |
| Same seats reordered | 6 | 14 | 3 | 3 |
| Verified dissent | 7 | 13 | 3 | 3 |

The new decision spent 62 seats against the current 63. It ran the WASI checker once and returned the witnessed sum 351 for primes from 61 through 79. The other bound request had no candidate to check. All 13 wrong deliveries and all three unjustified deliveries under the verified policy came from the unverified agreement fallback. Thus the predeclared relative hurdle was met by a single case. These results provide little evidence for using broad natural-language matching as an arbiter. A typed contract and a direct deterministic answer are viable where the exact operation is already known.

## Executable counterexamples for G47 programs

The second replay uses all eight actual G47 programs from three archived peer-correction chains. A public camera contract asks for the positive wait to the next 24-millisecond strobe. Savings asks for the positive distance to the next multiple of 17 cents. Transit asks for minimum 50-minute tickets with a half-open upper endpoint. Peers in this archive saw prior code and public failure feedback. [Original experiment and provenance](../../../reports/verified-learning/peer/)

Three admissible probes per contract challenged each candidate. The scalar oracle enumerates positive offsets until the next multiple. An independent dynamic program derives the minimum ticket count. The candidate code ran in the fieldwork WASI guest. Of the 24 candidate/probe combinations, 11 established a wrong return value and 13 failed to demonstrate an error. The checker also declined one proposed negative input for each contract. Re-executing all eight programs on 28 disjoint inputs per contract reproduced all 224 previously recorded outcomes. Selection used only the three public probes. The held-out values were already public archive material, and no new G47 model wrote code in this study.

| Selection on 84 jobs | Correct | Wrong | Withheld | Witness batches |
|---|---:|---:|---:|---:|
| Keep incumbent program | 35 | 49 | 0 | 0 |
| Use first peer program | 39 | 45 | 0 | 0 |
| Use first program surviving public probes | 28 | 0 | 56 | 8 |

The camera peer passed every held-out case, recovering four failures. Every savings and transit candidate failed a witnessed public case. Withholding their 56 jobs prevented 45 wrong first-peer outputs but also lost eleven correct transit outputs. This result covers three chosen contracts, and cannot establish that passing three probes proves an arbitrary program correct. It does establish which particular candidates failed their stated contracts, with executable inputs and original source digests. [Witness records and outcomes](results.json)

## Reproduce

Use Python with the repo's fieldwork dependencies and its CPython/WASI SDK (`python.wasm` and `lib/`). From the repository root run

```sh
python -m training.experiments.atlas.dissent.replay --sdk "$HIVE_FIELDWORK_SDK" --out /tmp/hive-dissent.json
python -m training.experiments.atlas.confirmation.dissent --sdk "$HIVE_FIELDWORK_SDK" --out /tmp/hive-dissent-confirmation.json
```

The archive replay asserts exact correspondence of original and replayed guest results. The output includes input, code, selector and SDK hashes, seat counts, guest instruction fuel and wall time. This run took approximately 19 seconds including WASM compilation. The 19 arithmetic checks consumed 21.80 billion units of WASI fuel, mostly from starting CPython. The eight program witness batches consumed 8.21 billion. Wall time depends on the machine. Seat counts are response accesses and do not provide token or inference-time savings measurements. [Source](replay.py) · [Raw results](results.json)
