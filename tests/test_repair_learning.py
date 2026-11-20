"""Induce expression edits from admitted experience without running candidate code on host Python."""
import ast
import hashlib

import pytest

from training.experiments.fieldwork import repair_learning as learning


def source(name, expression):
    return f"def solve({name}):\n    return {expression}"


def experience(name, before, after):
    parent = hashlib.sha256(before.encode()).hexdigest()
    return {"task": name, "description": "Work for " + name, "validation": 4,
            "digest": hashlib.sha256(after.encode()).hexdigest(),
            "repair_experience": [{"parent": parent, "validation_set": hashlib.sha256(name.encode()).hexdigest(),
                                   "rule": learning.discover(before, after)}]}


def bank():
    return [experience("tickets", source("codes", "sum(codes)"), source("codes", "len(codes)")),
            experience("alarms", source("events", "sum(events)"), source("events", "len(events)"))]


def test_induces_same_anonymous_rule_across_donors_replays_do_not_add_votes():
    a, b = bank()
    rule = a["repair_experience"][0]["rule"]
    assert rule == b["repair_experience"][0]["rule"] == {"before": "sum(v0)", "after": "len(v0)"}
    no_policy = learning.learn([])
    assert learning.learn([a, a, {**b, "description": " WORK FOR   TICKETS "}]) == no_policy
    assert learning.learn([a, {**b, "repair_experience": a["repair_experience"]}]) == no_policy
    assert learning.learn([a, {**b, "validation": 0}, {**b, "arithmetic_repair": {}}]) == no_policy
    other = b["repair_experience"][0]
    original = a["repair_experience"][0]
    for overrides in [{"validation_set": original["validation_set"]}, {"validation_set": None},
                      {"parent": original["parent"]}]:
        assert learning.learn([a, {**b, "repair_experience": [{**other, **overrides}]}]) == no_policy
    learned = learning.learn([a, b, b])
    assert len(learned["rules"]) == 1 and learned["rules"][0]["support"] == 2
    assert learning.learn([b, a]) == learned


def test_only_one_shared_pure_expression_changes_and_donor_values_do_not_leak():
    ceil = learning.discover(source("n", "n // 71341"), source("n", "(n + 71341 - 1) // 71341"))
    assert ceil == {"before": "v0 // k1", "after": "(v0 + k1 - 1) // k1"}
    a, b = "def solve(x, limit):\n if x < limit:\n  return 1\n return 0", "def solve(x, limit):\n if x <= limit:\n  return 1\n return 0"
    assert learning.discover(a, b) == {"before": "v0 < v1", "after": "v0 <= v1"}
    assert learning.discover(a, b.replace("return 1", "return 2")) is None
    assert learning.discover(source("x", "x // 2"), source("x", "(x + 927) // 2")) is None
    assert learning.discover(source("x", "sum(x)"), source("x", "len(x, y=2)")) is None
    assert learning.discover(source("x", "sum(call())"), source("x", "len(call())")) is None
    assert learning.discover("def solve(sum, xs): return sum(xs)", "def solve(sum, xs): return len(xs)") is None


def test_shared_budget_with_static_fallback_and_type_guarded_learned_edits():
    program = "def solve(samples, a, b, d):\n    cost = a*b//d\n    return cost + sum(samples)"
    policy = learning.learn(bank())
    listed = list(learning.learned_variants(program, policy))
    assert len(listed) == 1 and listed[0]["method"] == "learned"
    assert "if (type(samples) is list or type(samples) is tuple)" in listed[0]["source"]
    assert "else sum(samples)" in listed[0]["source"]
    # Check candidate selection and metering using a structural scorer. Actual
    # worker behavior is qualified by the fieldwork WASI path.
    calls = []
    def arithmetic_only(candidate, examples):
        calls.append(candidate)
        return len(examples) if "a * (b // d)" in candidate else 0
    one = learning.select(program, [1], arithmetic_only, 1, original_passed=0, policy=policy)
    assert one is None and len(calls) == 1
    calls.clear()
    winner = learning.select(program, [1], arithmetic_only, 2, original_passed=0, policy=policy)
    assert winner["method"] == "arithmetic" and len(calls) == winner["tried"] == 2
    calls.clear()
    assert learning.select(program, [1], arithmetic_only, 1, original_passed=1, policy=policy) is None and not calls
    assert learning.select(program, [1], arithmetic_only, 1, original_passed=0, policy=learning.learn([]))["tried"] == 1


@pytest.mark.parametrize("tamper", [
    {"after": "open('bad')"}, {"after": "v0.__class__"}, {"after": "2 ** 1000"},
    {"after": "min(v0, default=0)"}, {"after": "v0 + 581"}, {"after": "len(v8)"},
])
def test_malformed_saved_policy_cannot_inject_python(tamper):
    policy = learning.learn(bank())
    policy["rules"][0].update(tamper)
    assert list(learning.learned_variants(source("samples", "sum(samples)"), policy)) == []


def test_same_learned_arithmetic_shape_keeps_represented_constants_from_new_site():
    donors = [experience(n, source("x", f"x//{d}"), source("x", f"(x+{d}-1)//{d}"))
              for n, d in [("boxes", 25), ("rolls", 78)]]
    (variant,) = learning.learned_variants(source("total", "total//41"), learning.learn(donors))
    assert variant["after"] == "(total + 41 - 1) // 41"
    assert ast.parse(variant["source"]) and "25" not in variant["source"] and "78" not in variant["source"]


def test_field_donors_induce_the_same_rule_as_local_names_and_transfer_layouts():
    compact = "def solve(r, n): return n < r['cap']"
    expanded = "def solve(r):\n level = r['x']\n ceiling = r['t']\n return level < ceiling"
    donors = [experience(label, code, code.replace("<", "<=")) for label, code in
              [("stock", compact), ("trips", expanded)]]
    policy = learning.learn(donors)
    rule, = policy["rules"]
    assert rule["before"] == "v0 < v1" and rule["after"] == "v0 <= v1"
    target = "def solve(batch): return batch['units'] < batch['room']"
    edit, = learning.learned_variants(target, policy)
    assert edit["after"] == "batch['units'] <= batch['room']"
    assert "cap" not in edit["source"] and "ceiling" not in edit["source"]
    assert not list(learning.learned_variants(target, {**policy, "version": 1}))
    for unsafe in ["r[0]", "r[key]", "r[n()]", "r['meta']['cap']", "r.get('cap')"]:
        before = f"def solve(r, n, key): return n < {unsafe}"
        assert learning.discover(before, before.replace("<", "<=")) is None


def test_reducer_fields_keep_only_the_target_field_and_scope():
    source1 = "def solve(row): return sum(row['alarms'])"
    source2 = "def solve(row): return sum(row['tickets'])"
    donors = [experience(name, code, code.replace("sum(", "len(")) for name, code in [("a", source1), ("b", source2)]]
    policy = learning.learn(donors)
    target = "def solve(x): return sum(x['hits'])"
    edit, = learning.learned_variants(target, policy)
    assert edit["after"] == "len(x['hits'])"
    assert not learning.discover(source1, source1.replace("sum(row['alarms'])", "len(row['different'])"))
    assert not list(learning.learned_variants("def solve(x, str): return sum(x['hits'])", policy))
    assert not list(learning.learned_variants("def solve(x, dict): return sum(x['hits'])", policy))


def test_fields_evaluate_custom_receivers_once_and_preserve_unsupported_values_in_wasi():
    import os
    from training.experiments.fieldwork.guest import Guest

    sdk = os.environ.get("HIVE_FIELDWORK_WASI")
    if not sdk:
        pytest.skip("set HIVE_FIELDWORK_WASI for the CPU WebAssembly integration test")
    donors = [experience(label, code, code.replace("<", "<=")) for label, code in [
        ("orders", "def solve(r, z): return r['units'] < z"), ("lines", "def solve(val, bound): return val < bound")]]
    target = """def solve(packet):
    calls = []
    class LoggingDict(dict):
        def __getitem__(self, key):
            calls.append(key)
            return super().__getitem__(key)
    class Key:
        def __hash__(self):
            return hash("num")
        def __eq__(self, other):
            calls.append(other)
            return other == "num"
    if packet == "subclass":
        data = LoggingDict(num=1, cap=1)
    elif packet == "foreign_key":
        data = {Key(): 1, "cap": 1}
    else:
        data = packet
    outcome = data["num"] < data["cap"]
    return [outcome, calls]
"""
    edit, = learning.learned_variants(target, learning.learn(donors))
    inputs = [{"num": 1, "cap": 1}, {"num": 1.0, "cap": 1}, {"num": "a", "cap": "a"},
              "subclass", "foreign_key", {"cap": 2}]
    guest = Guest(sdk)
    originals, _, _ = guest.run(target, inputs)
    result, _, _ = guest.run(edit["source"], inputs)
    assert originals[0] == {"value": [False, []]} and result[0] == {"value": [True, []]}
    assert result[1:] == originals[1:]
    assert result[3] == {"value": [False, ["num", "cap"]]} and result[4] == {"value": [False, ["num"]]}
    assert "KeyError" in result[-1]["error"]


def test_three_methods_share_one_budget_and_report_their_origin():
    program = """import json
def solve(row):
    data = json.loads(row)
    a, b, d = data['a'], data['b'], data['d']
    nums = data['nums']
    return a*b//d + sum(nums)
"""
    seen = []
    def accepts_decoded(candidate, examples):
        seen.append(candidate)
        return len(examples) if "if type(row) is dict" in candidate else 0
    policy = learning.learn(bank())
    for cap in (1, 2, 3):
        seen.clear()
        winner = learning.select(program, [0], accepts_decoded, cap, original_passed=0, policy=policy)
        assert len(seen) == cap
        if cap < 3:
            assert winner is None
        else:
            assert winner["method"] == "decoded_input" and winner["support"] == 0
            assert "len(nums)" in seen[0] and "a * (b // d)" in seen[1]
    static = learning.select(program, [0], accepts_decoded, 2, original_passed=0, policy=learning.learn([]))
    assert static["method"] == "decoded_input" and static["tried"] == 2
    a, b = bank()
    assert learning.learn([a, {**b, "decoded_input_repair": {}}])["rules"] == []
