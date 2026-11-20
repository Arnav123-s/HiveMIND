"""Current standalone calculator certificate. The historical G49 evaluator remains in certificate.py."""
from datetime import date
from decimal import Context, Decimal, localcontext
import math
import re


MONTHS = 'january february march april may june july august september october november december'.split()
WEEKDAYS = 'monday tuesday wednesday thursday friday saturday sunday'.split()
MONTH = '(?:' + '|'.join(MONTHS) + ')'
DATE = rf'(?:[0-9]{{1,2}} {MONTH} [0-9]{{4}}|[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}})'
AMOUNT = r'[0-9]{1,8}(?:\.[0-9]{1,2})?'
WEEKDAY = re.compile(rf'(?:what|which) day of the week is ({DATE})\?', re.I)
DAYS = re.compile(rf'how many days (?:are there )?(?:from|between) ({DATE}) (?:to|and) ({DATE})\?', re.I)
GCD = re.compile(r'what is the (?:greatest common divisor|gcd) of ([0-9]{1,12}) and ([0-9]{1,12})\?', re.I)
TEMPERATURE = re.compile(r'what is ([+-]?[0-9]{1,6}(?:\.[0-9]{1,4})?) degrees (celsius|fahrenheit) in (fahrenheit|celsius)\? one decimal place\.', re.I)
PRICE = re.compile(rf'(?:a|an) [a-z]+ costs ({AMOUNT}) dollars and the price (rises|falls) by ([0-9]{{1,2}})%\. what is the new price\?', re.I)


def _date(text):
    # The calling full-match guards allow only ISO or a day, full English month, and year.
    try:
        if '-' in text:
            return date.fromisoformat(text)
        day, month, year = text.split()
        return date(int(year), MONTHS.index(month) + 1, int(day))
    except ValueError:
        return None


def expected(prompt):
    if not isinstance(prompt, str) or len(prompt) > 260:
        return None
    text = ' '.join(prompt.casefold().split())
    match = WEEKDAY.fullmatch(text)
    if match:
        day = _date(match[1])
        return ('weekday', WEEKDAYS[day.weekday()]) if day else None
    match = DAYS.fullmatch(text)
    if match:
        start, end = map(_date, match.groups())
        return ('days', (end-start).days) if start and end and end >= start else None
    match = GCD.fullmatch(text)
    if match:
        a, b = map(int, match.groups())
        return ('gcd', math.gcd(a, b)) if a and b else None
    match = TEMPERATURE.fullmatch(text)
    if match and match[2] != match[3]:
        with localcontext(Context(prec=28)):
            value = Decimal(match[1])
            # Express the exact answer in tenths as numerator / denominator. An exact half
            # has two permitted results unless the caller specifies a tie convention.
            numerator, denominator = ((value-32)*50, 9) if match[2] == 'fahrenheit' else (value*18+320, 1)
            if 2 * abs(numerator % denominator) == denominator:
                return None
            return match[3], (numerator / denominator / 10).quantize(Decimal('0.1'))
    match = PRICE.fullmatch(text)
    if match:
        with localcontext(Context(prec=28)):
            price = Decimal(match[1])
            percent = int(match[3]) * (1 if match[2] == 'rises' else -1)
            result = price * (100+percent) / 100
            return ('dollars', result) if result == result.quantize(Decimal('0.01')) else None
    return None


def certify(prompt, answer):
    contract = expected(prompt)
    if contract is None or not isinstance(answer, str) or len(answer) > 100:
        return False
    value = ' '.join(answer.casefold().strip().split()).removesuffix('.')
    kind, want = contract
    if kind == 'weekday':
        return value == want
    if kind in ('gcd', 'days'):
        unit = '(?: days?)?' if kind == 'days' else ''
        match = re.fullmatch(rf'(?:{kind}: )?([0-9]{{1,15}}){unit}', value)
        return bool(match and int(match[1]) == want)
    if kind == 'dollars':
        # A permitted eight-digit starting price can rise to a nine-digit result.
        match = re.fullmatch(r'(?:new price: )?\$?([0-9]{1,9}(?:\.[0-9]{1,2})?)(?: dollars?)?', value)
    else:
        unit = 'c' if kind == 'celsius' else 'f'
        match = re.fullmatch(rf'([+-]?[0-9]{{1,8}}\.[0-9])(?:\s*(?:degrees? |°\s*)?(?:{kind}|{unit}))?', value)
    return bool(match and Decimal(match[1]) == want)
