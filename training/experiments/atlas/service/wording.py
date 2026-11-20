"""Normalize two complete English calendar questions for the existing checked calculator."""
import re

from training.experiments.atlas.pulse.one_checked import current


# Month names are closed vocabulary. Numeric slash dates have no unambiguous default locale.
_MONTHS = {name: name for name in current.MONTHS}
_MONTHS.update({name[:3]: name for name in current.MONTHS})
_MONTHS["sept"] = "september"
_MONTH = "(?:" + "|".join(sorted(_MONTHS, key=len, reverse=True)) + ")"
_DAY = r"[0-9]{1,2}(?:st|nd|rd|th)?"
_DATE = re.compile(
    rf"(?<!\w)(?:[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}|"
    rf"(?:the )?{_DAY} (?:of )?{_MONTH}\.?,? [0-9]{{4}}|"
    rf"{_MONTH}\.? {_DAY},? [0-9]{{4}})(?!\w)"
)
_POLITE = re.compile(r"^(?:please[, ]+)?(?:(?:can|could|would) you (?:please )?(?:tell me |say )?|"
                     r"(?:tell me|let me know|i'd like to know) )?")
_WEEKDAY = r"(?:weekday|day of the week|day)"
_WEEKDAY_FORMS = (
    rf"(?:what|which) {_WEEKDAY} (?:is|was) @",
    rf"(?:what|which) {_WEEKDAY} (?:does|did|will|would) @ (?:fall|land) on",
    rf"on (?:what|which) {_WEEKDAY} (?:does|did|will|would) @ (?:fall|land)",
    rf"(?:what|which) {_WEEKDAY} @ (?:falls|fell|lands|landed) on",
    r"(?:what is |what's |give me |name |find )?(?:the )?(?:weekday|day of the week) (?:for|on|of) @",
    r"@ (?:falls|fell|lands|landed) on (?:which|what) (?:weekday|day of the week|day)",
)
_PAIR = r"(?:between @ and @|from @ (?:to|until) @)"
_DAYS = r"(?:calendar )?days"
_ELAPSED_FORMS = (
    rf"how many {_DAYS} (?:(?:are there|are|were there|elapsed|have elapsed|passed|have passed) )?{_PAIR}",
    rf"how many {_DAYS} (?:separate @ and @|apart are @ and @)",
    rf"(?:what is |what's |give me |calculate |find )?(?:the )?(?:number of {_DAYS}|difference in {_DAYS}) {_PAIR}",
    rf"count (?:the )?{_DAYS} {_PAIR}",
    rf"{_PAIR},? how many {_DAYS}(?: (?:is that|are there|elapsed|passed))?",
)


def _date(token):
    if "-" in token:
        return current._date(token)
    words = token.replace(".", "").replace(",", "").split()
    words = [word for word in words if word not in {"the", "of"}]
    first, second, year = words
    month, day = (first, second) if first in _MONTHS else (second, first)
    match = re.fullmatch(r"([0-9]{1,2})(st|nd|rd|th)?", day)
    number = int(match[1])
    if match[2]:
        suffix = "th" if 11 <= number <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
        if match[2] != suffix:
            return None
    return current._date(f"{number} {_MONTHS[month]} {year}")


def canonical_question(question):
    """Return a canonical weekday or elapsed-days question, or defer to the caller."""
    if not isinstance(question, str) or len(question) > 320 or "@" in question:
        return None
    text = " ".join(question.casefold().replace("’", "'").split())
    text = re.sub(r"[?!.]$", "", text)
    text = _POLITE.sub("", text, count=1)
    dates = [_date(match[0]) for match in _DATE.finditer(text)]
    if not dates or any(day is None for day in dates):
        return None
    frame = _DATE.sub("@", text)
    if len(dates) == 1 and any(re.fullmatch(pattern, frame) for pattern in _WEEKDAY_FORMS):
        return f"What day of the week is {dates[0].isoformat()}?"
    if (len(dates) == 2 and dates[0] <= dates[1]
            and any(re.fullmatch(pattern, frame) for pattern in _ELAPSED_FORMS)):
        return f"How many days are there from {dates[0].isoformat()} to {dates[1].isoformat()}?"
    return None
