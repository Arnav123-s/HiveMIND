"""Thermal sensor adapter for hosts whose temperature lives in a
watcher log rather than sysfs (Phase C) — e.g. ashp, where the
lab's tempwatch task appends readings to a log file while the VM's
sysfs exposes nothing.

    read_tempwatch(path) -> (celsius, source) | (None, None)

Accepts JSON-lines logs (objects carrying any of temp_c /
temperature / gpu_temp / celsius) or plain-text lines containing a
plausible temperature. Only the LATEST reading counts, and only if
the log was written within FRESH_SECONDS — a stale watcher must not
masquerade as a live sensor: the governor's heat gate stays inert
rather than trusting old data (fail-closed, same as no sensor).

Wired into host._thermal() via the FACTORY_TEMPWATCH_LOG
environment variable; unset or unreadable -> no reading, exactly
the pre-Phase-C behavior.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Optional, Tuple

FRESH_SECONDS = 600
_TEMP_KEYS = ("temp_c", "temperature", "gpu_temp", "celsius", "temp")
_NUM = re.compile(r"(-?\d+(?:\.\d+)?)\s*(?:°\s*)?C\b")


def read_tempwatch(path) -> Tuple[Optional[float], Optional[str]]:
    p = Path(path)
    try:
        if not p.exists():
            return None, None
        if time.time() - p.stat().st_mtime > FRESH_SECONDS:
            return None, None     # stale watcher: not a live sensor
        lines = p.read_text(errors="replace").splitlines()[-50:]
    except OSError:
        return None, None
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        if line.startswith("{"):
            try:
                obj = json.loads(line)
            except Exception:
                obj = None
            if isinstance(obj, dict):
                for k in _TEMP_KEYS:
                    v = obj.get(k)
                    if isinstance(v, (int, float)) and 0 < v < 130:
                        return float(v), f"tempwatch:{p.name}"
                continue
        m = _NUM.search(line)
        if m:
            v = float(m.group(1))
            if 0 < v < 130:
                return v, f"tempwatch:{p.name}"
    return None, None


def tempwatch_from_env() -> Tuple[Optional[float], Optional[str]]:
    path = os.environ.get("FACTORY_TEMPWATCH_LOG")
    if not path:
        return None, None
    return read_tempwatch(path)
