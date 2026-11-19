"""One optional public-search candidate for a writer that parses an already decoded JSON object."""

import ast
import symtable


def _docstring(node):
    return isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)


def _bound_names(scope, protected):
    for symbol in scope.get_symbols():
        if symbol.get_name() in protected and (symbol.is_assigned() or symbol.is_parameter()):
            return True
    return any(_bound_names(child, protected) for child in scope.get_children())


def _candidate(program):
    tree = ast.parse(program)
    nodes = list(ast.walk(tree))
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    if len(nodes) > 3000 or len(functions) != 1:
        return
    fn, = functions
    if fn.name != "solve" or fn.decorator_list or fn.args.kwonlyargs or fn.args.vararg or fn.args.kwarg:
        return
    args = fn.args.posonlyargs + fn.args.args
    if len(args) != 1 or fn.args.defaults or args[0].annotation or fn.returns:
        return
    arg = args[0].arg
    imports = (ast.Import, ast.ImportFrom)
    if any(node is not fn and not _docstring(node) and not isinstance(node, imports) for node in tree.body):
        return
    prefix = [node for node in tree.body if isinstance(node, imports)]
    for statement in fn.body:
        if isinstance(statement, imports):
            prefix.append(statement)
        elif not _docstring(statement):
            break
    else:
        return
    if isinstance(statement, ast.Assign):
        if len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name):
            return
    elif not isinstance(statement, ast.Return):
        return

    # Look through direct field access only. The original argument has had no opportunity to change.
    owner = statement
    call = owner.value
    while isinstance(call, ast.Subscript) or (isinstance(call, ast.Call)
                                               and isinstance(call.func, ast.Attribute) and call.func.attr == "get"):
        owner = call if isinstance(call, ast.Subscript) else call.func
        call = owner.value
    if not (isinstance(call, ast.Call) and len(call.args) == 1 and not call.keywords
            and isinstance(call.args[0], ast.Name) and call.args[0].id == arg):
        return
    if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name) and call.func.attr == "loads":
        binding, direct = call.func.value.id, False
    elif isinstance(call.func, ast.Name):
        binding, direct = call.func.id, True
    else:
        return

    # Demand one ordinary import of this name. Decline shadowed builtins, custom parsers and mutating namespaces.
    guards = {"type", "dict", "list"}
    if _bound_names(symtable.symtable(program, "<worker>", "exec"), guards | {binding}):
        return
    found = []
    for node in nodes:
        if isinstance(node, imports):
            for alias in node.names:
                name = alias.asname or alias.name.split(".")[0]
                if name in guards or alias.name == "*":
                    return
                if name == binding:
                    ordinary = ((not direct and isinstance(node, ast.Import) and alias.name == "json")
                                or (direct and isinstance(node, ast.ImportFrom) and not node.level
                                    and node.module == "json" and alias.name == "loads"))
                    found.append(ordinary and node in prefix)
        if isinstance(node, ast.Attribute) and (not isinstance(node.ctx, ast.Load) or node.attr == "__dict__"):
            return
        if isinstance(node, ast.Name) and node.id in {"globals", "locals", "setattr", "delattr", "exec", "eval", "__builtins__"}:
            return
    if found != [True]:
        return

    original = ast.unparse(call)
    replacement = ast.parse(f"{arg} if type({arg}) is dict or type({arg}) is list else {original}", mode="eval").body
    owner.value = ast.copy_location(replacement, call)
    return dict(source=ast.unparse(tree), line=call.lineno, column=call.col_offset,
                before=original, after=ast.unparse(replacement), method="decoded_input")


def variants(program):
    """Yield at most one edit to the first executable statement of an ordinary single-argument solve."""
    if not isinstance(program, str) or len(program) > 32_000:
        return
    try:
        candidate = _candidate(program)
    except (SyntaxError, ValueError, RecursionError):
        return
    if candidate is not None:
        yield candidate
