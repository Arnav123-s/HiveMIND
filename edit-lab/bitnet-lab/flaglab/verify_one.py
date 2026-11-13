#!/usr/bin/env python3
"""Run one flaglab verification case and print the outcome as JSON on the last line.
Usage: verify_one.py --file train_next.py -- <train args...>
Appends nothing to any shared record: cwd is flaglab/, so runs.jsonl lands here.
Muse's work, Muse's side.
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = "/home/hatch/workspace/edit-lab/fable-validation/venv/bin/python"


def last_record(before):
    path = os.path.join(HERE, "runs.jsonl")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        lines = [ln for ln in f if ln.strip()]
    new = lines[before:]
    return json.loads(new[-1]) if new else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--timeout", type=int, default=420)
    ap.add_argument("rest", nargs=argparse.REMAINDER)
    a = ap.parse_args()
    args = a.rest[1:] if a.rest[:1] == ["--"] else a.rest
    path = os.path.join(HERE, "runs.jsonl")
    before = sum(1 for _ in open(path)) if os.path.exists(path) else 0
    env = dict(os.environ, OMP_NUM_THREADS="2", MKL_NUM_THREADS="2")
    try:
        p = subprocess.run([PY, os.path.join(HERE, a.file)] + args, cwd=HERE, env=env,
                           capture_output=True, text=True, timeout=a.timeout)
        rec = last_record(before)
        print(json.dumps({"rc": p.returncode, "rec": rec,
                          "tail": (p.stdout + p.stderr).strip().splitlines()[-3:]}))
    except subprocess.TimeoutExpired:
        print(json.dumps({"rc": "timeout", "rec": None, "tail": []}))


if __name__ == "__main__":
    main()
