"""Use public module calls to find disagreements within the request's declared input domain."""
import ast
from hashlib import sha256
from itertools import combinations, islice, permutations
import json
from pathlib import Path
import re

from . import deliverables, saved
from .literal_examples import module_examples


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def list_calls(task):
    """Generate whole-row permutations only when the request declares that argument order unrestricted."""
    example = re.search(r"\bfor these (?P<var>[a-z]+):\s*(\[.*\])\.?\s*$", task, re.S)
    if not example or len(example[2]) > 6000:
        return []
    arg = example["var"]
    if not re.search(rf"\blist of {arg} may be in any order\b", task, re.I):
        return []
    funcs = list(dict.fromkeys(re.findall(rf"\b([a-zA-Z][a-zA-Z0-9_]*)\({arg}\) returns\b", task)))
    if not 1 <= len(funcs) <= 4:
        return []
    try:
        rows = ast.literal_eval(example[2])
        if not isinstance(rows, list) or not 1 <= len(rows) <= 20 or json.loads(canonical(rows)) != rows:
            return []
    except (TypeError, ValueError, SyntaxError, RecursionError):
        return []
    variants = [rows, list(reversed(rows))]
    # Removal is valid only when the public contract permits a subset. Check one- and two-row reductions first.
    if re.search(rf"\bany nonempty subset of (?:these |the ){arg} is valid\b", task, re.I):
        for size in (1, 2):
            variants.extend(list(sub) for sub in islice(combinations(rows, size), 30))
    variants.extend(list(p) for p in islice(permutations(rows), 30))
    calls, recorded = [], set()
    for variant in variants:
        key = canonical(variant)
        if key in recorded:
            continue
        recorded.add(key)
        for func in funcs:
            calls.append((func, [variant]))
        if len(calls) + len(funcs) > 30:
            break
    return calls


class Probe:
    def __init__(self, task, name):
        self.name = name
        examples = module_examples(task, [name])
        # "Examples to pass" alone is insufficient to make a public lookup implementation correct.
        self.complete = bool(examples and
            re.search(r"(?im)^The complete required behavior is one run of the checks below, in order, on a fresh module\.[ \t]*$", task)
            and re.search(r"(?im)^Required checks:[ \t]*$", task))
        self.calls = [(fn, args) for fn, args, _ in examples] if examples else list_calls(task)
        self.expected = [canonical(expected) for _, _, expected in examples]
        self.runner = saved.guest() if self.calls else None

    def inspect(self, work, expected_hash):
        pending = {"checked": False, "observed": []}
        if not self.runner:
            return pending
        try:
            with deliverables.regular(Path(work) / self.name) as file:
                data = file.read(65537)
            if len(data) > 65536 or sha256(data).hexdigest() != expected_hash:
                return pending
            source = data.decode("utf-8")
            wrapper = ("module = {'__name__': 'checked_module'}\n"
                       f"exec({source!r}, module)\n"
                       "def solve(call):\n"
                       "    import json\n"
                       "    value = module[call[0]](*call[1])\n"
                       "    if json.loads(json.dumps(value, allow_nan=False)) != value: raise ValueError('non-JSON result')\n"
                       "    return value\n")
            outputs, _, _ = self.runner.run(wrapper, self.calls)
            if len(outputs) != len(self.calls):
                return pending
            observed = [canonical(row["value"]) if isinstance(row, dict) and "value" in row else None for row in outputs]
        except (OSError, UnicodeError, RuntimeError, ValueError, TypeError, RecursionError):
            return pending
        return {"checked": self.complete and observed == self.expected,
                "observed": [sha256(x.encode()).hexdigest() if x is not None else None for x in observed]}

    def witness(self, first, second):
        observations = zip(self.calls, first["observed"], second["observed"])
        differences = [(fn, args) for (fn, args), a, b in observations if a and b and a != b]
        if differences:
            def size(call):
                args = call[1]
                items = len(args[0]) if len(args) == 1 and isinstance(args[0], list) else len(args)
                return items, len(canonical(args))
            fn, args = min(differences, key=size)
            literal = f"{fn}({', '.join(map(repr, args))})"
            if len(literal) <= 700:
                return literal
        return None
