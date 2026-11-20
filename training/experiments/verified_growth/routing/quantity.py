"""Optional quantity-based chooser fitted only from earlier externally labeled observations."""
from collections import defaultdict
from decimal import Decimal, InvalidOperation
import re


_SMALL = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
          "fifteen sixteen seventeen eighteen nineteen").split()
_TENS = "twenty thirty forty fifty sixty seventy eighty ninety".split()
_COUNTS = {name: i for i, name in enumerate(_SMALL)}
_COUNTS.update({name: i * 10 for i, name in enumerate(_TENS, 2)})
_FRACTION = {name: Decimal(10) ** -power for name, power in
             (("thousandth", 3), ("millionth", 6), ("billionth", 9))}
_PREFIX = {"femto": -15, "pico": -12, "nano": -9, "micro": -6, "milli": -3, "": 0}
_UNIT = {stem + "second": Decimal(10) ** scale for stem, scale in _PREFIX.items()}
_UNIT.update({abbr: Decimal(10) ** scale for abbr, scale in
              (("fs",-15), ("ps",-12), ("ns",-9), ("us",-6), ("µs",-6), ("ms",-3), ("s",0))})
_COUNT_WORD = "(?:" + "|".join([*_COUNTS, "hundred", "thousand", "million"]) + ")"
_NUMBER = (r"(?:minus |negative |plus |positive )?(?:[+-]?(?:[0-9]+(?:,[0-9]{3})*)(?:\.[0-9]+)?"
           r"(?:e[+-]?[0-9]+)?|10\^[+-]?[0-9]+|" + _COUNT_WORD + r"(?:(?:[ -]| and )" + _COUNT_WORD + r")*)")
_C = re.compile(r"(?<!\w)(" + _NUMBER + r")\s*(?:°\s*|degrees?\s*)?(?:celsius|c)\b")
_T = re.compile(r"(?<!\w)(" + _NUMBER + r")\s+(" + "|".join(sorted(_UNIT, key=len, reverse=True)) + r")s?\b")
_F = re.compile(r"(?<!\w)(?:(?:one|a) )?(thousandth|millionth|billionth)\s+of\s+(?:a |one )?("
                + "|".join(sorted(_UNIT, key=len, reverse=True)) + r")\b")
_EXTRA = re.compile(r"[0-9]|\b(?:or|not|above|below|more|less|at least|at most|between|compared|"
                    + "|".join([*_COUNTS,"hundred","thousand","million","twice","half","double","plus","minus"]) + r")\b")


def number(text):
    if text.startswith(("minus ", "negative ")):
        return -number(text.split(" ",1)[1])
    if text.startswith(("plus ", "positive ")):
        return number(text.split(" ",1)[1])
    if text.startswith("10^"):
        exponent = int(text[3:])
        if abs(exponent) > 24:
            raise ValueError("outside supported quantity")
        return Decimal(10) ** exponent
    if re.search(r"[0-9]", text):
        value = Decimal(text.replace(",",""))
        if not value.is_finite() or abs(value.adjusted()) > 30:
            raise ValueError("outside supported quantity")
        return value
    group = total = 0
    for word in text.replace("-"," ").split():
        if word == "and":
            continue
        if word == "hundred":
            group *= 100
        elif word in ("thousand", "million"):
            total += group * (1000 if word == "thousand" else 1000000)
            group = 0
        else:
            group += _COUNTS[word]
    return Decimal(total + group)


def quantity(domain, question):
    if domain not in ("physics","engineering"):
        return None
    text = question.casefold().replace("−", "-")
    patterns = [_C] if domain == "physics" else [_T, _F]
    matches = [(pattern, hit) for pattern in patterns for hit in pattern.finditer(text)]
    if len(matches) != 1:
        return None
    rule, hit = matches[0]
    if _EXTRA.search(text[:hit.start()] + " " + text[hit.end():]):
        return None
    try:
        if rule is _F:
            return _FRACTION[hit[1]] * _UNIT[hit[2]]
        value = number(hit[1])
        return value if rule is _C else value * _UNIT[hit[2]]
    except (ValueError, InvalidOperation, KeyError):
        return None


class QuantityChooser:
    def __init__(self):
        self.memory = defaultdict(list)

    def add(self, domain, question, label):
        val = quantity(domain, question)
        if val is not None:
            self.memory[domain].append((val, label, question))

    def predict(self, req):
        val = quantity(req.domain, req.question)
        if val is None:
            return req.words[0], req.words[0], None
        points = [(v,label) for v,label,q in self.memory[req.domain] if q != req.question]
        ordered = sorted({v for v,_ in points})
        # Match a repeated labeled magnitude, or interpolate strictly between two known
        # magnitudes whose nearest labels agree. Conflicting labels or extrapolation defer.
        same = [label for v,label in points if v == val]
        evidence = []
        if len(same) >= 2:
            evidence = same
        else:
            left = [p for p in ordered if p < val]
            right = [p for p in ordered if p > val]
            if left and right:
                evidence = [label for v,label in points if v in (left[-1], val, right[0])]
        if len(set(evidence)) != 1:
            return req.words[0], req.words[0], None
        supported = evidence[0]
        return supported if supported in req.words else req.words[0], supported, str(val)
