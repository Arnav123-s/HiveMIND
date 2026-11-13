"""E-001 — waking-in-the-loop say fit (Muse's work, Muse's side).

The learned say (factory/learned_say.py, Build 2) was fitted on RAW
composed verdicts and lost on the sealed set entirely through clean
recall (0.8182 -> 0.6364): its re-weighted margins push clean code
defect-ward into the waking-dream layer, whose clean-win gate reads
margin SCALE (clean may only win when max adjusted margin <= 0.5).
The factory report named the next attack and nobody ran it: fit
with the waking layer in the loop — objective = accuracy of the
FULL dev serving path (composer -> waking layer -> verdict).

The E-007 retro-check (reports/e007-retrocheck-2026-11-12.md) has
since shown the same mechanism from the other side: cycles 6 and 7
regressed serving with raw composed totals exactly flat, the whole
fall in clean recall, located in the waking refresh's clean gate
reading new members' margin scales. The margin-scale x clean-gate
interaction is the documented failure point, not a hypothesis.

Method here:
  * Per dev item, cache the config-independent facts once: seat
    margins, per-class verifier (score, raw verified) outcomes,
    and the clean verifier's positive-behaviour outcome. The
    verifiers are pure functions of the code; only the climb
    order, the thresholded verified flags, the clean gate and the
    composer fallback depend on (weights, thresholds).
  * Simulate WakingDream.answer() exactly from that cache
    (replicating class_margins' say branch, the climb, the
    thresholded verification, v_clean, the <= 0.5 clean gate and
    the composer fallback, statement for statement).
  * VALIDATE the simulator against the real WakingDream path on
    the dev pool for the incumbent config and the old say —
    answer-for-answer — before trusting it for fitting.
  * Coordinate ascent (same grids and strict-improvement
    discipline as learned_say.fit_on_cache) on simulated dev-path
    accuracy, from two starts (uniform, old say), under two
    objectives: pure accuracy, and lexicographic (accuracy, then
    clean recall) — E-007's signature is a clean loss at a flat
    total, so among equal-accuracy fits the clean-richer one is
    the better serving candidate.
  * The winning fit is re-measured on the REAL path. The sealed
    set is touched exactly once, through run_battery's own eval
    path, only if the new fit's real dev-path accuracy beats the
    old fit's real dev-path accuracy.

Discipline: this script never writes factory/learned_say.json,
the registry, or any serving state. Its fit lands in
factory/learned_say_waking.json (status stays "shadow"; serving
reads learned_say.json only). Dev pool only during fitting.
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

LAB = Path(__file__).parent.parent
sys.path.insert(0, str(LAB / "coding"))
sys.path.insert(0, str(LAB))
sys.path.insert(0, str(LAB / "waking-dream"))

from swarm import composers as C  # noqa: E402
from factory import learned_say as say_mod  # noqa: E402
from factory import say_dev  # noqa: E402
import waking_dream as wd  # noqa: E402

CLASSES = list(C.DEFECT_CLASSES)
VT = wd.VERIFY_THRESHOLD
STATE_OUT = Path(__file__).parent / "learned_say_waking.json"


# ------------------------------------------------------------ cache
def build_cache(reg, dev_items, seats):
    """Config-independent per-item facts. Verifier outcomes are
    computed for ALL five classes (the climb only ever verifies
    the top 3, but which 3 is config-dependent)."""
    cache = []
    for it in dev_items:
        code = it["text"]
        row = say_mod.seat_margins(reg, code, seats)
        ctx_raw = wd.gen_probes(code)
        ctx = {"probes": ctx_raw["probes"], "kinds": ctx_raw["kinds"]}
        ver: Dict[str, Tuple[float, bool]] = {}
        for cls in CLASSES:
            try:
                r = wd.VERIFIERS[cls](code, ctx)
                ver[cls] = (float(r.get("score", 0.0)),
                            bool(r.get("verified", False)))
            except Exception:  # noqa: BLE001 — recorded, sim flags it
                ver[cls] = (0.0, False)
        try:
            clean_ok = bool(wd.v_clean(code, ctx, []).get("verified"))
        except Exception:  # noqa: BLE001
            clean_ok = False
        cache.append({"label": it["label"], "margins": row,
                      "ver": ver, "clean_ok": clean_ok})
    return cache


# ------------------------------------------------------------ simulator
def combined_margins(row, weights):
    """Replicates composers.class_margins' say branch exactly:
    weighted mean of finite seat margins, class omitted when the
    weight denominator is 0."""
    out: Dict[str, float] = {}
    for cls in CLASSES:
        if cls not in weights:
            continue
        seats = row.get(cls) or {}
        if not seats:
            continue
        w = weights[cls]
        mean_w = sum(w.values()) / len(w)
        num = den = 0.0
        for nm, mv in seats.items():
            wv = w.get(nm, mean_w)
            num += wv * mv
            den += wv
        if den:
            out[cls] = num / den
    return out


def sim_answer(item, weights, thresholds):
    """WakingDream.answer() from cached facts. Returns
    (answer, mechanism, clean_block) where clean_block names why a
    clean-labelled item was lost, when it was."""
    margins = combined_margins(item["margins"], weights)
    adjusted = {c: margins[c] - float(thresholds.get(c, 0.0))
                for c in CLASSES if c in margins}
    # composer fallback verdict (make_bug_pattern_composer's rule;
    # the serving config carries no clean_guard, checked by caller)
    if not adjusted:
        base = None
    else:
        best = None
        for c in CLASSES:
            if c in adjusted and (best is None
                                  or adjusted[c] > adjusted[best]):
                best = c
        base = best if adjusted[best] > 0 else "clean"
    ranked = sorted(adjusted, key=lambda c: -adjusted[c])
    top = ranked[:3]
    climb = [c for c in top if adjusted[c] > 0] + ["clean"] + \
            [c for c in top if adjusted[c] <= 0]
    fin_ver = {}
    for c in top:
        score, raw = item["ver"][c]
        fin_ver[c] = raw and score >= VT[c]
    defect_verified = [(c, item["ver"][c][0]) for c in climb
                       if c != "clean" and fin_ver.get(c)]
    if defect_verified:
        winner = max(defect_verified,
                     key=lambda t: (t[1], -climb.index(t[0])))
        return winner[0], "verified", None
    fired = any(fin_ver.get(c) for c in top)
    best_defect = max((item["ver"][c][0] for c in top), default=0.0)
    clean_ver = (not fired) and best_defect < 0.30 and item["clean_ok"]
    if clean_ver and (not adjusted or max(adjusted.values()) <= 0.5):
        return "clean", "verified", None
    block = None
    if item["label"] == "clean":
        if fired:
            block = "defect-verified"
        elif clean_ver:
            block = "clean-gate-blocked"  # verified but max adj > 0.5
        else:
            block = "clean-unverified"
    return base, "fallback-unverified", block


def sim_eval(cache, weights, thresholds):
    right = clean_right = clean_n = 0
    per: Dict[str, List[int]] = {}
    blocks: Dict[str, int] = {}
    for item in cache:
        ans, _mech, block = sim_answer(item, weights, thresholds)
        d = per.setdefault(item["label"], [0, 0])
        d[1] += 1
        if ans == item["label"]:
            right += 1
            d[0] += 1
        if item["label"] == "clean":
            clean_n += 1
            if ans == "clean":
                clean_right += 1
            elif block:
                blocks[block] = blocks.get(block, 0) + 1
    recalls = {c: round(r / n, 4) for c, (r, n) in sorted(per.items())}
    return {"acc": right / len(cache), "right": right,
            "clean_recall": clean_right / clean_n if clean_n else 0.0,
            "clean_right": clean_right, "clean_n": clean_n,
            "recalls": recalls, "clean_blocks": blocks}


# ------------------------------------------------------------ ascent
W_CANDS = (0.0, 0.25, 0.5, 2.0)
T_OFFS = (-0.6, -0.3, -0.15, 0.15, 0.3, 0.6)


def _key(metrics, objective):
    if objective == "lex":
        return (metrics["right"], metrics["clean_right"])
    return (metrics["right"],)


def ascend(cache, seats, weights, thresholds, base_thresholds,
           objective, passes=6):
    weights = {c: dict(weights[c]) for c in weights}
    thresholds = dict(thresholds)
    best_m = sim_eval(cache, weights, thresholds)
    best_k = _key(best_m, objective)
    for _ in range(passes):
        improved = False
        for c in CLASSES:
            if c not in weights:
                continue
            for nm in seats.get(c, []):
                cur = weights[c][nm]
                for cand in W_CANDS:
                    if cand == cur:
                        continue
                    weights[c][nm] = cand
                    m = sim_eval(cache, weights, thresholds)
                    if _key(m, objective) > best_k:
                        best_k, best_m, cur, improved = \
                            _key(m, objective), m, cand, True
                    else:
                        weights[c][nm] = cur
            base_t = float(base_thresholds.get(c, 0.0))
            cur = thresholds[c]
            for off in T_OFFS:
                cand = round(base_t + off, 6)
                if cand == cur:
                    continue
                thresholds[c] = cand
                m = sim_eval(cache, weights, thresholds)
                if _key(m, objective) > best_k:
                    best_k, best_m, cur, improved = \
                        _key(m, objective), m, cand, True
                else:
                    thresholds[c] = cur
        if not improved:
            break
    return weights, thresholds, best_m


def shares_of(weights):
    out = {}
    for c, w in weights.items():
        tot = sum(w.values())
        out[c] = {n: (round(w[n] / tot, 6) if tot else 0.0) for n in w}
    return out


# ------------------------------------------------------------ real path
def real_answers(reg, config, items):
    w = wd.WakingDream(registry=reg, config=config)
    return [w.answer(it["text"])["answer"] for it in items]


def acc_recalls(answers, items):
    right = 0
    per: Dict[str, List[int]] = {}
    for ans, it in zip(answers, items):
        d = per.setdefault(it["label"], [0, 0])
        d[1] += 1
        if ans == it["label"]:
            right += 1
            d[0] += 1
    return right / len(items), \
        {c: round(r / n, 4) for c, (r, n) in sorted(per.items())}


def main() -> None:
    from factory.run_battery import _bug_reg, _eval_bug_path
    from factory.serve import ServingHive
    from factory.bug_heldout_v2 import load_sealed

    t0 = time.time()
    hive = ServingHive.load()
    reg = _bug_reg(hive)
    member_names = list(reg)
    base_cfg = C.load_config()
    base_thresholds = {c: float(base_cfg.get("thresholds", {}).get(c, 0.0))
                       for c in CLASSES}
    seats = say_mod.seats_of(member_names)
    dev_items = say_dev.load_dev_pool()["items"]
    old_state = say_mod.load_state()
    old_say = old_state["say"]
    out: Dict[str, Any] = {"base_thresholds": base_thresholds,
                           "clean_guard_in_config": bool(
                               base_cfg.get("clean_guard")),
                           "guard_in_reg": "bug-clean-guard-model" in reg,
                           "n_dev": len(dev_items)}

    # ---- cache + simulator validation on two say-form configs
    cache = build_cache(reg, dev_items, seats)
    uniform_w = {c: {n: 1.0 for n in seats[c]} for c in CLASSES}
    uniform_say = {"weights": shares_of(uniform_w),
                   "thresholds": dict(base_thresholds)}
    validations = {}
    for name, say_payload, raw_w in (
            ("uniform", uniform_say, uniform_w),
            ("old_say", old_say, old_say["weights"])):
        cfg = say_mod.merged_config(base_cfg, say_payload)
        real = real_answers(reg, cfg, dev_items)
        sim = [sim_answer(it, raw_w,
                          say_payload["thresholds"])[0] for it in cache]
        mism = sum(1 for a, b in zip(real, sim) if a != b)
        acc, rec = acc_recalls(real, dev_items)
        validations[name] = {"mismatches": mism, "n": len(dev_items),
                             "real_acc": round(acc, 4), "recalls": rec}
    out["sim_validation"] = validations
    if any(v["mismatches"] for v in validations.values()):
        out["verdict"] = "SIMULATOR INVALID — fitting aborted"
        print(json.dumps(out, indent=1))
        return

    # ---- real dev-path baselines
    acc_inc, rec_inc = acc_recalls(
        real_answers(reg, base_cfg, dev_items), dev_items)
    out["dev_path"] = {
        "incumbent": {"acc": round(acc_inc, 4), "recalls": rec_inc},
        "old_say": {"acc": validations["old_say"]["real_acc"],
                    "recalls": validations["old_say"]["recalls"],
                    "raw_fit_acc": old_say["fit"]["dev_acc_say"]},
        "uniform_say": {"acc": validations["uniform"]["real_acc"],
                        "recalls": validations["uniform"]["recalls"]}}
    old_sim = sim_eval(cache, old_say["weights"], old_say["thresholds"])
    out["dev_path"]["old_say_sim"] = old_sim

    # ---- ascents: 2 starts x 2 objectives, judged in simulation
    starts = {"uniform": (uniform_w, dict(base_thresholds)),
              "old_say": ({c: dict(old_say["weights"][c])
                           for c in old_say["weights"]},
                          dict(old_say["thresholds"]))}
    finals = {}
    for sname, (w0, t0_) in starts.items():
        for obj in ("pure", "lex"):
            w, t, m = ascend(cache, seats, w0, t0_, base_thresholds, obj)
            finals[f"{sname}/{obj}"] = (w, t, m)
    out["ascent_finals_sim"] = {
        k: {"acc": round(m["acc"], 4), "clean_recall": m["clean_recall"],
            "recalls": m["recalls"], "clean_blocks": m["clean_blocks"]}
        for k, (w, t, m) in finals.items()}
    champ_key = max(finals, key=lambda k: (finals[k][2]["right"],
                                           finals[k][2]["clean_right"]))
    cw, ct, cm = finals[champ_key]
    out["champion_lane"] = champ_key

    # ---- the winning fit, re-measured on the REAL dev path
    new_say = {"weights": shares_of(cw), "thresholds":
               {c: round(float(ct[c]), 6) for c in CLASSES},
               "seats": seats,
               "fitted_on": "factory/say_dev.json (dev pool) — "
                            "E-001 waking-in-the-loop"}
    beta = min((0.5, 0.75, 1.0, 1.5, 2.0, 3.0),
               key=lambda b: say_mod._cache_ce(cache, cw, ct, b))
    new_say["sharpness_beta"] = beta
    real_new = real_answers(
        reg, say_mod.merged_config(base_cfg, new_say), dev_items)
    sim_new = [sim_answer(it, cw, ct)[0] for it in cache]
    acc_new, rec_new = acc_recalls(real_new, dev_items)
    out["dev_path"]["new_fit"] = {
        "acc": round(acc_new, 4), "recalls": rec_new,
        "sim_acc": round(cm["acc"], 4),
        "sim_real_mismatches": sum(1 for a, b in zip(real_new, sim_new)
                                   if a != b),
        "clean_blocks_sim": cm["clean_blocks"],
        "thresholds": new_say["thresholds"],
        "weights": new_say["weights"]}

    # ---- sealed: exactly once, standard battery path, only if earned
    earned = acc_new > validations["old_say"]["real_acc"]
    evidence: Dict[str, Any] = {"dev_gate": {
        "new_fit_dev_path_acc": round(acc_new, 4),
        "old_fit_dev_path_acc": validations["old_say"]["real_acc"],
        "earned_sealed_eval": earned}}
    if earned:
        sealed_items = load_sealed()["items"]
        s_inc, s_rec_inc = _eval_bug_path(reg, base_cfg, sealed_items)
        s_new, s_rec_new = _eval_bug_path(
            reg, say_mod.merged_config(base_cfg, new_say), sealed_items)
        evidence["sealed"] = {
            "n": len(sealed_items),
            "incumbent_acc": round(s_inc, 4), "incumbent_recalls": s_rec_inc,
            "new_fit_acc": round(s_new, 4), "new_fit_recalls": s_rec_new,
            "beats_incumbent": s_new > s_inc}
    out["evidence"] = evidence

    doc = {"status": "shadow",
           "fitted_at": time.strftime("%Y-%m-%d %H:%M %Z"),
           "rule": ("E-001 candidate state. factory.serve reads "
                    "factory/learned_say.json ONLY; this file never "
                    "serves. Promotion is the standard battery "
                    "adoption step, not this file."),
           "method": ("waking-in-the-loop: coordinate ascent on "
                      "full dev serving-path accuracy, simulated "
                      "exactly from cached margins + verifier "
                      "outcomes and validated answer-for-answer "
                      "against the real WakingDream path"),
           "say": new_say,
           "fit": out["dev_path"],
           "evidence": evidence}
    tmp = STATE_OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, indent=1, ensure_ascii=False))
    tmp.replace(STATE_OUT)
    out["wall_s"] = round(time.time() - t0, 1)
    out["state_file"] = str(STATE_OUT)
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
