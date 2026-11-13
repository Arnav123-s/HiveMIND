# Muse's work - Muse's side. Kernel benchmark 2: the vote-counter update step.
# Baseline = the inner update of train.py's Layered.step (the champion's trainer),
# verbatim semantics: same gate (median of |g|), same vote, same clamp/reset, V=32,
# one flip per weight per step (t1 first, t2 only if t1 did not flip).
# The AdamW/backward parts are NOT timed - only the elementwise vote update over all
# BitLinear layers, which is the part a kernel can change.
import json, time
import torch

torch.set_num_threads(2)
torch.manual_seed(20261112)
V = 32

def bench(fn, reps=9, warm=3):
    for _ in range(warm):
        fn()
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter(); fn(); ts.append(time.perf_counter() - t0)
    ts.sort()
    return ts[len(ts) // 2]

def make_state(shapes):
    gs, t1s, t2s, c1s, c2s = [], [], [], [], []
    for (n, k) in shapes:
        gs.append(torch.randn(n, k) * 0.01)
        t = torch.randint(-1, 2, (n, k)).float()
        t1s.append(t.clone()); t2s.append(torch.zeros_like(t))
        c1s.append(torch.randint(-V, V + 1, (n, k), dtype=torch.int8))
        c2s.append(torch.randint(-V, V + 1, (n, k), dtype=torch.int8))
    return gs, t1s, t2s, c1s, c2s

def step_current(gs, t1s, t2s, c1s, c2s):
    """train.py Layered.step update block, verbatim (minus log_scale grad/counting)."""
    with torch.no_grad():
        for i in range(len(gs)):
            g = gs[i]; t1, t2 = t1s[i], t2s[i]
            strong = g.abs() >= g.abs().median()
            vote = (-g.sign() * strong).to(torch.int8)
            c1 = (c1s[i] + vote).clamp(-V, V)
            c2 = (c2s[i] + vote).clamp(-V, V)
            go1 = (c1.abs() >= V) & ((t1 + c1.sign()).clamp(-1, 1) != t1)
            go2 = (~go1) & (c2.abs() >= V) & ((t2 + c2.sign()).clamp(-1, 1) != t2)
            t1s[i] = torch.where(go1, (t1 + c1.sign()).clamp(-1, 1), t1)
            t2s[i] = torch.where(go2, (t2 + c2.sign()).clamp(-1, 1), t2)
            c1s[i] = torch.where(go1, torch.zeros_like(c1), c1)
            c2s[i] = torch.where(go2, torch.zeros_like(c2), c2)

def step_fused(gs, t1s, t2s, c1s, c2s):
    """Fused/in-place: sign computed once; the flip test (t+s).clamp(-1,1) != t is
    replaced by the exactly-equivalent (s != 0) & (t != s); counters updated in place;
    where() writes into preallocated outputs via out=."""
    with torch.no_grad():
        for i in range(len(gs)):
            g = gs[i]; t1, t2 = t1s[i], t2s[i]
            strong = g.abs() >= g.abs().median()
            vote = (-g.sign() * strong).to(torch.int8)
            c1 = c1s[i].add_(vote).clamp_(-V, V)
            c2 = c2s[i].add_(vote).clamp_(-V, V)
            s1, s2 = c1.sign(), c2.sign()
            go1 = (c1.abs() >= V) & (s1 != 0) & (t1 != s1.float())
            go2 = (~go1) & (c2.abs() >= V) & (s2 != 0) & (t2 != s2.float())
            # on a flip the new value is exactly t + s (t=0 -> s; t=-s -> 0; t=s never flips)
            t1s[i] = torch.where(go1, t1 + s1.float(), t1)
            t2s[i] = torch.where(go2, t2 + s2.float(), t2)
            c1s[i] = torch.where(go1, torch.zeros_like(c1), c1)
            c2s[i] = torch.where(go2, torch.zeros_like(c2), c2)

def clone_state(base):
    return [[x.clone() for x in lst] for lst in base]

def run(shapes, label):
    base = make_state(shapes)
    a = clone_state(base)
    step_current(a[0], a[1], a[2], a[3], a[4])
    b = clone_state(base)
    step_fused(b[0], b[1], b[2], b[3], b[4])
    maxerr = max((x - y).abs().max().item()
                 for la, lb in zip(a, b) for x, y in zip(la, lb))
    # NOTE: step_fused mutates counters in place; re-clone per timing call.
    def timed_current():
        st = clone_state(base)
        step_current(st[0], st[1], st[2], st[3], st[4])
    def timed_fused():
        st = clone_state(base)
        step_fused(st[0], st[1], st[2], st[3], st[4])
    # cloning cost is identical for both; also report clone-only time for honesty.
    clone_t = bench(lambda: clone_state(base))
    tc = bench(timed_current); tf = bench(timed_fused)
    nw = sum(g.numel() for g in base[0])
    print(json.dumps({'case': label, 'weights': nw, 'fused_max_state_err': maxerr,
                      'clone_only_s': clone_t, 'current_s': tc, 'fused_s': tf,
                      'current_net_s': tc - clone_t, 'fused_net_s': tf - clone_t}))

# Champion: dim 192, 2 blocks. Per block: qkv 192->576, out 192->192, up 192->768, down 768->192.
champ = [(576, 192), (192, 192), (768, 192), (192, 768)] * 2
run(champ, 'champion_884736')
# Ladder 2M: dim 288, 2 blocks.
lad = [(864, 288), (288, 288), (1152, 288), (288, 1152)] * 2
run(lad, 'ladder2m_1990656')
