"""The dream cycle (Phase C): idle-time self-practice for Tier-0
subjects, capability-matched and checker-verified.

Design (FACTORY-ARCHITECTURE.md section 10, from the 2026-11-10
research harvest — Ripple's steep-ascent RL, s1's selection filters,
LeCun's good views):

  * A subject GENERATES its own practice tasks (dream_gen.py):
    parameterized families at the edge of its measured ability.
  * A THERMOSTAT keeps generation at that edge: per class and band,
    fresh probes (never trained on) measure the incumbent; the
    training band is the highest band not yet mastered; mastery
    steps the band up, collapse steps it down. State is logged and
    persisted across cycles.
  * Every dreamed task is verified by EXECUTION before it may be
    trained on; unverifiable dreams are discarded, never trained.
  * s1 filters: what the incumbent already solves reliably is
    deleted; a per-slice diversity quota stops one surface from
    dominating; every kept case is stored in two views.
  * Probe hygiene: probes, screens and the confirm set are generated
    from disjoint draws and contamination-filtered against ALL
    training data (original train, the swarm's phase-4 dream corpus,
    and this cycle's dream-train pool). The confirm set is spent
    exactly once per set: the phase-4 held-out set served the first
    cycle (dream-phaseC-002) and is SPENT; later cycles confirm on
    the sealed held-out v2 set (bug_heldout_v2.py) against its
    recorded baseline recalls.

The first executor serves bug-pattern-composed, the subject Phase B
could not widen: there is no external surface to harvest for it, but
its weak classes are exactly what a checker-verified generator can
manufacture. Dreaming is a legitimate executor for it for the same
reason checker-verified synthesis was legitimate for the
coordinator: labels are not asserted, they are PROVED (by execution)
before training, and the win-gate is the same gate Phase B used —
threshold + per-class no-regression, confirm spent once.
"""
from __future__ import annotations

import json
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
from swarm.specialist import Specialist  # noqa: E402

from . import dream_gen as G  # noqa: E402
from .contracts import Subject, Verification  # noqa: E402
from .executors import (REGRESSION_TOLERANCE, _atomic_json,  # noqa: E402
                        contamination_filter, difficulty_filter, measure)
from .lineage import LineageLog  # noqa: E402

MODELS_DIR = LAB_ROOT / "coding" / "swarm" / "models"
MASTERY = 0.90        # probe acc at/above -> band mastered, step up
COLLAPSE = 0.30       # probe acc below -> step down
DREAM_STATE_PATH = Path(__file__).parent / "dream_state.json"


# ------------------------------------------------------------ composition
def load_bug_registry() -> Dict[str, Any]:
    reg: Dict[str, Any] = {}
    for f in sorted(MODELS_DIR.glob("bug-*.json")):
        rec = json.loads(f.read_text())
        if rec.get("adopted"):
            reg[rec["name"]] = F.TinyNet.from_record(rec)
    return reg


def make_composer(reg: Dict[str, Any]) -> Specialist:
    return Specialist("bug-pattern-composer", "debugging",
                      "compose the per-class bug models into one verdict",
                      fn=C.make_bug_pattern_composer(reg))


def composed_eval(reg: Dict[str, Any], examples: List[Dict[str, Any]]):
    """Mirror of phase4.composed_eval over an injectable registry."""
    composer = make_composer(reg)
    right, per = 0, {}
    for ex in examples:
        pred = composer.run({"code": ex["text"]})["output"]
        ok = pred == ex["label"]
        right += ok
        d = per.setdefault(ex["label"], {"n": 0, "right": 0})
        d["n"] += 1
        d["right"] += ok
    recall = {c: round(d["right"] / d["n"], 4) for c, d in per.items() if d["n"]}
    return (round(right / len(examples), 4) if examples else 0.0), recall


def _relabel(examples, cls):
    return [{"text": e["text"],
             "label": cls if e["label"] == cls else "other"}
            for e in examples]


# ------------------------------------------------------------ thermostat
class Thermostat:
    """Per-class difficulty state. The capability that matters for a
    binary class model is whether it FIRES on true positives, so the
    thermostat reads positive-class recall per band on fresh probes
    (binary accuracy is dominated by the 'other' majority and hides
    exactly the weakness being treated). The training band is the
    lowest band whose recall is not yet mastered; mastery steps up,
    collapse stays at the band (it is the edge by definition)."""

    def __init__(self, state: Optional[Dict[str, Any]] = None):
        self.state = state or {}

    def measure(self, subject_id: str, cls: str,
                probe_stats: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
        edge = G.BANDS[-1]
        mastered = []
        for band in G.BANDS:
            st = probe_stats.get(band) or {}
            rec = st.get("recall")
            if rec is not None and rec >= MASTERY:
                mastered.append(band)
                continue
            edge = band
            break
        entry = {"edge_band": edge,
                 "probe": {str(k): v for k, v in probe_stats.items()},
                 "mastered": mastered}
        self.state.setdefault(subject_id, {})[cls] = entry
        return entry


def _probe_band_accs(binaries: Dict[str, F.TinyNet], weak: List[str],
                     seed: int) -> Dict[str, Dict[int, Dict[str, Any]]]:
    """Fresh probes per band (same structures as training dreams,
    new parameter draws — the thermostat steers generation, it does
    not judge adoption; the screen and confirm judge). Per weak
    class: binary accuracy AND positive recall with counts."""
    out: Dict[str, Dict[int, Dict[str, Any]]] = {c: {} for c in weak}
    for band in G.BANDS:
        items, _ = G.gen_pool({band: 12}, seed=seed + band,
                              group_prefix=f"probe{seed}")
        for cls in weak:
            rel = _relabel(items, cls)
            m = measure(binaries[cls], rel)
            pos = [e for e in rel if e["label"] == cls]
            hit = sum(1 for e in pos
                      if binaries[cls].run({"text": e["text"]})["output"]
                      == cls)
            out[cls][band] = {"acc": m["acc"], "n": m["n"],
                              "recall": round(hit / len(pos), 4)
                              if pos else None,
                              "n_pos": len(pos)}
    return out


# ------------------------------------------------------------ coverage
def coverage_of(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    cov: Dict[str, Any] = {}
    for it in items:
        cls = it["label"]
        sl = D.slice_of(cls, it["text"]) if cls in D.SLICES else "-"
        key = f"{cls}|band{it.get('band')}|{sl}"
        cov[key] = cov.get(key, 0) + 1
    return cov


def slice_quota(items: List[Dict[str, Any]], cap_share: float = 0.5):
    """s1 diversity quota at group level: within a class, no slice
    may hold more than cap_share of the positive groups. Returns
    (kept_items, dropped_groups)."""
    groups: Dict[str, List[Dict[str, Any]]] = {}
    order: List[str] = []
    for it in items:
        gid = it.get("group", it["text"])
        if gid not in groups:
            groups[gid] = []
            order.append(gid)
        groups[gid].append(it)
    pos_by_class: Dict[str, List[str]] = {}
    for gid in order:
        lab = groups[gid][0]["label"]
        if lab != "clean":
            pos_by_class.setdefault(lab, []).append(gid)
    dropped = set()
    for cls, gids in pos_by_class.items():
        by_slice: Dict[str, List[str]] = {}
        for gid in gids:
            sl = D.slice_of(cls, groups[gid][0]["text"]) \
                if cls in D.SLICES else "-"
            by_slice.setdefault(sl, []).append(gid)
        cap = max(1, int(len(gids) * cap_share))
        for sl, sgids in by_slice.items():
            dropped.update(sgids[cap:])
    kept = [it for gid in order if gid not in dropped
            for it in groups[gid]]
    return kept, sorted(dropped)


# ------------------------------------------------------------ the executor
def run_dream_subject(subject: Subject, plan, run_dir: Path,
                      lineage: LineageLog, cycle_id: str,
                      governor_backoff: bool = False,
                      governor_cause: str = "") -> Dict[str, Any]:
    sid = subject.subject_id
    out_dir = Path(run_dir) / "subjects" / sid
    out_dir.mkdir(parents=True, exist_ok=True)
    outcome: Dict[str, Any] = {"subject_id": sid, "executed": False,
                               "supported": sid == "bug-pattern-composed",
                               "executor": "dream"}
    if not outcome["supported"]:
        outcome["block_reason"] = ("dream executor serves "
                                   "bug-pattern-composed only (fail-closed)")
        return outcome
    if governor_backoff:
        outcome["block_reason"] = (f"governor backoff ({governor_cause}): "
                                   "real execution held")
        return outcome
    lineage.append("dream_start", cycle_id=cycle_id, subject=sid)

    multi_train = P3.gen_bug_patterns(P3._BUG_TEMPLATES_TRAIN, 21)
    multi_held = P3.gen_bug_patterns(P3._BUG_TEMPLATES_HELD, 22)
    p4 = json.loads((LAB_ROOT / "coding" / "swarm" /
                     "phase4_results.json").read_text())
    recorded_recalls = p4["rounds"][-1]["per_class_recall"]
    plateau = p4["rounds"][-1]["composed_acc"]
    per_class_meta = subject.metadata.get("per_class", {})
    weak = [c for c, v in per_class_meta.items()
            if v.get("recall") is not None and v["recall"] < 0.75]
    if not weak:
        weak = ["off-by-one", "wrong-operator", "swapped-operands"]

    reg = load_bug_registry()
    binaries = {cls: reg[f"bug-{cls}-model"] for cls in C.DEFECT_CLASSES}
    # Harness sanity: the injectable-registry eval must reproduce the
    # recorded plateau exactly, or nothing measured here means
    # anything. Fail closed on mismatch.
    inc_comp_acc, inc_comp_recall = composed_eval(reg, multi_held)
    if abs(inc_comp_acc - plateau) > 0.001:
        outcome["block_reason"] = (
            f"composition harness mismatch: measured incumbent "
            f"{inc_comp_acc} vs recorded plateau {plateau} — refusing "
            f"to judge candidates with an uncalibrated harness")
        _atomic_json(out_dir / "outcome.json", outcome)
        return outcome
    lineage.append("dream_harness_calibrated", cycle_id=cycle_id,
                   subject=sid, composed=inc_comp_acc, plateau=plateau)

    # The swarm's phase-4 dream corpus is part of the incumbents'
    # effective training data: dreams must not duplicate it either.
    from swarm import dream as swarm_dream
    dream_corpus = swarm_dream.gen_dream_bug_examples()
    references = multi_train + multi_held + dream_corpus

    # --- thermostat, round 0 (fresh probes, never trained on) -----
    thermo = Thermostat(json.loads(DREAM_STATE_PATH.read_text())
                        if DREAM_STATE_PATH.exists() else {})
    probe0 = _probe_band_accs(binaries, weak, seed=7100)
    for cls in weak:
        thermo.measure(sid, cls, probe0[cls])
    lineage.append("dream_thermostat", cycle_id=cycle_id, subject=sid,
                   round=0, state=thermo.state.get(sid))

    # --- generate + verify + hygiene ------------------------------
    pool, gen_stats = G.gen_pool({1: 40, 2: 34, 3: 34}, seed=4200,
                                 group_prefix="dreamtrain")
    pool_clean, pool_dropped = contamination_filter(pool, references,
                                                    "code")
    # The screen has its OWN skeletons (structurally distinct idioms)
    # so it measures structure-generalization, and it passes the same
    # contamination filter against everything trained on.
    screen_raw, screen_stats = G.gen_screen_pool({1: 12, 2: 14, 3: 14},
                                                 seed=9100)
    screen_clean, screen_dropped = contamination_filter(
        screen_raw, references + pool_clean, "code")
    contamination = {
        "pool": {"in": len(pool), "kept": len(pool_clean),
                 "dropped": len(pool_dropped)},
        "screen": {"in": len(screen_raw), "kept": len(screen_clean),
                   "dropped": len(screen_dropped)},
        "generation": gen_stats, "screen_generation": screen_stats}
    _atomic_json(out_dir / "contamination.json", contamination)
    lineage.append("dream_generated", cycle_id=cycle_id, subject=sid,
                   contamination={k: v for k, v in contamination.items()
                                  if k not in ("generation",
                                               "screen_generation")},
                   gen_drops=gen_stats["drops"])

    pool_quota, quota_dropped = slice_quota(pool_clean)
    coverage_before = coverage_of(pool_clean)
    coverage_after = coverage_of(pool_quota)

    # --- per-class: filter, retrain, screen ------------------------
    class_results: Dict[str, Any] = {}
    winners: Dict[str, Optional[F.TinyNet]] = {}
    for cls in weak:
        edge = thermo.state[sid][cls]["edge_band"]
        bands_ok = {edge, max(edge - 1, G.BANDS[0])}
        positives = [it for it in pool_quota
                     if it["label"] == cls and it.get("band") in bands_ok]
        negatives = [it for it in pool_quota if it["label"] != cls]
        cls_pool = _relabel(positives + negatives, cls)
        kept, fstats = difficulty_filter(binaries[cls], cls_pool)
        kept = [{"text": k["text"], "label": k["label"]} for k in kept]
        train_bin = _relabel(multi_train, cls)
        held_bin = _relabel(multi_held, cls)
        screen_bin = _relabel(screen_clean, cls)
        inc_bin_held = measure(binaries[cls], held_bin)
        inc_bin_screen = measure(binaries[cls], screen_bin)
        widened = train_bin + kept
        task = {"name": f"bug-{cls}-model-dream", "niche": "debugging",
                "job": f"decide whether a snippet's defect is {cls} "
                       f"(vs anything else, including clean)",
                "classes": [cls, "other"], "train": widened,
                "heldout": held_bin}
        attempts, cand_rows, cands = [], [], []
        for fmode in ("text", "code"):
            for hidden in (0, 4, 8):
                m = F.train_candidate(task, fmode=fmode, hidden=hidden,
                                      epochs=800, train=widened)
                acc = F.accuracy(m, held_bin)
                m.weights, acc = F._prune(m.weights, m, held_bin, acc)
                scr = measure(m, screen_bin)
                attempts.append({"fmode": fmode, "hidden": hidden,
                                 "heldout_acc": round(acc, 4),
                                 "params": m.param_count()})
                cand_rows.append({"fmode": fmode, "hidden": hidden,
                                  "params": m.param_count(),
                                  "heldout_acc": round(acc, 4),
                                  "screen_acc": scr["acc"]})
                cands.append(m)
        floor = inc_bin_held["acc"] - REGRESSION_TOLERANCE
        eligible = [(m, cr) for m, cr in zip(cands, cand_rows)
                    if cr["heldout_acc"] >= floor]
        winner, win_row = None, None
        if eligible:
            eligible.sort(key=lambda t: (-t[1]["screen_acc"],
                                         t[1]["params"], t[1]["hidden"]))
            winner, win_row = eligible[0]
            if win_row["screen_acc"] <= inc_bin_screen["acc"]:
                winner, win_row = None, None   # incumbent wins the screen
        winners[cls] = winner
        class_results[cls] = {
            "edge_band": edge, "positives_at_edge": len(positives),
            "filter": fstats, "kept_dream_items": len(kept),
            "train_n_original": len(train_bin),
            "train_n_widened": len(widened),
            "incumbent_binary": {"heldout": inc_bin_held,
                                 "screen": inc_bin_screen},
            "attempts": attempts, "candidates": cand_rows,
            "regression_floor": round(floor, 4),
            "winner": ({"fmode": win_row["fmode"],
                        "hidden": win_row["hidden"],
                        "params": win_row["params"],
                        "heldout_acc": win_row["heldout_acc"],
                        "screen_acc": win_row["screen_acc"]}
                       if win_row else None)}
        lineage.append("dream_class_trained", cycle_id=cycle_id,
                       subject=sid, cls=cls, edge_band=edge,
                       kept=len(kept),
                       winner=class_results[cls]["winner"])

    # --- composed screen: the finalist must beat the incumbent ----
    cand_reg = dict(reg)
    for cls, w in winners.items():
        if w is not None:
            cand_reg[f"bug-{cls}-model"] = w
    cand_screen_acc, cand_screen_recall = composed_eval(cand_reg,
                                                        screen_clean)
    inc_screen_acc, inc_screen_recall = composed_eval(reg, screen_clean)
    outcome.update({
        "executed": True, "weak_classes": weak,
        "incumbent": {"composed_heldout_acc": inc_comp_acc,
                      "composed_heldout_recall": inc_comp_recall,
                      "composed_screen_acc": inc_screen_acc,
                      "composed_screen_recall": inc_screen_recall},
        "contamination": {k: v for k, v in contamination.items()
                          if k not in ("generation", "screen_generation")},
        "generation_drops": gen_stats["drops"],
        "quota_dropped_groups": quota_dropped,
        "coverage_before_quota": coverage_before,
        "coverage_after_quota": coverage_after,
        "classes": class_results,
        "candidate_screen": {"composed_acc": cand_screen_acc,
                             "per_class_recall": cand_screen_recall},
        "thermostat_round0": {c: thermo.state[sid][c] for c in weak},
        "plateau": plateau, "recorded_recalls": recorded_recalls,
    })
    if cand_screen_acc <= inc_screen_acc:
        outcome["verdict_basis"] = (
            f"composed screen {cand_screen_acc} does not beat the "
            f"incumbent composition's {inc_screen_acc} on fresh dreamed "
            f"surfaces; the plan stops at the screen and the confirm "
            f"set is NOT spent")
        _atomic_json(out_dir / "outcome.json", outcome)
        lineage.append("measured", cycle_id=cycle_id, subject=sid,
                       verdict="REVERT", basis=outcome["verdict_basis"])
        return outcome

    # --- thermostat, round 1: did the edge move? -------------------
    cand_binaries = dict(binaries)
    for cls, w in winners.items():
        if w is not None:
            cand_binaries[cls] = w
    probe1 = _probe_band_accs(cand_binaries, weak, seed=7300)
    thermo1 = Thermostat()
    for cls in weak:
        thermo1.measure(sid, cls, probe1[cls])
    outcome["thermostat_round1"] = {c: thermo1.state[sid][c]
                                    for c in weak}
    lineage.append("dream_thermostat", cycle_id=cycle_id, subject=sid,
                   round=1, state=thermo1.state.get(sid))

    # --- confirm: spent ONCE on the standing sealed set ------------
    # The phase-4 held-out set was spent by dream-phaseC-002. When
    # the sealed held-out v2 set exists it is the confirm set, gated
    # against its recorded baseline recalls; otherwise (pre-seal
    # history) the phase-4 set serves, gated on its recorded recalls.
    confirm_items, gate_recalls, confirm_label = multi_held, \
        recorded_recalls, "phase-4 held-out set"
    try:
        from . import bug_heldout_v2 as _bh
        if _bh.SEALED_PATH.exists():
            sealed = _bh.load_sealed()
            base_path = (LAB_ROOT / "results" /
                         "bug_heldout_v2_baseline.json")
            if base_path.exists():
                base = json.loads(base_path.read_text())
                confirm_items = sealed["items"]
                gate_recalls = base["per_class_recall"]
                confirm_label = ("sealed held-out v2 (baseline "
                                 f"{base['composed_acc']})")
    except Exception:
        pass   # fall back to the legacy confirm set, never improvise
    fin_acc, fin_recall = composed_eval(cand_reg, confirm_items)
    threshold = plan.win_gate.threshold if plan and plan.win_gate else 0.80
    recall_ok = all(fin_recall.get(c, 0.0) >= gate_recalls.get(c, 0.0)
                    for c in gate_recalls)
    win = fin_acc >= threshold and recall_ok
    outcome.update({
        "finalist": {"composed_confirm_acc": fin_acc,
                     "per_class_recall": fin_recall},
        "confirm_set": confirm_label,
        "threshold": threshold,
        "recall_gate_ok": recall_ok,
        "verdict_basis": (f"confirm composed {fin_acc:.4f} vs bar "
                          f"{threshold:.2f} (plateau {plateau}) on the "
                          f"{confirm_label}; per-class recall gate "
                          f"{'ok' if recall_ok else 'FAILED'} vs the "
                          f"confirm set's recorded recalls"),
        "win": win,
    })
    if win:
        backup_dir = out_dir / "backups"
        backup_dir.mkdir(exist_ok=True)
        adopted_files = []
        for cls, w in winners.items():
            if w is None:
                continue
            name = f"bug-{cls}-model"
            src = MODELS_DIR / f"{name}.json"
            (backup_dir / f"{name}.phase4.json").write_text(
                src.read_text())
            w.name = name
            cr = class_results[cls]
            extra = {"path": "trained (factory dream cycle, Phase C)",
                     "heldout_acc": cr["winner"]["heldout_acc"],
                     "train_n": cr["train_n_widened"],
                     "heldout_n": len(multi_held),
                     "incumbents": [{"name": name,
                                     "acc": cr["incumbent_binary"]
                                     ["heldout"]["acc"]}],
                     "bar": None,
                     "attempts": cr["attempts"], "adopted": True,
                     "supersedes": f"{name} (phase-4 record)",
                     "factory_cycle": cycle_id,
                     "dream": {"edge_band": cr["edge_band"],
                               "kept_dream_items": cr["kept_dream_items"],
                               "composed_confirm_acc": fin_acc}}
            F.save_model(w, extra, directory=MODELS_DIR)
            adopted_files.append(f"coding/swarm/models/{name}.json")
        outcome["adopted_files"] = adopted_files
    _atomic_json(out_dir / "outcome.json", outcome)
    # Persist the thermostat for the next cycle (round-1 state wins:
    # it describes the serving models after this cycle).
    merged = json.loads(DREAM_STATE_PATH.read_text()) \
        if DREAM_STATE_PATH.exists() else {}
    merged.setdefault(sid, {}).update(
        thermo1.state.get(sid, thermo.state.get(sid, {})))
    _atomic_json(DREAM_STATE_PATH, merged)
    lineage.append("measured", cycle_id=cycle_id, subject=sid,
                   verdict="WIN" if win else "REVERT",
                   basis=outcome["verdict_basis"],
                   adopted_files=outcome.get("adopted_files"))
    return outcome


# ------------------------------------------------------------ measured verify
def verify_dream_measured(subject: Subject, plan,
                          outcome: Dict[str, Any]) -> Verification:
    sid = subject.subject_id
    if not outcome.get("supported"):
        return Verification(sid, verdict="BLOCKED", measured=False,
                            reasons=[
                                outcome.get("block_reason",
                                            "no dream executor"),
                                "fail-closed: the dream executor serves "
                                "bug-pattern-composed only"])
    if not outcome.get("executed"):
        return Verification(sid, verdict="BLOCKED", measured=False,
                            reasons=[
                                outcome.get("block_reason",
                                            "execution did not run"),
                                "a real cycle that did not execute "
                                "cannot pass verification"])
    inc = outcome["incumbent"]
    reasons = [
        f"harness calibrated: incumbent composition re-measured "
        f"{inc['composed_heldout_acc']:.4f} = the recorded plateau "
        f"{outcome['plateau']} before any candidate was judged",
        f"dreams: pool kept {outcome['contamination']['pool']['kept']}/"
        f"{outcome['contamination']['pool']['in']} after contamination "
        f"(screen {outcome['contamination']['screen']['kept']}/"
        f"{outcome['contamination']['screen']['in']}); generation "
        f"drops {outcome['generation_drops']}; slice-quota dropped "
        f"{len(outcome['quota_dropped_groups'])} groups",
        "thermostat edges (round 0 -> round 1): " + "; ".join(
            f"{c} band {outcome['thermostat_round0'][c]['edge_band']} -> "
            f"{outcome.get('thermostat_round1', {}).get(c, {}).get('edge_band', 'n/a')}"
            for c in outcome["weak_classes"]),
        outcome["verdict_basis"],
    ]
    if outcome.get("win"):
        reasons.append(
            f"WIN: composed confirm {outcome['finalist']['composed_confirm_acc']:.4f} "
            f">= bar {outcome['threshold']:.2f} with every per-class "
            f"recall at or above its phase-4 recorded value; adopted "
            f"{outcome.get('adopted_files')} — phase-4 records backed "
            f"up inside the run directory, strong classes untouched")
        return Verification(sid, verdict="WIN", reasons=reasons,
                            measured=True)
    reasons.append("REVERT: the gate did not pass; the phase-4 "
                   "composition stands unchanged")
    return Verification(sid, verdict="REVERT", reasons=reasons,
                        measured=True)
