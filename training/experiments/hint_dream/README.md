# Can the kept hive learn a new stream-processing skill from a hint?

The kept G55 trunk wrote two Python programs for each generated task. Only the private call received an implementation hint. The public task, example, token limit and model stayed the same. A separate host computed the required values and ran both programs on 24 sealed inputs in CPU WebAssembly. A training row contains the public task and a verified program written by G55. Four formats and four state rules give 16 combinations with seeded parameters, names and inputs. The learning happens in the solver weights. This generator draws from its own practice domain. [Initial protocol](protocol.md) · [Conditional follow-up and transfer design](confirmation.md)

## Initial native sample

| Task | Checks passed blind | Checks passed with hint | Row admitted |
|---|---:|---:|---|
| CSV ranked totals | 0/24 | 0/24 | No |
| Queue alerts after repeated high readings | 6/24 | 9/24 | No |
| INI per-label meter wraps | 2/24 | 2/24 | No |
| JSON filter on final value | 13/24 | 24/24 | Yes |
| CSV alerts after repeated high readings | 11/24 | 0/24 | No |
| Queue per-label meter wraps | 2/24 | 2/24 | No |

One of six tasks qualified, or **16.7%**. This sample fell below the 20% threshold. The blind JSON program summed every reading per label. The private reminder led G55 to keep the latest reading and then apply the threshold. The CSV reminder made a partially correct alert program fail every case. Both directions matter when deciding what to teach. All 12 completions ended normally and took 921.6 seconds combined on two CPU cores while a separate packed workload ran. Each task had 23 unique sealed inputs across the 24 checks because both suites included the empty case. [All 12 native replies and exact grades](evidence/initial/results.json) · [Exported training row](evidence/initial/rows.jsonl)

A second implementation decoded 64 fresh JSON streams and evaluated them in arrival order, with lengths from zero through 63. The blind program passed 10/64. The hinted program passed 64/64. This measures the same practice contract on new inputs. [Independent audit](evidence/initial/independent-audit.json)

## Fresh follow-up with one parser and rule reminder

| Task | Checks passed blind | Checks passed with hint | Row admitted |
|---|---:|---:|---|
| JSON per-label meter wraps | 2/24 | 3/24 | No |
| INI filter on final value | 5/24 | 24/24 | Yes |
| Queue filter on final value | 14/24 | 24/24 | Yes |
| CSV per-label meter wraps | 2/24 | 24/24 | Yes |
| INI ranked totals | 21/24 | 22/24 | No |

Three of five fresh tasks qualified **(60%)**. Across both chronological samples, four of eleven tasks **(36.4%)** yielded training rows. Three involved the final reading per label and one involved cyclic meters. The two cohorts used different format/rule combinations. The live opt-in slot uses the parser-and-rule reminder and keeps the blind and hinted inputs identical apart from that private line. [All 10 follow-up replies and grades](evidence/confirmation/results.json) · [The three exported rows](evidence/confirmation/rows.jsonl)

## Reproduce

Use the pinned G55 weights and runtime hashes recorded in the receipts. `SDK` is the CPython WASI directory containing `python.wasm` and its standard library. Set `HF_HOME` to the cached unpacked Ternary-Bonsai-8B model and `HIVE_TERNARY_HOME` to a checkout containing the pinned `ik_llama.cpp` converter. The measured unpacked model revision was `ac20f03fc62e872399218b659c8e949dfca05769`. The host used wasmtime 36.0.0 with `python.wasm` SHA-256 `278a485c42319053a7989b837bbaa42c2b9d1892d65cb582d9c41dac8cef5f7e`. [WASI installation](../../reports/rule_lab/fieldwork/reproduce.md)

```bash
args=(--server "$SERVER" --model "$GGUF_BASE" --sdk "$SDK")
python -m training.experiments.hint_dream.pilot "${args[@]}" --adapter "$G55_GGUF" --panel initial --out runs/hint-initial
python -m training.experiments.hint_dream.pilot "${args[@]}" --adapter "$G55_GGUF" --panel transfer --out runs/hint-before
python -m training.experiments.hint_dream.pilot "${args[@]}" --adapter "$G55_GGUF" --panel confirmation --out runs/hint-confirmation
python -m training.experiments.hint_dream.audit --sdk "$SDK" --panel runs/hint-initial
python -m training.experiments.hint_dream.fit --parent "$G55_SAFETENSORS" --panels runs/hint-initial runs/hint-confirmation --out runs/hint-fit
candidate=runs/hint-fit/exports/t80+f4hintdream.gguf
python -m training.experiments.hint_dream.pilot "${args[@]}" --adapter "$candidate" --candidate-sha "$(sha256sum "$candidate" | cut -d' ' -f1)" --panel transfer --out runs/hint-after
```
