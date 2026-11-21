"""Select from pre-run actor names and documented parent links; score after choosing."""
from collections import Counter, defaultdict
import argparse
import gzip
import json
from pathlib import Path

from training.experiments.astra_retention.specialists.router import Chooser, decisions

HERE = Path(__file__).resolve().parent


def graph(lineage, gen, arm):
    gate=lineage["gates"][str(gen)]
    parents=defaultdict(set)
    for rev in gate["released_snapshots"]:
        for child,parent in lineage["released_snapshots"][rev]["parents"].items():
            if parent:
                parents["t80+"+child].add("t80+"+parent)
    if arm=="after":
        for child,parent in gate["plan"].items():
            if parent:
                parents["t80+"+child].add("t80+"+parent)
    return parents


def resolve(actor, parents, profiles):
    visited=[actor]
    while actor not in profiles:
        if actor.endswith("trunk"):
            return None, visited, "mixed trunk without a single parent"
        links=parents.get(actor,set())
        if not links:
            return None, visited, "documented chain ends without a verified practice profile"
        if len(links)!=1:
            return None, visited, "conflicting parent records"
        actor,=links
        if actor in visited:
            return None, visited, "cycle"
        visited.append(actor)
    return actor,visited,"own" if len(visited)==1 else "inherited"


def choose(practice, queries, lineage):
    # The score file is deliberately outside this function's arguments.
    direct,_=decisions({"practice":practice,"queries":queries})
    model=Chooser([p for p in practice if p["generation"]<=52])
    runs={}
    routes={}
    for key,q in queries.items():
        gen,arm=q["generation"],q["arm"]
        if gen<53 or "skip" in direct[key]:
            continue
        pair=q["actors"][:2]
        if (gen,arm) not in runs:
            runs[gen,arm]=graph(lineage,gen,arm)
        resolved=[resolve(a,runs[gen,arm],model.prototypes) for a in pair]
        profiles=[r[0] for r in resolved]
        chosen=1
        if all(profiles):
            chosen,_,_=model.choose(q["words"],profiles)
        routes[key]=dict(gen=gen,arm=arm,actors=pair,profiles=profiles,paths=[r[1] for r in resolved],
                         source=[r[2] for r in resolved],chosen=chosen,direct=direct[key]["word"])
    return routes


def score(routes, grades):
    report = {}
    for arm in ["after","before"]:
        unique={}
        counts=Counter()
        provenance=Counter()
        inheritance=Counter()
        against_stock=Counter()
        switches=Counter({f"{label}_{metric}":0 for label in ("first","direct") for metric in ("changes","gains","losses")})
        second_only=Counter()
        for key,row in routes.items():
            if row["arm"]!=arm: continue
            counts["eligible"]+=1
            for a,n,reason,path in zip(row["actors"],row["profiles"],row["source"],row["paths"]):
                unique[f"g{row['gen']}/{a}"] = dict(profile=n,source=reason,path=path)
            g=grades[key]
            observed = defaultdict(list)
            for seat,name,right in g["members"]:
                if seat in (1,2) and row["actors"][seat-1]==name:
                    observed[seat].append(right)
            if any(len(observed[s])!=1 for s in (1,2)):
                counts["unobserved"]+=1
                continue
            counts["common"]+=1
            a,b=row["profiles"]
            support=("same profile" if a==b else "two distinct profiles") if a and b else (
                "first only" if a else "second only" if b else "neither")
            provenance[support]+=1
            inheritance[" / ".join(row["source"])]+=1
            first,second=observed[1][0],observed[2][0]
            right=observed[row["chosen"]][0]
            old=observed[row["direct"]][0]
            counts["first"]+=first
            counts["second"]+=second
            counts["direct"]+=old
            counts["heritage"]+=right
            counts["stock_delivery"]+=g["final"]
            counts["oracle_two"]+=first or second
            for label,idx,previous in (("first",1,first),("direct",row["direct"],old)):
                if row["chosen"]!=idx:
                    switches[label+"_changes"]+=1
                    switches[label+"_gains"]+=right and not previous
                    switches[label+"_losses"]+=previous and not right
            against_stock["chooser_right_delivery_wrong"]+=right and not g["final"]
            against_stock["delivery_right_chooser_wrong"]+=g["final"] and not right
            if not a and b and row["source"][1]=="inherited":
                second_only["jobs"]+=1
                second_only["first_right"]+=first
                second_only["second_right"]+=second
                second_only["gains_if_second"]+=second and not first
                second_only["losses_if_second"]+=first and not second
        report[arm]=dict(counts=dict(counts),support=dict(provenance),sources=dict(inheritance),
                         differences=dict(switches),stock_mismatches=dict(against_stock),
                         only_second_has_inherited_profile=dict(second_only),actor_paths=unique)
    return report


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path,default=HERE/"results.json")
    p.add_argument("--check-label-independence", action="store_true")
    a=p.parse_args()
    data=json.loads(gzip.decompress((HERE.parent/"records.json.gz").read_bytes()))
    lineage=json.loads((HERE/"lineage.json").read_text())
    grades=data.pop("grades")
    choices=choose(data["practice"],data["queries"],lineage)
    result=score(choices,grades)
    if a.check_label_independence:
        # Negate every worker and final outcome. Scores must invert; selected actors must stay the same.
        inverted={k:dict(final=not g["final"],members=[[s,w,not ok] for s,w,ok in g["members"]])
                  for k,g in grades.items()}
        replayed=choose(data["practice"],data["queries"],lineage)
        assert choices==replayed
        flipped=score(replayed,inverted)
        for arm,panel in result.items():
            assert panel["counts"]["heritage"]+flipped[arm]["counts"]["heritage"]==panel["counts"]["common"]
    a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
