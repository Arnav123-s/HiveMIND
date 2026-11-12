"""Can the body teach its stem cell? The third body's stem cell (it never read a held window) goes on learning for
the same minutes in four ways: reading on at three rates, and "sleep": the body reads a set of training windows,
what it expects at every piece is kept (its 32 likeliest pieces), and the stem cell reads half its batches from
those windows, learning the body's expectations as well as the text. The time the body takes to read is part of
the sleep's minutes. Then each stem cell alone on held windows, and the body with it in the stem cell's seat."""
import sys, os, json, random, time, torch, torch.nn.functional as F
os.environ["HIVE_BODY"] = sys.argv[2] if len(sys.argv) > 2 else "b3"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from training import scratch as T, body as B
torch.set_num_threads(4)
MIN = float(sys.argv[1]); ONLY = sys.argv[3:]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sleep_result.json")
data = B._data(); b = B.Body(); rnd = random.Random(3); V = T.VOCAB
n = min(B._windows(data), B.YARD)
held = rnd.sample([i for i in range(n) if i % B.HELD == 0], 300)
train = [i for i in range(n) if i % B.HELD]
gate = B._held(data, "gate", 200, upto=B.YARD)
gf, gs, _ = b.read(data, gate)


def judged(stem):
    stem = stem.eval()
    f2, s2 = B._read_all({"stem": stem}, data, gate)
    first, second = gf.clone(), gs.clone()
    first[:, 0], second[:, 0] = f2[:, 0], s2[:, 0]
    return {"stem cell alone, held": round(B._check_loss(stem, data, held), 4), "the body with it, gate": round(B.fit_loss(first, second).mean().item(), 4)}


def fresh():
    stem = B._stem()
    for p in (stem.tok.weight, stem.pos.weight): p.requires_grad_(False)
    return stem


def teach(windows, k=32, m=B.NEAR_M):
    """What the body expects at every piece of these windows: its k likeliest pieces and their log-probabilities,
    and how much it leaves for all the others. Its members are weighed by how each fits the whole window."""
    alive = [c for c in b.alive if c < b.terr["centre"].shape[0]]
    m = min(m, len(alive)); rule = B._rule()
    open_ = torch.full((b.terr["centre"].shape[0],), float("-inf")); open_[alive] = 0.0
    idx, lp, rest = [], [], []
    with torch.no_grad():
        for j in range(0, len(windows), 8):
            ws = windows[j:j + 8]; x = torch.stack([B._window(data, i) for i in ws])
            full = F.log_softmax(b.stem.next_piece(x[:, :-1]), -1)[:, None].repeat(1, 1 + m, 1, 1)
            who = (b.near(data, ws) + open_).topk(m, dim=1).indices
            for c in sorted(set(who.flatten().tolist())):
                rows, slots = (who == c).nonzero(as_tuple=True)
                full[rows, 1 + slots] = F.log_softmax(b.cell(c).next_piece(x[rows, :-1]), -1)
            fit = -full.gather(-1, x[:, 1:][:, None, :, None].expand(-1, 1 + m, -1, 1))[..., 0].mean(2)
            mix = torch.logsumexp(full + B._say(fit, rule)[:, :, None, None], 1)
            top = mix.topk(k, dim=-1)
            idx.append(top.indices.to(torch.int16)); lp.append(top.values.to(torch.float16))
            rest.append(torch.log1p(-top.values.exp().sum(-1).clamp(max=1 - 1e-6)).to(torch.float16))
    return torch.cat(idx), torch.cat(lp), torch.cat(rest)


def sleep(stem, minutes, rate, dreams=2000, share=0.5, batch=32, seed=0):
    t0 = time.time(); r = random.Random(seed)
    D = r.sample(train, dreams)
    idx, lp, rest = teach(D)
    told = (time.time() - t0) / 60
    check = train[::10][:96]; seen = [w for i, w in enumerate(train) if i % 10]
    opt = torch.optim.AdamW([p for p in stem.parameters() if p.requires_grad], lr=rate, weight_decay=0.01, betas=(0.9, 0.95))
    def checked():
        stem.eval(); v = B._check_loss(stem, data, check); stem.train(); return v
    start = checked(); best, stale, steps = (start, {k: v.clone() for k, v in stem.state_dict().items()}), 0, 0
    half = batch // 2
    while time.time() - t0 < minutes * 60 and stale < 3:
        d = [r.randrange(dreams) for _ in range(half)]
        x = torch.stack([B._window(data, D[i]) for i in d] + [B._window(data, r.choice(seen)) for _ in range(batch - half)])
        logp = F.log_softmax(stem.next_piece(x[:, :-1]), -1)
        hard = F.nll_loss(logp.reshape(-1, V), x[:, 1:].reshape(-1))
        ls = logp[:half].gather(-1, idx[d].long())
        s_rest = torch.log1p(-ls.exp().sum(-1).clamp(max=1 - 1e-6))
        soft = (-(lp[d].float().exp() * ls).sum(-1) - rest[d].float().exp() * s_rest).mean()
        loss = (1 - share) * hard + share * soft
        opt.zero_grad(set_to_none=True); loss.backward(); torch.nn.utils.clip_grad_norm_(stem.parameters(), 1.0); opt.step()
        steps += 1
        if steps % 100 == 0:
            v = checked()
            if v < best[0] - 0.002: best, stale = (v, {k: t.clone() for k, t in stem.state_dict().items()}), 0
            else: stale += 1
    stem.load_state_dict(best[1])
    return steps, round(told, 2)


out = {"before": judged(B._stem())}
print("before", out["before"], flush=True)
try: out.update({k: v for k, v in json.load(open(OUT)).items() if k != "before"})
except Exception: pass
for rate in (3e-4, 1e-3, 3e-3):
    name = f"reads on, rate {rate:g}"
    if name in out or (ONLY and not any(o in name for o in ONLY)): continue
    stem = fresh()
    steps, best, was = B._read(stem, data, train, MIN, seed=0, lr=rate, share_table=False)
    out[name] = dict(judged(stem), steps=steps, rate=rate)
    print(name, out[name], flush=True); json.dump(out, open(OUT, "w"), indent=1)
plain = {k: v for k, v in out.items() if k.startswith("reads on")}
rate = min(plain.values(), key=lambda v: v["stem cell alone, held"])["rate"] if plain else 1e-3
for name, kw in {f"sleep: taught by the body, rate {rate:g}": dict(), f"sleep, 4000 windows, rate {rate:g}": dict(dreams=4000),
                 f"sleep, the body's word counts for three quarters, rate {rate:g}": dict(share=0.75)}.items():
    if name in out or (ONLY and not any(o in name for o in ONLY)): continue
    stem = fresh()
    steps, told = sleep(stem, MIN, rate, **kw)
    out[name] = dict(judged(stem), steps=steps, minutes_the_body_read=told)
    print(name, out[name], flush=True); json.dump(out, open(OUT, "w"), indent=1)
