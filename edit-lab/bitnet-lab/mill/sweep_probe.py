#!/usr/bin/env python3
"""sweep_probe.py — the mill's shared-data sweep runner (Muse's work, Muse's side).

ONE process loads the corpus memmap and builds the 128 held windows ONCE, then runs a
batch of same-chassis config variants back-to-back in-process. On this VM, interpreter +
torch startup and data setup are a large share of a 75-second probe's cost; the sweep
pays them once per batch instead of once per probe.

Fidelity rule: the per-job training loop below replicates train.py main()'s loop
statement-for-statement, using train.py's OWN classes and functions (Tiny, Direct,
Layered, STE, held_windows, held_loss, offsets, EASE) imported from the lab. Records
are appended to the lab's runs.jsonl in exactly main()'s format (tag mill<id>) and
also echoed to stdout as RESULT lines for screen.py to ledger.

Usage: sweep_probe.py <jobs.jsonl>     (run with the lab venv python)
Each job line: {"id": "MILL-1101", "run": "--arm layered_half --rope --dim 256
--layers-n 1", "minutes": 1.25, "seed": 0, "tag": "mill1101"}
Output lines:  MILLJOB <id>            (job starting)
               RESULT {json}           (train.py-format record)
               MILLERR <id> <why>      (job failed; batch continues)
               MILLSTOP busy:<pat>     (a heavier lab process appeared; batch stops
                                        cleanly, unrun jobs stay queued)
Between jobs the runner re-checks for ladder/growth/other drivers and stops cleanly —
the mill always yields the lab.

Job kinds: a job line may carry "kind": "confirm" — a confirmation run (screen.py's
selection-pressure guard). Its training sampler excludes BOTH the held blocks and the
confirmation blocks (every-40th offset by 20), and its record carries confirm_final:
the loss on the confirmation windows, measured with train.held_loss.

Startup refuses loudly (MILLFATAL, exit 2) if this file's argument parser has drifted
from train.py's — the parser is a copy, and a silent mismatch would bench jobs whose
only fault is a flag the copy never learned.
"""
import argparse, json, random, re, shlex, subprocess, sys, time
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB))

import numpy as np
import torch
import torch.nn.functional as F

import train as T  # the lab's own module: classes, held_windows, held_loss, offsets

BUSY_PATTERNS = ("run_scale_ladder", "growth_cycle", "run_jepa", "run_round2",
                 "run_sweep", "scale_ladder", "python -m team")


def busy():
    for pat in BUSY_PATTERNS:
        out = subprocess.run(["pgrep", "-fc", pat], capture_output=True, text=True).stdout.strip()
        if out.isdigit() and int(out) > 0:
            return pat
    return None


CONFIRM_OFFSET = 20  # confirmation blocks: every-40th, offset by 20 from the held blocks


def confirm_windows(data, n_eval=128):
    """The confirmation set — train.held_windows with the block residue shifted by
    CONFIRM_OFFSET. Disjoint from the held set by construction; used ONLY by
    confirmation runs, never for probes or verdicts."""
    starts = [w * T.CTX for w in range(0, (len(data) - T.CTX) // T.CTX)
              if w % T.HELD_EVERY == CONFIRM_OFFSET]
    pick = [starts[int(i * (len(starts) - 1) / (n_eval - 1))] for i in range(n_eval)]
    return torch.stack([torch.from_numpy(data[s:s + T.CTX + 1].astype("int64")) for s in pick])


def offsets_x(rnd, n, batch):
    """train.offsets with the confirmation blocks excluded as well: a window is
    rejected if either block it touches is a held block (residue 0) or a
    confirmation block (residue CONFIRM_OFFSET)."""
    out = []
    while len(out) < batch:
        i = rnd.randrange(0, n - T.CTX - 1)
        b0 = (i // T.CTX) % T.HELD_EVERY
        b1 = ((i + T.CTX) // T.CTX) % T.HELD_EVERY
        if b0 not in (0, CONFIRM_OFFSET) and b1 not in (0, CONFIRM_OFFSET):
            out.append(i)
    return out


def make_parser():
    """train.py main()'s argparse, verbatim, so job args mean exactly what they mean
    on the train.py command line."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=["plain", "ste", "mag", "layered", "layered_half",
                                                     "anneal", "plain_half", "ste_half"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--minutes", type=float, default=8.0)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--rope", action="store_true")
    ap.add_argument("--carry", action="store_true")
    ap.add_argument("--cooldown", action="store_true")
    ap.add_argument("--dim", type=int, default=T.DIM)
    ap.add_argument("--layers-n", type=int, default=None)
    ap.add_argument("--steps", type=int, default=0)
    ap.add_argument("--tag", default="")
    ap.add_argument("--ckpt", action="store_true")
    return ap


def parser_drift():
    """make_parser() is a verbatim copy of train.py's argparse. If train.py's
    interface moves (a flag lands, an arm is added), the copy must not silently
    reject jobs — compare against the real --help and report any mismatch."""
    r = subprocess.run([sys.executable, str(LAB / "train.py"), "--help"],
                       capture_output=True, text=True)
    helptext = r.stdout + r.stderr
    real_flags = set(re.findall(r"--[a-z0-9][a-z0-9\-]*", helptext))
    m = re.search(r"\{([^}]*)\}", helptext)
    real_arms = set(x.strip() for x in m.group(1).split(",")) if m else set()
    ap = make_parser()
    my_flags = {o for a in ap._actions for o in a.option_strings if o.startswith("--")}
    arm_action = next(a for a in ap._actions if a.dest == "arm")
    problems = []
    if real_flags != my_flags:
        problems.append(f"flags differ (train.py only: {sorted(real_flags - my_flags)}; "
                        f"sweep only: {sorted(my_flags - real_flags)})")
    if real_arms != set(arm_action.choices or []):
        problems.append(f"--arm choices differ (train.py: {sorted(real_arms)}; "
                        f"sweep: {sorted(arm_action.choices or [])})")
    return problems


def run_one(a, data, held, sampler=None, confirm=None):
    """train.py main()'s body from model construction onward, verbatim semantics.
    Confirmation runs pass sampler=offsets_x (held + confirmation blocks excluded)
    and confirm=<confirmation windows>; their record gains confirm_final."""
    if (a.carry or a.cooldown) and a.arm not in ("layered", "layered_half"):
        raise ValueError("--carry/--cooldown are levers on the layered vote trainer only")
    label = a.arm + ("_rope" if a.rope else "") + ("_carry" if a.carry else "") + \
        ("_cooldown" if a.cooldown else "") + (("_" + a.tag) if a.tag else "")
    torch.manual_seed(a.seed)
    layers = a.layers_n if a.layers_n else (2 if a.arm in ("layered_half", "plain_half", "ste_half") else 4)
    model = T.Tiny(layers=layers, dim=a.dim, rotary=a.rope)
    model.ckpt = a.ckpt
    if a.arm in ("ste", "ste_half"):
        trainer = T.STE(model)
    elif a.arm in ("layered", "layered_half"):
        trainer = T.Layered(model, carry=a.carry, cooldown=a.cooldown)
    else:
        trainer = T.Direct(model, mode="plain" if a.arm == "plain_half" else a.arm)
    n_tern = sum(t.numel() for t in (trainer.t if hasattr(trainer, "t") else trainer.t1)) \
        if a.arm not in ("ste", "ste_half") else \
        sum(p.numel() for m in model.modules() if isinstance(m, T.BitLinear) for p in [m.weight])
    h0 = T.held_loss(model, held)
    rnd, t0, steps, losses, jumps = random.Random(a.seed), time.time(), 0, [], []
    budget = a.minutes * 60
    while time.time() - t0 < budget:
        if a.steps and steps >= a.steps:
            break
        done = (steps / a.steps) if a.steps else (time.time() - t0) / budget
        T.EASE[0] = min(1.0, done / 0.5) if a.arm in ("ste", "ste_half") else 1.0
        at = (sampler or T.offsets)(rnd, len(data), a.batch)
        x = torch.stack([torch.from_numpy(data[i:i + T.CTX + 1].astype("int64")) for i in at])
        loss = F.cross_entropy(model.next_piece(x[:, :-1]).reshape(-1, T.VOCAB), x[:, 1:].reshape(-1))
        losses.append(loss.item())
        jumps.append(trainer.step(loss, done))
        steps += 1
    wall = time.time() - t0
    h1 = T.held_loss(model, held)
    if a.arm in ("layered", "layered_half"):
        states = torch.cat([(t1 + t2).flatten() for t1, t2 in zip(trainer.t1, trainer.t2)])
        hist = {int(v): round(float((states == v).float().mean()), 4) for v in (-2, -1, 0, 1, 2)}
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
           "dim": a.dim, "layers_n": layers, "ckpt": bool(a.ckpt),
           "steps_target": a.steps if a.steps else None,
           "total_params": sum(p.numel() for p in model.parameters())}
    if confirm is not None:
        rec["confirm_final"] = round(T.held_loss(model, confirm), 4)
        rec["eval_set"] = "confirm"
    with open(LAB / "runs.jsonl", "a") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


def main():
    drift = parser_drift()
    if drift:
        for p in drift:
            print(f"MILLFATAL parser drift: {p}", flush=True)
        return 2
    jobs_file = Path(sys.argv[1])
    jobs = [json.loads(l) for l in jobs_file.read_text().splitlines() if l.strip()]
    ap = make_parser()
    data = np.memmap(LAB / "corpus.u16", dtype=np.uint16, mode="r")
    held = T.held_windows(data)
    confirm = None
    print(f"MILLSWEEP up: {len(jobs)} jobs, corpus loaded once ({len(data)} pieces)", flush=True)
    for job in jobs:
        b = busy()
        if b:
            print(f"MILLSTOP busy:{b}", flush=True)
            return 0
        print(f"MILLJOB {job['id']}", flush=True)
        try:
            argv = shlex.split(job["run"]) + ["--seed", str(job.get("seed", 0)),
                                              "--minutes", str(job["minutes"]),
                                              "--tag", job.get("tag", "")]
            a = ap.parse_args(argv)
            if job.get("kind") == "confirm":
                if confirm is None:
                    confirm = confirm_windows(data)
                rec = run_one(a, data, held, sampler=offsets_x, confirm=confirm)
            else:
                rec = run_one(a, data, held)
            print("RESULT " + json.dumps(rec), flush=True)
        except SystemExit as e:  # argparse rejection of a job's args
            print(f"MILLERR {job['id']} argparse exit {e.code}", flush=True)
        except Exception as e:
            print(f"MILLERR {job['id']} {type(e).__name__}: {e}", flush=True)
    print("MILLSWEEP done", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
