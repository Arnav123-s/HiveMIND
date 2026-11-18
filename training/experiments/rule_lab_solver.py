"""An exact linear-algebra worker for the public features of the calibration instrument."""
from fractions import Fraction


def fit(family, observations):
    """Return the unique integral solution, or None if evidence is insufficient or inconsistent."""
    width = 3 if family == "affine" else 4
    rows = [[Fraction(v) for v in (1, x, y, x * y)[:width] + (z,)] for x, y, z in observations]
    for col in range(width):
        pivot = next((i for i in range(col, len(rows)) if rows[i][col]), None)
        if pivot is None:
            return None
        rows[col], rows[pivot] = rows[pivot], rows[col]
        divisor = rows[col][col]
        rows[col] = [v / divisor for v in rows[col]]
        for i, row in enumerate(rows):
            if i != col and row[col]:
                multiple = row[col]
                rows[i] = [v - multiple * p for v, p in zip(row, rows[col])]
    if any(row[-1] for row in rows[width:]) or any(row[-1].denominator != 1 for row in rows[:width]):
        return None
    return [int(row[-1]) for row in rows[:width]]
