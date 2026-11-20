"""Run both T80 slice sizes in fresh processes and preserve the exported adapters."""
import argparse
import json
import os
from pathlib import Path
from resource import RUSAGE_CHILDREN, getrusage
import signal
import subprocess
import sys
import time


HERE = Path(__file__).resolve().parent
CGROUP = Path("/sys/fs/cgroup")


def charged_gib():
    """Reclaimable clean checkpoint pages may fill an otherwise idle Linux cgroup."""
    stats = dict(line.split() for line in (CGROUP / "memory.stat").read_text().splitlines())
    return sum(int(stats.get(k, 0)) for k in ("anon", "kernel", "shmem", "file_dirty", "file_writeback")) / 2**30


def run_arm(arm, folder, cpus, env, ceiling):
    t0 = time.monotonic()
    before = getrusage(RUSAGE_CHILDREN)
    peak = 0
    with (folder / f"{arm}.log").open("w") as stream:
        result = folder / f"{arm}.json"
        command = [sys.executable, "-u", str(HERE / "slice_bench.py"), arm,
                   "--scratch", str(folder / arm), "--result", str(result)]
        proc = subprocess.Popen(command, env=env, stdout=stream, stderr=subprocess.STDOUT,
                                start_new_session=True, preexec_fn=lambda: os.sched_setaffinity(0, cpus))
        try:
            while proc.poll() is None:
                if ceiling:
                    peak = max(peak, charged_gib())
                    if peak >= ceiling:
                        raise MemoryError(f"private + kernel + dirty page charge {peak:.2f} GiB")
                time.sleep(.25)
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait()
    if proc.returncode:
        raise RuntimeError(f"{arm} failed with code {proc.returncode}; see {stream.name}")
    after = getrusage(RUSAGE_CHILDREN)
    return {"result": json.loads(result.read_text()), "wall_seconds": round(time.monotonic()-t0, 3),
            "cpu_seconds": round(after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime, 3),
            "max_cgroup_nonreclaimable_proxy_gib": round(peak, 3)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch", required=True, type=Path)
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--charged-limit-gib", type=float, default=14.5,
                        help="stop this experiment before shared memory pressure; use zero to disable")
    args = parser.parse_args()
    args.scratch.mkdir(parents=True, exist_ok=False)
    cpus = set(sorted(os.sched_getaffinity(0))[-2:])
    if len(cpus) != 2:
        raise RuntimeError("two CPUs are required")
    env = os.environ | {"OMP_NUM_THREADS": "2", "OPENBLAS_NUM_THREADS": "1", "TOKENIZERS_PARALLELISM": "false",
                        "PYTHONHASHSEED": "0", "HF_HUB_OFFLINE": "1"}
    result = {"threads": 2, "affinity": sorted(cpus), "arms": {}}
    for arm in ("half", "full"):
        print(f"Starting {arm}", flush=True)
        result["arms"][arm] = run_arm(arm, args.scratch, cpus, env, args.charged_limit_gib)
        args.result.write_text(json.dumps(result, indent=2) + "\n")
        row = result["arms"][arm]
        print(arm, row["result"]["meta"]["steps"], row["wall_seconds"], flush=True)


if __name__ == "__main__":
    main()
