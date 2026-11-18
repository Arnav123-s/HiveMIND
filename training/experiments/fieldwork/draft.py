"""Collect independently written first submissions before running private evaluation."""

import argparse
import json
from pathlib import Path

from .contracts import TASKS
from .native import generate, server


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("binary", "weights", "out"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--adapter", type=Path)
    p.add_argument("--tasks", nargs="+", choices=TASKS, required=True)
    p.add_argument("--threads", type=int, default=4)
    p.add_argument("--budget", type=int, default=1400)
    p.add_argument("--focused", action="store_true")
    p.add_argument("--concise", action="store_true")
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    with server(args.binary, args.weights, args.out / "server.log", args.adapter, args.threads) as url:
        for name in args.tasks:
            dest = args.out / (name + ".json")
            if dest.exists():
                continue
            row = generate(url, TASKS[name], budget=args.budget, focused=args.focused, concise=args.concise)
            temp = dest.with_suffix(".tmp")
            temp.write_text(json.dumps(row))
            temp.replace(dest)
            print(name, row["usage"], row["seconds"], flush=True)


if __name__ == "__main__":
    main()
