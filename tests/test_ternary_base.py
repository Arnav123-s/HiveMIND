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
