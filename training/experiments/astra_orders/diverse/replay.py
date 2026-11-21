"""Choose among frozen offers with the hive's actual file-aware rules before applying the blind grader."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from team import deliverables, solo
from team.specialists.coder import extract_code
from team.tools import sandbox
from training.experiments.astra_orders import grade, panel
from training.experiments.astra_orders.diverse.native import offers
from training.experiments.fieldwork.guest import Guest

HERE = Path(__file__).resolve().parent
ORIGINAL = HERE.parent / "native.json"
NEW = HERE / "native.json"


def choose(arms, tries, task, diverse=False):
    for size in range(2, len(arms) + 1):
        seen = [dict(tries[arm], diverse_orders=diverse) for arm in arms[:size]]
        pairs = solo.agreeing(seen, task)
        win = solo._winner(seen, pairs if deliverables.wanted(task) else pairs[:1], task)
        if win is not None:
            return {"selected": win["arm"], "seats": size}
    return {"selected": None, "seats": len(arms)}


def execute(guest, row, arm, call, root):
    source = extract_code(call["raw"])
    control = root / arm
    work = control / "work"
    work.mkdir(parents=True)
    names = deliverables.wanted(row["task"])
    sandbox.give(row["task"], work, skip=names)
    if guest is None:
        with patch.object(sandbox, "HOOK", control / "hooks"):
            result = sandbox.run_python(source, work, timeout=15)
        error = result["returncode"] != 0
    else:
        result = grade.execute(guest, work, source, control)
        error = bool(result["error"])
    return {"arm": arm, "answer": "" if error else result["stdout"].strip(),
            "stderr": result["stderr"].strip().splitlines()[-1:] if error else [],
            "error": error, "work": str(work), "delivery": deliverables.inspect(row["task"], work, names)}


def replay(sdk):
    digests = {k.name if k == ORIGINAL else "diverse/" + k.name:hashlib.sha256(k.read_bytes()).hexdigest()
               for k in (ORIGINAL, NEW)}
    if digests != json.loads((HERE / "reviewed.json").read_text()):
        raise ValueError("Host replay requires human-reviewed immutable programs.")
    native = json.loads(NEW.read_text())
    assert native["complete"] and len(native["calls"]) == 18
    inputs = json.loads((HERE.parent / "inputs.json").read_text())
    for recorded, (ident, arm, messages, settings) in zip(native["calls"], offers(inputs), strict=True):
        assert (recorded["id"], recorded["arm"]) == (ident, arm)
        assert recorded.get("sampling_override", {}) == settings
        assert recorded["system_sha256"] == hashlib.sha256(messages[0]["content"].encode()).hexdigest()
    familiar = {r["id"]:r["gate"] != "full" for r in inputs["rows"]}
    panels = json.loads((HERE.parent / "panel.json").read_text())
    calls = [c for c in json.loads(ORIGINAL.read_text())["calls"] if c["arm"] == "short"] + native["calls"]
    out = {"source_sha256": digests, "runtimes": {}}
    for runtime, guest in (("cpython", None), ("wasi", Guest(sdk))):
        rows = []
        for r in panels:
            with tempfile.TemporaryDirectory() as folder:
                tries = {c["arm"]:execute(guest, r, c["arm"], c, Path(folder))
                         for c in calls if c["id"] == r["id"]}
                diverse = "short2" if familiar[r["id"]] else "modular2"
                decisions = {}
                for policy, second in (("short", "short2"), ("diverse", diverse)):
                    for budget in (2, 3):
                        order = ["short", second, "short3"][:budget]
                        decisions[f"{policy}{budget}"] = choose(order, tries, r["task"], diverse=policy == "diverse")
                # Exploratory, added after reading native source. Never combine this arm with the frozen result.
                greedy_second = "short2" if familiar[r["id"]] else "modular0"
                exploratory = {
                    f"greedy_diverse{n}": choose(["short", greedy_second, "short3"][:n], tries, r["task"], diverse=True)
                    for n in (2, 3)
                }
                # Evaluator sees only decisions that already exist, plus actual outputs for the hindsight union.
                for tried in tries.values():
                    passed, why = panel.grade(r, tried["answer"], Path(tried.pop("work")))
                    tried["ok"], tried["grade"] = passed and not tried["error"], why
                for decision in (*decisions.values(), *exploratory.values()):
                    selected = decision["selected"]
                    decision["result"] = "abstain" if selected is None else "right" if tries[selected]["ok"] else "wrong"
                rows.append({"id":r["id"], "offers":tries, "policies":decisions, "exploratory":exploratory})
        out["runtimes"][runtime] = rows
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sdk", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.write_text(json.dumps(replay(args.sdk), indent=2, sort_keys=True) + "\n")
