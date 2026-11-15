import torch

from training import ternary_base as tb


def _ternary_linear(out=8, inp=256, seed=0):
    g = torch.Generator().manual_seed(seed)
    codes = torch.randint(-1, 2, (out, inp), generator=g).float()
    scale = torch.rand(out, inp // tb.GROUP, generator=g) + 0.5
    lin = torch.nn.Linear(inp, out, bias=False)
    lin.weight.data = (codes.view(out, -1, tb.GROUP) * scale.unsqueeze(-1)).view(out, inp)
    return lin


def test_held_ternary_it_computes_what_the_weights_compute():
    lin = _ternary_linear()
    t = tb.TernaryLinear(lin)
    assert t.codes.dtype == torch.int8 and t.error(lin) < 0.01
    x = torch.randn(3, 256)
    assert torch.allclose(t(x), lin(x), rtol=0.01, atol=0.1)


def test_the_gradient_goes_through_without_keeping_the_weights():
    lin = _ternary_linear()
    t = tb.TernaryLinear(lin, rank=4, alpha=8)
    t.lora_B.data.normal_()
    x = torch.randn(3, 256, requires_grad=True)
    t(x).sum().backward()
    x2 = x.detach().clone().requires_grad_(True)
    ref = lin(x2) + x2 @ t.lora_A.detach().t() @ t.lora_B.detach().t() * 2.0
    ref.sum().backward()
    assert torch.allclose(x.grad, x2.grad, rtol=0.01, atol=0.1)
    assert t.lora_A.grad is not None and t.lora_B.grad is not None


def test_the_edit_can_be_switched_off(monkeypatch):
    lin = _ternary_linear()
    t = tb.TernaryLinear(lin, rank=4, alpha=8)
    t.lora_B.data.normal_()

    class M(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.p = t
    cell = tb.Cell(M(), [0], 4, 8, 0.0)
    x = torch.randn(2, 256)
    with cell.off():
        assert torch.allclose(t(x), lin(x), rtol=0.01, atol=0.1)
    assert not torch.allclose(t(x), lin(x), rtol=0.01, atol=0.1)


def test_weights_that_are_not_ternary_are_refused():
    lin = torch.nn.Linear(256, 8, bias=False)
    t = tb.TernaryLinear(lin)
    assert t.error(lin) > 0.1


def test_the_c_routine_gives_the_very_same_numbers():
    if tb.kernel() is None:
        import pytest
        pytest.skip("no C compiler on this machine: the PyTorch way is used")
    g = torch.Generator().manual_seed(1)
    out, inp = 2048, 1024  # big enough for the routine to be used
    codes = torch.randint(-1, 2, (out, inp), generator=g, dtype=torch.int8)
    scale = (torch.rand(out, inp // tb.GROUP, generator=g) + 0.5).to(torch.bfloat16)
    slow = (codes.view(out, -1, tb.GROUP).to(torch.bfloat16) * scale.view(out, -1, 1)).view(out, inp)
    fast = tb._deq(codes, scale, torch.bfloat16)
    assert fast.dtype == torch.bfloat16 and torch.equal(fast.view(torch.int16), slow.view(torch.int16))
    assert tb._deq(codes, scale, torch.bfloat16) is fast  # one buffer for each shape, written again at every call


def test_a_tall_matrix_is_computed_in_slices_and_word_vectors_are_read_by_row(monkeypatch):
    monkeypatch.setattr(tb, "SLICE", 3)
    lin = _ternary_linear(out=8)
    t = tb.TernaryLinear(lin)
    x = torch.randn(2, 5, 256, requires_grad=True)
    y = t(x)
    assert torch.allclose(y, lin(x), rtol=0.01, atol=0.1)
    y.sum().backward()
    x2 = x.detach().clone().requires_grad_(True)
    lin(x2).sum().backward()
    assert torch.allclose(x.grad, x2.grad, rtol=0.01, atol=0.1)
    # the table of word vectors held as codes: a row is the same numbers as the matrix's row
    emb = tb.TernaryEmbedding(t.codes, t.scale, torch.float32)
    ids = torch.tensor([[0, 7, 3]])
    assert emb(ids).shape == (1, 3, 256) and torch.allclose(emb(ids)[0, 1], lin.weight[7], rtol=0.01, atol=0.01)


def test_the_whole_model_is_read_matrix_by_matrix(tmp_path):
    """A small model saved as the published ones are, with ternary weights: loaded held ternary it gives the logits
    the ordinary loading gives."""
    from transformers import AutoModelForCausalLM, Qwen3Config, Qwen3ForCausalLM
    torch.manual_seed(0)
    cfg = Qwen3Config(vocab_size=97, hidden_size=128, intermediate_size=256, num_hidden_layers=2, num_attention_heads=2,
                      num_key_value_heads=1, head_dim=64, max_position_embeddings=64, tie_word_embeddings=False)
    ref = Qwen3ForCausalLM(cfg)
    with torch.no_grad():
        for n, p in ref.named_parameters():
            if p.dim() == 2:  # make every matrix ternary in groups of 128, as the published weights are
                g = p.view(p.shape[0], -1, tb.GROUP)
                s = g.abs().mean(-1, keepdim=True)
                p.copy_((torch.sign(g) * (g.abs() > 0.5 * s) * s).view_as(p))
    ref.save_pretrained(tmp_path)
    model, cell = tb.load(tmp_path, rank=4, alpha=8, layers=[1], dtype=torch.float32, log=lambda *a, **k: None)
    ids = torch.randint(0, 97, (1, 9))
    with torch.no_grad():
        a, b = AutoModelForCausalLM.from_pretrained(tmp_path, dtype=torch.float32)(input_ids=ids).logits, model(input_ids=ids).logits
    assert torch.allclose(a, b, rtol=0.02, atol=0.02)
    assert isinstance(model.lm_head, tb.TernaryLinear) and isinstance(model.model.embed_tokens, tb.TernaryEmbedding)
    assert len(cell.params) == 2 * 7 and all(p.requires_grad for p in cell.params)  # the edit on layer 1 only
    assert not any(p.requires_grad for n, p in model.named_parameters() if "lora_" not in n)
