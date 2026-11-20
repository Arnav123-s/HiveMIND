"""Recover a duration module a hive worker already wrote; execute candidate code only in WASI."""
import ast
from hashlib import sha256
import re

# Only a fully specified request that matches this original benchmark contract is eligible.
SPEC = ("Write a Python module and save it as durations.py. It has two functions. "
        "1) to_seconds(s) returns the seconds of a duration written with the units h, m and s, any of "
        "them left out (to_seconds('1h30m15s') is 5415, to_seconds('45m') is 2700). "
        "2) to_text(n) writes a number of seconds that way, leaving out units that are zero "
        "(to_text(5415) is '1h30m15s', to_text(3600) is '1h', to_text(0) is '0s'). "
        "Test both yourself before you finish. Then tell me, each on its own line, the value of ")
REQUEST = re.compile(re.escape(SPEC) + r"to_seconds\('((?:\d{1,8}[hms]){1,3})'\) and of to_text\((\d{1,10})\)\.")
INPUT = re.compile(r'(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?')
DISPATCH = "\n\ndef solve(call):\n    return {'to_seconds': to_seconds, 'to_text': to_text}[call[0]](call[1])\n"


def format_duration(n):
    hours, remainder = divmod(n, 3600)
    minutes, seconds = divmod(remainder, 60)
    return ''.join(f'{v}{u}' for v, u in zip((hours, minutes, seconds), 'hms') if v) or '0s'


def seconds(text):
    m = INPUT.fullmatch(text)
    if not m or not text:
        raise ValueError('unsupported duration')
    return sum(int(v or 0)*unit for v, unit in zip(m.groups(), (3600, 60, 1)))


def contract_cases():
    values = (0, 1, 17, 59, 60, 61, 3599, 3600, 3601, 3659, 3660, 3661, 7199,
              7213, 86399, 86400, 86461, 115389, 666666)
    # The module promises integer durations without a word-size limit. Exercise both sides
    # of fixed-width boundaries. These probes were added after the first independent grade.
    values += tuple(2**bits + delta for bits in (8, 16, 32, 64, 128) for delta in (-1, 1))
    return [(name, arg, expected) for n in values for name, arg, expected in
            [('to_seconds', format_duration(n), n), ('to_text', n, format_duration(n))]]


def extract(program):
    """Keep the two declarations and ordinary re imports, discarding the worker's driver."""
    try:
        statements = ast.parse(program).body
    except (ValueError, SyntaxError):
        return None
    functions = {}
    imports = []
    for node in statements:
        if isinstance(node, ast.Import) and all(alias.name == 're' for alias in node.names):
            imports.append(node)
        if isinstance(node, ast.FunctionDef) and node.name in ('to_seconds', 'to_text'):
            if node.decorator_list or node.name in functions:
                return None
            functions[node.name] = node
    if set(functions) != {'to_text', 'to_seconds'}:
        return None
    return '\n\n'.join(ast.get_source_segment(program, n) for n in [*imports, *functions.values()]) + '\n'


def execute(guest, source, inputs):
    rows, fuel, elapsed = guest.run(source + DISPATCH, inputs)
    return [r.get('value') for r in rows], fuel, elapsed


def recover(task, declined, programs, guest, out):
    match = REQUEST.fullmatch(task.strip())
    if not declined or not match or not INPUT.fullmatch(match[1]):
        return None
    checks = contract_cases()
    asked = [('to_seconds', match[1]), ('to_text', int(match[2]))]
    expected = [row[2] for row in checks] + [seconds(match[1]), format_duration(int(match[2]))]
    seen, qualified, trials = set(), [], []
    for name, program in programs:
        source = extract(program)
        if source is None:
            continue
        digest = sha256(source.encode()).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        answers, fuel, elapsed = execute(guest, source, [r[:2] for r in checks]+asked)
        passed = all(type(x) is type(y) and x == y for x,y in zip(answers, expected, strict=True))
        trials.append(dict(program=name, sha256=digest, passed=passed, fuel=fuel, seconds=round(elapsed, 4)))
        if passed:
            qualified.append((name, source, answers[-2:]))
    if not qualified:
        return dict(delivered=False, trials=trials)
    name, source, answers = qualified[0]
    out.mkdir(parents=True, exist_ok=True)
    (out/'durations.py').write_text(source)
    (out/'REPORT.md').write_text('\n'.join(map(str, answers))+'\n')
    return dict(delivered=True, selected=name, sha256=sha256(source.encode()).hexdigest(), answers=answers, trials=trials)
