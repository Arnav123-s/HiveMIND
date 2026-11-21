"""Identify standalone worker functions without running their source."""
import ast
import copy
import hashlib

BUILTINS = set("abs all any bool dict divmod enumerate float int isinstance len list max min range reversed round sorted str sum tuple zip ValueError TypeError KeyError IndexError".split())
METHODS = set("append extend copy count format get index items join keys lower lstrip pop replace reverse rsplit rstrip sort split splitlines startswith endswith strip upper values".split())
FORBIDDEN = (ast.Import, ast.ImportFrom, ast.ClassDef, ast.AsyncFunctionDef, ast.Lambda, ast.Nonlocal, ast.Global,
             ast.Yield, ast.YieldFrom, ast.Await, ast.With, ast.AsyncWith, ast.Delete, ast.Set, ast.SetComp,
             ast.Try, ast.NamedExpr, ast.FunctionType)


def signature(node):
    f = copy.deepcopy(node)
    args = f.args.posonlyargs + f.args.args + f.args.kwonlyargs
    if not args or f.decorator_list or f.args.vararg or f.args.kwarg or getattr(f, "type_params", []):
        return None
    if any(v is not None and not isinstance(v, ast.Constant) for v in f.args.defaults + f.args.kw_defaults):
        return None
    for a in args:
        a.annotation = None
    f.returns = f.type_comment = None
    if isinstance(f.body[0], ast.Expr) and isinstance(f.body[0].value, ast.Constant) and isinstance(f.body[0].value.value, str):
        f.body.pop(0)
    nodes = list(ast.walk(f))
    if not any(isinstance(n, ast.Return) and n.value is not None for n in nodes):
        return None
    if any(isinstance(n, FORBIDDEN) or isinstance(n, ast.FunctionDef) and n is not f for n in nodes):
        return None
    names = {f.name: "function"}
    for a in args:
        names[a.arg] = f"v{len(names)}"
    for n in nodes:
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            names.setdefault(n.id, f"v{len(names)}")
    for n in nodes:
        if isinstance(n, ast.Attribute) and (n.attr not in METHODS or not isinstance(n.ctx, ast.Load)):
            return None
        if isinstance(n, ast.Name) and n.id not in names and n.id not in BUILTINS:
            return None
        if isinstance(n, ast.Call):
            if isinstance(n.func, ast.Name):
                if n.func.id != f.name and (n.func.id not in BUILTINS or n.func.id in names):
                    return None
            elif not isinstance(n.func, ast.Attribute):
                return None
        if isinstance(n, ast.Starred) or isinstance(n, ast.keyword) and n.arg is None:
            return None
    for n in nodes:
        if isinstance(n, ast.arg):
            n.arg = names[n.arg]
        elif isinstance(n, ast.Name):
            n.id = names.get(n.id, n.id)
    f.name = "function"
    return hashlib.sha256(ast.dump(f, include_attributes=False).encode()).hexdigest()
