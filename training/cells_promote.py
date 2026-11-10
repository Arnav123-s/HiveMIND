"""Gatekeeper: pick each skill's winning variant on the DEV split, convert it for llama.cpp, register the cell,
and re-measure it in the runtime that will actually serve it (test split).

    python training/cells_promote.py <skill> [...]
Winner = best dev score; ties go to the variant that changes fewer parameters. A variant must beat the untouched
base on dev to become a cell.
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from team.cells import runtime, skills as S  # noqa: E402
from training.cells import BASES, CELLS, data  # noqa: E402


def hf_dir(base):
    from huggingface_hub import snapshot_download
    if Path(BASES[base]).exists():
        return BASES[base]
    return snapshot_download(BASES[base], allow_patterns=["*.json", "*.safetensors", "*.txt"])


def variants(skill):
    out = {}
    for p in sorted((CELLS / "variants" / skill).glob("*/result.json")):
        out[p.parent.name] = json.loads(p.read_text())
    return out


def to_gguf(src, skill, base):
    env = dict(os.environ, PYTHONPATH=f"{ROOT}/training/llama_cpp_convert/gguf-py:{ROOT}/training/llama_cpp_convert")
    subprocess.run([sys.executable, str(ROOT / "training/llama_cpp_convert/convert_lora_to_gguf.py"), str(src),
                    "--base", hf_dir(base), "--outfile", str(CELLS / "gguf" / f"{skill}.gguf"), "--outtype", "f32"],
                   check=True, env=env, capture_output=True)


def runtime_eval(skill, rows):
    t0 = time.time()
    preds = [runtime.run(skill, x) for x, _ in rows]
    acc = sum(S.score(skill, p, y) for p, (_, y) in zip(preds, rows)) / len(rows)
    return acc, (time.time() - t0) / len(rows)


def vtype(tag):
    return "random" if tag.startswith("random") else tag


def prior(skill):
    """Mean test rank of each edit type on the OTHER skills (never this skill's own test): breaks dev ties."""
    ranks = {}
    for d in (CELLS / "variants").glob("*"):
        if d.name == skill:
            continue
        v = [r for k, r in variants(d.name).items() if k != "base"]
        for i, r in enumerate(sorted(v, key=lambda r: -r["test"])):
            ranks.setdefault(vtype(r["tag"]), []).append(i)
    return {k: sum(x) / len(x) for k, x in ranks.items()}


def dev_loss(skill, tag):
    from peft import PeftModel
    from training.cells import load, loss_on
    r = json.loads((CELLS / "variants" / skill / tag / "result.json").read_text())
    tok, model = load(r["base"])
    pm = PeftModel.from_pretrained(model, str(CELLS / "variants" / skill / tag))
    pm.eval()
    _, dv, _ = data(skill)
    return loss_on(pm, tok, skill, dv)


def promote(skill, measure=True, prefix=None):
    """prefix: only variants whose tag starts with it compete (the old ones were trained on data since withdrawn)."""
    v = variants(skill)
    if prefix:
        v = {k: r for k, r in v.items() if k == "base" or k.startswith(prefix)}
    base = v.get("base", {}).get("dev", 0.0)
    cands = [r for k, r in v.items() if k != "base" and vtype(k) != "random" and r["dev"] > base]
    if not cands:
        print(f"{skill}: no variant beats the base on dev ({base:.3f}); not promoted")
        return None
    # dev accuracy decides; within 2 dev points (small dev sets) the lower dev log-loss wins, then fewer edits
    best = max(r["dev"] for r in cands)
    tied = [r for r in cands if r["dev"] >= best - 0.02]
    for r in tied:
        r.setdefault("dev_loss", dev_loss(skill, r["tag"]))
    pr = {r["tag"]: round(r["dev_loss"], 4) for r in tied}
    win = min(tied, key=lambda r: (r["dev_loss"], r["trainable_params"]))
    src = CELLS / "variants" / skill / win["tag"]
    dst = CELLS / "adapters" / skill
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    to_gguf(dst, skill, win["base"])
    entry = {"skill": skill, "part": S.SKILLS[skill]["part"], "base": win["base"], "variant": win["tag"],
             "modules": win["modules"], "rank": win["rank"], "thin": win.get("thin"), "trainable_params": win["trainable_params"],
             "parent": win.get("parent"), "dev": win["dev"], "test_torch": win["test"],
             "variants": {k: {"dev": r["dev"], "test": r["test"], "params": r["trainable_params"]} for k, r in v.items()},
             "promoted": time.strftime("%Y-%m-%d %H:%M")}
    runtime.update_registry(skill, entry, replace=True)
    print(f"{skill}: {win['tag']} dev {win['dev']:.3f} test(torch) {win['test']:.3f}, "
          f"{win['trainable_params']:,} params changed (tied on dev, dev loss: {pr})", flush=True)
    if measure:
        retime(skill)
    return entry


def retime(skill):
    """The cell as served: llama.cpp accuracy and latency on the test split. Run on a quiet CPU."""
    _, _, te = data(skill)
    runtime.unload()
    acc, sec = runtime_eval(skill, te)
    entry = runtime.update_registry(skill, {"test_runtime": round(acc, 4), "ms_per_call": round(sec * 1000, 1),
                                            "gguf_bytes": (CELLS / "gguf" / f"{skill}.gguf").stat().st_size})
    print(f"{skill}: llama.cpp test {acc:.3f}, {sec * 1000:.0f} ms/call")
    return entry


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--retime" in sys.argv:
        for s in args or list(runtime.registry()):
            retime(s)
    else:
        for s in args:
            promote(s, measure="--no-runtime" not in sys.argv)
