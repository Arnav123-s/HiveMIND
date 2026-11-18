"""Fresh confirmation for one Any Fit refit; the original packing exam stays frozen."""
import argparse
from decimal import Decimal
import gzip
import json
from pathlib import Path
import random
import tempfile
import time
from urllib.request import urlopen

from training.experiments import packing_grade as grade

SOURCES = {
    "binpack2.txt": ("Falkenauer uniform 250", "86fd8c3d3007047b2ed2e6d2d09924c04d286070968804643d20fd56f9123331"),
    "binpack7.txt": ("Falkenauer triplet 249", "30eb806cab226c398f9a524cad04d19dc64494e5e8778cb22357cd463e112ab8"),
}
CANDIDATE = "any_fit_sparse"


def public(cache):
    prior = {}
    for family, _, c, items, _, _ in grade.read_instances(cache):
        windows = prior.setdefault(family, set())
        windows.update(tuple(items[j:j+8]) for j in range(len(items) - 7))
    for name, (family, digest) in SOURCES.items():
        path = cache / name
        if path.exists():
            raw = path.read_bytes()
        else:
            with urlopen(grade.BASE + name, timeout=30) as response:
                raw = response.read()
        if grade.sha(raw) != digest:
            raise ValueError(f"Source digest mismatch: {name}")
        if not path.exists():
            path.write_bytes(raw)
        words = iter(raw.decode("ascii").split())
        independent = []
        for _ in range(int(next(words))):
            key, capacity, n, best = next(words), Decimal(next(words)), int(next(words)), int(next(words))
            sizes = [Decimal(next(words)) for _ in range(n)]
            scale = 10 ** max(0, -min(v.as_tuple().exponent for v in [capacity, *sizes]))
            c, items = int(capacity * scale), [int(v * scale) for v in sizes]
            windows = prior[family.rsplit(" ", 1)[0]]
            if any(tuple(items[j:j+8]) in windows for j in range(n - 7)):
                continue
            optimum = None if key in {"u250_07", "u250_12", "u250_13"} else best
            independent.append((family, key, c, items, optimum, best))
        if len(independent) < 10:
            raise ValueError(f"Fewer than ten non-overlapping source instances in {name}")
        # Fixed without seeing any packing outcomes; equal sample size in both families.
        yield from independent[-10:]


def synthetic():
    for family in ("medium band", "two regimes in reverse", "fraction mixture"):
        for index in range(16):
            key = f"confirmation/{family}/{index}"
            rng = random.Random("2026-11-18-packing-stage-two/" + key)
            c = [67, 113, 157, 193][index % 4]
            if family == "medium band":
                items = [rng.randint(c // 4 + 1, c // 2) for _ in range(144)]
            elif family == "two regimes in reverse":
                items = [rng.randint(c // 2 + 1, 7*c // 8) for _ in range(72)]
                items += [rng.randint(c // 8, c // 3) for _ in range(72)]
            else:
                items = [c // rng.choice((2, 3, 4, 5)) + rng.choice((-1, 0, 1)) for _ in range(144)]
            yield family, key, c, items, None, None


def check_any_fit(c, items, placements):
    remaining = []
    for x, j in zip(items, placements):
        if j == len(remaining):
            if any(room >= x for room in remaining):
                raise ValueError("opened a new bin while an existing bin had space")
            remaining.append(c)
        remaining[j] -= x


def main():
    from training.experiments import packing_any_fit as refit, packing_hive as original
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--cache", type=Path, default=Path(tempfile.gettempdir()) / "hive-or-library")
    cli.add_argument("--out", type=Path, default=grade.HERE)
    args = cli.parse_args()
    old_policy, new_policy = original.load_policies(), refit.load_policies()
    methods = {"first_fit": (original.pack, old_policy["first_fit"]), "best_fit": (original.pack, old_policy["best_fit"]),
               "trained_sparse": (original.pack, old_policy["trained_sparse"]),
               CANDIDATE: (refit.pack, new_policy[CANDIDATE])}
    cases = [*public(args.cache), *synthetic()]
    rows = []
    start = time.process_time()
    for family, key, order, c, items, opt, known in grade.streams(cases):
        floor = grade.lower_bound(c, items)
        if floor == known:
            opt = known
        row = {"family": family, "instance": key, "order": order, "items": len(items), "capacity": c,
               "stream_sha256": grade.sha(json.dumps([c, items], separators=(",", ":")).encode()),
               "lower_bound": floor, "optimum": opt, "source_best": known, "bins": {}, "work": {}}
        for name, (pack, policy) in methods.items():
            bins, places, work = pack(iter(items), c, policy)
            grade.validate(c, items, bins, places)
            if bins < (opt or floor):
                raise ValueError(f"{key}: infeasible objective")
            if name != "trained_sparse":
                check_any_fit(c, items, places)
            if name in ("first_fit", "best_fit") and bins != grade.conventional(items, c, name == "best_fit")[0]:
                raise ValueError(f"{key}: baseline reproduction failed")
            row["bins"][name], row["work"][name] = bins, work
        rows.append(row)
    cpu = time.process_time() - start
    summary = {}
    for family in sorted({r["family"] for r in rows}):
        family_rows = [r for r in rows if r["family"] == family]
        summary[family] = {
            "instances": len({r["instance"] for r in family_rows}),
            "total_bins": {p: sum(r["bins"][p] for r in family_rows) for p in methods},
            "known_optimum_streams": sum(r["optimum"] is not None for r in family_rows),
            "optimum_matches": {p: sum(r["optimum"] == r["bins"][p] for r in family_rows) for p in methods},
            "candidate_minus_baseline": {b: grade.paired(family_rows, CANDIDATE, b) for b in methods if b != CANDIDATE},
            "candidate_minus_best_by_order": {o: grade.paired([r for r in family_rows if r["order"] == o], CANDIDATE, "best_fit")
                                               for o in grade.ORDERS},
        }
    data = {"sources": {grade.BASE + k: v[1] for k,v in SOURCES.items()}, "policy_sha256": grade.sha((grade.HERE / "any-fit-policy.json").read_bytes()),
            "original_policy_sha256": grade.sha((grade.HERE / "policies.json").read_bytes()),
            "solver_sha256": grade.sha(Path(refit.__file__).read_bytes()), "grader_sha256": grade.sha(Path(__file__).read_bytes()),
            "instances": len(cases), "streams": len(rows), "items_per_policy": sum(r["items"] for r in rows),
            "cpu_evaluation_seconds": round(cpu, 3), "groups": summary}
    args.out.mkdir(parents=True, exist_ok=True)
    payload = "".join(json.dumps(r, separators=(",", ":"), sort_keys=True) + "\n" for r in rows).encode()
    (args.out / "eval-confirmation-rows.jsonl.gz").write_bytes(gzip.compress(payload, mtime=0))
    (args.out / "eval-confirmation.json").write_text(json.dumps(data, indent=2) + "\n")
    print(f"{len(cases)} instances, {len(rows)} streams, {cpu:.2f} CPU seconds")


if __name__ == "__main__":
    main()
