import json
import os

import pytest

from training.experiments.fieldwork import practice_import as bridge
from training.experiments.fieldwork import work
from training.experiments.fieldwork.guest import Guest


def sitting(tmp_path, code):
    directory = tmp_path / "practice_10000001" / "h10000001_00"
    members = directory / "members"
    (members / "work").mkdir(parents=True)
    (members / "TASK.md").write_text(bridge.PREFIX + " takes a list of pairs.")
    (members / "work/member1_1.py").write_text(code)
    return directory


def test_recognizes_only_original_hard_practice_and_standalone_submissions(tmp_path):
    outside = tmp_path / "gate_after" / "h10000001_00"
    assert bridge.import_practice(outside, tmp_path / "bank", None)["status"] == "skipped"
    directory = sitting(tmp_path, "import os\nprint('a demonstration only')")
    assert bridge.import_practice(directory, tmp_path / "bank", None)["status"] == "skipped"
    for declaration in ["@decorator\ndef merge(xs): return xs", "def merge(xs=run()): return xs",
                        "def merge(xs: run()): return xs", "def merge(xs): return xs\ndef merge(xs): return []"]:
        assert bridge._function(declaration) is None
    fn = "def merge(xs):\n    return xs"
    assert bridge._function("print('top level')\n" + fn + "\nraise Exception()") == fn
    (directory / "members/TASK.md").write_text("Please create a different module.")
    assert bridge.import_practice(directory, tmp_path / "bank", None)["status"] == "skipped"


def test_reference_connects_touching_points_but_keeps_adjacent_integer_endpoints_separate():
    rows = [[3, 5], [1, 2], [5, 6], [15, 15], [2, 2], [17, 19], [16, 16]]
    assert bridge.reference(rows) == [[1, 2], [3, 6], [15, 15], [16, 16], [17, 19]]
    public = {json.dumps(x) for x, _ in bridge.PUBLIC}
    fresh = bridge.probes(3422225)
    ids = {json.dumps(row["input"]) for row in fresh}
    assert len(ids) == len(fresh) == 72
    assert not ids & public
    assert fresh == bridge.probes(3422225) and fresh != bridge.probes(3422226)


def test_import_ignores_practice_grade_and_rejects_public_memorization_in_real_wasi(tmp_path):
    sdk = os.environ.get("HIVE_FIELDWORK_WASI")
    if not sdk:
        pytest.skip("set HIVE_FIELDWORK_WASI for the CPU WebAssembly integration test")
    good = """def merge(xs):
    out = []
    for lo, hi in sorted(xs):
        if out and lo <= out[-1][1]:
            out[-1][1] = max(out[-1][1], hi)
        else:
            out.append([lo, hi])
    return out
"""
    directory = sitting(tmp_path, good + "\nraise RuntimeError('unrelated top-level code')\n")
    bank, guest = tmp_path / "bank", Guest(sdk)
    receipts = []
    for grade in [True, False]:
        (directory / "exam.json").write_text(json.dumps({"members": [{"member": 1, "ok": grade, "who": "worker"}],
                                                         "ok": grade}))
        receipts.append(bridge.import_practice(directory, bank, guest, seed=29))
    assert receipts[0] == receipts[1] and receipts[0]["status"] == "qualified"
    row, = work.load_bank(bank)
    assert row["practice_origin"]["model"] == "worker"
    result, _, _ = guest.run(row["source"], [[[2, 2], [2, 4]], [[3, 1]], [[True, 2]], [["1", 2]]])
    assert result[0]["value"] == [[2, 4]] and all("error" in r for r in result[1:])
    memo = "def merge(xs):\n    return " + repr({str(x): y for x, y in bridge.PUBLIC}) + ".get(str(xs), [])"
    (directory / "members/work/member1_1.py").write_text(memo)
    r = bridge.import_practice(directory, bank, guest, seed=29)
    assert r["public"] == len(bridge.PUBLIC) and r["status"] == "rejected"
    assert r["validation"] < r["validation_total"] and len(work.load_bank(bank)) == 1


@pytest.mark.parametrize("option,env_bank,matched,expected", [
    (None, "", True, False), (None, "bank", False, False), (None, "bank", True, True),
    ("other-bank", "", True, True), ("off", "bank", True, False)])
def test_grow_practice_optional_hook_uses_only_matching_tasks(tmp_path, monkeypatch, option, env_bank, matched, expected):
    from training import exam, grow

    task = bridge.PREFIX if matched else "Write a different module"
    check = lambda *_: (False, "")
    tid, seed = "h10000023_00", 10000023
    monkeypatch.setenv("HIVE_PRACTICE_BANK", env_bank)
    monkeypatch.setattr(exam, "RUNS", tmp_path / "runs")
    monkeypatch.setattr(exam, "_memory", lambda *_: tmp_path)
    monkeypatch.setattr(exam, "exam", lambda *a, **kw: iter([(tid, "code", "practice", task, check)]))
    monkeypatch.setattr(exam, "sit_one", lambda *a, **kw: {"ok": False, "seconds": 1})
    monkeypatch.setattr(grow, "rows_of", lambda *a: [])
    monkeypatch.setattr(grow, "pair_rows", lambda *a: [])
    monkeypatch.setattr(grow, "remember_failure", lambda *a: None)
    calls = []
    def record(directory, bank, guest):
        calls.append((directory, str(bank)))
        return {"status": "qualified"}
    def guest(path):
        assert expected
        return object()
    monkeypatch.setattr(bridge, "import_practice", record)
    monkeypatch.setattr(bridge, "Guest", guest)
    grow.practice(seed, 1, out=tmp_path / "rows.jsonl", log=lambda *a, **k: None, practice_bank=option)
    saved = json.loads((tmp_path / "practice.json").read_text())["tasks"][0]
    assert saved["ok"] is False
    if expected:
        assert calls == [(exam.RUNS / f"practice_{seed}" / tid, option or env_bank)]
        assert saved["practice_skill"] == {"status": "qualified"}
    else:
        assert not calls and "practice_skill" not in saved
