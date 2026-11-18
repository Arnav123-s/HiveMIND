"""Grade returned values, intervention trajectories and durable two-stage artifacts outside the guest."""
import csv
import hashlib
import io
import json
import math
import statistics
import tempfile
from pathlib import Path

from . import cases
from .guest import least_squares


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def preview(x, limit=520):
    return json.dumps(x, separators=(",",":"),ensure_ascii=True)[:limit]


def numbers(seq, n):
    return isinstance(seq,list) and len(seq)==n and all(type(v) in (int,float) and math.isfinite(v) for v in seq)


def rmse(a,b):
    return math.sqrt(statistics.mean((x-y)**2 for x,y in zip(a,b)))


def grade(guest, name, program, split):
    tests, fuel, seconds = [],0,0
    def run(inputs, budget=8_000_000_000):
        nonlocal fuel, seconds
        rows,used,elapsed=guest.run(program, inputs, fuel=budget)
        fuel+=used
        seconds+=elapsed
        return rows

    if name=="climate":
        bank=cases.climate_cases(split)
        for (x, gold), row in zip(bank,run([x for x,_ in bank],24_000_000_000)):
            val=row.get("value")
            ok = isinstance(val,dict) and numbers(val.get("forecast"),len(gold["y"]))
            met = dict(origin=gold["origin"], naive_rmse=rmse(gold["naive"],gold["y"]),
                       drift_rmse=rmse(gold["drift"],gold["y"]),observed_trend=gold["trend"],observed_peak=gold["peak"])
            if ok:
                error=rmse(val["forecast"],gold["y"])
                tr,pk=val.get("trend"),val.get("peak_month")
                ok=(type(tr) in (int,float) and abs(tr-gold["trend"])<=.5 and type(pk) is int and 1<=pk<=12
                    and min((pk-gold["peak"])%12,(gold["peak"]-pk)%12)<=1 and error<=2.0
                    and error<=.8*met["naive_rmse"] and isinstance(val.get("method"),str) and bool(val["method"].strip()))
                met.update(rmse=error,trend=tr,peak=pk,method=str(val.get("method",""))[:240],
                           predictions=val["forecast"],observations=gold["y"])
            tests.append(dict(ok=bool(ok),detail=met,feedback=row.get("error") or
                              ("check forecast, trend or peak: "+preview({k:v for k,v in met.items()
                                                                         if k not in ("predictions","observations")}))))
    elif name=="thermal":
        worlds=cases.thermal_worlds(split)
        design=run([{"phase":"design","budget":48}])[0]
        u=design.get("value")
        if not isinstance(u,list) or len(u)!=48 or not all(type(v) is int and -2<=v<=2 for v in u):
            tests=[dict(ok=False,feedback=design.get("error") or "design must be exactly 48 integer settings in [-2,2]")
                   for w in worlds]
        else:
            commands=[dict(phase="predict",u=u,y=cases.response(w,u,True),future=w[2]) for w in worlds]
            answers=run(commands,28_000_000_000)
            for w,command,row in zip(worlds,commands,answers):
                gold=cases.response(w,w[2])
                val=row.get("value")
                denom=max(.15,statistics.pstdev(gold))
                xx=[[1,x,old] for x,old in zip(u,[0]+command["y"][:-1])]
                a,b,c=least_squares(xx,command["y"])
                baseline=[]
                for v in w[2]:
                    baseline.append(a+b*v+c*(baseline[-1] if baseline else 0))
                norm=rmse(val,gold)/denom if numbers(val,len(gold)) else None
                tests.append(dict(ok=norm is not None and norm<=.10,detail=dict(family=w[0],nrmse=norm,
                                  simple_nrmse=rmse(baseline,gold)/denom,drive=u,
                                  predictions=val if numbers(val,len(gold)) else None,observations=gold),
                                  feedback=row.get("error") or f"intervention forecast normalized RMSE {norm}, required <=0.10"))
    elif name=="ledger":
        bank=cases.ledger_cases(split)
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            intakes=run([x[0] for x in bank])
            valid=[]
            for idx,(case,row) in enumerate(zip(bank,intakes)):
                snap=row.get("value")
                if digest(snap)!=digest(case[1]):
                    tests.append(dict(ok=False,detail={"case":idx,"phase":"intake"},
                        feedback=row.get("error") or "intake expected "+preview(case[1],210)+"; returned "+preview(snap,210)))
                    continue
                saved=base/str(idx)
                saved.mkdir()
                (saved/"snapshot.json").write_text(json.dumps(snap))
                valid.append(idx)
            # Cold interpreter instance. The only prior state handed over is the reopened snapshot.
            commands=[dict(bank[i][2],snapshot=json.loads((base/str(i)/"snapshot.json").read_text())) for i in valid]
            revised=run(commands)
            for idx,row in zip(valid,revised):
                case=bank[idx]
                files=row.get("value")
                ok=isinstance(files,dict) and set(files)=={"summary.csv","audit.json"} and all(isinstance(v,str) for v in files.values())
                saved=base/str(idx)
                if ok:
                    for key,value in files.items():
                        (saved/key).write_bytes(value.encode())
                    buf=(saved/"summary.csv").read_bytes().decode()
                    try:
                        rows=list(csv.reader(io.StringIO(buf)))
                        audit=json.loads((saved/"audit.json").read_bytes())
                        expected=[["zone","count","grams"]]+[[str(v) for v in r] for r in case[3]]
                        ok=(buf.endswith("\n") and rows==expected and digest(audit)==digest(
                            {"conflicts":case[1]["conflicts"],"kept_count":len(case[1]["kept"])}))
                    except (ValueError,csv.Error):
                        ok=False
                tests.append(dict(ok=ok,detail={"case":idx,"phase":"revise","files":files if idx==0 else None},
                                  feedback=row.get("error") or "revised files or ordering differ, returned "+preview(files,330)))
    else:
        bank=cases.static_cases(name,split)
        answers=run([x for x,_ in bank])
        for (x,y),row in zip(bank,answers):
            val=row.get("value")
            ok=(numbers(val,len(y)) and max(abs(a-b) for a,b in zip(val,y))<1e-4
                if name in ("trend","dynamics") else digest(val)==digest(y))
            tests.append(dict(ok=ok,feedback=row.get("error") or
                              ("input "+preview(x,450)+"; expected "+preview(y,100)+"; returned "+preview(val,120))))
        if name in ("roster","ferry") and split in ("public","exam","confirmation"):
            x,y=cases.stress(name,split)
            result=run([x], 14_000_000_000 if split=="public" else 115_000_000_000)[0]
            tests.append(dict(ok=digest(result.get("value"))==digest(y),detail={"stress":True,"expected":y,
                "returned":result.get("value"),"size":len(x["jobs"] if name=="roster" else x["edges"])},
                feedback=result.get("error") or "large timetable/schedule requires "+preview(y)+"; returned "+preview(result.get("value"))))
    correct=sum(r["ok"] for r in tests)
    return dict(correct=correct,total=len(tests),complete=correct==len(tests) and bool(tests),fuel=fuel,seconds=seconds,
                tests=tests,feedback=next((r["feedback"] for r in tests if not r["ok"]), "All public checks passed."))


def compact(record):
    return {k:v for k,v in record.items() if k!="tests"}
