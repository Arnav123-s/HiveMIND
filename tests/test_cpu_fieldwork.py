import ctypes.util
import json
import os
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

from training.experiments.fieldwork import cases
from training.experiments.fieldwork.algorithm_school import teach
from training.experiments.fieldwork.campaign import fingerprint
from training.experiments.fieldwork.discovery import atmosphere, drive, identify
from training.experiments.fieldwork.grade import digest, numbers
from training.experiments.fieldwork.guest import Guest, least_squares
from training.experiments.fieldwork.induction import align, grouped
from training.experiments.fieldwork.numeric_guest import NumericGuest
from training.experiments.fieldwork.observatory import files, reference
from training.experiments.fieldwork.strategy_feedback import feedback_sets, new_routes
from training.experiments.fieldwork.work import finish_files, load_bank, matches, work


def test_private_graph_and_scheduling_inputs_are_disjoint_from_teaching():
    for name in ("roster", "ferry"):
        seen = set()
        for split in ("public", "promotion", "exam", "confirmation"):
            bank = cases.static_cases(name, split)
            ids = {digest(x) for x, _ in bank}
            assert len(ids) == len(bank) and not (ids & seen)
            seen.update(ids)
    assert cases.bookings([[0, 2, -4, 1], [0, 2, -4, 1]], 0, True) == [-4, 2]
    x = dict(n=2, src=0, dst=1, start=0, lay=[0, 0], edges=[[0, 1, 0, 5, 10, 2]])
    assert cases.ferry_reference(x) == [2, 0]


def test_feedback_varies_one_rule_and_fresh_grading_routes_are_disjoint():
    prompts = feedback_sets()
    matched = prompts["matched"]
    assert len({digest({k: v for k, v in x.items() if k != "lay"}) for x in matched}) == 1
    assert [cases.ferry_reference(x) for x in matched] == [[10, 0], [10, 1], [10, 1]]
    seen = {digest(x) for x in matched}
    for split in cases.SEEDS:
        seen.update(digest(x) for x, _ in cases.static_cases("ferry", split))
    fresh = new_routes()
    ids = {digest(x) for x, _, _ in fresh}
    assert len(fresh) == len(ids) == 48 and ids.isdisjoint(seen)
    assert Counter(expected[1] for _, expected, _ in fresh) == {None: 16, 0: 16, 1: 16}


def test_school_learns_boundary_with_an_extra_observation_then_compiles_graph():
    code, width, questions = align(cases.static_cases("departure", "public"))
    assert width == 1 and len(questions) == 1 and len(set(questions[0]["competing"])) > 1
    grouper, count, _ = grouped(cases.static_cases("version", "public"))
    assert count == 1 and grouper
    bank = [dict(task="departure", admitted=True, source=code, digest=fingerprint(code))]
    for name in ("ferry", "roster"):
        trained = teach(name, bank)
        scope = {"least_squares": least_squares}
        exec(trained["source"], scope)
        assert all(scope["solve"](x) == y for x, y in cases.static_cases(name, "confirmation"))


def test_climate_forecasts_only_future_and_thermal_uses_fresh_reset():
    bank = cases.climate_cases("exam")
    for x, y in bank:
        assert max(r[0] for r in x["history"]) < min(r[0] for r in x["future"])
        assert len(y["y"]) == len(x["future"]) == 24
    x, _ = bank[0]
    f = atmosphere(x, False)
    assert 1.5 < f["trend"] < 2.7 and f["peak_month"] in (4, 5, 6)
    u = drive(48)
    w = cases.make_thermal(75131, 1)[0]
    output, model = identify(u, cases.response(w, u, True), w[2])
    assert model and np.sqrt(np.mean((np.asarray(output) - cases.response(w, w[2])) ** 2)) < 0.08
    assert not numbers([10**999], 1) and not numbers([True], 1)


def test_receipted_custom_work_resumes_without_redispatch_and_quarantines_failed_validation(tmp_path):
    pytest.importorskip("numpy")
    if not ctypes.util.find_library("seccomp"):
        pytest.skip("native Linux CPU guest unavailable")
    g = NumericGuest()
    attempts = []

    def emit(task, prefix, prior):
        attempts.append((task.text, prefix, prior))
        if len(attempts) == 2:
            raise InterruptedError("interrupted before reply")
        return {"source": "def solve(x): return " + ("0" if len(attempts) == 1 else "x*2"), "usage": {}}

    spec = dict(
        name="double",
        task="Return twice this integer",
        examples=[{"input": 4, "output": 8}],
        validation=[{"input": 3, "output": 6}],
        jobs=[dict(id="trial", input=11)],
    )
    out, bank = tmp_path / "run", tmp_path / "bank"
    with pytest.raises(InterruptedError):
        work(spec, g, emit, out, bank)
    result = work(spec, g, emit, out, bank)
    assert result["validated"] == 1 and result["jobs"][0]["value"] == 22 and len(attempts) == 3
    assert work(spec, g, emit, out, bank) == result and len(attempts) == 3
    assert len(load_bank(bank)) == 1
    (bank / "damaged.json").write_text("{")
    assert len(load_bank(bank)) == 1
    with pytest.raises(ValueError, match="different work order"):
        work(dict(spec, task="Something else"), g, emit, out, bank)
    failed = work(
        dict(spec, validation=[{"input": 3, "output": 7}]), g, emit, tmp_path / "failed", tmp_path / "other"
    )
    assert failed["validated"] == 0 and failed["jobs"] == [] and not (tmp_path / "other").exists()


def test_files_must_match_contract_and_retries_preserve_content(tmp_path):
    value = files([[1, 3], [5, 7]])
    assert json.loads(value["audit.json"])["longest"] == [1, 3]
    assert matches(
        value,
        dict(value, **{"audit.json": json.dumps({"longest": [1, 3], "covered": 4}, indent=2)}),
        {"audit.json": "json", "coverage.csv": "csv"},
    )
    names = list(value)
    finish_files(tmp_path, "night", value, names)
    finish_files(tmp_path, "night", value, names)
    with pytest.raises(FileExistsError):
        finish_files(tmp_path, "night", dict(value, **{"audit.json": "{}"}), names)
    with pytest.raises(ValueError):
        finish_files(tmp_path, "later", {"../report": "bad"}, ["../report"])
    assert reference(
        dict(window=[0, 7], quorum=2, records=[["A", 0, 4], ["A", 1, 6], ["B", 3, 5]])
    ) == files([[3, 5]])


def test_wasi_guest_runs_with_only_public_input_and_stdlib():
    root = os.environ.get("HIVE_FIELDWORK_WASI")
    if not root:
        pytest.skip("set HIVE_FIELDWORK_WASI for the CPU WebAssembly integration test")
    pytest.importorskip("wasmtime")
    guest = Guest(Path(root))
    rows, used, _ = guest.run(
        "import statistics\ndef solve(x): return statistics.mean(x)", [[1, 4]], fuel=5_000_000_000
    )
    assert rows == [{"value": 2.5}] and used > 0
    rows, _, _ = guest.run(
        "def solve(x): return open('/workspace/private-exam').read()", [{}], fuel=5_000_000_000
    )
    assert "error" in rows[0]


def test_worker_reuses_qualified_source_on_fresh_jobs_without_inference(tmp_path):
    from team.tools.source import extract_code

    class Doubler:
        def run(self, program, inputs, fuel):
            return [{"value": 2 * x} for x in inputs], 0, 0

    source = "def solve(x): return 2*x"
    bank = tmp_path / "bank"
    bank.mkdir()
    key = fingerprint(source)
    contract = "Double the measured integer."
    member = dict(task="double", description=contract, source=source, digest=key, validation=4)
    (bank / (key + ".json")).write_text(json.dumps(member))
    spec = dict(
        name="double",
        task=contract,
        examples=[dict(input=7, output=14)],
        validation=[dict(input=8, output=16)],
        jobs=[dict(id="fresh", input=19)],
    )

    def unexpected(*args):
        pytest.fail("qualified contract should need zero model calls")

    result = work(spec, Doubler(), unexpected, tmp_path / "fresh", bank)
    assert result["attempts"][0]["stop"] == "verified_reuse"
    assert result["jobs"] == [{"id": "fresh", "value": 38}]
    assert json.loads((bank / (key + ".json")).read_text()) == member
    assert extract_code("```python\ndef solve(x): return x") == "def solve(x): return x"
    assert extract_code("```") == ""


def test_recover_phase_from_a_broken_complete_program():
    from training.experiments.fieldwork.stages import fragments

    source = """def solve(x):
    kept = []
    for value in x['events']:
        kept.append(value)
    later = x['snapshot']
    return {'report': later}
"""
    x = {"phase": "intake", "events": [3, 1, 2]}
    solutions = []
    for explanation, code in fragments(source, "intake", {"kept": [1, 2, 3]}):
        scope = {}
        exec(code, scope)
        try:
            if scope["solve"](x) == {"kept": [1, 2, 3]}:
                solutions.append(explanation)
        except KeyError:
            pass
    assert solutions == ["return after statement 2, sorted lists=True"]


def test_new_work_order_reopens_a_declared_snapshot_and_delivers_the_late_request(tmp_path):
    from training.experiments.fieldwork.work import deliver

    class Recorder:
        def __init__(self):
            self.calls = []

        def run(self, program, inputs, fuel):
            self.calls.append(inputs)
            x = inputs[0]
            value = (
                {"value": x["observation"]}
                if "observation" in x
                else {"report.txt": str(x["state"]["value"])}
            )
            return [{"value": value}], 0, 0

    jobs = [
        dict(id="read", input={"observation": 12}, snapshot_file="state.json"),
        dict(id="report", input={}, from_job={"state": "read"}, files=["report.txt"]),
    ]
    recorder = Recorder()
    completed = deliver(recorder, "", jobs, tmp_path)
    assert (tmp_path / "report" / "report.txt").read_text() == "12" and len(recorder.calls) == 2
    assert json.loads((tmp_path / "read" / "state.json").read_bytes()) == recorder.calls[1][0]["state"]
    assert deliver(recorder, "", jobs, tmp_path) == completed
    broken = deliver(recorder, "", [dict(jobs[1], id="missing", from_job={"state": "unknown"})], tmp_path)
    assert "error" in broken[0] and not (tmp_path / "missing").exists()


def test_reporting_school_uses_a_probe_to_identify_an_unseen_tie_rule():
    from training.experiments.fieldwork.report_school import teach as report
    from training.experiments.fieldwork.stages import examples

    got = report(examples()["revise"])
    assert got["family_size"] == 768 and got["survivors_before_probes"] == 2 and len(got["probes"]) == 1
    scope = {}
    exec(got["source"], scope)
    result = scope["solve"](
        dict(
            snapshot={"kept": [["z", 1, "V", 30], ["u", 1, "B", 30]], "conflicts": ["e"]},
            exclude="Other",
            minimum=1,
        )
    )
    assert result["summary.csv"] == "zone,count,grams\nB,1,30\nV,1,30\n"
    assert json.loads(result["audit.json"]) == {"conflicts": ["e"], "kept_count": 2}


def test_verified_receipt_restores_missing_files_and_preserves_an_operator_edit(tmp_path):
    from training.experiments.fieldwork.work import saved_receipt

    order = dict(
        jobs=[
            dict(id="first", snapshot_file="state.json"),
            dict(id="second", from_job={"state": "first"}, files=["a.csv", "b.txt"]),
        ]
    )
    receipt = dict(
        jobs=[
            {"id": "first", "value": [4, 7]},
            {"id": "second", "value": {"a.csv": "a\n", "b.txt": "value\n"}},
        ]
    )
    (tmp_path / "receipt.json").write_text(json.dumps(receipt))
    assert saved_receipt(tmp_path, order) == receipt
    target = tmp_path / "second"
    (target / "a.csv").unlink()
    assert saved_receipt(tmp_path, order) == receipt and (target / "a.csv").read_text() == "a\n"
    (target / "b.txt").write_text("operator")
    assert (
        "error" in saved_receipt(tmp_path, order)["jobs"][-1]
        and (target / "b.txt").read_text() == "operator"
    )


def test_generic_csv_and_aggregation_repairs_on_an_independent_work_order():
    from training.experiments.fieldwork.phase_repair import mutations, oracle

    source = """def solve(x):
    count=sum(v[1] for v in x)
    return f'{x[0][0]},{count}'
"""
    variants = dict(mutations(source))
    assert len(variants) == 2
    counted = next(code for label, code in variants.items() if label.startswith("sum"))
    escaped = next(code for label, code in mutations(counted) if label.startswith("comma"))
    scope = {}
    exec(escaped, scope)
    assert scope["solve"]([["A, B", 5], ["C", 2]]) == '"A, B",2'
    snapshot, files = oracle([["k", 2, "A, B", 5, "ok"], ["k", 2, "A, B", 5, "ok"]], "Elsewhere", 1)
    assert snapshot["kept"] == [["k", 2, "A, B", 5]] and '"A, B",1,5' in files["summary.csv"]
