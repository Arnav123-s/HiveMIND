"""Train the research hive's cells and decide which take their jobs.

    python training/cells_research.py <skill> [...]      (after training/cells_incumbents.py <skill>)
Each cell: the bare base's dev score, then every module at rank 2 for 300 steps (the recipe that won for the triage
cell), promoted if it beats the base on dev; then served through llama.cpp on the test split and compared with what
does its job without it (training/reports/cells/incumbent_<skill>.json). Switched on in cells/wins.json only when it
scores at least as well.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from team.cells import runtime  # noqa: E402
from training import cells as C  # noqa: E402
from training.cells_promote import promote  # noqa: E402

for skill in sys.argv[1:]:
    if not (C.CELLS / "variants" / skill / "all_r2_300" / "result.json").exists():  # trained already: time it only
        C.eval_base(skill, "smol135")
        C.train(skill, "smol135", [f"{i}:{m}" for i in range(30) for m in C.MODS], rank=2, steps=300, tag="all_r2_300")
    entry = promote(skill)
    reg = runtime.registry().get(skill, {})
    inc_p = C.REPORTS / f"incumbent_{skill}.json"
    inc = json.loads(inc_p.read_text()) if inc_p.exists() else None
    cell = reg.get("test_runtime")
    w = json.loads((runtime.CELLS / "wins.json").read_text())
    beats = inc is not None and cell is not None and (cell > inc["test"] if str(inc["incumbent"]).startswith("code:")
                                                      else cell >= inc["test"])  # a tie with a code rule: the rule is cheaper
    w[skill] = {"use": bool(entry) and beats, "cell": cell,
                "incumbent": inc and inc["test"], "incumbent_name": inc and inc["incumbent"]}
    (runtime.CELLS / "wins.json").write_text(json.dumps(w, indent=1))
    print(f"{skill}: cell {cell} vs {inc and inc['incumbent']} {inc and inc['test']} -> {'ON' if w[skill]['use'] else 'off'}",
          flush=True)
runtime.unload()
