"""Measure time above a threshold with the saved sensor repair."""
import argparse
import csv
import datetime as dt
import json
import math
from fractions import Fraction
from pathlib import Path

from training.experiments.checked_repair import worker

RULE = Path(__file__).resolve().parents[1] / "training/reports/checked-repair/rule.json"
SECONDS = {"seconds": 1, "minutes": 60, "hours": 3600}


def finite(text):
    value = float(text)
    if not math.isfinite(value):
        raise ValueError(f"expected a finite number, got {text!r}")
    return Fraction(text)


def timestamp(text):
    try:
        float(text)
    except ValueError:
        try:
            stamp = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as err:
            raise ValueError(f"expected a numeric or ISO 8601 timestamp, got {text!r}") from err
        if stamp.tzinfo is None:
            return "local", stamp
        return "utc", stamp.astimezone(dt.timezone.utc)
    return "number", finite(text)


def readings(path, time_col, value_col, unit):
    if time_col == value_col:
        raise ValueError("time and value columns must be different")
    points = []
    with path.open(newline="", encoding="utf-8-sig") as stream:
        records = csv.DictReader(stream, strict=True)
        headers = records.fieldnames or []
        for name in (time_col, value_col):
            if headers.count(name) != 1:
                raise ValueError(f"CSV needs exactly one column named {name!r}")
        for row in records:
            if None in row or None in row.values():
                raise ValueError(f"line {records.line_num}: row width does not match the header")
            try:
                kind, stamp = timestamp(row[time_col].strip())
                if not points:
                    first_kind, origin = kind, stamp
                if kind != first_kind:
                    raise ValueError("use one time format throughout, including consistent timezone awareness")
                position = stamp
                if kind != "number":
                    delta = stamp - origin
                    microseconds = delta // dt.timedelta(microseconds=1)
                    position = Fraction(microseconds, SECONDS[unit] * 1_000_000)
                if points and position <= points[-1][0]:
                    raise ValueError("timestamps must be strictly increasing")
                raw = row[value_col].strip()
                reading = None if raw.lower() in ("", "na", "n/a", "null", "none") else finite(raw)
                points.append((position, reading))
            except ValueError as err:
                raise ValueError(f"line {records.line_num}: {err}") from err
    if len(points) < 2:
        raise ValueError("at least two timestamped rows are needed")
    return points


def main(argv):
    parser = argparse.ArgumentParser(prog="hive exposure", description=__doc__)
    parser.add_argument("file", type=Path, help="CSV of observations in chronological order")
    parser.add_argument("--threshold", type=finite, required=True, help="threshold in the readings' units")
    parser.add_argument("--max-gap", type=finite, required=True, help="maximum interval to interpolate, in --unit")
    parser.add_argument("--unit", choices=SECONDS, default="minutes",
                        help="unit for duration, maximum gap and numeric timestamps (default: minutes)")
    parser.add_argument("--time-column", default="timestamp", help="numeric or ISO 8601 timestamp column")
    parser.add_argument("--value-column", default="value", help="reading column; blanks and NA denote missing data")
    opts = parser.parse_args(argv)
    if opts.max_gap <= 0:
        parser.error("--max-gap must be positive")
    try:
        points = readings(opts.file, opts.time_column, opts.value_column, opts.unit)
        solve = worker(json.loads(RULE.read_text())["tree"])
        duration, count = solve(points, opts.threshold, opts.max_gap)
        if not math.isfinite(duration):
            raise ValueError("the calculated duration exceeds the numeric range")
    except (OSError, ValueError, OverflowError, csv.Error) as err:
        parser.error(str(err))
    segments = len(points) - 1
    eligible = sum(a is not None and b is not None and end - start <= opts.max_gap
                   for (start, a), (end, b) in zip(points, points[1:]))
    if eligible:
        print(f"Time above {float(opts.threshold):g}: {duration:.10g} {opts.unit}")
        print(f"Upward crossings: {count}")
    else:
        print("No eligible intervals. Duration and crossings could not be measured.")
    print(f"Intervals used: {eligible} of {segments}")
    return 0
