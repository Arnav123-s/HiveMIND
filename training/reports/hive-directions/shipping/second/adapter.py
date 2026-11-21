"""Pilot for direct fee requests against the local depot's retained parcel rule."""

import re


_WORDS = "one two three four five six seven eight nine ten eleven twelve".split()
_COUNT = r"(?:[1-9][0-9]{0,2}|" + "|".join(_WORDS) + ")"
_PARCEL = r"(?:parcels?|packages?|box(?:es)?|packets?|mailers?)"
_UNIT = r"(?:g|grams?|grammes?)\b"
_SHIP = r"\b(?:ship|send|shipping|shipment|postage|delivery|dispatch|post)\b"
_PRICE = r"\b(?:fees?|costs?|prices?|charge[ds]?|pay|payable|owe|postage|quote|how much)\b"
_REQUEST = (
    r"\b(?:how much|what(?:'s| is| would| will| does| do| should| are)|calculate|compute|"
    r"quote|price|estimate|work out|figure out|give me|tell me|find|determine|need|want|looking for)\b"
)
_DECLINE = re.compile(
    r"\b(?:not|no|never|don't|can't|won't|cannot|isn't|without|except|exclude|ignore|skip|"
    r"cancel|instead|replace\w*|corrected|correction|revised|previous\w*|formerly|original\w*|actually|"
    r"maybe|either|or|roughly|approximately|unknown|unsure|unweighed|unconfirmed|missing|"
    r"uncertain|perhaps|tbd|at least|at most|between|more than|less than|probably|around|"
    r"pending|unavailable|outdated|old weight|earlier|previously|superseded|together as one|rule change|pooled|aggregate|combined weight|total weight|weights? combined|round once|whole shipment weight|whole order weight|"
    r"free shipping|free postage|flat[- ]rate|storage|purchase|buy|freight|carrier|discount\w*|express|priority|international|overnight|customs|insurance|"
    r"surcharge|tax|vat|courier|fedex|ups|usps|dhl|premium|alternative|different|tariffs|"
    r"return label|book|tracking|track|schedule|cheapest|compare|explain|describe|teach|definition|define|meaning|mean|why|whether|"
    r"how it works|round down|nearest|per pound|per kilo|per gram|tutorial|formula|example|hypothetical|translate|write|email|refund|invoice me|"
    r"letters?|stamps?|ingredients?|contents?|tare|packaging weight|for packaging|bubble wrap|weight limit|capacity|kilograms?|kg|"
    r"euros?|dollars?|pounds?|lbs?|ounces?|oz|milligrams?|mg|liters?|litres?|centimeters?|centimetres?|cm|mm)\b|"
    r"\bhow much (?:does|do|would|did) [^?.]{0,30}\bweigh\b|"
    r"\bhow (?:do|can|should|would) (?:i|we|you) (?:calculate|work out|compute)|"
    r"\b(?:how to|about\s+\d|per\s+\d|each\s+started|per\s+started)\b"
)
# A count can expand a mass only when syntax binds it to that mass.
_ITEM = re.compile(
    rf"(?<![\w.+−–-])(?:(?P<mult>{_COUNT})\s*[x×]\s*|"
    rf"(?P<named>{_COUNT})\s+{_PARCEL}\s+(?:(?:at|of|weighing|weighs?|is|are)\s+)?"
    rf"(?=[0-9]+\s*{_UNIT}\s+(?:each|apiece)\b)|"
    rf"(?P<label>{_COUNT})\s+(?=[0-9]+\s*{_UNIT}\s+{_PARCEL}\b))?"
    rf"(?P<grams>[1-9][0-9]{{0,8}})\s*{_UNIT}"
    rf"(?:\s*[x×]\s*(?P<post>{_COUNT})\b)?"
)
_EMPTY = re.compile(r"\b(?:no (?:parcels|packages|boxes)|zero (?:parcels|packages|boxes)|"
                    r"0 (?:parcels|packages|boxes)|empty shipment)\b")
_METADATA = re.compile(
    r"\b(?:order|reference|ref|tracking|invoice)\s*(?:number\s*|id\s*|no\.\s*|#\s*|:\s*)?"
    r"(?=[a-z0-9-]*\d)[a-z0-9]+(?:-[a-z0-9]+)*\b|"
    r"\b(?:parcel|package|box)\s*#?\d+\s*(?=[:=])|"
    r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})\b"
)


def _count(value):
    return int(value) if value.isdigit() else _WORDS.index(value) + 1


def extract_shipping(message: str) -> list[int] | None:
    if not isinstance(message, str) or len(message) > 2048:
        return None
    text = " ".join(message.lower().replace("’", "'").split())
    domain = re.search(_SHIP, text) or (re.search(r"\bdepot\b", text) and re.search(rf"\b{_PARCEL}\b", text))
    if not domain or not re.search(_PRICE, text):
        return None
    # Accept a short request such as "Shipping fee for my parcels, please?".
    if not re.search(_REQUEST, text) and not re.search(
        r"\b(?:shipping|depot|postage|delivery)\b.{0,24}\b(?:fee|cost|quote|charge)\b"
        r".*(?:\?|please\b)", text
    ):
        return None
    text = _METADATA.sub(" ", text)
    empty = _EMPTY.search(text)
    if empty:
        text = text[:empty.start()] + " " + text[empty.end():]
    if _DECLINE.search(text) or text.count("?") > 1:
        return None
    # Bracketed weight lists explicitly declare one unit for every element.
    text = re.sub(r"\b(?:parcel\s+)?weights?(?:_g|\s*\(\s*(?:g|grams)\s*\)|\s+in\s+grams)"
                  r"\s*[:=]?\s*\[\s*([1-9][0-9]*(?:\s*,\s*[1-9][0-9]*)*)\s*\]",
                  lambda m: ", ".join(v.strip() + "g" for v in m[1].split(",")), text)
    # A comma with three following digits and no space is a thousands separator.
    text = re.sub(r"(?<![\d,])([1-9]\d{0,2}(?:,\d{3})+)\s*(?=" + _UNIT + ")",
                  lambda m: m[1].replace(",", ""), text)
    weights = []
    parts = []
    position = 0
    for item in _ITEM.finditer(text):
        counts = [value for key, value in item.groupdict().items() if key != "grams" and value]
        if len(counts) > 1:
            return None
        count = _count(counts[0]) if counts else 1
        if len(weights) + count > 256:
            return None
        weights.extend([int(item["grams"])] * count)
        parts.extend((text[position:item.start()], " @ "))
        position = item.end()
    if bool(empty) == bool(weights):
        return None
    rest = "".join(parts) + text[position:]
    # Independent count declarations must agree with the extracted shipment.
    rest = re.sub(rf"\b(?:1|one)\s+{_PARCEL}\s+(?:weighs|is|at|of)\s+@", " @ ", rest)
    for count in re.findall(rf"\b({_COUNT})\s+{_PARCEL}\b", rest):
        if _count(count) != len(weights):
            return None
    rest = re.sub(rf"\b{_COUNT}\s+{_PARCEL}\b", " ", rest)
    if re.search(r"\d|[$€£]|\b(?:" + "|".join(_WORDS) + r"|zero|several|multiple)\b", rest):
        return None
    if re.search(r"\b(?:and|plus|also)\s+(?:a|an)\s+" + _PARCEL +
                 r"\b(?!\s*(?:(?:is|of|at|weighs|weighing)\s+)?@)", rest):
        return None
    if re.search(r"\b(?:another|additional|extra|other)\s+" + _PARCEL +
                 r"\b(?!\s*(?:(?:is|of|at|weighs|weighing)\s+)?@)", rest):
        return None
    if re.search(r"\b(?:and|plus)\s+(?:more|others|another)\b(?!\s*(?:@|(?:parcel|package|box|weighs|weighing|is)\b))", rest):
        return None
    if re.search(r"\b(?:per|every|next|started|about)\s*@|@\s*[-–+/]\s*@|"
                 r"@\s*(?:blocks?|steps?|increments?|brackets?)\b", rest):
        return None
    return weights
