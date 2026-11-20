"""Select a submitted answer using only its text. No problem IDs, graders, future candidates or model names."""
from collections import Counter
from decimal import Decimal
from itertools import product
import re

NUMBER = re.compile(r'(?:[$£€]\s*)?([+-]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+))')


def key(answer):
    value = ' '.join(answer.strip().casefold().split()).rstrip('.,;:!?').rstrip()
    if not value:
        return None
    number = NUMBER.fullmatch(value)
    if number:
        return ('number', Decimal(number[1].replace(',', '')))
    return ('text', value)


def winner(votes, strict=False):
    counts = Counter(v for v in votes if v is not None)
    top = max(counts.values(), default=0)
    if top < 2:
        return None
    leaders = {v for v in counts if counts[v] == top}
    if strict and len(leaders) > 1:
        return None
    return next(i for i, v in enumerate(votes) if v in leaders)


def pulse(answer_stream, budget=4):
    """Read a prefix. Stop only when every possible remaining ballot yields the same deliverable."""
    votes = []
    for answer in answer_stream:
        votes.append(key(answer))
        used = len(votes)
        if used < 2:
            continue
        if used == budget:
            return winner(votes), used
        remaining = budget - used
        # Existing keys, silence, and enough distinct placeholders for all entirely new answer classes.
        alphabet = [None, *set(v for v in votes if v is not None), *(object() for _ in range(remaining))]
        possible = {winner(votes + list(extra)) for extra in product(alphabet, repeat=remaining)}
        if len(possible) == 1:
            selected = possible.pop()
            if selected is None or selected < used:
                return selected, used
    raise ValueError('a complete four-seat panel is required')


def reserve(answer_stream):
    """The crash trigger of R1 on this common four-seat pool; abstain without corroboration."""
    votes = []
    for answer in answer_stream:
        votes.append(key(answer))
        selected = winner(votes)
        if selected is not None or len(votes) == 4:
            return selected, len(votes)
        if len(votes) == 3 and (None not in votes or all(v is None for v in votes)):
            return None, len(votes)
    raise ValueError('a complete four-seat panel is required')


def fixed(answer_stream, budget, strict=False):
    values = iter(answer_stream)
    votes = [key(next(values)) for _ in range(budget)]
    return winner(votes, strict=strict), budget
