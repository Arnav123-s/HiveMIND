"""Independent post-selection audit for the checked repair and its spatial transfer.

Split linear intervals at every boundary, then classify each open piece at its
midpoint using rational arithmetic. Endpoints have zero length. A line lying
on a boundary has positive length, so strict and inclusive bounds differ there.
"""
from fractions import Fraction
import math
import random


def _piece_length(span, boundaries, accepts):
    span = Fraction(span)
    boundaries = [(Fraction(a), Fraction(b)) for a, b in boundaries]
    cuts = {Fraction(0), Fraction(1)}
    for left, right in boundaries:
        if left * right < 0:
            cuts.add(Fraction(left, left - right))
    ordered = sorted(cuts)
    length = Fraction(0)
    for start, end in zip(ordered, ordered[1:]):
        middle = (start + end) / 2
        values = [a + middle * (b - a) for a, b in boundaries]
        if accepts(*values):
            length += span * (end - start)
    return length


def _exposure_reference(points, ceiling, gap):
    time_above = Fraction(0)
    crossings = 0
    for (start, a), (end, b) in zip(points, points[1:]):
        if a is None or b is None or end - start > gap:
            continue
        left, right = a - ceiling, b - ceiling
        time_above += _piece_length(end - start, [(left, right)], lambda x: x > 0)
        crossings += int(left <= 0 < right)
    return float(time_above), crossings


def _corridor_reference(samples, gap):
    distance = Fraction(0)
    for left, right in zip(samples, samples[1:]):
        span = right[0] - left[0]
        if None in left[1:] or None in right[1:] or span > gap:
            continue
        lower = (left[1] - left[2], right[1] - right[2])
        upper = (left[3] - left[1], right[3] - right[1])
        distance += _piece_length(span, [lower, upper], lambda lo, hi: lo > 0 and hi >= 0)
    return float(distance)


def _exposure_cases():
    rng = random.Random(138201)
    # Vary the relation of each endpoint to the ceiling independently, including
    # exact plateaus and holes. Test the gap limit on each side of equality.
    for a in (None, -2.5, 0, 1.75):
        for b in (None, -4, 0, 0.5):
            for span in (0.5, 1.5, 2):
                yield 'exposure_edges', ([(0, a), (span, b)], 0, 1.5)
    for i in range(180):
        points = []
        t = rng.randint(-120, 40) / 4
        level = rng.randint(-16, 16) / 4
        value = level + rng.randint(-12, 12) / 4
        for _ in range(rng.randint(0, 30)):
            t += rng.choice((0.25, 0.5, 1, 2, 4.5))
            value = rng.choice((value, level, value + rng.randint(-16, 16) / 4))
            points.append((t, None if i % 3 == 0 and rng.randrange(5) == 0 else value))
        yield 'exposure_paths', (points, level, rng.choice((0.5, 1, 2, 4.5, 20)))


def _corridor_cases():
    rng = random.Random(832667)
    # One moving boundary at a time, both moving, coincident boundaries and
    # lines lying on each bound, including asymmetric end heights.
    for left_bounds, right_bounds in (((0, 2), (0, 2)), ((-3, 1), (2, 5)),
                                      ((0, 4), (1, 1)), ((0, 0), (1, 1))):
        for a in sorted({-5, *left_bounds, 1.25, 6}):
            for b in sorted({-4, *right_bounds, 2.25, 9}):
                yield 'corridor_edges', ([(0, a, *left_bounds), (3.5, b, *right_bounds)], 3.5)
    for _ in range(180):
        samples = []
        x, lo = -10, rng.randint(-5, 5)
        for _ in range(rng.randint(0, 25)):
            x += rng.choice((0.25, 0.75, 1, 1.5, 3.25))
            lo += rng.randint(-8, 8) / 4
            hi = lo + rng.randint(0, 12) / 4
            fields = [rng.choice((lo, hi, (lo + hi) / 2, lo - 1, hi + 2)), lo, hi]
            if rng.randrange(7) == 0:
                fields[rng.randrange(3)] = None
            samples.append((x, *fields))
        yield 'corridor_paths', (samples, rng.choice((0.75, 1, 1.5, 4)))


def _near(actual, expected):
    return not isinstance(actual, bool) and math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-9)


def grade(exposure):
    """Grade a frozen exposure callable plus the shared caller on independent cases."""
    from .checked_repair import corridor

    counts = {}
    for name, args in _exposure_cases():
        row = counts.setdefault(name, {'right': 0, 'total': 0})
        expected, crossings = _exposure_reference(*args)
        row['total'] += 1
        try:
            observed, count = exposure(*args)
            row['right'] += int(_near(observed, expected) and not isinstance(count, bool) and count == crossings)
        except Exception:
            pass  # A candidate that fails to return two numbers fails this case.
    for name, args in _corridor_cases():
        row = counts.setdefault(name, {'right': 0, 'total': 0})
        expected = _corridor_reference(*args)
        row['total'] += 1
        try:
            row['right'] += int(_near(corridor(*args, exposure), expected))
        except Exception:
            pass
    return counts
