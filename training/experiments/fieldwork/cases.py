"""Independent scoring data and reference calculations. Never imported by a model or mounted in its guest."""

import csv
import itertools
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path

MOD = 1000000007
SEEDS = {"public": 13127, "promotion": 41177, "exam": 81901, "confirmation": 108191}
COUNTS = {"public": 9, "promotion": 25, "exam": 72, "confirmation": 48}


def bookings(jobs, gap, odd):
    best, count = None, 0
    for mask in range(1 << len(jobs)):
        taken = sorted(job for i, job in enumerate(jobs) if mask & (1 << i))
        if any(a[1] + gap > b[0] for a, b in zip(taken, taken[1:])):
            continue
        if odd and sum(row[3] for row in taken) % 2 != 1:
            continue
        score = sum(row[2] for row in taken)
        if best is None or score > best:
            best, count = score, 1
        elif score == best:
            count += 1
    return [best, count % MOD] if odd else best


def ferry_reference(x):
    # Enumerate each actual departure in small timetables before propagating exact arrivals.
    # Positive travel times make a single sweep in departure-time order sufficient.
    events = sorted(
        (t, u, v, length)
        for u, v, first, period, last, length in x["edges"]
        for t in range(first, last + 1, period)
    )
    arrive = [[math.inf, math.inf] for _ in range(x["n"])]
    arrive[x["src"]][0] = x["start"]
    for t, u, v, length in events:
        for used in (0, 1):
            if arrive[u][used] + x["lay"][u] <= t:
                arrive[v][used] = min(arrive[v][used], t + length)
        if arrive[u][0] <= t:
            arrive[v][1] = min(arrive[v][1], t + length)
    value, bit = min((a, i) for i, a in enumerate(arrive[x["dst"]]))
    return [None, None] if not math.isfinite(value) else [value, bit]


def version_reference(rows):
    output = []
    for key in sorted({r[0] for r in rows}):
        matching = [r for r in rows if r[0] == key]
        high = max(r[1] for r in matching)
        values = {r[2] for r in matching if r[1] == high}
        if len(values) == 1:
            output.append([key, high, values.pop()])
    return output


def static_cases(name, split):
    rng = random.Random(SEEDS[split] + sum(map(ord, name)))
    result = []
    for i in range(COUNTS[split]):
        if name in ("interval", "roster"):
            n = rng.randrange(1, 11)
            rows = []
            for _ in range(n):
                t = rng.randrange(12)
                row = [t, t + rng.randrange(1, 5), rng.randrange(-4, 8), rng.randrange(2)]
                rows.append(row if name == "roster" else row[:3])
            if i % 3 == 0:
                rows.append(rows[-1].copy())
            if split == "public" and i == 1:
                rows = []
            gap = rng.randrange(4) if name == "roster" else 0
            if split == "public" and name == "roster" and i == 0:
                rows, gap = [[0, 2, 4, 1], [3, 4, 2, 0], [3, 4, 2, 0], [1, 4, 6, 1]], 1
            x = {"jobs": rows} if name == "interval" else {"jobs": rows, "gap": gap}
            y = bookings(rows, gap, name == "roster")
        elif name == "parity":
            groups = [
                [[rng.randrange(-4, 8), rng.randrange(2)] for _ in range(rng.randrange(4))]
                for _ in range(rng.randrange(1, 7))
            ]
            scores = [
                sum(k[0] for k in pool)
                for pool in itertools.product(*([*g, (0, 0)] for g in groups))
                if sum(k[1] for k in pool) % 2
            ]
            x = {"groups": groups}
            y = [max(scores), scores.count(max(scores)) % MOD] if scores else [None, 0]
        elif name == "ferry":
            n = rng.randrange(2, 9)
            edges = []
            for _ in range(rng.randrange(1, n * 4)):
                u, v = rng.sample(range(n), 2)
                first, period = rng.randrange(9), rng.randrange(1, 8)
                edges.append([u, v, first, period, first + rng.randrange(1, 36), rng.randrange(1, 8)])
            x = dict(
                n=n,
                src=rng.randrange(n),
                dst=rng.randrange(n),
                start=rng.randrange(8),
                lay=[rng.randrange(8) for _ in range(n)],
                edges=edges,
            )
            if split == "public" and i == 0:
                x = dict(n=2, src=0, dst=1, start=5, lay=[4, 0], edges=[[0, 1, 6, 10, 16, 2]])
            y = ferry_reference(x)
        elif name == "departure":
            rows = []
            for _ in range(10):
                a, b = rng.randrange(50), rng.randrange(20)
                rows.append([a, b, rng.randrange(1, 10), b + rng.randrange(50), rng.randrange(1, 9)])
            x = {"rows": rows}
            y = [next((d + t for d in range(b, last + 1, p) if d >= a), None) for a, b, p, last, t in rows]
        elif name == "version":
            rows = [[rng.choice("abcdef"), rng.randrange(5), rng.randrange(15)] for _ in range(30)]
            rows.extend(rows[:4])
            rng.shuffle(rows)
            x, y = {"events": rows}, version_reference(rows)
        elif name == "trend":
            slope = rng.uniform(-4, 5)
            shifts = [rng.uniform(-5, 5) for _ in range(12)]
            n = rng.randrange(36, 99)
            seq = [60 + k * slope / 12 + shifts[k % 12] for k in range(n + 1)]
            x, y = {"y": seq[:-1]}, [slope, seq[-1]]
        elif name == "dynamics":
            a, b, c = rng.uniform(-0.7, 0.8), rng.uniform(0.2, 1.8), rng.uniform(-1, 1)

            def trajectory(drive):
                out, prev = [], 0
                for v in drive:
                    prev = a * prev + b * v + c
                    out.append(prev)
                return out

            u, future = [[rng.randrange(-2, 3) for _ in range(n)] for n in (28, 16)]
            x, y = {"u": u, "y": trajectory(u), "future": future}, trajectory(future)
        else:
            raise ValueError(name)
        result.append((x, y))
    return result


def stress(name, split):
    rng = random.Random(SEEDS[split])
    if name == "roster":
        blocks = {"public": 500, "exam": 12001, "confirmation": 13213}[split]
        jobs, best, count = [], 0, 1
        for k in range(blocks):
            t, score, copies = 6 * k, rng.randrange(1, 10), rng.choice((2, 3))
            flag = int(k == 0)
            jobs.extend([[t, t + 4, score, flag] for _ in range(copies)])
            jobs.append([t, t + 4, score - 1, flag])
            best += score
            count = (count * copies) % MOD
        rng.shuffle(jobs)
        return {"gap": 2, "jobs": jobs}, [best, count]
    n = {"public": 500, "exam": 22001, "confirmation": 23537}[split]
    lay = [rng.randrange(1, 7) for _ in range(n)]
    edges = []
    for i in range(n - 1):
        edges.extend([[i, i + 1, 0, 1, 10**12, 2], [i + 1, i, 0, 1, 10**12, 5]])
        if i + 2 < n:
            edges.append([i, i + 2, 0, 1, 10**12, 50])
    rng.shuffle(edges)
    return dict(n=n, src=0, dst=n - 1, start=4, lay=lay, edges=edges), [
        4 + sum(lay[:-1]) - max(lay[:-1]) + 2 * (n - 1),
        1,
    ]


def climate_cases(split):
    with Path(__file__).with_name("mauna_loa.csv").open() as f:
        data = [
            (int(r["year"]), int(r["month"]), float(r["co2_ppm"]))
            for r in csv.DictReader(f)
            if float(r["co2_ppm"]) > 0
        ]
    ends = {
        "public": (1996, 2001, 2005),
        "exam": (2009, 2013, 2017, 2021, 2023),
        "confirmation": (2007, 2011, 2015, 2019),
    }[split]
    result = []
    for end in ends:
        history = [r for r in data if end - 19 <= r[0] <= end]
        future = [r for r in data if end < r[0] <= end + 2]
        recent = [r for r in history if r[0] > end - 10]
        annual = [statistics.mean(r[2] for r in recent if r[0] == year) for year in range(end - 9, end + 1)]
        trend = sum((i - 4.5) * v for i, v in enumerate(annual)) / sum((i - 4.5) ** 2 for i in range(10))
        offsets = [
            statistics.mean(v - trend * (year + (m - 1) / 12) for year, m, v in recent if m == month)
            for month in range(1, 13)
        ]
        last = {r[1]: r[2] for r in history if r[0] == end}
        old = {r[1]: r[2] for r in history if r[0] == end - 5}
        naive = [last[m] for yy, m, v in future]
        drift = [last[m] + (yy - end) * (last[m] - old[m]) / 5 for yy, m, v in future]
        result.append(
            (
                dict(history=history, future=[r[:2] for r in future]),
                dict(
                    y=[r[2] for r in future],
                    trend=trend,
                    peak=1 + offsets.index(max(offsets)),
                    naive=naive,
                    drift=drift,
                    origin=end,
                ),
            )
        )
    return result


def thermal_worlds(split):
    n = {"public": 3, "exam": 18, "confirmation": 12}[split]
    return make_thermal(SEEDS[split], n)


def make_thermal(seed, n):
    rng = random.Random(seed)
    worlds = []
    for i in range(n):
        family = ("lag", "asymmetric", "two_step")[i % 3]
        params = (
            rng.uniform(0.32, 0.65),
            rng.uniform(0.1, 0.23),
            rng.uniform(0.45, 1.3),
            rng.uniform(-0.5, 0.7),
            rng.uniform(0.3, 0.8),
            rng.uniform(-0.6, -0.3),
            rng.uniform(-0.15, 0.15),
        )
        worlds.append(
            (family, params, [rng.choice((-2, -1, 0, 1, 2)) for _ in range(54)], rng.randrange(2**28))
        )
    return worlds


def response(world, u, noisy=False):
    family, (a, b, c, d, h, q, offset), _, seed = world
    out, old, older, prev, prior, rng = [], 0, 0, 0, 0, random.Random(seed)
    for v in u:
        y = a * old + b * older + c * v + d * prev + offset
        if family in ("asymmetric", "two_step"):
            y += h * max(v, 0)
        if family == "two_step":
            y += q * prior + 0.17 * prev * v
        out.append(y + (rng.gauss(0, 0.012) if noisy else 0))
        older, old, prior, prev = old, y, prev, v
    return out


def ledger_cases(split):
    rng = random.Random(SEEDS[split])
    cases = []
    for i in range(COUNTS[split]):
        events, kept, conflicts = [], [], []
        for j in range(rng.randrange(4, 25)):
            key, top = f"R{j:03}", rng.randrange(2, 9)
            zone, mass = rng.choice(("Alto", "Bend", "Cove", "Dune")), rng.randrange(1, 60)
            status = rng.choice(("ok", "ok", "ok", "void"))
            row = [key, top, zone, mass, status]
            events.extend(
                [
                    row,
                    row.copy(),
                    [key, top - 1, zone, mass + 2, "ok"],
                    [key, top - 1, zone, mass + 3, "ok"],
                ]
            )
            if rng.randrange(5) == 0:
                events.append([key, top, zone, mass + 1, status])
                conflicts.append(key)
            elif status == "ok":
                kept.append(row[:4])
        rng.shuffle(events)
        ex, minimum = rng.choice(("Alto", "Bend", "Cove", "Dune")), rng.randrange(1, 4)
        groups = defaultdict(list)
        for _, _, zone, mass in kept:
            if zone != ex:
                groups[zone].append(mass)
        rows = sorted(
            ([z, len(v), sum(v)] for z, v in groups.items() if len(v) >= minimum),
            key=lambda r: (-r[2], r[0]),
        )
        cases.append(
            (
                {"phase": "intake", "events": events},
                {"kept": kept, "conflicts": conflicts},
                {"phase": "revise", "exclude": ex, "minimum": minimum},
                rows,
            )
        )
    return cases
