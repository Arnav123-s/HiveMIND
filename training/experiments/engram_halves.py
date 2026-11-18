"""Test ternary synapses, two different cells in one body, and cross-cell repairs on CPU."""
import argparse
import io
import json
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from training.scratch import BitLinear


def quantized_weight(w, method):
    rows = w if method == "rowfit" else w.reshape(1, -1)
    mag = rows.abs()
    scale = mag.mean(1, keepdim=True).clamp_min(1e-5)
    if method == "absmean":
        codes = (rows / scale).round().clamp(-1, 1)
    else:
        for _ in range(5):
            kept = mag > scale * 0.5
            scale = (mag * kept).sum(1, keepdim=True) / kept.sum(1, keepdim=True).clamp_min(1)
        codes = rows.sign() * (mag > scale * 0.5)
    return codes.reshape_as(w), scale.flatten()


def activation(x):
    top = x.abs().amax(-1, keepdim=True).clamp_min(1e-5)
    return (x * 127 / top).round().clamp(-128, 127) * top / 127


class FittedBitLinear(BitLinear):
    def __init__(self, nin, nout, method):
        super().__init__(nin, nout)
        self.method = method

    def forward(self, x):
        with torch.no_grad():
            codes, scale = quantized_weight(self.weight, self.method)
            rounded = codes * scale[:, None]
            ax = activation(x)
        w = self.weight + (rounded - self.weight).detach()
        return F.linear(x + (ax - x).detach(), w, self.bias)


class Cell(nn.Module):
    def __init__(self, width, method):
        super().__init__()
        def layer(nin, nout):
            return BitLinear(nin, nout) if method == "absmean" else FittedBitLinear(nin, nout, method)
        self.front, self.back = layer(12, width), layer(width, 1)

    def forward(self, x):
        return self.back(self.front(x).relu())[:, 0]


def measurements(count, seed):
    x = torch.randn(count, 12, generator=torch.Generator().manual_seed(seed))
    # Two independent needs of the same body. Both labels always exist for a sample.
    balance = x[:, :3].sum(1) > x[:, 3:6].sum(1)
    disagreement = (x[:, 6] > 0) != (x[:, 7] > 0)
    return x, torch.stack([balance, disagreement], dim=1)


def train(x, labels, task, method, seed):
    # Separate initial networks and batch streams for the two jobs, paired across quantizers.
    torch.manual_seed(1000 * seed + task)
    m = Cell((24, 40)[task], method)
    opt = torch.optim.AdamW(m.parameters(), lr=0.008, weight_decay=0.005)
    batches = torch.Generator().manual_seed(4000 * seed + task)
    for _ in range(400):
        idx = torch.randint(len(x), (128,), generator=batches)
        opt.zero_grad(set_to_none=True)
        loss = F.binary_cross_entropy_with_logits(m(x[idx]), labels[idx, task].float())
        loss.backward()
        opt.step()
    return m.eval()


@torch.no_grad()
def capture(layer, method):
    codes, scale = quantized_weight(layer.weight, method)
    buf = io.BytesIO()
    np.savez_compressed(buf, shape=np.array(codes.shape), plus=np.packbits(codes.numpy() > 0),
                        minus=np.packbits(codes.numpy() < 0), scale=scale.numpy(), bias=layer.bias.numpy())
    return buf.getvalue()


class DeployedLayer(nn.Module):
    """Read the deployable layer from its two sign planes, scales and bias."""
    def __init__(self, capsule):
        super().__init__()
        with np.load(io.BytesIO(capsule), allow_pickle=False) as p:
            shape = tuple(p["shape"])
            n = int(np.prod(shape))
            codes = np.unpackbits(p["plus"], count=n).astype("int8") - np.unpackbits(p["minus"], count=n).astype("int8")
            self.register_buffer("weight", torch.from_numpy(codes.reshape(shape) * p["scale"][:, None]))
            self.register_buffer("bias", torch.from_numpy(p["bias"]))

    def forward(self, x):
        return F.linear(activation(x), self.weight, self.bias)


def fraction(mask):
    return mask.double().mean().item()


def cross_repair(source, target, x, y, anchors):
    src, dst = source.front(x).relu(), target.front(x).relu()
    src_anchor, dst_anchor = source.front(anchors).relu(), target.front(anchors).relu()
    # Directly connect the first matching wires, padding or cutting to the target's width.
    wired = F.pad(src, (0, dst.shape[1] - src.shape[1]))
    feat = torch.cat([src_anchor, torch.ones(len(anchors), 1)], 1).double()
    # The donor and recipient both run on 512 calibration inputs. No labels or exam inputs enter the fit.
    ridge = torch.eye(feat.shape[1], dtype=torch.float64) * 1e-3
    bridge = torch.linalg.solve(feat.T @ feat + ridge, feat.T @ dst_anchor.double()).float()
    aligned = src @ bridge[:-1] + bridge[-1]
    def score(h):
        pred = target.back(h)[:, 0] > 0
        return {"accuracy": fraction(pred == y), "agreement_with_intact": fraction(pred == (target.back(dst)[:, 0] > 0))}
    return {"wired": score(wired), "bridge": score(aligned), "intact": score(dst),
            "bridge_fp32_bytes": bridge.numel() * bridge.element_size()}


@torch.no_grad()
def surgery(cells, x, labels, anchors, seed, method):
    original = torch.stack([cell(x) > 0 for cell in cells], 1)
    capsules = [{part: capture(getattr(cell, part), method) for part in ("front", "back")} for cell in cells]
    for cell, parts in zip(cells, capsules):
        cell.front, cell.back = DeployedLayer(parts["front"]), DeployedLayer(parts["back"])
    # Remove A's front and B's back. Each body keeps just its other live half.
    before = torch.stack([cell(x) for cell in cells], 1)
    del cells[0].front, cells[1].back
    cells[0].front = DeployedLayer(capsules[0]["front"])
    cells[1].back = DeployedLayer(capsules[1]["back"])
    restored = torch.stack([cell(x) for cell in cells], 1)
    assert torch.equal(before, restored)
    pred = restored > 0
    # The caller supplies the requested job as one bit; execute only that cell.
    jobs = torch.arange(len(x)) % 2
    routed = torch.zeros(len(x), dtype=torch.bool)
    for job, cell in enumerate(cells):
        mask = jobs == job
        routed[mask] = cell(x[mask]) > 0
    a = cells[0]
    h = a.front(x).relu()
    perm = torch.randperm(h.shape[1], generator=torch.Generator().manual_seed(seed))
    # This is the *same* encoder with its neurons in a different order.
    permuted = h[:, perm]
    restored_order = permuted[:, torch.argsort(perm)]
    assert torch.equal(a.back(restored_order), a.back(h))
    return {"accuracy": [fraction(pred[:, j] == labels[:, j]) for j in range(2)],
            "capsule_bytes": [{k: len(v) for k, v in parts.items()} for parts in capsules],
            "repaired_logit_max_error": (before - restored).abs().max().item(),
            "trained_to_deployed_decision_agreement": fraction(original == pred),
            "explicit_route_accuracy": fraction(routed == labels[torch.arange(len(x)), jobs]),
            "both_decisions_correct": fraction((pred == labels).all(1)),
            "no_cue_equal_job_accuracy_ceiling": 1. - fraction(labels[:, 0] != labels[:, 1]) / 2,
            "permuted_wires_A_accuracy": fraction((a.back(permuted)[:, 0] > 0) == labels[:, 0]),
            "aligned_wires_A_accuracy": fraction((a.back(restored_order)[:, 0] > 0) == labels[:, 0]),
            "A_front_B_back": cross_repair(cells[0], cells[1], x, labels[:, 1], anchors),
            "B_front_A_back": cross_repair(cells[1], cells[0], x, labels[:, 0], anchors)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    torch.set_num_threads(1)
    seeds = (17, 29, 43, 59, 71)
    out = {"seeds": seeds, "per_seed": {}, "train_per_seed": 8192, "anchors_per_seed": 512,
           "test_per_seed": 4096, "steps": 400, "widths": [24, 40], "activation_bits": 8}
    for seed in seeds:
        train_x, train_y = measurements(8192, seed * 100 + 1)
        anchors, _ = measurements(512, seed * 100 + 2)
        test_x, test_y = measurements(4096, seed * 100 + 3)
        out["per_seed"][seed] = {}
        for method in ("absmean", "fit", "rowfit"):
            cells = [train(train_x, train_y, task, method, seed) for task in (0, 1)]
            row = surgery(cells, test_x, test_y, anchors, seed, method)
            out["per_seed"][seed][method] = row
            print(seed, method, row["accuracy"], flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    main()
