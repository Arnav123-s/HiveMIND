"""Run duration relations, then separately grade the immutable set of survivors."""
import argparse
import hashlib
import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT))
from training.experiments.fieldwork.guest import Guest


MODULES = ROOT / "training/experiments/atlas/module_recovery"
HOLDOUT_SHA = "a80490174d28b72b7b453553c6680a7c8d8fe2458e54d881e68659a01f58db2e"
INPUTS = (
    [("number_roundtrip", n) for n in (2, 14, 55, 83, 152, 591, 2771, 3613, 13321, 198129, 407811)]
    + [("text_roundtrip", t) for t in ("8s", "16m", "3h", "8h12s", "16h7m", "13m5s", "3h15m12s", "78h", "93h18m47s")]
    + [("add_fragments", f) for f in (("3h", "12s"), ("4h", "8m"), ("13m", "5s"), ("38h", "19m", "47s"))]
)
WRAPPER = """
def solve(x):
    relation, value = x
    if relation == 'number_roundtrip':
        v = to_text(value)
        assert type(v) is str
        return to_seconds(v)
    if relation == 'text_roundtrip':
        v = to_seconds(value)
        assert type(v) is int
        return to_text(v)
    if relation == 'add_fragments':
        parts = [to_seconds(v) for v in value]
        whole = to_seconds(''.join(value))
        assert type(whole) is int and all(type(n) is int for n in parts)
        return whole == sum(parts)
    return to_seconds(value) if relation == 'to_seconds' else to_text(value)
"""


def sha(data):
    return hashlib.sha256(data).hexdigest()


def candidates():
    result = {p.parent.name: p.read_text() for p in sorted((MODULES / "g52").glob("*/durations.py"))}
    if set(result) != {"h20000523_03", "h20000527_03"}:
        raise RuntimeError("Original G52 pair unavailable")
    result.update({p.stem: p.read_text() for p in sorted((HERE / "controls").glob("*.py"))})
    return result


def execute(guest, source, inputs):
    outputs, fuel, _ = guest.run(source + "\n" + WRAPPER, inputs, fuel=2_000_000_000)
    return outputs, fuel


def select(guest, programs):
    rows = []
    for name, source in programs.items():
        observed, fuel = execute(guest, source, INPUTS)
        checks = []
        for (relation, value), actual in zip(INPUTS, observed, strict=True):
            expected = True if relation == "add_fragments" else value
            outcome = actual.get("value")
            checks.append({"relation": relation, "value": value, "observed": actual,
                           "passed": type(outcome) is type(expected) and outcome == expected})
        rows.append({"candidate": name, "sha256": sha(source.encode()), "fuel": fuel, "checks": checks,
                     "pass": all(c["passed"] for c in checks)})
    selection = {}
    for scope in ("real", "all"):
        eligible = sorted((r for r in rows if r["pass"] and (scope == "all" or r["candidate"].startswith("h2000"))),
                          key=lambda r: r["sha256"])
        selection[scope] = {"survivors": [r["candidate"] for r in eligible],
                            "single": eligible[0]["candidate"] if eligible else None}
    return {"source_sha256": sha(Path(__file__).read_bytes()), "protocol_sha256": sha((HERE / "protocol.md").read_bytes()),
            "python_wasm_sha256": sha((guest.sdk / "python.wasm").read_bytes()), "runs": rows, "selection": selection}


def grade(guest, programs, recorded):
    if sha((MODULES / "holdout.py").read_bytes()) != HOLDOUT_SHA:
        raise ValueError("Holdout changed")
    from training.experiments.atlas.module_recovery.holdout import cases, score
    receipts = {}
    for row in recorded["runs"]:
        name = row["candidate"]
        if row["sha256"] != sha(programs[name].encode()):
            raise ValueError("Candidate changed after selection")
        outputs, fuel = execute(guest, programs[name], [(f, x) for f, x, _ in cases()])
        receipts[name] = {"grade": score([r.get("value") for r in outputs]), "fuel": fuel, "outputs": outputs}
    return {"selected_before_grading": recorded["selection"], "holdout_sha256": HOLDOUT_SHA, "runs": receipts}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("select", "grade"))
    parser.add_argument("--sdk", required=True, type=Path)
    parser.add_argument("--selection", type=Path, default=HERE / "selection.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    guest, programs = Guest(args.sdk), candidates()
    if args.phase == "select":
        result = select(guest, programs)
    else:
        raw = args.selection.read_bytes()
        result = grade(guest, programs, json.loads(raw))
        result["selection_sha256"] = sha(raw)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
