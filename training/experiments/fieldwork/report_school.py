"""Teach a group-and-aggregate reporting member, then join it to a recovered model-written intake phase."""

import argparse
import itertools
import json
from pathlib import Path

from .campaign import fingerprint, read, save
from .guest import Guest
from .grade import grade
from .stages import assemble, examples
from .work import matches


FORMATS = {"summary.csv": "csv", "audit.json": "json"}


def renderer(group, value, exclude, threshold, strict, order, descend, reverse_ties, count):
    return f"""import json

def solve(x):
    rows = x['snapshot']['kept']
    totals = {{}}
    for row in rows:
        label = row[{group}]
        if label {exclude} x['exclude']:
            continue
        n, mass = totals.get(label, (0, 0))
        totals[label] = (n + 1, mass + row[{value}])
    report = [[label, n, mass] for label, (n, mass) in totals.items() if {threshold} {strict} x['minimum']]
    report.sort(key=lambda r: r[0], reverse={reverse_ties})
    report.sort(key=lambda r: r[{order}], reverse={descend})
    csv = 'zone,count,grams\\n' + ''.join(f'{{label}},{{n}},{{mass}}\\n' for label,n,mass in report)
    audit = {{'conflicts': x['snapshot']['conflicts'], 'kept_count': {count}}}
    return {{'summary.csv': csv, 'audit.json': json.dumps(audit)}}
"""


def teach(demos):
    # Field types determine possible group and value columns, while the public results resolve their roles.
    row = next(r for e in demos for r in e["input"]["snapshot"]["kept"])
    labels = [i for i, v in enumerate(row) if isinstance(v, str)]
    numbers = [i for i, v in enumerate(row) if type(v) is int]
    choices = itertools.product(
        labels,
        numbers,
        ("==", "!="),
        ("n", "mass"),
        (">=", ">"),
        (1, 2),
        (False, True),
        (False, True),
        ("len(rows)", "sum(n for n,_ in totals.values())", "sum(r[1] for r in report)"),
    )
    pool = []
    total = 0
    for rule in choices:
        total += 1
        code = renderer(*rule)
        scope = {}
        exec(code, scope)  # Every executed token comes from the finite family above.
        fn = scope["solve"]
        if all(matches(fn(e["input"]), e["output"], FORMATS) for e in demos):
            pool.append((code, rule, fn))
    survivors = len(pool)
    # In a probe with possible ties, the teacher reveals one observed report only if surviving policies disagree.
    probes = []
    for excluded in ("Alto", "Cove", "Dune"):
        for minimum in (1, 2, 3):
            data = [["R1", 1, "Alto", 4], ["R2", 2, "Bend", 1], ["R3", 5, "Bend", 3], ["R4", 3, "Cove", 4]]
            conflicts = ["R5"]
            x = dict(
                snapshot=dict(kept=data, conflicts=conflicts),
                exclude=excluded,
                minimum=minimum,
                phase="revise",
            )
            outputs = [p[2](x) for p in pool]
            if len({json.dumps(v, sort_keys=True) for v in outputs}) <= 1:
                continue
            groups = sorted({v[2] for v in data} - {excluded})
            rows = []
            for g in groups:
                values = [v[3] for v in data if v[2] == g]
                if len(values) >= minimum:
                    rows.append([g, len(values), sum(values)])
            rows.sort(key=lambda r: (-r[2], r[0]))
            observed = {
                "summary.csv": "zone,count,grams\n" + "".join(",".join(map(str, r)) + "\n" for r in rows),
                "audit.json": json.dumps({"kept_count": len(data), "conflicts": conflicts}),
            }
            probes.append(dict(input=x, observed=observed))
            pool = [p for p, o in zip(pool, outputs) if matches(o, observed, FORMATS)]
    if len(pool) != 1:
        raise ValueError(f"expected one identified reporting rule, found {len(pool)}")
    code, rule, _ = pool[0]
    return dict(
        source=code,
        digest=fingerprint(code),
        family_size=total,
        public_examples=len(demos),
        survivors_before_probes=survivors,
        probes=probes,
        rule=rule,
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for k in ("intake", "out", "sdk"):
        p.add_argument("--" + k, type=Path, required=True)
    args = p.parse_args()
    intake = read(args.intake)
    if fingerprint(intake["source"]) != intake["digest"] or intake["passed"] != intake["public"]:
        raise ValueError("expected a qualified intake fragment")
    report = teach(examples()["revise"])
    program = assemble({"intake": intake, "revise": report})
    save(
        args.out / "program.json",
        dict(source=program, digest=fingerprint(program), intake=intake["digest"], report=report),
    )
    guest = Guest(args.sdk)
    for split in ("public", "exam", "confirmation"):
        row = grade(guest, "ledger", program, split)
        save(args.out / (split + ".json"), row)
        print(split, row["correct"], row["total"], flush=True)


if __name__ == "__main__":
    main()
