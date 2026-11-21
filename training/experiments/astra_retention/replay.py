"""Chronological, fixed-exposure replay study on the published G55/G56 all-rows artifacts."""
import argparse
from collections import Counter, defaultdict
from functools import lru_cache
import gzip
from hashlib import sha256
import json
import math
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def fingerprint(text):
    return sha256(text.encode()).hexdigest()


def question(row):
    return " ".join(row["task"].split()).casefold()


def code(raw):
    stripped = raw.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        stripped = stripped.partition("\n")[2][:-3].strip()
    return stripped


def words(text):
    return re.findall(r"[a-z]+|[0-9]+", text.lower())


def unique(rows, key):
    result = {}
    for row in rows:
        result.setdefault(key(row), row)
    return list(result.values())


def usable(row):
    seed = row.get("seed")
    return (type(seed) is int and (10_000_000 <= seed < 20_000_000 or 30_000_000 <= seed < 40_000_000)
            and row.get("type") in ("first", "fix") and row.get("kind") and row.get("task") and code(row["output"]))


def self_rows(archive, actors):
    return unique([r for r in archive if usable(r) and r.get("who") in actors],
                  lambda r: (question(r), code(r["output"]), r.get("who"), r.get("agreed")))


def accepted(rows):
    # grow.taught's fallback only emits an agreeing member; false proves a per-member positive for this row.
    return unique([r for r in rows if r.get("agreed") is False],
                  lambda r: (question(r), code(r["output"])))


def identity(row):
    return fingerprint(question(row)+"\x00"+code(row["output"]))


def round_robin(groups):
    groups = [list(reversed(group)) for group in groups]
    out = []
    while any(groups):
        for group in groups:
            if group:
                out.append(group.pop())
    return out


def reservoir(rows, cap=400):
    from team.ternary import organ
    by = defaultdict(lambda: defaultdict(list))
    for r in rows:
        by[organ(r["task"])][r["kind"]].append(r)
    queues = [round_robin([sorted(by[o][k],key=identity) for k in sorted(by[o])]) for o in sorted(by)]
    return round_robin(queues)[:cap]


def census(rows, actors, trunk):
    from team.ternary import organ
    named = self_rows(rows,actors)
    checked = accepted(named)
    chosen = reservoir(checked)
    return {"named_distinct_task_program_author_evidence":len(named),
            "provable_individually_passed_distinct_task_programs":len(checked),
            "single_current_trunk_named_rows":len(self_rows(rows,{trunk})),
            "single_current_trunk_provable_distinct_task_programs":len(accepted(self_rows(rows,{trunk}))),
            "reservoir":len(chosen),"by_author":dict(Counter(r["who"] for r in chosen)),
            "by_task_organ":dict(Counter(organ(r["task"]) for r in chosen)),
            "kind_count":len({r["kind"] for r in chosen}),
            "source_versions":dict(Counter(r.get("gen","unstamped") for r in chosen))}


class Router:
    """Frozen multinomial question-word classifier; only task text is supplied for a prediction."""
    def __init__(self, rows):
        self.counts=defaultdict(Counter)
        self.docs=Counter()
        vocab=set()
        for r in unique(rows,question):
            w=words(question(r))
            self.counts[r["kind"]].update(w)
            self.docs[r["kind"]]+=1
            vocab.update(w)
        self.denom={k:sum(c.values())+len(vocab) for k,c in self.counts.items()}

    def predict(self, prompt):
        counts=Counter(words(prompt))
        return max(sorted(self.counts),key=lambda k:math.log(self.docs[k])+sum(
            n*(math.log(self.counts[k].get(w,0)+1)-math.log(self.denom[k])) for w,n in counts.items()))


@lru_cache(maxsize=10000)
def grams(program):
    b=program if isinstance(program, bytes) else program.encode("utf-8")
    history=[256,256]+list(b)
    counts=Counter((history[i]*257+history[i+1])*256+history[i+2] for i in range(len(b)))
    contexts=Counter()
    for token,n in counts.items():
        contexts[token//256]+=n
    return counts,contexts


class Counts:
    def __init__(self):
        self.next=defaultdict(Counter)
        self.prev=defaultdict(Counter)

    def add(self,row,weight,target=None):
        tri,ctx=grams(code(row["output"]) if target is None else target)
        for group in ("_all",row["kind"]):
            for g,n in tri.items():
                self.next[group][g]+=weight*n
            for g,n in ctx.items():
                self.prev[group][g]+=weight*n


def log_likelihood(program,kind,basis,factor,delta):
    ng,_=grams(program)
    bnext,bprev,dnext,dprev=basis.next,basis.prev,delta.next,delta.prev
    out=0.
    for tri,number in ng.items():
        ctx=tri//256
        p0=(factor*bnext["_all"].get(tri,0)+dnext["_all"].get(tri,0)+.1)/(
            factor*bprev["_all"].get(ctx,0)+dprev["_all"].get(ctx,0)+25.6)
        local=(factor*bnext[kind].get(tri,0)+dnext[kind].get(tri,0)+8*p0)/(
            factor*bprev[kind].get(ctx,0)+dprev[kind].get(ctx,0)+8)
        out+=number*math.log(local)
    return out/max(1,sum(ng.values()))


def schedule(new,old,ratio):
    steps=[]
    ci=ri=0
    while len(steps)<120:
        steps.append(new[ci%len(new)]);ci+=1
        for _ in range(ratio):
            steps.append(old[ri%len(old)]);ri+=1
    assert len(steps)==120
    return steps


def partition(rows):
    return unique([r for r in rows if r["type"]=="pair" and int(fingerprint(question(r)),16)%4==0
                   and code(r["output"]) and code(r["rejected"]) and code(r["output"])!=code(r["rejected"])],
                  lambda r:(question(r),code(r["output"]),code(r["rejected"])))


def main(g55,g56,target_bytes=None):
    old,newer=([json.loads(line) for line in p.read_text().splitlines()] for p in (g55,g56))
    records={r["generation"]:r for r in map(json.loads,(ROOT/"training/reports/generations.jsonl").read_text().splitlines())}
    g=records["g55"]
    assert g["kept"] and set(g["body_after"])==set(records["g56"]["body_before"])
    actors={"t80+"+w for w in g["body_after"]+[g["trunk"]]}
    trunk="t80+"+g["trunk"]
    fresh=[r for r in newer if r.get("gen")=="g56"]
    oldpairs=partition(old)
    newpairs=partition(fresh)
    old_questions={question(r) for r in old}
    newpairs=[r for r in newpairs if question(r) not in old_questions]
    panels={"old":oldpairs,"new":newpairs}
    keys={code(r[k]) for rs in panels.values() for r in rs for k in ("output","rejected")}
    def eligible(r):
        return (int(fingerprint(question(r)),16)%4!=0 and code(r["output"]) not in keys
                and r.get("kind") and r["type"] in ("first","fix"))
    positives=lambda rs:unique([r for r in rs if eligible(r) and (
        (r.get("who")=="lesson") or (usable(r) and r.get("who") in actors))],identity)
    base=positives(old)
    incoming=sorted(positives(fresh),key=identity)
    replay=reservoir([r for r in accepted(self_rows(old,actors)) if eligible(r)])
    assert incoming and replay and oldpairs and newpairs
    router=Router(base)
    b=Counts()
    for r in base:
        b.add(r,120/len(base))
    score_rows={slice_name:[(r,router.predict(question(r))) for r in rs] for slice_name,rs in panels.items()}
    results={}
    for arm,ratio in (("frozen",None),("new_only",0),("replay_2to1",2),("replay_4to1",4)):
        if ratio is None:
            steps=[]
        else:
            steps=schedule(incoming,replay,ratio)
        # A byte is one target token in this character model. Host time and 8B tokenizer costs can differ.
        replay_ids = {id(row) for row in replay}
        targets = []
        available = target_bytes
        partial_rows = 0
        for row in steps:
            if available == 0:
                break
            target = code(row["output"]).encode()
            if available is not None:
                partial_rows += len(target) > available
                target = target[:available]
                available -= len(target)
            targets.append((row, target))
        if steps and target_bytes is not None and available:
            raise ValueError("target budget exceeds the planned row sequence")
        exposure = {"partial_rows": partial_rows}
        for source, is_replay in (("old", True), ("new", False)):
            dose = [(row, t) for row, t in targets if (id(row) in replay_ids) == is_replay]
            exposure[source] = len(dose)
            exposure[source + "_distinct"] = len({identity(row) for row, _ in dose})
            exposure[source + "_target_bytes"] = sum(len(t) for _, t in dose)
        for fade in ([1.] if not steps else [.98,1.]):
            extra=Counts()
            for i, (row, target) in enumerate(targets):
                extra.add(row, fade ** (len(targets) - 1 - i), target)
            scores={}
            for label,rs in score_rows.items():
                out=[]
                for r,k in rs:
                    a,c=(log_likelihood(code(r[key]),k,b,fade**len(targets),extra) for key in ("output","rejected"))
                    out.append({"task_sha256":fingerprint(question(r)),"chosen_sha256":fingerprint(code(r["output"])),
                                "rejected_sha256":fingerprint(code(r["rejected"])),"producer_cohort":r.get("gen"),
                                "correct":a>c,"tie":a==c,"per_byte_logprob_margin":round(a-c,8)})
                scores[label]={"pairs":len(out),"questions":len({e["task_sha256"] for e in out}),
                               "correct":sum(e["correct"] for e in out),"ties":sum(e["tie"] for e in out),"observed":out}
            results[f"{arm}_{fade}"]={"exposure":exposure,"slices":scores}
    signatures=[{"question_sha256":fingerprint(question(r)),"program_sha256":fingerprint(code(r["output"])),
                 "kind":r["kind"],"who":r["who"],"collection":r.get("gen"),"agreed":r.get("agreed"),
                 "seed":r["seed"],"member":r.get("member")} for r in replay]
    def pair_count(rs):
        p=[r for r in rs if r["type"]=="pair"]
        return {"rows":len(p),"questions":len({question(r) for r in p}),
                "full_seat_verdicts":sum("members" in r for r in p),"rejected_actor_named":sum(bool(r.get("rejected_who")) for r in p)}
    return {"g55_sha256":sha256(g55.read_bytes()).hexdigest(),"g56_sha256":sha256(g56.read_bytes()).hexdigest(),
            "prior_generation":g["generation"],"prior_kept":g["kept"],"new_generation_kept":records["g56"]["kept"],
            "prior_current_trunk":trunk,"old_candidates":census(old,actors,trunk),"fresh_candidates":census(fresh,actors,trunk),
            "old_and_fresh_candidates":census(newer,actors,trunk),"base_rows":len(base),"new_rows":len(incoming),
            "new_source_counts":dict(Counter(r.get("who") for r in incoming)),
            "eligible_verified_replay":len(replay),"reservoir_signatures":signatures,"target_byte_limit":target_bytes,
            "preference_archive":{"cumulative_g55":pair_count(old),"fresh_g56":pair_count(fresh)},
            "old_eval_questions_excluded_from_new":len(partition(fresh))-len(newpairs),
            "results":results}


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--g55",type=Path,required=True)
    p.add_argument("--g56",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--target-bytes", type=int, help="truncate the final row to match a positive target-byte budget")
    args=p.parse_args()
    if args.target_bytes is not None and args.target_bytes < 1:
        p.error("--target-bytes must be positive")
    result=main(args.g55,args.g56,args.target_bytes)
    raw = (json.dumps(result, indent=2)+"\n").encode()
    args.out.write_bytes(gzip.compress(raw, mtime=0) if args.out.suffix == ".gz" else raw)
    print("base, new, replay",result["base_rows"],result["new_rows"],result["eligible_verified_replay"])
    for name,info in result["results"].items():
        print(name,[(k,v["correct"],v["pairs"]) for k,v in info["slices"].items()])
