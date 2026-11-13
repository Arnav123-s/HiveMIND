"""Subject configs for the niche-expansion picks (PLAN.md section 2).

_cfg-shaped like factory/executors.py's table, but kept HERE: the
executors.py entry is added once, at adoption time, by the
coordinator's serialized sitting (PLAN.md section 4). held_fn is the
deterministic seeded held-A generator — the same function the audit
will re-measure with, forever, so it must stay a pure function of
its seed (plan 5.4).
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from . import battery_sections as BS
from . import gen_data_format as GDF
from . import gen_sec_code as GSC
from . import gen_sql as GSQL


def _cfg(niche, job, classes, fmode, epochs, gen, battery_items):
    return {
        "niche": niche, "job": job, "classes": classes,
        "fmode": fmode, "epochs": epochs, "gen": gen,
        "train_fn": lambda: gen.gen_train()[0],
        "held_fn": lambda: gen.gen_held_a()[0],
        "held_b_fn": lambda: gen.gen_held_b()[0],
        "battery_items": battery_items,
    }


SUBJECTS: Dict[str, Dict[str, Any]] = {
    "sec-code-model": _cfg(
        "sec-code",
        "classify a code snippet by the one weakness class it "
        "contains (or clean)",
        GSC.CLASSES, "codetext", 300, GSC, BS.SEC_CODE_ITEMS),
    "data-format-model": _cfg(
        "data",
        "classify a short text payload by its data format",
        GDF.CLASSES, "text", 300, GDF, BS.DATA_FORMAT_ITEMS),
    "sql-statement-model": _cfg(
        "sql",
        "classify a SQL statement by its leading verb class",
        GSQL.CLASSES, "words", 800, GSQL, BS.SQL_ITEMS),
}

# cycle-id -> subject, in the build order fixed by the assignment
CYCLES = {
    "niche-expansion-001": "sec-code-model",
    "niche-expansion-002": "data-format-model",
    "niche-expansion-003": "sql-statement-model",
}


def subject_config(subject_id: str) -> Optional[Dict[str, Any]]:
    return SUBJECTS.get(subject_id)
