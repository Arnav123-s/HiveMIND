"""Recover a single pure Python module from worker attempts using the user's own examples."""
import ast
from hashlib import sha256
import json
import re


FILE = re.compile(r"(?<![\w./-])([A-Za-z_][A-Za-z_0-9]{0,60}\.py)\b", re.I)
IDENT = r"[A-Za-z_][A-Za-z_0-9]*"
# Literal arguments intentionally exclude nested calls and free variables.
CALL = re.compile(rf"(?<![.\w])({IDENT})\(([^()\n]{{0,160}})\)")
RELATION = re.compile(r"^\s*`?\s*(?:==|=>|->|returns?\b|is\b|gives?\b)\s*`?\s*", re.I)
VALUE = re.compile(r"""(?:'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*"|\[[^\]\n]{0,150}\]|\{[^}\n]{0,150}\}|-?\d+(?:\.\d+)?|True|False|None)(?![\w.](?=\w))""")
REPORT = re.compile(r"\b(?:then\s+)?(?:tell me|report|print|give me)\s+(?:each on its own line,?\s*|,\s*)?(?:the\s+)?(?:values?|results?|outputs?)\s+(?:of|for)\s+", re.I)
DECLINE = re.compile(r"^(?:not confirmed\b|no member got as far as an answer\b|could not (?:confirm|deliver)\b|unable to (?:confirm|deliver)\b)", re.I)
SAFE_IMPORTS = {"bisect","collections","decimal","fractions","functools","heapq","itertools","math","operator","re","statistics","string","typing"}


def call_args(match):
    try:
        expression = ast.parse(match.group(), mode="eval").body
        if expression.keywords:
            return None
        args = [ast.literal_eval(arg) for arg in expression.args]
        if json.loads(json.dumps(args, allow_nan=False)) != args:
            return None
        return match[1], args
    except (ValueError, SyntaxError, TypeError, RecursionError):
        return None


def contract(text):
    if not isinstance(text, str) or len(text) > 12000:
        return None
    filenames = set(FILE.findall(text))
    if len(filenames) != 1 or re.search(r"\b(?:class|classes|write a test file)\b", text, re.I):
        return None
    tail = REPORT.search(text)
    instruction = text[:tail.start()] if tail else text
    calls = list(CALL.finditer(instruction))
    expected = []
    for call in calls:
        relation = RELATION.match(instruction[call.end():])
        if not relation or not (args := call_args(call)):
            continue
        value = VALUE.match(instruction[call.end() + relation.end():])
        if value:
            try:
                expected.append((args, ast.literal_eval(value.group())))
            except (ValueError, SyntaxError):
                return None
    names = {call[0] for call, _ in expected}
    # A named function with only a signature still needs a public check before shipping.
    declared = {match[1] for match in calls}
    if names != declared or len({json.dumps(case) for case, _ in expected}) < 2:
        return None
    queries = []
    if tail:
        last = text[tail.end():].strip()
        for call in CALL.finditer(last):
            query = call_args(call)
            if query is None or query[0] not in names:
                return None
            queries.append(query)
        remainder = CALL.sub("", last)
        if not queries or re.sub(r"\b(?:and|of)\b|[ ,.`\s]", "", remainder):
            return None
    elif re.search(r"\b(?:then tell me|also (?:print|save|provide)|each on its own line)\b", text, re.I):
        return None
    return filenames.pop(), names, expected, queries


def module_source(raw, names):
    if not isinstance(raw, str) or len(raw) > 48000:
        return None
    try:
        statements = ast.parse(raw).body
    except (ValueError, SyntaxError, RecursionError):
        return None
    nodes, functions = [], set()
    for stmt in statements:
        if isinstance(stmt, ast.FunctionDef):
            if stmt.name in functions or stmt.decorator_list or stmt.name == "_hive_call":
                return None
            functions.add(stmt.name)
        elif isinstance(stmt, ast.Import):
            if not all(alias.name in SAFE_IMPORTS for alias in stmt.names):
                continue
        elif isinstance(stmt, ast.ImportFrom):
            if stmt.level or stmt.module not in SAFE_IMPORTS or any(x.name == "*" for x in stmt.names):
                continue
        elif isinstance(stmt, ast.Assign) and all(isinstance(x, ast.Name) for x in stmt.targets):
            try:
                ast.literal_eval(stmt.value)
            except (ValueError, TypeError, RecursionError):
                continue
        else:
            continue
        nodes.append(ast.get_source_segment(raw, stmt))
    return "\n\n".join(nodes) + "\n" if names <= functions else None


def propose(request, files, programs, visible_report, *, guest=None):
    skip = {"status": "abstained", "files": {}, "text": ""}
    if files or not isinstance(visible_report, str) or not (not visible_report.strip() or DECLINE.match(visible_report.strip())):
        return skip
    spec = contract(request)
    if not spec:
        return skip
    filename, names, cases, queries = spec
    if guest is None:
        from team.config import fieldwork_sdk_path
        from training.experiments.fieldwork.guest import Guest
        guest = Guest(fieldwork_sdk_path())
    dispatcher = "\n\ndef _hive_call(x):\n    return {" + ", ".join(f"{k!r}: {k}" for k in sorted(names)) + "}[x[0]](*x[1])\nsolve = _hive_call\n"
    qualified, seen = [], set()
    for _, raw in programs:
        src = module_source(raw, names)
        if src is None or src in seen:
            continue
        seen.add(src)
        if len(seen) > 16:
            return skip
        rows, _, _ = guest.run(src + dispatcher, [c for c, _ in cases] + queries)
        if len(rows) != len(cases) + len(queries) or any("value" not in x for x in rows):
            continue
        if not all(type(row["value"]) is type(key) and row["value"] == key for row, (_, key) in zip(rows, cases)):
            continue
        qualified.append((src, [row["value"] for row in rows[len(cases):]]))
    if not qualified or len({json.dumps(values, sort_keys=True) for _, values in qualified}) != 1:
        return skip
    src, values = qualified[0]
    return {"status": "answered", "files": {filename: src}, "text": "\n".join(map(str, values)) or f"Saved {filename}.",
            "module_sha256": sha256(src.encode()).hexdigest(), "public_checks": len(cases)}
