import contextlib

import pytest
import torch
from peft import LoraConfig, get_peft_model
from torch.nn import functional as F
from transformers import Qwen3Config, Qwen3ForCausalLM

from training import ternary_base
from training.lm_head_loss import answer_nll, projection_rows


def small_cell(kind):
    torch.manual_seed(17)
    cfg = Qwen3Config(vocab_size=137, hidden_size=128, intermediate_size=256,
                      num_hidden_layers=1, num_attention_heads=4, num_key_value_heads=2,
                      head_dim=32, max_position_embeddings=64, use_cache=False)
    model = Qwen3ForCausalLM(cfg)
    if kind == "peft":
        model = get_peft_model(model, LoraConfig(r=4, lora_alpha=8, target_modules=["q_proj", "down_proj"]))
        disable = model.disable_adapter
    else:
        model.requires_grad_(False)
        for parent, name in [(model.model.layers[0].self_attn, "q_proj"), (model.model.layers[0].mlp, "down_proj")]:
            setattr(parent, name, ternary_base.TernaryLinear(getattr(parent, name), rank=4, alpha=8))
        model.lm_head = ternary_base.TernaryLinear(model.lm_head)
        disable = ternary_base.Cell(model, [0], 4, 8, 0).off
    # An actual policy/base difference exercises all four scores in DPO.
    with torch.no_grad():
        for name, p in model.named_parameters():
            if "lora_B" in name:
                p.normal_(std=0.03)
    return model, disable


def old_scores(model, ids, k):
    logits = model(input_ids=ids, logits_to_keep=k + 1).logits[:, :-1].float()
    targets = ids[:, -k:]
    plain = F.cross_entropy(logits.reshape(-1, logits.shape[-1]), targets.reshape(-1))
    score = F.log_softmax(logits, -1).gather(-1, targets.unsqueeze(-1)).sum()
    return plain, score


@pytest.mark.parametrize("kind", ["peft", "int8"])
@pytest.mark.parametrize("paired", [False, True])
def test_scores_and_all_adapter_gradients_match_pre_chunk_trainer(kind, paired):
    model, disable = small_cell(kind)
    pos, neg = torch.randint(0, 137, (1, 21)), torch.randint(0, 137, (1, 13))
    def run(chunked):
        def scores(ids, k):
            if not chunked:
                return old_scores(model, ids, k)
            nll = answer_nll(model, ids, k, 3)
            return nll / k, -nll

        loss, chosen = scores(pos, 10)
        if paired:
            _, rejected = scores(neg, 5)
            with torch.no_grad(), disable():
                _, ref_chosen = scores(pos, 10)
                _, ref_rejected = scores(neg, 5)
            margin = 0.1 * ((chosen - ref_chosen) - (rejected - ref_rejected))
            loss = loss - F.logsigmoid(margin)
        model.zero_grad(set_to_none=True)
        loss.backward()
        return loss.detach(), [p.grad.clone() for p in model.parameters() if p.requires_grad]
    old, old_grad = run(False)
    new, new_grad = run(True)
    torch.testing.assert_close(new, old)
    for actual, expected in zip(new_grad, old_grad):
        torch.testing.assert_close(actual, expected, atol=1e-6, rtol=1e-4)


def test_projection_is_bounded_in_backward_and_short_rows_project_once():
    model, _ = small_cell("peft")
    base = model.get_base_model()
    # Even if a future trainer unfreezes the head, the blockwise backward
    # accumulates its full gradient. Cover batched, uneven final chunks.
    base.lm_head.weight.requires_grad_(True)
    ids = torch.randint(0, 137, (2, 19))
    answer_nll(model, ids, 9).backward()
    expected = base.lm_head.weight.grad.clone()
    model.zero_grad(set_to_none=True)
    projected, saved = [], []
    assert projection_rows(model, 9, 4) == 4
    assert projection_rows(model, 1, 4) == 2
    def record_head(module, args):
        projected.append(args[0].numel() // args[0].shape[-1])
    def record_tensor(t):
        saved.append(t.shape)
        return t
    with base.lm_head.register_forward_pre_hook(record_head):
        with torch.autograd.graph.saved_tensors_hooks(record_tensor, lambda t: t):
            loss = answer_nll(model, ids, 9, 4)
        assert projected == [4, 4, 4, 4, 2]
        assert not any(len(shape) >= 2 and shape[-1] == 137 for shape in saved)
        loss.backward()
        assert projected[5:] == [2, 4, 4, 4, 4]
        torch.testing.assert_close(base.lm_head.weight.grad, expected, atol=2e-6, rtol=1e-4)
        projected.clear()
        answer_nll(model, ids[:1], 1, 4).backward()
        assert projected == [2]  # the original single forward (its last prediction is discarded)


@pytest.mark.parametrize("cast", [contextlib.nullcontext, lambda: torch.autocast("cpu", torch.bfloat16)])
def test_held_out_and_raw_next_token_scoring(cast):
    from training.grow import kept_loss
    model, _ = small_cell("int8")
    ids = torch.randint(0, 137, (1, 20))
    k = ids.shape[1] - 1
    model.train()
    with torch.no_grad(), cast():
        expected = old_scores(model, ids, k)[0].item()
    actual = kept_loss(model, [("reading", (ids, k))], "cpu", cast, chunk_tokens=4)
    assert actual["reading"][0] == pytest.approx(expected, abs=2e-5)
    assert model.training


def test_other_architecture_keeps_its_public_forward():
    class OtherHead(torch.nn.Module):
        def forward(self, input_ids, logits_to_keep):
            # A model-specific score transformation must survive fallback.
            scores = 2 * F.one_hot(input_ids[:, -logits_to_keep:], 7).float() - 1
            return type("Output", (), {"logits": scores})()
    model = OtherHead()
    ids = torch.tensor([[2, 1, 1, 3, 1]])
    assert projection_rows(model, 4, 2) == 5
    torch.testing.assert_close(answer_nll(model, ids, 4, 2), 4 * old_scores(model, ids, 4)[0])
