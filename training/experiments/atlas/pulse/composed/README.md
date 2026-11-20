# A verified first answer and a recovered file on the same 64 jobs

On G52, combining the two frozen rules changed the official archive replay from **52 correct, two wrong and ten withheld in 142 worker calls** to **54 correct, two wrong and eight withheld in 133 calls**, plus two WebAssembly verification batches. Nine jobs saved a second worker. Two different jobs recovered a file written by a third worker. All eleven changed trajectories were disjoint. No previously correct delivery regressed. [Decisions, grades and costs](results.json) · [Original archive identities and SHA-256 values](../artifacts.json)

| G52 method | Correct | Wrong | Withheld | Worker calls | Extra admission batches |
| --- | ---: | ---: | ---: | ---: | ---: |
| Actual after-body | 52 | 2 | 10 | 142 | 0 |
| Verify first worker | 52 | 2 | 10 | 133 | 0 |
| Recover duration module | 54 | 2 | 8 | 142 | 2 |
| Verify first worker and recover module | 54 | 2 | 8 | 133 | 2 |
| Return calculator answer directly | 52 | 2 | 10 | 124 | 0 |
| Direct calculator and file recovery | 54 | 2 | 8 | 124 | 2 |

The simpler direct calculator achieves the same G52 outcomes with **18 fewer calls** than the original, compared with nine fewer for verifying a worker's complete answer. The human-authored calculator already derives the whole value. Requiring a worker buys its observed response and provenance. None of these methods fixed either remaining wrong G52 delivery. All three generations and both G52 duration failures were already known. This is a retrospective composition check. [Original G49 certificate](../one_checked/certificate.py) · [Archive recovery study](../../module_recovery/README.md)

## Three generations and file delivery

Each cell below gives correct / wrong / withheld followed by total worker calls. Each row contains a complete 64-job after-body pulse, including basic and hard questions, source lookups, named artifacts and unanswered tasks.

| Cohort | Actual baseline | Verify first | Recover module | Both | Direct calculator | Direct + recovery |
| --- | --- | --- | --- | --- | --- | --- |
| G50 | 54/2/8 · 144 | 54/2/8 · 138 | 54/2/8 · 144 | 54/2/8 · 138 | 54/2/8 · 130 | 54/2/8 · 130 |
| G51 | 50/6/8 · 142 | 50/6/8 · 133 | 50/6/8 · 142 | 50/6/8 · 133 | 50/6/8 · 124 | 50/6/8 · 124 |
| G52 | 52/2/10 · 142 | 52/2/10 · 133 | 54/2/8 · 142 | 54/2/8 · 133 | 52/2/10 · 124 | 54/2/8 · 124 |

The combined rule saved 24 of 428 completed worker calls across 192 jobs, raised correct deliveries from 156 to 158, retained all ten wrong deliveries and reduced withholding from 26 to 24. Its only additional serving execution was one guest batch per recovered module. The two admission runs consumed 2,059,683,495 WASI fuel units and 0.5373 seconds of recorded guest execution in total. These timings exclude SDK compilation. No paired end-to-end latency was measured. One G51 job timed out after recording two completed workers; both calls are included. The cost unit is one completed worker, which may take multiple turns, and every observed worker agent has a matching answer event and member verdict. [Archived measurements](../../module_recovery/results.json) · [Checkpoint with all 192 trajectories](checkpoint.json.gz)

| File-bearing jobs | Jobs | Original correct / wrong / withheld | Combined correct / wrong / withheld |
| --- | ---: | --- | --- |
| G50 | 22 | 15 / 0 / 7 | 15 / 0 / 7 |
| G51 | 20 | 12 / 1 / 7 | 12 / 1 / 7 |
| G52 | 24 | 13 / 2 / 9 | 15 / 2 / 7 |

File-bearing jobs include explicitly requested filenames and the exam's unnamed book-price CSV. The grades cover each complete task, including any requested printed values. The two additional files came from authentic member-three submissions. Their retained function bodies match the original source digests. Both shipped files were independently re-executed for this composition audit on the existing 50 official draws and 60 externally authored cases per file, with all 220 outputs and both pairs of visible answers correct. The earlier study documents overlap between some official draws and admission. Its 60 external cases were disjoint from admission, and are reused here. Grading consumed two extra guest batches, accounted separately from serving. [File audit](file-audit.json) · [First delivered file](../../module_recovery/g52/h20000523_03/durations.py) · [Second delivered file](../../module_recovery/g52/h20000527_03/durations.py)

## Reproduce

The scorer uses the historical G49 rule at SHA-256 `b9a526cef25260b2b567122f4f861138c1ce45f780cf06ca84390f511ee03157`. First-seat eligibility receives only the literal request and full observed first answer. After selection the official task generator independently checks the chosen answer and the direct-calculator answer. For unchanged items, the official archive's complete-task verdict is carried forward. A decline, empty report or timeout counts as withheld. Delivery with a failing official grade counts as wrong. Recovery checks the original decline, exact request and actual candidate program, preserves all previous worker charges, and uses the earlier WASI admissions. The composition input contains all 24 after-body ZIP selections from G50, G51 and G52. [Scorer](score.py) · [WASI file regrader](audit_files.py)

Use the project's Python environment from the repository root. The default score needs no network, live model or WASI SDK. The second command rebuilds the compact checkpoint and verifies the 24 ZIP digests. ZIP filenames are their numeric artifact IDs. The final command independently runs the two published files within WASI.

```sh
P=training/experiments/atlas/pulse/composed
python "$P/score.py" --output /tmp/composed.json
python "$P/score.py" --rebuild /path/to/original-zips --output /tmp/composed-rebuilt.json
python "$P/audit_files.py" --sdk /path/to/python-wasi-sdk --output /tmp/composed-file-audit.json
```
