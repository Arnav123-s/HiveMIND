"""Make, inspect and edit cells: the hive's smallest single-skill specialists.

    python training/cells.py probe <skill>                 # which parts of the base carry the skill (maps)
    python training/cells.py train <skill> --pick L:M,...  # edit only the modules the locator picked
    python training/cells.py train <skill> --auto 16       # control: top-16 modules by |W*grad|
    python training/cells.py train <skill> --random 16     # control: 16 random modules
    python training/cells.py train <skill> --all           # control: every module
    python training/cells.py clone <new_skill>             # factory: clone the nearest cell, edit the clone
    python training/cells.py eval-base <skill>

A cell = a frozen tiny base (shared by every cell) + a low-rank weight delta on a few chosen modules:
W' = W + (alpha/r) * B @ A, only where the locator put it. Variants are chosen on the dev split; the test split
(different words, frames and sites) is only reported.
"""
import argparse
import json
import random
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional as F

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from team.cells import skills as S  # noqa: E402

BASES = {"smol135": "HuggingFaceTB/SmolLM2-135M-Instruct", "smol360": "HuggingFaceTB/SmolLM2-360M-Instruct",
         "qwen05": "Qwen/Qwen2.5-0.5B-Instruct",
         # made here: SmolLM2-135M with the 8 layers the probes show matter least removed (training/cells_cut.py)
         "cut22": str(Path(__file__).resolve().parent.parent / "cells" / "bases" / "smol135-cut22")}
MODS = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
CELLS = ROOT / "cells"
REPORTS = ROOT / "training" / "reports" / "cells"
N = {"train": 600, "dev": 80, "test": 150}
# this CPU has AMX: bf16 matmuls are 5x faster than fp32 (1.8 vs 8.7 ms); edits stay fp32 (PEFT autocast)
DTYPE = torch.bfloat16 if __import__("os").environ.get("CELLS_FP32") != "1" else torch.float32

torch.set_num_threads(int(__import__("os").environ.get("CELLS_THREADS", "4")))
try:
    import ctypes
    _trim = ctypes.CDLL("libc.so.6").malloc_trim
except OSError:
    _trim = None


def load(base):
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(BASES[base])
    tok.padding_side = "left"
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(BASES[base], dtype=DTYPE)
    model.eval()
    return tok, model


_DATA = {}


def _words(x):
    import re
    return set(re.findall(r"[a-z]{4,}", x.lower()))


def data(skill):
    """train / dev / test. Test comes from the other pool of words. Dev must measure the same thing (unseen
    words), so it is made by holding out a random ~20% of the training words: an example with any held-out word
    goes to dev, never to train. A dev split with the training words saturates at 1.0 and cannot pick a winner."""
    if skill in _DATA:
        return _DATA[skill]
    pool = S.examples(skill, "train", N["train"] + N["dev"] * 2)
    te = S.examples(skill, "test", N["test"])
    from collections import Counter
    freq = Counter(w for x, _ in pool for w in _words(x))
    common = {w for w, c in freq.items() if c > len(pool) * 0.3}  # frame words every example shares stay in train
    cand = sorted(w for w in freq if w not in common)
    rnd = random.Random(f"heldout:{skill}")
    rnd.shuffle(cand)
    held, covered = set(), 0
    for w in cand:
        if covered >= len(pool) * 0.2:
            break
        held.add(w)
        covered = sum(bool(_words(x) & held) for x, _ in pool)
    dv = [(x, y) for x, y in pool if _words(x) & held][:N["dev"]]
    tr = [(x, y) for x, y in pool if not (_words(x) & held)][:N["train"]]
    if len(dv) < 20:  # too few distinct words to hold out: fall back to a plain carve
        rnd.shuffle(pool)
        n_dev = min(N["dev"], len(pool) // 4)
        dv, tr = pool[:n_dev], pool[n_dev:]
    _DATA[skill] = (tr, dv, te)
    return _DATA[skill]


def prompt(tok, skill, x):
    msgs = [{"role": "system", "content": S.SKILLS[skill]["instr"]}, {"role": "user", "content": x}]
    return tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)


def end_text(tok):
    return "<|im_end|>" if "<|im_end|>" in tok.get_vocab() else tok.eos_token


def encode(tok, skill, x, y):
    p = tok(prompt(tok, skill, x), add_special_tokens=False)["input_ids"]
    t = tok(y + end_text(tok), add_special_tokens=False)["input_ids"]
    return p + t, [-100] * len(p) + t


def collate(tok, batch):
    L = max(len(i) for i, _ in batch)
    ids = torch.full((len(batch), L), tok.pad_token_id)
    lab = torch.full((len(batch), L), -100)
    att = torch.zeros((len(batch), L), dtype=torch.long)
    for k, (i, l) in enumerate(batch):  # right padding for training
        ids[k, :len(i)] = torch.tensor(i)
        lab[k, :len(l)] = torch.tensor(l)
        att[k, :len(i)] = 1
    return ids, lab, att


def loss_on(model, tok, skill, rows, bs=16):
    tot, n = 0.0, 0
    with torch.no_grad():
        for i in range(0, len(rows), bs):
            ids, lab, att = collate(tok, [encode(tok, skill, x, y) for x, y in rows[i:i + bs]])
            out = model(input_ids=ids, attention_mask=att, labels=lab)
            tot += out.loss.item() * len(rows[i:i + bs])
            n += len(rows[i:i + bs])
    return tot / max(n, 1)


@torch.no_grad()
def predict(model, tok, skill, xs, bs=16):
    s = S.SKILLS[skill]
    preds = []
    if "labels" in s:  # a classifier: the label whose full text (and end) is most likely
        conts = [tok(lab + end_text(tok), add_special_tokens=False)["input_ids"] for lab in s["labels"]]
        for x in xs:
            p = tok(prompt(tok, skill, x), add_special_tokens=False)["input_ids"]
            batch = [(p + c, [-100] * len(p) + c) for c in conts]
            ids, lab, att = collate(tok, batch)
            logits = model(input_ids=ids, attention_mask=att).logits[:, :-1]
            tgt = lab[:, 1:]
            lp = torch.log_softmax(logits.float(), -1)
            m = tgt != -100
            tok_lp = lp.gather(-1, tgt.clamp(min=0).unsqueeze(-1)).squeeze(-1) * m
            preds.append(s["labels"][int(tok_lp.sum(-1).argmax())])
        return preds
    stop = tok.convert_tokens_to_ids(end_text(tok))
    for i in range(0, len(xs), bs):  # greedy, batched, left padded
        enc = tok([prompt(tok, skill, x) for x in xs[i:i + bs]], return_tensors="pt", padding=True, add_special_tokens=False)
        out = model.generate(**enc, max_new_tokens=s.get("max_new", 40), do_sample=False, eos_token_id=stop,
                             pad_token_id=tok.pad_token_id)
        preds += [tok.decode(o[enc["input_ids"].shape[1]:], skip_special_tokens=True) for o in out]
    return preds


def accuracy(model, tok, skill, rows):
    preds = predict(model, tok, skill, [x for x, _ in rows])
    return sum(S.score(skill, p, y) for p, (_, y) in zip(preds, rows)) / max(len(rows), 1), preds


def module_names(model):
    n = model.config.num_hidden_layers
    return [f"{i}:{m}" for i in range(n) for m in MODS]


def get_module(model, key):
    i, m = key.split(":")
    layer = model.model.layers[int(i)]
    return getattr(layer.self_attn if m in MODS[:4] else layer.mlp, m)


# ---------------------------------------------------------------- the probes (what the locator looks at)
def probe(skill, base, out=True):
    """Two maps of where a skill lives in the base:
    1. |W * dL/dW| per module: how much the loss would move if that module's weights moved (first-order).
    2. knockout per layer: dev loss when one layer's attention or MLP output is removed."""
    tok, model = load(base)
    tr, dv, _ = data(skill)
    rows = tr[:64]
    model.zero_grad()
    for i in range(0, len(rows), 16):
        ids, lab, att = collate(tok, [encode(tok, skill, x, y) for x, y in rows[i:i + 16]])
        model(input_ids=ids, attention_mask=att, labels=lab).loss.backward()
    attr = {}
    for k in module_names(model):
        w = get_module(model, k).weight
        attr[k] = float((w.detach().float() * w.grad.float()).abs().sum())
    model.zero_grad(set_to_none=True)
    kd = dv[:32]
    base_loss = loss_on(model, tok, skill, kd)
    knock = {}
    for i, layer in enumerate(model.model.layers):
        for part, mod in (("attn", layer.self_attn.o_proj), ("mlp", layer.mlp.down_proj)):
            h = mod.register_forward_hook(lambda m, a, o: torch.zeros_like(o))
            knock[f"{i}:{part}"] = loss_on(model, tok, skill, kd) - base_loss
            h.remove()
    res = {"skill": skill, "base": base, "dev_loss": base_loss, "attr": attr, "knockout": knock}
    if out:
        REPORTS.mkdir(parents=True, exist_ok=True)
        (REPORTS / f"probe_{skill}_{base}.json").write_text(json.dumps(res, indent=1))
    return res


def show_probe(res, top=20):
    attr, knock = res["attr"], res["knockout"]
    n = len(knock) // 2
    print(f"{res['skill']} on {res['base']}: dev loss {res['dev_loss']:.3f}")
    print("layer  " + " ".join(f"{m[:4]:>6s}" for m in MODS) + "   KO-attn  KO-mlp")
    mx = max(attr.values())
    for i in range(n):
        row = " ".join(f"{100 * attr[f'{i}:{m}'] / mx:6.1f}" for m in MODS)
        print(f"{i:5d}  {row}   {knock[f'{i}:attn']:+7.3f} {knock[f'{i}:mlp']:+7.3f}")
    print("top by |W*grad|:", ", ".join(k for k, _ in sorted(attr.items(), key=lambda kv: -kv[1])[:top]))


# ---------------------------------------------------------------- the edit
def _target(k):
    i, m = k.split(":")
    return f"layers.{i}.{'self_attn' if m in MODS[:4] else 'mlp'}.{m}"


def make_lora(model, keys, rank, alpha, thin=None):
    """Delta on `keys` at `rank`. With `thin`, every other module also gets a rank-`thin` delta: capacity where
    the locator says the skill lives, a thin layer everywhere else. One global alpha, so the scale of each
    module is alpha/its rank in PyTorch and in llama.cpp alike."""
    import re
    from peft import LoraConfig, get_peft_model
    if thin:
        every = [f"{i}:{m}" for i in range(model.config.num_hidden_layers) for m in MODS]
        cfg = LoraConfig(r=thin, lora_alpha=alpha, lora_dropout=0.0, target_modules=[_target(k) for k in every],
                         rank_pattern={re.escape(_target(k)): rank for k in keys}, task_type="CAUSAL_LM")
    else:
        cfg = LoraConfig(r=rank, lora_alpha=alpha, lora_dropout=0.0, target_modules=[_target(k) for k in keys],
                         task_type="CAUSAL_LM")
    return get_peft_model(model, cfg)


def copy_parent(peft_model, parent_dir):
    """Clone: start the new cell's deltas from the parent cell's deltas where they share a module."""
    from safetensors.torch import load_file
    w = load_file(str(Path(parent_dir) / "adapter_model.safetensors"))
    own = dict(peft_model.named_parameters())
    hit = 0
    for k, v in w.items():
        name = k.replace(".weight", ".default.weight")
        if name in own and own[name].shape == v.shape:
            own[name].data.copy_(v)
            hit += 1
    return hit


def train(skill, base, keys, rank=8, alpha=16, steps=150, lr=1e-3, bs=16, seed=0, parent=None, tag="pick",
          save=True, rows=None, thin=None):
    random.seed(seed)
    torch.manual_seed(seed)
    tok, model = load(base)
    tr, dv, te = data(skill)
    tr = rows or tr
    model = make_lora(model, keys, rank, alpha, thin)
    copied = copy_parent(model, parent) if parent else 0
    n_train = sum(p.numel() for p in model.parameters() if p.requires_grad)
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=lr, weight_decay=0.0)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / 10) * max(0.05, 1 - s / steps))
    enc = [encode(tok, skill, x, y) for x, y in tr]
    model.train()
    t0, order = time.time(), []
    for step in range(steps):
        if len(order) < bs:
            order += random.sample(range(len(enc)), len(enc))
        idx, order = order[:bs], order[bs:]
        ids, lab, att = collate(tok, [enc[i] for i in idx])
        loss = model(input_ids=ids, attention_mask=att, labels=lab).loss
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step(); sched.step(); opt.zero_grad(set_to_none=True)
        if _trim and step % 20 == 0:
            _trim(0)
        if step % 50 == 0 or step == steps - 1:
            print(f"  [{tag}] step {step} loss {loss.item():.4f} ({time.time() - t0:.0f}s)", flush=True)
    model.eval()
    dev, _ = accuracy(model, tok, skill, dv)
    test, preds = accuracy(model, tok, skill, te)
    res = {"skill": skill, "base": base, "tag": tag, "modules": keys, "rank": rank, "thin": thin, "alpha": alpha, "steps": steps,
           "lr": lr, "trainable_params": n_train, "parent": parent, "copied_tensors": copied, "dev": dev, "test": test,
           "train_seconds": round(time.time() - t0, 1),
           "test_errors": [(x, y, p) for (x, y), p in zip(te, preds) if not S.score(skill, p, y)][:8]}
    print(f"  [{tag}] {skill}: dev {dev:.3f} test {test:.3f} params {n_train:,} ({res['train_seconds']}s)", flush=True)
    if save:
        d = CELLS / "variants" / skill / tag
        model.save_pretrained(d)
        (d / "result.json").write_text(json.dumps(res, indent=1))
    return res


def eval_base(skill, base):
    tok, model = load(base)
    _, dv, te = data(skill)
    dev, _ = accuracy(model, tok, skill, dv)
    test, _ = accuracy(model, tok, skill, te)
    res = {"skill": skill, "base": base, "tag": "base", "dev": dev, "test": test, "trainable_params": 0}
    d = CELLS / "variants" / skill / "base"
    d.mkdir(parents=True, exist_ok=True)
    (d / "result.json").write_text(json.dumps(res, indent=1))
    print(f"  [base] {skill}: dev {dev:.3f} test {test:.3f}", flush=True)
    return res


def parse_pick(s):
    keys = []
    for part in s.split(","):
        layers, mods = part.split(":")
        a, _, b = layers.partition("-")
        for i in range(int(a), int(b or a) + 1):
            for m in mods.split("+"):
                keys.append(f"{i}:{m if m.endswith('_proj') else m + '_proj'}")
    return keys


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["probe", "train", "eval-base", "show"])
    ap.add_argument("skill")
    ap.add_argument("--base", default="smol135")
    ap.add_argument("--pick", help="locator's choice, e.g. '20-23:down,25:q+v'")
    ap.add_argument("--auto", type=int)
    ap.add_argument("--random", type=int)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--rank", type=int, default=8)
    ap.add_argument("--steps", type=int, default=150)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--tag")
    ap.add_argument("--parent")
    a = ap.parse_args()
    if a.cmd == "probe":
        show_probe(probe(a.skill, a.base))
    elif a.cmd == "show":
        show_probe(json.loads((REPORTS / f"probe_{a.skill}_{a.base}.json").read_text()))
    elif a.cmd == "eval-base":
        eval_base(a.skill, a.base)
    else:
        from transformers import AutoConfig
        n_layers = AutoConfig.from_pretrained(BASES[a.base]).num_hidden_layers
        every = [f"{i}:{m}" for i in range(n_layers) for m in MODS]
        if a.pick:
            keys, tag = parse_pick(a.pick), a.tag or "pick"
        elif a.auto:
            p = json.loads((REPORTS / f"probe_{a.skill}_{a.base}.json").read_text())
            keys, tag = [k for k, _ in sorted(p["attr"].items(), key=lambda kv: -kv[1])[:a.auto]], a.tag or f"auto{a.auto}"
        elif a.random:
            keys, tag = random.Random(7).sample(every, a.random), a.tag or f"random{a.random}"
        else:
            keys, tag = every, a.tag or "all"
        train(a.skill, a.base, keys, rank=a.rank, steps=a.steps, lr=a.lr, tag=tag, parent=a.parent)
