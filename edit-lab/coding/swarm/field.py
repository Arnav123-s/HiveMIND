"""Field-coverage specialists, part 1 (phase 2): the task/quality niches.

Each function is ONE tiny job over code the swarm is given, done
deterministically with the stdlib (mostly `ast`), at zero model RAM.
Same envelope convention as constructed.py: {"ok", "output", "evidence"}.

Checker semantics (as in review): ok = the check passed / the code is
clean. Finder semantics: ok = the finder ran; findings are the output.
Transform semantics (refactoring): ok = the new code is returned;
a transform that cannot apply says so and returns ok=False.
"""
import ast
import re


# ------------------------------------------------------------------ helpers
def _parse(code):
    try:
        return ast.parse(code), None
    except SyntaxError as e:
        return None, {"ok": False, "output": None,
                      "evidence": f"SyntaxError line {e.lineno}: {e.msg}"}


def _functions(tree):
    """All function defs (incl. methods, qualified), in source order."""
    out = []

    class V(ast.NodeVisitor):
        def __init__(self):
            self.stack = []

        def visit_ClassDef(self, node):
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        def _fn(self, node):
            out.append((".".join(self.stack + [node.name]), node))
            self.generic_visit(node)

        visit_FunctionDef = _fn
        visit_AsyncFunctionDef = _fn

    V().visit(tree)
    return out


# ------------------------------------------------------------------ reading
def import_lister(task):
    """List the top-level modules a Python program imports."""
    tree, err = _parse(task["code"])
    if err:
        return err
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                mods.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                mods.add(node.module.split(".")[0])
    return {"ok": True, "output": sorted(mods),
            "evidence": f"{len(mods)} imported module(s)"}


def function_lister(task):
    """List every function/method defined, qualified, in source order."""
    tree, err = _parse(task["code"])
    if err:
        return err
    names = [name for name, _ in _functions(tree)]
    return {"ok": True, "output": names, "evidence": f"{len(names)} function(s)"}


def class_lister(task):
    """List classes with their method names."""
    tree, err = _parse(task["code"])
    if err:
        return err
    out = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            methods = [n.name for n in node.body
                       if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            out.append({"class": node.name, "methods": methods})
    return {"ok": True, "output": out, "evidence": f"{len(out)} class(es)"}


def signature_extractor(task):
    """Return the signature string of one named function/method."""
    tree, err = _parse(task["code"])
    if err:
        return err
    for name, node in _functions(tree):
        if name.split(".")[-1] == task["name"]:
            sig = f"{task['name']}({ast.unparse(node.args)})"
            if node.returns is not None:
                sig += f" -> {ast.unparse(node.returns)}"
            return {"ok": True, "output": sig, "evidence": f"signature of {name}"}
    return {"ok": False, "output": None,
            "evidence": f"no function named {task['name']}", "gap": "no-such-function"}


def docstring_extractor(task):
    """Return the docstring of the module, or of one named function/class."""
    tree, err = _parse(task["code"])
    if err:
        return err
    name = task.get("name")
    if not name:
        doc = ast.get_docstring(tree)
        return {"ok": True, "output": doc,
                "evidence": "module docstring" if doc else "module has no docstring"}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) \
                and node.name == name:
            doc = ast.get_docstring(node)
            return {"ok": True, "output": doc,
                    "evidence": f"docstring of {name}" if doc else f"{name} has no docstring"}
    return {"ok": False, "output": None,
            "evidence": f"no function/class named {name}", "gap": "no-such-function"}


def call_finder(task):
    """List the distinct callables a program calls (names/attribute names)."""
    tree, err = _parse(task["code"])
    if err:
        return err
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
    return {"ok": True, "output": sorted(calls), "evidence": f"{len(calls)} distinct call(s)"}


def branch_counter(task):
    """Count decision points (cyclomatic complexity - 1) in one function
    or the whole module."""
    tree, err = _parse(task["code"])
    if err:
        return err
    scope, label = tree, "module"
    if task.get("name"):
        scope = None
        for name, node in _functions(tree):
            if name.split(".")[-1] == task["name"]:
                scope, label = node, name
                break
        if scope is None:
            return {"ok": False, "output": None,
                    "evidence": f"no function named {task['name']}",
                    "gap": "no-such-function"}
    n = 0
    for node in ast.walk(scope):
        if isinstance(node, (ast.If, ast.For, ast.AsyncFor, ast.While,
                             ast.ExceptHandler, ast.IfExp)):
            n += 1
        elif isinstance(node, ast.BoolOp):
            n += len(node.values) - 1
        elif isinstance(node, ast.comprehension):
            n += len(node.ifs)
    return {"ok": True, "output": n,
            "evidence": f"{label}: {n} decision point(s), complexity {n + 1}"}


def recursion_detector(task):
    """List functions that call themselves by name."""
    tree, err = _parse(task["code"])
    if err:
        return err
    out = []
    for name, node in _functions(tree):
        short = name.split(".")[-1]
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) \
                    and sub.func.id == short:
                out.append(name)
                break
    return {"ok": True, "output": out, "evidence": f"{len(out)} recursive function(s)"}


def code_line_counter(task):
    """Count code lines: non-blank lines that are not pure comments.
    (Docstring lines count as code — the rule is lexical, stated here.)"""
    text = task["code"] if "code" in task else task.get("text", "")
    n = sum(1 for l in text.splitlines() if l.strip() and not l.strip().startswith("#"))
    return {"ok": True, "output": n, "evidence": f"{n} code line(s)"}


# ------------------------------------------------------------- testing (ext)
def test_function_counter(task):
    """Count tests: module-level test_* functions + test_* methods."""
    tree, err = _parse(task["code"])
    if err:
        return err
    n = 0
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and node.name.startswith("test_"):
            n += 1
        elif isinstance(node, ast.ClassDef):
            n += sum(1 for m in node.body
                     if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
                     and m.name.startswith("test_"))
    return {"ok": True, "output": n, "evidence": f"{n} test function(s)"}


def assertion_counter(task):
    """Count assertions: assert statements + self.assert* calls."""
    tree, err = _parse(task["code"])
    if err:
        return err
    n = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            n += 1
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr.startswith("assert"):
            n += 1
    return {"ok": True, "output": n, "evidence": f"{n} assertion(s)"}


def untested_function_finder(task):
    """Module-level public functions whose name never appears in the tests."""
    tree, err = _parse(task["code"])
    if err:
        return err
    tests = task.get("tests", "")
    out = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and not node.name.startswith("_") \
                and not node.name.startswith("test_"):
            if not re.search(rf"\b{re.escape(node.name)}\b", tests):
                out.append(node.name)
    return {"ok": True, "output": sorted(out),
            "evidence": f"{len(out)} untested public function(s)"}


# ----------------------------------------------------------------- linting
def line_length_checker(task):
    """Lines longer than the limit (default 100). ok = none."""
    limit = task.get("limit", 100)
    bad = [(i + 1, len(l)) for i, l in enumerate(task["text"].splitlines())
           if len(l) > limit]
    return {"ok": not bad, "output": bad,
            "evidence": f"{len(bad)} line(s) over {limit} chars"}


def trailing_whitespace_checker(task):
    """Lines ending in a space or tab. ok = none."""
    bad = [i + 1 for i, l in enumerate(task["text"].splitlines())
           if l != l.rstrip(" \t")]
    return {"ok": not bad, "output": bad,
            "evidence": f"{len(bad)} line(s) with trailing whitespace"}


def tab_indent_checker(task):
    """Lines indented with a tab. ok = none."""
    bad = [i + 1 for i, l in enumerate(task["text"].splitlines())
           if l.startswith("\t")]
    return {"ok": not bad, "output": bad,
            "evidence": f"{len(bad)} tab-indented line(s)"}


def final_newline_checker(task):
    """Text ends with exactly one newline. ok = it does."""
    text = task["text"]
    ok = bool(text) and text.endswith("\n") and not text.endswith("\n\n")
    return {"ok": ok, "output": ok,
            "evidence": "exactly one final newline" if ok else "final newline missing or doubled"}


_SNAKE = re.compile(r"^[a-z_][a-z0-9_]*$")
_UPPER = re.compile(r"^[A-Z][A-Z0-9_]*$")


def function_name_case_checker(task):
    """Function names that are not snake_case (dunders exempt). ok = none."""
    tree, err = _parse(task["code"])
    if err:
        return err
    bad = [name for name, _ in _functions(tree)
           if not _SNAKE.match(name.split(".")[-1])
           and not (name.split(".")[-1].startswith("__") and name.split(".")[-1].endswith("__"))]
    return {"ok": not bad, "output": bad,
            "evidence": f"{len(bad)} non-snake-case function name(s)"}


def constant_name_case_checker(task):
    """Module-level literal assignments whose name is not UPPER_SNAKE —
    constants by convention, misnamed. ok = none."""
    tree, err = _parse(task["code"])
    if err:
        return err
    bad = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) \
                and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if not _UPPER.match(name) and not name.startswith("_"):
                bad.append(name)
    return {"ok": not bad, "output": bad,
            "evidence": f"{len(bad)} module constant(s) not UPPER_SNAKE"}


def wildcard_import_checker(task):
    """`from x import *` occurrences. ok = none."""
    tree, err = _parse(task["code"])
    if err:
        return err
    bad = [{"module": node.module, "line": node.lineno}
           for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
           and any(a.name == "*" for a in node.names)]
    return {"ok": not bad, "output": bad,
            "evidence": f"{len(bad)} wildcard import(s)"}


def bare_except_checker(task):
    """Bare `except:` clauses. ok = none."""
    tree, err = _parse(task["code"])
    if err:
        return err
    bad = [node.lineno for node in ast.walk(tree)
           if isinstance(node, ast.ExceptHandler) and node.type is None]
    return {"ok": not bad, "output": bad,
            "evidence": f"{len(bad)} bare except clause(s)"}


def print_call_checker(task):
    """print() call sites. ok = none."""
    tree, err = _parse(task["code"])
    if err:
        return err
    bad = [node.lineno for node in ast.walk(tree)
           if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
           and node.func.id == "print"]
    return {"ok": not bad, "output": bad,
            "evidence": f"{len(bad)} print() call(s)"}


# -------------------------------------------------------------- refactoring
def trailing_whitespace_stripper(task):
    """Remove trailing spaces/tabs from every line."""
    lines = task["code"].split("\n")
    out = [l.rstrip(" \t") for l in lines]
    changed = sum(1 for a, b in zip(lines, out) if a != b)
    return {"ok": True, "output": "\n".join(out),
            "evidence": f"stripped {changed} line(s)"}


def tab_expander(task):
    """Expand each leading tab to 4 spaces (indentation only)."""
    out, changed = [], 0
    for line in task["code"].split("\n"):
        stripped = line.lstrip("\t")
        tabs = len(line) - len(stripped)
        new = "    " * tabs + stripped
        changed += new != line
        out.append(new)
    return {"ok": True, "output": "\n".join(out),
            "evidence": f"expanded leading tabs on {changed} line(s)"}


def final_newline_fixer(task):
    """Make the text end with exactly one newline."""
    text = task["code"]
    if not text:
        return {"ok": True, "output": text, "evidence": "empty text, nothing to fix"}
    out = text.rstrip("\n") + "\n"
    return {"ok": True, "output": out,
            "evidence": "final newline normalized" if out != text else "already normalized"}


def import_block_sorter(task):
    """Sort the single-line import statements at the top of the file
    alphabetically, in place (blank/comment lines keep their slots).
    Parenthesized multi-line imports are refused, not guessed at."""
    lines = task["code"].split("\n")
    block = 0
    for line in lines:
        s = line.strip()
        if s.startswith(("import ", "from ")) and s.endswith("("):
            return {"ok": False, "output": None,
                    "evidence": "multi-line import in header block; refusing",
                    "gap": "multiline-import"}
        if s.startswith(("import ", "from ")) or s == "" or s.startswith("#"):
            block += 1
        else:
            break
    slots = [i for i in range(block)
             if lines[i].strip().startswith(("import ", "from "))]
    imports = sorted(lines[i] for i in slots)
    out = list(lines)
    for i, txt in zip(slots, imports):
        out[i] = txt
    changed = sum(1 for i in slots if lines[i] != out[i])
    return {"ok": True, "output": "\n".join(out),
            "evidence": f"{len(slots)} import line(s), {changed} moved"}


def unused_import_remover(task):
    """Remove single-line imports whose bound name occurs nowhere else.
    Conservative: only whole-line, single-statement, single-name imports
    where every alias is unused; anything ambiguous is left alone."""
    code = task["code"]
    tree, err = _parse(code)
    if err:
        return err
    lines = code.split("\n")
    drop, removed = set(), []

    def uses(name):
        return len(re.findall(rf"\b{re.escape(name)}\b", code))

    for node in tree.body:
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if node.end_lineno != node.lineno or node.lineno > len(lines):
            continue
        if not re.match(r"^\s*(import|from)\s", lines[node.lineno - 1]):
            continue
        bound = []
        for a in node.names:
            if a.name == "*":
                bound = None
                break
            bound.append(a.asname or (a.name.split(".")[0]
                                      if isinstance(node, ast.Import) else a.name))
        if bound and all(uses(b) == 1 for b in bound):
            drop.add(node.lineno - 1)
            removed.append(lines[node.lineno - 1].strip())
    out = "\n".join(l for i, l in enumerate(lines) if i not in drop)
    return {"ok": True, "output": out,
            "evidence": f"removed {len(removed)} unused import(s): {removed}"}


def rename_symbol(task):
    """Rename every whole-word occurrence of one identifier.
    Lexical rename: strings and comments are renamed too — the evidence
    says so, and the caller accepts that scope or uses a model."""
    code, old, new = task["code"], task["old"], task["new"]
    if not (old.isidentifier() and new.isidentifier()):
        return {"ok": False, "output": None, "evidence": "old/new must be identifiers"}
    n = len(re.findall(rf"\b{re.escape(old)}\b", code))
    if n == 0:
        return {"ok": False, "output": None,
                "evidence": f"{old!r} does not occur", "gap": "no-such-symbol"}
    out = re.sub(rf"\b{re.escape(old)}\b", new, code)
    return {"ok": True, "output": out,
            "evidence": f"renamed {n} occurrence(s) of {old} (lexical, incl. strings/comments)"}


# -------------------------------------------------------------- documenting
def docstring_coverage_checker(task):
    """Functions/classes (and methods) lacking a docstring. ok = none."""
    tree, err = _parse(task["code"])
    if err:
        return err
    targets = []

    class V(ast.NodeVisitor):
        def __init__(self):
            self.stack = []

        def visit_ClassDef(self, node):
            targets.append((".".join(self.stack + [node.name]), node))
            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        def _fn(self, node):
            targets.append((".".join(self.stack + [node.name]), node))
            self.generic_visit(node)

        visit_FunctionDef = _fn
        visit_AsyncFunctionDef = _fn

    V().visit(tree)
    missing = [name for name, node in targets if ast.get_docstring(node) is None]
    total = len(targets)
    return {"ok": not missing,
            "output": {"missing": missing, "covered": total - len(missing), "total": total},
            "evidence": f"docstrings on {total - len(missing)}/{total} definitions"}


def todo_marker_finder(task):
    """TODO/FIXME/XXX/HACK markers, with line numbers."""
    text = task["code"] if "code" in task else task.get("text", "")
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        m = re.search(r"\b(TODO|FIXME|XXX|HACK)\b", line)
        if m:
            out.append({"line": i, "marker": m.group(1), "text": line.strip()[:80]})
    return {"ok": True, "output": out, "evidence": f"{len(out)} marker(s)"}


def license_header_checker(task):
    """A license/copyright notice in the first 5 lines. ok = present."""
    head = "\n".join(task["text"].splitlines()[:5]).lower()
    found = any(k in head for k in ("copyright", "spdx-license-identifier",
                                    "licensed under", "license"))
    return {"ok": found, "output": found,
            "evidence": "license header present" if found else "no license header in first 5 lines"}


def comment_density_counter(task):
    """Comment lines / non-blank lines."""
    lines = [l for l in task["text"].splitlines() if l.strip()]
    comments = sum(1 for l in lines if l.strip().startswith("#"))
    ratio = round(comments / len(lines), 3) if lines else 0.0
    return {"ok": True, "output": ratio,
            "evidence": f"{comments}/{len(lines)} non-blank lines are comments"}


# ---------------------------------------------------------------- security
_SECRET_NAME = re.compile(r"(?i)(password|passwd|pwd|api_?key|secret|token|auth)")


def hardcoded_secret_finder(task):
    """Assignments of a non-empty string literal to a secret-looking name.
    ok = none found."""
    tree, err = _parse(task["code"])
    if err:
        return err
    bad = []
    for node in ast.walk(tree):
        targets, value = [], None
        if isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        elif isinstance(node, ast.AnnAssign):
            targets, value = [node.target], node.value
        if isinstance(value, ast.Constant) and isinstance(value.value, str) \
                and value.value != "":
            for t in targets:
                if isinstance(t, ast.Name) and _SECRET_NAME.search(t.id):
                    bad.append({"name": t.id, "line": node.lineno})
    return {"ok": not bad, "output": bad,
            "evidence": f"{len(bad)} hardcoded secret(s)"}


def eval_exec_finder(task):
    """Calls to eval()/exec(). ok = none."""
    tree, err = _parse(task["code"])
    if err:
        return err
    bad = [node.lineno for node in ast.walk(tree)
           if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
           and node.func.id in ("eval", "exec")]
    return {"ok": not bad, "output": bad,
            "evidence": f"{len(bad)} eval/exec call(s)"}


def _module_aliases(tree, module):
    """Local names bound to `module` itself or imported from it:
    returns (module_names, {local_func_name: original_func_name})."""
    mod_names, func_names = set(), {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name == module:
                    mod_names.add(a.asname or module)
        elif isinstance(node, ast.ImportFrom) and node.module == module:
            for a in node.names:
                func_names[a.asname or a.name] = a.name
    return mod_names, func_names


def _module_call_finder(task, module, funcs, label):
    tree, err = _parse(task["code"])
    if err:
        return err
    mod_names, func_names = _module_aliases(tree, module)
    bad = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) \
                and f.value.id in mod_names and f.attr in funcs:
            bad.append(node.lineno)
        elif isinstance(f, ast.Name) and func_names.get(f.id) in funcs:
            bad.append(node.lineno)
    return {"ok": not bad, "output": bad,
            "evidence": f"{len(bad)} {label} call(s)"}


def pickle_load_finder(task):
    """pickle.load/loads calls (untrusted deserialization). ok = none."""
    return _module_call_finder(task, "pickle", {"load", "loads"}, "pickle load")


def weak_hash_finder(task):
    """hashlib.md5/sha1 calls (weak hashes). ok = none."""
    return _module_call_finder(task, "hashlib", {"md5", "sha1"}, "weak hash")


def sql_interpolation_finder(task):
    """execute()/executemany() fed an f-string, a %-format or .format().
    ok = none — parameterized queries are the clean pattern."""
    tree, err = _parse(task["code"])
    if err:
        return err
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and node.func.attr in ("execute", "executemany") and node.args:
            arg = node.args[0]
            if isinstance(arg, ast.JoinedStr) \
                    or (isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Mod)) \
                    or (isinstance(arg, ast.Call) and isinstance(arg.func, ast.Attribute)
                        and arg.func.attr == "format"):
                bad.append(node.lineno)
    return {"ok": not bad, "output": bad,
            "evidence": f"{len(bad)} interpolated SQL call(s)"}


def shell_true_finder(task):
    """Calls passing shell=True. ok = none."""
    tree, err = _parse(task["code"])
    if err:
        return err
    bad = [node.lineno for node in ast.walk(tree)
           if isinstance(node, ast.Call)
           and any(kw.arg == "shell" and isinstance(kw.value, ast.Constant)
                   and kw.value.value is True for kw in node.keywords)]
    return {"ok": not bad, "output": bad,
            "evidence": f"{len(bad)} shell=True call(s)"}


# ------------------------------------------------------------- performance
def loop_depth_finder(task):
    """Deepest loop nesting in the module, and functions reaching depth 2+."""
    tree, err = _parse(task["code"])
    if err:
        return err

    def depth(node, d=0):
        best = d
        for child in ast.iter_child_nodes(node):
            nd = d + 1 if isinstance(child, (ast.For, ast.AsyncFor, ast.While)) else d
            best = max(best, depth(child, nd))
        return best

    deep = [name for name, node in _functions(tree) if depth(node) >= 2]
    return {"ok": True, "output": {"max_depth": depth(tree), "deep_functions": deep},
            "evidence": f"max loop depth {depth(tree)}; {len(deep)} function(s) at depth 2+"}


def string_concat_in_loop_finder(task):
    """Candidate += / x = x + ... accumulation inside a loop body
    (quadratic-string smell; name-based heuristic, stated in evidence)."""
    tree, err = _parse(task["code"])
    if err:
        return err
    bad = []

    class V(ast.NodeVisitor):
        def __init__(self):
            self.in_loop = 0

        def _loop(self, node):
            self.in_loop += 1
            self.generic_visit(node)
            self.in_loop -= 1

        visit_For = _loop
        visit_AsyncFor = _loop
        visit_While = _loop

        def visit_AugAssign(self, node):
            if self.in_loop and isinstance(node.op, ast.Add):
                bad.append(node.lineno)
            self.generic_visit(node)

        def visit_Assign(self, node):
            if self.in_loop and isinstance(node.value, ast.BinOp) \
                    and isinstance(node.value.op, ast.Add) \
                    and any(isinstance(t, ast.Name) and isinstance(node.value.left, ast.Name)
                            and t.id == node.value.left.id for t in node.targets):
                bad.append(node.lineno)
            self.generic_visit(node)

    V().visit(tree)
    return {"ok": True, "output": sorted(set(bad)),
            "evidence": f"{len(set(bad))} accumulation site(s) inside loops (heuristic)"}


def global_mutation_finder(task):
    """Functions declaring `global` (shared-state mutation smell)."""
    tree, err = _parse(task["code"])
    if err:
        return err
    out = [name for name, node in _functions(tree)
           if any(isinstance(n, ast.Global) for n in ast.walk(node))]
    return {"ok": True, "output": out,
            "evidence": f"{len(out)} function(s) using global"}
