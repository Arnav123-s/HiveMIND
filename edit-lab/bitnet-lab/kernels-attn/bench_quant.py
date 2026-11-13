# Muse's work — kernel strike team B (quant overhead), Muse's side. Read-only wrt train.py.
"""On-the-fly quantization overhead inside BitLinear.forward (train.py lines 67-74).

Every forward call re-quantizes the full weight matrix (abs/mean/div/round/
clamp/mul/sub/add over all weight elements) and per-token-quantizes the
activations (amax/round/clamp over all input elements), then calls F.linear.
Per BitLinear shape in a block (qkv, out, up, down) at ladder dims 288/512:
  full    - BitLinear.forward as-is (current implementation)
  wquant  - only the weight-quant op block (no matmul)
  aquant  - only the activation-quant op block (no matmul)
  linear  - F.linear on the already-quantized tensors (the matmul itself)
  rawfp   - F.linear on untouched fp tensors (what a plain nn.Linear pays)
Correctness: full BitLinear output vs composed quantize-then-linear (max abs err).
Timing: interleaved min-of-samples. Input [32, 256, in]. fp32, OMP/MKL=2.
"""
import os, sys, time, json
os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")
sys.path.insert(0, os.path.expanduser("~/workspace/edit-lab/bitnet-lab"))
import torch
import torch.nn.functional as F
import train as T

torch.set_num_threads(2)
B, CTX = 32, 256


def interleaved_min(fns, inner=5, samples=5):
    best = {n: float("inf") for n in fns}
    for _ in range(samples):
        for n, fn in fns.items():
            fn()
            t0 = time.perf_counter()
            for _ in range(inner):
                fn()
            dt = (time.perf_counter() - t0) / inner
            if dt < best[n]:
                best[n] = dt
    return {n: round(v * 1000, 3) for n, v in best.items()}


def wquant(w):
    scale = w.abs().mean().clamp(min=1e-5)
    return w + ((w / scale).round().clamp(-1, 1) * scale - w).detach()


def aquant(x):
    top = x.abs().amax(-1, keepdim=True).clamp(min=1e-5)
    return x + ((x * 127 / top).round().clamp(-128, 127) * top / 127 - x).detach()


def run(dim):
    torch.manual_seed(0)
    shapes = {"qkv": (dim, 3 * dim), "out": (dim, dim), "up": (dim, 4 * dim), "down": (4 * dim, dim)}
    print(f"\n== dim={dim} (min, ms) ==")
    print(f"{'layer':6s} {'full':>9s} {'wquant':>9s} {'aquant':>9s} {'linear(q)':>10s} {'rawfp':>9s} {'quant%':>7s} {'maxabs_err':>11s}")
    rows = {}
    for name, (fin, fout) in shapes.items():
        lin = T.BitLinear(fin, fout, bias=False)
        with torch.no_grad():
            lin.weight.normal_(0, 0.02)
        x = torch.randn(B, CTX, fin)
        wq, xq = wquant(lin.weight), aquant(x)
        err = (lin(x) - F.linear(xq, wq)).abs().max().item()
        r = interleaved_min({
            "full": lambda: lin(x),
            "wquant": lambda: wquant(lin.weight),
            "aquant": lambda: aquant(x),
            "linear_q": lambda: F.linear(xq, wq),
            "rawfp": lambda: F.linear(x, lin.weight),
        })
        share = 100.0 * (r["full"] - r["linear_q"]) / r["full"]
        print(f"{name:6s} {r['full']:9.2f} {r['wquant']:9.2f} {r['aquant']:9.2f} {r['linear_q']:10.2f} "
              f"{r['rawfp']:9.2f} {share:6.1f}% {err:11.3e}")
        rows[name] = {**r, "quant_share_pct": round(share, 1), "max_abs_err": err}
    return rows


if __name__ == "__main__":
    print(f"torch {torch.__version__} threads={torch.get_num_threads()} EASE={T.EASE[0]}")
    out = {}
    out["dim288_ladder2m"] = run(288)
    out["dim512_ladder10m"] = run(512)
    print("\nJSON " + json.dumps(out))
