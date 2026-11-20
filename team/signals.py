"""A small saved pair of text senders and their advisory domain reader. Standard library only."""
import base64
from dataclasses import dataclass
from functools import lru_cache
import gzip
import hashlib
import json
import math
from pathlib import Path
import re


DOMAINS = ('coding', 'math', 'physical_science', 'conversation', 'machine_learning', 'computer_engineering')
ROLES = ('request', 'context')
VERSION = 1
TASK = 'request-domain'
LEVELS = 31
ASSET = Path(__file__).with_name('assets') / 'request-signals-v1.json.gz'
ASSET_DIGEST = '5b4dae6310c3cb144d4f477199f426cbfaf0cc272a1869379060322512d75350'
TOKENS = re.compile(r'c\+\+|c#|[a-z]+(?:-[a-z]+)*|\d+(?:\.\d+)?|[+*/^%<>=−×÷√∫∑]', re.I)
MATH_GLYPHS = {'+', '*', '/', '^', '%', '<', '>', '=', '−', '×', '÷', '√', '∫', '∑'}


@dataclass(frozen=True)
class Frame:
    task: str
    role: str
    version: int
    sender: str
    bundle_id: str
    payload: tuple


def features(text):
    words = ['#num' if w[0].isdigit() else w for w in TOKENS.findall(text[:4096].lower())][:200]
    vals = {}
    def add(key, value):
        vals[key] = max(vals.get(key, 0), value)
    for word in words:
        add('w:' + word, 1.0)
        if len(word) >= 4:
            padded = '^' + word + '$'
            for i in range(len(padded) - 2):
                add('c:' + padded[i:i+3], .25)
    for a, b in zip(words, words[1:]):
        add('b:' + a + ' ' + b, .8)
    if '#num' in words and MATH_GLYPHS.intersection(words):
        add('s:numeric-expression', 1.4)
    return vals


def _softmax(values):
    off = max(values)
    weights = [math.exp(v-off) for v in values]
    total = sum(weights)
    return [w/total for w in weights]


def _dense(layer, inputs):
    return _softmax([b + sum(x*w for x, w in zip(inputs, row)) for b, row in zip(layer['bias'], layer['w'])])


def reader_features(request, context):
    q = [x/LEVELS for x in request]
    c = [x/LEVELS for x in context]
    follow = q[6]
    return q + c + [follow*x for x in c] + [a*b for a, b in zip(q[:6], c[:6])]


@lru_cache(maxsize=1)
def _model():
    packed = ASSET.read_bytes()
    ident = hashlib.sha256(packed).hexdigest()
    if ident != ASSET_DIGEST:
        raise ValueError('incompatible saved signal pair')
    model = json.loads(gzip.decompress(packed))
    if (model['task'] != TASK or model['version'] != VERSION or tuple(model['domains']) != DOMAINS
            or model['levels'] != LEVELS):
        raise ValueError('incompatible signal schema')
    model['id'] = ident
    model['vocab'] = {word: idx for idx, word in enumerate(model['vocab'])}
    for role in ROLES:
        model[role]['rows'] = memoryview(base64.b64decode(model[role]['weights'], validate=True)).cast('b')
    return model


def _send(model, role, task, text):
    n = len(model[role]['bias'])
    unknown = (0,) * (n-1) + (LEVELS,)
    observed = features(text)
    inp = [(model['vocab'][key], value) for key, value in observed.items() if key in model['vocab']]
    codes = unknown
    if inp:
        inp = [(idx, value * model['idf'][idx]) for idx, value in inp]
        scale = model[role]['scale'] / math.sqrt(sum(v*v for _, v in inp))
        logits = model[role]['bias'].copy()
        rows = model[role]['rows']
        for idx, value in inp:
            start = n*idx
            for j in range(n):
                logits[j] += scale*value*rows[start+j]
        winner = max(range(n), key=logits.__getitem__)
        # Familiar sentence structure alone is weak evidence for a technical or social domain.
        if winner >= len(DOMAINS) or any(model['anchor_masks'].get(key, 0) & (1 << winner) for key in observed):
            codes = tuple(round(LEVELS*v) for v in _softmax(logits))
    return Frame(task, role, VERSION, TASK+'/'+role, model['id'], codes)


def _last_user(history):
    if not isinstance(history, (tuple, list)):
        return ''
    for turn in reversed(history[-8:]):
        if isinstance(turn, dict):
            role, content = turn.get('role'), turn.get('content')
        elif isinstance(turn, (tuple, list)) and len(turn) == 2:
            role, content = turn
        else:
            continue
        if role == 'user' and isinstance(content, str):
            return content[:4096]
    return ''


def frames(message, history=()):
    """Return a task id and two original, independently computed sender frames."""
    text = message[:4096] if isinstance(message, str) else ''
    prior = _last_user(history)
    key = hashlib.sha256(json.dumps([TASK, VERSION, text, prior], ensure_ascii=True).encode()).hexdigest()
    model = _model()
    return key, _send(model, 'request', key, text), _send(model, 'context', key, prior)


def read_frames(task_id, incoming):
    """Accept a complete matching pair, permitting duplicate retransmission in either order."""
    model = _model()
    accepted = {}
    for frame in incoming:
        if (not isinstance(frame, Frame) or frame.task != task_id or frame.role not in ROLES
                or frame.version != VERSION or frame.bundle_id != model['id'] or frame.sender != TASK+'/'+frame.role):
            return None
        n = 8 if frame.role == 'request' else 7
        if (type(frame.payload) is not tuple or len(frame.payload) != n
                or any(type(code) is not int or not 0 <= code <= LEVELS for code in frame.payload)
                or abs(sum(frame.payload)-LEVELS) > n/2):
            return None
        if frame.role in accepted and accepted[frame.role] != frame.payload:
            return None
        accepted[frame.role] = frame.payload
    if len(accepted) != 2:
        return None
    req, ctx = accepted['request'], accepted['context']
    q = max(range(len(req)), key=req.__getitem__)
    if q == 7:
        return None
    source = ctx if q == 6 else req
    order = sorted(range(len(source)), key=source.__getitem__, reverse=True)
    top, second = order[:2]
    gate = model['gates']
    if (top >= len(DOMAINS) or req[q]/LEVELS < gate['intent']
            or (q == 6 and (req[q]-max(req[:6]+req[7:]))/LEVELS < gate['margin']) or source[top]/LEVELS < gate['domain']
            or (source[top]-source[second])/LEVELS < gate['margin']):
        return None
    posterior = _dense(model['reader'], reader_features(req, ctx))
    selected = max(range(len(posterior)), key=posterior.__getitem__)
    if top != selected or posterior[top] < gate['reader']:
        return None
    return {'domain': DOMAINS[top], 'confidence': round(posterior[top], 4), 'bundle_id': model['id'],
            'signals': {'source': 'context' if q == 6 else 'request', 'request': list(req), 'context': list(ctx)}}


def read_request(message, history=()):
    """Return advice for a recognized specialist, or None when evidence is weak or unavailable."""
    if not isinstance(message, str) or not message.strip():
        return None
    try:
        key, left, right = frames(message, history)
        return read_frames(key, (left, right))
    except (OSError, EOFError, ValueError, KeyError, OverflowError):
        return None
