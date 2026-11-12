"""Dream generators for bug-pattern (Phase C): parameterized code
families across three difficulty bands, execution-verified.

A dreamed case is born as a FAMILY: a correct function plus, per
defect class, a mutated variant produced by a named mutation
operator. Labels are true by construction AND verified by execution
before any item may be trained on:

  * the correct code must run cleanly on every probe input;
  * the buggy code's behavioral signature (outputs, or the exception
    type, across probes — for mutable-default, across repeated calls)
    must DIFFER from the correct code's on at least one probe;
  * a missing-return variant must actually return None where the
    correct code returns a value.

A mutation that changes nothing observable is not a bug example — it
is discarded and counted (unverifiable dreams are never trained on).
Every kept case is stored in TWO views (good views): the original
surface and an identifier-renamed surface, itself execution-verified
to behave identically.

Bands (structural difficulty):
  1 — single-expression / two-line functions;
  2 — one loop or comprehension, accumulator patterns;
  3 — guards, multiple statements, distractors, default-arg state.

Families are parameterized (names, operators, constants, operand
order), so train / screen / probe pools draw disjoint parameter
combinations from the same structures, and screen/probe-only
skeletons keep the pools structurally honest where it is cheap.
"""
from __future__ import annotations

import ast
import contextlib
import io
import random
import tokenize
from typing import Any, Callable, Dict, List, Optional, Tuple

BANDS = (1, 2, 3)
CLASSES = ["off-by-one", "wrong-operator", "swapped-operands",
           "mutable-default", "missing-return"]

_FN_NAMES = ["tally", "blend", "pick", "shift", "weigh", "fold", "trim",
             "mesh", "tally_up", "work_out", "run_through", "gather_in"]
_VARS = ["xs", "ys", "vals", "items", "nums", "data", "rows", "pool"]
_SCALARS = ["a", "b", "p", "q", "m", "n", "k", "f", "v", "w"]


# ------------------------------------------------------------ execution
_ALLOWED_BUILTINS = {k: getattr(__builtins__, k) if not isinstance(
    __builtins__, dict) else __builtins__[k]
    for k in ("range", "len", "min", "max", "sum", "abs", "print",
              "list", "dict", "set", "sorted", "enumerate", "zip",
              "int", "float", "bool")}


def _load_fn(code: str):
    tree = ast.parse(code)
    fn = next((n.name for n in tree.body
               if isinstance(n, ast.FunctionDef)), None)
    if fn is None:
        return None
    ns: Dict[str, Any] = {"__builtins__": dict(_ALLOWED_BUILTINS)}
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(tree, "<dream>", "exec"), ns)
    return ns.get(fn)


def _signature(code: str, probes: List[Tuple],
               repeat_probe: Optional[Tuple] = None):
    """Behavioral signature: per probe, ('ok', repr(out)) or
    ('exc', ExceptionType). For mutable-default families a second
    call with default arguments is appended (repeat_probe) —
    pollution across calls is the bug's observable signature: the
    correct code returns a fresh one-item list, the buggy one
    returns the first call's item as well."""
    fn = _load_fn(code)
    if fn is None:
        return None
    sig = []
    with contextlib.redirect_stdout(io.StringIO()):
        calls = list(probes) + ([repeat_probe] if repeat_probe else [])
        for args in calls:
            try:
                out = fn(*[list(a) if isinstance(a, list) else a
                           for a in args])
                sig.append(("ok", repr(out)))
            except Exception as exc:  # noqa: BLE001 - signature, not a failure
                sig.append(("exc", type(exc).__name__))
    return sig


def verify_family(fam: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """Execution checker. Returns {variant_key: keep/drop reason} —
    'correct' must verify; each mutation must be observably different
    from correct. Anything else is dropped, never trained on."""
    probes = fam["probes"]
    repeat = fam.get("repeat_probe")
    verdicts: Dict[str, Optional[str]] = {}
    csig = _signature(fam["correct"], probes, repeat)
    if csig is None or any(s[0] == "exc" for s in csig):
        return {"correct": "correct code does not run cleanly on probes"}
    verdicts["correct"] = None
    for cls, buggy in fam["mutations"].items():
        bsig = _signature(buggy, probes, repeat)
        if bsig is None:
            verdicts[cls] = "buggy code does not parse/load"
        elif bsig == csig:
            verdicts[cls] = "mutation is behaviorally identical on probes"
        elif cls == "missing-return" and not any(
                b == ("ok", "None") and c[0] == "ok" and c[1] != "None"
                for b, c in zip(bsig, csig)):
            verdicts[cls] = "variant does not actually drop the return value"
        else:
            verdicts[cls] = None
    return verdicts


# ------------------------------------------------------------ second view
def renamed_view(code: str) -> Optional[str]:
    """The good-view transform: rename the function and its local
    identifiers (never keywords, builtins, or attribute names). The
    result is execution-verified by the caller before use."""
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(code).readline))
    except Exception:
        return None
    tree = ast.parse(code)
    fn = next((n for n in tree.body if isinstance(n, ast.FunctionDef)), None)
    if fn is None:
        return None
    locals_ = {fn.name} | {a.arg for a in fn.args.args}
    for node in ast.walk(fn):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            locals_.add(node.id)
    mapping = {}
    fresh = iter(["alpha", "beta", "gamma", "delta", "omega", "kappa",
                  "sigma", "theta", "lambda_", "zeta", "nova", "onyx",
                  "pixel", "quartz", "vertex", "willow"])
    for name in sorted(locals_):
        try:
            mapping[name] = next(fresh)
        except StopIteration:
            return None
    out, prev = [], None
    try:
        for tok in toks:
            if (tok.type == tokenize.NAME and tok.string in mapping
                    and not (prev is not None and prev.string == ".")):
                out.append((tok.type, mapping[tok.string]))
            else:
                out.append((tok.type, tok.string))
            prev = tok
        return tokenize.untokenize(out)
    except Exception:
        return None


# ------------------------------------------------------------ families
# Each builder returns a family dict:
#   {band, family, correct, mutations{cls: code}, probes, repeat_calls}
def _fam(band, name, correct, mutations, probes, repeat_probe=None):
    return {"band": band, "family": name, "correct": correct,
            "mutations": mutations, "probes": probes,
            "repeat_probe": repeat_probe}


def _band1(rng: random.Random) -> Dict[str, Any]:
    fn = rng.choice(_FN_NAMES)
    kind = rng.choice(["arith", "lastidx", "scale", "ratio", "clamp",
                       "slice_head", "absdiff", "weighted", "nestedexpr"])
    a, b = rng.sample(_SCALARS, 2)
    xs = rng.choice(_VARS)
    if kind == "absdiff":
        correct = f"def {fn}({a}, {b}):\n    return {a} - {b} if {a} >= {b} else {b} - {a}"
        mut = {"swapped-operands": f"def {fn}({a}, {b}):\n    return {b} - {a} if {a} >= {b} else {a} - {b}",
               "wrong-operator": f"def {fn}({a}, {b}):\n    return {a} + {b} if {a} >= {b} else {b} - {a}"}
        probes = [(9, 4), (3, 8), (6, 6), (12, 5)]
        return _fam(1, "b1-absdiff", correct, mut, probes)
    if kind == "weighted":
        correct = f"def {fn}({a}, {b}):\n    return {a} * 2 - {b}"
        mut = {"swapped-operands": f"def {fn}({a}, {b}):\n    return {b} * 2 - {a}",
               "wrong-operator": f"def {fn}({a}, {b}):\n    return {a} * 2 + {b}"}
        probes = [(5, 3), (4, 9), (7, 7)]
        return _fam(1, "b1-weighted", correct, mut, probes)
    if kind == "nestedexpr":
        correct = f"def {fn}({a}, {b}):\n    return ({a} - {b}) * ({a} + {b})"
        mut = {"swapped-operands": f"def {fn}({a}, {b}):\n    return ({b} - {a}) * ({b} + {a})",
               "wrong-operator": f"def {fn}({a}, {b}):\n    return ({a} - {b}) + ({a} + {b})"}
        probes = [(6, 2), (3, 5), (9, 9)]
        return _fam(1, "b1-nestedexpr", correct, mut, probes)
    if kind == "arith":
        op, alt = rng.choice([("-", "+"), ("/", "*"), ("%", "-"),
                              ("//", "%")])
        correct = f"def {fn}({a}, {b}):\n    return {a} {op} {b}"
        mut = {"swapped-operands": f"def {fn}({a}, {b}):\n    return {b} {op} {a}",
               "wrong-operator": f"def {fn}({a}, {b}):\n    return {a} {alt} {b}"}
        probes = [(7, 3), (10, 4), (5, 5), (12, 7)]
        return _fam(1, f"b1-arith-{op}", correct, mut, probes)
    if kind == "lastidx":
        correct = f"def {fn}({xs}):\n    return {xs}[len({xs}) - 1]"
        mut = {"off-by-one": f"def {fn}({xs}):\n    return {xs}[len({xs})]"}
        probes = [([4, 9, 2],), ([7],), ([3, 1, 8, 5],)]
        return _fam(1, "b1-lastidx", correct, mut, probes)
    if kind == "scale":
        f = rng.choice([s for s in _SCALARS if s not in (a, b)])
        correct = f"def {fn}({xs}, {f}):\n    return [x * {f} for x in {xs}]"
        mut = {"wrong-operator": f"def {fn}({xs}, {f}):\n    return [x + {f} for x in {xs}]",
               "missing-return": f"def {fn}({xs}, {f}):\n    out = [x * {f} for x in {xs}]"}
        probes = [([1, 2, 3], 10), ([5], 3), ([], 7)]
        return _fam(1, "b1-scale", correct, mut, probes)
    if kind == "ratio":
        correct = f"def {fn}({a}, {b}):\n    return {a} / {b} * 100"
        mut = {"swapped-operands": f"def {fn}({a}, {b}):\n    return {b} / {a} * 100",
               "wrong-operator": f"def {fn}({a}, {b}):\n    return {a} * {b} * 100"}
        probes = [(1, 4), (3, 8), (50, 200)]
        return _fam(1, "b1-ratio", correct, mut, probes)
    if kind == "clamp":
        v, lo, hi = rng.sample(_SCALARS, 3)
        correct = f"def {fn}({v}, {lo}, {hi}):\n    return max({lo}, min({hi}, {v}))"
        mut = {"swapped-operands": f"def {fn}({v}, {lo}, {hi}):\n    return max({hi}, min({lo}, {v}))",
               "missing-return": f"def {fn}({v}, {lo}, {hi}):\n    res = max({lo}, min({hi}, {v}))"}
        probes = [(5, 1, 10), (0, 2, 9), (99, 3, 40)]
        return _fam(1, "b1-clamp", correct, mut, probes)
    k = rng.choice([s for s in _SCALARS if s not in (a, b)])
    correct = f"def {fn}({xs}, {k}):\n    return {xs}[:{k}]"
    mut = {"off-by-one": f"def {fn}({xs}, {k}):\n    return {xs}[:{k} + 1]"}
    probes = [([9, 8, 7, 6], 2), ([1, 2], 1), ([5, 4, 3], 3)]
    return _fam(1, "b1-slice", correct, mut, probes)


def _band2(rng: random.Random) -> Dict[str, Any]:
    fn = rng.choice(_FN_NAMES)
    kind = rng.choice(["sumrange", "countmatch", "accum", "zipdiff",
                       "countdown", "prefixsum"])
    xs = rng.choice(_VARS)
    n = rng.choice([s for s in _SCALARS])
    if kind == "sumrange":
        correct = (f"def {fn}({n}):\n    s = 0\n"
                   f"    for i in range(1, {n} + 1):\n        s += i\n"
                   f"    return s")
        mut = {"off-by-one": correct.replace(f"range(1, {n} + 1)",
                                             f"range(1, {n})"),
               "wrong-operator": correct.replace("s += i", "s -= i"),
               "missing-return": correct.replace("return s", "print(s)")}
        return _fam(2, "b2-sumrange", correct, mut, [(4,), (7,), (1,)])
    if kind == "countmatch":
        v = rng.choice([s for s in _SCALARS if s != n])
        correct = (f"def {fn}({xs}, {v}):\n    c = 0\n"
                   f"    for x in {xs}:\n        if x == {v}:\n"
                   f"            c += 1\n    return c")
        mut = {"wrong-operator": correct.replace("x == ", "x != "),
               "missing-return": correct.replace("return c", "print(c)")}
        probes = [([2, 5, 2, 9], 2), ([1, 1], 3), ([], 4)]
        return _fam(2, "b2-countmatch", correct, mut, probes)
    if kind == "accum":
        correct = (f"def {fn}({xs}):\n    s = 0\n"
                   f"    for i in range(len({xs})):\n        s += {xs}[i]\n"
                   f"    return s")
        mut = {"off-by-one": correct.replace(f"range(len({xs}))",
                                             f"range(len({xs}) - 1)"),
               "wrong-operator": correct.replace("s += ", "s -= ")}
        probes = [([3, 4, 5],), ([10],), ([1, 2],)]
        return _fam(2, "b2-accum", correct, mut, probes)
    if kind == "zipdiff":
        ys = rng.choice([v for v in _VARS if v != xs])
        correct = f"def {fn}({xs}, {ys}):\n    return [x - y for x, y in zip({xs}, {ys})]"
        mut = {"swapped-operands": f"def {fn}({xs}, {ys}):\n    return [y - x for x, y in zip({xs}, {ys})]",
               "wrong-operator": f"def {fn}({xs}, {ys}):\n    return [x + y for x, y in zip({xs}, {ys})]"}
        probes = [([9, 5], [1, 2]), ([10], [3]), ([4, 4, 4], [1, 1, 1])]
        return _fam(2, "b2-zipdiff", correct, mut, probes)
    if kind == "countdown":
        correct = (f"def {fn}({n}):\n    c = 0\n    i = {n}\n"
                   f"    while i > 0:\n        c += 1\n        i -= 1\n"
                   f"    return c")
        mut = {"off-by-one": correct.replace("while i > 0:", "while i > 1:"),
               "wrong-operator": correct.replace("c += 1", "c -= 1")}
        return _fam(2, "b2-countdown", correct, mut, [(5,), (3,), (8,)])
    correct = (f"def {fn}({xs}):\n    out = []\n    s = 0\n"
               f"    for x in {xs}:\n        s += x\n        out.append(s)\n"
               f"    return out")
    mut = {"wrong-operator": correct.replace("s += x", "s -= x"),
           "missing-return": correct.replace("return out", "total = out")}
    probes = [([1, 2, 3],), ([5, 5],), ([9],)]
    return _fam(2, "b2-prefix", correct, mut, probes)


def _band3(rng: random.Random) -> Dict[str, Any]:
    fn = rng.choice(_FN_NAMES)
    kind = rng.choice(["guarded", "defaultarg", "nested", "safediv",
                       "window"])
    xs = rng.choice(_VARS)
    if kind == "guarded":
        lim = rng.choice(_SCALARS)
        correct = (f"def {fn}({xs}, {lim}):\n    s = 0\n"
                   f"    for x in {xs}:\n        if x > {lim}:\n"
                   f"            s += x\n    note = len({xs})\n"
                   f"    return s")
        mut = {"wrong-operator": correct.replace("if x > ", "if x < "),
               "off-by-one": correct.replace("s += x\n", "s += x + 1\n"),
               "missing-return": correct.replace("return s", "result = s")}
        probes = [([1, 9, 3, 8], 5), ([2, 2], 4), ([10, 20], 3)]
        return _fam(3, "b3-guarded", correct, mut, probes)
    if kind == "defaultarg":
        item = rng.choice(_SCALARS)
        correct = (f"def {fn}({item}, acc=None):\n"
                   f"    acc = [] if acc is None else list(acc)\n"
                   f"    acc.append({item})\n    return acc")
        mut = {"mutable-default": (f"def {fn}({item}, acc=[]):\n"
                                   f"    acc.append({item})\n"
                                   f"    return acc")}
        return _fam(3, "b3-defaultarg", correct, mut, [("x",)],
                    repeat_probe=("y",))
    if kind == "nested":
        correct = (f"def {fn}({xs}):\n    total = 0\n"
                   f"    for row in {xs}:\n        for v in row:\n"
                   f"            if v % 2 == 0:\n                total += v\n"
                   f"    return total")
        mut = {"wrong-operator": correct.replace("v % 2 == 0", "v % 2 != 0"),
               "off-by-one": correct.replace("total += v", "total += v - 1")}
        probes = [([[1, 2], [3, 4]],), ([[6]],), ([[2, 8], [5]],)]
        return _fam(3, "b3-nested", correct, mut, probes)
    if kind == "safediv":
        a, b = rng.sample(_SCALARS, 2)
        correct = (f"def {fn}({a}, {b}):\n    if {b} == 0:\n"
                   f"        return 0\n    return {a} / {b}")
        mut = {"swapped-operands": (f"def {fn}({a}, {b}):\n"
                                    f"    if {b} == 0:\n        return 0\n"
                                    f"    return {b} / {a}"),
               "wrong-operator": correct.replace(f"{a} / {b}", f"{a} * {b}")}
        probes = [(10, 2), (9, 3), (5, 0)]
        return _fam(3, "b3-safediv", correct, mut, probes)
    k = rng.choice(_SCALARS)
    correct = (f"def {fn}({xs}, {k}):\n    s = 0\n"
               f"    for i in range({k}):\n        s += {xs}[i]\n"
               f"    return s")
    mut = {"off-by-one": correct.replace(f"range({k})", f"range({k} + 1)"),
           "wrong-operator": correct.replace("s += ", "s -= ")}
    probes = [([4, 2, 9, 1], 3), ([7, 7], 2), ([1, 2, 3], 3)]
    return _fam(3, "b3-window", correct, mut, probes)


_BUILDERS = {1: _band1, 2: _band2, 3: _band3}


def gen_families(band: int, count: int, seed: int) -> List[Dict[str, Any]]:
    rng = random.Random(seed + band * 100003)
    return [_BUILDERS[band](rng) for _ in range(count)]


def family_items(fam: Dict[str, Any], group_prefix: str,
                 with_views: bool = True) -> Tuple[List[Dict[str, Any]],
                                                    Dict[str, int]]:
    """Verified items from one family: the clean case + each verified
    mutation, each in two views when the renamed view also verifies.
    Returns (items, drop_counts). Items carry group/band/family so
    the difficulty filter keeps a case with its second view."""
    verdicts = verify_family(fam)
    drops: Dict[str, int] = {}
    items: List[Dict[str, Any]] = []
    if verdicts.get("correct") is not None:
        return [], {"family_dropped": 1}
    variants = [("clean", fam["correct"])]
    for cls, buggy in fam["mutations"].items():
        if verdicts.get(cls) is None:
            variants.append((cls, buggy))
        else:
            drops[f"mutation_{cls}"] = drops.get(f"mutation_{cls}", 0) + 1
    probes, repeat = fam["probes"], fam.get("repeat_probe")
    base_sig = _signature(fam["correct"], probes, repeat)
    for label, code in variants:
        gid = f"{group_prefix}:{fam['family']}:{label}"
        items.append({"text": code, "label": label, "group": gid,
                      "band": fam["band"], "family": fam["family"]})
        if with_views:
            view = renamed_view(code)
            if view is not None and view != code:
                vsig = _signature(view, probes, repeat)
                # the view of the CORRECT code must behave identically;
                # a mutation's view must differ from correct exactly
                # as the original does
                if label == "clean" and vsig == base_sig:
                    items.append({"text": view, "label": label,
                                  "group": gid, "band": fam["band"],
                                  "family": fam["family"], "view": 2})
                elif label != "clean" and vsig is not None \
                        and vsig != base_sig:
                    items.append({"text": view, "label": label,
                                  "group": gid, "band": fam["band"],
                                  "family": fam["family"], "view": 2})
                else:
                    drops["view_failed_verify"] = \
                        drops.get("view_failed_verify", 0) + 1
    return items, drops


def gen_pool(band_counts: Dict[int, int], seed: int,
             group_prefix: str) -> Tuple[List[Dict[str, Any]],
                                          Dict[str, Any]]:
    """Generate a verified multi-class dream pool. Returns (items,
    stats) — stats record what the checker discarded and why."""
    items: List[Dict[str, Any]] = []
    stats: Dict[str, Any] = {"families": 0, "drops": {}}
    for band, count in band_counts.items():
        for fam in gen_families(band, count, seed):
            stats["families"] += 1
            fams_items, drops = family_items(fam, group_prefix)
            items.extend(fams_items)
            for k, v in drops.items():
                stats["drops"][k] = stats["drops"].get(k, 0) + v
    stats["items"] = len(items)
    return items, stats


# ------------------------------------------------------------ screen-only
# Screen families are STRUCTURALLY distinct from the training
# families (different idioms: temp vars, enumerate, built-in sum,
# try/except, dict accumulation, break-search) so the screen measures
# generalization to new structures, not new parameters of trained
# structures. They are never trained on.
def _screen1(rng: random.Random) -> Dict[str, Any]:
    fn = rng.choice(_FN_NAMES)
    kind = rng.choice(["tempvar", "firstlast", "negidx"])
    a, b = rng.sample(_SCALARS, 2)
    xs = rng.choice(_VARS)
    if kind == "tempvar":
        correct = (f"def {fn}({a}, {b}):\n    t = {a} - {b}\n"
                   f"    return t * {b}")
        mut = {"swapped-operands": (f"def {fn}({a}, {b}):\n"
                                    f"    t = {b} - {a}\n"
                                    f"    return t * {b}"),
               "wrong-operator": (f"def {fn}({a}, {b}):\n"
                                  f"    t = {a} - {b}\n"
                                  f"    return t + {b}")}
        return _fam(1, "s1-tempvar", correct, mut, [(7, 3), (4, 9), (6, 6)])
    if kind == "firstlast":
        correct = f"def {fn}({xs}):\n    return {xs}[0] - {xs}[len({xs}) - 1]"
        mut = {"off-by-one": f"def {fn}({xs}):\n    return {xs}[0] - {xs}[len({xs})]",
               "wrong-operator": f"def {fn}({xs}):\n    return {xs}[0] + {xs}[len({xs}) - 1]"}
        return _fam(1, "s1-firstlast", correct, mut,
                    [([9, 1, 4],), ([5, 5],), ([8, 2, 7, 3],)])
    correct = f"def {fn}({xs}):\n    return {xs}[-1] * 2"
    mut = {"off-by-one": f"def {fn}({xs}):\n    return {xs}[-2] * 2"}
    return _fam(1, "s1-negidx", correct, mut,
                [([3, 8],), ([1, 4, 9],), ([7, 7, 2],)])


def _screen2(rng: random.Random) -> Dict[str, Any]:
    fn = rng.choice(_FN_NAMES)
    kind = rng.choice(["enumw", "sumtail", "revcount"])
    xs = rng.choice(_VARS)
    if kind == "enumw":
        correct = (f"def {fn}({xs}):\n    s = 0\n"
                   f"    for i, x in enumerate({xs}):\n"
                   f"        s += x * i\n    return s")
        mut = {"wrong-operator": correct.replace("s += x * i",
                                                 "s += x + i"),
               "off-by-one": correct.replace("enumerate(",
                                             "enumerate(").replace(
                                                 f"enumerate({xs})",
                                                 f"enumerate({xs}, 1)")}
        return _fam(2, "s2-enumw", correct, mut,
                    [([5, 5, 5],), ([2, 9],), ([1, 2, 3, 4],)])
    if kind == "sumtail":
        correct = f"def {fn}({xs}):\n    return sum({xs}[1:])"
        mut = {"off-by-one": f"def {fn}({xs}):\n    return sum({xs}[2:])",
               "missing-return": f"def {fn}({xs}):\n    t = sum({xs}[1:])"}
        return _fam(2, "s2-sumtail", correct, mut,
                    [([4, 1, 9],), ([7, 3],), ([2, 2, 2, 2],)])
    v = rng.choice(_SCALARS)
    correct = (f"def {fn}({xs}, {v}):\n    c = 0\n"
               f"    for x in reversed({xs}):\n        if x == {v}:\n"
               f"            c += 1\n    return c")
    mut = {"wrong-operator": correct.replace("x == ", "x != ")}
    return _fam(2, "s2-revcount", correct, mut,
                [([1, 2, 1], 1), ([5], 5), ([3, 3, 3], 2)])


def _screen3(rng: random.Random) -> Dict[str, Any]:
    fn = rng.choice(_FN_NAMES)
    kind = rng.choice(["tryidx", "dictcount", "whilebreak"])
    xs = rng.choice(_VARS)
    if kind == "tryidx":
        i = rng.choice(_SCALARS)
        correct = (f"def {fn}({xs}, {i}):\n    try:\n"
                   f"        return {xs}[{i}]\n"
                   f"    except IndexError:\n        return -1")
        mut = {"off-by-one": correct.replace(f"return {xs}[{i}]",
                                             f"return {xs}[{i} + 1]"),
               "missing-return": (f"def {fn}({xs}, {i}):\n    try:\n"
                                  f"        val = {xs}[{i}]\n"
                                  f"    except IndexError:\n"
                                  f"        return -1")}
        return _fam(3, "s3-tryidx", correct, mut,
                    [([10, 20, 30], 1), ([5, 6], 0), ([9], 5)])
    if kind == "dictcount":
        correct = (f"def {fn}({xs}):\n    seen = {{}}\n"
                   f"    for x in {xs}:\n"
                   f"        seen[x] = seen.get(x, 0) + 1\n"
                   f"    return seen")
        mut = {"wrong-operator": correct.replace("seen.get(x, 0) + 1",
                                                 "seen.get(x, 0) - 1"),
               "off-by-one": correct.replace("seen.get(x, 0) + 1",
                                             "seen.get(x, 1) + 1")}
        return _fam(3, "s3-dictcount", correct, mut,
                    [([1, 2, 1],), ([5, 5, 5],), ([9],)])
    v = rng.choice(_SCALARS)
    correct = (f"def {fn}({xs}, {v}):\n    i = 0\n"
               f"    while i < len({xs}):\n        if {xs}[i] == {v}:\n"
               f"            break\n        i += 1\n    return i")
    mut = {"off-by-one": correct.replace(f"while i < len({xs}):",
                                         f"while i < len({xs}) - 1:"),
           "wrong-operator": correct.replace(f"{xs}[i] == {v}",
                                             f"{xs}[i] != {v}")}
    return _fam(3, "s3-whilebreak", correct, mut,
                [([4, 7, 9], 9), ([1, 2], 5), ([8, 8, 3], 3)])


_SCREEN_BUILDERS = {1: _screen1, 2: _screen2, 3: _screen3}


def gen_screen_pool(band_counts: Dict[int, int], seed: int,
                    group_prefix: str = "screen"
                    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    stats: Dict[str, Any] = {"families": 0, "drops": {}}
    for band, count in band_counts.items():
        rng = random.Random(seed + band * 777001)
        for _ in range(count):
            fam = _SCREEN_BUILDERS[band](rng)
            stats["families"] += 1
            fams_items, drops = family_items(fam, group_prefix)
            items.extend(fams_items)
            for k, v in drops.items():
                stats["drops"][k] = stats["drops"].get(k, 0) + v
    stats["items"] = len(items)
    return items, stats
