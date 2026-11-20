"""Offline decision replay. The verifier sees only the request and proposed answers."""
from math import isqrt
from pathlib import Path
import re

from team import solo

CURRENT = ("coder_school", "untouched", "fast")
DIVERSE = ("coder_school", "yicoder15bchat", "fast")
REORDERED = ("coder_school", "fast", "untouched")
REFERENCE = Path(__file__).with_name("verifier.py").read_text()
NUM = r"([0-9]{1,7})"
ITEM = r"[+-]?[0-9]{1,7}"
SEP = r"(?:\s*,\s*(?:and\s+)?|\s+and\s+)"
ITEMS = rf"({ITEM}(?:{SEP}{ITEM}){{0,31}})"
QUOTED = r'''(?:"([A-Za-z ]{1,96})"|'([A-Za-z ]{1,96})')'''
PREFIX = re.compile(r"^(?:please\s+)?(?:what (?:is|are)|what's|find|compute|calculate|determine|"
                    r"print|return|give me|give|tell me|write a program (?:that prints|to print))\s+", re.I)
SUFFIX = re.compile(r"""(?:[.,]?\s+(?:(?:and )?(?:print|return|give) (?:only (?:the |a )?(?:number|answer|result)|the result)|and nothing else|answer (?:yes or no|with (?:only )?the number)))$""", re.I)


def contract(task):
    """Bind a whole, positive request. Unmatched text is meaningful and makes us defer."""
    if not isinstance(task, str) or len(task) > 320 or not task.isascii():
        return None
    phrase = task.strip().rstrip(".?").strip()
    phrase = SUFFIX.sub("", phrase)
    phrase = re.sub(r'''\.\s*print "yes" if it is, otherwise print "no"$''', "", phrase, flags=re.I)
    phrase = PREFIX.sub("", phrase)
    phrase = re.sub(r"^the\s+", "", phrase, flags=re.I)

    def match(expr):
        return re.fullmatch(expr, phrase, flags=re.I | re.ASCII)

    for kind, pattern in (
        ("gcd", rf"(?:greatest common (?:divisor|factor)|gcd|gcf) (?:of |for )?{NUM}(?: and |,\s*){NUM}"),
        ("divisors", rf"product of (?:all |the )*(?:positive )?(?:divisors|factors) of {NUM}"),
        ("factorial", rf"(?:factorial (?:of )?{NUM})"),
        ("digits", rf"sum of (?:the )?digits (?:in|of) (?:the (?:number|integer) )?{NUM}"),
        ("divisible", rf"(?:(?:whether|if|is) )?(?:the number )?{NUM} (?:is )?divisible by {NUM}"),
        ("percent", rf"percentage of {NUM} (?:that is )?(?:relative to|out of) {NUM}"),
        ("percent", rf"what (?:percent|percentage) (?:of {NUM} is {NUM})"),
        ("primes", rf"sum of (?:all |the )*(?:prime numbers|primes) (between|from) {NUM} (and|to|through) {NUM}(?:,? (inclusive|inclusively))?"),
    ):
        m = match(pattern)
        if not m:
            continue
        if kind == "primes":
            pre, lo, mid, hi, incl = m.groups()
            a, b = int(lo), int(hi)
            if not (0 <= a <= b <= 10000 and b - a <= 1000):
                return None
            if (pre.lower() == "between") != (mid.lower() == "and"):
                return None
            def prime(n):
                return n >= 2 and all(n % d for d in range(2, isqrt(n) + 1))
            if pre.lower() == "between" and not incl and any(prime(n) for n in (a, b)):
                return None
            return kind, [a, b]
        args = list(map(int, m.groups()))
        if kind == "percent" and phrase.lower().startswith("what "):
            args.reverse()
        if max(args) > 1_000_000 or (kind == "gcd" and not any(args)):
            return None
        if kind == "factorial" and args[0] > 30 or kind == "divisors" and not 1 <= args[0] <= 10000:
            return None
        if kind in ("percent", "divisible") and args[1] == 0:
            return None
        return kind, args
    for kind, pattern in (("mean", r"(?:arithmetic )?(?:mean|average)"),
                          ("squares", r"sum of (?:the )?squares"), ("cubes", r"sum of (?:the )?cubes")):
        m = match(rf"{pattern} (?:of )?(?:the numbers )?{ITEMS}")
        if m:
            args = [int(n) for n in re.findall(ITEM, m[1])]
            return (kind, args) if max(map(abs, args)) <= 1_000_000 else None
    for kind, pattern in (("vowels", r"(?:number of vowels in|count (?:the )?vowels in|how many vowels are (?:there )?in)"),
                          ("letters", r"(?:number of letters in|count (?:the )?letters in|how many letters are (?:there )?in)"),
                          ("reverse", r"(?:reverse of|reverse)")):
        m = match(rf"{pattern} (?:the (?:word|string|text) )?{QUOTED}")
        if m:
            value = m[1] or m[2]
            if kind == "vowels" and "y" in value.lower():
                return None
            return kind, [value]
    return None


def _vote(task, replies, order):
    tries = []
    for member in order:
        tries.append({"answer": replies.get(member) or "", "who": member})
        if len(tries) >= 2:
            winner = solo._winner(tries, solo.agreeing(tries, task), task)
            if winner:
                return {"answer": winner["answer"], "seats": [x["who"] for x in tries], "check": None}
    return {"answer": None, "seats": list(order), "check": None}


def decide(task, replies, policy, guest=None):
    """Compare logged stdout proposals. Validation failure with a bound contract abstains."""
    orders = {"current": CURRENT, "diverse": DIVERSE, "reordered": REORDERED, "verified": CURRENT}
    order = orders[policy]
    bound = contract(task) if policy == "verified" else None
    if not bound:
        return _vote(task, replies, order)
    kind, args = bound
    checked = {"kind": kind, "args": args, "calls": 0, "fuel": 0, "verdicts": []}
    seen, seats = {}, []
    for batch in (order[:2], order[2:]):
        seats.extend(batch)
        claims = [replies.get(member) for member in batch]
        fresh = list(dict.fromkeys(c for c in claims if isinstance(c, str) and 0 < len(c) <= 160 and c not in seen))
        if fresh:
            checked["calls"] += 1
            results, fuel, _ = guest.run(REFERENCE, [{"kind": kind, "args": args, "claims": fresh}])
            checked["fuel"] += fuel
            value = results[0].get("value", {})
            flags = value.get("valid", [])
            if len(flags) != len(fresh):
                checked["error"] = results[0].get("error", "missing verifier result")
                return {"answer": None, "seats": seats, "check": checked}
            checked["reference"] = value["reference"]
            seen.update(zip(fresh, flags))
        winner = None
        for member, claim in zip(batch, claims):
            valid = isinstance(claim, str) and seen.get(claim, False)
            checked["verdicts"].append({"member": member, "verified": bool(valid)})
            if valid and winner is None:
                winner = claim
        if winner is not None:
            return {"answer": winner, "seats": seats, "check": checked}
    return {"answer": None, "seats": seats, "check": checked}
