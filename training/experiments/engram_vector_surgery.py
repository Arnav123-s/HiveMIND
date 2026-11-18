"""Edit associations in the real scratch stem's output head and compare weight and activation surgery."""
import argparse
import hashlib
import json
import re
from pathlib import Path

import torch
from torch.nn import functional as F

from training import scratch
from training.experiments.engram_halves import fraction, quantized_weight


NAMES = ("acorn amber anchor apple apron arrow atlas badger bamboo barley basil beacon beetle berry birch bison "
         "brass brook brush cactus canyon cedar chalk cherry chestnut clay clover cobalt comet copper coral crane "
         "cricket daisy delta dune eagle elm ember falcon fern flint frost garnet glass granite grove harbor "
         "hazel heron honey indigo iris jade juniper kite larch laurel leaf linen lotus maple marble meadow").split()
COLORS = ("red", "blue", "green", "gold")
TRAIN = ("Send {n} to its {s} desk.", "Which desk handles {n} on the {s} shift?")
EXAM = ("For the {s} shift, where does {n} go?", "{n} needs a desk assignment for {s}.",
        "During {s} duty, please tell me the routing color for {n}.")


def encode(model, tokenizer, texts):
    vectors = []
    for i in range(0, len(texts), 32):
        ids = [torch.tensor([scratch.BOS] + tokenizer.encode(text).ids) for text in texts[i:i + 32]]
        batch = torch.nn.utils.rnn.pad_sequence(ids, batch_first=True, padding_value=scratch.PAD)
        h = model.body(batch)
        vectors.append(h[torch.arange(len(ids)), [len(row) - 1 for row in ids]])
    return torch.cat(vectors)


def joint(keys, values):
    k = keys.double()
    gram = k @ k.T + torch.eye(len(k), dtype=k.dtype) * 0.04
    return (torch.linalg.solve(gram, values.double()).T @ k).float()


def individual(keys, values):
    return ((values / keys.square().sum(1, keepdim=True).clamp_min(1e-9)).T @ keys)


def desired(h, ids, read):
    return F.one_hot(ids, num_classes=len(COLORS)).float() * 10 - h @ read.T


def score(h, codes, read, patch):
    return fraction((h @ (read + patch).T).argmax(1) == codes)


def compress(patch):
    scale = patch.abs().amax(1, keepdim=True).clamp_min(1e-12) / 127
    ints = (patch / scale).round().clamp(-127, 127).to(torch.int8)
    ternary, tri_scale = quantized_weight(patch, "rowfit")
    return {"int8": (ints.float() * scale, ints.numel() + 4 * len(scale)),
            "ternary": (ternary * tri_scale[:, None], 2 * ((ternary.numel() + 7) // 8) + 4 * len(tri_scale))}


def surgery_diagnostics(ordinary, read, full_weights, tokens, patch):
    # read @ decoder = I. W remains the input embedding; only the inference readout is edited.
    decoder = torch.linalg.pinv(read.double()).float()
    folded = full_weights + (full_weights @ decoder) @ patch
    reference = ordinary @ full_weights.T
    steered = (ordinary + (ordinary @ patch.T) @ decoder.T) @ full_weights.T
    mutated = ordinary @ folded.T
    scoped = reference.clone()
    scoped[:, tokens] += ordinary @ patch.T
    def effects(logits):
        return {"top1_kept": fraction(logits.argmax(1) == reference.argmax(1)),
                "mean_kl": F.kl_div(logits.log_softmax(1), reference.softmax(1), reduction="batchmean").item()}
    return {"max_full_vocab_fold_error": (steered - mutated).abs().max().item(),
            "candidate_logits_max_difference": (steered[:, tokens] - scoped[:, tokens]).abs().max().item(),
            "steer_hidden": effects(steered), "write_four_output_rows": effects(scoped)}


def study(seed, n, names, canonical, language, read, emb, tokens, ordinary):
    rng = torch.Generator().manual_seed(seed)
    first = torch.randperm(n, generator=rng) % 4
    second = (first + torch.randint(1, 4, (n,), generator=rng)) % 4
    h = canonical[:n]
    both = (first, second)
    rows = []
    for shift, labels in enumerate(both):
        train, exam = (x[:n] for x in language[shift])
        key = train.flatten(0, 1)
        real = labels.repeat_interleave(len(TRAIN))
        live = exam.flatten(0, 1)
        exam_labels = labels.repeat_interleave(len(EXAM))
        text_patch = joint(key, desired(key, real, read))
        target = desired(h, labels, read)
        patch = joint(h, target)
        row = {"original": score(h, labels, read, torch.zeros_like(patch)),
               "sum_rank_one": score(h, labels, read, individual(h, target)),
               "joint_known_name": score(h, labels, read, patch),
               "sentence_training": score(key, real, read, text_patch),
               "sentence_unseen_phrasing": score(live, exam_labels, read, text_patch),
               "fp32_weight_bytes": patch.numel() * patch.element_size()}
        # Exact-name retrieval is a genuine control. Resolve each held-out text using the directory alone.
        lookup = dict(zip(names[:n], labels.tolist()))
        hits = []
        for i, name in enumerate(names[:n]):
            for frame in EXAM:
                words = set(re.findall("[a-z]+", frame.format(n=name, s=("day", "night")[shift]).lower()))
                matches = words.intersection(lookup)
                hits.append(len(matches) == 1 and lookup[next(iter(matches))] == labels[i].item())
        row["name_directory"] = sum(hits) / len(hits)
        for fmt, (rounded, size) in compress(patch).items():
            row[fmt] = {"accuracy": score(h, labels, read, rounded), "weight_bytes": size}
        changed = torch.randperm(n, generator=rng)[:n // 4]
        stable = torch.ones(n, dtype=torch.bool)
        stable[changed] = False
        replacement = labels.clone()
        replacement[changed] = (replacement[changed] + 1) % 4
        current = patch.clone()
        fresh_target = desired(h, replacement, read)
        for index in changed:
            one = h[index:index + 1]
            current += individual(one, fresh_target[index:index + 1] - one @ current.T)
        refit = joint(h, fresh_target)
        row["one_quarter_reassigned"] = {
            key: {"changed": score(h[changed], replacement[changed], read, p),
                  "unaffected": score(h[stable], replacement[stable], read, p)}
            for key, p in (("sequential", current), ("refit_live_records", refit))}
        if shift == 0:
            row["unrelated_prompts_with_patch_forced_on"] = surgery_diagnostics(ordinary, read, emb, tokens, patch)
        rows.append(row)
    single = joint(torch.cat((h, h)), torch.cat([desired(h, y, read) for y in both]))
    return {"shifts": rows, "one_patch_no_shift": sum(score(h, y, read, single) for y in both) / 2}


@torch.inference_mode()
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    torch.set_num_threads(1)
    tokenizer = scratch.tokenizer()
    tokens = [tokenizer.encode(c).ids for c in COLORS]
    if any(len(x) != 1 for x in tokens):
        raise ValueError("expected four single-token routing labels")
    tokens = [x[0] for x in tokens]
    path = scratch.HOME / "base.pt"
    model = scratch.Tiny(bit=True).eval()
    model.load_state_dict(torch.load(path, weights_only=True))
    model.freeze_bit_weights()
    weights = model.tok.weight.detach()
    read = weights[tokens]
    canon = encode(model, tokenizer, ["Hive item " + name for name in NAMES])
    language = []
    for s in ("day", "night"):
        language.append([encode(model, tokenizer, [f.format(n=n, s=s) for n in NAMES for f in frames])
                         .reshape(len(NAMES), len(frames), -1) for frames in (TRAIN, EXAM)])
    ordinary = encode(model, tokenizer, [f.format(n=n) for n in NAMES for f in
                                         ("Tell me something about {n}.", "I wrote the word {n} in my notebook.")])
    seeds = [419, 431, 443, 457, 467]
    result = {"seeds": seeds, "stem_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
              "names": NAMES, "token_ids": tokens, "ordinary_prompt_count": len(ordinary), "trials": {}}
    for size in (4, 16, 32, 64):
        result["trials"][size] = {s: study(s, size, NAMES, canon, language, read, weights, tokens, ordinary) for s in seeds}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
