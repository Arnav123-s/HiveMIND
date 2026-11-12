"""Run one Phase B real cycle.

Usage (from ~/workspace/edit-lab):
    python3 -m factory.run_real [--cycle-id ID] [--resume ID]
                                [--subjects ID [ID ...]]

REAL mode executes Tier-0 TRAIN_DATA_WIDEN plans through the measured
win-gate (executors.py). Subjects without an executor fail closed at
verify; NO_OP subjects hold. Default: all loaded subjects.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from factory.contracts import Mode  # noqa: E402
from factory.loop import FactoryLoop  # noqa: E402
from factory.subjects import load_subjects  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Factory loop — Phase B real cycle")
    ap.add_argument("--cycle-id", default=None)
    ap.add_argument("--resume", default=None, help="cycle id to resume")
    ap.add_argument("--subjects", nargs="*", default=None,
                    help="subject ids to run (default: all)")
    args = ap.parse_args()

    lab_root = Path(__file__).parent.parent
    cycle_id = args.resume or args.cycle_id or time.strftime("real-%Y%m%d-%H%M%S")
    loop = FactoryLoop(lab_root=lab_root, cycle_id=cycle_id, mode=Mode.REAL)
    subjects = load_subjects(lab_root)
    if args.subjects:
        subjects = [s for s in subjects if s.subject_id in set(args.subjects)]
    report = loop.run_cycle(subjects)
    print(json.dumps({"cycle_id": cycle_id,
                      "run_dir": str(loop.run_dir),
                      "subjects": {k: (v.get("verify") or {}).get("verdict")
                                   for k, v in report["subjects"].items()},
                      "blocked": report["blocked"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
