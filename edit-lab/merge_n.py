"""Exact N-way LoRA merge (generalises soup.py).

Every input adapter i has delta dW_i = (alpha_i / r_i) * B_i @ A_i.
The merged adapter stacks A blocks and side-concatenates B blocks
scaled by c_i, with merged scale s' = alpha' / r':
    dW' = s' * sum_i c_i * B_i @ A_i.
Choosing s' = 2 (alpha' = 2 * r') and c_i = w_i * (alpha_i / r_i) / 2
gives dW' = sum_i w_i * dW_i exactly, for any per-adapter weights w_i.

Usage: merge_n.py OUT_DIR  DIR1:W1  DIR2:W2  [...]
All inputs must share the same tensor key set and target modules.
"""
import json, sys
from pathlib import Path
import torch
from safetensors.torch import load_file, save_file

out = Path(sys.argv[1])
specs = []
for arg in sys.argv[2:]:
    d, w = arg.rsplit(":", 1)
    specs.append((Path(d), float(w)))

tensors, cfgs = [], []
for d, w in specs:
    tensors.append(load_file(str(d / "adapter_model.safetensors")))
    cfgs.append(json.loads((d / "adapter_config.json").read_text()))

keys = set(tensors[0])
for t in tensors[1:]:
    assert set(t) == keys, "tensor key sets differ across adapters"

merged = {}
for k in keys:
    if ".lora_A." in k:
        merged[k] = torch.cat([t[k] for t in tensors], dim=0)
    elif ".lora_B." in k:
        blocks = []
        for t, cfg, (d, w) in zip(tensors, cfgs, specs):
            c = w * (cfg["lora_alpha"] / cfg["r"]) / 2.0
            blocks.append(c * t[k])
        merged[k] = torch.cat(blocks, dim=1)
    else:
        merged[k] = tensors[0][k]

r_total = sum(c["r"] for c in cfgs)
cfg = dict(cfgs[0])
cfg["r"] = r_total
cfg["lora_alpha"] = 2 * r_total
out.mkdir(parents=True, exist_ok=True)
save_file(merged, str(out / "adapter_model.safetensors"), metadata={"format": "pt"})
(out / "adapter_config.json").write_text(json.dumps(cfg, indent=2))
print(f"merged {len(specs)} adapters -> {out} (rank {r_total}, alpha {2 * r_total}); "
      f"weights: {[(str(d.name), w) for d, w in specs]}")
