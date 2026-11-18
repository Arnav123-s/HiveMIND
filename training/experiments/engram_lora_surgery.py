"""Measure weight-space composition on real GGUF LoRAs without materializing giant weight matrices."""
import argparse
import json
import shutil
from pathlib import Path

import numpy as np

from training.experiments.engram_regrow import GGUFReader, digest


def energy(b, a):
    # Squared Frobenius norm of b @ a using only rank-by-rank Gram matrices.
    return max(0., float(np.sum((b.T @ b) * (a @ a.T))))


def compose(a, b, c, d, rank):
    """Return a balanced rank-limited approximation of the mean effective maps."""
    qb, rb = np.linalg.qr(np.concatenate([b, d], 1) * 0.5)
    qa, ra = np.linalg.qr(np.concatenate([a, c], 0).T)
    u, s, vh = np.linalg.svd(rb @ ra.T, full_matrices=False)
    root = np.sqrt(s[:rank])
    return root[:, None] * (vh[:rank] @ qa.T), (qb @ u[:, :rank]) * root


def build_pair(left, right, dest):
    # Each destination has its own GGUF backing file. The inherited header describes
    # the same shape/rank; the manifest records the two actual ancestors and new hashes.
    dest.mkdir(parents=True, exist_ok=False)
    src = [GGUFReader(p) for p in (left, right)]
    if src[0].fields["adapter.lora.alpha"].contents() != src[1].fields["adapter.lora.alpha"].contents():
        raise ValueError("different parent scales")
    parents = [{t.name: t.data for t in reader.tensors} for reader in src]
    if parents[0].keys() != parents[1].keys():
        raise ValueError("different parent layouts")
    for label, path in (("child", left), ("words", right)):
        (dest / (label + ".gguf")).symlink_to(path.resolve(strict=True))
    files = [dest / f"{tag}.gguf" for tag in ("factor_mean", "effective_svd")]
    for file in files:
        shutil.copyfile(left, file)
    writers = [GGUFReader(file, "r+") for file in files]
    slots = [{t.name: t.data for t in r.tensors} for r in writers]
    for key in sorted(n for n in parents[0] if n.endswith(".lora_a")):
        back = key[:-1] + "b"
        a, b = (parents[0][k].astype("float64") for k in (key, back))
        c, d = (parents[1][k].astype("float64") for k in (key, back))
        if a.shape != c.shape or b.shape != d.shape:
            raise ValueError("incompatible parent widths")
        for tensors, pair in zip(slots, (((a + c) / 2, (b + d) / 2), compose(a, b, c, d, len(a)))):
            tensors[key][:] = pair[0]
            tensors[back][:] = pair[1]
    for writer in writers:
        writer.data.flush()
    (dest / "manifest.json").write_text(json.dumps({p.name: digest(p) for p in (left, right, *files)}, indent=2) + "\n")


def measure(left, right):
    l, r = GGUFReader(left), GGUFReader(right)
    def factors(reader):
        return {t.name: t.data for t in reader.tensors}
    lf, rf = factors(l), factors(r)
    if lf.keys() != rf.keys() or l.fields["adapter.lora.alpha"].contents() != r.fields["adapter.lora.alpha"].contents():
        raise ValueError("need matching tensor names and LoRA scaling")
    out = []
    for name in sorted(n for n in lf if n.endswith(".lora_a")):
        back = name[:-1] + "b"
        a, b = lf[name].astype("float64"), lf[back].astype("float64")
        c, d = rf[name].astype("float64"), rf[back].astype("float64")
        if a.shape != c.shape or b.shape != d.shape or a.shape[0] != b.shape[1]:
            raise ValueError("incompatible factor layout")
        rank = a.shape[0]
        # Both have the same alpha/r. Their effective 50:50 mixture has these rank-2r factors.
        left_factor, right_factor = np.concatenate([b, d], 1) * 0.5, np.concatenate([a, c], 0)
        rb = np.linalg.qr(left_factor, mode="r")
        ra = np.linalg.qr(right_factor.T, mode="r")
        sv = np.linalg.svd(rb @ ra.T, compute_uv=False)
        signal = float(sv @ sv)
        # If both factors of the second member flip sign its entire behavior is invariant.
        ordinary_error = energy((b - d) * 0.25, a - c)
        flipped_error = energy((b + d) * 0.25, a + c)
        out.append({"projection": name.removesuffix(".lora_a"), "rank": rank, "signal_sq": signal,
                    "mean_factors_error_sq": ordinary_error, "sign_flipped_mean_factors_error_sq": flipped_error,
                    "best_same_rank_error_sq": float(sv[rank:] @ sv[rank:])})
    denom = sum(x["signal_sq"] for x in out)
    if denom <= 0:
        raise ValueError("zero effective edit")
    return {"left": left.name, "right": right.name, "left_sha256": digest(left), "right_sha256": digest(right),
            "relative_frobenius": {k.removesuffix("_error_sq"): (sum(z[k] for z in out) / denom) ** 0.5 for k in
                ("mean_factors_error_sq", "sign_flipped_mean_factors_error_sq", "best_same_rank_error_sq")},
            "projections": out}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--build-catalog", type=Path, help="new output directory for two native child/words mixtures")
    args = parser.parse_args()
    def path(cell):
        return args.catalog / (cell + ".gguf")
    results = {tag: measure(path("t80+g41data"), path(partner)) for tag, partner in
               (("identical", "t80+g41data"), ("parent_child", "t80+labchild"), ("two_specialists", "t80+g41words"))}
    results["child_and_words"] = measure(path("t80+labchild"), path("t80+g41words"))
    if args.build_catalog:
        build_pair(path("t80+labchild"), path("t80+g41words"), args.build_catalog)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, indent=2) + "\n")


if __name__ == "__main__":
    main()
