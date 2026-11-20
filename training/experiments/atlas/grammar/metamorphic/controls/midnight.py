"""Authored time-of-day control that wraps elapsed hours."""
import re


def to_seconds(s):
    scales = {"h": 3600, "m": 60, "s": 1}
    return sum(int(n) * scales[unit] for n, unit in re.findall(r"(\d+)([hms])", s)) % 86400


def to_text(n):
    h, rest = divmod(n % 86400, 3600)
    m, s = divmod(rest, 60)
    return "".join(f"{v}{unit}" for v, unit in zip((h, m, s), "hms") if v) or "0s"
