"""Post-audit control allowing repetitions only when every occurrence is accounted for."""
from collections import Counter

from . import intake, lossless


def contract(request):
    spec=intake.contract(request)
    if spec is None:
        return None
    _, _, examples, queries=spec
    written=Counter()
    for start in lossless.START.finditer(request):
        end=lossless.end_of_call(request,start.end())
        if end is not None:
            match=lossless.COMPLETE.fullmatch(request[start.start():end])
            call=intake.relay.call_args(match) if match else None
            if call is not None:
                written[lossless.signature(call)]+=1
    captured=Counter(lossless.signature(call) for call,_ in examples)
    captured.update(lossless.signature(call) for call in queries)
    return spec if written==captured else None


def propose(request,files,programs,visible_report,*,guest=None):
    spec=contract(request)
    if spec is None:
        return {"status":"abstained","files":{},"text":""}
    return intake.relay.propose(intake.normalized(spec),files,programs,visible_report,guest=guest)
