"""Count cases covered by at least one archived candidate, with hindsight."""

import gzip
import json
from collections import Counter
from pathlib import Path

from . import cases


EVIDENCE = Path(__file__).resolve().parents[2] / "reports/rule_lab/fieldwork/evidence.json.gz"
FIRST = {
    "exam": ("g41", "recruit", "4b", "q35", "coder7b"),
    "confirmation": ("4b", "q35", "coder7b"),
}
ADDITIONAL = (("4b", "cold"), ("4b", "grown"), ("coder7b", "coached"))


def read_results():
    with gzip.open(EVIDENCE, "rt") as stream:
        return json.load(stream)["results"]


def coverage(results, split, task, include_additional=False):
    arms = [(writer, "first") for writer in FIRST[split]]
    if include_additional:
        arms.extend(ADDITIONAL)
    runs = [results[f"{writer}/{split}/{mode}/{task}.json"] for writer, mode in arms]
    bank = cases.static_cases(task, split) + [cases.stress(task, split)]
    for run in runs:
        tests = run["tests"]
        if (
            run["task"] != task
            or run["grader_version"] != 2
            or len(tests) != len(bank)
            or not tests[-1]["detail"]["stress"]
            or tests[-1]["detail"]["expected"] != bank[-1][1]
            or run["correct"] != sum(row["ok"] for row in tests)
        ):
            raise ValueError(f"Incompatible archived grades for {task} on {split}")
    groups, passed = Counter(), Counter()
    any_correct = 0
    for index, (_, expected) in enumerate(bank):
        if expected[0] is None:
            group = "unreachable" if task == "ferry" else "infeasible"
        elif task == "ferry":
            group = "waiver essential" if expected[1] else "reachable without waiver at optimum"
        else:
            group = "one optimal schedule" if expected[1] == 1 else "tied optimal schedules"
        ok = any(run["tests"][index]["ok"] for run in runs)
        groups[group] += 1
        passed[group] += ok
        any_correct += ok
    return {
        "conditions": len(runs),
        "distinct_sources": len({run["digest"] for run in runs}),
        "best_program": max(run["correct"] for run in runs),
        "any_program": any_correct,
        "cases": len(bank),
        "any_stress_pass": any(run["tests"][-1]["ok"] for run in runs),
        "groups": {group: [passed[group], size] for group, size in groups.items()},
    }


def main():
    results = read_results()
    for split in FIRST:
        for task in ("roster", "ferry"):
            for additional in (False, True):
                label = "plus public variants" if additional else "first submissions"
                print(split, task, label, json.dumps(coverage(results, split, task, additional)))


if __name__ == "__main__":
    main()
