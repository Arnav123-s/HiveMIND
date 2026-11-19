"""Check two explicit four-reading sensor banks using their saved four-bit sender pair."""
from decimal import Decimal, InvalidOperation, localcontext
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import time


ASSET = Path(__file__).with_name('assets') / 'sensor-banks-four-bit.json'
ASSET_SHA256 = '4bd8cb3db998581413c58484faadee35962d06d34593ad210b40577d67a21f9c'
REQUEST = re.compile(r'^\s*check\s+sensor\s+banks\s*(?=\[)', re.I)
BANKS = re.compile(r'(\[[^\[\]]*\])\s+and\s+(\[[^\[\]]*\])\s*[.!?]?\s*', re.I)
FORMAT = ('Use “Check sensor banks [x0,x1,x2,x3] and [y0,y1,y2,y3]” with four JSON numbers per bank. '
          'Readings may have up to 12 decimal places and absolute value up to one trillion.')
FLOAT32 = struct.Struct('f')


def _bank(block):
    values = json.loads(block, parse_int=Decimal, parse_float=Decimal)
    if not isinstance(values, list) or len(values) != 4:
        raise ValueError('expected four readings')
    clean = []
    for v in values:
        if not isinstance(v, Decimal) or not v.is_finite() or v.copy_abs() > 10**12:
            raise ValueError('invalid reading')
        if v.is_zero():
            v = Decimal(0)
        elif v.as_tuple().exponent < -12:
            # Insignificant trailing zeros do not consume the fractional precision allowance.
            digits = ''.join(map(str, v.as_tuple().digits))
            trailing_zeroes = len(digits) - len(digits.rstrip('0'))
            if v.as_tuple().exponent + trailing_zeroes < -12:
                raise ValueError('too many decimal places')
        clean.append(v)
    return clean


@lru_cache(maxsize=1)
def _model():
    body = ASSET.read_bytes()
    if hashlib.sha256(body).hexdigest() != ASSET_SHA256:
        raise ValueError('unrecognized four-bit sensor asset')
    return json.loads(body)


def _f32(value):
    return FLOAT32.unpack(FLOAT32.pack(value))[0]


def _send(values, sender):
    # The artifact's DeployedLayer first quantizes all four inputs to signed 8-bit
    # activations. Its learned scalar output is compressed to a four-bit message.
    readings = [_f32(float(v)) for v in values]
    scale = max(_f32(1e-5), *(abs(v) for v in readings))
    integers = [round(_f32(_f32(v * 127) / scale)) for v in readings]
    activated = [_f32(_f32(n * scale) / 127) for n in integers]
    dot = _f32(sum(_f32(x * w) for x, w in zip(activated, sender['weights'])))
    score = _f32(dot + sender['bias'])
    return round(_f32(_f32(_f32(math.tanh(score)) + 1) * 7.5))


def _pair(left, right):
    data = _model()
    codes = [_send(bank, sender) for bank, sender in zip((left, right), data['senders'])]
    cell = int(data['reader'][16*codes[0] + codes[1]])
    return codes, (bool(cell & 2), bool(cell & 1))


def _text_number(value):
    text = format(value, 'f')
    return (text.rstrip('0').rstrip('.') if '.' in text else text) if value else '0'


def _yes(value):
    return 'yes' if value else 'no'


def answer(message):
    """Return a talk result only for the explicit two-bank request."""
    if not isinstance(message, str) or not (start := REQUEST.match(message)):
        return None
    started = time.monotonic()
    result = {'task': message, 'dir': '', 'files': [], 'worked': True}
    try:
        parsed = BANKS.fullmatch(message, start.end()) if len(message) <= 512 else None
        if parsed is None:
            raise ValueError('expected two short arrays')
        left, right = (_bank(part) for part in parsed.groups())
    except (ValueError, InvalidOperation):
        result.update(text=FORMAT, agreed=False, sensor_banks={'status':'invalid'},
                      seconds=round(time.monotonic()-started, 4))
        return result
    with localcontext() as ctx:
        # At most 13 integer and 12 fractional places per input, including cancellation.
        ctx.prec = 32
        x = left[0] + left[1] - left[2]
        y = right[0] - right[1] + right[2]
        raw = ((x > 0) != (y > 0), x + y > 0)
    values = [_text_number(x), _text_number(y)]
    details = {'status':'checked', 'measurements':values, 'different_positivity':raw[0], 'positive_sum':raw[1]}
    lines = [f'Bank X (x0 + x1 − x2) = {values[0]}. Bank Y (y0 − y1 + y2) = {values[1]}. Both fourth entries are reserved in the raw check.',
             f'One positive and one nonpositive: {_yes(raw[0])}. Positive sum: {_yes(raw[1])}.']
    try:
        codes, predicted = _pair(left, right)
    except (OSError, ValueError):
        details.update(mode='raw_only', pair_agrees=None)
        lines.append('Returned the raw calculation. The saved four-bit pair is unavailable.')
    else:
        details.update(mode='checked_pair', codes=codes, pair_predictions=list(predicted), pair_agrees=predicted==raw)
        if predicted == raw:
            lines.append(f'Four-bit codes {codes[0]} and {codes[1]} agreed with both raw checks.')
        else:
            lines.append(f'Four-bit codes {codes[0]} and {codes[1]} predicted {_yes(predicted[0])} and '
                         f'{_yes(predicted[1])}, respectively. The raw checks above give the corrected answers.')
    result.update(text='\n'.join(lines), sensor_banks=details, agreed=True, seconds=round(time.monotonic()-started,4))
    return result
