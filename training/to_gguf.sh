#!/usr/bin/env bash
# Convert a specialist's PEFT weight edit (adapters/<name>) into a GGUF LoRA for the llama.cpp engine.
set -euo pipefail
cd "$(dirname "$0")/.."
BASE=$(.venv/bin/python -c "from huggingface_hub import snapshot_download as s; print(s('Qwen/Qwen3-1.7B', allow_patterns=['*.json','*.safetensors','*.txt']))")
mkdir -p adapters_gguf
for s in "$@"; do
  PYTHONPATH=training/llama_cpp_convert/gguf-py:training/llama_cpp_convert .venv/bin/python training/llama_cpp_convert/convert_lora_to_gguf.py \
    "adapters/$s" --base "$BASE" --outfile "adapters_gguf/$s.gguf" --outtype f16
done
