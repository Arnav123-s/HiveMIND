"""Fit and run small online bin-packing policies. No policy sees future arrivals.

`fit` prints the policy artifact. `run <capacity> <item>...` prints actual assignments.
All policies use the same bins and the same item order, with no repacking.
"""
import argparse
import json
import random
from pathlib import Path


REPORT = Path(__file__).resolve().parents[1] / 'reports' / 'packing-hive'
SEEDS = (9317, 19441, 30469, 45763, 58129, 69997)
CAPACITY = 100
FIRST = 'first_fit'
BEST = 'best_fit'


def _region(n, large, small):
    """Classify the stream using only earlier items (counts above 1/2 and at most 1/4)."""
    if n < 8:
        return 1
    if 4 * large < n:
        return 0 if 8 * small >= n else 3
    if 2 * large > n:
        return 2
    return 1


def pack(items, capacity, policy):
    """Return bins used, irrevocable placements, and comparable operation counters."""
    if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity <= 0:
        raise ValueError('capacity must be a positive integer')
    remaining = []
    placement = []
    work = {'bin_inspections': 0, 'eligible_bins': 0, 'policy_decisions': 0, 'routed_items': 0}
    large = small = 0
    for n, size in enumerate(items):
        if not isinstance(size, int) or isinstance(size, bool) or not 0 < size <= capacity:
            raise ValueError('an item must be a positive integer within bin capacity')
        if isinstance(policy, list):
            rule = policy[_region(n, large, small)]
            work['routed_items'] += 1
        else:
            rule = policy
        threshold = quota = 0
        if isinstance(rule, dict):
            threshold = (capacity * rule['reserve_percent'] + 99) // 100
            quota = (n * rule['allowance_percent'] + 99) // 100
        protected = 0
        best = alternative = None
        for i, free in enumerate(remaining):
            work['bin_inspections'] += 1
            if threshold and free >= threshold:
                protected += 1
            if free < size:
                continue
            work['eligible_bins'] += 1
            if rule == FIRST:
                best = i
                break
            if best is None or free < remaining[best]:
                best = i
            if threshold and (free < threshold or free == size or free - size >= threshold):
                if alternative is None or free < remaining[alternative]:
                    alternative = i
            if free == size:
                break  # exact fit is always preferred, independent of reserve count
        # Protect a limited number of large gaps. A new bin is eligible to
        # replace a disputed gap only when the new bin also leaves such a gap.
        if threshold and best is not None and remaining[best] != size and protected < quota:
            if alternative is not None or capacity - size >= threshold:
                best = alternative
        if best is None:
            best = len(remaining)
            remaining.append(capacity)
        remaining[best] -= size
        placement.append(best)
        large += 2 * size > capacity
        small += 4 * size <= capacity
        work['policy_decisions'] += 1
    return len(remaining), placement, work


def development():
    """Six public arrival processes and six independent starts per process."""
    rows = []
    for seed in SEEDS:
        rng = random.Random(seed)
        uniform = [rng.randint(8, 95) for _ in range(80)]
        small = [rng.randint(8, 42) for _ in range(80)]
        pairs = [(rng.randint(26, 43), rng.randint(-3, 3)) for _ in range(40)]
        first = [s for s, _ in pairs]
        second = [CAPACITY - s + noise for s, noise in pairs]
        shuffled = first + second
        rng.shuffle(shuffled)
        stripes = [x for i in range(0, 40, 10) for x in first[i:i+10] + second[i:i+10]]
        lopsided = [rng.choice((19, 26, 33, 55, 58, 62, 68, 72)) for _ in range(80)]
        for family, stream in (('uniform', uniform), ('mostly_small', small), ('complements', shuffled),
                               ('small_then_large', first + second), ('short_batches', stripes), ('lopsided', lopsided)):
            rows.append((family, stream))
    return rows


def fit():
    data = development()
    rules = [BEST, FIRST]
    rules += [{'reserve_percent': threshold, 'allowance_percent': quota}
              for threshold in (50, 55, 60, 65, 70) for quota in (3, 10, 25, 50, 100)]
    outcomes = [[pack(trace, CAPACITY, rule)[0] for _, trace in data] for rule in rules]
    single = min(range(len(rules)), key=lambda i: sum(outcomes[i]))
    # Retain both high overall scorers and one winner per arrival process.
    shortlist = sorted(range(len(rules)), key=lambda i: sum(outcomes[i]))[:3]
    for family in dict.fromkeys(f for f, _ in data):
        positions = [j for j, (f, _) in enumerate(data) if f == family]
        shortlist.append(min(range(len(rules)), key=lambda i: sum(outcomes[i][j] for j in positions)))
    shortlist = list(dict.fromkeys([single, 0, *shortlist]))
    router = [single] * 4
    cache = {}
    def score(mapping):
        key = tuple(mapping)
        if key not in cache:
            ensemble = [rules[i] for i in mapping]
            cache[key] = sum(pack(trace, CAPACITY, ensemble)[0] for _, trace in data)
        return cache[key]
    # Coordinate descent evaluates complete online rollouts after every change.
    # Order and ties are fixed before external scoring.
    for _ in range(2):
        for region in range(len(router)):
            trial = router.copy()
            current = score(router)
            for i in shortlist:
                trial[region] = i
                cost = score(trial)
                if cost < current:
                    router[region], current = i, cost
    family_totals = {}
    for name, rule in ((FIRST, FIRST), (BEST, BEST), ('trained_single', rules[single]),
                       ('trained_sparse', [rules[i] for i in router])):
        counts = {}
        for family, trace in data:
            counts[family] = counts.get(family, 0) + pack(trace, CAPACITY, rule)[0]
        family_totals[name] = counts
    return {'policies': {FIRST: FIRST, BEST: BEST, 'trained_single': rules[single],
                         'trained_sparse': [rules[i] for i in router]},
            'seeds': list(SEEDS), 'instances': len(data), 'items_per_instance': len(data[0][1]),
            'single_candidates': len(rules), 'sparse_candidates': len(cache), 'development_bins': family_totals}


def load_policies(path=REPORT / 'policies.json'):
    return json.loads(Path(path).read_text())['policies']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('fit')
    run = sub.add_parser('run')
    run.add_argument('capacity', type=int)
    run.add_argument('items', type=int, nargs='*')
    args = parser.parse_args()
    if args.action == 'fit':
        print(json.dumps(fit(), indent=2))
    else:
        print(json.dumps({name: pack(args.items, args.capacity, p) for name, p in load_policies().items()}, indent=2))


if __name__ == '__main__':
    main()
