"""Build the sealed bug-pattern held-out v2 set and take its
one baseline measurement (final-product item 1).

Usage (from ~/workspace/edit-lab):
    python3 -m factory.run_bug_heldout

Sealing is one-way: if coding/swarm/bug_heldout_v2.json exists it is
loaded and hash-verified, never rebuilt. The baseline evaluates the
CURRENT adopted composition (the factory dream registry — the same
calibrated harness the Phase C cycle used) on the sealed set exactly
once, no tuning, and writes results/bug_heldout_v2_baseline.json.
Re-running after the baseline exists reports the recorded baseline
instead of measuring again.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from factory import bug_heldout_v2 as BH  # noqa: E402
from factory.lineage import LineageLog, now_ts  # noqa: E402

LAB_ROOT = Path(__file__).parent.parent
BASELINE_PATH = LAB_ROOT / "results" / "bug_heldout_v2_baseline.json"
BAR = 0.80   # the phase-4 composition bar, unchanged


def main() -> int:
    if BH.SEALED_PATH.exists():
        rec = BH.load_sealed()
        sealed_now = False
    else:
        rec = BH.build_sealed()
        sealed_now = True
    print(f"sealed set: n={rec['n']} (raw {rec['n_raw']}, "
          f"decontamination dropped {rec['decontamination']['dropped']}), "
          f"per-class {rec['per_class']}, sha256 {rec['sha256'][:16]}…")

    if BASELINE_PATH.exists():
        base = json.loads(BASELINE_PATH.read_text())
        print(f"baseline already recorded ({base['measured_at']}): "
              f"composed {base['composed_acc']} vs bar {base['bar']}")
        return 0

    from factory import dream
    from factory.executors import measure
    items = rec["items"]
    reg = dream.load_bug_registry()
    acc, recall = dream.composed_eval(reg, items)
    binaries = {}
    for cls in ("off-by-one", "wrong-operator", "swapped-operands",
                "mutable-default", "missing-return"):
        rel = dream._relabel(items, cls)
        binaries[cls] = measure(reg[f"bug-{cls}-model"], rel)
    baseline = {
        "sealed_file": "coding/swarm/bug_heldout_v2.json",
        "sealed_sha256": rec["sha256"],
        "measured_at": now_ts(),
        "subject": "bug-pattern-composed (current adopted registry)",
        "n": len(items),
        "composed_acc": acc,
        "per_class_recall": recall,
        "per_class_binary_acc": {c: b["acc"] for c, b in binaries.items()},
        "bar": BAR,
        "clears_bar": acc >= BAR,
        "protocol": ("single measurement pass over the sealed set; no "
                     "threshold tuning, no model selection, no retries; "
                     "the phase-4 confirm (0.8276 on the spent set) is "
                     "the adoption evidence — this baseline is the new "
                     "standing reference for future cycles"),
    }
    tmp = BASELINE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(baseline, indent=1, ensure_ascii=False))
    tmp.replace(BASELINE_PATH)
    LineageLog(LAB_ROOT / "factory" / "lineage.jsonl").append(
        "bug_heldout_v2_baseline", sealed_file="coding/swarm/bug_heldout_v2.json",
        sha256=rec["sha256"], n=len(items), composed_acc=acc,
        per_class_recall=recall, bar=BAR, clears_bar=acc >= BAR,
        sealed_this_run=sealed_now)
    print(f"BASELINE: composed {acc} vs bar {BAR} "
          f"({'CLEARS' if acc >= BAR else 'BELOW'}) — recalls {recall}")
    print(f"binaries: {baseline['per_class_binary_acc']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
