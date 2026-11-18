"""Compare G47 with its parent by paired job and route on other seeds' results.

python -m training.experiments.retained_skills_replay --archives /path/to/grade-zips
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

from training import kinds

ROOT = Path(__file__).resolve().parents[1] / "reports"
MANIFEST = ROOT / "checked-delivery" / "g47-headroom.json"
RESULTS = ROOT / "retained-skills" / "g47.json"


def load(archives):
    spec = json.loads(MANIFEST.read_text())
    by_seed = defaultdict(dict)
    rosters = {}
    seats = defaultdict(Counter)
    commits = set()
    for entry in spec["grade_archives"]:
        name = entry["name"]
        path = archives / (name + ".zip")
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError(f"Digest mismatch for {name}")
        with ZipFile(path) as z:
            contents = [f for f in z.infolist() if f.filename.endswith("_mixed.json")]
            if len(contents) != 1 or contents[0].file_size > 2_000_000:
                raise ValueError(f"Invalid archive contents for {name}")
            sitting = json.loads(z.read(contents[0]))
        arm = name.split("-")[1]
        info = sitting["summary"]
        seed = info["seed"]
        roster = info["members"].split(",")
        if rosters.setdefault(arm, roster) != roster or arm in by_seed[seed]:
            raise ValueError(f"Nonconstant roster or duplicate seed for {name}")
        commits.add(info["code"])
        grades = {}
        for t in sitting["tasks"]:
            if type(t["ok"]) is not bool or t["id"] in grades:
                raise ValueError(f"Invalid task grade in {name}")
            grades[t["id"]] = t
            seats[arm].update(m["who"] for m in t["members"])
        by_seed[seed][arm] = grades
    labels = {label for maker in kinds.ALL for label in kinds.written(maker.KIND)}
    rows = []
    for seed, grades in sorted(by_seed.items()):
        old, new = grades["before"], grades["after"]
        if old.keys() != new.keys():
            raise ValueError(f"Task IDs differ in seed {seed}")
        for tid, t in sorted(old.items()):
            other = new[tid]
            if t["kind"] not in labels or any(t[k] != other[k] for k in ("task", "kind", "field")):
                raise ValueError(f"Prompt or registered task-kind mismatch for {tid}")
            rows.append({"seed": seed, "id": tid, "kind": t["kind"], "before": t["ok"], "after": other["ok"],
                         "prompt_sha256": hashlib.sha256(t["task"].encode()).hexdigest()})
    return rows, {"grading_commits": sorted(commits), "rosters": rosters, "graded_member_seats": seats}


def strict_winners(training_rows):
    """The only selector. One vote per training job. A tie or an unseen kind keeps the parent."""
    differences = Counter()
    for r in training_rows:
        differences[r["kind"]] += int(r["after"]) - int(r["before"])
    return {k for k, delta in differences.items() if delta > 0}


def run(archives):
    rows, provenance = load(archives)
    for held in sorted({r["seed"] for r in rows}):
        winners = strict_winners([r for r in rows if r["seed"] != held])
        for r in rows:
            if r["seed"] == held:
                r["selected"] = "after" if r["kind"] in winners else "before"
    scopes = {"all": rows, "hard": [r for r in rows if r["id"].startswith("h")],
              "easy": [r for r in rows if r["id"].startswith("e")]}
    comparisons = {}
    for scope, subset in scopes.items():
        both = sum(r["before"] and r["after"] for r in subset)
        old = sum(r["before"] for r in subset)
        new = sum(r["after"] for r in subset)
        upper = old + new - both
        comparisons[scope] = {"tasks": len(subset), "both_passed": both, "before_only": old-both,
                              "after_only": new-both, "neither_passed": len(subset)-upper, "always_before": old,
                              "always_after": new, "kind_selector": sum(r[r["selected"]] for r in subset),
                              "chose_after": sum(r["selected"] == "after" for r in subset), "oracle_union": upper}
    folds = {}
    for seed in sorted({r["seed"] for r in rows}):
        held = [r for r in rows if r["seed"] == seed]
        folds[seed] = {"tasks":len(held), "always_before":sum(r["before"] for r in held),
                       "always_after":sum(r["after"] for r in held),
                       "kind_selector":sum(r[r["selected"]] for r in held),
                       "chose_after_ids":[r["id"] for r in held if r["selected"] == "after"]}
    return {"source_manifest": "../checked-delivery/g47-headroom.json", "generation": "g47",
            "source_run": "https://github.com/Arnav123-s/HiveMIND/actions/runs/44313055326",
            "selector": "Hold out an entire exam seed. For a registered task-kind label, choose after only if it delivered more passing jobs than before on the other seven seeds. Otherwise choose before. The selector receives only the category of a test job.",
            "interpretation": "The oracle union uses the final task grades on the test jobs and is an upper bound for choosing one archived delivery. The evaluation uses known exam category labels. The recorded grades do not include model system prompt transcripts. Comparisons describe single archived runs per job.",
            "provenance": provenance, "comparisons": comparisons, "held_out_seeds": folds,
            "discordant_jobs": [r for r in rows if r["before"] != r["after"]]}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--archives", type=Path, required=True)
    cli.add_argument("--write", action="store_true", help="write the recorded result; default verifies it")
    args = cli.parse_args()
    result = json.dumps(run(args.archives), indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.write:
        RESULTS.parent.mkdir(exist_ok=True)
        RESULTS.write_text(result)
    elif RESULTS.read_text() != result:
        raise ValueError("The replay differs from the recorded result")
    print(json.dumps(json.loads(result)["comparisons"], indent=2))


if __name__ == "__main__":
    main()
