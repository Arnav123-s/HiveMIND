"""Spawn candidate #1 (from factory/spawn_mining.py, 2026-11-12):
a re-trained swapped-operands PLAIN-slice specialist — Muse's
work, Muse's side.

Why this candidate (mining evidence, factory/reports/
spawn-mining-2026-11-13.json):
  * raw composed recall for swapped-operands on the sealed set is
    0.0 in all 11 recorded measurements — the raw composer has
    never once named the class on fresh material;
  * on the dev pool, the routed rule's recall on the plain slice
    is 0.0667 (1/15) while every swapped seat is individually a
    strong binary classifier (0.88-0.96) — the seats can see the
    defect; the plain-slice seat the router *would* use exists
    (bug-swapped-operands-plain-model) but the strengths table
    routes plain to "whole", and no seat was ever trained for
    margin competition on plain shapes;
  * growth cycles attacked wrong-operator/expression and
    off-by-one/index in all 6 cycles — those shapes already have
    an owner; this one does not.

The candidate is trained the factory's usual way: a phase-3-style
generator (new template families below), the factory's own
contamination filter against the sealed set + phase-3 train + the
dev pool, and F.train_candidate (fmode "code", hidden 0 — the
parent seat's architecture). It faces the standard gates:

  Gate 1 (beat-parent, dual pristine slices): on two held slices
  built from family groups disjoint from the training families
  and from each other, the candidate's binary accuracy on
  plain-slice items must STRICTLY beat the incumbent plain
  seat's, on both.
  Gate 2 (battery): through the full waking-dream serving path
  on the sealed set, measured in one session — incumbent vs
  route-flip-only (strengths plain->slice, incumbent seat) vs
  candidate (flip + candidate seat). The candidate is adopted
  only if its configuration STRICTLY beats the incumbent's
  sealed slice; adoption then writes the model file, flips the
  strengths entry, updates the two registry hashes, and must
  pass the audit and a confirming battery run, else everything
  is rolled back from the snapshot in the run dir.
  Anything less: the candidate stays a recorded shadow in the
  run dir and serving does not change.

Outcome (2026-11-12, recorded in factory/reports/
spawn-mining-2026-11-13.md): Gate 1 failed in both rounds —
round 1 on surface collapse under the shape rule (train 44 -> 12
items; candidate 0.5714/0.7143 vs parent 0.7143/0.7143), round 2
with healthy surfaces (train 38, held 15/16; candidate
0.5333/0.625 vs parent 0.6667/0.625). Gate 2 never ran; nothing
was adopted. Twice-measured conclusion: data scale is the
binding constraint — a tens-of-items specialist does not beat a
corpus-trained seat; the mined shape is a composition problem
or a corpus-scale growth target, not a small-data birth.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

LAB_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(LAB_ROOT / "coding"))
sys.path.insert(0, str(LAB_ROOT))

from swarm import composers as C  # noqa: E402
from swarm import factory as F  # noqa: E402
from swarm import phase3 as P3  # noqa: E402
from swarm.decomposers import slice_of  # noqa: E402

from . import say_dev  # noqa: E402
from .bug_heldout_v2 import load_sealed  # noqa: E402
from .executors import contamination_filter  # noqa: E402

CLS = "swapped-operands"
RUN_DIR = Path(__file__).parent / "runs" / "spawn-candidate-001"
ROUND = 2
MODEL_REL = "coding/swarm/models/bug-swapped-operands-plain-model.json"

# ------------------------------------------------------------ families
# (correct, {class: buggy}) — order-bearing operations in plain
# (statement/expression, non-comprehension) shapes. Groups:
# train families first, then held-A families, then held-B
# families — disjoint structures per group by construction, and
# the contamination filter verifies against every standing corpus.
_TRAIN = [
    ("def total_diff(prices, base):\n    t = 0\n    for p in prices:\n        t += p - base\n    return t",
     {"swapped-operands": "def total_diff(prices, base):\n    t = 0\n    for p in prices:\n        t += base - p\n    return t",
      "wrong-operator": "def total_diff(prices, base):\n    t = 0\n    for p in prices:\n        t += p + base\n    return t"}),
    ("def scaled_gap(x, y, k):\n    d = x - y\n    return d * k",
     {"swapped-operands": "def scaled_gap(x, y, k):\n    d = y - x\n    return d * k",
      "wrong-operator": "def scaled_gap(x, y, k):\n    d = x + y\n    return d * k"}),
    ("def steps_to_target(start, target, step):\n    n = target - start\n    return n // step",
     {"swapped-operands": "def steps_to_target(start, target, step):\n    n = start - target\n    return n // step",
      "wrong-operator": "def steps_to_target(start, target, step):\n    n = target + start\n    return n // step"}),
    ("def weighted(a, wa, b, wb):\n    top = a * wa + b * wb\n    return top / (wa + wb)",
     {"swapped-operands": "def weighted(a, wa, b, wb):\n    top = b * wa + a * wb\n    return top / (wa + wb)",
      "wrong-operator": "def weighted(a, wa, b, wb):\n    top = a * wa + b * wb\n    return top * (wa + wb)"}),
    ("def used_share(total, used):\n    rate = used / total\n    return 1 - rate",
     {"swapped-operands": "def used_share(total, used):\n    rate = total / used\n    return 1 - rate",
      "wrong-operator": "def used_share(total, used):\n    rate = used * total\n    return 1 - rate"}),
    ("def growth(old, new):\n    d = new - old\n    return d / old",
     {"swapped-operands": "def growth(old, new):\n    d = old - new\n    return d / old",
      "wrong-operator": "def growth(old, new):\n    d = new - old\n    return d * old"}),
    ("def index_span(xs, i, j):\n    lo = xs[i]\n    hi = xs[j]\n    return hi - lo",
     {"swapped-operands": "def index_span(xs, i, j):\n    lo = xs[i]\n    hi = xs[j]\n    return lo - hi",
      "missing-return": "def index_span(xs, i, j):\n    lo = xs[i]\n    hi = xs[j]\n    span = hi - lo"}),
    ("def percent_off(price, sale):\n    cut = price - sale\n    return cut * 100 / price",
     {"swapped-operands": "def percent_off(price, sale):\n    cut = sale - price\n    return cut * 100 / price",
      "wrong-operator": "def percent_off(price, sale):\n    cut = price - sale\n    return cut * 100 * price"}),
    ("def countdown_diff(n, k):\n    t = n\n    while t > k:\n        t -= k\n    return n - t",
     {"swapped-operands": "def countdown_diff(n, k):\n    t = n\n    while t > k:\n        t -= k\n    return t - n",
      "off-by-one": "def countdown_diff(n, k):\n    t = n\n    while t >= k:\n        t -= k\n    return n - t"}),
    ("def span_mid(a, b):\n    d = b - a\n    return a + d / 2",
     {"swapped-operands": "def span_mid(a, b):\n    d = a - b\n    return a + d / 2",
      "wrong-operator": "def span_mid(a, b):\n    d = b - a\n    return a - d / 2"}),
    ("def convert_back(amount, rate):\n    base = amount / rate\n    fee = base * 0.1\n    return base - fee",
     {"swapped-operands": "def convert_back(amount, rate):\n    base = rate / amount\n    fee = base * 0.1\n    return base - fee",
      "wrong-operator": "def convert_back(amount, rate):\n    base = amount / rate\n    fee = base * 0.1\n    return base + fee"}),
    ("def score_gap(rounds):\n    best = max(rounds)\n    worst = min(rounds)\n    return best - worst",
     {"swapped-operands": "def score_gap(rounds):\n    best = max(rounds)\n    worst = min(rounds)\n    return worst - best",
      "wrong-operator": "def score_gap(rounds):\n    best = max(rounds)\n    worst = min(rounds)\n    return best + worst"}),
    ("def late_by(due, done):\n    d = done - due\n    if d < 0:\n        return 0\n    return d",
     {"swapped-operands": "def late_by(due, done):\n    d = due - done\n    if d < 0:\n        return 0\n    return d",
      "off-by-one": "def late_by(due, done):\n    d = done - due\n    if d <= 0:\n        return 0\n    return d"}),
    ("def unit_cost(total, n, pack):\n    each = total / n\n    return each * pack",
     {"swapped-operands": "def unit_cost(total, n, pack):\n    each = n / total\n    return each * pack",
      "wrong-operator": "def unit_cost(total, n, pack):\n    each = total / n\n    return each / pack"}),
]

_HELD_A = [
    ("def drift(a, b):\n    d = a - b\n    return d * 2 + a",
     {"swapped-operands": "def drift(a, b):\n    d = b - a\n    return d * 2 + a",
      "wrong-operator": "def drift(a, b):\n    d = a - b\n    return d * 2 - a"}),
    ("def share2(a, b):\n    t = a + b\n    return a / t",
     {"swapped-operands": "def share2(a, b):\n    t = a + b\n    return b / t",
      "wrong-operator": "def share2(a, b):\n    t = a + b\n    return a * t"}),
    ("def borrow(book, taken):\n    left = book - taken\n    return left * 2",
     {"swapped-operands": "def borrow(book, taken):\n    left = taken - book\n    return left * 2",
      "missing-return": "def borrow(book, taken):\n    left = book - taken\n    out = left * 2"}),
    ("def speed2(dist, time):\n    v = dist / time\n    return v * 3.6",
     {"swapped-operands": "def speed2(dist, time):\n    v = time / dist\n    return v * 3.6",
      "wrong-operator": "def speed2(dist, time):\n    v = dist / time\n    return v / 3.6"}),
    ("def order_pair(x, y):\n    if x < y:\n        return (x, y)\n    return (y, x)",
     {"swapped-operands": "def order_pair(x, y):\n    if x < y:\n        return (y, x)\n    return (x, y)",
      "wrong-operator": "def order_pair(x, y):\n    if x > y:\n        return (x, y)\n    return (y, x)"}),
    ("def twice_gap(a, b):\n    g = a - b\n    return g + g",
     {"swapped-operands": "def twice_gap(a, b):\n    g = b - a\n    return g + g",
      "wrong-operator": "def twice_gap(a, b):\n    g = a - b\n    return g * g"}),
]

_HELD_B = [
    ("def margin2(cost, price):\n    m = price - cost\n    return m / cost",
     {"swapped-operands": "def margin2(cost, price):\n    m = cost - price\n    return m / cost",
      "wrong-operator": "def margin2(cost, price):\n    m = price - cost\n    return m * cost"}),
    ("def fill_ratio(tank, used):\n    left = tank - used\n    return left / tank",
     {"swapped-operands": "def fill_ratio(tank, used):\n    left = used - tank\n    return left / tank",
      "wrong-operator": "def fill_ratio(tank, used):\n    left = tank - used\n    return left * tank"}),
    ("def seq_pair(a, b):\n    first = a * 100\n    return first + b",
     {"swapped-operands": "def seq_pair(a, b):\n    first = b * 100\n    return first + a",
      "wrong-operator": "def seq_pair(a, b):\n    first = a * 100\n    return first - b"}),
    ("def drop_pct(start, end):\n    d = start - end\n    return d * 100 / start",
     {"swapped-operands": "def drop_pct(start, end):\n    d = end - start\n    return d * 100 / start",
      "wrong-operator": "def drop_pct(start, end):\n    d = start - end\n    return d * 100 * start"}),
    ("def loan_left(principal, paid):\n    r = principal - paid\n    return r if r > 0 else 0",
     {"swapped-operands": "def loan_left(principal, paid):\n    r = paid - principal\n    return r if r > 0 else 0",
      "off-by-one": "def loan_left(principal, paid):\n    r = principal - paid\n    return r if r >= 0 else 0"}),
    ("def two_rates(a, b):\n    hi = max(a, b)\n    lo = min(a, b)\n    return hi / lo",
     {"swapped-operands": "def two_rates(a, b):\n    hi = max(a, b)\n    lo = min(a, b)\n    return lo / hi",
      "wrong-operator": "def two_rates(a, b):\n    hi = max(a, b)\n    lo = min(a, b)\n    return hi * lo"}),
]


def _gen(templates, seed):
    return P3.gen_bug_patterns(templates, seed)


def _binary(items):
    """Binary surface for THIS seat's job: swapped vs other,
    plain-slice items only."""
    out = []
    for it in items:
        if slice_of(CLS, it["text"]) != "plain":
            continue
        out.append({"text": it["text"],
                    "label": CLS if it["label"] == CLS else "other"})
    return out


def build_surfaces() -> Dict[str, Any]:
    refs: List[Dict[str, Any]] = list(load_sealed()["items"])
    refs += P3.gen_bug_patterns(P3._BUG_TEMPLATES_TRAIN, 21)
    refs += say_dev.load_dev_pool()["items"]
    surfaces = {}
    for name, templates, seed in (("train", _TRAIN, 777),
                                  ("held_a", _HELD_A, 778),
                                  ("held_b", _HELD_B, 779)):
        raw = _gen(templates, seed)
        kept, dropped = contamination_filter(raw, refs, "code")
        surfaces[name] = {"items": kept, "dropped": len(dropped),
                          "binary": _binary(kept)}
    return surfaces


def _binary_acc(model, items) -> float:
    if not items:
        return 0.0
    return F.accuracy(model, items)


def run_gates() -> Dict[str, Any]:
    from .run_battery import _bug_reg, _eval_bug_path
    from .serve import ServingHive
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    surfaces = build_surfaces()
    hive = ServingHive.load()
    reg = _bug_reg(hive)
    parent = reg["bug-swapped-operands-plain-model"]
    train_bin = surfaces["train"]["binary"]
    held_a = surfaces["held_a"]["binary"]
    held_b = surfaces["held_b"]["binary"]
    task = {"name": "bug-swapped-operands-plain-candidate",
            "niche": "debugging",
            "job": ("decide whether a plain-shaped snippet's defect "
                    "is swapped-operands (vs anything else)"),
            "classes": [CLS, "other"],
            "train": train_bin, "heldout": held_a + held_b}
    cand = F.train_candidate(task, fmode="code", hidden=0,
                             epochs=300)
    gate1 = {
        "parent_acc_held_a": round(_binary_acc(parent, held_a), 4),
        "parent_acc_held_b": round(_binary_acc(parent, held_b), 4),
        "candidate_acc_held_a": round(_binary_acc(cand, held_a), 4),
        "candidate_acc_held_b": round(_binary_acc(cand, held_b), 4),
        "n_held_a": len(held_a), "n_held_b": len(held_b),
        "n_train": len(train_bin)}
    gate1["passed"] = (
        gate1["candidate_acc_held_a"] > gate1["parent_acc_held_a"]
        and gate1["candidate_acc_held_b"] > gate1["parent_acc_held_b"])
    record: Dict[str, Any] = {
        "candidate": task["name"], "round": ROUND, "built_at":
        time.strftime("%Y-%m-%d %H:%M %Z"),
        "surfaces": {k: {"n": len(v["items"]),
                         "n_binary_plain": len(v["binary"]),
                         "dropped_contaminated": v["dropped"]}
                     for k, v in surfaces.items()},
        "gate1_beat_parent_dual_slice": gate1}
    if gate1["passed"]:
        sealed_items = load_sealed()["items"]
        base_cfg = C.load_config()
        acc_inc, rec_inc = _eval_bug_path(reg, base_cfg, sealed_items)
        flip_cfg = json.loads(json.dumps(base_cfg))
        flip_cfg.setdefault("strengths", {}).setdefault(
            CLS, {})["plain"] = "slice"
        acc_flip, rec_flip = _eval_bug_path(reg, flip_cfg,
                                            sealed_items)
        reg_c = dict(reg)
        reg_c["bug-swapped-operands-plain-model"] = cand
        acc_cand, rec_cand = _eval_bug_path(reg_c, flip_cfg,
                                            sealed_items)
        record["gate2_battery"] = {
            "incumbent": {"acc": round(acc_inc, 4),
                          "recalls": rec_inc},
            "flip_only": {"acc": round(acc_flip, 4),
                          "recalls": rec_flip},
            "candidate": {"acc": round(acc_cand, 4),
                          "recalls": rec_cand},
            "passed": acc_cand > acc_inc}
        if record["gate2_battery"]["passed"]:
            record["candidate_model"] = cand.record()
    (RUN_DIR / f"gate-record-round{ROUND}.json").write_text(
        json.dumps(record, indent=1, ensure_ascii=False))
    return record


if __name__ == "__main__":
    rec = run_gates()
    print(json.dumps({k: rec[k] for k in
                      ("surfaces", "gate1_beat_parent_dual_slice")},
                     indent=1))
    if "gate2_battery" in rec:
        print(json.dumps(rec["gate2_battery"], indent=1))
