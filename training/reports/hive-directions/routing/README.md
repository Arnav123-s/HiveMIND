# Saved-method routing probe

These 26 constructed messages exercise chat at main commit `1414d49243987ea58c5913af251c39e104d77b68`, which contains merged PR 107. The messages and expected behavior in `cases.json` were frozen before the first execution. Their SHA-256 is `4a429346814dcbee3b38ad1a82ff55bbdf08c8856dcd3a747429cba3c01467cc`. The author had already read the implementation and its published tests. These counts describe a deliberately difficult stress set.

| Group | Matched expected action and value | Observations |
|---|---:|---|
| Plain requests | 6/6 | Five correct numbers and one correct request for a rounding convention |
| Inputs with extra context | 0/6 | Three wrong numbers, two missing-input responses, one ambiguity response |
| Other tasks with overlapping words | 2/6 | Two correct worker fallbacks, three wrong numbers and one missing-input response that interrupted a different task |
| Incomplete inputs or incompatible requests | 0/6 | Six numeric answers despite an unknown weight, alternative weights, a different output contract, a replacement tariff or invalid typed data |
| Two dialogue controls | 2/2 route boundaries | A greeting reached the direct-answer boundary and an explanation request reached the learned routing boundary |

`probe.py` calls the normal `talk.reply()` entry point, using the repository's saved depot program and its two invoice convention programs. It runs the actual sources in the CPython WebAssembly guest. The test supplies a base-model identifier and stops execution at any learned-router, conversation-model or general-worker call. Thus it can observe these boundaries without grading what a language model or the ordinary team might have answered. The invoice bank is constructed from the repository's frozen source fixtures. Validation counts in its metadata follow the PR's test convention and are not new training or validation results.

For example, the parcel weights in `c1` are 410 and 820 grams. The router also treated order number 801 as a weight, so the saved method charged 700 cents instead of 520. In `o1` the user explicitly rules out a shipping fee and asks for a weight conversion. In `b5` the saved code accepted a negative weight supplied as JSON. The failure can arise before a previously checked program performs its calculation.

## Reproduce

Use a HiveMIND checkout at the commit above, the project's Python environment with the Fieldwork dependencies, and the CPython WASI SDK described in `training/reports/rule_lab/fieldwork/reproduce.md` in that checkout. The recorded run used Python 3.12.14, wasmtime 36.0.0 and a `python.wasm` with SHA-256 `278a485c42319053a7989b837bbaa42c2b9d1892d65cb582d9c41dac8cef5f7e`. Run the following from this probe's directory, using the corresponding paths on your machine.

```bash
python probe.py --checkout /path/to/HiveMIND --sdk /path/to/wasi --out replay.json
diff -u observed.json replay.json
```

Each fixture row contains the group, case ID, message, expected action or saved-method name, and expected scalar value where applicable. For `decline`, a missing-input response, an ambiguity response or a worker fallback is acceptable. For `fallback`, the request asks for a different operation that should reach the normal workers. `observed.json` includes the action, the values that the saved method actually received, the result and the grade for each message.
