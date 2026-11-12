# Muse's work — written by Muse, on Muse's side. Fable's HiveMIND was read read-only; nothing on Fable's side was touched.

"""RoPE test driver (2026-11-11, Arnav's order): layered_half + rotary positions Fable's way,
seeds 0-2, 8 minutes each, one process at a time. Refuses to run alongside another heavy job
and refuses to start a run that could not finish before the hard stop (04:15 PT = 12:15 UTC).
Events are appended to sweep.log, results land in runs.jsonl via train.py."""
import json, os, subprocess, time
from datetime import datetime, timezone
from pathlib import Path

LAB = Path(__file__).resolve().parent
PY = str(Path.home() / "workspace/edit-lab/fable-validation/venv/bin/python")
DEADLINE = datetime(2026, 11, 12, 12, 15, tzinfo=timezone.utc).timestamp()
MINUTES = 8.0
JOBS = [("layered_half", s) for s in (0, 1, 2)]

def log(msg):
    line = f"[sweep {datetime.now(timezone.utc).strftime('%H:%M:%S')}Z] rope: {msg}"
    print(line, flush=True)
    with open(LAB / "sweep.log", "a") as f:
        f.write(line + "\n")

def busy():
    for pat in ("growth_cycle", "python -m team", "bitnet-lab/train.py"):
        out = subprocess.run(["pgrep", "-fc", pat], capture_output=True, text=True).stdout.strip()
        if out.isdigit() and int(out) > 0:
            return pat
    return None

def done_jobs():
    f = LAB / "runs.jsonl"
    if not f.exists():
        return set()
    return {(json.loads(l)["arm"], json.loads(l)["seed"]) for l in f.read_text().splitlines() if l.strip()}

while busy():
    log(f"another heavy job is running ({busy()}); waiting 120 s")
    time.sleep(120)
log("machine free; starting rope runs")
for arm, seed in JOBS:
    if (arm + "_rope", seed) in done_jobs():
        log(f"skip {arm}_rope s{seed}: already recorded")
        continue
    need = MINUTES * 60 + 180
    if time.time() + need > DEADLINE:
        log(f"STOP: not enough time before 04:15 PT for {arm}_rope s{seed}; remaining jobs dropped")
        break
    while busy():
        log(f"another heavy job appeared ({busy()}); waiting 120 s")
        time.sleep(120)
    log(f"run {arm}_rope seed {seed}")
    env = {"OMP_NUM_THREADS": "2", "MKL_NUM_THREADS": "2", "PATH": "/usr/bin:/bin:/usr/local/bin",
           "HOME": os.environ.get("HOME", "/home/hatch"), "LANG": "C.UTF-8"}
    r = subprocess.run([PY, "train.py", "--arm", arm, "--rope", "--seed", str(seed), "--minutes", str(MINUTES)],
                       cwd=LAB, env=env, capture_output=True, text=True)
    tail = [l for l in r.stdout.splitlines() if l.startswith("RESULT")]
    log(f"done {arm}_rope s{seed} rc={r.returncode} {tail[-1] if tail else r.stderr[-300:]}")
log("rope runs finished")
