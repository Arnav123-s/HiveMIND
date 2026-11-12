"""The factory loop orchestrator (Phase A: dry-run; Phase B: real).

Wires the section-8 stages behind the gates:

    diagnose -> indict -> edit_train -> verify -> compose -> grow

Properties enforced here, not by convention:
  * Mode: DRY_RUN produces shadow plans only (Phase A behaviour,
    unchanged). REAL (Phase B) executes a plan only where a real
    executor exists (executors.py: Tier-0 TRAIN_DATA_WIDEN) and only
    through the measured win-gate; a plan with no executor fails
    closed at verify (BLOCKED) — the loop still cannot pretend.
  * Checkpointing: state is saved after every stage of every subject;
    lineage is written before and after every stage. A reboot costs
    at most the stage in flight.
  * Resume: re-running a cycle_id loads its state and skips finished
    stages (skip-if-done).
  * Governor: consulted before the edit_train stage; its decision is
    recorded in state + lineage. In REAL mode a governor backoff
    holds execution (the measured verify then BLOCKs, honestly).
  * Fail-closed: a stage whose gate fails marks the subject blocked
    and the loop moves on; it never advances a blocked subject.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import stages as stage_fns
from .contracts import (CompositionPlan, Diagnosis, GrowthPlan, Indictment,
                        InterventionPlan, Mode, StageResult, Subject,
                        Verification)
from .host import Governor, GovernorConfig, probe_host
from .lineage import LineageLog, now_ts
from .state import STAGES, CycleState, StateStore
from .subjects import load_subjects

FACTORY_DIR = Path(__file__).parent


class FactoryLoop:
    def __init__(self, lab_root: Path, cycle_id: str, mode: Mode = Mode.DRY_RUN,
                 governor_config: Optional[GovernorConfig] = None):
        self.lab_root = Path(lab_root)
        self.cycle_id = cycle_id
        self.mode = mode
        self.run_dir = FACTORY_DIR / "runs" / cycle_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.store = StateStore(self.run_dir)
        self.lineage = LineageLog(self.run_dir / "lineage.jsonl")
        self.factory_lineage = LineageLog(FACTORY_DIR / "lineage.jsonl")
        self.governor = Governor(governor_config)
        self.state: CycleState = self.store.load() or CycleState(
            cycle_id=cycle_id, mode=mode.value)

    # ------------------------------------------------------------ internals
    def _stage(self, subject: Subject, stage: str, fn, *args) -> StageResult:
        if self.state.is_stage_done(subject.subject_id, stage):
            return StageResult(stage, subject.subject_id, ok=True,
                               output=self.state.completed[subject.subject_id][stage])
        self.lineage.append("stage_start", cycle_id=self.cycle_id, stage=stage,
                            subject=subject.subject_id, mode=self.mode.value)
        try:
            out = fn(*args)
        except Exception as exc:  # fail-closed: an exception blocks, never advances
            self.lineage.append("stage_blocked", cycle_id=self.cycle_id, stage=stage,
                                subject=subject.subject_id, error=repr(exc))
            return StageResult(stage, subject.subject_id, ok=False, errors=[repr(exc)])
        return self._record_stage(subject, stage, out)

    def _record_stage(self, subject: Subject, stage: str, out) -> StageResult:
        """Gate + checkpoint bookkeeping for a stage output, whether it
        came from a pure stage callable or (Phase B) an executor."""
        if self.state.is_stage_done(subject.subject_id, stage):
            return StageResult(stage, subject.subject_id, ok=True,
                               output=self.state.completed[subject.subject_id][stage])
        out_dict = out.to_dict() if hasattr(out, "to_dict") else dict(out)
        # Gate checks that live in the loop, not the stage:
        errors: List[str] = []
        if stage == "diagnose" and not out.has_evidence:
            errors.append("diagnosis has no evidence (fail-closed)")
        if stage == "verify" and out.verdict == "BLOCKED":
            errors.extend(out.reasons)
        result = StageResult(stage, subject.subject_id, ok=not errors,
                             output=out_dict, errors=errors)
        if result.ok:
            self.state.record(subject.subject_id, stage, out_dict)
            self.store.save(self.state)
            self.lineage.append("stage_done", cycle_id=self.cycle_id, stage=stage,
                                subject=subject.subject_id)
        else:
            self.state.blocked[subject.subject_id] = f"{stage}: {'; '.join(errors)}"
            self.store.save(self.state)
            self.lineage.append("stage_blocked", cycle_id=self.cycle_id, stage=stage,
                                subject=subject.subject_id, errors=errors)
        return result

    # ------------------------------------------------------------ main cycle
    def run_cycle(self, subjects: Optional[List[Subject]] = None) -> Dict[str, Any]:
        subjects = subjects if subjects is not None else load_subjects(self.lab_root)
        profile = probe_host(str(self.run_dir))
        decision = self.governor.decide(profile, heavy_opt_in=False)
        self.state.host_profile = profile.to_dict()
        self.state.governor = decision.to_dict()
        self.store.save(self.state)
        with open(self.run_dir / "host_profile.json", "w", encoding="utf-8") as fh:
            json.dump(profile.to_dict(), fh, indent=1)
        self.lineage.append("cycle_start", cycle_id=self.cycle_id, mode=self.mode.value,
                            subjects=[s.subject_id for s in subjects],
                            host={"cpu": profile.cpu_count, "gpu_present": profile.gpu_present,
                                  "chunk_ceiling_minutes": profile.chunk_ceiling_minutes},
                            governor=decision.to_dict())
        if decision.backoff:
            self.lineage.append("governor_backoff", cycle_id=self.cycle_id,
                                cause=decision.cause, notes=decision.notes)

        report: Dict[str, Any] = {"cycle_id": self.cycle_id, "mode": self.mode.value,
                                  "ts": now_ts(), "subjects": {}}
        for subject in subjects:
            entry: Dict[str, Any] = {}
            r = self._stage(subject, "diagnose", stage_fns.diagnose, subject)
            entry["diagnose"] = r.output
            if not r.ok:
                report["subjects"][subject.subject_id] = entry
                continue
            diagnosis = Diagnosis.from_dict(r.output)
            r = self._stage(subject, "indict", stage_fns.indict, subject, diagnosis)
            entry["indict"] = r.output
            if not r.ok:
                report["subjects"][subject.subject_id] = entry
                continue
            indictment = Indictment.from_dict(r.output)
            # Governor gate before the intervention stage (Phase B: this
            # is where heavy legs are admitted or held).
            self.lineage.append("governor_check", cycle_id=self.cycle_id,
                                subject=subject.subject_id,
                                allow_heavy=decision.allow_heavy,
                                backoff=decision.backoff, cause=decision.cause)
            r = self._stage(subject, "edit_train", stage_fns.edit_train,
                            subject, diagnosis, indictment)
            entry["edit_train"] = r.output
            if not r.ok:
                report["subjects"][subject.subject_id] = entry
                continue
            plan = InterventionPlan.from_dict(r.output)
            # Phase B: in REAL mode, a TRAIN_DATA_WIDEN plan on a Tier-0
            # specialist with a built executor is EXECUTED here, between
            # planning and verification; verify then judges measured
            # numbers. Everything else keeps the Phase A shadow verify
            # (DRY_RUN) or fails closed at verify (REAL, no executor).
            execution = None
            if (self.mode == Mode.REAL and plan.action.value == "train_data_widen"
                    and subject.kind == "tier0_specialist"):
                from . import executors
                execution = executors.run_widen_subject(
                    subject, plan, self.run_dir, self.lineage, self.cycle_id,
                    governor_backoff=decision.backoff,
                    governor_cause=decision.cause)
                entry["execution"] = execution
            elif (self.mode == Mode.REAL and plan.action.value == "dream_train"
                    and subject.kind == "tier0_composition"):
                from . import dream
                execution = dream.run_dream_subject(
                    subject, plan, self.run_dir, self.lineage, self.cycle_id,
                    governor_backoff=decision.backoff,
                    governor_cause=decision.cause)
                entry["execution"] = execution
            elif (self.mode == Mode.REAL and plan.action.value == "dream_train"
                    and subject.kind == "tier0_specialist"):
                from . import dream_niches
                execution = dream_niches.run_dream_niche_subject(
                    subject, plan, self.run_dir, self.lineage, self.cycle_id,
                    governor_backoff=decision.backoff,
                    governor_cause=decision.cause)
                entry["execution"] = execution
            if execution is not None:
                self.lineage.append("stage_start", cycle_id=self.cycle_id,
                                    stage="verify", subject=subject.subject_id,
                                    mode=self.mode.value)
                if execution.get("executor") == "dream":
                    from . import dream
                    ver = dream.verify_dream_measured(subject, plan, execution)
                elif execution.get("executor") == "dream_niche":
                    from . import dream_niches
                    ver = dream_niches.verify_dream_niche_measured(
                        subject, plan, execution)
                else:
                    from . import executors
                    ver = executors.verify_measured(subject, plan, execution)
                r = self._record_stage(subject, "verify", ver)
            elif self.mode == Mode.REAL and plan.action.value != "no_op":
                from .contracts import Verification as _V
                self.lineage.append("stage_start", cycle_id=self.cycle_id,
                                    stage="verify", subject=subject.subject_id,
                                    mode=self.mode.value)
                ver = _V(subject.subject_id, verdict="BLOCKED", measured=False,
                         reasons=["REAL mode: no executor exists for this plan "
                                  "(fail-closed); executors exist for Tier-0 "
                                  "TRAIN_DATA_WIDEN plans (Phase B), the "
                                  "bug-pattern DREAM_TRAIN plan (Phase C), and "
                                  "niche DREAM_TRAIN plans for generator-backed "
                                  "drift subjects (final-product)"])
                r = self._record_stage(subject, "verify", ver)
            else:
                r = self._stage(subject, "verify", stage_fns.verify,
                                subject, plan, indictment)
            entry["verify"] = r.output
            if not r.ok:
                report["subjects"][subject.subject_id] = entry
                continue
            verification = Verification.from_dict(r.output)
            r = self._stage(subject, "compose", stage_fns.compose,
                            subject, plan, verification)
            entry["compose"] = r.output
            if not r.ok:
                report["subjects"][subject.subject_id] = entry
                continue
            composition = CompositionPlan.from_dict(r.output)
            r = self._stage(subject, "grow", stage_fns.grow,
                            subject, diagnosis, composition)
            entry["grow"] = r.output
            report["subjects"][subject.subject_id] = entry

        blocked = dict(self.state.blocked)
        self.state.status = "complete"
        self.store.save(self.state)
        report["blocked"] = blocked
        report["stages"] = STAGES
        with open(self.run_dir / "cycle_report.json", "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=1, ensure_ascii=False)
        self.lineage.append("cycle_complete", cycle_id=self.cycle_id,
                            subjects_completed=len(report["subjects"]),
                            blocked=blocked)
        note = ("Phase A dry-run: shadow plans only; no edits, no training, "
                "no eval legs, no GPU" if self.mode == Mode.DRY_RUN else
                "Real cycle: Tier-0 widen plans (Phase B), the "
                "bug-pattern dream plan (Phase C), and niche dream plans "
                "for generator-backed drift subjects (final-product) "
                "execute and are judged by the measured win-gate; all "
                "other plans fail closed or hold")
        self.factory_lineage.append(
            "factory_cycle", cycle_id=self.cycle_id, mode=self.mode.value,
            run_dir=f"factory/runs/{self.cycle_id}",
            subjects=list(report["subjects"].keys()), blocked=blocked,
            note=note)
        return report
