"""The ONE post-fix re-judge of the sealed bug-pattern held-out
v2 set (Arnav's direction 2026-11-10 13:51 PT: fix on the
training side, re-judge once, report moved/unmoved honestly).

Mirrors run_bug_heldout.py's measurement exactly (same harness:
dream.load_bug_registry + dream.composed_eval + per-class binary
measures), run against the composition AS SERVED after the fix
attempts (bugfix-2026-11-10-001..003), and writes
results/bug_heldout_v2_postfix.json. The script refuses to
overwrite that file: one judge, one record. The baseline record
is never touched.

    python3 -m factory.run_bug_heldout_postfix
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from factory import bug_heldout_v2 as BH  # noqa: E402
from factory.lineage import LineageLog, now_ts  # noqa: E402

LAB_ROOT = Path(__file__).parent.parent
POSTFIX_PATH = LAB_ROOT / "results" / "bug_heldout_v2_postfix.json"
BASELINE_PATH = LAB_ROOT / "results" / "bug_heldout_v2_baseline.json"
BAR = 0.80


def main() -> int:
    if POSTFIX_PATH.exists():
        post = json.loads(POSTFIX_PATH.read_text())
        print(f"post-fix judge already recorded ({post['measured_at']}): "
              f"composed {post['composed_acc']} vs bar {BAR} — "
              f"this script runs once and will not re-measure")
        return 0
    from factory import dream
    from factory.executors import measure
    rec = BH.load_sealed()
    items = rec["items"]
    base = json.loads(BASELINE_PATH.read_text())
    reg = dream.load_bug_registry()
    acc, recall = dream.composed_eval(reg, items)
    binaries = {}
    for cls in ("off-by-one", "wrong-operator", "swapped-operands",
                "mutable-default", "missing-return"):
        rel = dream._relabel(items, cls)
        binaries[cls] = measure(reg[f"bug-{cls}-model"], rel)
    delta = {c: round(recall.get(c, 0.0)
                      - base["per_class_recall"].get(c, 0.0), 4)
             for c in base["per_class_recall"]}
    post = {
        "sealed_file": "coding/swarm/bug_heldout_v2.json",
        "sealed_sha256": rec["sha256"],
        "measured_at": now_ts(),
        "subject": "bug-pattern-composed (as served after the fix "
                   "attempts)",
        "fix_cycle": "bugfix-2026-11-10-004",
        "fix_attempts": ["bugfix-2026-11-10-001",
                         "bugfix-2026-11-10-002",
                         "bugfix-2026-11-10-003",
                         "bugfix-2026-11-10-004"],
        "n": len(items),
        "composed_acc": acc,
        "per_class_recall": recall,
        "per_class_binary_acc": {c: b["acc"] for c, b in binaries.items()},
        "bar": BAR,
        "clears_bar": acc >= BAR,
        "baseline_composed_acc": base["composed_acc"],
        "baseline_per_class_recall": base["per_class_recall"],
        "delta_composed_acc": round(acc - base["composed_acc"], 4),
        "delta_per_class_recall": delta,
        "protocol": ("the single post-fix measurement of the sealed "
                     "set, taken after all fix decisions were made "
                     "on spent sets; no fix decision ever read this "
                     "set (it was a contamination reference only)"),
    }
    tmp = POSTFIX_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(post, indent=1, ensure_ascii=False))
    tmp.replace(POSTFIX_PATH)
    LineageLog(LAB_ROOT / "factory" / "lineage.jsonl").append(
        "bug_heldout_v2_postfix", sealed_sha256=rec["sha256"],
        composed_acc=acc, per_class_recall=recall,
        baseline=base["composed_acc"], delta=post["delta_composed_acc"],
        clears_bar=acc >= BAR, fix_cycle=post["fix_cycle"])
    print(f"POST-FIX: composed {acc} vs bar {BAR} "
          f"({'CLEARS' if acc >= BAR else 'BELOW'}) — "
          f"baseline {base['composed_acc']}, delta "
          f"{post['delta_composed_acc']:+}")
    print(f"recalls {recall} (deltas {delta})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
