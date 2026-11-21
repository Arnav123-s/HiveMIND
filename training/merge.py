"""The trunk: what the whole body has learned, as one weight edit.

Every cell is the DNA with a low-rank edit, B·A on each projection it trains. Cells that descend from one start and
learn from the same checked work stay near each other, and the average of such edits is as good as its members or
better, and holds up better on work none of them practised (model soups, Wortsman et al. 2022; averaging is also
how many learners trained apart are made one model, McMahan et al. 2017). So each generation the body's newest
cells are averaged into one edit, the trunk. The trunk answers first on every task, and every child starts as its
parent pulled halfway toward it (elastic averaging, Zhang et al. 2015): the lines of descent go on exploring, and
the body stays one. Nothing is counted to make it: every cell weighs the same.

The average of n edits of rank r has rank up to n·r. It is cut back exactly to the best edit of a given rank: the
A factors are stacked and the B factors set side by side, each is reduced by QR, and the small core between them is
split by SVD. No matrix of the DNA's size is ever built (an 8B DNA has projections of 4096 by 12288).

    python3 training/merge.py trunk OUT_FOLDER EDIT.safetensors ... [--rank 32] [--weights 1,1,2]
    python3 training/merge.py mix OUT.safetensors PARENT.safetensors TRUNK.safetensors [--pull 0.5] [--rank 16]
    python3 training/merge.py join OUT_FOLDER SLICE.safetensors ... --base t80 --name g29code [--out-dir DIR]
                         one child grown on several runners at once, each on a slice of the rows: the slices'
                         edits averaged into the child, cut to its rank (16), with a record joined from theirs

Needs numpy and safetensors only.
"""
import json
import sys
from pathlib import Path

import numpy as np

A_KEY, B_KEY = ".lora_A.weight", ".lora_B.weight"


def load(path):
    """{module: (A, B)} of one edit (PEFT's layout: base_model.model.<module>.lora_A.weight, ...lora_B.weight)."""
    from safetensors.numpy import load_file
    sd = load_file(str(path))
    out = {}
    for k, a in sd.items():
        if k.endswith(A_KEY) and k[:-len(A_KEY)] + B_KEY in sd:
            out[k[:-len(A_KEY)]] = (a.astype(np.float32), sd[k[:-len(A_KEY)] + B_KEY].astype(np.float32))
    return out


def save(edit, path):
    from safetensors.numpy import save_file
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    save_file({k + s: np.ascontiguousarray(v, dtype=np.float32) for k, (a, b) in edit.items() for s, v in ((A_KEY, a), (B_KEY, b))}, str(path))


def _cut(a_stack, b_side, rank):
    """The best (A, B) of the given rank for the product b_side @ a_stack, and the share of its energy that is kept."""
    qb, rb = np.linalg.qr(b_side.astype(np.float64))        # b_side = qb rb
    qa, ra = np.linalg.qr(a_stack.astype(np.float64).T)     # a_stack = ra' qa'
    u, s, vt = np.linalg.svd(rb @ ra.T, full_matrices=False)
    r = min(rank, len(s))
    root = np.sqrt(s[:r])
    total = float((s ** 2).sum())
    kept = float((s[:r] ** 2).sum()) / total if total > 0 else 1.0
    return (root[:, None] * (vt[:r] @ qa.T)).astype(np.float32), ((qb @ u[:, :r]) * root[None, :]).astype(np.float32), kept


def merge(edits, weights=None, rank=16, normalize=True):
    """The weighted average of several edits, cut back to `rank`: ({module: (A, B)}, the least share of energy any
    module kept). A module that only some edits train is averaged over all of them (the others add nothing there).
    normalize=False: the weighted sum, the weights as given (training/hive_engram.py adds its engram to the trunk)."""
    if not edits:
        raise ValueError("nothing to merge")
    w = np.array(weights if weights is not None else [1.0] * len(edits), dtype=np.float64)
    if len(w) != len(edits) or w.sum() <= 0:
        raise ValueError("one weight for each edit, not all zero")
    if normalize:
        w = w / w.sum()
    out, least = {}, 1.0
    for name in sorted({k for e in edits for k in e}):
        have = [(wi, e[name]) for wi, e in zip(w, edits) if name in e]
        a_stack = np.concatenate([a for _, (a, _) in have], axis=0)
        b_side = np.concatenate([wi * b for wi, (_, b) in have], axis=1)
        a, b, kept = _cut(a_stack, b_side, rank)
        if a.shape[0] < rank:  # fewer directions than the rank asked for: the rest are empty
            a = np.concatenate([a, np.zeros((rank - a.shape[0], a.shape[1]), np.float32)], axis=0)
            b = np.concatenate([b, np.zeros((b.shape[0], rank - b.shape[1]), np.float32)], axis=1)
        out[name], least = (a, b), min(least, kept)
    return out, least


def write(edit, folder, base_name, rank, layers=None):
    """The edit as a folder PEFT and the runtime's converter read (adapter_config.json, adapter_model.safetensors).
    lora_alpha is twice the rank, as every cell is trained, so the edit weighs the same at any rank."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    save(edit, folder / "adapter_model.safetensors")
    targets = sorted({k.rsplit(".", 1)[-1] for k in edit})
    if layers is None:
        layers = sorted({int(p) for k in edit for p in [k.split(".layers.")[-1].split(".")[0]] if ".layers." in k and p.isdigit()})
    (folder / "adapter_config.json").write_text(json.dumps({
        "peft_type": "LORA", "task_type": "CAUSAL_LM", "base_model_name_or_path": str(base_name), "r": rank, "lora_alpha": 2 * rank,
        "lora_dropout": 0.0, "target_modules": targets, "layers_to_transform": layers, "bias": "none", "fan_in_fan_out": False,
        "inference_mode": True, "modules_to_save": None, "use_rslora": False, "use_dora": False}, indent=1))
    return folder


def gguf(folder, base, name, out_dir=None):
    """The edit as the file the ternary runtime loads (cells/members/<dna>+<name>.gguf). Only the DNA's config is
    needed for it, not its weights."""
    import subprocess
    from huggingface_hub import snapshot_download

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from team import ternary
    from training.grow import UNPACKED
    src = snapshot_download(UNPACKED[base], allow_patterns=["config.json", "tokenizer*", "*.txt", "vocab.json", "added_tokens.json", "special_tokens_map.json",
                                                            "generation_config.json", "chat_template.jinja"])
    where = Path(out_dir or ternary.ADAPTERS)
    where.mkdir(parents=True, exist_ok=True)
    out = where / f"{base}+{name}.gguf"
    done = subprocess.run([sys.executable, str(ternary.source() / "convert_lora_to_gguf.py"), "--base", src, "--outfile", str(out), "--outtype", "f16", str(folder)],
                          capture_output=True, text=True)
    if done.returncode:
        raise RuntimeError("the edit could not be written as a GGUF adapter: " + done.stderr[-800:])
    return out


def slice_observations(metas):
    """Separate per-run experimental measurements from the legacy first-slice summary."""
    fields = ("plateau", "loss_chunk_tokens", "self_replay")
    memory_fields = ("row_modes", "mode_changes", "checkpoint_cost_per_piece_mb",
                     "checkpoint_formula_per_piece_mb", "training_max_len", "evaluation_max_len")
    observations = []
    for position, item in enumerate(metas):
        values = {k: item[k] for k in fields if k in item}
        memory = {k: item["memory"][k] for k in memory_fields if k in item.get("memory", {})}
        if memory:
            values["memory"] = memory
        if values:
            observations.append({"shard": item.get("shard") or f"input-{position + 1}", **values})
    meta = dict(metas[0]) if metas else {}
    for k in fields:
        meta.pop(k, None)
    if "memory" in meta:
        meta["memory"] = {k: v for k, v in meta["memory"].items() if k not in memory_fields}
    if observations:
        meta["slice_observations"] = observations
    return meta


def main(argv):
    opt = lambda k, d: type(d)(argv[argv.index(k) + 1]) if k in argv else d  # noqa: E731
    flags = {"--rank", "--weights", "--pull", "--base", "--name", "--out-dir"}
    files = [a for i, a in enumerate(argv[1:], 1) if not a.startswith("--") and argv[i - 1] not in flags]
    if argv[:1] == ["trunk"] and len(files) >= 2:
        folder, paths = files[0], files[1:]
        rank = opt("--rank", 32)
        weights = [float(x) for x in opt("--weights", "").split(",") if x] or None
        edit, least = merge([load(p) for p in paths], weights, rank)
        base, name = opt("--base", ""), opt("--name", "")
        from training.grow import UNPACKED
        write(edit, folder, UNPACKED.get(base, base), rank)
        meta = {"trunk_of": [Path(p).name for p in paths], "rank": rank, "modules": len(edit), "least_energy_kept": round(least, 4)}
        if base and name:
            out = gguf(folder, base, name, opt("--out-dir", "") or None)
            meta |= {"member": f"{base}+{name}", "file": str(out), "megabytes": round(out.stat().st_size / 2**20, 1)}
            out.with_suffix(".json").write_text(json.dumps(meta, indent=1))
        print(json.dumps(meta))
        return 0
    if argv[:1] == ["join"] and len(files) >= 2:
        folder, paths = files[0], files[1:]
        # Legacy slices used the hash assignment; a freshly balanced slice covers different rows.
        # Validate the records before loading weights or writing a partially joined child.
        metas, policies = [], set()
        for path in paths:
            record = Path(path).with_suffix(".json")
            if record.exists():
                m = json.loads(record.read_text())
                metas.append(m)
                policies.add(m.get("shard_policy", "hash"))
            else:
                policies.add("hash")
        if len(policies) != 1 or not policies <= {"cost", "hash"}:
            raise ValueError(f"Cannot join training slices with incompatible shard policies: {policies}")
        rank = opt("--rank", 16)
        edit, least = merge([load(p) for p in paths], None, rank)
        base, name = opt("--base", ""), opt("--name", "")
        from training.grow import UNPACKED
        write(edit, folder, UNPACKED.get(base, base), rank)
        meta = slice_observations(metas)
        meta |= {"slices": len(paths), "shard_policy": policies.pop(), "least_energy_kept": round(least, 4), "shard": "",
                 "steps": sum(m.get("steps") or 0 for m in metas), "used": sum(m.get("used") or 0 for m in metas),
                 "rows": sum(m.get("rows") or 0 for m in metas), "read": sum(m.get("read") or 0 for m in metas),
                 "judged": sum(m.get("judged") or 0 for m in metas), "seconds": max([m.get("seconds") or 0 for m in metas] or [0])}
        if base and name:
            out = gguf(folder, base, name, opt("--out-dir", "") or None)
            meta |= {"member": f"{base}+{name}", "file": str(out), "megabytes": round(out.stat().st_size / 2**20, 1)}
            out.with_suffix(".json").write_text(json.dumps(meta, indent=1))
        print(json.dumps({k: meta.get(k) for k in ("member", "slices", "steps", "used", "rows", "least_energy_kept")}))
        return 0
    if argv[:1] == ["mix"] and len(files) == 3:
        out, parent, trunk = files
        pull, rank = opt("--pull", 0.5), opt("--rank", 16)
        edit, least = merge([load(parent), load(trunk)], [1 - pull, pull], rank)
        save(edit, out)
        print(json.dumps({"mix": out, "pull": pull, "rank": rank, "least_energy_kept": round(least, 4)}))
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    sys.exit(main(sys.argv[1:]))
