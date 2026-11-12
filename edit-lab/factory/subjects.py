"""Subject loaders: wire the loop to existing lab evidence.

Read-only. This module reads the lab's recorded results — it never
trains, never evals, never writes outside factory/. Two subject
families (Phase A dry-run):

  1. The adopted coding specialists (coding/swarm/phase3_results.json,
     adopted == True), cross-checked against the fresh-surface battery
     (results/hive_battery.json) — same-distribution held-out vs fresh
     surfaces is exactly the diagnosis the loop needs.
  2. The bug-pattern composition (coding/swarm/phase4_results.json):
     per-class Tier-0 binaries composed to 0.7931 against a 0.800 bar.
  3. The coordinator winner synthv1-r4 (candsets/synthv1-r4/ +
     results/test_synthv1_r4.json): pristine 0.954 vs the 0.930 gate.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .contracts import Subject

# coding job name -> hive battery task key
_BATTERY_KEY = {
    "secret-line-model": "classify-secret-line",
    "error-class-model": "classify-error-class",
    "commit-type-model": "classify-commit-type",
    "contract-judgment-model": "classify-contract-judgment",
    "gap-move-model": "classify-gap-move",
}
_BATTERY_BAR = {  # correct-count bars recorded in the battery details
    "classify-secret-line": (9, 12),
    "classify-error-class": (9, 12),
    "classify-commit-type": (9, 12),
    "classify-contract-judgment": (9, 12),
    "classify-gap-move": (6, 10),
}


def _load_json(path: Path) -> Any:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_coding_subjects(lab_root: Path) -> List[Subject]:
    lab_root = Path(lab_root)
    phase3 = _load_json(lab_root / "coding" / "swarm" / "phase3_results.json")
    battery = _load_json(lab_root / "results" / "hive_battery.json")
    subjects: List[Subject] = []
    for row in phase3.get("table", []):
        if not row.get("adopted"):
            continue
        job = row["job"]
        subj = Subject(
            subject_id=job,
            kind="tier0_specialist",
            niche=row.get("niche", ""),
            artifact_path=f"coding/swarm/models/{job}.json",
            params=row.get("params"),
            footprint_bytes=row.get("footprint_bytes"),
            heldout_score=row.get("heldout_acc"),
            adopted=True,
            evidence_paths=["coding/swarm/phase3_results.json", "results/hive_battery.json"],
            metadata={"path": row.get("path", ""),
                      "incumbents": row.get("incumbents", [])},
        )
        bkey = _BATTERY_KEY.get(job)
        if bkey and bkey in battery:
            b = battery[bkey]
            subj.fresh_score = b.get("score")
            subj.fresh_label = "hive battery fresh-surface probe (2026-11-10)"
            if bkey in _BATTERY_BAR:
                need, n = _BATTERY_BAR[bkey]
                subj.fresh_bar = need / n
                subj.metadata["fresh_bar_detail"] = f"{need}/{n} correct"
            subj.metadata["battery_status"] = b.get("status")
            subj.metadata["battery_detail"] = (b.get("detail") or "")[:400]
        # Phase C intake fix, generalized at final-product time: if
        # the factory adopted a newer version for this job (Phase B
        # v2 wins; later cycles may add v3+), the subject IS the
        # highest adopted version — diagnose the artifact that
        # actually serves, with its own measured evidence, and keep
        # the v1 numbers in metadata for the record.
        models_dir = lab_root / "coding" / "swarm" / "models"
        v2_path = None
        for cand in sorted(models_dir.glob(f"{job}-v*.json")):
            stem = cand.stem[len(job) + 2:]
            if stem.isdigit():
                rec_c = _load_json(cand)
                if rec_c.get("adopted"):
                    v2_path = cand   # ascending order: highest adopted wins
        if v2_path is not None:
            v2 = _load_json(v2_path)
            subj.metadata["v1_record"] = {
                "heldout_score": subj.heldout_score,
                "fresh_score": subj.fresh_score,
                "params": subj.params,
                "artifact_path": subj.artifact_path}
            subj.artifact_path = f"coding/swarm/models/{v2_path.name}"
            subj.params = v2.get("params", subj.params)
            subj.footprint_bytes = v2.get("footprint_bytes",
                                          subj.footprint_bytes)
            subj.heldout_score = v2.get("heldout_acc", subj.heldout_score)
            if v2.get("fresh_confirm_acc") is not None:
                subj.fresh_score = v2["fresh_confirm_acc"]
                subj.fresh_label = ("factory one-shot fresh confirm "
                                    f"({v2.get('factory_cycle')}, "
                                    "confirm set spent once)")
            subj.metadata["version"] = (f"{v2_path.stem[len(job):]} "
                                        "(factory-adopted)")
            subj.metadata["supersedes"] = v2.get("supersedes", job)
            subj.metadata["factory_cycle"] = v2.get("factory_cycle")
            subj.metadata["fresh_screen_acc_v2"] = v2.get("fresh_screen_acc")
            subj.metadata["battery_reference_v2"] = v2.get(
                "battery_reference_acc")
            if v2.get("dream"):
                subj.metadata["dream"] = v2["dream"]
            subj.evidence_paths = list(subj.evidence_paths) + [
                f"coding/swarm/models/{v2_path.name}"]
        subjects.append(subj)

    # The bug-pattern composition: not adopted as a single model; its
    # per-class binaries were adopted and composed (phase 4).
    phase4_path = lab_root / "coding" / "swarm" / "phase4_results.json"
    if phase4_path.exists():
        p4 = _load_json(phase4_path)
        rounds = p4.get("rounds", [])
        final_acc = rounds[-1]["composed_acc"] if rounds else None
        per_class = {c: {"heldout_acc": v.get("heldout_acc"), "recall": v.get("recall"),
                         "adopted": v.get("adopted")}
                     for c, v in p4.get("classes", {}).items()}
        comp = Subject(
            subject_id="bug-pattern-composed",
            kind="tier0_composition",
            niche="debugging",
            artifact_path="coding/swarm/models/ (per-class bug-*-model.json)",
            heldout_score=final_acc,
            heldout_bar=p4.get("bar"),
            adopted=False,
            evidence_paths=["coding/swarm/phase4_results.json"],
            metadata={"per_class": per_class,
                      "single_model_reference": p4.get("single_model_reference"),
                      "rounds_tried": [r.get("what") for r in rounds]},
        )
        # Final-product intake: the Phase C dream cycle adopted a
        # retrained wrong-operator binary against the phase-4 set
        # (confirm 0.8276, that set now SPENT), and the sealed
        # held-out v2 baseline is the current standing measurement
        # of the serving composition. Diagnose what serves, on the
        # freshest sealed evidence; keep the phase-4 record in
        # metadata.
        dream_out_path = (lab_root / "factory" / "runs" /
                          "dream-phaseC-002" / "subjects" /
                          "bug-pattern-composed" / "outcome.json")
        if dream_out_path.exists():
            dout = _load_json(dream_out_path)
            if dout.get("win"):
                comp.metadata["phase4_record"] = {
                    "heldout_score": comp.heldout_score,
                    "per_class": per_class}
                comp.metadata["dream_phaseC"] = {
                    "cycle": "dream-phaseC-002",
                    "confirm_acc_on_spent_phase4_set":
                        dout["finalist"]["composed_confirm_acc"],
                    "adopted_files": dout.get("adopted_files")}
                comp.adopted = True
                comp.evidence_paths = list(comp.evidence_paths) + [
                    "factory/runs/dream-phaseC-002/subjects/"
                    "bug-pattern-composed/outcome.json"]
        base_path = lab_root / "results" / "bug_heldout_v2_baseline.json"
        if base_path.exists():
            base = _load_json(base_path)
            recalls = base.get("per_class_recall", {})
            comp.metadata["phase4_per_class"] = per_class
            comp.metadata["per_class"] = {
                c: {"heldout_acc": None, "recall": recalls.get(c),
                    "adopted": per_class.get(c, {}).get("adopted")}
                for c in per_class}
            comp.heldout_score = base["composed_acc"]
            comp.fresh_score = base["composed_acc"]
            comp.fresh_label = ("sealed held-out v2 baseline "
                                f"({base['measured_at']}, no tuning)")
            comp.fresh_bar = p4.get("bar")
            comp.metadata["fresh_sealed_baseline"] = {
                "file": "results/bug_heldout_v2_baseline.json",
                "sealed_sha256": base.get("sealed_sha256"),
                "n": base.get("n")}
            comp.evidence_paths = list(comp.evidence_paths) + [
                "results/bug_heldout_v2_baseline.json",
                "coding/swarm/bug_heldout_v2.json"]
        subjects.append(comp)
    return subjects


def load_coordinator_subject(lab_root: Path) -> Subject:
    lab_root = Path(lab_root)
    test = _load_json(lab_root / "results" / "test_synthv1_r4.json")
    cases = test.get("cases", {}).get("coordinator", [])
    failing: List[Dict[str, Any]] = []
    for i, c in enumerate(cases, start=1):
        if c.get("score", 1.0) < 1.0:
            failed_checks = [k for k, v in (c.get("checks") or {}).items() if v is False]
            failing.append({"case_index": i, "score": c.get("score"),
                            "failed_checks": failed_checks,
                            "case_preview": (c.get("case") or "")[:120],
                            "problems": c.get("problems", [])})
    meta_path = lab_root / "candsets" / "synthv1-r4" / "coordinator" / "training_meta.json"
    meta = _load_json(meta_path) if meta_path.exists() else {}
    return Subject(
        subject_id="synthv1-r4-coordinator",
        kind="tier1_adapter",
        niche="coordinator",
        artifact_path="candsets/synthv1-r4/coordinator/",
        heldout_score=None,  # judged on dev + pristine, below
        fresh_score=test.get("scores", {}).get("coordinator", {}).get("mean"),
        fresh_bar=0.930,
        fresh_label="pristine coordinator test (sealed, one run, n=14)",
        incumbent_score=0.930,  # reproduced base anchor
        adopted=True,
        evidence_paths=["results/test_synthv1_r4.json", "results/lineage.jsonl",
                        "candsets/synthv1-r4/coordinator/training_meta.json"],
        failing_cases=failing,
        metadata={"dev_score": 0.9483, "base_dev_score": 0.7479,
                  "rank": meta.get("rank"), "alpha": meta.get("alpha"),
                  "layers": meta.get("layers"), "train_examples": meta.get("examples"),
                  "contest": "CLOSED 2026-11-10: WIN 0.954 > 0.930 gate; no further "
                             "candidates against this gate per Arnav's binding decision"},
    )


def load_subjects(lab_root: Path) -> List[Subject]:
    return load_coding_subjects(lab_root) + [load_coordinator_subject(lab_root)]
