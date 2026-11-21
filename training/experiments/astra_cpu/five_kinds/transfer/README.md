# Five independent first programs after five updates

The native 8B starting adapter completed **0/5** fresh contracts. After five optimizer updates it completed **1/5**, gaining the bank class and losing none. The new bank question changed the withdrawal limit from three to four, the allowed overdraft from $100 to $0, and the initial sample balance from $215 to $15. The starting program omitted the overdraft check and reported −$421. The updated program checked the balance before withdrawing, reported $15, and passed all 283 hidden bank calls. [Paired results](results.json) · [Original training cases](../selection.json)

| Fresh family | Hidden operations, start → updated | Requested example printed, start → updated | Complete contract, start → updated |
| --- | ---: | --- | --- |
| Bank class | 208/283 → 283/283 | No → Yes | Fail → Pass |
| Arithmetic parser | 42/52 → 42/52 | Yes → Yes | Fail → Fail |
| LRU cache | 308/329 → 308/329 | No → Yes | Fail → Fail |
| State machine | 0/72 → 0/72 | No → No | Fail → Fail |
| Dependency schedule | 61/61 → 61/61 | No → No | Fail → Fail |

All 75 additional hidden-operation successes came from one question. The parser answers were byte-identical. The updated cache printed the right sample but missed 21 hidden operations. The starting state-machine program hit the token cap, and the updated program raised a key error. Both scheduling programs wrote valid modules, then failed their own assertions before printing the requested answer. The 797 operations exercise five related modules. The evidence measures one successful transfer to a new question from a familiar generator. [Starting grades](grades-parent.json) · [Updated grades](grades-five.json)

The starting arm generated 1,370 tokens across its five requests in 293 seconds, reaching the 384-token cap once. The updated arm used 1,163 tokens in 254 seconds without reaching the cap. Both used the same two pinned CPU cores. These timings exclude server initialization and grading. [Raw starting responses and settings](native-parent.json) · [Raw updated responses and settings](native-five.json)

The frozen panel takes one new seed from each of the five training makers. All five normalized prompts are absent from the cumulative G56 archive, including the five selected training inputs. The draws change the conditions, inputs and correct outputs within familiar programming families. Each writer receives only the stock taught-member orders and that question. [Exact messages and seeds](panel.json) · [Frozen protocol](protocol.md)

The grader runs each first program with writable access to its own task directory in a fuel-limited CPython WASI instance. After a clean exit it uses the hive's usual module-saving helper when needed. It then imports only the resulting module in a fresh, read-only guest. The guest receives operation names and arguments. The host keeps the expected returns and exceptions until it compares observations. To pass, a first program must exit successfully, produce the named module, pass every hidden operation and print the requested sample values. A missing module scores zero hidden operations. Where a constructor fails, none of that scenario's later calls receives credit. Positive controls passed 797/797 operations, and both missing-file and wrong-function controls failed. [Judge implementation](grade.py) · [Guest controls](controls.json)

## Reproduction

The exact five-update adapter is available as a 39,887,616-byte GGUF on the artifact branch. It loads beside the existing T80 base in the repository's CPU `llama-server` using `--lora t80-native-five.gguf`. Its SHA-256 is `99dc4d80a397ff307a89ecdb177fcca71aa6918c5a0f9f18e5570fde6ec6924f`. [Download the tested adapter](https://raw.githubusercontent.com/Arnav123-s/HiveMIND/e3c31661531953f4e4f65de4fd57f8ed27997ca2/training/experiments/astra_cpu/five_kinds/weights/t80-native-five.gguf)

To export the exact starting comparison after reproducing training, set `FIVE_RUN` to the five-step run's scratch directory, `T80_SNAPSHOT` to the unpacked base model directory and `IK_LLAMA` to the repository's pinned ik_llama.cpp checkout. The starting GGUF SHA-256 is `b603c9395c82838c28831a491d8fc8b48dd09e8bf26c158573724807bef2b3f4`.

```sh
baseline_export=$(mktemp -d)
mkdir "$baseline_export/t80+astrastudy"
cp "$FIVE_RUN/grow/t80+astrastudy/adapter_config.json" "$baseline_export/t80+astrastudy/"
cp "$FIVE_RUN/grow/t80+astrastudy.start.safetensors" "$baseline_export/t80+astrastudy/adapter_model.safetensors"
START_GGUF="$baseline_export/parent.gguf"
python "$IK_LLAMA/convert_lora_to_gguf.py" --base "$T80_SNAPSHOT" --outfile "$START_GGUF" --outtype f16 "$baseline_export/t80+astrastudy"
```

Use the same repository environment, native binary, T80 GGUF, WASI SDK, starting adapter and five-update adapter as the [training run](../README.md). The native runner checks its runtime, model, panel and LoRA hashes, starts a fresh single-adapter server for each arm and checks that its scale is one. The raw native receipts include the exact generation settings, response lengths and finish reasons. Supply real local asset paths in these commands.

```sh
post=training/experiments/astra_cpu/five_kinds/transfer
mkdir -p /tmp/astra-program-pairs
for arm in parent five; do
  if test "$arm" = parent; then
    edit="$START_GGUF"
  else
    edit="$FIVE_GGUF"
  fi
  edit_hash=$(sha256sum "$edit" | cut -d' ' -f1)
  taskset -c 3,4 python "$post/native.py" --runtime "$LLAMA_SERVER" --model "$T80_GGUF" --arm "$arm" --lora "$edit" --lora-sha "$edit_hash" --out "/tmp/astra-program-pairs/native-$arm.json" --log "/tmp/astra-program-pairs/$arm.log"
  python -m training.experiments.astra_cpu.five_kinds.transfer.grade --sdk "$WASI_SDK" --native "/tmp/astra-program-pairs/native-$arm.json" --out "/tmp/astra-program-pairs/grades-$arm.json"
done
python -m training.experiments.astra_cpu.five_kinds.transfer.summarize --directory /tmp/astra-program-pairs
```

To re-create the questions, run the frozen selector against the authenticated G56 `rows.jsonl`. The panel's SHA-256 is `8d3903f5bd41ea2d65973931026069baa297c0009af57471a0cdef8ee9db1945`. The fitted model scores concern one deterministic first attempt per family. No multi-turn debugging, ensemble selection or held-out-kind examination enters this comparison.
