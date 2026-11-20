# Replaying public examples against real worker files

The stock file relay accepted **0 of 90 archived module requests** from the G50–G52 before/after gates. For the two known G52 jobs its final-instruction pattern misses the comma in “Then tell me, each on its own line, the value of …”. Both had an acceptable module in the third worker's directory. No file or text left the stock relay on either. The two G52 requests are previously investigated examples of the same taught task. [Stock relay](../../file_relay/relay.py) · [Archive and run receipts](stock.json)

The denominator includes every request beginning “Write a Python module” in the 48 available gate archives. These are **90 attempts on 33 distinct prompt texts** across 10 module families, with 45 prior answers, 37 explicit declines and eight missing reports. Several attempts share an identical prompt, including before/after pairs. Eight absent reports were kept out of delivery decisions. The archive's all-source pass looked at every worker turn in stable order. All file filtering, code selection and sample execution used the same stored submissions and the same CPython/WASI guest. [Fixed evaluation protocol](protocol.md) · [Runner](replay.py)

## What the previously withheld worker code actually did

We transcribed the public examples and requested literal calls from each original duration prompt. We executed every distinct extractable module and a synthetic program that memorized only the five public examples. The prompt's two final queries supplied inputs alone. The measured outputs below came from running the files. This diagnostic had no access to historical stdout as a key and could neither qualify a missing program nor select which novel output was correct. [Statements, source hashes, individual outputs and historical events](stock.json)

| Original job | Prior report | Real modules passing all five public examples | First passing module returned | Lookup-only returned |
| --- | --- | ---: | --- | --- |
| G50 before, h20000502_00 | No answer | 1/2 | 69577 and `0s` | 0 and `0s` |
| G50 after, same request | No answer | 0/4 | No passing candidate | 0 and `0s` |
| G52 after, h20000523_03 | Unconfirmed | 1/1 | 36228 and `1h` | 0 and `1h` |
| G52 after, h20000527_03 | Unconfirmed | 1/1 | 72268 and `1m` | 0 and the empty string |
| G52 before, h20000523_03 | Answered | 2/2 | 36228 and `1h` | 0 and `1h` |
| G52 before, h20000527_03 | Answered | 3/3 | 72268 and `1m` | 0 and the empty string |

The lookup programs also passed every public example in every row. On a request the existing relay *does* accept, from its own development controls, the genuine worker's subtraction function returned 22. The lookup-only function returned 0 on the new input and the unchanged relay offered it for delivery. Supplying both files caused it to abstain. Reliably executing a candidate can establish its observable answer to the requested call. Public examples alone cannot tell whether a singleton implements the intended function. [Unmodified relay control decisions](stock.json) · [Origin of the subtraction prompt](../../file_relay/check.py)

The original parser ran zero guest calls for all 90 archived prompts. The observation runs and subtraction controls together used 23 WASI invocations, 145 total input rows, 23,557,587,359 fuel units, 6.07 seconds inside guest calls and 16.92 seconds total elapsed (16.63 process CPU seconds). These are one run with a single CPU and zero neural calls. They do not measure a training generation. [Metering receipts](stock.json)

## Independent parser on the archived requests

A second developer froze a general parser without viewing the archived prompts or programs for this study. It normalizes literal statements and final query calls, round-trips them through the original relay’s parser, then calls the original WASI proposer. Neither implementation received the grader or grader outputs. The new parser covered **10/90 attempts**, spanning duration conversion, Roman numerals and integer factorization. Four had an existing positive report, which it preserved. Of the remaining six declined attempts, it returned five candidate files with answers. Both parser results were written and hashed before scoring. An initial attempt to plug the parser into the runner recursively invoked it during its own stock round-trip. The corrected evaluator calls the independently frozen proposal function directly. The stock run and both frozen parsers were unchanged. [Independent source](../literal_intake/intake.py) · [Decision receipts](alternative.json)

The later grader regenerated each actual prompt exactly, used the official generator's two sets of 25 private function calls, and checked the requested output text separately. Every genuine proposed file passed all 50 checks and returned the requested lines in order. [Complete grading receipts](grades.json) · [Scoring code](score.py)

| Declined archive attempt | Real file and exact returned lines | Private file tests | Lookup alone passed private tests |
| --- | --- | ---: | ---: |
| G50 after, duration conversion | Withheld | — | 14/50 |
| G50 before, same duration prompt | `durations.py`, 69577 and `0s` | 50/50 | 14/50 |
| G50 after, Roman numerals | `roman.py`, `CMLIV` and 3997 | 50/50 | 0/50 |
| G50 before, same Roman prompt | `roman.py`, `CMLIV` and 3997 | 50/50 | 0/50 |
| G52 after, first known duration prompt | `durations.py`, 36228 and `1h` | 50/50 | 10/50 |
| G52 after, second known duration prompt | `durations.py`, 72268 and `1m` | 50/50 | 11/50 |

Retaining the other archived deliveries would move **26/90 to 31/90** on this module-only subset. The after-body share moved from 12/45 to 15/45 and the before-body share from 14/45 to 16/45. The five gains cover four distinct prompts, including the two previously examined G52 jobs. Counting each exact prompt once if *any* historical body passed it, coverage moved from **16/33 to 18/33**. Only the older G50 duration and Roman prompts were newly covered. Both G52 prompts had already passed in their before bodies. The additional Roman results reuse one prompt across the two bodies. All gains were on the taught two-function module task kind. The factorization attempts already had visible answers.

The parser also proposed **all six lookup-only files**, each failing both the official functional grade and the exact answer-text check. Supplying each lookup alongside all original worker programs led to five abstentions. Where no real worker passed the public examples, the lookup remained the only qualifying program, so the proposer still returned a wrong file. The broader parser found real work worth recovering, but its new proposal can be shown to a user only with a truthful description of its checks. A public-example pass alone cannot certify a novel output.

The alternative's six real candidate evaluations used ten guest invocations on 64 input rows, 10,250,597,545 fuel units and 2.42 seconds inside guest calls. Including all adversarial and development controls, the second phase took 32 invocations, 200 input rows, 32,782,210,774 fuel units, 7.68 guest seconds and 17.65 seconds elapsed (17.54 process CPU seconds). Post-decision grading took 12 invocations, 600 inputs, 12,333,008,970 fuel units, 3.18 guest seconds and 13.34 seconds elapsed (13.04 process CPU seconds). Each phase used one CPU and made zero model calls.

## Separate check for dropping statements from the question

An independently frozen, stricter parser checks that every written occurrence of a literal call survives normalization. On the same 90 archived attempts it rejected four of the ten supported cases (three with declines, one with an existing answer), retained six exact specifications (three declines, three already answered), and admitted no new specification. The retained specifications had identical file, symbols, ordered public expectations and query calls, so they could reuse the original program execution and private grades. Three of the five earlier gains survive: G50 Roman numerals in both bodies and the second G52 duration prompt in the after body. The stricter parser gives **29/90** passing archive attempts and **17/33** distinct prompt texts with at least one historical success. Only the G50 Roman prompt was newly covered. This comparison made no model or WASI calls. [Exact-specification comparison](guard.json) · [Source](equivalence.py) · [Frozen stricter parser](../literal_intake/lossless.py)

The final control checks that the number of occurrences of each literal call in the original request equals the number represented by examples and final queries. It allows repetitions that are fully accounted for. Across the same 90 archived attempts it retained all ten of the first parser's specifications exactly, including six declined and four answered attempts. All five real recoveries and all six false lookup-only offers therefore carry over. [Multiplicity-only comparison](multiplicity.json) · [Frozen occurrence check](../literal_intake/multiplicity.py)

| Grade across the same archive | Existing deliveries | Initial parser | Reject every repetition | Preserve accounted repetitions |
| --- | ---: | ---: | ---: | ---: |
| Passing attempts, including repeated bodies | 26/90 | 31/90 | 29/90 | 31/90 |
| Unique prompts passing in any archived body | 16/33 | 18/33 | 17/33 | 18/33 |
| Unique prompts passing in before bodies | 14/33 | 16/33 | 15/33 | 16/33 |
| Unique prompts passing in after bodies | 12/33 | 15/33 | 14/33 | 15/33 |

## Reproduce the keyless pass

```sh
python -m training.experiments.verified_growth.delivery_audit.public_examples.replay \
  --sdk /path/to/python-wasi-sdk --archives /path/to/gate-zips --out /tmp/public-examples.json
```

To replay the independent proposer, add `--alternative training.experiments.verified_growth.delivery_audit.literal_intake.intake --parser-sha 11aa54578a7af9fed43dbd0014f9791b04770c96fd4904b78d36ff5d6e70ba2c` and a different output path. For the historical checkout and recorded decisions, the separate scorer verifies both sealed decision digests before importing the official private grader.

```sh
python -m training.experiments.verified_growth.delivery_audit.public_examples.score \
  --sdk /path/to/python-wasi-sdk --archives /path/to/gate-zips --out /tmp/public-example-grades.json
```

[Archive manifest with SHA-256 checksums](../../../atlas/pulse/artifacts.json)
