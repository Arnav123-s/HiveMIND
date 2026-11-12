"""Scheduling layer (Phase C): the cross-process heavy-leg lock and
the persistent cycle queue (FACTORY-ARCHITECTURE.md section 7).

Two mechanisms, both file-based and restart-native:

  * HeavyLegLock — the single-heavy-leg lock as a cross-PROCESS
    object: an O_EXCL lock file carrying owner + timestamp. A lock
    older than the staleness horizon (default: the host profile's
    interruption horizon, 2 h here) may be broken — a crashed holder
    must not brick the factory — and breaking one is recorded.
    Light legs (everything the factory runs today is seconds-class
    Tier-0) do not take the lock; it exists so a future heavy leg
    (Tier-1/Tier-2) has the discipline built before it needs it.
  * CycleQueue — a persistent FIFO of cycle requests
    ({cycle_id, mode, subjects, requested_by, note}) in one JSON
    file, written atomically. A scheduler process (or a cron-driven
    run) pops the next request only when the governor admits it;
    the queue survives reboots because it is a file, not a process.

Duty-cycle helper: `polite_pause` sleeps in short slices and
re-checks a stop predicate — the shape a long leg uses to yield
between bursts (arch. section 3: duty-cycling, automatic backoff).
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

FACTORY_DIR = Path(__file__).parent
DEFAULT_STALE_SECONDS = 2 * 3600   # the observed interruption horizon


class HeavyLegLock:
    def __init__(self, path: Optional[Path] = None,
                 stale_seconds: int = DEFAULT_STALE_SECONDS):
        self.path = Path(path) if path else FACTORY_DIR / "heavy.lock"
        self.stale_seconds = stale_seconds
        self.held = False

    def _read(self) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(self.path.read_text())
        except Exception:
            return None

    def acquire(self, owner: str) -> Dict[str, Any]:
        """Returns {acquired, broke_stale, holder}. Never blocks:
        contention is a decision for the caller (backoff), not a
        sleep inside the lock."""
        if self.path.exists():
            info = self._read()
            age = time.time() - self.path.stat().st_mtime
            if info is not None and age < self.stale_seconds:
                return {"acquired": False, "broke_stale": False,
                        "holder": info}
            # stale or unreadable: break it, and say so
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass
            broke = True
        else:
            broke = False
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return {"acquired": False, "broke_stale": broke,
                    "holder": self._read()}
        with os.fdopen(fd, "w") as fh:
            json.dump({"owner": owner, "pid": os.getpid(),
                       "acquired_at": time.time()}, fh)
        self.held = True
        return {"acquired": True, "broke_stale": broke, "holder": None}

    def release(self) -> bool:
        if not self.held:
            return False
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass
        self.held = False
        return True

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.release()
        return False


class CycleQueue:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else FACTORY_DIR / "queue.json"

    def _load(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            return json.loads(self.path.read_text())
        except Exception:
            return []

    def _save(self, items: List[Dict[str, Any]]) -> None:
        tmp = self.path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(items, fh, indent=1)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.path)

    def enqueue(self, request: Dict[str, Any]) -> int:
        items = self._load()
        items.append({**request, "queued_at": time.time()})
        self._save(items)
        return len(items)

    def peek(self) -> Optional[Dict[str, Any]]:
        items = self._load()
        return items[0] if items else None

    def pop(self) -> Optional[Dict[str, Any]]:
        items = self._load()
        if not items:
            return None
        head, rest = items[0], items[1:]
        self._save(rest)
        return head

    def __len__(self) -> int:
        return len(self._load())


def polite_pause(seconds: float, stop_predicate=None,
                 slice_seconds: float = 0.25) -> bool:
    """Duty-cycle pause: sleep in slices so a backoff signal can
    interrupt promptly. Returns True if the full pause elapsed,
    False if the stop predicate fired first."""
    end = time.time() + seconds
    while time.time() < end:
        if stop_predicate is not None and stop_predicate():
            return False
        time.sleep(min(slice_seconds, max(0.0, end - time.time())))
    return True
