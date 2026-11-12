"""Append-only lineage logging in the lab's existing format.

The lab's results/lineage.jsonl entries are single-line JSON objects
with at least {"ts": ISO-naive, "kind": str, ...payload}. The factory
keeps its own lineage inside factory/ (per-run and factory-level) in
exactly that shape, so any tool that reads the lab lineage can read
the factory's. The lineage log is the state (arch. section 6): it is
written before and after every stage.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict


def now_ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


class LineageLog:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, kind: str, **payload: Any) -> Dict[str, Any]:
        entry = {"ts": now_ts(), "kind": kind}
        entry.update(payload)
        line = json.dumps(entry, ensure_ascii=False)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        return entry

    def read_all(self):
        if not self.path.exists():
            return []
        out = []
        with open(self.path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out
