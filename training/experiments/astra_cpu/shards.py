"""Replay sharding against actual T80 token lengths on a published all-rows artifact."""
import argparse
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
import re
import zlib

from training import grow
from training.shard_budget import cost_assignment, estimated_work

CAPS=(508,1152)


def identity(row):
    return json.dumps([row["messages"][1:],row["output"],row.get("rejected")],sort_keys=True)


def evaluate(paths, tokenizer_path):
    from team import solo
    from transformers import AutoTokenizer
    tok=AutoTokenizer.from_pretrained(tokenizer_path,local_files_only=True)

    @lru_cache(maxsize=20000)
    def length(text):
        return len(tok(text,add_special_tokens=False)["input_ids"])

    def work(row):
        answer=length(row["output"]+"<|im_end|>\n")
        msgs=row["messages"]
        day=re.search(r"Today is (\d{4}-\d\d-\d\d \(\w+\))",msgs[0]["content"])
        msgs=[{"role":"system","content":solo.SHORT.format(today=day[1] if day else "2026-01-01 (Thursday)")}]+msgs[1:]
        remaining=list(CAPS)
        pieces={cap:0 for cap in CAPS}
        for keep in (None,.6,.35,.15):
            shortened=grow.shorten(msgs,keep) if keep is not None else msgs
            if keep is not None and shortened is msgs:
                break
            prompt=tok.apply_chat_template(shortened,tokenize=False,add_generation_prompt=True,enable_thinking=False)
            seq=length(prompt)+answer
            for cap in tuple(remaining):
                if seq<=cap:
                    pieces[cap]=seq
                    remaining.remove(cap)
            if not remaining:
                break
        return pieces

    cache={}
    records={}
    for gen,path in paths:
        source=[json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        # Fixed parentless, ordinary SFT treatment: no generated mends, preference pairs, or foreseeable-output rows.
        unique={}
        for row in source:
            if row.get("type") not in {"pair","foresee"}:
                unique.setdefault(identity(row),row)
        back={t for group in grow.kept_back(unique.values()).values() for t in group}
        pool=[r for r in unique.values() if r.get("task") not in back]
        shared=[r for r in pool if r.get("gen")==gen or r.get("type")=="mend"]
        old=[r for r in pool if r.get("gen")!=gen and r.get("type")!="mend"]
        exact={}
        for row in pool:
            content=json.dumps([row["messages"],row["output"]],sort_keys=True)
            if content not in cache:
                cache[content]=work(row)
            exact[id(row)]=cache[content]
        rec={"rows_sha256":sha256(path.read_bytes()).hexdigest(),"raw_rows":len(source),"unique_before_holdback":len(unique),
             "old":len(old),"replicated":len(shared),"held_back_rows":len(unique)-len(pool),"caps":{}}
        legacy=[zlib.crc32(json.dumps([r["messages"][1:],r["output"]],sort_keys=True).encode()) for r in old]
        ordered=sorted(range(len(old)),key=lambda i:(-estimated_work(old[i]),identity(old[i])))
        for n in (2,3,8):
            snake=[0]*len(old)
            for j,i in enumerate(ordered):
                tail=j%(2*n)
                snake[i]=tail if tail<n else 2*n-1-tail
            choices={"hash":[v%n for v in legacy],"snake":snake,"cost":cost_assignment(old,n)}
            for cap in CAPS:
                at_cap=rec["caps"].setdefault(str(cap),{})
                shared_work=sum(exact[id(r)][cap] for r in shared)
                total_old=sum(exact[id(r)][cap] for r in old)
                at_cap["eligible_old"]=sum(exact[id(r)][cap]>0 for r in old)
                at_cap["eligible_shared"]=sum(exact[id(r)][cap]>0 for r in shared)
                by_n={}
                for label,owners in choices.items():
                    loads=[shared_work]*n
                    for row,k in zip(old,owners):
                        loads[k]+=exact[id(row)][cap]
                    assert len(owners)==len(old) and sum(loads)==total_old+n*shared_work
                    by_n[label]={"eligible_sequence_tokens":loads,
                                 "max_min_gap_percent_of_mean":round(100*(max(loads)-min(loads))/(sum(loads)/n),3)}
                at_cap[str(n)]=by_n
        records[gen]=rec
    return dict(tokenizer_sha256=sha256((tokenizer_path/"tokenizer.json").read_bytes()).hexdigest(),
                chat_template_sha256=sha256((tokenizer_path/"chat_template.jinja").read_bytes()).hexdigest(),
                treatment="ordinary archive rows, no parent mends/pairs/foresee/read/judged; one full traversal; same cap across workers",
                generations=records)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",nargs=2,action="append",metavar=("GEN","ROWS"),required=True)
    p.add_argument("--tokenizer",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    r=evaluate([(gen,Path(path)) for gen,path in a.archive],a.tokenizer)
    a.out.write_text(json.dumps(r,indent=2)+"\n")
    for gen,g in r["generations"].items():
        print(gen,{s:{k:v["max_min_gap_percent_of_mean"] for k,v in g["caps"]["1152"][s].items()} for s in ("2","3","8")})
