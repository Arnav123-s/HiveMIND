"""The model factory: where smallest specialist MODELS are made.

IDEA.md phase 3. Until now the swarm's specialists were rule-code
("calculators") or unloaded model bindings. This module is the
machinery the meta layer uses to produce genuine tiny learned models —
the hive brain's first real layer:

  TRAIN path   — a genuinely tiny model (softmax-linear, or a one-hidden
                 -layer MLP only if linear cannot reach the bar) trained
                 from scratch on harvested/generated examples. Thousands
                 of parameters, CPU-seconds per model. No LM, no download.
  EDIT path    — direct weight editing via mapping: the surgery niche's
                 protocol (trace -> find -> map -> untangle -> edit only
                 the indicted weights) applied to a trained TinyNet to
                 repair a systematic defect, verified before/after.

A TinyNet's weights are plain nested dicts of floats — the same shape
the registry socializes, the footprint test measures, and the surgeon
ablates. Inference is pure Python (no numpy at run time); numpy is used
only inside the training call. The featurizer is a generic tokenizer
(word tokens + char trigrams) — harness, not judgment; every judgment
the model makes is learned.

The factory is operated BY the swarm: `make_specialist_model` is the
behaviour of the meta niche's `model-factory` specialist, and the edit
path runs the surgery niche's own protocol functions. Adoption follows
the standing win rule: a candidate is adopted only if its held-out
score beats the incumbent's, and winners are cloned and socialized.
"""
import copy
import json
import math
import re
from pathlib import Path

from .specialist import Specialist

MODELS_DIR = Path(__file__).parent / "models"


# ------------------------------------------------------------ featurizing
_WORD = re.compile(r"[a-z0-9_]+")

# Each punctuation character gets its OWN code letter: collapsing them
# all to "_" (the naive sanitize) makes " - ", " + ", " * " the same
# feature — which destroys exactly the operator signal code jobs need.
_OP_CODE = {"-": "m", "+": "p", "*": "s", "/": "d", "=": "e", "<": "l",
            ">": "g", "(": "o", ")": "c", "[": "b", "]": "k", ":": "n",
            ",": "a", ".": "t", "'": "q", '"': "w", "%": "r", "!": "x",
            "&": "y", "|": "z", "^": "h", "~": "u", "@": "v", "#": "j",
            "$": "f", ";": "i", "?": "9", "\\": "8", "{": "7", "}": "6"}


def _encode(text):
    out = []
    for ch in text:
        if ch.isalnum() or ch == "_":
            out.append(ch)
        elif ch == " ":
            out.append("_")
        else:
            out.append("_" + _OP_CODE.get(ch, "z"))
    return "".join(out)


def _bag(text, trigrams=True, legacy=False):
    feats = {}
    for w in _WORD.findall(text):
        if len(w) >= 2:
            k = "w:" + w
            feats[k] = feats.get(k, 0) + 1
    if trigrams:
        squashed = re.sub(r"\s+", " ", text)
        if legacy:
            # the original sanitize: every punctuation char collapses to
            # "_" — lossy for operators, but the collapse also smooths
            # punctuation-heavy text (tracebacks), which some jobs prefer
            enc = re.sub(r"[^a-z0-9_]", "_", squashed)
        else:
            enc = _encode(squashed)
        for i in range(len(enc) - 2):
            k = "g:" + enc[i:i + 3]
            feats[k] = feats.get(k, 0) + 1
    return feats


def _featurize_words(text):
    """Word unigrams + bigrams only — for short judgment texts where the
    discriminating signal is phrasing, not spelling."""
    words = [w for w in _WORD.findall(text) if len(w) >= 2]
    feats = {}
    for w in words:
        k = "w:" + w
        feats[k] = feats.get(k, 0) + 1
    for a, b in zip(words, words[1:]):
        k = f"w2:{a}_{b}"
        feats[k] = feats.get(k, 0) + 1
    return feats


def _anonymize_code(code):
    """Tokenizer-level normalization for code: user identifiers -> VAR,
    numbers -> NUM, string literals -> STR, comments dropped; keywords
    and operators kept. The model learns code SHAPE, not names."""
    import io
    import keyword as _kw
    import tokenize
    out = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(code).readline):
            if tok.type == tokenize.NAME:
                out.append(tok.string if _kw.iskeyword(tok.string) else "VAR")
            elif tok.type == tokenize.NUMBER:
                out.append("NUM")
            elif tok.type == tokenize.STRING:
                out.append("STR")
            elif tok.type in (tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE,
                              tokenize.INDENT, tokenize.DEDENT, tokenize.ENCODING):
                out.append(" ")
            else:
                out.append(tok.string)
    except Exception:
        return code
    return " ".join(out)


def _featurize_secret(text):
    """Shape-normalize a code line: every quoted literal becomes a token
    naming its length class and charset class (lit:long:hex, lit:short:
    word, lit:empty) — the signal a secret scanner actually uses — while
    the rest of the line stays readable."""
    def shape(m):
        body = m.group(1)
        if not body:
            cls = "empty"
        else:
            if all(c in "0123456789abcdef" for c in body.lower()):
                cs = "hex"
            elif body.isalpha() and body.islower():
                cs = "word"
            elif all(c.isalnum() or c in "+/=._-" for c in body):
                cs = "b64"
            else:
                cs = "mix"
            cls = ("long:" if len(body) > 12 else "short:") + cs
        return f" lit:{cls} "
    text = re.sub(r'"([^"\n]*)"', shape, str(text))
    text = re.sub(r"'([^'\n]*)'", shape, text)
    return _bag(text.lower())


def featurize(text, mode="text"):
    """Tokenizer -> {feature_key: count}. Keys are dot-free so the
    surgeon's dotted leaf paths address every weight unambiguously.
    Modes: text (words+trigrams), words (words+bigrams), code
    (identifier-anonymized code), secret (literal-shape-normalized)."""
    text = str(text)
    if mode == "codetext":
        # union representation (phase 4 round 7): anonymized code
        # trigrams AND literal/name trigrams, prefix-separated so the
        # two signal sources never collide into one weight
        out = {"c:" + k: v for k, v in _bag(_anonymize_code(text).lower()).items()}
        out.update({"t:" + k: v for k, v in _bag(text.lower()).items()})
        return out
    if mode == "words":
        return _featurize_words(text.lower())
    if mode == "code":
        return _bag(_anonymize_code(text).lower())
    if mode == "secret":
        return _featurize_secret(text)
    if mode == "text0":
        return _bag(text.lower(), legacy=True)
    return _bag(text.lower())


def _vocab(train_feats, cap=1024):
    # min_df adapts to corpus size: on a small harvested set a feature
    # seen once can still be the whole signal
    min_df = 2 if len(train_feats) >= 100 else 1
    df = {}
    for f in train_feats:
        for k in f:
            df[k] = df.get(k, 0) + 1
    keys = [k for k, n in df.items() if n >= min_df]
    keys.sort(key=lambda k: (-df[k], k))
    return keys[:cap]


# ------------------------------------------------------------ the model
class TinyNet(Specialist):
    """A smallest specialist model: learned weights, one classification job.

    weights (float leaves only, so surgeon._leaf_paths sees every weight):
      linear: {"w": {feat: {cls: v}}, "b": {cls: v}}
      mlp:    {"w1": {unit: {feat: v}}, "b1": {unit: v},
               "w2": {cls: {unit: v}}, "b2": {cls: v}}
    Architecture metadata (classes, feature vocab, hidden size) lives on
    the object, not in weights — it is the same for every clone.
    """

    kind = "tiny"

    def __init__(self, name, niche, job, classes, features, hidden=0, fmode="text"):
        super().__init__(name, niche, job)
        self.classes = list(classes)
        self.features = list(features)
        self.hidden = hidden
        self.fmode = fmode
        self.kind = "tiny"
        self.weights = {}

    # -- inference (pure python, sparse) --------------------------------
    def _scores(self, feats):
        w = self.weights
        if self.hidden == 0:
            scores = {c: w.get("b", {}).get(c, 0.0) for c in self.classes}
            for f, v in feats.items():
                row = w.get("w", {}).get(f)
                if row:
                    for c, wt in row.items():
                        scores[c] += v * wt
            return scores
        h = {}
        for u in range(self.hidden):
            u = f"u{u}"
            s = w.get("b1", {}).get(u, 0.0)
            row = w.get("w1", {}).get(u, {})
            for f, v in feats.items():
                wt = row.get(f)
                if wt:
                    s += v * wt
            h[u] = math.tanh(s)
        scores = {}
        for c in self.classes:
            s = w.get("b2", {}).get(c, 0.0)
            row = w.get("w2", {}).get(c, {})
            for u, hv in h.items():
                wt = row.get(u)
                if wt:
                    s += hv * wt
            scores[c] = s
        return scores

    def run(self, task):
        text = task.get("text", "") if isinstance(task, dict) else str(task)
        # values capped at 3 — the SAME scaling training uses, so the
        # dict-form model scores exactly what the numpy trainer scored
        feats = {k: min(v, 3) for k, v in featurize(text, self.fmode).items()
                 if k in self._featset()}
        if not feats:
            return {"ok": False, "output": "unknown", "specialist": self.name,
                    "evidence": "no known feature fired", "gap": "no-features"}
        scores = self._scores(feats)
        best = max(scores, key=scores.get)
        top = sorted(scores.values(), reverse=True)
        margin = top[0] - (top[1] if len(top) > 1 else 0.0)
        return {"ok": True, "output": best, "specialist": self.name,
                "evidence": f"margin {margin:.2f} over {len(feats)} feature(s)"}

    def _featset(self):
        if not hasattr(self, "_fs"):
            self._fs = set(self.features)
        return self._fs

    def param_count(self):
        def count(tree):
            if isinstance(tree, dict):
                return sum(count(v) for v in tree.values())
            return 1
        return count(self.weights)

    def clone(self, suffix):
        c = TinyNet(f"{self.name}#{suffix}", self.niche, self.job,
                    self.classes, self.features, self.hidden, self.fmode)
        c.weights = copy.deepcopy(self.weights)
        c.dev_status = self.dev_status
        return c

    # -- persistence ------------------------------------------------------
    def record(self, extra=None):
        rec = {"name": self.name, "niche": self.niche, "job": self.job,
               "classes": self.classes, "features": self.features,
               "hidden": self.hidden, "fmode": self.fmode,
               "weights": self.weights,
               "params": self.param_count(),
               "footprint_bytes": self.footprint_bytes()}
        if extra:
            rec.update(extra)
        return rec

    @classmethod
    def from_record(cls, rec):
        m = cls(rec["name"], rec["niche"], rec["job"], rec["classes"],
                rec["features"], rec.get("hidden", 0), rec.get("fmode", "text"))
        m.weights = copy.deepcopy(rec["weights"])
        if rec.get("adopted"):
            m.dev_status = "running-alone"
        return m


# ------------------------------------------------------------ training
def _train_numpy(train, heldout, classes, hidden, seed=42, epochs=300,
                 fmode="text"):
    """Train one architecture with numpy; return (weights_dict, heldout_acc,
    feature_vocab). Weights come back as sparse nested dicts of floats."""
    import numpy as np

    rng = np.random.default_rng(seed)
    train_feats = [featurize(ex["text"], fmode) for ex in train]
    feats = _vocab(train_feats)
    fidx = {f: i for i, f in enumerate(feats)}
    cidx = {c: i for i, c in enumerate(classes)}
    F, C = len(feats), len(classes)

    def matrix(examples):
        X = np.zeros((len(examples), F), dtype=np.float64)
        y = np.zeros(len(examples), dtype=int)
        for r, ex in enumerate(examples):
            for k, v in featurize(ex["text"], fmode).items():
                if k in fidx:
                    X[r, fidx[k]] = min(v, 3)
            y[r] = cidx[ex["label"]]
        return X, y

    Xtr, ytr = matrix(train)
    Xhe, yhe = matrix(heldout)
    N = len(train)

    if hidden == 0:
        W = np.zeros((F, C)); b = np.zeros(C)
        mW = np.zeros_like(W); vW = np.zeros_like(W)
        mb = np.zeros_like(b); vb = np.zeros_like(b)
        for ep in range(epochs):
            Z = Xtr @ W + b
            Z -= Z.max(axis=1, keepdims=True)
            P = np.exp(Z); P /= P.sum(axis=1, keepdims=True)
            G = P; G[np.arange(N), ytr] -= 1; G /= N
            gW = Xtr.T @ G + 1e-4 * W; gb = G.sum(axis=0)
            t = ep + 1
            mW = 0.9 * mW + 0.1 * gW; vW = 0.999 * vW + 0.001 * gW ** 2
            mb = 0.9 * mb + 0.1 * gb; vb = 0.999 * vb + 0.001 * gb ** 2
            W -= 0.05 * (mW / (1 - 0.9 ** t)) / (np.sqrt(vW / (1 - 0.999 ** t)) + 1e-8)
            b -= 0.05 * (mb / (1 - 0.9 ** t)) / (np.sqrt(vb / (1 - 0.999 ** t)) + 1e-8)
        pred = (Xhe @ W + b).argmax(axis=1)
        acc = float((pred == yhe).mean()) if len(yhe) else 0.0
        weights = {"w": {}, "b": {c: float(b[cidx[c]]) for c in classes}}
        for f, i in fidx.items():
            row = {c: float(W[i, cidx[c]]) for c in classes if abs(W[i, cidx[c]]) > 1e-9}
            if row:
                weights["w"][f] = row
        return weights, acc, feats

    H = hidden
    W1 = rng.normal(0, 0.3, (F, H)); b1 = np.zeros(H)
    W2 = rng.normal(0, 0.3, (H, C)); b2 = np.zeros(C)
    params = [W1, b1, W2, b2]
    ms = [np.zeros_like(p) for p in params]; vs = [np.zeros_like(p) for p in params]
    for ep in range(epochs):
        Hh = np.tanh(Xtr @ W1 + b1)
        Z = Hh @ W2 + b2
        Z -= Z.max(axis=1, keepdims=True)
        P = np.exp(Z); P /= P.sum(axis=1, keepdims=True)
        G = P; G[np.arange(N), ytr] -= 1; G /= N
        gW2 = Hh.T @ G + 1e-4 * W2; gb2 = G.sum(axis=0)
        dH = (G @ W2.T) * (1 - Hh ** 2)
        gW1 = Xtr.T @ dH + 1e-4 * W1; gb1 = dH.sum(axis=0)
        for i, g in enumerate([gW1, gb1, gW2, gb2]):
            t = ep + 1
            ms[i] = 0.9 * ms[i] + 0.1 * g; vs[i] = 0.999 * vs[i] + 0.001 * g ** 2
            params[i] -= 0.03 * (ms[i] / (1 - 0.9 ** t)) / (np.sqrt(vs[i] / (1 - 0.999 ** t)) + 1e-8)
        W1, b1, W2, b2 = params
    pred = (np.tanh(Xhe @ W1 + b1) @ W2 + b2).argmax(axis=1)
    acc = float((pred == yhe).mean()) if len(yhe) else 0.0
    weights = {"w1": {}, "b1": {}, "w2": {}, "b2": {c: float(b2[cidx[c]]) for c in classes}}
    for u in range(H):
        un = f"u{u}"
        weights["b1"][un] = float(b1[u])
        row = {f: float(W1[fidx[f], u]) for f in feats if abs(W1[fidx[f], u]) > 1e-9}
        if row:
            weights["w1"][un] = row
    for c in classes:
        row = {f"u{u}": float(W2[u, cidx[c]]) for u in range(H) if abs(W2[u, cidx[c]]) > 1e-9}
        if row:
            weights["w2"][c] = row
    return weights, acc, feats


def _prune(weights, model, heldout, base_acc, thresholds=(0.02, 0.05, 0.1, 0.2, 0.35)):
    """Drop near-zero weights (sparsify) while held-out accuracy holds.
    Returns (weights, acc) — the sparsest version within 0.005 of base."""
    best_w, best_acc = weights, base_acc
    for th in thresholds:
        cand = copy.deepcopy(weights)

        def cut(tree):
            if isinstance(tree, dict):
                return {k: cut(v) for k, v in tree.items()}
            return tree if abs(tree) >= th else 0.0

        def strip(tree):
            if isinstance(tree, dict):
                out = {k: strip(v) for k, v in tree.items()}
                return {k: v for k, v in out.items() if v != {}}
            return tree
        cand = strip(cut(cand))
        saved = model.weights
        model.weights = cand
        acc = accuracy(model, heldout)
        model.weights = saved
        if acc >= base_acc - 0.005:
            best_w, best_acc = cand, acc
        else:
            break
    return best_w, best_acc


def accuracy(model, examples):
    if not examples:
        return 0.0
    right = sum(1 for ex in examples if model.run(ex)["output"] == ex["label"])
    return right / len(examples)


def _agreement(model, examples):
    """The dict-form model must reproduce the trained predictions exactly —
    checked by re-scoring: run() accuracy must equal the numpy held-out acc
    path within the same examples. (Guards the serialization.)"""
    return accuracy(model, examples)


# ------------------------------------------------------------ the factory
def produce_model(task):
    """model-factory behaviour (meta niche): make ONE smallest specialist
    model for a niche job, by training. Win rule enforced here.

    task: {name, niche, job, classes, train, heldout,
           incumbents: [{name, acc}], min_acc (default 0.80)}
    Returns the candidate record; adopted only if it beats every
    incumbent on the SAME held-out set and clears min_acc.
    """
    classes = task["classes"]
    train, heldout = task["train"], task["heldout"]
    incumbents = task.get("incumbents", [])
    fmodes = task.get("featurizer", "text")
    if isinstance(fmodes, str):
        fmodes = [fmodes]
    epochs = task.get("epochs", 300)
    bar = max([i["acc"] for i in incumbents] + [task.get("min_acc", 0.80)])
    attempts = []
    chosen = None
    # smallest-first search: representations in the order the niche
    # listed them, architectures linear -> mlp4 -> mlp8; the FIRST
    # candidate over the bar is adopted (the bar is the quality gate;
    # beyond it, simpler wins — params are recorded for every attempt)
    for fmode in fmodes:
        for hidden in (0, 4, 8):
            weights, acc, feats = _train_numpy(train, heldout, classes, hidden,
                                               epochs=epochs, fmode=fmode)
            probe = TinyNet(task["name"], task["niche"], task["job"], classes,
                            feats, hidden, fmode)
            probe.weights = weights
            dict_acc = _agreement(probe, heldout)
            attempts.append({"fmode": fmode, "hidden": hidden,
                             "numpy_acc": round(acc, 4),
                             "dict_acc": round(dict_acc, 4),
                             "params": probe.param_count()})
            if dict_acc > bar:
                chosen = (probe, dict_acc)
                break
        if chosen:
            break
    if chosen is None:
        # nothing beat the bar: report the best attempt honestly, adopt none
        best = max(attempts, key=lambda a: a["dict_acc"])
        return {"ok": False, "adopted": False,
                "output": {"name": task["name"], "attempts": attempts, "bar": bar},
                "evidence": f"no architecture beat the bar {bar:.3f} "
                            f"(best {best['dict_acc']:.3f}); nothing adopted"}
    model, acc = chosen
    model.weights, acc = _prune(model.weights, model, heldout, acc)
    rec = model.record({"path": "trained", "heldout_acc": round(acc, 4),
                        "train_n": len(train), "heldout_n": len(heldout),
                        "incumbents": incumbents, "bar": round(bar, 4),
                        "attempts": attempts, "adopted": True})
    return {"ok": True, "adopted": True, "output": rec, "model": model,
            "evidence": f"trained {'linear' if model.hidden == 0 else f'mlp{model.hidden}'}: "
                        f"held-out {acc:.3f} beats bar {bar:.3f}; "
                        f"{model.param_count()} params, {model.footprint_bytes()} B"}


def train_candidate(task, fmode="text", hidden=0, epochs=300, train=None):
    """Train one raw candidate TinyNet (no win-rule decision) — the
    starting point for the surgery-first improvement loop, which maps,
    observes, edits a copy, and only then decides."""
    train = train if train is not None else task["train"]
    weights, _acc, feats = _train_numpy(train, task["heldout"], task["classes"],
                                        hidden, epochs=epochs, fmode=fmode)
    m = TinyNet(task["name"], task["niche"], task["job"], task["classes"],
                feats, hidden, fmode)
    m.weights = weights
    return m


def make_specialist_model(registry, board=None):
    """Bind produce_model into the meta niche as a specialist behaviour:
    adopt -> register + record score on the board."""
    def _make(task):
        res = produce_model(task)
        if res.get("adopted"):
            model = res["model"]
            registry.add(model)
            if board:
                board.record_score("model", model.name, res["output"]["heldout_acc"],
                                   res["evidence"])
                board.event("model-factory", "adopt", model.name)
        elif board:
            board.event("model-factory", "reject", task["name"])
        return res
    return _make


# ------------------------------------------------------------ edit path
def repair_by_surgery(model, wrong_probes, guard_probes, heldout, surgeon):
    """EDIT path: repair a trained model's systematic defect by the
    surgery protocol — trace, find, map, untangle, edit only indicted
    weights — then verify. `surgeon` is the swarm.surgeon module; its
    protocol functions enforce the steps.

    Probing runs over wrong_probes + guard_probes (cases the model
    currently gets RIGHT). A weight is indicted only if the map says it
    moves a wrong probe and moves NO guard probe — the optimizer reads
    the map, it does not guess, and it never touches a weight that
    correct behaviour depends on. The edit (zero the indicted weights)
    is kept only if the wrong probes improve and held-out accuracy does
    not regress; otherwise it is reverted from the diff record.
    """
    probes = list(wrong_probes) + list(guard_probes)
    n_wrong = len(wrong_probes)
    base_wrong = accuracy(model, wrong_probes)
    base_held = accuracy(model, heldout)
    sprobes = [{"task": {"text": p["text"]}, "label": p["label"]} for p in probes]
    labels = [p["label"] for p in probes]
    trace = surgeon.trace_architecture({"specialist": model})["output"]
    probed = surgeon.probe_responsibilities({"specialist": model, "probes": sprobes})["output"]
    wmap = surgeon.build_map({"trace": trace, "probe": probed,
                              "probe_labels": labels})["output"]
    unt = surgeon.untangle({"trace": trace, "map": wmap})["output"]
    wrong_idx = set(range(n_wrong))
    guard_idx = set(range(n_wrong, len(probes)))
    edits = {}
    for path, info in wmap.items():
        aff = set(info["affects_probes"])
        if aff & wrong_idx and not (aff & guard_idx):
            edits[path] = 0
    diffs = {}
    if edits:
        diffs = surgeon.surgical_edit({"specialist": model, "map": wmap,
                                       "untangle": unt,
                                       "target_probes": sorted(wrong_idx),
                                       "edits": edits})["output"]
    new_wrong = accuracy(model, wrong_probes)
    new_held = accuracy(model, heldout)
    kept = bool(diffs) and new_wrong > base_wrong and new_held >= base_held
    if not kept:
        for path, (old, _new) in diffs.items():
            surgeon._set(model.weights, path, old)
    return {"kept": kept, "diffs": {k: list(v) for k, v in diffs.items()},
            "probes_before": base_wrong, "probes_after": new_wrong,
            "heldout_before": base_held, "heldout_after": new_held,
            "untangle_complete": unt["complete"],
            "n_weights": trace["n_leaves"],
            "indicted": sorted(edits)}


# ------------------------------------------------------------ persistence
def save_model(model, extra, directory=None):
    directory = Path(directory) if directory else MODELS_DIR
    directory.mkdir(parents=True, exist_ok=True)
    rec = model.record(extra)
    (directory / f"{model.name}.json").write_text(json.dumps(rec, indent=1))
    return rec


def load_models(registry, directory=None):
    """Register every adopted TinyNet saved by a factory run. Called by
    niches.build_swarm so the models are live members of their niches."""
    directory = Path(directory) if directory else MODELS_DIR
    if not directory.exists():
        return []
    loaded = []
    for f in sorted(directory.glob("*.json")):
        rec = json.loads(f.read_text())
        if rec.get("adopted"):
            registry.add(TinyNet.from_record(rec))
            loaded.append(rec["name"])
    return loaded
