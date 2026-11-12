"""Specialist growth (Phase C): intake scan + split-birth protocol.

The registry grows only through MEASURED births:

  * Intake scans the lab's own evidence for gaps: adopted-version
    feedback (subjects now diagnose their v2s — see subjects.py),
    missing slice variants (a decidable slice of a class with no
    specialist of its own), and per-slice weakness of the serving
    parents.
  * A SPLIT birth: when a class's errors cluster into a coherent
    slice (decidable from the snippet alone — swarm/decomposers.py),
    a narrower child specialist is trained for that slice (original
    slice data + slice-filtered dreams, contamination-checked).
  * The birth gate (binding): the child must BEAT the parent on the
    slice's held-out subset, strictly. The remainder is served by
    the parent unchanged (routing is by slice), so remainder
    regression is impossible by construction — the child's remainder
    accuracy is still measured and recorded for the record.
  * Only a passed gate writes anything: the child model file and
    the composer strengths entry that routes its slice to it (the
    phase-4 protocol: config follows measured strength). A failed
    or under-data candidate writes nothing and is recorded as a
    rejected birth with its numbers.

Nothing here touches the coordinator (contest closed) or any
non-bug subject; growth targets the composition's classes, where
the slice machinery exists.
"""
from __future__ import annotations

import copy
import json
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

LAB_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(LAB_ROOT / "coding"))
sys.path.insert(0, str(LAB_ROOT))

from swarm import composers as C  # noqa: E402
from swarm import decomposers as D  # noqa: E402
from swarm import factory as F  # noqa: E402
from swarm import phase3 as P3  # noqa: E402

from . import champion as champion_mod  # noqa: E402
from . import dream as dream_mod  # noqa: E402
from . import dream_gen as G  # noqa: E402
from .executors import _atomic_json, contamination_filter, \
    difficulty_filter, measure  # noqa: E402
from .lineage import LineageLog  # noqa: E402

MODELS_DIR = LAB_ROOT / "coding" / "swarm" / "models"
MIN_SLICE_POS_TRAIN = 8     # below this a birth is not attempted


def _relabel(examples, cls):
    return [{"text": e["text"],
             "label": cls if e["label"] == cls else "other"}
            for e in examples]


def _slice_subset(examples, cls, slice_name):
    return [e for e in examples
            if cls not in D.SLICES or D.slice_of(cls, e["text"]) == slice_name]


# ------------------------------------------ methods arms (2026-11-11)
# Candidate-generation methods adopted from Fable's make-it-work
# line (METHODS-FROM-MAKE-IT-WORK.md) plus one improvised arm,
# switched on per birth attempt by the `methods` argument of
# attempt_birth. Default (methods=None) is the exact legacy
# behaviour — cycles 1-3 stay reproducible. Every candidate these
# arms produce goes through the SAME prune + dual-gate judging as
# every other candidate; the arms change only how candidates are
# GENERATED, never how they are judged. The held slices are never
# used to choose anything here: recipe selection reads a DEV split
# carved out of TRAIN data only.

METHODS_DEFAULTS = {"seed": 99,
                    "probe_epochs": 120,
                    "full_epochs": 800,
                    "breadth_probe_epochs": 300,
                    "repair_epochs": 200,
                    "thin_alpha": 0.3,
                    "dev_frac": 0.2}


def _dev_split(items: List[Dict[str, Any]], seed: int,
               frac: float = 0.2):
    """Stratified fit/dev split of TRAIN-side items (Fable's
    selection discipline: winners are chosen on dev, never on the
    judging slices). Deterministic in (items, seed). Classes with
    fewer than 5 items contribute nothing to dev — a 1-item dev
    reading would be noise dressed as signal."""
    rng = random.Random(seed)
    by_label: Dict[str, List[Dict[str, Any]]] = {}
    for e in items:
        by_label.setdefault(e["label"], []).append(e)
    fit: List[Dict[str, Any]] = []
    dev: List[Dict[str, Any]] = []
    for label in sorted(by_label):
        lst = list(by_label[label])
        rng.shuffle(lst)
        k = int(round(len(lst) * frac)) if len(lst) >= 5 else 0
        dev.extend(lst[:k])
        fit.extend(lst[k:])
    rng.shuffle(fit)
    rng.shuffle(dev)
    return fit, dev


def _blend_node(b, m, alpha: float):
    if isinstance(b, dict) or isinstance(m, dict):
        bd = b if isinstance(b, dict) else {}
        md = m if isinstance(m, dict) else {}
        return {k: _blend_node(bd.get(k, 0.0), md.get(k, 0.0), alpha)
                for k in set(bd) | set(md)}
    return float(b) + alpha * (float(m) - float(b))


def _blend_weights(base: Dict[str, Any], moved: Dict[str, Any],
                   alpha: float,
                   tensors: Optional[set] = None) -> Dict[str, Any]:
    """base + alpha * (moved - base) over float leaves. With
    `tensors` given, only those top-level weight groups move and
    the rest are copied from base untouched — the substrate-level
    shape of a concentrated edit; without it, every group moves by
    the same small alpha — the thin/breadth edit."""
    out: Dict[str, Any] = {}
    for k in set(base) | set(moved):
        if tensors is not None and k not in tensors:
            out[k] = copy.deepcopy(base.get(k, {}))
        else:
            out[k] = _blend_node(base.get(k, {}), moved.get(k, {}),
                                 alpha)
    return out


def _tensor_deltas(base: Dict[str, Any],
                   moved: Dict[str, Any]) -> Dict[str, float]:
    """Total |moved - base| per top-level weight group — which
    module a fine-tune most wanted to move (the indicted module,
    for the concentrated-edit control)."""
    def total(b, m):
        if isinstance(b, dict) or isinstance(m, dict):
            bd = b if isinstance(b, dict) else {}
            md = m if isinstance(m, dict) else {}
            return sum(total(bd.get(k, 0.0), md.get(k, 0.0))
                       for k in set(bd) | set(md))
        return abs(float(m) - float(b))
    return {k: total(base.get(k, {}), moved.get(k, {}))
            for k in set(base) | set(moved)}


def _clone_with_weights(src: F.TinyNet,
                        weights: Dict[str, Any]) -> F.TinyNet:
    m = F.TinyNet(src.name, src.niche, src.job, list(src.classes),
                  list(src.features), src.hidden, src.fmode)
    m.weights = weights
    return m


def _methods_arms(*, cls: str, slice_name: str, task, parent,
                  train_child, init_train, replay_part, held_slice,
                  held_bin_all, intent_held_slice, references,
                  pool_counts, lineage: LineageLog, cycle_id: str,
                  cfg: Dict[str, Any], attempts: list,
                  trained: list) -> Dict[str, Any]:
    """The three cycle-3 candidate arms. Appends candidate rows to
    `attempts` and (model, row) pairs to `trained` exactly the way
    attempt_birth's own arms do, and returns the provenance record
    stored on the attempt (and in the cycle JSON / report).

    (1) RECIPE HEAD-TO-HEAD (Fable): 3 training recipes at a fixed
        small budget on the target's TRAIN diet; the winner is
        picked on a DEV split of that diet; only the winner is
        retrained at full budget as a gate candidate.
    (2) BREADTH EDIT (Fable: breadth beats concentration): one
        parent-initialized probe fine-tune supplies a delta; the
        THIN candidate applies a small alpha of it to EVERY weight
        group, the CONCENTRATED control applies the full delta to
        only the single group that moved most. The gate decides
        which shape (if either) is real on this substrate.
    (3) DREAM-FIRST REPAIR (improvised here, labelled as such):
        the parent is first REPAIRED — a gentle parent-init
        fine-tune on difficulty-filtered, execution-verified dream
        items concentrated on the parent's measured train-side
        failures — and the arm's candidates are then seeded from
        the repaired parent instead of the raw parent. The full
        dream-cycle executor (dream.run_dream_subject) is a
        whole-composition pipeline with its own state and judging;
        it cannot run inside a birth attempt, so this arm uses its
        machinery pieces (gen_pool, contamination_filter,
        difficulty_filter) at birth scale. That is the closest
        honest version, and it is recorded as such.
    (4) CHAMPION RECIPE (Fable-study Build 1, 2026-11-12): only
        on the cycle's designated target (cfg["champion"] true):
        the persistent champion recipe (factory/champion.py)
        and a challenger mutating exactly ONE of its genes each
        train at full budget as ordinary gate candidates. Their
        DEV accuracies are read here (dev only — held never
        selects); whether the challenger is crowned is decided
        by the crown rule in factory/champion.py and applied by
        the cycle runner only after the cycle's births survive
        serving verification."""
    prov: Dict[str, Any] = {}
    seed = int(cfg.get("seed", METHODS_DEFAULTS["seed"]))
    probe_epochs = int(cfg.get("probe_epochs",
                               METHODS_DEFAULTS["probe_epochs"]))
    full_epochs = int(cfg.get("full_epochs",
                              METHODS_DEFAULTS["full_epochs"]))

    def _judge(m, row):
        acc_all = F.accuracy(m, held_bin_all)
        m.weights, acc_all = F._prune(m.weights, m, held_bin_all,
                                      acc_all)
        row["slice_heldout_acc"] = measure(m, held_slice)["acc"]
        row["params"] = m.param_count()
        if intent_held_slice is not None:
            row["intent_heldout_acc"] = \
                measure(m, intent_held_slice)["acc"]
        attempts.append(row)
        trained.append((m, row))
        return m

    def _train_and_judge(train_set, arm_label, method, **kw):
        row = {"arm": arm_label, "method": method,
               "epochs": kw.get("epochs", 800),
               "lr_scale": kw.get("lr_scale")}
        try:
            m = F.train_candidate(task, train=train_set, **kw)
        except ValueError as exc:
            row["blocked"] = str(exc)
            attempts.append(row)
            return None
        row["fmode"] = m.fmode
        row["hidden"] = m.hidden
        return _judge(m, row)

    # ---- (1) recipe head-to-head on a dev split of TRAIN data
    fit_child, dev = _dev_split(
        train_child, seed,
        float(cfg.get("dev_frac", METHODS_DEFAULTS["dev_frac"])))
    recipes = [
        {"id": "scratch-text-h4", "kind": "scratch",
         "kw": {"fmode": "text", "hidden": 4}, "diet": fit_child},
        {"id": "init-lr03", "kind": "init",
         "kw": {"lr_scale": 0.3, "init_from": parent},
         "diet": fit_child + replay_part},
        {"id": "init-lr10", "kind": "init",
         "kw": {"lr_scale": 1.0, "init_from": parent},
         "diet": fit_child + replay_part},
    ]
    hh: Dict[str, Any] = {"budget_epochs": probe_epochs,
                          "dev_n": len(dev), "fit_n": len(fit_child),
                          "recipes": [],
                          "note": "recipes chosen on a DEV split "
                                  "of the target's TRAIN diet; the "
                                  "held slices never select"}
    winner = None
    if dev:
        for r in recipes:
            try:
                pm = F.train_candidate(task, train=r["diet"],
                                       epochs=probe_epochs,
                                       **r["kw"])
                r["dev_acc"] = round(F.accuracy(pm, dev), 4)
                r["params"] = pm.param_count()
            except ValueError as exc:
                r["blocked"] = str(exc)
            hh["recipes"].append(
                {k: r[k] for k in ("id", "dev_acc", "params",
                                   "blocked") if k in r})
        scored = [r for r in recipes if "dev_acc" in r]
        if scored:
            winner = max(scored, key=lambda r: (r["dev_acc"],
                                                -r["params"]))
            hh["winner"] = winner["id"]
            hh["winner_dev_acc"] = winner["dev_acc"]
    else:
        hh["skipped"] = "dev split empty (diet too small)"
    prov["headtohead"] = hh
    if winner is not None:
        full_diet = train_child if winner["kind"] == "scratch" \
            else init_train
        full_kw = dict(winner["kw"])
        _train_and_judge(full_diet, f"recipe:{winner['id']}",
                         "recipe-headtohead", epochs=full_epochs,
                         **full_kw)

    # ---- (2) breadth vs concentrated edit of one probe delta
    breadth_epochs = int(cfg.get(
        "breadth_probe_epochs",
        METHODS_DEFAULTS["breadth_probe_epochs"]))
    thin_alpha = float(cfg.get("thin_alpha",
                               METHODS_DEFAULTS["thin_alpha"]))
    br: Dict[str, Any] = {"probe_epochs": breadth_epochs,
                          "thin_alpha": thin_alpha}
    try:
        probe = F.train_candidate(task, train=init_train,
                                  epochs=breadth_epochs,
                                  lr_scale=1.0, init_from=parent)
        deltas = _tensor_deltas(parent.weights, probe.weights)
        indicted = max(deltas, key=deltas.get) if deltas else None
        br["tensor_deltas"] = {k: round(v, 4)
                               for k, v in deltas.items()}
        br["indicted_tensor"] = indicted
        thin = _clone_with_weights(
            probe, _blend_weights(parent.weights, probe.weights,
                                  thin_alpha))
        _judge(thin, {"arm": "breadth", "method": "breadth-thin-edit",
                      "epochs": breadth_epochs, "lr_scale": 1.0,
                      "fmode": thin.fmode, "hidden": thin.hidden})
        if indicted is not None:
            conc = _clone_with_weights(
                probe, _blend_weights(parent.weights, probe.weights,
                                      1.0, tensors={indicted}))
            _judge(conc, {"arm": "concentrated",
                          "method": "concentrated-edit-control",
                          "epochs": breadth_epochs, "lr_scale": 1.0,
                          "fmode": conc.fmode, "hidden": conc.hidden})
    except ValueError as exc:
        br["blocked"] = str(exc)
    prov["breadth"] = br

    # ---- (3) dream-first repair (improvised arm)
    df: Dict[str, Any] = {"note": "improvised arm: parent repaired "
                                  "on difficulty-filtered verified "
                                  "dreams of its own failures, then "
                                  "children seeded from the "
                                  "repaired parent"}
    repair_epochs = int(cfg.get("repair_epochs",
                                METHODS_DEFAULTS["repair_epochs"]))
    pool, _gen_stats = G.gen_pool(
        pool_counts or {1: 30, 2: 26, 3: 26}, seed=seed + 5251,
        group_prefix="repairdream")
    pool_clean, _dropped = contamination_filter(pool, references,
                                                "code")
    dream_slice = _relabel(_slice_subset(pool_clean, cls,
                                         slice_name), cls)
    kept, fstats = difficulty_filter(parent, dream_slice)
    df.update({"pool_n": len(pool), "pool_clean_n": len(pool_clean),
               "dream_slice_n": len(dream_slice),
               "kept_n": len(kept),
               "kept_hard_n": fstats.get("hard_items_kept"),
               "kept_easy_n": fstats.get("easy_items_kept"),
               "repair_epochs": repair_epochs})
    if kept:
        wrong_child = [e for e in train_child
                       if parent.run({"text": e["text"]})["output"]
                       != e["label"]]
        cap = max(50, len(kept))
        if len(replay_part) > cap:
            stride = max(1, len(replay_part) // cap)
            replay_capped = replay_part[::stride][:cap]
        else:
            replay_capped = list(replay_part)
        repair_diet = kept + wrong_child + replay_capped
        df["repair_diet_n"] = len(repair_diet)
        df["parent_wrong_train_items"] = len(wrong_child)
        try:
            repaired = F.train_candidate(
                task, train=repair_diet, epochs=repair_epochs,
                lr_scale=0.3, init_from=parent)
            for ep in sorted({300, full_epochs}):
                _train_and_judge(init_train, "dream-first",
                                 "dream-first-repair", epochs=ep,
                                 lr_scale=0.3, init_from=repaired)
        except ValueError as exc:
            df["blocked"] = str(exc)
    else:
        df["skipped"] = ("difficulty filter kept no dream items "
                         "for this slice — no repair attempted")
    prov["dream_first"] = df

    # ---- (4) champion recipe: one-gene challenger (Build 1)
    ch: Dict[str, Any] = {"note": "persistent champion recipe "
                                  "(Fable-study Build 1): on the "
                                  "cycle's designated target, the "
                                  "champion and its one-gene "
                                  "mutant train at full budget "
                                  "as gate candidates; the crown "
                                  "reads DEV only and is applied "
                                  "by the cycle runner after "
                                  "serving verification"}
    if cfg.get("champion"):
        try:
            rec = champion_mod.load_record()
            champ_recipe = rec["recipe"]
            mutant_recipe, mutation = champion_mod.mutate(
                champ_recipe, random.Random(seed + 90210))
            ch.update({"version": rec["version"],
                       "recipe": champ_recipe,
                       "mutation": mutation,
                       "mutant_recipe": mutant_recipe})
            trained_by_label: Dict[str, Any] = {}
            for label, recipe in (("champion", champ_recipe),
                                  ("champion-mutant",
                                   mutant_recipe)):
                kw, diet_kind = champion_mod.train_kwargs(
                    recipe, parent)
                diet = init_train if diet_kind == "init" \
                    else train_child
                n_before = len(trained)
                _train_and_judge(diet, label, "champion-recipe",
                                 **kw)
                if len(trained) > n_before:
                    trained_by_label[label] = trained[-1][0]
            if dev:
                for label, key in (("champion", "champ_dev_acc"),
                                   ("champion-mutant",
                                    "mutant_dev_acc")):
                    if label in trained_by_label:
                        ch[key] = round(
                            F.accuracy(trained_by_label[label],
                                       dev), 4)
                if "champ_dev_acc" in ch and \
                        "mutant_dev_acc" in ch:
                    ch["dev_margin"] = round(
                        ch["mutant_dev_acc"]
                        - ch["champ_dev_acc"], 4)
            else:
                ch["dev_note"] = ("dev split empty — no margin "
                                  "can be read, no crown "
                                  "possible this cycle")
        except (ValueError, KeyError) as exc:
            ch["blocked"] = str(exc)
    else:
        ch["skipped"] = ("not this cycle's designated champion "
                         "target")
    prov["champion"] = ch

    lineage.append("birth_methods", cycle_id=cycle_id, subject=cls,
                   slice=slice_name,
                   headtohead_winner=(prov.get("headtohead") or {})
                   .get("winner"),
                   headtohead_dev=(prov.get("headtohead") or {})
                   .get("winner_dev_acc"),
                   breadth_indicted=(prov.get("breadth") or {})
                   .get("indicted_tensor"),
                   dream_first_kept=(prov.get("dream_first") or {})
                   .get("kept_n"),
                   champion_mutation=(prov.get("champion") or {})
                   .get("mutation"),
                   champion_dev_margin=(prov.get("champion") or {})
                   .get("dev_margin"))
    return prov


# ------------------------------------------------------------ intake scan
def scan_intake(lab_root: Path) -> Dict[str, Any]:
    lab_root = Path(lab_root)
    config = C.load_config()
    multi_train = P3.gen_bug_patterns(P3._BUG_TEMPLATES_TRAIN, 21)
    multi_held = P3.gen_bug_patterns(P3._BUG_TEMPLATES_HELD, 22)
    reg = dream_mod.load_bug_registry()
    versions: Dict[str, Any] = {}
    models_dir = lab_root / "coding" / "swarm" / "models"
    for f in sorted(models_dir.glob("*.json")):
        rec = json.loads(f.read_text())
        if rec.get("adopted"):
            versions[rec["name"]] = {
                "path": rec.get("path"), "heldout_acc": rec.get("heldout_acc"),
                "substrate": rec.get("substrate", "fp"),
                "factory_cycle": rec.get("factory_cycle")}
    candidates: List[Dict[str, Any]] = []
    for cls in C.DEFECT_CLASSES:
        parent = reg.get(f"bug-{cls}-model")
        if parent is None:
            continue
        for slice_name in config.get("strengths", {}).get(cls, {}):
            child_name = f"bug-{cls}-{slice_name}-model"
            exists = (models_dir / f"{child_name}.json").exists()
            routed = config["strengths"][cls][slice_name] == "slice"
            held_slice = _relabel(_slice_subset(multi_held, cls,
                                                slice_name), cls)
            train_slice = _slice_subset(multi_train, cls, slice_name)
            parent_slice = measure(parent, held_slice) if held_slice \
                else {"acc": None, "n": 0}
            candidates.append({
                "cls": cls, "slice": slice_name, "child": child_name,
                "child_exists": exists, "routed_to_child": routed,
                "parent_slice_heldout_acc": parent_slice["acc"],
                "parent_slice_heldout_n": parent_slice["n"],
                "train_slice_n": len(train_slice),
                "train_slice_pos": sum(1 for e in train_slice
                                       if e["label"] == cls),
                # "whole" is the class itself, not a slice of it —
                # a split needs a proper sub-class.
                "birth_candidate": (not exists) and not routed
                                   and slice_name != "whole"})
    return {"adopted_versions": versions,
            "slice_candidates": candidates,
            "standing_proposals": [
                {"job": "second-view generator specialist (per niche)",
                 "status": "partially answered in Phase C: dream_gen "
                           "produces verified second views inside the "
                           "dream cycle; a standalone serving specialist "
                           "remains unbuilt"},
                {"job": "ternary substrate defaults per niche",
                 "status": "measured in Phase C: fp won all five "
                           "head-to-heads; ternary coexists where "
                           "surgery repaired it (secret-line)"}]}


# ------------------------------------------------------------ split birth
def attempt_birth(cls: str, slice_name: str, run_dir: Path,
                  lineage: LineageLog, cycle_id: str,
                  pool_counts: Optional[Dict[int, int]] = None,
                  train_full: bool = False,
                  train_full_pool: bool = False,
                  extra_train: Optional[List[Dict[str, Any]]] = None,
                  extra_held: Optional[List[Dict[str, Any]]] = None,
                  arms: tuple = ("scratch",),
                  init_train_extra: Optional[List[Dict[str, Any]]] = None,
                  failure_weight: bool = False,
                  slice_repeat: int = 1,
                  intent_repeat: int = 1,
                  extra_configs: Optional[List[Dict[str, Any]]] = None,
                  methods: Optional[Dict[str, Any]] = None,
                  ) -> Dict[str, Any]:
    """One gated split-birth attempt. Writes nothing unless the gate
    passes; the attempt and its numbers are recorded either way.

    pool_counts: the dream-pool band counts for the slice's data
    supply (assembly 2026-11-10 repair parameter — the default is
    the Phase C supply, {1: 30, 2: 26, 3: 26}; the gate, the held
    slice and the training protocol are unchanged by it).

    train_full: the assembly's second repair — instead of training
    the child on the slice subset alone, train it on the parent's
    own distribution (the full relabeled training set) with the
    slice's items (real + dreamed) oversampled x3. Same gate,
    same held slice, same config sweep.

    Growth-cycle parameters (2026-11-11; defaults reproduce the
    legacy behaviour exactly):

    extra_train: additional multiclass training items (the
    name-intent family, factory/name_intent.py) — relabeled and
    slice-filtered like every other supply, then added to the
    child's diet.
    extra_held: an additional PRISTINE held set (the name-intent
    held partition). When given, the birth gate becomes DUAL: the
    winning candidate must beat the parent on the phase-3 held
    slice AND on the extra held slice (both strict), and selection
    runs over candidates passing both gates.
    arms: which training arms compete under the identical gates —
    "scratch" (the legacy 6-config from-scratch sweep) and/or
    "init" (Lever 2: parent-initialized fine-tuning on slice data
    + extra_train + init_train_extra replay, at the parent's own
    architecture, epochs x lr_scale grid).
    init_train_extra: replay items (multiclass) added ONLY to the
    init arm's diet — the full-distribution slice that stops a
    fine-tuned child from forgetting what the parent knew.
    failure_weight: found-on-failure diet weighting (borrowed from
    Fable's founding rule): items in the child's diet that the
    PARENT currently gets wrong are duplicated once, so the diet
    leans toward the parent's measured failures.

    Growth-cycle-2 parameters (2026-11-11; defaults reproduce the
    cycle-1 behaviour exactly):

    slice_repeat / intent_repeat: mixture weights for the child's
    diet — the (phase-3 train slice + dream slice) part and the
    name-intent part are repeated this many times, so a cycle can
    lean the mixture toward the template slice or toward intent
    supply without changing either supply itself.
    extra_configs: additional candidate configs run through the
    same _run_config path (same gates, same judge surfaces) after
    the standard arms. Each entry: {arm_label, fmode, hidden,
    epochs, lr_scale, diet, mix, init_from, failure_weight}.
    diet is "child" (the call's composed diet), "init" (child +
    replay), or "mix" (built from the retained parts: mix =
    {"slice": a, "intent": b, "replay": c} repeats). init_from is
    None (from scratch), "parent" (Lever 2), or "stage:<arm_label>"
    — initialise from an earlier candidate trained IN THIS CALL,
    which is what makes two-stage curricula (intent-first then
    template polish, or the reverse) expressible in one attempt.

    Methods parameter (2026-11-11; None reproduces every earlier
    behaviour exactly):

    methods: when a dict is given, the cycle-3 candidate arms run
    after the standard arms and extra_configs — a recipe
    head-to-head with dev-split selection, a breadth-vs-
    concentrated edit pair, and a dream-first repair family (see
    _methods_arms). Keys override METHODS_DEFAULTS (seed, probe /
    full / breadth-probe / repair epochs, thin_alpha, dev_frac).
    Candidates from these arms enter the same selection and the
    same dual gate as all others; the provenance record is stored
    on the attempt dict under "methods"."""
    out: Dict[str, Any] = {"cls": cls, "slice": slice_name,
                           "child": f"bug-{cls}-{slice_name}-model",
                           "born": False}
    multi_train = P3.gen_bug_patterns(P3._BUG_TEMPLATES_TRAIN, 21)
    multi_held = P3.gen_bug_patterns(P3._BUG_TEMPLATES_HELD, 22)
    reg = dream_mod.load_bug_registry()
    parent = reg[f"bug-{cls}-model"]

    train_slice = _slice_subset(multi_train, cls, slice_name)
    held_slice = _relabel(_slice_subset(multi_held, cls, slice_name), cls)
    held_rest = _relabel([e for e in multi_held
                          if e not in _slice_subset(multi_held, cls,
                                                    slice_name)], cls)
    # Slice dreams: fresh pool, slice-filtered, contamination-checked
    # against everything the parent trained on.
    from swarm import dream as swarm_dream
    references = multi_train + multi_held + \
        swarm_dream.gen_dream_bug_examples()
    pool, _ = G.gen_pool(pool_counts or {1: 30, 2: 26, 3: 26},
                         seed=5150, group_prefix="birthdream")
    pool_clean, _ = contamination_filter(pool, references, "code")
    dream_slice = _slice_subset(pool_clean, cls, slice_name)
    slice_part = _relabel(train_slice, cls) + \
        _relabel(dream_slice, cls)
    intent_part: List[Dict[str, Any]] = []
    if extra_train:
        intent_part = _relabel(_slice_subset(extra_train, cls,
                                             slice_name), cls)
        out["intent_train_n"] = len(intent_part)
        out["intent_train_pos"] = sum(1 for e in intent_part
                                      if e["label"] == cls)
    train_child = slice_part * slice_repeat + \
        intent_part * intent_repeat
    if slice_repeat != 1 or intent_repeat != 1:
        out["diet_repeats"] = {"slice": slice_repeat,
                               "intent": intent_repeat}
    if train_full:
        slice_part = train_child
        train_child = _relabel(multi_train, cls) + \
            slice_part * 3
        out["train_mode"] = ("full-distribution + slice x3 "
                             "(assembly repair 2)")
    if train_full_pool:
        # Assembly repair 2b: the template train set is tiny and
        # its size varies with process RNG state, so repair 2's
        # "full distribution" was only ~48 items. The distribution
        # the parent family actually learned from is the dream
        # pool (all classes, execution-verified, fixed-seed
        # deterministic): train on ALL of it, slice x3 on top.
        slice_part = train_child
        train_child = _relabel(pool_clean, cls) + slice_part * 3
        out["train_mode"] = ("full dream-pool distribution + "
                             "slice x3 (assembly repair 2b)")
        out["pool_clean_n"] = len(pool_clean)
    if failure_weight:
        hard = [e for e in train_child
                if parent.run({"text": e["text"]})["output"]
                != e["label"]]
        train_child = train_child + hard
        out["failure_weighted_extra"] = len(hard)
    n_pos = sum(1 for e in train_child if e["label"] == cls)
    out.update({"train_slice_n": len(train_slice),
                "dream_slice_n": len(dream_slice),
                "train_child_n": len(train_child),
                "train_child_pos": n_pos,
                "held_slice_n": len(held_slice)})
    parent_slice = measure(parent, held_slice)
    out["parent_slice_heldout_acc"] = parent_slice["acc"]
    # The second gate surface (name-intent held slice), when given:
    # the parent's number on it is measured with the same routing
    # population the child would serve.
    intent_held_slice = None
    parent_intent = None
    if extra_held:
        intent_held_slice = _relabel(
            _slice_subset(extra_held, cls, slice_name), cls)
        parent_intent = measure(parent, intent_held_slice)
        out["parent_intent_heldout_acc"] = parent_intent["acc"]
        out["intent_held_slice_n"] = len(intent_held_slice)
        out["intent_held_slice_pos"] = sum(
            1 for e in intent_held_slice if e["label"] == cls)
    lineage.append("birth_attempt", cycle_id=cycle_id, **{
        k: out[k] for k in ("cls", "slice", "child", "train_child_n",
                            "train_child_pos", "held_slice_n",
                            "parent_slice_heldout_acc")})
    if n_pos < MIN_SLICE_POS_TRAIN or not held_slice:
        out["rejection"] = (f"insufficient data: {n_pos} positive "
                            f"training items (min {MIN_SLICE_POS_TRAIN}) "
                            f"or empty held slice — no birth attempted "
                            f"(fail-closed)")
        lineage.append("birth_rejected", cycle_id=cycle_id, subject=cls,
                       slice=slice_name, reason=out["rejection"])
        return out

    task = {"name": out["child"], "niche": "debugging",
            "job": f"decide whether a {slice_name}-slice snippet's "
                   f"defect is {cls} (vs anything else)",
            "classes": [cls, "other"], "train": train_child,
            "heldout": held_slice}
    held_bin_all = _relabel(multi_held, cls)
    attempts = []
    trained: List[Any] = []

    def _run_config(train_set, **kw):
        arm_label = kw.pop("arm_label", "scratch")
        epochs = kw.get("epochs", 800)
        lr_scale = kw.get("lr_scale")
        m = F.train_candidate(task, train=train_set, **kw)
        acc_all = F.accuracy(m, held_bin_all)
        m.weights, acc_all = F._prune(m.weights, m, held_bin_all,
                                      acc_all)
        sl = measure(m, held_slice)
        row = {"arm": arm_label,
               "fmode": m.fmode, "hidden": m.hidden,
               "epochs": epochs,
               "lr_scale": lr_scale,
               "slice_heldout_acc": sl["acc"],
               "params": m.param_count()}
        if intent_held_slice:
            row["intent_heldout_acc"] = \
                measure(m, intent_held_slice)["acc"]
        attempts.append(row)
        trained.append((m, row))
        return m, row

    if "scratch" in arms:
        for fmode in ("text", "code"):
            for hidden in (0, 4, 8):
                _run_config(train_child, fmode=fmode, hidden=hidden,
                            epochs=800, arm_label="scratch")
    init_train = train_child + _relabel(init_train_extra or [], cls)
    out["init_train_n"] = len(init_train)
    if "init" in arms:
        for epochs in (300, 800):
            for lr_scale in (0.3, 1.0):
                try:
                    _run_config(init_train, epochs=epochs,
                                lr_scale=lr_scale, init_from=parent,
                                arm_label="init")
                except ValueError as exc:
                    attempts.append({"arm": "init", "epochs": epochs,
                                     "lr_scale": lr_scale,
                                     "blocked": str(exc)})
    if extra_configs:
        # Cycle-2 candidates: merged recipes, mixture variants and
        # two-stage curricula, under the identical dual gate.
        replay_part = _relabel(init_train_extra or [], cls)
        stage_models: Dict[str, Any] = {}
        for m_, r_ in trained:
            if "arm" in r_:
                stage_models.setdefault(r_["arm"], m_)
        for cfg in extra_configs:
            label = cfg.get("arm_label", "c2")
            diet_kind = cfg.get("diet", "child")
            if diet_kind == "init":
                diet = init_train
            elif diet_kind == "mix":
                mix = cfg.get("mix", {})
                diet = slice_part * int(mix.get("slice", 1)) + \
                    intent_part * int(mix.get("intent", 1)) + \
                    replay_part * int(mix.get("replay", 0))
                if cfg.get("failure_weight"):
                    hard = [e for e in diet
                            if parent.run({"text": e["text"]})["output"]
                            != e["label"]]
                    diet = diet + hard
            else:
                diet = train_child
            kw = {k: cfg[k] for k in ("fmode", "hidden", "epochs",
                                      "lr_scale") if k in cfg}
            src = cfg.get("init_from")
            try:
                if src == "parent":
                    _run_config(diet, arm_label=label,
                                init_from=parent, **kw)
                elif isinstance(src, str) and \
                        src.startswith("stage:"):
                    sm = stage_models.get(src[len("stage:"):])
                    if sm is None:
                        attempts.append(
                            {"arm": label,
                             "blocked": f"stage model {src} not "
                                        f"available"})
                        continue
                    _run_config(diet, arm_label=label, init_from=sm,
                                **kw)
                else:
                    _run_config(diet, arm_label=label, **kw)
            except ValueError as exc:
                attempts.append({"arm": label, "blocked": str(exc)})
                continue
            if trained:
                stage_models[label] = trained[-1][0]
    if methods is not None:
        mcfg = dict(METHODS_DEFAULTS)
        mcfg.update(methods)
        out["methods"] = _methods_arms(
            cls=cls, slice_name=slice_name, task=task, parent=parent,
            train_child=train_child, init_train=init_train,
            replay_part=_relabel(init_train_extra or [], cls),
            held_slice=held_slice, held_bin_all=held_bin_all,
            intent_held_slice=intent_held_slice,
            references=references, pool_counts=pool_counts,
            lineage=lineage, cycle_id=cycle_id, cfg=mcfg,
            attempts=attempts, trained=trained)
    out["attempts"] = attempts
    scored = [(m, r) for m, r in trained
              if "slice_heldout_acc" in r]
    if intent_held_slice is not None and parent_intent is not None:
        eligible = [(m, r) for m, r in scored
                    if r["slice_heldout_acc"] > parent_slice["acc"]
                    and r["intent_heldout_acc"]
                    > parent_intent["acc"]]
        eligible.sort(key=lambda t: (-t[1]["slice_heldout_acc"],
                                     -t[1]["intent_heldout_acc"],
                                     t[1]["params"]))
        best = eligible[0] if eligible else None
    else:
        best = None
        for m, r in scored:
            if best is None or r["slice_heldout_acc"] \
                    > best[1]["slice_heldout_acc"]:
                best = (m, r)
    if best is None:
        if scored:
            top = max(scored, key=lambda t: t[1]["slice_heldout_acc"])
            out["child_slice_heldout_acc"] = \
                top[1]["slice_heldout_acc"]
        if isinstance((out.get("methods") or {}).get("champion"),
                      dict):
            out["methods"]["champion"]["mutant_born"] = False
            out["methods"]["champion"]["champion_born"] = False
        out["rejection"] = (
            f"gate failed: no candidate beat the parent on "
            f"{'both held slices' if intent_held_slice else 'the held slice'} "
            f"(phase-3 slice: parent {parent_slice['acc']}"
            + (f", best child "
               f"{out.get('child_slice_heldout_acc')}; name-intent "
               f"slice: parent {parent_intent['acc']}, best child "
               f"{max((r['intent_heldout_acc'] for _, r in scored), default=None)}"
               if intent_held_slice else "")
            + ") — no birth")
        lineage.append("birth_rejected", cycle_id=cycle_id, subject=cls,
                       slice=slice_name, reason=out["rejection"],
                       child_acc=out.get("child_slice_heldout_acc"),
                       parent_acc=parent_slice["acc"])
        return out
    child, win_row = best
    out["child_slice_heldout_acc"] = win_row["slice_heldout_acc"]
    out["winning_arm"] = win_row.get("arm")
    if isinstance((out.get("methods") or {}).get("champion"),
                  dict):
        # The crown rule's birth leg, recorded here; the crown
        # itself is applied by the cycle runner only if this
        # birth survives serving verification (never on rollback).
        out["methods"]["champion"]["mutant_born"] = \
            win_row.get("arm") == "champion-mutant"
        out["methods"]["champion"]["champion_born"] = \
            win_row.get("arm") == "champion"
    if intent_held_slice is not None:
        out["child_intent_heldout_acc"] = win_row["intent_heldout_acc"]
    out["child_remainder_heldout_acc"] = measure(child, held_rest)["acc"] \
        if held_rest else None
    out["parent_remainder_heldout_acc"] = measure(parent, held_rest)["acc"] \
        if held_rest else None
    if intent_held_slice is None and \
            not (win_row["slice_heldout_acc"] > parent_slice["acc"]):
        out["rejection"] = (f"gate failed: child slice held-out "
                            f"{win_row['slice_heldout_acc']} does not "
                            f"beat parent {parent_slice['acc']} "
                            f"(n={len(held_slice)}) — no birth")
        lineage.append("birth_rejected", cycle_id=cycle_id, subject=cls,
                       slice=slice_name, reason=out["rejection"],
                       child_acc=win_row["slice_heldout_acc"],
                       parent_acc=parent_slice["acc"])
        return out

    # Gate passed: the child is born. Save it, route its slice to it
    # (config backup first), record the birth in lineage.
    gate_desc = ("child slice held-out > parent slice held-out; "
                 "remainder served by parent unchanged")
    if intent_held_slice is not None:
        gate_desc = ("DUAL gate: child > parent on the phase-3 held "
                     "slice AND on the pristine name-intent held "
                     "slice; remainder served by parent unchanged")
    path_desc = "factory birth — split (Phase C)"
    if extra_train or "init" in arms:
        path_desc = ("factory birth — split + name-intent data"
                     + (" + parent-initialized fine-tuning"
                        if win_row.get("arm") == "init" else "")
                     + " (growth cycle)")
    extra = {"path": path_desc,
             "heldout_acc": win_row["slice_heldout_acc"],
             "train_n": len(train_child), "heldout_n": len(held_slice),
             "incumbents": [{"name": f"bug-{cls}-model",
                             "acc": parent_slice["acc"]}],
             "bar": parent_slice["acc"], "attempts": attempts,
             "adopted": True, "factory_cycle": cycle_id,
             "birth": {"parent": f"bug-{cls}-model", "slice": slice_name,
                       "gate": gate_desc,
                       "winning_arm": win_row.get("arm"),
                       "intent_heldout_acc":
                           win_row.get("intent_heldout_acc"),
                       "parent_intent_heldout_acc":
                           parent_intent["acc"]
                           if parent_intent else None}}
    if "methods" in out:
        extra["birth"]["methods"] = out["methods"]
    child.name = out["child"]
    F.save_model(child, extra, directory=MODELS_DIR)
    cfg_path = MODELS_DIR / "composer_config.json"
    backup_dir = Path(run_dir) / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    (backup_dir / "composer_config.before-birth.json").write_text(
        cfg_path.read_text())
    config = json.loads(cfg_path.read_text())
    config.setdefault("strengths", {}).setdefault(cls, {})[slice_name] = \
        "slice"
    _atomic_json(cfg_path, config)
    out["born"] = True
    out["adopted_file"] = f"coding/swarm/models/{out['child']}.json"
    # Post-birth composed reference (NOT a gate: the confirm set was
    # spent by the dream cycle; this is a same-set re-measurement,
    # labeled as such).
    reg2 = dream_mod.load_bug_registry()
    acc2, rec2 = dream_mod.composed_eval(reg2, multi_held)
    out["composed_reference_after_birth"] = {"acc": acc2, "recall": rec2,
                                             "pristine": False}
    lineage.append("specialist_birth", cycle_id=cycle_id, subject=cls,
                   slice=slice_name, child=out["child"],
                   child_acc=win_row["slice_heldout_acc"],
                   parent_acc=parent_slice["acc"],
                   composed_reference=acc2)
    return out
