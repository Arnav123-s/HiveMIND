"""The NAME-INTENT data family (growth cycle 1, Lever 1).

A new generator class for the factory. Every other data supply in
this lab labels by EXECUTION: a family's correct and mutated
versions are proved apart by behavioral probes (dream_gen.py).
That construction cannot express one real signal — INTENT DECLARED
BY THE FUNCTION'S NAME. `def remainder(a, b): return a - b` is a
perfectly good subtraction; it is a wrong-operator defect only
because the name declares remainder. The assembly growth runs
(ASSEMBLY.md Item 3) measured the floor exactly: the stubborn
held items all live on this axis, and scaling execution-verified
data made children WORSE (0.85 -> 0.80 -> 0.65) because the supply
cannot carry the signal at any scale.

This family's labels come from CONSTRUCTION, not execution:

  * an intent spec declares what a name promises (remainder -> %,
    first_two -> elements [0] and [1], last -> index len-1, ...);
  * the generator emits the body that KEEPS the promise (label
    clean) and bodies that BREAK it while remaining valid,
    runnable code (label = the defect class of the break:
    wrong-operator / swapped-operands / off-by-one);
  * CONTROLS are woven through every family so the agreement
    itself is the signal, never the name or the body alone:
      - the same body under a name whose intent it SATISFIES is
        clean (a - b under `difference` is correct code);
      - the correct body under its own name is clean (names do
        not always lie);
      - a canonical body under a NEUTRAL name (compute, calc) is
        clean (no promise was made, none was broken);
      - a structural defect (xs[len(xs)]) is labelled by its
        class under ANY name — position contracts in this lab's
        task construction are name-independent (dream_gen does
        the same under random names).

Held-out pristinity: the held partition uses function names,
variable names and body idioms DISJOINT from the training
partition, and both partitions are contamination-filtered against
every existing corpus (phase-3 train/held templates, the swarm
dream corpus, the factory dream pool, the sealed v2 set, the
acceptance battery items) with the factory's own filter before
they are written. The held file is a judge surface: the growth
runner loads it only in the judge step and filters every training
pool against it.

An execution SANITY pass (not a label check — name-intent labels
are not execution-provable, that is the point) drops degenerate
items: a correct body that raises on its probes, or a mutation
that is behaviorally identical to the correct body on every probe
(a no-op "mutation", e.g. swapping the operands of +). Drops are
counted in the manifest.
"""
from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

LAB_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(LAB_ROOT / "coding"))
sys.path.insert(0, str(LAB_ROOT))

GROWTH_DIR = LAB_ROOT / "growth"
DATA_DIR = GROWTH_DIR / "data"

NEUTRAL_NAMES = ["compute", "calc", "do_op", "apply_it", "process_vals",
                 "run_it", "handle", "work_out"]


# ------------------------------------------------------------ execution
def _load_fn(code: str):
    ns: Dict[str, Any] = {}
    try:
        exec(compile(code, "<intent>", "exec"), ns)  # noqa: S102
    except Exception:  # noqa: BLE001
        return None
    for v in ns.values():
        if callable(v):
            return v
    return None


def _probe_out(fn, args) -> Tuple[str, Any]:
    try:
        return ("ok", fn(*[list(a) if isinstance(a, list) else a
                           for a in args]))
    except IndexError:
        return ("index-error", None)
    except Exception:  # noqa: BLE001
        return ("error", None)


def _distinguishes(correct_code: str, mut_code: str,
                   probes: List[Tuple]) -> bool:
    """True when the mutation's behaviour differs from correct on at
    least one probe (IndexError counts as differing behaviour for
    index families — it IS the defect surfacing)."""
    fc, fm = _load_fn(correct_code), _load_fn(mut_code)
    if fc is None or fm is None:
        return False
    for args in probes:
        if _probe_out(fc, args) != _probe_out(fm, args):
            return True
    return False


def _runs_clean(code: str, probes: List[Tuple]) -> bool:
    fn = _load_fn(code)
    if fn is None:
        return False
    return all(_probe_out(fn, a)[0] == "ok" for a in probes)


# ------------------------------------------------------------ idioms
def _body(expr: str, idiom: str, ret_var: str = "res") -> str:
    """Body lines with RELATIVE indentation only — _fn adds the
    function-level 4 spaces to every line."""
    if idiom == "direct":
        return f"return {expr}"
    if idiom == "temp":
        return f"{ret_var} = {expr}\nreturn {ret_var}"
    if idiom == "guard_temp":
        return (f"{ret_var} = {expr}\nif {ret_var} is None:\n"
                f"    return {ret_var}\nreturn {ret_var}")
    raise ValueError(idiom)


def _fn(name: str, params: str, body_lines: str) -> str:
    indented = "\n".join("    " + ln if ln.strip() else ln
                         for ln in body_lines.split("\n"))
    return f"def {name}({params}):\n{indented}"


# ------------------------------------------------------------ binary-op
# Each op: (expression in terms of A and B, defect class when it
# replaces the intended op). Swapped variants are generated from
# the intended op's own expression with operands exchanged.
_BIN_OPS = {
    "mod":      ("{A} % {B}", "wrong-operator"),
    "floordiv": ("{A} // {B}", "wrong-operator"),
    "sub":      ("{A} - {B}", "wrong-operator"),
    "add":      ("{A} + {B}", "wrong-operator"),
    "mul":      ("{A} * {B}", "wrong-operator"),
    "div":      ("{A} / {B}", "wrong-operator"),
}

# intent id -> (intended op, wrong-op alternatives, name partitions,
#               extra fixed expression templates)
_BIN_INTENTS: List[Dict[str, Any]] = [
    {"id": "remainder", "op": "mod",
     "alts": ["sub", "floordiv", "add"],
     "names_train": ["remainder", "rem", "modulus", "remainder_of"],
     "names_held": ["modulo", "left_over", "whats_left", "rem_after_div"]},
    {"id": "quotient", "op": "floordiv",
     "alts": ["mod", "sub"],
     "names_train": ["quotient", "div_result", "whole_part"],
     "names_held": ["how_many_times", "full_div", "div_share"]},
    {"id": "difference", "op": "sub",
     "alts": ["add", "mod"],
     "names_train": ["difference", "subtract", "minus_vals", "diff_of"],
     "names_held": ["take_away", "subtraction_result", "gap_between"]},
    {"id": "product", "op": "mul",
     "alts": ["add", "sub"],
     "names_train": ["product_of", "times_vals", "multiply_pair"],
     "names_held": ["prod_pair", "scaled_prod", "mult_result"]},
    {"id": "sum_pair", "op": "add",
     "alts": ["sub", "mul"],
     "names_train": ["sum_pair", "total_pair", "add_up"],
     "names_held": ["combined_pair", "plus_total", "pair_sum"]},
    {"id": "max_of", "op": "max",
     "alts": ["min"],
     "names_train": ["bigger", "max_of", "the_larger"],
     "names_held": ["greater_of", "top_value", "max_pair"]},
    {"id": "min_of", "op": "min",
     "alts": ["max"],
     "names_train": ["smaller", "min_of", "the_lesser"],
     "names_held": ["lesser_of", "bottom_value", "min_pair"]},
]

_BIN_PROBES = [(17, 5), (10, 3), (8, 8), (23, 7), (4, 9), (31, 6)]
_VAR_PAIRS_TRAIN = [("a", "b"), ("x", "y"), ("m", "n")]
_VAR_PAIRS_HELD = [("p", "q"), ("u", "v"), ("first", "second")]


def _op_expr(op: str, A: str, B: str) -> str:
    if op in ("max", "min"):
        return f"{op}({A}, {B})"
    return _BIN_OPS[op][0].format(A=A, B=B)


def _swap_expr(op: str, A: str, B: str) -> Optional[str]:
    if op in ("add", "mul", "max", "min"):
        return None    # commutative: swapping is not a defect
    return _op_expr(op, B, A)


def _gen_binary_op(partition: str, rng: random.Random,
                   out: List[Dict[str, Any]]) -> Dict[str, int]:
    stats = {"made": 0, "dropped_noop": 0, "dropped_broken": 0}
    idioms = ["direct", "temp"] if partition == "train" \
        else ["temp", "guard_temp"]
    var_pairs = _VAR_PAIRS_TRAIN if partition == "train" \
        else _VAR_PAIRS_HELD
    names_key = "names_train" if partition == "train" else "names_held"
    op_names: Dict[str, List[str]] = {}
    for spec in _BIN_INTENTS:
        op_names.setdefault(spec["op"], []).extend(spec[names_key])

    def emit(name, expr, label, spec_id, kind):
        for idiom in idioms:
            for A, B in var_pairs:
                e = expr.format(A=A, B=B) if "{A}" in expr else expr
                code = _fn(name, f"{A}, {B}", _body(e, idiom))
                out.append({"text": code, "label": label,
                            "group": f"intent-bin-{spec_id}-{name}",
                            "intent": spec_id, "kind": kind,
                            "family": "name-intent-binary"})
                stats["made"] += 1

    for spec in _BIN_INTENTS:
        op = spec["op"]
        correct_expr = _op_expr(op, "{A}", "{B}")
        for name in spec[names_key]:
            emit(name, correct_expr, "clean", spec["id"], "correct")
            for alt in spec["alts"]:
                emit(name, _op_expr(alt, "{A}", "{B}"),
                     _BIN_OPS.get(alt, (None, "wrong-operator"))[1]
                     if alt not in ("max", "min") else "wrong-operator",
                     spec["id"], f"mutation-{alt}")
            sw = _swap_expr(op, "{A}", "{B}")
            if sw:
                emit(name, sw, "swapped-operands", spec["id"],
                     "mutation-swapped")
        # controls: the intent's correct body under a name whose own
        # intent it satisfies is already covered by that intent's
        # own correct rows; here: correct body under NEUTRAL names
        # (clean), and each alt body under the name of the intent
        # it actually implements (clean — name/body agreement).
        for name in NEUTRAL_NAMES[:3]:
            emit(name, correct_expr, "clean", spec["id"],
                 "control-neutral-correct")
        for alt in spec["alts"]:
            for name in op_names.get(alt, [])[:2]:
                emit(name, _op_expr(alt, "{A}", "{B}"), "clean",
                     spec["id"], f"control-agree-{alt}")
    return stats


# ------------------------------------------------- expression intents
# Compound expressions whose intent lives in the name (the minutes
# shape that the parent misses, percent, average-of-two).
_EXPR_INTENTS: List[Dict[str, Any]] = [
    {"id": "minutes",
     "names_train": ["total_minutes", "to_minutes", "minutes_of"],
     "names_held": ["minutes_total", "time_in_minutes", "mins_all"],
     "params": ("hours", "mins"),
     "correct": "{H} * 60 + {M}",
     "mutations": {"wrong-operator": "{H} * 60 - {M}",
                   "swapped-operands": "{M} * 60 + {H}"}},
    {"id": "percent",
     "names_train": ["percent_of", "pct", "percentage"],
     "names_held": ["share_pct", "percent_share", "pc_of"],
     "params": ("part", "whole"),
     "correct": "{H} / {M} * 100",
     "mutations": {"wrong-operator": "{H} * {M} * 100",
                   "swapped-operands": "{M} / {H} * 100"}},
    {"id": "average_pair",
     "names_train": ["average_pair", "mean_pair", "midpoint"],
     "names_held": ["pair_average", "avg_two", "mean_of_two"],
     "params": ("a", "b"),
     "correct": "({H} + {M}) / 2",
     "mutations": {"wrong-operator": "({H} - {M}) / 2",
                   "swapped-operands": None}},
    {"id": "clamp",
     "names_train": ["clamp_val", "clamp_it", "bounded"],
     "names_held": ["clamp_num", "keep_in_range", "bound_val"],
     "params": ("v", "lo", "hi"),
     "correct": "max({M}, min({X}, {H}))",
     "mutations": {"swapped-operands": "max({X}, min({M}, {H}))",
                   "wrong-operator": None}},
]

_EXPR_PROBES = {
    "minutes": [(2, 30), (1, 15), (3, 45), (0, 20)],
    "percent": [(25, 200), (1, 4), (30, 60), (7, 20)],
    "average_pair": [(10, 20), (3, 9), (8, 8), (5, 15)],
    "clamp": [(15, 0, 10), (5, 0, 10), (-3, 0, 10), (7, 2, 6)],
}


def _gen_expr_intents(partition: str, rng: random.Random,
                      out: List[Dict[str, Any]]) -> Dict[str, int]:
    stats = {"made": 0}
    idioms = ["direct", "temp"] if partition == "train" \
        else ["temp", "guard_temp"]
    names_key = "names_train" if partition == "train" else "names_held"
    for spec in _EXPR_INTENTS:
        H, M = spec["params"][0], spec["params"][1]
        X = spec["params"][2] if len(spec["params"]) > 2 else None
        params = ", ".join(spec["params"])
        subst = {"H": H, "M": M, "X": X or ""}
        for name in spec[names_key]:
            for idiom in idioms:
                c = _fn(name, params,
                        _body(spec["correct"].format(**subst), idiom))
                out.append({"text": c, "label": "clean",
                            "group": f"intent-expr-{spec['id']}-{name}",
                            "intent": spec["id"], "kind": "correct",
                            "family": "name-intent-expr"})
                stats["made"] += 1
                for cls, mexpr in spec["mutations"].items():
                    if mexpr is None:
                        continue
                    code = _fn(name, params,
                               _body(mexpr.format(**subst), idiom))
                    out.append({"text": code, "label": cls,
                                "group": f"intent-expr-{spec['id']}-{name}",
                                "intent": spec["id"],
                                "kind": f"mutation-{cls}",
                                "family": "name-intent-expr"})
                    stats["made"] += 1
        # neutral-name controls: correct body, neutral name -> clean
        for name in NEUTRAL_NAMES[:2]:
            c = _fn(name, params,
                    _body(spec["correct"].format(**subst), "direct"))
            out.append({"text": c, "label": "clean",
                        "group": f"intent-expr-{spec['id']}-neutral",
                        "intent": spec["id"], "kind": "control-neutral",
                        "family": "name-intent-expr"})
            stats["made"] += 1
    return stats


# ------------------------------------------------------------ index
# Position intents: the name declares WHERE (first/last/at) and HOW
# MANY. Bodies are parameterized by (start_shift, count_shift);
# (0, 0) keeps the promise, anything else is off-by-one — under the
# declaring name AND under neutral names (position contracts are
# structural in this task's construction; see module docstring).
_INDEX_PROBES = [([10, 20, 30, 40, 50],), ([3, 1, 4],),
                 ([7, 8, 9, 11],)]
_INDEX_PROBES_K = [([10, 20, 30, 40, 50], 2), ([3, 1, 4, 1, 5], 3),
                   ([7, 8, 9, 11], 1)]


def _index_family(partition: str, out: List[Dict[str, Any]],
                  names_key: str, spec: Dict[str, Any]) -> int:
    made = 0
    idioms = ["direct", "temp"] if partition == "train" \
        else ["temp", "guard_temp"]
    for name in spec[names_key]:
        for idiom in idioms:
            for tag, expr, label in spec["variants"]:
                code = _fn(name, spec["params"],
                           _body(expr, idiom, ret_var="out"))
                out.append({"text": code, "label": label,
                            "group": f"intent-idx-{spec['id']}-{name}",
                            "intent": spec["id"],
                            "kind": "correct" if label == "clean"
                                    else "mutation-off-by-one",
                            "family": "name-intent-index"})
                made += 1
    return made


_INDEX_SPECS: List[Dict[str, Any]] = [
    {"id": "first_two", "params": "xs",
     "names_train": ["first_two", "first_pair", "opening_two"],
     "names_held": ["initial_two", "lead_pair", "front_two"],
     "variants": [("ok", "xs[0], xs[1]", "clean"),
                  ("shift", "xs[1], xs[2]", "off-by-one"),
                  ("extend", "xs[0], xs[1], xs[2]", "off-by-one")]},
    {"id": "last_element", "params": "xs",
     "names_train": ["last_item", "last_val", "the_last"],
     "names_held": ["final_element", "last_entry", "end_value"],
     "variants": [("ok", "xs[len(xs) - 1]", "clean"),
                  ("over", "xs[len(xs)]", "off-by-one"),
                  ("under", "xs[len(xs) - 2]", "off-by-one")]},
    {"id": "first_k", "params": "xs, k",
     "names_train": ["first_k", "take_first", "head_k"],
     "names_held": ["leading_k", "front_k", "initial_k"],
     "variants": [("ok", "xs[:k]", "clean"),
                  ("plus", "xs[:k + 1]", "off-by-one"),
                  ("minus", "xs[:k - 1]", "off-by-one")]},
    {"id": "element_at", "params": "xs, i",
     "names_train": ["element_at", "get_item", "item_at_i"],
     "names_held": ["fetch_at", "value_at", "nth_item"],
     "variants": [("ok", "xs[i]", "clean"),
                  ("plus", "xs[i + 1]", "off-by-one"),
                  ("minus", "xs[i - 1]", "off-by-one")]},
    {"id": "last_two", "params": "xs",
     "names_train": ["last_two", "tail_pair", "closing_two"],
     "names_held": ["final_two", "end_pair", "rear_two"],
     "variants": [("ok", "xs[-2], xs[-1]", "clean"),
                  ("shift", "xs[-3], xs[-2]", "off-by-one"),
                  ("shiftin", "xs[-1], xs[0]", "off-by-one")]},
]


def _gen_index(partition: str, rng: random.Random,
               out: List[Dict[str, Any]]) -> Dict[str, int]:
    names_key = "names_train" if partition == "train" else "names_held"
    made = 0
    for spec in _INDEX_SPECS:
        made += _index_family(partition, out, names_key, spec)
        # loop-form variants for the two range-shaped intents are in
        # the range family below; here: neutral-name controls —
        # correct bodies clean, shifted bodies off-by-one.
        for name in NEUTRAL_NAMES[:2]:
            for tag, expr, label in spec["variants"][:2]:
                code = _fn(name, spec["params"], _body(expr, "direct",
                                                       ret_var="out"))
                out.append({"text": code, "label": label,
                            "group": f"intent-idx-{spec['id']}-neutral",
                            "intent": spec["id"],
                            "kind": "control-neutral",
                            "family": "name-intent-index"})
                made += 1
    # sum_first_k: the range-shaped member of the family (its slice
    # is "range", so it feeds the class generally, not the index
    # child's slice — included for the class-level judge).
    sfk_names = (["sum_first_k", "head_sum_k", "total_first"] if
                 partition == "train" else
                 ["sum_leading_k", "front_sum_k", "initial_sum_k"])
    idioms = ["direct", "temp"] if partition == "train" \
        else ["temp", "guard_temp"]
    for name in sfk_names:
        for idiom in idioms:
            for tag, bound, label in (("ok", "k", "clean"),
                                      ("plus", "k + 1", "off-by-one"),
                                      ("minus", "k - 1", "off-by-one")):
                lines = (f"s = 0\n    for i in range({bound}):\n"
                         f"        s += xs[i]\n    return s")
                code = f"def {name}(xs, k):\n    {lines}" \
                    if idiom == "direct" else \
                    f"def {name}(xs, k):\n    {lines}"
                out.append({"text": code, "label": label,
                            "group": f"intent-idx-sumfirst-{name}",
                            "intent": "sum_first_k",
                            "kind": "correct" if label == "clean"
                                    else "mutation-off-by-one",
                            "family": "name-intent-index"})
                made += 1
    return {"made": made}


# ------------------------------------------------------------ aggregate
_AGG_SPECS: List[Dict[str, Any]] = [
    {"id": "average_list", "params": "xs",
     "names_train": ["average_of", "mean_of", "avg_list"],
     "names_held": ["mean_value", "average_value", "list_mean"],
     "correct": "sum(xs) / len(xs)",
     "mutations": {"wrong-operator": "sum(xs) * len(xs)",
                   "missing-return": None}},
    {"id": "total_list", "params": "xs",
     "names_train": ["total_of", "sum_list", "sum_all"],
     "names_held": ["grand_total", "list_total", "sum_values"],
     "correct": "sum(xs)",
     "mutations": {"wrong-operator": None,
                   "missing-return": None}},
]

_AGG_PROBES = [([2, 4, 6],), ([10, 20],), ([1, 2, 3, 4],), ([5],)]


def _gen_aggregate(partition: str, rng: random.Random,
                   out: List[Dict[str, Any]]) -> Dict[str, int]:
    names_key = "names_train" if partition == "train" else "names_held"
    idioms = ["direct", "temp"] if partition == "train" \
        else ["temp", "guard_temp"]
    made = 0
    for spec in _AGG_SPECS:
        for name in spec[names_key]:
            for idiom in idioms:
                out.append({"text": _fn(name, spec["params"],
                                        _body(spec["correct"], idiom)),
                            "label": "clean",
                            "group": f"intent-agg-{spec['id']}-{name}",
                            "intent": spec["id"], "kind": "correct",
                            "family": "name-intent-aggregate"})
                made += 1
                for cls, mexpr in spec["mutations"].items():
                    if mexpr is None:
                        if cls == "missing-return":
                            code = _fn(name, spec["params"],
                                       f"res = {spec['correct']}")
                            out.append({"text": code, "label": cls,
                                        "group": f"intent-agg-{spec['id']}-{name}",
                                        "intent": spec["id"],
                                        "kind": f"mutation-{cls}",
                                        "family": "name-intent-aggregate"})
                            made += 1
                        continue
                    out.append({"text": _fn(name, spec["params"],
                                            _body(mexpr, idiom)),
                                "label": cls,
                                "group": f"intent-agg-{spec['id']}-{name}",
                                "intent": spec["id"],
                                "kind": f"mutation-{cls}",
                                "family": "name-intent-aggregate"})
                    made += 1
    return {"made": made}


# ------------------------------------------------------------ assembly
_PROBES_BY_FAMILY = {
    "name-intent-binary": _BIN_PROBES,
    "name-intent-aggregate": _AGG_PROBES,
}


_INDEX_PROBES_I = [([10, 20, 30, 40], 1), ([3, 1, 4, 1], 0),
                   ([7, 8, 9], 2)]


def _probes_for(item: Dict[str, Any]) -> Optional[List[Tuple]]:
    if item["family"] == "name-intent-expr":
        return _EXPR_PROBES.get(item["intent"])
    if item["family"] == "name-intent-index":
        if item["intent"] in ("first_k", "sum_first_k"):
            return _INDEX_PROBES_K
        if item["intent"] == "element_at":
            return _INDEX_PROBES_I
        return _INDEX_PROBES
    return _PROBES_BY_FAMILY.get(item["family"])


def _sanity_filter(items: List[Dict[str, Any]]) -> Tuple[List[Dict], Dict]:
    """Drop degenerate items (see module docstring): a correct body
    that does not run clean on its probes, or a mutation that no
    probe distinguishes from its group's correct body."""
    stats = {"dropped_broken_correct": 0, "dropped_noop_mutation": 0,
             "dropped_unprobed": 0}
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for it in items:
        groups.setdefault(it["group"], []).append(it)
    kept: List[Dict[str, Any]] = []
    for it in items:
        probes = _probes_for(it)
        if probes is None:
            stats["dropped_unprobed"] += 1
            continue
        if it["label"] == "clean":
            # a body labelled clean must actually run clean on the
            # probes — construction says it keeps its promise, and a
            # "correct" body that raises is a generator bug, not data
            if not _runs_clean(it["text"], probes):
                stats["dropped_broken_correct"] += 1
                continue
            kept.append(it)
            continue
        # mutation: must differ from SOME correct item in its group
        # with the same parameter signature
        sig = it["text"].split("):")[0]
        cands = [c for c in groups[it["group"]]
                 if c["label"] == "clean"
                 and c["text"].split("):")[0] == sig]
        if cands and not any(_distinguishes(c["text"], it["text"],
                                            probes) for c in cands):
            stats["dropped_noop_mutation"] += 1
            continue
        kept.append(it)
    return kept, stats


def generate(partition: str, seed: int) -> List[Dict[str, Any]]:
    """Raw (pre-filter) items for one partition."""
    rng = random.Random(seed)
    out: List[Dict[str, Any]] = []
    _gen_binary_op(partition, rng, out)
    _gen_expr_intents(partition, rng, out)
    _gen_index(partition, rng, out)
    _gen_aggregate(partition, rng, out)
    # exact-text dedupe (idiom/var collisions across families)
    seen, deduped = set(), []
    for it in out:
        if it["text"] in seen:
            continue
        seen.add(it["text"])
        deduped.append(it)
    kept, stats = _sanity_filter(deduped)
    for it in kept:
        it["sanity"] = "passed"
    kept_stats = dict(stats)
    kept_stats["raw"] = len(out)
    kept_stats["deduped"] = len(deduped)
    kept_stats["kept"] = len(kept)
    return kept, kept_stats  # type: ignore[return-value]


def _name_shape(text: str) -> Tuple[str, str]:
    """(function name, anonymized shape) — the pair that identifies
    a gate surface in disguise for THIS family."""
    from swarm import factory as F
    m = re.search(r"def\s+(\w+)", text)
    return (m.group(1) if m else "",
            re.sub(r"\s+", " ", F._anonymize_code(text).strip().lower()))


def build_datasets() -> Dict[str, Any]:
    """Generate both partitions, contamination-filter them against
    every existing corpus, and write
    growth/data/name_intent_{train,held}.json + manifest.json.

    FILTER MODE for this family is "text" (name-preserving), NOT
    the "code" mode the dream pool uses — deliberately. The code
    mode's anonymized-shape rule treats two snippets that differ
    only in identifiers as the same surface; for name-intent data
    the NAME is the signal, so `remainder: a - b` and
    `difference: a - b` are different items (one breaks its name's
    promise, the other keeps it), and anonymizing would delete
    exactly the signal the family exists to carry. What must not
    happen is training on a GATE surface in disguise, and that is
    guarded two ways: (1) the text-mode filter (exact duplicate +
    featurized keyset jaccard >= 0.85, where the keyset includes
    the name tokens and operator trigrams), and (2) an explicit
    (name, anonymized-shape) guard: any generated item whose
    function name AND anonymized shape both match a phase-3 held
    item is dropped — the same name on a genuinely different
    surface (other variables, other idiom) is how generalization
    is taught, exactly like the phase-3 train/held template split
    teaches the same concepts under different families.

    Filter order: the held partition is filtered against the train
    partition AND all corpora; the train partition against all
    corpora INCLUDING the phase-3 held set and the sealed v2 items
    (judge surfaces), and against the name-intent held set. The
    sealed items are used ONLY as filter references (the role
    battery items play in executors.contamination_filter); they
    are never trained on and never copied into any output."""
    import json as _json

    from swarm import dream as swarm_dream
    from swarm import phase3 as P3

    from . import dream_gen as G
    from .executors import contamination_filter

    train_raw, train_stats = generate("train", seed=7101)
    held_raw, held_stats = generate("held", seed=7202)

    corpora: Dict[str, List[Dict[str, Any]]] = {}
    corpora["phase3_train"] = P3.gen_bug_patterns(
        P3._BUG_TEMPLATES_TRAIN, 21)
    corpora["phase3_held"] = P3.gen_bug_patterns(
        P3._BUG_TEMPLATES_HELD, 22)
    corpora["swarm_dream"] = swarm_dream.gen_dream_bug_examples()
    pool, _ = G.gen_pool({1: 30, 2: 26, 3: 26}, seed=5150,
                         group_prefix="refpool")
    corpora["factory_dream_pool"] = pool
    try:
        from . import bug_heldout_v2 as bh
        corpora["sealed_v2_refs"] = bh.load_sealed()["items"]
    except Exception:  # noqa: BLE001
        corpora["sealed_v2_refs"] = []
    import hive_battery as HB
    corpora["battery_code_items"] = [
        {"text": t, "label": l} for t, l in
        HB.CONTRACT_ITEMS + HB.SECRET_ITEMS]

    all_refs: List[Dict[str, Any]] = []
    for v in corpora.values():
        all_refs.extend(v)

    held_clean, held_dropped = contamination_filter(
        held_raw, all_refs + train_raw, "text")
    train_clean, train_dropped = contamination_filter(
        train_raw, all_refs + held_clean, "text")

    # (name, anonymized-shape) guard against the phase-3 held gate
    gate_pairs = {_name_shape(r["text"]) for r in corpora["phase3_held"]}
    n_guard = {"train": 0, "held": 0}
    kept_train = []
    for it in train_clean:
        if _name_shape(it["text"]) in gate_pairs:
            n_guard["train"] += 1
            continue
        kept_train.append(it)
    kept_held = []
    for it in held_clean:
        if _name_shape(it["text"]) in gate_pairs:
            n_guard["held"] += 1
            continue
        kept_held.append(it)
    train_clean, held_clean = kept_train, kept_held

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "name_intent_train.json").write_text(
        _json.dumps(train_clean, indent=1, ensure_ascii=False))
    (DATA_DIR / "name_intent_held.json").write_text(
        _json.dumps(held_clean, indent=1, ensure_ascii=False))

    def dist(items):
        d: Dict[str, int] = {}
        for it in items:
            d[it["label"]] = d.get(it["label"], 0) + 1
        return d

    manifest = {
        "family": "name-intent (growth Lever 1)",
        "partitions": {
            "train": {"seed": 7101, "file": "name_intent_train.json",
                      "raw_stats": train_stats,
                      "after_contamination": len(train_clean),
                      "dropped_contamination": len(train_dropped),
                      "label_dist": dist(train_clean)},
            "held": {"seed": 7202, "file": "name_intent_held.json",
                     "raw_stats": held_stats,
                     "after_contamination": len(held_clean),
                     "dropped_contamination": len(held_dropped),
                     "label_dist": dist(held_clean)},
        },
        "partition_rules": [
            "INTENT-BEARING function names disjoint across "
            "partitions and disjoint from the phase-3 template "
            "names where the shape would collide (the contamination "
            "filter enforces the rest); NEUTRAL control names "
            "(compute, calc, ...) are shared by design — they carry "
            "no intent, so they leak no signal across the split",
            "variable-name pairs disjoint: train (a,b),(x,y),(m,n); "
            "held (p,q),(u,v),(first,second)",
            "idioms: train {direct, temp}; held {temp, guard_temp}",
            "held is a judge surface only: never trained on; every "
            "training pool is contamination-filtered against it",
            "contamination filter mode is TEXT (name-preserving) "
            "for this family — see build_datasets docstring; plus "
            "an explicit (name, anonymized-shape) guard against "
            "the phase-3 held gate surfaces",
        ],
        "name_shape_guard_drops": n_guard,
        "corpora_filtered_against": {k: len(v) for k, v in
                                     corpora.items()},
        "labels": "construction-known (declared name intent vs body), "
                  "NOT execution-verified — the new signal class; an "
                  "execution sanity pass removes only degenerate "
                  "items (broken correct bodies, no-op mutations)",
    }
    (DATA_DIR / "manifest.json").write_text(
        _json.dumps(manifest, indent=1, ensure_ascii=False))
    return manifest


def load_train() -> List[Dict[str, Any]]:
    import json as _json
    return _json.loads((DATA_DIR / "name_intent_train.json").read_text())


def load_held() -> List[Dict[str, Any]]:
    import json as _json
    return _json.loads((DATA_DIR / "name_intent_held.json").read_text())


if __name__ == "__main__":
    m = build_datasets()
    print(json.dumps(m, indent=1, ensure_ascii=False))
