"""Train a checkpointable low-rank CPU slice on 60 archived T80 endpoints."""
import argparse
from contextlib import nullcontext
from hashlib import sha256
import json
import os
from pathlib import Path
import random
import time

import torch

from training import grow, ternary_base
from training.experiments.atlas.islands import data
from training.experiments.verified_growth.recovery import checkpoint


HERE = Path(__file__).resolve().parent
CONFIG = {"updates": 32, "accum": 4, "rank": 4, "alpha": 8, "dropout": 0.1,
          "lr": 0.001, "seed": 91347, "weight_decay": 0.0}


def make_slice():
    rows, features, tokens, base, *_ = data.load()
    eligible = [i for i, row in enumerate(rows) if row.split == "train"]
    features = torch.tensor(features[eligible], dtype=torch.float32)
    base = torch.tensor(base[eligible], dtype=torch.float32)
    token_index = {int(token): j for j, token in enumerate(tokens)}
    targets = torch.tensor([token_index[rows[i].token] for i in eligible], dtype=torch.long)
    domains = {}
    for idx, i in enumerate(eligible):
        domains.setdefault(rows[i].domain, []).append(idx)
    study = grow.Study(domains, rng=random.Random(CONFIG["seed"]), own=("coding",))
    flat = torch.zeros((len(tokens), features.shape[1]))
    model = ternary_base.TernaryLinear(flat, rank=CONFIG["rank"], alpha=CONFIG["alpha"], dropout=CONFIG["dropout"])
    optimizer = torch.optim.AdamW(model.parameters(), lr=CONFIG["lr"], weight_decay=CONFIG["weight_decay"])
    encoded = sha256()
    for tensor in (features, base, targets):
        encoded.update(tensor.numpy().tobytes())
    encoded.update(json.dumps([rows[i].key for i in eligible]).encode())
    identity = {"data": encoded.hexdigest(), "config": CONFIG, "torch": str(torch.__version__),
                "sources": {p.name: checkpoint.digest(p) for p in (Path(__file__), Path(checkpoint.__file__),
                            Path(grow.__file__), Path(ternary_base.__file__), Path(data.__file__))}}
    return features, base, targets, study, model, optimizer, identity


def run(args):
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.manual_seed(CONFIG["seed"])
    random.seed(CONFIG["seed"])
    features, base, targets, study, model, optimizer, identity = make_slice()
    history = []
    step = 0
    rows_this_process = 0
    if args.store and not args.resume and any(args.store.glob("step-*.pt")):
        raise ValueError("published checkpoints already exist; resume them or select a new store")
    if args.resume:
        state = checkpoint.latest(args.store, identity)
        if state is None:
            raise ValueError("resume requested from an empty retained store")
        checkpoint.restore(state, model, optimizer, study)
        step, history = state["step"], state["history"]
    initial_step = step
    t0 = time.perf_counter()
    publications = []
    while step < CONFIG["updates"]:
        for _ in range(CONFIG["accum"]):
            subject, index = study.pick()
            logits = base[index:index + 1] + model(features[index:index + 1])
            loss = torch.nn.functional.cross_entropy(logits, targets[index:index + 1])
            (loss / CONFIG["accum"]).backward()
            study.learned(subject, loss.item())
            history.append([subject, index, loss.item()])
            rows_this_process += 1
            if args.fail_row == len(history):
                # This destroys the process before it can flush partial gradients or write a final model.
                print(json.dumps({"exit_at_row": len(history), "rows_executed": rows_this_process,
                                  "last_complete_update": step, "checkpoints": publications}), flush=True)
                os._exit(75)
        progress = (step + 1) / CONFIG["updates"]
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.param_groups[0]["lr"] = CONFIG["lr"] * grow.lr_share(progress)
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        step += 1
        if args.store and step % args.interval == 0:
            state = checkpoint.capture(identity, step, model, optimizer, study, history)
            started = time.perf_counter()
            obj = checkpoint.publish(args.store, state)
            publications.append({"step": step, "bytes": obj.stat().st_size,
                                 "seconds": round(time.perf_counter() - started, 6)})
    final = checkpoint.capture(identity, step, model, optimizer, study, history)
    with args.out.open("wb") as file:
        torch.save(final, file)
    print(json.dumps({"initial_step": initial_step, "final_step": step, "rows_executed": rows_this_process,
                      "eligible_rows": len(targets), "trainable_parameters": sum(p.numel() for p in model.parameters()),
                      "training_seconds": round(time.perf_counter() - t0, 6), "checkpoints": publications}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, help="single-writer directory on independently retained storage")
    parser.add_argument("--interval", type=int, default=5)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--fail-row", type=int, help="abruptly terminate during the indicated row (test only)")
    args = parser.parse_args()
    if args.interval < 1 or (args.resume and args.store is None):
        parser.error("positive checkpoint interval and a store for --resume required")
    with checkpoint.single_writer(args.store) if args.store else nullcontext():
        run(args)


if __name__ == "__main__":
    main()
