"""More training for the triage cell (task_kind): its first factory run (100 steps) scored 0.756 as served.

    python training/cells_task_kind.py <recipe>      recipe: all_r2 | clone
Same data, 300 steps. Then training/cells_promote.py task_kind keeps the best on dev among every variant.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from training import cells as C  # noqa: E402

recipe = sys.argv[1]
reg = json.loads((C.CELLS / "registry.json").read_text())
if recipe == "all_r2":
    keys = [f"{i}:{m}" for i in range(30) for m in C.MODS]
    C.train("task_kind", "smol135", keys, rank=2, steps=300, tag="all_r2_300")
else:
    par = reg["element_match"]
    C.train("task_kind", "smol135", par["modules"], rank=par["rank"], steps=300, tag="clone_element_match_300",
            parent=str(C.CELLS / "adapters" / "element_match"), thin=par.get("thin"))
