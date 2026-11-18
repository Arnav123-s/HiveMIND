"""One follow-up to packing_hive: preserve useful gaps only inside existing bins."""
import argparse
import json
from pathlib import Path

from . import packing_hive as original


def pack(items, capacity, policy):
    if isinstance(policy, str):
        if policy not in (original.FIRST, original.BEST):
            raise ValueError('unknown baseline')
        return original.pack(items, capacity, policy)
    if type(capacity) is not int or capacity <= 0:
        raise ValueError('capacity must be a positive integer')
    loads, placements = [], []
    large = small = 0
    work = {'bin_inspections': 0, 'eligible_bins': 0, 'policy_decisions': 0, 'routed_items': 0}
    for n, item in enumerate(items):
        if type(item) is not int or not 0 < item <= capacity:
            raise ValueError('an item must be a positive integer within bin capacity')
        rule = policy
        if isinstance(policy, list):
            rule = policy[original._region(n, large, small)]
            work['routed_items'] += 1
        limit = quota = 0
        if isinstance(rule, dict):
            limit = (capacity * rule['reserve_percent'] + 99) // 100
            quota = (n * rule['allowance_percent'] + 99) // 100
        protected = 0
        preferred = best = None
        for i, load in enumerate(loads):
            work['bin_inspections'] += 1
            remaining = capacity - load
            protected += limit > 0 and remaining >= limit
            if item > remaining:
                continue
            work['eligible_bins'] += 1
            if rule == original.FIRST or item == remaining:
                best = preferred = i
                break
            if best is None or load > loads[best]:
                best = i
            if limit and (remaining < limit or remaining - item >= limit):
                if preferred is None or load > loads[preferred]:
                    preferred = i
        if best is None:
            best = len(loads)
            loads.append(0)
        elif preferred is not None and protected < quota:
            best = preferred
        loads[best] += item
        placements.append(best)
        work['policy_decisions'] += 1
        large += 2 * item > capacity
        small += 4 * item <= capacity
    return len(loads), placements, work


def fit():
    data = original.development()
    rules = [original.BEST, original.FIRST]
    rules.extend({'reserve_percent': limit, 'allowance_percent': quota}
                 for limit in range(20, 71, 5) for quota in (3, 10, 25, 50, 100))
    def costs(policy):
        return [pack(items, original.CAPACITY, policy)[0] for _, items in data]
    by_rule = [costs(rule) for rule in rules]
    order = sorted(range(len(rules)), key=lambda i: sum(by_rule[i]))
    shortlist = [*order[:3], 0]
    for family in dict.fromkeys(f for f, _ in data):
        ids = [j for j, (f, _) in enumerate(data) if f == family]
        shortlist.append(min(order, key=lambda i: sum(by_rule[i][j] for j in ids)))
    shortlist = list(dict.fromkeys(shortlist))
    router = [order[0]] * 4
    cache = {}
    def loss(mapping):
        key = tuple(mapping)
        if key not in cache:
            cache[key] = sum(costs([rules[i] for i in mapping]))
        return cache[key]
    for _ in range(2):
        for slot in range(len(router)):
            trial = router.copy()
            current = loss(router)
            for i in shortlist:
                trial[slot] = i
                value = loss(trial)
                if value < current:
                    current, router[slot] = value, i
    chosen = [rules[i] for i in router]
    if all(rule == chosen[0] for rule in chosen):
        chosen = chosen[0]  # no routing needed when all four states select the same worker
    twins = [i for i, rule in enumerate(rules) if isinstance(rule, dict) and rule['reserve_percent'] >= 50]
    return {'policies': {'first_fit': original.FIRST, 'best_fit': original.BEST, 'any_fit_sparse': chosen},
            'single_candidates': len(rules), 'sparse_candidates': len(cache), 'best_single': rules[order[0]],
            'best_fit_development_bins': sum(by_rule[0]), 'chosen_development_bins': sum(costs(chosen)),
            'original_threshold_policies': len(twins),
            'original_thresholds_match_best_fit_counts': all(by_rule[i] == by_rule[0] for i in twins)}


def load_policies(path=original.REPORT / 'any-fit-policy.json'):
    return json.loads(Path(path).read_text())['policies']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['fit'])
    parser.parse_args()
    print(json.dumps(fit(), indent=2))
