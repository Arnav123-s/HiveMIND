"""Phase 4 dream cycle (meta layer): offline practice for models.

Arnav's design: specialists DREAM — they practice offline on many
examples (harvested + generated), and dreaming does two things:

  1. it improves the model's internals directly (warm-start practice
     on the practice pool, same optimizer the factory trains with);
  2. the dream runs produce activation/trigger traces over a large
     labelled corpus, and a responsibility map built from those
     traces indicts weights more precisely than a map built from the
     small training set — measured here as indictment precision
     (of the weights a map indicts for a class, how many actually
     move that class's margin when ablated on probes).

The win rule still judges: dreamt weights are kept only if held-out
accuracy does not regress. The dreamer is a meta specialist; this
module is its behaviour.
"""
import copy
import random

from . import factory as F


# ------------------------------------------------------------ dream data
# NEW template families (structures absent from phase 3's train AND
# held-out families: while loops, guarded division, dict defaults,
# prefix products...). Dreaming must not leak the held-out set.
_DREAM_TEMPLATES = [
    ("def count_down(n):\n    c = 0\n    i = n\n    while i > 0:\n        c += 1\n        i -= 1\n    return c",
     {"off-by-one": "def count_down(n):\n    c = 0\n    i = n\n    while i > 1:\n        c += 1\n        i -= 1\n    return c",
      "wrong-operator": "def count_down(n):\n    c = 0\n    i = n\n    while i > 0:\n        c -= 1\n        i -= 1\n    return c",
      "missing-return": "def count_down(n):\n    c = 0\n    i = n\n    while i > 0:\n        c += 1\n        i -= 1\n    print(c)"}),
    ("def zip_diff(a, b):\n    out = []\n    for i in range(len(a)):\n        out.append(a[i] - b[i])\n    return out",
     {"swapped-operands": "def zip_diff(a, b):\n    out = []\n    for i in range(len(a)):\n        out.append(b[i] - a[i])\n    return out",
      "off-by-one": "def zip_diff(a, b):\n    out = []\n    for i in range(len(a) - 1):\n        out.append(a[i] - b[i])\n    return out",
      "wrong-operator": "def zip_diff(a, b):\n    out = []\n    for i in range(len(a)):\n        out.append(a[i] + b[i])\n    return out"}),
    ("def running_min(xs):\n    m = xs[0]\n    i = 1\n    while i < len(xs):\n        if xs[i] < m:\n            m = xs[i]\n        i += 1\n    return m",
     {"wrong-operator": "def running_min(xs):\n    m = xs[0]\n    i = 1\n    while i < len(xs):\n        if xs[i] > m:\n            m = xs[i]\n        i += 1\n    return m",
      "off-by-one": "def running_min(xs):\n    m = xs[0]\n    i = 1\n    while i < len(xs) - 1:\n        if xs[i] < m:\n            m = xs[i]\n        i += 1\n    return m",
      "missing-return": "def running_min(xs):\n    m = xs[0]\n    i = 1\n    while i < len(xs):\n        if xs[i] < m:\n            m = xs[i]\n        i += 1"}),
    ("def safe_div(a, b):\n    if b == 0:\n        return 0\n    return a / b",
     {"swapped-operands": "def safe_div(a, b):\n    if b == 0:\n        return 0\n    return b / a",
      "wrong-operator": "def safe_div(a, b):\n    if b == 0:\n        return 0\n    return a * b"}),
    ("def count_if(xs, v):\n    n = 0\n    i = 0\n    while i < len(xs):\n        if xs[i] == v:\n            n += 1\n        i += 1\n    return n",
     {"wrong-operator": "def count_if(xs, v):\n    n = 0\n    i = 0\n    while i < len(xs):\n        if xs[i] != v:\n            n += 1\n        i += 1\n    return n",
      "off-by-one": "def count_if(xs, v):\n    n = 0\n    i = 0\n    while i < len(xs) - 1:\n        if xs[i] == v:\n            n += 1\n        i += 1\n    return n",
      "missing-return": "def count_if(xs, v):\n    n = 0\n    i = 0\n    while i < len(xs):\n        if xs[i] == v:\n            n += 1\n        i += 1\n    print(n)"}),
    ("def prefix_products(xs):\n    out = []\n    p = 1\n    for x in xs:\n        p *= x\n        out.append(p)\n    return out",
     {"wrong-operator": "def prefix_products(xs):\n    out = []\n    p = 1\n    for x in xs:\n        p += x\n        out.append(p)\n    return out",
      "missing-return": "def prefix_products(xs):\n    out = []\n    p = 1\n    for x in xs:\n        p *= x\n        out.append(p)\n    total = out"}),
    ("def collect_evens(xs, out=[]):\n    out = list(out)\n    for x in xs:\n        if x % 2 == 0:\n            out.append(x)\n    return out",
     {"mutable-default": "def collect_evens(xs, out=[]):\n    for x in xs:\n        if x % 2 == 0:\n            out.append(x)\n    return out"}),
    ("def add_tag(tag, bag={}):\n    bag = dict(bag)\n    bag[tag] = True\n    return bag",
     {"mutable-default": "def add_tag(tag, bag={}):\n    bag[tag] = True\n    return bag",
      "missing-return": "def add_tag(tag, bag={}):\n    bag = dict(bag)\n    bag[tag] = True\n    result = bag"}),
    ("def discounted(price, pct):\n    return price - price * pct / 100",
     {"swapped-operands": "def discounted(price, pct):\n    return pct - pct * price / 100",
      "wrong-operator": "def discounted(price, pct):\n    return price + price * pct / 100"}),
    ("def power_mod(a, b, m):\n    return (a ** b) % m",
     {"swapped-operands": "def power_mod(a, b, m):\n    return (b ** a) % m",
      "wrong-operator": "def power_mod(a, b, m):\n    return (a ** b) - m"}),
    ("def mean_of_squares(xs):\n    s = 0\n    for x in xs:\n        s += x * x\n    return s / len(xs)",
     {"wrong-operator": "def mean_of_squares(xs):\n    s = 0\n    for x in xs:\n        s -= x * x\n    return s / len(xs)",
      "swapped-operands": "def mean_of_squares(xs):\n    s = 0\n    for x in xs:\n        s += x * x\n    return len(xs) / s",
      "missing-return": "def mean_of_squares(xs):\n    s = 0\n    for x in xs:\n        s += x * x\n    avg = s / len(xs)"}),
]


def gen_dream_bug_examples(seed=77):
    """The dream corpus: labelled multiclass examples from families
    that appear in neither the training nor the held-out split."""
    rng = random.Random(seed)
    out = []
    for correct, bugs in _DREAM_TEMPLATES:
        out.append({"text": correct, "label": "clean"})
        for cls, buggy in bugs.items():
            out.append({"text": buggy, "label": cls})
    rng.shuffle(out)
    return out


# ------------------------------------------------------------ practice
def _dense(model):
    """Model weights (sparse dicts) -> dense numpy arrays + indexers."""
    import numpy as np
    feats, classes = model.features, model.classes
    fidx = {f: i for i, f in enumerate(feats)}
    cidx = {c: i for i, c in enumerate(classes)}
    w = model.weights
    if model.hidden == 0:
        W = np.zeros((len(feats), len(classes)))
        b = np.zeros(len(classes))
        for f, row in w.get("w", {}).items():
            for c, v in row.items():
                W[fidx[f], cidx[c]] = v
        for c, v in w.get("b", {}).items():
            b[cidx[c]] = v
        return (W, b), fidx, cidx
    H = model.hidden
    W1 = np.zeros((len(feats), H)); b1 = np.zeros(H)
    W2 = np.zeros((H, len(classes))); b2 = np.zeros(len(classes))
    for u in range(H):
        un = f"u{u}"
        b1[u] = w.get("b1", {}).get(un, 0.0)
        for f, v in w.get("w1", {}).get(un, {}).items():
            W1[fidx[f], u] = v
    for c in classes:
        b2[cidx[c]] = w.get("b2", {}).get(c, 0.0)
        for un, v in w.get("w2", {}).get(c, {}).items():
            W2[int(un[1:]), cidx[c]] = v
    return (W1, b1, W2, b2), fidx, cidx


def _sparse(model, params):
    """Dense arrays back to the sparse dict form (>1e-9 kept)."""
    feats, classes = model.features, model.classes
    if model.hidden == 0:
        W, b = params
        out = {"w": {}, "b": {c: float(b[i]) for i, c in enumerate(classes)}}
        for fi, f in enumerate(feats):
            row = {c: float(W[fi, ci]) for ci, c in enumerate(classes)
                   if abs(W[fi, ci]) > 1e-9}
            if row:
                out["w"][f] = row
        return out
    W1, b1, W2, b2 = params
    out = {"w1": {}, "b1": {}, "w2": {},
           "b2": {c: float(b2[i]) for i, c in enumerate(classes)}}
    for u in range(model.hidden):
        un = f"u{u}"
        out["b1"][un] = float(b1[u])
        row = {f: float(W1[fi, u]) for fi, f in enumerate(feats)
               if abs(W1[fi, u]) > 1e-9}
        if row:
            out["w1"][un] = row
    for ci, c in enumerate(classes):
        row = {f"u{u}": float(W2[u, ci]) for u in range(model.hidden)
               if abs(W2[u, ci]) > 1e-9}
        if row:
            out["w2"][c] = row
    return out


def dream_practice(model, practice, epochs=250):
    """Warm-start practice: continue training the model's OWN weights
    on the practice pool (its training data + the dream corpus), with
    the factory's optimizer (full-batch Adam, softmax CE). Returns
    (new_weights, practice_accuracy). The model itself is untouched —
    the dreamer decides by the win rule whether to keep the dream."""
    import numpy as np
    params, fidx, cidx = _dense(model)
    feats, classes = model.features, model.classes

    def matrix(examples):
        X = np.zeros((len(examples), len(feats)))
        y = np.zeros(len(examples), dtype=int)
        for r, ex in enumerate(examples):
            for k, v in F.featurize(ex["text"], model.fmode).items():
                if k in fidx:
                    X[r, fidx[k]] = min(v, 3)
            y[r] = cidx[ex["label"]]
        return X, y

    X, y = matrix(practice)
    N = len(practice)
    params = [p.copy() for p in params]
    ms = [np.zeros_like(p) for p in params]
    vs = [np.zeros_like(p) for p in params]
    lr = 0.05 if model.hidden == 0 else 0.03

    def forward(X):
        if model.hidden == 0:
            return X @ params[0] + params[1]
        return np.tanh(X @ params[0] + params[1]) @ params[2] + params[3]

    for ep in range(epochs):
        if model.hidden == 0:
            W, b = params
            Z = X @ W + b
            Z -= Z.max(axis=1, keepdims=True)
            P = np.exp(Z); P /= P.sum(axis=1, keepdims=True)
            G = P; G[np.arange(N), y] -= 1; G /= N
            grads = [X.T @ G + 1e-4 * W, G.sum(axis=0)]
        else:
            W1, b1, W2, b2 = params
            Hh = np.tanh(X @ W1 + b1)
            Z = Hh @ W2 + b2
            Z -= Z.max(axis=1, keepdims=True)
            P = np.exp(Z); P /= P.sum(axis=1, keepdims=True)
            G = P; G[np.arange(N), y] -= 1; G /= N
            gW2 = Hh.T @ G + 1e-4 * W2; gb2 = G.sum(axis=0)
            dH = (G @ W2.T) * (1 - Hh ** 2)
            grads = [X.T @ dH + 1e-4 * W1, dH.sum(axis=0), gW2, gb2]
        for i, g in enumerate(grads):
            t = ep + 1
            ms[i] = 0.9 * ms[i] + 0.1 * g
            vs[i] = 0.999 * vs[i] + 0.001 * g ** 2
            params[i] -= lr * (ms[i] / (1 - 0.9 ** t)) / \
                (np.sqrt(vs[i] / (1 - 0.999 ** t)) + 1e-8)
    acc = float((forward(X).argmax(axis=1) == y).mean()) if N else 0.0
    return _sparse(model, tuple(params)), acc


# ------------------------------------------------------------ trigger maps
def trigger_map(model, examples, top_k=8):
    """Responsibility map from activation traces: run the examples,
    and for each true class rank features by their total positive
    contribution to that class's score (weight x activation, summed
    over the class's examples). Linear models only — an MLP's
    responsibility is distributed across units, and pretending a
    per-feature map is exact there would be a false map."""
    if model.hidden != 0:
        return None
    contrib = {c: {} for c in model.classes}
    for ex in examples:
        c = ex["label"]
        if c not in contrib:
            continue
        feats = {k: min(v, 3) for k, v in
                 F.featurize(ex["text"], model.fmode).items()
                 if k in model._featset()}
        for f, v in feats.items():
            w = model.weights.get("w", {}).get(f, {}).get(c, 0.0)
            if w > 0:
                contrib[c][f] = contrib[c].get(f, 0.0) + v * w
    return {c: [f for f, _ in sorted(d.items(), key=lambda kv: -kv[1])[:top_k]]
            for c, d in contrib.items()}


def _margin(model, text, cls):
    feats = {k: min(v, 3) for k, v in
             F.featurize(text, model.fmode).items() if k in model._featset()}
    s = model._scores(feats)
    others = [v for c, v in s.items() if c != cls]
    return s.get(cls, 0.0) - (max(others) if others else 0.0)


def map_precision(model, indicted, probes, cls, eps=0.01):
    """Of the features the map indicts for `cls`, what fraction
    actually move the model's cls-margin when ablated (on a copy),
    measured over the probes? A precise map indicts only weights
    that matter; a sloppy map indicts bystanders."""
    if not indicted:
        return None
    base = [_margin(model, p["text"], cls) for p in probes]
    moved = 0
    for f in indicted:
        clone = copy.deepcopy(model)
        if f in clone.weights.get("w", {}):
            clone.weights["w"][f] = {}
        delta = max((abs(_margin(clone, p["text"], cls) - b)
                     for p, b in zip(probes, base)), default=0.0)
        if delta > eps:
            moved += 1
    return round(moved / len(indicted), 4)


# ------------------------------------------------------------ the dreamer
def dream_cycle(task):
    """dreamer specialist behaviour.

    task: {model, practice, heldout, registry?, board?, epochs?,
           train (for the before-map), dream_corpus (for the after-map),
           map_probes, map_class}
    Keeps the dreamt weights only if held-out does not regress
    (win rule). Records the trigger-map precision before (map from
    the small training traces) and after (map from dream traces)."""
    model = task["model"]
    heldout = task["heldout"]
    before = F.accuracy(model, heldout)
    new_weights, prac_acc = dream_practice(
        model, task["practice"], epochs=task.get("epochs", 250))
    clone = copy.deepcopy(model)
    clone.weights = new_weights
    after = F.accuracy(clone, heldout)
    kept = after >= before
    rec = {"heldout_before": round(before, 4),
           "heldout_after": round(after, 4), "kept": kept,
           "practice_acc": round(prac_acc, 4),
           "practice_n": len(task["practice"])}
    cls = task.get("map_class")
    if cls and task.get("dream_corpus") and task.get("map_probes"):
        probes = task["map_probes"]
        map_tr = trigger_map(model, task.get("train", []))
        map_dr = trigger_map(model, task["dream_corpus"])
        if map_tr is not None and map_dr is not None:
            rec["map_precision_before"] = map_precision(
                model, map_tr.get(cls, []), probes, cls)
            rec["map_precision_after"] = map_precision(
                model, map_dr.get(cls, []), probes, cls)
            rec["map_topk"] = 8
    if kept:
        model.weights = new_weights
        reg = task.get("registry")
        if reg is not None:
            reg.update_weights(model.name, model.weights)
        board = task.get("board")
        if board is not None:
            board.record_score("model", model.name, round(after, 4),
                               "dreamt weights kept by the win rule")
            board.event("dreamer", "dream", model.name)
    verdict = "kept" if kept else "reverted (no regression allowed)"
    return {"ok": True, "output": rec,
            "evidence": f"dream: held-out {before:.3f} -> {after:.3f} "
                        f"({verdict})"}
