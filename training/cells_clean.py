"""Retrain the cells whose training data held bench values (removed from team/cells/skills.py on 2026-11-09).

    python training/cells_clean.py
triage (task_kind), source picking (pick_source) and quote picking (quote_pick) run in the hive and their training
pools had named a bench task's model ids, units, category, package or version. Each is trained again on the cleaned
data (every module, rank 2, 300 steps); only the new variants compete on dev (the old ones learned the withdrawn
data). pick_source and quote_pick are then compared with their incumbents; task_kind's shortcut thresholds are
chosen on dev again (training/cells_triage_threshold.py).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from team.cells import runtime  # noqa: E402
from training import cells as C  # noqa: E402
from training.cells_promote import promote  # noqa: E402

for skill in sys.argv[1:] or ["task_kind", "pick_source", "quote_pick"]:
    C.eval_base(skill, "smol135")
    C.train(skill, "smol135", [f"{i}:{m}" for i in range(30) for m in C.MODS], rank=2, steps=300, tag="clean_all_r2_300")
    entry = promote(skill, prefix="clean")
    reg = runtime.registry().get(skill, {})
    print(f"{skill}: promoted {reg.get('variant')} (served test {reg.get('test_runtime')})", flush=True)
    if skill == "task_kind":
        from training import cells_triage_threshold
        cells_triage_threshold.main()
        continue
    inc_p = C.REPORTS / f"incumbent_{skill}.json"
    inc = json.loads(inc_p.read_text()) if inc_p.exists() else None
    w = json.loads((runtime.CELLS / "wins.json").read_text())
    old = w.get(skill, {})
    w[skill] = {**old, "use": bool(entry) and inc is not None and reg.get("test_runtime", 0) >= inc["test"],
                "cell": reg.get("test_runtime"), "incumbent": inc and inc["test"], "incumbent_name": inc and inc["incumbent"]}
    (runtime.CELLS / "wins.json").write_text(json.dumps(w, indent=1))
    print(f"{skill}: cell {w[skill]['cell']} vs {w[skill]['incumbent_name']} {w[skill]['incumbent']} -> "
          f"{'ON' if w[skill]['use'] else 'off'}", flush=True)
runtime.unload()
