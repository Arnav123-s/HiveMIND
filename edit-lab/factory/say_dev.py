"""Dev pool for the learned say (Fable-study Build 2) — Muse's work,
Muse's side.

The say is fitted ONLY on this pool: development material, never a
judging surface. Sources, all labelled bug-pattern items in the
usual {text, label} shape:

  * fresh — NEW template families written for this build (below),
    structures chosen apart from the sealed v2 families and the
    phase-3 families;
  * held — the phase-3 held set (seed 22): the phase-4 judge,
    SPENT as a one-shot confirm in dream-phaseC-002; a spent judge
    is dev material now, never a judge again;
  * screen — the factory dream screen pool (seed 9100), a control /
    fitting surface by design (the waking-dream verifier thresholds
    were tuned on it);
  * swarmdream — the swarm's phase-4 dream corpus (37 items).

Decontamination: every item is filtered with the factory's own
contamination filter (executors.contamination_filter, code mode)
against (a) the sealed held-out v2 items and (b) the phase-3 TRAIN
set — the two surfaces the say must never touch: the seal it will
be judged on, and the members' own training data (fitting a
combiner on its members' training answers would grade memory,
not combination). The fresh families are additionally filtered
against every reference corpus in bug_heldout_v2 (held/screen/
dream pools included) before merging, so a fresh family that
collides with an existing corpus is dropped, not shipped.

The built pool is written ONCE to factory/say_dev.json; the
builder refuses to overwrite it, so every battery run fits on the
same dev pool and fits stay comparable across runs.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

LAB_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(LAB_ROOT / "coding"))
sys.path.insert(0, str(LAB_ROOT))

from swarm import dream as swarm_dream  # noqa: E402
from swarm import phase3 as P3  # noqa: E402

from . import bug_heldout_v2 as sealed_mod  # noqa: E402
from . import dream_gen as G  # noqa: E402
from .executors import contamination_filter  # noqa: E402

DEV_PATH = Path(__file__).parent / "say_dev.json"
SEED = 20261112

# ------------------------------------------------------------ fresh families
# (correct_code, {bug_class: buggy_code}) — structures apart from the
# sealed v2 families (factorial, set-intersection, find_pos,
# count_upper, insert-prepend, grid_total, fib_step, longest_word,
# mean_positive, dedupe_count, prod_step, pct_of, slope, bmi,
# running_total) and from the phase-3 families; the contamination
# filter below is the enforcement, this list is the intent.
_TEMPLATES_DEV = [
    ("def clamp(x, lo, hi):\n    return max(lo, min(hi, x))",
     {"wrong-operator": "def clamp(x, lo, hi):\n    return min(lo, max(hi, x))",
      "missing-return": "def clamp(x, lo, hi):\n    r = max(lo, min(hi, x))"}),
    ("def second_largest(xs):\n    s = sorted(set(xs))\n    return s[-2]",
     {"off-by-one": "def second_largest(xs):\n    s = sorted(set(xs))\n    return s[-1]",
      "missing-return": "def second_largest(xs):\n    s = sorted(set(xs))\n    r = s[-2]"}),
    ("def count_char(s, ch):\n    n = 0\n    for c in s:\n        if c == ch:\n            n += 1\n    return n",
     {"wrong-operator": "def count_char(s, ch):\n    n = 0\n    for c in s:\n        if c != ch:\n            n += 1\n    return n",
      "off-by-one": "def count_char(s, ch):\n    n = 0\n    for c in s[:-1]:\n        if c == ch:\n            n += 1\n    return n",
      "missing-return": "def count_char(s, ch):\n    n = 0\n    for c in s:\n        if c == ch:\n            n += 1\n    print(n)"}),
    ("def merge_counts(a, b):\n    out = dict(a)\n    for k in b:\n        out[k] = out.get(k, 0) + b[k]\n    return out",
     {"wrong-operator": "def merge_counts(a, b):\n    out = dict(a)\n    for k in b:\n        out[k] = out.get(k, 0) - b[k]\n    return out",
      "missing-return": "def merge_counts(a, b):\n    out = dict(a)\n    for k in b:\n        out[k] = out.get(k, 0) + b[k]\n    result = out"}),
    ("def collect_positive(xs, acc=[]):\n    acc = list(acc)\n    for x in xs:\n        if x > 0:\n            acc.append(x)\n    return acc",
     {"mutable-default": "def collect_positive(xs, acc=[]):\n    for x in xs:\n        if x > 0:\n            acc.append(x)\n    return acc",
      "wrong-operator": "def collect_positive(xs, acc=[]):\n    acc = list(acc)\n    for x in xs:\n        if x < 0:\n            acc.append(x)\n    return acc"}),
    ("def is_pal(s):\n    return s == s[::-1]",
     {"wrong-operator": "def is_pal(s):\n    return s != s[::-1]",
      "missing-return": "def is_pal(s):\n    r = s == s[::-1]"}),
    ("def avg_evens(xs):\n    vals = [x for x in xs if x % 2 == 0]\n    return sum(vals) / len(vals)",
     {"wrong-operator": "def avg_evens(xs):\n    vals = [x for x in xs if x % 2 == 1]\n    return sum(vals) / len(vals)",
      "off-by-one": "def avg_evens(xs):\n    vals = [x for x in xs[1:] if x % 2 == 0]\n    return sum(vals) / len(vals)"}),
    ("def first_over(xs, target):\n    t = 0\n    for i, x in enumerate(xs):\n        t += x\n        if t > target:\n            return i\n    return -1",
     {"wrong-operator": "def first_over(xs, target):\n    t = 0\n    for i, x in enumerate(xs):\n        t += x\n        if t < target:\n            return i\n    return -1",
      "off-by-one": "def first_over(xs, target):\n    t = 0\n    for i, x in enumerate(xs[:-1]):\n        t += x\n        if t > target:\n            return i\n    return -1",
      "missing-return": "def first_over(xs, target):\n    t = 0\n    for i, x in enumerate(xs):\n        t += x\n        if t > target:\n            found = i\n    return -1"}),
    ("def rotate_left(xs):\n    return xs[1:] + xs[:1]",
     {"off-by-one": "def rotate_left(xs):\n    return xs[2:] + xs[:2]",
      "swapped-operands": "def rotate_left(xs):\n    return xs[:1] + xs[1:]"}),
    ("def aspect(w, h):\n    return w / h",
     {"swapped-operands": "def aspect(w, h):\n    return h / w",
      "wrong-operator": "def aspect(w, h):\n    return w * h"}),
    ("def sum_step_down(n):\n    t = 0\n    for i in range(n, 0, -1):\n        t += i\n    return t",
     {"off-by-one": "def sum_step_down(n):\n    t = 0\n    for i in range(n, 1, -1):\n        t += i\n    return t",
      "wrong-operator": "def sum_step_down(n):\n    t = 0\n    for i in range(n, 0, -1):\n        t -= i\n    return t"}),
    ("def repeat_name(name, n):\n    out = []\n    for i in range(n):\n        out.append(name)\n    return out",
     {"off-by-one": "def repeat_name(name, n):\n    out = []\n    for i in range(n - 1):\n        out.append(name)\n    return out",
      "missing-return": "def repeat_name(name, n):\n    out = []\n    for i in range(n):\n        out.append(name)\n    print(out)"}),
    ("def scale_all(xs, k):\n    return [x * k for x in xs]",
     {"wrong-operator": "def scale_all(xs, k):\n    return [x / k for x in xs]",
      "missing-return": "def scale_all(xs, k):\n    out = [x * k for x in xs]"}),
    ("def count_pairs(xs):\n    n = 0\n    for i in range(len(xs) - 1):\n        if xs[i] == xs[i + 1]:\n            n += 1\n    return n",
     {"off-by-one": "def count_pairs(xs):\n    n = 0\n    for i in range(len(xs) - 2):\n        if xs[i] == xs[i + 1]:\n            n += 1\n    return n",
      "wrong-operator": "def count_pairs(xs):\n    n = 0\n    for i in range(len(xs) - 1):\n        if xs[i] != xs[i + 1]:\n            n += 1\n    return n"}),
    ("def last_index(xs, v):\n    for i in range(len(xs) - 1, -1, -1):\n        if xs[i] == v:\n            return i\n    return -1",
     {"off-by-one": "def last_index(xs, v):\n    for i in range(len(xs) - 1, 0, -1):\n        if xs[i] == v:\n            return i\n    return -1",
      "wrong-operator": "def last_index(xs, v):\n    for i in range(len(xs) - 1, -1, -1):\n        if xs[i] != v:\n            return i\n    return -1"}),
    ("def tag(item, tags=[]):\n    tags = list(tags)\n    tags.append(item)\n    return tags",
     {"mutable-default": "def tag(item, tags=[]):\n    tags.append(item)\n    return tags"}),
]


def _fresh_items() -> List[Dict[str, Any]]:
    return [{"text": e["text"], "label": e["label"], "source": "fresh"}
            for e in P3.gen_bug_patterns(_TEMPLATES_DEV, SEED)]


def _source_items() -> Dict[str, List[Dict[str, Any]]]:
    held = P3.gen_bug_patterns(P3._BUG_TEMPLATES_HELD, 22)
    screen, _ = G.gen_screen_pool({1: 12, 2: 14, 3: 14}, seed=9100)
    swarm = swarm_dream.gen_dream_bug_examples()
    return {
        "held": [{"text": e["text"], "label": e["label"],
                  "source": "held"} for e in held],
        "screen": [{"text": e["text"], "label": e["label"],
                    "source": "screen"} for e in screen],
        "swarmdream": [{"text": e["text"], "label": e["label"],
                        "source": "swarmdream"} for e in swarm],
    }


def build_dev_pool() -> Dict[str, Any]:
    """Assemble + decontaminate + write once. Refuses to overwrite
    an existing pool (comparability across battery runs)."""
    if DEV_PATH.exists():
        raise FileExistsError(
            f"{DEV_PATH} already exists — the dev pool is built "
            f"once; rebuild under a new name if it must change")
    sealed_items = sealed_mod.load_sealed()["items"]
    train = P3.gen_bug_patterns(P3._BUG_TEMPLATES_TRAIN, 21)
    hard_refs = list(sealed_items) + list(train)

    # fresh families: must clear EVERY existing corpus + the seal
    corpora = sealed_mod.reference_corpora()
    all_refs: List[Dict[str, Any]] = list(hard_refs)
    for rows in corpora.values():
        all_refs.extend(rows)
    fresh_kept, fresh_dropped = contamination_filter(
        _fresh_items(), all_refs, "code")

    # existing dev surfaces: must clear the seal + the train set
    kept: List[Dict[str, Any]] = list(fresh_kept)
    dropped = list(fresh_dropped)
    per_source: Dict[str, Dict[str, int]] = {
        "fresh": {"in": len(_fresh_items()), "kept": len(fresh_kept)}}
    for name, items in _source_items().items():
        k, d = contamination_filter(items, hard_refs, "code")
        kept.extend(k)
        dropped.extend(d)
        per_source[name] = {"in": len(items), "kept": len(k)}

    # exact-text dedupe across sources (first source wins)
    seen = set()
    pool: List[Dict[str, Any]] = []
    for it in kept:
        if it["text"] in seen:
            continue
        seen.add(it["text"])
        pool.append(it)
    per_class: Dict[str, int] = {}
    for it in pool:
        per_class[it["label"]] = per_class.get(it["label"], 0) + 1
    record = {
        "name": "learned-say dev pool (fitting only, never a judge)",
        "built_by": "factory/say_dev.py (Muse's work, Muse's side)",
        "seed": SEED,
        "n": len(pool),
        "per_class": per_class,
        "per_source": per_source,
        "decontamination": {
            "references": {"sealed_v2": len(sealed_items),
                           "phase3_train": len(train),
                           "all_corpora_for_fresh": len(all_refs)},
            "dropped": len(dropped)},
        "items": pool,
    }
    tmp = DEV_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(record, indent=1, ensure_ascii=False))
    tmp.replace(DEV_PATH)
    return record


def load_dev_pool() -> Dict[str, Any]:
    if not DEV_PATH.exists():
        return build_dev_pool()
    return json.loads(DEV_PATH.read_text())


if __name__ == "__main__":
    rec = build_dev_pool()
    print(f"dev pool: n={rec['n']} per_class={rec['per_class']} "
          f"per_source={rec['per_source']} "
          f"dropped={rec['decontamination']['dropped']}")
