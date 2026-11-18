import json
import os
import shutil
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
torch = pytest.importorskip("torch")

from team.cells import tiny
from training import scratch
from training.experiments import hive_continual_reward as rl
from training.experiments import hive_kernel_bench as bench
from training.experiments import hive_signals as signals


def test_served_scratch_brain_keeps_exact_logits_and_reloads_changed_checkpoint(tmp_path, monkeypatch):
    monkeypatch.setattr(scratch, "HOME", tmp_path)
    monkeypatch.setattr(tiny, "HOME", tmp_path)
    monkeypatch.setattr(tiny, "_state", {})
    monkeypatch.setattr(scratch, "tokenizer", lambda: None)
    (tmp_path / "stem.json").write_text(json.dumps({"bit": True, "dim": 16, "layers": 1, "heads": 2}))
    (tmp_path / "brain.json").write_text(json.dumps({"jobs": {"job": ["a", "b"]}}))
    torch.manual_seed(836)
    baseline = scratch.Brain({"job": 2}).eval()
    ids, last = torch.tensor([[3, 9, 8], [8, 2, 4]]), torch.tensor([2, 2])
    path = tmp_path / "brain.pt"
    for version in (1, 2):
        with torch.no_grad():
            baseline.first["job"].bias.add_(1.)
            expected = baseline("job", ids, last)[0]
            torch.save(baseline.state_dict(), path)
            os.utime(path, (1000 + version, 1000 + version))
            served = tiny._brain()["model"]
            assert isinstance(served.trunk.blocks[0].qkv, scratch.FrozenBitLinear)
            assert isinstance(baseline.trunk.blocks[0].qkv, scratch.BitLinear)
            assert torch.equal(served("job", ids, last)[0], expected)


@pytest.mark.skipif(shutil.which("c++") is None, reason="kernel test needs a C++17 compiler")
def test_ternary_integer_kernels_cover_extreme_signed_values_and_tails(tmp_path):
    assert bench.verify(bench.library(tmp_path)) == 945


def test_corrupted_reward_is_independent_of_real_outcome():
    n = 4 * rl.WINDOW
    stations = np.zeros(n, dtype=int)
    role = np.ones(n, dtype=int)
    pred = np.zeros((n, 2), dtype=bool)
    truth = np.ones(n, dtype=bool)
    data = (stations, role, pred, truth, pred, truth, np.zeros((n, 2)))
    clean = rl.play(data, "oracle", False)
    faulty = rl.play(data, "oracle", True)
    assert clean["all"]["pass"] == faulty["all"]["pass"] == 0.
    assert clean["all"]["reported_pass"] == 0.
    assert faulty["all"]["reported_pass"] == 0.75


def test_cell_messages_bind_the_code_to_task_sender_role_and_version():
    frame = signals.FRAME.pack(22, 3, 1, 0, 9)
    assert signals.receive(frame, 22, 3, 1, 0) == 9
    for context in ((23, 3, 1, 0), (22, 4, 1, 0), (22, 3, 2, 0), (22, 3, 1, 1)):
        assert signals.receive(frame, *context) is None
    assert signals.receive(frame[:-1], 22, 3, 1, 0) is None
    assert signals.receive(signals.FRAME.pack(22, 3, 1, 0, 17), 22, 3, 1, 0) is None
    path = Path(__file__).resolve().parents[1] / "training/reports/rule_lab/engrams/four-bit-pair.npz"
    reader = signals.load_reader(path)
    a = signals.emit(signals.load_sender(path, 0), 0, 47, [1., 1., 0., 0.])
    b = signals.emit(signals.load_sender(path, 1), 1, 47, [-3., 1., 0., 0.])
    assert signals.interpret(reader, 48, [a, b]) is None
    assert signals.interpret(reader, 47, [a]) is None
    assert signals.interpret(reader, 47, [b, a, a]) == signals.interpret(reader, 47, [a, b])
    task, sender, schema, role, code = signals.FRAME.unpack(a)
    conflict = signals.FRAME.pack(task, sender, schema, role, 15 - code)
    with pytest.raises(ValueError, match="conflicting"):
        signals.interpret(reader, 47, [a, conflict, b])


def test_subhive_link_counts_include_reply_paths_and_local_replicas_survive_root_loss():
    assert [signals.hops(0, n) for n in (0, 1, 4, 16)] == [0, 2, 4, 6]
    for row in signals.subhives().values():
        cost = row["mean_directed_link_transmissions"]
        assert cost["local_replicas"] < cost["global_addresses"] < cost["broadcast"]
        assert row["root_outage_reachable_fraction"]["local_replicas"] == 1
        assert row["root_outage_reachable_fraction"]["global_addresses"] == 0
