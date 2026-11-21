# Reproduce the three controls

Use the assets and local environment from the completed mixed study, including its exact G55 parent, mixed trainable artifacts and measured G55 release responses. Its five questions, calibration controls and grading script are reused unchanged. [Setup](../reproduce.md)

Prepare an empty scratch directory. The archive selector rebuilds the three input JSONL files and verifies each replacement using the original generator, solution source and checker. The compressed rows contain every byte needed to reconstruct those input files without selecting replacements again.

```sh
module=training.experiments.replay_archive.native_cycles
HF_HOME="$TOKENIZER_CACHE" python -m "$module.fresh_only.freeze" \
  --archives "$ROW_ARCHIVES" --scratch "$CONTROLS"
cp "$MIXED"/release-{calls,grades}.json "$CONTROLS/"
```

Use the same two training CPUs and two inference CPUs for all comparisons. Each proposal begins at the original G55 release regardless of the preceding hypothetical acceptance. For each proposal run the following with `N` set to 1, 2 and 3 in turn.

```sh
taskset -c "$TWO_TRAIN_CPUS" python -m "$module.pilot" train --fresh-only --scratch "$CONTROLS" \
  --cycle "$N" --parent release --weights "$G55_TRUNK_TENSORS"
taskset -c "$TWO_INFER_CPUS" python -m "$module.pilot" evaluate --scratch "$CONTROLS" --cycle "$N" \
  --lora "$CONTROLS/cycle-$N/exports/t80+retention$N.gguf" --model "$PACKED_T80" --runtime "$LLAMA_SERVER"
python -m "$module.pilot" score --scratch "$CONTROLS" --arm "cycle-$N" --sdk "$WASI_SDK"
python -m "$module.pilot" decide --scratch "$CONTROLS" --cycle "$N" --parent release
```

Collect matched weights, realized optimizer input order, costs, raw programs and functional scores after all three controls finish.

```sh
python -m "$module.fresh_only.report" --scratch "$CONTROLS" --original "$MIXED" --initial "$G55_TRUNK_TENSORS"
```
