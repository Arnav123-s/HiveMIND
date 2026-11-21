import json
from pathlib import Path

import pytest
import yaml

from training import gate_look

ROOT = Path(__file__).resolve().parents[1]


def grades(root, arm, slot, right):
    seed = 20_000_000 + 10 * 99 + slot
    shard = root / f"gate-{arm}-{slot}"
    shard.mkdir(exist_ok=True)
    path = shard / f"{seed}_mixed.json"
    tasks = [{"id": f"e{seed}_{i:02d}", "kind": "a sum in words", "task": f"case {i}", "ok": i < right} for i in range(8)]
    data = {"summary": {"level": "mixed", "seed": seed, "code": "abcdef1", "tasks": 8, "passed": right, "minutes": 1},
            "tasks": tasks}
    path.write_text(json.dumps(data))
    return path


@pytest.mark.parametrize("before,after,stop", [(1, 3, True), (3, 1, True), (4, 5, False), (1, 1, False)])
def test_optional_gate_waits_for_decisive_verified_pairs(tmp_path, before, after, stop):
    for slot in range(1, 5):
        grades(tmp_path, "before", slot, before)
        grades(tmp_path, "after", slot, after)
    assert gate_look.look(tmp_path, 99, 4)["stop"] is stop
    assert not gate_look.look(tmp_path, 100, 4)["stop"]


def test_missing_or_different_questions_always_request_the_rest(tmp_path):
    for slot in range(1, 7):
        grades(tmp_path, "before", slot, 0)
        path = grades(tmp_path, "after", slot, 8)
    assert gate_look.look(tmp_path, 99, 6)["stop"]
    data = json.loads(path.read_text())
    data["tasks"][0]["task"] += " different prompt"
    path.write_text(json.dumps(data))
    assert not gate_look.look(tmp_path, 99, 6)["stop"]
    path.unlink()
    assert not gate_look.look(tmp_path, 99, 6)["stop"]


def test_frozen_g45_to_g55_pairs_never_cross_the_boundary():
    archive = ROOT / "training/experiments/astra_cpu/handoff_audit"
    ledger = json.loads((archive / "paired.json").read_text())
    expected = json.loads((archive / "results.json").read_text())
    paired = 0
    for gen, rows in ledger.items():
        if any(r["matched"] != 8 for r in rows):
            assert gen == "g45" and expected[gen]["matched"] == 63
            continue
        for seats in (4, 6):
            prefix = rows[:seats]
            assert not gate_look.decisive(sum(r["wins"] for r in prefix), sum(r["losses"] for r in prefix))
        assert expected[gen]["lr"]["seeds"] == 8 and expected[gen]["lr"]["agrees"]
        paired += sum(r["matched"] for r in rows)
    assert "g46" not in ledger and paired == 576


def test_future_jobs_only_start_if_previous_look_requested_more():
    jobs = yaml.safe_load((ROOT / ".github/workflows/grow.yml").read_text())["jobs"]
    initial = jobs["gate"]
    assert "needs.plan.outputs.grow && vars.HIVE_GATE_SPRT == '1' && '[1,2,3,4]'" in initial["strategy"]["matrix"]["seed"]
    for look, tail, seeds in (("gate_look4", "gate_5_6", [5, 6]), ("gate_look6", "gate_7_8", [7, 8])):
        assert look in jobs[tail]["needs"] and f"needs.{look}.outputs.stop != '1'" in jobs[tail]["if"]
        assert jobs[tail]["steps"] == initial["steps"]
        assert jobs[tail]["strategy"]["matrix"] == {"arm": ["before", "after"], "seed": seeds, "part": ["fresh"]}
        assert tail in jobs["record"]["needs"]
