"""Trusted exact references for the small scalar grammar. This source runs inside WASI."""
from fractions import Fraction
from math import factorial, gcd, isqrt, prod
import re


def solve(row):
    kind, args, claims = row["kind"], row["args"], row["claims"]
    if kind == "gcd":
        value = gcd(*args)
    elif kind == "divisors":
        value = prod(i for i in range(1, args[0] + 1) if args[0] % i == 0)
    elif kind == "primes":
        low, high = args
        value = sum(i for i in range(max(2, low), high + 1)
                    if all(i % d for d in range(2, isqrt(i) + 1)))
    elif kind == "factorial":
        value = factorial(args[0])
    elif kind == "digits":
        value = sum(int(i) for i in str(args[0]))
    elif kind == "divisible":
        value = "yes" if args[0] % args[1] == 0 else "no"
    elif kind == "mean":
        value = Fraction(sum(args), len(args))
    elif kind in ("squares", "cubes"):
        value = sum(i ** (2 if kind == "squares" else 3) for i in args)
    elif kind == "percent":
        value = Fraction(100 * args[0], args[1])
    elif kind == "vowels":
        value = sum(ch.lower() in "aeiou" for ch in args[0])
    elif kind == "letters":
        value = sum(ch.isalpha() for ch in args[0])
    elif kind == "reverse":
        value = args[0][::-1]
    else:
        raise ValueError("unknown contract")
    valid = []
    for claim in claims:
        if not claim or len(claim) > 160:
            valid.append(False)
            continue
        text = claim.strip()
        if kind == "reverse":
            valid.append(claim == value)
        elif kind == "divisible":
            valid.append(text.lower() == value)
        else:
            if kind == "percent" and text.endswith("%"):
                text = text[:-1].strip()
            match = re.fullmatch(r"[+-]?(?:[0-9]{1,64}(?:\.[0-9]{1,48})?|\.[0-9]{1,48}|[0-9]{1,32}/[1-9][0-9]{0,31})", text)
            valid.append(bool(match) and Fraction(text) == value)
    return {"reference": str(value), "valid": valid}
