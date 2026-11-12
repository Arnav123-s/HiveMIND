# Muse's work — built and run by Muse on Muse's side of the lab. Fable's HiveMIND was read read-only for the mechanism; nothing on Fable's side was touched or used.

"""Sequential sweep driver. Runs arms in the task's priority order, one process at a time.
Refuses to start a run while another heavy job (the composites `team` process) is alive, and
refuses to start a run that could not finish before the hard stop (22:15 PT = 06:15 UTC)."""
import json, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

LAB = Path(__file__).resolve().parent
PY = str(Path.home() / "workspace/edit-lab/fable-validation/venv/bin/python")
DEADLINE = datetime(2026, 11, 12, 6, 15, tzinfo=timezone.utc).timestamp()
MINUTES = 8.0
JOBS = ([("plain", s) for s in (0, 1, 2)] + [("ste", s) for s in (0, 1, 2)]
        + [("mag", s) for s in (0, 1, 2)]
        + [("layered", s) for s in (0, 1, 2)] + [("layered_half", s) for s in (0, 1, 2)]
        + [("anneal", s) for s in (0, 1, 2)])

def log(msg):
    print(f"[sweep {datetime.now(timezone.utc).strftime('%H:%M:%S')}Z] {msg}", flush=True)

def busy():
    out = subprocess.run(["pgrep", "-fc", "python -m team"], capture_output=True, text=True).stdout.strip()
    return out.isdigit() and int(out) > 0

def done_jobs():
    f = LAB / "runs.jsonl"
    if not f.exists():
        return set()
    return {(json.loads(l)["arm"], json.loads(l)["seed"]) for l in f.read_text().splitlines() if l.strip()}

while busy():
    log("another heavy job is running; waiting 120 s")
    time.sleep(120)
log("machine free; starting sweep")
for arm, seed in JOBS:
    if (arm, seed) in done_jobs():
        log(f"skip {arm} s{seed}: already recorded")
        continue
    need = MINUTES * 60 + 150
    if time.time() + need > DEADLINE:
        log(f"STOP: not enough time before 22:15 PT for {arm} s{seed}; remaining jobs dropped")
        break
    while busy():
        log("another heavy job appeared; waiting 120 s")
        time.sleep(120)
    log(f"run {arm} seed {seed}")
    import os
    env = {"OMP_NUM_THREADS": "2", "MKL_NUM_THREADS": "2", "PATH": "/usr/bin:/bin:/usr/local/bin",
           "HOME": os.environ.get("HOME", "/home/hatch"), "LANG": "C.UTF-8"}
    r = subprocess.run([PY, "train.py", "--arm", arm, "--seed", str(seed), "--minutes", str(MINUTES)],
                       cwd=LAB, env=env, capture_output=True, text=True)
    tail = [l for l in r.stdout.splitlines() if l.startswith("RESULT")]
    log(f"done {arm} s{seed} rc={r.returncode} {tail[-1] if tail else r.stderr[-300:]}")
log("sweep finished")
