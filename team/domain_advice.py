"""Consult a checked neural edit for one decision within an ordinary request."""
import http.client
import re

from . import domain_intent, engram, ternary
from .water_phase import equilibrium_phase


# Each starter edit learned a narrower question than its domain.
_SKILLS = {
    "python_operations": ("coding", {"map", "filter", "sum"}, r"each|every|only|retain|discard|filter|sum|total|add up"),
    "geometry_measure": ("math", {"length", "area", "volume"}, r"distance|span|covers?|holds?|capacity|edge|surface|perimeter|volume|area|length"),
    "water_phase": ("physical_science", {"solid", "liquid", "gas"}, r"water"),
    "conversation_move": ("conversation", {"ask", "confirm", "thank"}, r"arranged|agreed|settled|arrangement|booking|favou?r|helped|missing|omits?|appreciat\w*|thank\w*|confirm\w*"),
    "dataset_split": ("machine_learning", {"train", "validation", "test"}, r"split|dataset|examples|fold|holdout|held.out|early stopping|hyperparameters?|training data"),
    "timing_unit": ("computer_engineering", {"ns", "us", "ms"}, r"unit|prefix|millionth|thousandth|billionth|nanoseconds?|microseconds?|milliseconds?"),
}
# When the subject channel abstains, an explicit task can still identify one checked edit.
# Both a subject-specific phrase and the edit's scoped decision must appear.
_TOPICS = {
    "python_operations": r"python",
    "geometry_measure": r"geometr(?:y|ic)|container|tank|box|wall|surface|rectangle|cylinder|sphere|cube",
    "water_phase": r"water",
    "conversation_move": r"reply|respond|say|answer|acknowledge|word|write",
    "dataset_split": r"model|dataset|hyperparameters?|early stopping|data split",
    "timing_unit": r"clock|processor|timer|tick|circuit|latency|oscilloscope|time unit|timing unit",
}


def _matches(words, message):
    return re.search(r"\b(?:" + words + r")\b", message, re.I) is not None


def _explicit_skill(message):
    matches = [skill for skill, topic in _TOPICS.items()
               if _matches(topic, message) and _matches(_SKILLS[skill][2], message)]
    return matches[0] if len(matches) == 1 else None


def _query(base, system, prompt, row, skill, *, expected=None):
    receipt = {"engram": row["name"], "skill": skill}
    try:
        reply = ternary.chat(base, [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                             max_new_tokens=1, temperature=0.0, also=(row["name"],))
    except (OSError, RuntimeError, http.client.HTTPException):
        return {**receipt, "accepted": False, "label": None, "reason": "inference_unavailable"}
    surface = reply.strip().casefold()
    choices = {label.casefold(): label for label in row["labels"]}
    label = choices.get(surface) or choices.get(surface.removesuffix("."))
    if expected is not None and label is not None and label != expected:
        return {**receipt, "label": label, "model_reply": reply.strip(), "accepted": False,
                "reason": "contradicts_equilibrium_phase", "checked_phase": expected,
                "check": "pure_water_equilibrium_1atm"}
    if expected is not None and label is None:
        return {**receipt, "label": None, "model_reply": reply.strip(), "accepted": False,
                "reason": "unrecognized_phase_label", "checked_phase": expected,
                "check": "pure_water_equilibrium_1atm"}
    return {**receipt, "label": label, "accepted": label is not None}


def consult(message, base, domain, system, *, direct_labels=False):
    if not engram.enabled() or base == "coder":
        return None
    # A user can explicitly name a retained local convention, including one the subject router has never seen.
    learned = engram.named_label_for(message, base)
    if learned:
        if direct_labels and engram.is_label_request(message, learned, domain):
            return None
        return _query(base, system, message, learned, learned["task"])
    expected_skill = None
    lookup_domain = domain
    if not lookup_domain:
        expected_skill = _explicit_skill(message)
        if expected_skill is None:
            return None
        lookup_domain = _SKILLS[expected_skill][0]
    row = engram.label_for(message, base, lookup_domain)
    if not row:
        return None
    skill = row.get("skill_id", "")
    spec = _SKILLS.get(skill)
    if (not spec or lookup_domain != spec[0] or (expected_skill and expected_skill != skill)
            or set(row["labels"]) != spec[1] or not row.get("instruction")):
        return None
    if not _matches(spec[2], message):
        return None
    # An explicit label request can already use the edit on the answer itself.
    if direct_labels and engram.is_label_request(message, row, domain):
        return None
    if not domain_intent.requests_choice(message, skill, row["labels"]):
        return None
    expected = None
    if skill == "water_phase":
        expected = equilibrium_phase(message)
        if expected is None:
            return None
    prompt = row["instruction"] + " " + message
    return _query(base, system, prompt, row, skill, expected=expected)


def hint(decision):
    if decision and decision.get("reason") == "contradicts_equilibrium_phase":
        return (f"The equilibrium check for pure water at one standard atmosphere gives {decision['checked_phase']}. "
                "Use that checked phase for these conditions.")
    if not decision or not decision["accepted"]:
        return ""
    topic = decision["skill"].replace("_", " ")
    return f"A specialist suggests {decision['label']} for the {topic} decision. Check it against the request."
