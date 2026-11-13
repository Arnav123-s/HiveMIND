"""The serving path (arch. section 5; final-product item 3): ONE
entry point into this side of the hive.

    from factory.serve import ServingHive
    hive = ServingHive.load()          # audits at load, fail-closed
    hive.serve({"kind": "classify", "job": "commit-type-model",
                "text": "fix crash in the cart"})
    hive.serve({"kind": "bug-pattern",
                "code": "def f(xs):\n    return xs[len(xs)]"})

Serving reads ONLY the shared registry (factory/registry.json):
the serving artifact per job is the highest adopted version, the
composition serves its registered members through the swarm's
composer machinery, and every answer carries its provenance
(artifact name + registry sha). At load, the file audit runs —
any artifact whose bytes differ from its adoption record refuses
the whole load (fail-closed: an unverified artifact does not
serve, and neither does anything else through a tainted book).

Honest scope: this entry point serves Tier 0 (the TinyNet
specialists + the bug composition) and the ternary substrate
where a caller names it. The Tier-1 coordinator is registered
for provenance; serving it needs the LM backend (team.Hive, as
exercised by the whole-hive battery), and serve() says so instead
of pretending.

Assembly 2026-11-10 (Arnav's ruling — proven fixes switched ON):
  * bug-pattern serves through the waking-dream layer registered
    in the composition's serving_layer (verify-while-answering
    over the untouched fp member binaries; raw composer verdict
    as the flagged fallback);
  * ternary BitNet artifacts adopted under the battery gate
    (payload records) serve through factory/tern_runtime.py via
    factory/artifacts.py — the same loader the audit measures
    with. A classify call with no substrate named gets the
    registry's serving artifact, whatever its substrate; naming
    a substrate resolves: registered substrate members first,
    then the serving artifact, then fallbacks.

Learned say (2026-11-12, Fable-study Build 2): when the battery
has adopted a learned say (factory/learned_say.json, status
"adopted" — run state, deliberately outside this registry), the
waking-dream layer is built with the say's merged composer config
(per-seat standings + fitted thresholds). Any problem reading the
say state serves the incumbent fixed composition instead.

Decision log (2026-11-12, Fable-study Build 3): every serve()
call appends one JSON line to factory/serve_log.jsonl (override
with FACTORY_SERVE_LOG) — the raw material for spawn mining.
Logging never breaks serving: a failed append is swallowed.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

LAB_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(LAB_ROOT / "coding"))
sys.path.insert(0, str(LAB_ROOT))

from swarm import composers as C  # noqa: E402
from swarm import factory as F  # noqa: E402

from . import artifacts as artifacts_mod  # noqa: E402
from . import audit as audit_mod  # noqa: E402
from . import learned_say as say_mod  # noqa: E402
from .registry import REGISTRY_PATH, load_registry  # noqa: E402

SERVE_LOG_PATH = Path(__file__).parent / "serve_log.jsonl"


def _append_serve_log(task: Dict[str, Any], result: Dict[str, Any]) -> None:
    """Append one decision-log line (Build 3's mining source).
    Swallows every failure — the log serves the hive, never the
    other way round."""
    try:
        raw = task.get("text", task.get("code", "")) or ""
        prov = result.get("provenance") or {}
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "kind": task.get("kind"),
            "job": task.get("job"),
            "substrate": task.get("substrate"),
            "input_sha": hashlib.sha256(
                raw.encode("utf-8", "ignore")).hexdigest()[:16],
            "input_head": raw[:80],
            "ok": result.get("ok"),
            "output": (str(result.get("output"))[:60]
                       if result.get("output") is not None else None),
            "gap": result.get("gap"),
            "artifact": prov.get("artifact") or prov.get("composition"),
            "mechanism": prov.get("mechanism"),
            "verification_fired": prov.get("verification_fired"),
            "composer_verdict": prov.get("composer_verdict"),
        }
        path = Path(os.environ.get("FACTORY_SERVE_LOG", SERVE_LOG_PATH))
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001
        pass


class ServingRefused(Exception):
    """Raised when the audit fails: nothing serves from a book that
    does not match the artifacts on disk."""


class ServingHive:
    def __init__(self, registry: Dict[str, Any],
                 lab_root: Path = LAB_ROOT):
        self.registry = registry
        self.lab_root = Path(lab_root)
        self._models: Dict[str, Any] = {}
        self._composer = None
        self._waking = None
        self._say: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------ load
    @classmethod
    def load(cls, registry_path: Optional[Path] = None,
             lab_root: Path = LAB_ROOT) -> "ServingHive":
        reg = load_registry(registry_path or REGISTRY_PATH)
        failures = audit_mod.verify_files(reg, lab_root)
        failures += audit_mod.verify_rule(reg)
        if failures:
            raise ServingRefused(
                f"serve-time audit failed ({len(failures)} mismatch(es)); "
                f"first: {failures[0]}")
        return cls(reg, lab_root)

    # ------------------------------------------------------------ models
    def _model(self, path_rel: str):
        """Load a registered artifact file through the unified
        loader (TinyNet record or ternary payload record)."""
        if path_rel not in self._models:
            rec = json.loads((self.lab_root / path_rel).read_text())
            self._models[path_rel] = artifacts_mod.load_artifact(
                rec, self.lab_root)
        return self._models[path_rel]

    def specialist(self, job: str):
        """The serving artifact for a specialist job (registry's
        serving entry — the highest adopted version under the
        standing serving rule)."""
        entry = self.registry["specialists"][job]["serving"]
        return self._model(entry["path"])

    def resolve_entry(self, job: str,
                      substrate: Optional[str]) -> Optional[Dict[str, Any]]:
        """Which registered artifact answers a classify call.
        substrate=None -> the serving entry. A named substrate
        resolves: registered substrate members first (the
        coexisting alternatives), then the serving entry, then
        fallbacks — first substrate match wins."""
        spec = self.registry["specialists"][job]
        if substrate is None:
            return spec["serving"]
        for sub in spec.get("substrates", []):
            if sub["substrate"] == substrate:
                return sub
        if spec["serving"]["substrate"] == substrate:
            return spec["serving"]
        for fb in spec.get("fallbacks", []):
            if fb["substrate"] == substrate:
                return fb
        return None

    def substrate_model(self, job: str, substrate: str):
        entry = self.resolve_entry(job, substrate)
        if entry is None:
            raise KeyError(
                f"no {substrate} substrate registered for {job}")
        return self._model(entry["path"])

    def bug_composer(self):
        if self._composer is None:
            comp = self.registry["compositions"]["bug-pattern-composed"]
            reg: Dict[str, F.TinyNet] = {}
            for m in comp["members"]:
                model = self._model(m["path"])
                reg[model.name] = model
            self._composer = C.make_bug_pattern_composer(reg)
        return self._composer

    def waking_dream(self):
        """The registered serving layer for bug-pattern: the
        waking-dream wrapper over the composition's member
        binaries (loaded from THIS book, not a directory scan).
        Its margins need TinyNet members — a payload member in
        the composition would fail closed here, loudly."""
        if self._waking is None:
            comp = self.registry["compositions"]["bug-pattern-composed"]
            if not comp.get("serving_layer"):
                raise ServingRefused(
                    "the registry names no serving layer for "
                    "bug-pattern; refusing to serve the raw "
                    "composition as if it were the product")
            reg: Dict[str, F.TinyNet] = {}
            for m in comp["members"]:
                model = self._model(m["path"])
                if not isinstance(model, F.TinyNet):
                    raise ServingRefused(
                        f"composition member {m['name']} is not a "
                        f"TinyNet; the waking-dream layer cannot "
                        f"take its margins (fail-closed)")
                reg[model.name] = model
            wd_dir = str(self.lab_root / "waking-dream")
            if wd_dir not in sys.path:
                sys.path.insert(0, wd_dir)
            import waking_dream as wd_mod
            # Learned say (Build 2): an adopted say merges into the
            # composer config the layer runs with; anything else
            # (no state, shadow, unreadable) serves the incumbent
            # fixed composition.
            base_cfg = C.load_config()
            self._say = say_mod.load_serving_say()
            cfg = say_mod.merged_config(base_cfg, self._say) \
                if self._say else base_cfg
            self._waking = wd_mod.WakingDream(
                registry=reg, config=cfg)
        return self._waking

    # ------------------------------------------------------------ serve
    def serve(self, task: Dict[str, Any]) -> Dict[str, Any]:
        result = self._serve_impl(task)
        _append_serve_log(task, result)
        return result

    def _serve_impl(self, task: Dict[str, Any]) -> Dict[str, Any]:
        kind = task.get("kind")
        if kind == "classify":
            job = task.get("job", "")
            if job not in self.registry["specialists"]:
                return {"ok": False, "output": None,
                        "gap": f"no specialist registered for job {job!r}",
                        "growth_move": "registry intake (factory growth)"}
            entry = self.resolve_entry(job, task.get("substrate"))
            if entry is None:
                return {"ok": False, "output": None,
                        "gap": f"no {task.get('substrate')!r} substrate "
                               f"registered for job {job!r}",
                        "growth_move": "breed the named substrate "
                                       "(factory ternary stage)"}
            model = self._model(entry["path"])
            out = model.run({"text": task.get("text", "")})
            out["provenance"] = {
                "artifact": entry["name"], "path": entry["path"],
                "sha256": entry["sha256"][:16],
                "substrate": entry["substrate"],
                "heldout_acc": entry["heldout_acc"]}
            return out
        if kind == "bug-pattern":
            comp = self.registry["compositions"]["bug-pattern-composed"]
            layer = comp["serving_layer"]
            ans = self.waking_dream().answer(task.get("code", ""))
            base = comp["evidence"].get("fresh_sealed_baseline") or {}
            fired = ans["mechanism"] == "verified"
            return {
                "ok": True, "output": ans["answer"],
                "specialist": "bug-pattern-composed",
                "evidence": (
                    f"waking-dream verified {ans['verified_cls']} "
                    f"by execution" if fired else
                    "no candidate verified; raw composer verdict "
                    "stands (flagged unverified)"),
                "provenance": {
                    "composition": comp["name"],
                    "members": len(comp["members"]),
                    "serving_layer": layer["name"],
                    "verification_fired": fired,
                    "verified_cls": ans["verified_cls"],
                    "mechanism": ans["mechanism"],
                    "composer_verdict": ans["composer"],
                    "say": ({"status": "adopted",
                             "sharpness_beta":
                                 self._say.get("sharpness_beta"),
                             "fitted_on": self._say.get("fitted_on")}
                            if self._say else {"status": "none"}),
                    "sealed_layer_acc": layer["sealed_acc"],
                    "sealed_raw_composition_acc": base.get("acc"),
                    "bar": comp["evidence"].get("bar")}}
        if kind == "coordinate":
            return {"ok": False, "output": None,
                    "gap": "tier1-backend-required",
                    "evidence": ("the coordinator winner is registered "
                                 "for provenance; serving it requires "
                                 "the LM backend (team.Hive + HF "
                                 "engine), which is outside this "
                                 "Tier-0 entry point"),
                    "growth_move": "route through team.Hive"}
        return {"ok": False, "output": None,
                "gap": f"unknown task kind {kind!r}",
                "growth_move": "decompose the job, then route"}
