"""Fit top-one routes only from verified practice wins. Gate grades are read only by the scorer."""
import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
ACTOR = re.compile(r"t\d+\+g\d+(?:trunk|sources|code|data|words)\d*")


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def prompt_features(task):
    text = " ".join(task.casefold().split())
    return {"prompt": digest(text) if text else None,
            "words": dict(Counter(digest(w)[:20] for w in re.findall(r"[a-z]+", text)))}


def read_zip(source, roots):
    for root in roots:
        path = root / f"{source['id']}.zip"
        if path.exists():
            if hashlib.sha256(path.read_bytes()).hexdigest() != source["sha256"]:
                raise ValueError(f"Changed artifact {source['id']}")
            return ZipFile(path)
    raise FileNotFoundError(source["id"])


def intake(z, prefix):
    from team import parts
    names = set(z.namelist())
    def read(name):
        return z.read(prefix+name).decode() if prefix+name in names else ""
    task = read("members/TASK.md") or read("TASK.md")
    events = [json.loads(line) for line in read("members/events.jsonl").splitlines()]
    actors = []
    for event in events:
        if event["agent"] == "hive" and event["kind"] == "seats":
            _, sep, value = event["msg"].partition(": ")
            if sep:
                proposed = value.split(", ")
                if all(ACTOR.fullmatch(name) for name in proposed):
                    actors = proposed
            break
        if re.fullmatch(r"member\d+", event["agent"]):
            break  # A subsequent roster was not observed before this request.
    if not task.strip():
        reason = "missing request"
    elif len(parts.of_task(task)) > 1:
        reason = "compound"
    elif len(actors) < 2:
        reason = "missing pre-run pair"
    else:
        reason = ""
    return dict(**prompt_features(task), actors=actors, reason=reason), events


def practice_sample(features, events, members):
    if features["reason"]:
        return None, features["reason"]
    seen = {}
    for event in events:
        m = re.fullmatch(r"member(\d+)",event["agent"])
        if m and event["kind"] == "answer":
            seen[int(m[1])] = event["msg"] not in ("no answer","")
    if len(seen) < 2 or not all(seen.values()):
        return None, "fewer than two complete answers or a blank answer"
    checked = {m["member"]:m for m in members if type(m.get("ok")) is bool}
    if len(checked) != len(members) or set(seen) != set(checked):
        return None, "missing or ambiguous member grades"
    actors = features["actors"]
    if any(n<1 or n>len(actors) or checked[n]["who"]!=actors[n-1] for n in checked):
        return None, "not every graded actor matches the initial roster"
    if len(set(checked[n]["who"] for n in checked)) != len(checked):
        return None, "repeated actor in the same practice job"
    winners = [m["who"] for m in members if m["ok"]]
    if len(winners)!=1:
        return None, "multiple winners" if winners else "no winner"
    return winners[0], "sole verified winner"


def collect(roots):
    practice, queries, grades = [],{},{}
    for source in json.loads((HERE/"practice-artifacts.json").read_text()):
        gen = source["generation"]
        shard = int(source["file"].split("-")[-1])
        seed = 10_000_000 + gen*100 + shard
        with read_zip(source, roots) as z:
            matches = sorted(n for n in z.namelist() if re.fullmatch(rf"practice_{seed}/[^/]+/exam.json",n))
            for name in matches:
                prefix = name.removesuffix("exam.json")
                features, events = intake(z,prefix)
                verdict = json.loads(z.read(name))
                win, status = practice_sample(features, events, verdict.get("members",[]))
                practice.append(dict(generation=gen, prompt=features["prompt"], words=features["words"] if win else {},
                                     actor=win, status=status))
    for source in json.loads((HERE.parent/"minority/artifacts.json").read_text()):
        gen = int(source["generation"][1:])
        arm, shard = source["name"].split("-")[-2:]
        seed = 20_000_000 + gen*10 + int(shard)
        with read_zip(source,roots) as z:
            matches = sorted(n for n in z.namelist() if re.fullmatch(rf"exam_{seed}_mixed/[ehc]{seed}_\d\d/exam.json",n))
            if len(matches)!=8: raise ValueError(f"expected eight fresh requests: {source['id']}")
            for n in matches:
                prefix = n.removesuffix("exam.json")
                features,_ = intake(z,prefix)
                task = prefix.rstrip("/").split("/")[-1]
                key = f"g{gen}/{arm}/{task}"
                queries[key] = dict(generation=gen,arm=arm,**features)
                result = json.loads(z.read(n))
                assert type(result["ok"]) is bool and result["id"]==task
                grades[key] = dict(final=result["ok"],members=[
                    [m["member"],m["who"],m["ok"]] for m in result.get("members",[]) if type(m.get("ok")) is bool])
    return dict(practice=practice, queries=queries, grades=grades)


def normalize(values):
    norm = math.sqrt(sum(v*v for v in values.values()))
    return {k:v/norm for k,v in values.items()} if norm else {}


class Chooser:
    def __init__(self, practice):
        grouped = defaultdict(dict)
        for row in practice:
            if row["actor"]:
                grouped[row["prompt"]][row["actor"]] = row["words"]
        self.conflicting = sum(len(group)>1 for group in grouped.values())
        docs = [next(iter(group.items())) for group in grouped.values() if len(group)==1]
        self.count = Counter(actor for actor, _ in docs)
        freq = Counter(w for _, words in docs for w in words)
        self.idf = {w:1+math.log((len(docs)+1)/(f+1)) for w,f in freq.items()}
        sums = defaultdict(Counter)
        for actor,words in docs:
            sums[actor].update(self.vector(words))
        self.prototypes = {a:normalize(v) for a,v in sums.items()}

    def vector(self, words):
        return normalize({w:(1+math.log(n))*self.idf[w] for w,n in words.items() if w in self.idf})

    def choose(self, words, actors):
        first,second = actors[:2]
        if first==second: return 1,1,"same known identity"
        if not all(a in self.prototypes for a in (first,second)):
            missing = "both" if all(a not in self.prototypes for a in (first,second)) else (
                "first" if first not in self.prototypes else "second")
            return 1,1,"unseen "+missing
        v = self.vector(words)
        def similarity(actor):
            return sum(n*self.prototypes[actor].get(w,0.0) for w,n in v.items())
        left,right = similarity(first),similarity(second)
        choice = 2 if right>left else 1
        reason = "no word evidence" if not max(left,right) else "tie" if left==right else "supported"
        frequency = 2 if self.count[second]>self.count[first] else 1
        return choice,frequency,reason


def decisions(data):
    """Uses only historical verified practice, the public question and the two pre-run actor names."""
    train = data["practice"]
    dev_exact = {q["prompt"] for q in data["queries"].values() if q["generation"]<=52 and q["prompt"]}
    choices, fits = {},{}
    for gen in range(50,57):
        end = min(gen,52)
        samples = [r for r in train if r["generation"]<=end]
        fit_exact = {r["prompt"] for r in samples if r["prompt"]}
        router = Chooser(samples)
        fits[str(gen)] = dict(verified_unique_documents=sum(router.count.values()),actors=dict(sorted(router.count.items())),
                              competing_winners_same_prompt=router.conflicting)
        for key, q in data["queries"].items():
            if q["generation"]!=gen: continue
            reason = q["reason"]
            if not reason and q["prompt"] in fit_exact: reason = "practice exact overlap"
            if not reason and gen>52 and q["prompt"] in dev_exact: reason = "development gate exact overlap"
            if reason:
                choices[key] = dict(skip=reason)
                continue
            word, count, support = router.choose(q["words"],q["actors"])
            choices[key] = dict(word=word,count=count,support=support)
    return choices,fits


def score(data, choices, fits):
    panels = {}
    for split,gens in (("development",range(50,53)),("evaluation",range(53,57))):
        for arm in ("after","before"):
            reasons,support,known,scores,matched_support = Counter(),Counter(),Counter(),Counter(),Counter()
            for key,c in choices.items():
                q,g = data["queries"][key],data["grades"][key]
                if q["generation"] not in gens or q["arm"]!=arm:continue
                known["jobs"]+=1
                if "skip" in c:
                    reasons[c["skip"]]+=1
                    continue
                known["eligible"]+=1
                support[c["support"]]+=1
                results={}
                for idx,actor,right in g["members"]:
                    if idx in (1,2) and q["actors"][idx-1]==actor:
                        results[idx] = right if idx not in results else None
                if type(results.get(1)) is bool:
                    known["observed_first"]+=1
                    known["observed_first_right"]+=results[1]
                if type(results.get(2)) is bool:
                    known["observed_second"]+=1
                if any(type(results.get(i)) is not bool for i in (1,2)):
                    reasons["missing or unmatched actual first/second receipt"]+=1
                    continue
                known["matched"]+=1
                matched_support[c["support"]]+=1
                scores["delivery"]+=g["final"]
                scores["oracle"]+=any(results.values())
                for name,idx in (("first",1),("second",2),("count",c["count"]),("word",c["word"])):
                    scores[name]+=results[idx]
                    if idx==2:
                        scores[name+"_switched"]+=1
                        scores[name+"_gained"]+=results[2] and not results[1]
                        scores[name+"_lost"]+=results[1] and not results[2]
            panels[split+"_"+arm] = dict(coverage=dict(known), exclusions=dict(reasons), support=dict(support),
                                          matched_support=dict(matched_support), scores=dict(scores))
    return dict(practice_status=dict(Counter(r["status"] for r in data["practice"])),fits=fits,panels=panels)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archives",type=Path,action="append")
    p.add_argument("--ledger",type=Path,default=HERE/"records.json.gz")
    p.add_argument("--out",type=Path,default=HERE/"results.json")
    args=p.parse_args()
    if args.archives:
        ledger=collect(args.archives)
        args.ledger.write_bytes(gzip.compress(json.dumps(ledger,sort_keys=True,separators=(",",":")).encode(),mtime=0))
    ledger=json.loads(gzip.decompress(args.ledger.read_bytes()))
    picks,fits=decisions(ledger)
    args.out.write_text(json.dumps(score(ledger,picks,fits),indent=2,sort_keys=True)+"\n")
