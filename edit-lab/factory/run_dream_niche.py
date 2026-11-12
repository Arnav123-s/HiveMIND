"""Run one niche dream cycle (final-product item 2).

Usage (from ~/workspace/edit-lab):
    python3 -m factory.run_dream_niche <subject-id> [--cycle-id ID]

REAL mode, DREAM_TRAIN plan, for generator-backed drift subjects
(contract-judgment-model, commit-type-model). The subject generates
checker-verified practice at its capability edge (thermostat),
retrains, and is judged by the widen win-gate plus a paired
incumbent comparison on fresh confirm families, spent once.
Subjects without a generator fail closed in the executor.
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
    ap = argparse.ArgumentParser(description="Factory loop — niche dream cycle")
    ap.add_argument("subject")
    ap.add_argument("--cycle-id", default=None)
    args = ap.parse_args()

    lab_root = Path(__file__).parent.parent
    cycle_id = args.cycle_id or time.strftime("dream-niche-%Y%m%d-%H%M%S")
    loop = FactoryLoop(lab_root=lab_root, cycle_id=cycle_id, mode=Mode.REAL)
    subjects = [s for s in load_subjects(lab_root)
                if s.subject_id == args.subject]
    if not subjects:
        print(f"unknown subject {args.subject}")
        return 1
    report = loop.run_cycle(subjects)
    print(json.dumps({"cycle_id": cycle_id,
                      "run_dir": str(loop.run_dir),
                      "subjects": {k: (v.get("verify") or {}).get("verdict")
                                   for k, v in report["subjects"].items()},
                      "blocked": report["blocked"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
