"""Rebuild a missing encoder using a foreign encoder, the surviving head and saved output examples."""
import argparse
import hashlib
import io
import json
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from training.experiments.engram_distill import boundary_set
from training.experiments.engram_halves import Cell, DeployedLayer, FittedBitLinear, activation, capture, fraction, measurements


def interface(wires):
    return torch.cat([wires[:, :12], wires[:, 12:].relu()], 1)


class WireCell(Cell):
    def features(self, x):
        return interface(self.front(x))

    def forward(self, x):
        return self.back(self.features(x))[:, 0]


def grow(x, y, job, common, seed):
    torch.manual_seed(seed * 1000 + job)
    cell = WireCell((24, 40)[job], "fit")
    opt = torch.optim.AdamW(cell.parameters(), lr=0.008, weight_decay=0.005)
    batches = torch.Generator().manual_seed(seed * 4000 + job)
    for _ in range(400):
        idx = torch.randint(len(x), (128,), generator=batches)
        xx = x[idx]
        features = cell.features(xx)
        loss = F.binary_cross_entropy_with_logits(cell.back(features)[:, 0], y[idx, job].float())
        if common:
            # Both cells learn to communicate the same twelve sensor readings in the
            # same wire positions. The auxiliary target is independent of either job.
            loss = loss + F.mse_loss(features[:, :12], xx)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
    return cell.eval()


class RestoredHead(DeployedLayer):
    def forward(self, x):
        # Keep the last layer's deployed weights fixed. Pass a gradient through
        # activation rounding so a new upstream connector can learn.
        rounded = x + (activation(x) - x).detach()
        return F.linear(rounded, self.weight, self.bias)


def repair(examples, old_logits, head, seed):
    # No recipient encoder or original labels are available here. The fixed last
    # layer is the surviving half of the damaged recipient.
    torch.manual_seed(seed)
    bridge = nn.Sequential(FittedBitLinear(examples.shape[1], 16, "fit"), nn.ReLU(),
                           FittedBitLinear(16, head.weight.shape[1], "fit"))
    opt = torch.optim.AdamW(bridge.parameters(), lr=0.008, weight_decay=0.005)
    batches = torch.Generator().manual_seed(seed + 1)
    target = (old_logits.float() / 2).sigmoid()
    for _ in range(300):
        idx = torch.randint(len(examples), (128,), generator=batches)
        estimate = head(bridge(examples[idx]))[:, 0]
        loss = F.binary_cross_entropy_with_logits(estimate / 2, target[idx]) * 4
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
    return bridge.eval()


def grade(logits, truth, reference):
    return {"accuracy": fraction((logits > 0) == truth), "intact_agreement": fraction((logits > 0) == reference)}


class Hybrid(nn.Module):
    def __init__(self, front, bridge, back, public_only):
        super().__init__()
        self.front, self.bridge, self.back = front, bridge, back
        self.public_only = public_only

    def forward(self, x):
        wire = activation(interface(self.front(x)))
        if self.public_only:
            wire = shared_part(wire)
        return self.back(self.bridge(wire))[:, 0]


def shared_part(wires):
    return F.pad(wires[:, :12], (0, wires.shape[1] - 12))


def regrow(capsule):
    """Rebuild the hybrid from its two different parents' parts and the recipient's output memory."""
    with np.load(io.BytesIO(capsule), allow_pickle=False) as record:
        if int(record["format"]) != 1:
            raise ValueError("unknown half-repair record")
        front = DeployedLayer(record["foreign_front"].tobytes())
        back = RestoredHead(record["recipient_back"].tobytes())
        logits = torch.from_numpy(record["logits"])
        anchor, _ = measurements(len(logits), int(record["input_seed"]))
        if hashlib.sha256(anchor.numpy().tobytes()).hexdigest() != str(record["inputs_sha256"]):
            raise ValueError("input generator disagrees with the recorded probes")
        bridge_seed = int(record["bridge_seed"])
        public_only = bool(record["public_only"]) if "public_only" in record else False
    wires = activation(interface(front(anchor)))
    bridge = repair(shared_part(wires) if public_only else wires, logits, back, bridge_seed)
    return Hybrid(front, bridge, back, public_only).eval()


def trial(seed, common, example=None):
    x, labels = measurements(8192, seed * 100 + 1)
    anchor, _ = measurements(512, seed * 100 + 2)
    test, truth = measurements(4096, seed * 100 + 3)
    hard, edge = boundary_set(seed * 100 + 4)
    samples = torch.cat([anchor, test, hard])
    cells = [grow(x, labels, j, common, seed) for j in (0, 1)]
    with torch.no_grad():
        # Take inventories before the loss. Only the first 512 target responses
        # are made available for fitting. The other responses are for scoring.
        inventory = [c(samples) for c in cells]
        fronts = [capture(c.front, "fit") for c in cells]
        backs = [capture(c.back, "fit") for c in cells]
    del cells
    rows = {}
    for j, job in enumerate(("recover_A", "recover_B")):
        # Regrow a front half from one cell's record and a back half from another's.
        # This repair never receives the missing recipient's hidden activations.
        donor_half = DeployedLayer(fronts[1 - j])
        donor = activation(interface(donor_half(samples)))
        head = RestoredHead(backs[j])
        old = inventory[j]
        keys = (("fresh", slice(512, 4608), truth[:, j]), ("boundary", slice(4608, None), edge[:, j]))
        def scores(logits):
            return {key: grade(logits[idx], y, old[idx] > 0) for key, idx, y in keys}
        cut = F.pad(donor, (0, head.weight.shape[1] - donor.shape[1]))
        rows[job] = {"intact": scores(old), "direct_wire": scores(head(cut)[:, 0]),
                     "donor_front_archive_bytes": len(fronts[1 - j]), "recipient_back_archive_bytes": len(backs[j]),
                     "donor_public_wires_rmse": (donor[512:4608, :12] - test).square().mean().sqrt().item()}
        raw = F.pad(activation(samples), (0, donor.shape[1] - 12))
        common_only = shared_part(donor)
        bridge_seed = seed * 100 + 40 + j
        for name, available in (("foreign_features", donor), ("first_12_only", common_only), ("raw_control", raw)):
            bridge = repair(available[:512], old[:512].to(torch.float16), head, bridge_seed)
            with torch.no_grad():
                rows[job][name] = scores(head(bridge(available))[:, 0])
            rows[job][name]["learned_bridge_weights"] = sum(m.weight.numel() for m in bridge if isinstance(m, FittedBitLinear))
        if example is not None and j == 1:
            # A's encoder, B's decoder, and enough public observations of B to fit the missing connection.
            example.parent.mkdir(parents=True, exist_ok=True)
            with example.open("wb") as stream:
                np.savez_compressed(stream, format=np.int32(1), torch_version=np.array(str(torch.__version__)),
                                    foreign_front=np.frombuffer(fronts[0], np.uint8), recipient_back=np.frombuffer(backs[1], np.uint8),
                                    logits=old[:512].half().numpy(), input_seed=np.int64(seed * 100 + 2),
                                    inputs_sha256=np.array(hashlib.sha256(anchor.numpy().tobytes()).hexdigest()),
                                    bridge_seed=np.int64(bridge_seed), public_only=np.bool_(True))
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--example", type=Path, help="save the common-interface A-front/B-back example from seed 73")
    p.add_argument("--seeds", type=int, nargs="+", default=[73, 89, 101, 113, 127])
    args = p.parse_args()
    torch.set_num_threads(1)
    rows = {"seeds": args.seeds, "anchor_count": 512, "fresh_count_per_seed": 4096,
            "boundary_count_per_seed": 4096, "torch": str(torch.__version__), "per_seed": {}}
    for seed in rows["seeds"]:
        rows["per_seed"][seed] = {}
        for name in ("private", "common"):
            row = trial(seed, name == "common", args.example if seed == 73 and name == "common" else None)
            rows["per_seed"][seed][name] = row
            print(seed, name, [round(v["foreign_features"]["fresh"]["accuracy"], 4) for v in row.values()], flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(rows, indent=2) + "\n")


if __name__ == "__main__":
    main()
