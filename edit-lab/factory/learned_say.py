"""The learned say for the bug-pattern composition (Fable-study
Build 2) — Muse's work, Muse's side.

Fable's principle (study section 2.5): a combination rule is itself
a thing to be learned, per seat, re-made at every measurement, and
never frozen into an artifact. This factory's composer combines its
per-class bug-pattern members by FIXED logic (route each class to
one representation by a strengths table; thresholds from the
config). The say replaces that fixed combination with a learned
one:

  * seats — every serving member of a defect class (from the
    registry composition, e.g. the four off-by-one members);
  * standings — a positive weight per seat, fitted per class;
  * thresholds — a firing threshold per class, fitted jointly
    (a class's say and its threshold trade off against each other
    in the composed verdict);
  * sharpness — the temperature of the fit, fitted as a 1-D
    calibration and reported with the say (the serving verdict
    is an argmax, so sharpness calibrates the fit rather than
    the verdict).

Fitting discipline: fit ONLY on the dev pool (factory/say_dev.py —
fresh families + spent surfaces, decontaminated against the sealed
v2 set and the members' train set). The optimizer is joint
coordinate ascent on the composed verdict accuracy over the dev
pool — the objective the battery judges — with a change accepted
only on a strict improvement, so the say departs from the fixed
rule only where dev evidence strictly pushes it. (A cross-entropy
Adam fit was tried first in this build and measured WORSE on dev
verdict accuracy, 0.569-0.579 vs the uniform rule's 0.597: CE spent
itself calibrating hard items. The ascent is also the method this
codebase's own cycle-2 check used.) Prior art, honestly: growth
cycles 1-6 ran a measurement-only say check
(growth_cycle.learned_say_experiment[_v2]) fitted on the members'
TRAIN set and judged on the bare composer over a spent set; it
tied or trailed the routed rule (0.7931 vs 0.8276/0.8621) and was
never wired to serving. This build differs where the study said
it plausibly matters: fresh dev material instead of train, all
serving seats instead of a fixed name pattern, judged through the
full serving path (waking-dream layer included) on the sealed
set, re-fit at every battery run.

Serving discipline (the battery gate decides, not this module):
the fitted say is written to factory/learned_say.json — run state,
deliberately OUT of the specialist registry. factory.serve honors
it only when its status is "adopted", which run_battery sets only
when the composed sealed slice WITH the say beats the incumbent
composition's slice in the same battery run. Otherwise the state
says "shadow" and serving ignores it.
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

LAB_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(LAB_ROOT / "coding"))
sys.path.insert(0, str(LAB_ROOT))

from swarm import composers as C  # noqa: E402

STATE_PATH = Path(__file__).parent / "learned_say.json"
CLASSES = list(C.DEFECT_CLASSES)  # 5 defect classes; + "clean"


# ------------------------------------------------------------ seats
def seats_of(member_names: List[str]) -> Dict[str, List[str]]:
    """Group composition member names into per-class seats:
    bug-<class>-...-model belongs to <class>. Sorted for
    determinism."""
    seats: Dict[str, List[str]] = {}
    for name in member_names:
        for cls in CLASSES:
            if name.startswith(f"bug-{cls}-"):
                seats.setdefault(cls, []).append(name)
                break
    return {cls: sorted(names) for cls, names in seats.items()}


def seat_margins(reg: Dict[str, Any], code: str,
                 seats: Dict[str, List[str]]) -> Dict[str, Dict[str, float]]:
    """{class: {seat: margin}} for one snippet — finite margins
    only (a seat with no features for the snippet abstains, the
    same -inf the composer itself produces)."""
    out: Dict[str, Dict[str, float]] = {}
    for cls, names in seats.items():
        row: Dict[str, float] = {}
        for n in names:
            model = reg.get(n)
            if model is None:
                continue
            m = C._model_margin(model, code, cls)
            if m is not None and math.isfinite(m):
                row[n] = float(m)
        if row:
            out[cls] = row
    return out


def combine(row: Dict[str, Dict[str, float]],
            weights: Optional[Dict[str, Dict[str, float]]]) -> Dict[str, float]:
    """Weighted-mean margin per class. weights=None is the uniform
    (mean) rule. A seat missing from the weights takes the class's
    mean weight (neutral); a class missing from the weights falls
    back to the uniform mean for that class."""
    out: Dict[str, float] = {}
    for cls, seats in row.items():
        w = (weights or {}).get(cls)
        if not w:
            out[cls] = sum(seats.values()) / len(seats)
            continue
        mean_w = sum(w.values()) / len(w)
        num = sum(w.get(n, mean_w) * m for n, m in seats.items())
        den = sum(w.get(n, mean_w) for n in seats)
        out[cls] = num / den if den else 0.0
    return out


def verdict(margins: Dict[str, float],
            thresholds: Dict[str, float]) -> str:
    """The composer's decision form: argmax of margin - threshold,
    'clean' when nothing fires. Identical in form to the fixed
    composer's rule — the say changes the numbers, not the shape."""
    if not margins:
        return "clean"
    adj = {c: m - thresholds.get(c, 0.0) for c, m in margins.items()}
    best = max(adj, key=adj.get)
    return best if adj[best] > 0 else "clean"


# ------------------------------------------------------------ the fit
def _cache_accuracy(cache, weights, thresholds) -> float:
    right = sum(1 for r in cache
                if verdict(combine(r["margins"], weights),
                           thresholds) == r["label"])
    return right / len(cache) if cache else 0.0


def _cache_ce(cache, weights, thresholds, beta) -> float:
    """Mean composed cross-entropy at fixed standings/thresholds
    (defect logits beta * (margin - threshold), clean logit 0) —
    reported for the record; also calibrates the sharpness."""
    total = 0.0
    for r in cache:
        margins = combine(r["margins"], weights)
        logits = {c: beta * (margins[c] - thresholds.get(c, 0.0))
                  for c in CLASSES if c in margins}
        top = max([0.0] + list(logits.values()))
        denom = math.exp(-top) + sum(math.exp(v - top)
                                     for v in logits.values())
        lv = logits.get(r["label"], 0.0) if r["label"] in logits \
            else (0.0 if r["label"] == "clean" else -1e4)
        total += -(lv - top - math.log(denom))
    return total / len(cache) if cache else 0.0


def fit_on_cache(cache: List[Dict[str, Any]],
                 seats: Dict[str, List[str]],
                 base_thresholds: Dict[str, float],
                 passes: int = 4) -> Dict[str, Any]:
    """Fit standings + thresholds on cached seat margins.

    cache rows: {"margins": {cls: {seat: margin}}, "label": str}.
    Joint coordinate ascent on the COMPOSED verdict accuracy over
    the cache — per-seat weights on the grid 0 / 0.25 / 0.5 / 1 /
    2 (relative) and per-class threshold offsets on a grid around
    the base thresholds; a change is accepted only on a STRICT
    accuracy improvement, so ties keep the incumbent values.
    Pure arithmetic on the cache — unit-testable without models.
    A class with a single seat has nothing to combine; only its
    threshold is fitted."""
    classes = [c for c in CLASSES if seats.get(c)]
    freq: Dict[str, float] = {}
    for r in cache:
        freq[r["label"]] = freq.get(r["label"], 0.0) + 1.0
    weights: Dict[str, Dict[str, float]] = {
        c: {n: 1.0 for n in seats[c]} for c in classes}
    tau = {c: float(base_thresholds.get(c, 0.0)) for c in classes}
    acc_uniform = _cache_accuracy(cache, weights, tau)
    ce_before = _cache_ce(cache, weights, tau, 1.0)
    best = acc_uniform
    w_cands = (0.0, 0.25, 0.5, 2.0)
    t_cands = (-0.6, -0.3, -0.15, 0.15, 0.3, 0.6)
    for _ in range(passes):
        improved = False
        for c in classes:
            for nm in seats[c]:
                cur = weights[c][nm]
                for cand in w_cands:
                    if cand == cur:
                        continue
                    weights[c][nm] = cand
                    acc = _cache_accuracy(cache, weights, tau)
                    if acc > best:
                        best, cur, improved = acc, cand, True
                    else:
                        weights[c][nm] = cur
            base_t = float(base_thresholds.get(c, 0.0))
            cur = tau[c]
            for off in t_cands:
                cand = round(base_t + off, 6)
                if cand == cur:
                    continue
                tau[c] = cand
                acc = _cache_accuracy(cache, weights, tau)
                if acc > best:
                    best, cur, improved = acc, cand, True
                else:
                    tau[c] = cur
        if not improved:
            break
    # standings as shares for the record (combine() is scale-free;
    # shares are the readable form)
    shares = {}
    for c in classes:
        tot = sum(weights[c].values())
        shares[c] = {n: (round(weights[c][n] / tot, 6) if tot else 0.0)
                     for n in seats[c]}
    beta = min((0.5, 0.75, 1.0, 1.5, 2.0, 3.0),
               key=lambda b: _cache_ce(cache, weights, tau, b))
    return {"weights": shares,
            "thresholds": {c: round(float(tau[c]), 6) for c in classes},
            "sharpness_beta": beta,
            "fit": {"n": len(cache), "passes": passes,
                    "ce_before": round(ce_before, 4),
                    "ce_after": round(_cache_ce(cache, weights, tau,
                                                beta), 4),
                    "dev_acc_uniform": round(acc_uniform, 4),
                    "dev_acc_say": round(best, 4),
                    "class_freq": {k: int(v)
                                   for k, v in freq.items()}}}


def fit_say(reg: Dict[str, Any], dev_items: List[Dict[str, Any]],
            member_names: List[str],
            base_config: Dict[str, Any]) -> Dict[str, Any]:
    """Collect seat margins over the dev pool with the serving
    members and fit. Returns the say payload (weights, thresholds,
    sharpness, fit report)."""
    seats = seats_of(member_names)
    cache = [{"margins": seat_margins(reg, it["text"], seats),
              "label": it["label"]} for it in dev_items]
    payload = fit_on_cache(cache, seats,
                           base_config.get("thresholds", {}))
    payload["seats"] = seats
    payload["fitted_on"] = "factory/say_dev.json (dev pool)"
    return payload


# ------------------------------------------------------------ serving state
def merged_config(base_config: Dict[str, Any],
                  say: Dict[str, Any]) -> Dict[str, Any]:
    """The composer config the serving stack runs with an adopted
    say: base config + the say payload + the say's thresholds."""
    cfg = dict(base_config)
    cfg["say"] = {"weights": say["weights"]}
    cfg["thresholds"] = dict(say["thresholds"])
    return cfg


def write_state(status: str, say: Optional[Dict[str, Any]],
                evidence: Dict[str, Any]) -> Path:
    doc = {"status": status,
           "fitted_at": time.strftime("%Y-%m-%d %H:%M %Z"),
           "rule": ("serves only when status == 'adopted', set by "
                    "run_battery when the composed sealed slice with "
                    "the say beat the incumbent's in the same run"),
           "say": say, "evidence": evidence}
    tmp = STATE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, indent=1, ensure_ascii=False))
    tmp.replace(STATE_PATH)
    return STATE_PATH


def load_state() -> Optional[Dict[str, Any]]:
    try:
        return json.loads(STATE_PATH.read_text())
    except Exception:  # noqa: BLE001 — absent/corrupt state = no say
        return None


def load_serving_say() -> Optional[Dict[str, Any]]:
    """The say payload serving may use: only an adopted one. Any
    problem reading the state means no say — the incumbent fixed
    composition serves (fail toward the proven path)."""
    st = load_state()
    if not st or st.get("status") != "adopted" or not st.get("say"):
        return None
    return st["say"]
