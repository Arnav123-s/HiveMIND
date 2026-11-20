"""Publish one explicitly named local JSON result with exact decimal accumulation."""
import argparse
import csv
from decimal import Context, Decimal, localcontext
import json
from pathlib import Path
import re

from .files import publish
from .native import select
from .qualification import qualify, signature
from .solver import Unsupported, evidence_text, load_csv, mentions, run_files, schema, variants, words


NAME = re.compile(r"[\w-]+\.json", re.I)


# Unit names in the source column are the available unit declaration. A bare
# "price" column provides no currency identity for an explicit USD or EUR request.
UNITS = {
    "usd": {"usd", "dollar", "dollars"},
    "eur": {"eur", "euro", "euros"},
    "cent": {"cent", "cents"},
    "day": {"day", "days"},
    "hour": {"hour", "hours", "hr", "hrs"},
    "minute": {"minute", "minutes", "min", "mins"},
    "second": {"second", "seconds", "sec", "secs"},
    "gram": {"gram", "grams", "g"},
    "kilogram": {"kilogram", "kilograms", "kg"},
}


def verify_measure(request, operations):
    text = words(evidence_text(request))
    for op in operations:
        if op["op"] != "sum":
            continue
        field = op["field"]
        if not any(mentions(text, alias) for alias in variants(field)):
            raise Unsupported("name the numeric column to sum")
        tokens = set(words(field).split())
        for names in UNITS.values():
            target = r"\b(?:in|as|expressed in) (?:" + "|".join(sorted(names)) + r")\b"
            if re.search(target, text) and not (tokens & names):
                raise Unsupported("the requested unit is absent from the numeric column name")


def checked_run(request, file, source, *, mode="rules", server=None, example=None):
    try:
        if re.search(r'[/\\][^\s\'"]*\.(?:json|csv|txt|md|py)\b', request, re.I):
            raise Unsupported("name a local result file without directories")
        quoted = re.findall(r'''["']([^"'\r\n]+\.(?:json|csv))["']''', request, re.I)
        if any(s != file and not NAME.fullmatch(s) for s in quoted):
            raise Unsupported("use one plain JSON filename for the result")
        rows = load_csv(source) if file.casefold().endswith(".csv") else json.loads(source)
        numeric, _ = schema(rows)
        # For exact addition, reserve all integer and fractional columns, plus the
        # maximum number of carry places for this many rows.
        places_left = places_right = 0
        for r in rows:
            for column in numeric:
                v = Decimal(str(r[column]))
                places_left = max(places_left, v.adjusted() + 1)
                places_right = max(places_right, -v.as_tuple().exponent)
        precision = max(28, places_left + places_right + len(str(len(rows))) + 1)
        if precision > 10000:
            raise Unsupported("result exceeds the supported exact-digit budget")
        native_code = None
        if mode == "native" and example is None:
            if not server:
                raise Unsupported("native planning requires a local server")
            native_code = select(server, request, sorted(rows[0]))["code"]
        with localcontext(Context(prec=precision)):
            if example is None:
                result = run_files(request, {file:source}, mode, native_code)
            else:
                if set(example) != {"rows", "answer"}:
                    raise Unsupported("worked example must contain rows and answer")
                # Use the seven already known pairs. This requires no new model selection.
                qualified = qualify(request, example["rows"], example["answer"], rows, "seen_library")
                if qualified["status"] != "answered":
                    raise Unsupported(qualified["reason"])
                for code in qualified["codes"]:
                    result = run_files(request, {file:source}, "native", code)
                    if result["status"] != "answered" or signature(result["value"]) != signature(qualified["value"]):
                        raise Unsupported("the target file does not preserve the qualified answer")
                    verify_measure(request, result["plan"])
                result["admitted_codes"] = qualified["codes"]
                result["worked_examples"] = 1
        if result["status"] == "answered":
            if not result["files"]:
                raise Unsupported("name the result explicitly, for example 'Save as totals.json.'")
            verify_measure(request, result["plan"])
        return result
    except (ValueError, OverflowError, TypeError, csv.Error) as error:
        return {"status":"abstained", "value":None, "reason":str(error), "files":{}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("request")
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--mode", choices=("learned","rules","flat","single","agree","native"), default="rules")
    parser.add_argument("--server")
    parser.add_argument("--example", type=Path, help="JSON with rows and answer for one separate worked example; uses the known plan library")
    args = parser.parse_args()
    try:
        example = json.loads(args.example.read_text()) if args.example else None
        result = checked_run(args.request, args.file.name, args.file.read_text(), mode=args.mode,
                             server=args.server, example=example)
        if result["status"] == "answered":
            result["published"] = publish(args.out_dir, result["files"])
    except (OSError, ValueError) as error:
        result = {"status":"abstained", "value":None, "reason":str(error), "files":{}}
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 0 if result["status"]=="answered" else 1


if __name__ == "__main__":
    raise SystemExit(main())
