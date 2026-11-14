"""Every generation and trial the grow workflow recorded, from every branch it records to, as one table.

    python3 training/results.py            fetches main, make-it-work and the claude/* branches first
    python3 training/results.py --local    reads only training/reports/generations.jsonl as checked out

The record job of .github/workflows/grow.yml appends one line per run to training/reports/generations.jsonl on the
branch the run was started from, so results are spread over branches until they are merged. This reads them all,
drops repeats, and prints the oldest first. Needs nothing but git and Python.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILE = "training/reports/generations.jsonl"


def _git(*a):
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True)


def lines(local=False):
    texts = [(ROOT / FILE).read_text() if (ROOT / FILE).exists() else ""]
    if not local:
        _git("fetch", "-q", "origin", "main", "make-it-work")
        refs = [r for r in _git("branch", "-r", "--format=%(refname:short)").stdout.split()
                if r in ("origin/main", "origin/make-it-work") or r.startswith("origin/claude/")]
        for r in refs:
            texts.append(_git("show", f"{r}:{FILE}").stdout)
    seen, out = set(), []
    for text in texts:
        for ln in text.splitlines():
            try:
                d = json.loads(ln)
            except ValueError:
                continue
            key = (d.get("generation"), d.get("when"))
            if key not in seen:
                seen.add(key)
                out.append(d)
    return sorted(out, key=lambda d: d.get("when") or "")


def table(rows):
    print("| gen | when (UTC) | dna | kind | rows | DNA alone | body before | body after | never-practised kinds | kept | trial |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for d in rows:
        a = d.get("arms", {})
        cell = lambda k: (f"{a[k]['passed']}/{a[k]['tasks']} ({a[k]['minutes']} min)" if a.get(k, {}).get("seeds") else "-")
        kind = "ternary" if d.get("ternary_cells") else "ordinary"
        if d.get("foresee"):
            kind += " + foresee"
        up = a.get("after", {}).get("unpractised", [0, 0])
        print(f"| {d.get('generation')} | {d.get('when')} | {d.get('dna', 't17')} | {kind} | {d.get('rows')} | {cell('dna')} | "
              f"{cell('before')} | {cell('after')} | {up[0]} of {up[1]} | {'yes' if d.get('kept') else 'no'} | {'yes' if d.get('trial') else ''} |")


if __name__ == "__main__":
    table(lines(local="--local" in sys.argv))
