"""Require the paired domain reader and an independent public-data centroid to agree."""
from collections import Counter
from functools import lru_cache
import base64
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import struct

from .signals import _last_user


ASSET = Path(__file__).with_name('assets') / 'domain-centroid-v1.json.gz'
ASSET_DIGEST = '1bdef5f3dffdb8e5edfe756d02cb762782a9c4fa3497e0eabae88659d57e83a3'
CONTEXT = re.compile(r'\b(this|that|those|these|there|they|it|again|previous|same|suggested|first|second|last|mine|one|next)\b', re.I)


@lru_cache(maxsize=1)
def _model():
    content = ASSET.read_bytes()
    if hashlib.sha256(content).hexdigest() != ASSET_DIGEST:
        raise ValueError('incompatible domain centroid')
    stored = json.loads(gzip.decompress(content))
    data = base64.b64decode(stored['weights'], validate=True)
    width = 1 + len(stored['domains'])
    rows = struct.iter_unpack('>' + 'd'*width, data)
    vectors = dict(zip(stored['features'], rows, strict=True))
    return stored['domains'], stored['cut'], stored['margin'], vectors


def _predict(text):
    labels, cutoff, margin, vectors = _model()
    words = re.findall(r'[a-z0-9]+', text.casefold())
    counts = Counter('w:' + w for w in words)
    counts.update('p:' + a + ' ' + b for a,b in zip(words,words[1:]))
    for word in words:
        padded = '^' + word + '$'
        for size in (3, 4):
            counts.update('c:' + padded[i:i+size] for i in range(len(padded)-size+1))
    weights = [(vectors[f], (1+math.log(n))*vectors[f][0]) for f,n in counts.items() if f in vectors]
    norm = math.sqrt(sum(v*v for _,v in weights)) or 1.
    scores = [0.] * len(labels)
    for row, weight in weights:
        value = weight / norm
        for i, component in enumerate(row[1:]):
            scores[i] += value * component
    ranked = sorted(zip(scores,labels),reverse=True)
    (first, label), (second, _) = ranked[:2]
    return label if label != 'abstain' and first >= cutoff and first - second >= margin else None


def read_consensus(message, history, decision):
    """Return the original decision only when the independent text classifier names the same domain."""
    if not isinstance(decision, dict) or not isinstance(message, str) or not message.strip():
        return None
    try:
        text = message[:4096]
        agreed = _predict(text)
        if agreed is None and CONTEXT.search(text):
            prior = _last_user(history)
            if prior:
                agreed = _predict(prior)
        return decision if agreed is not None and decision.get('domain') == agreed else None
    except (OSError, ValueError, KeyError, EOFError):
        return None
