"""Phase C growth: intake scan + gated split-birth attempts.

Usage (from ~/workspace/edit-lab):
    python3 -m factory.run_growth [--cycle-id ID]
                                  [--attempt CLS:SLICE ...]

Default attempts, in intake-ranked order: the candidates whose
parent is measurably imperfect on a real slice with enough data —
wrong-operator/expression first, then off-by-one/index. Every
attempt is gated; a rejected birth writes nothing but its record.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from factory import growth  # noqa: E402
from factory.lineage import LineageLog  # noqa: E402

FACTORY_DIR = Path(__file__).parent
DEFAULT_ATTEMPTS = [("wrong-operator", "expression"),
                    ("off-by-one", "index")]


def main() -> int:
    ap = argparse.ArgumentParser(description="Factory Phase C — growth")
    ap.add_argument("--cycle-id", default=None)
    ap.add_argument("--attempt", nargs="*", default=None,
                    help="CLS:SLICE pairs (default: intake-ranked two)")
    args = ap.parse_args()
    cycle_id = args.cycle_id or time.strftime("phaseC-growth-%Y%m%d-%H%M%S")
    run_dir = FACTORY_DIR / "runs" / cycle_id
    run_dir.mkdir(parents=True, exist_ok=True)
    lineage = LineageLog(run_dir / "lineage.jsonl")
    factory_lineage = LineageLog(FACTORY_DIR / "lineage.jsonl")
    lab_root = FACTORY_DIR.parent

    scan = growth.scan_intake(lab_root)
    with open(run_dir / "intake_scan.json", "w", encoding="utf-8") as fh:
        json.dump(scan, fh, indent=1, ensure_ascii=False)
    lineage.append("intake_scan", cycle_id=cycle_id,
                   candidates=[c for c in scan["slice_candidates"]
                               if c["birth_candidate"]])

    attempts = []
    pairs = DEFAULT_ATTEMPTS
    if args.attempt:
        pairs = [tuple(p.split(":", 1)) for p in args.attempt]
    for cls, slice_name in pairs:
        out = growth.attempt_birth(cls, slice_name, run_dir, lineage,
                                   cycle_id)
        attempts.append(out)
        print(f"[birth] {out['child']}: "
              f"{'BORN' if out['born'] else 'rejected'} — "
              f"{out.get('rejection') or ('child ' + str(out.get('child_slice_heldout_acc')) + ' vs parent ' + str(out.get('parent_slice_heldout_acc')))}")
    with open(run_dir / "growth_results.json", "w",
              encoding="utf-8") as fh:
        json.dump({"cycle_id": cycle_id, "attempts": attempts}, fh,
                  indent=1, ensure_ascii=False)
    factory_lineage.append(
        "phaseC_growth", cycle_id=cycle_id,
        run_dir=f"factory/runs/{cycle_id}",
        births=[a["child"] for a in attempts if a["born"]],
        rejected=[a["child"] for a in attempts if not a["born"]])
    print(json.dumps({"cycle_id": cycle_id, "run_dir": str(run_dir),
                      "born": [a["child"] for a in attempts if a["born"]]},
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
