"""Small interface and boundary variants proposed from public failures. Every accepted edit must improve outcomes."""
import ast
import re

from .campaign import fingerprint, fitness
from .grade import compact, grade


IMPORTS={v:"import "+v for v in ("heapq","math","json","bisect","collections","itertools","statistics","functools","csv","io","re","random")}
IMPORTS.update({v:"from collections import "+v for v in ("defaultdict","Counter","deque")})
IMPORTS.update({v:"from bisect import "+v for v in ("bisect_left","bisect_right","insort")})
IMPORTS.update({v:"from heapq import "+v for v in ("heappop","heappush","heapify")})


def variants(source,result,remaining):
    error=result["feedback"]
    found=re.search("name '([a-zA-Z_]+)' is not defined",error)
    if found and found[1] in IMPORTS:
        yield "import "+found[1], IMPORTS[found[1]]+"\n"+source
    if "JSON object must be str" in error or "object has no attribute 'read'" in error:
        yield "encode JSON input",source+"\n_field_solve = solve\nimport json\ndef solve(x): return _field_solve(json.dumps(x))\n"
    if 'returned "' in error or "guest returned unreadable output" in error:
        yield "decode JSON result",source+"\n_field_solve = solve\nimport json\ndef solve(x):\n    y=_field_solve(x)\n    return json.loads(y) if isinstance(y,str) else y\n"
    if "not JSON serializable" in error:
        yield "normalize numeric result",source+"""
_field_solve = solve
def _plain(v):
    if isinstance(v,dict): return {k:_plain(x) for k,x in v.items()}
    if isinstance(v,(list,tuple)): return [_plain(x) for x in v]
    return v.tolist() if hasattr(v,'tolist') else v
def solve(x): return _plain(_field_solve(x))
"""
    if not remaining or not result["correct"]:
        return
    try:
        root=ast.parse(source)
    except SyntaxError:
        return
    flips={ast.Lt:ast.LtE,ast.LtE:ast.Lt,ast.Gt:ast.GtE,ast.GtE:ast.Gt}
    alternate={"bisect_left":"bisect_right","bisect_right":"bisect_left"}
    count=0
    for node in ast.walk(root):
        if isinstance(node,ast.Compare) and len(node.ops)==1 and type(node.ops[0]) in flips:
            old=node.ops[0]
            node.ops[0]=flips[type(old)]()
            yield "comparison at line "+str(node.lineno),ast.unparse(root)
            node.ops[0]=old
            count+=1
        elif isinstance(node,ast.Attribute) and node.attr in alternate:
            old=node.attr
            node.attr=alternate[old]
            yield "boundary search at line "+str(node.lineno),ast.unparse(root)
            node.attr=old
            count+=1
        if count>=remaining:
            return


def improve(guest,name,source,mutations=8):
    public=grade(guest,name,source,"public")
    history=[]
    for step in range(3):
        if public["complete"]:
            break
        best=None
        for label,new in variants(source,public,mutations):
            score=grade(guest,name,new,"public")
            history.append(dict(edit=label,parent=fingerprint(source),child=fingerprint(new),correct=score["correct"]))
            if fitness(score)>fitness(public) and (best is None or fitness(score)>fitness(best[2])):
                best=label,new,score
            if score["complete"]:
                break
        if best is None:
            break
        _,source,public=best
    return dict(program=source,selected=fingerprint(source),public=compact(public),history=history)


def main():
    import argparse
    from pathlib import Path
    from .campaign import read, save
    from .contracts import EXAM,SCHOOL
    from .numeric_guest import NumericGuest
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cold",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--tasks",nargs="+",default=(*SCHOOL,*EXAM))
    args=p.parse_args()
    g=NumericGuest()
    for name in args.tasks:
        dest=args.out/(name+".json")
        if dest.exists():
            continue
        got=improve(g,name,read(args.cold/(name+".json"))["source"])
        if name in SCHOOL and got["public"]["complete"]:
            got["promotion"]=compact(grade(g,name,got["program"],"promotion"))
        save(dest,got)
        print(name,got["public"]["correct"],got["public"]["total"],len(got["history"]),flush=True)


if __name__=="__main__":
    main()
