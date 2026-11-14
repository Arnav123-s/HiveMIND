"""Do engrams help? A stream of tasks whose kinds come round again, done by the body's DNA with and without them.

    python training/experiments/engram_stream.py [--seed 31000] [--rounds 4] [--who t17]

Each round holds one fresh task of each of a few kinds (new numbers every round). Arm "off": the members work with
no memory. Arm "on": after every task the check confirms, an engram is written (team/engram.py), and later tasks
recall the engrams of tasks like them. Both arms see the same tasks in the same order. Round 1 has nothing to
recall, so the arms should be level there; what engrams are worth shows in the later rounds.
Result: training/experiments/engram_stream_<seed>.json.
"""
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from training import exam as E  # noqa: E402

KINDS = ["m_percent", "m_days", "m_units", "m_table", "m_code", "m_fix", "m_weekday", "m_steps"]


def main(argv):
    opt = lambda k, d: type(d)(argv[argv.index(k) + 1]) if k in argv else d  # noqa: E731
    seed, rounds, who = opt("--seed", 31000), opt("--rounds", 4), opt("--who", "t17")
    stream = []
    for r in range(rounds):
        for tid, field, kind, task, check in E.exam(seed + r, 18, (), "basic", without=[m.__name__ for m in E.MAKERS if m.__name__ not in KINDS]):
            stream.append((r + 1, f"{tid}", kind, task, check))
    os.environ.update({"HIVE_MEMBERS": who, "AGENT_TEAM_SOLO": "2", "AGENT_TEAM_SOLO_ALONE": "1"})
    out = {"seed": seed, "who": who, "rounds": rounds, "tasks_a_round": len(stream) // rounds, "arms": {}}
    for arm in ("off", "on"):
        home, store = E._memory(True), Path(tempfile.mkdtemp(prefix="engrams-"))
        os.environ["HIVE_ENGRAMS_HOME"] = str(store)
        os.environ["HIVE_ENGRAMS"] = "1" if arm == "on" else "0"
        from team import ternary
        ternary.ENGRAMS = store
        ternary.stop()
        rows, t0, written = [], time.time(), 0
        for rnd, tid, kind, task, check in stream:
            res = E.sit_one(f"engram_{seed}_{arm}", tid, task, check, home)
            recalled = ""
            ev = E.RUNS / f"engram_{seed}_{arm}" / tid / "members" / "events.jsonl"
            if ev.exists():
                recalled = next((json.loads(x)["msg"] for x in ev.read_text().splitlines() if '"engrams"' in x), "")
            if arm == "on" and res["ok"]:
                from team import engram
                written += bool(engram.write(task, E.RUNS / f"engram_{seed}_{arm}" / tid, base=who.split("+")[0]))
            rows.append({"round": rnd, "kind": kind, "ok": res["ok"], "seconds": res["seconds"], "recalled": recalled})
            print(f"{arm} round {rnd} {'PASS' if res['ok'] else 'FAIL'} [{kind}] {res['seconds']}s {('recalled ' + recalled) if recalled else ''}", flush=True)
        by = {r: [sum(x["ok"] for x in rows if x["round"] == r), sum(1 for x in rows if x["round"] == r)] for r in range(1, rounds + 1)}
        out["arms"][arm] = {"by_round": by, "passed": sum(x["ok"] for x in rows), "tasks": len(rows), "minutes": round((time.time() - t0) / 60),
                            "engrams_written": written, "rows": rows}
        shutil.rmtree(store, ignore_errors=True)
        ternary.stop()
    (ROOT / "training" / "experiments" / f"engram_stream_{seed}.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({a: {"by_round": v["by_round"], "passed": v["passed"], "minutes": v["minutes"], "engrams_written": v["engrams_written"]} for a, v in out["arms"].items()}))


if __name__ == "__main__":
    main(sys.argv[1:])
