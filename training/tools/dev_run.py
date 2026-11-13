"""Run chosen tasks through the members form (team/solo.py) with every program and output kept, to find faults by
reading them.   python training/tools/dev_run.py OUT_DIR MEMBERS [TASKS.json]   (default dev_tasks.json here)
TASKS.json: [{"kind": ..., "task": ..., "why": ...}]; dev_tasks2.json / dev_tasks3.json are tasks members failed
on seeds 9005-9007. Each task's logs land in OUT_DIR/t<i>/ (members/**/member*_*.py and .out/.err beside them)."""
import json, os, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
os.environ["AGENT_TEAM_MEMORY"] = str(out / "mem")
from team import memory, solo
memory.HOME = out / "mem"; memory.HOME.mkdir(exist_ok=True)
solo.library = lambda: out / "mem" / "solved.jsonl"
tasks = json.load(open(Path(__file__).parent / (sys.argv[3] if len(sys.argv) > 3 else "dev_tasks.json")))
for i, t in enumerate(tasks):
    t0 = time.time()
    r = solo.run(t["task"], out / f"t{i}", "never", members=int(sys.argv[2]))
    progs = len(list((out / f"t{i}").rglob("member*_*.py")))
    print("TASK", t["kind"], "|", round(time.time() - t0), "s |", progs, "programs | agreed", r["agreed"], "|", r["report"].split("\n## ")[0].replace("\n", " | ")[:300], flush=True)
