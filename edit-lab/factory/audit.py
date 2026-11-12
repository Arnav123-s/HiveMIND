"""Serve-time audit (arch. section 5; final-product item 3).

Verifies that what would serve IS what the registry says was
adopted — two levels:

  * verify_files (the serve-time fast path): every registered
    artifact file exists and its sha256 matches the registry. Any
    mismatch is a hard failure: the serving path fails closed
    rather than serve an unverified artifact.
  * full_audit (the acceptance path): file checks PLUS score
    re-measurement — every serving specialist is re-run on its
    same-distribution held-out set and must reproduce its recorded
    adoption score; the ternary member is re-measured likewise;
    the bug composition is re-measured on the SEALED held-out v2
    set and must reproduce its recorded baseline exactly
    (deterministic inference — a drift here means the serving
    members changed, which is precisely what the audit exists to
    catch). The Tier-1 coordinator is hash-checked only; its
    pristine test is a sealed record, not an audit leg.

    python3 -m factory.audit            # full audit, exit 0/1
    python3 -m factory.audit --files    # hashes only
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

LAB_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(LAB_ROOT / "coding"))
sys.path.insert(0, str(LAB_ROOT))

from .registry import load_registry, sha256_file  # noqa: E402

TOL = 0.0011   # float dust on recorded 4-decimal scores; inference is
               # deterministic, so anything larger is a real drift


def _entries(reg: Dict[str, Any]):
    """(label, relpath, sha256) for every hashed file in the book."""
    for job, s in reg.get("specialists", {}).items():
        yield f"{job}:serving", s["serving"]["path"], s["serving"]["sha256"]
        for fb in s.get("fallbacks", []):
            yield f"{job}:fallback", fb["path"], fb["sha256"]
        for sh in s.get("shadow", []):
            yield f"{job}:shadow", sh["path"], sh["sha256"]
        for sub in s.get("substrates", []):
            yield f"{job}:substrate", sub["path"], sub["sha256"]
        # ternary payloads (assembly 2026-11-10): the npz bytes are
        # the served artifact — hashed like any record file.
        for e in [s["serving"]] + list(s.get("fallbacks", [])) \
                + list(s.get("shadow", [])) \
                + list(s.get("substrates", [])):
            pl = e.get("payload")
            if pl:
                yield (f"{job}:payload:{e['name']}",
                       pl["path"], pl["sha256"])
    for cname, comp in reg.get("compositions", {}).items():
        for m in comp.get("members", []):
            yield f"{cname}:member", m["path"], m["sha256"]
        layer = comp.get("serving_layer")
        if layer:
            yield (f"{cname}:serving-layer", layer["path"],
                   layer["sha256"])
        cfg = comp.get("composer_config", {})
        if cfg:
            yield f"{cname}:config", cfg["path"], cfg["sha256"]
        sealed = comp.get("evidence", {}).get(
            "fresh_sealed_baseline") or {}
        if sealed.get("sealed_file"):
            yield "bug-pattern:sealed-set", sealed["sealed_file"], None
    for tname, t in reg.get("tier1", {}).items():
        for fname, h in t.get("files", {}).items():
            yield f"{tname}:file", f"{t['artifact_dir']}/{fname}", h


def verify_files(reg: Dict[str, Any],
                 lab_root: Path = LAB_ROOT) -> List[Dict[str, Any]]:
    """Failures only; an empty list means every registered artifact
    on disk is byte-identical to its adoption record."""
    failures: List[Dict[str, Any]] = []
    for label, rel, want in _entries(reg):
        p = Path(lab_root) / rel
        if not p.exists():
            failures.append({"artifact": label, "path": rel,
                             "failure": "missing file"})
            continue
        if want is None:
            # the sealed set carries its own internal seal
            from . import bug_heldout_v2 as bh
            try:
                bh.load_sealed()
            except Exception as exc:  # noqa: BLE001
                failures.append({"artifact": label, "path": rel,
                                 "failure": f"seal broken: {exc}"})
            continue
        got = sha256_file(p)
        if got != want:
            failures.append({"artifact": label, "path": rel,
                             "failure": "sha256 mismatch",
                             "registry_sha256": want, "disk_sha256": got})
    return failures


def _version_key(job: str, name: str) -> int:
    if name == job:
        return 1
    tail = name[len(job) + 2:] if name.startswith(job + "-v") else "0"
    return int(tail) if tail.isdigit() else 0


def verify_rule(reg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The standing serving rule, re-derived: for every job, the
    registry's serving/fallback/shadow assignment must equal what
    the rule produces from the battery evidence. A registry that
    serves an artifact the battery has not promoted fails here —
    this is the check that keeps a future v3 from being served by
    hand. Failures only; empty means the book obeys the rule."""
    from . import registry as registry_mod
    try:
        evidence = registry_mod._battery_evidence()
    except Exception as exc:  # noqa: BLE001
        return [{"artifact": "serving-rule",
                 "failure": f"battery evidence unreadable: {exc}"}]
    failures: List[Dict[str, Any]] = []
    for job, s in reg.get("specialists", {}).items():
        names = [s["serving"]["name"]] \
            + [f["name"] for f in s.get("fallbacks", [])] \
            + [sh["name"] for sh in s.get("shadow", [])]
        ordered = sorted(names, key=lambda n: _version_key(job, n))
        want_serving, want_fb, want_shadow = \
            registry_mod._apply_serving_rule(
                job, [{"name": n} for n in ordered], evidence)
        got = {"serving": s["serving"]["name"],
               "fallbacks": sorted(f["name"]
                                   for f in s.get("fallbacks", [])),
               "shadow": sorted(sh["name"]
                                for sh in s.get("shadow", []))}
        want = {"serving": want_serving["name"],
                "fallbacks": sorted(f["name"] for f in want_fb),
                "shadow": sorted(sh["name"] for sh in want_shadow)}
        if got != want:
            failures.append({"artifact": f"{job}:serving-rule",
                             "failure": "registry assignment violates "
                                        "the standing serving rule",
                             "registry": got, "rule": want})
    return failures


def full_audit(reg: Dict[str, Any],
               lab_root: Path = LAB_ROOT) -> Dict[str, Any]:
    from swarm import factory as F
    from . import dream
    from .executors import measure, subject_config

    failures = verify_files(reg, lab_root)
    failures += verify_rule(reg)
    score_checks: List[Dict[str, Any]] = []

    def check(label, measured, recorded):
        ok = recorded is not None and abs(measured - recorded) <= TOL
        score_checks.append({"artifact": label, "measured": measured,
                             "recorded": recorded, "ok": ok})
        if not ok:
            failures.append({"artifact": label,
                             "failure": f"score drift: measured "
                                        f"{measured} vs recorded {recorded}"})

    from . import artifacts as artifacts_mod
    for job, s in reg.get("specialists", {}).items():
        cfg = subject_config(job)
        if cfg is None:
            failures.append({"artifact": job,
                             "failure": "no subject config to re-measure with"})
            continue
        held = cfg["held_fn"]()
        rec = json.loads(
            (Path(lab_root) / s["serving"]["path"]).read_text())
        model = artifacts_mod.load_artifact(rec, Path(lab_root))
        check(f"{job}:serving-heldout", measure(model, held)["acc"],
              s["serving"]["heldout_acc"])
        for sub in s.get("substrates", []):
            srec = json.loads(
                (Path(lab_root) / sub["path"]).read_text())
            smodel = artifacts_mod.load_artifact(srec, Path(lab_root))
            check(f"{job}:substrate-heldout",
                  measure(smodel, held)["acc"], sub["heldout_acc"])

    comp = reg.get("compositions", {}).get("bug-pattern-composed")
    if comp:
        from . import bug_heldout_v2 as bh
        sealed = bh.load_sealed()
        reg_bug = dream.load_bug_registry()
        acc, _ = dream.composed_eval(reg_bug, sealed["items"])
        base = comp["evidence"]["fresh_sealed_baseline"]
        check("bug-pattern-composed:sealed-baseline", acc,
              base["acc"] if base else None)
        layer = comp.get("serving_layer")
        if layer:
            # the SERVED path (assembly 2026-11-10): the waking-
            # dream layer over the same members must reproduce its
            # recorded sealed measurement.
            wd_dir = str(Path(lab_root) / "waking-dream")
            if wd_dir not in sys.path:
                sys.path.insert(0, wd_dir)
            import waking_dream as wd_mod
            res = wd_mod.evaluate(wd_mod.WakingDream(),
                                  sealed["items"])
            check("bug-pattern-composed:serving-layer-sealed",
                  res["acc"], layer["sealed_acc"])

    return {"ok": not failures, "failures": failures,
            "score_checks": score_checks,
            "file_checks": len(list(_entries(reg))) - len(failures)}


def main() -> int:
    ap = argparse.ArgumentParser(description="Factory serve-time audit")
    ap.add_argument("--files", action="store_true",
                    help="hash checks only (the serve-time fast path)")
    args = ap.parse_args()
    reg = load_registry()
    if args.files:
        failures = verify_files(reg)
        print(f"file audit: {'OK' if not failures else 'FAILED'} "
              f"({len(failures)} failure(s))")
        for f in failures:
            print(f"  FAIL {f}")
        return 0 if not failures else 1
    res = full_audit(reg)
    for c in res["score_checks"]:
        print(f"  {'ok ' if c['ok'] else 'FAIL'} {c['artifact']}: "
              f"measured {c['measured']} vs recorded {c['recorded']}")
    print(f"full audit: {'OK' if res['ok'] else 'FAILED'} "
          f"({len(res['failures'])} failure(s))")
    for f in res["failures"]:
        print(f"  FAIL {f}")
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
