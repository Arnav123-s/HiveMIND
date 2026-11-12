"""Tier-0 ternary substrate (Phase C): mapper + head-to-head harness.

FACTORY-ARCHITECTURE.md section 4, build item 3b. A Tier-0 specialist
has two first-class substrates; this module is the ternary one:

  * quantize: fp TinyNet weights -> ternary codes {-1, 0, +1} with a
    per-row scale (BitNet b1.58 style: threshold = multiplier x
    mean|row|). The multiplier is chosen on the subject's TRAINING
    data only (calibration), never on held-out — probe hygiene.
    Biases stay full-precision (few, and BitNet keeps them so).
  * materialize: codes + scales -> a dequantized TinyNet that runs
    through the standard inference path, so every measurement is the
    real serving measurement, not a simulation of one.
  * flip_map: the ternary-aware surgery instrument. At 3 states per
    weight an indictment map is near-exact: for every weight, try
    BOTH other states on a probe set and record the accuracy delta.
    Flips that improve the probes indict the weight; the map is the
    map-backed indictment contracts.Indictment requires before any
    weight edit is legal (IDEA.md section 6).
  * head_to_head: per niche, fp vs ternary on the same splits —
    held-out score, footprint, latency — decided by the win-gate:
    ternary ships only where it measures >= fp on held-out (the
    architecture's rule), recorded either way. Cross-substrate
    agreement is reported as the factory's first cross-family trust
    signal: where fp and ternary disagree, a served verdict would be
    flagged abstain/recheck rather than trusted (design, section 10
    of the architecture doc).

Ternary artifacts are saved as <subject>-ternary.json model records
(adopted only when the gate passes) next to the fp records; the fp
record is never modified by this module.
"""
from __future__ import annotations

import copy
import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

LAB_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(LAB_ROOT / "coding"))
sys.path.insert(0, str(LAB_ROOT))

from swarm import factory as F  # noqa: E402

MODELS_DIR = LAB_ROOT / "coding" / "swarm" / "models"
MULTIPLIERS = (0.5, 0.7, 1.0, 1.3)   # threshold = m * mean|row|, calibrated
BITS_PER_WEIGHT = 1.58               # log2(3), the honest ternary cost


# ------------------------------------------------------------ leaf walking
def _leaf_paths(tree, prefix=()):
    """Yield (path_tuple, value) for every float leaf of a weights
    dict — the same addressing the swarm surgeon uses."""
    if isinstance(tree, dict):
        for k in sorted(tree.keys(), key=str):
            yield from _leaf_paths(tree[k], prefix + (k,))
    else:
        yield prefix, tree


def _get(tree, path):
    for p in path:
        tree = tree[p]
    return tree


def _set(tree, path, value):
    for p in path[:-1]:
        tree = tree[p]
    tree[path[-1]] = value


def _row_groups(weights: Dict[str, Any]) -> List[Tuple[str, str]]:
    """(matrix, row) pairs whose leaves get one shared scale. Bias
    groups are excluded — biases stay full-precision."""
    groups = []
    for matrix in ("w", "w1", "w2"):
        sub = weights.get(matrix)
        if isinstance(sub, dict):
            for row in sub.keys():
                groups.append((matrix, row))
    return groups


# ------------------------------------------------------------ quantization
def quantize(model: F.TinyNet, calib: List[Dict[str, Any]],
             multipliers=MULTIPLIERS) -> Dict[str, Any]:
    """Ternary-quantize a TinyNet. The threshold multiplier is picked
    per model (not per row) by calibration accuracy on `calib`
    (training data — never held-out). Returns a pack:
    {codes, scales, biases, multiplier, calib_acc_fp, calib_acc_q}."""
    feats = [{k: min(v, 3) for k, v in F.featurize(ex["text"], model.fmode).items()
              if k in model._featset()} for ex in calib]
    labels = [ex["label"] for ex in calib]

    def acc_of(m: F.TinyNet) -> float:
        right = 0
        for f, lab in zip(feats, labels):
            s = m._scores(f)
            if s and max(s, key=s.get) == lab:
                right += 1
        return right / len(labels) if labels else 0.0

    fp_calib = acc_of(model)
    best = None
    for mult in multipliers:
        pack = _quantize_with(model.weights, mult)
        q = materialize(model, pack)
        a = acc_of(q)
        if best is None or a > best[0]:
            best = (a, mult, pack)
    q_acc, mult, pack = best
    pack["multiplier"] = mult
    pack["calib_acc_fp"] = round(fp_calib, 4)
    pack["calib_acc_q"] = round(q_acc, 4)
    return pack


def _quantize_with(weights: Dict[str, Any], mult: float) -> Dict[str, Any]:
    codes: Dict[str, Any] = {}
    scales: Dict[str, Dict[str, float]] = {}
    for matrix, row in _row_groups(weights):
        vals = [v for _, v in _leaf_paths(weights[matrix][row])]
        mean_abs = (sum(abs(v) for v in vals) / len(vals)) if vals else 0.0
        scale = mult * mean_abs
        scales.setdefault(matrix, {})[row] = scale
        row_codes: Dict[str, int] = {}
        for path, v in _leaf_paths(weights[matrix][row]):
            if scale <= 0:
                row_codes[path[-1]] = 0
            else:
                t = int(round(v / scale))
                row_codes[path[-1]] = max(-1, min(1, t))
        codes.setdefault(matrix, {})[row] = row_codes
    biases = {b: copy.deepcopy(weights[b]) for b in ("b", "b1", "b2")
              if b in weights}
    return {"codes": codes, "scales": scales, "biases": biases}


def materialize(template: F.TinyNet, pack: Dict[str, Any]) -> F.TinyNet:
    """Build the dequantized TinyNet a ternary artifact serves as."""
    m = template.clone("ternary")
    m.name = template.name
    w: Dict[str, Any] = {}
    for matrix, rows in pack["codes"].items():
        w[matrix] = {}
        for row, row_codes in rows.items():
            s = pack["scales"][matrix][row]
            w[matrix][row] = {leaf: code * s for leaf, code in row_codes.items()}
    for b, vals in pack["biases"].items():
        w[b] = copy.deepcopy(vals)
    m.weights = w
    return m


def packed_footprint(pack: Dict[str, Any], template: F.TinyNet) -> Dict[str, Any]:
    """Honest footprint: ternary weights at log2(3) bits, scales and
    biases at fp32, plus the real JSON artifact size for comparison."""
    n_ternary = sum(1 for rows in pack["codes"].values()
                    for row in rows.values() for _ in row)
    n_scales = sum(len(rows) for rows in pack["scales"].values())
    n_bias = sum(1 for vals in pack["biases"].values()
                 for _ in _leaf_paths(vals))
    packed = math.ceil(n_ternary * BITS_PER_WEIGHT / 8) + 4 * (n_scales + n_bias)
    return {"ternary_weights": n_ternary, "scales": n_scales,
            "bias_values": n_bias, "packed_bytes": packed,
            "fp_params": template.param_count()}


# ------------------------------------------------------------ flip mapping
def flip_map(template: F.TinyNet, pack: Dict[str, Any],
             probes: List[Dict[str, Any]], limit: Optional[int] = None):
    """Near-exact indictment map for a ternary model: every weight,
    both alternative states, measured on probes (training-side data —
    the map indicts; held-out judges). Returns (base_acc, entries)
    where each entry is {path, from, best_to, delta} sorted by the
    best achievable delta, descending."""
    q = materialize(template, pack)
    feats = [{k: min(v, 3) for k, v in F.featurize(ex["text"], q.fmode).items()
              if k in q._featset()} for ex in probes]
    labels = [ex["label"] for ex in probes]

    def acc() -> float:
        right = 0
        for f, lab in zip(feats, labels):
            s = q._scores(f)
            if s and max(s, key=s.get) == lab:
                right += 1
        return right / len(labels) if labels else 0.0

    base = acc()
    entries = []
    paths = []
    for matrix, rows in pack["codes"].items():
        for row, row_codes in rows.items():
            for leaf in row_codes:
                paths.append((matrix, row, leaf))
    if limit:
        paths = paths[:limit]
    for matrix, row, leaf in paths:
        scale = pack["scales"][matrix][row]
        cur_code = pack["codes"][matrix][row][leaf]
        best_to, best_delta = None, 0.0
        for alt in (-1, 0, 1):
            if alt == cur_code:
                continue
            old = q.weights[matrix][row][leaf]
            q.weights[matrix][row][leaf] = alt * scale
            d = acc() - base
            q.weights[matrix][row][leaf] = old
            if d > best_delta:
                best_to, best_delta = alt, d
        entries.append({"path": [matrix, row, leaf], "from": cur_code,
                        "best_to": best_to,
                        "delta": round(best_delta, 4)})
    entries.sort(key=lambda e: -e["delta"])
    return round(base, 4), entries


def apply_flips(template: F.TinyNet, pack: Dict[str, Any],
                flips: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Apply indicted flips to a copy of the pack (the surgery)."""
    new = copy.deepcopy(pack)
    for e in flips:
        if e.get("best_to") is None:
            continue
        matrix, row, leaf = e["path"]
        new["codes"][matrix][row][leaf] = e["best_to"]
    return new


# ------------------------------------------------------------ QAT training
def train_qat(train: List[Dict[str, Any]], classes: List[str], hidden: int,
              fmode: str = "text", epochs: int = 300, seed: int = 42,
              mult: float = 1.0):
    """Quantization-aware training (straight-through estimator): the
    forward pass always uses ternary weights; gradients flow to the
    latent full-precision weights (STE identity), Adam updates the
    latent weights — the standard BitNet-style born-ternary path,
    mirroring the swarm trainer's optimizer and featurization so the
    head-to-head compares substrates, not optimizers. Scales are
    per-row (per class / per unit / per feature, matching the pack
    layout), recomputed from the latent weights each step.
    Returns (pack, feature_vocab)."""
    import numpy as np

    rng = np.random.default_rng(seed)
    train_feats = [F.featurize(ex["text"], fmode) for ex in train]
    feats = F._vocab(train_feats)
    fidx = {f: i for i, f in enumerate(feats)}
    cidx = {c: i for i, c in enumerate(classes)}
    Fn, C = len(feats), len(classes)
    X = np.zeros((len(train), Fn)); y = np.zeros(len(train), dtype=int)
    for r, ex in enumerate(train):
        for k, v in F.featurize(ex["text"], fmode).items():
            if k in fidx:
                X[r, fidx[k]] = min(v, 3)
        y[r] = cidx[ex["label"]]
    N = len(train)

    def qrow(W):    # scale per row (axis 0)
        s = np.maximum(np.abs(W).mean(axis=1, keepdims=True) * mult, 1e-12)
        return np.clip(np.round(W / s), -1, 1) * s, s

    def qcol(W):    # scale per column (axis 1)
        s = np.maximum(np.abs(W).mean(axis=0, keepdims=True) * mult, 1e-12)
        return np.clip(np.round(W / s), -1, 1) * s, s

    def adam(params, grads, ms, vs, t, lr):
        for i, g in enumerate(grads):
            ms[i] = 0.9 * ms[i] + 0.1 * g
            vs[i] = 0.999 * vs[i] + 0.001 * g ** 2
            params[i] -= lr * (ms[i] / (1 - 0.9 ** t)) / \
                (np.sqrt(vs[i] / (1 - 0.999 ** t)) + 1e-8)

    def pack_of(Wl, bl, W1l=None, b1l=None, W2l=None):
        codes: Dict[str, Any] = {}
        scales: Dict[str, Dict[str, float]] = {}
        biases: Dict[str, Any] = {}
        if W1l is None:
            Q, s = qrow(Wl)
            codes["w"] = {f: {c: int(round(Q[fidx[f], cidx[c]] /
                                           s[fidx[f], 0]))
                              for c in classes} for f in feats}
            scales["w"] = {f: float(s[fidx[f], 0]) for f in feats}
            biases["b"] = {c: float(bl[cidx[c]]) for c in classes}
        else:
            Q1, s1 = qcol(W1l)
            codes["w1"] = {f"u{u}": {f: int(round(Q1[fidx[f], u] /
                                                  s1[0, u]))
                                     for f in feats} for u in range(W1l.shape[1])}
            scales["w1"] = {f"u{u}": float(s1[0, u]) for u in range(W1l.shape[1])}
            biases["b1"] = {f"u{u}": float(b1l[u]) for u in range(W1l.shape[1])}
            Q2, s2 = qcol(W2l)   # pack rows are classes = W2 columns
            codes["w2"] = {c: {f"u{u}": int(round(Q2[u, cidx[c]] /
                                                  s2[0, cidx[c]]))
                               for u in range(W2l.shape[0])} for c in classes}
            scales["w2"] = {c: float(s2[0, cidx[c]]) for c in classes}
            biases["b2"] = {c: float(bl[cidx[c]]) for c in classes}
        return {"codes": codes, "scales": scales, "biases": biases,
                "multiplier": mult}

    if hidden == 0:
        W = np.zeros((Fn, C)); b = np.zeros(C)
        params = [W, b]
        ms = [np.zeros_like(p) for p in params]
        vs = [np.zeros_like(p) for p in params]
        for ep in range(epochs):
            Q, _ = qrow(W)
            Z = X @ Q + b
            Z -= Z.max(axis=1, keepdims=True)
            P = np.exp(Z); P /= P.sum(axis=1, keepdims=True)
            G = P; G[np.arange(N), y] -= 1; G /= N
            gQ = X.T @ G + 1e-4 * Q; gb = G.sum(axis=0)
            adam(params, [gQ, gb], ms, vs, ep + 1, 0.05)
            W, b = params
        return pack_of(W, b), feats

    H = hidden
    W1 = rng.normal(0, 0.3, (Fn, H)); b1 = np.zeros(H)
    W2 = rng.normal(0, 0.3, (H, C)); b2 = np.zeros(C)
    params = [W1, b1, W2, b2]
    ms = [np.zeros_like(p) for p in params]
    vs = [np.zeros_like(p) for p in params]
    for ep in range(epochs):
        Q1, _ = qcol(W1); Q2, _ = qcol(W2)
        Hh = np.tanh(X @ Q1 + b1)
        Z = Hh @ Q2 + b2
        Z -= Z.max(axis=1, keepdims=True)
        P = np.exp(Z); P /= P.sum(axis=1, keepdims=True)
        G = P; G[np.arange(N), y] -= 1; G /= N
        gQ2 = Hh.T @ G + 1e-4 * Q2; gb2 = G.sum(axis=0)
        dH = (G @ Q2.T) * (1 - Hh ** 2)
        gQ1 = X.T @ dH + 1e-4 * Q1; gb1 = dH.sum(axis=0)
        adam(params, [gQ1, gb1, gQ2, gb2], ms, vs, ep + 1, 0.03)
        W1, b1, W2, b2 = params
    return pack_of(None, b2, W1l=W1, b1l=b1, W2l=W2), feats


# ------------------------------------------------------------ head-to-head
def _latency_ms(model: F.TinyNet, examples: List[Dict[str, Any]],
                reps: int = 3) -> float:
    best = None
    for _ in range(reps):
        t0 = time.perf_counter()
        for ex in examples:
            model.run({"text": ex["text"]})
        dt = (time.perf_counter() - t0) / max(len(examples), 1) * 1000
        best = dt if best is None else min(best, dt)
    return round(best, 3)


def _calib_acc(model: F.TinyNet, train: List[Dict[str, Any]]) -> float:
    right = 0
    for ex in train:
        feats = {k: min(v, 3) for k, v in F.featurize(ex["text"], model.fmode).items()
                 if k in model._featset()}
        s = model._scores(feats)
        if s and max(s, key=s.get) == ex["label"]:
            right += 1
    return round(right / len(train), 4) if train else 0.0


def head_to_head(subject_id: str, train: List[Dict[str, Any]],
                 held: List[Dict[str, Any]],
                 save: bool = True) -> Dict[str, Any]:
    """fp vs ternary for one adopted subject, same splits. Ternary
    has two birth paths and both are tried: (a) post-training
    quantization of the fp incumbent, calibrated on train; (b)
    born-ternary QAT (STE) training on the same train set, hidden
    ladder {incumbent hidden, 4, 8}. Candidates are ranked by
    TRAINING (calibration) accuracy only — held-out judges the
    winner once. The gate (architecture section 4): ternary ships
    only where it measures >= fp on held-out. Cross-substrate
    agreement is reported as a trust signal: disagreements are the
    cases a served system should abstain/recheck on."""
    from .executors import load_incumbent, measure
    fp = load_incumbent(subject_id)
    fp_held = measure(fp, held)
    fp_file = MODELS_DIR / f"{fp.name}.json"
    fp_bytes = fp_file.stat().st_size if fp_file.exists() else None

    candidates = []   # (calib_acc, label, model, pack, template)
    ptq_pack = quantize(fp, train)
    ptq = materialize(fp, ptq_pack)
    candidates.append((_calib_acc(ptq, train), "ptq", ptq, ptq_pack, fp))
    epochs = 800 if fp.fmode == "words" else 300
    for hidden in sorted({fp.hidden, 4, 8}):
        pack_q, feats = train_qat(train, fp.classes, hidden,
                                  fmode=fp.fmode, epochs=epochs)
        tmpl = F.TinyNet(fp.name, fp.niche, fp.job, fp.classes, feats,
                         hidden, fp.fmode)
        qm = materialize(tmpl, pack_q)
        candidates.append((_calib_acc(qm, train), f"qat-h{hidden}",
                            qm, pack_q, tmpl))
    candidates.sort(key=lambda t: -t[0])
    calib_best, path_label, q, pack, _tmpl = candidates[0]
    q_held = measure(q, held)
    foot = packed_footprint(pack, q)
    agree = sum(1 for ex in held
                if fp.run({"text": ex["text"]})["output"]
                == q.run({"text": ex["text"]})["output"])
    result = {
        "subject_id": subject_id,
        "fp": {"heldout_acc": fp_held["acc"], "heldout_n": fp_held["n"],
               "params": fp.param_count(), "artifact_bytes": fp_bytes,
               "latency_ms_per_case": _latency_ms(fp, held[:24])},
        "ternary": {"heldout_acc": q_held["acc"],
                    "winning_path": path_label,
                    "calib_acc": calib_best,
                    "candidates": [{"path": lbl, "calib_acc": ca}
                                   for ca, lbl, *_ in candidates],
                    "latency_ms_per_case": _latency_ms(q, held[:24]),
                    **foot},
        "agreement_on_heldout": round(agree / len(held), 4) if held else None,
        "disagreements": (len(held) - agree) if held else None,
        "gate": "ternary ships only if held-out >= fp held-out",
        "ships": q_held["acc"] >= fp_held["acc"],
    }
    if save and result["ships"]:
        q.name = f"{subject_id}-ternary"
        extra = {"path": f"ternary/{path_label} (factory Phase C head-to-head)",
                 "heldout_acc": q_held["acc"], "train_n": len(train),
                 "heldout_n": len(held),
                 "incumbents": [{"name": fp.name, "acc": fp_held["acc"]}],
                 "bar": fp_held["acc"], "adopted": True,
                 "substrate": "ternary", "supersedes": None,
                 "coexists_with": fp.name,
                 "ternary_pack": pack,
                 "packed_bytes": foot["packed_bytes"]}
        rec = F.save_model(q, extra, directory=MODELS_DIR)
        result["artifact"] = f"coding/swarm/models/{subject_id}-ternary.json"
        result["artifact_footprint_bytes"] = rec["footprint_bytes"]
    return result
