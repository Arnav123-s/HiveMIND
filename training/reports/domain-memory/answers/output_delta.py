"""Apply the released pure-water output veto to the saved actual replies and worker outputs."""
import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent


def replay(checkout, datasets):
    sys.path.insert(0, str(checkout))
    from team import water_phase

    panel = {r["id"]: r["prompt"] for r in json.loads((HERE / "panel.json").read_text())}
    out = {}
    for path in datasets:
        for row in json.loads(path.read_text())["rows"]:
            arm = out.setdefault(row["arm"], {"tasks": 0, "replies_checked": 0, "worker_outputs_checked": 0,
                                             "tasks_in_scope": [], "contradictions": []})
            arm["tasks"] += 1
            ident = row["id"]
            phase = water_phase.output_check_phase(panel[ident])
            if phase:
                arm["tasks_in_scope"].append(ident)
            candidates = [("visible", row["text"])] + [(m["who"], m["answer"]) for m in row["members"]]
            for source, value in candidates:
                if not value:
                    continue
                arm["replies_checked" if source == "visible" else "worker_outputs_checked"] += 1
                if water_phase.contradicts(phase, value):
                    arm["contradictions"].append({"id": ident, "source": source, "expected": phase, "actual": value})
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("results", type=Path, nargs="+")
    args = parser.parse_args()
    data = replay(args.checkout.resolve(), args.results)
    args.out.write_text(json.dumps(data, indent=2) + "\n")
