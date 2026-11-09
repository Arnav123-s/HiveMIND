"""Phase 4 decomposer specialists (meta layer).

Arnav's standing rule: EVERYTHING is done by a swarm of specialists —
including decomposition itself. When a job is too big for one
specialist to do COMPLETELY, a decomposer specialist does the
splitting into smallest completable tasks; per-kind decomposers exist
where the splitting itself differs:

  defect-class-splitter — a multiclass defect job -> one binary job
      per defect class ("is it class X, or anything else?"). This is
      the specialist that produced phase 4's bug-pattern decomposition.
  slice-splitter — one class job -> one variant job per decidable
      slice of the class (range-bound vs index off-by-ones,
      comparison vs accumulator wrong-operators, ...). The slices are
      decidable from the snippet alone, so a coordinator can route by
      them at inference time.

Both return their sub-jobs as data; the factory trains them and the
win rule judges them, exactly like any other job.
"""
import re


def _relabel(examples, cls):
    return [{"text": ex["text"],
             "label": cls if ex["label"] == cls else "other"}
            for ex in examples]


def defect_class_splitter(task):
    """task: {name_prefix, classes (defect classes), train, heldout}
    -> one binary sub-job per defect class, data relabelled."""
    prefix = task.get("name_prefix", "bug")
    jobs = []
    for cls in task["classes"]:
        tr = _relabel(task["train"], cls)
        he = _relabel(task["heldout"], cls)
        jobs.append({
            "name": f"{prefix}-{cls}-model", "cls": cls,
            "job": f"decide whether a snippet's defect is {cls} "
                   f"(vs anything else, including clean)",
            "classes": [cls, "other"], "train": tr, "heldout": he,
            "n_pos_train": sum(1 for e in tr if e["label"] == cls),
            "n_pos_held": sum(1 for e in he if e["label"] == cls)})
    return {"ok": True, "output": jobs,
            "evidence": f"split into {len(jobs)} per-class binary jobs "
                        f"(positives per class, train: "
                        f"{[j['n_pos_train'] for j in jobs]})"}


# ------------------------------------------------------------ slices
def _slice_wrong_operator(code):
    if re.search(r"(?m)^\s*(if|while)\b.*(==|!=|<=|>=|<|>)", code):
        return "comparison"
    if re.search(r"\+=|-=|\*=|//=|%=", code):
        return "accumulator"
    return "expression"


def _slice_off_by_one(code):
    return "range" if "range(" in code else "index"


def _slice_swapped_operands(code):
    return "comprehension" if re.search(r"\[.*\bfor\b.*\bin\b.*\]", code) \
        else "plain"


def _slice_missing_return(code):
    return "prints" if "print(" in code else "assigns"


SLICES = {"wrong-operator": _slice_wrong_operator,
          "off-by-one": _slice_off_by_one,
          "swapped-operands": _slice_swapped_operands,
          "missing-return": _slice_missing_return}
# mutable-default is deliberately not sliced: in the harvested data it
# has one shape (a mutable literal default, used in place). One shape,
# one completable task — splitting it would invent slices with no
# examples, which is decomposition theatre, not decomposition.


def slice_of(cls, code):
    fn = SLICES.get(cls)
    return fn(code) if fn else "whole"


# ------------------------------------------------------------ signal slices
# A different decomposition axis (phase 4, round 5): not the snippet's
# shape but its SIGNAL SOURCE. An operation-cue function name
# (remainder, quotient, minutes...) tells a reader which operator the
# function is supposed to use — signal the anonymized `code`
# featurizer throws away and the `text` featurizer keeps.
_NAME_CUES = ("remainder", "mod", "quotient", "div", "diff", "minus",
              "subtract", "sub", "ratio", "percent", "average", "mean",
              "total", "sum", "product", "scale", "minute", "hour",
              "count", "clamp", "max", "min")


def has_name_cue(code):
    m = re.search(r"def\s+(\w+)", code)
    return bool(m and any(cue in m.group(1) for cue in _NAME_CUES))


def slice_splitter(task):
    """task: {name_prefix, cls, train, heldout, min_pos (default 2)}
    -> one variant sub-job per slice that has enough positives to be
    a completable task. Slices below the floor are named, not hidden."""
    cls = task["cls"]
    prefix = task.get("name_prefix", "bug")
    min_pos = task.get("min_pos", 2)
    if cls not in SLICES:
        return {"ok": True, "output": [],
                "evidence": f"{cls}: no slice structure — one shape, "
                            f"stays a single completable task"}
    jobs, skipped = [], []
    slices = sorted({slice_of(cls, ex["text"]) for ex in task["train"]})
    for sl in slices:
        tr = [ex for ex in task["train"] if slice_of(cls, ex["text"]) == sl]
        he = [ex for ex in task["heldout"] if slice_of(cls, ex["text"]) == sl]
        n_pos = sum(1 for e in tr if e["label"] == cls)
        if n_pos < min_pos:
            skipped.append(f"{sl} ({n_pos} positives)")
            continue
        jobs.append({
            "name": f"{prefix}-{cls}-{sl}-model", "cls": cls, "slice": sl,
            "job": f"decide whether a {sl}-shaped snippet's defect is "
                   f"{cls} (vs anything else)",
            "classes": [cls, "other"], "train": tr, "heldout": he,
            "n_pos_train": n_pos,
            "n_pos_held": sum(1 for e in he if e["label"] == cls)})
    return {"ok": True, "output": jobs,
            "evidence": f"{cls}: {len(jobs)} slice variant job(s)"
                        + (f"; skipped (too few positives): "
                           f"{', '.join(skipped)}" if skipped else "")}
