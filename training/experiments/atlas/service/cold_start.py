"""Replay the pinned arithmetic CLI cold-start comparison from Git history on one Linux CPU."""
import argparse
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import platform
import resource
from statistics import median
import subprocess
import sys
import tarfile
from tempfile import TemporaryDirectory
import time


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
ORIGINAL = "ccd34f5702a67be64c0a5a3859e998f559b7d03a"
UPDATED = "f8fcb72d16fecd1eb2bfd967e584dca476c16abe"
CLI = Path("training/experiments/atlas/service/ask.py")
CERTS = Path("training/experiments/atlas/pulse/one_checked")
COMMAND = ["-m", "training.experiments.atlas.service.ask", "--json"]
QUESTIONS = [
    ("weekday", "Which day of the week is 2024-02-29?", "thursday"),
    ("dollars", "A bicycle costs 180 dollars and the price falls by 15%. What is the new price?", "153"),
    ("gcd", "What is the GCD of 66 and 132?", 66),
]


def git(*arguments):
    proc = subprocess.run(["git", *arguments], cwd=ROOT, capture_output=True)
    if proc.returncode:
        raise RuntimeError(f"Cannot retrieve the pinned benchmark sources. Fetch the PR's history. {proc.stderr.decode().strip()}")
    return proc.stdout


def materialize(directory, expected):
    shared = directory / "shared"
    archive = git("archive", UPDATED, "team", "training/__init__.py")
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as files:
        files.extractall(shared, filter="data")
    trees = {}
    for variant, commit, cert in (("original", ORIGINAL, "certificate.py"), ("updated", UPDATED, "current.py")):
        tree = directory / variant
        trees[variant] = tree
        (tree / "training").mkdir(parents=True)
        (tree / "team").symlink_to(shared / "team", target_is_directory=True)
        (tree / "training/__init__.py").symlink_to(shared / "training/__init__.py")
        for label, path in (("ask", CLI), ("certificate", CERTS / cert)):
            source = git("show", f"{commit}:{path.as_posix()}")
            if sha256(source).hexdigest() != expected[f"{variant}_{label}"]:
                raise ValueError(f"unexpected {variant} {path} digest")
            (tree / path).parent.mkdir(parents=True, exist_ok=True)
            (tree / path).write_bytes(source)
    return trees


def children_cpu():
    times = resource.getrusage(resource.RUSAGE_CHILDREN)
    return times.ru_utime + times.ru_stime


def run(cpu):
    recorded = json.loads((HERE / "cold-start.json").read_text())
    env = {**os.environ, "HIVE_BANK": "off", "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "RAYON_NUM_THREADS": "1"}
    rows = []
    with TemporaryDirectory() as tmp:
        trees = materialize(Path(tmp), recorded["sources"])
        for repeat in range(3):
            for offset in range(len(QUESTIONS)):
                kind, question, expected = QUESTIONS[(repeat + offset) % len(QUESTIONS)]
                order = ("original", "updated") if (repeat + offset) % 2 == 0 else ("updated", "original")
                for variant in order:
                    start, prior_cpu = time.perf_counter(), children_cpu()
                    proc = subprocess.run([sys.executable, *COMMAND, question], cwd=trees[variant], env=env,
                                          preexec_fn=lambda: os.sched_setaffinity(0, {cpu}), capture_output=True,
                                          text=True, timeout=90, check=True)
                    elapsed, spent = time.perf_counter() - start, children_cpu() - prior_cpu
                    answer = json.loads(proc.stdout)
                    if (answer["status"], answer["route"], answer["value"]) != ("answered", kind, expected):
                        raise ValueError(f"unexpected {kind} answer from {variant}: {answer}")
                    rows.append(dict(iteration=repeat + 1, kind=kind, question=question, variant=variant,
                                     cpu_s=spent, wall_s=elapsed, response=answer))
    summary = {}
    for variant in trees:
        summary[variant] = {}
        for kind in ("all", *(row[0] for row in QUESTIONS)):
            selected = [r for r in rows if r["variant"] == variant and kind in ("all", r["kind"])]
            summary[variant][kind] = {m: median(r[m] for r in selected) for m in ("cpu_s", "wall_s")}
    for kind, _, _ in QUESTIONS:
        if len({json.dumps(r["response"], sort_keys=True) for r in rows if r["kind"] == kind}) != 1:
            raise ValueError(f"{kind} JSON responses were not identical")
    return dict(sources=recorded["sources"], commits=dict(original=ORIGINAL, updated=UPDATED),
                python=platform.python_version(), platform=platform.platform(), affinity=[cpu], threads_env=1,
                command_template=["python", *COMMAND, "QUESTION"], identical_json_responses_for_all_repetitions=True,
                median=summary, rows=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cpu", type=int, help="one allowed CPU (default 4 when available, otherwise the first)")
    parser.add_argument("--out", type=Path, help="save the new full receipt; the original measurement stays in place")
    args = parser.parse_args()
    if not hasattr(os, "sched_getaffinity"):
        parser.error("this comparison requires Linux CPU affinity")
    allowed = os.sched_getaffinity(0)
    cpu = args.cpu if args.cpu is not None else (4 if 4 in allowed else min(allowed))
    if cpu not in allowed:
        parser.error(f"CPU {cpu} is outside this process's allowed set {sorted(allowed)}")
    if args.out and args.out.resolve() == (HERE / "cold-start.json").resolve():
        parser.error("choose a new output path to preserve the recorded comparison")
    output = run(cpu)
    if args.out:
        args.out.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(output["median"], indent=2))


if __name__ == "__main__":
    main()
