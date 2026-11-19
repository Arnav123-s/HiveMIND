"""Recognize a request for the decision a starter label edit can make."""
import re


# The output contract of each fitted head determines what it can answer.
_DECISION = {
    "python_operations": r"operation|function|built[- ]?in|transformation",
    "geometry_measure": r"measure(?:ment)?|quantity|dimension",
    "water_phase": r"phase|state",
    "conversation_move": r"move|approach|action|response type|kind of (?:response|reply)",
    "dataset_split": r"split|partition|fold|dataset|(?:data|example) set|subset",
    "timing_unit": r"unit|prefix|symbol|abbreviation",
}
_QUALIFIER = (r"the|a|an|kind|type|name|of|is|would|be|one|right|best|correct|appropriate|suitable|"
              r"python|built[- ]?in|list|geometric|physical|equilibrium|conversation(?:al)?|next|polite|"
              r"data|dataset|model|hardware|timing|time|si|short")


def requests_choice(message, skill, labels):
    decision = _DECISION.get(skill)
    if not decision:
        return False
    noun = r"(?:" + decision + r")"
    modifiers = r"(?:\s+(?:" + _QUALIFIER + r")){0,5}\s+"
    if re.search(r"\b(?:which|what|choose|select|identify|name|pick)" + modifiers + noun + r"\b", message, re.I):
        return True
    # Some questions name the decision first, for example "the time unit: what is it called?"
    if re.search(r"\b" + noun + r"\b[^.!?\n]{0,55}\b(?:is (?:it|that) called|should I (?:use|choose)|fits (?:best|here))\b",
                 message, re.I):
        return True
    if re.search(r"\b(?:give|return|reply with|answer with) (?:me )?(?:just |only )?(?:its |the )?"
                 + noun + r"(?: name)?\b", message, re.I):
        return True
    # An explicit choice between all labels also states the output contract.
    named = all(re.search(r"(?<!\w)" + re.escape(label) + r"(?!\w)", message, re.I) for label in labels)
    return named and bool(re.search(r"\b(?:choose|pick|select|classify|label|which|should I|only|one[- ]word)\b", message, re.I))
