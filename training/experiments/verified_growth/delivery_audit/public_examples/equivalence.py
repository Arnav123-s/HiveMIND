"""Compare two frozen intake parsers on original requests before attaching existing decision and grade receipts."""
import argparse
from collections import Counter, defaultdict
import importlib
import json
from pathlib import Path
import time

from .replay import HERE, archives, digest
from .score import SEALED


def wire(spec):
    if spec is None:
        return None
    filename, functions, examples, queries = spec
    return [filename, sorted(functions), examples, queries]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archives",type=Path,required=True)
    p.add_argument("--guard-module",required=True)
    p.add_argument("--guard-hash",required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    start=time.monotonic()
    original=importlib.import_module("training.experiments.verified_growth.delivery_audit.literal_intake.intake")
    guard=importlib.import_module(args.guard_module)
    assert digest(Path(original.__file__).read_bytes())=="11aa54578a7af9fed43dbd0014f9791b04770c96fd4904b78d36ff5d6e70ba2c"
    assert digest(Path(guard.__file__).read_bytes())==args.guard_hash
    statuses=Counter()
    records=[]
    for row,prompt,*unused in archives(args.archives):
        a,b=wire(original.contract(prompt)),wire(guard.contract(prompt))
        state="absent_both" if a is None and b is None else "new" if a is None else "removed" if b is None else "identical" if a==b else "different"
        statuses[state]+=1
        records.append(dict(archive=row["archive_id"],task=row["task"],filename=row["filename"],
                            prompt_sha256=row["prompt_sha256"],result=state))
    # Graded outcomes are reusable only after every accepted contract is found equivalent, with no new accepted requests.
    anchor=(HERE/"alternative.json").read_bytes()
    grades=(HERE/"grades.json").read_bytes()
    assert digest(anchor)==SEALED["alternative"] and digest(grades)=="f4911772f2b794bffa29eccf4ff4da7abbf254e004613ac9f1fba5b64587985d"
    previous=json.loads(grades)
    original_spec_rows=json.loads(anchor)["rows"]
    texts=defaultdict(lambda:[False,False,False])
    retained_by_report=Counter()
    if "different" in statuses or "new" in statuses:
        gains = None
    else:
        gains=0
        for req,hist,stage in zip(records,previous["rows"],original_spec_rows,strict=True):
            assert (req["archive"],req["task"])==(hist["archive_id"],hist["task"])
            retained=bool(req["result"]=="identical" and hist.get("proposal",{}).get("passed"))
            if retained and hist["original_ok"] is False:
                gains+=1
            retained_by_report[req["result"]+"_"+stage["prior"]]+=1
            req["preserves_passing_proposal"]=retained
            by_text=texts[req["prompt_sha256"]]
            by_text[0] |= bool(hist["original_ok"])
            by_text[1] |= bool(hist["original_ok"] or hist.get("proposal",{}).get("passed"))
            by_text[2] |= bool(hist["original_ok"] or retained)
    out=dict(module=args.guard_module,guard_sha256=args.guard_hash,previous_sha256=SEALED["alternative"],
             grades_sha256=digest(grades),results=statuses,reusable_historical_gains=gains,by_report=retained_by_report,
             any_pass_per_unique_text=dict(distinct_texts=len(texts),original=sum(v[0] for v in texts.values()),
                                           first_parser=sum(v[1] for v in texts.values()),guard=sum(v[2] for v in texts.values())) if gains is not None else None,
             wasm_calls=0,model_calls=0,wall_seconds=time.monotonic()-start,rows=records)
    args.out.write_text(json.dumps(out,indent=2)+"\n")
    print(statuses,gains)


if __name__=="__main__":
    main()
