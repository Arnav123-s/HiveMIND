# Muse's work, Muse's side - profiling probe (instrumented COPY, train.py untouched)
import sys, time, random, json, resource
sys.path.insert(0, "/home/hatch/workspace/edit-lab/bitnet-lab")
t_wall0 = time.perf_counter()
import numpy as np
t_np = time.perf_counter()
import torch
import torch.nn.functional as F
t_torch = time.perf_counter()
import train as T
t_trainmod = time.perf_counter()
print(json.dumps({"phase": "imports", "numpy_s": round(t_np - t_wall0, 3), "torch_s": round(t_torch - t_np, 3), "trainmod_s": round(t_trainmod - t_torch, 3)}), flush=True)
import argparse
ap = argparse.ArgumentParser()
ap.add_argument("--dim", type=int, default=192)
ap.add_argument("--layers-n", type=int, default=2)
ap.add_argument("--steps", type=int, default=12)
ap.add_argument("--batch", type=int, default=32)
ap.add_argument("--rope", action="store_true")
ap.add_argument("--prof", action="store_true")
a = ap.parse_args()
cpu_setup0 = time.process_time()
t0 = time.perf_counter()
data = np.memmap(T.LAB / "corpus.u16", dtype=np.uint16, mode="r")
t_map = time.perf_counter()
held = T.held_windows(data)
t_held = time.perf_counter()
torch.manual_seed(0)
model = T.Tiny(layers=a.layers_n, dim=a.dim, rotary=a.rope)
t_model = time.perf_counter()
trainer = T.Layered(model)
t_trainer = time.perf_counter()
h0 = T.held_loss(model, held)
t_h0 = time.perf_counter()
print(json.dumps({"phase": "setup", "memmap_s": round(t_map - t0, 4), "held_windows_s": round(t_held - t_map, 4), "model_init_s": round(t_model - t_held, 4), "trainer_init_s": round(t_trainer - t_model, 4), "held_loss_init_s": round(t_h0 - t_trainer, 4), "rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1), "cpu_setup_s": round(time.process_time() - cpu_setup0, 3)}), flush=True)
import torch.nn as nn

def timed_step(loss, trainer):
    ph = {}
    s = time.process_time()
    trainer.opt.zero_grad(set_to_none=True)
    for m in trainer.layers:
        m.weight.grad = None
    loss.backward()
    ph["backward"] = time.process_time() - s
    s = time.process_time()
    nn.utils.clip_grad_norm_([p for g in trainer.opt.param_groups for p in g["params"] if p.grad is not None], 1.0)
    ph["clip"] = time.process_time() - s
    s = time.process_time()
    V = trainer.votes
    with torch.no_grad():
        for i, m in enumerate(trainer.layers):
            g = m.weight.grad
            t1, t2 = trainer.t1[i], trainer.t2[i]
            ss = t1 + t2
            trainer.log_scale[i].grad = (g * ss).sum() * trainer.log_scale[i].exp()
            strong = g.abs() >= g.abs().median()
            vote = (-g.sign() * strong).to(torch.int8)
            c1 = (trainer.c1[i] + vote).clamp(-V, V)
            c2 = (trainer.c2[i] + vote).clamp(-V, V)
            go1 = (c1.abs() >= V) & ((t1 + c1.sign()).clamp(-1, 1) != t1)
            go2 = (~go1) & (c2.abs() >= V) & ((t2 + c2.sign()).clamp(-1, 1) != t2)
            trainer.t1[i] = torch.where(go1, (t1 + c1.sign()).clamp(-1, 1), t1)
            trainer.t2[i] = torch.where(go2, (t2 + c2.sign()).clamp(-1, 1), t2)
            trainer.c1[i] = torch.where(go1, torch.zeros_like(c1), c1)
            trainer.c2[i] = torch.where(go2, torch.zeros_like(c2), c2)
    ph["vote_update"] = time.process_time() - s
    s = time.process_time()
    trainer.opt.step()
    ph["adamw_shared"] = time.process_time() - s
    s = time.process_time()
    trainer.install()
    ph["install_rewrite"] = time.process_time() - s
    trainer.steps += 1
    return ph

rnd = random.Random(0)
rows = []
prof = None
if a.prof:
    from torch.profiler import profile, ProfilerActivity
    prof = profile(activities=[ProfilerActivity.CPU], record_shapes=False, with_stack=False)
    prof.start()
cpu0 = time.process_time()
wall0 = time.perf_counter()
for step in range(a.steps):
    s = time.process_time()
    at = T.offsets(rnd, len(data), a.batch)
    x = torch.stack([torch.from_numpy(data[i:i + T.CTX + 1].astype("int64")) for i in at])
    t_batch = time.process_time() - s
    s = time.process_time()
    loss = F.cross_entropy(model.next_piece(x[:, :-1]).reshape(-1, T.VOCAB), x[:, 1:].reshape(-1))
    lv = loss.item()
    t_fwd = time.process_time() - s
    ph = timed_step(loss, trainer)
    rows.append({"step": step, "batch_s": round(t_batch, 4), "fwd_lossitem_s": round(t_fwd, 4), **{k: round(v, 4) for k, v in ph.items()}})
    print(json.dumps(rows[-1]), flush=True)
wall_steps = time.perf_counter() - wall0
cpu_steps = time.process_time() - cpu0
if prof:
    prof.stop()
    print(prof.key_averages().table(sort_by="self_cpu_time_total", row_limit=30), flush=True)
t1 = time.perf_counter()
h1 = T.held_loss(model, held)
t_h1 = time.perf_counter()
import statistics
keys = [k for k in rows[0] if k != "step"]
use = rows[1:] if len(rows) > 3 else rows
med = {k: round(statistics.median([r[k] for r in use]), 4) for k in keys}
tot = sum(med.values())
print(json.dumps({"phase": "summary", "steps": a.steps, "median_s": med, "step_total_median_s": round(tot, 4), "steps_per_s": round(1 / tot, 3) if tot else None, "held_loss_final_s": round(t_h1 - t1, 4), "rss_peak_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1), "threads_torch": torch.get_num_threads(), "wall_steps_s": round(wall_steps, 2), "cpu_steps_s": round(cpu_steps, 2), "cpu_eff": round(cpu_steps / wall_steps, 3) if wall_steps else None, "wall_probe_s": round(time.perf_counter() - t_wall0, 2)}), flush=True)
