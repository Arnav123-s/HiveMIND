"""A small executable vocabulary for corrections to a two-entry draft."""
import re

from training.experiments.hive_commitments import DAYS, literal, replace


DAY = r"\b(day|date|weekday|when)\b"
SITE = r"\b(site|place|location|venue|where)\b"
BACK = r"\b(original|opening|restore|undo|back|revert|previous|old)\b"
REVERT = r"\b(scratch|withdraw|restore|forget|drop|undo|revert|cancel|discard|roll back|changed my mind)\b"


def fields(clause):
    return [i for i, pattern in enumerate((DAY, SITE)) if re.search(pattern, clause, re.I)]


def symbols(text, allowed):
    pattern = r"\b(?:" + "|".join(re.escape(s) for s in allowed) + r")\b"
    return [(m.start(), m.group().title()) for m in re.finditer(pattern, text, re.I)]


def learn_exchange(text, before, after):
    """Infer the demonstrated two-record operation from an independently checked before/after."""
    if len(before) != 2 or set(before) != set(after):
        raise ValueError("expected the same two entries")
    a, b = before
    candidates = [j for j in (0, 1) if before[a][j] != before[b][j] and
                  after == replace(before, [(a, j, before[b][j]), (b, j, before[a][j])])]
    verb = re.match(r"(?:please\s+)?([a-z]+)\b", text.lower())
    if len(candidates) != 1 or not verb:
        raise ValueError("receipt does not identify a single field exchange")
    return {"verb": verb.group(1), "operation": "exchange", "observed_field": candidates[0]}


def learned_exchange(t, names, draft, record):
    verb = re.escape(record["verb"])
    if record.get("operation") != "exchange" or not re.match(rf"(please\s+)?{verb}\b", t):
        return None
    # Only execute a two-party, one-field exchange with no additional instruction except preservation.
    parts = [p.strip() for p in re.split(r"[.;!?]", t) if p.strip()]
    if not parts or any(not re.match(r"(keep|preserve|leave|neither)\b", p) for p in parts[1:]):
        return None
    vocabulary = set(("please the two both of between current entries entry bookings booking reservations reservation "
                      "pickups pickup meetings meeting items item days day dates date weekdays weekday sites site "
                      "places place locations location venues venue").split()) | {record["verb"], *(n.lower() for n in names)}
    if (not re.search(r"\b(two|both|between)\b", parts[0])
            or set(re.findall("[a-z]+", parts[0])) - vocabulary):
        return None
    options = [i for i, pattern in enumerate((r"\b(days?|dates?|weekdays?)\b", r"\b(sites?|places?|locations?|venues?)\b"))
               if re.search(pattern, parts[0])]
    if len(options) != 1:
        return None
    j = options[0]
    protect = (r"\b(days?|dates?|weekdays?)\b", r"\b(sites?|places?|locations?|venues?)\b")
    if any(re.search(protect[j], p) or re.search(r"\b(and|then|move|change|set|give|except)\b", p) for p in parts[1:]):
        return None
    a, b = names
    return replace(draft, [(a, j, draft[b][j]), (b, j, draft[a][j])])


def interpret(public, draft, clarification=None, learned=None):
    opening, names, text = public["opening"], public["names"], public["last"]
    plain = literal(text, public, draft)
    if plain is not None:
        return "apply", plain
    edited = [n for n in names if opening[n] != draft[n]]
    if len(edited) != 1:
        return "defer", None
    source = edited[0]
    peer = next(n for n in names if n != source)
    changed = [j for j in (0, 1) if draft[source][j] != opening[source][j]]
    t = text.lower().replace("’", "'")
    mentions = symbols(t, names)
    values = symbols(t, (*DAYS, *public["sites"]))
    clauses = re.split(r"[.;!?]|\bbut\b", t)
    if re.search(r"\b(one of|one entry|one booking|one item|either entry|which one|which if you ask)\b", t) and not mentions and values:
        target = symbols(clarification or "", names)
        if len(target) != 1 or len(values) != 1:
            return "ask", f"Which item do you mean, {names[0]} or {names[1]}?"
        value = values[0][1]
        return "apply", replace(draft, [(target[0][1], int(value not in DAYS), value)])
    # Conditional changes need more evidence. A statement explicitly keeping the draft has a defined effect.
    if re.search(r"\b(if|unless|maybe|might|possibility|suggested|tentative|perhaps|proposed)\b", t):
        if re.search(r"not a decision|haven't approved|not approved|keep the draft|use the draft|do not act|don't change", t):
            return "apply", draft
        return "defer", None
    if re.search(r"\b(do not|don't|never)\s+(swap|exchange|duplicate|copy|move|schedule|restore|change|set)", t):
        return "defer", None
    if learned:
        swapped = learned_exchange(t, names, draft, learned)
        if swapped is not None:
            return "apply", swapped
    if re.search(r"day after|weekday immediately following|calendar day following", t):
        if not mentions or len(set(n for _, n in mentions)) != 2:
            return "defer", None
        dest, reference = mentions[0][1], mentions[-1][1]
        day = DAYS[(DAYS.index(draft[reference][0]) + 1) % 7]
        return "apply", replace(draft, [(dest, 0, day)])
    if re.search(r"\b(swap|exchange)\b|the other's current", t):
        scope = fields(clauses[0].replace("sites", "site").replace("days", "day").replace("locations", "location"))
        if len(scope) == 1:
            j = scope[0]
            return "apply", replace(draft, [(source, j, draft[peer][j]), (peer, j, draft[source][j])])
        return "defer", None
    if values:
        # Only named, affirmative assignments execute. An unfamiliar request stays unresolved.
        if not re.search(r"\b(move|set|switch|put|make|goes|give|change|assign|schedule|reschedule)\b", t):
            return "defer", None
        if re.search(r"\b(not|don't|never|or|between|except|after|before|unless|once|provided)\b|subject to", t):
            return "defer", None
        destinations = {s.lower() for s in public["sites"]} | {"its", "the"}
        if any(m[1] not in destinations for m in re.finditer(r"\bat\s+([\w'-]+)", t)):
            return "defer", None
        edits = []
        for pos, value in values:
            prior = [n for idx, n in mentions if idx < pos]
            if not prior:
                return "defer", None
            edits.append((prior[-1], int(value not in DAYS), value))
        if len({(n, j) for n, j, _ in edits}) != len(edits):
            return "defer", None
        base = opening if re.search(REVERT, clauses[0]) else draft
        return "apply", replace(base, edits)
    if re.search(r"exact same|as well|both.*match|duplicate|same.*too", t):
        return "apply", replace(draft, [(peer, j, draft[source][j]) for j in changed])
    moved = next((c for c in clauses if re.search(r"meant for|belongs (on|to)|intended for|wrong (label|item|entry)|misaddressed", c)), None)
    if moved is not None and peer.lower() in t:
        transfer = fields(moved) or changed
        steps = [(source, j, opening[source][j]) for j in transfer] + [(peer, j, draft[source][j]) for j in transfer]
        return "apply", replace(draft, steps)
    restore = [j for c in clauses if re.search(BACK, c) for j in fields(c)]
    if restore and source.lower() in t:
        return "apply", replace(draft, [(source, j, opening[source][j]) for j in restore])
    if re.search(REVERT, t) and re.search(r"both|altogether|in full|whole|entire|everything|start", t):
        return "apply", opening
    return "defer", None
