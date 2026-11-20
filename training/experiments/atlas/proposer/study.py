"""Enumerate typed requests, solve the resulting programs and grade on an external key."""
import argparse
from collections import Counter, defaultdict
from itertools import permutations
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
OPS = {
    "site": ("rows", "rows", "keep rows from site {site}"),
    "count": ("rows", "count", "count rows with label {label}"),
    "sum": ("rows", "totals", "sum the quantities for each observed label"),
    "winner": ("totals", "label", "return the label with the greatest total (lexical tie-break; null when empty)"),
}


def programs():
    found = {}
    for depth in range(1, 4):
        for path in permutations(OPS, depth):
            current = "rows"
            for op in path:
                input_type, output_type, _ = OPS[op]
                if input_type != current:
                    break
                current = output_type
            else:
                if current != "rows":
                    name = "_".join(op for op in path if op != "sum" or path[-1] != "winner")
                    found[name] = path
    return found


def evaluate(path, scenario):
    value = scenario["events"]
    for op in path:
        if op == "site":
            value = [row for row in value if row["site"] == scenario["site"]]
        elif op == "count":
            value = sum(row["label"] == scenario["label"] for row in value)
        elif op == "sum":
            totals = Counter()
            for row in value:
                totals[row["label"]] += row["qty"]
            value = dict(totals)
        elif op == "winner":
            value = min(value, key=lambda label: (-value[label], label), default=None)
    return value


def direct(name, scenario):
    # Fixed baseline written directly from the six public job descriptions.
    totals, occurrences = defaultdict(int), defaultdict(int)
    for row in scenario["events"]:
        if name.startswith("site_") and row["site"] != scenario["site"]:
            continue
        key = row["label"]
        totals[key] += row["qty"]
        occurrences[key] += 1
    if name.endswith("count"):
        return occurrences[scenario["label"]]
    if name.endswith("sum"):
        return dict(totals)
    tied = [key for key in totals if totals[key] == max(totals.values())]
    return sorted(tied)[0] if tied else None


def render(path, scenario):
    params = {k: json.dumps(scenario[k], ensure_ascii=False) for k in ("site", "label")}
    return "Using the event rows, " + ", then ".join(OPS[op][2].format(**params) for op in path) + "."


def grade(corpus, keys):
    catalog = programs()
    if set(keys) != {s["id"] for s in corpus} or len(corpus) != len(keys):
        raise ValueError("scenario and key IDs must match one-to-one")
    summaries, receipts, witnesses = {}, [], {}
    single = {OPS[p[0]][1]: p for p in catalog.values() if len(p) == 1}
    arms = ("one_operator", "same_output_type", "composed", "direct")
    for sample in corpus:
        scenario_id = sample["id"]
        if set(keys[scenario_id]) != set(catalog):
            raise ValueError(f"Incomplete key: {scenario_id}")
        for name, path in catalog.items():
            truth = keys[scenario_id][name]
            row = {"scenario": scenario_id, "id": name, "ops": path, "request": render(path, sample),
                   "expected": truth, "outputs": {}}
            for arm in arms:
                selected = path
                if arm == "one_operator" and len(path) != 1:
                    selected = None
                if arm == "same_output_type":
                    selected = single.get(OPS[path[-1]][1])
                status, actual = "unsupported", None
                if selected is not None:
                    actual = direct(name, sample) if arm == "direct" else evaluate(selected, sample)
                    status = "correct" if type(actual) is type(truth) and actual == truth else "wrong"
                row["outputs"][arm] = {"status": status, "value": actual}
                summaries.setdefault(arm, Counter())[status] += 1
            receipts.append(row)
        for name in ("count", "sum", "winner"):
            pairs_differ = keys[scenario_id][name] != keys[scenario_id]["site_" + name]
            witnesses[name] = witnesses.get(name, 0) + int(pairs_differ)
    return {"programs": catalog, "scenarios": len(corpus), "summary": summaries,
            "scenarios_where_site_changes_answer": witnesses, "receipts": receipts}


def file_digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=HERE / "panel" / "cases.json")
    parser.add_argument("--keys", type=Path, default=HERE / "panel" / "keys.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = grade(json.loads(args.cases.read_text()), json.loads(args.keys.read_text()))
    result["sha256"] = {s.name: file_digest(s) for s in (Path(__file__), args.cases, args.keys)}
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
