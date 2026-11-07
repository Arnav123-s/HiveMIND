#!/usr/bin/env bash
# Edit every specialist's weights, then report what changed.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
# coordinator already trained
$PY training/train_lora.py browser     --epochs 2 --layers 14-27 --rank 16 --max-len 2048
$PY training/train_lora.py researcher  --epochs 2 --layers 14-27 --rank 16 --max-len 2048
$PY training/train_lora.py verifier    --epochs 1 --layers 14-27 --rank 8
$PY training/train_lora.py writer      --epochs 3 --layers 14-27 --rank 8
$PY training/inspect_weights.py coordinator browser researcher verifier writer
