"""Unified artifact loading (assembly 2026-11-10).

One dispatch used by BOTH the serving path (factory/serve.py) and
the audit's score re-measurement (factory/audit.py), so what
serves and what the audit measures can never drift apart:

  * a record with a "payload" pointer is a ternary BitNet
    artifact — loaded through factory/tern_runtime.py;
  * any other record is a TinyNet record — loaded through
    swarm.factory.TinyNet.from_record, as before.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Union

LAB_ROOT = Path(__file__).parent.parent


def load_record(path: Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text())


def load_artifact(record: Dict[str, Any], lab_root: Path = LAB_ROOT):
    """record: a model record dict (from a registry-listed file).
    Returns a TinyNet or a tern_runtime.TernSpecialist — both
    expose run({"text": ...}) -> {"output": ...}."""
    if record.get("payload"):
        from .tern_runtime import load_tern
        return load_tern(record, Path(lab_root))
    import sys
    if str(LAB_ROOT / "coding") not in sys.path:
        sys.path.insert(0, str(LAB_ROOT / "coding"))
    from swarm import factory as F
    return F.TinyNet.from_record(record)
