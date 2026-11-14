"""The DNA held in memory as what it is: ternary. Training a cell on a 4B or 8B DNA.

The published unpacked weights of a Ternary-Bonsai model are ternary in groups of 128 along each row: every weight
is -s, 0 or +s for its group's scale s (checked on the 1.7B: within 0.7% of the scale, the rounding of the stored
floats). `grow.py` loaded them as 16-bit numbers, 2 bytes a weight: 16 GB for an 8B DNA, more than a free runner
has. Here each frozen layer keeps one byte a weight (its codes, -1/0/+1) and one scale per group of 128, and
turns them into numbers only while it computes; its backward pass does the same instead of keeping the numbers
(a custom autograd function), so the memory stays near one byte a weight. The cell's edit is LoRA, written in
the layout PEFT saves (adapter_config.json, adapter_model.safetensors), so `convert_lora_to_gguf.py` and the
ternary runtime take it as before.

    model, cell = load(src, rank=16, layers=[...])     # cell.params: what training updates
    with cell.off(): ...                               # the DNA without the edit (the reference for --pairs)
    cell.save(folder)                                  # PEFT layout
"""
import contextlib
import gc
import json
import math
from pathlib import Path

import torch

GROUP = 128
TARGETS = ("q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj")


def _deq(codes, scale, dtype):
    out, inp = codes.shape
    return (codes.view(out, inp // GROUP, GROUP).to(dtype) * scale.view(out, inp // GROUP, 1).to(dtype)).view(out, inp)


class _Matmul(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x, codes, scale):
        ctx.save_for_backward(codes, scale)
        return x @ _deq(codes, scale, x.dtype).t()

    @staticmethod
    def backward(ctx, g):
        codes, scale = ctx.saved_tensors
        return g @ _deq(codes, scale, g.dtype), None, None


class TernaryLinear(torch.nn.Module):
    """A frozen ternary layer (codes and group scales) with an optional LoRA edit beside it."""

    def __init__(self, linear, rank=0, alpha=0, dropout=0.0):
        super().__init__()
        w = linear.weight.detach()
        out, inp = w.shape
        if inp % GROUP:
            raise ValueError(f"{inp} inputs is not a whole number of groups of {GROUP}")
        g = w.float().view(out, inp // GROUP, GROUP)
        s = g.abs().amax(-1, keepdim=True).clamp(min=1e-12)
        self.register_buffer("codes", (g / s).round().clamp(-1, 1).to(torch.int8).view(out, inp))
        self.register_buffer("scale", s.view(out, inp // GROUP).to(torch.bfloat16))
        self.bias = None if linear.bias is None else torch.nn.Parameter(linear.bias.detach().clone(), requires_grad=False)
        self.in_features, self.out_features, self.rank, self.on = inp, out, rank, True
        if rank:
            self.lora_A = torch.nn.Parameter(torch.empty(rank, inp, dtype=torch.float32))
            self.lora_B = torch.nn.Parameter(torch.zeros(out, rank, dtype=torch.float32))
            torch.nn.init.kaiming_uniform_(self.lora_A, a=math.sqrt(5))  # as PEFT starts an edit: A random, B zero
            self.scaling = alpha / rank
            self.drop = torch.nn.Dropout(dropout)

    def error(self, linear):
        """The largest difference, relative to the group's scale, between the layer as held and the weights given."""
        w = linear.weight.detach().float()
        return ((_deq(self.codes, self.scale, torch.float32) - w).abs().view(self.out_features, -1, GROUP).amax(-1)
                / self.scale.float()).max().item()

    def forward(self, x):
        y = _Matmul.apply(x, self.codes, self.scale)
        if self.bias is not None:
            y = y + self.bias.to(y.dtype)
        if self.rank and self.on:
            y = y + (self.drop(x).to(self.lora_A.dtype) @ self.lora_A.t() @ self.lora_B.t() * self.scaling).to(y.dtype)
        return y


class Cell:
    """The LoRA edit spread over the TernaryLinear layers: what training updates, and how it is saved."""

    def __init__(self, model, layers, rank, alpha, dropout):
        self.layers = {n: m for n, m in model.named_modules() if isinstance(m, TernaryLinear) and m.rank}
        self.params = [p for m in self.layers.values() for p in (m.lora_A, m.lora_B)]
        self.config = {"r": rank, "lora_alpha": alpha, "lora_dropout": dropout, "layers": layers}

    @contextlib.contextmanager
    def off(self):
        for m in self.layers.values():
            m.on = False
        try:
            yield
        finally:
            for m in self.layers.values():
                m.on = True

    def save(self, folder, base_name):
        from peft import LoraConfig
        from safetensors.torch import save_file
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        tensors = {}
        for n, m in self.layers.items():
            tensors[f"base_model.model.{n}.lora_A.weight"] = m.lora_A.detach().float().contiguous()
            tensors[f"base_model.model.{n}.lora_B.weight"] = m.lora_B.detach().float().contiguous()
        save_file(tensors, str(folder / "adapter_model.safetensors"))
        LoraConfig(r=self.config["r"], lora_alpha=self.config["lora_alpha"], lora_dropout=self.config["lora_dropout"],
                   target_modules=list(TARGETS), layers_to_transform=self.config["layers"], task_type="CAUSAL_LM",
                   base_model_name_or_path=base_name).save_pretrained(str(folder))


def load(src, rank=16, alpha=32, dropout=0.05, layers=None, dtype=torch.bfloat16, log=print):
    """The model with every decoder projection held ternary, and the cell (LoRA on the layers named, all if None).
    Loads as 16-bit once (with swap on a runner for 8B), then turns layer after layer into codes and frees it."""
    from transformers import AutoModelForCausalLM
    model = AutoModelForCausalLM.from_pretrained(src, dtype=dtype, low_cpu_mem_usage=True)
    for p in model.parameters():
        p.requires_grad_(False)
    nl = model.config.num_hidden_layers
    which = list(range(nl)) if layers is None else list(layers)
    worst = 0.0
    for i, block in enumerate(model.model.layers):
        for parent in (block.self_attn, block.mlp):
            for name in TARGETS:
                lin = getattr(parent, name, None)
                if lin is None:
                    continue
                t = TernaryLinear(lin, rank if i in which else 0, alpha, dropout)
                worst = max(worst, t.error(lin))
                setattr(parent, name, t)
                del lin
        gc.collect()
    try:
        import ctypes
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except OSError:
        pass
    if worst > 0.02:
        raise ValueError(f"these weights are not ternary in groups of {GROUP} (the worst group is {worst:.3f} of its scale off)")
    log(f"the DNA held ternary: one byte a weight and one scale per {GROUP}; the worst group is {worst:.4f} of its scale off", flush=True)
    return model, Cell(model, which, rank, alpha, dropout)


def memory_gb():
    import resource
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20


if __name__ == "__main__":  # python training/ternary_base.py <unpacked folder>: the same logits held both ways
    import sys
    from transformers import AutoModelForCausalLM, AutoTokenizer
    src = sys.argv[1]
    tok = AutoTokenizer.from_pretrained(src)
    ids = tok("The capital of France is", return_tensors="pt")["input_ids"]
    ref = AutoModelForCausalLM.from_pretrained(src, dtype=torch.bfloat16)
    with torch.no_grad():
        a = ref(input_ids=ids).logits.float()
    del ref
    gc.collect()
    model, cell = load(src, rank=4, layers=[0])
    with torch.no_grad():
        b = model(input_ids=ids).logits.float()
    print(json.dumps({"max_logit_difference": round((a - b).abs().max().item(), 4), "same_next_word": bool((a[0, -1].argmax() == b[0, -1].argmax()).item()),
                      "lora_params": sum(p.numel() for p in cell.params), "most_memory_gb": round(memory_gb(), 2)}))
