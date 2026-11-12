#!/usr/bin/env python3
"""The hive's front door — one command, plain text in, composed
answer + provenance out.

    cd ~/workspace/edit-lab
    python3 hive.py secret 'api_key = "sk-live-9f27ac41bd"'
    python3 hive.py error  'KeyError: user_id (traceback text...)'
    python3 hive.py commit 'repair the broken cart total'
    python3 hive.py contract --file snippet.py
    python3 hive.py gap    'the model fails on inputs it never saw'
    python3 hive.py bug    --file buggy.py
    python3 hive.py jobs            # what serves, and its evidence

Everything goes through factory.serve.ServingHive — the audited
registry is the only book, and the load fails closed if any
registered artifact's bytes differ from its adoption record.
See USAGE.md for worked examples.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

LAB = Path(__file__).parent
sys.path.insert(0, str(LAB))

from factory.serve import ServingHive, ServingRefused  # noqa: E402

JOBS = {
    "secret": "secret-line-model",
    "error": "error-class-model",
    "commit": "commit-type-model",
    "contract": "contract-judgment-model",
    "gap": "gap-move-model",
}


def _text(args) -> str:
    if args.file:
        return Path(args.file).read_text()
    return args.text or ""


def _show(out: dict) -> int:
    prov = out.get("provenance") or {}
    if not out.get("ok"):
        print(f"NO ANSWER: {out.get('gap') or out.get('evidence')}")
        if out.get("growth_move"):
            print(f"growth move: {out['growth_move']}")
        return 1
    print(f"ANSWER: {out.get('output')}")
    if "artifact" in prov:
        print(f"served by: {prov['artifact']} "
              f"({prov['substrate']}, held-out {prov['heldout_acc']})")
        print(f"artifact:  {prov['path']} sha256:{prov['sha256']}…")
    if out.get("specialist") == "bug-pattern-composed":
        print(f"served by: {prov['composition']} "
              f"({prov['members']} members) + {prov['serving_layer']} "
              f"serving layer")
        if prov["verification_fired"]:
            print(f"waking-dream: VERIFIED {prov['verified_cls']} by "
                  f"execution (composer alone said "
                  f"{prov['composer_verdict']})")
        else:
            print(f"waking-dream: no candidate verified — raw "
                  f"composer verdict stands (flagged unverified)")
        print(f"sealed evidence: served path {prov['sealed_layer_acc']} "
              f"vs raw composition {prov['sealed_raw_composition_acc']} "
              f"(bar {prov['bar']})")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="hive", description="Ask the hive (see USAGE.md)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in list(JOBS) + ["bug"]:
        p = sub.add_parser(name)
        p.add_argument("text", nargs="?", default="")
        p.add_argument("--file", help="read the text/code from a file")
        if name in JOBS:
            p.add_argument("--substrate",
                           choices=["fp", "ternary"], default=None,
                           help="name a substrate instead of the "
                                "serving default")
    sub.add_parser("jobs", help="list what serves, with evidence")
    args = ap.parse_args()

    try:
        hive = ServingHive.load()
    except ServingRefused as exc:
        print(f"SERVING REFUSED: {exc}")
        return 2

    if args.cmd == "jobs":
        for job, s in hive.registry["specialists"].items():
            sv = s["serving"]
            print(f"{job}: {sv['name']} ({sv['substrate']}, "
                  f"held-out {sv['heldout_acc']}, "
                  f"battery {sv.get('battery_acc')})")
            for fb in s.get("fallbacks", []):
                print(f"    fallback: {fb['name']} ({fb['substrate']})")
            for sh in s.get("shadow", []):
                print(f"    shadow (never served): {sh['name']}")
            for sb in s.get("substrates", []):
                print(f"    substrate alternate: {sb['name']} "
                      f"({sb['substrate']}, held-out "
                      f"{sb['heldout_acc']})")
        comp = hive.registry["compositions"]["bug-pattern-composed"]
        layer = comp.get("serving_layer") or {}
        print(f"bug-pattern: {len(comp['members'])} members + "
              f"{layer.get('name')} serving layer "
              f"(sealed {layer.get('sealed_acc')}; raw composition "
              f"sealed {comp['evidence']['fresh_sealed_baseline']['acc']})")
        return 0

    if args.cmd == "bug":
        out = hive.serve({"kind": "bug-pattern", "code": _text(args)})
    else:
        task = {"kind": "classify", "job": JOBS[args.cmd],
                "text": _text(args)}
        if args.substrate:
            task["substrate"] = args.substrate
        out = hive.serve(task)
    return _show(out)


if __name__ == "__main__":
    raise SystemExit(main())
