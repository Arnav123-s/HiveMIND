"""How sure must the family_topic cell be before it blocks a step? Chosen on dev, reported on test.

    python training/cells_family_threshold.py
It only ever adds blocks (the rule's blocks stand regardless), so a false "yes" stops legitimate work: in the hive
bench it dropped the writer step of "Summarise this: <a paragraph about a bridge>" and the run had no report.
For each threshold on P(yes): precision and recall of its blocks on dev and test. The chosen threshold is the one
with the best dev accuracy (ties: the lower, stricter one). Writes training/reports/cells/family_threshold.json.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from team.cells import runtime  # noqa: E402
from training import cells as C  # noqa: E402

TS = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95]


def table(rows):
    ps = [(runtime.label_probs("family_topic", x)["yes"], y == "yes") for x, y in rows]
    out = {}
    for t in TS:
        tp = sum(p >= t and y for p, y in ps)
        fp = sum(p >= t and not y for p, y in ps)
        fn = sum(p < t and y for p, y in ps)
        out[t] = {"accuracy": round(sum((p >= t) == y for p, y in ps) / len(ps), 3),
                  "precision": round(tp / max(1, tp + fp), 3), "recall": round(tp / max(1, tp + fn), 3), "false_blocks": fp}
    return out


_, dv, te = C.data("family_topic")
dev, test = table(dv), table(te)
best = max(TS, key=lambda t: (dev[t]["accuracy"], -t))
res = {"chosen_on_dev": best, "dev": dev, "test": test}
for t in TS:
    print(f"t={t}: dev {dev[t]} | test {test[t]}")
print("chosen on dev:", best)
(C.REPORTS / "family_threshold.json").write_text(json.dumps(res, indent=1))
runtime.unload()
