"""Architecture edit: a smaller base for cells, made by removing whole layers the probes show barely matter.

    python training/cells_cut.py 25,26,7,9,22,5,4,21
Saves cells/bases/smol135-cut<N>/ (HF format) and cells/gguf/cut<N>.gguf. Layers are chosen from the average
knockout effect over the probed skills (training/reports/cells/probe_*.json); cells then train on the cut base.
"""
import os
import subprocess
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from training import cells as C  # noqa: E402

drop = sorted(int(x) for x in sys.argv[1].split(","))
tok, model = C.load("smol135")
model = model.to(torch.bfloat16)
keep = [l for i, l in enumerate(model.model.layers) if i not in drop]
for j, l in enumerate(keep):
    l.self_attn.layer_idx = j
model.model.layers = torch.nn.ModuleList(keep)
model.config.num_hidden_layers = len(keep)
if getattr(model.config, "layer_types", None):
    model.config.layer_types = model.config.layer_types[:len(keep)]
name = f"cut{len(keep)}"
out = C.CELLS / "bases" / f"smol135-{name}"
model.save_pretrained(out)
tok.save_pretrained(out)
env = dict(os.environ, PYTHONPATH=f"{ROOT}/training/llama_cpp_convert/gguf-py:{ROOT}/training/llama_cpp_convert")
subprocess.run([sys.executable, str(ROOT / "training/llama_cpp_convert/convert_hf_to_gguf.py"), str(out),
                "--outfile", str(C.CELLS / "gguf" / f"{name}.gguf"), "--outtype", "q8_0"], check=True, env=env,
               capture_output=True)
print(f"{name}: kept {len(keep)} of {len(keep) + len(drop)} layers, dropped {drop}; "
      f"{sum(p.numel() for p in model.parameters()) / 1e6:.1f}M params")
