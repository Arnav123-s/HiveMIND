# Merging six specialist heads and tuning one scalar

Simple addition produced **24/30** correct answers from a single head. The pooled starting head scored **22/30**. Truncating the addition to rank 4, 12, or 16 produced the same score. On this narrow task, increasing the rank alone did not fix any answers. Scores use real native T80 endpoint states and compare against all possible output tokens. Only six domains and thirty previously published test prompts enter this study. [Protocol and split](protocol.md) · [Case-level scores and scalar traces](results.json)

| Merge on the same 42 training rows | Correct of 30 |
| --- | ---: |
| Pooled starting head | 22 |
| Correct specialist supplied by domain | 23 |
| Mean of the six residual edits, rank 16 | 22 |
| Sum, rank 4 / 12 / 16 | 24 / 24 / 24 |
| TIES with sign election and 20% magnitude trim | 23 |
| DARE thinning then mean, three seeds | 22 / 22 / 22 |
| Two singular directions per task, then orthogonalization | 22 |

Sign disagreement affected 62,432 of 65,536 coordinates materially changed by at least two specialists. It did not imply that removing or orthogonalizing those directions would improve the delivered token. Six edits were learned from a common pooled starting head and merged as differences from it. The controlled DARE comparison is the arithmetic mean. The rank-12 arithmetic comparator has the same upper bound on retained residual directions as the orthogonalized alternative; the common starting edit can contribute additional rank.

An eleven-evaluation central-difference method tuned only the scalar multiplying a merged edit. It finished near 0.87 for the arithmetic sum and 0.91 for TIES. Both gave 23/30, versus 24 and 23 at the original scale. With the same eleven development evaluations, a grid chose zero and obtained 22/30 on both. The scale checks each took about 0.06 seconds of CPU using cached states. These timings exclude extracting the states and running the language model. [Executable comparison](compare.py)

```sh
OPENBLAS_NUM_THREADS=1 python training/experiments/atlas/merging/compare.py --out /tmp/hive-merge-results.json
```
