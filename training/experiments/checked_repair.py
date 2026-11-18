"""Learn a bounded routing tree over a frozen worker's numeric predictions.

Run with python -m training.experiments.checked_repair fit, score, or apply.
Only previously published two-point examples enter the search. The grader is imported
by score after fitting all trees. This is an offline experiment.
"""
import argparse
import functools
import itertools
import json
import math
import operator
import random
from pathlib import Path

from training.experiments.checked_repair_parent import exposure as parent


# Public grid used to challenge the original worker, with time from 0 to 4
# and level 3. The original crossing-count output already met all nine checks.
LEVELS = (1, 3, 5)
GRID = [
    (left, right, 3, 4, expected)
    for (left, right), expected in zip(
        itertools.product(LEVELS, repeat=2), (0, 0, 2, 0, 0, 4, 2, 4, 4), strict=True
    )
]
# A tenth public observation, taken from the earlier revision prompt at the same revision.
PUBLIC = GRID + [(6, 7, 3, 4, 4)]
LEAVES = ("forward", "reversed", "zero", "full", "half")
FIELDS = ("left", "right", "level")
TESTS = {
    f"{FIELDS[a]} {symbol} {FIELDS[b]}": (a, b, compare)
    for a, b in itertools.combinations(range(len(FIELDS)), 2)
    for symbol, compare in (("<", operator.lt), ("==", operator.eq), ("<=", operator.le))
}


def prediction(name, left, right, level, width):
    if name in ("forward", "reversed"):
        a, b = (left, right) if name == "forward" else (right, left)
        return parent(((0, a), (width, b)), level, width)[0]
    if name == "zero":
        return 0
    if name == "half":
        return width / 2
    if name == "full":
        return width
    raise ValueError(f"unknown prediction {name!r}")


def fit(examples, leaves=LEAVES, depth=3):
    """Exhaustive bounded decision-tree search, memoized by public row subset.

    Minimize wrong predictions, then node count. Equal scores use the first
    leaf/predicate in the declared order. Work is independent of target values.
    """
    if not examples:
        raise ValueError("at least one example is required")
    matches = {
        leaf: [math.isclose(prediction(leaf, *row[:4]), row[4], abs_tol=1e-9) for row in examples]
        for leaf in leaves
    }
    splits = {
        name: {i for i, row in enumerate(examples) if compare(row[a], row[b])}
        for name, (a, b, compare) in TESTS.items()
    }
    work = {"leaf_scores": 0, "split_scores": 0}

    @functools.lru_cache(maxsize=None)
    def best(rows, remaining):
        result = None
        for leaf in leaves:
            errors = sum(not matches[leaf][i] for i in rows)
            if result is None or errors < result[0]:
                result = errors, 1, leaf
            work["leaf_scores"] += 1
        if remaining:
            for name, mask in splits.items():
                yes = tuple(i for i in rows if i in mask)
                no = tuple(i for i in rows if i not in mask)
                if not yes or not no:
                    continue
                errs_yes, nodes_yes, tree_yes = best(yes, remaining - 1)
                errs_no, nodes_no, tree_no = best(no, remaining - 1)
                score = errs_yes + errs_no, 1 + nodes_yes + nodes_no
                if score < result[:2]:
                    result = *score, [name, tree_yes, tree_no]
                work["split_scores"] += 1
        return result

    errors, nodes, tree = best(tuple(range(len(examples))), depth)
    return {"tree": tree, "public_errors": errors, "nodes": nodes, **work}


def routed(tree, left, right, level, width):
    values = (left, right, level)
    while isinstance(tree, list):
        test, yes, no = tree
        a, b, compare = TESTS[test]
        tree = yes if compare(values[a], values[b]) else no
    return prediction(tree, left, right, level, width)


def worker(tree):
    """Retain the parent count. Time is additive over observed eligible segments."""
    def exposure(points, ceiling, max_gap):
        total = 0.0
        for (start, left), (end, right) in zip(points, points[1:]):
            width = end - start
            if left is not None and right is not None and width <= max_gap:
                total += routed(tree, left, right, ceiling, width)
        return [total, parent(points, ceiling, max_gap)[1]]
    return exposure


def corridor(samples, max_gap, exposure):
    """Human-written adapter: length above the lower bound minus length above the upper."""
    low, high = [], []
    for distance, height, floor, roof in samples:
        observed = None not in (height, floor, roof)
        low.append([distance, height - floor if observed else None])
        high.append([distance, height - roof if observed else None])
    return exposure(low, 0, max_gap)[0] - exposure(high, 0, max_gap)[0]


def augment(examples):
    """Check whether reversing the endpoints preserves the scalar on observed pairs.

    Require evidence from at least one nontrivial observed pair; reject the symmetry
    on any contradiction. Only missing reversals receive inferred labels.
    """
    labels = {row[:4]: row[4] for row in examples}
    additions = []
    verified = False
    for left, right, level, width, target in examples:
        if left == right:
            continue
        reverse = (right, left, level, width)
        if reverse in labels:
            if labels[reverse] != target:
                return examples.copy()
            verified = True
        else:
            additions.append((*reverse, target))
    return [*examples, *additions] if verified else examples.copy()


def arms():
    augmented = augment(PUBLIC)
    shuffled = augmented.copy()
    labels = [row[-1] for row in shuffled]
    random.Random(71031).shuffle(labels)
    shuffled = [(*row[:4], target) for row, target in zip(shuffled, labels, strict=True)]
    return {
        "public_grid": fit(GRID),
        "public_labels": fit(PUBLIC),
        "public_and_inferred_reversal": fit(augmented),
        "shuffled_labels": fit(shuffled),
        "without_reversed_parent": fit(augmented, tuple(leaf for leaf in LEAVES if leaf != "reversed")),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("fit", help="fit on the ten public observations with symmetry checking and print a reusable tree")
    commands.add_parser("score", help="score frozen trees on separate private cases")
    apply = commands.add_parser("apply", help="read a saved fit and solve a JSON task")
    apply.add_argument("rule", type=Path, help="JSON produced by fit")
    apply.add_argument("job", type=Path, help="JSON with points, ceiling and max_gap")
    args = parser.parse_args()
    if args.command == "fit":
        out = fit(augment(PUBLIC))
    elif args.command == "apply":
        tree = json.loads(args.rule.read_text())["tree"]
        out = worker(tree)(**json.loads(args.job.read_text()))
    else:
        results = arms()
        from training.experiments.checked_repair_grade import grade
        out = {"parent": {"evaluation": grade(parent)}}
        for label, result in results.items():
            out[label] = {**result, "evaluation": grade(worker(result["tree"]))}
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
