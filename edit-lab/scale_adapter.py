#!/usr/bin/env python3
"""Build a strength-scaled copy of a PEFT LoRA adapter.

Multiplies every lora_B tensor by s (lora_A untouched), which scales the
LoRA delta dW = (alpha/r) * B @ A by exactly s. adapter_config.json and
any other files are copied unchanged.

Usage: scale_adapter.py <src_dir> <dst_dir> <s>
"""
import json
import shutil
import sys
from pathlib import Path

from safetensors.torch import load_file, save_file

src, dst, s = Path(sys.argv[1]), Path(sys.argv[2]), float(sys.argv[3])
dst.mkdir(parents=True, exist_ok=True)
for f in src.iterdir():
    if f.name != "adapter_model.safetensors":
        shutil.copy2(f, dst / f.name)
tensors = load_file(str(src / "adapter_model.safetensors"))
nb = 0
for k in list(tensors):
    if "lora_B" in k:
        tensors[k] = (tensors[k].float() * s).to(tensors[k].dtype)
        nb += 1
save_file(tensors, str(dst / "adapter_model.safetensors"), metadata={"format": "pt"})
print(f"{src} -> {dst}: scaled {nb} lora_B tensors by {s}")
