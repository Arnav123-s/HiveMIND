"""List the local checked methods and collect input for one exact saved contract."""

import argparse
import json
import re
import sys

from training.experiments.fieldwork.work import contract_id, load_bank

from . import saved, skill_inputs


def _read(prompt):
    print(prompt, end=" ", file=sys.stderr, flush=True)
    line = sys.stdin.readline(32_769)
    if not line:
        raise EOFError("Input ended before the method had all its fields.")
    if len(line) > 32_768:
        raise ValueError("Input exceeds 32,768 characters.")
    return line.rstrip("\r\n")


def _entry(label, kind, *, optional=False):
    hints = {"array": "whole numbers separated by commas, or [] for none", "integer": "whole number",
             "string": "text"}
    hint = hints[kind] + (", blank to omit" if optional else "")
    raw = _read(f"{label} ({hint}):")
    if optional and not raw:
        return None
    if kind == "string":
        return raw
    if kind == "array" and raw.strip() == "[]":
        return []
    numbers = [v.strip() for v in raw.split(",")] if kind == "array" else [raw.strip()]
    if not all(re.fullmatch(r"[+-]?[0-9]+", value) for value in numbers):
        raise ValueError(f"{label} needs {hints[kind]}.")
    parsed = [int(v) for v in numbers]
    return parsed if kind == "array" else parsed[0]


def _kind(kinds, items):
    if kinds == ["array"] and items == ["integer"]:
        return "array"
    if kinds in (["integer"], ["string"]):
        return kinds[0]
    return None


def _payload(rows):
    shape = rows[0].get("input_contract")
    if shape and skill_inputs.valid(shape) and all(r.get("input_contract") == shape for r in rows):
        if shape["kinds"] == ["object"] and shape["properties"]:
            items = shape.get("property_items", {})
            fields = {k: _kind(shape["properties"][k], items.get(k)) for k in sorted(shape["properties"])}
            if all(fields.values()):
                value = {}
                for key, kind in fields.items():
                    label = key.replace("_", " ").capitalize()
                    answer = _entry(label, kind, optional=key not in shape["required"])
                    if answer is not None:
                        value[key] = answer
                return json.dumps(value, separators=(",", ":"))
        kind = _kind(shape["kinds"], shape.get("items"))
        if kind:
            return json.dumps(_entry("Input", kind), separators=(",", ":"))
    # Preserve raw JSON, including duplicate keys, for the saved method's strict parser.
    return _read("Input as JSON:")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="hive skills", description=__doc__)
    parser.add_argument("method", nargs="?", help="method name, optionally followed by @ and its contract ID")
    requested = parser.parse_args(argv).method
    bank = saved.bank_path()
    if bank is None:
        print("The saved-method bank is disabled by HIVE_BANK.", file=sys.stderr)
        return int(requested is not None)
    groups = {}
    for row in load_bank(bank):
        groups.setdefault((row["task"], contract_id(row)), []).append(row)
    choices = sorted(groups)
    if not choices:
        print(f"No checked methods in {bank}.")
        return int(requested is not None)
    try:
        if requested is None:
            for i, (name, digest) in enumerate(choices, 1):
                print(f"{i}. {name}@{digest[:12]} — {groups[name, digest][0]['description']}")
            if not (sys.stdin.isatty() and sys.stdout.isatty()):
                return 0
            number = _read("Choose a method by number (Enter to leave):").strip()
            if not number:
                return 0
            if not number.isascii() or not number.isdigit() or not 1 <= int(number) <= len(choices):
                raise ValueError("Choose a number from the list.")
            selected = choices[int(number) - 1]
        else:
            name, marker, prefix = requested.lower().partition("@")
            matches = [key for key in choices if key[0] == name and
                       (not marker or (re.fullmatch(r"[0-9a-f]{12,64}", prefix) and key[1].startswith(prefix)))]
            if len(matches) != 1:
                options = ", ".join(f"{n}@{d[:12]}" for n, d in choices if n == name)
                raise ValueError(f"Choose a checked contract from {options}." if options else
                                 f"No saved method named {requested}. Run './hive skills' to see the list.")
            selected = matches[0]
            print(groups[selected][0]["description"], file=sys.stderr)
        raw = _payload(groups[selected])
        result = saved.answer(f"Run the saved method {selected[0]}@{selected[1]} with {raw}", bank=bank)
        if result is None:
            raise ValueError("The saved method could not accept the input. Check its size and contract.")
        print(result["text"])
        return int(result["status"] != "answered")
    except KeyboardInterrupt:
        print(file=sys.stderr)
        return 130
    except (EOFError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1
