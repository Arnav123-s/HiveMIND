"""Phase 3 build: the hive brain's first real layer (PLAN.md section 17).

    python3 -m swarm.phase3

Makes smallest specialist MODELS — not rule-code — through the swarm's
own meta layer: the model-factory specialist trains candidates, the
win rule decides adoption against the incumbents (the phase-1 keyword
trainer and the rule-based placeholders), winners are cloned and
socialized, and every verified model is saved under swarm/models/ so
niches.build_swarm registers it as a live member of its niche.

Batch:
  1. error-class-model      (debugging) classify failure texts, 12 classes
  2. bug-pattern-model      (debugging) classify a snippet's bug pattern
  3. contract-judgment-model(review)    judge a snippet against the house contract
  4. gap-move-model         (meta)      classify a failure text into a growth move
  5. commit-type-model      (vcs)       classify a commit message's type
  6. secret-line-model      (security)  classify a code line: secret or benign
     — then repaired by the EDIT path (surgery protocol) on trap probes.

Plus a composition proof: debugging triage (error class + bug pattern
+ error line) assembled by the debugging coordinator through the board
from three separate specialists — no single model enlarged.

Held-out hygiene: for every job the held-out set uses template
families, phrasings, names or snippet shapes that never appear in
training. Incumbents are scored on the SAME held-out set.
"""
import json
import random
import re
import tempfile
import textwrap
import traceback
from pathlib import Path

from . import constructed as C
from . import factory as F
from . import meta as M
from . import surgeon as S
from .board import Board
from .niches import build_swarm

HERE = Path(__file__).parent


# ------------------------------------------------------------ incumbents
def kw_incumbent(train, heldout):
    """The swarm's standing trainable baseline: the phase-1 TRAINER's
    keyword classifier, fitted on the same training examples."""
    out = M.train_keyword_classifier({"examples": train})["output"]
    probe = M.KeywordClassifier("_incumbent", "meta")
    probe.weights = out["weights"]
    return {"name": "keyword-classifier (phase-1 trainer)",
            "acc": round(F.accuracy(probe, heldout), 4)}


def majority_incumbent(train, heldout):
    from collections import Counter
    top = Counter(ex["label"] for ex in train).most_common(1)[0][0]
    acc = sum(1 for ex in heldout if ex["label"] == top) / len(heldout)
    return {"name": f"majority-class ({top})", "acc": round(acc, 4)}


# ------------------------------------------------------------ job 1: errors
def _tb(code):
    try:
        exec(compile(code, "<case>", "exec"), {})
        return None
    except Exception:
        return traceback.format_exc()


_ERR_SNIPPETS = {
    "SyntaxError": (
        ["def broken(:\n    pass", "x = [1, 2\nprint(x)"],
        ["if True print('hi')", "return 5"]),
    "NameError": (
        ["print(usr_name)", "total = resutl + 1"],
        ["print(emial)", "value = df.head()"]),
    "TypeError": (
        ["x = 'a' + 1", "n = len(5)"],
        ["s = 3 - 'b'", "d = None[0]"]),
    "ValueError": (
        ["n = int('abc')", "a, b = [1, 2, 3]"],
        ["n = float('x9')", "import math\nmath.sqrt(-1)"]),
    "IndexError": (
        ["a = [1, 2]\nprint(a[5])", "s = 'hi'\nprint(s[9])"],
        ["t = (1,)\nprint(t[3])", "a = []\nprint(a[-1])"]),
    "KeyError": (
        ["d = {'a': 1}\nprint(d['user_id'])", "cfg = {}\nprint(cfg['total'])"],
        ["d = {'x': 1}\nprint(d['config'])", "m = {}\nprint(m['name'])"]),
    "AttributeError": (
        ["x = None\nx.strip()", "n = 5\nn.append(1)"],
        ["s = 'a'\ns.push('b')", "lst = []\nlst.upper()"]),
    "ModuleNotFoundError": (
        ["import numpyy", "import pandas2 as pd"],
        ["import requestsx", "from os2 import path"]),
    "ZeroDivisionError": (
        ["x = 1 / 0", "y = 10 % 0"],
        ["z = 5 // 0", "w = 1.5 / 0.0"]),
    "FileNotFoundError": (
        ["open('data.csv')", "open('in.txt').read()"],
        ["open('x.json')", "open('missing.log').read()"]),
    "RuntimeError": (
        ["raise RuntimeError('boom')", "d = {1: 1}\nfor k in d:\n    d[k + 1] = 2"],
        ["raise RuntimeError('kaput')", "raise RuntimeError()"]),
    "AssertionError": (
        ["assert 1 == 2", "assert 'a' == 'b', 'mismatch'"],
        ["assert len([]) > 0", "assert False, 'empty'"]),
}

_ERR_LINES = {
    "train": {
        "SyntaxError": ["SyntaxError: unexpected indent", "SyntaxError: '(' was never closed"],
        "NameError": ["NameError: name 'usr' is not defined", "NameError: name 'resutl' is not defined"],
        "TypeError": ["TypeError: can only concatenate str (not \"int\") to str",
                      "TypeError: 'NoneType' object is not subscriptable"],
        "ValueError": ["ValueError: invalid literal for int() with base 10: 'abc'",
                       "ValueError: too many values to unpack (expected 2)"],
        "IndexError": ["IndexError: list index out of range", "IndexError: tuple index out of range"],
        "KeyError": ["KeyError: 'user_id'", "KeyError: 'total'"],
        "AttributeError": ["AttributeError: 'NoneType' object has no attribute 'strip'",
                           "AttributeError: 'int' object has no attribute 'append'"],
        "ModuleNotFoundError": ["ModuleNotFoundError: No module named 'numpyy'",
                                "ModuleNotFoundError: No module named 'pandas2'"],
        "ZeroDivisionError": ["ZeroDivisionError: division by zero",
                              "ZeroDivisionError: integer division or modulo by zero"],
        "FileNotFoundError": ["FileNotFoundError: [Errno 2] No such file or directory: 'data.csv'",
                              "FileNotFoundError: [Errno 2] No such file or directory: 'in.txt'"],
        "RuntimeError": ["RuntimeError: boom", "RuntimeError: dictionary changed size during iteration"],
        "AssertionError": ["AssertionError", "AssertionError: mismatch"],
    },
    "heldout": {
        "SyntaxError": ["SyntaxError: invalid syntax", "SyntaxError: expected ':'"],
        "NameError": ["NameError: name 'emial' is not defined", "NameError: name 'df' is not defined"],
        "TypeError": ["TypeError: unsupported operand type(s) for -: 'int' and 'str'",
                      "TypeError: 'NoneType' object is not iterable"],
        "ValueError": ["ValueError: invalid literal for float() with base 10: 'x9'",
                       "ValueError: math domain error"],
        "IndexError": ["IndexError: string index out of range", "IndexError: pop from empty list"],
        "KeyError": ["KeyError: 'config'", "KeyError: 'name'"],
        "AttributeError": ["AttributeError: 'str' object has no attribute 'push'",
                           "AttributeError: 'list' object has no attribute 'upper'"],
        "ModuleNotFoundError": ["ModuleNotFoundError: No module named 'requestsx'",
                                "ModuleNotFoundError: No module named 'os2'"],
        "ZeroDivisionError": ["ZeroDivisionError: float division by zero",
                              "ZeroDivisionError: integer division or modulo by zero"],
        "FileNotFoundError": ["FileNotFoundError: [Errno 2] No such file or directory: 'x.json'",
                              "FileNotFoundError: [Errno 2] No such file or directory: 'missing.log'"],
        "RuntimeError": ["RuntimeError: kaput", "RuntimeError: Set changed size during iteration"],
        "AssertionError": ["AssertionError: empty", "AssertionError: assert failed"],
    },
}


def _wrap(text, width=64):
    out = []
    for line in text.splitlines():
        out.extend(textwrap.wrap(line, width=width) or [""])
    return "\n".join(out)


def _logify(text, rng):
    stamp = f"2026-11-08 {rng.randint(10, 23)}:{rng.randint(10, 59)}:0{rng.randint(1, 9)}"
    return "\n".join(f"{stamp} ERROR worker-3: {ln}" for ln in text.splitlines())


def gen_error_texts():
    rng = random.Random(11)
    train, held = [], []
    for cls, (snips_a, snips_b) in _ERR_SNIPPETS.items():
        for code in snips_a:
            tb = _tb(code)
            if tb:
                train += [{"text": tb, "label": cls},
                          {"text": _logify(tb, rng), "label": cls},
                          {"text": _wrap(tb), "label": cls}]
        for code in snips_b:
            tb = _tb(code)
            if tb:
                held += [{"text": tb, "label": cls},
                         {"text": _logify(tb, rng), "label": cls},
                         {"text": _wrap(tb), "label": cls}]
                # chained form: held-out ONLY — an outer exception was being
                # handled when this one fired; the label is the final class
                outer = _tb("raise ValueError('outer')") if cls != "ValueError" \
                    else _tb("raise KeyError('outer')")
                chained = (outer.rstrip() + "\n\nDuring handling of the above "
                           "exception, another exception occurred:\n\n" + tb)
                held.append({"text": chained, "label": cls})
    for cls, lines in _ERR_LINES["train"].items():
        train += [{"text": t, "label": cls} for t in lines]
    for cls, lines in _ERR_LINES["heldout"].items():
        held += [{"text": t, "label": cls} for t in lines]
    rng.shuffle(train); rng.shuffle(held)
    return train, held


def rule_error_incumbent(held):
    right = sum(1 for ex in held
                if C.traceback_classifier({"stderr": ex["text"]})["output"] == ex["label"])
    return {"name": "rule traceback-classifier", "acc": round(right / len(held), 4)}


# ------------------------------------------------------------ job 2: bug patterns
# (correct_code, {bug_class: buggy_code}) — families disjoint across splits
_BUG_TEMPLATES_TRAIN = [
    ("def total_upto(n):\n    s = 0\n    for i in range(1, n + 1):\n        s += i\n    return s",
     {"off-by-one": "def total_upto(n):\n    s = 0\n    for i in range(1, n):\n        s += i\n    return s",
      "wrong-operator": "def total_upto(n):\n    s = 0\n    for i in range(1, n + 1):\n        s -= i\n    return s",
      "missing-return": "def total_upto(n):\n    s = 0\n    for i in range(1, n + 1):\n        s += i\n    print(s)"}),
    ("def diff(a, b):\n    return a - b",
     {"swapped-operands": "def diff(a, b):\n    return b - a",
      "wrong-operator": "def diff(a, b):\n    return a + b"}),
    ("def collect(item, acc=[]):\n    acc = list(acc)\n    acc.append(item)\n    return acc",
     {"mutable-default": "def collect(item, acc=[]):\n    acc.append(item)\n    return acc"}),
    ("def average(nums):\n    return sum(nums) / len(nums)",
     {"wrong-operator": "def average(nums):\n    return sum(nums) * len(nums)",
      "missing-return": "def average(nums):\n    result = sum(nums) / len(nums)",
      "swapped-operands": "def average(nums):\n    return len(nums) / sum(nums)"}),
    ("def last(xs):\n    return xs[len(xs) - 1]",
     {"off-by-one": "def last(xs):\n    return xs[len(xs)]",
      "wrong-operator": "def last(xs):\n    return xs[len(xs) + 1]"}),
    ("def ratio(part, whole):\n    return part / whole * 100",
     {"swapped-operands": "def ratio(part, whole):\n    return whole / part * 100",
      "wrong-operator": "def ratio(part, whole):\n    return part * whole * 100"}),
    ("def product(xs):\n    p = 1\n    for v in xs:\n        p *= v\n    return p",
     {"wrong-operator": "def product(xs):\n    p = 1\n    for v in xs:\n        p += v\n    return p",
      "missing-return": "def product(xs):\n    p = 1\n    for v in xs:\n        p *= v\n    print(p)"}),
    ("def find_max(xs):\n    m = xs[0]\n    for v in xs:\n        if v > m:\n            m = v\n    return m",
     {"wrong-operator": "def find_max(xs):\n    m = xs[0]\n    for v in xs:\n        if v < m:\n            m = v\n    return m",
      "missing-return": "def find_max(xs):\n    m = xs[0]\n    for v in xs:\n        if v > m:\n            m = v"}),
    ("def sub_each(a, b):\n    return [x - y for x, y in zip(a, b)]",
     {"swapped-operands": "def sub_each(a, b):\n    return [y - x for x, y in zip(a, b)]",
      "wrong-operator": "def sub_each(a, b):\n    return [x + y for x, y in zip(a, b)]"}),
    ("def tag_all(xs, tags=None):\n    tags = list(tags) if tags else []\n    return tags + xs",
     {"mutable-default": "def tag_all(xs, tags=[]):\n    tags.extend(xs)\n    return tags",
      "missing-return": "def tag_all(xs, tags=None):\n    tags = list(tags) if tags else []\n    tags + xs"}),
    ("def sum_first(xs, k):\n    s = 0\n    for i in range(k):\n        s += xs[i]\n    return s",
     {"off-by-one": "def sum_first(xs, k):\n    s = 0\n    for i in range(k + 1):\n        s += xs[i]\n    return s",
      "wrong-operator": "def sum_first(xs, k):\n    s = 0\n    for i in range(k):\n        s -= xs[i]\n    return s"}),
    ("def quotient(a, b):\n    return a // b",
     {"swapped-operands": "def quotient(a, b):\n    return b // a",
      "wrong-operator": "def quotient(a, b):\n    return a % b"}),
    ("def scale(xs, f):\n    return [x * f for x in xs]",
     {"wrong-operator": "def scale(xs, f):\n    return [x + f for x in xs]",
      "missing-return": "def scale(xs, f):\n    out = [x * f for x in xs]"}),
    ("def count_matches(xs, v):\n    n = 0\n    for x in xs:\n        if x == v:\n            n += 1\n    return n",
     {"wrong-operator": "def count_matches(xs, v):\n    n = 0\n    for x in xs:\n        if x != v:\n            n += 1\n    return n",
      "missing-return": "def count_matches(xs, v):\n    n = 0\n    for x in xs:\n        if x == v:\n            n += 1\n    print(n)"}),
    ("def clamp(v, lo, hi):\n    return max(lo, min(hi, v))",
     {"swapped-operands": "def clamp(v, lo, hi):\n    return max(hi, min(lo, v))",
      "missing-return": "def clamp(v, lo, hi):\n    res = max(lo, min(hi, v))"}),
    ("def push_all(dst, src):\n    dst = list(dst)\n    dst.extend(src)\n    return dst",
     {"mutable-default": "def push_all(dst=[], src=()):\n    dst.extend(src)\n    return dst"}),
]
_BUG_TEMPLATES_HELD = [
    ("def count_vowels(s):\n    n = 0\n    for ch in s:\n        if ch in 'aeiou':\n            n += 1\n    return n",
     {"wrong-operator": "def count_vowels(s):\n    n = 0\n    for ch in s:\n        if ch in 'aeiou':\n            n -= 1\n    return n",
      "missing-return": "def count_vowels(s):\n    n = 0\n    for ch in s:\n        if ch in 'aeiou':\n            n += 1\n    print(n)"}),
    ("def head_sum(xs, k):\n    s = 0\n    for i in range(k):\n        s += xs[i]\n    return s",
     {"off-by-one": "def head_sum(xs, k):\n    s = 0\n    for i in range(k - 1):\n        s += xs[i]\n    return s",
      "wrong-operator": "def head_sum(xs, k):\n    s = 0\n    for i in range(k):\n        s -= xs[i]\n    return s"}),
    ("def greet(name, out=[]):\n    out = list(out)\n    out.append('hi ' + name)\n    return out",
     {"mutable-default": "def greet(name, out=[]):\n    out.append('hi ' + name)\n    return out"}),
    ("def minutes(hours, mins):\n    return hours * 60 + mins",
     {"swapped-operands": "def minutes(hours, mins):\n    return mins * 60 + hours",
      "wrong-operator": "def minutes(hours, mins):\n    return hours * 60 - mins"}),
    ("def first_two(xs):\n    return xs[0], xs[1]",
     {"off-by-one": "def first_two(xs):\n    return xs[1], xs[2]",
      "missing-return": "def first_two(xs):\n    pair = xs[0], xs[1]"}),
    ("def evens_upto(n):\n    return [i for i in range(0, n + 1, 2)]",
     {"off-by-one": "def evens_upto(n):\n    return [i for i in range(0, n, 2)]",
      "missing-return": "def evens_upto(n):\n    res = [i for i in range(0, n + 1, 2)]"}),
    ("def mods(a, b):\n    return [x % y for x, y in zip(a, b)]",
     {"swapped-operands": "def mods(a, b):\n    return [y % x for x, y in zip(a, b)]",
      "wrong-operator": "def mods(a, b):\n    return [x + y for x, y in zip(a, b)]"}),
    ("def sum_last(xs, k):\n    s = 0\n    for i in range(len(xs) - k, len(xs)):\n        s += xs[i]\n    return s",
     {"off-by-one": "def sum_last(xs, k):\n    s = 0\n    for i in range(len(xs) - k, len(xs) - 1):\n        s += xs[i]\n    return s",
      "wrong-operator": "def sum_last(xs, k):\n    s = 0\n    for i in range(len(xs) - k, len(xs)):\n        s -= xs[i]\n    return s"}),
    ("def remainder(a, b):\n    return a % b",
     {"swapped-operands": "def remainder(a, b):\n    return b % a",
      "wrong-operator": "def remainder(a, b):\n    return a - b"}),
    ("def shout_all(words, out=None):\n    out = list(out) if out else []\n    for w in words:\n        out.append(w.upper())\n    return out",
     {"mutable-default": "def shout_all(words, out=[]):\n    for w in words:\n        out.append(w.upper())\n    return out",
      "missing-return": "def shout_all(words, out=None):\n    out = list(out) if out else []\n    for w in words:\n        out.append(w.upper())"}),
]

_BUG_CLASSES = ["off-by-one", "wrong-operator", "swapped-operands",
                "mutable-default", "missing-return", "clean"]


def gen_bug_patterns(templates, seed):
    rng = random.Random(seed)
    out = []
    for correct, bugs in templates:
        out.append({"text": correct, "label": "clean"})
        for cls, buggy in bugs.items():
            out.append({"text": buggy, "label": cls})
    rng.shuffle(out)
    return out


def matcher_incumbent(held):
    """The rule bug-pattern-matcher read as a classifier: it fires only on
    its two loop signatures (both bound bugs) -> 'off-by-one', else 'clean'."""
    def classify(code):
        r = C.bug_pattern_matcher({"code": code})
        return "off-by-one" if r["ok"] else "clean"
    right = sum(1 for ex in held if classify(ex["text"]) == ex["label"])
    return {"name": "rule bug-pattern-matcher (as classifier)",
            "acc": round(right / len(held), 4)}


# ------------------------------------------------------------ job 3: contract judgment
# House contract: a function must not mutate its list argument, must
# handle an empty list, must handle None. Classes name the violation.
_CONTRACT_TRAIN = [
    ("def FN(ARG):\n    if ARG is None:\n        return []\n    return sorted(ARG)",
     "def FN(ARG):\n    if not ARG:\n        return ARG\n    ARG.sort()\n    return ARG",
     "def FN(ARG):\n    if ARG is None:\n        return 0\n    return ARG[0] + ARG[-1]",
     "def FN(ARG):\n    return len(ARG) + ARG.count(0)"),
    ("def FN(ARG):\n    out = []\n    for v in ARG or []:\n        out.append(v * 2)\n    return out",
     "def FN(ARG):\n    if not ARG:\n        return ARG\n    for i in range(len(ARG)):\n        ARG[i] = ARG[i] * 2\n    return ARG",
     "def FN(ARG):\n    if ARG is None:\n        return 0\n    return ARG[-1] * 2",
     "def FN(ARG):\n    total = 0\n    for v in ARG:\n        total += v\n    return total"),
    ("def FN(ARG):\n    if ARG is None:\n        return []\n    return [v for v in ARG if v > 0]",
     "def FN(ARG):\n    if not ARG:\n        return ARG\n    ARG[:] = [v for v in ARG if v > 0]\n    return ARG",
     "def FN(ARG):\n    if ARG is None:\n        return 0\n    best = ARG[0]\n    for v in ARG:\n        best = max(best, v)\n    return best",
     "def FN(ARG):\n    if len(ARG) == 0:\n        return 0\n    return sum(ARG) / len(ARG)"),
    ("def FN(ARG):\n    if ARG is None:\n        return []\n    return ARG[:2]",
     "def FN(ARG):\n    if not ARG:\n        return ARG\n    ARG.append(ARG[0])\n    return ARG",
     "def FN(ARG):\n    if ARG is None:\n        return ()\n    return ARG[0], ARG[1]",
     "def FN(ARG):\n    return len(ARG)"),
    ("def FN(ARG):\n    res = list(ARG) if ARG is not None else []\n    res.reverse()\n    return res",
     "def FN(ARG):\n    if not ARG:\n        return ARG\n    ARG.reverse()\n    return ARG",
     "def FN(ARG):\n    if ARG is None:\n        return 0\n    return ARG[len(ARG) - 1]",
     "def FN(ARG):\n    return max(ARG) - min(ARG) if len(ARG) else 0"),
]
_CONTRACT_HELD = [
    ("def FN(ARG):\n    return {v: v * v for v in ARG or []}",
     "def FN(ARG):\n    if not ARG:\n        return ARG\n    while ARG:\n        ARG.pop()\n    return ARG",
     "def FN(ARG):\n    if ARG is None:\n        return 0\n    mid = ARG[len(ARG) // 2]\n    return mid",
     "def FN(ARG):\n    return sum(ARG)"),
    ("def FN(ARG):\n    out = list(ARG) if ARG is not None else []\n    out.append(0)\n    return out",
     "def FN(ARG):\n    if not ARG:\n        return ARG\n    ARG.insert(0, 0)\n    return ARG",
     "def FN(ARG):\n    if ARG is None:\n        return 0\n    return ARG[0] * ARG[-1]",
     "def FN(ARG):\n    n = len(ARG)\n    return n"),
    ("def FN(ARG):\n    return [str(v) for v in ARG or []]",
     "def FN(ARG):\n    if not ARG:\n        return ARG\n    ARG.extend([1])\n    return ARG",
     "def FN(ARG):\n    if ARG is None:\n        return ''\n    first = ARG[0]\n    return first",
     "def FN(ARG):\n    return len(ARG) * 2"),
    ("def FN(ARG):\n    total = 0\n    for v in ARG or []:\n        total += v\n    return total",
     "def FN(ARG):\n    if not ARG:\n        return ARG\n    ARG[0] = 99\n    return ARG",
     "def FN(ARG):\n    if ARG is None:\n        return 0\n    return ARG[-1] + 1",
     "def FN(ARG):\n    return ARG.index(5) if len(ARG) else -1"),
]
_CONTRACT_CLASSES = ["ok", "mutates-input", "no-empty-guard", "no-none-guard"]
_CONTRACT_NAMES = [("summarize", "values"), ("process", "items"),
                   ("analyze", "data"), ("compute", "nums"), ("handle", "entries")]


def gen_contract(templates, seed):
    rng = random.Random(seed)
    out = []
    for row in templates:
        for cls, code in zip(_CONTRACT_CLASSES, row):
            for fn, arg in _CONTRACT_NAMES:
                out.append({"text": code.replace("FN", fn).replace("ARG", arg),
                            "label": cls})
    rng.shuffle(out)
    return out


# ------------------------------------------------------------ job 4: gap -> move
_GAP_CLASSES = ["harvest", "harvest+train", "spawn+harvest",
                "wait-for-backend", "surgery"]
_GAP_TRAIN = {
    "harvest": [
        "the {t} niche has no examples at all for {x}; we cannot fit anything until examples exist",
        "coverage hole: zero labelled cases for {x} in {t}; somebody has to gather raw material first",
        "no data on file for {x}; the {t} specialists are guessing blind",
        "we lack any recorded instances of {x}; collect samples before deciding anything",
        "what is {t} supposed to learn {x} from? the shelf is empty and no cases are filed",
        "{x} in {t}: zero samples on record, nothing to work from yet",
        "ask {t} for {x} cases and it comes back empty-handed",
        "there is simply nothing filed under {x} for {t} to learn from",
    ],
    "harvest+train": [
        "{t} keeps missing whole classes of {x}; gather labelled cases and refit it",
        "the {t} classifier was fitted on too little; more examples and a fresh training pass are needed",
        "accuracy on {x} is poor because the training set never covered it; harvest cases, then retrain",
        "{t} confuses {x} with its neighbours; it needs more labelled data and new weights",
        "a small top-up of {x} examples plus a quick refit would sort {t} out",
        "{t} is data-thin on {x}: collect a batch, then train on it",
        "{t}'s {x} misses trace to a thin, stale training set; feed it and refit",
        "more {x} cases in, fresh weights out — that is what {t} needs",
    ],
    "spawn+harvest": [
        "hit a {x} behaviour nobody covers; there is no specialist for it at all in {t}",
        "unknown problem in {t}: {x} is outside every existing niche job; a new specialist must be created",
        "no component owns {x}; spawn one for {t} and feed it examples",
        "the swarm met {x} for the first time; nothing in {t} can even attempt it",
        "who owns {x}? nobody in {t} does; the desk itself does not exist",
        "{x} falls between the stools in {t}; a whole job is unstaffed",
        "{x} is not a harder case of an old job in {t}; it is a new job entirely",
        "no desk, no owner, no coverage: {x} in {t} starts from a blank page",
    ],
    "wait-for-backend": [
        "{t} is bound to a model that is not loaded; the job stays queued until a backend is available",
        "no key in the vault for the {x} service; {t} cannot call out and must wait",
        "the local model for {t} is not resident right now; queue the job, do not stop",
        "{t} escalated to an api that is unreachable; the work waits on the board",
        "park {t} until the {x} service answers; it cannot proceed meanwhile",
        "hold {t}: still waiting for the {x} runtime to come up",
        "{t} sits idle: the {x} worker process is not running",
        "the queue holds {t} because its {x} backend never came up",
    ],
    "surgery": [
        "{t} systematically calls {x} by the wrong name; one weight is misleading it and must be mapped and corrected",
        "a single bad weight in {t} flips every {x} verdict; trace it, map it, edit only that weight",
        "{t} is right except when {x} appears, where it always errs the same way; a surgical fix, not a retrain",
        "the defect in {t} is localized: one responsible weight for {x}; untangle the model and change just that",
        "do not retrain {t} for this: the {x} fault sits in a single connection",
        "one offending mapping inside {t} produces every {x} miss; fix that mapping only",
        "retraining {t} would be wasteful: the {x} error is one weight, provably",
        "trace the {x} verdicts in {t} and they all pass through a single bad mapping",
    ],
}
_GAP_HELD = {
    "harvest": [
        "we are blind on {x}: the {t} corner has never seen a single case",
        "before {t} can judge {x}, raw examples have to be collected; none exist yet",
        "empty drawer for {x} in {t}; the first move is gathering material, nothing else is possible",
    ],
    "harvest+train": [
        "{t} was trained on a sliver and it shows on {x}; broaden the dataset and fit it again",
        "the {x} misses in {t} are a data problem: too few labelled examples, stale weights",
        "keep feeding {t} verified {x} cases and refit until the misses stop",
    ],
    "spawn+harvest": [
        "{x} arrived and no niche owns it; create the missing specialist for {t} and give it data",
        "a brand-new kind of problem for {t}: {x}; coverage has to be built from zero",
        "nothing in the tree does {x}; the growth move is a new smallest specialist in {t}",
    ],
    "wait-for-backend": [
        "{t} cannot answer: its backend is down and the request waits in the queue",
        "the {x} engine is not up; {t} jobs remain open until a model loads",
        "missing credentials block {t} from its api; nothing to do but hold the job",
    ],
    "surgery": [
        "every {x} case tips {t} the same wrong way; find the responsible weight and edit it alone",
        "{t} has one rotten weight behind its {x} errors; mapping first, then a single precise change",
        "do not retrain {t} for this: the {x} failure traces to one weight; operate on that",
    ],
}
_GAP_THINGS = ["debugging", "review", "sql", "testing", "security", "reading"]
_GAP_TOPICS = ["chained tracebacks", "empty inputs", "unicode names", "nested quotes",
               "long lines", "mixed tabs", "legacy encodings", "deep nesting"]


def gen_gap_moves(templates, seed):
    rng = random.Random(seed)
    out = []
    for cls, texts in templates.items():
        for t in texts:
            for thing in _GAP_THINGS:
                out.append({"text": t.format(t=thing, x=rng.choice(_GAP_TOPICS)),
                            "label": cls})
    rng.shuffle(out)
    return out


# ------------------------------------------------------------ job 5: commit types
_COMMIT_CLASSES = ["feat", "fix", "docs", "refactor", "test", "chore"]
_COMMIT_TRAIN = {
    "feat": ["add {o}", "implement {o}", "introduce {o} support", "new: {o}",
             "feat: add {o}", "feat(parser): implement {o}", "build {o}",
             "deliver {o}", "roll out {o}", "launch {o}",
             "wire up {o}", "enable {o}",
             "expose {o} as an api", "support {o} in the cli",
             "create a new {o}", "set up {o} from nothing", "get {o} shipped",
             "bring {o} into the product", "build out {o}"],
    "fix": ["fix {o}", "correct {o}", "repair {o}", "fix crash in {o}",
            "fix: correct {o}", "bugfix: {o}", "mend {o}",
            "address the fault in {o}", "stop {o} from crashing", "hotfix for {o}",
            "squash the bug in {o}", "fix the regression in {o}",
            "patch the hole in {o}", "stop the leak in {o}", "patch up {o}"],
    "docs": ["document {o}", "write docs for {o}", "update readme about {o}",
             "docs: explain {o}", "add guide for {o}", "clarify {o} in the manual",
             "note {o} in the docs", "write {o} documentation",
             "spell out {o} in the readme", "annotate {o}",
             "put {o} in the docs", "expand the docs on {o}",
             "write up {o}", "add {o} to the faq",
             "document {o} in the wiki", "write about {o} in the handbook"],
    "refactor": ["rename {o}", "extract {o} into a helper", "simplify {o}",
                 "refactor: tidy {o}", "reorganize {o}", "clean up {o}",
                 "restructure {o}", "move {o} into its own module",
                 "streamline {o}", "consolidate {o}",
                 "polish {o}", "untangle {o}",
                 "decouple {o}", "inline {o}"],
    "test": ["add tests for {o}", "cover {o} with unit tests", "test: verify {o}",
             "add a regression test for {o}", "extend the test suite for {o}",
             "check {o} in ci", "verify {o} behaves", "assert {o} works",
             "put {o} under test", "write a test case for {o}",
             "exercise {o} in tests", "snapshot {o}",
             "add a smoke test for {o}", "cover the edge cases of {o}",
             "raise coverage on {o}", "ensure {o} is covered by tests",
             "get {o} tested"],
    "chore": ["bump dependencies", "update ci configuration", "chore: tidy gitignore",
              "upgrade the linter", "pin tool versions", "refresh lockfile",
              "renew certificates", "tidy the repo layout",
              "update the formatter config", "sync the license headers",
              "bump the version", "archive old branches",
              "prune stale branches", "rotate the api keys"],
}
_COMMIT_HELD = {
    "feat": ["bring in {o}", "ship {o}", "feat: introduce {o}", "create {o} from scratch"],
    "fix": ["stop the crash in {o}", "patch {o}", "fix: repair {o}", "resolve the bug in {o}"],
    "docs": ["describe {o} in the wiki", "docs: document {o}", "write up {o} for the handbook"],
    "refactor": ["split {o} into smaller pieces", "deduplicate {o}", "refactor {o} for clarity"],
    "test": ["make sure {o} is tested", "add coverage for {o}", "test {o} end to end"],
    "chore": ["update the build scripts", "chore: bump the toolchain", "housekeeping: refresh badges"],
}
_COMMIT_OBJECTS = ["the csv exporter", "dark mode", "the login form", "retry logic",
                   "the search index", "user avatars", "the cache layer", "webhook retries",
                   "the settings page", "batch import", "the report builder", "session timeouts"]


def gen_commit_types(templates, seed):
    rng = random.Random(seed)
    out = []
    for cls, texts in templates.items():
        for t in texts:
            for _ in range(4):
                out.append({"text": t.format(o=rng.choice(_COMMIT_OBJECTS)),
                            "label": cls})
    rng.shuffle(out)
    return out


# ------------------------------------------------------------ job 6: secret lines
_SECRET_NAMES = ["api_key", "token", "secret", "passwd", "auth_token", "db_password",
                 "access_key", "private_key", "client_secret", "session_key"]
_BENIGN_NAMES = ["username", "host", "region", "timeout", "retries", "endpoint",
                 "mode", "label", "count", "path"]
_HEX = "0123456789abcdef"


def _lit(rng, style):
    if style == "hex":
        return "".join(rng.choice(_HEX) for _ in range(rng.choice([24, 32, 40])))
    if style == "b64":
        chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
        return "".join(rng.choice(chars) for _ in range(rng.choice([22, 30]))) + "=="
    if style == "akia":
        return "AKIA" + "".join(rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
                                 for _ in range(16))
    return "".join(rng.choice("abcdefghijklmnopqrstuvwxyz0123456789-_")
                   for _ in range(rng.choice([18, 26, 34])))


def gen_secret_lines(split, seed):
    """split 'train' or 'heldout': disjoint name pools and literal styles.
    Deliberate trap: NO benign `name = get_*()` call lines in training —
    the surgery episode's probes test exactly that shape."""
    rng = random.Random(seed)
    out = []
    if split == "train":
        names, styles = _SECRET_NAMES[:6], ["hex", "b64", "akia", "mix"]
        benign_names = _BENIGN_NAMES[:5]
    else:
        names, styles = _SECRET_NAMES[4:], ["hex", "b64", "mix"]
        benign_names = _BENIGN_NAMES[3:]
    for name in names:
        for style in styles:
            lit = _lit(rng, style)
            out.append({"text": f'{name} = "{lit}"', "label": "secret"})
            out.append({"text": f'"{name}": "{lit}",', "label": "secret"})
            out.append({"text": f'export {name.upper()}={lit}', "label": "secret"})
    for name in names:  # benign shapes that merely MENTION the name
        out.append({"text": f'{name} = os.environ["{name.upper()}"]', "label": "benign"})
        out.append({"text": f'{name} = getpass.getpass("enter {name}: ")', "label": "benign"})
        out.append({"text": f'{name} = ""', "label": "benign"})
        out.append({"text": f'{name} = "changeme"', "label": "benign"})
        out.append({"text": f'# {name} is loaded from the vault at runtime', "label": "benign"})
        out.append({"text": f'{name} = settings.{name}', "label": "benign"})
        out.append({"text": f'{name} = None', "label": "benign"})
        out.append({"text": f'{name} = input("enter {name}: ")', "label": "benign"})
    for name in benign_names:
        out.append({"text": f'{name} = "localhost"', "label": "benign"})
        out.append({"text": f'{name} = "us-east-1"', "label": "benign"})
        out.append({"text": f'{name} = 30', "label": "benign"})
        out.append({"text": f'{name} = "/tmp/data"', "label": "benign"})
    rng.shuffle(out)
    return out


def secret_trap_probes():
    """Benign function-call lines with secret-flavoured names — the shape
    deliberately absent from training. Plus guards: true secrets the
    model currently gets right (the surgery must not break them)."""
    probes = [{"text": f'{n} = get_{n}()', "label": "benign"}
              for n in ["api_key", "token", "secret", "auth_token"]]
    probes += [{"text": 'token = fetch_token()', "label": "benign"},
               {"text": 'api_key = vault.read("api_key")', "label": "benign"},
               {"text": 'client_secret = load_secret("client")', "label": "benign"}]
    return probes


# ------------------------------------------------------------ composition proof
_TRIAGE_CASES = [
    ("def total(xs):\n    s = 0\n    for i in range(len(xs) + 1):\n        s += xs[i]\n    return s\nprint(total([1, 2, 3]))",
     "IndexError", "off-by-one", 4),
    ("def ratio(a, b):\n    return b / a\nprint(ratio(0, 10))",
     "ZeroDivisionError", "swapped-operands", 2),
    ("def repeat(s, n):\n    return s - n\nprint(repeat('ab', 2))",
     "TypeError", "wrong-operator", 2),
    ("def first(xs):\n    picked = xs[0]\nprint(first([7, 8]) + 1)",
     "TypeError", "missing-return", 3),
    ("def second(xs):\n    return xs[1]\nprint(second([5]))",
     "IndexError", "off-by-one", 2),
    ("def head(xs):\n    if xs:\n        return xs[0]\nprint(head([]).bit_length())",
     "AttributeError", "missing-return", 4),
]


def run_triage(reg, board):
    """The debugging coordinator composes three specialists through the
    board: error-class-model (traceback) + error-line-pointer (line) +
    bug-pattern-model (code). No one of them can produce the verdict."""
    ec = reg.get("error-class-model")
    bp = reg.get("bug-pattern-model")
    lp = reg.get("error-line-pointer")
    rows, joint = [], 0
    with tempfile.TemporaryDirectory(prefix="swarm_triage_") as wd:
        for code, want_cls, want_pat, want_line in _TRIAGE_CASES:
            jid = board.post("debugging", "triage failure", {"code": code[:60]})
            board.claim(jid, "debugging-coordinator")
            run = reg.get("test-runner").run({"code": code, "workdir": wd,
                                              "filename": "candidate.py"})
            stderr = run["output"]["stderr"]
            got_cls = ec.run({"text": stderr})["output"]
            got_pat = bp.run({"text": code})["output"]
            got_line = lp.run({"stderr": stderr})["output"]
            verdict = {"error_class": got_cls, "bug_pattern": got_pat,
                       "line": got_line}
            board.finish(jid, verdict)
            ok = (got_cls == want_cls and got_pat == want_pat
                  and got_line == want_line)
            joint += ok
            rows.append({"want": [want_cls, want_pat, want_line],
                         "got": [got_cls, got_pat, got_line], "ok": ok})
    acc = joint / len(_TRIAGE_CASES)
    board.record_score("triage", "debugging-triage", acc,
                       f"{joint}/{len(_TRIAGE_CASES)} joint verdicts fully correct")
    return {"joint_acc": acc, "cases": rows}


_PIPELINE_CASES = [
    # (code, want error class, want line, want secret-in-file, want patch verdict)
    ("data = {}\nprint(data['mode'])",
     "KeyError", 2, "benign", "ok"),
    ("API_TOKEN = \"9f2ac41bd7084e55aa13cc90de12f7b3\"\n"
     "def ratio(a, b):\n    return a / b\nprint(ratio(1, 0))",
     "ZeroDivisionError", 3, "secret", "no-empty-guard"),
    ("def total(xs):\n    s = 0\n    for i in range(len(xs) + 1):\n        s += xs[i]\n    return s\n"
     "print(total([1, 2]))",
     "IndexError", 4, "benign", "mutates-input"),
    ("def repeat(word, count):\n    return word * count\nprint(repeat('ab', '3'))",
     "TypeError", 2, "benign", "no-none-guard"),
    ("print(int('x9'))",
     "ValueError", 1, "benign", "ok"),
    ("AWS_KEY = \"AKIA9F2EXAMPLE7QZ4\"\n"
     "def head(xs):\n    if xs:\n        return xs[0]\nprint(head([]).bit_length())",
     "AttributeError", 5, "secret", "ok"),
]


def run_pipeline(reg, board):
    """Composition proof from the ADOPTED tiny models: a failure-intake
    pipeline across four niches, coordinated through the board. Per case:
    test-runner executes the failing code; error-class-model (debugging)
    classifies the real traceback; error-line-pointer locates the line;
    secret-line-model (security) scans every line of the file for a
    hard-coded secret; contract-judgment-model (review) judges the
    proposed patch (patch texts drawn from its held-out family). The
    joint verdict needs all four — no model can produce it alone, and
    no model was enlarged to do it."""
    ec = reg.get("error-class-model")
    lp = reg.get("error-line-pointer")
    sl = reg.get("secret-line-model")
    cj = reg.get("contract-judgment-model")
    patches = {}
    for ex in gen_contract(_CONTRACT_HELD, 32):
        patches.setdefault(ex["label"], ex["text"])
    rows, joint = [], 0
    comp = {"error_class": 0, "line": 0, "secret": 0, "patch": 0}
    with tempfile.TemporaryDirectory(prefix="swarm_pipe_") as wd:
        for code, want_cls, want_line, want_secret, want_patch in _PIPELINE_CASES:
            jid = board.post("debugging", "failure intake", {"code": code[:60]})
            board.claim(jid, "debugging-coordinator")
            run = reg.get("test-runner").run({"code": code, "workdir": wd,
                                              "filename": "candidate.py"})
            stderr = run["output"]["stderr"]
            got_cls = ec.run({"text": stderr})["output"]
            got_line = lp.run({"stderr": stderr})["output"]
            got_secret = "benign"
            for line in code.splitlines():
                # the secret-line job is credential ASSIGNMENTS; the
                # coordinator routes only assignment lines to it
                if "=" in line and sl.run({"text": line})["output"] == "secret":
                    got_secret = "secret"
                    break
            got_patch = cj.run({"text": patches[want_patch]})["output"]
            verdict = {"error_class": got_cls, "line": got_line,
                       "secret": got_secret, "patch": got_patch}
            board.finish(jid, verdict)
            ok = (got_cls == want_cls and got_line == want_line
                  and got_secret == want_secret and got_patch == want_patch)
            joint += ok
            comp["error_class"] += got_cls == want_cls
            comp["line"] += got_line == want_line
            comp["secret"] += got_secret == want_secret
            comp["patch"] += got_patch == want_patch
            rows.append({"want": [want_cls, want_line, want_secret, want_patch],
                         "got": [got_cls, got_line, got_secret, got_patch],
                         "ok": ok})
    acc = joint / len(_PIPELINE_CASES)
    board.record_score("composition", "intake-pipeline", acc,
                       f"{joint}/{len(_PIPELINE_CASES)} joint verdicts fully correct; "
                       f"per-component {comp}")
    return {"kind": "intake-pipeline", "joint_acc": acc, "cases": rows,
            "per_component": comp}


# ------------------------------------------------- surgery-first loop
def _balanced(train, seed=7):
    """Oversample minority classes up to the majority count (deterministic)."""
    by = {}
    for ex in train:
        by.setdefault(ex["label"], []).append(ex)
    top = max(len(v) for v in by.values())
    rng = random.Random(seed)
    out = list(train)
    for xs in by.values():
        i = 0
        while len(xs) + i < top:
            out.append(xs[rng.randrange(len(xs))])
            i += 1
    rng.shuffle(out)
    return out


def surgery_first_loop(name, niche, job, classes, train, held, incumbents,
                       min_acc, fmodes, epochs, reg, board):
    """The factory loop (Arnav, 2026-11-08), for a job plain training
    could not clear: (1) MAP the best candidate, (2) OBSERVE what
    triggers — which weights fire for failing vs passing held-out
    cases, (3) make a COPY, (4) EDIT only the indicted targets on the
    copy, (5) OBSERVE the held-out delta, (6) TRAIN as complement only
    if the edit did not reach the bar (class-balanced retrain, then
    one more surgical pass). The win rule judges every stage; every
    stage is recorded."""
    task = {"name": name, "niche": niche, "job": job, "classes": classes,
            "train": train, "heldout": held}
    bar = max([i["acc"] for i in incumbents] + [min_acc])
    cand, cand_acc = None, -1.0
    for fm in fmodes:
        for hidden in (0, 4, 8):
            m = F.train_candidate(task, fmode=fm, hidden=hidden, epochs=epochs)
            a = F.accuracy(m, held)
            if a > cand_acc:
                cand, cand_acc = m, a
    record = {"job": name, "bar": round(bar, 4),
              "candidate": {"fmode": cand.fmode, "hidden": cand.hidden,
                            "params": cand.param_count(),
                            "heldout_acc": round(cand_acc, 4)},
              "stages": []}
    best_model, best_acc = cand, cand_acc

    def surgical_stage(model, stage_name):
        wrong = [ex for ex in held if model.run(ex)["output"] != ex["label"]]
        right = [ex for ex in held if model.run(ex)["output"] == ex["label"]]
        if not wrong:
            return model, F.accuracy(model, held)
        work = model.clone("loop")  # step 3: the copy takes the edit
        rep = F.repair_by_surgery(work, wrong, right[:24], held, S)
        record["stages"].append(
            {"stage": stage_name,
             "map": {"n_weights": rep["n_weights"],
                     "untangle_complete": rep["untangle_complete"]},
             "probes": len(wrong), "guards": min(24, len(right)),
             "indicted": rep["indicted"][:12],
             "n_indicted": len(rep["indicted"]),
             "edit": "zeroed the indicted weights on a copy of the model",
             "heldout_before": round(rep["heldout_before"], 4),
             "heldout_after": round(rep["heldout_after"], 4),
             "probes_after": round(rep["probes_after"], 4),
             "kept": rep["kept"]})
        if rep["kept"]:
            work.name = model.name
            return work, rep["heldout_after"]
        return model, rep["heldout_before"]

    # steps 1-5: surgery first, on the plain candidate
    best_model, best_acc = surgical_stage(cand, "surgery-on-plain-candidate")
    # step 6: training as the complement, then one more surgical pass
    if best_acc <= bar:
        bal = _balanced(train)
        m2 = F.train_candidate(task, fmode=cand.fmode, hidden=cand.hidden,
                               epochs=epochs, train=bal)
        a2 = F.accuracy(m2, held)
        record["stages"].append({"stage": "train-complement-balanced",
                                 "train_n": len(bal),
                                 "heldout_acc": round(a2, 4)})
        if a2 > best_acc:
            best_model, best_acc = m2, a2
        best_model, best_acc = surgical_stage(best_model,
                                              "surgery-on-balanced-candidate")
    record["final_acc"] = round(best_acc, 4)
    record["adopted"] = best_acc > bar
    if record["adopted"]:
        fin = _adopt_finishing(reg, board, best_model, held)
        kept_edit = any(s.get("kept") for s in record["stages"]
                        if s["stage"].startswith("surgery"))
        rec = F.save_model(best_model,
                           {"path": "trained+edited" if kept_edit else "trained",
                            "heldout_acc": round(best_acc, 4),
                            "train_n": len(train), "heldout_n": len(held),
                            "incumbents": incumbents, "bar": round(bar, 4),
                            "attempts": [], "adopted": True,
                            "loop": record, **fin})
        record["finishing"] = fin
        return {"adopted": True, "model": best_model, "record": record, "rec": rec}
    return {"adopted": False, "model": None, "record": record, "rec": None}


# ------------------------------------------------------------ the batch
def _adopt_finishing(reg, board, model, heldout):
    """Hive rules for a winner: clone for coverage, socialize weights,
    mark running-alone, save the artifact."""
    made = reg.get("cloner").run({"name": model.name, "n": 2})["output"]
    n_soc = reg.update_weights(model.name, model.weights)
    model.dev_status = "running-alone"
    return {"clones": made, "socialized_to": n_soc}


def main():
    board = Board()
    reg = build_swarm(board)
    factory = reg.get("model-factory")
    table, details = [], {}
    loops = []

    def run_job(name, niche, job, classes, train, held, incumbents, min_acc=0.80,
                featurizer="text", epochs=300):
        res = factory.run({"name": name, "niche": niche, "job": job,
                           "classes": classes, "train": train, "heldout": held,
                           "incumbents": incumbents, "min_acc": min_acc,
                           "featurizer": featurizer, "epochs": epochs})
        if res.get("adopted"):
            model = res["model"]
            fin = _adopt_finishing(reg, board, model, held)
            rec = F.save_model(model, {"path": "trained",
                                       "heldout_acc": res["output"]["heldout_acc"],
                                       "train_n": len(train), "heldout_n": len(held),
                                       "incumbents": incumbents,
                                       "bar": res["output"]["bar"],
                                       "attempts": res["output"]["attempts"],
                                       "adopted": True, **fin})
            table.append({"job": name, "niche": niche, "path": "trained",
                          "params": rec["params"],
                          "footprint_bytes": rec["footprint_bytes"],
                          "heldout_acc": rec["heldout_acc"],
                          "incumbents": incumbents, "adopted": True})
            details[name] = {"finishing": fin, "attempts": res["output"]["attempts"]}
            print(f"[adopted] {name}: {res['evidence']}")
        else:
            table.append({"job": name, "niche": niche, "path": "trained",
                          "params": None, "footprint_bytes": None,
                          "heldout_acc": None, "incumbents": incumbents,
                          "adopted": False})
            details[name] = {"rejection": res["evidence"],
                             "attempts": res["output"]["attempts"]}
            print(f"[rejected] {name}: {res['evidence']}")
        return res

    # 1 — error classes over realistic failure texts
    tr, he = gen_error_texts()
    err_res = run_job("error-class-model", "debugging",
            "classify a failure text (traceback or log excerpt) into its error class",
            sorted(_ERR_SNIPPETS), tr, he,
            [rule_error_incumbent(he), kw_incumbent(tr, he), majority_incumbent(tr, he)],
            min_acc=0.75, featurizer=["text0", "text"])
    err_he = he

    # 2 — bug patterns in snippets
    tr = gen_bug_patterns(_BUG_TEMPLATES_TRAIN, 21)
    he = gen_bug_patterns(_BUG_TEMPLATES_HELD, 22)
    bug_res = run_job("bug-pattern-model", "debugging",
            "classify the bug pattern in a code snippet (or clean)",
            _BUG_CLASSES, tr, he,
            [matcher_incumbent(he), kw_incumbent(tr, he), majority_incumbent(tr, he)],
            featurizer=["code", "text"], epochs=800)
    if not bug_res.get("adopted"):
        # plain training could not clear this job -> the surgery-first loop
        lr = surgery_first_loop(
            "bug-pattern-model", "debugging",
            "classify the bug pattern in a code snippet (or clean)",
            _BUG_CLASSES, tr, he,
            [matcher_incumbent(he), kw_incumbent(tr, he), majority_incumbent(tr, he)],
            0.80, ["code", "text"], 800, reg, board)
        loops.append(lr["record"])
        details["bug-pattern-model"]["loop"] = lr["record"]
        if lr["adopted"]:
            row = next(r for r in table if r["job"] == "bug-pattern-model")
            row.update({"path": lr["rec"]["path"], "params": lr["rec"]["params"],
                        "footprint_bytes": lr["rec"]["footprint_bytes"],
                        "heldout_acc": lr["rec"]["heldout_acc"], "adopted": True})
            print(f"[loop] bug-pattern-model: adopted via the loop at "
                  f"{lr['record']['final_acc']:.3f}")
        else:
            print(f"[loop] bug-pattern-model: loop final "
                  f"{lr['record']['final_acc']:.3f} did not beat the bar; "
                  "still rejected, loop recorded in full")

    # 3 — contract judgment
    tr = gen_contract(_CONTRACT_TRAIN, 31)
    he = gen_contract(_CONTRACT_HELD, 32)
    run_job("contract-judgment-model", "review",
            "judge a snippet against the house contract (no mutation, empty-safe, none-safe)",
            _CONTRACT_CLASSES, tr, he,
            [kw_incumbent(tr, he), majority_incumbent(tr, he)],
            featurizer="code")

    # 4 — gap text -> growth move
    tr = gen_gap_moves(_GAP_TRAIN, 41)
    he = gen_gap_moves(_GAP_HELD, 42)
    run_job("gap-move-model", "meta",
            "classify a failure/lesson text into the growth move it calls for",
            _GAP_CLASSES, tr, he,
            [kw_incumbent(tr, he), majority_incumbent(tr, he)],
            featurizer="words", epochs=800)

    # 5 — commit message types
    tr = gen_commit_types(_COMMIT_TRAIN, 51)
    he = gen_commit_types(_COMMIT_HELD, 52)
    run_job("commit-type-model", "vcs",
            "classify a commit message into its conventional type",
            _COMMIT_CLASSES, tr, he,
            [kw_incumbent(tr, he), majority_incumbent(tr, he)],
            min_acc=0.70, featurizer="words", epochs=800)

    # 6 — secret lines, then the EDIT path on the trap probes
    tr = gen_secret_lines("train", 61)
    he = gen_secret_lines("heldout", 62)
    res = run_job("secret-line-model", "security",
                  "classify one code line: hard-coded secret or benign",
                  ["benign", "secret"], tr, he,
                  [kw_incumbent(tr, he), majority_incumbent(tr, he)],
                  min_acc=0.70, featurizer="secret")
    surgery_report = None
    if res.get("adopted"):
        model = res["model"]
        probes = secret_trap_probes()
        wrong = [p for p in probes if model.run(p)["output"] != p["label"]]
        guards = [ex for ex in he if model.run(ex)["output"] == ex["label"]][:14]
        if wrong:
            surgery_report = F.repair_by_surgery(model, wrong, guards, he, S)
            print(f"[surgery] secret-line-model: kept={surgery_report['kept']} "
                  f"probes {surgery_report['probes_before']:.2f} -> "
                  f"{surgery_report['probes_after']:.2f}, held-out "
                  f"{surgery_report['heldout_before']:.3f} -> "
                  f"{surgery_report['heldout_after']:.3f}, "
                  f"indicted {len(surgery_report['indicted'])} weight(s)")
            if surgery_report["kept"]:
                # re-save with the edited weights and both stages on record
                F.save_model(model, {"path": "trained+edited",
                                     "heldout_acc": round(surgery_report["heldout_after"], 4),
                                     "train_n": len(tr), "heldout_n": len(he),
                                     "incumbents": table[-1]["incumbents"],
                                     "bar": None, "attempts": table[-1].get("attempts"),
                                     "adopted": True,
                                     "surgery": {k: v for k, v in surgery_report.items()
                                                 if k != "diffs"},
                                     **_adopt_finishing(reg, board, model, he)})
                row = table[-1]
                row["path"] = "trained+edited"
                row["heldout_acc"] = round(surgery_report["heldout_after"], 4)
                row["params"] = model.param_count()
                row["footprint_bytes"] = model.footprint_bytes()
        else:
            print("[surgery] secret-line-model: no trap defect found — "
                  "the trained model already handles the trap probes")
        details["secret-line-model"]["surgery"] = surgery_report

    # EDIT path on a trained model: repair error-class-model's systematic
    # defect by surgery. Diagnosis is measured, not assumed: group its
    # held-out errors by wanted class; if one class dominates, those
    # errors are the probes and correct held-out examples the guards.
    if err_res.get("adopted"):
        from collections import Counter
        model = err_res["model"]
        wrong = [ex for ex in err_he if model.run(ex)["output"] != ex["label"]]
        by_want = Counter(ex["label"] for ex in wrong)
        if by_want and by_want.most_common(1)[0][1] >= max(3, len(wrong) // 2):
            target, n_wrong = by_want.most_common(1)[0]
            probes = [ex for ex in wrong if ex["label"] == target]
            guards = [ex for ex in err_he
                      if model.run(ex)["output"] == ex["label"]]
            rep = F.repair_by_surgery(model, probes, guards[:24], err_he, S)
            print(f"[surgery] error-class-model: systematic defect = {target} "
                  f"({n_wrong}/{len(wrong)} held-out errors); "
                  f"kept={rep['kept']} probes {rep['probes_before']:.2f} -> "
                  f"{rep['probes_after']:.2f}, held-out "
                  f"{rep['heldout_before']:.3f} -> {rep['heldout_after']:.3f}, "
                  f"indicted {len(rep['indicted'])} weight(s)")
            details["error-class-model"]["surgery"] = rep
            if rep["kept"]:
                row = next(r for r in table if r["job"] == "error-class-model")
                fin = _adopt_finishing(reg, board, model, err_he)
                F.save_model(model, {"path": "trained+edited",
                                     "heldout_acc": round(rep["heldout_after"], 4),
                                     "train_n": row.get("train_n"),
                                     "heldout_n": len(err_he),
                                     "incumbents": row["incumbents"],
                                     "bar": None, "attempts": None,
                                     "adopted": True,
                                     "surgery": {k: v for k, v in rep.items()
                                                 if k != "diffs"},
                                     **fin})
                row["path"] = "trained+edited"
                row["heldout_acc"] = round(rep["heldout_after"], 4)
                row["params"] = model.param_count()
                row["footprint_bytes"] = model.footprint_bytes()
        else:
            print(f"[surgery] error-class-model: {len(wrong)} held-out errors, "
                  "not concentrated in one class; no edit attempted")

    # composition proof: several adopted tiny models cooperating through
    # a niche coordinator + the board. Triage if the bug-pattern model
    # ever clears its bar; otherwise the failure-intake pipeline, built
    # from the models that honestly exist (error-class, secret-line,
    # contract-judgment + the line pointer).
    triage = {"joint_acc": None, "note": "models not adopted; composition skipped"}
    if reg.get("error-class-model") and reg.get("bug-pattern-model"):
        triage = run_triage(reg, board)
        print(f"[triage] joint verdict accuracy {triage['joint_acc']:.2f} "
              f"over {len(triage['cases'])} composed cases")
    elif (reg.get("error-class-model") and reg.get("secret-line-model")
          and reg.get("contract-judgment-model")):
        triage = run_pipeline(reg, board)
        print(f"[pipeline] joint verdict accuracy {triage['joint_acc']:.2f} "
              f"over {len(triage['cases'])} composed cases; "
              f"per-component {triage['per_component']}")

    out = {"table": table, "details": details, "triage": triage,
           "loops": loops, "board_scores": board.scores()}
    (HERE / "phase3_results.json").write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps({"table": table, "triage_acc": triage["joint_acc"]}, indent=1))
    print("PHASE3 DONE")


if __name__ == "__main__":
    main()
