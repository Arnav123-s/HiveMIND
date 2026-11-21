# Replay the actual 8B updates

The three inputs were selected from the publicly archived G56 training stream before measuring their optimizer updates. The corpus fingerprint and raw row fingerprints are recorded separately. The rows are ordinary training data and were excluded if their task was reserved by the full generation's held-back selector. The frozen short and long row IDs have 198/29 and 475/188 total/answer tokens. The additional row has 847/206 tokens, task dependency ordering and no earlier assistant turn that the original encoder could shorten. This third row was selected for the separate static-cap experiment after the first pair was fixed.

The real T80 base is the unpacked 8B snapshot at `ac20f03fc62e872399218b659c8e949dfca05769`. The release's G53 sources2 edit and G55 trunk are mixed exactly as the G56 sources s0 slice required. The replay grow call trains LoRA rank 16 on the last 14 layers using FP32 on this CPU. The T80 training manifest's `dtype: bf16` records the requested dtype, while the hardware fallback and trainer log establish the actual FP32 computation. Both matched arms use two Torch threads, the same two CPUs, seed, cell name, row order and start tensors. Two steps replace thousands of candidates and a timed curriculum. The comparison excludes external read, judged, prefix caching and validation to measure the two row updates independently. It does not estimate changes to task accuracy.

## Preparation and invocation

Start in the experiment checkout with its pinned Python packages, Hugging Face access for the initial checkpoint download and a checkout of the repository's pinned ik_llama.cpp GGUF converter. Keep the training inputs and output outside the checkout.

```sh
export HF_HOME=/tmp/astra-replay-hf
export HIVE_TERNARY_HOME=/path/to/directory/containing/ik_llama.cpp
export PYTHONHASHSEED=0 TOKENIZERS_PARALLELISM=false
python - <<'PY'
from pathlib import Path
from huggingface_hub import snapshot_download
revision = "ac20f03fc62e872399218b659c8e949dfca05769"
p = Path(snapshot_download("prism-ml/Ternary-Bonsai-8B-unpacked", revision=revision))
refs = p.parent.parent / "refs"
refs.mkdir(exist_ok=True)
(refs / "main").write_text(revision)
PY
python training/experiments/astra_cpu/prepare_native.py /tmp/astra-inputs
git worktree add --detach /tmp/astra-stock d557fa9
```

Choose two CPUs actually assigned to the worker. Each output directory must be new. These commands compare the original source with the candidate training source and retain full GGUFs and trainable tensors in scratch.

```sh
taskset -c 3,4 python training/experiments/astra_cpu/native.py --repo /tmp/astra-stock --arm stock --inputs /tmp/astra-inputs --scratch /tmp/astra-stock-output
taskset -c 3,4 python training/experiments/astra_cpu/native.py --repo . --arm chunk --inputs /tmp/astra-inputs --scratch /tmp/astra-chunk-output
python training/experiments/astra_cpu/compare_native.py /tmp/astra-stock-output /tmp/astra-chunk-output
taskset -c 3,4 python training/experiments/astra_cpu/native.py --repo . --arm recompute --inputs /tmp/astra-inputs --row-file /tmp/astra-inputs/overcap/rows.jsonl --scratch /tmp/astra-recompute-output
```

For the separate retrospective admission replay, download the three `all-rows` ZIPs identified in `archives.json` and extract each `rows.jsonl` into one directory with the names `g51-rows.jsonl`, `g55-rows.jsonl`, `g56-rows.jsonl`. Compare their hashes to the manifest. Use Python module mode so imports resolve.

```sh
python -m training.experiments.astra_cpu.admission /tmp/astra-archives /path/to/unpacked-snapshot --out /tmp/astra-readmission.json
```

The initial availability and cost formula in each original job are rounded. The JSON includes sensitivity to ±0.05 GiB of initial available memory. Actual free memory changes after every pass and real subjects may be retried. This snapshot gives an upper bound on the rows that could be considered at that instant alone. No historical skip is attributed to a specific candidate here. [Per-job dated logs](code-s0-logs.json) · [Replayed admission](admission.json) · [Archive digests](archives.json)
