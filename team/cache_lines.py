"""Count aligned, zero-origin cache lines occupied by one explicit contiguous byte access."""
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class Access:
    line_size: int
    start: int
    width: int

    def details(self):
        end = self.start + self.width - 1
        first, last = self.start // self.line_size, end // self.line_size
        return dict(line_bytes=self.line_size, start_address=self.start, access_bytes=self.width,
                    end_address=end, first_line=first, last_line=last, count=last - first + 1)


_WORDS = dict(zip(('zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen '
                   'fifteen sixteen seventeen eighteen nineteen twenty').split(), range(21)))
_SPELLED = re.compile(r'\b(?:' + '|'.join(_WORDS) + r')\b')
_NUMBER = r'(?<!\w)(0x[\da-f]{1,16}|[0-9]{1,20})(?!\w)'
_B = r'[ -]*bytes?\b'
_ACCESS = r'(?:loads?|reads?|stores?|writes?|access(?:es)?|fetch(?:es)?)'
_LINE = r'(?:cache[ -]+)?lines?\b'
_COUNT = re.compile(r"\b(?:how many|(?:what is |what's )?(?:the )?(?:number|count) of|count(?: the)?|give (?:the )?count of)"
                    r'\s+(?:(?:different|distinct|unique|aligned|physical|separate|individual) )*' + _LINE)
_SIZE = (rf'{_NUMBER}{_B}[ -]+(?:cache[ -]+)?lines?\b',
         rf'\b(?:cache[ -]+)?line size\s*(?:is|of|=|:)?\s*{_NUMBER}{_B}',
         rf'\bcache[ -]+lines?\s+(?:are |is |of |uses? |hold |contain |have )?(?:each )?{_NUMBER}{_B}')
_ALIGNMENT = (rf'\b(?:divisible by|multiples? of)\s+{_NUMBER}(?:{_B})?',
              rf'\b(?:on|to|at)\s+{_NUMBER}{_B}[ -]+boundar(?:y|ies)',
              rf'\b(?:aligned (?:at|on|to)|boundaries (?:every|at))\s+{_NUMBER}{_B}')
_ORIGIN = r'\b(?:cache[ -]+lines?|line boundaries) (?:begin|start) (?:at|from) (?:byte )?(?:address )?0\b'
_ADDRESS = (rf'\b(?:starting |start |begins? |beginning )?(?:at |from )?(?:byte |memory )?address\s*(?:is |of |at |:|=)?\s*{_NUMBER}',
            rf'\b(?:start(?:s|ing)?|begin(?:s|ning)?|read(?:ing)?|load(?:ing)?)\s+(?:at|from) (?:byte\s+)?{_NUMBER}',
            rf'\b(?:at|from)\s+{_NUMBER}(?![ -]*bytes?\b)')
_WIDTH = (rf'{_NUMBER}(?:[ -](?:consecutive|contiguous|adjacent))?{_B}[ -]+(?:contiguous[ -]+|memory[ -]+)?{_ACCESS}\b',
          rf'\b(?:{_ACCESS}|reading|writing|access width|width|length)\s*(?:spans |covers |of |is |:|=)?\s*{_NUMBER}(?:[ -](?:consecutive|contiguous|adjacent))?{_B}',
          rf'{_NUMBER}[ -](?:consecutive|contiguous|adjacent){_B}',
          rf'\b(?:these|those|the)\s+{_NUMBER}{_B}')
_EXACT = re.compile(r'\b(?:single (?:integer|number)|(?:only|just) (?:the |an? |one )?(?:integer|number|count)|(?:integer|number|count) only)\b')
# Unsupported layouts and conditional/aggregate questions cannot use the single-access formula.
_OTHER = re.compile(
    r'\b(?:or|except|exclude|instead|not|minus|negative|up to|at least|at most|maybe|might|possibly|maximum|minimum|'
    r'capacity|fit|sets?|ways?|repeated|separately|also|wrap\w*|strid\w*|scatter\w*|gather\w*|prefetch\w*|'
    r'non[ -]?contiguous|offset|miss(?:es)?|hits?|respectively|alternat\w*|only every|every other|'
    r'all|fully|entirely|only the first|only the last|bit[s]?|either|another|twice|again)\b|'
    r'cache[ -]+lines? (?:are )?(?:un|mis)aligned|\b(?:un|mis)aligned cache|'
    r'\band (?:how|what|why|explain|output|list|give)\b|[<>/+*]|\d[.,]\d|(?<!\w)-\d')
_MAX = (1 << 64) - 1


def _word_number(match):
    return str(_WORDS[match.group(0)])


def parse(message):
    """Accept only a single line-count question with identified size, alignment, address and width."""
    if not isinstance(message, str) or len(message) > 1000 or 'cache' not in message.lower():
        return None
    text = ' '.join(message.lower().replace('‑', '-').replace('–', '-').split())
    line_count = re.search(r'\bcache\b', text) and _COUNT.search(text)
    alignment = re.search(r'\balign(?:ed|ment)\b|\bboundar(?:y|ies)\b|\bmultiples? of\b', text)
    if not line_count or not alignment or not re.search(r'\b' + _ACCESS + r'\b', text):
        return None
    if _OTHER.search(text) or text.count('?') > 1:
        return None
    text = re.sub(r'\b(?:one|a) (?:single )?(?:integer|number)\b', 'integer', text)
    text = _SPELLED.sub(_word_number, text)
    # An explicit nonzero line-grid origin changes the position of every boundary.
    if re.search(r'\baligned (?:at|to) (?:byte )?address (?!0\b|addresses\b)\w+', text):
        return None
    text = re.sub(_ORIGIN, ' ', text)

    def take(patterns):
        nonlocal text
        values = set()

        def extract(match):
            token = match.group(1)
            values.add(int(token, 16 if token.startswith('0x') else 10))
            return ' '

        for pattern in patterns:
            text = re.sub(pattern, extract, text)
        return values

    sizes = take(_SIZE)
    boundaries = take(_ALIGNMENT)
    addresses = take(_ADDRESS)
    widths = take(_WIDTH)
    if any(len(values) != 1 for values in (sizes, addresses, widths)) or (boundaries and boundaries != sizes):
        return None
    if re.search(r'\d|\b(?:kib|mib|end(?:s|ing)? at)\b', text):
        return None
    size, start, width = next(iter(sizes)), next(iter(addresses)), next(iter(widths))
    if not 0 < size <= _MAX or not width or start + width - 1 > _MAX:
        return None
    return Access(size, start, width)


def confirms(access, printed):
    result = re.fullmatch(r'\s*([0-9]{1,20})(?:\s+(?:cache[ -]+)?lines?)?\.?\s*', printed, re.I)
    return bool(result and int(result.group(1)) == access.details()['count'])


def answer(message):
    access = parse(message)
    if access is None:
        return None
    detail = access.details()
    if _EXACT.search(message.lower()):
        text = str(detail['count'])
    else:
        noun = 'line' if detail['count'] == 1 else 'lines'
        text = (f"{detail['count']} cache {noun}. The access covers byte addresses {access.start} through "
                f"{detail['end_address']} inclusive. With {access.line_size} bytes per line, "
                f"the first line index is {detail['first_line']} and the last is {detail['last_line']} (counting from 0).")
    return dict(text=text, worked=True, agreed=True, task=message, dir='', files=[], seconds=0,
                cache_lines=dict(method='aligned_byte_interval', **detail))
