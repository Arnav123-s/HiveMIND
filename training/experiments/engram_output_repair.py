"""Repair a missing encoder by learning the output direction that its surviving head reads."""
import argparse
import io
import json
import time
from pathlib import Path

import numpy as np
import torch

from training.experiments.engram_cross_repair import RestoredHead, grade, grow, interface, repair, shared_part
from training.experiments.engram_distill import boundary_set
from training.experiments.engram_halves import DeployedLayer, FittedBitLinear, activation, capture, measurements


def features(wires, degree):
    if degree not in (1, 2):
        raise ValueError("unknown feature degree")
    terms = [torch.ones_like(wires[:, :1]), wires]
    if degree == 2:
        a, b = torch.triu_indices(wires.shape[1], wires.shape[1])
        terms.append(wires[:, a] * wires[:, b])
    return torch.cat(terms, 1)


def fit(wires, teacher_logits, degree):
    x = features(wires, degree).double()
    penalty = torch.eye(x.shape[1], dtype=x.dtype) * (0.02 * len(x))
    penalty[0, 0] = 0
    return torch.linalg.solve(x.T @ x + penalty, x.T @ teacher_logits.double()).half()


def readout(wires, coeff, degree):
    return features(wires, degree) @ coeff.float()


def sparse_models(wires, responses):
    """Matching pursuit over all individual channels and pairwise products, without task labels."""
    x = features(wires, 2).double()
    target = (responses.double() / 2).tanh()
    families = {}
    for bias in (False, True):
        selected = [0] if bias else []
        residual = target - (target.mean() if bias else 0)
        atoms = x[:, 1:] - (x[:, 1:].mean(0) if bias else 0)
        atoms = atoms / atoms.norm(dim=0).clamp_min(1e-8)
        for size in range(1, 13):
            preference = (atoms.T @ residual).abs()
            preference[[i - 1 for i in selected if i]] = -1
            selected.append(int(preference.argmax()) + 1)
            design = x[:, selected]
            coeff = torch.linalg.lstsq(design, target).solution
            residual = target - design @ coeff
            if size in (1, 2, 4, 6, 8, 12):
                families[(size, bias)] = torch.tensor(selected, dtype=torch.uint8), coeff.half()
    return families


def sparse_value(wires, indices, coeff):
    # Evaluate only the archived terms. Index 0 is a bias; the next twelve are raw
    # channels, followed by upper-triangular products in the same order as features().
    width = wires.shape[1]
    a, b = torch.triu_indices(width, width)
    terms = []
    for index in indices.tolist():
        if index == 0:
            term = torch.ones_like(wires[:, 0])
        elif index <= width:
            term = wires[:, index - 1]
        else:
            pair = index - width - 1
            term = wires[:, a[pair]] * wires[:, b[pair]]
        terms.append(term)
    return torch.stack(terms, 1) @ coeff.float()


def inject(head, value):
    """Write one coordinate so the immutable scalar head produces the recovered value."""
    if head.weight.shape[0] != 1:
        raise ValueError("repair requires a scalar output")
    j = int(head.weight[0].abs().argmax())
    gain = head.weight[0, j]
    if gain == 0:
        raise ValueError("surviving head has no active synapse")
    hidden = value.new_zeros((len(value), head.weight.shape[1]))
    hidden[:, j] = (value - head.bias[0]) / gain
    return head(hidden)[:, 0]


def pack(front, back, degree, coeff, indices=None):
    stream = io.BytesIO()
    extra = {"indices": indices.numpy()} if indices is not None else {}
    np.savez_compressed(stream, version=np.uint8(2 if extra else 1), front=np.frombuffer(front, np.uint8),
                        back=np.frombuffer(back, np.uint8), degree=np.uint8(degree), coeff=coeff.numpy(), **extra)
    return stream.getvalue()


def restore(data):
    with np.load(io.BytesIO(data), allow_pickle=False) as record:
        version = int(record["version"])
        if version not in (1, 2):
            raise ValueError("unknown output repair archive")
        front = DeployedLayer(record["front"].tobytes())
        head = DeployedLayer(record["back"].tobytes())
        degree, coeff = int(record["degree"]), torch.from_numpy(record["coeff"])
        indices = torch.from_numpy(record["indices"]) if version == 2 else None
    def predict(x):
        signals = activation(interface(front(x)))[:, :12]
        value = readout(signals, coeff, degree) if indices is None else sparse_value(signals, indices, coeff)
        return inject(head, value)
    return predict


def trial(seed, example):
    data, labels = measurements(8192, seed * 100 + 1)
    anchors, _ = measurements(512, seed * 100 + 2)
    fresh, truth = measurements(4096, seed * 100 + 3)
    hard, edge = boundary_set(seed * 100 + 4)
    samples = torch.cat([anchors, fresh, hard])
    cells = [grow(data, labels, job, True, seed) for job in (0, 1)]
    with torch.no_grad():
        intact = [cell(samples).detach() for cell in cells]
        fronts = [capture(cell.front, "fit") for cell in cells]
        backs = [capture(cell.back, "fit") for cell in cells]
    del cells
    rows = {}
    for j, name in enumerate(("balance", "polarity")):
        head = RestoredHead(backs[j])
        signals = activation(interface(DeployedLayer(fronts[1 - j])(samples)))
        old = intact[j]
        teacher = old[:512].half()
        def evaluate(pred):
            return {"fresh": grade(pred[512:4608], truth[:, j], old[512:4608] > 0),
                    "boundary": grade(pred[4608:], edge[:, j], old[4608:] > 0)}
        row = {"intact": evaluate(old)}
        start = time.perf_counter()
        inputs = shared_part(signals)
        bridge = repair(inputs[:512], teacher, head, seed * 100 + 40 + j)
        elapsed = time.perf_counter() - start
        layers = [layer for layer in bridge if isinstance(layer, FittedBitLinear)]
        with torch.no_grad():
            row["old_bridge"] = dict(**evaluate(head(bridge(inputs))[:, 0]), fit_s=elapsed,
                                     weights=sum(layer.weight.numel() for layer in layers),
                                     packed_layer_archive_bytes=sum(len(capture(layer, "fit")) for layer in layers))
        for source, wires in (("donor", signals[:, :12]), ("raw", activation(samples))):
            start = time.perf_counter()
            # Select the family on withheld public responses before refitting on all 512.
            validation = {}
            for d in (1, 2):
                coeff = fit(wires[:384], teacher[:384], d)
                z = readout(wires[384:512], coeff, d)
                validation[d] = int(((z > 0) == (teacher[384:] > 0)).sum())
            chosen = max(validation, key=validation.get)
            coeff = fit(wires[:512], teacher, chosen)
            fit_s = time.perf_counter() - start
            value = readout(wires, coeff, chosen)
            predicted = inject(head, value)
            row[source] = dict(**evaluate(predicted), degree=chosen, validation=validation, fit_s=fit_s,
                               coeff_bytes=coeff.element_size() * coeff.numel(), coefficients=coeff.numel(),
                               max_injection_error=float((predicted - value).abs().max()))
            for d in (1, 2):
                fixed = fit(wires[:512], teacher, d)
                row[source][f"degree_{d}"] = evaluate(inject(head, readout(wires, fixed, d)))
            if source == "donor":
                archive = pack(fronts[1 - j], backs[j], chosen, coeff)
                row[source]["complete_archive_bytes"] = len(archive)
                row[source]["front_bytes"], row[source]["back_bytes"] = len(fronts[1 - j]), len(backs[j])
                torch.testing.assert_close(restore(archive)(samples), predicted, rtol=0, atol=0)
            start = time.perf_counter()
            candidates = sparse_models(wires[:384], teacher[:384])
            def quality(key):
                support, coef = candidates[key]
                logits = sparse_value(wires[384:512], support, coef)
                return int(((logits > 0) == (teacher[384:] > 0)).sum()), -len(coef)
            best = max(candidates, key=quality)
            support, coef = sparse_models(wires[:512], teacher)[best]
            elapsed = time.perf_counter() - start
            value = sparse_value(wires, support, coef)
            pred = inject(head, value)
            sparse = dict(**evaluate(pred), fit_s=elapsed, selected=list(best), indices=support.tolist(),
                          coefficients=len(coef), coeff_and_index_bytes=3 * len(coef),
                          max_injection_error=float((pred - value).abs().max()))
            if source == "donor":
                archive = pack(fronts[1 - j], backs[j], 2, coef, support)
                sparse["complete_archive_bytes"] = len(archive)
                torch.testing.assert_close(restore(archive)(samples), pred, rtol=0, atol=0)
                if example and j == 1:
                    example.write_bytes(archive)
            row[source + "_sparse"] = sparse
        rows[name] = row
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--example", type=Path)
    parser.add_argument("--seeds", type=int, nargs="+", default=[263, 277, 293, 307, 331])
    args = parser.parse_args()
    torch.set_num_threads(1)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.example:
        args.example.parent.mkdir(parents=True, exist_ok=True)
    rows = {}
    for seed in args.seeds:
        rows[seed] = trial(seed, args.example if seed == args.seeds[0] else None)
        print(seed, {k: v["donor"]["fresh"] for k, v in rows[seed].items()}, flush=True)
    args.out.write_text(json.dumps({"seeds": args.seeds, "probes": 512, "per_seed": rows}, indent=2) + "\n")


if __name__ == "__main__":
    main()
