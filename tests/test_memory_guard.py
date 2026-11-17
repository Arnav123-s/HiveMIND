"""The memory guard (training/grow.MemoryGuard): before each pass a row's need (pieces x cost per piece) is set
against the memory available, a row that would leave less than the spare is skipped for that pass and counted, the
cost of a piece is learned upward from the run, and the slice's record carries what was measured. g38 lost 7 of 24
8B slices and g39 5 of 20 to memory; the length formula missed 1.5-1.9 GB."""
import json
import random
from types import SimpleNamespace

import pytest

from training import grow

MB, GB = 2**20, 2**30


class FakePsutil:
    """psutil as the guard reads it: the memory available and the swap used are whatever the test says."""

    def __init__(self, available, swap=0):
        self.avail, self.used = available, swap

    def virtual_memory(self):
        return SimpleNamespace(available=self.avail, total=16 * GB)

    def swap_memory(self):
        return SimpleNamespace(used=self.used)


def test_a_row_that_would_not_fit_is_skipped_and_counted_by_subject():
    ps = FakePsutil(2 * GB)
    g = grow.MemoryGuard(1 * MB, spare_gb=1.0, psutil=ps, every=0)
    assert g.admit(500, "short")  # 2 GB - 0.5 GB leaves 1.5 GB
    assert not g.admit(1100, "long")  # would leave 0.9 GB
    assert not g.admit(1100, "long")
    ps.avail = 3 * GB
    assert g.admit(1100, "long")  # with more memory free the same row fits
    rec = g.record()
    assert rec["rows_skipped"] == 2 and rec["skipped_by_subject"] == {"long": 2}
    assert rec["min_available_gb"] == 2.0 and rec["cost_per_piece_mb"] == 1.0


def test_the_cost_of_a_piece_is_learned_upward_from_the_run_and_never_falls_under_the_formula():
    ps = FakePsutil(6 * GB)
    g = grow.MemoryGuard(1 * MB, spare_gb=1.0, psutil=ps, every=0)

    def one_pass(pieces, drop, keep=0):
        g.begin()
        ps.avail -= drop  # the pass at its peak
        g.sample()
        ps.avail += drop - keep  # what it kept for good (a scratch buffer, the optimizer's state) is not a row's cost
        g.end(pieces)

    one_pass(1000, 500 * MB)  # less than the formula's: the formula stands
    assert g.cost == 1 * MB
    one_pass(1000, 3000 * MB, keep=800 * MB)  # 3 GB at the peak, 0.8 of it kept: 2.2 MB a piece
    assert g.cost == pytest.approx(2200 * MB / 1000)
    one_pass(1000, 1000 * MB)  # a lighter pass does not lower it
    assert g.cost == pytest.approx(2200 * MB / 1000)
    one_pass(100, 1000 * MB)  # a short row's fixed part over few pieces does not teach it
    assert g.cost == pytest.approx(2200 * MB / 1000)
    one_pass(1200, 3600 * MB)  # a new longest row that costs more: up
    assert g.cost == pytest.approx(3 * MB)
    ps.used = 3 * GB
    g.sample()
    rec = g.record()
    assert rec["cost_per_piece_mb"] == 3.0 and rec["formula_per_piece_mb"] == 1.0 and rec["swap_peak_gb"] == 3.0
    # the learned cost is what the next row is weighed by: 1000 pieces now need 3 GB
    ps.avail = int(3.5 * GB)
    assert not g.admit(1000, "x") and g.admit(800, "x")


def test_the_spare_comes_from_the_environment(monkeypatch):
    monkeypatch.setenv("HIVE_MEMORY_SPARE_GB", "2.5")
    assert grow.MemoryGuard(1 * MB, psutil=FakePsutil(4 * GB), every=0).spare == 2.5 * GB


def test_a_skipped_row_is_not_met_and_its_subject_waits_for_a_pass_elsewhere():
    st = grow.Study({"a": [0, 1], "b": [2, 3]}, rng=random.Random(1))
    s, idx = st.pick()
    size = sum(len(q) for q in st.queue.values())
    st.skip(s, idx)
    assert st.passes[s] == 0 and st.n == 0 and st.skipped == {s: 1}
    assert sum(len(q) for q in st.queue.values()) == size + 1 and st.queue[s][0] == idx  # back, met last in its subject
    t, _ = st.pick()
    assert t != s  # the other subject is picked
    st.learned(t, 0.5)
    assert not st.waiting
    # a subject that is the only one left is picked again (the train loop stops a run of skips itself)
    one = grow.Study({"a": [0]}, rng=random.Random(1))
    s, idx = one.pick()
    one.skip(s, idx)
    assert one.pick() == ("a", 0)


def _row(i, long):
    task = f"Write the program number {i}."
    out = "```python\n" + ("x = 1\n" * (110 if long else 2)) + f"print({i})\n```"
    return {"task": task, "kind": "long kind" if long else "short kind", "type": "first", "who": "member", "member": 0, "seed": f"m:{i}",
            "messages": [{"role": "system", "content": "Today is 2026-11-17 (Tuesday)."}, {"role": "user", "content": f"TASK: {task}"}], "output": out}


def test_train_skips_the_rows_that_would_not_fit_goes_on_with_the_others_and_records_the_memory(tmp_path, monkeypatch):
    pytest.importorskip("peft")
    from test_held_out import _train
    # the tiny model: 2 layers of 32 values in 32-bit numbers, so the formula's piece is 2 x 32 x 4 x 46 bytes; the
    # memory available leaves room for 600 pieces above the spare: the short rows (~330 pieces) fit, the long (~990) not
    per_piece = 2 * 32 * 4 * 46
    ps = FakePsutil(1 * GB + 600 * per_piece, swap=5 * MB)
    monkeypatch.setitem(__import__("sys").modules, "psutil", ps)
    monkeypatch.setenv("HIVE_MEMORY_SPARE_GB", "1")
    rows = [_row(i, long=i % 3 == 0) for i in range(9)]
    meta, seen = _train(tmp_path, monkeypatch, rows, "")
    trained = [s for s, g in seen if g]
    assert trained and all("print(" in s for s in trained)
    assert not any(s.count("x = 1") > 10 for s in trained)  # no long row was trained on
    assert sum(s.count("x = 1") == 2 for s in trained) == meta["passes"] > 0  # the short rows were, every pass
    mem = meta["memory"]
    assert mem["rows_skipped"] > 0 and set(mem["skipped_by_subject"]) == {"long kind · first"}
    assert mem["min_available_gb"] == round(ps.avail / GB, 2) and mem["swap_peak_gb"] == 0.0
    assert mem["cost_per_piece_mb"] == round(per_piece / MB, 3) and mem["peak_gb"] > 0
    assert json.loads((tmp_path / "out" / "t17+kb.json").read_text())["memory"] == mem  # in the record the slice writes
    by = {x["subject"]: x for x in meta["subjects"]}
    assert by["long kind · first"]["passes"] == 0 and by["short kind · first"]["passes"] == meta["passes"]
