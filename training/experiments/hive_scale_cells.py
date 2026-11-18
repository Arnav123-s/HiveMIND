"""Small reversible, ternary-weight cells learned from checked before/after byte records."""
import hashlib
from dataclasses import dataclass
from functools import lru_cache
from itertools import product

import numpy as np


BYTES = np.arange(256, dtype=np.uint8)
BITS = 2 ** np.arange(4)
SIGNS = (((np.arange(16)[:, None] & BITS) > 0).astype(np.int8) * 2 - 1)


@lru_cache(maxsize=1)
def neurons():
    """One canonical weight/threshold representation per realizable four-input Boolean neuron."""
    weights, thresholds, outputs, seen = [], [], [], set()
    for w in product((-1, 0, 1), repeat=4):
        for threshold in (-3, -2, -1, 0, 1, 2, 3):
            truth = SIGNS @ np.array(w) >= threshold
            key = np.packbits(truth).tobytes()
            if key not in seen:
                weights.append(w)
                thresholds.append(threshold)
                outputs.append(truth)
                seen.add(key)
    return np.array(weights, dtype=np.int8), np.array(thresholds, dtype=np.int8), np.stack(outputs)


@dataclass
class Cell:
    weights: np.ndarray
    thresholds: np.ndarray

    def archive(self):
        """Thirty-two ternary synapses in two sign planes and eight signed thresholds."""
        w = self.weights
        return np.packbits(w > 0).tobytes() + np.packbits(w < 0).tobytes() + self.thresholds.tobytes()

    @classmethod
    def restore(cls, data):
        if len(data) != 16:
            raise ValueError("invalid ternary cell size")
        plus, minus = np.unpackbits(np.frombuffer(data[:8], np.uint8)).reshape(2, 32)
        if np.any(plus & minus):
            raise ValueError("overlapping weight signs")
        return cls((plus.astype(np.int8) - minus).reshape(8, 4), np.frombuffer(data[8:], np.int8))

    def tables(self):
        outputs = SIGNS @ self.weights.T >= self.thresholds
        return np.stack([outputs[:, :4] @ BITS, outputs[:, 4:] @ BITS]).astype(np.uint8)

    def neural(self, inputs):
        left, right = inputs >> 4, inputs & 15
        def fire(nibble, part):
            return ((SIGNS[nibble] @ self.weights[part].T >= self.thresholds[part]) @ BITS).astype(np.uint8)
        right = right ^ fire(left, slice(4))
        left = left ^ fire(right, slice(4, 8))
        return (left << 4) | right


def forward(t, x):
    left, right = x >> 4, x & 15
    right = right ^ t[0, left]
    return ((left ^ t[1, right]) << 4) | right


def inverse(t, y):
    right = y & 15
    left = (y >> 4) ^ t[1, right]
    return (left << 4) | (right ^ t[0, left])


def draw_cell(rng):
    w, t, truth = neurons()
    useful = np.flatnonzero((truth.sum(1) >= 3) & (truth.sum(1) <= 13) & (np.count_nonzero(w, axis=1) >= 2))
    rows = rng.choice(useful, 8)
    return Cell(w[rows], t[rows])


def observations(x, y):
    left, right = x >> 4, y & 15
    return (left, right), ((x & 15) ^ right, left ^ (y >> 4))


def fit(xs, ys):
    w, thresholds, truth = neurons()
    inputs, responses = observations(np.asarray(xs, np.uint8), np.asarray(ys, np.uint8))
    ids, disagreement = [], []
    for key, response in zip(inputs, responses):
        candidate = truth[:, key]
        masks = []
        for bit in BITS:
            keep = np.flatnonzero(np.all(candidate == ((response & bit) > 0), axis=1))
            if not len(keep):
                raise ValueError("observations contradict the threshold-cell family")
            ids.append(keep[0])
            masks.append(np.any(truth[keep] != truth[keep[0]], axis=0))
        disagreement.append(np.sum(masks, axis=0))
    return Cell(w[ids], thresholds[ids]), np.stack(disagreement)


def learn(source, order, budget=32, active=True):
    """Choose queries using disagreement among surviving hypotheses, then consult the source."""
    x = list(order[:6])
    table = source.tables()
    while True:
        xx = np.asarray(x, np.uint8)
        yy = forward(table, xx)
        cell, gaps = fit(xx, yy)
        if len(x) >= budget or not gaps.any():
            return cell, np.stack((xx, yy), axis=1).tobytes()
        if active:
            left = order >> 4
            predicted_right = (order & 15) ^ cell.tables()[0, left]
            gain = gaps[0, left] + gaps[1, predicted_right]
            gain[np.isin(order, xx)] = -1
            x.append(order[np.argmax(gain)])
        else:
            x.append(order[len(x)])


def regrow(receipt, digest):
    if not receipt or len(receipt) % 2:
        raise ValueError("incomplete teaching receipt")
    pairs = np.frombuffer(receipt, np.uint8).reshape(-1, 2)
    cell, _ = fit(pairs[:, 0], pairs[:, 1])
    raw = cell.archive()
    if hashlib.sha256(raw).digest() != digest:
        raise ValueError("teaching receipt cannot reconstruct the archived cell")
    return raw
