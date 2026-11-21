"""Conservative research adapter for the bank's per-parcel shipping rule."""

import re


_COUNT_WORDS = "one two three four five six seven eight nine ten".split()
_COUNT = r"(?:[1-9][0-9]{0,2}|" + "|".join(_COUNT_WORDS) + ")"
_ITEM = re.compile(
    rf"(?<![\w.+−-])(?:(?P<mult>{_COUNT})\s*(?:x|×)\s*|"
    rf"(?P<each>{_COUNT})\s+(?:parcels?|packages?)\s+(?:of|at|weighing)\s+|(?P<labelled>{_COUNT})\s+)?"
    r"(?P<grams>[1-9][0-9]{0,8})\s*(?:g|grams?|grammes?)\b"
    r"(?:\s+(?P<label>parcel|package)s?\b)?(?:\s+(?P<suffix>each)\b)?"
)
_CONVENTION = re.compile(
    r"\b(?:per[- ](?:parcel|package)(?:\s+(?:rounding|method|rule|tariff))?|"
    r"(?:parcel[- ]by[- ]parcel|package[- ]by[- ]package)(?:\s+rounding)?|"
    r"round(?:ing)?\s+(?:up\s+)?(?:the\s+weight\s+of\s+)?each\s+"
    r"(?:parcel|package)(?:\s+(?:up|separately|individually))?|"
    r"each\s+(?:parcel|package)\s+rounded\s+(?:up(?:\s+(?:separately|individually))?|separately|individually)|"
    r"round(?:ing)?\s+(?:the\s+)?(?:parcels|packages|weights|each)\s+"
    r"(?:up\s+)?(?:separately|individually))\b"
)
_INTENT = re.compile(
    r"\b(?:calculate|compute|quote|work out|figure out|how much|what(?: is|'s| would be)|"
    r"give me|tell me)\b"
)
_ALLOWED = set("""
a an and are at be by calculate can charge charges cost costs could compute delivery
dispatch do fee fees figure for from give grams how i in is it me method much my of on
our out package packages parcel parcels pay please postage price quote rule shipment
ship shipping should sum tariff tell that the these this to total use using we weigh
weighing weights what will with work would you
""".split())


def extract_shipping(message: str) -> list[int] | None:
    """Return ordered positive whole-gram weights, [] for explicit empty, else None."""
    if not isinstance(message, str) or len(message) > 2048:
        return None
    text = " ".join(message.lower().replace("’", "'").split())
    # Discard only labelled, bounded metadata. An unexplained number blocks release.
    text = re.sub(r"\border\s+(?:id\s*[:#]?\s*|#)[a-z0-9-]+\b", " ", text)
    text = re.sub(r"\b(?:order date|date)\s*:?\s*[0-9]{4}-[0-9]{2}-[0-9]{2}\b", " ", text)
    if text.count("?") > 1 or re.search(
        r"\b(?:how (?:do|can|would|should|could|will|to)|(?:can|could|should|would) (?:i|we)|"
        r"what (?:is|was) (?:the )?(?:rule|method))\b", text
    ):
        return None
    if not _INTENT.search(text) or not re.search(r"\b(?:shipping|ship|delivery|postage)\b", text):
        return None
    if not re.search(r"\b(?:costs?|fees?|charges?|price|quote|how much|postage)\b", text):
        return None
    conventions = list(_CONVENTION.finditer(text))
    if len(conventions) != 1:
        return None
    selected = conventions[0]
    if "round" not in selected.group() and not re.search(r"\b(?:total|sum)\b", text):
        return None
    text = text[:selected.start()] + " " + text[selected.end():]

    empty = re.search(r"\b(?:no parcels|no packages|zero parcels|zero packages|empty shipment)\b", text)
    items = list(_ITEM.finditer(text))
    if bool(empty) == bool(items):
        return None
    weights = []
    if empty:
        text = text[:empty.start()] + " " + text[empty.end():]
    else:
        for index, item in enumerate(items):
            if index and not re.fullmatch(r"\s*(?:,\s*(?:(?:and|plus)\s+)?|and\s+|plus\s+)\s*",
                                         text[items[index-1].end():item.start()]):
                return None
            if bool(item["each"]) != bool(item["suffix"]):
                return None
            if item["labelled"] and not item["label"]:
                return None
            count = item["mult"] or item["each"] or item["labelled"] or "1"
            n = int(count) if count.isascii() and count.isdigit() else _COUNT_WORDS.index(count) + 1
            if len(weights) + n > 256:
                return None
            weights.extend([int(item["grams"])] * n)
        text = text[:items[0].start()] + " " + text[items[-1].end():]
    text = text.replace("what's", "what is")
    if set(re.sub(r"[.,?!:()\[\]]", " ", text).split()) - _ALLOWED:
        return None
    return weights
