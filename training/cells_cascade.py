"""Cascade: the tiny cell answers when it is sure; an unsure case goes to the bigger member that did the job before.

    python training/cells_cascade.py [skills...]
For each label cell with a measured incumbent (training/reports/cells/incumbent_<skill>.json: its score on the same
150 test inputs and every input it got wrong), the cell's confidence is its probability for its own answer
(runtime.label_probs). The threshold is chosen on the dev split, never on test: the lowest confidence at which the
cell's confident dev answers are at least as accurate as the member is overall. On test: cascade accuracy, how many
cases go up, and cost per input (cell time + share escalated x member time).
Writes training/reports/cells/cascade.json.
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from team.cells import runtime, skills as S  # noqa: E402
from training import cells as C  # noqa: E402

R = ROOT / "training" / "reports" / "cells"


def answers(skill, rows):
    out, t = [], time.time()
    for x, y in rows:
        p = runtime.label_probs(skill, x)
        lab, conf = max(p.items(), key=lambda kv: kv[1])
        out.append((lab == y, conf))
    return out, (time.time() - t) / max(1, len(rows))


def threshold(dev, target):
    """Lowest t whose confident dev answers are at least `target` accurate (1.01 = always escalate)."""
    for t in [x / 100 for x in range(50, 100)] + [0.995, 0.999]:
        conf = [ok for ok, c in dev if c >= t]
        if conf and sum(conf) / len(conf) >= target:
            return t
    return 1.01


def main(skills):
    out = json.loads((R / "cascade.json").read_text()) if (R / "cascade.json").exists() else {}
    for skill in skills:
        f = R / f"incumbent_{skill}.json"
        if not f.exists() or "labels" not in S.SKILLS.get(skill, {}) or not runtime.available(skill):
            print(f"{skill}: skipped (no incumbent measurement, not a label cell, or not built)")
            continue
        inc = json.loads(f.read_text())
        _, dv, te = C.data(skill)
        te = te[:inc["n"]]
        wrong = {e[0] for e in inc["errors"]}
        if len(wrong) < round((1 - inc["test"]) * inc["n"]) - 1:
            print(f"{skill}: skipped (the incumbent's stored errors are incomplete)")
            continue
        inc_ok = [x not in wrong for x, _ in te]
        dev, _ = answers(skill, dv)
        test, cell_ms = answers(skill, te)
        t = threshold(dev, inc["test"])
        up = [c < t for _, c in test]
        casc = [(i_ok if u else c_ok) for (c_ok, _), u, i_ok in zip(test, up, inc_ok)]
        res = {"cell": round(sum(ok for ok, _ in test) / len(test), 3), "incumbent": inc["test"],
               "incumbent_name": inc["incumbent"], "threshold": t, "escalated": round(sum(up) / len(up), 3),
               "cascade": round(sum(casc) / len(casc), 3), "cell_ms": round(cell_ms * 1000, 1),
               "incumbent_ms": inc["ms_per_call"],
               "cascade_ms": round(cell_ms * 1000 + sum(up) / len(up) * inc["ms_per_call"], 1), "n": len(te)}
        out[skill] = res
        print(f"{skill}: cell {res['cell']} | {inc['incumbent']} {res['incumbent']} | cascade {res['cascade']} "
              f"(t={t}, {res['escalated']:.0%} go up, {res['cascade_ms']} ms vs {res['incumbent_ms']} ms)", flush=True)
        (R / "cascade.json").write_text(json.dumps(out, indent=1))
    runtime.unload()


if __name__ == "__main__":
    main(sys.argv[1:] or ["claim_support", "licence_open", "orders_spend", "orders_delete", "orders_send", "orders_login",
                          "orders_signup", "pick_source", "route_step", "next_move", "family_topic"])
