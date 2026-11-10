"""The research hive against the single researcher, on research questions that are in no bench and no training data.

    python training/research_eval.py
Each question runs through the whole hive twice (python -m team, risky actions: never): with the research hive
(sub-questions, relevance and gap cells, cross-checks) and with it off (AGENT_TEAM_RESEARCH_HIVE=0: one researcher
step). Measured from each run's board: time, model calls, cell calls, claims verified against their quotes, distinct
sources behind them, sub-questions left unanswered, instructions left undone. Both use the same memory folder
(memory-eval/), so their member decisions are logged there for `grow` (team/cells/learn.py).
Writes training/reports/research_eval.json and .md.
"""
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "training" / "reports"
RUNS = ROOT / "runs" / "research_eval"
QUESTIONS = [
    "Research how lithium-ion batteries degrade over time and what slows the degradation.",
    "Compare SQLite and DuckDB for analytics on a laptop: speed, features and limits.",
    "Investigate what the James Webb Space Telescope's main mirror is made of and why.",
    "Run an experiment to test whether Python's built-in sort is faster than a hand-written merge sort on lists of "
    "10,000 random numbers, and explain why.",
]


def measure(run):
    db = sqlite3.connect(run / "board.db")
    facts = db.execute("select url from facts where status='supported'").fetchall()
    ev = [json.loads(x) for x in (run / "events.jsonl").read_text().splitlines()] if (run / "events.jsonl").exists() else []
    calls = (run / "calls.jsonl").read_text().splitlines() if (run / "calls.jsonl").exists() else []
    rep = (run / "REPORT.md").read_text() if (run / "REPORT.md").exists() else ""
    return {"verified_claims": len(facts), "sources": len({u for (u,) in facts if u.startswith("http")}),
            "model_calls": len(calls), "cell_calls": sum(e["agent"].startswith("cell:") for e in ev),
            "open_sub_questions": sum(e["kind"] == "gap" for e in ev),
            "conflicts": sum(e["kind"] == "conflict" for e in ev),
            "undone": len(re.findall(r"^- ❌", rep, re.M)), "report_chars": len(rep.split("\n## ")[0])}


def main():
    home = ROOT / "memory-eval"
    home.mkdir(exist_ok=True)
    res = {}
    for i, q in enumerate(QUESTIONS):
        for mode in ("hive", "single"):
            run = RUNS / f"q{i + 1}_{mode}"
            if (run / "measure.json").exists():
                res[f"q{i + 1}_{mode}"] = json.loads((run / "measure.json").read_text())
                continue
            env = dict(os.environ, AGENT_TEAM_HOME=str(home), AGENT_TEAM_RESEARCH_HIVE="1" if mode == "hive" else "0")
            t = time.time()
            subprocess.run([sys.executable, "-m", "team", q, "--approve", "never", "--run-dir", str(run)], cwd=ROOT, env=env,
                           capture_output=True, text=True, timeout=3600)
            m = {"question": q, "mode": mode, "seconds": round(time.time() - t), **measure(run)}
            (run / "measure.json").write_text(json.dumps(m, indent=1))
            res[f"q{i + 1}_{mode}"] = m
            print(json.dumps(m), flush=True)
    (OUT / "research_eval.json").write_text(json.dumps(res, indent=1))
    keys = ["seconds", "model_calls", "cell_calls", "verified_claims", "sources", "open_sub_questions", "conflicts", "undone"]
    lines = ["# Research hive vs one researcher", "", "| question | mode | " + " | ".join(keys) + " |",
             "|---|---|" + "---|" * len(keys)]
    for k, m in res.items():
        lines.append(f"| {m['question'][:50]} | {m['mode']} | " + " | ".join(str(m[x]) for x in keys) + " |")
    (OUT / "research_eval.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
