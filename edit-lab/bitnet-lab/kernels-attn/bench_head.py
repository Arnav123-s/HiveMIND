# Muse's work — kernel strike team B (head/embedding), Muse's side. Read-only wrt train.py.
"""LM head + embedding cost share at the ladder shapes.

One training step's forward is model.next_piece(ids) = body(ids) @ tok.weight.T
plus (in main) cross-entropy over [batch*CTX, VOCAB=4096] logits. This script
splits forward and forward+backward into: embedding lookup, block body, head
matmul (tied embedding weight), cross-entropy, and the full step, at ladder 2M
(dim 288, 2 blocks) and 10M (dim 512, 3 blocks), rope on (ladder config).
Timing: interleaved min-of-samples (shared, loaded box; min = least contended).
fp32, OMP/MKL=2.
"""
import os, sys, time, json
os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")
sys.path.insert(0, os.path.expanduser("~/workspace/edit-lab/bitnet-lab"))
import torch
import torch.nn.functional as F
import train as T

torch.set_num_threads(2)
B, CTX, VOCAB = 32, 256, 4096


def interleaved_min(fns, inner=1, samples=4):
    best = {n: float("inf") for n in fns}
    for _ in range(samples):
        for n, fn in fns.items():
            t0 = time.perf_counter()
            for _ in range(inner):
                fn()
            dt = (time.perf_counter() - t0) / inner
            if dt < best[n]:
                best[n] = dt
    return {n: round(v * 1000, 3) for n, v in best.items()}


def run(dim, layers, label, fb_samples):
    torch.manual_seed(0)
    model = T.Tiny(layers=layers, dim=dim, rotary=True)
    model.train()
    ids = torch.randint(0, VOCAB, (B, CTX + 1))
    x_in, target = ids[:, :-1], ids[:, 1:]
    with torch.no_grad():
        body_out = model.body(x_in)

    fwd = interleaved_min({
        "embed_lookup": lambda: model.tok(x_in),
        "body": lambda: model.body(x_in),
        "head_matmul": lambda: body_out @ model.tok.weight.T,
        "cross_entropy": lambda: F.cross_entropy((body_out @ model.tok.weight.T).reshape(-1, VOCAB), target.reshape(-1)),
        "next_piece": lambda: model.next_piece(x_in),
    }, inner=3, samples=4)

    def step_full():
        model.zero_grad(set_to_none=True)
        loss = F.cross_entropy(model.next_piece(x_in).reshape(-1, VOCAB), target.reshape(-1))
        loss.backward()

    def step_head():
        h = body_out.clone().requires_grad_(True)
        loss = F.cross_entropy((h @ model.tok.weight.T).reshape(-1, VOCAB), target.reshape(-1))
        loss.backward()

    fb = interleaved_min({"full_step": step_full, "head_plus_ce": step_head}, inner=1, samples=fb_samples)

    print(f"\n== {label}: dim={dim} layers={layers} heads=4 rope on (min, ms) ==")
    for k_, v in fwd.items():
        print(f"  fwd {k_:16s} {v:9.2f}")
    for k_, v in fb.items():
        print(f"  fb  {k_:16s} {v:9.2f}")
    share_fb = 100.0 * fb["head_plus_ce"] / fb["full_step"]
    fwd_total = fwd["next_piece"] + fwd["cross_entropy"]
    share_fwd = 100.0 * (fwd["head_matmul"] + fwd["cross_entropy"]) / fwd_total
    print(f"  output side share: fwd {share_fwd:.1f}% | fwd+bwd {share_fb:.1f}%")
    return {"fwd_ms": fwd, "fb_ms": fb, "output_share_fwd_pct": round(share_fwd, 1),
            "output_share_fb_pct": round(share_fb, 1)}


if __name__ == "__main__":
    print(f"torch {torch.__version__} threads={torch.get_num_threads()}")
    out = {}
    out["ladder2m"] = run(288, 2, "ladder 2M", fb_samples=4)
    out["ladder10m"] = run(512, 3, "ladder 10M", fb_samples=3)
    print("\nJSON " + json.dumps(out))
