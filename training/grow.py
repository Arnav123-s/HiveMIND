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
import contextlib
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
UNPACKED = {"t17": "prism-ml/Ternary-Bonsai-1.7B-unpacked", "t40": "prism-ml/Ternary-Bonsai-4B-unpacked", "t80": "prism-ml/Ternary-Bonsai-8B-unpacked"}  # members whose full weights are published, so they can be taught
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


def pair_rows(run, task, kind="", seed=None, most=4):
    """Rows that set a right program beside a wrong one written for the same task, from a task the check confirmed.
    The right one is what two members agreed on; the wrong ones are the members' first programs that did not give
    that answer (sent back with an error, or a different result). Trained with --pairs (Iterative Reasoning
    Preference Optimization: DPO with a likelihood term, Pang et al. 2024), the cell learns what makes a program
    wrong as well as what a right one looks like; training only on right answers tends to memorise them (Chu et al.
    2025, "SFT memorizes, RL generalizes"). Used only with --pairs, until a gate has shown it helps."""
    from team import solo
    home = Path(run) / "members" if (Path(run) / "members" / "members.json").exists() else Path(run)
    try:
        info = json.loads((home / "members.json").read_text())
    except (OSError, ValueError):
        return []
    tries = {}
    for f in sorted(home.glob("member[0-9]*.json")):
        try:
            tries[int(re.sub(r"\D", "", f.stem))] = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
    win = next((tries[n] for n in info.get("agreeing", []) if n in tries and (tries[n].get("program") or "").strip()), None)
    if not win or len(win.get("messages") or []) < 3 or len(win["program"]) > 6000:
        return []
    ms, program = win["messages"], win["program"].strip()
    day = re.search(r"Today is (\d{4}-\d\d-\d\d \(\w+\))", ms[0]["content"])
    head = [{"role": "system", "content": solo.SHORT.format(today=day.group(1) if day else time.strftime("%Y-%m-%d (%A)"))}, ms[1]]
    out, seen = [], {program}
    for n, t in sorted(tries.items()):
        tm = t.get("messages") or []
        if len(tm) < 3 or tm[2].get("role") != "assistant":
            continue
        code = solo.extract_code(tm[2]["content"]).strip()
        if not code or code in seen or len(code) > 6000:
            continue
        seen.add(code)
        # whose wrong program it was, and what that member was shown when it ran (its output or its error): a child
        # of that cell learns the correction from exactly there (train: "mend")
        shown = tm[3]["content"].rsplit("\n\n", 1)[0][-900:] if len(tm) > 3 and tm[3].get("role") == "user" else ""
        out.append({"task": task, "kind": kind, "seed": seed, "type": "pair", "member": n, "messages": head,
                    "output": f"```python\n{program}\n```", "rejected": f"```python\n{code}\n```",
                    "rejected_who": t.get("who", ""), "shown": shown})
        if len(out) >= most:
            break
    return out


MEND = "{shown}\n\nThe task's check says that answer is not right. Reply with the whole corrected program."
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


def _dna():
    """The DNA of the body on this machine (cells/body.json), t80 when it says none."""
    from team import ternary
    try:
        return json.loads(ternary.BODY.read_text()).get("dna") or "t80"
    except (OSError, ValueError, AttributeError):
        return "t80"


def edge_weights(dna="t17", last=3, record=None):
    """{kind: weight} for practice at the edge: the more a kind sits near half passed, the more it is practised.
    A kind always passed is learned; one never passed gives no right program to learn from and no right-against-
    wrong pair yet. p is the body's pass rate on the kind over the last `last` gates of this DNA (with one pass and
    one failure added, so a kind seen twice is not taken as settled), and the weight is p(1 - p), the most at
    one half. As the body gets better, easy kinds drop out of practice and harder ones come in by themselves."""
    rec = Path(record or ROOT / "training" / "reports" / "generations.jsonl")
    lines = []
    for ln in (rec.read_text().splitlines() if rec.exists() else []):
        try:
            d = json.loads(ln)
        except ValueError:
            continue
        if d.get("dna", "t17") == dna and d.get("arms", {}).get("after", {}).get("kinds"):
            lines.append(d)
    seen = {}
    for d in lines[-last:]:
        for k, (p, n) in d["arms"]["after"]["kinds"].items():
            a = seen.setdefault(k, [0, 0])
            a[0], a[1] = a[0] + p, a[1] + n
    return {k: ((p + 1) / (n + 2)) * (1 - (p + 1) / (n + 2)) for k, (p, n) in seen.items()}


def practice(seed, n=16, level="mixed", out=None, log=print, minutes=0):
    """Fresh practice tasks done by the hive's members; the rows of those the check confirmed are appended to out.
    minutes: no new task is begun after so long (a runner's job that runs out of time keeps nothing; what is done
    by then is written task by task)."""
    born = time.time()
    from training import exam as E
    from training import exam_hard
    out = Path(out or GROW / "rows.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("AGENT_TEAM_SOLO", "2")
    os.environ.setdefault("AGENT_TEAM_SOLO_ALONE", "1")
    home = E._memory(True)
    made = right = 0
    # where to practise most: the kinds the body's own exams show at its edge (edge and ladder alike; the ladder sets
    # how hard each is). The weights of the body's own DNA: those of another DNA say nothing about this one.
    weights = edge_weights(_dna()) if level in ("edge", "ladder") else None
    if weights:
        log("practice at the edge: " + ", ".join(f"{k} {w:.2f}" for k, w in sorted(weights.items(), key=lambda x: -x[1])), flush=True)
    levels = body_levels() if level == "ladder" else None
    if levels:
        log("how hard the lessons are now: " + ", ".join(f"{k} {v}" for k, v in sorted(levels.items())), flush=True)
    passed = []
    for tid, field, kind, task, check in E.exam(seed, n, (), level, without=exam_hard.HELD_OUT, weights=weights, levels=levels):
        if minutes and time.time() - born > minutes * 60:
            log(f"time is up after {len(passed)} of {n} tasks: practice ends here", flush=True)
            break
        r = E.sit_one(f"practice_{seed}", tid, task, check, home, kind=kind)
        new = rows_of(E.RUNS / f"practice_{seed}" / tid, task, kind, seed) if r["ok"] else []
        new += pair_rows(E.RUNS / f"practice_{seed}" / tid, task, kind, seed) if r["ok"] else []
        if os.environ.get("HIVE_FORESEE") == "1":
            new += foresee_rows(E.RUNS / f"practice_{seed}" / tid, task, kind, seed)
        with open(out, "a") as f:
            for row in new:
                f.write(json.dumps(row) + "\n")
        made, right = made + sum(x["type"] not in ("foresee", "pair") for x in new), right + r["ok"]
        if not r["ok"]:
            remember_failure(E.RUNS / f"practice_{seed}" / tid, task, kind, check, r, out.with_name("failures.jsonl"))
        passed.append({"maker": getattr(check, "maker", ""), "level": getattr(check, "level", 0), "ok": bool(r["ok"])})
        # what was passed at which level, for the record to move the levels by (training/grow_record.levels)
        out.with_name("practice.json").write_text(json.dumps({"seed": seed, "tasks": passed}))
        log(f"{'RIGHT' if r['ok'] else 'not right'} {tid} [{kind}] {r['seconds']}s, {len(new)} rows", flush=True)
    return {"practice": seed, "level": level, "tasks": len(passed), "right": right, "rows": made, "file": str(out)}


def body_levels():
    """{maker: level, "compound": parts}: how hard the body's lessons are now (cells/body.json, moved by each
    generation's record)."""
    from team import ternary
    try:
        lv = json.loads(ternary.BODY.read_text()).get("levels") or {}
        return {str(k): int(v) for k, v in lv.items() if isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 9}
    except (OSError, ValueError, AttributeError):
        return {}


def _masked(why):
    """What the check said, with its numbers hidden: the hive is to find its mistake, not copy the answer."""
    return re.sub(r"\d+(?:[.,]\d+)*", "#", why or "")[:400]


def remember_failure(run, task, kind, check, result, path):
    """A task the hive got wrong, kept so that it can come back to it (dream): how to make the task again, its own
    last program and what that printed, and what the check said, numbers hidden."""
    if not getattr(check, "maker", None):
        return
    home = Path(run) / "members"
    program, printed, who = "", "", []
    for f in sorted(home.glob("member[0-9]*.json")):
        try:
            t = json.loads(f.read_text())
        except (OSError, ValueError):
            continue
        who.append(str(t.get("who", ""))[:80])
        if program:
            continue
        ms = [m for m in t.get("messages") or [] if m.get("role") == "assistant"]
        program = (t.get("program") or (solo_code(ms[-1]["content"]) if ms else "")).strip()
        printed = (t.get("answer") or "")[-600:]
    if not program or len(program) > 5000:
        return
    with open(path, "a") as f:
        f.write(json.dumps({"maker": check.maker, "rseed": check.rseed, "level": getattr(check, "level", 0), "parts": getattr(check, "parts", None),
                            "task": task, "kind": kind, "program": program, "printed": printed, "who": who,
                            "said": _masked(result.get("why")), "when": time.strftime("%Y-%m-%d %H:%M")}) + "\n")


def solo_code(text):
    from team import solo
    return solo.extract_code(text)


DREAM = ("{task}\n\nThis task was done once before, and the answer was wrong. The program written then:\n```python\n{program}\n```\n"
         "It printed: {printed}\nWhat the check said about it (its numbers hidden): {said}\n"
         "Find the mistake in that program, then write the whole corrected program.")


def dream(seed, n=4, failures=None, out=None, log=print, minutes=0):
    """The hive goes back to tasks it got wrong (failures.jsonl, kept by practice) and corrects itself. Each is made
    again exactly (training/exam.remake), with the old program and what the check said (numbers hidden); where the
    check now passes, the correction is a training row like any other: the old attempt and the verdict lead to the
    right program. Problem solving is the correcting of errors, and the hive's own errors are what it can correct
    (STaR's going back to failed problems, Zelikman et al. 2022; Reflexion, Shinn et al. 2023)."""
    from training import exam as E
    out = Path(out or GROW / "rows.jsonl")
    src = Path(failures or out.with_name("failures.jsonl"))
    seen = []
    for ln in (src.read_text().splitlines() if src.exists() else []):
        try:
            seen.append(json.loads(ln))
        except ValueError:
            continue
    if not seen:
        return {"dream": seed, "tasks": 0, "right": 0, "rows": 0}
    r = random.Random(f"dream:{seed}")
    recent = seen[-400:]
    pick = r.sample(recent, min(n, len(recent)))
    os.environ.setdefault("AGENT_TEAM_SOLO", "2")
    os.environ.setdefault("AGENT_TEAM_SOLO_ALONE", "1")
    home = E._memory(True)
    right = made = 0
    born = time.time()
    for i, f in enumerate(pick):
        if minutes and time.time() - born > minutes * 60:
            log(f"time is up after {i} of {len(pick)} dreams", flush=True)
            break
        again = E.remake(f.get("maker", ""), f.get("rseed", ""), f.get("level", 0), f.get("parts"))
        if not again:
            continue
        field, kind, task, check = again
        text = DREAM.format(task=task, program=f["program"][:5000], printed=(f.get("printed") or "nothing")[:600], said=f.get("said", ""))
        tid = f"d{seed}_{i:02d}"
        res = E.sit_one(f"dream_{seed}", tid, text, check, home, kind=kind)
        new = []
        if res["ok"]:
            new = rows_of(E.RUNS / f"dream_{seed}" / tid, task, kind, seed) + pair_rows(E.RUNS / f"dream_{seed}" / tid, task, kind, seed)
            for row in new:
                row["dream"] = True
        with open(out, "a") as fo:
            for row in new:
                fo.write(json.dumps(row) + "\n")
        right += res["ok"]
        made += sum(x["type"] != "pair" for x in new)
        log(f"dream {'CORRECTED' if res['ok'] else 'still wrong'} {tid} [{kind}] {res['seconds']}s, {len(new)} rows", flush=True)
    return {"dream": seed, "tasks": len(pick), "right": right, "rows": made}


def gather(out, gen, old=(), new=(), log=print):
    """Every checked row so far in one file: those of earlier generations as they are, then this generation's, each
    stamped with the generation it was practised in (training tells new rows from ones the parents already learned).
    The same row is kept once. Returns (rows kept from before, rows added)."""
    from training import grow_record
    lines_old = [ln for f in old for ln in grow_record.lines(f)]
    lines_new = []
    for f in new:
        for ln in grow_record.lines(f):
            try:
                row = json.loads(ln)
            except ValueError:
                continue
            if isinstance(row, dict):
                row.setdefault("gen", gen)
                lines_new.append(json.dumps(row))
    kept = grow_record.union([lines_old, lines_new])
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text("".join(ln + "\n" for ln in kept))
    before = len(grow_record.union([lines_old]))
    return before, len(kept) - before


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
                    t = task.read_text().strip()
                    for row in rows_of(ex.parent, t) + pair_rows(ex.parent, t):
                        f.write(json.dumps(row) + "\n")
                        made += 1
    return made


# ---- train -----------------------------------------------------------------------------------------------------------
class _Prefix:
    """The layers below the first trained one are frozen, so for a given row they compute the same thing on every
    pass. Their output (the input to the first trained layer) is kept from the first pass of each row, and on later
    passes those layers are skipped and the kept value is used: the same result, without a third to half of the
    forward work from the second pass on (a cell trains the last 14 layers of 28 or 36). Rows are known by their
    tensor. The kept values live in memory up to HIVE_PREFIX_GB (3 by default), or, given a folder, in files there
    up to HIVE_PREFIX_DISK_GB (6): an 8B DNA on a 16 GB runner has no memory to spare for them."""

    def __init__(self, model, first, log=print, folder=None):
        import torch
        layers = model.get_base_model().model.layers if hasattr(model, "get_base_model") else model.model.layers
        self.kept, self.key, self.skip, self.bytes, self.hits, self.misses = {}, None, False, 0, 0, 0
        self.folder = Path(folder) if folder else None
        if self.folder:
            import shutil
            shutil.rmtree(self.folder, ignore_errors=True)
            self.folder.mkdir(parents=True, exist_ok=True)
        self.most = float(os.environ.get("HIVE_PREFIX_DISK_GB", "6") if self.folder else os.environ.get("HIVE_PREFIX_GB", "3")) * 2**30
        for layer in layers[:first]:
            orig = layer.forward

            def passthrough(hidden_states, *a, _orig=orig, **k):
                return hidden_states if self.skip else _orig(hidden_states, *a, **k)
            layer.forward = passthrough

        def pre(module, args, kwargs):
            h = args[0] if args else kwargs["hidden_states"]
            if self.skip:
                h = self._get(self.key)
            elif self.key is not None and self.key not in self.kept and torch.is_grad_enabled() and self.bytes < self.most:
                self._put(self.key, h.detach())
            if args:
                return (h,) + tuple(args[1:]), kwargs
            return args, dict(kwargs, hidden_states=h)
        layers[first].register_forward_pre_hook(pre, with_kwargs=True)

    def _put(self, key, h):
        import torch
        self.bytes += h.numel() * h.element_size()
        if not self.folder:
            self.kept[key] = h
            return
        raw = {2: torch.int16, 4: torch.int32}[h.element_size()]  # the numbers' own bytes, whatever their type
        path = self.folder / f"{len(self.kept)}.bin"
        h.contiguous().view(raw).numpy().tofile(str(path))
        self.kept[key] = (path, tuple(h.shape), h.dtype, raw)

    def _get(self, key):
        import torch
        v = self.kept[key]
        if not isinstance(v, tuple):
            return v
        path, shape, dtype, raw = v
        return torch.from_file(str(path), shared=False, size=math.prod(shape), dtype=raw).view(dtype).view(shape)

    def done(self):
        if self.folder:
            import shutil
            shutil.rmtree(self.folder, ignore_errors=True)

    @contextlib.contextmanager
    def use(self, ids):
        self.key = id(ids)
        self.skip = self.key in self.kept
        self.hits += self.skip
        self.misses += not self.skip
        try:
            yield
        finally:
            self.key, self.skip = None, False


def train(rows_file, name, base="t17", epochs=2.0, rank=16, lr=2e-4, max_len=1152, layers="all", accum=4, seed=0, limit=0, minutes=0, log=print,
          lean="", weight=3, foresee=False, ternary_edit=False, out_dir=None, checkpoint=True, dtype="bf16", pairs=False, beta=0.1, int8_base=False, read=0, judged=0, parent="", parent_cell="",
          trunk="", pull=0.5, gen="", fresh=2):
    """A LoRA weight edit of a ternary member from the hive's rows, on a CPU; written as a GGUF adapter the
    ternary runtime loads beside the packed base.

    parent: the edit the child starts as. trunk: the body's shared edit (training/merge.py); the child then starts
    as its parent pulled `pull` of the way toward it, so every line of descent stays part of one body.
    parent_cell: the parent's name; what that cell (and the trunk) got wrong in practice, set beside the program
    that was right, is taught to the child as a correction. gen: this generation's name; its rows are new to the
    whole line and are met `fresh` times as often as the rows the parent already learned from."""
    born = time.time()
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
    # what the child's own parent got wrong (and the trunk, the body as one), with the program that was right: the
    # child is taught the correction from where its parent stood (the wrong program, what it was shown, the verdict)
    mend = []
    for r in rows:
        wrong = str(r.get("rejected_who") or "").partition("+")[2]
        if r.get("type") == "pair" and parent_cell and wrong and (wrong == parent_cell or re.fullmatch(r"g\d+trunk", wrong)):
            mend.append({k: v for k, v in r.items() if k not in ("rejected", "rejected_who", "shown")} | {
                "type": "mend", "messages": r["messages"] + [{"role": "assistant", "content": r["rejected"]},
                                                             {"role": "user", "content": MEND.format(shown=r.get("shown") or "It ran.")}]})
    if not pairs:
        rows = [r for r in rows if r.get("type") != "pair"]
    rows += mend
    seen, uniq = set(), []
    for r in rows:  # the same exchange from two sittings teaches nothing twice
        k = json.dumps([r["messages"][1:], r["output"], r.get("rejected")])
        if k not in seen:
            seen.add(k)
            uniq.append(r)
    rows = uniq
    src = snapshot_download(UNPACKED[base])
    tok = AutoTokenizer.from_pretrained(src)
    import contextlib
    # bf16 halves the memory and is fast where the CPU has instructions for it (AVX512-BF16); elsewhere 32-bit floats
    # may be the faster way (measured by `speed`)
    half = dtype != "f32"
    if half and int8_base:
        # On a CPU without the 16-bit instructions (about one free runner in four) PyTorch's 16-bit arithmetic is 10 to
        # 16 times slower than its 32-bit, and a cell's first row took hours (three of the first twelve 8B cells were
        # lost that way, with nothing in their logs). There the whole cell is trained in 32-bit: rows have to be
        # about half as long to fit, and it is several times faster than crawling.
        from training import ternary_base
        if not ternary_base.quick16():
            half = False
            log("this CPU has no quick 16-bit arithmetic (no AVX512-BF16, no AMX): the cell is trained in 32-bit numbers", flush=True)
    cast = (lambda: torch.autocast("cpu", dtype=torch.bfloat16)) if half else contextlib.nullcontext
    from transformers import AutoConfig
    nl = AutoConfig.from_pretrained(src).num_hidden_layers
    which = (list(range(nl)) if layers == "all" else list(range(nl // 2, nl)) if layers == "top" else
             list(range(nl - int(layers[4:]), nl)) if layers.startswith("last") else list(range(*map(int, layers.split("-")))))
    cell = None
    if int8_base:
        # the frozen DNA held as what it is, ternary: one byte a weight, so a 4B or 8B DNA trains on a free runner
        # (training/ternary_base.py); the edit is the same LoRA, saved in PEFT's layout
        if ternary_edit:
            raise ValueError("--ternary is not made for --int8-base")
        from training import ternary_base
        model, cell = ternary_base.load(src, rank, 2 * rank, 0.0, which, torch.bfloat16 if half else torch.float32, log=log)
        # How long a row fits beside the DNA on this machine. Measured on the 8B (2026-11-15): 8.1 GB held, and every
        # piece of a row takes about 5 MB more while it is trained on (46 values of the hidden size for each trained
        # layer). A row that does not fit sends the machine into its swap: two of the first eight 8B cells were lost
        # that way, one runner dead, one sitting in its first long row until the job's time was up.
        import psutil
        total = psutil.virtual_memory().total / 2**30
        fits = int((total - ternary_base.held_gb() - 2.5) * 2**30 / (len(which) * model.config.hidden_size * (2 if half else 4) * 46))
        if fits < max_len:
            log(f"this machine has {total:.1f} GB: rows of up to {max(256, fits)} pieces fit beside the DNA (asked for {max_len})", flush=True)
            max_len = max(256, fits)
    else:
        model = AutoModelForCausalLM.from_pretrained(src, dtype=torch.bfloat16 if half else torch.float32)
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
    start = parent if parent and Path(parent).exists() else ""
    if trunk and Path(trunk).exists():
        # the body's shared edit pulls every line toward it: the child starts as its parent moved `pull` of the way to
        # the trunk (with no parent: as the trunk), cut exactly to the child's rank (training/merge.py)
        from training import merge
        mixed, kept = merge.merge(([merge.load(start)] if start else []) + [merge.load(trunk)], [1 - pull, pull] if start else [1.0], rank)
        GROW.mkdir(parents=True, exist_ok=True)
        start = str(GROW / f"{base}+{name}.start.safetensors")
        merge.save(mixed, start)
        log(f"the child starts as its parent pulled {pull:g} of the way to the trunk ({Path(trunk).name}); at least {kept:.3f} of every matrix is kept at rank {rank}", flush=True)
    if start:
        # the child starts as its parent: every weight of the parent's edit is copied in before training, so what
        # the parent learned (its corrections included) is the child's from the start, and training moves it on
        from safetensors.torch import load_file
        sd = load_file(start)
        got = 0
        if cell:
            for n, m in cell.layers.items():
                a, b = sd.get(f"base_model.model.{n}.lora_A.weight"), sd.get(f"base_model.model.{n}.lora_B.weight")
                if a is not None and b is not None and a.shape == m.lora_A.shape and b.shape == m.lora_B.shape:
                    m.lora_A.data.copy_(a)
                    m.lora_B.data.copy_(b)
                    got += 1
        else:
            for n, p_ in model.named_parameters():
                k = n.replace(".default", "")
                if p_.requires_grad and k in sd and sd[k].shape == p_.shape:
                    p_.data.copy_(sd[k].to(p_.dtype))
                    got += 1
        log(f"the child starts as its parent ({Path(parent).name if parent else Path(trunk).name}): {got} of its matrices inherited", flush=True)
        if not got:
            raise RuntimeError(f"the child was to start from {Path(start).name}, and none of its matrices fit this edit (rank {rank}, layers {which[0]}-{which[-1]})")
    # Each layer's inner values are worked out again on the way back instead of being kept: a third slower, and the
    # memory no longer grows with the length of a row (the first run on a 16 GB runner was killed at step 5).
    if checkpoint:
        model.gradient_checkpointing_enable()
        model.enable_input_require_grads()

    def encode(row):
        p = tok(tok.apply_chat_template(row["messages"], tokenize=False, add_generation_prompt=True, enable_thinking=False), add_special_tokens=False)["input_ids"]
        t = tok(row["output"] + "<|im_end|>\n", add_special_tokens=False)["input_ids"]
        if len(p) + len(t) > max_len:
            return None
        if row.get("rejected"):
            w = tok(row["rejected"] + "<|im_end|>\n", add_special_tokens=False)["input_ids"]
            return None if len(p) + len(w) > max_len else (torch.tensor([p + t]), len(t), torch.tensor([p + w]), len(w))
        return (torch.tensor([p + t]), len(t))
    data, mine, new_rows, long = [], 0, 0, 0
    for row in rows:
        d = encode(row)
        if d is None:
            long += 1
            continue
        # a cell that leans to an organ meets that organ's rows `weight` times as often as the others: every cell
        # learns all of the hive's checked work (so any two can check each other), each one its own part best
        own = bool(lean) and ternary.organ(row["task"]) == lean
        # this generation's rows, and its parent's corrected mistakes, are new to the whole line of descent: met
        # `fresh` times as often as rows the parent already learned from (a child inherits those with its start)
        new = (bool(gen) and row.get("gen") == gen) or row.get("type") == "mend"
        data += [d] * min(6, (weight if own else 1) * (fresh if new else 1))
        mine += own
        new_rows += new
    if limit:
        data = data[:limit]
    if lean:
        log(f"this cell leans to {lean}: {mine} of its rows are that organ's, each met {weight} times", flush=True)
    if gen or mend:
        log(f"{new_rows} rows are new to this line (generation {gen or '-'}'s own, {len(mend)} of them its parent's mistakes corrected), each met {fresh} times as often", flush=True)
    if long:
        log(f"{long} rows are longer than {max_len} pieces and are left out", flush=True)
    judged_used = 0
    if judged:
        # answers people voted on (training/raw.judged): the best-voted beside the worst-voted for the same question,
        # trained as a right-against-wrong pair, the way the hive's own pairs are
        from training import raw
        for row in raw.judged(judged, name, lean, log=log):
            d = encode(row)
            if d is not None:
                data.append(d)
                judged_used += 1
        log(f"judged: {judged_used} pairs of answers people voted on", flush=True)
    read_used = 0
    if read:
        # raw text and code from the open web (training/raw.py): three times as many drawn as are read, each measured
        # by how well the DNA already predicts it, and the middle band kept: not known yet, but learnable
        from training import raw
        drawn = raw.draw(3 * read, name, lean, log=log)
        scored = []
        model.eval()
        for row in drawn:
            ids = tok(row["text"], add_special_tokens=False)["input_ids"][:512]
            if len(ids) < 64:
                continue
            x = torch.tensor([ids])
            with torch.no_grad(), cast():
                lg = model(input_ids=x, logits_to_keep=len(ids)).logits[:, :-1, :]
                loss_r = torch.nn.functional.cross_entropy(lg.float().reshape(-1, lg.size(-1)), x[:, 1:].reshape(-1)).item()
            scored.append((loss_r, (x, len(ids) - 1)))
        model.train()
        chosen = raw.pick(scored, read)
        data += chosen
        read_used = len(chosen)
        if scored:
            ls = sorted(l for l, _ in scored)
            log(f"read: {len(drawn)} raw pieces drawn, {len(scored)} measured (the DNA's error from {ls[0]:.2f} to {ls[-1]:.2f}), "
                f"{read_used} kept from the middle band", flush=True)
    random.seed(f"{seed}:{lean}:{name}")  # two children of one organ in a generation see their rows in their own orders
    torch.manual_seed(abs(hash(lean)) % 10**6 + seed)
    log(f"{len(rows)} rows, {len(data)} within {max_len} pieces (mean {sum(d[0].shape[1] for d in data) // max(1, len(data))}); "
        f"LoRA rank {rank} on layers {which[0]}-{which[-1]} of {UNPACKED[base]}", flush=True)
    params = cell.params if cell else [p for p in model.parameters() if p.requires_grad]
    # What machine this is, and a watch over every row. Three of the first twelve 8B cells never got past their
    # first row (hours, until the job's time was up) and their logs said nothing. Now the log says which CPU this
    # is, a row that takes minutes is reported with the machine's memory, and a row that takes longer than
    # HIVE_ROW_SECONDS (25 minutes) ends the job at once, so the generation goes on with the other children.
    try:
        cpu = next((ln.split(":", 1)[1].strip() for ln in open("/proc/cpuinfo") if ln.startswith("model name")), "?")
    except OSError:
        cpu = "?"
    if int8_base:
        from training import ternary_base
        log(f"this machine: {cpu}, {os.cpu_count()} threads; trained in {'16' if half else '32'}-bit numbers", flush=True)
    else:
        log(f"this machine: {cpu}, {os.cpu_count()} threads", flush=True)
    beat = {"t": time.time(), "what": "its first row", "on": True}

    def watch():
        import faulthandler
        import psutil
        most = float(os.environ.get("HIVE_ROW_SECONDS", 1500))
        while beat["on"]:
            time.sleep(60)
            idle = time.time() - beat["t"]
            if beat["on"] and idle > 240:
                vm, sw = psutil.virtual_memory(), psutil.swap_memory()
                log(f"still in {beat['what']} after {idle:.0f} s; memory free {vm.available / 2**30:.1f} GB, swap used {sw.used / 2**30:.1f} GB, load {os.getloadavg()[0]:.1f}", flush=True)
            if beat["on"] and idle > most:
                log(f"one row has taken more than {most:.0f} s: this machine cannot train this cell. The job ends here so that the generation goes on without it.", flush=True)
                faulthandler.dump_traceback(all_threads=True)
                os._exit(3)
    import threading
    threading.Thread(target=watch, daemon=True).start()
    if minutes and data:
        # Runners differ in speed by several times. One row is timed, and the passes are cut to what fits the time
        # given (a job that runs out of time leaves nothing behind). A row of middling length: the longest one is
        # where a machine short of memory stalls, and the plan is made from the mean anyway.
        t = time.time()
        with cast():
            big = sorted(data, key=lambda d: d[0].shape[1])[len(data) // 2]
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
    # not with recomputation (checkpoint): a layer recomputed on the way back would be fed the wrong input
    prefix = (_Prefix(model, which[0], log, folder=GROW / f"{base}+{name}.prefix" if int8_base else None)
              if which[0] > 0 and not checkpoint and os.environ.get("HIVE_PREFIX_CACHE", "1") != "0" else None)
    t0, running, step, hist, paired = time.time(), 0.0, 0, [], 0
    for i, idx in enumerate(order):
        if minutes and time.time() - born > minutes * 60:
            # The plan was made from one timed row; a runner can fall behind it. Two trials were lost on 2026-11-14
            # because their jobs ran into the time limit with nothing saved. Now the cell stops here and is kept.
            log(f"time is up after {i} of {len(order)} rows: the cell is saved as it is", flush=True)
            order = order[:i]
            break
        ids, k = data[idx][:2]
        beat["t"], beat["what"] = time.time(), f"row {i + 1} of {len(order)} ({ids.shape[1]} pieces)"
        with cast(), (prefix.use(ids) if prefix else contextlib.nullcontext()):
            logits = model(input_ids=ids, logits_to_keep=k + 1).logits[:, :-1, :]
        loss = torch.nn.functional.cross_entropy(logits.float().reshape(-1, logits.size(-1)), ids[:, -k:].reshape(-1))
        if len(data[idx]) == 4:
            # a right and a wrong program for the same task: DPO, with the plain loss on the right one kept beside it
            # (Iterative RPO). The reference is the cell as it started: the DNA with its edit switched off.
            wid, wk = data[idx][2:]
            def seq(x, n, lg=None):
                if lg is None:
                    with (prefix.use(x) if prefix else contextlib.nullcontext()):
                        lg = model(input_ids=x, logits_to_keep=n + 1).logits[:, :-1, :]
                return torch.log_softmax(lg.float(), -1).gather(-1, x[:, -n:].unsqueeze(-1)).sum()
            with cast():
                good, bad = seq(ids, k, logits), seq(wid, wk)
                with torch.no_grad(), (cell.off() if cell else model.disable_adapter()):
                    ref_good, ref_bad = seq(ids, k), seq(wid, wk)
            margin = beta * ((good - ref_good) - (bad - ref_bad))
            loss = loss - torch.nn.functional.logsigmoid(margin)
            paired += 1
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
    beat["on"] = False
    work = GROW / f"{base}+{name}"
    work.mkdir(parents=True, exist_ok=True)
    if ternary_edit:
        for m in edits:
            parametrize.remove_parametrizations(m, "weight", leave_parametrized=True)
        levels = max(len(torch.unique(m.weight.detach().float())) for m in edits)
        log(f"the cell's edit is ternary: at most {levels} different values in any of its {len(edits)} matrices", flush=True)
    if cell:
        cell.save(work, src)
    else:
        model.save_pretrained(str(work))
    if prefix:
        log(f"frozen layers skipped on {prefix.hits} of {prefix.hits + prefix.misses} passes (their output kept from the first pass of each row, {prefix.bytes / 2**30:.2f} GB{' on disk' if prefix.folder else ''})", flush=True)
        prefix.done()
    meta = {"member": f"{base}+{name}", "leans": lean, "dtype": dtype, "checkpoint": bool(checkpoint), "seconds_a_row": round((time.time() - t0) / max(1, len(order)), 1), "ternary_edit": bool(ternary_edit), "foresee": bool(foresee), "pairs": paired, "int8_base": bool(int8_base), "read": read_used, "judged": judged_used, "parent": Path(parent).name if parent and Path(parent).exists() else "", "parent_cell": parent_cell, "trunk": Path(trunk).name if trunk and Path(trunk).exists() else "", "mended": len(mend), "new_rows": new_rows, "base": UNPACKED[base], "rows": len(rows), "used": len(data), "epochs": epochs, "rank": rank, "lr": lr,
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
    if cmd == "dream":
        print(json.dumps(dream(opt("--seed", int(time.time() // 60)), opt("--tasks", 4), opt("--failures", ""), opt("--out", ""), minutes=opt("--minutes", 0))))
    elif cmd == "practice":
        print(json.dumps(practice(opt("--seed", 10_000_000 + int(time.time() // 60)), opt("--tasks", 16), opt("--level", "mixed"), opt("--out", ""), minutes=opt("--minutes", 0))))
    elif cmd == "gather":
        # python training/grow.py gather --gen g25 --out out/rows.jsonl --old old.jsonl [--old more.jsonl] new1.jsonl new2.jsonl ...
        olds = [argv[i + 1] for i, a in enumerate(argv) if a == "--old" and i + 1 < len(argv)]
        skip = {i + 1 for i, a in enumerate(argv) if a in ("--old", "--gen", "--out")}
        news = [a for i, a in enumerate(argv[1:], 1) if not a.startswith("--") and i not in skip]
        before, added = gather(opt("--out", str(GROW / "rows.jsonl")), opt("--gen", ""), olds, news)
        print(f"rows: {before} from earlier generations, {added} new in generation {opt('--gen', '')}")
    elif cmd == "rows":
        out = opt("--out", str(GROW / "rows.jsonl"))
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        print(rows_from([a for a in argv[1:] if not a.startswith("--") and a != out], out), "rows added to", out)
    elif cmd == "train":
        print(json.dumps(train(opt("--rows", str(GROW / "rows.jsonl")), opt("--name", "gen"), opt("--base", "t17"), opt("--epochs", 2.0), opt("--rank", 16),
                               opt("--lr", 2e-4), opt("--max-len", 1152), opt("--layers", "all"), limit=opt("--limit", 0), minutes=opt("--minutes", 0), lean=opt("--lean", ""), weight=opt("--weight", 3), foresee="--foresee" in argv, pairs="--pairs" in argv, int8_base="--int8-base" in argv, read=opt("--read", 0), judged=opt("--judged", 0), parent=opt("--parent", ""), parent_cell=opt("--parent-cell", ""), trunk=opt("--trunk", ""), pull=opt("--pull", 0.5), gen=opt("--gen", ""), fresh=opt("--fresh", 2), ternary_edit="--ternary" in argv, checkpoint="--no-checkpoint" not in argv, dtype=opt("--dtype", "bf16")), indent=1))
    elif cmd == "speed":
        # how long one row takes on this machine, each way of training: so that the fastest is used and not guessed
        rows, out = opt("--rows", str(GROW / "rows.jsonl")), []
        for dtype, layers, ck in (("bf16", "all", True), ("bf16", "all", False), ("bf16", "last14", False), ("f32", "all", False), ("f32", "last14", False)):
            p = subprocess.run([sys.executable, __file__, "train", "--rows", rows, "--name", "speed", "--limit", "6", "--epochs", "1", "--dtype", dtype,
                                "--layers", layers, "--base", opt("--base", "t17")] + ([] if ck else ["--no-checkpoint"]), capture_output=True, text=True)
            try:
                m = json.loads(p.stdout[p.stdout.rindex("\n{"):])
                out.append({"dtype": dtype, "layers": layers, "checkpoint": ck, "seconds_a_row": m["seconds_a_row"], "memory_gb": m["memory_gb"], "loss_last": m["loss_last"]})
            except (ValueError, KeyError):
                out.append({"dtype": dtype, "layers": layers, "checkpoint": ck, "failed": (p.stderr or p.stdout)[-200:]})
            print(json.dumps(out[-1]), flush=True)
        for f in (ROOT / "cells" / "members").glob("*+speed.*"):
            f.unlink()
    elif cmd == "fetch":
        print(fetch([a for a in argv[1:] if not a.startswith("--")]))
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
