# A live cell corrected a camera-timing method

An inspection camera strobes every 24 milliseconds. A user asked how long until the *next* strobe. At time 24, the first coding cell answered zero. The correct answer is 24. A second cell saw the first program and that one public counterexample. Its 31-token replacement passed all 16 independent checks and all 28 fresh jobs. It used integer division, so its wait time also remained correct for inputs well beyond the exact range of a double.

Two new scalar tasks and their checks were frozen before generation. They share a strict-boundary calculation across two applications, chosen to give a learned rule a chance to transfer. A third remedial exercise used a previously published transit-ticket failure. Each cell saw the task description. The first writer also saw four public examples. The peer saw its predecessor's source and one failed public example. Public checks determined retries. Every source was subsequently scored on 16 separate qualification cases and 28 additional cases in the project's CPython WASI guest.

| Work request | Writer public, qualification, fresh | First peer public, qualification, fresh | Final peer public, qualification, fresh |
|---|---|---|---|
| Time to next camera strobe | 2/4, 12/16, 24/28 | **4/4, 16/16, 28/28** | Stopped on public pass |
| Cents until next savings goal | 1/4, 0/16, 0/28 | 2/4, 0/16, 0/28 | 2/4, 0/16, 0/28 |
| Tickets required for the next 50-minute boundary, remedial | 3/4, 7/16, 11/28 | 3/4, 7/16, 11/28 | 3/4, 7/16, 11/28 |

The first writer used G47 code2, the first peer used G47 data2, and the final peer used G47 sources2. Each is a distinct adapter on the same Ternary-Bonsai 8B base. The seven primary live generations produced 321 tokens in a 305-second run using two inference threads, greedy decoding, seed 70479, and a ceiling of 240 output tokens per turn. The original transit submission came from the earlier run.

Fieldwork replayed the unedited live source sequence with deterministic repair disabled. It admitted the camera method into an empty bank. A separate CLI process with inference unavailable used that bank to return **1 millisecond at time 1031**, with the method digest in its receipt. Savings and transit were withheld. One of the two prospective tasks thus gained a callable method. The camera change involves a floating-point library call outside the learned expression grammar. The two-donor condition for learning a transfer rule was unmet, so the predeclared third task was left unused.

Two supplementary checks followed observation of the initial public outcome. With the identical counterexample and correction request, the original code2 adapter wrote the same corrected camera source as data2, byte for byte. Feedback was sufficient for the repair in both cells. Switching adapters gave no measured advantage on this case. On 12 additional inputs around integer boundaries at 53, 65, 257, and 1025 bits, the original camera program passed 2/12 and the corrected one passed 12/12.

## Reproduce locally

The evidence bundle contains the protocols and corpus, original public prompts, counterexamples, raw responses and source, generated-token counts, per-input WASI results, adapter and runtime hashes, bank receipts and experiment scripts. The included bank contains the admitted camera source. With the repository's Python environment and configured CPython WASI SDK, run these from this report directory.

```bash
python verify.py --checkout /path/to/HiveMIND --sdk /path/to/wasi
HIVE_BANK="$PWD/bank" HIVE_FIELDWORK_SDK=/path/to/wasi /path/to/HiveMIND/hive --local --once 'Run camera_pulse with 1031'
```

The verifier checks all 384 primary scores, 48 self-retry scores and 60 supplementary large-integer scores against the archived outputs.
