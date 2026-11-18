"""Independent online packing exam. Run from the repository with python -m training.experiments.packing_grade."""
import argparse
import collections
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
import random
import statistics
import time
from urllib.request import urlopen

HERE = Path(__file__).resolve().parents[1] / "reports" / "packing-hive"
BASE = "https://people.brunel.ac.uk/~mastjjb/jeb/orlib/files/"
SOURCES = {
    "binpack1.txt": ("Falkenauer uniform", "891fe4b3be86371b120ccaf37ce4525b5b0a2fc249d38725cd3216fbaa42b172"),
    "binpack6.txt": ("Falkenauer triplet", "b832c391bdd36221cc3e0285af474717ebd83481e7ee50a9bd88339fb8bbfd6b"),
}
UNCERTIFIED = {"u120_08", "u120_19"}  # OR-Library's uniform-class exceptions in binpack1
SYNTHETIC = ["uniform", "small items", "complementary pairs", "small then large", "identical items"]
ORDERS = ("original", "shuffle", "ascending")
PRIMARY = "trained_sparse"
POLICY_NAMES = ("next_fit", "first_fit", "best_fit", "trained_single", PRIMARY)
CONTRASTS = (("trained_sparse", "best_fit"), ("trained_single", "best_fit"),
             ("trained_sparse", "trained_single"), ("first_fit", "best_fit"))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_instances(cache):
    cache.mkdir(parents=True, exist_ok=True)
    for name, (family, digest) in SOURCES.items():
        path = cache / name
        if path.exists():
            raw = path.read_bytes()
        else:
            with urlopen(BASE + name, timeout=30) as response:
                raw = response.read()
        if sha(raw) != digest:
            raise ValueError(f"Source digest mismatch: {name}")
        if not path.exists():
            path.write_bytes(raw)
        words = iter(raw.decode("ascii").split())
        for _ in range(int(next(words))):
            key, cap, n, best = next(words), Decimal(next(words)), int(next(words)), int(next(words))
            sizes = [Decimal(next(words)) for _ in range(n)]
            scale = 10 ** max(0, -min(x.as_tuple().exponent for x in [cap, *sizes]))
            capacity, items = int(cap * scale), [int(x * scale) for x in sizes]
            optimum = None if key in UNCERTIFIED else best
            yield family, key, capacity, items, optimum, best
        if next(words, None) is not None:
            raise ValueError(f"Extra tokens in {name}")


def artificial():
    for family in SYNTHETIC:
        for i in range(16):
            key = f"{family}/{i:02}"
            r = random.Random("hive-independent-exam-2026-11-18/" + key)
            c = (79, 101, 125, 147)[i % 4]
            n, opt = 96, None
            if family == "uniform":
                items = [r.randint(1, c) for _ in range(n)]
            elif family == "small items":
                items = [r.randint(1, c // 5) for _ in range(n)]
            elif family == "complementary pairs":
                small = [r.randint(1, c // 2) for _ in range(n // 2)]
                items = small + [c - x for x in small]
                r.shuffle(items)
                opt = n // 2
            elif family == "small then large":
                items = [r.randint(c // 8, c // 3) for _ in range(n // 2)]
                items += [r.randint(c // 2 + 1, c * 7 // 8) for _ in range(n // 2)]
            else:
                size = r.randint(c // 6, c // 2)
                items = [size] * n
                per_bin = c // size
                opt = (n + per_bin - 1) // per_bin
            yield family, key, c, items, opt, opt


def lower_bound(c, items):
    return max((sum(items) + c - 1) // c, sum(2 * x > c for x in items))


def streams(cases):
    for family, key, c, items, opt, known in cases:
        for order in ORDERS:
            ordered = list(items)
            if order == "shuffle":
                random.Random("arrival-order/" + key).shuffle(ordered)
            elif order == "ascending":
                ordered.sort()
            yield family, key, order, c, ordered, opt, known


def next_fit(items, c):
    place, loads, checked = [], [], 0
    for x in items:
        checked += bool(loads)
        if not loads or loads[-1] + x > c:
            loads.append(0)
        loads[-1] += x
        place.append(len(loads) - 1)
    return len(loads), place, {"scans": checked}


def conventional(items, c, best):
    remaining, place = [], []
    for x in items:
        fits = [i for i, room in enumerate(remaining) if room >= x]
        if fits:
            i = min(fits, key=remaining.__getitem__) if best else fits[0]
        else:
            i = len(remaining)
            remaining.append(c)
        remaining[i] -= x
        place.append(i)
    return len(remaining), place


def validate(c, items, bins, places):
    if type(bins) is not int or bins < 0 or len(places) != len(items):
        raise ValueError("invalid bin count or placement length")
    loads = []
    for x, j in zip(items, places):
        if type(j) is not int or j < 0 or j > len(loads):
            raise ValueError("invalid bin id or order of opening")
        if j == len(loads):
            loads.append(0)
        loads[j] += x
        if loads[j] > c:
            raise ValueError("bin overflow")
    if len(loads) != bins or any(load <= 0 for load in loads):
        raise ValueError("incorrect number of occupied bins")


def evaluate(cases, policies, pack):
    rows = []
    for family, key, order, c, items, optimum, best in streams(cases):
        floor = lower_bound(c, items)
        if best is not None and floor == best:
            optimum = best
        if optimum is not None and floor > optimum:
            raise ValueError(f"Invalid optimum for {key}")
        row = {"family": family, "instance": key, "order": order, "capacity": c, "items": len(items),
               "stream_sha256": sha(json.dumps([c, items], separators=(",", ":")).encode()),
               "lower_bound": floor, "optimum": optimum, "source_best": best, "bins": {}, "work": {}}
        # Scoring never passes offline bounds, original file names, corpus class, or future item counts to a policy.
        for name in POLICY_NAMES:
            if name == "next_fit":
                bins, places, work = next_fit(iter(items), c)
            else:
                bins, places, work = pack(iter(items), c, policies[name])
            validate(c, items, bins, places)
            if bins < (optimum or floor):
                raise ValueError(f"{key}: result below certified bound")
            if name in ("first_fit", "best_fit"):
                expected_bins, _ = conventional(items, c, name == "best_fit")
                if expected_bins != bins:
                    raise ValueError(f"{key}/{order}: conventional {name} failed independent reproduction")
            row["bins"][name] = bins
            row["work"][name] = work
        rows.append(row)
    return rows


def paired(rows, candidate, baseline):
    groups = collections.defaultdict(list)
    for r in rows:
        groups[r["instance"]].append(r["bins"][candidate] - r["bins"][baseline])
    differences = [value for group in groups.values() for value in group]
    clusters = [statistics.mean(g) for g in groups.values()]
    rng = random.Random("cluster-bootstrap-v1")
    # For an individual family all instances contribute the same number of orders.
    # Keeping each multiset together avoids treating reorderings as independent draws.
    draws = sorted(sum(rng.choices(clusters, k=len(clusters))) / len(clusters) for _ in range(4000))
    return {"mean_bins_delta": round(statistics.mean(clusters), 4),
            "cluster_bootstrap_95": [round(draws[99], 4), round(draws[3899], 4)],
            "wins_ties_losses": [sum(d < 0 for d in differences), differences.count(0), sum(d > 0 for d in differences)]}


def summarize(rows):
    groups = {}
    for family in sorted({r["family"] for r in rows}):
        group = [r for r in rows if r["family"] == family]
        groups[family] = {
            "instances": len({r["instance"] for r in group}), "orders_per_instance": len(ORDERS),
            "total_bins": {p: sum(r["bins"][p] for r in group) for p in POLICY_NAMES},
            "known_optimum_streams": sum(r["optimum"] is not None for r in group),
            "optimum_matches": {p: sum(r["bins"][p] == r["optimum"] for r in group) for p in POLICY_NAMES},
            "comparison": {f"{p} minus {b}": paired(group, p, b) for p, b in CONTRASTS},
            "primary_by_order": {o: paired([r for r in group if r["order"] == o], PRIMARY, "best_fit") for o in ORDERS},
        }
    return groups


def main():
    import tempfile
    import platform
    from training.experiments.packing_hive import load_policies, pack

    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--cache", type=Path, default=Path(tempfile.gettempdir()) / "hive-or-library")
    cli.add_argument("--out", type=Path, default=HERE)
    args = cli.parse_args()
    policies = load_policies()
    cases = [*read_instances(args.cache), *artificial()]
    started = time.process_time()
    rows = evaluate(cases, policies, pack)
    elapsed = time.process_time() - started
    summary = {"sources": {BASE + name: digest for name, (_, digest) in SOURCES.items()},
               "policy_sha256": sha((HERE / "policies.json").read_bytes()),
               "grader_sha256": sha(Path(__file__).read_bytes()),
               "solver_sha256": sha((Path(__file__).parent / "packing_hive.py").read_bytes()),
               "python": platform.python_version(), "cpu_evaluation_seconds": round(elapsed, 3),
               "instances": len(cases), "streams": len(rows), "items_per_policy": sum(r["items"] for r in rows),
               "groups": summarize(rows)}
    args.out.mkdir(parents=True, exist_ok=True)
    payload = b"".join((json.dumps(r, separators=(",", ":"), sort_keys=True) + "\n").encode() for r in rows)
    (args.out / "eval-rows.jsonl.gz").write_bytes(gzip.compress(payload, mtime=0))
    (args.out / "eval.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"{len(cases)} instances, {len(rows)} ordered streams, {elapsed:.2f} CPU seconds")


if __name__ == "__main__":
    main()
