"""Fit the six released rank-4 deltas from their frozen native training states or re-extract states."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from training import domain_engram


def main():
    import numpy as np
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="new output directory for the fitted GGUFs")
    parser.add_argument("--extract", action="store_true", help="run the actual t80 model on all checked training inputs")
    parser.add_argument("--check", action="store_true", help="replay the 18 paired native greedy checks")
    parser.add_argument("--model", type=Path, help="local Ternary-Bonsai-8B GGUF")
    parser.add_argument("--runtime", type=Path, help="compatible ik_llama.cpp llama-server")
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args()
    if (args.extract or args.check) and not (args.model and args.runtime):
        parser.error("--extract and --check require --model and --runtime")
    if args.out.exists() and any(args.out.iterdir()):
        parser.error("--out must be an empty directory")
    args.out.mkdir(exist_ok=True, parents=True)
    catalog = json.loads((HERE / "catalog.json").read_text())
    tasks = json.loads((HERE / "exercises.json").read_text())
    system = (HERE / "system.txt").read_text()
    archive = np.load(HERE / "training-states.npz") if not args.extract else None
    for domain, task in tasks.items():
        name = "t80+e_domain_" + catalog[domain]["domain"] + ".gguf"
        path = args.out / name
        if args.extract:
            rows = [{"prompt": task["instruction"] + " " + q, "answer": gold, "system": system}
                    for q, gold in task["train"]]
            domain_engram.train(rows, path, model=args.model, runtime=args.runtime, threads=args.threads)
        else:
            ids, a, b, _ = domain_engram.fit(archive[domain], archive[domain + "_tokens"])
            domain_engram.write_adapter(path, ids, a, b, 151669)
        print(hashlib.sha256(path.read_bytes()).hexdigest(), name, flush=True)
        if args.check:
            cases = [{"prompt": task["instruction"] + " " + q, "answer": gold, "system": system}
                     for q, gold in task["check"]]
            result = domain_engram.validate(cases, path, model=args.model, runtime=args.runtime, threads=args.threads)
            (args.out / (domain + "-checks.json")).write_text(json.dumps(result, indent=2) + "\n")
            print(f"{domain}: {result['before']} of {result['count']} before, {result['after']} after", flush=True)


if __name__ == "__main__":
    main()
