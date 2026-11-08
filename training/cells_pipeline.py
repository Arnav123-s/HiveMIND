"""Every skill, one job at a time: probe -> locator's pick -> controls (top-K by |W*grad|, random K, all) -> promote.

    python training/cells_pipeline.py <skill> [...] [--random-for a,b,c]
"""
import json
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from training import cells as C  # noqa: E402
from training.cells_view import locator_pick  # noqa: E402
from team.cells import skills as S  # noqa: E402

TEXT_STEPS, LABEL_STEPS = 200, 100
args = [a for a in sys.argv[1:] if not a.startswith("--")]
rand_for = set(next((a.split("=", 1)[1].split(",") for a in sys.argv if a.startswith("--random-for=")), []))
log = C.REPORTS / "locator_log.jsonl"

for skill in args:
    probe_file = C.REPORTS / f"probe_{skill}_smol135.json"
    if not probe_file.exists():
        C.probe(skill, "smol135")
    p = json.loads(probe_file.read_text())
    why = locator_pick(p)
    keys = sorted(why, key=lambda m: (int(m.split(":")[0]), m))
    K = len(keys)
    steps = LABEL_STEPS if "labels" in S.SKILLS[skill] else TEXT_STEPS
    with open(log, "a") as f:
        f.write(json.dumps({"skill": skill, "picked": why}) + "\n")
    done = {d.name for d in (C.CELLS / "variants" / skill).glob("*") if (d / "result.json").exists()}
    every = [f"{i}:{m}" for i in range(len(p["knockout"]) // 2) for m in C.MODS]
    mlp = [k for k in every if k.split(":")[1] in C.MODS[4:]]
    # MLP-only (rank 2) was a candidate for the first skills and never won on test: dropped to save CPU
    plan = [("pick", keys, 8, None), ("thin", keys, 8, 2), ("all_r2", every, 2, None)]
    if skill in rand_for:  # controls for the locator: same number of modules at random, and everything at rank 8
        plan += [(f"random{K}", random.Random(7).sample(every, K), 8, None), ("all_r8", every, 8, None)]
    if "base" not in done:
        C.eval_base(skill, "smol135")
    for tag, ks, r, thin in plan:
        if tag not in done:
            C.train(skill, "smol135", ks, rank=r, steps=steps, tag=tag, thin=thin)
    subprocess.run([sys.executable, str(ROOT / "training" / "cells_promote.py"), skill, "--no-runtime"], check=False)
    print(f"=== {skill} finished", flush=True)
