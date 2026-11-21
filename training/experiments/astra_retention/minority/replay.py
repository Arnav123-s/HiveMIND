"""Replay predeclared switches on fresh gate archives; skip sealed exam entries."""
import argparse
from collections import Counter
from itertools import combinations
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
NUMBERS = dict(one=1, two=2, three=3, four=4, five=5, six=6, seven=7, eight=8, nine=9, ten=10)
LINE_COUNT = re.compile(r"\bexactly\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:non[- ]?empty\s+)?lines?\b", re.I)
JSON_ONLY = re.compile(r"\b(?:reply|answer|respond|return|output)\s+(?:only\s+(?:with|in|as)\s+(?:valid\s+)?json|(?:in\s+)?(?:valid\s+)?json\s+only)\b", re.I)
CONFIRM = re.compile(r"\b(?:two gave the same values|two of them agreed|two members agreed)\b", re.I)
RUN = re.compile(r"\bexit (-?\d+)\b")
FILE_UNCERTAIN = re.compile(r"\b(?:write|save|create|submit)\b[^.\n]{0,80}\b(?:file|module)\b", re.I)


def contract_violations(task, answer):
    failed = set()
    counts = {NUMBERS[s.lower()] if not s.isdigit() else int(s) for s in LINE_COUNT.findall(task)}
    if len(counts) == 1 and len([l for l in answer.splitlines() if l.strip()]) != counts.pop():
        failed.add("line_count")
    if JSON_ONLY.search(task):
        try:
            json.loads(answer, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        except (ValueError, RecursionError):
            failed.add("json")
    return failed


def observed(z, prefix):
    from team import parts, solo
    from training.hive_bench import _body

    names = set(z.namelist())
    def read(suffix):
        return z.read(prefix + suffix).decode() if prefix + suffix in names else ""
    task = read("members/TASK.md").strip()
    report = read("REPORT.md")
    final = _body(report) if report else ""
    confirmation = report.partition("\n## How it was checked")[2].split("\n## ", 1)[0]
    confirmed = bool(final) and not final.startswith(("Not confirmed", "No member")) and bool(CONFIRM.search(confirmation))
    files = None if not task else bool(solo.wanted(task) or FILE_UNCERTAIN.search(task))
    events = [json.loads(line) for line in read("members/events.jsonl").splitlines() if line.strip()]
    seat_info = {}
    late_retry = any(e["kind"] == "asked" for e in events)
    for event in events:
        m = re.fullmatch(r"member(\d+)",event["agent"])
        if not m:
            continue
        i = int(m[1])
        seat = seat_info.setdefault(i, dict(answer="", failed=0, hints=0, runs=0, incomplete=False))
        kind, msg = event["kind"], event["msg"]
        if kind == "run":
            exit_status = RUN.search(msg)
            if exit_status:
                seat["runs"] += 1
                seat["failed"] += int(exit_status[1]) != 0
            else:
                seat["incomplete"] = True
        elif kind == "hint":
            seat["hints"] += 1
        elif kind == "answer":
            seat["answer"] = msg if msg != "no answer" else ""
    answers = {i:v["answer"] for i,v in seat_info.items()}
    seen = [i for i,a in answers.items() if a.strip()]
    row = dict(confirmed=confirmed, report_present=bool(report), file_request=files,
               completed_seats=len(seen), observable_seats=len(answers), votes=[], switch={},
               history={str(i):[v["failed"],v["hints"],v["runs"]] for i,v in seat_info.items()})
    if not report:
        reason = "no report"
    elif not confirmed:
        reason = "no confirmed delivery"
    elif not task or not events:
        reason = "no single-task event stream"
    elif len(parts.of_task(task)) > 1:
        reason = "compound"
    elif len(answers) != 3 or set(seen) != {1,2,3}:
        reason = "not three complete seated answers"
    elif late_retry or any(len(a) >= 300 for a in answers.values()):
        reason = "truncated answer or later retry"
    else:
        pairs = [(i,j) for i,j in combinations(sorted(answers),2) if solo.same(answers[i],answers[j],task)]
        if len(pairs) != 1:
            reason = "no unique two-to-one printed split"
        else:
            i,j = pairs[0]
            k, = {1,2,3} - {i,j}
            if not (solo.same(final,answers[i],task) and solo.same(final,answers[j],task)) or solo.same(final,answers[k],task):
                reason = "reported answer does not identify the voting pair"
            else:
                reason = "observable split"
                row["votes"]=[i,j,k]
                clean = all(v["runs"] and not v["incomplete"] for v in seat_info.values())
                rank = {s:(v["failed"],v["hints"]) for s,v in seat_info.items()}
                beats = bool(clean and rank[k] < min(rank[i],rank[j]))
                failures = {s:contract_violations(task,a) for s,a in answers.items()}
                witness = bool(failures[i] & failures[j]) and not failures[k]
                row["switch"] = dict(history=beats and not files, contract=witness and not files, both=witness and beats and not files)
    row["reason"] = reason
    return row


def collect(roots):
    rows = []
    for item in json.loads((HERE/"artifacts.json").read_text()):
        path = next((p/f"{item['id']}.zip" for p in roots if (p/f"{item['id']}.zip").exists()),None)
        if path is None or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError(f"missing or changed archive {item['id']}")
        _,_,arm,seat = item['name'].split('-')
        seed = 20_000_000 + int(item['generation'][1:])*10 + int(seat)
        with ZipFile(path) as z:
            fresh = [n for n in z.namelist() if re.fullmatch(rf"exam_{seed}_mixed/[ehc]{seed}_\d\d/exam.json",n)]
            if len(fresh)!=8: raise ValueError(f"{item['name']} {seed} has {len(fresh)} tasks")
            for name in sorted(fresh):
                prefix=name.removesuffix('exam.json')
                # Compute the decision using only runtime data before opening the outcome.
                row=observed(z,prefix)
                grade=json.loads(z.read(name))
                assert grade["id"]==prefix.rstrip('/').rsplit('/',1)[1] and type(grade["ok"]) is bool
                members={str(m["member"]):m["ok"] for m in grade.get("members",[]) if type(m.get("ok")) is bool}
                row.update(generation=item['generation'],arm=arm,id=grade["id"],stock=grade["ok"],members=members)
                rows.append(row)
    return rows


def precision_interval(gains, switches):
    """Two-sided exact 95% binomial interval. Shared prompts and related bodies limit its interpretation."""
    if not switches:
        return None

    def invert(cutoff, probability):
        lo, hi = 0.0, 1.0
        for _ in range(55):
            p = (lo + hi) / 2
            cdf = sum(math.comb(switches, i) * p**i * (1-p)**(switches-i) for i in range(cutoff+1))
            if cdf > probability:
                lo = p
            else:
                hi = p
        return (lo + hi) / 2

    lower = invert(gains-1, 0.975) if gains else 0.0
    upper = invert(gains, 0.025) if gains < switches else 1.0
    return [round(lower, 5), round(upper, 5)]


def scores(rows, selector, allow_both, files=False):
    correct=sum(r["stock"] for r in rows)
    out=dict(stock_correct=correct,correct=correct,switches=0,gains=0,losses=0,both_right=0,both_wrong=0,ungraded_suggestions=0)
    for r in rows:
        if not r["votes"] or (r["file_request"] and not files):
            continue
        grade=r["members"].get(str(r["votes"][2]))
        if selector=="hindsight":
            switch=grade is True and not r["stock"]
        elif selector=="all":
            switch=True
        else:
            switch=r["switch"].get(selector,False) and (selector!="both" or allow_both)
        if not switch: continue
        if grade is None:
            out["ungraded_suggestions"]+=1
            continue
        out["switches"]+=1
        if grade!=r["stock"]:
            out["gains" if grade else "losses"]+=1
        else:
            out["both_right" if grade else "both_wrong"]+=1
    out["correct"]+=out["gains"]-out["losses"]
    out["gain_per_switch_95"] = precision_interval(out["gains"], out["switches"])
    return out


def summarize(rows):
    dev=[r for r in rows if r["arm"]=="after" and r["generation"]<="g52"]
    both=scores(dev,"both",True)
    allow=both["switches"]>=5 and 5*both["gains"]>=4*both["switches"]
    panel={}
    for split,gens in (("development",["g50","g51","g52"]),("evaluation",["g53","g54","g55","g56"])):
        for arm in ("after","before"):
            group=[r for r in rows if r["arm"]==arm and r["generation"] in gens]
            known_right=[r for r in group if not r["stock"] and any(r["members"].values())]
            eligible=[r for r in group if r["votes"]]
            panel[split+"_"+arm]=dict(jobs=len(group),stock_correct=sum(r["stock"] for r in group),
                ungraded_members=sum(not r["members"] for r in group),
                known_worker_right_delivery_wrong=len(known_right),
                of_those_already_confirmed=sum(r["confirmed"] for r in known_right),
                reasons=dict(sorted(Counter(r["reason"] for r in group).items())),
                split_text=sum(not r["file_request"] for r in eligible),split_files=sum(bool(r["file_request"]) for r in eligible),
                missing_minority_grade=sum(str(r["votes"][2]) not in r["members"] for r in eligible),
                arms={s:scores(group,s,allow) for s in ("contract","both","history","all","hindsight")},
                all_splits_including_files=scores(group,"all",False,True))
    return dict(development_qualified=allow,raw_development_double_witness=both,panels=panel)


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archives",type=Path,action="append")
    p.add_argument("--ledger",type=Path,default=HERE/"records.json.gz")
    p.add_argument("--out",type=Path,default=HERE/"results.json")
    args=p.parse_args()
    if args.archives:
        rows=collect(args.archives)
        args.ledger.write_bytes(gzip.compress(json.dumps(rows,sort_keys=True,separators=(",",":")).encode(),mtime=0))
    else:
        rows=json.loads(gzip.decompress(args.ledger.read_bytes()))
    args.out.write_text(json.dumps(summarize(rows),indent=2,sort_keys=True)+"\n")
