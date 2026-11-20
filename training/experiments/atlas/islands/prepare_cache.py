"""Compress the archived native feature/logit dump into the sufficient statistics for these output-only edits."""
import argparse
from hashlib import sha256
from pathlib import Path
import sys

import numpy as np

from data import corpus, EXTRA, HERE, ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--extras", type=Path, required=True, help="parent of hive-water-v2 and hive-timing-v2 raw dumps")
    parser.add_argument("--model", type=Path, required=True, help="t80 GGUF containing the native tokenizer")
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT / "training/llama_cpp_convert/gguf-py"))
    from gguf import GGUFReader
    class VocabularyReader(GGUFReader):
        def _build_tensors(self, start_offs, fields):
            # The standard GGUF reader knows the vocabulary metadata but not the IK weight formats.
            return
    reader = VocabularyReader(str(args.model))
    vocab = reader.get_field("tokenizer.ggml.tokens")
    rows, known = corpus()
    tokens = sorted({r.token for r in rows})
    scores, other, ids, words, anchors, vectors = [], [], [], [], [], []
    for row in rows:
        if "-extra-" in row.key:
            source = args.extras / ("hive-" + EXTRA[row.domain]) / ("new-train-" + row.key.split("-")[-1])
        else:
            source = args.original / row.key
        x = np.fromfile(source.with_suffix(".f32"), np.float32)
        logits = np.fromfile(source.with_suffix(".logits"), np.float32)
        assert x.shape == (4096,) and logits.shape == (151669,) and np.isfinite(logits).all()
        if row.key in known:
            assert np.array_equal(x, known[row.key])
        else:
            anchors.append(row.key)
            vectors.append(x)
        scores.append(logits[tokens])
        logits[tokens] = -np.inf
        outside = int(logits.argmax())
        ids.append(outside)
        other.append(logits[outside])
        def spelling(index):
            return vocab.contents(index).strip("ĠĊĉ \r\n\t").casefold()
        words.append(spelling(outside))
        assert spelling(row.token) == row.label.casefold()
    out = HERE / "cached-endpoints.npz"
    np.savez_compressed(out, ids=[r.key for r in rows], tokens=tokens, canonical_logits=scores, other_logits=other,
                        other_ids=ids, other_words=words, anchor_ids=anchors, anchor_features=vectors)
    print(sha256(out.read_bytes()).hexdigest(), out.name)


if __name__ == "__main__":
    main()
