"""Restart-native cycle state.

A cycle's state lives in one JSON file inside its run directory.
Writes are atomic (tmp file + fsync + os.replace), so a VM reboot
mid-write cannot corrupt it. On re-entry the loop loads the state,
skips stages already recorded as complete for a subject, and resumes
— it never restarts a finished stage (arch. section 6: idempotent,
resumable stages; skip-if-done is the standard contract).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from .lineage import now_ts

STAGES = ["diagnose", "indict", "edit_train", "verify", "compose", "grow"]


@dataclass
class CycleState:
    cycle_id: str
    mode: str
    status: str = "running"                # running | complete | blocked
    created_at: str = field(default_factory=now_ts)
    updated_at: str = field(default_factory=now_ts)
    host_profile: Dict[str, Any] = field(default_factory=dict)
    governor: Dict[str, Any] = field(default_factory=dict)
    # subject_id -> {stage_name: serialized stage output}
    completed: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    blocked: Dict[str, str] = field(default_factory=dict)  # subject_id -> reason

    def stages_done(self, subject_id: str) -> List[str]:
        return [s for s in STAGES if s in self.completed.get(subject_id, {})]

    def is_stage_done(self, subject_id: str, stage: str) -> bool:
        return stage in self.completed.get(subject_id, {})

    def record(self, subject_id: str, stage: str, output: Dict[str, Any]) -> None:
        self.completed.setdefault(subject_id, {})[stage] = output
        self.updated_at = now_ts()

    def to_dict(self) -> Dict[str, Any]:
        return {"cycle_id": self.cycle_id, "mode": self.mode, "status": self.status,
                "created_at": self.created_at, "updated_at": self.updated_at,
                "host_profile": self.host_profile, "governor": self.governor,
                "completed": self.completed, "blocked": self.blocked}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CycleState":
        return cls(cycle_id=d["cycle_id"], mode=d["mode"], status=d.get("status", "running"),
                   created_at=d.get("created_at", ""), updated_at=d.get("updated_at", ""),
                   host_profile=d.get("host_profile", {}), governor=d.get("governor", {}),
                   completed=d.get("completed", {}), blocked=d.get("blocked", {}))


class StateStore:
    def __init__(self, run_dir: Path):
        self.run_dir = Path(run_dir)
        self.path = self.run_dir / "state.json"

    def save(self, state: CycleState) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(state.to_dict(), fh, indent=1, ensure_ascii=False)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.path)

    def load(self) -> CycleState | None:
        if not self.path.exists():
            return None
        with open(self.path, encoding="utf-8") as fh:
            return CycleState.from_dict(json.load(fh))
