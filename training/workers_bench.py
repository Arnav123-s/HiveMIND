"""Several jobs at once: wall time and peak memory, one worker vs two.

    python training/workers_bench.py            # both modes, each in its own process
    python training/workers_bench.py one 1      # one mode (what the parent runs)
The same three jobs (a web lookup, a calculation, a short draft: none of them is a hive bench task) are submitted to a
Swarm with workers=1 (one after another) and with workers=2 (two at once, sharing every loaded model and taking turns
on the CPU). Each mode runs in a fresh process, so both pay the same model loading. Peak memory: the process's peak
resident size (VmHWM, includes the memory-mapped model files it touched) and the peak rise of the machine's used
memory. Writes training/reports/workers.json.
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "training" / "reports" / "workers.json"
JOBS = ["What is the latest version of the numpy package on PyPI?",
        "How many seconds are there in 3.5 hours?",
        "Write a two-line reminder to water the plants on Saturday."]


def used_gb():
    m = {ln.split(":")[0]: int(ln.split()[1]) for ln in open("/proc/meminfo")}
    return (m["MemTotal"] - m["MemAvailable"]) / 1e6


def one(workers):
    from team import sdk
    base, peak, done = used_gb(), [0.0], threading.Event()

    def sample():
        while not done.is_set():
            peak[0] = max(peak[0], used_gb() - base)
            time.sleep(0.5)
    threading.Thread(target=sample, daemon=True).start()
    sw = sdk.Swarm(root=Path(tempfile.mkdtemp(prefix="workers_bench_")), workers=workers)
    t = time.time()
    jobs = [sw.submit(task) for task in JOBS]
    for j in jobs:
        j.wait()
    wall = time.time() - t
    done.set()
    hwm = next(int(ln.split()[1]) for ln in open("/proc/self/status") if ln.startswith("VmHWM")) / 1e6
    res = {"workers": workers, "wall_s": round(wall, 1), "peak_rss_gb": round(hwm, 2),
           "peak_used_rise_gb": round(peak[0], 2),
           "jobs": [{"task": j.task, "status": j.status, "seconds": round(j.finished - j.created, 1),
                     "unmet": j.unmet, "dir": str(j.dir)} for j in jobs]}
    print(json.dumps(res))


def main():
    out = {}
    for w in (1, 2):
        p = subprocess.run([sys.executable, __file__, "one", str(w)], capture_output=True, text=True, cwd=ROOT)
        line = [ln for ln in p.stdout.splitlines() if ln.startswith("{")]
        if not line:
            print(f"workers={w} failed:\n{p.stderr[-2000:]}")
            return
        out[f"workers_{w}"] = json.loads(line[-1])
        r = out[f"workers_{w}"]
        print(f"workers={w}: {r['wall_s']} s for {len(JOBS)} jobs, peak RSS {r['peak_rss_gb']} GB, "
              f"machine used +{r['peak_used_rise_gb']} GB, " + ", ".join(f"{j['status']} {j['seconds']} s" for j in r["jobs"]),
              flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    if sys.argv[1:2] == ["one"]:
        one(int(sys.argv[2]))
    else:
        main()
