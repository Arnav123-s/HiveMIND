"""Composition research — Muse's work, Muse's side.

Prototypes composition rules BEYOND the learned say (which is a
separate build; this module never reads or writes its files, and
the serving composer config is required to carry no "say" payload
for any number here to mean anything).

Data hygiene
------------
Fit and judge come from ONE dev pool, split deterministically
(stratified by label, SPLIT_SEED; a harsher group-disjoint split
by generator kind is kept as `--split group`, a sensitivity
check — see split_pool for why it is not the primary split):

  * phase-3 TRAIN templates (swarm.phase3, seed 21)        — train split
  * the swarm's phase-4 dream corpus (swarm.dream, seed 77) — training data
  * the factory dream TRAIN pool (factory.dream_gen.gen_pool,
    seed 4200, group_prefix "dreamtrain" — the exact call
    factory.dream makes when it dreams for training)

No sealed surface is touched: bug_heldout_v2 / held_slice_v2 and
any sealed battery data are never imported, fitted on, or judged
on. The phase-3 HELD templates are not used either — train splits
only, per the assignment.

Honest caveat, stated in the report too: parts of this pool are
material some members were trained or dream-practised on, so
member margins on it are partly memory, not pure generalisation.
That inflates every rule measured here (baselines included) by an
unknown, shared amount. The COMPARISON between rules on the same
judge split is the finding; the absolute numbers are not a sealed
estimate and must not be quoted as one.

Members
-------
Every adopted bug-* model in factory.dream.load_bug_registry(),
grouped by defect class (16 members over 5 classes at build time).
A member's evidence for its class is its binary margin
logit(cls) - logit(other) (swarm.composers._model_margin); its
implied probability is sigmoid(margin) (exact for a 2-class
softmax). A member's SOLO verdict is its class when margin > 0,
else "clean".

Approaches
----------
1. Confidence routing with abstention: trust the single
   highest-margin member when its margin >= tau (tau fitted on the
   fit split); below tau, fall back to the serving margin-routed
   rule. Reports a coverage / covered-accuracy curve, not one point.
2. Calibrated voting: per-member Platt scaling (a * margin + b,
   i.e. temperature + shift, fitted per member on the fit split),
   then per-class weighted mean of calibrated logits, weights from
   each member's fit-split balanced binary accuracy.
3. Feature-based specialist selection: a multinomial logistic
   regression (numpy softmax regression — the factory interpreter
   is system python3, which has numpy but no torch; same model
   class, ~50x17 parameters, full-batch gradient descent) over
   text statistics + member margin patterns, trained on the fit
   split to pick WHICH member's solo verdict to trust (or NONE ->
   "clean").
4. Stacking (bonus): multinomial logistic regression on per-class
   margin summaries only, trained on the fit split (5-fold
   out-of-fold accuracy on the fit split reported as a sanity
   estimate only; the judged stacker is refit on all of fit).

Baselines on the same judge split: member-alone oracle (a perfect
selector over solo verdicts — an upper bound, not a rule),
mean-probability argmax, margin-routed (serving rule),
mean-margin voting, majority vote.

Run:  OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 python3 -m factory.compose_research
Prints a JSON summary; writes nothing.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

LAB_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(LAB_ROOT / "coding"))
sys.path.insert(0, str(LAB_ROOT))

from swarm import composers as C  # noqa: E402
from swarm import dream as swarm_dream  # noqa: E402
from swarm import phase3 as P3  # noqa: E402

from . import dream as dream_mod  # noqa: E402
from . import dream_gen as G  # noqa: E402

SPLIT_SEED = 20261113
CLASSES = list(C.DEFECT_CLASSES)            # 5 defect classes
LABELS = CLASSES + ["clean"]                # 6 verdicts
MCLIP = 30.0                                # margin clip for numerics


# ------------------------------------------------------------ pool / split
def _def_name(text: str) -> str:
    m = re.search(r"def\s+([A-Za-z_][A-Za-z0-9_]*)", text)
    return m.group(1) if m else "?"


def load_pool() -> List[Dict[str, Any]]:
    """The dev pool: train/dream material only (see module docstring)."""
    raw: List[Dict[str, Any]] = []
    for e in P3.gen_bug_patterns(P3._BUG_TEMPLATES_TRAIN, 21):
        raw.append({"text": e["text"], "label": e["label"],
                    "source": "phase3_train",
                    "group": f"fn:{_def_name(e['text'])}"})
    for e in swarm_dream.gen_dream_bug_examples():
        raw.append({"text": e["text"], "label": e["label"],
                    "source": "swarm_dream",
                    "group": f"fn:{_def_name(e['text'])}"})
    pool, _stats = G.gen_pool({1: 40, 2: 34, 3: 34}, seed=4200,
                              group_prefix="dreamtrain")
    for e in pool:
        raw.append({"text": e["text"], "label": e["label"],
                    "source": "dream_pool",
                    "group": e.get("group") or f"fn:{_def_name(e['text'])}"})
    # exact-text dedupe, first source wins (labels agree on duplicates
    # in this material; a conflicting duplicate would be dropped whole)
    seen: Dict[str, str] = {}
    out: List[Dict[str, Any]] = []
    for e in raw:
        if e["text"] in seen:
            continue
        seen[e["text"]] = e["label"]
        out.append(e)
    return out


def split_pool(items: List[Dict[str, Any]],
               mode: str = "item") -> Tuple[List[int], List[int]]:
    """Deterministic fit/judge split. Returns index lists.

    mode="item" (the primary split): stratified by label — items of
    each label are ordered by md5(SPLIT_SEED:label:text) (stable
    across interpreters, unlike hash()) and the first half goes to
    fit, the rest to judge. Why not group-disjoint: the pool's
    available group ids are generator KINDS (62 kind+label groups,
    ~52 distinct code skeletons for 540 dream items), so a
    group-disjoint split is a leave-kinds-out OOD test with a
    skewed label mix, not a representative dev fit/judge split.
    mode="group" keeps that harsher split available as a
    sensitivity check (greedy label-balanced assignment of whole
    groups, groups ordered by md5(SPLIT_SEED:group))."""
    if mode == "item":
        fit_idx, judge_idx = [], []
        for lab in LABELS:
            idxs = [i for i, e in enumerate(items) if e["label"] == lab]
            idxs.sort(key=lambda i: hashlib.md5(
                f"{SPLIT_SEED}:{lab}:{items[i]['text']}".encode()
            ).hexdigest())
            half = (len(idxs) + 1) // 2
            fit_idx.extend(idxs[:half])
            judge_idx.extend(idxs[half:])
        return sorted(fit_idx), sorted(judge_idx)
    # mode == "group": the greedy group assignment below
    groups: Dict[str, List[int]] = {}
    for i, e in enumerate(items):
        groups.setdefault(e["group"], []).append(i)
    label_total: Dict[str, int] = {}
    for e in items:
        label_total[e["label"]] = label_total.get(e["label"], 0) + 1

    def key(g: str) -> str:
        return hashlib.md5(f"{SPLIT_SEED}:{g}".encode()).hexdigest()

    fit_idx: List[int] = []
    judge_idx: List[int] = []
    fit_lab: Dict[str, int] = {c: 0 for c in label_total}
    judge_lab: Dict[str, int] = {c: 0 for c in label_total}
    for g in sorted(groups, key=key):
        idxs = groups[g]
        labs = {items[i]["label"] for i in idxs}
        fs = sum(fit_lab[c] / label_total[c] for c in labs)
        js = sum(judge_lab[c] / label_total[c] for c in labs)
        to_fit = fs < js or (fs == js and len(fit_idx) <= len(judge_idx))
        (fit_idx if to_fit else judge_idx).extend(idxs)
        tgt = fit_lab if to_fit else judge_lab
        for i in idxs:
            tgt[items[i]["label"]] += 1
    return sorted(fit_idx), sorted(judge_idx)


# ------------------------------------------------------------ margins
def member_table(reg) -> Tuple[List[str], Dict[str, List[int]]]:
    """Flat member list (defect-class order, name order inside a
    class) and, per class, the flat indices of its members."""
    flat: List[str] = []
    by_class: Dict[str, List[int]] = {}
    for cls in CLASSES:
        names = sorted(n for n in reg if n.startswith(f"bug-{cls}-"))
        by_class[cls] = []
        for n in names:
            by_class[cls].append(len(flat))
            flat.append(n)
    return flat, by_class


def extract(items, reg, flat, by_class, config):
    """Per item: member margins (n_members,), routed margins (5,),
    plus the serving composer's own verdict for cross-checking."""
    n = len(items)
    mm = np.zeros((n, len(flat)))
    routed = np.zeros((n, len(CLASSES)))
    for i, e in enumerate(items):
        for j, name in enumerate(flat):
            cls = next(c for c in CLASSES if name.startswith(f"bug-{c}-"))
            mv = C._model_margin(reg[name], e["text"], cls)
            mm[i, j] = mv
        rm = C.class_margins(reg, e["text"], config)
        for k, cls in enumerate(CLASSES):
            routed[i, k] = rm.get(cls, -MCLIP)
    mm = np.where(np.isfinite(mm), mm, np.sign(mm) * MCLIP)
    mm = np.clip(mm, -MCLIP, MCLIP)
    routed = np.clip(routed, -MCLIP, MCLIP)
    return mm, routed


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -35, 35)))


def verdict_from_scores(scores: np.ndarray) -> List[str]:
    """scores: (n, 5) class evidence; argmax wins when > 0 else clean."""
    out = []
    for row in scores:
        k = int(np.argmax(row))
        out.append(CLASSES[k] if row[k] > 0 else "clean")
    return out


def acc(preds: List[str], items, idx) -> float:
    """preds is aligned with items by index (preds[i] judges items[i])."""
    if not idx:
        return 0.0
    return round(sum(1 for i in idx
                     if preds[i] == items[i]["label"]) / len(idx), 4)


# ------------------------------------------------------------ text features
def text_stats(text: str) -> List[float]:
    toks = re.findall(r"[A-Za-z0-9_]+", text)
    return [
        len(text) / 100.0,
        text.count("\n") / 10.0,
        len(toks) / 50.0,
        text.count("+") / 3.0, text.count("-") / 3.0,
        text.count("*") / 3.0, text.count("/") / 3.0,
        text.count("%") / 3.0,
        text.count("==") / 2.0, text.count("!=") / 2.0,
        text.count("return") / 3.0, text.count("print") / 2.0,
        text.count("[") / 5.0, text.count("range") / 2.0,
        (1.0 if "[]" in text or "{}" in text else 0.0),
        (1.0 if "def " in text else 0.0),
    ]


def margin_features(mm_row, routed_row, by_class) -> List[float]:
    feats = [v / 10.0 for v in mm_row]                     # 16 members
    for cls in CLASSES:                                    # per-class mean/max
        vals = mm_row[by_class[cls]]
        feats += [float(vals.mean()) / 10.0, float(vals.max()) / 10.0]
    feats += [v / 10.0 for v in routed_row]                # 5 routed
    srt = np.sort(mm_row)
    feats += [float(srt[-1]) / 10.0,
              float(srt[-2]) / 10.0 if len(srt) > 1 else 0.0,
              float(srt[-1] - srt[-2]) / 10.0 if len(srt) > 1 else 0.0]
    return feats


# ------------------------------------------------------------ small logregs
def fit_softmax(X: np.ndarray, y: np.ndarray, n_out: int,
                epochs: int = 800, lr: float = 0.5, l2: float = 1e-3,
                seed: int = 0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Multinomial logistic regression, full-batch GD on standardised
    features. Deterministic. Returns (W, b, (mu, sd))."""
    mu, sd = X.mean(axis=0), X.std(axis=0) + 1e-9
    Xs = (X - mu) / sd
    rng = np.random.RandomState(seed)
    W = rng.normal(0, 0.01, size=(Xs.shape[1], n_out))
    b = np.zeros(n_out)
    Y = np.zeros((len(y), n_out)); Y[np.arange(len(y)), y] = 1.0
    for _ in range(epochs):
        z = Xs @ W + b
        z -= z.max(axis=1, keepdims=True)
        p = np.exp(z); p /= p.sum(axis=1, keepdims=True)
        g = (p - Y) / len(y)
        W -= lr * (Xs.T @ g + l2 * W)
        b -= lr * g.sum(axis=0)
    return W, b, (mu, sd)


def predict_softmax(X, W, b, norm) -> np.ndarray:
    mu, sd = norm
    z = ((X - mu) / sd) @ W + b
    return np.argmax(z, axis=1)


def fit_platt(margins: np.ndarray, y: np.ndarray) -> Tuple[float, float]:
    """Platt scaling for one member: p = sigmoid(a*m + b) — a is an
    inverse temperature, b a shift. Fitted on the STANDARDISED
    margin by full-batch gradient descent with an L2 penalty: a raw
    Newton fit on unstandardised margins (range ~60) diverges on
    near-separable members (first pass produced a ~ 3e5), so the
    fit is done in z-units and converted back:
    a = a_z / sd, b = b_z - a_z * mu / sd."""
    m = margins.astype(float)
    mu, sd = float(m.mean()), float(m.std()) + 1e-9
    z = (m - mu) / sd
    a_z, b_z = 1.0, 0.0
    for _ in range(1200):
        p = sigmoid(a_z * z + b_z)
        g = (p - y) / len(y)
        a_z -= 0.5 * (float(np.sum(g * z)) + 0.02 * a_z)
        b_z -= 0.5 * (float(np.sum(g)) + 0.02 * b_z)
    return float(a_z / sd), float(b_z - a_z * mu / sd)


# ------------------------------------------------------------ the run
def run(split_mode: str = "item") -> Dict[str, Any]:
    config = C.load_config()
    if config.get("say"):
        raise SystemExit("composer_config carries a 'say' payload — "
                         "that is the learned-say build's surface; "
                         "refusing to measure on top of it")
    reg = dream_mod.load_bug_registry()
    flat, by_class = member_table(reg)
    items = load_pool()
    fit_idx, judge_idx = split_pool(items, split_mode)
    mm, routed = extract(items, reg, flat, by_class, config)
    y = [e["label"] for e in items]
    fit_items = [items[i] for i in fit_idx]
    res: Dict[str, Any] = {
        "split_seed": SPLIT_SEED,
        "split_mode": split_mode,
        "pool_n": len(items),
        "pool_sources": {s: sum(1 for e in items if e["source"] == s)
                         for s in sorted({e["source"] for e in items})},
        "fit_n": len(fit_idx), "judge_n": len(judge_idx),
        "fit_labels": {c: sum(1 for i in fit_idx if y[i] == c) for c in LABELS},
        "judge_labels": {c: sum(1 for i in judge_idx if y[i] == c) for c in LABELS},
        "members": flat,
        "members_per_class": {c: len(v) for c, v in by_class.items()},
    }
    F_, J_ = fit_idx, judge_idx

    def class_agg(mat_mm, agg):
        out = np.zeros((len(items), len(CLASSES)))
        for k, cls in enumerate(CLASSES):
            out[:, k] = agg(mat_mm[:, by_class[cls]], axis=1)
        return out

    mean_margin = class_agg(mm, np.mean)
    mean_prob = np.stack([sigmoid(mm[:, by_class[c]]).mean(axis=1)
                          for c in CLASSES], axis=1)
    max_margin = class_agg(mm, np.max)

    # ---------- baselines (judge) ----------
    base: Dict[str, Any] = {}
    base["mean_probability_argmax"] = acc(
        [(CLASSES[int(np.argmax(mean_prob[i]))]
          if mean_prob[i].max() > 0.5 else "clean")
         for i in range(len(items))], items, J_)
    base["margin_routed"] = acc(verdict_from_scores(routed), items, J_)
    base["mean_margin_voting"] = acc(verdict_from_scores(mean_margin),
                                     items, J_)
    votes = np.stack([(mm[:, by_class[c]] > 0).sum(axis=1) for c in CLASSES],
                     axis=1)
    maj = []
    for i in range(len(items)):
        if votes[i].max() == 0:
            maj.append("clean")
        else:
            tied = [k for k in range(len(CLASSES))
                    if votes[i, k] == votes[i].max()]
            maj.append(CLASSES[max(tied, key=lambda k: mean_margin[i, k])])
    base["majority_vote"] = acc(maj, items, J_)
    # oracle: any member's solo verdict is right (upper bound on selection)
    solo = {}
    for j, name in enumerate(flat):
        cls = next(c for c in CLASSES if name.startswith(f"bug-{c}-"))
        solo[j] = cls
    oracle_right = 0
    for i in J_:
        ok = any((solo[j] if mm[i, j] > 0 else "clean") == y[i]
                 for j in range(len(flat)))
        oracle_right += ok
    base["member_alone_oracle"] = round(oracle_right / len(J_), 4)
    # also: best single member used as a solo composer, and the routed
    # rule's fit-split score for context
    best_solo = {}
    for j, name in enumerate(flat):
        p = [(solo[j] if mm[i, j] > 0 else "clean") for i in range(len(items))]
        best_solo[name] = acc(p, items, J_)
    base["best_single_member_solo_judge"] = max(best_solo.items(),
                                                key=lambda kv: kv[1])
    base["margin_routed_fit"] = acc(verdict_from_scores(routed), items, F_)
    res["baselines_judge"] = base

    # ---------- approach 1: confidence routing + abstention ----------
    best_j = np.argmax(mm, axis=1)
    best_m = mm[np.arange(len(items)), best_j]
    best_cls = [solo[int(j)] for j in best_j]
    routed_pred = verdict_from_scores(routed)

    def a1_preds(tau):
        return [best_cls[i] if best_m[i] >= tau else routed_pred[i]
                for i in range(len(items))]

    tau_grid = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0,
                10.0, 12.0, 15.0, 20.0]
    fit_scores = [(acc(a1_preds(t), items, F_), t) for t in tau_grid]
    tau_star = max(fit_scores)[1]           # ties -> larger tau (max tuple)
    # note: max over (acc, tau) picks the larger tau on an exact tie —
    # deliberate: equal fit accuracy, prefer the more selective rule.
    curve = []
    for t in sorted(set(tau_grid + [tau_star])):
        cov = [i for i in J_ if best_m[i] >= t]
        curve.append({
            "tau": t,
            "coverage": round(len(cov) / len(J_), 4),
            "covered_acc": (round(sum(1 for i in cov
                                      if best_cls[i] == y[i]) / len(cov), 4)
                            if cov else None),
            "overall_acc_with_routed_fallback": acc(a1_preds(t), items, J_),
        })
    res["approach1_confidence_routing"] = {
        "tau_star_fit": tau_star,
        "tau_star_fit_acc": max(s for s, _ in fit_scores),
        "judge_at_tau_star": [c for c in curve if c["tau"] == tau_star][0],
        "judge_curve": curve,
    }

    # ---------- approach 2: calibrated voting ----------
    platt: Dict[str, Tuple[float, float]] = {}
    weights: Dict[str, float] = {}
    cal_logits = np.zeros_like(mm)
    for j, name in enumerate(flat):
        cls = solo[j]
        ybin = np.array([1.0 if y[i] == cls else 0.0 for i in F_])
        a, b = fit_platt(mm[F_, j], ybin)
        platt[name] = (round(a, 4), round(b, 4))
        # balanced binary accuracy of the raw member on fit -> weight
        pred_bin = mm[F_, j] > 0
        tp = float(np.sum(pred_bin & (ybin == 1)))
        fn = float(np.sum(~pred_bin & (ybin == 1)))
        tn = float(np.sum(~pred_bin & (ybin == 0)))
        fp = float(np.sum(pred_bin & (ybin == 0)))
        bal = 0.5 * (tp / max(tp + fn, 1) + tn / max(tn + fp, 1))
        weights[name] = round(max(0.0, bal - 0.5) * 2, 4)
        p = sigmoid(a * mm[:, j] + b)
        cal_logits[:, j] = np.clip(
            np.log(np.clip(p, 1e-9, 1 - 1e-9) / np.clip(1 - p, 1e-9, 1)),
            -12.0, 12.0)   # a saturated member must not veto the vote
    cal_scores = np.zeros((len(items), len(CLASSES)))
    for k, cls in enumerate(CLASSES):
        idxs = by_class[cls]
        w = np.array([weights[flat[j]] for j in idxs])
        if w.sum() <= 0:
            w = np.ones(len(idxs))
        cal_scores[:, k] = (cal_logits[:, idxs] * w).sum(axis=1) / w.sum()
    res["approach2_calibrated_voting"] = {
        "judge_acc": acc(verdict_from_scores(cal_scores), items, J_),
        "uncalibrated_mean_margin_judge_acc": base["mean_margin_voting"],
        "mean_probability_judge_acc": base["mean_probability_argmax"],
        "platt_per_member": platt,
        "weights_per_member": weights,
    }

    # ---------- approach 3: feature-based specialist selection ----------
    X = np.array([text_stats(e["text"]) +
                  margin_features(mm[i], routed[i], by_class)
                  for i, e in enumerate(items)])
    NONE = len(flat)
    target = np.zeros(len(items), dtype=int)
    for i in range(len(items)):
        if y[i] == "clean":
            target[i] = NONE
            continue
        cand = [j for j in by_class[y[i]] if mm[i, j] > 0]
        target[i] = (max(cand, key=lambda j: mm[i, j]) if cand else NONE)
    W, b, norm = fit_softmax(X[F_], target[F_], NONE + 1, seed=1)
    pick = predict_softmax(X, W, b, norm)
    a3_pred = []
    for i in range(len(items)):
        j = int(pick[i])
        a3_pred.append("clean" if j == NONE else
                       (solo[j] if mm[i, j] > 0 else "clean"))
    pick_dist = {flat[int(j)]: int(np.sum(pick[J_] == j))
                 for j in sorted(set(pick[J_].tolist())) if int(j) != NONE}
    if np.any(pick[J_] == NONE):
        pick_dist["NONE->clean"] = int(np.sum(pick[J_] == NONE))
    res["approach3_router"] = {
        "judge_acc": acc(a3_pred, items, J_),
        "fit_acc": acc(a3_pred, items, F_),
        "n_features": int(X.shape[1]),
        "n_actions": NONE + 1,
        "judge_pick_distribution": pick_dist,
        "model": "numpy multinomial logistic regression (softmax), "
                 "full-batch GD, 800 epochs, L2 1e-3; features "
                 "standardised on fit",
    }

    # ---------- approach 4: stacking on margin summaries ----------
    S = np.concatenate([routed / 10.0, mean_margin / 10.0,
                        max_margin / 10.0, mean_prob,
                        votes / 3.0], axis=1)
    y6 = np.array([LABELS.index(v) for v in y])
    # 5-fold OOF on the fit split (sanity estimate only)
    folds = [[] for _ in range(5)]
    for n_, i in enumerate(F_):
        folds[n_ % 5].append(i)
    oof_right = 0
    for f in range(5):
        tr = [i for k, fo in enumerate(folds) if k != f for i in fo]
        Wf, bf, nf = fit_softmax(S[tr], y6[tr], 6, epochs=400, seed=2)
        pf = predict_softmax(S[folds[f]], Wf, bf, nf)
        oof_right += int(np.sum(pf == y6[folds[f]]))
    Ws, bs, ns = fit_softmax(S[F_], y6[F_], 6, epochs=800, seed=2)
    ps = predict_softmax(S, Ws, bs, ns)
    a4_pred = [LABELS[int(v)] for v in ps]
    res["approach4_stacking"] = {
        "judge_acc": acc(a4_pred, items, J_),
        "fit_5fold_oof_acc": round(oof_right / len(F_), 4),
        "n_features": int(S.shape[1]),
    }

    # per-class recall on judge for the headline rules (diagnostics)
    def recalls(preds):
        out = {}
        for c in LABELS:
            idx = [i for i in J_ if y[i] == c]
            out[c] = round(sum(1 for i in idx
                               if preds[i] == c) / len(idx), 4) if idx else None
        return out

    preds_by_name = {
        "margin_routed": routed_pred,
        "mean_margin": verdict_from_scores(mean_margin),
        "calibrated": verdict_from_scores(cal_scores),
        "router": a3_pred,
        "stacking": a4_pred,
        "confidence_tau_star": a1_preds(tau_star),
    }
    res["judge_per_class_recall"] = {k: recalls(v)
                                    for k, v in preds_by_name.items()}
    return res


if __name__ == "__main__":
    mode = "group" if "--split" in sys.argv and \
        sys.argv[sys.argv.index("--split") + 1:][:1] == ["group"] else "item"
    print(json.dumps(run(mode), indent=2))
