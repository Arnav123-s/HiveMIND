# Muse's work - Muse's side. Kernel benchmark 3: attention + rotary at lab scale.
# Baseline = train.py Block.forward path: rotated() (stack/flatten) then
# F.scaled_dot_product_attention(is_causal=True). Variants must reproduce the same
# numbers (fp rounding aside): manual attention, SDPA math backend, and a
# complex-multiplication rotary that computes the identical interleaved-pair rotation.
import json, time
import torch
import torch.nn.functional as F
from torch.nn.attention import sdpa_kernel, SDPBackend

torch.set_num_threads(2)
torch.manual_seed(20261112)
CTX = 256

def bench(fn, reps=9, warm=3):
    for _ in range(warm):
        fn()
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter(); fn(); ts.append(time.perf_counter() - t0)
    ts.sort()
    return ts[len(ts) // 2]

def rotated_ref(x, cos, sin):
    """train.py rotated(), verbatim."""
    a, b = x[..., ::2], x[..., 1::2]
    return torch.stack([a * cos - b * sin, a * sin + b * cos], -1).flatten(-2)

def rotated_cplx(x, rotor):
    """Same interleaved-pair rotation via complex multiply: pairs (a,b) as a+bi,
    times the precomputed unit rotor cos+i*sin, back to interleaved layout."""
    xc = torch.view_as_complex(x.reshape(*x.shape[:-1], -1, 2).contiguous())
    return torch.view_as_real(xc * rotor).flatten(-2)

def run(b, h, d, label):
    hd = d // h
    x = torch.randn(b, CTX, d) * 0.5
    q = torch.randn(b, h, CTX, hd) * 0.5
    k = torch.randn(b, h, CTX, hd) * 0.5
    v = torch.randn(b, h, CTX, hd) * 0.5
    each = hd
    angle = torch.arange(CTX).float()[:, None] / (10000 ** (torch.arange(0, each, 2).float() / each))[None]
    cos, sin = angle.cos(), angle.sin()
    rotor = torch.complex(cos, sin)  # [CTX, hd/2]

    ref_rope = rotated_ref(q, cos, sin)
    out_rope = rotated_cplx(q, rotor)
    rope_err = (ref_rope - out_rope).abs().max().item()

    ref = F.scaled_dot_product_attention(q, k, v, is_causal=True)
    def manual():
        att = (q @ k.transpose(-1, -2)) * (hd ** -0.5)
        mask = torch.ones(CTX, CTX, dtype=torch.bool).triu(1)
        att = att.masked_fill(mask, float('-inf'))
        return att.softmax(-1) @ v
    man_err = (manual() - ref).abs().max().item()
    with sdpa_kernel(SDPBackend.MATH):
        ref_math = F.scaled_dot_product_attention(q, k, v, is_causal=True)
    math_err = (ref_math - ref).abs().max().item()

    res = {'case': label, 'shape': [b, h, CTX, hd],
           'rope_cplx_err': rope_err, 'manual_err': man_err, 'sdpa_math_err': math_err,
           'rope_ref_s': bench(lambda: rotated_ref(q, cos, sin)),
           'rope_cplx_s': bench(lambda: rotated_cplx(q, rotor)),
           'sdpa_s': bench(lambda: F.scaled_dot_product_attention(q, k, v, is_causal=True)),
           'manual_s': bench(manual),
           'rope+sdpa_ref_s': bench(lambda: F.scaled_dot_product_attention(rotated_ref(q, cos, sin), rotated_ref(k, cos, sin), v, is_causal=True)),
           'rope+sdpa_cplx_s': bench(lambda: F.scaled_dot_product_attention(rotated_cplx(q, rotor), rotated_cplx(k, rotor), v, is_causal=True))}
    print(json.dumps(res))

run(32, 4, 192, 'champion_dim192')
run(32, 4, 288, 'ladder2m_dim288')
