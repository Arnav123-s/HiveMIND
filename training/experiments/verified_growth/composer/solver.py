"""Choose and execute a typed plan from an English request and a plain data table."""
from decimal import Decimal
import argparse
import csv
import io
import json
import math
from pathlib import Path
import re

from training.experiments.atlas.proposer.study import evaluate as evaluate_atlas
from .learner import models


class Unsupported(ValueError):
    pass


AGG_WORDS = r"\b(?:count|counts|number|how many|tally|sum|sums|total|totals|add|combined|how much|most|least|fewest|highest|greatest|largest|lowest|smallest|maximum|minimum|per|each|every|group|often|frequent\w*|breakdown|break down)\b"
OUTSIDE = (r"\b(?:average|mean|median|distinct|unique|percent\w*|ratio|except|excluding|exclude|"
           r"ignore|instead of|business day|last month|year.to.date|yesterday|before|after|"
           r"duplicate\w*|sort(?:ed)? list|second|top\s+\d+|bottom\s+\d+|at least|at most|"
           r"more than|fewer than|greater than|less than|exactly once|not equal|not from|not in|"
           r"not at|more recent|latest|earliest|order by date)\b|[<>]")
LOW = r"\b(?:fewest|least|lowest|smallest|minimum|minimal)\b"
HIGH = r"\b(?:most|highest|greatest|largest|maximum|busiest|leading|winner|winning|top)\b"
GROUP = r"\b(?:each|every|group(?:ed)?|breakdown|break down|per|by|mapping|separately)\b"
SUM = r"\b(?:sum|sums|combined|amount|weight|revenue|units|quantity|quantities|add(?:ed)?|cost|hours|total(?:s)?)\b"
RECORD_COUNT = r"\b(?:number|count|counts|tally|total|how many) (?:of )?(?:matching )?(?:rows|records|entries|observations|visits|calls|deliveries|transactions)\b"


def words(value):
    return " ".join(re.findall(r"[\w]+", str(value).casefold().replace("_", " ")))


def variants(name):
    name = words(name)
    simple = {name, name.split()[-1]}
    result = set(simple)
    for token in simple:
        if token.endswith("y"):
            result.add(token[:-1] + "ies")
        if token.endswith("ies"):
            result.add(token[:-3] + "y")
        if token.endswith("s"):
            result.add(token[:-1])
        else:
            result.add(token + "s")
    return sorted(result, key=len, reverse=True)


def mentions(text, value):
    return bool(re.search(r"(?<!\w)" + re.escape(value) + r"(?!\w)", text))


def schema(rows):
    if not isinstance(rows, list) or not rows or len(rows) > 100000:
        raise Unsupported("a nonempty table with a known schema is needed")
    if not isinstance(rows[0], dict):
        raise Unsupported("expected rows with named columns")
    headers = list(rows[0])
    if not headers or len(headers) > 100 or any(not isinstance(k, str) or not words(k) for k in headers):
        raise Unsupported("invalid header")
    if len({words(c) for c in headers}) != len(headers):
        raise Unsupported("ambiguous header")
    if any(not isinstance(r, dict) or r.keys() != rows[0].keys() for r in rows):
        raise Unsupported("rows disagree on the schema")
    for row in rows:
        for v in row.values():
            if type(v) not in (str, int, float) or (type(v) is float and not math.isfinite(v)):
                raise Unsupported("only finite numbers and text fields are supported")
    numeric = [k for k in headers if all(type(r[k]) in (float, int) for r in rows)]
    categories = [k for k in headers if k not in numeric and all(isinstance(r[k], str) for r in rows)]
    if set(headers) != set(categories + numeric):
        raise Unsupported("mixed field types")
    return numeric, categories


def evidence_text(request):
    s = re.sub(r"\b[\w.-]+\.(?:csv|json)\b", " ", request.casefold())
    # A tie instruction changes the final selector, not the quantity being aggregated.
    return re.split(r"\b(?:in (?:case|the event) of (?:a )?tie|break ties|if (?:there is )?(?:a |two )?tie|"
                    r"ties? (?:are |should |go |use |by |break)|tie.break)", s, maxsplit=1)[0]


def keyword_code(text, numeric):
    stage = ("L" if re.search(LOW, text) else "H" if re.search(HIGH, text) else
             "G" if re.search(GROUP, text) and not re.search(r"\bby (?:adding|counting|summing)\b", text) else "P")
    explicit_sum = (bool(re.search(SUM, text)) or
                    any(mentions(text, v) for name in numeric for v in variants(name)))
    count = bool(re.search(RECORD_COUNT, text)) or not explicit_sum
    return ("C" if count else "S") + stage


def bind_filters(text, categories, rows):
    filters = {}
    folded = words(text)
    possibilities = {}
    for key in categories:
        for value in {r[key] for r in rows}:
            token = words(value)
            if not token or token in {"a", "an", "the", "by", "to", "in", "of", "as", "on", "or", "is", "per"}:
                continue
            if mentions(folded, token):
                possibilities.setdefault(token, []).append((key, value))
    for token, found in possibilities.items():
        if any(token == v for key in categories for v in variants(key)):
            continue
        exact = [(k, v) for k, v in found if re.search(
            r"\b(?:" + "|".join(map(re.escape, variants(k))) + r") (?:is |equals |equal to )?" + re.escape(token) + r"\b", folded)]
        matches = exact or found
        if len(matches) != 1:
            raise Unsupported("a mentioned category value is ambiguous")
        key, value = matches[0]
        if key in filters:
            raise Unsupported("multiple values for one filter")
        filters[key] = value
    # Explicit equality can name an absent value. Do not silently drop such conditions.
    for key in categories:
        names = "|".join(map(re.escape, variants(key)))
        m = re.search(r"\b(?:" + names + r")\s*(?:=|equals\b|is equal to\b|is\b)\s*"
                      r"(?:['\"]([^'\"]+)['\"]|([\w-]+))", text)
        if m and key not in filters:
            filters[key] = m[1] or m[2]
    if not filters and re.search(r"\b(?:only (?:at|from|for|rows|records)|where|restricted to|filter(?:ed)? to)\b", text):
        raise Unsupported("could not ground a requested restriction")
    return filters


def group_column(text, categories, filters):
    priority = []
    for key in categories:
        names = "|".join(map(re.escape, variants(key)))
        if re.search(r"\b(?:for each|for every|each|every|per|group by|grouped by|by|which|what|"
                     r"name the|return the|find the)\s+(?:" + names + r")\b", text):
            priority.append(key)
    if len(priority) == 1:
        return priority[0]
    named = [k for k in categories if k not in filters and any(mentions(text, v) for v in variants(k))]
    possible = priority or named or [k for k in categories if k not in filters]
    if len(possible) != 1:
        raise Unsupported("the grouping field is ambiguous")
    return possible[0]


def plan(request, rows, mode, native_code=None):
    if not isinstance(request, str) or not 1 <= len(request.strip()) <= 4000:
        raise Unsupported("expected a short table request")
    numeric, categories = schema(rows)
    text = evidence_text(request)
    if (not re.search(AGG_WORDS, text) or re.search(OUTSIDE, text) or
        re.search(r"\b(?:or|versus|both the sum and|and the (?:sum|average))\b", text)):
        raise Unsupported("no supported single aggregation")
    if re.search(r"\b(?:return|output|save|write).{0,50}\b(?:csv|list of|all tied|all winners|markdown|top and bottom)\b",
                 re.sub(r"[\w.-]+\.csv\b", "", text)):
        raise Unsupported("unsupported output contract")
    filters = bind_filters(text, categories, rows)
    if mode == "native":
        code = native_code
    elif mode in ("rules", "single"):
        code = keyword_code(text, numeric)
    elif mode in ("learned", "flat", "agree"):
        agg, terminal, flat = models()
        code = flat.predict(text) if mode == "flat" else agg.predict(text) + terminal.predict(text)
        if mode == "agree" and code != keyword_code(text, numeric):
            raise Unsupported("the learned and rule selectors disagree")
    else:
        raise ValueError("unknown selector")
    if code not in ("CP", "CG", "CH", "CL", "SP", "SG", "SH", "SL"):
        raise Unsupported("planner did not select a valid typed path")
    ops = [{"op": "filter", "field": key, "equals": value} for key, value in filters.items()]
    field = None
    if code[0] == "S":
        named = [key for key in numeric if any(mentions(text, v) for v in variants(key))]
        if len(named or numeric) != 1:
            raise Unsupported("the numeric field is ambiguous")
        field = (named or numeric)[0]
    group = None if code[1] == "P" else group_column(words(text), categories, filters)
    ops.append({"op": "count" if code[0] == "C" else "sum", "field": field, "group": group})
    if code[1] in ("L", "H"):
        full = request.casefold()
        reverse = bool(re.search(r"(?:lexicograph\w*|alphabet\w*)[ -]+last|reverse alphabetical", full))
        specified = bool(re.search(r"lexic|alphabet|dictionary order|smallest name", full))
        ops.append({"op": "highest" if code[1] == "H" else "lowest",
                    "tie": ("last" if reverse else "first") if specified else None,
                    "empty_null": "null" in full or "none" in full})
    if mode == "single" and (len(ops) > 1 or group is not None):
        raise Unsupported("one ungrouped primitive only")
    return code, ops


def checked_number(value):
    if isinstance(value, Decimal) and value == value.to_integral_value():
        return int(value)
    if isinstance(value, Decimal):
        result = float(value)
        if not math.isfinite(result) or Decimal(str(result)) != value:
            raise Unsupported("result cannot be returned as an exact JSON number")
        return result
    return value


def execute(rows, ops):
    current = rows
    for op in ops:
        if op["op"] == "filter":
            current = [r for r in current if r[op["field"]] == op["equals"]]
        elif op["op"] in ("sum", "count"):
            key = op["group"]
            if key is None and op["op"] == "count":
                current = len(current)
                continue
            values = [{"qty": (1 if op["op"] == "count" else Decimal(str(r[op["field"]]))),
                       "label": r[key] if key else ""} for r in current]
            # Reuse the previously tested group-sum primitive on actual grounded row fields.
            totals = evaluate_atlas(("sum",), {"events": values})
            current = totals if key else totals.get("", 0)
        else:
            if not isinstance(current, dict):
                raise Unsupported("extremum requires grouped totals")
            if not current:
                if op["empty_null"]:
                    return None
                raise Unsupported("no observed groups to rank")
            target = (max if op["op"] == "highest" else min)(current.values())
            tied = sorted(k for k,v in current.items() if v == target)
            if len(tied) > 1 and not op["tie"]:
                raise Unsupported("tied groups have no stated tie rule")
            current = tied[-1] if op["tie"] == "last" else tied[0]
    return {k:checked_number(v) for k,v in current.items()} if isinstance(current, dict) else checked_number(current)


def solve(request, rows, mode="learned", native_code=None):
    try:
        code, ops = plan(request, rows, mode, native_code)
        return {"status": "answered", "code": code, "plan": ops, "value": execute(rows, ops)}
    except Unsupported as exc:
        return {"status": "abstained", "reason": str(exc), "value": None}


def load_csv(text):
    reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
    if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise Unsupported("missing or duplicate CSV headers")
    rows = list(reader)
    if any(None in row or None in row.values() for row in rows):
        raise Unsupported("ragged CSV row")
    for k in reader.fieldnames:
        values = [row[k] for row in rows]
        numeric = r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?"
        if values and all(re.fullmatch(numeric, s) for s in values):
            for row, s in zip(rows, values, strict=True):
                value = float(s) if "." in s else int(s)
                if not math.isfinite(value) or Decimal(str(value)) != Decimal(s):
                    raise Unsupported("CSV number exceeds exact representation")
                row[k] = value
    return rows


def run_files(request, files, mode="learned", native_code=None):
    try:
        if len(files) != 1:
            raise Unsupported("provide one flat CSV or JSON table")
        file, contents = next(iter(files.items()))
        if file.casefold().endswith(".csv"):
            rows = load_csv(contents)
        elif file.casefold().endswith(".json"):
            rows = json.loads(contents)
        else:
            raise Unsupported("unsupported input file")
        candidates = re.findall(r"(?<![\w./-])([\w-]+\.(?:json|csv|md|txt|py))\b", request, re.I)
        products = {s for s in candidates if s != file}
        if len(products) > 1 or any(not name.lower().endswith(".json") for name in products):
            raise Unsupported("only a single JSON output file is supported")
        result = solve(request, rows, mode, native_code)
        result["files"] = {}
        if result["status"] == "answered":
            result["text"] = json.dumps(result["value"], allow_nan=False, ensure_ascii=False)
            result["files"] = {s:result["text"]+"\n" for s in products}
        return result
    except (Unsupported, ValueError, csv.Error, TypeError, OverflowError) as exc:
        return {"status":"abstained","value":None,"reason":str(exc),"files":{}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("request")
    parser.add_argument("--mode", choices=("learned","flat","rules","single","agree","native"), default="learned")
    parser.add_argument("--server", help="local t80 server URL for the native selector")
    args = parser.parse_args()
    source = args.file.read_text()
    code = None
    if args.mode == "native":
        from .native import select
        if not args.server:
            parser.error("native mode requires --server")
        rows = load_csv(source) if args.file.suffix.casefold()==".csv" else json.loads(source)
        code = select(args.server, args.request, sorted(rows[0]) if rows else [])["code"]
    result = run_files(args.request, {args.file.name:source}, args.mode, code)
    print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    return 0 if result["status"]=="answered" else 1


if __name__ == "__main__":
    raise SystemExit(main())
