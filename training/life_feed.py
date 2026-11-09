"""Give the hive real work so it has calls of its own to learn from (the input of `python -m team life`).

    python training/life_feed.py [first] [last]     tasks from training/data/life_tasks.txt, one per line
Each task runs as `python -m team "<task>" --approve never` with the hive's real memory, in runs/life/<n>. These
tasks are not the bench's: the bench never teaches the hive, and what the hive learns here is not measured on them.
"""
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
tasks = [t.strip() for t in (ROOT / "training" / "data" / "life_tasks.txt").read_text().splitlines() if t.strip()]
a, b = (int(sys.argv[1]) if len(sys.argv) > 1 else 0), (int(sys.argv[2]) if len(sys.argv) > 2 else len(tasks))
tag = sys.argv[3] if len(sys.argv) > 3 else "life"
for i in range(a, min(b, len(tasks))):
    run = ROOT / "runs" / tag / f"{i:03d}"
    if (run / "REPORT.md").exists():
        continue
    t0 = time.time()
    try:
        r = subprocess.run([sys.executable, "-m", "team", tasks[i], "--approve", "never", "--run-dir", str(run)],
                           cwd=ROOT, capture_output=True, text=True, timeout=1500)
        code = r.returncode
    except subprocess.TimeoutExpired:
        code = "timeout"
    n = sum(1 for _ in open(run / "calls.jsonl")) if (run / "calls.jsonl").exists() else 0
    print(f"{i:03d} exit {code} {time.time() - t0:5.0f}s {n:3d} calls  {tasks[i][:70]}", flush=True)
