"""Describe the JSON shapes observed in a method's public examples."""


def _kind(value):
    return {dict: "object", list: "array", bool: "boolean", int: "integer",
            float: "number", str: "string", type(None): "null"}[type(value)]


def infer_contract(inputs):
    """Keep types and field names. Values from the examples need not be retained."""
    kinds = set()
    fields = {}
    required = None
    items = set()
    field_items = {}
    for value in inputs:
        kinds.add(_kind(value))
        if isinstance(value, list):
            items.update(_kind(item) for item in value)
        if isinstance(value, dict):
            required = set(value) if required is None else required.intersection(value)
            for key, entry in value.items():
                fields.setdefault(key, set()).add(_kind(entry))
                if isinstance(entry, list):
                    field_items.setdefault(key, set()).update(_kind(item) for item in entry)
    contract = dict(kinds=sorted(kinds), required=sorted(required or ()),
                    properties={k: sorted(v) for k, v in sorted(fields.items())})
    if "array" in kinds:
        contract["items"] = sorted(items)
    if field_items:
        contract["property_items"] = {k: sorted(v) for k, v in sorted(field_items.items())}
    return contract


def _accepts_kind(value, kinds):
    kind = _kind(value)
    return kind in kinds or (kind == "integer" and "number" in kinds)


def accepts(value, contract):
    """Stay within the observed top-level types and object fields when serving in chat."""
    if not _accepts_kind(value, contract["kinds"]):
        return False
    if isinstance(value, list) and "items" in contract:
        return all(_accepts_kind(item, contract["items"]) for item in value)
    if not isinstance(value, dict):
        return True
    fields = contract["properties"]
    items = contract.get("property_items", {})
    return (set(contract["required"]) <= set(value) <= set(fields)
            and all(_accepts_kind(entry, fields[key]) for key, entry in value.items())
            and all(all(_accepts_kind(item, items[key]) for item in entry) for key, entry in value.items()
                    if isinstance(entry, list) and key in items))


def valid(contract):
    """An unreadable saved shape must not turn into a permissive legacy contract."""
    kinds = {"object", "array", "number", "integer", "boolean", "string", "null"}

    def known(values):
        return isinstance(values, list) and all(isinstance(v, str) and v in kinds for v in values)

    if not isinstance(contract, dict) or not known(contract.get("kinds")):
        return False
    fields, required = contract.get("properties"), contract.get("required")
    items = contract.get("property_items", {})
    return (isinstance(fields, dict) and all(known(v) for v in fields.values())
            and isinstance(required, list) and all(isinstance(k, str) and k in fields for k in required)
            and ("items" not in contract or known(contract["items"]))
            and isinstance(items, dict) and all(k in fields and known(v) for k, v in items.items()))
