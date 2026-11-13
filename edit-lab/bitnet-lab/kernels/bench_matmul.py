# Muse's work - Muse's side. Kernel benchmark 1: ternary x int8 matmul variants.
# Reference math = train.py's BitLinear values: per-layer weight scale s (abs-mean),
# ternary weights t in {-1,0,1}, activations quantized per-row to int8 by absmax
# (x_q = round(x*127/top) * top/127). Output compared against F.linear(x_q, t*s) in fp32.
import json, time
import torch
import torch.nn.functional as F

torch.set_num_threads(2)
torch.manual_seed(20261112)

def bench(fn, reps=9, warm=3):
    for _ in range(warm):
        fn()
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter(); fn(); ts.append(time.perf_counter() - t0)
    ts.sort()
    return ts[len(ts) // 2]

def quantize_rows(x):
    top = x.abs().amax(-1, keepdim=True).clamp(min=1e-5)
    q = (x * 127 / top).round().clamp(-128, 127)
    return q, top / 127  # int8-valued fp32 codes, per-row dequant scale

def run_case(rows, k, n, label):
    x = torch.randn(rows, k) * 0.7
    t = torch.randint(-1, 2, (n, k)).float()          # ternary weights
    s = torch.tensor(0.043)                            # per-layer scale (abs-mean-like)
    xq_codes, xscale = quantize_rows(x)
    xq = xq_codes * xscale                             # dequantized activations (fp32)
    wq = t * s
    ref = F.linear(xq, wq)                             # (a) direct: current approach
    xi = xq_codes.to(torch.int8)                       # int8 activation codes
    wi = t.to(torch.int8)                              # int8 ternary weights

    out = {}
    out['direct_fp32'] = bench(lambda: F.linear(xq, wq))

    # (a2) direct integer: int32 matmul of codes @ ternary, rescale once at the end.
    def int_path():
        acc = xi.to(torch.int32) @ wi.t().to(torch.int32)
        return acc.float() * (xscale * s)
    r_int = int_path()
    out['direct_int32_err'] = (r_int - ref).abs().max().item()
    out['direct_int32'] = bench(int_path)

    # (b) LUT, TL2-like: groups of 4 along K; per (row, group) a table of all 3^4=81
    # ternary combos of the 4 int8 codes, built by DP; output = sum of gathers.
    G, T = 4, 81
    assert k % G == 0
    groups = k // G
    powers = torch.tensor([27, 9, 3, 1])
    widx = ((wi.reshape(n, groups, G) + 1) * powers).sum(-1)   # [n, groups] in 0..80
    # combo coefficient matrix [81, 4] with entries in {-1,0,1}
    combos = torch.zeros(T, G, dtype=torch.int32)
    for c in range(T):
        v, rem = [], c
        for p in (27, 9, 3, 1):
            d = rem // p; rem -= d * p; v.append(d - 1)
        combos[c] = torch.tensor(v)
    xi32 = xi.to(torch.int32)
    def lut_path():
        xg = xi32.view(rows, groups, G)
        tables = torch.einsum('rgk,tk->rgt', xg, combos)       # [rows, groups, 81]
        acc = torch.zeros(rows, n, dtype=torch.int32)
        for g in range(groups):
            acc += tables[:, g].gather(1, widx[:, g].unsqueeze(0).expand(rows, n).long())
        return acc.float() * (xscale * s)
    r_lut = lut_path()
    out['lut_g4_err'] = (r_lut - ref).abs().max().item()
    out['lut_g4'] = bench(lut_path, reps=3, warm=1)

    # (c) on-the-fly: start from RAW fp32 x each call (quantize inside), integer matmul.
    def otf_path():
        q, xs = quantize_rows(x)
        acc = q.to(torch.int8).to(torch.int32) @ wi.t().to(torch.int32)
        return acc.float() * (xs * s)
    r_otf = otf_path()
    out['onthefly_int_err'] = (r_otf - ref).abs().max().item()
    out['onthefly_int'] = bench(otf_path)
    out['quantize_only'] = bench(lambda: quantize_rows(x))
    print(json.dumps({'case': label, 'rows': rows, 'k': k, 'n': n,
                      'ref_out_scale': ref.abs().max().item(), **out}))
    return out

# Champion block linears (dim 192) at full training rows 8192.
run_case(8192, 192, 576, 'champ_qkv')
run_case(8192, 192, 768, 'champ_up')
run_case(8192, 768, 192, 'champ_down')
# Ladder 2M block linears (dim 288).
run_case(8192, 288, 864, 'lad2m_qkv')
run_case(8192, 288, 1152, 'lad2m_up')
run_case(8192, 1152, 288, 'lad2m_down')
# LM head at reduced rows (8192 x 4096 fp32 out = 134 MB; too big beside the ladder).
run_case(2048, 192, 4096, 'champ_head_r2048')
run_case(2048, 288, 4096, 'lad2m_head_r2048')
