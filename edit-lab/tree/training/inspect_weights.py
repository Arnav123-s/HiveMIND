"""Show exactly which weight matrices a specialist's training changed, and by how much.

For every adapted matrix W, the edit is dW = (alpha/r) * B @ A. Reports
||dW|| / ||W|| per layer and module, the top changed tensors, and the
effective rank of each edit.

    python training/inspect_weights.py coordinator
"""
import json
import sys
from pathlib import Path

import torch
from safetensors import safe_open
from safetensors.torch import load_file

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from team import config  # noqa: E402


from functools import lru_cache


@lru_cache(maxsize=None)
def _snapshot(model_id):
    from huggingface_hub import snapshot_download
    return Path(snapshot_download(model_id, allow_patterns=["*.safetensors", "*.json"], local_files_only=True))


def base_tensor(model_id, name):
    path = _snapshot(model_id)
    idx = path / "model.safetensors.index.json"
    shard = json.loads(idx.read_text())["weight_map"][name] if idx.exists() else "model.safetensors"
    with safe_open(str(path / shard), "pt") as f:
        return f.get_tensor(name).float()


def inspect(spec):
    adir = config.ADAPTERS / spec
    cfg = json.loads((adir / "adapter_config.json").read_text())
    scale = cfg["lora_alpha"] / cfg["r"]
    sd = load_file(str(adir / "adapter_model.safetensors"))
    rows = []
    for k in sorted(sd):
        if "lora_A" not in k:
            continue
        A = sd[k].float()
        B = sd[k.replace("lora_A", "lora_B")].float()
        # dW = scale * B @ A has rank <= r: its singular values are those of a small r x r core
        _, rb = torch.linalg.qr(B)
        _, ra = torch.linalg.qr(A.T)
        s = torch.linalg.svdvals(scale * rb @ ra.T)
        name = k.replace("base_model.model.", "").replace(".lora_A.weight", ".weight")
        W = base_tensor(cfg["base_model_name_or_path"], name)
        eff_rank = int((s > s[0] * 0.01).sum()) if s[0] > 0 else 0
        rows.append({"tensor": name, "layer": int(name.split(".layers.")[1].split(".")[0]),
                     "module": name.split(".")[-2], "rel_change": float(s.norm() / W.norm()),
                     "abs_change": float(s.norm()), "eff_rank": eff_rank})
    rows.sort(key=lambda r: -r["rel_change"])
    by_layer, by_module = {}, {}
    for r in rows:
        by_layer.setdefault(r["layer"], []).append(r["rel_change"])
        by_module.setdefault(r["module"], []).append(r["rel_change"])
    n_params = sum(v.numel() for v in sd.values())
    lines = [f"# Weight edit report: {spec}", "",
             f"Base model: `{cfg['base_model_name_or_path']}`  ",
             f"Edited: {len(rows)} matrices in layers {min(by_layer)}-{max(by_layer)} "
             f"({', '.join(sorted(by_module))}); rank {cfg['r']}, alpha {cfg['lora_alpha']}; "
             f"{n_params:,} trained numbers.", "",
             "## Mean relative change ||dW||/||W|| by layer", "", "| layer | mean | max |", "|---|---|---|"]
    for layer in sorted(by_layer):
        v = by_layer[layer]
        lines.append(f"| {layer} | {sum(v) / len(v):.4%} | {max(v):.4%} |")
    lines += ["", "## By module", "", "| module | mean | max |", "|---|---|---|"]
    for m in sorted(by_module):
        v = by_module[m]
        lines.append(f"| {m} | {sum(v) / len(v):.4%} | {max(v):.4%} |")
    lines += ["", "## 10 most-changed matrices", "", "| tensor | rel change | effective rank |", "|---|---|---|"]
    for r in rows[:10]:
        lines.append(f"| `{r['tensor']}` | {r['rel_change']:.4%} | {r['eff_rank']} |")
    out = ROOT / "training" / "reports" / f"weights_{spec}.md"
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:12]))
    return rows


if __name__ == "__main__":
    for s in sys.argv[1:]:
        inspect(s)
