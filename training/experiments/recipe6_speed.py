"""Faster: what gets a BitNet stem cell further in the same time. Same start, the same number of passages read
(600 steps of 32 = 19200), so the wall time is about equal; held loss with the weights as they are and with
their running mean. Results are kept as each ends; a run already in the file is not made again."""
import os, sys, json, time, math, random, torch, torch.nn as nn, torch.nn.functional as F
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from training import scratch as T
OUT, SEQS = sys.argv[1], int(sys.argv[2])
ONLY = sys.argv[3:]
torch.set_num_threads(4)
tk = T.tokenizer(); data = T.corpus(tk); CTX, VOCAB = T.CTX, T.VOCAB
held = [i * CTX for i in range(56541) if i % 40 == 0][::29][:96]   # the same 96 held passages as the runs before
HX = torch.stack([torch.from_numpy(data[i:i + CTX + 1].astype("int64")) for i in held])
LAM = [1.0]


class BL(nn.Linear):
    def forward(s, x):
        w = s.weight
        m = w.abs().mean().clamp(min=1e-5)
        w = w + LAM[0] * ((w / m).round().clamp(-1, 1) * m - w).detach()
        top = x.abs().amax(-1, keepdim=True).clamp(min=1e-5)
        xq = (x * 127 / top).round().clamp(-128, 127) * top / 127
        return F.linear(x + LAM[0] * (xq - x).detach(), w, s.bias)


class RMS(nn.Module):
    def __init__(s, d):
        super().__init__(); s.weight = nn.Parameter(torch.ones(d))
    def forward(s, x):
        return x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + 1e-6) * s.weight


def turn(x, cos, sin):  # rotary positions: [b, h, t, d]
    a, b = x[..., ::2], x[..., 1::2]
    return torch.stack([a * cos - b * sin, a * sin + b * cos], -1).flatten(-2)


class Block(nn.Module):
    def __init__(s, dim, heads, rope=False, act="gelu", rms=False, qknorm=False):
        super().__init__(); s.heads, s.rope, s.act, s.qknorm = heads, rope, act, qknorm
        N = RMS if rms else nn.LayerNorm
        s.n1, s.n2 = N(dim), N(dim)
        s.qkv, s.out, s.up, s.down = BL(dim, 3 * dim), BL(dim, dim), BL(dim, 4 * dim), BL(4 * dim, dim)
        if rope:
            f = 1.0 / (10000 ** (torch.arange(0, dim // heads, 2).float() / (dim // heads)))
            ang = torch.arange(CTX).float()[:, None] * f[None]
            s.register_buffer("cos", ang.cos(), persistent=False); s.register_buffer("sin", ang.sin(), persistent=False)
    def forward(s, x):
        b, t, d = x.shape
        q, k, v = s.qkv(s.n1(x)).view(b, t, 3, s.heads, d // s.heads).permute(2, 0, 3, 1, 4)
        if s.qknorm: q, k = F.normalize(q, dim=-1) * 4.0, F.normalize(k, dim=-1) * 4.0
        if s.rope: q, k = turn(q, s.cos[:t], s.sin[:t]), turn(k, s.cos[:t], s.sin[:t])
        a = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        x = x + s.out(a.transpose(1, 2).reshape(b, t, d))
        h = s.up(s.n2(x))
        return x + s.down(F.relu(h).square() if s.act == "relu2" else F.gelu(h))


class Net(nn.Module):
    def __init__(s, dim=192, layers=4, heads=4, small=False, **blk):
        super().__init__(); s.rope = blk.get("rope", False)
        s.tok, s.pos = nn.Embedding(VOCAB, dim), nn.Embedding(CTX, dim)
        s.blocks = nn.ModuleList(Block(dim, heads, **blk) for _ in range(layers))
        s.norm = (RMS if blk.get("rms") else nn.LayerNorm)(dim)
        s.apply(lambda m: nn.init.normal_(m.weight, std=0.02) if isinstance(m, (nn.Linear, nn.Embedding)) else None)
        if small:  # the layers that write into the stream start small
            for b in s.blocks:
                for m in (b.out, b.down): nn.init.normal_(m.weight, std=0.02 / math.sqrt(2 * layers))
    def next_piece(s, ids):
        x = s.tok(ids) if s.rope else s.tok(ids) + s.pos(torch.arange(ids.shape[1]))
        for b in s.blocks: x = b(x)
        return s.norm(x) @ s.tok.weight.T


def held_loss(m):
    m.eval(); lam, LAM[0] = LAM[0], 1.0; out = []
    with torch.no_grad():
        for j in range(0, len(HX), 32):
            x = HX[j:j + 32]; out.append(F.cross_entropy(m.next_piece(x[:, :-1]).reshape(-1, VOCAB), x[:, 1:].reshape(-1)).item() * len(x))
    m.train(); LAM[0] = lam; return sum(out) / len(HX)


def done():
    try: return json.load(open(OUT))
    except Exception: return {}


def run(name, lr=3e-3, batch=32, anneal=0.5, wd=0.01, ema=0.99, seqs=None, **shape):
    if name in done() or (ONLY and not any(o in name for o in ONLY)): return (done().get(name) or {}).get("held")
    n = (seqs or SEQS) // batch
    torch.manual_seed(0); rnd = random.Random(0)
    m = Net(**shape)
    opt = torch.optim.AdamW(m.parameters(), lr=lr, weight_decay=wd, betas=(0.9, 0.95))
    mean = {k: v.clone() for k, v in m.state_dict().items()}; keep = ema ** (batch / 32)
    warm = max(1, 200 * 32 // batch)
    t0, losses = time.time(), []
    for step in range(n):
        LAM[0] = min(1.0, step / (anneal * n)) if anneal else 1.0
        for g in opt.param_groups: g["lr"] = lr * min(1.0, (step + 1) / warm)
        at = [rnd.randrange(0, len(data) - CTX - 1) for _ in range(batch)]
        x = torch.stack([torch.from_numpy(data[i:i + CTX + 1].astype("int64")) for i in at])
        loss = F.cross_entropy(m.next_piece(x[:, :-1]).reshape(-1, VOCAB), x[:, 1:].reshape(-1))
        opt.zero_grad(set_to_none=True); loss.backward(); nn.utils.clip_grad_norm_(m.parameters(), 1.0); opt.step()
        losses.append(loss.item())
        with torch.no_grad():
            for k, v in m.state_dict().items(): mean[k].mul_(keep).add_(v, alpha=1 - keep)
    minutes = (time.time() - t0) / 60
    res = {"held": round(held_loss(m), 4), "minutes": round(minutes, 1), "steps": n, "batch": batch, "lr": lr, "anneal": anneal, **shape}
    now = {k: v.clone() for k, v in m.state_dict().items()}
    m.load_state_dict(mean); res["held, running mean of the weights"] = round(held_loss(m), 4); m.load_state_dict(now)
    res["train_last"] = round(sum(losses[-(100 * 32 // batch):]) / (100 * 32 // batch), 4)
    allr = done(); allr[name] = res; json.dump(allr, open(OUT, "w"), indent=1)
    print(name, res, flush=True); return res["held"]


base = run("as built in (32 at a time)")
got = {}
for name, kw in {
    "16 at a time, twice the steps": dict(batch=16),
    "16 at a time, rate 2e-3": dict(batch=16, lr=2e-3),
    "8 at a time, four times the steps, rate 2e-3": dict(batch=8, lr=2e-3),
    "rotary positions": dict(rope=True),
    "relu squared instead of gelu": dict(act="relu2"),
    "a plainer norm (no mean, no shift)": dict(rms=True),
    "the layers that write into the stream start small": dict(small=True),
    "normed queries and keys": dict(qknorm=True),
}.items():
    got[name] = (run(name, **kw), kw)
won = {}
for name, (g, kw) in sorted(got.items(), key=lambda kv: (kv[1][0] is None, kv[1][0])):
    if g is not None and base is not None and g < base - 0.01 and not any(k in won for k in kw): won.update(kw)
if len(won) > 1: run("every change that helped, together: " + json.dumps(won, sort_keys=True), **won)
