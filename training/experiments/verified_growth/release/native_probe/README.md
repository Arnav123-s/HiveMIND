# One fresh native candidate from each of ten held-out task families

This trial asks the stock ternary 8B model to respond directly to tasks beyond a table API. Each question was generated from a new seed. Only an exact prompt-hash collision could exclude a draw before generation. Seven duplicate draws were skipped, and all ten families yielded distinct messages. The model saw one generic file-format instruction plus each full original request. It received no worked example, earlier response, tool, training update, checker, family identity or grading key.

The two grades compare identical raw model outputs. The first treats each as an ordinary report. The second also writes any unambiguously bound complete fenced text files before running the same task-specific grader. It neither repairs incomplete files nor adds missing user answers. A network-dependent checker can be unavailable and is reported separately. One request per family cannot establish five kinds passed, which requires at least two of three on the official exam. [Protocol](protocol.md) · [Frozen settings](settings.json) · [Input draw and collisions](draw-manifest.json) · [Independent grading contract](grading.md)

## Measured result

The model returned all ten replies. The official task-specific graders passed **0/10** as plain messages and **1/10** with predeclared file delivery. A ranking request received all six correct rows and the correct seller, Tomas, in the answer. The original assistant message already contained both. Writing its complete CSV made it deliverable without a second model call. A different CSV had the expected heading but ten rows against five required, and still failed. The two reference web requests for the live package question succeeded. All ten checks returned determinate results. [Delivered top.csv](delivered/top.csv) · [Native answers](raw.json) · [Every check and reference observation](grades.json) · [Summary](summary.json)

| Outcome | Count |
| --- | ---: |
| Distinct new questions / returning requests | 10 / 10 |
| Requests requiring a file | 7 |
| Complete file blocks written / passing | 2 / 1 |
| Requested files with unclosed fences / no fence | 4 / 1 |
| Requests ending at the 128-token cap | 6 |
| Input tokens / generated tokens | 2,676 / 903 |
| Successful-run request wall / server CPU | 387.25 s / 680.23 s |

Returning one correct novel candidate establishes that this base can sometimes produce a working procedure's result on a new draw when it sees the ordinary text. File binding makes that existing result usable. This ten-question trial supplies neither a multi-generation comparison nor three independent draws per family. Truncated responses, missing source access and wrong semantics all limited what the chosen configuration could deliver. [Per-case outcomes and truncation](summary.json)

### Native transport

An initial one-thread attempt shared the host with training. It omitted the ordinary runtime tensor-repacking flag and timed out twice after 160 seconds before receiving a complete response. The driver stopped at the second request boundary; a third connection was interrupted in 0.007 seconds before any additional native CPU was used. No completed answer was replaced. Those attempts consumed roughly 300 server CPU seconds. After the trainer freed memory, the normal repacked server started on two CPUs and returned all ten first usable replies. The waiting time and failed transport calls are outside the completed-reply timing. Changing the hardware load and packing together prevents attributing the timing difference to either alone. [Initial transport receipts](first-transport.json) · [Initial server log](first-server.log.gz)

[Completed native server log](server.log.gz)

## Reproduce

Run from the repository root with the normal HiveMIND Python environment. Use the pinned ik_llama.cpp CPU server and Ternary-Bonsai-8B GGUF identified by the digests in settings.json. Regenerate the inputs in a separate directory, then use these commands for the measured single-model comparison. The output and scratch paths must be new.

```sh
P=training/experiments/verified_growth/release/native_probe
python "$P/draw.py" --out-dir /tmp/hive-fresh-draw
python "$P/generate.py" --runtime /path/to/llama-server --model /path/to/Ternary-Bonsai-8B-PQ2_0.gguf --threads 2 --scratch /tmp/hive-probe-server --out /tmp/hive-probe-raw.json
python "$P/bundle.py" --receipts /tmp/hive-probe-raw.json --out /tmp/hive-probe-bundle.json
python -m training.experiments.verified_growth.release.native_probe.grader --input /tmp/hive-probe-bundle.json --sdk /path/to/python-wasi-sdk --out /tmp/hive-probe-grades.json
python "$P/summary.py" --receipts /tmp/hive-probe-raw.json --grades /tmp/hive-probe-grades.json --out /tmp/hive-probe-summary.json
```

To re-score the original outputs use the archived raw receipt in the bundle step. No native model or GPU is required for score-only replay. The two site-dependent task families can change with the external websites. [Runner](generate.py) · [Grader](grader.py)
