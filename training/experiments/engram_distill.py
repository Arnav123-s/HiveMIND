"""Can two cells be reconstructed as one shared ternary network from input/output memories?"""
import argparse
import hashlib
import io
import json
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from training.experiments.engram_halves import FittedBitLinear, capture, fraction, measurements, train


class JointCell(nn.Module):
    def __init__(self):
        super().__init__()
        self.front = FittedBitLinear(12, 40, "fit")
        self.back = FittedBitLinear(40, 2, "fit")

    def forward(self, x):
        return self.back(self.front(x).relu())


def write_trace(logits, inputs, input_seed, init_seed, indices=None, pool_size=None):
    buf = io.BytesIO()
    arrays = {"format": np.int32(1), "torch_version": np.array(str(torch.__version__)),
              "init_seed": np.int64(init_seed), "logits": logits.to(torch.float16).numpy(),
              "input_seed": np.int64(input_seed), "inputs_sha256": np.array(hashlib.sha256(inputs.numpy().tobytes()).hexdigest())}
    if indices is not None:
        arrays.update(indices=indices.numpy().astype("uint16"), pool_size=np.int64(pool_size))
    np.savez_compressed(buf, **arrays)
    return buf.getvalue()


def replay(capsule):
    # The student receives only reproducible sensor inputs and the teachers' stored outputs.
    with np.load(io.BytesIO(capsule), allow_pickle=False) as a:
        if int(a["format"]) != 1:
            raise ValueError("unknown trace format")
        seed = int(a["init_seed"])
        logits = torch.from_numpy(a["logits"].astype("float32"))
        rng = torch.Generator().manual_seed(int(a["input_seed"]))
        count = int(a["pool_size"]) if "pool_size" in a else len(logits)
        inputs = torch.randn(count, 12, generator=rng)
        if "indices" in a:
            inputs = inputs[a["indices"].astype("int64")]
        if hashlib.sha256(inputs.numpy().tobytes()).hexdigest() != str(a["inputs_sha256"]):
            raise ValueError(f"input generator disagrees with trace from Torch {a['torch_version']}")
    torch.manual_seed(seed)
    model = JointCell()
    opt = torch.optim.AdamW(model.parameters(), lr=0.008, weight_decay=0.005)
    batch = torch.Generator().manual_seed(seed + 1)
    temperature = 2.
    targets = torch.sigmoid(logits / temperature)
    for _ in range(600):
        idx = torch.randint(len(inputs), (128,), generator=batch)
        opt.zero_grad(set_to_none=True)
        loss = F.binary_cross_entropy_with_logits(model(inputs[idx]) / temperature, targets[idx]) * temperature**2
        loss.backward()
        opt.step()
    return model.eval()


def boundary_set(seed):
    x, _ = measurements(4096, seed)
    x[:, 5] = x[:, :3].sum(1) - x[:, 3:5].sum(1) + 0.12 * x[:, 5]
    x[:, 6] *= 0.12
    y = torch.stack([x[:, :3].sum(1) > x[:, 3:6].sum(1), (x[:, 6] > 0) != (x[:, 7] > 0)], 1)
    return x, y


def scores(pred, y, teacher):
    return {"accuracy": [fraction(pred[:, i] == y[:, i]) for i in (0, 1)],
            "both_correct": fraction((pred == y).all(1)),
            "teacher_agreement": [fraction(pred[:, i] == teacher[:, i]) for i in (0, 1)]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(1)
    out = {"torch": str(torch.__version__), "steps": 600, "student_width": 40, "test_per_seed": 4096,
           "teacher_widths": [24, 40], "synapses": {"independent": 832, "shared": 560}, "per_seed": {}}
    for seed in (17, 29, 43, 59, 71):
        x, y = measurements(8192, seed * 100 + 1)
        teachers = [train(x, y, j, "fit", seed) for j in (0, 1)]
        def query(x):
            with torch.no_grad():
                return torch.stack([m(x) for m in teachers], 1)
        def reference(pair):
            xx, yy = pair
            return xx, yy, query(xx) > 0
        tests = {"fresh": reference(measurements(4096, seed * 100 + 7)),
                 "boundary": reference(boundary_set(seed * 100 + 8))}
        rows = {"teachers": {k: scores(t, yy, t) for k, (_, yy, t) in tests.items()}}
        rows["teachers"]["packed_layer_bytes"] = sum(len(capture(layer, "fit")) for m in teachers for layer in (m.front, m.back))
        input_seed = seed * 100 + 6
        init_seed = seed * 100 + 4
        pool = torch.randn(4096, 12, generator=torch.Generator().manual_seed(input_seed))
        responses = query(pool)
        for n in (64, 512, 4096, "512_margin"):
            # All shapes here are multiples of the CPU RNG vector size. Verify the random prefixes.
            if n == "512_margin":
                # Keep 256 typical inputs, then 128 low-confidence examples per teacher.
                chosen = torch.zeros(len(pool), dtype=torch.bool)
                chosen[:256] = True
                for j in (0, 1):
                    uncertain = responses[:, j].abs().masked_fill(chosen, float("inf")).topk(128, largest=False).indices
                    chosen[uncertain] = True
                idx = chosen.nonzero().flatten()
                trace = write_trace(responses[idx], pool[idx], input_seed, init_seed, idx, len(pool))
            else:
                xx = torch.randn(n, 12, generator=torch.Generator().manual_seed(input_seed))
                assert torch.equal(xx, pool[:n])
                trace = write_trace(responses[:n], xx, input_seed, init_seed)
            capsule = args.out / f"{seed}-{n}.npz"
            capsule.write_bytes(trace)
            student = replay(capsule.read_bytes())
            with torch.no_grad():
                rows[n] = {k: scores(student(xx) > 0, yy, t) for k, (xx, yy, t) in tests.items()}
            rows[n]["trace_bytes"] = capsule.stat().st_size
            rows[n]["packed_layer_bytes"] = sum(len(capture(layer, "fit")) for layer in (student.front, student.back))
            print(seed, n, rows[n]["fresh"]["accuracy"], flush=True)
        out["per_seed"][seed] = rows
    (args.out / "results.json").write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    main()
