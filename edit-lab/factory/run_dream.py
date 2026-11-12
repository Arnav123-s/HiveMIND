"""Run one Phase C dream cycle (bug-pattern-composed).

Usage (from ~/workspace/edit-lab):
    python3 -m factory.run_dream [--cycle-id ID] [--resume ID]

REAL mode, DREAM_TRAIN plan: the subject generates its own
execution-verified practice at its capability edge (thermostat),
retrains its weak classes' binaries, and is judged by the same
win-gate Phase B used — composed threshold + per-class
no-regression, confirm set spent once.
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
    ap = argparse.ArgumentParser(description="Factory loop — Phase C dream cycle")
    ap.add_argument("--cycle-id", default=None)
    ap.add_argument("--resume", default=None, help="cycle id to resume")
    args = ap.parse_args()

    lab_root = Path(__file__).parent.parent
    cycle_id = args.resume or args.cycle_id or \
        time.strftime("dream-%Y%m%d-%H%M%S")
    loop = FactoryLoop(lab_root=lab_root, cycle_id=cycle_id, mode=Mode.REAL)
    subjects = [s for s in load_subjects(lab_root)
                if s.subject_id == "bug-pattern-composed"]
    report = loop.run_cycle(subjects)
    print(json.dumps({"cycle_id": cycle_id,
                      "run_dir": str(loop.run_dir),
                      "subjects": {k: (v.get("verify") or {}).get("verdict")
                                   for k, v in report["subjects"].items()},
                      "blocked": report["blocked"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
