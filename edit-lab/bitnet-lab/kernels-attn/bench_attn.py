# Muse's work — kernel strike team B (attention), Muse's side. Read-only wrt train.py/kernels/.
"""Attention-variant benchmark for the lab trainer's Block.forward attention call.

Current implementation: F.scaled_dot_product_attention(q, k, v, is_causal=True),
q,k,v shape [batch, heads, T, head_dim]. Variants timed on CPU: default dispatch,
explicit MATH backend (the one never timed here before), explicit-mask form,
hand-rolled masked softmax, noncausal SDPA (causal-cost lower bound), and the
RoPE rotation applied to q,k in the ladder arms. EFFICIENT backend: probed once
for availability (it is CUDA-side; expected to fail on CPU).

Timing method: round-robin interleaved samples across variants, MIN reported —
the lab box is shared and loaded, and the min is the least-contended sample.
Correctness: every variant's forward output vs the current implementation's
output on identical inputs (max abs error).

Shapes: champion (dim 192, heads 4, hd 48), ladder 2M (dim 288, hd 72),
ladder 10M (dim 512, hd 128). batch 32, T=CTX=256, fp32, OMP/MKL=2.
"""
import os, time, json
os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")
import torch
import torch.nn.functional as F
from torch.nn.attention import sdpa_kernel, SDPBackend

torch.set_num_threads(2)
B, T = 32, 256


def interleaved_min(fns, inner, samples=6):
    """fns: {name: fn}. Runs samples rounds; each round times inner reps of each
    fn in rotation. Returns {name: min per-call seconds}."""
    best = {n: float("inf") for n in fns}
    for _ in range(samples):
        for n, fn in fns.items():
            fn()  # one warm rep inside the round keeps caches honest
            t0 = time.perf_counter()
            for _ in range(inner):
                fn()
            dt = (time.perf_counter() - t0) / inner
            if dt < best[n]:
                best[n] = dt
    return best


def rotated(x, cos, sin):
    a, b = x[..., ::2], x[..., 1::2]
    return torch.stack([a * cos - b * sin, a * sin + b * cos], -1).flatten(-2)


def run_shape(dim, heads, label, inner_fwd, inner_fb):
    hd = dim // heads
    g = torch.Generator().manual_seed(0)
    q = torch.randn(B, heads, T, hd, generator=g)
    k = torch.randn(B, heads, T, hd, generator=g)
    v = torch.randn(B, heads, T, hd, generator=g)
    mask = torch.triu(torch.full((T, T), float("-inf")), 1)
    ref = F.scaled_dot_product_attention(q, k, v, is_causal=True)

    fwd_fns = {
        "default_sdpa_is_causal (current)": lambda: F.scaled_dot_product_attention(q, k, v, is_causal=True),
        "sdpa_explicit_mask": lambda: F.scaled_dot_product_attention(q, k, v, attn_mask=mask),
        "manual_masked_softmax": lambda: torch.softmax(q @ k.transpose(-1, -2) / hd ** 0.5 + mask, -1) @ v,
        "sdpa_noncausal (lower bound)": lambda: F.scaled_dot_product_attention(q, k, v, is_causal=False),
    }
    errs = {n: (fn() - ref).abs().max().item() for n, fn in fwd_fns.items()}
    fwd = interleaved_min(fwd_fns, inner_fwd)

    def math_fwd():
        with sdpa_kernel(SDPBackend.MATH):
            return F.scaled_dot_product_attention(q, k, v, is_causal=True)
    errs["sdpa_backend_MATH"] = (math_fwd() - ref).abs().max().item()
    fwd["sdpa_backend_MATH"] = interleaved_min({"m": math_fwd}, inner_fwd)["m"]

    eff_status = "unavailable"
    try:
        with sdpa_kernel(SDPBackend.EFFICIENT_ATTENTION):
            F.scaled_dot_product_attention(q, k, v, is_causal=True)
        eff_status = "available"
    except Exception as e:
        eff_status = "unavailable: " + str(e)[:80]

    qq = q.clone().requires_grad_(True)
    kk = k.clone().requires_grad_(True)
    vv = v.clone().requires_grad_(True)

    def fb_default():
        qq.grad = kk.grad = vv.grad = None
        F.scaled_dot_product_attention(qq, kk, vv, is_causal=True).sum().backward()

    def fb_mask():
        qq.grad = kk.grad = vv.grad = None
        F.scaled_dot_product_attention(qq, kk, vv, attn_mask=mask).sum().backward()

    def fb_manual():
        qq.grad = kk.grad = vv.grad = None
        (torch.softmax(qq @ kk.transpose(-1, -2) / hd ** 0.5 + mask, -1) @ vv).sum().backward()

    fb = interleaved_min({"default_sdpa_is_causal (current)": fb_default,
                          "sdpa_explicit_mask": fb_mask,
                          "manual_masked_softmax": fb_manual}, inner_fb, samples=4)

    def fb_math():
        qq.grad = kk.grad = vv.grad = None
        with sdpa_kernel(SDPBackend.MATH):
            F.scaled_dot_product_attention(qq, kk, vv, is_causal=True).sum().backward()
    fb["sdpa_backend_MATH"] = interleaved_min({"m": fb_math}, inner_fb, samples=4)["m"]

    angle = torch.arange(T).float()[:, None] / (10000 ** (torch.arange(0, hd, 2).float() / hd))[None]
    cos, sin = angle.cos(), angle.sin()
    fwd["rope_rotate_qk"] = interleaved_min(
        {"r": lambda: (rotated(q, cos, sin), rotated(k, cos, sin))}, inner_fwd)["r"]

    print(f"\n== {label}: dim={dim} heads={heads} head_dim={hd} B={B} T={T} (min of interleaved samples) ==")
    print(f"{'variant':38s} {'maxabs_err':>11s} {'fwd ms':>9s} {'fwd+bwd ms':>11s}")
    rows = {}
    for n in ["default_sdpa_is_causal (current)", "sdpa_backend_MATH", "sdpa_explicit_mask",
              "manual_masked_softmax", "sdpa_noncausal (lower bound)"]:
        fbv = fb.get(n)
        print(f"{n:38s} {errs[n]:11.3e} {fwd[n]*1000:9.2f} {(fbv*1000 if fbv else float('nan')):11.2f}")
        rows[n] = {"max_abs_err": errs[n], "fwd_ms": round(fwd[n] * 1000, 3),
                   "fwd_bwd_ms": round(fbv * 1000, 3) if fbv else None}
    print(f"{'rope_rotate_qk':38s} {'n/a':>11s} {fwd['rope_rotate_qk']*1000:9.2f}")
    rows["rope_rotate_qk"] = {"fwd_ms": round(fwd["rope_rotate_qk"] * 1000, 3)}
    rows["sdpa_backend_EFFICIENT"] = {"status": eff_status}
    print(f"EFFICIENT backend on CPU: {eff_status}")
    return rows


if __name__ == "__main__":
    print(f"torch {torch.__version__} threads={torch.get_num_threads()}")
    out = {}
    out["champion_dim192"] = run_shape(192, 4, "champion shape", inner_fwd=20, inner_fb=6)
    out["ladder2m_dim288"] = run_shape(288, 4, "ladder 2M shape", inner_fwd=12, inner_fb=4)
    out["ladder10m_dim512"] = run_shape(512, 4, "ladder 10M shape", inner_fwd=8, inner_fb=3)
    print("\nJSON " + json.dumps(out))
