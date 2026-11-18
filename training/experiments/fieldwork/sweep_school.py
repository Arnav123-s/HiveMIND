"""Compose a learned interval worker with a finite event-sweep family and a separately qualified file writer."""

import argparse
import csv
import io
import itertools
from pathlib import Path

from .campaign import fingerprint, read, save, tool_source
from .guest import Guest
from .observatory import inspect_delivery, large, reference, specs
from .work import check, load_bank, work


# This is the algorithm family supplied to the learner. The previous school provides the union primitive.
SWEEP = """def sweep(x, rule):
    by_instrument, normalize, clip, inclusive, join = rule
    bins = {}
    lo, hi = x['window']
    for sensor, a, b in x['records']:
        if clip:
            a, b = max(a, lo), min(b, hi)
        if a < b:
            bins.setdefault(sensor if by_instrument else '', []).append([a,b])
    events = {}
    for spans in bins.values():
        for a,b in (skill_merge_runs(spans) if normalize else spans):
            events[a] = events.get(a,0) + 1
            events[b] = events.get(b,0) - 1
    level, prev, rows = 0, None, []
    for t in sorted(events):
        if prev is not None and (level >= x['quorum'] if inclusive else level > x['quorum']):
            rows.append([prev,t])
        level += events[t]
        prev = t
    return skill_merge_runs(rows) if join else rows
"""


def expected(value):
    reader = csv.reader(io.StringIO(value["coverage.csv"]))
    next(reader)
    return [[int(a), int(b)] for a, b in reader]


def learn(guest, member, public, candidates):
    rules = list(itertools.product((False, True), repeat=5))
    if member is None:
        rules = [r for r in rules if not r[1] and not r[4]]
    wrapped = tool_source(
        SWEEP + f"\n_rules={rules!r}\ndef solve(x): return [sweep(x,r) for r in _rules]",
        [member] if member else [],
    )
    inputs = [r["input"] for r in public] + candidates
    matrix = guest.run(wrapped, inputs, fuel=38_000_000_000)[0]
    if any("value" not in r for r in matrix):
        raise RuntimeError("sweep school candidate failed in the guest")
    predictions = [r["value"] for r in matrix]
    remaining = [
        i
        for i in range(len(rules))
        if all(predictions[j][i] == expected(p["output"]) for j, p in enumerate(public))
    ]
    initial = len(remaining)
    observations = []
    while len(remaining) > 1 and len(observations) < 8:
        limits = [len({str(row[i]) for i in remaining}) for row in predictions[len(public) :]]
        index = max(range(len(candidates)), key=lambda j: limits[j])
        if limits[index] < 2:
            break
        x = candidates[index]
        y = expected(reference(x))
        observations.append(dict(input=x, observed=y))
        remaining = [i for i in remaining if predictions[len(public) + index][i] == y]
    if not remaining:
        return dict(qualified=False, size=len(rules), public_survivors=initial, probes=observations)
    rule = rules[remaining[0]]
    code = tool_source(SWEEP + f"\ndef solve(x): return sweep(x,{rule!r})", [member] if member else [])
    return dict(
        qualified=True,
        size=len(rules),
        public_survivors=initial,
        survivors=len(remaining),
        rule=rule,
        probes=observations,
        digest=fingerprint(code),
        source=code,
        parents=[member["digest"]] if member else [],
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for k in ("sdk", "bank", "out"):
        p.add_argument("--" + k, type=Path, required=True)
    p.add_argument("--writers", nargs="*", type=Path, default=[])
    args = p.parse_args()
    g = Guest(args.sdk)
    member = next(r for r in load_bank(args.bank) if r["task"] == "merge_runs")
    _, development = specs(887731)
    candidates = [r["input"] for r in development["validation"]]
    for label, m in (("empty", None), ("school", member)):
        row = learn(g, m, development["examples"], candidates)
        save(args.out / (label + ".json"), row)
        print(label, row["public_survivors"], len(row["probes"]), flush=True)
    # Select a serializer purely by prior independent, same-contract promotion.
    writers = [r for b in args.writers for r in load_bank(b) if r["task"] == "coverage_files"]
    if not row["qualified"]:
        return
    _, audit = specs(991237)
    small = [dict(input=e["input"], output=expected(e["output"])) for e in audit["validation"]]
    score, feedback = check(g, row["source"], small)
    big, answer = large(7993, 991237)
    trial, fuel, seconds = g.run(row["source"], [big], fuel=115_000_000_000)
    save(
        args.out / "interval-exam.json",
        dict(
            correct=score,
            total=len(small),
            feedback=feedback,
            records=len(big["records"]),
            stress_ok=trial[0].get("value") == expected(answer),
            fuel=fuel,
            seconds=seconds,
        ),
    )
    if not writers:
        return
    writer = min(writers, key=lambda r: (-r["validation"], len(r["source"]), r["digest"]))
    pieces = [dict(task="intervals", source=row["source"]), dict(task="render", source=writer["source"])]
    code = tool_source("def solve(x): return skill_render(skill_intervals(x))", pieces)
    final = args.out / "joint"
    receipt = work(audit, g, lambda *a: dict(source=code, usage={"completion_tokens": 0}), final, None, 1)
    inspect_delivery(g, final, receipt, audit, 7993, 991237)
    audited = read(final / "independent.json")
    save(
        args.out / "outcome.json",
        dict(
            qualified=receipt["validated"] == len(audit["validation"])
            and audited["stress_ok"]
            and audited["reopened_filesets"] == len(audit["jobs"]),
            digest=receipt["digest"],
            parents=[row["digest"], writer["digest"]],
        ),
    )
    print("joint", receipt["validated"], len(receipt["jobs"]), flush=True)


if __name__ == "__main__":
    main()
