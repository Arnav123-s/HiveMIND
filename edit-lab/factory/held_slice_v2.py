"""The LARGER pristine phase-3-style held slice (cycle-3 prep,
2026-11-11).

Why this exists, in the cycle-2 report's own words: both cycle-2
births were decided on the phase-3 held slice, which is n=20 per
target slice and has now been spent as a decision surface twice.
"If a single phase-3 held item is the whole blocker for a target,
the honest fix is a LARGER pristine phase-3-style held slice (new
template families, disjoint names/idioms), not more candidates
against the same 20 items."

Construction, mirroring swarm/phase3.py's template discipline:

  * 25 NEW template families — function concepts, names and body
    idioms disjoint from the phase-3 train AND held templates,
    from both name-intent partitions, and from every other corpus
    the contamination filter knows;
  * each family is (correct code, {defect class: buggy code}) in
    exactly phase-3's shape, expanded by the same rule
    gen_bug_patterns uses (one clean + one item per defect);
  * labels are EXECUTION-VERIFIED, stronger than construction
    alone: every family's probes are run against the correct body
    and every buggy body — a clean item must run clean on all its
    probes, and every defect item must differ behaviourally from
    the correct body on at least one probe (mutable-default
    families are verified with sequential-call probes, the only
    way that defect surfaces);
  * the generated set is contamination-filtered (text mode)
    against phase-3 train/held, the swarm dream corpus, the
    factory dream pool, name-intent partitions 1 and 2, the
    sealed v2 set and the battery code items, plus the
    (name, anonymized-shape) guard against the phase-3 held gate;
  * items orphaned by filtering (a defect whose family's clean
    item was dropped) are dropped with it and counted.

SEALED. This slice is a judge surface for FUTURE growth cycles:
it is never trained on and never used for candidate selection.
It is registered (growth/cycle3_surfaces.json) as the successor
judge to the phase-3 held slice; wiring it into the runner as a
gate is cycle 3's own step, not this one's.

Files: growth/data/phase3x_held.json + phase3x_manifest.json.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

LAB_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(LAB_ROOT / "coding"))
sys.path.insert(0, str(LAB_ROOT))

from .name_intent import _load_fn, _probe_out  # noqa: E402

GROWTH_DIR = LAB_ROOT / "growth"
DATA_DIR = GROWTH_DIR / "data"

# (family, correct, {defect: buggy}, probes)
# A probe is an argument tuple, or ("seq", [args, args, ...]) for
# sequential calls on ONE loaded function (mutable-default).
_FAMILIES: List[Tuple[str, str, Dict[str, str], List[Any]]] = [
    ("area_rect",
     "def area_rect(w, h):\n    return w * h",
     {"wrong-operator": "def area_rect(w, h):\n    return w + h",
      "missing-return": "def area_rect(w, h):\n    res = w * h"},
     [(3, 4), (5, 2), (1, 1)]),
    ("sale_price",
     "def sale_price(price, off):\n    return price - off",
     {"swapped-operands": "def sale_price(price, off):\n    return off - price",
      "wrong-operator": "def sale_price(price, off):\n    return price + off"},
     [(100, 15), (40, 5), (9, 3)]),
    ("count_letter",
     "def count_letter(s, ch):\n    n = 0\n    for c in s:\n"
     "        if c == ch:\n            n += 1\n    return n",
     {"wrong-operator": "def count_letter(s, ch):\n    n = 0\n"
      "    for c in s:\n        if c != ch:\n            n += 1\n"
      "    return n",
      "missing-return": "def count_letter(s, ch):\n    n = 0\n"
      "    for c in s:\n        if c == ch:\n            n += 1\n"
      "    print(n)"},
     [("banana", "a"), ("xyz", "a"), ("aaa", "a")]),
    ("sum_step_range",
     "def sum_step_range(a, b, step):\n    s = 0\n"
     "    for i in range(a, b, step):\n        s += i\n    return s",
     {"off-by-one": "def sum_step_range(a, b, step):\n    s = 0\n"
      "    for i in range(a + step, b, step):\n        s += i\n"
      "    return s",
      "wrong-operator": "def sum_step_range(a, b, step):\n    s = 0\n"
      "    for i in range(a, b, step):\n        s -= i\n    return s"},
     [(0, 10, 2), (1, 9, 3), (0, 5, 1)]),
    ("second_last",
     "def second_last(xs):\n    return xs[-2]",
     {"off-by-one": "def second_last(xs):\n    return xs[-1]",
      "missing-return": "def second_last(xs):\n    res = xs[-2]"},
     [([10, 20, 30],), ([5, 6],)]),
    ("middle_slice",
     "def middle_slice(xs):\n    return xs[1:-1]",
     {"off-by-one": "def middle_slice(xs):\n    return xs[2:-1]",
      "missing-return": "def middle_slice(xs):\n    res = xs[1:-1]"},
     [([1, 2, 3, 4, 5],), ([9, 8, 7],)]),
    ("zip_ratio",
     "def zip_ratio(a, b):\n    return [x / y for x, y in zip(a, b)]",
     {"swapped-operands": "def zip_ratio(a, b):\n"
      "    return [y / x for x, y in zip(a, b)]",
      "wrong-operator": "def zip_ratio(a, b):\n"
      "    return [x + y for x, y in zip(a, b)]"},
     [([10, 20], [2, 5]), ([9, 3], [3, 3])]),
    ("running_max_list",
     "def running_max_list(xs):\n    m = xs[0]\n    out = []\n"
     "    for v in xs:\n        if v > m:\n            m = v\n"
     "        out.append(m)\n    return out",
     {"wrong-operator": "def running_max_list(xs):\n    m = xs[0]\n"
      "    out = []\n    for v in xs:\n        if v < m:\n"
      "            m = v\n        out.append(m)\n    return out",
      "missing-return": "def running_max_list(xs):\n    m = xs[0]\n"
      "    out = []\n    for v in xs:\n        if v > m:\n"
      "            m = v\n        out.append(m)"},
     [([3, 7, 2, 9],), ([5],), ([2, 1],)]),
    ("gather_odds",
     "def gather_odds(xs):\n    return [x for x in xs if x % 2 == 1]",
     {"wrong-operator": "def gather_odds(xs):\n"
      "    return [x for x in xs if x % 2 == 0]",
      "missing-return": "def gather_odds(xs):\n"
      "    res = [x for x in xs if x % 2 == 1]"},
     [([1, 2, 3, 4, 5],), ([2, 4],)]),
    ("append_copy",
     "def append_copy(item, bag=None):\n    bag = list(bag) if bag else []\n"
     "    bag.append(item)\n    return bag",
     {"mutable-default": "def append_copy(item, bag=[]):\n"
      "    bag.append(item)\n    return bag",
      "missing-return": "def append_copy(item, bag=None):\n"
      "    bag = list(bag) if bag else []\n    bag.append(item)"},
     [("seq", [(7,), (8,), (9,)])]),
    ("collect_scores",
     "def collect_scores(name, pts, table=None):\n"
     "    table = dict(table) if table else {}\n"
     "    table[name] = pts\n    return table",
     {"mutable-default": "def collect_scores(name, pts, table={}):\n"
      "    table[name] = pts\n    return table",
      "missing-return": "def collect_scores(name, pts, table=None):\n"
      "    table = dict(table) if table else {}\n"
      "    table[name] = pts"},
     [("seq", [("ann", 3), ("bob", 4)])]),
    ("total_cost",
     "def total_cost(prices, fee):\n    return sum(prices) + fee",
     {"wrong-operator": "def total_cost(prices, fee):\n"
      "    return sum(prices) - fee",
      "missing-return": "def total_cost(prices, fee):\n"
      "    res = sum(prices) + fee"},
     [([10, 20], 5), ([3], 2)]),
    ("first_negative_index",
     "def first_negative_index(xs):\n    for i in range(len(xs)):\n"
     "        if xs[i] < 0:\n            return i\n    return -1",
     {"off-by-one": "def first_negative_index(xs):\n"
      "    for i in range(1, len(xs)):\n        if xs[i] < 0:\n"
      "            return i\n    return -1",
      "wrong-operator": "def first_negative_index(xs):\n"
      "    for i in range(len(xs)):\n        if xs[i] > 0:\n"
      "            return i\n    return -1"},
     [([4, -2, 7],), ([-5, 3],), ([1, 2],)]),
    ("every_second_sum",
     "def every_second_sum(xs):\n    s = 0\n    for x in xs[::2]:\n"
     "        s += x\n    return s",
     {"off-by-one": "def every_second_sum(xs):\n    s = 0\n"
      "    for x in xs[1::2]:\n        s += x\n    return s",
      "wrong-operator": "def every_second_sum(xs):\n    s = 0\n"
      "    for x in xs[::2]:\n        s -= x\n    return s"},
     [([1, 2, 3, 4, 5],), ([10, 1, 20],)]),
    ("sum_digits",
     "def sum_digits(s):\n    total = 0\n    for ch in s:\n"
     "        total += int(ch)\n    return total",
     {"wrong-operator": "def sum_digits(s):\n    total = 0\n"
      "    for ch in s:\n        total -= int(ch)\n    return total",
      "missing-return": "def sum_digits(s):\n    total = 0\n"
      "    for ch in s:\n        total += int(ch)\n    print(total)"},
     [("123",), ("90",), ("5",)]),
    ("countdown_list",
     "def countdown_list(n):\n    return list(range(n, 0, -1))",
     {"off-by-one": "def countdown_list(n):\n"
      "    return list(range(n, 1, -1))",
      "wrong-operator": "def countdown_list(n):\n"
      "    return [i + 1 for i in range(n, 0, -1)]"},
     [(4,), (1,), (6,)]),
    ("average_first_half",
     "def average_first_half(xs):\n    h = len(xs) // 2\n"
     "    return sum(xs[:h]) / h",
     {"off-by-one": "def average_first_half(xs):\n"
      "    h = len(xs) // 2\n    return sum(xs[:h + 1]) / (h + 1)",
      "wrong-operator": "def average_first_half(xs):\n"
      "    h = len(xs) // 2\n    return sum(xs[:h]) * h"},
     [([2, 4, 6, 8],), ([1, 3, 5, 7, 9, 11],)]),
    ("both_ends_sum",
     "def both_ends_sum(xs):\n    return xs[0] + xs[-1]",
     {"off-by-one": "def both_ends_sum(xs):\n    return xs[1] + xs[-1]",
      "wrong-operator": "def both_ends_sum(xs):\n"
      "    return xs[0] - xs[-1]"},
     [([4, 9, 2, 7],), ([3, 5],)]),
    ("count_starting",
     "def count_starting(words, ch):\n    n = 0\n    for w in words:\n"
     "        if w[0] == ch:\n            n += 1\n    return n",
     {"wrong-operator": "def count_starting(words, ch):\n    n = 0\n"
      "    for w in words:\n        if w[0] != ch:\n"
      "            n += 1\n    return n",
      "missing-return": "def count_starting(words, ch):\n    n = 0\n"
      "    for w in words:\n        if w[0] == ch:\n"
      "            n += 1\n    print(n)"},
     [(["apple", "avocado", "banana"], "a"), (["kiwi"], "a")]),
    ("zip_sub",
     "def zip_sub(a, b):\n    return [x - y for x, y in zip(a, b)]",
     {"swapped-operands": "def zip_sub(a, b):\n"
      "    return [y - x for x, y in zip(a, b)]",
      "wrong-operator": "def zip_sub(a, b):\n"
      "    return [x + y for x, y in zip(a, b)]"},
     [([9, 5], [1, 2]), ([4, 4], [4, 1])]),
    ("double_each",
     "def double_each(xs):\n    return [x * 2 for x in xs]",
     {"wrong-operator": "def double_each(xs):\n"
      "    return [x + 2 for x in xs]",
      "missing-return": "def double_each(xs):\n"
      "    res = [x * 2 for x in xs]"},
     [([1, 3, 5],), ([0, 2],)]),
    ("index_sum_pair",
     "def index_sum_pair(xs, i, j):\n    return xs[i] + xs[j]",
     {"off-by-one": "def index_sum_pair(xs, i, j):\n"
      "    return xs[i + 1] + xs[j]",
      "wrong-operator": "def index_sum_pair(xs, i, j):\n"
      "    return xs[i] - xs[j]"},
     [([5, 6, 7], 0, 2), ([1, 2], 0, 1)]),
    ("divide_pair",
     "def divide_pair(a, b):\n    return a / b",
     {"swapped-operands": "def divide_pair(a, b):\n    return b / a",
      "wrong-operator": "def divide_pair(a, b):\n    return a * b"},
     [(10, 2), (9, 3), (7, 2)]),
    ("power_pair",
     "def power_pair(base, exp):\n    return base ** exp",
     {"swapped-operands": "def power_pair(base, exp):\n"
      "    return exp ** base",
      "wrong-operator": "def power_pair(base, exp):\n"
      "    return base * exp"},
     [(2, 3), (3, 2), (5, 1)]),
    ("sum_odds_upto",
     "def sum_odds_upto(n):\n    s = 0\n    for i in range(1, n + 1, 2):\n"
     "        s += i\n    return s",
     {"off-by-one": "def sum_odds_upto(n):\n    s = 0\n"
      "    for i in range(1, n, 2):\n        s += i\n    return s",
      "wrong-operator": "def sum_odds_upto(n):\n    s = 0\n"
      "    for i in range(1, n + 1, 2):\n        s -= i\n    return s"},
     [(7,), (5,), (9,)]),
]


# ------------------------------------------------------------ execution
def _run_probes(code: str, probes: List[Any]):
    """Outputs of one code body over its family's probes, or None
    if it does not load. A fresh function is loaded per probe
    entry; a ("seq", [...]) entry calls its args in order on ONE
    loaded function (mutable-default state is the signal)."""
    outs = []
    for p in probes:
        fn = _load_fn(code)
        if fn is None:
            return None
        if isinstance(p, tuple) and len(p) == 2 and p[0] == "seq":
            outs.append(tuple(_probe_out(fn, a) for a in p[1]))
        else:
            outs.append(_probe_out(fn, p))
    return outs


def verify_families(families=_FAMILIES) -> Dict[str, Any]:
    """Execution verification of the raw families: every clean
    body loads and runs clean (all probe calls 'ok'); every defect
    body is behaviourally distinguished from its family's correct
    body on at least one probe."""
    failures: List[str] = []
    checked = {"clean": 0, "defect": 0}
    for name, correct, bugs, probes in families:
        ref = _run_probes(correct, probes)
        checked["clean"] += 1
        if ref is None:
            failures.append(f"{name}: correct body does not load")
            continue
        flat = []
        for o in ref:
            flat.extend(o if isinstance(o, tuple) and o
                        and isinstance(o[0], tuple) else [o])
        if any(o[0] != "ok" for o in flat):
            failures.append(f"{name}: correct body does not run "
                            f"clean on its probes: {ref}")
        for cls, buggy in bugs.items():
            checked["defect"] += 1
            out = _run_probes(buggy, probes)
            if out is None:
                failures.append(f"{name}/{cls}: buggy body does "
                                f"not load")
            elif out == ref:
                failures.append(f"{name}/{cls}: indistinguishable "
                                f"from correct on all probes")
    return {"checked": checked, "failures": failures,
            "ok": not failures}


def generate() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for name, correct, bugs, _probes in _FAMILIES:
        out.append({"text": correct, "label": "clean",
                    "group": f"phase3x-{name}", "family": "phase3x",
                    "template_family": name})
        for cls, buggy in bugs.items():
            out.append({"text": buggy, "label": cls,
                        "group": f"phase3x-{name}", "family": "phase3x",
                        "template_family": name})
    return out


def verify_items(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Re-verification of written items against their families'
    probes (post-filter form of verify_families)."""
    probes_by_family = {f[0]: f[3] for f in _FAMILIES}
    correct_by_family = {f[0]: f[1] for f in _FAMILIES}
    failures: List[str] = []
    checked = {"clean": 0, "defect": 0}
    for it in items:
        fam = it["template_family"]
        probes = probes_by_family[fam]
        out = _run_probes(it["text"], probes)
        if out is None:
            failures.append(f"{fam}: item does not load")
            continue
        if it["label"] == "clean":
            checked["clean"] += 1
            flat = []
            for o in out:
                flat.extend(o if isinstance(o, tuple) and o
                            and isinstance(o[0], tuple) else [o])
            if any(o[0] != "ok" for o in flat):
                failures.append(f"{fam}: clean item does not run "
                                f"clean")
        else:
            checked["defect"] += 1
            ref = _run_probes(correct_by_family[fam], probes)
            if out == ref:
                failures.append(f"{fam}/{it['label']}: defect item "
                                f"indistinguishable from correct")
    return {"checked": checked, "failures": failures,
            "ok": not failures}


# ------------------------------------------------------------ assembly
def _name_shape(text: str) -> Tuple[str, str]:
    from swarm import factory as F
    m = re.search(r"def\s+(\w+)", text)
    return (m.group(1) if m else "",
            re.sub(r"\s+", " ", F._anonymize_code(text).strip().lower()))


def build_slice() -> Dict[str, Any]:
    from swarm import dream as swarm_dream
    from swarm import phase3 as P3

    from . import dream_gen as G
    from . import name_intent as ni1
    from . import name_intent2 as ni2
    from .executors import contamination_filter

    ver_raw = verify_families()
    if not ver_raw["ok"]:
        raise RuntimeError(f"phase3x family verification failed: "
                           f"{ver_raw['failures'][:4]}")
    raw = generate()

    corpora: Dict[str, List[Dict[str, Any]]] = {}
    corpora["phase3_train"] = P3.gen_bug_patterns(
        P3._BUG_TEMPLATES_TRAIN, 21)
    corpora["phase3_held"] = P3.gen_bug_patterns(
        P3._BUG_TEMPLATES_HELD, 22)
    corpora["swarm_dream"] = swarm_dream.gen_dream_bug_examples()
    pool, _ = G.gen_pool({1: 30, 2: 26, 3: 26}, seed=5150,
                         group_prefix="refpool")
    corpora["factory_dream_pool"] = pool
    corpora["name_intent1_train"] = ni1.load_train()
    corpora["name_intent1_held"] = ni1.load_held()
    try:
        corpora["name_intent2_train"] = ni2.load_train()
        corpora["name_intent2_held"] = ni2.load_held()
    except Exception:  # noqa: BLE001
        corpora["name_intent2_train"] = []
        corpora["name_intent2_held"] = []
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

    clean, dropped = contamination_filter(raw, all_refs, "text")
    gate_pairs = {_name_shape(r["text"])
                  for r in corpora["phase3_held"]}
    kept, n_guard = [], 0
    for it in clean:
        if _name_shape(it["text"]) in gate_pairs:
            n_guard += 1
            continue
        kept.append(it)
    clean = kept
    # orphan pass: a defect whose family's clean item was filtered
    # out leaves with it (counted, not hidden)
    clean_families = {it["template_family"] for it in clean
                      if it["label"] == "clean"}
    kept = [it for it in clean
            if it["label"] == "clean"
            or it["template_family"] in clean_families]
    n_orphan = len(clean) - len(kept)
    clean = kept

    ver = verify_items(clean)
    if not ver["ok"]:
        raise RuntimeError(f"phase3x post-filter verification "
                           f"failed: {ver['failures'][:4]}")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "phase3x_held.json").write_text(
        json.dumps(clean, indent=1, ensure_ascii=False))

    from swarm import decomposers as D

    def dist(items, key):
        d: Dict[str, int] = {}
        for it in items:
            d[key(it)] = d.get(key(it), 0) + 1
        return d

    slice_sizes: Dict[str, int] = {}
    for cls in ("wrong-operator", "off-by-one", "swapped-operands",
                "missing-return"):
        for sl in sorted({D.slice_of(cls, it["text"]) for it in clean}):
            sub = [it for it in clean
                   if D.slice_of(cls, it["text"]) == sl]
            slice_sizes[f"{cls}/{sl}"] = len(sub)

    manifest = {
        "surface": "phase3x — larger pristine phase-3-style held slice",
        "sealed": True,
        "role": "pristine judge for future growth cycles; NEVER "
                "trained on, NEVER used for candidate selection",
        "file": "phase3x_held.json",
        "n": len(clean),
        "families": sorted({it["template_family"] for it in clean}),
        "label_dist": dist(clean, lambda it: it["label"]),
        "slice_subset_sizes": slice_sizes,
        "verification": {"raw_families": ver_raw, "written_items": ver},
        "dropped_contamination": len(dropped),
        "name_shape_guard_drops": n_guard,
        "orphaned_defect_drops": n_orphan,
        "corpora_filtered_against": {k: len(v) for k, v in
                                     corpora.items()},
        "disjointness": "template families, function names and body "
                        "idioms are new — disjoint from phase-3 "
                        "train/held templates and both name-intent "
                        "partitions; enforced by the text-mode "
                        "contamination filter + the (name, shape) "
                        "guard against the phase-3 held gate",
        "labels": "execution-verified: clean bodies run clean on "
                  "their probes; every defect body differs "
                  "behaviourally from its family's correct body on "
                  "at least one probe (mutable-default via "
                  "sequential-call probes)",
    }
    (DATA_DIR / "phase3x_manifest.json").write_text(
        json.dumps(manifest, indent=1, ensure_ascii=False))
    return manifest


def load_held() -> List[Dict[str, Any]]:
    return json.loads((DATA_DIR / "phase3x_held.json").read_text())


if __name__ == "__main__":
    m = build_slice()
    print(json.dumps(m, indent=1, ensure_ascii=False))
