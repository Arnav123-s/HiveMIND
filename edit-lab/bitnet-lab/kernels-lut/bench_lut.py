#!/usr/bin/env python3
"""bench_lut.py — LUT ternary x int8 matmul strike team (Muse's work, Muse's side).

Lookup-table (TL1/TL2-style) ternary-weight x int8-activation matmul variants
vs the plain torch reference, at the BitNet lab's real BitLinear shapes.

WHAT IS BEING MEASURED
  The trainer (train.py BitLinear) quantizes weights to ternary {-1,0,+1} and
  activations to int8, then multiplies in fp32 with F.linear. The matmul core
  is therefore:  Y[n,m] = sum_k W[m,k] * X[n,k],  W ternary, X int8-valued.
  The per-token activation scale and per-matrix weight scale are scalars
  applied outside the matmul; they are identical for every variant and are
  excluded here (noted in RESULTS-LUT.md).

  All values in the core are integers with |Y| <= 2048*127 = 260,096 < 2^24,
  so fp32 arithmetic on them is EXACT regardless of summation order. The
  reference is therefore an exact oracle: any nonzero max-abs-error is a
  real bug in the variant, not rounding noise.

VARIANTS
  ref    : F.linear(X_fp32, W_fp32) — the trainer's actual op (oracle).
  lut2   : TL2-style, group g=2. Per token and input pair, a 9-entry table of
           all signed pair sums s0*x0 + s1*x1 (s in {-1,0,1}^2), built with one
           small matmul against the 9 sign patterns. Each output then gathers
           its precomputed pair sum by the weight pair's base-3 code and adds
           K/2 gathered values instead of doing K multiplies.
  lut4   : TL1-style widened, group g=4. 81-entry tables built by combining
           two pair tables (hi pair x lo pair); K/4 gathers per output.
  int8mm : CONTEXT ROW ONLY (not a LUT variant): torch._int_mm with the
           ternary weights stored as int8. Shows what a purpose-built integer
           GEMM does with the same operands, for scale.

  Weight base-3 codes are precomputed once per weight matrix (in a real
  deployment the codes ARE the weight storage) and are excluded from timing.
  Table construction depends on X, so it is per-forward work and IS timed.

FORWARD-ONLY: these are inference-style forward benches. None of the LUT
variants has a backward pass; trainer use would need an STE-gradient wrapper
(straight-through estimator around the quantized forward). See RESULTS-LUT.md.

CONTENTION: the timing phase refuses to time a cell while a foreign lab
process (scale ladder, mill, growth, another train.py) is running; it waits
a bounded time per cell and otherwise records the cell as deferred. The
correctness phase is compute-light and does not gate.

Usage:
  OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 python bench_lut.py correctness
  OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 python bench_lut.py timing [--wait-s 180]
Results append to results.jsonl next to this script; summary_timing.json is
rewritten by the timing phase.
"""

import json
import math
import subprocess
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional as F

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results.jsonl"

torch.set_num_threads(2)

N_TOKENS = 8192  # one trainer step: batch 32 x CTX 256

# (rung, dim, layers, [(K, M), ...]) — the four BitLinear matmuls per block:
# qkv K->3K, out K->K, up K->4K, down 4K->K. Ternary weights per block = 12*dim^2.
RUNGS = [
    ("champion", 192, 2, [(192, 576), (192, 192), (192, 768), (768, 192)]),
    ("scale2m", 288, 2, [(288, 864), (288, 288), (288, 1152), (1152, 288)]),
    ("scale10m", 512, 3, [(512, 1536), (512, 512), (512, 2048), (2048, 512)]),
]

# Ternary distribution matching the ladder's recorded state_hist
# (-1: 0.344, 0: 0.308, +1: 0.344, +-2 states negligible in the weights used).
TERN_P = (0.344, 0.308, 0.344)


def make_operands(K, M, n, gen):
    w = torch.multinomial(
        torch.tensor(TERN_P), K * M, replacement=True, generator=gen
    ).reshape(M, K)
    w = (w - 1).to(torch.float32)  # {-1, 0, +1}
    x = torch.randint(-128, 128, (n, K), generator=gen).to(torch.float32)
    return w, x


# ---------------------------------------------------------------- variants
def ref_fwd(x, w):
    return F.linear(x, w)


def _pair_tables(x, K):
    """x: [n, K] fp32 (int8-valued). Returns pair-sum tables [n, K/2, 9]:
    entry c = s0*x0 + s1*x1 where (s0, s1) is the base-3 digit pair of c,
    digit d -> sign (d - 1)."""
    n = x.shape[0]
    xg = x.view(n, K // 2, 2)
    patterns = torch.tensor(
        [[a - 1.0, b - 1.0] for a in range(3) for b in range(3)]
    )  # [9, 2], code = d0 * 3 + d1
    return torch.matmul(xg, patterns.t())  # [n, K/2, 9]


def weight_codes(w, g):
    """Base-3 codes per group of g ternary weights. w: [M, K] fp32 -> [M, K/g] int64.
    Digit for weight v is (v + 1) in {0, 1, 2}; code = sum digit_i * 3^(g-1-i),
    matching the pattern ordering used for the tables."""
    M, K = w.shape
    digits = (w + 1).to(torch.int64).view(M, K // g, g)
    powers = torch.tensor([3 ** (g - 1 - i) for i in range(g)], dtype=torch.int64)
    return (digits * powers).sum(-1)


def lut_fwd(x, w, codes, g, row_chunk=128, col_chunk=128):
    n, K = x.shape
    M = w.shape[0]
    G = K // g
    pair = _pair_tables(x, K)  # [n, K/2, 9]
    if g == 2:
        tables = pair
    elif g == 4:
        hi = pair[:, 0::2, :]  # first pair of each group of 4
        lo = pair[:, 1::2, :]  # second pair
        # code4 = code_hi * 9 + code_lo, value = hi_sum + lo_sum
        tables = (hi.unsqueeze(-1) + lo.unsqueeze(-2)).reshape(n, G, 81)
    else:
        raise ValueError(g)
    C = tables.shape[-1]
    out = torch.empty(n, M, dtype=torch.float32)
    for n0 in range(0, n, row_chunk):
        t = tables[n0 : n0 + row_chunk]  # [nc, G, C]
        nc = t.shape[0]
        for m0 in range(0, M, col_chunk):
            idx = codes[m0 : m0 + col_chunk]  # [mc, G]
            gathered = torch.gather(
                t.unsqueeze(1).expand(nc, idx.shape[0], G, C),
                3,
                idx.unsqueeze(0).unsqueeze(-1).expand(nc, idx.shape[0], G, 1),
            ).squeeze(-1)  # [nc, mc, G]
            out[n0 : n0 + row_chunk, m0 : m0 + col_chunk] = gathered.sum(-1)
    return out


def int8mm_fwd(x, w):
    xi = x.to(torch.int8)
    wi = w.t().contiguous().to(torch.int8)  # [K, M]
    return torch._int_mm(xi, wi).to(torch.float32)


VARIANTS = {
    "ref": lambda x, w, c2, c4: ref_fwd(x, w),
    "lut2": lambda x, w, c2, c4: lut_fwd(x, w, c2, 2),
    "lut4": lambda x, w, c2, c4: lut_fwd(x, w, c4, 4),
    "int8mm": lambda x, w, c2, c4: int8mm_fwd(x, w),
}


# ---------------------------------------------------------------- phases
def append_result(rec):
    with open(RESULTS, "a") as f:
        f.write(json.dumps(rec) + "\n")


def correctness():
    gen = torch.Generator().manual_seed(20261112)
    rows = []
    for rung, dim, layers, shapes in RUNGS:
        for K, M in shapes:
            w, x = make_operands(K, M, 512, gen)
            c2 = weight_codes(w, 2)
            c4 = weight_codes(w, 4)
            y_ref = ref_fwd(x, w)
            for name, fn in VARIANTS.items():
                try:
                    y = fn(x, w, c2, c4)
                    err = (y - y_ref).abs().max().item()
                    status = "ok"
                except Exception as e:  # noqa: BLE001 - record, don't crash
                    err, status = None, f"error: {type(e).__name__}: {e}"
                rec = {
                    "phase": "correctness",
                    "rung": rung,
                    "K": K,
                    "M": M,
                    "variant": name,
                    "max_abs_err": err,
                    "status": status,
                }
                rows.append(rec)
                append_result(rec)
                print(rec, flush=True)
    # one full-width (N=8192) correctness spot-check at the champion shape
    w, x = make_operands(192, 768, N_TOKENS, gen)
    c2, c4 = weight_codes(w, 2), weight_codes(w, 4)
    y_ref = ref_fwd(x, w)
    for name in ("lut2", "lut4"):
        y = VARIANTS[name](x, w, c2, c4)
        rec = {
            "phase": "correctness-fullwidth",
            "rung": "champion",
            "K": 192,
            "M": 768,
            "variant": name,
            "max_abs_err": (y - y_ref).abs().max().item(),
            "status": "ok",
        }
        rows.append(rec)
        append_result(rec)
        print(rec, flush=True)
    bad = [r for r in rows if r["status"] != "ok" or (r["max_abs_err"] or 0) != 0.0]
    print(f"correctness: {len(rows)} checks, {len(bad)} nonzero/error", flush=True)
    return rows


FOREIGN = ("run_scale_ladder", "growth_cycle", "screen.py", "sweep_probe",
           "run_overlap", "train.py --arm")


def lab_busy():
    out = subprocess.run(
        ["pgrep", "-af", "python"], capture_output=True, text=True
    ).stdout
    me = str(Path(__file__).name)
    for line in out.splitlines():
        if me in line:
            continue
        if any(p in line for p in FOREIGN):
            return line.strip()
    return None


def wait_for_free(wait_s):
    t0 = time.time()
    while True:
        busy = lab_busy()
        if not busy:
            return True
        if time.time() - t0 > wait_s:
            return False
        time.sleep(15)


def time_cell(fn, x, w, c2, c4):
    """Adaptive reps: one probe call, then enough reps for ~1.5 s total,
    clamped [2, 12]. Returns median ms/call."""
    with torch.inference_mode():
        fn(x, w, c2, c4)  # warmup
        t0 = time.perf_counter()
        fn(x, w, c2, c4)
        single = time.perf_counter() - t0
        reps = max(2, min(12, int(1.5 / max(single, 1e-4))))
        times = []
        for _ in range(reps):
            t0 = time.perf_counter()
            fn(x, w, c2, c4)
            times.append(time.perf_counter() - t0)
    times.sort()
    return times[len(times) // 2] * 1000.0, reps


def timing(wait_s=180):
    gen = torch.Generator().manual_seed(20261112)
    summary = {}
    for rung, dim, layers, shapes in RUNGS:
        block_totals = {}
        for K, M in shapes:
            w, x = make_operands(K, M, N_TOKENS, gen)
            c2 = weight_codes(w, 2)
            c4 = weight_codes(w, 4)
            for name, fn in VARIANTS.items():
                if not wait_for_free(wait_s):
                    rec = {"phase": "timing", "rung": rung, "K": K, "M": M,
                           "variant": name, "status": "deferred-contention",
                           "busy": lab_busy()}
                    append_result(rec)
                    print(rec, flush=True)
                    continue
                try:
                    ms, reps = time_cell(fn, x, w, c2, c4)
                    rec = {"phase": "timing", "rung": rung, "K": K, "M": M,
                           "variant": name, "ms_per_call": round(ms, 3),
                           "reps": reps, "status": "ok", "n_tokens": N_TOKENS,
                           "threads": torch.get_num_threads()}
                    block_totals[name] = block_totals.get(name, 0.0) + ms
                except Exception as e:  # noqa: BLE001
                    rec = {"phase": "timing", "rung": rung, "K": K, "M": M,
                           "variant": name, "status": f"error: {type(e).__name__}: {e}"}
                append_result(rec)
                print(rec, flush=True)
            del w, x, c2, c4
        summary[rung] = {
            "layers": layers,
            "block_ms": {k: round(v, 3) for k, v in block_totals.items()},
            "full_model_ms": {
                k: round(v * layers, 3) for k, v in block_totals.items()
            },
        }
        (HERE / "summary_timing.json").write_text(json.dumps(summary, indent=2))
        print(f"rung {rung}: {summary[rung]}", flush=True)
    return summary


if __name__ == "__main__":
    phase = sys.argv[1] if len(sys.argv) > 1 else "correctness"
    if phase == "correctness":
        correctness()
    elif phase == "timing":
        wait = 180
        if "--wait-s" in sys.argv:
            wait = int(sys.argv[sys.argv.index("--wait-s") + 1])
        timing(wait)
    else:
        sys.exit(f"unknown phase {phase}")
