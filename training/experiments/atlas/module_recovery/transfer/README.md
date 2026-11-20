# A saved G52 duration module completes a job G50 left unanswered

G50 spent 260 seconds and tried three workers on an elapsed-time request. No worker passed, its final report said “No member got as far as an answer”, and the user received no `durations.py`. Given the **same request after G52**, either retained module independently wrote the requested file, returned `69577` and `0s` on separate lines, and passed all 50 original G50 hidden draws in CPython WASI. The two-version arm checked both versions’ outputs, then returned a byte-identical copy of version A. A handwritten implementation achieved the same result. This is a backward replay of an earlier request with later artifacts. G50's original score stays unchanged. [Original report, worker verdicts and artifact hashes](g50-original.json) · [Recalled module](g50-recalled/durations.py) · [Delivered report](g50-recalled/REPORT.md)

| Recall option | New exact requests completed | Neighboring requests deferred | Earlier G50 job |
|---|---:|---:|---|
| Empty bank | 0/8 | 6/6 | Deferred |
| G52 version A | 8/8 | 6/6 | Correct file and report |
| G52 version B | 8/8 | 6/6 | Correct file and report |
| Require the two versions to agree on the request | 8/8 | 6/6 | Correct file and report |
| Handwritten integer solver | 8/8 | 6/6 | Correct file and report |

Each positive required a working module and two exact outputs. All 16 new function/input pairs were disjoint from admission, the earlier 60-case independent panel and all three archived G50/G52 duration exams. The requests used the exact published template with new arguments. The six remaining requests changed the filename, behavior, units or extra work, or used wording outside the registered contract. One of those six was a legitimate paraphrase that a general assistant ought to handle. The narrow recall rule deferred on it. The new panel was prospectively authored by the author of this diagnostic. No new ordinary worker was run on these fourteen prompts. [Frozen requests](requests.json) · [Scoring key](keys.json) · [Prospective protocol](protocol.md) · [Scores, outputs, digests and WASI fuel](results.json)

Version A originated on `h20000523_03`, and B on `h20000527_03`. The loader checks both retained source hashes against their prior admission records. It matches the whole request, executes the retained source in WASI, and writes the source bytes and returned values. In this experiment the two-version path compared the returned values on the user's inputs. The earlier G52 recovery had already tested the files independently. Neither the extra version nor the handwritten comparator improved answers on this panel. No model generation or retraining was needed. One CPU core was used for this run.

To reproduce with the repository Python environment and its WASI SDK, choose a new output directory. The run writes every delivered file and report, saves its ungraded deliveries, then opens the grading keys.

```sh
python training/experiments/atlas/module_recovery/transfer/compare.py \
  --sdk /path/to/python-wasi-sdk --out /tmp/hive-duration-transfer
```

The source ZIP for optional receipt regeneration is GitHub Actions artifact `14527107867`. Its digest is pinned in the [archive manifest](../../pulse/artifacts.json).
