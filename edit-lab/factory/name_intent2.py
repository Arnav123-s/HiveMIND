"""The NAME-INTENT family, PARTITION 2 (cycle-3 prep, 2026-11-11).

Partition 1 (factory/name_intent.py) covers binary-op, expression,
index and aggregate intents. Its held partition is now a standing
judge — a FIXED surface the growth grid can learn to overfit.
Partition 2 exists so the intent judge is not one fixed surface:
a second, independent partition over the intent territory
partition 1 does not touch — COMPARISON intents (a name that
declares a threshold test: count how many exceed, whether all
clear, where the first crossing is) and ACCUMULATOR intents (a
name that declares a running total/product/prefix series).

Construction discipline is partition 1's, unchanged:

  * an intent spec declares what a name promises; the generator
    emits the body that KEEPS the promise (clean) and bodies that
    BREAK it while remaining valid, runnable code (label = the
    defect class of the break: wrong-operator / off-by-one /
    missing-return);
  * labels are construction-known, NOT execution-provable (that
    is the point of the family); an execution sanity pass drops
    degenerate items only (a correct body that raises on its
    probes, a mutation no probe distinguishes from correct);
  * NEUTRAL-name controls carry the CORRECT body only, labelled
    clean (no promise was made); mutated bodies are never emitted
    under neutral names — partition 2 invents no new labelling
    rule;
  * comparison intents are written as loop + if-line idioms and
    accumulator intents as += / *= loop idioms, so the lab's own
    slice splitter (swarm/decomposers.slice_of) routes them into
    the comparison / accumulator slices they exist to judge;
  * partitions are disjoint in intent ids, function names,
    identifier vocabulary and body idioms, and BOTH partitions are
    contamination-filtered against every existing corpus AND
    against partition 1, in the same text (name-preserving) mode
    partition 1 uses, plus the (name, anonymized-shape) guard
    against the phase-3 held gate.

Files: growth/data/name_intent2_{train,held}.json +
name_intent2_manifest.json. The held partition is a judge surface
only: never trained on, and every future training pool must be
contamination-filtered against it, exactly as partition 1's held.
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

from .name_intent import (  # noqa: E402
    _distinguishes, _load_fn, _probe_out, _runs_clean)

GROWTH_DIR = LAB_ROOT / "growth"
DATA_DIR = GROWTH_DIR / "data"

NEUTRAL2 = ["tally_it", "work_it", "eval_it", "figure_it", "do_math"]

# Identifier vocabularies per partition — disjoint by construction.
_SUBST = {
    "train": {"@XS@": "xs", "@WS@": "ws", "@V@": "v", "@S@": "s",
              "@N@": "n", "@I@": "i", "@T@": "t", "@LO@": "lo",
              "@HI@": "hi", "@A@": "a", "@B@": "b", "@OUT@": "out"},
    "held": {"@XS@": "vals", "@WS@": "wts", "@V@": "val", "@S@": "acc",
             "@N@": "cnt", "@I@": "idx", "@T@": "limit", "@LO@": "low",
             "@HI@": "high", "@A@": "a", "@B@": "b", "@OUT@": "res"},
}


def _instantiate(template: str, partition: str, name: str) -> str:
    code = template
    for tok, ident in _SUBST[partition].items():
        code = code.replace(tok, ident)
    return code.replace("@NAME@", name)


# ------------------------------------------------------------ specs
# Each spec: full-code templates (def line included) in token form.
# "correct" keeps the name's promise; each mutation breaks it in
# exactly one labelled way. Probes are argument tuples on which
# every mutation must differ from correct (the sanity pass proves
# it per item, not per spec).
_SPECS: List[Dict[str, Any]] = [
    # ------------------------------------------------ comparison
    {"id": "count_above", "kind": "comparison",
     "names_train": ["count_above", "tally_over", "how_many_over"],
     "names_held": ["count_exceeding", "num_greater", "over_count"],
     "params": "@XS@, @T@",
     "correct": "def @NAME@(@XS@, @T@):\n    @N@ = 0\n"
                "    for @V@ in @XS@:\n        if @V@ > @T@:\n"
                "            @N@ += 1\n    return @N@",
     "mutations": {
         "wrong-operator": [
             "def @NAME@(@XS@, @T@):\n    @N@ = 0\n"
             "    for @V@ in @XS@:\n        if @V@ >= @T@:\n"
             "            @N@ += 1\n    return @N@",
             "def @NAME@(@XS@, @T@):\n    @N@ = 0\n"
             "    for @V@ in @XS@:\n        if @V@ < @T@:\n"
             "            @N@ += 1\n    return @N@"],
         "off-by-one": [
             "def @NAME@(@XS@, @T@):\n    @N@ = 0\n"
             "    for @V@ in @XS@:\n        if @V@ > @T@ + 1:\n"
             "            @N@ += 1\n    return @N@"]},
     "probes": [([5, 12, 7, 20], 10), ([1, 2, 3], 2),
                ([10, 10, 3], 10)]},
    {"id": "count_between", "kind": "comparison",
     "names_train": ["count_between", "tally_in_range",
                     "how_many_between"],
     "names_held": ["count_within", "num_in_band", "between_count"],
     "params": "@XS@, @LO@, @HI@",
     "correct": "def @NAME@(@XS@, @LO@, @HI@):\n    @N@ = 0\n"
                "    for @V@ in @XS@:\n"
                "        if @LO@ <= @V@ <= @HI@:\n"
                "            @N@ += 1\n    return @N@",
     "mutations": {
         "wrong-operator": [
             "def @NAME@(@XS@, @LO@, @HI@):\n    @N@ = 0\n"
             "    for @V@ in @XS@:\n"
             "        if @LO@ < @V@ < @HI@:\n"
             "            @N@ += 1\n    return @N@"],
         "off-by-one": [
             "def @NAME@(@XS@, @LO@, @HI@):\n    @N@ = 0\n"
             "    for @V@ in @XS@:\n"
             "        if @LO@ + 1 <= @V@ <= @HI@:\n"
             "            @N@ += 1\n    return @N@"]},
     "probes": [([1, 5, 10, 15], 5, 10), ([0, 3, 7], 2, 6),
                ([5, 5, 5], 5, 5)]},
    {"id": "first_index_above", "kind": "comparison",
     "names_train": ["first_index_above", "first_over_at",
                     "where_first_over"],
     "names_held": ["first_crossing_at", "earliest_over_idx",
                    "first_exceed_pos"],
     "params": "@XS@, @T@",
     "correct": "def @NAME@(@XS@, @T@):\n"
                "    for @I@ in range(len(@XS@)):\n"
                "        if @XS@[@I@] > @T@:\n"
                "            return @I@\n    return -1",
     "mutations": {
         "wrong-operator": [
             "def @NAME@(@XS@, @T@):\n"
             "    for @I@ in range(len(@XS@)):\n"
             "        if @XS@[@I@] >= @T@:\n"
             "            return @I@\n    return -1"],
         "off-by-one": [
             "def @NAME@(@XS@, @T@):\n"
             "    for @I@ in range(1, len(@XS@)):\n"
             "        if @XS@[@I@] > @T@:\n"
             "            return @I@\n    return -1",
             "def @NAME@(@XS@, @T@):\n"
             "    for @I@ in range(len(@XS@)):\n"
             "        if @XS@[@I@] > @T@:\n"
             "            return @I@ + 1\n    return -1"]},
     "probes": [([1, 9, 4], 5), ([3, 3, 3], 3), ([8, 2], 4)]},
    {"id": "any_below", "kind": "comparison",
     "names_train": ["any_below", "has_under", "some_below"],
     "names_held": ["any_under", "exists_below", "has_dip_under"],
     "params": "@XS@, @T@",
     "correct": "def @NAME@(@XS@, @T@):\n"
                "    for @V@ in @XS@:\n        if @V@ < @T@:\n"
                "            return True\n    return False",
     "mutations": {
         "wrong-operator": [
             "def @NAME@(@XS@, @T@):\n"
             "    for @V@ in @XS@:\n        if @V@ <= @T@:\n"
             "            return True\n    return False",
             "def @NAME@(@XS@, @T@):\n"
             "    for @V@ in @XS@:\n        if @V@ > @T@:\n"
             "            return True\n    return False"],
         "off-by-one": [
             "def @NAME@(@XS@, @T@):\n"
             "    for @V@ in @XS@:\n        if @V@ < @T@ - 1:\n"
             "            return True\n    return False"]},
     "probes": [([5, 9], 5), ([7, 8], 3), ([1, 2], 4)]},
    {"id": "all_above", "kind": "comparison",
     "names_train": ["all_above", "every_over", "all_clear_over"],
     "names_held": ["all_exceeding", "each_above", "every_greater"],
     "params": "@XS@, @T@",
     "correct": "def @NAME@(@XS@, @T@):\n"
                "    for @V@ in @XS@:\n        if @V@ <= @T@:\n"
                "            return False\n    return True",
     "mutations": {
         "wrong-operator": [
             "def @NAME@(@XS@, @T@):\n"
             "    for @V@ in @XS@:\n        if @V@ < @T@:\n"
             "            return False\n    return True",
             "def @NAME@(@XS@, @T@):\n"
             "    for @V@ in @XS@:\n        if @V@ > @T@:\n"
             "            return True\n    return False"],
         "off-by-one": [
             "def @NAME@(@XS@, @T@):\n"
             "    for @V@ in @XS@:\n        if @V@ <= @T@ + 1:\n"
             "            return False\n    return True"]},
     "probes": [([5, 9], 5), ([6, 7], 5), ([9, 4], 3)]},
    # ------------------------------------------------ accumulator
    {"id": "running_total", "kind": "accumulator",
     "names_train": ["running_total", "prefix_sums", "cumulative_sum"],
     "names_held": ["running_sums", "prefix_totals", "cumulated_vals"],
     "params": "@XS@",
     "correct": "def @NAME@(@XS@):\n    @S@ = 0\n    @OUT@ = []\n"
                "    for @V@ in @XS@:\n        @S@ += @V@\n"
                "        @OUT@.append(@S@)\n    return @OUT@",
     "mutations": {
         "wrong-operator": [
             "def @NAME@(@XS@):\n    @S@ = 0\n    @OUT@ = []\n"
             "    for @V@ in @XS@:\n        @S@ -= @V@\n"
             "        @OUT@.append(@S@)\n    return @OUT@"],
         "off-by-one": [
             "def @NAME@(@XS@):\n    @S@ = 0\n    @OUT@ = []\n"
             "    for @V@ in @XS@:\n        @OUT@.append(@S@)\n"
             "        @S@ += @V@\n    return @OUT@"],
         "missing-return": [
             "def @NAME@(@XS@):\n    @S@ = 0\n    @OUT@ = []\n"
             "    for @V@ in @XS@:\n        @S@ += @V@\n"
             "        @OUT@.append(@S@)"]},
     "probes": [([2, 3, 4],), ([5],), ([1, -1, 2],)]},
    {"id": "running_product", "kind": "accumulator",
     "names_train": ["running_product", "prefix_products",
                     "cumulative_prod"],
     "names_held": ["running_prods", "prefix_mults", "cumulated_prod"],
     "params": "@XS@",
     "correct": "def @NAME@(@XS@):\n    @S@ = 1\n    @OUT@ = []\n"
                "    for @V@ in @XS@:\n        @S@ *= @V@\n"
                "        @OUT@.append(@S@)\n    return @OUT@",
     "mutations": {
         "wrong-operator": [
             "def @NAME@(@XS@):\n    @S@ = 1\n    @OUT@ = []\n"
             "    for @V@ in @XS@:\n        @S@ += @V@\n"
             "        @OUT@.append(@S@)\n    return @OUT@"],
         "off-by-one": [
             "def @NAME@(@XS@):\n    @S@ = 1\n    @OUT@ = []\n"
             "    for @V@ in @XS@:\n        @OUT@.append(@S@)\n"
             "        @S@ *= @V@\n    return @OUT@"]},
     "probes": [([2, 3, 4],), ([5],), ([3, 0, 2],)]},
    {"id": "weighted_total", "kind": "accumulator",
     "names_train": ["weighted_total", "dot_total", "weighted_sum"],
     "names_held": ["weighted_grand", "pair_weighted_total",
                    "dot_grand_total"],
     "params": "@XS@, @WS@",
     "correct": "def @NAME@(@XS@, @WS@):\n    @S@ = 0\n"
                "    for @A@, @B@ in zip(@XS@, @WS@):\n"
                "        @S@ += @A@ * @B@\n    return @S@",
     "mutations": {
         "wrong-operator": [
             "def @NAME@(@XS@, @WS@):\n    @S@ = 0\n"
             "    for @A@, @B@ in zip(@XS@, @WS@):\n"
             "        @S@ += @A@ + @B@\n    return @S@"],
         "off-by-one": [
             "def @NAME@(@XS@, @WS@):\n    @S@ = 0\n"
             "    for @A@, @B@ in zip(@XS@[1:], @WS@):\n"
             "        @S@ += @A@ * @B@\n    return @S@"]},
     "probes": [([1, 2, 3], [4, 5, 6]), ([2, 2], [3, 3])]},
    {"id": "sum_squares", "kind": "accumulator",
     "names_train": ["sum_squares", "total_squares", "squares_total"],
     "names_held": ["squared_sum", "sum_of_squares", "sq_total"],
     "params": "@XS@",
     "correct": "def @NAME@(@XS@):\n    @S@ = 0\n"
                "    for @V@ in @XS@:\n        @S@ += @V@ * @V@\n"
                "    return @S@",
     "mutations": {
         "wrong-operator": [
             "def @NAME@(@XS@):\n    @S@ = 0\n"
             "    for @V@ in @XS@:\n        @S@ += @V@ + @V@\n"
             "    return @S@",
             "def @NAME@(@XS@):\n    @S@ = 0\n"
             "    for @V@ in @XS@:\n        @S@ += @V@\n"
             "    return @S@"],
         "missing-return": [
             "def @NAME@(@XS@):\n    @S@ = 0\n"
             "    for @V@ in @XS@:\n        @S@ += @V@ * @V@"]},
     "probes": [([2, 3],), ([4, 5, 6],), ([3],)]},
    {"id": "sum_upto_n", "kind": "accumulator",
     "names_train": ["sum_upto_n", "total_upto_n", "add_upto"],
     "names_held": ["sum_through_n", "grand_upto", "total_through"],
     "params": "@N@",
     # two-accumulator shape — deliberately NOT phase-3's total_upto
     # idiom (a single-accumulator range loop summing 1..n already
     # lives in the phase-3 train templates; partition 2's surfaces
     # must be disjoint in idiom, not just in name)
     "correct": "def @NAME@(@N@):\n    @S@ = 0\n    @N@2 = 0\n"
                "    for @I@ in range(1, @N@ + 1):\n"
                "        @S@ += @I@\n        @N@2 += 1\n"
                "    return @S@",
     "mutations": {
         "wrong-operator": [
             "def @NAME@(@N@):\n    @S@ = 0\n    @N@2 = 0\n"
             "    for @I@ in range(1, @N@ + 1):\n"
             "        @S@ -= @I@\n        @N@2 += 1\n"
             "    return @S@"],
         "off-by-one": [
             "def @NAME@(@N@):\n    @S@ = 0\n    @N@2 = 0\n"
             "    for @I@ in range(1, @N@):\n"
             "        @S@ += @I@\n        @N@2 += 1\n"
             "    return @S@",
             "def @NAME@(@N@):\n    @S@ = 0\n    @N@2 = 0\n"
             "    for @I@ in range(2, @N@ + 1):\n"
             "        @S@ += @I@\n        @N@2 += 1\n"
             "    return @S@"]},
     "probes": [(5,), (1,), (8,)]},
]

_PROBES = {s["id"]: s["probes"] for s in _SPECS}
_KIND = {s["id"]: s["kind"] for s in _SPECS}


# ------------------------------------------------------------ generation
def generate(partition: str) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    names_key = "names_train" if partition == "train" else "names_held"
    out: List[Dict[str, Any]] = []
    stats = {"made": 0}
    for spec in _SPECS:
        for name in spec[names_key]:
            group = f"intent2-{spec['id']}-{name}"
            out.append({"text": _instantiate(spec["correct"],
                                             partition, name),
                        "label": "clean", "group": group,
                        "intent": spec["id"], "kind": "correct",
                        "family": f"name-intent2-{spec['kind']}"})
            stats["made"] += 1
            for cls, templates in spec["mutations"].items():
                for ti, tpl in enumerate(templates):
                    out.append({"text": _instantiate(tpl, partition,
                                                     name),
                                "label": cls, "group": group,
                                "intent": spec["id"],
                                "kind": f"mutation-{cls}-{ti}",
                                "family": f"name-intent2-{spec['kind']}"})
                    stats["made"] += 1
        # neutral controls: the correct body under a neutral name
        for name in NEUTRAL2[:2]:
            out.append({"text": _instantiate(spec["correct"],
                                             partition, name),
                        "label": "clean",
                        "group": f"intent2-{spec['id']}-neutral",
                        "intent": spec["id"], "kind": "control-neutral",
                        "family": f"name-intent2-{spec['kind']}"})
            stats["made"] += 1
    seen, deduped = set(), []
    for it in out:
        if it["text"] in seen:
            continue
        seen.add(it["text"])
        deduped.append(it)
    kept, sstats = _sanity_filter(deduped)
    stats.update(sstats)
    stats["deduped"] = len(deduped)
    stats["kept"] = len(kept)
    return kept, stats


def _sanity_filter(items: List[Dict[str, Any]]) -> Tuple[List[Dict], Dict]:
    """Partition 1's sanity discipline: a clean body must run
    clean on its intent's probes; a mutation must be behaviourally
    distinguished from a same-signature clean body in its group on
    at least one probe."""
    stats = {"dropped_broken_correct": 0, "dropped_noop_mutation": 0}
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for it in items:
        groups.setdefault(it["group"], []).append(it)
    kept: List[Dict[str, Any]] = []
    for it in items:
        probes = _PROBES[it["intent"]]
        if it["label"] == "clean":
            if not _runs_clean(it["text"], probes):
                stats["dropped_broken_correct"] += 1
                continue
            kept.append(it)
            continue
        sig = it["text"].split("):")[0]
        cands = [c for c in groups[it["group"]]
                 if c["label"] == "clean"
                 and c["text"].split("):")[0] == sig]
        if cands and not any(_distinguishes(c["text"], it["text"],
                                            probes) for c in cands):
            stats["dropped_noop_mutation"] += 1
            continue
        kept.append(it)
    for it in kept:
        it["sanity"] = "passed"
    return kept, stats


# ------------------------------------------------------------ verification
def verify_items(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Independent execution re-verification of a written
    partition: every clean item runs clean on its probes; every
    defect item differs behaviourally from a same-signature clean
    group-mate on at least one probe. (Labels themselves are
    construction-known — this proves the items are not degenerate,
    exactly the claim partition 1's sanity pass makes.)"""
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for it in items:
        groups.setdefault(it["group"], []).append(it)
    checked = {"clean": 0, "defect": 0}
    failures: List[str] = []
    for it in items:
        probes = _PROBES[it["intent"]]
        if it["label"] == "clean":
            checked["clean"] += 1
            if not _runs_clean(it["text"], probes):
                failures.append(f"clean does not run clean: "
                                f"{it['group']} {it['kind']}")
            continue
        checked["defect"] += 1
        sig = it["text"].split("):")[0]
        cands = [c for c in groups[it["group"]]
                 if c["label"] == "clean"
                 and c["text"].split("):")[0] == sig]
        if not cands or not any(_distinguishes(c["text"], it["text"],
                                               probes) for c in cands):
            failures.append(f"defect indistinguishable from correct: "
                            f"{it['group']} {it['kind']}")
    return {"checked": checked, "failures": failures,
            "ok": not failures}


# ------------------------------------------------------------ assembly
def _name_shape(text: str) -> Tuple[str, str]:
    from swarm import factory as F
    m = re.search(r"def\s+(\w+)", text)
    return (m.group(1) if m else "",
            re.sub(r"\s+", " ", F._anonymize_code(text).strip().lower()))


def build_datasets() -> Dict[str, Any]:
    """Generate both partitions, contamination-filter against all
    corpora AND partition 1 (same discipline as partition 1's
    build), verify by execution, and write the files + manifest."""
    from swarm import dream as swarm_dream
    from swarm import phase3 as P3

    from . import dream_gen as G
    from . import name_intent as ni1
    from .executors import contamination_filter

    train_raw, train_stats = generate("train")
    held_raw, held_stats = generate("held")

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
        corpora["name_intent1_train"] = ni1.load_train()
        corpora["name_intent1_held"] = ni1.load_held()
    except Exception:  # noqa: BLE001
        corpora["name_intent1_train"] = []
        corpora["name_intent1_held"] = []
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

    gate_pairs = {_name_shape(r["text"])
                  for r in corpora["phase3_held"]}
    gate_pairs |= {_name_shape(r["text"])
                   for r in corpora["name_intent1_held"]}
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

    # Orphan pass: contamination wins — if a group's clean items
    # were all filtered out, its defect items are orphans (their
    # judge value depended on the correct body they break) and are
    # dropped with them, counted here rather than hidden.
    def drop_orphans(items):
        clean_groups = {it["group"] for it in items
                        if it["label"] == "clean"}
        kept = [it for it in items
                if it["label"] == "clean" or it["group"] in clean_groups]
        return kept, len(items) - len(kept)

    train_clean, n_orphan_train = drop_orphans(train_clean)
    held_clean, n_orphan_held = drop_orphans(held_clean)

    ver_train = verify_items(train_clean)
    ver_held = verify_items(held_clean)
    if not (ver_train["ok"] and ver_held["ok"]):
        raise RuntimeError(
            f"name-intent2 verification failed: "
            f"train={ver_train['failures'][:3]} "
            f"held={ver_held['failures'][:3]}")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "name_intent2_train.json").write_text(
        json.dumps(train_clean, indent=1, ensure_ascii=False))
    (DATA_DIR / "name_intent2_held.json").write_text(
        json.dumps(held_clean, indent=1, ensure_ascii=False))

    def dist(items):
        d: Dict[str, int] = {}
        for it in items:
            d[it["label"]] = d.get(it["label"], 0) + 1
        return d

    def intents(items):
        d: Dict[str, int] = {}
        for it in items:
            d[it["intent"]] = d.get(it["intent"], 0) + 1
        return d

    manifest = {
        "family": "name-intent partition 2 (comparison/accumulator)",
        "partitions": {
            "train": {"file": "name_intent2_train.json",
                      "raw_stats": train_stats,
                      "after_contamination": len(train_clean),
                      "dropped_contamination": len(train_dropped),
                      "label_dist": dist(train_clean),
                      "intent_dist": intents(train_clean),
                      "verification": ver_train},
            "held": {"file": "name_intent2_held.json",
                     "raw_stats": held_stats,
                     "after_contamination": len(held_clean),
                     "dropped_contamination": len(held_dropped),
                     "label_dist": dist(held_clean),
                     "intent_dist": intents(held_clean),
                     "verification": ver_held},
        },
        "intents": {s["id"]: s["kind"] for s in _SPECS},
        "partition_rules": [
            "intent ids, function names, identifier vocabulary and "
            "neutral names all DISJOINT from partition 1",
            "comparison intents use loop + if-line idioms (they "
            "slice as 'comparison'); accumulator intents use += / "
            "*= loop idioms with no if-comparison line (they slice "
            "as 'accumulator') under swarm.decomposers.slice_of",
            "held is a judge surface only: never trained on; "
            "training pools must be contamination-filtered against "
            "it (the growth runner does this for any pool it "
            "builds once cycle 3 wires it in)",
            "contamination filter mode is TEXT (name-preserving), "
            "as partition 1; plus the (name, anonymized-shape) "
            "guard against the phase-3 held gate AND partition "
            "1's held partition",
        ],
        "name_shape_guard_drops": n_guard,
        "orphaned_defect_drops": {"train": n_orphan_train,
                                  "held": n_orphan_held},
        "corpora_filtered_against": {k: len(v) for k, v in
                                     corpora.items()},
        "labels": "construction-known (declared name intent vs "
                  "body), NOT execution-verified as labels; every "
                  "written item passed the execution sanity + "
                  "re-verification pass (clean runs clean; defects "
                  "behaviourally distinguishable from correct)",
    }
    (DATA_DIR / "name_intent2_manifest.json").write_text(
        json.dumps(manifest, indent=1, ensure_ascii=False))
    return manifest


def load_train() -> List[Dict[str, Any]]:
    return json.loads((DATA_DIR / "name_intent2_train.json").read_text())


def load_held() -> List[Dict[str, Any]]:
    return json.loads((DATA_DIR / "name_intent2_held.json").read_text())


if __name__ == "__main__":
    m = build_datasets()
    print(json.dumps(m, indent=1, ensure_ascii=False))
