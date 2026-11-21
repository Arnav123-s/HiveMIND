"""Exercise the production chooser using historical failed modules, then two public desk controls."""
import argparse
import json
from pathlib import Path
import random
import re
import tempfile
from unittest.mock import patch

from team import deliverables, module_witness, solo
from training.experiments.astra_orders.module_checks import study
from training.experiments.fieldwork.guest import Guest
from training.kinds import h_prog_queue

HERE = Path(__file__).resolve().parent


def decide(task, name, programs):
    with tempfile.TemporaryDirectory() as tmp:
        probe = module_witness.Probe(task, name)
        tries = []
        for i, source in enumerate(programs):
            folder = Path(tmp) / str(i)
            folder.mkdir()
            (folder / name).write_text(source)
            delivery = deliverables.inspect(task, folder, [name])
            evidence = probe.inspect(folder, delivery["byte_hashes"].get(name))
            tries.append(dict(answer="independent agreement", work=str(folder), arm=i,
                              delivery=delivery, module_check=evidence))
        pairs = solo.agreeing(tries, task)
        selected = solo._winner(tries, pairs, task)
        a,b = [t["module_check"] for t in tries]
        return {"selected": selected["arm"] if selected is not None else None,
                "public_calls": len(probe.calls), "matches": sum(x == y and x is not None for x, y in zip(a["observed"], b["observed"])),
                "witness": probe.witness(a, b), "complete_domain": probe.complete}


def evaluate(sdk):
    historical = json.loads((HERE.parent / "module_checks" / "fixtures.json").read_text())
    texts = json.loads((HERE / "archived_requests.json").read_text())
    cases = []
    for row in historical["cases"]:
        name = row["filename"]
        source = historical["source_files"][row["lookup_alone"]["source"]]
        task = texts[str(row["archive_id"])]["task"]
        assert deliverables.wanted(task) == [name]
        cases.append({"archive_id":row["archive_id"],
                      **decide(task, name, [source, study.lookup_peer(name, fixed=False)])})
    _, _, prompt, _ = h_prog_queue.make(random.Random(21112026))
    desk = h_prog_queue.solution(prompt)
    renamed = re.sub(r"\btodo\b", "pending_queue", desk)
    assert renamed != desk
    # The creator's module is used as a comparison subject only inside this offline control.
    # Neither source, the hidden checker, nor expected queue outputs enter the routing policy.
    with patch.object(module_witness.saved, "guest", return_value=Guest(sdk)):
        wider = decide(prompt, "desk.py", [desk, renamed])
        narrower = ("Save desk.py. Implement this complete two-call interface. Print ready.\n"
                    "The complete required behavior is one run of the checks below, in order, on a fresh module.\n"
                    "Required checks:\n```python\nassert serve([['Ada', 0, 2, 1]]) == [['Ada', 0, 1]]\n"
                    "assert left([['Ada', 0, 2, 1]]) == []\n```")
        finite = decide(narrower, "desk.py", [desk, renamed])
        subset = ("The list of rows may be in any order. Any nonempty subset of the rows is valid. "
                  "size(rows) returns a value. Compute for these rows: [[1], [2], [3]].")
        smaller = decide(subset, "desk.py", ["def size(rows): return len(rows)", "def size(rows): return 0"])
    return {"lookups": cases, "renamed_queue_modules": wider, "explicit_finite_queue_interface": finite,
            "smallest_observed_input": smaller}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sdk", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.write_text(json.dumps(evaluate(args.sdk), indent=2, sort_keys=True) + "\n")
