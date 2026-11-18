"""Fit the rules of two supplied algorithm families from demonstrated input/output behavior."""

import argparse
import itertools
import json
from pathlib import Path

from .campaign import fingerprint, read, save, tool_source
from .cases import static_cases
from .grade import compact, grade
from .guest import Guest


def ordered(rule):
    comparison, target, flag, policy, gap_mode = rule
    return f"""from bisect import bisect_right, bisect_left

def solve(x):
    jobs = sorted(x["jobs"], key=lambda row: row[1])
    ends = [r[1] for r in jobs]
    scores = [[(0, 1), (None, 0)]]
    for i, (start, end, reward, marked) in enumerate(jobs):
        bound = {gap_mode}
        earlier = {comparison}(ends, bound, 0, i)
        best = list(scores[-1])
        for before, (value, ways) in enumerate(scores[earlier]):
            if value is None:
                continue
            after = before ^ {flag}
            total = value + reward
            previous, count = best[after]
            if previous is None or total > previous:
                best[after] = (total, ways)
            elif total == previous:
                best[after] = (total, {policy})
        scores.append(best)
    return list(scores[-1][{target}])
"""


def network(rule, school):
    discount, first_lay, preference, mandatory = rule
    code = f"""from heapq import heappush, heappop

def solve(x):
    n, src, dst = x["n"], x["src"], x["dst"]
    graph = [[] for _ in range(n)]
    for u,v,first,step,last,duration in x["edges"]:
        graph[u].append((v,first,step,last,duration))
    times = [[float("inf"),float("inf")] for _ in range(n)]
    times[src][0] = x["start"]
    queue = [(x["start"],src,0)]
    while queue:
        now,u,used = heappop(queue)
        if now != times[u][used]:
            continue
        wait = {first_lay}
        for v,first,step,last,duration in graph[u]:
            for spend in range(2-used):
                ready = {discount}
                arrive = skill_departure({{"rows":[[ready,first,step,last,duration]]}})[0]
                state = used+spend
                if arrive is not None and arrive < times[v][state]:
                    times[v][state] = arrive
                    heappush(queue,(arrive,v,state))
    choices = {mandatory}
    idx = min(choices,key=lambda j: (times[dst][j], {preference}))
    return [None,None] if times[dst][idx] == float("inf") else [times[dst][idx],idx]
"""
    return tool_source(code, [school])


def variants(name, bank):
    if name == "roster":
        for params in itertools.product(
            ("bisect_left", "bisect_right"),
            (0, 1),
            ("1", "marked"),
            ("1", "(ways + count) % 1000000007"),
            ("start", "start-x['gap']", "start+x['gap']"),
        ):
            yield params, ordered(params)
    else:
        school = next(r for r in bank if r["task"] == "departure" and r["admitted"])
        for params in itertools.product(
            ("now+wait", "now if spend else now+wait", "now+wait if spend else now"),
            ("x['lay'][u]", "0 if u==src else x['lay'][u]"),
            ("j", "-j"),
            ("[0,1]", "[1]"),
        ):
            yield params, network(params, school)


def teach(name, bank):
    public = static_cases(name, "public")
    possible = []
    for params, code in variants(name, bank):
        scope = {"least_squares": None}
        exec(code, scope)  # Only fixed, enumerated grammar source and the induced grid rule execute here.
        fn = scope["solve"]
        if all(fn(x) == answer for x, answer in public):
            possible.append((params, code, fn))
    initial = len(possible)
    observations = []
    # A schoolteacher may be asked about a new demonstration only when candidates predict different answers.
    for _ in range(4):
        if len(possible) < 2:
            break
        options = []
        for x, y in static_cases(name, "promotion"):
            outputs = [json.dumps(f(x)) for _, _, f in possible]
            options.append((len(set(outputs)), x, y, outputs))
        width, x, y, outputs = max(options, key=lambda k: k[0])
        if width == 1:
            break
        observations.append(dict(input=x, observed=y, predictions=sorted(set(outputs))))
        possible = [r for r, s in zip(possible, outputs) if json.dumps(y) == s]
    if not possible:
        raise ValueError("no family program satisfies the public demonstrations")
    params, code, _ = possible[0]
    return dict(
        source=code,
        digest=fingerprint(code),
        parameters=params,
        initial_survivors=initial,
        survivors=len(possible),
        queries=observations,
        public=len(public),
        parents=[] if name == "roster" else [next(r["digest"] for r in bank if r["task"] == "departure")],
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for k in ("sdk", "school", "out"):
        p.add_argument("--" + k, type=Path, required=True)
    args = p.parse_args()
    bank = read(args.school)
    # The executable enumerator accepts only locally generated grammar output, never arbitrary registry code.
    from .induction import align

    expected, _, _ = align(static_cases("departure", "public"))
    if any(r["source"] != expected for r in bank if r["task"] == "departure"):
        raise ValueError("unrecognized school source")
    g = Guest(args.sdk)
    for name in ("roster", "ferry"):
        row = teach(name, bank)
        for split in ("public", "exam", "confirmation"):
            got = grade(g, name, row["source"], split)
            row[split + "_score"] = dict(**compact(got), stress=got["tests"][-1].get("detail"))
        save(args.out / (name + ".json"), row)
        print(name, row["initial_survivors"], len(row["queries"]), row["exam_score"]["correct"], flush=True)


if __name__ == "__main__":
    main()
