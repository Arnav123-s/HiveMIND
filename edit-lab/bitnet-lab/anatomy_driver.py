# Muse's work — Muse's side
"""Anatomy driver (J-022/J-013/J-047): runs eval_anatomy.py --run for the 9
seed-matched configs, ONE at a time, and only while the lab is free.
Busy = any of: run_scale_ladder, growth_cycle, screen.py, sweep_probe,
preflight, train.py / train_next.py / run_overlap processes. Never kills or
preempts anything; waits 60 s between checks; requires 2 consecutive clear
checks before starting a run; re-checks before every run. Step counts are the
filed runs.jsonl step counts for the same (arm, seed), so each run replays its
filed run's budget exactly (batch stream depends only on seed + step index)."""
import subprocess, time
from datetime import datetime, timezone
from pathlib import Path

LAB = Path(__file__).resolve().parent
PY = str(Path.home() / "workspace/edit-lab/fable-validation/venv/bin/python")
PATTERNS = ["run_scale_ladder", "growth_cycle", "screen.py", "sweep_probe",
            "preflight.py", "train.py", "train_next.py",
            "run_overlap", "mill/screen"]
JOBS = [("layered_half", True, 0, 154), ("layered_half", True, 1, 170),
        ("layered_half", True, 2, 168),
        ("plain_half", False, 0, 150), ("plain_half", False, 1, 158),
        ("plain_half", False, 2, 176),
        ("ste_half", False, 0, 161), ("ste_half", False, 1, 163),
        ("ste_half", False, 2, 154)]

def log(msg):
    line = f"[anatomy {datetime.now(timezone.utc).strftime('%H:%M:%S')}Z] {msg}"
    print(line, flush=True)
    with open(LAB / "anatomy-driver.log", "a") as f:
        f.write(line + "\n")

def busy():
    for pat in PATTERNS:
        r = subprocess.run(["pgrep", "-fc", pat], capture_output=True, text=True)
        out = r.stdout.strip()
        if out.isdigit() and int(out) > 0:
            return pat
    return None

def wait_clear(tag):
    clears = 0
    while clears < 2:
        b = busy()
        if b:
            if clears or True:
                log(f"{tag}: lab busy ({b}); waiting 60 s")
            clears = 0
            time.sleep(60)
        else:
            clears += 1
            if clears < 2:
                time.sleep(60)
    log(f"{tag}: lab clear")

for arm, rope, seed, steps in JOBS:
    label = arm + ("_rope" if rope else "")
    done_file = LAB / "anatomy_runs" / f"{label}_s{seed}.json"
    if done_file.exists():
        log(f"skip {label} s{seed}: already done")
        continue
    wait_clear(f"{label} s{seed}")
    log(f"run {label} seed {seed} steps {steps}")
    import os
    env = dict(os.environ, OMP_NUM_THREADS="2", MKL_NUM_THREADS="2")
    cmd = [PY, "eval_anatomy.py", "--run", "--arm", arm, "--seed", str(seed),
           "--steps", str(steps), "--minutes-cap", "120"]
    if rope:
        cmd.append("--rope")
    r = subprocess.run(cmd, cwd=LAB, env=env, capture_output=True, text=True)
    tail = [l for l in r.stdout.splitlines() if l.startswith("ANATOMY_RESULT")]
    log(f"done {label} s{seed} rc={r.returncode} {tail[-1] if tail else r.stderr[-400:]}")
log("all anatomy runs finished")
