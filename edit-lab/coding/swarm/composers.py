"""Phase 4 composers: specialists whose one job is assembling other
specialists' verdicts into one verdict (IDEA point 3 — composition).

bug-pattern-composer (debugging niche): the phase-3 single
bug-pattern model was REJECTED (0.690 vs the 0.800 bar). Arnav's fix:
if a specialist cannot do its job COMPLETELY, the job is too big —
the defect-class-splitter (meta) split it into one binary specialist
MODEL per defect class, and the slice-splitter split classes further
into per-slice VARIANTS. This composer's one job:

  - for each defect class, decide the snippet's slice (decidable
    from the snippet alone), then take the margin from the variant
    the MEASURED strengths table says is best at that slice — the
    whole-class model or the slice variant — so each contributes
    where it is strongest;
  - apply the per-class thresholds calibrated on training data;
  - name the strongest class, or "clean" when nothing fires.

No model is enlarged; the capability exists only at the composition
level. Strengths/thresholds live in models/composer_config.json,
written by the phase-4 build from TRAIN measurements only — the
held-out set judges, it never tunes.
"""
import json
from pathlib import Path

from . import factory as F
from .decomposers import has_name_cue, slice_of
from .specialist import Specialist

DEFECT_CLASSES = ["off-by-one", "wrong-operator", "swapped-operands",
                  "mutable-default", "missing-return"]

CONFIG_PATH = Path(__file__).parent / "models" / "composer_config.json"


def load_config():
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {}


def _model_margin(model, code, cls):
    feats = {k: min(v, 3) for k, v in F.featurize(code, model.fmode).items()
             if k in model._featset()}
    if not feats:
        return float("-inf")
    s = model._scores(feats)
    return s.get(cls, 0.0) - s.get("other", 0.0)


def _variant_model(config, cls, code):
    """Signal-slice variant routes (phase 4 round 5): a route matches
    when the snippet carries the variant's signal — an operation-cue
    function name, or (for off-by-one) the index shape, where a
    literal-aware variant can see index values the anonymized whole
    model cannot."""
    for vr in config.get("variant_routes", []):
        if vr["cls"] != cls:
            continue
        if vr["when"] == "named" and has_name_cue(code):
            return vr["model"]
        if vr["when"] == "indexlit" and slice_of(cls, code) == "index":
            return vr["model"]
        if vr["when"] == "always":
            return vr["model"]
    return None


def class_margins(reg, code, config=None):
    """{defect class: margin} routed by the measured strengths table.
    Precedence: signal-slice variant (measured strongest on its
    signal slice) -> shape-slice variant -> whole-class model.
    A class with no adopted model is absent — a named gap, never a
    guessed verdict."""
    config = config if config is not None else load_config()
    strengths = config.get("strengths", {})
    out = {}
    for cls in DEFECT_CLASSES:
        if config.get("ensemble"):
            # round 8 composition: the class verdict is the MEAN
            # margin of every adopted representation of that class
            # (whole / name-aware / harvest-extended) — a jury of
            # diverse specialists instead of a single routed winner.
            cands = []
            for nm in (f"bug-{cls}-model", f"bug-{cls}-named-model",
                       f"bug-{cls}-harvest-model",
                       f"bug-{cls}-indexlit-model"):
                m = reg.get(nm)
                if m is not None:
                    cands.append(_model_margin(m, code, cls))
            if cands:
                out[cls] = sum(cands) / len(cands)
            continue
        margin = None
        vname = _variant_model(config, cls, code)
        if vname:
            vm = reg.get(vname)
            if vm is not None:
                margin = _model_margin(vm, code, cls)
        if margin is None:
            sl = slice_of(cls, code)
            if strengths.get(cls, {}).get(sl) == "slice":
                vm = reg.get(f"bug-{cls}-{sl}-model")
                if vm is not None:
                    margin = _model_margin(vm, code, cls)
        if margin is None:
            m = reg.get(f"bug-{cls}-model")
            if m is not None:
                margin = _model_margin(m, code, cls)
        if margin is not None:
            out[cls] = margin
    return out


def make_bug_pattern_composer(reg):
    def _compose(task):
        code = task.get("code", task.get("text", "")) \
            if isinstance(task, dict) else str(task)
        config = load_config()
        margins = class_margins(reg, code, config)
        if not margins:
            return {"ok": False, "output": None,
                    "specialist": "bug-pattern-composer",
                    "evidence": "no per-class bug models are loaded",
                    "gap": "no-class-models",
                    "growth_move": "harvest+train per-class models (phase 4)"}
        thresholds = config.get("thresholds", {})
        adjusted = {c: m - thresholds.get(c, 0.0)
                    for c, m in margins.items()}
        best = max(adjusted, key=adjusted.get)
        label = best if adjusted[best] > 0 else "clean"
        # two-stage composition (phase 4 round 6): the clean-guard
        # specialist — the one class phase 4 initially forgot to give
        # a specialist — can out-vote a defect verdict, but only by
        # margin: the defect stands unless the guard is MORE sure
        # the snippet is clean than the defect model is sure it isn't.
        guard = reg.get("bug-clean-guard-model")
        if label != "clean" and guard is not None \
                and config.get("clean_guard"):
            gm = _model_margin(guard, code, "clean")
            if gm > adjusted[best]:
                label = "clean"
        pretty = ", ".join(f"{c}:{margins[c]:+.2f}" for c in DEFECT_CLASSES
                           if c in margins)
        return {"ok": True, "output": label,
                "evidence": f"composed from {len(margins)} class model(s); "
                            f"margins {pretty}"}
    return _compose


def register_composers(reg):
    reg.add(Specialist("bug-pattern-composer", "debugging",
                       "compose the per-class bug models into one "
                       "bug-pattern verdict (or clean)",
                       fn=make_bug_pattern_composer(reg)))
    return reg
