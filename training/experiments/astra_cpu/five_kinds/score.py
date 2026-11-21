"""Join frozen row identities to actual update, admission and source-check receipts."""
import argparse
import json
from pathlib import Path

import numpy as np
from safetensors import safe_open

HERE=Path(__file__).resolve().parent


def score(run):
    selected=json.loads((HERE/"selection.json").read_text())
    receipts=json.loads((run/"result.json").read_text())
    assert receipts["torch_inputs"]["rows"]==selected["rows_sha256"]
    checks={r["kind"].removeprefix("h_prog_"):r for r in json.loads((HERE/"checks.json").read_text())}
    lengths={r["total"] for r in selected["rows"]}
    assert len(lengths)==len(selected["rows"])
    assert all(r["pieces"] in lengths for r in receipts["admissions"]+receipts["row_spans"])
    by_kind=[]
    for row in selected["rows"]:
        n=row["total"]
        spans=[s for s in receipts["row_spans"] if s["pieces"]==n]
        attempts=[s for s in receipts["admissions"] if s["pieces"]==n]
        by_kind.append(dict(kind=row["kind"],source_checked=checks[row["kind"]]["ok"],tokens=n,
                            answer_tokens=row["answer"],finished_updates=len(spans),
                            observed_modes=[s["mode"] for s in attempts],spans=spans))
    changed=0;values=0;difference=0.;changed_tensors=0
    start=run/"grow/t80+astrastudy.start.safetensors"
    end=run/"grow/t80+astrastudy/adapter_model.safetensors"
    with safe_open(start,framework="np") as a,safe_open(end,framework="np") as b:
        assert set(a.keys())==set(b.keys())
        for name in a.keys():
            x=a.get_tensor(name).astype(np.float64)
            y=b.get_tensor(name).astype(np.float64)
            delta=x-y
            changed+=int(np.count_nonzero(delta));values+=x.size
            changed_tensors+=int(np.any(delta))
            difference+=float(np.sum(delta*delta))
    return dict(covered=sum(r["finished_updates"]>=1 for r in by_kind),requested=len(by_kind),
                completed_updates=receipts["training"]["steps"],skipped_passes=receipts["training"]["memory"]["rows_skipped"],
                changed_values=changed,total_values=values,changed_tensors=changed_tensors,update_squared_norm=difference,
                per_kind=by_kind,raw=receipts)


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run",type=Path)
    print(json.dumps(score(ap.parse_args().run),indent=2))
