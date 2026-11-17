"""The kind m_summary: a text summed up in one sentence (writing).

A kind of task in one file (training/kinds/, docs/KINDS.md): its maker draws the task and its check from a seed, and
it has no lesson: the hive is never shown it done.
"""
from training import hive_bench as B
from training.kinds._common import NAMES

KIND = "m_summary"
FAMILY = "writing"
HARD = False
ORDER = 150


def m_summary(r):
    who, what = r.choice(NAMES), r.choice(["bridge", "library", "swimming pool", "market hall"])
    year, months, cost = r.randrange(1921, 1989), r.randrange(4, 15), r.choice(["2.6", "3.4", "4.8", "5.1"])
    street = r.choice(["Elm Street", "Mill Lane", "Harbour Road", "Station Street"])
    text = (f"The Ridgeway {what}, built in {year}, was closed in March for repairs after inspectors found cracks in two support beams. "
            f"The city expects the work to take {months} months and cost {cost} million dollars. Until it reopens, visitors are sent to the "
            f"{street} entrance, says the city engineer {who} Hartmann.")

    def check(run, report):
        body = B._body(report)
        n = len(B._sentences(body))
        ok = n == 1 and what.split()[-1] in body.lower() and any(w in body.lower() for w in ("repair", "closed", "close", "crack"))
        return ok, f"{n} sentence(s); names the {what} and the closing or the repairs: {ok}"
    return "writing", "sum up a text", f"Give me a one-sentence summary of this: {text}", check


make = m_summary
lesson = None
