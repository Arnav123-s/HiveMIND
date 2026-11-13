# Muse's work — written by Muse, on Muse's side. Fable's HiveMIND was read read-only; nothing on Fable's side was touched.
"""The product status surface (Arnav's usability test, 2026-11-12):
one read-only snapshot of the serving hive, assembled ONLY from
the factory's real records —

  * the registry (factory/registry.json): what serves, per niche;
  * the newest battery measurement under factory/runs/
    (results/hive_battery_acceptance.json is the fallback) — the
    overall is the mean of the section scores, the same formula
    factory/growth_cycle.py records as battery_overall;
  * the growth records (growth/growth-cycle-*.json and the
    factory/runs/growth-cycle-* run dirs, plus any repair records
    that later touched the last cycle);
  * the newest recorded full audit (growth cycle records and
    repair records carry one);
  * the serve-time gate itself, run live and read-only: the same
    verify_files + verify_rule checks ServingHive.load() fails
    closed on. No model is loaded and nothing is served here.

A missing or unreadable required record raises StatusUnavailable
(fail-closed: no record, no status). A failed serve-time gate is
NOT an exception — it is the status, reported as serving refused.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

LAB_ROOT = Path(__file__).parent.parent

# CLI short name -> registry job, in USAGE.md's order. The sixth
# niche is the bug-pattern composition (registry["compositions"]).
JOB_ORDER = [
    ("secret", "secret-line-model"),
    ("error", "error-class-model"),
    ("commit", "commit-type-model"),
    ("contract", "contract-judgment-model"),
    ("gap", "gap-move-model"),
]
COMPOSITION = "bug-pattern-composed"

_CYCLE_RE = re.compile(r"growth-cycle-(\d+)$")


class StatusUnavailable(Exception):
    """A required record is missing or unreadable: no status."""


def _load_json(path: Path, what: str) -> Dict[str, Any]:
    if not path.exists():
        raise StatusUnavailable(f"{what} record is missing: {path}")
    try:
        doc = json.loads(path.read_text())
    except Exception as exc:  # noqa: BLE001
        raise StatusUnavailable(
            f"{what} record is unreadable: {path} ({exc})")
    if not isinstance(doc, dict):
        raise StatusUnavailable(
            f"{what} record is not a JSON object: {path}")
    return doc


def _battery_overall(doc: Dict[str, Any]) -> Optional[float]:
    """Mean of the battery section scores — growth_cycle.py's
    battery_overall formula. None when the doc carries no scores."""
    scores = [e["score"] for e in (doc.get("results") or {}).values()
              if isinstance(e, dict)
              and isinstance(e.get("score"), (int, float))]
    if not scores:
        return None
    return round(sum(scores) / len(scores), 4)


def _newest_battery(lab_root: Path) -> Dict[str, Any]:
    runs_dir = lab_root / "factory" / "runs"
    cands = []
    if runs_dir.exists():
        for p in sorted(runs_dir.glob("*/battery_after.json")):
            try:
                doc = json.loads(p.read_text())
            except Exception:  # noqa: BLE001
                continue
            overall = _battery_overall(doc)
            if overall is not None:
                cands.append((str(doc.get("started", "")),
                              p.parent.name, doc, overall))
    if cands:
        started, source, doc, overall = max(
            cands, key=lambda c: (c[0], c[1]))
        return {"overall": overall, "source": source,
                "started": started or None,
                "sections": len(doc.get("results") or {})}
    fallback = lab_root / "results" / "hive_battery_acceptance.json"
    if fallback.exists():
        doc = _load_json(fallback, "battery")
        overall = _battery_overall(doc)
        if overall is not None:
            return {"overall": overall,
                    "source": "results/hive_battery_acceptance.json",
                    "started": doc.get("started"),
                    "sections": len(doc.get("results") or {})}
    raise StatusUnavailable(
        "battery record is missing: no factory/runs/*/battery_after.json "
        "and no results/hive_battery_acceptance.json")


def _audit_state(lab_root: Path) -> Dict[str, Any]:
    cands = []
    growth_dir = lab_root / "growth"
    if growth_dir.exists():
        for p in sorted(growth_dir.glob("growth-cycle-*.json")):
            try:
                doc = json.loads(p.read_text())
            except Exception:  # noqa: BLE001
                continue
            if isinstance(doc.get("audit"), dict):
                cands.append((str(doc.get("date", "")), p.stem,
                              doc["audit"]))
    runs_dir = lab_root / "factory" / "runs"
    if runs_dir.exists():
        for p in sorted(runs_dir.glob("*/repair-result.json")):
            try:
                doc = json.loads(p.read_text())
            except Exception:  # noqa: BLE001
                continue
            if isinstance(doc.get("audit"), dict):
                cands.append((str(doc.get("date", "")),
                              doc.get("repair_id") or p.parent.name,
                              doc["audit"]))
    if not cands:
        raise StatusUnavailable(
            "audit record is missing: no growth cycle or repair "
            "record carries a full-audit result")
    date, source, audit = max(cands, key=lambda c: (c[0], c[1]))
    return {"ok": bool(audit.get("ok")),
            "failures": len(audit.get("failures") or []),
            "date": date or None, "source": source}


def _growth(lab_root: Path) -> Dict[str, Any]:
    growth_dir = lab_root / "growth"
    runs_dir = lab_root / "factory" / "runs"
    cycles: Dict[int, Dict[str, Any]] = {}
    if growth_dir.exists():
        for p in growth_dir.glob("growth-cycle-*.json"):
            m = _CYCLE_RE.match(p.stem)
            if m:
                cycles.setdefault(int(m.group(1)), {})["record"] = p
    if runs_dir.exists():
        for d in runs_dir.glob("growth-cycle-*"):
            m = _CYCLE_RE.match(d.name)
            if m and d.is_dir():
                cycles.setdefault(int(m.group(1)), {})["run_dir"] = d
    if not cycles:
        raise StatusUnavailable(
            "growth records are missing: no growth/growth-cycle-*.json "
            "and no factory/runs/growth-cycle-* run dirs")
    last_no = max(cycles)
    cycle_id = f"growth-cycle-{last_no:03d}"
    entry = cycles[last_no]
    outcome: Dict[str, Any] = {"cycle_id": cycle_id}
    if "record" in entry:
        doc = _load_json(entry["record"], "growth cycle")
        outcome["battery_before"] = doc.get("battery_overall_before")
        outcome["battery_after"] = doc.get("battery_overall_after")
        outcome["rolled_back"] = bool(doc.get("rolled_back"))
        outcome["births"] = [a.get("child")
                             for a in doc.get("attempts") or []
                             if a.get("born")]
        audit = doc.get("audit")
        outcome["audit_ok"] = (bool(audit.get("ok"))
                               if isinstance(audit, dict) else None)
        outcome["rollback_reason"] = doc.get("rollback_reason")
    else:
        run_dir = entry["run_dir"]
        for tag in ("before", "after"):
            p = run_dir / f"battery_{tag}.json"
            if p.exists():
                outcome[f"battery_{tag}"] = _battery_overall(
                    _load_json(p, "growth cycle battery"))
        births_dir = run_dir / "births"
        outcome["births"] = (
            sorted(d.name for d in births_dir.iterdir() if d.is_dir())
            if births_dir.exists() else [])
        outcome["rolled_back"] = None
        outcome["audit_ok"] = None
    outcome["alert"] = (growth_dir / f"ALERT-{cycle_id}.md").exists()
    # Repairs that later touched THIS cycle (their run-dir names
    # carry the cycle token, e.g. repair-cycle007-2026-11-12b).
    token = f"cycle{last_no:03d}"
    repairs = []
    if runs_dir.exists():
        for p in sorted(runs_dir.glob("*/repair-result.json")):
            if token not in p.parent.name:
                continue
            try:
                doc = json.loads(p.read_text())
            except Exception:  # noqa: BLE001
                continue
            audit = doc.get("audit")
            repairs.append({
                "repair_id": doc.get("repair_id") or p.parent.name,
                "date": str(doc.get("date", "")),
                "battery_overall_after":
                    doc.get("battery_overall_after"),
                "audit_ok": (bool(audit.get("ok"))
                             if isinstance(audit, dict) else None)})
    if repairs:
        outcome["repair"] = max(repairs,
                                 key=lambda r: (r["date"], r["repair_id"]))
    return {"count": len(cycles), "last": outcome}


def _niches(reg: Dict[str, Any]) -> List[Dict[str, Any]]:
    specialists = reg.get("specialists") or {}
    out: List[Dict[str, Any]] = []
    for short, job in JOB_ORDER:
        s = specialists.get(job)
        if s is None:
            raise StatusUnavailable(
                f"registry record is missing the {job} niche")
        sv = s["serving"]
        out.append({
            "short": short, "job": job, "niche": s.get("niche"),
            "kind": "specialist", "serving": sv["name"],
            "substrate": sv.get("substrate"),
            "heldout_acc": sv.get("heldout_acc"),
            "battery_acc": sv.get("battery_acc"),
            "fallbacks": len(s.get("fallbacks") or []),
            "shadow": [sh["name"] for sh in s.get("shadow") or []],
            "substrates": len(s.get("substrates") or [])})
    comp = (reg.get("compositions") or {}).get(COMPOSITION)
    if comp is None:
        raise StatusUnavailable(
            "registry record is missing the bug-pattern composition")
    layer = comp.get("serving_layer") or {}
    sealed = (comp.get("evidence") or {}).get(
        "fresh_sealed_baseline") or {}
    out.append({
        "short": "bug", "job": COMPOSITION,
        "niche": comp.get("niche"), "kind": "composition",
        "serving": comp["name"],
        "members": len(comp.get("members") or []),
        "layer": layer.get("name"),
        "sealed_acc": layer.get("sealed_acc"),
        "raw_composed_acc": sealed.get("acc")})
    return out


def collect_status(lab_root: Path = LAB_ROOT) -> Dict[str, Any]:
    """Assemble the status dict from the factory's records.
    Raises StatusUnavailable when a required record is missing."""
    lab_root = Path(lab_root)
    reg = _load_json(lab_root / "factory" / "registry.json",
                     "registry")
    if not reg.get("specialists"):
        raise StatusUnavailable(
            "registry record carries no specialists: "
            "factory/registry.json")
    niches = _niches(reg)
    battery = _newest_battery(lab_root)
    growth = _growth(lab_root)
    audit = _audit_state(lab_root)
    # The serve-time gate, live and read-only: the exact checks
    # ServingHive.load() refuses on. A failure here is reported,
    # not raised — refused serving IS a status.
    from . import audit as audit_mod
    failures = audit_mod.verify_files(reg, lab_root)
    failures += audit_mod.verify_rule(reg)
    return {"niches": niches, "battery": battery, "growth": growth,
            "audit": audit,
            "serving": {"healthy": not failures,
                        "failures": failures}}


def _fmt_acc(v: Any) -> str:
    return str(v) if v is not None else "?"


def render(st: Dict[str, Any]) -> str:
    lines = ["HIVE STATUS — Muse's side"]
    sv = st["serving"]
    if sv["healthy"]:
        lines.append(
            "serving:  HEALTHY — the serve-time audit passes (every "
            "registered artifact matches its adoption record)")
    else:
        f0 = sv["failures"][0]
        lines.append(
            f"serving:  REFUSED — serve-time audit failed "
            f"({len(sv['failures'])} mismatch(es)); first: "
            f"{f0.get('artifact')}: {f0.get('failure')}")
    b = st["battery"]
    lines.append(
        f"battery:  {_fmt_acc(b['overall'])} overall across "
        f"{b['sections']} served sections (latest measurement: "
        f"{b['source']}, {b['started']})")
    lines.append("niches:")
    for n in st["niches"]:
        if n["kind"] == "specialist":
            extra = f" · fallbacks {n['fallbacks']}"
            if n["substrates"]:
                extra += f" · substrate alternates {n['substrates']}"
            if n["shadow"]:
                extra += (f" · shadow {len(n['shadow'])} "
                          f"(audited, never served)")
            lines.append(
                f"  {n['short']:<9} {n['niche'] or '':<10} "
                f"{n['serving']} · {n['substrate']} · held-out "
                f"{_fmt_acc(n['heldout_acc'])} · battery slice "
                f"{_fmt_acc(n['battery_acc'])}{extra}")
        else:
            lines.append(
                f"  {n['short']:<9} {n['niche'] or '':<10} "
                f"{n['serving']} · {n['members']} members + "
                f"{n['layer']} serving layer · sealed "
                f"{_fmt_acc(n['sealed_acc'])} (raw composition "
                f"{_fmt_acc(n['raw_composed_acc'])})")
    g = st["growth"]
    last = g["last"]
    out = (f"growth:   {g['count']} cycles run · last "
           f"{last['cycle_id']}: battery "
           f"{_fmt_acc(last.get('battery_before'))} -> "
           f"{_fmt_acc(last.get('battery_after'))}")
    if last.get("births"):
        out += f" · births {', '.join(last['births'])}"
    if last.get("rolled_back"):
        out += " · ROLLED BACK"
        if last.get("rollback_reason"):
            out += f" — {last['rollback_reason']}"
    if last.get("alert"):
        out += " · alert filed"
    if last.get("audit_ok") is not None:
        out += f" · audit {'OK' if last['audit_ok'] else 'FAILED'}"
    rep = last.get("repair")
    if rep:
        out += (f" · repaired by {rep['repair_id']}: battery "
                f"restored to "
                f"{_fmt_acc(rep.get('battery_overall_after'))}")
        if rep.get("audit_ok") is not None:
            out += f", audit {'OK' if rep['audit_ok'] else 'FAILED'}"
    lines.append(out)
    a = st["audit"]
    lines.append(
        f"audit:    last full audit "
        f"{'OK' if a['ok'] else 'FAILED'} — {a['source']}, "
        f"{a['date']} ({a['failures']} failure(s))")
    return "\n".join(lines)


def main() -> int:
    try:
        st = collect_status()
    except StatusUnavailable as exc:
        print(f"STATUS UNAVAILABLE: {exc}")
        return 3
    print(render(st))
    return 0 if st["serving"]["healthy"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
