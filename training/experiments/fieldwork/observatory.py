"""A new work order using the general runner. Its oracle counts occupied integer ticks directly."""

import argparse
import json
import random
from pathlib import Path

from .campaign import read, save
from .guest import Guest
from .native import generate, server
from .work import check, load_bank, matches, work


MERGE = """Write solve(x) to coalesce coverage intervals for one instrument. x is a list of [start,end] integer times, potentially shuffled, repeated or empty. Ignore intervals with end<=start. Return sorted, disjoint [start,end] rows for the union of these half-open intervals; touching intervals must merge. Time coordinates may be widely separated. Aim for O(n log n)."""
ORDER = """Deliver a two-file radio observatory coverage audit. Input x has 'window':[lo,hi], 'quorum' (positive integer) and 'records':[[instrument,start,end],...]. Records are half-open intervals, may repeat or overlap for the same instrument, and may extend beyond the window. Count DISTINCT instruments observing at the same time after clipping to [lo,hi). Produce every maximal interval where the count is at least quorum. Merge touching qualified spans even when the participating instruments change. Discard empty intervals. Return a dict mapping 'coverage.csv' and 'audit.json' to their file texts. CSV starts start,end with a final newline; rows sorted by start. Audit JSON must have keys 'covered' (total qualifying length) and 'longest' ([start,end] of the longest qualifying interval, earliest on ties, or null). Up to 60,000 records; coordinates can be trillions apart. Do not iterate over the time axis."""


def spans(points):
    rows = []
    for t in sorted(points):
        if rows and rows[-1][1] == t:
            rows[-1][1] += 1
        else:
            rows.append([t, t + 1])
    return rows


def files(rows):
    longest = max(rows, key=lambda r: r[1] - r[0]) if rows else None
    return {
        "coverage.csv": "start,end\n" + "".join(f"{a},{b}\n" for a, b in rows),
        "audit.json": json.dumps({"covered": sum(b - a for a, b in rows), "longest": longest}),
    }


def reference(x):
    lo, hi = x["window"]
    points = [
        t for t in range(lo, hi) if len({name for name, a, b in x["records"] if a <= t < b}) >= x["quorum"]
    ]
    return files(spans(points))


def specs(seed=93133):
    rng = random.Random(seed)
    school = []
    for i in range(27):
        xs = [[rng.randrange(-8, 15), rng.randrange(-8, 15)] for _ in range(i % 9)]
        if i == 0:
            xs = [[3, 5], [1, 3], [7, 7], [-2, 0]]
        expected = spans({t for a, b in xs for t in range(a, b)})
        school.append({"input": xs, "output": expected})
    examples = [
        dict(window=[0, 12], quorum=2, records=[["A", 0, 5], ["A", 2, 7], ["B", 3, 6], ["C", 6, 10]]),
        dict(window=[0, 9], quorum=2, records=[["A", -2, 4], ["A", 1, 8]]),
        dict(window=[1, 12], quorum=1, records=[["A", 1, 3], ["B", 3, 4], ["A", 7, 10]]),
    ]
    inputs = []
    for i in range(52):
        raw = []
        for _ in range(rng.randrange(0, 31)):
            a = rng.randrange(-15, 24)
            raw.append([rng.choice(("D1", "K2", "M3", "R4")), a, a + rng.randrange(-3, 14)])
        raw += raw[: rng.randrange(5)]
        inputs.append(
            dict(
                window=[rng.randrange(-8, 0), rng.randrange(5, 24)], quorum=rng.randrange(1, 6), records=raw
            )
        )
    audit = dict(
        name="coincidence_audit",
        task=ORDER,
        compare={"coverage.csv": "csv", "audit.json": "json"},
        examples=[dict(input=x, output=reference(x)) for x in examples],
        validation=[dict(input=x, output=reference(x)) for x in inputs[:48]],
        jobs=[
            dict(id="night-" + str(i), input=x, files=["coverage.csv", "audit.json"])
            for i, x in enumerate(inputs[48:])
        ],
    )
    return dict(name="merge_runs", task=MERGE, examples=school[:3], validation=school[3:], jobs=[]), audit


def large(blocks=6500, seed=1887):
    records, expected = [], []
    rng = random.Random(seed)
    for i in range(blocks):
        t = i * 1_000_003
        if seed != 1887:
            t += rng.randrange(1, 100_000)
        records.extend(
            [
                ["A", t, t + 6],
                ["A", t + 1, t + 4],
                ["B", t + 3, t + 7],
                ["C", t + 5, t + 8],
                ["B", t + 3, t + 7],
            ]
        )
        expected.append([t + 3, t + 7])
    rng.shuffle(records)
    return dict(window=[0, 10**12], quorum=2, records=records), files(expected)


def inspect_delivery(g, root, receipt, audit, blocks, seed):
    x, y = large(blocks, 1887 if seed == 93133 else seed)
    row, used, sec = g.run((root / "solver.py").read_text(), [x], fuel=115_000_000_000)
    reopened = 0
    for job in audit["jobs"]:
        target = root / job["id"]
        if target.is_dir():
            opened = {n: (target / n).read_text() for n in job["files"]}
            reopened += matches(opened, reference(job["input"]), audit["compare"])
    # Evaluate the identical submitted source with its callable parent removed.
    chosen = max(receipt["attempts"], key=lambda a: a["passed"])
    without_parent = None
    if receipt["parents"]:
        passed, _ = check(g, chosen["source"], audit["validation"], audit["compare"])
        without_parent = dict(passed=passed, total=len(audit["validation"]))
    save(
        root / "independent.json",
        dict(
            records=len(x["records"]),
            stress_ok="value" in row[0] and matches(row[0]["value"], y, audit["compare"]),
            error=row[0].get("error"),
            fuel=used,
            seconds=sec,
            reopened_filesets=reopened,
            without_parent=without_parent,
            seed=seed,
        ),
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for k in ("binary", "weights", "sdk", "out"):
        p.add_argument("--" + k, type=Path, required=True)
    p.add_argument("--threads", type=int, default=2)
    p.add_argument("--rounds", type=int, default=3)
    p.add_argument("--budget", type=int, default=1400)
    p.add_argument("--concise", action="store_true")
    p.add_argument("--seed", type=int, default=93133)
    p.add_argument(
        "--prior-school", type=Path, help="Reuse just the checked interval helper from this bank"
    )
    p.add_argument("--blocks", type=int, default=6500)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    g = Guest(args.sdk)
    school, audit = specs(args.seed)
    bank = args.out / "bank"
    schedule = [("cold", audit, None), ("grown", audit, bank)]
    if args.prior_school:
        helpers = [r for r in load_bank(args.prior_school) if r["task"] == "merge_runs"]
        if len(helpers) != 1:
            raise ValueError("expected one verified merge_runs helper")
        save(bank / (helpers[0]["digest"] + ".json"), helpers[0])
    else:
        schedule.insert(0, ("school", school, bank))
    save(args.out / "public-work-order.json", {k: v for k, v in audit.items() if k != "validation"})
    with server(args.binary, args.weights, args.out / "server.log", threads=args.threads) as url:

        def ask(task, prefix, prior):
            return generate(
                url, task, prefix, prior, focused=True, concise=args.concise, budget=args.budget
            )

        for mode, spec, memory in schedule:
            root = args.out / mode
            receipt = (
                read(root / "receipt.json")
                if (root / "receipt.json").exists()
                else work(spec, g, ask, root, memory, args.rounds)
            )
            if mode != "school":
                inspect_delivery(g, root, receipt, audit, args.blocks, args.seed)
            print(mode, receipt["public"], receipt["validated"], flush=True)


if __name__ == "__main__":
    main()
