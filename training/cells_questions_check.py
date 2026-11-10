"""Old and new order cells as served (llama.cpp), and the order group as the guard uses it, before and after.

    python training/cells_questions_check.py <old git commit> <old guard.py copy> [skills...]
Per cell: test set and held-out questions, old cell rebuilt from <old commit>, new cell from cells/adapters.
Group: parser AND the five cells on the held-out orders (training/evals/orders_heldout.json) and held-out questions:
exact set, false approvals (a kind treated as ordered that was not), missed orders (the guard then asks Arnav).
Writes training/reports/cells/questions_served.json.
"""
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from team.cells import runtime, skills as S  # noqa: E402
from team.guard import parse_orders  # noqa: E402
from training import cells as C  # noqa: E402
from training.cells_promote import hf_dir  # noqa: E402

KINDS = ("spend", "delete", "send", "login", "signup")
GG = runtime.GGUF


def gguf_from_commit(commit, skill, out):
    d = Path(tempfile.mkdtemp())
    for f in ("adapter_model.safetensors", "adapter_config.json"):
        (d / f).write_bytes(subprocess.run(["git", "show", f"{commit}:cells/adapters/{skill}/{f}"], cwd=ROOT,
                                           capture_output=True, check=True).stdout)
    env = {"PYTHONPATH": f"{ROOT}/training/llama_cpp_convert/gguf-py:{ROOT}/training/llama_cpp_convert", "PATH": "/usr/bin:/bin"}
    subprocess.run([sys.executable, str(ROOT / "training/llama_cpp_convert/convert_lora_to_gguf.py"), str(d), "--base",
                    hf_dir("smol135"), "--outfile", str(out), "--outtype", "f32"], check=True, capture_output=True,
                   env=env | {k: v for k, v in __import__("os").environ.items() if k.startswith(("HF_", "HOME"))})


def acc(skill, rows):
    return round(sum(runtime.run(skill, x) == y for x, y in rows) / len(rows), 4)


def group(parser, cases):
    exact = fa = miss = 0
    for text, gold in cases:
        gold = set(gold)
        got = {k for k in KINDS if runtime.run(f"orders_{k}", text) == "yes"} & (set(parser(text)) & set(KINDS))
        exact += got == gold
        fa += len(got - gold)
        miss += len(gold - got)
    return {"exact": round(exact / len(cases), 3), "false_approvals": fa, "missed_orders": miss, "n": len(cases)}


if __name__ == "__main__":
    commit, old_guard = sys.argv[1], sys.argv[2]
    skills = sys.argv[3:]
    spec = importlib.util.spec_from_file_location("team.guard_before", old_guard)
    og = importlib.util.module_from_spec(spec)
    og.__package__ = "team"
    spec.loader.exec_module(og)
    held = [(c["text"], c["orders"]) for c in json.loads((ROOT / "training/evals/orders_heldout.json").read_text())]
    qs = S._orders_q_rows("test")
    out = {"cells": {}, "group": {}}
    keep = Path(tempfile.mkdtemp())
    for skill in skills:  # set the new files aside; old ones built from the commit
        shutil.copy(GG / f"{skill}.gguf", keep / f"{skill}.gguf")
        gguf_from_commit(commit, skill, keep / f"{skill}.old.gguf")
    for which in ("old", "new"):
        for skill in skills:
            shutil.copy(keep / (f"{skill}.old.gguf" if which == "old" else f"{skill}.gguf"), GG / f"{skill}.gguf")
        runtime.unload()
        runtime._state["lora"].clear()
        for skill in skills:
            kind = skill.split("_", 1)[1]
            _, _, te = C.data(skill)
            q = [(t, "yes" if kind in k else "no") for t, k in qs]
            out["cells"].setdefault(skill, {})[which] = {"test": acc(skill, te), "questions": acc(skill, q)}
            print(skill, which, out["cells"][skill][which], flush=True)
        parser = og.parse_orders if which == "old" else parse_orders
        out["group"][which] = {"held_out_orders": group(parser, held), "held_out_questions": group(parser, qs)}
        print("group", which, out["group"][which], flush=True)
    for skill in skills:  # leave the new files in place
        shutil.copy(keep / f"{skill}.gguf", GG / f"{skill}.gguf")
    runtime.unload()
    (C.REPORTS / "questions_served.json").write_text(json.dumps(out, indent=1))
