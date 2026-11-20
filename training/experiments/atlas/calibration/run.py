"""Evaluate frozen answer/abstention rules on published four-worker archived panels."""
import argparse
from collections import Counter, defaultdict
from hashlib import sha256
from math import ceil, comb, exp, log, sqrt
from pathlib import Path
import gzip
import json
import sys

HERE = Path(__file__).resolve().parent
PULSE = HERE.parent / "pulse"
sys.path.insert(0, str(PULSE))
import policy

TARGET = 0.90
MARGINS = range(5)


def read(name):
    return json.loads(gzip.decompress((PULSE / name).read_bytes()))


def votes(row):
    return [policy.key(s["answer"]) for s in row["seats"]]


def proposal(row):
    v = votes(row)
    counts = Counter(x for x in v if x is not None)
    if not counts:
        return None, 0, 0.0
    ranked = counts.most_common()
    group, top = ranked[0]
    margin = top - (ranked[1][1] if len(ranked) > 1 else 0)
    return v.index(group), margin, (1 + margin / 4) / 2


def lower_or_upper(errors, n, alpha, *, upper=True):
    """Exact binomial tail inversion. For an upper bound P_p(X<=x)=alpha."""
    if not n:
        return None
    if not upper:
        return 1 - lower_or_upper(n-errors, n, alpha)
    if errors == n:
        return 1.0
    a, b = 0.0, 1.0
    for _ in range(70):
        mid = (a + b) / 2
        prob = sum(comb(n, i) * mid**i * (1-mid)**(n-i) for i in range(errors+1))
        if prob > alpha:
            a = mid
        else:
            b = mid
    return (a+b)/2


def interval(k, n):
    if not n:
        return None
    return [round(lower_or_upper(k, n, .025, upper=False), 6), round(lower_or_upper(k, n, .025), 6)]


def quantile(values):
    k = ceil((len(values) + 1) * TARGET)
    return sorted(values)[k-1] if k <= len(values) else None


def binary_set(p, q):
    if q is None:
        return [False, True]
    return [y for y, score in ((False, p), (True, 1-p)) if score <= q]


def calibration(rows, grades):
    residuals, by_seed, audit = [], defaultdict(list), []
    for row in rows:
        i, margin, p = proposal(row)
        y = i is not None and grades[row["id"]]["recorded_seat_verdicts"][i]
        residual = 1-p if y else p
        residuals.append(residual)
        by_seed[row["seed"]].append(residual)
        audit.append(dict(id=row["id"], index=i, margin=margin, p=p, truth=y, nonconformity=residual))
    grid, passing = [], []
    for m in MARGINS:
        kept = [r for r in audit if r["index"] is not None and r["margin"] >= m]
        wrong = sum(not r["truth"] for r in kept)
        upper = lower_or_upper(wrong, len(kept), .05/len(MARGINS))
        certified = upper is not None and upper <= 1-TARGET
        if certified:
            passing.append(m)
        grid.append(dict(margin=m, n=len(kept), errors=wrong, upper_adjusted=upper, certified=certified))
    return dict(q_job=quantile(residuals), q_seed=quantile([max(v) for v in by_seed.values()]),
                seed_maxima={str(k):max(v) for k,v in by_seed.items()}, chosen_margin=min(passing) if passing else None,
                grid=grid, audit=audit)


def norm(text):
    return " ".join(text.casefold().split())


def history_archive(row, history, grades):
    acts = [s["who"] for s in row["seats"]]
    counts = {w:[0, 0] for w in acts}
    for past in history:
        if past["kind"] != row["kind"] or norm(past["prompt"]) == norm(row["prompt"]):
            continue
        for s, ok in zip(past["seats"], grades[past["id"]]["recorded_seat_verdicts"]):
            if s["who"] in counts:
                counts[s["who"]][0] += int(ok)
                counts[s["who"]][1] += 1
    candidates = [(i,(counts[w][0]+1)/(counts[w][1]+2)) for i,w in enumerate(acts) if counts[w][1]>=2]
    winner = max(candidates,key=lambda kv:kv[1])[0] if candidates else 0
    return winner, not candidates, counts


def hedge(history, grades):
    eta = sqrt(2*log(4)/len(history))
    mistakes = [sum(not grades[r["id"]]["recorded_seat_verdicts"][i] for r in history) for i in range(4)]
    weights = [exp(-eta*n) for n in mistakes]
    total = sum(weights)
    return dict(eta=eta, mistakes=mistakes, weights=[w/total for w in weights])


def policy_decisions(row, cfg, history, prior_grades, weights):
    v = votes(row)
    seat, m, p = proposal(row)
    answers = [s["answer"] for s in row["seats"]]
    dec = {}
    def put(name, idx, seats, **details):
        dec[name] = dict(index=idx, seats=seats, **details)
    def one(idx):
        return idx if v[idx] is not None else None
    put("after_trunk", one(0), 1)
    put("before_trunk", one(2), 1)
    put("always_plurality", seat, 4)
    for n in (2,3,4):
        put(f"agreement_{n}", *policy.fixed(answers, n))
    put("reserve", *policy.reserve(answers))
    for name, q in (("conformal_job",cfg["q_job"]), ("conformal_seed",cfg["q_seed"])):
        labels = binary_set(p, q)
        put(name,seat if labels == [True] else None,4,prediction_set=labels)
    threshold = cfg["chosen_margin"]
    put("risk_certified",seat if threshold is not None and m>=threshold else None,4)
    for threshold in MARGINS:
        put(f"margin_{threshold}",seat if m>=threshold else None,4)
    idx, fallback, records = history_archive(row,history,prior_grades)
    put("kind_identity_archive",one(idx),1,choice=idx,defaulted=fallback,training_counts=records)
    weighted = Counter()
    for val,w in zip(v,weights):
        if val is not None:
            weighted[val] += w
    idx = v.index(max(weighted,key=weighted.get)) if weighted else None
    put("hedge_roles",idx,4)
    return dict(id=row["id"],tid=row["tid"],kind=row["kind"],seed=row["seed"],proposal=seat,margin=m,p=p,
                prior_identical_prompt=any(norm(row["prompt"])==norm(prev["prompt"]) for prev in history),
                decisions=dec)


def evaluate(predictions, outcomes):
    stats=defaultdict(Counter)
    receipts=[]
    for r in predictions:
        grade=outcomes[r["id"]]
        truth=grade["recorded_seat_verdicts"]
        y=r["proposal"] is not None and truth[r["proposal"]]
        oracle=any(truth)
        verdicts={}
        for name,act in r["decisions"].items():
            idx=act["index"]
            verdict="withheld" if idx is None else ("correct" if truth[idx] else "wrong")
            k = stats[name]
            k[verdict] += 1
            k["seats"] += act["seats"]
            if "prediction_set" in act:
                labels=act["prediction_set"]
                k["set_covered"] += y in labels
                k[f"set_size_{len(labels)}"] += 1
            if "defaulted" in act:
                k["defaulted"] += act["defaulted"]
            verdicts[name]=verdict
        stats["oracle_four"]["correct" if oracle else "withheld"]+=1
        stats["oracle_four"]["seats"]+=4
        actual=grade["actual_after"]
        original="withheld" if not actual["released"] else ("correct" if actual["ok"] else "wrong")
        stats["actual_after"][original]+=1
        stats["actual_after"]["seats"]+=actual["completed_workers"]
        receipts.append(dict(id=r["id"],proposal_correct=y,recorded_correct=truth,actual_after=original,
                             oracle_has_answer=oracle,outcomes=verdicts))
    summary={}
    for name,k in stats.items():
        n = len(predictions)
        delivered = k["correct"] + k["wrong"]
        res=dict(k)
        res.update(total=n,correct=k["correct"],wrong=k["wrong"],withheld=k["withheld"],released=delivered,
                   coverage=round(delivered/n,4) if n else None,wrong_per_task=round(k["wrong"]/n,4) if n else None,
                   selective_risk=round(k["wrong"]/delivered,4) if delivered else None,
                   selective_risk_iid_ci95=interval(k["wrong"],delivered),
                   coverage_iid_ci95=interval(delivered,n))
        if "set_covered" in k:
            res["set_coverage"]=round(k["set_covered"]/n,4)
            res["set_coverage_iid_ci95"]=interval(k["set_covered"],n)
        summary[name]=res
    return summary,receipts


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    rows=read("panels.json.gz")
    assessment=read("assessment.json.gz")
    dev,cal,test=([r for r in rows if r["generation"]==g] for g in ("g50","g51","g52"))
    assert [len(dev),len(cal),len(test)]==[27,27,28]
    assert len({r["id"] for r in rows})==len(rows)==len(assessment)
    assert all([(s["arm"],s["seat"]) for s in r["seats"]]==[("after",1),("after",2),("before",1),("before",2)] for r in rows)
    prior=dev+cal
    training={r["id"]:assessment[r["id"]] for r in prior}
    cfg=calibration(cal,training)
    h=hedge(prior,training)
    preds=[policy_decisions(r,cfg,prior,training,h["weights"]) for r in test]
    # All predictions are materialized before any test verdict is looked up.
    frozen=sha256(json.dumps(preds,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    held={r["id"]:assessment[r["id"]] for r in test}
    summary,receipts=evaluate(preds,held)
    fresh=[r for r in preds if not r["prior_identical_prompt"]]
    fresh_results,_=evaluate(fresh,held)
    wrong_unanimous=[r["id"] for r,score in zip(preds,receipts) if r["margin"]==4 and not score["proposal_correct"]]
    arm_pairs={g:sorted({(r["seats"][0]["who"],r["seats"][2]["who"]) for r in rr}) for g,rr in (("g50",dev),("g51",cal),("g52",test))}
    artifacts={f:sha256((PULSE/f).read_bytes()).hexdigest() for f in ("panels.json.gz","assessment.json.gz","policy.py","artifacts.json","cohort.json")}
    out=dict(source_sha256=artifacts,protocol_sha256=sha256((HERE/"protocol.md").read_bytes()).hexdigest(),prediction_sha256=frozen,
             sample_sizes=dict(development=len(dev),calibration=len(cal),test=len(test),fresh_prompts=len(fresh)),
             lineage_pairs=arm_pairs,calibration=cfg,hedge=h,summary=summary,prior_prompt_excluded=fresh_results,
             unanimous_wrong_test_ids=wrong_unanimous,predictions=preds,receipts=receipts)
    args.out.write_text(json.dumps(out,indent=2)+"\n")


if __name__=="__main__":
    main()
