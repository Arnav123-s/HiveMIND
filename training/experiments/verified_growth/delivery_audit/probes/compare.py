"""Compare two submitted files on authorized additional inputs, then separately grade any publication."""
import argparse
from collections import Counter
from hashlib import sha256
import json
import os
from pathlib import Path
import re

from training.experiments.fieldwork.guest import Guest
from training.experiments.verified_growth.delivery_audit.inspect_run import run_handoff
from .panel import panel

HERE = Path(__file__).resolve().parent


def digest(data):
    return sha256(data).hexdigest()


def admitted(x, domain):
    if domain in ("signed", "digit"):
        lo, hi = (-20, 20) if domain == "signed" else (0, 9)
        return type(x) is int and lo <= x <= hi
    if domain == "text":
        return type(x) is str and len(x) <= 256 and re.fullmatch(r"[A-Za-z ]*", x) is not None
    if not isinstance(x, list) or len(x) > 8:
        return False
    if domain == "word_list":
        return all(type(word) is str and re.fullmatch(r"[A-Za-z]+", word) for word in x)
    lo = 0 if domain == "nonnegative_list" else -20
    return domain in ("nonnegative_list","signed_list") and all(type(n) is int and lo <= n <= 20 for n in x)


def evaluate(guest, source, function, inputs):
    if not re.fullmatch(r"[a-z][a-z0-9_]*", function):
        raise ValueError("invalid function name")
    guest_source = source + f"\ndef solve(arg):\n    return {function}(arg)\n"
    return guest.run(guest_source, inputs)[:2]


def token(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def observe(guest, first, other, function, domain, probes):
    inputs = [x for x in probes if admitted(x, domain)]
    rejected = [x for x in probes if not admitted(x, domain)]
    evidence = dict(inputs=inputs,rejected=rejected,observations=[],fuel=0)
    if other is None or not inputs:
        return dict(evidence, status="unknown", reason="single worker" if other is None else "no admissible probes")
    for program in (first, other):
        responses, fuel = evaluate(guest, program, function, inputs)
        evidence["fuel"] += fuel
        evidence["observations"].append(responses)
    unknown = False
    for x, a, b in zip(inputs, *evidence["observations"], strict=True):
        if "value" not in a or "value" not in b:
            unknown = True
        elif token(a["value"]) != token(b["value"]):
            return dict(evidence, status="contradicted", witness={"input":x, "first":a["value"], "second":b["value"]})
    if unknown:
        return dict(evidence,status="unknown",reason="incomplete guest observations")
    return dict(evidence,status="matching_observations")


def submit(guest):
    rows = []
    for case in panel():
        function, programs = case["function"], case["programs"]
        primary = case["primary"]
        assert admitted(primary, case["domain"])
        outputs = [evaluate(guest, src, function, [primary])[0][0]["value"] for src in programs]
        assert len(set(map(token, outputs))) == 1
        printed = str(outputs[0])
        workers = [(printed,program) for program in programs]
        if len(workers) == 1:
            workers = [("",None),("",None),*workers]
        question = f"Write a Python module and save it as {function}.py. {case['contract']} Print {function}({primary!r})."
        original = run_handoff(question, workers)
        observed = observe(guest, programs[0], programs[1] if len(programs) > 1 else None, function, case["domain"], case["probes"])
        rows.append(dict(case=case["key"],function=function,actual_primary_outputs=outputs,
                         sources=[digest(src.encode()) for src in programs], original=original, evidence=observed,
                         pass_veto=bool(original["agreed"] and observed["status"]!="contradicted"),
                         has_matching_probes=bool(original["agreed"] and observed["status"]=="matching_observations")))
    return dict(panel_sha256=digest((HERE/"panel.py").read_bytes()),protocol_sha256=digest((HERE/"protocol.md").read_bytes()),rows=rows)


def decisions_without_metering(doc):
    rows = []
    for row in doc["rows"]:
        evidence = {k: v for k, v in row["evidence"].items() if k != "fuel"}
        rows.append(dict(row, evidence=evidence))
    return dict(doc, rows=rows)


def grade(guest, decisions, keys):
    combined, reports = [], {}
    for row, case in zip(decisions["rows"], panel(), strict=True):
        assert case["key"] == row["case"] and [digest(s.encode()) for s in case["programs"]] == row["sources"]
        cases = keys[case["function"]]
        assert all(admitted(c["input"],case["domain"]) for c in cases)
        exposed = {token(case["primary"]), *map(token, row["evidence"]["inputs"])}
        unexposed = [i for i, c in enumerate(cases) if token(c["input"]) not in exposed]
        scores, disjoint_scores = [], []
        for source in case["programs"]:
            answers, _ = evaluate(guest, source, case["function"], [c["input"] for c in cases])
            passed = ["value" in r and token(r["value"]) == token(c["expected"])
                      for r, c in zip(answers, cases, strict=True)]
            scores.append(sum(passed))
            disjoint_scores.append(sum(passed[i] for i in unexposed))
        all_pass = scores[0] == len(cases)
        for policy,sent in (("stock",row["original"]["agreed"]),("negative_only",row["pass_veto"]),
                            ("require_matched",row["has_matching_probes"])):
            reports.setdefault(policy,Counter())["correct" if sent and all_pass else "wrong" if sent else "withheld"] += 1
        combined.append(dict(case=row["case"],test_cases=len(cases),hidden_passes=scores,
                             additional_unexposed_cases=len(unexposed), additional_unexposed_passes=disjoint_scores,
                             stock_first_passes=all_pass,observation=row["evidence"]["status"]))
    return dict(outcomes=reports,grades=combined)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk",required=True,type=Path)
    parser.add_argument("--decisions",required=True,type=Path)
    parser.add_argument("--keys",type=Path)
    parser.add_argument("--grades",type=Path)
    args=parser.parse_args()
    os.environ["RAYON_NUM_THREADS"]="1"
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    guest=Guest(args.sdk)
    if args.keys is None:
        doc=submit(guest)
        args.decisions.write_text(json.dumps(doc,indent=2)+"\n")
        print(Counter(r["evidence"]["status"] for r in doc["rows"]),flush=True)
    else:
        if not args.grades:
            parser.error("grading requires --grades")
        original=json.loads(args.decisions.read_bytes())
        # Check input/source and recorded decision integrity before opening any efficacy keys.
        # WASI instruction consumption can vary across instances with identical outcomes.
        if decisions_without_metering(submit(guest)) != decisions_without_metering(original):
            raise ValueError("sealed decisions changed")
        graded=grade(guest,original,json.loads(args.keys.read_bytes()))
        graded.update(decisions_sha256=digest(args.decisions.read_bytes()),keys_sha256=digest(args.keys.read_bytes()))
        args.grades.write_text(json.dumps(graded,indent=2)+"\n")
        print(graded["outcomes"])


if __name__=="__main__":
    main()
