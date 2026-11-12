"""The niche dream executor (final-product item 2): the dream
cycle for Tier-0 specialists, generalizing dream.py's bug-pattern
executor to the niches with their own generators
(dream_gen_niches.py — contract-judgment, commit-type).

Same discipline as the widen executor (Phase B) and the bug dream
executor (Phase C), unchanged gates:

  * diagnosis decides: this executor exists only for subjects whose
    v2-aware diagnosis shows preventive drift; HOLD subjects
    (gap-move, secret-line, error-class) have no generator and fail
    closed here — a hold respected is a correct outcome;
  * a THERMOSTAT reads the incumbent per difficulty band on fresh
    generated probes (never trained on); training concentrates at
    the capability edge (the edge band and the one below it);
  * every dreamed case is checker-verified at generation
    (execution signatures for contract, signal dominance for
    commit), two views per case;
  * contamination filter against ALL standing data: the niche's
    original train + held-out, the battery items, and the Phase B
    harvest pools (whose confirms are already spent — dreams must
    not resurrect them as training data either);
  * difficulty filter (keep what the incumbent gets wrong + a
    per-class diversity quota), smallest-first retrain ladder;
  * the finalist must BEAT the incumbent on a fresh dreamed screen
    or the plan stops and the confirm set is not spent;
  * the confirm set — freshly generated confirm families, three
    structurally disjoint sets per niche — is spent ONCE: adoption
    requires confirm >= the plan threshold AND confirm strictly
    above the incumbent measured on the same set (paired) AND
    same-distribution held-out within the 0.02 regression gate.
    Adoption writes a NEW versioned model file; the incumbent
    stays as fallback.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import dream_gen_niches as GN
from .contracts import Subject, Verification
from .executors import (REGRESSION_TOLERANCE, _atomic_json,
                        contamination_filter, difficulty_filter, measure,
                        retrain_candidates, subject_config,
                        load_incumbent)
from . import harvest_data
from .lineage import LineageLog

LAB_ROOT = Path(__file__).parent.parent
MODELS_DIR = LAB_ROOT / "coding" / "swarm" / "models"
DREAM_STATE_PATH = Path(__file__).parent / "dream_state.json"
BANDS = GN.BANDS
MASTERY = 0.90          # same mastery line as the bug thermostat
POOL_COUNTS = {1: 42, 2: 42, 3: 42}
SCREEN_COUNTS = {1: 10, 2: 10, 3: 10}
CONFIRM_COUNTS = {1: 14, 2: 14, 3: 14}
PROBE_COUNTS = {1: 10, 2: 10, 3: 10}

GENERATORS = GN.niche_generators()


def _seed(cycle_id: str, salt: str) -> int:
    h = hashlib.sha256(f"{cycle_id}:{salt}".encode()).hexdigest()
    return int(h[:8], 16) % 900000 + 1000


def _probe_bands(gen, model, cycle_id: str, salt: str):
    """Fresh probes per band (train-family draws, new seed — the
    thermostat steers generation; it never judges adoption)."""
    out = {}
    for band in BANDS:
        items, _ = gen["gen_pool"]({band: PROBE_COUNTS[band]},
                                   seed=_seed(cycle_id, f"{salt}-probe{band}"),
                                   group_prefix=f"probe-{salt}")
        m = measure(model, items)
        out[band] = {"acc": m["acc"], "n": m["n"]}
    return out


def _thermostat_entry(probe_stats: Dict[int, Dict[str, Any]]):
    edge = BANDS[-1]
    mastered = []
    for band in BANDS:
        st = probe_stats.get(band) or {}
        if st.get("acc") is not None and st["acc"] >= MASTERY:
            mastered.append(band)
            continue
        edge = band
        break
    return {"edge_band": edge,
            "probe": {str(k): v for k, v in probe_stats.items()},
            "mastered": mastered}


def _persist_thermostat(subject_id: str, entry: Dict[str, Any]) -> None:
    state = json.loads(DREAM_STATE_PATH.read_text()) \
        if DREAM_STATE_PATH.exists() else {}
    state.setdefault(subject_id, {})["multiclass"] = entry
    _atomic_json(DREAM_STATE_PATH, state)


def coverage_of(items: List[Dict[str, Any]]) -> Dict[str, int]:
    cov: Dict[str, int] = {}
    for it in items:
        key = f"{it['label']}|band{it.get('band')}"
        cov[key] = cov.get(key, 0) + 1
    return cov


def run_dream_niche_subject(subject: Subject, plan, run_dir: Path,
                            lineage: LineageLog, cycle_id: str,
                            governor_backoff: bool = False,
                            governor_cause: str = "") -> Dict[str, Any]:
    sid = subject.subject_id
    out_dir = Path(run_dir) / "subjects" / sid
    out_dir.mkdir(parents=True, exist_ok=True)
    outcome: Dict[str, Any] = {"subject_id": sid, "executed": False,
                               "supported": sid in GENERATORS,
                               "executor": "dream_niche"}
    if sid not in GENERATORS:
        outcome["block_reason"] = (
            "no niche dream generator for this subject (fail-closed): "
            "generators exist only where the diagnosis called for one; "
            "HOLD subjects are not given cycles")
        return outcome
    if governor_backoff:
        outcome["block_reason"] = (f"governor backoff ({governor_cause}): "
                                   "real execution held")
        return outcome
    gen = GENERATORS[sid]
    cfg = subject_config(sid)
    lineage.append("dream_niche_start", cycle_id=cycle_id, subject=sid)

    train0 = cfg["train_fn"]()
    held = cfg["held_fn"]()
    battery = [{"text": t, "label": l} for t, l in cfg["battery_items"]]
    pools = harvest_data.POOLS[sid]
    harvest_refs = pools["widen"] + pools["screen"] + pools["confirm"]
    references = train0 + held + battery + harvest_refs

    incumbent = load_incumbent(sid)
    inc_held = measure(incumbent, held)
    inc_battery = measure(incumbent, battery)

    # --- thermostat, round 0 ---------------------------------------
    probe0 = _probe_bands(gen, incumbent, cycle_id, "r0")
    entry0 = _thermostat_entry(probe0)
    edge = entry0["edge_band"]
    lineage.append("dream_niche_thermostat", cycle_id=cycle_id,
                   subject=sid, round=0, state=entry0)
    if len(entry0["mastered"]) == len(BANDS):
        outcome.update({"executed": True, "thermostat_round0": entry0,
                        "verdict_basis": (
                            "thermostat: the incumbent masters every "
                            "probe band (>= 0.90) — there is no "
                            "capability edge to dream at; no pool was "
                            "trained on and the confirm set is NOT "
                            "spent")})
        _atomic_json(out_dir / "outcome.json", outcome)
        lineage.append("measured", cycle_id=cycle_id, subject=sid,
                       verdict="REVERT", basis=outcome["verdict_basis"])
        return outcome

    # --- generate + verify + hygiene -------------------------------
    pool, gen_stats = gen["gen_pool"](POOL_COUNTS,
                                      seed=_seed(cycle_id, "pool"),
                                      group_prefix="dreamtrain")
    screen_raw, screen_stats = gen["gen_screen_pool"](
        SCREEN_COUNTS, seed=_seed(cycle_id, "screen"))
    confirm_raw, confirm_stats = gen["gen_confirm_pool"](
        CONFIRM_COUNTS, seed=_seed(cycle_id, "confirm"))
    pool_clean, pool_dropped = contamination_filter(
        pool, references + screen_raw + confirm_raw, cfg["fmode"])
    screen_clean, screen_dropped = contamination_filter(
        screen_raw, references + pool_clean + confirm_raw, cfg["fmode"])
    confirm_clean, confirm_dropped = contamination_filter(
        confirm_raw, references + pool_clean + screen_clean, cfg["fmode"])
    contamination = {
        "pool": {"in": len(pool), "kept": len(pool_clean),
                 "dropped": len(pool_dropped)},
        "screen": {"in": len(screen_raw), "kept": len(screen_clean),
                   "dropped": len(screen_dropped)},
        "confirm": {"in": len(confirm_raw), "kept": len(confirm_clean),
                    "dropped": len(confirm_dropped)},
        "generation": gen_stats, "screen_generation": screen_stats,
        "confirm_generation": confirm_stats}
    _atomic_json(out_dir / "contamination.json", contamination)
    lineage.append("dream_niche_generated", cycle_id=cycle_id, subject=sid,
                   contamination={k: v for k, v in contamination.items()
                                  if not k.endswith("generation")},
                   gen_drops=gen_stats["drops"])

    # --- capability edge: train at the edge band and the one below -
    bands_ok = {edge, max(edge - 1, BANDS[0])}
    edge_pool = [it for it in pool_clean if it.get("band") in bands_ok]
    kept, filter_stats = difficulty_filter(incumbent, edge_pool)
    kept = [{"text": k["text"], "label": k["label"]} for k in kept]
    widened = ([{"text": ex["text"], "label": ex["label"]} for ex in train0]
               + kept)

    # --- retrain ladder + screen ------------------------------------
    cands, attempts = retrain_candidates(cfg, sid, widened, held)
    inc_screen = measure(incumbent, screen_clean)
    cand_rows = []
    for m, held_acc in cands:
        scr = measure(m, screen_clean)
        cand_rows.append({"hidden": m.hidden, "params": m.param_count(),
                          "heldout_acc": round(held_acc, 4),
                          "screen_acc": scr["acc"], "screen_n": scr["n"]})
    floor = inc_held["acc"] - REGRESSION_TOLERANCE
    eligible = [(m, ha, cr) for (m, ha), cr in zip(cands, cand_rows)
                if ha >= floor]
    outcome.update({
        "executed": True, "edge_band": edge, "bands_trained": sorted(bands_ok),
        "thermostat_round0": entry0,
        "incumbent": {"heldout": inc_held, "battery_reference": inc_battery,
                      "screen": inc_screen},
        "contamination": {k: v for k, v in contamination.items()
                          if not k.endswith("generation")},
        "generation_drops": gen_stats["drops"],
        "coverage_after_contamination": coverage_of(pool_clean),
        "filter": filter_stats, "attempts": attempts,
        "candidates": cand_rows,
        "regression_floor": round(floor, 4),
        "train_n_original": len(train0), "train_n_widened": len(widened),
        "screen_n": len(screen_clean), "confirm_n": len(confirm_clean),
    })
    lineage.append("dream_niche_trained", cycle_id=cycle_id, subject=sid,
                   edge_band=edge, kept=len(kept), attempts=attempts)
    if not eligible:
        outcome["verdict_basis"] = (
            f"no candidate cleared the regression floor {floor:.4f} on "
            f"held-out; the confirm set is NOT spent")
        _atomic_json(out_dir / "outcome.json", outcome)
        lineage.append("measured", cycle_id=cycle_id, subject=sid,
                       verdict="REVERT", basis=outcome["verdict_basis"])
        return outcome
    eligible.sort(key=lambda t: (-t[2]["screen_acc"], t[2]["params"],
                                 t[2]["hidden"]))
    finalist, fin_held_acc, fin_row = eligible[0]
    if fin_row["screen_acc"] <= inc_screen["acc"]:
        outcome["verdict_basis"] = (
            f"dreamed screen {fin_row['screen_acc']:.4f} does not beat "
            f"the incumbent's {inc_screen['acc']:.4f} on fresh dreamed "
            f"surfaces; the plan stops at the screen and the confirm "
            f"set is NOT spent")
        _atomic_json(out_dir / "outcome.json", outcome)
        lineage.append("measured", cycle_id=cycle_id, subject=sid,
                       verdict="REVERT", basis=outcome["verdict_basis"])
        return outcome

    # --- thermostat, round 1: did the edge move? --------------------
    probe1 = _probe_bands(gen, finalist, cycle_id, "r1")
    entry1 = _thermostat_entry(probe1)
    outcome["thermostat_round1"] = entry1
    lineage.append("dream_niche_thermostat", cycle_id=cycle_id,
                   subject=sid, round=1, state=entry1)

    # --- confirm: fresh confirm families, spent ONCE ----------------
    inc_confirm = measure(incumbent, confirm_clean)
    fin_confirm = measure(finalist, confirm_clean)
    threshold = plan.win_gate.threshold if plan and plan.win_gate else 0.75
    win = (fin_confirm["acc"] >= threshold
           and fin_confirm["acc"] > inc_confirm["acc"]
           and fin_held_acc >= floor)
    outcome.update({
        "finalist": {**fin_row, "confirm_acc": fin_confirm["acc"],
                     "confirm_right": fin_confirm["right"],
                     "confirm_n": fin_confirm["n"],
                     "confirm_wrong": fin_confirm["wrong"]},
        "incumbent_confirm": inc_confirm,
        "threshold": threshold,
        "verdict_basis": (
            f"confirm (fresh dreamed families) finalist "
            f"{fin_confirm['acc']:.4f} vs gate {threshold:.2f} and vs "
            f"incumbent {inc_confirm['acc']:.4f} measured on the same "
            f"set; held-out {fin_held_acc:.4f} vs regression floor "
            f"{floor:.4f}"),
        "win": win,
    })
    if win:
        inc_rec_name = incumbent.name or sid
        suffix = inc_rec_name[len(sid):] if inc_rec_name.startswith(sid) else ""
        ver = 2
        if suffix.startswith("-v") and suffix[2:].isdigit():
            ver = int(suffix[2:]) + 1
        finalist.name = f"{sid}-v{ver}"
        from swarm import factory as F
        extra = {"path": "trained (factory niche dream cycle, final-product)",
                 "heldout_acc": round(fin_held_acc, 4),
                 "train_n": len(widened), "heldout_n": len(held),
                 "incumbents": [{"name": inc_rec_name, "acc": inc_held["acc"]}],
                 "bar": None, "attempts": attempts, "adopted": True,
                 "supersedes": inc_rec_name, "factory_cycle": cycle_id,
                 "fresh_confirm_acc": fin_confirm["acc"],
                 "fresh_screen_acc": fin_row["screen_acc"],
                 "battery_reference_acc": inc_battery["acc"],
                 "dream": {"executor": "dream_niche", "edge_band": edge,
                           "kept_dream_items": len(kept),
                           "incumbent_confirm_acc": inc_confirm["acc"],
                           "thermostat_round0": entry0,
                           "thermostat_round1": entry1}}
        rec = F.save_model(finalist, extra, directory=MODELS_DIR)
        outcome["adopted_file"] = f"coding/swarm/models/{finalist.name}.json"
        outcome["adopted_params"] = rec["params"]
        outcome["adopted_footprint_bytes"] = rec["footprint_bytes"]
    _atomic_json(out_dir / "outcome.json", outcome)
    _persist_thermostat(sid, entry1)
    lineage.append("measured", cycle_id=cycle_id, subject=sid,
                   verdict="WIN" if win else "REVERT",
                   basis=outcome["verdict_basis"],
                   adopted_file=outcome.get("adopted_file"))
    return outcome


def verify_dream_niche_measured(subject: Subject, plan,
                                outcome: Dict[str, Any]) -> Verification:
    sid = subject.subject_id
    if not outcome.get("supported"):
        return Verification(sid, verdict="BLOCKED", measured=False, reasons=[
            outcome.get("block_reason", "no niche dream executor"),
            "fail-closed: niche dreaming serves only generator-backed "
            "drift subjects (contract-judgment, commit-type)"])
    if not outcome.get("executed"):
        return Verification(sid, verdict="BLOCKED", measured=False, reasons=[
            outcome.get("block_reason", "execution did not run"),
            "a real cycle that did not execute cannot pass verification"])
    inc = outcome["incumbent"]
    reasons = [
        f"incumbent measured: held-out {inc['heldout']['acc']:.4f} "
        f"(n={inc['heldout']['n']}), dreamed screen "
        f"{inc['screen']['acc']:.4f} (n={inc['screen']['n']}), battery "
        f"reference {inc['battery_reference']['acc']:.4f} (reference "
        f"only, not the gate)",
        f"thermostat edge band {outcome['edge_band']} (round 0 probes: "
        + "; ".join(f"band {b} acc {outcome['thermostat_round0']['probe'][str(b)]['acc']}"
                    for b in BANDS) + ")",
        f"dreams: pool kept {outcome['contamination']['pool']['kept']}/"
        f"{outcome['contamination']['pool']['in']} after contamination "
        f"(screen {outcome['contamination']['screen']['kept']}/"
        f"{outcome['contamination']['screen']['in']}, confirm "
        f"{outcome['contamination']['confirm']['kept']}/"
        f"{outcome['contamination']['confirm']['in']}); difficulty "
        f"filter kept {outcome['filter']['kept_items']} items "
        f"({outcome['filter']['hard_items_kept']} incumbent-wrong)",
        outcome["verdict_basis"],
    ]
    if outcome.get("win"):
        fin = outcome["finalist"]
        reasons.append(
            f"WIN: finalist (hidden={fin['hidden']}, {fin['params']} "
            f"params) confirm {fin['confirm_acc']:.4f} (n={fin['confirm_n']}) "
            f">= gate {outcome['threshold']:.2f} and above the incumbent "
            f"on the same fresh set, held-out above the regression "
            f"floor; adopted as {outcome.get('adopted_file')} — incumbent "
            f"kept as fallback")
        return Verification(sid, verdict="WIN", reasons=reasons,
                            measured=True)
    reasons.append("REVERT: the gate did not pass; the incumbent stands "
                   "and the candidates are kept only as cycle evidence")
    return Verification(sid, verdict="REVERT", reasons=reasons,
                        measured=True)
