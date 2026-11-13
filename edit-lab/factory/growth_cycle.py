"""The GROWTH RUNNER (2026-11-11, Arnav's authorization: "Make urs
keep growing and getting smarter and better too, learn from Fable
or better ways if needed, improvise if needed").

One invocable command runs one full growth cycle end to end:

    python3 -m factory.growth_cycle [--cycle-id growth-cycle-001]

  1. HARVEST the served hive's current measured failures
     (training-side surfaces: the parents' misses on the phase-3
     train slices and the name-intent train slices, by intent).
  2. GENERATE data: the existing supplies (phase-3 templates +
     execution-verified dream pool) plus the NAME-INTENT family
     (factory/name_intent.py — labels from declared name intent,
     the signal class the assembly proved the dream supply cannot
     express).
  3. TRAIN candidates per target slice under two arms competing
     under identical gates: from-scratch (the legacy sweep) and
     PARENT-INITIALIZED fine-tuning (Lever 2 — births inherit the
     parent's weights; the diet is slice + name-intent + a replay
     slice of the full distribution). Diets are failure-weighted
     (found-on-failure, borrowed from Fable: items the parent
     gets wrong count double).
  4. JUDGE on pristine surfaces only: the phase-3 held slice (the
     standing birth gate) AND the name-intent held slice (new
     pristine judge) — both strict, child must beat parent on
     both. Training distributions are never judge surfaces.
  5. ADOPT only through the standing law: a passed dual gate
     writes the child + routes its slice; Gate 3′ (2026-11-12,
     from the E-007 retro-check) then judges the FULL serving
     path on the say_dev pool — composer + the waking-dream
     refresh a birth triggers, child vs parent — and blocks the
     birth pre-adoption on any served total fall or a >=1-item
     served clean-recall fall, restoring the child's two files
     in place (no rollback involved); then the WHOLE is
     verified — registry rebuilt, the acceptance battery
     re-measured through the serving path, the full audit run.
     Any battery slice regression or audit failure ROLLS THE
     CYCLE'S BIRTHS BACK (files removed, config and evidence
     restored) and records the removal with its reason. Kept
     only if the whole improves: Fable's discipline, our gates.
  6. REPORT to edit-lab/growth/: <cycle>.md + <cycle>.json and an
     append-only ledger line. Removals at birth are normal and
     are reported as plainly as births.

Also measured (not adopted) each cycle: the LEARNED-SAY check —
whether learned per-representation margin weights beat the
composer's current routed rule, fitted on train, judged on the
phase-3 held set. Adoption of a composition-rule change is a
separate gated step (cycle 2 candidate); this cycle only brings
the numbers.

The sealed v2 set is touched only the way the audit touches it:
re-measured after an adoption decision to record the new standing
numbers (the growth judge file the registry's evidence chain
reads). It is never trained on and never selects candidates.

CRON MODE (2026-11-11, the cycle-2 report's four blockers, fixed):
invoked with no --cycle-id, the runner derives the next id from
the ledger, takes a single-instance lock, SKIPS cleanly (ledger
line, exit 0, nothing trained) when another cycle or a heavy lab
job is already running, rotates its candidate grid + data
partitions keyed by cycle number (deterministic training would
otherwise re-prove the same candidates every turn), and writes
growth/ALERT-<cycle>.md on rollback or audit failure. Explicit
--cycle-id invocations keep the exact cycle-1/2 behaviour.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")

LAB_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(LAB_ROOT / "coding"))
sys.path.insert(0, str(LAB_ROOT))

from swarm import composers as C  # noqa: E402
from swarm import decomposers as D  # noqa: E402
from swarm import factory as F  # noqa: E402
from swarm import phase3 as P3  # noqa: E402

from . import growth  # noqa: E402
from . import name_intent  # noqa: E402
from .executors import _atomic_json, measure  # noqa: E402
from .lineage import LineageLog  # noqa: E402

FACTORY_DIR = Path(__file__).parent
MODELS_DIR = LAB_ROOT / "coding" / "swarm" / "models"
GROWTH_DIR = LAB_ROOT / "growth"
TARGETS = [("wrong-operator", "expression"), ("off-by-one", "index")]
INTENT_CAP_POS = 120
INTENT_CAP_NEG = 160

# Cron readiness (cycle 3 prep, 2026-11-11): the four changes the
# cycle-2 report named before this runner may be scheduled.
LEDGER_PATH = GROWTH_DIR / "ledger.jsonl"
LOCK_PATH = GROWTH_DIR / ".growth.lock"
LOCK_STALE_SECONDS = 2 * 3600


# ------------------------------------------------------------ battery
def measure_served_battery(run_dir: Path, tag: str) -> Dict[str, Any]:
    """The acceptance battery's Tier-0 sections (a1/a1b/a1c/a2)
    through the serving path, written to a cycle-local file.
    Composites b1-b6 need the Tier-1 LM backend and are not part
    of a growth cycle's gate (the cycle changes no Tier-1 state)."""
    from . import run_battery
    out_path = Path(run_dir) / f"battery_{tag}.json"
    if out_path.exists():
        out_path.unlink()
    run_battery.OUT = out_path
    run_battery.part_a1()
    run_battery.part_a1b()
    run_battery.part_a1c()
    run_battery.part_a2()
    doc = json.loads(out_path.read_text())
    return {task: {"score": e["score"], "status": e["status"],
                   "detail": e["detail"]}
            for task, e in doc["results"].items()}


def _battery_regressions(before: Dict[str, Any],
                         after: Dict[str, Any]) -> List[str]:
    out = []
    for task, b in before.items():
        a = after.get(task)
        if a is None:
            out.append(f"{task}: missing after adoption")
        elif a["score"] < b["score"] - 1e-9:
            out.append(f"{task}: {b['score']} -> {a['score']}")
    return out


# ------------------------------------------------------------ data
def cap_intent(items: List[Dict[str, Any]], cls: str, slice_name: str,
               seed: int = 99,
               pos_cap: Optional[int] = None,
               neg_cap: Optional[int] = None) -> List[Dict[str, Any]]:
    """The name-intent slice contribution to a child's diet,
    stratified-capped so the new signal leans in without drowning
    the slice's own distribution (the assembly's dilution lesson).
    Multiclass items in, multiclass items out (attempt_birth
    relabels). pos_cap/neg_cap default to the cycle-1 caps; cycle 2
    raises them in one variant to test intent-slice supply."""
    import random
    sub = growth._slice_subset(items, cls, slice_name)
    pos = [e for e in sub if e["label"] == cls]
    neg = [e for e in sub if e["label"] != cls]
    rng = random.Random(seed)
    rng.shuffle(pos)
    rng.shuffle(neg)
    return pos[:INTENT_CAP_POS if pos_cap is None else pos_cap] + \
        neg[:INTENT_CAP_NEG if neg_cap is None else neg_cap]


def replay_set() -> List[Dict[str, Any]]:
    """The parent-distribution replay for the init arm: the phase-3
    template train set + the swarm's dream corpus — the surfaces
    the parent family actually learned from."""
    from swarm import dream as swarm_dream
    return P3.gen_bug_patterns(P3._BUG_TEMPLATES_TRAIN, 21) + \
        swarm_dream.gen_dream_bug_examples()


# ------------------------------------------------------------ harvest
def harvest_failures(intent_train: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Where the serving parents measurably fail, on training-side
    surfaces (never judge surfaces): per target slice, the
    parent's misses on the phase-3 train slice and on the
    name-intent train slice, the latter broken down by intent."""
    from . import dream as dream_mod
    reg = dream_mod.load_bug_registry()
    multi_train = P3.gen_bug_patterns(P3._BUG_TEMPLATES_TRAIN, 21)
    out: Dict[str, Any] = {}
    for cls, slice_name in TARGETS:
        parent = reg[f"bug-{cls}-model"]
        rows: Dict[str, Any] = {}
        for surf_name, surf in (
                ("phase3_train_slice",
                 growth._relabel(growth._slice_subset(
                     multi_train, cls, slice_name), cls)),
                ("intent_train_slice",
                 growth._relabel(growth._slice_subset(
                     intent_train, cls, slice_name), cls))):
            m = measure(parent, surf)
            by_intent: Dict[str, int] = {}
            if surf_name == "intent_train_slice":
                sub = growth._slice_subset(intent_train, cls,
                                           slice_name)
                for e in sub:
                    got = parent.run({"text": e["text"]})["output"]
                    want = cls if e["label"] == cls else "other"
                    if got != want:
                        by_intent[e.get("intent", "?")] = \
                            by_intent.get(e.get("intent", "?"), 0) + 1
            rows[surf_name] = {"acc": m["acc"], "n": m["n"],
                               "wrong_n": len(m["wrong"]),
                               "wrong_by_intent": by_intent}
        out[f"{cls}/{slice_name}"] = rows
    return out


# ------------------------------------------------------------ learned say
def learned_say_experiment() -> Dict[str, Any]:
    """Borrowed check (Fable: "the say of each member is learned —
    the body stops being winner-takes-all"). Our composer routes
    each class to ONE representation (variant -> slice -> whole).
    Three rules are compared on the phase-3 held set (a spent
    confirm surface — measurement only, labeled as such):
      routed   the serving rule (composer_config as it stands)
      mean     the mean margin of every adopted representation
      learned  per-class weights over representations, fitted by
               coordinate ascent on the phase-3 TRAIN set
    Adoption is NOT decided here: a composition-rule change is a
    serving change and goes through the battery gate as its own
    step; this experiment brings the numbers."""
    from . import dream as dream_mod
    reg = dream_mod.load_bug_registry()
    multi_train = P3.gen_bug_patterns(P3._BUG_TEMPLATES_TRAIN, 21)
    multi_held = P3.gen_bug_patterns(P3._BUG_TEMPLATES_HELD, 22)
    config = C.load_config()
    thresholds = config.get("thresholds", {})
    rep_names = {}
    for cls in C.DEFECT_CLASSES:
        reps = [n for n in (f"bug-{cls}-model", f"bug-{cls}-named-model",
                            f"bug-{cls}-harvest-model",
                            f"bug-{cls}-indexlit-model") if n in reg]
        rep_names[cls] = reps

    def rep_margins(code):
        return {cls: {n: C._model_margin(reg[n], code, cls)
                      for n in rep_names[cls]}
                for cls in C.DEFECT_CLASSES if rep_names[cls]}

    def verdict(margins_by_cls):
        adj = {c: m - thresholds.get(c, 0.0)
               for c, m in margins_by_cls.items()}
        if not adj:
            return "clean"
        best = max(adj, key=adj.get)
        return best if adj[best] > 0 else "clean"

    def routed_margins(code):
        return C.class_margins(reg, code, config)

    def mean_margins(code):
        rm = rep_margins(code)
        return {c: sum(d.values()) / len(d) for c, d in rm.items()}

    # fit learned weights per class on TRAIN (binary sign accuracy)
    weights: Dict[str, Dict[str, float]] = {}
    for cls in C.DEFECT_CLASSES:
        reps = rep_names[cls]
        if not reps:
            continue
        w = {n: 1.0 for n in reps}
        train_rows = []
        for e in multi_train:
            rm = rep_margins(e["text"])[cls]
            train_rows.append((rm, cls if e["label"] == cls
                               else "other"))

        def acc_with(wv):
            right = 0
            for rm, want in train_rows:
                s = sum(wv[n] * rm[n] for n in reps) \
                    - thresholds.get(cls, 0.0)
                got = cls if s > 0 else "other"
                right += got == want
            return right / len(train_rows) if train_rows else 0.0

        best_acc = acc_with(w)
        for _ in range(2):
            for n in reps:
                for cand in (0.0, 0.25, 0.5, 1.0, 2.0):
                    old = w[n]
                    w[n] = cand
                    a = acc_with(w)
                    if a > best_acc:
                        best_acc = a
                    else:
                        w[n] = old
        weights[cls] = w

    def learned_margins(code):
        rm = rep_margins(code)
        out = {}
        for c, d in rm.items():
            w = weights.get(c)
            if not w:
                out[c] = sum(d.values()) / len(d)
                continue
            tot = sum(w[n] for n in d)
            out[c] = (sum(w[n] * d[n] for n in d) / tot) if tot else 0.0
        return out

    results = {}
    for rule_name, fn in (("routed", routed_margins),
                          ("mean", mean_margins),
                          ("learned", learned_margins)):
        right = sum(1 for e in multi_held
                    if verdict(fn(e["text"])) == e["label"])
        results[rule_name] = round(right / len(multi_held), 4)
    return {"judged_on": "phase-3 held set (spent confirm surface "
                          "— measurement only, NOT pristine)",
            "n": len(multi_held), "composed_acc": results,
            "learned_weights": weights,
            "adoption": "not decided in this cycle — a composition-"
                        "rule change is a serving change and takes "
                        "its own battery-gated step"}


# ------------------------------------------------ learned say v2
def learned_say_experiment_v2() -> Dict[str, Any]:
    """Cycle 2's materially different fit (cycle 1's fit tied the
    incumbent exactly, 0.7931 vs routed 0.8276, and is NOT repeated
    as-is). What changed:
      * the objective is the SERVING objective — composed
        multiclass accuracy on the phase-3 train set — not cycle
        1's per-class binary sign accuracy fitted class by class;
      * the search is JOINT: per-class representation weights AND
        a per-class threshold multiplier are fitted together by
        coordinate ascent, because a class's say and its firing
        threshold trade off against each other in the composed
        verdict.
    Judged on the same spent surface as cycle 1 (phase-3 held,
    measurement only). Adoption remains a separate battery-gated
    step; this experiment only earns or fails to earn that step."""
    from . import dream as dream_mod
    reg = dream_mod.load_bug_registry()
    multi_train = P3.gen_bug_patterns(P3._BUG_TEMPLATES_TRAIN, 21)
    multi_held = P3.gen_bug_patterns(P3._BUG_TEMPLATES_HELD, 22)
    config = C.load_config()
    thresholds = config.get("thresholds", {})
    rep_names = {}
    for cls in C.DEFECT_CLASSES:
        reps = [n for n in (f"bug-{cls}-model", f"bug-{cls}-named-model",
                            f"bug-{cls}-harvest-model",
                            f"bug-{cls}-indexlit-model") if n in reg]
        rep_names[cls] = reps

    def rep_margins(code):
        return {cls: {n: C._model_margin(reg[n], code, cls)
                      for n in rep_names[cls]}
                for cls in C.DEFECT_CLASSES if rep_names[cls]}

    # cache margins once; the ascent itself is pure arithmetic
    train_cache = [(rep_margins(e["text"]), e["label"])
                   for e in multi_train]
    held_cache = [(rep_margins(e["text"]), e["label"])
                  for e in multi_held]

    def verdict(margins_by_cls, tmult=None):
        adj = {}
        for c, m in margins_by_cls.items():
            t = thresholds.get(c, 0.0)
            if tmult is not None:
                t = t * tmult.get(c, 1.0)
            adj[c] = m - t
        if not adj:
            return "clean"
        best = max(adj, key=adj.get)
        return best if adj[best] > 0 else "clean"

    def mean_margins(rm):
        return {c: sum(d.values()) / len(d) for c, d in rm.items()}

    classes = [c for c in C.DEFECT_CLASSES if rep_names[c]]
    weights: Dict[str, Dict[str, float]] = {
        c: {n: 1.0 for n in rep_names[c]} for c in classes}
    tmult: Dict[str, float] = {c: 1.0 for c in classes}

    def learned_margins(rm, w, tm):
        out = {}
        for c, d in rm.items():
            wv = w.get(c)
            if not wv:
                out[c] = sum(d.values()) / len(d)
                continue
            tot = sum(wv[n] for n in d)
            out[c] = (sum(wv[n] * d[n] for n in d) / tot) if tot \
                else 0.0
        return out

    def composed_acc(cache, w, tm):
        right = sum(1 for rm, label in cache
                    if verdict(learned_margins(rm, w, tm), tm) == label)
        return right / len(cache) if cache else 0.0

    best_train = composed_acc(train_cache, weights, tmult)
    w_cands = (0.0, 0.25, 0.5, 1.0, 2.0)
    t_cands = (0.5, 0.75, 1.0, 1.25, 1.5)
    for _ in range(2):
        for c in classes:
            for n in rep_names[c]:
                cur = weights[c][n]
                for cand in w_cands:
                    if cand == cur:
                        continue
                    weights[c][n] = cand
                    a = composed_acc(train_cache, weights, tmult)
                    if a > best_train:
                        best_train = a
                        cur = cand
                    else:
                        weights[c][n] = cur
            cur_t = tmult[c]
            for cand in t_cands:
                if cand == cur_t:
                    continue
                tmult[c] = cand
                a = composed_acc(train_cache, weights, tmult)
                if a > best_train:
                    best_train = a
                    cur_t = cand
                else:
                    tmult[c] = cur_t

    def acc_on(cache, fn):
        right = sum(1 for rm, label in cache if fn(rm) == label)
        return round(right / len(cache), 4) if cache else 0.0

    # the routed (serving) rule, exactly as cycle 1 measured it:
    # composer class_margins + the plain-threshold verdict
    routed_right = sum(
        1 for e in multi_held
        if verdict(C.class_margins(reg, e["text"], config))
        == e["label"])
    results = {
        "routed": round(routed_right / len(multi_held), 4),
        "mean": acc_on(held_cache, lambda rm: verdict(mean_margins(rm))),
        "learned": acc_on(
            held_cache,
            lambda rm: verdict(learned_margins(rm, weights, tmult),
                               tmult)),
    }
    return {"judged_on": "phase-3 held set (spent confirm surface "
                          "— measurement only, NOT pristine)",
            "n": len(multi_held),
            "fit": "v2 (cycle 2): joint coordinate ascent on "
                   "COMPOSED train accuracy over per-class "
                   "representation weights and per-class threshold "
                   "multipliers; cycle 1 fitted per-class binary "
                   "sign accuracy, weights only",
            "train_composed_acc_learned": round(best_train, 4),
            "composed_acc": results,
            "learned_weights": weights,
            "threshold_multipliers": tmult,
            "adoption": "not decided in this cycle — a composition-"
                        "rule change is a serving change and takes "
                        "its own battery-gated step"}


# ------------------------------------------------- serving verification
def _refresh_waking_dream_results(cycle_id: str) -> Dict[str, Any]:
    """After an adopted birth, the waking-dream layer's sealed
    record (waking-dream/results.json, which the registry reads)
    must be re-measured over the CURRENT members — the audit
    re-measures it and compares. Same shaping as the lab's
    run_judge.py; the pre-growth values are preserved in the file
    under growth_refresh."""
    from . import bug_heldout_v2 as bh
    from . import dream as dream_mod
    sealed = bh.load_sealed()
    wd_dir = str(LAB_ROOT / "waking-dream")
    if wd_dir not in sys.path:
        sys.path.insert(0, wd_dir)
    import waking_dream as wd_mod
    results_path = LAB_ROOT / "waking-dream" / "results.json"
    previous = json.loads(results_path.read_text())
    reg = dream_mod.load_bug_registry()
    wrapper = wd_mod.WakingDream(registry=reg,
                                 config=C.load_config())
    res = wd_mod.evaluate(wrapper, sealed["items"])
    rows = res.pop("rows")
    totals = sorted(r["total_ms"] for r in rows)
    p95 = totals[int(0.95 * len(totals)) - 1] if totals else 0.0
    res["latency_ms"]["wrapper_p95"] = round(p95, 2)
    res["latency_ms"]["added_mean"] = round(
        res["latency_ms"]["wrapper_mean"]
        - res["latency_ms"]["composer_mean"], 2)
    ver_activity: Dict[str, Any] = {}
    for r in rows:
        for a in r["attempts"]:
            d = ver_activity.setdefault(
                a["cls"], {"tried": 0, "verified": 0})
            d["tried"] += 1
            d["verified"] += a["verified"]
    out = {
        "subject": previous.get("subject"),
        "sealed_file": previous.get("sealed_file"),
        "sealed_sha256": sealed["sha256"],
        "n": res["n"],
        "baseline_composed_acc": res["composer_acc"],
        "baseline_per_class_recall": res["composer_per_class_recall"],
        "composer_acc_same_pass": res["composer_acc"],
        "composer_per_class_recall_same_pass":
            res["composer_per_class_recall"],
        "waking_dream": res,
        "verification_activity": ver_activity,
        "win_bar_preregistered": previous.get("win_bar_preregistered"),
        "win": res["acc"] >= (previous.get("win_bar_preregistered")
                              or 0.65) and res["verified"]["n"] > 0,
        "growth_refresh": {
            "cycle_id": cycle_id,
            "reason": "composition membership changed (adopted "
                      "birth); the layer's sealed record re-measured "
                      "over the current members, post-decision",
            "previous_baseline_composed_acc":
                previous.get("baseline_composed_acc"),
            "previous_waking_dream_acc":
                (previous.get("waking_dream") or {}).get("acc"),
        },
        "cases": [
            {"label": r["label"], "answer": r["answer"],
             "composer": r["composer"], "mechanism": r["mechanism"],
             "verified_cls": r["verified_cls"],
             "climb_depth": r["climb_depth"], "correct": r["correct"],
             "attempts": [{"cls": a["cls"], "verified": a["verified"],
                           "score": a["score"],
                           "evidence": a["evidence"]}
                          for a in r["attempts"]]}
            for r in rows],
    }
    _atomic_json(results_path, out)
    return {"acc": res["acc"], "raw_composed_acc": res["composer_acc"],
            "per_class_recall": res["per_class_recall"]}


def _sealed_judge(cycle_id: str, previous_acc: Optional[float]) -> Dict[str, Any]:
    """The growth judge file: the raw composition's sealed
    measurement after an adoption, in the shape registry.
    _sealed_evidence reads (composed_acc, per_class_recall,
    cycle_id)."""
    from . import bug_heldout_v2 as bh
    from . import dream as dream_mod
    sealed = bh.load_sealed()
    reg = dream_mod.load_bug_registry()
    acc, recalls = dream_mod.composed_eval(reg, sealed["items"])
    doc = {"cycle_id": cycle_id,
           "fix_cycle": cycle_id,
           "composed_acc": acc,
           "per_class_recall": recalls,
           "n": len(sealed["items"]),
           "previous_acc": previous_acc,
           "measured_via": "factory.growth_cycle post-adoption judge "
                           "(the audit's own measurement path); the "
                           "sealed set was never trained on and "
                           "never selected candidates"}
    path = LAB_ROOT / "results" / f"bug_heldout_v2_growth-{cycle_id}.json"
    _atomic_json(path, doc)
    return doc


def _full_audit() -> Dict[str, Any]:
    from . import audit as audit_mod
    from .registry import load_registry
    res = audit_mod.full_audit(load_registry())
    return {"ok": res["ok"], "failures": res["failures"],
            "score_checks": res["score_checks"]}


# ------------------------------------------------- model-file snapshots
def _target_child_names() -> List[str]:
    """The serving model names a cycle's births can touch: one
    child per target, named by factory/growth.py's convention."""
    return [f"bug-{cls}-{slice_name}-model"
            for cls, slice_name in TARGETS]


def _snapshot_model_files(names: List[str]) -> Dict[str, Any]:
    """Bytes of each named serving model file, or None where the
    file does not exist yet. Taken BEFORE any birth attempt: a
    birth overwrites the previous cycle's serving file of the
    same name, so the pre-cycle bytes are the only copy of the
    incumbent specialist. (Cycle-006 repair, 2026-11-12: rollback
    used to unlink the child files outright, which — because the
    birth had already overwritten the incumbents — deleted the
    serving specialists instead of restoring them.)"""
    out: Dict[str, Any] = {}
    for name in names:
        p = MODELS_DIR / f"{name}.json"
        out[name] = p.read_bytes() if p.exists() else None
    return out


def _restore_model_files(
        born: List[Dict[str, Any]],
        model_snapshots: Optional[Dict[str, Any]]) -> List[str]:
    """Undo a cycle's model-file writes. A child whose name has
    pre-cycle bytes in the snapshot gets those bytes back
    byte-for-byte; a genuinely new child file is removed.
    Returns the names restored from snapshot."""
    restored: List[str] = []
    for b in born:
        name = b["child"]
        p = MODELS_DIR / f"{name}.json"
        snap = (model_snapshots or {}).get(name)
        if snap is not None:
            p.write_bytes(snap)
            restored.append(name)
        elif p.exists():
            p.unlink()
    return restored


# ------------------------------------------------------------ rollback
def _rollback(born: List[Dict[str, Any]], snapshots: Dict[str, bytes],
              cycle_id: str, lineage: LineageLog,
              reason: str,
              model_snapshots: Optional[Dict[str, Any]] = None
              ) -> None:
    """Remove the cycle's births and restore every file they
    touched. Model files are restored from the pre-cycle
    snapshot (see _snapshot_model_files): a birth that overwrote
    an incumbent specialist must never become a deletion of it.
    The lineage keeps the whole story (append-only);
    nothing about the attempt is hidden."""
    restored = _restore_model_files(born, model_snapshots)
    (MODELS_DIR / "composer_config.json").write_bytes(
        snapshots["composer_config"])
    wd_path = LAB_ROOT / "waking-dream" / "results.json"
    wd_path.write_bytes(snapshots["waking_dream_results"])
    judge = LAB_ROOT / "results" / f"bug_heldout_v2_growth-{cycle_id}.json"
    if judge.exists():
        judge.unlink()
    from .registry import write_registry
    write_registry()
    lineage.append("growth_rollback", cycle_id=cycle_id, reason=reason,
                   removed=[b["child"] for b in born
                            if b["child"] not in restored],
                   restored=restored)


# ------------------------------------------------------------ Gate 3′
# Gate 3′ (2026-11-12, from the E-007 retro-check —
# factory/reports/e007-retrocheck-2026-11-12.md). E-007 proposed a
# third gate on the RAW composer's dev total; the retro-check
# REFUTED it on the cycle-6/7 records: on every composed surface
# anyone measured, the raw totals never fell (sealed raw 0.4722 ->
# 0.4722 in cycle 6; 0.5 -> 0.5 in cycle 7). Both regressions
# lived one layer down, in the waking-dream refresh a birth
# triggers: the entire serving fall was clean recall (cycle 6:
# clean 0.8182 -> 0.6364, -2 items; cycle 7: -1 item) while every
# defect class stood still. Gate 3′ judges that layer: per child,
# after the dual pristine gate passes and BEFORE the cycle's
# registry rewrite makes the birth final, the FULL serving path
# (composer + the waking-dream refresh, run in-memory over the
# say_dev 216 pool — dev, never the sealed set) is measured with
# the child installed and with the parent composition restored
# in-memory, and the birth is blocked on any served total fall
# OR a served clean-recall fall of >= 1 dev item, even when the
# total is flat or rising (a compensated clean loss is the
# demonstrated failure signature).
#
# A blocked child is un-born in place: attempt_birth writes
# exactly two serving files (the child model + composer_config
# routing), and the gate restores both from byte snapshots taken
# immediately before the attempt. registry.json and
# waking-dream/results.json are never written for a blocked
# child, so no rollback path is involved (rollback remains only
# for post-adoption verification failures of KEPT births).
# Targets are gated independently: each child's parent scorecard
# is measured against the composition current at its own gate,
# so a sibling birth already kept in the same cycle is part of
# the next child's parent state.
#
# Bookkeeping (retro-check §5, so the next retro-check is
# computable): the child's model bytes are snapshotted into the
# run dir (gate3/<child>.json, sha256 recorded) BEFORE the gate
# decides, kept or blocked; both scorecards — served totals,
# served per-class recalls AND the raw composed per-class
# recalls before (parent) and after (child) — land on the
# attempt record and in lineage.

_GATE3_DEV_ITEMS: Optional[List[Dict[str, Any]]] = None


def _gate3_dev_items() -> List[Dict[str, Any]]:
    global _GATE3_DEV_ITEMS
    if _GATE3_DEV_ITEMS is None:
        from . import say_dev
        _GATE3_DEV_ITEMS = say_dev.load_dev_pool()["items"]
    return _GATE3_DEV_ITEMS


def _gate3_pre_state(child_name: str) -> Dict[str, Any]:
    """Byte snapshots of exactly what a birth for this target
    can write, taken immediately BEFORE the attempt: the child
    model file (None if no incumbent file of that name exists)
    and composer_config.json."""
    p = MODELS_DIR / f"{child_name}.json"
    return {"child_name": child_name,
            "child_bytes": p.read_bytes() if p.exists() else None,
            "config_bytes": (MODELS_DIR / "composer_config.json")
            .read_bytes()}


def _gate3_registry(child_name: str,
                    child_bytes: Optional[bytes]) -> Dict[str, Any]:
    """dream.load_bug_registry with one member's bytes
    substituted — the in-memory sandbox the parent scorecard is
    measured in. child_bytes None = the member was absent
    before the attempt, so it is absent from the parent
    composition too."""
    reg: Dict[str, Any] = {}
    for f in sorted(MODELS_DIR.glob("bug-*.json")):
        if f.stem == child_name:
            if child_bytes is None:
                continue
            rec = json.loads(child_bytes.decode())
        else:
            rec = json.loads(f.read_text())
        if rec.get("adopted"):
            reg[rec["name"]] = F.TinyNet.from_record(rec)
    return reg


def _gate3_scorecard(reg: Dict[str, Any], config: Dict[str, Any],
                     items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """One serving-path pass over the dev pool: the waking-dream
    wrapper exactly as production runs it (same WakingDream +
    evaluate as _refresh_waking_dream_results, but in-memory —
    nothing is written). evaluate's rows carry the bare
    composer's verdict per item, so the raw composed leg is the
    same pass's by-product (diagnostic only, per the spec)."""
    wd_dir = str(LAB_ROOT / "waking-dream")
    if wd_dir not in sys.path:
        sys.path.insert(0, wd_dir)
    import waking_dream as wd_mod
    wrapper = wd_mod.WakingDream(registry=reg, config=config)
    res = wd_mod.evaluate(wrapper, items)
    rows = res["rows"]

    def counts(key: str) -> Dict[str, Dict[str, int]]:
        per: Dict[str, Dict[str, int]] = {}
        for r in rows:
            d = per.setdefault(r["label"], {"n": 0, "right": 0})
            d["n"] += 1
            d["right"] += 1 if r[key] else 0
        return per

    served = counts("correct")
    raw = counts("composer_correct")
    return {"n": res["n"],
            "served_acc": res["acc"],
            "served_right": sum(d["right"] for d in served.values()),
            "served_per_class_recall": res["per_class_recall"],
            "served_per_class": served,
            "raw_acc": res["composer_acc"],
            "raw_right": sum(d["right"] for d in raw.values()),
            "raw_per_class_recall": res["composer_per_class_recall"],
            "raw_per_class": raw}


def _gate3_verdict(child_card: Dict[str, Any],
                   parent_card: Dict[str, Any]) -> Optional[str]:
    """Block reason, or None to keep the birth. Judged in exact
    item counts on the SERVED path (same pool both ways, so
    counts and accuracies order identically)."""
    if child_card["served_right"] < parent_card["served_right"]:
        return (f"serving-dev total fell "
                f"{parent_card['served_right']}/{parent_card['n']} "
                f"({parent_card['served_acc']}) -> "
                f"{child_card['served_right']}/{child_card['n']} "
                f"({child_card['served_acc']})")
    pc = parent_card["served_per_class"].get(
        "clean", {"right": 0, "n": 0})
    cc = child_card["served_per_class"].get(
        "clean", {"right": 0, "n": 0})
    if cc["right"] < pc["right"]:
        return (f"serving-dev clean recall fell by "
                f"{pc['right'] - cc['right']} item(s) "
                f"({pc['right']}/{pc['n']} -> {cc['right']}/{cc['n']}) "
                f"at served total "
                f"{parent_card['served_right']} -> "
                f"{child_card['served_right']} — the cycle-6/7 "
                f"signature (compensated clean loss in the "
                f"waking-dream refresh)")
    return None


def _gate3_prime(out: Dict[str, Any], pre: Dict[str, Any],
                 run_dir: Path, lineage: LineageLog,
                 cycle_id: str) -> Dict[str, Any]:
    """Gate 3′ for one dual-gate-passing child. On a block, the
    attempt returns with born=False and the rejection recorded;
    on a keep, the birth proceeds to the cycle's standing
    post-adoption verification (sealed judge, waking refresh,
    battery, audit) exactly as before."""
    import hashlib

    from . import dream as dream_mod
    child_name = out["child"]
    child_path = MODELS_DIR / f"{child_name}.json"
    # Bookkeeping first (retro-check §5): the child's bytes are
    # snapshotted into the run dir BEFORE adoption is decided,
    # so a future retro-check can re-measure this exact child.
    child_bytes_now = child_path.read_bytes()
    snap_dir = Path(run_dir) / "gate3"
    snap_dir.mkdir(parents=True, exist_ok=True)
    (snap_dir / f"{child_name}.json").write_bytes(child_bytes_now)
    items = _gate3_dev_items()
    child_card = _gate3_scorecard(dream_mod.load_bug_registry(),
                                  C.load_config(), items)
    parent_card = _gate3_scorecard(
        _gate3_registry(child_name, pre["child_bytes"]),
        json.loads(pre["config_bytes"].decode()), items)
    record: Dict[str, Any] = {
        "gate": "Gate 3′ — full serving path (composer + "
                "waking-dream refresh) on the say_dev pool, "
                "child vs parent, pre-adoption",
        "pool": "factory/say_dev.json (216 items, dev only — "
                "the sealed set is never spent here)",
        "child_snapshot": f"gate3/{child_name}.json",
        "child_snapshot_sha256":
            hashlib.sha256(child_bytes_now).hexdigest(),
        "child": child_card,
        "parent": parent_card,
    }
    reason = _gate3_verdict(child_card, parent_card)
    if reason is None:
        record["verdict"] = "kept"
        out["gate3_prime"] = record
        lineage.append("gate3_prime_kept", cycle_id=cycle_id,
                       child=child_name,
                       served_child=child_card["served_acc"],
                       served_parent=parent_card["served_acc"],
                       clean_child=child_card["served_per_class"]
                       .get("clean", {}).get("right"),
                       clean_parent=parent_card["served_per_class"]
                       .get("clean", {}).get("right"))
        print(f"[{cycle_id}] Gate 3′ KEPT {child_name}: served "
              f"dev {parent_card['served_acc']} -> "
              f"{child_card['served_acc']}, clean "
              f"{parent_card['served_per_class'].get('clean', {}).get('right')}"
              f" -> "
              f"{child_card['served_per_class'].get('clean', {}).get('right')}",
              flush=True)
        return out
    # Blocked: un-born in place. Restore the two files the
    # birth wrote from the pre-attempt byte snapshots; nothing
    # else was ever written for this child.
    if pre["child_bytes"] is None:
        child_path.unlink(missing_ok=True)
    else:
        child_path.write_bytes(pre["child_bytes"])
    (MODELS_DIR / "composer_config.json").write_bytes(
        pre["config_bytes"])
    record["verdict"] = "blocked"
    record["reason"] = reason
    out["gate3_prime"] = record
    out["born"] = False
    out["rejection"] = (
        f"Gate 3′ blocked the birth (the dual pristine gate had "
        f"passed): {reason}. Serving state untouched — the "
        f"child model file and composer config were restored "
        f"from pre-attempt byte snapshots before any registry "
        f"rewrite; no rollback was involved.")
    lineage.append("gate3_prime_blocked", cycle_id=cycle_id,
                   child=child_name, reason=reason,
                   served_child=child_card["served_acc"],
                   served_parent=parent_card["served_acc"],
                   clean_child=child_card["served_per_class"]
                   .get("clean", {}).get("right"),
                   clean_parent=parent_card["served_per_class"]
                   .get("clean", {}).get("right"))
    print(f"[{cycle_id}] Gate 3′ BLOCKED {child_name}: {reason}",
          flush=True)
    return out


# ------------------------------------------------------------ report
def _apply_champion_crowns(cycle_id: str,
                           attempts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build 1 crown application — called ONLY from the
    births-kept branch of a cycle, after serving verification
    has passed. A challenger is crowned when its candidate was
    the attempt's born child AND its dev margin over the
    champion candidate was positive (factory/champion.py's
    crown rule; dev selects, held never does). Rolled-back or
    unborn challengers can never reach this function."""
    from . import champion as champion_mod
    applied: List[Dict[str, Any]] = []
    rec = champion_mod.ensure_record()
    for att in attempts:
        if not att.get("born"):
            continue
        ch = (att.get("methods") or {}).get("champion") or {}
        if not ch.get("mutation"):
            continue
        if champion_mod.should_crown(
                mutant_born=bool(ch.get("mutant_born")),
                dev_margin=ch.get("dev_margin")):
            rec = champion_mod.crown(
                rec, cycle_id=cycle_id,
                target=f"{att['cls']}/{att['slice']}",
                mutant_recipe=ch["mutant_recipe"],
                mutation=ch["mutation"],
                dev_margin=ch["dev_margin"],
                champ_dev_acc=ch.get("champ_dev_acc"),
                mutant_dev_acc=ch.get("mutant_dev_acc"))
            champion_mod.save_record(rec)
            applied.append(
                {"target": f"{att['cls']}/{att['slice']}",
                 "version": rec["version"],
                 "mutation": ch["mutation"],
                 "dev_margin": ch["dev_margin"]})
    return applied


def _fmt(x):
    return "—" if x is None else (f"{x:.4f}" if isinstance(x, float)
                                  else str(x))


def write_report(cycle: Dict[str, Any]) -> None:
    GROWTH_DIR.mkdir(parents=True, exist_ok=True)
    cid = cycle["cycle_id"]
    _atomic_json(GROWTH_DIR / f"{cid}.json", cycle)
    b = cycle["battery_before"]
    a = cycle.get("battery_after") or {}
    lines = [
        f"# Growth {cid} — {cycle['date']}",
        "",
        "Runner: `python3 -m factory.growth_cycle`. Gates: dual "
        "pristine held slices (phase-3 held + name-intent held), "
        "strict child > parent on both; then Gate 3′ — the full "
        "serving path on the say_dev pool (composer + waking-"
        "dream refresh), child vs parent, blocking on any served "
        "total fall or a >=1-item served clean-recall fall; "
        "adoption verified on the served battery + full audit; "
        "any regression rolls the births back.",
        "",
        "## Births",
        "",
        "| target | parent (phase-3 slice) | parent (intent slice) "
        "| best child (phase-3) | best child (intent) | verdict |",
        "|---|---|---|---|---|---|",
    ]
    for att in cycle["attempts"]:
        best_slice = att.get("child_slice_heldout_acc")
        best_intent = None
        scored = [r for r in att.get("attempts", [])
                  if "intent_heldout_acc" in r]
        if scored:
            best_intent = max(r["intent_heldout_acc"] for r in scored)
        verdict = ("BORN — " + att["child"] if att["born"]
                   else "no birth")
        if cycle.get("rolled_back") and att["born"]:
            verdict += " — REMOVED at serving verification"
        lines.append(
            f"| {att['cls']}/{att['slice']} "
            f"| {_fmt(att['parent_slice_heldout_acc'])} "
            f"(n={att['held_slice_n']}) "
            f"| {_fmt(att.get('parent_intent_heldout_acc'))} "
            f"(n={att.get('intent_held_slice_n')}) "
            f"| {_fmt(best_slice)} | {_fmt(best_intent)} "
            f"| {verdict} |")
        if att.get("rejection"):
            lines.append(f"\n  gate record: {att['rejection']}")
        if att["born"]:
            lines.append(
                f"\n  winning arm: {att.get('winning_arm')}; "
                f"child remainder acc "
                f"{_fmt(att.get('child_remainder_heldout_acc'))} "
                f"(parent {_fmt(att.get('parent_remainder_heldout_acc'))}, "
                f"informational — routing serves the remainder "
                f"by the parent)")
    if any(att.get("methods") for att in cycle["attempts"]):
        lines += ["", "## Methods provenance (cycle-3 arms)", ""]
        for att in cycle["attempts"]:
            mp = att.get("methods")
            if not mp:
                continue
            lines.append(f"### {att['cls']}/{att['slice']}")
            hh = mp.get("headtohead") or {}
            if hh.get("skipped"):
                lines.append(f"- Recipe head-to-head: skipped — "
                             f"{hh['skipped']}")
            elif hh:
                parts = "; ".join(
                    f"{r['id']} dev "
                    f"{_fmt(r.get('dev_acc'))}"
                    + (f" (blocked: {r['blocked']})"
                       if r.get("blocked") else "")
                    for r in hh.get("recipes", []))
                lines.append(
                    f"- Recipe head-to-head (budget "
                    f"{hh.get('budget_epochs')} epochs, dev split "
                    f"of TRAIN data, dev n={hh.get('dev_n')}): "
                    f"{parts} -> winner {hh.get('winner')} "
                    f"(dev {_fmt(hh.get('winner_dev_acc'))}). "
                    f"Held slices never used for this choice.")
            br = mp.get("breadth") or {}
            if br:
                lines.append(
                    f"- Breadth edit: probe {br.get('probe_epochs')} "
                    f"epochs from parent; thin candidate = alpha "
                    f"{br.get('thin_alpha')} of the probe delta on "
                    f"EVERY weight group; concentrated control = "
                    f"full delta on '{br.get('indicted_tensor')}' "
                    f"only (largest |delta| "
                    f"{(br.get('tensor_deltas') or {}).get(br.get('indicted_tensor'))})."
                    + (f" BLOCKED: {br['blocked']}"
                       if br.get("blocked") else ""))
            df = mp.get("dream_first") or {}
            if df:
                if df.get("skipped"):
                    lines.append(f"- Dream-first repair "
                                 f"(improvised): skipped — "
                                 f"{df['skipped']}")
                else:
                    lines.append(
                        f"- Dream-first repair (improvised): dream "
                        f"pool {df.get('pool_n')} -> "
                        f"{df.get('pool_clean_n')} clean -> slice "
                        f"{df.get('dream_slice_n')} -> difficulty "
                        f"filter kept {df.get('kept_n')} "
                        f"({df.get('kept_hard_n')} the parent got "
                        f"wrong); repaired parent on "
                        f"{df.get('repair_diet_n')} items "
                        f"({df.get('repair_epochs')} epochs), "
                        f"children seeded from it."
                        + (f" BLOCKED: {df['blocked']}"
                           if df.get("blocked") else ""))
            cp = mp.get("champion") or {}
            if cp:
                if cp.get("skipped"):
                    lines.append(f"- Champion recipe: skipped — "
                                 f"{cp['skipped']}")
                elif cp.get("blocked"):
                    lines.append(f"- Champion recipe: BLOCKED — "
                                 f"{cp['blocked']}")
                else:
                    mut = cp.get("mutation") or {}
                    lines.append(
                        f"- Champion recipe v{cp.get('version')} "
                        f"(Build 1): one-gene mutant "
                        f"({mut.get('gene')}: {mut.get('from')} "
                        f"-> {mut.get('to')}); dev champion "
                        f"{_fmt(cp.get('champ_dev_acc'))} vs "
                        f"mutant {_fmt(cp.get('mutant_dev_acc'))} "
                        f"(margin {_fmt(cp.get('dev_margin'))}); "
                        f"mutant born: {cp.get('mutant_born')}. "
                        f"A crown lands only if the birth is "
                        f"kept after verification.")
            lines.append("")
    champ_cycle = cycle.get("champion") or {}
    if champ_cycle:
        lines += ["", "## Champion recipe (Build 1)", "",
                  f"Designated target: "
                  f"{champ_cycle.get('designated_target')}; "
                  f"record v{champ_cycle.get('version_before')}"
                  + (f" -> v{champ_cycle['version_after']}"
                     if champ_cycle.get("version_after")
                     is not None else "")
                  + f"; crowns applied: "
                    f"{len(champ_cycle.get('crowns_applied') or [])}"
                  + (f" — {champ_cycle['note']}"
                     if champ_cycle.get("note") else "")]
    lines += ["", "## Served battery (acceptance, Tier-0 sections)",
              "", "| check | before | after |", "|---|---|---|"]
    for task in b:
        lines.append(f"| {task} | {b[task]['score']} "
                     f"| {a.get(task, {}).get('score', '—')} |")
    lines += ["",
              f"Overall (Tier-0 sections): "
              f"{cycle['battery_overall_before']}"
              + (f" -> {cycle['battery_overall_after']}"
                 if cycle.get("battery_overall_after") is not None
                 else " (unchanged — no adoption)"),
              "",
              f"Full audit after cycle: "
              f"{'OK' if cycle['audit']['ok'] else 'FAILED'} "
              f"({len(cycle['audit']['failures'])} failure(s))",
              "",
              "## Learned say (measured, not adopted)",
              "",
              f"Composed acc on the phase-3 held set by margin rule: "
              f"{cycle['learned_say']['composed_acc']} "
              f"(fit on train; judged on a spent surface — see "
              f"cycle JSON for weights and the adoption note).",
              "",
              "## Harvest (parents' measured failures, training-side)",
              ""]
    for tgt, rows in cycle["harvest"].items():
        for surf, r in rows.items():
            lines.append(f"- {tgt} on {surf}: acc {r['acc']} "
                         f"(n={r['n']}, {r['wrong_n']} wrong)"
                         + (f"; wrong by intent: {r['wrong_by_intent']}"
                            if r["wrong_by_intent"] else ""))
    if cycle.get("rolled_back"):
        lines += ["", f"## ROLLED BACK\n\n{cycle['rollback_reason']}"]
    if cycle.get("novelty"):
        nov = cycle["novelty"]
        lines += ["", "## Novelty rotation (cron mode)", "",
                  f"Keyed by cycle number {nov.get('cycle_no')}: "
                  f"intent-cap sampling seed {nov.get('intent_seed')}, "
                  f"dream-pool band counts {nov.get('pool_counts')}, "
                  f"grid seed {nov.get('grid_seed')}. "
                  f"{nov.get('scheme', '')}"]
        for ch in nov.get("grid_changes", []):
            lines.append(f"- grid: {ch}")
    lines += ["", f"## Next\n\n{cycle['next_attack']}"]
    (GROWTH_DIR / f"{cid}.md").write_text("\n".join(lines) + "\n")
    with open(GROWTH_DIR / "ledger.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "cycle_id": cid, "ts": cycle["date"],
            "births": [att["child"] for att in cycle["attempts"]
                       if att["born"] and not cycle.get("rolled_back")],
            "removed": [att["child"] for att in cycle["attempts"]
                        if att["born"] and cycle.get("rolled_back")],
            "rejected": [att["child"] for att in cycle["attempts"]
                         if not att["born"]],
            "battery_overall_before": cycle["battery_overall_before"],
            "battery_overall_after": cycle.get("battery_overall_after"),
            "audit_ok": cycle["audit"]["ok"],
        }, ensure_ascii=False) + "\n")


# ------------------------------------------------- cron readiness
# The four changes the cycle-2 report required before scheduling:
# (1) cycle-id auto-increment, (2) single-instance lock + lab-busy
# skip, (3) per-cycle novelty keyed by cycle number, (4) an alert
# file on rollback / audit failure. Behaviour contract: invoking
# the runner the OLD way (an explicit --cycle-id, no --rotate)
# reproduces cycles 1/2 exactly — legacy seeds, the fixed grids, no
# rotation. Novelty activates only for auto-derived ids (the cron
# path) or when --rotate is passed explicitly.

_CYCLE_ID_RE = re.compile(r"growth-cycle-(\d+)")


def cycle_number(cycle_id: str) -> int:
    m = _CYCLE_ID_RE.search(cycle_id or "")
    if m:
        return int(m.group(1))
    digits = re.findall(r"\d+", cycle_id or "")
    return int(digits[-1]) if digits else 0


def _ledger_entries() -> List[Dict[str, Any]]:
    out = []
    if LEDGER_PATH.exists():
        for line in LEDGER_PATH.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def next_cycle_id() -> str:
    """(1) The next growth-cycle-NNN, derived from the ledger
    (skips consume an id too — ids stay unique and monotonic).
    Existing report files are also scanned so a hand-written cycle
    record can never be overwritten by an auto run."""
    n = 0
    for e in _ledger_entries():
        m = _CYCLE_ID_RE.search(str(e.get("cycle_id", "")))
        if m:
            n = max(n, int(m.group(1)))
    if GROWTH_DIR.exists():
        for p in GROWTH_DIR.glob("growth-cycle-*.json"):
            m = _CYCLE_ID_RE.search(p.stem)
            if m:
                n = max(n, int(m.group(1)))
    return f"growth-cycle-{n + 1:03d}"


def _read_lock() -> Optional[Dict[str, Any]]:
    try:
        return json.loads(LOCK_PATH.read_text())
    except Exception:  # noqa: BLE001 — absent/corrupt lock = no lock
        return None


def _pid_alive(pid: Any) -> bool:
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, TypeError, ValueError):
        return False


def _lock_blocker() -> Optional[str]:
    """Why the lock blocks a new cycle, or None. A lock is stale
    after LOCK_STALE_SECONDS or when its pid is dead; a stale lock
    never blocks (the acquirer overwrites it and says so)."""
    lock = _read_lock()
    if lock is None:
        return None
    age = time.time() - float(lock.get("ts", 0))
    if age > LOCK_STALE_SECONDS:
        return None
    if not _pid_alive(lock.get("pid")):
        return None
    return (f"growth lock held by pid {lock.get('pid')} "
            f"(cycle {lock.get('cycle_id')}, "
            f"{int(age)}s old, stale after {LOCK_STALE_SECONDS}s)")


def _acquire_lock(cycle_id: str) -> Dict[str, Any]:
    GROWTH_DIR.mkdir(parents=True, exist_ok=True)
    lock = {"pid": os.getpid(), "cycle_id": cycle_id,
            "ts": time.time(),
            "date": time.strftime("%Y-%m-%d %H:%M %Z")}
    LOCK_PATH.write_text(json.dumps(lock))
    return lock


def _release_lock() -> None:
    lock = _read_lock()
    if lock and lock.get("pid") == os.getpid():
        try:
            LOCK_PATH.unlink()
        except OSError:
            pass


_HEAVY_TOKENS = ("weights-reader", "v2gen", "v2train", "v2dream",
                 "v2reader", "train", "dream", "growth_cycle",
                 "phase3", "phase4", "battery", "audit", "loop.py",
                 "daemon.py")


def _lab_busy_jobs() -> List[Dict[str, Any]]:
    """(2) Other heavy lab jobs on this VM, found in /proc: python
    processes (not this one, not its ancestors) whose cwd sits
    inside the lab or whose command line references a lab path AND
    carries a heavy-work token (the weights-reader v2 worker —
    v2gen/v2train under weights-reader/ — is the standing example).
    This VM runs one heavy job at a time; a cron cycle must skip,
    not collide."""
    me = os.getpid()
    ancestors = set()
    pid = me
    while pid > 1:
        ancestors.add(pid)
        try:
            stat = Path(f"/proc/{pid}/stat").read_text()
            pid = int(stat.rsplit(")", 1)[1].split()[1])
        except Exception:  # noqa: BLE001
            break
    lab = str(LAB_ROOT)
    jobs = []
    proc = Path("/proc")
    if not proc.exists():
        return jobs
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        p = int(entry.name)
        if p in ancestors:
            continue
        try:
            cmdline = (entry / "cmdline").read_bytes() \
                .replace(b"\0", b" ").decode("utf-8", "replace").strip()
            cwd = os.readlink(entry / "cwd")
        except OSError:
            continue
        if "python" not in cmdline:
            continue
        in_lab = cwd.startswith(lab) or lab in cmdline
        if not in_lab:
            continue
        hay = (cmdline + " " + cwd).lower()
        if any(tok in hay for tok in _HEAVY_TOKENS):
            jobs.append({"pid": p, "cwd": cwd, "cmd": cmdline[:200]})
    return jobs


def _skip_cycle(cycle_id: str, reason: str) -> Dict[str, Any]:
    """A skipped cycle trains nothing and exits 0 — but it is on
    the record: one ledger line saying skipped + why."""
    GROWTH_DIR.mkdir(parents=True, exist_ok=True)
    entry = {"cycle_id": cycle_id,
             "ts": time.strftime("%Y-%m-%d %H:%M %Z"),
             "skipped": True, "skip_reason": reason,
             "births": [], "removed": [], "rejected": [],
             "battery_overall_before": None,
             "battery_overall_after": None, "audit_ok": None}
    with open(LEDGER_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(json.dumps({"cycle_id": cycle_id, "skipped": True,
                      "reason": reason}, indent=1))
    return entry


def write_alert(cycle: Dict[str, Any]) -> Path:
    """(4) The alert path: on rollback or audit failure, a plain
    file the cron reads for. Absence of ALERT-<cycle>.md = a quiet
    cycle."""
    cid = cycle["cycle_id"]
    removed = [a["child"] for a in cycle.get("attempts", [])
               if a.get("born")]
    lines = [f"# ALERT {cid} — {cycle.get('date', '')}", ""]
    if cycle.get("rolled_back"):
        lines += ["## Rolled back", "",
                  str(cycle.get("rollback_reason", "")),
                  "",
                  f"Births removed: {removed or 'none recorded'}",
                  ""]
    audit = cycle.get("audit") or {}
    if audit and not audit.get("ok", True):
        lines += ["## Audit FAILED", ""]
        for f in audit.get("failures", []):
            lines.append(f"- {f}")
        lines.append("")
    if cycle.get("error"):
        lines += ["## Runner error", "", str(cycle["error"]), ""]
    lines += [f"Battery overall: {cycle.get('battery_overall_before')}"
              f" -> {cycle.get('battery_overall_after')}",
              "",
              f"Full record: growth/{cid}.json (+ factory lineage)."]
    path = GROWTH_DIR / f"ALERT-{cid}.md"
    path.write_text("\n".join(lines) + "\n")
    return path


# ------------------------------------------------------------ novelty
def rotation_spec(cycle_no: int) -> Dict[str, Any]:
    """(3) Per-cycle novelty, a pure function of the cycle number.
    Training in this lab is deterministic, so a fixed grid on a
    cron would re-prove the same candidates forever. Keyed by
    cycle number, the rotation varies three things:
      * the name-intent diet's sampling seed (which slice of the
        intent partition each child trains on),
      * the dream-pool band counts handed to the birth protocol
        (the data partition grows/shifts by cycle),
      * the cycle-2 candidate grid itself — epoch points, mixture
        leans and curriculum leans are transformed by a seeded RNG
        (see _rotated_variants).
    Same cycle number -> same rotation (reproducible); different
    cycle number -> different candidates."""
    rng = random.Random(0xC0FFEE + cycle_no)
    return {
        "cycle_no": cycle_no,
        "intent_seed": 99 + 7919 * cycle_no,
        "pool_counts": {1: 30 + (cycle_no % 3) * 4,
                        2: 26 + ((cycle_no + 1) % 3) * 4,
                        3: 26 + ((cycle_no + 2) % 3) * 4},
        "grid_seed": rng.randrange(1 << 30),
        "scheme": "keyed by cycle number: intent-cap sampling seed "
                  "+ dream-pool band counts + seeded transforms of "
                  "the candidate grid (epoch ladder steps, mixture "
                  "leans, curriculum leans, occasional hidden-size "
                  "changes). Legacy invocations (explicit --cycle-id, "
                  "no --rotate) skip all of it and reproduce the "
                  "cycle-1/2 grids and seeds exactly.",
    }


def _rotated_variants(base: List[Dict[str, Any]], rotation: Dict[str, Any],
                      target_key: str) -> List[Dict[str, Any]]:
    """The cycle-2 grid under this cycle's rotation. Deterministic
    in (grid_seed, target); every transform is logged so the report
    can say exactly how this cycle's grid differs."""
    rng = random.Random(rotation["grid_seed"]
                        + sum(ord(c) for c in target_key))
    out = copy.deepcopy(base)
    changes: List[str] = []
    curr: List[Dict[str, Any]] = []
    for var in out:
        for cfg in var["configs"]:
            label = cfg.get("arm_label", "?")
            scale = rng.choice([0.75, 1.0, 1.0, 1.25, 1.5])
            if "epochs" in cfg and scale != 1.0:
                old = cfg["epochs"]
                cfg["epochs"] = max(
                    300, int(round(old * scale / 50.0)) * 50)
                if cfg["epochs"] != old:
                    changes.append(f"{label}: epochs {old} -> "
                                   f"{cfg['epochs']}")
            mix = cfg.get("mix")
            if mix:
                comp = rng.choice(list(mix.keys()))
                delta = rng.choice([-1, 1])
                new = max(1, min(4, mix[comp] + delta))
                if new != mix[comp]:
                    changes.append(f"{label}: mix {comp} "
                                   f"{mix[comp]} -> {new}")
                    mix[comp] = new
            if "curr" in label:
                curr.append(cfg)
            if "fmode" in cfg and rng.random() < 0.2:
                old_h = cfg.get("hidden")
                new_h = rng.choice([0, 4, 6, 8])
                if new_h != old_h:
                    cfg["hidden"] = new_h
                    changes.append(f"{label}: hidden {old_h} -> "
                                   f"{new_h}")
    if len(curr) >= 2 and rng.random() < 0.5:
        a, b = curr[0], curr[-1]
        if a.get("mix") and b.get("mix") and a["mix"] != b["mix"]:
            a["mix"], b["mix"] = b["mix"], a["mix"]
            changes.append("curriculum leans swapped: "
                           f"{a.get('arm_label')} <-> "
                           f"{b.get('arm_label')}")
    if not changes and out and out[0]["configs"]:
        cfg = out[0]["configs"][0]
        old = cfg.get("epochs", 800)
        cfg["epochs"] = max(300, int(round(old * 1.25 / 50.0)) * 50)
        changes.append(f"{cfg.get('arm_label')}: epochs {old} -> "
                       f"{cfg['epochs']} (forced step — the seeded "
                       f"draw left the grid unchanged)")
    rotation.setdefault("grid_changes", []).extend(
        f"{target_key}: {c}" for c in changes)
    return out


def preflight(cycle_id: str) -> Dict[str, Any]:
    """The cron decision, without running anything: would this
    invocation skip, and why. Writes nothing."""
    blocker = _lock_blocker()
    busy = _lab_busy_jobs()
    reasons = []
    if blocker:
        reasons.append(blocker)
    if busy:
        reasons.append("lab busy: " + "; ".join(
            f"pid {j['pid']} ({j['cmd']})" for j in busy))
    return {"cycle_id": cycle_id, "would_skip": bool(reasons),
            "reasons": reasons, "lock": _read_lock(), "busy": busy}


# ------------------------------------------------------------ the cycle
def run_cycle(cycle_id: str,
              rotation: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    t0 = time.time()
    run_dir = FACTORY_DIR / "runs" / cycle_id
    run_dir.mkdir(parents=True, exist_ok=True)
    lineage = LineageLog(run_dir / "lineage.jsonl")
    factory_lineage = LineageLog(FACTORY_DIR / "lineage.jsonl")
    lineage.append("growth_cycle_start", cycle_id=cycle_id)

    if not (name_intent.DATA_DIR / "name_intent_train.json").exists():
        name_intent.build_datasets()
    intent_train = name_intent.load_train()
    intent_held = name_intent.load_held()

    snapshots = {
        "composer_config": (MODELS_DIR / "composer_config.json")
        .read_bytes(),
        "waking_dream_results": (LAB_ROOT / "waking-dream"
                                 / "results.json").read_bytes(),
        "registry": (FACTORY_DIR / "registry.json").read_bytes(),
    }
    snap_dir = run_dir / "snapshots"
    snap_dir.mkdir(exist_ok=True)
    for k, v in snapshots.items():
        (snap_dir / k).write_bytes(v)
    # Pre-cycle serving model files (cycle-006 repair): a birth
    # overwrites the incumbent file of the same name, so these
    # bytes are the only restore point if the cycle rolls back.
    model_snapshots = _snapshot_model_files(_target_child_names())
    models_snap_dir = snap_dir / "models"
    models_snap_dir.mkdir(exist_ok=True)
    for name, data in model_snapshots.items():
        if data is not None:
            (models_snap_dir / f"{name}.json").write_bytes(data)

    cycle: Dict[str, Any] = {
        "cycle_id": cycle_id,
        "date": time.strftime("%Y-%m-%d %H:%M %Z"),
        "targets": [f"{c}/{s}" for c, s in TARGETS],
        "levers": ["name-intent data family (Lever 1)",
                   "parent-initialized fine-tuning (Lever 2)",
                   "found-on-failure diet weighting (Fable)",
                   "learned-say check (Fable) — measured only"],
    }
    if rotation is not None:
        cycle["novelty"] = rotation

    print(f"[{cycle_id}] battery BEFORE ...", flush=True)
    cycle["battery_before"] = measure_served_battery(run_dir, "before")
    bb = cycle["battery_before"]
    cycle["battery_overall_before"] = round(
        sum(v["score"] for v in bb.values()) / len(bb), 4)
    print(f"[{cycle_id}] harvest ...", flush=True)
    cycle["harvest"] = harvest_failures(intent_train)
    print(f"[{cycle_id}] learned-say experiment ...", flush=True)
    cycle["learned_say"] = learned_say_experiment()

    replay = replay_set()
    attempts: List[Dict[str, Any]] = []
    for cls, slice_name in TARGETS:
        print(f"[{cycle_id}] birth attempt {cls}/{slice_name} ...",
              flush=True)
        extra = cap_intent(intent_train, cls, slice_name,
                           seed=rotation["intent_seed"] if rotation
                           else 99)
        gate3_pre = _gate3_pre_state(
            f"bug-{cls}-{slice_name}-model")
        out = growth.attempt_birth(
            cls, slice_name, run_dir / "births" / f"{cls}-{slice_name}",
            lineage, cycle_id,
            extra_train=extra, extra_held=intent_held,
            arms=("scratch", "init"), init_train_extra=replay,
            failure_weight=True,
            pool_counts=rotation["pool_counts"] if rotation else None)
        if out["born"]:
            out = _gate3_prime(out, gate3_pre, run_dir, lineage,
                               cycle_id)
        out["intent_train_capped_n"] = len(extra)
        attempts.append(out)
        print(f"[{cycle_id}]   -> born={out['born']} "
              f"{out.get('rejection') or ''}", flush=True)
    cycle["attempts"] = attempts
    born = [a for a in attempts if a["born"]]
    cycle["rolled_back"] = False

    if born:
        print(f"[{cycle_id}] serving verification ...", flush=True)
        from .registry import load_registry
        prev_raw = load_registry()["compositions"][
            "bug-pattern-composed"]["evidence"][
                "fresh_sealed_baseline"]["acc"]
        judge = _sealed_judge(cycle_id, previous_acc=prev_raw)
        cycle["sealed_raw_composed"] = {
            "served_sealed_before": bb[
                "bug-pattern-composed-sealed-v2"]["score"],
            "raw_composed_before": prev_raw,
            "raw_composed_after": judge["composed_acc"],
            "per_class_recall_after": judge["per_class_recall"],
            "note": "the battery line is the SERVED (waking-dream) "
                    "number; the raw composed number is the audit's "
                    "baseline leg, re-recorded by the growth judge"}
        cycle["waking_dream_refresh"] = \
            _refresh_waking_dream_results(cycle_id)
        from .registry import write_registry
        write_registry()
        cycle["battery_after"] = measure_served_battery(run_dir,
                                                        "after")
        ba = cycle["battery_after"]
        cycle["battery_overall_after"] = round(
            sum(v["score"] for v in ba.values()) / len(ba), 4)
        cycle["audit"] = _full_audit()
        regressions = _battery_regressions(bb, ba)
        if regressions or not cycle["audit"]["ok"]:
            reason = ("serving verification failed: "
                      + ("; ".join(regressions) if regressions else "")
                      + (f"; audit failures: "
                         f"{cycle['audit']['failures']}"
                         if not cycle["audit"]["ok"] else ""))
            _rollback(born, snapshots, cycle_id, lineage, reason,
                      model_snapshots=model_snapshots)
            cycle["rolled_back"] = True
            cycle["rollback_reason"] = reason
            cycle["audit"] = _full_audit()
            print(f"[{cycle_id}] ROLLED BACK: {reason}", flush=True)
        else:
            print(f"[{cycle_id}] births KEPT; whole verified",
                  flush=True)
    else:
        cycle["audit"] = _full_audit()

    if cycle["attempts"] and all(not a["born"] for a in attempts):
        cycle["next_attack"] = (
            "No birth under the dual gate. Read the per-config "
            "table in the cycle JSON: whichever gate each best "
            "candidate failed names cycle 2's target (intent-slice "
            "supply quality vs template-slice capacity), plus the "
            "learned-say adoption step if its held margin holds.")
    elif cycle.get("rolled_back"):
        cycle["next_attack"] = (
            "Births passed the dual held gate but failed serving "
            "verification — cycle 2 attacks the gap between the "
            "held slices and the sealed/served surfaces (broader "
            "pristine held slices before any re-attempt).")
    else:
        cycle["next_attack"] = (
            "Extend the loop: the remaining slices from the intake "
            "scan, the learned-say adoption step under its own "
            "battery gate, and a second name-intent partition "
            "(comparison/accumulator slices) so growth is not a "
            "one-cycle event.")
    cycle["wall_seconds"] = round(time.time() - t0, 1)
    write_report(cycle)
    factory_lineage.append(
        "growth_cycle", cycle_id=cycle_id,
        run_dir=f"factory/runs/{cycle_id}",
        births=[a["child"] for a in born
                if not cycle["rolled_back"]],
        removed=[a["child"] for a in born if cycle["rolled_back"]],
        rejected=[a["child"] for a in attempts if not a["born"]],
        battery_overall_before=cycle["battery_overall_before"],
        battery_overall_after=cycle.get("battery_overall_after"),
        audit_ok=cycle["audit"]["ok"])
    lineage.append("growth_cycle_done", cycle_id=cycle_id,
                   wall_seconds=cycle["wall_seconds"])
    print(json.dumps({"cycle_id": cycle_id,
                      "born": [a["child"] for a in attempts
                               if a["born"]],
                      "rolled_back": cycle["rolled_back"],
                      "battery_overall_before":
                          cycle["battery_overall_before"],
                      "battery_overall_after":
                          cycle.get("battery_overall_after"),
                      "audit_ok": cycle["audit"]["ok"],
                      "wall_seconds": cycle["wall_seconds"]},
                     indent=1))
    return cycle


# ------------------------------------------------------------ cycle 2
# Cycle 2's pre-declared candidate grid. Cycle 1's per-config table
# named the split precisely:
#   wrong-operator: the phase-3 winner (scratch code h4, 0.90) knew
#     no intent (0.572); the intent winner (scratch text h4, 0.7882)
#     only TIED the parent on phase-3 (0.85). One model must hold
#     both: text features + longer training, mixture leans both
#     ways, two-stage curricula in both directions, one capacity
#     probe (h6), and — only if those fail — a raised intent cap
#     (supply test: parent fails 242/757 intent-train items).
#   off-by-one: the intent bar is already cleared by several arms
#     (best 0.9971); the ONLY blocker is one phase-3 held item
#     (parent 0.95 = 19/20, strict gate needs 20/20). Attack is
#     template-slice capacity: parent-init fine-tunes on
#     slice-lean mixtures with replay, longer/warmer variants of
#     the cycle-1 winners, and a slice-polish curriculum.
# The grid is bounded and declared here, before any held number is
# seen; every candidate is judged by the unchanged dual gate.
def _cfg(label, **kw):
    d = {"arm_label": label}
    d.update(kw)
    return d


CYCLE2_VARIANTS: Dict[Any, List[Dict[str, Any]]] = {
    ("wrong-operator", "expression"): [
        {"name": "merged-recipes-standard-cap",
         "configs": [
             _cfg("c2-wo-ep1200", fmode="text", hidden=4, epochs=1200,
                  diet="child"),
             _cfg("c2-wo-ep1600", fmode="text", hidden=4, epochs=1600,
                  diet="child"),
             _cfg("c2-wo-intentx2", fmode="text", hidden=4, epochs=1200,
                  diet="mix", mix={"slice": 1, "intent": 2}),
             _cfg("c2-wo-slicex2", fmode="text", hidden=4, epochs=800,
                  diet="mix", mix={"slice": 2, "intent": 1}),
             _cfg("c2-wo-stage-intent", fmode="text", hidden=4,
                  epochs=800, diet="mix", mix={"slice": 1, "intent": 3}),
             _cfg("c2-wo-curr-i2s", epochs=300, lr_scale=0.3,
                  init_from="stage:c2-wo-stage-intent",
                  diet="mix", mix={"slice": 2, "intent": 1}),
             _cfg("c2-wo-stage-slice", fmode="text", hidden=4,
                  epochs=800, diet="mix", mix={"slice": 3, "intent": 1}),
             _cfg("c2-wo-curr-s2i", epochs=300, lr_scale=0.3,
                  init_from="stage:c2-wo-stage-slice",
                  diet="mix", mix={"slice": 1, "intent": 2}),
             _cfg("c2-wo-h6", fmode="text", hidden=6, epochs=1200,
                  diet="child"),
             _cfg("c2-wo-code-ep1200", fmode="code", hidden=4,
                  epochs=1200, diet="child"),
         ]},
        {"name": "raised-intent-cap",
         "cap_pos": 220, "cap_neg": 300,
         "configs": [
             _cfg("c2-wo-capR-ep800", fmode="text", hidden=4, epochs=800,
                  diet="child"),
             _cfg("c2-wo-capR-ep1200", fmode="text", hidden=4,
                  epochs=1200, diet="child"),
             _cfg("c2-wo-capR-slicex2", fmode="text", hidden=4,
                  epochs=1200, diet="mix", mix={"slice": 2, "intent": 1}),
         ]},
    ],
    ("off-by-one", "index"): [
        {"name": "template-capacity",
         "configs": [
             _cfg("c2-ob-init-sx2", epochs=800, lr_scale=0.3,
                  init_from="parent", diet="mix",
                  mix={"slice": 2, "intent": 1, "replay": 1}),
             _cfg("c2-ob-init-sx3", epochs=800, lr_scale=0.3,
                  init_from="parent", diet="mix",
                  mix={"slice": 3, "intent": 1, "replay": 1}),
             _cfg("c2-ob-init-ep1600", epochs=1600, lr_scale=0.3,
                  init_from="parent", diet="init"),
             _cfg("c2-ob-init-lr05", epochs=800, lr_scale=0.5,
                  init_from="parent", diet="init"),
             _cfg("c2-ob-h8-ep1200", fmode="text", hidden=8,
                  epochs=1200, diet="child"),
             _cfg("c2-ob-h8-sx2", fmode="text", hidden=8, epochs=800,
                  diet="mix", mix={"slice": 2, "intent": 1}),
             _cfg("c2-ob-h0-ep1200", fmode="text", hidden=0,
                  epochs=1200, diet="child"),
             _cfg("c2-ob-stage", fmode="text", hidden=8, epochs=800,
                  diet="mix", mix={"slice": 2, "intent": 1}),
             _cfg("c2-ob-curr-polish", epochs=300, lr_scale=0.3,
                  init_from="stage:c2-ob-stage",
                  diet="mix", mix={"slice": 3, "intent": 1}),
         ]},
        {"name": "slice-repeat-fallback",
         "slice_repeat": 2,
         "configs": [
             _cfg("c2-ob2-init", epochs=800, lr_scale=0.3,
                  init_from="parent", diet="init"),
             _cfg("c2-ob2-init-ep1200", epochs=1200, lr_scale=0.3,
                  init_from="parent", diet="init"),
             _cfg("c2-ob2-h8", fmode="text", hidden=8, epochs=800,
                  diet="child"),
         ]},
    ],
}


def _attempt_target_cycle2(cls: str, slice_name: str, run_dir: Path,
                           lineage: LineageLog, cycle_id: str,
                           intent_train, intent_held, replay,
                           rotation: Optional[Dict[str, Any]] = None
                           ) -> Dict[str, Any]:
    """Run a target's pre-declared diet variants in order until one
    produces a dual-gate birth (or all are exhausted). Attempt rows
    from every variant are merged into one record for the report;
    a variant after a birth is never run (the child exists and is
    routed — further attempts would be a different cycle's work).
    With a rotation (cron mode), the declared grid is first passed
    through _rotated_variants and the intent diet's sampling seed
    and the dream-pool counts come from the rotation — the gates
    are untouched either way."""
    variants = CYCLE2_VARIANTS[(cls, slice_name)]
    if rotation is not None:
        variants = _rotated_variants(variants, rotation,
                                     f"{cls}/{slice_name}")
    merged: Optional[Dict[str, Any]] = None
    all_rows: List[Dict[str, Any]] = []
    variant_records: List[Dict[str, Any]] = []
    for vi, var in enumerate(variants):
        extra = cap_intent(intent_train, cls, slice_name,
                           seed=rotation["intent_seed"] if rotation
                           else 99,
                           pos_cap=var.get("cap_pos"),
                           neg_cap=var.get("cap_neg"))
        out = growth.attempt_birth(
            cls, slice_name,
            run_dir / "births" / f"{cls}-{slice_name}-v{vi + 1}",
            lineage, cycle_id,
            extra_train=extra, extra_held=intent_held,
            arms=(), init_train_extra=replay,
            failure_weight=var.get("failure_weight", True),
            slice_repeat=var.get("slice_repeat", 1),
            intent_repeat=var.get("intent_repeat", 1),
            extra_configs=var["configs"],
            pool_counts=rotation["pool_counts"] if rotation else None)
        variant_records.append({
            "variant": var["name"],
            "cap_pos": var.get("cap_pos", INTENT_CAP_POS),
            "cap_neg": var.get("cap_neg", INTENT_CAP_NEG),
            "slice_repeat": var.get("slice_repeat", 1),
            "intent_repeat": var.get("intent_repeat", 1),
            "intent_train_capped_n": len(extra),
            "train_child_n": out.get("train_child_n"),
            "born": out["born"]})
        all_rows.extend(out.get("attempts", []))
        if merged is None:
            merged = out
        if out["born"]:
            merged = dict(out)
            merged["winning_variant"] = var["name"]
            break
    assert merged is not None
    merged["attempts"] = all_rows
    merged["variants"] = variant_records
    merged.pop("intent_train_capped_n", None)
    if not merged["born"]:
        scored = [r for r in all_rows if "slice_heldout_acc" in r]
        if scored:
            merged["child_slice_heldout_acc"] = max(
                r["slice_heldout_acc"] for r in scored)
            both = [r for r in scored
                    if r["slice_heldout_acc"]
                    > merged["parent_slice_heldout_acc"]
                    and r.get("intent_heldout_acc", 0)
                    > merged["parent_intent_heldout_acc"]]
            merged["candidates_clearing_both"] = len(both)
            merged["rejection"] = (
                f"gate failed (cycle 2: {len(variant_records)} diet "
                f"variant(s), {len(scored)} candidates): no single "
                f"candidate beat the parent on both held slices "
                f"(phase-3 slice: parent "
                f"{merged['parent_slice_heldout_acc']}, best child "
                f"{merged['child_slice_heldout_acc']}; name-intent "
                f"slice: parent {merged['parent_intent_heldout_acc']}, "
                f"best child "
                f"{max(r['intent_heldout_acc'] for r in scored)}) "
                f"— no birth")
    return merged


def run_cycle2(cycle_id: str,
               rotation: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Growth cycle 2: merged recipes under the unchanged dual
    gate. Same skeleton as run_cycle (snapshots, battery before/
    after, sealed judge + waking-dream refresh on adoption, full
    audit, rollback on any regression) — only the candidate
    generation and the learned-say fit differ."""
    t0 = time.time()
    run_dir = FACTORY_DIR / "runs" / cycle_id
    run_dir.mkdir(parents=True, exist_ok=True)
    lineage = LineageLog(run_dir / "lineage.jsonl")
    factory_lineage = LineageLog(FACTORY_DIR / "lineage.jsonl")
    lineage.append("growth_cycle_start", cycle_id=cycle_id,
                   strategy="cycle2")

    if not (name_intent.DATA_DIR / "name_intent_train.json").exists():
        name_intent.build_datasets()
    intent_train = name_intent.load_train()
    intent_held = name_intent.load_held()

    snapshots = {
        "composer_config": (MODELS_DIR / "composer_config.json")
        .read_bytes(),
        "waking_dream_results": (LAB_ROOT / "waking-dream"
                                 / "results.json").read_bytes(),
        "registry": (FACTORY_DIR / "registry.json").read_bytes(),
    }
    snap_dir = run_dir / "snapshots"
    snap_dir.mkdir(exist_ok=True)
    for k, v in snapshots.items():
        (snap_dir / k).write_bytes(v)
    # Pre-cycle serving model files (cycle-006 repair; this block
    # was MISSING here until the cycle-007 repair — the rollback
    # call below passed model_snapshots that was never taken, so
    # a rollback in this path died with NameError): a birth
    # overwrites the incumbent file of the same name, so these
    # bytes are the only restore point if the cycle rolls back.
    model_snapshots = _snapshot_model_files(_target_child_names())
    models_snap_dir = snap_dir / "models"
    models_snap_dir.mkdir(exist_ok=True)
    for name, data in model_snapshots.items():
        if data is not None:
            (models_snap_dir / f"{name}.json").write_bytes(data)

    cycle: Dict[str, Any] = {
        "cycle_id": cycle_id,
        "date": time.strftime("%Y-%m-%d %H:%M %Z"),
        "targets": [f"{c}/{s}" for c, s in TARGETS],
        "levers": ["name-intent data family (Lever 1)",
                   "parent-initialized fine-tuning (Lever 2)",
                   "found-on-failure diet weighting (Fable)",
                   "cycle-2 merged recipes: mixture leans, "
                   "two-stage curricula, raised intent cap variant",
                   "learned-say v2 fit (joint weights + threshold "
                   "multipliers on the composed objective) — "
                   "measured only"],
        "strategy": "cycle2",
    }
    if rotation is not None:
        cycle["novelty"] = rotation

    print(f"[{cycle_id}] battery BEFORE ...", flush=True)
    cycle["battery_before"] = measure_served_battery(run_dir, "before")
    bb = cycle["battery_before"]
    cycle["battery_overall_before"] = round(
        sum(v["score"] for v in bb.values()) / len(bb), 4)
    print(f"[{cycle_id}] harvest ...", flush=True)
    cycle["harvest"] = harvest_failures(intent_train)
    print(f"[{cycle_id}] learned-say v2 experiment ...", flush=True)
    cycle["learned_say"] = learned_say_experiment_v2()

    replay = replay_set()
    attempts: List[Dict[str, Any]] = []
    for cls, slice_name in TARGETS:
        print(f"[{cycle_id}] birth attempt {cls}/{slice_name} ...",
              flush=True)
        gate3_pre = _gate3_pre_state(
            f"bug-{cls}-{slice_name}-model")
        out = _attempt_target_cycle2(cls, slice_name, run_dir,
                                     lineage, cycle_id,
                                     intent_train, intent_held, replay,
                                     rotation=rotation)
        if out["born"]:
            out = _gate3_prime(out, gate3_pre, run_dir, lineage,
                               cycle_id)
        attempts.append(out)
        print(f"[{cycle_id}]   -> born={out['born']} "
              f"{out.get('rejection') or ''}", flush=True)
    cycle["attempts"] = attempts
    born = [a for a in attempts if a["born"]]
    cycle["rolled_back"] = False

    if born:
        print(f"[{cycle_id}] serving verification ...", flush=True)
        from .registry import load_registry
        prev_raw = load_registry()["compositions"][
            "bug-pattern-composed"]["evidence"][
                "fresh_sealed_baseline"]["acc"]
        judge = _sealed_judge(cycle_id, previous_acc=prev_raw)
        cycle["sealed_raw_composed"] = {
            "served_sealed_before": bb[
                "bug-pattern-composed-sealed-v2"]["score"],
            "raw_composed_before": prev_raw,
            "raw_composed_after": judge["composed_acc"],
            "per_class_recall_after": judge["per_class_recall"],
            "note": "the battery line is the SERVED (waking-dream) "
                    "number; the raw composed number is the audit's "
                    "baseline leg, re-recorded by the growth judge"}
        cycle["waking_dream_refresh"] = \
            _refresh_waking_dream_results(cycle_id)
        from .registry import write_registry
        write_registry()
        cycle["battery_after"] = measure_served_battery(run_dir,
                                                        "after")
        ba = cycle["battery_after"]
        cycle["battery_overall_after"] = round(
            sum(v["score"] for v in ba.values()) / len(ba), 4)
        cycle["audit"] = _full_audit()
        regressions = _battery_regressions(bb, ba)
        if regressions or not cycle["audit"]["ok"]:
            reason = ("serving verification failed: "
                      + ("; ".join(regressions) if regressions else "")
                      + (f"; audit failures: "
                         f"{cycle['audit']['failures']}"
                         if not cycle["audit"]["ok"] else ""))
            _rollback(born, snapshots, cycle_id, lineage, reason,
                      model_snapshots=model_snapshots)
            cycle["rolled_back"] = True
            cycle["rollback_reason"] = reason
            cycle["audit"] = _full_audit()
            print(f"[{cycle_id}] ROLLED BACK: {reason}", flush=True)
        else:
            print(f"[{cycle_id}] births KEPT; whole verified",
                  flush=True)
    else:
        cycle["audit"] = _full_audit()

    ls = cycle["learned_say"]["composed_acc"]
    ls_note = (
        f"Learned-say v2 (joint fit on the composed objective): "
        f"held routed {ls.get('routed')}, mean {ls.get('mean')}, "
        f"learned {ls.get('learned')}. "
        + ("It BEATS the routed rule on the spent held surface — "
           "that earns it a battery-gated adoption step as its own "
           "cycle-3 item (still not adopted here)."
           if ls.get("learned", 0) > ls.get("routed", 1)
           else "It does not beat the routed rule — the learned-say "
                "question is closed unless the representation set "
                "itself changes."))
    cycle["cycle3_recommendation"] = (
        "Cycle 3 attacks, in order: (1) whichever dual-gate bar "
        "each target's cycle-2 per-config table shows still "
        "binding — if a single phase-3 held item (n=20 slice) is "
        "the whole blocker for a target, the honest fix is a "
        "LARGER pristine phase-3-style held slice (new template "
        "families, disjoint names/idioms), not more candidates "
        "against the same 20 items; (2) a second name-intent "
        "partition (comparison/accumulator intents) so the intent "
        "judge is not a fixed surface the grid can overfit; "
        "(3) the learned-say adoption step IF cycle 2's v2 fit "
        "beat the routed rule. " + ls_note)
    cycle["cron_readiness"] = (
        "Runner readiness for a recurring ~6h cron: the cycle runs "
        "end to end non-interactively (one command, md+json+ledger "
        "written, rollback automatic on any serving regression) — "
        "the mechanics are ready. Four changes are needed before "
        "scheduling it: (1) cycle-id auto-increment from the "
        "ledger (today it is a CLI argument); (2) a single-instance "
        "lock + a lab-busy check (this VM runs one heavy job at a "
        "time; a cron cycle must skip, not collide, when another "
        "lab job is training); (3) per-cycle novelty — training is "
        "deterministic, so re-running a fixed grid reproduces the "
        "same candidates exactly; a cron'd cycle must rotate its "
        "grid or grow its data partitions keyed by cycle number, "
        "or it will spend compute re-proving cycle 2 forever; "
        "(4) an alert path on rollback or audit failure (today "
        "that is only a ledger line). With (1)-(4) it can be "
        "scheduled; without (3) it should not be.")
    cycle["next_attack"] = (cycle["cycle3_recommendation"] + " "
                            + cycle["cron_readiness"])
    cycle["wall_seconds"] = round(time.time() - t0, 1)
    write_report(cycle)
    factory_lineage.append(
        "growth_cycle", cycle_id=cycle_id,
        run_dir=f"factory/runs/{cycle_id}",
        births=[a["child"] for a in born
                if not cycle["rolled_back"]],
        removed=[a["child"] for a in born if cycle["rolled_back"]],
        rejected=[a["child"] for a in attempts if not a["born"]],
        battery_overall_before=cycle["battery_overall_before"],
        battery_overall_after=cycle.get("battery_overall_after"),
        audit_ok=cycle["audit"]["ok"])
    lineage.append("growth_cycle_done", cycle_id=cycle_id,
                   wall_seconds=cycle["wall_seconds"])
    print(json.dumps({"cycle_id": cycle_id,
                      "born": [a["child"] for a in attempts
                               if a["born"]],
                      "rolled_back": cycle["rolled_back"],
                      "battery_overall_before":
                          cycle["battery_overall_before"],
                      "battery_overall_after":
                          cycle.get("battery_overall_after"),
                      "audit_ok": cycle["audit"]["ok"],
                      "wall_seconds": cycle["wall_seconds"]},
                     indent=1))
    return cycle


def run_cycle3(cycle_id: str,
               rotation: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Growth cycle 3 strategy (2026-11-11, Arnav: "Use fables
    methods learn from it if thats better improvise if u really
    can"): the legacy skeleton (same snapshots, battery before/
    after, sealed judge + waking-dream refresh on adoption, full
    audit, rollback on any regression, unchanged dual gate) with
    the candidate generation upgraded by the methods arms in
    factory/growth.py — a recipe head-to-head selected on a DEV
    split (Fable), a breadth-vs-concentrated edit pair (Fable),
    and a dream-first repair family (improvised here). Method
    provenance lands in the cycle JSON (attempts[].methods +
    per-candidate arm/method on every row) and in the report's
    Methods provenance section. This is the AUTO path's strategy:
    the cron's bare invocation runs it, while an explicit
    --cycle-id without --strategy still reproduces the legacy
    cycle-1/3 behaviour exactly."""
    t0 = time.time()
    run_dir = FACTORY_DIR / "runs" / cycle_id
    run_dir.mkdir(parents=True, exist_ok=True)
    lineage = LineageLog(run_dir / "lineage.jsonl")
    factory_lineage = LineageLog(FACTORY_DIR / "lineage.jsonl")
    lineage.append("growth_cycle_start", cycle_id=cycle_id,
                   strategy="cycle3")

    from . import champion as champion_mod
    champ_rec = champion_mod.ensure_record()
    champ_idx = cycle_number(cycle_id) % len(TARGETS)
    # Muse's fix, 2026-11-12 (cycle 006 crash): this block ran
    # before `cycle` was created below, raising UnboundLocalError
    # and killing the cycle before any training. Hold it in a
    # local and attach it once the cycle dict exists.
    champion_info = {
        "designated_target":
            f"{TARGETS[champ_idx][0]}/{TARGETS[champ_idx][1]}",
        "version_before": champ_rec["version"],
        "recipe_before": champ_rec["recipe"],
        "crowns_applied": [],
        "note": "crowns apply only in the births-kept branch, "
                "after serving verification"}

    if not (name_intent.DATA_DIR / "name_intent_train.json").exists():
        name_intent.build_datasets()
    intent_train = name_intent.load_train()
    intent_held = name_intent.load_held()

    snapshots = {
        "composer_config": (MODELS_DIR / "composer_config.json")
        .read_bytes(),
        "waking_dream_results": (LAB_ROOT / "waking-dream"
                                 / "results.json").read_bytes(),
        "registry": (FACTORY_DIR / "registry.json").read_bytes(),
    }
    snap_dir = run_dir / "snapshots"
    snap_dir.mkdir(exist_ok=True)
    for k, v in snapshots.items():
        (snap_dir / k).write_bytes(v)
    # Pre-cycle serving model files (cycle-006 repair; this block
    # was MISSING here until the cycle-007 repair — the rollback
    # call below passed model_snapshots that was never taken, so
    # cycle 007's rollback died with NameError and its regressed
    # births stayed serving): a birth overwrites the incumbent
    # file of the same name, so these bytes are the only restore
    # point if the cycle rolls back.
    model_snapshots = _snapshot_model_files(_target_child_names())
    models_snap_dir = snap_dir / "models"
    models_snap_dir.mkdir(exist_ok=True)
    for name, data in model_snapshots.items():
        if data is not None:
            (models_snap_dir / f"{name}.json").write_bytes(data)

    cycle: Dict[str, Any] = {
        "cycle_id": cycle_id,
        "date": time.strftime("%Y-%m-%d %H:%M %Z"),
        "targets": [f"{c}/{s}" for c, s in TARGETS],
        "levers": ["name-intent data family (Lever 1)",
                   "parent-initialized fine-tuning (Lever 2)",
                   "found-on-failure diet weighting (Fable)",
                   "recipe head-to-head at a fixed small budget, "
                   "winner chosen on a DEV split of train data "
                   "(Fable selection discipline)",
                   "breadth edit arm: thin full-network blend "
                   "vs concentrated single-module edit (Fable: "
                   "breadth beats concentration)",
                   "dream-first repair arm (improvised): parent "
                   "repaired on difficulty-filtered verified "
                   "dreams of its own measured failures, children "
                   "seeded from the repaired parent",
                   "persistent champion recipe (Fable-study "
                   "Build 1): one designated target per cycle "
                   "races the champion against its one-gene "
                   "mutant; a kept mutant birth with a positive "
                   "dev margin crowns the mutation",
                   "learned-say check (Fable) — measured only"],
        "strategy": "cycle3",
    }
    cycle["champion"] = champion_info
    if rotation is not None:
        cycle["novelty"] = rotation

    print(f"[{cycle_id}] battery BEFORE ...", flush=True)
    cycle["battery_before"] = measure_served_battery(run_dir, "before")
    bb = cycle["battery_before"]
    cycle["battery_overall_before"] = round(
        sum(v["score"] for v in bb.values()) / len(bb), 4)
    print(f"[{cycle_id}] harvest ...", flush=True)
    cycle["harvest"] = harvest_failures(intent_train)
    print(f"[{cycle_id}] learned-say experiment ...", flush=True)
    cycle["learned_say"] = learned_say_experiment()

    replay = replay_set()
    methods_cfg = {"seed": rotation["intent_seed"] if rotation
                   else 99}
    attempts: List[Dict[str, Any]] = []
    for cls, slice_name in TARGETS:
        print(f"[{cycle_id}] birth attempt {cls}/{slice_name} ...",
              flush=True)
        extra = cap_intent(intent_train, cls, slice_name,
                           seed=rotation["intent_seed"] if rotation
                           else 99)
        target_methods = dict(methods_cfg)
        if (cls, slice_name) == TARGETS[champ_idx]:
            target_methods["champion"] = True
        gate3_pre = _gate3_pre_state(
            f"bug-{cls}-{slice_name}-model")
        out = growth.attempt_birth(
            cls, slice_name, run_dir / "births" / f"{cls}-{slice_name}",
            lineage, cycle_id,
            extra_train=extra, extra_held=intent_held,
            arms=("scratch", "init"), init_train_extra=replay,
            failure_weight=True,
            pool_counts=rotation["pool_counts"] if rotation else None,
            methods=target_methods)
        if out["born"]:
            out = _gate3_prime(out, gate3_pre, run_dir, lineage,
                               cycle_id)
        out["intent_train_capped_n"] = len(extra)
        attempts.append(out)
        print(f"[{cycle_id}]   -> born={out['born']} "
              f"{out.get('rejection') or ''}", flush=True)
    cycle["attempts"] = attempts
    born = [a for a in attempts if a["born"]]
    cycle["rolled_back"] = False

    if born:
        print(f"[{cycle_id}] serving verification ...", flush=True)
        from .registry import load_registry
        prev_raw = load_registry()["compositions"][
            "bug-pattern-composed"]["evidence"][
                "fresh_sealed_baseline"]["acc"]
        judge = _sealed_judge(cycle_id, previous_acc=prev_raw)
        cycle["sealed_raw_composed"] = {
            "served_sealed_before": bb[
                "bug-pattern-composed-sealed-v2"]["score"],
            "raw_composed_before": prev_raw,
            "raw_composed_after": judge["composed_acc"],
            "per_class_recall_after": judge["per_class_recall"],
            "note": "the battery line is the SERVED (waking-dream) "
                    "number; the raw composed number is the audit's "
                    "baseline leg, re-recorded by the growth judge"}
        cycle["waking_dream_refresh"] = \
            _refresh_waking_dream_results(cycle_id)
        from .registry import write_registry
        write_registry()
        cycle["battery_after"] = measure_served_battery(run_dir,
                                                        "after")
        ba = cycle["battery_after"]
        cycle["battery_overall_after"] = round(
            sum(v["score"] for v in ba.values()) / len(ba), 4)
        cycle["audit"] = _full_audit()
        regressions = _battery_regressions(bb, ba)
        if regressions or not cycle["audit"]["ok"]:
            reason = ("serving verification failed: "
                      + ("; ".join(regressions) if regressions else "")
                      + (f"; audit failures: "
                         f"{cycle['audit']['failures']}"
                         if not cycle["audit"]["ok"] else ""))
            _rollback(born, snapshots, cycle_id, lineage, reason,
                      model_snapshots=model_snapshots)
            cycle["rolled_back"] = True
            cycle["rollback_reason"] = reason
            cycle["audit"] = _full_audit()
            cycle["champion"]["note"] = (
                "no crowns: the cycle rolled back — a "
                "rolled-back birth can never crown a recipe")
            print(f"[{cycle_id}] ROLLED BACK: {reason}", flush=True)
        else:
            cycle["champion"]["crowns_applied"] = \
                _apply_champion_crowns(cycle_id, attempts)
            cycle["champion"]["version_after"] = \
                champion_mod.load_record()["version"]
            if cycle["champion"]["crowns_applied"]:
                lineage.append(
                    "champion_crowned", cycle_id=cycle_id,
                    crowns=cycle["champion"]["crowns_applied"])
            print(f"[{cycle_id}] births KEPT; whole verified",
                  flush=True)
    else:
        cycle["audit"] = _full_audit()
        cycle["champion"]["note"] = (
            "no crowns: no births this cycle")

    cycle["next_attack"] = (
        "First cycle under the methods upgrade: read the "
        "per-candidate table — which arm (recipe / breadth / "
        "concentrated / dream-first vs the standing scratch+init "
        "grid) produced each target's best dual-gate candidate "
        "names where the next cycle pushes. An arm that never "
        "produces a competitive candidate across both targets is "
        "dropped from the grid rather than re-proved forever; a "
        "winning recipe becomes the next cycle's declared default "
        "candidate shape. The accumulator/comparison/range "
        "surfaces sealed for the earlier plan remain available "
        "when a target's binding bar is judge size, not candidate "
        "quality.")
    cycle["wall_seconds"] = round(time.time() - t0, 1)
    write_report(cycle)
    factory_lineage.append(
        "growth_cycle", cycle_id=cycle_id,
        run_dir=f"factory/runs/{cycle_id}",
        births=[a["child"] for a in born
                if not cycle["rolled_back"]],
        removed=[a["child"] for a in born if cycle["rolled_back"]],
        rejected=[a["child"] for a in attempts if not a["born"]],
        battery_overall_before=cycle["battery_overall_before"],
        battery_overall_after=cycle.get("battery_overall_after"),
        audit_ok=cycle["audit"]["ok"])
    lineage.append("growth_cycle_done", cycle_id=cycle_id,
                   wall_seconds=cycle["wall_seconds"])
    print(json.dumps({"cycle_id": cycle_id,
                      "born": [a["child"] for a in attempts
                               if a["born"]],
                      "rolled_back": cycle["rolled_back"],
                      "battery_overall_before":
                          cycle["battery_overall_before"],
                      "battery_overall_after":
                          cycle.get("battery_overall_after"),
                      "audit_ok": cycle["audit"]["ok"],
                      "wall_seconds": cycle["wall_seconds"]},
                     indent=1))
    return cycle


def main() -> int:
    ap = argparse.ArgumentParser(description="Factory growth cycle")
    ap.add_argument("--cycle-id", default=None,
                    help="omit for cron mode: the next id is derived "
                         "from the ledger (growth/ledger.jsonl). An "
                         "explicit id reproduces the legacy cycle-1/2 "
                         "invocations exactly (fixed seeds and grids, "
                         "no rotation unless --rotate is given).")
    ap.add_argument("--strategy", choices=("legacy", "cycle2",
                                           "cycle3"),
                    default=None,
                    help="legacy = the cycle-1 candidate generation; "
                         "cycle2 = merged recipes (mixture leans, "
                         "curricula, raised-cap variant) + the "
                         "learned-say v2 fit; cycle3 = legacy "
                         "skeleton + the methods arms (recipe "
                         "head-to-head on a dev split, breadth vs "
                         "concentrated edits, dream-first repair). "
                         "Default when omitted: cycle3 for an "
                         "auto-derived id (the cron path), legacy "
                         "for an explicit --cycle-id, so the legacy "
                         "invocations reproduce cycles 1-3 exactly")
    ap.add_argument("--rotate", action="store_true",
                    help="apply the per-cycle novelty rotation even "
                         "with an explicit --cycle-id")
    ap.add_argument("--preflight", action="store_true",
                    help="print the cron decision (derived id, "
                         "rotation, would-skip + why) and exit "
                         "without writing or training anything")
    args = ap.parse_args()
    auto = args.cycle_id is None
    cycle_id = args.cycle_id or next_cycle_id()
    strategy = args.strategy or ("cycle3" if auto else "legacy")
    rotation = rotation_spec(cycle_number(cycle_id)) \
        if (auto or args.rotate) else None
    if args.preflight:
        decision = preflight(cycle_id)
        decision["auto_id"] = auto
        decision["strategy"] = strategy
        decision["rotation"] = rotation
        print(json.dumps(decision, indent=1, default=str))
        return 0
    pf = preflight(cycle_id)
    if pf["would_skip"]:
        _skip_cycle(cycle_id, "; ".join(pf["reasons"]))
        return 0
    _acquire_lock(cycle_id)
    try:
        if strategy == "cycle2":
            cycle = run_cycle2(cycle_id, rotation=rotation)
        elif strategy == "cycle3":
            cycle = run_cycle3(cycle_id, rotation=rotation)
        else:
            cycle = run_cycle(cycle_id, rotation=rotation)
    except Exception as exc:  # noqa: BLE001 — alert, then propagate
        write_alert({"cycle_id": cycle_id,
                     "date": time.strftime("%Y-%m-%d %H:%M %Z"),
                     "rolled_back": False, "audit": {"ok": True},
                     "attempts": [],
                     "error": f"{type(exc).__name__}: {exc}"})
        raise
    finally:
        _release_lock()
    if cycle.get("rolled_back") or not cycle["audit"]["ok"]:
        path = write_alert(cycle)
        print(f"[{cycle_id}] ALERT written: {path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
