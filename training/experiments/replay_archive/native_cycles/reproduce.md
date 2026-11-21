# Reproduce the native retention pilot

Use the parent experiment's T80 CPU environment, including the pinned packed and unpacked base models, the repository's llama-server build and a CPython WASI SDK. The local fit needs a 16 GiB worker. Prepare the public cumulative G55 and G56 row files with their recorded hashes. Obtain the release's G55 trunk GGUF and trainable safetensors. Download the three `practice-work` archives by the IDs in the manifest and name them `g55-retention-work-2.zip`, `g55-retention-work-3.zip` and `g55-retention-work-9.zip`. [Native setup](../../astra_cpu/native-replay.md) · [Source IDs and hashes](manifest.json)

With the repository on the Python import path, use a new scratch directory and set the environment variables below to the local assets. The freeze step reconstructs the input JSONL files used by the trainer and verifies each numbered replay record.

```sh
export HF_HUB_OFFLINE=1 PYTHONHASHSEED=0 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1
export TOKENIZERS_PARALLELISM=false
module=training.experiments.replay_archive.native_cycles
python -m "$module.freeze" --archives "$ROW_ARCHIVES" --proofs "$WORK_ARCHIVES" --scratch "$SCRATCH"
python -m "$module.controls" --sdk "$WASI_SDK"

taskset -c "$TWO_CPUS" python -m "$module.pilot" evaluate --scratch "$SCRATCH" --cycle 0 \
  --lora "$G55_TRUNK_GGUF" --model "$PACKED_T80" --runtime "$LLAMA_SERVER"
python -m "$module.pilot" score --scratch "$SCRATCH" --arm release --sdk "$WASI_SDK"
```

Run fits one through three. Start from the exact previous decision's `next` parent. For the first fit this is `release` and the weights are the original G55 trainable safetensors. A kept child's trainable file is under `$SCRATCH/cycle-N/grow/t80+retentionN/adapter_model.safetensors`.

```sh
taskset -c "$TWO_CPUS" python -m "$module.pilot" train --scratch "$SCRATCH" \
  --cycle "$N" --parent "$PARENT" --weights "$PARENT_TENSORS"
taskset -c "$TWO_CPUS" python -m "$module.pilot" evaluate --scratch "$SCRATCH" --cycle "$N" \
  --lora "$SCRATCH/cycle-$N/exports/t80+retention$N.gguf" --model "$PACKED_T80" --runtime "$LLAMA_SERVER"
python -m "$module.pilot" score --scratch "$SCRATCH" --arm "cycle-$N" --sdk "$WASI_SDK"
python -m "$module.pilot" decide --scratch "$SCRATCH" --cycle "$N" --parent "$PARENT"
```

After all three fits and decisions, collect verified per-arm results and compress the original native calls.

```sh
python -m "$module.report" --scratch "$SCRATCH"
```
