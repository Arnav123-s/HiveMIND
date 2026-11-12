# Muse's work — written by Muse, on Muse's side. Fable's HiveMIND was read read-only; nothing on Fable's side was touched.
# Muse's work — built and run by Muse on Muse's side of the lab. Fable's HiveMIND was read read-only for the mechanism; nothing on Fable's side was touched or used.

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
All arms: same corpus, same seed -> same init and same batch stream, batch 32, CTX 256,
held windows (every 40th) never trained on, judged on a fixed set of 128 held windows.
Non-ternary parts in the vote arms train exactly as Fable's Direct: AdamW lr 1e-3,
betas (0.9, 0.95), weight decay 0, per-layer scale via the hand-set gradient (g.t)*scale."""
import argparse, json, math, random, time
from pathlib import Path
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

LAB = Path(__file__).resolve().parent
VOCAB, DIM, HEADS, CTX = 4096, 192, 4, 256
HELD_EVERY = 40
EASE = [1.0]

def offsets(rnd, n, batch):
    out = []
    while len(out) < batch:
        i = rnd.randrange(0, n - CTX - 1)
        if (i // CTX) % HELD_EVERY and ((i + CTX) // CTX) % HELD_EVERY:
            out.append(i)
    return out

class BitLinear(nn.Linear):
    def forward(self, x):
        w, ease = self.weight, EASE[0]
        scale = w.abs().mean().clamp(min=1e-5)
        w = w + ease * ((w / scale).round().clamp(-1, 1) * scale - w).detach()
        top = x.abs().amax(-1, keepdim=True).clamp(min=1e-5)
        x = x + ease * ((x * 127 / top).round().clamp(-128, 127) * top / 127 - x).detach()
        return F.linear(x, w, self.bias)

def rotated(x, cos, sin):
    """Rotary positions, Fable's way (their scratch.rotated, read in the audit copy at 4bd8308 and
    reimplemented here): each interleaved pair of numbers of a query or key is turned by an angle
    that grows with its place in the text. x: [batch, heads, places, numbers]; cos/sin: [places, pairs]."""
    a, b = x[..., ::2], x[..., 1::2]
    return torch.stack([a * cos - b * sin, a * sin + b * cos], -1).flatten(-2)

class Block(nn.Module):
    def __init__(self, dim=DIM, heads=HEADS, rotary=False):
        super().__init__()
        self.heads = heads
        self.n1, self.n2 = nn.LayerNorm(dim), nn.LayerNorm(dim)
        self.qkv, self.out = BitLinear(dim, 3 * dim), BitLinear(dim, dim)
        self.up, self.down = BitLinear(dim, 4 * dim), BitLinear(4 * dim, dim)
        self.rotary = rotary
        if rotary:
            each = dim // heads
            angle = torch.arange(CTX).float()[:, None] / (10000 ** (torch.arange(0, each, 2).float() / each))[None]
            self.register_buffer("cos", angle.cos(), persistent=False)
            self.register_buffer("sin", angle.sin(), persistent=False)
    def forward(self, x, causal=True):
        b, t, d = x.shape
        q, k, v = self.qkv(self.n1(x)).view(b, t, 3, self.heads, d // self.heads).permute(2, 0, 3, 1, 4)
        if self.rotary:
            q, k = rotated(q, self.cos[:t], self.sin[:t]), rotated(k, self.cos[:t], self.sin[:t])
        a = F.scaled_dot_product_attention(q, k, v, is_causal=causal).transpose(1, 2).reshape(b, t, d)
        x = x + self.out(a)
        h = F.gelu(self.up(self.n2(x)))
        return x + self.down(h)

class Tiny(nn.Module):
    def __init__(self, layers=4, dim=DIM, rotary=False):
        super().__init__()
        self.dim = dim
        self.tok, self.pos = nn.Embedding(VOCAB, dim), nn.Embedding(CTX, dim)
        self.rotary = rotary  # then the table of places (pos) is carried, as in Fable's shape, but not used
        self.blocks = nn.ModuleList(Block(dim, rotary=rotary) for _ in range(layers))
        self.norm = nn.LayerNorm(dim)
        self.apply(lambda m: nn.init.normal_(m.weight, std=0.02) if isinstance(m, (nn.Linear, nn.Embedding)) else None)
    def body(self, ids):
        x = self.tok(ids) if self.rotary else self.tok(ids) + self.pos(torch.arange(ids.shape[1]))
        for blk in self.blocks:
            x = blk(x)
        return self.norm(x)
    def next_piece(self, ids):
        return self.body(ids) @ self.tok.weight.T

class Direct:
    """Vote-counter trainer (Fable's mechanism, reimplemented). mode: plain | mag | anneal."""
    def __init__(self, model, lr=1e-3, mode="plain", votes=32):
        self.mode, self.votes, self.steps = mode, votes, 0
        self.layers = [m for m in model.modules() if isinstance(m, BitLinear)]
        own = {id(m.weight) for m in self.layers}
        self.t, self.log_scale = [], []
        for m in self.layers:
            scale = m.weight.detach().abs().mean().clamp(min=1e-5)
            self.t.append((m.weight.detach() / scale).round().clamp(-1, 1))
            self.log_scale.append(torch.nn.Parameter(scale.log()))
        self.opt = torch.optim.AdamW([p for p in model.parameters() if id(p) not in own] + self.log_scale,
                                     lr=lr, weight_decay=0.0, betas=(0.9, 0.95))
        dt = torch.int16 if mode == "mag" else torch.int8
        self.count = [torch.zeros_like(t, dtype=dt) for t in self.t]
        self.model = model
        self.install()
    def install(self):
        with torch.no_grad():
            for m, t, ls in zip(self.layers, self.t, self.log_scale):
                m.weight.copy_(t * (ls.exp() / t.abs().mean().clamp(min=1e-5)))
    def threshold(self, done):
        if self.mode == "mag":
            return 96
        if self.mode == "anneal":
            return int(round(8 + 56 * done))
        return self.votes
    def step(self, loss, done=0.0):
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
                self.log_scale[i].grad = (g * t).sum() * self.log_scale[i].exp()
                c = self.count[i]
                if self.mode == "mag":
                    inc = (-g / g.abs().mean().clamp(min=1e-12)).round().clamp(-3, 3).to(torch.int16)
                    c = (c + inc).clamp(-V, V)
                    go = c.abs() >= V
                    want = (t + c.sign()).clamp(-1, 1)
                    self.count[i] = torch.where(go, torch.zeros_like(c), c)
                    go = go & (want != t)
                else:
                    strong = g.abs() >= g.abs().median()
                    vote = (-g.sign() * strong).to(torch.int8)
                    c = (c + vote).clamp(-V, V)
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
    """Weight = t1 + t2, two ternary states with independent int8 vote counters (V=32).
    At most one component flips per weight per step (t1 first, unless its flip is a
    boundary no-op, then t2); only the flipped component's counter resets."""
    def __init__(self, model, lr=1e-3, votes=32, carry=False, cooldown=False):
        self.votes, self.steps = votes, 0
        self.carry, self.cooldown = carry, cooldown
        self.base_lr, self.base_wd = lr, 0.0  # the AdamW weight decay this trainer is built with
        self.layers = [m for m in model.modules() if isinstance(m, BitLinear)]
        own = {id(m.weight) for m in self.layers}
        self.t1, self.t2, self.log_scale = [], [], []
        for m in self.layers:
            scale = m.weight.detach().abs().mean().clamp(min=1e-5)
            self.t1.append((m.weight.detach() / scale).round().clamp(-1, 1))
            self.t2.append(torch.zeros_like(self.t1[-1]))
            self.log_scale.append(torch.nn.Parameter(scale.log()))
        self.opt = torch.optim.AdamW([p for p in model.parameters() if id(p) not in own] + self.log_scale,
                                     lr=lr, weight_decay=0.0, betas=(0.9, 0.95))
        # carry needs counters that can pass +-V (overshoot); int8 would overflow, so int16.
        cdt = torch.int16 if carry else torch.int8
        self.c1 = [torch.zeros_like(t, dtype=cdt) for t in self.t1]
        self.c2 = [torch.zeros_like(t, dtype=cdt) for t in self.t1]
        self.model = model
        self.install()
    def install(self):
        with torch.no_grad():
            for m, t1, t2, ls in zip(self.layers, self.t1, self.t2, self.log_scale):
                s = t1 + t2
                m.weight.copy_(s * (ls.exp() / s.abs().mean().clamp(min=1e-5)))
    def step(self, loss, done=0.0):
        if self.cooldown:
            # Two-stage schedule on the AdamW parts only: stage 1 constant, stage 2
            # (second half) lr and weight decay decayed linearly toward zero. The
            # vote threshold and gate below never see `done` — the vote rule is fixed.
            mult = 1.0 if done < 0.5 else max(0.0, (1.0 - done) / 0.5)
            for g in self.opt.param_groups:
                g["lr"] = self.base_lr * mult
                g["weight_decay"] = self.base_wd * mult
        self.opt.zero_grad(set_to_none=True)
        for m in self.layers:
            m.weight.grad = None
        loss.backward()
        nn.utils.clip_grad_norm_([p for g in self.opt.param_groups for p in g["params"] if p.grad is not None], 1.0)
        jumped, total = 0, 0
        V = self.votes
        with torch.no_grad():
            for i, m in enumerate(self.layers):
                g = m.weight.grad
                t1, t2 = self.t1[i], self.t2[i]
                s = t1 + t2
                self.log_scale[i].grad = (g * s).sum() * self.log_scale[i].exp()
                strong = g.abs() >= g.abs().median()
                vote = (-g.sign() * strong).to(torch.int8)
                if self.carry:
                    # No saturation at +-V: votes that arrive while a flip is blocked
                    # (boundary no-op, or the pair's one-flip-per-step rule) are kept,
                    # not clamped away. A flip subtracts sign*V instead of resetting.
                    c1, c2 = self.c1[i] + vote, self.c2[i] + vote
                else:
                    c1 = (self.c1[i] + vote).clamp(-V, V)
                    c2 = (self.c2[i] + vote).clamp(-V, V)
                go1 = (c1.abs() >= V) & ((t1 + c1.sign()).clamp(-1, 1) != t1)
                go2 = (~go1) & (c2.abs() >= V) & ((t2 + c2.sign()).clamp(-1, 1) != t2)
                self.t1[i] = torch.where(go1, (t1 + c1.sign()).clamp(-1, 1), t1)
                self.t2[i] = torch.where(go2, (t2 + c2.sign()).clamp(-1, 1), t2)
                if self.carry:
                    self.c1[i] = torch.where(go1, c1 - c1.sign() * V, c1)
                    self.c2[i] = torch.where(go2, c2 - c2.sign() * V, c2)
                else:
                    self.c1[i] = torch.where(go1, torch.zeros_like(c1), c1)
                    self.c2[i] = torch.where(go2, torch.zeros_like(c2), c2)
                jumped, total = jumped + int(go1.sum()) + int(go2.sum()), total + t1.numel()
        self.opt.step()
        self.install()
        self.steps += 1
        return jumped / total

class STE:
    """The published way: latent fp weights, AdamW lr 3e-3, warmup 200, wd 0.01 (built-in recipe)."""
    def __init__(self, model, lr=3e-3, warm=200):
        self.opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01, betas=(0.9, 0.95))
        self.lr, self.warm, self.steps, self.model = lr, warm, 0, model
    def step(self, loss, done=0.0):
        for g in self.opt.param_groups:
            g["lr"] = self.lr * min(1.0, (self.steps + 1) / max(1, self.warm))
        self.opt.zero_grad(set_to_none=True)
        loss.backward()
        nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
        self.opt.step()
        self.steps += 1
        return 0.0

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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=["plain", "ste", "mag", "layered", "layered_half", "anneal",
                                                     "plain_half", "ste_half"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--minutes", type=float, default=8.0)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--rope", action="store_true",
                    help="rotary positions Fable's way instead of the built-in (added) table of places")
    ap.add_argument("--carry", action="store_true",
                    help="layered arms only: overshoot carry — counters keep count - sign*V on a flip")
    ap.add_argument("--cooldown", action="store_true",
                    help="layered arms only: two-stage lr/wd cooldown on the AdamW parts (vote rule fixed)")
    a = ap.parse_args()
    if (a.carry or a.cooldown) and a.arm not in ("layered", "layered_half"):
        ap.error("--carry/--cooldown are levers on the layered vote trainer only")
    label = a.arm + ("_rope" if a.rope else "") + ("_carry" if a.carry else "") + \
        ("_cooldown" if a.cooldown else "")
    data = np.memmap(LAB / "corpus.u16", dtype=np.uint16, mode="r")
    held = held_windows(data)
    torch.manual_seed(a.seed)
    layers = 2 if a.arm in ("layered_half", "plain_half", "ste_half") else 4
    model = Tiny(layers=layers, rotary=a.rope)
    if a.arm in ("ste", "ste_half"):
        trainer = STE(model)
    elif a.arm in ("layered", "layered_half"):
        trainer = Layered(model, carry=a.carry, cooldown=a.cooldown)
    else:
        trainer = Direct(model, mode="plain" if a.arm == "plain_half" else a.arm)
    n_tern = sum(t.numel() for t in (trainer.t if hasattr(trainer, "t") else trainer.t1)) if a.arm not in ("ste", "ste_half") else \
        sum(p.numel() for m in model.modules() if isinstance(m, BitLinear) for p in [m.weight])
    h0 = held_loss(model, held)
    rnd, t0, steps, losses, jumps = random.Random(a.seed), time.time(), 0, [], []
    budget = a.minutes * 60
    while time.time() - t0 < budget:
        done = (time.time() - t0) / budget
        EASE[0] = min(1.0, done / 0.5) if a.arm in ("ste", "ste_half") else 1.0
        at = offsets(rnd, len(data), a.batch)
        x = torch.stack([torch.from_numpy(data[i:i + CTX + 1].astype("int64")) for i in at])
        loss = F.cross_entropy(model.next_piece(x[:, :-1]).reshape(-1, VOCAB), x[:, 1:].reshape(-1))
        losses.append(loss.item())
        jumps.append(trainer.step(loss, done))
        steps += 1
        if steps % 100 == 0:
            print(f"[{label} s{a.seed}] step {steps}: train {sum(losses[-100:])/100:.3f}, "
                  f"flips {sum(jumps[-100:])/100:.3%}", flush=True)
    wall = time.time() - t0
    h1 = held_loss(model, held)
    if a.arm in ("layered", "layered_half"):
        states = torch.cat([(t1 + t2).flatten() for t1, t2 in zip(trainer.t1, trainer.t2)])
        hist = {int(v): round(float((states == v).float().mean()), 4) for v in (-2, -1, 0, 1, 2)}
        # 2 counters (int8, or int16 with --carry) + 2 ternary states at 2 bits each
        state_bytes = (4 if a.carry else 2) * n_tern + n_tern // 2
    elif a.arm in ("ste", "ste_half"):
        hist, state_bytes = {}, 12 * n_tern
    else:
        states = torch.cat([t.flatten() for t in trainer.t])
        hist = {int(v): round(float((states == v).float().mean()), 4) for v in (-1, 0, 1)}
        state_bytes = (2 if a.arm == "mag" else 1) * n_tern + n_tern // 4
    rec = {"arm": label, "seed": a.seed, "steps": steps, "wall_s": round(wall, 1),
           "held_init": round(h0, 4), "held_final": round(h1, 4),
           "train_last100": round(sum(losses[-100:]) / max(1, len(losses[-100:])), 4),
           "ternary_weights": n_tern, "mech_state_bytes": state_bytes,
           "mean_flip_share": round(sum(jumps) / max(1, len(jumps)), 5), "state_hist": hist,
           "corpus_pieces": int(len(data)), "minutes": a.minutes,
           "rope": bool(a.rope), "carry": bool(a.carry), "cooldown": bool(a.cooldown),
           "total_params": sum(p.numel() for p in model.parameters())}
    with open(LAB / "runs.jsonl", "a") as f:
        f.write(json.dumps(rec) + "\n")
    print("RESULT " + json.dumps(rec), flush=True)

if __name__ == "__main__":
    main()
