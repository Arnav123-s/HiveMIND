"""Spawn mining over the factory's serving history (Fable-study
Build 3) — Muse's work, Muse's side.

Fable's principle (study sections 2.6 + 2.2): the system notices
its own micro-jobs and grows where it measurably fails; nothing
is staffed on a hunch. This module mines the factory's recorded
serving history for (a) decision sites — repeated calls whose
answers take a few fixed values, the spawn-trainer signal — and
(b) failure sites — recurring shapes serving gets wrong that no
current niche covers.

Sources (all recorded history; the log itself is never a judging
surface):
  * factory/serve_log.jsonl — the append-only decision log added
    to serve.py by this build (young: it starts accumulating
    today, and the report says so);
  * results/hive_battery.json (2026-11-10) and
    results/hive_battery_acceptance.json — per-niche battery
    scores and the recorded wrongs (confusion pairs);
  * results/bug_heldout_v2_*.json — the sealed raw-composition
    trajectory (11+ measurements): per-class recalls over time;
  * growth/growth-cycle-*.json — targets attacked per cycle,
    births and rollbacks: a target attacked repeatedly is a
    failure shape the factory already knows it has;
  * the dev pool (factory/say_dev.py) — per-seat and routed
    accuracy per class/slice on DEV material, used to locate a
    slice no current seat covers (the sealed set is never
    inspected to design a candidate; it only judges).

Output: factory/reports/spawn-mining-<date>.json + .md with the
ranked failure shapes and candidate niches, each candidate with
its evidence and disposition. Candidates are proposals — a
candidate becomes a specialist only through the standard gates
(dual held slices vs its parent, the battery, the audit).
"""
from __future__ import annotations

import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List

LAB_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(LAB_ROOT / "coding"))
sys.path.insert(0, str(LAB_ROOT))

FACTORY = Path(__file__).parent
RESULTS = LAB_ROOT / "results"
GROWTH = LAB_ROOT / "growth"
REPORTS = FACTORY / "reports"


def _load(path: Path):
    try:
        return json.loads(path.read_text())
    except Exception:  # noqa: BLE001
        return None


# ------------------------------------------------------------ sources
def mine_serve_log() -> Dict[str, Any]:
    path = FACTORY / "serve_log.jsonl"
    rows = []
    if path.exists():
        for line in path.read_text().splitlines():
            try:
                rows.append(json.loads(line))
            except Exception:  # noqa: BLE001
                continue
    by_kind = Counter(r.get("kind") for r in rows)
    bug = [r for r in rows if r.get("kind") == "bug-pattern"]
    gaps = Counter(r.get("gap") for r in rows if r.get("gap"))
    disagreements = [r for r in bug
                     if r.get("composer_verdict")
                     and r.get("output") != r.get("composer_verdict")]
    return {"n": len(rows), "by_kind": dict(by_kind),
            "gap_kinds": dict(gaps),
            "bug_pattern": {
                "n": len(bug),
                "mechanisms": dict(Counter(
                    r.get("mechanism") for r in bug)),
                "composer_overruled": len(disagreements),
                "note": ("the waking layer overruling the raw "
                         "composer is a composer failure site, "
                         "counted per call")}}


def mine_batteries() -> Dict[str, Any]:
    out: Dict[str, Any] = {"eras": {}, "confusions": Counter()}
    for name, era in (("hive_battery.json", "2026-11-10"),
                      ("hive_battery_acceptance.json", "current")):
        doc = _load(RESULTS / name)
        if not doc:
            continue
        res = doc.get("results", doc)
        scores = {}
        for task, entry in res.items():
            if isinstance(entry, dict) and "score" in entry:
                scores[task] = entry["score"]
                detail = entry.get("detail") or ""
                for want, got in re.findall(
                        r'"want":\s*"([^"]+)",\s*"got":\s*"([^"]+)"',
                        detail):
                    if want != got:
                        out["confusions"][(task, want, got)] += 1
        out["eras"][era] = scores
    out["confusions"] = {f"{t}: {w} -> {g}": n
                         for (t, w, g), n in
                         out["confusions"].most_common()}
    return out


def mine_sealed_trajectory() -> Dict[str, Any]:
    files = sorted(RESULTS.glob("bug_heldout_v2_*.json"))
    traj = []
    for f in files:
        d = _load(f)
        if d and (d.get("per_class_recall") or d.get("recalls")):
            traj.append({"file": f.name,
                         "acc": d.get("acc") or d.get("composed_acc"),
                         "recalls": d.get("per_class_recall")
                         or d.get("recalls")})
    per_class: Dict[str, List[float]] = defaultdict(list)
    for t in traj:
        for c, r in t["recalls"].items():
            per_class[c].append(r)
    summary = {c: {"n_meas": len(v), "mean": round(sum(v) / len(v), 4),
                   "last": v[-1], "min": min(v), "max": max(v)}
               for c, v in per_class.items()}
    return {"measurements": len(traj), "per_class": summary}


def mine_growth_targets() -> Dict[str, Any]:
    targets = Counter()
    cycles = []
    for f in sorted(GROWTH.glob("growth-cycle-*.json")):
        d = _load(f)
        if not d:
            continue
        for t in d.get("targets", []):
            targets[t] += 1
        cycles.append({"cycle": d.get("cycle_id"),
                       "targets": d.get("targets"),
                       "rolled_back": bool(d.get("rolled_back")),
                       "next_attack": d.get("next_attack")})
    return {"target_frequency": dict(targets.most_common()),
            "cycles": cycles}


def mine_dev_slices() -> Dict[str, Any]:
    """Per-class routed accuracy and per-slice routed accuracy on
    the DEV pool, plus each seat's binary accuracy on its class's
    dev items — locates slices where the routed rule fails and no
    seat is strong."""
    from swarm import composers as C
    from swarm.decomposers import slice_of
    from . import learned_say as S
    from . import say_dev
    from .run_battery import _bug_reg
    from .serve import ServingHive
    hive = ServingHive.load()
    reg = _bug_reg(hive)
    seats = S.seats_of(list(reg))
    base = C.load_config()
    dev = say_dev.load_dev_pool()["items"]
    per_class: Dict[str, Any] = {}
    slice_rows: Dict[str, Dict[str, List[int]]] = defaultdict(
        lambda: defaultdict(lambda: [0, 0]))
    for cls in C.DEFECT_CLASSES:
        items = [it for it in dev if it["label"] == cls]
        others = [it for it in dev if it["label"] != cls]
        routed_right = 0
        for it in dev:
            got = S.verdict(C.class_margins(reg, it["text"], base),
                            base.get("thresholds", {}))
            sl = slice_of(cls, it["text"]) if it["label"] == cls \
                else None
            if it["label"] == cls:
                ok = got == cls
                routed_right += ok
                slice_rows[cls][sl][1] += 1
                slice_rows[cls][sl][0] += ok
        seat_acc = {}
        for nm in seats.get(cls, []):
            right = 0
            for it in items + others:
                m = C._model_margin(reg[nm], it["text"], cls)
                pred = cls if (m is not None and m > 0) else "other"
                if pred == (cls if it["label"] == cls else "other"):
                    right += 1
            seat_acc[nm] = round(right / (len(items) + len(others)), 4) \
                if items or others else None
        per_class[cls] = {
            "dev_items": len(items),
            "routed_recall": round(routed_right / len(items), 4)
            if items else None,
            "seat_binary_acc": seat_acc,
            "slices": {sl: {"right": v[0], "n": v[1],
                            "recall": round(v[0] / v[1], 4) if v[1]
                            else None}
                       for sl, v in sorted(slice_rows[cls].items())}}
    return per_class


def mine_registry_gaps() -> Dict[str, Any]:
    reg = _load(FACTORY / "registry.json") or {}
    return {
        "classify_jobs": sorted(reg.get("specialists", {})),
        "compositions": sorted(reg.get("compositions", {})),
        "fixed_answer_sites": [
            {"kind": "coordinate",
             "answer": "gap: tier1-backend-required (fixed)",
             "disposition": ("noticed decision site — every "
                             "coordinate call takes the same fixed "
                             "answer; NOT Tier-0 staffable (needs "
                             "the LM backend), recorded not built")},
            {"kind": "unknown kind / unregistered job",
             "answer": "gap with growth_move (fixed)",
             "disposition": ("fail-closed routing answer; the "
                             "growth_move names the intake path")}]}


# ------------------------------------------------------------ report
def build_report() -> Dict[str, Any]:
    return {"built_at": time.strftime("%Y-%m-%d %H:%M %Z"),
            "built_by": "factory/spawn_mining.py (Muse's work, "
                        "Muse's side)",
            "serve_log": mine_serve_log(),
            "batteries": mine_batteries(),
            "sealed_trajectory_raw": mine_sealed_trajectory(),
            "growth_targets": mine_growth_targets(),
            "dev_slices": mine_dev_slices(),
            "registry_gaps": mine_registry_gaps()}


def main() -> int:
    rep = build_report()
    REPORTS.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%d")
    out = REPORTS / f"spawn-mining-{stamp}.json"
    out.write_text(json.dumps(rep, indent=1, ensure_ascii=False))
    print(f"wrote {out}")
    print(json.dumps({k: rep[k] for k in
                      ("serve_log", "sealed_trajectory_raw")},
                     indent=1)[:1200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
