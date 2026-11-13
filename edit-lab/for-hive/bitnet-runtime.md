# Muse's work, Muse's side

# Q3 — A runtime on which the published 2.4B BitNet actually works

**What I chose and why:** I took Fable's question as advised, but attacked it as three
parallel lanes instead of a serial commit hunt — (A) current head, measured stock, with a
no-rebuild metadata override, and with the one-line source fix; (B) the May-2025 runtime
Fable's check could not build, plus source-level bisect evidence; (C) a Hugging Face
transformers reference reading on the bf16 weights, on the exact bytes Fable scored.
Reason: the public record (microsoft/BitNet issue #588, the lowbit-atlas audit) already
localized the fault to the July-2026 llama.cpp submodule bump, so the fastest honest path
was to verify that claim at head, land the era measurement that was missing, and price the
model itself independently — all at once. The prompt format was not chased: the model's own
chat template renders exactly the `User: …<|eot_id|>Assistant: ` form Fable used, and the
model's config states its activation outright (`hidden_act: "relu2"`).

## The question

`microsoft/bitnet-b1.58-2B-4T-gguf` on Microsoft's BitNet runtime at its current head
reads plain English at perplexity ~70 and repeats itself on every answer, on two CPUs.
Needed: the exact commit, build commands and prompt format on which it answers "print
every prime below 30" with a working program — or a reference reading
(Hugging Face transformers on the bf16 weights) showing the model itself is that weak.

## What was tried

All perplexity rows: the published GGUF (`ggml-model-i2_s.gguf`, 1,187,801,280 bytes,
sha256 `4221b252…c2162`), scored on Fable's exact input — the first 9000 bytes of GPL-3 —
with `llama-perplexity -c 256 --chunks 6 -t 4`, on an AMD EPYC 9D25 (AVX2 + AVX-512).
Generations greedy (`--temp 0 --special -r '<|eot_id|>' -no-cnv`), prompt
`User: {q}<|eot_id|>Assistant: `.

| Arm | Runtime | Change vs stock | PPL | Primes below 30 |
|---|---|---|---|---|
| Fable baseline | BitNet head 0b341e5, submodule 390c3077 | — | 70.2536 | loops, no code |
| A1 stock (reproduced here) | same | — | **70.2536 ± 7.71** (per-chunk identical) | NOT working: 160 tokens loop "Here is a Python program…" ×11, never emits code |
| A2 + `--override-kv bitnet-b1.58.hidden_activation=str:relu2` | same binary | metadata override only | **70.2536 ± 7.71** — bit-identical | not run (PPL unchanged) |
| **A3 + one-line patch** | 0b341e5 + patch | `LLM_FFN_SILU → LLM_FFN_RELU_SQR`, `src/models/bitnet.cpp:133` | **10.3541 ± 1.10** | **WORKING PROGRAM** — executed, prints exactly 2 3 5 7 11 13 17 19 23 29 (two independent generation runs, both pass) |
| A4 = A3 with official sampling | 0b341e5 + patch | `--temp 0.6 --top-p 0.9` instead of greedy | (same build) | **WORKING PROGRAM** |
| B May-2025 era, unpatched | BitNet c1e9a9a (2025-05-31), submodule 40ed0f29 | era build (see commands) | **10.3149 ± 1.10** | begun twice, coherent prefix identical to A3's program; not run to the end on the era binary (decode starved, ~90 s/token under load) |
| C reference reading | HF transformers 5.22.2 on the bf16 weights | no C++ runtime | **9.4303** (6 windows: 5.15 / 8.68 / 17.47 / 6.88 / 11.77 / 11.12) | generations not completed (runner killed by a VM restart after the PPL saved) |

Source evidence, head: in `3rdparty/llama.cpp/src/models/bitnet.cpp` the FFN activation is
hardcoded `LLM_FFN_SILU` (line 133); there is no `LLM_FFN_RELU_SQR` in the file, and the
bitnet builder never reads `hidden_activation` — the only consumer of that key is the
modern-bert builder, and the string→op map has no `relu2` entry at all. That is why A2 is a
measured no-op in this fork, whatever it does in other lineages. Source evidence, era: the
May-2025 tree still had separate builders — `build_bitnet_158()` uses `LLM_FFN_RELU_SQR`
(src/llama.cpp line 15501) for this model's arch (`bitnet-b1.58`); the SiLU builder serves
the different `bitnet` arch only. 765741d records the same submodule commit as c1e9a9a and
their CPU-runtime diff is empty, so the era number covers both May commits. The July-2026
submodule bump (BitNet 425fbbc → 390c3077) is where the builders merged and the wrong one
survived — issue #588's account, confirmed here at source level and by measurement.

## Verdict

**The model is not weak. Current head is broken by one wrong constant, and the working
recipe is:**

- **Commit:** microsoft/BitNet main `0b341e5` (2026-07-27), submodule
  isHuangXin/llama.cpp `390c3077` — i.e. current head, plus one line.
- **Patch:** in `3rdparty/llama.cpp/src/models/bitnet.cpp`, line 133:
  `LLM_FFN_SILU` → `LLM_FFN_RELU_SQR`.
- **Build:** the setup_env flow (`python setup_env.py -md models/BitNet-b1.58-2B-4T -q i2_s`,
  clang 18; in our runs its steps were driven directly — tree gguf-py, `codegen_tl2`,
  cmake — with the same flags; the published GGUF needs no conversion).
- **Prompt:** `User: Write a Python program that prints every prime below 30.<|eot_id|>Assistant: `
  with `--special -r '<|eot_id|>' -no-cnv`, greedy. It answers with a complete `is_prime`
  program, stops at `<|eot_id|>`, and the program was executed here: output exactly
  `[2, 3, 5, 7, 11, 13, 17, 19, 23, 29]`. The capital question answers coherently in the
  same run ("…chosen as the capital in 1908 and is located in the Australian Capital
  Territory (ACT)…"), where stock head loops on the same sentence.

Three independent readings agree: patched head 10.3541, unpatched May-2025 runtime
10.3149, transformers on the master weights 9.4303 (bf16 scoring, so a small gap is
expected) — against 70.2536 stock. If an unpatched tree is preferred, **c1e9a9a is the
newest commit measured healthy**; anything from the July-2026 submodule bump onward
carries the bug until the one line is applied. `team/bitnet.py` can take the patched
build as-is.

## What was not run

- **Conversion from bf16** (A5): attempted, clean negative. With the tree's own gguf-py
  (0.19.0, staged in `~/workspace/bitnet-q3/venv_conv/`) the converter died at step 1/3
  (preprocess) — OOM-killed at 4,404 MB peak RSS on this 7 GB VM; it wants ~12 GB. The
  ashp fallback (32 GB) was deliberately not taken: Arnav parked all laptop work on
  2026-11-13. The staged tree stays in Q3 for any ≥16 GB machine. It is also unnecessary
  — the patch fixes the published GGUF itself. The provenance rule stands from Fable's
  attempt: the converter only works with the tree's own gguf-py; the public package
  dies with `KeyError: BITNET_25`.
- **Transformers generations** (lane C): the PPL reference landed; the generation stage
  was killed by a VM restart and not re-run, because A3's executed program already
  answers the question and B/C agree on the model's strength.
- **Era primes to completion**: the era binary's two partial generations match A3's
  completed output token-for-token up to their cut points, but the era run itself was
  never carried to `<|eot_id|>` — decode was starved by the shared VM.
- **Wikitext-2 numbers**: not measured here. The 17.109 reference and #588's 99.8→17.1
  are wikitext; every number above is on Fable's GPL bytes, like-for-like against
  Fable's 70.2536.

## Exact commands

Stock / patched perplexity (the only difference is the one-line patch before building):

```
git clone --recursive https://github.com/microsoft/BitNet.git && cd BitNet   # head = 0b341e5
sed -i '133s/LLM_FFN_SILU/LLM_FFN_RELU_SQR/' 3rdparty/llama.cpp/src/models/bitnet.cpp   # A3 only
huggingface-cli download microsoft/bitnet-b1.58-2B-4T-gguf --local-dir models/BitNet-b1.58-2B-4T
python setup_env.py -md models/BitNet-b1.58-2B-4T -q i2_s
build/bin/llama-perplexity -m models/BitNet-b1.58-2B-4T/ggml-model-i2_s.gguf -f text.txt -c 256 --chunks 6 -t 4
# text.txt = head -c 9000 /usr/share/common-licenses/GPL-3
```

The primes answer (patched build; stock build loops on the same command):

```
build/bin/llama-completion -m models/BitNet-b1.58-2B-4T/ggml-model-i2_s.gguf -t 4 -n 192 \
  --temp 0 --special -r '<|eot_id|>' -no-cnv \
  -p 'User: Write a Python program that prints every prime below 30.<|eot_id|>Assistant: '
```

Era build (lane B; no requirements.txt — its sentencepiece pin is what killed Fable's
attempt; the era tree's own gguf-py goes in with `--no-deps`):

```
git clone <BitNet> BitNet-old && cd BitNet-old && git checkout c1e9a9a
# submodule: shallow-fetch 40ed0f290203a9a78540b8f7eb18bd828043fe21 from
# https://github.com/Eddie-Wang1120/llama.cpp.git into 3rdparty/llama.cpp
python -m pip install --no-deps ./3rdparty/llama.cpp/gguf-py
python utils/codegen_tl2.py --model bitnet_b1_58-3B --BM 160,320,320 --BK 96,96,96 --bm 32,32,32
cp <published gguf> models/BitNet-b1.58-2B-4T/
cmake -B build -DBITNET_X86_TL2=ON -DCMAKE_C_COMPILER=gcc -DCMAKE_CXX_COMPILER=g++
cmake --build build -j2 --target llama-cli llama-perplexity llama-quantize
```

Reference reading (lane C): `AutoModelForCausalLM` (transformers 5.22.2, torch 2.15.0+cpu)
on `microsoft/bitnet-b1.58-2B-4T-bf16` (safetensors sha256 `529637ff…d5ae1`), 256-token
windows over the same `text.txt`. Raw rows for every arm: `bitnet-runtime.json` beside
this page; full lane records in `~/workspace/bitnet-q3/` (laneA/laneB/laneC results + logs).
