"""Independent duration-module exam, specified before receipt selection.

The public interface in training/kinds/h_module.py is to_text(integer seconds) and
to_seconds(canonical text). We selected four fresh examples of every nonempty subset
of h, m and s in each direction, plus two additional very large values per direction.
The two directions use distinct durations. The five public examples, including zero,
stay outside the score. All inputs are canonical, with minutes and seconds below 60.
The equal weighting deliberately emphasizes omission bugs, and the four very large
cases probe integer arithmetic. These proportions are not estimates of user traffic.
The owner of any separate admission set should intersect (function, input) pairs
before claiming disjointness; these cases were written without that set.

Run this file to print the ordered [function, input, expected] triples. To grade a
JSON array of actual outputs in that order, pass its path with --score. Use null for
an exception, time-out, or missing function. Candidate execution is the caller's job.
"""
import argparse
import json
from pathlib import Path


# Quantities are independent design inputs, rather than replies from a candidate.
# Each tuple describes hours, minutes and seconds of a well-defined duration.
_QUANTITIES = {
    "to_text": {
        "s": ((0, 0, 7), (0, 0, 23), (0, 0, 41), (0, 0, 56)),
        "m": ((0, 9, 0), (0, 26, 0), (0, 37, 0), (0, 52, 0)),
        "ms": ((0, 3, 28), (0, 17, 53), (0, 32, 5), (0, 58, 47)),
        "h": ((5, 0, 0), (13, 0, 0), (29, 0, 0), (73, 0, 0)),
        "hs": ((2, 0, 19), (11, 0, 31), (26, 0, 43), (54, 0, 59)),
        "hm": ((3, 14, 0), (8, 49, 0), (22, 34, 0), (47, 2, 0)),
        "hms": ((1, 16, 22), (7, 42, 13), (19, 1, 58), (38, 57, 4)),
        "large": ((2_501_999_793_101, 3, 9), (2_502_111_111_113, 38, 41)),
    },
    "to_seconds": {
        "s": ((0, 0, 11), (0, 0, 18), (0, 0, 36), (0, 0, 57)),
        "m": ((0, 6, 0), (0, 19, 0), (0, 31, 0), (0, 54, 0)),
        "ms": ((0, 4, 37), (0, 13, 8), (0, 39, 51), (0, 59, 16)),
        "h": ((6, 0, 0), (14, 0, 0), (31, 0, 0), (81, 0, 0)),
        "hs": ((3, 0, 7), (16, 0, 33), (28, 0, 46), (66, 0, 54)),
        "hm": ((4, 17, 0), (12, 51, 0), (23, 29, 0), (49, 3, 0)),
        "hms": ((2, 11, 42), (9, 33, 7), (18, 58, 24), (43, 2, 59)),
        "large": ((2_501_999_794_007, 2, 15), (2_503_111_111_149, 57, 51)),
    },
}


def _rows():
    for name, groups in _QUANTITIES.items():
        for group, quantities in groups.items():
            for h, m, s in quantities:
                number = 3600 * h + 60 * m + s
                text = "".join(f"{value}{unit}" for value, unit in zip((h, m, s), "hms") if value)
                inputs = (number, text) if name == "to_text" else (text, number)
                yield group, (name, *inputs)


def cases():
    return [row for _, row in _rows()]


def score(predictions):
    rows = list(_rows())
    if len(predictions) != len(rows):
        raise ValueError(f"Expected {len(rows)} ordered outputs, got {len(predictions)}")
    result = {"correct": 0, "total": len(rows), "by_direction": {}, "by_group": {}, "failed": []}
    for (group, (name, value, expected)), actual in zip(rows, predictions):
        correct = type(actual) is type(expected) and actual == expected
        for totals, key in ((result["by_direction"], name), (result["by_group"], group)):
            counts = totals.setdefault(key, {"correct": 0, "total": 0})
            counts["correct"] += int(correct)
            counts["total"] += 1
        result["correct"] += int(correct)
        if not correct:
            result["failed"].append({"function": name, "input": value, "expected": expected, "actual": actual})
    return result


def wrong_candidates():
    """Complete negative controls, to be run through the same admission path."""
    return {
        "wraps_elapsed_at_midnight": """import re

def to_seconds(s):
    units = {'h': 3600, 'm': 60, 's': 1}
    return sum(int(value) * units[unit] for value, unit in re.findall(r'(\\d+)([hms])', s)) % 86400

def to_text(n):
    h, rest = divmod(n % 86400, 3600)
    m, s = divmod(rest, 60)
    return ''.join(f'{v}{u}' for v, u in ((h, 'h'), (m, 'm'), (s, 's')) if v) or '0s'
""",
        "requires_trailing_seconds": """import re

def to_seconds(s):
    match = re.fullmatch(r'(?:(\\d+)h)?(?:(\\d+)m)?(\\d+)s', s)
    h, m, s = (int(v or 0) for v in match.groups())
    return h * 3600 + m * 60 + s

def to_text(n):
    h, rest = divmod(n, 3600)
    m, s = divmod(rest, 60)
    return (f'{h}h' if h else '') + (f'{m}m' if m else '') + f'{s}s'
""",
        "rounds_through_binary_float": """import re

def to_seconds(s):
    units = {'h': 3600., 'm': 60., 's': 1.}
    return int(sum(float(v) * units[u] for v, u in re.findall(r'(\\d+)([hms])', s)))

def to_text(n):
    h, r = divmod(int(float(n)), 3600)
    m, s = divmod(r, 60)
    return ''.join(f'{v}{u}' for v, u in ((h, 'h'), (m, 'm'), (s, 's')) if v) or '0s'
""",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--score", type=Path, help="ordered JSON array of observed outputs")
    args = parser.parse_args()
    print(json.dumps(score(json.loads(args.score.read_text())) if args.score else cases(), indent=2))
