# Two worker programs that the hive failed to deliver

On two generation 52 pulse jobs a member had written correct duration functions, but the hive reported that it could not deliver a file. This experiment copied the function bodies from the original programs and verified them using integer arithmetic in a WebAssembly guest. Both files passed all **50 original hidden checks apiece** and all **60 additional independently authored inputs apiece**. The requested answers also matched. Running this recovery rule over all three after-arm archives changes the G52 replay from **52/64 to 54/64**. G50 stays **54/64** and G51 stays **50/64**. Both G52 examples were known failures in the same taught family. No worker was regenerated. [Frozen experiment](protocol.md) · [Results and program digests](results.json)

| Original job | Values delivered | Recovered source |
| --- | --- | --- |
| h20000523_03 | 36,228 seconds and `1h` | [durations.py](g52/h20000523_03/durations.py) |
| h20000527_03 | 72,268 seconds and `1m` | [durations.py](g52/h20000527_03/durations.py) |

The replay receives the request, the visible decline and the workers' programs. It extracts complete definitions for the two requested functions. It omits the worker's surrounding test driver and retains supported imports. A human wrote the narrow contract and qualification examples. After a program qualifies, the same guest runs the user's two inputs and publishes the candidate source and its actual outputs. The original grades score the comparison only after selection. A G50 duration request received a wrong delivery that the original system had accepted. This particular recovery only inspects explicit declines, so it left that answer alone.

The first qualification used 38 small and medium duration checks. An independent author supplied sixty disjoint checks and three faulty programs. One program rounded through binary floating point: it passed qualification and then failed four large integer cases. A revised qualification probes both sides of integer word-size boundaries from 8 to 128 bits. It rejected all three known faulty programs and qualified the same two real worker modules. The original negative controls were known when that change was made. Finite tests provide bounded evidence. [First qualification and false admission](first-results.json) · [Independent panel and controls](holdout.py) · [Revised qualification](recover.py)

## Reproduce

From the combined experiment checkout, use the repository environment with `wasmtime` and the project's Python WASI SDK. The command replays the compact extracted inputs, writes real modules into a new directory, and re-creates each task's official checker seed in a separate grading step.

```sh
python training/experiments/atlas/module_recovery/replay.py \
  --sdk /path/to/python-wasi-sdk --out /tmp/hive-atlas-durations
```

The compact archive records all 192 fresh pulse IDs and earlier grades. It includes the original request and candidate programs only when the full contract matches. To rebuild it from the original action artifacts, pass `--collect` with the ZIP directory named by artifact ID. The importer verifies each archive's digest first. [Compact archive](archive.json) · [GitHub run and artifact manifest](../pulse/artifacts.json)
