"""Emit a static seat manifest from earlier timings and fresh task identities."""
import argparse
import json
from pathlib import Path

from replay import ARMS, HERE, blind_place


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--through",choices=("g50","g51","g52"),required=True,help="latest prior generation")
    p.add_argument("--ids",type=Path,help="JSON array of unique fresh and fixed task IDs, same for both arms")
    p.add_argument("--example",choices=("g51","g52"),help="use an archived identity set for a dry run")
    p.add_argument("--mode",choices=("uniform_overhead","older_times","round_robin"),default="uniform_overhead")
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    if bool(args.ids)==bool(args.example):
        p.error("choose --ids or --example")
    data=json.loads((HERE/"timings.json").read_bytes())
    if args.example:
        if args.through>=args.example:
            p.error("choose only generations before the example")
        ids=[tid for s,x in data[args.example].items() if s.startswith("before") for tid in x["tasks"]]
    else:
        ids=json.loads(args.ids.read_bytes())
    if not ids or len(set(ids))!=len(ids) or any(not isinstance(t,str)or not t for t in ids):
        p.error("expected unique task IDs")
    old=[data[g]for g in sorted(data)if g<=args.through]
    plan={}
    for arm in ARMS:
        for seat,queue in blind_place(arm,old,ids,args.mode).items():
            plan[seat]={"fresh":[t for t in queue if not t.startswith("x_")],
                        "held":[t for t in queue if t.startswith("x_")]}
    args.out.write_text(json.dumps(plan,indent=1,sort_keys=True)+"\n")


if __name__=="__main__":
    main()
