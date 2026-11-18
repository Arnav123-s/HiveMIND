# One free-form repair by the G47 code cell

The code cell received the original, failing sensor function and ten checks. It could write any Python solution. In its one greedy response, it reproduced the parent function byte for byte. Both passed **105/228** previously published sensor cases, including **42/48** boundary cases and **63/180** longer input sequences. The upward-count result was right on all 228. Elapsed time was wrong on 123. For example, when a signal starts at 1.75 and ends at −4 half a minute later, it spends about 0.15217 minutes above zero. The returned function gives zero because it accumulates exposure only on upward crossings. The earlier bounded search passed 228/228 on the same inputs. This comparison measures one free-form model attempt. The search had a human-specified set of candidate operations.

## Repeat the score

Run the following commands from a HiveMIND checkout containing the original sensor grader at commit `39ec64b` or later. The numerical worker requires Linux with `libseccomp.so.2`. Python’s standard library supplies the rest.

```sh
trial=training/reports/checked-repair/free-proposal
python "$trial/grade_submission.py" --repo . --parent
python "$trial/grade_submission.py" --repo . --reply "$trial/output.txt"
```

The grader accepts only the two reviewed program hashes and verifies the original oracle’s hash. It extracts the first Python-fenced block from the frozen response. Only an unfenced response would be treated as plain Python. The candidate process gets the original 228 inputs and returns raw pairs. It runs with restricted builtins, no filesystem, network or process operations after startup, 160 MiB of address space and a three-second soft CPU limit. The separate scoring process runs the existing rational-arithmetic oracle. Duration uses the original relative and absolute tolerance of `1e-9`. Counts must match and booleans fail both checks.

## Reproduce the model request

`prompt.txt` is the exact prompt. `request.json` contains the inference payload including the fixed seed, greedy sampling and 1,200-token limit. `results.json` records the base, the sole active adapter (`t80+g47code2` at scale 1), runtime revision and asset hashes, and both scores. On a local compatible server with that adapter active, repeat the HTTP request by setting `inference_endpoint` to its `/v1/chat/completions` URL.

```sh
curl --fail-with-body --header 'Content-Type: application/json' --data-binary @"$trial/request.json" "$inference_endpoint"
```

The recorded server stopped naturally after 304 output tokens in 102.467 seconds. The reported score uses the one stored response. A rerun on another machine can produce different text. These existing 228 inputs had already been published when this follow-up ran.
