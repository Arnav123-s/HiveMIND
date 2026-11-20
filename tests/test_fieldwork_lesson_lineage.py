"""An independent repair lesson requires the actual writer predecessor and fresh qualification data."""

from training.experiments.fieldwork import repair_learning
from training.experiments.fieldwork import work as fw


class ArithmeticGuest:
    """Known programs for the controlled writer; all are checked via the real work-order flow."""

    def run(self, program, inputs, fuel):
        expression = program.strip().split("return ")[-1]
        if expression == "0":
            return [{"value": 0} for x in inputs], 0, 0
        sign = expression.split()[1]
        assert sign in ("+", "-")
        return [{"value": x + 1 if sign == "+" else x - 1} for x in inputs], 0, 0


def correction(argument, sign):
    return f"def solve({argument}):\n    return {argument} {sign} 1"


def order(name, description, validation):
    def examples(inputs):
        return [dict(input=x, output=x + 1) for x in inputs]
    return dict(name=name, task=description, examples=examples([-1, 1]),
                validation=examples(validation), jobs=[dict(id="fresh", input=10)])


def run_proposals(out, bank, spec, sources):
    seen = []
    proposals = iter(sources)

    def writer(task, prefix, prior):
        seen.append(prior[0] if prior is not None else None)
        return {"source": next(proposals), "usage": {}}

    receipt = fw.work(spec, ArithmeticGuest(), writer, out, bank, rounds=len(sources))
    assert receipt["jobs"] == [{"id": "fresh", "value": 11}]
    return receipt, seen


def test_unshown_sibling_cannot_become_the_predecessor_of_a_success(tmp_path):
    zero = "def solve(n):\n    return 0"
    wrong, right = correction("n", "-"), correction("n", "+")
    spec = order("levels", "Scale instrument levels", [3, 4])
    bank = tmp_path / "bank"
    result, seen = run_proposals(tmp_path / "work", bank, spec, [zero, wrong, right])
    # The constant passes one public case. The second proposal passes neither,
    # so the writer sees the constant's feedback again on the successful attempt.
    assert seen == [None, zero, zero]
    assert repair_learning.discover(wrong, right) and repair_learning.discover(zero, right) is None
    assert not result.get("repair_experience")
    assert not fw.load_bank(bank)[0].get("repair_experience")


def test_same_private_corpus_as_two_aliases_supplies_one_independent_vote(tmp_path):
    bank = tmp_path / "bank"
    visits = [
        ("dials", "Advance the dial", "dial", [3, 4]),
        ("tallies", "Increment the tally", "count", [4, 3, 4]),
        ("heights", "Raise the surface", "height", [17, 41]),
    ]
    events = []
    for name, description, argument, validation in visits:
        wrong, right = correction(argument, "-"), correction(argument, "+")
        receipt, seen = run_proposals(tmp_path / name, bank, order(name, description, validation), [wrong, right])
        assert seen == [None, wrong]
        event, = receipt["repair_experience"]
        assert event["parent"] == fw.fingerprint(wrong)
        events.append(event)
        rules = repair_learning.learn(fw.load_bank(bank))["rules"]
        if name != "heights":
            assert rules == []
        else:
            assert len(rules) == 1 and rules[0]["support"] == 2
    assert events[0]["validation_set"] == events[1]["validation_set"]
    assert events[0]["validation_set"] != events[2]["validation_set"]


def test_validation_input_repeated_from_writer_examples_cannot_teach(tmp_path):
    bank = tmp_path / "bank"
    spec = order("volume", "Increase meter volume", [1, 42])
    wrong, right = correction("volume", "-"), correction("volume", "+")
    receipt, seen = run_proposals(tmp_path / "work", bank, spec, [wrong, right])
    assert seen == [None, wrong]
    assert not receipt.get("repair_experience")
    assert receipt["admission"] == "overlapping_checks"
    assert not fw.load_bank(bank)


def test_same_writer_predecessor_under_two_contracts_supplies_one_vote(tmp_path):
    bank = tmp_path / "bank"
    wrong, right = correction("reading", "-"), correction("reading", "+")
    for name, description, validation in (("dials", "Advance the dial", [6, 9]),
                                          ("gauges", "Increment the gauge", [27, 42])):
        receipt, seen = run_proposals(tmp_path / name, bank, order(name, description, validation), [wrong, right])
        assert seen == [None, wrong] and receipt["repair_experience"][0]["parent"] == fw.fingerprint(wrong)
    assert len(fw.load_bank(bank)) == 2
    assert repair_learning.learn(fw.load_bank(bank))["rules"] == []
