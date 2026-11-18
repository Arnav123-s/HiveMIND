"""Check changes to the weight scales of the existing scratch language stem on task text."""
import argparse
import hashlib
import json
import random
from pathlib import Path

import torch
from torch.nn import functional as F

from training import exam, scratch
from training.experiments.engram_halves import FittedBitLinear


def prompts(makers, count, seed):
    tk = scratch.tokenizer()
    batches = []
    for maker in makers:
        rnd = random.Random(f"{seed}/{maker.__name__}")
        texts = {}
        for _ in range(1000):
            text = maker(rnd)[2]
            texts[text] = None
            if len(texts) == count:
                break
        if len(texts) != count:
            raise ValueError(f"insufficient distinct prompts for {maker.__name__}")
        ids = [torch.tensor(([scratch.BOS] + tk.encode(t).ids)[:scratch.CTX]) for t in texts]
        for offset in range(0, len(ids), 8):
            batch = torch.nn.utils.rnn.pad_sequence(ids[offset:offset + 8], batch_first=True, padding_value=scratch.PAD)
            batches.append((maker.__name__, batch))
    return batches


@torch.inference_mode()
def score(state, policy, batches):
    model = scratch.Tiny(bit=True).eval()
    for block, method in zip(model.blocks, policy):
        if method != "absmean":
            for name in ("qkv", "out", "up", "down"):
                layer = getattr(block, name)
                setattr(block, name, FittedBitLinear(layer.in_features, layer.out_features, method))
    model.load_state_dict(state)
    stats = {}
    for kind, ids in batches:
        logits = model.next_piece(ids[:, :-1])
        target = ids[:, 1:]
        nll = F.cross_entropy(logits.reshape(-1, logits.shape[-1]), target.reshape(-1),
                              ignore_index=scratch.PAD, reduction="sum").item()
        loss, n = stats.get(kind, (0., 0))
        stats[kind] = (loss + nll, n + int((target != scratch.PAD).sum()))
    losses, counts = zip(*stats.values())
    return {"nll": sum(losses) / sum(counts), "tokens": sum(counts),
            "nll_by_family": {key: v / n for key, (v, n) in stats.items()}}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    torch.set_num_threads(1)
    dev = prompts((exam.m_percent, exam.m_days, exam.m_fix, exam.m_table), 16, 51001)
    test = prompts((exam.m_units, exam.m_weekday, exam.m_code, exam.m_steps), 24, 51002)
    path = scratch.HOME / "base.pt"
    state = torch.load(path, weights_only=True)
    layers = scratch.kind()["layers"]
    with path.open("rb") as stream:
        stem_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    out = {"stem_sha256": stem_hash, "calibration_prompts": 64, "test_prompts": 96,
           "block_trials_calibration_only": [], "policies": {}}
    methods = ("absmean", "fit", "rowfit")
    for method in methods:
        policy = [method] * layers
        out["policies"][method] = {"blocks": policy, "calibration": score(state, policy, dev)}
    chosen = ["absmean"] * layers
    for block in range(layers):
        trials = {}
        for method in methods:
            chosen[block] = method
            trials[method] = score(state, chosen, dev)["nll"]
        chosen[block] = min(trials, key=trials.get)
        out["block_trials_calibration_only"].append(trials)
    out["policies"]["calibrated"] = {"blocks": chosen, "calibration": score(state, chosen, dev)}
    for row in out["policies"].values():
        row["test"] = score(state, row["blocks"], test)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2) + "\n")
    print([(k, row["blocks"], row["test"]["nll"]) for k, row in out["policies"].items()])


if __name__ == "__main__":
    main()
