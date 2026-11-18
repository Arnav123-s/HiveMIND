"""Bounded one-edit repair of rounding order in a Python worker's integer arithmetic.

Search uses Python syntax only. Selection takes a caller-supplied public-example
scorer; the candidate still needs an independent validation pass before admission.
"""
import ast
import copy
import symtable


def _integer_expression(node):
    if isinstance(node, ast.Name):
        return isinstance(node.ctx, ast.Load)
    if isinstance(node, ast.Constant):
        return type(node.value) is int
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        return _integer_expression(node.operand)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.FloorDiv, ast.Mod)):
        return _integer_expression(node.left) and _integer_expression(node.right)
    return False


def _builtin_type_names(table):
    for symbol in table.get_symbols():
        if symbol.get_name() in ("type", "int") and (symbol.is_assigned() or symbol.is_parameter() or symbol.is_imported()):
            return False
    return all(_builtin_type_names(child) for child in table.get_children())


def _rotation(node):
    # Preserve the denominator and the evaluation order of all three original operands.
    if isinstance(node.op, ast.FloorDiv) and isinstance(node.left, ast.BinOp) and isinstance(node.left.op, ast.Mult):
        return ast.BinOp(node.left.left, ast.Mult(), ast.BinOp(node.left.right, ast.FloorDiv(), node.right))
    if isinstance(node.op, ast.Mult) and isinstance(node.right, ast.BinOp) and isinstance(node.right.op, ast.FloorDiv):
        return ast.BinOp(ast.BinOp(node.left, ast.Mult(), node.right.left), ast.FloorDiv(), node.right.right)
    return None


class _Replace(ast.NodeTransformer):
    def __init__(self, node, replacement):
        self.position = (node.lineno, node.col_offset, node.end_lineno, node.end_col_offset)
        self.replacement = replacement

    def visit_BinOp(self, node):
        if (node.lineno, node.col_offset, node.end_lineno, node.end_col_offset) == self.position:
            return ast.copy_location(self.replacement, node)
        return self.generic_visit(node)


def regroup(program, limit=8):
    """Yield up to eight deterministic alternatives in source order, each differing at one site."""
    if not isinstance(program, str) or len(program) > 32_000 or limit <= 0:
        return
    try:
        tree = ast.parse(program)
        nodes = list(ast.walk(tree))
        if len(nodes) > 3_000 or any(isinstance(n, ast.alias) and n.name == "*" for n in nodes):
            return
        if not _builtin_type_names(symtable.symtable(program, "<worker>", "exec")):
            return
        # Annotations and function defaults are outside the worker calculations.
        sites = {}
        for statement in nodes:
            if isinstance(statement, (ast.Assign, ast.AugAssign, ast.AnnAssign, ast.Return)) and statement.value is not None:
                for node in ast.walk(statement.value):
                    if isinstance(node, ast.BinOp):
                        sites[node] = None
        emitted = 0
        for node in sorted(sites, key=lambda n: (n.lineno, n.col_offset, n.end_lineno, n.end_col_offset)):
            new = _rotation(node)
            if new is None or not _integer_expression(node):
                continue
            # Names can hold floats or objects with overloaded arithmetic. For those
            # inputs, evaluate only the original expression with its original grouping.
            names = sorted({v.id for v in ast.walk(node) if isinstance(v, ast.Name)})
            guards = [ast.Compare(ast.Call(ast.Name("type", ast.Load()), [ast.Name(name, ast.Load())], []),
                                  [ast.Is()], [ast.Name("int", ast.Load())]) for name in names]
            replacement = new
            if guards:
                condition = guards[0] if len(guards) == 1 else ast.BoolOp(ast.And(), guards)
                replacement = ast.IfExp(condition, new, node)
            variant = _Replace(node, replacement).visit(copy.deepcopy(tree))
            source = ast.unparse(ast.fix_missing_locations(variant))
            yield {"source": source, "line": node.lineno, "column": node.col_offset,
                   "before": ast.unparse(node), "after": ast.unparse(new)}
            emitted += 1
            if emitted >= min(limit, 8):
                return
    except (SyntaxError, ValueError, RecursionError):
        return


def select(program, examples, score, limit=8, *, original_passed=None):
    """Return the first public-perfect improvement. A public score is never a promotion decision."""
    if not examples:
        return None
    original = score(program, examples) if original_passed is None else original_passed
    if type(original) is not int or not 0 <= original < len(examples):
        return None
    for tried, variant in enumerate(regroup(program, limit), 1):
        passed = score(variant["source"], examples)
        if type(passed) is int and passed == len(examples):
            return {"program": variant["source"], "original_passed": original, "passed": passed, "tried": tried,
                    "edit": {key: variant[key] for key in ("line", "column", "before", "after")}}
    return None
