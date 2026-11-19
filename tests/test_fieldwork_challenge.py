"""Bounded rival checks through the real comparison and staged output path."""
import hashlib
import json

import pytest

from training.experiments.fieldwork.challenge import assess


SOURCE = "def solve(x):\n    return len(x['weights'])"
RULE = {"before": "len(v0)", "after": "sum(v0)", "support": 2,
        "id": hashlib.sha256(json.dumps(["len(v0)", "sum(v0)"]).encode()).hexdigest()}


class WeightsGuest:
    """Deterministic stand-in for the count and sum workers, with no evaluation of Python."""
    def run(self, program, inputs, **kwargs):
        operation = sum if "sum(x['weights'])" in program else len
        return [{"value": operation(x["weights"])} for x in inputs], 0, 0


def run(jobs, *, public_weights=(1,), validation_weights=(0, 2), rule=RULE, limit=2):
    spec = {"examples": [{"input": {"weights": public_weights}, "output": len(public_weights)}],
            "validation": [{"input": {"weights": validation_weights}, "output": len(validation_weights)}],
            "jobs": jobs}
    return assess(SOURCE, SOURCE, {"version": 2, "rules": [rule]}, spec, WeightsGuest(),
                  wrap=lambda source: source, limit=limit)


def test_failure_to_distinguish_publicly_can_reveal_a_chained_job():
    jobs = [{"id": "previous", "input": {"weights": []}, "snapshot_file": "n.json"},
            {"id": "current", "input": {"weights": [3]}, "from_job": {"prior": "previous"}}]
    result, staged = run(jobs)
    assert staged is None
    assert result["status"] == "ambiguous"
    assert result["witness"] == {"job": "current", "input": {"weights": [3], "prior": 0}, "answers": [1, 3]}
    assert result["rivals"][0]["validated"] == 1
    assert (result["guest_executions"], result["guest_inputs"]) == (6, 6)


def test_qualified_rivals_can_agree_on_a_whole_batch():
    result, staged = run([{"id": "same", "input": {"weights": [1, 1]}}])
    assert result["status"] == "agreement"
    assert staged == [{"id": "same", "value": 2}]
    assert result["guest_executions"] == 4
    assert "witness" not in result


def test_a_rejected_rival_never_touches_the_jobs():
    result, staged = run([], validation_weights=(4, 5))
    assert result["status"] == "unopposed"
    assert result["rivals"][0]["validated"] == 0
    assert result["guest_executions"] == 2
    assert staged is None


def test_malformed_policy_metadata_cannot_add_rivals():
    for invalid in ({**RULE, "id": "forged"}, {**RULE, "support": 1}, {**RULE, "after": "x.attr"}):
        result, staged = run([], rule=invalid)
        assert result["status"] == "unopposed" and not result["rivals"]
        assert result["guest_executions"] == 0 and staged is None
    with pytest.raises(ValueError, match="between zero and two"):
        run([], limit=3)


def test_semantically_agreeing_upstream_files_can_give_different_chained_inputs():
    class WorkingFilesGuest(WeightsGuest):
        def run(self, program, inputs, **kwargs):
            if all('weights' in item for item in inputs):
                return super().run(program, inputs, **kwargs)
            has_edit = "sum(x['weights'])" in program
            values = [{"reply.json": "1 " if has_edit else "1"} if 'previous' not in item
                      else len(item['previous']['reply.json']) for item in inputs]
            return [{'value': value} for value in values], 0, 0

    jobs = [{"id": "upstream", "input": {}, "snapshot_file": "ref.json", "compare": {"reply.json": "json"}},
            {"id": "next", "input": {}, "from_job": {"previous": "upstream"}}]
    spec = {"examples": [{"input": {"weights": [1]}, "output": 1}],
            "validation": [{"input": {"weights": [0, 2]}, "output": 2}], "jobs": jobs}
    result, staged = assess(SOURCE, SOURCE, {"version": 2, "rules": [RULE]}, spec, WorkingFilesGuest(),
                            wrap=lambda source: source)
    assert staged is None
    assert result["witness"] == {"job": "next", "input": {"previous": {"reply.json": "1"}},
                                 "rival_input": {"previous": {"reply.json": "1 "}}, "answers": [1, 2]}


@pytest.mark.parametrize(("bad_worker", "value"), [("primary", float("nan")), ("rival", float("inf")),
                                                   ("both", float("-inf"))])
def test_nonfinite_job_results_withhold_without_a_witness(bad_worker, value):
    class NonfiniteGuest(WeightsGuest):
        def run(self, program, inputs, **kwargs):
            if not inputs[0].get("on_job"):
                return super().run(program, inputs, **kwargs)
            role = "rival" if "sum(x['weights'])" in program else "primary"
            total = value if bad_worker in (role, "both") else 1
            return [{"value": {"totals": [total]}}], 0, 0

    spec = {"examples": [{"input": {"weights": [1]}, "output": 1}],
            "validation": [{"input": {"weights": [2, 0]}, "output": 2}],
            "jobs": [{"id": "new", "input": {"weights": [3], "on_job": True}}]}
    result, staged = assess(SOURCE, SOURCE, {"version": 2, "rules": [RULE]}, spec, NonfiniteGuest(),
                            wrap=lambda source: source)
    assert staged is None and "witness" not in result
    assert result["status"] == "inconclusive"
    assert "Job new failed" in result["reason"]
    json.dumps(result, allow_nan=False)
