"""Learn a finite communication channel between cells with disjoint observations."""
import argparse
import json
import struct
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from training.experiments.engram_halves import DeployedLayer, FittedBitLinear, capture, fraction


FRAME = struct.Struct("!IHHBB")  # task id, sender, schema version, role, unsigned code
SEEDS = (197, 211, 223, 239, 251)


def observations(count, seed):
    x = torch.randn(count, 8, generator=torch.Generator().manual_seed(seed))
    a, b = x[:, 0] + x[:, 1] - x[:, 2], x[:, 4] - x[:, 5] + x[:, 6]
    truth = torch.stack([(a > 0) != (b > 0), a + b > 0], 1)
    return x, truth, torch.stack([a, b], 1)


def grid(x, bits):
    if bits == 0:
        return x
    steps = 2**bits - 1
    return ((x.clamp(-1, 1) + 1) * (steps / 2)).round() * (2 / steps) - 1


class Pair(nn.Module):
    def __init__(self, bits):
        super().__init__()
        self.bits = bits
        self.a = FittedBitLinear(4, 1, "fit")
        self.b = FittedBitLinear(4, 1, "fit")
        self.reader = nn.Sequential(nn.Linear(2, 24), nn.Tanh(), nn.Linear(24, 2))

    def signal(self, emitter, x):
        h = emitter(x).tanh()
        return h + (grid(h, self.bits) - h).detach()

    def wires(self, x):
        return self.signal(self.a, x[:, :4]), self.signal(self.b, x[:, 4:])

    def forward(self, x):
        return self.reader(torch.cat(self.wires(x), 1))


def train(seed, kind, x, y):
    torch.manual_seed(seed * 1000)
    paired = isinstance(kind, int)
    if paired:
        model = Pair(kind)
    else:
        if kind == "single":
            x = x[:, :4]
        model = nn.Sequential(nn.Linear(x.shape[1], 32), nn.Tanh(), nn.Linear(32, 2))
    opt = torch.optim.AdamW(model.parameters(), lr=0.016, weight_decay=0.001)
    batches = torch.Generator().manual_seed(seed * 1000 + 1)
    for _ in range(650):
        ids = torch.randint(len(x), (160,), generator=batches)
        opt.zero_grad(set_to_none=True)
        loss = F.binary_cross_entropy_with_logits(model(x[ids]), y[ids].float())
        loss.backward()
        opt.step()
    return model.eval()


def scores(pred, truth):
    good = pred == truth
    return {"opposite_signs": fraction(good[:, 0]), "positive_sum": fraction(good[:, 1]), "both": fraction(good.all(1))}


def receive(frame, task, sender, version, role):
    if len(frame) != FRAME.size:
        return None
    tid, source, schema, kind, code = FRAME.unpack(frame)
    if (tid, source, schema, kind) != (task, sender, version, role) or code > 15:
        return None
    return code


def save_pair(model, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    weights = {name: value.detach().numpy() for name, value in model.reader.state_dict().items()}
    with path.open("wb") as f:
        np.savez_compressed(f, format=np.int32(1), left=np.frombuffer(capture(model.a, "fit"), np.uint8),
                            right=np.frombuffer(capture(model.b, "fit"), np.uint8), **weights)


def load_sender(path, role):
    if role not in (0, 1):
        raise ValueError("unknown sender role")
    with np.load(path, allow_pickle=False) as record:
        if int(record["format"]) != 1:
            raise ValueError("unknown signal protocol")
        return DeployedLayer(record[("left", "right")[role]].tobytes())


def load_reader(path):
    with np.load(path, allow_pickle=False) as record:
        if int(record["format"]) != 1:
            raise ValueError("unknown signal protocol")
        reader = nn.Sequential(nn.Linear(2, 24), nn.Tanh(), nn.Linear(24, 2))
        reader.load_state_dict({k: torch.from_numpy(record[k]) for k in reader.state_dict()})
        return reader.eval()


@torch.no_grad()
def emit(sender, role, task, observations):
    values = torch.as_tensor(observations, dtype=torch.float32).reshape(1, 4)
    code = int(((sender(values).tanh() + 1) * 7.5).round().item())
    return FRAME.pack(task, 6 + role, 1, role, code)


@torch.no_grad()
def interpret(reader, task, frames):
    codes = {}
    for frame in frames:
        if len(frame) != FRAME.size:
            continue
        role = FRAME.unpack(frame)[3]
        code = receive(frame, task, 6 + role, 1, role)
        if role in (0, 1) and code is not None:
            if role in codes and code != codes[role]:
                raise ValueError("conflicting signals for this task and role")
            codes[role] = code
    if len(codes) < 2:
        return None
    wires = torch.tensor([[codes[0], codes[1]]]) * (2 / 15) - 1
    return (reader(wires)[0] > 0).tolist()


@torch.no_grad()
def communication(model, foreign, seed):
    x, truth, _ = observations(4096, seed * 100 + 3)
    a, b = model.wires(x)
    def predict(signal):
        return model.reader(torch.cat([a, signal], 1)) > 0
    ideal = predict(b)
    other = foreign.signal(foreign.b, x[:, 4:])
    anchors, _, _ = observations(64, seed * 100 + 2)
    own_anchor = model.signal(model.b, anchors[:, 4:])
    peer_anchor = foreign.signal(foreign.b, anchors[:, 4:])
    design = torch.cat([peer_anchor, torch.ones_like(peer_anchor)], 1).double()
    slope, offset = torch.linalg.lstsq(design, own_anchor.double()).solution.float()
    aligned = grid(other * slope + offset, 4)
    # Change the foreign dialect without damaging its own task behavior: invert
    # its B channel and the B column of the first receiving layer together.
    partner_a, partner_b = foreign.wires(x)
    flipped = torch.cat([partner_a, -partner_b], 1)
    changed_weight = foreign.reader[0].weight * torch.tensor([1., -1.])
    changed_logits = foreign.reader[2](F.linear(flipped, changed_weight, foreign.reader[0].bias).tanh())
    assert torch.equal(changed_logits > 0, foreign(x) > 0)
    opposite_design = torch.cat([-peer_anchor, torch.ones_like(peer_anchor)], 1).double()
    opposite_slope, opposite_offset = torch.linalg.lstsq(opposite_design, own_anchor.double()).solution.float()
    repaired_dialect = grid(-other * opposite_slope + opposite_offset, 4)
    original_codes = ((b[:, 0] + 1) * 7.5).round().long().tolist()
    unchecked, checked, rejected = [], [], []
    for task, code in enumerate(original_codes):
        frame = FRAME.pack(task, 7, 1, 1, code)
        if task % 16 == 0:
            old = (task - 1) % len(x)
            frame = FRAME.pack(old, 7, 1, 1, original_codes[old])
        elif task % 16 == 8:
            frame = FRAME.pack(task, 7, 2, 1, 15 - code)
        unchecked.append(FRAME.unpack(frame)[-1])
        accepted = receive(frame, task, 7, 1, 1)
        rejected.append(accepted is None)
        if accepted is None:
            accepted = receive(FRAME.pack(task, 7, 1, 1, code), task, 7, 1, 1)
        checked.append(accepted)
    def unpack(codes):
        return torch.tensor(codes)[:, None] * (2 / 15) - 1
    verified = predict(unpack(checked))
    assert torch.equal(verified, ideal)
    mask = ~torch.tensor(rejected)
    return {"matched": scores(ideal, truth), "foreign": scores(predict(other), truth),
            "aligned": scores(predict(aligned), truth), "alignment_slope": slope.item(),
            "equivalent_opposite_dialect": scores(predict(-other), truth),
            "translated_opposite_dialect": scores(predict(repaired_dialect), truth),
            "wrong_task_or_schema_unchecked": scores(predict(unpack(unchecked)), truth),
            "checked_with_retry": scores(verified, truth), "rejected_attempts": sum(rejected),
            "requests": len(x), "no_retry_coverage": fraction(mask),
            "no_retry_both_correct_all_requests": fraction((ideal == truth).all(1) & mask)}


def hops(a, b):
    steps = 0
    while a != b:
        steps += 2
        a, b = a // 4, b // 4
    return steps


def subhives():
    out = {}
    for size in (16, 64, 256, 1024):
        group = size // 4
        edges = (4 * size - 4) // 3
        meters = {"broadcast": [], "global_addresses": [], "local_replicas": []}
        under_outage = {"broadcast": 0, "global_addresses": 0, "local_replicas": 0}
        for origin in range(size):
            local = (origin // group) * group
            primary, replicas = (0, size // 2 + 1), (local, local + 1)
            global_hops = sum(hops(origin, t) for t in primary)
            meters["broadcast"].append(edges + global_hops)
            meters["global_addresses"].append(2 * global_hops)
            meters["local_replicas"].append(2 * sum(hops(origin, t) for t in replicas))
            for name, targets in (("global_addresses", primary), ("broadcast", primary), ("local_replicas", replicas)):
                under_outage[name] += all(t // group == origin // group for t in targets)
        out[size] = {"mean_directed_link_transmissions": {k: sum(v) / size for k, v in meters.items()},
                     "root_outage_reachable_fraction": {k: v / size for k, v in under_outage.items()},
                     "primary_worker_instances": 2, "replicated_worker_instances": 8, "max_router_neighbors": 5}
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--example", type=Path, help="save the first four-bit pair for separate senders and a reader")
    args = p.parse_args()
    torch.set_num_threads(1)
    out = {"seeds": SEEDS, "training_per_seed": 8192, "exam_per_seed": 4096, "alignment_anchors": 64,
           "frame_bytes": FRAME.size, "per_seed": {}, "subhives": subhives()}
    four = []
    for seed in SEEDS:
        xx, yy, _ = observations(8192, seed * 100 + 1)
        x, truth, local = observations(4096, seed * 100 + 3)
        rows = {}
        for kind in ("single", "central", 1, 2, 4, 8, 0):
            model = train(seed, kind, xx, yy)
            with torch.no_grad():
                rows["float" if kind == 0 else str(kind)] = scores(model(x[:, :4] if kind == "single" else x) > 0, truth)
            if kind == 4:
                four.append(model)
                if args.example is not None and seed == SEEDS[0]:
                    save_pair(model, args.example)
                    senders = [load_sender(args.example, j) for j in (0, 1)]
                    reader = load_reader(args.example)
                    with torch.no_grad():
                        expected = (model(x[:128]) > 0).tolist()
                    for i, row in enumerate(x[:128]):
                        frames = [emit(s, j, i, row[j * 4:(j + 1) * 4]) for j, s in enumerate(senders)]
                        assert interpret(reader, i, frames[::-1]) == expected[i]
        for bits in (1, 4):
            signals = grid((local / 2).tanh(), bits)
            pred = torch.stack([(signals[:, 0] > 0) != (signals[:, 1] > 0), signals.sum(1) > 0], 1)
            rows[f"known_rule_{bits}"] = scores(pred, truth)
        out["per_seed"][seed] = {"width": rows}
        print(seed, rows["4"], flush=True)
    for i, seed in enumerate(SEEDS):
        out["per_seed"][seed]["communication"] = communication(four[i], four[(i + 1) % len(four)], seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    main()
