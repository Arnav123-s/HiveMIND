"""Probe real archived worker modules and correlated lookup controls only inside the WASI guest."""
import argparse
import ast
from collections import defaultdict
from hashlib import sha256
from itertools import combinations
import json
import os
from pathlib import Path
import random

from training.experiments.fieldwork.guest import Guest

HERE = Path(__file__).resolve().parent
RETURN_TYPES = {"to_seconds": int, "to_text": str, "from_roman": int, "to_roman": str}


def roman(n):
    result = ""
    for value, word in ((1000,"M"),(900,"CM"),(500,"D"),(400,"CD"),(100,"C"),(90,"XC"),(50,"L"),
                        (40,"XL"),(10,"X"),(9,"IX"),(5,"V"),(4,"IV"),(1,"I")):
        count,n = divmod(n,value)
        result += word*count
    return result


def duration(n):
    hours, left = divmod(n,3600)
    minutes, seconds = divmod(left,60)
    return "".join(f"{value}{unit}" for value,unit in ((hours,"h"),(minutes,"m"),(seconds,"s")) if value) or "0s"


def probes(filename):
    rng = random.Random(filename)
    result = []
    for _ in range(15):
        if filename=="roman.py":
            n,m = rng.randint(1,3999),rng.randint(1,3999)
            result.extend([("from_roman",roman(n),n),("to_roman",m,roman(m))])
        else:
            n,m = rng.randint(0,86399),rng.randint(0,86399)
            result.extend([("to_seconds",duration(n),n),("to_text",m,duration(m))])
    return result


# Public examples printed in the two original requests. The correlated peer uses a dictionary
# for new inputs and the same typed fallback as the earlier lookup-only control.
PUBLIC = {
    "roman.py": {"from_roman": ({"XLII":42},0),"to_roman": ({1994:"MCMXCIV"},"")},
    "durations.py": {"to_seconds": ({"1h30m15s":5415,"45m":2700},0),
                     "to_text": ({5415:"1h30m15s",3600:"1h",0:"0s"},"")},
}


def lookup_peer(filename, fixed):
    functions = []
    for name,(table,default) in PUBLIC[filename].items():
        if fixed:
            source = f"def {name}(value):\n    return {table!r}.get(value, {default!r})\n"
        else:
            keyed = {(value,):answer for value,answer in table.items()}
            source = f"def {name}(*values):\n    return {keyed!r}.get(values, {default!r})\n"
        functions.append(source)
    return "\n".join(functions)


def fixed_original(source):
    """Adapt the original lookup's public declaration, preserving all original comparisons and outcomes."""
    root = ast.parse(source)
    for f in root.body:
        if isinstance(f,ast.FunctionDef):
            assert f.args.vararg and f.args.vararg.arg=="args" and not f.args.args
            f.args.args = [ast.arg(arg="value")]
            f.args.vararg = None
            f.body.insert(0,ast.parse("args = (value,)").body[0])
    return ast.unparse(ast.fix_missing_locations(root))+"\n"


def declared(source, names):
    signatures = {}
    for node in ast.parse(source).body:
        if isinstance(node,ast.FunctionDef) and node.name in names:
            a=node.args
            signatures[node.name] = [len(a.posonlyargs)+len(a.args),len(a.defaults),bool(a.vararg),
                                     len(a.kwonlyargs),bool(a.kwarg)]
    return signatures


def study(sdk):
    fixtures = json.loads((HERE/"fixtures.json").read_text())
    guest = Guest(sdk)
    sources = fixtures["source_files"]
    cache, comparisons, genuine = {},[],defaultdict(set)

    def h(s): return sha256(s.encode()).hexdigest()
    def run(source,filename):
        key = h(source)
        if key not in cache:
            test = probes(filename)
            functions = sorted(PUBLIC[filename])
            dispatch = "\n\ndef solve(x):\n    return {"+", ".join(f"{n!r}: {n}" for n in functions)+"}[x[0]](x[1])\n"
            outputs, fuel, _ = guest.run(source+dispatch,[[n,arg] for n,arg,_ in test])
            if len(outputs)!=30:
                raise ValueError("Expected one result for every probe")
            right=sum("value" in got and type(got["value"]) is type(expected) and got["value"]==expected
                      for got,(_,_,expected) in zip(outputs,test))
            cache[key] = dict(probes=30,right=right,errors=sum("error" in o for o in outputs),outputs=outputs,
                              signatures=declared(source,functions),fuel=fuel)
        return key

    def pair(group, case, filename, left, right):
        l,r=run(left,filename),run(right,filename)
        a,b=cache[l],cache[r]
        outputs=list(zip(a["outputs"],b["outputs"]))
        expected_types=[RETURN_TYPES[name] for name,_,_ in probes(filename)]
        def equal(i,x,y):
            return ("value" in x and "value" in y and type(x["value"]) is expected_types[i]
                    and type(y["value"]) is expected_types[i] and x["value"]==y["value"])
        same=sum(equal(i,x,y) for i,(x,y) in enumerate(outputs))
        comparisons.append(dict(group=group,case=case,filename=filename,left=l,right=r,successful_agreement=same,
                                confirmed=same==30,identical_declarations=a["signatures"]==b["signatures"],
                                left_right=a["right"],right_right=b["right"],
                                first_distinguishing_probe=next((i for i,(x,y) in enumerate(outputs) if not equal(i,x,y)),None)))
    for c in fixtures["cases"]:
        filename=c["filename"]
        case=c["gate"]+"/"+c["task"]
        first=sources[c["lookup_alone"]["source"]]
        assert h(first)==c["lookup_alone"]["source"] and not c["lookup_alone"]["original_official_pass"]
        pair("original_and_dictionary_lookup",case,filename,first,lookup_peer(filename,False))
        pair("two_single_argument_lookups",case,filename,fixed_original(first),lookup_peer(filename,True))
        if "proposal" in c:
            key=c["proposal"]["source"]
            worker=sources[key]
            assert h(worker)==key
            genuine[filename].add(key)
            pair("original_lookup_and_worker",case,filename,first,worker)
    for filename,keys in sorted(genuine.items()):
        for left,right in combinations(sorted(keys),2):
            pair("distinct_archived_workers",None,filename,sources[left],sources[right])
    groups=sorted(set(p["group"] for p in comparisons))
    summary={group:{"pairs":sum(p["group"]==group for p in comparisons),
                    "confirmed":sum(p["group"]==group and p["confirmed"] for p in comparisons)}
             for group in groups}
    return dict(summary=summary,comparisons=comparisons,
                probes={f:probes(f) for f in sorted(PUBLIC)},candidates=cache,
                sdk_sha256=sha256((sdk/"python.wasm").read_bytes()).hexdigest())


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sdk",type=Path,required=True)
    ap.add_argument("--out",type=Path,default=HERE/"results.json")
    args=ap.parse_args()
    os.environ["RAYON_NUM_THREADS"]="1"
    if hasattr(os,"sched_setaffinity"):
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    result=study(args.sdk)
    args.out.write_text(json.dumps(result,indent=1,sort_keys=True)+"\n")
    print(json.dumps(result["summary"]))
