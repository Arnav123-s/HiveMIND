"""Run the saved-method routing stress probe on a checkout with a CPython WASI SDK."""
import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


class Boundary(Exception):
    """The request would now call a model or the ordinary worker team."""


def no_model(base, messages, **options):
    from team import talk
    raise Boundary("routing-model" if messages[0]["content"] == talk.DECIDE else "talk")


def no_workers(*args, **options):
    raise Boundary("fallback")


def run(checkout, sdk, cases):
    sys.path.insert(0, str(checkout.resolve()))
    from team import saved, solo, talk, ternary
    from training.experiments.fieldwork.guest import Guest
    from training.experiments.fieldwork import work

    source_dir = checkout / "training/reports/retained-skills"
    shipping, = work.load_bank(source_dir / "shipping/bank")
    invoice = json.loads((source_dir / "work-order-cases.json").read_text())
    with TemporaryDirectory() as tmp:
        bank = Path(tmp) / "bank"
        work.admit(bank, shipping)
        for key in ("per_line", "per_invoice"):
            source = invoice["programs"][key]
            work.admit(bank, dict(task=invoice["name"], description=invoice["description"], source=source,
                                  digest=work.fingerprint(source), public=2, validation=2, parents=[]))
        guest = Guest(sdk.resolve())
        results = []
        with (patch.dict(os.environ, {"HIVE_BANK": str(bank)}), patch.object(saved, "guest", lambda: guest),
              patch.object(ternary, "chat", no_model), patch.object(solo, "first", no_workers)):
            for group, key, message, expected, target in cases:
                try:
                    result = talk.reply(message, base="stub-dna", run_dir=tmp)["saved"]
                    outcome = result["task"] if result["status"] == "answered" else result["status"]
                    value, fields = result.get("value"), result.get("input")
                except Boundary as exc:
                    outcome, value, fields = str(exc), None, None
                correct = (outcome == expected and value == target) or (
                    expected == "decline" and outcome in ("fallback", "missing", "ambiguous"))
                results.append(dict(group=group, id=key, expected=expected, target=target, actual=outcome,
                                    value=value, input=fields, correct=correct))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True, help="HiveMIND source directory to evaluate")
    parser.add_argument("--sdk", type=Path, required=True, help="WASI directory containing python.wasm and lib/")
    parser.add_argument("--out", type=Path, help="write raw observations here")
    args = parser.parse_args()
    if not (args.sdk / "python.wasm").is_file() or not (args.sdk / "lib").is_dir():
        parser.error("the SDK must contain python.wasm and its lib directory")
    cases = json.loads(Path(__file__).with_name("cases.json").read_text())
    results = run(args.checkout.resolve(), args.sdk, cases)
    for group in dict.fromkeys(row["group"] for row in results):
        rows = [row for row in results if row["group"] == group]
        counts = dict(Counter(row["actual"] for row in rows))
        print(f"{group} {sum(row['correct'] for row in rows)}/{len(rows)} {counts}")
    if args.out:
        args.out.write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
