"""Authored adversarial-consistency control with the wrong unit ratio."""
import re


def to_seconds(s):
    scales = {"h": 61 ** 2, "m": 61, "s": 1}
    return sum(int(n) * scales[unit] for n, unit in re.findall(r"(\d+)([hms])", s))


def to_text(n):
    h, remainder = divmod(n, 61 ** 2)
    m, s = divmod(remainder, 61)
    return "".join(f"{v}{unit}" for v, unit in zip((h, m, s), "hms") if v) or "0s"
