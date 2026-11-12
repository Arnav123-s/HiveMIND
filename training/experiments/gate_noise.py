"""Is what a cell gains where it lives more than chance? Reads the hive as it is; changes nothing.

    HIVE_BODY=<name> python training/experiments/gate_noise.py [out.json]      (HIVE_BODY unset: the first body)

A newborn is kept if the body, on the 60 unseen passages nearest its territory, reads better with it than as if it
were not there by more than body.LOCAL (0.004). Two things are measured here for every living cell of one body:

- the gain and its standard error over those 60 passages. If the standard error is as large as LOCAL, a cell that
  adds nothing passes the gate now and then by luck alone, and growth by such births is partly noise.
- the same gain on the 60 nearest REPORT passages. Gate passages decide who is kept; report passages never decided
  anything. A cell kept by luck looks good on the gate passages and not on the report ones, so over the cells that
  went through the gate, a gate gain well above the report gain is the size of that luck.

Cells made when the territories were first drawn never went through the gate (body.differentiate); the body's own
record says which cells did (births, kept). Both kinds are listed, marked.
"""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from training import body as B  # noqa: E402
from training import scratch as T  # noqa: E402

NEAREST = 60  # as body.turn judges a newborn


def main(argv):
    data, b = B._data(), B.Body()
    gated = {x["cell"]: x for x in B._report().get("births", []) if x.get("kept")}
    rows = []
    for part in ("gate", "report"):
        pool = B._held(data, part, 10 ** 9)
        near = b.near(data, pool)
        for k in b.alive:
            local = [pool[i] for i in near[:, k].topk(min(NEAREST, len(pool))).indices.tolist()]
            f1, s1, _ = b.read(data, local, without=(k,))
            f2, s2, w2 = b.read(data, local)
            d = B.fit_loss(f1, s1) - B.fit_loss(f2, s2)  # per passage: what the body gains by having this cell
            rows.append({"cell": k, "on": part, "gain": round(d.mean().item(), 4), "standard_error": round(d.std().item() / math.sqrt(len(d)), 4),
                         "awake_on": round((w2 == k).any(1).float().mean().item(), 2), "went_through_the_gate": k in gated,
                         "gain_at_birth": round(gated[k]["near_before"] - gated[k]["near_after"], 4)
                         if k in gated and "near_before" in gated[k] else None})  # older records have no such numbers
    def mean(xs):
        return round(sum(xs) / len(xs), 4) if xs else None
    res = {"body": T.BODY or "first", "cells": len(b.alive), "needs": B.LOCAL, "passages": NEAREST,
           "standard_error_of_a_gain": mean([r["standard_error"] for r in rows]),
           "gated_cells": {"n": len([k for k in b.alive if k in gated]),
                           "gain_at_birth": mean([r["gain_at_birth"] for r in rows if r["on"] == "gate" and r["gain_at_birth"] is not None]),
                           "gain_now_on_gate_passages": mean([r["gain"] for r in rows if r["on"] == "gate" and r["went_through_the_gate"]]),
                           "gain_now_on_report_passages": mean([r["gain"] for r in rows if r["on"] == "report" and r["went_through_the_gate"]])},
           "first_cells": {"n": len([k for k in b.alive if k not in gated]),
                           "gain_now_on_gate_passages": mean([r["gain"] for r in rows if r["on"] == "gate" and not r["went_through_the_gate"]]),
                           "gain_now_on_report_passages": mean([r["gain"] for r in rows if r["on"] == "report" and not r["went_through_the_gate"]])},
           "each": rows}
    print(json.dumps({k: v for k, v in res.items() if k != "each"}, indent=1))
    for r in rows:
        print(r)
    if argv:
        Path(argv[0]).write_text(json.dumps(res, indent=1))
    return res


if __name__ == "__main__":
    main(sys.argv[1:])
