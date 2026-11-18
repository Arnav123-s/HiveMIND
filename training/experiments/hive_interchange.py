"""Causally swap a cell signal and progressively reveal bits until the receiver's answer is fixed."""
import argparse
import json
from pathlib import Path

import torch

from training.experiments.hive_signals import FRAME, observations, scores, train


def decision_grid(reader):
    axis = torch.arange(256) * (2 / 255) - 1
    pairs = torch.cartesian_prod(axis, axis)
    flags = reader(pairs) > 0
    return (flags[:, 0].byte() + 2 * flags[:, 1].byte()).reshape(256, 256)


def bit_budget(grid):
    # A block of codes with the same leading bits certifies a decision iff all entries agree.
    required = torch.full_like(grid, 8)
    for bits in (6, 4, 2):
        size = 256 >> bits
        blocks = grid.view(1 << bits, size, 1 << bits, size)
        low, high = blocks.amin((1, 3)), blocks.amax((1, 3))
        settled = (low == high).repeat_interleave(size, 0).repeat_interleave(size, 1)
        required[settled] = bits
    return required


def decode(grid, codes):
    packed = grid[codes[:, 0], codes[:, 1]]
    return torch.stack([packed.bitwise_and(1).bool(), packed.bitwise_and(2).bool()], 1)


def prefix_center(codes, bits):
    span = 2 ** (8 - bits)
    return codes // span * span + (span - 1) // 2


@torch.no_grad()
def audit(pair, seed):
    x, truth, local = observations(4096, seed * 100 + 3)
    def encode_inputs(value):
        return ((torch.cat(pair.wires(value), 1) + 1) * 127.5).round().long()
    code = encode_inputs(x)
    grid = decision_grid(pair.reader)
    needed = bit_budget(grid)
    bits = needed[code[:, 0], code[:, 1]]
    full = decode(grid, code)
    if not torch.equal(full, pair(x) > 0):
        raise RuntimeError("code grid disagrees with running components")
    # Verify every possible code pair, including values absent from the sampled conversations.
    all_codes = torch.cartesian_prod(torch.arange(256), torch.arange(256))
    steps = needed.flatten().long()
    center = prefix_center(all_codes, steps[:, None])
    if not torch.equal(decode(grid, all_codes), decode(grid, center)):
        raise RuntimeError("early exit changed a decision")
    idx = torch.roll(torch.arange(len(x)), 103)
    mixed_code = torch.stack([code[idx, 0], code[:, 1]], 1)
    mixed = torch.cat([x[idx, :4], x[:, 4:]], 1)
    a, b = local[idx, 0], local[:, 1]
    counterfactual = torch.stack([(a > 0) != (b > 0), a + b > 0], 1)
    after_swap = decode(grid, mixed_code)
    if not torch.equal(after_swap, pair(mixed) > 0):
        raise RuntimeError("interchange disagrees with substituting the whole input")
    muted_code = code.clone()
    muted_code[:, 0] = 128
    changes = (counterfactual != truth).any(1)
    rounds = bits.float().mean().item() / 2
    return {"intact": scores(full, truth), "interchange": scores(after_swap, counterfactual),
            "ignore_swap": scores(full, counterfactual),
            "interchange_on_changed_cases": scores(after_swap[changes], counterfactual[changes]),
            "ignore_on_changed_cases": scores(full[changes], counterfactual[changes]),
            "mute_one_sender": scores(decode(grid, muted_code), truth), "changed_cases": int(changes.sum()),
            "fixed_prefix": {b: scores(decode(grid, prefix_center(code, b)), truth) for b in (2, 4, 6, 8)},
            "adaptive_bits_both_senders": 2 * bits.float().mean().item(), "mean_rounds": rounds,
            "responses_bytes_if_framed_separately": 2 * FRAME.size * rounds,
            "bytes_including_individual_refinement_requests": 2 * FRAME.size * (2 * rounds - 1),
            "exhaustive_code_pairs": len(all_codes), "all_decisions_preserved": True,
            "receiver_table_uint8_bytes": grid.numel(), "prefix_depth_uint8_bytes": needed.numel()}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    torch.set_num_threads(1)
    result = {}
    for seed in (479, 487, 503, 521, 541):
        x, y, _ = observations(8192, seed * 100 + 1)
        result[seed] = audit(train(seed, 8, x, y), seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
