"""The shared composition registry (arch. section 5; final-product
item 3): ONE book for everything this side of the hive serves.

Before this module, the swarm and the lab kept separate books —
phase3_results.json said what was adopted in Phase 3, the v2/v3
model files carried Phase B/C adoption records, the ternary pack
lived in its own record, the bug composition's state was split
across phase4_results.json + composer_config.json + the dream
outcome, and the coordinator winner's evidence sat in results/.
The registry consolidates the CURRENT serving truth:

  * per specialist job: the serving artifact — chosen by the
    STANDING SERVING RULE (an adopted version serves only when
    its measured battery slice, factory/battery_evidence.json,
    is >= the incumbent's; otherwise it is registered as shadow:
    audited, never served, never a fallback), its fallback chain
    (versions that served before), its shadow list, and the
    adoption evidence recorded at its gate;
  * the ternary secret-line artifact as a coexisting substrate
    member (fp stays the niche default — the head-to-head gate
    decided that; the registry records the decision, not a wish);
  * the bug-pattern composition: every adopted member file, the
    composer config, and its evidence chain (phase-4 plateau ->
    dream confirm on the spent set -> sealed v2 baseline);
  * the Tier-1 coordinator winner (adopted, contest closed —
    registered for provenance; serving it needs the LM backend).

Every file entry carries the sha256 of its bytes. The audit
(factory/audit.py) verifies served artifacts against this book and
fails closed on any mismatch; the serving path (factory/serve.py)
reads ONLY this book. Rebuild after any adoption:

    python3 -m factory.registry
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .executors import _atomic_json
from .lineage import now_ts

LAB_ROOT = Path(__file__).parent.parent
MODELS_DIR = LAB_ROOT / "coding" / "swarm" / "models"
REGISTRY_PATH = Path(__file__).parent / "registry.json"
SPECIALIST_JOBS = ["secret-line-model", "error-class-model",
                   "commit-type-model", "contract-judgment-model",
                   "gap-move-model"]


# THE STANDING SERVING RULE (Arnav's direction 2026-11-10,
# created by the contract-judgment v3 case): adoption and serving
# are different decisions. An adopted artifact becomes the
# SERVING artifact only when its measured battery slice
# (factory/battery_evidence.json) is >= the serving incumbent's
# slice. Until then it is registered as SHADOW: on the books,
# hash-audited, never served, never a fallback. A version with
# no measured slice cannot be promoted (fail-closed). The
# battery is the independent surface a cycle's own gates never
# consult — v3 passed its win-gates (paired confirm 0.9048,
# held-out 1.0) and still measured 5/12 against v2's 11/12.
BATTERY_EVIDENCE_PATH = Path(__file__).parent / "battery_evidence.json"


def _battery_evidence() -> Dict[str, Dict[str, Any]]:
    if not BATTERY_EVIDENCE_PATH.exists():
        raise ValueError(
            "factory/battery_evidence.json is missing: serving "
            "cannot be determined under the standing rule "
            "(fail-closed — no evidence, no promotion)")
    return json.loads(BATTERY_EVIDENCE_PATH.read_text())["artifacts"]


def _apply_serving_rule(job: str, entries: List[Dict[str, Any]],
                        evidence: Dict[str, Dict[str, Any]]):
    """entries: version-ascending artifact entries for one job.
    Returns (serving, fallbacks, shadow) under the standing rule."""
    serving = dict(entries[0], role="serving")
    serving_ev = evidence.get(serving["name"])
    if serving_ev:
        serving["battery_acc"] = serving_ev["battery_acc"]
        serving["battery_source"] = serving_ev["source"]
    fallbacks: List[Dict[str, Any]] = []
    shadow: List[Dict[str, Any]] = []
    for entry in entries[1:]:
        ev = evidence.get(entry["name"])
        entry = dict(entry)
        if ev:
            entry["battery_acc"] = ev["battery_acc"]
            entry["battery_source"] = ev["source"]
        if ev and serving_ev and \
                ev["battery_acc"] >= serving_ev["battery_acc"]:
            displaced = dict(serving, role="fallback")
            displaced.pop("promotion", None)
            fallbacks.insert(0, displaced)
            serving = dict(entry, role="serving")
            serving["promotion"] = {
                "rule": "standing serving rule: battery slice >= "
                        "the incumbent's slice",
                "battery_acc": ev["battery_acc"],
                "incumbent_battery_acc": serving_ev["battery_acc"],
                "source": ev["source"]}
            serving_ev = ev
        else:
            entry["role"] = "shadow"
            if not ev:
                entry["shadow_reason"] = (
                    "no measured battery slice in "
                    "factory/battery_evidence.json — the standing "
                    "rule cannot promote what the battery has not "
                    "measured (fail-closed)")
            elif not serving_ev:
                entry["shadow_reason"] = (
                    "the serving incumbent has no recorded battery "
                    "slice, so no comparison exists to promote on "
                    "(fail-closed)")
            else:
                entry["shadow_reason"] = (
                    f"standing serving rule: battery slice "
                    f"{ev['battery_acc']} < incumbent "
                    f"{serving['name']}'s {serving_ev['battery_acc']} "
                    f"({ev['source']}) — adopted, audited, not served")
            shadow.append(entry)
    return serving, fallbacks, shadow


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load(path: Path) -> Any:
    return json.loads(Path(path).read_text())


def _artifact_entry(lab_root: Path, path: Path, role: str) -> Dict[str, Any]:
    rec = _load(path)
    entry = {
        "name": rec["name"], "role": role,
        "path": str(path.relative_to(lab_root)),
        "sha256": sha256_file(path),
        "substrate": rec.get("substrate", "fp"),
        "params": rec.get("params"),
        "footprint_bytes": rec.get("footprint_bytes"),
        "heldout_acc": rec.get("heldout_acc"),
        "evidence": {
            "factory_cycle": rec.get("factory_cycle"),
            "path_taken": rec.get("path"),
            "supersedes": rec.get("supersedes"),
            "fresh_confirm_acc": rec.get("fresh_confirm_acc"),
            "fresh_screen_acc": rec.get("fresh_screen_acc"),
            "battery_reference_acc": rec.get("battery_reference_acc"),
            "train_n": rec.get("train_n"),
            "heldout_n": rec.get("heldout_n"),
            "dream": rec.get("dream"),
            "flips_applied": rec.get("flips_applied"),
        },
    }
    if rec.get("payload"):
        # ternary BitNet artifact (assembly 2026-11-10): the record
        # is the adoption book entry; the npz payload is the served
        # bytes. Both are hash-audited (factory/audit.py).
        entry["payload"] = {
            "path": rec["payload"]["path"],
            "sha256": rec["payload"]["sha256"],
            "runtime": rec["payload"].get("runtime"),
            "payload_bytes_theoretical":
                rec["payload"].get("payload_bytes_theoretical"),
        }
    return entry


def _versions_of(lab_root: Path, job: str) -> List[Path]:
    """All adopted artifact files for a job, v1 first, highest
    adopted version last (the serving one)."""
    out: List[Path] = []
    v1 = MODELS_DIR / f"{job}.json"
    if v1.exists() and _load(v1).get("adopted"):
        out.append(v1)
    vers = []
    for cand in sorted(MODELS_DIR.glob(f"{job}-v*.json")):
        stem = cand.stem[len(job) + 2:]
        if stem.isdigit() and _load(cand).get("adopted"):
            vers.append(cand)
    out.extend(vers)
    return out


def _sealed_evidence(lab_root: Path) -> Optional[Dict[str, Any]]:
    """The sealed v2 evidence: the recorded baseline, superseded
    as the standing number by the post-fix judge measurement when
    that exists (factory/run_bug_heldout_postfix.py — the ONE
    re-judge after the 2026-11-10 fix attempts; both numbers stay
    in the book)."""
    base_path = lab_root / "results" / "bug_heldout_v2_baseline.json"
    sealed_path = lab_root / "coding" / "swarm" / "bug_heldout_v2.json"
    if not base_path.exists():
        return None
    base = _load(base_path)
    ev: Dict[str, Any] = {
        "acc": base["composed_acc"],
        "per_class_recall": base["per_class_recall"],
        "n": base["n"],
        "file": "results/bug_heldout_v2_baseline.json",
        "sealed_file": "coding/swarm/bug_heldout_v2.json",
        "sealed_sha256": (_load(sealed_path)["sha256"]
                          if sealed_path.exists() else None)}
    post_path = lab_root / "results" / "bug_heldout_v2_postfix.json"
    if post_path.exists():
        post = _load(post_path)
        ev["baseline_acc"] = base["composed_acc"]
        ev["baseline_recalls"] = base["per_class_recall"]
        ev["acc"] = post["composed_acc"]
        ev["per_class_recall"] = post["per_class_recall"]
        ev["post_fix_file"] = "results/bug_heldout_v2_postfix.json"
        ev["post_fix_cycle"] = post.get("fix_cycle")
    # Growth-cycle judges (2026-11-11): when a growth cycle adopts
    # a birth that changes the composition, its post-adoption judge
    # measurement (results/bug_heldout_v2_growth-<cycle>.json,
    # written by factory/growth_cycle.py after the battery gate
    # passed) supersedes as the standing number, exactly like the
    # post-fix judge did. The full chain stays in the book; a
    # rolled-back birth deletes its judge file and the chain falls
    # back on its own.
    growth_files = sorted(
        (lab_root / "results").glob("bug_heldout_v2_growth-*.json"))
    if growth_files:
        g = _load(growth_files[-1])
        ev["pre_growth_acc"] = ev["acc"]
        ev["pre_growth_recalls"] = ev["per_class_recall"]
        ev["acc"] = g["composed_acc"]
        ev["per_class_recall"] = g["per_class_recall"]
        ev["growth_judge_file"] = str(
            growth_files[-1].relative_to(lab_root))
        ev["growth_cycle"] = g.get("cycle_id")
    return ev


def build_registry(lab_root: Optional[Path] = None) -> Dict[str, Any]:
    lab_root = Path(lab_root) if lab_root else LAB_ROOT
    evidence = _battery_evidence()
    specialists: Dict[str, Any] = {}
    for job in SPECIALIST_JOBS:
        files = _versions_of(lab_root, job)
        if not files:
            continue
        entries = [_artifact_entry(lab_root, f, "adopted")
                   for f in files]
        serving, fallbacks, shadow = _apply_serving_rule(
            job, entries, evidence)
        specialists[job] = {
            "niche": _load(files[-1]).get("niche"),
            "serving": serving, "fallbacks": fallbacks,
            "shadow": shadow,
            "substrate_default": "fp",
        }
    # ternary coexisting member (secret-line niche)
    substrates: List[Dict[str, Any]] = []
    tern_path = MODELS_DIR / "secret-line-model-ternary.json"
    if tern_path.exists() and _load(tern_path).get("adopted"):
        entry = _artifact_entry(lab_root, tern_path,
                                "coexisting_alternative")
        entry["niche_default"] = False
        entry["note"] = ("flip-surgery-repaired ternary pack (Phase C); "
                         "held-out 0.9385 < fp 1.0, so fp remains the "
                         "niche default and this serves only where a "
                         "caller names the ternary substrate")
        substrates.append(entry)
        if "secret-line-model" in specialists:
            specialists["secret-line-model"]["substrates"] = substrates

    # bug-pattern composition
    members = []
    for f in sorted(MODELS_DIR.glob("bug-*.json")):
        rec = _load(f)
        if rec.get("adopted"):
            members.append(_artifact_entry(lab_root, f, "member"))
    cfg_path = MODELS_DIR / "composer_config.json"
    p4 = _load(lab_root / "coding" / "swarm" / "phase4_results.json")
    dream_out = (lab_root / "factory" / "runs" / "dream-phaseC-002" /
                 "subjects" / "bug-pattern-composed" / "outcome.json")
    base_path = lab_root / "results" / "bug_heldout_v2_baseline.json"
    sealed_path = lab_root / "coding" / "swarm" / "bug_heldout_v2.json"
    composition = {
        "name": "bug-pattern-composed",
        "niche": "debugging",
        "role": "composition",
        "members": members,
        "composer_config": {
            "path": str(cfg_path.relative_to(lab_root)),
            "sha256": sha256_file(cfg_path),
            "ensemble": _load(cfg_path).get("ensemble"),
            "thresholds": _load(cfg_path).get("thresholds"),
        },
        "evidence": {
            "phase4_plateau_acc": p4["rounds"][-1]["composed_acc"],
            "bar": p4.get("bar"),
            "dream_confirm_acc_on_spent_phase4_set": (
                _load(dream_out)["finalist"]["composed_confirm_acc"]
                if dream_out.exists() else None),
            "fresh_sealed_baseline": _sealed_evidence(lab_root),
        },
        "fallback": ("the phase-4 composition (plateau 0.7931): the "
                     "pre-dream member records are backed up inside "
                     "factory/runs/dream-phaseC-002"),
    }
    # Serving layer (assembly 2026-11-10, Arnav's ruling): the
    # waking-dream verify-while-answering wrapper is the SERVING
    # path for bug-pattern — it runs over the untouched fp member
    # binaries above; when no candidate verifies, the raw composer
    # verdict stands (flagged). Its sealed-v2 measurement
    # (0.8333 vs the raw composition's 0.4444) is recorded in
    # waking-dream/results.json; the layer's code file is hashed
    # into this book and audited like an artifact.
    wd_path = lab_root / "waking-dream" / "waking_dream.py"
    wd_results = lab_root / "waking-dream" / "results.json"
    if wd_path.exists() and wd_results.exists():
        wd = _load(wd_results)
        composition["serving_layer"] = {
            "name": "waking-dream",
            "role": "serving_layer",
            "path": str(wd_path.relative_to(lab_root)),
            "sha256": sha256_file(wd_path),
            "mechanism": ("margins nominate the top-3 defect "
                          "candidates (+clean); each candidate must "
                          "prove its behavioral signature by "
                          "execution; strongest verified signature "
                          "wins; none verifies -> raw composer "
                          "verdict stands, flagged unverified"),
            "sealed_acc": wd["waking_dream"]["acc"],
            "sealed_n": wd["n"],
            "sealed_file": wd["sealed_file"],
            "sealed_sha256": wd["sealed_sha256"],
            "raw_composition_acc": wd["baseline_composed_acc"],
            "evidence_file": "waking-dream/results.json",
            "fallback": "raw composer verdict (the members above)",
        }

    # Tier-1 coordinator winner (provenance only — serving needs the
    # LM backend; the registry does not pretend otherwise)
    coord_dir = lab_root / "candsets" / "synthv1-r4" / "coordinator"
    test = _load(lab_root / "results" / "test_synthv1_r4.json")
    tier1 = {
        "name": "synthv1-r4-coordinator",
        "role": "tier1_adopted",
        "artifact_dir": str(coord_dir.relative_to(lab_root)),
        "files": {f.name: sha256_file(f)
                  for f in sorted(coord_dir.iterdir()) if f.is_file()},
        "evidence": {
            "pristine_test_acc": test.get("scores", {}).get(
                "coordinator", {}).get("mean"),
            "gate": 0.930,
            "contest": "CLOSED 2026-11-10 — WIN; the winner is "
                       "untouched by the factory (no executor, by "
                       "design and by Arnav's binding decision)",
        },
        "serving": "via team.Hive with the HF backend (see the "
                   "whole-hive battery); not served by factory/serve.py",
    }

    return {
        "registry_version": 1,
        "built_at": now_ts(),
        "built_by": "factory.registry.build_registry",
        "note": ("the single serving book for this side of the hive; "
                 "verify with factory.audit; serve only through "
                 "factory.serve (which audits at load and fails "
                 "closed on mismatch)"),
        "specialists": specialists,
        "compositions": {"bug-pattern-composed": composition},
        "tier1": {"synthv1-r4-coordinator": tier1},
    }


def write_registry(lab_root: Optional[Path] = None) -> Path:
    reg = build_registry(lab_root)
    _atomic_json(REGISTRY_PATH, reg)
    return REGISTRY_PATH


def load_registry(path: Optional[Path] = None) -> Dict[str, Any]:
    return _load(Path(path) if path else REGISTRY_PATH)


def main() -> int:
    path = write_registry()
    reg = load_registry()
    n_members = sum(len(c["members"])
                    for c in reg["compositions"].values())
    print(f"wrote {path}: {len(reg['specialists'])} specialist jobs, "
          f"{n_members} composition members, "
          f"{len(reg['tier1'])} tier-1 records")
    for job, s in reg["specialists"].items():
        print(f"  {job}: serving {s['serving']['name']} "
              f"(held {s['serving']['heldout_acc']}), "
              f"fallbacks {[f['name'] for f in s['fallbacks']]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
