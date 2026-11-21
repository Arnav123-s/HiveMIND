"""Literal user-provided module checks. Their agreement never certifies a candidate."""
import ast
import re
from pathlib import Path

from . import deliverables, saved
from .literal_examples import module_examples


INSPECT = ("Inspect the supplied input first (use look(data) if its shape is unclear). Before DONE, run "
           "assertions for the prompt's stated example and a boundary it defines. Use only checks with a "
           "known expected result. Print the requested answer without diagnostic output.")


def _portable(source):
    """Only compare functions whose runtime inputs come from arguments or literal module data."""
    try:
        tree = ast.parse(source)
    except (ValueError, SyntaxError, RecursionError):
        return False
    builtins = {"abs", "all", "any", "bool", "dict", "divmod", "enumerate", "float", "int", "len",
                "list", "max", "min", "range", "reversed", "round", "sorted", "str", "sum", "tuple", "zip"}
    methods = {"append", "clear", "copy", "count", "extend", "get", "index", "insert", "items",
               "join", "keys", "lower", "pop", "replace", "reverse", "sort", "split", "strip", "upper", "values"}
    functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    local = {node.arg for node in ast.walk(tree) if isinstance(node, ast.arg)}
    local.update(node.id for node in ast.walk(tree) if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store))
    if any(not isinstance(node, (ast.FunctionDef, ast.Assign, ast.Expr)) for node in tree.body):
        return False
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.ClassDef, ast.Global, ast.Nonlocal,
                             ast.AsyncFunctionDef, ast.Lambda, ast.Set, ast.SetComp)):
            return False
        if isinstance(node, ast.Name) and (node.id.startswith("__") or node.id not in local | builtins | functions):
            return False
        if isinstance(node, ast.Attribute) and node.attr not in methods:
            return False
        if isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Name) and fn.id in builtins | functions:
                continue
            if not isinstance(fn, ast.Attribute) or fn.attr not in methods:
                return False
    return bool(functions)


class ModuleChecks:
    def __init__(self, name, examples):
        self.name = name
        self.examples = examples
        self.runner = saved.guest()
        self.previous = None
        self.feedback = ""

    def issue(self, work):
        if self.runner is None:
            return ""
        try:
            with deliverables.regular(Path(work) / self.name) as f:
                raw = f.read(65537)
            if len(raw) > 65536:
                return ""
            if raw == self.previous:
                return self.feedback
            source = raw.decode("utf-8")
            if not _portable(source):
                return ""
            # The guest cannot read the task workspace or the expected observations.
            wrapper = ("_module = {'__name__': 'hive_public_module'}\n"
                       f"exec({source!r}, _module)\n"
                       "def solve(sample):\n"
                       "    fn = _module[sample[0]]\n"
                       "    try:\n        value = fn(*sample[1])\n"
                       "    except (ValueError, TypeError, IndexError, KeyError, ZeroDivisionError) as error:\n"
                       "        return {'raised': type(error).__name__}\n"
                       "    import json\n"
                       "    if json.loads(json.dumps(value, allow_nan=False)) != value: return {}\n"
                       "    return {'result': value}\n")
            outputs, _, _ = self.runner.run(wrapper, [[name, args] for name, args, _ in self.examples])
        except (OSError, ValueError, RuntimeError, UnicodeError, RecursionError):
            return ""
        except Exception as exc:
            # Wasmtime can also fail while opening the optional SDK, before the guest receives any input.
            if type(exc).__module__.startswith("wasmtime."):
                return ""
            raise
        self.previous, self.feedback = raw, ""
        for (name, args, want), row in zip(self.examples, outputs):
            observed = row.get("value")
            if not isinstance(observed, dict):
                continue  # Missing runtime dependencies and unsupported modules give no contrary evidence.
            if "raised" in observed or ("result" in observed and observed["result"] != want):
                got = "raised " + observed["raised"] if "raised" in observed else "returned " + repr(observed["result"])[:120]
                args_text = ", ".join(map(repr, args))[:300]
                self.feedback = f"The supplied test {name}({args_text}) expected {want!r}. The saved module {got}."
                break
        return self.feedback


def required_gets(task):
    """Only a literal list explicitly required to be fetched with Requests, for a transport-level check."""
    from requests import Request
    found = re.findall(r"(?im)^using requests, fetch each of these urls:[ \t]*\r?\n((?:https?://[^\s]+[ \t]*(?:\r?\n|$))+)", task)
    if len(found) != 1:
        return ()
    urls = found[0].split()
    if not 2 <= len(urls) <= 16:
        return ()
    if any(len(u) > 512 or re.search(r"[?#@<>]", u) or u[-1] in ",.)" for u in urls):
        return ()
    try:
        return tuple(dict.fromkeys(Request("GET", u).prepare().url for u in urls))
    except ValueError:
        return ()


def literal_requests_only(program):
    """When every request in a program is visibly a plain literal GET, missing observations are conclusive."""
    try:
        body = ast.parse(program).body
    except (SyntaxError, ValueError):
        return False
    # This deliberately excludes helper functions, proxy sessions, dynamic dispatch and subprocesses.
    if not body or not isinstance(body[0], ast.Import) or len(body[0].names) != 1:
        return False
    first = body[0].names[0]
    if first.name != "requests" or first.asname:
        return False
    calls = 0
    for stmt in body[1:]:
        if not isinstance(stmt, ast.Expr) or not isinstance(stmt.value, ast.Call):
            return False
        call = stmt.value
        if call.keywords or len(call.args) != 1 or not isinstance(call.args[0], ast.Constant):
            return False
        func = call.func
        if isinstance(func, ast.Name) and func.id == "print":
            continue
        if not (isinstance(func, ast.Attribute) and func.attr == "get"
                and isinstance(func.value, ast.Name) and func.value.id == "requests"
                and isinstance(call.args[0].value, str)):
            return False
        calls += 1
    return bool(calls)
