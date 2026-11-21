"""Answer-token negative log likelihood for HiveMIND's Qwen3 trainer."""
import torch
from torch.nn import functional as F
from torch.utils.checkpoint import checkpoint


def _chunk_base(model, targets, chunk_tokens):
    if 0 < chunk_tokens < targets:
        # Qwen3ForCausalLM.forward projects this exact state with no logit scaling
        # or soft cap. Only bypass that forward for the architecture we verified.
        from transformers import Qwen3ForCausalLM
        if type(model) is Qwen3ForCausalLM:
            return model
        # The trainer's LoRA modules live inside the decoder. Prompt-learning
        # and other PEFT wrappers may instead change their inputs in forward.
        from peft import LoraConfig, PeftModel
        if isinstance(model, PeftModel) and type(model.active_peft_config) is LoraConfig:
            base = model.get_base_model()
            if model.active_peft_config.alora_invocation_tokens is None and type(base) is Qwen3ForCausalLM:
                return base
    return None


def projection_rows(model, targets, chunk_tokens):
    """Max tokens sent to the output head in grow's single-sequence forward."""
    return chunk_tokens if _chunk_base(model, targets, chunk_tokens) is not None else targets + 1


def answer_nll(model, ids, k, chunk_tokens=0):
    """Sum the k next-token losses at the end of each sequence, across the batch.

    The stock path also serves unknown architectures and short answers. On long
    Qwen3 answers only the output projection and CE are recomputed in backward.
    The transformer runs once and no chunk's vocabulary logits survive forward.
    Input is unpadded, as in grow.train. Call inside the trainer's autocast.
    """
    if ids.ndim != 2 or not 0 < k < ids.shape[1] or chunk_tokens < 0:
        raise ValueError("expected batched token IDs, 0 < k < sequence length, and a nonnegative chunk size")
    labels = ids[:, -k:].reshape(-1)
    base = _chunk_base(model, labels.numel(), chunk_tokens)
    if base is not None:
        states = base.model(input_ids=ids, return_dict=True).last_hidden_state
        hidden = states[:, -k - 1:-1].reshape(-1, states.shape[-1])

        def project(block, targets):
            return F.cross_entropy(base.lm_head(block).float(), targets, reduction="sum")

        loss = hidden.new_zeros((), dtype=torch.float32)
        for block, targets in zip(hidden.split(chunk_tokens), labels.split(chunk_tokens)):
            if torch.is_grad_enabled():
                # Summing ordinary per-chunk CEs alone still retains every
                # softmax for backward. Save only its hidden input and IDs.
                part = checkpoint(project, block, targets, use_reentrant=False)
            else:
                part = project(block, targets)
            loss = loss + part
        return loss
    logits = model(input_ids=ids, logits_to_keep=k + 1).logits[:, :-1, :]
    return F.cross_entropy(logits.float().reshape(-1, logits.shape[-1]), labels, reduction="sum")
