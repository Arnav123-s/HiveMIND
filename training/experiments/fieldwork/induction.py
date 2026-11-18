"""Grow two reusable data operations by identifying small programs from earlier demonstrations."""
import argparse
import itertools
import random
from pathlib import Path

from .campaign import fingerprint,save
from .cases import static_cases
from .grade import compact,grade
from .guest import Guest


def aligned(row,roles,rounding,clamp,inclusive):
    ready,origin,step,limit,delay=roles
    h=row[step]
    if h<=0:
        return "invalid"
    diff=row[ready]-row[origin]
    k=-(-diff//h) if rounding=="up" else diff//h
    nxt=row[origin]+(max(0,k) if clamp else k)*h
    valid=nxt<=row[limit] if inclusive else nxt<row[limit]
    return nxt+row[delay] if valid else None


def align(rows):
    data=[(v,t) for x,y in rows for v,t in zip(x["rows"],y)]
    candidates=[]
    for args in itertools.product(itertools.permutations(range(5)),("down","up"),(False,True),(False,True)):
        if all(aligned(row,*args)==target for row,target in data):
            candidates.append(args)
    active=[]
    rng=random.Random(19)
    for _ in range(2000):
        if len(candidates)<=1 or len(active)>=6:
            break
        first=rng.randrange(12)
        row=[rng.randrange(24),first,rng.randrange(1,7),first+rng.randrange(24),rng.randrange(1,7)]
        predictions=[aligned(row,*c) for c in candidates]
        if len(set(predictions))>1:
            # This teacher belongs to the earlier alignment exercise. Only a requested row is observed.
            ready,first,period,last,duration=row
            measured=next((t+duration for t in range(first,last+1,period) if t>=ready),None)
            active.append(dict(input=row,observed=measured,competing=predictions))
            candidates=[c for c,v in zip(candidates,predictions) if v==measured]
    if len(candidates)!=1:
        return None,len(candidates),active
    roles,rounding,clamp,inclusive=candidates[0]
    a,b,c,d,e=roles
    div=f"-(-(r[{a}]-r[{b}])//r[{c}])" if rounding=="up" else f"(r[{a}]-r[{b}])//r[{c}]"
    if clamp:
        div=f"max(0, {div})"
    compare="<=" if inclusive else "<"
    code=f"""def solve(x):
    out = []
    for r in x['rows']:
        grid = r[{b}] + ({div}) * r[{c}]
        out.append(grid + r[{e}] if grid {compare} r[{d}] else None)
    return out"""
    return code,len(candidates),active


def grouped(rows):
    candidates=[]
    for key,version,value in itertools.permutations(range(3)):
        for choose,conflict,order in itertools.product(("min","max"),("drop","first","last"),("asc","desc")):
            code=f"""def solve(x):
    groups = {{}}
    for row in x['events']:
        groups.setdefault(row[{key}], []).append(row)
    out = []
    for k in sorted(groups, reverse={order=='desc'}):
        batch = groups[k]
        level = {choose}(r[{version}] for r in batch)
        vals = [r[{value}] for r in batch if r[{version}] == level]
        if {conflict=='drop'} and len(set(vals)) > 1:
            continue
        out.append([k, level, vals[{-1 if conflict=='last' else 0}]])
    return out"""
            scope={}
            exec(code,scope)
            if all(scope["solve"](x)==y for x,y in rows):
                candidates.append(code)
    return (candidates[0] if len(candidates)==1 else None),len(candidates),[]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sdk",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    g=Guest(args.sdk)
    records=[]
    for name,learner in (("departure",align),("version",grouped)):
        pub=static_cases(name,"public")
        source,width,active=learner(pub)
        if source is None:
            print(name,"remaining programs",width,flush=True)
            continue
        public=grade(g,name,source,"public")
        promotion=grade(g,name,source,"promotion")
        records.append(dict(task=name,source=source,digest=fingerprint(source),admitted=public["complete"] and promotion["complete"],
                            origin="enumerated school grammar",surviving_programs=width,active_observations=active,
                            public=compact(public),promotion=compact(promotion)))
        print(name,width,promotion["correct"],flush=True)
    save(args.out,records)


if __name__=="__main__":
    main()
