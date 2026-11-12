"""Fresh sealed held-out set for bug-pattern (final-product item 1).

The phase-4 held-out set was SPENT as the one-shot confirm of dream
cycle dream-phaseC-002 (FACTORY-LOOP.md, Phase C consequence). Any
future gated bug-pattern verdict needs a new sealed set first. This
module builds one:

  * NEW template families (literal phase-3-style pairs) whose
    structures appear in NO existing corpus: not the phase-3 train
    or held templates, not the swarm's phase-4 dream templates, not
    the factory dream train/screen families;
  * decontamination against ALL of those corpora with the factory's
    own filter (executors.contamination_filter, code mode — exact,
    anonymized-shape, and keyset-jaccard rules);
  * the surviving items are written ONCE to
    coding/swarm/bug_heldout_v2.json with a sha256 seal. The builder
    refuses to overwrite an existing sealed file: a sealed set that
    can be silently regenerated is not sealed.

The baseline measurement (run_bug_heldout.py) evaluates the CURRENT
adopted composition on the sealed set exactly once, with no tuning
of anything — no thresholds, no model selection, no retries. The
set then judges future cycles the way the phase-4 set judged past
ones: spent only as a gated confirm, never as training data.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

LAB_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(LAB_ROOT / "coding"))
sys.path.insert(0, str(LAB_ROOT))

from swarm import dream as swarm_dream  # noqa: E402
from swarm import phase3 as P3  # noqa: E402

from . import dream_gen as G  # noqa: E402
from .executors import contamination_filter  # noqa: E402

SEALED_PATH = LAB_ROOT / "coding" / "swarm" / "bug_heldout_v2.json"
SEED = 20261110

# ------------------------------------------------------------ new families
# (correct_code, {bug_class: buggy_code}) — structures chosen to be
# absent from train / held / swarm-dream / factory-dream corpora:
# factorial loop, set intersection, for-loop search, string-method
# counting, insert-based mutable default, nested i*j grid, fibonacci
# tuple-swap loop, max(key=len), filtered mean, dedupe count,
# stepped range product, percentage, slope, bmi, running-total
# mutable default.
_TEMPLATES_V2 = [
    ("def fact(n):\n    r = 1\n    for i in range(2, n + 1):\n        r *= i\n    return r",
     {"off-by-one": "def fact(n):\n    r = 1\n    for i in range(2, n):\n        r *= i\n    return r",
      "wrong-operator": "def fact(n):\n    r = 1\n    for i in range(2, n + 1):\n        r += i\n    return r",
      "missing-return": "def fact(n):\n    r = 1\n    for i in range(2, n + 1):\n        r *= i\n    print(r)"}),
    ("def common(a, b):\n    return len(set(a) & set(b))",
     {"wrong-operator": "def common(a, b):\n    return len(set(a) | set(b))",
      "missing-return": "def common(a, b):\n    n = len(set(a) & set(b))"}),
    ("def find_pos(xs, v):\n    for i in range(len(xs)):\n        if xs[i] == v:\n            return i\n    return -1",
     {"off-by-one": "def find_pos(xs, v):\n    for i in range(len(xs) - 1):\n        if xs[i] == v:\n            return i\n    return -1",
      "wrong-operator": "def find_pos(xs, v):\n    for i in range(len(xs)):\n        if xs[i] != v:\n            return i\n    return -1"}),
    ("def count_upper(s):\n    n = 0\n    for ch in s:\n        if ch.isupper():\n            n += 1\n    return n",
     {"wrong-operator": "def count_upper(s):\n    n = 0\n    for ch in s:\n        if ch.islower():\n            n += 1\n    return n",
      "missing-return": "def count_upper(s):\n    n = 0\n    for ch in s:\n        if ch.isupper():\n            n += 1\n    total = n"}),
    ("def prepend(item, log=[]):\n    log = list(log)\n    log.insert(0, item)\n    return log",
     {"mutable-default": "def prepend(item, log=[]):\n    log.insert(0, item)\n    return log"}),
    ("def grid_total(rows, cols):\n    t = 0\n    for i in range(rows):\n        for j in range(cols):\n            t += i * j\n    return t",
     {"off-by-one": "def grid_total(rows, cols):\n    t = 0\n    for i in range(rows):\n        for j in range(cols - 1):\n            t += i * j\n    return t",
      "wrong-operator": "def grid_total(rows, cols):\n    t = 0\n    for i in range(rows):\n        for j in range(cols):\n            t -= i * j\n    return t"}),
    ("def fib_step(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a",
     {"off-by-one": "def fib_step(n):\n    a, b = 0, 1\n    for _ in range(n - 1):\n        a, b = b, a + b\n    return a",
      "wrong-operator": "def fib_step(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a - b\n    return a",
      "missing-return": "def fib_step(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    result = a"}),
    ("def longest_word(words):\n    return max(words, key=len)",
     {"wrong-operator": "def longest_word(words):\n    return min(words, key=len)",
      "missing-return": "def longest_word(words):\n    best = max(words, key=len)"}),
    ("def mean_positive(xs):\n    vals = [x for x in xs if x > 0]\n    return sum(vals) / len(vals)",
     {"off-by-one": "def mean_positive(xs):\n    vals = [x for x in xs[1:] if x > 0]\n    return sum(vals) / len(vals)",
      "wrong-operator": "def mean_positive(xs):\n    vals = [x for x in xs if x < 0]\n    return sum(vals) / len(vals)"}),
    ("def dedupe_count(xs):\n    return len(set(xs))",
     {"wrong-operator": "def dedupe_count(xs):\n    return len(xs) - len(set(xs))",
      "missing-return": "def dedupe_count(xs):\n    n = len(set(xs))"}),
    ("def prod_step(n):\n    p = 1\n    for i in range(1, n + 1, 2):\n        p *= i\n    return p",
     {"off-by-one": "def prod_step(n):\n    p = 1\n    for i in range(1, n, 2):\n        p *= i\n    return p",
      "wrong-operator": "def prod_step(n):\n    p = 1\n    for i in range(1, n + 1, 2):\n        p += i\n    return p"}),
    ("def pct_of(part, total):\n    return part * 100 / total",
     {"swapped-operands": "def pct_of(part, total):\n    return total * 100 / part",
      "wrong-operator": "def pct_of(part, total):\n    return part * 100 * total"}),
    ("def slope(x1, y1, x2, y2):\n    return (y2 - y1) / (x2 - x1)",
     {"swapped-operands": "def slope(x1, y1, x2, y2):\n    return (x2 - x1) / (y2 - y1)",
      "wrong-operator": "def slope(x1, y1, x2, y2):\n    return (y2 + y1) / (x2 - x1)"}),
    ("def bmi(weight, height):\n    return weight / (height * height)",
     {"swapped-operands": "def bmi(weight, height):\n    return height / (weight * weight)",
      "wrong-operator": "def bmi(weight, height):\n    return weight * (height * height)"}),
    ("def running_total(x, acc=[]):\n    acc = list(acc)\n    acc.append(x + (acc[-1] if acc else 0))\n    return acc",
     {"mutable-default": "def running_total(x, acc=[]):\n    acc.append(x + (acc[-1] if acc else 0))\n    return acc"}),
]


def reference_corpora() -> Dict[str, List[Dict[str, Any]]]:
    """Every corpus the sealed set must be disjoint from."""
    train = P3.gen_bug_patterns(P3._BUG_TEMPLATES_TRAIN, 21)
    held = P3.gen_bug_patterns(P3._BUG_TEMPLATES_HELD, 22)
    swarm_corpus = swarm_dream.gen_dream_bug_examples()
    factory_pool, _ = G.gen_pool({1: 40, 2: 34, 3: 34}, seed=4200,
                                 group_prefix="dreamtrain")
    factory_screen, _ = G.gen_screen_pool({1: 12, 2: 14, 3: 14},
                                          seed=9100)
    return {"phase3_train": train, "phase3_held_spent": held,
            "swarm_phase4_dream_corpus": swarm_corpus,
            "factory_dream_pool_phaseC": factory_pool,
            "factory_dream_screen_phaseC": factory_screen}


def canonical_hash(items: List[Dict[str, Any]]) -> str:
    blob = json.dumps(items, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def build_sealed() -> Dict[str, Any]:
    """Generate + decontaminate + seal. Refuses to overwrite an
    existing sealed file (fail-closed: sealing is one-way)."""
    if SEALED_PATH.exists():
        raise FileExistsError(
            f"{SEALED_PATH} already exists — a sealed set is never "
            f"regenerated in place; build a v3 under a new name instead")
    raw = P3.gen_bug_patterns(_TEMPLATES_V2, SEED)
    corpora = reference_corpora()
    references: List[Dict[str, Any]] = []
    for rows in corpora.values():
        references.extend(rows)
    kept, dropped = contamination_filter(raw, references, "code")
    per_class: Dict[str, int] = {}
    for it in kept:
        per_class[it["label"]] = per_class.get(it["label"], 0) + 1
    record = {
        "name": "bug-pattern held-out v2 (sealed)",
        "status": "SEALED",
        "created": "2026-11-10",
        "purpose": ("successor to the phase-4 held-out set, which was "
                    "spent as the dream-phaseC-002 one-shot confirm; "
                    "this set restores the ability to judge future "
                    "bug-pattern cycles"),
        "usage_rule": ("measurement only: gated confirms and baselines. "
                       "Never training data, never tuning input. Any "
                       "item used to select or tune a model spends "
                       "that item's class coverage and must be "
                       "recorded against the seal."),
        "seed": SEED,
        "n_raw": len(raw),
        "n": len(kept),
        "per_class": per_class,
        "decontamination": {
            "references": {k: len(v) for k, v in corpora.items()},
            "dropped": len(dropped),
            "dropped_detail": [
                {"label": d["label"], "reason": d["drop_reason"]}
                for d in dropped],
        },
        "sha256": canonical_hash(kept),
        "items": kept,
    }
    tmp = SEALED_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(record, indent=1, ensure_ascii=False))
    tmp.replace(SEALED_PATH)
    return record


def load_sealed() -> Dict[str, Any]:
    rec = json.loads(SEALED_PATH.read_text())
    if canonical_hash(rec["items"]) != rec["sha256"]:
        raise ValueError("sealed held-out v2 hash mismatch — the seal "
                         "is broken; refuse to measure on it")
    return rec
