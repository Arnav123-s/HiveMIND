"""Replay a frozen local lesson stream through the ordinary teach and refresh CLI."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
FROZEN = "8457b562e9044343248efad405610b84142d7dee4b467b2678ac5cfc72a32521"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", required=True, type=Path)
    p.add_argument("--runtime", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path, help="new empty output directory")
    a = p.parse_args()
    raw = (HERE/"incident-labels.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != FROZEN:
        raise ValueError("frozen lesson sequence changed")
    data = json.loads(raw)
    a.out.mkdir(parents=True, exist_ok=True)
    if any(a.out.iterdir()):
        raise ValueError("output directory must be empty")
    env = {**os.environ, "HIVE_PYTHON":sys.executable, "OPENBLAS_NUM_THREADS":"1", "OMP_NUM_THREADS":"1",
           "MKL_NUM_THREADS":"1", "HIVE_LEARNING_HOME":str(a.out/"lessons"), "HIVE_ENGRAMS_HOME":str(a.out/"native")}
    def learn(*args):
        proc = subprocess.run([str(ROOT/"hive"), "learn", *args], env=env, cwd=ROOT, capture_output=True, text=True)
        if proc.returncode:
            raise RuntimeError(proc.stderr or proc.stdout)
        return json.loads(proc.stdout)
    stages = []
    for number, batch in enumerate(data["batches"],1):
        start = time.monotonic()
        added = [learn("teach","--domain",data["domain"],"--topic",data["topic"],
                       "--prompt",data["instruction"]+stem,"--answer",label) for stem,label in batch]
        report, = learn("refresh","--domain",data["domain"],"--model",str(a.model.resolve()),
                        "--runtime",str(a.runtime.resolve()),"--threads","1")
        expected = [r["id"] for r in added if r.get("split") == "validation"]
        stage = dict(stage=number, distinct_new=len(added), newly_held_out=len(expected), seconds=round(time.monotonic()-start,1),
                     refresh=report)
        stages.append(stage)
        (a.out/f"stage-{number}.json").write_text(json.dumps(stage,indent=2)+"\n")
        print(number, report["status"], report.get("measurement",{}).get("validation",{}), flush=True)
    fast, = learn("refresh","--domain",data["domain"],"--model",str(a.model.resolve()),
                  "--runtime",str(a.runtime.resolve()),"--threads","1")
    report = dict(corpus_sha256=FROZEN, stages=stages, unchanged_revision_cached=bool(fast.get("cached")))
    (a.out/"result.json").write_text(json.dumps(report,indent=2)+"\n")


if __name__ == "__main__":
    main()
