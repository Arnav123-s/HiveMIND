"""Reconstruct a fixed admission snapshot from actual code s0 training inputs."""
import argparse
from collections import Counter
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
from team import solo
from training import grow
from transformers import AutoTokenizer

# Fixed historical rows and guard inputs are taken from code-s0-logs.json.
RUNS={
    "g51":dict(parent="g48code2", date="2026-11-19 (Thursday)",shards=3, cap=508,avail=4.7,bytes=4,given=2387),
    "g55":dict(parent="g51code", date="2026-11-20 (Friday)",shards=2, cap=797,avail=4.9,bytes=2,given=4041),
    "g56":dict(parent="g53code", date="2026-11-20 (Friday)",shards=2, cap=748,avail=4.6,bytes=2,given=4393),
}
GIB=2**30


def shard(file, gen, conf):
    rows=[json.loads(l) for l in file.read_text().splitlines()]
    for r in rows:
        day=re.search(r"Today is (\d{4}-\d\d-\d\d \(\w+\))",r["messages"][0]["content"])
        r["messages"][0]=dict(role="system",content=solo.SHORT.format(today=day[1] if day else conf["date"]))
    rows=[r for r in rows if r.get("type")!="foresee"]
    mend=[]
    for r in rows:
        wrong=str(r.get("rejected_who") or "").partition("+")[2]
        if r.get("type")=="pair" and (wrong==conf["parent"] or re.fullmatch(r"g\d+trunk",wrong)):
            mend.append({k:v for k,v in r.items() if k not in ("rejected","rejected_who","shown")} |
                        dict(type="mend", messages=r["messages"]+[dict(role="assistant",content=r["rejected"]),
                             dict(role="user",content=grow.MEND.format(shown=r.get("shown") or "It ran."))]))
    unique={}
    for r in [r for r in rows if r.get("type")!="pair"]+mend:
        unique.setdefault(json.dumps([r["messages"][1:],r["output"],r.get("rejected")]),r)
    held={task for ts in grow.kept_back(unique.values(),n=2).values() for task in ts}
    rows=[r for r in unique.values() if r["task"] not in held]
    fresh=[];old=[]
    for r in rows:
        (fresh if r.get("gen")==gen or r.get("type")=="mend" else old).append(r)
    return fresh+grow.slice_rows(old,0,conf["shards"])


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("archives",type=Path);ap.add_argument("snapshot");ap.add_argument("--out",required=True,type=Path)
    args=ap.parse_args()
    tok=AutoTokenizer.from_pretrained(args.snapshot)
    config=json.loads((Path(args.snapshot)/"config.json").read_text())
    hidden,vocab=config["hidden_size"],config["vocab_size"]
    @lru_cache(maxsize=40000)
    def size(s):
        return len(tok(s,add_special_tokens=False)["input_ids"])
    def encode(r,cap):
        k=size(r["output"]+"<|im_end|>\n")
        for keep in (None,.6,.35,.15):
            msg=grow.shorten(r["messages"],keep) if keep else r["messages"]
            if keep and msg is r["messages"]:
                break
            p=size(tok.apply_chat_template(msg,tokenize=False,add_generation_prompt=True,enable_thinking=False))
            if p+k<=cap:
                return p+k,k
        return None
    def breakdown(pairs,avail,conf):
        room=(avail-1)*GIB
        train_floor=14*hidden*conf["bytes"]*46
        cp_floor=(46+2*14)*hidden*conf["bytes"]
        totals=Counter();cross=Counter()
        for old,new in pairs:
            old_mode=("ordinary" if old[0]*train_floor<=room else "guard-declined") if old else "static-cap"
            if new:
                pieces,k=new
                head=grow.row_head_bytes(vocab,k)
                mode=next((m for m,f in [("ordinary",train_floor),("checkpoint",cp_floor)] if pieces*f+head<=room),"declined")
            else: mode="requested-cap"
            cross[old_mode+" to "+mode]+=1;totals["stock-"+old_mode]+=1;totals["candidate-"+mode]+=1
        return dict(counts=dict(totals),transition=dict(cross))
    results={}
    for g,conf in RUNS.items():
        file=args.archives/(g+"-rows.jsonl")
        rows=shard(file,g,conf); assert len(rows)==conf["given"],(g,len(rows),conf)
        pairs=[(encode(r,conf["cap"]),encode(r,1152)) for r in rows]
        logged={"g51":(4,40,1836),"g55":(8,40,3797),"g56":(8,40,4061)}[g]
        encoded=sum(old is not None for old,_ in pairs)
        assert encoded+logged[0]+logged[1]==logged[2],(g,encoded,logged)
        results[g]=dict(original_encoded=encoded,external_judged=logged[0],external_read=logged[1],
                        logged_study_size=logged[2],row_archive_sha256=hashlib.sha256(file.read_bytes()).hexdigest(),given=len(rows),inputs=conf,
                        midpoint=breakdown(pairs,conf["avail"],conf),
                        rounding_sensitivity=[breakdown(pairs,conf["avail"]+delta,conf)["counts"] for delta in (-.05,.05)])
        print(g,results[g]["midpoint"],flush=True)
    args.out.write_text(json.dumps(results,indent=2)+"\n")


if __name__=="__main__":
    main()
