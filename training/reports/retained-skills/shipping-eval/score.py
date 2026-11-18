"""Replay four recorded shipping programs with independent arithmetic fixtures in a CPU WebAssembly guest."""
import argparse
from decimal import Decimal, ROUND_CEILING
import gzip
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))
from training.experiments.fieldwork import arithmetic_repair  # noqa: E402
from training.experiments.fieldwork.guest import Guest  # noqa: E402


def digest(data):
    return hashlib.sha256(data).hexdigest()


def verify_fixtures(fixtures, protocol):
    for key in ("cases", "controls"):
        original = (json.dumps(fixtures[key], indent=1, sort_keys=True) + "\n").encode()
        if digest(original) != protocol["files"][key + ".json"]:
            raise ValueError(f"Frozen {key} digest differs")
    if digest(fixtures["mechanism_control"].encode()) != "dc8486dd044b420121dd2646af78d4aaee3fbe12f88144e70af88d2ae227fca9":
        raise ValueError("Mechanism control changed")
    seen = {tuple(c) for c in fixtures["old_excluded_weight_multisets"]}
    if len(seen) != protocol["prior_unique_gram_multisets_excluded"]:
        raise ValueError("Incomplete prior input list")

    def ceil_units(weight):
        return int((Decimal(weight) / 500).to_integral_value(rounding=ROUND_CEILING))

    for policy, rows in fixtures["cases"].items():
        if len(rows) != protocol["cases_per_policy"]:
            raise ValueError(f"Wrong case count for {policy}")
        for row in rows:
            grams = row["input"]["grams"]
            unordered = tuple(sorted(grams))
            if unordered in seen:
                raise ValueError(f"Repeated shipment in {row['id']}")
            seen.add(unordered)
            units = sum(ceil_units(g) for g in grams) if policy == "A" else ceil_units(sum(grams))
            if row["expected"] != (250 + 90 * units if grams else 0):
                raise ValueError(f"Invalid reference fee for {row['id']}")


def replay(sdk):
    protocol_bytes = (HERE / "protocol.json").read_bytes()
    if digest(protocol_bytes) != "679fe032443e230639348faa52ebe77d0d6b91ec4b07606a8562399f2fcf0f45":
        raise ValueError("Original freeze protocol changed")
    live = json.loads((HERE.parent / "shipping-live.json").read_text())
    if digest((sdk / "python.wasm").read_bytes()) != live["runtime"]["python_wasm_sha256"]:
        raise ValueError("Use the recorded WebAssembly interpreter")
    fixtures = json.loads(gzip.decompress((HERE / "fixtures.json.gz").read_bytes()))
    verify_fixtures(fixtures, json.loads(protocol_bytes))
    guest = Guest(sdk)
    results = {}
    # Avoid rerunning byte-identical programs on the same examples. No grade is shared across different inputs.
    cache = {}

    def grade(source, rows):
        key = source, json.dumps(rows, sort_keys=True)
        if key not in cache:
            outputs, _, _ = guest.run(source, [r["input"] for r in rows])
            passed = [type(o.get("value")) is int and o["value"] == r.get("output", r.get("expected"))
                      for o, r in zip(outputs, rows, strict=True)]
            by_stratum = {s: sum(ok and r["stratum"] == s for ok, r in zip(passed, rows))
                          for s in sorted({r["stratum"] for r in rows if "stratum" in r})}
            cache[key] = {"passed": sum(passed), "total": len(rows), "errors": sum("error" in o for o in outputs),
                          "by_stratum": by_stratum,
                          "output_sha256": digest(json.dumps(outputs, sort_keys=True, separators=(",", ":")).encode())}
        return cache[key]

    def public_count(source, public):
        return grade(source, public)["passed"]

    def arms(source, examples):
        selected = arithmetic_repair.select(source, examples, public_count, limit=8)
        edits = list(arithmetic_repair.regroup(source, limit=8))
        return {"raw": source, "public_selected": selected["program"] if selected else source,
                "first_edit": edits[0]["source"] if edits else source}, len(edits), bool(selected)

    chosen_a = None
    for order in (r for r in live["rounds"] if r["arm"] == "learning"):
        case, examples = order["case"], order["public_examples"]
        policy = case.split("-")[1]
        record = []
        for attempt in order["attempts"]:
            # The selector sees only public examples. All three programs are fixed before scoring qualification and new jobs.
            sources, count, selected = arms(attempt["source"], examples)
            if policy == "A" and chosen_a is None and selected:
                chosen_a = sources["public_selected"]
            rec = {"generated_edits": count, "selected_perfect_public_edit": selected, "arms": {}}
            for name, src in sources.items():
                rec["arms"][name] = {"program_sha256": digest(src.encode()), "public_passed": public_count(src, examples),
                                     "qualification_passed": public_count(src, fixtures["qualification"][case]),
                                     "fresh": grade(src, fixtures["cases"][policy])}
            record.append(rec)
        results[policy] = record
    controls = {}
    for name, ctrl in dict(fixtures["controls"],
                           mechanism_control=dict(fixtures["controls"]["net_fee"], source=fixtures["mechanism_control"])).items():
        sources, count, _ = arms(ctrl["source"], ctrl["public"])
        controls[name] = {"raw_sha256": digest(ctrl["source"].encode()), "eligible_edits": count,
                          "public_passed": public_count(ctrl["source"], ctrl["public"]),
                          "unchanged_bytes": sources["public_selected"] == ctrl["source"],
                          "selected_fresh": grade(sources["public_selected"], ctrl["hidden"]),
                          "first_edit_fresh": grade(sources["first_edit"], ctrl["hidden"])}
    return {"protocol_sha256": digest(protocol_bytes),
            "original_frozen_algorithm_sha256": "fa4432ee1bccf68c3aa25257aa081556905472de512ea0ca379e331fb9572fe1",
            "cases_per_policy": 100, "new_model_calls": 0, "limit_per_raw_program": 8, "shipping_policies": results,
            "A_selected_applied_to_B": grade(chosen_a, fixtures["cases"]["B"]) if chosen_a else None, "controls": controls}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sdk", type=Path, required=True, help="pinned CPython WASI directory containing python.wasm and lib/")
    p.add_argument("--out", type=Path, help="optionally write a second copy of the computed JSON")
    args = p.parse_args()
    result = replay(args.sdk)
    text = json.dumps(result, indent=1, sort_keys=True) + "\n"
    if args.out:
        args.out.write_text(text)
    if result != json.loads((HERE / "results.json").read_text()):
        raise SystemExit("Current results differ from the frozen scores")
    for policy, attempts in result["shipping_policies"].items():
        for i, a in enumerate(attempts, 1):
            print(policy, i, {k: v["fresh"]["passed"] for k, v in a["arms"].items()})
    print("Verified every recorded score, raw output hash and control.")


if __name__ == "__main__":
    main()
