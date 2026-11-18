"""Assemble a school using only independent school qualifications, before the field exams."""

import argparse
from pathlib import Path

from .campaign import read, save


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sources", type=Path, nargs="+", required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    bank = {}
    for path in args.sources:
        for row in read(path):
            if row["admitted"] and row["promotion"]["complete"]:
                bank.setdefault(row["task"], row)
    save(args.out, list(bank.values()))
    print("admitted:", ", ".join(bank), flush=True)


if __name__ == "__main__":
    main()
