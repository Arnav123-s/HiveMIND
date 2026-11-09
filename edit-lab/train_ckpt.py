"""Edit one specialist's weights on CPU.

Trains a low-rank weight delta (LoRA) restricted to chosen layers and
projection matrices, so only those tensors change: W' = W + (alpha/r) * B @ A.
Loss is taken on the specialist's reply tokens only.

    python training/train_lora.py coordinator --layers 14-27 --rank 16 --epochs 3
"""
import argparse
import json
import math
import random
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional  # noqa: F401
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT = Path(__file__).resolve().parent.parent
# edit-lab: this copy lives outside the repo tree; the team package is
# in the copied tree, so point imports (and any ROOT-relative reads)
# there explicitly.
ROOT = Path.home() / "workspace/edit-lab/tree"
sys.path.insert(0, str(ROOT))
from team import config  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("specialist")
ap.add_argument("--data", nargs="*", help="jsonl files (default training/data/<specialist>*.jsonl + self/)")
ap.add_argument("--layers", default="auto", help="e.g. 14-27; auto = top half")
ap.add_argument("--modules", default="q_proj,k_proj,v_proj,o_proj,gate_proj,up_proj,down_proj")
ap.add_argument("--rank", type=int, default=16)
ap.add_argument("--alpha", type=int, default=32)
ap.add_argument("--epochs", type=float, default=2)
ap.add_argument("--lr", type=float, default=2e-4)
ap.add_argument("--accum", type=int, default=4)
ap.add_argument("--max-len", type=int, default=2048)
ap.add_argument("--out", help="output dir (default adapters/<specialist>)")
ap.add_argument("--threads", type=int, default=config.THREADS)
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--save-every", type=int, default=0,
                help="edit-lab addition: checkpoint every N optimizer steps (0=off)")
ap.add_argument("--ckpt", help="edit-lab addition: checkpoint dir (default <out>.ckpt)")
ap.add_argument("--resume", action="store_true",
                help="edit-lab addition: resume from --ckpt checkpoint")
args = ap.parse_args()

torch.set_num_threads(args.threads)
try:  # give freed memory back to the OS between steps (variable-length batches fragment the heap)
    import ctypes
    _trim = ctypes.CDLL("libc.so.6").malloc_trim
except OSError:
    _trim = None
random.seed(args.seed)
torch.manual_seed(args.seed)

model_id = config.SPECIALISTS[args.specialist]
out_dir = Path(args.out or config.ADAPTERS / args.specialist)
files = args.data or sorted(str(p) for p in (ROOT / "training" / "data").glob(f"{args.specialist}*.jsonl"))
files += sorted(str(p) for p in (ROOT / "training" / "data" / "self").glob(f"{args.specialist}*.jsonl")) if not args.data else []
rows = [json.loads(line) for f in files for line in open(f) if line.strip()]
print(f"{args.specialist}: {len(rows)} examples from {files}", flush=True)

tok = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(model_id, dtype=torch.bfloat16)
n_layers = model.config.num_hidden_layers
if args.layers == "auto":
    layers = list(range(n_layers // 2, n_layers))
else:
    a, b = (int(x) for x in args.layers.split("-"))
    layers = list(range(a, b + 1))

lcfg = LoraConfig(r=args.rank, lora_alpha=args.alpha, lora_dropout=0.05, target_modules=args.modules.split(","),
                  layers_to_transform=layers, task_type="CAUSAL_LM")
# edit-lab: checkpoint/resume support (recipe otherwise identical to
# training/train_lora.py). --resume loads the checkpoint adapter as a
# trainable PEFT model and restores optimizer/scheduler/loop state.
ckpt_dir = Path(args.ckpt) if args.ckpt else None
resume_state = None
if args.resume and ckpt_dir is not None and (ckpt_dir / "state.json").exists():
    from peft import PeftModel
    model = PeftModel.from_pretrained(model, str(ckpt_dir), is_trainable=True)
    resume_state = json.loads((ckpt_dir / "state.json").read_text())
    print(f"resuming from checkpoint at step {resume_state['step']}", flush=True)
else:
    model = get_peft_model(model, lcfg)
model.print_trainable_parameters()
model.config.use_cache = False


def encode(row):
    msgs = row["messages"]
    prompt = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    target = row["output"] + "<|im_end|>\n"
    p_ids = tok(prompt, add_special_tokens=False)["input_ids"]
    t_ids = tok(target, add_special_tokens=False)["input_ids"]
    if len(p_ids) + len(t_ids) > args.max_len:
        return None  # never cut the system prompt off; skip instead
    return torch.tensor([p_ids + t_ids]), len(t_ids)


data = [d for d in (encode(r) for r in rows) if d is not None]
print(f"skipped {len(rows) - len(data)} examples longer than {args.max_len} tokens", flush=True)
print("tokens per example: mean", sum(d[0].shape[1] for d in data) // max(1, len(data)),
      "max", max(d[0].shape[1] for d in data), flush=True)

params = [p for p in model.parameters() if p.requires_grad]
opt = torch.optim.AdamW(params, lr=args.lr, weight_decay=0.0)
total_steps = math.ceil(len(data) * args.epochs / args.accum)
sched = torch.optim.lr_scheduler.LambdaLR(
    opt, lambda s: min(1.0, (s + 1) / max(1, total_steps // 10)) * max(0.05, 1 - s / max(1, total_steps)))
if resume_state is not None:
    opt.load_state_dict(torch.load(ckpt_dir / "opt.pt"))
    sched.load_state_dict(torch.load(ckpt_dir / "sched.pt"))

model.train()
log, t0, step, seen = [], time.time(), 0, 0
order = []
while len(order) < len(data) * args.epochs:
    perm = list(range(len(data)))
    random.shuffle(perm)
    order += perm
order = order[:int(len(data) * args.epochs)]
running = 0.0
start_pos = 0
if resume_state is not None:
    step, seen = resume_state["step"], resume_state["seen"]
    log = resume_state["log"]
    start_pos = resume_state["pos"] + 1
    t0 = time.time() - resume_state.get("elapsed", 0)
    print(f"continuing at order position {start_pos}/{len(order)}", flush=True)
for i, idx in enumerate(order):
    if i < start_pos:
        continue
    ids, k = data[idx]
    _tex = time.time()
    with torch.autocast("cpu", dtype=torch.bfloat16):
        # Only score the reply: vocab logits for k+1 positions instead of the whole sequence
        # (the full 151k-vocab logits for 2k tokens is what ran out of RAM).
        logits = model(input_ids=ids, logits_to_keep=k + 1).logits[:, :-1, :]
    loss = torch.nn.functional.cross_entropy(logits.float().reshape(-1, logits.size(-1)), ids[:, -k:].reshape(-1))
    (loss / args.accum).backward()
    print(f"ex {i} idx {idx} len {ids.shape[1]} k {k} loss {loss.item():.4f} {time.time() - _tex:.1f}s", flush=True)
    running += loss.item()
    seen += 1
    if seen % args.accum == 0 or i == len(order) - 1:
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        opt.step()
        sched.step()
        opt.zero_grad()
        if _trim:
            _trim(0)
        step += 1
        avg = running / args.accum
        running = 0.0
        log.append({"step": step, "loss": round(avg, 4), "sec": round(time.time() - t0)})
        if step % 5 == 0 or step == total_steps:
            print(f"step {step}/{total_steps} loss {avg:.4f} {time.time() - t0:.0f}s", flush=True)
        if args.save_every and ckpt_dir is not None and step % args.save_every == 0 and i != len(order) - 1:
            ckpt_dir.mkdir(parents=True, exist_ok=True)
            model.save_pretrained(str(ckpt_dir))
            torch.save(opt.state_dict(), ckpt_dir / "opt.pt")
            torch.save(sched.state_dict(), ckpt_dir / "sched.pt")
            (ckpt_dir / "state.json").write_text(json.dumps(
                {"step": step, "seen": seen, "pos": i, "log": log,
                 "elapsed": round(time.time() - t0)}))
            print(f"checkpoint saved at step {step}", flush=True)

out_dir.mkdir(parents=True, exist_ok=True)
model.save_pretrained(str(out_dir))
meta = {"specialist": args.specialist, "base": model_id, "examples": len(rows), "files": files,
        "layers": layers, "modules": args.modules.split(","), "rank": args.rank, "alpha": args.alpha,
        "epochs": args.epochs, "lr": args.lr, "steps": step, "seconds": round(time.time() - t0),
        "loss_first": log[0]["loss"] if log else None, "loss_last": log[-1]["loss"] if log else None,
        "time": time.strftime("%F %T")}
(out_dir / "training_meta.json").write_text(json.dumps({**meta, "log": log}, indent=1))
print(json.dumps(meta, indent=1))
