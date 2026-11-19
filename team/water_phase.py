"""Eligibility of the pure-water label exercise at one standard atmosphere."""
from decimal import Decimal
import re


_SMALL = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
_TENS = "twenty thirty forty fifty sixty seventy eighty ninety".split()
_WORDS = "(?:" + "|".join(_TENS) + ")(?:[- ](?:" + "|".join(_SMALL[1:10]) + "))?|" + "|".join(_SMALL)
_TEMP = re.compile(r"(?<![\w.+-])(?P<sign>minus\s+|negative\s+|plus\s+|[+-])?"
                   r"(?P<value>\d+(?:\.\d+)?|\.\d+|" + _WORDS + r")\s*(?:degrees?\s*)?(?:°\s*)?(?:celsius|c)\b")
_PRESSURE = re.compile(r"(?<![\w.+-])(?:1(?:\.0+)?\s*(?:atm|atmospheres?)|one atmosphere|standard atmospheric pressure)\b")
_OUTSIDE = re.compile(
    r"[\d±−–—<>≤≥%~]|\b(?:not|never|except|false|incorrect|wrong|isn['’]t|wasn['’]t|wouldn['’]t|without|non[- ]?pure|impure|"
    r"salt\w*|brine|sea\s*water|tap|mineral|river|lake|spring|brackish|sugar\w*|alcohol\w*|ethanol|solute\w*|solution|mixture|mix\w*|dissolv\w*|"
    r"contain\w*|additive\w*|contamin\w*|heavy|supersatur\w*|supercool\w*|superheat\w*|metastable|"
    r"rapid\w*|transient|nonequilibrium|non-equilibrium|heated|cooled|minus|negative|plus|between|from|"
    r"range|interval|below|above|under|over|roughly|around|approximately|about|hundred|thousand|point|fahrenheit|kelvin|"
    r"celsius|degrees?|atm|atmospheres?|bar|kpa|pa|psi|torr|vacuum|gauge|relative|partial|altitude|"
    r"half|double|twice|triple|percent|pressuri[sz]\w*)\b")


def equilibrium_phase(message):
    """Return one phase well inside the single-temperature pure-water exercise, else abstain."""
    text = " ".join(message.casefold().replace("−", "-").split())
    readings, pressures = list(_TEMP.finditer(text)), list(_PRESSURE.finditer(text))
    if len(readings) != 1 or len(pressures) != 1 or not re.search(r"\bwater\b", text):
        return None
    reading = readings[0]
    remainder = _PRESSURE.sub("", text[:reading.start()] + " " + text[reading.end():])
    if (_OUTSIDE.search(remainder) or re.search(r"(?<!\w)[+-](?!\w)|\b(?:at least|at most|up to|other than|water (?:with|and))\b", remainder)
            or re.search(r"\b(?:" + _WORDS + r")\s+(?:(?:or|to|and)\s+)?$", text[:reading.start()])):
        return None
    value = reading["value"]
    if len(value) > 32:
        return None
    if value[0].isalpha():
        parts = value.replace("-", " ").split()
        integer = (_TENS.index(parts[0]) + 2) * 10 if parts[0] in _TENS else _SMALL.index(parts[0])
        degrees = Decimal(integer + (_SMALL.index(parts[1]) if len(parts) == 2 else 0))
    else:
        degrees = Decimal(value)
    if (reading["sign"] or "").strip() in {"minus", "negative", "-"}:
        degrees = -degrees
    if degrees <= Decimal("-273.15") or degrees > 300:
        return None  # Extreme temperatures exceed the ordinary condensed-phase and steam exercise.
    if abs(degrees) <= Decimal("0.1") or abs(degrees - 100) <= Decimal("0.1"):
        return None
    return "solid" if degrees < 0 else "gas" if degrees > 100 else "liquid"


_PHASES = ('solid', 'liquid', 'gas')
# Strip optional output formatting before checking that the whole request is a phase question.
_FORMAT = re.compile(r'\b(?:answer|reply|respond|return|give (?:me )?(?:the )?answer)\s+'
                     r'(?:(?:in|with|using|as|only|just|exactly|a|an|the|one|single|short|brief)\s+)*'
                     r'(?:sentence|word|label|phase(?: name)?)\b(?: only)?')
_PHASE_WORDS = set(('a an the at and is it its of in as on to be will would does do my this that sample '
                    'pure water distilled ordinary equilibrium physical matter normally stable state phase '
                    'what which choose pick select classify label applies holds has occupies exists expect '
                    'give name please only just solid liquid gas or for assume assuming conditions sample '
                    'under these those standard reading pressurevalue').split())


def standalone_phase(message, history=()):
    """A complete phase-only request. Any history, other deliverable or unspecified condition defers."""
    if history or not isinstance(message, str) or len(message) > 650 or 'water' not in message.casefold():
        return None
    from .domain_intent import requests_choice
    if not requests_choice(message, 'water_phase', _PHASES):
        return None
    text = ' '.join(message.casefold().replace('−', '-').split())
    if text.count('?') > 1 or not re.search(r'\b(?:pure|distilled) water\b', text):
        return None
    expected = equilibrium_phase(text)
    if expected is None:
        return None
    remaining = _FORMAT.sub('', _TEMP.sub(' reading ', _PRESSURE.sub(' pressurevalue ', text)))
    if re.search(r'[^a-z\s.,?!:;\-]', remaining) or set(re.findall(r'[a-z]+', remaining)) - _PHASE_WORDS:
        return None
    return expected


def _phase_answer(proposed):
    pattern = (r'(?:(?:(?:the |this )?(?:pure |distilled )?water|it|the phase|the state) (?:is|would be) )?'
               r'(?:in )?(?:the |a |an |its )?(solid|liquid|gas)(?: (?:state|phase))?[.!]?')
    match = re.fullmatch(pattern, ' '.join(proposed.casefold().split()))
    return match.group(1) if match else None


def confirms(expected, proposed):
    """Accept a bare phase or an affirmative phase sentence without conflicting extra claims."""
    return expected in _PHASES and _phase_answer(proposed) == expected


_PURE = r'(?:pure|distilled) water'
_SUBJECT = (r'(?:(?:(?:the|a|this|that) )?(?:sample of )?' + _PURE
            + r'|it|(?:the|this|that) (?:water|sample))')
_TARGET = r'(?:phase|state)(?: of matter)?'
_WATER_QUESTION = re.compile(
    r'\b(?:' + _TARGET + r' (?:(?:of|for) |(?:is|does|would|will|should|can) (?:you expect (?:for )?)?)?' + _SUBJECT
    + r'|(?:its|' + _SUBJECT + r"[’']s) (?:physical |equilibrium )?" + _TARGET
    + r'|' + _SUBJECT + r' (?:is|be|remain|exist) in (?:what|which) ' + _TARGET + r')\b')
_WATER_SETUP = re.compile(r'^(?:(?:suppose|consider|given|for|assume) (?:that )?)?'
                          r'(?:(?:a|the|this|our) )?(?:sample of )?' + _PURE + r'\b')


def output_check_phase(message, history=()):
    """A condition for rejecting a contradictory scalar output, never permission to answer the whole request."""
    if (history or not isinstance(message, str) or len(message) > 1200
            or '(This continues a conversation.' in message):
        return None
    text = ' '.join(message.casefold().replace('−', '-').split())
    if text.count('?') > 1 or not re.search(r'\b' + _PURE + r'\b', text):
        return None
    expected = equilibrium_phase(text)
    if expected is None:
        return None
    # Bind the phase to the water in a question or a direct command. A mere phase mention
    # in some other assignment does not make its output a water-phase measurement.
    water_subject = False
    for clause in re.split(r'(?<=[!?;])\s+|\.(?!\d)\s+', text):
        water_subject = water_subject or bool(_WATER_SETUP.match(clause))
        asked = '?' in clause or re.match(r'(?:please )?(?:what|which|identify|name|state|choose|select|give|report|determine)\b', clause)
        options = ' or ' in clause and sum(bool(re.search(r'\b' + label + r'\b', clause)) for label in _PHASES) >= 2
        target = _WATER_QUESTION.search(clause)
        if options and not target:
            target = re.search(r'\b(?:is|would|will|classify|for) ' + _SUBJECT + r'\b', clause)
        if asked and target and (water_subject or re.search(_PURE, target[0])):
            return expected
        # A pure-water setup can precede a separate question about that sample.
        if not (re.search(r'\b' + _PURE + r'\b', clause) or _TEMP.search(clause) or _PRESSURE.search(clause)):
            break
    return None


def contradicts(expected, proposed):
    """Only a complete scalar claim can contradict this check; prose and artifacts pass through."""
    if not expected:
        return False
    text = ' '.join(proposed.casefold().split())
    actual = _phase_answer(text)
    if actual is None:
        assertion = re.fullmatch(
            r'(?:(?:under these conditions|at equilibrium),? )?'
            r'(?:(?:(?:(?:the|this) )?(?:(?:pure|distilled) )?water|the sample|this sample|it|the phase|the state) '
            r'(?:is|would be|will be) )?'
            r'(?:in )?(?:(?:the|a|its) )?(solid|liquid|gas|gaseous|ice|steam|water vapou?r)'
            r'(?: (?:state|phase))?(?: (?:under these conditions|at equilibrium))?[.!]?', text)
        if assertion:
            word = assertion[1]
            actual = {'ice': 'solid', 'steam': 'gas', 'gaseous': 'gas', 'water vapor': 'gas', 'water vapour': 'gas'}.get(word, word)
    return actual is not None and actual != expected


WITHHELD = 'The proposed phase conflicts with the equilibrium check for the stated pure water. I could not confirm the requested answer.'


def checked_reply(message, expected, *, source, proposed=None):
    bare = bool(re.search(r'\b(?:(?:one|single)[ -](?:word|label)|(?:word|label) only|'
                          r'(?:just|only) (?:the )?(?:phase|label)|choose|pick|select)\b', message, re.I))
    text = expected if bare and 'sentence' not in message.casefold() else f'The water is {expected}.'
    detail = dict(method='pure_water_equilibrium_1atm', phase=expected, source=source)
    if proposed is not None:
        detail['model_answer'] = proposed[:500]
    return dict(text=text, worked=False, agreed=None, task='', dir='', files=[], seconds=0, water_phase_check=detail)
