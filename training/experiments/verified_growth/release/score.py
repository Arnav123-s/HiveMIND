"""Grade sealed outputs using official exam tasks and archived fallback grades."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

from audit import HERE, digest, score

sys.path.insert(0, str(HERE.parents[3]))
from training import exam
from training.kinds import _programs
from training.experiments.fieldwork.guest import Guest


# Run functions in the repo's isolated CPython guest. The submitted module receives operations only.
SCENARIO = """
def solve(scenario):
    object_name = scenario['new']
    try:
        obj = globals()[object_name[0]](*object_name[1]) if object_name else None
    except Exception:
        return None
    outputs = []
    for name, args in scenario['steps']:
        try:
            fn = getattr(obj, name) if object_name else globals()[name]
            outputs.append(fn(*args))
        except Exception as exc:
            outputs.append({'raises': type(exc).__name__})
    return outputs
"""


def hidden_in_guest(guest, path, scenarios):
    operations = [{"new": sc["new"], "steps": [[n, args] for n, args, _ in sc["steps"]]} for sc in scenarios]
    rows, _, _ = guest.run(path.read_text() + SCENARIO, operations)
    count = sum(len(sc["steps"]) for sc in scenarios)
    if len(rows) != len(scenarios):
        return False, "incomplete WASI output"
    correct = 0
    for row, sc in zip(rows, scenarios, strict=True):
        got = row.get("value")
        if isinstance(got, list) and len(got) == len(sc["steps"]):
            correct += sum(item == official for item, (_, _, official) in zip(got, sc["steps"], strict=True))
    return correct == count, f"{correct} of {count} official hidden calls passed in WASI"


def grade(question, response, sdk):
    if response["status"] != "answered":
        assert response["status"] == "abstained"
        return {"submitted": False}
    with TemporaryDirectory() as tmp:
        run = Path(tmp)
        work = run / "work"
        work.mkdir()
        for name, content in response["files"].items():
            path = Path(name)
            if path.is_absolute() or ".." in path.parts or not path.name or not isinstance(content, str):
                raise ValueError("invalid submission path or contents")
            dest = work / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content)
        text = response["text"]
        (run / "REPORT.md").write_text(text)
        with patch.object(_programs, "hidden", lambda p, sc: hidden_in_guest(Guest(sdk), p, sc)):
            okay, reason = question[-1](run, text)
    return {"submitted": True, "passed": bool(okay), "reason": reason}


def run(receipts, sdk):
    data = json.loads(receipts.read_bytes())
    ledger = json.loads((HERE / "ledger.json").read_bytes())
    questions = {q[0]: q for q in exam.held_exam()}
    prompts = {tid: digest(q[3].strip().encode()) for tid, q in questions.items()}
    assert prompts == ledger["prompt_sha256"] and set(data["decisions"]) == set(prompts.values())
    cases = {}
    arms = {}
    for gen in ("g51", "g52"):
        original = ledger["snapshots"][gen + "-after"]
        outcomes = {"original": {}, "table_only": {}, "table_fallback": {}, "relay_fallback": {}, "both": {}}
        for tid, key in sorted(prompts.items()):
            obs = original[tid]
            orig = "correct" if obs["delivered"] else "wrong" if obs["status"] == "delivered" else "withheld"
            decision = data["decisions"][key]
            # First try the general composer. If it abstains, run the original hive, then the post-worker relay.
            table = grade(questions[tid], decision["table"], sdk)
            relay = grade(questions[tid], decision["relay"][gen], sdk)
            if relay["submitted"] and orig != "withheld":
                raise ValueError("relay replaced a delivered job")
            def status(result, fallback):
                return ("correct" if result["passed"] else "wrong") if result["submitted"] else fallback
            observed = {"original": orig, "table_only": status(table, "withheld"),
                        "table_fallback": status(table, orig), "relay_fallback": status(relay, orig),
                        "both": status(table, status(relay, orig))}
            for arm, value in observed.items():
                outcomes[arm][tid] = value
            cases.setdefault(tid, {})[gen] = {"table": table, "relay": relay, "outcomes": observed}
        arms[gen] = {
            arm: {"scores": score({k: v == "correct" for k, v in flags.items()}),
                  "counts": dict(Counter(flags.values()))}
            for arm, flags in outcomes.items()
        }
    return {"decisions_sha256": digest(receipts.read_bytes()), "archive_sha256": digest((HERE / "ledger.json").read_bytes()),
            "official_tasks_matched": len(questions), "arms": arms, "cases": cases}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decisions", type=Path, default=HERE / "decisions.json")
    parser.add_argument("--sdk", type=Path, help="CPython WASI SDK for a submitted Python module")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.decisions, args.sdk)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    for generation, arms in result["arms"].items():
        print(generation, {arm: (r["scores"]["tasks"], r["scores"]["kinds"]) for arm, r in arms.items()})
