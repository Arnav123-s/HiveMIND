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

Three of five fresh tasks qualified **(60%)**. Across both chronological samples, four of eleven tasks **(36.4%)** yielded training rows. Three involved the final reading per label and one involved cyclic meters. The two cohorts used different format/rule combinations. Across the eleven public prompts, the largest word-set similarity to any of 2,852 checked G55 task texts ranged from 0.080 to 0.100 on a zero-to-one scale. This measures wording overlap. The live opt-in slot uses the parser-and-rule reminder and keeps the blind and hinted inputs identical apart from that private line. [All 10 follow-up replies and grades](evidence/confirmation/results.json) · [The three exported rows](evidence/confirmation/rows.jsonl)

The second implementation cross-checked 64 additional fresh input streams for each selected follow-up contract. The earlier INI, queue and CSV programs passed 17, 13 and 3. Every corrected program passed all 64. Including the earlier JSON audit, that gives **43/256 blind and 256/256 hinted** across four selected contracts. These are new inputs to known practice contracts. [Follow-up independent audit](evidence/confirmation/independent-audit.json)

## Four verified updates on the original weights

The ordinary CPU training worker gathered all four programs, inherited all 98 G55 LoRA modules at rank 32 and finished one optimizer step per row. The average training length was 328 tokens. Three rows fit the ordinary backward pass and one used checkpointing. The measured fit and weight comparison took 407.66 seconds, peaked at 11.34 GiB and used zero swap. All 196 LoRA tensors changed. The 73,835,264-byte candidate GGUF has SHA-256 `fffbb3692c8f1202b7df14014c8e515f77799f000428fe3fbd906f5b11f7490b`. [Download the tested GGUF](https://raw.githubusercontent.com/Arnav123-s/HiveMIND/df9317a688e2a6a2461fb664c393ec9b8311cce4/t80-hint-dream.gguf) · [Training receipt](evidence/fit/receipt.json) · [Worker log](evidence/fit/worker.log)

## Unhinted recall on every training task

| Previously taught task | Original G55, 24 checks | Trained G55, same 24 | Original G55, separate 64 | Trained G55, same 64 |
|---|---:|---:|---:|---:|
| JSON filter on final value | 13 | 24 | 10 | 64 |
| INI filter on final value | 5 | 2 | 17 | 13 |
| Queue filter on final value | 14 | 24 | 13 | 64 |
| CSV per-label meter wraps | 2 | 2 | 3 | 3 |

After four optimizer steps the child could solve **two of its four training tasks** from their original public instructions, up from zero. Its unhinted JSON and queue programs reproduced the respective teaching programs byte for byte. Each passed all 64 inputs from the independent streaming implementation. The INI program selected the name of the input field instead of its label value. The CSV program used accumulated change as the previous meter reading. Across the four tasks, blind checks rose from 34/96 to 52/96 and from 43/256 to 144/256 on the second implementation. Both comparisons used all four known prompts, identical messages and greedy decoding. Every completion stopped within the cap. [JSON](evidence/trained-0/results.json) · [INI](evidence/trained-1/results.json) · [Queue](evidence/trained-2/results.json) · [CSV](evidence/trained-3/results.json)

## Blind transfer to three reserved combinations

| New task | Original G55 checks | Trained G55 checks |
|---|---:|---:|
| JSON threshold alerts | 7/24 | 10/24 |
| CSV filter on final value | 0/24 | 0/24 |
| INI threshold alerts | 2/24 | 2/24 |
| Completely solved tasks | 0/3 | 0/3 |

The three task types were disjoint from both practice cohorts. The candidate matched 12/72 sealed outputs, compared with 9/72 for the starting model. Both scored zero whole tasks. Both CSV programs wrote a correct final-value filter but passed the list returned by `splitlines()` to `StringIO`, which requires a string. They failed before filtering a row. Both INI programs attempted integer conversion on label text. Neither JSON alert program tested the required threshold. The local study establishes a way to collect verified training examples and fit them on a CPU. Whole-task transfer remains unproven on this panel. [Original blind responses](evidence/transfer-parent/results.json) · [Candidate blind responses](evidence/transfer-child/results.json) · [Frozen prompts and oracle digests](transfer-manifest.json)

An independent hosted diagnostic substitutes the measured GGUF for the single trunk in the ordinary 25-member G55 roster and uses the original fixed held-out examiner. It has a separate control and thirty tasks across ten kinds. [Official evaluation recipe](https://github.com/Arnav123-s/HiveMIND/blob/e24bbea34b7ddbd80ce6456ebbb2aaf40749c97b/training/experiments/astra_orders/worker_contracts/f4-held.md)

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
child_sha=fffbb3692c8f1202b7df14014c8e515f77799f000428fe3fbd906f5b11f7490b
python -m training.experiments.hint_dream.pilot "${args[@]}" --adapter "$candidate" --candidate-sha "$child_sha" --panel transfer --out runs/hint-after
python -m training.experiments.hint_dream.pilot "${args[@]}" --adapter "$candidate" --candidate-sha "$child_sha" --panel trained --out runs/hint-seen
python -m training.experiments.hint_dream.parser_transfer --qualify --sdk "$SDK" --bank runs/parser-bank
for case_index in 0 1 2 3; do
  python -m training.experiments.hint_dream.parser_transfer "${args[@]}" --adapter "$candidate" --bank runs/parser-bank --case "$case_index" --out "runs/parser-case-$case_index"
done
```
