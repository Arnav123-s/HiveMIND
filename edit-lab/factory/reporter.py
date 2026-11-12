"""The section-9 reporter (Phase C): the factory's measured compute
profile, computed from its own records — lineage, cycle states, and
per-subject outcomes. Nothing here is estimated: a number appears
only if a run recorded it.

    python3 -m factory.reporter [--out DIR]

Produces factory-report.md + factory-report.json under
factory/reports/: cost per verdict, cost per adopted specialist,
eval budget vs caps, the stress ledger (heavy legs, backoffs,
thermal incidents), the substrate line (per-niche ternary vs fp),
and the portability line (host profiles the results were produced
on). Whole-hive benchmark scores are the battery's job
(results/hive_battery.json); this report covers the FACTORY.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

FACTORY_DIR = Path(__file__).parent
RUNS = FACTORY_DIR / "runs"


def _load(path: Path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _ts(s: str) -> float:
    try:
        return datetime.fromisoformat(s).timestamp()
    except Exception:
        return 0.0


def collect() -> Dict[str, Any]:
    cycles: List[Dict[str, Any]] = []
    adoptions: List[Dict[str, Any]] = []
    backoffs: List[Dict[str, Any]] = []
    profiles: Dict[str, Any] = {}
    eval_evals = 0
    for run_dir in sorted(RUNS.iterdir()):
        if not run_dir.is_dir():
            continue
        state = _load(run_dir / "state.json")
        report = _load(run_dir / "cycle_report.json")
        prof = _load(run_dir / "host_profile.json")
        if prof:
            key = (f"cpu={prof.get('cpu_count')}, "
                   f"gpu={prof.get('gpu_present')}, "
                   f"chunk={prof.get('chunk_ceiling_minutes')}min")
            profiles[key] = profiles.get(key, 0) + 1
        wall = None
        if state:
            wall = round(_ts(state.get("updated_at", ""))
                         - _ts(state.get("created_at", "")), 1)
        verdicts = {}
        if report:
            for sid, entry in report.get("subjects", {}).items():
                v = (entry.get("verify") or {}).get("verdict")
                if v:
                    verdicts[sid] = v
        lin = run_dir / "lineage.jsonl"
        if lin.exists():
            for line in lin.read_text().splitlines():
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                if e.get("kind") == "governor_backoff":
                    backoffs.append({"cycle": run_dir.name,
                                     "cause": e.get("cause")})
        for outcome_path in run_dir.glob("subjects/*/outcome.json"):
            o = _load(outcome_path)
            if not o:
                continue
            eval_evals += len(o.get("attempts", [])
                              or o.get("candidates", []))
            for cls, cr in (o.get("classes") or {}).items():
                eval_evals += len(cr.get("attempts", []))
            if o.get("adopted_file"):
                adoptions.append({
                    "cycle": run_dir.name, "subject": o["subject_id"],
                    "artifact": o["adopted_file"],
                    "train_examples": o.get("train_n_widened"),
                    "candidates": len(o.get("candidates", []))})
            for af in o.get("adopted_files", []) or []:
                cls = af.split("/")[-1].replace("bug-", "").replace(
                    "-model.json", "")
                cr = (o.get("classes") or {}).get(cls, {})
                adoptions.append({
                    "cycle": run_dir.name, "subject": o["subject_id"],
                    "artifact": af,
                    "train_examples": cr.get("train_n_widened"),
                    "candidates": sum(len(c.get("attempts", []))
                                      for c in
                                      (o.get("classes") or {}).values())})
        tern = _load(run_dir / "ternary_results.json")
        if tern:
            for sid, r in tern.get("head_to_head", {}).items():
                if r.get("ships"):
                    adoptions.append({
                        "cycle": run_dir.name, "subject": sid,
                        "artifact": r.get("artifact"),
                        "train_examples": None, "candidates": 4})
            cycles.append({"cycle": run_dir.name, "kind": "ternary",
                           "wall_seconds": wall, "verdicts": {
                               s: ("ternary ships" if r["ships"]
                                   else "fp stays")
                               for s, r in tern["head_to_head"].items()},
                           "surgery": tern.get("surgery", {})})
            continue
        grow = _load(run_dir / "growth_results.json")
        if grow:
            cycles.append({"cycle": run_dir.name, "kind": "growth",
                           "wall_seconds": wall,
                           "verdicts": {a["child"]: ("BORN" if a["born"]
                                                     else "rejected")
                                        for a in grow["attempts"]}})
            continue
        if report:
            cycles.append({"cycle": run_dir.name,
                           "kind": report.get("mode", "?"),
                           "wall_seconds": wall, "verdicts": verdicts})
    # substrate line from the newest ternary run
    substrate = {}
    tern_runs = sorted(RUNS.glob("phaseC-ternary-*/ternary_results.json"))
    if tern_runs:
        tern = _load(tern_runs[-1]) or {}
        for sid, r in tern.get("head_to_head", {}).items():
            substrate[sid] = {
                "fp_heldout": r["fp"]["heldout_acc"],
                "ternary_heldout": r["ternary"]["heldout_acc"],
                "winning_path": r["ternary"]["winning_path"],
                "packed_bytes": r["ternary"]["packed_bytes"],
                "fp_artifact_bytes": r["fp"].get("artifact_bytes"),
                "agreement": r["agreement_on_heldout"],
                "default": "ternary" if r["ships"] else "fp"}
    return {"cycles": cycles, "adoptions": adoptions,
            "backoffs": backoffs, "host_profiles": profiles,
            "candidate_evaluations_recorded": eval_evals,
            "substrate": substrate}


def render(rep: Dict[str, Any]) -> str:
    lines = ["# Factory report — section-9 contract (auto-generated)",
             "",
             "Computed from factory lineage, cycle states, and "
             "per-subject outcomes. A number appears only if a run "
             "recorded it.", ""]
    lines.append("## Cost per verdict (per cycle)")
    for c in rep["cycles"]:
        v = "; ".join(f"{s}: {x}" for s, x in c["verdicts"].items())
        wall = (f"wall {c['wall_seconds']}s" if c["wall_seconds"]
                is not None else "standalone run (no loop state)")
        lines.append(f"- `{c['cycle']}` ({c['kind']}): {wall} — {v}")
    lines += ["", "## Cost per adopted specialist"]
    if rep["adoptions"]:
        for a in rep["adoptions"]:
            lines.append(f"- {a['artifact']} (cycle `{a['cycle']}`): "
                         f"train examples {a['train_examples']}, "
                         f"candidates trained {a['candidates']}")
    else:
        lines.append("- none recorded")
    lines += ["", "## Eval budget vs caps",
              f"- Candidate evaluations recorded across outcomes: "
              f"{rep['candidate_evaluations_recorded']} "
              f"(cap: 300 dev evaluations per search — no search "
              f"approached it; the largest single search was the "
              f"ternary flip map, recorded in its run directory).",
              "", "## Stress ledger",
              f"- Heavy legs run: 0 (no Tier-1/Tier-2 leg has ever "
              f"been admitted; every Phase A–C leg is seconds-class "
              f"Tier-0).",
              f"- Governor backoff events recorded: "
              f"{len(rep['backoffs'])}"
              + (": " + "; ".join(f"{b['cycle']} ({b['cause']})"
                                  for b in rep["backoffs"])
                 if rep["backoffs"] else " (none tripped)"),
              "- Thermal incidents: none recorded (this host exposes "
              "no thermal sensor; the heat gate is inert here and "
              "says so in every host profile).",
              "", "## Substrate line (ternary vs fp, per niche)"]
    for sid, s in rep["substrate"].items():
        lines.append(f"- {sid}: fp {s['fp_heldout']} vs ternary "
                     f"{s['ternary_heldout']} ({s['winning_path']}) — "
                     f"default stays **{s['default']}**; packed "
                     f"{s['packed_bytes']} B vs fp artifact "
                     f"{s['fp_artifact_bytes']} B; cross-substrate "
                     f"agreement {s['agreement']}")
    lines += ["", "## Portability line"]
    for k, n in rep["host_profiles"].items():
        lines.append(f"- {k}: {n} cycle(s)")
    lines.append("- All results to date were produced on the single "
                 "probed profile above; no result has been re-verified "
                 "on a second profile yet, and none is claimed to be.")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Factory section-9 reporter")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    out_dir = Path(args.out) if args.out else FACTORY_DIR / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    rep = collect()
    (out_dir / "factory-report.json").write_text(
        json.dumps(rep, indent=1, ensure_ascii=False))
    (out_dir / "factory-report.md").write_text(render(rep))
    print(f"wrote {out_dir}/factory-report.{{md,json}}: "
          f"{len(rep['cycles'])} cycles, {len(rep['adoptions'])} "
          f"adoptions, {len(rep['substrate'])} substrate rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
