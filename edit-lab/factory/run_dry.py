"""Run one Phase A dry-run cycle.

Usage (from ~/workspace/edit-lab):
    python3 -m factory.run_dry [--cycle-id ID] [--resume ID]

Default cycle id: dry-YYYYmmdd-HHMMSS. Re-running with --resume ID
loads that cycle's state and skips its finished stages.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Allow running as a plain script from inside factory/ as well.
sys.path.insert(0, str(Path(__file__).parent.parent))

from factory.contracts import Mode  # noqa: E402
from factory.loop import FactoryLoop  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Factory loop — Phase A dry-run")
    ap.add_argument("--cycle-id", default=None)
    ap.add_argument("--resume", default=None, help="cycle id to resume")
    args = ap.parse_args()

    lab_root = Path(__file__).parent.parent
    cycle_id = args.resume or args.cycle_id or time.strftime("dry-%Y%m%d-%H%M%S")
    loop = FactoryLoop(lab_root=lab_root, cycle_id=cycle_id, mode=Mode.DRY_RUN)
    report = loop.run_cycle()
    print(json.dumps({"cycle_id": cycle_id,
                      "run_dir": str(loop.run_dir),
                      "subjects": {k: (v.get("verify") or {}).get("verdict")
                                   for k, v in report["subjects"].items()},
                      "blocked": report["blocked"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
