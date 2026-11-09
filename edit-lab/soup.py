"""Exact LoRA soup: merge two rank-16 adapters into one rank-32 adapter
whose delta is the weighted average of the two deltas.

For adapter i: dW_i = (alpha_i / r_i) * B_i @ A_i = 2 * B_i @ A_i.
Block construction: A' = [A_1 ; A_2] (stacked), B' = [c1*B_1 , c2*B_2]
(side by side) gives B' @ A' = c1*B_1@A_1 + c2*B_2@A_2. With output
config r=32, alpha=32 (scale 1), choosing c_i = 2*w_i yields
dW' = w_1*dW_1 + w_2*dW_2 exactly.
"""
import json, sys
from pathlib import Path
from safetensors.torch import load_file, save_file

w1 = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5
src1, src2, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[4])
w2 = 1.0 - w1

t1 = load_file(str(src1 / "adapter_model.safetensors"))
t2 = load_file(str(src2 / "adapter_model.safetensors"))
assert set(t1) == set(t2), "adapter tensor sets differ"

merged = {}
for k in t1:
    if ".lora_A." in k:
        import torch
        merged[k] = torch.cat([t1[k], t2[k]], dim=0)
    elif ".lora_B." in k:
        import torch
        merged[k] = torch.cat([2 * w1 * t1[k], 2 * w2 * t2[k]], dim=1)
    else:
        merged[k] = t1[k]

cfg = json.loads((src1 / "adapter_config.json").read_text())
cfg["r"] = 32
cfg["lora_alpha"] = 32
out.mkdir(parents=True, exist_ok=True)
save_file(merged, str(out / "adapter_model.safetensors"), metadata={"format": "pt"})
(out / "adapter_config.json").write_text(json.dumps(cfg, indent=2))
print(f"soup written to {out}: w1={w1} (from {src1.name}), w2={w2} (from {src2.name}); "
      f"{len(merged)} tensors, rank 32, alpha 32")
