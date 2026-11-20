"""Post-audit guard. Every written literal call must be covered exactly once."""
from collections import Counter
import json
import re

from training.experiments.verified_growth.file_relay import relay
from . import intake


START = re.compile(rf"(?<!\w){relay.IDENT}[ \t]*\(")
COMPLETE = re.compile(rf"({relay.IDENT})[ \t]*\(.*\)", re.S)


def end_of_call(text, begin):
    depth, quoted, escaped = 1, None, False
    for idx in range(begin, len(text)):
        char = text[idx]
        if quoted is not None:
            if escaped:
                escaped=False
            elif char=="\\":
                escaped=True
            elif char==quoted:
                quoted=None
        elif char in ("'", '"'):
            quoted=char
        elif char=="(":
            depth+=1
        elif char==")":
            depth-=1
            if depth==0:
                return idx+1
    return None


def signature(call):
    return json.dumps(call,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(",",":"))


def contract(request):
    spec=intake.contract(request)
    if spec is None:
        return None
    _, _, examples, queries=spec
    seen=Counter()
    for start in START.finditer(request):
        end=end_of_call(request,start.end())
        if end is not None:
            candidate=COMPLETE.fullmatch(request[start.start():end])
            call=relay.call_args(candidate) if candidate else None
            if call is not None:
                seen[signature(call)]+=1
    accounted=Counter(signature(c) for c,_ in examples)
    accounted.update(signature(c) for c in queries)
    # Conservatively withhold repeated literal invocations; their separate roles can be ambiguous.
    if any(n>1 for n in seen.values()) or seen!=accounted:
        return None
    return spec


def propose(request,files,programs,visible_report,*,guest=None):
    spec=contract(request)
    if spec is None:
        return {"status":"abstained","files":{},"text":""}
    return relay.propose(intake.normalized(spec),files,programs,visible_report,guest=guest)
