"""Typed stage contracts for the factory self-driving loop.

Stdlib only. Every stage is a callable with a typed input and a typed
output (see stages.py). The loop (loop.py) refuses to advance a cycle
when a stage output fails its gate — fail-closed by construction:

  * a Diagnosis with no evidence cannot be indicted;
  * an InterventionPlan that proposes a weight edit without a prior
    map/indictment cannot pass verification (IDEA.md section 6:
    no change before the map exists);
  * a plan with no win-gate or no regression gate cannot pass
    verification;
  * in Phase A the loop runs in DRY_RUN mode only: plans are produced,
    nothing is executed (executed is always False), and any plan that
    would require a heavy leg is recorded, never run.

Serialization: every contract is a dataclass with to_dict()/from_dict()
so cycle state can be checkpointed to disk and resumed after a reboot
(FACTORY-ARCHITECTURE.md section 6, restart-native).
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class Mode(str, Enum):
    DRY_RUN = "dry_run"   # Phase A: shadow only, no edits, no training
    REAL = "real"         # Phase B: executes where an executor exists (executors.py)


class Action(str, Enum):
    NO_OP = "no_op"                       # healthy incumbent: hold
    TRAIN_DATA_WIDEN = "train_data_widen"  # broader surfaces / good views, then retrain Tier-0
    DREAM_TRAIN = "dream_train"            # Phase C: self-generated, execution-verified
                                           # practice at the capability edge (thermostat),
                                           # then retrain Tier-0
    COMPOSE = "compose"                    # recompose existing specialists differently
    GROW = "grow"                          # spawn a new smallest specialist for an ownerless gap
    WEIGHT_EDIT = "weight_edit"            # surgery: only legal with a map-backed indictment


class ClusterKind(str, Enum):
    DEFECT = "defect"           # shared mechanism, indictable
    CAPABILITY = "capability"   # surface/coverage gap: train/compose/grow, not surgery
    NONE = "none"               # no material failure observed
    UNKNOWN = "unknown"


@dataclass
class Subject:
    """One thing the loop can work on: a specialist or an adapter."""
    subject_id: str
    kind: str                                # tier0_specialist | tier0_composition | tier1_adapter
    niche: str
    artifact_path: Optional[str] = None
    params: Optional[int] = None
    footprint_bytes: Optional[int] = None
    heldout_score: Optional[float] = None    # same-distribution held-out (adoption evidence)
    heldout_bar: Optional[float] = None
    fresh_score: Optional[float] = None      # fresh-surface / pristine evidence
    fresh_bar: Optional[float] = None
    fresh_label: str = ""                    # what the fresh evidence is (battery / pristine test)
    incumbent_score: Optional[float] = None  # base/incumbent the subject is judged against
    adopted: bool = False
    evidence_paths: List[str] = field(default_factory=list)
    failing_cases: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Subject":
        return cls(**d)


@dataclass
class FailureCluster:
    label: str
    kind: ClusterKind
    severity: str                            # info | low | medium | high
    evidence: str
    examples: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = dataclasses.asdict(self)
        d["kind"] = self.kind.value
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FailureCluster":
        d = dict(d)
        d["kind"] = ClusterKind(d["kind"])
        return cls(**d)


@dataclass
class Diagnosis:
    subject_id: str
    clusters: List[FailureCluster]
    summary: str
    has_evidence: bool                       # False -> fail-closed: cycle must not advance

    def to_dict(self) -> Dict[str, Any]:
        return {"subject_id": self.subject_id,
                "clusters": [c.to_dict() for c in self.clusters],
                "summary": self.summary, "has_evidence": self.has_evidence}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Diagnosis":
        return cls(subject_id=d["subject_id"],
                   clusters=[FailureCluster.from_dict(c) for c in d["clusters"]],
                   summary=d["summary"], has_evidence=d["has_evidence"])


@dataclass
class Indictment:
    subject_id: str
    indictable: bool                         # is there a specific, named target?
    target_units: List[str]                  # e.g. "training_surface_coverage:review"
    method: str                              # how the target was identified
    rationale: str
    weight_edit_justified: bool = False      # True only with a map (flip/knockout/locator)
    map_evidence: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Indictment":
        return cls(**d)


@dataclass
class WinGate:
    """The verification contract for a plan. All fields are required for
    a plan to pass the verify stage — a missing gate is a blocked plan."""
    metric: str
    threshold: float
    regression_gate: str                     # human-readable per-case / no-regression rule
    confirm_protocol: str                    # dev ranks -> confirm -> one pristine run

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "WinGate":
        return cls(**d)


@dataclass
class InterventionPlan:
    """Output of the edit/train stage. In DRY_RUN this is a plan only:
    executed is always False and shadow_only is always True."""
    subject_id: str
    action: Action
    steps: List[str]
    win_gate: Optional[WinGate]
    estimated_cost: str                      # qualitative budget character (arch. section 8)
    requires_heavy_leg: bool = False
    requires_map_before_edit: bool = False
    shadow_only: bool = True
    executed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = dataclasses.asdict(self)
        d["action"] = self.action.value
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "InterventionPlan":
        d = dict(d)
        d["action"] = Action(d["action"])
        if d.get("win_gate"):
            d["win_gate"] = WinGate.from_dict(d["win_gate"])
        return cls(**d)


@dataclass
class Verification:
    subject_id: str
    verdict: str                             # SHADOW_PASS | HOLD | BLOCKED (shadow);
                                             # WIN | REVERT (measured, Phase B only)
    reasons: List[str]
    measured: bool = False                   # True only when every number in the
                                             # verdict was actually measured

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Verification":
        return cls(**d)


@dataclass
class CompositionPlan:
    subject_id: str
    members: List[str]
    strategy: str
    fallback: str                            # best single measured candidate (arch. section 5)
    audit_plan: str                          # serve-time audit + retirement rule
    shadow_only: bool = True
    executed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CompositionPlan":
        return cls(**d)


@dataclass
class GrowthPlan:
    subject_id: str
    proposals: List[Dict[str, Any]]          # {job, niche, tier, why, gate}
    shadow_only: bool = True
    executed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "GrowthPlan":
        return cls(**d)


@dataclass
class StageResult:
    stage: str
    subject_id: str
    ok: bool                                 # False -> fail-closed stop for this subject
    output: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)
