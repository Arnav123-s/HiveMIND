"""Per-row activation recomputation must preserve the optimizer update and both policy graphs."""
from contextlib import nullcontext
from types import SimpleNamespace

import pytest
import torch

from training import grow


MB = 2**20


def test_gear_admission_keeps_head_spare_and_separate_observed_peaks(tmp_path):
    use = tmp_path / "memory.current"
    use.write_text(str(100 * MB))
    ps = SimpleNamespace(virtual_memory=lambda: SimpleNamespace(available=2000 * MB),
                         swap_memory=lambda: SimpleNamespace(used=0))
    guard = grow.MemoryGuard(10 * MB, psutil=ps, spare_gb=100 * MB / 2**30, every=0,
                             checkpoint_floor=3 * MB, limits=[(use, 1200 * MB)])
    assert guard.row_mode(80, "short", 100 * MB) == "ordinary"
    assert guard.row_mode(100, "long", 100 * MB) == "checkpoint"
    assert guard.row_mode(100, "both", 701 * MB) is None
    assert guard.skips == {"both": 1}
    guard.begin()
    use.write_text(str(700 * MB))
    guard.sample()
    use.write_text(str(100 * MB))
    guard.end(100, "checkpoint")
    assert guard.cost == 10 * MB and guard.checkpoint_cost == 6 * MB
    # The 600 MB measured peak already includes the readout. Its 350 MB is added to the *analytic* floor only.
    use.write_text(str(450 * MB))
    assert guard.row_mode(100, "long", 350 * MB) == "checkpoint"
    use.write_text(str(451 * MB))
    assert guard.row_mode(100, "long", 350 * MB) is None
    assert guard.record()["row_modes"] == {"ordinary": 1, "checkpoint": 2}
    assert guard.skips == {"both": 1, "long": 1}
    use.unlink()
    assert guard.row_mode(1, "unreadable limit", 0) is None


def test_dpo_readout_accounts_for_two_live_policy_graphs_and_one_transient_reference():
    assert grow.row_head_bytes(13, 3) == 13 * 4 * 16
    assert grow.row_head_bytes(13, 3, 7) == 13 * (4 + 8 + 8) * 16
    # A short answer still uses the full head even when its longer counterpart qualifies for chunks.
    assert grow.row_head_bytes(13, 3, 7, lambda n: n + 1 if n <= 5 else 5) == 13 * (4 + 5 + 5) * 16


def test_alternating_forward_and_preference_gears_preserve_deltas_and_frozen_cache(tmp_path):
    from transformers import Qwen3Config, Qwen3ForCausalLM
    from peft import LoraConfig, get_peft_model
    from training.lm_head_loss import answer_nll

    def train(alternate):
        torch.manual_seed(1194)
        config = Qwen3Config(vocab_size=53, hidden_size=32, intermediate_size=64, num_hidden_layers=3,
                             num_attention_heads=2, num_key_value_heads=1, head_dim=16, use_cache=False)
        model = get_peft_model(Qwen3ForCausalLM(config), LoraConfig(r=2, lora_alpha=4, lora_dropout=0.05,
                               layers_to_transform=[1, 2], target_modules=["q_proj", "down_proj"]))
        model.train()
        opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=0.001)
        embeds = model.get_input_embeddings()
        hooks = len(embeds._forward_hooks)
        gear = grow._RowCheckpoints(model, 1) if alternate else None
        prefix = grow._Prefix(model, 1, folder=tmp_path / "prefix") if alternate else None
        right, wrong = torch.randint(1, 53, (1, 20)), torch.randint(1, 53, (1, 16))
        results = []
        for use_gear, preference in [(False, False), (True, True), (False, True), (True, False), (False, False)]:
            if gear:
                gear.set(use_gear)
            cache = prefix if not use_gear else None
            def nll(t):
                with cache.use(t) if cache else nullcontext():
                    return answer_nll(model, t, 6, 3)
            good = nll(right)
            loss = good / 6
            if preference:
                bad = nll(wrong)
                with torch.no_grad(), model.disable_adapter():
                    ref_good, ref_bad = nll(right), nll(wrong)
                loss = loss - torch.nn.functional.logsigmoid(0.1 * (ref_good - good + bad - ref_bad))
            loss.backward()
            opt.step()
            opt.zero_grad()
            results.append(loss.item())
            assert len(embeds._forward_hooks) == hooks
        if gear:
            gear.set(False)
            assert prefix.hits >= 2 and prefix.misses >= 1
            assert not any(layer.gradient_checkpointing for layer in model.get_base_model().model.layers)
            prefix.done()
        return results, torch.cat([p.detach().flatten() for p in model.parameters() if p.requires_grad])

    stock, old_weights = train(False)
    adaptive, new_weights = train(True)
    assert adaptive == pytest.approx(stock, abs=1e-5)
    torch.testing.assert_close(new_weights, old_weights, rtol=1e-5, atol=1e-6)


def test_reclaim_counts_only_eligible_inactive_file_pages(tmp_path):
    usage = tmp_path / "memory.current"
    usage.write_text(str(98 * MB))
    stat = {"inactive_file": 50, "file_dirty": 5, "file_writeback": 2, "file_mapped": 10,
            "shmem": 3, "unevictable": 2, "active_file": 100}
    (tmp_path / "memory.stat").write_text("".join(f"{k} {v * MB}\n" for k, v in stat.items()))
    ps = SimpleNamespace(virtual_memory=lambda: SimpleNamespace(available=90 * MB))
    assert grow._available(ps, [(usage, 100 * MB)]) == 30 * MB
    ps = SimpleNamespace(virtual_memory=lambda: SimpleNamespace(available=7 * MB))
    assert grow._available(ps, [(usage, 100 * MB)]) == 7 * MB


def test_native_training_admits_formerly_pretrimmed_row_and_preserves_validation_limit(tmp_path, monkeypatch):
    import os
    import sys
    from pathlib import Path
    from transformers import Qwen3Config, Qwen3ForCausalLM
    from test_held_out import _tiny, _train
    from test_memory_guard import FakePsutil, _row

    folder = tmp_path / "dna"
    folder.mkdir()
    tokenizer = _tiny(folder)
    # Stored grouped ternary matrices through the actual one-byte loader, autograd and AdamW.
    config = Qwen3Config(vocab_size=len(tokenizer), hidden_size=128, intermediate_size=256, num_hidden_layers=3,
                         num_attention_heads=4, num_key_value_heads=2, head_dim=32, max_position_embeddings=2048)
    model = Qwen3ForCausalLM(config)
    with torch.no_grad():
        for p in model.parameters():
            if p.ndim == 2:
                p.copy_(torch.randint(-1, 2, p.shape) * 0.01)
    model.save_pretrained(folder)
    del model
    per_piece = 3 * 128 * 4 * 46
    ps = FakePsutil(int(1.7 * 2**30) + 421 * per_piece)
    monkeypatch.setitem(sys.modules, "psutil", ps)
    use = tmp_path / "memory.current"
    use.write_text("0")
    monkeypatch.setattr(grow, "_cgroup_limits", lambda: [(use, 8 * 2**30)])
    advised = []
    monkeypatch.setattr(os, "posix_fadvise", lambda fd, offset, size, advice:
                        advised.append((Path(f"/proc/self/fd/{fd}").resolve(), offset, size, advice)), raising=False)
    monkeypatch.setattr(os, "POSIX_FADV_DONTNEED", 4, raising=False)
    monkeypatch.setenv("HIVE_MEMORY_SPARE_GB", "1.68")
    rows = [_row(1, False), _row(2, True), _row(3, True) | {"who": "lesson"}]

    monkeypatch.setenv("HIVE_ROW_CHECKPOINT", "0")
    fixed, seen = _train(tmp_path, monkeypatch, rows, "", checkpoint=False, int8_base=True)
    assert fixed["used"] == 1 and all("print(2)" not in s for s, g in seen if g)
    assert advised == []

    monkeypatch.setenv("HIVE_ROW_CHECKPOINT", "1")
    adaptive, seen = _train(tmp_path, monkeypatch, rows, "", checkpoint=False, int8_base=True)
    assert adaptive["used"] == 2 and any("print(2)" in s for s, g in seen if g)
    assert advised == [(folder / "model.safetensors", 0, 0, os.POSIX_FADV_DONTNEED)]
    assert all("print(3)" not in s for s, _ in seen)
    mem = adaptive["memory"]
    assert 420 <= mem["evaluation_max_len"] <= 421 < mem["training_max_len"]
    assert all(n > 0 for n in mem["row_modes"].values())

def test_missing_root_counter_preserves_finite_child_bound(tmp_path, monkeypatch):
    from pathlib import Path

    root = tmp_path / "cgroup"
    leaf = root / "worker"
    leaf.mkdir(parents=True)
    (leaf / "memory.max").write_text(str(1024 * MB))
    membership = tmp_path / "membership"
    membership.write_text("0::/worker\n")
    paths = {"/proc/self/cgroup": membership, "/sys/fs/cgroup": root}
    monkeypatch.setattr(grow, "Path", lambda name: paths.get(name, Path(name)))
    assert grow._cgroup_limits() == [(leaf / "memory.current", 1024 * MB)]


def test_pressure_near_limit_does_not_toggle_gears_or_discard_a_safe_row():
    from test_memory_guard import FakePsutil

    ps = FakePsutil(99 * MB)
    guard = grow.MemoryGuard(MB, psutil=ps, spare_gb=0, every=0, checkpoint_floor=MB / 4)
    assert guard.row_mode(100, "initial", 0) == "checkpoint"
    for room in (101, 99, 104, 102):
        ps.avail = room * MB
        assert guard.row_mode(100, "near limit", 0) == "checkpoint"
    ps.avail = 126 * MB
    assert guard.row_mode(100, "ordinary with margin", 0) == "ordinary"
    ps.avail = 99 * MB
    assert guard.row_mode(100, "tight again", 0) == "checkpoint"
    guard.checkpoint_cost = 2 * MB
    ps.avail = 101 * MB
    assert guard.row_mode(100, "only ordinary fits", 0) == "ordinary"
    assert guard.record()["mode_changes"] == 3
