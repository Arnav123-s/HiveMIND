"""A public-data text classifier with TF–IDF class centroids and open-set rejection."""
from collections import Counter, defaultdict
import hashlib
import math
import re

from keywords import CONTEXT


def features(text):
    words = re.findall(r"[a-z0-9]+", text.casefold())
    counts = Counter('w:' + word for word in words)
    counts.update('p:' + left + ' ' + right for left, right in zip(words, words[1:]))
    for word in words:
        padded = '^' + word + '$'
        for size in (3, 4):
            counts.update('c:' + padded[i:i + size] for i in range(len(padded) - size + 1))
    return counts


def unit(vector):
    norm = math.sqrt(sum(v * v for v in vector.values())) or 1
    return {k: v / norm for k, v in vector.items()}


class Centroid:
    def __init__(self, rows):
        vectors = [(f, label) for text, label in rows if (f := features(text))]
        frequency = Counter(f for fs, _ in vectors for f in fs)
        self.idf = {g: math.log((1 + len(vectors)) / (1 + count)) + 1 for g, count in frequency.items()}
        sums = defaultdict(Counter)
        for fs, label in vectors:
            sums[label].update(self.vector(fs))
        self.centers = {group: unit(sums[group]) for group in sorted(sums)}

    def vector(self, fs):
        return unit({g: (1 + math.log(c)) * self.idf[g] for g, c in fs.items() if g in self.idf})

    def best(self, text):
        vector = self.vector(features(text))
        ranked = sorted(((sum(v * center.get(f, 0) for f, v in vector.items()), domain)
                         for domain, center in self.centers.items()), reverse=True)
        first, second = ranked[:2]
        return first[1], first[0], first[0] - second[0]


def build(rows):
    # Select rejection thresholds using only a deterministic 20% of the supplied
    # public training texts, then refit centroids to all training rows.
    by_domain = defaultdict(set)
    for text, label in rows:
        by_domain[label or 'abstain'].add(text)
    training, calibration = [], []
    for label, texts in sorted(by_domain.items()):
        ordered = sorted(texts, key=lambda t: hashlib.sha256(t.encode()).hexdigest())
        for i, text in enumerate(ordered):
            (calibration if i % 5 == 0 else training).append((text, label))
    model = Centroid(training)
    scored = [(model.best(text), gold) for text, gold in calibration]
    def rank(cut, margin):
        good = Counter()
        total = Counter()
        for (domain, strength, gap), gold in scored:
            routed = domain if strength >= cut and gap >= margin else 'abstain'
            total[gold] += 1
            good[gold] += routed == gold
        return sum(good[g]/n for g, n in total.items())/len(total), -cut, -margin
    cut, margin = max(((c/100, m/100) for c in range(0,36,2) for m in range(0,21,2)),
                      key=lambda p:rank(*p))
    full = Centroid(training + calibration)
    def predict(text):
        domain, strength, gap = full.best(text)
        if domain != 'abstain' and strength >= cut and gap >= margin:
            return domain
        return None
    def read(message, history):
        prediction = predict(message)
        if prediction is None and CONTEXT.search(message) and history:
            # The last two turns are an ordinary public-information comparator;
            # the candidate never uses the held-out task family or its label.
            return predict(' '.join(row['content'] for row in history[-2:]))
        return prediction
    return read, {'examples': len(training)+len(calibration), 'counts': {k:len(v) for k,v in sorted(by_domain.items())},
                  'calibration':len(calibration),'cut':cut,'margin':margin}
