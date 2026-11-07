"""Before/after table from observation reports.

    python training/compare.py base base_tools trained
"""
import json
import sys
from pathlib import Path

R = Path(__file__).resolve().parent / "reports"
tags = sys.argv[1:] or ["base", "trained"]
reps = {t: json.loads((R / f"{t}.json").read_text()) for t in tags if (R / f"{t}.json").exists()}
suites = []
for r in reps.values():
    for s in r["scores"]:
        if s not in suites:
            suites.append(s)
lines = ["| specialist / eval | n | " + " | ".join(reps) + " |", "|---|---|" + "---|" * len(reps)]
for s in suites:
    n = next((r["scores"][s]["n"] for r in reps.values() if s in r["scores"]), "")
    cells = [f"{r['scores'][s]['mean']:.2f}" if s in r["scores"] else "-" for r in reps.values()]
    lines.append(f"| {s} | {n} | " + " | ".join(cells) + " |")
out = "\n".join(lines)
print(out)
(R / "SUMMARY.md").write_text("# Specialist scores on held-out evals\n\n" + out + "\n")
