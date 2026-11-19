"""Compare three routes into the same saved per-parcel shipping method on a frozen panel."""
import argparse
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
GRADES = ("correct_call", "incorrect_arguments", "missed_call", "false_call", "true_decline",
          "execution_failure", "incorrect_fee")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ObservedGuest:
    """Log actual method calls including invocations that return an error rather than a usable answer."""
    def __init__(self, guest):
        self.guest = guest
        self.inputs = []

    def run(self, program, inputs, fuel):
        self.inputs.extend(inputs)
        return self.guest.run(program, inputs, fuel=fuel)


def load_extractor(path):
    spec = importlib.util.spec_from_file_location("shipping_study_adapter", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.extract_shipping


def expected_price(weights):
    return 0 if not weights else 250 + 90 * sum((w + 499) // 500 for w in weights)


def exact_weights(got, wanted):
    return isinstance(got, list) and all(type(w) is int for w in got) and got == wanted


def grade(outcome, weights, price):
    if weights is None:
        return "false_call" if outcome["called"] else "true_decline"
    if not outcome["called"]:
        return "missed_call"
    if not exact_weights(outcome["actual_weights"], weights):
        return "incorrect_arguments"
    if not outcome["released"]:
        return "execution_failure"
    if type(outcome["fee_cents"]) is not int or outcome["fee_cents"] != price:
        return "incorrect_fee"
    return "correct_call"


def observe(status, fee, inputs):
    if inputs and any(x != inputs[0] for x in inputs[1:]):
        raise RuntimeError("the saved versions were run on different argument objects")
    return {"called": bool(inputs), "actual_weights": inputs[0].get("grams") if inputs else None,
            "released": status == "answered", "status": status, "fee_cents": fee}


def run(checkout, sdk, adapter, cases_path):
    sys.path.insert(0, str(checkout.resolve()))
    from team import saved
    from training.experiments.fieldwork import work
    from training.experiments.fieldwork.guest import Guest

    cases = json.loads(cases_path.read_text())
    extract = load_extractor(adapter)
    bank = checkout / "training/reports/retained-skills/shipping/bank"
    versions = work.load_bank(bank)
    if not versions or any(r["task"] != "depot_shipping_fee" for r in versions):
        raise ValueError("expected the per-parcel depot shipping bank from the named checkout")
    guest = Guest(sdk.resolve())
    positives = [r["weights"] for r in cases if r["weights"] is not None]
    if any(not isinstance(ws, list) or any(type(w) is not int or w <= 0 for w in ws) for ws in positives):
        raise ValueError("invalid positive-label weights")
    # Independent contract arithmetic, cross-checked against the immutable program before evaluating routes.
    for version in versions:
        rows = guest.run(version["source"], [{"grams": ws} for ws in positives], fuel=30_000_000_000)[0]
        if len(rows) != len(positives) or not all(type(row.get("value")) is int and row["value"] == expected_price(ws)
                                                  for row, ws in zip(rows, positives)):
            raise RuntimeError("saved fee method and independent contract arithmetic disagree")

    results = []
    for row in cases:
        observer = ObservedGuest(guest)
        result = saved.answer(row["text"], bank=bank, runner=observer)
        baseline = observe(result["status"] if result else "declined", result.get("value") if result else None,
                           observer.inputs)
        weights = extract(row["text"])
        candidate = observe("declined", None, [])
        if weights is not None:
            observer = ObservedGuest(guest)
            answers, conflict = work.shared_results(versions, observer, [dict(id="request", input={"grams": weights})])
            candidate = observe("missing" if conflict else "answered", None if conflict else answers[0]["value"],
                                observer.inputs)
        arms = {"baseline": baseline, "candidate": candidate, "always_decline": observe("declined", None, [])}
        gold = row["weights"]
        fee = None if gold is None else expected_price(gold)
        for out in arms.values():
            out["grade"] = grade(out, gold, fee)
        results.append({"id": row["id"], "group": row["group"], "expected_weights": gold,
                        "expected_fee_cents": fee, "arms": arms})

    summary = {}
    for name in ("baseline", "candidate", "always_decline"):
        counts = Counter(row["arms"][name]["grade"] for row in results)
        summary[name] = {label: counts[label] for label in GRADES}
        summary[name]["correct_decisions"] = counts["correct_call"] + counts["true_decline"]
        summary[name]["incorrect_arguments_same_numeric_fee"] = sum(
            row["arms"][name]["grade"] == "incorrect_arguments" and row["arms"][name]["released"]
            and row["arms"][name]["fee_cents"] == row["expected_fee_cents"] for row in results)
    return {"labels_sha256": digest(cases_path), "adapter_sha256": digest(adapter),
            "saved_router_sha256": digest(checkout / "team/saved.py"),
            "runner_sha256": digest(Path(__file__)), "wasi_python_sha256": digest(sdk / "python.wasm"),
            "saved_program_digests": [r["digest"] for r in versions], "summary": summary, "rows": results}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checkout", type=Path, required=True)
    p.add_argument("--sdk", type=Path, required=True, help="CPython WASI SDK including python.wasm and lib/")
    p.add_argument("--adapter", type=Path, default=HERE / "adapter.py")
    p.add_argument("--cases", type=Path, default=HERE / "cases.json")
    p.add_argument("--out", type=Path, help="write all inputs, fees, per-case decisions, counts and hashes")
    args = p.parse_args()
    result = run(args.checkout.resolve(), args.sdk.resolve(), args.adapter, args.cases)
    print(json.dumps(result["summary"], indent=2))
    if args.out:
        args.out.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
