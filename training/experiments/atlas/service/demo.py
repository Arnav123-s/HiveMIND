"""Reproduce four local CLI receipts, including one real one-CPU WASI quote."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
QUESTIONS = [
    ("Which day of the week is 2024-02-29?", "thursday", None),
    ("A bicycle costs 180 dollars and the price falls by 15%. What is the new price?", "153", "dollars"),
    ("Calculate the depot shipping fee for 0.2 kg and 0.9 kg using per-parcel rounding", 520, "cents"),
    ("Can the depot deliver a bicycle before the weekend?", None, None),
]


def cpu():
    v = resource.getrusage(resource.RUSAGE_CHILDREN)
    return v.ru_utime + v.ru_stime


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    # The native study has its own CPU allocation. Start every process with a single allowed CPU.
    allowed = min(os.sched_getaffinity(0))
    rows = []
    for q, value, unit in QUESTIONS:
        command = [sys.executable, "-m", "training.experiments.atlas.service.ask", "--json", "--sdk", str(args.sdk), q]
        env = dict(os.environ, HIVE_BANK=str(ROOT / "training/reports/retained-skills/shipping/bank"),
                   RAYON_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1")
        start, before = time.monotonic(), cpu()
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=100,
                                preexec_fn=lambda: os.sched_setaffinity(0, {allowed}))
        row = json.loads(result.stdout)
        assert (row["value"], row["unit"], result.returncode) == (value, unit, int(value is None)), (q,row)
        if row["route"] == "shipping":
            assert row["proof"]["fuel"] > 0 and row["proof"]["path"] == "side_exit"
        rows.append(dict(question=q, response=row, exit=result.returncode, process_cpu_s=cpu()-before,
                         wall_s=time.monotonic()-start))
    output = dict(program_sha256=sha256((HERE / "ask.py").read_bytes()).hexdigest(), affinity=[allowed],
                  sdk_sha256=sha256((args.sdk / "python.wasm").read_bytes()).hexdigest(),
                  model_generations=0, cases=rows)
    args.out.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
