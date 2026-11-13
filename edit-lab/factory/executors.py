"""Real executors for the factory loop (Phase B).

Phase A planned; this module executes — for the one plan shape that has
an executor, Action.TRAIN_DATA_WIDEN on Tier-0 specialists:

    harvest fresh surfaces (factory/harvest_data.py pools)
      -> contamination check (never train on anything that resembles
         a training / held-out / battery / screen / confirm item)
      -> difficulty filter (keep what the incumbent gets WRONG, plus a
         per-class diversity quota of what it gets right — the s1
         lesson: delete what the learner already solves, keep balance)
      -> retrain Tier-0 candidates on original + widened data
         (smallest-first: linear -> mlp4 -> mlp8, the phase-3 search)
      -> MEASURE: same-distribution held-out + a fresh-surface screen
      -> finalist spends the confirm set ONCE
      -> win-gate + regression gate decide (contracts.WinGate):
         adopt (saved as a NEW versioned model file, incumbent kept as
         fallback) or revert. The gate decides, never the operator.

Honesty rules carried over from Phase A:
  * measured=False remains the default everywhere a number was not
    actually measured; this module's Verification objects carry
    measured=True only because every number in them was produced by
    running a model on a set in this process.
  * A SHADOW_PASS is never a win: shadow verdicts come from stages.py;
    measured verdicts here are WIN / REVERT / BLOCKED only.
  * The original battery items are re-measured as a REFERENCE only —
    they were the diagnosis evidence, so they are never the gate.

Anything without an executor (Tier-1 adapters, compositions, weight
edits) fails closed in REAL mode: BLOCKED, with the reason recorded.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

LAB_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(LAB_ROOT / "coding"))
sys.path.insert(0, str(LAB_ROOT))

from swarm import factory as F  # noqa: E402
from swarm import phase3 as P3  # noqa: E402

from . import harvest_data  # noqa: E402
from .contracts import Subject, Verification, WinGate  # noqa: E402
from .lineage import LineageLog  # noqa: E402

MODELS_DIR = LAB_ROOT / "coding" / "swarm" / "models"
REGRESSION_TOLERANCE = 0.02  # the win-gate's held-out regression allowance


# ------------------------------------------------------------ subject config
def _cfg(niche, job, classes, fmode, epochs, train_fn, held_fn, battery_items):
    return {"niche": niche, "job": job, "classes": classes, "fmode": fmode,
            "epochs": epochs, "train_fn": train_fn, "held_fn": held_fn,
            "battery_items": battery_items}


def _battery():
    import hive_battery as B
    return B


def subject_config(subject_id: str) -> Optional[Dict[str, Any]]:
    B = _battery()
    table = {
        "error-class-model": _cfg(
            "debugging",
            "classify a failure text into its exception class",
            ["AssertionError", "AttributeError", "FileNotFoundError",
             "IndexError", "KeyError", "ModuleNotFoundError", "NameError",
             "RuntimeError", "SyntaxError", "TypeError", "ValueError",
             "ZeroDivisionError"], "text0", 300,
            lambda: P3.gen_error_texts()[0],
            lambda: P3.gen_error_texts()[1],
            B.ERROR_ITEMS),
        "contract-judgment-model": _cfg(
            "review",
            "judge a snippet against the house contract (no mutation, empty-safe, none-safe)",
            P3._CONTRACT_CLASSES, "code", 300,
            lambda: P3.gen_contract(P3._CONTRACT_TRAIN, 31),
            lambda: P3.gen_contract(P3._CONTRACT_HELD, 32),
            B.CONTRACT_ITEMS),
        "gap-move-model": _cfg(
            "meta",
            "classify a failure/lesson text into the growth move it calls for",
            P3._GAP_CLASSES, "words", 800,
            lambda: P3.gen_gap_moves(P3._GAP_TRAIN, 41),
            lambda: P3.gen_gap_moves(P3._GAP_HELD, 42),
            B.GAP_ITEMS),
        "secret-line-model": _cfg(
            "security",
            "classify one code line: hard-coded secret or benign",
            ["benign", "secret"], "secret", 300,
            lambda: P3.gen_secret_lines("train", 61),
            lambda: P3.gen_secret_lines("heldout", 62),
            B.SECRET_ITEMS),
        "commit-type-model": _cfg(
            "vcs",
            "classify a commit message into its conventional type",
            P3._COMMIT_CLASSES, "words", 800,
            lambda: P3.gen_commit_types(P3._COMMIT_TRAIN, 51),
            lambda: P3.gen_commit_types(P3._COMMIT_HELD, 52),
            B.COMMIT_ITEMS),
    }
    # Niche-expansion wave 1 (2026-11-13, coordinator's adoption
    # sitting; factory/niche_expansion/PLAN.md section 4): configs
    # live in factory/niche_expansion/subjects.py and are merged here
    # for ADOPTED jobs only, so full_audit can re-measure them on
    # their deterministic held sets. A rejected/unadopted expansion
    # subject (data-format-model) is deliberately absent.
    from .niche_expansion import subjects as _expansion_subjects
    for _sid in ("sec-code-model", "sql-statement-model"):
        _c = _expansion_subjects.SUBJECTS[_sid]
        table[_sid] = _cfg(_c["niche"], _c["job"], _c["classes"],
                           _c["fmode"], _c["epochs"], _c["train_fn"],
                           _c["held_fn"], _c["battery_items"])
    return table.get(subject_id)


SUPPORTED = sorted(harvest_data.POOLS.keys())


# ------------------------------------------------------------ measurement
def load_incumbent(subject_id: str) -> F.TinyNet:
    """The incumbent is the ADOPTED artifact: the highest adopted
    factory version where one exists (Phase B v2; later cycles may
    add v3+), else the v1. (Phase C intake fix, generalized —
    retraining a subject must start from the serving artifact's
    weights/data state, and its regression floor is that artifact's
    held-out score.)"""
    best = None
    for cand in sorted(MODELS_DIR.glob(f"{subject_id}-v*.json")):
        stem = cand.stem[len(subject_id) + 2:]
        if stem.isdigit():
            rec = json.loads(cand.read_text())
            # payload records are ternary BitNet artifacts (assembly
            # 2026-11-10): they serve, but a training cycle's
            # incumbent — the weights a widen/edit starts from —
            # remains the highest adopted TinyNet version.
            if rec.get("adopted") and "payload" not in rec:
                best = rec   # ascending order: highest adopted wins
    if best is not None:
        return F.TinyNet.from_record(best)
    rec = json.loads((MODELS_DIR / f"{subject_id}.json").read_text())
    return F.TinyNet.from_record(rec)


def measure(model: F.TinyNet, examples: List[Dict[str, Any]]) -> Dict[str, Any]:
    wrong = []
    right = 0
    for ex in examples:
        got = model.run({"text": ex["text"]})["output"]
        if got == ex["label"]:
            right += 1
        else:
            wrong.append({"want": ex["label"], "got": got,
                          "text": ex["text"][:80]})
    n = len(examples)
    return {"acc": round(right / n, 4) if n else 0.0, "right": right, "n": n,
            "wrong": wrong}


# ------------------------------------------------------------ contamination
def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text).strip().lower())


def _keyset(text: str, fmode: str) -> set:
    return set(F.featurize(text, fmode).keys())


def _word_ngrams(text: str, n: int = 8) -> set:
    words = re.findall(r"[a-z0-9]+", str(text).lower())
    return {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)}


def contamination_filter(items, references, fmode):
    """Drop any item that duplicates or nearly duplicates a reference
    item (training / held-out / battery / other eval pools). Returns
    (kept, dropped_with_reasons). Code-mode items are compared on their
    anonymized shape as well as their featurized keysets: two snippets
    that differ only in identifier names are the SAME surface."""
    ref_norm = {_norm(r["text"]) for r in references}
    ref_keys = [_keyset(r["text"], fmode) for r in references]
    ref_anon = set()
    if fmode == "code":
        ref_anon = {_norm(F._anonymize_code(r["text"])) for r in references}
    ref_grams: List[set] = []
    if fmode != "code":
        ref_grams = [_word_ngrams(r["text"]) for r in references]
    kept, dropped = [], []
    for it in items:
        text = it["text"]
        if _norm(text) in ref_norm:
            dropped.append({**it, "drop_reason": "exact duplicate of a reference item"})
            continue
        if fmode == "code" and _norm(F._anonymize_code(text)) in ref_anon:
            dropped.append({**it, "drop_reason": "anonymized shape duplicates a reference item"})
            continue
        ks = _keyset(text, fmode)
        worst = 0.0
        for rk in ref_keys:
            union = ks | rk
            if union:
                worst = max(worst, len(ks & rk) / len(union))
        cap = 0.92 if fmode == "code" else 0.85
        if worst >= cap:
            dropped.append({**it, "drop_reason": f"featurized keyset jaccard {worst:.2f} >= {cap}"})
            continue
        if ref_grams:
            grams = _word_ngrams(text)
            if grams:
                worst_g = 0.0
                for rg in ref_grams:
                    if rg:
                        worst_g = max(worst_g, len(grams & rg) / len(grams))
                if worst_g >= 0.34:
                    dropped.append({**it, "drop_reason": f"8-gram containment {worst_g:.2f} >= 0.34"})
                    continue
        kept.append(it)
    return kept, dropped


# ------------------------------------------------------------ difficulty filter
def difficulty_filter(incumbent: F.TinyNet, pool: List[Dict[str, Any]]):
    """Group-aware (a case and its second view stay together): keep
    every group the incumbent gets ANY view wrong on, plus a per-class
    diversity quota of groups it gets fully right. Returns
    (kept_items, stats)."""
    groups: Dict[str, List[Dict[str, Any]]] = {}
    order: List[str] = []
    for i, it in enumerate(pool):
        gid = it.get("group", f"__single_{i}")
        if gid not in groups:
            groups[gid] = []
            order.append(gid)
        groups[gid].append(it)
    hard, easy_by_class = [], {}
    for gid in order:
        members = groups[gid]
        misses = [m for m in members
                  if incumbent.run({"text": m["text"]})["output"] != m["label"]]
        if misses:
            hard.extend(members)
        else:
            easy_by_class.setdefault(members[0]["label"], []).append(members)
    kept = list(hard)
    n_easy_kept = 0
    hard_by_class: Dict[str, int] = {}
    for m in hard:
        hard_by_class[m["label"]] = hard_by_class.get(m["label"], 0) + 1
    for cls, cls_groups in easy_by_class.items():
        quota_groups = max(2, hard_by_class.get(cls, 0) // 2)
        for members in cls_groups[:quota_groups]:
            kept.extend(members)
            n_easy_kept += len(members)
    stats = {"pool_items": len(pool), "hard_items_kept": len(hard),
             "easy_items_kept": n_easy_kept, "kept_items": len(kept),
             "hard_by_class": hard_by_class}
    return kept, stats


# ------------------------------------------------------------ retrain
def retrain_candidates(cfg, subject_id, train_set, held_set):
    task = {"name": f"{subject_id}-cand", "niche": cfg["niche"],
            "job": cfg["job"], "classes": cfg["classes"],
            "train": train_set, "heldout": held_set}
    attempts, cands = [], []
    for hidden in (0, 4, 8):
        m = F.train_candidate(task, fmode=cfg["fmode"], hidden=hidden,
                              epochs=cfg["epochs"], train=train_set)
        acc = F.accuracy(m, held_set)
        m.weights, acc = F._prune(m.weights, m, held_set, acc)
        attempts.append({"hidden": hidden, "heldout_acc": round(acc, 4),
                         "params": m.param_count()})
        cands.append((m, acc))
    return cands, attempts


def _atomic_json(path: Path, obj: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False)
    tmp.replace(path)


# ------------------------------------------------------------ the widen cycle
def run_widen_subject(subject: Subject, plan, run_dir: Path,
                      lineage: LineageLog, cycle_id: str,
                      governor_backoff: bool = False,
                      governor_cause: str = "") -> Dict[str, Any]:
    """Execute one TRAIN_DATA_WIDEN plan for real. Writes its own
    checkpoints under run_dir/subjects/<id>/ so a reboot mid-cycle
    loses at most the leg in flight. Returns the outcome record; the
    measured verdict is produced by verify_measured()."""
    sid = subject.subject_id
    out_dir = Path(run_dir) / "subjects" / sid
    out_dir.mkdir(parents=True, exist_ok=True)
    outcome: Dict[str, Any] = {"subject_id": sid, "executed": False,
                               "supported": sid in SUPPORTED}
    if sid not in SUPPORTED:
        outcome["block_reason"] = ("no Phase B executor for this subject "
                                   "(fail-closed)")
        return outcome
    if governor_backoff:
        outcome["block_reason"] = f"governor backoff ({governor_cause}): real execution held"
        return outcome
    cfg = subject_config(sid)
    pools = harvest_data.POOLS[sid]
    lineage.append("executor_start", cycle_id=cycle_id, subject=sid,
                   action="train_data_widen")

    train0 = cfg["train_fn"]()
    held = cfg["held_fn"]()
    battery = [{"text": t, "label": l} for t, l in cfg["battery_items"]]
    incumbent = load_incumbent(sid)
    inc_held = measure(incumbent, held)
    inc_battery = measure(incumbent, battery)

    # Contamination: each pool is filtered against the reference sets
    # AND the other pools, in widen -> screen -> confirm order.
    widen_clean, widen_dropped = contamination_filter(
        pools["widen"], train0 + held + battery + pools["screen"] + pools["confirm"],
        cfg["fmode"])
    screen_clean, screen_dropped = contamination_filter(
        pools["screen"], train0 + held + battery + widen_clean + pools["confirm"],
        cfg["fmode"])
    confirm_clean, confirm_dropped = contamination_filter(
        pools["confirm"], train0 + held + battery + widen_clean + screen_clean,
        cfg["fmode"])
    contamination = {
        "widen": {"in": len(pools["widen"]), "kept": len(widen_clean),
                  "dropped": len(widen_dropped)},
        "screen": {"in": len(pools["screen"]), "kept": len(screen_clean),
                   "dropped": len(screen_dropped)},
        "confirm": {"in": len(pools["confirm"]), "kept": len(confirm_clean),
                    "dropped": len(confirm_dropped)},
        "dropped_detail": widen_dropped + screen_dropped + confirm_dropped,
    }
    _atomic_json(out_dir / "contamination.json", contamination)
    lineage.append("harvest_done", cycle_id=cycle_id, subject=sid,
                   contamination={k: v for k, v in contamination.items()
                                  if k != "dropped_detail"})

    kept, filter_stats = difficulty_filter(incumbent, widen_clean)
    widened_train = ([{"text": ex["text"], "label": ex["label"]} for ex in train0]
                     + [{"text": ex["text"], "label": ex["label"]} for ex in kept])
    _atomic_json(out_dir / "harvest.json",
                 {"filter": filter_stats, "kept": kept,
                  "widened_train_n": len(widened_train)})
    lineage.append("difficulty_filter_done", cycle_id=cycle_id, subject=sid,
                   filter=filter_stats)

    cands, attempts = retrain_candidates(cfg, sid, widened_train, held)
    cand_rows = []
    for m, held_acc in cands:
        scr = measure(m, screen_clean)
        cand_rows.append({"hidden": m.hidden, "params": m.param_count(),
                          "heldout_acc": round(held_acc, 4),
                          "screen_acc": scr["acc"], "screen_n": scr["n"]})
    _atomic_json(out_dir / "candidates.json",
                 {"attempts": attempts, "candidates": cand_rows})
    lineage.append("retrain_done", cycle_id=cycle_id, subject=sid,
                   attempts=attempts)

    floor = inc_held["acc"] - REGRESSION_TOLERANCE
    eligible = [(m, ha, cr) for (m, ha), cr in zip(cands, cand_rows)
                if ha >= floor]
    outcome.update({
        "executed": True,
        "incumbent": {"heldout": inc_held, "battery_reference": inc_battery,
                      "screen": measure(incumbent, screen_clean),
                      "confirm": measure(incumbent, confirm_clean)},
        "contamination": {k: v for k, v in contamination.items()
                          if k != "dropped_detail"},
        "filter": filter_stats,
        "attempts": attempts, "candidates": cand_rows,
        "regression_floor": round(floor, 4),
        "train_n_original": len(train0), "train_n_widened": len(widened_train),
        "screen_n": len(screen_clean), "confirm_n": len(confirm_clean),
    })
    if not eligible:
        outcome["verdict_basis"] = ("no candidate cleared the regression floor "
                                     f"{floor:.4f} on held-out; confirm set not spent")
        _atomic_json(out_dir / "outcome.json", outcome)
        lineage.append("measured", cycle_id=cycle_id, subject=sid,
                       verdict="REVERT", basis=outcome["verdict_basis"])
        return outcome

    # Rank on the screen only; the confirm set is spent once, below.
    eligible.sort(key=lambda t: (-t[2]["screen_acc"], t[2]["params"], t[2]["hidden"]))
    finalist, fin_held_acc, fin_row = eligible[0]
    fin_confirm = measure(finalist, confirm_clean)
    fin_battery = measure(finalist, battery)
    threshold = plan.win_gate.threshold if plan and plan.win_gate else 0.75
    win = fin_confirm["acc"] >= threshold and fin_held_acc >= floor
    outcome.update({
        "finalist": {**fin_row, "confirm_acc": fin_confirm["acc"],
                     "confirm_right": fin_confirm["right"],
                     "confirm_n": fin_confirm["n"],
                     "confirm_wrong": fin_confirm["wrong"],
                     "battery_reference_acc": fin_battery["acc"]},
        "threshold": threshold,
        "verdict_basis": (f"confirm fresh {fin_confirm['acc']:.4f} vs gate "
                          f"{threshold:.2f}; held-out {fin_held_acc:.4f} vs "
                          f"regression floor {floor:.4f}"),
        "win": win,
    })
    if win:
        # Version follows the incumbent actually beaten: beating a v2
        # produces a v3, never an overwrite of the v2 record.
        inc_rec_name = incumbent.name or sid
        suffix = inc_rec_name[len(sid):] if inc_rec_name.startswith(sid) else ""
        ver = 2
        if suffix.startswith("-v") and suffix[2:].isdigit():
            ver = int(suffix[2:]) + 1
        finalist.name = f"{sid}-v{ver}"
        extra = {"path": "trained (factory widen, Phase B)",
                 "heldout_acc": round(fin_held_acc, 4),
                 "train_n": len(widened_train), "heldout_n": len(held),
                 "incumbents": [{"name": sid, "acc": inc_held["acc"]}],
                 "bar": None, "attempts": attempts, "adopted": True,
                 "supersedes": inc_rec_name, "factory_cycle": cycle_id,
                 "fresh_confirm_acc": fin_confirm["acc"],
                 "fresh_screen_acc": fin_row["screen_acc"],
                 "battery_reference_acc": fin_battery["acc"]}
        rec = F.save_model(finalist, extra, directory=MODELS_DIR)
        outcome["adopted_file"] = f"coding/swarm/models/{finalist.name}.json"
        outcome["adopted_params"] = rec["params"]
        outcome["adopted_footprint_bytes"] = rec["footprint_bytes"]
    _atomic_json(out_dir / "outcome.json", outcome)
    lineage.append("measured", cycle_id=cycle_id, subject=sid,
                   verdict="WIN" if win else "REVERT",
                   basis=outcome["verdict_basis"],
                   adopted_file=outcome.get("adopted_file"))
    return outcome


# ------------------------------------------------------------ measured verify
def verify_measured(subject: Subject, plan, outcome: Dict[str, Any]) -> Verification:
    """Apply the win-gate to MEASURED numbers. Every value in the
    returned Verification was produced by running a model in this
    process (see run_widen_subject); measured=True is earned, and no
    SHADOW_PASS is ever returned from here."""
    sid = subject.subject_id
    if not outcome.get("supported"):
        return Verification(sid, verdict="BLOCKED", measured=False, reasons=[
            outcome.get("block_reason", "no executor for this subject"),
            "fail-closed: Phase B executes only Tier-0 TRAIN_DATA_WIDEN "
            "plans with a built executor"])
    if not outcome.get("executed"):
        return Verification(sid, verdict="BLOCKED", measured=False, reasons=[
            outcome.get("block_reason", "execution did not run"),
            "a real cycle that did not execute cannot pass verification"])
    inc = outcome["incumbent"]
    reasons = [
        f"incumbent measured: held-out {inc['heldout']['acc']:.4f} "
        f"(n={inc['heldout']['n']}), battery reference "
        f"{inc['battery_reference']['acc']:.4f} (reference only, not the gate)",
        f"widened train {outcome['train_n_original']} -> "
        f"{outcome['train_n_widened']} examples (difficulty filter: "
        f"{outcome['filter']['hard_items_kept']} incumbent-wrong kept, "
        f"{outcome['filter']['easy_items_kept']} diversity-quota kept; "
        f"contamination drops: widen {outcome['contamination']['widen']['dropped']}, "
        f"screen {outcome['contamination']['screen']['dropped']}, "
        f"confirm {outcome['contamination']['confirm']['dropped']})",
        outcome["verdict_basis"],
    ]
    if outcome.get("win"):
        fin = outcome["finalist"]
        reasons.append(
            f"WIN: finalist (hidden={fin['hidden']}, {fin['params']} params) "
            f"screen {fin['screen_acc']:.4f} (n={fin['screen_n']}), confirm "
            f"{fin['confirm_acc']:.4f} (n={fin['confirm_n']}) >= gate "
            f"{outcome['threshold']:.2f}, held-out above the regression floor; "
            f"adopted as {outcome.get('adopted_file')} — incumbent kept as fallback")
        return Verification(sid, verdict="WIN", reasons=reasons, measured=True)
    reasons.append("REVERT: the gate did not pass; the incumbent stands and "
                   "the candidate is kept only as cycle evidence")
    return Verification(sid, verdict="REVERT", reasons=reasons, measured=True)
