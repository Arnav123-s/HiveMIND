"""Finite worker admission and normal practice-to-chat routing."""
import json

import pytest

from team import bank_admit as ba, saved
from training import exam
from training.experiments.fieldwork import work


class Guest:
    """Only for source written in these tests. The archive replay runs workers in real WASI."""

    def __init__(self):
        self.calls = 0

    def run(self, program, inputs, fuel=None):
        self.calls += 1
        scope = {}
        exec(program, scope)
        outputs = []
        for sample in inputs:
            try:
                outputs.append({"value": scope["solve"](sample)})
            except ValueError:
                outputs.append({"error": "outside verified domain"})
        return outputs, 0, 0


PROGRAM = "def double(n):\n    return n + n\n"


def specification(lo=0, hi=3):
    return dict(task="double_integer", description="Double the supplied integer.", function="double",
                arguments=[dict(name="n", min=lo, max=hi)], outputs=[2*n for n in range(lo, hi + 1)])


def test_versions_keep_their_verified_ranges_and_decline_disagreement(tmp_path):
    guest = Guest()
    def add(src, spec):
        return ba.admit(src, spec, tmp_path, guest, origin={"test": True})["digest"]
    def ask(n):
        return saved.answer("Double the integer " + json.dumps({"n": n}), bank=tmp_path, runner=guest)
    older = add(PROGRAM, specification())
    assert add(PROGRAM, specification()) == older and guest.calls == 1
    newer = add(PROGRAM, specification(2, 5))
    assert older != newer
    assert ask(0)["methods"] == [older] and ask(5)["methods"] == [newer]
    assert sorted(ask(2)["methods"]) == sorted([older, newer])
    for value in [True, 2.0, -1, "3", [2]]:
        assert ask(value)["status"] == "missing"
    assert saved.answer("Double the integer 5", bank=tmp_path, runner=guest)["value"] == 10
    changed = specification(2, 2)
    changed["outputs"] = [2]
    add("def double(n): return n", changed)
    assert ask(2)["status"] == "ambiguous"
    assert ask(4)["value"] == 8


def test_guard_matches_domain_and_never_executes_surrounding_program(tmp_path):
    axes = [dict(name="a", values=[True, 1, None, ["x"]]), dict(name="b", min=-1, max=0)]
    expected = [[a, b] for a in [True, 1, None, ["x"]] for b in [-1, 0]]
    spec = dict(task="pair", description="Pair two values.", function="pair", arguments=axes, outputs=expected)
    source = "raise RuntimeError('outer program ran')\ndef pair(a, *, b): return [a, b]"
    guest = Guest()
    receipt = ba.admit(source, spec, tmp_path, guest, origin={})
    assert receipt["validation"] == 8
    row, = work.load_bank(tmp_path)
    assert "outer program" not in row["source"] and "outputs" not in row
    bad = [{"a": False, "b": 0}, {"a": 1.0, "b": 0}, {"a": 1, "b": True}, {"a": 1, "b": -2},
           {"a": 1}, {"a": None, "b": 0, "c": 2}, None]
    assert all(not ba.applies(axes, value) for value in bad)
    assert all("error" in v for v in guest.run(row["source"], bad)[0])


def test_source_or_metadata_corruption_fails_closed_with_immutable_recovery(tmp_path):
    guest = Guest()
    spec = specification()
    result = ba.admit(PROGRAM, spec, tmp_path, guest, origin={})
    key = result["digest"]
    path = tmp_path / (key + ".json")
    row = json.loads(path.read_text())
    row["arguments"][0]["max"] = 200
    path.write_text(json.dumps(row))
    assert not work.load_bank(tmp_path)
    assert saved.answer("Double integer 90", bank=tmp_path, runner=guest) is None
    assert ba.admit(PROGRAM, spec, tmp_path, guest, origin={}) == result
    intact, = work.load_bank(tmp_path)
    assert intact["arguments"] == spec["arguments"] and len(list(tmp_path.glob("*.json"))) == 2
    recovery = next(p for p in tmp_path.glob("*.json") if p != path)
    recovery.write_text("broken")
    with pytest.raises(ValueError, match="integrity"):
        ba.admit(PROGRAM, spec, tmp_path, guest, origin={})
    assert not work.load_bank(tmp_path)


@pytest.mark.parametrize("arguments", [
    [dict(name="a", min=False, max=4)],
    [dict(name="a", min=0, max=256), dict(name="b", min=0, max=255)],
    [dict(name="a", values=[True, True])], [dict(name="a", values=[float("nan")])],
    [dict(name="a", min=0, max=1), dict(name="a", values=[2])],
])
def test_malformed_contract_is_rejected(arguments):
    with pytest.raises(ValueError):
        ba.fields(arguments)


def test_missing_expected_output_and_worker_errors_never_publish(tmp_path):
    def try_admit(program, spec):
        with pytest.raises(ValueError):
            ba.admit(program, spec, tmp_path, Guest(), origin={})
        assert not list(tmp_path.glob("*.json"))
    spec = specification()
    try_admit(PROGRAM, dict(spec, outputs=[0]))
    try_admit(PROGRAM, dict(spec, outputs=[False, 2, 4, 6]))
    try_admit("def double(n): return n", spec)
    try_admit("def double(n): return private_oracle(n)", spec)
    try_admit("def double(m): return m + m", spec)


def test_normal_practice_entrypoint_only_admits_individually_passing_members(tmp_path, monkeypatch):

    registry = tmp_path / "contracts"
    registry.mkdir()
    (registry / "double.json").write_text(json.dumps(specification()))
    runs, bank = tmp_path / "runs", tmp_path / "bank"
    monkeypatch.setattr(exam, "RUNS", runs)
    monkeypatch.setattr(ba, "runtime", lambda sdk: Guest())
    monkeypatch.setenv("HIVE_BANK", str(bank))
    monkeypatch.setenv("HIVE_BANK_CONTRACTS", str(registry))
    def fake_run(cmd, *args, **kwargs):
        from pathlib import Path
        run = Path(cmd[-1])
        (run / "members").mkdir()
        for seat, answer in [(1, "wrong"), (2, "confirmed")]:
            data = dict(program=PROGRAM, who="archived" + str(seat), answer=answer)
            (run / "members" / f"member{seat}.json").write_text(json.dumps(data))
        return 0, ""
    monkeypatch.setattr(exam, "run_task", fake_run)
    def sit(tag):
        return exam.sit_one(tag, "job", "a question", lambda _, report: (report == "confirmed", ""), tmp_path)
    assert "bank_admissions" not in sit("exam_100") and not work.load_bank(bank)
    passed = sit("practice_100")
    assert len(passed["bank_admissions"]) == 1
    row, = work.load_bank(bank)
    assert row["origin"]["member"] == 2
    def offline(*args):
        raise RuntimeError("WASI unavailable")
    monkeypatch.setattr(ba, "runtime", offline)
    partial = sit("practice_102")
    assert partial["bank_admissions"] == [{"unavailable": "WASI unavailable"}]
    assert partial["members"][1]["ok"] and (runs / "practice_102/job/exam.json").exists()
    monkeypatch.delenv("HIVE_BANK_CONTRACTS")
    assert "bank_admissions" not in sit("practice_101")
