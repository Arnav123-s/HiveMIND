"""Use a checked fieldwork method from the local bank.

Every method can be invoked explicitly with an exact task name and JSON input.
Two retained contracts also accept direct natural-language requests. Their parsers
consume the whole message. Unrecognized requests continue to the ordinary team.
All implementations of the chosen contract must agree inside the fieldwork guest.
"""
import json
import math
import re

from . import config, skill_inputs


def bank_path():
    return config.saved_bank_path()


def available():
    """Task names that can be invoked from the configured local bank."""
    from training.experiments.fieldwork.work import load_bank
    return sorted({row["task"] for row in load_bank(bank_path())})


def guest():
    """The fieldwork guest, or None when the runtime is not on this machine."""
    from training.experiments.fieldwork.guest import Guest
    sdk = config.fieldwork_sdk_path()
    try:
        import wasmtime  # noqa: F401
        return Guest(sdk) if (sdk / "python.wasm").is_file() else None
    except (ImportError, OSError):
        return None


# Natural-language adapters are tied to the contracts they were checked on. A new
# description under the same name may require a different provider, unit or tariff.
SHIPPING = ("depot_shipping_fee", "Write solve(x) to calculate a depot's shipping fee in integer cents. "
            "x has a grams list of positive whole parcel weights. An empty shipment costs zero. "
            "Any nonempty shipment has one dispatch charge of 250 cents and costs another 90 cents per started "
            "500 grams. Use the depot's rounding convention illustrated by the examples. Return just the integer fee.")
INVOICE = ("invoice_tax", "Return the invoice tax in integer cents for the nonnegative line amounts in x['lines']. "
           "Use the billing convention illustrated by the labeled examples on this work order.")
# These diagnostic bills distinguish the two stated rounding conventions.
# The second invoice bill also separates half-up from a competing tie convention.
_CONVENTIONS = {
    (SHIPPING, "per-parcel"): ("grams", [([1, 1], 430), ([501, 499], 520)]),
    (SHIPPING, "pooled"): ("grams", [([1, 1], 340), ([501, 499], 430)]),
    (INVOICE, "per-line"): ("lines", [([11, 11], 2), ([10, 20], 2)]),
    (INVOICE, "invoice-total"): ("lines", [([11, 11], 1), ([10, 20], 2)]),
}
_CONVENTION = re.compile(r"\s+(?:with|using)\s+(?:(?:our|the)\s+)?(?:usual\s+)?"
                         r"(per-parcel|pooled|per-line|invoice-total)\s+(?:pricing|rounding)[.?!]?\s*$", re.I)
_EXPLICIT = re.compile(r"(?:please\s+)?(?:run|use|apply)\s+(?P<saved>the saved (?:method|task)\s+)?"
                       r"(?P<task>[a-z][a-z0-9_]{0,60})(?:@(?P<contract>[^\s:]*))?"
                       r"(?:\s*(?::|\bwith\b|\bon\b)\s*(?P<data>.*))?", re.I | re.S)


def explicit_request(message):
    """Parse a direct invocation of a named method and its optional JSON argument."""
    return _EXPLICIT.fullmatch(message.strip()) if len(message) <= 32_768 else None


def input_keys(versions, description):
    """Literal top-level fields named by a retained description or its implementations."""
    keys = set()
    for text in [description] + [row["source"] for row in versions]:
        for match in re.finditer(r"""\bx(?:\[\s*|\.get\(\s*)['"]([^'"\n]+)['"]""", text):
            keys.add(match[1])
    return sorted(keys)


def _object(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError("duplicate JSON key")
    return result


def _finite(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("non-finite number")
    return number


def _archived_geology_phases(contract):
    """The two documented public inputs for this legacy, phase-dependent work order."""
    if contract[0] != "geology_order":
        return {}
    path = config.ROOT / "training/reports/rule_lab/fieldwork/geology-order.json"
    try:
        spec = json.loads(path.read_text())
        if (spec["name"], spec["task"]) == contract:
            return {row["input"]["phase"]: row["input"] for row in spec["examples"]}
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return {}


def _geology_inputs(value, phases):
    phase = value.get("phase") if isinstance(value, dict) else None
    if not isinstance(phase, str) or phase not in phases:
        return "a JSON object with phase " + " or ".join(sorted(phases))
    sample = phases[phase]
    parts = [(value, sample, phase)]
    if "snapshot" in sample:
        parts.append((value.get("snapshot"), sample["snapshot"], "snapshot"))
    for actual, example, label in parts:
        if not skill_inputs.accepts(actual, skill_inputs.infer_contract([example])):
            return f"{label} fields " + ", ".join(sorted(example)) + " with the types in the work order"
        # Events and kept tickets are positional records; repeated rows and an empty input are allowed.
        for key, rows in example.items():
            if isinstance(rows, list) and rows and isinstance(rows[0], list):
                layout = tuple(type(cell) for cell in rows[0])
                if any(tuple(type(cell) for cell in row) != layout for row in actual[key]):
                    return f"the {key} rows in the format of the public work order"
    return None


def _json_input(data, versions, contract):
    rule = {SHIPPING: ("grams", 1), INVOICE: ("lines", 0)}.get(contract)
    legacy = [r for r in versions if not r.get("input_contract")]
    phases = _archived_geology_phases(contract) if legacy else {}
    keys = input_keys(legacy, contract[1]) if legacy and not phases else []
    shapes = [r["input_contract"] for r in versions if "input_contract" in r]
    if not all(skill_inputs.valid(shape) for shape in shapes):
        return None, "a new fieldwork check for the saved method because its input types could not be read"
    names = sorted(set(keys).union(*(s["properties"] for s in shapes)))
    kinds = sorted({k for shape in shapes for k in shape["kinds"]})
    needed = ("a JSON value of type " + " or ".join(kinds)) if kinds else "the method's input as JSON"
    if names:
        needed += " with the checked fields " + ", ".join(names)
    if rule:
        field, minimum = rule
        needed = (f'a JSON object with "{field}" as a list of '
                  + ("positive" if minimum else "nonnegative") + " whole numbers")
    if data and len(data) > 32_768:
        return None, "a smaller batch (32,768 characters of JSON or fewer)"
    try:
        value = json.loads(data or "", object_pairs_hook=_object, parse_float=_finite, parse_constant=_finite)
    except (ValueError, RecursionError):
        return None, needed
    if phases:
        missing = _geology_inputs(value, phases)
        if missing:
            return None, missing
    if keys and (not isinstance(value, dict) or set(value) != set(keys)):
        return None, needed
    if any(not skill_inputs.accepts(value, shape) for shape in shapes):
        return None, needed
    if rule and (not isinstance(value, dict) or set(value) != {field} or not isinstance(value[field], list)
                 or any(type(v) is not int or v < minimum for v in value[field])):
        return None, needed
    return value, None


# Every token of the request must be accounted for as a direct question, its
# arguments, or a labeled reference. In particular, numbers in other clauses
# never become a parcel weight or an invoice line.
_POLITE = r"(?:(?:please|(?:can|could|would) you)\s+)*(?:please\s+)?"
_DET = r"(?:(?:the|our|my|this|these|a|an|its)\s+)?"
_DEPOT = r"(?:(?:usual|standard|local)\s+)?depot(?:'s)?"
_SHIP_FEE = rf"{_DET}(?:(?:{_DEPOT}\s+)?(?:shipping|dispatch|delivery|shipment)\s+(?:fee|cost|charge|price)|{_DEPOT}\s+(?:fee|cost|charge|price|postage)|postage at (?:our|the) depot)"
_VERB = r"(?:calculate|compute|quote|find|tell me|work out|give me|what(?:'s| is| will be))"
_SEND = r"(?:send|ship|dispatch|post)"
_SHIP_QUESTION = re.compile(
    rf"{_POLITE}(?:{_VERB}\s+{_SHIP_FEE}(?:\s+in cents)?"
    rf"|(?:what (?:will|does)|how (?:much|many cents) (?:will|does|would))\s+{_DET}{_DEPOT}\s+(?:charge|bill)(?: me)?"
    rf"|how much (?:is it |will it cost |does it cost )?to {_SEND}"
    rf"|(?:please )?price\s+{_DET}{_DEPOT}\s+shipment"
    rf"|for {_DET}{_DEPOT} tariff, (?:please )?(?:price|quote)"
    rf"|{_VERB} the charge under {_DET}{_DEPOT} parcel tariff"
    rf"|what(?:'s| is) the price for this shipment)"
    rf"(?:\s+(?:to\s+{_SEND}|for|on)|\s*:)?"
    r"(?P<data>\s+.*|$)"
)
_INVOICE_QUESTION = re.compile(rf"{_POLITE}{_VERB}\s+{_DET}invoice tax(?:\s+(?:on|for))?(?P<data>\s+.*|$)")
_REFERENCE = re.compile(r"(?:(?:for|on)\s+)?(?:order|invoice|ref(?:erence)?)\s+(?:id\s+|number\s+)?#?[a-z0-9-]*[0-9][a-z0-9-]*\b")
_PARCEL = r"(?:parcels?|packages?|box(?:es)?|packets?|mailers?|cartons?|envelopes?)"
_UNIT = {"grams": r"(?:grams?|g)", "lines": r"(?:cents?|¢)"}
_COUNTS = ("one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve")
_COUNT = r"(?:[1-9][0-9]{0,2}|" + "|".join(_COUNTS) + ")"
_MASS = r"(?:[1-9][0-9]{0,2}(?:,[0-9]{3})+|[0-9]+)"


def _count(word):
    return int(word) if word.isdigit() else _COUNTS.index(word) + 1


def _amounts(data, field):
    """Parse a complete list; a final unit may apply to a preceding comma list."""
    if field == "grams" and re.fullmatch(r"(?:an? )?empty shipment|(?:no|zero|0) " + _PARCEL, data):
        return []
    if field == "grams":
        list_in_grams = re.fullmatch(r"(?:parcel )?weights? \(grams?\):\s*([0-9]+(?:\s*,\s*[0-9]+)*)", data)
        if list_in_grams:
            weights = [int(v) for v in list_in_grams[1].split(",")]
            return weights if all(weights) else None
    data = re.sub(r"^(?:(?:at the depot )?i have|(?:my|the) shipment (?:contains|has))\s+", "", data)
    data = re.sub(rf"^(?:one|a single) (?=[0-9]+\s*{_UNIT[field]})", "", data)
    data = re.sub(rf"^(?P<count>{_COUNT}) separate (?={_PARCEL}\b)", r"\g<count> ", data)
    noun = _PARCEL if field == "grams" else r"(?:invoice )?line(?: amounts?|s)?"
    prefix = re.match(rf"^{_DET}(?:(?P<count>{_COUNT})\s+)?(?P<noun>{noun})\b"
                      r"(?:\s+weights?)?(?:\s+(?:of|at|weighing|weighs?|is|are))?\s*[:,]?\s*", data)
    declared = None
    if prefix:
        if prefix["count"]:
            declared = _count(prefix["count"])
        elif field == "grams" and prefix["noun"] in ("parcel", "package", "box", "packet", "mailer", "carton", "envelope") and "weights" not in prefix[0]:
            declared = 1
        data = data[prefix.end():]
    unit = _UNIT[field]
    # One declared group "three parcels, 480 g each" represents three items.
    repeated = re.fullmatch(rf"({_MASS})\s*{unit}\s+(?:each|apiece)", data)
    if declared and repeated:
        number = int(repeated[1].replace(",", ""))
        return [number] * declared if number or field == "lines" else None
    # A comma with a three-digit suffix inside an integer is thousands punctuation.
    data = re.sub(rf"{_MASS}", lambda m: m[0].replace(",", ""), data)
    parts = re.split(r"\s*(?:,\s*(?:and\s+)?|\band\b|\bplus\b)\s*", data)
    item = rf"{_DET}(?P<number>[0-9]+)(?:(?:-|\s*)(?P<unit>{unit}))?(?:\s+{noun})?"
    result = []
    for index, part in enumerate(parts):
        copies = 1
        repeated_item = re.fullmatch(rf"(?:(?P<n>{_COUNT})\s*[x×]\s*|(?:a )?pair of )(?P<item>.+)", part)
        if repeated_item:
            copies = _count(repeated_item["n"]) if repeated_item["n"] else 2
            part = repeated_item["item"]
        match = re.fullmatch(item, part)
        if not match or (not match["unit"] and (index == len(parts) - 1 or not part.isdigit())):
            return None
        value = int(match["number"])
        if field == "grams" and value == 0:
            return None
        result.extend([value] * copies)
    if declared is not None and declared != len(result):
        return None
    return result


def _natural(message, contract):
    """Return (input, missing field) for a scoped request, or None to defer."""
    if len(message) > 2048:
        return None
    question = _SHIP_QUESTION if contract == SHIPPING else _INVOICE_QUESTION
    if "{" in message:
        prefix, _, body = message.strip().partition("{")
        match = question.fullmatch(" ".join(prefix.lower().replace("’", "'").split()).strip(": "))
        if not match or match["data"].strip(" :,") not in ("", "from this exact input", "this empty shipment"):
            return None
        # Preserve original key case and reject any text after the JSON document.
        data = "{" + body
        if data.endswith((".", "?")):
            data = data[:-1]
        value, missing = _json_input(data, [], contract)
        if match["data"].strip(" :,") == "this empty shipment" and value != {"grams": []}:
            return None
        return value, missing
    text = " ".join(message.lower().replace("’", "'").split()).strip(" .?!")
    clauses = [s.strip(" ,") for s in re.split(r"\s*[?!;]\s*|\.\s+", text)]
    field = "grams" if contract == SHIPPING else "lines"
    question_seen = False
    values = None
    declared = None
    for clause in clauses:
        # Only complete, explicitly labeled references may be omitted.
        clause = re.sub(rf"^(?:{_REFERENCE.pattern})\s*[:,]\s*", "", clause)
        clause = re.sub(rf"\s+(?:{_REFERENCE.pattern})$", "", clause)
        if field == "grams" and re.fullmatch(rf"(?:please )?use {_DET}{_DEPOT} tariff", clause):
            continue
        match = question.fullmatch(clause)
        if match:
            if question_seen:
                return None
            question_seen = True
            clause = match["data"].strip(" :,")
            clause = re.sub(rf"^(?:{_REFERENCE.pattern})\s*[:,]\s*", "", clause)
            if field == "grams":
                if clause in ("sending them together", "to send them", "sending them"):
                    clause = ""
                count = re.fullmatch(rf"{_DET}({_COUNT}) {_PARCEL}(?: at the depot)?", clause)
                if count:
                    declared, clause = _count(count[1]), ""
        if not clause or _REFERENCE.fullmatch(clause):
            continue
        bare = _PARCEL if field == "grams" else "lines"
        if match and re.fullmatch(rf"{_DET}{bare}", clause):
            continue
        # Several clauses can identify consecutive parcels by ordinal.
        ordinal = re.match(r"^the (first|second|third|other) (?:weighs|is) ", clause) if field == "grams" else None
        if ordinal:
            position = {"first": 0, "second": 1, "third": 2, "other": 1}[ordinal[1]]
            if position != len(values or []):
                return None
            parsed = _amounts(clause[ordinal.end():], field)
            if parsed is None or len(parsed) != 1:
                return None
            values = (values or []) + parsed
        else:
            parsed = _amounts(clause, field)
            if parsed is None or values is not None:
                return None
            values = parsed
    if not question_seen:
        return None
    if values is None:
        return None, ("grams for each parcel" if field == "grams" else "invoice line amounts in cents")
    if declared is not None and declared != len(values):
        return None
    return {field: values}, None


def answer(message, bank=None, runner=None, log=None, *, local_only=False):
    """Try a checked method; a deferred request continues through the ordinary hive."""
    from training.experiments.fieldwork.guest import Guest
    from training.experiments.fieldwork.work import check, contract_id, load_bank, shared_results
    if len(message) > 32_768:
        return None
    bank = bank if bank is not None else bank_path()
    registered = load_bank(bank)
    call = explicit_request(message)
    convention = None
    if call:
        task = call["task"].lower()
        bound = None
    else:
        for contract in (SHIPPING, INVOICE):
            if any((r["task"], r["description"]) == contract for r in registered):
                marker = _CONVENTION.search(message)
                label = marker[1].lower() if marker else None
                convention = _CONVENTIONS.get((contract, label))
                request = message[:marker.start()] if convention else message
                bound = _natural(request, contract)
                if bound is not None:
                    task = contract[0]
                    break
        else:
            return None

    contract_ref = call["contract"] if call else None
    groups = {}
    for row in registered:
        if row["task"] == task:
            cid = contract_id(row)
            if contract_ref is None or (re.fullmatch(r"[a-f0-9]{12,64}", contract_ref, re.I)
                                        and cid.startswith(contract_ref.lower())):
                groups.setdefault(cid, []).append(row)
    if not groups:
        if call and (call["saved"] or contract_ref is not None or "_" in task
                     or (call["data"] or "").lstrip().startswith(("{", "["))):
            if contract_ref is not None:
                matches = sorted({contract_id(row)[:12] for row in registered if row["task"] == task})
                reason = f"The saved contract {task}@{call['contract']} is unavailable."
                if matches:
                    reason += " Available contracts: " + ", ".join(f"{task}@{cid}" for cid in matches) + "."
            else:
                reason = f"There is no saved method named {task} in this bank."
            return dict(status="missing", task=task, methods=[], text=reason)
        return None
    if len(groups) > 1:
        choices = "\n".join(f"- {task}@{cid[:12]} — {rows[0]['description']}" for cid, rows in sorted(groups.items()))
        return dict(status="missing", task=task, methods=[], text=(
            f"I have several contracts named {task}. Choose one and run it with its JSON input.\n{choices}"))

    group = next(iter(groups.values()))
    versions = sorted({r["digest"]: r for r in group}.values(), key=lambda r: r["digest"])
    description = versions[0]["description"]
    digests = [r["digest"] for r in versions]
    if call:
        value, missing = _json_input(call["data"], versions, (task, description))
    else:
        value, missing = bound
        if not missing:
            value, missing = _json_input(json.dumps(value), versions, (task, description))
    if missing:
        return dict(status="missing", task=task, methods=digests,
                    text=f"To run {task}, please give me {missing}.")
    runner = runner or guest()
    reason = f"The saved method {task} needs the CPython WebAssembly runtime."
    setup = "Run python scripts/setup_fieldwork.py."
    if isinstance(runner, Guest):
        import wasmtime
        try:
            # Compilation is lazy and cached. An installed file may still be incomplete.
            _ = runner.runtime
        except (OSError, wasmtime.WasmtimeError):
            reason = f"The saved method {task} is unavailable because its WebAssembly runtime could not load python.wasm."
            setup = "Set HIVE_FIELDWORK_SDK to a fresh directory and run python scripts/setup_fieldwork.py."
            runner = None
    if runner is None:
        if call or local_only:
            return dict(status="missing", task=task, methods=digests, fallback_to_members=not bool(call),
                        text=reason + " " + setup)
        if log:
            log(reason)
        return None
    proof = None
    if convention:
        field, bills = convention
        witnesses = [{"input": {field: amounts}, "output": expected} for amounts, expected in bills]
        versions = [row for row in versions if check(runner, row["source"], witnesses, explain=False)[0] == len(witnesses)]
        digests = [row["digest"] for row in versions]
        if not versions:
            return dict(status="missing", task=task, methods=[], input=value,
                        text=f"No saved version passed the checks for {label} rounding.")
        proof = dict(convention=label, checks=witnesses)
    rows, conflict = shared_results(versions, runner, [dict(id="request", input=value)])
    shown = json.dumps(value, separators=(", ", ": "))
    if conflict and "different answers" in conflict:
        amounts = re.search(r"\((.*)\)\.$", conflict)
        return dict(status="ambiguous", task=task, methods=digests, input=value,
                    text=f"My {len(versions)} saved methods for {task} disagree on {shown}"
                         + (f". They give {amounts.group(1)}" if amounts else "")
                         + ". Please give a labeled example that distinguishes the rules.")
    if conflict:
        return dict(status="missing", task=task, methods=digests, input=value,
                    text=f"A saved method for {task} could not complete this input. {shown}")
    result = rows[0]["value"]
    method = ", ".join(digest[:12] for digest in digests)
    who = (f"the saved method {task} ({method}, passed {versions[0]['validation']} independent checks)"
           if len(versions) == 1 else f"{len(versions)} saved methods for {task}, which agree ({method})")
    text = (f"{json.dumps(result) if not isinstance(result, str) else result}\n\n"
            f"Worked out by {who}, on {shown}, with no model call.")
    out = dict(status="answered", task=task, methods=digests, input=value, value=result, text=text)
    if proof:
        sample = proof["checks"][0]
        out["convention_check"] = proof
        unit = "cent" if sample["output"] == 1 else "cents"
        out["text"] += f" I selected {label} rounding. On {json.dumps(sample['input'])}, it gives {sample['output']} {unit}."
    return out
