"""The DNA held in memory as what it is: ternary. Training a cell on a 4B or 8B DNA.

The published unpacked weights of a Ternary-Bonsai model are ternary in groups of 128 along each row: every weight
is -s, 0 or +s for its group's scale s (checked on the 1.7B: within 0.7% of the scale, the rounding of the stored
floats). `grow.py` loaded them as 16-bit numbers, 2 bytes a weight: 16 GB for an 8B DNA, more than a free runner
has. Here each frozen layer keeps one byte a weight (its codes, -1/0/+1) and one scale per group, and
turns them into numbers only while it computes; its backward pass does the same instead of keeping the numbers
(a custom autograd function), so the memory stays near one byte a weight. The cell's edit is LoRA, written in
the layout PEFT saves (adapter_config.json, adapter_model.safetensors), so `convert_lora_to_gguf.py` and the
ternary runtime take it as before.

Found on the first 8B generations (2026-11-14 and 15): one cell in four died in training, its runner out of memory
(a 16 GB runner; the job "lost communication" or sat for five hours in its first long row). Three things took the
room, and each is gone now:
  - the whole DNA was first loaded as 16-bit numbers (16 GB) and only then turned into codes. Now every matrix is
    read from the file by itself and turned into codes at once: nothing but codes is ever held.
  - the table of word vectors and the output layer stayed 16-bit (1.2 GB each on the 8B, which keeps two). They
    are ternary too and are held as codes; the output layer computes in slices of its rows.
  - the edit's own path copied each layer's input as 32-bit numbers. It computes in the input's own type now.

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
SLICE = 16384  # rows of a very tall matrix (the output layer: one row a word) turned into numbers at a time


# Turning a layer's codes back into numbers is most of a training row's time on an 8B DNA (measured 2026-11-15: about
# 9 of 12 seconds of a forward pass, more than the multiplying itself): PyTorch does it in three passes over memory on
# one core. This small C routine does it in one pass on every core: a 16-bit number is the group's scale with its
# sign bit set where the code is -1, and zero where the code is 0. Built once with the machine's compiler; where
# there is none, the PyTorch way is used.
_C = r"""
#include <stdint.h>
void hive_deq16(const int8_t *codes, const uint16_t *scale, uint16_t *out, long r0, long r1, long inp, long group) {
    for (long r = r0; r < r1; r++) {
        const int8_t *c = codes + r * inp;
        const uint16_t *s = scale + r * (inp / group);
        uint16_t *o = out + r * inp;
        for (long g = 0; g < inp / group; g++) {
            const uint16_t sb = s[g];
            for (long i = 0; i < group; i++) {
                const int16_t ci = c[g * group + i];
                o[g * group + i] = (uint16_t)((sb ^ (uint16_t)(ci & 0x8000)) & (uint16_t)(-(ci & 1)));
            }
        }
    }
}
"""
_kernel, _pool, _scratch = None, None, {}


def kernel():
    """The C routine, built on first use (None where it cannot be built: no compiler, or HIVE_DEQ=torch)."""
    global _kernel, _pool
    if _kernel is not None:
        return _kernel or None
    _kernel = False
    import ctypes
    import hashlib
    import os
    import subprocess
    if os.environ.get("HIVE_DEQ") == "torch":
        return None
    home = Path(os.environ.get("HIVE_TERNARY_HOME", Path.home() / ".cache" / "hive" / "ternary"))
    so = home / f"deq_{hashlib.sha1(_C.encode()).hexdigest()[:10]}.so"
    try:
        if not so.exists():
            home.mkdir(parents=True, exist_ok=True)
            src = so.with_suffix(".c")
            src.write_text(_C)
            tmp = so.with_suffix(f".{os.getpid()}.tmp")
            subprocess.run(["cc", "-O3", "-march=native", "-shared", "-fPIC", "-o", str(tmp), str(src)], check=True, capture_output=True, timeout=120)
            os.replace(tmp, so)
        lib = ctypes.CDLL(str(so))
        lib.hive_deq16.argtypes = [ctypes.c_void_p] * 3 + [ctypes.c_long] * 4
        lib.hive_deq16.restype = None
        from concurrent.futures import ThreadPoolExecutor
        _pool = ThreadPoolExecutor(max(1, torch.get_num_threads()))
        _kernel = lib.hive_deq16
    except (OSError, subprocess.SubprocessError):
        _kernel = False
    return _kernel or None


def _deq(codes, scale, dtype):
    """The numbers of a layer held as codes. In 16-bit: written by the C routine into one buffer for each shape of
    matrix, used again at every call (the caller multiplies with it at once and keeps no reference to it)."""
    out, inp = codes.shape
    fast = kernel() if (dtype == torch.bfloat16 and scale.dtype == torch.bfloat16 and out * inp >= 1 << 20
                        and codes.is_contiguous() and scale.is_contiguous()) else None
    if fast is None:
        return (codes.view(out, inp // GROUP, GROUP).to(dtype) * scale.view(out, inp // GROUP, 1).to(dtype)).view(out, inp)
    buf = _scratch.get((out, inp))
    if buf is None:
        buf = _scratch[(out, inp)] = torch.empty(out, inp, dtype=torch.bfloat16)
    n = _pool._max_workers
    step = -(-out // n)
    c, sc, o = codes.data_ptr(), scale.data_ptr(), buf.data_ptr()
    list(_pool.map(lambda r0: fast(c, sc, o, r0, min(out, r0 + step), inp, GROUP), range(0, out, step)))
    return buf


def _codes(w):
    """A stored matrix as (codes, scales, how far the worst group is from ternary, relative to its scale)."""
    out, inp = w.shape
    if inp % GROUP:
        raise ValueError(f"{inp} inputs is not a whole number of groups of {GROUP}")
    codes = torch.empty(out, inp, dtype=torch.int8)
    scale = torch.empty(out, inp // GROUP, dtype=torch.bfloat16)
    worst = 0.0
    for i in range(0, out, 4096):  # in slices of rows: a matrix of 150,000 rows is never held twice as 32-bit numbers
        g = w[i:i + 4096].float().view(-1, inp // GROUP, GROUP)
        s = g.abs().amax(-1, keepdim=True).clamp(min=1e-12)
        c = (g / s).round().clamp(-1, 1)
        worst = max(worst, ((c * s - g).abs().amax(-1) / s.squeeze(-1)).max().item())
        codes[i:i + 4096] = c.to(torch.int8).view(-1, inp)
        scale[i:i + 4096] = s.view(-1, inp // GROUP).to(torch.bfloat16)
    return codes, scale, worst


class _Matmul(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x, codes, scale):
        ctx.save_for_backward(codes, scale)
        if codes.shape[0] <= SLICE:
            return x @ _deq(codes, scale, x.dtype).t()
        return torch.cat([x @ _deq(codes[i:i + SLICE], scale[i:i + SLICE], x.dtype).t() for i in range(0, codes.shape[0], SLICE)], -1)  # each slice is used before the next is made

    @staticmethod
    def backward(ctx, g):
        codes, scale = ctx.saved_tensors
        if codes.shape[0] <= SLICE:
            return g @ _deq(codes, scale, g.dtype), None, None
        out = None
        for i in range(0, codes.shape[0], SLICE):
            part = g[..., i:i + SLICE] @ _deq(codes[i:i + SLICE], scale[i:i + SLICE], g.dtype)
            out = part if out is None else out + part
        return out, None, None


class TernaryLinear(torch.nn.Module):
    """A frozen ternary layer (codes and group scales) with an optional LoRA edit beside it.
    Made from an ordinary layer, or from the matrix as stored (and its bias)."""

    def __init__(self, linear, rank=0, alpha=0, dropout=0.0, bias=None, codes=None):
        super().__init__()
        if codes is None:
            w = linear.weight.detach() if hasattr(linear, "weight") else linear
            bias = linear.bias if hasattr(linear, "weight") else bias
            codes = _codes(w)
        c, s, self.worst = codes
        out, inp = c.shape
        self.register_buffer("codes", c)
        self.register_buffer("scale", s)
        self.bias = None if bias is None else torch.nn.Parameter(bias.detach().clone(), requires_grad=False)
        self.in_features, self.out_features, self.rank, self.on = inp, out, rank, True
        if rank:
            self.lora_A = torch.nn.Parameter(torch.empty(rank, inp, dtype=torch.float32))
            self.lora_B = torch.nn.Parameter(torch.zeros(out, rank, dtype=torch.float32))
            torch.nn.init.kaiming_uniform_(self.lora_A, a=math.sqrt(5))  # as PEFT starts an edit: A random, B zero
            self.scaling = alpha / rank
            self.drop = torch.nn.Dropout(dropout) if dropout else torch.nn.Identity()

    def error(self, linear):
        """The largest difference, relative to the group's scale, between the layer as held and the weights given."""
        w = linear.weight.detach().float()
        return ((_deq(self.codes, self.scale, torch.float32) - w).abs().view(self.out_features, -1, GROUP).amax(-1)
                / self.scale.float()).max().item()

    def forward(self, x):
        # in the type the pass computes in: the last norm hands 32-bit numbers to the output layer, and turning its
        # 600 million codes into 32-bit numbers took 10 of a row's 14 seconds (profiled 2026-11-15)
        if torch.is_autocast_enabled("cpu") and x.dtype != torch.get_autocast_dtype("cpu"):
            x = x.to(torch.get_autocast_dtype("cpu"))
        y = _Matmul.apply(x, self.codes, self.scale)
        if self.bias is not None:
            y = y + self.bias.to(y.dtype)
        if self.rank and self.on:
            # in the input's own type: the two small matrices are converted, never the layer's whole input
            y = y + (self.drop(x) @ self.lora_A.to(x.dtype).t() @ self.lora_B.to(x.dtype).t()) * self.scaling
        return y


class TernaryEmbedding(torch.nn.Module):
    """The table of word vectors held as codes: only the rows a text uses are turned into numbers."""

    def __init__(self, codes, scale, dtype):
        super().__init__()
        self.register_buffer("codes", codes)
        self.register_buffer("scale", scale)
        self.dtype_out, self.num_embeddings, self.embedding_dim = dtype, codes.shape[0], codes.shape[1]

    def forward(self, ids):
        c, s = self.codes[ids], self.scale[ids]
        return (c.view(*ids.shape, -1, GROUP).to(self.dtype_out) * s.unsqueeze(-1).to(self.dtype_out)).view(*ids.shape, -1)


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


def _trim():
    gc.collect()
    try:
        import ctypes
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except OSError:
        pass


def load(src, rank=16, alpha=32, dropout=0.0, layers=None, dtype=torch.bfloat16, log=print):
    """The model with every decoder projection, its table of word vectors and its output layer held ternary, and the
    cell (LoRA on the layers named, all if None). Every matrix is read from the file by itself and turned into codes
    at once, so the most memory used is the codes plus one matrix: an 8B DNA loads inside 9 GB."""
    from accelerate import init_empty_weights
    from accelerate.utils import set_module_tensor_to_device
    from safetensors import safe_open
    from transformers import AutoConfig, AutoModelForCausalLM
    src = Path(src)
    config = AutoConfig.from_pretrained(src)
    with init_empty_weights():  # the shape of the model, with no memory behind any weight yet
        model = AutoModelForCausalLM.from_config(config)
    index = src / "model.safetensors.index.json"
    where = json.loads(index.read_text())["weight_map"] if index.exists() else None
    files = {}

    def opened(f):
        if f not in files:
            files.clear()  # one file open at a time: an open file's pages count as this process's memory
            files[f] = safe_open(str(src / f), "pt")
        return files[f]

    def stored(name):
        return opened(where[name] if where else "model.safetensors").get_tensor(name)

    def has(name):
        return name in where if where is not None else name in opened("model.safetensors").keys()

    nl = config.num_hidden_layers
    which = list(range(nl)) if layers is None else list(layers)
    worst = 0.0
    for i, block in enumerate(model.model.layers):
        for part in ("self_attn", "mlp"):
            parent = getattr(block, part)
            for name in TARGETS:
                lin = getattr(parent, name, None)
                if lin is None:
                    continue
                key = f"model.layers.{i}.{part}.{name}"
                t = TernaryLinear(stored(key + ".weight"), rank if i in which else 0, alpha, dropout,
                                  bias=stored(key + ".bias") if lin.bias is not None and has(key + ".bias") else None)
                worst = max(worst, t.worst)
                setattr(parent, name, t)
        if i % 6 == 5:
            _trim()
    if worst > 0.02:
        raise ValueError(f"these weights are not ternary in groups of {GROUP} (the worst group is {worst:.3f} of its scale off)")
    # the table of word vectors and the output layer: ternary too where the model's are (one table when they are tied)
    emb = _codes(stored("model.embed_tokens.weight"))
    tied = bool(getattr(config, "tie_word_embeddings", False)) or not has("lm_head.weight")
    as_codes = emb[2] <= 0.02
    if as_codes:
        model.model.embed_tokens = TernaryEmbedding(emb[0], emb[1], dtype)
    else:
        model.model.embed_tokens.weight = torch.nn.Parameter(stored("model.embed_tokens.weight").to(dtype), requires_grad=False)
    head = emb if tied else _codes(stored("lm_head.weight"))
    if head[2] <= 0.02:
        model.lm_head = TernaryLinear(None, codes=head)
    elif tied and not as_codes:
        model.lm_head.weight = model.model.embed_tokens.weight
    else:
        model.lm_head.weight = torch.nn.Parameter(stored("model.embed_tokens.weight" if tied else "lm_head.weight").to(dtype), requires_grad=False)
    del emb, head
    # what is left is small (the norms): as stored
    for name, p in list(model.named_parameters()):
        if p.is_meta:
            set_module_tensor_to_device(model, name, "cpu", value=stored(name).to(dtype))
    for p in model.parameters():
        p.requires_grad_(False)
    files.clear()
    _trim()
    cell = Cell(model, which, rank, alpha, dropout)
    for p in cell.params:
        p.requires_grad_(True)
    log(f"the DNA held ternary: one byte a weight and one scale per {GROUP} (the word vectors and the output layer "
        f"{'too' if as_codes else 'as numbers'}); the worst group is {worst:.4f} of its scale off; {held_gb():.1f} GB held", flush=True)
    return model, cell


def memory_gb():
    import resource
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20


def held_gb():
    """The memory this process holds of its own right now (not the pages of files it has open), in GB."""
    try:
        for ln in open("/proc/self/status"):
            if ln.startswith("RssAnon:"):
                return int(ln.split()[1]) / 2**20
    except OSError:
        pass
    return memory_gb()


if __name__ == "__main__":  # python training/ternary_base.py <unpacked folder>: the same logits held both ways
    import sys
    from transformers import AutoModelForCausalLM, AutoTokenizer
    src = sys.argv[1]
    tok = AutoTokenizer.from_pretrained(src)
    ids = tok("The capital of France is", return_tensors="pt")["input_ids"]
    model, cell = load(src, rank=4, layers=[0])
    with torch.no_grad():
        b = model(input_ids=ids).logits.float()
    held = held_gb()
    del model, cell
    gc.collect()
    ref = AutoModelForCausalLM.from_pretrained(src, dtype=torch.bfloat16)
    with torch.no_grad():
        a = ref(input_ids=ids).logits.float()
    print(json.dumps({"max_logit_difference": round((a - b).abs().max().item(), 4), "same_next_word": bool((a[0, -1].argmax() == b[0, -1].argmax()).item()),
                      "next_word": tok.decode(b[0, -1].argmax()), "most_memory_gb_held_ternary": round(held, 2)}))
