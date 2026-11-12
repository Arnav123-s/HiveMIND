"""Phase C ternary head-to-head + one flip-map surgery trial.

Usage (from ~/workspace/edit-lab):
    python3 -m factory.run_ternary [--cycle-id ID]

For every adopted Tier-0 specialist: fp vs ternary on the same
splits (held-out score, footprint, latency, cross-substrate
agreement). Ternary artifacts are saved only where the gate passes
(ternary held-out >= fp held-out). Then one surgery trial: a
flip-ablation map on the smallest subject's ternary pack indicts
weights on TRAINING-side probes; the indicted flips are applied and
judged on held-out — adopted only if held-out improves, reverted
and recorded either way (the map is evidence, not a verdict).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from factory import ternary  # noqa: E402
from factory.executors import subject_config  # noqa: E402
from factory.lineage import LineageLog  # noqa: E402

FACTORY_DIR = Path(__file__).parent
SUBJECTS = ["error-class-model", "contract-judgment-model",
            "gap-move-model", "secret-line-model", "commit-type-model"]


def _splits(subject_id):
    if subject_id == "error-class-model":
        sys.path.insert(0, str(FACTORY_DIR.parent / "coding"))
        from swarm import phase3 as P3
        return P3.gen_error_texts()
    cfg = subject_config(subject_id)
    return cfg["train_fn"](), cfg["held_fn"]()


def main() -> int:
    ap = argparse.ArgumentParser(description="Factory Phase C — ternary")
    ap.add_argument("--cycle-id", default=None)
    args = ap.parse_args()
    cycle_id = args.cycle_id or time.strftime("phaseC-ternary-%Y%m%d-%H%M%S")
    run_dir = FACTORY_DIR / "runs" / cycle_id
    run_dir.mkdir(parents=True, exist_ok=True)
    lineage = LineageLog(run_dir / "lineage.jsonl")
    factory_lineage = LineageLog(FACTORY_DIR / "lineage.jsonl")
    lineage.append("ternary_start", cycle_id=cycle_id, subjects=SUBJECTS)

    results = {}
    for sid in SUBJECTS:
        train, held = _splits(sid)
        r = ternary.head_to_head(sid, train, held)
        results[sid] = r
        lineage.append("ternary_head_to_head", cycle_id=cycle_id, subject=sid,
                       fp_heldout=r["fp"]["heldout_acc"],
                       ternary_heldout=r["ternary"]["heldout_acc"],
                       ships=r["ships"], path=r["ternary"]["winning_path"],
                       agreement=r["agreement_on_heldout"],
                       packed_bytes=r["ternary"]["packed_bytes"],
                       fp_params=r["fp"]["params"])
        print(f"[h2h] {sid}: fp {r['fp']['heldout_acc']} vs ternary "
              f"{r['ternary']['heldout_acc']} ({r['ternary']['winning_path']}) "
              f"-> {'SHIPS' if r['ships'] else 'fp stays'} "
              f"(packed {r['ternary']['packed_bytes']} B, "
              f"agreement {r['agreement_on_heldout']})")

    # ---- flip-map surgery trial -------------------------------------
    # Subject: secret-line — its ternary pack is close to its fp
    # incumbent and its training probes are not saturated, so a flip
    # map has something to indict. The map is built on TRAINING-side
    # probes only; held-out judges the surgery once, after.
    surgery = {}
    sid = "secret-line-model"
    train, held = _splits(sid)
    from factory.executors import load_incumbent, measure
    fp = load_incumbent(sid)
    pack = ternary.quantize(fp, train)
    probes = train[:64]
    base, entries = ternary.flip_map(fp, pack, probes)
    indicted = [e for e in entries if e["delta"] > 0]
    surgery = {"subject_id": sid, "probe_n": len(probes),
               "probe_base_acc": base, "weights_mapped": len(entries),
               "indicted_improving_flips": len(indicted),
               "top": entries[:8]}
    if indicted:
        before = measure(ternary.materialize(fp, pack), held)
        cut = [e for e in indicted if e["delta"] >= 0.015]
        new_pack = ternary.apply_flips(fp, pack, cut)
        after = measure(ternary.materialize(fp, new_pack), held)
        surgery.update({
            "flips_applied": len(cut),
            "heldout_before": before["acc"],
            "heldout_after": after["acc"],
            "adopted": after["acc"] > before["acc"],
            "note": "flips selected on training-side probes only; "
                    "held-out judged once, after"})
        if surgery["adopted"]:
            q = ternary.materialize(fp, new_pack)
            q.name = f"{sid}-ternary"
            from swarm import factory as F
            F.save_model(q, {"path": "ternary/ptq+flip-surgery (Phase C)",
                             "heldout_acc": after["acc"],
                             "train_n": len(train), "heldout_n": len(held),
                             "adopted": True, "substrate": "ternary",
                             "ternary_pack": new_pack,
                             "flips_applied": len(cut)},
                         directory=ternary.MODELS_DIR)
    lineage.append("ternary_flip_surgery", cycle_id=cycle_id, **{
        k: v for k, v in surgery.items() if k != "top"})
    print(f"[surgery] {sid} ternary: probe base {base}, "
          f"{len(indicted)} improving flips indicted; "
          f"held-out {surgery.get('heldout_before')} -> "
          f"{surgery.get('heldout_after')} "
          f"({'ADOPTED' if surgery.get('adopted') else 'reverted'})")

    out = {"cycle_id": cycle_id, "head_to_head": results, "surgery": surgery}
    with open(run_dir / "ternary_results.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, ensure_ascii=False)
    factory_lineage.append("phaseC_ternary", cycle_id=cycle_id,
                           run_dir=f"factory/runs/{cycle_id}",
                           ships={s: r["ships"] for s, r in results.items()},
                           surgery_adopted=surgery.get("adopted"))
    print(json.dumps({"cycle_id": cycle_id, "run_dir": str(run_dir)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
