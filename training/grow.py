"""The hive is one body: one ternary model (its DNA) and many cells, each the DNA with a small weight edit of its own.

    practice  ->  rows  ->  every cell regrown from the rows  ->  gate  ->  the body's next generation

practice   Fresh tasks that are never an exam's (seeds from ten million up; the exam's held-out kinds are never
           practised). The body's own cells do them as they do any task (team/solo.py). A task counts only when two
           cells agreed AND the task's own check, computed by code, confirms the answer.
rows       From each such task, what the cell that got it right wrote: the task -> its final program, the
           program's output -> DONE, and, where it first failed, the failure -> the mended program. Nobody labelled
           anything: the label is that the program ran and its answer was checked.
train      Every cell is grown again from the same DNA (Ternary-Bonsai-1.7B, 0.43 GB packed, the smallest ternary
           model whose full weights are published) on all the rows, as a low-rank weight edit (LoRA) on a CPU. A
           cell leans to one organ (team/ternary.ORGANS): it meets that organ's rows three times as often. So the
           cells are the same size, overlap, and each is strongest somewhere. A cell is a file of a few megabytes
           (cells/members/<dna>+<name>.gguf); the DNA is in memory once for all of them.
gate       The same fresh exam sat by the DNA as published, by the body as it was and by the body as regrown; the
           body changes only when the numbers say so (.github/workflows/grow.yml, training/grow_record.py).

    python training/grow.py practice --seed 10000001 --tasks 16 [--level mixed|hard|basic] [--out runs/grow/rows.jsonl]
    python training/grow.py rows RUN_FOLDER ... [--out rows.jsonl]      rows from sittings already done (checked tasks only)
    python training/grow.py train --rows rows.jsonl --name g3code --lean code [--epochs 2] [--minutes 240] [--ternary] [--foresee]
    python training/grow.py fetch                                        the cells of the body, from the release
"""
import json
import math
import os
import random
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

GROW = ROOT / "runs" / "grow"
UNPACKED = {"t17": "prism-ml/Ternary-Bonsai-1.7B-unpacked", "t40": "prism-ml/Ternary-Bonsai-4B-unpacked"}  # members whose full weights are published, so they can be taught
RELEASE = "hive-grown"  # the GitHub release that holds the rows and the weight edits (never in git: they are big and machine-made)


# ---- rows ------------------------------------------------------------------------------------------------------------
def rows_of(run, task, kind="", seed=None):
    """The training rows of one task that two members agreed on and the check confirmed. run: the task's folder."""
    from team import solo
    home = Path(run) / "members" if (Path(run) / "members" / "members.json").exists() else Path(run)
    try:
        info = json.loads((home / "members.json").read_text())
    except (OSError, ValueError):
        return []
    out = []
    for n in info.get("agreeing", []):
        try:
            t = json.loads((home / f"member{n}.json").read_text())
        except (OSError, ValueError):
            continue
        ms, program = t.get("messages") or [], (t.get("program") or "").strip()
        if len(ms) < 3 or not program or len(program) > 6000:
            continue
        # the taught member's short orders (team/solo.SHORT) with the day the work was done, and the task
        day = re.search(r"Today is (\d{4}-\d\d-\d\d \(\w+\))", ms[0]["content"])
        head = [{"role": "system", "content": solo.SHORT.format(today=day.group(1) if day else time.strftime("%Y-%m-%d (%A)"))}, ms[1]]
        fenced = f"```python\n{program}\n```"
        base = {"task": task, "kind": kind, "seed": seed, "who": t.get("who", ""), "member": n}
        out.append(base | {"type": "first", "messages": head, "output": fenced})
        out.append(base | {"type": "done", "messages": head + [{"role": "assistant", "content": fenced},
                                                                 {"role": "user", "content": f"OUTPUT:\n{t['answer'][-1800:]}\n\n{solo.MORE}"}], "output": "DONE"})
        # where it failed first: the failing program and what it was told, then the program that was right
        for i in range(2, len(ms) - 2, 2):
            a, fb, nxt = ms[i], ms[i + 1], ms[i + 2]
            if a["role"] == "assistant" and nxt["role"] == "assistant" and solo.extract_code(nxt["content"]).strip() == program \
                    and solo.extract_code(a["content"]).strip() != program and len(a["content"]) < 5000 and len(fb["content"]) < 3000:
                out.append(base | {"type": "fix", "messages": head + [a, fb], "output": fenced})
                break
    return out


FORESEE = ("Here is a program that was written for the TASK. Do not write a program: say exactly what this one prints "
           "when it is run (or the last line of its error if it fails).\n```python\n{program}\n```")


def foresee_rows(run, task, kind="", seed=None, most=4):
    """Rows of another kind, from every program any cell ran on a task, right or wrong: the program -> what it
    printed. A cell that can say what a program will print before it runs knows how programs behave; the hive has
    many times more of these rows than of solved tasks, and running the program was the only label needed.
    (The hive's own form of learning by predicting. Used in training only with --foresee, until a gate has shown
    that cells grown with them do better than cells grown without.)"""
    from team import solo
    home = Path(run) / "members" if (Path(run) / "members").exists() else Path(run)
    out, seen = [], set()
    for prog in sorted(home.rglob("member*_*.py")):
        code = prog.read_text(errors="ignore").strip()
        printed = (prog.parent / f".{prog.name}.out")
        err = (prog.parent / f".{prog.name}.err")
        said = printed.read_text(errors="ignore").strip() if printed.exists() else ""
        if not said and err.exists() and err.read_text(errors="ignore").strip():
            said = err.read_text(errors="ignore").strip().splitlines()[-1]
        if not code or not said or len(code) > 3000 or len(said) > 500 or code in seen or re.search(r"look\(|requests|urllib|http|datetime\.(?:now|today)|date\.today|random", code):  # only what the program alone decides
            continue
        seen.add(code)
        out.append({"task": task, "kind": kind, "seed": seed, "type": "foresee", "output": said,
                    "messages": [{"role": "system", "content": solo.SHORT.format(today=time.strftime("%Y-%m-%d (%A)"))},
                                 {"role": "user", "content": f"TASK: {task}\n\n" + FORESEE.format(program=code)}]})
        if len(out) >= most:
            break
    return out


def practice(seed, n=16, level="mixed", out=None, log=print):
    """Fresh practice tasks done by the hive's members; the rows of those the check confirmed are appended to out."""
    from training import exam as E
    from training import exam_hard
    out = Path(out or GROW / "rows.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("AGENT_TEAM_SOLO", "2")
    os.environ.setdefault("AGENT_TEAM_SOLO_ALONE", "1")
    home = E._memory(True)
    made = right = 0
    for tid, field, kind, task, check in E.exam(seed, n, (), level, without=exam_hard.HELD_OUT):
        r = E.sit_one(f"practice_{seed}", tid, task, check, home)
        new = rows_of(E.RUNS / f"practice_{seed}" / tid, task, kind, seed) if r["ok"] else []
        new += foresee_rows(E.RUNS / f"practice_{seed}" / tid, task, kind, seed)
        with open(out, "a") as f:
            for row in new:
                f.write(json.dumps(row) + "\n")
        made, right = made + sum(x["type"] != "foresee" for x in new), right + r["ok"]
        log(f"{'RIGHT' if r['ok'] else 'not right'} {tid} [{kind}] {r['seconds']}s, {len(new)} rows", flush=True)
    return {"practice": seed, "level": level, "tasks": n, "right": right, "rows": made, "file": str(out)}


def rows_from(folders, out):
    """Rows from sittings that were already done: every task folder with an exam.json that says ok."""
    made = 0
    with open(out, "a") as f:
        for folder in folders:
            for ex in sorted(Path(folder).rglob("exam.json")):
                try:
                    r = json.loads(ex.read_text())
                except ValueError:
                    continue
                task = (ex.parent / "members" / "TASK.md")
                if r.get("ok") and task.exists():
                    for row in rows_of(ex.parent, task.read_text().strip()):
                        f.write(json.dumps(row) + "\n")
                        made += 1
    return made


# ---- train -----------------------------------------------------------------------------------------------------------
def train(rows_file, name, base="t17", epochs=2.0, rank=16, lr=2e-4, max_len=1152, layers="all", accum=4, seed=0, limit=0, minutes=0, log=print,
          lean="", weight=3, foresee=False, ternary_edit=False, out_dir=None, checkpoint=True):
    """A LoRA weight edit of a ternary member from the hive's rows, on a CPU; written as a GGUF adapter the
    ternary runtime loads beside the packed base."""
    import torch
    from huggingface_hub import snapshot_download
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer

    from team import ternary
    torch.set_num_threads(int(os.environ.get("AGENT_TEAM_THREADS", os.cpu_count() or 4)))
    random.seed(seed)
    torch.manual_seed(seed)
    from team import solo
    rows = [json.loads(x) for x in Path(rows_file).read_text().splitlines() if x.strip()]
    for r in rows:  # rows made before the short orders existed carry the long ones: the taught member is trained under the short
        day = re.search(r"Today is (\d{4}-\d\d-\d\d \(\w+\))", r["messages"][0]["content"])
        r["messages"][0] = {"role": "system", "content": solo.SHORT.format(today=day.group(1) if day else time.strftime("%Y-%m-%d (%A)"))}
    if not foresee:
        rows = [r for r in rows if r.get("type") != "foresee"]
    seen, uniq = set(), []
    for r in rows:  # the same exchange from two sittings teaches nothing twice
        k = json.dumps([r["messages"][1:], r["output"]])
        if k not in seen:
            seen.add(k)
            uniq.append(r)
    rows = uniq
    src = snapshot_download(UNPACKED[base])
    tok = AutoTokenizer.from_pretrained(src)
    model = AutoModelForCausalLM.from_pretrained(src, dtype=torch.bfloat16)
    nl = model.config.num_hidden_layers
    which = (list(range(nl)) if layers == "all" else list(range(nl // 2, nl)) if layers == "top" else
             list(range(nl - int(layers[4:]), nl)) if layers.startswith("last") else list(range(*map(int, layers.split("-")))))
    model = get_peft_model(model, LoraConfig(r=rank, lora_alpha=2 * rank, lora_dropout=0.05, layers_to_transform=which, task_type="CAUSAL_LM",
                                             target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]))
    if ternary_edit:
        # The cell's own edit in three values as well: each of its matrices is held as ordinary numbers while it is
        # trained, and what the net computes with is their ternary form (-s, 0, +s; s the mean size), the way
        # BitNet b1.58 trains. What is saved is the ternary form, so the whole cell is a BitNet.
        from torch.nn.utils import parametrize

        class Three(torch.nn.Module):
            def forward(self, w):
                s = w.detach().abs().mean().clamp(min=1e-8)
                return w + ((w / s).round().clamp(-1, 1) * s - w).detach()
        edits = [m for n, m in model.named_modules() if n.endswith(("lora_A.default", "lora_B.default"))]
        for m in edits:
            parametrize.register_parametrization(m, "weight", Three())
    model.config.use_cache = False
    # Each layer's inner values are worked out again on the way back instead of being kept: a third slower, and the
    # memory no longer grows with the length of a row (the first run on a 16 GB runner was killed at step 5).
    if checkpoint:
        model.gradient_checkpointing_enable()
        model.enable_input_require_grads()

    def encode(row):
        p = tok(tok.apply_chat_template(row["messages"], tokenize=False, add_generation_prompt=True, enable_thinking=False), add_special_tokens=False)["input_ids"]
        t = tok(row["output"] + "<|im_end|>\n", add_special_tokens=False)["input_ids"]
        return (torch.tensor([p + t]), len(t)) if len(p) + len(t) <= max_len else None
    data, mine = [], 0
    for row in rows:
        d = encode(row)
        if d is not None:
            # a cell that leans to an organ meets that organ's rows `weight` times as often as the others: every cell
            # learns all of the hive's checked work (so any two can check each other), each one its own part best
            own = bool(lean) and ternary.organ(row["task"]) == lean
            data += [d] * (weight if own else 1)
            mine += own
    if limit:
        data = data[:limit]
    if lean:
        log(f"this cell leans to {lean}: {mine} of its rows are that organ's, each met {weight} times", flush=True)
    random.seed(f"{seed}:{lean}")
    torch.manual_seed(abs(hash(lean)) % 10**6 + seed)
    log(f"{len(rows)} rows, {len(data)} within {max_len} pieces (mean {sum(d[0].shape[1] for d in data) // max(1, len(data))}); "
        f"LoRA rank {rank} on layers {which[0]}-{which[-1]} of {UNPACKED[base]}", flush=True)
    params = [p for p in model.parameters() if p.requires_grad]
    if minutes and data:
        # Runners differ in speed by several times. One row is timed, and the passes are cut to what fits the time
        # given (a job that runs out of time leaves nothing behind).
        t = time.time()
        with torch.autocast("cpu", dtype=torch.bfloat16):
            big = max(data, key=lambda d: d[0].shape[1])
            model(input_ids=big[0], logits_to_keep=big[1] + 1).logits.float().mean().backward()
        model.zero_grad()
        per = (time.time() - t) * (sum(d[0].shape[1] for d in data) / len(data)) / big[0].shape[1]
        fit = minutes * 60 / max(per, 1e-3) / len(data)
        log(f"one row of mean length takes about {per:.1f} s; {minutes} minutes hold {fit:.2f} passes over {len(data)} rows", flush=True)
        if fit < epochs:
            epochs = max(0.25, round(fit, 2))
            log(f"passes cut to {epochs}", flush=True)
    opt = torch.optim.AdamW(params, lr=lr, weight_decay=0.0)
    steps = math.ceil(len(data) * epochs / accum)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / max(1, steps // 10)) * max(0.05, 1 - s / max(1, steps)))
    order = []
    while len(order) < len(data) * epochs:
        perm = list(range(len(data)))
        random.shuffle(perm)
        order += perm
    order = order[:int(len(data) * epochs)]
    try:
        import ctypes
        trim = ctypes.CDLL("libc.so.6").malloc_trim
    except OSError:
        trim = None
    model.train()
    t0, running, step, hist = time.time(), 0.0, 0, []
    for i, idx in enumerate(order):
        ids, k = data[idx]
        with torch.autocast("cpu", dtype=torch.bfloat16):
            logits = model(input_ids=ids, logits_to_keep=k + 1).logits[:, :-1, :]
        loss = torch.nn.functional.cross_entropy(logits.float().reshape(-1, logits.size(-1)), ids[:, -k:].reshape(-1))
        (loss / accum).backward()
        running += loss.item()
        if (i + 1) % accum == 0 or i == len(order) - 1:
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            opt.step()
            sched.step()
            opt.zero_grad()
            if trim:
                trim(0)
            step += 1
            n = accum if (i + 1) % accum == 0 else (i + 1) % accum
            hist.append(round(running / n, 4))
            running = 0.0
            if step % 5 == 0 or step == steps:
                import resource
                log(f"step {step}/{steps} loss {hist[-1]:.4f} {time.time() - t0:.0f}s, most memory {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20:.1f} GB", flush=True)
    work = GROW / f"{base}+{name}"
    work.mkdir(parents=True, exist_ok=True)
    if ternary_edit:
        for m in edits:
            parametrize.remove_parametrizations(m, "weight", leave_parametrized=True)
        levels = max(len(torch.unique(m.weight.detach().float())) for m in edits)
        log(f"the cell's edit is ternary: at most {levels} different values in any of its {len(edits)} matrices", flush=True)
    model.save_pretrained(str(work))
    meta = {"member": f"{base}+{name}", "leans": lean, "ternary_edit": bool(ternary_edit), "foresee": bool(foresee), "base": UNPACKED[base], "rows": len(rows), "used": len(data), "epochs": epochs, "rank": rank, "lr": lr,
            "layers": [which[0], which[-1]], "steps": step, "seconds": round(time.time() - t0), "loss_first": hist[0] if hist else None,
            "loss_last": round(sum(hist[-5:]) / max(1, len(hist[-5:])), 4) if hist else None, "when": time.strftime("%Y-%m-%d %H:%M"),
            "memory_gb": round(__import__("resource").getrusage(__import__("resource").RUSAGE_SELF).ru_maxrss / 2**20, 1)}
    # the adapter as the runtime reads it
    conv = ternary.source() / "convert_lora_to_gguf.py"
    where = Path(out_dir or ternary.ADAPTERS)
    where.mkdir(parents=True, exist_ok=True)
    gguf = where / f"{base}+{name}.gguf"
    done = subprocess.run([sys.executable, str(conv), "--base", src, "--outfile", str(gguf), "--outtype", "f16", str(work)], capture_output=True, text=True)
    if done.returncode:
        raise RuntimeError("the edit could not be written as a GGUF adapter: " + done.stderr[-800:])
    meta["file"], meta["megabytes"] = str(gguf), round(gguf.stat().st_size / 2**20, 1)
    (where / f"{base}+{name}.json").write_text(json.dumps(meta, indent=1))
    return meta


def fetch(names=(), log=print):
    """The weight edits the roster names (or those given), downloaded from the release into cells/members/."""
    import urllib.request

    from team import ternary
    repo = os.environ.get("GITHUB_REPOSITORY", "Arnav123-s/HiveMIND")
    got = []
    if not names and not os.environ.get("HIVE_MEMBERS"):
        try:
            body = json.loads(ternary.BODY.read_text())
            names = [f"{body['dna']}+{c}" for c in body.get("cells", [])]
        except (OSError, ValueError, KeyError):
            names = []
    for who in names or ternary.roster():
        if "+" not in who or ternary.adapter(who).exists():
            continue
        ternary.ADAPTERS.mkdir(parents=True, exist_ok=True)
        url = f"https://github.com/{repo}/releases/download/{RELEASE}/{who.replace('+', '.')}.gguf"
        try:
            urllib.request.urlretrieve(url, ternary.adapter(who))
            got.append(who)
        except OSError as e:
            log(f"{who}: not fetched from {url}: {e}")
    return got


def main(argv):
    opt = lambda k, d: type(d)(argv[argv.index(k) + 1]) if k in argv else d  # noqa: E731
    cmd = argv[0] if argv else ""
    if cmd == "practice":
        print(json.dumps(practice(opt("--seed", 10_000_000 + int(time.time() // 60)), opt("--tasks", 16), opt("--level", "mixed"), opt("--out", ""))))
    elif cmd == "rows":
        out = opt("--out", str(GROW / "rows.jsonl"))
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        print(rows_from([a for a in argv[1:] if not a.startswith("--") and a != out], out), "rows added to", out)
    elif cmd == "train":
        print(json.dumps(train(opt("--rows", str(GROW / "rows.jsonl")), opt("--name", "gen"), opt("--base", "t17"), opt("--epochs", 2.0), opt("--rank", 16),
                               opt("--lr", 2e-4), opt("--max-len", 1152), opt("--layers", "all"), limit=opt("--limit", 0), minutes=opt("--minutes", 0), lean=opt("--lean", ""), weight=opt("--weight", 3), foresee="--foresee" in argv, ternary_edit="--ternary" in argv), indent=1))
    elif cmd == "fetch":
        print(fetch([a for a in argv[1:] if not a.startswith("--")]))
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
