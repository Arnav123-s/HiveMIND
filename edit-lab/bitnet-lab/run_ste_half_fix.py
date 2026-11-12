# Muse's work — written by Muse, on Muse's side. Fable's HiveMIND was read read-only; nothing on Fable's side was touched.

"""Relaunch of ste_half only (2026-11-12): the first attempt crashed instantly on all three
seeds — train.py's n_tern line branched on arm != "ste", sending ste_half into the vote
trainers' state path (STE has no .t/.t1). One-line fix applied and import-verified; the
plain_half records were written before the crash and are unaffected. Same discipline:
8 minutes per seed, threads pinned, a seed starts only if it can finish by 18:34 UTC
(hard stop 10:35 PT, growth cycle 6 needs a free lab)."""
import json, os, subprocess, time
from datetime import datetime, timezone
from pathlib import Path

LAB = Path(__file__).resolve().parent
PY = str(Path.home() / "workspace/edit-lab/fable-validation/venv/bin/python")
DEADLINE = datetime(2026, 11, 12, 18, 34, tzinfo=timezone.utc).timestamp()
MINUTES = 8.0

def log(msg):
    line = f"[sweep {datetime.now(timezone.utc).strftime('%H:%M:%S')}Z] halfctl-fix: {msg}"
    print(line, flush=True)
    with open(LAB / "sweep.log", "a") as f:
        f.write(line + "\n")

def done_jobs():
    f = LAB / "runs.jsonl"
    return {(json.loads(l)["arm"], json.loads(l)["seed"]) for l in f.read_text().splitlines() if l.strip()}

for seed in (0, 1, 2):
    if ("ste_half", seed) in done_jobs():
        log(f"skip ste_half s{seed}: already recorded")
        continue
    if time.time() + MINUTES * 60 + 120 > DEADLINE:
        log(f"STOP: ste_half s{seed} cannot finish by 10:35 PT; dropped")
        break
    log(f"run ste_half seed {seed}")
    env = {"OMP_NUM_THREADS": "2", "MKL_NUM_THREADS": "2", "PATH": "/usr/bin:/bin:/usr/local/bin",
           "HOME": os.environ.get("HOME", "/home/hatch"), "LANG": "C.UTF-8"}
    r = subprocess.run([PY, "train.py", "--arm", "ste_half", "--seed", str(seed), "--minutes", str(MINUTES)],
                       cwd=LAB, env=env, capture_output=True, text=True)
    tail = [l for l in r.stdout.splitlines() if l.startswith("RESULT")]
    log(f"done ste_half s{seed} rc={r.returncode} {tail[-1] if tail else r.stderr[-300:]}")
log("ste_half relaunch finished")
