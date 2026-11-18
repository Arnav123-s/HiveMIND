"""Run a new, user-defined programming work order on CPU with public examples and a persistent skill directory."""
import argparse
import csv
import io
import json
import os
import re
import tempfile
from pathlib import Path

from .campaign import fingerprint, save, tool_source
from .contracts import Task
from .guest import Guest
from .native import generate,server


def words(text):
    return set(re.findall(r"[a-z]{4,}",text.lower()))-{"return","input","output","write","python","list","function","solve","with","each"}


def retrieve(text,bank):
    mine=words(text)
    def score(row):
        other=words(row["description"])
        return len(mine & other)/max(1,len(mine | other))
    ranked=sorted((r for r in bank if score(r)>0),key=lambda r:(-score(r),-r["validation"],r["digest"]))
    selected={}
    for r in ranked:
        selected.setdefault(r["task"],r)
    return list(selected.values())[:2]


def matches(actual,expected,formats=None):
    if formats:
        if not isinstance(actual,dict) or set(expected)!=set(actual):
            return False
        actual,expected=actual.copy(),expected.copy()
        for key,fmt in formats.items():
            if not isinstance(actual.get(key),str) or not isinstance(expected.get(key),str):
                return False
            try:
                if fmt=="json":
                    actual[key],expected[key]=json.loads(actual[key]),json.loads(expected[key])
                elif fmt=="csv":
                    if expected[key].endswith("\n") and not actual[key].endswith("\n"):
                        return False
                    actual[key]=list(csv.reader(io.StringIO(actual[key])))
                    expected[key]=list(csv.reader(io.StringIO(expected[key])))
                else:
                    raise ValueError("unknown file comparison")
            except (ValueError,csv.Error):
                return False
    return json.dumps(actual,sort_keys=True)==json.dumps(expected,sort_keys=True)


def check(guest,program,examples,formats=None):
    results,_,_=guest.run(program,[r["input"] for r in examples],fuel=14_000_000_000)
    ok=[("value" in v and matches(v["value"],r["output"],formats))
        for v,r in zip(results,examples)]
    failed=next((i for i,b in enumerate(ok) if not b),None)
    feedback="All examples passed."
    if failed is not None:
        feedback=json.dumps({"input":examples[failed]["input"],"expected":examples[failed]["output"],
                             "actual":results[failed]},separators=(",",":"))[:650]
    return sum(ok),feedback


def load_bank(directory):
    if directory is None or not directory.is_dir():
        return []
    old=[]
    for p in sorted(directory.glob("*.json")):
        row=json.loads(p.read_text())
        if re.fullmatch("[a-z][a-z0-9_]{0,60}", row["task"]) and fingerprint(row["source"])==p.stem:
            old.append(row)
    return old


def finish_files(root,ident,value,names):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}",ident):
        raise ValueError("job ID must be a single name")
    if (len(set(names))!=len(names) or not names or any(Path(n).name!=n or n in (".","..","") for n in names)
        or not isinstance(value,dict) or set(value)!=set(names) or not all(isinstance(v,str) for v in value.values())):
        raise ValueError("returned files differ from the requested file contract")
    destination=root/ident
    if destination.exists():
        raise FileExistsError(destination)
    with tempfile.TemporaryDirectory(dir=root) as tmp:
        stage=Path(tmp)/"files"
        stage.mkdir()
        for n in names:
            (stage/n).write_bytes(value[n].encode())
        os.replace(stage,destination)


def work(spec,guest,ask,out,bank_path=None,rounds=3):
    name=spec["name"]
    if not re.fullmatch("[a-z][a-z0-9_]{0,60}",name) or not spec["examples"]:
        raise ValueError("provide a short program name and at least one checked example")
    out.mkdir(parents=True,exist_ok=False)
    old=retrieve(spec["task"],load_bank(bank_path))
    prompt=Task(spec["task"],(),"Public examples: "+json.dumps(spec["examples"],separators=(",",":"))[:1900])
    prefix=""
    if old:
        prefix="\nVerified optional functions from previous work:\n"+"\n".join(
            f"skill_{r['task']}(x): {r['description']}\n{r['source'][:1300]}" for r in old)
    best,trace=None,[]
    for attempt in range(rounds):
        prior=(best["source"],best["feedback"]) if best else None
        row=ask(prompt,prefix,prior)
        program=tool_source(row["source"],old)
        passed,feedback=check(guest,program,spec["examples"],spec.get("compare"))
        new=dict(program=program,source=row["source"],passed=passed,feedback=feedback,usage=row["usage"])
        trace.append(new)
        if best is None or passed>best["passed"]:
            best=new
        if passed==len(spec["examples"]):
            break
    (out/"solver.py").write_text(best["program"]+"\n")
    promotion=spec.get("validation",[])
    checked=0
    if promotion and best["passed"]==len(spec["examples"]):
        checked,_=check(guest,best["program"],promotion,spec.get("compare"))
    key=fingerprint(best["program"])
    result=dict(digest=key,public=best["passed"],examples=len(spec["examples"]),validated=checked,
                validation_total=len(promotion),parents=[r["digest"] for r in old],attempts=trace,jobs=[])
    jobs=spec.get("jobs",[])
    if best["passed"]==len(spec["examples"]) and (not promotion or checked==len(promotion)):
        outputs,_,_=guest.run(best["program"],[j["input"] for j in jobs],fuel=30_000_000_000)
        for job,value in zip(jobs,outputs):
            if "files" in job and "value" in value:
                try:
                    finish_files(out,job["id"],value["value"],job["files"])
                except (OSError,ValueError) as exc:
                    value={"error":str(exc)}
            result["jobs"].append({"id":job["id"],**value})
    if bank_path and promotion and checked==len(promotion) and best["passed"]==len(spec["examples"]):
        save(bank_path/(key+".json"),dict(task=name,description=spec["task"],source=best["program"],digest=key,
                                       public=best["passed"],validation=checked,parents=result["parents"]))
    save(out/"receipt.json",result)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ("spec","out","binary","weights","sdk"):
        p.add_argument("--"+k,type=Path,required=True)
    p.add_argument("--adapter",type=Path)
    p.add_argument("--bank",type=Path)
    p.add_argument("--rounds",type=int,default=3)
    p.add_argument("--threads",type=int,default=4)
    args=p.parse_args()
    if args.rounds<1:
        p.error("rounds must be positive")
    spec=json.loads(args.spec.read_text())
    g=Guest(args.sdk)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp, server(args.binary,args.weights,Path(tmp)/"server.log",
                                                     args.adapter,args.threads) as url:
        score=work(spec,g,lambda task,prefix,prior:generate(url,task,prefix,prior),
                   args.out,args.bank,args.rounds)
    print(f"{score['public']}/{score['examples']} examples, {score['validated']}/{score['validation_total']} independent checks")


if __name__=="__main__":
    main()
