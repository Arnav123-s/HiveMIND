"""Drill one team on real work, so the hive has many decisions of its own to learn from (`python -m team life`).

    python training/life_drill.py <first> <last> [tag]     questions from training/data/life_questions.txt
A whole task spends most of its time planning and writing; a small job's decisions come slowly that way. A drill runs
only the research step of the hive on a real question: the researcher picks live sources, reads them and extracts
facts with quotes, and the verifier checks every fact, every listed item and the step, with its jury - the same code
and the same members as inside a task, on real pages. Every member call is logged in runs/<tag>/<n>/calls.jsonl.
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from team import llm  # noqa: E402
from team.board import Board  # noqa: E402
from team.specialists import researcher, verifier  # noqa: E402

qs = [t.strip() for t in (ROOT / "training" / "data" / "life_questions.txt").read_text().splitlines() if t.strip()]
a, b = int(sys.argv[1]), int(sys.argv[2])
tag = sys.argv[3] if len(sys.argv) > 3 else "drill"
for i in range(a, min(b, len(qs))):
    run = ROOT / "runs" / tag / f"{i:03d}"
    if (run / "done.json").exists():
        continue
    board = Board(run, echo=False)
    step = {"id": "s1", "agent": "researcher", "task": qs[i], "needs": [], "done_when": ""}
    board.add_step(step)

    def record(specialist, messages, output, **info):
        with open(run / "calls.jsonl", "a") as f:
            f.write(json.dumps({"step": "s1", "specialist": specialist, "messages": messages, "output": output, **info},
                               ensure_ascii=False) + "\n")
    llm.set_recorder(record)
    t0 = time.time()
    try:
        result = researcher.run(qs[i], "", board, "s1")
        verdict, why = verifier.verify(step, result, board, run / "work")
    except Exception as e:  # noqa: BLE001 - one unreadable source must not end the drill
        verdict, why = "ERROR", f"{type(e).__name__}: {e}"
    facts = board.facts("s1")
    out = {"q": qs[i], "verdict": verdict, "why": str(why)[:200], "seconds": round(time.time() - t0),
           "facts": len(facts), "supported": sum(f["status"] == "supported" for f in facts)}
    (run / "done.json").write_text(json.dumps(out, indent=1))
    print(f"{i:03d} {verdict:5s} {out['seconds']:4d}s facts {out['supported']}/{out['facts']}  {qs[i][:70]}", flush=True)
