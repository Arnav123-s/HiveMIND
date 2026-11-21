"""Read explicitly requested public tests as literal data."""
import ast
import json
import re


BLOCK = re.compile(r"(?im)^(?:acceptance tests|required checks|examples to pass):[ \t]*\r?\n```python[ \t]*\r?\n(.*?)^```[ \t]*\r?$", re.S)
def module_examples(task, names):
    """An explicitly labelled test block for a single requested Python file. No evaluation of prompt code."""
    if len(names) != 1 or not names[0].endswith(".py"):
        return ()
    blocks = BLOCK.findall(task)
    if len(blocks) != 1 or len(blocks[0]) > 3000:
        return ()
    try:
        checks = ast.parse(blocks[0]).body
        if not 1 <= len(checks) <= 12:
            return ()
        result = []
        for check in checks:
            if not isinstance(check, ast.Assert) or check.msg is not None:
                return ()
            test = check.test
            if not isinstance(test, ast.Compare) or len(test.ops) != 1 or not isinstance(test.ops[0], ast.Eq):
                return ()
            call = test.left
            if (not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name) or call.keywords
                    or call.func.id.startswith("_") or len(call.args) > 8):
                return ()
            args = [ast.literal_eval(arg) for arg in call.args]
            want = ast.literal_eval(test.comparators[0])
            # Require lossless JSON arguments/results so a tuple or integer-keyed mapping never changes type.
            if json.loads(json.dumps([args, want], allow_nan=False)) != [args, want]:
                return ()
            result.append((call.func.id, args, want))
        return tuple(result)
    except (SyntaxError, TypeError, ValueError, OverflowError, RecursionError):
        return ()
