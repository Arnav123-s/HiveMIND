# Muse's work — written by Muse, on Muse's side. Fable's HiveMIND was read read-only; nothing on Fable's side was touched.

"""Scale ladder driver (2026-11-12, Arnav's question): does the champion recipe
(layered vote trainer + rotary) get better PER BYTE as the model grows?
Every run: --steps 56 (batch 32 x CTX 256 = 458,752 tokens, identical for all rungs),
same corpus, same held set, seeds fixed per job. One process at a time; refuses to run
alongside another heavy job; skips runs already in runs.jsonl; never starts a run that
would straddle the ~22:50 PT (06:50 UTC) growth-cycle window. Events -> sweep.log,
results -> runs.jsonl via train.py. Job order puts the required minimums first
(2M x3 seeds, 10M x2, 50M x1), then the plain+rotary ride-along at 2M, the 0.9M
calibration at ladder steps, then the extra seeds (10M s2, 50M s1)."""
import json, os, subprocess, time
from datetime import datetime, timezone, timedelta
from pathlib import Path

LAB = Path(__file__).resolve().parent
PY = str(Path.home() / "workspace/edit-lab/fable-validation/venv/bin/python")
STEPS = 56

# (arm, label, extra train.py args, seed, est total seconds incl. evals+startup, minutes cap)
def job(arm, tag, extra, seed, est, minutes):
    label = arm + "_rope" + (("_" + tag) if tag else "")
    return (arm, label, extra + ["--tag", tag] if tag else extra, seed, est, minutes)

JOBS = []
for s in (0, 1, 2):   # ~2M rung: dim 288, 2 blocks -> 1,990,656 ternary weights
    JOBS.append(job("layered", "scale2m", ["--dim", "288", "--layers-n", "2"], s, 330, 12))
for s in (0, 1):      # ~10M rung: dim 512, 3 blocks -> 9,437,184
    JOBS.append(job("layered", "scale10m", ["--dim", "512", "--layers-n", "3"], s, 900, 25))
# ~50M rung: dim 768, 7 blocks -> 49,545,216; --ckpt or it does not fit this VM (OOM at 5.7 GB)
JOBS.append(job("layered", "scale50m", ["--dim", "768", "--layers-n", "7", "--ckpt"], 0, 5100, 115))
for s in (0, 1, 2):   # ride-along: plain votes + rotary at the 2M rung, same size/steps
    JOBS.append(job("plain", "scale2m", ["--dim", "288", "--layers-n", "2"], s, 330, 12))
# 0.9M calibration: the record rung's config at the ladder's step budget (NOT a re-run of the record)
JOBS.append(job("layered_half", "laddercal", [], 0, 240, 8))
JOBS.append(job("layered", "scale10m", ["--dim", "512", "--layers-n", "3"], 2, 900, 25))       # extra seed
JOBS.append(job("layered", "scale50m", ["--dim", "768", "--layers-n", "7", "--ckpt"], 1, 5100, 115))  # extra seed

def log(msg):
    line = f"[sweep {datetime.now(timezone.utc).strftime('%H:%M:%S')}Z] ladder: {msg}"
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

def cycle_window():
    """Next ~06:50 UTC growth-cycle start; returns (block_from, block_until) timestamps:
    no run may be scheduled to end inside [cycle-10min, cycle+35min]."""
    now = datetime.now(timezone.utc)
    cyc = now.replace(hour=6, minute=50, second=0, microsecond=0)
    if cyc.timestamp() < now.timestamp() - 35 * 60:
        cyc += timedelta(days=1)
    return cyc.timestamp() - 600, cyc.timestamp() + 35 * 60

HARD_STOP = datetime.now(timezone.utc).replace(hour=10, minute=30, second=0, microsecond=0).timestamp()
if HARD_STOP < time.time():
    HARD_STOP += 86400

log(f"ladder driver up: {len(JOBS)} jobs, steps={STEPS} ({STEPS*32*256} tokens per run)")
for arm, label, extra, seed, est, minutes in JOBS:
    if (label, seed) in done_jobs():
        log(f"skip {label} s{seed}: already recorded")
        continue
    # growth-cycle window guard
    while True:
        bf, bu = cycle_window()
        now = time.time()
        if now + est > bf and now < bu:
            if bu > HARD_STOP:
                log(f"DROP {label} s{seed}: would straddle the growth window and pass the hard stop")
                break
            log(f"waiting out the growth-cycle window before {label} s{seed}")
            time.sleep(120)
            continue
        break
    else:
        continue
    if time.time() > HARD_STOP:
        log(f"DROP {label} s{seed}: past hard stop")
        continue
    while busy():
        log(f"another heavy job is running ({busy()}); waiting 120 s")
        time.sleep(120)
    log(f"run {label} seed {seed} (est {est}s)")
    env = {"OMP_NUM_THREADS": "2", "MKL_NUM_THREADS": "2", "PATH": "/usr/bin:/bin:/usr/local/bin",
           "HOME": os.environ.get("HOME", "/home/hatch"), "LANG": "C.UTF-8"}
    try:
        r = subprocess.run([PY, "train.py", "--arm", arm, "--rope", "--seed", str(seed),
                            "--steps", str(STEPS), "--minutes", str(minutes)] + extra,
                           cwd=LAB, env=env, capture_output=True, text=True, timeout=int(est * 1.8) + 300)
        tail = [l for l in r.stdout.splitlines() if l.startswith("RESULT")]
        log(f"done {label} s{seed} rc={r.returncode} {tail[-1] if tail else r.stderr[-300:]}")
    except subprocess.TimeoutExpired:
        log(f"TIMEOUT {label} s{seed} after {int(est * 1.8) + 300}s — moving on")
log("ladder runs finished")
