"""Replay the frozen, independent shipping panel through real WASI saved-method calls."""
from collections import Counter
from decimal import Decimal, ROUND_CEILING
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
from team import saved
from training.experiments.atlas.traces.trace import GuardedTrace
from training.experiments.fieldwork import work
from training.experiments.fieldwork.guest import Guest

SOURCE = ROOT / "training/reports/retained-skills/shipping/bank"
FROZEN = "b6531e94e68e4d2e67e978b5511f2d123131355443f1dfa9604cc90dca91d219"
POOL = "def solve(x):\n    return 250 + 90 * ((sum(x['grams']) + 499) // 500) if x['grams'] else 0"


def fee(weights, pooled):
    if not weights:
        return 0
    bins = [sum(weights)] if pooled else weights
    return 250 + 90 * sum(int((Decimal(w) / 500).to_integral_value(rounding=ROUND_CEILING)) for w in bins)


def command(items, convention):
    prompt = "Calculate the depot shipping fee for " + " and ".join(i + " kg" for i in items)
    return prompt + (" using " + convention + " rounding" if convention else "")


def pooled_bank(root, guest):
    def examples(rows):
        return [{"input": {"grams": r}, "output": fee(r, True)} for r in rows]

    spec = {"name": saved.SHIPPING[0], "task": saved.SHIPPING[1],
            "examples": examples([[73, 46], [91, 94, 33]]), "validation": examples([[78, 33, 37], [29, 51]]),
            "jobs": [{"id": "one", "input": {"grams": [41, 49]}}]}
    target = root / "mixed"
    shutil.copytree(SOURCE, target)
    result = work.work(spec, guest, lambda *_: {"source": POOL, "usage": {}}, root / "pool-qualification",
                       target, rounds=1)
    assert result["validated"] == 2 and len(work.load_bank(target)) == 2
    return target


def prepare(trace, credential):
    log = []
    for index, convention in enumerate((None, "per-parcel", "pooled")):
        draws = [[f"0.{89 + index*200 + k:03d}", f"0.{51+k:03d}"] for k in range(3)]
        for items in draws:
            receipt = trace.answer(command(items, convention))
            log.append(dict(step="warmup", convention=convention, input=items,
                            result=(receipt or {}).get("value"), **trace.last))
        packet = [dict(input=row["input"], output=row["pooled"] if convention == "pooled" else row["per"])
                  for row in credential if row["rule"] == convention]
        before = (trace.guest.calls, trace.guest.fuel)
        qualification = trace.qualify(command(draws[0], convention), packet)
        log.append(dict(step="qualify", convention=convention,
                        calls=trace.guest.calls-before[0], fuel=trace.guest.fuel-before[1], **qualification))
    return log


def compare(sdk):
    cases = json.loads((HERE / "shipping.json").read_text())
    credential = json.loads((HERE / "credential.json").read_text())
    module_path = ROOT / "training/experiments/atlas/traces/trace.py"
    assert hashlib.sha256(module_path.read_bytes()).hexdigest() == FROZEN
    guest = Guest(sdk)
    out = {}
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for profile, bank in (("per_bank", SOURCE), ("mixed_bank", pooled_bank(root, guest))):
            out[profile] = {}
            for arm in ("stock", "handwritten", "cold", "warm"):
                trace = GuardedTrace(bank=bank, sibling_bank=root / f"{profile}-{arm}", guest=guest)
                setup = prepare(trace, credential) if arm == "warm" else []
                rows, tally = [], Counter()
                method = arm if arm in ("stock", "handwritten") else "guarded"
                for case in cases:
                    result = trace.answer(case["message"], mode=method) or {}
                    delivered = result.get("status") == "answered"
                    expected, value = case[profile], result.get("value")
                    if delivered:
                        outcome = "correct" if expected is not None and value == expected else "wrong"
                    else:
                        outcome = "justified_abstention" if expected is None else "missed"
                    tally[outcome] += 1
                    tally["guest_calls"] += trace.last["calls"]
                    tally["guest_inputs"] += trace.last["guest_inputs"]
                    tally["fuel"] += trace.last["fuel"]
                    rows.append(dict(id=case["id"], expected=expected, value=value, status=result.get("status"),
                                     outcome=outcome, **trace.last))
                out[profile][arm] = {"counts": dict(tally), "qualification": setup, "rows": rows}
    return {"trace_sha256": FROZEN, "wasm_sha256": hashlib.sha256((sdk / "python.wasm").read_bytes()).hexdigest(),
            "per_bank_files": {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in SOURCE.glob("*.json")},
            "model_generations": 0, "results": out}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    args.out.write_text(json.dumps(compare(args.sdk), indent=2) + "\n")
