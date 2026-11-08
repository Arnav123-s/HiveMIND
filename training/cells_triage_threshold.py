"""How sure must the task_kind cell be before its shortcut skips the coordinator? Per kind, chosen on dev.

    python training/cells_triage_threshold.py
A shortcut (a template plan, no 4B coordinator or plan reviewer) is taken when the cell names a kind other than 'plan'
with at least that kind's threshold. A wrong shortcut costs most when it lands on 'write' (writer only: no research,
no calculation): on dev and test every wrong shortcut was 'write'. For each kind: the lowest threshold in the grid
whose confident dev answers for that kind are all right (at least 0.9 for every kind). Reported on test, never chosen
there. Writes training/reports/cells/triage_threshold.json; the hive reads the thresholds from cells/wins.json.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from team.cells import runtime, skills as S  # noqa: E402
from training import cells as C  # noqa: E402

GRID = [0.9, 0.93, 0.95, 0.97, 0.98, 0.99, 0.995]


def answers(rows):
    out = []
    for x, y in rows:
        k, c = max(runtime.label_probs("task_kind", x).items(), key=lambda kv: kv[1])
        out.append((k, c, y))
    return out


def shortcut(ans, th):
    used = [(k, y) for k, c, y in ans if k != "plan" and c >= th.get(k, 1.01)]
    return {"shortcut": len(used), "n": len(ans), "right": sum(k == y for k, y in used),
            "precision": round(sum(k == y for k, y in used) / max(1, len(used)), 3),
            "wrong": sorted(f"{y}->{k}" for k, y in used if k != y)}


def main():
    _, dv, te = C.data("task_kind")
    dev, test = answers(dv), answers(te)
    th = {}
    for kind in S.SKILLS["task_kind"]["labels"]:
        if kind == "plan":
            continue
        th[kind] = next((t for t in GRID if all(k == y for k, c, y in dev if k == kind and c >= t)), 1.01)
    flat = {k: 0.9 for k in th}
    res = {"thresholds_chosen_on_dev": th, "dev": shortcut(dev, th), "test": shortcut(test, th),
           "flat_0.9": {"dev": shortcut(dev, flat), "test": shortcut(test, flat)}}
    print(json.dumps(res, indent=1))
    (C.REPORTS / "triage_threshold.json").write_text(json.dumps(res, indent=1))
    runtime.unload()


if __name__ == "__main__":
    main()
