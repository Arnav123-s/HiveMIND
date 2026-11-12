# Muse's work — written by Muse, on Muse's side. Fable's HiveMIND was read read-only; nothing on Fable's side was touched.

"""Half-size control driver (2026-11-12, ordered after Fable's critique relayed by Arnav):
plain_half and ste_half, seeds 0-2, 8 minutes each, one process at a time. The question:
layered_half (2 blocks, 5 levels) beat the full-width arms — was that the five levels, or
just the ~161 steps a half-size model gets in 8 minutes vs ~115-121 at full width?
plain_half has the same size and step count with 3 levels; ste_half checks whether the
gradient way also gains from half size. Refuses to run alongside another heavy job and
refuses to start a run that could not finish before the hard stop (10:35 PT = 18:35 UTC,
so growth cycle 6 at ~10:50 PT gets a free lab). Events go to sweep.log; results land
in runs.jsonl via train.py."""
import json, os, subprocess, time
from datetime import datetime, timezone
from pathlib import Path

LAB = Path(__file__).resolve().parent
PY = str(Path.home() / "workspace/edit-lab/fable-validation/venv/bin/python")
DEADLINE = datetime(2026, 11, 12, 18, 35, tzinfo=timezone.utc).timestamp()
MINUTES = 8.0
JOBS = ([("plain_half", s) for s in (0, 1, 2)]
        + [("ste_half", s) for s in (0, 1, 2)])

def log(msg):
    line = f"[sweep {datetime.now(timezone.utc).strftime('%H:%M:%S')}Z] halfctl: {msg}"
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

b = busy()
while b:
    log(f"another heavy job is running ({b}); waiting 60 s")
    time.sleep(60)
    b = busy()
log("machine free; starting half-control runs")
for arm, seed in JOBS:
    if (arm, seed) in done_jobs():
        log(f"skip {arm} s{seed}: already recorded")
        continue
    need = MINUTES * 60 + 150
    if time.time() + need > DEADLINE:
        log(f"STOP: not enough time before 10:35 PT for {arm} s{seed}; remaining jobs dropped")
        break
    b = busy()
    while b:
        log(f"another heavy job appeared ({b}); waiting 60 s")
        time.sleep(60)
        b = busy()
    log(f"run {arm} seed {seed}")
    env = {"OMP_NUM_THREADS": "2", "MKL_NUM_THREADS": "2", "PATH": "/usr/bin:/bin:/usr/local/bin",
           "HOME": os.environ.get("HOME", "/home/hatch"), "LANG": "C.UTF-8"}
    r = subprocess.run([PY, "train.py", "--arm", arm, "--seed", str(seed), "--minutes", str(MINUTES)],
                       cwd=LAB, env=env, capture_output=True, text=True)
    tail = [l for l in r.stdout.splitlines() if l.startswith("RESULT")]
    log(f"done {arm} s{seed} rc={r.returncode} {tail[-1] if tail else r.stderr[-300:]}")
log("half-control runs finished")
