import torch

from training import grow


def _run(cache, folder=None):
    from peft import LoraConfig, get_peft_model
    from transformers import Qwen3Config, Qwen3ForCausalLM
    torch.manual_seed(0)
    cfg = Qwen3Config(vocab_size=97, hidden_size=64, intermediate_size=128, num_hidden_layers=4, num_attention_heads=4,
                      num_key_value_heads=2, head_dim=16, max_position_embeddings=64)
    model = Qwen3ForCausalLM(cfg)
    model = get_peft_model(model, LoraConfig(r=4, lora_alpha=8, lora_dropout=0.0, layers_to_transform=[2, 3], target_modules=["q_proj", "down_proj"]))
    model.config.use_cache = False
    model.train()
    prefix = grow._Prefix(model, 2, log=lambda *a, **k: None, folder=folder) if cache else None
    rows = [torch.randint(0, 97, (1, 20)) for _ in range(3)]
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=1e-2)
    losses = []
    for _ in range(3):
        for ids in rows:
            with (prefix.use(ids) if prefix else torch.enable_grad()):
                logits = model(input_ids=ids).logits[:, :-1]
            loss = torch.nn.functional.cross_entropy(logits.reshape(-1, 97), ids[:, 1:].reshape(-1))
            loss.backward()
            opt.step()
            opt.zero_grad()
            losses.append(loss.item())
    edit = torch.cat([p.detach().flatten() for p in model.parameters() if p.requires_grad])
    return losses, edit, prefix


def test_skipping_the_frozen_layers_gives_the_same_cell():
    plain_losses, plain_edit, _ = _run(False)
    kept_losses, kept_edit, prefix = _run(True)
    assert prefix.hits == 6 and prefix.misses == 3      # each row computed once below layer 2, reused twice
    assert max(abs(a - b) for a, b in zip(plain_losses, kept_losses)) < 1e-5
    assert torch.allclose(plain_edit, kept_edit, atol=1e-6)


def test_kept_on_disk_it_is_the_same_cell_and_the_files_are_cleared(tmp_path):
    plain_losses, plain_edit, _ = _run(False)
    kept_losses, kept_edit, prefix = _run(True, tmp_path / "kept")
    assert prefix.hits == 6 and len(list((tmp_path / "kept").glob("*.bin"))) == 3  # one file a row, nothing held in memory
    assert max(abs(a - b) for a, b in zip(plain_losses, kept_losses)) < 1e-5
    assert torch.allclose(plain_edit, kept_edit, atol=1e-6)
    prefix.done()
    assert not (tmp_path / "kept").exists()
