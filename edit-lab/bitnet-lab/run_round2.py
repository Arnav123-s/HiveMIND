# Muse's work — written by Muse, on Muse's side. Fable's HiveMIND was read read-only; nothing on Fable's side was touched.

"""Round-2 driver (2026-11-12, Arnav's order: find how to make BitNets better, work on BitNets).
Two one-change levers on the best stack (layered_half + rope + plain votes, baseline held
2.8580 +- 0.0161), 3 seeds x 8 minutes each, one process at a time:
  layered_half_rope_carry    — overshoot carry in the layered vote counters
  layered_half_rope_cooldown — two-stage lr/wd cooldown on the AdamW parts (vote rule fixed)
Lab discipline: never start before 11:05 PT (the half-size control owns the lab until ~10:35
and growth cycle 6 ~10:50-11:05), never overlap another heavy job, give up entirely if the
first run cannot start by 12:00 PT, and never start a run that cannot finish by the 13:00 PT
hard stop. Events are appended to sweep.log; results land in runs.jsonl via train.py."""
import json, os, subprocess, time
from datetime import datetime, timezone
from pathlib import Path

LAB = Path(__file__).resolve().parent
PY = str(Path.home() / "workspace/edit-lab/fable-validation/venv/bin/python")
START_AFTER = datetime(2026, 11, 12, 19, 5, tzinfo=timezone.utc).timestamp()   # 11:05 PT
GIVE_UP = datetime(2026, 11, 12, 20, 0, tzinfo=timezone.utc).timestamp()       # 12:00 PT
DEADLINE = datetime(2026, 11, 12, 21, 0, tzinfo=timezone.utc).timestamp()      # 13:00 PT
MINUTES = 8.0
JOBS = [("layered_half", ["--rope", "--carry"], "layered_half_rope_carry", s) for s in (0, 1, 2)] + \
       [("layered_half", ["--rope", "--cooldown"], "layered_half_rope_cooldown", s) for s in (0, 1, 2)]
LOCK = Path.home() / "workspace/edit-lab/growth/.growth.lock"

def log(msg):
    line = f"[sweep {datetime.now(timezone.utc).strftime('%H:%M:%S')}Z] round2: {msg}"
    print(line, flush=True)
    with open(LAB / "sweep.log", "a") as f:
        f.write(line + "\n")

def busy():
    for pat in ("growth_cycle", "train.py", "run_half_control", "run_sweep", "run_rope.py",
                "python -m team"):
        out = subprocess.run(["pgrep", "-fc", pat], capture_output=True, text=True).stdout.strip()
        if out.isdigit() and int(out) > 0:
            return pat
    if LOCK.exists() and time.time() - LOCK.stat().st_mtime < 1800:
        return "growth lock (fresh)"
    return None

def done_jobs():
    f = LAB / "runs.jsonl"
    if not f.exists():
        return set()
    return {(json.loads(l)["arm"], json.loads(l)["seed"]) for l in f.read_text().splitlines() if l.strip()}

started = False
while time.time() < START_AFTER or busy():
    if not started and time.time() > GIVE_UP:
        log("GIVE UP: lab never freed by 12:00 PT; round 2 not started")
        raise SystemExit(0)
    why = "before 11:05 PT" if time.time() < START_AFTER else f"another heavy job is running ({busy()})"
    log(f"waiting: {why}; recheck in 60 s")
    time.sleep(60)
log("lab free and past 11:05 PT; starting round-2 runs")
for arm, flags, label, seed in JOBS:
    if (label, seed) in done_jobs():
        log(f"skip {label} s{seed}: already recorded")
        continue
    need = MINUTES * 60 + 180
    if time.time() + need > DEADLINE:
        log(f"STOP: not enough time before 13:00 PT for {label} s{seed}; remaining jobs dropped")
        break
    while busy():
        if not started and time.time() > GIVE_UP:
            log("GIVE UP: lab never freed by 12:00 PT; round 2 not started")
            raise SystemExit(0)
        log(f"another heavy job appeared ({busy()}); waiting 60 s")
        time.sleep(60)
    log(f"run {label} seed {seed}")
    env = {"OMP_NUM_THREADS": "2", "MKL_NUM_THREADS": "2", "PATH": "/usr/bin:/bin:/usr/local/bin",
           "HOME": os.environ.get("HOME", "/home/hatch"), "LANG": "C.UTF-8"}
    r = subprocess.run([PY, "train.py", "--arm", arm] + flags + ["--seed", str(seed),
                       "--minutes", str(MINUTES)], cwd=LAB, env=env, capture_output=True, text=True)
    started = True
    tail = [l for l in r.stdout.splitlines() if l.startswith("RESULT")]
    log(f"done {label} s{seed} rc={r.returncode} {tail[-1] if tail else r.stderr[-300:]}")
log("round-2 runs finished")
