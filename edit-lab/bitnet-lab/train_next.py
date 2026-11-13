# Muse's work — written by Muse, on Muse's side. Fable's HiveMIND was read read-only; nothing on Fable's side was touched.
# STAGING FILE (2026-11-12, mill flag factory): train_next.py is train.py plus the mill
# pool's deferred flags, built WITHOUT touching the live train.py while the scale ladder
# runs against it. The main agent merges this file into train.py after review; until then
# the mill keeps deferring the entries below. Every flag defaults OFF (absent = the exact
# chassis behaviour of train.py, verified seed-for-seed — see mill/FLAGS-BUILT.md).
# NOTE for the merge: mill/sweep_probe.py carries a verbatim copy of train.py's argparse
# and run_one; any flag that ever becomes champion (champion.json's run string is executed
# by the sweep for job zero) needs the same flag added there too. All mill entries using
# the flags below are process-mode, so nothing in the sweep needs them today.

"""BitNet direct-training experiments, Muse's side. A from-scratch reimplementation of the
mechanisms described in BITNET-DIRECT-TRAINER-STUDY-2026-11-11.md (Fable's repo was read,
never executed or modified). Arms:
  plain    - vote counter, exactly as scratch.Direct(votes=32): median strong gate, int8
             counter clamped +-32, flip one step at 32 net votes, counter resets.
  ste      - the published way: latent fp weights + AdamW, Fable's built-in recipe
             (lr 3e-3, warmup 200 steps, rounding eased in over the first half of the run).
  mag      - magnitude-weighted votes (study C1): every weight votes with a clipped
             magnitude clip(round(-g/mean|g|), -3, +3), int16 counter, threshold 96, no gate.
  layered  - Arnav's idea: weight = sum of TWO independently vote-trained ternary weights
             (levels -2..+2, two int8 counters per weight, at most one component flips per
             weight per step). Full architecture.
  layered_half - layered with half the ternary weights (2 blocks instead of 4): the
             equal-total-state-bytes comparison (2 counters x half the weights = plain's
             1 counter x all the weights, up to the small packed-state difference).
  plain_half - plain vote counter at half width (2 blocks, 884,736 weights, 3 levels):
             the missing control for layered_half (2026-11-12) — same size, same step
             count, no second layer. If it matches layered_half, the win was the steps.
  ste_half - gradient/STE trainer (built-in recipe, unchanged) at the same half width:
             does STE also gain from half size and its extra steps?
  anneal   - plain votes with the threshold annealed 8 -> 64 linearly over the run (study C2).
  annealflip - annealed stochastic flips (mill MILL-223/224, study A1): per weight a
             neighbour flip is proposed and accepted with probability min(1, exp(-dL/T)),
             dL estimated from the gradient already computed; T anneals --temp A:B.
  disarm   - probability-state trainer (mill MILL-225, study A2): two Bernoulli logits
             per weight, state = b+ - b- in {-1,0,1}; antithetic pair (u, 1-u) forwards
             per step, logits updated by the antithetic difference estimator (DisARM
             family — see mill/FLAGS-BUILT.md for the exact form used).
  resid8 / resid16 - accumulator dial (mill MILL-226/227, study A3): per-weight residual
             r += -lr*g; a flip fires when r crosses one installed quantum, which is then
             subtracted from r. resid8 stores r on an int8 grid, resid16 in fp16.
  fisherflip - measured greedy flips (mill MILL-228..230, study A5): gradients averaged
             over 4 batches, candidate flips ranked by estimated loss change with a
             diagonal-Fisher penalty, top --share applied tentatively and kept or undone
             by measured loss on a fixed check batch; the share halves on rejection.
  --rope   - with any arm: rotary positions Fable's way (their scratch.rotated at 4bd8308) instead
             of the built-in table of places; the table is still carried, exactly as in their shape,
             but not used. Recorded under the arm name + "_rope".
  --carry  - layered arms only (round 2, 2026-11-12): overshoot carry — the vote counters no
             longer saturate at +-V and no longer reset on a flip; a flip keeps count - sign*V
             (the direct-trainer study's one-line lever, tested separately). Counters are int16
             so they can hold the overshoot. Recorded under the arm name + "_carry".
  --cooldown - layered arms only (round 2, 2026-11-12): two-stage cooldown on the AdamW parts
             only (embeddings, norms, per-layer scales), Microsoft b1.58 style: stage 1 (first
             half of the run) at the current constant lr, stage 2 (second half) with lr and
             weight decay decayed linearly toward zero. The vote rule (threshold, gate) never
             changes — this is NOT the anneal arm, which moved the vote threshold and lost.
             Recorded under the arm name + "_cooldown".
  scale ladder (2026-11-12): --dim / --layers-n override the built-in shape (defaults reproduce
             every prior arm exactly); --steps N runs a fixed step budget instead of a time box
             (equal tokens across rungs; --minutes remains a safety cap); --tag suffixes the
             recorded arm label; --ckpt turns on gradient checkpointing (memory-only trade,
             same math) for rungs that do not fit this VM otherwise.
  mill flags (2026-11-12, all default OFF; one line each — mechanism detail lives in
             mill/IDEA-POOL.md and mill/FLAGS-BUILT.md):
             --qk-norm/--qk-norm-q/--qk-norm-k  per-head RMSNorm on Q and/or K before RoPE.
             --gated-attn / --gated-attn-lr R   FP sigmoid gate on the attention output
             (optionally low-rank R). --sink-logit: one learned per-head sink logit in the
             softmax denominator. --qk-clip TAU: rescale a head's Q/K when its max logit
             exceeds TAU. --rope-frac F: rotate only the first F of each head's dims.
             --rope-base B: rotary base (chassis 10000). --nope-every N: every Nth block
             position-free. --swa L:G:W: sliding-window/global block hybrid.
             --gqa N / --heads N: KV head count / attention head count.
             --scale-gran G: weight-scale granularity tensor|channel|group32|group64|
             group128|boundary (per-output-channel/group absmean scales, in BitLinear and
             the vote trainers' install). --wquant absmax: absmax instead of absmean weight
             quant statistic. --agrid balanced: median-centred activation grid.
             --learn-scale: the BitLinear scale is a learned parameter. --lowrank R: rank-R
             FP side path per BitLinear. --hadamard: Hadamard rotation of the attention-out
             and FFN-down inputs before activation quant.
             --norm rms|prepost|post|none: norm family/placement. --subln: extra norms
             before the out and down projections. --no-ffn-norm: drop the FFN pre-norm.
             --ffn gelu|swiglu|relu2|relu and --ffn-width M: FFN form and inner width.
             --emb-int8: tied embedding/head table quantised to INT8 per row.
             --untie-head: separate FP head table. --init-std S: weight init std.
             --deltanet N / --rwkv N: recurrent blocks in an N:1 hybrid with attention
             (FP state and gates, ternary projections). --moe E --moe-top K --moe-shared
             --moe-hash-first: coarse MoE FFN inside the same total weight budget.
             --mtp W: auxiliary t+2 prediction head (training-only). --kd A [--kd-attn]:
             logits distillation from an FP twin trained first inside the same run.
             --fp-first F: FP forward for the first F of the run, ternary after (EASE
             schedule). --ease F / --ease-off: rounding ease-in over the first F of the
             run for any arm / ease disabled. --failweight W: oversample the worst-decile
             training windows W-fold.
             --votes N: vote threshold (Direct/Layered; int16 counters above 127).
             --gate-q Q: strong-gate quantile (chassis 0.5 = the median gate).
             --mag-cal X: magnitude votes, no gate, threshold calibrated at the first
             step to X * 32 * measured mean |increment| (Direct, int16 counters).
             --vsched A:B: vote threshold schedule A -> B over the run (Layered).
             --vlayer T: per-layer adaptive threshold tracking flip rate T/step (Layered).
             --leak L: fractional counter leak count <- L*count + vote (Layered, fp
             counters). --ileak N: every N steps all counters step one toward 0 (Layered).
             --agree: a vote counts only if it matches last step's pull (Layered).
             --freeze K: a component flipping >= K times in a 40-step window freezes at
             its modal state for the rest of the run (Layered). --clamp F|none: counter
             clamp at F x V, or none = no clamp and no reset on flip (Layered, int16).
             --flip-rule R: counter|t1-first|sign-agree|alternate flip arbitration
             (Layered; default and t1-first are the chassis rule). --comps N / --comp-v
             A,B,..: component count / per-component thresholds (Layered). --modal K:
             readout = per-weight modal state over the last K saved states (Layered,
             eval-side). --verify-flips N: every N steps, near-threshold flips are
             verified by measured loss on a check batch and only winners fire (Layered).
             --whiten: per-layer second-moment normalisation + Hadamard rotation of the
             gradient field before signing (Layered). --hybrid F:ste|F:votes: phase
             hand-off between the vote and STE trainers at fraction F of the run.
             --opt-lr LR: AdamW lr of the shared (non-ternary) parts in the vote arms.
             STE recipe: --ste-lr, --ste-warmup, --ste-wd, --two-stage (abrupt mid-run
             lr drop), --two-stage-wd (plus stage-1 cosine weight decay to 0.1, off in
             stage 2), --muon [--muon-split] (Muon for matrix params, AdamW for the
             rest; split = per-head orthogonalisation of QKV), --polish F (after the
             run, F more steps at lr 3e-4).
             Round-2 priority flags: --corpus NAME (corpus stream: v1 | v2 | variant
             name resolved to corpus-<name>.u16; held windows always follow the same
             every-40th rule on the chosen stream); --wd X (AdamW weight decay of the
             shared parts — on Layered it is also the cooldown schedule's base, closing
             the chassis confound where cooldown decayed a wd of 0); --buffer B
             (exclude training windows within B window positions of a held window);
             --log-level-hist (record layered level populations + per-component flip
             counts); --cooldown-noemb (cooldown schedule skips the embedding group).
             --vote-kernel fused: the kernel stream's fused vote-counter update
             (kernels/RESULTS-KERNELS.md section 2) — bitwise-identical state,
             in-place counters, sign computed once; default "current" (chassis form).
All arms: same corpus, same seed -> same init and same batch stream, batch 32, CTX 256,
held windows (every 40th) never trained on, judged on a fixed set of 128 held windows.
Non-ternary parts in the vote arms train exactly as Fable's Direct: AdamW lr 1e-3,
betas (0.9, 0.95), weight decay 0, per-layer scale via the hand-set gradient (g.t)*scale."""
import argparse, hashlib, json, math, random, time
from collections import deque
from pathlib import Path
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

LAB = Path(__file__).resolve().parent
VOCAB, DIM, HEADS, CTX = 4096, 192, 4, 256
HELD_EVERY = 40
EASE = [1.0]
FRAC = [0.0]  # run-progress fraction, set by the training loop each step (mill: --act-sparsify)
BUFFER = [0]  # mill A-050: held-adjacency exclusion radius in windows (0 = chassis rule)

def _near_held(w, B):
    r = w % HELD_EVERY
    return min(r, HELD_EVERY - r) <= B

def offsets(rnd, n, batch):
    out = []
    B = BUFFER[0]
    while len(out) < batch:
        i = rnd.randrange(0, n - CTX - 1)
        if B:
            if _near_held(i // CTX, B) or _near_held((i + CTX) // CTX, B):
                continue
            out.append(i)
        elif (i // CTX) % HELD_EVERY and ((i + CTX) // CTX) % HELD_EVERY:
            out.append(i)
    return out

class RMSNorm(nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.w = nn.Parameter(torch.ones(dim))
    def forward(self, x):
        return x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + 1e-6) * self.w

def make_norm(dim, kind):
    if kind == "rms":
        return RMSNorm(dim)
    if kind == "none":
        return nn.Identity()
    return nn.LayerNorm(dim)

_HAD = {}

def _had(d):
    if d not in _HAD:
        h = torch.ones(1, 1)
        while h.shape[0] < d:
            h = torch.cat([torch.cat([h, h], 1), torch.cat([h, -h], 1)], 0)
        _HAD[d] = h / math.sqrt(d)
    return _HAD[d]

def fwht_pad(x):
    """Orthonormal Hadamard rotation along the last dim (zero-padded to a power of two)."""
    n = x.shape[-1]
    N = 1
    while N < n:
        N *= 2
    if N == n:
        return x @ _had(n)
    return (F.pad(x, (0, N - n)) @ _had(N))[..., :n]

def _wstat(v, wquant):
    """Quantisation statistic over the last dim: absmean (chassis) or absmax (MILL-1011)."""
    return v.abs().mean(-1) if wquant == "absmean" else v.abs().amax(-1)

def _bounds(n, G):
    if G is None:
        return [(0, n)]
    return [(i, min(i + G, n)) for i in range(0, n, G)]

def _gran_quant(w, G, wquant):
    """Ternary quantisation of a weight tensor with per-(row, group) scales.
    G None = one per-tensor statistic (the --wquant absmax path; the absmean tensor
    path stays in BitLinear.forward verbatim)."""
    if G is None:
        s = (w.abs().mean() if wquant == "absmean" else w.abs().max()).clamp(min=1e-5)
        return (w / s).round().clamp(-1, 1) * s
    parts = []
    for i0, i1 in _bounds(w.shape[1], G):
        c = w[:, i0:i1]
        s = _wstat(c, wquant).clamp(min=1e-5)[:, None]
        parts.append((c / s).round().clamp(-1, 1) * s)
    return torch.cat(parts, 1)

def scale_init(w, G, wquant):
    """(ternary state, log-scale parameter) for a fresh BitLinear weight.
    G None + absmean reproduces the chassis init exactly."""
    if G is None:
        s = (w.abs().mean() if wquant == "absmean" else w.abs().max()).clamp(min=1e-5)
        return (w.detach() / s).round().clamp(-1, 1), torch.nn.Parameter(s.log())
    ts, lss = [], []
    for i0, i1 in _bounds(w.shape[1], G):
        c = w.detach()[:, i0:i1]
        s = _wstat(c, wquant).clamp(min=1e-5)
        ts.append((c / s[:, None]).round().clamp(-1, 1))
        lss.append(s.log())
    return torch.cat(ts, 1), torch.nn.Parameter(torch.stack(lss, 1))

def install_w(t, ls, G):
    """Installed fp weight for ternary state t under log-scales ls (chassis formula
    per group: t * exp(ls) / mean|t|). G None reproduces the chassis install exactly."""
    if G is None:
        return t * (ls.exp() / t.abs().mean().clamp(min=1e-5))
    parts = []
    for j, (i0, i1) in enumerate(_bounds(t.shape[1], G)):
        tc = t[:, i0:i1]
        parts.append(tc * (ls[:, j].exp() / tc.abs().mean(1).clamp(min=1e-5))[:, None])
    return torch.cat(parts, 1)

def ls_grad(g, t, ls, G):
    """Hand-set log-scale gradient: (g . t) * scale, per group when G is set.
    G None reproduces the chassis expression exactly."""
    if G is None:
        return (g * t).sum() * ls.exp()
    cols = []
    for j, (i0, i1) in enumerate(_bounds(g.shape[1], G)):
        cols.append((g[:, i0:i1] * t[:, i0:i1]).sum(1) * ls[:, j].exp())
    return torch.stack(cols, 1)

class BitLinear(nn.Linear):
    """Chassis forward is statement-identical to train.py when every mill option is off.
    Options (all from the arch dict, all default off): gran_g (resolved scale group size
    or None), wquant, agrid, learn_scale (scale is a learned parameter), lowrank (rank of
    an FP side path), hadamard (rotate the input before activation quant)."""
    def __init__(self, in_features, out_features, arch=None, proj=""):
        super().__init__(in_features, out_features)
        A = arch or {}
        self.proj = proj
        gran = A.get("gran")
        if gran == "channel" or (gran == "boundary" and proj in ("qkv", "out", "down")):
            self.gran_g = in_features
        elif isinstance(gran, str) and gran.startswith("group"):
            self.gran_g = int(gran[len("group"):])
        else:
            self.gran_g = None
        self.wquant = A.get("wquant", "absmean")
        self.agrid = A.get("agrid", "absmax")
        self.hadamard = bool(A.get("hadamard")) and proj in ("out", "down")
        self.learn_scale = bool(A.get("learn_scale"))
        if self.learn_scale:
            self.scale_param = nn.Parameter(torch.zeros(()))
        r = int(A.get("lowrank", 0) or 0)
        if r > 0:
            self.lr_a = nn.Parameter(torch.randn(in_features, r) * 0.02)
            self.lr_b = nn.Parameter(torch.zeros(r, out_features))
        else:
            self.lr_a = None
            self.lr_b = None
    def refresh_scale(self):
        """Re-anchor a learned scale to the current weight's statistic (called after
        Tiny's init pass and by main() before the trainer is built)."""
        if self.learn_scale:
            with torch.no_grad():
                self.scale_param.copy_(self.weight.detach().abs().mean().clamp(min=1e-5).log())
    def forward(self, x):
        w, ease = self.weight, EASE[0]
        if self.hadamard:
            x = fwht_pad(x)
        if self.learn_scale:
            s = self.scale_param.exp()
            z = w / s
            w = w + ease * ((z.round().clamp(-1, 1) - z).detach() * s)
        elif self.gran_g is None and self.wquant == "absmean":
            scale = w.abs().mean().clamp(min=1e-5)
            w = w + ease * ((w / scale).round().clamp(-1, 1) * scale - w).detach()
        else:
            wq = _gran_quant(w, self.gran_g, self.wquant)
            w = w + ease * (wq - w).detach()
        if self.agrid == "balanced":
            c = torch.median(x, -1, keepdim=True).values
            top = (x - c).abs().amax(-1, keepdim=True).clamp(min=1e-5)
            xq = ((x - c) * 127 / top).round().clamp(-128, 127) * top / 127 + c
            x = x + ease * (xq - x).detach()
        else:
            top = x.abs().amax(-1, keepdim=True).clamp(min=1e-5)
            x = x + ease * ((x * 127 / top).round().clamp(-128, 127) * top / 127 - x).detach()
        y = F.linear(x, w, self.bias)
        if self.lr_b is not None:
            y = y + (x @ self.lr_a) @ self.lr_b
        return y

def rotated(x, cos, sin):
    """Rotary positions, Fable's way (their scratch.rotated, read in the audit copy at 4bd8308 and
    reimplemented here): each interleaved pair of numbers of a query or key is turned by an angle
    that grows with its place in the text. x: [batch, heads, places, numbers]; cos/sin: [places, pairs].
    Kernel (2026-11-13, kernels/RESULTS-KERNELS.md section 3): the identical
    interleaved-pair rotation computed as one complex multiply by the unit rotor
    cos+i*sin — measured bitwise identical (max abs err 0.0) to the slice/stack form
    and 1.4-2.9x faster on the full rope+attention path, so it is the staging default
    (no flag); identity is re-proven per-step in flaglab/proof.py."""
    xc = torch.view_as_complex(x.reshape(*x.shape[:-1], -1, 2).contiguous())
    return torch.view_as_real(xc * torch.complex(cos, sin)).flatten(-2)

class MoeFFN(nn.Module):
    """Coarse MoE FFN (mill MILL-120..122): E expert FFNs + one always-on shared expert,
    top-K routing, FP router, experts sized so the total FFN weight budget matches the
    chassis FFN (inner width 4*dim/(E + shared)). Hash routing (first block) sends token
    id % E to a fixed expert with weight 1."""
    def __init__(self, dim, n_exp, top, shared, hash_first, arch):
        super().__init__()
        self.n_exp, self.top = n_exp, top
        self.hash_first = hash_first
        w = max(8, int(round(4 * dim / (n_exp + (1 if shared else 0)))))
        def expert():
            e = nn.Module()
            e.up = BitLinear(dim, w, arch, "up")
            e.down = BitLinear(w, dim, arch, "down")
            return e
        self.experts = nn.ModuleList([expert() for _ in range(n_exp)])
        self.shared = expert() if shared else None
        self.router = nn.Linear(dim, n_exp)
    def _expert(self, e, x):
        return e.down(F.gelu(e.up(x)))
    def forward(self, x, ids=None):
        b, t, d = x.shape
        xf = x.reshape(-1, d)
        out = torch.zeros_like(xf)
        if self.hash_first and ids is not None:
            idx = ids.reshape(-1) % self.n_exp
            for e in range(self.n_exp):
                m = idx == e
                if bool(m.any()):
                    out[m] = self._expert(self.experts[e], xf[m])
        else:
            pr = torch.softmax(self.router(xf), -1)
            vals, idx = pr.topk(self.top, dim=-1)
            for e in range(self.n_exp):
                for s in range(self.top):
                    m = idx[:, s] == e
                    if bool(m.any()):
                        out[m] = out[m] + self._expert(self.experts[e], xf[m]) * vals[m, s][:, None]
        if self.shared is not None:
            out = out + self._expert(self.shared, xf)
        return out.view(b, t, d)

class Block(nn.Module):
    """Chassis block; with every mill arch option off, forward executes the original
    statements (see plain_attn fast path and the pre-norm branch)."""
    def __init__(self, dim=DIM, heads=HEADS, rotary=False, arch=None):
        super().__init__()
        A = arch or {}
        self.heads = heads
        self.kind = A.get("kind", "attn")
        self.norm_kind = A.get("norm")
        self.n1, self.n2 = make_norm(dim, self.norm_kind), make_norm(dim, self.norm_kind)
        if A.get("no_ffn_norm"):
            self.n2 = nn.Identity()
        if self.norm_kind == "prepost":
            self.p1, self.p2 = nn.LayerNorm(dim), nn.LayerNorm(dim)
        self.kv_heads = A.get("kv_heads", heads)
        self.window = A.get("window")
        self.qk_clip = A.get("qk_clip")
        self.sink_on = bool(A.get("sink"))
        self.subln = bool(A.get("subln"))
        self.ffn_kind = A.get("ffn", "gelu")
        self.sparsify = A.get("sparsify")
        self.gate, self.gate1, self.gate2 = None, None, None
        self.rotary = rotary
        hd = dim // heads
        frac = A.get("rope_frac", 1.0)
        self.rd = int(hd * frac) // 2 * 2
        if rotary and self.rd > 0:
            base = A.get("rope_base", 10000)
            angle = torch.arange(CTX).float()[:, None] / (base ** (torch.arange(0, self.rd, 2).float() / hd))[None]
            self.register_buffer("cos", angle.cos(), persistent=False)
            self.register_buffer("sin", angle.sin(), persistent=False)
        if self.kind == "delta":
            self.dq, self.dk, self.dv = (BitLinear(dim, dim, A, "qkv") for _ in range(3))
            self.dg = BitLinear(dim, 2 * heads, A, "qkv")
            self.do = BitLinear(dim, dim, A, "out")
        elif self.kind == "rwkv":
            self.r_, self.k_, self.v_ = (BitLinear(dim, dim, A, "qkv") for _ in range(3))
            self.w_ = BitLinear(dim, heads, A, "qkv")
            self.g_ = BitLinear(dim, dim, A, "qkv")
            self.o_ = BitLinear(dim, dim, A, "out")
            self.mu = nn.Parameter(torch.zeros(5, dim))
        else:
            kv = dim * self.kv_heads // heads
            self.qkv, self.out = BitLinear(dim, dim + 2 * kv, A, "qkv"), BitLinear(dim, dim, A, "out")
            qk = A.get("qk_norm")
            if qk in ("both", "q"):
                self.qn = RMSNorm(hd)
            if qk in ("both", "k"):
                self.kn = RMSNorm(hd)
            if A.get("gated_lr"):
                self.gate1 = nn.Linear(dim, int(A["gated_lr"]))
                self.gate2 = nn.Linear(int(A["gated_lr"]), dim)
            elif A.get("gated"):
                self.gate = nn.Linear(dim, dim)
            if self.sink_on:
                self.sink = nn.Parameter(torch.zeros(heads))
        self.plain_attn = (self.kind == "attn" and self.kv_heads == heads
                           and not hasattr(self, "qn") and not hasattr(self, "kn")
                           and self.rd == hd and not self.sink_on and not self.qk_clip
                           and not self.window and self.gate is None and self.gate1 is None)
        moe = A.get("moe")
        self.moe = None
        self.wants_ids = False
        if moe:
            n_exp, top, shared, hash_first = moe
            self.moe = MoeFFN(dim, n_exp, top, shared,
                              bool(hash_first) and bool(A.get("moe_first")), A)
            self.wants_ids = self.moe.hash_first
        else:
            inner = int(round(dim * A.get("ffn_width", 4.0)))
            if self.ffn_kind == "swiglu":
                self.up, self.down = BitLinear(dim, 2 * inner, A, "up"), BitLinear(inner, dim, A, "down")
            else:
                self.up, self.down = BitLinear(dim, inner, A, "up"), BitLinear(inner, dim, A, "down")
            if self.subln:
                self.s1, self.s2 = nn.LayerNorm(dim), nn.LayerNorm(inner)
    def _qkv(self, h):
        b, t, d = h.shape
        hd = d // self.heads
        kvd = d * self.kv_heads // self.heads
        qkv = self.qkv(h)
        q = qkv[..., :d].view(b, t, self.heads, hd).permute(0, 2, 1, 3)
        k = qkv[..., d:d + kvd].view(b, t, self.kv_heads, hd).permute(0, 2, 1, 3)
        v = qkv[..., d + kvd:].view(b, t, self.kv_heads, hd).permute(0, 2, 1, 3)
        if self.kv_heads < self.heads:
            rep = self.heads // self.kv_heads
            k = k.repeat_interleave(rep, dim=1)
            v = v.repeat_interleave(rep, dim=1)
        if hasattr(self, "qn"):
            q = self.qn(q)
        if hasattr(self, "kn"):
            k = self.kn(k)
        if self.rotary and self.rd > 0:
            cos, sin = self.cos[:t], self.sin[:t]
            if self.rd < hd:
                q = torch.cat([rotated(q[..., :self.rd], cos, sin), q[..., self.rd:]], -1)
                k = torch.cat([rotated(k[..., :self.rd], cos, sin), k[..., self.rd:]], -1)
            else:
                q, k = rotated(q, cos, sin), rotated(k, cos, sin)
        return q, k, v
    def _mix(self, h, ids=None):
        if self.kind == "delta":
            return self._delta(h)
        if self.kind == "rwkv":
            return self._rwkv(h)
        b, t, d = h.shape
        if self.plain_attn:
            q, k, v = self.qkv(h).view(b, t, 3, self.heads, d // self.heads).permute(2, 0, 3, 1, 4)
            if self.rotary:
                q, k = rotated(q, self.cos[:t], self.sin[:t]), rotated(k, self.cos[:t], self.sin[:t])
            a = F.scaled_dot_product_attention(q, k, v, is_causal=True).transpose(1, 2).reshape(b, t, d)
        else:
            q, k, v = self._qkv(h)
            hd = d // self.heads
            if self.sink_on or self.qk_clip or self.window:
                if self.qk_clip:
                    with torch.no_grad():
                        sc = q @ k.transpose(-2, -1) / math.sqrt(hd)
                        sc = sc.masked_fill(torch.triu(torch.ones(t, t, dtype=torch.bool), 1), float("-inf"))
                        mx = sc.amax(dim=(-2, -1)).clamp(min=1e-9)
                        f = (self.qk_clip / mx).clamp(max=1.0).sqrt()
                    q = q * f[:, :, None, None]
                    k = k * f[:, :, None, None]
                scores = q @ k.transpose(-2, -1) / math.sqrt(hd)
                idx = torch.arange(t)
                mask = (idx[None, :] > idx[:, None])
                if self.window:
                    mask = mask | ((idx[:, None] - idx[None, :]) >= self.window)
                scores = scores.masked_fill(mask, float("-inf"))
                if self.sink_on:
                    m = scores.amax(-1, keepdim=True)
                    p = torch.exp(scores - m)
                    denom = p.sum(-1, keepdim=True) + torch.exp(self.sink[None, :, None, None] - m)
                    a = (p / denom) @ v
                else:
                    a = torch.softmax(scores, -1) @ v
                a = a.transpose(1, 2).reshape(b, t, d)
            else:
                a = F.scaled_dot_product_attention(q, k, v, is_causal=True).transpose(1, 2).reshape(b, t, d)
        if self.gate is not None or self.gate1 is not None:
            g = torch.sigmoid(self.gate(h)) if self.gate is not None else torch.sigmoid(self.gate2(self.gate1(h)))
            a = (a.view(b, t, self.heads, d // self.heads)
                 * g.view(b, t, self.heads, d // self.heads)).reshape(b, t, d)
        if self.subln:
            a = self.s1(a)
        return self.out(a)
    def _delta(self, h):
        """Gated-DeltaNet-style recurrent mix (mill MILL-116): FP state S per head,
        sigmoid beta/decay gates, delta-rule update, L2-normalised Q/K, ternary
        projections. Sequential over positions, as the recurrence requires."""
        b, t, d = h.shape
        H, hd = self.heads, d // self.heads
        q = F.normalize(self.dq(h).view(b, t, H, hd), dim=-1)
        k = F.normalize(self.dk(h).view(b, t, H, hd), dim=-1)
        v = self.dv(h).view(b, t, H, hd)
        g = self.dg(h).view(b, t, H, 2)
        beta, alpha = g[..., 0].sigmoid(), g[..., 1].sigmoid()
        S = torch.zeros(b, H, hd, hd)
        outs = []
        for i in range(t):
            ki, qi, vi = k[:, i], q[:, i], v[:, i]
            S = S * alpha[:, i][:, :, None, None]
            pred = (ki[..., :, None] * S).sum(-2)
            S = S + ki[..., :, None] * (beta[:, i][:, :, None, None] * (vi - pred)[..., None, :])
            outs.append((qi[..., :, None] * S).sum(-2) * (hd ** -0.5))
        return self.do(torch.stack(outs, 1).reshape(b, t, d))
    def _rwkv(self, h):
        """RWKV-style recurrent mix (mill MILL-117): learned token-shift mixes, per-head
        exponential decay, matrix state, gated output; ternary projections, FP state."""
        b, t, d = h.shape
        H, hd = self.heads, d // self.heads
        prev = torch.cat([torch.zeros_like(h[:, :1]), h[:, :-1]], 1)
        xr = h + self.mu[0] * (prev - h)
        xk = h + self.mu[1] * (prev - h)
        xv = h + self.mu[2] * (prev - h)
        xw = h + self.mu[3] * (prev - h)
        xg = h + self.mu[4] * (prev - h)
        r = self.r_(xr).view(b, t, H, hd)
        k = self.k_(xk).view(b, t, H, hd)
        v = self.v_(xv).view(b, t, H, hd)
        w = torch.exp(-torch.exp(self.w_(xw)))
        g = torch.sigmoid(self.g_(xg))
        S = torch.zeros(b, H, hd, hd)
        outs = []
        for i in range(t):
            S = S * w[:, i][:, :, None, None]
            S = S + k[:, i][..., :, None] * v[:, i][..., None, :]
            outs.append((r[:, i][..., :, None] * S).sum(-2))
        return self.o_(torch.stack(outs, 1).reshape(b, t, d) * g)
    def _ffn(self, h, ids=None):
        if self.moe is not None:
            return self.moe(h, ids)
        if self.ffn_kind == "swiglu":
            u = self.up(h)
            a1, a2 = u.chunk(2, dim=-1)
            x = F.silu(a1) * a2
        elif self.ffn_kind == "relu2":
            x = F.relu(self.up(h)) ** 2
        elif self.ffn_kind == "relu":
            x = F.relu(self.up(h))
        else:
            x = F.gelu(self.up(h))
        if self.subln:
            x = self.s2(x)
        if self.sparsify is not None and FRAC[0] >= self.sparsify:
            thr = torch.median(x.abs(), -1, keepdim=True).values
            x = x * (x.abs() >= thr)
        return self.down(x)
    def forward(self, x, ids=None):
        if self.norm_kind == "post":
            x = self.n1(x + self._mix(x, ids))
            return self.n2(x + self._ffn(x, ids))
        if self.norm_kind == "prepost":
            x = self.p1(x + self._mix(self.n1(x), ids))
            return self.p2(x + self._ffn(self.n2(x), ids))
        x = x + self._mix(self.n1(x), ids)
        return x + self._ffn(self.n2(x), ids)

class Tiny(nn.Module):
    def __init__(self, layers=4, dim=DIM, rotary=False, arch=None):
        super().__init__()
        A = arch or {}
        self.dim = dim
        self.ckpt = False  # scale ladder (2026-11-12): gradient checkpointing, memory-only trade
        self.tok, self.pos = nn.Embedding(VOCAB, dim), nn.Embedding(CTX, dim)
        self.rotary = rotary  # then the table of places (pos) is carried, as in Fable's shape, but not used
        self.emb_int8 = bool(A.get("emb_int8"))
        self.head = nn.Embedding(VOCAB, dim) if A.get("untie") else None
        heads = A.get("heads", HEADS)
        blocks = []
        for i in range(layers):
            ba = dict(A)
            kind = "attn"
            if A.get("deltanet") and (i % (A["deltanet"] + 1)) < A["deltanet"]:
                kind = "delta"
            if A.get("rwkv") and (i % (A["rwkv"] + 1)) < A["rwkv"]:
                kind = "rwkv"
            ba["kind"] = kind
            brot = rotary and not (A.get("nope_every") and (i + 1) % A["nope_every"] == 0)
            if A.get("swa"):
                L, G, W = A["swa"]
                ba["window"] = W if (i % (L + G)) < L else None
            ba["moe_first"] = (i == 0)
            blocks.append(Block(dim, heads, rotary=brot, arch=ba))
        self.blocks = nn.ModuleList(blocks)
        self.norm = make_norm(dim, A.get("norm"))
        std = A.get("init_std", 0.02)
        def _init(m):
            if isinstance(m, (nn.Linear, nn.Embedding)):
                nn.init.normal_(m.weight, std=std)
            if isinstance(m, BitLinear):
                m.refresh_scale()
        self.apply(_init)
    def emb_w(self):
        w = self.tok.weight
        if not self.emb_int8:
            return w
        s = w.abs().amax(1, keepdim=True).clamp(min=1e-5) / 127
        q = (w / s).round().clamp(-128, 127) * s
        return w + (q - w).detach()
    def body(self, ids):
        if self.emb_int8:
            x = F.embedding(ids, self.emb_w())
            if not self.rotary:
                x = x + self.pos(torch.arange(ids.shape[1]))
        else:
            x = self.tok(ids) if self.rotary else self.tok(ids) + self.pos(torch.arange(ids.shape[1]))
        for blk in self.blocks:
            if self.ckpt and self.training:
                x = torch.utils.checkpoint.checkpoint(blk, x, use_reentrant=False)
            else:
                x = blk(x, ids)
        return self.norm(x)
    def next_piece(self, ids):
        W = self.head.weight if self.head is not None else self.emb_w()
        return self.body(ids) @ W.T
    def last_attn_probs(self, ids):
        """Last block's per-head attention probabilities (mill --kd-attn only; assumes
        the chassis pre-norm structure the KD entries run on)."""
        x = self.tok(ids) if self.rotary else self.tok(ids) + self.pos(torch.arange(ids.shape[1]))
        for blk in self.blocks[:-1]:
            x = blk(x, ids)
        blk = self.blocks[-1]
        q, k, v = blk._qkv(blk.n1(x))
        t = ids.shape[1]
        scores = q @ k.transpose(-2, -1) / math.sqrt(q.shape[-1])
        scores = scores.masked_fill(torch.triu(torch.ones(t, t, dtype=torch.bool), 1), float("-inf"))
        return torch.softmax(scores, -1)

def install_sum(ts, ls, G):
    """Layered install: the summed state scaled by exp(ls)/mean|sum| — per group when
    G is set. G None reproduces the chassis Layered.install exactly."""
    s = ts[0]
    for t in ts[1:]:
        s = s + t
    if G is None:
        return s * (ls.exp() / s.abs().mean().clamp(min=1e-5))
    parts = []
    for j, (i0, i1) in enumerate(_bounds(s.shape[1], G)):
        sc = s[:, i0:i1]
        parts.append(sc * (ls[:, j].exp() / sc.abs().mean(1).clamp(min=1e-5))[:, None])
    return torch.cat(parts, 1)

def _quantum(t, ls, G):
    """Installed-weight step size per entry (gradient-based dL estimates, mill arms)."""
    if G is None:
        return torch.full_like(t, float(ls.exp() / t.abs().mean().clamp(min=1e-5)))
    parts = []
    for j, (i0, i1) in enumerate(_bounds(t.shape[1], G)):
        tc = t[:, i0:i1]
        parts.append(torch.full_like(tc, 0.0) + (ls[:, j].exp() / tc.abs().mean(1).clamp(min=1e-5))[:, None])
    return torch.cat(parts, 1)

def _ce_on(model, xb):
    """Plain CE of the model on one [batch, CTX+1] window batch, current EASE kept."""
    was = model.training
    model.eval()
    with torch.no_grad():
        L = F.cross_entropy(model.next_piece(xb[:, :-1]).reshape(-1, VOCAB), xb[:, 1:].reshape(-1))
    if was:
        model.train()
    return float(L)

class Direct:
    """Vote-counter trainer (Fable's mechanism, reimplemented). mode: plain | mag | anneal.
    Mill extensions (all default off): --gate-q (strong-gate quantile in place of the
    median), --mag-cal (mode magcal: magnitude votes, no gate, threshold calibrated at
    the first step to cal x 32 x measured mean |increment|), --clamp (counter clamp at
    clamp x V instead of V), --opt-lr (AdamW lr of the shared parts)."""
    def __init__(self, model, lr=1e-3, mode="plain", votes=32, gate_q=0.5, mag_cal=None,
                 clamp=None, opt_lr=None, wd=None, vote_kernel="current"):
        if opt_lr is not None:
            lr = opt_lr
        self.fused = (vote_kernel == "fused")
        self.mode = "magcal" if mag_cal is not None else mode
        self.votes, self.steps = votes, 0
        self.gate_q, self.mag_cal, self.clamp = gate_q, mag_cal, clamp
        self.mag_thr = None
        self.layers = [m for m in model.modules() if isinstance(m, BitLinear)]
        own = {id(m.weight) for m in self.layers}
        self.t, self.log_scale = [], []
        for m in self.layers:
            t, ls = scale_init(m.weight.data, m.gran_g, m.wquant)
            self.t.append(t)
            self.log_scale.append(ls)
        self.opt = torch.optim.AdamW([p for p in model.parameters() if id(p) not in own] + self.log_scale,
                                     lr=lr, weight_decay=wd if wd is not None else 0.0, betas=(0.9, 0.95))
        dt = torch.int32 if (votes > 32767 or mag_cal is not None) else (
            torch.int16 if (self.mode == "mag" or clamp is not None or votes > 127) else torch.int8)
        self.count = [torch.zeros_like(t, dtype=dt) for t in self.t]
        self.model = model
        self.install()
    def install(self):
        with torch.no_grad():
            for m, t, ls in zip(self.layers, self.t, self.log_scale):
                m.weight.copy_(install_w(t, ls, m.gran_g))
    def threshold(self, done):
        if self.mode == "mag":
            return 96
        if self.mode == "magcal":
            return self.mag_thr if self.mag_thr is not None else 96
        if self.mode == "anneal":
            return int(round(8 + 56 * done))
        return self.votes
    def step(self, loss, done=0.0, x=None, y=None):
        self.opt.zero_grad(set_to_none=True)
        for m in self.layers:
            m.weight.grad = None
        loss.backward()
        nn.utils.clip_grad_norm_([p for g in self.opt.param_groups for p in g["params"] if p.grad is not None], 1.0)
        jumped, total = 0, 0
        V = self.threshold(done)
        with torch.no_grad():
            for i, m in enumerate(self.layers):
                g, t = m.weight.grad, self.t[i]
                self.log_scale[i].grad = ls_grad(g, t, self.log_scale[i], m.gran_g)
                c = self.count[i]
                if self.mode in ("mag", "magcal"):
                    inc = (-g / g.abs().mean().clamp(min=1e-12)).round().clamp(-3, 3)
                    if self.mode == "magcal" and self.mag_thr is None:
                        self.mag_thr = max(1, int(round(self.mag_cal * 32 * float(inc.abs().mean()))))
                        V = self.mag_thr
                    if self.fused:
                        # --vote-kernel fused: in-place counters, sign once, exact flip test
                        c.add_(inc.to(c.dtype)).clamp_(-V, V)
                        s = c.sign()
                        over = c.abs() >= V
                        go = over & (s != 0) & (t != s)
                        want = t + s
                        c.masked_fill_(over, 0)
                    else:
                        c = (c + inc.to(c.dtype)).clamp(-V, V)
                        go = c.abs() >= V
                        want = (t + c.sign()).clamp(-1, 1)
                        self.count[i] = torch.where(go, torch.zeros_like(c), c)
                        go = go & (want != t)
                else:
                    if self.gate_q == 0.5:
                        strong = g.abs() >= g.abs().median()
                    else:
                        strong = g.abs() >= torch.quantile(g.abs().reshape(-1).float(), self.gate_q)
                    vote = (-g.sign() * strong).to(c.dtype)
                    bound = V if self.clamp is None else max(1, int(round(self.clamp * V)))
                    if self.fused:
                        c.add_(vote).clamp_(-bound, bound)
                        s = c.sign()
                        over = c.abs() >= V
                        go = over & (s != 0) & (t != s)
                        want = t + s
                        c.masked_fill_(over, 0)
                    else:
                        c = (c + vote).clamp(-bound, bound)
                        go = c.abs() >= V
                        want = (t + c.sign()).clamp(-1, 1)
                        self.count[i] = torch.where(go, torch.zeros_like(c), c)
                        go = go & (want != t)
                self.t[i] = torch.where(go, want, t)
                jumped, total = jumped + int(go.sum()), total + t.numel()
        self.opt.step()
        self.install()
        self.steps += 1
        return jumped / total

class Layered:
    """Weight = sum of N ternary components, each with its own vote counter (chassis:
    N=2, V=32 — at most one component flips per weight per step, first component first,
    a component whose flip would be a boundary no-op passes its turn to the next; only
    the flipped component's counter resets). Mill extensions (all default off):
    --comps/--comp-v, --gate-q, --leak (fractional fp counters), --ileak, --agree,
    --freeze, --clamp (x V, or "none" = no clamp and no reset on flip), --flip-rule
    (t1-first = the chassis rule | counter | sign-agree | alternate), --vsched,
    --vlayer, --whiten, --opt-lr. --carry/--cooldown are the chassis round-2 levers."""
    def __init__(self, model, lr=1e-3, votes=32, carry=False, cooldown=False, comps=2,
                 comp_v=None, gate_q=0.5, leak=None, ileak=None, agree=False, freeze=None,
                 clamp=None, flip_rule="t1-first", vsched=None, vlayer=None, whiten=False,
                 opt_lr=None, wd=None, cooldown_noemb=False, vote_kernel="current"):
        if opt_lr is not None:
            lr = opt_lr
        self.fused = (vote_kernel == "fused")
        self.votes, self.steps = votes, 0
        self.carry, self.cooldown = carry, cooldown
        self.base_lr, self.base_wd = lr, (wd if wd is not None else 0.0)  # mill E-015: --wd gives the cooldown a real base
        self.N = comps
        self.Vs = [float(v) for v in comp_v] if comp_v else [float(votes)] * comps
        self.gate_q, self.leak, self.ileak, self.agree = gate_q, leak, ileak, agree
        self.freeze, self.clamp, self.flip_rule = freeze, clamp, flip_rule
        self.vsched, self.vlayer_t, self.whiten = vsched, vlayer, whiten
        self.layers = [m for m in model.modules() if isinstance(m, BitLinear)]
        own = {id(m.weight) for m in self.layers}
        self.ts, self.log_scale = [], []
        for m in self.layers:
            t0, ls = scale_init(m.weight.data, m.gran_g, m.wquant)
            self.ts.append([t0] + [torch.zeros_like(t0) for _ in range(comps - 1)])
            self.log_scale.append(ls)
        self.cooldown_noemb = cooldown_noemb
        self.emb_group = None
        if cooldown_noemb:
            # mill E-016: embeddings form their own group; the cooldown schedule never
            # touches it (constant lr and wd), norms + scales + the rest decay as usual.
            emb_ids = {id(p) for p in model.tok.parameters()} | {id(p) for p in model.pos.parameters()}
            if getattr(model, "head", None) is not None:
                emb_ids |= {id(p) for p in model.head.parameters()}
            g_main = [p for p in model.parameters() if id(p) not in own and id(p) not in emb_ids] + self.log_scale
            g_emb = [p for p in model.parameters() if id(p) in emb_ids]
            self.opt = torch.optim.AdamW([{"params": g_main}, {"params": g_emb}],
                                         lr=lr, weight_decay=self.base_wd, betas=(0.9, 0.95))
            self.emb_group = 1
        else:
            self.opt = torch.optim.AdamW([p for p in model.parameters() if id(p) not in own] + self.log_scale,
                                         lr=lr, weight_decay=self.base_wd, betas=(0.9, 0.95))
        mx = max(self.Vs)
        if leak is not None:
            cdt = torch.float32
        elif mx > 32767 or clamp == "none":
            cdt = torch.int32
        elif carry or mx > 127 or clamp is not None:
            cdt = torch.int16
        else:
            cdt = torch.int8
        self.cs = [[torch.zeros_like(self.ts[i][0], dtype=cdt) for _ in range(comps)]
                   for i in range(len(self.layers))]
        self.pull = [torch.zeros_like(self.ts[i][0]) for i in range(len(self.layers))] if agree else None
        self.frozen = [[torch.zeros_like(self.ts[i][0], dtype=torch.bool) for _ in range(comps)]
                       for i in range(len(self.layers))] if freeze is not None else None
        self.flips = [[torch.zeros_like(self.ts[i][0], dtype=torch.int32) for _ in range(comps)]
                      for i in range(len(self.layers))] if freeze is not None else None
        self.hist = [[deque(maxlen=10) for _ in range(comps)]
                     for _ in range(len(self.layers))] if freeze is not None else None
        self.vmul = [[1.0] * comps for _ in self.layers] if vlayer is not None else None
        self.level_flips = None  # mill E-013: main sets this to [0]*N to start counting
        self.vema = [[0.0] * comps for _ in self.layers] if vlayer is not None else None
        self.model = model
        self.install()
    def install(self):
        with torch.no_grad():
            for m, ts, ls in zip(self.layers, self.ts, self.log_scale):
                m.weight.copy_(install_sum(ts, ls, m.gran_g))
    def _thresholds(self, i, done):
        out = []
        for ci in range(self.N):
            V = self.Vs[ci]
            if self.vsched is not None:
                V = self.vsched[0] + (self.vsched[1] - self.vsched[0]) * min(1.0, done)
            if self.vlayer_t is not None:
                V = V * self.vmul[i][ci]
            out.append(V)
        return out
    def _arbitrate(self, i, Vs, signs=None):
        ts, cs = self.ts[i], self.cs[i]
        cand = []
        for ci in range(self.N):
            if signs is not None:
                # --vote-kernel fused: (t + s).clamp(-1,1) != t  <=>  (s != 0) & (t != s)
                eff = (signs[ci] != 0) & (ts[ci] != signs[ci])
            else:
                eff = (ts[ci] + cs[ci].sign()).clamp(-1, 1) != ts[ci]
            c = (cs[ci].abs() >= Vs[ci]) & eff
            if self.frozen is not None:
                c = c & ~self.frozen[i][ci]
            cand.append(c)
        if self.flip_rule == "counter" and self.N > 1:
            overs = torch.stack([cs[ci].abs() - Vs[ci] for ci in range(self.N)])
            overs = torch.where(torch.stack(cand), overs, torch.full_like(overs, float("-inf")))
            mx = overs.amax(0)
            gos, taken = [], torch.zeros_like(cand[0])
            for ci in range(self.N):
                go = cand[ci] & (overs[ci] >= mx) & ~taken
                gos.append(go)
                taken = taken | go
            return gos
        if self.flip_rule == "sign-agree":
            gos = []
            for ci in range(self.N):
                ok = torch.ones_like(cand[ci])
                for j in range(self.N):
                    if j != ci:
                        ok = ok & ((cs[j] == 0) | (cs[j].sign() == cs[ci].sign()))
                gos.append(cand[ci] & ok)
            return gos
        if self.flip_rule == "alternate":
            return [cand[ci] & ((self.steps + 1) % self.N == ci) for ci in range(self.N)]
        gos, taken = [], torch.zeros_like(cand[0])  # t1-first: the chassis rule
        for ci in range(self.N):
            go = cand[ci] & ~taken
            gos.append(go)
            taken = taken | go
        return gos
    def verify(self, xb, done, budget=32):
        """--verify-flips: near-threshold candidate flips are tried one at a time and
        kept only if the measured loss on the check batch does not rise. The check
        batch is drawn from the training distribution, never from held windows."""
        base = _ce_on(self.model, xb)
        cands = []
        for i in range(len(self.layers)):
            Vs = self._thresholds(i, done)
            for ci in range(self.N):
                c = self.cs[i][ci]
                near = (c.abs() >= Vs[ci] - 4).nonzero()
                for r, col in near.tolist():
                    cands.append((float(c[r, col].abs()), i, ci, r, col))
        cands.sort(key=lambda z: -z[0])
        kept = 0
        for _, i, ci, r, col in cands[:budget]:
            t, c = self.ts[i][ci], self.cs[i][ci]
            old = float(t[r, col])
            new = max(-1.0, min(1.0, old + (1.0 if float(c[r, col]) > 0 else -1.0)))
            if new == old:
                continue
            t[r, col] = new
            self.install()
            now = _ce_on(self.model, xb)
            if now <= base:
                base = now
                c[r, col] = 0
                kept += 1
            else:
                t[r, col] = old
                self.install()
        return kept
    def step(self, loss, done=0.0, x=None, y=None):
        if self.cooldown:
            # Two-stage schedule on the AdamW parts only: stage 1 constant, stage 2
            # (second half) lr and weight decay decayed linearly toward zero. The
            # vote threshold and gate below never see `done` — the vote rule is fixed.
            mult = 1.0 if done < 0.5 else max(0.0, (1.0 - done) / 0.5)
            for gi, g in enumerate(self.opt.param_groups):
                if self.emb_group is not None and gi == self.emb_group:
                    g["lr"] = self.base_lr
                    g["weight_decay"] = self.base_wd
                else:
                    g["lr"] = self.base_lr * mult
                    g["weight_decay"] = self.base_wd * mult
        self.opt.zero_grad(set_to_none=True)
        for m in self.layers:
            m.weight.grad = None
        loss.backward()
        nn.utils.clip_grad_norm_([p for g in self.opt.param_groups for p in g["params"] if p.grad is not None], 1.0)
        jumped, total = 0, 0
        with torch.no_grad():
            for i, m in enumerate(self.layers):
                g0 = m.weight.grad
                g = fwht_pad(g0 / g0.pow(2).mean().sqrt().clamp(min=1e-12)) if self.whiten else g0
                ts = self.ts[i]
                s = ts[0]
                for t in ts[1:]:
                    s = s + t
                self.log_scale[i].grad = ls_grad(g0, s, self.log_scale[i], m.gran_g)
                if self.gate_q == 0.5:
                    strong = g.abs() >= g.abs().median()
                else:
                    strong = g.abs() >= torch.quantile(g.abs().reshape(-1).float(), self.gate_q)
                raw = -g.sign() * strong
                vote = raw * (raw == self.pull[i]) if self.agree else raw
                if self.agree:
                    self.pull[i] = raw
                Vs = self._thresholds(i, done)
                signs = None
                if self.fused:
                    # --vote-kernel fused (kernels/RESULTS-KERNELS.md section 2):
                    # counters updated in place, sign computed once per component.
                    signs = []
                    for ci in range(self.N):
                        c = self.cs[i][ci]
                        if self.leak is not None:
                            c.mul_(self.leak).add_(vote).clamp_(-Vs[ci], Vs[ci])
                        elif self.carry:
                            c.add_(vote.to(c.dtype))
                        else:
                            c.add_(vote.to(c.dtype))
                            if self.clamp is None:
                                c.clamp_(-int(round(Vs[ci])), int(round(Vs[ci])))
                            elif self.clamp != "none":
                                b = max(1, int(round(self.clamp * Vs[ci])))
                                c.clamp_(-b, b)
                        if self.frozen is not None:
                            c.masked_fill_(self.frozen[i][ci], 0)
                        signs.append(c.sign())
                else:
                    for ci in range(self.N):
                        c = self.cs[i][ci]
                        if self.leak is not None:
                            nc = (self.leak * c + vote).clamp(-Vs[ci], Vs[ci])
                        elif self.carry:
                            nc = c + vote.to(c.dtype)
                        else:
                            nc = c + vote.to(c.dtype)
                            if self.clamp is None:
                                nc = nc.clamp(-int(round(Vs[ci])), int(round(Vs[ci])))
                            elif self.clamp != "none":
                                b = max(1, int(round(self.clamp * Vs[ci])))
                                nc = nc.clamp(-b, b)
                        if self.frozen is not None:
                            nc = torch.where(self.frozen[i][ci], torch.zeros_like(nc), nc)
                        self.cs[i][ci] = nc
                gos = self._arbitrate(i, Vs, signs)
                for ci in range(self.N):
                    go = gos[ci]
                    c = self.cs[i][ci]
                    if self.fused:
                        self.ts[i][ci] = torch.where(go, ts[ci] + signs[ci].float(), ts[ci])
                        if self.carry:
                            self.cs[i][ci] = torch.where(go, c - signs[ci] * int(round(Vs[ci])), c)
                        elif self.clamp != "none":
                            self.cs[i][ci] = torch.where(go, torch.zeros_like(c), c)
                    else:
                        self.ts[i][ci] = torch.where(go, (ts[ci] + c.sign()).clamp(-1, 1), ts[ci])
                        if self.carry:
                            self.cs[i][ci] = torch.where(go, c - c.sign() * int(round(Vs[ci])), c)
                        elif self.clamp != "none":
                            self.cs[i][ci] = torch.where(go, torch.zeros_like(c), c)
                    jumped += int(go.sum())
                    if self.level_flips is not None:
                        self.level_flips[ci] += int(go.sum())
                    if self.flips is not None:
                        self.flips[i][ci] += go.to(torch.int32)
                    if self.vlayer_t is not None:
                        rate = float(go.float().mean())
                        self.vema[i][ci] = 0.9 * self.vema[i][ci] + 0.1 * rate
                        if self.vema[i][ci] > self.vlayer_t:
                            self.vmul[i][ci] *= 1.05
                        elif self.vema[i][ci] < 0.5 * self.vlayer_t:
                            self.vmul[i][ci] *= 0.95
                total += ts[0].numel()
                if self.ileak is not None and (self.steps + 1) % self.ileak == 0:
                    for ci in range(self.N):
                        c = self.cs[i][ci]
                        self.cs[i][ci] = c - c.sign()
                if self.freeze is not None and (self.steps + 1) % 10 == 0:
                    for ci in range(self.N):
                        self.hist[i][ci].append(self.ts[i][ci].clone())
                    if (self.steps + 1) % 40 == 0:
                        for ci in range(self.N):
                            need = (self.flips[i][ci] >= self.freeze) & ~self.frozen[i][ci]
                            if bool(need.any()) and len(self.hist[i][ci]) >= 2:
                                st = torch.stack(list(self.hist[i][ci]))
                                mode = st.mode(0).values
                                self.ts[i][ci] = torch.where(need, mode, self.ts[i][ci])
                                self.frozen[i][ci] = self.frozen[i][ci] | need
                                self.cs[i][ci] = torch.where(need, torch.zeros_like(self.cs[i][ci]), self.cs[i][ci])
                            self.flips[i][ci].zero_()
        self.opt.step()
        self.install()
        self.steps += 1
        return jumped / total

class STE:
    """The published way: latent fp weights, AdamW lr 3e-3, warmup 200, wd 0.01 (built-in recipe).
    Mill extensions (all default off): --ste-lr/--ste-warmup/--ste-wd recipe knobs,
    --two-stage (abrupt lr drop to 3e-4 at the run's midpoint), --two-stage-wd (plus a
    stage-1 cosine weight-decay ramp to 0.1, off in stage 2), --muon [--muon-split]
    (Muon for matrix params, AdamW for the rest), --polish via fixed_lr()."""
    def __init__(self, model, lr=3e-3, warm=200, wd=0.01, muon=False, muon_split_hd=None,
                 two_stage=False, two_stage_wd=False):
        self.lr, self.warm, self.steps, self.model = lr, warm, 0, model
        self.two_stage, self.two_stage_wd = two_stage, two_stage_wd
        self.fixed = None
        self.muon_opt = None
        if muon:
            mats, rest = [], []
            for name, p in model.named_parameters():
                if p.dim() == 2 and not name.startswith(("tok.", "pos.", "head.")):
                    mats.append(p)
                else:
                    rest.append(p)
            self.muon_opt = MuonOpt(mats, lr=lr, split_hd=muon_split_hd)
            self.opt = torch.optim.AdamW(rest, lr=lr, weight_decay=wd, betas=(0.9, 0.95))
        else:
            self.opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=wd, betas=(0.9, 0.95))
    def fixed_lr(self, lr):
        self.fixed = lr
    def state_bytes(self):
        if self.muon_opt is None:
            return None
        mset = {id(p) for p in self.muon_opt.params}
        return sum(4 * p.numel() + (4 if id(p) in mset else 8) * p.numel()
                   for p in self.model.parameters())
    def step(self, loss, done=0.0, x=None, y=None):
        if self.fixed is not None:
            lr_now = self.fixed
        elif self.two_stage and done >= 0.5:
            lr_now = 3e-4
        else:
            lr_now = self.lr * min(1.0, (self.steps + 1) / max(1, self.warm))
        for g in self.opt.param_groups:
            g["lr"] = lr_now
        if self.two_stage_wd:
            wd_now = 0.1 * (0.5 - 0.5 * math.cos(math.pi * min(1.0, done / 0.5))) if done < 0.5 else 0.0
            for g in self.opt.param_groups:
                g["weight_decay"] = wd_now
        if self.muon_opt is not None:
            self.muon_opt.param_groups[0]["lr"] = lr_now
            self.muon_opt.zero_grad()
        self.opt.zero_grad(set_to_none=True)
        loss.backward()
        nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
        self.opt.step()
        if self.muon_opt is not None:
            self.muon_opt.step()
        self.steps += 1
        return 0.0

def _ns_orth(G, split=None):
    """Newton-Schulz orthogonalisation (the Muon quintic iteration)."""
    def one(X):
        X = X.float()
        X = X / (X.norm() + 1e-7)
        tr = X.shape[0] > X.shape[1]
        if tr:
            X = X.T
        a, b, c = 3.4445, -4.7750, 2.0315
        for _ in range(5):
            A = X @ X.T
            X = a * X + (b * A + c * (A @ A)) @ X
        return X.T if tr else X
    if split and G.shape[0] > split and G.shape[0] % split == 0:
        return torch.cat([one(G[i:i + split]) for i in range(0, G.shape[0], split)], 0)
    return one(G)

class MuonOpt:
    """Minimal Muon: Nesterov momentum + Newton-Schulz orthogonalised update, step
    scaled by lr * sqrt(max(1, rows/cols)). split_hd orthogonalises per-head row
    blocks of the update instead of the whole matrix (--muon-split)."""
    def __init__(self, params, lr=3e-3, momentum=0.95, split_hd=None):
        self.params = list(params)
        self.bufs = [torch.zeros_like(p) for p in self.params]
        self.momentum = momentum
        self.split_hd = split_hd
        self.param_groups = [{"lr": lr}]
    def zero_grad(self):
        for p in self.params:
            p.grad = None
    def step(self):
        lr = self.param_groups[0]["lr"]
        for p, buf in zip(self.params, self.bufs):
            if p.grad is None:
                continue
            buf.mul_(self.momentum).add_(p.grad)
            g = p.grad + self.momentum * buf
            o = _ns_orth(g, self.split_hd)
            p.data.add_(o.to(p.dtype), alpha=-lr * math.sqrt(max(1.0, p.shape[0] / max(1, p.shape[1]))))

class AnnealFlip:
    """Annealed stochastic flips (mill MILL-223/224): each step, per weight, propose a
    neighbour move (an extreme proposes 0; a zero proposes +-1 at random), estimate the
    loss change from the gradient already computed (dL ~ g * dw * installed quantum),
    and accept with probability min(1, exp(-dL / T)); T anneals linearly over the run
    (--temp A:B). The proposals are random on purpose: a greedy proposal would have
    dL <= 0 by construction and the Metropolis test would be vacuous."""
    def __init__(self, model, lr=1e-3, temp=(1.0, 0.05), gen=None, opt_lr=None, wd=None):
        if opt_lr is not None:
            lr = opt_lr
        self.temp, self.steps = temp, 0
        self.gen = gen if gen is not None else torch.Generator().manual_seed(777)
        self.layers = [m for m in model.modules() if isinstance(m, BitLinear)]
        own = {id(m.weight) for m in self.layers}
        self.t, self.log_scale = [], []
        for m in self.layers:
            t, ls = scale_init(m.weight.data, m.gran_g, m.wquant)
            self.t.append(t)
            self.log_scale.append(ls)
        self.opt = torch.optim.AdamW([p for p in model.parameters() if id(p) not in own] + self.log_scale,
                                     lr=lr, weight_decay=wd if wd is not None else 0.0, betas=(0.9, 0.95))
        self.model = model
        self.install()
    def install(self):
        with torch.no_grad():
            for m, t, ls in zip(self.layers, self.t, self.log_scale):
                m.weight.copy_(install_w(t, ls, m.gran_g))
    def state_bytes(self):
        return sum(t.numel() // 4 for t in self.t)
    def step(self, loss, done=0.0, x=None, y=None):
        T = max(self.temp[0] + (self.temp[1] - self.temp[0]) * min(1.0, done), 1e-9)
        self.opt.zero_grad(set_to_none=True)
        for m in self.layers:
            m.weight.grad = None
        loss.backward()
        nn.utils.clip_grad_norm_([p for g in self.opt.param_groups for p in g["params"] if p.grad is not None], 1.0)
        jumped, total = 0, 0
        with torch.no_grad():
            for i, m in enumerate(self.layers):
                g, t = m.weight.grad, self.t[i]
                self.log_scale[i].grad = ls_grad(g, t, self.log_scale[i], m.gran_g)
                rnd = torch.rand(t.shape, generator=self.gen)
                dw = torch.where(t != 0, -t, torch.where(rnd < 0.5, torch.ones_like(t), -torch.ones_like(t)))
                dL = g * dw * _quantum(t, self.log_scale[i], m.gran_g)
                p = torch.exp((-dL / T).clamp(max=0.0))
                acc = torch.rand(t.shape, generator=self.gen) < p
                newt = torch.where(acc, t + dw, t)
                jumped, total = jumped + int((newt != t).sum()), total + t.numel()
                self.t[i] = newt
        self.opt.step()
        self.install()
        self.steps += 1
        return jumped / total

class Resid:
    """Accumulator dial (mill MILL-226/227): a per-weight residual r += -rate * g / quantum
    each step; when |r| crosses one installed quantum the weight flips one step and one
    quantum is subtracted from r. rate = 0.05 (chosen so a consistent gradient flips a
    weight in ~20-50 steps at lab gradient scales). resid8 stores r on an int8 grid of
    127 steps per quantum, resid16 in fp16; r saturates at +-1 quantum (so pressure on
    a boundary-blocked weight is capped, not accumulated forever)."""
    def __init__(self, model, lr=1e-3, bits=8, rate=0.05, opt_lr=None, wd=None):
        if opt_lr is not None:
            lr = opt_lr
        self.bits, self.rate, self.steps = bits, rate, 0
        self.layers = [m for m in model.modules() if isinstance(m, BitLinear)]
        own = {id(m.weight) for m in self.layers}
        self.t, self.log_scale = [], []
        for m in self.layers:
            t, ls = scale_init(m.weight.data, m.gran_g, m.wquant)
            self.t.append(t)
            self.log_scale.append(ls)
        self.opt = torch.optim.AdamW([p for p in model.parameters() if id(p) not in own] + self.log_scale,
                                     lr=lr, weight_decay=wd if wd is not None else 0.0, betas=(0.9, 0.95))
        self.r = [torch.zeros_like(t, dtype=torch.int8 if bits == 8 else torch.float16) for t in self.t]
        self.model = model
        self.install()
    def install(self):
        with torch.no_grad():
            for m, t, ls in zip(self.layers, self.t, self.log_scale):
                m.weight.copy_(install_w(t, ls, m.gran_g))
    def state_bytes(self):
        per = 1 if self.bits == 8 else 2
        return sum(per * t.numel() + t.numel() // 4 for t in self.t)
    def step(self, loss, done=0.0, x=None, y=None):
        self.opt.zero_grad(set_to_none=True)
        for m in self.layers:
            m.weight.grad = None
        loss.backward()
        nn.utils.clip_grad_norm_([p for g in self.opt.param_groups for p in g["params"] if p.grad is not None], 1.0)
        jumped, total = 0, 0
        with torch.no_grad():
            for i, m in enumerate(self.layers):
                g, t = m.weight.grad, self.t[i]
                self.log_scale[i].grad = ls_grad(g, t, self.log_scale[i], m.gran_g)
                q = _quantum(t, self.log_scale[i], m.gran_g)
                rf = (self.r[i].float() / 127.0 if self.bits == 8 else self.r[i].float()) \
                    + (-self.rate * g / q.clamp(min=1e-12))
                k = rf.trunc().clamp(-1, 1)
                newt = (t + k).clamp(-1, 1)
                applied = newt - t
                rf = (rf - applied).clamp(-1, 1)
                self.r[i] = (rf * 127).round().to(torch.int8) if self.bits == 8 else rf.to(torch.float16)
                self.t[i] = newt
                jumped, total = jumped + int((applied != 0).sum()), total + t.numel()
        self.opt.step()
        self.install()
        self.steps += 1
        return jumped / total

class FisherFlip:
    """Measured greedy flips (mill MILL-228..230): gradients are averaged over 4 batches;
    candidate flips are ranked by the estimated loss change dL = g*dw + 0.5 * F * dw^2
    with F the mean squared gradient (diagonal Fisher) and dw the installed-weight
    change of the single-step move (extremes move toward 0, zeros move along -sign(g));
    the top --share are applied tentatively and kept or undone by the measured loss on
    a fixed check batch drawn from the training distribution; the share halves on
    rejection (floor: initial share / 16)."""
    def __init__(self, model, lr=1e-3, share=0.002, check=None, opt_lr=None, wd=None):
        if opt_lr is not None:
            lr = opt_lr
        self.share, self.share0, self.steps, self.cnt = share, share, 0, 0
        self.check = check
        self.layers = [m for m in model.modules() if isinstance(m, BitLinear)]
        own = {id(m.weight) for m in self.layers}
        self.t, self.log_scale = [], []
        for m in self.layers:
            t, ls = scale_init(m.weight.data, m.gran_g, m.wquant)
            self.t.append(t)
            self.log_scale.append(ls)
        self.opt = torch.optim.AdamW([p for p in model.parameters() if id(p) not in own] + self.log_scale,
                                     lr=lr, weight_decay=wd if wd is not None else 0.0, betas=(0.9, 0.95))
        self.gs = [torch.zeros_like(t) for t in self.t]
        self.fs = [torch.zeros_like(t) for t in self.t]
        self.model = model
        self.install()
    def install(self):
        with torch.no_grad():
            for m, t, ls in zip(self.layers, self.t, self.log_scale):
                m.weight.copy_(install_w(t, ls, m.gran_g))
    def state_bytes(self):
        return sum(8 * t.numel() + t.numel() // 4 for t in self.t)
    def _round(self):
        base = _ce_on(self.model, self.check)
        total = sum(t.numel() for t in self.t)
        K = max(1, int(self.share * total))
        ests = []
        for i, m in enumerate(self.layers):
            gb, fb = self.gs[i] / 4, self.fs[i] / 4
            t = self.t[i]
            q = _quantum(t, self.log_scale[i], m.gran_g)
            dw = torch.where(t != 0, -t, -torch.sign(gb)) * q
            ests.append(gb * dw + 0.5 * fb * dw * dw)
        flat = torch.cat([e.reshape(-1) for e in ests])
        thr = flat.topk(K, largest=False).values[-1]
        old = [t.clone() for t in self.t]
        flips = 0
        for i, m in enumerate(self.layers):
            msk = ests[i] <= thr
            dwt = torch.where(self.t[i] != 0, -self.t[i], -torch.sign(self.gs[i]))
            newt = torch.where(msk, (self.t[i] + dwt).clamp(-1, 1), self.t[i])
            flips += int((newt != self.t[i]).sum())
            self.t[i] = newt
        self.install()
        now = _ce_on(self.model, self.check)
        if now <= base:
            kept = flips
        else:
            self.t = old
            self.install()
            self.share = max(self.share0 / 16, self.share / 2)
            kept = 0
        for i in range(len(self.gs)):
            self.gs[i].zero_()
            self.fs[i].zero_()
        return kept / total
    def step(self, loss, done=0.0, x=None, y=None):
        self.opt.zero_grad(set_to_none=True)
        for m in self.layers:
            m.weight.grad = None
        loss.backward()
        nn.utils.clip_grad_norm_([p for g in self.opt.param_groups for p in g["params"] if p.grad is not None], 1.0)
        share = 0.0
        with torch.no_grad():
            for i, m in enumerate(self.layers):
                g = m.weight.grad
                self.log_scale[i].grad = ls_grad(g, self.t[i], self.log_scale[i], m.gran_g)
                self.gs[i] += g
                self.fs[i] += g * g
            self.cnt += 1
            if self.cnt >= 4 and self.check is not None:
                self.cnt = 0
                share = self._round()
        self.opt.step()
        self.install()
        self.steps += 1
        return share

class DisARM:
    """Probability-state trainer (mill MILL-225): two Bernoulli logits per weight (b+
    for state +1, b- for state -1); the installed state is the modal b+ - b-. Each
    step draws an antithetic pair of samples (u, 1-u), runs both forwards, and updates
    the logits with the antithetic score-function estimator
        grad = 0.5 * [(L_A - Lbar) * (b_A - p) + (L_B - Lbar) * (b_B - p)],
    Lbar the pair mean — the DisARM family's antithetic-coupling idea in its
    score-function form, not the paper's exact correction term (see FLAGS-BUILT.md).
    Non-ternary parts and scales train from forward A's gradient, as in Direct."""
    def __init__(self, model, lr=1e-3, gen=None, opt_lr=None, wd=None):
        if opt_lr is not None:
            lr = opt_lr
        self.steps = 0
        self.gen = gen if gen is not None else torch.Generator().manual_seed(778)
        self.layers = [m for m in model.modules() if isinstance(m, BitLinear)]
        own = {id(m.weight) for m in self.layers}
        self.t, self.log_scale, self.thp, self.thm = [], [], [], []
        for m in self.layers:
            t, ls = scale_init(m.weight.data, m.gran_g, m.wquant)
            self.t.append(t)
            self.log_scale.append(ls)
            hp = torch.where(t > 0, torch.full_like(t, 2.0), torch.full_like(t, -2.0))
            hm = torch.where(t < 0, torch.full_like(t, 2.0), torch.full_like(t, -2.0))
            self.thp.append(torch.nn.Parameter(hp))
            self.thm.append(torch.nn.Parameter(hm))
        self.opt = torch.optim.AdamW([p for p in model.parameters() if id(p) not in own]
                                     + self.log_scale + self.thp + self.thm,
                                     lr=lr, weight_decay=wd if wd is not None else 0.0, betas=(0.9, 0.95))
        self.model = model
        self.install()
    def install(self):
        with torch.no_grad():
            for m, t, ls in zip(self.layers, self.t, self.log_scale):
                m.weight.copy_(install_w(t, ls, m.gran_g))
    def state_bytes(self):
        return sum(24 * t.numel() + t.numel() // 4 for t in self.t)
    def _sample(self, antithetic):
        out = []
        with torch.no_grad():
            for i in range(len(self.layers)):
                pp = torch.sigmoid(self.thp[i])
                pm = torch.sigmoid(self.thm[i])
                u = torch.rand(pp.shape, generator=self.gen)
                if antithetic:
                    u = 1 - u
                bp = (u < pp).float()
                bm = (u < pm).float()
                self.t[i] = bp - bm
                out.append((bp, bm, pp, pm))
        self.install()
        return out
    def _modal(self):
        with torch.no_grad():
            for i in range(len(self.layers)):
                self.t[i] = (torch.sigmoid(self.thp[i]) >= 0.5).float() \
                    - (torch.sigmoid(self.thm[i]) >= 0.5).float()
        self.install()
    def step(self, loss, done=0.0, x=None, y=None):
        if x is None:
            return 0.0
        A = self._sample(False)
        self.opt.zero_grad(set_to_none=True)
        for m in self.layers:
            m.weight.grad = None
        la = F.cross_entropy(self.model.next_piece(x[:, :-1]).reshape(-1, VOCAB), x[:, 1:].reshape(-1))
        la.backward()
        nn.utils.clip_grad_norm_([p for g in self.opt.param_groups for p in g["params"] if p.grad is not None], 1.0)
        with torch.no_grad():
            for i, m in enumerate(self.layers):
                self.log_scale[i].grad = ls_grad(m.weight.grad, self.t[i], self.log_scale[i], m.gran_g)
        B = self._sample(True)
        lb = _ce_on(self.model, x)
        la_v = float(la)
        bar = 0.5 * (la_v + lb)
        with torch.no_grad():
            for i in range(len(self.layers)):
                bpA, bmA, pp, pm = A[i]
                bpB, bmB, _, _ = B[i]
                self.thp[i].grad = 0.5 * ((la_v - bar) * (bpA - pp) + (lb - bar) * (bpB - pp))
                self.thm[i].grad = 0.5 * ((la_v - bar) * (bmA - pm) + (lb - bar) * (bmB - pm))
        self.opt.step()
        self._modal()
        self.steps += 1
        return 0.0

class FailPicker:
    """--failweight (mill MILL-406/407): every 50 steps, score 256 candidate training
    windows with the current model; the worst decile is oversampled so it fills
    min(1, W x 10%) of each batch."""
    def __init__(self, model, data, rnd, W):
        self.model, self.data, self.rnd, self.W = model, data, rnd, W
        self.hard = []
    def maybe_score(self, step):
        if step % 50:
            return
        was = self.model.training
        self.model.eval()
        offs = offsets(self.rnd, len(self.data), 256)
        losses = []
        with torch.no_grad():
            for i in range(0, len(offs), 32):
                b = offs[i:i + 32]
                x = torch.stack([torch.from_numpy(self.data[j:j + CTX + 1].astype("int64")) for j in b])
                losses.append(F.cross_entropy(self.model.next_piece(x[:, :-1]).reshape(-1, VOCAB),
                                              x[:, 1:].reshape(-1), reduction="none").view(len(b), -1).mean(1))
        L = torch.cat(losses)
        k = max(1, len(offs) // 10)
        self.hard = [offs[i] for i in L.topk(k).indices.tolist()]
        if was:
            self.model.train()
    def batch(self, batch):
        offs = offsets(self.rnd, len(self.data), batch)
        nh = int(round(batch * min(1.0, self.W * 0.1)))
        for i in range(min(nh, len(offs))):
            if self.hard:
                offs[i] = self.hard[self.rnd.randrange(len(self.hard))]
        return offs

def _shingle_sig(data, i):
    w = np.asarray(data[i:i + CTX + 1])
    hs = sorted({int.from_bytes(hashlib.blake2b(w[j:j + 8].tobytes(), digest_size=8).digest(), "little")
                 for j in range(len(w) - 7)})
    return hash(tuple(hs))

def sampler_filter(at, data, rnd, seen, freq_mask):
    """Mill sampler preprocessing (A-047/A-049): --dedup drops windows whose
    sorted-8-gram-shingle signature was already trained on (the first occurrence
    trains); --freq-balance half-rates windows where the corpus's 100 most frequent
    tokens cover more than 60% of positions. Replacements are fresh sampler draws."""
    out = []
    for i in at:
        keep = i
        for _try in range(9):
            ok = True
            if seen is not None:
                sig = _shingle_sig(data, keep)
                if sig in seen:
                    ok = False
                else:
                    seen.add(sig)
            if ok and freq_mask is not None:
                w = np.asarray(data[keep:keep + CTX + 1])
                if freq_mask[w].mean() > 0.6 and rnd.random() < 0.5:
                    ok = False
            if ok:
                break
            keep = offsets(rnd, len(data), 1)[0]
        out.append(keep)
    return out

def curr_len(done, mode):
    """Mill A-045/A-046 context-length curriculum, by run thirds."""
    if mode == "rev":
        return CTX if done < 1 / 3 else (128 if done < 2 / 3 else 64)
    return 64 if done < 1 / 3 else (128 if done < 2 / 3 else CTX)

def held_windows(data, n_eval=128):
    starts = [w * CTX for w in range(0, (len(data) - CTX) // CTX) if w % HELD_EVERY == 0]
    pick = [starts[int(i * (len(starts) - 1) / (n_eval - 1))] for i in range(n_eval)]
    return torch.stack([torch.from_numpy(data[s:s + CTX + 1].astype("int64")) for s in pick])

@torch.no_grad()
def held_loss(model, held):
    old = EASE[0]
    EASE[0] = 1.0
    model.eval()
    tot, n = 0.0, 0
    for i in range(0, len(held), 32):
        x = held[i:i + 32]
        tot += F.cross_entropy(model.next_piece(x[:, :-1]).reshape(-1, VOCAB), x[:, 1:].reshape(-1),
                               reduction="sum").item()
        n += x[:, 1:].numel()
    model.train()
    EASE[0] = old
    return tot / n

HALF_ARMS = ("layered_half", "plain_half", "ste_half", "annealflip", "disarm",
             "resid8", "resid16", "fisherflip")
VOTE_ARMS = ("plain", "mag", "anneal", "plain_half", "layered", "layered_half")
STE_ARMS = ("ste", "ste_half")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=["plain", "ste", "mag", "layered", "layered_half", "anneal",
                                                     "plain_half", "ste_half", "annealflip", "disarm",
                                                     "resid8", "resid16", "fisherflip"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--minutes", type=float, default=8.0)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--rope", action="store_true",
                    help="rotary positions Fable's way instead of the built-in (added) table of places")
    ap.add_argument("--carry", action="store_true",
                    help="layered arms only: overshoot carry — counters keep count - sign*V on a flip")
    ap.add_argument("--cooldown", action="store_true",
                    help="layered arms only: two-stage lr/wd cooldown on the AdamW parts (vote rule fixed)")
    ap.add_argument("--dim", type=int, default=DIM,
                    help="scale ladder (2026-11-12): model width override; default keeps every prior arm identical")
    ap.add_argument("--layers-n", type=int, default=None,
                    help="scale ladder: block-count override; default keeps the arm's built-in count")
    ap.add_argument("--steps", type=int, default=0,
                    help="scale ladder: fixed step budget (equal tokens across rungs); 0 = time-boxed as before. "
                         "--minutes still applies as a safety cap")
    ap.add_argument("--tag", default="",
                    help="scale ladder: suffix appended to the recorded arm label, e.g. scale2m")
    ap.add_argument("--ckpt", action="store_true",
                    help="scale ladder: gradient checkpointing on the blocks (memory-only trade, same math)")
    # mill architecture flags (IDEA-POOL section A) — all default off
    ap.add_argument("--qk-norm", action="store_true")
    ap.add_argument("--qk-norm-q", action="store_true")
    ap.add_argument("--qk-norm-k", action="store_true")
    ap.add_argument("--gated-attn", action="store_true")
    ap.add_argument("--gated-attn-lr", type=int, default=None)
    ap.add_argument("--sink-logit", action="store_true")
    ap.add_argument("--qk-clip", type=float, default=None)
    ap.add_argument("--rope-frac", type=float, default=1.0)
    ap.add_argument("--rope-base", type=float, default=10000.0)
    ap.add_argument("--nope-every", type=int, default=None)
    ap.add_argument("--swa", default=None, help="L:G:W sliding-window/global block hybrid")
    ap.add_argument("--gqa", type=int, default=None)
    ap.add_argument("--heads", type=int, default=None)
    ap.add_argument("--scale-gran", default=None,
                    choices=["tensor", "channel", "group32", "group64", "group128", "boundary"])
    ap.add_argument("--wquant", default="absmean", choices=["absmean", "absmax"])
    ap.add_argument("--agrid", default="absmax", choices=["absmax", "balanced"])
    ap.add_argument("--learn-scale", action="store_true")
    ap.add_argument("--lowrank", type=int, default=0)
    ap.add_argument("--hadamard", action="store_true")
    ap.add_argument("--norm", default=None, choices=["rms", "prepost", "post", "none"])
    ap.add_argument("--subln", action="store_true")
    ap.add_argument("--no-ffn-norm", action="store_true")
    ap.add_argument("--ffn", default="gelu", choices=["gelu", "swiglu", "relu2", "relu"])
    ap.add_argument("--ffn-width", type=float, default=4.0)
    ap.add_argument("--emb-int8", action="store_true")
    ap.add_argument("--untie-head", action="store_true")
    ap.add_argument("--init-std", type=float, default=0.02)
    ap.add_argument("--deltanet", type=int, default=None)
    ap.add_argument("--rwkv", type=int, default=None)
    ap.add_argument("--moe", type=int, default=None)
    ap.add_argument("--moe-top", type=int, default=1)
    ap.add_argument("--moe-shared", action="store_true")
    ap.add_argument("--moe-hash-first", action="store_true")
    ap.add_argument("--act-sparsify", type=float, default=None)
    # mill vote-trainer flags (sections B/C/E)
    ap.add_argument("--votes", type=int, default=32)
    ap.add_argument("--gate-q", type=float, default=0.5)
    ap.add_argument("--mag-cal", type=float, default=None)
    ap.add_argument("--vsched", default=None, help="A:B vote-threshold schedule (layered)")
    ap.add_argument("--vlayer", type=float, default=None)
    ap.add_argument("--leak", type=float, default=None)
    ap.add_argument("--ileak", type=int, default=None)
    ap.add_argument("--agree", action="store_true")
    ap.add_argument("--freeze", type=int, default=None)
    ap.add_argument("--clamp", default=None, help="counter clamp factor x V, or 'none' (layered)")
    ap.add_argument("--flip-rule", default="t1-first", choices=["t1-first", "counter", "sign-agree", "alternate"])
    ap.add_argument("--comps", type=int, default=2)
    ap.add_argument("--comp-v", default=None)
    ap.add_argument("--modal", type=int, default=None)
    ap.add_argument("--verify-flips", type=int, default=None)
    ap.add_argument("--whiten", action="store_true")
    ap.add_argument("--hybrid", default=None, help="F:ste or F:votes phase hand-off")
    ap.add_argument("--opt-lr", type=float, default=None)
    ap.add_argument("--temp", default="1.0:0.05", help="annealflip temperature schedule A:B")
    ap.add_argument("--share", type=float, default=0.002, help="fisherflip flip share")
    ap.add_argument("--fp-first", type=float, default=None)
    ap.add_argument("--ease", type=float, default=None)
    ap.add_argument("--ease-off", action="store_true")
    ap.add_argument("--failweight", type=float, default=None)
    ap.add_argument("--mtp", type=float, default=None)
    ap.add_argument("--kd", type=float, default=None)
    ap.add_argument("--kd-attn", action="store_true")
    # mill STE-recipe flags
    ap.add_argument("--ste-lr", type=float, default=3e-3)
    ap.add_argument("--ste-warmup", type=int, default=200)
    ap.add_argument("--ste-wd", type=float, default=0.01)
    ap.add_argument("--two-stage", action="store_true")
    ap.add_argument("--two-stage-wd", action="store_true")
    ap.add_argument("--muon", action="store_true")
    ap.add_argument("--muon-split", action="store_true")
    ap.add_argument("--polish", type=int, default=None)
    # mill round-2 priority flags (E/A waves)
    ap.add_argument("--corpus", default="v1",
                    help="mill E-018..E-021: corpus stream — v1 (corpus.u16), v2 (corpus-v2/corpus-v2.u16), "
                         "or a variant name resolved to corpus-<name>.u16; held windows follow the "
                         "same every-40th rule on the chosen stream")
    ap.add_argument("--wd", type=float, default=None,
                    help="mill E-015: AdamW weight decay of the shared parts (on STE arms it overrides "
                         "--ste-wd). On Layered it is also the cooldown schedule's base — the chassis "
                         "cooldown decayed a wd of 0, so its wd component was a no-op")
    ap.add_argument("--buffer", type=int, default=None,
                    help="mill A-050: exclude training windows within this many window positions of a held window")
    ap.add_argument("--log-level-hist", action="store_true",
                    help="mill E-013: record layered level-population histograms and per-component flip counts")
    ap.add_argument("--cooldown-noemb", action="store_true",
                    help="mill E-016: the cooldown schedule skips the embedding group (constant lr/wd)")
    ap.add_argument("--repeat", type=int, default=None,
                    help="mill A-044: train each sampled batch this many times consecutively")
    ap.add_argument("--ctx-curr", nargs="?", const="fwd", default=None, choices=["fwd", "rev"],
                    help="mill A-045/A-046: context-length curriculum by thirds (fwd 64->128->256, rev the reverse)")
    ap.add_argument("--dedup", action="store_true",
                    help="mill A-047: drop near-duplicate windows (sorted 8-gram shingle signature)")
    ap.add_argument("--freq-balance", action="store_true",
                    help="mill A-049: half-rate windows dominated by the 100 most frequent tokens")
    ap.add_argument("--shift-aug", action="store_true",
                    help="mill A-051: cyclically shift each sampled window by a random offset")
    ap.add_argument("--vote-kernel", default="current", choices=["current", "fused"],
                    help="kernels/RESULTS-KERNELS.md section 2: fused vote-counter update (sign computed "
                         "once, exact flip test, in-place counters) — bitwise identical state, ~1.7-1.8x "
                         "on the update block at champion size")
    a = ap.parse_args()
    if (a.carry or a.cooldown) and a.arm not in ("layered", "layered_half"):
        ap.error("--carry/--cooldown are levers on the layered vote trainer only")
    hybrid_to = a.hybrid.split(":")[-1] if a.hybrid and ":" in a.hybrid else None
    if a.hybrid is not None and hybrid_to not in ("ste", "votes"):
        ap.error("--hybrid must look like 0.5:ste or 0.5:votes")
    if hybrid_to == "ste" and a.arm not in VOTE_ARMS:
        ap.error("--hybrid F:ste needs a vote arm to start from")
    if hybrid_to == "votes" and a.arm not in STE_ARMS:
        ap.error("--hybrid F:votes needs an STE arm to start from")
    if a.cooldown_noemb and not a.cooldown:
        ap.error("--cooldown-noemb needs --cooldown")
    layered_only = (a.comps != 2 or a.comp_v or a.leak is not None or a.ileak is not None or a.agree
                    or a.freeze is not None or a.clamp is not None or a.flip_rule != "t1-first"
                    or a.vsched or a.vlayer is not None or a.whiten or a.modal is not None
                    or a.verify_flips is not None or a.log_level_hist or a.cooldown_noemb)
    if layered_only and a.arm not in ("layered", "layered_half") and hybrid_to != "votes":
        ap.error("layered-trainer flags used on a non-layered arm")
    if a.mag_cal is not None and a.arm not in ("plain", "plain_half"):
        ap.error("--mag-cal is a Direct (plain-arm) lever")
    ste_only = (a.muon or a.muon_split or a.two_stage or a.two_stage_wd or a.polish is not None
                or a.ste_lr != 3e-3 or a.ste_warmup != 200 or a.ste_wd != 0.01)
    if ste_only and a.arm not in STE_ARMS and hybrid_to != "ste":
        ap.error("STE-recipe flags used on a non-STE arm")
    if (a.kd is not None or a.mtp is not None) and a.arm == "disarm":
        ap.error("--kd/--mtp need the standard loss path (not disarm)")
    if a.vote_kernel == "fused" and a.arm not in VOTE_ARMS and hybrid_to is None:
        ap.error("--vote-kernel fused applies to the Direct/Layered vote trainers only")
    clamp_val = None
    if a.clamp is not None:
        clamp_val = "none" if a.clamp == "none" else float(a.clamp)
    comp_v = [int(v) for v in a.comp_v.split(",")] if a.comp_v else None
    if comp_v and len(comp_v) != a.comps:
        ap.error("--comp-v must list one threshold per component")
    vsched = tuple(float(v) for v in a.vsched.split(":")) if a.vsched else None
    swa = tuple(int(v) for v in a.swa.split(":")) if a.swa else None
    temp = tuple(float(v) for v in a.temp.split(":"))
    heads = a.heads if a.heads else HEADS
    if a.gqa and heads % a.gqa:
        ap.error("--gqa must divide the head count")
    arch = {}
    qk = "both" if (a.qk_norm or (a.qk_norm_q and a.qk_norm_k)) else (
        "q" if a.qk_norm_q else ("k" if a.qk_norm_k else None))
    if qk:
        arch["qk_norm"] = qk
    if a.gated_attn:
        arch["gated"] = True
    if a.gated_attn_lr:
        arch["gated_lr"] = a.gated_attn_lr
    if a.sink_logit:
        arch["sink"] = True
    if a.qk_clip is not None:
        arch["qk_clip"] = a.qk_clip
    if a.rope_frac != 1.0:
        arch["rope_frac"] = a.rope_frac
    if a.rope_base != 10000.0:
        arch["rope_base"] = a.rope_base
    if a.nope_every:
        arch["nope_every"] = a.nope_every
    if swa:
        arch["swa"] = swa
    if a.gqa:
        arch["kv_heads"] = heads // a.gqa
    if a.heads:
        arch["heads"] = a.heads
    if a.scale_gran and a.scale_gran != "tensor":
        arch["gran"] = a.scale_gran
    if a.wquant != "absmean":
        arch["wquant"] = a.wquant
    if a.agrid != "absmax":
        arch["agrid"] = a.agrid
    if a.learn_scale:
        arch["learn_scale"] = True
    if a.lowrank:
        arch["lowrank"] = a.lowrank
    if a.hadamard:
        arch["hadamard"] = True
    if a.norm:
        arch["norm"] = a.norm
    if a.subln:
        arch["subln"] = True
    if a.no_ffn_norm:
        arch["no_ffn_norm"] = True
    if a.ffn != "gelu":
        arch["ffn"] = a.ffn
    arch["ffn_width"] = a.ffn_width
    arch["init_std"] = a.init_std
    if a.emb_int8:
        arch["emb_int8"] = True
    if a.untie_head:
        arch["untie"] = True
    if a.deltanet:
        arch["deltanet"] = a.deltanet
    if a.rwkv:
        arch["rwkv"] = a.rwkv
    if a.moe:
        arch["moe"] = (a.moe, a.moe_top, a.moe_shared, a.moe_hash_first)
    if a.act_sparsify is not None:
        arch["sparsify"] = a.act_sparsify
    label = a.arm + ("_rope" if a.rope else "") + ("_carry" if a.carry else "") + \
        ("_cooldown" if a.cooldown else "") + (("_" + a.tag) if a.tag else "")
    BUFFER[0] = a.buffer if a.buffer else 0
    if a.corpus == "v1":
        data_path = LAB / "corpus.u16"
    elif a.corpus == "v2":
        data_path = LAB / "corpus-v2" / "corpus-v2.u16"
    else:
        cand = [LAB / f"corpus-{a.corpus}.u16", LAB / f"{a.corpus}.u16",
                LAB / "corpus-v2" / f"corpus-{a.corpus}.u16"]
        data_path = next((c for c in cand if c.exists()), None)
        if data_path is None:
            ap.error(f"--corpus {a.corpus}: no corpus file found (looked for corpus-{a.corpus}.u16)")
    data = np.memmap(data_path, dtype=np.uint16, mode="r")
    held = held_windows(data)
    torch.manual_seed(a.seed)
    layers = a.layers_n if a.layers_n else (2 if a.arm in HALF_ARMS else 4)
    model = Tiny(layers=layers, dim=a.dim, rotary=a.rope, arch=arch)
    model.ckpt = a.ckpt
    layered_kw = dict(comps=a.comps, comp_v=comp_v, gate_q=a.gate_q, leak=a.leak, ileak=a.ileak,
                      agree=a.agree, freeze=a.freeze, clamp=clamp_val, flip_rule=a.flip_rule,
                      vsched=vsched, vlayer=a.vlayer, whiten=a.whiten, opt_lr=a.opt_lr,
                      carry=a.carry, cooldown=a.cooldown, wd=a.wd, cooldown_noemb=a.cooldown_noemb,
                      vote_kernel=a.vote_kernel)
    def make_ste(m):
        return STE(m, lr=a.ste_lr, warm=a.ste_warmup,
                   wd=a.wd if a.wd is not None else a.ste_wd, muon=a.muon,
                   muon_split_hd=(a.dim // heads) if a.muon_split else None,
                   two_stage=a.two_stage, two_stage_wd=a.two_stage_wd)
    gen2 = torch.Generator().manual_seed(a.seed + 777)
    check = None
    if a.arm == "fisherflip" or a.verify_flips is not None:
        crnd = random.Random(4242)
        coffs = offsets(crnd, len(data), a.batch)
        check = torch.stack([torch.from_numpy(data[i:i + CTX + 1].astype("int64")) for i in coffs])
    if a.arm in STE_ARMS:
        trainer = make_ste(model)
    elif a.arm in ("layered", "layered_half"):
        trainer = Layered(model, **layered_kw)
    elif a.arm == "annealflip":
        trainer = AnnealFlip(model, temp=temp, gen=gen2, opt_lr=a.opt_lr, wd=a.wd)
    elif a.arm == "disarm":
        trainer = DisARM(model, gen=gen2, opt_lr=a.opt_lr, wd=a.wd)
    elif a.arm == "resid8":
        trainer = Resid(model, bits=8, opt_lr=a.opt_lr, wd=a.wd)
    elif a.arm == "resid16":
        trainer = Resid(model, bits=16, opt_lr=a.opt_lr, wd=a.wd)
    elif a.arm == "fisherflip":
        trainer = FisherFlip(model, share=a.share, check=check, opt_lr=a.opt_lr, wd=a.wd)
    else:
        trainer = Direct(model, mode="plain" if a.arm == "plain_half" else a.arm, votes=a.votes,
                         gate_q=a.gate_q, mag_cal=a.mag_cal,
                         clamp=clamp_val if isinstance(clamp_val, float) else None,
                         opt_lr=a.opt_lr, wd=a.wd, vote_kernel=a.vote_kernel)
    if a.log_level_hist and isinstance(trainer, Layered):
        trainer.level_flips = [0] * trainer.N
    teacher, ttrainer = None, None
    if a.kd is not None:
        teacher = Tiny(layers=layers, dim=a.dim, rotary=a.rope, arch=arch)
        ttrainer = STE(teacher, lr=a.ste_lr, warm=a.ste_warmup, wd=a.ste_wd)
    hybrid = None
    if a.hybrid is not None:
        hf, hto = a.hybrid.split(":")
        hybrid = {"at": float(hf), "to": hto, "swapped": False}
    def aux_loss(x):
        tot = 0.0
        if a.mtp is not None:
            logits = model.next_piece(x[:, :-1])
            tot = tot + a.mtp * F.cross_entropy(logits[:, :-1].reshape(-1, VOCAB), x[:, 2:].reshape(-1))
        if a.kd is not None and teacher is not None:
            e = EASE[0]
            EASE[0] = 0.0
            with torch.no_grad():
                tl = teacher.next_piece(x[:, :-1])
                tp = teacher.last_attn_probs(x[:, :-1]) if a.kd_attn else None
            EASE[0] = e
            sl = model.next_piece(x[:, :-1])
            T = 2.0
            tot = tot + a.kd * (T * T) * F.kl_div(F.log_softmax(sl / T, -1),
                                                  F.softmax(tl / T, -1), reduction="batchmean")
            if tp is not None:
                sp = model.last_attn_probs(x[:, :-1])
                tot = tot + a.kd * F.kl_div(torch.log(sp + 1e-9), tp, reduction="batchmean")
        return tot
    if a.arm in STE_ARMS:
        n_tern = sum(p.numel() for m in model.modules() if isinstance(m, BitLinear) for p in [m.weight])
    elif hasattr(trainer, "ts"):
        n_tern = sum(ts[0].numel() for ts in trainer.ts)
    else:
        n_tern = sum(t.numel() for t in trainer.t)
    h0 = held_loss(model, held)
    rnd, t0, steps, losses, jumps = random.Random(a.seed), time.time(), 0, [], []
    budget = a.minutes * 60
    failp = FailPicker(model, data, rnd, a.failweight) if a.failweight is not None else None
    dedup_seen = set() if a.dedup else None
    freq_mask = None
    if a.freq_balance:
        counts = np.bincount(np.asarray(data), minlength=VOCAB)
        freq_mask = np.zeros(VOCAB, dtype=bool)
        freq_mask[np.argsort(counts)[-100:]] = True
    modal_snaps = {}
    level_hist = []
    def snap_level():
        if not (a.log_level_hist and isinstance(trainer, Layered)):
            return
        if trainer.level_flips is None:
            trainer.level_flips = [0] * trainer.N
        tot = None
        for ts in trainer.ts:
            s = ts[0]
            for t in ts[1:]:
                s = s + t
            tot = s.flatten() if tot is None else torch.cat([tot, s.flatten()])
        level_hist.append({"step": steps,
                           "hist": {int(v): round(float((tot == v).float().mean()), 4)
                                    for v in range(-trainer.N, trainer.N + 1)},
                           "flips": list(trainer.level_flips)})
    while time.time() - t0 < budget:
        if a.steps and steps >= a.steps:
            break
        done = (steps / a.steps) if a.steps else (time.time() - t0) / budget
        FRAC[0] = done
        if hybrid is not None and not hybrid["swapped"] and done >= hybrid["at"]:
            trainer = make_ste(model) if hybrid["to"] == "ste" else Layered(model, **layered_kw)
            hybrid["swapped"] = True
            if a.log_level_hist and isinstance(trainer, Layered):
                trainer.level_flips = [0] * trainer.N
        if a.ease_off:
            EASE[0] = 0.0
        elif a.ease is not None:
            EASE[0] = min(1.0, done / a.ease) if a.ease > 0 else 1.0
        elif a.fp_first is not None:
            EASE[0] = 0.0 if done < a.fp_first else min(1.0, (done - a.fp_first) / max(1e-9, 1.0 - a.fp_first))
        elif isinstance(trainer, STE):
            d = (done - hybrid["at"]) / max(1e-9, 1.0 - hybrid["at"]) \
                if (hybrid and hybrid["swapped"] and hybrid["to"] == "ste") else done
            EASE[0] = min(1.0, d / 0.5)
        else:
            EASE[0] = 1.0
        if failp is not None:
            failp.maybe_score(steps)
            at = failp.batch(a.batch)
        else:
            at = offsets(rnd, len(data), a.batch)
        if dedup_seen is not None or freq_mask is not None:
            at = sampler_filter(at, data, rnd, dedup_seen, freq_mask)
        x = torch.stack([torch.from_numpy(data[i:i + CTX + 1].astype("int64")) for i in at])
        if a.ctx_curr:
            x = x[:, :curr_len(done, a.ctx_curr) + 1]
        if a.shift_aug:
            x = torch.stack([torch.roll(row, rnd.randrange(x.shape[1])) for row in x])
        if teacher is not None and done < 0.5:
            EASE[0] = 0.0
            tloss = F.cross_entropy(teacher.next_piece(x[:, :-1]).reshape(-1, VOCAB), x[:, 1:].reshape(-1))
            losses.append(tloss.item())
            jumps.append(ttrainer.step(tloss, done))
            steps += 1
            continue
        for _pass in range(a.repeat if a.repeat else 1):
            loss = F.cross_entropy(model.next_piece(x[:, :-1]).reshape(-1, VOCAB), x[:, 1:].reshape(-1))
            if a.mtp is not None or (a.kd is not None and teacher is not None):
                loss = loss + aux_loss(x)
            losses.append(loss.item())
            jumps.append(trainer.step(loss, done, x=x))
            steps += 1
        if a.verify_flips is not None and isinstance(trainer, Layered) and steps % a.verify_flips == 0:
            trainer.verify(check, done)
        if a.modal is not None and isinstance(trainer, Layered) and steps % 10 == 0:
            for i, ts in enumerate(trainer.ts):
                for ci in range(trainer.N):
                    modal_snaps.setdefault((i, ci), deque(maxlen=a.modal)).append(ts[ci].clone())
        if steps % 100 == 0:
            snap_level()
            print(f"[{label} s{a.seed}] step {steps}: train {sum(losses[-100:])/100:.3f}, "
                  f"flips {sum(jumps[-100:])/100:.3%}", flush=True)
    wall = time.time() - t0
    if a.polish is not None and isinstance(trainer, STE):
        trainer.fixed_lr(3e-4)
        for _ in range(a.polish):
            at = offsets(rnd, len(data), a.batch)
            x = torch.stack([torch.from_numpy(data[i:i + CTX + 1].astype("int64")) for i in at])
            loss = F.cross_entropy(model.next_piece(x[:, :-1]).reshape(-1, VOCAB), x[:, 1:].reshape(-1))
            losses.append(loss.item())
            jumps.append(trainer.step(loss, 1.0, x=x))
            steps += 1
    snap_level()
    h1 = held_loss(model, held)
    held_state_final = None
    if a.modal is not None and isinstance(trainer, Layered) and modal_snaps:
        held_state_final = h1
        with torch.no_grad():
            vals = torch.tensor([-1.0, 0.0, 1.0])
            for (i, ci), dq in modal_snaps.items():
                st = torch.stack(list(dq))
                cnt = torch.stack([(st == v).sum(0).float() for v in (-1.0, 0.0, 1.0)])
                bonus = (vals[:, None, None] == trainer.ts[i][ci].unsqueeze(0)).float() * 0.5
                trainer.ts[i][ci] = vals[(cnt + bonus).argmax(0)]
            trainer.install()
        h1 = held_loss(model, held)
    if hasattr(trainer, "ts"):
        def _sumts(ts):
            s = ts[0]
            for t in ts[1:]:
                s = s + t
            return s
        states = torch.cat([_sumts(ts).flatten() for ts in trainer.ts])
        hist = {int(v): round(float((states == v).float().mean()), 4)
                for v in range(-trainer.N, trainer.N + 1)}
    elif hasattr(trainer, "t"):
        states = torch.cat([t.flatten() for t in trainer.t])
        hist = {int(v): round(float((states == v).float().mean()), 4) for v in (-1, 0, 1)}
    else:
        hist = {}
    sb_method = trainer.state_bytes() if hasattr(trainer, "state_bytes") else None
    if sb_method is not None:
        state_bytes = sb_method
    elif hasattr(trainer, "ts"):
        state_bytes = 0
        for cs, ts in zip(trainer.cs, trainer.ts):
            n = ts[0].numel()
            state_bytes += sum(c.element_size() * n for c in cs) + len(cs) * (n // 4)
    elif hasattr(trainer, "count"):
        state_bytes = sum(c.element_size() * t.numel() + t.numel() // 4
                          for c, t in zip(trainer.count, trainer.t))
    else:
        state_bytes = 12 * n_tern
    mill_flags = {}
    def mf(name, val, default=None):
        if val != default:
            mill_flags[name] = val
    mf("qk_norm", qk); mf("gated_attn", a.gated_attn, False); mf("gated_attn_lr", a.gated_attn_lr)
    mf("sink_logit", a.sink_logit, False); mf("qk_clip", a.qk_clip); mf("rope_frac", a.rope_frac, 1.0)
    mf("rope_base", a.rope_base, 10000.0); mf("nope_every", a.nope_every); mf("swa", a.swa)
    mf("gqa", a.gqa); mf("heads", a.heads); mf("scale_gran", a.scale_gran)
    mf("wquant", a.wquant, "absmean"); mf("agrid", a.agrid, "absmax")
    mf("learn_scale", a.learn_scale, False); mf("lowrank", a.lowrank, 0)
    mf("hadamard", a.hadamard, False); mf("norm", a.norm); mf("subln", a.subln, False)
    mf("no_ffn_norm", a.no_ffn_norm, False); mf("ffn", a.ffn, "gelu"); mf("ffn_width", a.ffn_width, 4.0)
    mf("emb_int8", a.emb_int8, False); mf("untie_head", a.untie_head, False)
    mf("init_std", a.init_std, 0.02); mf("deltanet", a.deltanet); mf("rwkv", a.rwkv)
    mf("moe", a.moe); mf("moe_top", a.moe_top if a.moe else None)
    mf("moe_shared", a.moe_shared, False); mf("moe_hash_first", a.moe_hash_first, False)
    mf("act_sparsify", a.act_sparsify)
    mf("votes", a.votes, 32); mf("gate_q", a.gate_q, 0.5); mf("mag_cal", a.mag_cal)
    mf("vsched", a.vsched); mf("vlayer", a.vlayer); mf("leak", a.leak); mf("ileak", a.ileak)
    mf("agree", a.agree, False); mf("freeze", a.freeze); mf("clamp", a.clamp)
    mf("flip_rule", a.flip_rule, "t1-first"); mf("comps", a.comps, 2); mf("comp_v", a.comp_v)
    mf("modal", a.modal); mf("verify_flips", a.verify_flips); mf("whiten", a.whiten, False)
    mf("hybrid", a.hybrid); mf("opt_lr", a.opt_lr); mf("temp", a.temp, "1.0:0.05")
    mf("share", a.share, 0.002); mf("fp_first", a.fp_first); mf("ease", a.ease)
    mf("ease_off", a.ease_off, False); mf("failweight", a.failweight); mf("mtp", a.mtp)
    mf("kd", a.kd); mf("kd_attn", a.kd_attn, False)
    mf("ste_lr", a.ste_lr, 3e-3); mf("ste_warmup", a.ste_warmup, 200); mf("ste_wd", a.ste_wd, 0.01)
    mf("two_stage", a.two_stage, False); mf("two_stage_wd", a.two_stage_wd, False)
    mf("muon", a.muon, False); mf("muon_split", a.muon_split, False); mf("polish", a.polish)
    mf("corpus", a.corpus, "v1"); mf("wd", a.wd); mf("buffer", a.buffer)
    mf("log_level_hist", a.log_level_hist, False); mf("cooldown_noemb", a.cooldown_noemb, False)
    mf("repeat", a.repeat); mf("ctx_curr", a.ctx_curr); mf("dedup", a.dedup, False)
    mf("freq_balance", a.freq_balance, False); mf("shift_aug", a.shift_aug, False)
    mf("vote_kernel", a.vote_kernel, "current")
    rec = {"arm": label, "seed": a.seed, "steps": steps, "wall_s": round(wall, 1),
           "held_init": round(h0, 4), "held_final": round(h1, 4),
           "train_last100": round(sum(losses[-100:]) / max(1, len(losses[-100:])), 4),
           "ternary_weights": n_tern, "mech_state_bytes": state_bytes,
           "mean_flip_share": round(sum(jumps) / max(1, len(jumps)), 5), "state_hist": hist,
           "corpus_pieces": int(len(data)), "minutes": a.minutes,
           "rope": bool(a.rope), "carry": bool(a.carry), "cooldown": bool(a.cooldown),
           "dim": a.dim, "layers_n": layers, "ckpt": bool(a.ckpt),
           "steps_target": a.steps if a.steps else None,
           "corpus": a.corpus,
           "total_params": sum(p.numel() for p in model.parameters()),
           "mill_flags": mill_flags}
    if isinstance(trainer, Direct) and trainer.mag_thr is not None:
        rec["mag_thr"] = trainer.mag_thr
    if level_hist:
        rec["level_hist"] = level_hist
    if held_state_final is not None:
        rec["held_final_state"] = round(held_state_final, 4)
    with open(LAB / "runs.jsonl", "a") as f:
        f.write(json.dumps(rec) + "\n")
    print("RESULT " + json.dumps(rec), flush=True)

if __name__ == "__main__":
    main()
