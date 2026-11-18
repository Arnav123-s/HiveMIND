"""Distil verified hive actions into a CPU LoRA child of the data cell."""
import argparse
import hashlib
import json
import math
import random
import resource
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from training.experiments import rule_lab as lab


def teaching_rows(sources, recipe=None):
    """Keep successful actions and their public context. The learner sees no exam worlds."""
    rows = {}
    origins = []
    for path in sources:
        state = json.loads(path.read_text())
        if state["family"] != "affine" or not 10 <= state["seed"] <= 15:
            raise ValueError(f"unexpected teaching world: {path}")
        if not state.get("score", {}).get("correct"):
            continue
        origins.append(path.name)
        prefix = {"turns": [], "observations": []}
        for t in state["turns"]:
            prompt = lab.messages("affine", "open", prefix)
            if "observed" in t or ("submit" in t and not t.get("error")):
                # Train the new cell to take either role. Keep the measured action;
                # discard optional prose so the target is just the successful tool use.
                target = ({"measure": t["measure"], "next": t.get("next", "self")} if "observed" in t
                          else {"submit": t["submit"]})
                rows.setdefault(json.dumps(prompt), (prompt, target))
            prefix["turns"].append(t)
            prefix["observations"].extend(t.get("observed", []))
    if recipe:
        from training.experiments.rule_lab_recipe import execute
        # Add demonstrations by the hive's own executable method only when all its
        # predictions match the teaching world's existing, public instrument readings.
        for path in sources:
            state = json.loads(path.read_text())
            table = {(x, y): z for x, y, z in state["observations"]}
            guess = execute(recipe, lambda x, y: table[x, y])
            if any(lab.instrument(guess, x, y) != z for (x, y), z in table.items()):
                raise ValueError("recipe failed a public teaching receipt")
            points = recipe["points"]
            blank = lab.messages("affine", "open", {"observations": [], "turns": []})
            # Train this procedure as one worker. For a shared prompt, prefer the
            # verified portable expression over the original example's numeric answer.
            rows[json.dumps(blank)] = (blank, {"measure": points, "next": "self"})
            seen = [[x, y, table[x, y]] for x, y in points]
            observed = {"observations": seen, "turns": [{"measure": points}]}
            prompt = lab.messages("affine", "open", observed)
            rows[json.dumps(prompt)] = (prompt, {"submit": recipe["expressions"]})
    if not rows:
        raise ValueError("no checked demonstrations")
    return [{"messages": p, "output": json.dumps(t, separators=(",", ":"))} for p, t in rows.values()], origins


def train(args):
    import torch
    from safetensors.torch import load_file
    from transformers import AutoTokenizer
    from training import grow, ternary_base

    start = time.monotonic()
    torch.set_num_threads(args.threads)
    torch.manual_seed(17)
    rng = random.Random(17)
    paths = sorted(args.source.glob("affine-*-guided.json"))
    recipe = json.loads(args.recipe.read_text())["recipe"] if args.recipe else None
    rows, origins = teaching_rows(paths, recipe)
    args.out.mkdir(parents=True, exist_ok=True)
    lab.save(args.out / "rows.json", rows)
    src = str(args.unpacked.resolve())
    tok = AutoTokenizer.from_pretrained(src, local_files_only=True)
    data = []
    for row in rows:
        text = tok.apply_chat_template(row["messages"], tokenize=False, add_generation_prompt=True, enable_thinking=False)
        prompt = tok(text, add_special_tokens=False)["input_ids"]
        target = tok(row["output"] + "<|im_end|>\n", add_special_tokens=False)["input_ids"]
        data.append((torch.tensor([prompt + target], dtype=torch.long), len(target)))
    parent = load_file(str(args.parent))
    depth = sorted({int(n.split(".layers.")[1].split(".")[0]) for n in parent})
    rank = next(v.shape[0] for n, v in parent.items() if ".lora_A." in n)
    model, cell = ternary_base.load(src, rank=rank, alpha=2 * rank, dropout=0.0, layers=depth)
    model.config.use_cache = False
    names = set()
    updating = []
    for name, layer in cell.layers.items():
        block = int(name.split(".layers.")[1].split(".")[0])
        for part in ("lora_A", "lora_B"):
            key = f"base_model.model.{name}.{part}.weight"
            param = getattr(layer, part)
            with torch.no_grad():
                param.copy_(parent[key])
            names.add(key)
            param.requires_grad_(block in depth[-2:])
            if param.requires_grad:
                updating.append((key, param))
    if names != set(parent):
        raise ValueError("incomplete inheritance")
    model.eval()
    optimizer = torch.optim.AdamW([p for _, p in updating], lr=args.lr, weight_decay=0)
    losses = []
    with tempfile.TemporaryDirectory(dir=args.out) as cache:
        prefix = grow._Prefix(model, depth[-2], folder=Path(cache) / "activations")
        for epoch in range(args.epochs):
            order = list(range(len(data)))
            rng.shuffle(order)
            epoch_losses = []
            for i in order:
                ids, k = data[i]
                optimizer.zero_grad(set_to_none=True)
                with torch.autocast("cpu", dtype=torch.bfloat16), prefix.use(ids):
                    logits = model(input_ids=ids, logits_to_keep=k + 1).logits[:, :-1, :]
                loss = torch.nn.functional.cross_entropy(logits.float().reshape(-1, logits.size(-1)), ids[:, -k:].reshape(-1))
                if not torch.isfinite(loss):
                    raise ValueError("non-finite training loss")
                loss.backward()
                torch.nn.utils.clip_grad_norm_([p for _, p in updating], 1.0, error_if_nonfinite=True)
                optimizer.step()
                epoch_losses.append(loss.item())
            losses.append(sum(epoch_losses) / len(epoch_losses))
            print(f"epoch {epoch + 1}, mean training loss {losses[-1]:.4f}", flush=True)
        prefix.done()
    delta = math.sqrt(sum((p.detach().float() - parent[n]).square().sum().item() for n, p in updating))
    if not math.isfinite(delta) or delta <= 0:
        raise ValueError("child weights did not change")
    adapter = args.out / "adapter"
    cell.save(adapter, src)
    with args.parent.open("rb") as f:
        parent_digest = hashlib.file_digest(f, "sha256").hexdigest()
    lab.save(args.out / "training.json", {
        "parent_sha256": parent_digest,
        "inherited_tensors": len(parent), "updated_tensors": len(updating),
        "trainable_parameters": sum(p.numel() for _, p in updating), "trained_blocks": depth[-2:],
        "delta_l2": delta, "mean_training_loss_by_epoch": losses, "demonstrations": origins,
        "procedure_from_teaching_worlds": bool(recipe), "rows": len(rows), "epochs": args.epochs,
        "lr": args.lr, "threads": args.threads, "seconds": time.monotonic() - start,
        "peak_trainer_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "unpacked", "parent", "out", "converter", "deploy"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--recipe", type=Path)
    p.add_argument("--epochs", type=int, default=3)
    p.add_argument("--threads", type=int, default=4)
    p.add_argument("--lr", type=float, default=0.00015)
    args = p.parse_args()
    train(args)
    args.deploy.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, str(args.converter.resolve()), "--base", str(args.unpacked.resolve()),
                    "--outfile", str(args.deploy.resolve()), "--outtype", "f16", str((args.out / "adapter").resolve())],
                   check=True)


if __name__ == "__main__":
    main()
