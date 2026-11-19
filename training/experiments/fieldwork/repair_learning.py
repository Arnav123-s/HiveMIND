"""Learn small expression rewrites from independently qualified fieldwork programs.

The learned data contains only expressions in a bounded grammar with anonymous
operand slots. Public execution selects among proposals. Admission is the caller's
separate qualification decision. This module never runs candidate Python.
"""
import ast
import copy
import hashlib
import json
import re
import symtable
from collections import Counter, defaultdict, deque

from . import arithmetic_repair, decoded_input_repair


REDUCERS = {"sum", "len", "min", "max"}
GUARD_NAMES = {"type", "int", "list", "tuple", "all"} | REDUCERS
COMPARE = (ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE)
SLOT = re.compile(r"[vk][0-9]{1,2}\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")
MAX_EDITS = 8


def _scope_ok(table, names):
    return all(not (symbol.get_name() in names and
                    (symbol.is_assigned() or symbol.is_imported() or symbol.is_parameter()))
               for symbol in table.get_symbols()) and all(_scope_ok(child, names) for child in table.get_children())


def _tree(source, *, field_guards=True):
    if not isinstance(source, str) or len(source) > 32_000:
        return None
    tree = ast.parse(source)
    nodes = list(ast.walk(tree))
    names = GUARD_NAMES | {"dict", "str"} if field_guards else GUARD_NAMES
    if (len(nodes) > 3000 or any(isinstance(n, ast.alias) and n.name == "*" for n in nodes)
            or not _scope_ok(symtable.symtable(source, "<worker>", "exec"), names)):
        return None
    return tree


def _sites(tree):
    """Executable expressions. Skip annotations, defaults, decorators and class bodies."""
    sites = set()

    def visit_statement(node):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            return
        if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign, ast.Return)):
            value = node.value
        elif isinstance(node, (ast.If, ast.While)):
            value = node.test
        else:
            value = None
        if value is not None:
            todo = [value]
            while todo:
                part = todo.pop()
                if isinstance(part, (ast.BinOp, ast.Compare, ast.UnaryOp, ast.Call)):
                    sites.add(part)
                if not isinstance(part, ast.Lambda):
                    todo.extend(ast.iter_child_nodes(part))
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.stmt, ast.ExceptHandler, ast.match_case)):
                visit_statement(child)

    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for stmt in fn.body:
                visit_statement(stmt)
    return sorted(sites, key=lambda n: (n.lineno, n.col_offset, n.end_lineno, n.end_col_offset))


def _operand_key(node):
    """An opaque read of a variable or one fixed string field on a variable."""
    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
        return node.id
    if (isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Load) and isinstance(node.value, ast.Name)
            and isinstance(node.slice, ast.Constant) and type(node.slice.value) is str):
        return (node.value.id, node.slice.value)
    return None


def _operand(key):
    if isinstance(key, str):
        return ast.Name(key, ast.Load())
    if isinstance(key, tuple):
        mapping, field = key
        return ast.Subscript(ast.Name(mapping, ast.Load()), ast.Constant(field), ast.Load())
    return ast.Constant(key)


def _reducer(node):
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in REDUCERS
            and len(node.args) == 1 and _operand_key(node.args[0]) is not None and not node.keywords)


def _integer(node):
    if _operand_key(node) is not None:
        return True
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        return _integer(node.operand)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.FloorDiv, ast.Mod)):
        return _integer(node.left) and _integer(node.right)
    return isinstance(node, ast.Constant) and type(node.value) is int


def _scalar(node):
    if isinstance(node, ast.Compare):
        return (len(node.ops) == 1 and isinstance(node.ops[0], COMPARE)
                and _integer(node.left) and _integer(node.comparators[0]))
    return _integer(node)


def _encode(node, slots, *, add):
    """Replace identifiers and nonstructural integer constants with typed slots."""
    class Encode(ast.NodeTransformer):
        def slot(self, key, prefix):
            if key not in slots:
                if not add:
                    raise KeyError(key)
                slots[key] = prefix + str(len(slots))
            return ast.Name(slots[key], ast.Load())

        def visit_Name(self, n):
            return self.slot(n.id, "v")

        def visit_Subscript(self, n):
            return self.slot(_operand_key(n), "v")

        def visit_Constant(self, n):
            return n if n.value in (0, 1) else self.slot(n.value, "k")

        def visit_Call(self, n):
            return ast.Call(n.func, [self.visit(n.args[0])], [])

    return ast.unparse(Encode().visit(copy.deepcopy(node)))


def _rule(old, new):
    a_call, b_call = _reducer(old), _reducer(new)
    if a_call or b_call:
        if not (a_call and b_call and _operand_key(old.args[0]) == _operand_key(new.args[0])):
            return None
    elif not (_scalar(old) and _scalar(new)):
        return None
    if max(sum(1 for _ in ast.walk(n)) for n in (old, new)) > 48:
        return None
    slots = {}
    before = _encode(old, slots, add=True)
    try:
        after = _encode(new, slots, add=False)
    except KeyError:
        return None
    if before == after or not slots:  # structural constants alone carry no reusable operands
        return None
    used = {n.id for n in ast.walk(ast.parse(after, mode="eval")) if isinstance(n, ast.Name)}
    if not set(slots.values()) <= used:
        return None
    return {"before": before, "after": after}


def _shape(value):
    if isinstance(value, ast.AST):
        return ast.dump(value)
    if isinstance(value, list):
        return tuple(_shape(item) for item in value)
    return value


def _difference(old, new, old_sites):
    """Descend the one changed branch; use the smallest supported expression covering its differences."""
    if type(old) is type(new) and isinstance(old, (ast.AST, list)):
        children = (zip(old, new) if isinstance(old, list) else
                    ((v, getattr(new, k)) for k, v in ast.iter_fields(old)))
        if not isinstance(old, list) or len(old) == len(new):
            differs = [(a, b) for a, b in children if _shape(a) != _shape(b)]
            if len(differs) == 1:
                deeper = _difference(*differs[0], old_sites)
                if deeper:
                    return deeper
    if isinstance(old, ast.AST) and old in old_sites and isinstance(new, ast.expr):
        return _rule(old, new)
    return None


def discover(before_source, after_source):
    """Extract one expression change, ignoring formatting. Other simultaneous edits disqualify the pair."""
    try:
        before, after = _tree(before_source), _tree(after_source)
        if before is None or after is None:
            return None
        return _difference(before, after, set(_sites(before)))
    except (SyntaxError, ValueError, RecursionError):
        return None


def _read_rule(rule):
    if not isinstance(rule, dict):
        return None
    try:
        before, after = (rule.get(key) for key in ("before", "after"))
        if not all(isinstance(s, str) and len(s) <= 400 for s in (before, after)):
            return None
        a, b = (ast.parse(s, mode="eval").body for s in (before, after))
        for expr in (a, b):
            if not (_scalar(expr) or _reducer(expr)) or sum(1 for _ in ast.walk(expr)) > 48:
                return None
            for n in ast.walk(expr):
                if isinstance(n, ast.Name) and not SLOT.fullmatch(n.id) and not (_reducer(expr) and n is expr.func):
                    return None
                if isinstance(n, ast.Constant) and n.value not in (0, 1):
                    return None
        if before == after or not isinstance(a, (ast.BinOp, ast.UnaryOp, ast.Compare, ast.Call)):
            return None
        slots = lambda t: {n.id for n in ast.walk(t) if isinstance(n, ast.Name) and SLOT.fullmatch(n.id)}
        if not slots(a) or slots(a) != slots(b) or _reducer(a) != _reducer(b):
            return None
        if _reducer(a) and a.args[0].id != b.args[0].id:
            return None
        return a, b
    except (SyntaxError, ValueError, RecursionError):
        return None


def _support(donors):
    """Conservative support from disjoint contracts, failed sources and validation corpora.

    Prefer scarce coordinates to avoid simple replay collisions. Greedy packing
    stays bounded and deterministic. It may undercount genuine corroboration.
    """
    counts = [Counter(row[i] for row in donors) for i in range(3)]
    taken = [set() for _ in counts]
    support = 0
    for row in sorted(donors, key=lambda row: (sum(c[v] for c, v in zip(counts, row)), row)):
        if any(value in used for value, used in zip(row, taken)):
            continue
        for value, used in zip(row, taken):
            used.add(value)
        support += 1
        if support == 64:
            break
    return support


def _rule_id(before, after):
    return hashlib.sha256(json.dumps([before, after]).encode()).hexdigest()


def learn(bank):
    """Derive a repeatable policy from the output of work.load_bank (qualified entries only)."""
    evidence = defaultdict(set)
    for entry in bank:
        if not isinstance(entry, dict) or type(entry.get("validation")) is not int or entry["validation"] <= 0:
            continue
        if (any(tag in entry for tag in ("arithmetic_repair", "learned_repair", "decoded_input_repair")) or not isinstance(entry.get("description"), str)
                or not isinstance(entry.get("repair_experience"), list)):
            continue
        contract = " ".join(entry["description"].casefold().split())
        for event in entry["repair_experience"][:32]:
            if not isinstance(event, dict):
                continue
            parent = event.get("parent")
            validation_set = event.get("validation_set")
            if not all(isinstance(value, str) and SHA.fullmatch(value) for value in (parent, validation_set)):
                continue
            rule = event.get("rule")
            if contract and _read_rule(rule) and parent != entry.get("digest"):
                evidence[(rule["before"], rule["after"])].add((contract, parent, validation_set))
    rules = []
    for (before, after), donors in evidence.items():
        support = _support(donors)
        if support >= 2:
            ident = _rule_id(before, after)
            rules.append({"id": ident, "before": before, "after": after, "support": support})
    rules.sort(key=lambda r: (-r["support"], r["id"]))
    return {"version": 2, "rules": rules[:64]}


class _Substitute(ast.NodeTransformer):
    def __init__(self, values):
        self.values = values

    def visit_Name(self, node):
        return copy.deepcopy(self.values.get(node.id, node))


class _AtSite(ast.NodeTransformer):
    def __init__(self, site, new):
        self.key = (type(site), site.lineno, site.col_offset, site.end_lineno, site.end_col_offset)
        self.new = new

    def visit(self, node):
        if isinstance(node, ast.expr) and (type(node), node.lineno, node.col_offset, node.end_lineno, node.end_col_offset) == self.key:
            return self.new
        return super().visit(node)


def _guard(site, slots):
    checks = []
    fields = [key for key in slots if isinstance(key, tuple)]
    for mapping in dict.fromkeys(name for name, _ in fields):
        # Exact dict alone is insufficient: a custom key with a colliding hash
        # could run arbitrary equality code. Check all keys before looking up any.
        checks.append(f"type({mapping}) is dict")
        checks.append(f"all(type(_key) is str for _key in {mapping})")
    for mapping, field in fields:
        checks.append(f"{field!r} in {mapping}")
    if _reducer(site):
        value = ast.unparse(site.args[0])
        checks.append(f"(type({value}) is list or type({value}) is tuple)")
        checks.append(f"all(type(_item) is int for _item in {value})")
    else:
        checks.extend(f"type({ast.unparse(_operand(key))}) is int" for key in slots if not isinstance(key, int))
    checks = [ast.parse(expr, mode="eval").body for expr in checks]
    if not checks:
        return None
    return checks[0] if len(checks) == 1 else ast.BoolOp(ast.And(), checks)


def learned_variants(program, policy):
    try:
        if (not isinstance(policy, dict) or policy.get("version") not in (1, 2)
                or not isinstance(policy.get("rules"), list) or not policy["rules"]):
            return
        tree = _tree(program, field_guards=policy["version"] >= 2)
        if tree is None:
            return
        by_shape = defaultdict(list)
        for site in _sites(tree):
            if (_scalar(site) or _reducer(site)) and sum(1 for _ in ast.walk(site)) <= 48:
                slots = {}
                shape = _encode(site, slots, add=True)
                if policy["version"] == 1 and any(isinstance(key, tuple) for key in slots):
                    continue
                by_shape[shape].append((site, slots))
        for rule in policy["rules"][:64]:
            parsed = _read_rule(rule)
            if (not parsed or type(rule.get("support")) is not int or not 2 <= rule["support"] <= 64
                    or rule.get("id") != _rule_id(rule["before"], rule["after"])):
                continue
            _, replacement = parsed
            for site, slots in by_shape.get(rule["before"], ()):
                values = {slot: _operand(key) for key, slot in slots.items()}
                proposed = _Substitute(values).visit(copy.deepcopy(replacement))
                condition = _guard(site, slots)
                new = ast.IfExp(condition, proposed, site) if condition else proposed
                changed = _AtSite(site, new).visit(copy.deepcopy(tree))
                yield {"source": ast.unparse(ast.fix_missing_locations(changed)), "line": site.lineno, "column": site.col_offset,
                       "before": ast.unparse(site), "after": ast.unparse(proposed), "method": "learned",
                       "rule_id": rule["id"], "support": rule["support"]}
    except (SyntaxError, ValueError, RecursionError, KeyError):
        return


def _interleave(program, policy):
    streams = deque([learned_variants(program, policy), arithmetic_repair.regroup(program)])
    if not isinstance(policy, dict) or policy.get("version") != 1:
        streams.append(decoded_input_repair.variants(program))
    while streams:
        stream = streams.popleft()
        variant = next(stream, None)
        if variant is not None:
            streams.append(stream)
            yield variant


def select(program, examples, score, limit=MAX_EDITS, *, original_passed=None, policy=None):
    """Interleave learned and original alternatives, charging each distinct public evaluation to the same cap."""
    if not examples or limit <= 0:
        return None
    original = score(program, examples) if original_passed is None else original_passed
    if type(original) is not int or not 0 <= original < len(examples):
        return None
    seen = set()
    for variant in _interleave(program, policy):
        edit = {k: variant[k] for k in ("line", "column", "before", "after")}
        key = tuple(edit.values())
        if key in seen:
            continue
        seen.add(key)
        passed = score(variant["source"], examples)
        if type(passed) is int and passed == len(examples):
            return {"program": variant["source"], "original_passed": original, "passed": passed, "tried": len(seen),
                    "edit": edit, "method": variant.get("method", "arithmetic"),
                    "rule_id": variant.get("rule_id"), "support": variant.get("support", 0)}
        if len(seen) >= min(limit, MAX_EDITS):
            return None
    return None
