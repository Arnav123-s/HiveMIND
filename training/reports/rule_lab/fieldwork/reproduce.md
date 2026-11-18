# Run the field workers

From the repository root, a verified worker can handle new data on a CPU with no language model loaded. This example reads incoming geology samples, writes a snapshot, starts a fresh interpreter with only the reopened snapshot and the revised request, and commits the CSV and JSON.

```bash
python3 -m venv .fieldwork-venv
. .fieldwork-venv/bin/activate
python -m pip install wasmtime==36.0.0 numpy
A=runs/fieldwork-assets
OUT=training/reports/rule_lab/fieldwork
mkdir -p "$A/wasi"
curl -fL 'https://github.com/brettcannon/cpython-wasi-build/releases/download/v3.13.9/python-3.13.9-wasi_sdk-24.zip' -o "$A/wasi.zip"
echo "f974d681668b8a51bf548474c9999630fe83a316155a4e937eaff57ea3ea4f39  $A/wasi.zip" | sha256sum -c -
unzip -q "$A/wasi.zip" -d "$A/wasi"
python -m team fieldwork --sdk "$A/wasi" --bank "$OUT/bank" \
  --spec "$OUT/geology-order.json" --out runs/my-geology-order
cat runs/my-geology-order/late-request/summary.csv
cat runs/my-geology-order/late-request/audit.json
```

The example reports two Ridge tickets weighing 40 grams in total. The audit retains the original kept-ticket count and conflict list. A second invocation with the same work order and output directory checks the saved receipt and restores missing output files from its recorded values. A new set of inputs belongs in a fresh output directory. The shipped bank contains qualified executable source. Its filenames are SHA-256 digests of the source. The CPython guest sees its standard library and a JSON input stream. The host reopens snapshots and commits named file outputs.

## Give the hive a new job

A work-order JSON file has a short `name`, a natural-language `task`, public `examples` with input and expected output, optional independent `validation`, and `jobs` with IDs and inputs. A `files` list requests exact named text outputs. Use `compare` to compare parsed CSV or JSON and retain the terminal newline requirement for CSV. A job that returns a JSON value can name a `snapshot_file`. A later job can bind it into one of its input fields with `from_job`. See the bundled geology order for both phases. The validation rows are withheld from the local model. All validation rows must pass before the host releases job files. When a new task has only public examples, the receipt identifies the independent check count as zero.

To have a local model author a new worker, supply its GGUF and `llama-server`. The checked library can grow in a writable directory between orders.

```bash
python -m team fieldwork --spec my-order.json --out runs/my-new-order \
  --bank runs/my-learned-workers --sdk "$A/wasi" --weights "$WEIGHTS" \
  --binary "$LLAMA_SERVER" --threads 4 --concise --budget 1400 --rounds 2
```

The measured runtime was ik_llama.cpp revision `7aa7e01482db892b023bb9aace9a40567ab5297a`. The trials used greedy decoding, seed 3141, one slot and 6,144 tokens of context. The runtime and all model files are external to the repository. [Runtime source](https://github.com/ikawrakow/ik_llama.cpp/tree/7aa7e01482db892b023bb9aace9a40567ab5297a)

| Model file used | SHA-256 | Source |
| --- | --- | --- |
| Qwen2.5-Coder-3B-Instruct Q4_K_M | `724fb256bec1ff062b2f65e4569e871ad2e95ab2a3989723d1769c54294730b7` | [Qwen release](https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct-GGUF/tree/f74adce6aa16316c625447af059dbebe4983757c) |
| Qwen3-4B-Instruct-2507 Q4_K_M | `3605803b982cb64aead44f6c1b2ae36e3acdb41d8e46c8a94c6533bc4c67e597` | [GGUF release](https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF/tree/a06e946bb6b655725eafa393f4a9745d460374c9) |
| Qwen3.5-4B Q4_K_M | `00fe7986ff5f6b463e62455821146049db6f9313603938a70800d1fb69ef11a4` | [GGUF release](https://huggingface.co/unsloth/Qwen3.5-4B-GGUF/tree/e87f176479d0855a907a41277aca2f8ee7a09523) |
| Qwen2.5-Coder-7B-Instruct Q4_K_M | `509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c` | [Qwen release](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF/tree/13fb94bfda8c8cf22497dc57b78f391a9acb426a) |
| Ternary Bonsai 8B with the HiveMIND g41 coding adapter | Base and adapter revisions and hashes are recorded in the earlier experiment | [HiveMIND model provenance](../README.md) |

## Reproduce the experiments

Set `PKG=training.experiments.fieldwork` and `R=runs/my-field-study`. The dependencies above suffice for the pure WASI trials. The optional NumPy guest for competing numerical workers requires Linux with libseccomp. The optional forecast plot uses Matplotlib. Set `OPENBLAS_NUM_THREADS=1` and `OMP_NUM_THREADS=1` for the numerical studies.

```bash
PKG=training.experiments.fieldwork
R=runs/my-field-study
mkdir -p "$R"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
python -m "$PKG.induction" --sdk "$A/wasi" --out "$R/induced-school.json"
python -m "$PKG.algorithm_school" --sdk "$A/wasi" --school "$R/induced-school.json" --out "$R/algorithm-school-v2"
for split in public exam confirmation; do
  python -m "$PKG.discovery" --split "$split" --out "$R/scientist"
done
python -m "$PKG.thermal_school" --out "$R/scientist/thermal-school.json"
python -m "$PKG.unknown_instruments" --out "$R/scientist/unknown.json"
python -m "$PKG.outlook" --snapshot "$OUT/noaa-2026-10-09.csv" --out "$R/outlook"
```

For a language model's school and original field exams, set `WEIGHTS` to its pinned file. Repeat with the other weights in separate directories. The g41 pair also takes `--adapter /path/to/t80+g41code.gguf` on the drafting command. Private grades read the frozen source file.

```bash
python -m "$PKG.draft" --binary "$LLAMA_SERVER" --weights "$WEIGHTS" --out "$R/4b-cold" \
  --threads 2 --tasks interval parity departure version trend dynamics roster ferry climate thermal ledger
python -m "$PKG.campaign" school --cold "$R/4b-cold" --out "$R/4b" --sdk "$A/wasi"
python -m "$PKG.library" --sources "$R/4b/school.json" "$R/induced-school.json" --out "$R/checked-library.json"
python -m "$PKG.campaign" develop --cold "$R/4b-cold" --out "$R/4b" --sdk "$A/wasi" \
  --binary "$LLAMA_SERVER" --weights "$WEIGHTS" --library "$R/checked-library.json" --rounds 2 --threads 2
for split in exam confirmation; do
  python -m "$PKG.campaign" examine --cold "$R/4b-cold" --out "$R/4b" --sdk "$A/wasi" --split "$split"
done
```

The observatory runner accepts a local-model path, independent seed, token budget and optional verified school. The larger-attempt comparison used one 2,800-token attempt per arm. The shorter comparison used two 1,400-token attempts. The two-member version uses a supplied intermediate type containing the qualifying intervals.

```bash
python -m "$PKG.observatory" --binary "$LLAMA_SERVER" --weights "$Q35" --sdk "$A/wasi" --out "$R/observatory" --rounds 2
python -m "$PKG.observatory" --binary "$LLAMA_SERVER" --weights "$Q35" --sdk "$A/wasi" \
  --out "$R/observatory-long" --rounds 1 --budget 2800 --concise --prior-school "$R/observatory/bank" --seed 240587 --blocks 7103
python -m "$PKG.observatory_parts" --binary "$LLAMA_SERVER" --weights "$Q4B" --sdk "$A/wasi" \
  --prior-school "$R/observatory/bank" --out "$R/observatory-contract" --memory-view contract
python -m "$PKG.stages" --binary "$LLAMA_SERVER" --weights "$Q4B" --sdk "$A/wasi" --out "$R/stages-typed" \
  --sources "$R/4b-cold/ledger.json" "$R/g41-cold/ledger.json" "$R/recruit-cold/ledger.json"
python -m "$PKG.report_school" --sdk "$A/wasi" --intake "$R/stages-typed/intake.json" --out "$R/report-school"
python -m "$PKG.coding_trials" --binary "$LLAMA_SERVER" --weights "$CODER7B" --sdk "$A/wasi" \
  --root "$R" --library "$R/checked-library.json"
python -m "$PKG.dispatch" --sdk "$A/wasi" --root "$R" --out "$R/routing"
```

To measure the effect of permitting NumPy on frozen scientific submissions, run `python -m "$PKG.runtime_trial" --root "$R"` before dispatch. The original whole-phase prompt for the first geology comparison is preserved in commit `6184101`. The later version supplies the input paths for the requested phase. For a quick regression run, set `HIVE_FIELDWORK_WASI` to the extracted SDK directory and run `python -m pytest -q tests/test_cpu_fieldwork.py`.

The model-written geology phase can also be repaired by choosing generic program edits against its public examples. The extended exam uses an independent SQLite implementation. The observatory sweep school can combine its learned span logic with a previously promoted file writer. Both studies record the sources and checks for every released worker.

```bash
python -m "$PKG.phase_repair" --sdk "$A/wasi" --phases "$R/stages-typed" --out "$R/phase-repair"
python -m "$PKG.sweep_school" --sdk "$A/wasi" --bank "$R/observatory/bank" --out "$R/sweep-school" \
  --writers "$R/observatory-contract/coverage_files-bank"
python -m team fieldwork --sdk "$A/wasi" --bank "$OUT/bank" \
  --spec "$OUT/observatory-order.json" --out runs/my-observatory-order
```

One frozen program can also be run directly from the archive against JSON on stdin. The runner verifies its source digest and uses the execution environment in its manifest. This scheduler example returns `[6, 3]`.

```bash
echo '{"gap":1,"jobs":[[0,2,4,1],[3,4,2,0],[3,4,2,0],[1,4,6,1]]}' | \
  python -m training.experiments.fieldwork.replay --archive "$OUT/programs.zip" --worker roster --sdk "$A/wasi"
```
