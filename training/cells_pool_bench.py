"""Many cells at once: throughput and memory of the cell pool, 1 vs 2 vs 4 workers.

    python training/cells_pool_bench.py
The same 160 cell questions (route_step's test inputs, repeated) answered: in the main process (4 threads, one
question after another), then by the pool with 2 and 4 workers (one thread each). Each mode runs in a fresh process.
Memory: the rise of the machine's used memory while it runs. Writes training/reports/cells/pool.json.
"""
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "training" / "reports" / "cells" / "pool.json"


def used_gb():
    m = {ln.split(":")[0]: int(ln.split()[1]) for ln in open("/proc/meminfo")}
    return (m["MemTotal"] - m["MemAvailable"]) / 1e6


def one(workers):
    os.environ["AGENT_TEAM_CELL_WORKERS"] = str(workers)
    from team.cells import pool
    from training.cells import data
    _, _, te = data("route_step")
    texts = [x for x, _ in te][:80] * 2
    base, peak, done = used_gb(), [0.0], threading.Event()

    def sample():
        while not done.is_set():
            peak[0] = max(peak[0], used_gb() - base)
            time.sleep(0.2)
    threading.Thread(target=sample, daemon=True).start()
    pool.map("route_step", texts[:8])  # warm: load the base (and start the workers)
    t = time.time()
    out = pool.map("route_step", texts)
    sec = time.time() - t
    done.set()
    print(json.dumps({"workers": workers, "questions": len(texts), "seconds": round(sec, 2),
                      "per_second": round(len(texts) / sec, 1), "memory_rise_gb": round(peak[0], 2),
                      "answers_sample": out[:3]}))
    pool.shutdown()


if __name__ == "__main__":
    if sys.argv[1:2] == ["one"]:
        one(int(sys.argv[2]))
    else:
        res = {}
        for w in (1, 2, 4):
            p = subprocess.run([sys.executable, __file__, "one", str(w)], capture_output=True, text=True, cwd=ROOT)
            line = [ln for ln in p.stdout.splitlines() if ln.startswith("{")]
            if not line:
                print(f"workers={w} failed:\n{p.stderr[-1500:]}")
                continue
            res[f"workers_{w}"] = json.loads(line[-1])
            r = res[f"workers_{w}"]
            print(f"workers={w}: {r['questions']} questions in {r['seconds']} s ({r['per_second']}/s), memory +{r['memory_rise_gb']} GB",
                  flush=True)
        OUT.write_text(json.dumps(res, indent=1))
