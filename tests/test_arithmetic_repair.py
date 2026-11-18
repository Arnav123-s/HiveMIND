"""Local AST regrouping is bounded, type guarded, and selected using only public outcomes."""
import ast

from training.experiments.fieldwork.arithmetic_repair import regroup, select


def solve(program):
    scope = {}
    exec(program, scope)
    return scope["solve"]


def score(source, rows):
    fn = solve(source)
    return sum(fn(*args) == target for args, target in rows)


def test_public_perfect_improvement_only_and_untouched_parent():
    program = "def solve(a, b, c): return a*b//c"
    rows = [((4, 13, 5), 8), ((3, 6, 4), 3)]
    win = select(program, rows, score)
    assert win["original_passed"] == 0 and win["passed"] == 2 and win["tried"] == 1
    assert win["edit"]["before"] == "a * b // c" and win["edit"]["after"] == "a * (b // c)"
    assert select(win["program"], rows, score) is None
    assert select(program, [*rows, ((1, 1, 1), 99)], score) is None
    assert select(program, [], lambda *a: 1 / 0) is None


def test_opposite_rotation_and_original_expression_for_floats_and_overloaded_numbers():
    program = "def solve(a, b, c): return a*(b//c)"
    (alt,) = regroup(program)
    assert alt["after"] == "a * b // c"
    changed, original = solve(alt["source"]), solve(program)
    assert changed(4, 13, 5) == 10 and original(4, 13, 5) == 8
    assert changed(4.0, 13.0, 5.0) == original(4.0, 13.0, 5.0) == 8.0

    calls = []

    class Counter(int):
        def __floordiv__(self, divisor):
            calls.append(("division", divisor))
            return int(self) // divisor
    assert changed(4, Counter(13), 5) == 8 and calls == [("division", 5)]


def test_reject_calls_subscripts_attributes_effects_and_rebound_builtins():
    for expr in ["a * load() // b", "a * path.value // b", "a * values[0] // b", "a * 2.0 // b",
                 "a * (k := 9) // b", "a * True // b"]:
        assert list(regroup("def solve(a, b): return " + expr)) == []
    assert list(regroup("def solve(type, a, b): return 3*a//b")) == []
    assert list(regroup("from random import *\ndef solve(a): return 3*a//2")) == []
    assert list(regroup("invalid ! syntax")) == []


def test_ceiling_and_source_order_for_multiple_one_site_alternatives():
    source = "def solve(x):\n" + "\n".join(f"    a{i} = x * {i + 2} // 4" for i in range(12)) + "\n    return a0"
    all_edits = list(regroup(source, 100))
    assert [r["line"] for r in all_edits] == list(range(2, 10))
    assert all(sum(isinstance(n, ast.IfExp) for n in ast.walk(ast.parse(r["source"]))) == 1 for r in all_edits)
    assert list(regroup(source, 2)) == all_edits[:2]
    assert list(regroup(source, 0)) == []
